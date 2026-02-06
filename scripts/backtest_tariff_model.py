#!/usr/bin/env python3
"""
Backtest: Section 232 Tariff Model Validation
==============================================

Validates the model's tariff adjustment against empirical data:
1. Compares pre-tariff vs post-tariff HRC prices from Bloomberg
2. Adjusts for confounding factors (scrap prices, capacity changes)
3. Compares to OLS regression coefficient
4. Reports whether the model's 15% uplift is calibrated correctly

Usage:
    python scripts/backtest_tariff_model.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from price_volume_model import (
    BENCHMARK_PRICES_THROUGH_CYCLE, BENCHMARK_PRICES_PRE_COVID,
    BENCHMARK_PRICES_POST_SPIKE, TARIFF_CONFIG,
    calculate_tariff_adjustment, get_tariff_decomposition,
)


def run_backtest():
    """Run tariff model backtest and print results."""
    print("=" * 70)
    print("Section 232 Tariff Model Backtest")
    print("=" * 70)

    # 1. Empirical tariff premium (Bloomberg data)
    print("\n1. EMPIRICAL TARIFF PREMIUM (Bloomberg)")
    print("-" * 50)

    # Pre-tariff (before March 2018): avg HRC ~$610/ton
    # Post-tariff pre-COVID (March 2018 - Dec 2019): avg HRC ~$720/ton
    pre_tariff_hrc = 610
    post_tariff_pre_covid_hrc = 720
    empirical_uplift = (post_tariff_pre_covid_hrc / pre_tariff_hrc) - 1

    print(f"  Pre-tariff HRC (avg):       ${pre_tariff_hrc}/ton")
    print(f"  Post-tariff HRC (avg):      ${post_tariff_pre_covid_hrc}/ton")
    print(f"  Empirical uplift:           {empirical_uplift:.1%}")
    print(f"  (Raw, not adjusted for confounders)")

    # 2. OLS regression coefficient
    print("\n2. OLS REGRESSION COEFFICIENT")
    print("-" * 50)

    ols_coeff = TARIFF_CONFIG['ols_coefficient']
    ols_uplift = (2.71828 ** ols_coeff) - 1  # exp(β) - 1

    print(f"  Model: ln(HRC) = -2.98 + 1.57×ln(Scrap) + 0.01×Capacity + {ols_coeff}×Tariff")
    print(f"  OLS coefficient:            {ols_coeff:.4f}")
    print(f"  Implied uplift (exp(β)-1):  {ols_uplift:.1%}")
    print(f"  (Direct effect only; underestimates total market impact)")

    # 3. Model calibration
    print("\n3. MODEL CALIBRATION")
    print("-" * 50)

    model_uplift = TARIFF_CONFIG['model_uplift_hrc']
    print(f"  Model uplift (HRC):         {model_uplift:.0%}")
    print(f"  Position vs OLS:            {model_uplift/ols_uplift:.1f}x OLS ({ols_uplift:.1%})")
    print(f"  Position vs empirical:      {model_uplift/empirical_uplift:.1f}x empirical ({empirical_uplift:.1%})")
    print(f"  Rationale: Conservative between OLS and empirical")

    # 4. Tariff adjustment at key rates
    print("\n4. TARIFF ADJUSTMENTS AT KEY RATES")
    print("-" * 50)

    rates = [0.0, 0.10, 0.25, 0.50]
    print(f"  {'Rate':>8s}  {'HRC US':>8s}  {'CRC US':>8s}  {'EU HRC':>8s}  {'OCTG':>8s}")
    for rate in rates:
        adjs = {
            bt: calculate_tariff_adjustment(rate, bt)
            for bt in ['hrc_us', 'crc_us', 'hrc_eu', 'octg']
        }
        print(f"  {rate:>7.0%}  {adjs['hrc_us']:>8.3f}  {adjs['crc_us']:>8.3f}  "
              f"{adjs['hrc_eu']:>8.3f}  {adjs['octg']:>8.3f}")

    # 5. Dollar price impact
    print("\n5. DOLLAR PRICE IMPACT (vs Through-Cycle Baseline)")
    print("-" * 50)

    for rate in rates:
        hrc_base = BENCHMARK_PRICES_THROUGH_CYCLE['hrc_us']
        adj = calculate_tariff_adjustment(rate, 'hrc_us')
        hrc_adj = hrc_base * adj
        print(f"  Tariff {rate:>5.0%}: HRC ${hrc_adj:,.0f}/ton "
              f"(adj={adj:.3f}, delta=${hrc_adj - hrc_base:+,.0f})")

    # 6. Tariff decomposition
    print("\n6. TARIFF DECOMPOSITION (at current 25%)")
    print("-" * 50)

    decomp = get_tariff_decomposition(0.25)
    print(f"  {'Product':>10s}  {'Through-Cycle':>14s}  {'Pre-Tariff Est':>14s}  "
          f"{'Tariff $':>10s}  {'% of Price':>10s}")
    for btype, data in decomp.items():
        print(f"  {btype:>10s}  ${data['through_cycle']:>12,.0f}  "
              f"${data['pre_tariff_est']:>12,.0f}  "
              f"${data['tariff_component']:>8,.0f}  "
              f"{data['tariff_pct_of_price']:>8.1f}%")

    # 7. Validation summary
    print("\n7. VALIDATION SUMMARY")
    print("-" * 50)

    checks = []

    # Check 1: Model uplift between OLS and empirical
    if ols_uplift < model_uplift < empirical_uplift:
        checks.append(("Model uplift between OLS and empirical", "PASS"))
    else:
        checks.append(("Model uplift between OLS and empirical", "FAIL"))

    # Check 2: Status quo adjustment = 1.0
    if calculate_tariff_adjustment(0.25, 'hrc_us') == 1.0:
        checks.append(("Status quo (25%) returns 1.0", "PASS"))
    else:
        checks.append(("Status quo (25%) returns 1.0", "FAIL"))

    # Check 3: Removal reduces HRC by 10-20%
    removal_adj = calculate_tariff_adjustment(0.0, 'hrc_us')
    if 0.80 <= removal_adj <= 0.90:
        checks.append(("Removal reduces HRC 10-20%", "PASS"))
    else:
        checks.append(("Removal reduces HRC 10-20%", "FAIL"))

    # Check 4: EU impact < 50% of US
    eu_removal = calculate_tariff_adjustment(0.0, 'hrc_eu')
    us_impact = abs(1.0 - removal_adj)
    eu_impact = abs(1.0 - eu_removal)
    if eu_impact < us_impact * 0.5:
        checks.append(("EU impact < 50% of US impact", "PASS"))
    else:
        checks.append(("EU impact < 50% of US impact", "FAIL"))

    # Check 5: Through-cycle HRC is avg of pre-COVID and post-spike
    tc_hrc = BENCHMARK_PRICES_THROUGH_CYCLE['hrc_us']
    avg_hrc = (BENCHMARK_PRICES_PRE_COVID['hrc_us'] + BENCHMARK_PRICES_POST_SPIKE['hrc_us']) / 2
    if abs(tc_hrc - avg_hrc) <= 2:
        checks.append(("Through-cycle HRC = avg(pre-COVID, post-spike)", "PASS"))
    else:
        checks.append(("Through-cycle HRC = avg(pre-COVID, post-spike)", "FAIL"))

    for desc, result in checks:
        marker = "✓" if result == "PASS" else "✗"
        print(f"  {marker} {desc}: {result}")

    n_pass = sum(1 for _, r in checks if r == "PASS")
    print(f"\n  {n_pass}/{len(checks)} checks passed")

    return n_pass == len(checks)


if __name__ == '__main__':
    success = run_backtest()
    sys.exit(0 if success else 1)
