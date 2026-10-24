import logging
from typing import Optional
from urllib.parse import urljoin, urlparse
from strategies.base import BaseStrategy

log = logging.getLogger(__name__)


class FaviconStrategy(BaseStrategy):
    favicon_url: str = "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128"

    async def resolve_domain(self, domain: str, pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        if not domain or "." not in domain:
            return None
        fav_url = self.favicon_url.format(domain=domain)
        icon = await self._fetch_image(fav_url)
        if icon:
            log.info("✓ Icon hit for %r via website favicon (%s)", pkg_name or domain, domain)
            return icon, "homepage_favicon", fav_url
        return None

    async def resolve_homepage(self, homepage: str, repo: str = "", pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        if not homepage:
            return None

        clean_repo = repo.lower().replace("-", "").replace("_", "") if repo else ""
        candidate_urls = []
        if repo:
            candidate_urls.extend([
                urljoin(homepage, f"/img/{repo}.svg"),
                urljoin(homepage, f"/img/{clean_repo}.svg"),
            ])
        candidate_urls.extend([
            urljoin(homepage, "/favicon.svg"),
            urljoin(homepage, "/logo.svg"),
            urljoin(homepage, "/favicon.png"),
            urljoin(homepage, "/logo.png"),
            urljoin(homepage, "/favicon.ico"),
        ])
        domain = urlparse(homepage).netloc
        if domain:
            candidate_urls.append(self.favicon_url.format(domain=domain))

        for url in dict.fromkeys(candidate_urls):
            icon = await self._fetch_image(url)
            if icon:
                log.info("✓ Icon hit for %r via homepage (%s)", pkg_name or repo or homepage, url)
                return icon, "homepage_favicon", url

        return None
