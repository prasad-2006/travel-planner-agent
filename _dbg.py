import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'travel-planner-agent')
import os; os.chdir('travel-planner-agent')
from backend.agents.travel_agent import TravelPlannerAgent

agent = TravelPlannerAgent.__new__(TravelPlannerAgent)

raw = """ No other text.

DAY 1 | Exploring French Revolution History and Architecture
MORNING: Visit Place de la Concorde and the Luxor Obelisk
AFTERNOON: Tour Notre-Dame Cathedral and Sainte-Chapelle
EVENING: Dinner at Le Comptoir du Relais in Saint-Germain

DAY 2 | French Cuisine and Art
MORNING: Guided tour of Versailles Palace
AFTERNOON: Lunch at Laduree for pastries, then visit Musee d'Orsay
EVENING: Dinner at L'Ambroisie, a Michelin 3-star restaurant

DAY 3 | Local Parisian Neighborhoods and Markets
MORNING: Wandering around the Marais and Centre Pompidou
AFTERNOON: Visit Marche des Enfants Rouges market
EVENING: Dinner at Le Moulin Rouge, a historic cabaret
"""

result = agent._parse_itinerary_from_text(raw, 3, '2026-07-15', 150, 'Paris, France')
for d in result:
    print("Day", d["day"], "|", d["title"])
    print("  M:", d["morning"][:80])
    print("  A:", d["afternoon"][:80])
    print("  E:", d["evening"][:80])
    print()
