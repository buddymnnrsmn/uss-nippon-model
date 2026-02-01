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

    def __init__(self, data_dir: str = "references"):
        self.data_dir = Path(data_dir)
        self.financials_file = self.data_dir / "United States Steel Corporation Financials.xls"
        self.comps_file = self.data_dir / "Company Comparable Analysis United States Steel Corporation.xls"
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
        sheets = ['Financial Data', 'Capital Structure', 'Financial Ratios', 'Credit Ratios', 'Implied Valuation']

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
        return {
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

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# =============================================================================
# Standalone functions for quick access
# =============================================================================

def load_financials(data_dir: str = "references") -> Dict[str, pd.DataFrame]:
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


def load_comps(data_dir: str = "references") -> Dict[str, pd.DataFrame]:
    """Quick load of comparable company and M&A data."""
    loader = USSteelDataLoader(data_dir)
    ma_trans, ma_summary = loader.load_ma_transactions()
    return {
        'comparable_companies': loader.load_comparable_companies(),
        'ma_transactions': ma_trans,
        'ma_summary': ma_summary,
    }


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
