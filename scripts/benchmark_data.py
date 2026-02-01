"""
Benchmark Data Accessor for Steel Competitor Analysis

Provides a unified interface to access peer company benchmarks from multiple
data sources (Capital IQ, WRDS, manual operational data).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

# Handle import from different contexts (scripts dir vs parent dir)
try:
    from data_loader import USSteelDataLoader
except ModuleNotFoundError:
    from scripts.data_loader import USSteelDataLoader


@dataclass
class BenchmarkStats:
    """Statistical summary for a benchmark metric."""
    min: float
    q1: float
    median: float
    mean: float
    q3: float
    max: float
    count: int

    def to_dict(self) -> Dict:
        return {
            'min': self.min,
            'q1': self.q1,
            'median': self.median,
            'mean': self.mean,
            'q3': self.q3,
            'max': self.max,
            'count': self.count
        }


@dataclass
class GrowthStats:
    """Multi-year growth analysis statistics for CAGR comparison."""
    metric: str
    period_years: int
    start_year: int
    end_year: int
    uss_cagr: Optional[float]
    peer_min: float
    peer_q1: float
    peer_median: float
    peer_mean: float
    peer_q3: float
    peer_max: float
    peer_count: int
    uss_percentile: Optional[float]

    def to_dict(self) -> Dict:
        return {
            'metric': self.metric,
            'period_years': self.period_years,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'uss_cagr': self.uss_cagr,
            'peer_min': self.peer_min,
            'peer_q1': self.peer_q1,
            'peer_median': self.peer_median,
            'peer_mean': self.peer_mean,
            'peer_q3': self.peer_q3,
            'peer_max': self.peer_max,
            'peer_count': self.peer_count,
            'uss_percentile': self.uss_percentile
        }


class BenchmarkData:
    """
    Unified accessor for steel competitor benchmark data.

    Combines data from:
    - Capital IQ comparable company analysis
    - WRDS Compustat (if available)
    - Manual operational metrics (capacity, utilization, shipments)

    Example usage:
        benchmark = BenchmarkData()

        # Get valuation multiples
        multiples = benchmark.get_peer_multiples()
        print(f"Median TEV/EBITDA: {multiples['tev_ebitda'].median}")

        # Get margins comparison
        margins = benchmark.get_peer_margins()

        # Get specific company data
        nucor = benchmark.get_company_data('NUE')
    """

    # Peer company ticker mapping
    PEER_TICKERS = {
        'STLD': 'Steel Dynamics, Inc.',
        'NUE': 'Nucor Corporation',
        'CLF': 'Cleveland-Cliffs Inc.',
        'CMC': 'Commercial Metals Company',
        'ZEUS': 'Olympic Steel, Inc.',
        'MT': 'ArcelorMittal S.A.',
        'PKX': 'POSCO Holdings Inc.',
        'GGB': 'Gerdau S.A.',
        'NISTF': 'Nippon Steel Corporation',
        'BSL': 'BlueScope Steel Limited',
        'TX': 'Ternium S.A.',
    }

    # Primary US comps (for weighted analysis)
    PRIMARY_COMPS = ['STLD', 'NUE', 'CLF']

    def __init__(self, data_dir: str = None):
        """
        Initialize BenchmarkData with data sources.

        Args:
            data_dir: Directory containing Capital IQ Excel files (default: project_root/references)
        """
        # Resolve data_dir relative to project root if not absolute
        if data_dir is None:
            project_root = Path(__file__).parent.parent
            data_dir = project_root / "references"
        elif not Path(data_dir).is_absolute():
            project_root = Path(__file__).parent.parent
            data_dir = project_root / data_dir

        self.loader = USSteelDataLoader(str(data_dir))
        self._cache: Dict = {}

    def _get_comps_data(self) -> Dict[str, pd.DataFrame]:
        """Load Capital IQ comparable company data."""
        if 'comps' not in self._cache:
            self._cache['comps'] = self.loader.load_comparable_companies()
        return self._cache['comps']

    def _get_steel_metrics(self) -> Dict[str, pd.DataFrame]:
        """Load steel operational metrics."""
        if 'steel' not in self._cache:
            self._cache['steel'] = self.loader.load_steel_metrics()
        return self._cache['steel']

    def _calculate_stats(self, series: pd.Series) -> BenchmarkStats:
        """Calculate summary statistics for a series."""
        clean = series.dropna()
        if len(clean) == 0:
            return BenchmarkStats(
                min=np.nan, q1=np.nan, median=np.nan,
                mean=np.nan, q3=np.nan, max=np.nan, count=0
            )
        return BenchmarkStats(
            min=clean.min(),
            q1=clean.quantile(0.25),
            median=clean.median(),
            mean=clean.mean(),
            q3=clean.quantile(0.75),
            max=clean.max(),
            count=len(clean)
        )

    # =========================================================================
    # Valuation Multiples
    # =========================================================================

    def get_peer_multiples(self, primary_only: bool = False) -> Dict[str, BenchmarkStats]:
        """
        Get valuation multiple benchmarks for peer companies.

        Args:
            primary_only: If True, only use primary US comps (STLD, NUE, CLF)

        Returns:
            Dict mapping multiple name to BenchmarkStats
        """
        comps = self._get_comps_data()

        # Try to get from trading multiples or financial data
        df = None
        if 'trading_multiples' in comps:
            df = comps['trading_multiples']
        elif 'financial_data' in comps:
            df = comps['financial_data']

        if df is None or df.empty:
            return {}

        # Filter to primary comps if requested
        if primary_only:
            mask = df['Company Name'].str.contains('|'.join(self.PRIMARY_COMPS), na=False)
            df = df[mask]

        result = {}

        # Map column names to standardized names
        column_mapping = {
            'TEV/EBITDA LTM': 'tev_ebitda',
            'TEV/EBITDA LTM - Latest': 'tev_ebitda',
            'TEV/Total Revenues LTM': 'tev_revenue',
            'TEV/Total Revenues LTM - Latest': 'tev_revenue',
            'P/Diluted EPS Before Extra LTM': 'pe_ratio',
            'P/Diluted EPS Before Extra LTM - Latest': 'pe_ratio',
        }

        for col, name in column_mapping.items():
            if col in df.columns:
                result[name] = self._calculate_stats(df[col])

        return result

    def get_exit_multiple_range(self, multiple: str = 'tev_ebitda') -> Dict[str, float]:
        """
        Get recommended exit multiple range based on peer data.

        Returns:
            Dict with 'low', 'base', 'high' exit multiples
        """
        multiples = self.get_peer_multiples()

        if multiple not in multiples:
            # Default fallback values
            return {'low': 4.0, 'base': 5.0, 'high': 6.0}

        stats = multiples[multiple]
        return {
            'low': stats.q1,
            'base': stats.median,
            'high': stats.q3,
        }

    # =========================================================================
    # Margin Benchmarks
    # =========================================================================

    def get_peer_margins(self, primary_only: bool = False) -> pd.DataFrame:
        """
        Get margin benchmarks for peer companies.

        Returns:
            DataFrame with company names and margin columns
        """
        comps = self._get_comps_data()

        # Try operating statistics or financial ratios
        df = None
        if 'operating_statistics' in comps:
            df = comps['operating_statistics']
        elif 'trading_multiples' in comps:
            df = comps['trading_multiples']

        if df is None or df.empty:
            return pd.DataFrame()

        # Filter to primary comps if requested
        if primary_only:
            mask = df['Company Name'].str.contains('|'.join(self.PRIMARY_COMPS), na=False)
            df = df[mask]

        # Select margin columns
        margin_cols = [col for col in df.columns if 'Margin' in col or 'margin' in col]
        if 'Company Name' in df.columns:
            margin_cols = ['Company Name'] + margin_cols

        return df[margin_cols].copy()

    def get_margin_stats(self) -> Dict[str, BenchmarkStats]:
        """Get statistical summary of peer margins."""
        margins = self.get_peer_margins()

        if margins.empty:
            return {}

        result = {}
        for col in margins.columns:
            if col != 'Company Name' and 'Margin' in col:
                # Standardize name
                name = col.lower().replace(' ', '_').replace('%', '').strip('_')
                result[name] = self._calculate_stats(margins[col])

        return result

    # =========================================================================
    # Leverage & Credit
    # =========================================================================

    def get_peer_leverage(self) -> pd.DataFrame:
        """Get leverage metrics for peer companies."""
        comps = self._get_comps_data()

        df = None
        if 'credit_health_panel' in comps:
            df = comps['credit_health_panel']
        elif 'credit_ratios' in comps:
            df = comps['credit_ratios']

        if df is None or df.empty:
            return pd.DataFrame()

        # Select leverage columns
        leverage_cols = [col for col in df.columns
                        if any(x in col.lower() for x in ['debt', 'leverage', 'coverage'])]
        if 'Company Name' in df.columns:
            leverage_cols = ['Company Name'] + leverage_cols

        return df[leverage_cols].copy()

    def get_leverage_stats(self) -> Dict[str, BenchmarkStats]:
        """Get statistical summary of peer leverage metrics."""
        leverage = self.get_peer_leverage()

        if leverage.empty:
            return {}

        result = {}
        for col in leverage.columns:
            if col != 'Company Name':
                name = col.lower().replace(' ', '_').replace('/', '_').strip('_')
                result[name] = self._calculate_stats(leverage[col])

        return result

    # =========================================================================
    # Steel Operational Metrics
    # =========================================================================

    def get_peer_capacity(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        Get raw steel capacity for peer companies.

        Args:
            year: Filter to specific year. Default is latest available.
        """
        steel = self._get_steel_metrics()

        if 'capacity' not in steel or steel['capacity'].empty:
            return pd.DataFrame()

        df = steel['capacity'].copy()

        if year is not None:
            df = df[df['Year'] == year]
        else:
            # Get latest year for each company
            df = df.sort_values('Year', ascending=False)
            df = df.drop_duplicates(subset=['Company'], keep='first')

        return df

    def get_peer_utilization(self, year: Optional[int] = None, quarter: Optional[str] = None) -> pd.DataFrame:
        """
        Get capacity utilization for peer companies.

        Args:
            year: Filter to specific year
            quarter: Filter to specific quarter (Q1, Q2, Q3, Q4)
        """
        steel = self._get_steel_metrics()

        if 'utilization' not in steel or steel['utilization'].empty:
            return pd.DataFrame()

        df = steel['utilization'].copy()

        if year is not None:
            df = df[df['Year'] == year]
        if quarter is not None:
            df = df[df['Quarter'] == quarter]

        return df

    def get_peer_shipments(self, year: Optional[int] = None, segment: Optional[str] = None) -> pd.DataFrame:
        """
        Get shipment volumes for peer companies.

        Args:
            year: Filter to specific year
            segment: Filter to specific segment (Flat-Rolled, Long Products, etc.)
        """
        steel = self._get_steel_metrics()

        if 'shipments' not in steel or steel['shipments'].empty:
            return pd.DataFrame()

        df = steel['shipments'].copy()

        if year is not None:
            df = df[df['Year'] == year]
        if segment is not None:
            df = df[df['Segment'] == segment]

        return df

    # =========================================================================
    # Geographic Mix
    # =========================================================================

    def get_geographic_mix(self, company: Optional[str] = None) -> pd.DataFrame:
        """
        Get geographic revenue breakdown.

        Args:
            company: Filter to specific company ticker
        """
        steel = self._get_steel_metrics()

        if 'wrds_geo_mix' not in steel:
            return pd.DataFrame()

        df = steel['wrds_geo_mix'].copy()

        if company is not None:
            # Would need gvkey mapping
            pass

        return df

    # =========================================================================
    # Company-Specific Data
    # =========================================================================

    def get_company_data(self, ticker: str) -> Dict:
        """
        Get all available benchmark data for a specific company.

        Args:
            ticker: Company ticker (e.g., 'NUE', 'CLF')

        Returns:
            Dict with all available data for the company
        """
        result = {'ticker': ticker, 'name': self.PEER_TICKERS.get(ticker, ticker)}

        # Get from Capital IQ comps
        comps = self._get_comps_data()
        for sheet_name, df in comps.items():
            if 'Company Name' in df.columns:
                match = df[df['Company Name'].str.contains(ticker, na=False)]
                if not match.empty:
                    result[sheet_name] = match.iloc[0].to_dict()

        # Get from steel metrics
        steel = self._get_steel_metrics()
        for metric_name, df in steel.items():
            if isinstance(df, pd.DataFrame) and 'Company' in df.columns:
                match = df[df['Company'].str.contains(ticker, na=False)]
                if not match.empty:
                    result[metric_name] = match.to_dict('records')

        return result

    # =========================================================================
    # Summary Methods
    # =========================================================================

    def get_benchmark_summary(self) -> pd.DataFrame:
        """
        Get a summary table of key benchmarks.

        Returns:
            DataFrame with metrics as rows and statistics as columns
        """
        rows = []

        # Valuation multiples
        multiples = self.get_peer_multiples()
        for name, stats in multiples.items():
            rows.append({
                'Category': 'Valuation',
                'Metric': name,
                'Min': stats.min,
                'Q1': stats.q1,
                'Median': stats.median,
                'Mean': stats.mean,
                'Q3': stats.q3,
                'Max': stats.max,
                'Count': stats.count
            })

        # Margins
        margin_stats = self.get_margin_stats()
        for name, stats in margin_stats.items():
            rows.append({
                'Category': 'Margins',
                'Metric': name,
                'Min': stats.min,
                'Q1': stats.q1,
                'Median': stats.median,
                'Mean': stats.mean,
                'Q3': stats.q3,
                'Max': stats.max,
                'Count': stats.count
            })

        # Leverage
        leverage_stats = self.get_leverage_stats()
        for name, stats in leverage_stats.items():
            rows.append({
                'Category': 'Leverage',
                'Metric': name,
                'Min': stats.min,
                'Q1': stats.q1,
                'Median': stats.median,
                'Mean': stats.mean,
                'Q3': stats.q3,
                'Max': stats.max,
                'Count': stats.count
            })

        return pd.DataFrame(rows)

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
        self.loader.clear_cache()

    # =========================================================================
    # USS Comparison Methods
    # =========================================================================

    def get_uss_metrics(self, year: int = 2023) -> dict:
        """Get USS metrics for comparison against peers.

        Args:
            year: Fiscal year for metrics (default 2023)

        Returns:
            Dict with USS key metrics
        """
        try:
            income = self.loader.load_income_statement()

            # Helper to extract values from income statement
            def get_value(df: pd.DataFrame, row_name: str, yr: int) -> Optional[float]:
                if df.empty:
                    return None
                # Try to find the row
                mask = df.iloc[:, 0].astype(str).str.contains(row_name, case=False, na=False)
                if not mask.any():
                    return None
                # Find the year column
                for col in df.columns:
                    if str(yr) in str(col):
                        val = df.loc[mask, col].iloc[0]
                        if pd.notna(val):
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return None
                return None

            # Extract key metrics from USS income statement
            revenue = get_value(income, 'Net Sales|Total Revenue|Revenue', year)
            ebitda = get_value(income, 'EBITDA', year)

            # If EBITDA not directly available, calculate from components
            if ebitda is None and revenue is not None:
                operating_income = get_value(income, 'Operating Income|Income from Operations', year)
                da = get_value(income, 'Depreciation|D&A', year)
                if operating_income is not None and da is not None:
                    ebitda = operating_income + da

            # Calculate margin
            ebitda_margin = None
            if ebitda is not None and revenue is not None and revenue != 0:
                ebitda_margin = ebitda / revenue

            # Load balance sheet for additional metrics
            balance = self.loader.load_balance_sheet()

            def get_balance_value(df: pd.DataFrame, row_name: str, yr: int) -> Optional[float]:
                if df.empty:
                    return None
                mask = df.iloc[:, 0].astype(str).str.contains(row_name, case=False, na=False)
                if not mask.any():
                    return None
                for col in df.columns:
                    if str(yr) in str(col):
                        val = df.loc[mask, col].iloc[0]
                        if pd.notna(val):
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                return None
                return None

            # Extract balance sheet items
            total_assets = get_balance_value(balance, 'Total Assets', year)
            total_equity = get_balance_value(balance, 'Total Common Equity', year)
            total_debt = get_balance_value(balance, 'Total Debt', year)
            net_debt = get_balance_value(balance, 'Net Debt', year)
            net_income = get_value(income, 'Net Income to Company|Net Income$', year)

            # Calculate return ratios
            roa = (net_income / total_assets * 100) if net_income and total_assets else None
            roe = (net_income / total_equity * 100) if net_income and total_equity else None

            # Calculate leverage ratios
            net_debt_ebitda = (net_debt / ebitda) if net_debt and ebitda and ebitda > 0 else None

            # Get interest expense for coverage ratio
            interest_exp = get_value(income, 'Interest Expense', year)
            interest_coverage = (ebitda / abs(interest_exp)) if ebitda and interest_exp and interest_exp != 0 else None

            return {
                'ticker': 'X',
                'company': 'United States Steel Corporation',
                'revenue': revenue,
                'ebitda': ebitda,
                'ebitda_margin': ebitda_margin,
                'capacity_mtons': 22.4,  # From USS 10-K
                'shipments_mtons': 14.8,  # From USS 10-K (aggregate 2023)
                'year': year,
                # Balance sheet items
                'total_assets': total_assets,
                'total_equity': total_equity,
                'total_debt': total_debt,
                'net_debt': net_debt,
                'net_income': net_income,
                # Calculated ratios
                'roa': roa,
                'roe': roe,
                'net_debt_ebitda': net_debt_ebitda,
                'interest_coverage': interest_coverage,
            }
        except Exception as e:
            # Return defaults if data loading fails
            return {
                'ticker': 'X',
                'company': 'United States Steel Corporation',
                'revenue': 18025.0,  # 2023 actual from financials
                'ebitda': 2189.0,    # 2023 actual
                'ebitda_margin': 0.121,  # ~12.1%
                'capacity_mtons': 22.4,
                'shipments_mtons': 14.8,
                'year': year,
                'roa': 5.2,
                'roe': 9.1,
                'net_debt_ebitda': 0.6,
                'interest_coverage': 8.5,
                'note': f'Using hardcoded defaults: {str(e)}'
            }

    def get_peer_summary(self) -> pd.DataFrame:
        """Get summary DataFrame of peer company metrics.

        Returns:
            DataFrame with ticker, company name, and key metrics
        """
        comps = self._get_comps_data()

        # Try to get from financial data or trading multiples
        df = None
        for sheet in ['financial_data', 'trading_multiples', 'operating_statistics']:
            if sheet in comps and not comps[sheet].empty:
                df = comps[sheet].copy()
                break

        if df is None or df.empty:
            return pd.DataFrame()

        # Standardize column names
        df = df.rename(columns={
            'Company Name': 'company',
            'Stock Symbol': 'ticker',
        })

        # Add calculated columns if possible
        if 'Total Revenues LTM' in df.columns and 'EBITDA LTM' in df.columns:
            df['revenue'] = df['Total Revenues LTM']
            df['ebitda'] = df['EBITDA LTM']
            df['ebitda_margin'] = df['ebitda'] / df['revenue']

        return df

    def get_uss_percentile_rank(self, metric: str) -> Optional[dict]:
        """Calculate USS percentile rank vs peers for a metric.

        Args:
            metric: Metric name ('ebitda_margin', 'revenue', 'capacity_mtons', etc.)

        Returns:
            Dict with USS value, percentile, and peer distribution, or None if unavailable
        """
        uss = self.get_uss_metrics()
        peer_summary = self.get_peer_summary()

        # Handle different metric names
        metric_lower = metric.lower()

        # Get USS value
        uss_value = uss.get(metric_lower)
        if uss_value is None:
            return None

        # Try to get peer values from summary
        peer_values = None

        if not peer_summary.empty:
            # Map metric name to possible column names
            column_mappings = {
                'ebitda_margin': ['ebitda_margin', 'EBITDA Margin %', 'EBITDA Margin', 'LTM EBITDA Margin'],
                'revenue': ['revenue', 'LTM Total Revenue ', 'Total Revenues LTM', 'Revenue'],
                'ebitda': ['ebitda', 'LTM EBITDA ', 'EBITDA LTM'],
                'tev_ebitda': ['TEV/EBITDA LTM - Latest', 'TEV/EBITDA LTM'],
                'capacity_mtons': ['capacity_mtons'],
                'shipments_mtons': ['shipments_mtons'],
            }

            # If looking for EBITDA margin, calculate it from revenue and EBITDA
            if metric_lower == 'ebitda_margin' and 'LTM EBITDA ' in peer_summary.columns and 'LTM Total Revenue ' in peer_summary.columns:
                peer_values = (peer_summary['LTM EBITDA '] / peer_summary['LTM Total Revenue ']).dropna()

            for col_name in column_mappings.get(metric_lower, [metric]):
                if col_name in peer_summary.columns:
                    peer_values = peer_summary[col_name].dropna()
                    break

        # If no peer values from summary, try steel metrics for capacity/shipments
        if peer_values is None or peer_values.empty:
            if metric_lower in ['capacity_mtons', 'shipments_mtons']:
                steel = self._get_steel_metrics()
                if metric_lower == 'capacity_mtons' and 'capacity' in steel:
                    cap_df = steel['capacity']
                    if 'Raw_Capacity_Mtons' in cap_df.columns:
                        peer_values = cap_df['Raw_Capacity_Mtons'].dropna()
                elif metric_lower == 'shipments_mtons' and 'shipments' in steel:
                    ship_df = steel['shipments']
                    if 'Shipments_Ktons' in ship_df.columns:
                        peer_values = ship_df['Shipments_Ktons'].dropna() / 1000  # Convert to Mtons

        if peer_values is None or peer_values.empty:
            return None

        peer_values = peer_values.sort_values()

        # Calculate percentile
        below_count = (peer_values < uss_value).sum()
        percentile = below_count / len(peer_values) * 100

        return {
            'metric': metric,
            'uss_value': uss_value,
            'percentile': percentile,
            'peer_min': peer_values.min(),
            'peer_q1': peer_values.quantile(0.25),
            'peer_median': peer_values.median(),
            'peer_q3': peer_values.quantile(0.75),
            'peer_max': peer_values.max(),
            'peer_count': len(peer_values),
            'vs_median': 'above' if uss_value > peer_values.median() else 'below'
        }

    # =========================================================================
    # Multi-Year Growth & Profitability Analysis
    # =========================================================================

    # Metric mapping for WRDS fundamentals
    WRDS_METRIC_MAPPING = {
        'revenue': 'revenue',
        'ebitda': 'ebitda',
        'net_income': 'net_income',
        'capex': 'capex',
        'depreciation': 'depreciation',
        'total_assets': 'total_assets',
    }

    # High confidence metrics (93.5%+ coverage)
    HIGH_CONFIDENCE_METRICS = ['net_income', 'capex', 'depreciation', 'total_assets']

    # Medium confidence metrics (53.3% coverage) - BSL excluded
    MEDIUM_CONFIDENCE_METRICS = ['revenue', 'ebitda']

    def _get_wrds_fundamentals(self) -> pd.DataFrame:
        """Load peer fundamentals from WRDS cache.

        Returns:
            DataFrame with peer company fundamentals indexed by ticker and year.
        """
        if 'wrds_fundamentals' in self._cache:
            return self._cache['wrds_fundamentals']

        # Try to load from cache file
        wrds_path = Path(__file__).parent.parent / 'local' / 'wrds_cache' / 'peer_fundamentals.csv'

        if not wrds_path.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(wrds_path)

            # Parse datadate and extract year
            df['datadate'] = pd.to_datetime(df['datadate'])
            df['year'] = df['datadate'].dt.year

            # Remove duplicate rows (some tickers have two records per year)
            # Keep the one with more data (non-null revenue)
            df = df.sort_values(['ticker', 'year', 'revenue'], ascending=[True, True, False])
            df = df.drop_duplicates(subset=['ticker', 'year'], keep='first')

            self._cache['wrds_fundamentals'] = df
            return df

        except Exception as e:
            print(f"Error loading WRDS fundamentals: {e}")
            return pd.DataFrame()

    @staticmethod
    def calculate_cagr(start_value: float, end_value: float, periods: int) -> Optional[float]:
        """Calculate Compound Annual Growth Rate.

        Args:
            start_value: Value at start of period
            end_value: Value at end of period
            periods: Number of years between start and end

        Returns:
            CAGR as decimal (e.g., 0.05 for 5%), or None if calculation impossible
        """
        if start_value is None or end_value is None or periods <= 0:
            return None
        if pd.isna(start_value) or pd.isna(end_value):
            return None
        if start_value <= 0 or end_value <= 0:
            # Can't calculate CAGR for negative or zero values
            return None

        try:
            cagr = (end_value / start_value) ** (1 / periods) - 1
            return cagr
        except (ZeroDivisionError, ValueError):
            return None

    def _get_uss_financial_data(self) -> pd.DataFrame:
        """Load USS historical financial data from Excel.

        Returns:
            DataFrame with USS financials by year
        """
        if 'uss_financials' in self._cache:
            return self._cache['uss_financials']

        uss_path = Path(__file__).parent.parent / 'audit-verification' / 'evidence' / 'USS Financial Statements.xlsx'

        if not uss_path.exists():
            return pd.DataFrame()

        try:
            # Read income statement
            income_df = pd.read_excel(uss_path, sheet_name='US Steel_Income Statement', header=None)

            # Find the header row (row 12 has years)
            # Years are in columns 1-35 (1990-2024)
            header_row = 12
            years = []
            year_cols = {}

            for col in range(1, 36):
                val = income_df.iloc[header_row, col]
                if pd.notna(val) and 'FY' in str(val):
                    year = int(str(val).split()[0])
                    years.append(year)
                    year_cols[year] = col

            # Extract key metrics by row
            def get_row_values(df, row_pattern, year_cols):
                """Extract values for a row matching pattern."""
                for idx in range(len(df)):
                    cell = df.iloc[idx, 0]
                    if pd.notna(cell) and row_pattern in str(cell):
                        values = {}
                        for year, col in year_cols.items():
                            val = df.iloc[idx, col]
                            if pd.notna(val):
                                try:
                                    values[year] = float(val)
                                except (ValueError, TypeError):
                                    pass
                        return values
                return {}

            # Get income statement metrics (values in thousands)
            revenue_vals = get_row_values(income_df, 'Total Revenue', year_cols)
            net_income_vals = get_row_values(income_df, 'Net Income to Company', year_cols)
            da_vals = get_row_values(income_df, 'Depreciation & Amort.', year_cols)
            operating_income_vals = get_row_values(income_df, 'Operating Income', year_cols)

            # Read cash flow statement for capex
            cf_df = pd.read_excel(uss_path, sheet_name='US Steel_Cash Flow', header=None)
            capex_vals = get_row_values(cf_df, 'Capital Expenditure', year_cols)

            # Read balance sheet for total assets
            bs_df = pd.read_excel(uss_path, sheet_name='US Steel_Balance Sheet', header=None)
            assets_vals = get_row_values(bs_df, 'Total Assets', year_cols)

            # Build DataFrame - convert from thousands to millions
            records = []
            for year in sorted(set(revenue_vals.keys()) | set(net_income_vals.keys())):
                record = {
                    'year': year,
                    'revenue': revenue_vals.get(year, np.nan) / 1000 if year in revenue_vals else np.nan,
                    'net_income': net_income_vals.get(year, np.nan) / 1000 if year in net_income_vals else np.nan,
                    'depreciation': da_vals.get(year, np.nan) / 1000 if year in da_vals else np.nan,
                    'operating_income': operating_income_vals.get(year, np.nan) / 1000 if year in operating_income_vals else np.nan,
                    'capex': abs(capex_vals.get(year, np.nan)) / 1000 if year in capex_vals else np.nan,
                    'total_assets': assets_vals.get(year, np.nan) / 1000 if year in assets_vals else np.nan,
                }
                # Calculate EBITDA = Operating Income + D&A
                if not pd.isna(record['operating_income']) and not pd.isna(record['depreciation']):
                    record['ebitda'] = record['operating_income'] + record['depreciation']
                else:
                    record['ebitda'] = np.nan
                records.append(record)

            result = pd.DataFrame(records)
            self._cache['uss_financials'] = result
            return result

        except Exception as e:
            print(f"Error loading USS financials: {e}")
            return pd.DataFrame()

    def get_uss_timeseries(self, metrics: List[str], start_year: int = 2019,
                          end_year: int = 2024) -> pd.DataFrame:
        """Extract USS historical timeseries for specified metrics.

        Args:
            metrics: List of metric names (revenue, ebitda, net_income, capex, etc.)
            start_year: Start year for timeseries
            end_year: End year for timeseries

        Returns:
            DataFrame with year and metric columns
        """
        uss_df = self._get_uss_financial_data()

        if uss_df.empty:
            return pd.DataFrame()

        # Filter to requested year range
        mask = (uss_df['year'] >= start_year) & (uss_df['year'] <= end_year)
        result = uss_df.loc[mask, ['year'] + [m for m in metrics if m in uss_df.columns]].copy()

        return result.reset_index(drop=True)

    def get_multiyear_growth_analysis(self, metrics: List[str] = None,
                                      periods: List[int] = None) -> List[GrowthStats]:
        """Main engine: Calculate USS vs peer CAGRs for multiple metrics and periods.

        Args:
            metrics: List of metrics to analyze (default: all available)
            periods: List of period lengths in years (default: [3, 5])

        Returns:
            List of GrowthStats objects with CAGR comparisons
        """
        if metrics is None:
            metrics = ['revenue', 'ebitda', 'net_income', 'capex', 'depreciation', 'total_assets']
        if periods is None:
            periods = [3, 5]

        # Load data sources
        wrds_df = self._get_wrds_fundamentals()
        uss_df = self._get_uss_financial_data()

        if wrds_df.empty or uss_df.empty:
            return []

        results = []
        end_year = 2024  # Most recent year

        for period in periods:
            start_year = end_year - period

            for metric in metrics:
                # Skip BSL for revenue/ebitda (no data)
                if metric in self.MEDIUM_CONFIDENCE_METRICS:
                    peer_data = wrds_df[wrds_df['ticker'] != 'BSL']
                else:
                    peer_data = wrds_df

                # Calculate USS CAGR
                uss_start = uss_df[uss_df['year'] == start_year]
                uss_end = uss_df[uss_df['year'] == end_year]

                uss_cagr = None
                if not uss_start.empty and not uss_end.empty:
                    start_val = uss_start[metric].iloc[0] if metric in uss_start.columns else None
                    end_val = uss_end[metric].iloc[0] if metric in uss_end.columns else None
                    uss_cagr = self.calculate_cagr(start_val, end_val, period)

                # Calculate peer CAGRs
                peer_cagrs = []
                for ticker in peer_data['ticker'].unique():
                    ticker_data = peer_data[peer_data['ticker'] == ticker]
                    t_start = ticker_data[ticker_data['year'] == start_year]
                    t_end = ticker_data[ticker_data['year'] == end_year]

                    if not t_start.empty and not t_end.empty:
                        start_val = t_start[metric].iloc[0] if metric in t_start.columns else None
                        end_val = t_end[metric].iloc[0] if metric in t_end.columns else None
                        cagr = self.calculate_cagr(start_val, end_val, period)
                        if cagr is not None:
                            peer_cagrs.append(cagr)

                if not peer_cagrs:
                    continue

                peer_series = pd.Series(peer_cagrs)

                # Calculate USS percentile
                uss_percentile = None
                if uss_cagr is not None:
                    below_count = (peer_series < uss_cagr).sum()
                    uss_percentile = below_count / len(peer_series) * 100

                growth_stats = GrowthStats(
                    metric=metric,
                    period_years=period,
                    start_year=start_year,
                    end_year=end_year,
                    uss_cagr=uss_cagr,
                    peer_min=peer_series.min(),
                    peer_q1=peer_series.quantile(0.25),
                    peer_median=peer_series.median(),
                    peer_mean=peer_series.mean(),
                    peer_q3=peer_series.quantile(0.75),
                    peer_max=peer_series.max(),
                    peer_count=len(peer_series),
                    uss_percentile=uss_percentile
                )
                results.append(growth_stats)

        return results

    def get_peer_timeseries(self, metric: str, start_year: int = 2019,
                            end_year: int = 2024) -> pd.DataFrame:
        """Get long-format peer data for trend charts.

        Args:
            metric: Metric name to extract
            start_year: Start year for timeseries
            end_year: End year for timeseries

        Returns:
            DataFrame in long format with columns: ticker, company_name, year, value
        """
        wrds_df = self._get_wrds_fundamentals()

        if wrds_df.empty or metric not in wrds_df.columns:
            return pd.DataFrame()

        # Filter years and metric
        mask = (wrds_df['year'] >= start_year) & (wrds_df['year'] <= end_year)
        if metric in self.MEDIUM_CONFIDENCE_METRICS:
            mask = mask & (wrds_df['ticker'] != 'BSL')

        result = wrds_df.loc[mask, ['ticker', 'company_name', 'year', metric]].copy()
        result = result.rename(columns={metric: 'value'})
        result = result.dropna(subset=['value'])

        return result.reset_index(drop=True)

    def get_rolling_period_analysis(self, metrics: List[str] = None,
                                    window_years: int = 3) -> pd.DataFrame:
        """Calculate rolling CAGRs (e.g., 2019-21, 2020-22, 2021-23, 2022-24).

        Args:
            metrics: List of metrics to analyze
            window_years: Rolling window size in years

        Returns:
            DataFrame with columns: ticker, metric, period_start, period_end, cagr
        """
        if metrics is None:
            metrics = ['revenue', 'ebitda', 'net_income', 'capex']

        wrds_df = self._get_wrds_fundamentals()
        uss_df = self._get_uss_financial_data()

        if wrds_df.empty:
            return pd.DataFrame()

        records = []
        available_years = sorted(wrds_df['year'].unique())

        # Generate rolling periods
        for start_year in available_years:
            end_year = start_year + window_years
            if end_year > max(available_years):
                break

            for metric in metrics:
                # Skip BSL for medium confidence metrics
                if metric in self.MEDIUM_CONFIDENCE_METRICS:
                    peer_data = wrds_df[wrds_df['ticker'] != 'BSL']
                else:
                    peer_data = wrds_df

                # Calculate for each peer
                for ticker in peer_data['ticker'].unique():
                    ticker_data = peer_data[peer_data['ticker'] == ticker]
                    t_start = ticker_data[ticker_data['year'] == start_year]
                    t_end = ticker_data[ticker_data['year'] == end_year]

                    if not t_start.empty and not t_end.empty:
                        start_val = t_start[metric].iloc[0] if metric in t_start.columns else None
                        end_val = t_end[metric].iloc[0] if metric in t_end.columns else None
                        cagr = self.calculate_cagr(start_val, end_val, window_years)
                        if cagr is not None:
                            company_name = t_start['company_name'].iloc[0] if 'company_name' in t_start.columns else ticker
                            records.append({
                                'ticker': ticker,
                                'company_name': company_name,
                                'metric': metric,
                                'period_start': start_year,
                                'period_end': end_year,
                                'period_label': f"{start_year}-{str(end_year)[2:]}",
                                'cagr': cagr
                            })

                # Calculate for USS
                if not uss_df.empty and metric in uss_df.columns:
                    uss_start = uss_df[uss_df['year'] == start_year]
                    uss_end = uss_df[uss_df['year'] == end_year]

                    if not uss_start.empty and not uss_end.empty:
                        start_val = uss_start[metric].iloc[0]
                        end_val = uss_end[metric].iloc[0]
                        cagr = self.calculate_cagr(start_val, end_val, window_years)
                        if cagr is not None:
                            records.append({
                                'ticker': 'X',
                                'company_name': 'United States Steel',
                                'metric': metric,
                                'period_start': start_year,
                                'period_end': end_year,
                                'period_label': f"{start_year}-{str(end_year)[2:]}",
                                'cagr': cagr
                            })

        return pd.DataFrame(records)

    def get_uss_longterm_historical(self, metrics: List[str] = None) -> pd.DataFrame:
        """Get USS-only decade CAGRs from 1990s to 2020s.

        Args:
            metrics: List of metrics to analyze

        Returns:
            DataFrame with decade CAGRs for USS only
        """
        if metrics is None:
            metrics = ['revenue', 'ebitda', 'net_income', 'capex', 'total_assets']

        uss_df = self._get_uss_financial_data()

        if uss_df.empty:
            return pd.DataFrame()

        # Define decades
        decades = [
            ('1990s', 1990, 1999),
            ('2000s', 2000, 2009),
            ('2010s', 2010, 2019),
            ('2020s', 2020, 2024),  # Partial decade
        ]

        records = []
        for decade_name, start_year, end_year in decades:
            # Find actual available years in this decade
            decade_data = uss_df[(uss_df['year'] >= start_year) & (uss_df['year'] <= end_year)]

            if decade_data.empty or len(decade_data) < 2:
                continue

            actual_start = decade_data['year'].min()
            actual_end = decade_data['year'].max()
            period = actual_end - actual_start

            if period <= 0:
                continue

            for metric in metrics:
                if metric not in decade_data.columns:
                    continue

                start_row = decade_data[decade_data['year'] == actual_start]
                end_row = decade_data[decade_data['year'] == actual_end]

                if start_row.empty or end_row.empty:
                    continue

                start_val = start_row[metric].iloc[0]
                end_val = end_row[metric].iloc[0]
                cagr = self.calculate_cagr(start_val, end_val, period)

                records.append({
                    'decade': decade_name,
                    'metric': metric,
                    'start_year': actual_start,
                    'end_year': actual_end,
                    'start_value': start_val,
                    'end_value': end_val,
                    'cagr': cagr,
                    'years': period
                })

        return pd.DataFrame(records)

    def get_growth_summary_table(self) -> pd.DataFrame:
        """Generate a summary table of growth statistics for dashboard display.

        Returns:
            DataFrame formatted for display with percentile color coding info
        """
        growth_stats = self.get_multiyear_growth_analysis()

        if not growth_stats:
            return pd.DataFrame()

        records = []
        for gs in growth_stats:
            # Determine color coding based on percentile
            if gs.uss_percentile is not None:
                if gs.uss_percentile >= 75:
                    color_code = 'green'
                elif gs.uss_percentile >= 25:
                    color_code = 'yellow'
                else:
                    color_code = 'red'
            else:
                color_code = 'gray'

            # Format CAGR values as percentages
            records.append({
                'Metric': gs.metric.replace('_', ' ').title(),
                'Period': f"{gs.period_years}-Year",
                'Years': f"{gs.start_year}-{gs.end_year}",
                'USS CAGR': f"{gs.uss_cagr:.1%}" if gs.uss_cagr is not None else 'N/A',
                'Peer Median': f"{gs.peer_median:.1%}",
                'Peer Range': f"[{gs.peer_min:.1%}, {gs.peer_max:.1%}]",
                'USS Percentile': f"{gs.uss_percentile:.0f}th" if gs.uss_percentile is not None else 'N/A',
                'Peer Count': gs.peer_count,
                '_color_code': color_code,
                '_uss_cagr_raw': gs.uss_cagr,
                '_peer_median_raw': gs.peer_median,
            })

        return pd.DataFrame(records)


