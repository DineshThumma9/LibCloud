import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.storage.base import BaseStore

log = logging.getLogger(__name__)


class RepoStore(BaseStore):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)
        self.collection = db["repos"]
        self._mem_repos: dict[str, dict] = {}

    async def get_repo_deps(self, username: str, repo: str, repo_sha: str):
        user_repo_key = f"{username}_{repo}"
        mem = self._mem_repos.get(user_repo_key)
        if mem and mem.get("repo_sha") == repo_sha:
            pkg_data = mem.get("pkg_dic")
            pkg_count = len(pkg_data) if isinstance(pkg_data, dict) else 0
            log.info("⚡ [Cache HIT: Memory] Repo %s (sha: %s, %d packages)", user_repo_key, repo_sha[:8] if repo_sha else "none", pkg_count)
            return pkg_data

        try:
            doc = await self.collection.find_one({"user_repo": user_repo_key})
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
            "repo_sha": repo_sha,
        }
        try:
            await self.collection.update_one(
                {"user_repo": user_repo_key},
                {"$set": {"pkg_dic": serializable_pkg_dic, "repo_sha": repo_sha}},
                upsert=True,
            )
            log.info("💾 [Cache SAVED: MongoDB] Repo %s (%d packages, sha: %s)", user_repo_key, len(pkg_dic), repo_sha[:8] if repo_sha else "none")
        except Exception as e:
            self._warn_db(e)
        return pkg_dic

    async def clear(self):
        self._mem_repos.clear()
        try:
            await self.collection.drop()
        except Exception as e:
            self._warn_db(e)
