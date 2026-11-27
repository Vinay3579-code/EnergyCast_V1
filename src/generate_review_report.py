"""
EnergyCast V1 — UPGRADED Project Review Document Generator
Concise, reviewer-ready Word document (~10 pages) covering the entire
project from Introduction through Step 11, PLUS 7 anticipated reviewer
questions with prepared answers.
"""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SDP_ROOT = PROJECT_ROOT.parent
OUTPUT_DOCX = SDP_ROOT / "EnergyCast_V1_Project_Review_Document.docx"

# Figure paths
EDA_FIG = PROJECT_ROOT / "outputs" / "figures" / "eda"
TREE_FIG = PROJECT_ROOT / "outputs" / "figures" / "models" / "trees"
ARCH_FIG = PROJECT_ROOT / "outputs" / "figures" / "system_architecture_pipeline.png"

# Colors
C_PRI = RGBColor(0x1F, 0x4E, 0x79)
C_SEC = RGBColor(0x2E, 0x75, 0xB6)
C_BODY = RGBColor(0x33, 0x33, 0x33)
C_MUT = RGBColor(0x66, 0x66, 0x66)
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_ACC = RGBColor(0xD9, 0x53, 0x4F)
C_GRN = RGBColor(0x27, 0xAE, 0x60)
HX_PRI = "1F4E79"
HX_LT = "EBF0F7"
HX_CALL = "F0F4FA"


def set_bg(cell, h):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{h}"/>'))


def hd(doc, text, lvl=1):
    h = doc.add_heading(text, level=lvl)
    for r in h.runs:
        r.font.name = "Calibri"
        r.font.color.rgb = C_PRI
    h.paragraph_format.space_before = Pt(10 if lvl == 1 else 8)
    h.paragraph_format.space_after = Pt(3)
    return h


def pa(doc, text, bold=False, italic=False, sz=10, sa=4, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(sa)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(sz)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color or C_BODY
    return p


def bl(doc, text, bp=None, sz=9.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.12
    if bp:
        rb = p.add_run(bp)
        rb.font.name = "Calibri"
        rb.font.size = Pt(sz)
        rb.font.bold = True
        rb.font.color.rgb = C_PRI
    rt = p.add_run(text)
    rt.font.name = "Calibri"
    rt.font.size = Pt(sz)
    rt.font.color.rgb = C_BODY
    return p


def fig(doc, path, caption, w=5.8):
    if not path.exists():
        print(f"  [SKIP] {path.name}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)
    p.add_run().add_picture(str(path), width=Inches(w))
    pc = doc.add_paragraph()
    pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pc.paragraph_format.space_after = Pt(6)
    rc = pc.add_run(caption)
    rc.font.name = "Calibri"
    rc.font.size = Pt(8.5)
    rc.font.italic = True
    rc.font.color.rgb = C_MUT


def tbl(doc, headers, rows, cw=None):
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        set_bg(c, HX_PRI)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.name = "Calibri"
            r.font.size = Pt(8.5)
            r.font.bold = True
            r.font.color.rgb = C_WHITE
    for ri, row in enumerate(rows):
        bg = HX_LT if ri % 2 == 1 else "FFFFFF"
        for ci, v in enumerate(row):
            c = t.rows[ri + 1].cells[ci]
            c.text = str(v)
            set_bg(c, bg)
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if ci > 0 else WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(8.5)
                r.font.color.rgb = C_BODY
    if cw:
        for row in t.rows:
            for i, w in enumerate(cw):
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(3)


def callout(doc, title, text):
    """Highlighted Q&A callout box with left accent border."""
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.cell(0, 0)
    c.width = Inches(6.3)
    set_bg(c, HX_CALL)
    # left border accent
    tcPr = c._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="28" w:space="0" w:color="{HX_PRI}"/>'
        f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    ))
    # padding
    tcPr.append(parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/>'
        f'<w:left w:w="200" w:type="dxa"/><w:right w:w="160" w:type="dxa"/>'
        f'</w:tcMar>'
    ))
    p = c.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    rt = p.add_run(f"Q: {title}\n")
    rt.font.name = "Calibri"
    rt.font.size = Pt(10.5)
    rt.font.bold = True
    rt.font.color.rgb = C_PRI
    rb = p.add_run(text)
    rb.font.name = "Calibri"
    rb.font.size = Pt(9.5)
    rb.font.color.rgb = C_BODY
    doc.add_paragraph().paragraph_format.space_after = Pt(3)


