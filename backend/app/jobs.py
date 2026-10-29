

from app.events import Event,EventBus 
import uuid 
import time 




class JobManager:

    def __init__(self):
        self.queue = EventBus(maxsize=2000)
        self.job_id = str(uuid.uuid4()) 
        self.seq = 0 
        

    async def emit(self,event_type,data):
        await self.queue.put(Event(
            job_id=self.job_id,
            type=event_type,
            seq=self.seq,
            ts=int(time.time()*1000),
            data=data 
        ))
        self.seq += 1
