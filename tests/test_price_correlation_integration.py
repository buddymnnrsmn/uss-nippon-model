#!/usr/bin/env python3
"""
Integration test for price correlation feature.
Run this to verify all components work together.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.price_correlation_analysis import (
    load_historical_prices,
    aggregate_prices_by_year,
    calculate_price_correlation,
    create_correlation_matrix,
    get_price_trend_summary,
    format_correlation_strength,
    get_correlation_insight_text
)


def test_price_data_loading():
    """Test that historical price data loads correctly"""
    print("=" * 60)
    print("TEST 1: Loading Historical Price Data")
    print("=" * 60)

    try:
        hist_prices = load_historical_prices()
        print("✓ Price data loaded successfully")

        # Check each price series
        for name, df in [
            ('HRC US', hist_prices.hrc_us),
            ('CRC US', hist_prices.crc_us),
            ('HRC EU', hist_prices.hrc_eu),
            ('OCTG US', hist_prices.octg_us)
        ]:
            print(f"  • {name}: {len(df)} observations ({df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d})")

        return hist_prices

    except Exception as e:
        print(f"✗ Failed to load price data: {e}")
        return None


def test_price_aggregation(hist_prices):
    """Test annual price aggregation"""
    print("\n" + "=" * 60)
    print("TEST 2: Annual Price Aggregation")
    print("=" * 60)

    try:
        hrc_annual = aggregate_prices_by_year(hist_prices.hrc_us, 2024, 2033)
        print(f"✓ Aggregated {len(hrc_annual)} years of HRC US data")
        print(f"  • Year range: {hrc_annual.index.min()} - {hrc_annual.index.max()}")
        print(f"  • Price range: ${hrc_annual.min():,.0f} - ${hrc_annual.max():,.0f}/ton")

        return hrc_annual

    except Exception as e:
        print(f"✗ Failed to aggregate prices: {e}")
        return None


def test_correlation_calculation(hrc_annual):
    """Test correlation calculation"""
    print("\n" + "=" * 60)
    print("TEST 3: Correlation Calculation")
    print("=" * 60)

    try:
        # Create synthetic FCF data for testing
        fcf_data = pd.Series(
            np.linspace(1000, 2000, len(hrc_annual)),
            index=hrc_annual.index
        )

        result = calculate_price_correlation(hrc_annual, fcf_data, "FCF")

        print("✓ Correlation calculated successfully")
        print(f"  • Correlation: {result['correlation']:.3f}")
        print(f"  • P-value: {result['p_value']:.4f}")
        print(f"  • Strength: {result['strength']}")
        print(f"  • Observations: {result['n_observations']}")

        return result

    except Exception as e:
        print(f"✗ Failed to calculate correlation: {e}")
        return None


def test_price_trends(hist_prices):
    """Test price trend summary statistics"""
    print("\n" + "=" * 60)
    print("TEST 4: Price Trend Summary Statistics")
    print("=" * 60)

    try:
        hrc_summary = get_price_trend_summary(hist_prices.hrc_us)

        print("✓ Trend summary calculated successfully")
        print(f"  • Mean: ${hrc_summary['mean']:,.0f}/ton")
        print(f"  • Median: ${hrc_summary['median']:,.0f}/ton")
        print(f"  • Range: ${hrc_summary['min']:,.0f} - ${hrc_summary['max']:,.0f}/ton")
        print(f"  • Volatility: {hrc_summary['volatility']*100:.1f}%")
        print(f"  • CAGR: {hrc_summary['cagr']*100:+.1f}% per year")
        print(f"  • Observations: {hrc_summary['n_observations']}")

        return hrc_summary

    except Exception as e:
        print(f"✗ Failed to calculate trend summary: {e}")
        return None


def test_correlation_formatting():
    """Test correlation strength formatting"""
    print("\n" + "=" * 60)
    print("TEST 5: Correlation Strength Formatting")
    print("=" * 60)

    try:
        test_cases = [
            (0.85, "Strong Positive"),
            (-0.75, "Strong Negative"),
            (0.55, "Moderate Positive"),
            (-0.45, "Moderate Negative"),
            (0.25, "Weak"),
            (np.nan, "N/A")
        ]

        print("✓ Testing correlation strength labels:")
        for corr, expected in test_cases:
            strength, color = format_correlation_strength(corr)
            status = "✓" if expected.lower() in strength.lower() else "✗"
            corr_str = f"{corr:.2f}" if not np.isnan(corr) else "NaN"
            print(f"  {status} r={corr_str} → {strength} (color: {color})")

        return True

    except Exception as e:
        print(f"✗ Failed to format correlations: {e}")
        return False


def test_insight_generation():
    """Test insight text generation"""
    print("\n" + "=" * 60)
    print("TEST 6: Correlation Insight Text Generation")
    print("=" * 60)

    try:
        insight = get_correlation_insight_text(0.82, "HRC US", "FCF", 0.001)

        print("✓ Insight text generated successfully")
        print(f"\n{insight}\n")

        # Check for key phrases
        checks = [
            ("correlation" in insight.lower(), "Contains 'correlation'"),
            ("HRC US" in insight, "Mentions price type"),
            ("FCF" in insight, "Mentions metric"),
            ("significant" in insight.lower(), "Discusses significance")
        ]

        for check, desc in checks:
            print(f"  {'✓' if check else '✗'} {desc}")

        return insight

    except Exception as e:
        print(f"✗ Failed to generate insight text: {e}")
        return None


def test_correlation_matrix():
    """Test full correlation matrix creation"""
    print("\n" + "=" * 60)
    print("TEST 7: Correlation Matrix Creation")
    print("=" * 60)

    try:
        hist_prices = load_historical_prices()

        # Create synthetic consolidated data with correct column names
        years = range(2024, 2034)
        consolidated = pd.DataFrame({
            'Year': years,
            'Revenue': np.linspace(10000, 15000, 10),
            'Total_EBITDA': np.linspace(2000, 3000, 10),
            'FCF': np.linspace(1000, 2000, 10),
            'Total_Volume_000tons': np.linspace(15000, 18000, 10)
        })

        segment_dfs = {}  # Empty for this test

        matrix = create_correlation_matrix(
            segment_dfs,
            consolidated,
            hist_prices,
            2024,
            2033
        )

        print("✓ Correlation matrix created successfully")
        print(f"  • Shape: {matrix.shape[0]} price types × {matrix.shape[1]} metrics")
        print(f"  • Price types: {list(matrix.index)}")
        print(f"  • Metrics: {list(matrix.columns)}")

        # Display matrix
        print("\nCorrelation Matrix:")
        print(matrix.to_string(float_format=lambda x: f"{x:6.2f}" if not np.isnan(x) else "   N/A"))

        return matrix

    except Exception as e:
        print(f"✗ Failed to create correlation matrix: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all integration tests"""
    print("\n" + "=" * 60)
    print("PRICE CORRELATION FEATURE - INTEGRATION TEST")
    print("=" * 60)

    results = {}

    # Test 1: Load price data
    hist_prices = test_price_data_loading()
    results['load_prices'] = hist_prices is not None

    if hist_prices is None:
        print("\n✗ Cannot continue tests without price data")
        print("\nTo resolve:")
        print("  1. Check that CSV files exist in market-data/exports/processed/")
        print("  2. Verify file names: hrc_us_spot.csv, crc_us_spot.csv, hrc_eu_spot.csv, octg_us_spot.csv")
        return

    # Test 2: Aggregate prices
    hrc_annual = test_price_aggregation(hist_prices)
    results['aggregate_prices'] = hrc_annual is not None

    # Test 3: Calculate correlation
    if hrc_annual is not None:
        corr_result = test_correlation_calculation(hrc_annual)
        results['calculate_correlation'] = corr_result is not None

    # Test 4: Price trends
    trend_summary = test_price_trends(hist_prices)
    results['price_trends'] = trend_summary is not None

    # Test 5: Correlation formatting
    results['format_correlation'] = test_correlation_formatting()

    # Test 6: Insight generation
    insight = test_insight_generation()
    results['generate_insights'] = insight is not None

    # Test 7: Correlation matrix
    matrix = test_correlation_matrix()
    results['correlation_matrix'] = matrix is not None

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n✓ All integration tests passed! Feature is ready to use.")
        return 0
    else:
        print(f"\n✗ {total_tests - passed_tests} test(s) failed. Review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
