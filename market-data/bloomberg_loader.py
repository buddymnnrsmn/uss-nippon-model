#!/usr/bin/env python3
"""
Bloomberg Data Loader for USS / Nippon Steel Merger Model
==========================================================

Loads and processes Bloomberg Terminal exports for:
- Monte Carlo distribution calibration
- Correlation matrix estimation
- Scenario validation
- Peer benchmarking

Usage:
    python bloomberg_loader.py --load-all
    python bloomberg_loader.py --steel-prices
    python bloomberg_loader.py --calibrate
    python bloomberg_loader.py --validate

Author: RAMBAS Financial Model Team
Date: 2026-02-01
"""

import os
import sys
import argparse
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
from scipy import stats

# Suppress Excel parsing warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


# =============================================================================
# CONFIGURATION
# =============================================================================

# Directory paths
BLOOMBERG_DIR = Path(__file__).parent
EXPORTS_DIR = BLOOMBERG_DIR / 'exports'
RAW_DIR = BLOOMBERG_DIR / 'raw'
CACHE_DIR = BLOOMBERG_DIR / 'cache'

# Ensure directories exist
for d in [EXPORTS_DIR, RAW_DIR, CACHE_DIR]:
    d.mkdir(exist_ok=True)

# Expected file patterns
FILE_PATTERNS = {
    'steel_prices': {
        'hrc_us': ['steel_hrc_us*.xlsx', 'MWST1MCA*.xlsx', 'hrc*.xlsx'],
        'crc_us': ['steel_crc_us*.xlsx', 'MWST1MCR*.xlsx', 'crc*.xlsx'],
        'hdg_us': ['steel_hdg*.xlsx', 'MWST1MHD*.xlsx', 'galv*.xlsx', 'coated*.xlsx'],
        'hrc_eu': ['steel_hrc_eu*.xlsx', 'SPGSTHRC*.xlsx', 'eu_hrc*.xlsx'],
        'octg': ['steel_octg*.xlsx', 'octg*.xlsx', 'tubular*.xlsx'],
        'scrap': ['scrap*.xlsx', 'STLSCRBR*.xlsx', 'busheling*.xlsx'],
        'iron_ore': ['iron_ore*.xlsx', 'IABORUSE*.xlsx', 'ore*.xlsx'],
        'nat_gas': ['natgas*.xlsx', 'NG1*.xlsx', 'gas*.xlsx'],
        'coking_coal': ['coking_coal*.xlsx', 'XAL1*.xlsx', 'met_coal*.xlsx'],
    },
    'rates': {
        'ust_10y': ['ust_10y*.xlsx', 'USGG10YR*.xlsx', 'treasury_10*.xlsx'],
        'ust_30y': ['ust_30y*.xlsx', 'USGG30YR*.xlsx', 'treasury_30*.xlsx'],
        'jgb_10y': ['jgb_10y*.xlsx', 'JGBS10*.xlsx', 'japan_10*.xlsx'],
        'jgb_30y': ['jgb_30y*.xlsx', 'JGBS30*.xlsx', 'japan_30*.xlsx'],
        'sofr': ['sofr*.xlsx', 'SOFRRATE*.xlsx'],
        'fed_funds': ['fed_funds*.xlsx', 'FDTR*.xlsx'],
    },
    'credit': {
        'bbb_spread': ['credit_spread_bbb*.xlsx', 'LUACOAS*.xlsx', 'bbb*.xlsx'],
        'hy_spread': ['credit_spread_hy*.xlsx', 'LF98OAS*.xlsx', 'high_yield*.xlsx'],
    },
    'demand': {
        'auto_production': ['auto_production*.xlsx', 'SAABORWT*.xlsx', 'auto*.xlsx'],
        'housing_starts': ['housing_starts*.xlsx', 'NHSPSTOT*.xlsx', 'housing*.xlsx'],
        'industrial_prod': ['industrial_production*.xlsx', 'IP*.xlsx'],
        'ism_pmi': ['ism_pmi*.xlsx', 'NAPMPMI*.xlsx', 'pmi*.xlsx'],
        'rig_count': ['rig_count*.xlsx', 'RIGSUA*.xlsx', 'baker*.xlsx'],
        'construction': ['construction*.xlsx', 'CNSTTMOM*.xlsx'],
    },
    'macro': {
        'gdp': ['gdp*.xlsx', 'GDP*.xlsx'],
        'cpi': ['cpi*.xlsx', 'CPI*.xlsx', 'inflation*.xlsx'],
        'unemployment': ['unemployment*.xlsx', 'USURTOT*.xlsx'],
        'consumer_conf': ['consumer_confidence*.xlsx', 'CONCCONF*.xlsx'],
    },
    'peers': {
        'financials': ['peer_*_financials*.xlsx', 'all_peers*.xlsx'],
        'multiples': ['peer_*_multiples*.xlsx'],
        'wacc': ['peer_*_wacc*.xlsx'],
    },
}

