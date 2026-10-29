from app.jobs import JobManager
import logging
from app.client import GraphGithubClient
from collections import defaultdict
import asyncio
import tempfile
from app.constants import SLUG_MAP, TARGETS
from app.queries import REPO_DEP_QUERY, REPOS_QUERY
from app.parser import DependencyParser
from app.models import PKGInfo, merge_pkg_dicts
from pathlib import Path
from app.storage import DepsDB 
from app.config import settings
import time 
from typing import Optional
import os 


log = logging.getLogger(__name__)


def _read_file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-16")


class GraphGithubAPI:
    def __init__(
        self,
        username: str,
        token: str = None,
        allow_fork: bool = False,
        job_manager: Optional[JobManager] = None,
        report_dir: Optional[Path] = None,
    ):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.allow_fork = allow_fork 
        self.username = username
        self.ghc = GraphGithubClient(token=self.token)
        self.dep_db = DepsDB()
        self.parser = DependencyParser()
        self.job_manager = job_manager 
        self.report_dir = Path(report_dir) if report_dir is not None else None
        self.repo_count = 0
        

    @property
    def token_exists(self) -> bool:
        return bool(self.token)

    async def aclose(self):
        if hasattr(self, "ghc") and self.ghc:
            await self.ghc.close()

    async def __aenter__(self):
        return self 
    
    async def __aexit__(self, *args):
        await self.aclose()

    def _ingest_manifest_file(self, file_path: Path, origin: str, pkg_dic: dict[str, PKGInfo], root: Path):
        try:
            before = len(pkg_dic)
            content = _read_file_text(file_path)
            sub_dic = self.parser.parser(content, origin)
            merge_pkg_dicts(pkg_dic, sub_dic)
            extracted = len(pkg_dic) - before
            log.info("  │    %-50s → %d package(s)", str(file_path.relative_to(root)), extracted)
        except Exception as e:
            log.warning("  │    failed to parse %s: %s", file_path, e)

    async def _emit_packages(self, repo: str, packages: dict[str, PKGInfo]):
        if not packages or not self.job_manager:
            return
        package_list = [
            {
                "slug": SLUG_MAP.get(norm, norm).lower(),
                "name": norm,
                "count": pkg.count,
                "dep_origin": pkg.dep_origin,
            }
            for norm, pkg in packages.items()
        ]
        await self.job_manager.emit("package.found", {
            "repo": repo,
            "packages": package_list,
        })




    async def fetch_all_user_repos(self) -> list[dict]:


        
        all_repos = []
        cursor = None
        has_next = True
        page = 0
        log.info("Fetching repos for user: %s (forks=%s, private=%s)", self.username, self.allow_fork, self.token_exists)
        total_so_far = 0 
        
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
            total_so_far += len(nodes)
            total_repos = len(nodes)*50
            if self.job_manager:
                await self.job_manager.emit("repo.page", {
                    "page": page,
                    "count": len(nodes),
                    "total_so_far": total_so_far,
                    "total_repos": total_repos
                })

        log.info("Found %d repos for %s", len(all_repos), self.username)
        self.repo_count = len(all_repos)
        if self.job_manager:
            await self.job_manager.emit("repo.listed",{
                "total":len(all_repos)
            })
        return all_repos



    async def fetch_repo_deps(self, repo: str, repo_sha: str = "",index:int=0):
        
        start = time.time() 

        if self.job_manager:
            await self.job_manager.emit("repo.scan.start",{
                "username":self.username,
                "repo":repo
            })
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
            await self._emit_packages(repo, pkg_dic)
            if self.job_manager:
                await self.job_manager.emit("repo.scan.done",{
                    "repo":repo,
                    "index":index,
                    "cache_hit":True,
                    "ms":time.time()-start,
                    "package_count":len(pkg_dic),
                })
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
            announced_slugs: set[str] = set()
            for manifest in manifests:
                raw_fname = manifest["filename"]
                fname = Path(raw_fname).name

                if fname in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "poetry.lock", "Pipfile.lock", "uv.lock", "Cargo.lock"):
                    continue

                before = len(pkg_dic)
                manifest_pkgs: dict[str, PKGInfo] = {}
                for dep in manifest["dependencies"]["nodes"]:
                    raw_dep = dep["packageName"]
                    norm_dep, lang = self.parser.normalize_pkg(raw_dep, raw_fname)
                    if norm_dep and lang:
                        pkg = pkg_dic[norm_dep]
                        pkg.count += 1
                        pkg.dep_origin = lang
                        pkg.raw_names.add(raw_dep)

                        delta = manifest_pkgs.get(norm_dep)
                        if delta is None:
                            manifest_pkgs[norm_dep] = PKGInfo(
                                count=1, dep_origin=lang, raw_names={raw_dep}
                            )
                        else:
                            delta.count += 1
                            delta.dep_origin = lang
                            delta.raw_names.add(raw_dep)

                if manifest_pkgs and self.job_manager:
                    await self._emit_packages(repo, manifest_pkgs)
                    announced_slugs.update(manifest_pkgs)

                extracted = len(pkg_dic) - before
                log.info("  │  %-30s → %d package(s) extracted", fname, extracted)
            if pkg_dic:
                log.info("  └─ total: %d unique packages", len(pkg_dic))
                remaining = {
                    norm: pkg for norm, pkg in pkg_dic.items()
                    if norm not in announced_slugs
                }
                await self._emit_packages(repo, remaining)
                if self.job_manager:
                    await self.job_manager.emit("repo.scan.done",{
                        "repo":repo,
                        "index":index,
                        "cache_hit":False,
                        "ms":time.time()-start,
                        "package_count":len(pkg_dic),
                    })
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
                try:
                    await asyncio.wait_for(proc.communicate(), timeout=25.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    log.warning("  │  git clone timed out for %s/%s — skipping clone", self.username, repo)
                    await self._emit_packages(repo, pkg_dic)
                    if self.job_manager:
                        await self.job_manager.emit("repo.scan.done",{
                            "repo":repo,
                            "index":index,
                            "cache_hit":False,
                            "ms":time.time()-start,
                            "package_count":len(pkg_dic),
                        })
                    return pkg_dic
                log.info("  │  clone done, scanning for: %s", TARGETS)

                root = Path(tmp_dir)
                ignore_parts = ("node_modules", ".venv", "venv", ".git", "target")
                for target in TARGETS:
                    found_files = [f for f in root.rglob(target) if not any(p in f.parts for p in ignore_parts)]
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
                        self._ingest_manifest_file(pkgfile, target, pkg_dic, root)

                # Scan GitHub Actions workflows
                wf_files = [
                    f for f in root.glob(".github/workflows/*.y*ml")
                    if f.is_file() and not any(p in f.parts for p in ignore_parts)
                ]
                if wf_files:
                    log.info("  │  found %d × workflow file(s)", len(wf_files))
                    for wffile in wf_files:
                        rel_path = str(wffile.relative_to(root))
                        self._ingest_manifest_file(wffile, rel_path, pkg_dic, root)

            except Exception as e:
                log.error("  │  clone failed for %s/%s: %s", self.username, repo, e)

        await self._emit_packages(repo, pkg_dic)
        if self.job_manager:
            await self.job_manager.emit("repo.scan.done",{
                "repo":repo,
                "index":index,
                "cache_hit":False,
                "ms":time.time()-start,
                "package_count":len(pkg_dic),
            })
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
        semp = asyncio.Semaphore(settings.max_concurrent_repo_scans)

        async def task(i: int, repo: dict):
            async with semp:
                log.info("[%d/%d] %s", i, len(repos), repo["name"])
                # Fetches a Single repo deps 
                defaultRef = repo.get("defaultBranchRef")
                if not defaultRef:
                    return None 
                target_sha = defaultRef.get("target", {}).get("oid", "")
                return await self.fetch_repo_deps(repo=repo["name"], repo_sha=target_sha,index=i)

        results = await asyncio.gather(*(task(i, repo) for i, repo in enumerate(repos, 1)))

        # Aggregate everything and Return 
        for r in results:
            if r:
                merge_pkg_dicts(pkg_dics, r)

        top_10 = sorted(pkg_dics.items(), key=lambda x: x[1].count, reverse=True)[:10]
        log.info("=" * 60)
        log.info("Done. %d unique packages found across all repos", len(pkg_dics))
        log.info("Top 10: %s", [(k, v.count) for k, v in top_10])
        log.info("=" * 60)

        if export_csv:
            if self.report_dir:
                if self.parser.can_records:
                    self.parser.export_filtered_csv(self.report_dir / "filtered.csv")
                if self.parser.unnormalized_records:
                    self.parser.export_unnormalized_csv(self.report_dir / "unnormalized.csv")

        return pkg_dics


