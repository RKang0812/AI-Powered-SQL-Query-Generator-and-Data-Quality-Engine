"""
Generates realistic simulated shipping data, including deliberately injected abnormal data
"""

import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import sys
import os

# add parent directory to sys.path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.shipping_config import (
    PORTS, COMMON_ROUTES, VESSEL_TYPES, VESSEL_SUFFIXES,
    ANOMALY_TYPES, NAUTICAL_MILE_TO_KM
)

fake = Faker()
Faker.seed(42) 
np.random.seed(42)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculates the nautical miles distance between two points using the Haversine formula
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 3440.065  # Earth radius in nautical miles
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return round(distance, 2)


def generate_normal_voyage(voyage_id):
    """
    generates a single normal voyage data entry with realistic values based on predefined routes and vessel types
    """
    # randomly select a route
    departure_port, arrival_port = random.choice(COMMON_ROUTES)
    dep_info = PORTS[departure_port]
    arr_info = PORTS[arrival_port]
    
    # randomly select a vessel type
    vessel_type = random.choice(list(VESSEL_TYPES.keys()))
    vessel_config = VESSEL_TYPES[vessel_type]
    
    # generate vessel name
    vessel_name = f"{vessel_config['prefix']} {random.choice(VESSEL_SUFFIXES)}"
    
    # calculate real distance
    distance_nm = calculate_distance(
        dep_info["lat"], dep_info["lon"],
        arr_info["lat"], arr_info["lon"]
    )
    
    # generate reasonable speed
    avg_speed = round(np.random.uniform(*vessel_config["avg_speed_range"]), 2)
    
    # calculate sailing time (days)
    sailing_days = distance_nm / (avg_speed * 24)
    
    # generate timestamps
    departure_at = fake.date_time_between(start_date="-90d", end_date="-30d")
    arrival_at = departure_at + timedelta(days=sailing_days)
    
    # generate fuel consumption (based on distance and speed)
    daily_consumption = np.random.uniform(*vessel_config["hfo_consumption_range"])
    hfo_consumption = round(daily_consumption * sailing_days, 2)
    
    # generate cargo quantity
    is_ballast = random.choice([True, False])
    if is_ballast:
        cargo_qty = 0
    else:
        cargo_qty = round(np.random.uniform(
            vessel_config["cargo_capacity_range"][0] * 0.6,
            vessel_config["cargo_capacity_range"][1] * 0.95
        ), 2)
    
    return {
        "voyage_id": voyage_id,
        "vessel_name": vessel_name,
        "vessel_type": vessel_type,
        "departure_port": departure_port,
        "departure_lat": dep_info["lat"],
        "departure_lon": dep_info["lon"],
        "arrival_port": arrival_port,
        "arrival_lat": arr_info["lat"],
        "arrival_lon": arr_info["lon"],
        "departure_at": departure_at,
        "arrival_at": arrival_at,
        "distance_nm": distance_nm,
        "avg_speed_knots": avg_speed,
        "heavy_fuel_oil_cons": hfo_consumption,
        "cargo_qty_mt": cargo_qty,
        "is_ballast": is_ballast,
        "is_anomaly": False,
        "anomaly_type": None,
    }


def inject_anomaly(normal_data, anomaly_type):
    """
    Injects a specific type of anomaly into normal data
    """
    data = normal_data.copy()
    data["is_anomaly"] = True
    data["anomaly_type"] = anomaly_type
    
    if anomaly_type == "time_inversion":
        # swap departure and arrival times
        data["departure_at"], data["arrival_at"] = data["arrival_at"], data["departure_at"]
    
    elif anomaly_type == "zero_consumption":
        # set fuel consumption to 0
        data["heavy_fuel_oil_cons"] = 0
    
    elif anomaly_type == "excessive_speed":
        # set unreasonable high speed
        data["avg_speed_knots"] = round(np.random.uniform(35, 50), 2)
    
    elif anomaly_type == "negative_values":
        # generate negative values
        field = random.choice(["distance_nm", "heavy_fuel_oil_cons", "cargo_qty_mt"])
        data[field] = -abs(data[field])
    
    elif anomaly_type == "lat_lon_swap":
        # swap latitude and longitude
        data["departure_lat"], data["departure_lon"] = data["departure_lon"], data["departure_lat"]
        data["arrival_lat"], data["arrival_lon"] = data["arrival_lon"], data["arrival_lat"]
    
    elif anomaly_type == "cargo_inconsistency":
        # empty cargo but not ballast
        data["is_ballast"] = True
        data["cargo_qty_mt"] = round(np.random.uniform(5000, 20000), 2)
    
    elif anomaly_type == "impossible_consumption":
        # fuel consumption that doesn't match distance and speed
        data["heavy_fuel_oil_cons"] = round(data["distance_nm"] * 0.01, 2)  # 极低油耗
    
    return data


def generate_dataset(n_rows=1000, anomaly_rate=0.15):
    """
    generates a complete dataset
    
    Args:
        n_rows: total number of rows
        anomaly_rate: proportion of anomalous data (0-1)
    """
    print(f"🚢 starting to generate {n_rows} rows of voyage data...")
    print(f"📊 anomaly rate: {anomaly_rate*100}%")
    
    # calculate number of anomalous and normal rows
    n_anomalies = int(n_rows * anomaly_rate)
    n_normal = n_rows - n_anomalies
    
    # generate normal data
    normal_data = []
    for i in range(1, n_normal + 1):
        normal_data.append(generate_normal_voyage(i))
    
    # generate anomalous data
    anomaly_data = []
    anomaly_counts = {}
    
    for i in range(n_normal + 1, n_rows + 1):
        # randomly select an anomaly type based on predefined weights
        anomaly_type = random.choices(
            list(ANOMALY_TYPES.keys()),
            weights=[v["weight"] for v in ANOMALY_TYPES.values()]
        )[0]
        
        # first generate normal data, then inject anomaly
        normal_voyage = generate_normal_voyage(i)
        anomaly_voyage = inject_anomaly(normal_voyage, anomaly_type)
        anomaly_data.append(anomaly_voyage)
        
        # culculate anomaly type counts
        anomaly_counts[anomaly_type] = anomaly_counts.get(anomaly_type, 0) + 1
    
    # merging normal and anomalous data
    all_data = normal_data + anomaly_data
    
    # shuffle the order
    random.shuffle(all_data)
    
    # convert to DataFrame
    df = pd.DataFrame(all_data)
    
    # print statistics
    print(f"\n✅ Data generation complete!")
    print(f"   Normal data: {n_normal} rows")
    print(f"   Anomalous data: {n_anomalies} rows")
    print(f"\nAnomaly type distribution:")
    for atype, count in sorted(anomaly_counts.items(), key=lambda x: -x[1]):
        print(f"   - {atype}: {count} rows ({ANOMALY_TYPES[atype]['description']})")
    
    return df


if __name__ == "__main__":
    # generate dataset with 1000 rows and 15% anomalies
    df = generate_dataset(n_rows=1000, anomaly_rate=0.15)
    
    # save to CSV
    output_path = os.path.join(
        os.path.dirname(__file__), 
        "raw", 
        "voyage_performance.csv"
    )
    df.to_csv(output_path, index=False)
    print(f"\n💾 Data saved to: {output_path}")
    
    # display first 5 rows
    print("\n📋 Data preview:")
    print(df.head())
    
    # display basic statistics
    print("\n📊 Data statistics:")
    print(df.describe())
