import asyncio
import time
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

_geolocator = Nominatim(user_agent="nas-visualizer/1.0", timeout=5)
_last_request = 0.0
_RATE_LIMIT = 1.1  # Nominatim requires >= 1 req/sec

# Cache by rounded coordinates (~110m at 3 decimals) so photos taken in the
# same place don't each hit Nominatim. Massive speedup for location detection.
_cache: dict[tuple[float, float], Optional[dict]] = {}
_lock = asyncio.Lock()


def _cache_key(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 3), round(lon, 3))


def _reverse_sync(lat: float, lon: float) -> Optional[dict]:
    global _last_request
    elapsed = time.monotonic() - _last_request
    if elapsed < _RATE_LIMIT:
        time.sleep(_RATE_LIMIT - elapsed)
    _last_request = time.monotonic()

    try:
        location = _geolocator.reverse(
            f"{lat},{lon}",
            language="es",
            exactly_one=True,
        )
        if not location:
            return None

        addr = location.raw.get("address", {})
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("county")
            or addr.get("state_district")
        )
        country = addr.get("country")
        state = addr.get("state")

        parts = [p for p in [city, state, country] if p]
        display_name = ", ".join(parts[:2]) if parts else location.address.split(",")[0]

        return {
            "location_name": display_name,
            "location_city": city,
            "location_country": country,
        }
    except (GeocoderTimedOut, Exception):
        return None


async def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    key = _cache_key(lat, lon)
    if key in _cache:
        return _cache[key]
    # Serialize network calls so the rate limit is honored under concurrency
    async with _lock:
        if key in _cache:
            return _cache[key]
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _reverse_sync, lat, lon)
        _cache[key] = result
        return result
