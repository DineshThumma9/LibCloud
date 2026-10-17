import logging
from client import GraphGithubClient
from collections import defaultdict
import asyncio
import tempfile
import glob
import subprocess
from constants import TARGETS
from queries import REPO_DEP_QUERY, REPOS_QUERY
from parser import normalize_pkg, process
from models import PKGInfo
from pathlib import Path

log = logging.getLogger(__name__)



async def fetch_all_user_repos(ghc: GraphGithubClient, username: str, allow_fork: bool = False, token_exists: bool = False) -> list[dict]:
    all_repos = []
    cursor = None
    has_next = True
    page = 0

    log.info("Fetching repos for user: %s (forks=%s, private=%s)", username, allow_fork, token_exists)

    while has_next:
        page += 1
        payload = {
            "query": REPOS_QUERY,
            "variables": {"owner": username, "cursor": cursor},
        }
        user_data = await ghc.execute(variables=payload)
        if not user_data:
            log.warning("No data returned from GitHub API on page %d — stopping", page)
            break

        repos_container = user_data.get("user", {}).get("repositories", {})
        nodes = repos_container.get("nodes", [])

        for repo in nodes:
            name = repo.get("name", "?")
            if not allow_fork and repo.get("isFork"):
                log.debug("  skip %-40s (fork)", name)
                continue
            if repo["isPrivate"] and not token_exists:
                log.debug("  skip %-40s (private, no token)", name)
                continue
            log.debug("  + %-40s", name)
            all_repos.append(repo)

        page_info = repos_container.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

    log.info("Found %d repos for %s", len(all_repos), username)
    return all_repos


async def fetch_repo_deps(ghc: GraphGithubClient, username: str, repo: str, token: str = ""):
    pkg_dic = defaultdict(PKGInfo)
    log.info("  ┌─ %s/%s", username, repo)

    variables = {"owner": username, "repo": repo}
    dep_json = {"query": REPO_DEP_QUERY, "variables": variables}
    result = await ghc.execute(dep_json)

    manifests = (result or {}).get("repository", {}).get("dependencyGraphManifests", {}).get("nodes", [])

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
                norm_dep, lang = normalize_pkg(raw_dep, raw_fname)
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
        f"https://{token}@github.com/{username}/{repo}.git"
        if token
        else f"https://github.com/{username}/{repo}.git"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            log.info("  │  cloning %s/%s ...", username, repo)
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", auth_url, tmp_dir,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            log.info("  │  clone done, scanning for: %s", TARGETS)

            root = Path(tmp_dir)
            for target in TARGETS:
                found_files = list(root.rglob(target))
                if not found_files:
                    continue
                log.info("  │  found %d × %s", len(found_files), target)
                for pkgfile in found_files:
                    try:
                        before = len(pkg_dic)
                        try:
                            content = pkgfile.read_text(encoding="utf-8-sig")
                        except UnicodeDecodeError:
                            content = pkgfile.read_text(encoding="utf-16")
                        sub_dic = process(content, target)
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
            log.error("  │  clone failed for %s/%s: %s", username, repo, e)

    log.info("  └─ total: %d unique packages", len(pkg_dic))
    return pkg_dic


async def fetch_all_repos_deps(username: str, token: str):
    ghc = GraphGithubClient(token)
    repos = await fetch_all_user_repos(ghc, username, token_exists=bool(token))

    log.info("=" * 60)
    log.info("Scanning dependencies across %d repos for %s", len(repos), username)
    log.info("=" * 60)

    pkg_dics = defaultdict(PKGInfo)
    semp = asyncio.Semaphore(7)

    async def task(i: int, repo: dict):
        async with semp:
            log.info("[%d/%d] %s", i, len(repos), repo["name"])
            return await fetch_repo_deps(ghc=ghc, username=username, repo=repo["name"], token=token)

    results = await asyncio.gather(*(task(i, repo) for i, repo in enumerate(repos, 1)))
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
    return pkg_dics

