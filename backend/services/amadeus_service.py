"""
Amadeus Travel API Service — Live flights and hotels.
Free sandbox: https://developers.amadeus.com  (2,000 calls/month)
Production: same credentials, flip AMADEUS_HOSTNAME to api.amadeus.com
"""
import logging
import time
import requests

logger = logging.getLogger(__name__)

# City name → IATA airport code fallback map (top travel cities)
CITY_TO_IATA = {
    "new york": "JFK", "london": "LHR", "paris": "CDG", "dubai": "DXB",
    "tokyo": "NRT", "singapore": "SIN", "hong kong": "HKG", "sydney": "SYD",
    "los angeles": "LAX", "chicago": "ORD", "toronto": "YYZ", "amsterdam": "AMS",
    "frankfurt": "FRA", "madrid": "MAD", "barcelona": "BCN", "rome": "FCO",
    "milan": "MXP", "zurich": "ZRH", "vienna": "VIE", "brussels": "BRU",
    "istanbul": "IST", "mumbai": "BOM", "delhi": "DEL", "bangalore": "BLR",
    "bangkok": "BKK", "kuala lumpur": "KUL", "jakarta": "CGK", "seoul": "ICN",
    "beijing": "PEK", "shanghai": "PVG", "osaka": "KIX", "cairo": "CAI",
    "johannesburg": "JNB", "nairobi": "NBO", "lagos": "LOS", "casablanca": "CMN",
    "mexico city": "MEX", "sao paulo": "GRU", "buenos aires": "EZE", "lima": "LIM",
    "bogota": "BOG", "miami": "MIA", "san francisco": "SFO", "seattle": "SEA",
    "boston": "BOS", "atlanta": "ATL", "dallas": "DFW", "denver": "DEN",
    "bali": "DPS", "phuket": "HKT", "maldives": "MLE", "auckland": "AKL",
    "cape town": "CPT", "lisbon": "LIS", "athens": "ATH", "prague": "PRG",
    "budapest": "BUD", "warsaw": "WAW", "stockholm": "ARN", "oslo": "OSL",
    "copenhagen": "CPH", "helsinki": "HEL", "dublin": "DUB", "edinburgh": "EDI",
    "manchester": "MAN", "munich": "MUC", "berlin": "BER", "hamburg": "HAM",
}


