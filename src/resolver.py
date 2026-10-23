import asyncio
import base64
import logging
from pathlib import Path
from typing import Optional, Union, Iterable
import httpx
import re
import struct
from collections import Counter
from urllib.parse import urljoin, urlparse

from constants import PACKAGE_REGISTRY, SLUG_MAP, NORM,HOSTING_BLOCKLIST
from models import PKG_MODELS, PKGInfo, ProjectLinks
from storage import DepsDB
from config import settings
from queries import IMAGE_QUERY
from client import GraphGithubClient
from ops_logger import DepOpsLogger


log = logging.getLogger(__name__)


all_norm = {}
for lang_map in NORM.values():
    all_norm.update({k.lower(): v for k, v in lang_map.items()})


class ValidationResult(tuple):
    """
    Tuple representing (is_valid, reason).
    Unpacks as 2 items (is_valid, reason) for backwards compatibility with tests,
    while also exposing .mime_type, .is_valid, and .reason attributes.
    """
    def __new__(cls, is_valid: bool, reason: str, mime_type: str = ""):
        obj = super().__new__(cls, (is_valid, reason))
        obj.is_valid = is_valid
        obj.reason = reason
        obj.mime_type = mime_type
        return obj


class ImageResolver:
    def __init__(self, timeout: float = settings.request_timeout_seconds, headers: Optional[dict] = None, github_token: Optional[str] = None):
        self.cache = DepsDB()
        self.url_cache: dict[str, str] = {}
        self.gh_cache: dict[str, str] = {}
        self.failed_icons: list[dict] = []
        self._seen_failed: set[str] = set()
        
        # Telemetry & metrics ledgers
        self.recovery_stats = Counter()
        self.resolved_methods: dict[str, str] = {}
        self.resolved_urls: dict[str, str] = {}
        self.validation_failures: list[dict] = []
        self._seen_validation_failures: set[str] = set()
        self.exporter = DepOpsLogger()

        client_headers = headers or {"User-Agent": "logo-ext/1.0"}
        self.client = httpx.AsyncClient(timeout=timeout, headers=client_headers)
        self.github_token = github_token
        self.favicon_url = "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128"
        self.github_avatar_url = "https://github.com/{owner}.png?size=128"
        self.ghc = GraphGithubClient(token=github_token)

    def _get_github_headers(self, accept: str = "application/vnd.github.v3+json") -> dict:
        headers = {"User-Agent": "logo-ext/1.0", "Accept": accept}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    @staticmethod
    def validate_image(content: bytes, mime_type: str = "") -> ValidationResult:
        """
        Validates image bytes. Returns ValidationResult(is_valid, reason, mime_type).
        Checks file signatures (magic bytes), minimum size, and SVG structure.
        """
        if not content or len(content) < 40:
            return ValidationResult(False, "file_too_small_or_empty", "")

        # Reject HTML error pages masked as 200 OK
        header = content[:1024].lower()
        if b"<!doctype html" in header or b"<html" in header:
            return ValidationResult(False, "is_html_page_not_image", "")

        # SVG Validation
        if b"<svg" in header or "svg" in mime_type:
            text = content.decode("utf-8", errors="ignore").lower()
            if "<svg" not in text:
                return ValidationResult(False, "malformed_svg_missing_svg_tag", "")
            if "</svg>" not in text and "/>" not in text:
                return ValidationResult(False, "malformed_svg_unclosed", "")
            return ValidationResult(True, "valid_svg", "image/svg+xml")

        # PNG Validation
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            if len(content) < 24:
                return ValidationResult(False, "corrupt_png_header", "")
            try:
                width, height = struct.unpack(">II", content[16:24])
                if width <= 2 and height <= 2:
                    return ValidationResult(False, f"rejected_tracking_pixel_{width}x{height}", "")
                if width / max(height, 1) > 1.6 or height / max(width, 1) > 1.6:
                    return ValidationResult(False, f"rejected_banner_aspect_ratio_{width}x{height}", "")
                return ValidationResult(True, f"valid_png_{width}x{height}", "image/png")
            except Exception:
                return ValidationResult(True, "valid_png", "image/png")

        # ICO Validation
        if content.startswith(b"\x00\x00\x01\x00"):
            return ValidationResult(True, "valid_ico", "image/x-icon")

        # JPEG Validation
        if content.startswith(b"\xff\xd8\xff"):
            return ValidationResult(True, "valid_jpeg", "image/jpeg")

        # WebP Validation
        if content.startswith(b"RIFF") and b"WEBP" in content[8:16]:
            return ValidationResult(True, "valid_webp", "image/webp")

        return ValidationResult(False, "unknown_unsupported_format", "")

    def _to_data_uri(self, content: bytes, mime: str = "", source: str = "") -> Optional[str]:
        val = ImageResolver.validate_image(content, mime)
        if not val.is_valid:
            log.info("Validation rejected image from %s: %s", source, val.reason)
            if source and source not in self._seen_validation_failures:
                self._seen_validation_failures.add(source)
                self.validation_failures.append({
                    "url": source,
                    "reason": val.reason,
                    "size_bytes": len(content)
                })
            return None
        detected_mime = val.mime_type or (mime if mime.startswith("image/") else "image/png")
        if detected_mime == "image/svg+xml":
            try:
                text = content.decode("utf-8", errors="ignore")
                sanitized = self._sanitize_svg(text)
                content = sanitized.encode("utf-8")
            except Exception as e:
                log.debug("Failed sanitizing SVG from %s: %s", source, e)
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{detected_mime};base64,{b64}"

    @staticmethod
    def _sanitize_svg(svg_text: str) -> str:
        """
        1. Strips hardcoded white background <rect> elements to eliminate bright box contrast.
        2. Inverts near-black fills to white (#ffffff) for visibility on dark backgrounds.
        3. Injects fill="#ffffff" if no fill is defined anywhere (preventing default black).
        """
        svg_text = re.sub(
            r'<rect[^>]*fill=["\'](?:#fff(?:fff)?|white)["\'][^>]*\/?>',
            '',
            svg_text,
            flags=re.IGNORECASE,
        )
        svg_text = re.sub(
            r'<rect[^>]*style=["\'][^"\']*fill:\s*(?:#fff(?:fff)?|white)[^"\']*["\'][^>]*\/?>',
            '',
            svg_text,
            flags=re.IGNORECASE,
        )

        dark_colors = {
            "#000", "#000000", "#111", "#111111", "#161618",
            "#181717", "#1a1a1a", "#222", "#222222", "#2d3748", "black"
        }

        def replace_fill(match):
            val = match.group(1).lower().strip()
            if val in dark_colors:
                return 'fill="#ffffff"'
            return match.group(0)

        svg_text = re.sub(r'fill=["\']([^"\']+)["\']', replace_fill, svg_text, flags=re.IGNORECASE)

        def replace_style_fill(match):
            val = match.group(1).lower().strip()
            if val in dark_colors:
                return 'fill: #ffffff'
            return match.group(0)

        svg_text = re.sub(r'fill:\s*([^;}"\']+)', replace_style_fill, svg_text, flags=re.IGNORECASE)

        if "fill=" not in svg_text and "fill:" not in svg_text:
            svg_text = re.sub(r'<svg\b([^>]*)>', r'<svg\1 fill="#ffffff">', svg_text, count=1, flags=re.IGNORECASE)

        return svg_text

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
                diagram_noise = ("diagram", "flowchart", "request", "architecture", "screenshot", "preview", "workflow", "overview", "schema", "banner", "header", "benchmark")
                if any(term in path_lower for term in diagram_noise):
                    continue

                score = 0
                filename = path_lower.split("/")[-1]
                if path_lower.endswith(".svg"):
                    score += 50
                elif path_lower.endswith(".png"):
                    score += 20
                elif path_lower.endswith(".ico"):
                    score += 5

                clean_filename = filename.replace("-", "").replace("_", "")
                if clean_repo in clean_filename:
                    score += 60
                elif filename.startswith("logo"):
                    score += 40
                elif filename.startswith("icon") or "brand" in filename:
                    score += 30
                elif "favicon" in filename:
                    score += 15

                if score > 0:
                    candidates.append((score, path))

            candidates.sort(key=lambda x: x[0], reverse=True)
            for _, image_path in candidates[:5]:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{image_path}"
                icon = await self._fetch_image(raw_url)
                if icon:
                    log.info("✓ Icon hit for %s/%s via repo tree asset (%s)", owner, repo, image_path)
                    return icon, raw_url
        except Exception as e:
            log.debug("Failed fetching tree for %s/%s: %s", owner, repo, e)
        return None

    async def _fetch_image(self, url: str) -> Optional[str]:
        """Fetch image bytes and return as base64 data URI with SVG sanitization and validation."""
        if url in self.url_cache:
            log.info("⚡ [Cache HIT: Image URL] %s", url)
            return self.url_cache[url]
        try:
            res = await self.client.get(url, follow_redirects=True)
            if res.status_code == 200 and len(res.content) > 0:
                ct = res.headers.get("content-type", "").lower()
                data_uri = self._to_data_uri(res.content, mime=ct, source=url)
                if data_uri:
                    self.url_cache[url] = data_uri
                    return data_uri
            log.debug("HTTP %d for image: %s", res.status_code, url)
        except Exception as e:
            log.debug("Failed fetching image from %s: %s", url, e)
        return None

    async def _fetch_json(self, url: str) -> Optional[dict]:
        """Fetch JSON data from package registries."""
        try:
            res = await self.client.get(url, follow_redirects=True)
            if res.status_code == 200:
                return res.json()
            log.debug("HTTP %d for registry JSON: %s", res.status_code, url)
        except Exception as e:
            log.debug("Failed fetching JSON from %s: %s", url, e)
        return None

    async def _is_github_org(self, owner: str) -> bool:
        """Checks if a GitHub account is an Organization (ignoring personal User accounts)."""
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

    async def fetch_iconlib(self, slug: str) -> Optional[tuple[str, str]]:
        """Tries distinct vector registries using auto-generated slug variations. Returns (icon, source_url)."""
        raw = slug.strip().lower().replace("_", "-")
        
        compact = raw.replace(" ", "").replace("-", "").replace(".", "dot")
        kebab = raw.replace(" ", "-").replace(".", "")

        candidate_urls = [
            # Tier 1: Devicon (True multi-color official SVGs)
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-original.svg",
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-original-wordmark.svg",
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-plain-wordmark.svg",
            
            # Tier 2: SimpleIcons (Official brand hex colors, 3,300+ entries, square icon marks)
            f"https://cdn.simpleicons.org/{compact}",
            
            # Tier 3: Iconify Gilbarbara Logos (Single check)
            f"https://api.iconify.design/logos:{kebab}.svg",
            
            # Tier 4: Devicon plain
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-plain.svg",
        ]

        for url in dict.fromkeys(candidate_urls):
            icon = await self._fetch_image(url)
            if icon:
                log.info("✓ Icon hit for %r via %s", slug, url)
                return icon, url
                
        return None

    async def resolve_heuristic(self, owner: str, repo: str, pkg_name: str) -> Optional[tuple[str, str, str]]:
        """Resolves package to icon via GitHub explore topics, GraphQL probes, OpenGraph, or tree assets. Returns (icon, method, source_url)."""
        # 1. Try github/explore topics first
        topics_url = f"https://raw.githubusercontent.com/github/explore/main/topics/{pkg_name}/{pkg_name}.png"
        icon = await self._fetch_image(topics_url)
        if icon:
            log.info("✓ Icon hit for %r via topics", pkg_name)
            return icon, "github_topic", topics_url
        
        # 2. Query GitHub GraphQL for custom OpenGraph, homepage, and top convention paths
        payload = {
            "query": IMAGE_QUERY,
            "variables": {
                "owner": owner,
                "name": repo
            }
        }

        result = await self.ghc.execute(payload)
        data = (result or {}).get("repository") or {}

        if data:
            # Check custom OpenGraph branding
            if data.get("usesCustomOpenGraphImage"):
                og_url = data.get("openGraphImageUrl")
                if og_url:
                    icon = await self._fetch_image(og_url)
                    if icon:
                        log.info("✓ Icon hit for %r via custom OpenGraph (%s)", pkg_name, og_url)
                        return icon, "github_opengraph", og_url

            # Check inlined SVG convention paths
            targets = ["logo_root", "logo_assets", "logo_docs", "logo_github"]
            for target in targets:
                dest = data.get(target)
                if dest and isinstance(dest, dict) and dest.get("text"):
                    svg_text = self._sanitize_svg(dest["text"])
                    probe_url = f"https://github.com/{owner}/{repo}/blob/HEAD/{target}.svg"
                    data_uri = self._to_data_uri(
                        svg_text.encode("utf-8"), 
                        "image/svg+xml", 
                        source=f"github:{owner}/{repo}:{target}"
                    )
                    if data_uri:
                        log.info("✓ Icon hit for %r via repo GraphQL probe (%s)", pkg_name, target)
                        return data_uri, "github_repo_probe", probe_url

            # Check homepage / docs site
            homepage = data.get("homepageUrl")
            if homepage:
                clean_repo = repo.lower().replace("-", "").replace("_", "")
                candidate_urls = [
                    urljoin(homepage, f"/img/{repo}.svg"),
                    urljoin(homepage, f"/img/{clean_repo}.svg"),
                    urljoin(homepage, "/favicon.svg"),
                    urljoin(homepage, "/logo.svg"),
                    urljoin(homepage, "/favicon.png"),
                    urljoin(homepage, "/logo.png"),
                    urljoin(homepage, "/favicon.ico"),
                ]
                domain = urlparse(homepage).netloc
                if domain:
                    candidate_urls.append(self.favicon_url.format(domain=domain))
                
                for url in dict.fromkeys(candidate_urls):
                    icon = await self._fetch_image(url)
                    if icon:
                        log.info("✓ Icon hit for %r via homepage (%s)", pkg_name, url)
                        return icon, "homepage_favicon", url

        # 3. Deep fallback: scan git tree
        tree_res = await self.fetch_logo_candidates(owner=owner, repo=repo)
        if tree_res:
            tree_icon, tree_url = tree_res
            return tree_icon, "github_repo_tree", tree_url

        return None

    async def resolve_package(self, pkg_name: str, dep_origin: str, norm_name: str) -> Optional[tuple[str, str, str]]:
        """Resolves package to icon via registry -> website favicon -> GitHub heuristic -> GitHub avatar. Returns (icon, method, source_url)."""
        if not dep_origin:
            return None

        slug = SLUG_MAP.get(norm_name, norm_name).lower()
        res = await self.cache.get_icon_entry(slug)
        if res:
            icon, source_url = res
            return icon, "db_cache", source_url or "db_cache"

        # Direct GitHub Actions repository probe
        if dep_origin == "actions":
            if "/" in pkg_name:
                parts = pkg_name.split("/")
                owner = parts[0]
                repo = parts[1].split("@")[0]
                res_h = await self.resolve_heuristic(owner=owner, repo=repo, pkg_name=pkg_name)
                if res_h:
                    return res_h
            return None

        # Direct Go module repository probe
        if dep_origin == "go":
            if pkg_name.startswith("github.com/"):
                parts = [p for p in pkg_name.split("/") if p]
                if len(parts) >= 3:
                    owner = parts[1]
                    repo = parts[2]
                    res_h = await self.resolve_heuristic(owner=owner, repo=repo, pkg_name=pkg_name)
                    if res_h:
                        return res_h
            elif "/" in pkg_name:
                parts = [p for p in pkg_name.split("/") if p]
                domain = parts[0]
                if domain not in HOSTING_BLOCKLIST and "." in domain:
                    fav_url = self.favicon_url.format(domain=domain)
                    icon = await self._fetch_image(fav_url)
                    if icon:
                        return icon, "homepage_favicon", fav_url
    
        reg_template = PACKAGE_REGISTRY.get(dep_origin)
        Model = PKG_MODELS.get(dep_origin)
        if not reg_template or not Model:
            return None

        links = ProjectLinks()
        data_json = await self._fetch_json(reg_template.format(pkg=pkg_name))
        if data_json:
            try:
                links = Model.model_validate(data_json).extract_links()
            except Exception as e:
                log.debug("Failed parsing registry links for %r: %s", pkg_name, e)

        # Search fallback for repositories where PyPI / NPM / Maven metadata has missing/placeholder URLs
        if not (links.github_owner and links.github_repo):
            try:
                bare_name = pkg_name.split(":")[-1]
                if bare_name.startswith("@") and "/" in bare_name:
                    bare_name = bare_name.split("/", 1)[1]
                clean_name = bare_name.split("@")[0].strip().lower()
                if clean_name:
                    from urllib.parse import quote_plus
                    search_url = f"https://api.github.com/search/repositories?q={quote_plus(clean_name)}+in:name&sort=stars"
                    gh_headers = self._get_github_headers()
                    res_search = await self.client.get(search_url, headers=gh_headers)
                    if res_search.status_code == 200:
                        items = res_search.json().get("items", [])
                        for item in items:
                            item_name = item.get("name", "").lower()
                            if item_name in (clean_name, clean_name.replace("-", "_"), clean_name.replace("_", "-")):
                                links.github_owner = item["owner"]["login"]
                                links.github_repo = item["name"]
                                if not links.custom_domain and item.get("homepage"):
                                    parsed_hp = urlparse(item["homepage"]).netloc
                                    if parsed_hp and parsed_hp not in ("github.com", "gitlab.com", "pypi.org"):
                                        links.custom_domain = parsed_hp
                                break
                    elif res_search.status_code in (403, 429):
                        log.warning("GitHub search rate limited (HTTP %d) for query %r", res_search.status_code, clean_name)
            except Exception as e:
                log.debug("GitHub search fallback failed for %s: %s", pkg_name, e)

        try:
            # 1. GitHub heuristic (uses parsed owner & repo)
            if links.github_owner and links.github_repo:
                res_h = await self.resolve_heuristic(
                    owner=links.github_owner,
                    repo=links.github_repo,
                    pkg_name=pkg_name
                )
                if res_h:
                    return res_h

            # 2. Custom domain favicon fallback
            if links.custom_domain:
                fav_url = self.favicon_url.format(domain=links.custom_domain)
                icon = await self._fetch_image(fav_url)
                if icon:
                    log.info("✓ Icon hit for %r via website favicon (%s)", pkg_name, links.custom_domain)
                    return icon, "homepage_favicon", fav_url

            # 3. GitHub organization avatar
            if links.github_owner:
                is_org = await self._is_github_org(links.github_owner)
                if is_org:
                    avatar_url = self.github_avatar_url.format(owner=links.github_owner)
                    icon = await self._fetch_image(avatar_url)
                    if icon:
                        log.info("✓ Icon hit for %r via GitHub organization avatar (%s)", pkg_name, links.github_owner)
                        return icon, "github_org_avatar", avatar_url
                else:
                    log.debug("Skipping avatar for %r: %s is a personal User account", pkg_name, links.github_owner)

        except Exception as e:
            log.debug("Failed resolving icon links for %r: %s", pkg_name, e)

        log.warning("✗ Missing icon for %r — no icon found across all sources", pkg_name)
        return None

    async def resolve(
        self,
        pkg_dic: Union[dict[str, Union[PKGInfo, int]], Iterable[tuple[str, Union[PKGInfo, int]]]],
        export_csv: bool = True,
    ) -> list[tuple[str, str, int]]:
        """
        Resolves all packages to data URI icons.
        Groups by canonical tool (slug) first so technologies never appear twice,
        and their total counts accumulate correctly.
        """
        items = list(pkg_dic.items()) if hasattr(pkg_dic, "items") else list(pkg_dic)


        # 1. Group and accumulate by canonical key before fetching
        grouped: dict[str, dict] = {}
        for norm_name, val in items:
            canonical_name = all_norm.get(norm_name.lower(), norm_name)
            slug = SLUG_MAP.get(canonical_name, canonical_name).lower()
            key = slug
            if isinstance(val, PKGInfo):
                count = val.count
                dep_origin = val.dep_origin
                raw_name = next(iter(val.raw_names), norm_name) if val.raw_names else norm_name
            else:
                count = val
                dep_origin = ""
                raw_name = norm_name

            if key in grouped:
                grouped[key]["count"] += count
            else:
                grouped[key] = {
                    "norm_name": canonical_name,
                    "count": count,
                    "dep_origin": dep_origin,
                    "raw_name": raw_name,
                    "val_ref": val if isinstance(val, PKGInfo) else None,
                }

        total = len(grouped)
        semp = asyncio.Semaphore(settings.max_concurrent_icon_resolves)

        async def task(i: int, key: str, entry: dict):
            async with semp:
                norm_name = entry["norm_name"]
                count = entry["count"]
                dep_origin = entry["dep_origin"]
                raw_name = entry["raw_name"]
                log.info("[%d/%d] %s", i, total, norm_name)

                # Check DB cache first
                slug = SLUG_MAP.get(norm_name, norm_name)
                cached = await self.cache.get_icon_entry(slug)
                if cached:
                    cached_icon, cached_url = cached
                    self.recovery_stats["db_cache"] += 1
                    self.resolved_methods[norm_name] = "db_cache"
                    self.resolved_urls[norm_name] = cached_url or "db_cache"
                    return (norm_name, cached_icon, count)

                # 1. Check icon libraries first
                res_cdn = await self.fetch_iconlib(slug)
                if res_cdn:
                    icon, source_url = res_cdn
                    self.recovery_stats["cdn_catalog"] += 1
                    self.resolved_methods[norm_name] = "cdn_catalog"
                    self.resolved_urls[norm_name] = source_url
                    await self.cache.save_icon(slug, icon, source_url=source_url)
                    return (norm_name, icon, count)

                # 2. Fall back to package registry & GitHub heuristic lookup
                res_pkg = None
                if dep_origin:
                    res_pkg = await self.resolve_package(raw_name, dep_origin, norm_name)
                    if not res_pkg and slug and slug != raw_name.lower():
                        res_pkg = await self.resolve_package(slug, dep_origin, norm_name)

                if res_pkg:
                    icon, method, source_url = res_pkg
                    self.recovery_stats[method] += 1
                    self.resolved_methods[norm_name] = method
                    self.resolved_urls[norm_name] = source_url
                    await self.cache.save_icon(slug, icon, source_url=source_url)
                    return (norm_name, icon, count)

                log.warning("✗ Missing icon for %r — skipped from cloud", norm_name)
                if norm_name not in self._seen_failed:
                    self._seen_failed.add(norm_name)
                    self.failed_icons.append({
                        "norm_name": norm_name,
                        "raw_name": raw_name,
                        "dep_origin": dep_origin,
                        "count": count,
                        "slug_tried": slug,
                        "reason": "no_icon_found",
                    })
                return None

        results = await asyncio.gather(*(task(i, k, v) for i, (k, v) in enumerate(grouped.items(), 1)))

        # Deduplicate by icon URI so identical logos never render multiple times
        unique_badges: dict[str, dict] = {}
        for item in results:
            if item:
                norm_name, icon, count = item
                if icon in unique_badges:
                    unique_badges[icon]["count"] += count
                else:
                    unique_badges[icon] = {
                        "norm_name": norm_name,
                        "icon": icon,
                        "count": count,
                    }

        badge_items = [
            (entry["norm_name"], entry["icon"], entry["count"])
            for entry in unique_badges.values()
        ]

        self.export_reports(badge_items, should_export=export_csv)
        return badge_items

    def export_reports(self, badge_items: list[tuple[str, str, int]], should_export: bool = True):
        """Exports all report CSVs and HTML visual audit via exporter if should_export is True."""
        if not should_export:
            return
        self.exporter.export_failed_icons_csv(self.failed_icons)
        self.exporter.export_output_csv(badge_items, self.resolved_methods, self.resolved_urls)
        self.exporter.export_audit_html(badge_items, self.resolved_methods, self.resolved_urls)
        self.exporter.export_resolution_metrics_csv(self.recovery_stats, self.failed_icons)
        if self.validation_failures:
            self.exporter.export_validation_failures_csv(self.validation_failures)


    async def aclose(self):
        await self.client.aclose()
        if hasattr(self, "ghc") and self.ghc:
            await self.ghc.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()
