"""
EnergyCast V1 — Step 10: Linear Regression & Ridge Regularization Models
Trains interpretable linear baselines, tunes Ridge alpha on Validation (2024),
and evaluates out-of-sample on Test (2025).
"""

from pathlib import Path
import json
import joblib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "predictions"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "models" / "linear"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
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
    
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2.0
    valid_mask = denominator > 1e-4
    smape = np.mean(np.abs(y_true[valid_mask] - y_pred[valid_mask]) / denominator[valid_mask]) * 100.0
    
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1.0 - (ss_res / (ss_tot + 1e-8))
    
    return {
        "MAE": round(float(mae), 2),
        "RMSE": round(float(rmse), 2),
        "sMAPE": round(float(smape), 2),
        "R2": round(float(r2), 4)
    }

def train_and_evaluate_linear_models():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 10: LINEAR & RIDGE REGRESSION PIPELINE")
    print("===========================================================================")
    
    # 1. Load Datasets
    print("Loading partitioned datasets from:", SPLITS_DIR)
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df   = pd.read_csv(SPLITS_DIR / "val.csv")
    test_df  = pd.read_csv(SPLITS_DIR / "test.csv")
    
    for df in [train_df, val_df, test_df]:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
    print(f"Loaded Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    # 2. Separate Target and Feature Matrix
    target_col = "mcp_rs_per_mwh"
    ignore_cols = ["timestamp", target_col]
    feature_cols = [c for c in train_df.columns if c not in ignore_cols]
    print(f"Total Predictive Features (p): {len(feature_cols)}")

    X_train_raw = train_df[feature_cols].values
    y_train = train_df[target_col].values

    X_val_raw = val_df[feature_cols].values
    y_val = val_df[target_col].values

    X_test_raw = test_df[feature_cols].values
    y_test = test_df[target_col].values

    # 3. Fit Scaler Strictly on Training Data (Zero Leakage)
    print("Fitting StandardScaler strictly on Training set (2022-2023)...")
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_val   = scaler.transform(X_val_raw)
    X_test  = scaler.transform(X_test_raw)
    
    joblib.dump(scaler, MODEL_DIR / "feature_scaler.joblib")
    print("Saved feature_scaler.joblib to:", MODEL_DIR)

    # 4. Train Ordinary Least Squares (OLS) Linear Regression
    print("\n--- Training Ordinary Least Squares (OLS) ---")
    ols = LinearRegression()
    ols.fit(X_train, y_train)
    joblib.dump(ols, MODEL_DIR / "linear_regression.joblib")

    ols_val_pred = ols.predict(X_val)
    ols_test_pred = ols.predict(X_test)

    m_ols_val = calculate_metrics(y_val, ols_val_pred)
    m_ols_test = calculate_metrics(y_test, ols_test_pred)
    print(f"OLS Validation -> MAE: Rs {m_ols_val['MAE']}, RMSE: Rs {m_ols_val['RMSE']}, sMAPE: {m_ols_val['sMAPE']}%, R2: {m_ols_val['R2']}")
    print(f"OLS Test       -> MAE: Rs {m_ols_test['MAE']}, RMSE: Rs {m_ols_test['RMSE']}, sMAPE: {m_ols_test['sMAPE']}%, R2: {m_ols_test['R2']}")

    # 5. Tune Ridge Regularization Parameter (Alpha) on Validation Set
    print("\n--- Tuning Ridge Regularization Penalty (Alpha) ---")
    alphas = [0.01, 0.1, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0, 5000.0]
    tuning_records = []

    best_alpha = None
    best_val_mae = float("inf")
    best_ridge_model = None

    for alpha in alphas:
        r_model = Ridge(alpha=alpha, random_state=42)
        r_model.fit(X_train, y_train)
        pred_val = r_model.predict(X_val)
        m_val = calculate_metrics(y_val, pred_val)
        
        tuning_records.append({
            "Alpha": alpha,
            "Val_MAE": m_val["MAE"],
            "Val_RMSE": m_val["RMSE"],
            "Val_sMAPE": m_val["sMAPE"],
            "Val_R2": m_val["R2"]
        })
        
        if m_val["MAE"] < best_val_mae:
            best_val_mae = m_val["MAE"]
            best_alpha = alpha
            best_ridge_model = r_model

    tuning_df = pd.DataFrame(tuning_records)
    print(f"Optimal Alpha chosen based on Validation MAE: Alpha = {best_alpha} (Val MAE: Rs {best_val_mae})")
    joblib.dump(best_ridge_model, MODEL_DIR / "ridge_regression.joblib")
    tuning_df.to_csv(TABLE_DIR / "ridge_alpha_tuning_results.csv", index=False)

    # 6. Evaluate Best Ridge Model on Validation and Out-of-Sample Test Sets
    ridge_val_pred = best_ridge_model.predict(X_val)
    ridge_test_pred = best_ridge_model.predict(X_test)

    m_ridge_val = calculate_metrics(y_val, ridge_val_pred)
    m_ridge_test = calculate_metrics(y_test, ridge_test_pred)
    print(f"Best Ridge (alpha={best_alpha}) Validation -> MAE: Rs {m_ridge_val['MAE']}, RMSE: Rs {m_ridge_val['RMSE']}, sMAPE: {m_ridge_val['sMAPE']}%, R2: {m_ridge_val['R2']}")
    print(f"Best Ridge (alpha={best_alpha}) Test       -> MAE: Rs {m_ridge_test['MAE']}, RMSE: Rs {m_ridge_test['RMSE']}, sMAPE: {m_ridge_test['sMAPE']}%, R2: {m_ridge_test['R2']}")

    # 7. Compile and Save Metrics Summary Table
    metrics_summary = pd.DataFrame([
        {"Model": "Linear Regression (OLS)", "Split": "Validation (2024)", "Hyperparameters": "None", **m_ols_val},
        {"Model": "Linear Regression (OLS)", "Split": "Test (2025)", "Hyperparameters": "None", **m_ols_test},
        {"Model": f"Ridge Regression (alpha={best_alpha}) ★", "Split": "Validation (2024)", "Hyperparameters": f"alpha={best_alpha}", **m_ridge_val},
        {"Model": f"Ridge Regression (alpha={best_alpha}) ★", "Split": "Test (2025)", "Hyperparameters": f"alpha={best_alpha}", **m_ridge_test},
    ])
    metrics_summary.to_csv(TABLE_DIR / "linear_ridge_metrics.csv", index=False)
    metrics_summary.to_csv(OUTPUT_DIR / "linear_ridge_metrics.csv", index=False)

    # 8. Extract Standardized Coefficients Table
    coef_df = pd.DataFrame({
        "Feature": feature_cols,
        "OLS_Coefficient": ols.coef_,
        "Ridge_Coefficient": best_ridge_model.coef_,
        "Abs_Ridge_Weight": np.abs(best_ridge_model.coef_)
    }).sort_values(by="Abs_Ridge_Weight", ascending=False).reset_index(drop=True)
    coef_df.to_csv(TABLE_DIR / "ridge_standardized_coefficients.csv", index=False)

    # 9. Save Predictions Tables
    val_out = val_df[["timestamp", target_col]].copy()
    val_out["pred_ols"] = ols_val_pred
    val_out["pred_ridge"] = ridge_val_pred
    val_out.to_csv(OUTPUT_DIR / "linear_ridge_val_predictions.csv", index=False)

    test_out = test_df[["timestamp", target_col]].copy()
    test_out["pred_ols"] = ols_test_pred
    test_out["pred_ridge"] = ridge_test_pred
    test_out.to_csv(OUTPUT_DIR / "linear_ridge_test_predictions.csv", index=False)
    print(f"Predictions saved to: {OUTPUT_DIR}")

    # 10. Generate Figures
    generate_linear_figures(tuning_df, coef_df, test_df, ridge_test_pred, y_test, best_alpha)

    print("===========================================================================")
    print("STEP 10 LINEAR & RIDGE REGRESSION PIPELINE COMPLETED SUCCESSFULLY!")
    print("===========================================================================")
    return metrics_summary, coef_df

def generate_linear_figures(tuning_df, coef_df, test_df, ridge_test_pred, y_test, best_alpha):
    print("Generating diagnostic visualisations for Linear/Ridge...")

    # Figure 1: Ridge Alpha Regularization Tuning Curve
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()

    l1 = ax1.plot(tuning_df["Alpha"], tuning_df["Val_MAE"], color=PRIMARY_COLOR, marker="o", lw=2, label="Validation MAE (₹/MWh)")
    l2 = ax2.plot(tuning_df["Alpha"], tuning_df["Val_RMSE"], color=ACCENT_COLOR, marker="s", ls="--", lw=2, label="Validation RMSE (₹/MWh)")
    
    ax1.axvline(best_alpha, color=GOLD_COLOR, ls=":", lw=1.8, label=f"Optimal α = {best_alpha}")

    ax1.set_xscale("log")
    ax1.set_xlabel("Regularization Strength α (Log Scale)")
    ax1.set_ylabel("Validation MAE (₹/MWh)", color=PRIMARY_COLOR)
    ax2.set_ylabel("Validation RMSE (₹/MWh)", color=ACCENT_COLOR)
    ax1.set_title("Figure 1: Ridge Regularization Path (Alpha Tuning on Validation Set)", fontweight="bold")
    
    lines = l1 + l2 + [plt.Line2D([0], [0], color=GOLD_COLOR, ls=":", lw=1.8)]
    labels = ["Val MAE", "Val RMSE", f"Optimal α = {best_alpha}"]
    ax1.legend(lines, labels, loc="center left", frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_linear01_ridge_alpha_tuning.png", dpi=300)
    plt.close(fig)

    # Figure 2: Top 20 Standardized Ridge Coefficients
    top_20 = coef_df.head(20).sort_values("Ridge_Coefficient", ascending=True)
    
    fig, ax = plt.subplots(figsize=(11, 8))
    colors = [ACCENT_COLOR if c < 0 else PRIMARY_COLOR for c in top_20["Ridge_Coefficient"]]
    ax.barh(top_20["Feature"], top_20["Ridge_Coefficient"], color=colors, alpha=0.85, height=0.65)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title("Figure 2: Top 20 Standardized Ridge Regression Coefficients (β)", fontweight="bold")
    ax.set_xlabel("Standardized Weight (Impact on MCP in ₹/MWh per 1σ change)")
    ax.set_ylabel("Predictive Feature")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_linear02_standardized_coefficients.png", dpi=300)
    plt.close(fig)

    # Figure 3: Actual vs Predicted Parity Plot on Test Set
    fig, ax = plt.subplots(figsize=(7, 7))
    sample_idx = np.random.choice(len(y_test), size=min(2500, len(y_test)), replace=False)
    ax.scatter(y_test[sample_idx], ridge_test_pred[sample_idx], alpha=0.25, color=SECONDARY_COLOR, s=12, label="Test Observations")
    
    # 45-degree parity line
    min_val = min(y_test.min(), ridge_test_pred.min())
    max_val = max(y_test.max(), ridge_test_pred.max())
    ax.plot([min_val, max_val], [min_val, max_val], color=ACCENT_COLOR, ls="--", lw=1.8, label="Ideal Parity Line (y = ŷ)")
    
    ax.set_title("Figure 3: Ridge Predicted vs Actual MCP on Test Set (2025)", fontweight="bold")
    ax.set_xlabel("Ground Truth MCP (₹/MWh)")
    ax.set_ylabel("Ridge Predicted MCP (₹/MWh)")
    ax.set_xlim(0, 11000)
    ax.set_ylim(0, 11000)
    ax.xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_linear03_actual_vs_predicted_scatter.png", dpi=300)
    plt.close(fig)

    # Figure 4: 14-Day Forecast Tracking Sample
    sample_df = test_df.iloc[1000:1336].copy()
    sample_df["ridge_pred"] = ridge_test_pred[1000:1336]
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(sample_df["timestamp"], sample_df["mcp_rs_per_mwh"], color=PRIMARY_COLOR, lw=2, label="Actual Ground Truth MCP")
    ax.plot(sample_df["timestamp"], sample_df["mcp_lag_24"], color=GOLD_COLOR, lw=1.2, ls=":", label="Daily sNaive Benchmark (Lag 24)")
    ax.plot(sample_df["timestamp"], sample_df["ridge_pred"], color=GREEN_COLOR, lw=1.8, ls="--", label="Ridge Regression Forecast")
    
    ax.set_title("Figure 4: Ridge Regression vs Seasonal Naive Forecast Tracking (14-Day Test Horizon)", fontweight="bold")
    ax.set_ylabel("Market Clearing Price (₹/MWh)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper right", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_linear04_forecast_tracking_sample.png", dpi=300)
    plt.close(fig)

    # Figure 5: Hourly MAE Profile Comparison (Ridge vs sNaive)
    test_analysis = test_df.copy()
    test_analysis["hour"] = test_analysis["timestamp"].dt.hour
    test_analysis["err_snaive"] = np.abs(test_analysis["mcp_rs_per_mwh"] - test_analysis["mcp_lag_24"])
    test_analysis["err_ridge"] = np.abs(test_analysis["mcp_rs_per_mwh"] - ridge_test_pred)
    
    hourly_comparison = test_analysis.groupby("hour")[["err_snaive", "err_ridge"]].mean()
    
    fig, ax = plt.subplots(figsize=(12, 5.5))
    hours = np.arange(24)
    ax.plot(hours, hourly_comparison["err_snaive"], marker="o", color=GOLD_COLOR, lw=2, label="Daily sNaive (24h) Hourly MAE")
    ax.plot(hours, hourly_comparison["err_ridge"], marker="^", color=GREEN_COLOR, lw=2.2, label="Ridge Regression Hourly MAE")
    
    ax.axvspan(18, 22, color="red", alpha=0.1, label="Critical Evening Peak Hours (18:00 - 22:00)")
    ax.set_title("Figure 5: Hourly MAE Profile: Ridge Regression vs Seasonal Naive Benchmark", fontweight="bold")
    ax.set_xlabel("Hour of Day (0 to 23)")
    ax.set_ylabel("Mean Absolute Error (₹/MWh)")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_linear05_hourly_mae_profile.png", dpi=300)
    plt.close(fig)
    print("All diagnostic visualisations exported to:", FIG_DIR)

if __name__ == "__main__":
    train_and_evaluate_linear_models()
