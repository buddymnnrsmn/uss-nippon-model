#!/usr/bin/env python3
"""
Monte Carlo Simulation Demo
============================

Demonstrates the Monte Carlo sensitivity analysis capabilities.

Usage:
    python scripts/run_monte_carlo_demo.py

This will:
1. Run a Monte Carlo simulation with 1,000 iterations (quick demo)
2. Generate summary statistics
3. Save results to CSV
4. Optionally create visualization plots (if matplotlib available)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from monte_carlo import MonteCarloEngine


def run_demo(n_simulations: int = 1000, create_plots: bool = True):
    """
    Run Monte Carlo demo

    Args:
        n_simulations: Number of Monte Carlo iterations
        create_plots: Whether to create visualization plots
    """
    print("=" * 80)
    print("MONTE CARLO SIMULATION DEMO")
    print("USS / Nippon Steel Merger Valuation")
    print("=" * 80)
    print()

    # Initialize engine
    mc = MonteCarloEngine(
        n_simulations=n_simulations,
        random_seed=42,
        use_lhs=True  # Latin Hypercube Sampling
    )

    print(f"Configuration:")
    print(f"  - Simulations: {n_simulations:,}")
    print(f"  - Sampling method: Latin Hypercube")
    print(f"  - Random seed: 42 (reproducible)")
    print(f"  - Variables: {len(mc.variables)}")
    print()

    # List key variables
    print("Key uncertain variables:")
    for i, (name, var) in enumerate(mc.variables.items(), 1):
        print(f"  {i}. {var.description}")
    print()

    # Run simulation
    results = mc.run_simulation(verbose=True)

    # Calculate statistics
    stats = mc.calculate_statistics()

    # Print summary
    mc.print_summary()

    # Save results
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)

    results_file = output_dir / f'monte_carlo_results_{n_simulations}.csv'
    inputs_file = output_dir / f'monte_carlo_inputs_{n_simulations}.csv'

    mc.simulation_results.to_csv(results_file, index=False)
    mc.simulation_inputs.to_csv(inputs_file, index=False)

    print(f"\n{'='*80}")
    print("RESULTS SAVED")
    print("=" * 80)
    print(f"  Results: {results_file}")
    print(f"  Inputs:  {inputs_file}")

    # Create plots if requested
    if create_plots:
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend

            create_visualization_plots(mc, output_dir)
            print(f"  Plots:   {output_dir / 'monte_carlo_plots.png'}")
        except ImportError:
            print("\n  (matplotlib not available - skipping plots)")

    print()

    return mc, results, stats


def create_visualization_plots(mc: MonteCarloEngine, output_dir: Path):
    """Create visualization plots from Monte Carlo results"""
    import matplotlib.pyplot as plt

    values = mc.simulation_results['nippon_share_price'].values
    stats_dict = mc.summary_stats

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Monte Carlo Simulation Results - USS/Nippon Merger', fontsize=16, fontweight='bold')

    # 1. Histogram
    ax = axes[0, 0]
    ax.hist(values, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    ax.axvline(stats_dict['mean'], color='red', linestyle='--', linewidth=2, label=f"Mean: ${stats_dict['mean']:.2f}")
    ax.axvline(stats_dict['median'], color='green', linestyle='--', linewidth=2, label=f"Median: ${stats_dict['median']:.2f}")
    ax.axvline(55, color='orange', linestyle='-', linewidth=2, label='$55 Offer')
    ax.set_xlabel('Share Price ($)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Valuation Outcomes', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Cumulative Distribution Function
    ax = axes[0, 1]
    sorted_values = np.sort(values)
    cdf = np.arange(1, len(sorted_values) + 1) / len(sorted_values)
    ax.plot(sorted_values, cdf * 100, linewidth=2, color='steelblue')
    ax.axvline(55, color='orange', linestyle='--', linewidth=2, label='$55 Offer')
    ax.axhline(50, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('Share Price ($)', fontsize=12)
    ax.set_ylabel('Cumulative Probability (%)', fontsize=12)
    ax.set_title('Cumulative Distribution Function', fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Box Plot with Percentiles
    ax = axes[1, 0]
    box = ax.boxplot([values], vert=True, patch_artist=True, widths=0.5)
    box['boxes'][0].set_facecolor('lightblue')
    ax.axhline(55, color='orange', linestyle='--', linewidth=2, label='$55 Offer')

    # Add percentile annotations
    percentiles = [stats_dict['p10'], stats_dict['p25'], stats_dict['p50'], stats_dict['p75'], stats_dict['p90']]
    labels = ['P10', 'P25', 'P50', 'P75', 'P90']
    for p, label in zip(percentiles, labels):
        ax.text(1.15, p, f'{label}: ${p:.2f}', va='center', fontsize=10)

    ax.set_ylabel('Share Price ($)', fontsize=12)
    ax.set_title('Percentile Distribution', fontsize=13, fontweight='bold')
    ax.set_xticklabels(['Nippon Value'])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Risk Metrics Summary
    ax = axes[1, 1]
    ax.axis('off')

    risk_text = f"""
    RISK METRICS SUMMARY

    Expected Value:     ${stats_dict['mean']:.2f}
    Median Value:       ${stats_dict['median']:.2f}

    Confidence Intervals:
      80% CI:  ${stats_dict['ci_80_lower']:.2f} - ${stats_dict['ci_80_upper']:.2f}
      90% CI:  ${stats_dict['ci_90_lower']:.2f} - ${stats_dict['ci_90_upper']:.2f}
      95% CI:  ${stats_dict['ci_95_lower']:.2f} - ${stats_dict['ci_95_upper']:.2f}

    Value at Risk:
      VaR (95%):          ${stats_dict['var_95']:.2f}
      CVaR (95%):         ${stats_dict['cvar_95']:.2f}

    Probability Metrics:
      P(Value < $55):     {stats_dict['prob_below_55']:.1%}
      P(Value > $75):     {stats_dict['prob_above_75']:.1%}
      P(Value > $100):    {stats_dict['prob_above_100']:.1%}

    Distribution Shape:
      Std Deviation:      ${stats_dict['std']:.2f}
      Skewness:           {stats_dict['skewness']:.2f}
      Kurtosis:           {stats_dict['kurtosis']:.2f}
    """

    ax.text(0.1, 0.95, risk_text, transform=ax.transAxes,
            fontsize=11, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig(output_dir / 'monte_carlo_plots.png', dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run Monte Carlo simulation demo')
    parser.add_argument('-n', '--simulations', type=int, default=1000,
                       help='Number of Monte Carlo iterations (default: 1000)')
    parser.add_argument('--no-plots', action='store_true',
                       help='Skip creating visualization plots')

    args = parser.parse_args()

    # Run demo
    mc, results, stats = run_demo(
        n_simulations=args.simulations,
        create_plots=not args.no_plots
    )

    print("\nDemo complete!")
    print("\nNext steps:")
    print("  1. Review the summary statistics above")
    print("  2. Open the CSV files to explore individual simulation results")
    print("  3. Adjust distributions in monte_carlo_engine.py to reflect your assumptions")
    print("  4. Run with more iterations (10,000+) for production analysis")
    print()
