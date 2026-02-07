#!/usr/bin/env python3
"""
Price Calibrator
================

Calibrates benchmark prices from Bloomberg data for model integration.
Provides current prices, scenario price factors, and historical comparisons.

Usage:
    from market_data.bloomberg import get_current_benchmark_prices

    prices = get_current_benchmark_prices()
    if prices:
        # Use Bloomberg prices
        hrc_price = prices['hrc_us']
    else:
        # Fall back to defaults
        pass
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .bloomberg_data_service import get_bloomberg_service, is_bloomberg_available


# Hardcoded fallback prices (used only if Bloomberg unavailable)
_HARDCODED_BENCHMARK_PRICES = {
    'hrc_us': 680,      # US HRC Midwest (rough average)
    'crc_us': 850,      # US CRC
    'coated_us': 950,   # US Coated/Galvanized
    'hrc_eu': 620,      # EU HRC
    'octg': 2800,       # OCTG (Oil Country Tubular Goods)
}

# 2023 annual average prices from Bloomberg data (ANALYSIS EFFECTIVE DATE: YE 2023)
# Calculated from 51-52 weekly observations in 2023
# These provide a more representative baseline than year-end point-in-time prices
#
# These are the ACTUAL 2023 annual averages from Bloomberg.
# Scenario factors (in scenario_calibrator.py) express prices relative to this baseline.
BLOOMBERG_BENCHMARK_PRICES_2023 = {
    'hrc_us': 916,      # US HRC Midwest (2023 annual avg)
    'crc_us': 1127,     # US CRC (2023 annual avg)
    'coated_us': 1263,  # US Coated/Galvanized (CRC * 1.12)
    'hrc_eu': 717,      # EU HRC (2023 annual avg)
    'octg': 2750,       # OCTG (2023 annual avg) - note: elevated due to energy cycle
}

# DEFAULT_BENCHMARK_PRICES uses Bloomberg 2023 data
DEFAULT_BENCHMARK_PRICES = BLOOMBERG_BENCHMARK_PRICES_2023.copy()


@dataclass
class PriceComparison:
    """Comparison of current vs default prices"""
    benchmark: str
    current_price: float
    default_price: float
    difference: float
    percent_change: float
    percentile_vs_history: Optional[float]
    latest_date: Optional[datetime]


def get_current_benchmark_prices(use_analysis_date: bool = True) -> Optional[Dict[str, float]]:
    """
    Get benchmark prices from Bloomberg data.

    By default, returns year-end 2023 prices to match the analysis effective date.

    Args:
        use_analysis_date: If True (default), return year-end 2023 prices.
                          If False, return latest/current prices.

    Returns:
        Dict with keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        Returns None if Bloomberg data unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        if use_analysis_date:
            prices = service.get_benchmark_prices_2023()
        else:
            prices = service.get_current_prices()

        # Ensure we have all required keys
        required_keys = ['hrc_us', 'crc_us', 'coated_us', 'hrc_eu', 'octg']
        for key in required_keys:
            if key not in prices:
                # Try to derive missing values
                if key == 'coated_us' and 'crc_us' in prices:
                    prices['coated_us'] = prices['crc_us'] * 1.12
                else:
                    prices[key] = DEFAULT_BENCHMARK_PRICES.get(key)

        return prices

    except Exception as e:
        print(f"Warning: Failed to get Bloomberg prices: {e}")
        return None


def get_latest_benchmark_prices() -> Optional[Dict[str, float]]:
    """
    Get the latest/current benchmark prices from Bloomberg data.

    Use this when you need current market prices instead of the
    year-end 2023 analysis baseline.

    Returns:
        Dict with keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        Returns None if Bloomberg data unavailable.
    """
    return get_current_benchmark_prices(use_analysis_date=False)


