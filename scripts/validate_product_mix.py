#!/usr/bin/env python3
"""
Validate product mix weights empirically by regressing segment realized prices
on benchmark steel prices.

Approach:
1. Annual benchmark prices (avg of weekly spot data) for HRC, CRC, HRC EU, OCTG
2. Estimate Coated as CRC * 1.12 (historical premium ~12% based on model ratios)
3. For each segment, solve: realized_price = w1*P1 + w2*P2 + ... + premium
   using constrained least squares (weights >= 0, sum to 1)
4. Compare fitted weights to model assumptions in SEGMENT_PRICE_MAP
"""

import sys
sys.path.insert(0, '/workspaces/claude-in-docker/FinancialModel')

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from data.uss_segment_data import USS_SEGMENT_DATA, SEGMENT_PRICE_MAP, MODEL_ASSUMPTIONS

# ---------------------------------------------------------------------------
# 1. Load benchmark price series and compute annual averages
# ---------------------------------------------------------------------------
base = '/workspaces/claude-in-docker/FinancialModel/market-data/exports/processed'

def load_annual_avg(filename):
    df = pd.read_csv(f'{base}/{filename}', parse_dates=['date'])
    df['year'] = df['date'].dt.year
    return df.groupby('year')['value'].mean()

hrc_us = load_annual_avg('hrc_us_spot.csv')
crc_us = load_annual_avg('crc_us_spot.csv')
hrc_eu = load_annual_avg('hrc_eu_spot.csv')
octg_us = load_annual_avg('octg_us_spot.csv')

# Estimate Coated from CRC with historical premium
# Model: coated_us = 1113, crc_us = 994 → ratio 1.12
COATED_PREMIUM = 1113 / 994  # ~1.12
coated_us = crc_us * COATED_PREMIUM

years = [2019, 2020, 2021, 2022, 2023]

print("=" * 80)
print("ANNUAL BENCHMARK PRICES ($/ton)")
print("=" * 80)
print(f"{'Year':>6} {'HRC US':>8} {'CRC US':>8} {'Coated':>8} {'HRC EU':>8} {'OCTG':>8}")
for y in years:
    print(f"{y:>6} {hrc_us.get(y, np.nan):>8.0f} {crc_us.get(y, np.nan):>8.0f} "
          f"{coated_us.get(y, np.nan):>8.0f} {hrc_eu.get(y, np.nan):>8.0f} {octg_us.get(y, np.nan):>8.0f}")

# ---------------------------------------------------------------------------
# 2. Build price matrix for each segment's relevant benchmarks
# ---------------------------------------------------------------------------

# Segment price configurations
SEGMENT_BENCHMARKS = {
    "Flat-Rolled": {
        "benchmarks": ["HRC US", "CRC US", "Coated"],
        "series": [hrc_us, crc_us, coated_us],
    },
    "Mini Mill": {
        "benchmarks": ["HRC US", "CRC US", "Coated"],
        "series": [hrc_us, crc_us, coated_us],
    },
    "USSE": {
        "benchmarks": ["HRC EU", "CRC US", "Coated"],
        "series": [hrc_eu, crc_us, coated_us],
    },
    "Tubular": {
        "benchmarks": ["OCTG US"],
        "series": [octg_us],
    },
}

print("\n" + "=" * 80)
print("SEGMENT REALIZED PRICES ($/ton, from 10-K)")
print("=" * 80)
for seg_name, data in USS_SEGMENT_DATA.items():
    prices_str = ", ".join([f"{yr}: ${rp}" for yr, _, _, _, rp in data])
    print(f"  {seg_name}: {prices_str}")


# ---------------------------------------------------------------------------
# 3. Constrained regression: min |realized - (w @ benchmarks + premium)|²
#    subject to: w >= 0, sum(w) = 1
# ---------------------------------------------------------------------------

print("\n" + "=" * 80)
print("CONSTRAINED REGRESSION: PRODUCT MIX WEIGHT ESTIMATION")
print("=" * 80)

results = {}

