"""
EnergyCast V2 (TPWRS Revision) — Step 3 (Upgraded):
Causality-Aware Multi-Tier Deterministic Benchmarking (13 Models across 4 Tiers),
Capacity-Relative Non-Stationary Adaptation, Innovation-Target Expanding Recalibration,
PyTorch N-BEATS & Temporal Fusion Transformer (TFT), Residual-Centered Conformalized
Quantile Regression (Residual-CQR), Correlated Gaussian Copula Scenario Engine,
Strict Causality Ablation, Seasonal Robustness & Exact Operational TreeSHAP.
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import xgboost as xgb
from catboost import CatBoostRegressor
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAUSAL_DIR = PROJECT_ROOT / "data" / "processed" / "causal_d1"
MODELS_V2_DIR = PROJECT_ROOT / "models" / "v2_causal"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
PRED_DIR = PROJECT_ROOT / "outputs" / "predictions"
MODELS_V2_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
PRED_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.set_num_threads(6)

QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


# ==============================================================================
# CAPACITY-RELATIVE NON-STATIONARITY AUGMENTATION (100% STRICTLY CAUSAL)
# ==============================================================================
def add_capacity_relative_features(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Directly motivated by our physical merit-order finding that India's scarcity knee
    migrates upward from 152 GW (2022) -> 174 GW (2025) alongside thermal fleet expansion.
    Constructs 3 strictly causal trailing-30-day capacity-normalized features using ONLY
    prior-day D-1/D-2 published observations:
      - nd_fcst_rel_30d:   Forecasted Net Demand minus trailing 30-day realized Net Demand mean
      - nd_fcst_zscore_30d: Standardized net demand anomaly vs. current 30-day operating regime
      - mcp_d1_rel_30d:    Yesterday's same-hour MCP minus trailing 30-day MCP mean
    """
    df = df_all.copy()
    roll_nd_mean = df["net_demand_d2_same_h"].rolling(window=30 * 24, min_periods=7 * 24).mean().bfill()
    roll_nd_std = df["net_demand_d2_same_h"].rolling(window=30 * 24, min_periods=7 * 24).std().bfill().clip(lower=1000.0)
    roll_mcp_mean = df["mcp_d1_same_h"].rolling(window=30 * 24, min_periods=7 * 24).mean().bfill()

    df["nd_fcst_rel_30d"] = df["net_demand_fcst_mw"] - roll_nd_mean
    df["nd_fcst_zscore_30d"] = df["nd_fcst_rel_30d"] / roll_nd_std
    df["mcp_d1_rel_30d"] = df["mcp_d1_same_h"] - roll_mcp_mean
    return df


def make_recency_weights(timestamps: pd.Series, half_life_days: float = 240.0) -> np.ndarray:
    """Exponential recency weights giving higher emphasis to post-Apr-2023 uniform Rs.10k cap regime."""
    ts = pd.to_datetime(timestamps)
    age_days = (ts.max() - ts).dt.total_seconds().values / 86400.0
    w = np.exp(-np.log(2.0) * age_days / half_life_days)
    # Downweight pre-Apr-4-2023 Rs.12,000 cap era slightly to reduce ceiling-shift bias
    pre_cap = (ts < pd.Timestamp("2023-04-04 00:00:00")).values
    w = np.where(pre_cap, w * 0.55, w)
    return w / np.mean(w)


# ==============================================================================
# METRICS & NEWEY-WEST HAC DIEBOLD-MARIANO TEST
# ==============================================================================
def cerc_clip(y: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(y, dtype=np.float64), 0.0, 10000.0)


def compute_point_metrics(y_true: np.ndarray, y_pred: np.ndarray, hours: np.ndarray) -> dict[str, float]:
    yt = np.asarray(y_true, dtype=np.float64)
    yp = cerc_clip(y_pred)
    err = yt - yp
    abs_err = np.abs(err)
    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    smape = float(np.mean(200.0 * abs_err / (np.abs(yt) + np.abs(yp) + 1e-6)))
    r2 = float(1.0 - np.sum(err ** 2) / np.sum((yt - np.mean(yt)) ** 2))
    peak_mask = np.isin(hours, [18, 19, 20, 21, 22])
    solar_mask = (hours >= 9) & (hours <= 16)
    spike_mask = yt >= 8000.0
    return {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "sMAPE": round(smape, 2),
        "R2": round(r2, 4),
        "Peak_MAE": round(float(np.mean(abs_err[peak_mask])), 2),
        "Solar_MAE": round(float(np.mean(abs_err[solar_mask])), 2),
        "Spike_MAE": round(float(np.mean(abs_err[spike_mask])), 2) if spike_mask.any() else np.nan,
        "Mean_Bias": round(float(np.mean(yp - yt)), 2),
    }


def diebold_mariano_hac(y_true: np.ndarray, pred_1: np.ndarray, pred_2: np.ndarray, loss: str = "abs") -> tuple[float, float]:
    e1 = y_true - cerc_clip(pred_1)
    e2 = y_true - cerc_clip(pred_2)
    d = (np.abs(e1) - np.abs(e2)) if loss == "abs" else (e1 ** 2 - e2 ** 2)
    n = len(d)
    d_bar = float(np.mean(d))
    dm = d - d_bar
    L = int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    gamma0 = float(np.dot(dm, dm) / n)
    var_hac = gamma0
    for k in range(1, L + 1):
        w = 1.0 - k / (L + 1.0)
        gk = float(np.dot(dm[k:], dm[:-k]) / n)
        var_hac += 2.0 * w * gk
    var_hac = max(var_hac, 1e-12)
    dm_stat = d_bar / np.sqrt(var_hac / n)
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(dm_stat))))
    return round(float(dm_stat), 3), p_val


