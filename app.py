"""
Flask application factory for Travel Planner Agent.
IBM Cloud Lite / IBM Granite integration.
"""
import os
import logging
from flask import Flask, render_template
from flask_cors import CORS

from config.config import config_map
from backend.routes.api_routes import api_bp
from backend.agents.travel_agent import TravelPlannerAgent
from backend.services.granite_service import GraniteService
from backend.services.weather_service import WeatherService
from backend.services.currency_service import CurrencyService
from backend.services.amadeus_service import AmadeusService
from backend.services.places_service import PlacesService
from backend.services.visa_service import VisaService
from backend.services.destination_service import DestinationService


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(env: str = None) -> Flask:
    env = env or os.getenv("FLASK_ENV", "development")
    cfg = config_map.get(env, config_map["default"])

    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static",
    )
    app.config.from_object(cfg)
    CORS(app)

    # ── Initialise IBM services ──────────────────────────────────────────
    granite_svc  = GraniteService(cfg)
    weather_svc  = WeatherService(cfg.OPENWEATHER_API_KEY)
    currency_svc = CurrencyService()

    # ── Initialise live travel data services ─────────────────────────────
    amadeus_svc = AmadeusService(
        api_key    = cfg.AMADEUS_API_KEY,
        api_secret = cfg.AMADEUS_API_SECRET,
        use_sandbox= cfg.AMADEUS_SANDBOX,
    )
    places_svc = PlacesService(api_key=cfg.OPENTRIPMAP_API_KEY)
    visa_svc        = VisaService()          # curated facts — no key needed
    destination_svc = DestinationService()   # Wikipedia + Nominatim + REST Countries

    status_parts = ["IBM Granite ✓", "Weather/wttr.in ✓", "Currency/ECB ✓",
                    "Visa/Country ✓", "Wikipedia/OSM ✓"]
    if amadeus_svc.available:  status_parts.append("Amadeus ✓")
    else:                       status_parts.append("Amadeus ✗ (optional)")
    if places_svc.available:   status_parts.append("OpenTripMap ✓")
    else:                       status_parts.append("OpenTripMap ✗ (optional)")
    logger.info("Live data services: %s", " | ".join(status_parts))

    # ── Wire travel agent into app context ───────────────────────────────
    agent = TravelPlannerAgent(
        granite_svc, weather_svc, currency_svc,
        amadeus_service=amadeus_svc,
        places_service=places_svc,
        visa_service=visa_svc,
        destination_service=destination_svc,
    )
    app.config["TRAVEL_AGENT"] = agent

    # ── Blueprints ───────────────────────────────────────────────────────
    app.register_blueprint(api_bp)

    # ── Frontend routes ──────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/planner")
    def planner():
        return render_template("planner.html")

    @app.route("/chat")
    def chat_page():
        return render_template("chat.html")

    logger.info("Travel Planner Agent started. IBM Granite model: %s", cfg.GRANITE_CHAT_MODEL)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
