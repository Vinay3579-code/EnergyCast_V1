from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

IEX_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "iex"
    / "iex_dam_hourly_2022_2025.csv"
)

GRID_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "grid_india"
    / "grid_india_hourly_2022_2025.csv"
)

WEATHER_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather"
    / "india_weather_hourly_2022_2025.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "master"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


START = pd.Timestamp("2022-04-01 00:00:00")
END = pd.Timestamp("2025-06-24 23:00:00")


# ============================================================
# LOAD IEX
# ============================================================

print("=" * 75)
print("LOADING IEX DATA")
print("=" * 75)

iex = pd.read_csv(
    IEX_FILE,
    parse_dates=["timestamp"]
)

print("Original rows:", len(iex))


# Keep common modeling period only
iex = iex[
    iex["timestamp"].between(
        START,
        END
    )
].copy()


# Keep useful market variables
iex = iex[
    [
        "timestamp",
        "mcp_rs_per_mwh",
        "weighted_mcp_rs_per_mwh",
        "purchase_bid_mwh",
        "sell_bid_mwh",
        "mcv_mwh",
        "final_scheduled_volume_mwh"
    ]
]


print("Filtered rows:", len(iex))
print(
    "Range:",
    iex["timestamp"].min(),
    "->",
    iex["timestamp"].max()
)


# ============================================================
# LOAD GRID INDIA
# ============================================================

print("\n")
print("=" * 75)
print("LOADING GRID INDIA DATA")
print("=" * 75)

grid = pd.read_csv(
    GRID_FILE,
    parse_dates=["timestamp"]
)


grid = grid[
    [
        "timestamp",
        "demand_mw",
        "wind_mw",
        "solar_mw"
    ]
].copy()


# Make generation columns clearer
grid = grid.rename(
    columns={
        "wind_mw":
            "wind_generation_mw",

        "solar_mw":
            "solar_generation_mw"
    }
)


print("Rows:", len(grid))
print(
    "Range:",
    grid["timestamp"].min(),
    "->",
    grid["timestamp"].max()
)


# ============================================================
# LOAD WEATHER
# ============================================================

print("\n")
print("=" * 75)
print("LOADING WEATHER DATA")
print("=" * 75)

weather = pd.read_csv(
    WEATHER_FILE,
    parse_dates=["timestamp"]
)


print("Rows:", len(weather))
print(
    "Range:",
    weather["timestamp"].min(),
    "->",
    weather["timestamp"].max()
)


# ============================================================
# VALIDATE SOURCE TIMESTAMPS
# ============================================================

for name, df in [
    ("IEX", iex),
    ("GRID", grid),
    ("WEATHER", weather)
]:

    duplicates = (
        df["timestamp"]
        .duplicated()
        .sum()
    )

    print(
        f"{name} duplicate timestamps:",
        duplicates
    )

    if duplicates != 0:
        raise RuntimeError(
            f"{name} contains duplicate timestamps."
        )


# ============================================================
# MERGE
# ============================================================

print("\n")
print("=" * 75)
print("MERGING DATASETS")
print("=" * 75)


master = iex.merge(
    grid,
    on="timestamp",
    how="inner",
    validate="one_to_one"
)


print(
    "Rows after IEX + Grid:",
    len(master)
)


master = master.merge(
    weather,
    on="timestamp",
    how="inner",
    validate="one_to_one"
)


print(
    "Rows after adding weather:",
    len(master)
)


# ============================================================
# SORT
# ============================================================

master = (
    master
    .sort_values("timestamp")
    .reset_index(drop=True)
)


# ============================================================
# EXPECTED TIMELINE
# ============================================================

expected = pd.date_range(
    start=START,
    end=END,
    freq="h"
)


actual = pd.DatetimeIndex(
    master["timestamp"]
)


missing_timestamps = (
    expected.difference(actual)
)


extra_timestamps = (
    actual.difference(expected)
)


# ============================================================
# QUALITY CHECK
# ============================================================

duplicate_count = (
    master["timestamp"]
    .duplicated()
    .sum()
)


missing_values = (
    master
    .isna()
    .sum()
)


