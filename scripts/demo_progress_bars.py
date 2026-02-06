#!/usr/bin/env python3
"""
Monte Carlo Progress Bar Demo
==============================

Demonstrates the enhanced progress bar functionality for Monte Carlo simulation.

This script runs a quick Monte Carlo simulation with:
- Enhanced progress bars using tqdm
- Both sequential and parallel execution modes
- Visualization generation progress tracking

Usage:
    # Sequential (default)
    python scripts/demo_progress_bars.py

    # Parallel execution
    python scripts/demo_progress_bars.py --workers 4

    # Quick test with fewer simulations
    python scripts/demo_progress_bars.py --simulations 100
"""

import argparse
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monte_carlo import MonteCarloEngine
from price_volume_model import get_scenario_presets, ScenarioType

def demo_sequential_simulation(n_simulations: int = 500):
    """Demo sequential simulation with progress bar"""
    print("\n" + "=" * 70)
    print("DEMO 1: SEQUENTIAL MONTE CARLO SIMULATION")
    print("=" * 70)
    print(f"Running {n_simulations:,} simulations sequentially...")
    print("Watch the progress bar below:")
    print()

    mc = MonteCarloEngine(
        n_simulations=n_simulations,
        use_lhs=True,
        use_config_file=True,
        n_workers=1  # Sequential
    )

    results = mc.run_simulation(verbose=True)
    mc.calculate_statistics()

    print(f"\n✓ Completed {len(results):,} simulations")
    print(f"  Mean share price: ${mc.summary_stats['mean']:.2f}")
    print(f"  Median share price: ${mc.summary_stats['median']:.2f}")
    print(f"  P5-P95 range: ${mc.summary_stats['p05']:.2f} - ${mc.summary_stats['p95']:.2f}")

    return mc


def demo_parallel_simulation(n_simulations: int = 500, n_workers: int = 4):
    """Demo parallel simulation with progress bar"""
    print("\n" + "=" * 70)
    print("DEMO 2: PARALLEL MONTE CARLO SIMULATION")
    print("=" * 70)
    print(f"Running {n_simulations:,} simulations with {n_workers} workers...")
    print("Watch how the progress bar tracks completion across workers:")
    print()

    mc = MonteCarloEngine(
        n_simulations=n_simulations,
        use_lhs=True,
        use_config_file=True,
        n_workers=n_workers  # Parallel
    )

    results = mc.run_simulation(verbose=True)
    mc.calculate_statistics()

    print(f"\n✓ Completed {len(results):,} simulations using {n_workers} workers")
    print(f"  Mean share price: ${mc.summary_stats['mean']:.2f}")
    print(f"  Median share price: ${mc.summary_stats['median']:.2f}")
    print(f"  P5-P95 range: ${mc.summary_stats['p05']:.2f} - ${mc.summary_stats['p95']:.2f}")

    return mc