class AmadeusService:
    """Wraps Amadeus REST API for live flight and hotel data."""

    SANDBOX_HOST = "https://test.api.amadeus.com"
    PROD_HOST    = "https://api.amadeus.com"

    def __init__(self, api_key: str, api_secret: str, use_sandbox: bool = True):
        self.api_key    = api_key
        self.api_secret = api_secret
        self.host       = self.SANDBOX_HOST if use_sandbox else self.PROD_HOST
        self._token     = None
        self._token_exp = 0

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.api_secret)

    # ── Auth ──────────────────────────────────────────────────────────────────
    def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        resp = requests.post(
            f"{self.host}/v1/security/oauth2/token",
            data={"grant_type": "client_credentials",
                  "client_id": self.api_key,
                  "client_secret": self.api_secret},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token     = data["access_token"]
        self._token_exp = time.time() + int(data.get("expires_in", 1799))
        return self._token

    def _get(self, path: str, params: dict) -> dict:
        headers = {"Authorization": f"Bearer {self._get_token()}"}
        resp = requests.get(f"{self.host}{path}", params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()

    # ── IATA lookup ───────────────────────────────────────────────────────────
    def city_to_iata(self, city_name: str) -> str:
        """Resolve city name to IATA code — API first, fallback map second."""
        key = city_name.lower().strip().split(",")[0].strip()
        # Try fallback map first (fast, no API call)
        if key in CITY_TO_IATA:
            return CITY_TO_IATA[key]
        if not self.available:
            return key[:3].upper()
        try:
            data = self._get("/v1/reference-data/locations", {
                "keyword": city_name, "subType": "CITY,AIRPORT", "page[limit]": 1
            })
            locs = data.get("data", [])
            if locs:
                return locs[0].get("iataCode", key[:3].upper())
        except Exception as e:
            logger.warning("IATA lookup failed for %s: %s", city_name, e)
        return key[:3].upper()

    # ── Flights ───────────────────────────────────────────────────────────────
    def search_flights(self, origin: str, destination: str,
                       departure_date: str, adults: int = 1,
                       currency: str = "USD", max_results: int = 5) -> list:
        """Search live flight offers. Returns list of flight dicts."""
        if not self.available:
            return []
        try:
            origin_code = self.city_to_iata(origin)
            dest_code   = self.city_to_iata(destination)
            data = self._get("/v2/shopping/flight-offers", {
                "originLocationCode":      origin_code,
                "destinationLocationCode": dest_code,
                "departureDate":           departure_date,
                "adults":                  adults,
                "currencyCode":            currency,
                "max":                     max_results,
                "nonStop":                 "false",
            })
            flights = []
            for offer in data.get("data", [])[:max_results]:
                seg     = offer["itineraries"][0]["segments"][0]
                price   = offer["price"]["total"]
                carrier = offer["validatingAirlineCodes"][0] if offer.get("validatingAirlineCodes") else seg.get("carrierCode", "")
                # Resolve carrier code to name from dictionaries
                carriers = data.get("dictionaries", {}).get("carriers", {})
                airline_name = carriers.get(carrier, carrier)
                stops = len(offer["itineraries"][0]["segments"]) - 1
                flights.append({
                    "airline":      airline_name,
                    "carrier_code": carrier,
                    "route":        f"{origin_code} → {dest_code}",
                    "departure":    seg["departure"]["at"],
                    "arrival":      offer["itineraries"][0]["segments"][-1]["arrival"]["at"],
                    "duration":     offer["itineraries"][0]["duration"].replace("PT","").replace("H","h ").replace("M","m").lower(),
                    "stops":        "Nonstop" if stops == 0 else f"{stops} stop{'s' if stops>1 else ''}",
                    "price":        float(price),
                    "currency":     currency,
                    "seats_left":   offer.get("numberOfBookableSeats", "—"),
                    "source":       "Amadeus (live)",
                })
            return flights
        except Exception as e:
            logger.error("Amadeus flight search error: %s", e)
            return []

    # ── Hotels ────────────────────────────────────────────────────────────────
    def search_hotels(self, city: str, check_in: str, check_out: str,
                      adults: int = 1, currency: str = "USD",
                      max_results: int = 6) -> list:
        """Search live hotel offers. Returns list of hotel dicts."""
        if not self.available:
            return []
        try:
            # Step 1: Get hotel IDs for the city
            city_code = self.city_to_iata(city)
            id_resp = self._get("/v1/reference-data/locations/hotels/by-city", {
                "cityCode": city_code, "radius": 5, "radiusUnit": "KM",
                "hotelSource": "ALL",
            })
            hotel_ids = [h["hotelId"] for h in id_resp.get("data", [])[:20]]
            if not hotel_ids:
                return []

            # Step 2: Get offers for those hotel IDs
            offer_resp = self._get("/v3/shopping/hotel-offers", {
                "hotelIds":  ",".join(hotel_ids[:10]),
                "checkInDate":  check_in,
                "checkOutDate": check_out,
                "adults":       adults,
                "currencyCode": currency,
                "bestRateOnly": "true",
            })
            hotels = []
            for item in offer_resp.get("data", [])[:max_results]:
                h = item.get("hotel", {})
                offers = item.get("offers", [{}])
                offer  = offers[0] if offers else {}
                price_info = offer.get("price", {})
                hotels.append({
                    "name":        h.get("name", "Hotel"),
                    "hotel_id":    h.get("hotelId", ""),
                    "city":        h.get("cityCode", city),
                    "latitude":    h.get("latitude"),
                    "longitude":   h.get("longitude"),
                    "price_total": float(price_info.get("total", 0)),
                    "price_per_night": round(float(price_info.get("total", 0)) /
                                             max((len(offer_resp.get("data",[])) or 1), 1), 2),
                    "currency":    price_info.get("currency", currency),
                    "room_type":   offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard"),
                    "board_type":  offer.get("boardType", "Room Only"),
                    "check_in":    check_in,
                    "check_out":   check_out,
                    "source":      "Amadeus (live)",
                })
            return hotels
        except Exception as e:
            logger.error("Amadeus hotel search error: %s", e)
            return []
