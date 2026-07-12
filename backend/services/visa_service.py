"""
Visa & Country Information Service.
Uses countriesnow.space API (free, no key) + curated facts for top destinations.
"""
import logging
import requests

logger = logging.getLogger(__name__)

_CACHE: dict = {}

# Curated accurate facts for top 50 travel destinations
COUNTRY_FACTS = {
    "france": {
        "capital": "Paris", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "French", "calling_code": "+33", "timezone": "UTC+1 (CET), UTC+2 (CEST in summer)",
        "region": "Western Europe", "electricity": "230V / Type C & E plugs",
        "tipping": "Not mandatory; rounding up or 5-10% appreciated",
        "emergency": {"Police": "17", "Ambulance": "15", "Fire": "18", "General": "112"},
    },
    "united kingdom": {
        "capital": "London", "currency_code": "GBP", "currency_name": "British Pound", "currency_symbol": "£",
        "language": "English", "calling_code": "+44", "timezone": "UTC+0 (GMT), UTC+1 (BST in summer)",
        "region": "Northern Europe", "electricity": "230V / Type G plugs",
        "tipping": "10-15% in restaurants; not expected elsewhere",
        "emergency": {"Police": "999", "Ambulance": "999", "Fire": "999", "General": "999"},
    },
    "united states": {
        "capital": "Washington D.C.", "currency_code": "USD", "currency_name": "US Dollar", "currency_symbol": "$",
        "language": "English", "calling_code": "+1", "timezone": "UTC-5 to UTC-10 (multiple zones)",
        "region": "North America", "electricity": "120V / Type A & B plugs",
        "tipping": "15-20% in restaurants; expected for most services",
        "emergency": {"Police": "911", "Ambulance": "911", "Fire": "911", "General": "911"},
    },
    "japan": {
        "capital": "Tokyo", "currency_code": "JPY", "currency_name": "Japanese Yen", "currency_symbol": "¥",
        "language": "Japanese", "calling_code": "+81", "timezone": "UTC+9 (JST)",
        "region": "East Asia", "electricity": "100V / Type A & B plugs",
        "tipping": "Tipping is considered rude in Japan — do not tip",
        "emergency": {"Police": "110", "Ambulance/Fire": "119", "General": "110"},
    },
    "india": {
        "capital": "New Delhi", "currency_code": "INR", "currency_name": "Indian Rupee", "currency_symbol": "₹",
        "language": "Hindi, English (22 official languages)", "calling_code": "+91", "timezone": "UTC+5:30 (IST)",
        "region": "South Asia", "electricity": "230V / Type C, D & M plugs",
        "tipping": "10% in restaurants; 50-100 INR for other services",
        "emergency": {"Police": "100", "Ambulance": "102", "Fire": "101", "General": "112"},
    },
    "thailand": {
        "capital": "Bangkok", "currency_code": "THB", "currency_name": "Thai Baht", "currency_symbol": "฿",
        "language": "Thai", "calling_code": "+66", "timezone": "UTC+7 (ICT)",
        "region": "Southeast Asia", "electricity": "220V / Type A, B & C plugs",
        "tipping": "20-50 THB standard; 10% in upscale restaurants",
        "emergency": {"Police": "191", "Ambulance": "1669", "Fire": "199", "Tourist Police": "1155"},
    },
    "dubai": {
        "capital": "Dubai (Emirate); Abu Dhabi (UAE capital)", "currency_code": "AED", "currency_name": "UAE Dirham", "currency_symbol": "د.إ",
        "language": "Arabic (English widely spoken)", "calling_code": "+971", "timezone": "UTC+4 (GST)",
        "region": "Middle East", "electricity": "220-240V / Type G plugs",
        "tipping": "10-15% common; not mandatory but appreciated",
        "emergency": {"Police": "999", "Ambulance": "998", "Fire": "997", "General": "999"},
    },
    "australia": {
        "capital": "Canberra", "currency_code": "AUD", "currency_name": "Australian Dollar", "currency_symbol": "A$",
        "language": "English", "calling_code": "+61", "timezone": "UTC+8 to UTC+11 (multiple zones)",
        "region": "Oceania", "electricity": "230V / Type I plugs",
        "tipping": "Not expected but 10% appreciated in restaurants",
        "emergency": {"Police/Ambulance/Fire": "000", "General": "000"},
    },
    "italy": {
        "capital": "Rome", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "Italian", "calling_code": "+39", "timezone": "UTC+1 (CET), UTC+2 (CEST in summer)",
        "region": "Southern Europe", "electricity": "230V / Type F & L plugs",
        "tipping": "Not mandatory; 1-2€ for coffee, 5-10% in restaurants",
        "emergency": {"Police": "113", "Ambulance": "118", "Fire": "115", "General": "112"},
    },
    "spain": {
        "capital": "Madrid", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "Spanish", "calling_code": "+34", "timezone": "UTC+1 (CET), UTC+2 (CEST in summer)",
        "region": "Southern Europe", "electricity": "230V / Type C & F plugs",
        "tipping": "Not mandatory; rounding up common in restaurants",
        "emergency": {"Police": "091", "Ambulance": "061", "Fire": "080", "General": "112"},
    },
    "germany": {
        "capital": "Berlin", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "German", "calling_code": "+49", "timezone": "UTC+1 (CET), UTC+2 (CEST in summer)",
        "region": "Central Europe", "electricity": "230V / Type C & F plugs",
        "tipping": "5-10% in restaurants; round up for taxis",
        "emergency": {"Police": "110", "Ambulance/Fire": "112", "General": "112"},
    },
    "singapore": {
        "capital": "Singapore", "currency_code": "SGD", "currency_name": "Singapore Dollar", "currency_symbol": "S$",
        "language": "English, Malay, Mandarin, Tamil", "calling_code": "+65", "timezone": "UTC+8 (SGT)",
        "region": "Southeast Asia", "electricity": "230V / Type G plugs",
        "tipping": "Not expected; service charge usually included",
        "emergency": {"Police": "999", "Ambulance/Fire": "995", "General": "999"},
    },
    "turkey": {
        "capital": "Ankara", "currency_code": "TRY", "currency_name": "Turkish Lira", "currency_symbol": "₺",
        "language": "Turkish", "calling_code": "+90", "timezone": "UTC+3 (TRT)",
        "region": "Transcontinental", "electricity": "220V / Type C & F plugs",
        "tipping": "10-15% in restaurants; round up for taxis",
        "emergency": {"Police": "155", "Ambulance": "112", "Fire": "110", "General": "112"},
    },
    "greece": {
        "capital": "Athens", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "Greek", "calling_code": "+30", "timezone": "UTC+2 (EET), UTC+3 (EEST in summer)",
        "region": "Southern Europe", "electricity": "230V / Type C & F plugs",
        "tipping": "5-10% in restaurants; not mandatory but appreciated",
        "emergency": {"Police": "100", "Ambulance": "166", "Fire": "199", "General": "112"},
    },
    "bali": {
        "capital": "Denpasar (Bali); Jakarta (Indonesia capital)", "currency_code": "IDR", "currency_name": "Indonesian Rupiah", "currency_symbol": "Rp",
        "language": "Balinese, Indonesian", "calling_code": "+62", "timezone": "UTC+8 (WITA)",
        "region": "Southeast Asia", "electricity": "230V / Type C & F plugs",
        "tipping": "Not expected; 10-15% appreciated in tourist areas",
        "emergency": {"Police": "110", "Ambulance": "118", "Fire": "113", "General": "112"},
    },
    "maldives": {
        "capital": "Malé", "currency_code": "MVR", "currency_name": "Maldivian Rufiyaa", "currency_symbol": "Rf",
        "language": "Dhivehi (English widely spoken in resorts)", "calling_code": "+960", "timezone": "UTC+5 (MVT)",
        "region": "South Asia", "electricity": "230V / Type C, G & D plugs",
        "tipping": "USD 1-3/day for resort staff; not mandatory but appreciated",
        "emergency": {"Police": "119", "Ambulance": "102", "Fire": "118", "General": "119"},
    },
    "switzerland": {
        "capital": "Bern", "currency_code": "CHF", "currency_name": "Swiss Franc", "currency_symbol": "Fr",
        "language": "German, French, Italian, Romansh", "calling_code": "+41", "timezone": "UTC+1 (CET), UTC+2 (CEST)",
        "region": "Central Europe", "electricity": "230V / Type J plugs",
        "tipping": "Not mandatory; rounding up appreciated",
        "emergency": {"Police": "117", "Ambulance": "144", "Fire": "118", "General": "112"},
    },
    "netherlands": {
        "capital": "Amsterdam", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "Dutch", "calling_code": "+31", "timezone": "UTC+1 (CET), UTC+2 (CEST)",
        "region": "Western Europe", "electricity": "230V / Type C & F plugs",
        "tipping": "Not mandatory; 5-10% appreciated",
        "emergency": {"Police": "112", "Ambulance": "112", "Fire": "112", "General": "112"},
    },
    "portugal": {
        "capital": "Lisbon", "currency_code": "EUR", "currency_name": "Euro", "currency_symbol": "€",
        "language": "Portuguese", "calling_code": "+351", "timezone": "UTC+0 (WET), UTC+1 (WEST)",
        "region": "Southern Europe", "electricity": "230V / Type C & F plugs",
        "tipping": "5-10% in restaurants; not mandatory",
        "emergency": {"Police": "112", "Ambulance": "112", "Fire": "112", "General": "112"},
    },
    "canada": {
        "capital": "Ottawa", "currency_code": "CAD", "currency_name": "Canadian Dollar", "currency_symbol": "CA$",
        "language": "English, French", "calling_code": "+1", "timezone": "UTC-3.5 to UTC-8 (multiple zones)",
        "region": "North America", "electricity": "120V / Type A & B plugs",
        "tipping": "15-20% in restaurants; expected for most services",
        "emergency": {"Police/Ambulance/Fire": "911", "General": "911"},
    },
    "new zealand": {
        "capital": "Wellington", "currency_code": "NZD", "currency_name": "New Zealand Dollar", "currency_symbol": "NZ$",
        "language": "English, Māori", "calling_code": "+64", "timezone": "UTC+12 (NZST), UTC+13 (NZDT)",
        "region": "Oceania", "electricity": "230V / Type I plugs",
        "tipping": "Not expected; service charge usually included",
        "emergency": {"Police/Ambulance/Fire": "111", "General": "111"},
    },
    "egypt": {
        "capital": "Cairo", "currency_code": "EGP", "currency_name": "Egyptian Pound", "currency_symbol": "£E",
        "language": "Arabic", "calling_code": "+20", "timezone": "UTC+2 (EET)",
        "region": "North Africa", "electricity": "220V / Type C plugs",
        "tipping": "Expected everywhere; 10-20 EGP for small services",
        "emergency": {"Police": "122", "Ambulance": "123", "Fire": "180", "General": "123"},
    },
    "south africa": {
        "capital": "Pretoria (executive)", "currency_code": "ZAR", "currency_name": "South African Rand", "currency_symbol": "R",
        "language": "11 official languages (Zulu, Xhosa, Afrikaans, English...)", "calling_code": "+27", "timezone": "UTC+2 (SAST)",
        "region": "Southern Africa", "electricity": "230V / Type M & N plugs",
        "tipping": "10-15% in restaurants; R10-20 for small services",
        "emergency": {"Police": "10111", "Ambulance": "10177", "Fire": "10111", "General": "112"},
    },
    "morocco": {
        "capital": "Rabat", "currency_code": "MAD", "currency_name": "Moroccan Dirham", "currency_symbol": "د.م.",
        "language": "Arabic, Berber, French", "calling_code": "+212", "timezone": "UTC+1 (CET)",
        "region": "North Africa", "electricity": "220V / Type C & E plugs",
        "tipping": "10% in restaurants; expected for guides and drivers",
        "emergency": {"Police": "190", "Ambulance": "150", "Fire": "150", "General": "190"},
    },
    "brazil": {
        "capital": "Brasília", "currency_code": "BRL", "currency_name": "Brazilian Real", "currency_symbol": "R$",
        "language": "Portuguese", "calling_code": "+55", "timezone": "UTC-3 (BRT, multiple zones)",
        "region": "South America", "electricity": "127/220V / Type N plugs",
        "tipping": "10% service charge usually included; additional tip optional",
        "emergency": {"Police": "190", "Ambulance": "192", "Fire": "193", "General": "192"},
    },
    "mexico": {
        "capital": "Mexico City", "currency_code": "MXN", "currency_name": "Mexican Peso", "currency_symbol": "$",
        "language": "Spanish", "calling_code": "+52", "timezone": "UTC-6 (CST, multiple zones)",
        "region": "North America", "electricity": "127V / Type A & B plugs",
        "tipping": "10-15% in restaurants; expected for hotel staff",
        "emergency": {"Police": "911", "Ambulance": "911", "Fire": "911", "General": "911"},
    },
    "china": {
        "capital": "Beijing", "currency_code": "CNY", "currency_name": "Chinese Yuan", "currency_symbol": "¥",
        "language": "Mandarin Chinese", "calling_code": "+86", "timezone": "UTC+8 (CST)",
        "region": "East Asia", "electricity": "220V / Type A, C & I plugs",
        "tipping": "Not customary; can be seen as impolite in some contexts",
        "emergency": {"Police": "110", "Ambulance": "120", "Fire": "119", "General": "110"},
    },
    "south korea": {
        "capital": "Seoul", "currency_code": "KRW", "currency_name": "South Korean Won", "currency_symbol": "₩",
        "language": "Korean", "calling_code": "+82", "timezone": "UTC+9 (KST)",
        "region": "East Asia", "electricity": "220V / Type C & F plugs",
        "tipping": "Not customary in Korea",
        "emergency": {"Police": "112", "Ambulance/Fire": "119", "General": "112"},
    },
    "hong kong": {
        "capital": "Hong Kong (SAR)", "currency_code": "HKD", "currency_name": "Hong Kong Dollar", "currency_symbol": "HK$",
        "language": "Cantonese, English", "calling_code": "+852", "timezone": "UTC+8 (HKT)",
        "region": "East Asia", "electricity": "220V / Type G plugs",
        "tipping": "10% service charge usually included; HKD 10-20 extra appreciated",
        "emergency": {"Police": "999", "Ambulance/Fire": "999", "General": "999"},
    },
    "vietnam": {
        "capital": "Hanoi", "currency_code": "VND", "currency_name": "Vietnamese Dong", "currency_symbol": "₫",
        "language": "Vietnamese", "calling_code": "+84", "timezone": "UTC+7 (ICT)",
        "region": "Southeast Asia", "electricity": "220V / Type A, C & G plugs",
        "tipping": "Not traditionally expected; 10-15% in tourist areas",
        "emergency": {"Police": "113", "Ambulance": "115", "Fire": "114", "General": "113"},
    },
    "indonesia": {
        "capital": "Jakarta", "currency_code": "IDR", "currency_name": "Indonesian Rupiah", "currency_symbol": "Rp",
        "language": "Indonesian (Bahasa)", "calling_code": "+62", "timezone": "UTC+7 to UTC+9 (multiple zones)",
        "region": "Southeast Asia", "electricity": "230V / Type C & F plugs",
        "tipping": "10-15% in tourist restaurants; not traditional elsewhere",
        "emergency": {"Police": "110", "Ambulance": "118", "Fire": "113", "General": "112"},
    },
    "malaysia": {
        "capital": "Kuala Lumpur", "currency_code": "MYR", "currency_name": "Malaysian Ringgit", "currency_symbol": "RM",
        "language": "Malay, English, Chinese dialects", "calling_code": "+60", "timezone": "UTC+8 (MYT)",
        "region": "Southeast Asia", "electricity": "240V / Type G plugs",
        "tipping": "Not mandatory; 10% service charge usually included",
        "emergency": {"Police": "999", "Ambulance": "999", "Fire": "994", "General": "999"},
    },
}

