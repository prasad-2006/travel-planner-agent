"""
Weather service using wttr.in — completely free, no API key required.
Falls back to OpenWeatherMap if OPENWEATHER_API_KEY is set.
"""
import logging
import requests
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class WeatherService:
    WTTR_URL   = "https://wttr.in/{city}?format=j1"
    OWM_URL    = "https://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #
    def get_current_weather(self, city: str) -> dict:
        """Return current weather. Tries OWM first (if key set), then wttr.in."""
        if self.api_key:
            result = self._owm_current(city)
            if result:
                return result
        return self._wttr_current(city)

    def get_forecast(self, city: str, days: int = 5) -> list:
        """Return daily forecast. Tries OWM first (if key set), then wttr.in."""
        if self.api_key:
            result = self._owm_forecast(city, days)
            if result:
                return result
        return self._wttr_forecast(city, days)

    # ------------------------------------------------------------------ #
    #  wttr.in (no key)                                                     #
    # ------------------------------------------------------------------ #
    def _wttr_current(self, city: str) -> dict:
        try:
            resp = requests.get(
                self.WTTR_URL.format(city=city.replace(" ", "+")),
                timeout=10,
                headers={"User-Agent": "TravelPlannerAgent/1.0"},
            )
            resp.raise_for_status()
            data    = resp.json()
            cur     = data["current_condition"][0]
            area    = data.get("nearest_area", [{}])[0]
            country = area.get("country", [{}])[0].get("value", "")
            return {
                "city":        city,
                "country":     country,
                "temperature": float(cur["temp_C"]),
                "feels_like":  float(cur["FeelsLikeC"]),
                "humidity":    int(cur["humidity"]),
                "description": cur["weatherDesc"][0]["value"],
                "icon":        "01d",
                "wind_speed":  round(float(cur["windspeedKmph"]) / 3.6, 1),
                "fetched_at":  datetime.now(timezone.utc).isoformat(),
                "source":      "wttr.in (live)",
            }
        except Exception as exc:
            logger.error("wttr.in weather error for %s: %s", city, exc)
            return self._mock_weather(city)

    def _wttr_forecast(self, city: str, days: int = 5) -> list:
        try:
            resp = requests.get(
                self.WTTR_URL.format(city=city.replace(" ", "+")),
                timeout=10,
                headers={"User-Agent": "TravelPlannerAgent/1.0"},
            )
            resp.raise_for_status()
            data   = resp.json()
            result = []
            for entry in data.get("weather", [])[:days]:
                result.append({
                    "date":        entry["date"],
                    "temp_min":    float(entry["mintempC"]),
                    "temp_max":    float(entry["maxtempC"]),
                    "description": entry["hourly"][4]["weatherDesc"][0]["value"],
                })
            return result
        except Exception as exc:
            logger.error("wttr.in forecast error for %s: %s", city, exc)
            return self._mock_forecast(city, days)

    # ------------------------------------------------------------------ #
    #  OpenWeatherMap (optional, if key provided)                           #
    # ------------------------------------------------------------------ #
    def _owm_current(self, city: str) -> dict | None:
        try:
            resp = requests.get(
                f"{self.OWM_URL}/weather",
                params={"q": city, "appid": self.api_key, "units": "metric"},
                timeout=10,
            )
            resp.raise_for_status()
            d = resp.json()
            return {
                "city":        d["name"],
                "country":     d["sys"]["country"],
                "temperature": round(d["main"]["temp"], 1),
                "feels_like":  round(d["main"]["feels_like"], 1),
                "humidity":    d["main"]["humidity"],
                "description": d["weather"][0]["description"].capitalize(),
                "icon":        d["weather"][0]["icon"],
                "wind_speed":  d["wind"]["speed"],
                "fetched_at":  datetime.now(timezone.utc).isoformat(),
                "source":      "OpenWeatherMap (live)",
            }
        except Exception:
            return None

    def _owm_forecast(self, city: str, days: int = 5) -> list | None:
        try:
            resp = requests.get(
                f"{self.OWM_URL}/forecast",
                params={"q": city, "appid": self.api_key, "units": "metric", "cnt": days * 8},
                timeout=10,
            )
            resp.raise_for_status()
            data  = resp.json()
            daily = {}
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]
                if date not in daily:
                    daily[date] = {
                        "date":        date,
                        "temp_min":    item["main"]["temp_min"],
                        "temp_max":    item["main"]["temp_max"],
                        "description": item["weather"][0]["description"].capitalize(),
                    }
            return list(daily.values())[:days]
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    #  Mock fallback                                                        #
    # ------------------------------------------------------------------ #
    def _mock_weather(self, city: str) -> dict:
        return {
            "city": city, "country": "–", "temperature": 22.0, "feels_like": 21.0,
            "humidity": 60, "description": "Partly cloudy", "icon": "02d",
            "wind_speed": 3.5, "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "mock",
        }

    def _mock_forecast(self, city: str, days: int) -> list:
        today = datetime.now(timezone.utc).date()
        return [
            {
                "date":        str(today + timedelta(days=i)),
                "temp_min":    18 + i,
                "temp_max":    26 + i,
                "description": ["Sunny", "Partly cloudy", "Light rain", "Sunny", "Cloudy"][i % 5],
            }
            for i in range(days)
        ]
