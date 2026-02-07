#!/usr/bin/env python3
"""
Bloomberg Data Service
======================

Central singleton service for loading and managing Bloomberg market data.
Provides statistics, freshness tracking, and typed accessors for model integration.

Usage:
    from market_data.bloomberg import get_bloomberg_service

    service = get_bloomberg_service()
    prices = service.get_current_prices()
    rates = service.get_current_rates()
    status = service.get_status()
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import threading


class DataFreshness(Enum):
    """Data staleness status"""
    FRESH = "fresh"           # Within threshold
    STALE = "stale"           # Beyond threshold but usable
    UNAVAILABLE = "unavailable"  # Data not loaded


@dataclass
class TimeSeriesStats:
    """Statistics for a time series"""
    latest_value: float
    latest_date: datetime
    avg_1m: Optional[float] = None
    avg_3m: Optional[float] = None
    avg_1y: Optional[float] = None
    avg_5y: Optional[float] = None
    percentile_10: Optional[float] = None
    percentile_25: Optional[float] = None
    percentile_50: Optional[float] = None
    percentile_75: Optional[float] = None
    percentile_90: Optional[float] = None
    volatility_1y: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    data_points: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'latest_value': self.latest_value,
            'latest_date': self.latest_date.isoformat() if self.latest_date else None,
            'avg_1m': self.avg_1m,
            'avg_3m': self.avg_3m,
            'avg_1y': self.avg_1y,
            'avg_5y': self.avg_5y,
            'percentile_10': self.percentile_10,
            'percentile_25': self.percentile_25,
            'percentile_50': self.percentile_50,
            'percentile_75': self.percentile_75,
            'percentile_90': self.percentile_90,
            'volatility_1y': self.volatility_1y,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'data_points': self.data_points,
        }


@dataclass
class DatasetInfo:
    """Information about a loaded dataset"""
    name: str
    file_path: str
    loaded: bool = False
    load_error: Optional[str] = None
    stats: Optional[TimeSeriesStats] = None
    freshness: DataFreshness = DataFreshness.UNAVAILABLE
    staleness_days: int = 0
    data: Optional[pd.DataFrame] = None


class BloombergDataService:
    """
    Singleton service for Bloomberg market data.

    Features:
    - Loads 24 CSV files from exports/processed/
    - Calculates comprehensive statistics
    - Tracks data freshness
    - Provides typed accessors for different data types
    - Thread-safe singleton pattern
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config: Dict = {}
        self._datasets: Dict[str, DatasetInfo] = {}
        self._load_timestamp: Optional[datetime] = None
        self._enabled: bool = True

        # Load configuration and data
        self._load_config()
        self._load_all_data()

    def _get_config_path(self) -> Path:
        """Get path to config.json"""
        return Path(__file__).parent / "config.json"

    def _get_data_directory(self) -> Path:
        """Get path to data directory"""
        config_dir = Path(__file__).parent
        data_dir = config_dir / ".." / "exports" / "processed"
        return data_dir.resolve()

    def _load_config(self) -> None:
        """Load configuration from config.json"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            self._enabled = self._config.get('bloomberg_enabled', True)
        except FileNotFoundError:
            print(f"Warning: Bloomberg config not found at {config_path}")
            self._config = {}
            self._enabled = False
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid Bloomberg config: {e}")
            self._config = {}
            self._enabled = False

    def _load_all_data(self) -> None:
        """Load all configured datasets"""
        if not self._enabled:
            return

        data_dir = self._get_data_directory()

        # Load price data
        for key, cfg in self._config.get('price_data', {}).items():
            self._load_dataset(key, cfg, data_dir, 'price')

        # Load rate data
        for key, cfg in self._config.get('rate_data', {}).items():
            self._load_dataset(key, cfg, data_dir, 'rate')

        # Load macro data
        for key, cfg in self._config.get('macro_data', {}).items():
            self._load_dataset(key, cfg, data_dir, 'macro')

        # Load stock data
        for key, cfg in self._config.get('stock_data', {}).items():
            self._load_dataset(key, cfg, data_dir, 'stock')

        # Load derived data
        for key, cfg in self._config.get('derived_data', {}).items():
            self._load_dataset(key, cfg, data_dir, 'derived')

        self._load_timestamp = datetime.now()

    def _load_dataset(self, key: str, cfg: Dict, data_dir: Path, data_type: str) -> None:
        """Load a single dataset and calculate statistics"""
        file_name = cfg.get('file')
        if not file_name:
            return

        file_path = data_dir / file_name
        info = DatasetInfo(name=key, file_path=str(file_path))

        try:
            df = pd.read_csv(file_path)

            # Handle date column
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

            info.loaded = True
            info.data = df

            # Calculate statistics for numeric time series
            if 'value' in df.columns and 'date' in df.columns:
                info.stats = self._calculate_stats(df, data_type)
                info.freshness, info.staleness_days = self._check_freshness(
                    info.stats.latest_date, data_type
                )
            elif key == 'correlation_matrix':
                # Special handling for correlation matrix
                info.stats = TimeSeriesStats(
                    latest_value=0,
                    latest_date=datetime.now(),
                    data_points=len(df)
                )
                info.freshness = DataFreshness.FRESH

        except FileNotFoundError:
            info.load_error = f"File not found: {file_path}"
        except Exception as e:
            info.load_error = str(e)

        self._datasets[key] = info

    def _calculate_stats(self, df: pd.DataFrame, data_type: str) -> TimeSeriesStats:
        """Calculate comprehensive statistics for a time series"""
        values = df['value'].dropna()
        dates = df['date']

        latest_idx = values.index[-1]
        latest_value = values.iloc[-1]
        latest_date = dates.iloc[-1]

        now = datetime.now()

        # Time-based averages
        def avg_since(days: int) -> Optional[float]:
            cutoff = now - timedelta(days=days)
            mask = dates >= cutoff
            if mask.sum() > 0:
                return values[mask].mean()
            return None

        # Calculate volatility (annualized standard deviation of returns)
        def calc_volatility(days: int) -> Optional[float]:
            cutoff = now - timedelta(days=days)
            mask = dates >= cutoff
            recent_values = values[mask]
            if len(recent_values) > 10:
                returns = recent_values.pct_change().dropna()
                if len(returns) > 0:
                    # Annualize based on data frequency
                    # Assume weekly data for prices, daily for rates
                    periods_per_year = 52 if data_type == 'price' else 252
                    return returns.std() * np.sqrt(periods_per_year)
            return None

        return TimeSeriesStats(
            latest_value=float(latest_value),
            latest_date=pd.Timestamp(latest_date).to_pydatetime(),
            avg_1m=avg_since(30),
            avg_3m=avg_since(90),
            avg_1y=avg_since(365),
            avg_5y=avg_since(365 * 5),
            percentile_10=float(np.percentile(values, 10)),
            percentile_25=float(np.percentile(values, 25)),
            percentile_50=float(np.percentile(values, 50)),
            percentile_75=float(np.percentile(values, 75)),
            percentile_90=float(np.percentile(values, 90)),
            volatility_1y=calc_volatility(365),
            min_value=float(values.min()),
            max_value=float(values.max()),
            data_points=len(values),
        )

    def _check_freshness(self, latest_date: datetime, data_type: str) -> Tuple[DataFreshness, int]:
        """Check data freshness based on configured thresholds"""
        if latest_date is None:
            return DataFreshness.UNAVAILABLE, 0

        thresholds = self._config.get('staleness_thresholds_days', {})

        # Map data type to threshold category
        category_map = {
            'price': 'prices',
            'rate': 'rates',
            'macro': 'macro',
            'stock': 'prices',
            'derived': 'forecasts',
        }
        category = category_map.get(data_type, 'prices')
        threshold = thresholds.get(category, 7)

        days_old = (datetime.now() - latest_date).days

        if days_old <= threshold:
            return DataFreshness.FRESH, days_old
        else:
            return DataFreshness.STALE, days_old

    # =========================================================================
    # PUBLIC API - Status and Metadata
    # =========================================================================

    def is_available(self) -> bool:
        """Check if Bloomberg data is available and enabled"""
        return self._enabled and len(self._datasets) > 0

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all datasets"""
        if not self._enabled:
            return {
                'enabled': False,
                'message': 'Bloomberg integration disabled',
                'datasets': {},
            }

        datasets_status = {}
        fresh_count = 0
        stale_count = 0
        unavailable_count = 0

        for key, info in self._datasets.items():
            status = {
                'loaded': info.loaded,
                'freshness': info.freshness.value,
                'staleness_days': info.staleness_days,
            }
            if info.load_error:
                status['error'] = info.load_error
            if info.stats:
                status['latest_date'] = info.stats.latest_date.isoformat() if info.stats.latest_date else None
                status['latest_value'] = info.stats.latest_value
                status['data_points'] = info.stats.data_points

            datasets_status[key] = status

            if info.freshness == DataFreshness.FRESH:
                fresh_count += 1
            elif info.freshness == DataFreshness.STALE:
                stale_count += 1
            else:
                unavailable_count += 1

        # Overall status
        if unavailable_count > len(self._datasets) // 2:
            overall = 'unavailable'
        elif stale_count > 0:
            overall = 'stale'
        else:
            overall = 'fresh'

        return {
            'enabled': True,
            'overall_status': overall,
            'load_timestamp': self._load_timestamp.isoformat() if self._load_timestamp else None,
            'summary': {
                'fresh': fresh_count,
                'stale': stale_count,
                'unavailable': unavailable_count,
                'total': len(self._datasets),
            },
            'datasets': datasets_status,
        }

    def refresh(self) -> None:
        """Reload all data from disk"""
        self._datasets = {}
        self._load_all_data()

    def get_data_as_of_date(self) -> Optional[datetime]:
        """Get the most recent data date across price datasets"""
        dates = []
        for key in ['hrc_us', 'crc_us', 'hrc_eu', 'octg_us']:
            info = self._datasets.get(key)
            if info and info.stats and info.stats.latest_date:
                dates.append(info.stats.latest_date)

        return max(dates) if dates else None

    # =========================================================================
    # PUBLIC API - Price Data
    # =========================================================================

    def get_price_stats(self, price_key: str) -> Optional[TimeSeriesStats]:
        """Get statistics for a price series"""
        info = self._datasets.get(price_key)
        if info and info.loaded:
            return info.stats
        return None

    def get_analysis_effective_date(self) -> Optional[datetime]:
        """Get the configured analysis effective date (default: year-end 2023)"""
        date_str = self._config.get('analysis_effective_date')
        if date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                pass
        return None

    def get_prices_as_of(self, as_of_date: datetime) -> Dict[str, float]:
        """
        Get benchmark prices as of a specific date.

        Args:
            as_of_date: The date to get prices for

        Returns dict with keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        """
        prices = {}
        price_configs = self._config.get('price_data', {})

        # Map internal keys to model fields
        key_to_field = {
            'hrc_us': 'hrc_us',
            'crc_us': 'crc_us',
            'hrc_eu': 'hrc_eu',
            'octg_us': 'octg',
        }

        for key, model_field in key_to_field.items():
            info = self._datasets.get(key)
            if info and info.data is not None:
                df = info.data
                # Find the closest date on or before as_of_date
                df_before = df[df['date'] <= as_of_date]
                if len(df_before) > 0:
                    prices[model_field] = float(df_before.iloc[-1]['value'])
                else:
                    # Use fallback if no data before date
                    cfg = price_configs.get(key, {})
                    fallback = cfg.get('fallback_value')
                    if fallback is not None:
                        prices[model_field] = fallback

        # Handle coated_us (derive from CRC with premium)
        if 'crc_us' in prices:
            prices['coated_us'] = prices['crc_us'] * 1.12

        return prices

    def get_current_prices(self, use_analysis_date: bool = False) -> Dict[str, float]:
        """
        Get current (latest) prices for all steel benchmarks.

        Args:
            use_analysis_date: If True, return prices as of the analysis effective
                              date (year-end 2023) instead of latest prices.

        Returns dict with keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        Falls back to configured defaults if data unavailable.
        """
        # If using analysis date, get prices as of that date
        if use_analysis_date:
            analysis_date = self.get_analysis_effective_date()
            if analysis_date:
                return self.get_prices_as_of(analysis_date)

        prices = {}
        price_configs = self._config.get('price_data', {})

        for key, cfg in price_configs.items():
            model_field = cfg.get('model_field')
            if not model_field:
                continue

            info = self._datasets.get(key)
            if info and info.stats:
                prices[model_field] = info.stats.latest_value
            else:
                # Use fallback
                fallback = cfg.get('fallback_value')
                if fallback is not None:
                    prices[model_field] = fallback

        # Handle coated_us (not in Bloomberg, derive from CRC)
        if 'coated_us' not in prices and 'crc_us' in prices:
            # Coated typically trades at ~12% premium to CRC
            prices['coated_us'] = prices['crc_us'] * 1.12

        return prices

    def get_annual_average_prices(self, year: int = 2023) -> Dict[str, float]:
        """
        Get annual average prices for a calendar year.

        This calculates the mean price across all observations in the given
        calendar year, providing a more representative baseline than point-in-time
        year-end prices.

        Args:
            year: Calendar year (default: 2023)

        Returns:
            Dict with average prices for the full year
            Keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        prices = {}
        key_to_field = {
            'hrc_us': 'hrc_us',
            'crc_us': 'crc_us',
            'hrc_eu': 'hrc_eu',
            'octg_us': 'octg',
        }

        for key, model_field in key_to_field.items():
            info = self._datasets.get(key)
            if info and info.data is not None:
                df = info.data
                mask = (df['date'] >= start_date) & (df['date'] <= end_date)
                if mask.sum() > 0:
                    prices[model_field] = float(df.loc[mask, 'value'].mean())

        # Handle coated_us (derived from CRC with 12% premium)
        if 'crc_us' in prices:
            prices['coated_us'] = prices['crc_us'] * 1.12

        return prices

    def get_benchmark_prices_2023(self) -> Dict[str, float]:
        """
        Get 2023 annual average benchmark prices.

        This is the primary method for getting baseline prices that match
        the model's DCF analysis period. Uses annual averages rather than
        year-end point-in-time prices for a more representative baseline.

        Returns dict with keys: hrc_us, crc_us, coated_us, hrc_eu, octg
        """
        return self.get_annual_average_prices(2023)

    def get_historical_prices(self, price_key: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """Get historical price data for a series"""
        info = self._datasets.get(price_key)
        if not info or info.data is None:
            return None

        df = info.data.copy()

        if start_date:
            df = df[df['date'] >= start_date]
        if end_date:
            df = df[df['date'] <= end_date]

        return df

    def get_price_percentile(self, price_key: str, percentile: int) -> Optional[float]:
        """Get a specific percentile for a price series"""
        info = self._datasets.get(price_key)
        if info and info.stats:
            percentile_map = {
                10: info.stats.percentile_10,
                25: info.stats.percentile_25,
                50: info.stats.percentile_50,
                75: info.stats.percentile_75,
                90: info.stats.percentile_90,
            }
            return percentile_map.get(percentile)
        return None

    # =========================================================================
    # PUBLIC API - Rate Data
    # =========================================================================

    def get_rates_as_of(self, as_of_date: datetime) -> Dict[str, float]:
        """
        Get interest rates and spreads as of a specific date.

        Args:
            as_of_date: The date to get rates for

        Returns dict with keys: risk_free_rate, investment_grade_spread,
        high_yield_spread, sofr, ust_30y
        """
        rates = {}
        rate_configs = self._config.get('rate_data', {})

        for key, cfg in rate_configs.items():
            model_field = cfg.get('model_field')
            field_name = model_field if model_field else key

            info = self._datasets.get(key)
            if info and info.data is not None:
                df = info.data
                # Find the closest date on or before as_of_date
                df_before = df[df['date'] <= as_of_date]
                if len(df_before) > 0:
                    value = float(df_before.iloc[-1]['value'])
                    # Convert to decimal (all rate data is in percent or pct points)
                    rates[field_name] = value / 100
                else:
                    fallback = cfg.get('fallback_value')
                    if fallback is not None:
                        rates[field_name] = fallback / 100

        return rates

    def get_current_rates(self, use_analysis_date: bool = False) -> Dict[str, float]:
        """
        Get current interest rates and spreads.

        Args:
            use_analysis_date: If True, return rates as of the analysis effective
                              date (year-end 2023) instead of latest rates.

        Returns dict with keys: risk_free_rate, investment_grade_spread,
        high_yield_spread, sofr, ust_30y
        """
        # If using analysis date, get rates as of that date
        if use_analysis_date:
            analysis_date = self.get_analysis_effective_date()
            if analysis_date:
                return self.get_rates_as_of(analysis_date)

        rates = {}
        rate_configs = self._config.get('rate_data', {})

        for key, cfg in rate_configs.items():
            model_field = cfg.get('model_field')
            info = self._datasets.get(key)

            # Store by model_field if specified, otherwise by key
            field_name = model_field if model_field else key

            if info and info.stats:
                value = info.stats.latest_value
                # Treasury yields are in percent (e.g., 4.28 for 4.28%)
                # Spreads are in percentage points (e.g., 0.73 for 0.73% = 73 bps)
                # Both need to be converted to decimal form
                # Treasury data has values > 1 (like 4.28)
                # Spread data has values < 1 (like 0.73)
                if key in ['ust_10y', 'ust_30y', 'sofr']:
                    # Treasury/SOFR rates: divide by 100 to get decimal
                    rates[field_name] = value / 100
                else:
                    # Spreads are already in decimal percentage points
                    # 0.73 means 0.73% = 0.0073 in decimal
                    rates[field_name] = value / 100
            else:
                fallback = cfg.get('fallback_value')
                if fallback is not None:
                    rates[field_name] = fallback / 100  # Convert to decimal

        return rates

    def get_rates_2023(self) -> Dict[str, float]:
        """
        Get interest rates as of year-end 2023 (analysis effective date).

        Returns dict with keys: risk_free_rate, investment_grade_spread, etc.
        """
        return self.get_current_rates(use_analysis_date=True)

    def get_rate_stats(self, rate_key: str) -> Optional[TimeSeriesStats]:
        """Get statistics for a rate series"""
        info = self._datasets.get(rate_key)
        if info and info.loaded:
            return info.stats
        return None

    # =========================================================================
    # PUBLIC API - Stock Data
    # =========================================================================

    def get_stock_prices(self) -> Dict[str, float]:
        """Get current stock prices for USS and Nippon"""
        prices = {}
        stock_configs = self._config.get('stock_data', {})

        for key, cfg in stock_configs.items():
            model_field = cfg.get('model_field')
            info = self._datasets.get(key)

            if info and info.stats:
                prices[model_field if model_field else key] = info.stats.latest_value

        return prices

    def get_stock_returns(self, stock_key: str,
                          period_days: int = 252) -> Optional[pd.Series]:
        """Get stock returns for beta calculation"""
        info = self._datasets.get(stock_key)
        if not info or info.data is None:
            return None

        df = info.data.copy()
        cutoff = datetime.now() - timedelta(days=period_days)
        df = df[df['date'] >= cutoff]

        if len(df) < 10:
            return None

        returns = df['value'].pct_change().dropna()
        returns.index = df['date'].iloc[1:].values

        return returns

    # =========================================================================
    # PUBLIC API - Correlation Data
    # =========================================================================

    def get_correlation_matrix(self) -> Optional[pd.DataFrame]:
        """Get the pre-computed correlation matrix"""
        info = self._datasets.get('correlation_matrix')
        if info and info.data is not None:
            df = info.data.copy()
            # Set first column as index if it's unnamed
            if df.columns[0] == '' or df.columns[0] == 'Unnamed: 0':
                df = df.set_index(df.columns[0])
            return df
        return None

    # =========================================================================
    # PUBLIC API - Macro Data
    # =========================================================================

    def get_macro_indicators(self) -> Dict[str, float]:
        """Get current values of macro indicators"""
        indicators = {}
        macro_configs = self._config.get('macro_data', {})

        for key, cfg in macro_configs.items():
            info = self._datasets.get(key)
            if info and info.stats:
                indicators[key] = info.stats.latest_value

        return indicators

    def get_macro_stats(self, indicator_key: str) -> Optional[TimeSeriesStats]:
        """Get statistics for a macro indicator"""
        info = self._datasets.get(indicator_key)
        if info and info.loaded:
            return info.stats
        return None


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_service_instance: Optional[BloombergDataService] = None

def get_bloomberg_service() -> BloombergDataService:
    """
    Get the Bloomberg data service singleton.

    This is the primary entry point for accessing Bloomberg data.
    The service is lazily initialized on first access.

    Returns:
        BloombergDataService singleton instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = BloombergDataService()
    return _service_instance


