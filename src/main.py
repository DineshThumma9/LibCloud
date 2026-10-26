import logging
from typing import Optional
from fastapi import FastAPI, Response, Query
from api import fetch_all_repos_deps
from resolver import ImageResolver
from utils import transform_wordcloud
from fastapi.middleware.cors import CORSMiddleware
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="LibCloud")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
]
if settings.frontend_url:
    origins.append(settings.frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/framecloud")
async def framecloud(
    username: str,
    token: Optional[str] = None,
    preset: str = Query("web", description="Preset mode: 'web' (max space, 1400x900) or 'readme' (standard GitHub card, 920x540)"),
    width: Optional[int] = Query(None, description="Custom canvas width in pixels"),
    height: Optional[int] = Query(None, description="Custom canvas height in pixels"),
    min_size: Optional[int] = Query(None, description="Minimum logo size in pixels"),
    max_size: Optional[int] = Query(None, description="Maximum logo size in pixels"),
    padding: Optional[int] = Query(None, description="Padding between logos in pixels"),
    max_logos: Optional[int] = Query(None, description="Max logos to display (default: all)"),
    bg_color: Optional[str] = Query(None, description="Background hex color (defaults based on theme)"),
    theme: Optional[str] = Query(None, description="Theme: 'dark' (light logo plates) or 'light' (original logos)"),
):
    
    pkg_dic = await fetch_all_repos_deps(username, token)
    async with ImageResolver(github_token=token) as resolver:
        badge_dic = await resolver.resolve(pkg_dic)
    svg_content = transform_wordcloud(
        badge_dic,
        preset=preset,
        width=width,
        height=height,
        min_size=min_size,
        max_size=max_size,
        padding=padding,
        max_logos=max_logos,
        bg_color=bg_color,
        theme=theme,
    )
    return Response(content=svg_content, media_type="image/svg+xml")
