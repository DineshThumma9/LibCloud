from motor.motor_asyncio import AsyncIOMotorDatabase

from app.storage.base import BaseStore


class ShareStore(BaseStore):
    MAX_MEM_SHARES = 200

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db)
        self.collection = db["shares"]
        self._mem_shares: dict[str, dict] = {}

    def _remember(self, share_id: str, doc: dict) -> dict:
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
            "svg_data": svg_data,
        }
        self._remember(share_id, doc)
        try:
            await self.collection.update_one(
                {"share_id": share_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            self._warn_db(e)
        return share_id

    async def fetch_png(self, share_id: str):
        if share_id in self._mem_shares:
            return self._remember(share_id, self._mem_shares[share_id]).get("png_base64")
        try:
            obj = await self.collection.find_one({"share_id": share_id})
            if obj:
                self._remember(share_id, obj)
                return obj.get("png_base64")
        except Exception as e:
            self._warn_db(e)
        return None

    async def fetch_svg(self, share_id: str):
        if share_id in self._mem_shares:
            return self._remember(share_id, self._mem_shares[share_id]).get("svg_data")
        try:
            obj = await self.collection.find_one({"share_id": share_id})
            if obj:
                self._remember(share_id, obj)
                return obj.get("svg_data")
        except Exception as e:
            self._warn_db(e)
        return None
