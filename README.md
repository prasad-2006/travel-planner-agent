# ✈️ TravelAI — IBM Granite Travel Planner

> An AI-powered travel planning assistant built on **IBM Granite (watsonx.ai)** with real live data — no extra API keys required to run.

---

## 🌟 Features

| Feature | Description |
|---|---|
| **Full Trip Planner** | Destination, flights, hotels, day-by-day itinerary, budget — all in one form |
| **Real Day-by-Day Itinerary** | AI generates unique activities per day with real place names |
| **Live Weather** | Real-time weather + 5-day forecast via **wttr.in** (no key needed) |
| **Live Exchange Rates** | ECB official rates via **frankfurter.app** (no key needed) |
| **Country Facts** | Currency, language, tipping, electricity, emergency numbers (built-in) |
| **Destination Info** | Wikipedia summaries + OpenStreetMap geocoding (no key needed) |
| **AI Chat** | Travel-only assistant — refuses all non-travel questions |
| **Budget Dashboard** | Visual animated budget breakdown chart |
| **Travel Tips** | Real emergency numbers, actual electricity type, live weather in tips |

---

## 🏗️ Architecture

```
travel-planner-agent/
├── app.py                              # Flask app factory
├── requirements.txt                    # Python dependencies
├── .env.example                        # ← copy this to .env and add your IBM keys
│
├── config/
│   └── config.py                       # All configuration
│
├── backend/
│   ├── agents/
│   │   └── travel_agent.py             # Core AI agent — all prompts + orchestration
│   ├── services/
│   │   ├── granite_service.py          # IBM watsonx.ai / Granite LLM
│   │   ├── weather_service.py          # wttr.in (free) + OpenWeatherMap (optional)
│   │   ├── currency_service.py         # frankfurter.app ECB rates (free)
│   │   ├── destination_service.py      # Wikipedia + Nominatim (free)
│   │   ├── visa_service.py             # Curated country facts (built-in)
│   │   ├── amadeus_service.py          # Live flights/hotels (optional key)
│   │   └── places_service.py          # Attractions (optional key)
│   └── routes/
│       └── api_routes.py               # Flask REST API endpoints
│
└── frontend/
    ├── templates/
    │   ├── index.html                   # Landing page
    │   ├── planner.html                 # Trip planner + visual dashboard
    │   └── chat.html                    # AI chat interface
    └── static/
        ├── css/style.css
        └── js/app.js
```

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd travel-planner-agent
pip install -r requirements.txt
```

### 2. Add your IBM credentials

```bash
cp .env.example .env
```

Open `.env` and fill in **only these 3 lines** — everything else works without keys:

```env
IBM_WATSONX_API_KEY=your_ibm_api_key_here
IBM_WATSONX_PROJECT_ID=your_project_id_here
IBM_WATSONX_URL=https://eu-de.ml.cloud.ibm.com
```

> **How to get IBM keys (free):**
> 1. Create a free account at [cloud.ibm.com](https://cloud.ibm.com)
> 2. Go to **watsonx.ai** → create a project
> 3. **API Key:** IBM Cloud → Manage → Access (IAM) → API Keys → Create
> 4. **Project ID:** watsonx.ai project → Manage tab → copy Project ID

### 3. Run

```bash
python app.py
# → http://localhost:5000
```

---

## 🔑 API Keys Summary

| Key | Required? | Where to Get | What It Unlocks |
|---|---|---|---|
| `IBM_WATSONX_API_KEY` | ✅ Yes | [cloud.ibm.com](https://cloud.ibm.com) → IAM → API Keys | AI trip planning + chat |
| `IBM_WATSONX_PROJECT_ID` | ✅ Yes | watsonx.ai project → Manage tab | AI trip planning + chat |
| `OPENWEATHER_API_KEY` | ❌ Optional | [openweathermap.org/api](https://openweathermap.org/api) | Higher weather quota (wttr.in used if blank) |
| `AMADEUS_API_KEY` + `SECRET` | ❌ Optional | [developers.amadeus.com](https://developers.amadeus.com) | Live real flight & hotel prices |
| `OPENTRIPMAP_API_KEY` | ❌ Optional | [dev.opentripmap.org](https://dev.opentripmap.org) | Live tourist attractions |

**Live data that works with zero extra keys:**
- 🌤️ Weather — [wttr.in](https://wttr.in) (completely free, no registration)
- 💱 Exchange rates — [frankfurter.app](https://frankfurter.app) (ECB official, free)
- 🌍 Country facts — built-in curated database (30+ countries)
- 📖 Destination info — Wikipedia REST API + Nominatim/OpenStreetMap (free)

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/session` | Create planning session |
| `GET` | `/api/session/:id` | Get session |
| `POST` | `/api/plan/full` | Full AI trip plan with visual dashboard |
| `POST` | `/api/chat` | Travel-only AI chat |
| `GET` | `/api/weather/:city` | Live weather |
| `GET` | `/api/weather/:city/forecast` | 5-day forecast |
| `GET` | `/api/currency/convert` | Currency conversion |
| `GET` | `/api/health` | Health check |

---

## 🤖 AI Model

- **Model:** `ibm/granite-4-h-small` on IBM watsonx.ai
- **Region:** Frankfurt (`eu-de.ml.cloud.ibm.com`)
- **Chat restriction:** The AI assistant only answers travel-related questions — it politely declines all off-topic queries

---

## 📄 License

MIT
