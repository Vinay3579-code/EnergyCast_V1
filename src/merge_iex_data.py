from pathlib import Path
import pandas as pd

# ============================================================
# EnergyCast V1 - Merge IEX Day-Ahead Market monthly files
# Expected raw structure:
#
# data/raw/iex/
#   2022/*.xlsx
#   2023/*.xlsx
#   2024/*.xlsx
#   2025/*.xlsx
#
# IEX export format:
# Row 1 : blank
# Row 2 : "Market Snapshot"
# Row 3 : date-range metadata
# Row 4 : blank
# Row 5 : actual column headers
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "iex"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "iex"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. Find all monthly Excel files recursively
# ------------------------------------------------------------
files = sorted(RAW_DIR.rglob("*.xlsx"))

print("=" * 70)
print("ENERGYCAST V1 - IEX DATA MERGER")
print("=" * 70)
print(f"Raw directory : {RAW_DIR}")
print(f"Files found   : {len(files)}")

if not files:
    raise FileNotFoundError(
        f"\nNo .xlsx files were found inside:\n{RAW_DIR}\n"
        "Place the monthly IEX files under data/raw/iex/<year>/"
    )

# Your expected total is 45 files:
# Apr-Dec 2022 = 9
# 2023 = 12
# 2024 = 12
# 2025 = 12
if len(files) != 45:
    print(
        f"\nWARNING: Expected 45 monthly files, but found {len(files)}."
        "\nThe merge will continue, but verify that no month is missing."
    )

# ------------------------------------------------------------
# 2. Expected IEX columns
# ------------------------------------------------------------
expected_columns = [
    "Date",
    "Hour",
    "Purchase Bid (MWh)",
    "Sell Bid (MWh)",
    "MCV (MWh)",
    "Final Scheduled Volume (MWh)",
    "MCP (Rs/MWh) *",
    "Weighted MCP (Rs/MWh)",
]

frames = []
failed_files = []

# ------------------------------------------------------------
# 3. Read every monthly file
# ------------------------------------------------------------
for i, file in enumerate(files, start=1):
    print(f"[{i:02d}/{len(files)}] Reading: {file.relative_to(RAW_DIR)}")

    try:
        # IEX's actual header is on Excel row 5 -> pandas header=4
        df = pd.read_excel(
            file,
            sheet_name=0,
            header=4,
            engine="openpyxl"
        )

        # Remove totally empty rows/columns
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")

        # Clean header whitespace
        df.columns = [str(c).strip() for c in df.columns]

        missing = [c for c in expected_columns if c not in df.columns]

        if missing:
            print(f"    ERROR: Missing columns: {missing}")
            print(f"    Found columns: {list(df.columns)}")
            failed_files.append(str(file))
            continue

        # Keep only the 8 expected IEX columns.
        # This prevents accidental unnamed/export columns from entering dataset.
        df = df[expected_columns].copy()

        # Traceability
        df["source_file"] = file.name
        df["source_year"] = file.parent.name

        frames.append(df)

        print(f"    Loaded {len(df):,} rows")

    except Exception as e:
        print(f"    ERROR: {e}")
        failed_files.append(str(file))

if not frames:
    raise RuntimeError("None of the IEX Excel files could be loaded.")

if failed_files:
    print("\nFiles that failed:")
    for f in failed_files:
        print(" -", f)
    raise RuntimeError(
        "\nSome files failed validation. Fix them before creating the final dataset."
    )

# ------------------------------------------------------------
# 4. Concatenate all months
# ------------------------------------------------------------
combined = pd.concat(frames, ignore_index=True)

print("\n" + "=" * 70)
print("MERGE SUMMARY")
print("=" * 70)
print(f"Rows after concatenation : {len(combined):,}")
print(f"Columns                  : {len(combined.columns)}")

# ------------------------------------------------------------
# 5. Preserve a raw-combined CSV before transformations
# ------------------------------------------------------------
raw_combined_path = OUTPUT_DIR / "iex_dam_hourly_master_raw.csv"
combined.to_csv(raw_combined_path, index=False)

print(f"\nRaw combined file saved:\n{raw_combined_path}")

# ------------------------------------------------------------
# 6. Standardize names for modeling
# ------------------------------------------------------------
combined = combined.rename(
    columns={
        "Purchase Bid (MWh)": "purchase_bid_mwh",
        "Sell Bid (MWh)": "sell_bid_mwh",
        "MCV (MWh)": "mcv_mwh",
        "Final Scheduled Volume (MWh)": "final_scheduled_volume_mwh",
        "MCP (Rs/MWh) *": "mcp_rs_per_mwh",
        "Weighted MCP (Rs/MWh)": "weighted_mcp_rs_per_mwh",
    }
)

