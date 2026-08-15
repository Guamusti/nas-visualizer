import io
from datetime import datetime
from typing import Optional
from PIL import Image
import pillow_heif
import exifread

pillow_heif.register_heif_opener()

# rawpy is optional: if it fails to import, RAW thumbnails degrade gracefully
try:
    import rawpy
    _HAS_RAWPY = True
except Exception:
    _HAS_RAWPY = False

RAW_EXTENSIONS = {".raw", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".rw2", ".orf", ".raf", ".pef", ".srw"}


def _ext(filename: str) -> str:
    return ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""


def _ratio_to_float(r) -> float:
    try:
        return float(r.num) / float(r.den) if r.den else 0.0
    except AttributeError:
        return float(r)


def _dms_to_decimal(values, ref: str) -> Optional[float]:
    try:
        parts = values.values if hasattr(values, "values") else values
        deg = _ratio_to_float(parts[0])
        minute = _ratio_to_float(parts[1])
        sec = _ratio_to_float(parts[2])
        decimal = deg + minute / 60.0 + sec / 3600.0
        if ref and ref.upper() in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def extract(data: bytes, filename: str = "") -> dict:
    """Format-agnostic EXIF extraction (JPEG, HEIC, TIFF and RAW)."""
    result: dict = {}
    try:
        tags = exifread.process_file(io.BytesIO(data), details=False)
    except Exception:
        tags = {}

    def _str(key: str) -> Optional[str]:
        v = tags.get(key)
        return str(v).strip() if v is not None else None

    # Date taken
    for key in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
        raw = _str(key)
        if raw:
            try:
                result["taken_at"] = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                break
            except ValueError:
                pass

    result["camera_make"] = _str("Image Make")
    result["camera_model"] = _str("Image Model")

    # Dimensions from EXIF (may be refined later by the decoder)
    for wkey in ("EXIF ExifImageWidth", "Image ImageWidth"):
        if wkey in tags:
            try:
                result["width"] = int(str(tags[wkey]))
                break
            except ValueError:
                pass
    for hkey in ("EXIF ExifImageLength", "Image ImageLength"):
        if hkey in tags:
            try:
                result["height"] = int(str(tags[hkey]))
                break
            except ValueError:
                pass

    # GPS
    lat = tags.get("GPS GPSLatitude")
    lon = tags.get("GPS GPSLongitude")
    if lat is not None and lon is not None:
        lat_ref = _str("GPS GPSLatitudeRef") or "N"
        lon_ref = _str("GPS GPSLongitudeRef") or "E"
        dlat = _dms_to_decimal(lat, lat_ref)
        dlon = _dms_to_decimal(lon, lon_ref)
        if dlat is not None and dlon is not None:
            result["gps_lat"] = dlat
            result["gps_lon"] = dlon
        alt = tags.get("GPS GPSAltitude")
        if alt is not None:
            try:
                result["gps_alt"] = _ratio_to_float(alt.values[0] if hasattr(alt, "values") else alt)
            except Exception:
                pass

    return result


def _thumb_from_pil(img: Image.Image, size: tuple[int, int]) -> bytes:
    img = img.convert("RGB")
    img.thumbnail(size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82, optimize=True)
    return buf.getvalue()


def _raw_thumbnail(data: bytes, size: tuple[int, int]) -> bytes:
    """Extract the JPEG preview embedded in a RAW file — fast, no demosaicing."""
    if not _HAS_RAWPY:
        return b""
    try:
        with rawpy.imread(io.BytesIO(data)) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = Image.open(io.BytesIO(thumb.data))
                return _thumb_from_pil(img, size)
            elif thumb.format == rawpy.ThumbFormat.BITMAP:
                img = Image.fromarray(thumb.data)
                return _thumb_from_pil(img, size)
    except Exception:
        pass
    return b""


def make_thumbnail(data: bytes, filename: str = "", size: tuple[int, int] = (400, 400)) -> bytes:
    ext = _ext(filename)
    if ext in RAW_EXTENSIONS:
        thumb = _raw_thumbnail(data, size)
        if thumb:
            return thumb
        # Fall through: some RAW containers can still be opened by Pillow
    try:
        img = Image.open(io.BytesIO(data))
        return _thumb_from_pil(img, size)
    except Exception:
        return b""


def dimensions_of(data: bytes, filename: str = "") -> Optional[tuple[int, int]]:
    """Best-effort real pixel dimensions from the decoder."""
    ext = _ext(filename)
    try:
        if ext in RAW_EXTENSIONS and _HAS_RAWPY:
            with rawpy.imread(io.BytesIO(data)) as raw:
                s = raw.sizes
                return (s.width, s.height)
        img = Image.open(io.BytesIO(data))
        return (img.width, img.height)
    except Exception:
        return None
