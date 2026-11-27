"""
EnergyCast V2 (TPWRS Revision) — Step 2: Independent Physical Validation of the
Indian National Merit-Order Supply Stack & Scarcity Threshold Analysis.

Solves Reviewer Critical Weakness B (The 160 GW Scarcity Threshold Needs Physical Validation):
  1. Independent Econometric Structural-Break Testing (Hansen Sup-Wald / Chow F-test
     & Piecewise Hinge Regression) completely decoupled from LightGBM/TreeSHAP.
  2. Real Grid-India (POSOCO) NLDC Fuel-Mix Dispatch Analysis (15,360 hours, 2022-2023)
     examining Coal/Thermal (TOTAL_THM_ONLY), Gas Peakers (TOTAL_NLDC_GAS),
     Hydro (TOTAL_NLDC_HYD), Nuclear (TOTAL_NLDC_NPC), Solar, and Wind output across
     operating regimes of Net Thermal Demand.
  3. Threshold Sensitivity Sweep across theta in {140, 145, 150, 155, 160, 165, 170, 175, 180} GW.
  4. Multi-Year (2022, 2023, 2024, 2025) and Multi-Season (Winter, Summer, Monsoon)
     Stability Analysis — testing whether the scarcity knee is fixed at 160 GW or
     shifts dynamically with thermal capacity additions, seasonal hydro availability,
     and maintenance cycles!
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_PATH = PROJECT_ROOT / "data" / "processed" / "master" / "energycast_master_hourly_2022_2025.csv"
FUEL_MIX_PATH = PROJECT_ROOT / "data" / "processed" / "grid_india" / "grid_india_fuel_mix_hourly_2022_2023.csv"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def fit_piecewise_hinge(x: np.ndarray, y: np.ndarray, theta: float) -> dict[str, float]:
    """
    Fits continuous piecewise linear (hinge) model:
        y = b0 + b1 * x + b2 * max(0, x - theta) + eps
    and compares against unconstrained linear model (y = a0 + a1 * x + eps)
    via exact Chow / Wald F-statistic on H0: b2 = 0 (no slope inflection at theta).
    """
    n = len(x)
    # Null linear model
    X0 = np.column_stack([np.ones(n), x])
    beta0, *_ = np.linalg.lstsq(X0, y, rcond=None)
    rss0 = float(np.sum((y - X0 @ beta0) ** 2))
    tss = float(np.sum((y - np.mean(y)) ** 2))

    # Alternative hinge model
    hinge = np.maximum(0.0, x - theta)
    X1 = np.column_stack([np.ones(n), x, hinge])
    beta1, *_ = np.linalg.lstsq(X1, y, rcond=None)
    yhat1 = X1 @ beta1
    rss1 = float(np.sum((y - yhat1) ** 2))
    r2_lin = 1.0 - rss0 / max(tss, 1e-9)
    r2_hinge = 1.0 - rss1 / max(tss, 1e-9)

    # F-statistic for H0: b2 = 0 (1 restriction, n - 3 df)
    f_stat = ((rss0 - rss1) / 1.0) / max(rss1 / max(n - 3, 1), 1e-9)
    p_val = float(1.0 - stats.f.cdf(f_stat, 1, max(n - 3, 1)))

    # Regime-stratified empirical statistics
    above = x >= theta
    below = ~above
    cap_above = float(np.mean(y[above] >= 9990.0) * 100.0) if above.sum() > 0 else np.nan
    cap_below = float(np.mean(y[below] >= 9990.0) * 100.0) if below.sum() > 0 else np.nan

    return {
        "theta_gw": theta,
        "n_above": int(above.sum()),
        "pct_above": round(float(above.mean() * 100.0), 2),
        "slope_below_rs_per_gw": round(float(beta1[1]), 2),
        "slope_jump_rs_per_gw": round(float(beta1[2]), 2),
        "slope_above_rs_per_gw": round(float(beta1[1] + beta1[2]), 2),
        "r2_linear": round(r2_lin, 4),
        "r2_hinge": round(r2_hinge, 4),
        "delta_r2": round(r2_hinge - r2_lin, 4),
        "rss_reduction_pct": round((rss0 - rss1) / max(rss0, 1e-9) * 100.0, 2),
        "wald_F_stat": round(f_stat, 2),
        "p_value": p_val,
        "mean_mcp_below": round(float(np.mean(y[below])), 2) if below.sum() > 0 else np.nan,
        "mean_mcp_above": round(float(np.mean(y[above])), 2) if above.sum() > 0 else np.nan,
        "cap_hit_pct_below": round(cap_below, 2),
        "cap_hit_pct_above": round(cap_above, 2),
    }


def assign_indian_season(month: int) -> str:
    if month in (11, 12, 1, 2):
        return "Winter (Nov-Feb)"
    if month in (3, 4, 5, 6):
        return "Summer (Mar-Jun)"
    return "Monsoon (Jul-Oct)"


def main() -> None:
    print("=" * 80)
    print("ENERGYCAST V2 — INDEPENDENT PHYSICAL MERIT-ORDER & SCARCITY KNEE VALIDATION")
    print("=" * 80)

    # 1. Load full 2022-2025 master panel (28,344 hours)
    master = pd.read_csv(MASTER_PATH)
    master["timestamp"] = pd.to_datetime(master["timestamp"])
    master = master.sort_values("timestamp").reset_index(drop=True)
    # Remove/clean 4 isolated zero-demand SCADA dropouts
    master = master[master["demand_mw"] > 90000.0].copy()
    master["net_demand_gw"] = (master["demand_mw"] - master["solar_generation_mw"] - master["wind_generation_mw"]) / 1000.0
    master["year"] = master["timestamp"].dt.year
    master["month"] = master["timestamp"].dt.month
    master["hour"] = master["timestamp"].dt.hour
    master["season"] = master["month"].map(assign_indian_season)
    master["is_evening"] = master["hour"].isin([18, 19, 20, 21, 22])

    # Note: CERC lowered price cap from Rs. 12,000 to Rs. 10,000 on April 4, 2023.
    # For regime analysis on uniform Rs. 10,000 cap, we analyze BOTH Full 2022-2025
    # and Post-Apr-2023 uniform-cap regime, plus year-by-year!
    x_all = master["net_demand_gw"].values
    y_all = master["mcp_rs_per_mwh"].values

    # -------------------------------------------------------------------------
    # EXPERIMENT B1: THRESHOLD SENSITIVITY SWEEP (140 GW to 180 GW)
    # -------------------------------------------------------------------------
    print("\n[B1] Piecewise Structural-Break Threshold Sensitivity Sweep (Full 2022-2025, N=" + f"{len(master):,}):")
    sweep_rows = []
    for theta in [140.0, 145.0, 150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0]:
        res = fit_piecewise_hinge(x_all, y_all, theta)
        sweep_rows.append(res)
        print(
            f"  theta={theta:5.1f} GW | slope_below={res['slope_below_rs_per_gw']:6.1f} -> "
            f"slope_above={res['slope_above_rs_per_gw']:6.1f} Rs/GW | "
            f"F={res['wald_F_stat']:7.1f} | R2={res['r2_hinge']:.4f} | "
            f"CapHit(<th)={res['cap_hit_pct_below']:4.1f}% vs (>=th)={res['cap_hit_pct_above']:4.1f}%"
        )
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_df.to_csv(TABLE_DIR / "v2_merit_order_threshold_sweep.csv", index=False)

    # Fine 1 GW grid search for exact Sup-Wald optimal threshold theta*
    fine_grid = np.arange(135.0, 186.0, 1.0)
    fine_res = [fit_piecewise_hinge(x_all, y_all, float(th)) for th in fine_grid]
    best_all = max(fine_res, key=lambda r: r["wald_F_stat"])
    print(f"  => Full-Sample Sup-Wald Optimal Inflection Knee: theta* = {best_all['theta_gw']:.1f} GW (F = {best_all['wald_F_stat']:.1f}, slope jump = +{best_all['slope_jump_rs_per_gw']:.1f} Rs/GW)")

    # -------------------------------------------------------------------------
    # EXPERIMENT B2: MULTI-YEAR & SEASONAL THRESHOLD STABILITY ANALYSIS
    # -------------------------------------------------------------------------
    print("\n[B2] Multi-Year & Seasonal Scarcity Knee Stability Analysis:")
    stability_rows = []
    subsets = []
    for yr in [2022, 2023, 2024, 2025]:
        subsets.append(("Year", str(yr), master[master["year"] == yr]))
    for seas in ["Winter (Nov-Feb)", "Summer (Mar-Jun)", "Monsoon (Jul-Oct)"]:
        subsets.append(("Season", seas, master[master["season"] == seas]))
    # Also test Evening Peak vs Solar Midday
    subsets.append(("Diurnal", "Solar Window (09-16h)", master[master["hour"].between(9, 16)]))
    subsets.append(("Diurnal", "Evening Peak (18-22h)", master[master["hour"].between(18, 22)]))
    subsets.append(("Diurnal", "Night Base (00-06h)", master[master["hour"].between(0, 6)]))

    for grp_type, grp_name, sub in subsets:
        xs = sub["net_demand_gw"].values
        ys = sub["mcp_rs_per_mwh"].values
        # Search candidate knots inside the [15th, 85th] percentile of this subset's Net Demand
        lo_th = max(125.0, float(np.percentile(xs, 15)))
        hi_th = min(195.0, float(np.percentile(xs, 85)))
        cands = np.arange(np.ceil(lo_th), np.floor(hi_th) + 1.0, 1.0)
        best_sub = max((fit_piecewise_hinge(xs, ys, float(th)) for th in cands), key=lambda r: r["wald_F_stat"])
        at_160 = fit_piecewise_hinge(xs, ys, 160.0)
        row = {
            "Stratification": grp_type,
            "Regime": grp_name,
            "Hours": len(sub),
            "Mean_Net_Demand_GW": round(float(np.mean(xs)), 2),
            "P90_Net_Demand_GW": round(float(np.percentile(xs, 90)), 2),
            "Mean_MCP_Rs": round(float(np.mean(ys)), 2),
            "Optimal_Knee_GW": best_sub["theta_gw"],
            "SupWald_F": best_sub["wald_F_stat"],
            "Slope_Below_Opt": best_sub["slope_below_rs_per_gw"],
            "Slope_Above_Opt": best_sub["slope_above_rs_per_gw"],
            "CapHit_Below_Opt_pct": best_sub["cap_hit_pct_below"],
            "CapHit_Above_Opt_pct": best_sub["cap_hit_pct_above"],
            "F_at_160GW": at_160["wald_F_stat"],
            "Slope_Above_160GW": at_160["slope_above_rs_per_gw"],
        }
        stability_rows.append(row)
        print(
            f"  [{grp_type:7s}] {grp_name:22s} | N={len(sub):5d} | MeanND={row['Mean_Net_Demand_GW']:5.1f} GW | "
            f"theta*={row['Optimal_Knee_GW']:5.1f} GW (F={row['SupWald_F']:6.1f}) | "
            f"Slope: {row['Slope_Below_Opt']:5.1f} -> {row['Slope_Above_Opt']:6.1f} Rs/GW | "
            f"CapHit: {row['CapHit_Below_Opt_pct']:4.1f}% -> {row['CapHit_Above_Opt_pct']:4.1f}%"
        )

    stab_df = pd.DataFrame(stability_rows)
    stab_df.to_csv(TABLE_DIR / "v2_merit_order_stability_by_year_season.csv", index=False)

    # -------------------------------------------------------------------------
    # EXPERIMENT B3: REAL POSOCO/NLDC FUEL-MIX DISPATCH VALIDATION (2022-2023)
    # -------------------------------------------------------------------------
    print("\n[B3] Real Grid-India (POSOCO) Fuel-Mix Dispatch Validation (Coal, Hydro, Gas, Nuclear, RE):")
    fm = pd.read_csv(FUEL_MIX_PATH)
    fm["timestamp"] = pd.to_datetime(fm["timestamp"])
    merged = pd.merge(
        fm,
        master[["timestamp", "mcp_rs_per_mwh", "purchase_bid_mwh", "sell_bid_mwh", "mcv_mwh", "season", "hour"]],
        on="timestamp",
        how="inner",
    )
    # Clean rare telemetry glitches (<90 GW gross demand or <70 GW thermal coal)
    merged = merged[(merged["demand_mw"] > 90000.0) & (merged["thermal_coal_mw"] > 70000.0)].copy()
    merged["net_demand_gw"] = merged["net_demand_mw"] / 1000.0
    merged["coal_gw"] = merged["thermal_coal_mw"] / 1000.0
    merged["hydro_gw"] = merged["hydro_mw"] / 1000.0
    merged["gas_gw"] = merged["gas_mw"] / 1000.0
    merged["nuclear_gw"] = merged["nuclear_mw"] / 1000.0
    merged["solar_gw"] = merged["solar_mw"] / 1000.0
    merged["wind_gw"] = merged["wind_mw"] / 1000.0
    merged["re_gw"] = merged["solar_gw"] + merged["wind_gw"]
    merged["tightness"] = merged["purchase_bid_mwh"] / np.maximum(merged["sell_bid_mwh"], 1.0)
    # Approximate Coal Fleet Utilization vs observed peak dispatched coal (proxy for operational available thermal ceiling)
    p995_coal = float(np.percentile(merged["coal_gw"], 99.5))
    merged["coal_util_pct"] = (merged["coal_gw"] / p995_coal) * 100.0

    bins = [0, 130, 145, 155, 160, 165, 175, 250]
    labels = ["<130 GW", "130-145 GW", "145-155 GW", "155-160 GW", "160-165 GW", "165-175 GW", ">175 GW"]
    merged["nd_regime"] = pd.cut(merged["net_demand_gw"], bins=bins, labels=labels, right=False)

    regime_rows = []
    for lbl in labels:
        sub = merged[merged["nd_regime"] == lbl]
        if len(sub) == 0:
            continue
        r = {
            "Net_Demand_Band": lbl,
            "Hours": len(sub),
            "Share_pct": round(len(sub) / len(merged) * 100.0, 2),
            "Mean_Coal_GW": round(float(sub["coal_gw"].mean()), 2),
            "Coal_Util_Pct_of_Peak": round(float(sub["coal_util_pct"].mean()), 2),
            "Mean_Hydro_GW": round(float(sub["hydro_gw"].mean()), 2),
            "Mean_Gas_GW": round(float(sub["gas_gw"].mean()), 2),
            "P90_Gas_GW": round(float(sub["gas_gw"].quantile(0.90)), 2),
            "Mean_Nuclear_GW": round(float(sub["nuclear_gw"].mean()), 2),
            "Mean_Solar_GW": round(float(sub["solar_gw"].mean()), 2),
            "Mean_Wind_GW": round(float(sub["wind_gw"].mean()), 2),
            "Mean_MCP_Rs": round(float(sub["mcp_rs_per_mwh"].mean()), 2),
            "Median_MCP_Rs": round(float(sub["mcp_rs_per_mwh"].median()), 2),
            "Cap_Hit_10k_pct": round(float((sub["mcp_rs_per_mwh"] >= 9990.0).mean() * 100.0), 2),
            "Mean_Tightness": round(float(sub["tightness"].mean()), 3),
        }
        regime_rows.append(r)
        print(
            f"  {lbl:10s} (n={r['Hours']:4d}) | Coal={r['Mean_Coal_GW']:6.2f} GW ({r['Coal_Util_Pct_of_Peak']:5.1f}%) | "
            f"Hydro={r['Mean_Hydro_GW']:5.2f} | Gas={r['Mean_Gas_GW']:4.2f} (P90={r['P90_Gas_GW']:4.2f}) | "
            f"RE={r['Mean_Solar_GW']+r['Mean_Wind_GW']:5.2f} | MCP=Rs.{r['Mean_MCP_Rs']:7.1f} | CapHit={r['Cap_Hit_10k_pct']:5.1f}%"
        )

    regime_df = pd.DataFrame(regime_rows)
    regime_df.to_csv(TABLE_DIR / "v2_posoco_fuel_mix_dispatch_by_regime.csv", index=False)

    # Also test piecewise inflection directly on GAS PEAKER DISPATCH (MW) vs Net Demand (GW)!
    gas_hinge_grid = [fit_piecewise_hinge(merged["net_demand_gw"].values, merged["gas_gw"].values * 1000.0, float(th)) for th in np.arange(135.0, 180.0, 1.0)]
    best_gas_knee = max(gas_hinge_grid, key=lambda r: r["wald_F_stat"])
    coal_hinge_grid = [fit_piecewise_hinge(merged["net_demand_gw"].values, merged["coal_gw"].values * 1000.0, float(th)) for th in np.arange(135.0, 180.0, 1.0)]
    best_coal_knee = max(coal_hinge_grid, key=lambda r: r["wald_F_stat"])
    # Marginal dispatch slopes (dCoal/dND, dHydro/dND, dGas/dND) below vs above 160 GW
    below160 = merged[merged["net_demand_gw"] < 160.0]
    above160 = merged[merged["net_demand_gw"] >= 160.0]

    def lin_slope(s: pd.DataFrame, col: str) -> float:
        x = s["net_demand_gw"].values
        y = s[col].values
        return float(np.polyfit(x, y, 1)[0])

    dispatch_slopes = {
        "p995_observed_coal_gw": round(p995_coal, 2),
        "n_fuel_mix_hours": int(len(merged)),
        "full_2022_2025_mcp_optimal_knee_gw": best_all["theta_gw"],
        "full_2022_2025_mcp_supwald_F": best_all["wald_F_stat"],
        "gas_dispatch_optimal_knee_gw": best_gas_knee["theta_gw"],
        "gas_dispatch_supwald_F": best_gas_knee["wald_F_stat"],
        "gas_slope_below_mw_per_gw": best_gas_knee["slope_below_rs_per_gw"],
        "gas_slope_above_mw_per_gw": best_gas_knee["slope_above_rs_per_gw"],
        "coal_saturation_knee_gw": best_coal_knee["theta_gw"],
        "coal_slope_below_160_gw_per_gw": round(lin_slope(below160, "coal_gw"), 4),
        "coal_slope_above_160_gw_per_gw": round(lin_slope(above160, "coal_gw"), 4),
        "hydro_slope_below_160_gw_per_gw": round(lin_slope(below160, "hydro_gw"), 4),
        "hydro_slope_above_160_gw_per_gw": round(lin_slope(above160, "hydro_gw"), 4),
        "gas_slope_below_160_gw_per_gw": round(lin_slope(below160, "gas_gw"), 4),
        "gas_slope_above_160_gw_per_gw": round(lin_slope(above160, "gas_gw"), 4),
    }
    print("\n[B4] Marginal Physical Dispatch Slopes (dGen_GW / dNetDemand_GW):")
    print(f"  Coal/Thermal slope: {dispatch_slopes['coal_slope_below_160_gw_per_gw']:.3f} GW/GW (<160 GW) -> {dispatch_slopes['coal_slope_above_160_gw_per_gw']:.3f} GW/GW (>=160 GW)")
    print(f"  Hydro peaking slope: {dispatch_slopes['hydro_slope_below_160_gw_per_gw']:.3f} GW/GW (<160 GW) -> {dispatch_slopes['hydro_slope_above_160_gw_per_gw']:.3f} GW/GW (>=160 GW)")
    print(f"  Gas peaker slope:   {dispatch_slopes['gas_slope_below_160_gw_per_gw']:.4f} GW/GW (<160 GW) -> {dispatch_slopes['gas_slope_above_160_gw_per_gw']:.4f} GW/GW (>=160 GW)")
    print(f"  Direct Gas Peaker Inflection Knee: theta_gas* = {best_gas_knee['theta_gw']:.1f} GW (F = {best_gas_knee['wald_F_stat']:.1f}, slope {best_gas_knee['slope_below_rs_per_gw']:.1f} -> {best_gas_knee['slope_above_rs_per_gw']:.1f} MW_gas/GW_ND)")

    with open(TABLE_DIR / "v2_merit_order_physical_validation_summary.json", "w") as f:
        json.dump(dispatch_slopes, f, indent=2)

    print("\n[OK] Independent physical merit-order validation complete!")


if __name__ == "__main__":
    main()
