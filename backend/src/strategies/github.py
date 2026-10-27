import base64
import logging
from typing import Optional
from urllib.parse import quote_plus, urlparse
import httpx
from client import GraphGithubClient
from queries import IMAGE_QUERY
from processor import ImageProcessor
from strategies.base import BaseStrategy

log = logging.getLogger(__name__)


def _data_uri_bytes(uri: str) -> bytes:
    try:
        return base64.b64decode(uri.split(",", 1)[1])
    except Exception:
        return b""


class HeuristicStrategy(BaseStrategy):
    def __init__(
        self,
        client: httpx.AsyncClient,
        processor: ImageProcessor,
        github_token: Optional[str] = None,
        url_cache: Optional[dict[str, str]] = None,
        ghc: Optional[GraphGithubClient] = None,
    ):
        super().__init__(client, processor, url_cache)
        self.github_token = github_token
        self.ghc = ghc or GraphGithubClient(token=github_token)
        self.github_avatar_url = "https://github.com/{owner}.png?size=128"
        self.github_identicon_url = "https://github.com/identicons/{owner}.png?size=128"
        self.gh_cache: dict[str, str] = {}

    def _get_github_headers(self, accept: str = "application/vnd.github.v3+json") -> dict:
        headers = {"User-Agent": "logo-ext/1.0", "Accept": accept}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    async def _is_github_org(self, owner: str) -> bool:
        cache_key = f"gh_type:{owner.lower()}"
        if cache_key in self.gh_cache:
            return self.gh_cache[cache_key] == "Organization"
        try:
            gh_headers = self._get_github_headers()
            res = await self.client.get(f"https://api.github.com/users/{owner}", headers=gh_headers)
            if res.status_code == 200:
                account_type = res.json().get("type", "")
                self.gh_cache[cache_key] = account_type
                return account_type == "Organization"
        except Exception as e:
            log.debug("Failed checking GitHub account type for %s: %s", owner, e)
        return False

    async def fetch_logo_candidates(self, owner: str, repo: str) -> Optional[tuple[str, str]]:
        """Discovers repo logo assets recursively via Git Trees API and ranks candidates."""
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        gh_headers = self._get_github_headers()

        try:
            response = await self.client.get(url, headers=gh_headers)
            if response.status_code != 200:
                return None
            tree = response.json().get("tree", [])
            noise = {"tests", "test", "fixture", "fixtures", "vendor", "node_modules", "examples", "example"}

            clean_repo = repo.lower().replace("-", "").replace("_", "")
            candidates: list[tuple[int, str]] = []

            for item in tree:
                if item.get("type") != "blob":
                    continue
                path = item["path"]
                path_lower = path.lower()
                if not path_lower.endswith((".svg", ".png", ".ico", ".webp")):
                    continue
                parts = set(path_lower.split("/"))
                if parts & noise:
                    continue
                diagram_noise = (
                    "diagram", "flowchart", "request", "architecture", "screenshot",
                    "preview", "workflow", "overview", "schema", "banner", "header",
                    "benchmark", "anchor", "sample", "sponsor", "sponsors", "sponsorkit"
                )
                if any(term in path_lower for term in diagram_noise):
                    continue

                filename = path_lower.split("/")[-1]
                clean_filename = filename.replace("-", "").replace("_", "")

                name_score = 0
                if clean_repo in clean_filename:
                    name_score += 60
                elif "logo" in filename:
                    name_score += 40
                elif "icon" in filename or "brand" in filename:
                    name_score += 30
                elif "favicon" in filename:
                    name_score += 15

                # Must have semantic match with repo, logo, icon, brand, or favicon
                if name_score == 0:
                    continue

                format_score = 50 if path_lower.endswith(".svg") else (20 if path_lower.endswith(".png") else 5)
                score = name_score + format_score
                candidates.append((score, path))

            candidates.sort(key=lambda x: (x[0], -len(x[1])), reverse=True)
            for _, image_path in candidates[:5]:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{image_path}"
                icon = await self._fetch_image(raw_url)
                if icon:
                    log.info("✓ Icon hit for %s/%s via repo tree asset (%s)", owner, repo, image_path)
                    return icon, raw_url
        except Exception as e:
            log.debug("Failed fetching tree for %s/%s: %s", owner, repo, e)
        return None

    async def resolve_topics(self, pkg_name: str) -> Optional[tuple[str, str, str]]:
        topics_url = f"https://raw.githubusercontent.com/github/explore/main/topics/{pkg_name}/{pkg_name}.png"
        icon = await self._fetch_image(topics_url)
        if icon:
            log.info("✓ Icon hit for %r via topics", pkg_name)
            return icon, "github_topic", topics_url
        return None

    async def resolve_graphql(self, owner: str, repo: str, pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        payload = {
            "query": IMAGE_QUERY,
            "variables": {
                "owner": owner,
                "name": repo,
            },
        }
        result = await self.ghc.execute(payload)
        data = (result or {}).get("repository") or {}

        if data:
            targets = ["logo_root", "logo_assets", "logo_docs", "logo_github"]
            for target in targets:
                dest = data.get(target)
                if dest and isinstance(dest, dict) and dest.get("text"):
                    probe_url = f"https://github.com/{owner}/{repo}/blob/HEAD/{target}.svg"
                    data_uri = self.processor.to_data_uri(
                        dest["text"].encode("utf-8"),
                        "image/svg+xml",
                        source=f"github:{owner}/{repo}:{target}",
                    )
                    if data_uri:
                        log.info("✓ Icon hit for %r via repo GraphQL probe (%s)", pkg_name or repo, target)
                        return data_uri, "github_repo_probe", probe_url

            if data.get("usesCustomOpenGraphImage"):
                og_url = data.get("openGraphImageUrl")
                if og_url:
                    icon = await self._fetch_image(og_url)
                    if icon:
                        log.info("✓ Icon hit for %r via custom OpenGraph (%s)", pkg_name or repo, og_url)
                        return icon, "github_opengraph", og_url

        return None

    async def search_repo(self, pkg_name: str) -> Optional[tuple[str, str, Optional[str]]]:
        """Search GitHub for repositories when registry metadata has missing/placeholder URLs. Returns (owner, repo, homepage_domain)."""
        try:
            bare_name = pkg_name.split(":")[-1]
            if bare_name.startswith("@") and "/" in bare_name:
                bare_name = bare_name.split("/", 1)[1]
            clean_name = bare_name.split("@")[0].strip().lower()
            if not clean_name:
                return None

            search_url = f"https://api.github.com/search/repositories?q={quote_plus(clean_name)}+in:name&sort=stars"
            gh_headers = self._get_github_headers()
            res_search = await self.client.get(search_url, headers=gh_headers)
            if res_search.status_code == 200:
                items = res_search.json().get("items", [])
                for item in items:
                    item_name = item.get("name", "").lower()
                    if item_name in (clean_name, clean_name.replace("-", "_"), clean_name.replace("_", "-")):
                        owner = item["owner"]["login"]
                        repo = item["name"]
                        custom_domain = None
                        if item.get("homepage"):
                            parsed_hp = urlparse(item["homepage"]).netloc
                            if parsed_hp and parsed_hp not in ("github.com", "gitlab.com", "pypi.org"):
                                custom_domain = parsed_hp
                        return owner, repo, custom_domain
            elif res_search.status_code in (403, 429):
                log.warning("GitHub search rate limited (HTTP %d) for query %r", res_search.status_code, clean_name)
        except Exception as e:
            log.debug("GitHub search fallback failed for %s: %s", pkg_name, e)
        return None

    async def resolve_avatar(self, owner: str, pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        if not await self._is_github_org(owner):
            log.debug("Skipping avatar for %r: %s is a personal User account", pkg_name or owner, owner)
            return None
        avatar_url = self.github_avatar_url.format(owner=owner)
        icon = await self._fetch_image(avatar_url)
        if not icon:
            return None
        identicon = await self._fetch_image(self.github_identicon_url.format(owner=owner))
        if not identicon:
            log.info("Skipping unverifiable GitHub avatar for %r (%s)", pkg_name or owner, owner)
            return None
        if self.processor.same_pixels(_data_uri_bytes(icon), _data_uri_bytes(identicon)):
            log.info("Skipping default GitHub avatar for %r (%s)", pkg_name or owner, owner)
            return None
        log.info("✓ Icon hit for %r via GitHub organization avatar (%s)", pkg_name or owner, owner)
        return icon, "github_org_avatar", avatar_url

    async def resolve(self, owner: str, repo: str, pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        """Resolves package to icon via GitHub explore topics, GraphQL probes, OpenGraph, or tree assets."""
        # 1. Topics
        if pkg_name:
            res_topic = await self.resolve_topics(pkg_name)
            if res_topic:
                return res_topic

        # 2. GraphQL probes
        res_gql = await self.resolve_graphql(owner, repo, pkg_name)
        if res_gql:
            return res_gql

        # 3. Git Tree scan
        res_tree = await self.fetch_logo_candidates(owner, repo)
        if res_tree:
            icon, url = res_tree
            return icon, "github_repo_tree", url

        return None
