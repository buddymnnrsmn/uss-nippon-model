#!/usr/bin/env python3
"""
Monte Carlo Analysis and Visualization
========================================

Runs Monte Carlo simulation and generates comprehensive visualizations.

Usage:
    python scripts/run_monte_carlo_analysis.py [--simulations 10000]
"""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monte_carlo import MonteCarloEngine

# Output directory for charts
CHARTS_DIR = Path(__file__).parent.parent / 'charts'
DATA_DIR = Path(__file__).parent.parent / 'data'


def report_calibration_quality(config_path: Path = None) -> tuple:
    """Categorize MC variables by calibration quality and compute aggregate score.

    Categories:
        recalibrated (1.0): Fitted to observed data with documented methodology
        derived (0.75): Derived from another calibrated variable
        expert (0.5): Expert judgment with stated rationale
        assumed (0.25): Assumed with minimal justification

    Returns (quality_dict, aggregate_score)
    """
    import json
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'monte_carlo' / 'distributions_config.json'

    if not config_path.exists():
        print("  WARNING: distributions_config.json not found")
        return {}, 0.0

    with open(config_path) as f:
        config = json.load(f)

    variables = config.get('variables', {})
    weights = {'recalibrated': 1.0, 'derived': 0.75, 'expert': 0.5, 'assumed': 0.25}
    categories = {}

    for var_name, var_info in variables.items():
        gof = var_info.get('goodness_of_fit', {})
        if gof.get('recalibrated'):
            cat = 'recalibrated'
        elif gof.get('derived'):
            cat = 'derived'
        elif gof.get('expert'):
            cat = 'expert'
        elif gof.get('composite'):
            cat = 'derived'
        elif gof.get('assumed'):
            cat = 'assumed'
        else:
            # Check n_observations
            if var_info.get('n_observations', 0) > 0:
                cat = 'recalibrated'
            else:
                cat = 'assumed'
        categories[var_name] = cat

    # Compute aggregate score
    if categories:
        total_weight = sum(weights[c] for c in categories.values())
        score = total_weight / len(categories)
    else:
        score = 0.0

    # Print summary
    counts = {}
    for cat in ['recalibrated', 'derived', 'expert', 'assumed']:
        vars_in_cat = [v for v, c in categories.items() if c == cat]
        counts[cat] = len(vars_in_cat)

    print("\n--- MC Calibration Quality Report ---")
    print(f"  Total variables: {len(categories)}")
    for cat in ['recalibrated', 'derived', 'expert', 'assumed']:
        pct = counts[cat] / len(categories) * 100 if categories else 0
        vars_list = [v for v, c in categories.items() if c == cat]
        print(f"  {cat:14s}: {counts[cat]:2d} ({pct:5.1f}%) — weight {weights[cat]:.2f}")
        if len(vars_list) <= 6:
            print(f"    {', '.join(vars_list)}")
    print(f"  Aggregate quality score: {score:.3f} (1.0 = all recalibrated)")

    return categories, score


def run_simulation(n_simulations: int = 10000, n_workers: int = 1) -> tuple:
    """Run Monte Carlo simulation and return engine with results"""
    print("=" * 70)
    print("MONTE CARLO SIMULATION")
    print("=" * 70)

    mc = MonteCarloEngine(
        n_simulations=n_simulations,
        use_lhs=True,
        use_config_file=True,
        n_workers=n_workers
    )

    print(f"\nConfig file used: {mc.config_file_used}")
    print(f"Variables: {len(mc.variables)}")

    results = mc.run_simulation(verbose=True)
    mc.calculate_statistics()

    # Report calibration quality
    report_calibration_quality()

    return mc, results


