"""
Generates a comprehensive, professionally styled Microsoft Word document (.docx)
explaining every feature, control, graph, table, and backend algorithm of the
EnergyCast Web Application in complete technical and operational detail.

Output:
    v:/College/7th SEM/SDP/EnergyCast_Web_Application_Complete_Guide.docx
"""

from __future__ import annotations

from pathlib import Path
import docx
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor


OUTPUT_PATH = Path(r"v:\College\7th SEM\SDP\EnergyCast_Web_Application_Complete_Guide.docx")


def set_cell_background(cell, hex_color: str) -> None:
    """Sets background shading color of a Word table cell."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_margins(cell, top=100, bottom=100, left=140, right=140) -> None:
    """Sets internal padding (in dxa) for a Word table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def add_styled_table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float] | None = None,
    header_bg: str = "0F172A",
    stripe_bg: str = "F8FAFC",
) -> None:
    """Adds a clean, bordered, alternating-row table to the Word document."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        cell = hdr_cells[i]
        set_cell_background(cell, header_bg)
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(h_text)
        run.bold = True
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for r_idx, r_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        bg = stripe_bg if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(r_data):
            cell = row_cells[c_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=90, bottom=90, left=130, right=130)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(str(val))
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
            if c_idx == 0:
                run.bold = True

    if col_widths:
        for row in table.rows:
            for idx, w_in in enumerate(col_widths):
                if idx < len(row.cells):
                    row.cells[idx].width = Inches(w_in)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(6)


def add_callout_box(doc: Document, title: str, body_text: str, fill_hex: str = "F0FDFA") -> None:
    """Adds a single-cell shaded callout box for formulas, key insights, or viva tips."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.style = "Table Grid"
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    r_title = p.add_run(title + "\n")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(10.5)
    r_title.font.color.rgb = RGBColor(0x0D, 0x94, 0x88)

    r_body = p.add_run(body_text)
    r_body.font.name = "Calibri"
    r_body.font.size = Pt(10)
    r_body.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(6)


def add_heading_1(doc: Document, text: str) -> None:
    h = doc.add_heading(level=1)
    h.paragraph_format.space_before = Pt(16)
    h.paragraph_format.space_after = Pt(6)
    run = h.add_run(text)
    run.bold = True
    run.font.name = "Calibri"
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)


def add_heading_2(doc: Document, text: str) -> None:
    h = doc.add_heading(level=2)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(4)
    run = h.add_run(text)
    run.bold = True
    run.font.name = "Calibri"
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(0x0D, 0x94, 0x88)


def add_heading_3(doc: Document, text: str) -> None:
    h = doc.add_heading(level=3)
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(3)
    run = h.add_run(text)
    run.bold = True
    run.font.name = "Calibri"
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)


def add_para(doc: Document, text: str, bold_prefix: str | None = None) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Calibri"
        r_pre.font.size = Pt(10.5)
        r_pre.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    r_txt = p.add_run(text)
    r_txt.font.name = "Calibri"
    r_txt.font.size = Pt(10.5)
    r_txt.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)


def add_bullet(doc: Document, bold_prefix: str, text: str) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.12
    r_pre = p.add_run(bold_prefix)
    r_pre.bold = True
    r_pre.font.name = "Calibri"
    r_pre.font.size = Pt(10)
    r_pre.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    r_txt = p.add_run(text)
    r_txt.font.name = "Calibri"
    r_txt.font.size = Pt(10)
    r_txt.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)


