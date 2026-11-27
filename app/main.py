"""
EnergyCast V1 — Step 14: Interactive Web Application & Real-Time Forecasting Engine
===================================================================================
High-performance Python REST API & Web Application Server for Indian Energy Exchange (IEX)
Day-Ahead Market (DAM) Electricity Price Forecasting, Counterfactual Stress-Testing,
Exact TreeSHAP Attribution, and Econometric Benchmarking.

Run with:
    uv run python app/main.py
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

STATIC_DIR = Path(__file__).resolve().parent / "static"
MODELS_DIR = PROJECT_ROOT / "models"
SPLITS_DIR = PROJECT_ROOT / "data" / "processed" / "splits"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
PRED_DIR = PROJECT_ROOT / "outputs" / "predictions"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures"

# Category mapping for 53 features
CATEGORY_MAPPING = {
    "net_demand_mw": "Physical Grid & Renewables",
    "net_demand_lag_1": "Physical Grid & Renewables",
    "net_demand_lag_24": "Physical Grid & Renewables",
    "net_demand_ramp_1": "Physical Grid & Renewables",
    "re_penetration_pct": "Physical Grid & Renewables",
    "demand_mw": "Physical Grid & Renewables",
    "demand_lag_1": "Physical Grid & Renewables",
    "demand_lag_24": "Physical Grid & Renewables",
    "solar_generation_mw": "Physical Grid & Renewables",
    "solar_lag_24": "Physical Grid & Renewables",
    "wind_generation_mw": "Physical Grid & Renewables",
    "wind_lag_24": "Physical Grid & Renewables",
    "is_solar_hour": "Physical Grid & Renewables",
    "net_demand_x_peak": "Physical Grid & Renewables",
    "net_demand_x_cdd": "Physical Grid & Renewables",
    "mcp_lag_1": "Price History & Momentum",
    "mcp_lag_2": "Price History & Momentum",
    "mcp_lag_24": "Price History & Momentum",
    "mcp_lag_48": "Price History & Momentum",
    "mcp_lag_168": "Price History & Momentum",
    "mcp_diff_1_2": "Price History & Momentum",
    "mcp_diff_24_25": "Price History & Momentum",
    "mcp_ratio_1_24": "Price History & Momentum",
    "mcp_rolling_mean_24": "Price History & Momentum",
    "mcp_rolling_std_24": "Price History & Momentum",
    "mcp_rolling_min_24": "Price History & Momentum",
    "mcp_rolling_max_24": "Price History & Momentum",
    "mcp_zscore_24": "Price History & Momentum",
    "mcp_rolling_mean_168": "Price History & Momentum",
    "mcp_rolling_std_168": "Price History & Momentum",
    "hour_sin": "Calendar & Diurnal",
    "hour_cos": "Calendar & Diurnal",
    "day_of_week_sin": "Calendar & Diurnal",
    "day_of_week_cos": "Calendar & Diurnal",
    "month_sin": "Calendar & Diurnal",
    "month_cos": "Calendar & Diurnal",
    "is_weekend": "Calendar & Diurnal",
    "is_peak_hour": "Calendar & Diurnal",
    "temperature_mean_c": "Weather & Climate",
    "temperature_max_c": "Weather & Climate",
    "temperature_min_c": "Weather & Climate",
    "temperature_lag_24": "Weather & Climate",
    "temperature_sq": "Weather & Climate",
    "apparent_temperature_mean_c": "Weather & Climate",
    "cdd_24": "Weather & Climate",
    "humidity_mean_pct": "Weather & Climate",
    "weather_wind_speed_mean_ms": "Weather & Climate",
    "precipitation_mean_mm": "Weather & Climate",
    "precipitation_max_mm": "Weather & Climate",
    "purchase_bid_lag_24": "Market Bidding Signals",
    "sell_bid_lag_24": "Market Bidding Signals",
    "mcv_lag_24": "Market Bidding Signals",
    "market_tightness_lag_24": "Market Bidding Signals",
}

FEATURE_LABELS = {
    "mcp_lag_24": "MCP Lag-24h (Yesterday Same Hour)",
    "mcp_lag_1": "MCP Lag-1h (Previous Hour)",
    "net_demand_ramp_1": "1h Net Demand Ramp (MW/h)",
    "mcp_diff_24_25": "24h Price Velocity (Lag 1 - Lag 25)",
    "market_tightness_lag_24": "Market Tightness Ratio (Buy/Sell Lag-24h)",
    "net_demand_mw": "System Net Demand (Demand - Solar - Wind)",
    "mcp_lag_48": "MCP Lag-48h (2 Days Ago)",
    "mcp_diff_1_2": "1h Price Acceleration (Lag 1 - Lag 2)",
    "mcp_lag_168": "MCP Lag-168h (Last Week Same Hour)",
    "purchase_bid_lag_24": "Purchase Bids Lag-24h (MWh)",
    "mcp_rolling_min_24": "24h Rolling Min Price",
    "mcp_rolling_mean_168": "7-Day Rolling Mean Price",
    "mcp_rolling_max_24": "24h Rolling Max Price",
    "sell_bid_lag_24": "Sell Bids Lag-24h (MWh)",
    "demand_mw": "Gross System Demand (MW)",
    "solar_generation_mw": "Solar Generation (MW)",
    "wind_generation_mw": "Wind Generation (MW)",
    "re_penetration_pct": "Renewable Penetration (%)",
    "temperature_mean_c": "National Mean Temp (°C)",
    "cdd_24": "Cooling Degree Days (CDD > 24°C)",
    "is_peak_hour": "Evening Peak Window (18:00-22:00)",
    "is_solar_hour": "Solar Window (09:00-16:00)",
}


class EnergyCastEngine:
    """In-memory quantitative forecasting, simulation, and TreeSHAP explainability engine."""

    def __init__(self) -> None:
        t0 = time.perf_counter()
        print("[EnergyCastEngine] Loading trained model artifacts & datasets...")

        # Load models
        self.lgb_model = joblib.load(MODELS_DIR / "lightgbm_model.joblib")
        self.lgb_booster = self.lgb_model.booster_
        self.xgb_model = joblib.load(MODELS_DIR / "xgboost_model.joblib")
        self.ridge_model = joblib.load(MODELS_DIR / "ridge_regression.joblib")
        self.ols_model = joblib.load(MODELS_DIR / "linear_regression.joblib")
        self.scaler = joblib.load(MODELS_DIR / "feature_scaler.joblib")

        # Load test dataset (2025: 4,200 hours)
        self.test_df = pd.read_csv(SPLITS_DIR / "test.csv")
        self.test_df["timestamp_dt"] = pd.to_datetime(self.test_df["timestamp"])
        self.test_df["date_str"] = self.test_df["timestamp_dt"].dt.strftime("%Y-%m-%d")
        self.test_df["hour"] = self.test_df["timestamp_dt"].dt.hour

        self.feature_cols = [
            c for c in self.test_df.columns
            if c not in ("timestamp", "mcp_rs_per_mwh", "timestamp_dt", "date_str", "hour")
        ]

        # Precompute aligned predictions on test_df for ultra-fast serving
        X_test_raw = self.test_df[self.feature_cols].values
        X_test_scaled = self.scaler.transform(X_test_raw)

        self.test_df["pred_lightgbm"] = np.clip(self.lgb_booster.predict(X_test_raw), 0.0, 10000.0)
        self.test_df["pred_xgboost"] = np.clip(self.xgb_model.predict(self.test_df[self.feature_cols]), 0.0, 10000.0)
        self.test_df["pred_ridge"] = np.clip(self.ridge_model.predict(X_test_scaled), 0.0, 10000.0)
        self.test_df["pred_ols"] = np.clip(self.ols_model.predict(X_test_scaled), 0.0, 10000.0)
        self.test_df["pred_snaive_24h"] = self.test_df["mcp_lag_24"]
        self.test_df["pred_persistence_1h"] = self.test_df["mcp_lag_1"]
        self.test_df["pred_snaive_168h"] = self.test_df["mcp_lag_168"]

        # Precompute TreeSHAP matrix on test_df (4200 x 54)
        self.shap_contribs = self.lgb_booster.predict(X_test_raw, pred_contrib=True)
        self.shap_values = self.shap_contribs[:, :-1]
        self.base_value = float(self.shap_contribs[0, -1])

        # Load pre-computed tables from Steps 7-13
        self.leaderboard_df = pd.read_csv(TABLES_DIR / "master_model_leaderboard.csv")
        self.dm_df = pd.read_csv(TABLES_DIR / "diebold_mariano_pairwise_tests.csv")
        self.residuals_df = pd.read_csv(TABLES_DIR / "residual_error_diagnostics.csv")
        self.shap_global_df = pd.read_csv(TABLES_DIR / "shap_global_feature_importance.csv")
        self.shap_cat_df = pd.read_csv(TABLES_DIR / "shap_category_attribution_summary.csv")
        self.shap_cases_df = pd.read_csv(TABLES_DIR / "shap_local_case_studies.csv")
        self.feature_dict_df = pd.read_csv(TABLES_DIR / "energycast_feature_dictionary.csv")

        # Build list of available dates and curated regime presets
        self.available_dates = sorted(self.test_df["date_str"].unique().tolist())

        # Precompute merit-order curve sample (500 points + smoothed curve) for frontend visualization
        self._build_merit_order_reference()
        self._build_hourly_error_profiles()

        elapsed = (time.perf_counter() - t0) * 1000.0
        print(f"[EnergyCastEngine] Ready in {elapsed:.1f} ms | Test hours: {len(self.test_df):,} | Features: {len(self.feature_cols)}")

    def _build_merit_order_reference(self) -> None:
        """Builds empirical merit-order curve data (Net Demand GW vs SHAP impact & MCP)."""
        nd_idx = self.feature_cols.index("net_demand_mw")
        nd_gw = self.test_df["net_demand_mw"].values / 1000.0
        nd_shap = self.shap_values[:, nd_idx]
        mcp = self.test_df["mcp_rs_per_mwh"].values
        is_peak = self.test_df["is_peak_hour"].values

        # Stratified sample of 450 points across the net demand range
        rng = np.random.default_rng(42)
        sample_indices = rng.choice(len(nd_gw), size=min(450, len(nd_gw)), replace=False)

        self.merit_scatter = [
            {
                "net_demand_gw": round(float(nd_gw[i]), 2),
                "shap_rs": round(float(nd_shap[i]), 2),
                "mcp_rs": round(float(mcp[i]), 2),
                "is_peak": int(is_peak[i]),
                "timestamp": str(self.test_df.loc[i, "timestamp"]),
            }
            for i in sample_indices
        ]

        # Binned curve across Net Demand deciles/bins
        bins = np.linspace(np.percentile(nd_gw, 1), np.percentile(nd_gw, 99.5), 28)
        curve = []
        for b_idx in range(len(bins) - 1):
            mask = (nd_gw >= bins[b_idx]) & (nd_gw < bins[b_idx + 1])
            if np.sum(mask) >= 5:
                curve.append({
                    "net_demand_gw": round(float(np.mean(nd_gw[mask])), 2),
                    "mean_shap_rs": round(float(np.mean(nd_shap[mask])), 2),
                    "mean_mcp_rs": round(float(np.mean(mcp[mask])), 2),
                    "count": int(np.sum(mask)),
                })
        self.merit_curve = curve

    def _build_hourly_error_profiles(self) -> None:
        """Computes 24-hour diurnal MAE profile for all models on the test set."""
        models_map = {
            "LightGBM (Champion)": "pred_lightgbm",
            "XGBoost": "pred_xgboost",
            "Ridge (α=50)": "pred_ridge",
            "OLS Linear": "pred_ols",
            "Daily S-Naive (24h)": "pred_snaive_24h",
            "Persistence (1h)": "pred_persistence_1h",
            "Weekly S-Naive (168h)": "pred_snaive_168h",
        }
        hourly_profiles = []
        for h in range(24):
            sub = self.test_df[self.test_df["hour"] == h]
            actual = sub["mcp_rs_per_mwh"].values
            row_data: dict[str, Any] = {
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "mean_actual_mcp": round(float(np.mean(actual)), 2),
                "mean_net_demand_gw": round(float(np.mean(sub["net_demand_mw"].values / 1000.0)), 2),
                "mean_solar_gw": round(float(np.mean(sub["solar_generation_mw"].values / 1000.0)), 2),
            }
            for label, col in models_map.items():
                mae = float(np.mean(np.abs(actual - sub[col].values)))
                row_data[label] = round(mae, 2)
            hourly_profiles.append(row_data)
        self.hourly_error_profiles = hourly_profiles

    def get_overview_payload(self) -> dict[str, Any]:
        """Returns system metadata, available dates, preset scenarios, and summary KPIs."""
        presets = [
            {
                "id": "scarcity_cap",
                "label": "Jan 01, 2025 // Winter Solar Trough + Evening ₹10k Cap",
                "date": "2025-01-01",
                "focus_hour": 18,
                "tag": "SCARCITY CAP",
                "description": "Classic Duck Curve day: midday solar depresses MCP to ₹2,607/MWh at 13:00, followed by a +13.5 GW net demand ramp hitting ₹9,754/MWh at 18:00.",
            },
            {
                "id": "evening_ramp_spike",
                "label": "Jan 06, 2025 // Steep Evening Industrial Peak",
                "date": "2025-01-06",
                "focus_hour": 19,
                "tag": "PEAK RAMP",
                "description": "High industrial demand (197.5 GW gross, 188.4 GW net) triggers consecutive ₹10,000/MWh price cap blocks during evening ramp.",
            },
            {
                "id": "spring_solar_glut",
                "label": "Mar 16, 2025 // Spring High-Solar Midday Collapse",
                "date": "2025-03-16",
                "focus_hour": 12,
                "tag": "SOLAR GLUT",
                "description": "Strong solar injection floods the midday grid, pushing Renewable Penetration above 26% and creating deep buyer procurement savings.",
            },
            {
                "id": "summer_heatwave",
                "label": "May 18, 2025 // Peak Summer Cooling Stress",
                "date": "2025-05-18",
                "focus_hour": 21,
                "tag": "HEATWAVE",
                "description": "High Cooling Degree Days (CDD) keep night-time AC load elevated well past sunset, sustaining elevated clearing prices across evening blocks.",
            },
            {
                "id": "monsoon_wind_surge",
                "label": "Jun 15, 2025 // Early Monsoon Wind + Thermal Relief",
                "date": "2025-06-15",
                "focus_hour": 15,
                "tag": "WIND SURGE",
                "description": "Elevated wind generation moderates net demand across both afternoon and late-night blocks.",
            },
        ]

        return {
            "project": "EnergyCast V1",
            "market": "Indian Energy Exchange (IEX) — Day-Ahead Market (DAM)",
            "unit": "₹/MWh",
            "cerc_bounds": [0, 10000],
            "total_dataset_hours": 28176,
            "train_hours": 15192,
            "val_hours": 8784,
            "test_hours": len(self.test_df),
            "feature_count": len(self.feature_cols),
            "base_expected_mcp": round(self.base_value, 2),
            "available_dates": self.available_dates,
            "presets": presets,
            "champion_metrics": {
                "model": "LightGBM Regressor (282 Trees)",
                "test_mae": 433.33,
                "test_rmse": 703.43,
                "test_smape": 11.88,
                "test_r2": 0.9317,
                "vs_snaive_pct": 34.19,
                "vs_ridge_pct": 20.43,
                "peak_mae": 617.63,
                "spike_mae": 609.94,
                "dm_vs_snaive_stat": -7.780,
                "dm_vs_snaive_pval": "9.10e-15",
                "dm_vs_ridge_stat": -10.449,
                "dm_vs_ridge_pval": "< 1e-20",
            },
        }

    def get_day_forecast(self, date_str: str) -> dict[str, Any]:
        """Returns 24-hour multi-model predictions, physical grid telemetry, and bidding strategy for a given date."""
        if date_str not in self.available_dates:
            date_str = self.available_dates[0]

        sub = self.test_df[self.test_df["date_str"] == date_str].sort_values("hour")
        hours_list = []

        for idx, row in sub.iterrows():
            h = int(row["hour"])
            actual = float(row["mcp_rs_per_mwh"])
            lgb_p = float(row["pred_lightgbm"])
            xgb_p = float(row["pred_xgboost"])
            ridge_p = float(row["pred_ridge"])
            ols_p = float(row["pred_ols"])
            snaive_p = float(row["pred_snaive_24h"])

            hours_list.append({
                "row_index": int(idx),
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "timestamp": str(row["timestamp"]),
                "actual_mcp": round(actual, 2),
                "pred_lightgbm": round(lgb_p, 2),
                "pred_xgboost": round(xgb_p, 2),
                "pred_ridge": round(ridge_p, 2),
                "pred_ols": round(ols_p, 2),
                "pred_snaive_24h": round(snaive_p, 2),
                "error_lightgbm": round(lgb_p - actual, 2),
                "abs_error_lightgbm": round(abs(lgb_p - actual), 2),
                "abs_error_ridge": round(abs(ridge_p - actual), 2),
                "abs_error_snaive": round(abs(snaive_p - actual), 2),
                "demand_mw": round(float(row["demand_mw"]), 1),
                "net_demand_mw": round(float(row["net_demand_mw"]), 1),
                "solar_generation_mw": round(float(row["solar_generation_mw"]), 1),
                "wind_generation_mw": round(float(row["wind_generation_mw"]), 1),
                "re_penetration_pct": round(float(row["re_penetration_pct"]), 2),
                "net_demand_ramp_1": round(float(row["net_demand_ramp_1"]), 1),
                "temperature_mean_c": round(float(row["temperature_mean_c"]), 2),
                "market_tightness_lag_24": round(float(row["market_tightness_lag_24"]), 3),
                "is_peak_hour": int(row["is_peak_hour"]),
                "is_solar_hour": int(row["is_solar_hour"]),
            })

        # Compute daily summary metrics for this specific 24h slice
        actuals = np.array([x["actual_mcp"] for x in hours_list])
        lgb_preds = np.array([x["pred_lightgbm"] for x in hours_list])
        xgb_preds = np.array([x["pred_xgboost"] for x in hours_list])
        ridge_preds = np.array([x["pred_ridge"] for x in hours_list])
        snaive_preds = np.array([x["pred_snaive_24h"] for x in hours_list])

        def _slice_mae(p: np.ndarray) -> float:
            return round(float(np.mean(np.abs(actuals - p))), 2)

        def _slice_rmse(p: np.ndarray) -> float:
            return round(float(np.sqrt(np.mean((actuals - p) ** 2))), 2)

        # Automated Bidding Strategy Recommendations (based on LightGBM forecast)
        sorted_by_lgb = sorted(hours_list, key=lambda x: x["pred_lightgbm"])
        cheapest_4 = sorted(sorted_by_lgb[:4], key=lambda x: x["hour"])
        expensive_4 = sorted(sorted_by_lgb[-4:], key=lambda x: x["hour"])
        mean_lgb = float(np.mean(lgb_preds))
        mean_cheapest_4 = float(np.mean([x["pred_lightgbm"] for x in cheapest_4]))
        mean_expensive_4 = float(np.mean([x["pred_lightgbm"] for x in expensive_4]))

        return {
            "date": date_str,
            "hours_count": len(hours_list),
            "daily_kpis": {
                "mean_actual_mcp": round(float(np.mean(actuals)), 2),
                "max_actual_mcp": round(float(np.max(actuals)), 2),
                "min_actual_mcp": round(float(np.min(actuals)), 2),
                "mean_pred_lightgbm": round(mean_lgb, 2),
                "mae_lightgbm": _slice_mae(lgb_preds),
                "rmse_lightgbm": _slice_rmse(lgb_preds),
                "mae_xgboost": _slice_mae(xgb_preds),
                "mae_ridge": _slice_mae(ridge_preds),
                "mae_snaive": _slice_mae(snaive_preds),
                "max_solar_mw": round(float(max(x["solar_generation_mw"] for x in hours_list)), 1),
                "max_net_demand_mw": round(float(max(x["net_demand_mw"] for x in hours_list)), 1),
            },
            "bidding_strategy": {
                "discom_buy_windows": [
                    {"hour_label": x["hour_label"], "pred_mcp": x["pred_lightgbm"], "actual_mcp": x["actual_mcp"], "solar_mw": x["solar_generation_mw"]}
                    for x in cheapest_4
                ],
                "generator_dispatch_windows": [
                    {"hour_label": x["hour_label"], "pred_mcp": x["pred_lightgbm"], "actual_mcp": x["actual_mcp"], "net_demand_mw": x["net_demand_mw"]}
                    for x in expensive_4
                ],
                "expected_procurement_savings_rs_per_mwh": round(mean_lgb - mean_cheapest_4, 2),
                "expected_procurement_savings_pct": round(100.0 * (mean_lgb - mean_cheapest_4) / max(mean_lgb, 1.0), 1),
                "peak_spread_rs_per_mwh": round(mean_expensive_4 - mean_cheapest_4, 2),
            },
            "hourly": hours_list,
        }

    def get_hour_explanation(self, date_str: str, hour: int) -> dict[str, Any]:
        """Returns exact TreeSHAP feature breakdown and full feature vector for a specific date & hour."""
        sub = self.test_df[(self.test_df["date_str"] == date_str) & (self.test_df["hour"] == hour)]
        if sub.empty:
            sub = self.test_df.iloc[[0]]

        row_idx = int(sub.index[0])
        row = self.test_df.loc[row_idx]
        shap_row = self.shap_values[row_idx, :]

        # Build sorted feature attributions
        attributions = []
        for f_idx, col in enumerate(self.feature_cols):
            val = float(row[col])
            s_val = float(shap_row[f_idx])
            attributions.append({
                "feature": col,
                "label": FEATURE_LABELS.get(col, col),
                "category": CATEGORY_MAPPING.get(col, "Other"),
                "value": round(val, 4),
                "shap_rs": round(s_val, 2),
                "abs_shap_rs": round(abs(s_val), 2),
            })

        attributions_sorted = sorted(attributions, key=lambda x: x["abs_shap_rs"], reverse=True)
        top_12 = attributions_sorted[:12]
        other_sum = sum(x["shap_rs"] for x in attributions_sorted[12:])

        # Category sum for this specific hour
        cat_totals: dict[str, float] = {}
        for item in attributions:
            c = item["category"]
            cat_totals[c] = cat_totals.get(c, 0.0) + item["shap_rs"]

        raw_unclipped_pred = self.base_value + float(np.sum(shap_row))

        return {
            "row_index": row_idx,
            "timestamp": str(row["timestamp"]),
            "date": str(row["date_str"]),
            "hour": int(row["hour"]),
            "hour_label": f"{int(row['hour']):02d}:00",
            "actual_mcp": round(float(row["mcp_rs_per_mwh"]), 2),
            "pred_lightgbm": round(float(row["pred_lightgbm"]), 2),
            "raw_shap_sum_pred": round(raw_unclipped_pred, 2),
            "pred_xgboost": round(float(row["pred_xgboost"]), 2),
            "pred_ridge": round(float(row["pred_ridge"]), 2),
            "pred_snaive_24h": round(float(row["pred_snaive_24h"]), 2),
            "base_value": round(self.base_value, 2),
            "top_attributions": top_12,
            "other_features_shap_rs": round(float(other_sum), 2),
            "category_net_shap": {k: round(v, 2) for k, v in cat_totals.items()},
            "physical_state": {
                "demand_mw": round(float(row["demand_mw"]), 1),
                "solar_generation_mw": round(float(row["solar_generation_mw"]), 1),
                "wind_generation_mw": round(float(row["wind_generation_mw"]), 1),
                "net_demand_mw": round(float(row["net_demand_mw"]), 1),
                "net_demand_ramp_1": round(float(row["net_demand_ramp_1"]), 1),
                "re_penetration_pct": round(float(row["re_penetration_pct"]), 2),
                "temperature_mean_c": round(float(row["temperature_mean_c"]), 2),
                "cdd_24": round(float(row["cdd_24"]), 2),
                "market_tightness_lag_24": round(float(row["market_tightness_lag_24"]), 3),
                "mcp_lag_1": round(float(row["mcp_lag_1"]), 2),
                "mcp_lag_24": round(float(row["mcp_lag_24"]), 2),
            },
        }

    def run_counterfactual_simulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Executes live multi-model counterfactual simulation and real-time TreeSHAP attribution
        when physical grid or market parameters are perturbed.
        """
        t0 = time.perf_counter()
        date_str = str(payload.get("date", "2025-01-01"))
        hour = int(payload.get("hour", 18))

        sub = self.test_df[(self.test_df["date_str"] == date_str) & (self.test_df["hour"] == hour)]
        if sub.empty:
            sub = self.test_df.iloc[[18]]

        row_idx = int(sub.index[0])
        base_row = self.test_df.loc[row_idx, self.feature_cols].copy()
        actual_mcp = float(self.test_df.loc[row_idx, "mcp_rs_per_mwh"])

        # Baseline predictions & SHAP
        base_lgb = float(self.test_df.loc[row_idx, "pred_lightgbm"])
        base_xgb = float(self.test_df.loc[row_idx, "pred_xgboost"])
        base_ridge = float(self.test_df.loc[row_idx, "pred_ridge"])
        base_shap = self.shap_values[row_idx, :]

        # Perturbation parameters from user sliders
        delta_demand_mw = float(payload.get("delta_demand_mw", 0.0))
        delta_solar_mw = float(payload.get("delta_solar_mw", 0.0))
        delta_wind_mw = float(payload.get("delta_wind_mw", 0.0))
        delta_ramp_mw = float(payload.get("delta_ramp_mw", 0.0))
        delta_temp_c = float(payload.get("delta_temp_c", 0.0))
        tightness_override = payload.get("market_tightness_override", None)
        mcp_lag1_override = payload.get("mcp_lag_1_override", None)
        mcp_lag24_override = payload.get("mcp_lag_24_override", None)

        sim_row = base_row.copy()

        # 1. Update Physical Demand & Renewables
        new_demand = max(50000.0, float(base_row["demand_mw"]) + delta_demand_mw)
        new_solar = max(0.0, float(base_row["solar_generation_mw"]) + delta_solar_mw)
        new_wind = max(0.0, float(base_row["wind_generation_mw"]) + delta_wind_mw)
        new_total_re = new_solar + new_wind
        new_net_demand = new_demand - new_total_re
        new_re_pct = (new_total_re / max(new_demand, 1.0)) * 100.0

        sim_row["demand_mw"] = new_demand
        sim_row["solar_generation_mw"] = new_solar
        sim_row["wind_generation_mw"] = new_wind
        sim_row["net_demand_mw"] = new_net_demand
        sim_row["re_penetration_pct"] = new_re_pct

        # 2. Update Net Demand Ramp
        # Net demand change automatically affects ramp_1 plus any explicit ramp shock
        induced_nd_change = new_net_demand - float(base_row["net_demand_mw"])
        sim_row["net_demand_ramp_1"] = float(base_row["net_demand_ramp_1"]) + induced_nd_change + delta_ramp_mw

        # 3. Update Weather & Cooling Stress
        new_temp = float(base_row["temperature_mean_c"]) + delta_temp_c
        sim_row["temperature_mean_c"] = new_temp
        sim_row["temperature_max_c"] = float(base_row["temperature_max_c"]) + delta_temp_c
        sim_row["temperature_min_c"] = float(base_row["temperature_min_c"]) + delta_temp_c
        sim_row["apparent_temperature_mean_c"] = float(base_row["apparent_temperature_mean_c"]) + delta_temp_c
        sim_row["cdd_24"] = max(0.0, new_temp - 24.0)
        sim_row["temperature_sq"] = new_temp ** 2

        # 4. Update Cross-Feature Physical Interactions
        sim_row["net_demand_x_peak"] = new_net_demand * float(base_row["is_peak_hour"])
        sim_row["net_demand_x_cdd"] = new_net_demand * float(sim_row["cdd_24"])

        # 5. Update Market Tightness if overridden
        if tightness_override is not None:
            new_tightness = max(0.05, float(tightness_override))
            sim_row["market_tightness_lag_24"] = new_tightness
            sim_row["purchase_bid_lag_24"] = new_tightness * float(base_row["sell_bid_lag_24"])

        # 6. Update Autoregressive Price Anchors if overridden
        if mcp_lag1_override is not None:
            new_lag1 = np.clip(float(mcp_lag1_override), 0.0, 10000.0)
            old_lag1 = float(base_row["mcp_lag_1"])
            lag25_est = old_lag1 - float(base_row["mcp_diff_24_25"])
            sim_row["mcp_lag_1"] = new_lag1
            sim_row["mcp_diff_1_2"] = new_lag1 - float(base_row["mcp_lag_2"])
            sim_row["mcp_diff_24_25"] = new_lag1 - lag25_est
            sim_row["mcp_zscore_24"] = (new_lag1 - float(base_row["mcp_rolling_mean_24"])) / (float(base_row["mcp_rolling_std_24"]) + 1e-4)

        if mcp_lag24_override is not None:
            new_lag24 = np.clip(float(mcp_lag24_override), 0.0, 10000.0)
            sim_row["mcp_lag_24"] = new_lag24

        sim_row["mcp_ratio_1_24"] = float(sim_row["mcp_lag_1"]) / (float(sim_row["mcp_lag_24"]) + 1e-4)

        # Convert to 2D array & DataFrame for model scoring
        X_sim_df = pd.DataFrame([sim_row.values], columns=self.feature_cols)
        X_sim_raw = X_sim_df.values
        X_sim_scaled = self.scaler.transform(X_sim_raw)

        sim_lgb = float(np.clip(self.lgb_booster.predict(X_sim_raw)[0], 0.0, 10000.0))
        sim_xgb = float(np.clip(self.xgb_model.predict(X_sim_df)[0], 0.0, 10000.0))
        sim_ridge = float(np.clip(self.ridge_model.predict(X_sim_scaled)[0], 0.0, 10000.0))

        # Exact TreeSHAP for simulated state
        sim_contrib = self.lgb_booster.predict(X_sim_raw, pred_contrib=True)[0]
        sim_shap = sim_contrib[:-1]

        # Rank features by largest SHAP shift or largest absolute simulated SHAP
        shap_comparison = []
        for i, col in enumerate(self.feature_cols):
            b_s = float(base_shap[i])
            s_s = float(sim_shap[i])
            shap_comparison.append({
                "feature": col,
                "label": FEATURE_LABELS.get(col, col),
                "category": CATEGORY_MAPPING.get(col, "Other"),
                "base_val": round(float(base_row[col]), 2),
                "sim_val": round(float(sim_row[col]), 2),
                "base_shap_rs": round(b_s, 2),
                "sim_shap_rs": round(s_s, 2),
                "delta_shap_rs": round(s_s - b_s, 2),
                "abs_sim_shap_rs": round(abs(s_s), 2),
            })

        top_sim_shap = sorted(shap_comparison, key=lambda x: x["abs_sim_shap_rs"], reverse=True)[:12]
        top_shifted_shap = sorted(shap_comparison, key=lambda x: abs(x["delta_shap_rs"]), reverse=True)[:8]

        latency_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "latency_ms": round(latency_ms, 2),
            "timestamp": str(self.test_df.loc[row_idx, "timestamp"]),
            "date": date_str,
            "hour": hour,
            "hour_label": f"{hour:02d}:00",
            "actual_mcp": round(actual_mcp, 2),
            "base_value": round(self.base_value, 2),
            "predictions": {
                "lightgbm": {
                    "baseline": round(base_lgb, 2),
                    "simulated": round(sim_lgb, 2),
                    "delta_rs": round(sim_lgb - base_lgb, 2),
                    "delta_pct": round(100.0 * (sim_lgb - base_lgb) / max(base_lgb, 1.0), 2),
                },
                "xgboost": {
                    "baseline": round(base_xgb, 2),
                    "simulated": round(sim_xgb, 2),
                    "delta_rs": round(sim_xgb - base_xgb, 2),
                },
                "ridge": {
                    "baseline": round(base_ridge, 2),
                    "simulated": round(sim_ridge, 2),
                    "delta_rs": round(sim_ridge - base_ridge, 2),
                },
            },
            "grid_telemetry": {
                "baseline": {
                    "demand_mw": round(float(base_row["demand_mw"]), 1),
                    "solar_mw": round(float(base_row["solar_generation_mw"]), 1),
                    "wind_mw": round(float(base_row["wind_generation_mw"]), 1),
                    "net_demand_mw": round(float(base_row["net_demand_mw"]), 1),
                    "net_demand_gw": round(float(base_row["net_demand_mw"]) / 1000.0, 2),
                    "re_penetration_pct": round(float(base_row["re_penetration_pct"]), 2),
                    "net_demand_ramp_1": round(float(base_row["net_demand_ramp_1"]), 1),
                    "temperature_c": round(float(base_row["temperature_mean_c"]), 2),
                    "market_tightness": round(float(base_row["market_tightness_lag_24"]), 3),
                },
                "simulated": {
                    "demand_mw": round(new_demand, 1),
                    "solar_mw": round(new_solar, 1),
                    "wind_mw": round(new_wind, 1),
                    "net_demand_mw": round(new_net_demand, 1),
                    "net_demand_gw": round(new_net_demand / 1000.0, 2),
                    "re_penetration_pct": round(new_re_pct, 2),
                    "net_demand_ramp_1": round(float(sim_row["net_demand_ramp_1"]), 1),
                    "temperature_c": round(new_temp, 2),
                    "market_tightness": round(float(sim_row["market_tightness_lag_24"]), 3),
                },
            },
            "top_sim_shap": top_sim_shap,
            "top_shifted_shap": top_shifted_shap,
        }

    def get_shap_lab_payload(self) -> dict[str, Any]:
        """Returns global TreeSHAP rankings, category breakdown, merit-order curve, and canonical case studies."""
        global_features = []
        for idx, row in self.shap_global_df.iterrows():
            feat = str(row["Feature"])
            global_features.append({
                "rank": int(idx) + 1,
                "feature": feat,
                "label": FEATURE_LABELS.get(feat, feat),
                "category": str(row["Category"]),
                "mean_abs_shap_rs": round(float(row["Mean_Abs_SHAP_Rs_per_MWh"]), 2),
                "mean_shap_rs": round(float(row["Mean_SHAP_Rs_per_MWh"]), 2),
                "std_shap_rs": round(float(row["Std_SHAP_Rs_per_MWh"]), 2),
                "correlation": round(float(row["Feature_SHAP_Correlation"]), 3),
                "direction": str(row["Impact_Direction"]),
            })

        categories = []
        for _, row in self.shap_cat_df.iterrows():
            categories.append({
                "category": str(row["Category"]),
                "total_abs_shap_rs": round(float(row["Total_Abs_SHAP_Rs"]), 2),
                "avg_abs_shap_rs": round(float(row["Avg_Abs_SHAP_Rs"]), 2),
                "feature_count": int(row["Feature_Count"]),
                "share_pct": round(float(row["Attribution_Share_%"]), 2),
            })

        # Group local case studies
        cases_grouped = []
        for case_name, grp in self.shap_cases_df.groupby("Case", sort=False):
            first = grp.iloc[0]
            drivers = []
            for _, r in grp.iterrows():
                f_name = str(r["Feature"])
                drivers.append({
                    "feature": f_name,
                    "label": FEATURE_LABELS.get(f_name, f_name),
                    "value": round(float(r["Feature_Value"]), 2),
                    "shap_rs": round(float(r["SHAP_Contribution_Rs"]), 2),
                })
            cases_grouped.append({
                "case_title": str(case_name),
                "timestamp": str(first["Timestamp"]),
                "actual_mcp": round(float(first["Actual_MCP"]), 2),
                "predicted_mcp": round(float(first["Predicted_MCP"]), 2),
                "base_value": round(self.base_value, 2),
                "drivers": drivers,
            })

        return {
            "base_value": round(self.base_value, 2),
            "global_features": global_features,
            "categories": categories,
            "merit_order_scatter": self.merit_scatter,
            "merit_order_curve": self.merit_curve,
            "case_studies": cases_grouped,
        }

    def get_benchmarks_payload(self) -> dict[str, Any]:
        """Returns master model leaderboard, Diebold-Mariano matrix, hourly error profiles, and residual diagnostics."""
        leaderboard = []
        for _, row in self.leaderboard_df.iterrows():
            leaderboard.append({
                "tier": str(row["Tier"]),
                "model": str(row["Model"]),
                "val_mae": round(float(row["Val_MAE"]), 2),
                "val_rmse": round(float(row["Val_RMSE"]), 2),
                "val_smape": round(float(row["Val_sMAPE"]), 2),
                "val_r2": round(float(row["Val_R2"]), 4),
                "test_mae": round(float(row["Test_MAE"]), 2),
                "test_rmse": round(float(row["Test_RMSE"]), 2),
                "test_smape": round(float(row["Test_sMAPE"]), 2),
                "test_r2": round(float(row["Test_R2"]), 4),
                "test_peak_mae": round(float(row["Test_Peak_MAE"]), 2),
                "test_offpeak_mae": round(float(row["Test_OffPeak_MAE"]), 2),
                "test_spike_mae": round(float(row["Test_Spike_MAE"]), 2),
                "vs_snaive_pct": round(float(row["MAE_Reduction_vs_SNaive_%"]), 2),
            })

        dm_tests = []
        for _, row in self.dm_df.iterrows():
            dm_tests.append({
                "model_1": str(row["Model_1"]),
                "model_2": str(row["Model_2"]),
                "dm_stat": round(float(row["DM_Statistic"]), 3),
                "p_value": float(row["p_value_two_sided"]),
                "significance": str(row["Significance_at_1%"]),
                "superior_model": str(row["Superior_Model"]),
            })

        residuals = []
        for _, row in self.residuals_df.iterrows():
            residuals.append({
                "model": str(row["Model"]),
                "mean_bias": round(float(row["Mean_Error (Bias)"]), 2),
                "std_error": round(float(row["Std_Error"]), 2),
                "skewness": round(float(row["Skewness"]), 3),
                "kurtosis": round(float(row["Kurtosis"]), 3),
                "jb_stat": round(float(row["Jarque_Bera_Stat"]), 1),
                "p10": round(float(row["Error_P10"]), 2),
                "median": round(float(row["Error_P50 (Median)"]), 2),
                "p90": round(float(row["Error_P90"]), 2),
            })

        return {
            "leaderboard": leaderboard,
            "dm_tests": dm_tests,
            "residuals": residuals,
            "hourly_error_profiles": self.hourly_error_profiles,
        }


