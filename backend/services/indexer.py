import asyncio
import hashlib
from datetime import datetime
from pathlib import PurePosixPath
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import SessionLocal
from db.models import Photo, IndexJob
from services import nas_client, exif_extractor, geocoder
from config import settings

# In-memory status so the UI can poll progress without hammering the DB
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


async def _process_file(db: AsyncSession, entry: dict, geocode: bool) -> bool:
    """Returns True if a new photo was added."""
    path = entry["path"]

    existing = await db.scalar(select(Photo).where(Photo.path == path))
    if existing:
        return False

    photo = Photo(
        path=path,
        filename=entry["filename"],
        folder=entry["folder"],
        size=entry.get("size"),
    )

    # Videos: store the record but skip image-only processing
    is_video = entry.get("is_video", False)

    if not is_video:
        try:
            data = await nas_client.download_file(path)
            meta = exif_extractor.extract(data)

            photo.width = meta.get("width")
            photo.height = meta.get("height")
            photo.taken_at = meta.get("taken_at")
            photo.camera_make = meta.get("camera_make")
            photo.camera_model = meta.get("camera_model")
            photo.gps_lat = meta.get("gps_lat")
            photo.gps_lon = meta.get("gps_lon")
            photo.gps_alt = meta.get("gps_alt")

            # Thumbnail
            thumb = exif_extractor.make_thumbnail(data)
            if thumb:
                thumb_path = settings.thumbnail_path / _thumb_name(path)
                thumb_path.write_bytes(thumb)
                photo.thumbnail_cached = True

            # Reverse geocode (rate-limited to ~1/sec by geocoder)
            if geocode and photo.gps_lat is not None and photo.gps_lon is not None:
                loc = await geocoder.reverse_geocode(photo.gps_lat, photo.gps_lon)
                if loc:
                    photo.location_name = loc["location_name"]
                    photo.location_city = loc["location_city"]
                    photo.location_country = loc["location_country"]
        except Exception as e:
            _status["message"] = f"Error en {entry['filename']}: {e}"

    # Fallback date from filename patterns is skipped; NULL taken_at is fine
    db.add(photo)
    return True


async def run_index(geocode: bool = True):
    if _status["running"]:
        return

    _status.update({
        "running": True,
        "phase": "listing",
        "total": 0,
        "processed": 0,
        "new": 0,
        "current_file": "",
        "message": "Listando archivos del NAS...",
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
    })

    async with SessionLocal() as db:
        job = IndexJob(status="running")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        try:
            files = await nas_client.list_media_files()
            _status["total"] = len(files)
            _status["phase"] = "processing"
            _status["message"] = f"{len(files)} archivos encontrados"
            job.total_files = len(files)
            await db.commit()

            new_count = 0
            for i, entry in enumerate(files):
                _status["current_file"] = entry["filename"]
                _status["processed"] = i + 1
                added = await _process_file(db, entry, geocode)
                if added:
                    new_count += 1
                    _status["new"] = new_count
                # Commit periodically to keep memory low and persist progress
                if (i + 1) % 20 == 0:
                    await db.commit()
                    job.processed_files = i + 1
                    job.new_files = new_count
                    await db.commit()

            await db.commit()
            job.processed_files = len(files)
            job.new_files = new_count
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


def thumbnail_file(path: str):
    return settings.thumbnail_path / _thumb_name(path)
