import io
import struct
from datetime import datetime
from typing import Optional
from PIL import Image, ExifTags
import pillow_heif

pillow_heif.register_heif_opener()

EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()}


def _rational_to_float(value) -> float:
    if isinstance(value, tuple) and len(value) == 2:
        return value[0] / value[1] if value[1] != 0 else 0.0
    return float(value)


def _gps_to_decimal(dms, ref: str) -> Optional[float]:
    try:
        deg = _rational_to_float(dms[0])
        min_ = _rational_to_float(dms[1])
        sec = _rational_to_float(dms[2])
        decimal = deg + min_ / 60.0 + sec / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def extract(data: bytes) -> dict:
    result: dict = {}
    try:
        img = Image.open(io.BytesIO(data))
        result["width"] = img.width
        result["height"] = img.height

        raw_exif = img._getexif() if hasattr(img, "_getexif") else None
        if not raw_exif:
            # Try getexif() for newer Pillow
            try:
                exif_data = img.getexif()
                raw_exif = dict(exif_data) if exif_data else None
            except Exception:
                pass

        if not raw_exif:
            return result

        exif = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}

        # Date taken
        for date_field in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            if date_field in exif:
                try:
                    result["taken_at"] = datetime.strptime(
                        str(exif[date_field]), "%Y:%m:%d %H:%M:%S"
                    )
                    break
                except (ValueError, TypeError):
                    pass

        # Camera info
        result["camera_make"] = str(exif.get("Make", "")).strip() or None
        result["camera_model"] = str(exif.get("Model", "")).strip() or None

        # GPS
        gps_info = exif.get("GPSInfo")
        if gps_info and isinstance(gps_info, dict):
            gps = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}
            lat = _gps_to_decimal(gps.get("GPSLatitude"), str(gps.get("GPSLatitudeRef", "N")))
            lon = _gps_to_decimal(gps.get("GPSLongitude"), str(gps.get("GPSLongitudeRef", "E")))
            if lat is not None and lon is not None:
                result["gps_lat"] = lat
                result["gps_lon"] = lon
            if "GPSAltitude" in gps:
                try:
                    result["gps_alt"] = _rational_to_float(gps["GPSAltitude"])
                except Exception:
                    pass

    except Exception:
        pass

    return result


def make_thumbnail(data: bytes, size: tuple[int, int] = (400, 400)) -> bytes:
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82, optimize=True)
        return buf.getvalue()
    except Exception:
        return b""
