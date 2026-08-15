import io
import mimetypes
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Photo
from services import nas_client, indexer, exif_extractor

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/thumb/{photo_id}")
async def thumbnail(photo_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Photo, photo_id)
    if not p:
        raise HTTPException(404, "Foto no encontrada")

    thumb_path = indexer.thumbnail_file(p.path)
    if thumb_path.exists():
        return Response(
            content=thumb_path.read_bytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    # Generate on demand if missing
    try:
        data = await nas_client.download_file(p.path)
        thumb = exif_extractor.make_thumbnail(data, p.filename)
        if thumb:
            thumb_path.write_bytes(thumb)
            p.thumbnail_cached = True
            await db.commit()
            return Response(content=thumb, media_type="image/jpeg")
    except Exception:
        pass
    raise HTTPException(404, "Miniatura no disponible")


@router.get("/full/{photo_id}")
async def full_image(photo_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Photo, photo_id)
    if not p:
        raise HTTPException(404, "Foto no encontrada")
    try:
        data = await nas_client.download_file(p.path)
        if p.media_type == "video":
            media_type = mimetypes.guess_type(p.filename)[0] or "video/mp4"
            return Response(
                content=data,
                media_type=media_type,
                headers={"Cache-Control": "private, max-age=3600", "Accept-Ranges": "bytes"},
            )
        # Serve a web-friendly version for HEIC/RAW so browsers can render it
        suffix = p.filename.lower().rsplit(".", 1)[-1] if "." in p.filename else ""
        raw_or_special = {"heic", "heif", "tiff", "tif", "raw", "cr2", "cr3",
                          "nef", "arw", "dng", "rw2", "orf", "raf", "pef", "srw"}
        if suffix in raw_or_special:
            web = exif_extractor.make_thumbnail(data, p.filename, size=(2048, 2048))
            if web:
                return Response(content=web, media_type="image/jpeg")
        media_type = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix or 'jpeg'}"
        return Response(content=data, media_type=media_type)
    except Exception as e:
        raise HTTPException(500, f"No se pudo cargar la imagen: {e}")
