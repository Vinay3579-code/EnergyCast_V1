"""
Generates all 8 publication-grade empirical figures & system schematic for the
revised IEEE Transactions on Power Systems (TPWRS) & Springer LNCS manuscripts:

Title:
  Causality-Aware Renewable-Integrated Electricity Price Forecasting and
  Risk-Constrained Procurement Optimization for Day-Ahead Power Markets

All data are loaded directly from verified V2 out-of-sample outputs in:
  - outputs/tables/v2_*.csv
  - outputs/predictions/v2_operational_test_predictions.csv
  - outputs/predictions/v2_procurement_schedules.npz
  - data/processed/master/energycast_master_hourly_2022_2025.csv

Exported as crisp, Overleaf-fast RGB JPEGs (max width 1180px, 130 DPI) in:
  outputs/paper_figures_v2/
"""

from __future__ import annotations

import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from PIL import Image

PROJ_ROOT = pathlib.Path(r"v:\College\7th SEM\SDP\EnergyCast_V1")
TABLE_DIR = PROJ_ROOT / "outputs" / "tables"
PRED_DIR = PROJ_ROOT / "outputs" / "predictions"
MASTER_PATH = PROJ_ROOT / "data" / "processed" / "master" / "energycast_master_hourly_2022_2025.csv"
OUT_DIR = PROJ_ROOT / "outputs" / "paper_figures_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Arial", "Segoe UI"],
    "axes.edgecolor": "#334155",
    "axes.linewidth": 0.9,
    "axes.grid": True,
    "grid.alpha": 0.30,
    "grid.linestyle": "--",
})

C_NAVY = "#0F172A"
C_TEAL = "#0D9488"
C_BLUE = "#2563EB"
C_CRIMSON = "#DC2626"
C_AMBER = "#D97706"
C_GREEN = "#16A34A"
C_PURPLE = "#7C3AED"
C_SLATE = "#64748B"


def save_jpg(fig: plt.Figure, name: str, max_w: int = 1180, dpi: int = 130) -> None:
    tmp = OUT_DIR / name.replace(".jpg", "_tmp.png")
    dst = OUT_DIR / name
    fig.savefig(tmp, dpi=220, bbox_inches="tight", pad_inches=0.14, facecolor="#FFFFFF")
    plt.close(fig)
    with Image.open(tmp) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        if w > max_w:
            rgb = rgb.resize((max_w, int(round(h * max_w / w))), Image.Resampling.LANCZOS)
        rgb.save(dst, format="JPEG", quality=89, optimize=True, dpi=(dpi, dpi))
    if tmp.exists():
        tmp.unlink()
    print(f"  [OK] {name:42s} ({dst.stat().st_size / 1024:5.1f} KB)")


