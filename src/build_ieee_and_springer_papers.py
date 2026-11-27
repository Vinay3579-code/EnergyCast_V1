r"""
Builds complete, publication-ready 12+ page LaTeX Research Papers for EnergyCast
in BOTH:
  1. IEEE Format (`v:\College\7th SEM\SDP\IEEE_Paper\`) -> `EnergyCast_IEEE_Paper.zip`
  2. Springer LNCS Format (`v:\College\7th SEM\SDP\Springer_Paper\`) -> `EnergyCast_Springer_Paper.zip`
  3. Combined Bundle (`v:\College\7th SEM\SDP\EnergyCast_Research_Papers_IEEE_and_Springer.zip`)

Key Formatting Guarantees:
  1. Every equation (Eq. 1 to Eq. 22) uses narrow single-line or multi-line `aligned`
     blocks (< 5.5 cm wide per line) so NO formula ever overflows a column or overlaps
     with equation numbers or text in either IEEE two-column or Springer single-column mode.
  2. Every table (Table 1 to Table 6) is wrapped in `\resizebox{\textwidth}{!}{...}` inside
     full-width floats (`table*` in IEEE, `table` in Springer) so NO table ever goes out of
     the page or overlaps with text.
  3. Both algorithms (Algorithm 1 & Algorithm 2) use full-width `algorithm*` in IEEE and
     concise pseudocode lines so they never overflow into adjacent columns.
  4. Zero bold text (`\textbf` or `\mathbf`) is used anywhere in the paper prose, lists,
     equations, algorithms, or tables.
"""

from __future__ import annotations

import pathlib
import shutil
import zipfile

SDP_ROOT = pathlib.Path(r"v:\College\7th SEM\SDP")
PROJ_ROOT = SDP_ROOT / "EnergyCast_V1"
PAPER_FIG_DIR = PROJ_ROOT / "outputs" / "paper_figures"

IEEE_DIR = SDP_ROOT / "IEEE_Paper"
SPRINGER_DIR = SDP_ROOT / "Springer_Paper"


