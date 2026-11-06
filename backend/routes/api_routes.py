"""
Flask API routes for the Travel Planner Agent.
"""
import logging
from flask import Blueprint, request, jsonify, current_app

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_agent():
    return current_app.config["TRAVEL_AGENT"]


# ─────────────────────────────  Session  ─────────────────────────────────────

@api_bp.route("/session", methods=["POST"])
def create_session():
    """Create a new planning session."""
    agent      = get_agent()
    session_id = agent.create_session()
    return jsonify({"session_id": session_id, "message": "Session created."})


@api_bp.route("/session/<session_id>", methods=["GET"])
def get_session(session_id):
    agent   = get_agent()
    session = agent.get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session)


@api_bp.route("/session/<session_id>", methods=["PATCH"])
def update_session(session_id):
    agent   = get_agent()
    updates = request.get_json() or {}
    ok      = agent.update_session(session_id, updates)
    if not ok:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({"message": "Session updated."})


# ─────────────────────────  Full Trip Plan  ──────────────────────────────────

@api_bp.route("/plan/full", methods=["POST"])
def full_trip_plan():
    """Generate a complete all-in-one trip plan."""
    data   = request.get_json() or {}
    agent  = get_agent()
    result = agent.full_trip_plan(data)
    session_id = data.get("session_id")
    if session_id:
        agent.update_session(session_id, {
            "destination": result.get("destination"),
            "itinerary":   result.get("plan"),
        })
    return jsonify(result)


# ───────────────────────────  Destinations  ──────────────────────────────────

@api_bp.route("/destinations/suggest", methods=["POST"])
def suggest_destinations():
    """AI-powered destination suggestions."""
    data   = request.get_json() or {}
    agent  = get_agent()
    result = agent.suggest_destinations(data)
    return jsonify(result)


# ─────────────────────────────  Itinerary  ───────────────────────────────────

@api_bp.route("/itinerary/build", methods=["POST"])
def build_itinerary():
    """Generate a day-by-day itinerary."""
    data   = request.get_json() or {}
    agent  = get_agent()
    result = agent.build_itinerary(data)

    # Persist to session if provided
    session_id = data.get("session_id")
    if session_id:
        agent.update_session(session_id, {"itinerary": result["itinerary"],
                                           "destination": result["destination"]})
    return jsonify(result)


# ──────────────────────────  Accommodation  ──────────────────────────────────

@api_bp.route("/accommodation/recommend", methods=["POST"])
def recommend_accommodation():
    data   = request.get_json() or {}
    agent  = get_agent()
    return jsonify(agent.recommend_accommodation(data))


# ─────────────────────────────  Transport  ───────────────────────────────────

@api_bp.route("/transport/recommend", methods=["POST"])
def recommend_transport():
    data   = request.get_json() or {}
    agent  = get_agent()
    return jsonify(agent.recommend_transport(data))


# ──────────────────────────────  Budget  ─────────────────────────────────────

@api_bp.route("/budget/calculate", methods=["POST"])
def calculate_budget():
    data   = request.get_json() or {}
    agent  = get_agent()
    return jsonify(agent.calculate_budget(data))


# ──────────────────────────────  Weather  ────────────────────────────────────

@api_bp.route("/weather/<city>", methods=["GET"])
def get_weather(city):
    agent = get_agent()
    return jsonify(agent.weather.get_current_weather(city))


@api_bp.route("/weather/<city>/forecast", methods=["GET"])
def get_forecast(city):
    days  = request.args.get("days", 5, type=int)
    agent = get_agent()
    return jsonify(agent.weather.get_forecast(city, days))


# ──────────────────────────────  Currency  ───────────────────────────────────

@api_bp.route("/currency/convert", methods=["GET"])
def convert_currency():
    amount   = request.args.get("amount", 100.0, type=float)
    from_cur = request.args.get("from", "USD").upper()
    to_cur   = request.args.get("to", "EUR").upper()
    agent    = get_agent()
    converted = agent.currency.convert(amount, from_cur, to_cur)
    return jsonify({"amount": amount, "from": from_cur, "to": to_cur, "converted": converted})


# ───────────────────────────────  Chat  ──────────────────────────────────────

@api_bp.route("/chat", methods=["POST"])
def chat():
    """Conversational IBM Granite-powered travel assistant."""
    data       = request.get_json() or {}
    message    = data.get("message", "")
    session_id = data.get("session_id", "")
    if not message:
        return jsonify({"error": "Message is required"}), 400
    agent  = get_agent()
    result = agent.chat(session_id, message)
    return jsonify(result)


# ──────────────────────────────  Bookings  ───────────────────────────────────

@api_bp.route("/bookings", methods=["POST"])
def add_booking():
    data       = request.get_json() or {}
    session_id = data.pop("session_id", "")
    agent      = get_agent()
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    return jsonify(agent.add_booking(session_id, data))


# ──────────────────────────────  Alerts  ─────────────────────────────────────

@api_bp.route("/alerts/<destination>", methods=["GET"])
def travel_alerts(destination):
    agent = get_agent()
    return jsonify(agent.get_travel_alerts(destination))


# ───────────────────────  Schedule Optimisation  ─────────────────────────────

@api_bp.route("/schedule/optimize", methods=["POST"])
def optimize_schedule():
    data       = request.get_json() or {}
    session_id = data.get("session_id", "")
    constraints = data.get("constraints", {})
    agent      = get_agent()
    return jsonify(agent.optimize_schedule(session_id, constraints))


# ──────────────────────────────  Health  ─────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health():
    agent = get_agent()
    langflow_enabled = (
        agent.langflow is not None and agent.langflow.available
    )
    return jsonify({
        "status":           "ok",
        "service":          "Travel Planner Agent",
        "model":            "IBM Granite (watsonx.ai)",
        "langflow_enabled": langflow_enabled,
        "chat_engine":      "Langflow → IBM Granite (fallback)" if langflow_enabled else "IBM Granite",
    })
