"""
Price Correlation Analysis Utility

This module provides functions to analyze correlations between historical steel prices
and company financial metrics for the USS-Nippon merger model.

Key Features:
- Load historical price data from weekly CSV exports
- Aggregate prices to annual averages matching projection periods
- Calculate Pearson correlations between prices and metrics
- Generate correlation matrices and trend summaries
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from pathlib import Path
from scipy.stats import pearsonr


@dataclass
class HistoricalPriceData:
    """Container for historical steel price series"""
    hrc_us: pd.DataFrame
    crc_us: pd.DataFrame
    hrc_eu: pd.DataFrame
    octg_us: pd.DataFrame

    def get_price_series(self, price_type: str) -> Optional[pd.DataFrame]:
        """Get price series by type name"""
        mapping = {
            "HRC US": self.hrc_us,
            "CRC US": self.crc_us,
            "HRC EU": self.hrc_eu,
            "OCTG US": self.octg_us
        }
        return mapping.get(price_type)


def load_historical_prices(base_path: str = "market-data/exports/processed") -> HistoricalPriceData:
    """
    Load historical steel price data from CSV exports.

    Args:
        base_path: Directory containing price CSV files

    Returns:
        HistoricalPriceData object with all price series

    Raises:
        FileNotFoundError: If price files are missing
        ValueError: If CSV format is invalid
    """
    base_dir = Path(base_path)

    # Define file paths
    files = {
        'hrc_us': base_dir / 'hrc_us_spot.csv',
        'crc_us': base_dir / 'crc_us_spot.csv',
        'hrc_eu': base_dir / 'hrc_eu_spot.csv',
        'octg_us': base_dir / 'octg_us_spot.csv'
    }

    # Load each file
    price_data = {}
    for key, filepath in files.items():
        if not filepath.exists():
            raise FileNotFoundError(f"Price file not found: {filepath}")

        df = pd.read_csv(filepath)

        # Validate required columns
        if 'date' not in df.columns or 'value' not in df.columns:
            raise ValueError(f"CSV must contain 'date' and 'value' columns: {filepath}")

        # Parse dates
        df['date'] = pd.to_datetime(df['date'])

        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)

        price_data[key] = df

    return HistoricalPriceData(**price_data)


def aggregate_prices_by_year(
    df: pd.DataFrame,
    start_year: int = 2024,
    end_year: int = 2033
) -> pd.Series:
    """
    Aggregate weekly price data to annual averages.

    Args:
        df: DataFrame with 'date' and 'value' columns
        start_year: First year to include
        end_year: Last year to include

    Returns:
        Series indexed by year with annual average prices
    """
    # Extract year from date
    df = df.copy()
    df['year'] = df['date'].dt.year

    # Calculate annual averages
    annual_avg = df.groupby('year')['value'].mean()

    # Filter to projection window
    annual_avg = annual_avg[(annual_avg.index >= start_year) &
                            (annual_avg.index <= end_year)]

    return annual_avg


def calculate_price_correlation(
    price_series: pd.Series,
    metric_series: pd.Series,
    metric_name: str
) -> Dict[str, any]:
    """
    Calculate Pearson correlation between price and financial metric.

    Args:
        price_series: Annual average prices indexed by year
        metric_series: Annual metric values indexed by year
        metric_name: Name of the metric for reporting

    Returns:
        Dictionary with correlation, p_value, strength, and metadata
    """
    # Align series by index (year)
    aligned = pd.DataFrame({
        'price': price_series,
        'metric': metric_series
    }).dropna()

    if len(aligned) < 3:
        return {
            'correlation': np.nan,
            'p_value': np.nan,
            'strength': 'insufficient_data',
            'n_observations': len(aligned),
            'metric_name': metric_name
        }

    # Calculate Pearson correlation
    corr, p_value = pearsonr(aligned['price'], aligned['metric'])

    # Determine strength
    abs_corr = abs(corr)
    if abs_corr >= 0.7:
        strength = 'strong'
    elif abs_corr >= 0.4:
        strength = 'moderate'
    else:
        strength = 'weak'

    return {
        'correlation': corr,
        'p_value': p_value,
        'strength': strength,
        'n_observations': len(aligned),
        'metric_name': metric_name
    }


def create_correlation_matrix(
    segment_dfs: Dict[str, pd.DataFrame],
    consolidated: pd.DataFrame,
    historical_prices: HistoricalPriceData,
    start_year: int = 2024,
    end_year: int = 2033
) -> pd.DataFrame:
    """
    Build correlation matrix between steel prices and company metrics.

    Args:
        segment_dfs: Dictionary of segment DataFrames
        consolidated: Consolidated company DataFrame
        historical_prices: Historical price data
        start_year: First projection year
        end_year: Last projection year

    Returns:
        DataFrame with prices as rows, metrics as columns
    """
    # Define price types
    price_types = {
        'HRC US': historical_prices.hrc_us,
        'CRC US': historical_prices.crc_us,
        'HRC EU': historical_prices.hrc_eu,
        'OCTG US': historical_prices.octg_us
    }

    # Define metrics to correlate (use actual column names from consolidated DataFrame)
    metrics = {
        'USS Value': None,  # Will be calculated if available
        'Revenue': consolidated.set_index('Year')['Revenue'] if 'Revenue' in consolidated.columns else None,
        'EBITDA': consolidated.set_index('Year')['Total_EBITDA'] if 'Total_EBITDA' in consolidated.columns else None,
        'FCF': consolidated.set_index('Year')['FCF'] if 'FCF' in consolidated.columns else None,
        'Volume': consolidated.set_index('Year')['Total_Volume_000tons'] if 'Total_Volume_000tons' in consolidated.columns else None
    }

    # Initialize correlation matrix
    corr_matrix = pd.DataFrame(
        index=price_types.keys(),
        columns=metrics.keys(),
        dtype=float
    )

    # Calculate correlations
    for price_name, price_df in price_types.items():
        # Aggregate price to annual
        annual_price = aggregate_prices_by_year(price_df, start_year, end_year)

        for metric_name, metric_series in metrics.items():
            if metric_series is None:
                corr_matrix.loc[price_name, metric_name] = np.nan
                continue

            result = calculate_price_correlation(
                annual_price,
                metric_series,
                metric_name
            )

            corr_matrix.loc[price_name, metric_name] = result['correlation']

    return corr_matrix


def get_price_trend_summary(price_df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate summary statistics for a price series.

    Args:
        price_df: DataFrame with 'date' and 'value' columns

    Returns:
        Dictionary with mean, min, max, volatility, CAGR
    """
    prices = price_df['value'].values
    dates = pd.to_datetime(price_df['date'])

    # Basic statistics
    summary = {
        'mean': float(np.mean(prices)),
        'median': float(np.median(prices)),
        'min': float(np.min(prices)),
        'max': float(np.max(prices)),
        'std': float(np.std(prices)),
        'volatility': float(np.std(prices) / np.mean(prices))  # Coefficient of variation
    }

    # Calculate CAGR if we have sufficient data
    if len(prices) >= 2:
        years_elapsed = (dates.max() - dates.min()).days / 365.25
        if years_elapsed > 0:
            cagr = (prices[-1] / prices[0]) ** (1 / years_elapsed) - 1
            summary['cagr'] = float(cagr)
        else:
            summary['cagr'] = 0.0
    else:
        summary['cagr'] = 0.0

    # Add date range
    summary['start_date'] = dates.min().strftime('%Y-%m-%d')
    summary['end_date'] = dates.max().strftime('%Y-%m-%d')
    summary['n_observations'] = len(prices)

    return summary