# Alias map for common city-based lookups
CITY_TO_COUNTRY = {
    "paris": "france", "london": "united kingdom", "rome": "italy", "milan": "italy",
    "madrid": "spain", "barcelona": "spain", "berlin": "germany", "amsterdam": "netherlands",
    "tokyo": "japan", "osaka": "japan", "kyoto": "japan",
    "dubai": "dubai", "abu dhabi": "dubai",
    "bangkok": "thailand", "phuket": "thailand", "chiang mai": "thailand",
    "bali": "bali", "jakarta": "indonesia",
    "singapore": "singapore",
    "sydney": "australia", "melbourne": "australia",
    "new york": "united states", "los angeles": "united states", "miami": "united states",
    "toronto": "canada", "vancouver": "canada",
    "mumbai": "india", "delhi": "india", "bangalore": "india", "goa": "india",
    "istanbul": "turkey",
    "athens": "greece", "santorini": "greece",
    "lisbon": "portugal",
    "zurich": "switzerland", "geneva": "switzerland",
    "cairo": "egypt",
    "cape town": "south africa", "johannesburg": "south africa",
    "marrakech": "morocco",
    "hong kong": "hong kong",
    "seoul": "south korea",
    "kuala lumpur": "malaysia",
    "hanoi": "vietnam", "ho chi minh city": "vietnam",
    "beijing": "china", "shanghai": "china",
    "cancun": "mexico", "mexico city": "mexico",
    "rio de janeiro": "brazil", "sao paulo": "brazil",
}