# Model's 2023 benchmark prices (for calibration validation)
BENCHMARK_PRICES_2023 = {
    'hrc_us': 680,
    'crc_us': 850,
    'hdg_us': 950,
    'hrc_eu': 620,
    'octg': 2800,
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TimeSeriesStats:
    """Statistical summary of a time series"""
    name: str
    count: int
    start_date: datetime
    end_date: datetime
    mean: float
    std: float
    min: float
    max: float
    median: float
    q1: float
    q3: float
    annualized_volatility: float
    latest_value: float

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'count': self.count,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'mean': self.mean,
            'std': self.std,
            'min': self.min,
            'max': self.max,
            'median': self.median,
            'q1': self.q1,
            'q3': self.q3,
            'annualized_volatility': self.annualized_volatility,
            'latest_value': self.latest_value,
        }


@dataclass
class DistributionParams:
    """Parameters for probability distribution fitting"""
    name: str
    dist_type: str  # 'normal', 'lognormal', 'triangular'
    params: Dict[str, float]
    goodness_of_fit: float  # KS test p-value
    recommendation: str

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'dist_type': self.dist_type,
            'params': self.params,
            'goodness_of_fit': self.goodness_of_fit,
            'recommendation': self.recommendation,
        }


# =============================================================================
# BLOOMBERG DATA LOADER CLASS
# =============================================================================