# ==============================================================================
# TIER 2: 24-EQUATION HOURLY SARIMAX (EXPANDING KALMAN FILTER)
# ==============================================================================
def run_24h_sarimax(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    exog_cols = [
        "nd_fcst_rel_30d", "net_demand_fcst_ramp_1", "solar_fcst_mw",
        "wind_fcst_mw", "market_tightness_d1", "temp_mean_fcst_c",
        "cdd_24_fcst", "is_weekend", "is_holiday_india",
    ]
    n_va, n_te = len(val_df), len(test_df)
    val_pred = np.zeros(n_va, dtype=np.float64)
    test_pred = np.zeros(n_te, dtype=np.float64)

    tr_hrs = pd.to_datetime(train_df["timestamp"]).dt.hour.values
    va_hrs = pd.to_datetime(val_df["timestamp"]).dt.hour.values
    te_hrs = pd.to_datetime(test_df["timestamp"]).dt.hour.values

    for h in range(24):
        tr_h = train_df[tr_hrs == h]
        va_h = val_df[va_hrs == h]
        te_h = test_df[te_hrs == h]

        sc_ex = StandardScaler()
        ex_tr = sc_ex.fit_transform(tr_h[exog_cols].values)
        ex_va = sc_ex.transform(va_h[exog_cols].values)

        y_tr = tr_h["mcp_rs_per_mwh"].values
        y_va = va_h["mcp_rs_per_mwh"].values
        y_te = te_h["mcp_rs_per_mwh"].values

        # Fit on Train -> predict Val via causal 1-step Kalman filter
        try:
            mod_v = SARIMAX(y_tr, exog=ex_tr, order=(2, 0, 0), seasonal_order=(1, 0, 0, 7),
                            trend="c", enforce_stationarity=False, enforce_invertibility=False)
            res_v = mod_v.fit(disp=False, maxiter=80)
            res_va_all = res_v.apply(np.concatenate([y_tr, y_va]), exog=np.vstack([ex_tr, ex_va]), refit=False)
            p_va_h = res_va_all.fittedvalues[len(y_tr):]

            # Expanding refit on Train + Val (2022-2024) -> predict Test (2025) via causal 1-step Kalman filter
            sc_ex2 = StandardScaler()
            ex_trva = sc_ex2.fit_transform(np.vstack([tr_h[exog_cols].values, va_h[exog_cols].values]))
            ex_te = sc_ex2.transform(te_h[exog_cols].values)
            y_trva = np.concatenate([y_tr, y_va])
            mod_t = SARIMAX(y_trva, exog=ex_trva, order=(2, 0, 0), seasonal_order=(1, 0, 0, 7),
                            trend="c", enforce_stationarity=False, enforce_invertibility=False)
            res_t = mod_t.fit(disp=False, maxiter=80)
            res_te_all = res_t.apply(np.concatenate([y_trva, y_te]), exog=np.vstack([ex_trva, ex_te]), refit=False)
            p_te_h = res_te_all.fittedvalues[len(y_trva):]
        except Exception:
            lr = Ridge(alpha=20.0)
            lr.fit(np.column_stack([tr_h["mcp_d1_same_h"].values, tr_h["mcp_d7_same_h"].values, ex_tr]), y_tr)
            p_va_h = lr.predict(np.column_stack([va_h["mcp_d1_same_h"].values, va_h["mcp_d7_same_h"].values, ex_va]))
            ex_te = sc_ex.transform(te_h[exog_cols].values)
            p_te_h = lr.predict(np.column_stack([te_h["mcp_d1_same_h"].values, te_h["mcp_d7_same_h"].values, ex_te]))

        val_pred[va_hrs == h] = cerc_clip(p_va_h)
        test_pred[te_hrs == h] = cerc_clip(p_te_h)

    return val_pred, test_pred


# ==============================================================================
# TIER 4: PYTORCH N-BEATS & TEMPORAL FUSION TRANSFORMER (INNOVATION-TARGET)
# ==============================================================================
class NBeatsBlock(nn.Module):
    def __init__(self, in_dim: int, theta_dim: int, horizon: int, hidden_dim: int = 224, basis_type: str = "generic"):
        super().__init__()
        self.basis_type = basis_type
        self.fc = nn.Sequential(
            nn.Linear(in_dim, hidden_dim), nn.SiLU(), nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim), nn.SiLU(), nn.Dropout(0.15),
            nn.Linear(hidden_dim, hidden_dim), nn.SiLU(),
        )
        self.theta_b = nn.Linear(hidden_dim, theta_dim, bias=False)
        self.theta_f = nn.Linear(hidden_dim, theta_dim, bias=False)
        self.backcast_proj = nn.Linear(theta_dim, in_dim)
        if basis_type == "generic":
            self.forecast_proj = nn.Linear(theta_dim, horizon)
        elif basis_type == "seasonal":
            t = torch.arange(horizon, dtype=torch.float32) / float(horizon)
            k = torch.arange(1, theta_dim // 2 + 1, dtype=torch.float32).unsqueeze(1)
            self.register_buffer("F_basis", torch.cat([torch.cos(2 * np.pi * k * t.unsqueeze(0)), torch.sin(2 * np.pi * k * t.unsqueeze(0))], dim=0))
        elif basis_type == "trend":
            t = torch.linspace(-1.0, 1.0, horizon)
            self.register_buffer("T_basis", torch.stack([t ** p for p in range(theta_dim)], dim=0))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.fc(x)
        backcast = self.backcast_proj(self.theta_b(h))
        tf = self.theta_f(h)
        if self.basis_type == "generic":
            forecast = self.forecast_proj(tf)
        elif self.basis_type == "seasonal":
            forecast = tf @ self.F_basis
        else:
            forecast = tf @ self.T_basis
        return backcast, forecast


class NBeatsInnovationNet(nn.Module):
    """Multi-Stack N-BEATSx predicting 24h day-ahead price innovations delta_P = P_{D,h} - P_{D-1,h}."""
    def __init__(self, in_dim: int, horizon: int = 24, hidden_dim: int = 224):
        super().__init__()
        self.blocks = nn.ModuleList([
            NBeatsBlock(in_dim, 4, horizon, hidden_dim, "trend"),
            NBeatsBlock(in_dim, 4, horizon, hidden_dim, "trend"),
            NBeatsBlock(in_dim, 12, horizon, hidden_dim, "seasonal"),
            NBeatsBlock(in_dim, 12, horizon, hidden_dim, "seasonal"),
            NBeatsBlock(in_dim, 48, horizon, hidden_dim, "generic"),
            NBeatsBlock(in_dim, 48, horizon, hidden_dim, "generic"),
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = x
        fcst = torch.zeros((x.shape[0], 24), device=x.device, dtype=x.dtype)
        for blk in self.blocks:
            b, f = blk(res)
            res = res - b
            fcst = fcst + f
        return fcst


class GatedResidualNetwork(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int, out_dim: int, dropout: float = 0.15):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_dim, out_dim * 2)
        self.drop = nn.Dropout(dropout)
        self.skip = nn.Linear(in_dim, out_dim) if in_dim != out_dim else nn.Identity()
        self.norm = nn.LayerNorm(out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.drop(self.elu(self.fc1(x)))
        a, b = self.fc2(h).chunk(2, dim=-1)
        return self.norm(self.skip(x) + a * torch.sigmoid(b))


class TemporalFusionTransformerInnovation(nn.Module):
    """
    TFT with Variable Selection Gate, Bi-LSTM 24h sequence encoder, 4-Head Self-Attention,
    and Multi-Quantile Output Head predicting residual innovations relative to P_{D-1,h}.
    """
    def __init__(self, n_features: int, d_model: int = 96, n_heads: int = 4, n_quantiles: int = 7, dropout: float = 0.15):
        super().__init__()
        self.vsn_gate = nn.Sequential(nn.Linear(n_features, n_features), nn.Sigmoid())
        self.input_grn = GatedResidualNetwork(n_features, d_model, d_model, dropout)
        self.lstm = nn.LSTM(d_model, d_model // 2, num_layers=2, batch_first=True, bidirectional=True, dropout=dropout)
        self.lstm_norm = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.attn_norm = nn.LayerNorm(d_model)
        self.post_grn = GatedResidualNetwork(d_model, d_model, d_model, dropout)
        self.q_head = nn.Linear(d_model, n_quantiles)

    def forward(self, x_seq: torch.Tensor) -> torch.Tensor:
        h = self.input_grn(x_seq * self.vsn_gate(x_seq))
        lo, _ = self.lstm(h)
        h = self.lstm_norm(h + lo)
        ao, _ = self.attn(h, h, h)
        h = self.attn_norm(h + ao)
        return self.q_head(self.post_grn(h))


def pinball_loss_torch(y_pred_q: torch.Tensor, y_true: torch.Tensor, quantiles: list[float], sample_w: torch.Tensor | None = None) -> torch.Tensor:
    q = torch.tensor(quantiles, device=y_pred_q.device, dtype=y_pred_q.dtype).view(1, 1, -1)
    diff = y_true.unsqueeze(-1) - y_pred_q
    pb = torch.maximum(q * diff, (q - 1.0) * diff).mean(dim=(1, 2))  # (B,)
    if sample_w is not None:
        return torch.mean(pb * sample_w)
    return torch.mean(pb)


def reshape_daily(X_sc: np.ndarray, y: np.ndarray, anchor: np.ndarray):
    nd = len(y) // 24
    return (
        X_sc[: nd * 24].reshape(nd, 24, -1),
        y[: nd * 24].reshape(nd, 24),
        anchor[: nd * 24].reshape(nd, 24),
    )


def fit_predict_nbeats_expanding(
    X_tr_sc, y_tr, anc_tr, w_tr,
    X_va_sc, y_va, anc_va, w_va,
    X_te_sc, y_te, anc_te,
    epochs: int = 70,
) -> tuple[np.ndarray, np.ndarray]:
    key_idx = [0, 3, 18, 21, 25, 26, 27, 28, 30, 42, 48, 62, 63]
    def make_flat(X3):
        return np.hstack([X3[:, :, key_idx].reshape(X3.shape[0], -1), X3.mean(axis=1), X3.max(axis=1)]).astype(np.float32)

    Xtr3, ytr2, atr2 = reshape_daily(X_tr_sc, y_tr, anc_tr)
    Xva3, yva2, ava2 = reshape_daily(X_va_sc, y_va, anc_va)
    Xte3, yte2, ate2 = reshape_daily(X_te_sc, y_te, anc_te)
    w_tr_d = torch.tensor(w_tr[: len(Xtr3) * 24].reshape(-1, 24).mean(axis=1).astype(np.float32))

    F_tr = torch.tensor(make_flat(Xtr3))
    F_va = torch.tensor(make_flat(Xva3))
    F_te = torch.tensor(make_flat(Xte3))
    D_tr = torch.tensor(((ytr2 - atr2) / 5000.0).astype(np.float32))
    D_va = torch.tensor(((yva2 - ava2) / 5000.0).astype(np.float32))

    def train_one(F_fit, D_fit, W_fit, F_eval=None, D_eval=None, n_ep=epochs):
        torch.manual_seed(SEED)
        m = NBeatsInnovationNet(F_fit.shape[1], horizon=24, hidden_dim=224)
        opt = torch.optim.AdamW(m.parameters(), lr=1.2e-3, weight_decay=3e-3)
        sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_ep)
        best_l, best_st, best_ep = 1e9, None, n_ep
        for ep in range(n_ep):
            m.train()
            perm = torch.randperm(F_fit.shape[0])
            for i in range(0, F_fit.shape[0], 32):
                idx = perm[i : i + 32]
                opt.zero_grad()
                out = m(F_fit[idx])
                loss = torch.mean(torch.abs(out - D_fit[idx]).mean(dim=1) * W_fit[idx])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                opt.step()
            sch.step()
            if F_eval is not None:
                m.eval()
                with torch.no_grad():
                    vl = float(torch.mean(torch.abs(m(F_eval) - D_eval)).item())
                if vl < best_l:
                    best_l, best_st, best_ep = vl, {k: v.clone() for k, v in m.state_dict().items()}, ep + 1
        if best_st is not None:
            m.load_state_dict(best_st)
        m.eval()
        return m, best_ep

    # 1. Fit Train -> predict Val & determine optimal epoch count
    m_va, best_ep = train_one(F_tr, D_tr, w_tr_d, F_va, D_va, epochs)
    with torch.no_grad():
        va_pred = cerc_clip(anc_va + m_va(F_va).numpy().reshape(-1) * 5000.0)

    # 2. Expanding refit on Train + Val (2022-2024) for optimal epochs -> predict Test 2025
    F_trva = torch.cat([F_tr, F_va], dim=0)
    D_trva = torch.cat([D_tr, D_va], dim=0)
    w_trva_d = torch.tensor(np.concatenate([
        w_tr[: len(Xtr3) * 24].reshape(-1, 24).mean(axis=1) * 0.6,
        w_va[: len(Xva3) * 24].reshape(-1, 24).mean(axis=1) * 1.4,
    ]).astype(np.float32))
    m_te, _ = train_one(F_trva, D_trva, w_trva_d, None, None, max(25, best_ep))
    with torch.no_grad():
        te_pred = cerc_clip(anc_te + m_te(F_te).numpy().reshape(-1) * 5000.0)
    return va_pred, te_pred


def fit_predict_tft_expanding(
    X_tr_sc, y_tr, anc_tr, w_tr,
    X_va_sc, y_va, anc_va, w_va,
    X_te_sc, y_te, anc_te,
    epochs: int = 75,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    Xtr3, ytr2, atr2 = reshape_daily(X_tr_sc, y_tr, anc_tr)
    Xva3, yva2, ava2 = reshape_daily(X_va_sc, y_va, anc_va)
    Xte3, yte2, ate2 = reshape_daily(X_te_sc, y_te, anc_te)

    T_tr = torch.tensor(Xtr3.astype(np.float32))
    T_va = torch.tensor(Xva3.astype(np.float32))
    T_te = torch.tensor(Xte3.astype(np.float32))
    D_tr = torch.tensor(((ytr2 - atr2) / 5000.0).astype(np.float32))
    D_va = torch.tensor(((yva2 - ava2) / 5000.0).astype(np.float32))
    w_tr_d = torch.tensor(w_tr[: len(Xtr3) * 24].reshape(-1, 24).mean(axis=1).astype(np.float32))

    def train_one(T_fit, D_fit, W_fit, T_eval=None, D_eval=None, n_ep=epochs):
        torch.manual_seed(SEED + 7)
        m = TemporalFusionTransformerInnovation(T_fit.shape[2], d_model=96, n_heads=4, n_quantiles=len(QUANTILES), dropout=0.15)
        opt = torch.optim.AdamW(m.parameters(), lr=1.2e-3, weight_decay=2.5e-3)
        sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_ep)
        best_l, best_st, best_ep = 1e9, None, n_ep
        for ep in range(n_ep):
            m.train()
            perm = torch.randperm(T_fit.shape[0])
            for i in range(0, T_fit.shape[0], 24):
                idx = perm[i : i + 24]
                opt.zero_grad()
                out = m(T_fit[idx])
                loss = pinball_loss_torch(out, D_fit[idx], QUANTILES, W_fit[idx])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                opt.step()
            sch.step()
            if T_eval is not None:
                m.eval()
                with torch.no_grad():
                    vl = float(pinball_loss_torch(m(T_eval), D_eval, QUANTILES).item())
                if vl < best_l:
                    best_l, best_st, best_ep = vl, {k: v.clone() for k, v in m.state_dict().items()}, ep + 1
        if best_st is not None:
            m.load_state_dict(best_st)
        m.eval()
        return m, best_ep

    # 1. Fit Train -> predict Val
    m_va, best_ep = train_one(T_tr, D_tr, w_tr_d, T_va, D_va, epochs)
    with torch.no_grad():
        va_q = np.sort(cerc_clip(anc_va[:, None] + m_va(T_va).numpy().reshape(-1, len(QUANTILES)) * 5000.0), axis=1)

    # 2. Expanding refit on Train+Val (2022-2024) -> predict Test 2025
    T_trva = torch.cat([T_tr, T_va], dim=0)
    D_trva = torch.cat([D_tr, D_va], dim=0)
    w_trva_d = torch.tensor(np.concatenate([
        w_tr[: len(Xtr3) * 24].reshape(-1, 24).mean(axis=1) * 0.6,
        w_va[: len(Xva3) * 24].reshape(-1, 24).mean(axis=1) * 1.4,
    ]).astype(np.float32))
    m_te, _ = train_one(T_trva, D_trva, w_trva_d, None, None, max(30, best_ep))
    with torch.no_grad():
        te_q = np.sort(cerc_clip(anc_te[:, None] + m_te(T_te).numpy().reshape(-1, len(QUANTILES)) * 5000.0), axis=1)

    med_i = QUANTILES.index(0.50)
    return va_q[:, med_i], te_q[:, med_i], va_q, te_q


# ==============================================================================
# RESIDUAL-CENTERED CONFORMALIZED QUANTILE REGRESSION (RESIDUAL-CQR) & COPULA
# ==============================================================================
def evaluate_probabilistic_forecasts(
    y_true: np.ndarray, q_mat: np.ndarray, quantiles: list[float], hours: np.ndarray, label: str
) -> dict[str, float]:
    yt = np.asarray(y_true, dtype=np.float64)
    qm = np.sort(cerc_clip(q_mat), axis=1)

    pinballs = [float(np.mean(np.maximum(tau * (yt - qm[:, j]), (tau - 1.0) * (yt - qm[:, j]))))
                for j, tau in enumerate(quantiles)]
    mean_pb = float(np.mean(pinballs))
    crps = 2.0 * mean_pb

    def interval_stats(lo_q: float, hi_q: float):
        lo = qm[:, quantiles.index(lo_q)]
        hi = qm[:, quantiles.index(hi_q)]
        covered = (yt >= lo) & (yt <= hi)
        picp = float(np.mean(covered) * 100.0)
        width = hi - lo
        mean_w = float(np.mean(width))
        pinaw = mean_w / 10000.0 * 100.0
        alpha = 1.0 - (hi_q - lo_q)
        winkler = float(np.mean(width + (2.0 / alpha) * np.maximum(lo - yt, 0.0) + (2.0 / alpha) * np.maximum(yt - hi, 0.0)))
        return picp, mean_w, pinaw, winkler, covered

    picp50, _, _, _, _ = interval_stats(0.25, 0.75)
    picp80, _, _, _, _ = interval_stats(0.10, 0.90)
    picp90, w90, pinaw90, wink90, cov90 = interval_stats(0.05, 0.95)

    peak_mask = np.isin(hours, [18, 19, 20, 21, 22])
    spike_mask = yt >= 8000.0
    picp90_peak = float(np.mean(cov90[peak_mask]) * 100.0)
    picp90_spike = float(np.mean(cov90[spike_mask]) * 100.0) if spike_mask.any() else np.nan

    n = len(cov90)
    k = int(np.sum(cov90))
    p_hat = np.clip(k / n, 1e-6, 1.0 - 1e-6)
    lr_kupiec = -2.0 * (k * np.log(0.90) + (n - k) * np.log(0.10) - (k * np.log(p_hat) + (n - k) * np.log(1.0 - p_hat)))
    kupiec_p = float(1.0 - stats.chi2.cdf(lr_kupiec, df=1))

    return {
        "Probabilistic_Model": label,
        "Mean_Pinball_Rs": round(mean_pb, 2),
        "CRPS_Rs": round(crps, 2),
        "PICP_50_pct": round(picp50, 2),
        "PICP_80_pct": round(picp80, 2),
        "PICP_90_pct": round(picp90, 2),
        "Width_90_Rs": round(w90, 1),
        "PINAW_90_pct": round(pinaw90, 2),
        "Winkler_90_Rs": round(wink90, 1),
        "Peak_PICP_90_pct": round(picp90_peak, 2),
        "Spike_PICP_90_pct": round(picp90_spike, 2),
        "Kupiec_LR_p": round(kupiec_p, 4),
    }


def fit_residual_cqr_quantiles(
    X_va: np.ndarray, y_va: np.ndarray, pt_va: np.ndarray, hrs_va: np.ndarray,
    X_te: np.ndarray, pt_te: np.ndarray, hrs_te: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict, dict]:
    """
    Trains heteroskedastic Residual Quantile Regression models on the post-cap-revision
    Validation 2024 out-of-sample residuals (e_t = y_t - pt_t) using 5-fold temporally
    blocked Purged OOF CV for conformal calibration, then fits full-2024 residual quantile
    models to generate sharp, well-calibrated, asymmetric prediction intervals on Test 2025!
    """
    res_va = y_va - pt_va
    # Build enriched uncertainty feature matrix: X + point forecast + distance to CERC cap/floor
    def aug_X(X_in, pt_in):
        return np.column_stack([X_in, pt_in, 10000.0 - pt_in, np.abs(pt_in - 5000.0)])

    Xva_q = aug_X(X_va, pt_va)
    Xte_q = aug_X(X_te, pt_te)

    # 1. 5-fold temporally blocked OOF residual quantile predictions on Val 2024
    n_va = len(y_va)
    oof_res_q = np.zeros((n_va, len(QUANTILES)), dtype=np.float64)
    folds = np.linspace(0, n_va, 6, dtype=int)
    purge = 48

    q_params = dict(
        n_estimators=220, learning_rate=0.035, num_leaves=31, min_child_samples=50,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.75, reg_lambda=8.0,
        random_state=SEED, n_jobs=-1, verbose=-1,
    )

    for f in range(5):
        vs, ve = folds[f], folds[f + 1]
        keep = np.ones(n_va, dtype=bool)
        keep[max(0, vs - purge) : min(n_va, ve + purge)] = False
        for j, tau in enumerate(QUANTILES):
            qm = lgb.LGBMRegressor(objective="quantile", alpha=tau, **q_params)
            qm.fit(Xva_q[keep], res_va[keep])
            oof_res_q[vs:ve, j] = qm.predict(Xva_q[vs:ve])

    q_va_raw = np.sort(cerc_clip(pt_va[:, None] + oof_res_q), axis=1)

    # 2. Fit full Val-2024 residual quantile models -> predict Test 2025
    q_te_raw_res = np.zeros((len(pt_te), len(QUANTILES)), dtype=np.float64)
    q_models_res = {}
    for j, tau in enumerate(QUANTILES):
        qm = lgb.LGBMRegressor(objective="quantile", alpha=tau, **q_params)
        qm.fit(Xva_q, res_va)
        q_te_raw_res[:, j] = qm.predict(Xte_q)
        q_models_res[tau] = qm

    q_te_raw = np.sort(cerc_clip(pt_te[:, None] + q_te_raw_res), axis=1)

    # 3. Regime-Conditional Conformalized Quantile Regression (CQR) calibrated strictly on Val-2024 OOF!
    def reg_code(hrs):
        r = np.zeros(len(hrs), dtype=int)
        r[(hrs >= 9) & (hrs <= 16)] = 1
        r[np.isin(hrs, [18, 19, 20, 21, 22])] = 2
        return r

    r_va = reg_code(hrs_va)
    r_te = reg_code(hrs_te)
    q_va_cqr = q_va_raw.copy()
    q_te_cqr = q_te_raw.copy()
    cal_margins = {}

    for lo_q, hi_q, nom in [(0.25, 0.75, 0.50), (0.10, 0.90, 0.80), (0.05, 0.95, 0.90)]:
        i_lo, i_hi = QUANTILES.index(lo_q), QUANTILES.index(hi_q)
        for rc in [0, 1, 2]:
            mk_va = r_va == rc
            mk_te = r_te == rc
            scores = np.maximum(q_va_raw[mk_va, i_lo] - y_va[mk_va], y_va[mk_va] - q_va_raw[mk_va, i_hi])
            q_lev = min(1.0, (1.0 + 1.0 / len(scores)) * nom)
            m = float(np.quantile(scores, q_lev))
            q_va_cqr[mk_va, i_lo] = q_va_raw[mk_va, i_lo] - m
            q_va_cqr[mk_va, i_hi] = q_va_raw[mk_va, i_hi] + m
            q_te_cqr[mk_te, i_lo] = q_te_raw[mk_te, i_lo] - m
            q_te_cqr[mk_te, i_hi] = q_te_raw[mk_te, i_hi] + m
            cal_margins[f"nom{int(nom*100)}_reg{rc}"] = round(m, 2)

    q_va_cqr = np.sort(cerc_clip(q_va_cqr), axis=1)
    q_te_cqr = np.sort(cerc_clip(q_te_cqr), axis=1)
    return q_va_cqr, q_te_raw, q_te_cqr, cal_margins, q_models_res


def generate_copula_price_scenarios(
    y_val: np.ndarray, q_val_cqr: np.ndarray, q_test_cqr: np.ndarray, n_scenarios: int = 200
) -> np.ndarray:
    tau_grid = np.array([0.005] + QUANTILES + [0.995], dtype=np.float64)

    def augment(qm):
        lo = np.maximum(0.0, qm[:, 0] - 0.55 * (qm[:, 1] - qm[:, 0]))
        hi = np.minimum(10000.0, qm[:, -1] + 0.55 * (qm[:, -1] - qm[:, -2]))
        return np.column_stack([lo, qm, hi])

    qva_a = augment(q_val_cqr)
    qte_a = augment(q_test_cqr)
    n_va_d = len(y_val) // 24
    u_va = np.zeros((n_va_d, 24), dtype=np.float64)
    for idx in range(n_va_d * 24):
        di, hi = divmod(idx, 24)
        qs = np.maximum.accumulate(qva_a[idx] + np.linspace(0, 1e-3, len(tau_grid)))
        u_va[di, hi] = np.interp(y_val[idx], qs, tau_grid)

    z_va = stats.norm.ppf(np.clip(u_va, 0.005, 0.995))
    corr_pd = 0.95 * np.corrcoef(z_va, rowvar=False) + 0.05 * np.eye(24)
    L_chol = np.linalg.cholesky(corr_pd)

    rng = np.random.default_rng(SEED)
    n_te_d = len(q_test_cqr) // 24
    scenarios = np.zeros((n_te_d, n_scenarios, 24), dtype=np.float64)
    for di in range(n_te_d):
        U = stats.norm.cdf(rng.standard_normal((n_scenarios, 24)) @ L_chol.T)
        for hi in range(24):
            scenarios[di, :, hi] = cerc_clip(np.interp(U[:, hi], tau_grid, qte_a[di * 24 + hi]))
    return scenarios


# ==============================================================================
# MAIN BENCHMARKING & PROBABILISTIC PIPELINE
# ==============================================================================
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 86)
    print("ENERGYCAST V2 — CAPACITY-ADAPTIVE 13-MODEL, DEEP NEURAL & RESIDUAL-CQR SUITE")
    print("=" * 86)

    tr_raw = pd.read_csv(CAUSAL_DIR / "operational_train.csv")
    va_raw = pd.read_csv(CAUSAL_DIR / "operational_val.csv")
    te_raw = pd.read_csv(CAUSAL_DIR / "operational_test.csv")

    with open(CAUSAL_DIR / "causal_d1_metadata.json") as f:
        meta = json.load(f)
    base_features = meta["feature_cols"]

    # Add 3 strictly causal trailing-30-day capacity-relative features continuously across chronological splits
    all_op = pd.concat([tr_raw, va_raw, te_raw], ignore_index=True)
    all_op = add_capacity_relative_features(all_op)
    n_tr, n_va, n_te = len(tr_raw), len(va_raw), len(te_raw)
    tr_df = all_op.iloc[:n_tr].reset_index(drop=True)
    va_df = all_op.iloc[n_tr : n_tr + n_va].reset_index(drop=True)
    te_df = all_op.iloc[n_tr + n_va :].reset_index(drop=True)

    # Save augmented operational splits so stress-testing uses identical 65-feature schema!
    tr_df.to_csv(CAUSAL_DIR / "operational_train_v2.csv", index=False)
    va_df.to_csv(CAUSAL_DIR / "operational_val_v2.csv", index=False)
    te_df.to_csv(CAUSAL_DIR / "operational_test_v2.csv", index=False)

    feature_cols = base_features + ["nd_fcst_rel_30d", "nd_fcst_zscore_30d", "mcp_d1_rel_30d"]
    print(f"Loaded Capacity-Adaptive D-1 splits: Train={n_tr:,}, Val={n_va:,}, Test={n_te:,} | Features={len(feature_cols)}")

    X_tr, y_tr, anc_tr = tr_df[feature_cols].values, tr_df["mcp_rs_per_mwh"].values, tr_df["mcp_d1_same_h"].values
    X_va, y_va, anc_va = va_df[feature_cols].values, va_df["mcp_rs_per_mwh"].values, va_df["mcp_d1_same_h"].values
    X_te, y_te, anc_te = te_df[feature_cols].values, te_df["mcp_rs_per_mwh"].values, te_df["mcp_d1_same_h"].values
    hrs_va = pd.to_datetime(va_df["timestamp"]).dt.hour.values
    hrs_te = pd.to_datetime(te_df["timestamp"]).dt.hour.values

    # Stationarized day-ahead innovation target: delta_y = P_{D,h} - P_{D-1,h}
    dy_tr = y_tr - anc_tr
    dy_va = y_va - anc_va
    w_tr = make_recency_weights(tr_df["timestamp"])
    w_va = make_recency_weights(va_df["timestamp"])

    # Expanding Train+Val matrix for Test 2025 operational deployment (strictly <= Dec 31, 2024!)
    trva_df = pd.concat([tr_df, va_df], ignore_index=True)
    X_trva = trva_df[feature_cols].values
    y_trva = trva_df["mcp_rs_per_mwh"].values
    anc_trva = trva_df["mcp_d1_same_h"].values
    dy_trva = y_trva - anc_trva
    w_trva = make_recency_weights(trva_df["timestamp"], half_life_days=270.0)

    # Scalers (Train-only for Val 2024; Train+Val for Test 2025)
    sc_val = StandardScaler().fit(X_tr)
    X_tr_sc = sc_val.transform(X_tr)
    X_va_sc = sc_val.transform(X_va)

    sc_test = StandardScaler().fit(X_trva)
    X_trva_sc = sc_test.transform(X_trva)
    X_te_sc = sc_test.transform(X_te)
    joblib.dump(sc_test, MODELS_V2_DIR / "scaler_d1.joblib")

    val_preds: dict[str, np.ndarray] = {}
    test_preds: dict[str, np.ndarray] = {}
    tiers: dict[str, str] = {}

    # -------------------------------------------------------------------------
    # TIER 1: OPERATIONAL D-1 MARKET BASELINES
    # -------------------------------------------------------------------------
    print("\n[Tier 1] Operational D-1 Market Baselines...")
    val_preds["Weekly S-Naive (168h)"] = cerc_clip(va_df["mcp_d7_same_h"].values)
    test_preds["Weekly S-Naive (168h)"] = cerc_clip(te_df["mcp_d7_same_h"].values)
    tiers["Weekly S-Naive (168h)"] = "Tier 1: Baselines"

    val_preds["Daily S-Naive (24h Ref.)"] = cerc_clip(anc_va)
    test_preds["Daily S-Naive (24h Ref.)"] = cerc_clip(anc_te)
    tiers["Daily S-Naive (24h Ref.)"] = "Tier 1: Baselines"

    # -------------------------------------------------------------------------
    # TIER 2: ECONOMETRIC & REGULARIZED LINEAR MODELS (EXPANDING RECALIBRATION)
    # -------------------------------------------------------------------------
    print("[Tier 2] Fitting 24-Equation SARIMAX, OLS, LASSO, ElasticNet, Ridge...")
    va_sar, te_sar = run_24h_sarimax(tr_df, va_df, te_df)
    val_preds["SARIMAX (24-Eq. Seasonal)"] = va_sar
    test_preds["SARIMAX (24-Eq. Seasonal)"] = te_sar
    tiers["SARIMAX (24-Eq. Seasonal)"] = "Tier 2: Econometric"

    # OLS (Innovation target)
    ols_v = LinearRegression().fit(X_tr_sc, dy_tr, sample_weight=w_tr)
    val_preds["OLS Linear Regression"] = cerc_clip(anc_va + ols_v.predict(X_va_sc))
    ols_t = LinearRegression().fit(X_trva_sc, dy_trva, sample_weight=w_trva)
    test_preds["OLS Linear Regression"] = cerc_clip(anc_te + ols_t.predict(X_te_sc))
    tiers["OLS Linear Regression"] = "Tier 2: Linear"

    # LASSO (tune alpha on Val 2024, refit expanding for Test 2025)
    best_la, best_la_mae = 5.0, 1e9
    for a in [1.0, 3.0, 8.0, 15.0, 30.0, 60.0]:
        m = Lasso(alpha=a, max_iter=3500, random_state=SEED).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
        mv = float(np.mean(np.abs(y_va - cerc_clip(anc_va + m.predict(X_va_sc)))))
        if mv < best_la_mae:
            best_la, best_la_mae = a, mv
    lasso_v = Lasso(alpha=best_la, max_iter=3500, random_state=SEED).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
    lasso_t = Lasso(alpha=best_la, max_iter=3500, random_state=SEED).fit(X_trva_sc, dy_trva, sample_weight=w_trva)
    lasso_key = f"LASSO L1 (alpha={best_la:g})"
    val_preds[lasso_key] = cerc_clip(anc_va + lasso_v.predict(X_va_sc))
    test_preds[lasso_key] = cerc_clip(anc_te + lasso_t.predict(X_te_sc))
    tiers[lasso_key] = "Tier 2: Linear"

    # Elastic Net (tune on Val 2024, refit expanding for Test 2025)
    best_en_cfg, best_en_mae = (0.1, 0.5), 1e9
    for a in [0.05, 0.2, 0.5, 1.5]:
        for l1r in [0.2, 0.5, 0.8]:
            m = ElasticNet(alpha=a, l1_ratio=l1r, max_iter=3000, random_state=SEED).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
            mv = float(np.mean(np.abs(y_va - cerc_clip(anc_va + m.predict(X_va_sc)))))
            if mv < best_en_mae:
                best_en_cfg, best_en_mae = (a, l1r), mv
    en_v = ElasticNet(alpha=best_en_cfg[0], l1_ratio=best_en_cfg[1], max_iter=3000, random_state=SEED).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
    en_t = ElasticNet(alpha=best_en_cfg[0], l1_ratio=best_en_cfg[1], max_iter=3000, random_state=SEED).fit(X_trva_sc, dy_trva, sample_weight=w_trva)
    en_key = f"Elastic Net (a={best_en_cfg[0]:g}, l1={best_en_cfg[1]:g})"
    val_preds[en_key] = cerc_clip(anc_va + en_v.predict(X_va_sc))
    test_preds[en_key] = cerc_clip(anc_te + en_t.predict(X_te_sc))
    tiers[en_key] = "Tier 2: Linear"

    # Ridge (tune alpha on Val 2024, refit expanding for Test 2025)
    best_ra, best_ra_mae = 100.0, 1e9
    for a in [10.0, 50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0]:
        m = Ridge(alpha=a).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
        mv = float(np.mean(np.abs(y_va - cerc_clip(anc_va + m.predict(X_va_sc)))))
        if mv < best_ra_mae:
            best_ra, best_ra_mae = a, mv
    ridge_v = Ridge(alpha=best_ra).fit(X_tr_sc, dy_tr, sample_weight=w_tr)
    ridge_t = Ridge(alpha=best_ra).fit(X_trva_sc, dy_trva, sample_weight=w_trva)
    ridge_key = f"Tikhonov Ridge (alpha={int(best_ra)})"
    val_preds[ridge_key] = cerc_clip(anc_va + ridge_v.predict(X_va_sc))
    test_preds[ridge_key] = cerc_clip(anc_te + ridge_t.predict(X_te_sc))
    tiers[ridge_key] = "Tier 2: Linear"
    joblib.dump(ridge_t, MODELS_V2_DIR / "ridge_d1.joblib")

    # -------------------------------------------------------------------------
    # TIER 3: NONLINEAR TREE ENSEMBLES (RF, XGBoost, CatBoost, LightGBM)
    # Using Innovation Target + Expanding Monthly Recalibration (100% Causal!)
    # -------------------------------------------------------------------------
    print("[Tier 3] Training Random Forest, XGBoost, CatBoost, and LightGBM (Innovation Target + Expanding Recalibration)...")

    rf_v = RandomForestRegressor(n_estimators=220, max_depth=16, min_samples_leaf=8, max_features=0.65, random_state=SEED, n_jobs=-1)
    rf_v.fit(X_tr, dy_tr, sample_weight=w_tr)
    val_preds["Random Forest (220 Trees)"] = cerc_clip(anc_va + rf_v.predict(X_va))
    rf_t = RandomForestRegressor(n_estimators=220, max_depth=16, min_samples_leaf=8, max_features=0.65, random_state=SEED, n_jobs=-1)
    rf_t.fit(X_trva, dy_trva, sample_weight=w_trva)
    test_preds["Random Forest (220 Trees)"] = cerc_clip(anc_te + rf_t.predict(X_te))
    tiers["Random Forest (220 Trees)"] = "Tier 3: Tree Ensemble"

    # XGBoost: early-stop on Val 2024 to fix best n_estimators, then expanding monthly recalibration on Test 2025
    xgb_v = xgb.XGBRegressor(
        n_estimators=1200, learning_rate=0.025, max_depth=6, min_child_weight=25,
        subsample=0.8, colsample_bytree=0.75, reg_lambda=8.0, reg_alpha=1.5,
        objective="reg:absoluteerror", early_stopping_rounds=50,
        random_state=SEED, n_jobs=-1, tree_method="hist",
    )
    xgb_v.fit(X_tr, dy_tr, sample_weight=w_tr, eval_set=[(X_va, dy_va)], verbose=False)
    xgb_best_n = max(120, int(xgb_v.best_iteration))
    val_preds["XGBoost Regressor"] = cerc_clip(anc_va + xgb_v.predict(X_va))

    # CatBoost: early-stop on Val 2024 to fix best iterations
    cb_v = CatBoostRegressor(
        iterations=1500, learning_rate=0.03, depth=6, l2_leaf_reg=8.0,
        loss_function="MAE", eval_metric="MAE", random_seed=SEED,
        early_stopping_rounds=60, verbose=False, thread_count=-1,
    )
    cb_v.fit(X_tr, dy_tr, sample_weight=w_tr, eval_set=(X_va, dy_va), use_best_model=True)
    cb_best_n = max(150, int(cb_v.get_best_iteration()))
    val_preds["CatBoost Regressor"] = cerc_clip(anc_va + cb_v.predict(X_va))

    # LightGBM: early-stop on Val 2024 to fix best iterations
    lgb_v = lgb.LGBMRegressor(
        objective="regression_l1", n_estimators=1500, learning_rate=0.025,
        num_leaves=47, min_child_samples=45, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.75, reg_lambda=8.0, reg_alpha=1.5,
        random_state=SEED, n_jobs=-1, verbose=-1,
    )
    lgb_v.fit(X_tr, dy_tr, sample_weight=w_tr, eval_set=[(X_va, dy_va)], callbacks=[lgb.early_stopping(60, verbose=False)])
    lgb_best_n = max(150, int(lgb_v.best_iteration_))
    val_preds["LightGBM Regressor"] = cerc_clip(anc_va + lgb_v.predict(X_va))

    # Record Static-Frozen (trained ONLY on 2022-2023) LightGBM on Test 2025 for recalibration ablation!
    lgb_static_te = cerc_clip(anc_te + lgb_v.predict(X_te))

    # Operational Monthly Expanding-Window Recalibration on Test 2025 (strictly <= end of prior month m-1!)
    te_months = pd.to_datetime(te_df["timestamp"]).dt.month.values
    xgb_te_pred = np.zeros(n_te, dtype=np.float64)
    cb_te_pred = np.zeros(n_te, dtype=np.float64)
    lgb_te_pred = np.zeros(n_te, dtype=np.float64)
    lgb_last_model = None

    for m_num in sorted(np.unique(te_months)):
        # Strictly past test rows from months < m_num appended to Train+Val (zero leakage!)
        past_te_mask = te_months < m_num
        curr_te_mask = te_months == m_num
        if past_te_mask.any():
            hist_df = pd.concat([trva_df, te_df.iloc[np.where(past_te_mask)[0]]], ignore_index=True)
        else:
            hist_df = trva_df
        Xh = hist_df[feature_cols].values
        dyh = hist_df["mcp_rs_per_mwh"].values - hist_df["mcp_d1_same_h"].values
        wh = make_recency_weights(hist_df["timestamp"], half_life_days=240.0)
        Xc = X_te[curr_te_mask]
        ac = anc_te[curr_te_mask]

        m_x = xgb.XGBRegressor(
            n_estimators=xgb_best_n, learning_rate=0.025, max_depth=6, min_child_weight=25,
            subsample=0.8, colsample_bytree=0.75, reg_lambda=8.0, reg_alpha=1.5,
            objective="reg:absoluteerror", random_state=SEED, n_jobs=-1, tree_method="hist",
        ).fit(Xh, dyh, sample_weight=wh, verbose=False)
        xgb_te_pred[curr_te_mask] = cerc_clip(ac + m_x.predict(Xc))

        m_c = CatBoostRegressor(
            iterations=cb_best_n, learning_rate=0.03, depth=6, l2_leaf_reg=8.0,
            loss_function="MAE", random_seed=SEED, verbose=False, thread_count=-1,
        ).fit(Xh, dyh, sample_weight=wh)
        cb_te_pred[curr_te_mask] = cerc_clip(ac + m_c.predict(Xc))

        m_l = lgb.LGBMRegressor(
            objective="regression_l1", n_estimators=lgb_best_n, learning_rate=0.025,
            num_leaves=47, min_child_samples=45, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.75, reg_lambda=8.0, reg_alpha=1.5,
            random_state=SEED, n_jobs=-1, verbose=-1,
        ).fit(Xh, dyh, sample_weight=wh)
        lgb_te_pred[curr_te_mask] = cerc_clip(ac + m_l.predict(Xc))
        if m_num == 1:
            # Save Jan-2025 expanding model (strictly trained on 2022-2024) for consistent stress-testing & TreeSHAP!
            lgb_last_model = m_l
            joblib.dump(m_l, MODELS_V2_DIR / "lightgbm_d1.joblib")
            joblib.dump(m_x, MODELS_V2_DIR / "xgboost_d1.joblib")
            joblib.dump(m_c, MODELS_V2_DIR / "catboost_d1.joblib")

    test_preds["XGBoost Regressor"] = xgb_te_pred
    tiers["XGBoost Regressor"] = "Tier 3: GBDT"
    test_preds["CatBoost Regressor"] = cb_te_pred
    tiers["CatBoost Regressor"] = "Tier 3: GBDT"
    test_preds["LightGBM Regressor"] = lgb_te_pred
    tiers["LightGBM Regressor"] = "Tier 3: GBDT"

    # -------------------------------------------------------------------------
    # TIER 4: DEEP TEMPORAL NEURAL BENCHMARKS (PyTorch N-BEATS & TFT)
    # -------------------------------------------------------------------------
    print("[Tier 4] Training Deep Temporal Neural Benchmarks (PyTorch N-BEATS & TFT, Innovation Target)...")
    va_nb, te_nb = fit_predict_nbeats_expanding(
        X_tr_sc, y_tr, anc_tr, w_tr,
        X_va_sc, y_va, anc_va, w_va,
        sc_val.transform(X_te), y_te, anc_te, epochs=65,
    )
    val_preds["N-BEATS (Multi-Stack Neural)"] = va_nb
    test_preds["N-BEATS (Multi-Stack Neural)"] = te_nb
    tiers["N-BEATS (Multi-Stack Neural)"] = "Tier 4: Deep Neural"

    va_tft, te_tft, va_tft_q, te_tft_q = fit_predict_tft_expanding(
        X_tr_sc, y_tr, anc_tr, w_tr,
        X_va_sc, y_va, anc_va, w_va,
        sc_val.transform(X_te), y_te, anc_te, epochs=70,
    )
    val_preds["Temporal Fusion Transformer (TFT)"] = va_tft
    test_preds["Temporal Fusion Transformer (TFT)"] = te_tft
    tiers["Temporal Fusion Transformer (TFT)"] = "Tier 4: Deep Neural"

    # Hybrid Ensemble tuned strictly on Val 2024 (LightGBM + CatBoost + XGBoost + TFT)
    cand_names = ["LightGBM Regressor", "CatBoost Regressor", "XGBoost Regressor", "Temporal Fusion Transformer (TFT)"]
    best_w, best_ens_mae = (0.35, 0.35, 0.15, 0.15), 1e9
    for w1 in np.linspace(0.1, 0.6, 11):
        for w2 in np.linspace(0.1, 0.6, 11):
            for w3 in np.linspace(0.0, 0.35, 8):
                w4 = round(1.0 - w1 - w2 - w3, 4)
                if w4 < 0.05 or w4 > 0.45:
                    continue
                pv = w1 * val_preds[cand_names[0]] + w2 * val_preds[cand_names[1]] + w3 * val_preds[cand_names[2]] + w4 * val_preds[cand_names[3]]
                mv = float(np.mean(np.abs(y_va - pv)))
                if mv < best_ens_mae:
                    best_ens_mae = mv
                    best_w = (round(float(w1), 2), round(float(w2), 2), round(float(w3), 2), round(float(w4), 2))

    ens_label = "EnergyCast Hybrid Ensemble (GBDT+TFT)"
    val_preds[ens_label] = sum(w * val_preds[n] for w, n in zip(best_w, cand_names))
    test_preds[ens_label] = sum(w * test_preds[n] for w, n in zip(best_w, cand_names))
    tiers[ens_label] = "Tier 4+: Hybrid Champion"
    print(f"  Optimal Val-2024 Hybrid Weights (LGB/CB/XGB/TFT): {best_w}")

    # -------------------------------------------------------------------------
    # MASTER LEADERBOARD & DIEBOLD-MARIANO HAC (L=9) TESTS
    # -------------------------------------------------------------------------
    ref_mae_te = compute_point_metrics(y_te, test_preds["Daily S-Naive (24h Ref.)"], hrs_te)["MAE"]
    champ_name = min(val_preds.keys(), key=lambda k: compute_point_metrics(y_va, val_preds[k], hrs_va)["MAE"])
    print(f"\n==> Validation-Selected Champion: {champ_name}")

    lb_rows, dm_rows = [], []
    print("\n" + "-" * 116)
    print(f"{'Model':38s} | {'ValMAE':7s} | {'TestMAE':7s} | {'RMSE':7s} | {'sMAPE':6s} | {'R2':6s} | {'PeakMAE':7s} | {'Gain24h':7s} | {'DM_vs_Ch':8s}")
    print("-" * 116)
    for m_name in val_preds.keys():
        vm = compute_point_metrics(y_va, val_preds[m_name], hrs_va)
        tm = compute_point_metrics(y_te, test_preds[m_name], hrs_te)
        gain_24 = round((ref_mae_te - tm["MAE"]) / ref_mae_te * 100.0, 2)
        dm_stat, dm_p = (0.0, 1.0) if m_name == champ_name else diebold_mariano_hac(y_te, test_preds[m_name], test_preds[champ_name], loss="abs")
        dm_lgb, dm_p_lgb = (0.0, 1.0) if m_name == "LightGBM Regressor" else diebold_mariano_hac(y_te, test_preds[m_name], test_preds["LightGBM Regressor"], loss="abs")

        lb_rows.append({
            "Tier": tiers[m_name], "Model": m_name,
            "Val_MAE": vm["MAE"], "Val_RMSE": vm["RMSE"], "Val_R2": vm["R2"],
            "Test_MAE": tm["MAE"], "Test_RMSE": tm["RMSE"], "Test_sMAPE": tm["sMAPE"],
            "Test_R2": tm["R2"], "Test_Peak_MAE": tm["Peak_MAE"], "Test_Solar_MAE": tm["Solar_MAE"],
            "Test_Spike_MAE": tm["Spike_MAE"], "Test_Bias": tm["Mean_Bias"],
            "Gain_vs_SNaive24_pct": gain_24, "DM_vs_Champion": dm_stat, "DM_p_vs_Champion": dm_p,
            "DM_vs_LightGBM": dm_lgb, "DM_p_vs_LightGBM": dm_p_lgb,
        })
        dm_rows.append({
            "Model_1": m_name, "Model_2": champ_name, "DM_HAC_L9": dm_stat, "p_value": dm_p,
            "Sig_1pct": "Yes" if (m_name != champ_name and dm_p < 0.01) else ("Yes (5%)" if (m_name != champ_name and dm_p < 0.05) else "Ref/No"),
        })
        print(
            f"{m_name:38s} | {vm['MAE']:7.2f} | {tm['MAE']:7.2f} | {tm['RMSE']:7.2f} | "
            f"{tm['sMAPE']:5.2f}% | {tm['R2']:6.4f} | {tm['Peak_MAE']:7.2f} | {gain_24:+6.2f}% | {dm_stat:+8.3f}"
        )

    pd.DataFrame(lb_rows).to_csv(TABLE_DIR / "v2_master_benchmark_leaderboard.csv", index=False)
    pd.DataFrame(dm_rows).to_csv(TABLE_DIR / "v2_diebold_mariano_hac_tests.csv", index=False)

    # -------------------------------------------------------------------------
    # CAUSALITY & RECALIBRATION ABLATION AUDIT
    # -------------------------------------------------------------------------
    print("\n[Causality & Recalibration Audit] Running Ex-Post Perfect-Exogenous Ablation...")
    all_or = add_capacity_relative_features(pd.concat([
        pd.read_csv(CAUSAL_DIR / "oracle_exog_train.csv"),
        pd.read_csv(CAUSAL_DIR / "oracle_exog_val.csv"),
        pd.read_csv(CAUSAL_DIR / "oracle_exog_test.csv"),
    ], ignore_index=True))
    or_trva = all_or.iloc[: n_tr + n_va]
    or_te = all_or.iloc[n_tr + n_va :].reset_index(drop=True)
    # Monthly expanding Oracle-Exog LightGBM (identical protocol to Operational D-1 LightGBM!)
    or_te_pred = np.zeros(n_te, dtype=np.float64)
    for m_num in sorted(np.unique(te_months)):
        pm = te_months < m_num
        cm = te_months == m_num
        hd = pd.concat([or_trva, or_te.iloc[np.where(pm)[0]]], ignore_index=True) if pm.any() else or_trva
        ml_o = lgb.LGBMRegressor(
            objective="regression_l1", n_estimators=lgb_best_n, learning_rate=0.025,
            num_leaves=47, min_child_samples=45, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.75, reg_lambda=8.0, reg_alpha=1.5,
            random_state=SEED, n_jobs=-1, verbose=-1,
        ).fit(hd[feature_cols].values, hd["mcp_rs_per_mwh"].values - hd["mcp_d1_same_h"].values, sample_weight=make_recency_weights(hd["timestamp"], 240.0))
        or_te_pred[cm] = cerc_clip(or_te["mcp_d1_same_h"].values[cm] + ml_o.predict(or_te[feature_cols].values[cm]))

    m_static = compute_point_metrics(y_te, lgb_static_te, hrs_te)
    m_op_lgb = compute_point_metrics(y_te, test_preds["LightGBM Regressor"], hrs_te)
    m_op_ch = compute_point_metrics(y_te, test_preds[champ_name], hrs_te)
    m_or_lgb = compute_point_metrics(y_te, or_te_pred, hrs_te)
    dm_exog, p_exog = diebold_mariano_hac(y_te, test_preds["LightGBM Regressor"], or_te_pred)

    ablation_rows = [
        {
            "Information_Regime": "1. Strict Operational D-1 — Static Frozen 2022-2023 (LightGBM)",
            "Same_Day_Price_Lags": "No (Removed)",
            "Delivery_Day_Grid_Weather": "Stage-1 Causal D-1 Forecast",
            "Test_MAE": m_static["MAE"], "Test_RMSE": m_static["RMSE"], "Test_sMAPE": m_static["sMAPE"],
            "Test_R2": m_static["R2"], "Peak_MAE": m_static["Peak_MAE"],
            "Note": "Shows cost of skipping operational recalibration under thermal capacity drift",
        },
        {
            "Information_Regime": "2. Strict Operational D-1 — Expanding Recalibrated (LightGBM)",
            "Same_Day_Price_Lags": "No (Removed)",
            "Delivery_Day_Grid_Weather": "Stage-1 Causal D-1 Forecast",
            "Test_MAE": m_op_lgb["MAE"], "Test_RMSE": m_op_lgb["RMSE"], "Test_sMAPE": m_op_lgb["sMAPE"],
            "Test_R2": m_op_lgb["R2"], "Peak_MAE": m_op_lgb["Peak_MAE"],
            "Note": "Deployable single-model GBDT strictly respecting F_{D-1,10:30}",
        },
        {
            "Information_Regime": "3. Strict Operational D-1 — Expanding Hybrid Champion (GBDT+TFT)",
            "Same_Day_Price_Lags": "No (Removed)",
            "Delivery_Day_Grid_Weather": "Stage-1 Causal D-1 Forecast",
            "Test_MAE": m_op_ch["MAE"], "Test_RMSE": m_op_ch["RMSE"], "Test_sMAPE": m_op_ch["sMAPE"],
            "Test_R2": m_op_ch["R2"], "Peak_MAE": m_op_ch["Peak_MAE"],
            "Note": "Primary deployable champion strictly respecting F_{D-1,10:30}",
        },
        {
            "Information_Regime": "4. Ex-Post Perfect-Exogenous Upper Bound (LightGBM, No P_{t-1})",
            "Same_Day_Price_Lags": "No (Removed)",
            "Delivery_Day_Grid_Weather": "Realized Ex-Post Day-D (Oracle)",
            "Test_MAE": m_or_lgb["MAE"], "Test_RMSE": m_or_lgb["RMSE"], "Test_sMAPE": m_or_lgb["sMAPE"],
            "Test_R2": m_or_lgb["R2"], "Peak_MAE": m_or_lgb["Peak_MAE"],
            "Note": f"Value of Perfect Day-Ahead Grid/RE Forecast: DeltaMAE = Rs.{m_op_lgb['MAE'] - m_or_lgb['MAE']:.2f}/MWh (DM={dm_exog:+.2f})",
        },
        {
            "Information_Regime": "5. Legacy V1 Contemporaneous Specification (Audited Leakage)",
            "Same_Day_Price_Lags": "Yes (Inadmissible P_{t-1})",
            "Delivery_Day_Grid_Weather": "Realized Ex-Post Day-D",
            "Test_MAE": 433.33, "Test_RMSE": 703.43, "Test_sMAPE": 11.88,
            "Test_R2": 0.9317, "Peak_MAE": 617.63,
            "Note": "Superseded V1 benchmark; transparently audited to quantify intraday look-ahead bias",
        },
    ]
    pd.DataFrame(ablation_rows).to_csv(TABLE_DIR / "v2_causality_ablation_audit.csv", index=False)
    print(f"  Static Frozen LGB MAE: Rs.{m_static['MAE']:.2f} -> Expanding Op. LGB MAE: Rs.{m_op_lgb['MAE']:.2f} -> Hybrid Champ MAE: Rs.{m_op_ch['MAE']:.2f} | Ex-Post Perfect-Exog LGB MAE: Rs.{m_or_lgb['MAE']:.2f} (Value of Perfect Exog = Rs.{m_op_lgb['MAE'] - m_or_lgb['MAE']:+.2f}/MWh, DM={dm_exog:+.2f})")

    # -------------------------------------------------------------------------
    # PROBABILISTIC FORECASTING: RESIDUAL-CENTERED CQR + GAUSSIAN COPULA
    # -------------------------------------------------------------------------
    print("\n[Probabilistic Forecasting] Fitting Residual-Centered Heteroskedastic CQR...")
    q_va_cqr, q_te_raw, q_te_cqr, cqr_margins, q_models_res = fit_residual_cqr_quantiles(
        X_va, y_va, val_preds[champ_name], hrs_va,
        X_te, test_preds[champ_name], hrs_te,
    )
    joblib.dump(q_models_res, MODELS_V2_DIR / "residual_quantiles_d1.joblib")

    # Homoskedastic Gaussian Baseline on Val 2024 residuals
    sigma_va = float(np.std(y_va - val_preds[champ_name]))
    q_te_gauss = np.column_stack([cerc_clip(test_preds[champ_name] + stats.norm.ppf(tau) * sigma_va) for tau in QUANTILES])

    # Hybrid Residual-CQR + TFT-Q blend (80/20) conformalized
    q_va_hyb = np.sort(0.80 * q_va_cqr + 0.20 * va_tft_q, axis=1)
    q_te_hyb = np.sort(0.80 * q_te_cqr + 0.20 * te_tft_q, axis=1)

    prob_rows = [
        evaluate_probabilistic_forecasts(y_te, q_te_gauss, QUANTILES, hrs_te, "Homoskedastic Gaussian (Baseline)"),
        evaluate_probabilistic_forecasts(y_te, te_tft_q, QUANTILES, hrs_te, "Temporal Fusion Transformer (TFT-Q)"),
        evaluate_probabilistic_forecasts(y_te, q_te_raw, QUANTILES, hrs_te, "Residual LightGBM Quantile (Uncalibrated)"),
        evaluate_probabilistic_forecasts(y_te, q_te_cqr, QUANTILES, hrs_te, "Residual-CQR (Regime Conformalized)"),
        evaluate_probabilistic_forecasts(y_te, q_te_hyb, QUANTILES, hrs_te, "Hybrid Residual-CQR + TFT-Q"),
    ]
    prob_df = pd.DataFrame(prob_rows)
    prob_df.to_csv(TABLE_DIR / "v2_probabilistic_evaluation.csv", index=False)
    print(prob_df[["Probabilistic_Model", "Mean_Pinball_Rs", "CRPS_Rs", "PICP_50_pct", "PICP_80_pct", "PICP_90_pct", "Width_90_Rs", "Winkler_90_Rs", "Spike_PICP_90_pct", "Kupiec_LR_p"]].to_string(index=False))

    # Generate 200 temporally coherent Copula scenarios over the best Residual-CQR distribution
    print("\n[Scenario Engine] Generating 200 temporally correlated 24h Copula scenarios for all 175 test days...")
    scenarios_test = generate_copula_price_scenarios(y_va, q_va_cqr, q_te_cqr, n_scenarios=200)
    n_te_d = len(y_te) // 24
    dates_te = pd.to_datetime(te_df["timestamp"]).dt.strftime("%Y-%m-%d").values[::24][:n_te_d]

    np.savez_compressed(
        PRED_DIR / "v2_test_price_scenarios.npz",
        dates=dates_te, scenarios=scenarios_test,
        actual_24h=y_te[: n_te_d * 24].reshape(n_te_d, 24),
        point_24h=test_preds[champ_name][: n_te_d * 24].reshape(n_te_d, 24),
        lgb_24h=test_preds["LightGBM Regressor"][: n_te_d * 24].reshape(n_te_d, 24),
        snaive_24h=test_preds["Daily S-Naive (24h Ref.)"][: n_te_d * 24].reshape(n_te_d, 24),
        q05_24h=q_te_cqr[: n_te_d * 24, 0].reshape(n_te_d, 24),
        q10_24h=q_te_cqr[: n_te_d * 24, 1].reshape(n_te_d, 24),
        q50_24h=q_te_cqr[: n_te_d * 24, 3].reshape(n_te_d, 24),
        q90_24h=q_te_cqr[: n_te_d * 24, 5].reshape(n_te_d, 24),
        q95_24h=q_te_cqr[: n_te_d * 24, 6].reshape(n_te_d, 24),
    )

    pred_out = pd.DataFrame({
        "timestamp": te_df["timestamp"], "actual_mcp": y_te,
        "pred_snaive_168h": test_preds["Weekly S-Naive (168h)"],
        "pred_snaive_24h": test_preds["Daily S-Naive (24h Ref.)"],
        "pred_sarimax": test_preds["SARIMAX (24-Eq. Seasonal)"],
        "pred_ols": test_preds["OLS Linear Regression"],
        "pred_lasso": test_preds[lasso_key], "pred_enet": test_preds[en_key],
        "pred_ridge": test_preds[ridge_key], "pred_rf": test_preds["Random Forest (220 Trees)"],
        "pred_xgboost": test_preds["XGBoost Regressor"], "pred_catboost": test_preds["CatBoost Regressor"],
        "pred_lightgbm": test_preds["LightGBM Regressor"],
        "pred_nbeats": test_preds["N-BEATS (Multi-Stack Neural)"],
        "pred_tft": test_preds["Temporal Fusion Transformer (TFT)"],
        "pred_champion": test_preds[champ_name], "pred_oracle_exog_lgb": or_te_pred,
    })
    for j, tau in enumerate(QUANTILES):
        pred_out[f"q{int(tau*100):02d}_cqr"] = q_te_cqr[:, j]
    pred_out.to_csv(PRED_DIR / "v2_operational_test_predictions.csv", index=False)

    # -------------------------------------------------------------------------
    # SEASONAL, CALENDAR & EXTREME-EVENT ROBUSTNESS BREAKDOWN
    # -------------------------------------------------------------------------
    print("\n[Robustness Audit] Computing Seasonal, Calendar & Extreme-Event Robustness Breakdown...")
    ts_te = pd.to_datetime(te_df["timestamp"])
    rob_masks = [
        ("Season: Winter (Jan-Feb 2025)", ts_te.dt.month.isin([1, 2]).values),
        ("Season: Spring (Mar-Apr 2025)", ts_te.dt.month.isin([3, 4]).values),
        ("Season: Summer/Monsoon (May-Jun 2025)", ts_te.dt.month.isin([5, 6]).values),
        ("Calendar: Weekdays (Mon-Fri)", (ts_te.dt.dayofweek < 5).values),
        ("Calendar: Weekends (Sat-Sun)", (ts_te.dt.dayofweek >= 5).values),
        ("Diurnal: Night Base (00:00-06:00)", (ts_te.dt.hour <= 6).values),
        ("Diurnal: Solar Trough (09:00-16:00)", ts_te.dt.hour.between(9, 16).values),
        ("Diurnal: Evening Peak (18:00-22:00)", ts_te.dt.hour.isin([18, 19, 20, 21, 22]).values),
        ("Extreme: High-Price Spikes (>=8k)", (y_te >= 8000.0)),
        ("Extreme: CERC Cap Hits (>=9,990)", (y_te >= 9990.0)),
        ("Extreme: Deep Solar Glut (<=2,500)", (y_te <= 2500.0)),
    ]
    rob_rows = []
    for r_name, mk in rob_masks:
        if mk.sum() == 0:
            continue
        m_sn = float(np.mean(np.abs(y_te[mk] - test_preds["Daily S-Naive (24h Ref.)"][mk])))
        m_rd = float(np.mean(np.abs(y_te[mk] - test_preds[ridge_key][mk])))
        m_lg = float(np.mean(np.abs(y_te[mk] - test_preds["LightGBM Regressor"][mk])))
        m_tf = float(np.mean(np.abs(y_te[mk] - test_preds["Temporal Fusion Transformer (TFT)"][mk])))
        m_ch = float(np.mean(np.abs(y_te[mk] - test_preds[champ_name][mk])))
        cov90_sub = float(np.mean((y_te[mk] >= q_te_cqr[mk, 0]) & (y_te[mk] <= q_te_cqr[mk, -1])) * 100.0)
        rob_rows.append({
            "Regime": r_name, "Hours": int(mk.sum()), "Mean_Actual_MCP": round(float(np.mean(y_te[mk])), 1),
            "SNaive24_MAE": round(m_sn, 2), "Ridge_MAE": round(m_rd, 2), "LightGBM_MAE": round(m_lg, 2),
            "TFT_MAE": round(m_tf, 2), "Champion_MAE": round(m_ch, 2),
            "Gain_vs_SNaive_pct": round((m_sn - m_ch) / max(m_sn, 1.0) * 100.0, 1),
            "CQR_PICP90_pct": round(cov90_sub, 1),
        })
    rob_df = pd.DataFrame(rob_rows)
    rob_df.to_csv(TABLE_DIR / "v2_seasonal_and_extreme_robustness.csv", index=False)
    print(rob_df[["Regime", "Hours", "SNaive24_MAE", "Ridge_MAE", "LightGBM_MAE", "Champion_MAE", "Gain_vs_SNaive_pct", "CQR_PICP90_pct"]].to_string(index=False))

    # -------------------------------------------------------------------------
    # EXACT OPERATIONAL D-1 TREESHAP (ON INNOVATION MODEL: DELTA P_{D,h})
    # -------------------------------------------------------------------------
    print("\n[TreeSHAP] Computing Exact Operational D-1 Innovation TreeSHAP...")
    shap_contribs = lgb_last_model.booster_.predict(X_te, pred_contrib=True)
    shap_vals = shap_contribs[:, :-1]
    base_val = float(shap_contribs[0, -1])

    def map_cat(f: str) -> str:
        if f.startswith("mcp_"):
            return "D-1 Published Price Memory"
        if any(k in f for k in ["purchase_bid", "sell_bid", "mcv_", "market_tightness"]):
            return "D-1 Order-Book Liquidity"
        if any(k in f for k in ["demand_", "solar_fcst", "solar_d2", "wind_fcst", "wind_d2", "re_penetration", "net_demand", "nd_fcst"]):
            return "Stage-1 Grid & RE Forecasts"
        if any(k in f for k in ["temp_", "apparent_", "humidity_", "wind_speed_", "precip_", "cdd_"]):
            return "Stage-1 Weather Forecasts"
        return "Calendar & Astronomical"

    shap_rows = []
    for idx, col in enumerate(feature_cols):
        sv = shap_vals[:, idx]
        corr = float(np.corrcoef(X_te[:, idx], sv)[0, 1]) if np.std(X_te[:, idx]) > 1e-8 and np.std(sv) > 1e-8 else 0.0
        shap_rows.append({
            "Feature": col, "Category": map_cat(col),
            "Mean_Abs_SHAP_Rs": round(float(np.mean(np.abs(sv))), 2),
            "Std_SHAP_Rs": round(float(np.std(sv)), 2),
            "Corr_Feature_SHAP": round(corr, 3),
        })
    shap_df = pd.DataFrame(shap_rows).sort_values("Mean_Abs_SHAP_Rs", ascending=False).reset_index(drop=True)
    shap_df.to_csv(TABLE_DIR / "v2_shap_global_importance.csv", index=False)

    cat_df = shap_df.groupby("Category", as_index=False)["Mean_Abs_SHAP_Rs"].sum()
    cat_df["Share_pct"] = (cat_df["Mean_Abs_SHAP_Rs"] / cat_df["Mean_Abs_SHAP_Rs"].sum() * 100.0).round(2)
    cat_df = cat_df.sort_values("Share_pct", ascending=False)
    cat_df.to_csv(TABLE_DIR / "v2_shap_category_summary.csv", index=False)
    print(f"  Innovation TreeSHAP Base E[Delta P] = Rs.{base_val:+.2f}/MWh")
    print("  Top 10 Operational D-1 Innovation Drivers:")
    print(shap_df.head(10).to_string(index=False))
    print("\n  Category Attribution Share (Innovation Target):")
    print(cat_df.to_string(index=False))

    with open(TABLE_DIR / "v2_benchmark_summary.json", "w") as f:
        json.dump({
            "champion_model": champ_name,
            "feature_cols": feature_cols,
            "hybrid_weights": dict(zip(cand_names, best_w)),
            "treeshap_base_innovation": round(base_val, 2),
            "cqr_margins": cqr_margins,
            "val_ridge_alpha": best_ra,
            "val_lasso_alpha": best_la,
            "val_enet_cfg": best_en_cfg,
            "lgb_best_iteration": lgb_best_n,
            "xgb_best_iteration": xgb_best_n,
            "cb_best_iteration": cb_best_n,
        }, f, indent=2)

    print(f"\n[OK] Complete upgraded V2 benchmark + Residual-CQR suite finished in {time.perf_counter() - t0:.1f}s!")


if __name__ == "__main__":
    main()
