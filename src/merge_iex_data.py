from pathlib import Path
import calendar
import pandas as pd

# ============================================================
# EnergyCast V1 - Clean IEX DAM Hourly Merger
# Designed for:
# EnergyCast_V1/
#   data/raw/iex/2022...2025/*.xlsx
#   src/energycast_v1/merge_iex_data.py
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "iex"
OUTPUT_DIR = Path("V:/College/7th SEM/SDP/EnergyCast_V1/data/processed/iex")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_COLUMNS = [
    "Date",
    "Hour",
    "Purchase Bid (MWh)",
    "Sell Bid (MWh)",
    "MCV (MWh)",
    "Final Scheduled Volume (MWh)",
    "MCP (Rs/MWh) *",
    "Weighted MCP (Rs/MWh)",
]

MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

print("=" * 72)
print("ENERGYCAST V1 - IEX DAM HOURLY DATA VALIDATOR + MERGER")
print("=" * 72)
print(f"Project root : {PROJECT_ROOT}")
print(f"Raw folder   : {RAW_DIR}")

files = sorted(RAW_DIR.rglob("*.xlsx"))

print(f"Excel files found: {len(files)}")

if len(files) != 45:
    raise RuntimeError(
        f"Expected 45 monthly files (Apr 2022-Dec 2025), found {len(files)}."
    )

frames = []
validation_rows = []
errors = []

for idx, file in enumerate(files, start=1):
    year_text = file.parent.name
    month_text = file.stem.lower()

    try:
        expected_year = int(year_text)
    except ValueError:
        errors.append(f"{file}: parent folder is not a numeric year.")
        continue

    expected_month = MONTH_MAP.get(month_text)

    if expected_month is None:
        errors.append(f"{file}: cannot infer month from filename '{file.stem}'.")
        continue

    df = pd.read_excel(
        file,
        sheet_name=0,
        header=4,
        engine="openpyxl",
    )

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"{file}: missing columns {missing_cols}")
        continue

    df = df[EXPECTED_COLUMNS].copy()

    # --------------------------------------------------------
    # CRITICAL:
    # IEX monthly exports contain extra rows such as:
    # Total, Max, Min, Avg and Summary.
    # Only Hour 1...24 are actual hourly market observations.
    # --------------------------------------------------------
    numeric_hour = pd.to_numeric(df["Hour"], errors="coerce")
    hourly = df.loc[numeric_hour.between(1, 24)].copy()
    hourly["Hour"] = pd.to_numeric(hourly["Hour"], errors="raise").astype(int)

    hourly["Date"] = pd.to_datetime(
        hourly["Date"],
        dayfirst=True,
        errors="coerce",
    )

    invalid_dates = int(hourly["Date"].isna().sum())

    expected_days = calendar.monthrange(expected_year, expected_month)[1]
    expected_rows = expected_days * 24

    actual_min = hourly["Date"].min()
    actual_max = hourly["Date"].max()

    correct_year_month = (
        invalid_dates == 0
        and actual_min is not pd.NaT
        and actual_max is not pd.NaT
        and actual_min.year == expected_year
        and actual_max.year == expected_year
        and actual_min.month == expected_month
        and actual_max.month == expected_month
    )

    correct_row_count = len(hourly) == expected_rows

    status = "OK" if (correct_year_month and correct_row_count) else "FAIL"

    validation_rows.append(
        {
            "source_file": str(file.relative_to(RAW_DIR)),
            "expected_year": expected_year,
            "expected_month": expected_month,
            "actual_start_date": actual_min,
            "actual_end_date": actual_max,
            "expected_hourly_rows": expected_rows,
            "actual_hourly_rows": len(hourly),
            "invalid_dates": invalid_dates,
            "status": status,
        }
    )

    print(
        f"[{idx:02d}/45] {file.relative_to(RAW_DIR)} -> "
        f"{len(hourly):4d}/{expected_rows:4d} hourly rows -> {status}"
    )

    if status == "FAIL":
        errors.append(
            f"{file.relative_to(RAW_DIR)}: expected "
            f"{expected_year}-{expected_month:02d}, "
            f"but data range is {actual_min} to {actual_max}, "
            f"rows={len(hourly)} (expected {expected_rows})."
        )
        continue

    hourly["source_year"] = expected_year
    hourly["source_file"] = file.name
    frames.append(hourly)