print("\n")
print("=" * 75)
print("FINAL MASTER DATA QUALITY CHECK")
print("=" * 75)

print(
    "Rows:",
    len(master)
)

print(
    "Expected rows:",
    len(expected)
)

print(
    "Start:",
    master["timestamp"].min()
)

print(
    "End:",
    master["timestamp"].max()
)

print(
    "Duplicate timestamps:",
    duplicate_count
)

print(
    "Missing timestamps:",
    len(missing_timestamps)
)

print(
    "Extra timestamps:",
    len(extra_timestamps)
)

print("\nMissing values:")
print(
    missing_values
)


# ============================================================
# STRICT VALIDATION
# ============================================================

errors = []


if len(master) != len(expected):

    errors.append(
        f"Expected {len(expected)} rows, "
        f"found {len(master)}."
    )


if duplicate_count > 0:

    errors.append(
        f"{duplicate_count} duplicate timestamps."
    )


if len(missing_timestamps) > 0:

    errors.append(
        f"{len(missing_timestamps)} timestamps missing."
    )


if len(extra_timestamps) > 0:

    errors.append(
        f"{len(extra_timestamps)} extra timestamps."
    )


if missing_values.sum() > 0:

    errors.append(
        f"{missing_values.sum()} total missing values."
    )


if errors:

    print("\nVALIDATION FAILED")

    for error in errors:
        print(" -", error)

    raise RuntimeError(
        "Master dataset failed validation."
    )


# ============================================================
# SAVE FINAL DATASET
# ============================================================

OUTPUT_FILE = (
    OUTPUT_DIR
    / "energycast_master_hourly_2022_2025.csv"
)


master.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SAVE DATA DICTIONARY
# ============================================================

dictionary = pd.DataFrame(
    [
        ["timestamp",
         "Hourly timestamp in IST",
         "All sources"],

        ["mcp_rs_per_mwh",
         "IEX Market Clearing Price (Rs/MWh)",
         "IEX"],

        ["weighted_mcp_rs_per_mwh",
         "Weighted IEX MCP",
         "IEX"],

        ["purchase_bid_mwh",
         "IEX purchase bid volume",
         "IEX"],

        ["sell_bid_mwh",
         "IEX sell bid volume",
         "IEX"],

        ["mcv_mwh",
         "IEX Market Cleared Volume",
         "IEX"],

        ["final_scheduled_volume_mwh",
         "IEX final scheduled volume",
         "IEX"],

        ["demand_mw",
         "All-India electricity demand",
         "Grid India"],

        ["wind_generation_mw",
         "All-India wind generation",
         "Grid India"],

        ["solar_generation_mw",
         "All-India solar generation",
         "Grid India"],

        ["temperature_mean_c",
         "Mean temperature across selected Indian cities",
         "ERA5/Open-Meteo"],

        ["temperature_max_c",
         "Maximum temperature across selected cities",
         "ERA5/Open-Meteo"],

        ["temperature_min_c",
         "Minimum temperature across selected cities",
         "ERA5/Open-Meteo"],

        ["humidity_mean_pct",
         "Mean relative humidity",
         "ERA5/Open-Meteo"],

        ["apparent_temperature_mean_c",
         "Mean apparent temperature",
         "ERA5/Open-Meteo"],

        ["weather_wind_speed_mean_ms",
         "Mean weather wind speed",
         "ERA5/Open-Meteo"],

        ["precipitation_mean_mm",
         "Mean precipitation",
         "ERA5/Open-Meteo"],

        ["precipitation_max_mm",
         "Maximum precipitation",
         "ERA5/Open-Meteo"],
    ],

    columns=[
        "column",
        "description",
        "source"
    ]
)


dictionary.to_csv(
    OUTPUT_DIR
    / "energycast_data_dictionary.csv",
    index=False
)


print("\n")
print("=" * 75)
print("SUCCESS")
print("=" * 75)

print(
    "Master dataset saved:"
)

print(
    OUTPUT_FILE
)

print(
    "\nData dictionary saved:"
)

print(
    OUTPUT_DIR
    / "energycast_data_dictionary.csv"
)