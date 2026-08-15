from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Photo

router = APIRouter(prefix="/api/photos", tags=["photos"])


def _serialize(p: Photo) -> dict:
    return {
        "id": p.id,
        "filename": p.filename,
        "folder": p.folder,
        "media_type": p.media_type or "photo",
        "path": p.path,
        "width": p.width,
        "height": p.height,
        "size": p.size,
        "taken_at": p.taken_at.isoformat() if p.taken_at else None,
        "camera": f"{p.camera_make or ''} {p.camera_model or ''}".strip() or None,
        "gps_lat": p.gps_lat,
        "gps_lon": p.gps_lon,
        "location_name": p.location_name,
        "location_city": p.location_city,
        "location_country": p.location_country,
        "country_code": p.country_code,
        "thumbnail_cached": p.thumbnail_cached,
        "ai_tags": p.ai_tags,
        "face_count": p.face_count,
    }


@router.get("")
async def list_photos(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(60, le=200),
    offset: int = 0,
    folder: str | None = None,
    location: str | None = None,
    country: str | None = None,
    year: int | None = None,
    media: str = Query("all", pattern="^(all|photo|video)$"),
    sort: str = Query("taken_desc", pattern="^(taken_desc|taken_asc|name)$"),
):
    stmt = select(Photo)

    if folder:
        stmt = stmt.where(Photo.folder == folder)
    if location:
        stmt = stmt.where(Photo.location_city == location)
    if country:
        stmt = stmt.where(Photo.location_country == country)
    if year:
        stmt = stmt.where(func.strftime("%Y", Photo.taken_at) == str(year))
    if media != "all":
        stmt = stmt.where(Photo.media_type == media)

    if sort == "taken_desc":
        stmt = stmt.order_by(Photo.taken_at.is_(None), Photo.taken_at.desc())
    elif sort == "taken_asc":
        stmt = stmt.order_by(Photo.taken_at.asc())
    else:
        stmt = stmt.order_by(Photo.filename.asc())

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.limit(limit).offset(offset)
    rows = (await db.scalars(stmt)).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "photos": [_serialize(p) for p in rows],
    }


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(Photo.id)))
    with_gps = await db.scalar(
        select(func.count(Photo.id)).where(Photo.gps_lat.isnot(None))
    )
    with_location = await db.scalar(
        select(func.count(Photo.id)).where(Photo.location_name.isnot(None))
    )
    folders = await db.scalar(select(func.count(distinct(Photo.folder))))
    countries = (
        await db.scalars(
            select(distinct(Photo.location_country))
            .where(Photo.location_country.isnot(None))
            .order_by(Photo.location_country)
        )
    ).all()
    return {
        "total": total or 0,
        "with_gps": with_gps or 0,
        "with_location": with_location or 0,
        "folders": folders or 0,
        "countries": list(countries),
    }


@router.get("/locations")
async def locations(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(
                Photo.location_city,
                Photo.location_country,
                func.count(Photo.id).label("count"),
                func.avg(Photo.gps_lat).label("lat"),
                func.avg(Photo.gps_lon).label("lon"),
            )
            .where(Photo.location_city.isnot(None))
            .group_by(Photo.location_city, Photo.location_country)
            .order_by(func.count(Photo.id).desc())
        )
    ).all()
    return [
        {
            "city": r.location_city,
            "country": r.location_country,
            "count": r.count,
            "lat": r.lat,
            "lon": r.lon,
        }
        for r in rows
    ]


@router.get("/folders")
async def folders(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Photo.folder, func.count(Photo.id).label("count"))
            .group_by(Photo.folder)
            .order_by(Photo.folder)
        )
    ).all()
    return [{"folder": r.folder, "count": r.count} for r in rows]


@router.get("/years")
async def years(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(
                func.strftime("%Y", Photo.taken_at).label("year"),
                func.count(Photo.id).label("count"),
            )
            .where(Photo.taken_at.isnot(None))
            .group_by("year")
            .order_by("year")
        )
    ).all()
    return [{"year": r.year, "count": r.count} for r in rows if r.year]


@router.get("/{photo_id}")
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    p = await db.get(Photo, photo_id)
    if not p:
        raise HTTPException(404, "Foto no encontrada")
    return _serialize(p)
