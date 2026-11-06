"""
Langflow Orchestration Service
Routes chat messages through a Langflow flow for visual AI orchestration.
Falls back gracefully to direct IBM Granite calls when Langflow is unavailable.

Setup:
    pip install langflow          # or run via Docker (see README)
    Set LANGFLOW_HOST and LANGFLOW_FLOW_ID in your .env file.

Langflow REST API:
    POST {host}/api/v1/run/{flow_id}
    Body: { "input_value": "<message>", "input_type": "chat", "output_type": "chat" }
"""
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class LangflowService:
    """
    Thin client for the Langflow REST API.

    When ``available`` is True the service will attempt to call the configured
    Langflow flow and return its response.  On any error (network, timeout, bad
    config) it returns None so the caller can fall back to IBM Granite.
    """

    def __init__(self, host: str = "", flow_id: str = "", api_key: str = "",
                 timeout: int = 30):
        """
        Parameters
        ----------
        host    : Full base URL of your Langflow instance,
                  e.g. ``http://127.0.0.1:7860`` or a cloud URL.
        flow_id : The UUID of the Langflow flow to run.
                  Found in Langflow UI → flow URL or Settings panel.
        api_key : Optional Langflow API key (required if auth is enabled).
        timeout : HTTP timeout in seconds.
        """
        self.host    = host.rstrip("/")
        self.flow_id = flow_id
        self.api_key = api_key
        self.timeout = timeout

    @property
    def available(self) -> bool:
        """True only when both host and flow_id are configured."""
        return bool(self.host and self.flow_id)

    # ------------------------------------------------------------------ #
    #  Public interface                                                     #
    # ------------------------------------------------------------------ #

    def run_chat(
        self,
        message: str,
        session_id: str = "",
        tweaks: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Send a chat message to the Langflow flow and return the text output.

        Returns the assistant's reply string, or None if unavailable / errored.
        The caller should treat None as a signal to fall back to Granite.

        Parameters
        ----------
        message    : The user's chat message.
        session_id : Optional Langflow session/thread ID for conversation memory.
        tweaks     : Optional dict of component-level overrides sent to the flow
                     (e.g. ``{"ChatInput-abc12": {"input_value": "override"}}``).
        """
        if not self.available:
            logger.debug("LangflowService: not configured — skipping.")
            return None

        url     = f"{self.host}/api/v1/run/{self.flow_id}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        payload: dict = {
            "input_value": message,
            "input_type":  "chat",
            "output_type": "chat",
        }
        if session_id:
            payload["session_id"] = session_id
        if tweaks:
            payload["tweaks"] = tweaks

        try:
            resp = requests.post(url, json=payload, headers=headers,
                                 timeout=self.timeout)
            resp.raise_for_status()
            return self._extract_text(resp.json())
        except requests.exceptions.ConnectionError:
            logger.warning("LangflowService: could not connect to %s — falling back to Granite.", self.host)
        except requests.exceptions.Timeout:
            logger.warning("LangflowService: request timed out after %ds — falling back to Granite.", self.timeout)
        except requests.exceptions.HTTPError as exc:
            logger.warning("LangflowService: HTTP %s from Langflow — falling back to Granite.", exc.response.status_code)
        except Exception as exc:
            logger.warning("LangflowService: unexpected error (%s) — falling back to Granite.", exc)

        return None

    # ------------------------------------------------------------------ #
    #  Response parsing                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_text(data: dict) -> Optional[str]:
        """
        Extract the assistant text from a Langflow /api/v1/run response.

        Langflow wraps the output in a nested structure; this handles both the
        v1.0+ ``outputs`` envelope and older flat formats.
        """
        try:
            # Standard Langflow v1 response shape:
            # { "outputs": [{ "outputs": [{ "results": { "message": { "text": "..." } } }] }] }
            outputs = data.get("outputs", [])
            if outputs:
                inner = outputs[0].get("outputs", [])
                if inner:
                    results = inner[0].get("results", {})
                    msg     = results.get("message", {})
                    text    = msg.get("text") or msg.get("message")
                    if text:
                        return str(text).strip()

            # Fallback: older / custom flows may put the answer at top level
            if "result" in data:
                return str(data["result"]).strip()
            if "text" in data:
                return str(data["text"]).strip()

        except Exception as exc:
            logger.warning("LangflowService: could not parse response — %s", exc)

        return None