# ==============================================================================
# SHARED CORE CONTENT (SECTIONS 1 TO 6 + EQUATIONS + ALGORITHMS + TABLES + BIB)
# ==============================================================================
def get_core_body(is_ieee: bool) -> str:
    tbl_env = "table*" if is_ieee else "table"
    fig_wide_env = "figure*" if is_ieee else "figure"
    alg_env = "algorithm*" if is_ieee else "algorithm"
    fig_width_wide = r"0.95\textwidth" if is_ieee else r"0.96\textwidth"

    body = r"""
\section{Introduction}
The rapid decarbonization of modern power grids and the accelerating integration of utility-scale solar photovoltaic (PV) and wind generation have fundamentally altered the price formation mechanics of wholesale electricity markets \cite{weron2014electricity,lago2021forecasting}. In the Indian Energy Exchange (IEX) Day-Ahead Market (DAM), which clears over 70\% of India's short-term traded electricity across 96 fifteen-minute blocks daily through a blind double-sided uniform-price auction, renewable energy penetration has introduced pronounced diurnal non-stationarity, steep evening net-load ramps, and frequent price spikes reaching the statutory Central Electricity Regulatory Commission (CERC) ceiling of Rs.~10,000/MWh \cite{cerc2023order,iex2024market}. Distribution Companies (DISCOMs), industrial open-access consumers, and merchant thermal generators must submit their price-quantity bid curves prior to the strict 10:30~AM Indian Standard Time (IST) auction gate on day $D-1$ for all 24 delivery hours of day $D$ without knowledge of subsequent market clearing outcomes.

Traditional electricity price forecasting (EPF) systems deployed by utility trading desks rely either on heuristic seasonal persistence baselines (such as yesterday's same-hour clearing price or last week's profile) or linear autoregressive econometric specifications \cite{contreras2003arima,conejo2005day}. While computationally simple, linear econometric models fail to capture the piece-wise convex topology of the national generation merit-order supply stack. Specifically, during midday solar peaks (10:00--15:00~IST), zero-marginal-cost solar injection suppresses clearing prices into a depressed solar trough (Rs.~2,400--Rs.~3,100/MWh). Conversely, as solar generation collapses between 16:00 and 19:00~IST simultaneously with rising residential and industrial lighting demand, the national grid experiences a +12 to +18~GW net thermal ramp within three hours. When net thermal load crosses the critical 160~GW baseload coal capacity threshold, high-heat-rate open-cycle gas turbines and liquid-fuel peakers set the marginal clearing price, triggering abrupt, non-linear price surges toward the Rs.~10,000/MWh regulatory cap \cite{posoco2024report}.

Conversely, recent deep learning approaches for EPF---including Long Short-Term Memory (LSTM) networks, Temporal Fusion Transformers (TFT), and deep hybrid convolutional-recurrent ensembles \cite{ugurlu2018electricity,lehna2022forecasting}---suffer from three critical operational barriers in commercial power trading desks:
\begin{enumerate}
    \item Opaque black-box inference: Utility procurement officers and state regulatory commissions cannot audit why a deep neural network predicts a Rs.~9,500/MWh scarcity spike, preventing traders from defending high-value hedge positions during financial audits.
    \item Subtle temporal data leakage: Many published EPF studies inadvertently incorporate same-day ($D$) realized demand, unlagged clearing volumes, or random cross-validation splits that violate the strict 10:30~AM IST $D-1$ auction gate, yielding artificially inflated accuracy metrics that collapse in live production \cite{lago2021forecasting}.
    \item Disconnect between forecasting and procurement optimization: Existing academic frameworks treat point-price error minimization as the terminal objective, failing to translate hourly forecasts and uncertainty bounds into energy-neutral load-shifting schedules or counterfactual weather stress tests.
\end{enumerate}

In this paper, we present the design, mathematical formulation, implementation, and rigorous econometric evaluation of EnergyCast, an end-to-end causal day-ahead electricity price forecasting, exact game-theoretic attribution, and energy-neutral procurement optimization system engineered for the Indian Energy Exchange (IEX) Day-Ahead Market. Evaluated across a multi-year dataset spanning 28,176 clean hourly observations (April 2022 to June 2025) that integrates IEX DAM auction records, Grid-India (POSOCO) national generation telemetry, and 5-zone demand-weighted ERA5 meteorological reanalysis, EnergyCast bridges the gap between high-precision machine learning and auditable utility decision support. The core contributions of this research are:
\begin{itemize}
    \item A leak-free 53-signal causal feature engineering architecture that enforces a strict mathematical information boundary ($\mathcal{F}_{D-1, 10:30}$), fusing multi-horizon autoregressive price memory, physical net thermal demand ramps, lagged order-book tightness ratios, trigonometric Fourier harmonics, and quadratic cooling degree days ($CDD_{24}$) with zero forward look-ahead leakage.
    \item A three-tier progressive modeling hierarchy benchmarking seven models across Tier~1 seasonal naive baselines, Tier~2 $L_2$-regularized Tikhonov Ridge regression ($\alpha=50$) that resolves severe collinearity ($\text{VIF} > 40$), and Tier~3 histogram-based gradient-boosted decision trees (LightGBM and XGBoost) coupled with a CERC statutory boundary projection operator ($[\text{Rs.~0}, \text{Rs.~10,000}]/\text{MWh}$).
    \item Rigorous out-of-sample econometric verification on an unseen 4,200-hour chronological test split (January--June 2025), where our champion 282-tree LightGBM ensemble achieves a Mean Absolute Error (MAE) of Rs.~433.33/MWh (Rs.~0.43/kWh) and $R^2 = 0.9317$, outperforming the 24-hour market persistence baseline (Rs.~658.42/MWh) by 34.19\% and tuned Ridge regression (Rs.~544.61/MWh) by 20.43\%, verified via Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC, $L=9$) Diebold-Mariano testing ($DM = -7.780, p = 9.10 \times 10^{-15}$).
    \item Exact TreeSHAP rupee attribution and counterfactual merit-order stress simulation that decompose every hourly forecast into an unconditional base price ($\mathbb{E}[f(X)] = \text{Rs.~3,873.06/MWh}$) plus 53 exact rupee-per-MWh feature contributions, revealing the empirical 160~GW national peaker scarcity inflection point and enabling sub-4~ms weather stress testing and energy-neutral DISCOM load shifting (saving Rs.~12.73~Lakhs/day or 11.9\% on a 100~MW industrial portfolio).
\end{itemize}

The remainder of this paper is organized as follows: Section~2 reviews related work in electricity price forecasting and compares representative systems with EnergyCast; Section~3 details the system architecture, causal telemetry harmonization, 53-feature mathematical formulation, multi-tier learning algorithms, and energy-neutral bid optimization; Section~4 presents the experimental evaluation, Diebold-Mariano HAC hypothesis tests, TreeSHAP attributions, and counterfactual stress-test results; Section~5 discusses physical grid insights, operational trade-offs, limitations, and regulatory considerations; and Section~6 concludes the paper.

\section{Background and Related Work}
The scientific literature on short-term electricity price forecasting has evolved through four distinct methodological paradigms over the past two decades: statistical time-series econometrics, physical merit-order equilibrium models, machine learning ensembles, and deep neural architectures \cite{weron2014electricity,lago2021forecasting}.

\subsection{Statistical and Econometric Time-Series Models}
Early wholesale market forecasting relied on Autoregressive Integrated Moving Average (ARIMA), Seasonal ARIMA with Exogenous regressors (SARIMAX), and Generalized Autoregressive Conditional Heteroskedasticity (GARCH) models \cite{contreras2003arima,conejo2005day,ziel2018day}. Contreras et al.~\cite{contreras2003arima} applied ARIMA models to the Spanish and Californian power pools, demonstrating that 24-hour and 168-hour seasonal lags capture basic diurnal and weekly periodicity. Conejo et al.~\cite{conejo2005day} enhanced ARIMA models via wavelet decomposition, while Ziel and Weron~\cite{ziel2018day} systematically compared univariate and multivariate LASSO and elastic-net autoregressions across European power exchanges. However, linear parametric specifications assume constant marginal sensitivities across all operating regimes. In markets with high solar penetration such as IEX DAM, the marginal price effect of an additional gigawatt of load is near zero at 13:00~IST (when cheap solar and baseload coal have ample headroom) but exceeds Rs.~450/MWh per gigawatt at 19:00~IST (when the grid operates on the vertical segment of the thermal supply stack). Furthermore, standard Ordinary Least Squares (OLS) estimators suffer from severe variance inflation when fed correlated price lags, rolling windows, and meteorological polynomials.

\subsection{Gradient-Boosted Decision Trees and Deep Learning in EPF}
To capture non-linear regime switching, researchers have increasingly adopted non-parametric tree ensembles and deep learning \cite{ugurlu2018electricity,lago2018forecasting,tschora2022electricity,lehna2022forecasting}. Lago et al.~\cite{lago2018forecasting,lago2021forecasting} established open benchmarks comparing Deep Neural Networks (DNNs), LSTMs, and Gated Recurrent Units (GRUs) against statistical models across European markets, emphasizing that many complex deep learning architectures fail to beat well-tuned gradient-boosted trees on tabular energy data once temporal data leakage is eliminated. Ke et al.~\cite{ke2017lightgbm} introduced LightGBM with Gradient-based One-Side Sampling (GOSS) and Exclusive Feature Bundling (EFB), while Chen and Guestrin~\cite{chen2016xgboost} formalized second-order regularized XGBoost. On structured spatio-temporal energy tabular features, histogram-based GBDTs naturally partition the feature space at physical threshold knots (such as net demand exceeding 160~GW or market tightness exceeding $1.5\times$) without requiring parametric functional assumptions.

\subsection{Explainable AI (XAI) and Post-Auction Procurement Optimization}
Despite high predictive accuracy, ensemble models are traditionally viewed as opaque by power system operators. Lundberg and Lee~\cite{lundberg2017unified,lundberg2020local} unified cooperative game theory with local model explanations via SHapley Additive exPlanations (SHAP) and derived the exact polynomial-time TreeSHAP algorithm ($O(TLD^2)$) for tree ensembles. In the Indian power sector, existing studies on IEX DAM forecasting \cite{iex2024market,posoco2024report} have largely focused on isolated point-forecast metrics (RMSE or MAPE) over short 3-to-6 month windows without integrating national POSOCO renewable generation telemetry, Newey-West HAC autocorrelation-robust statistical testing \cite{diebold1995comparing,newey1987simple}, exact TreeSHAP rupee decomposition, or constrained DISCOM load-shifting optimization.

\begin{__TBL_ENV__}[!t]
\centering
\caption{Comparison of Representative Existing Electricity Price Forecasting Systems with the Proposed EnergyCast System}
\label{tab:related_work}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|p{2.8cm}|p{2.3cm}|p{2.7cm}|p{2.8cm}|p{2.2cm}|p{2.5cm}|p{2.7cm}|}
\hline
System / Study & Target Market & Model Architecture & Physical Grid \& RE Fusion & D-1 Gate Causality & Explainable AI (XAI) & Bid Optimizer \& Stress Sim. \\
\hline
Contreras et al. \cite{contreras2003arima} & Spain / Calif. Pool & Linear ARIMA & None (Price Lags Only) & Partial & Parametric Coeffs Only & No \\
\hline
Ziel \& Weron \cite{ziel2018day} & EPEX SPOT (Europe) & Multivariate LASSO & Basic Load Forecast & Yes & Linear Shrinkage & No \\
\hline
Ugurlu et al. \cite{ugurlu2018electricity} & Turkish EPIAS DAM & Multi-Layer GRU / LSTM & No Multi-Zone Weather & Unverified & None (Black-Box) & No \\
\hline
Lago et al. \cite{lago2021forecasting} & ENTSO-E (EU Markets) & DNN / LEAR Hybrid & Exogenous Load + Gen & Yes & None & No \\
\hline
Tschora et al. \cite{tschora2022electricity} & European Spot Grid & Deep CNN + Attention & Cross-Border Flows & Yes & Attention Weights Only & No \\
\hline
Lehna et al. \cite{lehna2022forecasting} & German Day-Ahead & LSTM-XGBoost Hybrid & Wind \& Solar Aggregated & Partial & Global Gain Only & No \\
\hline
Proposed (EnergyCast) & India IEX DAM (28,176h) & 3-Tier: Naive, Ridge, LightGBM & POSOCO Load, Solar, Wind + 5-Zone ERA5 & Strict 10:30 AM IST D-1 Gate & Exact TreeSHAP (Rs./MWh) & Yes (Energy-Neutral LP + 3.4ms Sim.) \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\subsection{Comparative Analysis of Existing Forecasting Systems}
Existing electricity price forecasting frameworks generally address isolated algorithmic accuracy rather than integrating multi-source physical grid telemetry, strict auction-gate causality, exact game-theoretic rupee attribution, counterfactual weather stress testing, and automated procurement bid optimization within a unified production architecture. Table~\ref{tab:related_work} compares representative systems from the literature with the proposed EnergyCast platform across target market scale, modeling hierarchy, physical renewable integration, causal boundary enforcement, explainability, and procurement optimization capabilities.

\section{Proposed Methodology}
The proposed EnergyCast system integrates multi-source telemetry harmonization, strict D-1 auction-gate causal feature synthesis, a three-tier econometric and gradient-boosted learning hierarchy, statutory CERC price projection, exact TreeSHAP attribution, counterfactual supply-stack stress testing, and constrained energy-neutral bid optimization. The implementation is engineered in Python~3.12 using LightGBM~4.6, XGBoost~3.0, Scikit-Learn~1.6, and NumPy~2.2. The complete 5-layer architectural workflow is illustrated in Fig.~\ref{fig:architecture}.

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_1_architecture.jpg}
\caption{Detailed 5-layer system architecture and operational dataflow of the proposed EnergyCast platform, illustrating multi-source telemetry acquisition, 10:30~AM IST D-1 causal gate enforcement, 53-signal domain synthesis, three-tier progressive learning with CERC statutory clipping, exact TreeSHAP attribution, counterfactual merit-order simulation, and energy-neutral DISCOM bid optimization.}
\label{fig:architecture}
\end{__FIG_WIDE_ENV__}

\subsection{Multi-Source Telemetry Harmonization and Spatial Weather Fusion}
Electricity price formation in the Indian national grid is governed by the simultaneous interaction of auction order-book liquidity, dispatchable thermal supply versus non-dispatchable renewable injection, and regional meteorological cooling demand. We construct a unified, gap-free hourly master panel spanning 3.25 years (April~1, 2022 to June~24, 2025; 28,344 raw hours, yielding 28,176 causal records after 168-hour initialization) by harmonizing three primary data streams onto a canonical Indian Standard Time ($\text{IST} = \text{UTC} + 05:30$) hourly index:
\begin{enumerate}
    \item IEX DAM Auction Telemetry: Raw 15-minute market clearing blocks ($\tau \in \{1, 2, 3, 4\}$ within each delivery hour $t$) containing Market Clearing Price ($MCP_{t,\tau}$ in Rs./MWh), Market Clearing Volume ($MCV_{t,\tau}$ in MW), Purchase Bid Volume ($B_{t,\tau}^{\text{buy}}$), and Sell Bid Volume ($B_{t,\tau}^{\text{sell}}$).
    \item Grid-India (POSOCO) National SCADA Telemetry: Hourly national gross power demand met ($D_t$ in MW), utility-scale solar generation ($S_t$ in MW), and wind generation ($W_t$ in MW).
    \item Multi-Zone ERA5 Meteorological Reanalysis: Hourly surface temperature ($T_{z,t}$ in $^\circ$C), apparent temperature ($AT_{z,t}$), relative humidity ($RH_{z,t}$ in \%), 100m hub-height wind speed ($WS_{z,t}$ in m/s), and precipitation ($PR_{z,t}$ in mm) across India's five regional load dispatch centers: Northern Region ($z=\text{NR}$, Delhi), Western Region ($z=\text{WR}$, Mumbai), Southern Region ($z=\text{SR}$, Bengaluru/Chennai), Eastern Region ($z=\text{ER}$, Kolkata), and North-Eastern Region ($z=\text{NER}$, Guwahati).
\end{enumerate}

To harmonize the 15-minute IEX auction blocks with the hourly national SCADA and meteorological streams without introducing aggregation bias, the hourly clearing price $P_t$ and clearing volume $V_t$ at delivery hour $t$ are computed via block-level arithmetic averaging:
\begin{equation}
\begin{aligned}
P_t &= \frac{1}{4}\sum_{\tau=1}^{4} MCP_{t,\tau}, \quad V_t = \frac{1}{4}\sum_{\tau=1}^{4} MCV_{t,\tau}, \\
B_t^{\text{buy}} &= \frac{1}{4}\sum_{\tau=1}^{4} B_{t,\tau}^{\text{buy}}, \quad B_t^{\text{sell}} = \frac{1}{4}\sum_{\tau=1}^{4} B_{t,\tau}^{\text{sell}}
\end{aligned}
\label{eq:block_agg}
\end{equation}
\noindent\textit{Eq.~1:} This equation aggregates the four 15-minute auction blocks ($\tau \in \{1,2,3,4\}$) within each delivery hour $t$ into a standardized hourly clearing price $P_t$ (in Rs./MWh) and hourly power flow equivalents $V_t$, $B_t^{\text{buy}}$, and $B_t^{\text{sell}}$ (in MWh/h or average MW). Averaging across the four 15-minute blocks preserves the exact financial settlement value of a 1-hour flat delivery contract while filtering sub-hourly auction micro-jitter.

To synthesize a single national meteorological vector from the five regional load dispatch zones ($z \in \mathcal{Z} = \{\text{NR}, \text{WR}, \text{SR}, \text{ER}, \text{NER}\}$), we apply convex consumption-weighted spatial aggregation along with extreme-value envelope extraction:
\begin{equation}
\begin{aligned}
\psi_t^{\text{mean}} &= \sum_{z \in \mathcal{Z}} \omega_z \, \psi_{z,t}, \quad \text{s.t.} \sum_{z \in \mathcal{Z}} \omega_z = 1, \\
\psi_t^{\text{max}} &= \max_{z \in \mathcal{Z}} \psi_{z,t}, \quad \psi_t^{\text{min}} = \min_{z \in \mathcal{Z}} \psi_{z,t}
\end{aligned}
\label{eq:spatial_weather}
\end{equation}
\noindent\textit{Eq.~2:} For each meteorological state variable $\psi \in \{T, AT, RH, WS, PR\}$, $\omega_z \ge 0$ represents the regional grid consumption share of zone $z$ ($\omega_{\text{WR}}=0.32$, $\omega_{\text{NR}}=0.30$, $\omega_{\text{SR}}=0.25$, $\omega_{\text{ER}}=0.11$, $\omega_{\text{NER}}=0.02$). While $\psi_t^{\text{mean}}$ captures the national load-weighted thermal state, the spatial envelope operators $\psi_t^{\text{max}}$ and $\psi_t^{\text{min}}$ preserve localized regional heatwaves (for example, Northern and Western afternoon peak temperatures exceeding $43^\circ$C) that trigger localized cooling surges even when the national mean temperature appears moderate.

\subsection{Strict 10:30 AM IST D-1 Auction Gate Causal Boundary}
A pervasive methodological flaw in academic electricity price forecasting is look-ahead data leakage, wherein models inadvertently access realized prices, auction bid volumes, or actual clearing volumes from earlier hours of the same delivery day $D$ that were not yet known when bids were submitted on day $D-1$. In the IEX Day-Ahead Market, market participants must submit their entire 24-hour bid portfolio for delivery day $D$ (covering hours $h \in \{0, 1, \dots, 23\}$) before the auction gate closes at 10:30~AM IST on day $D-1$. Consequently, for any target delivery timestamp $t = (D, h)$, the admissible causal information set $\mathcal{F}_{D-1, 10:30}$ is strictly bounded by:
\begin{equation}
\begin{aligned}
\mathcal{F}_{D-1, 10:30} = \Big\{ & P_{t-k}, V_{t-m}, B_{t-m}^{\text{buy}}, B_{t-m}^{\text{sell}}, \\
& D_{t-\ell}, S_{t-\ell}, W_{t-\ell}, \Psi_{t-\ell} \;\Big|\; m \ge 24 \Big\}
\end{aligned}
\label{eq:causal_gate}
\end{equation}
\noindent\textit{Eq.~3:} This causal conditioning equation restricts all auction-clearing volume and bid features ($V, B^{\text{buy}}, B^{\text{sell}}$) to a minimum lag of $m \ge 24$ hours ($m \in \{24, 48, 168\}$), ensuring that order-book depth for delivery day $D$ is derived exclusively from published prior-day auction sheets. Autoregressive price anchors ($k \in \{1, 2, 24, 48, 168\}$) and day-ahead physical and meteorological schedule vectors ($\ell \in \{0, 1, 24\}$) strictly exclude any contemporaneous target clearing price $P_t$ or realized post-gate order-book volume $V_t$.

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_2_duck_curve_regimes.jpg}
\caption{Empirical market regime dynamics across the 28,176-hour dataset: (a) Diurnal duck curve profile showing midday solar price suppression (10:00--15:00~IST) and evening net thermal ramp scarcity (18:00--22:00~IST); (b) Multi-year structural evolution of IEX DAM clearing prices from 2022 to 2025.}
\label{fig:duck_curve}
\end{__FIG_WIDE_ENV__}

\subsection{Mathematical Formulation of the 53 Causal Features}
Guided by power systems microeconomics and the empirical duck curve structure shown in Fig.~\ref{fig:duck_curve}(a), we engineer 53 leak-free features partitioned into five orthogonal domain categories.

\subsubsection{1) Physical Grid Load and Renewable Penetration Dynamics (15 Features):}
Thermal coal and gas generators do not respond to gross national demand $D_t$ directly; instead, they must serve the residual load remaining after must-run, zero-marginal-cost solar ($S_t$) and wind ($W_t$) generation are absorbed by the grid. We define System Net Thermal Demand ($ND_t$) as:
\begin{equation}
ND_t = D_t - \left(S_t + W_t\right)
\label{eq:net_demand}
\end{equation}
\noindent\textit{Eq.~4:} Expressed in megawatts (MW), $ND_t$ measures the exact dispatchable demand that must be met by thermal, hydro, and gas generators. During midday solar peaks, $S_t$ exceeds 35,000~MW nationally, carving a deep trough in $ND_t$ and pushing the grid down onto flat, low-cost pit-head coal units.

However, thermal coal boilers face severe thermodynamic ramp-rate limits (typically 1--2\% of rated capacity per minute). When solar output drops rapidly toward sunset while industrial and residential lighting loads surge, the rate of change of net demand forces the system operator to dispatch fast-ramping, high-cost gas and liquid peakers. We capture this dynamic via the 1-hour Net Demand Ramp Velocity ($\Delta ND_t^{(1)}$):
\begin{equation}
\begin{aligned}
\Delta ND_t^{(1)} &= ND_t - ND_{t-1} \\
&= (D_t - D_{t-1}) - (S_t - S_{t-1}) - (W_t - W_{t-1})
\end{aligned}
\label{eq:net_demand_ramp}
\end{equation}
\noindent\textit{Eq.~5:} Measured in MW/h, a large positive value of $\Delta ND_t^{(1)}$ (for instance, $+13,467$~MW/h at 18:00~IST on January~1, 2025) signals that solar generation is collapsing simultaneously with rising evening demand. As verified in Section~4, $\Delta ND_t^{(1)}$ is the single most influential physical grid driver of clearing prices (mean absolute SHAP contribution of Rs.~321.07/MWh).

To normalize renewable supply relative to seasonal grid size, we compute the Renewable Energy Penetration Percentage ($REP_t$):
\begin{equation}
REP_t = \left( \frac{S_t + W_t}{\max(D_t, \epsilon)} \right) \times 100, \quad \epsilon = 1.0\text{ MW}
\label{eq:re_penetration}
\end{equation}
\noindent\textit{Eq.~6:} This dimensionless ratio quantifies the percentage of national load displaced by renewables. When $REP_t > 22\%$, renewable supply shifts the aggregate supply curve rightward, compressing clearing prices across the midday solar window ($t \in [09:00, 16:00]$). We additionally include 1-hour and 24-hour lags of gross demand, net demand, solar generation, and wind generation ($D_{t-1}$, $D_{t-24}$, $ND_{t-1}$, $ND_{t-24}$, $S_{t-24}$, $W_{t-24}$).

\subsubsection{2) Multi-Horizon Autoregressive Price Memory and Volatility (15 Features):}
Because power plant unit-commitment schedules, coal stock inventories, and bilateral contract positions persist across consecutive hours, days, and weeks, spot electricity prices exhibit strong multi-scale autocorrelation. In addition to raw historical lags ($P_{t-1}$, $P_{t-2}$, $P_{t-24}$, $P_{t-48}$, $P_{t-168}$), we formulate first- and second-order price momentum operators:
\begin{equation}
\begin{aligned}
\Delta P_t^{(1,2)} &= P_{t-1} - P_{t-2}, \\
\Delta P_t^{(24,25)} &= P_{t-1} - P_{t-25}, \\
\rho_t^{(1,24)} &= \frac{P_{t-1}}{\max(P_{t-24}, \epsilon)}
\end{aligned}
\label{eq:price_momentum}
\end{equation}
\noindent\textit{Eq.~7:} Here, $\Delta P_t^{(1,2)}$ measures immediate 1-hour price acceleration prior to hour $t$, $\Delta P_t^{(24,25)}$ captures the 24-hour diurnal price velocity (comparing the most recent hour $t-1$ against the corresponding hour $t-25$ from yesterday), and $\rho_t^{(1,24)}$ is the dimensionless regime-inflation ratio indicating whether today's price trajectory is running higher ($\rho_t^{(1,24)} > 1$) or lower ($\rho_t^{(1,24)} < 1$) than yesterday's baseline.

To quantify rolling market turbulence and detect anomalous price breakouts, we compute 24-hour and 168-hour rolling means ($\mu_t^{(24)}$, $\mu_t^{(168)}$), rolling standard deviations ($\sigma_t^{(24)}$, $\sigma_t^{(168)}$), 24-hour rolling extrema ($P_t^{\min,24}$, $P_t^{\max,24}$), and the standardized 24-hour Price Volatility Z-Score ($Z_t^{(24)}$):
\begin{equation}
\begin{aligned}
\mu_t^{(K)} &= \frac{1}{K}\sum_{i=1}^{K} P_{t-i}, \quad \sigma_t^{(K)} = \sqrt{\frac{1}{K}\sum_{i=1}^{K}\left(P_{t-i} - \mu_t^{(K)}\right)^2}, \\
Z_t^{(24)} &= \frac{P_{t-1} - \mu_t^{(24)}}{\sigma_t^{(24)} + \epsilon}
\end{aligned}
\label{eq:price_zscore}
\end{equation}
\noindent\textit{Eq.~8:} By normalizing the deviation of $P_{t-1}$ from its 24-hour rolling mean $\mu_t^{(24)}$ by the local 24-hour volatility $\sigma_t^{(24)}$ (with $\epsilon = 10^{-4}$ preventing division by zero during prolonged Rs.~10,000/MWh price-cap plateaus), $Z_t^{(24)}$ acts as a regime-invariant breakout oscillator that distinguishes normal diurnal rises from acute scarcity shocks.

\subsubsection{3) IEX Auction Order-Book Liquidity and Market Tightness (4 Features):}
In a uniform-price double auction, clearing price sensitivity depends heavily on the ratio of buyer demand bids to seller supply offers. Using strictly causal 24-hour lagged order-book volumes ($B_{t-24}^{\text{buy}}$, $B_{t-24}^{\text{sell}}$, $V_{t-24}$), we define the Auction Market Tightness Ratio ($\tau_{t-24}$):
\begin{equation}
\tau_{t-24} = \frac{B_{t-24}^{\text{buy}}}{\max\left(B_{t-24}^{\text{sell}}, \, \epsilon\right)}
\label{eq:market_tightness}
\end{equation}
\noindent\textit{Eq.~9:} When $\tau_{t-24} < 1.0$, aggregate seller supply offers exceed buyer purchase bids, indicating a buyer's market with ample generation surplus (for example, $\tau_{t-24} = 0.47$ during midday solar hours). Conversely, when $\tau_{t-24} > 1.5$ (reaching $2.90\times$ during evening scarcity blocks), aggressive price-inelastic DISCOM buying overwhelms seller liquidity, driving the auction clearing intersection onto the vertical Rs.~10,000/MWh price cap.

\subsubsection{4) Cyclical Calendar and Diurnal Harmonics (8 Features):}
Representing hour of day ($h \in \{0,\dots,23\}$), day of week ($d_w \in \{0,\dots,6\}$), and month of year ($m \in \{1,\dots,12\}$) as raw integers introduces an artificial geometric discontinuity at cycle boundaries (treating 23:00~IST and 00:00~IST as 23 units apart rather than 1 hour apart). We project each calendar index $c \in \{h, d_w, m\}$ with period $T_c \in \{24, 7, 12\}$ onto the 2D unit circle via orthogonal Fourier harmonics:
\begin{equation}
c_{\sin} = \sin\left(\frac{2\pi \, c}{T_c}\right), \quad c_{\cos} = \cos\left(\frac{2\pi \, c}{T_c}\right)
\label{eq:fourier_cycles}
\end{equation}
\noindent\textit{Eq.~10:} This bivariate trigonometric embedding guarantees smooth Euclidean continuity across midnight, weekend transitions, and year-end boundaries, enabling both linear Ridge regression and decision-tree splitters to isolate arbitrary phase-shifted diurnal and seasonal regimes alongside binary indicators for weekend ($I_{\text{wknd}}$) and evening peak hours ($I_{\text{peak}}(t) = 1$ for $t \in [18:00, 22:00]$).

\subsubsection{5) Non-Linear Meteorological Cooling Stress and Physical Interactions (11 Features):}
Ambient temperature affects electricity demand non-linearly: below a comfort threshold of $24^\circ\text{C}$, temperature rises have minimal impact on grid load, whereas above $24^\circ\text{C}$, residential and commercial air-conditioning (AC) compressor loads scale super-linearly. We formulate Cooling Degree Days ($CDD_{24,t}$), quadratic thermal stress ($T_{\text{sq},t}$), and cross-domain physical interaction terms:
\begin{equation}
CDD_{24,t} = \max\left(0, \; T_t^{\text{mean}} - 24.0^\circ\text{C}\right), \quad T_{\text{sq},t} = \left(T_t^{\text{mean}}\right)^2
\label{eq:cdd}
\end{equation}
\noindent\textit{Eq.~11:} The hinge function $\max(0, T_t^{\text{mean}} - 24.0)$ zeroes out non-cooling temperatures while linearly tracking heat accumulation above $24^\circ\text{C}$, and $T_{\text{sq},t}$ captures convex resistive transmission losses and AC compressor efficiency degradation under extreme heat.

Finally, because a $+5^\circ\text{C}$ heat anomaly or a high net demand level produces a much larger price spike when it coincides with the evening thermal peak than at 03:00~AM, we construct two explicit multiplicative interaction features:
\begin{equation}
I_t^{\text{peak}} = ND_t \cdot I_{\text{peak}}(t), \quad I_t^{\text{cool}} = ND_t \cdot CDD_{24,t}
\label{eq:interactions}
\end{equation}
\noindent\textit{Eq.~12:} Here, $I_t^{\text{peak}}$ isolates the megawatt stress exerted specifically during evening peak hours (18:00--22:00~IST), while $I_t^{\text{cool}}$ captures the compound grid stress when high industrial net demand coincides with severe summer cooling load. The complete 53-feature taxonomy is cataloged in Table~\ref{tab:feature_taxonomy}, and the causal synthesis procedure is formalized in Algorithm~\ref{alg:feature_engine}.

\begin{__TBL_ENV__}[!t]
\centering
\caption{Complete Taxonomy of the 53 Leak-Free Causal Features Engineered Across Five Physical and Econometric Domains}
\label{tab:feature_taxonomy}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|p{3.4cm}|c|p{7.6cm}|p{5.2cm}|}
\hline
Domain Category & Count & Engineered Feature Identifiers & Primary Physical / Market Mechanism \\
\hline
1. Price History \& Momentum & 15 & \texttt{mcp\_lag\_1}, \texttt{mcp\_lag\_2}, \texttt{mcp\_lag\_24}, \texttt{mcp\_lag\_48}, \texttt{mcp\_lag\_168}, \texttt{mcp\_diff\_1\_2}, \texttt{mcp\_diff\_24\_25}, \texttt{mcp\_ratio\_1\_24}, \texttt{mcp\_rolling\_mean\_24}, \texttt{mcp\_rolling\_std\_24}, \texttt{mcp\_rolling\_min\_24}, \texttt{mcp\_rolling\_max\_24}, \texttt{mcp\_zscore\_24}, \texttt{mcp\_rolling\_mean\_168}, \texttt{mcp\_rolling\_std\_168} & Captures multi-horizon unit-commitment persistence, diurnal velocity, and regime breakout volatility. \\
\hline
2. Physical Grid \& Renewables & 15 & \texttt{demand\_mw}, \texttt{demand\_lag\_1}, \texttt{demand\_lag\_24}, \texttt{solar\_generation\_mw}, \texttt{solar\_lag\_24}, \texttt{wind\_generation\_mw}, \texttt{wind\_lag\_24}, \texttt{net\_demand\_mw}, \texttt{net\_demand\_lag\_1}, \texttt{net\_demand\_lag\_24}, \texttt{net\_demand\_ramp\_1}, \texttt{re\_penetration\_pct}, \texttt{is\_solar\_hour}, \texttt{net\_demand\_x\_peak}, \texttt{net\_demand\_x\_cdd} & Isolates residual thermal load, midday solar merit-order suppression, and evening duck curve neck ramp rates. \\
\hline
3. Market Bidding Signals & 4 & \texttt{purchase\_bid\_lag\_24}, \texttt{sell\_bid\_lag\_24}, \texttt{mcv\_lag\_24}, \texttt{market\_tightness\_lag\_24} & Quantifies D-1 auction order-book elasticity and buyer-to-seller bid imbalance ($\tau_{t-24}$). \\
\hline
4. Calendar \& Diurnal Cycles & 8 & \texttt{hour\_sin}, \texttt{hour\_cos}, \texttt{day\_of\_week\_sin}, \texttt{day\_of\_week\_cos}, \texttt{month\_sin}, \texttt{month\_cos}, \texttt{is\_weekend}, \texttt{is\_peak\_hour} & Encodes continuous circular phase harmonics for diurnal, weekly industrial, and seasonal monsoon cycles. \\
\hline
5. Weather \& Climate Stress & 11 & \texttt{temperature\_mean\_c}, \texttt{temperature\_max\_c}, \texttt{temperature\_min\_c}, \texttt{temperature\_lag\_24}, \texttt{temperature\_sq}, \texttt{apparent\_temperature\_mean\_c}, \texttt{cdd\_24}, \texttt{humidity\_mean\_pct}, \texttt{weather\_wind\_speed\_mean\_ms}, \texttt{precipitation\_mean\_mm}, \texttt{precipitation\_max\_mm} & Models non-linear AC cooling demand above $24^\circ\text{C}$, humidity heat-index stress, and monsoon convective relief. \\
\hline
Total Causal Signals & 53 & Zero Forward Data Leakage ($\mathcal{F}_{D-1, 10:30}$ Verified) & Full Spatio-Temporal Coverage (28,176 Hours) \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\begin{__ALG_ENV__}[!t]
\caption{Causal Multi-Source Telemetry Harmonization and 53-Feature Synthesis}
\label{alg:feature_engine}
\footnotesize
\begin{algorithmic}[1]
\State Input: Raw 15-min IEX blocks $\mathcal{I}_{15m}$, hourly POSOCO grid stream $\mathcal{G}_{1h}$, 5-zone ERA5 weather $\mathcal{W}_{5z,1h}$
\State Output: Leak-free causal feature matrix $X \in \mathbb{R}^{28176 \times 53}$ and target vector $y \in \mathbb{R}^{28176}$
\For{each delivery hour $t \in \{1, \dots, T_{\text{raw}}\}$ on canonical IST grid}
    \State Compute hourly block averages $P_t, V_t, B_t^{\text{buy}}, B_t^{\text{sell}}$ via Eq.~1
    \State Fuse 5-zone regional weather $\Psi_t^{\text{mean}}, \Psi_t^{\text{max}}, \Psi_t^{\text{min}}$ using weights $\omega_z$ via Eq.~2
    \State Compute Net Thermal Demand $ND_t \gets D_t - (S_t + W_t)$ and 1h ramp $\Delta ND_t^{(1)}$ via Eq.~4--5
    \State Compute Renewable Penetration $REP_t \gets 100 \cdot (S_t + W_t) / \max(D_t, 1.0)$ via Eq.~6
    \State Extract causal lags $\{P_{t-1}, P_{t-2}, P_{t-24}, P_{t-48}, P_{t-168}\}$ and velocities $\Delta P_t^{(1,2)}, \Delta P_t^{(24,25)}$ via Eq.~7
    \State Compute rolling moments $\mu_t^{(24)}, \sigma_t^{(24)}, \mu_t^{(168)}, \sigma_t^{(168)}$ and $Z_t^{(24)}$ over $[t-K, t-1]$ via Eq.~8
    \State Compute lagged D-1 auction order-book tightness $\tau_{t-24} \gets B_{t-24}^{\text{buy}} / \max(B_{t-24}^{\text{sell}}, 1.0)$ via Eq.~9
    \State Project $(h_t, d_{w,t}, m_t)$ onto $(\sin, \cos)$ harmonics and compute $CDD_{24,t}, I_t^{\text{peak}}, I_t^{\text{cool}}$ via Eq.~10--12
\EndFor
\State Discard initial 168 warm-up hours ($t \le 168$) required for 7-day rolling memory initialization
\State Partition $(X, y)$ chronologically: Train ($2022\text{--}2023$), Validation ($2024$), Test ($2025$)
\State \Return $(X_{\text{train}}, y_{\text{train}}), (X_{\text{val}}, y_{\text{val}}), (X_{\text{test}}, y_{\text{test}})$
\end{algorithmic}
\end{__ALG_ENV__}

\subsection{Three-Tier Progressive Modeling Hierarchy and Regulatory Projection}
Rather than deploying a complex model in isolation, we construct a disciplined three-tier modeling hierarchy where each successive tier must demonstrate statistically significant error reduction over its predecessor on identical chronological splits.

\subsubsection{Tier 1: Domain-Specific Market Persistence Baselines:}
We establish three zero-parameter domain benchmarks reflecting standard utility trading heuristics: (i) Daily Seasonal Naive (24h) ($\hat{y}_t^{\text{SNaive24}} = P_{t-24}$), which assumes today's clearing price at hour $h$ equals yesterday's clearing price at the same hour $h$; (ii) Weekly Seasonal Naive (168h) ($\hat{y}_t^{\text{SNaive168}} = P_{t-168}$), which matches the same hour and day of the previous week; and (iii) 1-Hour Persistence ($\hat{y}_t^{\text{Persist1}} = P_{t-1}$).

\subsubsection{Tier 2: Linear Econometric Benchmark and Tikhonov $L_2$ Ridge Regularization:}
Before fitting linear models, all 53 features are z-score standardized using training-set moments ($\tilde{x}_{t,j} = (x_{t,j} - \bar{x}_{j,\text{train}}) / s_{j,\text{train}}$) so that regularized shrinkage applies equitably across megawatt, Celsius, and rupee scales. Because the 53-feature matrix contains structurally collinear signals (such as $D_t = ND_t + S_t + W_t$ and $T_{\text{sq},t}$ versus $T_t^{\text{mean}}$, yielding Variance Inflation Factors $\text{VIF} > 40$), unregularized Ordinary Least Squares (OLS) suffers from severe coefficient instability. We resolve this via Tikhonov $L_2$-regularized Ridge regression:
\begin{equation}
\begin{aligned}
\hat{\beta}_{\text{Ridge}}(\alpha) &= \arg\min_{\beta \in \mathbb{R}^{53}} \left\{ \|y_{\text{train}} - \tilde{X}_{\text{train}}\beta\|_2^2 + \alpha \|\beta\|_2^2 \right\} \\
&= \left( \tilde{X}_{\text{train}}^\top \tilde{X}_{\text{train}} + \alpha I_{53} \right)^{-1} \tilde{X}_{\text{train}}^\top y_{\text{train}}
\end{aligned}
\label{eq:ridge}
\end{equation}
\noindent\textit{Eq.~13:} Adding the positive ridge penalty $\alpha I_{53}$ shifts all eigenvalues of the Gram matrix $\tilde{X}^\top\tilde{X}$ from $\lambda_j$ to $\lambda_j + \alpha > 0$, bounding the matrix condition number and shrinking collinear coefficient pairs toward stable physical weights. Grid search over $\alpha \in \{0.01, 0.1, 1, 10, 50, 100, 500, 1000\}$ on the 2024 validation split identifies $\alpha^* = 50$ as optimal.

\subsubsection{Tier 3: Histogram-Based Gradient-Boosted Decision Trees (LightGBM \& XGBoost):}
To capture non-linear supply-stack thresholds and higher-order feature interactions without manual specification, Tier~3 deploys two gradient-boosted decision tree (GBDT) ensembles: XGBoost \cite{chen2016xgboost} (depth-wise growth) and LightGBM \cite{ke2017lightgbm} (leaf-wise best-first growth with 255-bin feature histograms). At boosting iteration $m \in \{1, \dots, M\}$, given first- and second-order loss gradients $g_t = \hat{y}_t^{(m-1)} - y_t$ and $h_t = 1$, the second-order Taylor-expanded objective $\mathcal{L}^{(m)}$ and optimal leaf weight $w_q^*$ for leaf region $I_q$ are given by:
\begin{equation}
\begin{aligned}
\mathcal{L}^{(m)} &\approx \sum_{q=1}^{J} \left[ G_q w_q + \frac{1}{2}(H_q + \lambda) w_q^2 \right] + \gamma J, \\
w_q^* &= -\frac{G_q}{H_q + \lambda}, \quad G_q = \sum_{t \in I_q} g_t, \;\; H_q = \sum_{t \in I_q} h_t
\end{aligned}
\label{eq:gbdt_leaf}
\end{equation}
\noindent\textit{Eq.~14:} Here, $J$ is the number of leaves per tree ($J=63$ in our tuned LightGBM configuration), $\lambda = 2.0$ is the $L_2$ leaf-weight regularization parameter that prevents overfitting to isolated scarcity spikes, and $\gamma$ is the minimum split-gain complexity penalty.

When evaluating candidate split thresholds across the 255 discretized histogram bins of feature $j$, LightGBM selects the leaf and threshold that maximize the regularized variance-reduction Split Gain ($\mathcal{G}_{\text{split}}$):
\begin{equation}
\mathcal{G}_{\text{split}}(I_L, I_R) = \frac{1}{2} \left[ \frac{G_L^2}{H_L + \lambda} + \frac{G_R^2}{H_R + \lambda} - \frac{(G_L + G_R)^2}{H_L + H_R + \lambda} \right] - \gamma
\label{eq:split_gain}
\end{equation}
\noindent\textit{Eq.~15:} By splitting the leaf with the highest global $\mathcal{G}_{\text{split}}$ across the entire tree (leaf-wise growth) rather than splitting all leaves at depth $d$ uniformly, LightGBM allocates deeper resolution specifically to the steep evening scarcity regime ($ND_t > 160$~GW) while keeping flat midday solar branches shallow. Early stopping on the 8,784-hour 2024 validation set (with learning rate $\eta = 0.03$, subsample $= 0.8$, colsample $= 0.8$) converges at $M^* = 282$ trees for LightGBM and $M^* = 268$ trees for XGBoost.

\subsubsection{Statutory CERC Price-Cap Projection Operator:}
In the IEX Day-Ahead Market, the Central Electricity Regulatory Commission (CERC) enforces a hard statutory floor of Rs.~0/MWh and a ceiling cap of Rs.~10,000/MWh \cite{cerc2023order}. Because unconstrained regression models can extrapolate above Rs.~10,000/MWh during extreme net-load ramps or below Rs.~0/MWh during extreme midday solar gluts, all raw model predictions $f(x_t)$ are passed through the non-expansive CERC projection operator:
\begin{equation}
\hat{y}_t = \Pi_{\text{CERC}}\big(f(x_t)\big) = \min\Big(10000.0, \; \max\big(0.0, \; f(x_t)\big)\Big)
\label{eq:cerc_clip}
\end{equation}
\noindent\textit{Eq.~16:} By the theorem of convex projection onto closed intervals, since the true target $y_t \in [0, 10000]$ for all post-April 2023 operating hours, $\Pi_{\text{CERC}}$ strictly reduces or preserves pointwise absolute and squared error while guaranteeing 100\% regulatory compliance.

\subsection{Exact Game-Theoretic TreeSHAP Attribution}
To eliminate the black-box barrier for utility trading desks, we integrate the exact TreeSHAP algorithm \cite{lundberg2020local} directly into the LightGBM inference pipeline. For any hourly feature vector $x_t \in \mathbb{R}^{53}$, the exact Shapley value $\phi_j(x_t)$ of feature $j \in \mathcal{F}$ ($\mathcal{F} = \{1,\dots,53\}$) is defined over all coalition subsets $S \subseteq \mathcal{F} \setminus \{j\}$ and satisfies the exact additive efficiency identity:
\begin{equation}
\begin{aligned}
\phi_j(x_t) &= \sum_{S \subseteq \mathcal{F}\setminus\{j\}} \frac{|S|!(|\mathcal{F}| - |S| - 1)!}{|\mathcal{F}|!} \Big[ f_x(S \cup \{j\}) - f_x(S) \Big], \\
f(x_t) &= \mathbb{E}[f(X)] + \sum_{j=1}^{53} \phi_j(x_t)
\end{aligned}
\label{eq:treeshap}
\end{equation}
\noindent\textit{Eq.~17:} Here, $\mathbb{E}[f(X)] = \text{Rs.~3,873.06/MWh}$ is the expected unconditional base clearing price across the training distribution, and each $\phi_j(x_t)$ is expressed in exact Rs./MWh. Unlike permutation importance or global split-gain heuristics, Eq.~\ref{eq:treeshap} guarantees that for every single hour $t$, the sum of the 53 feature attributions plus the base value equals the exact unclipped LightGBM prediction to machine precision ($0.00$~Rs./MWh reconstruction error).

\subsection{Econometric Verification Metrics and Newey-West HAC Diebold-Mariano Test}
We evaluate all models across the 4,200 unseen test hours of 2025 using four complementary accuracy metrics---Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Symmetric Mean Absolute Percentage Error (sMAPE), and the Coefficient of Determination ($R^2$):
\begin{equation}
\begin{aligned}
\text{MAE} &= \frac{1}{N}\sum_{t=1}^{N} |y_t - \hat{y}_t|, \quad \text{RMSE} = \sqrt{\frac{1}{N}\sum_{t=1}^{N} (y_t - \hat{y}_t)^2}, \\
\text{sMAPE} &= \frac{200\%}{N}\sum_{t=1}^{N}\frac{|y_t - \hat{y}_t|}{|y_t| + |\hat{y}_t| + \epsilon}, \quad R^2 = 1 - \frac{\sum_{t=1}^{N}(y_t - \hat{y}_t)^2}{\sum_{t=1}^{N}(y_t - \bar{y})^2}
\end{aligned}
\label{eq:metrics}
\end{equation}
\noindent\textit{Eq.~18:} MAE measures the direct financial procurement error in Rs./MWh per unit of flat volume, RMSE penalizes large tail errors during Rs.~10,000/MWh evening scarcity spikes, sMAPE provides a scale-free percentage error bounded in $[0\%, 200\%]$ that remains stable near low midday prices, and $R^2$ quantifies the proportion of total price variance explained out-of-sample.

Because hourly electricity forecast errors $e_{i,t} = y_t - \hat{y}_{i,t}$ exhibit strong diurnal serial correlation and conditional heteroskedasticity, standard paired $t$-tests underestimate residual variance and inflate Type-I error rates. We therefore apply the Diebold-Mariano (DM) test \cite{diebold1995comparing} equipped with the Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC) variance estimator \cite{newey1987simple}. Given competing models $M_1$ and $M_2$, let $d_t = |e_{1,t}| - |e_{2,t}|$ denote the absolute loss differential at hour $t$, with sample mean $\bar{d} = \frac{1}{N}\sum_{t=1}^{N} d_t$. The Newey-West HAC variance $\hat{V}_{\text{HAC}}(\bar{d})$ with Bartlett kernel bandwidth $L = \lfloor 4(N/100)^{2/9} \rfloor = 9$ is computed from sample autocovariances $\hat{\gamma}_k$:
\begin{equation}
\begin{aligned}
\hat{\gamma}_k &= \frac{1}{N}\sum_{t=k+1}^{N} (d_t - \bar{d})(d_{t-k} - \bar{d}), \\
\hat{V}_{\text{HAC}}(\bar{d}) &= \hat{\gamma}_0 + 2\sum_{k=1}^{L}\left(1 - \frac{k}{L+1}\right)\hat{\gamma}_k
\end{aligned}
\label{eq:hac_var}
\end{equation}
\noindent\textit{Eq.~19:} The Bartlett weights $(1 - k/(L+1))$ downweight higher-order autocovariances up to lag $L=9$ hours, guaranteeing that $\hat{V}_{\text{HAC}}(\bar{d})$ is strictly positive semi-definite in finite samples while correcting for serial error correlation across consecutive auction blocks.

The resulting asymptotic Diebold-Mariano test statistic ($DM$) under the null hypothesis of equal predictive accuracy ($H_0: \mathbb{E}[d_t] = 0$) is:
\begin{equation}
DM = \frac{\bar{d}}{\sqrt{\hat{V}_{\text{HAC}}(\bar{d}) \, / \, N}} \;\xrightarrow{d}\; \mathcal{N}(0, 1)
\label{eq:dm_stat}
\end{equation}
\noindent\textit{Eq.~20:} A positive statistic $DM > +1.96$ ($p < 0.05$) or $DM > +2.58$ ($p < 0.01$) proves that Model~1 incurs a statistically higher loss than Model~2, confirming the superiority of Model~2 after accounting for autocorrelation.

\subsection{Energy-Neutral DISCOM Bid Optimization and Counterfactual Simulation}
To translate hourly forecasts into direct financial savings for a DISCOM or industrial open-access plant, we formulate an energy-neutral daily load-shifting optimization problem. Consider a buyer with baseline hourly demand $L_h^0$ (in MW) across hours $h \in \{0,\dots,23\}$, a flexible shiftable load fraction $\gamma \in [0, 0.5]$ (for example, $\gamma = 0.30$ for industrial pumping, cold storage, electric arc furnaces, or agricultural feeder scheduling), and a maximum bid price cap $P_{\max}$. Given the 24-hour LightGBM forecast vector $\hat{y}_d = (\hat{y}_{d,0}, \dots, \hat{y}_{d,23})$, we solve for the optimal hourly bid schedule $L^* = (L_0^*, \dots, L_{23}^*)$:
\begin{equation}
\begin{aligned}
\min_{L_0^*, \dots, L_{23}^*} \quad & \sum_{h=0}^{23} L_h^* \cdot \hat{y}_{d,h} \\
\text{s.t.} \quad & \sum_{h=0}^{23} L_h^* = \sum_{h=0}^{23} L_h^0, \\
& (1 - \gamma)L_h^0 \le L_h^* \le (1 + \gamma)L_h^0 \quad \forall h \in \{0,\dots,23\}
\end{aligned}
\label{eq:bid_opt}
\end{equation}
\noindent\textit{Eq.~21:} The equality constraint $\sum_{h=0}^{23} L_h^* = \sum_{h=0}^{23} L_h^0$ enforces 100\% daily energy neutrality (the plant consumes the exact same daily megawatt-hours, such as $2,400$~MWh/day for a 100~MW baseline load), while the box constraints restrict hourly ramping within $\pm\gamma L_h^0$. By sorting the 24 delivery hours by predicted price, the exact global optimum shifts $+\gamma L_h^0$ into the cheapest midday solar trough hours and shaves $-\gamma L_h^0$ from the most expensive evening scarcity hours.

Finally, to stress-test procurement bids against unexpected weather or grid shocks prior to the 10:30~AM IST gate, we define the coupled physical perturbation operator $\mathcal{T}$ for any exogenous shock vector $\Delta = (\Delta D, \Delta S, \Delta W, \Delta R, \Delta T, \tau')$:
\begin{equation}
\begin{aligned}
ND_t' &= (D_t + \Delta D) - (S_t + \Delta S) - (W_t + \Delta W), \\
\Delta ND_t^{(1)\prime} &= \Delta ND_t^{(1)} + (ND_t' - ND_t) + \Delta R, \\
CDD_{24,t}' &= \max(0, \; T_t^{\text{mean}} + \Delta T - 24.0), \\
I_t^{\text{cool}\prime} &= ND_t' \cdot CDD_{24,t}'
\end{aligned}
\label{eq:counterfactual}
\end{equation}
\noindent\textit{Eq.~22:} Rather than perturbing a single column in isolation (which violates physical conservation laws), Eq.~\ref{eq:counterfactual} propagates any solar dropout ($\Delta S < 0$) or demand surge ($\Delta D > 0$) consistently through net thermal demand $ND_t'$, renewable penetration $REP_t'$, 1-hour ramp velocity $\Delta ND_t^{(1)\prime}$, cooling degree days $CDD_{24,t}'$, and multiplicative interaction terms before re-scoring $\Pi_{\text{CERC}}(f(x_t'))$ and recomputing exact TreeSHAP attributions $\phi_j(x_t')$ in real time ($\sim 3.4$~ms). The complete optimization and stress-testing workflow is detailed in Algorithm~\ref{alg:optimizer}.

\begin{__ALG_ENV__}[!t]
\caption{Energy-Neutral DISCOM Bid Optimization and Counterfactual Stress Testing}
\label{alg:optimizer}
\footnotesize
\begin{algorithmic}[1]
\State Input: Delivery date $d$, baseline load $L^0$ (MW), flex fraction $\gamma$, price cap $P_{\max}$, shock vector $\Delta$
\State Output: Optimal 24h schedule $L^*$, daily savings $\Delta C_d$, stressed price $\hat{y}_t'$, shifted SHAP drivers $\Delta\phi_t$
\For{each delivery hour $h \in \{0, \dots, 23\}$ of date $d$}
    \State Retrieve causal feature vector $x_{d,h} \in \mathcal{F}_{d-1, 10:30}$
    \State Compute CERC-projected forecast $\hat{y}_{d,h} \gets \min(10000, \max(0, f_{\text{LightGBM}}(x_{d,h})))$ via Eq.~16
    \State Compute exact TreeSHAP vector $\phi_{d,h} \in \mathbb{R}^{53}$ via \texttt{pred\_contrib=True} (Eq.~17)
\EndFor
\State Sort delivery hours by predicted price: $\pi \gets \text{argsort}(\hat{y}_{d,0}, \dots, \hat{y}_{d,23})$
\State Define solar boost window $\mathcal{H}_{\text{solar}} \gets \{\pi_1, \dots, \pi_6\}$ and peak shave window $\mathcal{H}_{\text{peak}} \gets \{\pi_{19}, \dots, \pi_{24}\}$
\For{$h \in \{0, \dots, 23\}$}
    \If{$h \in \mathcal{H}_{\text{solar}}$} $L_h^* \gets (1 + \gamma)L^0$
    \ElsIf{$h \in \mathcal{H}_{\text{peak}}$} $L_h^* \gets (1 - \gamma)L^0$
    \Else $\; L_h^* \gets L^0$
    \EndIf
    \State Set limit bid price $P_{d,h}^{\text{bid}} \gets \min(P_{\max}, \, \hat{y}_{d,h} + 1.645 \, \hat{\sigma}_h)$
\EndFor
\State Compute energy-neutral daily savings $\Delta C_d \gets \sum_{h=0}^{23} (L^0 - L_h^*) \hat{y}_{d,h}$ via Eq.~21
\If{counterfactual shock $\Delta \neq 0$ is requested for focus hour $t=(d,h)$}
    \State Construct physically coupled perturbed state $x_t' \gets \mathcal{T}(x_t, \Delta)$ via Eq.~22
    \State Re-score $\hat{y}_t' \gets \Pi_{\text{CERC}}(f_{\text{LightGBM}}(x_t'))$ and $\Delta\phi_t \gets \text{TreeSHAP}(x_t') - \phi_t$
\EndIf
\State \Return $L^*, \Delta C_d, \hat{y}_t', \Delta\phi_t$, and formatted 24-block IEX DAM CSV bid sheet
\end{algorithmic}
\end{__ALG_ENV__}

\section{Experimental Results}
The proposed EnergyCast system was evaluated through rigorous chronological experiments covering dataset regime characterization, collinearity shrinkage analysis, multi-tier out-of-sample forecasting accuracy, Newey-West HAC statistical hypothesis testing, exact TreeSHAP attribution, counterfactual weather stress testing, and DISCOM procurement ROI.

\begin{__TBL_ENV__}[!t]
\centering
\caption{Chronological Dataset Partitioning and Structural Regime Characteristics (2022--2025, $N = 28,176$ Causal Hours)}
\label{tab:split_summary}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|l|r|l|r|r|r|r|r|r|}
\hline
Chronological Split & Hours ($N$) & Time Span (IST) & Mean MCP & Median MCP & Std. Dev. & Cap Hits ($\ge$10k) & Mean Net Load & Mean RE \% \\
\hline
Training Set (53.9\%) & 15,192 & 2022-04-08 to 2023-12-31 & Rs. 5,669.32 & Rs. 4,477.26 & Rs. 2,974.76 & 2,738 (18.02\%) & 158,439.7 MW & 10.63\% \\
\hline
Validation Set (31.2\%) & 8,784 & 2024-01-01 to 2024-12-31 & Rs. 4,585.00 & Rs. 3,606.39 & Rs. 2,597.13 & 1,148 (13.07\%) & 169,349.6 MW & 11.39\% \\
\hline
Unseen Test Set (14.9\%) & 4,200 & 2025-01-01 to 2025-06-24 & Rs. 4,450.87 & Rs. 3,471.42 & Rs. 2,691.11 & 488 (11.62\%) & 169,790.8 MW & 13.91\% \\
\hline
Total / Master Panel & 28,176 & 38.5 Months (Zero Gaps) & Rs. 5,149.81 & Rs. 3,991.50 & Rs. 2,882.40 & 4,374 (15.52\%) & 163,532.4 MW & 11.36\% \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\subsection{Dataset Partitioning and Structural Regime Shift Analysis}
As summarized in Table~\ref{tab:split_summary} and illustrated earlier in Fig.~\ref{fig:duck_curve}(b), we enforce a strict chronological split with zero random shuffling:
\begin{itemize}
    \item Training Split (15,192 hours; April~8, 2022 -- December~31, 2023): Captures the post-pandemic industrial recovery and the April~2023 CERC regulatory transition that lowered the uniform price ceiling from Rs.~12,000/MWh to Rs.~10,000/MWh. Mean clearing price is Rs.~5,669.32/MWh with an 18.02\% cap-hit rate.
    \item Validation Split (8,784 hours; Full Leap Year 2024): Used exclusively for Ridge regularization tuning ($\alpha=50$) and GBDT early stopping. Average net thermal load rose by $+10.9$~GW to 169,349.6~MW while renewable penetration increased to 11.39\%, moderating the mean clearing price to Rs.~4,585.00/MWh.
    \item Out-of-Sample Test Split (4,200 hours; January~1, 2025 -- June~24, 2025): Held out completely during all feature design and hyperparameter selection. Renewable penetration reached a record 13.91\% mean, compressing midday solar prices as low as Rs.~99.33/MWh while evening scarcity ramps still triggered 488 ceiling hits ($\ge$Rs.~10,000/MWh, 11.62\% of all test hours).
\end{itemize}

\begin{__TBL_ENV__}[!t]
\centering
\caption{Comparison of Top Standardized OLS vs. Regularized Ridge ($\alpha = 50$) Coefficients Demonstrating Collinearity Suppression}
\label{tab:ridge_coeffs}
\renewcommand{\arraystretch}{1.20}
\setlength{\tabcolsep}{6pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|l|l|r|r|r|l|}
\hline
Feature Identifier & Domain Category & OLS Weight (Rs.) & Ridge Weight ($\alpha=50$) & $|\Delta|$ Shrinkage & Econometric Interpretation \\
\hline
\texttt{mcp\_lag\_24} & Price History \& Momentum & $+1,400.87$ & $+1,342.31$ & $-4.18\%$ & Primary 24-hour diurnal price anchor \\
\hline
\texttt{mcp\_diff\_24\_25} & Price History \& Momentum & $+542.73$ & $+537.04$ & $-1.05\%$ & 24-hour diurnal velocity adjustment \\
\hline
\texttt{mcp\_lag\_1} & Price History \& Momentum & $+518.00$ & $+535.97$ & $+3.47\%$ & Immediate 1-hour persistence anchor \\
\hline
\texttt{re\_penetration\_pct} & Physical Grid \& Renewables & $+690.65$ & $+298.32$ & $-56.81\%$ & Collinear inflation with \texttt{solar\_mw} suppressed \\
\hline
\texttt{solar\_generation\_mw} & Physical Grid \& Renewables & $-588.71$ & $-269.17$ & $-54.28\%$ & Stabilized negative merit-order solar effect \\
\hline
\texttt{net\_demand\_ramp\_1} & Physical Grid \& Renewables & $+270.08$ & $+234.62$ & $-13.13\%$ & Evening duck curve neck ramp premium \\
\hline
\texttt{net\_demand\_mw} & Physical Grid \& Renewables & $+274.50$ & $+188.33$ & $-31.39\%$ & Positive thermal supply-stack slope \\
\hline
\texttt{demand\_mw} & Physical Grid \& Renewables & $-232.46$ & $-56.37$ & $-75.75\%$ & Unphysical negative OLS sign damped by $L_2$ \\
\hline
\texttt{temperature\_mean\_c} & Weather \& Climate & $-350.65$ & $-19.83$ & $-94.34\%$ & Collinear clash with $CDD_{24}$ \& $AT_t$ resolved \\
\hline
\texttt{cdd\_24} & Weather \& Climate & $-344.77$ & $-50.72$ & $-85.29\%$ & Collinear clash with $I_t^{\text{cool}}$ stabilized \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\subsection{Tier 2 Collinearity Resolution via Tikhonov Ridge Regularization}
Table~\ref{tab:ridge_coeffs} compares the standardized regression weights learned by unconstrained OLS against $L_2$-regularized Ridge regression ($\alpha = 50$). In OLS, exact linear dependencies between \texttt{demand\_mw}, \texttt{solar\_generation\_mw}, \texttt{wind\_generation\_mw}, and \texttt{net\_demand\_mw} cause severe coefficient oscillation: OLS assigns an unphysical $+690.65$~Rs./MWh weight to \texttt{re\_penetration\_pct} cancelled by a $-588.71$~Rs./MWh weight on \texttt{solar\_generation\_mw}, and a $-350.65$~Rs./MWh weight on \texttt{temperature\_mean\_c} clashing against $+250.26$ on \texttt{apparent\_temperature\_mean\_c} and $+384.82$ on \texttt{net\_demand\_x\_cdd}. Applying Tikhonov regularization ($\alpha=50$) damps the collinear \texttt{temperature\_mean\_c} oscillation by 94.34\% and \texttt{demand\_mw} by 75.75\%, reducing out-of-sample test MAE from Rs.~561.12/MWh (OLS) to Rs.~544.61/MWh (Ridge).

\begin{__TBL_ENV__}[!t]
\centering
\caption{Master Out-of-Sample Performance Leaderboard Across All Three Modeling Tiers on the Unseen 2025 Test Split ($N = 4,200$ Hours)}
\label{tab:leaderboard}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|l|l|r|r|r|r|r|r|r|r|}
\hline
Modeling Tier & Evaluated Model & Val MAE & Test MAE & Test RMSE & sMAPE & Test $R^2$ & Peak MAE & Spike MAE & Gain vs. 24h \\
\hline
Tier 1: Baselines & Weekly Seasonal Naive (168h) & 903.60 & 986.82 & 1,750.12 & 23.21\% & 0.5770 & 1,279.88 & 1,675.22 & $-49.88\%$ \\
\hline
Tier 1: Baselines & Persistence Naive (1h Lag) & 751.50 & 877.87 & 1,580.71 & 18.45\% & 0.6549 & 1,552.58 & 1,605.32 & $-33.33\%$ \\
\hline
Tier 1: Baselines & Daily Seasonal Naive (24h Ref.) & 629.84 & 658.42 & 1,254.07 & 16.52\% & 0.7828 & 1,125.36 & 1,063.73 & $0.00\%$ (Ref) \\
\hline
Tier 2: Linear & Ordinary Least Squares (OLS) & 483.26 & 561.12 & 834.66 & 16.81\% & 0.9038 & 839.99 & 843.31 & $+14.78\%$ \\
\hline
Tier 2: Linear & Tikhonov Ridge ($\alpha = 50$) & 477.93 & 544.61 & 825.53 & 15.55\% & 0.9059 & 839.22 & 853.88 & $+17.29\%$ \\
\hline
Tier 3: GBDT & XGBoost Regressor (268 Trees) & 361.00 & 439.67 & 708.59 & 12.03\% & 0.9307 & 636.37 & 631.73 & $+33.22\%$ \\
\hline
Tier 3: GBDT & LightGBM Champion (282 Trees) & 358.74 & 433.33 & 703.43 & 11.88\% & 0.9317 & 617.63 & 609.94 & $+34.19\%$ \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_3_tier_progression.jpg}
\caption{Progressive forecast error reduction across modeling tiers on the 4,200-hour unseen 2025 test split: (a) Overall Test MAE versus Evening Peak MAE (18:00--22:00~IST) across all seven models; (b) 24-hour diurnal MAE profile demonstrating consistent LightGBM dominance across every hour of the day.}
\label{fig:tier_progression}
\end{__FIG_WIDE_ENV__}

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_4_forecast_trajectories.jpg}
\caption{Out-of-sample 24-hour price forecast trajectories comparing Actual IEX MCP against LightGBM (Champion), Ridge ($\alpha=50$), and Daily S-Naive across three canonical market regimes: (a) Winter Solar Trough + Evening Scarcity Spike (2025-01-01), (b) Steep Industrial Peak Ramp (2025-01-06), and (c) Spring High-Solar Midday Glut (2025-03-16).}
\label{fig:trajectories}
\end{__FIG_WIDE_ENV__}

\subsection{Multi-Tier Out-of-Sample Forecasting Performance}
Table~\ref{tab:leaderboard} and Fig.~\ref{fig:tier_progression} present the comprehensive out-of-sample evaluation across all seven models on the 4,200 unseen hours of 2025. Several key quantitative findings emerge:
\begin{enumerate}
    \item Failure of heuristic market baselines during ramps: Among Tier~1 baselines, the 24-hour Daily Seasonal Naive model is the strongest heuristic (Test MAE of Rs.~658.42/MWh, $R^2 = 0.7828$), outperforming 1-hour Persistence (Rs.~877.87/MWh) and 168-hour Weekly Naive (Rs.~986.82/MWh). However, during evening peak hours (18:00--22:00~IST), Daily S-Naive error balloons to Rs.~1,125.36/MWh because yesterday's clearing price cannot anticipate today's cloud cover or industrial demand ramps.
    \item Value of causal exogenous features in Tier~2: Introducing the 53 causal features in Tier~2 Ridge regression ($\alpha=50$) reduces Test MAE by Rs.~113.81/MWh ($-17.29\%$) down to Rs.~544.61/MWh and cuts Test RMSE by 34.17\% (from Rs.~1,254.07 to Rs.~825.53/MWh), raising out-of-sample $R^2$ from $0.7828$ to $0.9059$.
    \item Superiority of non-linear leaf-wise GBDT in Tier~3: Moving from linear Ridge regression to Tier~3 histogram-based gradient boosting yields a substantial second leap in accuracy. The champion 282-tree LightGBM Regressor achieves an out-of-sample Test MAE of Rs.~433.33/MWh (equivalent to Rs.~0.43/kWh), Test RMSE of Rs.~703.43/MWh, sMAPE of 11.88\%, and $R^2 = 0.9317$. This represents a 34.19\% MAE reduction (Rs.~225.09/MWh saved per hour) over the 24h market persistence baseline and a 20.43\% MAE reduction (Rs.~111.28/MWh saved) over tuned Ridge regression.
    \item Peak-hour and scarcity spike resilience: During high-risk evening peak hours (18:00--22:00~IST) and severe price spikes ($P_t \ge \text{Rs.~8,000/MWh}$), LightGBM achieves a Peak MAE of Rs.~617.63/MWh and Spike MAE of Rs.~609.94/MWh, cutting peak procurement errors by 45.12\% compared to Daily S-Naive (Rs.~1,125.36/MWh) and by 26.40\% compared to Ridge (Rs.~839.22/MWh). Fig.~\ref{fig:trajectories} illustrates how LightGBM tracks both deep midday solar collapses and abrupt Rs.~10,000/MWh evening ceiling plateaus across three distinct seasonal regimes.
\end{enumerate}

\begin{__TBL_ENV__}[!t]
\centering
\caption{Pairwise Diebold-Mariano Newey-West HAC ($L = 9$) Statistical Significance Tests and Residual Error Distribution Diagnostics on the 2025 Test Split ($N = 4,200$)}
\label{tab:dm_and_residuals}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|l|r|r|r|r|r|r|r|r|}
\hline
Evaluated Model & Mean Bias & Std. Error & Skewness & Kurtosis & Error P10 & Error P90 & DM vs. LightGBM & Two-Sided $p$-Value \\
\hline
Weekly S-Naive (168h) & $-51.24$ & 1,749.37 & $-0.173$ & $4.622$ & $-1,482.42$ & $+1,200.80$ & $+11.889$ & $< 1.0 \times 10^{-20}$ (1\% Sig.) \\
\hline
Persistence Naive (1h) & $+1.12$ & 1,580.71 & $+0.162$ & $4.480$ & $-1,216.04$ & $+1,168.38$ & $+18.685$ & $< 1.0 \times 10^{-20}$ (1\% Sig.) \\
\hline
Daily S-Naive (24h Ref.) & $-7.10$ & 1,254.05 & $+0.128$ & $7.458$ & $-962.02$ & $+820.84$ & $+7.780$ & $9.10 \times 10^{-15}$ (1\% Sig.) \\
\hline
Linear Regression (OLS) & $-37.49$ & 833.81 & $-0.415$ & $4.747$ & $-902.11$ & $+735.54$ & $+11.917$ & $< 1.0 \times 10^{-20}$ (1\% Sig.) \\
\hline
Tikhonov Ridge ($\alpha=50$) & $-54.87$ & 823.70 & $-0.343$ & $5.009$ & $-896.76$ & $+705.62$ & $+10.449$ & $< 1.0 \times 10^{-20}$ (1\% Sig.) \\
\hline
XGBoost (268 Trees) & $-175.60$ & 686.49 & $-0.211$ & $6.051$ & $-900.15$ & $+361.60$ & $+2.514$ & $1.20 \times 10^{-2}$ (5\% Sig.) \\
\hline
LightGBM (Champion) & $-187.82$ & 677.89 & $-0.267$ & $6.927$ & $-891.18$ & $+323.03$ & Reference & Superior Champion \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_8_residual_diagnostics.jpg}
\caption{Econometric residual diagnostics on the 4,200-hour test set: (a) Inter-decile (P10 to P90) residual error spread demonstrating how LightGBM compresses positive over-prediction tail risk down to $+$Rs.~323.03/MWh; (b) Newey-West HAC ($L=9$) Diebold-Mariano test statistics proving statistically significant superiority of LightGBM over all six competing models.}
\label{fig:residuals}
\end{__FIG_WIDE_ENV__}

\subsection{Econometric Residual Diagnostics and Diebold-Mariano HAC Tests}
Table~\ref{tab:dm_and_residuals} and Fig.~\ref{fig:residuals} report the residual distribution moments and Newey-West HAC ($L=9$) Diebold-Mariano hypothesis test statistics. Across all 4,200 test hours, LightGBM achieves the lowest residual standard deviation (Rs.~677.89/MWh versus Rs.~1,254.05/MWh for Daily S-Naive and Rs.~823.70/MWh for Ridge) and compresses the 90th-percentile error (\texttt{Error\_P90}) from $+$Rs.~820.84/MWh (Daily S-Naive) and $+$Rs.~705.62/MWh (Ridge) down to $+$Rs.~323.03/MWh. The Newey-West HAC Diebold-Mariano test confirms that LightGBM's accuracy improvement is statistically significant at the 1\% level against Daily S-Naive ($DM = +7.780, p = 9.10 \times 10^{-15}$), Ridge $\alpha=50$ ($DM = +10.449, p < 10^{-20}$), OLS ($DM = +11.917, p < 10^{-20}$), and Persistence ($DM = +18.685, p < 10^{-20}$), and significant at the 5\% level even against the fellow Tier~3 XGBoost ensemble ($DM = +2.514, p = 0.0120$).

\begin{__TBL_ENV__}[!t]
\centering
\caption{Exact TreeSHAP Global Feature Importance (Top 10 Signals) and Local Regime Case-Study Attributions on the 2025 Test Split ($\mathbb{E}[f(X)] = \text{Rs.~3,873.06/MWh}$)}
\label{tab:shap_results}
\renewcommand{\arraystretch}{1.22}
\setlength{\tabcolsep}{5pt}
\resizebox{\textwidth}{!}{%
\begin{tabular}{|c|l|l|r|r|r|l|}
\hline
Rank & Feature Identifier & Domain Category & Mean $|\text{SHAP}|$ & Std. SHAP & Corr. ($r$) & Local Case Study Attribution Examples \\
\hline
1 & \texttt{mcp\_lag\_24} & Price History \& Momentum & Rs. 1,250.71 & Rs. 1,227.98 & $+0.978$ & Case A: $-1,161.50$ $\vert$ Case C: $+2,200.87$ \\
\hline
2 & \texttt{mcp\_lag\_1} & Price History \& Momentum & Rs. 949.39 & Rs. 993.93 & $+0.972$ & Case A: $-782.91$ $\vert$ Case B: $+1,627.24$ \\
\hline
3 & \texttt{net\_demand\_ramp\_1} & Physical Grid \& Renewables & Rs. 321.07 & Rs. 384.45 & $+0.900$ & Case A: $-315.74$ $\vert$ Case C: $+921.29$ \\
\hline
4 & \texttt{mcp\_diff\_24\_25} & Price History \& Momentum & Rs. 242.83 & Rs. 338.80 & $+0.900$ & Case A: $-131.79$ $\vert$ Case B: $+753.31$ \\
\hline
5 & \texttt{market\_tightness\_lag\_24} & Market Bidding Signals & Rs. 181.88 & Rs. 213.55 & $+0.547$ & Case A ($\tau=0.47$): $-140.99$ $\vert$ Case C ($\tau=2.90$): $+534.39$ \\
\hline
6 & \texttt{net\_demand\_mw} & Physical Grid \& Renewables & Rs. 149.62 & Rs. 158.49 & $+0.905$ & Case A (133 GW): $-100.04$ $\vert$ Case C (182 GW): $+358.42$ \\
\hline
7 & \texttt{mcp\_lag\_48} & Price History \& Momentum & Rs. 65.78 & Rs. 61.71 & $+0.831$ & Case C (10k Cap 48h ago): $+132.32$ \\
\hline
8 & \texttt{mcp\_diff\_1\_2} & Price History \& Momentum & Rs. 59.04 & Rs. 74.55 & $+0.750$ & Case A ($-\text{Rs.}538$ drop): $-60.76$ \\
\hline
9 & \texttt{mcp\_lag\_168} & Price History \& Momentum & Rs. 58.26 & Rs. 51.97 & $+0.863$ & Case A (7-day anchor): $-63.80$ \\
\hline
10 & \texttt{purchase\_bid\_lag\_24} & Market Bidding Signals & Rs. 31.99 & Rs. 45.56 & $+0.796$ & Case C (17.9 GW buy bids): $+167.93$ \\
\hline
\end{tabular}%
}
\end{__TBL_ENV__}

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_5_shap_global_and_category.jpg}
\caption{Exact TreeSHAP explainability analysis across 4,200 unseen test hours: (a) Top 12 individual features ranked by mean absolute rupee contribution ($\mathbb{E}[|\phi_j|]$ in Rs./MWh); (b) Cumulative attribution share across the five physical and econometric domain categories.}
\label{fig:shap_global}
\end{__FIG_WIDE_ENV__}

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_6_merit_order_supply_stack.jpg}
\caption{Physical grid supply-stack verification and counterfactual stress testing: (a) Empirical TreeSHAP contribution of \texttt{net\_demand\_mw} versus National Net Thermal Demand (GW), revealing the non-linear 160~GW Peaker Scarcity Knee; (b) Simulated MCP response under counterfactual weather and demand perturbations.}
\label{fig:merit_order}
\end{__FIG_WIDE_ENV__}

\subsection{Exact TreeSHAP Attribution and the 160 GW Peaker Scarcity Knee}
Table~\ref{tab:shap_results} and Fig.~\ref{fig:shap_global} present the exact TreeSHAP decomposition of the champion LightGBM model across the 4,200 test hours. Aggregated by domain category (Fig.~\ref{fig:shap_global}(b)), Price History and Momentum accounts for 74.18\% (Rs.~2,806.43/MWh cumulative $|\text{SHAP}|$) of total attribution, Physical Grid and Renewables accounts for 16.13\% (Rs.~610.26/MWh), Market Bidding Signals accounts for 6.66\% (Rs.~251.92/MWh), Calendar and Diurnal Cycles accounts for 2.07\% (Rs.~78.40/MWh), and Weather and Climate accounts for 0.96\% (Rs.~36.37/MWh direct effect, as the majority of weather impact is mediated through \texttt{net\_demand\_mw} and \texttt{solar\_generation\_mw}).

Examining specific local regime case studies in Table~\ref{tab:shap_results} demonstrates how TreeSHAP provides auditable rupee explanations:
\begin{itemize}
    \item Case A (Midday Solar Glut on Jan~1, 2025 at 13:00~IST; Actual: Rs.~2,607.33, Predicted: Rs.~2,823.17/MWh): Starting from the base price of Rs.~3,873.06/MWh, a steep negative net demand ramp ($\Delta ND_t^{(1)} = -8,576.96$~MW/h as midday solar surges) deducts $-$Rs.~315.74/MWh, low net thermal demand ($133.13$~GW) deducts $-$Rs.~100.04/MWh, buyer-favorable auction tightness ($\tau_{t-24} = 0.47$) deducts $-$Rs.~140.99/MWh, and low prior-day and prior-hour price anchors deduct $-$Rs.~1,161.50 and $-$Rs.~782.91/MWh.
    \item Case C (Evening Scarcity Spike on Jan~1, 2025 at 18:00~IST; Actual: Rs.~9,753.90, Predicted: Rs.~9,690.02/MWh): Five hours later on the same day, solar output drops to zero and net thermal demand ramps by $+13,466.77$~MW/h to 181.72~GW. TreeSHAP reveals that \texttt{net\_demand\_ramp\_1} adds $+$Rs.~921.29/MWh, \texttt{net\_demand\_mw} adds $+$Rs.~358.42/MWh, severe order-book tightness ($\tau_{t-24} = 2.90\times$) adds $+$Rs.~534.39/MWh, and \texttt{mcp\_lag\_24} adds $+$Rs.~2,200.87/MWh, driving the prediction to Rs.~9,690.02/MWh (within 0.65\% of the actual Rs.~9,753.90/MWh clearing price).
\end{itemize}

Crucially, plotting the TreeSHAP impact of \texttt{net\_demand\_mw} against national net thermal load in Fig.~\ref{fig:merit_order}(a) uncovers the empirical National Merit-Order Supply Stack: below 145~GW, net demand exerts a negative SHAP effect ($-$Rs.~100 to $-$Rs.~200/MWh) because cheap pit-head coal and renewables dominate; between 145~GW and 160~GW, the slope rises gently; and above the 160~GW Peaker Scarcity Knee, the curve inflects steeply upward ($+$Rs.~350 to $+$Rs.~410/MWh direct contribution) as marginal generation shifts to expensive gas and liquid-fuel peakers.

\begin{__FIG_WIDE_ENV__}[!t]
\centering
\includegraphics[width=__FIG_WIDTH_WIDE__]{images/paper_fig_7_bid_optimization_roi.jpg}
\caption{Energy-neutral DISCOM procurement optimization results on a 100~MW baseline portfolio (2,400~MWh/day, $\gamma = 30\%$ flexible load): (a) Optimized 24-hour load schedule shifting 30~MW/h from the evening scarcity peak (18:00--23:00~IST) into the midday solar window (10:00--15:00~IST); (b) Cumulative 24-hour bill trajectory demonstrating a net daily saving of 11.9\%.}
\label{fig:bid_opt}
\end{__FIG_WIDE_ENV__}

\subsection{Counterfactual Stress Testing and DISCOM Procurement Optimization ROI}
Fig.~\ref{fig:merit_order}(b) illustrates the counterfactual weather stress-testing engine (Algorithm~\ref{alg:optimizer}) applied to a baseline operating block ($ND_t = 146.0$~GW, baseline $\hat{y}_t = \text{Rs.~4,610/MWh}$). While a $+30\%$ solar surge depresses the clearing price by $-25.8\%$ to Rs.~3,420/MWh, simulating a monsoon cloud-cover dropout ($-40\%$ solar generation) combined with a $+25\%$ evening thermal ramp pushes net thermal load across the 160~GW knee to 162.4~GW, causing the simulated clearing price to jump by $+40.8\%$ ($+$Rs.~1,880/MWh) to Rs.~6,490/MWh in 3.4~ms of live inference time.

Finally, Fig.~\ref{fig:bid_opt} evaluates the financial return on investment (ROI) of the Energy-Neutral Smart Bid Optimizer (Eq.~\ref{eq:bid_opt}) for a typical 100~MW DISCOM or open-access industrial portfolio ($2,400$~MWh/day total energy requirement, $\gamma = 30\%$ shiftable load). Across representative winter scarcity profiles, an unoptimized flat 100~MW procurement schedule incurs a daily electricity bill of Rs.~106.85~Lakhs/day. By shifting 30~MW/h out of the six highest-priced evening scarcity hours (reducing evening draw to 70~MW) and reallocating that exact $180$~MWh into the six lowest-priced midday solar trough hours (boosting midday draw to 130~MW), the AI-optimized schedule reduces the daily bill to Rs.~94.12~Lakhs/day while preserving 100\% daily energy neutrality ($2,400$~MWh). This yields a net financial saving of Rs.~12.73~Lakhs/day ($-11.9\%$ direct bill reduction), translating to an annualized procurement saving of Rs.~46.46~Crores/year.

\section{Discussion}

\subsection{Why Gradient-Boosted Trees Outperform Linear Econometrics on Power Grids}
The experimental progression from Tier~1 Daily Seasonal Naive ($\text{MAE} = \text{Rs.~658.42/MWh}$) to Tier~2 Ridge Regression ($\text{MAE} = \text{Rs.~544.61/MWh}$) and Tier~3 LightGBM ($\text{MAE} = \text{Rs.~433.33/MWh}$) highlights two distinct sources of predictive skill. First, the Rs.~113.81/MWh gain from Tier~1 to Tier~2 stems from incorporating exogenous physical telemetry (net thermal demand, 1-hour ramp velocity, renewable penetration, and lagged auction tightness). Second, the additional Rs.~111.28/MWh gain from Tier~2 to Tier~3 (statistically significant at $DM = +10.449, p < 10^{-20}$) arises because wholesale electricity price formation is governed by threshold regime switching rather than global linear additivity. In a linear model, a $+10$~GW increase in net demand adds a constant rupee increment regardless of whether the grid is operating at 120~GW (midday solar surplus) or 175~GW (evening thermal scarcity). LightGBM's leaf-wise decision trees naturally partition the feature space around the 160~GW peaker knee and condition the effect of net demand ramps on order-book tightness ($\tau_{t-24}$) and hour-of-day harmonics.

\subsection{Operational Value of Exact TreeSHAP and Counterfactual Stress Testing}
In commercial utility procurement desks, point forecasts alone are insufficient when bidding millions of rupees into a blind day-ahead auction. By pairing every hourly prediction with its exact 53-feature TreeSHAP rupee decomposition, EnergyCast transforms an ensemble of 282 decision trees into a transparent glass-box ledger. When the platform flags an evening scarcity alert, the trading officer can immediately verify whether the predicted spike is driven by structural order-book tightness ($\tau_{t-24} > 2.0$), a steep sunset solar ramp ($\Delta ND_t^{(1)} > +12$~GW/h), or historical price momentum. Furthermore, because the in-memory inference engine scores perturbed 53-feature vectors in $\sim 3.4$~ms, traders can interactively stress-test their bid caps against sudden cloud cover or temperature anomalies before locking in their 10:30~AM IST IEX DAM submission.

\subsection{Limitations and Generalizability}
Despite its strong out-of-sample performance across 4,200 test hours, the present architecture has three practical limitations that should be noted:
\begin{enumerate}
    \item Unobserved unplanned thermal outages: While Grid-India telemetry captures aggregate national demand and renewable generation, real-time unit-level forced outages (boiler tube leaks or coal stock-outs at specific super-critical thermal stations) and inter-regional transmission corridor congestion are not publicly released prior to the D-1 gate. Sudden evening scarcity spikes triggered by unannounced generator trips therefore remain partially unexplainable by public pre-gate telemetry, contributing to the residual negative mean bias ($-$Rs.~187.82/MWh) observed on censored Rs.~10,000/MWh ceiling hours.
    \item Deterministic day-ahead physical schedules: In our historical out-of-sample evaluation, day-ahead physical demand and renewable generation profiles represent realized national grid trajectories. In live deployment prior to 10:30~AM IST on day $D-1$, these variables must be supplied by day-ahead numerical weather prediction (NWP) and load forecasts, which introduce upstream input uncertainty. However, our counterfactual simulator explicitly mitigates this risk by allowing traders to evaluate $\pm 40\%$ renewable and load forecast errors interactively.
    \item Single-market uniform clearing assumption: The current system is calibrated specifically for India's uniform-price IEX Day-Ahead Market under CERC's $[\text{Rs.~0}, \text{Rs.~10,000}]/\text{MWh}$ regulatory cap and does not directly model locational marginal pricing (LMP) or nodal transmission congestion used in US ISO markets.
\end{enumerate}

\subsection{Regulatory, Market Governance, and Ethical Considerations}
Automated algorithmic bidding in wholesale electricity markets raises important regulatory and market-governance considerations under the Central Electricity Regulatory Commission (CERC) Power Market Regulations \cite{cerc2023order}. First, EnergyCast is designed strictly as a price-taking procurement decision-support and load-shifting tool for DISCOMs and industrial consumers rather than a strategic capacity-withholding or market-manipulation agent. Shifting flexible industrial demand from evening thermal scarcity hours (18:00--22:00~IST) into midday solar surplus hours (10:00--15:00~IST) is socially and environmentally beneficial: it reduces curtailment of clean solar energy at midday while shaving peak thermal coal and gas dispatch in the evening, thereby improving national grid stability and lowering carbon intensity. Second, because all 53 features strictly respect the public 10:30~AM IST D-1 information boundary ($\mathcal{F}_{D-1, 10:30}$), the system operates exclusively on transparent, publicly auditable market and meteorological data without relying on privileged insider order-book information.

\subsection{Future Directions}
Future research will extend EnergyCast along five technical directions: (i) integrating conformal quantile regression (LightGBM-CQR) to replace empirical residual bands with distribution-free, heteroskedastic 90\% prediction intervals that widen dynamically during monsoon and heatwave transitions; (ii) expanding the forecasting engine to jointly model the IEX Real-Time Market (RTM), which clears every 30 minutes, and the Green Day-Ahead Market (GDAM) to enable cross-market arbitrage between D-1 DAM and intra-day RTM auctions; (iii) incorporating satellite cloud-motion vector forecasts from INSAT-3DR to improve 36-hour solar ramp anticipation; (iv) coupling the linear load-shifting optimizer with Battery Energy Storage System (BESS) state-of-charge degradation models for hybrid solar-plus-storage bidding; and (v) implementing automated online incremental re-training to adapt to future CERC price-cap revisions and expanding national renewable capacity.

\section{Conclusion}
This paper presented EnergyCast, an end-to-end causal day-ahead electricity market clearing price forecasting, exact TreeSHAP explainability, and energy-neutral procurement optimization system for the Indian Energy Exchange (IEX) Day-Ahead Market. By harmonizing 28,176 hours of multi-year IEX auction data, POSOCO national grid telemetry, and 5-zone demand-weighted ERA5 weather reanalysis under a strict 10:30~AM IST D-1 causal gate, we engineered 53 leak-free features across five physical and econometric domains. Across a rigorous three-tier evaluation on 4,200 unseen test hours in 2025, our champion 282-tree LightGBM ensemble achieved an out-of-sample MAE of Rs.~433.33/MWh (Rs.~0.43/kWh), RMSE of Rs.~703.43/MWh, sMAPE of 11.88\%, and $R^2 = 0.9317$. This represents a 34.19\% error reduction over the 24-hour market persistence baseline (Rs.~658.42/MWh) and a 20.43\% reduction over $L_2$-regularized Ridge regression (Rs.~544.61/MWh), confirmed at $p = 9.10 \times 10^{-15}$ ($DM = -7.780$) via Newey-West HAC Diebold-Mariano testing.

Beyond predictive accuracy, exact TreeSHAP attribution decomposed every hourly forecast into an unconditional base price (Rs.~3,873.06/MWh) plus 53 exact rupee-per-MWh drivers, empirically identifying the national grid's non-linear 160~GW Peaker Scarcity Knee. Deployed within a sub-4~ms interactive web command center with counterfactual weather stress testing and constrained energy-neutral load shifting, EnergyCast demonstrated a Rs.~12.73~Lakhs/day (11.9\%, or Rs.~46.46~Crores/year) procurement bill reduction on a 100~MW baseline portfolio, providing DISCOMs and open-access power traders with an auditable, high-precision decision-support platform.
"""
    return (
        body.replace("__TBL_ENV__", tbl_env)
        .replace("__FIG_WIDE_ENV__", fig_wide_env)
        .replace("__ALG_ENV__", alg_env)
        .replace("__FIG_WIDTH_WIDE__", fig_width_wide)
    )


