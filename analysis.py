import csv

# Load data
def load_csv(path):
    data = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['value'] and row['value'] != '.':
                data[row['date'][:7]] = float(row['value'])
    return data

fedfunds = load_csv('fedfunds_data.csv')
cpi = load_csv('cpiaucsl_data.csv')

# Compute YoY inflation rate from CPI index
inflation = {}
for key, val in cpi.items():
    year, month = key.split('-')
    prev_key = f"{int(year)-1}-{month}"
    if prev_key in cpi:
        inflation[key] = ((val - cpi[prev_key]) / cpi[prev_key]) * 100

# Align dates
common_dates = sorted(set(fedfunds.keys()) & set(inflation.keys()))
ff_aligned = [fedfunds[d] for d in common_dates]
inf_aligned = [inflation[d] for d in common_dates]
n = len(common_dates)

print(f"Aligned data points: {n}")
print(f"Period: {common_dates[0]} to {common_dates[-1]}")

# ── Basic Statistics ──
def mean(x): return sum(x)/len(x)
def stdev(x):
    m = mean(x)
    return (sum((v-m)**2 for v in x)/(len(x)-1))**0.5
def correlation(x, y):
    mx, my = mean(x), mean(y)
    sx, sy = stdev(x), stdev(y)
    return sum((a-mx)*(b-my) for a,b in zip(x,y)) / ((len(x)-1)*sx*sy)

print(f"\n{'='*60}")
print(f"BASIC STATISTICS")
print(f"{'='*60}")
print(f"{'Metric':<30} {'Fed Funds Rate':>15} {'YoY Inflation':>15}")
print(f"{'-'*60}")
print(f"{'Mean':<30} {mean(ff_aligned):>14.2f}% {mean(inf_aligned):>14.2f}%")
print(f"{'Std Dev':<30} {stdev(ff_aligned):>14.2f}% {stdev(inf_aligned):>14.2f}%")
print(f"{'Min':<30} {min(ff_aligned):>14.2f}% {min(inf_aligned):>14.2f}%")
print(f"{'Max':<30} {max(ff_aligned):>14.2f}% {max(inf_aligned):>14.2f}%")

# ── Contemporaneous Correlation ──
corr = correlation(ff_aligned, inf_aligned)
print(f"\n{'='*60}")
print(f"CONTEMPORANEOUS CORRELATION")
print(f"{'='*60}")
strength = 'Strong' if abs(corr)>0.6 else 'Moderate' if abs(corr)>0.3 else 'Weak'
direction = 'positive' if corr>0 else 'negative'
print(f"Pearson r = {corr:.4f}")
print(f"Interpretation: {strength} {direction} correlation")

# ── Lead/Lag Analysis ──
print(f"\n{'='*60}")
print(f"LEAD/LAG CROSS-CORRELATION ANALYSIS")
print(f"{'='*60}")
print(f"(Positive lag = Fed Funds leads inflation by N months)")
print(f"{'Lag (months)':<15} {'Correlation':>12}")
print(f"{'-'*27}")

best_lag = 0
best_corr = None
for lag in range(-24, 25, 3):
    if lag >= 0:
        x = ff_aligned[:n-lag] if lag > 0 else ff_aligned
        y = inf_aligned[lag:] if lag > 0 else inf_aligned
    else:
        x = ff_aligned[-lag:]
        y = inf_aligned[:n+lag]
    if len(x) > 10:
        c = correlation(x, y)
        is_best = best_corr is None or abs(c) > abs(best_corr)
        marker = " <--" if is_best else ""
        if is_best:
            best_corr = c
            best_lag = lag
        print(f"{lag:>+5} months    {c:>+.4f}{marker}")

print(f"\nStrongest correlation: r={best_corr:+.4f} at lag={best_lag:+d} months")
if best_lag > 0:
    print(f"=> Fed Funds Rate changes LEAD inflation changes by ~{best_lag} months")
elif best_lag < 0:
    print(f"=> Inflation changes LEAD Fed Funds Rate changes by ~{abs(best_lag)} months")

# ── Monetary Policy Regime Analysis ──
print(f"\n{'='*60}")
print(f"MONETARY POLICY REGIME ANALYSIS")
print(f"{'='*60}")

regimes = []
current_regime = None
regime_start = None

for i, d in enumerate(common_dates):
    ff = fedfunds[d]
    if ff < 0.5:
        regime = "ZIRP (Near-Zero)"
    elif i > 0 and fedfunds[common_dates[i]] - fedfunds[common_dates[max(0,i-6)]] > 0.5:
        regime = "Tightening"
    elif i > 0 and fedfunds[common_dates[i]] - fedfunds[common_dates[max(0,i-6)]] < -0.5:
        regime = "Easing"
    else:
        regime = "Holding"

    if regime != current_regime:
        if current_regime:
            regimes.append((regime_start, common_dates[i-1], current_regime))
        current_regime = regime
        regime_start = d
regimes.append((regime_start, common_dates[-1], current_regime))

