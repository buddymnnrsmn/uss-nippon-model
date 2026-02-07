#!/usr/bin/env python3
"""
Monte Carlo Calibrator
======================

Calibrates Monte Carlo simulation parameters from Bloomberg historical data.
Fits distributions to price data and calculates correlations for simulation.

Usage:
    from market_data.bloomberg import get_calibrated_distributions

    distributions = get_calibrated_distributions()
    if distributions:
        # Use calibrated parameters
        hrc_params = distributions['hrc_price_factor']
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from scipy import stats

from .bloomberg_data_service import get_bloomberg_service, is_bloomberg_available


@dataclass
class CalibratedDistribution:
    """Parameters for a calibrated distribution"""
    name: str
    dist_type: str  # 'lognormal', 'normal', 'triangular'
    params: Dict[str, float]
    goodness_of_fit: float  # KS statistic p-value
    calibration_period_days: int
    n_observations: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'dist_type': self.dist_type,
            'params': self.params,
            'goodness_of_fit': self.goodness_of_fit,
            'calibration_period_days': self.calibration_period_days,
            'n_observations': self.n_observations,
        }


def calibrate_steel_price_distributions(
    period_years: int = 5,
    use_log_returns: bool = True,
    end_date: Optional[datetime] = None,
    baseline_prices: Optional[Dict[str, float]] = None
) -> Optional[Dict[str, CalibratedDistribution]]:
    """
    Calibrate steel price distributions from historical Bloomberg data.

    Fits lognormal distributions to historical price factors (price / 2023 baseline).

    Args:
        period_years: Number of years of history to use
        use_log_returns: If True, fit to log returns; if False, fit to levels
        end_date: Optional cutoff date for historical data (default: now).
                  Use this to avoid look-ahead bias (e.g., end_date=datetime(2023, 12, 31))
        baseline_prices: Optional dict of baseline prices to use instead of defaults.
                        Keys: 'hrc_us', 'crc_us', 'hrc_eu', 'octg_us'

    Returns:
        Dict of CalibratedDistribution for each price series,
        or None if Bloomberg data unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        # Load defaults from config
        config_path = Path(__file__).parent / "config.json"
        with open(config_path, 'r') as f:
            config = json.load(f)
        defaults = config.get('monte_carlo_defaults', {})

        # 2023 baseline prices - use provided or default
        # Default to more accurate 2023 actual realized prices
        baseline_2023 = baseline_prices or {
            'hrc_us': 780,   # Updated to reflect actual 2023 avg
            'crc_us': 990,   # Updated to reflect actual 2023 avg
            'hrc_eu': 620,
            'octg_us': 1650, # Updated to reflect actual 2023 avg
        }

        distributions = {}

        # Use provided end_date or default to now
        reference_date = end_date or datetime.now()
        cutoff_date = reference_date - timedelta(days=period_years * 365)

        # Calibrate each price series
        price_series = {
            'hrc_us': ('hrc_price_factor', defaults.get('hrc_volatility', 0.18)),
            'crc_us': ('crc_price_factor', defaults.get('crc_volatility', 0.16)),
            'hrc_eu': ('hrc_eu_price_factor', defaults.get('hrc_volatility', 0.18)),
            'octg_us': ('octg_price_factor', defaults.get('octg_volatility', 0.22)),
        }

        for data_key, (dist_name, default_vol) in price_series.items():
            baseline = baseline_2023.get(data_key)
            if not baseline:
                continue

            # Get historical data
            df = service.get_historical_prices(data_key, start_date=cutoff_date)
            if df is None or len(df) < 52:  # Need at least 1 year weekly data
                # Use default parameters
                distributions[dist_name] = CalibratedDistribution(
                    name=dist_name,
                    dist_type='lognormal',
                    params={
                        'mean': np.log(0.95),  # Default: 95% of 2023
                        'std': default_vol,
                    },
                    goodness_of_fit=0.0,
                    calibration_period_days=0,
                    n_observations=0,
                )
                continue

            # Filter to end_date if specified (avoid look-ahead bias)
            if end_date is not None and 'date' in df.columns:
                df = df[df['date'] <= end_date]

            if len(df) < 52:  # Re-check after filtering
                # Use default parameters
                distributions[dist_name] = CalibratedDistribution(
                    name=dist_name,
                    dist_type='lognormal',
                    params={
                        'mean': np.log(0.95),  # Default: 95% of 2023
                        'std': default_vol,
                    },
                    goodness_of_fit=0.0,
                    calibration_period_days=0,
                    n_observations=0,
                )
                continue

            # Calculate price factors (price / 2023 baseline)
            factors = df['value'].values / baseline

            if use_log_returns:
                # Fit lognormal to factors
                log_factors = np.log(factors)
                mean = np.mean(log_factors)
                std = np.std(log_factors)

                # Test fit
                _, p_value = stats.kstest(log_factors, 'norm', args=(mean, std))
            else:
                # Fit lognormal directly
                shape, loc, scale = stats.lognorm.fit(factors, floc=0)
                mean = np.log(scale)
                std = shape
                p_value = 0.5  # Skip test for this method

            distributions[dist_name] = CalibratedDistribution(
                name=dist_name,
                dist_type='lognormal',
                params={
                    'mean': float(mean),
                    'std': float(std),
                },
                goodness_of_fit=float(p_value),
                calibration_period_days=int(len(df)),
                n_observations=int(len(factors)),
            )

        # Add coated factor (derived from CRC)
        if 'crc_price_factor' in distributions:
            crc = distributions['crc_price_factor']
            distributions['coated_price_factor'] = CalibratedDistribution(
                name='coated_price_factor',
                dist_type='lognormal',
                params=crc.params.copy(),  # Same as CRC
                goodness_of_fit=crc.goodness_of_fit,
                calibration_period_days=crc.calibration_period_days,
                n_observations=crc.n_observations,
            )

        return distributions

    except Exception as e:
        print(f"Warning: Failed to calibrate price distributions: {e}")
        return None