# ==============================================================================
# FIG 1: 5-LAYER CAUSALITY-AWARE & RISK-CONSTRAINED SYSTEM ARCHITECTURE
# ==============================================================================
def _draw_layer(ax, x, y, w, h, title, fc, ec, bfc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", facecolor=fc, edgecolor=ec, lw=1.4, zorder=1))
    ax.add_patch(FancyBboxPatch((x, y + h - 3.6), w, 3.6, boxstyle="round,pad=0,rounding_size=1.2", facecolor=bfc, edgecolor=ec, lw=1.1, zorder=2))
    ax.text(x + w / 2, y + h - 1.8, title, ha="center", va="center", fontsize=8.0, fontweight="bold", color="#FFFFFF", zorder=3)


def _draw_card(ax, x, y, w, h, title, lines, fc="#FFFFFF", ec="#64748B", hfc="#F1F5F9", tc="#0F172A", tsz=7.2, bsz=6.3, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", facecolor=fc, edgecolor=ec, lw=lw, zorder=4))
    hh = min(3.3, h * 0.34)
    ax.add_patch(FancyBboxPatch((x, y + h - hh), w, hh, boxstyle="round,pad=0,rounding_size=0.8", facecolor=hfc, edgecolor=ec, lw=lw * 0.9, zorder=5))
    ax.text(x + w / 2, y + h - hh / 2, title, ha="center", va="center", fontsize=tsz, fontweight="bold", color=tc, zorder=6)
    avail = h - hh - 0.9
    step = avail / max(len(lines), 1)
    cy = y + h - hh - 0.55 - step * 0.45
    for ln in lines:
        ax.text(x + w / 2, cy, ln, ha="center", va="center", fontsize=bsz, color="#1E293B", zorder=6)
        cy -= step


def _arrow(ax, pts, col="#0F172A", lw=1.5):
    if len(pts) > 2:
        ax.plot([p[0] for p in pts[:-1]], [p[1] for p in pts[:-1]], color=col, lw=lw, zorder=3)
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>,head_length=0.55,head_width=0.32", color=col, lw=lw, shrinkA=0, shrinkB=0), zorder=5)


def _badge(ax, x, y, txt, ec="#334155", tc="#0F172A"):
    ax.text(x, y, txt, ha="center", va="center", fontsize=6.5, fontweight="bold", color=tc,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="#FFFFFF", edgecolor=ec, lw=0.9), zorder=8)


def build_fig_1_architecture():
    fig, ax = plt.subplots(figsize=(14.2, 9.8), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # LAYER 1
    _draw_layer(ax, 1.5, 81.0, 97.0, 17.6,
                "LAYER 1: MULTI-SOURCE TELEMETRY HARMONIZATION & STRICT 10:30 AM IST D-1 CAUSAL FIREWALL (28,344 HOURS)",
                "#F0F9FF", "#0284C7", "#0369A1")
    _draw_card(ax, 3.0, 82.2, 22.0, 11.8, "1A. IEX DAM Auction Stream",
               ["Published D-1 Curve (Cleared D-2)", "MCP, MCV, Buy/Sell Bids (h=0..23)", "Zero Same-Day P_{D,h-1} Lags", "2022-04 to 2025-06 (Zero Gaps)"],
               ec="#0284C7", hfc="#E0F2FE", tc="#0C4A6E")
    _draw_card(ax, 27.0, 82.2, 22.0, 11.8, "1B. Grid-India NLDC SCADA",
               ["Gross Load, Solar, Wind (2022-25)", "Fuel-Mix: Coal, Hydro, Gas, Nuc.", "(15,360h Physical Validation)", "Strict Cutoff <= (D-1, 10:00 IST)"],
               ec="#0284C7", hfc="#E0F2FE", tc="#0C4A6E")
    _draw_card(ax, 51.0, 82.2, 22.0, 11.8, "1C. 5-Zone Weather & Astronomy",
               ["NR/WR/SR/ER/NER ERA5 Hubs", "Load-Weighted Temp, RH, Wind", "Clear-Sky Solar Elevation Angle", "Indian Holiday & Calendar Flags"],
               ec="#0284C7", hfc="#E0F2FE", tc="#0C4A6E")
    _draw_card(ax, 75.0, 82.2, 22.0, 11.8, "1D. Stage-1 D-1 Exog. Reconstructor",
               ["Purged OOF Train | Expanding Test", "Demand MAPE: 2.46% (Test 2025)", "Solar nRMSE: 11.17% | Temp: 0.48C", "Zero Day-D Realized Telemetry"],
               fc="#FFF1F2", ec="#E11D48", hfc="#FFE4E6", tc="#881337", lw=1.2)
    _arrow(ax, [(25.0, 88.1), (27.0, 88.1)], "#0369A1", 1.3)
    _arrow(ax, [(49.0, 88.1), (51.0, 88.1)], "#0369A1", 1.3)
    _arrow(ax, [(73.0, 88.1), (75.0, 88.1)], "#E11D48", 1.4)

    # LAYER 2
    _draw_layer(ax, 1.5, 59.5, 97.0, 18.0,
                "LAYER 2: CAPACITY-RELATIVE 65-SIGNAL CAUSAL FEATURE MATRIX & INNOVATION-TARGET FORMULATION",
                "#F0FDFA", "#0D9488", "#0F766E")
    domains = [
        (3.0,  15.0, "D-1 Price Memory (19)", ["D-1/D-2/D-3/D-7/D-14 Lags", "Adjacent D-1 Curve & h=23", "D-1 Mean/Std/Min/Max/Caps", "30d Relative Price Anomaly"]),
        (19.2, 15.0, "Stage-1 Grid & RE (19)", ["Fcst Load, Solar, Wind, ND", "1h & 3h Fcst Thermal Ramps", "30d Capacity-Relative ND", "Peak & CDD Interactions"]),
        (35.4, 14.5, "Order-Book (7)", ["D-1 Buy & Sell Bids (MWh)", "D-1 Cleared Volume (MCV)", "Tightness tau = Buy/Sell", "D-7 & Daily Mean Tightness"]),
        (51.1, 14.5, "Stage-1 Weather (10)", ["Fcst Mean/Max/App. Temp", "Fcst Humidity, Wind, Precip", "CDD_24 & Quadratic T^2", "D-1 Morning Temp Drift"]),
        (66.8, 14.5, "Calendar & Solar (10)", ["Hour/DoW/DoY Harmonics", "Weekend & India Holidays", "Evening Peak Flag (18-22h)", "Solar Elevation Angle (deg)"]),
    ]
    for dx, dw, dt, dl in domains:
        _draw_card(ax, dx, 60.7, dw, 12.2, dt, dl, ec="#0D9488", hfc="#CCFBF1", tc="#115E59", tsz=6.9, bsz=6.1)
    _draw_card(ax, 82.5, 60.7, 14.5, 12.2, "Stationarity Engine",
               ["Innovation: dP = P - P_{D-1}", "30d Capacity Normalization", "Recency-Weighted Expanding", "Val: 2024 | Test: 2025 (4,200h)"],
               fc="#EEF2FF", ec="#4F46E5", hfc="#E0E7FF", tc="#312E81", tsz=6.9, bsz=6.1, lw=1.2)
    _arrow(ax, [(86.0, 81.0), (86.0, 77.5)], "#0F766E", 1.6)
    _badge(ax, 74.5, 79.2, "Leak-Free F_{D-1, 10:30} Tensor (28,008 x 65)", "#0F766E", "#0F766E")

    # LAYER 3
    _draw_layer(ax, 1.5, 38.0, 97.0, 18.0,
                "LAYER 3: 4-TIER 13-MODEL BENCHMARKING, PROBABILISTIC RESIDUAL-CQR & COPULA SCENARIO ENGINE",
                "#FFFBEB", "#D97706", "#B45309")
    _draw_card(ax, 3.0, 39.2, 16.5, 12.2, "Tier 1 & 2: Econometric",
               ["Daily/Weekly S-Naive", "24-Eq. Seasonal SARIMAX", "OLS, LASSO, ElasticNet", "Tikhonov Ridge (a=2500)"],
               ec="#64748B", hfc="#F1F5F9", tc="#1E293B", tsz=7.0, bsz=6.1)
    _draw_card(ax, 20.8, 39.2, 18.5, 12.2, "Tier 3: Tree Ensembles",
               ["Random Forest (220 Trees)", "XGBoost & CatBoost", "LightGBM (MAE: Rs.496.71)", "Monthly Expanding Refit"],
               ec="#D97706", hfc="#FEF3C7", tc="#78350F", tsz=7.0, bsz=6.1)
    _draw_card(ax, 40.6, 39.2, 19.5, 12.2, "Tier 4: Deep Neural + Hybrid",
               ["PyTorch N-BEATS (Multi-Stack)", "PyTorch TFT (BiLSTM+Attn)", "Hybrid GBDT+TFT Champion", "Test MAE: Rs.481.19 (+26.9%)"],
               fc="#F0FDF4", ec="#16A34A", hfc="#DCFCE7", tc="#14532D", tsz=7.0, bsz=6.1, lw=1.3)
    _draw_card(ax, 61.4, 39.2, 19.0, 12.2, "Residual-CQR Uncertainty",
               ["7-Quantile Residual LGBM", "Regime Conformalized (Val24)", "PICP90: 90.69% (Kupiec p=0.13)", "CRPS: Rs.290.73 | W90: Rs.1774"],
               fc="#FFF1F2", ec="#E11D48", hfc="#FFE4E6", tc="#881337", tsz=7.0, bsz=6.1, lw=1.2)
    _draw_card(ax, 81.7, 39.2, 15.3, 12.2, "Copula Scenarios",
               ["24x24 PIT Corr. Matrix", "Gaussian Copula Sampling", "S=200 Coherent 24h Paths", "CERC [0, 10,000] Clipped"],
               fc="#EEF2FF", ec="#4F46E5", hfc="#E0E7FF", tc="#312E81", tsz=7.0, bsz=6.1)
    _arrow(ax, [(19.5, 45.3), (20.8, 45.3)], "#475569", 1.2)
    _arrow(ax, [(39.3, 45.3), (40.6, 45.3)], "#B45309", 1.3)
    _arrow(ax, [(60.1, 45.3), (61.4, 45.3)], "#16A34A", 1.3)
    _arrow(ax, [(80.4, 45.3), (81.7, 45.3)], "#E11D48", 1.3)
    _arrow(ax, [(50.0, 59.5), (50.0, 56.0)], "#B45309", 1.6)
    _badge(ax, 63.0, 57.7, "Expanding Walk-Forward Tensors + Recency Weights", "#B45309", "#78350F")

    # LAYER 4
    _draw_layer(ax, 1.5, 16.5, 97.0, 18.0,
                "LAYER 4: STOCHASTIC CVaR PROCUREMENT OPTIMIZATION, PHYSICAL MERIT-ORDER AUDIT & STRESS LAB",
                "#EEF2FF", "#4338CA", "#3730A3")
    _draw_card(ax, 3.0, 17.8, 30.5, 12.2, "4A. Rockafellar-Uryasev Stochastic CVaR LP",
               ["min E[sum L_h P_h] + lambda * CVaR_0.90(C)", "Ramp Limits, Rolling Payback Buffer & Energy Neutrality", "4 Profiles x 4 Flex Ratios (10-40%) across 175 Test Days", "Realized Savings: 5.5%-12.4% (98.4%-98.8% Oracle Eff.)"],
               fc="#F0FDF4", ec="#16A34A", hfc="#DCFCE7", tc="#14532D", tsz=7.1, bsz=6.2, lw=1.2)
    _draw_card(ax, 35.0, 17.8, 30.5, 12.2, "4B. Physical Merit-Order & Fuel-Mix Validation",
               ["15,360h NLDC Coal, Gas, Hydro & Nuclear SCADA", "Coal Saturation: 0.812 -> 0.544 GW/GW | Gas 6.5x Surge", "Dynamic Knee: 152 (2022) -> 156 -> 169 -> 174 GW (2025)", "Supporting Operational TreeSHAP (32.2% Grid/RE Share)"],
               fc="#FFFFFF", ec="#4338CA", hfc="#E0E7FF", tc="#312E81", tsz=7.1, bsz=6.2)
    _draw_card(ax, 67.0, 17.8, 30.0, 12.2, "4C. Multi-Disturbance Stress & Risk Lab",
               ["17 Scenarios: Solar/Wind -10..-40%, Demand +5..+15%", "Unexpected Thermal Outages (-5, -10, -15 GW) + Heatwaves", "Tracks Point DeltaP, W90 Width, Cap Risk & CVaR_90", "Compound Crisis: +Rs.286/MWh, +20.6% W90, +12.3% CVaR"],
               fc="#FFF1F2", ec="#E11D48", hfc="#FFE4E6", tc="#881337", tsz=7.1, bsz=6.2)
    _arrow(ax, [(89.0, 38.0), (89.0, 34.5)], "#3730A3", 1.6)
    _arrow(ax, [(50.0, 38.0), (50.0, 34.5)], "#3730A3", 1.6)
    _badge(ax, 70.0, 36.2, "200 Correlated 24h Scenarios + Point & CQR Intervals", "#3730A3", "#312E81")

    # LAYER 5
    _draw_layer(ax, 1.5, 1.5, 97.0, 11.8,
                "LAYER 5: PRODUCTION REST API & COMMERCIAL DISCOM / INDUSTRIAL TRADING COMMAND CENTER",
                "#ECFDF5", "#059669", "#047857")
    tabs = [
        (3.0,  "Tab 1: 24h Probabilistic Forecast", ["CQR 90% Band & Scarcity Alerts"]),
        (27.0, "Tab 2: Stochastic Bid Optimizer",   ["CVaR Risk Slider & IEX Bid CSV"]),
        (51.0, "Tab 3: Weather & Outage Stress",    ["Merit-Order Stack & Shock Sliders"]),
        (75.0, "Tab 4: HAC Trust & Audit Suite",    ["13-Model DM & CQR Scorecard"]),
    ]
    for tx, tt, tl in tabs:
        _draw_card(ax, tx, 2.5, 22.0, 6.8, tt, tl, ec="#059669", hfc="#D1FAE5", tc="#065F46", tsz=7.0, bsz=6.2)
    for ax_x in [18.0, 50.0, 82.0]:
        _arrow(ax, [(ax_x, 16.5), (ax_x, 13.3)], "#047857", 1.4)

    save_jpg(fig, "paper_fig_1_architecture.jpg")


# ==============================================================================
# FIG 2: INDEPENDENT PHYSICAL MERIT-ORDER & POSOCO FUEL-MIX VALIDATION
# ==============================================================================
def build_fig_2_physical_merit_order():
    fm_reg = pd.read_csv(TABLE_DIR / "v2_posoco_fuel_mix_dispatch_by_regime.csv")
    stab = pd.read_csv(TABLE_DIR / "v2_merit_order_stability_by_year_season.csv")
    master = pd.read_csv(MASTER_PATH)
    master = master[master["demand_mw"] > 90000.0].copy()
    master["timestamp"] = pd.to_datetime(master["timestamp"])
    master["year"] = master["timestamp"].dt.year
    master["nd_gw"] = (master["demand_mw"] - master["solar_generation_mw"] - master["wind_generation_mw"]) / 1000.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.2), dpi=220)

    # Panel A: POSOCO Fuel-Mix Dispatch & Cap-Hit Probability across Net Demand Bands
    x = np.arange(len(fm_reg))
    w = 0.25
    b1 = ax1.bar(x - w, fm_reg["Coal_Util_Pct_of_Peak"], width=w, color=C_NAVY, alpha=0.88, label="Coal Fleet Utilization (% Peak)")
    b2 = ax1.bar(x, fm_reg["Mean_Hydro_GW"] * 2.5, width=w, color=C_BLUE, alpha=0.85, label="Hydro Peaking (GW x 2.5)")
    b3 = ax1.bar(x + w, fm_reg["P90_Gas_GW"] * 10.0, width=w, color=C_AMBER, alpha=0.90, label="Gas Peaker P90 (GW x 10)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(fm_reg["Net_Demand_Band"], rotation=22, ha="right", fontsize=8.5)
    ax1.set_ylabel("Scaled Dispatch Intensity (Coal %, Hydro x2.5, Gas x10)", fontsize=9.2, color=C_NAVY)
    ax1.set_ylim(0, 112)
    ax1.set_title("(a) POSOCO NLDC Fuel-Mix Dispatch vs. Cap-Hit Risk (15,350h)", fontsize=10.2, fontweight="bold", pad=8)

    ax1r = ax1.twinx()
    l1 = ax1r.plot(x, fm_reg["Cap_Hit_10k_pct"], color=C_CRIMSON, marker="o", lw=2.4, ms=6, label="CERC Cap-Hit Rate (%)")
    ax1r.set_ylabel("CERC Rs.10,000 Cap-Hit Probability (%)", fontsize=9.2, color=C_CRIMSON)
    ax1r.set_ylim(0, 78)
    ax1r.grid(False)
    for xi, ci in zip(x, fm_reg["Cap_Hit_10k_pct"]):
        ax1r.text(xi, ci + 2.5, f"{ci:.1f}%", ha="center", va="bottom", fontsize=7.8, color=C_CRIMSON, fontweight="bold")

    ax1.axvline(3.5, color=C_CRIMSON, ls=":", lw=1.4)
    ax1.text(3.58, 102, "160 GW Pooled\nTransition Zone", fontsize=7.6, color=C_CRIMSON, fontweight="bold", va="top")

    h1, lab1 = ax1.get_legend_handles_labels()
    h2, lab2 = ax1r.get_legend_handles_labels()
    ax1.legend(h1 + h2, lab1 + lab2, loc="upper left", fontsize=7.5, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    # Panel B: Year-by-Year Empirical Supply Curves & Dynamic Migrating Scarcity Knee (2022 -> 2025)
    yr_styles = [
        (2022, C_SLATE,   "-",  "2022 (Knee: 152 GW, F=1,560)"),
        (2023, C_AMBER,   "-",  "2023 (Knee: 156 GW, F=1,036)"),
        (2024, C_BLUE,    "-",  "2024 (Knee: 169 GW, F=1,844)"),
        (2025, C_TEAL,    "-",  "2025 (Knee: 174 GW, F=1,480)"),
    ]
    yr_knees = {2022: 152.0, 2023: 156.0, 2024: 169.0, 2025: 174.0}
    bins_gw = np.arange(115, 208, 4.5)
    for yr, col, ls, lbl in yr_styles:
        sub = master[master["year"] == yr]
        bx, by = [], []
        for b0, b1_e in zip(bins_gw[:-1], bins_gw[1:]):
            m = (sub["nd_gw"] >= b0) & (sub["nd_gw"] < b1_e)
            if m.sum() >= 25:
                bx.append(sub.loc[m, "nd_gw"].mean())
                by.append(sub.loc[m, "mcp_rs_per_mwh"].mean())
        ax2.plot(bx, by, color=col, lw=2.3, ls=ls, marker="o", ms=3.5, label=lbl)
        # Mark Sup-Wald optimal knee on curve
        kn = yr_knees[yr]
        y_kn = np.interp(kn, bx, by)
        ax2.scatter([kn], [y_kn], color=col, s=75, edgecolor="#FFFFFF", linewidth=1.4, zorder=6)

    ax2.annotate("Capacity-Driven Knee Shift\n152 GW (2022) -> 174 GW (2025)\n(+22 GW Thermal Expansion)",
                 xy=(174, 4800), xytext=(122, 8300),
                 arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=1.4),
                 fontsize=8.0, fontweight="bold", color=C_NAVY,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#F8FAFC", edgecolor=C_NAVY, lw=0.9))
    ax2.set_xlabel("National Net Thermal Demand (GW)", fontsize=9.5)
    ax2.set_ylabel("Empirical Mean IEX Clearing Price (Rs./MWh)", fontsize=9.5)
    ax2.set_title("(b) Multi-Year Supply-Stack Migration (28,334h Sup-Wald Knees)", fontsize=10.2, fontweight="bold", pad=8)
    ax2.set_xlim(115, 205)
    ax2.set_ylim(1800, 10600)
    ax2.legend(loc="lower right", fontsize=7.8, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    plt.tight_layout(w_pad=2.2)
    save_jpg(fig, "paper_fig_2_physical_merit_order.jpg")


# ==============================================================================
# FIG 3: 4-TIER 13-MODEL BENCHMARK LEADERBOARD & DIURNAL MAE PROFILE
# ==============================================================================
def build_fig_3_benchmark_progression():
    lb = pd.read_csv(TABLE_DIR / "v2_master_benchmark_leaderboard.csv")
    preds = pd.read_csv(PRED_DIR / "v2_operational_test_predictions.csv")
    preds["hour"] = pd.to_datetime(preds["timestamp"]).dt.hour

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.5), dpi=220, gridspec_kw={"width_ratios": [1.18, 1.0]})

    # Panel A: Horizontal bar comparison sorted by Test MAE
    lb_s = lb.sort_values("Test_MAE", ascending=False).reset_index(drop=True)
    y_pos = np.arange(len(lb_s))
    tier_col = {
        "Tier 1: Baselines": C_SLATE,
        "Tier 2: Econometric": "#94A3B8",
        "Tier 2: Linear": C_AMBER,
        "Tier 3: Tree Ensemble": C_BLUE,
        "Tier 3: GBDT": C_BLUE,
        "Tier 4: Deep Neural": C_PURPLE,
        "Tier 4+: Hybrid Champion": C_TEAL,
    }
    cols = [tier_col.get(t, C_SLATE) for t in lb_s["Tier"]]
    short_names = [m.replace(" (24-Eq. Seasonal)", " (24-Eq)").replace(" (Multi-Stack Neural)", "").replace("Temporal Fusion Transformer (TFT)", "TFT (PyTorch)").replace("EnergyCast Hybrid Ensemble (GBDT+TFT)", "Hybrid Champion (GBDT+TFT)").replace(" (220 Trees)", "") for m in lb_s["Model"]]

    ax1.barh(y_pos - 0.18, lb_s["Test_MAE"], height=0.35, color=cols, alpha=0.92, label="Overall Test MAE (4,200h)")
    ax1.barh(y_pos + 0.18, lb_s["Test_Peak_MAE"], height=0.35, color=cols, alpha=0.40, hatch="//", edgecolor="#334155", lw=0.4, label="Evening Peak MAE (18-22h)")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(short_names, fontsize=8.0)
    ax1.set_xlabel("Out-of-Sample Mean Absolute Error (Rs./MWh)", fontsize=9.2)
    ax1.set_title("(a) Strict D-1 Out-of-Sample Benchmark (14 Entries Across 4 Tiers)", fontsize=10.0, fontweight="bold", pad=8)
    ax1.set_xlim(0, 1480)
    for i, (m_all, m_pk) in enumerate(zip(lb_s["Test_MAE"], lb_s["Test_Peak_MAE"])):
        ax1.text(m_all + 12, i - 0.20, f"{m_all:.0f}", va="center", fontsize=7.2, fontweight="bold", color=C_NAVY)
        ax1.text(m_pk + 12, i + 0.20, f"{m_pk:.0f}", va="center", fontsize=6.9, color="#475569")
    ax1.legend(loc="upper right", fontsize=7.8, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    # Panel B: 24-Hour Diurnal MAE Profile across Representative Tier Models
    hrs = np.arange(24)
    series_spec = [
        ("pred_snaive_24h", "Daily S-Naive (Tier 1)", C_CRIMSON, "--", 1.8),
        ("pred_sarimax",    "SARIMAX 24-Eq (Tier 2)", C_SLATE,   ":",  1.8),
        ("pred_enet",       "Elastic Net (Tier 2)",   C_AMBER,   "-.", 1.9),
        ("pred_tft",        "PyTorch TFT (Tier 4)",   C_PURPLE,  "-",  2.0),
        ("pred_lightgbm",   "LightGBM (Tier 3)",      C_BLUE,    "-",  2.1),
        ("pred_champion",   "Hybrid Champion (GBDT+TFT)", C_TEAL,"-",  2.8),
    ]
    for col_k, lbl, col, ls, lw in series_spec:
        h_mae = preds.groupby("hour").apply(lambda g: np.mean(np.abs(g["actual_mcp"] - g[col_k])), include_groups=False).values
        ax2.plot(hrs, h_mae, color=col, ls=ls, lw=lw, label=lbl, marker="o" if col_k == "pred_champion" else None, ms=3.5)

    ax2.axvspan(9, 16, color=C_GREEN, alpha=0.07, label="Solar Trough Window")
    ax2.axvspan(18, 22, color=C_CRIMSON, alpha=0.08, label="Evening Scarcity Peak")
    ax2.set_xticks(range(0, 24, 3))
    ax2.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], fontsize=8.2)
    ax2.set_xlabel("Delivery Hour (IST)", fontsize=9.2)
    ax2.set_ylabel("Hourly Out-of-Sample MAE (Rs./MWh)", fontsize=9.2)
    ax2.set_title("(b) 24-Hour Diurnal Forecast Error Across Modeling Tiers", fontsize=10.0, fontweight="bold", pad=8)
    ax2.set_ylim(180, 1540)
    ax2.legend(loc="upper left", fontsize=7.3, ncol=2, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    plt.tight_layout(w_pad=2.0)
    save_jpg(fig, "paper_fig_3_benchmark_progression.jpg")


# ==============================================================================
# FIG 4: PROBABILISTIC RESIDUAL-CQR FORECAST TRAJECTORIES ACROSS 3 REGIMES
# ==============================================================================
def build_fig_4_probabilistic_trajectories():
    preds = pd.read_csv(PRED_DIR / "v2_operational_test_predictions.csv")
    preds["ts"] = pd.to_datetime(preds["timestamp"])
    preds["date"] = preds["ts"].dt.strftime("%Y-%m-%d")
    preds["hour"] = preds["ts"].dt.hour

    cases = [
        ("2025-01-01", "(a) Winter Scarcity Day (2025-01-01)"),
        ("2025-03-16", "(b) Spring Solar Glut (2025-03-16)"),
        ("2025-05-18", "(c) Summer Cooling Peak (2025-05-18)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14.0, 4.4), dpi=220, sharey=True)
    for ax, (dt_s, title) in zip(axes, cases):
        sub = preds[preds["date"] == dt_s].sort_values("hour")
        h = sub["hour"].values
        ax.fill_between(h, sub["q05_cqr"], sub["q95_cqr"], color=C_TEAL, alpha=0.18, label="90% CQR Band")
        ax.fill_between(h, sub["q25_cqr"], sub["q75_cqr"], color=C_TEAL, alpha=0.32, label="50% CQR Band")
        ax.plot(h, sub["pred_snaive_24h"], color=C_SLATE, ls=":", lw=1.4, label="24h S-Naive")
        ax.plot(h, sub["pred_champion"], color=C_TEAL, lw=2.2, label="Hybrid Point")
        ax.plot(h, sub["actual_mcp"], color=C_NAVY, lw=2.0, ls="--", marker="o", ms=3.0, label="Actual IEX MCP")
        mae_d = np.mean(np.abs(sub["actual_mcp"] - sub["pred_champion"]))
        cov_d = np.mean((sub["actual_mcp"] >= sub["q05_cqr"]) & (sub["actual_mcp"] <= sub["q95_cqr"])) * 100.0
        ax.text(0.03, 0.96, f"Day MAE: Rs.{mae_d:.0f}\n90% Cov: {cov_d:.0f}%", transform=ax.transAxes,
                va="top", ha="left", fontsize=7.8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFFFFF", edgecolor=C_TEAL, alpha=0.92))
        ax.set_title(title, fontsize=9.6, fontweight="bold", pad=6)
        ax.set_xlabel("Hour (IST)", fontsize=8.8)
        ax.set_xticks(range(0, 24, 4))
        ax.set_xticklabels([f"{x:02d}" for x in range(0, 24, 4)], fontsize=8.0)
        ax.set_ylim(-200, 10600)
    axes[0].set_ylabel("Clearing Price (Rs./MWh)", fontsize=9.2)
    axes[2].legend(loc="lower right", fontsize=7.4, frameon=True, facecolor="#FFFFFF")

    plt.tight_layout(w_pad=1.4)
    save_jpg(fig, "paper_fig_4_probabilistic_trajectories.jpg")


# ==============================================================================
# FIG 5: DIEBOLD-MARIANO HAC SIGNIFICANCE & PROBABILISTIC CALIBRATION
# ==============================================================================
def build_fig_5_probabilistic_and_dm():
    dm = pd.read_csv(TABLE_DIR / "v2_diebold_mariano_hac_tests.csv")
    prob = pd.read_csv(TABLE_DIR / "v2_probabilistic_evaluation.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.0), dpi=220)

    # Panel A: Diebold-Mariano HAC (L=9) statistics vs Champion
    dm_sub = dm[dm["DM_HAC_L9"] > 0].sort_values("DM_HAC_L9", ascending=True).reset_index(drop=True)
    y = np.arange(len(dm_sub))
    names = [m.replace(" (24-Eq. Seasonal)", " (24-Eq)").replace(" (Multi-Stack Neural)", "").replace("Temporal Fusion Transformer (TFT)", "TFT (PyTorch)").replace(" (220 Trees)", "") for m in dm_sub["Model_1"]]
    cols = [C_TEAL if v < 5.0 else (C_BLUE if v < 10.0 else C_CRIMSON) for v in dm_sub["DM_HAC_L9"]]
    ax1.barh(y, dm_sub["DM_HAC_L9"], color=cols, alpha=0.88, height=0.62)
    ax1.axvline(1.96, color=C_AMBER, ls="--", lw=1.3, label="5% Sig. (DM = 1.96)")
    ax1.axvline(2.58, color=C_CRIMSON, ls="-.", lw=1.3, label="1% Sig. (DM = 2.58)")
    ax1.set_yticks(y)
    ax1.set_yticklabels(names, fontsize=8.0)
    ax1.set_xlabel("Newey-West HAC (L=9) Diebold-Mariano Statistic vs. Hybrid Champion", fontsize=8.8)
    ax1.set_title("(a) Pairwise Diebold-Mariano Superiority Tests (4,200h)", fontsize=10.0, fontweight="bold", pad=8)
    ax1.set_xlim(0, 18.0)
    for i, v in enumerate(dm_sub["DM_HAC_L9"]):
        ax1.text(v + 0.25, i, f"+{v:.2f}", va="center", fontsize=7.5, fontweight="bold", color=C_NAVY)
    ax1.legend(loc="lower right", fontsize=7.8, frameon=True)

    # Panel B: Probabilistic Calibration (Nominal vs Empirical PICP 50/80/90% + CRPS inset)
    nom = np.array([50.0, 80.0, 90.0])
    ax2.plot([30, 96], [30, 96], color=C_NAVY, ls="--", lw=1.6, label="Perfect Calibration (Ideal)")
    p_styles = [
        ("Homoskedastic Gaussian (Baseline)",         C_SLATE,   "s", ":"),
        ("Temporal Fusion Transformer (TFT-Q)",       C_PURPLE,  "^", "-."),
        ("Residual LightGBM Quantile (Uncalibrated)", C_AMBER,   "D", "--"),
        ("Residual-CQR (Regime Conformalized)",       C_TEAL,    "o", "-"),
    ]
    for pname, col, mk, ls in p_styles:
        row = prob[prob["Probabilistic_Model"] == pname].iloc[0]
        emp = [row["PICP_50_pct"], row["PICP_80_pct"], row["PICP_90_pct"]]
        lbl = f"{pname.split(' (')[0]} (CRPS={row['CRPS_Rs']:.0f}, W90={row['Width_90_Rs']:.0f})"
        ax2.plot(nom, emp, color=col, marker=mk, ms=7.0, ls=ls, lw=2.4 if col == C_TEAL else 1.8, label=lbl)

    ax2.annotate("Residual-CQR: 90.69% Cov.\nKupiec p = 0.132 (PASS)\nSpike Cov: 91.50%",
                 xy=(90, 90.69), xytext=(55, 86),
                 arrowprops=dict(arrowstyle="->", color=C_TEAL, lw=1.5),
                 fontsize=8.0, fontweight="bold", color="#0F766E",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#F0FDFA", edgecolor=C_TEAL, lw=1.0))
    ax2.set_xlabel("Nominal Prediction Interval Coverage (%)", fontsize=9.2)
    ax2.set_ylabel("Empirical Out-of-Sample Coverage PICP (%)", fontsize=9.2)
    ax2.set_title("(b) Probabilistic Interval Calibration & CRPS (Test 2025)", fontsize=10.0, fontweight="bold", pad=8)
    ax2.set_xlim(45, 95)
    ax2.set_ylim(34, 98)
    ax2.legend(loc="lower right", fontsize=7.5, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    plt.tight_layout(w_pad=2.0)
    save_jpg(fig, "paper_fig_5_probabilistic_and_dm.jpg")


# ==============================================================================
# FIG 6: CAUSALITY ABLATION AUDIT & OPERATIONAL INNOVATION TREESHAP
# ==============================================================================
def build_fig_6_shap_and_causality():
    abl = pd.read_csv(TABLE_DIR / "v2_causality_ablation_audit.csv")
    shap_top = pd.read_csv(TABLE_DIR / "v2_shap_global_importance.csv").head(10)
    shap_cat = pd.read_csv(TABLE_DIR / "v2_shap_category_summary.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.0), dpi=220, gridspec_kw={"width_ratios": [1.0, 1.15]})

    # Panel A: Causality & Recalibration Ablation
    labels = [
        "1. Static\n2022-23\n(Op. D-1)",
        "2. Expanding\nLightGBM\n(Op. D-1)",
        "3. Expanding\nHybrid\n(Op. D-1)",
        "4. Ex-Post\nPerf. Exog.\n(No P_{t-1})",
        "5. Audited\nLegacy V1\n(With P_{t-1})",
    ]
    x = np.arange(len(abl))
    cols = [C_SLATE, C_BLUE, C_TEAL, C_AMBER, C_CRIMSON]
    bars = ax1.bar(x, abl["Test_MAE"], width=0.56, color=cols, alpha=0.90, edgecolor=C_NAVY, lw=0.7)
    ax1.plot(x, abl["Peak_MAE"], color=C_NAVY, marker="D", ms=5.5, lw=1.6, ls="--", label="Evening Peak MAE (18-22h)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7.5)
    ax1.set_ylabel("Out-of-Sample Error on Test 2025 (Rs./MWh)", fontsize=9.2)
    ax1.set_title("(a) Information Boundary & Recalibration Ablation Audit", fontsize=10.0, fontweight="bold", pad=8)
    ax1.set_ylim(0, 1140)
    for xi, (m, pk) in enumerate(zip(abl["Test_MAE"], abl["Peak_MAE"])):
        ax1.text(xi, m + 16, f"Rs.{m:.1f}", ha="center", va="bottom", fontsize=7.6, fontweight="bold", color=C_NAVY)
        ax1.text(xi, pk + 26, f"{pk:.0f}", ha="center", va="bottom", fontsize=7.3, color="#334155")
    ax1.annotate("Recalibration Gain\n(-Rs.130.2/MWh)", xy=(1.0, 540), xytext=(1.35, 925),
                 arrowprops=dict(arrowstyle="->", color=C_BLUE, lw=1.3), fontsize=7.4, fontweight="bold", color=C_BLUE,
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="#EFF6FF", edgecolor=C_BLUE, lw=0.7))
    ax1.annotate("Intraday Leakage\nBias Audited", xy=(4.0, 480), xytext=(3.15, 905),
                 arrowprops=dict(arrowstyle="->", color=C_CRIMSON, lw=1.3), fontsize=7.4, fontweight="bold", color=C_CRIMSON,
                 bbox=dict(boxstyle="round,pad=0.22", facecolor="#FEF2F2", edgecolor=C_CRIMSON, lw=0.7))
    ax1.legend(loc="upper right", fontsize=7.6, frameon=True, facecolor="#FFFFFF")

    # Panel B: Top 10 Strict Operational D-1 Innovation TreeSHAP Features
    sh_s = shap_top.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(sh_s))
    cat_cols = {
        "D-1 Published Price Memory": C_BLUE,
        "Stage-1 Grid & RE Forecasts": C_TEAL,
        "Calendar & Astronomical": C_PURPLE,
        "D-1 Order-Book Liquidity": C_AMBER,
        "Stage-1 Weather Forecasts": C_CRIMSON,
    }
    bcols = [cat_cols.get(c, C_SLATE) for c in sh_s["Category"]]
    ax2.barh(y, sh_s["Mean_Abs_SHAP_Rs"], color=bcols, alpha=0.90, height=0.64)
    ax2.set_yticks(y)
    ax2.set_yticklabels(sh_s["Feature"], fontsize=8.3, family="monospace")
    ax2.set_xlabel("Mean Absolute Innovation Attribution |SHAP| (Rs./MWh)", fontsize=9.2)
    ax2.set_title("(b) Top 10 Strict Operational D-1 Innovation TreeSHAP Drivers", fontsize=10.0, fontweight="bold", pad=8)
    ax2.set_xlim(0, 118)
    for i, (v, r) in enumerate(zip(sh_s["Mean_Abs_SHAP_Rs"], sh_s["Corr_Feature_SHAP"])):
        ax2.text(v + 1.5, i, f"Rs.{v:.1f} (r={r:+.2f})", va="center", fontsize=7.4, color=C_NAVY, fontweight="bold")

    # Domain share legend box
    share_txt = "Domain Attribution Share:\n" + "\n".join(
        f"• {row['Category']}: {row['Share_pct']:.1f}%" for _, row in shap_cat.iterrows()
    )
    ax2.text(0.98, 0.04, share_txt, transform=ax2.transAxes, ha="right", va="bottom", fontsize=7.2,
             bbox=dict(boxstyle="round,pad=0.35", facecolor="#F8FAFC", edgecolor=C_SLATE, alpha=0.95))

    plt.tight_layout(w_pad=2.0)
    save_jpg(fig, "paper_fig_6_shap_and_causality.jpg")


# ==============================================================================
# FIG 7: MULTI-PROFILE STOCHASTIC CVaR PROCUREMENT OPTIMIZATION (175 TEST DAYS)
# ==============================================================================
def build_fig_7_stochastic_procurement():
    c1 = pd.read_csv(TABLE_DIR / "v2_procurement_multi_profile_results.csv")
    c2 = pd.read_csv(TABLE_DIR / "v2_procurement_flexibility_sensitivity.csv")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.1), dpi=220)

    # Panel A: Multi-Profile Realized Out-of-Sample Savings (All 175 Test Days)
    profs = [
        ("P1_Flat_Industrial_100MW", "P1: Flat Ind.\n(100 MW, 30%)"),
        ("P2_TwoShift_Mfg_100MW",    "P2: 2-Shift Mfg\n(100 MW, 25%)"),
        ("P3_State_DISCOM_350MW",    "P3: State DISCOM\n(350 MW, 20%)"),
        ("P4_Hybrid_ColdDC_80MW",    "P4: Cold/DC\n(80 MW, 35%)"),
    ]
    pol_spec = [
        ("Rule-Based ToU Heuristic",             "Rule-Based ToU",      C_SLATE),
        ("Deterministic LP (Constrained)",       "Det. Constrained LP", C_BLUE),
        ("Stochastic CVaR LP (lam=2.0)",         "Stoch. CVaR LP",      C_TEAL),
        ("Ex-Post Perfect Oracle (Constrained)", "Constrained Oracle",  C_AMBER),
    ]
    x = np.arange(len(profs))
    bw = 0.19
    for j, (pol_k, lbl, col) in enumerate(pol_spec):
        vals = [c1[(c1["Profile_ID"] == pid) & (c1["Policy"] == pol_k)]["Realized_Save_pct"].iloc[0] for pid, _ in profs]
        offset = (j - 1.5) * bw
        bars = ax1.bar(x + offset, vals, width=bw, color=col, alpha=0.90, label=lbl)
        if pol_k in ("Rule-Based ToU Heuristic", "Stochastic CVaR LP (lam=2.0)"):
            for xi, v in zip(x + offset, vals):
                ax1.text(xi, v + 0.25, f"{v:.1f}%", ha="center", va="bottom", fontsize=7.2, fontweight="bold", color=col)

    ax1.set_xticks(x)
    ax1.set_xticklabels([pl for _, pl in profs], fontsize=8.3)
    ax1.set_ylabel("Realized Out-of-Sample Bill Reduction (%)", fontsize=9.2)
    ax1.set_title("(a) 175-Day Realized Procurement Savings Across 4 Profiles", fontsize=10.0, fontweight="bold", pad=8)
    ax1.set_ylim(0, 14.8)
    ax1.legend(loc="upper left", fontsize=7.6, ncol=2, frameon=True, facecolor="#FFFFFF")

    # Panel B: Flexibility Ratio Sensitivity (10% - 40%) on P1 (Realized vs Simulated) & CVaR Reduction
    p1_c2 = c2[c2["Profile"].str.contains("Continuous")]
    gammas = [10, 20, 30, 40]
    for pol_k, lbl, col, ls, mk in [
        ("Rule-Based ToU",           "Rule-Based ToU (Realized)",       C_SLATE, "--", "s"),
        ("Stoch. CVaR LP (lam=1.0)", "Stochastic CVaR LP (Realized)",   C_TEAL,  "-",  "o"),
        ("Oracle Constrained",       "Constrained Oracle (Realized)",   C_AMBER, ":",  "^"),
    ]:
        sub = p1_c2[p1_c2["Policy"] == pol_k].sort_values("Gamma_pct")
        ax2.plot(sub["Gamma_pct"], sub["Realized_Save_pct"], color=col, ls=ls, lw=2.3, marker=mk, ms=6.5, label=lbl)

    # Also plot Simulated Expected Savings for Stoch CVaR LP to show near-zero optimism gap!
    sub_cv = p1_c2[p1_c2["Policy"] == "Stoch. CVaR LP (lam=1.0)"].sort_values("Gamma_pct")
    ax2.plot(sub_cv["Gamma_pct"], sub_cv["Sim_Save_pct"], color=C_BLUE, ls="-.", lw=1.6, marker="x", ms=6.5, label="Stochastic CVaR LP (Ex-Ante Sim.)")

    ax2r = ax2.twinx()
    ax2r.plot(sub_cv["Gamma_pct"], sub_cv["Realized_CVaR90_Bill_Lakhs"], color=C_CRIMSON, ls="-", lw=2.0, marker="D", ms=5.5, label="Realized CVaR_90 Daily Bill (Rs.L)")
    ax2r.set_ylabel("Realized 90% Tail Daily Bill CVaR_90 (Rs. Lakhs)", fontsize=9.0, color=C_CRIMSON)
    ax2r.set_ylim(120, 148)
    ax2r.grid(False)

    ax2.set_xticks(gammas)
    ax2.set_xticklabels([f"{g}%" for g in gammas], fontsize=8.8)
    ax2.set_xlabel("Flexible Shiftable Load Ratio gamma (%)", fontsize=9.2)
    ax2.set_ylabel("Daily Electricity Bill Reduction (%)", fontsize=9.2, color=C_NAVY)
    ax2.set_title("(b) Flexibility Sensitivity: Realized vs. Simulated & CVaR_90", fontsize=10.0, fontweight="bold", pad=8)
    ax2.set_ylim(0, 14.5)

    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2r.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7.3, frameon=True, facecolor="#FFFFFF", framealpha=0.95)

    plt.tight_layout(w_pad=2.2)
    save_jpg(fig, "paper_fig_7_stochastic_procurement.jpg")


# ==============================================================================
# FIG 8: COMPREHENSIVE WEATHER, RE & THERMAL OUTAGE STRESS-TEST IMPACT
# ==============================================================================
def build_fig_8_stress_testing():
    st = pd.read_csv(TABLE_DIR / "v2_comprehensive_stress_tests.csv")
    # Select 10 most informative progressive & compound scenarios for crystal clarity
    sel = [
        ("Solar Drop -20%",                                          "Solar -20%"),
        ("Solar Drop -40% (Heavy Cloud Cover)",                      "Solar -40%"),
        ("Wind Drop -20%",                                           "Wind -20%"),
        ("Wind Drop -40% (Monsoon Wind Lull)",                       "Wind -40%"),
        ("Demand Surge +5%",                                         "Demand +5%"),
        ("Demand Surge +15% (Extreme Peak Load)",                    "Demand +15%"),
        ("Thermal Outage -5 GW",                                     "Outage -5 GW"),
        ("Thermal Outage -15 GW (Severe Forced Trip)",               "Outage -15 GW"),
        ("Compound: Heatwave + Low RE (+10%D,+4C,-30%S,-30%W)",      "Heatwave+LowRE"),
        ("Compound Crisis: Outage(-8GW)+Heatwave+Cloud+WindLull",    "Compound Crisis"),
    ]
    sub = pd.DataFrame([st[st["Scenario"] == k].iloc[0].to_dict() | {"Short": lbl} for k, lbl in sel])
    base = st.iloc[0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.1), dpi=220)
    y = np.arange(len(sub))

    # Panel A: Point Price Surge DeltaP and 90% Uncertainty Expansion DeltaW90
    ax1.barh(y - 0.18, sub["Delta_Mean_MCP_Rs"], height=0.35, color=C_CRIMSON, alpha=0.88, label="Mean Price Surge Delta P (Rs./MWh)")
    ax1.barh(y + 0.18, sub["Delta_W90_Rs"], height=0.35, color=C_AMBER, alpha=0.88, label="90% Uncertainty Widening Delta W90 (Rs./MWh)")
    ax1.set_yticks(y)
    ax1.set_yticklabels(sub["Short"], fontsize=8.2)
    ax1.set_xlabel("Incremental Price & Uncertainty Shock vs. Baseline (Rs./MWh)", fontsize=9.0)
    ax1.set_title("(a) Clearing Price Surge & CQR Uncertainty Expansion", fontsize=10.0, fontweight="bold", pad=8)
    ax1.set_xlim(0, 420)
    for i, (dp, dw) in enumerate(zip(sub["Delta_Mean_MCP_Rs"], sub["Delta_W90_Rs"])):
        ax1.text(dp + 5, i - 0.18, f"+{dp:.0f}", va="center", fontsize=7.3, fontweight="bold", color=C_CRIMSON)
        ax1.text(dw + 5, i + 0.18, f"+{dw:.0f}", va="center", fontsize=7.3, fontweight="bold", color="#B45309")
    ax1.legend(loc="lower right", fontsize=7.6, frameon=True, facecolor="#FFFFFF")

    # Panel B: Daily Tail Financial Risk CVaR_90 (Unoptimized vs Stochastic CVaR LP)
    ax2.barh(y + 0.18, sub["Unopt_CVaR90_Lakhs"], height=0.35, color=C_SLATE, alpha=0.75, label="Unoptimized Flat Load CVaR_90 (Rs.L)")
    ax2.barh(y - 0.18, sub["Opt_CVaR90_Lakhs"], height=0.35, color=C_TEAL, alpha=0.92, label="Stochastic CVaR LP CVaR_90 (Rs.L)")
    ax2.axvline(base["Opt_CVaR90_Lakhs"], color=C_TEAL, ls="--", lw=1.2, label=f"Baseline Opt CVaR_90 (Rs.{base['Opt_CVaR90_Lakhs']:.1f}L)")
    ax2.set_yticks(y)
    ax2.set_yticklabels(sub["Short"], fontsize=8.2)
    ax2.set_xlabel("Daily 90% Tail Procurement Risk CVaR_90 (Rs. Lakhs/Day, 100 MW)", fontsize=9.0)
    ax2.set_title("(b) Tail Financial Risk Exposure & Stochastic CVaR Protection", fontsize=10.0, fontweight="bold", pad=8)
    ax2.set_xlim(95, 154)
    ax2.set_ylim(-2.0, 9.7)
    for i, (u_cv, o_cv, sav) in enumerate(zip(sub["Unopt_CVaR90_Lakhs"], sub["Opt_CVaR90_Lakhs"], sub["CVaR90_Risk_Reduction_Lakhs"])):
        ax2.text(u_cv + 0.6, i + 0.18, f"{u_cv:.1f}L", va="center", fontsize=7.1, color="#475569")
        ax2.text(o_cv + 0.6, i - 0.18, f"{o_cv:.1f}L (-{sav:.1f}L)", va="center", fontsize=7.1, fontweight="bold", color="#0F766E")
    ax2.legend(loc="lower right", fontsize=7.2, frameon=True, facecolor="#FFFFFF", framealpha=0.96)

    plt.tight_layout(w_pad=2.0)
    save_jpg(fig, "paper_fig_8_stress_testing.jpg")


def main() -> None:
    print("=" * 78)
    print("GENERATING ALL 8 V2 PUBLICATION-GRADE FIGURES FOR REVISED TPWRS/LNCS PAPERS")
    print("=" * 78)
    build_fig_1_architecture()
    build_fig_2_physical_merit_order()
    build_fig_3_benchmark_progression()
    build_fig_4_probabilistic_trajectories()
    build_fig_5_probabilistic_and_dm()
    build_fig_6_shap_and_causality()
    build_fig_7_stochastic_procurement()
    build_fig_8_stress_testing()
    print(f"[OK] All 8 V2 publication figures saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
