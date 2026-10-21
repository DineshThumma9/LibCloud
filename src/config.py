import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings 
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    port: int = 8000
    host: str = "0.0.0.0"
    mongo_uri: Optional[str] = None
    mongo_db_name: str = "my_mongodb"

    max_concurrent_repo_scans:int = 5 
    max_concurrent_icon_resolves:int = 10
    request_delay_seconds:float = 0.05
    request_timeout_seconds:float = 10.0
    

    @field_validator("port", mode="before")
    @classmethod
    def parse_port(cls, v):
        if isinstance(v, str) and not v.strip():
            return 8000
        return v

    def get_mongo_uri(self) -> str:
        raw_uri = (self.mongo_uri or os.environ.get("MONGO_URI", "")).strip()
        if raw_uri.startswith(("mongodb://", "mongodb+srv://")):
            return raw_uri

        user = os.environ.get("MONGO_INITDB_ROOT_USERNAME", "").strip()
        pwd = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "").strip()
        host = os.environ.get("MONGO_HOST", "localhost").strip()
        port = os.environ.get("MONGO_PORT", "27017").strip()
        db = self.mongo_db_name

        if user and pwd:
            return f"mongodb://{user}:{pwd}@{host}:{port}/{db}?authSource=admin"
        return f"mongodb://{host}:{port}/{db}"

settings = Settings()