for seg_name, config in SEGMENT_BENCHMARKS.items():
    seg_data = USS_SEGMENT_DATA[seg_name]
    n_bench = len(config["benchmarks"])

    # Build arrays
    realized = []
    bench_matrix = []
    for yr, rev, ebitda, ship, rp in seg_data:
        if yr in years:
            realized.append(rp)
            row = [s.get(yr, np.nan) for s in config["series"]]
            bench_matrix.append(row)

    realized = np.array(realized)
    B = np.array(bench_matrix)
    n = len(realized)

    if n_bench == 1:
        # Tubular: just compute realization factor
        ratio = realized / B[:, 0]
        print(f"\n--- {seg_name} ---")
        print(f"  Single benchmark: {config['benchmarks'][0]}")
        print(f"  Realization factors: {[f'{r:.2f}' for r in ratio]}")
        print(f"  Mean realization: {ratio.mean():.3f} (model: {1 + MODEL_ASSUMPTIONS[seg_name]['realization_premium']:.3f})")
        results[seg_name] = {"weights": {config["benchmarks"][0]: 1.0}, "premium": ratio.mean() - 1}
        continue

    # Model A: weights only (no intercept), realized = w @ benchmarks
    def objective_no_intercept(w):
        pred = B @ w
        return np.sum((realized - pred) ** 2)

    constraints_a = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
    bounds_a = [(0, 1)] * n_bench
    x0 = np.ones(n_bench) / n_bench
    res_a = minimize(objective_no_intercept, x0, bounds=bounds_a, constraints=constraints_a, method='SLSQP')

    # Model B: weights + intercept (premium), realized = w @ benchmarks + alpha
    def objective_with_intercept(params):
        w = params[:n_bench]
        alpha = params[n_bench]
        pred = B @ w + alpha
        return np.sum((realized - pred) ** 2)

    constraints_b = [{'type': 'eq', 'fun': lambda p: np.sum(p[:n_bench]) - 1}]
    bounds_b = [(0, 1)] * n_bench + [(-500, 500)]
    x0_b = list(np.ones(n_bench) / n_bench) + [0]
    res_b = minimize(objective_with_intercept, x0_b, bounds=bounds_b, constraints=constraints_b, method='SLSQP')

    # Compute R² for both
    ss_tot = np.sum((realized - realized.mean()) ** 2)

    pred_a = B @ res_a.x
    r2_a = 1 - np.sum((realized - pred_a) ** 2) / ss_tot if ss_tot > 0 else 0

    w_b = res_b.x[:n_bench]
    alpha_b = res_b.x[n_bench]
    pred_b = B @ w_b + alpha_b
    r2_b = 1 - np.sum((realized - pred_b) ** 2) / ss_tot if ss_tot > 0 else 0

    # Model assumptions for comparison
    model_weights = SEGMENT_PRICE_MAP[seg_name]
    model_w = []
    for bname in config["benchmarks"]:
        # Match benchmark name to SEGMENT_PRICE_MAP keys
        matched = False
        for k, v in model_weights.items():
            if bname in k or k in bname:
                model_w.append(v)
                matched = True
                break
        if not matched:
            model_w.append(0)
    model_w = np.array(model_w)
    pred_model = B @ model_w
    r2_model = 1 - np.sum((realized - pred_model) ** 2) / ss_tot if ss_tot > 0 else 0

    # With model weights + premium
    model_premium = MODEL_ASSUMPTIONS[seg_name]['realization_premium']
    pred_model_prem = pred_model * (1 + model_premium)
    r2_model_prem = 1 - np.sum((realized - pred_model_prem) ** 2) / ss_tot if ss_tot > 0 else 0

    print(f"\n--- {seg_name} (n={n} years) ---")
    print(f"  Realized prices: {realized}")
    print(f"  Benchmark names: {config['benchmarks']}")
    print()

    print(f"  {'Method':<30} ", end="")
    for b in config["benchmarks"]:
        print(f"{b:>10}", end="")
    print(f"  {'Premium':>10} {'R²':>8} {'RMSE':>8}")
    print(f"  {'-'*30} ", end="")
    for _ in config["benchmarks"]:
        print(f"{'----------':>10}", end="")
    print(f"  {'----------':>10} {'--------':>8} {'--------':>8}")

    # Row: Fitted (no intercept)
    rmse_a = np.sqrt(np.mean((realized - pred_a) ** 2))
    print(f"  {'Fitted (no intercept)':<30} ", end="")
    for w in res_a.x:
        print(f"{w:>10.1%}", end="")
    print(f"  {'n/a':>10} {r2_a:>8.3f} {rmse_a:>8.0f}")

    # Row: Fitted (with intercept)
    rmse_b = np.sqrt(np.mean((realized - pred_b) ** 2))
    print(f"  {'Fitted (with intercept)':<30} ", end="")
    for w in w_b:
        print(f"{w:>10.1%}", end="")
    print(f"  {'$' + str(int(alpha_b)):>10} {r2_b:>8.3f} {rmse_b:>8.0f}")

    # Row: Model assumptions
    rmse_model = np.sqrt(np.mean((realized - pred_model) ** 2))
    print(f"  {'Model assumed':<30} ", end="")
    for w in model_w:
        print(f"{w:>10.1%}", end="")
    print(f"  {'n/a':>10} {r2_model:>8.3f} {rmse_model:>8.0f}")

    # Row: Model + premium
    rmse_model_prem = np.sqrt(np.mean((realized - pred_model_prem) ** 2))
    print(f"  {'Model + premium':<30} ", end="")
    for w in model_w:
        print(f"{w:>10.1%}", end="")
    print(f"  {model_premium:>10.1%} {r2_model_prem:>8.3f} {rmse_model_prem:>8.0f}")

    results[seg_name] = {
        "fitted_weights": {b: round(w, 3) for b, w in zip(config["benchmarks"], res_a.x)},
        "fitted_with_intercept": {b: round(w, 3) for b, w in zip(config["benchmarks"], w_b)},
        "intercept": round(alpha_b, 1),
        "model_weights": {b: round(w, 3) for b, w in zip(config["benchmarks"], model_w)},
        "r2_fitted": round(r2_a, 3),
        "r2_model": round(r2_model, 3),
    }

    # Year-by-year comparison
    print(f"\n  Year-by-year fit:")
    print(f"  {'Year':>6} {'Actual':>8} {'Fitted':>8} {'Model':>8} {'Mod+Prem':>8} {'Err(Fit)':>8} {'Err(Mod)':>8}")
    for i, (yr, _, _, _, rp) in enumerate([d for d in seg_data if d[0] in years]):
        err_fit = pred_a[i] - rp
        err_mod = pred_model_prem[i] - rp
        print(f"  {yr:>6} {rp:>8.0f} {pred_a[i]:>8.0f} {pred_model[i]:>8.0f} {pred_model_prem[i]:>8.0f} {err_fit:>+8.0f} {err_mod:>+8.0f}")