def get_bibliography_items() -> str:
    """Returns 30 formatted bibliography items with zero bold text."""
    return r"""
\begin{thebibliography}{30}

\bibitem{weron2014electricity}
Weron, R.: Electricity price forecasting: A review of the state-of-the-art with a look into the future. International Journal of Forecasting 30(4), 1030--1081 (2014).

\bibitem{lago2021forecasting}
Lago, J., Marcjasz, G., De Schutter, B., Weron, R.: Forecasting day-ahead electricity prices: A review of state-of-the-art algorithms, best practices and an open-access benchmark. Applied Energy 293, 116983 (2021).

\bibitem{cerc2023order}
Central Electricity Regulatory Commission (CERC): Order on Review of Price Cap in Day-Ahead Market (DAM) and Real-Time Market (RTM) on Power Exchanges in India. Petition No.~04/SM/2023, New Delhi (2023).

\bibitem{iex2024market}
Indian Energy Exchange (IEX): Day-Ahead Market (DAM) Auction Mechanism and Historical Market Snapshot Reports (2022--2025). Available at: \url{https://www.iexindia.com/}. Accessed 2025.

\bibitem{contreras2003arima}
Contreras, J., Espinola, R., Nogales, F.J., Conejo, A.J.: ARIMA models to predict next-day electricity prices. IEEE Transactions on Power Systems 18(3), 1014--1020 (2003).

\bibitem{conejo2005day}
Conejo, A.J., Plazas, M.A., Espinola, R., Molina, A.B.: Day-ahead electricity price forecasting using the wavelet transform and ARIMA models. IEEE Transactions on Power Systems 20(2), 1035--1042 (2005).

\bibitem{posoco2024report}
Grid Controller of India Limited (POSOCO / Grid-India): National Load Despatch Centre (NLDC) Daily Power System Operation and Renewable Generation Reports. New Delhi (2025).

\bibitem{ugurlu2018electricity}
Ugurlu, U., Oksuz, I., Tas, O.: Electricity price forecasting using recurrent neural networks. Energies 11(5), 1255 (2018).

\bibitem{lehna2022forecasting}
Lehna, M., Scheller, F., Herwartz, H.: Forecasting day-ahead electricity prices: A comparison of time series and deep learning models on the German spot market. Energy Economics 106, 105742 (2022).

\bibitem{ziel2018day}
Ziel, F., Weron, R.: Day-ahead electricity price forecasting with high-dimensional structures: Univariate vs. multivariate modeling frameworks. Energy Economics 70, 396--420 (2018).

\bibitem{lago2018forecasting}
Lago, J., De Ridder, F., De Schutter, B.: Forecasting spot electricity prices: Deep learning approaches and empirical comparison of traditional algorithms. Applied Energy 221, 386--405 (2018).

\bibitem{tschora2022electricity}
Tschora, L., Pierre, E., Plantevit, M., Robardet, C.: Electricity price forecasting on the day-ahead market using machine learning. Applied Energy 313, 118752 (2022).

\bibitem{ke2017lightgbm}
Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., Liu, T.-Y.: LightGBM: A highly efficient gradient boosting decision tree. In: Advances in Neural Information Processing Systems (NeurIPS), vol.~30, pp.~3146--3154 (2017).

\bibitem{chen2016xgboost}
Chen, T., Guestrin, C.: XGBoost: A scalable tree boosting system. In: Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp.~785--794 (2016).

\bibitem{lundberg2017unified}
Lundberg, S.M., Lee, S.-I.: A unified approach to interpreting model predictions. In: Advances in Neural Information Processing Systems (NeurIPS), vol.~30, pp.~4765--4774 (2017).

\bibitem{lundberg2020local}
Lundberg, S.M., Erion, G., Chen, H., DeGrave, A., Prutkin, J.M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., Lee, S.-I.: From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence 2(1), 56--67 (2020).

\bibitem{diebold1995comparing}
Diebold, F.X., Mariano, R.S.: Comparing predictive accuracy. Journal of Business \& Economic Statistics 13(3), 253--263 (1995).

\bibitem{newey1987simple}
Newey, W.K., West, K.D.: A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica 55(3), 703--708 (1987).

\bibitem{nowotarski2018recent}
Nowotarski, J., Weron, R.: Recent advances in electricity price forecasting: A review of probabilistic forecasting. Renewable and Sustainable Energy Reviews 81, 1548--1568 (2018).

\bibitem{hoerl1970ridge}
Hoerl, A.E., Kennard, R.W.: Ridge regression: Biased estimation for nonorthogonal problems. Technometrics 12(1), 55--67 (1970).

\bibitem{friedman2001greedy}
Friedman, J.H.: Greedy function approximation: A gradient boosting machine. Annals of Statistics 29(5), 1189--1232 (2001).

\bibitem{hersbach2020era5}
Hersbach, H., Bell, B., Berrisford, P., et al.: The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society 146(730), 1999--2049 (2020).

\bibitem{denholm2015overgeneration}
Denholm, P., O'Connell, M., Brinkman, G., Jorgenson, J.: Overgeneration from solar energy in California: A field guide to the duck chart. Technical Report NREL/TP-6A20-65023, National Renewable Energy Laboratory (2015).

\bibitem{pedregosa2011scikit}
Pedregosa, F., Varoquaux, G., Gramfort, A., et al.: Scikit-learn: Machine learning in Python. Journal of Machine Learning Research 12, 2825--2830 (2011).

\bibitem{shapley1953value}
Shapley, L.S.: A value for $n$-person games. In: Kuhn, H.W., Tucker, A.W. (eds.) Contributions to the Theory of Games, vol.~II, pp.~307--317. Princeton University Press, Princeton (1953).

\bibitem{harvey1997testing}
Harvey, D., Leybourne, S., Newbold, P.: Testing the equality of prediction mean squared errors. International Journal of Forecasting 13(2), 281--291 (1997).

\bibitem{marcjasz2023distributional}
Marcjasz, G., Narajewski, M., Weron, R., Ziel, F.: Distributional neural networks for electricity price forecasting. Energy Economics 125, 106843 (2023).

\bibitem{kirschen2018fundamentals}
Kirschen, D.S., Strbac, G.: Fundamentals of Power System Economics, 2nd edn. John Wiley \& Sons, Chichester (2018).

\bibitem{openmeteo2025}
Zippenfenig, P.: Open-Meteo.com Weather API: High-resolution historical ERA5 reanalysis data feed. Zenodo (2024).

\bibitem{cea2025load}
Central Electricity Authority (CEA), Ministry of Power, Government of India: National Electricity Plan and All-India Installed Renewable Capacity Statistics. New Delhi (2025).

\end{thebibliography}
"""


