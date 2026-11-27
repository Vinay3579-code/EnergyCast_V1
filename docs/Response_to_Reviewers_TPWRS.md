# Point-by-Point Response to Peer-Review Comments (SDP / IEEE TPWRS Revision)

**Revised Manuscript Title:**
*Causality-Aware Renewable-Integrated Electricity Price Forecasting and Risk-Constrained Procurement Optimization for Day-Ahead Power Markets*

We thank the reviewer for the rigorous, constructive, power-systems-oriented evaluation. Every critical weakness (A–E), all five recommended priority experiments, the Stochastic CVaR procurement formulation, and the revised manuscript positioning have been fully executed on real operational data and integrated into both the **IEEE TPWRS** (`EnergyCast_IEEE_Paper.zip`) and **Springer LNCS** (`EnergyCast_Springer_Paper.zip`) manuscripts.

---

## Summary of Changes & Quantitative Evidence

### 1. Critical Weakness A & Priority 1: Eliminating D-1 Information Leakage via True Stage-1 Forecast Reconstruction
* **Reviewer Concern:** The previous manuscript claimed a strict 10:30 AM IST $D-1$ information boundary while using realized delivery-day demand, solar, and wind trajectories ($\ell \in \{0,1,24\}$) and same-day price lags.
* **Resolution Executed (`src/build_causal_d1_dataset.py`, Section 3.1–3.2, Table 2, Table 7, Fig. 6(a)):**
  1. **Removed all inadmissible inputs:** Permanently removed all same-day price lags ($P_{D, h-1}, P_{D, h-2}$, rolling windows ending at $t-1$), all contemporaneous Day-$D$ realized demand/solar/wind/weather values, and all unrealized afternoon $D-1$ SCADA observations ($> 10:00$ AM IST on $D-1$).
  2. **Stage-1 Causal Day-Ahead Forecast Reconstruction:** Built dedicated Stage-1 LightGBM forecasters conditioned strictly on $\mathcal{F}_{D-1, 10:30}$ (SCADA/weather $\le D-1$ 10:00 AM IST, $D-2..D-14$ full-day lags, deterministic astronomical solar elevation angle, Indian public holidays, and published $D-1$ IEX schedules) using 5-fold temporally blocked & purged (48h gap) Out-of-Fold CV on Train (2022–2023) and expanding splits on Val (2024) and Test (2025).
     * **Verified Stage-1 Test-2025 Quality:** National Gross Demand `MAPE = 2.46%` (`nRMSE = 5.05%`, $R^2 = 0.8611$), Utility Solar `nRMSE = 11.17%` ($R^2 = 0.9053$), Utility Wind `nRMSE = 10.18%`, 5-Zone Mean Temperature `MAE = 0.48 °C` ($R^2 = 0.9798$), and derived Net Thermal Demand `MAPE = 4.24%`.
  3. **Transparent Information-Boundary Ablation Audit (Table 7A, Fig. 6(a)):** Explicitly contrasts:
     * Strict Operational D-1 (Static Frozen 2022–2023 LightGBM): Test MAE `Rs. 626.89/MWh`
     * Strict Operational D-1 (Expanding Operational LightGBM): Test MAE `Rs. 496.71/MWh` (`-Rs. 130.18/MWh` recalibration gain)
     * Strict Operational D-1 (Expanding Hybrid GBDT+TFT Champion): Test MAE **`Rs. 481.19/MWh`** ($R^2 = 0.8942$, `+26.92%` vs. 24h S-Naive)
     * Ex-Post Perfect-Exogenous Upper Bound (realized Day-$D$ grid/weather, still zero $P_{t-1}$): LightGBM MAE `Rs. 491.84/MWh` (quantifying Value of Perfect Exogenous Forecasts = `+Rs. 4.87/MWh`, $DM = +0.77$)
     * Audited Legacy V1 Specification (with inadmissible $P_{t-1}$): `Rs. 433.33/MWh` (quantifying the exact look-ahead bias removed).

---

