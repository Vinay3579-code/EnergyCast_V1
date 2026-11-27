# EnergyCast — Causality-Aware Renewable-Integrated Electricity Price Forecasting & Risk-Constrained Procurement Optimization

**EnergyCast** is an end-to-end quantitative electricity price forecasting, conformalized probabilistic uncertainty, independent physical merit-order validation, and stochastic Conditional Value-at-Risk (CVaR) procurement optimization platform built for the **Indian Energy Exchange (IEX) Day-Ahead Market (DAM)**.

Harmonizing **28,344 hourly records** (April 2022 – June 2025) across **IEX DAM auctions**, **Grid-India (POSOCO) NLDC SCADA** (gross load, solar, wind, plus **15,350 hours** of coal, hydro, gas, and nuclear generation dispatch), and **5-zone demand-weighted ERA5 meteorology**, the platform bridges power-systems rigor with an interactive commercial trading command center.

---

## Quick Launch: Interactive Web Command Center

### Mode A: Live Python Multi-Model & Real-Time Stress-Testing Server *(Recommended)*
```powershell
uv run python app/main.py --open
```
* Launches `http://127.0.0.1:8501` in your browser.
* Serves live in-memory inference across LightGBM, XGBoost, Ridge, and OLS models with real-time TreeSHAP attribution (`~3.4 ms` simulation latency), bid optimization, and IEX CSV bid-sheet export.

### Mode B: Standalone Zero-Server Browser Mode
Open [`app/static/index.html`](app/static/index.html) directly in Chrome, Edge, or Firefox to explore all 175 unseen 2025 test days (`4,200` hours) offline via the pre-compiled bundle (`app/static/embedded_data.js`).

---

## Key Empirical Results (Strict 10:30 AM IST D-1 Operational Causality)

All benchmarks enforce the strict **$\mathcal{F}_{D-1, 10:30}$** auction information boundary (zero same-day price lags $P_{D, h-1}$ and zero realized delivery-day $D$ demand/RE/weather telemetry). Stage-1 causal exogenous forecasters reconstruct day-ahead demand (`2.46%` Test-2025 MAPE), solar (`11.17%` nRMSE), wind (`10.18%` nRMSE), and 5-zone temperature (`0.48 °C` MAE).

### 1. 4-Tier 13-Model Forecasting Leaderboard (Unseen Test 2025: 4,200 Hours)

| Tier | Model Architecture (Strict $\mathcal{F}_{D-1, 10:30}$) | Val 2024 MAE | Test 2025 MAE | Test RMSE | sMAPE | Test $R^2$ | Peak MAE (18–22h) | Gain vs. 24h | DM HAC ($L=9$) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Tier 1** | Weekly Seasonal Naive (168h) | ₹903.60 | ₹986.82 | ₹1,750.12 | 23.21% | 0.5770 | ₹1,279.88 | -49.88% | +13.196 |
| **Tier 1** | Daily Seasonal Naive (24h Ref.) | ₹629.84 | ₹658.42 | ₹1,254.07 | 16.52% | 0.7828 | ₹1,125.36 | Baseline | +9.641 |
| **Tier 2** | SARIMAX (24-Eq. Seasonal) | ₹734.88 | ₹685.13 | ₹1,050.89 | 18.07% | 0.8475 | ₹1,019.19 | -4.06% | +14.294 |
| **Tier 2** | OLS Linear Regression | ₹701.98 | ₹683.45 | ₹1,034.03 | 17.01% | 0.8523 | ₹994.92 | -3.80% | +15.366 |
| **Tier 2** | Tikhonov Ridge ($\alpha=2500$) | ₹677.38 | ₹648.50 | ₹1,026.26 | 16.23% | 0.8545 | ₹989.23 | +1.51% | +15.640 |
| **Tier 2** | LASSO $L_1$ ($\alpha=60$) | ₹645.06 | ₹631.89 | ₹1,059.15 | 15.40% | 0.8451 | ₹1,020.59 | +4.03% | +14.107 |
| **Tier 2** | Elastic Net ($\alpha=1.5, \rho=0.2$) | ₹634.94 | ₹619.74 | ₹1,079.79 | 15.13% | 0.8390 | ₹1,023.00 | +5.87% | +12.959 |
| **Tier 3** | CatBoost Regressor (Depth 6) | ₹555.95 | ₹527.63 | ₹1,000.81 | 13.03% | 0.8617 | ₹853.79 | +19.86% | +5.516 |
| **Tier 3** | Random Forest (220 Trees) | ₹675.34 | ₹515.16 | ₹877.06 | 13.27% | 0.8938 | ₹798.54 | +21.76% | +4.273 |
| **Tier 3** | XGBoost Regressor (Depth 6) | ₹549.74 | ₹508.51 | ₹962.35 | 12.94% | 0.8721 | ₹810.92 | +22.77% | +3.894 |
| **Tier 3** | LightGBM Regressor (47 Leaves) | ₹554.78 | ₹496.71 | ₹948.64 | 12.47% | 0.8757 | ₹791.75 | +24.56% | +2.279 |
| **Tier 4** | PyTorch N-BEATS (Multi-Stack) | ₹580.74 | ₹578.33 | ₹1,034.96 | 15.00% | 0.8521 | ₹924.46 | +12.16% | +9.364 |
| **Tier 4** | PyTorch Temporal Fusion Transformer | ₹559.43 | ₹517.84 | ₹905.66 | 13.70% | 0.8867 | ₹778.99 | +21.35% | +4.227 |
| **Tier 4+** | **Hybrid Champion (GBDT + TFT)** | **₹516.64** | **₹481.19** | **₹875.27** | **12.45%** | **0.8942** | **₹754.18** | **+26.92%** | **Champion** |