def align_price_with_projections(
    price_df: pd.DataFrame,
    projection_years: pd.Series
) -> pd.Series:
    """
    Align historical price data with projection years using annual averages.

    Args:
        price_df: DataFrame with 'date' and 'value' columns
        projection_years: Series or array of projection years (e.g., 2024-2033)

    Returns:
        Series indexed by projection years with annual average prices
    """
    # Calculate annual averages for all years in the price data
    df = price_df.copy()
    df['year'] = pd.to_datetime(df['date']).dt.year
    annual_avg = df.groupby('year')['value'].mean()

    # Reindex to match projection years
    aligned = annual_avg.reindex(projection_years, method=None)

    return aligned


def calculate_segment_price_sensitivity(
    segment_df: pd.DataFrame,
    price_series: pd.Series,
    segment_name: str
) -> Dict[str, any]:
    """
    Calculate price sensitivity for a specific segment.

    Args:
        segment_df: Segment projection DataFrame with 'Year' column
        price_series: Annual average prices indexed by year
        segment_name: Name of the segment

    Returns:
        Dictionary with correlation metrics and sensitivity analysis
    """
    # Align data by year
    df = segment_df.set_index('Year')

    metrics_to_analyze = {
        'Revenue': df.get('Revenue', None),
        'EBITDA': df.get('EBITDA', None),
        'FCF': df.get('FCF', None),
        'Volume': df.get('Total_Volume', None)
    }

    results = {
        'segment': segment_name,
        'correlations': {}
    }

    for metric_name, metric_series in metrics_to_analyze.items():
        if metric_series is not None and not metric_series.isna().all():
            corr_result = calculate_price_correlation(
                price_series,
                metric_series,
                metric_name
            )
            results['correlations'][metric_name] = corr_result

    return results


def format_correlation_strength(correlation: float) -> Tuple[str, str]:
    """
    Format correlation value with strength descriptor and color.

    Args:
        correlation: Correlation coefficient (-1 to 1)

    Returns:
        Tuple of (strength_text, color_code)
    """
    abs_corr = abs(correlation)

    if np.isnan(correlation):
        return "N/A", "#888888"
    elif abs_corr >= 0.7:
        direction = "Positive" if correlation > 0 else "Negative"
        return f"Strong {direction}", "#ff6b6b" if correlation < 0 else "#4ecdc4"
    elif abs_corr >= 0.4:
        direction = "Positive" if correlation > 0 else "Negative"
        return f"Moderate {direction}", "#ffa07a" if correlation < 0 else "#45b7d1"
    else:
        return "Weak", "#888888"


def get_correlation_insight_text(
    correlation: float,
    price_type: str,
    metric_name: str,
    p_value: float
) -> str:
    """
    Generate natural language insight for a correlation result.

    Args:
        correlation: Correlation coefficient
        price_type: Type of steel price (e.g., "HRC US")
        metric_name: Name of the metric
        p_value: Statistical significance p-value

    Returns:
        Formatted insight text
    """
    if np.isnan(correlation):
        return f"Insufficient data to calculate correlation between {price_type} and {metric_name}."

    strength, _ = format_correlation_strength(correlation)
    direction = "increases" if correlation > 0 else "decreases"

    significance = "statistically significant" if p_value < 0.05 else "not statistically significant"

    text = (
        f"{strength.lower()} correlation (r={correlation:.2f}, p={p_value:.3f}) "
        f"suggests that when {price_type} prices rise, {metric_name} typically {direction}. "
        f"This relationship is {significance} at the 95% confidence level."
    )

    return text