# ---------------------------------------------------------------------------
# 4. Summary comparison
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("SUMMARY: MODEL vs EMPIRICAL WEIGHTS")
print("=" * 80)

for seg_name in ["Flat-Rolled", "Mini Mill", "USSE"]:
    r = results[seg_name]
    print(f"\n  {seg_name}:")
    benchmarks = list(r["fitted_weights"].keys())
    for b in benchmarks:
        fw = r["fitted_weights"][b]
        mw = r["model_weights"][b]
        diff = fw - mw
        print(f"    {b:<20} Model: {mw:>6.1%}  Empirical: {fw:>6.1%}  Delta: {diff:>+6.1%}")
    print(f"    R² (empirical): {r['r2_fitted']:.3f}   R² (model): {r['r2_model']:.3f}")

print("\n" + "=" * 80)
print("CAVEATS")
print("=" * 80)
print("""
  1. Only 5 annual observations (2019-2023) — very low degrees of freedom
  2. No separate Coated price series — estimated as CRC × 1.12 ratio
  3. Multicollinearity: HRC/CRC/Coated move together (R²>0.95), making
     individual weight estimates unstable
  4. Realized prices include contract premiums, product specs, and customer mix
     that benchmarks don't capture — the "realization premium"
  5. Better test: do the FITTED weights track realized prices better (lower RMSE)
     than the MODEL weights? That's the real validation.
""")
