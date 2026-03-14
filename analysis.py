"""
Analysis: How interest rate changes relate to inflation trends.
Uses Federal Funds Rate (FEDFUNDS) and CPI (CPIAUCSL) data.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from scipy import stats

# ── Load data ──────────────────────────────────────────────────────────────────
fed = pd.read_csv("FEDFUNDS.csv", parse_dates=["date"]).rename(columns={"value": "fed_rate"})
cpi = pd.read_csv("CPIAUCSL.csv", parse_dates=["date"]).rename(columns={"value": "cpi"})

df = pd.merge(fed, cpi, on="date").sort_values("date").reset_index(drop=True)
df["fed_rate"] = pd.to_numeric(df["fed_rate"], errors="coerce")
df["cpi"] = pd.to_numeric(df["cpi"], errors="coerce")

# YoY CPI inflation rate (%)
df["inflation"] = df["cpi"].pct_change(12) * 100

# Fed rate change vs prior month
df["fed_change"] = df["fed_rate"].diff()

# Fed rate lagged by N months (inflation responds with a delay)
LAG_MONTHS = 12
df["fed_rate_lagged"] = df["fed_rate"].shift(LAG_MONTHS)

df_clean = df.dropna()

# ── Summary statistics ─────────────────────────────────────────────────────────
print("=" * 60)
print("SUMMARY STATISTICS")
print("=" * 60)
print(f"Period: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Observations: {len(df_clean)}\n")

for col, label in [("fed_rate", "Fed Funds Rate (%)"), ("inflation", "YoY Inflation (%)")]:
    s = df_clean[col]
    print(f"{label}")
    print(f"  Mean:  {s.mean():.2f}   Std: {s.std():.2f}")
    print(f"  Min:   {s.min():.2f}   Max: {s.max():.2f}\n")

# ── Correlation analysis ───────────────────────────────────────────────────────
r_contemp, p_contemp = stats.pearsonr(df_clean["fed_rate"], df_clean["inflation"])
r_lagged, p_lagged   = stats.pearsonr(df_clean["fed_rate_lagged"], df_clean["inflation"])

print("=" * 60)
print("CORRELATION ANALYSIS")
print("=" * 60)
print(f"Contemporaneous  r = {r_contemp:.3f}  (p = {p_contemp:.4f})")
print(f"Fed rate lagged {LAG_MONTHS}m  r = {r_lagged:.3f}  (p = {p_lagged:.4f})\n")

# ── Rate-hike / rate-cut cycle detection ──────────────────────────────────────
def label_cycle(rate):
    cycles = []
    for i in range(1, len(rate)):
        if rate.iloc[i] > rate.iloc[i - 1] + 0.1:
            cycles.append("hike")
        elif rate.iloc[i] < rate.iloc[i - 1] - 0.1:
            cycles.append("cut")
        else:
            cycles.append("hold")
    return ["hold"] + cycles

df["cycle"] = label_cycle(df["fed_rate"])

print("=" * 60)
print(f"AVERAGE INFLATION BY FED CYCLE  (lag = {LAG_MONTHS} months)")
print("=" * 60)
for cyc in ["hike", "cut", "hold"]:
    mask = df["cycle"] == cyc
    inf_vals = df.loc[mask, "inflation"].dropna()
    if len(inf_vals):
        print(f"  {cyc.capitalize():5s}: {inf_vals.mean():.2f}%  (n={len(inf_vals)})")

# ── Key episodes ──────────────────────────────────────────────────────────────
episodes = {
    "GFC tightening end":  ("2006-01-01", "2007-09-01"),
    "Post-GFC ZIRP":       ("2009-01-01", "2015-12-01"),
    "2015-2018 hike cycle":("2015-12-01", "2019-07-01"),
    "COVID cuts":          ("2020-03-01", "2022-02-01"),
    "2022-2023 hikes":     ("2022-03-01", "2023-12-01"),
}

print("\n" + "=" * 60)
print("KEY EPISODE AVERAGES")
print("=" * 60)
print(f"{'Episode':<26} {'Avg Fed Rate':>12} {'Avg Inflation':>14}")
print("-" * 60)
for name, (start, end) in episodes.items():
    mask = (df["date"] >= start) & (df["date"] <= end)
    avg_fed = df.loc[mask, "fed_rate"].mean()
    avg_inf = df.loc[mask, "inflation"].mean()
    if not np.isnan(avg_fed):
        print(f"{name:<26} {avg_fed:>11.2f}% {avg_inf:>13.2f}%")

# ── Plots ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(13, 14), sharex=False)
fig.suptitle("Federal Funds Rate vs. CPI Inflation (20-Year Analysis)", fontsize=14, fontweight="bold")

# Plot 1: dual-axis time series
ax1 = axes[0]
ax1b = ax1.twinx()
ax1.plot(df["date"], df["fed_rate"], color="#1f77b4", lw=1.8, label="Fed Funds Rate")
ax1b.plot(df["date"], df["inflation"], color="#d62728", lw=1.8, alpha=0.85, label="YoY Inflation")
ax1.set_ylabel("Fed Funds Rate (%)", color="#1f77b4")
ax1b.set_ylabel("YoY Inflation (%)", color="#d62728")
ax1.set_title("Interest Rate & Inflation Over Time")
lines = ax1.get_lines() + ax1b.get_lines()
ax1.legend(lines, [l.get_label() for l in lines], loc="upper right")
ax1.grid(True, alpha=0.3)

# Shade episodes
shades = [("2022-03-01", "2023-12-01", "#ffe0b2", "2022-23 hikes"),
          ("2009-01-01", "2015-12-01", "#e3f2fd", "ZIRP era")]
for s, e, color, lbl in shades:
    ax1.axvspan(pd.Timestamp(s), pd.Timestamp(e), color=color, alpha=0.4, label=lbl)

# Plot 2: scatter with regression (lagged)
ax2 = axes[1]
x, y = df_clean["fed_rate_lagged"], df_clean["inflation"]
slope, intercept, *_ = stats.linregress(x, y)
x_line = np.linspace(x.min(), x.max(), 200)
ax2.scatter(x, y, alpha=0.35, s=18, color="#2ca02c")
ax2.plot(x_line, slope * x_line + intercept, color="black", lw=1.5, label=f"OLS  r={r_lagged:.2f}")
ax2.set_xlabel(f"Fed Funds Rate ({LAG_MONTHS}m lag, %)")
ax2.set_ylabel("YoY Inflation (%)")
ax2.set_title(f"Scatter: Lagged Fed Rate vs. Inflation (lag = {LAG_MONTHS} months)")
ax2.legend()
ax2.grid(True, alpha=0.3)

# Plot 3: rolling 24-month correlation
ax3 = axes[2]
rolling_corr = (
    df_clean.set_index("date")[["fed_rate", "inflation"]]
    .rolling(24)
    .corr()
    .unstack()["fed_rate"]["inflation"]
)
ax3.plot(rolling_corr.index, rolling_corr.values, color="#9467bd", lw=1.8)
ax3.axhline(0, color="black", lw=0.8, linestyle="--")
ax3.fill_between(rolling_corr.index, rolling_corr.values, 0,
                 where=(rolling_corr.values > 0), alpha=0.2, color="#9467bd", label="Positive")
ax3.fill_between(rolling_corr.index, rolling_corr.values, 0,
                 where=(rolling_corr.values < 0), alpha=0.2, color="#d62728", label="Negative")
ax3.set_ylabel("Pearson r")
ax3.set_title("Rolling 24-Month Correlation: Fed Rate vs. Inflation")
ax3.set_ylim(-1, 1)
ax3.legend()
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("analysis_chart.png", dpi=150, bbox_inches="tight")
print("\nChart saved -> analysis_chart.png")
plt.show()