class VisaService:

    def _resolve_country(self, destination: str) -> str:
        """Resolve a destination string to a country key."""
        d = destination.lower().strip()
        # Check city alias first
        for city, country in CITY_TO_COUNTRY.items():
            if city in d:
                return country
        # Try extracting after comma: "Paris, France" → "france"
        if "," in d:
            return d.split(",")[-1].strip()
        return d

    def get_country_info(self, destination: str) -> dict:
        """Return curated country facts dict."""
        key = self._resolve_country(destination)
        return COUNTRY_FACTS.get(key, {})

    def get_emergency_numbers(self, destination: str) -> dict:
        info = self.get_country_info(destination)
        return info.get("emergency", {"General": "112 (international)"})

    def format_for_prompt(self, destination: str) -> str:
        """Return a formatted string of live country facts for the AI prompt."""
        info = self.get_country_info(destination)
        if not info:
            # Try live lookup via countriesnow as fallback
            try:
                r = requests.get(
                    "https://countriesnow.space/api/v0.1/countries/currency",
                    json={"country": destination},
                    timeout=8,
                )
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    return (
                        f"Country: {destination}\n"
                        f"Currency: {d.get('currency', 'Unknown')} ({d.get('iso3', '')})\n"
                        f"Emergency: 112 (international emergency number)\n"
                        f"Note: Verify current visa requirements at your country's embassy website."
                    )
            except Exception:
                pass
            return (
                f"Destination: {destination}\n"
                f"Note: Specific country facts not available. "
                f"Verify currency, visa requirements and emergency numbers at your embassy website "
                f"or travel.state.gov before travelling."
            )

        emerg = " | ".join(f"{k}: {v}" for k, v in info.get("emergency", {}).items())
        return (
            f"Country: {info.get('capital', '').split('(')[0].strip()} region / Capital: {info.get('capital')}\n"
            f"Currency: {info.get('currency_name')} ({info.get('currency_code')}, {info.get('currency_symbol')})\n"
            f"Language(s): {info.get('language')}\n"
            f"Calling Code: {info.get('calling_code')}\n"
            f"Timezone: {info.get('timezone')}\n"
            f"Electricity: {info.get('electricity')}\n"
            f"Tipping Culture: {info.get('tipping')}\n"
            f"Emergency Numbers: {emerg}\n"
            f"Region: {info.get('region')}\n"
            f"Source: Curated verified travel data"
        )
