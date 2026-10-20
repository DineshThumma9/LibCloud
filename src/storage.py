import logging
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

log = logging.getLogger(__name__)


class DepsDB:
    _shared_client: Optional[AsyncIOMotorClient] = None

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
        self._mem_icons: dict[str, str] = {}
        self._mem_repos: dict[str, dict] = {}
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

    async def save_icon(self, slug: str, icon_uri: str):
        key = slug.strip().lower()
        self._mem_icons[key] = icon_uri
        try:
            await self.icons.update_one(
                {"_id": key},
                {"$set": {"icon_uri": icon_uri}},
                upsert=True
            )
            log.info("💾 [Cache SAVED: MongoDB] Icon for %r", key)
        except Exception as e:
            self._warn_db(e)

    async def get_icon(self, slug: str) -> Optional[str]:
        key = slug.strip().lower()
        if key in self._mem_icons:
            log.info("⚡ [Cache HIT: Memory] Icon for %r", key)
            return self._mem_icons[key]
        try:
            doc = await self.icons.find_one({"_id": key}) 
            if doc:
                icon_uri = doc.get("icon_uri")
                if icon_uri:
                    self._mem_icons[key] = icon_uri
                    log.info("⚡ [Cache HIT: MongoDB] Icon for %r", key)
                    return icon_uri
        except Exception as e:
            self._warn_db(e)
        if key in self._mem_icons:
            log.info("⚡ [Cache HIT: Memory fallback] Icon for %r", key)
            return self._mem_icons[key]
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
            if mem and mem.get("repo_sha") == repo_sha:
                pkg_data = mem.get("pkg_dic")
                pkg_count = len(pkg_data) if isinstance(pkg_data, dict) else 0
                log.info("⚡ [Cache HIT: Memory fallback] Repo %s (sha: %s, %d packages)", user_repo_key, repo_sha[:8] if repo_sha else "none", pkg_count)
                return pkg_data
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
