#!/usr/bin/env python3
"""
Value Alignment Checker
========================

Checks that all preset scenario values are aligned with Streamlit slider steps.
Misaligned values cause "values property in conflict with step" errors.

Usage:
    python scripts/check_value_alignment.py
"""

import sys
sys.path.insert(0, '.')

from price_volume_model import get_scenario_presets


def check_alignment(value, step, tolerance=0.001):
    """Check if a value is aligned with a step size."""
    remainder = abs(value * 100 % (step * 100))
    return remainder < tolerance or remainder > (step * 100 - tolerance)


def check_scenario_alignment(verbose=True):
    """
    Check all scenario presets for value alignment issues.

    Returns:
        dict: Results with any misaligned values
    """
    results = {
        "passed": True,
        "issues": [],
        "checked": 0
    }

    # Define slider configurations (name, step)
    price_sliders = [
        ('hrc_us_factor', 0.05),
        ('crc_us_factor', 0.05),
        ('coated_us_factor', 0.05),
        ('hrc_eu_factor', 0.05),
        ('octg_factor', 0.05),
    ]

    volume_sliders = [
        ('flat_rolled_volume_factor', 0.05),
        ('mini_mill_volume_factor', 0.05),
        ('usse_volume_factor', 0.05),
        ('tubular_volume_factor', 0.05),
    ]

    if verbose:
        print("=" * 60)
        print("VALUE ALIGNMENT CHECK")
        print("=" * 60)
        print("\nChecking all scenario presets for slider compatibility...")
        print("(All values must be multiples of 0.05 for slider step alignment)\n")

    presets = get_scenario_presets()

    for scenario_type, scenario in presets.items():
        scenario_issues = []

        # Check price factors
        ps = scenario.price_scenario
        for attr, step in price_sliders:
            value = getattr(ps, attr)
            results["checked"] += 1
            if not check_alignment(value, step):
                scenario_issues.append(f"price.{attr}={value} (step={step})")

        # Check volume factors
        vs = scenario.volume_scenario
        for attr, step in volume_sliders:
            value = getattr(vs, attr)
            results["checked"] += 1
            if not check_alignment(value, step):
                scenario_issues.append(f"volume.{attr}={value} (step={step})")

        if scenario_issues:
            results["issues"].extend([(scenario_type.value, issue) for issue in scenario_issues])
            results["passed"] = False
            if verbose:
                print(f"  ✗ {scenario_type.value}:")
                for issue in scenario_issues:
                    print(f"      - {issue}")
        else:
            if verbose:
                print(f"  ✓ {scenario_type.value}: OK")

    if verbose:
        print("\n" + "=" * 60)
        print(f"Checked {results['checked']} values across {len(presets)} scenarios")

        if results["passed"]:
            print("\n✓ All values are properly aligned!")
        else:
            print(f"\n✗ Found {len(results['issues'])} misaligned values")
            print("\nTo fix, update values to be multiples of the slider step:")
            print("  0.68 → 0.70")
            print("  0.88 → 0.90")
            print("  0.92 → 0.90 or 0.95")
            print("  0.93 → 0.90 or 0.95")
        print("=" * 60)

    return results


if __name__ == "__main__":
    results = check_scenario_alignment()
    sys.exit(0 if results["passed"] else 1)
