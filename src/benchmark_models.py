"""
EnergyCast V1 - Step 12: Model Benchmarking, Statistical Significance & Master Evaluation
Comprehensive evaluation across all model tiers:
  - Non-parametric: Persistence (1h), Daily Seasonal Naive (24h), Weekly Seasonal Naive (168h)
  - Linear / Regularized: OLS, Ridge Regression (alpha=50.0)
  - Gradient Boosted Trees: XGBoost, LightGBM (Champion)

Key Analyses:
  1. Master Model Leaderboard (Validation & Test: MAE, RMSE, sMAPE, R2, Peak MAE, Off-peak MAE, Spike MAE)
  2. Diebold-Mariano (1995) Statistical Significance Hypothesis Testing (MAE & MSE loss differentials with Newey-West HAC)
  3. Error Distribution & Residual Diagnostics (Kurtosis, Skewness, Jarque-Bera)
  4. Segmented Analysis (Hourly 24h error curve, Peak vs Off-Peak, Spike regimes > 7000 Rs/MWh)
  5. Multi-panel publication-quality figures:
     - fig_bench01_master_leaderboard_bar.png
     - fig_bench02_diebold_mariano_heatmap.png
     - fig_bench03_hourly_mae_profile_all_models.png
     - fig_bench04_cumulative_absolute_loss.png
     - fig_bench05_error_residuals_distribution.png
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

PRED_DIR = PROJECT_ROOT / "outputs" / "predictions"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures" / "benchmarks"

TABLES_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Plotting style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "legend.fontsize": 9.5,
    "figure.titlesize": 14,
    "figure.dpi": 200,
})

MODEL_COLORS = {
    "Weekly Seasonal Naive (168h)": "#7F8C8D",
    "Daily Seasonal Naive (24h)": "#95A5A6",
    "Persistence Naive (1h)": "#BDC3C7",
    "Linear Regression (OLS)": "#E67E22",
    "Ridge Regression (alpha=50)": "#D35400",
    "XGBoost Regressor": "#2980B9",
    "LightGBM Regressor (Champion)": "#27AE60"
}


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute core forecasting evaluation metrics."""
    err = y_true - y_pred
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))
    denom = np.abs(y_true) + np.abs(y_pred)
    smape = 100.0 * np.mean(2.0 * np.abs(err) / np.where(denom == 0, 1e-6, denom))
    
    ss_res = np.sum(err ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "MAE": mae,
        "RMSE": rmse,
        "sMAPE": smape,
        "R2": r2
    }


def diebold_mariano_test(y_true: np.ndarray, y_pred1: np.ndarray, y_pred2: np.ndarray,
                         loss: str = "absolute", h: int = 1) -> tuple:
    """
    Diebold-Mariano (1995) test for equal predictive accuracy.
    Tests H0: E[d_t] = 0 vs H1: E[d_t] != 0 (Two-sided)
    or H1: Model 1 has lower loss than Model 2 (One-sided).
    
    Parameters:
      y_true: Actual values
      y_pred1: Predictions from Model 1 (e.g. Challenger/LightGBM)
      y_pred2: Predictions from Model 2 (e.g. Baseline/Ridge)
      loss: 'absolute' (MAE differential) or 'squared' (MSE differential)
      h: forecast horizon (for h-step ahead, lag truncation for Newey-West)
      
    Returns:
      dm_stat: Test statistic
      p_value_two_sided: Two-tailed p-value
      p_value_one_sided: One-tailed p-value (H1: Model 1 loss < Model 2 loss)
    """
    e1 = y_true - y_pred1
    e2 = y_true - y_pred2
    
    if loss == "absolute":
        d = np.abs(e1) - np.abs(e2)
    elif loss == "squared":
        d = (e1 ** 2) - (e2 ** 2)
    else:
        raise ValueError(f"Unknown loss: {loss}")
        
    T = len(d)
    d_mean = np.mean(d)
    
    # Compute auto-covariances for Newey-West HAC spectral density at frequency 0
    # Rule of thumb for lag truncation: max(1, int(np.floor(4 * (T / 100) ** (2 / 9)))) or h - 1
    max_lag = max(h - 1, int(np.floor(4 * (T / 100) ** (2 / 9))))
    
    # Autocovariance at lag 0
    gamma_0 = np.var(d, ddof=0)
    gamma_sum = 0.0
    
    for lag in range(1, max_lag + 1):
        # Bartlett kernel weight: w_l = 1 - lag / (max_lag + 1)
        w = 1.0 - (lag / (max_lag + 1))
        cov = np.mean((d[lag:] - d_mean) * (d[:-lag] - d_mean))
        gamma_sum += 2.0 * w * cov
        
    lr_var = (gamma_0 + gamma_sum) / T
    if lr_var <= 0:
        lr_var = 1e-12
        
    dm_stat = d_mean / np.sqrt(lr_var)
    
    # Harvey, Leybourne and Newbold (1997) finite sample correction
    hln_corr = np.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    dm_stat_corrected = dm_stat * hln_corr
    
    # p-values from standard normal / t-distribution
    # Using t-distribution with T-1 degrees of freedom as recommended by HLN (1997)
    df = T - 1
    p_two_sided = 2.0 * (1.0 - stats.t.cdf(np.abs(dm_stat_corrected), df=df))
    # One-sided test (H1: d < 0, i.e., Model 1 is significantly better than Model 2)
    p_one_sided = stats.t.cdf(dm_stat_corrected, df=df)
    
    return dm_stat_corrected, p_two_sided, p_one_sided


