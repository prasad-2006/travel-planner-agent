"""Data models for Travel Planner Agent."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime, timezone


@dataclass
class TravelPreferences:
    interests:    List[str] = field(default_factory=list)
    budget:       float     = 2000.0
    currency:     str       = "USD"
    duration:     int       = 7
    travel_style: str       = "balanced"   # budget / balanced / luxury
    origin:       str       = ""
    climate:      str       = "mild"
    travellers:   int       = 1
    avoid:        str       = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Booking:
    id:         str  = ""
    type:       str  = ""          # flight / hotel / activity / transfer
    name:       str  = ""
    date:       str  = ""
    status:     str  = "Confirmed"
    price:      float = 0.0
    currency:   str  = "USD"
    reference:  str  = ""
    notes:      str  = ""
    added_at:   str  = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TripPlan:
    session_id:   str           = ""
    destination:  str           = ""
    start_date:   str           = ""
    end_date:     str           = ""
    duration:     int           = 0
    travellers:   int           = 1
    total_budget: float         = 0.0
    currency:     str           = "USD"
    itinerary:    str           = ""
    bookings:     List[Booking] = field(default_factory=list)
    created_at:   str           = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at:   str           = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
