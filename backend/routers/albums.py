from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import Photo, FolderCountry

router = APIRouter(prefix="/api/albums", tags=["albums"])


def _folder_leaf(folder: str) -> str:
    return folder.rstrip("/").split("/")[-1] or folder


@router.get("")
async def list_albums(
    db: AsyncSession = Depends(get_db),
    by: str = Query("auto", pattern="^(auto|country|folder)$"),
):
    """
    Returns album cards. Each album = a country (when photos have a country,
    via GPS or a manual folder tag) or a folder. Includes a cover photo id and
    a country_code for the flag.
    """
    has_country = await db.scalar(
        select(func.count(Photo.id)).where(Photo.location_country.isnot(None))
    )
    mode = by
    if by == "auto":
        mode = "country" if (has_country or 0) > 0 else "folder"

    albums = []

    if mode == "country":
        rows = (
            await db.execute(
                select(
                    Photo.location_country,
                    func.max(Photo.country_code).label("cc"),
                    func.count(Photo.id).label("count"),
                    func.coalesce(
                        func.min(case((Photo.media_type == "photo", Photo.id))),
                        func.min(Photo.id),
                    ).label("cover"),
                    func.min(Photo.taken_at).label("from_date"),
                    func.max(Photo.taken_at).label("to_date"),
                )
                .where(Photo.location_country.isnot(None))
                .group_by(Photo.location_country)
                .order_by(func.count(Photo.id).desc())
            )
        ).all()
        for r in rows:
            albums.append({
                "key": r.location_country,
                "type": "country",
                "title": r.location_country,
                "country_code": r.cc,
                "count": r.count,
                "cover_photo_id": r.cover,
                "from_date": r.from_date.isoformat() if r.from_date else None,
                "to_date": r.to_date.isoformat() if r.to_date else None,
            })
    else:
        # Folder albums, resolving country from manual tags where present
        tags = {t.folder: (t.country_code, t.country_name)
                for t in (await db.scalars(select(FolderCountry))).all()}
        rows = (
            await db.execute(
                select(
                    Photo.folder,
                    func.max(Photo.country_code).label("cc"),
                    func.max(Photo.location_country).label("country"),
                    func.count(Photo.id).label("count"),
                    func.coalesce(
                        func.min(case((Photo.media_type == "photo", Photo.id))),
                        func.min(Photo.id),
                    ).label("cover"),
                    func.min(Photo.taken_at).label("from_date"),
                    func.max(Photo.taken_at).label("to_date"),
                )
                .group_by(Photo.folder)
                .order_by(Photo.folder.desc())
            )
        ).all()
        for r in rows:
            tag = tags.get(r.folder)
            cc = (tag[0] if tag else None) or r.cc
            country = (tag[1] if tag else None) or r.country
            albums.append({
                "key": r.folder,
                "type": "folder",
                "title": _folder_leaf(r.folder),
                "subtitle": country,
                "country_code": cc,
                "count": r.count,
                "cover_photo_id": r.cover,
                "from_date": r.from_date.isoformat() if r.from_date else None,
                "to_date": r.to_date.isoformat() if r.to_date else None,
            })

    return {"mode": mode, "albums": albums}


class FolderCountryIn(BaseModel):
    folder: str
    country_code: str
    country_name: str


@router.post("/folder-country")
async def set_folder_country(payload: FolderCountryIn, db: AsyncSession = Depends(get_db)):
    """Tag a folder with a country; propagate to its photos so country albums
    and filters work even without GPS."""
    code = payload.country_code.lower().strip()
    name = payload.country_name.strip()

    existing = await db.get(FolderCountry, payload.folder)
    if existing:
        existing.country_code = code
        existing.country_name = name
    else:
        db.add(FolderCountry(folder=payload.folder, country_code=code, country_name=name))

    # Manual tags fill gaps only. Never overwrite trustworthy GPS-derived data.
    photos = (await db.scalars(
        select(Photo).where(
            Photo.folder == payload.folder,
            Photo.gps_lat.is_(None),
        )
    )).all()
    for p in photos:
        p.country_code = code
        p.location_country = name
    await db.commit()
    return {"updated": len(photos), "country": name, "country_code": code}


@router.delete("/folder-country")
async def clear_folder_country(folder: str, db: AsyncSession = Depends(get_db)):
    existing = await db.get(FolderCountry, folder)
    old_code = existing.country_code if existing else None
    old_name = existing.country_name if existing else None
    if existing:
        await db.delete(existing)
    photos = (await db.scalars(select(Photo).where(
        Photo.folder == folder,
        Photo.gps_lat.is_(None),
        Photo.country_code == old_code,
        Photo.location_country == old_name,
    ))).all() if existing else []
    for p in photos:
        p.country_code = None
        p.location_country = None
    await db.commit()
    return {"cleared": len(photos)}