# ==============================================================================
# 1. SPRINGER LNCS FORMAT GENERATOR (`Springer_Paper/main.tex`)
# ==============================================================================
def build_springer_tex() -> str:
    header = r"""\documentclass[10pt,a4paper,twoside]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{mathptmx}
\usepackage[scaled=0.90]{helvet}
\usepackage{courier}
\usepackage[a4paper,textwidth=12.2cm,textheight=19.3cm,centering,headsep=14pt]{geometry}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{array,booktabs,multirow}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage[font=small,labelfont=normalfont]{caption}
\usepackage[colorlinks=true,linkcolor=black,citecolor=black,urlcolor=black]{hyperref}
\usepackage{url}

\setlength{\parindent}{15pt}
\setlength{\parskip}{0pt}
\renewcommand{\baselinestretch}{1.04}
\allowdisplaybreaks
\emergencystretch=1.5em

\titleformat{\section}{\normalfont\large}{\thesection}{1em}{}
\titlespacing*{\section}{0pt}{18pt plus 4pt minus 2pt}{8pt plus 2pt}
\titleformat{\subsection}{\normalfont\normalsize}{\thesubsection}{1em}{}
\titlespacing*{\subsection}{0pt}{14pt plus 3pt minus 2pt}{6pt plus 2pt}
\titleformat{\subsubsection}{\normalfont\normalsize\itshape}{\thesubsubsection}{0.8em}{}
\titlespacing*{\subsubsection}{0pt}{10pt plus 2pt minus 2pt}{4pt plus 1pt}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyhead[LE]{\small\thepage\hspace{1.8em}Madgi V. et al.}
\fancyhead[RO]{\small EnergyCast: Causal Day-Ahead Electricity Market Price Forecasting\hspace{1.8em}\thepage}

\begin{document}
\thispagestyle{empty}

\vspace*{0.6cm}
\begin{center}
{\Large EnergyCast: Causal Multi-Tier Day-Ahead Electricity Market Clearing Price Forecasting, Exact TreeSHAP Attribution, and Energy-Neutral Procurement Optimization\par}
\vspace{0.65cm}
{\normalsize
Vinay M Madgi\textsuperscript{[0009-0006-8583-331X]},
Rahul S Yankanchi\textsuperscript{[0009-0004-7182-1940]},\\
Sagar S Mirje\textsuperscript{[0009-0007-5391-8421]},
Darshan R Talawar\textsuperscript{[0009-0008-6124-9032]}, and\\
Channabasappa Muttal\textsuperscript{[0000-0002-8419-6370]}\par}
\vspace{0.35cm}
{\small
Department of Computer Science and Engineering, KLE Technological University, Hubballi\\
580031, Karnataka, India\\
\texttt{vinaymadgi28@gmail.com, \{01fe23bcs306, 01fe23bcs297, 01fe23bcs287, 01fe23bcs303, channabasappa\}@kletech.ac.in}\par}
\end{center}

\vspace{0.45cm}
\begin{quote}\small
\noindent Abstract. Day-ahead wholesale electricity markets with high renewable penetration exhibit severe diurnal non-stationarity, midday solar price suppression, and abrupt evening scarcity spikes that challenge traditional linear econometrics and opaque deep neural networks. In the Indian Energy Exchange (IEX) Day-Ahead Market (DAM), Distribution Companies (DISCOMs) and industrial open-access traders must submit 24-hour bid portfolios prior to the strict 10:30~AM IST auction gate on day $D-1$ without forward market visibility. We present EnergyCast, an end-to-end causal multi-tier electricity price forecasting, exact game-theoretic explainability, and energy-neutral procurement optimization system evaluated across 28,176 hourly observations (2022--2025). The architecture harmonizes 15-minute IEX DAM auction records, Grid-India (POSOCO) national demand and renewable generation telemetry, and 5-zone demand-weighted ERA5 meteorological reanalysis into 53 leak-free causal features across five physical and econometric domains. We benchmark a three-tier modeling hierarchy spanning seasonal persistence baselines, Tikhonov $L_2$-regularized Ridge regression ($\alpha=50$), and histogram-based gradient-boosted decision trees (LightGBM and XGBoost) integrated with a statutory Central Electricity Regulatory Commission (CERC) boundary projection operator ($[\text{Rs.~0}, \text{Rs.~10,000}]/\text{MWh}$). On an unseen 4,200-hour chronological test split in 2025, our champion 282-tree LightGBM ensemble achieves an out-of-sample Mean Absolute Error (MAE) of Rs.~433.33/MWh (Rs.~0.43/kWh) and $R^2 = 0.9317$, reducing forecast error by 34.19\% over the 24-hour market persistence baseline (Rs.~658.42/MWh, Newey-West HAC Diebold-Mariano $DM = -7.780, p = 9.10 \times 10^{-15}$) and by 20.43\% over tuned Ridge regression (Rs.~544.61/MWh). Furthermore, exact TreeSHAP attribution decomposes every hourly forecast into exact rupee-per-MWh drivers, uncovering the national grid's non-linear 160~GW Peaker Scarcity Knee and powering an energy-neutral load-shifting optimizer that reduces daily DISCOM procurement costs by 11.9\% (Rs.~12.73~Lakhs/day on a 100~MW portfolio).

\vspace{0.25cm}
\noindent Keywords: Day-Ahead Electricity Market $\cdot$ Indian Energy Exchange (IEX) $\cdot$ LightGBM $\cdot$ Explainable AI (TreeSHAP) $\cdot$ Diebold-Mariano HAC Test $\cdot$ Duck Curve $\cdot$ Merit-Order Supply Stack $\cdot$ Energy-Neutral Bid Optimization
\end{quote}
\vspace{0.2cm}
"""
    return header + get_core_body(is_ieee=False) + get_bibliography_items() + "\n\\end{document}\n"


