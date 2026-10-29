"""Storage facade over the icon, repo, and share stores."""

from typing import Optional

from app.config import settings
from app.storage.icons import IconStore
from app.storage.mongo import get_client
from app.storage.repos import RepoStore
from app.storage.runs import RunStore
from app.storage.shares import ShareStore


class DepsDB:
    """Keeps the existing public cache API while delegating to focused stores."""

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        target_db = db_name or settings.mongo_db_name
        self.db_client = get_client(uri)
        self.db = self.db_client[target_db]
        self.icon_store = IconStore(self.db)
        self.repo_store = RepoStore(self.db)
        self.run_store = RunStore(self.db)
        self.share_store = ShareStore(self.db)

    async def save_icon(self, slug: str, icon_uri: str, source_url: str = ""):
        return await self.icon_store.save_icon(slug, icon_uri, source_url)

    async def get_icon(self, slug: str) -> Optional[str]:
        return await self.icon_store.get_icon(slug)

    async def get_icon_entry(self, slug: str) -> Optional[tuple[str, str]]:
        return await self.icon_store.get_icon_entry(slug)

    async def delete_icon(self, slug: str):
        return await self.icon_store.delete_icon(slug)

    async def get_repo_deps(self, username: str, repo: str, repo_sha: str):
        return await self.repo_store.get_repo_deps(username, repo, repo_sha)

    async def save_repo_deps(self, username: str, repo: str, repo_sha: str, pkg_dic: dict):
        return await self.repo_store.save_repo_deps(username, repo, repo_sha, pkg_dic)

    async def create_share(self, username: str, base64: str, svg_data: str, share_id: str):
        return await self.share_store.create_share(username, base64, svg_data, share_id)

    async def fetch_png(self, share_id: str):
        return await self.share_store.fetch_png(share_id)

    async def fetch_svg(self, share_id: str):
        return await self.share_store.fetch_svg(share_id)