def get_scenario_price_factors(scenario_type: str) -> Optional[Dict[str, float]]:
    """
    Get price factors for a scenario based on historical percentiles.

    Maps scenario types to historical price percentiles:
    - severe_downturn: 10th percentile
    - downside: 25th percentile
    - base_case: 50th percentile (median)
    - above_average: 65th percentile
    - optimistic: 75th percentile

    Returns:
        Dict with price factors (1.0 = current price) for each benchmark,
        or None if Bloomberg data unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        # Load scenario mapping from config
        config_path = Path(__file__).parent / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)

        scenario_mapping = config.get('scenario_price_mapping', {})
        scenario_config = scenario_mapping.get(scenario_type.lower().replace(' ', '_'))

        if not scenario_config:
            return None

        percentile = scenario_config.get('percentile', 50)

        # Get current prices and historical percentiles
        current_prices = service.get_current_prices()
        factors = {}

        # Map internal keys to model fields
        price_keys = {
            'hrc_us': 'hrc_us',
            'crc_us': 'crc_us',
            'hrc_eu': 'hrc_eu',
            'octg_us': 'octg',
        }

        for data_key, model_key in price_keys.items():
            stats = service.get_price_stats(data_key)
            if stats and model_key in current_prices:
                current = current_prices[model_key]

                # Get historical percentile value
                percentile_value = service.get_price_percentile(data_key, percentile)
                if percentile_value and current > 0:
                    # Factor = scenario_price / current_price
                    factors[model_key] = percentile_value / current
                else:
                    factors[model_key] = 1.0
            else:
                factors[model_key] = 1.0

        # Handle coated_us (derived from CRC)
        if 'crc_us' in factors:
            factors['coated_us'] = factors['crc_us']

        return factors

    except Exception as e:
        print(f"Warning: Failed to get scenario price factors: {e}")
        return None


def compare_current_to_historical() -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Compare current prices to historical statistics.

    Returns:
        Dict with comparison data for each benchmark, including:
        - current_price
        - avg_1y, avg_5y
        - percentiles (10, 25, 50, 75, 90)
        - current_percentile (where current falls in distribution)
        - vs_avg_1y (percent difference from 1Y average)
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        comparisons = {}

        # Price series to compare
        price_keys = {
            'hrc_us': 'US HRC Midwest',
            'crc_us': 'US CRC',
            'hrc_eu': 'EU HRC',
            'octg_us': 'OCTG',
        }

        for key, name in price_keys.items():
            stats = service.get_price_stats(key)
            if not stats:
                continue

            comparison = {
                'name': name,
                'current_price': stats.latest_value,
                'latest_date': stats.latest_date.isoformat() if stats.latest_date else None,
                'avg_1m': stats.avg_1m,
                'avg_3m': stats.avg_3m,
                'avg_1y': stats.avg_1y,
                'avg_5y': stats.avg_5y,
                'percentile_10': stats.percentile_10,
                'percentile_25': stats.percentile_25,
                'percentile_50': stats.percentile_50,
                'percentile_75': stats.percentile_75,
                'percentile_90': stats.percentile_90,
                'volatility_1y': stats.volatility_1y,
                'min_historical': stats.min_value,
                'max_historical': stats.max_value,
            }

            # Calculate current percentile in distribution
            if stats.min_value is not None and stats.max_value is not None:
                range_val = stats.max_value - stats.min_value
                if range_val > 0:
                    comparison['current_percentile'] = (
                        (stats.latest_value - stats.min_value) / range_val * 100
                    )

            # Calculate vs 1Y average
            if stats.avg_1y and stats.avg_1y > 0:
                comparison['vs_avg_1y'] = (stats.latest_value / stats.avg_1y - 1) * 100

            comparisons[key] = comparison

        return comparisons

    except Exception as e:
        print(f"Warning: Failed to compare prices: {e}")
        return None


def get_price_comparison_table(compare_to_current: bool = False) -> List[PriceComparison]:
    """
    Get a comparison table of Bloomberg 2023 prices vs hardcoded fallbacks,
    or optionally compare current prices to 2023 baseline.

    Args:
        compare_to_current: If True, compare latest prices to 2023 baseline.
                           If False (default), compare 2023 Bloomberg to hardcoded fallbacks.

    Returns:
        List of PriceComparison objects for display in dashboard.
    """
    comparisons = []

    # Get Bloomberg 2023 prices (analysis baseline)
    bloomberg_2023_prices = get_current_benchmark_prices(use_analysis_date=True)

    if compare_to_current:
        # Compare current prices to 2023 baseline
        current_prices = get_current_benchmark_prices(use_analysis_date=False)
        baseline = bloomberg_2023_prices or BLOOMBERG_BENCHMARK_PRICES_2023
    else:
        # Compare 2023 Bloomberg to hardcoded fallbacks
        current_prices = bloomberg_2023_prices
        baseline = _HARDCODED_BENCHMARK_PRICES

    if not current_prices:
        # No Bloomberg data - return empty comparisons
        for benchmark, default in _HARDCODED_BENCHMARK_PRICES.items():
            comparisons.append(PriceComparison(
                benchmark=benchmark,
                current_price=default,
                default_price=default,
                difference=0,
                percent_change=0,
                percentile_vs_history=None,
                latest_date=None,
            ))
        return comparisons

    # Get historical comparison for percentiles
    historical = compare_current_to_historical() or {}

    # Build comparison for each benchmark
    benchmark_names = {
        'hrc_us': 'HRC US',
        'crc_us': 'CRC US',
        'coated_us': 'Coated US',
        'hrc_eu': 'HRC EU',
        'octg': 'OCTG',
    }

    # Map to historical data keys
    historical_keys = {
        'hrc_us': 'hrc_us',
        'crc_us': 'crc_us',
        'coated_us': 'crc_us',  # Use CRC data for coated
        'hrc_eu': 'hrc_eu',
        'octg': 'octg_us',
    }

    for benchmark, name in benchmark_names.items():
        current = current_prices.get(benchmark)
        default = baseline.get(benchmark)

        if current is None:
            current = default

        difference = current - default if current and default else 0
        percent_change = (difference / default * 100) if default and default > 0 else 0

        # Get percentile from historical data
        hist_key = historical_keys.get(benchmark)
        hist_data = historical.get(hist_key, {})
        percentile = hist_data.get('current_percentile')

        # Get latest date
        latest_date = None
        if hist_data.get('latest_date'):
            try:
                latest_date = datetime.fromisoformat(hist_data['latest_date'])
            except (ValueError, TypeError):
                pass

        comparisons.append(PriceComparison(
            benchmark=name,
            current_price=current,
            default_price=default,
            difference=difference,
            percent_change=percent_change,
            percentile_vs_history=percentile,
            latest_date=latest_date,
        ))

    return comparisons


def get_price_factors_vs_2023() -> Dict[str, float]:
    """
    Get current prices as factors vs 2023 baseline.

    Returns:
        Dict with factors (current / 2023) for each benchmark.
        Factor > 1.0 means current > 2023, < 1.0 means current < 2023.
    """
    factors = {}
    current_prices = get_current_benchmark_prices()

    if not current_prices:
        # Return 1.0 factors (no change)
        return {k: 1.0 for k in DEFAULT_BENCHMARK_PRICES.keys()}

    for benchmark, default in DEFAULT_BENCHMARK_PRICES.items():
        current = current_prices.get(benchmark, default)
        factors[benchmark] = current / default if default > 0 else 1.0

    return factors


if __name__ == '__main__':
    # Demo usage
    print("Price Calibrator Demo")
    print("=" * 50)

    print("\n1. Current Benchmark Prices:")
    prices = get_current_benchmark_prices()
    if prices:
        for k, v in prices.items():
            default = DEFAULT_BENCHMARK_PRICES.get(k, 0)
            diff = ((v / default) - 1) * 100 if default else 0
            print(f"  {k}: ${v:,.0f} ({diff:+.1f}% vs 2023)")
    else:
        print("  Bloomberg data not available")

    print("\n2. Price Comparison Table:")
    comparisons = get_price_comparison_table()
    for c in comparisons:
        print(f"  {c.benchmark}: ${c.current_price:,.0f} vs ${c.default_price:,.0f} "
              f"({c.percent_change:+.1f}%)")

    print("\n3. Scenario Price Factors:")
    for scenario in ['severe_downturn', 'downside', 'base_case', 'above_average', 'optimistic']:
        factors = get_scenario_price_factors(scenario)
        if factors:
            hrc = factors.get('hrc_us', 1.0)
            print(f"  {scenario}: HRC factor = {hrc:.2f}")
        else:
            print(f"  {scenario}: N/A")

    print("\n4. Historical Comparison:")
    historical = compare_current_to_historical()
    if historical:
        for key, data in historical.items():
            current = data['current_price']
            avg_1y = data.get('avg_1y')
            vs_avg = data.get('vs_avg_1y', 0)
            print(f"  {key}: ${current:,.0f} ({vs_avg:+.1f}% vs 1Y avg)")
    else:
        print("  Historical data not available")