# ==============================================================================
# 2. IEEE FORMAT GENERATOR (`IEEE_Paper/main.tex`)
# ==============================================================================
def build_ieee_tex() -> str:
    header = r"""\documentclass[journal,10pt,twocolumn]{IEEEtran}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{array,booktabs,multirow}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage[font=footnotesize,labelfont=normalfont]{caption}
\usepackage[colorlinks=true,linkcolor=black,citecolor=black,urlcolor=black]{hyperref}
\usepackage{url}

\allowdisplaybreaks
\emergencystretch=1.5em

\begin{document}

\title{EnergyCast: Causal Multi-Tier Day-Ahead Electricity Market Clearing Price Forecasting, Exact TreeSHAP Attribution, and Energy-Neutral Procurement Optimization}

\author{Vinay~M~Madgi,~\IEEEmembership{ORCID:~0009-0006-8583-331X},
        Rahul~S~Yankanchi,
        Sagar~S~Mirje,
        Darshan~R~Talawar,
        and~Channabasappa~Muttal%
\thanks{The authors are with the Department of Computer Science and Engineering, KLE Technological University, Hubballi 580031, Karnataka, India (e-mail: vinaymadgi28@gmail.com; 01fe23bcs306@kletech.ac.in; 01fe23bcs297@kletech.ac.in; 01fe23bcs287@kletech.ac.in; 01fe23bcs303@kletech.ac.in; channabasappa@kletech.ac.in).}}

\markboth{IEEE Transactions on Power Systems / Smart Grid Research Manuscript, Vol.~XX, No.~X, 2026}%
{Madgi \MakeLowercase{\textit{et al.}}: EnergyCast: Causal Day-Ahead Electricity Market Clearing Price Forecasting}

\maketitle

\begin{abstract}
Day-ahead wholesale electricity markets with high renewable penetration exhibit severe diurnal non-stationarity, midday solar price suppression, and abrupt evening scarcity spikes that challenge traditional linear econometrics and opaque deep neural networks. In the Indian Energy Exchange (IEX) Day-Ahead Market (DAM), Distribution Companies (DISCOMs) and industrial open-access traders must submit 24-hour bid portfolios prior to the strict 10:30~AM IST auction gate on day $D-1$ without forward market visibility. We present EnergyCast, an end-to-end causal multi-tier electricity price forecasting, exact game-theoretic explainability, and energy-neutral procurement optimization system evaluated across 28,176 hourly observations (2022--2025). The architecture harmonizes 15-minute IEX DAM auction records, Grid-India (POSOCO) national demand and renewable generation telemetry, and 5-zone demand-weighted ERA5 meteorological reanalysis into 53 leak-free causal features across five physical and econometric domains. We benchmark a three-tier modeling hierarchy spanning seasonal persistence baselines, Tikhonov $L_2$-regularized Ridge regression ($\alpha=50$), and histogram-based gradient-boosted decision trees (LightGBM and XGBoost) integrated with a statutory Central Electricity Regulatory Commission (CERC) boundary projection operator ($[\text{Rs.~0}, \text{Rs.~10,000}]/\text{MWh}$). On an unseen 4,200-hour chronological test split in 2025, our champion 282-tree LightGBM ensemble achieves an out-of-sample Mean Absolute Error (MAE) of Rs.~433.33/MWh (Rs.~0.43/kWh) and $R^2 = 0.9317$, reducing forecast error by 34.19\% over the 24-hour market persistence baseline (Rs.~658.42/MWh, Newey-West HAC Diebold-Mariano $DM = -7.780, p = 9.10 \times 10^{-15}$) and by 20.43\% over tuned Ridge regression (Rs.~544.61/MWh). Furthermore, exact TreeSHAP attribution decomposes every hourly forecast into exact rupee-per-MWh drivers, uncovering the national grid's non-linear 160~GW Peaker Scarcity Knee and powering an energy-neutral load-shifting optimizer that reduces daily DISCOM procurement costs by 11.9\% (Rs.~12.73~Lakhs/day on a 100~MW portfolio).
\end{abstract}

\begin{IEEEkeywords}
Day-ahead electricity market, Indian Energy Exchange (IEX), LightGBM, explainable AI (TreeSHAP), Diebold-Mariano HAC test, duck curve, merit-order supply stack, energy-neutral bid optimization.
\end{IEEEkeywords}
"""
    return header + get_core_body(is_ieee=True) + get_bibliography_items() + "\n\\end{document}\n"


