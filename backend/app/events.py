



from asyncio import QueueEmpty
from pydantic import Field
from pydantic import BaseModel
from fastapi.sse import EventSourceResponse,ServerSentEvent
from typing import Any
from fastapi.requests import Request
from typing import List ,Optional
import asyncio 
from asyncio import Task,Queue
import time




class JobAccepted(BaseModel):
    username:str 
    params:str
    job_taken:str 
    run_id:str = ""


class RepoPage(BaseModel):
    page:int
    count:int 
    total_so_far:int 

class RepoListed(BaseModel):
    total:int 

class RepoScanStart(BaseModel):
    repo:str 
    index:int = 0
    total:int = 0

class RepoScanDone(BaseModel):
    repo:str
    index:int 
    cache_hit:bool 
    ms:str 
    package_count:int 



class IconAttempted(BaseModel):
    slug:str 
    name:str 
    strategy:str 
    candidate:Optional[str]
    result:Optional[str]
    reason:Optional[str]
                                                                                                                                                                        
class IconResolved(BaseModel):                                                                                                                                             
    slug: str                                                                                                                                                              
    name: str                                                                                                                                                              
    strategy: Optional[str] = None                                                                                                                                         
    id: Optional[str] = ""                                                                                                                                                 
    method: Optional[str] = ""                                                                                                                                             
    source: Optional[str] = ""                                                                                                                                             
    icon: Optional[str] = ""                                                                                                                                               
    icon_meta: Optional[str] = ""  
    
class PackageFound(BaseModel):
    repo:str 
    packages:List[dict]
    new_slugs:int = 0
    total_unknown:int = 0 
     


class IconFailed(BaseModel):
    slug:str 
    name:str 
    tried:Optional[str] = "" 
    reason:str 

class Progress(BaseModel):
    phase:str 
    done:int = Field(default=0)
    total:str = Field(default=0)

class Warning(BaseModel):
    code:str 
    message:str 
    repo:Optional[str]

class Done(BaseModel):
    job_id:str 
    scene_url:str 
    stats:str 
    run_id:str = ""

class Error(BaseModel):
    phase:str 
    message:str 
    retryable:str 
    run_id:str = ""


class Event(BaseModel):
    job_id:str 
    type:str
    ts:float 
    seq:int 
    data:Any


async def stream_events(queue:Queue,job_task:Task,request:Request):



    try:

        while True:

            if await request.is_disconnected():
                job_task.cancel()
                break 
            
            event = await queue.get()

            yield f"data: {event.model_dump_json()}\n\n"

            
            if event.type and event.type in ("done","error"):
                break 
            

    except Exception as e:
        yield f"data: {Event(job_id='', type='error', ts=time.time(), seq=0, data=Error(phase='stream_error', message=str(e), retryable='false')).model_dump_json()}\n\n"
    finally:
        job_task.cancel()


    


class EventBus:


    def __init__(self,maxsize:int=2000):
        self.queue = Queue(maxsize=maxsize)
        
    async def get(self):
        return await self.queue.get() 

    async def put(self,item):
        return await self.queue.put(item)