class BloombergDataLoader:
    """
    Loads and processes Bloomberg Terminal data exports.

    Handles various export formats:
    - Direct Excel exports from GP (price graph)
    - Excel Add-In BDH exports
    - CSV exports
    """

    def __init__(self, exports_dir: Optional[Path] = None):
        """
        Initialize the loader.

        Args:
            exports_dir: Directory containing Bloomberg exports
        """
        self.exports_dir = exports_dir or EXPORTS_DIR
        self.raw_dir = RAW_DIR
        self.cache_dir = CACHE_DIR

        # Data storage
        self._data: Dict[str, pd.DataFrame] = {}
        self._stats: Dict[str, TimeSeriesStats] = {}
        self._correlations: Optional[pd.DataFrame] = None

    def _find_file(self, patterns: List[str]) -> Optional[Path]:
        """Find first matching file from patterns."""
        import glob
        for pattern in patterns:
            matches = list(self.exports_dir.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _parse_bloomberg_excel(self, filepath: Path) -> pd.DataFrame:
        """
        Parse Bloomberg Excel export with various formats.

        Handles:
        - Standard GP exports (Date in column A, Value in column B)
        - BDH exports (may have headers)
        - Multi-column exports
        """
        try:
            # Try reading with different header options
            df = pd.read_excel(filepath, header=None)

            # Find the header row (look for 'Date' or datetime-like values)
            header_row = None
            for i in range(min(10, len(df))):
                row = df.iloc[i]
                # Check if this looks like a header
                if any(str(v).lower() in ['date', 'dates', 'time'] for v in row.values if pd.notna(v)):
                    header_row = i
                    break
                # Check if first column contains dates
                try:
                    pd.to_datetime(row.iloc[0])
                    header_row = i - 1 if i > 0 else None
                    break
                except:
                    continue

            # Re-read with proper header
            if header_row is not None and header_row >= 0:
                df = pd.read_excel(filepath, header=header_row)
            else:
                df = pd.read_excel(filepath)

            # Standardize column names
            df.columns = [str(c).strip() for c in df.columns]

            # Find date column
            date_col = None
            for col in df.columns:
                if 'date' in col.lower() or col.lower() in ['dates', 'time']:
                    date_col = col
                    break

            # If no date column found, assume first column
            if date_col is None:
                date_col = df.columns[0]

            # Parse dates
            df['date'] = pd.to_datetime(df[date_col], errors='coerce')

            # Find value column (usually PX_LAST or second column)
            value_col = None
            for col in df.columns:
                if col.lower() in ['px_last', 'close', 'value', 'price', 'last']:
                    value_col = col
                    break

            if value_col is None:
                # Use second column if it's numeric
                for col in df.columns[1:]:
                    if pd.api.types.is_numeric_dtype(df[col]) or df[col].dtype == object:
                        try:
                            pd.to_numeric(df[col], errors='raise')
                            value_col = col
                            break
                        except:
                            continue

            if value_col is None:
                value_col = df.columns[1]

            df['value'] = pd.to_numeric(df[value_col], errors='coerce')

            # Clean and sort
            result = df[['date', 'value']].dropna()
            result = result.sort_values('date').reset_index(drop=True)

            return result

        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return pd.DataFrame()

    def _calculate_stats(self, df: pd.DataFrame, name: str) -> TimeSeriesStats:
        """Calculate comprehensive statistics for a time series."""
        values = df['value'].dropna()

        if len(values) == 0:
            return TimeSeriesStats(
                name=name, count=0, start_date=None, end_date=None,
                mean=np.nan, std=np.nan, min=np.nan, max=np.nan,
                median=np.nan, q1=np.nan, q3=np.nan,
                annualized_volatility=np.nan, latest_value=np.nan
            )

        # Calculate returns for volatility
        returns = values.pct_change().dropna()

        # Annualized volatility (assuming daily data, 252 trading days)
        if len(returns) > 1:
            daily_vol = returns.std()
            annual_vol = daily_vol * np.sqrt(252)
        else:
            annual_vol = np.nan

        return TimeSeriesStats(
            name=name,
            count=len(values),
            start_date=df['date'].min(),
            end_date=df['date'].max(),
            mean=values.mean(),
            std=values.std(),
            min=values.min(),
            max=values.max(),
            median=values.median(),
            q1=values.quantile(0.25),
            q3=values.quantile(0.75),
            annualized_volatility=annual_vol,
            latest_value=values.iloc[-1]
        )

    # =========================================================================
    # LOADING METHODS
    # =========================================================================

    def load_steel_prices(self) -> Dict[str, pd.DataFrame]:
        """Load all steel price data."""
        print("\n" + "=" * 60)
        print("LOADING STEEL PRICES")
        print("=" * 60)

        steel_data = {}
        patterns = FILE_PATTERNS['steel_prices']

        for name, file_patterns in patterns.items():
            filepath = self._find_file(file_patterns)
            if filepath:
                print(f"Loading {name}: {filepath.name}")
                df = self._parse_bloomberg_excel(filepath)
                if not df.empty:
                    steel_data[name] = df
                    self._data[f'steel_{name}'] = df
                    self._stats[f'steel_{name}'] = self._calculate_stats(df, name)
                    print(f"  ✓ {len(df)} observations ({df['date'].min().date()} to {df['date'].max().date()})")
                else:
                    print(f"  ✗ Failed to parse")
            else:
                print(f"  - {name}: Not found")

        return steel_data

    def load_rates(self) -> Dict[str, pd.DataFrame]:
        """Load interest rate data."""
        print("\n" + "=" * 60)
        print("LOADING INTEREST RATES")
        print("=" * 60)

        rates_data = {}
        patterns = FILE_PATTERNS['rates']

        for name, file_patterns in patterns.items():
            filepath = self._find_file(file_patterns)
            if filepath:
                print(f"Loading {name}: {filepath.name}")
                df = self._parse_bloomberg_excel(filepath)
                if not df.empty:
                    rates_data[name] = df
                    self._data[f'rates_{name}'] = df
                    self._stats[f'rates_{name}'] = self._calculate_stats(df, name)
                    print(f"  ✓ {len(df)} observations")
            else:
                print(f"  - {name}: Not found")

        return rates_data

    def load_credit_spreads(self) -> Dict[str, pd.DataFrame]:
        """Load credit spread data."""
        print("\n" + "=" * 60)
        print("LOADING CREDIT SPREADS")
        print("=" * 60)

        credit_data = {}
        patterns = FILE_PATTERNS['credit']

        for name, file_patterns in patterns.items():
            filepath = self._find_file(file_patterns)
            if filepath:
                print(f"Loading {name}: {filepath.name}")
                df = self._parse_bloomberg_excel(filepath)
                if not df.empty:
                    credit_data[name] = df
                    self._data[f'credit_{name}'] = df
                    self._stats[f'credit_{name}'] = self._calculate_stats(df, name)
                    print(f"  ✓ {len(df)} observations")
            else:
                print(f"  - {name}: Not found")

        return credit_data

    def load_demand_drivers(self) -> Dict[str, pd.DataFrame]:
        """Load demand driver data."""
        print("\n" + "=" * 60)
        print("LOADING DEMAND DRIVERS")
        print("=" * 60)

        demand_data = {}
        patterns = FILE_PATTERNS['demand']

        for name, file_patterns in patterns.items():
            filepath = self._find_file(file_patterns)
            if filepath:
                print(f"Loading {name}: {filepath.name}")
                df = self._parse_bloomberg_excel(filepath)
                if not df.empty:
                    demand_data[name] = df
                    self._data[f'demand_{name}'] = df
                    self._stats[f'demand_{name}'] = self._calculate_stats(df, name)
                    print(f"  ✓ {len(df)} observations")
            else:
                print(f"  - {name}: Not found")

        return demand_data

    def load_macro(self) -> Dict[str, pd.DataFrame]:
        """Load macro economic data."""
        print("\n" + "=" * 60)
        print("LOADING MACRO DATA")
        print("=" * 60)

        macro_data = {}
        patterns = FILE_PATTERNS['macro']

        for name, file_patterns in patterns.items():
            filepath = self._find_file(file_patterns)
            if filepath:
                print(f"Loading {name}: {filepath.name}")
                df = self._parse_bloomberg_excel(filepath)
                if not df.empty:
                    macro_data[name] = df
                    self._data[f'macro_{name}'] = df
                    self._stats[f'macro_{name}'] = self._calculate_stats(df, name)
                    print(f"  ✓ {len(df)} observations")
            else:
                print(f"  - {name}: Not found")

        return macro_data

    def load_peer_data(self) -> Dict[str, pd.DataFrame]:
        """Load peer company data."""
        print("\n" + "=" * 60)
        print("LOADING PEER DATA")
        print("=" * 60)

        peer_data = {}

        # Look for peer files
        peer_files = list(self.exports_dir.glob('peer_*.xlsx'))
        peer_files.extend(list(self.exports_dir.glob('all_peers*.xlsx')))

        for filepath in peer_files:
            print(f"Loading: {filepath.name}")
            try:
                # Peer data may have multiple sheets
                xl = pd.ExcelFile(filepath)
                for sheet in xl.sheet_names:
                    df = pd.read_excel(filepath, sheet_name=sheet)
                    key = f"{filepath.stem}_{sheet}"
                    peer_data[key] = df
                    print(f"  ✓ Sheet '{sheet}': {len(df)} rows")
            except Exception as e:
                print(f"  ✗ Error: {e}")

        return peer_data

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all available data."""
        print("\n" + "=" * 60)
        print("BLOOMBERG DATA LOADER - LOADING ALL DATA")
        print("=" * 60)
        print(f"Exports directory: {self.exports_dir}")

        # Check what files exist
        all_files = list(self.exports_dir.glob('*.xlsx'))
        print(f"Found {len(all_files)} Excel files")

        if len(all_files) == 0:
            print("\n⚠ No Excel files found in exports directory!")
            print(f"  Please place Bloomberg exports in: {self.exports_dir}")
            return {}

        # Load each category
        self.load_steel_prices()
        self.load_rates()
        self.load_credit_spreads()
        self.load_demand_drivers()
        self.load_macro()
        self.load_peer_data()

        # Summary
        print("\n" + "=" * 60)
        print("LOADING COMPLETE")
        print("=" * 60)
        print(f"Loaded {len(self._data)} time series")

        return self._data

    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================

    def calculate_correlations(self,
                               series_list: Optional[List[str]] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Calculate correlation matrix between time series.

        Args:
            series_list: List of series names to include. Default: all steel prices.
            start_date: Start date for correlation window
            end_date: End date for correlation window

        Returns:
            Correlation matrix DataFrame
        """
        if series_list is None:
            # Default to steel prices
            series_list = [k for k in self._data.keys() if k.startswith('steel_')]

        if len(series_list) < 2:
            print("Need at least 2 series for correlation")
            return pd.DataFrame()

        # Merge all series on date
        merged = None
        for name in series_list:
            if name not in self._data:
                continue
            df = self._data[name][['date', 'value']].copy()
            df = df.rename(columns={'value': name})

            if merged is None:
                merged = df
            else:
                merged = pd.merge(merged, df, on='date', how='outer')

        if merged is None:
            return pd.DataFrame()

        # Apply date filters
        if start_date:
            merged = merged[merged['date'] >= pd.to_datetime(start_date)]
        if end_date:
            merged = merged[merged['date'] <= pd.to_datetime(end_date)]

        # Calculate correlations
        merged = merged.set_index('date')
        corr = merged.corr()

        self._correlations = corr
        return corr

    def fit_distribution(self, series_name: str) -> DistributionParams:
        """
        Fit probability distributions to a time series.

        Tests normal, lognormal, and provides parameters for Monte Carlo.

        Args:
            series_name: Name of the series to fit

        Returns:
            DistributionParams with fitted parameters
        """
        if series_name not in self._data:
            raise ValueError(f"Series '{series_name}' not loaded")

        values = self._data[series_name]['value'].dropna().values

        # Calculate log returns for price series
        returns = np.diff(np.log(values))

        # Test normal distribution on returns
        norm_params = stats.norm.fit(returns)
        norm_ks, norm_p = stats.kstest(returns, 'norm', args=norm_params)

        # Test lognormal on price levels
        # For lognormal, we need positive values
        if np.all(values > 0):
            lognorm_params = stats.lognorm.fit(values, floc=0)
            lognorm_ks, lognorm_p = stats.kstest(values, 'lognorm', args=lognorm_params)
        else:
            lognorm_p = 0

        # Determine best fit
        if lognorm_p > norm_p and lognorm_p > 0.05:
            return DistributionParams(
                name=series_name,
                dist_type='lognormal',
                params={
                    'shape': lognorm_params[0],
                    'loc': lognorm_params[1],
                    'scale': lognorm_params[2],
                    'log_mean': np.log(values).mean(),
                    'log_std': np.log(values).std(),
                },
                goodness_of_fit=lognorm_p,
                recommendation=f"Use lognormal with log_mean={np.log(values).mean():.4f}, log_std={np.log(values).std():.4f}"
            )
        else:
            # Normal on log returns (standard for Monte Carlo)
            return DistributionParams(
                name=series_name,
                dist_type='normal',
                params={
                    'mean': returns.mean(),
                    'std': returns.std(),
                    'annualized_mean': returns.mean() * 252,
                    'annualized_std': returns.std() * np.sqrt(252),
                },
                goodness_of_fit=norm_p,
                recommendation=f"Use normal on log returns: mean={returns.mean():.6f}, std={returns.std():.4f}"
            )

    def calibrate_monte_carlo_params(self) -> Dict[str, Dict]:
        """
        Calibrate Monte Carlo parameters from loaded data.

        Returns parameters compatible with the model's MonteCarloEngine.
        """
        print("\n" + "=" * 60)
        print("CALIBRATING MONTE CARLO PARAMETERS")
        print("=" * 60)

        calibration = {}

        # Steel price parameters
        steel_series = [k for k in self._data.keys() if k.startswith('steel_')]

        for series in steel_series:
            name = series.replace('steel_', '')
            stats_obj = self._stats.get(series)

            if stats_obj is None:
                continue

            # Calculate price factor distribution
            # Price factor = current_price / benchmark_price
            benchmark = BENCHMARK_PRICES_2023.get(name)

            if benchmark and stats_obj.latest_value:
                current_factor = stats_obj.latest_value / benchmark
            else:
                current_factor = 1.0

            # Use historical volatility for distribution
            calibration[f'{name}_price_factor'] = {
                'dist_type': 'lognormal',
                'log_mean': np.log(current_factor),
                'log_std': stats_obj.annualized_volatility if not np.isnan(stats_obj.annualized_volatility) else 0.18,
                'historical_mean': stats_obj.mean,
                'historical_std': stats_obj.std,
                'historical_vol': stats_obj.annualized_volatility,
                'latest_value': stats_obj.latest_value,
                'benchmark_2023': benchmark,
            }

            print(f"\n{name}:")
            print(f"  Latest: ${stats_obj.latest_value:,.0f}")
            print(f"  Historical Mean: ${stats_obj.mean:,.0f}")
            print(f"  Annualized Vol: {stats_obj.annualized_volatility:.1%}")
            if benchmark:
                print(f"  Current Factor: {current_factor:.2f}x benchmark")

        # Interest rate parameters
        rate_series = [k for k in self._data.keys() if k.startswith('rates_')]

        for series in rate_series:
            name = series.replace('rates_', '')
            stats_obj = self._stats.get(series)

            if stats_obj is None:
                continue

            # Rates are in percentage or decimal - normalize
            mean_val = stats_obj.mean
            if mean_val > 1:  # Likely in percentage points
                mean_val = mean_val / 100
                std_val = stats_obj.std / 100
            else:
                std_val = stats_obj.std

            calibration[f'{name}_rate'] = {
                'dist_type': 'normal',
                'mean': mean_val,
                'std': std_val,
                'historical_min': stats_obj.min,
                'historical_max': stats_obj.max,
                'latest_value': stats_obj.latest_value,
            }

            print(f"\n{name}:")
            print(f"  Latest: {stats_obj.latest_value:.2f}%")
            print(f"  Historical Range: {stats_obj.min:.2f}% - {stats_obj.max:.2f}%")

        return calibration

    # =========================================================================
    # EXPORT METHODS
    # =========================================================================

    def save_processed_data(self, format: str = 'parquet'):
        """
        Save processed data to raw directory.

        Args:
            format: 'parquet' or 'csv'
        """
        print("\n" + "=" * 60)
        print(f"SAVING PROCESSED DATA ({format})")
        print("=" * 60)

        for name, df in self._data.items():
            if format == 'parquet':
                filepath = self.raw_dir / f"{name}.parquet"
                df.to_parquet(filepath, index=False)
            else:
                filepath = self.raw_dir / f"{name}.csv"
                df.to_csv(filepath, index=False)
            print(f"Saved: {filepath.name}")

        # Save statistics
        stats_df = pd.DataFrame([s.to_dict() for s in self._stats.values()])
        stats_path = self.raw_dir / f"statistics.{format if format == 'csv' else 'csv'}"
        stats_df.to_csv(stats_path, index=False)
        print(f"Saved: {stats_path.name}")

        # Save correlations if calculated
        if self._correlations is not None:
            corr_path = self.raw_dir / "correlations.csv"
            self._correlations.to_csv(corr_path)
            print(f"Saved: {corr_path.name}")

    def generate_calibration_report(self) -> str:
        """Generate a markdown report of calibration results."""
        report = []
        report.append("# Bloomberg Data Calibration Report")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append(f"\n**Data Directory:** `{self.exports_dir}`")

        # Summary
        report.append("\n## Data Summary")
        report.append(f"\n- Total series loaded: {len(self._data)}")
        report.append(f"- Steel prices: {len([k for k in self._data if k.startswith('steel_')])}")
        report.append(f"- Interest rates: {len([k for k in self._data if k.startswith('rates_')])}")
        report.append(f"- Demand drivers: {len([k for k in self._data if k.startswith('demand_')])}")

        # Steel prices
        report.append("\n## Steel Price Calibration")
        report.append("\n| Series | Observations | Date Range | Mean | Std | Ann. Vol |")
        report.append("|--------|-------------|------------|------|-----|----------|")

        for name, stats_obj in self._stats.items():
            if name.startswith('steel_'):
                report.append(
                    f"| {name} | {stats_obj.count:,} | "
                    f"{stats_obj.start_date.strftime('%Y-%m') if stats_obj.start_date else 'N/A'} - "
                    f"{stats_obj.end_date.strftime('%Y-%m') if stats_obj.end_date else 'N/A'} | "
                    f"${stats_obj.mean:,.0f} | ${stats_obj.std:,.0f} | "
                    f"{stats_obj.annualized_volatility:.1%} |"
                )

        # Monte Carlo parameters
        report.append("\n## Recommended Monte Carlo Parameters")
        report.append("\n```python")
        report.append("# Paste into monte_carlo_engine.py")
        report.append("CALIBRATED_PARAMS = {")

        for name, stats_obj in self._stats.items():
            if name.startswith('steel_'):
                short_name = name.replace('steel_', '')
                vol = stats_obj.annualized_volatility if not np.isnan(stats_obj.annualized_volatility) else 0.18
                report.append(f"    '{short_name}_price_factor': {{")
                report.append(f"        'dist_type': 'lognormal',")
                report.append(f"        'log_mean': np.log(0.95),  # Adjust based on scenario")
                report.append(f"        'log_std': {vol:.4f},  # Calibrated from historical data")
                report.append(f"    }},")

        report.append("}")
        report.append("```")

        # Correlations
        if self._correlations is not None:
            report.append("\n## Correlation Matrix")
            report.append("\n```")
            report.append(self._correlations.to_string())
            report.append("```")

        return "\n".join(report)

    def print_summary(self):
        """Print summary of loaded data."""
        print("\n" + "=" * 60)
        print("DATA SUMMARY")
        print("=" * 60)

        if not self._stats:
            print("No data loaded. Run load_all() first.")
            return

        # Group by category
        categories = {
            'Steel Prices': 'steel_',
            'Interest Rates': 'rates_',
            'Credit Spreads': 'credit_',
            'Demand Drivers': 'demand_',
            'Macro Data': 'macro_',
        }

        for cat_name, prefix in categories.items():
            series = [(k, v) for k, v in self._stats.items() if k.startswith(prefix)]
            if series:
                print(f"\n{cat_name}:")
                print("-" * 50)
                for name, stats_obj in series:
                    print(f"  {name}: {stats_obj.count:,} obs, "
                          f"mean={stats_obj.mean:.2f}, "
                          f"vol={stats_obj.annualized_volatility:.1%}")


# =============================================================================
# VALIDATION
# =============================================================================

def validate_data(loader: BloombergDataLoader) -> Dict[str, bool]:
    """
    Validate that required data is present and complete.

    Returns dict of validation results.
    """
    print("\n" + "=" * 60)
    print("DATA VALIDATION")
    print("=" * 60)

    validations = {}

    # Required series
    required = {
        'steel_hrc_us': 5000,  # Min observations
        'steel_crc_us': 3000,
        'rates_ust_10y': 5000,
        'rates_jgb_10y': 5000,
    }

    for series, min_obs in required.items():
        stats = loader._stats.get(series)
        if stats is None:
            print(f"✗ {series}: NOT FOUND (required)")
            validations[series] = False
        elif stats.count < min_obs:
            print(f"⚠ {series}: {stats.count} obs (expected ≥{min_obs})")
            validations[series] = True  # Warning, not failure
        else:
            print(f"✓ {series}: {stats.count} obs")
            validations[series] = True

    # Check for reasonable values
    if 'steel_hrc_us' in loader._stats:
        hrc_stats = loader._stats['steel_hrc_us']
        if hrc_stats.mean < 200 or hrc_stats.mean > 2000:
            print(f"⚠ HRC mean (${hrc_stats.mean:.0f}) outside expected range ($200-$2000)")

    return validations


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Load and process Bloomberg data exports'
    )
    parser.add_argument('--load-all', action='store_true',
                        help='Load all available data')
    parser.add_argument('--steel-prices', action='store_true',
                        help='Load steel price data only')
    parser.add_argument('--rates', action='store_true',
                        help='Load interest rate data only')
    parser.add_argument('--calibrate', action='store_true',
                        help='Calibrate Monte Carlo parameters')
    parser.add_argument('--correlations', action='store_true',
                        help='Calculate correlation matrix')
    parser.add_argument('--validate', action='store_true',
                        help='Validate loaded data')
    parser.add_argument('--save', action='store_true',
                        help='Save processed data')
    parser.add_argument('--report', action='store_true',
                        help='Generate calibration report')
    parser.add_argument('--exports-dir', type=str, default=None,
                        help='Directory containing Bloomberg exports')

    args = parser.parse_args()

    # Initialize loader
    exports_dir = Path(args.exports_dir) if args.exports_dir else None
    loader = BloombergDataLoader(exports_dir)

    # Execute requested operations
    if args.load_all or not any([args.steel_prices, args.rates]):
        loader.load_all()
    else:
        if args.steel_prices:
            loader.load_steel_prices()
        if args.rates:
            loader.load_rates()

    if args.correlations:
        corr = loader.calculate_correlations()
        print("\nCorrelation Matrix:")
        print(corr)

    if args.calibrate:
        params = loader.calibrate_monte_carlo_params()

    if args.validate:
        validate_data(loader)

    if args.save:
        loader.save_processed_data()

    if args.report:
        report = loader.generate_calibration_report()
        report_path = BLOOMBERG_DIR / 'CALIBRATION_REPORT.md'
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")

    # Always print summary
    loader.print_summary()

    return 0


if __name__ == '__main__':
    sys.exit(main())
