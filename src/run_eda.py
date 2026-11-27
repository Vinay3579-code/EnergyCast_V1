"""
EnergyCast V1 — Step 6: Exploratory Data Analysis (EDA)
Comprehensive statistical analysis and visualization generator for the Indian Electricity Market.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from scipy import stats
import seaborn as sns
from statsmodels.tsa.stattools import acf, pacf

# Configure paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "master" / "energycast_master_hourly_2022_2025.csv"
FIG_DIR = PROJECT_ROOT / "outputs" / "figures" / "eda"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)

# Set visual style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "axes.edgecolor": "#CCCCCC",
    "axes.linewidth": 0.8,
    "grid.color": "#E5E5E5",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
    "figure.autolayout": True,
    "figure.dpi": 300
})

PRIMARY_COLOR = "#1F4E79"
ACCENT_COLOR = "#D9534F"
SECONDARY_COLOR = "#2E75B6"
GOLD_COLOR = "#E67E22"
GREEN_COLOR = "#27AE60"

def load_and_prepare_data():
    print(f"Loading master dataset from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Calendar & cyclical features for EDA
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["day_name"] = df["timestamp"].dt.day_name()
    df["month"] = df["timestamp"].dt.month
    df["month_name"] = df["timestamp"].dt.month_name()
    df["year"] = df["timestamp"].dt.year
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    # Power System metrics
    df["net_demand_mw"] = df["demand_mw"] - (df["solar_generation_mw"] + df["wind_generation_mw"])
    df["total_re_generation_mw"] = df["solar_generation_mw"] + df["wind_generation_mw"]
    df["re_penetration_pct"] = (df["total_re_generation_mw"] / df["demand_mw"]) * 100
    
    print(f"Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")
    print(f"Timeline: {df['timestamp'].min()} to {df['timestamp'].max()}")
    return df

def generate_statistical_summaries(df):
    print("Generating comprehensive statistical summaries...")
    mcp = df["mcp_rs_per_mwh"]
    
    # Target variable statistics
    q25, q50, q75 = mcp.quantile([0.25, 0.50, 0.75])
    iqr = q75 - q25
    
    stats_dict = {
        "Metric": [
            "Observations (count)",
            "Mean (Rs/MWh)",
            "Standard Deviation (Rs/MWh)",
            "Median (Rs/MWh)",
            "Minimum (Rs/MWh)",
            "25th Percentile (Q1) (Rs/MWh)",
            "75th Percentile (Q3) (Rs/MWh)",
            "Interquartile Range (IQR)",
            "90th Percentile (Rs/MWh)",
            "95th Percentile (Rs/MWh)",
            "99th Percentile (Rs/MWh)",
            "Maximum (Rs/MWh)",
            "Skewness (Fisher-Pearson)",
            "Kurtosis (Excess)",
            "Regulatory Cap Hits (>= Rs 10,000)",
            "Cap Hit Percentage (%)",
            "Severe Spikes (>= Rs 12,000)",
            "Historical Cap Hits (== Rs 20,000)"
        ],
        "Value": [
            f"{len(mcp):,}",
            f"{mcp.mean():.2f}",
            f"{mcp.std():.2f}",
            f"{q50:.2f}",
            f"{mcp.min():.2f}",
            f"{q25:.2f}",
            f"{q75:.2f}",
            f"{iqr:.2f}",
            f"{mcp.quantile(0.90):.2f}",
            f"{mcp.quantile(0.95):.2f}",
            f"{mcp.quantile(0.99):.2f}",
            f"{mcp.max():.2f}",
            f"{stats.skew(mcp):.4f}",
            f"{stats.kurtosis(mcp):.4f}",
            f"{(mcp >= 10000).sum():,}",
            f"{(mcp >= 10000).mean() * 100:.2f}%",
            f"{(mcp >= 12000).sum():,}",
            f"{(mcp == 20000).sum():,}"
        ]
    }
    stats_df = pd.DataFrame(stats_dict)
    stats_df.to_csv(TABLE_DIR / "eda_mcp_statistical_summary.csv", index=False)
    
    # Year-wise statistics
    yearly_df = df.groupby("year")["mcp_rs_per_mwh"].agg([
        ("Count", "count"),
        ("Mean", "mean"),
        ("Median", "median"),
        ("Std", "std"),
        ("Min", "min"),
        ("Max", "max"),
        ("P95", lambda x: x.quantile(0.95)),
        ("Cap_Hits_10k", lambda x: (x >= 10000).sum())
    ]).reset_index()
    yearly_df.to_csv(TABLE_DIR / "eda_mcp_yearly_summary.csv", index=False)
    
    # Core system variables summary
    system_cols = [
        "mcp_rs_per_mwh", "demand_mw", "net_demand_mw", "solar_generation_mw", 
        "wind_generation_mw", "temperature_mean_c", "humidity_mean_pct"
    ]
    core_summary = df[system_cols].describe().T
    core_summary["skewness"] = df[system_cols].apply(stats.skew)
    core_summary["kurtosis"] = df[system_cols].apply(stats.kurtosis)
    core_summary.to_csv(TABLE_DIR / "eda_core_system_variables_summary.csv")

    # Correlations table
    corr_p = df.corr(numeric_only=True)["mcp_rs_per_mwh"]
    corr_s = df.corr(numeric_only=True, method="spearman")["mcp_rs_per_mwh"]
    corr_df = pd.DataFrame({
        "Variable": corr_p.index,
        "Pearson_r": corr_p.values,
        "Spearman_rho": corr_s.values
    }).sort_values(by="Spearman_rho", ascending=False)
    corr_df.to_csv(TABLE_DIR / "eda_mcp_correlation_rankings.csv", index=False)
    
    print("Statistical summaries saved to:", TABLE_DIR)

def plot_fig1_mcp_timeseries_overview(df):
    print("Generating Figure 1: Full MCP Time Series Overview...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})
    
    # MCP series with 7-day rolling mean
    rolling_7d = df["mcp_rs_per_mwh"].rolling(168).mean()
    
    ax1.plot(df["timestamp"], df["mcp_rs_per_mwh"], color="#A0C4DF", alpha=0.45, linewidth=0.5, label="Hourly MCP")
    ax1.plot(df["timestamp"], rolling_7d, color=PRIMARY_COLOR, linewidth=1.8, label="7-Day Rolling Mean MCP (168-hr)")
    
    # Horizontal regulatory cap lines
    ax1.axhline(10000, color=ACCENT_COLOR, linestyle="--", linewidth=1.2, alpha=0.85, label="Current CERC Cap (Rs 10,000/MWh)")
    ax1.axhline(12000, color="#8E44AD", linestyle=":", linewidth=1.2, alpha=0.85, label="2022-2023 Cap (Rs 12,000/MWh)")
    
    ax1.set_ylabel("Market Clearing Price (Rs/MWh)")
    ax1.set_title("Figure 1A: IEX Day-Ahead Market Hourly MCP Time Series (April 2022 – June 2025)", fontweight="bold")
    ax1.legend(loc="upper right", frameon=True)
    ax1.set_ylim(0, 21000)
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # Subplot 2: 7-day rolling standard deviation (Volatility)
    rolling_vol_7d = df["mcp_rs_per_mwh"].rolling(168).std()
    ax2.plot(df["timestamp"], rolling_vol_7d, color=GOLD_COLOR, linewidth=1.2, label="7-Day Rolling Price Volatility (Std Dev)")
    ax2.set_ylabel("Volatility (Rs/MWh)")
    ax2.set_xlabel("Date")
    ax2.set_title("Figure 1B: Market Price Volatility Regime (7-Day Rolling Standard Deviation)", fontweight="bold")
    ax2.legend(loc="upper right", frameon=True)
    ax2.set_ylim(0, 5000)
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig01_mcp_timeseries_overview.png", dpi=300)
    plt.close(fig)

def plot_fig2_mcp_distribution_and_spikes(df):
    print("Generating Figure 2: MCP Distribution and Spike Dynamics...")
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    mcp = df["mcp_rs_per_mwh"]
    
    # 2A: Histogram with KDE and Mean/Median markers
    sns.histplot(mcp, bins=70, kde=True, color=SECONDARY_COLOR, ax=axes[0], edgecolor="white", alpha=0.6)
    axes[0].axvline(mcp.mean(), color=ACCENT_COLOR, linestyle="--", linewidth=1.6, label=f"Mean: Rs {mcp.mean():,.0f}")
    axes[0].axvline(mcp.median(), color=GREEN_COLOR, linestyle="-", linewidth=1.6, label=f"Median: Rs {mcp.median():,.0f}")
    axes[0].axvline(10000, color="#8E44AD", linestyle=":", linewidth=1.6, label="Cap: Rs 10,000")
    axes[0].set_title("Figure 2A: MCP Distribution & Positive Skew", fontweight="bold")
    axes[0].set_xlabel("MCP (Rs/MWh)")
    axes[0].set_ylabel("Frequency (Hours)")
    axes[0].legend(frameon=True)
    axes[0].xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 2B: Year-wise Boxplot showing cap shifts
    sns.boxplot(x="year", y="mcp_rs_per_mwh", data=df, palette="Blues", ax=axes[1], flierprops={"marker": ".", "markersize": 2, "alpha": 0.3})
    axes[1].axhline(10000, color=ACCENT_COLOR, linestyle="--", linewidth=1.2, alpha=0.7)
    axes[1].set_title("Figure 2B: Annual Price Spread & Cap Saturation", fontweight="bold")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("MCP (Rs/MWh)")
    axes[1].yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 2C: Quantile-Quantile (Q-Q) Plot vs Normal Distribution
    (osm, osr), (slope, intercept, r) = stats.probplot(mcp, dist="norm")
    axes[2].scatter(osm, osr, s=4, color=PRIMARY_COLOR, alpha=0.3, label="Observed Quantiles")
    axes[2].plot(osm, slope * np.array(osm) + intercept, color=ACCENT_COLOR, linewidth=1.5, label="Theoretical Normal")
    axes[2].set_title(f"Figure 2C: Normal Q-Q Plot (Skew={stats.skew(mcp):.2f})", fontweight="bold")
    axes[2].set_xlabel("Theoretical Quantiles")
    axes[2].set_ylabel("Sample Quantiles (Rs/MWh)")
    axes[2].legend(frameon=True)
    axes[2].yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig02_mcp_distribution_and_spikes.png", dpi=300)
    plt.close(fig)

def plot_fig3_hourly_diurnal_profiles(df):
    print("Generating Figure 3: Hourly Diurnal Profiles...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    hourly_stats = df.groupby("hour").agg({
        "mcp_rs_per_mwh": ["mean", "median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)],
        "demand_mw": "mean",
        "solar_generation_mw": "mean",
        "wind_generation_mw": "mean",
        "net_demand_mw": "mean"
    })
    hours = np.arange(24)
    
    # 3A: MCP Diurnal Profile (Mean, Median, IQR)
    mcp_mean = hourly_stats["mcp_rs_per_mwh"]["mean"]
    mcp_med = hourly_stats["mcp_rs_per_mwh"]["median"]
    mcp_q25 = hourly_stats["mcp_rs_per_mwh"]["<lambda_0>"]
    mcp_q75 = hourly_stats["mcp_rs_per_mwh"]["<lambda_1>"]
    
    axes[0, 0].plot(hours, mcp_mean, color=ACCENT_COLOR, marker="o", linewidth=2, label="Mean MCP")
    axes[0, 0].plot(hours, mcp_med, color=PRIMARY_COLOR, marker="s", linestyle="--", linewidth=1.5, label="Median MCP")
    axes[0, 0].fill_between(hours, mcp_q25, mcp_q75, color=PRIMARY_COLOR, alpha=0.15, label="IQR (25th-75th)")
    axes[0, 0].set_title("Figure 3A: Diurnal Hourly MCP Pattern (Peak Spikes)", fontweight="bold")
    axes[0, 0].set_xlabel("Hour of Day (0 to 23)")
    axes[0, 0].set_ylabel("Price (Rs/MWh)")
    axes[0, 0].set_xticks(range(0, 24, 2))
    axes[0, 0].legend(frameon=True)
    axes[0, 0].yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 3B: Electricity Demand vs Net Demand Diurnal Profile
    axes[0, 1].plot(hours, hourly_stats["demand_mw"]["mean"] / 1000, color="#2C3E50", linewidth=2, marker="o", label="Gross Demand (GW)")
    axes[0, 1].plot(hours, hourly_stats["net_demand_mw"]["mean"] / 1000, color="#E67E22", linewidth=2, linestyle="--", marker="^", label="Net Demand (GW)")
    axes[0, 1].fill_between(hours, hourly_stats["net_demand_mw"]["mean"] / 1000, hourly_stats["demand_mw"]["mean"] / 1000, color=GOLD_COLOR, alpha=0.2, label="RE Displacement")
    axes[0, 1].set_title("Figure 3B: Gross vs. Net Demand (Duck Belly)", fontweight="bold")
    axes[0, 1].set_xlabel("Hour of Day")
    axes[0, 1].set_ylabel("Power (Gigawatts - GW)")
    axes[0, 1].set_xticks(range(0, 24, 2))
    axes[0, 1].legend(frameon=True)
    
    # 3C: Solar Generation Curve
    axes[1, 0].plot(hours, hourly_stats["solar_generation_mw"]["mean"] / 1000, color="#F39C12", linewidth=2.2, marker="o", label="Mean Solar (GW)")
    axes[1, 0].fill_between(hours, 0, hourly_stats["solar_generation_mw"]["mean"] / 1000, color="#F39C12", alpha=0.25)
    axes[1, 0].set_title("Figure 3C: Diurnal Solar Generation (Midday Peak)", fontweight="bold")
    axes[1, 0].set_xlabel("Hour of Day")
    axes[1, 0].set_ylabel("Solar Generation (GW)")
    axes[1, 0].set_xticks(range(0, 24, 2))
    axes[1, 0].legend(frameon=True)
    
    # 3D: Wind Generation Curve
    axes[1, 1].plot(hours, hourly_stats["wind_generation_mw"]["mean"] / 1000, color="#16A085", linewidth=2.2, marker="o", label="Mean Wind (GW)")
    axes[1, 1].fill_between(hours, 0, hourly_stats["wind_generation_mw"]["mean"] / 1000, color="#16A085", alpha=0.2)
    axes[1, 1].set_title("Figure 3D: Diurnal Wind Generation Profile", fontweight="bold")
    axes[1, 1].set_xlabel("Hour of Day")
    axes[1, 1].set_ylabel("Wind Generation (GW)")
    axes[1, 1].set_xticks(range(0, 24, 2))
    axes[1, 1].legend(frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig03_hourly_diurnal_profiles.png", dpi=300)
    plt.close(fig)

def plot_fig4_weekly_and_monthly_seasonality(df):
    print("Generating Figure 4: Weekly & Monthly Seasonality...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_summary = df.groupby("day_name")["mcp_rs_per_mwh"].agg(["mean", "median"]).reindex(day_order)
    
    # 4A: Weekday vs Weekend Price
    x_days = np.arange(len(day_order))
    width = 0.35
    ax1.bar(x_days - width/2, weekday_summary["mean"], width, label="Mean MCP", color=PRIMARY_COLOR, alpha=0.85)
    ax1.bar(x_days + width/2, weekday_summary["median"], width, label="Median MCP", color=SECONDARY_COLOR, alpha=0.7)
    ax1.set_xticks(x_days)
    ax1.set_xticklabels(day_order, rotation=25)
    ax1.set_title("Figure 4A: Day-of-Week Price Patterns (Weekday vs Weekend)", fontweight="bold")
    ax1.set_ylabel("Price (Rs/MWh)")
    ax1.legend(frameon=True)
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 4B: Monthly Seasonality
    month_order = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    monthly_summary = df.groupby("month_name").agg({
        "mcp_rs_per_mwh": "mean",
        "demand_mw": lambda x: x.mean() / 1000
    }).reindex(month_order)
    
    ax2_twin = ax2.twinx()
    p1 = ax2.plot(range(12), monthly_summary["mcp_rs_per_mwh"], color=ACCENT_COLOR, marker="o", linewidth=2.2, label="Mean MCP (Rs/MWh)")
    p2 = ax2_twin.plot(range(12), monthly_summary["demand_mw"], color="#27AE60", marker="s", linestyle="--", linewidth=2, label="Mean Demand (GW)")
    
    ax2.set_xticks(range(12))
    ax2.set_xticklabels([m[:3] for m in month_order])
    ax2.set_title("Figure 4B: Annual Monthly Seasonality (Summer Peaks)", fontweight="bold")
    ax2.set_ylabel("MCP (Rs/MWh)", color=ACCENT_COLOR)
    ax2_twin.set_ylabel("National Demand (GW)", color="#27AE60")
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2_twin.grid(False)
    
    lines = p1 + p2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc="upper right", frameon=True)
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig04_weekly_and_monthly_seasonality.png", dpi=300)
    plt.close(fig)

def plot_fig5_heatmaps(df):
    print("Generating Figure 5: Seasonal Heatmaps...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 5A: Hour of Day vs Month of Year Heatmap
    pivot_hour_month = df.pivot_table(index="hour", columns="month", values="mcp_rs_per_mwh", aggfunc="mean")
    sns.heatmap(pivot_hour_month, cmap="YlOrRd", ax=ax1, cbar_kws={'label': 'Mean MCP (Rs/MWh)'}, fmt=".0f")
    ax1.set_title("Figure 5A: Hourly-Monthly MCP Intensity Matrix", fontweight="bold")
    ax1.set_xlabel("Month of Year (1=Jan, 12=Dec)")
    ax1.set_ylabel("Hour of Day (0 to 23)")
    ax1.invert_yaxis()
    
    # 5B: Hour of Day vs Day of Week Heatmap
    day_abbr = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    pivot_hour_day = df.pivot_table(index="hour", columns="day_of_week", values="mcp_rs_per_mwh", aggfunc="mean")
    sns.heatmap(pivot_hour_day, cmap="YlOrRd", ax=ax2, cbar_kws={'label': 'Mean MCP (Rs/MWh)'}, fmt=".0f")
    ax2.set_title("Figure 5B: Hourly-DayOfWeek MCP Intensity Matrix", fontweight="bold")
    ax2.set_xlabel("Day of Week")
    ax2.set_xticklabels(day_abbr)
    ax2.set_ylabel("Hour of Day")
    ax2.invert_yaxis()
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig05_heatmaps_hour_month_weekday.png", dpi=300)
    plt.close(fig)

def plot_fig6_merit_order_and_duck_curve(df):
    print("Generating Figure 6: Merit-Order Effect & Duck Curve Dynamics...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 6A: Duck Curve & MCP Inversion
    hourly_avg = df.groupby("hour").agg({
        "demand_mw": lambda x: x.mean() / 1000,
        "net_demand_mw": lambda x: x.mean() / 1000,
        "solar_generation_mw": lambda x: x.mean() / 1000,
        "mcp_rs_per_mwh": "mean"
    })
    
    ax1_twin = ax1.twinx()
    l1 = ax1.plot(hourly_avg.index, hourly_avg["demand_mw"], color="#2C3E50", linewidth=2.2, label="Gross Demand (GW)")
    l2 = ax1.plot(hourly_avg.index, hourly_avg["net_demand_mw"], color="#E67E22", linewidth=2.2, linestyle="--", label="Net Demand (Duck Curve)")
    l3 = ax1.plot(hourly_avg.index, hourly_avg["solar_generation_mw"], color="#F1C40F", linewidth=2, label="Solar Generation (GW)")
    l4 = ax1_twin.plot(hourly_avg.index, hourly_avg["mcp_rs_per_mwh"], color=ACCENT_COLOR, linewidth=2.5, marker="o", label="MCP (Rs/MWh)")
    
    ax1.set_xlabel("Hour of Day (0 to 23)")
    ax1.set_ylabel("Power Capacity (GW)")
    ax1_twin.set_ylabel("Market Clearing Price (Rs/MWh)", color=ACCENT_COLOR)
    ax1.set_title("Figure 6A: The Duck Curve & Evening Price Spike Inversion", fontweight="bold")
    ax1.set_xticks(range(0, 24, 2))
    
    lines1 = l1 + l2 + l3 + l4
    labels1 = [l.get_label() for l in lines1]
    ax1.legend(lines1, labels1, loc="upper left", frameon=True, fontsize=9)
    ax1_twin.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 6B: Merit-Order Effect: Solar Generation vs Midday MCP (Hours 10 to 15)
    midday_df = df[df["hour"].between(10, 15)]
    sns.regplot(
        x=midday_df["solar_generation_mw"] / 1000, 
        y=midday_df["mcp_rs_per_mwh"], 
        ax=ax2, 
        scatter_kws={"alpha": 0.15, "color": "#F39C12", "s": 10}, 
        line_kws={"color": ACCENT_COLOR, "linewidth": 2}
    )
    ax2.set_title("Figure 6B: Midday Merit-Order Effect (Solar vs MCP 10:00-15:00)", fontweight="bold")
    ax2.set_xlabel("Solar Generation (GW)")
    ax2.set_ylabel("MCP (Rs/MWh)")
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    corr_solar_midday = midday_df["solar_generation_mw"].corr(midday_df["mcp_rs_per_mwh"])
    ax2.annotate(f"Midday r = {corr_solar_midday:.3f}", xy=(0.05, 0.90), xycoords="axes fraction", 
                 fontsize=11, fontweight="bold", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig06_merit_order_and_duck_curve.png", dpi=300)
    plt.close(fig)

def plot_fig7_scatter_dynamics(df):
    print("Generating Figure 7: Scatter Dynamics (Gross vs Net Demand vs MCP)...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 7A: Gross Demand vs MCP
    sample_df = df.sample(n=6000, random_state=42)  # Representative subsample for scannability
    ax1.scatter(sample_df["demand_mw"] / 1000, sample_df["mcp_rs_per_mwh"], alpha=0.2, color=SECONDARY_COLOR, s=8)
    # Regression line
    sns.regplot(x=sample_df["demand_mw"] / 1000, y=sample_df["mcp_rs_per_mwh"], ax=ax1, scatter=False, color=ACCENT_COLOR)
    ax1.set_title("Figure 7A: Gross Demand vs MCP (r = +0.252)", fontweight="bold")
    ax1.set_xlabel("Gross National Demand (GW)")
    ax1.set_ylabel("MCP (Rs/MWh)")
    ax1.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # 7B: Net Demand vs MCP
    ax2.scatter(sample_df["net_demand_mw"] / 1000, sample_df["mcp_rs_per_mwh"], alpha=0.2, color="#8E44AD", s=8)
    sns.regplot(x=sample_df["net_demand_mw"] / 1000, y=sample_df["mcp_rs_per_mwh"], ax=ax2, scatter=False, color=ACCENT_COLOR)
    ax2.set_title("Figure 7B: Net Demand vs MCP (r = +0.620, rho = +0.685)", fontweight="bold")
    ax2.set_xlabel("Net National Demand (Demand - Solar - Wind) (GW)")
    ax2.set_ylabel("MCP (Rs/MWh)")
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig07_scatter_demand_netdemand_renewables_vs_mcp.png", dpi=300)
    plt.close(fig)

def plot_fig8_weather_cooling_curve(df):
    print("Generating Figure 8: Weather Temperature vs Demand Non-Linearity...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 8A: Temperature vs Gross Demand (Hockey-stick / U-shape)
    sns.regplot(
        x=df["temperature_mean_c"], 
        y=df["demand_mw"] / 1000, 
        ax=ax1, 
        order=2,  # Polynomial order 2 to show non-linear cooling curve
        scatter_kws={"alpha": 0.15, "color": PRIMARY_COLOR, "s": 6},
        line_kws={"color": ACCENT_COLOR, "linewidth": 2.2}
    )
    ax1.set_title("Figure 8A: National Temperature vs Gross Demand (Cooling Elasticity)", fontweight="bold")
    ax1.set_xlabel("National Mean Temperature (°C)")
    ax1.set_ylabel("National Demand (GW)")
    
    # 8B: Temperature vs Net Demand
    sns.regplot(
        x=df["temperature_mean_c"], 
        y=df["mcp_rs_per_mwh"], 
        ax=ax2, 
        order=2,
        scatter_kws={"alpha": 0.15, "color": GOLD_COLOR, "s": 6},
        line_kws={"color": ACCENT_COLOR, "linewidth": 2.2}
    )
    ax2.set_title("Figure 8B: National Temperature vs Market Clearing Price", fontweight="bold")
    ax2.set_xlabel("National Mean Temperature (°C)")
    ax2.set_ylabel("MCP (Rs/MWh)")
    ax2.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig08_weather_temperature_vs_demand_cooling_curve.png", dpi=300)
    plt.close(fig)

def plot_fig9_acf_pacf(df):
    print("Generating Figure 9: ACF and PACF Time Series Memory...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    
    mcp = df["mcp_rs_per_mwh"]
    nlags = 168 # 7 days of hourly memory
    
    acf_vals = acf(mcp, nlags=nlags)
    pacf_vals = pacf(mcp, nlags=nlags)
    lags = np.arange(nlags + 1)
    
    # 9A: Autocorrelation Function (ACF)
    ax1.stem(lags, acf_vals, linefmt="#2E75B6", markerfmt="o", basefmt="k-")
    ax1.axhline(0, color="gray", linewidth=0.8)
    ax1.axhline(1.96 / np.sqrt(len(mcp)), color=ACCENT_COLOR, linestyle="--", linewidth=1, label="95% Significance Threshold")
    ax1.axhline(-1.96 / np.sqrt(len(mcp)), color=ACCENT_COLOR, linestyle="--", linewidth=1)
    ax1.set_title("Figure 9A: Autocorrelation Function (ACF) of MCP (168 Hours / 7 Days)", fontweight="bold")
    ax1.set_ylabel("ACF Coefficient")
    ax1.legend(loc="upper right", frameon=True)
    
    # Annotate key seasonal spikes: Lag 1, Lag 24, Lag 48, Lag 168
    for target_lag in [1, 24, 48, 168]:
        val = acf_vals[target_lag]
        ax1.annotate(f"Lag {target_lag}\n({val:.2f})", xy=(target_lag, val), xytext=(target_lag, val + 0.12),
                     arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
                     ha="center", fontsize=8, fontweight="bold")
        
    # 9B: Partial Autocorrelation Function (PACF)
    ax2.stem(lags, pacf_vals, linefmt="#E67E22", markerfmt="s", basefmt="k-")
    ax2.axhline(0, color="gray", linewidth=0.8)
    ax2.axhline(1.96 / np.sqrt(len(mcp)), color=ACCENT_COLOR, linestyle="--", linewidth=1, label="95% Significance Threshold")
    ax2.axhline(-1.96 / np.sqrt(len(mcp)), color=ACCENT_COLOR, linestyle="--", linewidth=1)
    ax2.set_title("Figure 9B: Partial Autocorrelation Function (PACF) of MCP", fontweight="bold")
    ax2.set_ylabel("PACF Coefficient")
    ax2.set_xlabel("Lag (Hours)")
    ax2.legend(loc="upper right", frameon=True)
    
    # Annotate key PACF spikes: Lag 1, Lag 2, Lag 24, Lag 25
    for target_lag in [1, 2, 24]:
        val = pacf_vals[target_lag]
        ax2.annotate(f"Lag {target_lag}\n({val:.2f})", xy=(target_lag, val), xytext=(target_lag, val + 0.15),
                     arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
                     ha="center", fontsize=8, fontweight="bold")
        
    ax2.set_xticks(range(0, nlags + 1, 12))
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig09_acf_pacf_time_series_memory.png", dpi=300)
    plt.close(fig)

def plot_fig10_correlation_matrix(df):
    print("Generating Figure 10: Correlation Heatmaps...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    cols = [
        "mcp_rs_per_mwh", "purchase_bid_mwh", "sell_bid_mwh", "mcv_mwh",
        "demand_mw", "net_demand_mw", "solar_generation_mw", "wind_generation_mw",
        "temperature_mean_c", "humidity_mean_pct", "weather_wind_speed_mean_ms"
    ]
    labels = [
        "MCP", "Purchase Bids", "Sell Bids", "MCV",
        "Demand", "Net Demand", "Solar Gen", "Wind Gen",
        "Mean Temp", "Humidity", "Wind Speed"
    ]
    
    p_corr = df[cols].corr()
    s_corr = df[cols].corr(method="spearman")
    
    mask = np.triu(np.ones_like(p_corr, dtype=bool))
    
    sns.heatmap(p_corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax1, 
                xticklabels=labels, yticklabels=labels, cbar_kws={'label': 'Pearson r'}, annot_kws={"size": 8.5})
    ax1.set_title("Figure 10A: Pearson Linear Correlation Matrix", fontweight="bold")
    
    sns.heatmap(s_corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax2, 
                xticklabels=labels, yticklabels=labels, cbar_kws={'label': 'Spearman rho'}, annot_kws={"size": 8.5})
    ax2.set_title("Figure 10B: Spearman Rank (Non-Linear) Correlation Matrix", fontweight="bold")
    
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig10_correlation_matrix_pearson_spearman.png", dpi=300)
    plt.close(fig)

def run_all():
    print("===========================================================================")
    print("STARTING ENERGYCAST V1 — STEP 6: EXPLORATORY DATA ANALYSIS (EDA)")
    print("===========================================================================")
    df = load_and_prepare_data()
    generate_statistical_summaries(df)
    plot_fig1_mcp_timeseries_overview(df)
    plot_fig2_mcp_distribution_and_spikes(df)
    plot_fig3_hourly_diurnal_profiles(df)
    plot_fig4_weekly_and_monthly_seasonality(df)
    plot_fig5_heatmaps(df)
    plot_fig6_merit_order_and_duck_curve(df)
    plot_fig7_scatter_dynamics(df)
    plot_fig8_weather_cooling_curve(df)
    plot_fig9_acf_pacf(df)
    plot_fig10_correlation_matrix(df)
    print("===========================================================================")
    print("STEP 6 EDA ANALYSIS COMPLETED SUCCESSFULLY!")
    print(f"All figures generated in: {FIG_DIR}")
    print(f"All statistical tables generated in: {TABLE_DIR}")
    print("===========================================================================")

if __name__ == "__main__":
    run_all()