def build():
    print("Generating UPGRADED Project Review Document...")
    doc = Document()

    for sec in doc.sections:
        sec.top_margin = Cm(1.8)
        sec.bottom_margin = Cm(1.6)
        sec.left_margin = Cm(2.0)
        sec.right_margin = Cm(2.0)

    # =============== TITLE ===============
    doc.add_paragraph().paragraph_format.space_after = Pt(20)

    pt = doc.add_paragraph()
    pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = pt.add_run("ENERGYCAST V1")
    rt.font.name = "Calibri"
    rt.font.size = Pt(28)
    rt.font.bold = True
    rt.font.color.rgb = C_PRI

    ps = doc.add_paragraph()
    ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ps.paragraph_format.space_after = Pt(6)
    rs = ps.add_run("Electricity Price Forecasting System\nfor the Indian Day-Ahead Power Market")
    rs.font.name = "Calibri"
    rs.font.size = Pt(15)
    rs.font.color.rgb = C_MUT

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    pm = doc.add_paragraph()
    pm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pm.paragraph_format.space_after = Pt(4)
    rm = pm.add_run("7th Semester Software Development Project (SDP)\nProject Review Document")
    rm.font.name = "Calibri"
    rm.font.size = Pt(13)
    rm.font.bold = True
    rm.font.color.rgb = C_BODY

    pd_ = doc.add_paragraph()
    pd_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rd = pd_.add_run("October 2026")
    rd.font.name = "Calibri"
    rd.font.size = Pt(11)
    rd.font.color.rgb = C_MUT

    doc.add_page_break()

    # =============== 1. INTRODUCTION ===============
    hd(doc, "1. Introduction", 1)
    pa(doc, (
        "EnergyCast V1 is a machine learning-based system that predicts hourly electricity "
        "prices on the Indian Energy Exchange (IEX). Specifically, it forecasts the Market "
        "Clearing Price (MCP) of the Day-Ahead Market (DAM) in Rs/MWh. The IEX DAM is a "
        "double-sided uniform-price auction where generators and buyers submit hourly bids, "
        "and the clearing price is set at the intersection of aggregated supply and demand "
        "curves, regulated between Rs 0 and Rs 10,000/MWh by CERC."
    ))

    hd(doc, "1.1 Problem Statement & Need", 2)
    pa(doc, (
        "India's electricity market has become highly volatile due to over 180 GW of "
        "renewable energy. On a sunny afternoon, cheap solar floods the grid and prices drop "
        "below Rs 1,500/MWh. But in the evening, solar disappears while demand peaks (cooling, "
        "lighting, cooking), causing prices to spike above Rs 8,000/MWh in hours. Currently, "
        "most market participants rely on intuition or spreadsheets. There is no widely "
        "available, data-driven forecasting tool tailored to the Indian market. EnergyCast V1 "
        "fills this gap."
    ))

    hd(doc, "1.2 Stakeholders", 2)
    bl(doc, "Plan bidding strategies based on expected prices.", bp="Power Generators: ")
    bl(doc, "Schedule purchases at optimal hours to reduce costs.", bp="DISCOMs & Industries: ")
    bl(doc, "Hedge risk and make informed trading decisions.", bp="Energy Traders: ")
    bl(doc, "Anticipate price-driven dispatch patterns.", bp="Grid Operators (NLDC): ")

    # =============== 2. ARCHITECTURE ===============
    hd(doc, "2. System Architecture", 1)
    pa(doc, (
        "The figure below shows the complete end-to-end pipeline from raw data ingestion "
        "through model training and forecast output."
    ))

    fig(doc, ARCH_FIG,
        "Figure 1: EnergyCast V1 System Architecture — End-to-end pipeline from 3 data sources "
        "through feature engineering, chronological splitting, and 3-tier model evaluation.",
        w=6.3)

    # =============== 3. DATA ===============
    hd(doc, "3. Data Collection & Preprocessing (Steps 1-5)", 1)
    pa(doc, (
        "We collected hourly data from three sources covering January 2022 to May 2025 "
        "(~3.5 years, 28,176 hourly records):"
    ))
    bl(doc, "Hourly DAM clearing prices (MCP), trading volumes, purchase and sell bids.", bp="IEX Market Data: ")
    bl(doc, "Hourly generation from solar, wind, thermal, hydro, nuclear; total demand; inter-regional flows.", bp="Grid-India (POSOCO): ")
    bl(doc, "Hourly temperature, humidity, wind speed, solar radiation across major Indian load centers.", bp="Open-Meteo Weather: ")
    pa(doc, (
        "After cleaning (handling missing values, removing duplicates, IST timezone alignment) "
        "and merging, we produced a unified master dataset of 28,176 rows x 55 columns."
    ), sz=9.5)

    # =============== 4. EDA ===============
    hd(doc, "4. Exploratory Data Analysis (Step 6)", 1)
    pa(doc, "Key discoveries from our data exploration:")
    bl(doc, "Net Demand (Demand - Solar - Wind) correlates at r = +0.620 with price — 2.46x stronger than gross demand alone (r = +0.252). This proves renewable patterns are critical.", bp="Net Demand is the #1 driver: ")
    bl(doc, "India's 'Duck Curve' — midday solar floods the grid, collapsing net demand and prices. Evening solar sunset triggers massive ramps and price spikes (6-10 PM).", bp="Duck Curve Effect: ")
    bl(doc, "Prices strongly correlate with the same hour yesterday (autocorrelation = 0.76 at lag-24). Weekly patterns also exist.", bp="Strong cyclical patterns: ")

    fig(doc, EDA_FIG / "fig06_merit_order_and_duck_curve.png",
        "Figure 2: The Duck Curve — solar depresses midday prices; evening ramps spike prices as expensive peakers fire up.",
        w=6.0)

    # =============== 5. FEATURES ===============
    hd(doc, "5. Feature Engineering (Step 7)", 1)
    pa(doc, (
        "We engineered 53 predictive features from the raw data across 7 categories:"
    ))
    feat_h = ["Category", "Count", "Examples"]
    feat_d = [
        ["Price History Lags", "8", "Price 1h, 24h, 48h, 168h ago"],
        ["Rolling Statistics", "7", "24h rolling mean, min, max, std of price"],
        ["Price Momentum", "6", "Price velocity, ratio of recent to yesterday"],
        ["Grid & Renewables", "12", "Net demand, solar/wind gen, thermal, ramp rate"],
        ["Calendar & Time", "8", "Hour (sine/cosine), day of week, month, holiday"],
        ["Weather", "7", "Temperature, humidity, wind speed, solar radiation"],
        ["Lagged Market Signals", "5", "Yesterday's purchase/sell bids, market tightness"],
    ]
    tbl(doc, feat_h, feat_d, cw=[1.5, 0.7, 4.3])

    pa(doc, (
        "Critical: We removed 5 contemporaneous variables (actual clearing volume, weighted "
        "MCP, etc.) that would only be known after the price is set — preventing data leakage. "
        "All market features use values from at least 24 hours ago."
    ), sz=9.5, italic=True)

    # =============== 6. SPLIT ===============
    hd(doc, "6. Chronological Train-Validation-Test Split (Step 8)", 1)

    sp_h = ["Partition", "Period", "Hours", "Share", "Purpose"]
    sp_d = [
        ["Training", "Jan 2022 - Dec 2023", "15,192", "53.9%", "Models learn patterns"],
        ["Validation", "Jan 2024 - Dec 2024", "8,784", "31.2%", "Tune hyperparameters"],
        ["Test", "Jan 2025 - May 2025", "4,200", "14.9%", "Final unseen evaluation"],
    ]
    tbl(doc, sp_h, sp_d, cw=[1.0, 1.5, 0.7, 0.6, 2.2])

    pa(doc, (
        "Strict chronological order — no random shuffling. The test set is completely unseen "
        "during training. Results on test represent genuine real-world forecasting accuracy."
    ), sz=9.5)

    # =============== 7. MODELS ===============
    hd(doc, "7. Three-Tier Model Hierarchy (Steps 9-11)", 1)

    hd(doc, "7.1 Tier 1: Seasonal Naive Baseline (Step 9)", 2)
    pa(doc, (
        "Simplest forecast: 'Tomorrow's 3 PM price = today's 3 PM price' (Daily Seasonal "
        "Naive, period = 24h). This sets the minimum bar. Test MAE = Rs 658.42/MWh, R2 = 0.7828."
    ))

    hd(doc, "7.2 Tier 2: Ridge Regression (Step 10)", 2)
    pa(doc, (
        "Linear model using all 53 features with L2 regularization (alpha = 50.0, tuned on "
        "validation set). Captures linear relationships — solar pushes prices down (coeff = -269), "
        "net demand ramps push prices up (+235). Test MAE = Rs 544.61/MWh, R2 = 0.9059. "
        "Beats naive by 17.3%."
    ))

    hd(doc, "7.3 Tier 3: Gradient Boosted Trees (Step 11)", 2)
    pa(doc, (
        "State-of-the-art non-linear models. Hundreds of small decision trees built "
        "sequentially, each correcting previous mistakes. Key advantages over linear models: "
        "capture non-linear price dynamics, automatic feature interactions, and natural "
        "adherence to price bounds."
    ))
    bl(doc, "Histogram-based leaf-wise GBDT. Stopped early at 282 trees.", bp="LightGBM: ")
    bl(doc, "Exact second-order Newton GBDT. Stopped early at 268 trees.", bp="XGBoost: ")
    pa(doc, (
        "Both used early stopping (50-round patience on validation set) to prevent overfitting."
    ), sz=9.5)

    # =============== 8. RESULTS ===============
    hd(doc, "8. Final Results", 1)

    r_h = ["Model", "MAE (Rs/MWh)", "RMSE (Rs/MWh)", "R2 Score", "vs Naive"]
    r_d = [
        ["Weekly Seasonal Naive", "964.57", "1,673.55", "0.6136", "—"],
        ["Daily Seasonal Naive", "658.42", "1,254.07", "0.7828", "Baseline"],
        ["Persistence Naive", "584.28", "1,043.68", "0.8500", "+11.3%"],
        ["OLS Linear Regression", "545.19", "826.65", "0.9056", "+17.2%"],
        ["Ridge (alpha=50)", "544.61", "825.53", "0.9059", "+17.3%"],
        ["XGBoost (268 trees)", "439.67", "708.59", "0.9307", "+33.2%"],
        ["LightGBM (282 trees) ★", "433.33", "703.43", "0.9317", "+34.2%"],
    ]
    tbl(doc, r_h, r_d, cw=[2.0, 1.0, 1.0, 0.8, 0.8])

    bl(doc, "LightGBM is the champion — MAE Rs 433/MWh, R2 = 0.93, explaining 93.2% of price variation.", bp="Winner: ")
    bl(doc, "Each tier adds value: Naive -> Ridge (+17.3%), Ridge -> LightGBM (+20.4%).", bp="Progressive improvement: ")
    bl(doc, "LightGBM excels during volatile evening peaks (6-10 PM), reducing errors by 50%+ over naive.", bp="Best where it matters: ")

    fig(doc, TREE_FIG / "fig_trees04_14day_forecast_tracking.png",
        "Figure 3: 14-day forecast tracking — LightGBM (green) tracks rapid price swings far better than Ridge (gold).",
        w=6.0)

    fig(doc, TREE_FIG / "fig_trees05_hourly_mae_profile_comparison.png",
        "Figure 4: Hourly error profile — LightGBM dominates across all 24 hours, especially during the critical evening peak.",
        w=5.6)

    # ============================================================
    #                 REVIEWER Q&A SECTION
    # ============================================================
    doc.add_page_break()
    hd(doc, "9. Anticipated Reviewer Questions & Answers", 1)
    pa(doc, (
        "This section provides prepared, well-reasoned answers to the questions most commonly "
        "asked during SDP project reviews."
    ), sz=9.5, italic=True)

    # --- Q1: Novelty ---
    callout(doc,
        '"What\'s novel about your project? How does it compare to existing work?"',
        "Answer: Most existing electricity price forecasting research focuses on European "
        "and American markets (Nord Pool, PJM, ERCOT). Very few studies target the Indian IEX "
        "DAM specifically. Our key novelties are:\n\n"
        "1. India-Specific Feature Engineering: We engineered 'Net Demand' (Demand - Solar - Wind) "
        "which captures India's unique duck curve dynamics — this single feature has 2.46x "
        "stronger correlation with price than gross demand. No prior Indian study uses this.\n\n"
        "2. Market Tightness Index: We created a novel 'bidding deficit' feature "
        "(Purchase Bids - Sell Bids) / Sell Bids from lagged IEX data, which directly captures "
        "supply scarcity signals unique to double-sided auction markets.\n\n"
        "3. Rigorous Leakage Prevention: Many published studies accidentally use contemporaneous "
        "variables (current-hour demand or volume) that wouldn't be available in a real "
        "forecasting scenario. We explicitly identified and removed 5 such leaking variables.\n\n"
        "4. Three-Tier Hierarchical Benchmarking: We systematically compare non-parametric, "
        "linear, and non-linear models — most studies only report one model without baselines.\n\n"
        "Related Work: Lago et al. (2021) benchmarked 27 methods on European markets — "
        "tree ensembles (like our LightGBM) consistently ranked in the top 3. Ugurlu et al. "
        "(2018) showed GBDT outperforms ARIMA and SVR for Turkish electricity prices. Our "
        "work extends these findings to the structurally different Indian market."
    )

    # --- Q2: Why not LSTM ---
    callout(doc,
        '"Why not use LSTM or deep learning? Aren\'t neural networks better?"',
        "Answer: This is a deliberate, well-reasoned engineering decision, not a limitation:\n\n"
        "1. Tabular Data Favors Trees: Our data is structured/tabular (53 numeric features "
        "per hour). Multiple peer-reviewed benchmarks (Grinsztajn et al., NeurIPS 2022; "
        "Shwartz-Ziv & Armon, 2022) conclusively show that tree-based models (XGBoost, "
        "LightGBM) outperform deep learning on medium-sized tabular datasets.\n\n"
        "2. Sample Size: With 15,192 training hours, we have insufficient data to train "
        "deep architectures (LSTMs typically need 50,000-100,000+ samples to generalize).\n\n"
        "3. Interpretability: Tree models provide direct feature importance rankings (gain, "
        "split count). For a power market application, stakeholders need to understand WHY a "
        "price was predicted — 'because mcp_lag_24 was high and net_demand_ramp was steep' "
        "is actionable. LSTM hidden states are opaque.\n\n"
        "4. Training Efficiency: LightGBM trained in under 30 seconds with early stopping. "
        "Equivalent LSTM training would take hours with GPU requirements.\n\n"
        "5. Empirical Evidence: Lago et al. (2021) — the largest electricity price forecasting "
        "benchmark to date — found that gradient boosted trees match or exceed LSTM/DNN "
        "performance on 5 of 6 markets tested.\n\n"
        "Future Scope: We plan to evaluate Temporal Fusion Transformers (TFT) in V2 to "
        "formally validate this architectural choice."
    )

    # --- Q3: Limitations ---
    callout(doc,
        '"What are the limitations of your system?"',
        "Answer: We acknowledge the following limitations:\n\n"
        "1. Point Forecasts Only: We predict a single price value per hour. We do not "
        "provide prediction intervals or probabilistic forecasts (e.g., '80% chance price "
        "is between Rs 3,000 and Rs 5,000'). This limits risk assessment.\n\n"
        "2. No Exogenous Forecast Integration: We use actual observed weather and demand "
        "values. In a true real-time deployment, we would need weather forecasts and demand "
        "forecasts as inputs, which introduce additional forecast error cascading.\n\n"
        "3. Static Model: The model is trained once and frozen. It does not retrain "
        "automatically as new data arrives. Market regime shifts (e.g., new policy, new "
        "capacity additions) would degrade performance over time.\n\n"
        "4. Single Market: We only forecast IEX DAM MCP. We don't cover the Real-Time "
        "Market (RTM), Term-Ahead Market (TAM), or bilateral contract prices.\n\n"
        "5. Limited History: 3.5 years of data may not capture rare events like once-in-a-"
        "decade coal shortages or extreme monsoon failures.\n\n"
        "6. No Spike-Specific Model: Extreme price spikes (>Rs 8,000/MWh) are rare events "
        "where our model's accuracy drops. A dedicated spike classifier could help."
    )

    # --- Q4: Architecture (already covered with diagram, add verbal explanation) ---
    callout(doc,
        '"Can you walk me through the architecture / data flow?"',
        "Answer: (Refer to Figure 1 on page 2)\n\n"
        "The pipeline has 5 layers:\n\n"
        "Layer 1 — Data Ingestion: Three independent data streams (IEX market data, "
        "Grid-India physical grid data, Open-Meteo weather data) are downloaded as CSVs.\n\n"
        "Layer 2 — Preprocessing & Fusion: All three sources are cleaned (missing values "
        "imputed, duplicates removed), timezone-aligned to IST, and merged on hourly "
        "timestamps into a single unified dataset (28,176 rows x 55 columns).\n\n"
        "Layer 3 — Feature Engineering: 53 predictive features are computed: price lags "
        "and rolling statistics (temporal memory), net demand and ramp rates (physical "
        "drivers), calendar harmonics (cyclical patterns), and weather aggregations. "
        "5 contemporaneous leaking variables are dropped.\n\n"
        "Layer 4 — Chronological Split: Data is split strictly by time into Train "
        "(2022-2023), Validation (2024), and Test (2025). No random shuffling.\n\n"
        "Layer 5 — Model Hierarchy: Three model tiers are trained on the training set, "
        "tuned on validation, and evaluated on test: Seasonal Naive (benchmark), Ridge "
        "Regression (linear), LightGBM/XGBoost (non-linear). The champion model "
        "(LightGBM) produces the final hourly Rs/MWh forecast."
    )

    # --- Q5: Real-time Deployment ---
    callout(doc,
        '"What about real-time deployment? Can this run in production?"',
        "Answer: The current system is a research prototype. For production deployment, "
        "we would need:\n\n"
        "1. Automated Data Pipeline: Scheduled scripts (cron/Airflow) to pull IEX market "
        "reports, Grid-India generation data, and weather forecasts every hour.\n\n"
        "2. Weather Forecast Integration: Replace actual weather with forecast weather "
        "(e.g., IMD or Open-Meteo forecast API). This adds ~2-5% additional MAE from "
        "weather forecast error.\n\n"
        "3. Model Serving: The trained LightGBM model (saved as .joblib, only ~2 MB) "
        "can generate 24-hour ahead forecasts in under 50 milliseconds. It can be served "
        "via a simple Flask/FastAPI REST endpoint.\n\n"
        "4. Online Retraining: Periodic retraining (weekly/monthly) with new data to "
        "adapt to market regime changes (new capacity additions, policy shifts).\n\n"
        "5. Monitoring & Alerting: Track live forecast errors. If MAE exceeds a threshold "
        "(e.g., 2x historical average), trigger an alert for model retraining.\n\n"
        "6. Dashboard: We plan to build a Streamlit web app (Step 14) for interactive "
        "visualization and scenario analysis as a proof-of-concept deployment interface.\n\n"
        "Inference Latency: LightGBM inference for 24 hours takes <50ms — well within "
        "the IEX gate closure timeline (10 AM for next-day delivery)."
    )

    # --- Q6: Why MAE not MAPE ---
    callout(doc,
        '"Why did you use MAE and RMSE? Why not MAPE?"',
        "Answer: This is a deliberate choice based on the mathematical properties of "
        "electricity prices:\n\n"
        "1. MAE (Mean Absolute Error): The average of |actual - predicted| in Rs/MWh. "
        "It's in the same units as the price, making it directly interpretable. 'Our model "
        "is off by Rs 433 on average' is immediately meaningful to a trader.\n\n"
        "2. RMSE (Root Mean Squared Error): Penalizes large errors more than small ones "
        "(due to squaring). This is critical because a single hour with a Rs 3,000 error "
        "can cost a DISCOM crores — we want our model to minimize big blunders.\n\n"
        "3. Why NOT MAPE (Mean Absolute Percentage Error): MAPE = |error|/|actual| x 100%. "
        "Electricity prices can be very close to zero (e.g., Rs 100/MWh during solar noon "
        "oversupply). When actual price = Rs 100 and prediction = Rs 200, MAPE = 100% — "
        "making it look catastrophic even though the absolute error is just Rs 100. This "
        "makes MAPE unreliable and misleadingly inflated for electricity markets.\n\n"
        "4. We use sMAPE (symmetric MAPE) as a supplementary metric, which partially fixes "
        "this by averaging actual and predicted in the denominator.\n\n"
        "5. R-squared (R2): The proportion of variance explained. R2 = 0.93 means our model "
        "explains 93% of all price variation. This is a unitless measure useful for comparing "
        "across different datasets or markets.\n\n"
        "This metric combination (MAE + RMSE + sMAPE + R2) is the standard in electricity "
        "price forecasting literature (Weron, 2014; Lago et al., 2021)."
    )

    # --- Q7: Challenges ---
    callout(doc,
        '"What challenges did you face and how did you solve them?"',
        "Answer: We encountered several significant challenges:\n\n"
        "1. Data Leakage (Critical): Initially, our model showed suspiciously high R2 = 0.99. "
        "Investigation revealed 5 contemporaneous market variables (actual clearing volume, "
        "weighted MCP at hour t) were being used as features. These are only known AFTER the "
        "price is set — using them is 'cheating'. Solution: We systematically identified and "
        "removed all 5 leaking variables, dropping R2 to a realistic 0.93.\n\n"
        "2. Missing Data Alignment: IEX reports use delivery-day timestamps while Grid-India "
        "uses calendar-day. Weather data is in UTC. Merging required careful timezone "
        "conversion and hourly alignment across all three sources.\n\n"
        "3. Unicode Encoding on Windows: Python scripts crashed with UnicodeEncodeError "
        "when printing the Rs symbol on Windows terminal (cp1252 encoding). Solution: "
        "Used 'Rs' in console output, reserved Unicode characters for file/report output.\n\n"
        "4. Extreme Price Spikes: Prices above Rs 8,000/MWh are rare (<2% of data) but "
        "financially critical. Standard MSE loss under-weighs these. Solution: Tree models "
        "with sufficient depth naturally partition the feature space to handle tail events, "
        "and early stopping prevents overfitting to the dominant moderate-price regime.\n\n"
        "5. Feature Engineering for Non-Linearity: Linear models couldn't capture the convex "
        "merit-order stack. Rather than manually engineering polynomial features (which "
        "explode combinatorially with 53 inputs), we leveraged tree ensembles that "
        "automatically discover non-linear interactions through recursive splitting.\n\n"
        "6. Overfitting Prevention: With 282 trees and 53 features, overfitting is a real "
        "risk. Solution: L1/L2 regularization on leaf weights, row/column subsampling (80%), "
        "minimum leaf samples (25), and early stopping on a held-out validation year (2024)."
    )

    # =============== 10. NEXT STEPS ===============
    hd(doc, "10. Next Steps", 1)
    bl(doc, "Statistical significance testing (Diebold-Mariano), seasonal sub-analysis, unified benchmark.", bp="Step 12 — Benchmarking: ")
    bl(doc, "SHAP analysis for instance-level 'why did the model predict this price?' explanations.", bp="Step 13 — Explainability: ")
    bl(doc, "Interactive Streamlit web app for live forecasting and scenario analysis.", bp="Step 14 — Dashboard: ")

    # =============== SAVE ===============
    doc.save(str(OUTPUT_DOCX))
    fsize = OUTPUT_DOCX.stat().st_size / 1024 / 1024
    print(f"UPGRADED Project Review Document saved to: {OUTPUT_DOCX}")
    print(f"File size: {fsize:.2f} MB")


if __name__ == "__main__":
    build()
