"""
EnergyCast V2 (TPWRS Revision) — Step 1: Strict D-1 10:30 AM IST Operational
Causal Forecast Reconstruction & Leakage-Free Feature Pipeline.

Solves Reviewer Critical Weakness A (D-1 Information Leakage):
  1. Removes ALL inadmissible intraday price lags (mcp_lag_1, mcp_lag_2, rolling
     stats ending at t-1) because all 24 hours of Delivery Day D clear jointly
     after the 10:30 AM IST D-1 auction gate.
  2. Removes ALL contemporaneous realized Day-D demand, solar, wind, and weather
     observations AND all unrealized afternoon D-1 SCADA (> 10:00 AM IST on D-1).
  3. Builds a dedicated Stage-1 Causal Day-Ahead Exogenous Forecasting Suite
     (using strictly SCADA/weather observations <= D-1 10:00 AM IST, deterministic
     astronomical clear-sky solar elevation, and calendar/holiday indicators) to
     reconstruct genuine out-of-sample Day-Ahead Forecasts:
        - National Demand Forecast       (demand_fcst_mw)
        - National Solar Gen Forecast    (solar_fcst_mw)
        - National Wind Gen Forecast     (wind_fcst_mw)
        - 5-Zone Weather Forecasts       (temp, max_temp, apparent_temp, humidity,
                                          wind_speed, precipitation)
     Train (2022-2023) Stage-1 predictions are generated via 5-fold temporally
     blocked & purged Out-Of-Fold CV (48h purge gap) to prevent Stage-1 overfitting;
     Val (2024) is trained strictly on 2022-2023; Test (2025) is trained strictly
     on 2022-2024 (expanding window, zero 2025 leakage).
  4. Exports BOTH:
       (a) Strict Operational D-1 splits (zero future leakage, primary benchmark)
       (b) Ex-Post Perfect-Exogenous splits (strict D-1 prices + realized Day-D
           demand/RE/weather) to quantify the exact Value of Perfect Exogenous
           Forecasts.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = PROJECT_ROOT / "data" / "processed" / "master" / "energycast_master_hourly_2022_2025.csv"
CITIES_PATH = PROJECT_ROOT / "data" / "processed" / "weather" / "india_weather_cities_hourly_2022_2025.csv"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "causal_d1"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# Major Indian national & regional public holidays (2022-2025) affecting industrial load
INDIAN_HOLIDAYS = {
    # 2022
    "2022-04-14", "2022-04-15", "2022-05-03", "2022-08-15", "2022-08-31",
    "2022-10-02", "2022-10-05", "2022-10-24", "2022-10-25", "2022-11-08", "2022-12-25",
    # 2023
    "2023-01-26", "2023-03-08", "2023-03-30", "2023-04-07", "2023-04-22",
    "2023-08-15", "2023-09-19", "2023-10-02", "2023-10-24", "2023-11-12", "2023-11-13",
    "2023-11-27", "2023-12-25",
    # 2024
    "2024-01-26", "2024-03-25", "2024-03-29", "2024-04-11", "2024-04-17",
    "2024-08-15", "2024-09-07", "2024-10-02", "2024-10-12", "2024-10-31", "2024-11-01",
    "2024-11-15", "2024-12-25",
    # 2025
    "2025-01-26", "2025-02-26", "2025-03-14", "2025-03-31", "2025-04-14", "2025-04-18",
    "2025-05-01",
}


def compute_solar_elevation_deg(timestamps: pd.Series, lat_deg: float = 23.5, lon_deg: float = 78.9) -> np.ndarray:
    """
    Exact deterministic astronomical solar elevation angle (degrees) for Central India
    (IST = UTC+5.5). Uses only calendar date & hour — zero weather or future data.
    """
    doy = timestamps.dt.dayofyear.values.astype(np.float64)
    hour_ist = timestamps.dt.hour.values.astype(np.float64) + 0.5  # mid-hour average

    # Equation of time & solar declination (Spencer 1971 approximation)
    gamma = 2.0 * np.pi * (doy - 1.0) / 365.25
    decl = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma)
        + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma)
        + 0.001480 * np.sin(3 * gamma)
    )
    eq_time_min = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma)
        - 0.040849 * np.sin(2 * gamma)
    )
    # IST meridian is 82.5 deg E
    time_offset_min = eq_time_min + 4.0 * (lon_deg - 82.5)
    true_solar_time_h = hour_ist + time_offset_min / 60.0
    hour_angle_rad = np.deg2rad(15.0 * (true_solar_time_h - 12.0))
    lat_rad = np.deg2rad(lat_deg)

    sin_elev = np.sin(lat_rad) * np.sin(decl) + np.cos(lat_rad) * np.cos(decl) * np.cos(hour_angle_rad)
    elev_deg = np.rad2deg(np.arcsin(np.clip(sin_elev, -1.0, 1.0)))
    return np.maximum(0.0, elev_deg)


def build_daily_panel(df: pd.DataFrame, cols: list[str]) -> dict[str, pd.DataFrame]:
    """
    Pivots each hourly column into a (date x 24 hours) table so D-1, D-2, D-7,
    morning-only (h <= 10 on D-1) extractions are mathematically exact and auditable.
    """
    out = {}
    for c in cols:
        piv = df.pivot(index="date", columns="hour", values=c).sort_index()
        out[c] = piv
    return out


def build_stage1_exogenous_features(df: pd.DataFrame, panels: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Constructs STRICTLY CAUSAL features known at <= (D-1, 10:00 IST) for Stage-1
    Day-Ahead Forecasting of Demand, Solar, Wind, and 5-Zone Weather on Day (D, h).

    Causality proof:
      - Uses ONLY Day D-2, D-3, D-7, D-14 full-day SCADA/weather (all <= D-2 23:00 < D-1 10:00)
      - Uses ONLY Day D-1 morning hours h' in {0..10} (all <= D-1 10:00)
      - Uses ONLY Day D-1 IEX auction schedules (published ~13:00 IST on D-2)
      - Uses deterministic calendar, holiday, and astronomical solar elevation for (D, h).
    """
    dates = df["date"]
    hours = df["hour"].values

    def lookup_day_shift(col: str, day_shift: int, hour_override: int | None = None) -> np.ndarray:
        shifted = panels[col].shift(day_shift)
        if hour_override is not None:
            s = shifted[hour_override]
            return dates.map(s).values.astype(np.float64)
        # Map (date, hour) pair
        arr = shifted.loc[dates].values
        return arr[np.arange(len(df)), hours].astype(np.float64)

    def lookup_morning_stat(col: str, day_shift: int, h_start: int, h_end: int, stat: str = "mean") -> np.ndarray:
        sub = panels[col].shift(day_shift).loc[:, h_start:h_end]
        if stat == "mean":
            s = sub.mean(axis=1)
        elif stat == "max":
            s = sub.max(axis=1)
        elif stat == "min":
            s = sub.min(axis=1)
        elif stat == "std":
            s = sub.std(axis=1)
        else:
            raise ValueError(stat)
        return dates.map(s).values.astype(np.float64)

    def lookup_rolling_same_h(col: str, min_day_shift: int, window_days: int, stat: str = "mean") -> np.ndarray:
        piv = panels[col].shift(min_day_shift)
        if stat == "mean":
            rolled = piv.rolling(window=window_days, min_periods=max(1, window_days // 2)).mean()
        elif stat == "max":
            rolled = piv.rolling(window=window_days, min_periods=max(1, window_days // 2)).max()
        else:
            raise ValueError(stat)
        arr = rolled.loc[dates].values
        return arr[np.arange(len(df)), hours].astype(np.float64)

    s1 = pd.DataFrame(index=df.index)

    # Deterministic calendar & solar geometry for target (D, h)
    doy = df["timestamp"].dt.dayofyear.values
    dow = df["timestamp"].dt.dayofweek.values
    s1["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
    s1["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
    s1["dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
    s1["dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)
    s1["doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    s1["doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
    s1["is_weekend"] = (dow >= 5).astype(np.float64)
    s1["is_sunday"] = (dow == 6).astype(np.float64)
    s1["is_holiday"] = df["date_str"].isin(INDIAN_HOLIDAYS).astype(np.float64)
    s1["solar_elev_deg"] = compute_solar_elevation_deg(df["timestamp"])
    s1["sin_solar_elev"] = np.sin(np.deg2rad(s1["solar_elev_deg"]))
    s1["trend_days"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() / 86400.0

    # Strictly causal realized SCADA lags: D-2, D-3, D-7, D-14 + D-1 morning (<=10:00 IST)
    for col in ["demand_mw", "solar_generation_mw", "wind_generation_mw"]:
        s1[f"{col}_d2_h"] = lookup_day_shift(col, 2)
        s1[f"{col}_d3_h"] = lookup_day_shift(col, 3)
        s1[f"{col}_d7_h"] = lookup_day_shift(col, 7)
        s1[f"{col}_d14_h"] = lookup_day_shift(col, 14)
        s1[f"{col}_7d_h_mean"] = lookup_rolling_same_h(col, 2, 7, "mean")
        s1[f"{col}_14d_h_max"] = lookup_rolling_same_h(col, 2, 14, "max")
        # Strictly known morning telemetry on Day D-1 (hours 0..10)
        s1[f"{col}_d1_h10"] = lookup_day_shift(col, 1, hour_override=10)
        s1[f"{col}_d1_h09"] = lookup_day_shift(col, 1, hour_override=9)
        s1[f"{col}_d1_morn_mean"] = lookup_morning_stat(col, 1, 6, 10, "mean")
        s1[f"{col}_d2_morn_mean"] = lookup_morning_stat(col, 2, 6, 10, "mean")
        s1[f"{col}_morn_delta"] = s1[f"{col}_d1_morn_mean"] - s1[f"{col}_d2_morn_mean"]
        # For h <= 10, D-1 same hour IS already realized before 10:30 AM on D-1!
        # For h > 10, strictly mask with D-2 same hour + morning drift (zero leakage)
        d1_same_h = lookup_day_shift(col, 1)
        s1[f"{col}_latest_causal_h"] = np.where(hours <= 10, d1_same_h, s1[f"{col}_d2_h"])

    # Strictly causal weather telemetry <= (D-1, 10:00 IST)
    weather_cols = [
        "temperature_mean_c", "temperature_max_c", "temperature_min_c",
        "apparent_temperature_mean_c", "humidity_mean_pct",
        "weather_wind_speed_mean_ms", "precipitation_mean_mm",
    ]
    for col in weather_cols:
        s1[f"{col}_d2_h"] = lookup_day_shift(col, 2)
        s1[f"{col}_d7_h"] = lookup_day_shift(col, 7)
        s1[f"{col}_7d_h_mean"] = lookup_rolling_same_h(col, 2, 7, "mean")
        s1[f"{col}_d1_h10"] = lookup_day_shift(col, 1, hour_override=10)
        s1[f"{col}_d1_morn_mean"] = lookup_morning_stat(col, 1, 6, 10, "mean")
        s1[f"{col}_morn_delta"] = s1[f"{col}_d1_morn_mean"] - lookup_morning_stat(col, 2, 6, 10, "mean")
        d1_same_h = lookup_day_shift(col, 1)
        s1[f"{col}_latest_causal_h"] = np.where(hours <= 10, d1_same_h, s1[f"{col}_d2_h"])

    # Clear-sky solar capacity proxy = recent 14-day same-hour max solar * ratio of current elev
    s1["solar_clearsky_proxy"] = s1["solar_generation_mw_14d_h_max"] * (s1["sin_solar_elev"] > 0.01)
    # Morning cloudiness attenuation ratio on D-1 (at 09:00-10:00 IST vs 14-day max at 09:00-10:00)
    d1_sol_10 = lookup_day_shift("solar_generation_mw", 1, hour_override=10)
    max14_sol_10 = dates.map(
        panels["solar_generation_mw"][10].shift(2).rolling(14, min_periods=5).max()
    ).values.astype(np.float64)
    s1["d1_morn_solar_clearness"] = np.clip(d1_sol_10 / np.maximum(max14_sol_10, 500.0), 0.0, 1.3)

    # Published D-1 IEX clearing volumes/prices (published D-2 13:00 IST) as demand signal
    s1["mcv_d1_h"] = lookup_day_shift("mcv_mwh", 1)
    s1["mcp_d1_h"] = lookup_day_shift("mcp_rs_per_mwh", 1)

    return s1


def fit_and_predict_stage1_target(
    X_s1: pd.DataFrame,
    y_target: np.ndarray,
    timestamps: pd.Series,
    target_name: str,
    clip_low: float | None = None,
    clip_high: float | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Generates strictly leak-free out-of-sample Stage-1 Day-Ahead Forecasts across all splits:
      - Train (2022-2023): 5-fold temporally blocked Out-of-Fold CV with 48h purge buffer
      - Val   (2024):      Trained strictly on Train (2022-2023)
      - Test  (2025):      Trained strictly on Train + Val (2022-2024)
    """
    train_mask = (timestamps <= pd.Timestamp("2023-12-31 23:00:00")).values
    val_mask = ((timestamps >= pd.Timestamp("2024-01-01 00:00:00")) & (timestamps <= pd.Timestamp("2024-12-31 23:00:00"))).values
    test_mask = (timestamps >= pd.Timestamp("2025-01-01 00:00:00")).values

    preds = np.full(len(y_target), np.nan, dtype=np.float64)

    params = dict(
        objective="regression",
        n_estimators=450,
        learning_rate=0.04,
        num_leaves=47,
        min_child_samples=35,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=3.0,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )

    # 1. Temporally blocked 5-fold Purged OOF on Train (2022-2023)
    train_idx = np.where(train_mask)[0]
    n_folds = 5
    fold_bounds = np.linspace(0, len(train_idx), n_folds + 1, dtype=int)
    purge_h = 48
    for f in range(n_folds):
        va_start, va_end = fold_bounds[f], fold_bounds[f + 1]
        va_pos = train_idx[va_start:va_end]
        tr_keep = np.ones(len(train_idx), dtype=bool)
        tr_keep[max(0, va_start - purge_h) : min(len(train_idx), va_end + purge_h)] = False
        tr_pos = train_idx[tr_keep]
        model = lgb.LGBMRegressor(**params)
        model.fit(X_s1.iloc[tr_pos], y_target[tr_pos])
        preds[va_pos] = model.predict(X_s1.iloc[va_pos])

    # 2. Val (2024) trained strictly on Train (2022-2023)
    model_val = lgb.LGBMRegressor(**params)
    model_val.fit(X_s1.iloc[train_idx], y_target[train_idx])
    preds[val_mask] = model_val.predict(X_s1.iloc[val_mask])

    # 3. Test (2025) trained strictly on Train + Val (2022-2024)
    tr_val_idx = np.where(train_mask | val_mask)[0]
    model_test = lgb.LGBMRegressor(**params)
    model_test.fit(X_s1.iloc[tr_val_idx], y_target[tr_val_idx])
    preds[test_mask] = model_test.predict(X_s1.iloc[test_mask])

    if clip_low is not None:
        preds = np.maximum(clip_low, preds)
    if clip_high is not None:
        preds = np.minimum(clip_high, preds)

    # Enforce physical midnight zero for solar when elevation == 0
    if target_name == "solar_generation_mw":
        preds = np.where(X_s1["solar_elev_deg"].values <= 0.0, 0.0, preds)

    # Compute out-of-sample quality metrics on Val (2024) & Test (2025)
    def calc_stats(mask: np.ndarray) -> dict[str, float]:
        yt = y_target[mask]
        yp = preds[mask]
        mae = float(np.mean(np.abs(yt - yp)))
        rmse = float(np.sqrt(np.mean((yt - yp) ** 2)))
        denom = float(np.max(yt) - np.min(yt)) if np.max(yt) > np.min(yt) else 1.0
        nrmse = rmse / denom * 100.0
        r2 = float(1.0 - np.sum((yt - yp) ** 2) / np.sum((yt - np.mean(yt)) ** 2))
        mape = float(np.mean(np.abs(yt - yp) / np.maximum(np.abs(yt), 1.0)) * 100.0) if np.min(yt) > 100 else np.nan
        return {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "nRMSE_pct": round(nrmse, 2), "R2": round(r2, 4), "MAPE_pct": round(mape, 2) if not np.isnan(mape) else None}

    metrics = {
        "target": target_name,
        "val_2024": calc_stats(val_mask),
        "test_2025": calc_stats(test_mask),
    }
    return preds, metrics


def assemble_stage2_feature_matrix(
    df: pd.DataFrame,
    panels: dict[str, pd.DataFrame],
    fcst: dict[str, np.ndarray],
    use_oracle_exog: bool = False,
) -> pd.DataFrame:
    """
    Assembles the final 62-feature Stage-2 matrix under STRICT D-1 10:30 AM IST Causality.
    ZERO same-day prices (no mcp_lag_1 / mcp_lag_2).
    If use_oracle_exog=False (Operational D-1 Mode): uses ONLY Stage-1 reconstructed forecasts.
    If use_oracle_exog=True  (Ex-Post Perfect Exog Mode): substitutes realized Day-D physical/weather
    while STILL strictly keeping D-1 price/order-book features (to measure Value of Perfect Exog).
    """
    dates = df["date"]
    hours = df["hour"].values

    def lookup_day_shift(col: str, day_shift: int, hour_override: int | None = None) -> np.ndarray:
        shifted = panels[col].shift(day_shift)
        if hour_override is not None:
            return dates.map(shifted[hour_override]).values.astype(np.float64)
        arr = shifted.loc[dates].values
        return arr[np.arange(len(df)), hours].astype(np.float64)

    def lookup_day_agg(col: str, day_shift: int, agg: str) -> np.ndarray:
        shifted = panels[col].shift(day_shift)
        if agg == "mean":
            s = shifted.mean(axis=1)
        elif agg == "std":
            s = shifted.std(axis=1)
        elif agg == "min":
            s = shifted.min(axis=1)
        elif agg == "max":
            s = shifted.max(axis=1)
        elif agg == "cap_hits":
            s = (shifted >= 9990.0).sum(axis=1)
        else:
            raise ValueError(agg)
        return dates.map(s).values.astype(np.float64)

    def lookup_7d_same_h(col: str, stat: str = "mean") -> np.ndarray:
        piv = panels[col].shift(1)
        rolled = piv.rolling(7, min_periods=4).mean() if stat == "mean" else piv.rolling(7, min_periods=4).std()
        arr = rolled.loc[dates].values
        return arr[np.arange(len(df)), hours].astype(np.float64)

    def lookup_7d_all_h_mean(col: str) -> np.ndarray:
        daily_mean = panels[col].mean(axis=1).shift(1).rolling(7, min_periods=4).mean()
        return dates.map(daily_mean).values.astype(np.float64)

    def lookup_morning_mean(col: str, day_shift: int) -> np.ndarray:
        s = panels[col].shift(day_shift).loc[:, 6:10].mean(axis=1)
        return dates.map(s).values.astype(np.float64)

    out = pd.DataFrame(index=df.index)
    out["timestamp"] = df["timestamp"]
    out["mcp_rs_per_mwh"] = df["mcp_rs_per_mwh"].values

    # =========================================================================
    # FAMILY 1: STRICT D-1 PUBLISHED IEX PRICE MEMORY (18 FEATURES)
    # All 24h of Day D-1 cleared on Day D-2 (~13:00 IST) -> 100% known before D-1 10:30 AM!
    # =========================================================================
    out["mcp_d1_same_h"] = lookup_day_shift("mcp_rs_per_mwh", 1)
    out["mcp_d2_same_h"] = lookup_day_shift("mcp_rs_per_mwh", 2)
    out["mcp_d3_same_h"] = lookup_day_shift("mcp_rs_per_mwh", 3)
    out["mcp_d7_same_h"] = lookup_day_shift("mcp_rs_per_mwh", 7)
    out["mcp_d14_same_h"] = lookup_day_shift("mcp_rs_per_mwh", 14)

    # Adjacent hours from Day D-1's published curve (strictly known!)
    piv_d1 = panels["mcp_rs_per_mwh"].shift(1).loc[dates].values
    prev_h = (hours - 1) % 24
    next_h = (hours + 1) % 24
    out["mcp_d1_prev_h"] = piv_d1[np.arange(len(df)), prev_h]
    out["mcp_d1_next_h"] = piv_d1[np.arange(len(df)), next_h]
    out["mcp_d1_h23"] = lookup_day_shift("mcp_rs_per_mwh", 1, hour_override=23)

    out["mcp_d1_diff_d2"] = out["mcp_d1_same_h"] - out["mcp_d2_same_h"]
    out["mcp_d1_diff_d7"] = out["mcp_d1_same_h"] - out["mcp_d7_same_h"]
    out["mcp_d1_diurnal_slope"] = out["mcp_d1_same_h"] - out["mcp_d1_prev_h"]

    out["mcp_d1_day_mean"] = lookup_day_agg("mcp_rs_per_mwh", 1, "mean")
    out["mcp_d1_day_std"] = lookup_day_agg("mcp_rs_per_mwh", 1, "std")
    out["mcp_d1_day_min"] = lookup_day_agg("mcp_rs_per_mwh", 1, "min")
    out["mcp_d1_day_max"] = lookup_day_agg("mcp_rs_per_mwh", 1, "max")
    out["mcp_d1_cap_hits"] = lookup_day_agg("mcp_rs_per_mwh", 1, "cap_hits")
    out["mcp_7d_same_h_mean"] = lookup_7d_same_h("mcp_rs_per_mwh", "mean")
    out["mcp_7d_rolling_mean"] = lookup_7d_all_h_mean("mcp_rs_per_mwh")

    # =========================================================================
    # FAMILY 2: STRICT D-1 PUBLISHED IEX ORDER-BOOK LIQUIDITY (7 FEATURES)
    # =========================================================================
    out["purchase_bid_d1"] = lookup_day_shift("purchase_bid_mwh", 1)
    out["sell_bid_d1"] = lookup_day_shift("sell_bid_mwh", 1)
    out["mcv_d1"] = lookup_day_shift("mcv_mwh", 1)
    out["market_tightness_d1"] = out["purchase_bid_d1"] / np.maximum(out["sell_bid_d1"], 1.0)
    pb_d7 = lookup_day_shift("purchase_bid_mwh", 7)
    sb_d7 = lookup_day_shift("sell_bid_mwh", 7)
    out["market_tightness_d7"] = pb_d7 / np.maximum(sb_d7, 1.0)
    # Mean buy/sell ratio across all 24h of day D-1
    tight_piv = panels["purchase_bid_mwh"] / np.maximum(panels["sell_bid_mwh"], 1.0)
    out["market_tightness_d1_day_mean"] = dates.map(tight_piv.shift(1).mean(axis=1)).values.astype(np.float64)
    out["purchase_bid_d1_diff_d2"] = out["purchase_bid_d1"] - lookup_day_shift("purchase_bid_mwh", 2)

    # =========================================================================
    # FAMILY 3: DAY-AHEAD PHYSICAL GRID & RENEWABLE FORECASTS (17 FEATURES)
    # =========================================================================
    if use_oracle_exog:
        d_use = df["demand_mw"].values.astype(np.float64)
        s_use = df["solar_generation_mw"].values.astype(np.float64)
        w_use = df["wind_generation_mw"].values.astype(np.float64)
        t_mean = df["temperature_mean_c"].values.astype(np.float64)
        t_max = df["temperature_max_c"].values.astype(np.float64)
        at_mean = df["apparent_temperature_mean_c"].values.astype(np.float64)
        rh_mean = df["humidity_mean_pct"].values.astype(np.float64)
        ws_mean = df["weather_wind_speed_mean_ms"].values.astype(np.float64)
        pr_mean = df["precipitation_mean_mm"].values.astype(np.float64)
    else:
        d_use = fcst["demand_mw"]
        s_use = fcst["solar_generation_mw"]
        w_use = fcst["wind_generation_mw"]
        t_mean = fcst["temperature_mean_c"]
        t_max = fcst["temperature_max_c"]
        at_mean = fcst["apparent_temperature_mean_c"]
        rh_mean = fcst["humidity_mean_pct"]
        ws_mean = fcst["weather_wind_speed_mean_ms"]
        pr_mean = fcst["precipitation_mean_mm"]

    nd_use = d_use - (s_use + w_use)
    nd_series = pd.Series(nd_use, index=df.index)
    # Compute intraday ramps strictly within the forecasted Day-D trajectory
    nd_day_df = pd.DataFrame({"date": dates, "hour": hours, "nd": nd_use})
    nd_day_max = nd_day_df.groupby("date")["nd"].transform("max").values

    out["demand_fcst_mw"] = d_use
    out["solar_fcst_mw"] = s_use
    out["wind_fcst_mw"] = w_use
    out["net_demand_fcst_mw"] = nd_use
    out["re_penetration_fcst_pct"] = (s_use + w_use) / np.maximum(d_use, 1.0) * 100.0
    out["net_demand_fcst_ramp_1"] = nd_series.diff(1).fillna(0.0).values
    out["net_demand_fcst_ramp_3"] = nd_series.diff(3).fillna(0.0).values
    out["net_demand_fcst_day_max"] = nd_day_max

    d_d2 = lookup_day_shift("demand_mw", 2)
    s_d2 = lookup_day_shift("solar_generation_mw", 2)
    w_d2 = lookup_day_shift("wind_generation_mw", 2)
    nd_d2 = d_d2 - (s_d2 + w_d2)
    out["net_demand_fcst_vs_d2"] = nd_use - nd_d2
    out["demand_d2_same_h"] = d_d2
    out["net_demand_d2_same_h"] = nd_d2
    out["solar_d2_same_h"] = s_d2
    out["wind_d2_same_h"] = w_d2
    d1_morn = lookup_morning_mean("demand_mw", 1)
    d2_morn = lookup_morning_mean("demand_mw", 2)
    out["demand_d1_morn_mean"] = d1_morn
    out["demand_d1_morn_vs_d2"] = d1_morn - d2_morn

    is_peak = np.isin(hours, [18, 19, 20, 21, 22]).astype(np.float64)
    cdd_fcst = np.maximum(0.0, t_mean - 24.0)
    out["net_demand_fcst_x_peak"] = nd_use * is_peak
    out["net_demand_fcst_x_cdd"] = nd_use * cdd_fcst

    # =========================================================================
    # FAMILY 4: DAY-AHEAD WEATHER & THERMAL STRESS FORECASTS (10 FEATURES)
    # =========================================================================
    out["temp_mean_fcst_c"] = t_mean
    out["temp_max_fcst_c"] = t_max
    out["apparent_temp_fcst_c"] = at_mean
    out["humidity_fcst_pct"] = rh_mean
    out["wind_speed_fcst_ms"] = ws_mean
    out["precip_fcst_mm"] = pr_mean
    out["cdd_24_fcst"] = cdd_fcst
    out["temp_sq_fcst"] = t_mean ** 2
    out["temp_d1_morn_mean"] = lookup_morning_mean("temperature_mean_c", 1)
    out["temp_fcst_diff_d2"] = t_mean - lookup_day_shift("temperature_mean_c", 2)

    # =========================================================================
    # FAMILY 5: DETERMINISTIC CALENDAR, HOLIDAY & SOLAR HARMONICS (10 FEATURES)
    # =========================================================================
    doy = df["timestamp"].dt.dayofyear.values
    dow = df["timestamp"].dt.dayofweek.values
    out["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
    out["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
    out["dow_sin"] = np.sin(2.0 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2.0 * np.pi * dow / 7.0)
    out["doy_sin"] = np.sin(2.0 * np.pi * doy / 365.25)
    out["doy_cos"] = np.cos(2.0 * np.pi * doy / 365.25)
    out["is_weekend"] = (dow >= 5).astype(np.float64)
    out["is_holiday_india"] = df["date_str"].isin(INDIAN_HOLIDAYS).astype(np.float64)
    out["is_peak_hour"] = is_peak
    out["solar_elevation_deg"] = compute_solar_elevation_deg(df["timestamp"])

    # Also attach auxiliary realized columns for post-hoc evaluation & physical validation
    # (prefixed with _actual_ and strictly excluded from feature columns during model training!)
    out["_actual_demand_mw"] = df["demand_mw"].values
    out["_actual_solar_mw"] = df["solar_generation_mw"].values
    out["_actual_wind_mw"] = df["wind_generation_mw"].values
    out["_actual_net_demand_mw"] = df["demand_mw"].values - (df["solar_generation_mw"].values + df["wind_generation_mw"].values)
    out["_actual_temp_mean_c"] = df["temperature_mean_c"].values

    return out


def main() -> None:
    t0 = time.perf_counter()
    print("=" * 80)
    print("ENERGYCAST V2 — STRICT D-1 10:30 AM CAUSAL FORECAST RECONSTRUCTION PIPELINE")
    print("=" * 80)

    df = pd.read_csv(MASTER_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Clean 4 isolated SCADA zero-demand dropout hours via linear interpolation
    dropout = df["demand_mw"] <= 1000.0
    if dropout.any():
        print(f"Interpolating {dropout.sum()} isolated SCADA dropout hours...")
        for col in ["demand_mw", "solar_generation_mw", "wind_generation_mw"]:
            df.loc[dropout, col] = np.nan
            df[col] = df[col].interpolate(method="linear")

    df["date"] = df["timestamp"].dt.normalize()
    df["date_str"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["timestamp"].dt.hour

    panel_cols = [
        "mcp_rs_per_mwh", "purchase_bid_mwh", "sell_bid_mwh", "mcv_mwh",
        "demand_mw", "solar_generation_mw", "wind_generation_mw",
        "temperature_mean_c", "temperature_max_c", "temperature_min_c",
        "apparent_temperature_mean_c", "humidity_mean_pct",
        "weather_wind_speed_mean_ms", "precipitation_mean_mm",
    ]
    panels = build_daily_panel(df, panel_cols)

    print("Building strictly causal Stage-1 exogenous feature matrix (cutoff <= D-1 10:00 IST)...")
    X_s1 = build_stage1_exogenous_features(df, panels)

    # Drop first 14 days (336 hours) warm-up so D-14 lags have zero NaNs
    warmup = 14 * 24
    df_clean = df.iloc[warmup:].reset_index(drop=True)
    X_s1_clean = X_s1.iloc[warmup:].reset_index(drop=True)
    assert X_s1_clean.isna().sum().sum() == 0, f"NaNs in X_s1: {X_s1_clean.isna().sum()[X_s1_clean.isna().sum()>0]}"
    print(f"Stage-1 matrix shape: {X_s1_clean.shape} | Range: {df_clean['timestamp'].min()} -> {df_clean['timestamp'].max()}")

    # Train Stage-1 Causal Day-Ahead Forecasters for all 9 exogenous signals
    stage1_specs = [
        ("demand_mw", 50000.0, None),
        ("solar_generation_mw", 0.0, None),
        ("wind_generation_mw", 0.0, None),
        ("temperature_mean_c", -5.0, 52.0),
        ("temperature_max_c", -5.0, 55.0),
        ("apparent_temperature_mean_c", -5.0, 60.0),
        ("humidity_mean_pct", 0.0, 100.0),
        ("weather_wind_speed_mean_ms", 0.0, None),
        ("precipitation_mean_mm", 0.0, None),
    ]

    fcst_dict: dict[str, np.ndarray] = {}
    stage1_metrics = []
    print("\nTraining Stage-1 Causal Day-Ahead Exogenous Forecasters (Purged OOF Train | Expanding Val/Test):")
    for col, c_lo, c_hi in stage1_specs:
        preds, m = fit_and_predict_stage1_target(
            X_s1_clean,
            df_clean[col].values.astype(np.float64),
            df_clean["timestamp"],
            col,
            clip_low=c_lo,
            clip_high=c_hi,
        )
        fcst_dict[col] = preds
        stage1_metrics.append(m)
        t25 = m["test_2025"]
        v24 = m["val_2024"]
        print(
            f"  {col:30s} | Val24 R2={v24['R2']:.4f} MAE={v24['MAE']:8.2f} | "
            f"Test25 R2={t25['R2']:.4f} MAE={t25['MAE']:8.2f} nRMSE={t25['nRMSE_pct']:5.2f}%"
            + (f" MAPE={t25['MAPE_pct']:.2f}%" if t25["MAPE_pct"] is not None else "")
        )

    # Also compute reconstructed Net Thermal Demand forecast quality
    nd_true = df_clean["demand_mw"].values - (df_clean["solar_generation_mw"].values + df_clean["wind_generation_mw"].values)
    nd_fcst = fcst_dict["demand_mw"] - (fcst_dict["solar_generation_mw"] + fcst_dict["wind_generation_mw"])
    test_mask = (df_clean["timestamp"] >= pd.Timestamp("2025-01-01 00:00:00")).values
    val_mask = ((df_clean["timestamp"] >= pd.Timestamp("2024-01-01 00:00:00")) & (df_clean["timestamp"] <= pd.Timestamp("2024-12-31 23:00:00"))).values
    for sp_name, mk in [("val_2024", val_mask), ("test_2025", test_mask)]:
        mae = np.mean(np.abs(nd_true[mk] - nd_fcst[mk]))
        rmse = np.sqrt(np.mean((nd_true[mk] - nd_fcst[mk]) ** 2))
        mape = np.mean(np.abs(nd_true[mk] - nd_fcst[mk]) / nd_true[mk]) * 100.0
        r2 = 1.0 - np.sum((nd_true[mk] - nd_fcst[mk]) ** 2) / np.sum((nd_true[mk] - np.mean(nd_true[mk])) ** 2)
        if sp_name == "val_2024":
            nd_v = {"MAE": round(float(mae), 2), "RMSE": round(float(rmse), 2), "nRMSE_pct": round(float(rmse / (nd_true[mk].max() - nd_true[mk].min()) * 100), 2), "R2": round(float(r2), 4), "MAPE_pct": round(float(mape), 2)}
        else:
            nd_t = {"MAE": round(float(mae), 2), "RMSE": round(float(rmse), 2), "nRMSE_pct": round(float(rmse / (nd_true[mk].max() - nd_true[mk].min()) * 100), 2), "R2": round(float(r2), 4), "MAPE_pct": round(float(mape), 2)}
    stage1_metrics.append({"target": "net_demand_mw (derived)", "val_2024": nd_v, "test_2025": nd_t})
    print(f"  {'net_demand_mw (derived)':30s} | Val24 R2={nd_v['R2']:.4f} MAPE={nd_v['MAPE_pct']:.2f}% | Test25 R2={nd_t['R2']:.4f} MAE={nd_t['MAE']:8.2f} MAPE={nd_t['MAPE_pct']:.2f}%")

    # Save Stage-1 reconstruction accuracy table
    s1_rows = []
    for m in stage1_metrics:
        s1_rows.append({
            "Exogenous_Signal": m["target"],
            "Val24_MAE": m["val_2024"]["MAE"],
            "Val24_RMSE": m["val_2024"]["RMSE"],
            "Val24_R2": m["val_2024"]["R2"],
            "Test25_MAE": m["test_2025"]["MAE"],
            "Test25_RMSE": m["test_2025"]["RMSE"],
            "Test25_nRMSE_pct": m["test_2025"]["nRMSE_pct"],
            "Test25_MAPE_pct": m["test_2025"]["MAPE_pct"],
            "Test25_R2": m["test_2025"]["R2"],
        })
    pd.DataFrame(s1_rows).to_csv(TABLE_DIR / "v2_stage1_exogenous_forecast_quality.csv", index=False)

    # Assemble Stage-2 feature matrices (Operational D-1 AND Oracle-Exog)
    print("\nAssembling 62-feature Stage-2 datasets (Strict Operational D-1 vs. Ex-Post Oracle-Exog)...")
    op_full = assemble_stage2_feature_matrix(df_clean, panels, fcst_dict, use_oracle_exog=False)
    or_full = assemble_stage2_feature_matrix(df_clean, panels, fcst_dict, use_oracle_exog=True)

    feature_cols = [c for c in op_full.columns if c not in ("timestamp", "mcp_rs_per_mwh") and not c.startswith("_actual_")]
    assert len(feature_cols) == 62, f"Expected 62 features, got {len(feature_cols)}"
    assert op_full[feature_cols].isna().sum().sum() == 0, "NaNs found in operational features!"
    assert or_full[feature_cols].isna().sum().sum() == 0, "NaNs found in oracle-exog features!"

    # Strict chronological partitioning (identical Val 2024 & Test 2025 boundaries!)
    splits = {
        "train": lambda ts: ts <= pd.Timestamp("2023-12-31 23:00:00"),
        "val":   lambda ts: (ts >= pd.Timestamp("2024-01-01 00:00:00")) & (ts <= pd.Timestamp("2024-12-31 23:00:00")),
        "test":  lambda ts: ts >= pd.Timestamp("2025-01-01 00:00:00"),
    }

    for sp_name, fn in splits.items():
        mk = fn(op_full["timestamp"])
        op_full[mk].to_csv(OUT_DIR / f"operational_{sp_name}.csv", index=False)
        or_full[mk].to_csv(OUT_DIR / f"oracle_exog_{sp_name}.csv", index=False)
        print(f"  Saved {sp_name:5s}: {mk.sum():6,d} hours ({op_full.loc[mk, 'timestamp'].min()} -> {op_full.loc[mk, 'timestamp'].max()})")

    meta = {
        "feature_count": len(feature_cols),
        "feature_cols": feature_cols,
        "train_hours": int(splits["train"](op_full["timestamp"]).sum()),
        "val_hours": int(splits["val"](op_full["timestamp"]).sum()),
        "test_hours": int(splits["test"](op_full["timestamp"]).sum()),
        "causality_gate": "10:30 AM IST on Day D-1 (zero same-day prices, zero Day-D realized telemetry, zero D-1 >10:00 SCADA)",
        "stage1_metrics": stage1_metrics,
    }
    with open(OUT_DIR / "causal_d1_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n[OK] Strict D-1 causal dataset built in {time.perf_counter() - t0:.1f}s -> {OUT_DIR}")


if __name__ == "__main__":
    main()
