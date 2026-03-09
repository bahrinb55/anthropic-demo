"""
Analysis: Federal Funds Rate vs CPI Inflation (2006-2026)
Explores how interest rate changes relate to inflation trends.
"""

import json
import csv
import os
from datetime import datetime, date

# ── Load raw data ─────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))

def load_observations(path):
    with open(path) as f:
        data = json.load(f)
    rows = []
    for o in data["observations"]:
        try:
            rows.append((datetime.strptime(o["date"], "%Y-%m-%d").date(), float(o["value"])))
        except ValueError:
            pass  # skip "." missing values
    return rows

fedfunds = load_observations(os.path.join(BASE, "fedfunds_raw.json"))
cpi_raw  = load_observations(os.path.join(BASE, "cpiaucsl_raw.json"))

# ── Compute YoY CPI inflation from CPI index ──────────────────────────────────
cpi_dict = {d: v for d, v in cpi_raw}
inflation = []
for d, v in cpi_raw:
    prev = date(d.year - 1, d.month, d.day)
    if prev in cpi_dict:
        yoy = (v - cpi_dict[prev]) / cpi_dict[prev] * 100
        inflation.append((d, round(yoy, 4)))

# ── Build aligned dataset (inner join on date) ────────────────────────────────
fed_dict = {d: v for d, v in fedfunds}
inf_dict = {d: v for d, v in inflation}
common_dates = sorted(set(fed_dict) & set(inf_dict))

dates     = [d for d in common_dates]
fed_vals  = [fed_dict[d] for d in common_dates]
inf_vals  = [inf_dict[d] for d in common_dates]

