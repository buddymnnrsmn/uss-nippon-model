#!/usr/bin/env python3
"""
Sensitivity Analysis: Tornado Diagram (Elasticity-Based)
=========================================================

Identifies the top 3 most influential input variables on USS share price
using standardized elasticity analysis.

Elasticity = (% change in share price) / (% change in input)

This allows apples-to-apples comparison across all variable types.

Usage:
    python scripts/sensitivity_tornado.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copy import deepcopy
from dataclasses import replace
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from price_volume_model import (
    PriceVolumeModel,
    get_scenario_presets,
    ScenarioType,
    SteelPriceScenario,
    VolumeScenario,
)


def run_sensitivity_analysis(perturbation_pct: float = 0.10) -> dict:
    """
    Run standardized one-way sensitivity analysis on key input variables.

    Uses uniform ±10% relative perturbation for ALL variables to enable
    apples-to-apples comparison via elasticity.

    Elasticity = (% change in share price) / (% change in input)

    Args:
        perturbation_pct: Percentage to perturb each variable (e.g., 0.10 = ±10%)

    Returns:
        Dict with sensitivity results including elasticity for each variable
    """
    # Get base case scenario
    presets = get_scenario_presets()
    base_scenario = presets[ScenarioType.BASE_CASE]

    # Run base case
    base_model = PriceVolumeModel(base_scenario)
    base_result = base_model.run_full_analysis()
    base_price = base_result['val_uss']['share_price']

    print(f"Base Case Share Price: ${base_price:.2f}")
    print(f"Perturbation: ±{perturbation_pct*100:.0f}% (uniform for all variables)")
    print("-" * 70)
    print(f"{'Variable':<25} {'Base Val':>10} {'Low':>8} {'High':>8} {'Elasticity':>12}")
    print("-" * 70)

    # Define all variables to test
    # Format: (name, location, attr, description)
    # location: 'price_scenario', 'volume_scenario', or 'scenario'
    all_vars = [
        # Steel price factors
        ('HRC US Price Factor', 'price_scenario', 'hrc_us_factor', 'HRC steel price'),
        ('CRC US Price Factor', 'price_scenario', 'crc_us_factor', 'CRC steel price'),
        ('Coated Price Factor', 'price_scenario', 'coated_us_factor', 'Coated/galvanized'),
        ('OCTG Price Factor', 'price_scenario', 'octg_factor', 'Oil country tubular'),
        ('Annual Price Growth', 'price_scenario', 'annual_price_growth', 'Price inflation'),
        # Volume factors
        ('Flat-Rolled Volume', 'volume_scenario', 'flat_rolled_volume_factor', 'FR segment'),
        ('Mini Mill Volume', 'volume_scenario', 'mini_mill_volume_factor', 'MM segment'),
        ('USSE Volume', 'volume_scenario', 'usse_volume_factor', 'Europe segment'),
        ('Tubular Volume', 'volume_scenario', 'tubular_volume_factor', 'Tubular segment'),
        # Valuation parameters
        ('WACC', 'scenario', 'uss_wacc', 'Discount rate'),
        ('Terminal Growth', 'scenario', 'terminal_growth', 'Perpetual growth'),
        ('Exit Multiple', 'scenario', 'exit_multiple', 'EV/EBITDA multiple'),
    ]

    results = {}

    for name, location, attr, desc in all_vars:
        # Get base value
        if location == 'price_scenario':
            base_val = getattr(base_scenario.price_scenario, attr)
        elif location == 'volume_scenario':
            base_val = getattr(base_scenario.volume_scenario, attr)
        else:
            base_val = getattr(base_scenario, attr)

        # Apply uniform ±10% relative perturbation
        low_val = base_val * (1 - perturbation_pct)
        high_val = base_val * (1 + perturbation_pct)

        # Create modified scenarios
        if location == 'price_scenario':
            low_sub = replace(base_scenario.price_scenario, **{attr: low_val})
            high_sub = replace(base_scenario.price_scenario, **{attr: high_val})
            low_scenario = replace(base_scenario, price_scenario=low_sub)
            high_scenario = replace(base_scenario, price_scenario=high_sub)
        elif location == 'volume_scenario':
            low_sub = replace(base_scenario.volume_scenario, **{attr: low_val})
            high_sub = replace(base_scenario.volume_scenario, **{attr: high_val})
            low_scenario = replace(base_scenario, volume_scenario=low_sub)
            high_scenario = replace(base_scenario, volume_scenario=high_sub)
        else:
            low_scenario = replace(base_scenario, **{attr: low_val})
            high_scenario = replace(base_scenario, **{attr: high_val})

        # Run models
        low_result = PriceVolumeModel(low_scenario).run_full_analysis()
        high_result = PriceVolumeModel(high_scenario).run_full_analysis()

        low_price = low_result['val_uss']['share_price']
        high_price = high_result['val_uss']['share_price']

        # Calculate elasticity: (% change in output) / (% change in input)
        # Using average of upside and downside elasticity
        pct_change_input = perturbation_pct  # 10%
        pct_change_output_up = (high_price - base_price) / base_price
        pct_change_output_down = (base_price - low_price) / base_price

        elasticity_up = pct_change_output_up / pct_change_input
        elasticity_down = pct_change_output_down / pct_change_input
        avg_elasticity = (abs(elasticity_up) + abs(elasticity_down)) / 2

        results[name] = {
            'base_val': base_val,
            'low_val': low_val,
            'high_val': high_val,
            'low_price': low_price,
            'high_price': high_price,
            'elasticity': avg_elasticity,
            'elasticity_up': elasticity_up,
            'elasticity_down': elasticity_down,
            'description': desc,
            'dollar_impact': (high_price - low_price) / 2,  # ± impact from base
        }

        # Format base value for display
        if base_val < 0.1:
            base_str = f"{base_val:.3f}"
        elif base_val < 10:
            base_str = f"{base_val:.2f}"
        else:
            base_str = f"{base_val:.1f}"

        print(f"{name:<25} {base_str:>10} ${low_price:>6.2f} ${high_price:>6.2f} {avg_elasticity:>11.2f}x")

    return results, base_price


def rank_by_elasticity(results: dict) -> list:
    """
    Rank variables by elasticity (standardized measure of sensitivity).

    Elasticity = (% change in share price) / (% change in input)

    Returns:
        List of dicts sorted by elasticity descending
    """
    rankings = []
    for name, data in results.items():
        rankings.append({
            'name': name,
            'elasticity': data['elasticity'],
            'dollar_impact': data['dollar_impact'],
            'low_price': data['low_price'],
            'high_price': data['high_price'],
            'base_val': data['base_val'],
            'description': data['description'],
        })

    rankings.sort(key=lambda x: x['elasticity'], reverse=True)
    return rankings


def create_tornado_chart(rankings: list, base_price: float, top_n: int = None, output_path: str = None):
    """
    Create a tornado diagram showing elasticity of share price to each variable.

    Args:
        rankings: List from rank_by_elasticity()
        base_price: Base case share price
        top_n: If specified, only show top N variables
        output_path: Path to save the chart
    """
    if top_n:
        rankings = rankings[:top_n]

    fig, ax = plt.subplots(figsize=(12, max(6, len(rankings) * 0.6)))

    y_positions = np.arange(len(rankings))

    # Color based on elasticity magnitude
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(rankings)))

    for i, item in enumerate(reversed(rankings)):
        y = i
        elasticity = item['elasticity']
        low_delta = item['low_price'] - base_price
        high_delta = item['high_price'] - base_price

        # Draw symmetric bars showing price impact
        bar_color = colors[len(rankings) - 1 - i]

        # Left bar (low scenario)
        ax.barh(y, low_delta, height=0.6, color='#e74c3c', alpha=0.8)
        # Right bar (high scenario)
        ax.barh(y, high_delta, height=0.6, color='#27ae60', alpha=0.8)

        # Add elasticity annotation
        max_delta = max(abs(low_delta), abs(high_delta))
        ax.annotate(f'ε = {elasticity:.2f}',
                   xy=(max_delta + 1.5, y),
                   va='center', fontsize=9, fontweight='bold', color='#333')

    # Formatting
    ax.set_yticks(y_positions)
    ax.set_yticklabels([r['name'] for r in reversed(rankings)])
    ax.axvline(x=0, color='black', linewidth=1.5)

    ax.set_xlabel('Change in Share Price from ±10% Input Change ($/share)', fontsize=11)
    ax.set_title(f'Sensitivity Analysis: Elasticity Ranking\n(Base Case: ${base_price:.2f}/share, ε = % Δ Output / % Δ Input)',
                fontsize=13, fontweight='bold')

    # Legend
    red_patch = mpatches.Patch(color='#e74c3c', label='-10% Input')
    green_patch = mpatches.Patch(color='#27ae60', label='+10% Input')
    ax.legend(handles=[green_patch, red_patch], loc='lower right')

    # Add grid
    ax.grid(axis='x', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nChart saved to: {output_path}")

    plt.show()
    return fig


def print_top_3_summary(rankings: list, base_price: float):
    """Print a summary of the top 3 most influential variables."""
    print("\n" + "=" * 70)
    print("TOP 3 MOST INFLUENTIAL INPUT VARIABLES (by Elasticity)")
    print("=" * 70)
    print("\nElasticity (ε) = % change in share price / % change in input")
    print("Higher elasticity = greater sensitivity to that variable")

    for i, item in enumerate(rankings[:3], 1):
        print(f"\n#{i}: {item['name']}")
        print(f"    Elasticity: {item['elasticity']:.2f}x")
        print(f"    Interpretation: A 1% change in {item['name']} causes a {item['elasticity']:.2f}% change in share price")
        print(f"    Base Value: {item['base_val']:.3f}")
        print(f"    Price Range (±10% input): ${item['low_price']:.2f} to ${item['high_price']:.2f}")
        print(f"    Dollar Impact: ±${item['dollar_impact']:.2f}/share")


def main():
    print("=" * 70)
    print("USS Valuation Model - Standardized Sensitivity Analysis")
    print("=" * 70)
    print()

    # Run sensitivity analysis with uniform ±10% perturbation
    results, base_price = run_sensitivity_analysis(perturbation_pct=0.10)

    # Rank by elasticity (standardized comparison)
    rankings = rank_by_elasticity(results)

    # Print top 3 summary
    print_top_3_summary(rankings, base_price)

    # Create tornado chart (all variables)
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'charts',
        'sensitivity_tornado.png'
    )
    create_tornado_chart(rankings, base_price, output_path=output_path)

    # Also create a top-3 only chart
    output_path_top3 = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'charts',
        'sensitivity_tornado_top3.png'
    )
    create_tornado_chart(rankings, base_price, top_n=3, output_path=output_path_top3)

    return rankings, base_price


if __name__ == '__main__':
    rankings, base_price = main()
