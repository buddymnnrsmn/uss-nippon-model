#!/usr/bin/env python3
"""
Distribution Validation Script
================================

Validates the calibrated probability distributions from distributions_config.json.

Validation Checks:
1. Statistical validation: Sample 100k from each distribution, verify statistics match
2. Business bounds: 99% CI within reasonable business range
3. Correlation validation: Joint samples produce sensible scenarios
4. Backtesting: Fit to historical period, test coverage on out-of-sample period

Usage:
    python scripts/validate_distributions.py [--config monte_carlo/distributions_config.json]
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import cholesky

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monte_carlo.distribution_fitter import validate_distribution_params


# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG_PATH = Path(__file__).parent.parent / 'monte_carlo' / 'distributions_config.json'
DATA_DIR = Path(__file__).parent.parent / 'market-data' / 'exports' / 'processed'

# Business bounds for validation (99% CI should fall within these)
BUSINESS_BOUNDS = {
    'hrc_price_factor': (0.30, 3.00),      # 30% to 300% of baseline
    'crc_price_factor': (0.30, 3.00),
    'coated_price_factor': (0.30, 3.00),
    'octg_price_factor': (0.20, 4.00),      # Higher volatility
    'flat_rolled_volume': (0.50, 1.50),     # -50% to +50%
    'mini_mill_volume': (0.60, 1.40),       # Less volatile
    'tubular_volume': (0.20, 2.00),         # High volatility
    'uss_wacc': (7.0, 15.0),                # 7% to 15%
    'japan_rf_rate': (-0.5, 3.0),           # Negative rates possible
    'terminal_growth': (-2.0, 5.0),         # Broad range
    'exit_multiple': (2.0, 10.0),           # 2x to 10x
    'gary_works_execution': (0.0, 1.0),     # 0% to 100%
    'mon_valley_execution': (0.0, 1.0),
    'flat_rolled_margin_factor': (0.50, 1.80),
    'operating_synergy_factor': (0.0, 1.0),
    'revenue_synergy_factor': (0.0, 1.0),
    'working_capital_efficiency': (0.50, 1.50),
    'capex_intensity_factor': (0.50, 2.00),
}


# =============================================================================
# SAMPLING FUNCTIONS
# =============================================================================

def sample_distribution(dist_type: str, params: dict, n: int, rng: np.random.RandomState) -> np.ndarray:
    """Generate samples from a distribution"""

    if dist_type == 'normal':
        return rng.normal(params['mean'], params['std'], n)

    elif dist_type == 'lognormal':
        return rng.lognormal(params['mean'], params['std'], n)

    elif dist_type == 'triangular':
        return rng.triangular(params['min'], params['mode'], params['max'], n)

    elif dist_type == 'beta':
        beta_samples = rng.beta(params['alpha'], params['beta'], n)
        return params['min'] + beta_samples * (params['max'] - params['min'])

    elif dist_type == 'uniform':
        return rng.uniform(params['min'], params['max'], n)

    elif dist_type == 'truncnorm':
        a = (params['min'] - params['mean']) / params['std']
        b = (params['max'] - params['mean']) / params['std']
        return stats.truncnorm.rvs(a, b, loc=params['mean'], scale=params['std'], size=n, random_state=rng)

    else:
        raise ValueError(f"Unknown distribution type: {dist_type}")


def theoretical_statistics(dist_type: str, params: dict) -> dict:
    """Calculate theoretical mean and std for a distribution"""

    if dist_type == 'normal':
        return {
            'mean': params['mean'],
            'std': params['std']
        }

    elif dist_type == 'lognormal':
        mu, sigma = params['mean'], params['std']
        return {
            'mean': np.exp(mu + sigma**2 / 2),
            'std': np.sqrt((np.exp(sigma**2) - 1) * np.exp(2*mu + sigma**2))
        }

    elif dist_type == 'triangular':
        a, c, b = params['min'], params['mode'], params['max']
        mean = (a + b + c) / 3
        var = (a**2 + b**2 + c**2 - a*b - a*c - b*c) / 18
        return {
            'mean': mean,
            'std': np.sqrt(var)
        }

    elif dist_type == 'beta':
        alpha, beta_param = params['alpha'], params['beta']
        min_val, max_val = params['min'], params['max']
        range_val = max_val - min_val

        beta_mean = alpha / (alpha + beta_param)
        beta_var = (alpha * beta_param) / ((alpha + beta_param)**2 * (alpha + beta_param + 1))

        return {
            'mean': min_val + range_val * beta_mean,
            'std': range_val * np.sqrt(beta_var)
        }

    elif dist_type == 'uniform':
        a, b = params['min'], params['max']
        return {
            'mean': (a + b) / 2,
            'std': (b - a) / np.sqrt(12)
        }

    else:
        return {'mean': np.nan, 'std': np.nan}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_statistical_properties(config: dict, n_samples: int = 100000) -> dict:
    """
    Validate that sampled statistics match theoretical values

    Returns dict with validation results for each variable
    """
    print("\n" + "=" * 70)
    print("STATISTICAL VALIDATION (100,000 samples per variable)")
    print("=" * 70)

    rng = np.random.RandomState(42)
    results = {}

    for var_name, var_config in config['variables'].items():
        dist_type = var_config['distribution_type']
        params = var_config['parameters']

        # Validate parameters first
        errors = validate_distribution_params(dist_type, params)
        if errors:
            print(f"  {var_name}: INVALID PARAMETERS - {errors}")
            results[var_name] = {'valid': False, 'errors': errors}
            continue

        # Sample from distribution
        try:
            samples = sample_distribution(dist_type, params, n_samples, rng)
        except Exception as e:
            print(f"  {var_name}: SAMPLING FAILED - {e}")
            results[var_name] = {'valid': False, 'error': str(e)}
            continue

        # Calculate sample statistics
        sample_mean = np.mean(samples)
        sample_std = np.std(samples, ddof=1)
        sample_min = np.min(samples)
        sample_max = np.max(samples)
        sample_p01 = np.percentile(samples, 1)
        sample_p99 = np.percentile(samples, 99)

        # Get theoretical statistics
        theoretical = theoretical_statistics(dist_type, params)

        # Check if sample statistics are close to theoretical
        mean_error = abs(sample_mean - theoretical['mean']) / max(abs(theoretical['mean']), 0.001)
        std_error = abs(sample_std - theoretical['std']) / max(theoretical['std'], 0.001)

        is_valid = mean_error < 0.05 and std_error < 0.10  # 5% mean tolerance, 10% std tolerance

        results[var_name] = {
            'valid': is_valid,
            'distribution_type': dist_type,
            'sample_mean': float(sample_mean),
            'theoretical_mean': float(theoretical['mean']),
            'mean_error_pct': float(mean_error * 100),
            'sample_std': float(sample_std),
            'theoretical_std': float(theoretical['std']),
            'std_error_pct': float(std_error * 100),
            'sample_min': float(sample_min),
            'sample_max': float(sample_max),
            'p01': float(sample_p01),
            'p99': float(sample_p99),
        }

        status = "OK" if is_valid else "WARN"
        print(f"  {var_name}: {status}")
        print(f"    Mean: {sample_mean:.4f} (theoretical: {theoretical['mean']:.4f}, error: {mean_error*100:.1f}%)")
        print(f"    Std:  {sample_std:.4f} (theoretical: {theoretical['std']:.4f}, error: {std_error*100:.1f}%)")

    # Summary
    n_valid = sum(1 for r in results.values() if r.get('valid', False))
    print(f"\n  Summary: {n_valid}/{len(results)} variables passed statistical validation")

    return results


def validate_business_bounds(config: dict, n_samples: int = 100000) -> dict:
    """
    Validate that 99% CI falls within reasonable business bounds

    Returns dict with validation results for each variable
    """
    print("\n" + "=" * 70)
    print("BUSINESS BOUNDS VALIDATION (99% CI within reasonable range)")
    print("=" * 70)

    rng = np.random.RandomState(42)
    results = {}

    for var_name, var_config in config['variables'].items():
        dist_type = var_config['distribution_type']
        params = var_config['parameters']

        # Get business bounds for this variable
        bounds = BUSINESS_BOUNDS.get(var_name)
        if bounds is None:
            print(f"  {var_name}: SKIPPED (no bounds defined)")
            results[var_name] = {'valid': True, 'skipped': True}
            continue

        # Sample from distribution
        try:
            samples = sample_distribution(dist_type, params, n_samples, rng)
        except:
            results[var_name] = {'valid': False, 'error': 'sampling failed'}
            continue

        # Calculate 99% CI
        p01 = np.percentile(samples, 0.5)
        p99 = np.percentile(samples, 99.5)

        # Check bounds
        lower_ok = p01 >= bounds[0] or (p01 >= bounds[0] * 0.9)  # Allow 10% slack
        upper_ok = p99 <= bounds[1] or (p99 <= bounds[1] * 1.1)  # Allow 10% slack

        is_valid = lower_ok and upper_ok

        results[var_name] = {
            'valid': is_valid,
            'p01': float(p01),
            'p99': float(p99),
            'business_lower': bounds[0],
            'business_upper': bounds[1],
            'lower_ok': lower_ok,
            'upper_ok': upper_ok,
        }

        status = "OK" if is_valid else "WARN"
        bound_issues = []
        if not lower_ok:
            bound_issues.append(f"P0.5={p01:.3f} < {bounds[0]}")
        if not upper_ok:
            bound_issues.append(f"P99.5={p99:.3f} > {bounds[1]}")

        print(f"  {var_name}: {status}")
        print(f"    99% CI: [{p01:.3f}, {p99:.3f}], bounds: [{bounds[0]}, {bounds[1]}]")
        if bound_issues:
            print(f"    Issues: {', '.join(bound_issues)}")

    # Summary
    n_valid = sum(1 for r in results.values() if r.get('valid', False))
    print(f"\n  Summary: {n_valid}/{len(results)} variables passed business bounds validation")

    return results


def validate_correlations(config: dict, n_samples: int = 10000) -> dict:
    """
    Validate correlation structure produces sensible joint scenarios

    Returns dict with validation results
    """
    print("\n" + "=" * 70)
    print("CORRELATION VALIDATION")
    print("=" * 70)

    correlations = config.get('correlations', {})
    variables = config['variables']

    if not correlations:
        print("  No correlations defined in config")
        return {'valid': True, 'note': 'no correlations to validate'}

    rng = np.random.RandomState(42)

    # Build list of variables that have correlations
    var_names = list(variables.keys())
    n_vars = len(var_names)

    # Build correlation matrix
    corr_matrix = np.eye(n_vars)

    for i, var1 in enumerate(var_names):
        if var1 in correlations:
            for var2, corr_val in correlations[var1].items():
                if var2 in var_names:
                    j = var_names.index(var2)
                    corr_matrix[i, j] = corr_val
                    corr_matrix[j, i] = corr_val

    # Check if positive semi-definite
    eigenvalues = np.linalg.eigvalsh(corr_matrix)
    is_psd = np.all(eigenvalues >= -1e-10)

    print(f"  Correlation matrix: {n_vars}x{n_vars}")
    print(f"  Positive semi-definite: {is_psd}")

    if not is_psd:
        print(f"    WARNING: Min eigenvalue = {np.min(eigenvalues):.6f}")
        # Make PSD by adding small value to diagonal
        corr_matrix += np.eye(n_vars) * (abs(np.min(eigenvalues)) + 0.01)
        D = np.diag(1.0 / np.sqrt(np.diag(corr_matrix)))
        corr_matrix = D @ corr_matrix @ D

    # Generate correlated samples
    try:
        L = cholesky(corr_matrix, lower=True)
        standard_normal = rng.randn(n_samples, n_vars)
        correlated_normal = standard_normal @ L.T

        # Transform to target distributions
        samples = {}
        for i, var_name in enumerate(var_names):
            uniform_samples = stats.norm.cdf(correlated_normal[:, i])
            var_config = variables[var_name]
            dist_type = var_config['distribution_type']
            params = var_config['parameters']

            if dist_type == 'normal':
                samples[var_name] = stats.norm.ppf(uniform_samples, params['mean'], params['std'])
            elif dist_type == 'lognormal':
                samples[var_name] = stats.lognorm.ppf(uniform_samples, s=params['std'], scale=np.exp(params['mean']))
            elif dist_type == 'triangular':
                c = (params['mode'] - params['min']) / (params['max'] - params['min'])
                samples[var_name] = stats.triang.ppf(uniform_samples, c, loc=params['min'], scale=params['max']-params['min'])
            elif dist_type == 'beta':
                beta_samples = stats.beta.ppf(uniform_samples, params['alpha'], params['beta'])
                samples[var_name] = params['min'] + beta_samples * (params['max'] - params['min'])
            else:
                samples[var_name] = uniform_samples  # Fallback to uniform

        samples_df = pd.DataFrame(samples)

        # Check realized correlations
        realized_corr = samples_df.corr()

        print("\n  Key correlation checks:")
        correlation_results = []

        for var1, corr_dict in correlations.items():
            if var1 not in var_names:
                continue
            for var2, target_corr in corr_dict.items():
                if var2 not in var_names:
                    continue

                realized = realized_corr.loc[var1, var2]
                error = abs(realized - target_corr)

                is_ok = error < 0.15  # Allow 15% tolerance
                status = "OK" if is_ok else "WARN"

                print(f"    {var1} <-> {var2}: target={target_corr:.3f}, realized={realized:.3f} ({status})")
                correlation_results.append({
                    'var1': var1,
                    'var2': var2,
                    'target': target_corr,
                    'realized': realized,
                    'error': error,
                    'valid': is_ok
                })

        # Check for sensible scenarios
        print("\n  Scenario sensibility checks:")

        # High HRC price should come with high CRC price
        if 'hrc_price_factor' in samples and 'crc_price_factor' in samples:
            high_hrc = samples_df['hrc_price_factor'] > samples_df['hrc_price_factor'].quantile(0.90)
            crc_when_high_hrc = samples_df.loc[high_hrc, 'crc_price_factor'].mean()
            crc_overall = samples_df['crc_price_factor'].mean()

            check_ok = crc_when_high_hrc > crc_overall
            print(f"    When HRC is high (>P90): CRC mean = {crc_when_high_hrc:.3f} vs overall {crc_overall:.3f} ({'OK' if check_ok else 'WARN'})")

        # Low WACC should come with lower (not higher) prices (flight to safety)
        if 'uss_wacc' in samples and 'hrc_price_factor' in samples:
            low_wacc = samples_df['uss_wacc'] < samples_df['uss_wacc'].quantile(0.10)
            hrc_when_low_wacc = samples_df.loc[low_wacc, 'hrc_price_factor'].mean()
            hrc_overall = samples_df['hrc_price_factor'].mean()

            # Correlation should be negative (lower rates -> lower commodity prices in risk-off)
            corr = samples_df['uss_wacc'].corr(samples_df['hrc_price_factor'])
            print(f"    WACC-HRC correlation: {corr:.3f} (expected negative)")

        return {
            'valid': is_psd,
            'is_psd': is_psd,
            'correlation_checks': correlation_results,
        }

    except Exception as e:
        print(f"  ERROR generating correlated samples: {e}")
        return {'valid': False, 'error': str(e)}


def validate_backtesting(config: dict) -> dict:
    """
    Backtest distributions: fit to 2018-2020, test coverage on 2021-2023

    Returns dict with backtesting results
    """
    print("\n" + "=" * 70)
    print("BACKTESTING VALIDATION (train 2018-2020, test 2021-2023)")
    print("=" * 70)

    results = {}

    # Test HRC price factor
    hrc_file = DATA_DIR / 'hrc_us_futures.csv'
    if hrc_file.exists():
        hrc_data = pd.read_csv(hrc_file, parse_dates=['date'])

        # Split into train/test
        train_mask = (hrc_data['date'] >= '2018-01-01') & (hrc_data['date'] < '2021-01-01')
        test_mask = (hrc_data['date'] >= '2021-01-01') & (hrc_data['date'] < '2024-01-01')

        train_data = hrc_data.loc[train_mask, 'value'].values / 780  # Factor
        test_data = hrc_data.loc[test_mask, 'value'].values / 780

        if len(train_data) > 100 and len(test_data) > 100:
            # Fit lognormal to training data
            log_train = np.log(train_data)
            train_mu = np.mean(log_train)
            train_sigma = np.std(log_train, ddof=1)

            # Test coverage on test data
            log_test = np.log(test_data)

            # What % of test data falls within training distribution's 90% CI?
            p05_train = np.exp(train_mu + stats.norm.ppf(0.05) * train_sigma)
            p95_train = np.exp(train_mu + stats.norm.ppf(0.95) * train_sigma)

            coverage = np.mean((test_data >= p05_train) & (test_data <= p95_train))

            print(f"  HRC Price Factor:")
            print(f"    Training period: 2018-2020 ({len(train_data)} obs)")
            print(f"    Training 90% CI: [{p05_train:.3f}, {p95_train:.3f}]")
            print(f"    Test period: 2021-2023 ({len(test_data)} obs)")
            print(f"    Test data coverage: {coverage:.1%} within training 90% CI")

            results['hrc_price_factor'] = {
                'train_n': len(train_data),
                'test_n': len(test_data),
                'train_90_ci': [float(p05_train), float(p95_train)],
                'test_coverage': float(coverage),
                'valid': coverage > 0.60  # At least 60% coverage expected
            }

            if coverage < 0.70:
                print(f"    WARNING: Low coverage suggests distribution shift between periods")
        else:
            print(f"  HRC: Insufficient data for backtesting")

    # Test capacity utilization
    capacity_file = DATA_DIR / 'capacity_us.csv'
    if capacity_file.exists():
        capacity_data = pd.read_csv(capacity_file, parse_dates=['date'])

        train_mask = (capacity_data['date'] >= '2018-01-01') & (capacity_data['date'] < '2021-01-01')
        test_mask = (capacity_data['date'] >= '2021-01-01') & (capacity_data['date'] < '2024-01-01')

        train_values = capacity_data.loc[train_mask, 'value'].values
        test_values = capacity_data.loc[test_mask, 'value'].values

        if len(train_values) > 50 and len(test_values) > 50:
            # Normalize to factors
            train_mean = np.mean(train_values)
            train_factors = train_values / train_mean
            test_factors = test_values / train_mean  # Use training mean!

            train_mu = np.mean(train_factors)
            train_sigma = np.std(train_factors, ddof=1)

            p05 = train_mu - 1.645 * train_sigma
            p95 = train_mu + 1.645 * train_sigma

            coverage = np.mean((test_factors >= p05) & (test_factors <= p95))

            print(f"\n  Capacity Utilization Factor:")
            print(f"    Training period: 2018-2020 ({len(train_factors)} obs)")
            print(f"    Training 90% CI: [{p05:.3f}, {p95:.3f}]")
            print(f"    Test period: 2021-2023 ({len(test_factors)} obs)")
            print(f"    Test data coverage: {coverage:.1%} within training 90% CI")

            results['capacity_factor'] = {
                'train_n': len(train_factors),
                'test_n': len(test_factors),
                'train_90_ci': [float(p05), float(p95)],
                'test_coverage': float(coverage),
                'valid': coverage > 0.60
            }

    if not results:
        print("  No data available for backtesting")
        return {'valid': True, 'note': 'no backtesting data available'}

    n_valid = sum(1 for r in results.values() if r.get('valid', False))
    print(f"\n  Summary: {n_valid}/{len(results)} backtests passed")

    return results


# =============================================================================
# MAIN VALIDATION
# =============================================================================

def run_validation(config_path: Path) -> dict:
    """
    Run all validation checks

    Returns dict with all validation results
    """
    print("=" * 70)
    print("DISTRIBUTION VALIDATION")
    print(f"Config: {config_path}")
    print("=" * 70)

    # Load config
    with open(config_path) as f:
        config = json.load(f)

    print(f"\nConfig version: {config['version']}")
    print(f"Calibration date: {config['calibration_date']}")
    print(f"Variables: {len(config['variables'])}")

    # Run validations
    results = {
        'config_path': str(config_path),
        'validation_timestamp': datetime.now().isoformat(),
        'config_version': config['version'],
    }

    # 1. Statistical validation
    results['statistical'] = validate_statistical_properties(config)

    # 2. Business bounds validation
    results['business_bounds'] = validate_business_bounds(config)

    # 3. Correlation validation
    results['correlations'] = validate_correlations(config)

    # 4. Backtesting
    results['backtesting'] = validate_backtesting(config)

    # Overall summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    n_stat_valid = sum(1 for r in results['statistical'].values() if r.get('valid', False))
    n_stat_total = len(results['statistical'])

    n_bounds_valid = sum(1 for r in results['business_bounds'].values() if r.get('valid', False))
    n_bounds_total = len(results['business_bounds'])

    corr_valid = results['correlations'].get('valid', True)

    n_bt_valid = sum(1 for r in results.get('backtesting', {}).values() if isinstance(r, dict) and r.get('valid', False))
    n_bt_total = len([r for r in results.get('backtesting', {}).values() if isinstance(r, dict)])

    print(f"  Statistical validation:   {n_stat_valid}/{n_stat_total} passed")
    print(f"  Business bounds:          {n_bounds_valid}/{n_bounds_total} passed")
    print(f"  Correlation structure:    {'VALID' if corr_valid else 'ISSUES'}")
    print(f"  Backtesting:              {n_bt_valid}/{n_bt_total} passed")

    overall_valid = (
        n_stat_valid == n_stat_total and
        n_bounds_valid == n_bounds_total and
        corr_valid
    )

    results['overall_valid'] = overall_valid

    print(f"\n  OVERALL: {'PASSED' if overall_valid else 'ISSUES FOUND'}")
    print("=" * 70)

    return results


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Validate calibrated probability distributions'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=str(CONFIG_PATH),
        help='Path to distributions_config.json'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output path for validation results JSON'
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    results = run_validation(config_path)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
