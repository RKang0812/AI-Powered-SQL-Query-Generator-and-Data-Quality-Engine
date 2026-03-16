"""
Contains real data such as ports, ships, routes, etc.
"""

# real mean ports with lat/lon and country
PORTS = {
    "Singapore": {"lat": 1.2644, "lon": 103.8540, "country": "Singapore"},
    "Shanghai": {"lat": 31.2304, "lon": 121.4737, "country": "China"},
    "Rotterdam": {"lat": 51.9244, "lon": 4.4777, "country": "Netherlands"},
    "Hong Kong": {"lat": 22.3193, "lon": 114.1694, "country": "Hong Kong"},
    "Busan": {"lat": 35.1796, "lon": 129.0756, "country": "South Korea"},
    "Dubai": {"lat": 25.2769, "lon": 55.2962, "country": "UAE"},
    "Los Angeles": {"lat": 33.7405, "lon": -118.2725, "country": "USA"},
    "Hamburg": {"lat": 53.5453, "lon": 9.9700, "country": "Germany"},
    "Antwerp": {"lat": 51.2194, "lon": 4.4025, "country": "Belgium"},
    "Tokyo": {"lat": 35.6528, "lon": 139.8394, "country": "Japan"},
}

# commen shipping routes between major ports (origin, destination)
COMMON_ROUTES = [
    ("Shanghai", "Los Angeles"),
    ("Singapore", "Rotterdam"),
    ("Busan", "Hamburg"),
    ("Dubai", "Singapore"),
    ("Hong Kong", "Los Angeles"),
    ("Shanghai", "Rotterdam"),
    ("Singapore", "Dubai"),
    ("Tokyo", "Los Angeles"),
]

# ship types with their characteristics
VESSEL_TYPES = {
    "Container": {
        "avg_speed_range": (18, 24),  # knots
        "hfo_consumption_range": (50, 120),  # tons/day
        "cargo_capacity_range": (5000, 20000),  # TEU
        "prefix": "MSC",
    },
    "Tanker": {
        "avg_speed_range": (12, 16),
        "hfo_consumption_range": (30, 80),
        "cargo_capacity_range": (50000, 300000),  # DWT
        "prefix": "VLCC",
    },
    "Bulk": {
        "avg_speed_range": (13, 17),
        "hfo_consumption_range": (25, 70),
        "cargo_capacity_range": (30000, 180000),  # DWT
        "prefix": "CAPE",
    },
}

# ship names suffixes
VESSEL_SUFFIXES = [
    "Star", "Spirit", "Fortune", "Horizon", "Victory", 
    "Pride", "Glory", "Express", "Navigator", "Explorer",
    "Ocean", "Sea", "Wave", "Pacific", "Atlantic"
]

# anomaly types configuration
ANOMALY_TYPES = {
    "time_inversion": {
        "description": "Arrival time is earlier than departure time",
        "weight": 0.2,  # accounts for 20% of anomalous data
    },
    "zero_consumption": {
        "description": "Fuel consumption is 0 but distance is greater than 0",
        "weight": 0.15,
    },
    "excessive_speed": {
        "description": "The speed exceeds the physical limit (> 30 knots)",
        "weight": 0.15,
    },
    "negative_values": {
        "description": "distance, fuel consumption or cargo quantity is negative",
        "weight": 0.1,
    },
    "lat_lon_swap": {
        "description": "Latitude and longitude are swapped",
        "weight": 0.15,
    },
    "cargo_inconsistency": {
        "description": "Discharge quantity is greater than loading quantity (when empty)",
        "weight": 0.15,
    },
    "impossible_consumption": {
        "description": "Fuel consumption is not proportional to航行 distance/time",
        "weight": 0.1,
    },
}

NAUTICAL_MILE_TO_KM = 1.852
AVG_HOURS_PER_DAY = 24
