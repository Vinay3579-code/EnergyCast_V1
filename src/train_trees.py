"""
EnergyCast V1 — Step 11: Non-Linear Gradient Boosted Trees (LightGBM & XGBoost)
Trains advanced tree ensembles with early stopping on Validation (2024),
evaluates out-of-sample on Test (2025), and extracts feature importances.
"""

from pathlib import Path
import json
import joblib
import lightgbm as lgb
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "predictions"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "models" / "trees"
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
PURPLE_COLOR = "#8E44AD"

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

def train_and_evaluate_tree_models():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 11: GRADIENT BOOSTED TREES PIPELINE")
    print("===========================================================================")
    
    # 1. Load Partitions
    print("Loading partitioned datasets from:", SPLITS_DIR)
    train_df = pd.read_csv(SPLITS_DIR / "train.csv")
    val_df   = pd.read_csv(SPLITS_DIR / "val.csv")
    test_df  = pd.read_csv(SPLITS_DIR / "test.csv")
    
    for df in [train_df, val_df, test_df]:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
    print(f"Loaded Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    target_col = "mcp_rs_per_mwh"
    ignore_cols = ["timestamp", target_col]
    feature_cols = [c for c in train_df.columns if c not in ignore_cols]
    print(f"Total Predictive Features (p): {len(feature_cols)}")

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]

    X_val = val_df[feature_cols]
    y_val = val_df[target_col]

    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    # 2. Train LightGBM Regressor
    print("\n--- Training LightGBM Regressor (Leaf-Wise GBDT) ---")
    lgb_params = {
        "objective": "regression",
        "metric": "l2",
        "boosting_type": "gbdt",
        "n_estimators": 1200,
        "learning_rate": 0.04,
        "num_leaves": 31,
        "max_depth": 6,
        "min_child_samples": 25,
        "subsample": 0.8,
        "subsample_freq": 1,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.5,
        "reg_lambda": 2.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1
    }

    lgb_model = lgb.LGBMRegressor(**lgb_params)
    lgb_model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        eval_names=["train", "val"],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)]
    )

    best_iter_lgb = lgb_model.best_iteration_
    print(f"LightGBM stopped early at iteration: {best_iter_lgb}")
    joblib.dump(lgb_model, MODEL_DIR / "lightgbm_model.joblib")

    lgb_val_pred = lgb_model.predict(X_val)
    lgb_test_pred = lgb_model.predict(X_test)

    m_lgb_val = calculate_metrics(y_val, lgb_val_pred)
    m_lgb_test = calculate_metrics(y_test, lgb_test_pred)
    print(f"LightGBM Validation -> MAE: Rs {m_lgb_val['MAE']}, RMSE: Rs {m_lgb_val['RMSE']}, sMAPE: {m_lgb_val['sMAPE']}%, R2: {m_lgb_val['R2']}")
    print(f"LightGBM Test       -> MAE: Rs {m_lgb_test['MAE']}, RMSE: Rs {m_lgb_test['RMSE']}, sMAPE: {m_lgb_test['sMAPE']}%, R2: {m_lgb_test['R2']}")

    # 3. Train XGBoost Regressor
    print("\n--- Training XGBoost Regressor (Second-Order Exact Newton GBDT) ---")
    xgb_params = {
        "objective": "reg:squarederror",
        "eval_metric": "rmse",
        "n_estimators": 1200,
        "learning_rate": 0.04,
        "max_depth": 6,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 1.0,
        "reg_lambda": 5.0,
        "random_state": 42,
        "n_jobs": -1,
        "early_stopping_rounds": 50
    }

    xgb_model = xgb.XGBRegressor(**xgb_params)
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=False
    )

    best_iter_xgb = xgb_model.best_iteration
    print(f"XGBoost stopped early at iteration: {best_iter_xgb}")
    joblib.dump(xgb_model, MODEL_DIR / "xgboost_model.joblib")

    xgb_val_pred = xgb_model.predict(X_val)
    xgb_test_pred = xgb_model.predict(X_test)

    m_xgb_val = calculate_metrics(y_val, xgb_val_pred)
    m_xgb_test = calculate_metrics(y_test, xgb_test_pred)
    print(f"XGBoost Validation -> MAE: Rs {m_xgb_val['MAE']}, RMSE: Rs {m_xgb_val['RMSE']}, sMAPE: {m_xgb_val['sMAPE']}%, R2: {m_xgb_val['R2']}")
    print(f"XGBoost Test       -> MAE: Rs {m_xgb_test['MAE']}, RMSE: Rs {m_xgb_test['RMSE']}, sMAPE: {m_xgb_test['sMAPE']}%, R2: {m_xgb_test['R2']}")

    # 4. Save Metrics Summary Table
    tree_metrics = pd.DataFrame([
        {"Model": "LightGBM Regressor ★", "Split": "Validation (2024)", "Best_Iteration": best_iter_lgb, **m_lgb_val},
        {"Model": "LightGBM Regressor ★", "Split": "Test (2025)", "Best_Iteration": best_iter_lgb, **m_lgb_test},
        {"Model": "XGBoost Regressor", "Split": "Validation (2024)", "Best_Iteration": best_iter_xgb, **m_xgb_val},
        {"Model": "XGBoost Regressor", "Split": "Test (2025)", "Best_Iteration": best_iter_xgb, **m_xgb_test},
    ])
    tree_metrics.to_csv(TABLE_DIR / "tree_models_metrics.csv", index=False)
    tree_metrics.to_csv(OUTPUT_DIR / "tree_models_metrics.csv", index=False)

    # 5. Extract Feature Importances (Gain and Split)
    print("\nExtracting feature importance rankings...")
    lgb_gain = lgb_model.booster_.feature_importance(importance_type="gain")
    lgb_split = lgb_model.booster_.feature_importance(importance_type="split")
    xgb_gain = xgb_model.feature_importances_  # Normalized gain

    feat_imp = pd.DataFrame({
        "Feature": feature_cols,
        "LGBM_Gain": lgb_gain,
        "LGBM_Split": lgb_split,
        "XGB_Gain": xgb_gain
    }).sort_values(by="LGBM_Gain", ascending=False).reset_index(drop=True)
    
    feat_imp.to_csv(TABLE_DIR / "tree_feature_importances.csv", index=False)

    # 6. Save Predictions Tables
    val_preds = val_df[["timestamp", target_col]].copy()
    val_preds["pred_lightgbm"] = lgb_val_pred
    val_preds["pred_xgboost"] = xgb_val_pred
    val_preds.to_csv(OUTPUT_DIR / "trees_val_predictions.csv", index=False)

    test_preds = test_df[["timestamp", target_col]].copy()
    test_preds["pred_lightgbm"] = lgb_test_pred
    test_preds["pred_xgboost"] = xgb_test_pred
    test_preds.to_csv(OUTPUT_DIR / "trees_test_predictions.csv", index=False)
    print("Predictions saved to:", OUTPUT_DIR)

    # 7. Generate Publication Figures
    generate_tree_figures(lgb_model, xgb_model, feat_imp, test_df, lgb_test_pred, xgb_test_pred, y_test)

    print("===========================================================================")
    print("STEP 11 GRADIENT BOOSTED TREES PIPELINE COMPLETED SUCCESSFULLY!")
    print("===========================================================================")
    return tree_metrics, feat_imp

