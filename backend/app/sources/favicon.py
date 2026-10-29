import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.sources.base import BaseStrategy

log = logging.getLogger(__name__)


class FaviconStrategy(BaseStrategy):
    favicon_url: str = "https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128"

    async def resolve_domain(self, domain: str, pkg_name: str = "") -> Optional[tuple[str, str, str]]:
        if not domain or "." not in domain:
            return None

        # 1. Probe domain homepage for high-res vector/SVG brand logo via BeautifulSoup
        try:
            r = await self.client.get(f"https://{domain}/", follow_redirects=True)
            if r.status_code == 200:
                html = r.text
                base_url = str(r.url)
                soup = BeautifulSoup(html, "html.parser")
                candidates: list[str] = []

                # Navbar / brand anchors
                for a in soup.find_all("a", class_=re.compile(r"navbar-brand|brand|logo", re.I)):
                    img = a.find("img")
                    if img:
                        src = img.get("src") or img.get("data-src")
                        if src:
                            candidates.append(urljoin(base_url, src))
                    svg = a.find("svg")
                    if svg:
                        data_uri = self.processor.to_data_uri(str(svg).encode("utf-8"), "image/svg+xml")
                        if data_uri:
                            log.info("✓ Brand logo hit for %r via inline SVG (%s)", pkg_name or domain, domain)
                            return data_uri, "homepage_favicon", base_url

                # Direct logo/brand images
                for img in soup.find_all("img"):
                    src = img.get("src") or img.get("data-src")
                    if not src:
                        continue
                    classes = " ".join(img.get("class", [])) if isinstance(img.get("class"), list) else str(img.get("class", ""))
                    img_id = img.get("id", "")
                    alt = img.get("alt", "")
                    text_meta = f"{src} {classes} {img_id} {alt}".lower()
                    if "logo" in text_meta or "brand" in text_meta:
                        candidates.append(urljoin(base_url, src))

                # Touch icons and standard favicons
                for link in soup.find_all("link", rel=True):
                    rels = link.get("rel", [])
                    rel_str = " ".join(rels).lower() if isinstance(rels, list) else str(rels).lower()
                    if "icon" in rel_str or "apple-touch-icon" in rel_str:
                        href = link.get("href")
                        if href:
                            candidates.append(urljoin(base_url, href))

                # Meta tags (og:image, twitter:image with logo/brand)
                for meta in soup.find_all("meta"):
                    prop = (meta.get("property") or meta.get("name") or "").lower()
                    if prop in ("og:image", "twitter:image"):
                        content = meta.get("content")
                        if content and any(w in content.lower() for w in ("logo", "brand", "icon")):
                            candidates.append(urljoin(base_url, content))

                # Sort candidates: SVGs first, then PNGs, then other formats
                def candidate_rank(u: str) -> int:
                    u_low = u.lower()
                    if ".svg" in u_low:
                        return 0
                    if any(w in u_low for w in ("logo", "brand")):
                        return 1
                    if "apple-touch-icon" in u_low:
                        return 2
                    return 3

                candidates.sort(key=candidate_rank)

                for url in dict.fromkeys(candidates):
                    icon = await self._fetch_image(url)
                    if icon:
                        log.info("✓ Brand logo hit for %r via %s (%s)", pkg_name or domain, domain, url)
                        return icon, "homepage_favicon", url
        except Exception as e:
            log.debug("Homepage extraction error for %s: %s", domain, e)

        # 2. Fall back to Google Favicon proxy
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
