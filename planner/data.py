"""Curated destination knowledge base used by demo mode (no API key required).

Every destination exposes the same "destination profile" contract that the AI
providers are asked to return, so the itinerary engine treats both identically.

Coordinates are approximate and costs are indicative per-person prices in the
local currency. Always verify opening hours and prices before travelling.

Place tuple:      (name, category, lat, lon, cost, hours, "tags", indoor, description)
Restaurant tuple: (name, lat, lon, cost, tier, cuisine, "tags", description)
"""

from __future__ import annotations

import copy
import re

_IN_EMERGENCY = {"Police": "100 / 112", "Ambulance": "108", "Fire": "101", "Tourist helpline": "1363"}

_RAW = {
    "Goa": {
        "country": "India", "currency": "INR", "center": (15.5300, 73.8000),
        "vibes": ["Beach"], "cost_tier": 1, "good_for": ["Couple", "Friends", "Solo"],
        "best_months": [11, 12, 1, 2, 3], "avoid_months": {6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Late monsoon"},
        "interests": ["Food", "Nightlife", "Adventure", "History", "Nature"],
        "highlights": ["Golden beaches", "Portuguese heritage", "Seafood shacks", "Night markets"],
        "hotel": {"Budget": 2000, "Moderate": 5000, "Luxury": 15000}, "transport_per_km": 25,
        "emergency": _IN_EMERGENCY,
        "places": [
            ("Basilica of Bom Jesus", "history", 15.5009, 73.9116, 0, 1.5, "iconic unesco heritage church", True, "Baroque UNESCO church holding the relics of St Francis Xavier."),
            ("Se Cathedral, Old Goa", "history", 15.5039, 73.9122, 0, 1.0, "heritage church", True, "One of Asia's largest churches, famous for its Golden Bell."),
            ("Fort Aguada & Lighthouse", "history", 15.4925, 73.7737, 0, 1.5, "views sunset heritage", False, "17th-century Portuguese fort with sweeping Arabian Sea views."),
            ("Calangute Beach", "beach", 15.5439, 73.7553, 0, 2.5, "iconic family", False, "Goa's 'Queen of Beaches' — lively sands and shacks."),
            ("Baga Beach Water Sports", "adventure", 15.5553, 73.7517, 1500, 2.0, "watersports adventure", False, "Parasailing, jet-ski and banana-boat rides."),
            ("Anjuna Flea Market", "shopping", 15.5735, 73.7410, 0, 2.0, "market souvenirs", False, "Iconic Wednesday market for crafts, clothes and trinkets."),
            ("Chapora Fort", "history", 15.6060, 73.7366, 0, 1.0, "views sunset", False, "Hilltop ruins overlooking Vagator beach — a classic sunset spot."),
            ("Fontainhas Latin Quarter Walk", "culture", 15.4960, 73.8320, 0, 1.5, "heritage walking art photo", False, "Colourful Portuguese-era lanes, galleries and bakeries in Panaji."),
            ("Sahakari Spice Farm Tour", "nature", 15.4180, 74.0200, 800, 2.5, "family food garden", False, "Guided spice-plantation walk with a traditional Goan lunch."),
            ("Mandovi River Sunset Cruise", "culture", 15.5010, 73.8290, 500, 1.5, "sunset family romantic", False, "Folk dance and music on a relaxed river cruise."),
            ("Dudhsagar Falls Jeep Safari", "adventure", 15.3144, 74.3143, 3000, 6.0, "waterfall nature trek", False, "Full-day jeep safari to the four-tiered 'Sea of Milk' waterfall."),
            ("Vagator Beach", "beach", 15.6010, 73.7340, 0, 2.0, "views", False, "Dramatic red cliffs and quieter sands in North Goa."),
            ("Saturday Night Market, Arpora", "shopping", 15.5600, 73.7640, 0, 2.5, "market evening nightlife food", False, "Weekend night bazaar with live music and street food."),
        ],
        "restaurants": [
            ("Fisherman's Wharf, Panaji", 15.4900, 73.8250, 900, 2, "Goan seafood", "seafood local", "Riverside Goan curries and seafood."),
            ("Mum's Kitchen, Panaji", 15.4990, 73.8180, 800, 2, "Traditional Goan", "local", "Home-style recipes from Goan family kitchens."),
            ("Britto's, Baga", 15.5560, 73.7520, 900, 2, "Seafood & continental", "seafood nightlife", "Beachfront institution that buzzes late."),
            ("Vinayak Family Restaurant, Assagao", 15.5940, 73.7680, 500, 1, "Goan thali", "local seafood", "Legendary no-frills fish thali."),
            ("Bean Me Up, Vagator", 15.5990, 73.7420, 700, 2, "Vegan & vegetarian", "vegetarian vegan", "Leafy garden café with plant-based bowls."),
            ("Thalassa, Siolim", 15.6080, 73.7380, 1800, 3, "Greek", "sunset romantic nightlife", "Clifftop Greek taverna famous for sunsets."),
            ("Gunpowder, Assagao", 15.5960, 73.7660, 1000, 2, "South Indian", "vegetarian local", "Peninsular Indian flavours in an old Goan house."),
        ],
    },
    "Manali": {
        "country": "India", "currency": "INR", "center": (32.2432, 77.1892),
        "vibes": ["Mountains"], "cost_tier": 1, "good_for": ["Couple", "Friends", "Solo", "Family"],
        "best_months": [3, 4, 5, 6, 10], "avoid_months": {1: "Heavy snow, road closures", 2: "Heavy snow, road closures", 7: "Monsoon landslides", 8: "Monsoon landslides"},
        "interests": ["Adventure", "Nature", "Culture", "Wellness"],
        "highlights": ["Snow peaks", "Paragliding", "Old Manali cafés", "Apple orchards"],
        "hotel": {"Budget": 1500, "Moderate": 4000, "Luxury": 12000}, "transport_per_km": 22,
        "emergency": _IN_EMERGENCY,
        "places": [
            ("Hadimba Devi Temple", "culture", 32.2486, 77.1806, 0, 1.0, "iconic temple heritage", False, "Pagoda-style wooden temple in a cedar forest."),
            ("Old Manali Village Walk", "culture", 32.2600, 77.1830, 0, 1.5, "walking photo", False, "Stone houses, apple orchards and hippie cafés."),
            ("Solang Valley Paragliding", "adventure", 32.3166, 77.1570, 3000, 3.0, "iconic adventure views", False, "Tandem paragliding and ropeway with Himalayan views."),
            ("Vashisht Hot Springs", "wellness", 32.2690, 77.1880, 0, 1.0, "hot-springs temple", False, "Natural sulphur springs beside an ancient temple."),
            ("Jogini Waterfall Trek", "nature", 32.2770, 77.1960, 0, 2.5, "trek waterfall views", False, "Easy forest hike to a 150 ft cascade."),
            ("Mall Road", "shopping", 32.2432, 77.1892, 0, 1.5, "market souvenirs family", False, "Bustling high street for woollens and snacks."),
            ("Manu Temple", "culture", 32.2610, 77.1800, 0, 0.75, "temple", False, "Only temple dedicated to sage Manu, above Old Manali."),
            ("Van Vihar Park", "nature", 32.2420, 77.1880, 20, 1.0, "park family", False, "Deodar forest park with boating on the Beas."),
            ("Naggar Castle", "history", 32.1150, 77.1700, 30, 1.5, "heritage views museum", True, "15th-century stone-and-wood castle with valley views."),
            ("Beas River Rafting", "adventure", 32.1700, 77.1650, 1500, 2.0, "watersports adventure", False, "Grade II-III rafting between Pirdi and Jhiri."),
            ("Atal Tunnel & Sissu Day Trip", "nature", 32.4850, 77.1250, 2500, 6.0, "iconic views snow", False, "Drive through the world's longest highway tunnel to Lahaul."),
            ("Tibetan Monastery, Manali", "culture", 32.2440, 77.1870, 0, 0.75, "temple", True, "Colourful Gadhan Thekchhokling Gompa near the bazaar."),
        ],
        "restaurants": [
            ("Johnson's Café", 32.2470, 77.1860, 800, 2, "Continental & trout", "nightlife", "Garden café known for grilled trout."),
            ("Café 1947, Old Manali", 32.2590, 77.1840, 700, 2, "Italian", "riverside nightlife", "Riverside café with live music evenings."),
            ("Chopsticks, Mall Road", 32.2430, 77.1890, 450, 1, "Tibetan", "local", "Momos and thukpa favourite since the 90s."),
            ("Dylan's Toasted & Roasted", 32.2595, 77.1835, 400, 1, "Café", "vegetarian", "Cosy coffee house famous for cookies."),
            ("Il Forno", 32.2480, 77.1810, 700, 2, "Wood-fired pizza", "vegetarian", "Pizzas in a 100-year-old wooden house."),
            ("The Himalayan, Manali", 32.2520, 77.1830, 2500, 3, "Fine dining", "romantic", "Castle-style hotel dining with mountain views."),
        ],
    },
    "Jaipur": {
        "country": "India", "currency": "INR", "center": (26.9124, 75.7873),
        "vibes": ["Cultural"], "cost_tier": 1, "good_for": ["Family", "Couple", "Solo", "Friends"],
        "best_months": [10, 11, 12, 1, 2, 3], "avoid_months": {5: "Extreme heat (45°C)", 6: "Extreme heat (45°C)"},
        "interests": ["History", "Culture", "Shopping", "Food"],
        "highlights": ["Royal forts", "Pink City bazaars", "Rajasthani thalis", "Palaces"],
        "hotel": {"Budget": 1500, "Moderate": 4500, "Luxury": 18000}, "transport_per_km": 20,
        "emergency": _IN_EMERGENCY,
        "places": [
            ("Amber Fort", "history", 26.9855, 75.8513, 200, 3.0, "iconic unesco heritage views", False, "Hilltop fort-palace of red sandstone and mirror halls."),
            ("Hawa Mahal", "history", 26.9239, 75.8267, 50, 1.0, "iconic heritage photo", False, "The 953-window 'Palace of Winds'."),
            ("City Palace", "history", 26.9258, 75.8237, 300, 2.0, "heritage museum", True, "Royal residence with courtyards and museums."),
            ("Jantar Mantar", "history", 26.9248, 75.8246, 50, 1.0, "unesco heritage", False, "18th-century astronomical instruments, UNESCO listed."),
            ("Nahargarh Fort", "history", 26.9374, 75.8155, 50, 1.5, "views sunset", False, "Ridge-top fort with the best sunset over the Pink City."),
            ("Jal Mahal Viewpoint", "landmark", 26.9535, 75.8463, 0, 0.5, "photo", False, "Palace floating in Man Sagar lake."),
            ("Albert Hall Museum", "culture", 26.9118, 75.8195, 40, 1.5, "museum heritage", True, "Indo-Saracenic museum of Rajasthani art."),
            ("Johari & Bapu Bazaar", "shopping", 26.9196, 75.8260, 0, 2.0, "market souvenirs", False, "Gems, block-print textiles and mojari shoes."),
            ("Patrika Gate", "landmark", 26.8420, 75.8040, 0, 0.5, "photo art", False, "Vividly painted gateway — Jaipur's most photogenic arch."),
            ("Galtaji (Monkey Temple)", "culture", 26.9170, 75.8570, 0, 1.0, "temple views", False, "Temple complex with sacred tanks in a gorge."),
            ("Chokhi Dhani Village", "culture", 26.7686, 75.8350, 1100, 3.0, "evening performance family food", False, "Rajasthani village fair with folk shows and dinner."),
            ("Hot-air Balloon over Amber", "adventure", 26.9800, 75.8600, 12000, 2.0, "adventure views luxury", False, "Sunrise flight over forts and villages."),
        ],
        "restaurants": [
            ("Laxmi Misthan Bhandar (LMB)", 26.9200, 75.8240, 500, 1, "Rajasthani vegetarian", "vegetarian local", "Old City classic for thalis and sweets."),
            ("Rawat Mishtan Bhandar", 26.9160, 75.8000, 200, 1, "Snacks", "vegetarian street-food", "Famous for pyaaz kachori."),
            ("Niro's, MI Road", 26.9160, 75.8090, 900, 2, "Indian & continental", "local", "Retro restaurant serving since 1949."),
            ("Spice Court", 26.9130, 75.8050, 800, 2, "Rajasthani", "local", "Laal maas and ker sangri done right."),
            ("1135 AD, Amber Fort", 26.9855, 75.8510, 2500, 3, "Royal Indian", "romantic", "Regal dining inside Amber Fort."),
            ("Suvarna Mahal, Rambagh Palace", 26.8980, 75.8080, 4500, 3, "Royal Indian", "romantic luxury", "Palace ballroom fine-dining."),
            ("Bar Palladio", 26.8985, 75.8090, 2000, 3, "Italian & cocktails", "nightlife vegetarian", "Jewel-toned bar in the Narain Niwas gardens."),
        ],
    },
    "Mumbai": {
        "country": "India", "currency": "INR", "center": (18.9750, 72.8258),
        "vibes": ["Urban", "Cultural"], "cost_tier": 2, "good_for": ["Friends", "Solo", "Couple", "Family"],
        "best_months": [11, 12, 1, 2], "avoid_months": {6: "Heavy monsoon", 7: "Heavy monsoon", 8: "Heavy monsoon"},
        "interests": ["Food", "Nightlife", "History", "Culture", "Shopping"],
        "highlights": ["Colonial architecture", "Street food", "Sea-face promenades", "Bollywood"],
        "hotel": {"Budget": 2500, "Moderate": 7000, "Luxury": 20000}, "transport_per_km": 22,
        "emergency": _IN_EMERGENCY,
        "places": [
            ("Gateway of India", "landmark", 18.9220, 72.8347, 0, 1.0, "iconic heritage photo", False, "1924 arch overlooking the harbour."),
            ("Elephanta Caves", "history", 18.9633, 72.9315, 600, 4.0, "unesco heritage", False, "Rock-cut Shiva temples, by ferry from the Gateway."),
            ("Chhatrapati Shivaji Terminus", "history", 18.9400, 72.8353, 0, 0.75, "unesco heritage photo", False, "Victorian-Gothic railway station, UNESCO listed."),
            ("Marine Drive", "landmark", 18.9440, 72.8230, 0, 1.0, "sunset views walking", False, "The 'Queen's Necklace' promenade."),
            ("CSMVS Museum", "culture", 18.9269, 72.8326, 150, 2.0, "museum heritage", True, "Mumbai's premier museum of art and history."),
            ("Colaba Causeway", "shopping", 18.9150, 72.8250, 0, 1.5, "market souvenirs", False, "Street shopping for jewellery and curios."),
            ("Kala Ghoda Art District", "culture", 18.9280, 72.8320, 0, 1.5, "art walking", False, "Galleries, cafés and heritage buildings."),
            ("Haji Ali Dargah", "culture", 18.9827, 72.8089, 0, 1.0, "temple views", False, "Mosque on an islet reached by a causeway."),
            ("Dhobi Ghat", "culture", 18.9827, 72.8258, 0, 0.5, "photo", False, "World's largest open-air laundry."),
            ("Bandra Fort & Bandstand", "landmark", 19.0420, 72.8190, 0, 1.5, "sunset views", False, "Sea-facing promenade near Bollywood homes."),
            ("Kanheri Caves, Sanjay Gandhi NP", "nature", 19.2060, 72.9060, 200, 3.5, "trek heritage park", False, "Buddhist caves inside a forest national park."),
            ("Juhu Beach", "beach", 19.0988, 72.8267, 0, 1.5, "street-food family sunset", False, "Sunset strolls and pav bhaji stalls."),
            ("Bollywood Studio Tour", "culture", 19.1550, 72.8800, 2500, 3.0, "family", True, "Behind-the-scenes tour of Film City sets."),
        ],
        "restaurants": [
            ("Leopold Café", 18.9226, 72.8316, 900, 2, "Multi-cuisine", "nightlife", "Iconic Colaba café since 1871."),
            ("Britannia & Co.", 18.9345, 72.8380, 800, 2, "Parsi", "local", "Legendary berry pulao (lunch only)."),
            ("Trishna", 18.9295, 72.8318, 2500, 3, "Seafood", "seafood", "Famous butter-garlic crab."),
            ("Swati Snacks", 18.9670, 72.8100, 500, 1, "Gujarati snacks", "vegetarian street-food", "Refined takes on street classics."),
            ("Shree Thaker Bhojanalay", 18.9500, 72.8270, 700, 2, "Gujarati thali", "vegetarian local", "Bottomless vegetarian thalis."),
            ("Bademiya, Colaba", 18.9228, 72.8318, 500, 1, "Kebabs", "street-food nightlife", "Late-night kebab rolls."),
            ("AER, Four Seasons", 19.0000, 72.8250, 3500, 3, "Cocktails & small plates", "nightlife luxury", "Rooftop bar with skyline views."),
        ],
    },
    "Kochi": {
        "country": "India", "currency": "INR", "center": (9.9650, 76.2550),
        "vibes": ["Cultural", "Beach"], "cost_tier": 1, "good_for": ["Couple", "Family", "Solo"],
        "best_months": [10, 11, 12, 1, 2, 3], "avoid_months": {6: "Southwest monsoon", 7: "Southwest monsoon"},
        "interests": ["History", "Culture", "Food", "Nature", "Wellness"],
        "highlights": ["Chinese fishing nets", "Spice trade history", "Kathakali", "Backwaters"],
        "hotel": {"Budget": 1500, "Moderate": 4000, "Luxury": 12000}, "transport_per_km": 20,
        "emergency": _IN_EMERGENCY,
        "places": [
            ("Chinese Fishing Nets", "landmark", 9.9680, 76.2420, 0, 0.75, "iconic sunset photo", False, "Cantilevered nets at Fort Kochi beach."),
            ("Mattancherry (Dutch) Palace", "history", 9.9583, 76.2594, 5, 1.0, "heritage museum", True, "Kerala murals depicting the Ramayana."),
            ("Paradesi Synagogue & Jew Town", "history", 9.9571, 76.2595, 10, 1.0, "heritage", True, "1568 synagogue with hand-painted tiles."),
            ("St Francis Church", "history", 9.9659, 76.2421, 0, 0.5, "heritage church", True, "India's oldest European church."),
            ("Fort Kochi Heritage Walk", "culture", 9.9650, 76.2430, 0, 2.0, "walking art photo", False, "Colonial bungalows, street art and cafés."),
            ("Marine Drive, Ernakulam", "landmark", 9.9800, 76.2760, 0, 1.0, "sunset walking", False, "Waterfront promenade with boat rides."),
            ("Cherai Beach", "beach", 10.1410, 76.1780, 0, 2.5, "family", False, "Golden beach between sea and backwaters."),
            ("Hill Palace Museum", "history", 9.9520, 76.3620, 50, 1.5, "museum heritage", True, "Former royal palace of the Kochi kings."),
            ("Kumbalangi Village Backwaters", "nature", 9.8640, 76.2840, 800, 3.0, "family views", False, "Canoe rides and village life on the backwaters."),
            ("Ayurvedic Massage", "wellness", 9.9640, 76.2450, 1800, 1.5, "spa", True, "Traditional Kerala abhyanga therapy."),
            ("Kathakali Show, Kerala Kathakali Centre", "culture", 9.9640, 76.2440, 500, 2.0, "evening performance", True, "Make-up session and classical dance-drama."),
            ("Alleppey Houseboat Day Cruise", "nature", 9.4981, 76.3388, 6000, 6.0, "iconic views romantic", False, "Full-day backwater cruise on a kettuvallam."),
        ],
        "restaurants": [
            ("Kayees Rahmathulla Café", 9.9580, 76.2580, 300, 1, "Malabar biryani", "local", "Lunchtime biryani institution."),
            ("Fort House Restaurant", 9.9680, 76.2440, 900, 2, "Kerala seafood", "seafood", "Waterside tables, catch of the day."),
            ("Kashi Art Café", 9.9665, 76.2425, 500, 1, "Café", "vegetarian art", "Gallery café with home-baked cakes."),
            ("Saravana Bhavan, MG Road", 9.9780, 76.2800, 300, 1, "South Indian vegetarian", "vegetarian vegan", "Dosas and Kerala sadya."),
            ("History, Brunton Boatyard", 9.9670, 76.2430, 2500, 3, "Heritage Kerala", "romantic seafood", "Recipes from Kochi's trading communities."),
            ("Dal Roti, Fort Kochi", 9.9660, 76.2450, 500, 1, "North Indian", "vegetarian", "Popular for kathi rolls and dal."),
        ],
    },
    "Bali": {
        "country": "Indonesia", "currency": "IDR", "center": (-8.6000, 115.2000),
        "vibes": ["Beach", "Cultural"], "cost_tier": 1, "good_for": ["Couple", "Friends", "Solo", "Family"],
        "best_months": [4, 5, 6, 7, 8, 9], "avoid_months": {1: "Peak wet season", 2: "Peak wet season"},
        "interests": ["Culture", "Nature", "Wellness", "Adventure", "Nightlife"],
        "highlights": ["Temples", "Rice terraces", "Surf beaches", "Spa culture"],
        "hotel": {"Budget": 400000, "Moderate": 1200000, "Luxury": 4500000}, "transport_per_km": 7000,
        "emergency": {"General emergency": "112", "Police": "110", "Ambulance": "118", "Fire": "113"},
        "places": [
            ("Uluwatu Temple", "culture", -8.8291, 115.0849, 50000, 1.5, "iconic temple sunset views", False, "Clifftop sea temple above the Indian Ocean."),
            ("Tegallalang Rice Terraces", "nature", -8.4345, 115.2793, 50000, 1.5, "iconic views photo", False, "Emerald terraces carved into the valley."),
            ("Sacred Monkey Forest, Ubud", "nature", -8.5188, 115.2585, 100000, 1.5, "family temple", False, "Jungle sanctuary home to 1,000+ macaques."),
            ("Tanah Lot", "culture", -8.6212, 115.0868, 75000, 1.5, "iconic temple sunset", False, "Temple perched on a rock in the surf."),
            ("Mount Batur Sunrise Trek", "adventure", -8.2420, 115.3750, 600000, 6.0, "trek views adventure", False, "Pre-dawn hike up an active volcano."),
            ("Seminyak Beach", "beach", -8.6913, 115.1571, 0, 2.5, "sunset", False, "Wide sandy beach lined with beach clubs."),
            ("Tirta Empul Water Temple", "culture", -8.4155, 115.3153, 50000, 1.5, "temple heritage", False, "Holy spring-water purification pools."),
            ("Ubud Art Market", "shopping", -8.5070, 115.2630, 0, 1.5, "market souvenirs art", False, "Handicrafts, sarongs and woodcarvings."),
            ("Campuhan Ridge Walk", "nature", -8.5030, 115.2540, 0, 1.5, "walking views", False, "Easy ridge-top walk through lalang grass."),
            ("Balinese Spa Ritual, Ubud", "wellness", -8.5100, 115.2620, 350000, 2.0, "spa", True, "Traditional massage and flower bath."),
            ("Waterbom Bali", "adventure", -8.7286, 115.1688, 600000, 4.0, "family watersports", False, "Award-winning water park in Kuta."),
            ("Nusa Dua Beach", "beach", -8.8000, 115.2330, 0, 2.5, "family watersports", False, "Calm lagoon waters ideal for snorkelling."),
            ("Kecak Fire Dance, Uluwatu", "culture", -8.8285, 115.0855, 150000, 1.5, "evening performance", False, "Sunset trance-dance performance at the cliff temple."),
        ],
        "restaurants": [
            ("Warung Babi Guling Ibu Oka", -8.5065, 115.2625, 70000, 1, "Balinese", "local", "Famous suckling-pig warung."),
            ("Sari Organik", -8.5000, 115.2580, 120000, 1, "Organic", "vegetarian vegan views", "Café in the middle of rice fields."),
            ("Clear Café, Ubud", -8.5080, 115.2650, 150000, 2, "Healthy fusion", "vegetarian vegan", "Smoothie bowls and raw desserts."),
            ("Potato Head Beach Club", -8.6797, 115.1534, 450000, 3, "Modern", "nightlife sunset luxury", "Iconic beach club with pool and DJs."),
            ("La Favela, Seminyak", -8.6830, 115.1600, 300000, 2, "Mediterranean", "nightlife", "Jungle-themed restaurant turned club."),
            ("Single Fin, Uluwatu", -8.8150, 115.0880, 250000, 2, "Café & bar", "sunset nightlife", "Surf bar perched over the break."),
            ("Jimbaran Bay Seafood", -8.7800, 115.1600, 300000, 2, "Grilled seafood", "seafood sunset romantic", "Candle-lit seafood on the sand."),
        ],
    },
    "Paris": {
        "country": "France", "currency": "EUR", "center": (48.8566, 2.3522),
        "vibes": ["Cultural", "Urban"], "cost_tier": 3, "good_for": ["Couple", "Solo", "Family", "Friends"],
        "best_months": [4, 5, 6, 9, 10], "avoid_months": {},
        "interests": ["Culture", "History", "Food", "Shopping", "Nightlife"],
        "highlights": ["World-class museums", "Cafés & patisseries", "Seine cruises", "Haute couture"],
        "hotel": {"Budget": 90, "Moderate": 190, "Luxury": 600}, "transport_per_km": 2.0,
        "emergency": {"General emergency": "112", "Medical (SAMU)": "15", "Police": "17", "Fire": "18"},
        "places": [
            ("Eiffel Tower", "landmark", 48.8584, 2.2945, 29, 2.0, "iconic views romantic", False, "Summit views over the city of light."),
            ("Louvre Museum", "culture", 48.8606, 2.3376, 22, 3.0, "iconic museum art", True, "Home of the Mona Lisa and 35,000 works."),
            ("Musée d'Orsay", "culture", 48.8600, 2.3266, 16, 2.0, "museum art", True, "Impressionist masterpieces in a Beaux-Arts station."),
            ("Notre-Dame Cathedral", "history", 48.8530, 2.3499, 0, 1.0, "iconic heritage church", True, "Gothic masterpiece, restored and reopened."),
            ("Montmartre & Sacré-Cœur", "culture", 48.8867, 2.3431, 0, 2.0, "views art walking", False, "Artists' hill with a white-domed basilica."),
            ("Seine River Cruise", "landmark", 48.8640, 2.3060, 17, 1.0, "sunset romantic family", False, "Glide past the city's landmarks by boat."),
            ("Arc de Triomphe & Champs-Élysées", "landmark", 48.8738, 2.2950, 16, 1.5, "views shopping", False, "Rooftop panorama over the twelve avenues."),
            ("Le Marais Walk", "culture", 48.8590, 2.3620, 0, 2.0, "walking shopping heritage", False, "Medieval lanes, boutiques and falafel."),
            ("Luxembourg Gardens", "nature", 48.8462, 2.3372, 0, 1.0, "park garden family", False, "Formal gardens, fountains and toy sailboats."),
            ("Sainte-Chapelle", "history", 48.8554, 2.3450, 13, 1.0, "heritage church", True, "Breathtaking 13th-century stained glass."),
            ("Palace of Versailles", "history", 48.8049, 2.1204, 21, 6.0, "iconic unesco heritage garden", True, "Full-day trip to the Sun King's palace and gardens."),
            ("Marché des Enfants Rouges", "food", 48.8628, 2.3620, 0, 1.0, "market street-food", True, "Paris's oldest covered market."),
            ("Galeries Lafayette Rooftop", "shopping", 48.8738, 2.3320, 0, 1.5, "shopping views luxury", True, "Art-nouveau dome and free rooftop terrace."),
            ("Moulin Rouge Show", "nightlife", 48.8841, 2.3322, 120, 2.0, "evening performance", True, "The original cabaret, can-can and all."),
        ],
        "restaurants": [
            ("Bouillon Chartier", 48.8720, 2.3440, 20, 1, "Classic French", "local", "Belle-époque canteen with bargain prices."),
            ("L'As du Fallafel", 48.8574, 2.3590, 12, 1, "Middle Eastern", "vegetarian street-food", "The Marais' famous falafel pitta."),
            ("Le Relais de l'Entrecôte", 48.8540, 2.3330, 35, 2, "Steak frites", "local", "One dish, done perfectly."),
            ("Café de Flore", 48.8541, 2.3326, 30, 2, "Café", "local", "Literary café of Saint-Germain."),
            ("Le Comptoir du Relais", 48.8520, 2.3390, 45, 2, "Bistro", "local", "Beloved Saint-Germain bistro."),
            ("Le Train Bleu", 48.8443, 2.3740, 85, 3, "Fine French", "romantic luxury", "Opulent dining room in Gare de Lyon."),
            ("Le Syndicat Cocktail Club", 48.8710, 2.3550, 18, 2, "Cocktail bar", "nightlife", "All-French spirits cocktail bar."),
        ],
    },
    "Tokyo": {
        "country": "Japan", "currency": "JPY", "center": (35.6812, 139.7671),
        "vibes": ["Urban", "Cultural"], "cost_tier": 3, "good_for": ["Solo", "Couple", "Friends", "Family"],
        "best_months": [3, 4, 10, 11], "avoid_months": {6: "Rainy season (tsuyu)", 8: "Hot, humid & typhoons"},
        "interests": ["Food", "Culture", "Shopping", "Nightlife", "History"],
        "highlights": ["Neon districts", "Shrines & temples", "Sushi & ramen", "Pop culture"],
        "hotel": {"Budget": 9000, "Moderate": 20000, "Luxury": 65000}, "transport_per_km": 250,
        "emergency": {"Police": "110", "Ambulance / Fire": "119", "Visitor hotline": "+81-50-3816-2787"},
        "places": [
            ("Senso-ji Temple, Asakusa", "culture", 35.7148, 139.7967, 0, 1.5, "iconic temple heritage", False, "Tokyo's oldest temple and Nakamise street."),
            ("Shibuya Crossing & Sky", "landmark", 35.6595, 139.7005, 2500, 1.5, "iconic views photo", False, "The world's busiest crossing from above."),
            ("Meiji Shrine", "culture", 35.6764, 139.6993, 0, 1.5, "temple park", False, "Forest shrine to Emperor Meiji."),
            ("teamLab Planets", "culture", 35.6491, 139.7898, 3800, 2.0, "art family", True, "Immersive digital-art museum."),
            ("Tsukiji Outer Market", "food", 35.6655, 139.7707, 0, 1.5, "market street-food", False, "Fresh sushi, tamago and street bites."),
            ("Tokyo Skytree", "landmark", 35.7101, 139.8107, 3100, 1.5, "views family", True, "634 m broadcast tower with observation decks."),
            ("Shinjuku Gyoen", "nature", 35.6852, 139.7100, 500, 1.5, "garden park", False, "Elegant gardens, famous for cherry blossoms."),
            ("Akihabara Electric Town", "shopping", 35.6984, 139.7731, 0, 2.0, "souvenirs", True, "Anime, manga and electronics paradise."),
            ("Harajuku & Takeshita Street", "shopping", 35.6717, 139.7036, 0, 1.5, "street-food", False, "Youth fashion and crêpes."),
            ("Tokyo National Museum, Ueno", "history", 35.7188, 139.7765, 1000, 2.0, "museum heritage", True, "Japan's largest collection of art and antiquities."),
            ("Imperial Palace East Gardens", "history", 35.6852, 139.7528, 0, 1.5, "garden heritage", False, "Former Edo Castle grounds."),
            ("Odaiba Waterfront", "landmark", 35.6300, 139.7750, 0, 2.0, "views family shopping", False, "Bay views, Gundam statue and malls."),
            ("Mt Fuji & Hakone Day Trip", "nature", 35.2324, 139.1069, 15000, 8.0, "iconic views", False, "Lake Ashi cruise and Fuji views."),
            ("Shinjuku Golden Gai", "nightlife", 35.6940, 139.7046, 2000, 2.0, "evening bar", True, "200 tiny bars in six narrow alleys."),
        ],
        "restaurants": [
            ("Ichiran Ramen, Shibuya", 35.6610, 139.7010, 1300, 1, "Tonkotsu ramen", "local", "Solo-booth ramen experience."),
            ("Afuri, Harajuku", 35.6710, 139.7070, 1400, 1, "Yuzu ramen", "vegan", "Light yuzu broth with a vegan option."),
            ("T's Tantan, Tokyo Station", 35.6812, 139.7671, 1100, 1, "Vegan ramen", "vegetarian vegan", "Plant-based tantanmen inside the station."),
            ("Ain Soph Journey, Shinjuku", 35.6910, 139.7080, 2500, 2, "Vegan", "vegetarian vegan", "Famous for vegan pancakes."),
            ("Gonpachi Nishi-Azabu", 35.6560, 139.7240, 5000, 2, "Izakaya", "nightlife", "Wooden izakaya with yakitori and soba."),
            ("Omoide Yokocho", 35.6930, 139.6995, 3000, 2, "Yakitori alley", "nightlife street-food local", "Smoky lantern-lit yakitori stalls."),
            ("Sushi Dai, Toyosu", 35.6456, 139.7840, 6500, 3, "Omakase sushi", "seafood luxury", "Market-fresh omakase."),
        ],
    },
    "Interlaken": {
        "country": "Switzerland", "currency": "CHF", "center": (46.6863, 7.8632),
        "vibes": ["Mountains"], "cost_tier": 3, "good_for": ["Couple", "Family", "Friends", "Solo"],
        "best_months": [6, 7, 8, 9, 12, 1, 2], "avoid_months": {4: "Shoulder season – some lifts closed", 11: "Shoulder season – some lifts closed"},
        "interests": ["Adventure", "Nature", "Wellness"],
        "highlights": ["Alpine peaks", "Turquoise lakes", "Paragliding", "Cogwheel railways"],
        "hotel": {"Budget": 120, "Moderate": 260, "Luxury": 650}, "transport_per_km": 3.0,
        "emergency": {"General emergency": "112", "Police": "117", "Ambulance": "144", "Fire": "118", "Rega air rescue": "1414"},
        "places": [
            ("Jungfraujoch – Top of Europe", "nature", 46.5475, 7.9853, 220, 7.0, "iconic views snow", False, "Railway to Europe's highest station at 3,454 m."),
            ("Harder Kulm", "nature", 46.6970, 7.8510, 40, 1.5, "views sunset", False, "Funicular to a viewpoint over both lakes."),
            ("Lauterbrunnen & Staubbach Falls", "nature", 46.5935, 7.9070, 0, 2.0, "waterfall views walking", False, "Valley of 72 waterfalls."),
            ("Trümmelbach Falls", "nature", 46.5660, 7.9120, 14, 1.0, "waterfall", True, "Glacier waterfalls inside the mountain."),
            ("Lake Brienz Cruise & Iseltwald", "nature", 46.7110, 7.9640, 40, 2.5, "views romantic family", False, "Turquoise lake by paddle steamer."),
            ("Grindelwald First Cliff Walk", "adventure", 46.6590, 8.0540, 70, 3.0, "views adventure", False, "Cliff walkway, zipline and mountain carts."),
            ("Tandem Paragliding", "adventure", 46.6863, 7.8632, 180, 1.5, "iconic adventure views", False, "Soar over Interlaken between the lakes."),
            ("Schynige Platte", "nature", 46.6530, 7.9120, 70, 3.0, "views garden trek", False, "Vintage railway to an alpine garden."),
            ("Höhematte Park", "nature", 46.6860, 7.8590, 0, 0.75, "park family", False, "Meadow with Jungfrau views in the town centre."),
            ("Oberhofen Castle, Lake Thun", "history", 46.7310, 7.6680, 14, 1.5, "heritage museum", True, "Fairytale lakeside castle."),
            ("Canyoning in Saxeten Gorge", "adventure", 46.6600, 7.8300, 150, 3.0, "adventure watersports", False, "Slide and abseil down a gorge."),
            ("Mürren Cliff Village", "nature", 46.5590, 7.8920, 0, 2.0, "views walking", False, "Car-free village on a 800 m cliff."),
        ],
        "restaurants": [
            ("Goldener Anker", 46.6866, 7.8530, 35, 2, "Swiss & international", "nightlife", "Laid-back pub with live music."),
            ("Restaurant Taverne", 46.6860, 7.8680, 45, 2, "Swiss fondue", "local vegetarian", "Cheese fondue and rösti."),
            ("Husi Bierhaus", 46.6850, 7.8560, 30, 1, "Pub food", "nightlife local", "Craft beers and burgers."),
            ("Little Thai", 46.6860, 7.8580, 28, 1, "Thai", "vegetarian vegan", "Cosy spot with many veg options."),
            ("Restaurant Bebbis", 46.6880, 7.8610, 45, 2, "Swiss", "local", "Alpine décor and hearty classics."),
            ("La Terrasse, Victoria-Jungfrau", 46.6857, 7.8590, 120, 3, "Fine dining", "romantic luxury", "Grand-hotel terrace facing the Jungfrau."),
        ],
    },
    "Dubai": {
        "country": "UAE", "currency": "AED", "center": (25.2048, 55.2708),
        "vibes": ["Urban", "Beach"], "cost_tier": 3, "good_for": ["Family", "Couple", "Friends"],
        "best_months": [11, 12, 1, 2, 3], "avoid_months": {6: "Extreme heat (45°C+)", 7: "Extreme heat (45°C+)", 8: "Extreme heat (45°C+)"},
        "interests": ["Shopping", "Adventure", "Food", "Nightlife"],
        "highlights": ["Skyscrapers", "Desert safaris", "Mega malls", "Beach clubs"],
        "hotel": {"Budget": 280, "Moderate": 650, "Luxury": 2000}, "transport_per_km": 2.5,
        "emergency": {"Police": "999", "Ambulance": "998", "Fire": "997", "Police non-emergency": "901"},
        "places": [
            ("Burj Khalifa – At the Top", "landmark", 25.1972, 55.2744, 170, 1.5, "iconic views", True, "Observation deck on the world's tallest building."),
            ("Dubai Mall & Aquarium", "shopping", 25.1985, 55.2796, 0, 2.5, "family shopping", True, "1,200 shops, aquarium and ice rink."),
            ("Al Fahidi Historic District", "history", 25.2637, 55.2972, 0, 1.5, "heritage walking museum", False, "Wind-tower houses and the Dubai Museum."),
            ("Gold & Spice Souks via Abra", "shopping", 25.2700, 55.2970, 2, 1.5, "market souvenirs", False, "Cross the creek by abra to the old souks."),
            ("Museum of the Future", "culture", 25.2192, 55.2818, 149, 2.0, "museum art family", True, "Futuristic exhibits in an iconic torus."),
            ("Atlantis Aquaventure", "adventure", 25.1304, 55.1171, 330, 4.0, "family watersports", False, "Record-breaking waterpark on the Palm."),
            ("Kite Beach", "beach", 25.1600, 55.1960, 0, 2.0, "family sunset", False, "Clean beach with Burj Al Arab views."),
            ("Dubai Frame", "landmark", 25.2352, 55.3004, 50, 1.0, "views", True, "150 m picture frame bridging old and new Dubai."),
            ("Dubai Miracle Garden", "nature", 25.0600, 55.2440, 95, 1.5, "garden family", False, "Floral sculptures (Nov–Apr)."),
            ("Ski Dubai", "adventure", 25.1180, 55.2000, 250, 2.0, "family snow", True, "Indoor ski slope and penguins."),
            ("Evening Desert Safari", "adventure", 25.0300, 55.5900, 250, 6.0, "iconic adventure", False, "Dune bashing, camel rides and BBQ camp."),
            ("Dubai Fountain Show", "landmark", 25.1960, 55.2750, 0, 0.75, "evening family", False, "Choreographed fountains every 30 min after dark."),
            ("Marina Dhow Dinner Cruise", "nightlife", 25.0805, 55.1403, 150, 2.0, "evening romantic", False, "Glittering skyline from a traditional dhow."),
        ],
        "restaurants": [
            ("Al Ustad Special Kebab", 25.2580, 55.2970, 50, 1, "Persian kebabs", "local", "Family-run kebab house since 1978."),
            ("Ravi Restaurant, Satwa", 25.2350, 55.2650, 35, 1, "Pakistani", "local street-food", "Legendary cheap-eats curry house."),
            ("Arabian Tea House", 25.2635, 55.2995, 70, 2, "Emirati", "local vegetarian", "Courtyard café in Al Fahidi."),
            ("Saravana Bhavan, Karama", 25.2470, 55.3040, 35, 1, "South Indian vegetarian", "vegetarian vegan", "Reliable vegetarian thalis."),
            ("At.mosphere, Burj Khalifa", 25.1972, 55.2744, 550, 3, "Fine dining", "luxury romantic views", "Dining on level 122."),
            ("Pierchic", 25.1340, 55.1850, 450, 3, "Seafood", "seafood romantic luxury", "Over-water seafood restaurant."),
            ("Barasti Beach Bar", 25.0890, 55.1460, 150, 2, "Beach bar", "nightlife sunset", "Dubai's classic beach bar."),
        ],
    },
    "Bangkok": {
        "country": "Thailand", "currency": "THB", "center": (13.7466, 100.5340),
        "vibes": ["Urban", "Cultural"], "cost_tier": 1, "good_for": ["Friends", "Solo", "Couple", "Family"],
        "best_months": [11, 12, 1, 2], "avoid_months": {4: "Hottest month", 9: "Peak monsoon rain"},
        "interests": ["Food", "Nightlife", "Culture", "Shopping", "Wellness"],
        "highlights": ["Golden temples", "Street food", "Rooftop bars", "Floating markets"],
        "hotel": {"Budget": 900, "Moderate": 2500, "Luxury": 8000}, "transport_per_km": 15,
        "emergency": {"Tourist police": "1155", "Police": "191", "Ambulance": "1669", "Fire": "199"},
        "places": [
            ("Grand Palace & Wat Phra Kaew", "history", 13.7500, 100.4913, 500, 2.5, "iconic temple heritage", False, "Dazzling royal palace and Emerald Buddha."),
            ("Wat Pho", "culture", 13.7465, 100.4930, 300, 1.5, "temple heritage", False, "46 m Reclining Buddha and massage school."),
            ("Wat Arun", "culture", 13.7437, 100.4889, 100, 1.0, "temple sunset views", False, "Temple of Dawn on the river bank."),
            ("Chatuchak Weekend Market", "shopping", 13.7999, 100.5500, 0, 3.0, "market street-food souvenirs", False, "15,000 stalls of everything."),
            ("Jim Thompson House", "history", 13.7492, 100.5283, 200, 1.5, "heritage museum art", True, "Teak houses of the silk king."),
            ("Lumphini Park", "nature", 13.7310, 100.5418, 0, 1.0, "park walking", False, "Green lung with monitor lizards and paddle boats."),
            ("Traditional Thai Massage, Wat Pho School", "wellness", 13.7460, 100.4935, 480, 1.0, "spa", True, "Massage at the home of Thai massage."),
            ("Damnoen Saduak Floating Market", "food", 13.5194, 99.9590, 600, 5.0, "market street-food photo", False, "Half-day trip to the famous canal market."),
            ("Iconsiam", "shopping", 13.7266, 100.5103, 0, 2.0, "shopping family", True, "Riverside mega-mall with an indoor floating market."),
            ("Chinatown (Yaowarat) Food Walk", "food", 13.7400, 100.5100, 300, 2.0, "street-food evening nightlife", False, "Neon-lit street food heaven after dark."),
            ("Khao San Road", "nightlife", 13.7590, 100.4975, 0, 2.0, "evening bar", False, "Backpacker street of bars and buckets."),
            ("Muay Thai at Rajadamnern Stadium", "culture", 13.7600, 100.5100, 2000, 2.5, "evening performance", True, "Thailand's oldest boxing stadium."),
            ("Asiatique The Riverfront", "shopping", 13.7046, 100.5030, 0, 2.0, "evening market family", False, "Night bazaar with a giant Ferris wheel."),
        ],
        "restaurants": [
            ("Thipsamai Pad Thai", 13.7528, 100.5047, 150, 1, "Pad Thai", "local street-food", "The city's most famous pad thai."),
            ("Jay Fai", 13.7525, 100.5049, 1500, 3, "Street food (Michelin)", "street-food", "Crab omelette by the goggled chef."),
            ("Som Tam Nua", 13.7450, 100.5330, 250, 1, "Isaan", "local", "Papaya salad and fried chicken."),
            ("Broccoli Revolution", 13.7300, 100.5700, 350, 2, "Vegetarian", "vegetarian vegan", "Plant-based Thai and global plates."),
            ("May Veggie Home", 13.7370, 100.5600, 250, 1, "Vegan Thai", "vegetarian vegan", "Vegan versions of Thai classics."),
            ("Sky Bar, Lebua", 13.7217, 100.5170, 1500, 3, "Rooftop bar", "nightlife luxury views", "63rd-floor rooftop bar."),
            ("Supanniga Eating Room", 13.7330, 100.5800, 700, 2, "Thai", "romantic", "Family recipes from Trat and Isaan."),
        ],
    },
    "Rome": {
        "country": "Italy", "currency": "EUR", "center": (41.8986, 12.4769),
        "vibes": ["Cultural", "Urban"], "cost_tier": 2, "good_for": ["Couple", "Family", "Solo", "Friends"],
        "best_months": [4, 5, 6, 9, 10], "avoid_months": {8: "Very hot & crowded"},
        "interests": ["History", "Culture", "Food", "Shopping"],
        "highlights": ["Ancient ruins", "Vatican art", "Gelato & pasta", "Piazzas"],
        "hotel": {"Budget": 80, "Moderate": 170, "Luxury": 500}, "transport_per_km": 1.8,
        "emergency": {"General emergency": "112", "Ambulance": "118", "Police": "113", "Fire": "115"},
        "places": [
            ("Colosseum & Roman Forum", "history", 41.8902, 12.4922, 18, 3.0, "iconic unesco heritage", False, "The Flavian amphitheatre and imperial forums."),
            ("Vatican Museums & Sistine Chapel", "culture", 41.9065, 12.4536, 20, 3.0, "iconic museum art", True, "Michelangelo's ceiling and Raphael Rooms."),
            ("St Peter's Basilica", "history", 41.9022, 12.4539, 0, 1.5, "iconic heritage church views", True, "Climb the dome for Rome's best view."),
            ("Trevi Fountain", "landmark", 41.9009, 12.4833, 0, 0.5, "iconic photo", False, "Toss a coin to return to Rome."),
            ("Pantheon", "history", 41.8986, 12.4769, 5, 0.75, "heritage", True, "2,000-year-old temple with a perfect dome."),
            ("Piazza Navona", "landmark", 41.8992, 12.4731, 0, 1.0, "art walking", False, "Baroque square with Bernini's fountains."),
            ("Spanish Steps", "landmark", 41.9057, 12.4823, 0, 0.75, "shopping photo", False, "135 steps beneath Trinità dei Monti."),
            ("Borghese Gallery & Gardens", "culture", 41.9142, 12.4921, 15, 2.0, "museum art garden", True, "Bernini and Caravaggio in a villa."),
            ("Castel Sant'Angelo", "history", 41.9031, 12.4663, 16, 1.5, "heritage views", True, "Hadrian's mausoleum turned papal fortress."),
            ("Campo de' Fiori Market", "food", 41.8956, 12.4722, 0, 1.0, "market street-food", False, "Morning produce market."),
            ("Appian Way Bike Ride", "adventure", 41.8550, 12.5200, 25, 3.0, "heritage walking", False, "Cycle the ancient road past catacombs."),
            ("Baths of Caracalla", "history", 41.8790, 12.4925, 18, 1.5, "heritage", False, "Vast ruins of imperial bath complex."),
            ("Trastevere Evening Stroll", "nightlife", 41.8897, 12.4699, 0, 2.0, "evening walking food", False, "Ivy-draped lanes, trattorias and bars."),
        ],
        "restaurants": [
            ("Da Enzo al 29", 41.8885, 12.4770, 30, 2, "Roman trattoria", "local", "Cacio e pepe and carbonara classics."),
            ("Roscioli Salumeria", 41.8940, 12.4740, 55, 3, "Roman", "local", "Deli-restaurant famous for carbonara."),
            ("Pizzarium Bonci", 41.9070, 12.4460, 12, 1, "Pizza al taglio", "vegetarian street-food", "Inventive pizza by the slice near the Vatican."),
            ("Ginger Sapori e Salute", 41.9010, 12.4800, 25, 2, "Healthy Italian", "vegetarian vegan", "Fresh bowls and juices."),
            ("Trapizzino Trastevere", 41.8890, 12.4710, 8, 1, "Street food", "street-food", "Pizza-pocket sandwiches."),
            ("Freni e Frizioni", 41.8915, 12.4700, 15, 1, "Aperitivo bar", "nightlife vegetarian", "Trastevere aperitivo buffet."),
            ("La Pergola", 41.9180, 12.4430, 300, 3, "Three-Michelin-star", "luxury romantic views", "Rome's finest rooftop dining."),
        ],
    },
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _expand(name: str, raw: dict) -> dict:
    places = []
    for (pname, cat, lat, lon, cost, hours, tags, indoor, desc) in raw["places"]:
        places.append({
            "id": _slug(f"{name}-{pname}"), "name": pname, "category": cat, "lat": lat, "lon": lon,
            "cost": float(cost), "duration": float(hours), "tags": tags.split(), "indoor": indoor,
            "description": desc, "generic": False,
        })
    restaurants = []
    for (rname, lat, lon, cost, tier, cuisine, tags, desc) in raw["restaurants"]:
        restaurants.append({
            "id": _slug(f"{name}-{rname}"), "name": rname, "lat": lat, "lon": lon, "cost": float(cost),
            "tier": int(tier), "cuisine": cuisine, "tags": tags.split(), "description": desc, "generic": False,
        })
    return {
        "name": name,
        "country": raw["country"],
        "currency": raw["currency"],
        "center": {"lat": raw["center"][0], "lon": raw["center"][1]},
        "vibes": raw["vibes"],
        "cost_tier": raw["cost_tier"],
        "good_for": raw["good_for"],
        "best_months": raw["best_months"],
        "avoid_months": {int(k): v for k, v in raw["avoid_months"].items()},
        "interests": raw["interests"],
        "highlights": raw["highlights"],
        "hotel": raw["hotel"],
        "transport_per_km": float(raw["transport_per_km"]),
        "emergency": raw["emergency"],
        "places": places,
        "restaurants": restaurants,
        "source": "curated",
    }


DESTINATIONS = {name: _expand(name, raw) for name, raw in _RAW.items()}


def list_destinations() -> list[str]:
    return sorted(DESTINATIONS)


def get_destination(name: str) -> dict | None:
    """Return a deep copy of a curated destination profile (case-insensitive)."""
    for key, value in DESTINATIONS.items():
        if key.lower() == (name or "").strip().lower():
            return copy.deepcopy(value)
    return None


# Templates used to build a plausible offline plan for a city we have no data for.
_GENERIC_PLACES = [
    ("Historic Old Town Walk", "history", 1.0, 0.0, 2.0, "heritage walking iconic", False, "Wander the oldest quarter and its main square."),
    ("City Museum", "culture", 0.5, 0.0, 2.0, "museum", True, "Get the city's story in its flagship museum."),
    ("Main Cathedral / Temple", "culture", -0.6, 0.7, 1.0, "temple heritage", True, "Visit the city's best-known place of worship."),
    ("Central Market", "food", 0.2, -0.8, 1.5, "market street-food", False, "Graze on local snacks and produce."),
    ("Panoramic Viewpoint", "landmark", 2.5, 1.5, 1.0, "views sunset", False, "Climb up for the classic skyline photo."),
    ("Riverside / Waterfront Promenade", "nature", -1.8, -1.2, 1.5, "walking park", False, "Slow stroll along the water."),
    ("Botanical Garden or City Park", "nature", 3.0, -2.0, 1.5, "park garden family", False, "Green escape popular with locals."),
    ("Local Crafts Quarter", "shopping", -2.5, 2.2, 1.5, "souvenirs art", False, "Browse workshops for handmade souvenirs."),
    ("Guided Food Tasting Tour", "food", 0.8, 1.8, 2.5, "street-food", False, "Sample regional specialities with a local guide."),
    ("Outdoor Adventure Activity", "adventure", 6.0, 5.0, 3.0, "adventure", False, "Kayaking, cycling or a hike on the outskirts."),
    ("Art Gallery District", "culture", -1.0, 3.0, 1.5, "art", True, "Contemporary galleries and street art."),
    ("Wellness Spa Session", "wellness", 1.5, -2.8, 1.5, "spa", True, "Unwind with a local-style massage."),
    ("Evening Live Music / Cultural Show", "nightlife", 0.3, 0.4, 2.0, "evening performance", True, "Catch a local performance after dinner."),
]
_GENERIC_RESTAURANTS = [
    ("Popular local eatery", 0.4, 0.2, 1, "Local", "local", "Busy spot locals recommend for regional dishes."),
    ("Vegetarian-friendly café", -0.5, 0.6, 1, "Café", "vegetarian vegan", "Light bites with plenty of plant-based options."),
    ("Traditional restaurant", 0.9, -0.4, 2, "Regional", "local", "Sit-down meal of signature regional cuisine."),
    ("Rooftop bar & grill", -0.2, -0.9, 3, "Modern", "nightlife views", "Dinner with a view and a lively bar."),
    ("Street-food lane", 1.2, 1.1, 1, "Street food", "street-food nightlife", "Evening stalls for cheap, delicious bites."),
    ("Fine-dining room", -1.1, -0.3, 3, "Contemporary", "romantic luxury", "Tasting menu showcasing local produce."),
]


def generic_destination(name: str, currency: str = "USD") -> dict:
    """Offline fallback profile for an unknown city.

    Places are templates scattered on a small synthetic grid around a nominal
    centre, so the clustering and budgeting pipeline still works end-to-end.
    """
    from .config import USD_PER_UNIT  # local import avoids a cycle at module load

    usd = USD_PER_UNIT.get(currency, 1.0)
    # Express mid-range USD prices in the local currency.
    def local(usd_amount: float) -> float:
        return round(usd_amount / usd, 0)

    lat0, lon0 = 0.0, 0.0
    km_to_deg = 1 / 111.0
    places = []
    for i, (pname, cat, dx, dy, hours, tags, indoor, desc) in enumerate(_GENERIC_PLACES):
        places.append({
            "id": _slug(f"{name}-{pname}"), "name": pname, "category": cat,
            "lat": lat0 + dy * km_to_deg, "lon": lon0 + dx * km_to_deg,
            "cost": local([0, 10, 0, 0, 5, 0, 3, 0, 40, 45, 0, 35, 25][i]),
            "duration": hours, "tags": tags.split(), "indoor": indoor, "description": desc, "generic": True,
        })
    restaurants = []
    for (rname, dx, dy, tier, cuisine, tags, desc) in _GENERIC_RESTAURANTS:
        restaurants.append({
            "id": _slug(f"{name}-{rname}"), "name": rname, "lat": lat0 + dy * km_to_deg, "lon": lon0 + dx * km_to_deg,
            "cost": local({1: 10, 2: 25, 3: 70}[tier]), "tier": tier, "cuisine": cuisine, "tags": tags.split(),
            "description": desc, "generic": True,
        })
    return {
        "name": name.strip().title() or "Your destination",
        "country": "",
        "currency": currency,
        "center": {"lat": lat0, "lon": lon0},
        "vibes": [], "cost_tier": 2, "good_for": [], "best_months": [], "avoid_months": {},
        "interests": [], "highlights": [],
        "hotel": {"Budget": local(45), "Moderate": local(110), "Luxury": local(320)},
        "transport_per_km": local(1.2),
        "emergency": {"General emergency (most countries)": "112"},
        "places": places,
        "restaurants": restaurants,
        "source": "generic",
    }
