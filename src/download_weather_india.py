from pathlib import Path
import requests
import pandas as pd
import time


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "weather"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "weather"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


START_DATE = "2022-04-01"
END_DATE = "2025-06-24"


CITIES = {
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "bengaluru": (12.9716, 77.5946),
    "hyderabad": (17.3850, 78.4867),
}


API_URL = "https://archive-api.open-meteo.com/v1/archive"


HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "wind_speed_10m",
    "precipitation",
]


city_data = {}


# ============================================================
# DOWNLOAD EACH CITY
# ============================================================

for city, (lat, lon) in CITIES.items():

    print(f"\nDownloading: {city}")

    params = {
        "latitude": lat,
        "longitude": lon,

        "start_date": START_DATE,
        "end_date": END_DATE,

        "hourly": ",".join(HOURLY_VARIABLES),

        "timezone": "Asia/Kolkata",

        # Store wind speed directly in m/s
        "wind_speed_unit": "ms",

        # Consistent historical reanalysis
        "models": "era5",
    }


    response = requests.get(
        API_URL,
        params=params,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()


    if "hourly" not in data:
        raise RuntimeError(
            f"No hourly weather returned for {city}"
        )


    df = pd.DataFrame(
        data["hourly"]
    )


    df = df.rename(
        columns={
            "time": "timestamp",

            "temperature_2m":
                "temperature_c",

            "relative_humidity_2m":
                "humidity_pct",

            "apparent_temperature":
                "apparent_temperature_c",

            "wind_speed_10m":
                "weather_wind_speed_ms",

            "precipitation":
                "precipitation_mm"
        }
    )


    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )


    df = df.dropna(
        subset=["timestamp"]
    )


    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)


    # --------------------------------------------
    # Validate city
    # --------------------------------------------

    print(
        "Rows:",
        len(df)
    )

    print(
        "Start:",
        df["timestamp"].min()
    )

    print(
        "End:",
        df["timestamp"].max()
    )

    print(
        "Missing values:"
    )

    print(
        df.isna().sum()
    )


    # --------------------------------------------
    # Save raw downloaded city dataset
    # --------------------------------------------

    city_file = (
        RAW_DIR /
        f"{city}_weather_hourly.csv"
    )


    df.to_csv(
        city_file,
        index=False
    )


    city_data[city] = df


    # Be polite to API
    time.sleep(1)


# ============================================================
# CREATE COMMON HOURLY INDEX
# ============================================================

expected = pd.date_range(
    start="2022-04-01 00:00:00",
    end="2025-06-24 23:00:00",
    freq="h"
)


master = pd.DataFrame({
    "timestamp": expected
})


# ============================================================
# MERGE ALL SIX CITIES
# ============================================================

for city, df in city_data.items():

    temp = df.copy()


    temp = temp.rename(
        columns={
            "temperature_c":
                f"{city}_temperature_c",

            "humidity_pct":
                f"{city}_humidity_pct",

            "apparent_temperature_c":
                f"{city}_apparent_temperature_c",

            "weather_wind_speed_ms":
                f"{city}_weather_wind_speed_ms",

            "precipitation_mm":
                f"{city}_precipitation_mm",
        }
    )


    master = master.merge(
        temp,
        on="timestamp",
        how="left",
        validate="one_to_one"
    )


# ============================================================
# NATIONAL WEATHER PROXY
# ============================================================

temperature_cols = [
    f"{city}_temperature_c"
    for city in CITIES
]

humidity_cols = [
    f"{city}_humidity_pct"
    for city in CITIES
]

apparent_cols = [
    f"{city}_apparent_temperature_c"
    for city in CITIES
]

wind_cols = [
    f"{city}_weather_wind_speed_ms"
    for city in CITIES
]

precipitation_cols = [
    f"{city}_precipitation_mm"
    for city in CITIES
]


# ------------------------------------------------------------
# Temperature
# ------------------------------------------------------------

master["temperature_mean_c"] = (
    master[temperature_cols].mean(axis=1)
)

master["temperature_max_c"] = (
    master[temperature_cols].max(axis=1)
)

master["temperature_min_c"] = (
    master[temperature_cols].min(axis=1)
)


# ------------------------------------------------------------
# Humidity
# ------------------------------------------------------------

master["humidity_mean_pct"] = (
    master[humidity_cols].mean(axis=1)
)


# ------------------------------------------------------------
# Apparent temperature
# ------------------------------------------------------------

master["apparent_temperature_mean_c"] = (
    master[apparent_cols].mean(axis=1)
)


# ------------------------------------------------------------
# Wind
# ------------------------------------------------------------

master["weather_wind_speed_mean_ms"] = (
    master[wind_cols].mean(axis=1)
)


# ------------------------------------------------------------
# Rain
# ------------------------------------------------------------

master["precipitation_mean_mm"] = (
    master[precipitation_cols].mean(axis=1)
)

master["precipitation_max_mm"] = (
    master[precipitation_cols].max(axis=1)
)


# ============================================================
# SAVE DETAILED CITY DATA
# ============================================================

detailed_file = (
    PROCESSED_DIR /
    "india_weather_cities_hourly_2022_2025.csv"
)


master.to_csv(
    detailed_file,
    index=False
)


# ============================================================
# CREATE COMPACT MODEL WEATHER DATASET
# ============================================================

MODEL_COLUMNS = [

    "timestamp",

    "temperature_mean_c",
    "temperature_max_c",
    "temperature_min_c",

    "humidity_mean_pct",

    "apparent_temperature_mean_c",

    "weather_wind_speed_mean_ms",

    "precipitation_mean_mm",
    "precipitation_max_mm",
]


weather = master[
    MODEL_COLUMNS
].copy()


final_file = (
    PROCESSED_DIR /
    "india_weather_hourly_2022_2025.csv"
)


weather.to_csv(
    final_file,
    index=False
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n")
print("=" * 70)
print("FINAL WEATHER QUALITY CHECK")
print("=" * 70)

print(
    "Rows:",
    len(weather)
)

print(
    "Start:",
    weather["timestamp"].min()
)

print(
    "End:",
    weather["timestamp"].max()
)

print(
    "Duplicate timestamps:",
    weather["timestamp"].duplicated().sum()
)

print(
    "\nMissing values:"
)

print(
    weather.isna().sum()
)

print(
    "\nSaved:",
    final_file
)