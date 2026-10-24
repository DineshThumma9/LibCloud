import logging
from typing import Optional
from constants import PACKAGE_REGISTRY
from models import PKG_MODELS, ProjectLinks
from strategies.base import BaseStrategy

log = logging.getLogger(__name__)


class RegistryStrategy(BaseStrategy):
    async def get_links(self, pkg_name: str, dep_origin: str) -> Optional[ProjectLinks]:
        reg_template = PACKAGE_REGISTRY.get(dep_origin)
        Model = PKG_MODELS.get(dep_origin)
        if not reg_template or not Model:
            return None

        url = reg_template.format(pkg=pkg_name)
        data_json = await self._fetch_json(url)
        if data_json:
            try:
                return Model.model_validate(data_json).extract_links()
            except Exception as e:
                log.debug("Failed parsing registry links for %r: %s", pkg_name, e)
        return None