### 2. Probabilistic Calibration (`Residual-CQR`)
* **Mean Pinball Loss:** `₹145.37/MWh` | **CRPS:** `₹290.73/MWh` (`-20.6%` vs. Homoskedastic Gaussian)
* **Empirical Coverage (Test 2025):** `PICP 50% = 49.02%`, `PICP 80% = 81.67%`, **`PICP 90% = 90.69%`** (passes Kupiec LR test at $p = 0.1317$; `91.50%` coverage during extreme $\ge ₹8,000$ spikes; sharp 90% width `₹1,774/MWh`).

### 3. Independent Physical Merit-Order Validation (15,350h NLDC SCADA)
* **Coal Saturation & Gas Peaker Surge:** Above the pooled `160 GW` transition zone, marginal coal dispatch drops from `0.812` to `0.544 GW/GW`, hydro peaking doubles (`0.175` $\to$ `0.351 GW/GW`), gas-peaker response surges **6.5×** (`16.5` $\to$ `107.8 MW/GW`, Sup-Wald $F = 5,641.4$), and CERC cap-hit probability jumps from `2.7%` to `64.8%` (`>175 GW`).
* **Dynamic Scarcity Knee Migration:** Independent Hansen Sup-Wald tests prove the scarcity knee shifts upward with thermal capacity expansion: **152 GW (2022)** $\to$ **156 GW (2023)** $\to$ **169 GW (2024)** $\to$ **174 GW (2025)** ($F > 1,036$ every year).

### 4. Stochastic CVaR-Constrained Procurement Optimization (All 175 Test Days)
Exact Rockafellar-Uryasev LP (`scipy.optimize.linprog` HiGHS) minimizing $\mathbb{E}[\sum L_h P_h] + \lambda \operatorname{CVaR}_{0.90}(C)$ over 200 Gaussian Copula scenarios with energy neutrality, ramp limits, dwell smoothness, and rolling payback buffers:
* **P1 Flat Industrial (100 MW, $\gamma=30\%$):** **9.06% realized bill reduction** (`₹9.68L/day`, `₹35.32 Cr/yr`, `98.8%` Oracle efficiency vs. `5.31%` Rule-Based ToU; `100%` winning days).
* **P2 Two-Shift Manufacturing (100 MW, $\gamma=25\%$):** **7.64% realized savings** (`₹28.63 Cr/yr`, `98.3%` Oracle efficiency).
* **P3 State DISCOM Portfolio (350 MW, $\gamma=20\%$):** **5.54% realized savings** (`₹75.07 Cr/yr`, `98.4%` Oracle efficiency).
* **P4 Cold-Storage / Data Center (80 MW, $\gamma=35\%$):** **12.37% realized savings** (`₹38.03 Cr/yr`, `98.8%` Oracle efficiency).

---

## Repository Structure

```text
EnergyCast_V1/
├── app/                         # Python REST API (main.py) & 4-tab HTML5 Canvas Web UI (static/)
├── data/
│   ├── raw/                     # Raw IEX DAM, Grid-India NLDC SCADA, and city weather archives
│   └── processed/               # Master panel, fuel-mix SCADA, causal_d1/ splits, features/
├── models/                      # Trained V1 and V2 strictly causal model binaries (.joblib)
├── outputs/
│   ├── tables/                  # Verified V1 & V2 benchmark, CQR, merit-order, CVaR, stress CSVs
│   ├── predictions/             # Test predictions & 200-scenario Copula trajectories (.npz)
│   └── paper_figures_v2/        # 8 publication-grade figures for IEEE TPWRS & Springer LNCS
├── docs/                        # Revised IEEE & Springer LaTeX papers, Reviewer Response & Web Guide
└── src/                         # Complete end-to-end reproducible Python pipeline scripts
```

---

## Reproducing the Full V2 Pipeline

```powershell
# 1. Extract 15,350 hours of Grid-India NLDC Coal/Hydro/Gas/Nuclear SCADA telemetry
uv run python src/extract_grid_india_fuel_mix.py

# 2. Run independent physical merit-order & Hansen Sup-Wald dynamic knee validation
uv run python src/validate_physical_merit_order.py

# 3. Build strict 10:30 AM IST D-1 Stage-1 exogenous forecasts & 65-signal causal splits
uv run python src/build_causal_d1_dataset.py

# 4. Train all 13 models (Tiers 1-4), Hybrid Champion, Residual-CQR & 200 Copula scenarios
uv run python src/train_v2_benchmarks_and_probabilistic.py

# 5. Run multi-profile Rockafellar-Uryasev Stochastic CVaR procurement across 175 test days
uv run python src/run_stochastic_cvar_procurement.py

# 6. Run 17-scenario weather, renewable & thermal outage stress-test suite
uv run python src/run_v2_comprehensive_stress_tests.py

# 7. Regenerate all 8 publication figures
uv run python src/generate_v2_paper_figures.py
```
