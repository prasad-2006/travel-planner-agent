"""
Core Travel Planner Agent powered by IBM Granite (watsonx.ai).
Orchestrates destination suggestions, itinerary building, accommodation/transport
recommendations, and booking management.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

def _now():
    return datetime.now(timezone.utc).isoformat()
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
#  Prompt templates
# ──────────────────────────────────────────────────────────────────────────────

DESTINATION_PROMPT = """You are an expert travel consultant. A traveller wants to visit: {destination_query}

Traveller preferences:
- Interests: {interests}
- Budget: {budget} {currency} (total)
- Duration: {duration} days
- Travel style: {travel_style}
- Departing from: {origin}
- Preferred climate: {climate}
- Must avoid: {avoid}

Provide detailed travel information specifically about {destination_query}. Include:
1. Why {destination_query} is a great choice
2. Best areas/neighbourhoods to stay
3. Best time to visit
4. Estimated total cost for {duration} days on a {budget} {currency} budget
5. Top 5 must-see highlights and activities

Be specific, enthusiastic, and focus ONLY on {destination_query}."""


ITINERARY_PROMPT = """You are an expert travel planner. Create a detailed day-by-day itinerary for:
- Destination: {destination}
- Duration: {duration} days
- Start date: {start_date}
- Traveller interests: {interests}
- Budget per day: {daily_budget} {currency}
- Travel style: {travel_style}
- Number of travellers: {travellers}

Create a complete itinerary with:
- Morning, afternoon, and evening activities for each day
- Recommended restaurants for meals
- Estimated costs per day
- Local tips and insider advice
- Transport suggestions between activities

Format clearly with Day 1, Day 2, etc."""


ACCOMMODATION_PROMPT = """You are a travel accommodation expert. Recommend accommodation options for:
- Destination: {destination}
- Check-in: {check_in}
- Check-out: {check_out}
- Travellers: {travellers}
- Budget per night: {budget_per_night} {currency}
- Preferences: {preferences}

Provide 3 accommodation options (budget, mid-range, luxury) with:
1. Hotel/property name
2. Location and neighbourhood description
3. Price per night (approximate)
4. Star rating and guest score
5. Key amenities
6. Why it suits these travellers"""


TRANSPORT_PROMPT = """You are a transport planning expert. Suggest transport options for:
- Origin: {origin}
- Destination: {destination}
- Travel dates: {travel_dates}
- Travellers: {travellers}
- Budget: {budget} {currency} (for transport)
- Preferences: {preferences}

Cover:
1. Flights / long-distance travel options
2. Local transport at the destination (metro, bus, rental car, taxi apps)
3. Recommended booking platforms
4. Money-saving tips
5. Estimated total transport cost"""


FULL_TRIP_PLAN_PROMPT = """You are an expert travel planner powered by IBM Granite. A traveller has provided all their trip details. Create a COMPLETE, detailed trip plan covering everything from departure to return.

TRIP DETAILS:
- Destination: {destination}
- Departing From: {origin}
- Travel Dates: {start_date} to {end_date} ({duration} nights)
- Number of Travellers: {travellers}
- Total Budget: {total_budget} {currency}
- Hotel / Accommodation Budget per night: {hotel_budget} {currency}
- Daily Spending Budget (food + activities): {daily_budget} {currency}
- Travel Style: {travel_style}
- Interests: {interests}
- Dietary Requirements: {dietary}
- Special Requests / Notes: {special_requests}

LIVE DATA (use this real information in your plan — do not guess or override):
🌤️ LIVE WEATHER: {weather_context}
💱 LIVE EXCHANGE RATES: {rates_context}
🌍 COUNTRY FACTS: {country_context}
📖 DESTINATION INFO: {destination_info}

Produce a COMPLETE trip plan with these sections:

## ✈️ FLIGHTS & GETTING THERE
- Recommended flight options (airlines, approximate fares, flight duration)
- Best booking platforms and tips to save money
- Airport transfer advice on arrival

## 🏨 ACCOMMODATION
- 3 hotel/accommodation recommendations matching the {hotel_budget} {currency}/night budget (budget, mid-range, best value)
- For each: name, neighbourhood, estimated price per night, key features, why it suits this traveller
- Check-in/check-out tips

## 📅 DAY-BY-DAY ITINERARY
Create a full day-by-day plan for all {duration} days covering:
- Morning, Afternoon, Evening activities
- Recommended restaurants for breakfast, lunch, dinner with estimated costs
- Entry fees and booking tips for attractions
- Local transport between locations

## 💰 BUDGET BREAKDOWN
Provide an itemised budget table using LIVE EXCHANGE RATES above:
- Flights (estimated)
- Accommodation ({duration} nights × {hotel_budget} {currency})
- Food & Dining ({duration} days)
- Activities & Entrance Fees
- Local Transport
- Shopping / Souvenirs
- Emergency Fund (10%)
- TOTAL vs available budget of {total_budget} {currency}

