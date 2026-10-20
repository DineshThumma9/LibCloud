import logging
from client import GraphGithubClient
from collections import defaultdict
import asyncio
import tempfile
import glob
import subprocess
from constants import TARGETS
from queries import REPO_DEP_QUERY, REPOS_QUERY
from parser import DependencyParser
from models import PKGInfo
from pathlib import Path
from storage import DepsDB 


log = logging.getLogger(__name__)

class GraphGithubAPI:
    def __init__(self, username: str, token: str = None, allow_fork: bool = False):
        self.token = token
        self.token_exists = bool(token)
        self.allow_fork = allow_fork 
        self.username = username
        self.ghc = GraphGithubClient(token=token)
        self.dep_db = DepsDB()
        self.parser = DependencyParser()

    async def fetch_all_user_repos(self) -> list[dict]:
        all_repos = []
        cursor = None
        has_next = True
        page = 0

        log.info("Fetching repos for user: %s (forks=%s, private=%s)", self.username, self.allow_fork, self.token_exists)

        while has_next:
            page += 1
            payload = {
                "query": REPOS_QUERY,
                "variables": {"owner": self.username, "cursor": cursor},
            }
            user_data = await self.ghc.execute(variables=payload)
            if not user_data:
                log.warning("No data returned from GitHub API on page %d — stopping", page)
                break

            repos_container = user_data.get("user", {}).get("repositories", {})
            nodes = repos_container.get("nodes", [])

            for repo in nodes:
                name = repo.get("name", "?")
                
                if not self.allow_fork and repo.get("isFork"):
                    log.debug("  skip %-40s (fork)", name)
                    continue
                if repo.get("isPrivate") and not self.token_exists:
                    log.debug("  skip %-40s (private, no token)", name)
                    continue
                log.debug("  + %-40s", name)
                all_repos.append(repo)

            page_info = repos_container.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

        log.info("Found %d repos for %s", len(all_repos), self.username)
        return all_repos

    async def fetch_repo_deps(self, repo: str, repo_sha: str = ""):
        res = await self.dep_db.get_repo_deps(username=self.username, repo=repo, repo_sha=repo_sha)
        if res:
            pkg_dic = defaultdict(PKGInfo)
            for norm, data in res.items():
                if isinstance(data, dict):
                    pkg_dic[norm] = PKGInfo(
                        count=data.get("count", 0),
                        dep_origin=data.get("dep_origin", ""),
                        raw_names=set(data.get("raw_names", []))
                    )
                else:
                    pkg_dic[norm] = data
            log.info("  ⚡ [Cache HIT: Repo] %s/%s (%d packages restored — scan skipped)", self.username, repo, len(pkg_dic))
            return pkg_dic 

        pkg_dic = defaultdict(PKGInfo)
        log.info("  ┌─ %s/%s", self.username, repo)

        variables = {"owner": self.username, "repo": repo}
        dep_json = {"query": REPO_DEP_QUERY, "variables": variables}
        result = await self.ghc.execute(dep_json)

        repo_data = (result or {}).get("repository") or {}
        has_docker = bool(
            repo_data.get("dockerfile")
            or repo_data.get("dockerfile_lower")
            or repo_data.get("docker_compose")
            or repo_data.get("docker_compose_yaml")
            or repo_data.get("compose_yaml")
        )
        if has_docker:
            pkg = pkg_dic["Docker"]
            pkg.count += 1
            pkg.dep_origin = "docker"
            pkg.raw_names.add("docker")
            log.info("  │  ✓ Docker detected in %s", repo)

        manifests = repo_data.get("dependencyGraphManifests", {}).get("nodes", [])

        if manifests:
            log.info("  │  path: GitHub dependency graph API (%d manifest(s))", len(manifests))
            for manifest in manifests:
                raw_fname = manifest["filename"]
                fname = Path(raw_fname).name

                if fname in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "poetry.lock", "Pipfile.lock", "uv.lock"):
                    continue

                before = len(pkg_dic)
                for dep in manifest["dependencies"]["nodes"]:
                    raw_dep = dep["packageName"]
                    norm_dep, lang = self.parser.normalize_pkg(raw_dep, raw_fname)
                    if norm_dep and lang:
                        pkg = pkg_dic[norm_dep]
                        pkg.count += 1
                        pkg.dep_origin = lang
                        pkg.raw_names.add(raw_dep)

                extracted = len(pkg_dic) - before
                log.info("  │  %-30s → %d package(s) extracted", fname, extracted)
            if pkg_dic:
                log.info("  └─ total: %d unique packages", len(pkg_dic))
                return pkg_dic

        log.info("  │  path: git-clone fallback (no dependency graph)")
        auth_url = (
            f"https://{self.token}@github.com/{self.username}/{repo}.git"
            if self.token
            else f"https://github.com/{self.username}/{repo}.git"
        )
       
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                log.info("  │  cloning %s/%s ...", self.username, repo)
                proc = await asyncio.create_subprocess_exec(
                    "git", "clone", "--depth", "1", auth_url, tmp_dir,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.communicate()
                log.info("  │  clone done, scanning for: %s", TARGETS)

                root = Path(tmp_dir)
                for target in TARGETS:
                    found_files = [f for f in root.rglob(target) if not any(p in f.parts for p in ("node_modules", ".venv", "venv", ".git", "target"))]
                    if not found_files:
                        continue
                    if target.lower() in ("dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml"):
                        pkg = pkg_dic["Docker"]
                        pkg.count += 1
                        pkg.dep_origin = "docker"
                        pkg.raw_names.add("docker")
                        log.info("  │  ✓ Docker detected from %s in %s", target, repo)
                        continue
                    log.info("  │  found %d × %s", len(found_files), target)    
                    for pkgfile in found_files:
                        try:
                            before = len(pkg_dic)
                            try:
                                content = pkgfile.read_text(encoding="utf-8-sig")
                            except UnicodeDecodeError:
                                content = pkgfile.read_text(encoding="utf-16")
                            sub_dic = self.parser.parser(content, target)
                            for norm, info in sub_dic.items():
                                pkg = pkg_dic[norm]
                                pkg.count += info.count
                                pkg.dep_origin = info.dep_origin
                                pkg.raw_names |= info.raw_names
                            extracted = len(pkg_dic) - before
                            log.info("  │    %-50s → %d package(s)", str(pkgfile.relative_to(root)), extracted)
                        except Exception as e:
                            log.warning("  │    failed to parse %s: %s", pkgfile, e)

            except Exception as e:
                log.error("  │  clone failed for %s/%s: %s", self.username, repo, e)

        await self.dep_db.save_repo_deps(username=self.username, repo=repo, repo_sha=repo_sha, pkg_dic=pkg_dic)
        log.info("  └─ total: %d unique packages", len(pkg_dic))
        return pkg_dic

    async def fetch_all_repos_deps(self, export_csv: bool = True):
        # Fetches every repo of users 
        repos = await self.fetch_all_user_repos()

        log.info("=" * 60)
        log.info("Scanning dependencies across %d repos for %s", len(repos), self.username)
        log.info("=" * 60)

        # Complete counter of Lib used in All Repo 
        pkg_dics = defaultdict(PKGInfo)
        semp = asyncio.Semaphore(7)

        async def task(i: int, repo: dict):
            async with semp:
                log.info("[%d/%d] %s", i, len(repos), repo["name"])
                # Fetches a Single repo deps 
                defaultRef = repo.get("defaultBranchRef")
                if not defaultRef:
                    return None 
                target_sha = defaultRef.get("target", {}).get("oid", "")
                return await self.fetch_repo_deps(repo=repo["name"], repo_sha=target_sha)

        results = await asyncio.gather(*(task(i, repo) for i, repo in enumerate(repos, 1)))

        # Aggregate everything and Return 
        for r in results:
            if r:
                for norm, info in r.items():
                    pkg = pkg_dics[norm]
                    pkg.count += info.count
                    pkg.dep_origin = info.dep_origin
                    pkg.raw_names |= info.raw_names

        top_10 = sorted(pkg_dics.items(), key=lambda x: x[1].count, reverse=True)[:10]
        log.info("=" * 60)
        log.info("Done. %d unique packages found across all repos", len(pkg_dics))
        log.info("Top 10: %s", [(k, v.count) for k, v in top_10])
        log.info("=" * 60)

        if export_csv and self.parser.can_records:
            self.parser.export_filtered_csv()

        return pkg_dics

    def export_filtered_csv(self, filepath: str = "filtered_packages.csv"):
        return self.parser.export_filtered_csv(filepath)


async def fetch_all_repos_deps(username: str, token: str = None, export_csv: bool = True):
    api = GraphGithubAPI(username=username, token=token)
    return await api.fetch_all_repos_deps(export_csv=export_csv)

