import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import uuid 

log = logging.getLogger(__name__)


class DepsDB:
    _shared_client: Optional[AsyncIOMotorClient] = None
    MAX_MEM_SHARES = 200

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        mongo_uri = uri or settings.get_mongo_uri()
        target_db = db_name or settings.mongo_db_name

        if uri:
            self.db_client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
        else:
            if DepsDB._shared_client is None:
                DepsDB._shared_client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=2000)
            self.db_client = DepsDB._shared_client

        self.db = self.db_client[target_db]
        self.repo = self.db["repos"]
        self.icons = self.db["icons"]
        self.shares = self.db["shares"]
        self._mem_icons: dict[str, str] = {}
        self._mem_urls: dict[str, str] = {}
        self._mem_repos: dict[str, dict] = {}
        self._mem_shares: dict[str, dict] = {}
        self._db_warned = False

    def _warn_db(self, err: Exception):
        if not self._db_warned:
            log.warning("MongoDB unavailable (%s) — falling back to in-memory caching", err)
            self._db_warned = True

    async def clear_all(self):
        """Drops all collections in the database and clears in-memory caches."""
        self._mem_icons.clear()
        self._mem_repos.clear()
        try:
            await self.repo.drop()
            await self.icons.drop()
            log.info("Cleared all collections in %s", self.db.name)
        except Exception as e:
            self._warn_db(e)

    async def save_icon(self, slug: str, icon_uri: str, source_url: str = ""):
        key = slug.strip().lower()
        self._mem_icons[key] = icon_uri
        self._mem_urls[key] = source_url
        try:
            await self.icons.update_one(
                {"_id": key},
                {"$set": {"icon_uri": icon_uri, "source_url": source_url}},
                upsert=True
            )
            log.info("💾 [Cache SAVED: MongoDB] Icon for %r", key)
        except Exception as e:
            self._warn_db(e)

    async def get_icon(self, slug: str) -> Optional[str]:
        entry = await self.get_icon_entry(slug)
        return entry[0] if entry else None

    async def get_icon_entry(self, slug: str) -> Optional[tuple[str, str]]:
        key = slug.strip().lower()
        if key in self._mem_icons:
            log.info("⚡ [Cache HIT: Memory] Icon for %r", key)
            return self._mem_icons[key], self._mem_urls.get(key, "")
        try:
            doc = await self.icons.find_one({"_id": key}) 
            if doc:
                icon_uri = doc.get("icon_uri")
                source_url = doc.get("source_url", "")
                if icon_uri:
                    self._mem_icons[key] = icon_uri
                    self._mem_urls[key] = source_url
                    log.info("⚡ [Cache HIT: MongoDB] Icon for %r", key)
                    return icon_uri, source_url
        except Exception as e:
            self._warn_db(e)
        return None

    async def get_repo_deps(self, username: str, repo: str, repo_sha: str):
        user_repo_key = f"{username}_{repo}"
        mem = self._mem_repos.get(user_repo_key)
        if mem and mem.get("repo_sha") == repo_sha:
            pkg_data = mem.get("pkg_dic")
            pkg_count = len(pkg_data) if isinstance(pkg_data, dict) else 0
            log.info("⚡ [Cache HIT: Memory] Repo %s (sha: %s, %d packages)", user_repo_key, repo_sha[:8] if repo_sha else "none", pkg_count)
            return pkg_data

        try:
            doc = await self.repo.find_one({"user_repo": user_repo_key})
            if doc and doc.get("repo_sha") == repo_sha:
                pkg_data = doc.get("pkg_dic")
                self._mem_repos[user_repo_key] = doc
                pkg_count = len(pkg_data) if isinstance(pkg_data, dict) else 0
                log.info("⚡ [Cache HIT: MongoDB] Repo %s (sha: %s, %d packages)", user_repo_key, repo_sha[:8] if repo_sha else "none", pkg_count)
                return pkg_data
        except Exception as e:
            self._warn_db(e)
        return None 

    async def save_repo_deps(self, username: str, repo: str, repo_sha: str, pkg_dic: dict):
        user_repo_key = f"{username}_{repo}"
        serializable_pkg_dic = {
            k: {"count": v.count, "dep_origin": v.dep_origin, "raw_names": list(v.raw_names)}
            for k, v in pkg_dic.items()
        }
        self._mem_repos[user_repo_key] = {
            "pkg_dic": serializable_pkg_dic,
            "repo_sha": repo_sha
        }
        try:
            fil_query = {"user_repo": user_repo_key}
            update_data = {
                "$set": {
                    "pkg_dic": serializable_pkg_dic,
                    "repo_sha": repo_sha
                }
            }
            await self.repo.update_one(fil_query, update_data, upsert=True)
            log.info("💾 [Cache SAVED: MongoDB] Repo %s (%d packages, sha: %s)", user_repo_key, len(pkg_dic), repo_sha[:8] if repo_sha else "none")
        except Exception as e:
            self._warn_db(e)
        return pkg_dic
    
    def _remember_share(self, share_id: str, doc: dict) -> dict:
        """Store a share in the bounded in-memory LRU cache."""
        self._mem_shares.pop(share_id, None)
        self._mem_shares[share_id] = doc
        while len(self._mem_shares) > self.MAX_MEM_SHARES:
            self._mem_shares.pop(next(iter(self._mem_shares)), None)
        return doc

    async def create_share(self, username: str, base64: str, svg_data: str, share_id: str):
        doc = {
            "username": username,
            "png_base64": base64,
            "share_id": share_id,
            "svg_data": svg_data
        }
        self._remember_share(share_id, doc)
        try:
            await self.shares.update_one(
                {"share_id": share_id},
                {"$set": doc},
                upsert=True
            )
        except Exception as e:
            self._warn_db(e)
        return share_id

    async def fetch_png(self, share_id: str):
        if share_id in self._mem_shares:
            return self._remember_share(share_id, self._mem_shares[share_id]).get("png_base64")
        try:
            obj = await self.shares.find_one({"share_id": share_id})
            if obj:
                self._remember_share(share_id, obj)
                return obj.get("png_base64")
        except Exception as e:
            self._warn_db(e)
        return None

    async def fetch_svg(self, share_id: str):
        if share_id in self._mem_shares:
            return self._remember_share(share_id, self._mem_shares[share_id]).get("svg_data")
        try:
            obj = await self.shares.find_one({"share_id": share_id})
            if obj:
                self._remember_share(share_id, obj)
                return obj.get("svg_data")
        except Exception as e:
            self._warn_db(e)
        return None
        


