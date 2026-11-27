"""
EnergyCast V1 — Step 14: Build Embedded Data Bundle & Step 14 Architecture Figures
===================================================================================
1. Exports `app/static/embedded_data.js` containing the complete 4,200-hour Test Set
   multi-model forecasts, physical telemetry, TreeSHAP global/local attributions,
   merit-order curve, and Diebold-Mariano matrices so that `app/static/index.html`
   operates seamlessly both via the live Python REST server (`uv run python app/main.py`)
   AND when opened directly via `file://` in any browser.
2. Generates publication-grade figures in `outputs/figures/app/` for the Step 14
   Technical Report Word Document.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.main import CATEGORY_MAPPING, FEATURE_LABELS, EnergyCastEngine

STATIC_DIR = PROJECT_ROOT / "app" / "static"
APP_FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "app"
APP_FIG_DIR.mkdir(parents=True, exist_ok=True)


def build_embedded_js(eng: EnergyCastEngine) -> None:
    print("[1/2] Building embedded_data.js for zero-latency hybrid server/standalone execution...")

    overview = eng.get_overview_payload()
    shap_lab = eng.get_shap_lab_payload()
    benchmarks = eng.get_benchmarks_payload()

    # Compact per-day dictionary for all 175 dates (4,200 hours)
    days_map = {}
    for date_str in eng.available_dates:
        days_map[date_str] = eng.get_day_forecast(date_str)

    # Pre-cache exact hour_explain for preset dates (all 24 hours of preset dates)
    preset_dates = {p["date"] for p in overview["presets"]}
    explain_cache = {}
    for d_str in preset_dates:
        for h in range(24):
            explain_cache[f"{d_str}_{h}"] = eng.get_hour_explanation(d_str, h)

    # Also store feature means & stds and Ridge/LightGBM local sensitivities for offline fallback
    bundle = {
        "overview": overview,
        "shapLab": shap_lab,
        "benchmarks": benchmarks,
        "daysMap": days_map,
        "explainCache": explain_cache,
    }

    js_path = STATIC_DIR / "embedded_data.js"
    js_content = "window.ENERGYCAST_EMBEDDED = " + json.dumps(bundle, separators=(",", ":"), ensure_ascii=False) + ";\n"
    js_path.write_text(js_content, encoding="utf-8")
    size_mb = js_path.stat().st_size / (1024 * 1024)
    print(f"  [SAVED] {js_path} ({size_mb:.2f} MB)")


def generate_step14_figures(eng: EnergyCastEngine) -> None:
    print("[2/2] Generating Step 14 technical report figures...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "figure.dpi": 220,
    })

    # FIGURE 1: Counterfactual Stress-Test Sensitivity Curves across 4 Macro Shocks (Jan 01, 2025)
    scenarios = [
        ("Baseline (Unperturbed)", {"delta_demand_mw": 0, "delta_solar_mw": 0, "delta_wind_mw": 0, "delta_temp_c": 0}),
        ("Solar Cloud Dropout (-8 GW Solar, +5 GW Ramp)", {"delta_demand_mw": 0, "delta_solar_mw": -8000, "delta_ramp_mw": 5000}),
        ("Summer Heatwave (+18 GW Demand, +4.5°C)", {"delta_demand_mw": 18000, "delta_temp_c": 4.5}),
        ("Monsoon Wind Surplus (+10 GW Wind, -4 GW Ramp)", {"delta_wind_mw": 10000, "delta_ramp_mw": -4000}),
    ]
    colors = ["#121417", "#D97706", "#D1341B", "#0B7A5E"]
    styles = ["-", "--", "-.", ":"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.8))

    hours = list(range(24))
    for (label, params), col, ls in zip(scenarios, colors, styles):
        preds_24 = []
        nd_24 = []
        for h in hours:
            req = {"date": "2025-03-16", "hour": h}
            req.update(params)
            res = eng.run_counterfactual_simulation(req)
            preds_24.append(res["predictions"]["lightgbm"]["simulated"])
            nd_24.append(res["grid_telemetry"]["simulated"]["net_demand_gw"])
        ax1.plot(hours, preds_24, label=label, color=col, linestyle=ls, linewidth=2.3, marker="o", markersize=3.5)
        ax2.plot(hours, nd_24, label=label, color=col, linestyle=ls, linewidth=2.2)

    ax1.axvspan(8.5, 16.5, color="#F59E0B", alpha=0.08, label="Solar Window")
    ax1.axvspan(17.5, 22.5, color="#D1341B", alpha=0.08, label="Evening Peak")
    ax1.set_title("(a) 24-Hour Simulated MCP Response Under Grid Shocks", fontweight="bold")
    ax1.set_xlabel("Delivery Hour (IST)", fontweight="bold")
    ax1.set_ylabel("Predicted Clearing Price (Rs/MWh)", fontweight="bold")
    ax1.set_xticks(range(0, 24, 3))
    ax1.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)])
    ax1.legend(loc="upper left", fontsize=8.5, frameon=True)

    ax2.set_title("(b) Coupled System Net Demand Trajectory (GW)", fontweight="bold")
    ax2.set_xlabel("Delivery Hour (IST)", fontweight="bold")
    ax2.set_ylabel("Net Demand = Gross Demand - Solar - Wind (GW)", fontweight="bold")
    ax2.set_xticks(range(0, 24, 3))
    ax2.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)])
    ax2.axhline(160, color="#D1341B", linestyle="--", linewidth=1.2, label="160 GW Peaker Inflection")
    ax2.legend(loc="upper left", fontsize=8.5, frameon=True)

    plt.suptitle("EnergyCast V1 — Real-Time Counterfactual Stress-Test Engine (March 16, 2025)", fontsize=13.5, fontweight="bold", y=1.01)
    plt.tight_layout()
    f1_path = APP_FIG_DIR / "fig_app01_counterfactual_shock_trajectories.png"
    plt.savefig(f1_path, dpi=240, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] {f1_path.name}")

    # FIGURE 2: Algorithmic Bidding Procurement Arbitrage (DISCOM Trough vs Generator Peak across 2025 Test Months)
    df_t = eng.test_df.copy()
    df_t["month_name"] = df_t["timestamp_dt"].dt.strftime("%b 2025")
    df_t["month_num"] = df_t["timestamp_dt"].dt.month

    monthly_stats = []
    for m_num, grp in df_t.groupby("month_num"):
        m_label = grp["month_name"].iloc[0]
        # Per-day cheapest 4h and most expensive 4h based on LightGBM forecast
        daily_mean = grp["mcp_rs_per_mwh"].mean()
        solar_window = grp[grp["hour"].between(10, 15)]["mcp_rs_per_mwh"].mean()
        peak_window = grp[grp["hour"].between(18, 22)]["mcp_rs_per_mwh"].mean()
        monthly_stats.append({
            "month": m_label,
            "Daily_Mean_MCP": daily_mean,
            "DISCOM_Solar_Trough_10_15h": solar_window,
            "Generator_Peak_Window_18_22h": peak_window,
            "Arbitrage_Spread": peak_window - solar_window,
        })
    df_m = pd.DataFrame(monthly_stats)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(df_m))
    w = 0.26
    b1 = ax.bar(x - w, df_m["DISCOM_Solar_Trough_10_15h"], width=w, color="#0B7A5E", edgecolor="black", label="Optimal DISCOM Buy Window (10:00–15:00)")
    b2 = ax.bar(x, df_m["Daily_Mean_MCP"], width=w, color="#64748B", edgecolor="black", label="24-Hour Flat Baseline Mean")
    b3 = ax.bar(x + w, df_m["Generator_Peak_Window_18_22h"], width=w, color="#D1341B", edgecolor="black", label="Optimal Generator Dispatch Window (18:00–22:00)")

    for bars in [b1, b2, b3]:
        for bar in bars:
            h_val = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h_val + 80, f"Rs {h_val:,.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(df_m["month"], fontweight="bold")
    ax.set_ylabel("Realized Clearing Price (Rs/MWh)", fontweight="bold")
    ax.set_ylim(0, max(df_m["Generator_Peak_Window_18_22h"]) * 1.18)
    ax.set_title("EnergyCast V1 — Economic Value of Algorithmic Dispatch & Procurement Scheduling (Jan–Jun 2025)", fontweight="bold", pad=12)
    ax.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    f2_path = APP_FIG_DIR / "fig_app02_economic_arbitrage_bidding_value.png"
    plt.savefig(f2_path, dpi=240, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] {f2_path.name}")


if __name__ == "__main__":
    engine = EnergyCastEngine()
    build_embedded_js(engine)
    generate_step14_figures(engine)

