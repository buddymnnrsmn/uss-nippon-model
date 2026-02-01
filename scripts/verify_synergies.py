#!/usr/bin/env python3
"""
Synergy Verification Script
============================

Verifies that synergy calculations are working correctly by comparing
valuations with and without synergies enabled.

Usage:
    python scripts/verify_synergies.py
"""

import sys
sys.path.insert(0, '.')

from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, get_synergy_presets,
    ScenarioType, BENCHMARK_PRICES_2023
)
from dataclasses import replace


def verify_synergies(verbose=True):
    """
    Verify synergy calculations are working correctly.

    Returns:
        dict: Verification results
    """
    results = {
        "passed": True,
        "checks": [],
        "values": {}
    }

    if verbose:
        print("=" * 60)
        print("SYNERGY MODULE VERIFICATION")
        print("=" * 60)

    presets = get_scenario_presets()
    synergy_presets = get_synergy_presets()
    base_scenario = presets[ScenarioType.BASE_CASE]

    # Test 1: Without synergies
    if verbose:
        print("\n1. Base Case WITHOUT Synergies:")

    model_no_syn = PriceVolumeModel(base_scenario, custom_benchmarks=BENCHMARK_PRICES_2023)
    results_no_syn = model_no_syn.run_full_analysis()

    uss_no_syn = results_no_syn['val_uss']['share_price']
    nippon_no_syn = results_no_syn['val_nippon']['share_price']

    results["values"]["uss_no_synergies"] = uss_no_syn
    results["values"]["nippon_no_synergies"] = nippon_no_syn

    if verbose:
        print(f"   USS Standalone: ${uss_no_syn:.2f}/share")
        print(f"   Nippon Value:   ${nippon_no_syn:.2f}/share")
        print(f"   Synergy schedule: {results_no_syn.get('synergy_schedule') is not None}")

    # Test 2: With Base Case synergies
    if verbose:
        print("\n2. Base Case WITH Base Case Synergies:")

    scenario_with_syn = replace(base_scenario, synergies=synergy_presets['base_case'])
    model_syn = PriceVolumeModel(scenario_with_syn, custom_benchmarks=BENCHMARK_PRICES_2023)
    results_syn = model_syn.run_full_analysis()

    uss_syn = results_syn['val_uss']['share_price']
    nippon_syn = results_syn['val_nippon']['share_price']

    results["values"]["uss_with_synergies"] = uss_syn
    results["values"]["nippon_with_synergies"] = nippon_syn

    if verbose:
        print(f"   USS Standalone: ${uss_syn:.2f}/share")
        print(f"   Nippon Value:   ${nippon_syn:.2f}/share")
        print(f"   Synergy schedule: {results_syn.get('synergy_schedule') is not None}")

    # Check synergy value details
    syn_value = results_syn.get('synergy_value')
    if syn_value:
        results["values"]["npv_synergies"] = syn_value['npv_synergies']
        results["values"]["run_rate_synergies"] = syn_value['run_rate_synergies']
        results["values"]["integration_costs"] = syn_value['total_integration_costs']
        results["values"]["synergy_per_share"] = syn_value['synergy_value_per_share']

        if verbose:
            print(f"\n3. Synergy Value Breakdown:")
            print(f"   NPV of Synergies:     ${syn_value['npv_synergies']:.0f}M")
            print(f"   Run-Rate Synergies:   ${syn_value['run_rate_synergies']:.0f}M/year")
            print(f"   Integration Costs:    ${syn_value['total_integration_costs']:.0f}M")
            print(f"   Synergy Value/Share:  ${syn_value['synergy_value_per_share']:.2f}")

    # Check synergy schedule
    syn_schedule = results_syn.get('synergy_schedule')
    if syn_schedule is not None:
        if verbose:
            print(f"\n4. Synergy Ramp Schedule (first 5 years):")
            print(f"   Year | Operating | Technology | Revenue | Integration | Total")
            print(f"   -----|-----------|------------|---------|-------------|------")
            for i in range(min(5, len(syn_schedule))):
                row = syn_schedule.iloc[i]
                print(f"   {int(row['Year'])}  | ${row['Operating_Synergy']:>7.0f}M | "
                      f"${row['Technology_Synergy']:>8.0f}M | ${row['Revenue_Synergy']:>5.0f}M | "
                      f"${row['Integration_Cost']:>9.0f}M | ${row['Total_Synergy_EBITDA']:>5.0f}M")

    # Verification checks
    if verbose:
        print(f"\n5. Verification Checks:")

    # Check 1: USS value should be same with/without synergies
    uss_unchanged = abs(uss_syn - uss_no_syn) < 0.01
    results["checks"].append(("USS unchanged with synergies", uss_unchanged))
    if verbose:
        print(f"   {'✓' if uss_unchanged else '✗'} USS value unchanged: ${uss_no_syn:.2f} vs ${uss_syn:.2f}")

    # Check 2: Nippon value should increase with synergies
    nippon_increased = nippon_syn > nippon_no_syn
    results["checks"].append(("Nippon value increased", nippon_increased))
    if verbose:
        diff = nippon_syn - nippon_no_syn
        print(f"   {'✓' if nippon_increased else '✗'} Nippon value increased: +${diff:.2f}/share")

    # Check 3: Synergy schedule should exist
    schedule_exists = syn_schedule is not None
    results["checks"].append(("Synergy schedule exists", schedule_exists))
    if verbose:
        print(f"   {'✓' if schedule_exists else '✗'} Synergy schedule present")

    # Check 4: Synergy value should be positive
    syn_positive = syn_value is not None and syn_value['npv_synergies'] > 0
    results["checks"].append(("Synergy NPV positive", syn_positive))
    if verbose:
        print(f"   {'✓' if syn_positive else '✗'} Synergy NPV positive")

    # Check 5: Run-rate synergies should match expected (~$400M for base case)
    run_rate_ok = syn_value is not None and 350 < syn_value['run_rate_synergies'] < 500
    results["checks"].append(("Run-rate synergies in range", run_rate_ok))
    if verbose:
        print(f"   {'✓' if run_rate_ok else '✗'} Run-rate synergies ~$400M")

    results["passed"] = all(check[1] for check in results["checks"])

    if verbose:
        print("\n" + "=" * 60)
        if results["passed"]:
            print("✓ SYNERGY MODULE IS WORKING CORRECTLY")
        else:
            print("✗ SYNERGY MODULE HAS ISSUES")
            for name, passed in results["checks"]:
                if not passed:
                    print(f"  - Failed: {name}")
        print("=" * 60)

    return results