# Save validation report even if a bad source file is found.
validation_df = pd.DataFrame(validation_rows)
validation_path = OUTPUT_DIR / "iex_monthly_validation.csv"
validation_df.to_csv(validation_path, index=False)

print(f"\nValidation report saved:\n{validation_path}")

if errors:
    print("\n" + "=" * 72)
    print("SOURCE DATA VALIDATION FAILED")
    print("=" * 72)
    for err in errors:
        print(" -", err)

    raise RuntimeError(
        "\nFix the source file(s) listed above and rerun the script. "
        "No final master dataset was produced."
    )

# ------------------------------------------------------------
# Merge only validated hourly rows
# ------------------------------------------------------------
combined = pd.concat(frames, ignore_index=True)

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

# IEX Hour 1 = 00:00-01:00, Hour 24 = 23:00-24:00.
combined["timestamp"] = (
    combined["Date"]
    + pd.to_timedelta(combined["Hour"] - 1, unit="h")
)

combined = combined.sort_values("timestamp").reset_index(drop=True)

# ------------------------------------------------------------
# Strict final quality checks
# ------------------------------------------------------------
EXPECTED_START = pd.Timestamp("2022-04-01 00:00:00")
EXPECTED_END = pd.Timestamp("2025-12-31 23:00:00")

expected_timeline = pd.date_range(
    EXPECTED_START,
    EXPECTED_END,
    freq="h",
)

duplicate_mask = combined["timestamp"].duplicated(keep=False)
duplicate_rows = int(duplicate_mask.sum())

actual_timestamps = pd.DatetimeIndex(combined["timestamp"])
missing_timestamps = expected_timeline.difference(actual_timestamps)

extra_timestamps = actual_timestamps.difference(expected_timeline)

missing_mcp = int(combined["mcp_rs_per_mwh"].isna().sum())

print("\n" + "=" * 72)
print("FINAL QUALITY CHECK")
print("=" * 72)
print(f"Rows                    : {len(combined):,}")
print(f"Expected rows           : {len(expected_timeline):,}")
print(f"First timestamp         : {combined['timestamp'].min()}")
print(f"Last timestamp          : {combined['timestamp'].max()}")
print(f"Duplicate hourly rows   : {duplicate_rows}")
print(f"Missing hourly timestamps: {len(missing_timestamps)}")
print(f"Extra timestamps        : {len(extra_timestamps)}")
print(f"Missing hourly MCP      : {missing_mcp}")

quality_errors = []

if len(combined) != len(expected_timeline):
    quality_errors.append(
        f"row count {len(combined)} != expected {len(expected_timeline)}"
    )

if duplicate_rows:
    quality_errors.append(f"{duplicate_rows} duplicate hourly rows")

if len(missing_timestamps):
    quality_errors.append(
        f"{len(missing_timestamps)} missing hourly timestamps"
    )

if len(extra_timestamps):
    quality_errors.append(
        f"{len(extra_timestamps)} timestamps outside expected range"
    )

if missing_mcp:
    quality_errors.append(f"{missing_mcp} hourly MCP values are missing")

if quality_errors:
    raise RuntimeError(
        "Final quality check failed: " + "; ".join(quality_errors)
    )

# ------------------------------------------------------------
# Final clean master output
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

final_path = OUTPUT_DIR / "iex_dam_hourly_2022_2025.csv"
combined.to_csv(final_path, index=False)

# Remove stale diagnostic files from the older merger if they exist.
for stale_name in [
    "iex_duplicate_timestamps.csv",
    "iex_missing_timestamps.csv",
]:
    stale_path = OUTPUT_DIR / stale_name
    if stale_path.exists():
        stale_path.unlink()

print("\n" + "=" * 72)
print("SUCCESS")
print("=" * 72)
print(f"Clean master dataset:\n{final_path}")
print("\nIEX price-data Step 1 has passed all validation checks.")