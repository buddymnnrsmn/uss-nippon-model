"""
Data Loader for U.S. Steel Financial Model
Parses Capital IQ Excel exports into clean pandas DataFrames for analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import warnings

# Suppress pandas FutureWarning for replace() downcasting behavior
warnings.filterwarnings('ignore', category=FutureWarning, message='.*Downcasting behavior.*')
# Suppress xlrd file size warnings (benign - files read correctly)
warnings.filterwarnings('ignore', message='.*file size.*not 512.*')
# Also suppress via logging for xlrd
import logging
logging.getLogger('xlrd').setLevel(logging.ERROR)


class USSteelDataLoader:
    """Loads and parses U.S. Steel financial data from Capital IQ exports."""

    def __init__(self, data_dir: str = "reference_materials"):
        self.data_dir = Path(data_dir)
        self.financials_file = self.data_dir / "United States Steel Corporation Financials.xls"
        # Use the 12/31/2023 vintage comps file
        self.comps_file = self.data_dir / "steel_comps" / "Company Comparable Analysis uss.xls"
        self.ma_file = self.data_dir / "United States Steel Corporation Comparable M A Transactions.xls"

        # Cache for loaded data
        self._cache: Dict[str, pd.DataFrame] = {}

    def _clean_column_headers(self, df: pd.DataFrame, header_row: int) -> pd.DataFrame:
        """Extract period dates from header row and set as column names."""
        headers = df.iloc[header_row].tolist()
        df = df.iloc[header_row + 2:].copy()  # Skip header and currency rows
        df.columns = headers
        df = df.rename(columns={df.columns[0]: 'Item'})
        return df

    def _clean_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric columns, handling '-' as NaN."""
        for col in df.columns[1:]:
            # Replace '-' with NaN and convert to numeric
            series = df[col].copy()
            series = series.replace('-', np.nan)
            series = series.replace('', np.nan)
            df[col] = pd.to_numeric(series, errors='coerce')
        return df

    def _parse_dates_from_header(self, header_val) -> Optional[str]:
        """Parse date from Capital IQ header formats."""
        if pd.isna(header_val):
            return None
        header_str = str(header_val)
        # Handle formats like "12 months\nDec-31-2023" or datetime objects
        if hasattr(header_val, 'strftime'):
            return header_val.strftime('%Y-%m-%d')
        if '\n' in header_str:
            parts = header_str.split('\n')
            return parts[-1].strip()
        return header_str

    # =========================================================================
    # Financial Statement Loaders
    # =========================================================================

    def load_income_statement(self, use_cache: bool = True) -> pd.DataFrame:
        """Load income statement data."""
        cache_key = 'income_statement'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Income Statement', header=None)

        # Find data start row (where "Revenue" appears)
        for i, val in enumerate(df.iloc[:, 0]):
            if str(val).strip() == 'Revenue':
                data_start = i
                break

        # Header row is 3 rows before Revenue
        header_row = data_start - 3

        # Extract headers and data
        headers = ['Item'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 1:] if pd.notna(h)]

        # Get data rows until we hit empty section
        data = df.iloc[data_start:].copy()
        data = data.dropna(how='all')

        # Remove rows where first column is NaN (section breaks)
        data = data[data.iloc[:, 0].notna()]

        # Set columns
        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers

        # Clean numeric values
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    def load_balance_sheet(self, use_cache: bool = True) -> pd.DataFrame:
        """Load balance sheet data."""
        cache_key = 'balance_sheet'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Balance Sheet', header=None)

        # Find header row (Balance Sheet as of:)
        for i, val in enumerate(df.iloc[:, 0]):
            if 'Balance Sheet as of' in str(val):
                header_row = i
                break

        # Extract headers
        headers = ['Item'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 1:] if pd.notna(h)]

        # Data starts after currency row
        data_start = header_row + 2
        data = df.iloc[data_start:].copy()

        # Remove rows where first column is NaN or ASSETS/LIABILITIES headers
        data = data[data.iloc[:, 0].notna()]
        data = data[~data.iloc[:, 0].isin(['ASSETS', 'LIABILITIES'])]

        # Set columns
        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers

        # Clean numeric values
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    def load_cash_flow(self, use_cache: bool = True) -> pd.DataFrame:
        """Load cash flow statement data."""
        cache_key = 'cash_flow'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Cash Flow', header=None)

        # Find header row
        for i, val in enumerate(df.iloc[:, 0]):
            if 'Fiscal Period Ending' in str(val):
                header_row = i
                break

        headers = ['Item'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 1:] if pd.notna(h)]

        # Data starts after currency row
        data_start = header_row + 2
        data = df.iloc[data_start:].copy()
        data = data[data.iloc[:, 0].notna()]

        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    def load_ratios(self, use_cache: bool = True) -> pd.DataFrame:
        """Load financial ratios."""
        cache_key = 'ratios'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Ratios', header=None)

        # Find header row
        for i, val in enumerate(df.iloc[:, 0]):
            if 'Fiscal Period Ending' in str(val):
                header_row = i
                break

        headers = ['Item'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 1:] if pd.notna(h)]

        data_start = header_row + 1
        data = df.iloc[data_start:].copy()
        data = data[data.iloc[:, 0].notna()]

        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    def load_multiples(self, use_cache: bool = True) -> pd.DataFrame:
        """Load valuation multiples."""
        cache_key = 'multiples'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Multiples', header=None)

        # Find header row (For Quarter Ending)
        for i, val in enumerate(df.iloc[:, 0]):
            if 'For Quarter Ending' in str(val):
                header_row = i
                break

        headers = ['Item', 'Stat'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 2:] if pd.notna(h)]

        data_start = header_row + 1
        data = df.iloc[data_start:].copy()

        # Forward fill the metric names
        data.iloc[:, 0] = data.iloc[:, 0].ffill()
        data = data[data.iloc[:, 1].notna()]

        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    def load_capital_structure(self, use_cache: bool = True) -> pd.DataFrame:
        """Load historical capitalization data."""
        cache_key = 'capital_structure'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.financials_file, sheet_name='Historical Capitalization', header=None)

        # Find header row
        for i, val in enumerate(df.iloc[:, 0]):
            if 'Capitalization as of' in str(val):
                header_row = i
                break

        headers = ['Item'] + [self._parse_dates_from_header(h) for h in df.iloc[header_row, 1:] if pd.notna(h)]

        data_start = header_row + 1
        data = df.iloc[data_start:].copy()
        data = data[data.iloc[:, 0].notna()]

        data.columns = range(len(data.columns))
        data = data.iloc[:, :len(headers)]
        data.columns = headers
        data = self._clean_numeric(data)
        data = data.reset_index(drop=True)

        self._cache[cache_key] = data
        return data

    # =========================================================================
    # Comparable Company Analysis
    # =========================================================================

    def load_comparable_companies(self, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """Load all comparable company analysis sheets."""
        cache_key = 'comparable_companies'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        result = {}
        # Sheets available in 12/31/2023 vintage Capital IQ export
        sheets = ['Financial Data', 'Trading Multiples', 'Operating Statistics', 'Credit Health Panel', 'Implied Valuation']

        for sheet in sheets:
            try:
                df = pd.read_excel(self.comps_file, sheet_name=sheet, header=None)

                # Find header row (Company Name)
                header_row = None
                for i, val in enumerate(df.iloc[:, 0]):
                    if 'Company Name' in str(val):
                        header_row = i
                        break

                if header_row is None:
                    continue

                # Get headers from the header row
                headers = df.iloc[header_row].tolist()
                # Clean up None values in headers
                headers = [h if pd.notna(h) else f'Col_{i}' for i, h in enumerate(headers)]

                # Extract data starting after header row
                data = df.iloc[header_row + 1:].copy()
                data.columns = headers

                # Filter valid company rows
                data = data[data.iloc[:, 0].notna()]
                # Exclude summary stats and footer rows
                first_col = data.iloc[:, 0].astype(str)
                exclude_patterns = (
                    'Summary Statistics|High|Low|Mean|Median|^$|'
                    'Displaying|Values converted|Companies by default|'
                    'Historical Equity|S&P Capital IQ'
                )
                mask = ~first_col.str.contains(exclude_patterns, na=False, regex=True)
                data = data[mask]

                data = self._clean_numeric(data)
                data = data.reset_index(drop=True)

                result[sheet.lower().replace(' ', '_')] = data
            except Exception as e:
                print(f"Warning: Could not load sheet {sheet}: {e}")

        self._cache[cache_key] = result
        return result

    def load_comp_summary_stats(self, use_cache: bool = True) -> pd.DataFrame:
        """Load summary statistics from comparable company analysis."""
        df = pd.read_excel(self.comps_file, sheet_name='Financial Data', header=None)

        # Find Summary Statistics row
        for i, val in enumerate(df.iloc[:, 0]):
            if 'Summary Statistics' in str(val):
                stats_start = i
                break

        stats = df.iloc[stats_start:stats_start + 5].copy()
        stats.columns = df.iloc[13]  # Header row
        stats = self._clean_numeric(stats)
        stats = stats.reset_index(drop=True)

        return stats

    # =========================================================================
    # M&A Transactions
    # =========================================================================

    def load_ma_transactions(self, use_cache: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load M&A transaction comparables.
        Returns: (transactions_df, summary_stats_df)
        """
        cache_key = 'ma_transactions'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        df = pd.read_excel(self.ma_file, sheet_name='Comparable M A Transactions', header=None)

        # Header is row 6
        headers = df.iloc[6].tolist()

        # Transactions data (rows 7-15)
        transactions = df.iloc[7:16].copy()
        transactions.columns = headers
        transactions = transactions[transactions['Announced Date'].notna()]

        # Clean numeric columns
        for col in ['Target TEV(USD mm)', 'Size(USD mm)']:
            series = transactions[col].copy()
            series = series.replace('-', np.nan)
            transactions[col] = pd.to_numeric(series, errors='coerce')

        # Parse multiples (remove 'x' suffix)
        for col in ['Implied TEV/LTM Revenue', 'Implied TEV/LTM EBITDA']:
            series = transactions[col].astype(str).str.replace('x', '', regex=False)
            series = series.replace('-', np.nan)
            transactions[col] = pd.to_numeric(series, errors='coerce')

        transactions = transactions.reset_index(drop=True)

        # Summary statistics (rows 16-19)
        summary = df.iloc[16:20].copy()
        summary.columns = headers
        summary['Stat'] = ['Max', 'Median', 'Mean', 'Min']
        summary = summary[['Stat', 'Size(USD mm)', 'Implied TEV/LTM Revenue', 'Implied TEV/LTM EBITDA']]

        for col in summary.columns[1:]:
            series = summary[col].astype(str).str.replace('x', '', regex=False)
            series = series.replace('-', np.nan)
            summary[col] = pd.to_numeric(series, errors='coerce')

        summary = summary.reset_index(drop=True)

        self._cache[cache_key] = (transactions, summary)
        return transactions, summary

    # =========================================================================
    # Steel Operational Metrics
    # =========================================================================

    def load_steel_metrics(self, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Load steel-specific operational metrics from local data sources.

        Combines:
        - Manual operational data from local/steel_operational_metrics.xlsx
        - WRDS Compustat data (if wrds_loader is available and configured)

        Returns:
            Dict with keys: 'capacity', 'utilization', 'shipments', 'wrds_fundamentals',
            'wrds_segments', 'wrds_geographic', 'derived_metrics'
        """
        cache_key = 'steel_metrics'
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        result = {}

        # Load manual operational data from local folder
        local_metrics_file = Path(__file__).parent / 'local' / 'steel_operational_metrics.xlsx'
        if local_metrics_file.exists():
            result.update(self._load_manual_steel_metrics(local_metrics_file))
        else:
            print(f"Note: Manual metrics file not found at {local_metrics_file}")

        # Try to load WRDS data if available
        wrds_data = self._load_wrds_data()
        if wrds_data:
            result.update(wrds_data)

        # Calculate derived metrics if we have both shipments and segment revenue
        if 'shipments' in result and 'wrds_segments' in result:
            result['derived_metrics'] = self._calculate_derived_steel_metrics(
                result['shipments'], result['wrds_segments']
            )

        self._cache[cache_key] = result
        return result

    def _load_manual_steel_metrics(self, filepath: Path) -> Dict[str, pd.DataFrame]:
        """Load manual operational metrics from Excel template."""
        result = {}

        try:
            # Load capacity data
            capacity = pd.read_excel(filepath, sheet_name='Capacity')
            capacity = capacity.dropna(subset=['Raw_Capacity_Mtons'], how='all')
            result['capacity'] = capacity

            # Load utilization data
            utilization = pd.read_excel(filepath, sheet_name='Utilization')
            utilization = utilization.dropna(subset=['Utilization_Pct'], how='all')
            result['utilization'] = utilization

            # Load shipments data
            shipments = pd.read_excel(filepath, sheet_name='Shipments')
            shipments = shipments.dropna(subset=['Shipments_Ktons'], how='all')
            result['shipments'] = shipments

            print(f"Loaded manual steel metrics: {len(result['capacity'])} capacity rows, "
                  f"{len(result['utilization'])} utilization rows, {len(result['shipments'])} shipment rows")

        except Exception as e:
            print(f"Warning: Error loading manual steel metrics: {e}")

        return result

    def _load_wrds_data(self) -> Optional[Dict[str, pd.DataFrame]]:
        """
        Load WRDS Compustat data if wrds_loader is available.

        Returns None if WRDS is not configured or unavailable.
        """
        try:
            # Import from local folder
            import sys
            local_path = Path(__file__).parent / 'local'
            if local_path.exists() and str(local_path) not in sys.path:
                sys.path.insert(0, str(local_path))

            from wrds_loader import WRDSDataLoader

            loader = WRDSDataLoader()

            result = {
                'wrds_fundamentals': loader.fetch_fundamentals(),
                'wrds_segments': loader.fetch_business_segments(),
                'wrds_geographic': loader.fetch_geographic_segments(),
            }

            # Add calculated metrics
            if 'wrds_fundamentals' in result:
                result['wrds_metrics'] = loader.calculate_metrics(result['wrds_fundamentals'])

            if 'wrds_segments' in result:
                result['wrds_segment_mix'] = loader.calculate_segment_mix(result['wrds_segments'])

            if 'wrds_geographic' in result:
                result['wrds_geo_mix'] = loader.calculate_geographic_mix(result['wrds_geographic'])

            loader.close()
            return result

        except ImportError:
            print("Note: WRDS loader not available (wrds_loader.py not found in local/)")
            return None
        except ValueError as e:
            print(f"Note: WRDS not configured: {e}")
            return None
        except Exception as e:
            print(f"Warning: Error loading WRDS data: {e}")
            return None

    def _calculate_derived_steel_metrics(
        self,
        shipments: pd.DataFrame,
        segments: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate derived metrics like Average Selling Price.

        ASP = Segment Revenue / Shipment Volume
        """
        # This is a simplified calculation - would need mapping between
        # shipment segments and WRDS segments for accurate ASP
        derived = []

        # Group shipments by company and year
        if not shipments.empty:
            grouped = shipments.groupby(['Company', 'Year'])['Shipments_Ktons'].sum().reset_index()
            grouped.columns = ['Company', 'Year', 'Total_Shipments_Ktons']
            derived.append(grouped)

        if derived:
            return pd.concat(derived, ignore_index=True)
        return pd.DataFrame()

    def get_peer_benchmark_summary(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        Get summary benchmark data for all peers.

        Combines Capital IQ comparable data with WRDS/manual operational data.
        """
        # Start with Capital IQ comps
        comps = self.load_comparable_companies()

        if 'financial_data' not in comps:
            return pd.DataFrame()

        summary = comps['financial_data'].copy()

        # Try to add steel metrics
        steel = self.load_steel_metrics(use_cache=True)

        if 'capacity' in steel and not steel['capacity'].empty:
            # Merge capacity data
            cap_latest = steel['capacity'].sort_values('Year', ascending=False)
            cap_latest = cap_latest.drop_duplicates(subset=['Company'], keep='first')
            # Would need company name mapping to merge properly
            pass

        return summary

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_item(self, df: pd.DataFrame, item_name: str) -> pd.Series:
        """Get a single row from a DataFrame by item name."""
        mask = df['Item'].str.contains(item_name, case=False, na=False)
        if mask.any():
            return df[mask].iloc[0]
        return pd.Series()

    def get_latest_values(self, df: pd.DataFrame, n_years: int = 5) -> pd.DataFrame:
        """Get the most recent n years of data."""
        cols = ['Item'] + list(df.columns[-n_years:])
        return df[cols]

    def load_all(self) -> Dict[str, pd.DataFrame]:
        """Load all available data into a dictionary."""
        data = {
            'income_statement': self.load_income_statement(),
            'balance_sheet': self.load_balance_sheet(),
            'cash_flow': self.load_cash_flow(),
            'ratios': self.load_ratios(),
            'multiples': self.load_multiples(),
            'capital_structure': self.load_capital_structure(),
            'comparable_companies': self.load_comparable_companies(),
            'ma_transactions': self.load_ma_transactions()[0],
            'ma_summary': self.load_ma_transactions()[1],
        }

        # Add steel metrics if available
        steel_metrics = self.load_steel_metrics()
        if steel_metrics:
            data['steel_metrics'] = steel_metrics

        return data

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# =============================================================================
# Standalone functions for quick access
# =============================================================================

def load_financials(data_dir: str = "reference_materials") -> Dict[str, pd.DataFrame]:
    """Quick load of all financial statement data."""
    loader = USSteelDataLoader(data_dir)
    return {
        'income_statement': loader.load_income_statement(),
        'balance_sheet': loader.load_balance_sheet(),
        'cash_flow': loader.load_cash_flow(),
        'ratios': loader.load_ratios(),
        'multiples': loader.load_multiples(),
        'capital_structure': loader.load_capital_structure(),
    }


def load_comps(data_dir: str = "reference_materials") -> Dict[str, pd.DataFrame]:
    """Quick load of comparable company and M&A data."""
    loader = USSteelDataLoader(data_dir)
    ma_trans, ma_summary = loader.load_ma_transactions()
    return {
        'comparable_companies': loader.load_comparable_companies(),
        'ma_transactions': ma_trans,
        'ma_summary': ma_summary,
    }


def load_steel_metrics(data_dir: str = "reference_materials") -> Dict[str, pd.DataFrame]:
    """
    Quick load of steel-specific operational metrics.

    Returns dict with capacity, utilization, shipments, and WRDS data if available.
    """
    loader = USSteelDataLoader(data_dir)
    return loader.load_steel_metrics()


if __name__ == "__main__":
    # Demo usage
    loader = USSteelDataLoader()

    print("=" * 60)
    print("U.S. Steel Financial Data Loader")
    print("=" * 60)

    # Load Income Statement
    print("\n--- Income Statement (Latest 5 Years) ---")
    income = loader.load_income_statement()
    print(loader.get_latest_values(income, 5).head(10).to_string())

    # Load Balance Sheet
    print("\n--- Balance Sheet (Latest 5 Years) ---")
    balance = loader.load_balance_sheet()
    print(loader.get_latest_values(balance, 5).head(10).to_string())

    # Load Ratios
    print("\n--- Financial Ratios (Latest 5 Years) ---")
    ratios = loader.load_ratios()
    print(loader.get_latest_values(ratios, 5).head(10).to_string())

    # Load M&A Transactions
    print("\n--- M&A Transaction Comparables ---")
    ma_trans, ma_summary = loader.load_ma_transactions()
    print(ma_trans[['Announced Date', 'Target', 'Size(USD mm)', 'Implied TEV/LTM EBITDA']].to_string())

    print("\n--- M&A Summary Statistics ---")
    print(ma_summary.to_string())

    # Load Comparable Companies
    print("\n--- Comparable Companies ---")
    comps = loader.load_comparable_companies()
    if 'financial_data' in comps:
        print(comps['financial_data'].iloc[:, :5].to_string())