# ------------------------------------------------------------
# 7. Parse Date and Hour
# ------------------------------------------------------------
combined["Date"] = pd.to_datetime(
    combined["Date"],
    dayfirst=True,
    errors="coerce"
)

combined["Hour"] = pd.to_numeric(
    combined["Hour"],
    errors="coerce"
)

invalid_date_rows = combined["Date"].isna().sum()
invalid_hour_rows = combined["Hour"].isna().sum()

print(f"\nInvalid date rows : {invalid_date_rows}")
print(f"Invalid hour rows : {invalid_hour_rows}")

# IEX hourly exports use Hour = 1...24.
bad_hours = combined.loc[
    ~combined["Hour"].between(1, 24, inclusive="both"),
    ["Date", "Hour", "source_file"]
]

if len(bad_hours) > 0:
    print("\nWARNING: Rows with Hour outside 1-24:")
    print(bad_hours.head(20).to_string(index=False))

# ------------------------------------------------------------
# 8. Create an hourly timestamp
#
# Hour 1  -> 00:00
# Hour 2  -> 01:00
# ...
# Hour 24 -> 23:00
# ------------------------------------------------------------
combined["timestamp"] = (
    combined["Date"]
    + pd.to_timedelta(combined["Hour"] - 1, unit="h")
)

# ------------------------------------------------------------
# 9. Convert market columns to numeric
# ------------------------------------------------------------
numeric_columns = [
    "purchase_bid_mwh",
    "sell_bid_mwh",
    "mcv_mwh",
    "final_scheduled_volume_mwh",
    "mcp_rs_per_mwh",
    "weighted_mcp_rs_per_mwh",
]

for col in numeric_columns:
    combined[col] = pd.to_numeric(combined[col], errors="coerce")

# ------------------------------------------------------------
# 10. Sort chronologically
# ------------------------------------------------------------
combined = combined.sort_values("timestamp").reset_index(drop=True)

# ------------------------------------------------------------
# 11. Quality checks
# ------------------------------------------------------------
duplicate_timestamps = combined["timestamp"].duplicated(keep=False)
duplicate_count = int(duplicate_timestamps.sum())

print("\n" + "=" * 70)
print("QUALITY CHECK")
print("=" * 70)

print(f"First timestamp       : {combined['timestamp'].min()}")
print(f"Last timestamp        : {combined['timestamp'].max()}")
print(f"Duplicate timestamps  : {duplicate_count}")
print(f"Missing MCP values    : {combined['mcp_rs_per_mwh'].isna().sum():,}")

if duplicate_count:
    duplicate_path = OUTPUT_DIR / "iex_duplicate_timestamps.csv"
    combined.loc[duplicate_timestamps].to_csv(duplicate_path, index=False)
    print(f"Duplicate rows exported to:\n{duplicate_path}")

# Expected hourly timeline
valid_time = combined["timestamp"].dropna()

if not valid_time.empty:
    expected_timestamps = pd.date_range(
        start=valid_time.min(),
        end=valid_time.max(),
        freq="h"
    )

    actual_timestamps = pd.DatetimeIndex(valid_time.unique())
    missing_timestamps = expected_timestamps.difference(actual_timestamps)

    print(f"Missing hourly timestamps: {len(missing_timestamps):,}")

    if len(missing_timestamps):
        missing_path = OUTPUT_DIR / "iex_missing_timestamps.csv"
        pd.DataFrame({"missing_timestamp": missing_timestamps}).to_csv(
            missing_path,
            index=False
        )
        print(f"Missing timestamps exported to:\n{missing_path}")

# ------------------------------------------------------------
# 12. Reorder columns
# ------------------------------------------------------------
final_columns = [
    "timestamp",
    "Date",
    "Hour",
    "purchase_bid_mwh",
    "sell_bid_mwh",
    "mcv_mwh",
    "final_scheduled_volume_mwh",
    "mcp_rs_per_mwh",
    "weighted_mcp_rs_per_mwh",
    "source_year",
    "source_file",
]

combined = combined[final_columns]

# ------------------------------------------------------------
# 13. Export clean master dataset
# ------------------------------------------------------------
final_path = OUTPUT_DIR / "iex_dam_hourly_2022_2025.csv"

combined.to_csv(final_path, index=False)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
print(f"Final rows : {len(combined):,}")
print(f"Final file :\n{final_path}")
print("\nDo NOT manually edit this file. Regenerate it from the raw files.")
