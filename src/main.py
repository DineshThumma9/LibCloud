import logging
from typing import Optional
from fastapi import FastAPI
from api import fetch_all_repos_deps
from resolver import ImageResolver
from utils import transform_wordcloud

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI()


@app.get("/framecloud")
async def func(username: str, token: Optional[str] = None):
    pkg_dic = await fetch_all_repos_deps(username, token)
    async with ImageResolver(github_token=token) as resolver:
        badge_dic = await resolver.resolve(pkg_dic)
    return transform_wordcloud(badge_dic)
