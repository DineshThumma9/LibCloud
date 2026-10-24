import logging
from typing import Optional
import httpx
from processor import ImageProcessor

log = logging.getLogger(__name__)


class BaseStrategy:
    def __init__(
        self,
        client: httpx.AsyncClient,
        processor: ImageProcessor,
        url_cache: Optional[dict[str, str]] = None,
    ):
        self.client = client
        self.processor = processor
        self.url_cache = url_cache if url_cache is not None else {}

    async def _fetch_image(self, url: str) -> Optional[str]:
        """Fetch image bytes and return as base64 data URI via ImageProcessor with URL caching."""
        if url in self.url_cache:
            log.info("⚡ [Cache HIT: Image URL] %s", url)
            return self.url_cache[url]
        try:
            res = await self.client.get(url, follow_redirects=True)
            if res.status_code == 200 and len(res.content) > 0:
                ct = res.headers.get("content-type", "").lower()
                data_uri = self.processor.to_data_uri(res.content, mime=ct, source=url)
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
