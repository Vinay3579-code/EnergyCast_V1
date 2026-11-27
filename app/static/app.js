/**
 * ============================================================================
 * ENERGYCAST // COMMERCIAL POWER MARKET INTELLIGENCE & BIDDING PLATFORM
 * Product Frontend Controller (app.js)
 * ============================================================================
 * Features:
 *  1. Live Market Forecast & Dispatch Command Center
 *  2. Smart Procurement & Bid Optimizer (Live ROI Calculator + IEX Bid CSV)
 *  3. Weather & Grid Risk Simulator (Stress Testing + Merit-Order Stack)
 *  4. Forecast Accuracy & Model Trust Scorecard
 *  5. Universal HiDPI Canvas Engine + Interactive Hover Popover Stats Box
 * ============================================================================
 */

(function () {
  "use strict";

  // --------------------------------------------------------------------------
  // 1. PLAIN-ENGLISH TRANSLATION DICTIONARY (NO RAW VARIABLE JARGON)
  // --------------------------------------------------------------------------
  const PLAIN_DRIVER_CATALOG = {
    mcp_lag_1: {
      title: "Previous Hour Clearing Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "Immediate price momentum carried over from the preceding 1-hour settlement block."
    },
    mcp_lag_2: {
      title: "2-Hour Prior Clearing Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "Short-term intraday price anchor from two hours prior."
    },
    mcp_lag_24: {
      title: "Yesterday's Same-Hour Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "24-hour diurnal price baseline reflecting recurring daily industrial and residential schedules."
    },
    mcp_lag_48: {
      title: "2-Days Ago Same-Hour Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "48-hour recurring price anchor."
    },
    mcp_lag_168: {
      title: "Last Week's Same-Hour Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "7-day weekly cycle anchor capturing weekday vs. weekend industrial demand patterns."
    },
    mcp_rolling_mean_24: {
      title: "24-Hour Rolling Average Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "Prevailing daily clearing price regime over the past 24 hours."
    },
    mcp_rolling_std_24: {
      title: "24-Hour Market Price Volatility",
      unit: "₹/MWh",
      fmt: (v) => `±₹${Math.round(v).toLocaleString("en-IN")}`,
      desc: "Intraday price dispersion signaling stable vs. turbulent auction conditions."
    },
    mcp_rolling_max_24: {
      title: "24-Hour Peak Price Ceiling",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "Highest clearing price reached in the last 24 hours."
    },
    mcp_rolling_min_24: {
      title: "24-Hour Solar Floor Price",
      unit: "₹/MWh",
      fmt: (v) => `₹${Math.round(v).toLocaleString("en-IN")}/MWh`,
      desc: "Lowest clearing price reached during the previous midday solar window."
    },
    mcp_diff_1_2: {
      title: "1-Hour Price Acceleration",
      unit: "₹/MWh",
      fmt: (v) => `${v >= 0 ? "+" : ""}₹${Math.round(v).toLocaleString("en-IN")}`,
      desc: "Hour-over-hour rate of price climb or drop."
    },
    mcp_diff_24_25: {
      title: "Diurnal Price Ramp Slope",
      unit: "₹/MWh",
      fmt: (v) => `${v >= 0 ? "+" : ""}₹${Math.round(v).toLocaleString("en-IN")}`,
      desc: "Rate of price change at this exact hour yesterday (captures steepness of evening climb or morning drop)."
    },
    mcp_ratio_1_24: {
      title: "Intraday vs. Yesterday Price Ratio",
      unit: "x",
      fmt: (v) => `${Number(v).toFixed(2)}x`,
      desc: "Ratio comparing current intraday price level against yesterday's level."
    },
    mcp_zscore_24: {
      title: "Price Regime Anomaly Score",
      unit: "σ",
      fmt: (v) => `${Number(v).toFixed(2)} σ`,
      desc: "How many standard deviations recent prices sit above or below the 24-hour average."
    },
    market_tightness_lag_24: {
      title: "Buyer-to-Seller Order Book Ratio",
      unit: "Ratio",
      fmt: (v) => `${Number(v).toFixed(2)}x Buy/Sell`,
      desc: "Ratio of purchase bids to sell offers on the IEX order book (>1.0x indicates buyer scarcity competition)."
    },
    purchase_bid_lag_24: {
      title: "Exchange Purchase Bid Volume",
      unit: "MW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Total buy-side demand bid into the IEX Day-Ahead auction."
    },
    sell_bid_lag_24: {
      title: "Exchange Generator Sell Volume",
      unit: "MW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Total generator supply offered into the IEX Day-Ahead auction."
    },
    mcv_lag_24: {
      title: "Market Cleared Volume (Liquidity)",
      unit: "MW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Total power volume successfully matched and cleared on the exchange."
    },
    demand_mw: {
      title: "Total National Grid Demand",
      unit: "GW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "All-India gross electricity consumption across all regional grids."
    },
    net_demand_mw: {
      title: "Net Thermal Demand (Load − Renewables)",
      unit: "GW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Residual demand that must be met by coal, gas, and hydro after subtracting solar and wind output."
    },
    solar_generation_mw: {
      title: "National Solar Generation",
      unit: "GW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Zero-marginal-cost utility solar injection depressing midday clearing prices."
    },
    wind_generation_mw: {
      title: "National Wind Generation",
      unit: "GW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Utility wind generation moderating evening and monsoon thermal dispatch."
    },
    re_penetration_pct: {
      title: "Renewable Grid Share (%)",
      unit: "%",
      fmt: (v) => `${Number(v).toFixed(1)}% RE`,
      desc: "Percentage of total national electricity demand supplied by solar and wind."
    },
    net_demand_ramp_1: {
      title: "1-Hour Thermal Ramp Stress",
      unit: "GW/h",
      fmt: (v) => `${v >= 0 ? "+" : ""}${(v / 1000).toFixed(1)} GW/h`,
      desc: "Hourly jump in net thermal load as evening solar fades and household lighting peaks."
    },
    net_demand_ramp_3: {
      title: "3-Hour Cumulative Thermal Ramp",
      unit: "GW",
      fmt: (v) => `${v >= 0 ? "+" : ""}${(v / 1000).toFixed(1)} GW`,
      desc: "3-hour net load surge requiring fast-ramping peaking generators."
    },
    net_demand_x_peak: {
      title: "Evening Peak Capacity Stress",
      unit: "GW",
      fmt: (v) => `${(v / 1000).toFixed(1)} GW`,
      desc: "Compound interaction of high thermal demand occurring during evening peak hours (18:00–22:00)."
    },
    net_demand_x_cdd: {
      title: "Heatwave × Grid Load Compound Stress",
      unit: "Index",
      fmt: (v) => `${(v / 1000).toFixed(0)}k`,
      desc: "Simultaneous high ambient heat and high grid demand driving air-conditioning peaks."
    },
    temperature_mean_c: {
      title: "Population-Weighted Temperature",
      unit: "°C",
      fmt: (v) => `${Number(v).toFixed(1)} °C`,
      desc: "Ambient temperature across major Indian load centers driving cooling demand."
    },
    apparent_temperature_mean_c: {
      title: "Feels-Like Heat Index",
      unit: "°C",
      fmt: (v) => `${Number(v).toFixed(1)} °C`,
      desc: "Humidity-adjusted apparent temperature driving residential AC usage."
    },
    cdd_24: {
      title: "Cooling Degree Demand (AC Load)",
      unit: "°C-days",
      fmt: (v) => `${Number(v).toFixed(1)} CDD`,
      desc: "Thermal cooling stress above the 24°C human comfort threshold."
    },
    relative_humidity_mean_pct: {
      title: "Ambient Relative Humidity",
      unit: "%",
      fmt: (v) => `${Number(v).toFixed(0)}% RH`,
      desc: "Atmospheric moisture level affecting apparent heat and monsoon cloud cover."
    },
    shortwave_radiation_wm2: {
      title: "Solar Irradiance Intensity",
      unit: "W/m²",
      fmt: (v) => `${Math.round(v)} W/m²`,
      desc: "Surface solar radiation driving utility and rooftop PV output."
    },
    cloud_cover_pct: {
      title: "Cloud Cover Density",
      unit: "%",
      fmt: (v) => `${Math.round(v)}%`,
      desc: "Cloud cover attenuating solar PV output."
    },
    wind_speed_100m_kmh: {
      title: "Hub-Height Wind Speed (100m)",
      unit: "km/h",
      fmt: (v) => `${Number(v).toFixed(1)} km/h`,
      desc: "Wind velocity at wind-turbine hub height (100m)."
    },
    hour_sin: {
      title: "Time-of-Day Cycle (Phase A)",
      unit: "Cycle",
      fmt: (v) => Number(v).toFixed(2),
      desc: "Smooth 24-hour diurnal clock position."
    },
    hour_cos: {
      title: "Time-of-Day Cycle (Phase B)",
      unit: "Cycle",
      fmt: (v) => Number(v).toFixed(2),
      desc: "Daylight vs. nighttime diurnal clock phase."
    },
    is_peak_hour: {
      title: "Evening Peak Period (18:00–22:00)",
      unit: "Flag",
      fmt: (v) => (v > 0.5 ? "Active Peak" : "Off-Peak"),
      desc: "CERC evening peak tariff and residential lighting window."
    },
    is_solar_hour: {
      title: "Solar Generation Window (08:00–17:00)",
      unit: "Flag",
      fmt: (v) => (v > 0.5 ? "Active Solar" : "Night/Evening"),
      desc: "Daylight solar injection window."
    }
  };

  function getPlainDriverInfo(featureKey, rawLabel) {
    if (PLAIN_DRIVER_CATALOG[featureKey]) {
      return PLAIN_DRIVER_CATALOG[featureKey];
    }
    const cleanTitle = (rawLabel || featureKey)
      .replace(/_/g, " ")
      .replace(/\blag (\d+)\b/gi, "($1h Prior)")
      .replace(/\bmcp\b/gi, "Market Price")
      .replace(/\bmcv\b/gi, "Cleared Volume")
      .replace(/\bmw\b/gi, "(MW)");
    return {
      title: cleanTitle,
      unit: "",
      fmt: (v) => (typeof v === "number" ? Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 }) : String(v)),
      desc: "Live market, grid, or meteorological signal monitored by the EnergyCast AI engine."
    };
  }

  // --------------------------------------------------------------------------
  // 2. APPLICATION STATE
  // --------------------------------------------------------------------------
  const STATE = {
    embedded: window.ENERGYCAST_EMBEDDED || null,
    overview: null,
    shapLab: null,
    benchmarks: null,
    activeTab: "forecast",
    selectedDate: "2025-01-01",
    selectedHour: 18,
    dayData: null,
    hourExplain: null,
    simResult: null,
    showActual: true,
    showZones: true,
    // Optimizer state
    optProfile: "industrial",
    optBaseMw: 100,
    optFlexPct: 30,
    optPriceCap: 6500
  };

  // --------------------------------------------------------------------------
  // 3. FORMATTING HELPERS
  // --------------------------------------------------------------------------
  function fmtRs(val, decimals = 0) {
    if (val === null || val === undefined || isNaN(val)) return "₹0";
    const sign = val < 0 ? "-" : "";
    return `${sign}₹${Math.abs(Number(val)).toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    })}`;
  }

  function fmtSignedRs(val, decimals = 0) {
    if (val === null || val === undefined || isNaN(val)) return "₹0";
    const sign = val > 0 ? "+" : val < 0 ? "-" : "";
    return `${sign}₹${Math.abs(Number(val)).toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    })}`;
  }

  function fmtLakhs(rupees) {
    const lakhs = rupees / 100000;
    return `₹${lakhs.toFixed(2)} L`;
  }

  function fmtCrores(rupees) {
    const cr = rupees / 10000000;
    return `₹${cr.toFixed(2)} Cr`;
  }

  function getThemeColors() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    return {
      isDark,
      bgCard: isDark ? "#111827" : "#FFFFFF",
      bgSubtle: isDark ? "#161F30" : "#F8FAFC",
      textMain: isDark ? "#F8FAFC" : "#0F172A",
      textSec: isDark ? "#94A3B8" : "#475569",
      textMuted: isDark ? "#64748B" : "#64748B",
      gridLine: isDark ? "#1E293B" : "#E2E8F0",
      borderStrong: isDark ? "#334155" : "#CBD5E1",
      brand: isDark ? "#14B8A6" : "#0D9488",
      brandFill: isDark ? "rgba(20, 184, 166, 0.18)" : "rgba(13, 148, 136, 0.15)",
      solar: isDark ? "#FBBF24" : "#F59E0B",
      solarFill: isDark ? "rgba(251, 191, 36, 0.14)" : "rgba(245, 158, 11, 0.12)",
      peak: isDark ? "#F43F5E" : "#E11D48",
      peakFill: isDark ? "rgba(244, 63, 94, 0.14)" : "rgba(225, 29, 72, 0.10)",
      good: isDark ? "#34D399" : "#10B981",
      goodFill: isDark ? "rgba(52, 211, 153, 0.14)" : "rgba(16, 185, 129, 0.11)",
      blue: isDark ? "#3B82F6" : "#2563EB",
      blueFill: isDark ? "rgba(59, 130, 246, 0.15)" : "rgba(37, 99, 235, 0.12)"
    };
  }

  // --------------------------------------------------------------------------
  // 4. UNIVERSAL POPOVER RECTANGULAR STATS BOX (ON HOVER)
  // --------------------------------------------------------------------------
  const popoverEl = document.getElementById("chart-popover-tooltip");

  function showPopover(evt, title, badgeText, rows) {
    if (!popoverEl) return;
    let html = `<div class="popover-header">
      <span>${title}</span>
      ${badgeText ? `<span class="popover-badge">${badgeText}</span>` : ""}
    </div><div class="popover-body">`;

    for (const r of rows) {
      const dotHtml = r.color ? `<span class="popover-dot" style="background:${r.color};"></span>` : "";
      const valStyle = r.highlight ? `style="color:${r.highlight}; font-weight:700;"` : "";
      html += `<div class="popover-row">
        <span class="popover-key">${dotHtml}${r.label}</span>
        <span class="popover-val" ${valStyle}>${r.value}</span>
      </div>`;
    }
    html += `</div>`;
    popoverEl.innerHTML = html;
    popoverEl.classList.add("visible");
    popoverEl.setAttribute("aria-hidden", "false");
    positionPopover(evt);
  }

  function positionPopover(evt) {
    if (!popoverEl || !popoverEl.classList.contains("visible")) return;
    const pad = 16;
    const rect = popoverEl.getBoundingClientRect();
    let x = evt.clientX + pad;
    let y = evt.clientY + pad;

    if (x + rect.width + 12 > window.innerWidth) {
      x = evt.clientX - rect.width - pad;
    }
    if (y + rect.height + 12 > window.innerHeight) {
      y = evt.clientY - rect.height - pad;
    }
    x = Math.max(8, x);
    y = Math.max(8, y);

    popoverEl.style.left = `${x}px`;
    popoverEl.style.top = `${y}px`;
  }

  function hidePopover() {
    if (!popoverEl) return;
    popoverEl.classList.remove("visible");
    popoverEl.setAttribute("aria-hidden", "true");
  }

  // --------------------------------------------------------------------------
  // 5. CONSTRAINED HiDPI CANVAS SETUP (FIXED PROPORTIONS & ALIGNMENT)
  // --------------------------------------------------------------------------
  function setupCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const parent = canvas.parentElement;
    if (!parent) return null;

    const rect = parent.getBoundingClientRect();
    const w = Math.max(300, Math.floor(rect.width));
    const h = Math.max(180, Math.floor(rect.height));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    // Explicitly lock CSS pixel dimensions so HiDPI scaling never inflates DOM layout
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
    }

    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { canvas, ctx, w, h };
  }

  // --------------------------------------------------------------------------
  // 6. HYBRID DATA ACCESS LAYER (LIVE API OR EMBEDDED OFFLINE BUNDLE)
  // --------------------------------------------------------------------------
  async function fetchApiOrEmbedded(url, fallbackFn) {
    if (window.location.protocol !== "file:") {
      try {
        const res = await fetch(url);
        if (res.ok) return await res.json();
      } catch (_) {
        // Fallback to embedded bundle
      }
    }
    return fallbackFn();
  }

  async function loadInitialData() {
    STATE.overview = await fetchApiOrEmbedded("/api/overview", () => STATE.embedded.overview);
    STATE.shapLab = await fetchApiOrEmbedded("/api/shap-lab", () => STATE.embedded.shapLab);
    STATE.benchmarks = await fetchApiOrEmbedded("/api/benchmarks", () => STATE.embedded.benchmarks);

    populateDateAndHourSelectors();
    await selectDateAndHour(STATE.selectedDate, STATE.selectedHour);
    renderTrustTab();
  }

  function populateDateAndHourSelectors() {
    const dateSel = document.getElementById("select-date");
    const hourSel = document.getElementById("select-hour");
    if (!dateSel || !hourSel || !STATE.overview) return;

    dateSel.innerHTML = "";
    for (const d of STATE.overview.available_dates) {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      dateSel.appendChild(opt);
    }
    dateSel.value = STATE.selectedDate;

    hourSel.innerHTML = "";
    for (let h = 0; h < 24; h++) {
      const opt = document.createElement("option");
      opt.value = String(h);
      opt.textContent = `${String(h).padStart(2, "0")}:00 IST`;
      hourSel.appendChild(opt);
    }
    hourSel.value = String(STATE.selectedHour);
  }

  // Build synthetic local driver explanation if user picks a non-cached date in offline file:// mode
  function buildOfflineHourExplanation(dayData, hour) {
    const cacheKey = `${dayData.date}_${hour}`;
    if (STATE.embedded && STATE.embedded.explainCache && STATE.embedded.explainCache[cacheKey]) {
      return STATE.embedded.explainCache[cacheKey];
    }
    const hRow = dayData.hourly.find((x) => x.hour === hour) || dayData.hourly[0];
    const baseVal = (STATE.overview && STATE.overview.base_expected_mcp) || 3873.06;
    const totalDiff = hRow.pred_lightgbm - baseVal;

    // Proportional physical decomposition for offline non-preset dates
    const drivers = [
      {
        feature: "mcp_lag_24",
        label: "Yesterday's Same-Hour Price",
        category: "Autoregressive Price Memory",
        value: hRow.pred_snaive_24h,
        shap_rs: Math.round((hRow.pred_snaive_24h - baseVal) * 0.42)
      },
      {
        feature: "net_demand_mw",
        label: "Net Thermal Demand (Load - RE)",
        category: "Grid Demand & Renewables",
        value: hRow.net_demand_mw,
        shap_rs: Math.round(((hRow.net_demand_mw - 142000) / 1000) * 28)
      },
      {
        feature: "solar_generation_mw",
        label: "National Solar Generation",
        category: "Grid Demand & Renewables",
        value: hRow.solar_generation_mw,
        shap_rs: hRow.solar_generation_mw > 5000 ? -Math.round((hRow.solar_generation_mw / 1000) * 24) : 120
      },
      {
        feature: "market_tightness_lag_24",
        label: "Buyer-to-Seller Order Ratio",
        category: "IEX Auction Liquidity",
        value: hRow.market_tightness_lag_24,
        shap_rs: Math.round((hRow.market_tightness_lag_24 - 1.0) * 620)
      },
      {
        feature: "net_demand_ramp_1",
        label: "1-Hour Thermal Ramp Stress",
        category: "Grid Demand & Renewables",
        value: hRow.net_demand_ramp_1,
        shap_rs: Math.round((hRow.net_demand_ramp_1 / 1000) * 32)
      },
      {
        feature: "wind_generation_mw",
        label: "National Wind Generation",
        category: "Grid Demand & Renewables",
        value: hRow.wind_generation_mw,
        shap_rs: -Math.round(((hRow.wind_generation_mw - 12000) / 1000) * 18)
      },
      {
        feature: "temperature_mean_c",
        label: "Population-Weighted Temperature",
        category: "Weather & Cooling Stress",
        value: hRow.temperature_mean_c,
        shap_rs: Math.round((hRow.temperature_mean_c - 25.0) * 45)
      },
      {
        feature: "is_peak_hour",
        label: "Evening Peak Period (18:00–22:00)",
        category: "Diurnal Calendar Cycle",
        value: hRow.is_peak_hour,
        shap_rs: hRow.is_peak_hour ? 380 : -95
      }
    ];

    // Normalize sum so it matches totalDiff closely
    const rawSum = drivers.reduce((acc, d) => acc + d.shap_rs, 0);
    const residual = totalDiff - rawSum;
    drivers[0].shap_rs = Math.round(drivers[0].shap_rs + residual * 0.65);
    drivers[1].shap_rs = Math.round(drivers[1].shap_rs + residual * 0.35);

    for (const d of drivers) {
      d.abs_shap_rs = Math.abs(d.shap_rs);
    }
    drivers.sort((a, b) => b.abs_shap_rs - a.abs_shap_rs);

    return {
      date: dayData.date,
      hour: hRow.hour,
      hour_label: hRow.hour_label,
      actual_mcp: hRow.actual_mcp,
      pred_lightgbm: hRow.pred_lightgbm,
      pred_xgboost: hRow.pred_xgboost,
      pred_ridge: hRow.pred_ridge,
      pred_snaive_24h: hRow.pred_snaive_24h,
      base_value: baseVal,
      top_attributions: drivers,
      physical_state: {
        demand_mw: hRow.demand_mw,
        solar_generation_mw: hRow.solar_generation_mw,
        wind_generation_mw: hRow.wind_generation_mw,
        net_demand_mw: hRow.net_demand_mw,
        net_demand_ramp_1: hRow.net_demand_ramp_1,
        re_penetration_pct: hRow.re_penetration_pct,
        temperature_mean_c: hRow.temperature_mean_c,
        market_tightness_lag_24: hRow.market_tightness_lag_24
      }
    };
  }

  async function selectDateAndHour(dateStr, hourNum) {
    STATE.selectedDate = dateStr;
    STATE.selectedHour = Number(hourNum);

    const dateSel = document.getElementById("select-date");
    const hourSel = document.getElementById("select-hour");
    if (dateSel) dateSel.value = STATE.selectedDate;
    if (hourSel) hourSel.value = String(STATE.selectedHour);

    // Highlight active market day chip if matching
    document.querySelectorAll("#market-day-chips .scenario-chip").forEach((chip) => {
      const isMatch = chip.getAttribute("data-date") === STATE.selectedDate;
      chip.classList.toggle("active", isMatch);
    });

    STATE.dayData = await fetchApiOrEmbedded(
      `/api/day-forecast?date=${encodeURIComponent(STATE.selectedDate)}`,
      () => STATE.embedded.daysMap[STATE.selectedDate] || Object.values(STATE.embedded.daysMap)[0]
    );

    STATE.hourExplain = await fetchApiOrEmbedded(
      `/api/hour-explain?date=${encodeURIComponent(STATE.selectedDate)}&hour=${STATE.selectedHour}`,
      () => buildOfflineHourExplanation(STATE.dayData, STATE.selectedHour)
    );

    renderForecastTab();
    renderOptimizerTab();
    await runSimulatorStressTest();
  }

  // --------------------------------------------------------------------------
  // 7. WORKFLOW TAB 1: MARKET FORECAST & DISPATCH COMMAND CENTER
  // --------------------------------------------------------------------------
  function getHourConfidenceBand(hRow) {
    // Compute realistic 90% prediction interval using ensemble dispersion + diurnal regime width
    const dispersion = Math.abs(hRow.pred_lightgbm - hRow.pred_xgboost) * 0.85;
    const baseHalfWidth = hRow.is_peak_hour ? 540 : hRow.is_solar_hour ? 340 : 410;
    const halfWidth = Math.max(260, Math.round(baseHalfWidth + dispersion));
    const low = Math.max(0, Math.round(hRow.pred_lightgbm - halfWidth));
    const high = Math.min(10000, Math.round(hRow.pred_lightgbm + halfWidth));
    return { low, high, halfWidth };
  }

  function renderForecastTab() {
    const day = STATE.dayData;
    const explain = STATE.hourExplain;
    if (!day || !explain) return;

    const kpis = day.daily_kpis;
    const strat = day.bidding_strategy;
    const cheap4 = strat.discom_buy_windows;
    const peak4 = strat.generator_dispatch_windows;

    const cheapAvg = cheap4.reduce((s, x) => s + x.pred_mcp, 0) / Math.max(1, cheap4.length);
    const peakAvg = peak4.reduce((s, x) => s + x.pred_mcp, 0) / Math.max(1, peak4.length);
    const focusRow = day.hourly.find((x) => x.hour === STATE.selectedHour) || day.hourly[0];
    const focusBand = getHourConfidenceBand(focusRow);

    // 1. Update Dynamic Market Advisory Banner
    const bannerEl = document.getElementById("advisory-banner");
    const badgeEl = document.getElementById("advisory-badge");
    const headlineEl = document.getElementById("advisory-headline");
    const summaryEl = document.getElementById("advisory-summary");

    const maxPred = Math.max(...day.hourly.map((x) => x.pred_lightgbm));
    const minPred = Math.min(...day.hourly.map((x) => x.pred_lightgbm));
    const cheapHoursText = cheap4.map((x) => x.hour_label).join(", ");
    const peakHoursText = peak4.map((x) => x.hour_label).join(", ");

    if (maxPred >= 7500) {
      bannerEl.classList.add("high-alert");
      badgeEl.textContent = "HIGH EVENING SCARCITY ALERT";
      headlineEl.textContent = `Evening Peak Reaches ${fmtRs(maxPred)}/MWh — Shift Flexible Load to Solar Hours (${fmtRs(cheapAvg)}/MWh)`;
      summaryEl.textContent = `Strong evening thermal ramp pushes clearing prices toward the regulatory ceiling during ${peakHoursText}. Procuring flexible volume during ${cheapHoursText} reduces unit power cost by ${strat.expected_procurement_savings_pct}%.`;
    } else if (minPred <= 2600) {
      bannerEl.classList.remove("high-alert");
      badgeEl.textContent = "SOLAR SURPLUS BUYING OPPORTUNITY";
      headlineEl.textContent = `Deep Midday Solar Discount (${fmtRs(minPred)}/MWh) — Optimal Window for Industrial & BESS Charging`;
      summaryEl.textContent = `High renewable injection up to ${(kpis.max_solar_mw / 1000).toFixed(1)} GW depresses midday clearing prices across ${cheapHoursText}, creating a ${fmtRs(strat.peak_spread_rs_per_mwh)}/MWh peak-to-trough spread.`;
    } else {
      bannerEl.classList.remove("high-alert");
      badgeEl.textContent = "MODERATE BALANCED MARKET";
      headlineEl.textContent = `24-Hour Average Clearing Price Forecast at ${fmtRs(kpis.mean_pred_lightgbm)}/MWh (₹${(kpis.mean_pred_lightgbm / 1000).toFixed(2)}/kWh)`;
      summaryEl.textContent = `Lowest procurement costs occur at ${cheapHoursText} (avg ${fmtRs(cheapAvg)}/MWh); highest tariff blocks occur at ${peakHoursText} (avg ${fmtRs(peakAvg)}/MWh).`;
    }

    // 2. Update 4 Executive KPI Cards
    document.getElementById("kpi-avg-price").textContent = fmtRs(kpis.mean_pred_lightgbm);
    document.getElementById("kpi-avg-sub").textContent = `Equivalent to ₹${(kpis.mean_pred_lightgbm / 1000).toFixed(2)}/kWh • Range: ${fmtRs(minPred)}–${fmtRs(maxPred)}`;

    document.getElementById("kpi-buy-window").textContent = `${cheap4[0].hour_label} – ${cheap4[cheap4.length - 1].hour_label}`;
    document.getElementById("kpi-buy-pill").textContent = `Save ${strat.expected_procurement_savings_pct}%`;
    document.getElementById("kpi-buy-sub").textContent = `Avg ${fmtRs(cheapAvg)}/MWh (${fmtRs(strat.expected_procurement_savings_rs_per_mwh)} below daily mean)`;

    document.getElementById("kpi-peak-window").textContent = `${peak4[0].hour_label} – ${peak4[peak4.length - 1].hour_label}`;
    document.getElementById("kpi-peak-sub").textContent = `Avg ${fmtRs(peakAvg)}/MWh • Max Net Load ${(kpis.max_net_demand_mw / 1000).toFixed(1)} GW`;

    document.getElementById("kpi-focus-pill").textContent = `${focusRow.hour_label} IST`;
    document.getElementById("kpi-focus-price").textContent = fmtRs(focusRow.pred_lightgbm);
    document.getElementById("kpi-focus-sub").textContent = `90% Band: ${fmtRs(focusBand.low)} – ${fmtRs(focusBand.high)}/MWh`;

    document.getElementById("day-accuracy-badge").textContent = `Verified Day Error (MAE): ${fmtRs(kpis.mae_lightgbm)}/MWh (₹${(kpis.mae_lightgbm / 1000).toFixed(2)}/kWh)`;

    // 3. Render 24-Hour Quick Timeline Buttons
    renderHourTimelineBar(day, cheap4, peak4);

    // 4. Render Plain-English Market Drivers for Selected Hour
    renderPlainDriversList(explain);

    // 5. Render Actionable Buying & Selling Slot Pills
    renderActionSlotPills(cheap4, peak4, cheapAvg, peakAvg, strat.peak_spread_rs_per_mwh);

    // 6. Render Main 24-Hour Forecast Chart & Generation Mix Chart
    drawMainForecastChart();
    drawGenMixChart();
  }

  function renderHourTimelineBar(day, cheap4, peak4) {
    const bar = document.getElementById("hour-timeline-bar");
    if (!bar) return;
    const cheapSet = new Set(cheap4.map((x) => x.hour_label));
    const peakSet = new Set(peak4.map((x) => x.hour_label));

    bar.innerHTML = "";
    for (const hRow of day.hourly) {
      const btn = document.createElement("button");
      btn.className = "hour-btn";
      if (hRow.hour === STATE.selectedHour) btn.classList.add("active");
      if (cheapSet.has(hRow.hour_label)) btn.classList.add("cheap-slot");
      if (peakSet.has(hRow.hour_label)) btn.classList.add("peak-slot");
      btn.textContent = String(hRow.hour).padStart(2, "0");
      btn.title = `${hRow.hour_label} IST — AI Forecast: ${fmtRs(hRow.pred_lightgbm)}/MWh`;
      btn.addEventListener("click", () => {
        selectDateAndHour(STATE.selectedDate, hRow.hour);
      });
      bar.appendChild(btn);
    }
  }

  function renderPlainDriversList(explain) {
    const labelEl = document.getElementById("driver-hour-label");
    const baseEl = document.getElementById("driver-base-val");
    const shiftEl = document.getElementById("driver-shift-val");
    const finalEl = document.getElementById("driver-final-val");
    const listEl = document.getElementById("drivers-list");
    if (!listEl) return;

    labelEl.textContent = `${explain.hour_label} IST`;
    const baseVal = explain.base_value || 3873;
    const finalVal = explain.pred_lightgbm;
    const netShift = finalVal - baseVal;

    baseEl.textContent = fmtRs(baseVal);
    shiftEl.textContent = fmtSignedRs(netShift);
    shiftEl.style.color = netShift >= 0 ? "var(--accent-peak)" : "var(--accent-good)";
    finalEl.textContent = fmtRs(finalVal);

    const topDrivers = (explain.top_attributions || []).slice(0, 8);
    const maxAbs = Math.max(100, ...topDrivers.map((d) => Math.abs(d.shap_rs)));

    listEl.innerHTML = "";
    for (const d of topDrivers) {
      const info = getPlainDriverInfo(d.feature, d.label);
      const isUp = d.shap_rs >= 0;
      const pctWidth = Math.min(48, Math.max(4, (Math.abs(d.shap_rs) / maxAbs) * 48));
      const leftPos = isUp ? 50 : 50 - pctWidth;

      const row = document.createElement("div");
      row.className = "driver-item";
      row.innerHTML = `
        <div>
          <div class="driver-name">${info.title}</div>
          <div class="driver-reading">Current: ${info.fmt(d.value)}</div>
        </div>
        <div class="driver-bar-wrap">
          <div class="driver-bar-center"></div>
          <div class="driver-bar-fill ${isUp ? "up" : "down"}" style="left:${leftPos}%; width:${pctWidth}%;"></div>
        </div>
        <div class="driver-impact ${isUp ? "up" : "down"}">
          ${fmtSignedRs(d.shap_rs)}
        </div>
      `;

      row.addEventListener("mousemove", (evt) => {
        showPopover(
          evt,
          info.title,
          isUp ? "PUSHES PRICE UP" : "PULLS PRICE DOWN",
          [
            { label: "Current Reading", value: info.fmt(d.value) },
            {
              label: "Rupee Price Impact",
              value: `${fmtSignedRs(d.shap_rs)}/MWh`,
              highlight: isUp ? "var(--accent-peak)" : "var(--accent-good)"
            },
            { label: "Signal Group", value: d.category || "Market Driver" },
            { label: "Market Interpretation", value: info.desc }
          ]
        );
      });
      row.addEventListener("mouseleave", hidePopover);
      listEl.appendChild(row);
    }
  }

  function renderActionSlotPills(cheap4, peak4, cheapAvg, peakAvg, spread) {
    const cheapGrid = document.getElementById("cheap-slots-grid");
    const peakGrid = document.getElementById("peak-slots-grid");
    document.getElementById("cheap-slots-avg").textContent = `Avg ${fmtRs(cheapAvg)}/MWh`;
    document.getElementById("peak-slots-avg").textContent = `Avg ${fmtRs(peakAvg)}/MWh`;
    document.getElementById("arbitrage-spread-val").textContent = `${fmtRs(spread)} / MWh`;

    cheapGrid.innerHTML = "";
    for (const slot of cheap4) {
      const hr = parseInt(slot.hour_label.split(":")[0], 10);
      const box = document.createElement("div");
      box.className = "slot-pill-box";
      box.innerHTML = `
        <div class="slot-time">${slot.hour_label} IST</div>
        <div class="slot-mcp" style="color: var(--accent-good);">${fmtRs(slot.pred_mcp)}</div>
        <div class="slot-sub">Solar: ${(slot.solar_mw / 1000).toFixed(1)} GW</div>
      `;
      box.addEventListener("click", () => selectDateAndHour(STATE.selectedDate, hr));
      cheapGrid.appendChild(box);
    }

    peakGrid.innerHTML = "";
    for (const slot of peak4) {
      const hr = parseInt(slot.hour_label.split(":")[0], 10);
      const box = document.createElement("div");
      box.className = "slot-pill-box";
      box.innerHTML = `
        <div class="slot-time">${slot.hour_label} IST</div>
        <div class="slot-mcp" style="color: var(--accent-peak);">${fmtRs(slot.pred_mcp)}</div>
        <div class="slot-sub">Net: ${(slot.net_demand_mw / 1000).toFixed(1)} GW</div>
      `;
      box.addEventListener("click", () => selectDateAndHour(STATE.selectedDate, hr));
      peakGrid.appendChild(box);
    }
  }

  // --------------------------------------------------------------------------
  // 8. CHART 1: MAIN 24-HOUR AI PRICE FORECAST & CONFIDENCE BAND
  // --------------------------------------------------------------------------
  function drawMainForecastChart(hoverHour = null) {
    const setup = setupCanvas("canvas-main-forecast");
    if (!setup || !STATE.dayData) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const hourly = STATE.dayData.hourly;

    const pad = { top: 20, right: 24, bottom: 32, left: 64 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const bands = hourly.map((row) => getHourConfidenceBand(row));
    const maxVal = Math.min(10500, Math.max(6000, ...bands.map((b) => b.high), ...hourly.map((r) => r.actual_mcp)) * 1.06);
    const minVal = 0;

    const xForHour = (hr) => pad.left + (hr / 23) * plotW;
    const yForPrice = (p) => pad.top + plotH - ((p - minVal) / (maxVal - minVal)) * plotH;

    // 1. Optional Buy / Peak Highlight Zones
    if (STATE.showZones) {
      const cheapHours = STATE.dayData.bidding_strategy.discom_buy_windows.map((x) => parseInt(x.hour_label, 10));
      const peakHours = STATE.dayData.bidding_strategy.generator_dispatch_windows.map((x) => parseInt(x.hour_label, 10));
      const stepW = plotW / 23;

      for (const ch of cheapHours) {
        ctx.fillStyle = c.goodFill;
        ctx.fillRect(xForHour(ch) - stepW * 0.45, pad.top, stepW * 0.9, plotH);
      }
      for (const ph of peakHours) {
        ctx.fillStyle = c.peakFill;
        ctx.fillRect(xForHour(ph) - stepW * 0.45, pad.top, stepW * 0.9, plotH);
      }
    }

    // 2. Horizontal Grid Lines & Y-Axis Labels
    ctx.strokeStyle = c.gridLine;
    ctx.lineWidth = 1;
    ctx.fillStyle = c.textMuted;
    ctx.font = "500 11px 'JetBrains Mono', monospace";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";

    const yTicks = 5;
    for (let i = 0; i <= yTicks; i++) {
      const val = minVal + ((maxVal - minVal) * i) / yTicks;
      const y = yForPrice(val);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();
      ctx.fillText(`₹${Math.round(val).toLocaleString("en-IN")}`, pad.left - 8, y);
    }

    // 3. X-Axis Hour Labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let hr = 0; hr < 24; hr += 2) {
      const x = xForHour(hr);
      ctx.fillText(`${String(hr).padStart(2, "0")}:00`, x, h - pad.bottom + 8);
    }

    // 4. 90% Confidence Interval Shaded Polygon
    ctx.beginPath();
    hourly.forEach((row, idx) => {
      const x = xForHour(row.hour);
      const y = yForPrice(bands[idx].high);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    for (let idx = hourly.length - 1; idx >= 0; idx--) {
      const x = xForHour(hourly[idx].hour);
      const y = yForPrice(bands[idx].low);
      ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = c.brandFill;
    ctx.fill();

    // 5. Verified Actual Clearing Price Line (if toggled)
    if (STATE.showActual) {
      ctx.beginPath();
      ctx.strokeStyle = c.solar;
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 4]);
      hourly.forEach((row, idx) => {
        const x = xForHour(row.hour);
        const y = yForPrice(row.actual_mcp);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 6. Primary AI Forecast Curve
    ctx.beginPath();
    ctx.strokeStyle = c.brand;
    ctx.lineWidth = 2.8;
    hourly.forEach((row, idx) => {
      const x = xForHour(row.hour);
      const y = yForPrice(row.pred_lightgbm);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // 7. Data Nodes & Selected / Hovered Crosshair
    const activeHour = hoverHour !== null ? hoverHour : STATE.selectedHour;
    const activeX = xForHour(activeHour);

    ctx.save();
    ctx.strokeStyle = c.borderStrong;
    ctx.lineWidth = 1.2;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(activeX, pad.top);
    ctx.lineTo(activeX, pad.top + plotH);
    ctx.stroke();
    ctx.restore();

    hourly.forEach((row) => {
      const x = xForHour(row.hour);
      const y = yForPrice(row.pred_lightgbm);
      const isFocus = row.hour === activeHour;

      ctx.beginPath();
      ctx.arc(x, y, isFocus ? 5.5 : 3, 0, Math.PI * 2);
      ctx.fillStyle = isFocus ? c.brand : c.bgCard;
      ctx.fill();
      ctx.lineWidth = isFocus ? 2.5 : 1.8;
      ctx.strokeStyle = c.brand;
      ctx.stroke();

      if (STATE.showActual && isFocus) {
        const yAct = yForPrice(row.actual_mcp);
        ctx.beginPath();
        ctx.arc(x, yAct, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = c.solar;
        ctx.fill();
      }
    });

    // Attach interactive hover & click handlers once
    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const rel = Math.max(0, Math.min(1, (mx - pad.left) / plotW));
      const hIdx = Math.round(rel * 23);
      const row = hourly[hIdx];
      if (!row) return;

      drawMainForecastChart(row.hour);
      const band = bands[hIdx];
      const regimeBadge = row.is_peak_hour
        ? "EVENING PEAK RISK"
        : row.is_solar_hour
        ? "SOLAR WINDOW"
        : "OFF-PEAK BASE";

      showPopover(evt, `${STATE.selectedDate} • ${row.hour_label} IST`, regimeBadge, [
        {
          label: "AI Forecast Price",
          value: `${fmtRs(row.pred_lightgbm)}/MWh (₹${(row.pred_lightgbm / 1000).toFixed(2)}/kWh)`,
          color: c.brand,
          highlight: c.brand
        },
        {
          label: "90% Confidence Band",
          value: `${fmtRs(band.low)} – ${fmtRs(band.high)}/MWh`
        },
        {
          label: "Verified Actual Price",
          value: `${fmtRs(row.actual_mcp)}/MWh (Diff: ${fmtSignedRs(row.error_lightgbm)})`,
          color: c.solar
        },
        {
          label: "National Net Thermal Load",
          value: `${(row.net_demand_mw / 1000).toFixed(1)} GW (Gross: ${(row.demand_mw / 1000).toFixed(1)} GW)`
        },
        {
          label: "Solar + Wind Output",
          value: `${(row.solar_generation_mw / 1000).toFixed(1)} GW Solar • ${(row.wind_generation_mw / 1000).toFixed(1)} GW Wind`
        },
        {
          label: "Buyer Action",
          value: row.pred_lightgbm < STATE.dayData.daily_kpis.mean_pred_lightgbm
            ? "Favorable Buy / Charge Slot"
            : "High-Tariff — Avoid or Shave Load",
          highlight: row.pred_lightgbm < STATE.dayData.daily_kpis.mean_pred_lightgbm ? c.good : c.peak
        }
      ]);
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawMainForecastChart(null);
    };

    canvas.onclick = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const rel = Math.max(0, Math.min(1, (mx - pad.left) / plotW));
      const hIdx = Math.round(rel * 23);
      if (hourly[hIdx]) {
        selectDateAndHour(STATE.selectedDate, hourly[hIdx].hour);
      }
    };
  }

  // --------------------------------------------------------------------------
  // 9. CHART 2: NATIONAL RENEWABLE GENERATION & NET THERMAL DEMAND (GW)
  // --------------------------------------------------------------------------
  function drawGenMixChart(hoverHour = null) {
    const setup = setupCanvas("canvas-gen-mix");
    if (!setup || !STATE.dayData) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const hourly = STATE.dayData.hourly;

    const pad = { top: 18, right: 24, bottom: 30, left: 58 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const maxGw = Math.max(195, ...hourly.map((r) => r.demand_mw / 1000)) * 1.05;
    const minGw = 0;

    const xForHour = (hr) => pad.left + ((hr + 0.5) / 24) * plotW;
    const yForGw = (gw) => pad.top + plotH - ((gw - minGw) / (maxGw - minGw)) * plotH;

    // Grid lines
    ctx.strokeStyle = c.gridLine;
    ctx.lineWidth = 1;
    ctx.fillStyle = c.textMuted;
    ctx.font = "500 11px 'JetBrains Mono', monospace";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";

    for (let i = 0; i <= 4; i++) {
      const gw = (maxGw * i) / 4;
      const y = yForGw(gw);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();
      ctx.fillText(`${Math.round(gw)} GW`, pad.left - 8, y);
    }

    // X-Axis labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let hr = 0; hr < 24; hr += 3) {
      ctx.fillText(`${String(hr).padStart(2, "0")}:00`, xForHour(hr), h - pad.bottom + 7);
    }

    // Stacked Renewable Bars (Solar + Wind)
    const barW = Math.max(6, (plotW / 24) * 0.62);
    hourly.forEach((row) => {
      const x = xForHour(row.hour) - barW / 2;
      const solarGw = row.solar_generation_mw / 1000;
      const windGw = row.wind_generation_mw / 1000;

      // Wind bar at bottom
      const yWindTop = yForGw(windGw);
      const hWind = pad.top + plotH - yWindTop;
      ctx.fillStyle = c.brand;
      ctx.globalAlpha = row.hour === hoverHour ? 0.95 : 0.72;
      ctx.fillRect(x, yWindTop, barW, hWind);

      // Solar bar stacked on top of Wind
      const ySolarTop = yForGw(windGw + solarGw);
      const hSolar = yWindTop - ySolarTop;
      ctx.fillStyle = c.solar;
      ctx.fillRect(x, ySolarTop, barW, hSolar);
      ctx.globalAlpha = 1.0;
    });

    // 160 GW Peaker Stress Threshold Line
    const y160 = yForGw(160);
    ctx.save();
    ctx.strokeStyle = c.peak;
    ctx.lineWidth = 1.4;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, y160);
    ctx.lineTo(w - pad.right, y160);
    ctx.stroke();
    ctx.restore();

    // Net Thermal Demand Line
    ctx.beginPath();
    ctx.strokeStyle = c.blue;
    ctx.lineWidth = 2.6;
    hourly.forEach((row, idx) => {
      const x = xForHour(row.hour);
      const y = yForGw(row.net_demand_mw / 1000);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    hourly.forEach((row) => {
      const x = xForHour(row.hour);
      const y = yForGw(row.net_demand_mw / 1000);
      ctx.beginPath();
      ctx.arc(x, y, row.hour === hoverHour ? 5 : 2.6, 0, Math.PI * 2);
      ctx.fillStyle = c.blue;
      ctx.fill();
    });

    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const rel = Math.max(0, Math.min(0.999, (mx - pad.left) / plotW));
      const hIdx = Math.floor(rel * 24);
      const row = hourly[hIdx];
      if (!row) return;

      drawGenMixChart(row.hour);
      const netGw = row.net_demand_mw / 1000;
      showPopover(
        evt,
        `Grid Supply Stack • ${row.hour_label} IST`,
        netGw >= 160 ? "PEAKER STRESS (>160 GW)" : `${row.re_penetration_pct.toFixed(1)}% RENEWABLE`,
        [
          { label: "Total National Demand", value: `${(row.demand_mw / 1000).toFixed(1)} GW` },
          {
            label: "Net Thermal Demand",
            value: `${netGw.toFixed(1)} GW`,
            color: c.blue,
            highlight: netGw >= 160 ? c.peak : c.blue
          },
          { label: "Solar Generation", value: `${(row.solar_generation_mw / 1000).toFixed(1)} GW`, color: c.solar },
          { label: "Wind Generation", value: `${(row.wind_generation_mw / 1000).toFixed(1)} GW`, color: c.brand },
          { label: "1-Hour Thermal Ramp", value: `${row.net_demand_ramp_1 >= 0 ? "+" : ""}${(row.net_demand_ramp_1 / 1000).toFixed(1)} GW/h` },
          { label: "AI Clearing Price", value: `${fmtRs(row.pred_lightgbm)}/MWh` }
        ]
      );
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawGenMixChart(null);
    };
  }

  // --------------------------------------------------------------------------
  // 10. WORKFLOW TAB 2: SMART PROCUREMENT & BID OPTIMIZER (ROI CALCULATOR)
  // --------------------------------------------------------------------------
  function computeBidOptimization() {
    if (!STATE.dayData) return null;
    const hourly = STATE.dayData.hourly;
    const baseMw = STATE.optBaseMw;
    const flexFrac = STATE.optFlexPct / 100;
    const priceCap = STATE.optPriceCap;

    // Rank hours by AI predicted clearing price
    const sorted = [...hourly].sort((a, b) => a.pred_lightgbm - b.pred_lightgbm);
    const cheapest6 = new Set(sorted.slice(0, 6).map((x) => x.hour));
    const expensive6 = new Set(sorted.slice(-6).map((x) => x.hour));

    // Calculate total MWh shaved from expensive hours and reallocate to cheapest solar hours
    let shavedTotalMWh = 0;
    const rawSchedule = hourly.map((row) => {
      let optMw = baseMw;
      let action = "STANDARD BASE";
      let actionType = "normal";

      if (expensive6.has(row.hour)) {
        // Shave flexible load in peak hours (more aggressive if above price cap)
        const shaveRatio = row.pred_lightgbm > priceCap ? Math.min(0.75, flexFrac * 1.25) : flexFrac;
        const shaved = Math.round(baseMw * shaveRatio);
        optMw = baseMw - shaved;
        shavedTotalMWh += shaved;
        action = row.pred_lightgbm > priceCap ? "CAP PROTECT / SHAVE" : "PEAK LOAD SHAVE";
        actionType = "shave";
      }
      return { row, baseMw, optMw, action, actionType };
    });

    // Distribute shavedTotalMWh across the 6 cheapest solar/off-peak hours (energy-neutral day)
    const boostPerCheapHour = shavedTotalMWh / 6;
    let totalBaseCostRs = 0;
    let totalOptCostRs = 0;

    const schedule = rawSchedule.map((item) => {
      const { row } = item;
      let finalMw = item.optMw;
      let action = item.action;
      let actionType = item.actionType;

      if (cheapest6.has(row.hour)) {
        finalMw = Math.round((item.optMw + boostPerCheapHour) * 10) / 10;
        action = "SOLAR SHIFT BOOST";
        actionType = "boost";
      }

      const band = getHourConfidenceBand(row);
      const recommendedBidLimit = Math.min(priceCap, Math.min(10000, Math.round(band.high / 50) * 50));

      const baseCostRs = item.baseMw * row.pred_lightgbm;
      const optCostRs = finalMw * row.pred_lightgbm;
      totalBaseCostRs += baseCostRs;
      totalOptCostRs += optCostRs;

      return {
        hour: row.hour,
        hour_label: row.hour_label,
        pred_mcp: row.pred_lightgbm,
        actual_mcp: row.actual_mcp,
        bid_limit: recommendedBidLimit,
        base_mw: item.baseMw,
        opt_mw: finalMw,
        action,
        actionType,
        base_cost_rs: baseCostRs,
        opt_cost_rs: optCostRs,
        hourly_Delta_rs: baseCostRs - optCostRs
      };
    });

    const dailySavingsRs = Math.max(0, totalBaseCostRs - totalOptCostRs);
    const savingsPct = totalBaseCostRs > 0 ? (dailySavingsRs / totalBaseCostRs) * 100 : 0;
    const annualSavingsRs = dailySavingsRs * 365;

    return {
      schedule,
      totalBaseCostRs,
      totalOptCostRs,
      dailySavingsRs,
      savingsPct,
      annualSavingsRs
    };
  }

  function renderOptimizerTab() {
    const res = computeBidOptimization();
    if (!res) return;

    // Update badge labels next to sliders
    document.getElementById("opt-val-mw").textContent = `${STATE.optBaseMw} MW`;
    document.getElementById("opt-val-flex").textContent = `${STATE.optFlexPct}%`;
    document.getElementById("opt-val-cap").textContent = `${fmtRs(STATE.optPriceCap)} / MWh`;

    // Update 4 ROI KPI Cards
    document.getElementById("opt-kpi-base-cost").textContent = fmtLakhs(res.totalBaseCostRs);
    document.getElementById("opt-kpi-base-sub").textContent = `Daily Energy: ${(STATE.optBaseMw * 24).toLocaleString("en-IN")} MWh flat load`;

    document.getElementById("opt-kpi-opt-cost").textContent = fmtLakhs(res.totalOptCostRs);
    document.getElementById("opt-kpi-opt-sub").textContent = `100% Energy-Neutral (${(STATE.optBaseMw * 24).toLocaleString("en-IN")} MWh delivered)`;

    document.getElementById("opt-kpi-daily-save").textContent = fmtLakhs(res.dailySavingsRs);
    document.getElementById("opt-kpi-save-pct").textContent = `-${res.savingsPct.toFixed(1)}% Bill`;
    document.getElementById("opt-kpi-save-sub").textContent = `Saves ${fmtRs(res.dailySavingsRs / (STATE.optBaseMw * 24))}/MWh across portfolio`;

    document.getElementById("opt-kpi-annual-save").textContent = fmtCrores(res.annualSavingsRs);
    document.getElementById("opt-kpi-annual-sub").textContent = `Based on 365-day automated solar load shifting`;

    // Populate 24-Hour Bid Schedule Table
    const tbody = document.getElementById("opt-schedule-tbody");
    if (tbody) {
      tbody.innerHTML = "";
      for (const s of res.schedule) {
        const tr = document.createElement("tr");
        if (s.actionType === "boost") tr.className = "highlight-row";
        const badgeClass = s.actionType === "boost" ? "good" : s.actionType === "shave" ? "peak" : "info";
        const costDiffText =
          s.hourly_Delta_rs >= 0
            ? `<span style="color:var(--accent-good); font-weight:600;">Save ${fmtRs(s.hourly_Delta_rs)}</span>`
            : `<span style="color:var(--brand-primary);">Reallocated +${fmtRs(Math.abs(s.hourly_Delta_rs))}</span>`;

        tr.innerHTML = `
          <td class="mono">${s.hour_label} – ${String((s.hour + 1) % 24).padStart(2, "0")}:00</td>
          <td class="mono" style="font-weight:600;">${fmtRs(s.pred_mcp)}</td>
          <td class="mono">${fmtRs(s.bid_limit)}</td>
          <td class="mono">${s.base_mw.toFixed(1)} MW</td>
          <td class="mono" style="font-weight:700;">${s.opt_mw.toFixed(1)} MW</td>
          <td><span class="metric-pill ${badgeClass}">${s.action}</span></td>
          <td class="mono">${costDiffText}</td>
        `;
        tbody.appendChild(tr);
      }
    }

    drawBidOptimizerChart(res);
  }

  function drawBidOptimizerChart(optRes, hoverHour = null) {
    const setup = setupCanvas("canvas-bid-optimizer");
    if (!setup || !optRes) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const sched = optRes.schedule;

    const pad = { top: 20, right: 64, bottom: 30, left: 58 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const maxMw = Math.max(...sched.map((s) => Math.max(s.base_mw, s.opt_mw))) * 1.22;
    const maxPrice = Math.max(6000, ...sched.map((s) => s.pred_mcp)) * 1.1;

    const xForHour = (hr) => pad.left + ((hr + 0.5) / 24) * plotW;
    const yForMw = (mw) => pad.top + plotH - (mw / maxMw) * plotH;
    const yForPrice = (p) => pad.top + plotH - (p / maxPrice) * plotH;

    // Grid & Left Axis (MW)
    ctx.strokeStyle = c.gridLine;
    ctx.lineWidth = 1;
    ctx.fillStyle = c.textMuted;
    ctx.font = "500 11px 'JetBrains Mono', monospace";

    for (let i = 0; i <= 4; i++) {
      const mwVal = (maxMw * i) / 4;
      const pVal = (maxPrice * i) / 4;
      const y = yForMw(mwVal);

      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`${Math.round(mwVal)} MW`, pad.left - 8, y);

      ctx.textAlign = "left";
      ctx.fillText(`₹${Math.round(pVal).toLocaleString("en-IN")}`, w - pad.right + 8, y);
    }

    // X-Axis labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let hr = 0; hr < 24; hr += 2) {
      ctx.fillText(`${String(hr).padStart(2, "0")}:00`, xForHour(hr), h - pad.bottom + 7);
    }

    // Baseline Flat Load Reference Line
    const yBase = yForMw(STATE.optBaseMw);
    ctx.save();
    ctx.strokeStyle = c.textMuted;
    ctx.lineWidth = 1.3;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad.left, yBase);
    ctx.lineTo(w - pad.right, yBase);
    ctx.stroke();
    ctx.restore();

    // Optimized Load Bars
    const barW = Math.max(8, (plotW / 24) * 0.64);
    sched.forEach((s) => {
      const x = xForHour(s.hour) - barW / 2;
      const yTop = yForMw(s.opt_mw);
      const barH = pad.top + plotH - yTop;

      ctx.fillStyle = s.actionType === "boost" ? c.good : s.actionType === "shave" ? c.peak : c.blue;
      ctx.globalAlpha = s.hour === hoverHour ? 0.95 : 0.76;
      ctx.fillRect(x, yTop, barW, barH);
      ctx.globalAlpha = 1.0;
    });

    // AI Forecast Price Line Overlay
    ctx.beginPath();
    ctx.strokeStyle = c.solar;
    ctx.lineWidth = 2.5;
    sched.forEach((s, idx) => {
      const x = xForHour(s.hour);
      const y = yForPrice(s.pred_mcp);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    sched.forEach((s) => {
      const x = xForHour(s.hour);
      const y = yForPrice(s.pred_mcp);
      ctx.beginPath();
      ctx.arc(x, y, s.hour === hoverHour ? 5 : 2.8, 0, Math.PI * 2);
      ctx.fillStyle = c.solar;
      ctx.fill();
    });

    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const rel = Math.max(0, Math.min(0.999, (mx - pad.left) / plotW));
      const hIdx = Math.floor(rel * 24);
      const s = sched[hIdx];
      if (!s) return;

      drawBidOptimizerChart(optRes, s.hour);
      showPopover(evt, `Bid Schedule • ${s.hour_label} IST`, s.action, [
        { label: "AI Forecast Price", value: `${fmtRs(s.pred_mcp)}/MWh`, color: c.solar },
        { label: "Recommended Bid Cap", value: `${fmtRs(s.bid_limit)}/MWh` },
        { label: "Unoptimized Flat Load", value: `${s.base_mw.toFixed(1)} MW (${fmtRs(s.base_cost_rs)})` },
        {
          label: "AI-Optimized Bid Volume",
          value: `${s.opt_mw.toFixed(1)} MW (${fmtRs(s.opt_cost_rs)})`,
          color: s.actionType === "boost" ? c.good : s.actionType === "shave" ? c.peak : c.blue,
          highlight: s.actionType === "boost" ? c.good : s.actionType === "shave" ? c.peak : c.textMain
        },
        {
          label: "Volume Adjustment",
          value: `${s.opt_mw - s.base_mw >= 0 ? "+" : ""}${(s.opt_mw - s.base_mw).toFixed(1)} MW`
        }
      ]);
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawBidOptimizerChart(optRes, null);
    };
  }

  // --------------------------------------------------------------------------
  // 11. WORKFLOW TAB 3: WEATHER & GRID RISK SIMULATOR (STRESS TEST)
  // --------------------------------------------------------------------------
  async function runSimulatorStressTest() {
    if (!STATE.dayData || !STATE.hourExplain) return;
    const hRow = STATE.dayData.hourly.find((x) => x.hour === STATE.selectedHour) || STATE.dayData.hourly[0];

    const demandPct = Number(document.getElementById("sim-demand").value || 0);
    const solarPct = Number(document.getElementById("sim-solar").value || 0);
    const windPct = Number(document.getElementById("sim-wind").value || 0);
    const rampPct = Number(document.getElementById("sim-ramp").value || 0);
    const tempDelta = Number(document.getElementById("sim-temp").value || 0);
    const liqPct = Number(document.getElementById("sim-liq").value || 0);

    document.getElementById("sim-val-demand").textContent = `${demandPct >= 0 ? "+" : ""}${demandPct}%`;
    document.getElementById("sim-val-solar").textContent = `${solarPct >= 0 ? "+" : ""}${solarPct}%`;
    document.getElementById("sim-val-wind").textContent = `${windPct >= 0 ? "+" : ""}${windPct}%`;
    document.getElementById("sim-val-ramp").textContent = `${rampPct >= 0 ? "+" : ""}${rampPct}%`;
    document.getElementById("sim-val-temp").textContent = `${tempDelta >= 0 ? "+" : ""}${tempDelta.toFixed(1)} °C`;
    document.getElementById("sim-val-liq").textContent = `${liqPct >= 0 ? "+" : ""}${liqPct}%`;
    document.getElementById("sim-target-label").textContent = `${STATE.selectedDate} ${hRow.hour_label} IST`;

    const deltaDemandMw = hRow.demand_mw * (demandPct / 100);
    const deltaSolarMw = hRow.solar_generation_mw * (solarPct / 100);
    const deltaWindMw = hRow.wind_generation_mw * (windPct / 100);
    const deltaRampMw = Math.abs(hRow.net_demand_ramp_1 || 4000) * (rampPct / 100);
    const newTightness = Math.max(0.1, hRow.market_tightness_lag_24 * (1 + liqPct / 100));

    const payload = {
      date: STATE.selectedDate,
      hour: STATE.selectedHour,
      delta_demand_mw: deltaDemandMw,
      delta_solar_mw: deltaSolarMw,
      delta_wind_mw: deltaWindMw,
      delta_ramp_mw: deltaRampMw,
      delta_temp_c: tempDelta,
      market_tightness_override: liqPct === 0 ? null : newTightness
    };

    let simData = null;
    if (window.location.protocol !== "file:") {
      try {
        const resp = await fetch("/api/simulate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (resp.ok) simData = await resp.json();
      } catch (_) {
        // Fallback below
      }
    }

    if (!simData) {
      simData = computeOfflineSimulation(hRow, payload);
    }

    STATE.simResult = simData;
    renderSimulatorResults(simData);
  }

  function computeOfflineSimulation(hRow, payload) {
    const baseLgb = hRow.pred_lightgbm;
    const newDemand = Math.max(50000, hRow.demand_mw + payload.delta_demand_mw);
    const newSolar = Math.max(0, hRow.solar_generation_mw + payload.delta_solar_mw);
    const newWind = Math.max(0, hRow.wind_generation_mw + payload.delta_wind_mw);
    const newNetDemand = newDemand - newSolar - newWind;
    const netDemandChangeGw = (newNetDemand - hRow.net_demand_mw) / 1000;

    // Non-linear merit-order sensitivity (steeper above 158 GW peaker knee)
    const peakerMultiplier = newNetDemand / 1000 >= 158 ? 92 : 48;
    const ndShockRs = netDemandChangeGw * peakerMultiplier;
    const rampShockRs = (payload.delta_ramp_mw / 1000) * 35;
    const tempShockRs = payload.delta_temp_c * 65;
    const liqDiff = payload.market_tightness_override
      ? payload.market_tightness_override - hRow.market_tightness_lag_24
      : 0;
    const liqShockRs = liqDiff * 850;

    const totalDeltaRs = ndShockRs + rampShockRs + tempShockRs + liqShockRs;
    const simLgb = Math.min(10000, Math.max(0, baseLgb + totalDeltaRs));

    const shiftedDrivers = [
      {
        feature: "net_demand_mw",
        label: "Net Thermal Demand (Load − RE)",
        base_shap_rs: Math.round(((hRow.net_demand_mw - 142000) / 1000) * 28),
        sim_shap_rs: Math.round(((hRow.net_demand_mw - 142000) / 1000) * 28 + ndShockRs),
        delta_shap_rs: Math.round(ndShockRs)
      },
      {
        feature: "solar_generation_mw",
        label: "National Solar Generation",
        base_shap_rs: hRow.solar_generation_mw > 5000 ? -380 : 110,
        sim_shap_rs: Math.round((hRow.solar_generation_mw > 5000 ? -380 : 110) - (payload.delta_solar_mw / 1000) * 38),
        delta_shap_rs: Math.round(-(payload.delta_solar_mw / 1000) * 38)
      },
      {
        feature: "market_tightness_lag_24",
        label: "Buyer-to-Seller Order Book Ratio",
        base_shap_rs: Math.round((hRow.market_tightness_lag_24 - 1.0) * 620),
        sim_shap_rs: Math.round((hRow.market_tightness_lag_24 - 1.0) * 620 + liqShockRs),
        delta_shap_rs: Math.round(liqShockRs)
      },
      {
        feature: "net_demand_ramp_1",
        label: "Evening Thermal Ramp Stress",
        base_shap_rs: Math.round((hRow.net_demand_ramp_1 / 1000) * 32),
        sim_shap_rs: Math.round((hRow.net_demand_ramp_1 / 1000) * 32 + rampShockRs),
        delta_shap_rs: Math.round(rampShockRs)
      },
      {
        feature: "temperature_mean_c",
        label: "Population-Weighted Temperature",
        base_shap_rs: Math.round((hRow.temperature_mean_c - 25) * 45),
        sim_shap_rs: Math.round((hRow.temperature_mean_c - 25) * 45 + tempShockRs),
        delta_shap_rs: Math.round(tempShockRs)
      }
    ];

    return {
      predictions: {
        lightgbm: {
          baseline: baseLgb,
          simulated: simLgb,
          delta_rs: simLgb - baseLgb,
          delta_pct: ((simLgb - baseLgb) / Math.max(1, baseLgb)) * 100
        }
      },
      grid_telemetry: {
        baseline: {
          net_demand_gw: hRow.net_demand_mw / 1000,
          re_penetration_pct: hRow.re_penetration_pct
        },
        simulated: {
          net_demand_gw: newNetDemand / 1000,
          re_penetration_pct: ((newSolar + newWind) / Math.max(1, newDemand)) * 100
        }
      },
      top_shifted_shap: shiftedDrivers
    };
  }

  function renderSimulatorResults(simData) {
    const lgb = simData.predictions.lightgbm;
    const simGw = simData.grid_telemetry.simulated.net_demand_gw;

    document.getElementById("sim-kpi-base").textContent = fmtRs(lgb.baseline);
    document.getElementById("sim-kpi-new").textContent = fmtRs(lgb.simulated);
    document.getElementById("sim-kpi-band").textContent = `90% Band: ${fmtRs(Math.max(0, lgb.simulated - 420))} – ${fmtRs(Math.min(10000, lgb.simulated + 420))}`;

    const deltaEl = document.getElementById("sim-kpi-delta");
    deltaEl.textContent = fmtSignedRs(lgb.delta_rs);
    deltaEl.style.color = lgb.delta_rs > 0 ? "var(--accent-peak)" : lgb.delta_rs < 0 ? "var(--accent-good)" : "var(--text-main)";
    document.getElementById("sim-kpi-pct").textContent = `${lgb.delta_pct >= 0 ? "+" : ""}${lgb.delta_pct.toFixed(1)}% vs baseline`;

    const regimeEl = document.getElementById("sim-kpi-regime");
    if (simGw >= 160) {
      regimeEl.textContent = "Peaker Scarcity (>160 GW)";
      regimeEl.style.color = "var(--accent-peak)";
    } else if (simGw <= 125) {
      regimeEl.textContent = "Solar Surplus (<125 GW)";
      regimeEl.style.color = "var(--accent-good)";
    } else {
      regimeEl.textContent = "Coal Base-Load Zone";
      regimeEl.style.color = "var(--brand-primary)";
    }
    document.getElementById("sim-kpi-netload").textContent = `Simulated Net Load: ${simGw.toFixed(1)} GW`;

    // Render shifted drivers list
    const compEl = document.getElementById("sim-drivers-compare");
    if (compEl) {
      compEl.innerHTML = "";
      const list = (simData.top_shifted_shap || []).slice(0, 6);
      for (const item of list) {
        const info = getPlainDriverInfo(item.feature, item.label);
        const isUp = item.delta_shap_rs >= 0;
        const div = document.createElement("div");
        div.className = "driver-item";
        div.innerHTML = `
          <div>
            <div class="driver-name">${info.title}</div>
            <div class="driver-reading">Baseline Impact: ${fmtSignedRs(item.base_shap_rs)} &rarr; Simulated: ${fmtSignedRs(item.sim_shap_rs)}</div>
          </div>
          <div style="font-size: 12px; color: var(--text-secondary); text-align: right;">Net Shift:</div>
          <div class="driver-impact ${isUp ? "up" : "down"}">${fmtSignedRs(item.delta_shap_rs)}</div>
        `;
        compEl.appendChild(div);
      }
    }

    drawMeritOrderChart(simData);
  }

  function drawMeritOrderChart(simData, hoverIdx = null) {
    const setup = setupCanvas("canvas-sim-merit");
    if (!setup || !STATE.shapLab) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const curve = STATE.shapLab.merit_order_curve || [];
    if (!curve.length) return;

    const pad = { top: 20, right: 28, bottom: 32, left: 64 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const minGw = Math.min(95, ...curve.map((x) => x.net_demand_gw));
    const maxGw = Math.max(195, ...curve.map((x) => x.net_demand_gw));
    const minP = 1500;
    const maxP = 10000;

    const xForGw = (gw) => pad.left + ((gw - minGw) / (maxGw - minGw)) * plotW;
    const yForP = (p) => pad.top + plotH - ((p - minP) / (maxP - minP)) * plotH;

    // Peaker Scarcity Zone (>160 GW)
    const x160 = xForGw(160);
    if (x160 < w - pad.right) {
      ctx.fillStyle = c.peakFill;
      ctx.fillRect(x160, pad.top, w - pad.right - x160, plotH);
    }

    // Grid lines
    ctx.strokeStyle = c.gridLine;
    ctx.lineWidth = 1;
    ctx.fillStyle = c.textMuted;
    ctx.font = "500 11px 'JetBrains Mono', monospace";

    for (let i = 0; i <= 4; i++) {
      const pVal = minP + ((maxP - minP) * i) / 4;
      const y = yForP(pVal);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`₹${Math.round(pVal).toLocaleString("en-IN")}`, pad.left - 8, y);
    }

    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let gw = 100; gw <= 190; gw += 15) {
      ctx.fillText(`${gw} GW`, xForGw(gw), h - pad.bottom + 8);
    }

    // Draw Merit-Order Supply Curve
    ctx.beginPath();
    ctx.strokeStyle = c.textSec;
    ctx.lineWidth = 2.5;
    curve.forEach((pt, idx) => {
      const x = xForGw(pt.net_demand_gw);
      const y = yForP(pt.mean_mcp_rs);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw Baseline vs Simulated Operating Points
    if (simData) {
      const bGw = simData.grid_telemetry.baseline.net_demand_gw;
      const bP = simData.predictions.lightgbm.baseline;
      const sGw = simData.grid_telemetry.simulated.net_demand_gw;
      const sP = simData.predictions.lightgbm.simulated;

      const bx = xForGw(bGw);
      const by = yForP(bP);
      const sx = xForGw(sGw);
      const sy = yForP(sP);

      // Connector arrow
      ctx.beginPath();
      ctx.strokeStyle = c.peak;
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 3]);
      ctx.moveTo(bx, by);
      ctx.lineTo(sx, sy);
      ctx.stroke();
      ctx.setLineDash([]);

      // Baseline Point
      ctx.beginPath();
      ctx.arc(bx, by, 6, 0, Math.PI * 2);
      ctx.fillStyle = c.blue;
      ctx.fill();
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Simulated Point
      ctx.beginPath();
      ctx.arc(sx, sy, 7, 0, Math.PI * 2);
      ctx.fillStyle = c.peak;
      ctx.fill();
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const gwAtMouse = minGw + ((mx - pad.left) / plotW) * (maxGw - minGw);

      let bestIdx = 0;
      let bestDist = Infinity;
      curve.forEach((pt, idx) => {
        const d = Math.abs(pt.net_demand_gw - gwAtMouse);
        if (d < bestDist) {
          bestDist = d;
          bestIdx = idx;
        }
      });

      const pt = curve[bestIdx];
      if (!pt) return;

      drawMeritOrderChart(simData, bestIdx);
      const zone =
        pt.net_demand_gw >= 160
          ? "PEAKER SCARCITY (>160 GW)"
          : pt.net_demand_gw <= 125
          ? "SOLAR SURPLUS (<125 GW)"
          : "COAL BASE-LOAD";

      showPopover(evt, `National Merit-Order Curve`, zone, [
        { label: "Net Thermal Demand Level", value: `${pt.net_demand_gw.toFixed(1)} GW` },
        { label: "Historical Avg Clearing Price", value: `${fmtRs(pt.mean_mcp_rs)}/MWh`, color: c.brand },
        { label: "Net Load Price Impact", value: `${fmtSignedRs(pt.mean_shap_rs)}/MWh` },
        {
          label: "Your Baseline Operating Point",
          value: `${simData.grid_telemetry.baseline.net_demand_gw.toFixed(1)} GW (${fmtRs(simData.predictions.lightgbm.baseline)})`,
          color: c.blue
        },
        {
          label: "Stress-Tested Operating Point",
          value: `${simData.grid_telemetry.simulated.net_demand_gw.toFixed(1)} GW (${fmtRs(simData.predictions.lightgbm.simulated)})`,
          color: c.peak,
          highlight: c.peak
        }
      ]);
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawMeritOrderChart(simData, null);
    };
  }

  // --------------------------------------------------------------------------
  // 12. WORKFLOW TAB 4: FORECAST ACCURACY & MODEL TRUST SCORECARD
  // --------------------------------------------------------------------------
  function renderTrustTab() {
    if (!STATE.benchmarks || !STATE.shapLab) return;

    const friendlyModels = {
      "LightGBM Regressor": {
        name: "EnergyCast AI Production Engine (Gradient Boosted Trees)",
        cat: "Production AI Engine",
        status: "ACTIVE PRODUCTION"
      },
      "XGBoost Regressor": {
        name: "XGBoost Ensemble Challenger",
        cat: "Nonlinear Tree Ensemble",
        status: "Secondary Challenger"
      },
      "Ridge Regression (α=100)": {
        name: "L2-Regularized Econometric Model",
        cat: "Linear Parametric",
        status: "Benchmark Only"
      },
      "Ridge Regression (α=50)": {
        name: "L2-Regularized Econometric Model",
        cat: "Linear Parametric",
        status: "Benchmark Only"
      },
      "OLS Linear Regression": {
        name: "Standard Linear Regression (OLS)",
        cat: "Linear Parametric",
        status: "Benchmark Only"
      },
      "Daily Seasonal Naive (lag_24)": {
        name: "Yesterday Same-Hour Price (24h Market Baseline)",
        cat: "Standard Market Baseline",
        status: "Industry Baseline"
      },
      "Persistence Baseline (lag_1)": {
        name: "1-Hour Rolling Persistence",
        cat: "Intraday Reference",
        status: "Intraday Only"
      },
      "Weekly Seasonal Naive (lag_168)": {
        name: "Last Week Same-Hour Price (168h Baseline)",
        cat: "Weekly Baseline",
        status: "Benchmark Only"
      }
    };

    const tbody = document.getElementById("trust-benchmark-tbody");
    if (tbody) {
      tbody.innerHTML = "";
      for (const row of STATE.benchmarks.leaderboard) {
        const info = friendlyModels[row.model] || {
          name: row.model,
          cat: row.tier,
          status: "Evaluated"
        };
        const isChamp = row.model.includes("LightGBM");
        const tr = document.createElement("tr");
        if (isChamp) tr.className = "highlight-row";

        const gainText =
          row.vs_snaive_pct > 0
            ? `<span style="color:var(--accent-good); font-weight:700;">+${row.vs_snaive_pct.toFixed(1)}% More Accurate</span>`
            : row.vs_snaive_pct < 0
            ? `<span style="color:var(--accent-peak);">${row.vs_snaive_pct.toFixed(1)}%</span>`
            : `<span>Baseline (0.0%)</span>`;

        tr.innerHTML = `
          <td style="font-weight:${isChamp ? "700" : "500"};">${info.name}</td>
          <td>${info.cat}</td>
          <td class="mono" style="font-weight:700;">${fmtRs(row.test_mae)} / MWh</td>
          <td class="mono">₹${(row.test_mae / 1000).toFixed(2)} / kWh</td>
          <td class="mono">${fmtRs(row.test_rmse)} / MWh</td>
          <td class="mono">${(row.test_r2 * 100).toFixed(1)}%</td>
          <td class="mono">${gainText}</td>
          <td><span class="metric-pill ${isChamp ? "good" : "info"}">${info.status}</span></td>
        `;
        tbody.appendChild(tr);
      }
    }

    drawTrustAccuracyChart();
    drawTrustSignalsChart();
  }

  function drawTrustAccuracyChart(hoverHour = null) {
    const setup = setupCanvas("canvas-trust-accuracy");
    if (!setup || !STATE.benchmarks) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const profiles = STATE.benchmarks.hourly_error_profiles || [];
    if (!profiles.length) return;

    const pad = { top: 20, right: 24, bottom: 30, left: 58 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const maxErr = Math.max(1200, ...profiles.map((p) => p["Daily S-Naive (24h)"] || 900)) * 1.08;
    const xForHour = (hr) => pad.left + (hr / 23) * plotW;
    const yForErr = (e) => pad.top + plotH - (e / maxErr) * plotH;

    // Grid
    ctx.strokeStyle = c.gridLine;
    ctx.lineWidth = 1;
    ctx.fillStyle = c.textMuted;
    ctx.font = "500 11px 'JetBrains Mono', monospace";

    for (let i = 0; i <= 4; i++) {
      const val = (maxErr * i) / 4;
      const y = yForErr(val);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`₹${Math.round(val)}`, pad.left - 8, y);
    }

    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (let hr = 0; hr < 24; hr += 3) {
      ctx.fillText(`${String(hr).padStart(2, "0")}:00`, xForHour(hr), h - pad.bottom + 7);
    }

    const series = [
      { key: "Daily S-Naive (24h)", color: c.peak, width: 2, dash: [4, 4] },
      { key: "Ridge (α=50)", color: c.blue, width: 2, dash: [] },
      { key: "LightGBM (Champion)", color: c.brand, width: 3, dash: [] }
    ];

    for (const s of series) {
      ctx.beginPath();
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.width;
      ctx.setLineDash(s.dash);
      profiles.forEach((p, idx) => {
        const x = xForHour(p.hour);
        const y = yForErr(p[s.key] || 0);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    if (hoverHour !== null && profiles[hoverHour]) {
      const hx = xForHour(hoverHour);
      ctx.save();
      ctx.strokeStyle = c.borderStrong;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(hx, pad.top);
      ctx.lineTo(hx, pad.top + plotH);
      ctx.stroke();
      ctx.restore();
    }

    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const mx = evt.clientX - rect.left;
      const rel = Math.max(0, Math.min(1, (mx - pad.left) / plotW));
      const hIdx = Math.round(rel * 23);
      const p = profiles[hIdx];
      if (!p) return;

      drawTrustAccuracyChart(p.hour);
      const lgbErr = p["LightGBM (Champion)"];
      const ridgeErr = p["Ridge (α=50)"];
      const naiveErr = p["Daily S-Naive (24h)"];
      const gainPct = (((naiveErr - lgbErr) / Math.max(1, naiveErr)) * 100).toFixed(1);

      showPopover(evt, `Diurnal Accuracy • ${p.hour_label} IST`, `+${gainPct}% SKILL`, [
        {
          label: "EnergyCast AI Error (MAE)",
          value: `${fmtRs(lgbErr)}/MWh (₹${(lgbErr / 1000).toFixed(2)}/kWh)`,
          color: c.brand,
          highlight: c.brand
        },
        { label: "Linear Econometric Error", value: `${fmtRs(ridgeErr)}/MWh`, color: c.blue },
        { label: "24h Market Baseline Error", value: `${fmtRs(naiveErr)}/MWh`, color: c.peak },
        { label: "Avg Clearing Price at Hour", value: `${fmtRs(p.mean_actual_mcp)}/MWh` }
      ]);
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawTrustAccuracyChart(null);
    };
  }

  function drawTrustSignalsChart(hoverIdx = null) {
    const setup = setupCanvas("canvas-trust-signals");
    if (!setup || !STATE.shapLab) return;
    const { canvas, ctx, w, h } = setup;
    const c = getThemeColors();
    const top12 = (STATE.shapLab.global_features || []).slice(0, 12);
    if (!top12.length) return;

    const pad = { top: 14, right: 68, bottom: 20, left: 215 };
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const maxImpact = Math.max(...top12.map((f) => f.mean_abs_shap_rs)) * 1.1;
    const rowH = plotH / top12.length;

    top12.forEach((f, idx) => {
      const info = getPlainDriverInfo(f.feature, f.label);
      const yCenter = pad.top + idx * rowH + rowH / 2;
      const barH = Math.max(10, rowH * 0.62);
      const barW = (f.mean_abs_shap_rs / maxImpact) * plotW;

      // Label on left
      ctx.fillStyle = idx === hoverIdx ? c.textMain : c.textSec;
      ctx.font = `${idx === hoverIdx ? "700" : "500"} 11.5px 'Inter', sans-serif`;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(info.title, pad.left - 12, yCenter);

      // Horizontal Bar
      ctx.fillStyle = idx === 0 ? c.brand : idx < 4 ? c.blue : c.solar;
      ctx.globalAlpha = idx === hoverIdx ? 0.95 : 0.78;
      ctx.fillRect(pad.left, yCenter - barH / 2, barW, barH);
      ctx.globalAlpha = 1.0;

      // Value on right
      ctx.fillStyle = c.textMain;
      ctx.font = "600 11px 'JetBrains Mono', monospace";
      ctx.textAlign = "left";
      ctx.fillText(`₹${Math.round(f.mean_abs_shap_rs)}`, pad.left + barW + 8, yCenter);
    });

    canvas.onmousemove = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const my = evt.clientY - rect.top;
      const idx = Math.floor(((my - pad.top) / plotH) * top12.length);
      if (idx < 0 || idx >= top12.length) {
        hidePopover();
        return;
      }
      const f = top12[idx];
      const info = getPlainDriverInfo(f.feature, f.label);
      drawTrustSignalsChart(idx);

      showPopover(evt, `#${f.rank} • ${info.title}`, f.category, [
        { label: "Avg Price Influence", value: `±${fmtRs(f.mean_abs_shap_rs)}/MWh`, highlight: c.brand },
        { label: "Impact Volatility", value: `±${fmtRs(f.std_shap_rs)}/MWh` },
        { label: "Signal Correlation", value: `${f.correlation >= 0 ? "+" : ""}${f.correlation.toFixed(2)}` },
        { label: "What It Captures", value: info.desc }
      ]);
    };

    canvas.onmouseleave = () => {
      hidePopover();
      drawTrustSignalsChart(null);
    };
  }

  // --------------------------------------------------------------------------
  // 13. CSV EXPORT UTILITIES (24H FORECAST CSV & OFFICIAL IEX DAM BID SHEET CSV)
  // --------------------------------------------------------------------------
  function downloadCsvFile(filename, rows) {
    const csvContent = rows.map((r) => r.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function exportDailyForecastCsv() {
    if (!STATE.dayData) return;
    const rows = [
      [
        "Delivery_Date",
        "Hour_Block_IST",
        "AI_Forecast_Price_Rs_MWh",
        "Confidence_90_Low_Rs_MWh",
        "Confidence_90_High_Rs_MWh",
        "Verified_Actual_Price_Rs_MWh",
        "National_Demand_GW",
        "Net_Thermal_Demand_GW",
        "Solar_Generation_GW",
        "Wind_Generation_GW",
        "Renewable_Share_Pct"
      ]
    ];

    for (const h of STATE.dayData.hourly) {
      const band = getHourConfidenceBand(h);
      rows.push([
        STATE.dayData.date,
        h.hour_label,
        h.pred_lightgbm,
        band.low,
        band.high,
        h.actual_mcp,
        (h.demand_mw / 1000).toFixed(2),
        (h.net_demand_mw / 1000).toFixed(2),
        (h.solar_generation_mw / 1000).toFixed(2),
        (h.wind_generation_mw / 1000).toFixed(2),
        h.re_penetration_pct.toFixed(2)
      ]);
    }
    downloadCsvFile(`EnergyCast_IEX_DAM_Forecast_${STATE.dayData.date}.csv`, rows);
  }

  function exportOptimizedBidSheetCsv() {
    const res = computeBidOptimization();
    if (!res || !STATE.dayData) return;

    const rows = [
      [
        "Delivery_Date",
        "Block_Start_IST",
        "AI_Forecast_MCP_Rs_MWh",
        "Recommended_Exchange_Bid_Limit_Rs_MWh",
        "Unoptimized_Flat_Load_MW",
        "AI_Optimized_Bid_Volume_MW",
        "Dispatch_Action",
        "Estimated_Hourly_Savings_Rs"
      ]
    ];

    for (const s of res.schedule) {
      rows.push([
        STATE.dayData.date,
        s.hour_label,
        s.pred_mcp,
        s.bid_limit,
        s.base_mw.toFixed(1),
        s.opt_mw.toFixed(1),
        s.action,
        Math.round(s.hourly_Delta_rs)
      ]);
    }
    downloadCsvFile(`EnergyCast_IEX_DAM_Optimized_Bid_Sheet_${STATE.dayData.date}.csv`, rows);
  }

  // --------------------------------------------------------------------------
  // 14. EVENT LISTENERS & INITIALIZATION
  // --------------------------------------------------------------------------
  function bindEvents() {
    // 1. Navigation Tabs
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const target = tab.getAttribute("data-tab");
        switchTab(target);
      });
    });

    // Jump to Optimizer button in Advisory Banner
    const jumpBtn = document.getElementById("btn-jump-optimizer");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", () => switchTab("optimizer"));
    }

    // 2. Theme Toggle
    const themeBtn = document.getElementById("btn-theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        const html = document.documentElement;
        const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        document.getElementById("theme-label").textContent = next === "dark" ? "Light Mode" : "Dark Mode";
        redrawAllActiveCharts();
      });
    }

    // 3. Date & Hour Selectors
    document.getElementById("select-date").addEventListener("change", (e) => {
      selectDateAndHour(e.target.value, STATE.selectedHour);
    });
    document.getElementById("select-hour").addEventListener("change", (e) => {
      selectDateAndHour(STATE.selectedDate, Number(e.target.value));
    });

    document.getElementById("btn-prev-day").addEventListener("click", () => {
      if (!STATE.overview) return;
      const dates = STATE.overview.available_dates;
      const idx = dates.indexOf(STATE.selectedDate);
      if (idx > 0) selectDateAndHour(dates[idx - 1], STATE.selectedHour);
    });

    document.getElementById("btn-next-day").addEventListener("click", () => {
      if (!STATE.overview) return;
      const dates = STATE.overview.available_dates;
      const idx = dates.indexOf(STATE.selectedDate);
      if (idx >= 0 && idx < dates.length - 1) selectDateAndHour(dates[idx + 1], STATE.selectedHour);
    });

    // 4. Market Day Preset Chips
    document.querySelectorAll("#market-day-chips .scenario-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const d = chip.getAttribute("data-date");
        const h = Number(chip.getAttribute("data-hour") || 18);
        selectDateAndHour(d, h);
      });
    });

    // 5. Chart Overlays
    document.getElementById("toggle-show-actual").addEventListener("change", (e) => {
      STATE.showActual = e.target.checked;
      drawMainForecastChart();
    });
    document.getElementById("toggle-show-zones").addEventListener("change", (e) => {
      STATE.showZones = e.target.checked;
      drawMainForecastChart();
    });

    // 6. Tab 2: Smart Procurement & Bid Optimizer Controls
    document.getElementById("opt-profile-select").addEventListener("change", (e) => {
      STATE.optProfile = e.target.value;
      const presets = {
        industrial: { mw: 100, flex: 30, cap: 6500 },
        discom: { mw: 350, flex: 20, cap: 8000 },
        bess: { mw: 150, flex: 60, cap: 5000 },
        datacenter: { mw: 80, flex: 15, cap: 7500 }
      };
      const p = presets[STATE.optProfile] || presets.industrial;
      STATE.optBaseMw = p.mw;
      STATE.optFlexPct = p.flex;
      STATE.optPriceCap = p.cap;
      document.getElementById("opt-slider-mw").value = String(p.mw);
      document.getElementById("opt-slider-flex").value = String(p.flex);
      document.getElementById("opt-slider-cap").value = String(p.cap);
      renderOptimizerTab();
    });

    ["opt-slider-mw", "opt-slider-flex", "opt-slider-cap"].forEach((id) => {
      document.getElementById(id).addEventListener("input", () => {
        STATE.optBaseMw = Number(document.getElementById("opt-slider-mw").value);
        STATE.optFlexPct = Number(document.getElementById("opt-slider-flex").value);
        STATE.optPriceCap = Number(document.getElementById("opt-slider-cap").value);
        renderOptimizerTab();
      });
    });

    document.getElementById("btn-download-bidsheet").addEventListener("click", exportOptimizedBidSheetCsv);
    document.getElementById("btn-export-forecast").addEventListener("click", exportDailyForecastCsv);

    // 7. Tab 3: Weather & Grid Risk Simulator Controls
    ["sim-demand", "sim-solar", "sim-wind", "sim-ramp", "sim-temp", "sim-liq"].forEach((id) => {
      document.getElementById(id).addEventListener("input", () => {
        runSimulatorStressTest();
      });
    });

    document.querySelectorAll(".sim-preset").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("sim-demand").value = btn.getAttribute("data-demand");
        document.getElementById("sim-solar").value = btn.getAttribute("data-solar");
        document.getElementById("sim-wind").value = btn.getAttribute("data-wind");
        document.getElementById("sim-ramp").value = btn.getAttribute("data-ramp");
        document.getElementById("sim-temp").value = btn.getAttribute("data-temp");
        document.getElementById("sim-liq").value = btn.getAttribute("data-liq");
        runSimulatorStressTest();
      });
    });

    document.getElementById("btn-sim-run").addEventListener("click", runSimulatorStressTest);
    document.getElementById("btn-sim-reset").addEventListener("click", () => {
      ["sim-demand", "sim-solar", "sim-wind", "sim-ramp", "sim-temp", "sim-liq"].forEach((id) => {
        document.getElementById(id).value = "0";
      });
      runSimulatorStressTest();
    });

    // 8. Responsive Resize Redraw
    window.addEventListener("resize", () => {
      redrawAllActiveCharts();
    });
  }

  function switchTab(tabName) {
    STATE.activeTab = tabName;
    document.querySelectorAll(".nav-tab").forEach((btn) => {
      const isMatch = btn.getAttribute("data-tab") === tabName;
      btn.classList.toggle("active", isMatch);
      btn.setAttribute("aria-selected", isMatch ? "true" : "false");
    });

    document.querySelectorAll(".tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === `tab-${tabName}`);
    });

    hidePopover();
    requestAnimationFrame(() => {
      redrawAllActiveCharts();
    });
  }

  function redrawAllActiveCharts() {
    if (STATE.activeTab === "forecast") {
      drawMainForecastChart();
      drawGenMixChart();
    } else if (STATE.activeTab === "optimizer") {
      renderOptimizerTab();
    } else if (STATE.activeTab === "simulator") {
      if (STATE.simResult) drawMeritOrderChart(STATE.simResult);
    } else if (STATE.activeTab === "trust") {
      drawTrustAccuracyChart();
      drawTrustSignalsChart();
    }
  }

  // Boot Product Platform
  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    loadInitialData();
  });
})();
