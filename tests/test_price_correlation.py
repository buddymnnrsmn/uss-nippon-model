"""
Unit tests for price correlation analysis module.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.price_correlation_analysis import (
    HistoricalPriceData,
    load_historical_prices,
    aggregate_prices_by_year,
    calculate_price_correlation,
    create_correlation_matrix,
    get_price_trend_summary,
    align_price_with_projections,
    format_correlation_strength,
    get_correlation_insight_text
)


@pytest.fixture
def sample_price_df():
    """Create sample price DataFrame for testing"""
    dates = pd.date_range('2020-01-01', periods=200, freq='W')
    values = 700 + 50 * np.sin(np.linspace(0, 4*np.pi, 200)) + np.random.normal(0, 20, 200)
    return pd.DataFrame({'date': dates, 'value': values})


@pytest.fixture
def sample_historical_data(sample_price_df):
    """Create sample HistoricalPriceData object"""
    return HistoricalPriceData(
        hrc_us=sample_price_df.copy(),
        crc_us=sample_price_df.copy(),
        hrc_eu=sample_price_df.copy(),
        octg_us=sample_price_df.copy()
    )


def test_aggregate_prices_by_year(sample_price_df):
    """Test annual price aggregation"""
    annual = aggregate_prices_by_year(sample_price_df, 2020, 2023)

    # Should return a Series
    assert isinstance(annual, pd.Series)

    # Should have years as index
    assert all(isinstance(idx, (int, np.integer)) for idx in annual.index)

    # Should have filtered to requested range
    assert annual.index.min() >= 2020
    assert annual.index.max() <= 2023

    # Values should be reasonable (around 700 based on fixture)
    assert all((annual > 600) & (annual < 800))


def test_calculate_price_correlation():
    """Test correlation calculation"""
    # Create perfectly correlated series
    years = pd.Series(range(2024, 2034))
    price_series = pd.Series(range(700, 800, 10), index=range(2024, 2034))
    metric_series = pd.Series(range(1000, 2000, 100), index=range(2024, 2034))

    result = calculate_price_correlation(price_series, metric_series, "Revenue")

    # Should return dictionary with expected keys
    assert 'correlation' in result
    assert 'p_value' in result
    assert 'strength' in result
    assert 'n_observations' in result
    assert 'metric_name' in result

    # Correlation should be strong positive (perfectly linear)
    assert result['correlation'] > 0.99
    assert result['strength'] == 'strong'
    assert result['metric_name'] == "Revenue"
    assert result['n_observations'] == 10


def test_calculate_price_correlation_insufficient_data():
    """Test correlation with insufficient data"""
    price_series = pd.Series([700, 750], index=[2024, 2025])
    metric_series = pd.Series([1000], index=[2024])

    result = calculate_price_correlation(price_series, metric_series, "Revenue")

    # Should indicate insufficient data
    assert result['strength'] == 'insufficient_data'
    assert np.isnan(result['correlation'])


def test_get_price_trend_summary(sample_price_df):
    """Test price trend summary calculation"""
    summary = get_price_trend_summary(sample_price_df)

    # Should have all expected keys
    required_keys = ['mean', 'median', 'min', 'max', 'std', 'volatility',
                     'cagr', 'start_date', 'end_date', 'n_observations']
    for key in required_keys:
        assert key in summary

    # Validate types
    assert isinstance(summary['mean'], float)
    assert isinstance(summary['n_observations'], int)
    assert isinstance(summary['start_date'], str)

    # Validate ranges
    assert summary['min'] < summary['mean'] < summary['max']
    assert summary['volatility'] >= 0
    assert summary['n_observations'] == len(sample_price_df)


def test_align_price_with_projections(sample_price_df):
    """Test alignment of prices with projection years"""
    projection_years = pd.Series(range(2020, 2024))
    aligned = align_price_with_projections(sample_price_df, projection_years)

    # Should return Series indexed by projection years
    assert isinstance(aligned, pd.Series)
    assert len(aligned) == len(projection_years)
    assert all(aligned.index == projection_years)


def test_format_correlation_strength():
    """Test correlation strength formatting"""
    # Strong positive
    text, color = format_correlation_strength(0.85)
    assert "Strong Positive" in text
    assert color == "#4ecdc4"

    # Strong negative
    text, color = format_correlation_strength(-0.85)
    assert "Strong Negative" in text
    assert color == "#ff6b6b"

    # Moderate positive
    text, color = format_correlation_strength(0.55)
    assert "Moderate Positive" in text

    # Weak
    text, color = format_correlation_strength(0.25)
    assert "Weak" in text

    # NaN
    text, color = format_correlation_strength(np.nan)
    assert text == "N/A"


def test_get_correlation_insight_text():
    """Test insight text generation"""
    # Strong positive correlation
    text = get_correlation_insight_text(0.85, "HRC US", "Revenue", 0.001)
    assert "strong positive" in text.lower()
    assert "HRC US" in text
    assert "Revenue" in text
    assert "statistically significant" in text

    # Weak negative correlation
    text = get_correlation_insight_text(-0.3, "OCTG US", "Volume", 0.15)
    assert "weak" in text.lower()
    assert "not statistically significant" in text

    # NaN correlation
    text = get_correlation_insight_text(np.nan, "HRC US", "FCF", 1.0)
    assert "Insufficient data" in text


def test_historical_price_data_get_price_series(sample_historical_data):
    """Test HistoricalPriceData.get_price_series method"""
    # Valid price type
    hrc = sample_historical_data.get_price_series("HRC US")
    assert hrc is not None
    assert isinstance(hrc, pd.DataFrame)

    # Invalid price type
    invalid = sample_historical_data.get_price_series("Invalid")
    assert invalid is None


def test_create_correlation_matrix(sample_historical_data):
    """Test correlation matrix creation"""
    # Create sample consolidated data with correct column names
    years = range(2024, 2034)
    consolidated = pd.DataFrame({
        'Year': years,
        'Revenue': np.linspace(10000, 15000, 10),
        'Total_EBITDA': np.linspace(2000, 3000, 10),
        'FCF': np.linspace(1000, 2000, 10),
        'Total_Volume_000tons': np.linspace(15000, 18000, 10)
    })

    # Create empty segment dict (not used in this test)
    segment_dfs = {}

    # Create correlation matrix
    matrix = create_correlation_matrix(
        segment_dfs,
        consolidated,
        sample_historical_data,
        2024,
        2033
    )

    # Should return DataFrame
    assert isinstance(matrix, pd.DataFrame)

    # Should have correct dimensions (4 price types × 5 metrics)
    assert matrix.shape[0] == 4  # HRC US, CRC US, HRC EU, OCTG US
    assert matrix.shape[1] == 5  # USS Value, Revenue, EBITDA, FCF, Volume

    # Should contain correlation values (or NaN), all columns should be float64
    assert all(dtype == np.dtype('float64') for dtype in matrix.dtypes)


# Integration test (only runs if data files exist)
@pytest.mark.skipif(
    not Path("market-data/exports/processed/hrc_us_spot.csv").exists(),
    reason="Historical price data files not available"
)
def test_load_historical_prices_integration():
    """Integration test for loading real price data"""
    data = load_historical_prices()

    # Should return HistoricalPriceData
    assert isinstance(data, HistoricalPriceData)

    # All price series should be DataFrames
    assert isinstance(data.hrc_us, pd.DataFrame)
    assert isinstance(data.crc_us, pd.DataFrame)
    assert isinstance(data.hrc_eu, pd.DataFrame)
    assert isinstance(data.octg_us, pd.DataFrame)

    # Should have required columns
    for df in [data.hrc_us, data.crc_us, data.hrc_eu, data.octg_us]:
        assert 'date' in df.columns
        assert 'value' in df.columns

    # Dates should be parsed
    assert pd.api.types.is_datetime64_any_dtype(data.hrc_us['date'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