def plot_share_price_distribution(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot histogram of share price distribution"""
    fig, ax = plt.subplots(figsize=(12, 7))

    values = mc.simulation_results['nippon_share_price'].values

    # Histogram
    n, bins, patches = ax.hist(values, bins=50, density=True, alpha=0.7,
                                color='steelblue', edgecolor='white', linewidth=0.5)

    # Fit and overlay normal distribution
    mu, std = np.mean(values), np.std(values)
    x = np.linspace(values.min(), values.max(), 100)
    ax.plot(x, stats.norm.pdf(x, mu, std), 'r-', lw=2, label=f'Normal fit (μ={mu:.1f}, σ={std:.1f})')

    # Key percentiles
    p5 = np.percentile(values, 5)
    p50 = np.percentile(values, 50)
    p95 = np.percentile(values, 95)

    ax.axvline(p5, color='orange', linestyle='--', lw=2, label=f'P5: ${p5:.0f}')
    ax.axvline(p50, color='green', linestyle='-', lw=2, label=f'Median: ${p50:.0f}')
    ax.axvline(p95, color='orange', linestyle='--', lw=2, label=f'P95: ${p95:.0f}')

    # Nippon offer price
    ax.axvline(55, color='red', linestyle='-', lw=3, label='Nippon Offer: $55')

    # Fill area below offer
    below_offer = values[values < 55]
    prob_below = len(below_offer) / len(values) * 100

    ax.set_xlabel('Share Price ($)', fontsize=12)
    ax.set_ylabel('Probability Density', fontsize=12)
    ax.set_title(f'USS Share Price Distribution\n(n={len(values):,} simulations, {prob_below:.1f}% below $55 offer)',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    # Add statistics box
    stats_text = f'Mean: ${mu:.2f}\nMedian: ${p50:.2f}\nStd Dev: ${std:.2f}\n90% CI: [${p5:.0f}, ${p95:.0f}]'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_cumulative_distribution(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot cumulative distribution function"""
    fig, ax = plt.subplots(figsize=(12, 7))

    values = np.sort(mc.simulation_results['nippon_share_price'].values)
    cdf = np.arange(1, len(values) + 1) / len(values)

    ax.plot(values, cdf, 'b-', lw=2)

    # Key reference points
    ax.axvline(55, color='red', linestyle='-', lw=2, label='Nippon Offer: $55')
    ax.axhline(0.5, color='gray', linestyle=':', lw=1, alpha=0.5)

    # Mark key percentiles
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    for p in percentiles:
        val = np.percentile(values, p)
        ax.plot(val, p/100, 'ro', markersize=6)
        ax.annotate(f'P{p}: ${val:.0f}', (val, p/100), textcoords="offset points",
                   xytext=(10, 0), fontsize=9)

    # Probability below offer
    prob_below = np.mean(values < 55)
    ax.plot(55, prob_below, 'r^', markersize=12)
    ax.annotate(f'{prob_below:.1%} below offer', (55, prob_below),
               textcoords="offset points", xytext=(10, 10), fontsize=10, color='red')

    ax.set_xlabel('Share Price ($)', fontsize=12)
    ax.set_ylabel('Cumulative Probability', fontsize=12)
    ax.set_title('Cumulative Distribution Function of USS Share Price', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_tornado_sensitivity(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot tornado chart showing sensitivity to each input"""
    fig, ax = plt.subplots(figsize=(12, 10))

    inputs = mc.simulation_inputs
    outputs = mc.simulation_results['nippon_share_price']

    # Calculate correlation of each input with output
    correlations = {}
    for col in inputs.columns:
        corr = np.corrcoef(inputs[col], outputs)[0, 1]
        correlations[col] = corr

    # Sort by absolute correlation
    sorted_vars = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

    # Take top 15 most impactful
    top_vars = sorted_vars[:15]

    var_names = [v[0] for v in top_vars]
    corr_values = [v[1] for v in top_vars]

    # Create horizontal bar chart
    colors = ['green' if c > 0 else 'red' for c in corr_values]
    y_pos = np.arange(len(var_names))

    ax.barh(y_pos, corr_values, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([v.replace('_', ' ').title() for v in var_names], fontsize=10)
    ax.set_xlabel('Correlation with Share Price', fontsize=12)
    ax.set_title('Sensitivity Analysis: Input Variable Impact on Share Price', fontsize=14, fontweight='bold')
    ax.axvline(0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='x')

    # Add correlation values as labels
    for i, (name, corr) in enumerate(top_vars):
        ax.text(corr + 0.02 if corr > 0 else corr - 0.02, i, f'{corr:.2f}',
               va='center', ha='left' if corr > 0 else 'right', fontsize=9)

    ax.set_xlim(-1, 1)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_input_distributions(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot distributions of key input variables"""
    fig, axes = plt.subplots(3, 3, figsize=(14, 12))
    axes = axes.flatten()

    key_vars = [
        'hrc_price_factor', 'crc_price_factor', 'octg_price_factor',
        'flat_rolled_volume', 'tubular_volume', 'uss_wacc',
        'terminal_growth', 'exit_multiple', 'gary_works_execution'
    ]

    inputs = mc.simulation_inputs

    for i, var in enumerate(key_vars):
        if var not in inputs.columns:
            continue

        ax = axes[i]
        data = inputs[var].values

        ax.hist(data, bins=40, density=True, alpha=0.7, color='steelblue', edgecolor='white')

        # Add mean and std
        mean = np.mean(data)
        std = np.std(data)
        ax.axvline(mean, color='red', linestyle='-', lw=2, label=f'Mean: {mean:.3f}')
        ax.axvline(mean - std, color='orange', linestyle='--', lw=1)
        ax.axvline(mean + std, color='orange', linestyle='--', lw=1, label=f'±1σ')

        ax.set_title(var.replace('_', ' ').title(), fontsize=11, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel('Density')
        ax.legend(fontsize=8, loc='upper right')
        ax.grid(True, alpha=0.3)

    plt.suptitle('Input Variable Distributions', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_correlation_heatmap(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot correlation heatmap of input variables"""
    fig, ax = plt.subplots(figsize=(14, 12))

    inputs = mc.simulation_inputs

    # Select subset of most important variables for readability
    key_vars = [
        'hrc_price_factor', 'crc_price_factor', 'coated_price_factor', 'octg_price_factor',
        'flat_rolled_volume', 'mini_mill_volume', 'tubular_volume',
        'uss_wacc', 'terminal_growth', 'exit_multiple',
        'gary_works_execution', 'mon_valley_execution'
    ]

    available_vars = [v for v in key_vars if v in inputs.columns]
    subset = inputs[available_vars]

    corr_matrix = subset.corr()

    # Create heatmap
    im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Correlation', fontsize=11)

    # Set ticks
    ax.set_xticks(np.arange(len(available_vars)))
    ax.set_yticks(np.arange(len(available_vars)))
    ax.set_xticklabels([v.replace('_', '\n') for v in available_vars], fontsize=9, rotation=45, ha='right')
    ax.set_yticklabels([v.replace('_', ' ') for v in available_vars], fontsize=9)

    # Add correlation values
    for i in range(len(available_vars)):
        for j in range(len(available_vars)):
            val = corr_matrix.iloc[i, j]
            color = 'white' if abs(val) > 0.5 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=8)

    ax.set_title('Input Variable Correlation Matrix', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_price_vs_valuation(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot scatter of HRC price factor vs share price"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    inputs = mc.simulation_inputs
    outputs = mc.simulation_results

    # HRC Price Factor vs Share Price
    ax = axes[0]
    ax.scatter(inputs['hrc_price_factor'], outputs['nippon_share_price'],
               alpha=0.3, s=10, c='steelblue')

    # Add trend line
    z = np.polyfit(inputs['hrc_price_factor'], outputs['nippon_share_price'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(inputs['hrc_price_factor'].min(), inputs['hrc_price_factor'].max(), 100)
    ax.plot(x_line, p(x_line), 'r-', lw=2, label=f'Trend (slope={z[0]:.1f})')

    ax.axhline(55, color='red', linestyle='--', lw=2, alpha=0.7, label='$55 Offer')
    ax.set_xlabel('HRC Price Factor', fontsize=12)
    ax.set_ylabel('Share Price ($)', fontsize=12)
    ax.set_title('HRC Price Factor vs Share Price', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # WACC vs Share Price
    ax = axes[1]
    ax.scatter(inputs['uss_wacc'], outputs['nippon_share_price'],
               alpha=0.3, s=10, c='steelblue')

    z = np.polyfit(inputs['uss_wacc'], outputs['nippon_share_price'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(inputs['uss_wacc'].min(), inputs['uss_wacc'].max(), 100)
    ax.plot(x_line, p(x_line), 'r-', lw=2, label=f'Trend (slope={z[0]:.1f})')

    ax.axhline(55, color='red', linestyle='--', lw=2, alpha=0.7, label='$55 Offer')
    ax.set_xlabel('USS WACC (%)', fontsize=12)
    ax.set_ylabel('Share Price ($)', fontsize=12)
    ax.set_title('WACC vs Share Price', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.suptitle('Key Driver Relationships', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_percentile_waterfall(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot waterfall showing percentile ranges"""
    fig, ax = plt.subplots(figsize=(12, 7))

    values = mc.simulation_results['nippon_share_price'].values

    # Calculate percentiles
    percentiles = {
        'P1': np.percentile(values, 1),
        'P5': np.percentile(values, 5),
        'P10': np.percentile(values, 10),
        'P25': np.percentile(values, 25),
        'P50': np.percentile(values, 50),
        'P75': np.percentile(values, 75),
        'P90': np.percentile(values, 90),
        'P95': np.percentile(values, 95),
        'P99': np.percentile(values, 99),
    }

    # Create bar chart of percentiles
    labels = list(percentiles.keys())
    vals = list(percentiles.values())

    colors = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(labels)))

    bars = ax.bar(labels, vals, color=colors, edgecolor='black', linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
               f'${val:.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Add offer line
    ax.axhline(55, color='red', linestyle='--', lw=2, label='Nippon Offer: $55')

    ax.set_xlabel('Percentile', fontsize=12)
    ax.set_ylabel('Share Price ($)', fontsize=12)
    ax.set_title('Share Price by Percentile', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_scenario_comparison(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot box plots comparing different scenario segments"""
    fig, ax = plt.subplots(figsize=(12, 7))

    inputs = mc.simulation_inputs
    outputs = mc.simulation_results['nippon_share_price'].values

    # Segment by HRC price scenarios
    hrc = inputs['hrc_price_factor'].values

    low_price = outputs[hrc < np.percentile(hrc, 25)]
    mid_price = outputs[(hrc >= np.percentile(hrc, 25)) & (hrc <= np.percentile(hrc, 75))]
    high_price = outputs[hrc > np.percentile(hrc, 75)]

    data = [low_price, mid_price, high_price]
    labels = ['Low Steel Prices\n(Bottom 25%)', 'Mid Steel Prices\n(Middle 50%)', 'High Steel Prices\n(Top 25%)']

    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)

    colors = ['#ff6b6b', '#ffd93d', '#6bcb77']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.axhline(55, color='red', linestyle='--', lw=2, label='Nippon Offer: $55')

    ax.set_ylabel('Share Price ($)', fontsize=12)
    ax.set_title('Share Price Distribution by Steel Price Scenario', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # Add medians as text
    for i, d in enumerate(data):
        median = np.median(d)
        ax.text(i + 1, median + 10, f'Median: ${median:.0f}', ha='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_dual_distribution(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot side-by-side histograms of USS standalone vs Nippon perspective share prices"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    uss_vals = mc.simulation_results['uss_share_price'].values
    nip_vals = mc.simulation_results['nippon_share_price'].values

    for ax, vals, label, color in [
        (ax1, uss_vals, 'USS Standalone', '#2196F3'),
        (ax2, nip_vals, 'Nippon Perspective', '#4CAF50'),
    ]:
        mu, std = np.mean(vals), np.std(vals)
        p5, p50, p95 = np.percentile(vals, [5, 50, 95])

        ax.hist(vals, bins=50, density=True, alpha=0.7, color=color, edgecolor='white', linewidth=0.5)

        # Normal fit
        x = np.linspace(vals.min(), vals.max(), 100)
        ax.plot(x, stats.norm.pdf(x, mu, std), 'k-', lw=1.5, alpha=0.6)

        # Percentile lines
        ax.axvline(p5, color='orange', linestyle='--', lw=1.5, label=f'P5: ${p5:.0f}')
        ax.axvline(p50, color='darkgreen', linestyle='-', lw=2, label=f'Median: ${p50:.0f}')
        ax.axvline(p95, color='orange', linestyle='--', lw=1.5, label=f'P95: ${p95:.0f}')
        ax.axvline(55, color='red', linestyle='-', lw=3, label='$55 Offer')

        prob_below = np.mean(vals < 55) * 100
        ax.set_xlabel('Share Price ($)', fontsize=11)
        ax.set_ylabel('Probability Density', fontsize=11)
        ax.set_title(f'{label}\n({prob_below:.1f}% below $55)', fontsize=13, fontweight='bold')
        ax.legend(fontsize=9, loc='upper right')
        ax.grid(True, alpha=0.3)

        stats_text = f'Mean: ${mu:.2f}\nStd: ${std:.2f}\n90% CI: [${p5:.0f}, ${p95:.0f}]'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.suptitle('Dual-Perspective Share Price Distribution', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_dual_cdf(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot overlaid CDF curves for USS standalone vs Nippon perspective"""
    fig, ax = plt.subplots(figsize=(12, 7))

    for col, label, color in [
        ('uss_share_price', 'USS Standalone', '#2196F3'),
        ('nippon_share_price', 'Nippon Perspective', '#4CAF50'),
    ]:
        vals = np.sort(mc.simulation_results[col].values)
        cdf = np.arange(1, len(vals) + 1) / len(vals)
        ax.plot(vals, cdf, color=color, lw=2.5, label=label)

        prob_below = np.mean(vals < 55)
        ax.plot(55, prob_below, 'o', color=color, markersize=10)
        ax.annotate(f'{prob_below:.1%} below $55', (55, prob_below),
                   textcoords="offset points", xytext=(12, -5 if col == 'uss_share_price' else 8),
                   fontsize=10, color=color, fontweight='bold')

    ax.axvline(55, color='red', linestyle='-', lw=2, alpha=0.7, label='$55 Offer')
    ax.axhline(0.5, color='gray', linestyle=':', lw=1, alpha=0.5)

    ax.set_xlabel('Share Price ($)', fontsize=12)
    ax.set_ylabel('Cumulative Probability', fontsize=12)
    ax.set_title('CDF Comparison: USS Standalone vs Nippon Perspective', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_synergy_premium(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Plot distribution of synergy premium (nippon_price - uss_price)"""
    fig, ax = plt.subplots(figsize=(12, 7))

    premium = mc.simulation_results['nippon_share_price'].values - mc.simulation_results['uss_share_price'].values
    mu, std = np.mean(premium), np.std(premium)
    p5, p50, p95 = np.percentile(premium, [5, 50, 95])

    ax.hist(premium, bins=50, density=True, alpha=0.7, color='#9C27B0', edgecolor='white', linewidth=0.5)

    ax.axvline(p50, color='green', linestyle='-', lw=2, label=f'Median: ${p50:.1f}')
    ax.axvline(p5, color='orange', linestyle='--', lw=1.5, label=f'P5: ${p5:.1f}')
    ax.axvline(p95, color='orange', linestyle='--', lw=1.5, label=f'P95: ${p95:.1f}')
    ax.axvline(0, color='black', linestyle='-', lw=1, alpha=0.5)

    # What % of Nippon value comes from synergies
    nippon_mean = np.mean(mc.simulation_results['nippon_share_price'].values)
    pct_from_synergies = mu / nippon_mean * 100 if nippon_mean > 0 else 0

    ax.set_xlabel('Synergy Premium ($/share)', fontsize=12)
    ax.set_ylabel('Probability Density', fontsize=12)
    ax.set_title(f'Synergy Premium Distribution (Nippon − USS Standalone)\n'
                 f'Mean: ${mu:.1f}/share ({pct_from_synergies:.1f}% of Nippon value)',
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    stats_text = f'Mean: ${mu:.2f}\nStd: ${std:.2f}\n90% CI: [${p5:.1f}, ${p95:.1f}]'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def plot_dual_summary_dashboard(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Create 2x3 dual-perspective summary dashboard"""
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

    uss_vals = mc.simulation_results['uss_share_price'].values
    nip_vals = mc.simulation_results['nippon_share_price'].values
    inputs = mc.simulation_inputs
    premium = nip_vals - uss_vals

    # Row 1, Col 1: USS histogram + stats
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(uss_vals, bins=40, density=True, alpha=0.7, color='#2196F3', edgecolor='white')
    ax1.axvline(55, color='red', linestyle='-', lw=2)
    ax1.axvline(np.median(uss_vals), color='darkgreen', linestyle='-', lw=2)
    prob_uss = np.mean(uss_vals < 55)
    ax1.set_title(f'USS Standalone\nMedian: ${np.median(uss_vals):.0f} | P(<$55): {prob_uss:.1%}',
                  fontweight='bold', fontsize=10)
    ax1.set_xlabel('Share Price ($)')
    ax1.set_ylabel('Density')
    ax1.grid(True, alpha=0.3)

    # Row 1, Col 2: Nippon histogram + stats
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.hist(nip_vals, bins=40, density=True, alpha=0.7, color='#4CAF50', edgecolor='white')
    ax2.axvline(55, color='red', linestyle='-', lw=2)
    ax2.axvline(np.median(nip_vals), color='darkgreen', linestyle='-', lw=2)
    prob_nip = np.mean(nip_vals < 55)
    ax2.set_title(f'Nippon Perspective\nMedian: ${np.median(nip_vals):.0f} | P(<$55): {prob_nip:.1%}',
                  fontweight='bold', fontsize=10)
    ax2.set_xlabel('Share Price ($)')
    ax2.set_ylabel('Density')
    ax2.grid(True, alpha=0.3)

    # Row 1, Col 3: Stats comparison box
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.axis('off')
    stats_text = (
        f"{'':>16}{'USS':>10}{'Nippon':>10}\n"
        f"{'─' * 36}\n"
        f"{'Mean':>16}${np.mean(uss_vals):>8.1f}  ${np.mean(nip_vals):>8.1f}\n"
        f"{'Median':>16}${np.median(uss_vals):>8.1f}  ${np.median(nip_vals):>8.1f}\n"
        f"{'Std Dev':>16}${np.std(uss_vals):>8.1f}  ${np.std(nip_vals):>8.1f}\n"
        f"{'P5':>16}${np.percentile(uss_vals,5):>8.1f}  ${np.percentile(nip_vals,5):>8.1f}\n"
        f"{'P95':>16}${np.percentile(uss_vals,95):>8.1f}  ${np.percentile(nip_vals,95):>8.1f}\n"
        f"{'─' * 36}\n"
        f"{'P(<$55)':>16}{prob_uss:>9.1%}  {prob_nip:>9.1%}\n"
        f"{'P(>$75)':>16}{np.mean(uss_vals>75):>9.1%}  {np.mean(nip_vals>75):>9.1%}\n"
        f"{'─' * 36}\n"
        f"{'Synergy Premium':>16}  ${np.mean(premium):>8.1f}\n"
        f"{'% of Nippon':>16}  {np.mean(premium)/np.mean(nip_vals)*100:>7.1f}%\n"
    )
    ax3.text(0.05, 0.95, stats_text, transform=ax3.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Row 2, Col 1: Dual CDF overlay
    ax4 = fig.add_subplot(gs[1, 0])
    for vals, label, color in [(uss_vals, 'USS', '#2196F3'), (nip_vals, 'Nippon', '#4CAF50')]:
        sorted_v = np.sort(vals)
        cdf = np.arange(1, len(sorted_v) + 1) / len(sorted_v)
        ax4.plot(sorted_v, cdf, color=color, lw=2, label=label)
    ax4.axvline(55, color='red', linestyle='--', lw=2)
    ax4.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    ax4.set_xlabel('Share Price ($)')
    ax4.set_ylabel('Cumulative Probability')
    ax4.set_title('CDF Comparison', fontweight='bold', fontsize=10)
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 1)

    # Row 2, Col 2: Synergy premium distribution
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.hist(premium, bins=40, density=True, alpha=0.7, color='#9C27B0', edgecolor='white')
    ax5.axvline(np.median(premium), color='green', linestyle='-', lw=2, label=f'Median: ${np.median(premium):.1f}')
    ax5.axvline(0, color='black', linestyle='-', lw=1, alpha=0.5)
    ax5.set_xlabel('Premium ($/share)')
    ax5.set_ylabel('Density')
    ax5.set_title('Synergy Premium (Nippon − USS)', fontweight='bold', fontsize=10)
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)

    # Row 2, Col 3: Tornado sensitivity for both
    ax6 = fig.add_subplot(gs[1, 2])
    corr_uss = {col: np.corrcoef(inputs[col], uss_vals)[0, 1] for col in inputs.columns}
    corr_nip = {col: np.corrcoef(inputs[col], nip_vals)[0, 1] for col in inputs.columns}
    # Sort by max absolute correlation across both
    all_vars = sorted(inputs.columns, key=lambda c: max(abs(corr_uss[c]), abs(corr_nip[c])), reverse=True)[:10]
    y_pos = np.arange(len(all_vars))
    bar_h = 0.35
    ax6.barh(y_pos - bar_h/2, [corr_uss[v] for v in all_vars], height=bar_h,
             color='#2196F3', alpha=0.7, label='USS')
    ax6.barh(y_pos + bar_h/2, [corr_nip[v] for v in all_vars], height=bar_h,
             color='#4CAF50', alpha=0.7, label='Nippon')
    ax6.set_yticks(y_pos)
    ax6.set_yticklabels([v.replace('_', ' ').title()[:18] for v in all_vars], fontsize=8)
    ax6.set_xlabel('Correlation')
    ax6.set_title('Sensitivity (Top 10)', fontweight='bold', fontsize=10)
    ax6.axvline(0, color='black', linewidth=0.5)
    ax6.legend(fontsize=8, loc='lower right')
    ax6.grid(True, alpha=0.3, axis='x')
    ax6.set_xlim(-1, 1)

    plt.suptitle('Dual-Perspective Monte Carlo Dashboard', fontsize=15, fontweight='bold', y=0.98)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def create_summary_dashboard(mc: MonteCarloEngine, save_path: Path, verbose: bool = True):
    """Create a comprehensive summary dashboard"""
    fig = plt.figure(figsize=(16, 12))

    # Create grid
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    values = mc.simulation_results['nippon_share_price'].values
    inputs = mc.simulation_inputs

    # 1. Main histogram (top left, spans 2 columns)
    ax1 = fig.add_subplot(gs[0, :2])
    n, bins, patches = ax1.hist(values, bins=50, density=True, alpha=0.7,
                                 color='steelblue', edgecolor='white')
    ax1.axvline(55, color='red', linestyle='-', lw=3, label='$55 Offer')
    ax1.axvline(np.median(values), color='green', linestyle='-', lw=2, label=f'Median: ${np.median(values):.0f}')
    ax1.set_xlabel('Share Price ($)')
    ax1.set_ylabel('Density')
    ax1.set_title('Share Price Distribution', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Statistics box (top right)
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis('off')

    stats_text = f"""
    SIMULATION RESULTS
    ══════════════════════

    Simulations: {len(values):,}

    Central Tendency
    ────────────────
    Mean:      ${np.mean(values):.2f}
    Median:    ${np.median(values):.2f}
    Std Dev:   ${np.std(values):.2f}

    Percentiles
    ────────────────
    P5:   ${np.percentile(values, 5):.0f}
    P25:  ${np.percentile(values, 25):.0f}
    P50:  ${np.percentile(values, 50):.0f}
    P75:  ${np.percentile(values, 75):.0f}
    P95:  ${np.percentile(values, 95):.0f}

    vs $55 Offer
    ────────────────
    P(< $55):  {np.mean(values < 55):.1%}
    P(> $75):  {np.mean(values > 75):.1%}
    P(> $100): {np.mean(values > 100):.1%}
    """
    ax2.text(0.1, 0.95, stats_text, transform=ax2.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 3. Tornado chart (middle row, spans 2 columns)
    ax3 = fig.add_subplot(gs[1, :2])
    correlations = {}
    for col in inputs.columns:
        corr = np.corrcoef(inputs[col], values)[0, 1]
        correlations[col] = corr
    sorted_vars = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
    var_names = [v[0].replace('_', ' ').title()[:20] for v in sorted_vars]
    corr_values = [v[1] for v in sorted_vars]
    colors = ['green' if c > 0 else 'red' for c in corr_values]
    y_pos = np.arange(len(var_names))
    ax3.barh(y_pos, corr_values, color=colors, alpha=0.7)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels(var_names, fontsize=9)
    ax3.set_xlabel('Correlation with Share Price')
    ax3.set_title('Top 10 Sensitivity Drivers', fontweight='bold')
    ax3.axvline(0, color='black', linewidth=0.5)
    ax3.grid(True, alpha=0.3, axis='x')
    ax3.set_xlim(-1, 1)

    # 4. CDF (middle right)
    ax4 = fig.add_subplot(gs[1, 2])
    sorted_vals = np.sort(values)
    cdf = np.arange(1, len(sorted_vals) + 1) / len(sorted_vals)
    ax4.plot(sorted_vals, cdf, 'b-', lw=2)
    ax4.axvline(55, color='red', linestyle='--', lw=2)
    ax4.axhline(0.5, color='gray', linestyle=':', alpha=0.5)
    ax4.set_xlabel('Share Price ($)')
    ax4.set_ylabel('Cumulative Probability')
    ax4.set_title('CDF', fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # 5. HRC scatter (bottom left)
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.scatter(inputs['hrc_price_factor'], values, alpha=0.2, s=5, c='steelblue')
    ax5.axhline(55, color='red', linestyle='--', lw=2)
    ax5.set_xlabel('HRC Price Factor')
    ax5.set_ylabel('Share Price ($)')
    ax5.set_title('HRC Price Impact', fontweight='bold')
    ax5.grid(True, alpha=0.3)

    # 6. WACC scatter (bottom middle)
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.scatter(inputs['uss_wacc'], values, alpha=0.2, s=5, c='steelblue')
    ax6.axhline(55, color='red', linestyle='--', lw=2)
    ax6.set_xlabel('WACC (%)')
    ax6.set_ylabel('Share Price ($)')
    ax6.set_title('WACC Impact', fontweight='bold')
    ax6.grid(True, alpha=0.3)

    # 7. Scenario box plot (bottom right)
    ax7 = fig.add_subplot(gs[2, 2])
    hrc = inputs['hrc_price_factor'].values
    low = values[hrc < np.percentile(hrc, 33)]
    mid = values[(hrc >= np.percentile(hrc, 33)) & (hrc <= np.percentile(hrc, 67))]
    high = values[hrc > np.percentile(hrc, 67)]
    bp = ax7.boxplot([low, mid, high], tick_labels=['Low\nPrices', 'Mid\nPrices', 'High\nPrices'], patch_artist=True)
    for patch, color in zip(bp['boxes'], ['#ff6b6b', '#ffd93d', '#6bcb77']):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax7.axhline(55, color='red', linestyle='--', lw=2)
    ax7.set_ylabel('Share Price ($)')
    ax7.set_title('By Price Scenario', fontweight='bold')
    ax7.grid(True, alpha=0.3, axis='y')

    plt.suptitle('USS/Nippon Steel Monte Carlo Analysis Summary', fontsize=16, fontweight='bold', y=0.98)

    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    if verbose:
        print(f"  Saved: {save_path}")


def main():
    parser = argparse.ArgumentParser(description='Run Monte Carlo analysis and generate visualizations')
    parser.add_argument('--simulations', '-n', type=int, default=5000,
                       help='Number of simulations (default: 5000)')
    parser.add_argument('--workers', '-w', type=int, default=1,
                       help='Number of parallel worker processes (default: 1)')
    args = parser.parse_args()

    # Create output directories
    CHARTS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    # Run simulation
    mc, results = run_simulation(args.simulations, n_workers=args.workers)

    # Print summary
    mc.print_summary()

    # Generate visualizations
    print("\n" + "=" * 70)
    print("GENERATING VISUALIZATIONS")
    print("=" * 70)

    # Define visualization tasks (with verbose=False for cleaner progress bar output)
    visualization_tasks = [
        ("Share Price Distribution", lambda: plot_share_price_distribution(mc, CHARTS_DIR / 'mc_share_price_distribution.png', verbose=False)),
        ("Cumulative Distribution", lambda: plot_cumulative_distribution(mc, CHARTS_DIR / 'mc_cumulative_distribution.png', verbose=False)),
        ("Tornado Sensitivity", lambda: plot_tornado_sensitivity(mc, CHARTS_DIR / 'mc_tornado_sensitivity.png', verbose=False)),
        ("Input Distributions", lambda: plot_input_distributions(mc, CHARTS_DIR / 'mc_input_distributions.png', verbose=False)),
        ("Correlation Heatmap", lambda: plot_correlation_heatmap(mc, CHARTS_DIR / 'mc_correlation_heatmap.png', verbose=False)),
        ("Price vs Valuation", lambda: plot_price_vs_valuation(mc, CHARTS_DIR / 'mc_price_vs_valuation.png', verbose=False)),
        ("Percentile Waterfall", lambda: plot_percentile_waterfall(mc, CHARTS_DIR / 'mc_percentile_waterfall.png', verbose=False)),
        ("Scenario Comparison", lambda: plot_scenario_comparison(mc, CHARTS_DIR / 'mc_scenario_comparison.png', verbose=False)),
        ("Summary Dashboard", lambda: create_summary_dashboard(mc, CHARTS_DIR / 'mc_summary_dashboard.png', verbose=False)),
        ("Dual Distribution", lambda: plot_dual_distribution(mc, CHARTS_DIR / 'mc_dual_distribution.png', verbose=False)),
        ("Dual CDF", lambda: plot_dual_cdf(mc, CHARTS_DIR / 'mc_dual_cdf.png', verbose=False)),
        ("Synergy Premium", lambda: plot_synergy_premium(mc, CHARTS_DIR / 'mc_synergy_premium.png', verbose=False)),
        ("Dual Summary Dashboard", lambda: plot_dual_summary_dashboard(mc, CHARTS_DIR / 'mc_dual_summary_dashboard.png', verbose=False)),
    ]

    # Run visualizations with progress bar
    try:
        from tqdm import tqdm
        print()  # Add newline for cleaner output
        for desc, task in tqdm(visualization_tasks, desc="Creating charts", unit="chart", ncols=100,
                               bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'):
            task()
        print()  # Add newline after progress bar
    except ImportError:
        print("  (Install tqdm for progress bar: pip install tqdm)")
        for desc, task in visualization_tasks:
            print(f"  Creating: {desc}...")
            task()

    # Save data
    print("\n" + "=" * 70)
    print("SAVING DATA")
    print("=" * 70)

    results.to_csv(DATA_DIR / 'monte_carlo_results.csv', index=False)
    print(f"  Saved: {DATA_DIR / 'monte_carlo_results.csv'}")

    mc.simulation_inputs.to_csv(DATA_DIR / 'monte_carlo_inputs.csv', index=False)
    print(f"  Saved: {DATA_DIR / 'monte_carlo_inputs.csv'}")

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"\nCharts saved to: {CHARTS_DIR}")
    print(f"Data saved to: {DATA_DIR}")


if __name__ == '__main__':
    main()