# =============================================================================
# Convenience functions
# =============================================================================

def get_benchmark_stats(metric: str = 'tev_ebitda') -> BenchmarkStats:
    """Quick access to benchmark statistics for a specific metric."""
    benchmark = BenchmarkData()
    multiples = benchmark.get_peer_multiples()
    return multiples.get(metric, BenchmarkStats(
        min=np.nan, q1=np.nan, median=np.nan,
        mean=np.nan, q3=np.nan, max=np.nan, count=0
    ))


def get_exit_multiple(scenario: str = 'base') -> float:
    """
    Get exit multiple for a scenario.

    Args:
        scenario: 'low', 'base', or 'high'

    Returns:
        Exit multiple value
    """
    benchmark = BenchmarkData()
    multiples = benchmark.get_exit_multiple_range()
    return multiples.get(scenario, 5.0)


if __name__ == "__main__":
    # Demo usage
    print("=" * 60)
    print("Benchmark Data Demo")
    print("=" * 60)

    benchmark = BenchmarkData()

    # Valuation multiples
    print("\n--- Valuation Multiples ---")
    multiples = benchmark.get_peer_multiples()
    for name, stats in multiples.items():
        print(f"{name}: median={stats.median:.2f}, range=[{stats.min:.2f}, {stats.max:.2f}]")

    # Exit multiple range
    print("\n--- Recommended Exit Multiples ---")
    exit_range = benchmark.get_exit_multiple_range()
    print(f"Low: {exit_range['low']:.2f}x, Base: {exit_range['base']:.2f}x, High: {exit_range['high']:.2f}x")

    # Margins
    print("\n--- Margin Benchmarks ---")
    margins = benchmark.get_peer_margins()
    if not margins.empty:
        print(margins.head().to_string())

    # Summary
    print("\n--- Benchmark Summary ---")
    summary = benchmark.get_benchmark_summary()
    if not summary.empty:
        print(summary.to_string())