def test_all_synergy_presets(verbose=True):
    """Test all synergy presets."""
    if verbose:
        print("\n" + "=" * 60)
        print("TESTING ALL SYNERGY PRESETS")
        print("=" * 60)

    presets = get_scenario_presets()
    synergy_presets = get_synergy_presets()
    base_scenario = presets[ScenarioType.BASE_CASE]

    results = []

    for name, syn_preset in synergy_presets.items():
        if not syn_preset.enabled:
            if verbose:
                print(f"\n{name}: Disabled (no synergies)")
            results.append((name, True, 0, 0))
            continue

        scenario = replace(base_scenario, synergies=syn_preset)
        model = PriceVolumeModel(scenario, custom_benchmarks=BENCHMARK_PRICES_2023)
        analysis = model.run_full_analysis()

        nippon_value = analysis['val_nippon']['share_price']
        syn_value = analysis.get('synergy_value', {})
        run_rate = syn_value.get('run_rate_synergies', 0) if syn_value else 0

        if verbose:
            print(f"\n{name}:")
            print(f"   Nippon Value: ${nippon_value:.2f}/share")
            print(f"   Run-Rate Synergies: ${run_rate:.0f}M/year")

        results.append((name, True, nippon_value, run_rate))

    return results


if __name__ == "__main__":
    verify_synergies()
    test_all_synergy_presets()
