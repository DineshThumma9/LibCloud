from httpx import head
from events import stream_events
from fastapi.responses import StreamingResponse
from jobs import JobManager
import logging
from typing import Optional
from fastapi import FastAPI, Response, Query
from resolver import ImageResolver
from utils import transform_wordcloud
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from fastapi.requests import Request 
import asyncio

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

from apis import router as api_router
app.include_router(api_router)

from api import GraphGithubAPI




async def run_pipeline(job_manager:JobManager,username:str,token:str=None):
    try:
        await job_manager.emit("job.accepted",{
            "username":username,
             "params":"",
             "job_taken":job_manager.job_id
        })

        api = GraphGithubAPI(username=username,token=token,job_manager=job_manager)
        pkg_dic = await api.fetch_all_repos_deps()


        async with ImageResolver(github_token=token,job_manager=job_manager) as resolver:
            await resolver.resolve(pkg_dic)

        await job_manager.emit("done",{
            "job_id":job_manager.job_id,
            "scene_url":"",
            "stats":""
        })
    except Exception as e:
        await job_manager.emit("error",{
            "phase":"pipeline",
            "message":str(e),
            "retryable":"true"
        })
        

@app.api_route("/framecloud/stream", methods=["GET", "POST"])
@app.api_route("/framecloud", methods=["GET", "POST"])
@app.api_route("/libcloud", methods=["GET", "POST"])
async def libcloud(
    username: str,
    request:Request,

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


    job_manager = JobManager()
    
    job_tsk = asyncio.create_task(run_pipeline(job_manager,username,token))
    
    return StreamingResponse(
        stream_events(job_manager.queue,job_tsk,request),
        headers = {
            "Cache-Control":"no-cache",
            "Connection":"keep-alive",
            "X-Accel-Buffering":"no"
        },

        media_type="text/event-stream"
    )