## 🌍 PRACTICAL TRAVEL TIPS
Use the COUNTRY FACTS above to provide accurate tips:
- Visa & entry requirements
- Local currency, payment tips, and tipping culture
- Best local transport options (metro, taxi apps, rental)
- Safety advice and emergency numbers (from COUNTRY FACTS)
- Must-try local foods and drinks
- Packing essentials for this destination and LIVE WEATHER conditions
- Electricity / plug type information

## ⚠️ TRAVEL ALERTS
- Current advisories if any
- Health requirements or vaccinations
- Weather outlook based on LIVE WEATHER DATA above

Make the plan specific, practical, and actionable. Use {currency} for all prices. Reference the LIVE DATA wherever relevant."""


STRUCTURED_DATA_PROMPT = """Based on this trip:
- Destination: {destination}
- From: {origin}
- Dates: {start_date} to {end_date} ({duration} nights)
- Travellers: {travellers}
- Total Budget: {total_budget} {currency}
- Hotel Budget/night: {hotel_budget} {currency}
- Daily Budget: {daily_budget} {currency}
- Interests: {interests}
- Travel Style: {travel_style}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:
{{
  "flights": [
    {{"airline": "Airline Name", "route": "City A to City B", "duration": "Xh Ym", "price": 000, "stops": "Nonstop"}},
    {{"airline": "Airline Name", "route": "City A to City B", "duration": "Xh Ym", "price": 000, "stops": "1 stop"}}
  ],
  "hotels": [
    {{"name": "Hotel Name", "type": "Budget", "price_per_night": 00, "rating": 4.2, "neighbourhood": "Area Name", "highlight": "Key feature"}},
    {{"name": "Hotel Name", "type": "Mid-range", "price_per_night": 00, "rating": 4.5, "neighbourhood": "Area Name", "highlight": "Key feature"}},
    {{"name": "Hotel Name", "type": "Best Value", "price_per_night": 00, "rating": 4.7, "neighbourhood": "Area Name", "highlight": "Key feature"}}
  ],
  "budget": {{
    "flights": 000,
    "accommodation": 000,
    "food": 000,
    "activities": 000,
    "transport": 000,
    "shopping": 000,
    "emergency": 000,
    "total": 000,
    "available": {total_budget}
  }}
}}
Return ONLY the JSON. No markdown fences, no extra text."""


ITINERARY_PROMPT_SIMPLE = """Create a detailed day-by-day travel itinerary.

Trip details:
- Destination: {destination}
- Duration: {duration} days
- Start date: {start_date}
- Interests: {interests}
- Travel style: {travel_style}
- Daily budget: {daily_budget} {currency}

OUTPUT FORMAT — follow this exactly for every day, no deviations:

DAY 1 | [Theme for Day 1]
MORNING: [Specific morning activity with real place name in {destination}]
AFTERNOON: [Specific afternoon activity with real place name in {destination}]
EVENING: [Specific restaurant or evening activity with real name in {destination}]

DAY 2 | [Theme for Day 2]
MORNING: [Specific morning activity with real place name in {destination}]
AFTERNOON: [Specific afternoon activity with real place name in {destination}]
EVENING: [Specific restaurant or evening activity with real name in {destination}]

[Continue exactly this pattern for all {duration} days]

Rules:
- Use REAL names of places, restaurants, landmarks and neighbourhoods in {destination}
- Each day must have a different unique theme
- Every MORNING/AFTERNOON/EVENING line must be on its own line starting with that exact label
- Do NOT add any other text, headers, or explanations"""


CHAT_PROMPT = """You are a travel-only AI assistant powered by IBM Granite. Your sole purpose is to help users with travel-related topics.

STRICT RULES:
1. You ONLY answer questions about travel, tourism, trips, destinations, flights, hotels, transportation, itineraries, travel budgets, visas, packing, local culture, food, weather at destinations, and travel safety.
2. If the user asks about ANYTHING unrelated to travel (e.g. coding, math, politics, health advice, personal relationships, finance, entertainment, sports scores, etc.), you MUST politely decline and redirect them to travel topics. Example: "I'm a travel-only assistant and can only help with travel-related questions. I'd love to help you plan a trip instead!"
3. Never pretend to be a general assistant. Never answer off-topic questions even if asked nicely or repeatedly.
4. Keep all answers focused, practical, and travel-relevant.
5. When answering about weather, exchange rates, or current conditions — use the LIVE DATA provided below. Do not guess or use outdated information.
6. NEVER fabricate or guess specific details you cannot verify in real-time, including:
   - Phone numbers, email addresses, or direct contact details for hotels, airlines, or businesses
   - Exact current prices, tariffs, or availability
   - Specific booking URLs or reservation links
   - Visa fees, processing times, or entry requirements that change frequently
   Instead, tell the user WHERE to find this information (e.g. "Check the hotel's official website", "Visit the embassy website for current visa fees", "Use Google Flights or Skyscanner for live prices").