### 2. Critical Weakness B & Priority 3: Independent Physical Validation of the Scarcity Threshold Using Real NLDC Fuel-Mix SCADA
* **Reviewer Concern:** A TreeSHAP plot alone does not establish a physical merit-order threshold; independent dispatch evidence, fuel-mix analysis, seasonal/yearly stability, and threshold sensitivity are required.
* **Resolution Executed (`src/extract_grid_india_fuel_mix.py`, `src/validate_physical_merit_order.py`, Section 3.6 & 4.2, Tables 4–5, Fig. 2):**
  1. **Extracted Real POSOCO/NLDC Fuel-Mix SCADA (`15,350` hourly observations, Apr 2022 – Dec 2023):** Direct coal/thermal-only (`TOTAL_THM_ONLY|P`), hydro (`TOTAL_NLDC_HYD|P`), gas (`TOTAL_NLDC_GAS|P`), nuclear (`TOTAL_NLDC_NPC|P`), solar, and wind telemetry.
  2. **Physical Dispatch Proof (Table 4, Fig. 2(a)):** Below 160 GW, domestic coal absorbs `81.2%` of incremental net demand (`0.812 GW/GW`), hydro supplies `0.175 GW/GW`, gas remains flat (`0.0165 GW/GW`), and CERC cap hits stay `< 2.7%`. Above 160 GW (as coal utilization climbs from `85.4%` to `92.5%` of peak output), marginal coal response saturates (`0.812 -> 0.544 GW/GW`), hydro peaking doubles (`0.175 -> 0.351 GW/GW`), gas-peaker response surges **6.5×** (`16.5 -> 107.8 MW/GW`, direct Sup-Wald on gas MW yields $F = 5,641.4$, P90 gas climbs from `2.47 GW` to `7.40 GW`), and cap-hit probability surges to `10.5%` (160–165 GW), `27.1%` (165–175 GW), and `64.8%` (`> 175 GW`).
  3. **Retracted Static 160 GW Claim & Proved Dynamic Capacity-Driven Migration (Table 5, Fig. 2(b)):** Independent Hansen Sup-Wald structural-break sweeps across 140–180 GW prove that the optimal scarcity knee is **non-stationary**, migrating +22 GW upward as thermal capacity expanded: **152.0 GW (2022, $F=1,560$)** $\to$ **156.0 GW (2023, $F=1,036$)** $\to$ **169.0 GW (2024, $F=1,844$)** $\to$ **174.0 GW (2025, $F=1,480$)**, and shifting seasonally across **Winter (151 GW)**, **Monsoon (159 GW)**, and **Summer (188 GW)**. This physical finding directly motivated our trailing 30-day capacity-relative features (`nd_fcst_rel_30d`, `nd_fcst_zscore_30d`).

---

### 3. Critical Weakness D & Priority 2: Strengthened 13-Model Benchmarks & Calibrated Probabilistic Forecasting
* **Reviewer Concern:** Add SARIMAX, LASSO, Elastic Net, Random Forest, CatBoost, N-BEATS, Temporal Fusion Transformer (TFT), and calibrated probabilistic forecasts.
* **Resolution Executed (`src/train_v2_benchmarks_and_probabilistic.py`, Section 3.4–3.5 & 4.3–4.5, Tables 6 & 8, Figs. 3–5):**
  1. **All 13 Requested Models Benchmarked Across 4 Tiers on Strict D-1 Test 2025 (`4,200h`):**
     * Tier 1: Weekly S-Naive (`986.82`), Daily S-Naive (`658.42`)
     * Tier 2: 24-Equation Seasonal SARIMAX (`685.13`, RMSE `-16.2%`), OLS (`683.45`), Ridge (`648.50`), LASSO (`631.89`), Elastic Net (`619.74`)
     * Tier 3: CatBoost (`527.63`), Random Forest (`515.16`), XGBoost (`508.51`), LightGBM (`496.71`)
     * Tier 4: PyTorch N-BEATS (`578.33`), PyTorch Temporal Fusion Transformer (`517.84`, best single-model Peak MAE `778.99`)
     * Validation-Selected Champion: **Hybrid GBDT+TFT Ensemble** (`Test MAE = Rs. 481.19/MWh`, `RMSE = Rs. 875.27`, $R^2 = 0.8942$, `Peak MAE = Rs. 754.18`, `+26.92%` vs. 24h S-Naive, beating every single competitor via Newey-West HAC $L=9$ Diebold-Mariano tests: $DM = +2.28$ to $+15.64$).
  2. **Probabilistic Forecasting (`Residual-CQR` + 200-Scenario Copula, Table 8 & Fig. 5(b)):**
     * Regime-Conditional Residual-CQR achieves `Mean Pinball = Rs. 145.37/MWh`, `CRPS = Rs. 290.73/MWh` (`-20.6%` vs. Homoskedastic Gaussian), `Winkler-90 = Rs. 2,906.3`, sharp `90% Width = Rs. 1,774.0/MWh`, empirical coverage **`PICP 50% = 49.02%`**, **`PICP 80% = 81.67%`**, **`PICP 90% = 90.69%`** (**sole model passing the Kupiec LR test at $p = 0.1317$**), and **`91.50%` coverage on extreme $\ge$Rs. 8,000 spikes**.

---

