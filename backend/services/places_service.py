"""
Places & Attractions Service using OpenTripMap API (free, no credit card).
Get your key at: https://dev.opentripmap.org/
5,000 requests/day on free tier.
"""
import logging
import requests

logger = logging.getLogger(__name__)


class PlacesService:
    BASE = "https://api.opentripmap.com/0.1/en/places"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: dict) -> dict:
        params["apikey"] = self.api_key
        resp = requests.get(f"{self.BASE}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Geocode a city ────────────────────────────────────────────────────────
    def geocode(self, city: str) -> tuple:
        """Return (lat, lon) for a city name."""
        if not self.available:
            return (None, None)
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "format": "json", "limit": 1},
                headers={"User-Agent": "TravelAI-Agent/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            results = resp.json()
            if results:
                return (float(results[0]["lat"]), float(results[0]["lon"]))
        except Exception as e:
            logger.warning("Geocode failed for %s: %s", city, e)
        return (None, None)

    # ── Top attractions ───────────────────────────────────────────────────────
    def get_attractions(self, city: str, kinds: str = "cultural,natural,tourist_facilities",
                        limit: int = 10) -> list:
        """Return top attractions for a city."""
        if not self.available:
            return []
        try:
            lat, lon = self.geocode(city)
            if lat is None:
                return []
            data = self._get("/radius", {
                "radius": 10000,  # 10km radius
                "lon": lon, "lat": lat,
                "kinds": kinds,
                "rate": "3",      # min rating 3h (notable places)
                "format": "json",
                "limit": limit,
            })
            attractions = []
            for place in data:
                if place.get("name"):
                    attractions.append({
                        "name":     place["name"],
                        "kinds":    place.get("kinds", "").replace("_", " ").replace(",", ", "),
                        "rate":     place.get("rate", 0),
                        "osm_id":   place.get("osm", ""),
                        "distance": round(place.get("dist", 0) / 1000, 1),  # km from centre
                    })
            return sorted(attractions, key=lambda x: x["rate"], reverse=True)
        except Exception as e:
            logger.error("Places API error for %s: %s", city, e)
            return []

    # ── Place details ─────────────────────────────────────────────────────────
    def get_place_details(self, xid: str) -> dict:
        """Get full details for a place by its OpenTripMap ID."""
        if not self.available or not xid:
            return {}
        try:
            data = self._get(f"/xid/{xid}", {})
            info = data.get("info", {})
            return {
                "name":        data.get("name", ""),
                "description": info.get("descr", ""),
                "wikipedia":   data.get("wikipedia", ""),
                "image":       data.get("preview", {}).get("source", ""),
                "address":     data.get("address", {}),
            }
        except Exception as e:
            logger.error("Place detail error for %s: %s", xid, e)
            return {}
