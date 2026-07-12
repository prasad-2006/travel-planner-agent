"""
IBM Granite LLM Service via IBM watsonx.ai
Handles all AI generation tasks using IBM Cloud Lite free tier.
"""
import json
import logging
from typing import Optional

import requests

# IBM watsonx.ai SDK – available on IBM Cloud Lite.
# Install via: pip install ibm-watsonx-ai
# Falls back to mock mode if SDK is not installed.
try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    IBM_SDK_AVAILABLE = True
except ImportError:
    IBM_SDK_AVAILABLE = False
    Credentials = ModelInference = GenParams = None

logger = logging.getLogger(__name__)


class GraniteService:
    """Wrapper around IBM Granite models hosted on watsonx.ai (IBM Cloud Lite)."""

    def __init__(self, config):
        self.config  = config
        self._model  = None
        self._token  = None
        self._token_expiry = 0

    # ------------------------------------------------------------------ #
    #  Authentication                                                       #
    # ------------------------------------------------------------------ #
    def _get_iam_token(self) -> str:
        """Obtain a short-lived IAM bearer token from IBM Cloud."""
        import time
        if self._token and time.time() < self._token_expiry - 60:
            return self._token

        resp = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "urn:ibm:params:oauth:grant-type:apikey",
                "apikey":        self.config.IBM_WATSONX_API_KEY,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token        = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 3600))
        return self._token

    # ------------------------------------------------------------------ #
    #  Model initialisation                                                 #
    # ------------------------------------------------------------------ #
    def _get_model(self):
        if not IBM_SDK_AVAILABLE:
            raise RuntimeError("ibm-watsonx-ai SDK not installed.")
        if self._model is None:
            credentials = Credentials(
                url=self.config.IBM_WATSONX_URL,
                api_key=self.config.IBM_WATSONX_API_KEY,
            )
            self._model = ModelInference(
                model_id=self.config.GRANITE_CHAT_MODEL,
                credentials=credentials,
                project_id=self.config.IBM_WATSONX_PROJECT_ID,
                params={
                    GenParams.MAX_NEW_TOKENS: self.config.LLM_MAX_TOKENS,
                    GenParams.TEMPERATURE:    self.config.LLM_TEMPERATURE,
                    GenParams.TOP_P:          self.config.LLM_TOP_P,
                    GenParams.TOP_K:          self.config.LLM_TOP_K,
                    GenParams.STOP_SEQUENCES: ["<|endoftext|>"],
                },
            )
        return self._model

    # ------------------------------------------------------------------ #
    #  Core generation                                                      #
    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Send a prompt to IBM Granite and return the generated text."""
        if not IBM_SDK_AVAILABLE or not self.config.IBM_WATSONX_API_KEY:
            logger.warning("IBM watsonx SDK/key not available – returning mock response.")
            return self._mock_response(prompt)

        try:
            model  = self._get_model()
            params = {}
            if max_tokens:
                params[GenParams.MAX_NEW_TOKENS] = max_tokens
            result = model.generate_text(prompt=prompt, params=params if params else None)
            return result
        except Exception as exc:
            logger.error("Granite generation error: %s", exc)
            return self._mock_response(prompt)

    def generate_json(self, prompt: str) -> dict:
        """Generate text and parse it as JSON. Falls back to empty dict on failure."""
        raw = self.generate(prompt + "\n\nRespond ONLY with valid JSON. No markdown, no explanation.")
        try:
            # Try to extract JSON object from the response
            import re
            text = raw.strip()
            # Strip markdown fences
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            text = text.strip()
            # Find the first { ... } block
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Could not parse JSON from Granite output: %s", e)
            return {}

    # ------------------------------------------------------------------ #
    #  Mock responses (when API key is absent / during local dev)           #
    # ------------------------------------------------------------------ #
    def _mock_response(self, prompt: str) -> str:
        p = prompt.lower()
        if "destination" in p:
            return (
                "Based on your preferences, I recommend **Paris, France** for a cultural city break, "
                "**Bali, Indonesia** for a tropical retreat, or **Queenstown, New Zealand** for adventure. "
                "Each offers distinct experiences suited to different travel styles and budgets."
            )
        if "itinerary" in p:
            return (
                "**Day 1** – Arrive, check in, explore the city centre and enjoy a welcome dinner.\n"
                "**Day 2** – Morning guided tour of top landmarks; afternoon free for shopping.\n"
                "**Day 3** – Day trip to a nearby natural attraction; evening sunset cruise.\n"
                "**Day 4** – Cultural museum visits and local cuisine food tour.\n"
                "**Day 5** – Leisure morning, checkout, and departure."
            )
        if "hotel" in p or "accommodation" in p:
            return (
                "**Budget:** City Hostel Central (from $25/night, 4.2★)\n"
                "**Mid-range:** Comfort Inn Downtown (from $80/night, 4.5★)\n"
                "**Luxury:** Grand Palace Hotel (from $200/night, 4.9★)"
            )
        if "weather" in p:
            return "Expected weather: Mild temperatures 18–24 °C, mostly sunny with occasional afternoon showers. Light jacket recommended for evenings."
        if "budget" in p:
            return (
                "Estimated budget breakdown:\n"
                "• Flights: $400–$800 (economy, round-trip)\n"
                "• Accommodation: $50–$150/night\n"
                "• Food: $30–$60/day\n"
                "• Activities: $20–$50/day\n"
                "• Transport: $10–$25/day"
            )
        return "I'm your AI travel assistant powered by IBM Granite. How can I help plan your perfect trip today?"