### 4. Critical Weakness C & Priority 4: Multi-Profile Constrained & Stochastic CVaR Procurement Optimization
* **Reviewer Concern:** Single hypothetical 100 MW winter case is insufficient; add multiple industrial load profiles, flexibility sweep (10–40%), ramp & recovery constraints, uncertainty-aware $\mathbb{E}[\sum L_h P_h] + \lambda \operatorname{CVaR}_{\alpha}(C)$ formulation, rule-based benchmarks, and realized vs. simulated savings over the full test horizon.
* **Resolution Executed (`src/run_stochastic_cvar_procurement.py`, Section 3.7 & 4.6, Table 9, Fig. 7):**
  1. **Exact Rockafellar-Uryasev Stochastic CVaR LP** solved via HiGHS across **all 175 unseen test days (Jan–Jun 2025)** over `200` Gaussian Copula correlated 24-hour price trajectories per day, subject to daily energy neutrality, flexibility bounds ($\gamma \in \{10\%, 20\%, 30\%, 40\%\}$), cyclic inter-hour ramp limits ($20\%\text{--}35\%$/h), anti-chattering dwell smoothness, and rolling energy payback buffers ($2.5\text{--}4.0\text{h}$).
  2. **Multi-Profile Realized Out-of-Sample Savings (Evaluated on TRUE IEX MCP):**
     * **P1 Continuous Industrial (100 MW, $\gamma=30\%$):** Simulated `9.12%` vs. **Realized `9.06%`** (`Rs. 9.68L/day`, `Rs. 35.32 Cr/yr`, `98.8%` of Constrained Oracle, vs. `5.31%` Rule-Based ToU; `100%` winning days). *(Also transparently contrasts unconstrained LP `12.18%` to show the physical cost of ramp/buffer limits.)*
     * **P2 Two-Shift Manufacturing (100 MW, $\gamma=25\%$):** Simulated `7.71%` vs. **Realized `7.64%`** (`Rs. 28.63 Cr/yr`, `98.3%` Oracle Efficiency, vs. `4.96%` ToU).
     * **P3 State DISCOM Portfolio (350 MW, $\gamma=20\%$):** Simulated `5.59%` vs. **Realized `5.54%`** (`Rs. 75.07 Cr/yr`, `98.4%` Oracle Efficiency, vs. `3.26%` ToU).
     * **P4 Cold-Storage/Data Center (80 MW, $\gamma=35\%$):** Simulated `12.45%` vs. **Realized `12.37%`** (`Rs. 38.03 Cr/yr`, `98.8%` Oracle Efficiency, vs. `7.51%` ToU).
  3. **Flexibility Sensitivity & Risk-Aversion Frontier:** Monotonic scaling from `3.06%` ($\gamma=10\%$) to `11.87%` ($\gamma=40\%$) realized savings, with monotonic reduction in both ex-ante and realized $\operatorname{CVaR}_{0.90}$ tail daily bills as $\lambda$ increases from `0` to `2.0`.

---

### 5. Critical Weakness E & Priority 5: Comprehensive Stress Testing & Seasonal/Extreme Robustness
* **Reviewer Concern:** Expand counterfactual tests to Solar/Wind `-10%..-40%`, Demand `+5%..+15%`, unexpected thermal outages, and compound heatwave/multi-disturbance scenarios, reporting price, uncertainty, schedule, and financial risk impacts.
* **Resolution Executed (`src/run_v2_comprehensive_stress_tests.py`, Table 7B, Table 10, Fig. 8):**
  * Evaluated all **17 physical disturbance scenarios** across 4,200 test hours, demonstrating monotonic increases in point price (`+Rs. 17.4` to `+Rs. 286.2/MWh`), Residual-CQR uncertainty width $W_{90}$ (`+Rs. 5.6` to `+Rs. 355.5/MWh`, `+20.6%` under compound outage+heatwave+cloud+lull crisis), cap-hit risk (`19.9% -> 22.0%`), and proving consistent `Rs. 10.7–11.2 Lakhs/day` $\operatorname{CVaR}_{0.90}$ tail-risk reduction by the Stochastic CVaR optimizer across every disturbance.
  * Seasonal and extreme-event robustness (Table 7B) confirms `+18.6%` to `+35.7%` MAE reductions across Winter, Spring, Summer/Monsoon, Weekends, Solar Troughs, Evening Peaks, High-Price Spikes ($\ge$Rs. 8k), and CERC Cap Hits ($\ge$Rs. 9,990), with CQR 90% coverage maintained between `88.8%` and `94.7%`.

---

### 6. Manuscript Repositioning & Title Revision
* Adopted the recommended power-systems title (*"Causality-Aware Renewable-Integrated Electricity Price Forecasting and Risk-Constrained Procurement Optimization for Day-Ahead Power Markets"*).
* Positioned strict D-1 operational causality, physical merit-order dispatch validation, conformalized probabilistic uncertainty, and stochastic CVaR procurement optimization as the core contributions, retaining exact operational TreeSHAP (`32.2%` Stage-1 grid/RE innovation share) as a transparent supporting layer.