# Global singleton engine initialized when server starts
ENGINE: EnergyCastEngine | None = None


class EnergyCastRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving both JSON API endpoints and static frontend assets."""

    def log_message(self, format: str, *args: Any) -> None:
        # Quiet, clean single-line logging
        pass

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File Not Found")
            return
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        global ENGINE
        assert ENGINE is not None

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/api/overview":
                self._send_json(ENGINE.get_overview_payload())
                return

            if path == "/api/day_forecast":
                date_str = query.get("date", ["2025-01-01"])[0]
                self._send_json(ENGINE.get_day_forecast(date_str))
                return

            if path == "/api/hour_explain":
                date_str = query.get("date", ["2025-01-01"])[0]
                hour = int(query.get("hour", ["18"])[0])
                self._send_json(ENGINE.get_hour_explanation(date_str, hour))
                return

            if path == "/api/shap_lab":
                self._send_json(ENGINE.get_shap_lab_payload())
                return

            if path == "/api/benchmarks":
                self._send_json(ENGINE.get_benchmarks_payload())
                return

            # Serve static files
            if path in ("/", "/index.html"):
                self._serve_file(STATIC_DIR / "index.html")
                return

            if path.startswith("/static/"):
                rel = path[len("/static/"):]
                target = (STATIC_DIR / rel).resolve()
                if str(target).startswith(str(STATIC_DIR.resolve())):
                    self._serve_file(target)
                    return

            # Also allow serving generated project figures if requested
            if path.startswith("/figures/"):
                rel = path[len("/figures/"):]
                target = (FIG_DIR / rel).resolve()
                if str(target).startswith(str(FIG_DIR.resolve())):
                    self._serve_file(target)
                    return

            # Fallback to static directory root
            rel_clean = path.lstrip("/")
            candidate = (STATIC_DIR / rel_clean).resolve()
            if str(candidate).startswith(str(STATIC_DIR.resolve())) and candidate.is_file():
                self._serve_file(candidate)
                return

            self.send_error(404, f"Route not found: {path}")
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def do_POST(self) -> None:
        global ENGINE
        assert ENGINE is not None

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))

            if path == "/api/simulate":
                result = ENGINE.run_counterfactual_simulation(payload)
                self._send_json(result)
                return

            self.send_error(404, f"POST route not found: {path}")
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)


def run_server(host: str = "127.0.0.1", port: int = 8501, open_browser: bool = False) -> None:
    global ENGINE
    ENGINE = EnergyCastEngine()

    server = ThreadingHTTPServer((host, port), EnergyCastRequestHandler)
    url = f"http://{host}:{port}"
    print("=" * 78)
    print(f"  ENERGYCAST V1 // IEX-DAM QUANTITATIVE DISPATCH TERMINAL")
    print(f"  Live Web Application URL : {url}")
    print(f"  Models Active            : LightGBM (282T) | XGBoost (268T) | Ridge (a=50) | OLS")
    print("=" * 78)

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[EnergyCastEngine] Shutting down server...")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EnergyCast V1 Interactive Web Application Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8501, help="Bind port (default: 8501)")
    parser.add_argument("--open", action="store_true", help="Automatically open in browser")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, open_browser=args.open)