7. When giving approximate prices, budgets, or typical costs, always clearly state they are ESTIMATES based on general knowledge, not real-time data. Use phrases like "typically around", "estimated", "usually costs".
8. For hotel or restaurant recommendations, name well-known places but always add: "Please verify details and book directly through their official website or a trusted booking platform like Booking.com or TripAdvisor."

TODAY'S DATE: {today}

LIVE WEATHER DATA (fetched right now):
{weather_context}

LIVE EXCHANGE RATES (fetched right now, base: {currency}):
{rates_context}

LIVE COUNTRY & DESTINATION FACTS (fetched right now):
{country_context}

LIVE TOP ATTRACTIONS (fetched right now):
{attractions_context}

Current trip context:
- Destination: {destination}
- Trip dates: {dates}
- Budget: {budget} {currency}
- Interests: {interests}

Conversation history:
{history}

User: {user_message}
Assistant:"""


BUDGET_PROMPT = """You are a travel budget analyst. Create a detailed budget breakdown for:
- Destination: {destination}
- Duration: {duration} days
- Total budget: {total_budget} {currency}
- Travellers: {travellers}
- Travel style: {travel_style}

Provide:
1. Budget allocation table (flights, accommodation, food, activities, transport, shopping, emergency)
2. Daily spending limit
3. Money-saving tips specific to this destination
4. Best currency exchange advice
5. Budget alerts to watch out for"""


# ──────────────────────────────────────────────────────────────────────────────
#  Agent class
# ──────────────────────────────────────────────────────────────────────────────

class TravelPlannerAgent:
    """Main AI agent that orchestrates all travel planning tasks using IBM Granite."""

    def __init__(self, granite_service, weather_service, currency_service,
                 amadeus_service=None, places_service=None, visa_service=None,
                 destination_service=None, langflow_service=None):
        self.granite     = granite_service
        self.weather     = weather_service
        self.currency    = currency_service
        self.amadeus     = amadeus_service
        self.places      = places_service
        self.visa        = visa_service
        self.destination = destination_service
        self.langflow    = langflow_service   # optional Langflow orchestration layer
        self._sessions: dict = {}   # in-memory session store

    # ------------------------------------------------------------------ #
    #  Session management                                                   #
    # ------------------------------------------------------------------ #
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "created_at":  datetime.now(timezone.utc).isoformat(),
            "destination": "",
            "dates":       "",
            "budget":      0,
            "currency":    "USD",
            "interests":   [],
            "travellers":  1,
            "history":     [],
            "itinerary":   None,
            "bookings":    [],
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: dict) -> bool:
        if session_id not in self._sessions:
            return False
        self._sessions[session_id].update(updates)
        return True

    # ------------------------------------------------------------------ #
    #  Core agent capabilities                                              #
    # ------------------------------------------------------------------ #
    def suggest_destinations(self, preferences: dict) -> dict:
        """Use IBM Granite to suggest destinations based on user preferences."""
        prompt = DESTINATION_PROMPT.format(
            destination_query = preferences.get("destination_query", "any destination"),
            interests         = ", ".join(preferences.get("interests", ["culture", "food"])),
            budget            = preferences.get("budget", 2000),
            currency          = preferences.get("currency", "USD"),
            duration          = preferences.get("duration", 7),
            travel_style      = preferences.get("travel_style", "balanced"),
            origin            = preferences.get("origin", "Not specified"),
            climate           = preferences.get("climate", "mild"),
            avoid             = preferences.get("avoid", "none"),
        )
        response = self.granite.generate(prompt)
        return {"suggestions": response, "preferences": preferences,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    def build_itinerary(self, params: dict) -> dict:
        """Generate a complete day-by-day itinerary using IBM Granite."""
        destination  = params.get("destination", "Paris")
        duration     = params.get("duration", 5)
        start_date   = params.get("start_date", str(datetime.now(timezone.utc).date()))
        daily_budget = params.get("daily_budget", 150)
        currency     = params.get("currency", "USD")

        prompt = ITINERARY_PROMPT.format(
            destination  = destination,
            duration     = duration,
            start_date   = start_date,
            interests    = ", ".join(params.get("interests", ["sightseeing", "food"])),
            daily_budget = daily_budget,
            currency     = currency,
            travel_style = params.get("travel_style", "balanced"),
            travellers   = params.get("travellers", 1),
        )
        itinerary_text = self.granite.generate(prompt)

        # Enrich with weather data
        weather = self.weather.get_current_weather(destination)
        forecast = self.weather.get_forecast(destination, min(duration, 5))

        # Build end date
        end_date = str((datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration - 1)).date())

        return {
            "destination":     destination,
            "duration":        duration,
            "start_date":      start_date,
            "end_date":        end_date,
            "itinerary":       itinerary_text,
            "weather_current": weather,
            "weather_forecast": forecast,
            "total_budget":    daily_budget * duration,
            "currency":        currency,
            "generated_at":    datetime.now(timezone.utc).isoformat(),
        }

    def recommend_accommodation(self, params: dict) -> dict:
        """Recommend accommodation options using IBM Granite."""
        prompt = ACCOMMODATION_PROMPT.format(
            destination      = params.get("destination", "Paris"),
            check_in         = params.get("check_in", str(datetime.now(timezone.utc).date())),
            check_out        = params.get("check_out", ""),
            travellers       = params.get("travellers", 1),
            budget_per_night = params.get("budget_per_night", 100),
            currency         = params.get("currency", "USD"),
            preferences      = ", ".join(params.get("preferences", ["central location", "wifi"])),
        )
        response = self.granite.generate(prompt)
        return {"recommendations": response, "params": params,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    def recommend_transport(self, params: dict) -> dict:
        """Recommend transport options using IBM Granite."""
        prompt = TRANSPORT_PROMPT.format(
            origin       = params.get("origin", "New York"),
            destination  = params.get("destination", "Paris"),
            travel_dates = params.get("travel_dates", "flexible"),
            travellers   = params.get("travellers", 1),
            budget       = params.get("budget", 500),
            currency     = params.get("currency", "USD"),
            preferences  = ", ".join(params.get("preferences", ["comfort", "value for money"])),
        )
        response = self.granite.generate(prompt)
        return {"recommendations": response, "params": params,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    def calculate_budget(self, params: dict) -> dict:
        """Detailed budget breakdown with currency conversion."""
        prompt = BUDGET_PROMPT.format(
            destination  = params.get("destination", "Paris"),
            duration     = params.get("duration", 7),
            total_budget = params.get("total_budget", 2000),
            currency     = params.get("currency", "USD"),
            travellers   = params.get("travellers", 1),
            travel_style = params.get("travel_style", "balanced"),
        )
        analysis   = self.granite.generate(prompt)
        rates      = self.currency.get_rates(params.get("currency", "USD"))
        currencies = {k: round(params.get("total_budget", 2000) * v, 2)
                      for k, v in rates.items() if k in ["EUR", "GBP", "JPY", "AUD", "CAD"]}
        return {"analysis": analysis, "currency_conversions": currencies,
                "params": params, "generated_at": datetime.now(timezone.utc).isoformat()}

    def _parse_itinerary_from_text(self, text: str, duration: int,
                                    start_date: str, daily_budget: float,
                                    destination: str) -> list:
        """
        Parse itinerary text in DAY N | Title / MORNING: / AFTERNOON: / EVENING: format.
        Robust to extra whitespace, missing labels, or different model output styles.
        """
        import re
        from datetime import datetime as dt, timedelta as td

        def get_date(i):
            try:
                return str((dt.strptime(start_date, "%Y-%m-%d") + td(days=i)).date())
            except Exception:
                return start_date

        def clean(s):
            return s.strip().replace("\n", " ").strip()[:200] if s else ""

        days = []

        # Split the whole text into day blocks using DAY N as delimiter
        # Pattern: split on lines that start with "DAY <number>"
        day_sections = re.split(r'(?im)^DAY\s+(\d+)', text)
        # day_sections = [preamble, '1', block1, '2', block2, ...]

        idx = 1
        while idx < len(day_sections) - 1:
            try:
                day_num = int(day_sections[idx].strip())
                block   = day_sections[idx + 1]
                idx += 2
            except (ValueError, IndexError):
                idx += 1
                continue

            if day_num < 1 or day_num > duration + 1:
                continue

            # --- Title: first non-empty line (the "| Theme" part) ---
            lines = [l.strip() for l in block.splitlines()]
            title = ""
            body_start = 0
            for li, line in enumerate(lines):
                if line:
                    # Strip leading pipe/dash
                    candidate = re.sub(r'^[\|\-\s]+', '', line).strip()
                    # Only use as title if it doesn't look like a MORNING/AFTERNOON/EVENING line
                    if candidate and not re.match(r'^(MORNING|AFTERNOON|EVENING)', candidate, re.I):
                        title = candidate[:100]
                        body_start = li + 1
                    break
            if not title:
                # Title-case the destination for display
                dest_display = ' '.join(w.capitalize() for w in destination.split())
                title = f"Day {day_num} in {dest_display}"

            body = "\n".join(lines[body_start:])

            # --- Extract time-of-day slots ---
            def extract_slot(label, src):
                # Match "MORNING: text" until next slot or end
                m = re.search(
                    rf'(?im)^{label}[:\s]+(.+?)(?=\n(?:MORNING|AFTERNOON|EVENING)|$)',
                    src, re.DOTALL
                )
                if m:
                    return clean(m.group(1))
                return ""

            morning   = extract_slot("MORNING",   body)
            afternoon = extract_slot("AFTERNOON", body)
            evening   = extract_slot("EVENING",   body)

            # Fallback: use non-empty lines in order if labels not found
            if not (morning or afternoon or evening):
                non_empty = [l for l in lines[body_start:] if l and not re.match(
                    r'^(MORNING|AFTERNOON|EVENING)', l, re.I)]
                morning   = clean(non_empty[0]) if len(non_empty) > 0 else f"Explore {destination}"
                afternoon = clean(non_empty[1]) if len(non_empty) > 1 else "Visit local landmarks"
                evening   = clean(non_empty[2]) if len(non_empty) > 2 else "Dinner at local restaurant"

            days.append({
                "day":       day_num,
                "date":      get_date(day_num - 1),
                "title":     title,
                "morning":   morning   or f"Explore {destination}",
                "afternoon": afternoon or "Visit local landmarks",
                "evening":   evening   or "Dinner at local restaurant",
                "est_cost":  round(daily_budget),
            })

        # Fill any missing days
        days.sort(key=lambda x: x["day"])
        existing = {d["day"] for d in days}
        dest_display = ' '.join(w.capitalize() for w in destination.split())
        for n in range(1, duration + 1):
            if n not in existing:
                days.append({
                    "day":       n,
                    "date":      get_date(n - 1),
                    "title":     f"Day {n} in {dest_display}",
                    "morning":   f"Explore {destination}",
                    "afternoon": "Visit local landmarks and museums",
                    "evening":   "Dinner at a recommended local restaurant",
                    "est_cost":  round(daily_budget),
                })
        days.sort(key=lambda x: x["day"])
        return days[:duration]

    def _gather_live_context(self, destination: str, currency: str) -> dict:
        """Fetch all live data for a destination. Returns a context dict."""
        ctx = {
            "weather":         {},
            "forecast":        [],
            "rates":           {},
            "country_facts":   "",
            "destination_info":"",
        }

        # Live weather (wttr.in — no key needed)
        try:
            ctx["weather"]  = self.weather.get_current_weather(destination)
            ctx["forecast"] = self.weather.get_forecast(destination, 5)
        except Exception as e:
            logger.warning("Weather fetch failed: %s", e)

        # Live exchange rates (frankfurter.app — no key needed)
        try:
            ctx["rates"] = self.currency.get_rates(currency)
        except Exception as e:
            logger.warning("Currency fetch failed: %s", e)

        # Curated country facts (visa_service — no key needed)
        if self.visa:
            try:
                ctx["country_facts"] = self.visa.format_for_prompt(destination)
            except Exception as e:
                logger.warning("Visa/country facts failed: %s", e)

        # Wikipedia + Nominatim + REST Countries (destination_service — no key needed)
        if self.destination:
            try:
                ctx["destination_info"] = self.destination.format_for_prompt(destination)
            except Exception as e:
                logger.warning("Destination enrichment failed: %s", e)

        return ctx

    def full_trip_plan(self, params: dict) -> dict:
        """Generate a complete all-in-one trip plan using IBM Granite + structured visual data."""
        from datetime import datetime as dt, timedelta
        start_date   = params.get("start_date", str(datetime.now(timezone.utc).date()))
        duration     = int(params.get("duration", 7))
        try:
            end_date = str((dt.strptime(start_date, "%Y-%m-%d") + timedelta(days=duration)).date())
        except ValueError:
            end_date = "TBD"

        total_budget = float(params.get("total_budget", 2000))
        hotel_budget = float(params.get("hotel_budget", 100))
        daily_budget = float(params.get("daily_budget", total_budget / max(duration, 1) - hotel_budget))
        currency     = params.get("currency", "USD")
        destination  = params.get("destination", "Paris, France")
        origin       = params.get("origin", "Not specified")
        interests    = ", ".join(params.get("interests", ["culture", "food"]))
        travel_style = params.get("travel_style", "balanced")

        # ── Gather all live data upfront ──────────────────────────────────
        ctx = self._gather_live_context(destination, currency)
        weather = ctx["weather"]

        # Format weather context for prompt
        weather_str = "Weather data unavailable."
        if weather.get("temperature") is not None:
            weather_str = (
                f"Current weather in {destination}: {weather.get('description')}, "
                f"{weather.get('temperature')}°C (feels like {weather.get('feels_like')}°C), "
                f"humidity {weather.get('humidity')}%, wind {weather.get('wind_speed')} m/s. "
                f"Source: {weather.get('source', 'live')}"
            )
            if ctx["forecast"]:
                fc = ctx["forecast"][:3]
                fc_lines = ", ".join(
                    f"{f['date']}: {f['description']} {f['temp_min']}–{f['temp_max']}°C"
                    for f in fc
                )
                weather_str += f"\nForecast: {fc_lines}"

        # Format rates context for prompt
        rates = ctx["rates"]
        top_currencies = ["EUR", "GBP", "JPY", "AUD", "CAD", "INR", "AED", "CHF", "SGD", "THB"]
        rate_lines = [f"1 {currency} = {rates[c]:.4f} {c}" for c in top_currencies if c in rates and c != currency]
        rates_str  = "\n".join(rate_lines[:8]) if rate_lines else "Exchange rate data unavailable."

        shared = dict(
            destination  = destination,
            origin       = origin,
            start_date   = start_date,
            end_date     = end_date,
            duration     = duration,
            travellers   = params.get("travellers", 1),
            total_budget = total_budget,
            hotel_budget = hotel_budget,
            daily_budget = round(daily_budget, 0),
            currency     = currency,
            travel_style = travel_style,
            interests    = interests,
        )

        # 1. Full narrative plan — inject real live data into prompt
        plan_prompt = FULL_TRIP_PLAN_PROMPT.format(
            **shared,
            dietary          = params.get("dietary", "No restrictions"),
            special_requests = params.get("special_requests", "None"),
            weather_context  = weather_str,
            rates_context    = rates_str,
            country_context  = ctx["country_facts"] or f"Country facts for {destination} unavailable.",
            destination_info = ctx["destination_info"] or f"Destination info for {destination} unavailable.",
        )
        plan = self.granite.generate(plan_prompt, max_tokens=2000)

        # 2. Generate focused day-by-day itinerary using simple structured prompt
        itinerary_raw = self.granite.generate(
            ITINERARY_PROMPT_SIMPLE.format(
                destination  = destination,
                duration     = duration,
                start_date   = start_date,
                interests    = interests,
                travel_style = travel_style,
                daily_budget = round(daily_budget, 0),
                currency     = currency,
            ),
            max_tokens=1800,
        )
        parsed_itinerary = self._parse_itinerary_from_text(
            itinerary_raw, duration, start_date, daily_budget, destination
        )
        logger.info("Parsed %d/%d itinerary days from AI", len(parsed_itinerary), duration)

        # 3. Budget calculations
        accom_cost    = round(hotel_budget * duration)
        food_cost     = round(daily_budget * 0.55 * duration)
        activity_cost = round(daily_budget * 0.30 * duration)
        transport_cost= round(daily_budget * 0.10 * duration)
        flight_est    = max(0, round((total_budget - accom_cost - food_cost - activity_cost - transport_cost - total_budget * 0.10) * 0.7))
        shopping_est  = round(total_budget * 0.05)
        emergency     = round(total_budget * 0.10)
        total_est     = round(flight_est + accom_cost + food_cost + activity_cost + transport_cost + shopping_est + emergency)

        # 4. Build real tips from country facts
        country_info  = {}
        country_tips  = []
        if self.visa:
            try:
                country_info = self.visa.get_country_info(destination)
            except Exception:
                pass

        if country_info:
            emerg = country_info.get("emergency", {})
            emerg_str = " | ".join(f"{k}: {v}" for k, v in emerg.items()) if emerg else "112"
            country_tips = [
                {"icon": "🛂", "title": "Visa",      "text": f"Check entry requirements for {destination} at your embassy website before travelling."},
                {"icon": "💳", "title": "Currency",  "text": f"Local currency: {country_info.get('currency_name','local currency')} ({country_info.get('currency_code','')} {country_info.get('currency_symbol','')}). {country_info.get('tipping','Tipping varies by region.')}"},
                {"icon": "🔌", "title": "Electricity","text": f"Power: {country_info.get('electricity','Check local standards')}"},
                {"icon": "🌡️", "title": "Weather",   "text": weather_str.split("\n")[0] if weather_str != "Weather data unavailable." else f"Check seasonal weather in {destination} before packing."},
                {"icon": "🚨", "title": "Emergency", "text": f"Emergency numbers: {emerg_str}"},
                {"icon": "🔒", "title": "Safety",    "text": f"Keep copies of your passport. Language: {country_info.get('language','local language')}. Timezone: {country_info.get('timezone','local time')}."},
            ]
        else:
            country_tips = [
                {"icon": "🛂", "title": "Visa",      "text": f"Check entry requirements for {destination} before travelling."},
                {"icon": "💳", "title": "Currency",  "text": f"Carry some local cash; cards widely accepted in {destination}."},
                {"icon": "🚇", "title": "Transport", "text": "Use local metro/bus apps for cheapest city transport."},
                {"icon": "⚕️", "title": "Health",    "text": "Check recommended vaccinations and carry travel insurance."},
                {"icon": "🌡️", "title": "Weather",   "text": weather_str.split("\n")[0] if weather_str != "Weather data unavailable." else f"Research seasonal weather in {destination} before packing."},
                {"icon": "🔒", "title": "Safety",    "text": "Keep copies of your passport; stay aware in crowded areas."},
            ]

        # 5. Try to get hotels & flights from AI JSON (small prompt, best-effort)
        ai_hotels  = []
        ai_flights = []
        try:
            ai_struct = self.granite.generate_json(STRUCTURED_DATA_PROMPT.format(**shared))
            if isinstance(ai_struct.get("hotels"),  list) and ai_struct["hotels"]:
                ai_hotels  = ai_struct["hotels"]
            if isinstance(ai_struct.get("flights"), list) and ai_struct["flights"]:
                ai_flights = ai_struct["flights"]
            if isinstance(ai_struct.get("budget"),  dict) and ai_struct["budget"].get("total", 0) > 0:
                b = ai_struct["budget"]
                accom_cost    = b.get("accommodation", accom_cost)
                food_cost     = b.get("food",          food_cost)
                activity_cost = b.get("activities",    activity_cost)
                transport_cost= b.get("transport",     transport_cost)
                flight_est    = b.get("flights",       flight_est)
                shopping_est  = b.get("shopping",      shopping_est)
                emergency     = b.get("emergency",     emergency)
                total_est     = b.get("total",         total_est)
        except Exception as e:
            logger.warning("AI JSON enrichment skipped: %s", e)

        structured = {
            "flights": ai_flights or [
                {"airline": "Major Airline (Economy)", "route": f"{origin} → {destination}", "duration": "varies", "price": round(flight_est / max(params.get("travellers", 1), 1)), "stops": "1 stop"},
                {"airline": "Budget Airline Option",   "route": f"{origin} → {destination}", "duration": "varies", "price": round(flight_est / max(params.get("travellers", 1), 1) * 0.85), "stops": "1–2 stops"},
            ],
            "hotels": ai_hotels or [
                {"name": f"Budget Hotel – {destination}", "type": "Budget",      "price_per_night": round(hotel_budget * 0.65), "rating": 4.0, "neighbourhood": "City Centre",     "highlight": "Great value, central location"},
                {"name": f"Mid-Range Hotel – {destination}", "type": "Mid-range","price_per_night": round(hotel_budget),        "rating": 4.4, "neighbourhood": "Popular District", "highlight": "Comfort and convenience"},
                {"name": f"Best Value Hotel – {destination}", "type": "Best Value","price_per_night": round(hotel_budget * 1.25),"rating": 4.7, "neighbourhood": "Boutique Area",  "highlight": "Premium amenities, great reviews"},
            ],
            "itinerary": parsed_itinerary,   # real AI-generated unique activities per day
            "budget": {
                "flights":       round(flight_est),
                "accommodation": round(accom_cost),
                "food":          round(food_cost),
                "activities":    round(activity_cost),
                "transport":     round(transport_cost),
                "shopping":      round(shopping_est),
                "emergency":     round(emergency),
                "total":         round(total_est),
                "available":     round(total_budget),
            },
            "tips": country_tips,
        }

        currencies = {k: round(total_budget * v, 2)
                      for k, v in rates.items() if k in ["EUR", "GBP", "JPY", "AUD", "CAD", "INR"]}

        return {
            "plan":                 plan,
            "structured":           structured,
            "destination":          destination,
            "origin":               origin,
            "start_date":           start_date,
            "end_date":             end_date,
            "duration":             duration,
            "travellers":           params.get("travellers", 1),
            "total_budget":         total_budget,
            "hotel_budget":         hotel_budget,
            "daily_budget":         round(daily_budget, 0),
            "currency":             currency,
            "weather":              weather,
            "currency_conversions": currencies,
            "generated_at":         datetime.now(timezone.utc).isoformat(),
        }

    def chat(self, session_id: str, message: str) -> dict:
        """Conversational travel assistant using IBM Granite."""
        session = self.get_session(session_id)
        if session is None:
            session_id = self.create_session()
            session    = self.get_session(session_id)

        history_text = ""
        for turn in session["history"][-6:]:
            history_text += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"

        destination = session.get("destination") or ""
        currency    = session.get("currency", "USD")
        today_str   = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

        # ── Gather all live data via shared helper ─────────────────────────
        if destination:
            ctx = self._gather_live_context(destination, currency)
        else:
            ctx = {"weather": {}, "forecast": [], "rates": {}, "country_facts": "", "destination_info": ""}

        # Format weather context
        w = ctx["weather"]
        if w.get("temperature") is not None:
            weather_context = (
                f"Location: {w.get('city', destination)}, {w.get('country', '')}\n"
                f"Temperature: {w.get('temperature')}°C (feels like {w.get('feels_like')}°C)\n"
                f"Condition: {w.get('description')}\n"
                f"Humidity: {w.get('humidity')}%  |  Wind: {w.get('wind_speed')} m/s\n"
                f"Source: {w.get('source', 'live')} | Fetched: {w.get('fetched_at', 'just now')}"
            )
            if ctx["forecast"]:
                fc_lines = ", ".join(
                    f"{f['date']}: {f['description']} {f['temp_min']}–{f['temp_max']}°C"
                    for f in ctx["forecast"][:4]
                )
                weather_context += f"\n5-day forecast: {fc_lines}"
        else:
            weather_context = ("No destination set yet — weather data will appear once "
                               "a destination is chosen.") if not destination else \
                              f"Live weather for {destination} currently unavailable."

        # Format rates context
        rates = ctx["rates"]
        if rates:
            top   = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "INR", "CHF", "SGD", "AED"]
            lines = [f"1 {currency} = {rates[c]:.4f} {c}" for c in top if c in rates and c != currency]
            rates_context = "\n".join(lines[:8]) if lines else "Rates unavailable."
        else:
            rates_context = "Exchange rate data unavailable."

        # Country facts context (curated)
        country_context = ctx.get("country_facts") or (
            "No destination set yet." if not destination else f"Country data for {destination} unavailable."
        )

        # Destination info context (Wikipedia + REST Countries)
        dest_info = ctx.get("destination_info") or ""

        # Attractions context (OpenTripMap if key set, otherwise skip)
        attractions_context = "Attractions API not configured (set OPENTRIPMAP_API_KEY for live data)."
        if destination and self.places and self.places.available:
            try:
                attractions = self.places.get_attractions(destination, limit=8)
                if attractions:
                    lines = [f"• {a['name']} ({a['kinds']}) — {a['distance']}km from centre"
                             for a in attractions[:8] if a.get("name")]
                    attractions_context = "\n".join(lines) if lines else "No attractions found."
            except Exception:
                attractions_context = f"Attractions data for {destination} unavailable."
        elif destination and dest_info:
            attractions_context = f"See destination info: {dest_info}"
        # ───────────────────────────────────────────────────────────────────

        prompt = CHAT_PROMPT.format(
            today               = today_str,
            weather_context     = weather_context,
            rates_context       = rates_context,
            country_context     = country_context,
            attractions_context = attractions_context,
            destination  = destination or "Not yet decided",
            dates        = session.get("dates")   or "Not yet decided",
            budget       = session.get("budget")  or "Not specified",
            currency     = currency,
            interests    = ", ".join(session.get("interests") or ["travel"]),
            history      = history_text or "No previous conversation.",
            user_message = message,
        )
        # ── Try Langflow first; fall back to direct Granite if unavailable ──
        response = None
        if self.langflow and self.langflow.available:
            response = self.langflow.run_chat(message, session_id=session_id)
            if response:
                logger.info("Chat response served by Langflow.")
            else:
                logger.info("Langflow unavailable or returned no response — falling back to IBM Granite.")

        if response is None:
            response = self.granite.generate(prompt, max_tokens=800)

        # Persist turn to session
        session["history"].append({"user": message, "assistant": response,
                                   "timestamp": datetime.now(timezone.utc).isoformat()})
        self.update_session(session_id, {"history": session["history"]})

        return {"response": response, "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()}

    def add_booking(self, session_id: str, booking: dict) -> dict:
        """Record a booking and return a confirmation."""
        session = self.get_session(session_id)
        if session is None:
            return {"error": "Session not found"}

        booking["id"]     = str(uuid.uuid4())[:8].upper()
        booking["status"] = "Confirmed"
        booking["added_at"] = datetime.now(timezone.utc).isoformat()

        session["bookings"].append(booking)
        self.update_session(session_id, {"bookings": session["bookings"]})
        return {"booking": booking, "message": f"Booking {booking['id']} confirmed!"}

    def get_travel_alerts(self, destination: str) -> dict:
        """Generate travel alerts and tips using IBM Granite."""
        prompt = (
            f"Provide current practical travel alerts and tips for {destination}. Include:\n"
            "1. Safety and security advice\n2. Health requirements (vaccinations, etc.)\n"
            "3. Entry requirements (visa, passport validity)\n4. Local customs and etiquette\n"
            "5. Scam awareness\n6. Emergency numbers\nKeep it concise and practical."
        )
        alerts = self.granite.generate(prompt, max_tokens=600)
        return {"destination": destination, "alerts": alerts,
                "generated_at": datetime.now(timezone.utc).isoformat()}

    def optimize_schedule(self, session_id: str, constraints: dict) -> dict:
        """Re-optimize an existing itinerary based on new constraints."""
        session = self.get_session(session_id)
        if not session or not session.get("itinerary"):
            return {"error": "No itinerary found for this session."}

        prompt = (
            f"The traveller has new constraints: {json.dumps(constraints)}.\n"
            f"Original itinerary:\n{session['itinerary']}\n\n"
            "Please optimise and adjust the itinerary to accommodate these changes. "
            "Highlight what changed and why."
        )
        updated = self.granite.generate(prompt)
        self.update_session(session_id, {"itinerary": updated})
        return {"updated_itinerary": updated, "constraints": constraints,
                "generated_at": datetime.now(timezone.utc).isoformat()}