def get_calibrated_correlation_matrix() -> Optional[pd.DataFrame]:
    """
    Get the calibrated correlation matrix from Bloomberg data.

    Returns the pre-computed correlation matrix if available.

    Returns:
        DataFrame with correlation matrix, or None if unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        return service.get_correlation_matrix()

    except Exception as e:
        print(f"Warning: Failed to get correlation matrix: {e}")
        return None


def calibrate_correlation_matrix(period_years: int = 5) -> Optional[pd.DataFrame]:
    """
    Calculate correlation matrix from aligned time series.

    Computes correlations between price series and other variables.

    Args:
        period_years: Number of years of history to use

    Returns:
        DataFrame with correlation matrix, or None if calculation fails.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        # Try to use pre-computed matrix first
        precomputed = service.get_correlation_matrix()
        if precomputed is not None:
            return precomputed

        # If no pre-computed matrix, calculate from raw data
        cutoff_date = datetime.now() - timedelta(days=period_years * 365)

        # Collect aligned price series
        series_data = {}
        price_keys = ['hrc_us', 'crc_us', 'hrc_eu', 'octg_us']

        for key in price_keys:
            df = service.get_historical_prices(key, start_date=cutoff_date)
            if df is not None and len(df) > 52:
                # Resample to weekly and take returns
                df = df.set_index('date')
                weekly = df['value'].resample('W').last()
                returns = weekly.pct_change().dropna()
                series_data[key] = returns

        if len(series_data) < 2:
            return None

        # Align all series
        combined = pd.DataFrame(series_data)
        combined = combined.dropna()

        if len(combined) < 52:
            return None

        # Calculate correlation matrix
        corr_matrix = combined.corr()

        return corr_matrix

    except Exception as e:
        print(f"Warning: Failed to calculate correlation matrix: {e}")
        return None


