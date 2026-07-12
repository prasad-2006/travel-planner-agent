"""
Destination enrichment service.
Pulls real information about a destination from:
  1. Wikipedia REST API  — summary, extract, highlights (no key)
  2. Nominatim (OpenStreetMap) — geocoding, country code (no key)

All sources are free and require no registration.
"""
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "TravelPlannerAgent/1.0 (educational project)"}

_CACHE: dict = {}


class DestinationService:
    """Fetches real, live destination data from free public APIs."""

    # ------------------------------------------------------------------ #
    #  Public interface                                                     #
    # ------------------------------------------------------------------ #
    def get_destination_info(self, destination: str) -> dict:
        """
        Returns a combined dict with:
          - wiki_summary     : 2-3 sentence Wikipedia intro
          - wiki_highlights  : bullet list of top sights / facts
          - coordinates      : {lat, lon}
          - country          : full country name
          - country_code     : ISO 2-letter
          - timezone         : e.g. "Europe/Paris"
          - population       : integer
          - languages        : list of strings
          - currencies       : list of strings e.g. ["Euro (EUR)"]
          - region           : e.g. "Western Europe"
        """
        cache_key = destination.lower().strip()
        if cache_key in _CACHE:
            return _CACHE[cache_key]

        result: dict = {"destination": destination}

        geo   = self._nominatim(destination)
        wiki  = self._wikipedia(destination)
        ctry  = self._country_from_visa_service(destination)

        result.update(geo)
        result.update(wiki)
        result.update(ctry)

        _CACHE[cache_key] = result
        return result

    def format_for_prompt(self, destination: str) -> str:
        """Return a compact string ready to be injected into an AI prompt."""
        info = self.get_destination_info(destination)
        lines = []
        if info.get("wiki_summary"):
            lines.append(f"About {destination}: {info['wiki_summary']}")
        if info.get("country"):
            lines.append(f"Country: {info['country']}")
        if info.get("region"):
            lines.append(f"Region: {info['region']}")
        if info.get("population"):
            lines.append(f"Population: {info['population']:,}")
        if info.get("languages"):
            lines.append(f"Languages: {', '.join(info['languages'])}")
        if info.get("currencies"):
            lines.append(f"Currencies: {', '.join(info['currencies'])}")
        if info.get("timezone"):
            lines.append(f"Timezone: {info['timezone']}")
        if info.get("wiki_highlights"):
            lines.append(f"Highlights: {info['wiki_highlights']}")
        return "\n".join(lines) if lines else f"No enrichment data available for {destination}."

    # ------------------------------------------------------------------ #
    #  Nominatim (OpenStreetMap geocoding — no key)                        #
    # ------------------------------------------------------------------ #
    def _nominatim(self, destination: str) -> dict:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": destination, "format": "json", "limit": 1, "addressdetails": 1},
                headers=HEADERS,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return {}
            top  = data[0]
            addr = top.get("address", {})
            return {
                "coordinates":   {"lat": float(top["lat"]), "lon": float(top["lon"])},
                "country":       addr.get("country", ""),
                "country_code":  addr.get("country_code", "").upper(),
                "nominatim_type": top.get("type", ""),
            }
        except Exception as exc:
            logger.warning("Nominatim error for %s: %s", destination, exc)
            return {}

    # ------------------------------------------------------------------ #
    #  Wikipedia REST API (no key)                                         #
    # ------------------------------------------------------------------ #
    def _wikipedia(self, destination: str) -> dict:
        # Try the destination name, then just the city part (before comma)
        queries = [destination]
        if "," in destination:
            queries.append(destination.split(",")[0].strip())

        for query in queries:
            try:
                title = query.replace(" ", "_")
                resp  = requests.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                    headers=HEADERS,
                    timeout=8,
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data    = resp.json()
                extract = data.get("extract", "")

                # Clean up & take first 3 sentences as summary
                sentences = re.split(r'(?<=[.!?])\s+', extract.strip())
                summary   = " ".join(sentences[:3])

                # Pull interesting short facts from extract as highlights
                highlights = self._extract_highlights(extract)

                return {
                    "wiki_summary":    summary,
                    "wiki_highlights": highlights,
                    "wiki_url":        data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                }
            except Exception as exc:
                logger.warning("Wikipedia error for %s: %s", query, exc)

        return {}

    def _extract_highlights(self, text: str) -> str:
        """Pull short interesting facts from Wikipedia extract."""
        if not text:
            return ""
        # Grab sentences containing tourism keywords
        keywords = ["known for", "famous for", "notable", "attract", "tourism",
                    "landmark", "UNESCO", "historic", "cuisine", "capital", "largest",
                    "popular", "founded", "established", "located"]
        sentences = re.split(r'(?<=[.!?])\s+', text)
        picks = [s.strip() for s in sentences
                 if any(kw in s.lower() for kw in keywords) and len(s) < 200]
        return " ".join(picks[:3]) if picks else ""

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                     #
    # ------------------------------------------------------------------ #
    def _country_from_visa_service(self, destination: str) -> dict:
        """Pull country metadata from the curated COUNTRY_FACTS dict in visa_service."""
        try:
            from backend.services.visa_service import COUNTRY_FACTS, CITY_TO_COUNTRY
            d = destination.lower().strip()
            # Resolve city → country key
            country_key = None
            for city, ck in CITY_TO_COUNTRY.items():
                if city in d:
                    country_key = ck
                    break
            if not country_key:
                if "," in d:
                    country_key = d.split(",")[-1].strip()
                else:
                    country_key = d

            facts = COUNTRY_FACTS.get(country_key, {})
            if not facts:
                return {}

            return {
                "languages":  [facts.get("language", "")],
                "currencies": [f"{facts.get('currency_name','')} ({facts.get('currency_code','')})"],
                "region":     facts.get("region", ""),
                "capital":    facts.get("capital", "").split("(")[0].strip(),
                "timezone":   facts.get("timezone", ""),
                "population": 0,   # not in our curated dict
            }
        except Exception as exc:
            logger.warning("Visa service country lookup failed: %s", exc)
            return {}