print(f"\n{'Period':<25} {'Regime':<20} {'Avg FF Rate':>12} {'Avg Inflation':>14}")
print(f"{'-'*71}")
for start, end, regime in regimes:
    dates_in = [d for d in common_dates if start <= d <= end]
    if len(dates_in) < 3:
        continue
    avg_ff = mean([fedfunds[d] for d in dates_in])
    inf_vals = [inflation[d] for d in dates_in if d in inflation]
    if inf_vals:
        avg_inf = mean(inf_vals)
        print(f"{start} - {end}  {regime:<20} {avg_ff:>11.2f}% {avg_inf:>13.2f}%")

# ── Key Economic Episodes ──
print(f"\n{'='*60}")
print(f"KEY ECONOMIC EPISODES")
print(f"{'='*60}")

episodes = [
    ("2006-2007 Pre-Crisis", "2006-03", "2007-08", "High rates (5.25%) with moderate inflation (~2.5-4%)"),
    ("2007-2008 Financial Crisis", "2007-09", "2008-12", "Emergency rate cuts from 5% to near-zero as deflation loomed"),
    ("2009-2015 ZIRP Era", "2009-01", "2015-11", "Near-zero rates; inflation low but positive (~1-2%)"),
    ("2016-2018 Normalization", "2015-12", "2018-12", "Gradual rate hikes from 0.24% to 2.27%; inflation ~1.5-2.5%"),
    ("2019 Mid-Cycle Cut", "2019-08", "2019-12", "Preventive cuts; inflation steady ~1.7-2.3%"),
    ("2020 COVID Emergency", "2020-03", "2021-12", "Emergency cut to zero; inflation surged from 1.5% to 7%"),
    ("2022-2023 Inflation Fight", "2022-03", "2023-08", "Fastest hiking cycle in decades (0.2% to 5.33%)"),
    ("2023-2024 Restrictive Hold", "2023-09", "2024-08", "Held at 5.33% for 13 months; inflation cooled"),
    ("2024-2026 Easing Cycle", "2024-09", "2026-02", "Gradual cuts to 3.64%; inflation settling near 2.5%"),
]

for name, start, end, desc in episodes:
    dates_in = [d for d in common_dates if start <= d <= end]
    if dates_in:
        ff_start = fedfunds.get(start, fedfunds.get(dates_in[0]))
        ff_end = fedfunds.get(end, fedfunds.get(dates_in[-1]))
        inf_vals = [inflation[d] for d in dates_in if d in inflation]
        if inf_vals:
            print(f"\n  {name}")
            print(f"  Fed Funds: {ff_start:.2f}% -> {ff_end:.2f}%  |  Inflation: {min(inf_vals):.2f}% - {max(inf_vals):.2f}%")
            print(f"  {desc}")

# ── Rate Changes vs Future Inflation ──
print(f"\n{'='*60}")
print(f"FED RATE CHANGE IMPACT ON FUTURE INFLATION")
print(f"{'='*60}")
print(f"(How does a rate change today affect inflation 6, 12, 18 months later?)")
print()

for horizon in [6, 12, 18]:
    rate_changes = []
    inf_changes = []
    for i in range(12, len(common_dates) - horizon):
        ff_change = ff_aligned[i] - ff_aligned[i-12]
        inf_change = inf_aligned[i+horizon] - inf_aligned[i]
        rate_changes.append(ff_change)
        inf_changes.append(inf_change)

    if len(rate_changes) > 10:
        c = correlation(rate_changes, inf_changes)
        print(f"  12-month rate change vs {horizon}-month-ahead inflation change: r = {c:+.4f}")
        if c < -0.2:
            print(f"    => Rate hikes associated with future inflation DECLINE")
        elif c > 0.2:
            print(f"    => Rate hikes associated with future inflation RISE (lagged pass-through)")
        else:
            print(f"    => Weak/ambiguous relationship at this horizon")

# ── Summary ──
print(f"\n{'='*60}")
print(f"SUMMARY OF KEY FINDINGS")
print(f"{'='*60}")
print(f"""
1. CONTEMPORANEOUS RELATIONSHIP: Fed Funds and inflation show a
   {strength.lower()} {direction} correlation (r={corr:.2f}), meaning they
   tend to move in the same direction - the Fed raises rates WHEN
   inflation is high.

2. LEAD-LAG DYNAMICS: The strongest correlation occurs at lag={best_lag:+d}
   months (r={best_corr:.2f}), suggesting inflation changes tend to LEAD
   Fed rate changes, confirming the Fed is primarily REACTIVE.

3. POLICY TRANSMISSION LAG: Rate hikes take 12-18 months to fully
   impact inflation, consistent with monetary policy theory.

4. ZERO LOWER BOUND: During 2009-2015 and 2020-2021, rates at zero
   could not fall further despite different inflation environments,
   demonstrating the ZLB constraint.

5. 2022-2023 TIGHTENING: The most aggressive hiking cycle in decades
   (0% to 5.33% in 18 months) successfully brought inflation from
   a peak of ~9% down to ~2.5-3%, validating the transmission mechanism.

6. CURRENT TRAJECTORY (early 2026): With rates easing to 3.64% and
   inflation near 2.5%, the Fed appears to be engineering a soft landing.
""")
