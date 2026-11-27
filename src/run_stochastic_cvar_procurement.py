"""
EnergyCast V2 (TPWRS Revision) — Step 4: Multi-Profile Operational Constrained &
Stochastic CVaR-Aware Procurement Optimization Across All 175 Out-of-Sample Test Days.

Solves Reviewer Critical Weakness C & Priority 4 (Stochastic Procurement Optimization):
  Formulation (Rockafellar-Uryasev Exact Linear Program via HiGHS):
      min_{L_0..L_23, eta, u_s}  (1/S) sum_s sum_h L_h * P_h^(s)
                                 + lambda * [ eta + 1/((1-alpha)*S) * sum_s u_s ]
      s.t.
        1. Tail excess (CVaR):      u_s >= sum_h L_h * P_h^(s) - eta,   u_s >= 0   forall s=1..S
        2. Daily energy neutrality: sum_{h=0}^{23} L_h = sum_{h=0}^{23} L_h^0
        3. Flexibility bounds:      (1 - gamma) L_h^0 <= L_h <= (1 + gamma) L_h^0   forall h
        4. Inter-hour ramp limit:   |L_h - L_{h-1}| <= R_max * L_mean^0             forall h=1..23
                                    |L_0 - L_23|    <= R_max * L_mean^0 (cyclic boundary)
        5. Rolling energy recovery / process buffer constraint (bounded payback window):
                                    -B_max <= sum_{k=0}^{h} (L_k - L_k^0) <= +B_max  forall h
        6. Minimum operating duration & sustained shift smoothness (total variation cap):
                                    sum_{h=1}^{23} |L_h - L_{h-1} - (L_h^0 - L_{h-1}^0)| <= TV_max

  Evaluates ALL 175 unseen test days (Jan 1 - Jun 24, 2025) comparing:
    - 4 Realistic Industrial & Utility Load Profiles:
        (P1) Continuous Flat Industrial (Steel/Smelter, 100 MW flat, 2,400 MWh/day)
        (P2) Two-Shift Manufacturing Plant (Cement/Textile, 06:00-22:00 heavy, 100 MW mean)
        (P3) State DISCOM Feeder Portfolio (Real Indian diurnal shape, 350 MW mean)
        (P4) Cold-Storage / EV & Data Center Hybrid (80 MW mean, high midday flexibility)
    - 4 Flexible-Load Ratios: gamma in {10%, 20%, 30%, 40%}
    - 5 Scheduling Policies:
        (1) Unoptimized Baseline Schedule (L^0)
        (2) Rule-Based Time-of-Use Heuristic (fixed shift: shave 18-22h, boost 10-14h)
        (3) Conventional Deterministic LP (lambda = 0, point forecast only, unconstrained ramp vs constrained)
        (4) Proposed Stochastic CVaR-Constrained LP (lambda in {0.25, 0.5, 1.0, 2.0, 5.0}, alpha=0.90)
        (5) Ex-Post Perfect-Foresight Oracle LP (upper bound on achievable savings)
    - Explicitly distinguishes:
        * Ex-Ante Expected (Simulated) Savings (evaluated on forecasted prices)
        * Realized Out-of-Sample Operational Savings (evaluated on ACTUAL realized IEX MCP!)
        * Tail Financial Risk (Realized 95th-percentile Daily Bill & Realized CVaR_90 across 175 days)
        * Oracle Capture Efficiency (%) = Realized_Savings / Oracle_Savings * 100
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRED_DIR = PROJECT_ROOT / "outputs" / "predictions"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
CAUSAL_DIR = PROJECT_ROOT / "data" / "processed" / "causal_d1"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


def build_industrial_profiles(test_df: pd.DataFrame) -> dict[str, dict]:
    """Constructs 4 realistic industrial and utility hourly load shapes (MW)."""
    hours = np.arange(24)

    # Empirical Indian national diurnal shape normalized to mean 1.0
    test_df = test_df.copy()
    test_df["hour"] = pd.to_datetime(test_df["timestamp"]).dt.hour
    emp_shape = test_df.groupby("hour")["_actual_demand_mw"].mean().values
    emp_shape = emp_shape / np.mean(emp_shape)

    # P1: Continuous Flat Industrial (Steel / Aluminum Smelter, 100 MW flat)
    p1 = np.full(24, 100.0)

    # P2: Two-Shift Manufacturing (Cement / Textile / Auto, daytime heavy 06:00-22:00, mean = 100 MW)
    p2_raw = np.array([
        0.55, 0.52, 0.50, 0.50, 0.55, 0.65,
        0.95, 1.15, 1.25, 1.30, 1.32, 1.30,
        1.25, 1.28, 1.30, 1.28, 1.25, 1.20,
        1.15, 1.10, 1.05, 0.90, 0.70, 0.60,
    ])
    p2 = p2_raw / np.mean(p2_raw) * 100.0

    # P3: State DISCOM Utility Feeder Portfolio (Empirical Indian shape, 350 MW mean)
    p3 = emp_shape * 350.0

    # P4: Cold-Storage / Agricultural Pumping / Data Center Hybrid (80 MW mean)
    p4_raw = np.array([
        0.85, 0.82, 0.80, 0.80, 0.82, 0.88,
        0.95, 1.02, 1.08, 1.12, 1.15, 1.16,
        1.16, 1.15, 1.12, 1.10, 1.06, 1.04,
        1.05, 1.06, 1.04, 1.00, 0.94, 0.88,
    ])
    p4 = p4_raw / np.mean(p4_raw) * 80.0

    return {
        "P1_Flat_Industrial_100MW": {
            "label": "Continuous Industrial (100 MW Flat)",
            "base_mw": p1,
            "ramp_frac": 0.25,     # max 25% of mean MW ramp per hour
            "buffer_hours": 3.0,   # rolling cumulative shift energy recovery cap (<= 3h * gamma * mean_MW)
            "default_gamma": 0.30,
        },
        "P2_TwoShift_Mfg_100MW": {
            "label": "Two-Shift Manufacturing (100 MW Avg)",
            "base_mw": p2,
            "ramp_frac": 0.30,
            "buffer_hours": 3.0,
            "default_gamma": 0.25,
        },
        "P3_State_DISCOM_350MW": {
            "label": "State DISCOM Portfolio (350 MW Avg)",
            "base_mw": p3,
            "ramp_frac": 0.20,
            "buffer_hours": 2.5,
            "default_gamma": 0.20,
        },
        "P4_Hybrid_ColdDC_80MW": {
            "label": "Cold-Storage / Data Center (80 MW Avg)",
            "base_mw": p4,
            "ramp_frac": 0.35,
            "buffer_hours": 4.0,
            "default_gamma": 0.35,
        },
    }


def solve_procurement_lp(
    base_mw: np.ndarray,
    scenarios_24h: np.ndarray,
    gamma: float,
    lam: float = 0.0,
    alpha: float = 0.90,
    ramp_frac: float | None = 0.25,
    buffer_hours: float | None = 3.0,
    min_dwell_tv_factor: float | None = 6.0,
) -> np.ndarray:
    """
    Solves the exact Rockafellar-Uryasev Stochastic CVaR-Constrained Procurement LP:
        min  E[L^T P] + lam * CVaR_alpha(L^T P)
    subject to daily energy neutrality, flexibility bounds, inter-hour ramp constraints,
    rolling payback/recovery buffer constraints, and schedule smoothness (total variation).

    Parameters:
      base_mw:        shape (24,) baseline hourly load in MW
      scenarios_24h:  shape (S, 24) price scenarios in Rs./MWh (for deterministic LP, S=1 or mean)
      gamma:          shiftable load fraction (e.g. 0.30)
      lam:            CVaR risk-aversion weight (0.0 => pure expected-cost / deterministic LP)
      alpha:          CVaR confidence level (default 0.90)
      ramp_frac:      max hourly change in deviation |(L_h - L_h^0) - (L_{h-1} - L_{h-1}^0)| <= ramp_frac * mean(L^0)
      buffer_hours:   rolling energy recovery buffer |sum_{k=0}^h (L_k - L_k^0)| <= buffer_hours * gamma * mean(L^0)
      min_dwell_tv_factor: caps rapid chattering by bounding sum |d_h - d_{h-1}| <= min_dwell_tv_factor * gamma * mean(L^0)
    """
    H = 24
    mean_mw = float(np.mean(base_mw))
    P = np.atleast_2d(scenarios_24h)
    S = P.shape[0]
    mean_p = P.mean(axis=0)  # (24,)

    # Variables:
    #   x[0..23]       = L_h (hourly procurement in MW)
    #   x[24..47]      = r_h >= |(L_h - L_h^0) - (L_{h-1} - L_{h-1}^0)| (24 cyclic ramp slack vars)
    #   if lam > 0:
    #     x[48]        = eta (VaR threshold)
    #     x[49..49+S-1]= u_s >= 0 (CVaR tail excess per scenario)
    use_cvar = (lam > 1e-12) and (S > 1)
    n_L = H
    n_r = H
    n_vars = n_L + n_r + (1 + S if use_cvar else 0)

    c = np.zeros(n_vars, dtype=np.float64)
    c[:n_L] = mean_p
    # Tiny smoothness regularizer (0.01 Rs/MW) prevents degenerate chattering while preserving exact cost
    c[n_L : n_L + n_r] = 0.01
    if use_cvar:
        c[n_L + n_r] = lam
        c[n_L + n_r + 1 :] = lam / ((1.0 - alpha) * S)

    # Bounds
    bounds = []
    for h in range(H):
        bounds.append(((1.0 - gamma) * base_mw[h], (1.0 + gamma) * base_mw[h]))
    max_step = (ramp_frac * mean_mw) if ramp_frac is not None else None
    for h in range(H):
        bounds.append((0.0, max_step))
    if use_cvar:
        bounds.append((None, None))  # eta unrestricted
        for _ in range(S):
            bounds.append((0.0, None))  # u_s >= 0

    # Equality constraint: sum(L_h) = sum(base_mw)
    A_eq = np.zeros((1, n_vars), dtype=np.float64)
    A_eq[0, :n_L] = 1.0
    b_eq = np.array([float(np.sum(base_mw))], dtype=np.float64)

    # Inequality constraints A_ub @ x <= b_ub
    ub_rows = []
    ub_rhs = []

    # 1. Ramp deviation definition: -r_h <= (L_h - L_h^0) - (L_{h-1} - L_{h-1}^0) <= +r_h
    for h in range(H):
        hp = (h - 1) % H
        base_diff = base_mw[h] - base_mw[hp]
        # (L_h - L_hp) - r_h <= base_diff
        row1 = np.zeros(n_vars, dtype=np.float64)
        row1[h] = 1.0
        row1[hp] = -1.0
        row1[n_L + h] = -1.0
        ub_rows.append(row1)
        ub_rhs.append(base_diff)
        # -(L_h - L_hp) - r_h <= -base_diff
        row2 = np.zeros(n_vars, dtype=np.float64)
        row2[h] = -1.0
        row2[hp] = 1.0
        row2[n_L + h] = -1.0
        ub_rows.append(row2)
        ub_rhs.append(-base_diff)

    # 2. Minimum operating duration / anti-chattering Total Variation bound: sum(r_h) <= TV_max
    if min_dwell_tv_factor is not None:
        tv_max = min_dwell_tv_factor * gamma * mean_mw
        row_tv = np.zeros(n_vars, dtype=np.float64)
        row_tv[n_L : n_L + n_r] = 1.0
        ub_rows.append(row_tv)
        ub_rhs.append(tv_max)

    # 3. Rolling energy recovery / process buffer constraint:
    #    -B_max <= sum_{k=0}^h (L_k - L_k^0) <= +B_max
    if buffer_hours is not None:
        b_max = buffer_hours * gamma * mean_mw
        cum_base = np.cumsum(base_mw)
        for h in range(H - 1):
            row_hi = np.zeros(n_vars, dtype=np.float64)
            row_hi[: h + 1] = 1.0
            ub_rows.append(row_hi)
            ub_rhs.append(cum_base[h] + b_max)

            row_lo = np.zeros(n_vars, dtype=np.float64)
            row_lo[: h + 1] = -1.0
            ub_rows.append(row_lo)
            ub_rhs.append(-cum_base[h] + b_max)

    # 4. CVaR constraints: P_s^T L - eta - u_s <= 0
    if use_cvar:
        for s in range(S):
            row_c = np.zeros(n_vars, dtype=np.float64)
            row_c[:n_L] = P[s]
            row_c[n_L + n_r] = -1.0
            row_c[n_L + n_r + 1 + s] = -1.0
            ub_rows.append(row_c)
            ub_rhs.append(0.0)

    A_ub = np.vstack(ub_rows)
    b_ub = np.array(ub_rhs, dtype=np.float64)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        # Fallback to baseline if infeasible (should never happen since L = base_mw is always feasible)
        return base_mw.copy()
    return res.x[:n_L]


def rule_based_tou_schedule(base_mw: np.ndarray, gamma: float, ramp_frac: float = 0.25, buffer_hours: float = 3.0) -> np.ndarray:
    """
    Conventional fixed Time-of-Use (ToU) rule-based heuristic (no AI price forecast):
    Always shaves evening peak window (18:00-22:00, 5h) and shifts energy into fixed
    midday solar window (10:00-14:00, 5h), solved with identical physical ramp/buffer
    constraints using a synthetic fixed ToU tariff proxy (High=3 at 18-22h, Low=1 at 10-14h, Mid=2 elsewhere).
    """
    synthetic_tou = np.full(24, 2000.0)
    synthetic_tou[10:15] = 1000.0
    synthetic_tou[18:23] = 3000.0
    return solve_procurement_lp(
        base_mw, synthetic_tou.reshape(1, 24), gamma=gamma, lam=0.0,
        ramp_frac=ramp_frac, buffer_hours=buffer_hours
    )


def calc_cvar(values: np.ndarray, alpha: float = 0.90) -> float:
    q = float(np.quantile(values, alpha))
    tail = values[values >= q]
    return float(np.mean(tail)) if len(tail) > 0 else q


def evaluate_policy_across_days(
    base_mw: np.ndarray,
    actual_24h: np.ndarray,
    point_24h: np.ndarray,
    scenarios_all: np.ndarray,
    gamma: float,
    policy: str,
    lam: float = 0.0,
    ramp_frac: float | None = 0.25,
    buffer_hours: float | None = 3.0,
) -> dict:
    """Evaluates a scheduling policy across all D=175 out-of-sample test days."""
    n_days = actual_24h.shape[0]
    base_realized = np.zeros(n_days)
    opt_realized = np.zeros(n_days)
    base_expected = np.zeros(n_days)
    opt_expected = np.zeros(n_days)
    ex_ante_cvar90 = np.zeros(n_days)
    schedules = np.zeros((n_days, 24))

    for d in range(n_days):
        p_act = actual_24h[d]
        p_pt = point_24h[d]
        sc = scenarios_all[d]

        if policy == "baseline":
            L = base_mw.copy()
        elif policy == "rule_tou":
            L = rule_based_tou_schedule(base_mw, gamma, ramp_frac=ramp_frac or 0.25, buffer_hours=buffer_hours or 3.0)
        elif policy == "det_unconstrained":
            L = solve_procurement_lp(base_mw, p_pt.reshape(1, 24), gamma=gamma, lam=0.0, ramp_frac=None, buffer_hours=None, min_dwell_tv_factor=None)
        elif policy == "det_constrained":
            L = solve_procurement_lp(base_mw, p_pt.reshape(1, 24), gamma=gamma, lam=0.0, ramp_frac=ramp_frac, buffer_hours=buffer_hours)
        elif policy == "stoch_cvar":
            L = solve_procurement_lp(base_mw, sc, gamma=gamma, lam=lam, alpha=0.90, ramp_frac=ramp_frac, buffer_hours=buffer_hours)
        elif policy == "oracle_constrained":
            L = solve_procurement_lp(base_mw, p_act.reshape(1, 24), gamma=gamma, lam=0.0, ramp_frac=ramp_frac, buffer_hours=buffer_hours)
        else:
            raise ValueError(policy)

        schedules[d] = L
        base_realized[d] = float(base_mw @ p_act)
        opt_realized[d] = float(L @ p_act)
        base_expected[d] = float(base_mw @ p_pt)
        opt_expected[d] = float(L @ p_pt)
        scen_costs = sc @ L
        ex_ante_cvar90[d] = calc_cvar(scen_costs, 0.90)

    realized_save_rs = base_realized - opt_realized
    expected_save_rs = base_expected - opt_expected
    realized_pct = float(np.sum(realized_save_rs) / np.sum(base_realized) * 100.0)
    expected_pct = float(np.sum(expected_save_rs) / np.sum(base_expected) * 100.0)
    # Count days where schedule saved money on REALIZED prices
    win_rate = float(np.mean(realized_save_rs > 0) * 100.0)
    # Worst-case tail risk across all 175 test days (Realized 90% CVaR of Daily Bill)
    realized_cvar90_bill = calc_cvar(opt_realized, 0.90)
    base_cvar90_bill = calc_cvar(base_realized, 0.90)
    # Realized 90% CVaR of Regret / Worst-5% Daily Savings
    worst5_save_rs = float(np.quantile(realized_save_rs, 0.05))
    # Peak-day realized savings (top 20% highest-spread days)
    daily_spread = actual_24h.max(axis=1) - actual_24h.min(axis=1)
    top20_mask = daily_spread >= np.quantile(daily_spread, 0.80)
    top20_save_pct = float(np.sum(realized_save_rs[top20_mask]) / np.sum(base_realized[top20_mask]) * 100.0)

    return {
        "policy": policy,
        "lambda": lam,
        "gamma_pct": int(round(gamma * 100)),
        "base_mean_bill_lakhs": round(float(np.mean(base_realized)) / 1e5, 3),
        "opt_mean_bill_lakhs": round(float(np.mean(opt_realized)) / 1e5, 3),
        "expected_sim_save_lakhs_day": round(float(np.mean(expected_save_rs)) / 1e5, 3),
        "expected_sim_save_pct": round(expected_pct, 2),
        "realized_save_lakhs_day": round(float(np.mean(realized_save_rs)) / 1e5, 3),
        "realized_save_pct": round(realized_pct, 2),
        "realized_annual_save_cr": round(float(np.mean(realized_save_rs)) * 365.0 / 1e7, 2),
        "top20_scarcity_save_pct": round(top20_save_pct, 2),
        "positive_saving_days_pct": round(win_rate, 1),
        "ex_ante_cvar90_lakhs": round(float(np.mean(ex_ante_cvar90)) / 1e5, 3),
        "realized_cvar90_bill_lakhs": round(realized_cvar90_bill / 1e5, 3),
        "cvar90_bill_reduction_lakhs": round((base_cvar90_bill - realized_cvar90_bill) / 1e5, 3),
        "worst5pct_daily_save_lakhs": round(worst5_save_rs / 1e5, 3),
        "daily_realized_bills": opt_realized,
        "daily_realized_saves": realized_save_rs,
        "schedules": schedules,
    }


def main() -> None:
    t0 = time.perf_counter()
    print("=" * 82)
    print("ENERGYCAST V2 — STOCHASTIC CVaR-CONSTRAINED MULTI-PROFILE PROCUREMENT OPTIMIZER")
    print("=" * 82)

    npz = np.load(PRED_DIR / "v2_test_price_scenarios.npz", allow_pickle=True)
    dates = npz["dates"]
    scenarios_all = npz["scenarios"]   # (175, 200, 24)
    actual_24h = npz["actual_24h"]     # (175, 24)
    point_24h = npz["point_24h"]       # (175, 24)
    n_days = len(dates)
    print(f"Loaded {n_days} unseen test days ({dates[0]} -> {dates[-1]}) x {scenarios_all.shape[1]} scenarios x 24h")

    test_df = pd.read_csv(CAUSAL_DIR / "operational_test.csv")
    profiles = build_industrial_profiles(test_df)

    # -------------------------------------------------------------------------
    # C1: POLICY COMPARISON ACROSS ALL 4 PROFILES (175-DAY OUT-OF-SAMPLE)
    # -------------------------------------------------------------------------
    print("\n[C1] Multi-Profile Out-of-Sample Policy Benchmark (All 175 Test Days, Jan-Jun 2025):")
    c1_rows = []
    for pid, pinfo in profiles.items():
        gamma = pinfo["default_gamma"]
        base_mw = pinfo["base_mw"]
        rf = pinfo["ramp_frac"]
        bh = pinfo["buffer_hours"]

        oracle = evaluate_policy_across_days(base_mw, actual_24h, point_24h, scenarios_all, gamma, "oracle_constrained", 0.0, rf, bh)
        oracle_save = max(oracle["realized_save_lakhs_day"], 1e-6)

        policies_to_run = [
            ("Rule-Based ToU Heuristic", "rule_tou", 0.0, rf, bh),
            ("Deterministic LP (Unconstrained)", "det_unconstrained", 0.0, None, None),
            ("Deterministic LP (Constrained)", "det_constrained", 0.0, rf, bh),
            ("Stochastic CVaR LP (lam=0.5)", "stoch_cvar", 0.5, rf, bh),
            ("Stochastic CVaR LP (lam=2.0)", "stoch_cvar", 2.0, rf, bh),
            ("Ex-Post Perfect Oracle (Constrained)", "oracle_constrained", 0.0, rf, bh),
        ]
        print(f"\n  Profile: {pinfo['label']} (gamma={int(gamma*100)}%, ramp<={int(rf*100)}%/h, buf={bh}h)")
        for pname, pcode, lam, r_use, b_use in policies_to_run:
            r = evaluate_policy_across_days(base_mw, actual_24h, point_24h, scenarios_all, gamma, pcode, lam, r_use, b_use)
            capture_eff = round(r["realized_save_lakhs_day"] / oracle_save * 100.0, 1)
            row = {
                "Profile_ID": pid,
                "Profile_Label": pinfo["label"],
                "Gamma_pct": int(gamma * 100),
                "Policy": pname,
                "Lambda": lam,
                "Base_Bill_Lakhs": r["base_mean_bill_lakhs"],
                "Sim_Expected_Save_Lakhs": r["expected_sim_save_lakhs_day"],
                "Sim_Expected_Save_pct": r["expected_sim_save_pct"],
                "Realized_Save_Lakhs": r["realized_save_lakhs_day"],
                "Realized_Save_pct": r["realized_save_pct"],
                "Top20_Scarcity_Save_pct": r["top20_scarcity_save_pct"],
                "Annual_Realized_Cr": r["realized_annual_save_cr"],
                "Oracle_Capture_pct": capture_eff,
                "Win_Days_pct": r["positive_saving_days_pct"],
                "ExAnte_CVaR90_Lakhs": r["ex_ante_cvar90_lakhs"],
                "Realized_CVaR90_Bill_Lakhs": r["realized_cvar90_bill_lakhs"],
                "CVaR90_Reduction_Lakhs": r["cvar90_bill_reduction_lakhs"],
                "Worst5pct_Save_Lakhs": r["worst5pct_daily_save_lakhs"],
            }
            c1_rows.append(row)
            print(
                f"    {pname:36s} | Sim={r['expected_sim_save_pct']:5.2f}% | "
                f"Realized={r['realized_save_pct']:5.2f}% (Rs.{r['realized_save_lakhs_day']:5.2f}L/d, "
                f"Rs.{r['realized_annual_save_cr']:5.2f}Cr/yr) | CapEff={capture_eff:5.1f}% | "
                f"CVaR90_Bill=Rs.{r['realized_cvar90_bill_lakhs']:6.2f}L | Win={r['positive_saving_days_pct']:5.1f}%"
            )

    pd.DataFrame(c1_rows).to_csv(TABLE_DIR / "v2_procurement_multi_profile_results.csv", index=False)

    # -------------------------------------------------------------------------
    # C2: FLEXIBLE LOAD SENSITIVITY SWEEP (gamma in {10%, 20%, 30%, 40%})
    # -------------------------------------------------------------------------
    print("\n[C2] Flexibility Ratio Sensitivity Sweep (10%, 20%, 30%, 40%) on P1 (100 MW Flat) & P3 (350 MW DISCOM):")
    c2_rows = []
    for pid in ["P1_Flat_Industrial_100MW", "P3_State_DISCOM_350MW"]:
        pinfo = profiles[pid]
        for gamma in [0.10, 0.20, 0.30, 0.40]:
            for pname, pcode, lam in [
                ("Rule-Based ToU", "rule_tou", 0.0),
                ("Det. Constrained LP", "det_constrained", 0.0),
                ("Stoch. CVaR LP (lam=1.0)", "stoch_cvar", 1.0),
                ("Oracle Constrained", "oracle_constrained", 0.0),
            ]:
                r = evaluate_policy_across_days(
                    pinfo["base_mw"], actual_24h, point_24h, scenarios_all,
                    gamma, pcode, lam, pinfo["ramp_frac"], pinfo["buffer_hours"]
                )
                c2_rows.append({
                    "Profile": pinfo["label"],
                    "Gamma_pct": int(gamma * 100),
                    "Policy": pname,
                    "Sim_Save_pct": r["expected_sim_save_pct"],
                    "Realized_Save_pct": r["realized_save_pct"],
                    "Realized_Save_Lakhs_Day": r["realized_save_lakhs_day"],
                    "Annual_Realized_Cr": r["realized_annual_save_cr"],
                    "Realized_CVaR90_Bill_Lakhs": r["realized_cvar90_bill_lakhs"],
                    "Win_Days_pct": r["positive_saving_days_pct"],
                })
                if pid == "P1_Flat_Industrial_100MW":
                    print(
                        f"  P1 gamma={int(gamma*100):2d}% | {pname:24s} | Sim={r['expected_sim_save_pct']:5.2f}% | "
                        f"Realized={r['realized_save_pct']:5.2f}% (Rs.{r['realized_save_lakhs_day']:5.2f}L/d) | "
                        f"CVaR90=Rs.{r['realized_cvar90_bill_lakhs']:6.2f}L"
                    )
    pd.DataFrame(c2_rows).to_csv(TABLE_DIR / "v2_procurement_flexibility_sensitivity.csv", index=False)

    # -------------------------------------------------------------------------
    # C3: RISK-AVERSION FRONTIER (lambda sweep: 0.0 -> 5.0)
    # -------------------------------------------------------------------------
    print("\n[C3] Stochastic Risk-Aversion Pareto Frontier (lambda sweep on P1 100 MW, gamma=30%):")
    p1_info = profiles["P1_Flat_Industrial_100MW"]
    c3_rows = []
    for lam in [0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0]:
        pcode = "det_constrained" if lam == 0.0 else "stoch_cvar"
        r = evaluate_policy_across_days(
            p1_info["base_mw"], actual_24h, point_24h, scenarios_all,
            0.30, pcode, lam, p1_info["ramp_frac"], p1_info["buffer_hours"]
        )
        c3_rows.append({
            "Lambda": lam,
            "Realized_Mean_Bill_Lakhs": r["opt_mean_bill_lakhs"],
            "Realized_Save_Lakhs_Day": r["realized_save_lakhs_day"],
            "Realized_Save_pct": r["realized_save_pct"],
            "ExAnte_CVaR90_Lakhs": r["ex_ante_cvar90_lakhs"],
            "Realized_CVaR90_Bill_Lakhs": r["realized_cvar90_bill_lakhs"],
            "CVaR90_Reduction_Lakhs": r["cvar90_bill_reduction_lakhs"],
            "Worst5pct_Save_Lakhs": r["worst5pct_daily_save_lakhs"],
            "Win_Days_pct": r["positive_saving_days_pct"],
        })
        print(
            f"  lambda={lam:4.2f} | MeanBill=Rs.{r['opt_mean_bill_lakhs']:6.3f}L | "
            f"RealizedSave={r['realized_save_pct']:5.2f}% | ExAnte_CVaR90=Rs.{r['ex_ante_cvar90_lakhs']:6.3f}L | "
            f"Realized_CVaR90=Rs.{r['realized_cvar90_bill_lakhs']:6.3f}L | Worst5%Save=Rs.{r['worst5pct_daily_save_lakhs']:+.3f}L"
        )
    pd.DataFrame(c3_rows).to_csv(TABLE_DIR / "v2_procurement_cvar_frontier.csv", index=False)

    # -------------------------------------------------------------------------
    # C4: SEASONAL BREAKDOWN OF REALIZED SAVINGS (WINTER vs SPRING vs SUMMER)
    # -------------------------------------------------------------------------
    print("\n[C4] Seasonal Breakdown of Realized Procurement Savings (P1 100 MW, gamma=30%):")
    dt_idx = pd.to_datetime(dates)
    r_det = evaluate_policy_across_days(p1_info["base_mw"], actual_24h, point_24h, scenarios_all, 0.30, "det_constrained", 0.0, p1_info["ramp_frac"], p1_info["buffer_hours"])
    r_cvar = evaluate_policy_across_days(p1_info["base_mw"], actual_24h, point_24h, scenarios_all, 0.30, "stoch_cvar", 1.0, p1_info["ramp_frac"], p1_info["buffer_hours"])
    r_tou = evaluate_policy_across_days(p1_info["base_mw"], actual_24h, point_24h, scenarios_all, 0.30, "rule_tou", 0.0, p1_info["ramp_frac"], p1_info["buffer_hours"])
    r_ora = evaluate_policy_across_days(p1_info["base_mw"], actual_24h, point_24h, scenarios_all, 0.30, "oracle_constrained", 0.0, p1_info["ramp_frac"], p1_info["buffer_hours"])
    base_bills = np.array([float(p1_info["base_mw"] @ actual_24h[d]) for d in range(n_days)])

    c4_rows = []
    for s_name, months in [
        ("Winter (Jan-Feb 2025)", [1, 2]),
        ("Spring Transition (Mar-Apr 2025)", [3, 4]),
        ("Summer & Early Monsoon (May-Jun 2025)", [5, 6]),
        ("Full Test Horizon (Jan-Jun 2025)", [1, 2, 3, 4, 5, 6]),
    ]:
        mk = dt_idx.month.isin(months)
        b_tot = float(np.sum(base_bills[mk]))
        row = {
            "Season": s_name,
            "Days": int(mk.sum()),
            "Mean_Actual_MCP_Rs": round(float(np.mean(actual_24h[mk])), 2),
            "Mean_Daily_Spread_Rs": round(float(np.mean(actual_24h[mk].max(axis=1) - actual_24h[mk].min(axis=1))), 2),
            "Rule_ToU_Save_pct": round(float(np.sum(r_tou["daily_realized_saves"][mk]) / b_tot * 100.0), 2),
            "Det_LP_Save_pct": round(float(np.sum(r_det["daily_realized_saves"][mk]) / b_tot * 100.0), 2),
            "Stoch_CVaR_Save_pct": round(float(np.sum(r_cvar["daily_realized_saves"][mk]) / b_tot * 100.0), 2),
            "Stoch_CVaR_Save_Lakhs_Day": round(float(np.mean(r_cvar["daily_realized_saves"][mk])) / 1e5, 3),
            "Oracle_Save_pct": round(float(np.sum(r_ora["daily_realized_saves"][mk]) / b_tot * 100.0), 2),
            "Stoch_CVaR_Win_Days_pct": round(float(np.mean(r_cvar["daily_realized_saves"][mk] > 0) * 100.0), 1),
        }
        c4_rows.append(row)
        print(
            f"  {s_name:38s} (d={row['Days']:3d}) | ToU={row['Rule_ToU_Save_pct']:4.2f}% | "
            f"DetLP={row['Det_LP_Save_pct']:4.2f}% | StochCVaR={row['Stoch_CVaR_Save_pct']:4.2f}% "
            f"(Rs.{row['Stoch_CVaR_Save_Lakhs_Day']:5.2f}L/d) | Oracle={row['Oracle_Save_pct']:4.2f}% | Win={row['Stoch_CVaR_Win_Days_pct']:5.1f}%"
        )
    pd.DataFrame(c4_rows).to_csv(TABLE_DIR / "v2_procurement_seasonal_breakdown.csv", index=False)

    # Save representative day schedule for plotting (e.g., 2025-01-01 + highest-spread day)
    np.savez_compressed(
        PRED_DIR / "v2_procurement_schedules.npz",
        dates=dates,
        base_p1=p1_info["base_mw"],
        sched_tou=r_tou["schedules"],
        sched_det=r_det["schedules"],
        sched_cvar=r_cvar["schedules"],
        sched_oracle=r_ora["schedules"],
        daily_saves_tou=r_tou["daily_realized_saves"],
        daily_saves_det=r_det["daily_realized_saves"],
        daily_saves_cvar=r_cvar["daily_realized_saves"],
        daily_saves_oracle=r_ora["daily_realized_saves"],
        base_bills=base_bills,
    )

    print(f"\n[OK] Stochastic CVaR procurement optimization completed in {time.perf_counter() - t0:.1f}s!")


if __name__ == "__main__":
    main()
