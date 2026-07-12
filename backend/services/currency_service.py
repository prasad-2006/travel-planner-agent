"""
Currency conversion service.
Primary:  frankfurter.app  — ECB official rates, completely free, no API key.
Fallback: exchangerate-api.com free tier (also no key for latest endpoint).
"""
import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_CACHE: dict = {}


class CurrencyService:
    FRANKFURTER = "https://api.frankfurter.app/latest"
    EXCHANGERATE = "https://api.exchangerate-api.com/v4/latest"

    def __init__(self, base_url: str = ""):
        # base_url kept for backward-compat but ignored — we always use frankfurter first
        pass

    def get_rates(self, base_currency: str = "USD") -> dict:
        key    = base_currency.upper()
        cached = _CACHE.get(key)
        if cached and (datetime.now(timezone.utc) - cached["ts"]).seconds < 3600:
            return cached["rates"]

        # 1. Try frankfurter.app (ECB official, no key)
        rates = self._frankfurter(key)
        if rates:
            _CACHE[key] = {"rates": rates, "ts": datetime.now(timezone.utc)}
            return rates

        # 2. Fallback: exchangerate-api.com
        rates = self._exchangerate(key)
        if rates:
            _CACHE[key] = {"rates": rates, "ts": datetime.now(timezone.utc)}
            return rates

        # 3. Last resort: hardcoded approximates
        logger.warning("All currency APIs failed — using static mock rates.")
        return self._mock_rates(key)

    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        rates = self.get_rates(from_currency.upper())
        rate  = rates.get(to_currency.upper(), 1.0)
        return round(amount * rate, 2)

    # ------------------------------------------------------------------ #
    #  Providers                                                            #
    # ------------------------------------------------------------------ #
    def _frankfurter(self, base: str) -> dict | None:
        try:
            resp = requests.get(
                self.FRANKFURTER,
                params={"from": base},
                timeout=8,
                headers={"User-Agent": "TravelPlannerAgent/1.0"},
            )
            resp.raise_for_status()
            data  = resp.json()
            rates = data.get("rates", {})
            rates[base] = 1.0        # add self-rate
            logger.info("Currency rates fetched from frankfurter.app (ECB) for %s", base)
            return rates
        except Exception as exc:
            logger.warning("frankfurter.app error: %s", exc)
            return None

    def _exchangerate(self, base: str) -> dict | None:
        try:
            resp = requests.get(f"{self.EXCHANGERATE}/{base}", timeout=8)
            resp.raise_for_status()
            rates = resp.json().get("rates", {})
            logger.info("Currency rates fetched from exchangerate-api.com for %s", base)
            return rates
        except Exception as exc:
            logger.warning("exchangerate-api error: %s", exc)
            return None

    def _mock_rates(self, base: str) -> dict:
        base_rates = {
            "USD": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.5, "AUD": 1.54, "CAD": 1.36,
                    "CHF": 0.90, "INR": 83.1, "TRY": 30.4,  "BRL": 5.0,  "USD": 1.0,
                    "AED": 3.67,"SGD": 1.35, "THB": 35.0,   "MXN": 17.2, "ZAR": 18.5},
            "EUR": {"USD": 1.09, "GBP": 0.86, "JPY": 162.7, "AUD": 1.67, "CAD": 1.48,
                    "CHF": 0.98, "INR": 90.5, "TRY": 33.1,  "BRL": 5.45, "EUR": 1.0,
                    "AED": 4.00,"SGD": 1.47, "THB": 38.1,   "MXN": 18.7, "ZAR": 20.1},
        }
        return base_rates.get(base, {"USD": 1.0})
