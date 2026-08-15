from datetime import datetime
from sqlalchemy import Integer, String, Float, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    folder: Mapped[str] = mapped_column(String, nullable=False, index=True)
    size: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    # EXIF
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    camera_make: Mapped[str | None] = mapped_column(String)
    camera_model: Mapped[str | None] = mapped_column(String)

    # GPS
    gps_lat: Mapped[float | None] = mapped_column(Float)
    gps_lon: Mapped[float | None] = mapped_column(Float)
    gps_alt: Mapped[float | None] = mapped_column(Float)

    # Geocoded location
    location_name: Mapped[str | None] = mapped_column(String, index=True)
    location_city: Mapped[str | None] = mapped_column(String, index=True)
    location_country: Mapped[str | None] = mapped_column(String, index=True)
    country_code: Mapped[str | None] = mapped_column(String, index=True)  # ISO 2-letter, for flags

    # Thumbnail
    thumbnail_cached: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI processing (Phase 2+)
    ai_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ai_tags: Mapped[str | None] = mapped_column(Text)  # JSON list of strings
    face_count: Mapped[int] = mapped_column(Integer, default=0)

    indexed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="running")  # running|done|error
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    new_files: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class FolderCountry(Base):
    """Manual country assignment for a folder (for photos without GPS)."""
    __tablename__ = "folder_countries"

    folder: Mapped[str] = mapped_column(String, primary_key=True)
    country_code: Mapped[str] = mapped_column(String, nullable=False)
    country_name: Mapped[str] = mapped_column(String, nullable=False)
