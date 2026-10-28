import strategies
from jobs import JobManager
import asyncio
import logging
from collections import Counter
from typing import Iterable, Optional, Union

import httpx

from client import GraphGithubClient
from config import settings
from constants import ALL_NOISE, HOSTING_BLOCKLIST, NORM, SLUG_MAP
from models import PKGInfo, ProjectLinks
from ops_logger import DepOpsLogger
from processor import ImageProcessor
from storage import DepsDB
from strategies import (
    DBCache,
    FaviconStrategy,
    HeuristicStrategy,
    IconLib,
    RegistryStrategy,
)

log = logging.getLogger(__name__)

# Flatten normalized package maps for quick canonical lookup
all_norm: dict[str, str] = {}
for lang_map in NORM.values():
    all_norm.update({k.lower(): v for k, v in lang_map.items()})


class ImageResolver:
    def __init__(
        self,
        timeout: float = settings.request_timeout_seconds,
        headers: Optional[dict] = None,
        github_token: Optional[str] = None,
        cache: Optional[DepsDB] = None,
        job_manager:Optional[JobManager] = None 
    ):
        self.cache = cache or DepsDB()
        self.url_cache: dict[str, str] = {}
        self.failed_icons: list[dict] = []
        self._seen_failed: set[str] = set()

        # Telemetry & metrics ledgers
        self.recovery_stats = Counter()
        self.resolved_methods: dict[str, str] = {}
        self.resolved_urls: dict[str, str] = {}
        self.exporter = DepOpsLogger()

        client_headers = headers or {"User-Agent": "logo-ext/1.0"}
        self.client = httpx.AsyncClient(timeout=timeout, headers=client_headers)
        self.github_token = github_token
        self.ghc = GraphGithubClient(token=github_token)

        # Image processing & validation
        self.processor = ImageProcessor()
        self.job_manager = job_manager
        # Resolution strategies
        self.db_cache = DBCache(cache=self.cache, processor=self.processor)
        self.iconlib = IconLib(self.client, self.processor, self.url_cache)
        self.registry = RegistryStrategy(self.client, self.processor, self.url_cache)
        self.github = HeuristicStrategy(self.client, self.processor, github_token, self.url_cache, self.ghc)
        self.favicon = FaviconStrategy(self.client, self.processor, self.url_cache)

    @property
    def validation_failures(self) -> list[dict]:
        return self.processor.validation_failures

    async def resolve_package(self, pkg_name: str, dep_origin: str, norm_name: str) -> Optional[tuple[str, str, str]]:
        """Resolves package to icon via registry -> website favicon -> GitHub heuristic -> GitHub avatar."""
        if not dep_origin:
            return None

        # Check DB cache first
        slug = SLUG_MAP.get(norm_name, norm_name).lower()
        cached = await self.db_cache.resolve(slug)
        if cached:
            if self.job_manager:
                await self.job_manager.emit("icon.resolved",{
                    "slug":slug,
                    "strategy":"cached",
                    "method":cached[1],
                    "icon":cached[0],
                    "source":cached[2] or "",
                    "name":norm_name 
                })
            return cached

        # Direct GitHub Actions repository probe
        if dep_origin == "actions":
            if "/" in pkg_name:
                parts = pkg_name.split("/")
                owner = parts[0]
                repo = parts[1].split("@")[0]
                res_h = await self.github.resolve(owner, repo, pkg_name)
                if res_h:
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved",{
                            "slug":slug,
                            "strategy":"github",
                            "method":res_h[1],
                            "icon":res_h[0],
                            "source":res_h[2] or "",
                            "name":norm_name 
                        })
                    return res_h
                
                avatar = await self.github.resolve_avatar(owner, pkg_name)
                if avatar:
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved",{
                            "slug":slug,
                            "strategy":"github_avatar",
                            "method":avatar[1],
                            "icon":avatar[0],
                            "source":avatar[2] or "",
                            "name":norm_name 
                        })
                    return avatar
            return None

        # Direct Go module repository probe
        if dep_origin == "go":
            if pkg_name.startswith("github.com/"):
                parts = [p for p in pkg_name.split("/") if p]
                if len(parts) >= 3:
                    owner, repo = parts[1], parts[2]
                    res_h = await self.github.resolve(owner, repo, pkg_name)
                    if res_h:
                        if self.job_manager:
                            await self.job_manager.emit("icon.resolved",{
                                "slug":slug,
                                "strategy":"github",
                                "method":res_h[1],
                                "icon":res_h[0],
                                "source":res_h[2] or "",
                                "name":norm_name 
                            })
                        return res_h
            elif "/" in pkg_name:
                parts = [p for p in pkg_name.split("/") if p]
                domain = parts[0]
                if domain not in HOSTING_BLOCKLIST and "." in domain:
                    res_fav = await self.favicon.resolve_domain(domain, pkg_name)
                    if res_fav:
                        if self.job_manager:
                            await self.job_manager.emit("icon.resolved",{
                                "slug":slug,
                                "strategy":"favicon",
                                "method":res_fav[1],
                                "icon":res_fav[0],
                                "source":res_fav[2] or "",
                                "name":norm_name 
                            })
                        return res_fav

        # Registry lookup (PyPI, npm, Maven, Cargo, RubyGems)
        links = await self.registry.get_links(pkg_name, dep_origin)
        if not links:
            links = ProjectLinks()

        # Search fallback if registry metadata had missing/placeholder URLs
        if not (links.github_owner and links.github_repo):
            search_match = await self.github.search_repo(pkg_name)
            if search_match:
                owner, repo, custom_domain = search_match
                links.github_owner = owner
                links.github_repo = repo
                if not links.custom_domain and custom_domain:
                    links.custom_domain = custom_domain

        try:
            # 1. GitHub heuristic (GraphQL OpenGraph, root SVG probes, Git Tree scan)
            if links.github_owner and links.github_repo:
                res_h = await self.github.resolve(links.github_owner, links.github_repo, pkg_name)
                if res_h:
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved",{
                            "slug":slug,
                            "strategy":"github",
                            "method":res_h[1],
                            "icon":res_h[0],
                            "source":res_h[2] or "",
                            "name":norm_name 
                        })
                    return res_h

            # 2. Custom domain favicon fallback
            if links.custom_domain:
                res_fav = await self.favicon.resolve_domain(links.custom_domain, pkg_name)
                if res_fav:
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved",{
                            "slug":slug,
                            "strategy":"favicon",
                            "method":res_fav[1],
                            "icon":res_fav[0],
                            "source":res_fav[2] or "",
                            "name":norm_name 
                        })                    
                    return res_fav

            # 3. GitHub organization avatar
            if links.github_owner:
                res_av = await self.github.resolve_avatar(links.github_owner, pkg_name)
                if res_av:
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved",{
                            "slug":slug,
                            "strategy":"github_avatar",
                            "method":res_av[1],
                            "icon":res_av[0],
                            "source":res_av[2] or "",
                            "name":norm_name 
                        })
                    return res_av

        except Exception as e:
            if self.job_manager:
                await self.job_manager.emit("icon.failed",{
                    "slug":slug,
                    "name":norm_name ,
                    "reason":str(e)  
                })  
            log.debug("Failed resolving icon links for %r: %s", pkg_name, e)

        log.warning("✗ Missing icon for %r — no icon found across all sources", pkg_name)
        if self.job_manager:
            await self.job_manager.emit("icon.failed",{
                "slug":slug,
                "name":norm_name ,
                "reason":"no icon found across all sources"  
            })  
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

            if canonical_name.lower() in ALL_NOISE or raw_name.lower() in ALL_NOISE or key in ALL_NOISE:
                continue

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
                cached = await self.db_cache.resolve(slug)
                if cached:
                    cached_icon, method, cached_url = cached
                    self.recovery_stats[method] += 1
                    self.resolved_methods[norm_name] = method
                    self.resolved_urls[norm_name] = cached_url or method
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved", {
                            "slug": slug,
                            "name": norm_name,
                            "strategy": method,
                            "icon": cached_icon,
                            "source": cached_url or ""
                        })
                    return (norm_name, cached_icon, count)

                # 1. Check icon libraries first (Devicon, SimpleIcons, Iconify)
                res_cdn = await self.iconlib.resolve(slug)
                if res_cdn:
                    icon, method, source_url = res_cdn
                    self.recovery_stats[method] += 1
                    self.resolved_methods[norm_name] = method
                    self.resolved_urls[norm_name] = source_url
                    await self.cache.save_icon(slug, icon, source_url=source_url)
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved", {
                            "slug": slug,
                            "name": norm_name,
                            "strategy": method,
                            "icon": icon,
                            "source": source_url
                        })
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
                    if self.job_manager:
                        await self.job_manager.emit("icon.resolved", {
                            "slug": slug,
                            "name": norm_name,
                            "strategy": method,
                            "icon": icon,
                            "source": source_url
                        })
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
                if self.job_manager:
                    await self.job_manager.emit("icon.failed", {
                        "slug": slug,
                        "name": norm_name,
                        "reason": "no_icon_found"
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