def reset_bloomberg_service() -> None:
    """
    Reset the Bloomberg service singleton.

    Use this to force a reload of all data, typically after
    updating the underlying CSV files.
    """
    global _service_instance
    _service_instance = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_bloomberg_available() -> bool:
    """Check if Bloomberg data is available without fully initializing"""
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        return False

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('bloomberg_enabled', True)
    except Exception:
        return False


if __name__ == '__main__':
    # Demo usage
    service = get_bloomberg_service()

    print("Bloomberg Data Service Status")
    print("=" * 50)

    status = service.get_status()
    print(f"Overall: {status['overall_status']}")
    print(f"Datasets: {status['summary']}")

    print("\nCurrent Prices:")
    prices = service.get_current_prices()
    for k, v in prices.items():
        print(f"  {k}: ${v:,.0f}/ton")

    print("\nCurrent Rates:")
    rates = service.get_current_rates()
    for k, v in rates.items():
        print(f"  {k}: {v*100:.2f}%")

    print("\nHRC US Statistics:")
    stats = service.get_price_stats('hrc_us')
    if stats:
        print(f"  Latest: ${stats.latest_value:,.0f} ({stats.latest_date.strftime('%Y-%m-%d')})")
        print(f"  1Y Avg: ${stats.avg_1y:,.0f}" if stats.avg_1y else "  1Y Avg: N/A")
        print(f"  Volatility: {stats.volatility_1y*100:.1f}%" if stats.volatility_1y else "  Volatility: N/A")
        print(f"  Range: ${stats.min_value:,.0f} - ${stats.max_value:,.0f}")