def package_folder_to_zip(src_dir: pathlib.Path, zip_path: pathlib.Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fp in sorted(src_dir.rglob("*")):
            if fp.is_file():
                arcname = fp.relative_to(src_dir).as_posix()
                zf.write(fp, arcname)


def main():
    for folder in (SPRINGER_DIR, IEEE_DIR):
        if folder.exists():
            shutil.rmtree(folder)
        (folder / "images").mkdir(parents=True, exist_ok=True)
        for img_file in sorted(PAPER_FIG_DIR.glob("*.jpg")):
            shutil.copy2(img_file, folder / "images" / img_file.name)

    springer_tex = build_springer_tex()
    ieee_tex = build_ieee_tex()

    # Assert zero bold commands remain anywhere in either paper
    for name, content in [("Springer", springer_tex), ("IEEE", ieee_tex)]:
        assert "\\textbf" not in content, f"Found \\textbf in {name}"
        assert "\\mathbf" not in content, f"Found \\mathbf in {name}"
        assert "\\bfseries" not in content, f"Found \\bfseries in {name}"

    (SPRINGER_DIR / "main.tex").write_text(springer_tex, encoding="utf-8")
    (IEEE_DIR / "main.tex").write_text(ieee_tex, encoding="utf-8")

    springer_zip = SDP_ROOT / "EnergyCast_Springer_Paper.zip"
    ieee_zip = SDP_ROOT / "EnergyCast_IEEE_Paper.zip"
    combined_zip = SDP_ROOT / "EnergyCast_Research_Papers_IEEE_and_Springer.zip"

    package_folder_to_zip(SPRINGER_DIR, springer_zip)
    package_folder_to_zip(IEEE_DIR, ieee_zip)

    with zipfile.ZipFile(combined_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for fp in sorted(SPRINGER_DIR.rglob("*")):
            if fp.is_file():
                zf.write(fp, f"Springer_Paper/{fp.relative_to(SPRINGER_DIR).as_posix()}")
        for fp in sorted(IEEE_DIR.rglob("*")):
            if fp.is_file():
                zf.write(fp, f"IEEE_Paper/{fp.relative_to(IEEE_DIR).as_posix()}")
        zf.write(springer_zip, "EnergyCast_Springer_Paper.zip")
        zf.write(ieee_zip, "EnergyCast_IEEE_Paper.zip")

    print(f"[OK] Verified 0 bold commands (\\textbf, \\mathbf, \\bfseries) in both papers")
    print(f"[OK] Created Springer LNCS Paper -> {springer_zip} ({springer_zip.stat().st_size / 1024:.1f} KB)")
    print(f"[OK] Created IEEE Journal Paper  -> {ieee_zip} ({ieee_zip.stat().st_size / 1024:.1f} KB)")
    print(f"[OK] Created Combined ZIP Bundle -> {combined_zip} ({combined_zip.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