def build_document() -> None:
    doc = Document()

    # Configure page margins (0.85 inches all around for wide tables)
    for section in doc.sections:
        section.top_margin = Inches(0.85)
        section.bottom_margin = Inches(0.85)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    # =========================================================================
    # TITLE BANNER
    # =========================================================================
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(6)
    title_p.paragraph_format.space_after = Pt(4)
    r_t = title_p.add_run("ENERGYCAST WEB APPLICATION\nCOMPLETE TECHNICAL & USER GUIDE")
    r_t.bold = True
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(20)
    r_t.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(14)
    r_s = sub_p.add_run(
        "Comprehensive In-Detail Documentation of All 4 Workflow Tabs, Interactive Controls, "
        "HiDPI Charts, Tables, Mathematical Formulas, and Live Backend Inference Pipelines\n"
        "Indian Energy Exchange (IEX) Day-Ahead Market (DAM) Forecasting & Procurement Platform"
    )
    r_s.font.name = "Calibri"
    r_s.font.size = Pt(11)
    r_s.font.color.rgb = RGBColor(0x0D, 0x94, 0x88)

    # =========================================================================
    # SECTION 1: SYSTEM ARCHITECTURE & HOW THE WEBSITE WORKS
    # =========================================================================
    add_heading_1(doc, "1. Overview: What Is the EnergyCast Web Application?")
    add_para(
        doc,
        "The EnergyCast Web Application is a full-stack commercial decision-support and algorithmic bidding platform "
        "built for State Distribution Companies (DISCOMs), Open-Access Industrial Plants (steel, cement, aluminum, "
        "textiles), Grid-Scale Battery Energy Storage Systems (BESS), and Power Trading Desks operating on the "
        "Indian Energy Exchange (IEX) Day-Ahead Market (DAM).",
    )
    add_para(
        doc,
        "Every day before 10:30 AM IST, market participants must submit 24 hourly (or 96 fifteen-minute) price-quantity "
        "bids for physical electricity delivery across the 24 hours of the next calendar day (Day D). Because the IEX "
        "DAM clears via a blind uniform-price double auction between Rs. 0/MWh and the Central Electricity Regulatory "
        "Commission (CERC) statutory ceiling of Rs. 10,000/MWh, traders face extreme price volatility driven by midday "
        "solar surpluses (which depress prices to Rs. 2,200-2,600/MWh) and evening thermal ramping (which pushes prices "
        "to Rs. 9,500-10,000/MWh when solar drops to zero).",
    )

    add_heading_2(doc, "1.1 Three-Layer Software Architecture of the Web App")
    add_bullet(
        doc,
        "1. Python Backend & In-Memory Inference Engine (app/main.py): ",
        "Runs a multi-threaded HTTP REST server powered by the EnergyCastEngine class. At startup (in ~180 ms), it loads "
        "all trained machine learning models (lightgbm_model.joblib, xgboost_model.joblib, ridge_regression.joblib, "
        "linear_regression.joblib, feature_scaler.joblib) and the 4,200-hour unseen 2025 out-of-sample test partition "
        "(data/processed/splits/test.csv) into RAM. It exposes five REST API endpoints: GET /api/overview, "
        "GET /api/day-forecast, GET /api/hour-explain, POST /api/simulate, and GET /api/benchmarks.",
    )
    add_bullet(
        doc,
        "2. Custom HiDPI HTML5 Canvas & Product Controller (app/static/app.js & index.html): ",
        "A zero-dependency, institutional-grade frontend controller (2,300 lines of JavaScript) that renders six "
        "device-pixel-ratio-calibrated (HiDPI) interactive charts, a universal rectangular hover popover statistics box, "
        "plain-English signal translation dictionaries, a live Linear Programming (LP) bid optimizer, and one-click "
        "IEX CSV exporters.",
    )
    add_bullet(
        doc,
        "3. Hybrid Live API + Embedded Offline Digital Twin (app/static/embedded_data.js): ",
        "When launched via 'uv run python app/main.py', the frontend communicates with the live Python backend over "
        "HTTP. If the HTML file is opened directly without a server (file:// mode), the frontend automatically falls "
        "back to an embedded data bundle containing all 175 test days (4,200 hours) and analytical response surfaces.",
    )

    add_callout_box(
        doc,
        "CRITICAL CONCEPT: Why Can the Website Show 'Verified Actual Price' for Tomorrow's Forecast?",
        "In a live trading environment at 10:15 AM today, tomorrow's actual clearing price is unknown—only the AI "
        "Forecast Price and the 90% Confidence Band exist before the 10:30 AM IEX gate closure.\n\n"
        "However, for scientific verification and academic auditing, the website operates as an Out-of-Sample "
        "Historical Digital Twin over the 4,200 unseen test hours of Jan 2025 - Jun 2025 (test.csv). All models were "
        "trained strictly on 2022-2023 data (15,192 hours) and tuned on 2024 data (8,784 hours)—they never saw a single "
        "hour of 2025 during training. Furthermore, for every date selected in the app, the model only receives the 53 "
        "causal features known BEFORE 10:30 AM on Day D-1. Because those dates in 2025 have already settled in history, "
        "the website allows you to toggle 'Show Verified Actual Price' on or off: turning it OFF shows exactly what a "
        "trader sees before bidding at 10:15 AM; turning it ON overlays the real post-settlement IEX price so an "
        "auditor or examiner can verify the model's accuracy (Rs. 433.33/MWh MAE, 93.17% R-squared).",
    )

    # =========================================================================
    # SECTION 2: GLOBAL NAVIGATION HEADER & SCENARIO CONTEXT BAR
    # =========================================================================
    add_heading_1(doc, "2. Global Navigation Bar & Market Scenario Context Bar")
    add_para(
        doc,
        "At the top of the screen, two persistent bars remain visible across all tabs so the user can switch workflows, "
        "change the delivery date or focus hour, jump to notable market stress days, or export data at any time.",
    )

    add_heading_2(doc, "2.1 Top Product Navigation Bar")
    add_styled_table(
        doc,
        headers=["UI Element / Button", "Location", "Detailed Function & Behavior"],
        rows=[
            [
                "Brand Identity & Market Badge",
                "Top Left",
                "Displays 'EnergyCast | IEX Day-Ahead Market — AI Power Price Forecasting & Automated Procurement Platform'.",
            ],
            [
                "4 Workflow Navigation Tabs",
                "Top Center",
                "Switches instantaneously between (1) Market Forecast & Dispatch, (2) Smart Bid & Cost Optimizer, "
                "(3) Weather & Grid Risk Simulator, and (4) Forecast Accuracy & Trust.",
            ],
            [
                "Export 24h CSV Button",
                "Top Right",
                "Generates and downloads 'EnergyCast_IEX_DAM_Forecast_<DATE>.csv' containing 11 columns for all 24 hours: "
                "Delivery_Date, Hour_Block_IST, AI_Forecast_Price_Rs_MWh, Confidence_90_Low_Rs_MWh, "
                "Confidence_90_High_Rs_MWh, Verified_Actual_Price_Rs_MWh, National_Demand_GW, Net_Thermal_Demand_GW, "
                "Solar_Generation_GW, Wind_Generation_GW, and Renewable_Share_Pct.",
            ],
            [
                "Dark Mode / Light Mode Toggle",
                "Top Right",
                "Switches the entire application theme between institutional Light Mode and high-contrast trading-desk "
                "Dark Mode, immediately redrawing all six HTML5 canvases with theme-calibrated color palettes.",
            ],
        ],
        col_widths=[1.8, 1.1, 3.8],
    )

    add_heading_2(doc, "2.2 Global Delivery Date, Focus Hour & 5 Curated Market Scenario Chips")
    add_para(
        doc,
        "Below the header sits the Market Context Bar. It contains the Delivery Date selector (175 out-of-sample test "
        "days from 2025-01-01 to 2025-06-24), Previous/Next Day navigation arrows (<- and ->), the Focus Hour dropdown "
        "(00:00 IST to 23:00 IST), and 5 One-Click Notable Market Day Preset Chips. Clicking any preset chip loads "
        "that exact historical date and focus hour across all four tabs simultaneously:",
    )
    add_styled_table(
        doc,
        headers=["Scenario Chip Label", "Target Date & Focus Hour", "Physical Grid Regime & Market Behavior Demonstrated"],
        rows=[
            [
                "Jan 01: Evening Scarcity",
                "2025-01-01 @ 18:00 IST",
                "Classic Duck Curve Day: Midday solar depresses clearing price to Rs. 2,607/MWh at 13:00 IST, followed by "
                "a steep +13.5 GW evening net thermal demand ramp as solar fades, pushing MCP to Rs. 9,754/MWh at 18:00 IST.",
            ],
            [
                "Jan 06: Rs. 10k Peak Cap",
                "2025-01-06 @ 19:00 IST",
                "Extreme Industrial Peak: High gross demand (197.5 GW gross, 188.4 GW net thermal) exhausts domestic coal "
                "capacity and triggers consecutive Rs. 10,000/MWh CERC statutory ceiling blocks during the evening ramp.",
            ],
            [
                "Mar 16: Solar Discount",
                "2025-03-16 @ 12:00 IST",
                "Spring High-Solar Midday Collapse: Strong utility solar injection pushes Renewable Penetration above 26%, "
                "creating deep midday price discounts ideal for industrial load shifting and BESS battery charging.",
            ],
            [
                "May 18: Summer Heatwave",
                "2025-05-18 @ 21:00 IST",
                "Peak Summer Cooling Stress: High Cooling Degree Days (CDD > 24 C) keep night-time residential AC load "
                "elevated well past sunset, sustaining high clearing prices across late-night blocks (21:00-23:00 IST).",
            ],
            [
                "Jun 15: Monsoon Wind Surge",
                "2025-06-15 @ 15:00 IST",
                "Early Monsoon Wind + Thermal Relief: High hub-height wind generation moderates net thermal demand across "
                "both afternoon and late-night blocks, stabilizing market clearing prices.",
            ],
        ],
        col_widths=[1.6, 1.5, 3.6],
    )

    # =========================================================================
    # SECTION 3: TAB 1 — MARKET FORECAST & DISPATCH COMMAND CENTER
    # =========================================================================
    add_heading_1(doc, "3. Workflow Tab 1: Market Forecast & Dispatch Command Center")
    add_para(
        doc,
        "Tab 1 is the primary morning situational-awareness dashboard used by a DISCOM or industrial power trader "
        "between 09:30 AM and 10:15 AM IST before submitting day-ahead bids. Every component on this tab updates "
        "instantly when you change the Delivery Date or Focus Hour.",
    )

    add_heading_2(doc, "3.1 Dynamic Plain-English Trading Advisory Banner")
    add_para(
        doc,
        "At the top of Tab 1 sits an automated intelligence banner that scans the 24 hourly LightGBM predictions for "
        "the selected date, identifies the 4 cheapest buying hours and 4 most expensive peak hours, and classifies "
        "the day into one of three actionable trading regimes:",
    )
    add_bullet(
        doc,
        "Regime A — HIGH EVENING SCARCITY ALERT (Triggered when Max 24h Forecast >= Rs. 7,500/MWh): ",
        "Banner turns crimson-accented and warns: 'Evening Peak Reaches Rs. X/MWh — Shift Flexible Load to Solar Hours "
        "(Rs. Y/MWh)'. Summarizes the exact peak hours approaching the Rs. 10,000/MWh ceiling and reports the exact "
        "percentage cost reduction achieved by shifting flexible load into the 4 cheapest solar hours.",
    )
    add_bullet(
        doc,
        "Regime B — SOLAR SURPLUS BUYING OPPORTUNITY (Triggered when Min 24h Forecast <= Rs. 2,600/MWh): ",
        "Highlights the deep midday solar discount window, reporting peak national solar GW injection and the "
        "peak-to-trough arbitrage spread in Rs./MWh for industrial and BESS charging.",
    )
    add_bullet(
        doc,
        "Regime C — MODERATE BALANCED MARKET (All other days): ",
        "Reports the 24-hour average clearing price in both Rs./MWh and Rs./kWh alongside the lowest-cost buying "
        "hours and highest-tariff evening blocks.",
    )
    add_para(
        doc,
        "On the right side of the banner, the 'Calculate My Cost Savings ->' button jumps directly to Tab 2 (Smart Bid "
        "& Cost Optimizer) with the current date loaded.",
    )

    add_heading_2(doc, "3.2 Four Executive Summary KPI Cards (Tab 1 Top Row)")
    add_styled_table(
        doc,
        headers=["KPI Card Title", "Primary Value Displayed", "Sub-Caption & Mathematical Definition"],
        rows=[
            [
                "1. Expected 24h Avg Price",
                "Rs. X,XXX / MWh",
                "Arithmetic mean of the 24 hourly LightGBM predictions for the selected date. Sub-caption converts "
                "this to retail units (Rs./kWh = Rs./MWh / 1000) and displays the daily Min-Max range.",
            ],
            [
                "2. Best 4h Buying Window",
                "HH:00 - HH:00 (Save X%)",
                "Identifies the 4 hours with the lowest predicted clearing prices (typically 11:00-15:00 solar trough). "
                "Pill shows percentage savings relative to the 24-hour daily mean price.",
            ],
            [
                "3. Peak Risk Window",
                "HH:00 - HH:00 (Avoid/Shave)",
                "Identifies the 4 hours with the highest predicted clearing prices (typically 18:00-22:00 evening ramp). "
                "Sub-caption shows average peak price and maximum national net thermal load in GW.",
            ],
            [
                "4. Focus Hour AI Forecast",
                "Rs. X,XXX / MWh @ HH:00 IST",
                "Shows the exact LightGBM prediction for the currently selected Focus Hour along with its lower and "
                "upper 90% confidence interval bounds.",
            ],
        ],
        col_widths=[1.7, 1.6, 3.4],
    )

    add_heading_2(doc, "3.3 Graph 1: '24-Hour Day-Ahead Price Forecast & 90% Confidence Band'")
    add_para(
        doc,
        "This primary canvas (canvas-main-forecast) plots the complete 24-hour price trajectory from 00:00 to 23:00 IST. "
        "Below is the exact breakdown of every visual layer, formula, and interactive control on this chart:",
    )
    add_bullet(
        doc,
        "Solid Teal Line (AI Forecast Price in Rs./MWh): ",
        "Plots the Champion LightGBM model's point prediction (pred_lightgbm) for each hour h in {0..23}, strictly "
        "clipped to the CERC statutory range [Rs. 0, Rs. 10,000/MWh].",
    )
    add_bullet(
        doc,
        "Shaded Teal Band (90% Confidence Interval): ",
        "Represents the uncertainty envelope around the point forecast. For each hour h, the half-width is computed in "
        "getHourConfidenceBand(hRow) by combining the cross-ensemble disagreement between LightGBM and XGBoost with a "
        "regime-dependent diurnal base width: "
        "dispersion = 0.85 * |pred_lightgbm - pred_xgboost|; "
        "baseHalfWidth = Rs. 540 (if evening peak hour 18:00-22:00), Rs. 340 (if solar hour 08:00-17:00), or Rs. 410 "
        "(if off-peak night hour); "
        "halfWidth = max(260, round(baseHalfWidth + dispersion)). "
        "The lower bound is max(0, pred_lightgbm - halfWidth) and the upper bound is min(10000, pred_lightgbm + halfWidth).",
    )
    add_bullet(
        doc,
        "Dashed Gold Line ('Show Verified Actual Price' Checkbox): ",
        "When checked, overlays the actual historical IEX DAM clearing price (actual_mcp) for that day so users can "
        "visually verify forecast tracking across solar troughs and evening spikes. The top-right badge displays the "
        "exact Verified Day Error (MAE) in Rs./MWh and Rs./kWh.",
    )
    add_bullet(
        doc,
        "Vertical Green & Red Shaded Columns ('Highlight Buy / Peak Zones' Checkbox): ",
        "When checked, highlights the 4 lowest-priced hours in soft emerald green (Best Buy Window) and the 4 "
        "highest-priced hours in soft crimson red (Evening Peak Risk).",
    )
    add_bullet(
        doc,
        "Interactive Hover Popover & Click Selection: ",
        "Hovering anywhere on the chart opens a floating rectangular popover displaying: (1) AI Forecast Price in "
        "Rs./MWh and Rs./kWh, (2) 90% Confidence Band, (3) Verified Actual Price & Signed Error, (4) National Net "
        "Thermal Load & Gross Load in GW, (5) Solar + Wind Output in GW, and (6) Recommended Buyer Action. Clicking "
        "any hour on the chart (or clicking any of the 24 numbered buttons 00-23 on the timeline bar directly underneath "
        "the chart) locks that hour as the Focus Hour and updates the right-hand price driver panel.",
    )

    add_heading_2(doc, "3.4 Right Sidebar Panel: 'What's Driving the Price at [HH:00 IST]?' (TreeSHAP Breakdown)")
    add_para(
        doc,
        "Adjacent to the main forecast chart, this panel solves the 'black-box AI' problem by decomposing the exact "
        "hourly price prediction into plain-English market drivers using exact TreeSHAP game-theoretic attribution.",
    )
    add_bullet(
        doc,
        "Top Summary Banner (3 Numbers): ",
        "Displays (1) Market Average Baseline (E[f(X)] = Rs. 3,873/MWh, the unconditional mean clearing price across "
        "the training history), (2) Net Market Pressure (the signed sum of all 53 feature attributions +Rs. X or -Rs. Y "
        "for that specific hour), and (3) AI Hour Forecast (Rs. 3,873 + Net Market Pressure, clipped to [0, 10000]).",
    )
    add_bullet(
        doc,
        "Top 8 Plain-English Driver Bars: ",
        "Lists the 8 most influential features for the selected hour, sorted by absolute Rupee impact (|SHAP|). Each row "
        "translates technical variable names into plain trading terminology (e.g., 'mcp_lag_24' -> 'Yesterday's Same-Hour "
        "Price', 'net_demand_mw' -> 'Net Thermal Demand (Load - Renewables)', 'market_tightness_lag_24' -> "
        "'Buyer-to-Seller Order Book Ratio'), displays the current physical reading in engineering units (GW, C, Ratio, "
        "or Rs./MWh), draws a center-zero horizontal bar extending right in Red (if it pushes price UP) or left in "
        "Green (if it pulls price DOWN), and prints the exact signed Rupee impact (+Rs. X or -Rs. Y/MWh).",
    )

    add_heading_2(doc, "3.5 Bottom-Left Card: 'Actionable Procurement & Dispatch Windows'")
    add_para(
        doc,
        "Translates the 24-hour forecast into two side-by-side operational slot grids:",
    )
    add_bullet(
        doc,
        "Green Panel — Best 4 Hours to Buy / Charge BESS: ",
        "Displays 4 clickable cards for the 4 lowest-cost hours of the day, showing the time block (e.g., 12:00 IST), "
        "predicted price in green, and national solar output in GW.",
    )
    add_bullet(
        doc,
        "Red Panel — Highest 4 Hours to Avoid / Dispatch: ",
        "Displays 4 clickable cards for the 4 highest-cost hours of the day, showing the time block (e.g., 19:00 IST), "
        "predicted price in crimson, and national net thermal load in GW.",
    )
    add_bullet(
        doc,
        "Bottom Callout — Peak-to-Trough Arbitrage Spread (4h Avg Spread): ",
        "Computes the exact spread between the mean of the 4 most expensive hours and the mean of the 4 cheapest hours "
        "(in Rs./MWh). This number represents the gross arbitrage revenue per MWh available to a BESS battery operator "
        "charging at midday and discharging in the evening, or the unit savings available to a flexible industrial buyer.",
    )

    add_heading_2(doc, "3.6 Graph 2 (Bottom-Right): 'National Renewable Generation & Net Thermal Demand (GW)'")
    add_para(
        doc,
        "This canvas (canvas-gen-mix) displays the real, synchronized physical grid telemetry from POSOCO / Grid-India "
        "for the selected date across all 24 hours:",
    )
    add_bullet(
        doc,
        "Stacked Teal Bars (Wind Generation in GW) & Stacked Gold Bars (Solar Generation in GW): ",
        "Shows exact hourly utility wind and solar power injection on the national grid. Notice how the gold solar bars "
        "rise sharply between 08:00 and 16:00 IST (reaching 28-38 GW) and vanish to 0 GW at night.",
    )
    add_bullet(
        doc,
        "Solid Blue Curve (Net Thermal Demand in GW): ",
        "Plots residual demand that must be met by dispatchable coal, gas, and hydro generators: "
        "Net Thermal Demand (GW) = Gross National Demand (GW) - Solar (GW) - Wind (GW). "
        "This curve exhibits the famous 'Duck Curve' belly during midday solar hours and a steep upward ramp between "
        "17:00 and 20:00 IST.",
    )
    add_bullet(
        doc,
        "Dashed Crimson Line (160 GW Peaker Stress Threshold): ",
        "Marks the critical 160 GW national thermal capacity inflection point. Whenever the blue Net Thermal Demand line "
        "crosses above this 160 GW dashed line, cheap pit-head coal plants are exhausted and expensive gas/imported-coal "
        "peakers must be dispatched, causing IEX clearing prices to surge toward Rs. 10,000/MWh.",
    )

    # =========================================================================
    # SECTION 4: TAB 2 — SMART PROCUREMENT & BID OPTIMIZER
    # =========================================================================
    add_heading_1(doc, "4. Workflow Tab 2: Smart Procurement & Bid Optimizer (ROI Calculator)")
    add_para(
        doc,
        "Tab 2 converts the 24-hour AI price forecast into a concrete, energy-neutral procurement schedule and an "
        "exchange-ready IEX Day-Ahead Market bid sheet. It proves the financial value (in Rupees, Lakhs, and Crores) "
        "of forecast-driven load shifting.",
    )

    add_heading_2(doc, "4.1 Four Financial ROI KPI Cards (Tab 2 Top Row)")
    add_styled_table(
        doc,
        headers=["KPI Card Title", "Formula & Financial Meaning"],
        rows=[
            [
                "1. Unoptimized Flat-Load Bill",
                "Sum_{h=0..23} (Base_MW * Pred_MCP_h), displayed in Rs. Lakhs/day. Represents what a passive buyer pays "
                "when purchasing a constant flat MW volume across all 24 hours without AI optimization.",
            ],
            [
                "2. AI-Optimized Daily Bill",
                "Sum_{h=0..23} (Optimized_MW_h * Pred_MCP_h), displayed in Rs. Lakhs/day. Represents the daily bill after "
                "shifting flexible MW out of the 6 most expensive evening hours into the 6 cheapest solar hours while "
                "delivering 100% of the exact same total daily MWh.",
            ],
            [
                "3. Net Daily Cost Savings",
                "(Unoptimized Bill - AI-Optimized Bill), displayed in Rs. Lakhs/day along with a green pill showing "
                "percentage bill reduction (-X.X% Bill) and average portfolio savings in Rs./MWh.",
            ],
            [
                "4. Projected Annualized Savings",
                "Net Daily Cost Savings * 365 days, displayed in Rs. Crores/year (1 Crore = Rs. 1,00,00,000), showing the "
                "annual bottom-line P&L impact for the selected participant profile.",
            ],
        ],
        col_widths=[2.1, 4.6],
    )

    add_heading_2(doc, "4.2 Left Panel: 'Configure Your Procurement Portfolio' (Presets & Sliders)")
    add_para(
        doc,
        "Users can select one of 4 industry participant profiles from the dropdown (which automatically loads realistic "
        "MW, flexibility, and price-cap parameters) or drag the 3 interactive sliders to match their exact plant or "
        "DISCOM portfolio:",
    )
    add_styled_table(
        doc,
        headers=["Participant Profile Preset", "Default Base Demand", "Default Flexible Load %", "Default Max Bid Price Cap"],
        rows=[
            ["Industrial Open-Access Plant (Steel / Cement / Mfg)", "100 MW (2,400 MWh/day)", "30% Shiftable", "Rs. 6,500 / MWh"],
            ["State DISCOM Utility (Portfolio Procurement Desk)", "350 MW (8,400 MWh/day)", "20% Shiftable", "Rs. 8,000 / MWh"],
            ["Grid-Scale Battery Storage (BESS Arbitrage)", "150 MW (3,600 MWh/day)", "60% Shiftable", "Rs. 5,000 / MWh"],
            ["Hyperscale Data Center / EV Fleet Hub", "80 MW (1,920 MWh/day)", "15% Shiftable", "Rs. 7,500 / MWh"],
        ],
        col_widths=[2.5, 1.5, 1.3, 1.4],
    )

    add_callout_box(
        doc,
        "MATHEMATICAL ALGORITHM: How computeBidOptimization() Works (100% Energy-Neutral LP Heuristic)",
        "Every time you move a slider or change the date, the optimizer executes a 3-step algorithm across the 24 hours:\n"
        "1. Rank Hours by AI Forecast Price: Sorts all 24 hours by pred_lightgbm. Identifies the 6 lowest-priced hours "
        "(cheapest6) and the 6 highest-priced hours (expensive6).\n"
        "2. Shave Peak Hours (expensive6): For each of the 6 most expensive hours, if pred_lightgbm <= Price_Cap, it "
        "reduces load by Flex_Pct (shaved = round(Base_MW * Flex_Frac)). If pred_lightgbm > Price_Cap, it applies "
        "aggressive cap-protection shaving: shaveRatio = min(0.75, Flex_Frac * 1.25). All shaved megawatt-hours across "
        "the 6 peak hours are summed into shavedTotalMWh.\n"
        "3. Boost Solar Hours (cheapest6): Divides shavedTotalMWh equally across the 6 cheapest solar hours: "
        "boostPerCheapHour = shavedTotalMWh / 6, so Optimized_MW = Base_MW + boostPerCheapHour.\n"
        "Result: Total 24-hour energy procured is 100% identical (Sum(Optimized_MW) == 24 * Base_MW), guaranteeing zero "
        "loss of industrial output while capturing the midday solar discount.",
    )

    add_heading_2(doc, "4.3 Graph 3: '24-Hour AI-Optimized Procurement Schedule (MW) vs. Clearing Price'")
    add_para(
        doc,
        "This dual-axis chart (canvas-bid-optimizer) visually overlays your physical MW bidding schedule against the "
        "predicted hourly clearing price:",
    )
    add_bullet(
        doc,
        "Left Y-Axis (MW Volume Bars & Dashed Flat-Load Reference Line): ",
        "The horizontal dashed gray line shows your unoptimized flat baseline load (e.g., 100 MW). The 24 vertical bars "
        "show your AI-Optimized Bid Volume for each hour, color-coded by operational action: "
        "Emerald Green Bars = 'SOLAR SHIFT BOOST' (the 6 cheapest hours where you buy extra power, e.g., 130+ MW); "
        "Blue Bars = 'STANDARD BASE' (the 12 normal hours where you buy exactly 100 MW); "
        "Crimson Red Bars = 'PEAK LOAD SHAVE' (the 6 expensive evening hours where you curtail exchange buying to "
        "62-70 MW).",
    )
    add_bullet(
        doc,
        "Right Y-Axis (Solid Gold Curve — AI Forecast Price in Rs./MWh): ",
        "Plots the 24-hour predicted clearing price trajectory. Visually, the green bars rise exactly where the gold "
        "price curve dips into the midday solar trough, and the red bars drop exactly where the gold price curve spikes "
        "during the evening peak.",
    )

    add_heading_2(doc, "4.4 Table 1: 'Generated 24-Hour IEX Day-Ahead Bid Schedule' (In-Detail Column Guide)")
    add_para(
        doc,
        "Directly below the optimizer chart sits the 24-row execution table (and the 'Download Official IEX DAM 24h Bid "
        "Sheet (.CSV)' button). Below is the exact meaning and formula of all 7 columns in this table:",
    )
    add_styled_table(
        doc,
        headers=["Column Name", "Unit / Format", "Exact Calculation & Operational Meaning for Traders"],
        rows=[
            [
                "1. Delivery Block",
                "HH:00 - HH+1:00 IST",
                "The 1-hour settlement window on Delivery Day D (from 00:00-01:00 through 23:00-00:00 IST).",
            ],
            [
                "2. AI Forecast (Rs./MWh)",
                "Rs. X,XXX",
                "The Champion LightGBM predicted Market Clearing Price (pred_lightgbm) for that delivery block.",
            ],
            [
                "3. Recommended Bid Limit",
                "Rs. X,XXX",
                "Formula: min(User_Price_Cap, min(10000, round_to_50(Upper_90%_Confidence_Band))).\n"
                "Why this matters: Because IEX DAM is a uniform-price auction, all cleared buyers pay the same Market "
                "Clearing Price regardless of their bid limit. Setting your limit order at the 90% upper confidence "
                "bound guarantees your volume clears even if actual price settles slightly above the point forecast, "
                "while still protecting you from paying above your maximum risk cap.",
            ],
            [
                "4. Flat Load (MW)",
                "XXX.X MW",
                "Your unoptimized baseline hourly demand (e.g., 100.0 MW every hour).",
            ],
            [
                "5. Optimized Bid (MW)",
                "XXX.X MW",
                "The AI-recommended MW volume to bid in this block after shifting load from peak hours to solar hours.",
            ],
            [
                "6. Dispatch Action",
                "Status Pill Badge",
                "Displays one of four operational instructions for plant/DISCOM dispatchers:\n"
                "- SOLAR SHIFT BOOST (Green): Increase demand / charge BESS / run pumps during cheap solar window.\n"
                "- STANDARD BASE (Blue): Maintain normal baseline load.\n"
                "- PEAK LOAD SHAVE (Red): Shave flexible load by Flex_Pct during evening peak.\n"
                "- CAP PROTECT / SHAVE (Red): Aggressive load curtailment when forecast exceeds your Max Price Cap.",
            ],
            [
                "7. Hourly Cost Impact",
                "Save Rs. X / Reallocated +Rs. Y",
                "Formula: Hourly_Delta_Rs = (Flat_Load_MW - Optimized_Bid_MW) * AI_Forecast_MCP.\n"
                "- In Peak Hours (where Optimized_Bid < Flat_Load): Displays green 'Save Rs. X' because you avoided "
                "buying expensive peak power (e.g., shaving 38 MW at Rs. 9,754/MWh saves Rs. 3,70,652 in one hour).\n"
                "- In Solar Hours (where Optimized_Bid > Flat_Load): Displays teal 'Reallocated +Rs. Y' because you "
                "purchased that shifted energy during the cheap solar window (e.g., buying +38 MW at Rs. 2,607/MWh "
                "costs +Rs. 99,066).\n"
                "- Net Portfolio Effect: Saving Rs. 3.71 Lakhs at 18:00 and spending +Rs. 0.99 Lakhs at 13:00 for the "
                "exact same 38 MWh nets a pure profit of Rs. 2.72 Lakhs in just that pair of hours!",
            ],
        ],
        col_widths=[1.5, 1.2, 4.0],
    )

    # =========================================================================
    # SECTION 5: TAB 3 — WEATHER & GRID RISK SIMULATOR (STRESS TESTING)
    # =========================================================================
    add_heading_1(doc, "5. Workflow Tab 3: Weather & Grid Risk Simulator (Counterfactual Stress Lab)")
    add_para(
        doc,
        "Before locking in bids at 10:30 AM IST, risk managers ask 'What-If' questions: What happens to the 18:00 IST "
        "clearing price if afternoon monsoon clouds suddenly cut national solar output by 40%? Or if a summer heatwave "
        "pushes ambient temperatures up by +4 C and national demand surges by +12%? Tab 3 provides a real-time "
        "counterfactual simulation laboratory to answer these exact questions.",
    )

    add_heading_2(doc, "5.1 Left Panel: 1-Click Shock Scenarios & 6 Physical Perturbation Sliders")
    add_para(
        doc,
        "Users can click one of the 4 pre-calibrated stress scenario buttons or manually drag any combination of the "
        "6 physical/market perturbation sliders:",
    )
    add_styled_table(
        doc,
        headers=["Control / Preset Name", "Slider Range / Settings", "Physical & Market Variables Perturbed in Backend"],
        rows=[
            [
                "Preset 1: Monsoon Cloud Cover",
                "Solar -40%, Ramp +25%, Order Book +15%",
                "Simulates sudden afternoon cloud cover collapsing solar PV injection and triggering an early thermal ramp.",
            ],
            [
                "Preset 2: Summer Heatwave",
                "Demand +12%, Wind -15%, Ramp +30%, Temp +4 C, Order Book +20%",
                "Simulates extreme heat dome with stagnant wind, soaring AC cooling load, and aggressive buyer competition.",
            ],
            [
                "Preset 3: High Renewable Surplus",
                "Demand -5%, Solar +25%, Wind +40%, Ramp -20%, Temp -2 C, Order Book -15%",
                "Simulates mild weather with strong solar and monsoon wind flooding the grid and depressing prices.",
            ],
            [
                "Preset 4: Evening Peaker Squeeze",
                "Demand +8%, Solar -15%, Wind -25%, Ramp +40%, Temp +2 C, Order Book +35%",
                "Simulates a severe evening supply crunch pushing net thermal load deep into the >160 GW peaker zone.",
            ],
            [
                "Slider 1: National Grid Demand Shift",
                "-20% to +25% (step 1%)",
                "Perturbs gross national demand (demand_mw) and propagates into net_demand_mw, re_penetration_pct, "
                "net_demand_ramp_1, net_demand_x_peak, and net_demand_x_cdd.",
            ],
            [
                "Slider 2: Solar Generation Output",
                "-60% to +50% (step 5%)",
                "Perturbs national utility solar output (solar_generation_mw) and inversely shifts net_demand_mw.",
            ],
            [
                "Slider 3: Wind Generation Output",
                "-60% to +60% (step 5%)",
                "Perturbs national utility wind output (wind_generation_mw) and inversely shifts net_demand_mw.",
            ],
            [
                "Slider 4: Evening Thermal Ramp Stress",
                "-40% to +60% (step 5%)",
                "Adds an explicit shock to 1-hour net thermal ramp velocity (net_demand_ramp_1 in MW/h).",
            ],
            [
                "Slider 5: Ambient Temperature Anomaly",
                "-5.0 C to +6.0 C (step 0.5 C)",
                "Shifts temperature_mean_c, temperature_max_c, temperature_min_c, apparent_temperature_mean_c, "
                "recomputes Cooling Degree Days cdd_24 = max(0, T - 24), quadratic temperature T^2, and net_demand_x_cdd.",
            ],
            [
                "Slider 6: Buyer-to-Seller Order Pressure",
                "-40% to +50% (step 5%)",
                "Perturbs the IEX order-book tightness ratio (market_tightness_lag_24) and scales purchase_bid_lag_24.",
            ],
        ],
        col_widths=[1.8, 1.5, 3.4],
    )

    add_heading_2(doc, "5.2 How Live Multi-Model Backend Simulation Works (POST /api/simulate)")
    add_para(
        doc,
        "Every time you move a slider in Tab 3, the frontend sends an HTTP POST request to /api/simulate, which executes "
        "run_counterfactual_simulation() in app/main.py in ~3.4 milliseconds:",
    )
    add_bullet(
        doc,
        "Step 1 — Coupled Physical State Propagation: ",
        "The backend retrieves the 53-feature vector x_t for the selected date and hour. Rather than modifying a single "
        "column in isolation (which would violate physical conservation laws), it enforces exact physical coupling: "
        "new_net_demand = new_demand - new_solar - new_wind; updates renewable share percentage; propagates the net "
        "demand change into the 1-hour ramp rate (net_demand_ramp_1); updates linear, apparent, and quadratic "
        "temperatures plus Cooling Degree Days (cdd_24); and updates the multiplicative interaction terms "
        "(net_demand_x_peak and net_demand_x_cdd).",
    )
    add_bullet(
        doc,
        "Step 2 — Live Multi-Model Forward Scoring: ",
        "The perturbed 1x53 feature vector X_sim_raw (and its Z-score standardized version X_sim_scaled) is scored live "
        "across LightGBM (self.lgb_booster.predict), XGBoost (self.xgb_model.predict), and Ridge Regression "
        "(self.ridge_model.predict), with all outputs projected onto the CERC interval [Rs. 0, Rs. 10,000/MWh].",
    )
    add_bullet(
        doc,
        "Step 3 — Live Exact TreeSHAP Re-Attribution: ",
        "Simultaneously, LightGBM's C++ TreeSHAP engine runs self.lgb_booster.predict(X_sim_raw, pred_contrib=True) to "
        "compute the exact 53-feature Shapley attribution vector under the stressed grid state, subtracting the baseline "
        "SHAP values to isolate the exact Rupee shift (delta_shap_rs) caused by your sliders.",
    )

    add_heading_2(doc, "5.3 Four Stress-Test KPI Cards (Tab 3 Top Right)")
    add_bullet(
        doc,
        "1. Baseline Hour Forecast: ",
        "Shows the original unperturbed AI forecast price (in Rs./MWh) for the target date and hour.",
    )
    add_bullet(
        doc,
        "2. Stress-Tested Forecast: ",
        "Shows the new simulated AI clearing price after applying your weather/demand shocks, along with the updated "
        "90% confidence interval.",
    )
    add_bullet(
        doc,
        "3. Net Clearing Price Shock: ",
        "Displays the signed Rupee jump or drop (+Rs. X or -Rs. Y/MWh) and percentage change vs. baseline.",
    )
    add_bullet(
        doc,
        "4. Grid Supply Regime: ",
        "Classifies the simulated net thermal load into one of the three physical regimes of the Indian power grid: "
        "'Solar Surplus (<125 GW)' in green, 'Coal Base-Load Zone (125-160 GW)' in teal, or 'Peaker Scarcity (>160 GW)' "
        "in crimson red.",
    )

    add_heading_2(doc, "5.4 Graph 4: 'National Grid Supply Stack (Merit-Order Curve) & Stress Shift'")
    add_para(
        doc,
        "This chart (canvas-sim-merit) is one of the most important economic visualizations in the platform. In "
        "electricity economics, generators are dispatched in ascending order of their marginal production cost—known as "
        "the Merit-Order Supply Stack:",
    )
    add_bullet(
        doc,
        "How the Curve Is Constructed (_build_merit_order_reference in app/main.py): ",
        "The backend partitions all 4,200 out-of-sample test hours into 28 bins across National Net Thermal Demand "
        "(X-axis, from ~95 GW to ~195 GW) and plots the empirical mean clearing price (Y-axis, from Rs. 1,500 to "
        "Rs. 10,000/MWh) alongside the mean TreeSHAP impact of net demand.",
    )
    add_bullet(
        doc,
        "The Three Economic Zones Visible on the Curve: ",
        "(1) Below 125 GW (Solar Surplus): Zero-marginal-cost solar and wind dominate; coal plants back down to "
        "technical minimums, and prices sit flat near Rs. 2,200-3,000/MWh. "
        "(2) 125 GW to 160 GW (Coal Base-Load): Domestic pit-head and rail-fed thermal coal units supply incremental "
        "load with a moderate linear slope (~Rs. 45-55/MWh per GW). "
        "(3) Above 160 GW (Shaded Crimson Zone — Peaker Scarcity Threshold): Domestic coal fleet reaches exhaustion. "
        "Meeting any additional gigawatt requires dispatching imported coal, open-cycle gas turbines, and liquid-fuel "
        "peakers, causing the supply curve to bend steeply upward toward the Rs. 10,000/MWh CERC cap.",
    )
    add_bullet(
        doc,
        "Blue Dot, Red Dot & Dashed Red Arrow: ",
        "The Blue Circle marks your Baseline Operating Point (e.g., 152 GW at Rs. 4,800/MWh). As you drag the stress "
        "sliders, the Red Circle (Stress-Tested Operating Point) and the Dashed Red Connector Arrow move dynamically "
        "along the supply stack, visually demonstrating how a solar drop or heatwave pushes the national grid across "
        "the 160 GW cliff into the crimson Peaker Scarcity Zone.",
    )

    add_heading_2(doc, "5.5 Bottom-Right Card: 'Which Market Drivers Changed Under This Stress Scenario?'")
    add_para(
        doc,
        "Lists the top 6 features whose TreeSHAP Rupee attributions shifted the most between the Baseline state and "
        "the Stress-Tested state (Baseline Impact: +Rs. A -> Simulated: +Rs. B | Net Shift: +Rs. (B - A)). This proves "
        "to an auditor that the model responds to physical shocks in strict accordance with power systems economics.",
    )

    # =========================================================================
    # SECTION 6: TAB 4 — FORECAST ACCURACY & MODEL TRUST SCORECARD
    # =========================================================================
    add_heading_1(doc, "6. Workflow Tab 4: Forecast Accuracy & Model Trust Scorecard")
    add_para(
        doc,
        "Tab 4 is the quantitative validation and econometric auditing center. It presents the verified out-of-sample "
        "benchmark results across all 4,200 unseen test hours (175 days from Jan 2025 to Jun 2025) so institutional "
        "traders and academic examiners can verify why LightGBM was selected as the production champion.",
    )

    add_heading_2(doc, "6.1 Four Verification Summary KPI Cards (Tab 4 Top Row)")
    add_bullet(
        doc,
        "1. Out-of-Sample Accuracy (R-Squared = 93.2%): ",
        "LightGBM explains 93.17% of the total variance in unseen IEX Day-Ahead Market clearing prices.",
    )
    add_bullet(
        doc,
        "2. Average Forecast Error (Rs. 433/MWh | Rs. 0.43/kWh): ",
        "Out-of-sample Mean Absolute Error across all 4,200 test hours—equivalent to just 43 paise per kWh unit.",
    )
    add_bullet(
        doc,
        "3. Gain vs. Market Baseline (+34.2% Skill | -Rs. 225/MWh Error): ",
        "Reduces forecast error by 34.19% compared to the standard 24-hour Seasonal Naive market baseline (Rs. 658.42/MWh).",
    )
    add_bullet(
        doc,
        "4. Data Coverage & Signals (53 Signals | 5 Live Streams): ",
        "Synthesizes 53 strictly causal features across IEX DAM auctions, Grid-India SCADA load, utility solar/wind "
        "generation, 5-zone ERA5 meteorology, and Fourier calendar harmonics.",
    )

    add_heading_2(doc, "6.2 Graph 5 (Left): 'Hourly Forecast Accuracy Across the 24-Hour Day (MAE in Rs./MWh)'")
    add_para(
        doc,
        "This chart (canvas-trust-accuracy, built by _build_hourly_error_profiles() in app/main.py) plots the average "
        "Mean Absolute Error (MAE in Rs./MWh) for each of the 24 hours of the day (00:00 to 23:00 IST) across three "
        "tier representatives:",
    )
    add_bullet(
        doc,
        "Dashed Crimson Curve — Yesterday Same-Hour Baseline (24h Seasonal Naive): ",
        "Shows high error during midday solar transitions (~Rs. 650-750/MWh) and extreme error during the 18:00-22:00 "
        "evening peak (~Rs. 900-1,150/MWh) because yesterday's price cannot anticipate today's cloud cover or load ramp.",
    )
    add_bullet(
        doc,
        "Solid Blue Curve — Linear Econometric Baseline (Ridge Regression alpha=50): ",
        "Improves over naive persistence by incorporating weather and load covariates, but still suffers high error "
        "during evening peaks because a linear hyperplane cannot capture the sharp 160 GW merit-order bend.",
    )
    add_bullet(
        doc,
        "Solid Teal Curve — EnergyCast AI Production Engine (LightGBM): ",
        "Sits lowest across all 24 hours of the day, achieving its largest skill advantage (+35% to +42% error "
        "reduction) during volatile solar transition and evening peak ramp hours.",
    )

    add_heading_2(doc, "6.3 Graph 6 (Right): 'Top 12 Market Signals Powering the Forecast Engine'")
    add_para(
        doc,
        "This horizontal bar chart (canvas-trust-signals) ranks the top 12 features out of all 53 signals by their "
        "Global Mean Absolute TreeSHAP Attribution (Mean |SHAP| in Rs./MWh) across all 4,200 test hours:",
    )
    add_styled_table(
        doc,
        headers=["Rank", "Plain-English Signal Name (Raw Feature)", "Category", "Mean |SHAP| (Rs./MWh)", "Physical / Economic Role"],
        rows=[
            ["#1", "Previous Hour Clearing Price (mcp_lag_1)", "Price Memory", "Rs. 994.75", "Captures immediate intraday price regime persistence."],
            ["#2", "1-Hour Thermal Ramp Stress (net_demand_ramp_1)", "Physical Grid", "Rs. 253.83", "Captures evening solar drop & fast thermal ramping."],
            ["#3", "Diurnal Price Ramp Slope (mcp_diff_24_25)", "Price Memory", "Rs. 244.71", "Captures yesterday's exact hour-over-hour price velocity."],
            ["#4", "Yesterday's Same-Hour Price (mcp_lag_24)", "Price Memory", "Rs. 235.15", "24-hour diurnal auction baseline anchor."],
            ["#5", "Buyer-to-Seller Order Ratio (market_tightness_lag_24)", "Order Book", "Rs. 122.41", "Ratio of purchase bids to sell offers (>1.0 = scarcity)."],
            ["#6", "Net Thermal Demand (net_demand_mw)", "Physical Grid", "Rs. 88.24", "Residual load (Demand - Solar - Wind) on supply stack."],
            ["#7", "2-Days Ago Same-Hour Price (mcp_lag_48)", "Price Memory", "Rs. 59.35", "48-hour recurring diurnal price anchor."],
            ["#8", "1-Hour Price Acceleration (mcp_diff_1_2)", "Price Memory", "Rs. 56.50", "Short-term momentum acceleration."],
            ["#9", "Last Week's Same-Hour Price (mcp_lag_168)", "Price Memory", "Rs. 54.09", "7-day weekly industrial/weekend cycle anchor."],
            ["#10", "Exchange Purchase Bid Volume (purchase_bid_lag_24)", "Order Book", "Rs. 45.40", "Aggregate buy-side demand bid volume on IEX."],
            ["#11", "24-Hour Solar Floor Price (mcp_rolling_min_24)", "Price Memory", "Rs. 42.16", "Depth of preceding midday solar price trough."],
            ["#12", "7-Day Rolling Average Price (mcp_rolling_mean_168)", "Price Memory", "Rs. 36.74", "Weekly macro clearing price regime."],
        ],
        col_widths=[0.5, 2.2, 1.1, 1.1, 1.8],
    )

    add_heading_2(doc, "6.4 Table 2: 'Verified Out-of-Sample Accuracy Scorecard (4,200 Hours)' — In-Detail Guide")
    add_para(
        doc,
        "At the bottom of Tab 4 sits the master model comparison table (populated from master_model_leaderboard.csv). "
        "It compares all 7 models across 3 modeling tiers on the 4,200 unseen test hours:",
    )
    add_styled_table(
        doc,
        headers=[
            "Forecasting Engine / Baseline",
            "Category (Tier)",
            "Avg Error (MAE)",
            "Per-Unit Error",
            "RMSE",
            "Variance (R2)",
            "Gain vs. 24h Baseline",
            "Status",
        ],
        rows=[
            [
                "EnergyCast AI Production Engine (LightGBM, 282 Trees)",
                "Production AI (Tier 3)",
                "Rs. 433.33 / MWh",
                "Rs. 0.43 / kWh",
                "Rs. 703.43",
                "93.17%",
                "+34.19% More Accurate",
                "ACTIVE PRODUCTION",
            ],
            [
                "XGBoost Ensemble Challenger (268 Trees, Depth 6)",
                "Tree Ensemble (Tier 3)",
                "Rs. 446.63 / MWh",
                "Rs. 0.45 / kWh",
                "Rs. 720.30",
                "92.83%",
                "+32.17% More Accurate",
                "Secondary Challenger",
            ],
            [
                "1-Hour Rolling Persistence (mcp_lag_1)",
                "Intraday Ref (Tier 1)",
                "Rs. 512.01 / MWh",
                "Rs. 0.51 / kWh",
                "Rs. 897.81",
                "88.87%",
                "+22.24% (Intraday Only)",
                "Intraday Only",
            ],
            [
                "L2-Regularized Econometric Model (Ridge alpha=50)",
                "Linear Parametric (Tier 2)",
                "Rs. 544.61 / MWh",
                "Rs. 0.54 / kWh",
                "Rs. 764.61",
                "91.93%",
                "+17.29% More Accurate",
                "Benchmark Only",
            ],
            [
                "Standard Linear Regression (OLS)",
                "Linear Parametric (Tier 2)",
                "Rs. 545.67 / MWh",
                "Rs. 0.55 / kWh",
                "Rs. 764.86",
                "91.92%",
                "+17.12% More Accurate",
                "Benchmark Only",
            ],
            [
                "Yesterday Same-Hour Price (24h Seasonal Naive)",
                "Market Baseline (Tier 1)",
                "Rs. 658.42 / MWh",
                "Rs. 0.66 / kWh",
                "Rs. 1,173.40",
                "80.99%",
                "Baseline (0.0%)",
                "Industry Baseline",
            ],
            [
                "Last Week Same-Hour Price (168h Weekly Naive)",
                "Weekly Baseline (Tier 1)",
                "Rs. 784.08 / MWh",
                "Rs. 0.78 / kWh",
                "Rs. 1,372.42",
                "74.00%",
                "-19.08% Worse",
                "Benchmark Only",
            ],
        ],
        col_widths=[1.6, 0.9, 0.85, 0.75, 0.75, 0.65, 0.9, 0.8],
    )

    add_callout_box(
        doc,
        "HOW THE SCORECARD TABLE RELATES TO LIVE BACKEND INFERENCE",
        "1. What is Fixed vs. Live: The summary metrics in the Tab 4 Scorecard Table (e.g., MAE = Rs. 433.33/MWh, "
        "RMSE = Rs. 703.43/MWh, R2 = 93.17%) are the fixed, verified out-of-sample benchmark scores evaluated across all "
        "4,200 hours of the test set (Jan-Jun 2025), backed by Newey-West HAC Diebold-Mariano statistical tests "
        "(DM = -7.78, p = 9.10e-15 vs. 24h Naive; DM = -10.45, p < 1e-20 vs. Ridge).\n"
        "2. How All Models Run at the Backend: When the backend server starts (app/main.py lines 131-161), it loads the "
        "actual trained model binaries for LightGBM, XGBoost, Ridge, OLS, and the Naive baselines into memory, scores "
        "every hour of the dataset, and—whenever you adjust any weather or demand slider in Tab 3—executes live forward "
        "inference across LightGBM, XGBoost, and Ridge simultaneously in ~3.4 milliseconds!",
    )

    # =========================================================================
    # SECTION 7: VIVA / PROJECT DEMONSTRATION QUICK-REFERENCE FAQ
    # =========================================================================
    add_heading_1(doc, "7. Viva & Project Demonstration Quick-Reference Q&A")
    add_para(
        doc,
        "Use these concise, technically rigorous answers when demonstrating the website to professors, external "
        "examiners, or industry interviewers:",
    )
    add_bullet(
        doc,
        "Q1: Are the numbers in the website hardcoded or computed by real ML models? ",
        "Answer: Nothing is hardcoded. The backend loads the actual trained LightGBM (282 trees), XGBoost (268 trees), "
        "and Ridge Regression (alpha=50) model artifacts (.joblib) and the 28,176-hour dataset. All hourly predictions, "
        "TreeSHAP Rupee attributions, LP bid schedules, and counterfactual stress-test simulations are computed "
        "mathematically from the 53-feature vectors.",
    )
    add_bullet(
        doc,
        "Q2: How do you guarantee there is no data leakage (look-ahead bias) in the day-ahead forecast? ",
        "Answer: In the real IEX Day-Ahead Market, bids for all 24 hours of tomorrow (Day D) must be submitted before "
        "10:30 AM IST today (Day D-1). Therefore, our feature pipeline enforces a strict 10:30 AM IST causal firewall: "
        "all exchange order-book features (purchase bids, sell bids, cleared volume, market tightness) use a minimum "
        "24-hour lag, and all chronological splits (Train: 2022-2023, Val: 2024, Test: 2025) are strictly forward-in-time "
        "with zero random shuffling.",
    )
    add_bullet(
        doc,
        "Q3: Why does LightGBM beat Linear/Ridge Regression by over 20% (Rs. 433 vs. Rs. 545/MWh)? ",
        "Answer: Because the Indian power grid's Merit-Order Supply Stack is highly non-linear. Below 160 GW of net "
        "thermal load, domestic coal supplies electricity at a gentle linear slope (~Rs. 50/MWh per GW). Above 160 GW, "
        "coal is exhausted and expensive gas/imported-coal peakers cause prices to jump vertically toward the Rs. 10,000 "
        "CERC cap. Linear models cannot bend at 160 GW, whereas tree ensembles partition the 160 GW regime boundary "
        "and capture multiplicative interactions between evening peak hours, ramp rates, and order-book tightness.",
    )
    add_bullet(
        doc,
        "Q4: How does a DISCOM or industrial plant actually save money using Tab 2? ",
        "Answer: By shifting flexible load (e.g., 20-30% of demand from water pumping, grinding mills, thermal storage, "
        "or BESS charging) out of the 6 highest-priced evening peak hours (Rs. 8,000-10,000/MWh) into the 6 lowest-priced "
        "midday solar hours (Rs. 2,400-2,800/MWh). Total daily energy (MWh) stays 100% unchanged, reducing the daily "
        "electricity bill by 8% to 14% (over Rs. 12.7 Lakhs/day for a 100 MW industrial plant on peak scarcity days).",
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_PATH))
    print(f"[OK] Successfully generated Word document: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_document()
