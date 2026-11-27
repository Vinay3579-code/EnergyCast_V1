"""
EnergyCast V1 — Generate System Architecture Pipeline Diagram
Creates a clean, professional flowchart-style pipeline diagram using matplotlib.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def draw_architecture():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9.5)
    ax.axis('off')
    fig.patch.set_facecolor('#FAFBFD')

    # Color palette
    C_DATA = '#2E86AB'      # Steel blue
    C_PROCESS = '#1F4E79'   # Deep navy
    C_MODEL = '#27AE60'     # Green
    C_OUTPUT = '#E67E22'    # Gold
    C_DEPLOY = '#8E44AD'    # Purple
    C_ARROW = '#555555'
    C_TEXT = '#FFFFFF'
    C_TITLE_BG = '#1F4E79'

    def draw_box(x, y, w, h, label, sublabel, color, fontsize=9, sublabel_size=7):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                             facecolor=color, edgecolor='white', linewidth=2,
                             alpha=0.92, zorder=3)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2 + 0.12, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color=C_TEXT, zorder=4)
        if sublabel:
            ax.text(x + w/2, y + h/2 - 0.22, sublabel, ha='center', va='center',
                    fontsize=sublabel_size, color='#E0E0E0', zorder=4, style='italic')

    def draw_arrow(x1, y1, x2, y2, curved=False):
        style = "Simple,tail_width=2.5,head_width=10,head_length=6"
        if curved:
            arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle=style, color=C_ARROW, alpha=0.6,
                                     connectionstyle="arc3,rad=0.15", zorder=2)
        else:
            arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle=style, color=C_ARROW, alpha=0.6,
                                     zorder=2)
        ax.add_patch(arrow)

    # Title
    ax.text(7, 9.15, "EnergyCast V1 — System Architecture & Data Pipeline",
            ha='center', va='center', fontsize=16, fontweight='bold', color=C_PROCESS)
    ax.text(7, 8.8, "End-to-End Hourly Electricity Price Forecasting for Indian DAM",
            ha='center', va='center', fontsize=10, color='#666666', style='italic')

    # ===== ROW 1: Data Sources (y ~ 7.2) =====
    ax.text(7, 8.3, "DATA INGESTION LAYER", ha='center', fontsize=8,
            fontweight='bold', color='#999999')

    draw_box(0.3, 7.0, 3.5, 0.9, "IEX Market Data", "DAM MCP, Bids, Volumes (Hourly)", C_DATA)
    draw_box(5.25, 7.0, 3.5, 0.9, "Grid-India / POSOCO", "Demand, Solar, Wind, Thermal (Hourly)", C_DATA)
    draw_box(10.2, 7.0, 3.5, 0.9, "Open-Meteo Weather", "Temp, Humidity, Wind, Radiation", C_DATA)

    # Arrows: Data Sources -> Merge
    draw_arrow(2.05, 7.0, 5.0, 6.15)
    draw_arrow(7.0, 7.0, 7.0, 6.15)
    draw_arrow(11.95, 7.0, 9.0, 6.15)

    # ===== ROW 2: Preprocessing (y ~ 5.5) =====
    ax.text(7, 6.45, "PREPROCESSING & FUSION", ha='center', fontsize=8,
            fontweight='bold', color='#999999')

    draw_box(4.0, 5.3, 6.0, 0.9, "Data Cleaning, Merging & Alignment",
             "28,176 hourly records | IST timezone | Missing value imputation", C_PROCESS)

    draw_arrow(7.0, 5.3, 7.0, 4.65)

    # ===== ROW 3: Feature Engineering (y ~ 3.9) =====
    ax.text(7, 4.85, "FEATURE ENGINEERING & LEAKAGE PREVENTION", ha='center', fontsize=8,
            fontweight='bold', color='#999999')

    draw_box(1.0, 3.7, 3.6, 0.9, "Temporal Features",
             "Lags (1,2,24,48,168h), Rolling stats", C_PROCESS, fontsize=8.5)
    draw_box(5.2, 3.7, 3.6, 0.9, "Physical Features",
             "Net Demand, Ramps, Duck Curve", C_PROCESS, fontsize=8.5)
    draw_box(9.4, 3.7, 3.6, 0.9, "Calendar + Weather",
             "Fourier hour/day, Temp, Humidity", C_PROCESS, fontsize=8.5)

    # Arrows: Features -> Split
    draw_arrow(2.8, 3.7, 5.5, 3.05)
    draw_arrow(7.0, 3.7, 7.0, 3.05)
    draw_arrow(11.2, 3.7, 8.5, 3.05)

    # ===== ROW 4: Train/Val/Test Split (y ~ 2.3) =====
    ax.text(7, 3.22, "CHRONOLOGICAL SPLIT (NO DATA LEAKAGE)", ha='center', fontsize=8,
            fontweight='bold', color='#999999')

    draw_box(0.5, 2.1, 3.5, 0.8, "Train (2022-2023)", "15,192 hours | 53.9%", '#3498DB', fontsize=9)
    draw_box(5.25, 2.1, 3.5, 0.8, "Validation (2024)", "8,784 hours | 31.2%", '#E67E22', fontsize=9)
    draw_box(10.0, 2.1, 3.5, 0.8, "Test (2025)", "4,200 hours | 14.9%", '#E74C3C', fontsize=9)

    # Arrows: Splits -> Models
    draw_arrow(2.25, 2.1, 4.0, 1.45)
    draw_arrow(7.0, 2.1, 7.0, 1.45)
    draw_arrow(11.75, 2.1, 10.0, 1.45)

    # ===== ROW 5: Model Hierarchy (y ~ 0.6) =====
    ax.text(7, 1.62, "3-TIER MODEL HIERARCHY", ha='center', fontsize=8,
            fontweight='bold', color='#999999')

    draw_box(0.3, 0.3, 3.0, 0.9, "Tier 1: Seasonal Naive",
             "MAE: Rs 658 | R2: 0.78", '#95A5A6', fontsize=8.5, sublabel_size=6.5)
    draw_box(4.0, 0.3, 3.0, 0.9, "Tier 2: Ridge Regression",
             "MAE: Rs 545 | R2: 0.91", C_MODEL, fontsize=8.5, sublabel_size=6.5)
    draw_box(7.7, 0.3, 3.3, 0.9, "Tier 3: LightGBM / XGB",
             "MAE: Rs 433 | R2: 0.93 ★", '#27AE60', fontsize=8.5, sublabel_size=6.5)

    # Output box
    draw_box(11.5, 0.3, 2.2, 0.9, "Forecast Output",
             "Rs/MWh per hour", C_DEPLOY, fontsize=8.5, sublabel_size=6.5)

    # Arrow from champion to output
    draw_arrow(11.0, 0.75, 11.5, 0.75)

    # Legend boxes at bottom-right
    legend_items = [
        (C_DATA, "Data Source"),
        (C_PROCESS, "Processing"),
        (C_MODEL, "Model"),
        (C_DEPLOY, "Output"),
    ]

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "system_architecture_pipeline.png", dpi=250,
                bbox_inches='tight', facecolor='#FAFBFD')
    plt.close(fig)
    print(f"Architecture diagram saved to: {OUTPUT_DIR / 'system_architecture_pipeline.png'}")


if __name__ == "__main__":
    draw_architecture()