def load_and_merge_predictions(split_type: str = "test") -> pd.DataFrame:
    """Load and align predictions from all models into a single master evaluation DataFrame."""
    if split_type == "test":
        f_snaive = PRED_DIR / "snaive_test_predictions.csv"
        f_linear = PRED_DIR / "linear_ridge_test_predictions.csv"
        f_trees = PRED_DIR / "trees_test_predictions.csv"
    else:
        f_snaive = PRED_DIR / "snaive_val_predictions.csv"
        f_linear = PRED_DIR / "linear_ridge_val_predictions.csv"
        f_trees = PRED_DIR / "trees_val_predictions.csv"
        
    df_snaive = pd.read_csv(f_snaive)
    df_linear = pd.read_csv(f_linear)
    df_trees = pd.read_csv(f_trees)
    
    # Standardize column naming
    df_snaive["timestamp"] = pd.to_datetime(df_snaive["timestamp"])
    df_linear["timestamp"] = pd.to_datetime(df_linear["timestamp"])
    df_trees["timestamp"] = pd.to_datetime(df_trees["timestamp"])
    
    merged = pd.merge(df_snaive, df_linear[["timestamp", "pred_ols", "pred_ridge"]], on="timestamp", how="inner")
    merged = pd.merge(merged, df_trees[["timestamp", "pred_lightgbm", "pred_xgboost"]], on="timestamp", how="inner")
    
    # Renaming for clean unified representation
    col_mapping = {
        "actual_mcp": "actual_mcp",
        "pred_persistence_1h": "Persistence Naive (1h)",
        "pred_daily_snaive_24h": "Daily Seasonal Naive (24h)",
        "pred_weekly_snaive_168h": "Weekly Seasonal Naive (168h)",
        "pred_ols": "Linear Regression (OLS)",
        "pred_ridge": "Ridge Regression (alpha=50)",
        "pred_xgboost": "XGBoost Regressor",
        "pred_lightgbm": "LightGBM Regressor (Champion)"
    }
    
    return merged.rename(columns=col_mapping)


