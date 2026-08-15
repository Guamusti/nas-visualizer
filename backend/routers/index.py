import asyncio
from fastapi import APIRouter, Query
from services import indexer, nas_client

router = APIRouter(prefix="/api/index", tags=["index"])


@router.get("/status")
async def index_status():
    return indexer.get_status()


@router.post("/start")
async def start_index(
    geocode: bool = True,
    limit: int | None = Query(None, ge=1, le=1000),
):
    status = indexer.get_status()
    if status["running"]:
        return {"started": False, "message": "Ya hay una indexación en curso"}
    # Run in the event loop as a background task
    asyncio.create_task(indexer.run_index(geocode=geocode, limit=limit))
    message = f"Indexación de muestra iniciada ({limit} archivos)" if limit else "Indexación completa iniciada"
    return {"started": True, "message": message, "limit": limit}


@router.get("/connection")
async def connection_check():
    ok = await nas_client.check_connection()
    return {"connected": ok}
