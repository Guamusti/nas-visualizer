import asyncio
from fastapi import APIRouter, BackgroundTasks
from services import indexer, nas_client

router = APIRouter(prefix="/api/index", tags=["index"])


@router.get("/status")
async def index_status():
    return indexer.get_status()


@router.post("/start")
async def start_index(background_tasks: BackgroundTasks, geocode: bool = True):
    status = indexer.get_status()
    if status["running"]:
        return {"started": False, "message": "Ya hay una indexación en curso"}
    # Run in the event loop as a background task
    asyncio.create_task(indexer.run_index(geocode=geocode))
    return {"started": True, "message": "Indexación iniciada"}


@router.get("/connection")
async def connection_check():
    ok = await nas_client.check_connection()
    return {"connected": ok}
