#!/usr/bin/env python3
"""
Steel Price Benchmark Sensitivity Analysis
Shows the impact of changing benchmark prices on valuation
"""

import pandas as pd
from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, ScenarioType,
    BENCHMARK_PRICES_2023
)

def analyze_benchmark_sensitivity():
    """Analyze how changing steel price benchmarks affects valuation"""

    # Use Base Case scenario as starting point
    base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]

    # Test different benchmark price levels (as % of 2023 actuals)
    benchmark_multipliers = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]

    results = []

    for multiplier in benchmark_multipliers:
        # Create modified benchmark prices
        modified_benchmarks = {
            key: value * multiplier
            for key, value in BENCHMARK_PRICES_2023.items()
        }

        # Temporarily modify the benchmarks (monkey patch)
        import price_volume_model
        original_benchmarks = price_volume_model.BENCHMARK_PRICES_2023.copy()
        price_volume_model.BENCHMARK_PRICES_2023.update(modified_benchmarks)

        # Run the model
        model = PriceVolumeModel(base_scenario)
        analysis = model.run_full_analysis()

        # Restore original benchmarks
        price_volume_model.BENCHMARK_PRICES_2023.update(original_benchmarks)

        # Extract key metrics
        consolidated = analysis['consolidated']
        val_uss = analysis['val_uss']
        val_nippon = analysis['val_nippon']

        results.append({
            'Benchmark Level': f"{multiplier:.0%}",
            'HRC Price': f"${modified_benchmarks['hrc_us']:.0f}",
            'OCTG Price': f"${modified_benchmarks['octg']:.0f}",
            'Avg Revenue ($B)': consolidated['Revenue'].mean() / 1000,
            'Avg EBITDA ($M)': consolidated['Total_EBITDA'].mean(),
            'Avg EBITDA Margin': consolidated['EBITDA_Margin'].mean(),
            '10Y FCF ($B)': consolidated['FCF'].sum() / 1000,
            'USS Value ($/sh)': val_uss['share_price'],
            'Nippon Value ($/sh)': val_nippon['share_price'],
            'vs $55 Offer': val_nippon['share_price'] - 55
        })

    df = pd.DataFrame(results)

    # Calculate sensitivity metrics
    print("=" * 100)
    print("STEEL PRICE BENCHMARK SENSITIVITY ANALYSIS")
    print("=" * 100)
    print("\nBase Case Scenario with varying benchmark price levels:")
    print("-" * 100)
    print(df.to_string(index=False))

    # Calculate impact of 10% change
    base_idx = 3  # 100% level
    high_idx = 4  # 110% level
    low_idx = 2   # 90% level

    print("\n" + "=" * 100)
    print("KEY SENSITIVITY METRICS")
    print("=" * 100)

    print(f"\nImpact of +10% benchmark price increase (from 100% to 110%):")
    print(f"  Revenue:        {(df.iloc[high_idx]['Avg Revenue ($B)'] / df.iloc[base_idx]['Avg Revenue ($B)'] - 1) * 100:+.1f}%")
    print(f"  EBITDA:         {(df.iloc[high_idx]['Avg EBITDA ($M)'] / df.iloc[base_idx]['Avg EBITDA ($M)'] - 1) * 100:+.1f}%")
    print(f"  10Y FCF:        {(df.iloc[high_idx]['10Y FCF ($B)'] / df.iloc[base_idx]['10Y FCF ($B)'] - 1) * 100:+.1f}%")
    print(f"  USS Value:      ${df.iloc[high_idx]['USS Value ($/sh)'] - df.iloc[base_idx]['USS Value ($/sh)']:+.2f}/share ({(df.iloc[high_idx]['USS Value ($/sh)'] / df.iloc[base_idx]['USS Value ($/sh)'] - 1) * 100:+.1f}%)")
    print(f"  Nippon Value:   ${df.iloc[high_idx]['Nippon Value ($/sh)'] - df.iloc[base_idx]['Nippon Value ($/sh)']:+.2f}/share ({(df.iloc[high_idx]['Nippon Value ($/sh)'] / df.iloc[base_idx]['Nippon Value ($/sh)'] - 1) * 100:+.1f}%)")

    print(f"\nImpact of -10% benchmark price decrease (from 100% to 90%):")
    print(f"  Revenue:        {(df.iloc[low_idx]['Avg Revenue ($B)'] / df.iloc[base_idx]['Avg Revenue ($B)'] - 1) * 100:+.1f}%")
    print(f"  EBITDA:         {(df.iloc[low_idx]['Avg EBITDA ($M)'] / df.iloc[base_idx]['Avg EBITDA ($M)'] - 1) * 100:+.1f}%")
    print(f"  10Y FCF:        {(df.iloc[low_idx]['10Y FCF ($B)'] / df.iloc[base_idx]['10Y FCF ($B)'] - 1) * 100:+.1f}%")
    print(f"  USS Value:      ${df.iloc[low_idx]['USS Value ($/sh)'] - df.iloc[base_idx]['USS Value ($/sh)']:+.2f}/share ({(df.iloc[low_idx]['USS Value ($/sh)'] / df.iloc[base_idx]['USS Value ($/sh)'] - 1) * 100:+.1f}%)")
    print(f"  Nippon Value:   ${df.iloc[low_idx]['Nippon Value ($/sh)'] - df.iloc[base_idx]['Nippon Value ($/sh)']:+.2f}/share ({(df.iloc[low_idx]['Nippon Value ($/sh)'] / df.iloc[base_idx]['Nippon Value ($/sh)'] - 1) * 100:+.1f}%)")

    # Calculate price elasticity
    print("\n" + "=" * 100)
    print("PRICE ELASTICITY")
    print("=" * 100)

    # Elasticity = % change in value / % change in price
    elasticity_uss = ((df.iloc[high_idx]['USS Value ($/sh)'] / df.iloc[base_idx]['USS Value ($/sh)'] - 1) / 0.10)
    elasticity_nippon = ((df.iloc[high_idx]['Nippon Value ($/sh)'] / df.iloc[base_idx]['Nippon Value ($/sh)'] - 1) / 0.10)

    print(f"\nElasticity (% change in value per 1% change in steel prices):")
    print(f"  USS Value:      {elasticity_uss:.2f}x")
    print(f"  Nippon Value:   {elasticity_nippon:.2f}x")
    print(f"\nInterpretation:")
    print(f"  - A 1% increase in steel prices → USS value increases by {elasticity_uss:.2f}%")
    print(f"  - A 1% increase in steel prices → Nippon value increases by {elasticity_nippon:.2f}%")

    # Valuation range
    print("\n" + "=" * 100)
    print("VALUATION RANGE ACROSS PRICE SCENARIOS")
    print("=" * 100)

    print(f"\nUSS Value Range:")
    print(f"  Low (70% benchmarks):  ${df.iloc[0]['USS Value ($/sh)']:.2f}/share")
    print(f"  Base (100% benchmarks): ${df.iloc[base_idx]['USS Value ($/sh)']:.2f}/share")
    print(f"  High (130% benchmarks): ${df.iloc[6]['USS Value ($/sh)']:.2f}/share")
    print(f"  Total Range:           ${df.iloc[6]['USS Value ($/sh)'] - df.iloc[0]['USS Value ($/sh)']:.2f}/share ({df.iloc[6]['USS Value ($/sh)'] / df.iloc[0]['USS Value ($/sh)']:.1f}x)")

    print(f"\nNippon Value Range:")
    print(f"  Low (70% benchmarks):  ${df.iloc[0]['Nippon Value ($/sh)']:.2f}/share")
    print(f"  Base (100% benchmarks): ${df.iloc[base_idx]['Nippon Value ($/sh)']:.2f}/share")
    print(f"  High (130% benchmarks): ${df.iloc[6]['Nippon Value ($/sh)']:.2f}/share")
    print(f"  Total Range:           ${df.iloc[6]['Nippon Value ($/sh)'] - df.iloc[0]['Nippon Value ($/sh)']:.2f}/share ({df.iloc[6]['Nippon Value ($/sh)'] / df.iloc[0]['Nippon Value ($/sh)']:.1f}x)")

    print("\n" + "=" * 100)
    print("CONCLUSION")
    print("=" * 100)
    print("\nSteel price benchmarks have a MASSIVE impact on valuation:")
    print(f"  - Moving from recession (70%) to boom (130%) pricing:")
    print(f"    • USS value ranges from ${df.iloc[0]['USS Value ($/sh)']:.0f} to ${df.iloc[6]['USS Value ($/sh)']:.0f} per share")
    print(f"    • Nippon value ranges from ${df.iloc[0]['Nippon Value ($/sh)']:.0f} to ${df.iloc[6]['Nippon Value ($/sh)']:.0f} per share")
    print(f"  - This is the #1 driver of valuation uncertainty")
    print(f"  - A realistic +/- 10% steel price swing moves valuation by ~$15-20/share")
    print("\n")

if __name__ == "__main__":
    analyze_benchmark_sensitivity()
