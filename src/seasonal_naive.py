"""
EnergyCast V1 — Step 9: Seasonal Naive Baseline Models
Implements Daily Seasonal Naive (s=24) and Weekly Seasonal Naive (s=168) benchmarks.
"""

from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "predictions"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "models" / "snaive"
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

def calculate_metrics(y_true, y_pred):
    """Computes MAE, RMSE, sMAPE, and R2."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # sMAPE bounded between 0% and 200%
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    # Avoid zero division
    valid_mask = denominator > 1e-4
    smape = np.mean(np.abs(y_true[valid_mask] - y_pred[valid_mask]) / denominator[valid_mask]) * 100.0
    
    # R2
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1.0 - (ss_res / (ss_tot + 1e-8))
    
    return {
        "MAE": round(float(mae), 2),
        "RMSE": round(float(rmse), 2),
        "sMAPE": round(float(smape), 2),
        "R2": round(float(r2), 4)
    }

def run_seasonal_naive():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 9: SEASONAL NAIVE BASELINE")
    print("===========================================================================")
    
    # Load splits
    print("Loading partitioned datasets from:", SPLITS_DIR)
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df   = pd.read_csv(SPLITS_DIR / "val.csv")
    test_df  = pd.read_csv(SPLITS_DIR / "test.csv")
    
    for df in [train_df, val_df, test_df]:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    print(f"Loaded Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    # Seasonal Naive Formulations:
    # 1. Daily Seasonal Naive: y_hat_t = y_{t-24} (mcp_lag_24)
    # 2. Weekly Seasonal Naive: y_hat_t = y_{t-168} (mcp_lag_168)
    # 3. Simple Naive (Persistence): y_hat_t = y_{t-1} (mcp_lag_1)
    
    models = {
        "Daily_Seasonal_Naive_24h": "mcp_lag_24",
        "Weekly_Seasonal_Naive_168h": "mcp_lag_168",
        "Simple_Persistence_1h": "mcp_lag_1"
    }

    results = []

    for split_name, s_df in [("Validation (2024)", val_df), ("Test (2025)", test_df), ("Train (2022-2023)", train_df)]:
        y_true = s_df["mcp_rs_per_mwh"]
        for model_name, lag_col in models.items():
            y_pred = s_df[lag_col]
            m = calculate_metrics(y_true, y_pred)
            results.append({
                "Split": split_name,
                "Model": model_name,
                "Predictor_Feature": lag_col,
                "MAE": m["MAE"],
                "RMSE": m["RMSE"],
                "sMAPE": m["sMAPE"],
                "R2": m["R2"],
                "Observations": len(s_df)
            })

    results_df = pd.DataFrame(results)
    print("\n--- Benchmark Performance Metrics ---")
    print(results_df.to_string(index=False))

    # Save metrics table
    results_df.to_csv(TABLE_DIR / "seasonal_naive_metrics.csv", index=False)
    results_df.to_csv(OUTPUT_DIR / "seasonal_naive_metrics.csv", index=False)

    # Save prediction tables for Val and Test
    val_preds = val_df[["timestamp", "mcp_rs_per_mwh", "mcp_lag_1", "mcp_lag_24", "mcp_lag_168"]].copy()
    val_preds.columns = ["timestamp", "actual_mcp", "pred_persistence_1h", "pred_daily_snaive_24h", "pred_weekly_snaive_168h"]
    val_preds.to_csv(OUTPUT_DIR / "snaive_val_predictions.csv", index=False)

    test_preds = test_df[["timestamp", "mcp_rs_per_mwh", "mcp_lag_1", "mcp_lag_24", "mcp_lag_168"]].copy()
    test_preds.columns = ["timestamp", "actual_mcp", "pred_persistence_1h", "pred_daily_snaive_24h", "pred_weekly_snaive_168h"]
    test_preds.to_csv(OUTPUT_DIR / "snaive_test_predictions.csv", index=False)
    print(f"\nPredictions saved to: {OUTPUT_DIR}")

    # Generate Figures
    generate_snaive_figures(test_df)

    print("===========================================================================")
    print("STEP 9 SEASONAL NAIVE BASELINE COMPLETED SUCCESSFULLY!")
    print("===========================================================================")
    return results_df

def generate_snaive_figures(test_df):
    print("Generating Seasonal Naive diagnostic figures...")
    
    # 1. 2-Week Forecast Tracking Sample on Test Set
    sample = test_df.iloc[1000:1336] # 14 days (336 hours)
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(sample["timestamp"], sample["mcp_rs_per_mwh"], color=PRIMARY_COLOR, lw=2, label="Actual Ground Truth MCP")
    ax.plot(sample["timestamp"], sample["mcp_lag_24"], color=GOLD_COLOR, lw=1.5, ls="--", label="Daily Seasonal Naive (Lag 24)")
    ax.plot(sample["timestamp"], sample["mcp_lag_168"], color=ACCENT_COLOR, lw=1.2, ls=":", label="Weekly Seasonal Naive (Lag 168)")
    
    ax.set_title("Figure 1: Seasonal Naive Benchmark Tracking (14-Day Test Horizon Sample)", fontweight="bold")
    ax.set_ylabel("Market Clearing Price (Rs/MWh)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper right", frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_snaive01_forecast_tracking_sample.png", dpi=300)
    plt.close(fig)

    # 2. Residual Error Distribution
    err_24 = test_df["mcp_rs_per_mwh"] - test_df["mcp_lag_24"]
    err_168 = test_df["mcp_rs_per_mwh"] - test_df["mcp_lag_168"]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    sns.histplot(err_24, bins=60, kde=True, color=GOLD_COLOR, ax=axes[0], edgecolor="white")
    axes[0].axvline(0, color="black", ls="--", lw=1)
    axes[0].axvline(err_24.mean(), color=ACCENT_COLOR, ls=":", lw=1.5, label=f"Mean Error: Rs {err_24.mean():.1f}")
    axes[0].set_title("Figure 2A: Daily sNaive (24h) Residual Error Distribution", fontweight="bold")
    axes[0].set_xlabel("Forecast Error (Actual - Predicted) (Rs/MWh)")
    axes[0].set_xlim(-8000, 8000)
    axes[0].legend()
    
    sns.histplot(err_168, bins=60, kde=True, color=ACCENT_COLOR, ax=axes[1], edgecolor="white")
    axes[1].axvline(0, color="black", ls="--", lw=1)
    axes[1].axvline(err_168.mean(), color=PRIMARY_COLOR, ls=":", lw=1.5, label=f"Mean Error: Rs {err_168.mean():.1f}")
    axes[1].set_title("Figure 2B: Weekly sNaive (168h) Residual Error Distribution", fontweight="bold")
    axes[1].set_xlabel("Forecast Error (Actual - Predicted) (Rs/MWh)")
    axes[1].set_xlim(-8000, 8000)
    axes[1].legend()

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_snaive02_error_residuals_distribution.png", dpi=300)
    plt.close(fig)

    # 3. Hourly MAE Profile (Where does sNaive fail?)
    test_df_copy = test_df.copy()
    test_df_copy["hour"] = test_df_copy["timestamp"].dt.hour
    test_df_copy["err_24"] = np.abs(test_df_copy["mcp_rs_per_mwh"] - test_df_copy["mcp_lag_24"])
    test_df_copy["err_168"] = np.abs(test_df_copy["mcp_rs_per_mwh"] - test_df_copy["mcp_lag_168"])
    
    hourly_mae = test_df_copy.groupby("hour")[["err_24", "err_168"]].mean()
    
    fig, ax = plt.subplots(figsize=(12, 5.5))
    hours = np.arange(24)
    ax.plot(hours, hourly_mae["err_24"], marker="o", color=GOLD_COLOR, lw=2, label="Daily sNaive (24h) Hourly MAE")
    ax.plot(hours, hourly_mae["err_168"], marker="s", color=ACCENT_COLOR, lw=2, label="Weekly sNaive (168h) Hourly MAE")
    
    ax.axvspan(18, 22, color="red", alpha=0.1, label="Critical Evening Peak Hours (18:00 - 22:00)")
    ax.set_title("Figure 3: Hourly MAE Error Profile (Peak Hour Vulnerability Analysis)", fontweight="bold")
    ax.set_xlabel("Hour of Day (0 to 23)")
    ax.set_ylabel("Mean Absolute Error (Rs/MWh)")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_snaive03_hourly_error_profile.png", dpi=300)
    plt.close(fig)
    print("All diagnostic figures exported to:", FIG_DIR)

if __name__ == "__main__":
    run_seasonal_naive()