def generate_tree_figures(lgb_model, xgb_model, feat_imp, test_df, lgb_test_pred, xgb_test_pred, y_test):
    print("Generating diagnostic visualisations for Tree Ensembles...")

    # Figure 1: Training & Validation Learning Curves
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # LightGBM Loss
    lgb_history = lgb_model.evals_result_
    axes[0].plot(lgb_history["train"]["l2"], color=PRIMARY_COLOR, lw=1.5, label="Train L2 Loss")
    axes[0].plot(lgb_history["val"]["l2"], color=ACCENT_COLOR, lw=1.8, label="Validation L2 Loss")
    axes[0].axvline(lgb_model.best_iteration_, color=GOLD_COLOR, ls=":", lw=1.5, label=f"Best Iter ({lgb_model.best_iteration_})")
    axes[0].set_title("Figure 1A: LightGBM Early Stopping Loss Convergence", fontweight="bold")
    axes[0].set_xlabel("Boosting Iterations (Trees)")
    axes[0].set_ylabel("Mean Squared Error (₹²/MWh²)")
    axes[0].set_yscale("log")
    axes[0].legend(frameon=True)

    # XGBoost Loss
    xgb_history = xgb_model.evals_result()
    axes[1].plot(xgb_history["validation_0"]["rmse"], color=PRIMARY_COLOR, lw=1.5, label="Train RMSE")
    axes[1].plot(xgb_history["validation_1"]["rmse"], color=ACCENT_COLOR, lw=1.8, label="Validation RMSE")
    axes[1].axvline(xgb_model.best_iteration, color=GOLD_COLOR, ls=":", lw=1.5, label=f"Best Iter ({xgb_model.best_iteration})")
    axes[1].set_title("Figure 1B: XGBoost Early Stopping RMSE Convergence", fontweight="bold")
    axes[1].set_xlabel("Boosting Iterations (Trees)")
    axes[1].set_ylabel("Root Mean Squared Error (₹/MWh)")
    axes[1].legend(frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_trees01_training_learning_curves.png", dpi=300)
    plt.close(fig)

    # Figure 2: Top 20 Feature Importance (Gain)
    top_20 = feat_imp.head(20).sort_values("LGBM_Gain", ascending=True)
    
    fig, ax = plt.subplots(figsize=(11, 8))
    norm_gain = top_20["LGBM_Gain"] / top_20["LGBM_Gain"].max() * 100.0
    ax.barh(top_20["Feature"], norm_gain, color=SECONDARY_COLOR, alpha=0.85, height=0.65)
    ax.set_title("Figure 2: Top 20 Feature Importances by Total Split Gain (LightGBM)", fontweight="bold")
    ax.set_xlabel("Relative Total Gain (% of Top Feature)")
    ax.set_ylabel("Predictive Feature")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_trees02_top_feature_importance.png", dpi=300)
    plt.close(fig)

    # Figure 3: Test Set Actual vs Predicted Parity Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sample_idx = np.random.choice(len(y_test), size=min(2500, len(y_test)), replace=False)
    
    # LightGBM Parity
    axes[0].scatter(y_test.iloc[sample_idx], lgb_test_pred[sample_idx], alpha=0.25, color=GREEN_COLOR, s=12, label="Test Observations")
    axes[0].plot([0, 11000], [0, 11000], color=ACCENT_COLOR, ls="--", lw=1.8, label="Ideal Parity Line (y = ŷ)")
    axes[0].axvline(10000, color="gray", ls=":", lw=1.2, label="₹10k Price Cap")
    axes[0].axhline(10000, color="gray", ls=":", lw=1.2)
    axes[0].set_title("Figure 3A: LightGBM Parity Plot on Test Set (2025)", fontweight="bold")
    axes[0].set_xlabel("Ground Truth MCP (₹/MWh)")
    axes[0].set_ylabel("LightGBM Predicted MCP (₹/MWh)")
    axes[0].set_xlim(0, 11000)
    axes[0].set_ylim(0, 11000)
    axes[0].legend(loc="upper left", frameon=True)

    # XGBoost Parity
    axes[1].scatter(y_test.iloc[sample_idx], xgb_test_pred[sample_idx], alpha=0.25, color=PURPLE_COLOR, s=12, label="Test Observations")
    axes[1].plot([0, 11000], [0, 11000], color=ACCENT_COLOR, ls="--", lw=1.8, label="Ideal Parity Line (y = ŷ)")
    axes[1].axvline(10000, color="gray", ls=":", lw=1.2, label="₹10k Price Cap")
    axes[1].axhline(10000, color="gray", ls=":", lw=1.2)
    axes[1].set_title("Figure 3B: XGBoost Parity Plot on Test Set (2025)", fontweight="bold")
    axes[1].set_xlabel("Ground Truth MCP (₹/MWh)")
    axes[1].set_ylabel("XGBoost Predicted MCP (₹/MWh)")
    axes[1].set_xlim(0, 11000)
    axes[1].set_ylim(0, 11000)
    axes[1].legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_trees03_test_parity_plots.png", dpi=300)
    plt.close(fig)

    # Figure 4: 14-Day Horizon Time-Series Forecast Tracking
    sample_df = test_df.iloc[1000:1336].copy()
    sample_df["lgb_pred"] = lgb_test_pred[1000:1336]
    sample_df["xgb_pred"] = xgb_test_pred[1000:1336]
    
    # Load Ridge pred for comparison
    ridge_test_path = PROJECT_ROOT / "outputs" / "predictions" / "linear_ridge_test_predictions.csv"
    if ridge_test_path.exists():
        ridge_p = pd.read_csv(ridge_test_path)["pred_ridge"].values
        sample_df["ridge_pred"] = ridge_p[1000:1336]

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(sample_df["timestamp"], sample_df["mcp_rs_per_mwh"], color=PRIMARY_COLOR, lw=2.2, label="Actual Ground Truth MCP")
    if "ridge_pred" in sample_df.columns:
        ax.plot(sample_df["timestamp"], sample_df["ridge_pred"], color=GOLD_COLOR, lw=1.2, ls=":", label="Ridge Regression (Step 10)")
    ax.plot(sample_df["timestamp"], sample_df["lgb_pred"], color=GREEN_COLOR, lw=1.8, ls="--", label="LightGBM GBDT (Step 11)")
    
    ax.set_title("Figure 4: Model Hierarchy Forecast Tracking Comparison (14-Day Test Horizon)", fontweight="bold")
    ax.set_ylabel("Market Clearing Price (₹/MWh)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper right", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_trees04_14day_forecast_tracking.png", dpi=300)
    plt.close(fig)

    # Figure 5: Hourly MAE Comparison Across All Model Families
    test_analysis = test_df.copy()
    test_analysis["hour"] = test_analysis["timestamp"].dt.hour
    test_analysis["err_lgb"] = np.abs(test_analysis["mcp_rs_per_mwh"] - lgb_test_pred)
    test_analysis["err_xgb"] = np.abs(test_analysis["mcp_rs_per_mwh"] - xgb_test_pred)
    
    # Pull sNaive and Ridge errors
    snaive_path = PROJECT_ROOT / "outputs" / "predictions" / "snaive_test_predictions.csv"
    if snaive_path.exists():
        snaive_p = pd.read_csv(snaive_path)["pred_daily_snaive_24h"].values
        test_analysis["err_snaive"] = np.abs(test_analysis["mcp_rs_per_mwh"] - snaive_p)
    if ridge_test_path.exists():
        test_analysis["err_ridge"] = np.abs(test_analysis["mcp_rs_per_mwh"] - ridge_p)

    hourly_comp = test_analysis.groupby("hour").mean(numeric_only=True)

    fig, ax = plt.subplots(figsize=(12, 5.5))
    hours = np.arange(24)
    if "err_snaive" in hourly_comp.columns:
        ax.plot(hours, hourly_comp["err_snaive"], marker="o", color=GOLD_COLOR, lw=1.8, ls=":", label="1. Daily sNaive Benchmark (Step 9)")
    if "err_ridge" in hourly_comp.columns:
        ax.plot(hours, hourly_comp["err_ridge"], marker="s", color=SECONDARY_COLOR, lw=1.8, ls="--", label="2. Ridge Regression Baseline (Step 10)")
    ax.plot(hours, hourly_comp["err_lgb"], marker="^", color=GREEN_COLOR, lw=2.4, label="3. LightGBM GBDT (Step 11 ★ Champion)")
    ax.plot(hours, hourly_comp["err_xgb"], marker="d", color=PURPLE_COLOR, lw=2.0, label="4. XGBoost GBDT (Step 11)")

    ax.axvspan(18, 22, color="red", alpha=0.1, label="Critical Evening Peak (18:00 - 22:00)")
    ax.set_title("Figure 5: The Three-Family Model Hierarchy: Hourly MAE Error Profiles", fontweight="bold")
    ax.set_xlabel("Hour of Day (0 to 23)")
    ax.set_ylabel("Mean Absolute Error (₹/MWh)")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig_trees05_hourly_mae_profile_comparison.png", dpi=300)
    plt.close(fig)
    print("All diagnostic figures exported to:", FIG_DIR)

if __name__ == "__main__":
    train_and_evaluate_tree_models()