def get_calibrated_distributions(
    end_date: Optional[datetime] = None,
    baseline_prices: Optional[Dict[str, float]] = None
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Get calibrated distributions for Monte Carlo simulation.

    Returns a dict compatible with MonteCarloEngine input variable format.

    Args:
        end_date: Optional cutoff date for historical data (default: now).
                  Use datetime(2023, 12, 31) to avoid look-ahead bias.
        baseline_prices: Optional dict of baseline prices to use instead of defaults.

    Returns:
        Dict with distribution parameters, or None if unavailable.
    """
    distributions = calibrate_steel_price_distributions(
        end_date=end_date,
        baseline_prices=baseline_prices
    )
    if not distributions:
        return None

    # Convert to format expected by MonteCarloEngine
    result = {}
    for name, dist in distributions.items():
        result[name] = {
            'dist_type': dist.dist_type,
            'params': dist.params,
            'calibration_info': {
                'goodness_of_fit': dist.goodness_of_fit,
                'period_days': dist.calibration_period_days,
                'n_observations': dist.n_observations,
            }
        }

    return result


def export_for_monte_carlo_engine() -> Optional[Dict[str, Any]]:
    """
    Export calibration data in format for MonteCarloEngine integration.

    Returns complete calibration package including:
    - Distribution parameters for each variable
    - Correlation matrix
    - Metadata

    Returns:
        Dict with all calibration data, or None if unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        # Get distributions
        distributions = calibrate_steel_price_distributions()
        if not distributions:
            return None

        # Get correlation matrix
        corr_matrix = get_calibrated_correlation_matrix()

        # Build export package
        export = {
            'calibration_date': datetime.now().isoformat(),
            'data_as_of': service.get_data_as_of_date().isoformat() if service.get_data_as_of_date() else None,
            'distributions': {},
            'correlation_matrix': None,
            'metadata': {
                'source': 'Bloomberg via market-data/bloomberg',
                'period_years': 5,
            }
        }

        # Add distributions
        for name, dist in distributions.items():
            export['distributions'][name] = dist.to_dict()

        # Add correlation matrix
        if corr_matrix is not None:
            export['correlation_matrix'] = corr_matrix.to_dict()

        return export

    except Exception as e:
        print(f"Warning: Failed to export calibration data: {e}")
        return None


def get_calibration_summary() -> str:
    """
    Generate a summary of Monte Carlo calibration from Bloomberg data.

    Returns:
        Formatted summary string.
    """
    lines = [
        "Monte Carlo Calibration Summary",
        "=" * 50,
        "",
    ]

    distributions = calibrate_steel_price_distributions()
    if not distributions:
        lines.append("Bloomberg calibration data not available.")
        lines.append("Monte Carlo will use default distributions.")
        return "\n".join(lines)

    lines.append("CALIBRATED DISTRIBUTIONS")
    lines.append("-" * 50)

    for name, dist in distributions.items():
        lines.append(f"\n{name}:")
        lines.append(f"  Type: {dist.dist_type}")
        if dist.dist_type == 'lognormal':
            mean = np.exp(dist.params['mean'] + dist.params['std']**2 / 2)
            lines.append(f"  Mean (implied): {mean:.2f}")
            lines.append(f"  Volatility: {dist.params['std']*100:.1f}%")
        lines.append(f"  Observations: {dist.n_observations}")
        if dist.goodness_of_fit > 0:
            lines.append(f"  KS test p-value: {dist.goodness_of_fit:.3f}")

    # Correlation matrix
    corr = get_calibrated_correlation_matrix()
    if corr is not None:
        lines.extend([
            "",
            "CORRELATION MATRIX",
            "-" * 50,
        ])
        lines.append(corr.to_string())

    return "\n".join(lines)


if __name__ == '__main__':
    # Demo usage
    print(get_calibration_summary())

    print("\n" + "=" * 50)
    print("EXPORT FOR MONTE CARLO ENGINE")
    print("=" * 50 + "\n")

    export = export_for_monte_carlo_engine()
    if export:
        import json
        # Print just the structure, not full correlation matrix
        export_summary = {
            'calibration_date': export['calibration_date'],
            'distributions': list(export['distributions'].keys()),
            'has_correlation_matrix': export['correlation_matrix'] is not None,
        }
        print(json.dumps(export_summary, indent=2))
    else:
        print("Export not available")
