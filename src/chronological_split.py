"""
EnergyCast V1 — Step 8: Chronological Train / Validation / Test Splitting Pipeline
Strict temporal splitting preserving the arrow of time with zero forward-looking leakage.
"""

from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "features" / "energycast_features_hourly_2022_2025.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "splits"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# Styling
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 300,
    "figure.autolayout": True
})

PRIMARY_COLOR = "#1F4E79"
SECONDARY_COLOR = "#2E75B6"
ACCENT_COLOR = "#D9534F"
GOLD_COLOR = "#E67E22"
GREEN_COLOR = "#27AE60"

def perform_chronological_split():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 8: CHRONOLOGICAL SPLIT PIPELINE")
    print("===========================================================================")
    print(f"Loading feature matrix from: {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    total_rows = len(df)
    print(f"Total features rows loaded: {total_rows:,} (Columns: {df.shape[1]})")
    print(f"Full Timeline: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Temporal Cutoff Boundaries
    # Train: 2022-04-08 00:00:00 -> 2023-12-31 23:00:00 (approx 21 months)
    # Val:   2024-01-01 00:00:00 -> 2024-12-31 23:00:00 (full leap year 2024)
    # Test:  2025-01-01 00:00:00 -> 2025-06-24 23:00:00 (final out-of-sample forward test)

    train_end = pd.Timestamp("2023-12-31 23:00:00")
    val_start = pd.Timestamp("2024-01-01 00:00:00")
    val_end   = pd.Timestamp("2024-12-31 23:00:00")
    test_start = pd.Timestamp("2025-01-01 00:00:00")

    train_mask = (df["timestamp"] <= train_end)
    val_mask   = (df["timestamp"] >= val_start) & (df["timestamp"] <= val_end)
    test_mask  = (df["timestamp"] >= test_start)

    train_df = df[train_mask].reset_index(drop=True)
    val_df   = df[val_mask].reset_index(drop=True)
    test_df  = df[test_mask].reset_index(drop=True)

    # Verification of completeness and disjointness
    n_train = len(train_df)
    n_val   = len(val_df)
    n_test  = len(test_df)
    n_sum   = n_train + n_val + n_test

    print("\n--- Split Verification ---")
    print(f"Train Set: {n_train:,} hours ({n_train/total_rows*100:.2f}%) | {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")
    print(f"Val Set:   {n_val:,} hours ({n_val/total_rows*100:.2f}%) | {val_df['timestamp'].min()} to {val_df['timestamp'].max()}")
    print(f"Test Set:  {n_test:,} hours ({n_test/total_rows*100:.2f}%) | {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    print(f"Sum of Splits: {n_sum:,} / Expected: {total_rows:,}")

    if n_sum != total_rows:
        raise ValueError(f"Split size mismatch: {n_sum} != {total_rows}")
    
    # Save Split Datasets
    print("\nSaving split datasets to:", OUTPUT_DIR)
    train_df.to_csv(OUTPUT_DIR / "train.csv", index=False)
    val_df.to_csv(OUTPUT_DIR / "val.csv", index=False)
    test_df.to_csv(OUTPUT_DIR / "test.csv", index=False)

    # Statistical Comparison Across Splits
    create_split_summaries(train_df, val_df, test_df)

    # Generate Publication Figures
    generate_split_figures(train_df, val_df, test_df, df)

    print("===========================================================================")
    print("STEP 8 CHRONOLOGICAL SPLIT PIPELINE COMPLETED SUCCESSFULLY!")
    print("===========================================================================")
    return train_df, val_df, test_df

def create_split_summaries(train_df, val_df, test_df):
    print("Generating split summary statistics...")
    summary_rows = []
    
    splits = [("Train", train_df), ("Validation", val_df), ("Test", test_df)]
    for name, s_df in splits:
        mcp = s_df["mcp_rs_per_mwh"]
        net_d = s_df["net_demand_mw"]
        re_pen = s_df["re_penetration_pct"]
        temp = s_df["temperature_mean_c"]
        
        summary_rows.append({
            "Split": name,
            "Observations": len(s_df),
            "Start_Time": str(s_df["timestamp"].min()),
            "End_Time": str(s_df["timestamp"].max()),
            "MCP_Mean": round(mcp.mean(), 2),
            "MCP_Median": round(mcp.median(), 2),
            "MCP_Std": round(mcp.std(), 2),
            "MCP_Min": round(mcp.min(), 2),
            "MCP_Max": round(mcp.max(), 2),
            "MCP_Cap_Hits_10k": int((mcp >= 10000).sum()),
            "Cap_Hit_Pct": round((mcp >= 10000).mean() * 100, 2),
            "Net_Demand_Mean_MW": round(net_d.mean(), 2),
            "RE_Penetration_Mean_Pct": round(re_pen.mean(), 2),
            "Temperature_Mean_C": round(temp.mean(), 2)
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(TABLE_DIR / "chronological_split_summary.csv", index=False)
    summary_df.to_csv(OUTPUT_DIR / "split_summary.csv", index=False)
    
    # Save JSON metadata
    meta = {
        "dataset": "EnergyCast V1 Feature Matrix",
        "total_observations": len(train_df) + len(val_df) + len(test_df),
        "split_method": "Strict Chronological Walk-Forward Split (No Shuffling)",
        "train": {
            "rows": len(train_df),
            "pct": round(len(train_df) / (len(train_df) + len(val_df) + len(test_df)) * 100, 2),
            "start": str(train_df["timestamp"].min()),
            "end": str(train_df["timestamp"].max())
        },
        "validation": {
            "rows": len(val_df),
            "pct": round(len(val_df) / (len(train_df) + len(val_df) + len(test_df)) * 100, 2),
            "start": str(val_df["timestamp"].min()),
            "end": str(val_df["timestamp"].max())
        },
        "test": {
            "rows": len(test_df),
            "pct": round(len(test_df) / (len(train_df) + len(val_df) + len(test_df)) * 100, 2),
            "start": str(test_df["timestamp"].min()),
            "end": str(test_df["timestamp"].max())
        }
    }
    with open(OUTPUT_DIR / "split_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print("Split summary tables and JSON metadata exported successfully.")

def generate_split_figures(train_df, val_df, test_df, full_df):
    print("Generating split visualisations...")

    # Figure 1: Full Timeline Partitioning
    fig, ax = plt.subplots(figsize=(15, 6))
    
    ax.plot(train_df["timestamp"], train_df["mcp_rs_per_mwh"], color=PRIMARY_COLOR, alpha=0.55, lw=0.6, label=f"Train Set ({len(train_df):,} hrs / 53.9%)")
    ax.plot(val_df["timestamp"], val_df["mcp_rs_per_mwh"], color=GOLD_COLOR, alpha=0.65, lw=0.6, label=f"Validation Set ({len(val_df):,} hrs / 31.2%)")
    ax.plot(test_df["timestamp"], test_df["mcp_rs_per_mwh"], color=ACCENT_COLOR, alpha=0.75, lw=0.6, label=f"Test Set ({len(test_df):,} hrs / 14.9%)")
    
    # Boundary Cutoff Lines
    ax.axvline(train_df["timestamp"].max(), color="black", linestyle="--", lw=1.2, label="Train / Val Boundary (31-Dec-2023)")
    ax.axvline(val_df["timestamp"].max(), color="black", linestyle=":", lw=1.2, label="Val / Test Boundary (31-Dec-2024)")
    
    # 7-day rolling mean overlay to show structural price trajectory
    rolling_7d = full_df["mcp_rs_per_mwh"].rolling(168).mean()
    ax.plot(full_df["timestamp"], rolling_7d, color="#111111", lw=1.8, label="7-Day Rolling Trend")

    ax.set_title("Figure 1: Chronological Dataset Partitioning (Preserving Temporal Arrow of Time)", fontweight="bold")
    ax.set_ylabel("Market Clearing Price (Rs/MWh)")
    ax.set_xlabel("Timeline (April 2022 to June 2025)")
    ax.set_ylim(0, 21000)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper right", frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_split01_chronological_timeline.png", dpi=300)
    plt.close(fig)

    # Figure 2: Target Distribution Comparison Across Splits
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    
    # Boxplot
    combined_plot_data = pd.concat([
        train_df.assign(Split="Train (2022-2023)"),
        val_df.assign(Split="Validation (2024)"),
        test_df.assign(Split="Test (2025)")
    ])
    
    sns.boxplot(x="Split", y="mcp_rs_per_mwh", data=combined_plot_data, 
                hue="Split", palette=[PRIMARY_COLOR, GOLD_COLOR, ACCENT_COLOR], legend=False, ax=axes[0], 
                flierprops={"marker": ".", "markersize": 2, "alpha": 0.3})
    axes[0].set_title("Figure 2A: Price Dispersion & Spread Across Splits", fontweight="bold")
    axes[0].set_ylabel("MCP (Rs/MWh)")
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # KDE distribution overlay
    sns.kdeplot(train_df["mcp_rs_per_mwh"], color=PRIMARY_COLOR, lw=2, label="Train KDE", ax=axes[1])
    sns.kdeplot(val_df["mcp_rs_per_mwh"], color=GOLD_COLOR, lw=2, label="Validation KDE", ax=axes[1])
    sns.kdeplot(test_df["mcp_rs_per_mwh"], color=ACCENT_COLOR, lw=2, label="Test KDE", ax=axes[1])
    axes[1].axvline(10000, color="gray", linestyle="--", lw=1, label="Regulatory Cap (Rs 10,000)")
    axes[1].set_title("Figure 2B: Kernel Density Estimates of MCP", fontweight="bold")
    axes[1].set_xlabel("MCP (Rs/MWh)")
    axes[1].legend(loc="upper right", frameon=True)
    axes[1].xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_split02_split_distributions.png", dpi=300)
    plt.close(fig)

    # Figure 3: Diurnal Profile Stability Across Splits
    fig, ax = plt.subplots(figsize=(12, 5.5))
    
    h_train = train_df.groupby(train_df["timestamp"].dt.hour)["mcp_rs_per_mwh"].mean()
    h_val   = val_df.groupby(val_df["timestamp"].dt.hour)["mcp_rs_per_mwh"].mean()
    h_test  = test_df.groupby(test_df["timestamp"].dt.hour)["mcp_rs_per_mwh"].mean()
    
    hours = np.arange(24)
    ax.plot(hours, h_train, color=PRIMARY_COLOR, marker="o", lw=2, label="Train Diurnal Profile (2022-2023)")
    ax.plot(hours, h_val, color=GOLD_COLOR, marker="s", lw=2, label="Validation Diurnal Profile (2024)")
    ax.plot(hours, h_test, color=ACCENT_COLOR, marker="^", lw=2, label="Test Diurnal Profile (2025)")
    
    ax.set_title("Figure 3: Diurnal Intra-day Price Profile Stability Across Splits", fontweight="bold")
    ax.set_xlabel("Hour of Day (0 to 23)")
    ax.set_ylabel("Mean Price (Rs/MWh)")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_split03_seasonal_coverage.png", dpi=300)
    plt.close(fig)
    print("All split visualisations exported to:", FIG_DIR)

if __name__ == "__main__":
    perform_chronological_split()
