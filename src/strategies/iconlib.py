import logging
from typing import Optional
from strategies.base import BaseStrategy

log = logging.getLogger(__name__)


class IconLib(BaseStrategy):
    async def fetch_iconlib(self, slug: str) -> Optional[tuple[str, str]]:
        """Tries distinct vector registries using auto-generated slug variations. Returns (icon, source_url)."""
        if slug.startswith(("http://", "https://")):
            icon = await self._fetch_image(slug)
            if icon:
                log.info("✓ Icon hit for %r via direct URL", slug)
                return icon, slug

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
            f"https://cdn.simpleicons.org/{kebab}",

            # Tier 3: Iconify Logos (Gil Barbara vector marks)
            f"https://api.iconify.design/logos/{kebab}-icon.svg",
            f"https://api.iconify.design/logos/{kebab}.svg",
            f"https://api.iconify.design/logos/{compact}-icon.svg",
            f"https://api.iconify.design/logos/{compact}.svg",

            # Tier 4: Devicon plain
            f"https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/{compact}/{compact}-plain.svg",
        ]

        for url in dict.fromkeys(candidate_urls):
            icon = await self._fetch_image(url)
            if icon:
                log.info("✓ Icon hit for %r via %s", slug, url)
                return icon, url

        return None

    async def resolve(self, slug: str) -> Optional[tuple[str, str, str]]:
        res = await self.fetch_iconlib(slug)
        if res:
            icon, source_url = res
            return icon, "cdn_catalog", source_url
        return None