# ── Save combined CSV ─────────────────────────────────────────────────────────
csv_path = os.path.join(BASE, "fed_vs_inflation.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "fedfunds_pct", "cpi_yoy_pct"])
    for d, ff, inf in zip(dates, fed_vals, inf_vals):
        w.writerow([d, ff, inf])
print(f"Saved combined CSV: {csv_path}")

# ── Statistics ────────────────────────────────────────────────────────────────
def stats(name, vals):
    mn, mx, avg = min(vals), max(vals), sum(vals)/len(vals)
    print(f"  {name:20s}  min={mn:6.2f}%  max={mx:6.2f}%  avg={avg:6.2f}%")

print("\n=== Descriptive Statistics (2006-2026) ===")
stats("Fed Funds Rate", fed_vals)
stats("CPI Inflation (YoY)", inf_vals)

# ── Correlation ───────────────────────────────────────────────────────────────
n = len(dates)
mean_f = sum(fed_vals) / n
mean_i = sum(inf_vals) / n
cov = sum((f - mean_f)*(i - mean_i) for f, i in zip(fed_vals, inf_vals)) / n
std_f = (sum((f - mean_f)**2 for f in fed_vals) / n) ** 0.5
std_i = (sum((i - mean_i)**2 for i in inf_vals) / n) ** 0.5
corr  = cov / (std_f * std_i)
print(f"\n  Pearson Correlation (contemporaneous): {corr:.3f}")

# Lagged correlations (Fed leads inflation by 6/12/18/24 months)
def lagged_corr(x, y, lag):
    x2, y2 = x[:-lag], y[lag:]
    mx, my = sum(x2)/len(x2), sum(y2)/len(y2)
    cov_ = sum((a-mx)*(b-my) for a,b in zip(x2,y2))/len(x2)
    sx = (sum((a-mx)**2 for a in x2)/len(x2))**0.5
    sy = (sum((b-my)**2 for b in y2)/len(y2))**0.5
    return cov_/(sx*sy) if sx*sy else 0

print("\n=== Lagged Correlation: Fed Rate -> Inflation ===")
for lag in [6, 12, 18, 24]:
    lc = lagged_corr(fed_vals, inf_vals, lag)
    print(f"  Fed leads inflation by {lag:2d} months: r = {lc:.3f}")

# ── Key historical episodes ───────────────────────────────────────────────────
print("\n=== Key Historical Episodes ===")
episodes = [
    ("2008 Financial Crisis",    date(2008, 1, 1),  date(2009, 12, 31)),
    ("Post-GFC Low Rates",       date(2010, 1, 1),  date(2015, 12, 31)),
    ("Rate Hike Cycle 2015-18",  date(2015, 12, 1), date(2018, 12, 31)),
    ("COVID-19 Shock",           date(2020, 1, 1),  date(2021, 12, 31)),
    ("Post-COVID Inflation",     date(2021, 6, 1),  date(2023, 6, 30)),
    ("Aggressive Tightening",    date(2022, 3, 1),  date(2023, 12, 31)),
]
for label, start, end in episodes:
    subset = [(d, f, i) for d, f, i in zip(dates, fed_vals, inf_vals) if start <= d <= end]
    if not subset:
        continue
    avg_ff  = sum(x[1] for x in subset) / len(subset)
    avg_inf = sum(x[2] for x in subset) / len(subset)
    peak_inf = max(x[2] for x in subset)
    print(f"\n  [{label}]")
    print(f"    Avg Fed Funds: {avg_ff:.2f}%   Avg Inflation: {avg_inf:.2f}%   Peak Inflation: {peak_inf:.2f}%")

# ── ASCII Chart ───────────────────────────────────────────────────────────────
print("\n=== Time Series Overview (Annual Averages) ===")
print("  Year  | FedRate | Inflation | Fed [#]  Infl [*]")
print("  ------+---------+-----------+" + "-"*30)
# Annual averages
years_seen = {}
for d, f, i in zip(dates, fed_vals, inf_vals):
    y = d.year
    if y not in years_seen:
        years_seen[y] = []
    years_seen[y].append((f, i))
for yr in sorted(years_seen):
    vals = years_seen[yr]
    af = sum(v[0] for v in vals)/len(vals)
    ai = sum(v[1] for v in vals)/len(vals)
    bar_f = "#" * max(0, round(af))
    bar_i = "*" * max(0, round(ai))
    sign = "+" if ai >= 0 else ""
    print(f"  {yr}  |  {af:5.2f}%  |  {sign}{ai:5.2f}%   | {bar_f} | {bar_i}")

# ── Generate matplotlib figure ────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 14))
    fig.suptitle("Federal Funds Rate vs CPI Inflation (2006\u20132026)\nSource: FRED \u2013 Federal Reserve Bank of St. Louis",
                 fontsize=14, fontweight="bold", y=0.98)

    pydt = [datetime(d.year, d.month, d.day) for d in dates]

    # Panel 1 \u2014 Dual-axis overlay
    ax1.set_title("Federal Funds Rate & YoY Inflation Overlay", fontsize=12)
    l1, = ax1.plot(pydt, fed_vals, color="#1565C0", linewidth=2, label="Fed Funds Rate (%)")
    ax1.set_ylabel("Fed Funds Rate (%)", color="#1565C0")
    ax1.tick_params(axis="y", labelcolor="#1565C0")
    ax1b = ax1.twinx()
    l2, = ax1b.plot(pydt, inf_vals, color="#C62828", linewidth=1.8, linestyle="--", label="CPI Inflation YoY (%)")
    ax1b.set_ylabel("CPI Inflation YoY (%)", color="#C62828")
    ax1b.tick_params(axis="y", labelcolor="#C62828")
    ax1b.axhline(2, color="#C62828", linewidth=0.8, linestyle=":", alpha=0.6)
    ax1b.text(pydt[-1], 2.2, "2% target", color="#C62828", fontsize=8, ha="right")
    ax1.legend(handles=[l1, l2], loc="upper left", fontsize=9)
    ax1.grid(alpha=0.3)

    # Panel 2 \u2014 Rate of change
    fed_changes = [fed_vals[i] - fed_vals[i-1] for i in range(1, len(fed_vals))]
    colors_bar  = ["#1565C0" if c >= 0 else "#EF5350" for c in fed_changes]
    ax2.bar(pydt[1:], fed_changes, color=colors_bar, width=25, alpha=0.85)
    ax2.set_title("Monthly Change in Federal Funds Rate (Hikes / Cuts)", fontsize=12)
    ax2.set_ylabel("Change (percentage points)")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.grid(alpha=0.3)

    # Panel 3 \u2014 Scatter
    ax3.scatter(fed_vals, inf_vals, c=range(len(fed_vals)), cmap="viridis", alpha=0.65, s=30, zorder=3)
    mx_ = sum(fed_vals)/n
    my_ = sum(inf_vals)/n
    m_  = sum((f-mx_)*(i-my_) for f,i in zip(fed_vals,inf_vals)) / sum((f-mx_)**2 for f in fed_vals)
    b_  = my_ - m_*mx_
    x0, x1 = min(fed_vals), max(fed_vals)
    ax3.plot([x0, x1], [m_*x0+b_, m_*x1+b_], "r--", linewidth=1.5, label=f"Trend  r={corr:.2f}")
    ax3.set_xlabel("Federal Funds Rate (%)")
    ax3.set_ylabel("CPI Inflation YoY (%)")
    ax3.set_title(f"Fed Funds Rate vs Inflation \u2014 Scatter (Pearson r = {corr:.3f})", fontsize=12)
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = os.path.join(BASE, "fed_vs_inflation.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\nChart saved: {out_path}")
    plt.close()
except ImportError:
    print("\n[matplotlib not available \u2014 skipping chart generation]")

print("\nDone.")
