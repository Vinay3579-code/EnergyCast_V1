"""
EnergyCast V2 (TPWRS Revision) — Step 5 (Upgraded):
Comprehensive Renewable, Weather & Unexpected Thermal Outage Stress-Testing Suite
using the Capacity-Adaptive Operational D-1 Innovation Model + Residual-CQR
Probabilistic Intervals + Stochastic CVaR Procurement Optimizer.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from run_stochastic_cvar_procurement import (
    build_industrial_profiles,
    calc_cvar,
    solve_procurement_lp,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAUSAL_DIR = PROJECT_ROOT / "data" / "processed" / "causal_d1"
MODELS_V2_DIR = PROJECT_ROOT / "models" / "v2_causal"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def apply_physical_shock(
    df_base: pd.DataFrame,
    demand_pct: float = 0.0,
    solar_pct: float = 0.0,
    wind_pct: float = 0.0,
    temp_delta_c: float = 0.0,
    thermal_outage_gw: float = 0.0,
) -> pd.DataFrame:
    df = df_base.copy()
    d_old = df["demand_fcst_mw"].values
    nd_old = df["net_demand_fcst_mw"].values
    d_new = d_old * (1.0 + demand_pct / 100.0)
    s_new = np.maximum(0.0, df["solar_fcst_mw"].values * (1.0 + solar_pct / 100.0))
    w_new = np.maximum(0.0, df["wind_fcst_mw"].values * (1.0 + wind_pct / 100.0))

    outage_mw = thermal_outage_gw * 1000.0
    nd_new = d_new - (s_new + w_new) + outage_mw
    delta_nd = nd_new - nd_old
    nd_series = pd.Series(nd_new, index=df.index)

    dates = pd.to_datetime(df["timestamp"]).dt.normalize()
    nd_day_max = pd.DataFrame({"d": dates, "nd": nd_new}).groupby("d")["nd"].transform("max").values

    t_new = df["temp_mean_fcst_c"].values + temp_delta_c
    cdd_new = np.maximum(0.0, t_new - 24.0)

    df["demand_fcst_mw"] = d_new
    df["solar_fcst_mw"] = s_new
    df["wind_fcst_mw"] = w_new
    df["net_demand_fcst_mw"] = nd_new
    df["re_penetration_fcst_pct"] = (s_new + w_new) / np.maximum(d_new, 1.0) * 100.0
    df["net_demand_fcst_ramp_1"] = nd_series.diff(1).fillna(0.0).values
    df["net_demand_fcst_ramp_3"] = nd_series.diff(3).fillna(0.0).values
    df["net_demand_fcst_day_max"] = nd_day_max
    df["net_demand_fcst_vs_d2"] = nd_new - df["net_demand_d2_same_h"].values
    df["net_demand_fcst_x_peak"] = nd_new * df["is_peak_hour"].values
    df["net_demand_fcst_x_cdd"] = nd_new * cdd_new

    # Propagate into trailing-30-day capacity-relative anomaly features!
    df["nd_fcst_rel_30d"] = df["nd_fcst_rel_30d"].values + delta_nd
    roll_std_est = np.where(np.abs(df["nd_fcst_zscore_30d"].values) > 0.15,
                            np.abs(df_base["nd_fcst_rel_30d"].values / df_base["nd_fcst_zscore_30d"].values), 15000.0)
    roll_std_est = np.clip(roll_std_est, 5000.0, 30000.0)
    df["nd_fcst_zscore_30d"] = df["nd_fcst_rel_30d"].values / roll_std_est

    df["temp_mean_fcst_c"] = t_new
    df["temp_max_fcst_c"] = df["temp_max_fcst_c"].values + temp_delta_c
    df["apparent_temp_fcst_c"] = df["apparent_temp_fcst_c"].values + temp_delta_c
    df["cdd_24_fcst"] = cdd_new
    df["temp_sq_fcst"] = t_new ** 2
    df["temp_fcst_diff_d2"] = df["temp_fcst_diff_d2"].values + temp_delta_c

    if thermal_outage_gw > 0.0:
        tau_boost = 1.0 + 0.045 * thermal_outage_gw
        df["market_tightness_d1"] = df["market_tightness_d1"].values * tau_boost
        df["market_tightness_d1_day_mean"] = df["market_tightness_d1_day_mean"].values * tau_boost
        df["sell_bid_d1"] = np.maximum(100.0, df["sell_bid_d1"].values / tau_boost)

    return df


def main() -> None:
    t0 = time.perf_counter()
    print("=" * 86)
    print("ENERGYCAST V2 — COMPREHENSIVE WEATHER, RE & THERMAL OUTAGE STRESS-TEST SUITE")
    print("=" * 86)

    te_df = pd.read_csv(CAUSAL_DIR / "operational_test_v2.csv")
    with open(TABLE_DIR / "v2_benchmark_summary.json") as f:
        bench_meta = json.load(f)
    feature_cols = bench_meta["feature_cols"]
    cqr_margins = bench_meta["cqr_margins"]

    lgb_pt = joblib.load(MODELS_V2_DIR / "lightgbm_d1.joblib")
    q_models_res = joblib.load(MODELS_V2_DIR / "residual_quantiles_d1.joblib")

    hrs = pd.to_datetime(te_df["timestamp"]).dt.hour.values
    peak_mask = np.isin(hrs, [18, 19, 20, 21, 22])
    solar_mask = (hrs >= 9) & (hrs <= 16)
    n_days = len(te_df) // 24
    anc = te_df["mcp_d1_same_h"].values

    p1 = build_industrial_profiles(te_df)["P1_Flat_Industrial_100MW"]
    base_mw = p1["base_mw"]

    def score_df(df_in: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        X = df_in[feature_cols].values
        # Innovation target reconstruction: P_hat = clip(P_{D-1,h} + delta_P_hat, 0, 10000)
        pt = np.clip(anc + lgb_pt.predict(X), 0.0, 10000.0)
        X_q = np.column_stack([X, pt, 10000.0 - pt, np.abs(pt - 5000.0)])
        qmat = np.column_stack([np.clip(pt + q_models_res[tau].predict(X_q), 0.0, 10000.0) for tau in QUANTILES])
        reg = np.zeros(len(hrs), dtype=int)
        reg[solar_mask] = 1
        reg[peak_mask] = 2
        for rc in [0, 1, 2]:
            mk = reg == rc
            m90 = cqr_margins.get(f"nom90_reg{rc}", 0.0)
            qmat[mk, 0] -= m90
            qmat[mk, -1] += m90
        qmat = np.sort(np.clip(qmat, 0.0, 10000.0), axis=1)
        return pt, qmat

    scenarios = [
        ("Baseline (Unperturbed D-1 Forecast)",        dict()),
        ("Solar Drop -10%",                            dict(solar_pct=-10.0)),
        ("Solar Drop -20%",                            dict(solar_pct=-20.0)),
        ("Solar Drop -30%",                            dict(solar_pct=-30.0)),
        ("Solar Drop -40% (Heavy Cloud Cover)",        dict(solar_pct=-40.0)),
        ("Wind Drop -10%",                             dict(wind_pct=-10.0)),
        ("Wind Drop -20%",                             dict(wind_pct=-20.0)),
        ("Wind Drop -30%",                             dict(wind_pct=-30.0)),
        ("Wind Drop -40% (Monsoon Wind Lull)",         dict(wind_pct=-40.0)),
        ("Demand Surge +5%",                           dict(demand_pct=+5.0)),
        ("Demand Surge +10%",                          dict(demand_pct=+10.0)),
        ("Demand Surge +15% (Extreme Peak Load)",      dict(demand_pct=+15.0)),
        ("Thermal Outage -5 GW",                       dict(thermal_outage_gw=5.0)),
        ("Thermal Outage -10 GW",                      dict(thermal_outage_gw=10.0)),
        ("Thermal Outage -15 GW (Severe Forced Trip)", dict(thermal_outage_gw=15.0)),
        ("Compound: Heatwave + Low RE (+10%D,+4C,-30%S,-30%W)", dict(demand_pct=10.0, temp_delta_c=4.0, solar_pct=-30.0, wind_pct=-30.0)),
        ("Compound Crisis: Outage(-8GW)+Heatwave+Cloud+WindLull", dict(thermal_outage_gw=8.0, demand_pct=8.0, temp_delta_c=3.5, solar_pct=-35.0, wind_pct=-25.0)),
    ]

    pt_base, q_base = score_df(te_df)
    mean_pt_base = float(np.mean(pt_base))
    peak_pt_base = float(np.mean(pt_base[peak_mask]))
    w90_base = float(np.mean(q_base[:, -1] - q_base[:, 0]))
    sample_days = np.linspace(0, n_days - 1, 35, dtype=int)

    rows = []
    print(f"\n{'Scenario':55s} | {'MeanP':7s} | {'DeltaP':7s} | {'PeakP':7s} | {'W90':6s} | {'CapRisk':7s} | {'OptBill':7s} | {'CVaR90':7s}")
    print("-" * 124)

    for s_name, kwargs in scenarios:
        df_s = apply_physical_shock(te_df, **kwargs) if kwargs else te_df
        pt_s, q_s = score_df(df_s)

        mean_p = float(np.mean(pt_s))
        delta_p = mean_p - mean_pt_base
        delta_pct = delta_p / max(mean_pt_base, 1.0) * 100.0
        peak_p = float(np.mean(pt_s[peak_mask]))
        solar_p = float(np.mean(pt_s[solar_mask]))
        w90 = float(np.mean(q_s[:, -1] - q_s[:, 0]))
        q95_mean = float(np.mean(q_s[:, -1]))
        cap_risk_pct = float(np.mean(q_s[:, -1] >= 9500.0) * 100.0)
        mean_nd_gw = float(np.mean(df_s["net_demand_fcst_mw"].values) / 1000.0)

        base_bills, cvar_bills, cvar90_base_list, cvar90_opt_list, shifted_mwh_list = [], [], [], [], []
        for d_idx in sample_days:
            sl = slice(d_idx * 24, (d_idx + 1) * 24)
            p_d = pt_s[sl]
            q_d = q_s[sl]
            grid = np.linspace(0.0, 1.0, 21)
            sc_21 = np.zeros((21, 24))
            for h_i in range(24):
                sc_21[:, h_i] = np.interp(grid, np.linspace(0.0, 1.0, 7), q_d[h_i])
            L_cvar = solve_procurement_lp(base_mw, sc_21, gamma=0.30, lam=1.0, alpha=0.90, ramp_frac=0.25, buffer_hours=3.0)
            base_bills.append(float(base_mw @ p_d))
            cvar_bills.append(float(L_cvar @ p_d))
            cvar90_base_list.append(calc_cvar(sc_21 @ base_mw, 0.90))
            cvar90_opt_list.append(calc_cvar(sc_21 @ L_cvar, 0.90))
            shifted_mwh_list.append(float(np.sum(np.abs(L_cvar - base_mw)) / 2.0))

        row = {
            "Scenario": s_name,
            "Mean_Net_Demand_GW": round(mean_nd_gw, 2),
            "Mean_Forecast_MCP_Rs": round(mean_p, 2),
            "Delta_Mean_MCP_Rs": round(delta_p, 2),
            "Delta_Mean_MCP_pct": round(delta_pct, 2),
            "Evening_Peak_MCP_Rs": round(peak_p, 2),
            "Delta_Peak_MCP_Rs": round(peak_p - peak_pt_base, 2),
            "Solar_Window_MCP_Rs": round(solar_p, 2),
            "Interval_Width_W90_Rs": round(w90, 1),
            "Delta_W90_Rs": round(w90 - w90_base, 1),
            "Upper_Tail_q95_Rs": round(q95_mean, 1),
            "Cap_Risk_P_q95_ge_9500_pct": round(cap_risk_pct, 2),
            "Unopt_Daily_Bill_Lakhs": round(float(np.mean(base_bills)) / 1e5, 2),
            "Stoch_Opt_Bill_Lakhs": round(float(np.mean(cvar_bills)) / 1e5, 2),
            "Opt_Save_Under_Shock_pct": round((1.0 - float(np.mean(cvar_bills)) / max(float(np.mean(base_bills)), 1.0)) * 100.0, 2),
            "Unopt_CVaR90_Lakhs": round(float(np.mean(cvar90_base_list)) / 1e5, 2),
            "Opt_CVaR90_Lakhs": round(float(np.mean(cvar90_opt_list)) / 1e5, 2),
            "CVaR90_Risk_Reduction_Lakhs": round((float(np.mean(cvar90_base_list)) - float(np.mean(cvar90_opt_list))) / 1e5, 2),
            "Shifted_Volume_MWh_Day": round(float(np.mean(shifted_mwh_list)), 1),
        }
        rows.append(row)
        print(
            f"{s_name:55s} | {mean_p:7.1f} | {delta_p:+7.1f} | {peak_p:7.1f} | {w90:6.1f} | "
            f"{cap_risk_pct:6.1f}% | {row['Stoch_Opt_Bill_Lakhs']:6.2f}L | {row['Opt_CVaR90_Lakhs']:6.2f}L"
        )

    pd.DataFrame(rows).to_csv(TABLE_DIR / "v2_comprehensive_stress_tests.csv", index=False)
    print(f"\n[OK] Comprehensive stress-test battery completed in {time.perf_counter() - t0:.1f}s!")


if __name__ == "__main__":
    main()