def main():
    print("=" * 80)
    print("ENERGYCAST V1 - STEP 12: MODEL BENCHMARKING & STATISTICAL EVALUATION")
    print("=" * 80)
    
    # 1. Load Data
    print("\n[1/5] Loading aligned predictions for Validation (2024) and Test (2025)...")
    df_test = load_and_merge_predictions("test")
    df_val = load_and_merge_predictions("val")
    
    print(f"  Test observations: {len(df_test):,} hours ({df_test['timestamp'].min()} to {df_test['timestamp'].max()})")
    print(f"  Val observations:  {len(df_val):,} hours ({df_val['timestamp'].min()} to {df_val['timestamp'].max()})")
    
    models = [
        "Weekly Seasonal Naive (168h)",
        "Daily Seasonal Naive (24h)",
        "Persistence Naive (1h)",
        "Linear Regression (OLS)",
        "Ridge Regression (alpha=50)",
        "XGBoost Regressor",
        "LightGBM Regressor (Champion)"
    ]
    
    # 2. Master Evaluation Leaderboard
    print("\n[2/5] Computing Master Leaderboard metrics across splits and segments...")
    records = []
    
    # Segment definitions
    # Peak hours: 18:00 to 22:00 (hours 18, 19, 20, 21, 22)
    # Off-peak hours: Remaining hours
    # Spike hours: actual_mcp >= 7000 Rs/MWh
    df_test["hour"] = df_test["timestamp"].dt.hour
    df_val["hour"] = df_val["timestamp"].dt.hour
    
    test_is_peak = df_test["hour"].isin([18, 19, 20, 21, 22])
    test_is_spike = df_test["actual_mcp"] >= 7000.0
    
    val_is_peak = df_val["hour"].isin([18, 19, 20, 21, 22])
    val_is_spike = df_val["actual_mcp"] >= 7000.0
    
    print(f"  Test hours breakdown: Total={len(df_test)}, Peak={test_is_peak.sum()}, Off-Peak={(~test_is_peak).sum()}, Spikes(>=7k)={test_is_spike.sum()}")
    
    base_mae_test = None
    for m in models:
        # Test full
        m_test = compute_metrics(df_test["actual_mcp"].values, df_test[m].values)
        if m == "Daily Seasonal Naive (24h)":
            base_mae_test = m_test["MAE"]
            
        # Segments test
        mae_peak_test = np.mean(np.abs(df_test.loc[test_is_peak, "actual_mcp"] - df_test.loc[test_is_peak, m]))
        mae_offpeak_test = np.mean(np.abs(df_test.loc[~test_is_peak, "actual_mcp"] - df_test.loc[~test_is_peak, m]))
        mae_spike_test = np.mean(np.abs(df_test.loc[test_is_spike, "actual_mcp"] - df_test.loc[test_is_spike, m])) if test_is_spike.sum() > 0 else np.nan
        
        # Val full
        m_val = compute_metrics(df_val["actual_mcp"].values, df_val[m].values)
        mae_peak_val = np.mean(np.abs(df_val.loc[val_is_peak, "actual_mcp"] - df_val.loc[val_is_peak, m]))
        mae_offpeak_val = np.mean(np.abs(df_val.loc[~val_is_peak, "actual_mcp"] - df_val.loc[~val_is_peak, m]))
        
        records.append({
            "Tier": "Tier 1: Baselines" if "Naive" in m else ("Tier 2: Linear" if "Linear" in m or "Ridge" in m else "Tier 3: GBDT"),
            "Model": m,
            "Val_MAE": m_val["MAE"],
            "Val_RMSE": m_val["RMSE"],
            "Val_sMAPE": m_val["sMAPE"],
            "Val_R2": m_val["R2"],
            "Test_MAE": m_test["MAE"],
            "Test_RMSE": m_test["RMSE"],
            "Test_sMAPE": m_test["sMAPE"],
            "Test_R2": m_test["R2"],
            "Test_Peak_MAE": mae_peak_test,
            "Test_OffPeak_MAE": mae_offpeak_test,
            "Test_Spike_MAE": mae_spike_test,
        })
        
    df_leaderboard = pd.DataFrame(records)
    df_leaderboard["MAE_Reduction_vs_SNaive_%"] = 100.0 * (base_mae_test - df_leaderboard["Test_MAE"]) / base_mae_test
    
    # Save master leaderboard
    out_lead_csv = TABLES_DIR / "master_model_leaderboard.csv"
    df_leaderboard.to_csv(out_lead_csv, index=False)
    print(f"  [SAVED] Master leaderboard table -> {out_lead_csv}")
    
    # Print clean table to console
    print("\n--- MASTER BENCHMARK LEADERBOARD (TEST 2025) ---")
    lead_print = df_leaderboard[["Model", "Test_MAE", "Test_RMSE", "Test_sMAPE", "Test_R2", "MAE_Reduction_vs_SNaive_%", "Test_Peak_MAE", "Test_Spike_MAE"]].copy()
    lead_print.columns = ["Model", "MAE", "RMSE", "sMAPE%", "R2", "vs SNaive%", "Peak MAE", "Spike MAE"]
    print(lead_print.to_string(index=False))

    # 3. Diebold-Mariano Statistical Significance Matrix
    print("\n[3/5] Performing Diebold-Mariano (1995) Pairwise Statistical Significance Tests...")
    dm_matrix_stat = np.zeros((len(models), len(models)))
    dm_matrix_pval = np.zeros((len(models), len(models)))
    
    # We will test on Test Set (2025) using Absolute Loss (MAE metric)
    y_true_test = df_test["actual_mcp"].values
    
    dm_records = []
    for i, m1 in enumerate(models):
        for j, m2 in enumerate(models):
            if i == j:
                dm_matrix_stat[i, j] = 0.0
                dm_matrix_pval[i, j] = 1.0
            else:
                pred1 = df_test[m1].values
                pred2 = df_test[m2].values
                stat_val, p_two, p_one = diebold_mariano_test(y_true_test, pred1, pred2, loss="absolute", h=24)
                dm_matrix_stat[i, j] = stat_val
                dm_matrix_pval[i, j] = p_two
                
                if i < j:
                    dm_records.append({
                        "Model_1": m1,
                        "Model_2": m2,
                        "DM_Statistic": stat_val,
                        "p_value_two_sided": p_two,
                        "p_value_one_sided_M1_better": p_one,
                        "Significance_at_1%": "Yes (p < 0.01)" if p_two < 0.01 else ("Yes (p < 0.05)" if p_two < 0.05 else "No"),
                        "Superior_Model": m1 if stat_val < 0 else m2
                    })

    df_dm_pairwise = pd.DataFrame(dm_records)
    out_dm_csv = TABLES_DIR / "diebold_mariano_pairwise_tests.csv"
    df_dm_pairwise.to_csv(out_dm_csv, index=False)
    print(f"  [SAVED] Diebold-Mariano pairwise test results -> {out_dm_csv}")
    
    # Highlight Champion comparisons
    print("\n--- CHAMPION LIGHTGBM vs ALL COMPETING ARCHITECTURES (Diebold-Mariano) ---")
    champ_dm = df_dm_pairwise[(df_dm_pairwise["Model_1"] == "LightGBM Regressor (Champion)") | (df_dm_pairwise["Model_2"] == "LightGBM Regressor (Champion)")]
    for _, r in champ_dm.iterrows():
        comp = r["Model_1"] if r["Model_2"] == "LightGBM Regressor (Champion)" else r["Model_2"]
        # stat negative means LightGBM better if LightGBM is Model_1
        stat = r["DM_Statistic"] if r["Model_1"] == "LightGBM Regressor (Champion)" else -r["DM_Statistic"]
        p_val = r["p_value_two_sided"]
        sig = "*** (p < 0.001)" if p_val < 0.001 else ("** (p < 0.01)" if p_val < 0.01 else ("* (p < 0.05)" if p_val < 0.05 else "ns"))
        print(f"  LightGBM vs {comp:32s} : DM-Stat = {stat:+7.3f} | p-value = {p_val:.2e} {sig}")

    # 4. Residual Diagnostics (Kurtosis, Skewness, Normality)
    print("\n[4/5] Computing Residual Error Distribution Diagnostics...")
    res_records = []
    for m in models:
        res = y_true_test - df_test[m].values
        jb_stat, jb_pval = stats.jarque_bera(res)
        res_records.append({
            "Model": m,
            "Mean_Error (Bias)": np.mean(res),
            "Std_Error": np.std(res),
            "Skewness": stats.skew(res),
            "Kurtosis": stats.kurtosis(res),
            "Jarque_Bera_Stat": jb_stat,
            "JB_p_value": jb_pval,
            "Error_P10": np.percentile(res, 10),
            "Error_P50 (Median)": np.median(res),
            "Error_P90": np.percentile(res, 90)
        })
    df_residuals = pd.DataFrame(res_records)
    out_res_csv = TABLES_DIR / "residual_error_diagnostics.csv"
    df_residuals.to_csv(out_res_csv, index=False)
    print(f"  [SAVED] Residual error diagnostics -> {out_res_csv}")
    
    # 5. Publication-Grade Visualizations
    print("\n[5/5] Generating publication-grade benchmark figures...")
    
    # FIGURE 1: Master Leaderboard Horizontal Bar Chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    models_rev = list(reversed(models))
    colors_rev = [MODEL_COLORS[m] for m in models_rev]
    
    # Test MAE
    mae_vals = [df_leaderboard.loc[df_leaderboard["Model"] == m, "Test_MAE"].values[0] for m in models_rev]
    bars1 = ax1.barh(models_rev, mae_vals, color=colors_rev, height=0.6, edgecolor="black", linewidth=0.8, alpha=0.9)
    ax1.set_xlabel("Mean Absolute Error (₹/MWh)", fontweight="bold")
    ax1.set_title("(a) Test Set MAE (Lower is Better)", fontweight="bold", pad=10)
    for bar in bars1:
        w = bar.get_width()
        ax1.text(w + 15, bar.get_y() + bar.get_height() / 2, f"₹{w:.1f}", va="center", fontsize=9, fontweight="bold")
    ax1.set_xlim(0, max(mae_vals) * 1.15)
    
    # Test RMSE
    rmse_vals = [df_leaderboard.loc[df_leaderboard["Model"] == m, "Test_RMSE"].values[0] for m in models_rev]
    bars2 = ax2.barh(models_rev, rmse_vals, color=colors_rev, height=0.6, edgecolor="black", linewidth=0.8, alpha=0.9)
    ax2.set_xlabel("Root Mean Squared Error (₹/MWh)", fontweight="bold")
    ax2.set_title("(b) Test Set RMSE (Lower is Better)", fontweight="bold", pad=10)
    for bar in bars2:
        w = bar.get_width()
        ax2.text(w + 25, bar.get_y() + bar.get_height() / 2, f"₹{w:.1f}", va="center", fontsize=9, fontweight="bold")
    ax2.set_xlim(0, max(rmse_vals) * 1.15)
    
    plt.suptitle("EnergyCast V1 — Master Model Benchmark Leaderboard (Test Set 2025)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig1_path = FIGURES_DIR / "fig_bench01_master_leaderboard_bar.png"
    plt.savefig(fig1_path, dpi=250, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Figure 1 -> {fig1_path.name}")
    
    # FIGURE 2: Diebold-Mariano Heatmap
    fig, ax = plt.subplots(figsize=(10, 8))
    # Format labels for clean display
    short_labels = [
        "W-SNaive",
        "D-SNaive",
        "Persistence",
        "OLS Linear",
        "Ridge (a=50)",
        "XGBoost",
        "LightGBM ★"
    ]
    
    # Mask diagonal
    mask = np.eye(len(models), dtype=bool)
    
    # Colormap: green where row model has significantly lower loss than column model (stat < 0), red if row model is worse (stat > 0)
    cmap = sns.diverging_palette(133, 10, as_cmap=True)
    sns.heatmap(dm_matrix_stat, mask=mask, annot=True, fmt="+.2f", cmap=cmap, center=0.0,
                xticklabels=short_labels, yticklabels=short_labels, cbar_kws={'label': 'DM Test Statistic (Row vs Column)'},
                linewidths=1.0, linecolor="white", ax=ax)
    
    ax.set_title("Diebold-Mariano Pairwise Test Statistic Matrix (HAC Newey-West)\nNegative Value (Green) = Row Model is Statistically Superior to Column Model",
                 fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()
    fig2_path = FIGURES_DIR / "fig_bench02_diebold_mariano_heatmap.png"
    plt.savefig(fig2_path, dpi=250, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Figure 2 -> {fig2_path.name}")
    
    # FIGURE 3: Hourly MAE Profile across all models
    fig, ax = plt.subplots(figsize=(12, 6))
    hours = np.arange(24)
    for m in models:
        hourly_mae = []
        for h in hours:
            sub = df_test[df_test["hour"] == h]
            hourly_mae.append(np.mean(np.abs(sub["actual_mcp"] - sub[m])))
            
        lw = 2.8 if "LightGBM" in m or "Ridge" in m or "Daily" in m else 1.4
        alpha = 1.0 if "LightGBM" in m or "Ridge" in m else 0.75
        linestyle = "-" if "GBM" in m or "XGB" in m or "Ridge" in m else "--"
        ax.plot(hours, hourly_mae, label=m, color=MODEL_COLORS[m], linewidth=lw, alpha=alpha, linestyle=linestyle,
                marker="o" if "LightGBM" in m else None, markersize=4)
        
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
    ax.set_xlabel("Hour of Day (IST)", fontweight="bold")
    ax.set_ylabel("Mean Absolute Error (₹/MWh)", fontweight="bold")
    ax.set_title("EnergyCast V1 — Hourly Error Profile Across All Evaluated Models (Test Set 2025)", fontweight="bold", pad=10)
    
    # Highlight evening peak block
    ax.axvspan(17.5, 22.5, color="#FADBD8", alpha=0.35, label="Evening Peak Ramp (18:00 - 22:00)")
    ax.legend(loc="upper left", frameon=True, framealpha=0.9)
    plt.tight_layout()
    fig3_path = FIGURES_DIR / "fig_bench03_hourly_mae_profile_all_models.png"
    plt.savefig(fig3_path, dpi=250, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Figure 3 -> {fig3_path.name}")

    # FIGURE 4: Cumulative Absolute Forecast Loss Trajectory
    fig, ax = plt.subplots(figsize=(12, 6))
    for m in ["Daily Seasonal Naive (24h)", "Ridge Regression (alpha=50)", "XGBoost Regressor", "LightGBM Regressor (Champion)"]:
        abs_loss = np.abs(df_test["actual_mcp"].values - df_test[m].values)
        cum_loss = np.cumsum(abs_loss) / 1000.0  # in thousand Rs
        lw = 2.5 if "LightGBM" in m else 1.8
        ax.plot(df_test["timestamp"], cum_loss, label=f"{m} (Final: ₹{cum_loss[-1]:,.0f}k)", color=MODEL_COLORS[m], linewidth=lw)
        
    ax.set_xlabel("Test Set Timeline (Jan 2025 - May 2025)", fontweight="bold")
    ax.set_ylabel("Cumulative Absolute Loss (₹ Thousand)", fontweight="bold")
    ax.set_title("EnergyCast V1 — Cumulative Error Accumulation over 4,200 Unseen Test Hours", fontweight="bold", pad=10)
    ax.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    fig4_path = FIGURES_DIR / "fig_bench04_cumulative_absolute_loss.png"
    plt.savefig(fig4_path, dpi=250, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Figure 4 -> {fig4_path.name}")
    
    # FIGURE 5: Residual Error Distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    for m in ["Daily Seasonal Naive (24h)", "Ridge Regression (alpha=50)", "LightGBM Regressor (Champion)"]:
        res = df_test["actual_mcp"].values - df_test[m].values
        # Filter extreme tails for plotting density cleanly
        res_clipped = np.clip(res, -3000, 3000)
        sns.kdeplot(res_clipped, label=f"{m} (Std: ₹{np.std(res):.1f})", color=MODEL_COLORS[m], linewidth=2.2, ax=ax)
        
    ax.axvline(0, color="black", linestyle="--", alpha=0.6)
    ax.set_xlabel("Residual Error: Actual MCP - Predicted MCP (₹/MWh)", fontweight="bold")
    ax.set_ylabel("Probability Density", fontweight="bold")
    ax.set_title("EnergyCast V1 — Error Distribution Comparison: Density & Zero-Concentration", fontweight="bold", pad=10)
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    fig5_path = FIGURES_DIR / "fig_bench05_error_residuals_distribution.png"
    plt.savefig(fig5_path, dpi=250, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Figure 5 -> {fig5_path.name}")

    print("\n" + "=" * 80)
    print("STEP 12 BENCHMARKING PIPELINE SUCCESSFULLY COMPLETED!")
    print("=" * 80)


if __name__ == "__main__":
    main()

