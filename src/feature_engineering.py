"""
EnergyCast V1 — Step 7: Feature Engineering Pipeline
Constructs a comprehensive, leakage-free feature matrix for hourly electricity price forecasting.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "master" / "energycast_master_hourly_2022_2025.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "features"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "features"
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

def engineer_features():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 7: FEATURE ENGINEERING PIPELINE")
    print("===========================================================================")
    print(f"Loading master dataset: {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    initial_rows = len(df)
    print(f"Initial raw master rows: {initial_rows:,}")

    # Interpolate rare SCADA telemetry dropouts (4 isolated hours out of 28,344 where demand was 0)
    dropout_mask = (df["demand_mw"] == 0)
    if dropout_mask.any():
        print(f"Interpolating {dropout_mask.sum()} SCADA telemetry dropout hours...")
        for col in ["demand_mw", "solar_generation_mw", "wind_generation_mw"]:
            df.loc[dropout_mask, col] = np.nan
            df[col] = df[col].interpolate(method="linear")

    # 1. Base Target
    # mcp_rs_per_mwh (Target variable at hour t)
    target_series = df["mcp_rs_per_mwh"]

    # 2. Strict Leakage-Free Autoregressive Price Lags
    # Because target is at time t, lag_k must be shift(k)
    print("Engineering autoregressive price lags (1, 2, 24, 48, 168)...")
    df["mcp_lag_1"] = target_series.shift(1)
    df["mcp_lag_2"] = target_series.shift(2)
    df["mcp_lag_24"] = target_series.shift(24)
    df["mcp_lag_48"] = target_series.shift(48)
    df["mcp_lag_168"] = target_series.shift(168)

    # 3. Price Differencing & Momentum Features
    # Hourly momentum: change from t-2 to t-1
    print("Engineering price momentum & velocity metrics...")
    df["mcp_diff_1_2"] = df["mcp_lag_1"] - df["mcp_lag_2"]
    # Daily momentum: change from t-25 to t-1
    df["mcp_diff_24_25"] = df["mcp_lag_1"] - target_series.shift(25)
    # Price ratio relative to 24h ago
    df["mcp_ratio_1_24"] = df["mcp_lag_1"] / (df["mcp_lag_24"] + 1e-4)

    # 4. Rolling Volatility & Regime Statistics (Strictly over shifted target to avoid leakage)
    print("Engineering rolling statistical features (24h, 168h windows)...")
    shifted_target = target_series.shift(1)  # Most recently observed price prior to forecast hour t
    
    # 24-hour rolling window
    roll24 = shifted_target.rolling(window=24, min_periods=24)
    df["mcp_rolling_mean_24"] = roll24.mean()
    df["mcp_rolling_std_24"] = roll24.std()
    df["mcp_rolling_min_24"] = roll24.min()
    df["mcp_rolling_max_24"] = roll24.max()
    # Standardized price shock z-score
    df["mcp_zscore_24"] = (df["mcp_lag_1"] - df["mcp_rolling_mean_24"]) / (df["mcp_rolling_std_24"] + 1e-4)

    # 168-hour (7-day) rolling window
    roll168 = shifted_target.rolling(window=168, min_periods=168)
    df["mcp_rolling_mean_168"] = roll168.mean()
    df["mcp_rolling_std_168"] = roll168.std()

    # 5. Power System & Grid Features (Net Demand & Renewables)
    print("Engineering grid metrics (Net Demand, RE Penetration, Ramps, Lags)...")
    total_re = df["solar_generation_mw"] + df["wind_generation_mw"]
    df["net_demand_mw"] = df["demand_mw"] - total_re
    df["re_penetration_pct"] = (total_re / df["demand_mw"]) * 100.0
    
    # Lagged grid metrics
    df["net_demand_lag_1"] = df["net_demand_mw"].shift(1)
    df["net_demand_lag_24"] = df["net_demand_mw"].shift(24)
    df["demand_lag_1"] = df["demand_mw"].shift(1)
    df["demand_lag_24"] = df["demand_mw"].shift(24)
    df["solar_lag_24"] = df["solar_generation_mw"].shift(24)
    df["wind_lag_24"] = df["wind_generation_mw"].shift(24)
    
    # Grid ramp requirement (thermal peaker ramp rate)
    df["net_demand_ramp_1"] = df["net_demand_mw"] - df["net_demand_lag_1"]

    # 6. Lagged Market Liquidity & Bidding Ratios
    print("Engineering market liquidity & bid tightness features...")
    df["purchase_bid_lag_24"] = df["purchase_bid_mwh"].shift(24)
    df["sell_bid_lag_24"] = df["sell_bid_mwh"].shift(24)
    df["mcv_lag_24"] = df["mcv_mwh"].shift(24)
    df["market_tightness_lag_24"] = df["purchase_bid_lag_24"] / (df["sell_bid_lag_24"] + 1e-4)

    # 7. Meteorological & Non-linear Weather Features
    print("Engineering meteorological cooling elasticity features...")
    df["cdd_24"] = np.maximum(0.0, df["temperature_mean_c"] - 24.0)
    df["temperature_sq"] = df["temperature_mean_c"] ** 2
    df["temperature_lag_24"] = df["temperature_mean_c"].shift(24)

    # 8. Calendar & Cyclical Temporal Encodings
    print("Engineering continuous cyclical encodings (sin/cos transformations)...")
    hour = df["timestamp"].dt.hour
    dow = df["timestamp"].dt.dayofweek
    month = df["timestamp"].dt.month

    # Diurnal (Period = 24)
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    # Weekly (Period = 7)
    df["day_of_week_sin"] = np.sin(2 * np.pi * dow / 7.0)
    df["day_of_week_cos"] = np.cos(2 * np.pi * dow / 7.0)

    # Annual (Period = 12)
    df["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * month / 12.0)

    # Indicator Features
    df["is_weekend"] = dow.isin([5, 6]).astype(int)
    df["is_peak_hour"] = hour.isin([18, 19, 20, 21, 22]).astype(int)
    df["is_solar_hour"] = hour.between(9, 16).astype(int)

    # 9. Cross-Feature Physical Interactions
    print("Engineering physical interaction terms...")
    df["net_demand_x_peak"] = df["net_demand_mw"] * df["is_peak_hour"]
    df["net_demand_x_cdd"] = df["net_demand_mw"] * df["cdd_24"]

    # 10. Drop Burn-In Window & Drop Contemporaneous Market Clearing Variables
    max_lag = 168
    print(f"\nDropping initial burn-in window of {max_lag} hours due to weekly lag (168)...")
    feature_df = df.iloc[max_lag:].reset_index(drop=True)
    
    # Strictly prevent data leakage: drop unlagged market clearing outcomes for hour t
    leakage_cols = [
        "weighted_mcp_rs_per_mwh",
        "purchase_bid_mwh",
        "sell_bid_mwh",
        "mcv_mwh",
        "final_scheduled_volume_mwh"
    ]
    print(f"Dropping {len(leakage_cols)} contemporaneous market clearing variables to prevent data leakage...")
    feature_df = feature_df.drop(columns=leakage_cols)
    
    null_counts = feature_df.isnull().sum()
    total_nulls = null_counts.sum()
    print(f"Total nulls in feature matrix: {total_nulls}")
    if total_nulls > 0:
        print("Warning! Columns with nulls:")
        print(null_counts[null_counts > 0])
        raise ValueError("Null values detected in feature matrix!")

    final_rows, final_cols = feature_df.shape
    print(f"Final clean feature matrix: {final_rows:,} rows × {final_cols} columns")
    print(f"Time range: {feature_df['timestamp'].min()} to {feature_df['timestamp'].max()}")

    # 11. Save Processed Feature Matrix
    out_csv = OUTPUT_DIR / "energycast_features_hourly_2022_2025.csv"
    print(f"Saving feature matrix to: {out_csv}")
    feature_df.to_csv(out_csv, index=False)

    # 12. Create Feature Dictionary
    create_feature_dictionary(feature_df)

    # 13. Generate Feature Visualizations
    generate_feature_figures(feature_df)

    print("===========================================================================")
    print("STEP 7 FEATURE ENGINEERING PIPELINE COMPLETED SUCCESSFULLY!")
    print("===========================================================================")
    return feature_df

def create_feature_dictionary(df):
    print("Creating comprehensive feature dictionary...")
    meta = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        if col == "timestamp":
            desc = "Synchronized hourly timestamp (UTC+05:30 / IST)"
            category = "Index / Temporal"
            math_formula = "t"
        elif col == "mcp_rs_per_mwh":
            desc = "Market Clearing Price on IEX Day-Ahead Market in Rs/MWh (Forecasting Target)"
            category = "Target Variable"
            math_formula = "y_t"
        elif "mcp_lag" in col:
            k = col.split("_")[-1]
            desc = f"Autoregressive price lag at t - {k} hours"
            category = "Autoregressive Price Lag"
            math_formula = f"y_{{t-{k}}}"
        elif "mcp_diff" in col:
            desc = "Price velocity / differencing momentum metric"
            category = "Price Momentum"
            math_formula = "y_{t-1} - y_{t-k}"
        elif "mcp_ratio" in col:
            desc = "Price ratio relative to same-hour yesterday"
            category = "Price Momentum"
            math_formula = "y_{t-1} / (y_{t-24} + eps)"
        elif "rolling" in col:
            desc = "Moving statistical summary over past historical price (leakage-free shifted)"
            category = "Rolling Volatility Regime"
            math_formula = "f(y_{t-1}, ..., y_{t-W})"
        elif col == "mcp_zscore_24":
            desc = "Standardized daily price shock z-score relative to 24h moving mean and std"
            category = "Volatility Shock Indicator"
            math_formula = "(y_{t-1} - mu_24) / (sigma_24 + eps)"
        elif "net_demand" in col:
            desc = "Residual national power demand to be cleared by dispatchable generation"
            category = "Power System / Grid"
            math_formula = "Demand_t - (Solar_t + Wind_t)"
        elif "re_penetration" in col:
            desc = "Renewable energy generation share as a percentage of total national demand"
            category = "Power System / Renewables"
            math_formula = "[(Solar_t + Wind_t) / Demand_t] * 100"
        elif "_sin" in col or "_cos" in col:
            desc = "Orthogonal continuous circular transformation of cyclical calendar integer"
            category = "Cyclical Calendar"
            math_formula = "sin(2*pi*t / T) or cos(2*pi*t / T)"
        elif "is_" in col:
            desc = "Binary calendar or operating regime indicator flag (0 or 1)"
            category = "Calendar Indicator"
            math_formula = "I(condition)"
        elif "cdd" in col:
            desc = "Cooling Degree Days representing meteorological cooling elasticity above 24°C"
            category = "Meteorological Transformation"
            math_formula = "max(0, Temp - 24)"
        elif "_sq" in col:
            desc = "Quadratic polynomial term capturing non-linear cooling demand response"
            category = "Meteorological Transformation"
            math_formula = "Temp^2"
        elif "tightness" in col:
            desc = "Market liquidity bidding pressure ratio (lagged buyer bids over seller bids)"
            category = "Market Liquidity"
            math_formula = "PurchaseBid_{t-24} / (SellBid_{t-24} + eps)"
        elif "_x_" in col:
            desc = "Cross-domain interaction term capturing compounded physical/market stress"
            category = "Interaction Term"
            math_formula = "Feature_A * Feature_B"
        else:
            desc = "Synchronized exogenous physical, market, or weather variable"
            category = "Exogenous Input"
            math_formula = "x_t"

        meta.append({
            "Feature_Name": col,
            "Category": category,
            "Data_Type": dtype,
            "Mathematical_Formula": math_formula,
            "Description": desc
        })

    dict_df = pd.DataFrame(meta)
    dict_df.to_csv(OUTPUT_DIR / "energycast_feature_dictionary.csv", index=False)
    dict_df.to_csv(TABLE_DIR / "energycast_feature_dictionary.csv", index=False)
    print(f"Feature dictionary saved ({len(dict_df)} features recorded).")

def generate_feature_figures(df):
    print("Generating feature visualisations...")

    # Figure 1: Cyclical Encodings (Unit Circle Mapping)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    
    # 1A: 24-Hour Cycle Circle
    sample_hours = df.drop_duplicates(subset=["hour_sin", "hour_cos"]).sort_values("hour_sin")
    axes[0].scatter(sample_hours["hour_cos"], sample_hours["hour_sin"], color=PRIMARY_COLOR, s=60, zorder=3)
    circle = plt.Circle((0, 0), 1.0, color="#CCCCCC", fill=False, linestyle="--", linewidth=1.2)
    axes[0].add_artist(circle)
    axes[0].axhline(0, color="gray", linewidth=0.6)
    axes[0].axvline(0, color="gray", linewidth=0.6)
    axes[0].set_xlim(-1.25, 1.25)
    axes[0].set_ylim(-1.25, 1.25)
    axes[0].set_aspect('equal')
    axes[0].set_title("Figure 1A: 24-Hour Continuous Cyclical Unit Circle", fontweight="bold")
    axes[0].set_xlabel("hour_cos = cos(2π · hour / 24)")
    axes[0].set_ylabel("hour_sin = sin(2π · hour / 24)")

    # 1B: Waveform over 48 hours
    sub_48 = df.iloc[0:48]
    axes[1].plot(range(48), sub_48["hour_sin"], color=SECONDARY_COLOR, linewidth=2, label="hour_sin (Sine Component)")
    axes[1].plot(range(48), sub_48["hour_cos"], color=ACCENT_COLOR, linewidth=2, linestyle="--", label="hour_cos (Cosine Component)")
    axes[1].set_title("Figure 1B: Orthogonal Harmonic Waveforms (48-Hour Sample)", fontweight="bold")
    axes[1].set_xlabel("Elapsed Time (Hours)")
    axes[1].set_ylabel("Encoding Value [-1.0, +1.0]")
    axes[1].legend(frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_feat01_cyclical_encodings.png", dpi=300)
    plt.close(fig)

    # Figure 2: Price Lags & Rolling Volatility Bands
    fig, ax = plt.subplots(figsize=(14, 6))
    sub_sample = df.iloc[500:850]  # ~14 days sample
    ax.plot(sub_sample["timestamp"], sub_sample["mcp_rs_per_mwh"], color="#1F4E79", linewidth=1.5, label="Actual MCP (y_t)")
    ax.plot(sub_sample["timestamp"], sub_sample["mcp_lag_24"], color="#E67E22", linewidth=1.2, linestyle=":", label="Daily Lag (y_{t-24})")
    ax.plot(sub_sample["timestamp"], sub_sample["mcp_rolling_mean_24"], color="#27AE60", linewidth=1.8, label="24h Rolling Mean")
    
    # Volatility band: Mean ± 1 Std
    upper_band = sub_sample["mcp_rolling_mean_24"] + sub_sample["mcp_rolling_std_24"]
    lower_band = sub_sample["mcp_rolling_mean_24"] - sub_sample["mcp_rolling_std_24"]
    ax.fill_between(sub_sample["timestamp"], lower_band, upper_band, color="#27AE60", alpha=0.15, label="±1σ Rolling Volatility Band")
    
    ax.set_title("Figure 2: Autoregressive Tracking & Dynamic Volatility Envelope (2-Week Sample)", fontweight="bold")
    ax.set_ylabel("Price (Rs/MWh)")
    ax.set_xlabel("Date")
    ax.legend(loc="upper right", frameon=True)
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_feat02_price_lags_and_rolling_bands.png", dpi=300)
    plt.close(fig)

    # Figure 3: Correlation of Engineered Features with Target
    fig, ax = plt.subplots(figsize=(10, 11))
    numeric_cols = [c for c in df.columns if c not in ["timestamp"]]
    spearman_corr = df[numeric_cols].corr(method="spearman")["mcp_rs_per_mwh"].drop("mcp_rs_per_mwh")
    
    top_corrs = spearman_corr.sort_values(ascending=True)
    colors = [ACCENT_COLOR if v < 0 else PRIMARY_COLOR for v in top_corrs.values]
    
    ax.barh(top_corrs.index, top_corrs.values, color=colors, alpha=0.85, edgecolor="none", height=0.65)
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set_title("Figure 3: Spearman Rank Correlation of All Engineered Features with Target (MCP)", fontweight="bold")
    ax.set_xlabel("Spearman Rank Correlation Coefficient (ρ)")
    ax.set_ylabel("Engineered Feature")
    ax.grid(True, linestyle="--", alpha=0.5, axis="x")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_feat03_feature_correlation_with_target.png", dpi=300)
    plt.close(fig)
    print("All feature visualisations successfully exported to:", FIG_DIR)

if __name__ == "__main__":
    engineer_features()
