import asyncio
import base64
import logging
from typing import Optional, Union, Iterable
import httpx
from constants import PACKAGE_REGISTRY, SLUG_MAP, NORM
from models import PKG_MODELS, PKGInfo
from collections import Counter 

import re

log = logging.getLogger(__name__)


class ImageResolver:
    def __init__(self, timeout: float = 10.0, headers: Optional[dict] = None, github_token: Optional[str] = None):
        self.cache: dict[str, str] = {}
        client_headers = headers or {"User-Agent": "logo-ext/1.0"}
        self.client = httpx.AsyncClient(timeout=timeout, headers=client_headers)
        self.github_token = github_token
        self.favicon_url = "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128"
        self.github_avatar_url = "https://github.com/{owner}.png?size=128"
       
    @staticmethod
    def _to_data_uri(content: bytes, mime: str = "image/png") -> str:
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{mime};base64,{b64}"

    @staticmethod
    def _sanitize_svg(svg_text: str) -> str:
        """
        1. Strips hardcoded white background <rect> elements to eliminate bright box contrast.
        2. Inverts near-black fills to white (#ffffff) for visibility on dark backgrounds.
        3. Injects fill="#ffffff" if no fill is defined anywhere (preventing default black).
        """
        # Strip white background rects
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

        # Invert near-black fills
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

        # If no fill specified anywhere, inject fill="#ffffff" on <svg> tag
        if "fill=" not in svg_text and "fill:" not in svg_text:
            svg_text = re.sub(r'<svg\b([^>]*)>', r'<svg\1 fill="#ffffff">', svg_text, count=1, flags=re.IGNORECASE)

        return svg_text

    async def _fetch_image(self, url: str) -> Optional[str]:
        """Fetch image bytes and return as base64 data URI with SVG sanitization."""
        if url in self.cache:
            return self.cache[url]
        try:
            res = await self.client.get(url, follow_redirects=True)
            if res.status_code == 200 and len(res.content) > 0:
                ct = res.headers.get("content-type", "").lower()
                is_svg = "svg" in ct or res.content.strip().startswith(b"<svg")
                content = res.content
                if is_svg:
                    try:
                        text = content.decode("utf-8", errors="ignore")
                        sanitized = self._sanitize_svg(text)
                        content = sanitized.encode("utf-8")
                    except Exception as e:
                        log.debug("Failed sanitizing SVG from %s: %s", url, e)
                mime = "image/svg+xml" if is_svg else "image/png"
                data_uri = self._to_data_uri(content, mime)
                self.cache[url] = data_uri
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
        if cache_key in self.cache:
            return self.cache[cache_key] == "Organization"
        try:
            gh_headers = {"User-Agent": "logo-ext/1.0"}
            if self.github_token:
                gh_headers["Authorization"] = f"Bearer {self.github_token}"
            res = await self.client.get(f"https://api.github.com/users/{owner}", headers=gh_headers)
            if res.status_code == 200:
                account_type = res.json().get("type", "")
                self.cache[cache_key] = account_type
                return account_type == "Organization"
        except Exception as e:
            log.debug("Failed checking GitHub account type for %s: %s", owner, e)
        return False

    async def fetch_iconlib(self, slug: str) -> Optional[str]:
        """Tries distinct vector registries using auto-generated slug variations."""
        raw = slug.strip().lower().replace("_", "-")
        
        compact = raw.replace(" ", "").replace("-", "").replace(".", "dot")
        kebab = raw.replace(" ", "-").replace(".", "")

        candidate_urls = [
            # Tier 1: Devicon (True multi-color official SVGs)
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-original.svg",
            
            # Tier 2: SimpleIcons (Official brand hex colors, 3,300+ entries, square icon marks)
            f"https://cdn.simpleicons.org/{compact}",
            
            # Tier 3: Iconify Gilbarbara Logos (Single check)
            f"https://api.iconify.design/logos:{kebab}.svg",
            
            # Tier 4: Devicon plain
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-plain.svg",
        ]

        # Deduplicate while preserving order
        for url in dict.fromkeys(candidate_urls):
            icon = await self._fetch_image(url)
            if icon:
                log.info("✓ Icon hit for %r via %s", slug, url)
                return icon
                
        return None

    async def resolve_package(self, pkg_name: str, dep_origin: str) -> Optional[str]:
        """Resolves package to icon via registry (npm/pypi/maven) -> website favicon -> GitHub avatar."""
        if not dep_origin:
            return None

        reg_template = PACKAGE_REGISTRY.get(dep_origin)
        Model = PKG_MODELS.get(dep_origin)
        if not reg_template or not Model:
            return None

        data_json = await self._fetch_json(reg_template.format(pkg=pkg_name))
        if not data_json:
            return None

        try:
            links = Model.model_validate(data_json).extract_links()
            if links.custom_domain:
                icon = await self._fetch_image(self.favicon_url.format(domain=links.custom_domain))
                if icon:
                    log.info("✓ Icon hit for %r via website favicon (%s)", pkg_name, links.custom_domain)
                    return icon

            if links.github_owner:
                is_org = await self._is_github_org(links.github_owner)
                if is_org:
                    icon = await self._fetch_image(self.github_avatar_url.format(owner=links.github_owner))
                    if icon:
                        log.info("✓ Icon hit for %r via GitHub organization avatar (%s)", pkg_name, links.github_owner)
                        return icon
                else:
                    log.debug("Skipping avatar for %r: %s is a personal User account", pkg_name, links.github_owner)
        except Exception as e:
            log.debug("Failed parsing registry links for %r: %s", pkg_name, e)

        log.warning("✗ Missing icon for %r — no icon found across all sources", pkg_name)
        return None

    async def resolve(
        self, pkg_dic: Union[dict[str, Union[PKGInfo, int]], Iterable[tuple[str, Union[PKGInfo, int]]]]
    ) -> Counter:
        """
        Resolves all packages to data URI icons.
        Groups by canonical tool (slug) first so technologies never appear twice,
        and their total counts accumulate correctly.
        """
        items = list(pkg_dic.items()) if hasattr(pkg_dic, "items") else list(pkg_dic)

        # Flatten NORM dict for quick canonical lookup
        all_norm = {}
        for lang_map in NORM.values():
            all_norm.update({k.lower(): v for k, v in lang_map.items()})

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
        semp = asyncio.Semaphore(7)

        async def task(i: int, key: str, entry: dict):
            async with semp:
                norm_name = entry["norm_name"]
                count = entry["count"]
                dep_origin = entry["dep_origin"]
                raw_name = entry["raw_name"]
                log.info("[%d/%d] %s", i, total, norm_name)

                # 1. Check icon libraries first
                slug = SLUG_MAP.get(norm_name, norm_name)
                icon = await self.fetch_iconlib(slug)

                # 2. Fall back to package registry lookup
                if not icon and dep_origin:
                    icon = await self.resolve_package(raw_name, dep_origin)

                if icon:
                    if entry["val_ref"]:
                        entry["val_ref"].icon = icon
                    return (icon, count)
                log.warning("✗ Missing icon for %r — skipped from cloud", norm_name)
                await asyncio.sleep(0.2)
                return None

        results = await asyncio.gather(*(task(i, k, v) for i, (k, v) in enumerate(grouped.items(), 1)))

        icon_dic: Counter = Counter()
        for item in results:
            if item:
                icon, count = item
                icon_dic[icon] += count

        return icon_dic
        

    async def aclose(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()