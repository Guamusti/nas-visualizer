import asyncio
import time
from typing import Optional
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

_geolocator = Nominatim(user_agent="nas-visualizer/1.0", timeout=5)
_last_request = 0.0
_RATE_LIMIT = 1.1  # Nominatim requires >= 1 req/sec


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
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _reverse_sync, lat, lon)
