import asyncio
import hashlib
from datetime import datetime
from sqlalchemy import select
from db.database import SessionLocal
from db.models import Photo, IndexJob
from services import nas_client, exif_extractor, geocoder
from config import settings

CONCURRENCY = 6   # files processed in parallel
CHUNK = 30        # DB commit batch size

_status = {
    "running": False,
    "phase": "idle",       # idle | listing | processing | done | error
    "total": 0,
    "processed": 0,
    "new": 0,
    "current_file": "",
    "message": "",
    "started_at": None,
    "finished_at": None,
}


def get_status() -> dict:
    return dict(_status)


def _thumb_name(path: str) -> str:
    return hashlib.sha1(path.encode("utf-8")).hexdigest() + ".jpg"


def thumbnail_file(path: str):
    return settings.thumbnail_path / _thumb_name(path)


def _process_sync(entry: dict) -> dict:
    """Runs in a worker thread: download + EXIF + thumbnail. No DB, no geocode."""
    path = entry["path"]
    fields: dict = {
        "path": path,
        "filename": entry["filename"],
        "folder": entry["folder"],
        "media_type": "video" if entry.get("is_video") else "photo",
        "size": entry.get("size"),
    }

    if entry.get("is_video"):
        return fields  # videos are catalogued but not downloaded/thumbnailed here

    try:
        data = nas_client.download_sync(path)
    except Exception as e:
        fields["_error"] = f"download: {e}"
        return fields

    try:
        meta = exif_extractor.extract(data, entry["filename"])
        fields.update({k: meta.get(k) for k in
                       ("taken_at", "camera_make", "camera_model",
                        "gps_lat", "gps_lon", "gps_alt", "width", "height")})

        dims = exif_extractor.dimensions_of(data, entry["filename"])
        if dims:
            fields["width"], fields["height"] = dims

        thumb = exif_extractor.make_thumbnail(data, entry["filename"])
        if thumb:
            thumbnail_file(path).write_bytes(thumb)
            fields["thumbnail_cached"] = True
    except Exception as e:
        fields["_error"] = f"process: {e}"

    return fields


async def _prepare(entry: dict, geocode: bool, sem: asyncio.Semaphore) -> dict:
    async with sem:
        loop = asyncio.get_event_loop()
        fields = await loop.run_in_executor(None, _process_sync, entry)
        _status["current_file"] = entry["filename"]
        _status["processed"] += 1

        if geocode and fields.get("gps_lat") is not None and fields.get("gps_lon") is not None:
            loc = await geocoder.reverse_geocode(fields["gps_lat"], fields["gps_lon"])
            if loc:
                fields["location_name"] = loc["location_name"]
                fields["location_city"] = loc["location_city"]
                fields["location_country"] = loc["location_country"]
                fields["country_code"] = loc.get("country_code")
        return fields


def _to_photo(fields: dict) -> Photo:
    fields.pop("_error", None)
    return Photo(**fields)


async def run_index(geocode: bool = True):
    if _status["running"]:
        return

    _status.update({
        "running": True, "phase": "listing", "total": 0, "processed": 0,
        "new": 0, "current_file": "", "message": "Listando archivos del NAS...",
        "started_at": datetime.utcnow().isoformat(), "finished_at": None,
    })

    async with SessionLocal() as db:
        job = IndexJob(status="running")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        try:
            files = await nas_client.list_media_files()

            # Skip already-indexed files (one query, not one per file)
            existing = set((await db.scalars(select(Photo.path))).all())
            todo = [f for f in files if f["path"] not in existing]

            _status["total"] = len(todo)
            _status["phase"] = "processing"
            _status["message"] = (
                f"{len(files)} archivos · {len(existing)} ya indexados · "
                f"{len(todo)} nuevos por procesar"
            )
            job.total_files = len(files)
            await db.commit()

            sem = asyncio.Semaphore(CONCURRENCY)
            new_count = 0

            for i in range(0, len(todo), CHUNK):
                chunk = todo[i:i + CHUNK]
                results = await asyncio.gather(
                    *(_prepare(e, geocode, sem) for e in chunk)
                )
                for fields in results:
                    db.add(_to_photo(fields))
                    new_count += 1
                _status["new"] = new_count
                await db.commit()
                job.processed_files = min(i + CHUNK, len(todo))
                job.new_files = new_count
                await db.commit()

            job.status = "done"
            job.finished_at = datetime.utcnow()
            await db.commit()

            _status.update({
                "phase": "done",
                "message": f"Indexación completa: {new_count} nuevas de {len(files)} archivos",
                "finished_at": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            job.status = "error"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            await db.commit()
            _status.update({
                "phase": "error",
                "message": f"Error: {e}",
                "finished_at": datetime.utcnow().isoformat(),
            })
        finally:
            _status["running"] = False
