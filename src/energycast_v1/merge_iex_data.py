from pathlib import Path
import pandas as pd

# -------------------------------------------------
# PATHS
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "iex"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "iex"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------
# FIND ALL MONTHLY IEX FILES
# -------------------------------------------------

files = sorted(
    list(RAW_DIR.rglob("*.xlsx")) +
    list(RAW_DIR.rglob("*.xls"))
)

print(f"\nFound {len(files)} IEX files.\n")

if len(files) == 0:
    raise FileNotFoundError(
        f"No Excel files found inside: {RAW_DIR}"
    )


# -------------------------------------------------
# READ FILES
# -------------------------------------------------

dataframes = []

for file in files:

    print(f"Reading: {file.name}")

    try:
        df = pd.read_excel(file)

        # Remove completely empty rows/columns
        df = df.dropna(how="all")
        df = df.dropna(axis=1, how="all")

        # Helpful for tracing any problem back to raw data
        df["source_file"] = file.name

        dataframes.append(df)

        print(
            f"   Rows: {len(df):,} | "
            f"Columns: {len(df.columns)}"
        )

    except Exception as e:
        print(f"ERROR reading {file.name}: {e}")


# -------------------------------------------------
# CHECK THAT SOMETHING WAS LOADED
# -------------------------------------------------

if len(dataframes) == 0:
    raise RuntimeError("No IEX files could be loaded.")


# -------------------------------------------------
# MERGE EVERYTHING
# -------------------------------------------------

combined = pd.concat(
    dataframes,
    ignore_index=True,
    sort=False
)

print("\n--------------------------------")
print("MERGE COMPLETED")
print("--------------------------------")

print(f"Total rows before cleaning: {len(combined):,}")
print(f"Total columns: {len(combined.columns)}")

print("\nColumns:")
for col in combined.columns:
    print(f" - {col}")


# -------------------------------------------------
# REMOVE EXACT DUPLICATE ROWS
# -------------------------------------------------

before = len(combined)

combined = combined.drop_duplicates()

after = len(combined)

print(f"\nExact duplicate rows removed: {before - after}")


# -------------------------------------------------
# EXPORT MASTER RAW-COMBINED DATASET
# -------------------------------------------------

output_file = (
    OUTPUT_DIR /
    "iex_dam_hourly_2022_2025.csv"
)

combined.to_csv(
    output_file,
    index=False
)

print("\nMaster dataset saved:")
print(output_file)

print(f"\nFinal rows: {len(combined):,}")
print(f"Final columns: {len(combined.columns)}")