def demo_visualization_progress():
    """Demo progress bar for visualization generation"""
    print("\n" + "=" * 70)
    print("DEMO 3: VISUALIZATION PROGRESS TRACKING")
    print("=" * 70)
    print("Creating mock visualizations to demonstrate progress tracking...")
    print()

    try:
        from tqdm import tqdm
        import matplotlib.pyplot as plt

        # Simulate creating several charts
        chart_tasks = [
            "Share Price Distribution",
            "Cumulative Distribution",
            "Tornado Sensitivity",
            "Input Distributions",
            "Correlation Heatmap",
            "Summary Dashboard"
        ]

        for task in tqdm(chart_tasks, desc="Creating charts", unit="chart", ncols=100,
                        bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'):
            # Simulate chart creation time
            time.sleep(0.3)

        print("\n✓ All visualizations created successfully")

    except ImportError:
        print("tqdm not installed - install with: pip install tqdm")


def demo_progress_bar_features():
    """Demonstrate various progress bar features"""
    print("\n" + "=" * 70)
    print("DEMO 4: PROGRESS BAR FEATURES")
    print("=" * 70)
    print("Showcasing progress bar capabilities:")
    print()

    try:
        from tqdm import tqdm
        import numpy as np

        # Feature 1: Basic progress with custom format
        print("1. Basic iteration progress:")
        for i in tqdm(range(100), desc="Processing", unit="item", ncols=80):
            time.sleep(0.01)

        print()

        # Feature 2: Nested progress bars
        print("2. Nested progress (outer/inner loops):")
        outer_loop = tqdm(range(5), desc="Outer", position=0, leave=True)
        for i in outer_loop:
            inner_loop = tqdm(range(20), desc=f"  Inner {i+1}", position=1, leave=False)
            for j in inner_loop:
                time.sleep(0.01)
            inner_loop.close()
        outer_loop.close()

        print()

        # Feature 3: Manual updates
        print("3. Manual progress updates:")
        pbar = tqdm(total=1000, desc="Processing data", unit="MB", ncols=80)
        for _ in range(10):
            # Simulate processing
            time.sleep(0.1)
            pbar.update(100)
        pbar.close()

        print()

        # Feature 4: Progress bar with custom statistics
        print("4. Progress with custom postfix stats:")
        values = []
        pbar = tqdm(range(100), desc="Sampling", ncols=100)
        for i in pbar:
            val = np.random.randn()
            values.append(val)
            if len(values) > 0:
                pbar.set_postfix({'mean': f'{np.mean(values):.3f}', 'std': f'{np.std(values):.3f}'})
            time.sleep(0.02)
        pbar.close()

        print("\n✓ Progress bar features demonstrated")

    except ImportError:
        print("tqdm not installed - install with: pip install tqdm")


def main():
    parser = argparse.ArgumentParser(
        description='Demo Monte Carlo progress bars',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick demo with 100 simulations
  python scripts/demo_progress_bars.py --simulations 100

  # Full demo with parallel execution
  python scripts/demo_progress_bars.py --simulations 500 --workers 4

  # Show all progress bar features
  python scripts/demo_progress_bars.py --features-only
        """
    )
    parser.add_argument('--simulations', '-n', type=int, default=500,
                       help='Number of simulations per demo (default: 500)')
    parser.add_argument('--workers', '-w', type=int, default=4,
                       help='Number of workers for parallel demo (default: 4)')
    parser.add_argument('--sequential-only', action='store_true',
                       help='Run only sequential simulation demo')
    parser.add_argument('--parallel-only', action='store_true',
                       help='Run only parallel simulation demo')
    parser.add_argument('--features-only', action='store_true',
                       help='Show only progress bar features demo')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("MONTE CARLO PROGRESS BAR DEMONSTRATION")
    print("=" * 70)
    print()
    print("This demo showcases the enhanced progress tracking for:")
    print("  • Monte Carlo simulation (sequential and parallel)")
    print("  • Visualization generation")
    print("  • Advanced tqdm features")
    print()

    # Check if tqdm is installed
    try:
        import tqdm
        print(f"✓ tqdm {tqdm.__version__} is installed")
    except ImportError:
        print("✗ tqdm is not installed")
        print("\nInstall it with: pip install tqdm")
        print("Or: pip install -r requirements.txt")
        return

    if args.features_only:
        demo_progress_bar_features()
        return

    # Run demos
    if not args.parallel_only:
        mc_seq = demo_sequential_simulation(args.simulations)

    if not args.sequential_only:
        mc_par = demo_parallel_simulation(args.simulations, args.workers)

    if not (args.sequential_only or args.parallel_only):
        demo_visualization_progress()
        demo_progress_bar_features()

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  • Run full analysis: python scripts/run_monte_carlo_analysis.py")
    print("  • Customize simulations: python scripts/run_monte_carlo_analysis.py --simulations 10000")
    print("  • Use parallel mode: python scripts/run_monte_carlo_analysis.py --workers 4")
    print()


if __name__ == '__main__':
    main()
