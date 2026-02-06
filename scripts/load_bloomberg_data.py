"""
Bloomberg Data Loader and Validator
Loads all 24 organized Bloomberg files and validates data quality
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class BloombergDataLoader:
    """Load and validate Bloomberg data from organized exports"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            self.base_path = Path(__file__).parent.parent / "market-data" / "exports"
        else:
            self.base_path = Path(base_path)

        self.data = {}
        self.validation_results = {}
        self.summary_stats = {}

    def load_all_data(self) -> Dict[str, pd.DataFrame]:
        """Load all Bloomberg data files"""
        print("=" * 80)
        print("BLOOMBERG DATA LOADER - Starting data load...")
        print("=" * 80)
        print()

        categories = {
            '01_steel_prices': self._load_steel_prices,
            '02_rates_credit': self._load_rates_credit,
            '03_demand_drivers': self._load_demand_drivers,
            '04_energy': self._load_energy,
            '05_equities': self._load_equities,
            '06_synergy_validation': self._load_synergy_validation,
            '07_macro': self._load_macro
        }

        for category, loader_func in categories.items():
            print(f"\n📂 Loading {category.replace('_', ' ').title()}...")
            print("-" * 80)
            try:
                loader_func()
            except Exception as e:
                print(f"❌ ERROR loading {category}: {str(e)}")
                continue

        print("\n" + "=" * 80)
        print(f"✅ Data load complete! Loaded {len(self.data)} datasets")
        print("=" * 80)

        return self.data

    def _load_excel_file(self, filepath: Path, name: str,
                        date_col: int = 0, value_col: int = 1,
                        skiprows: int = 0) -> pd.DataFrame:
        """Generic Excel file loader with error handling"""
        try:
            df = pd.read_excel(filepath, skiprows=skiprows)

            # Ensure we have at least 2 columns
            if df.shape[1] < 2:
                raise ValueError(f"File has fewer than 2 columns: {df.shape[1]}")

            # Get column names
            cols = df.columns.tolist()
            date_col_name = cols[date_col]
            value_col_name = cols[value_col]

            # Create clean dataframe
            result = pd.DataFrame({
                'date': pd.to_datetime(df[date_col_name]),
                'value': pd.to_numeric(df[value_col_name], errors='coerce')
            })

            # Remove NaN values
            result = result.dropna()

            # Sort by date
            result = result.sort_values('date').reset_index(drop=True)

            rows = len(result)
            start = result['date'].min().strftime('%Y-%m-%d')
            end = result['date'].max().strftime('%Y-%m-%d')

            print(f"  ✓ {name:40s} | {rows:5d} rows | {start} to {end}")

            return result

        except Exception as e:
            print(f"  ✗ {name:40s} | ERROR: {str(e)}")
            return pd.DataFrame()

    def _load_steel_prices(self):
        """Load steel pricing and capacity data"""
        category_path = self.base_path / "01_steel_prices"

        files = {
            'hrc_us_spot': 'bloomberg_hrc_us_spot_weekly_20150101-20260202.xlsx',
            'hrc_us_futures': 'bloomberg_hrc_us_futures_daily_20081027-20260202.xlsx',
            'crc_us_spot': 'bloomberg_crc_us_spot_weekly_20150101-20260202.xlsx',
            'hrc_eu_spot': 'bloomberg_hrc_eu_spot_weekly_20140101-20260202.xlsx',
            'octg_us_spot': 'bloomberg_octg_us_spot_weekly_20150101-20260202.xlsx',
            'scrap_us_ppi': 'bloomberg_scrap_us_ppi_monthly_20000101-20260202.xlsx',
            'capacity_us': 'bloomberg_capacity_us_aisi_weekly_19950101-20260202.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                self.data[key] = self._load_excel_file(filepath, key)

    def _load_rates_credit(self):
        """Load interest rates and credit spreads"""
        category_path = self.base_path / "02_rates_credit"

        files = {
            'ust_10y': 'bloomberg_ust_10y_daily_19900101-20260202.xlsx',
            'ust_30y': 'bloomberg_ust_30y_daily_19900101-20260202.xlsx',
            'spread_bbb': 'bloomberg_spread_bbb_daily_20000101-20260202.xlsx',
            'spread_hy': 'bloomberg_spread_hy_daily_20000101-20260202.xlsx',
            'sofr': 'bloomberg_sofr_daily_20180101-20260202.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                self.data[key] = self._load_excel_file(filepath, key)

    def _load_demand_drivers(self):
        """Load automotive, housing, and manufacturing indicators"""
        category_path = self.base_path / "03_demand_drivers"

        files = {
            'auto_production': 'bloomberg_auto_production_us_monthly_19900101-20260202.xlsx',
            'auto_sales': 'bloomberg_auto_sales_saar_us_monthly_19900101-20260202.xlsx',
            'housing_starts': 'bloomberg_housing_starts_us_monthly_19900101-20260202.xlsx',
            'ism_pmi': 'bloomberg_ism_pmi_us_monthly_19900101-20260202.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                self.data[key] = self._load_excel_file(filepath, key)

    def _load_energy(self):
        """Load oil and rig count data"""
        category_path = self.base_path / "04_energy"

        files = {
            'wti_crude': 'bloomberg_wti_crude_daily_19900101-20260202.xlsx',
            'rig_count': 'bloomberg_rig_count_us_weekly_20000101-20260202.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                self.data[key] = self._load_excel_file(filepath, key)

    def _load_equities(self):
        """Load USS and Nippon stock prices"""
        category_path = self.base_path / "05_equities"

        files = {
            'stock_uss': 'bloomberg_stock_uss_daily_20000101-20260202.xlsx',
            'stock_nippon': 'bloomberg_stock_nippon_daily_20000101-20260202.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                self.data[key] = self._load_excel_file(filepath, key)

    def _load_synergy_validation(self):
        """Load EV forecasts and market analysis"""
        category_path = self.base_path / "06_synergy_validation"

        # These files may have different structures, load carefully
        files = {
            'ev_forecast': 'bloomberg_ev_forecast_us_annual_2024-2035.xlsx',
            'steel_demand': 'bloomberg_steel_demand_us_eu_2015-2026.xlsx',
            'steel_costs': 'bloomberg_steel_costs_us_eu_2015-2026.xlsx'
        }

        for key, filename in files.items():
            filepath = category_path / filename
            if filepath.exists():
                try:
                    # Try standard loading first
                    self.data[key] = self._load_excel_file(filepath, key)
                except:
                    # If it fails, just load raw and we'll inspect it
                    df = pd.read_excel(filepath)
                    self.data[key] = df
                    print(f"  ⚠ {key:40s} | Loaded raw (non-standard format)")

    def _load_macro(self):
        """Load macro aggregate data"""
        category_path = self.base_path / "07_macro"

        filepath = category_path / 'bloomberg_macro_aggregate_us_2015-2026.xlsx'
        if filepath.exists():
            try:
                self.data['macro_aggregate'] = self._load_excel_file(filepath, 'macro_aggregate')
            except:
                df = pd.read_excel(filepath)
                self.data['macro_aggregate'] = df
                print(f"  ⚠ {'macro_aggregate':40s} | Loaded raw (non-standard format)")

    def validate_data(self) -> Dict[str, dict]:
        """Validate all loaded datasets"""
        print("\n" + "=" * 80)
        print("DATA VALIDATION - Checking data quality...")
        print("=" * 80)

        for name, df in self.data.items():
            print(f"\n📊 Validating {name}...")
            print("-" * 80)

            if df.empty:
                print(f"  ⚠️  WARNING: Dataset is empty")
                self.validation_results[name] = {'status': 'EMPTY', 'issues': ['No data']}
                continue

            issues = []

            # Check if it has standard format (date, value columns)
            if 'date' in df.columns and 'value' in df.columns:
                # Check for missing values
                missing_count = df['value'].isna().sum()
                if missing_count > 0:
                    issues.append(f"{missing_count} missing values")
                    print(f"  ⚠️  Missing values: {missing_count} ({missing_count/len(df)*100:.1f}%)")

                # Check for date gaps
                if len(df) > 1:
                    date_diff = df['date'].diff()
                    median_gap = date_diff.median()
                    large_gaps = (date_diff > median_gap * 2).sum()
                    if large_gaps > 0:
                        issues.append(f"{large_gaps} large date gaps")
                        print(f"  ⚠️  Large date gaps: {large_gaps} gaps > 2x median")

                # Check for outliers (beyond 5 std devs)
                mean_val = df['value'].mean()
                std_val = df['value'].std()
                outliers = ((df['value'] - mean_val).abs() > 5 * std_val).sum()
                if outliers > 0:
                    issues.append(f"{outliers} extreme outliers")
                    print(f"  ⚠️  Extreme outliers: {outliers} values > 5σ")

                # Check for duplicates
                duplicates = df.duplicated(subset='date').sum()
                if duplicates > 0:
                    issues.append(f"{duplicates} duplicate dates")
                    print(f"  ⚠️  Duplicate dates: {duplicates}")

                # Summary statistics
                print(f"\n  📈 Summary Statistics:")
                print(f"     Range: {df['value'].min():.2f} to {df['value'].max():.2f}")
                print(f"     Mean:  {df['value'].mean():.2f}")
                print(f"     Std:   {df['value'].std():.2f}")
                print(f"     Observations: {len(df)}")

            else:
                print(f"  ℹ️  Non-standard format (not date/value)")
                issues.append("Non-standard format")

            if not issues:
                print(f"\n  ✅ PASSED - No issues found")
                self.validation_results[name] = {'status': 'PASSED', 'issues': []}
            else:
                print(f"\n  ⚠️  ISSUES FOUND: {len(issues)}")
                self.validation_results[name] = {'status': 'WARNING', 'issues': issues}

        return self.validation_results

    def calculate_correlations(self) -> pd.DataFrame:
        """Calculate correlation matrix for key price series"""
        print("\n" + "=" * 80)
        print("CORRELATION ANALYSIS")
        print("=" * 80)

        # Merge key price series on date
        series_to_correlate = {
            'HRC US': 'hrc_us_spot',
            'CRC US': 'crc_us_spot',
            'OCTG US': 'octg_us_spot',
            'HRC EU': 'hrc_eu_spot',
            'Scrap': 'scrap_us_ppi',
            'Capacity': 'capacity_us',
            'WTI': 'wti_crude',
            'Auto Prod': 'auto_production',
            'Housing': 'housing_starts',
            'ISM PMI': 'ism_pmi'
        }

        # Create merged dataframe
        merged = None
        for label, key in series_to_correlate.items():
            if key in self.data and not self.data[key].empty:
                if 'date' in self.data[key].columns and 'value' in self.data[key].columns:
                    df = self.data[key][['date', 'value']].copy()
                    df = df.rename(columns={'value': label})

                    if merged is None:
                        merged = df
                    else:
                        merged = merged.merge(df, on='date', how='outer')

        if merged is not None and len(merged.columns) > 2:
            # Calculate correlations
            corr_matrix = merged.drop('date', axis=1).corr()

            print("\n📊 Correlation Matrix (Pearson):")
            print(corr_matrix.round(2).to_string())

            # Highlight strong correlations
            print("\n🔗 Strong Correlations (|r| > 0.7):")
            for i in range(len(corr_matrix)):
                for j in range(i+1, len(corr_matrix)):
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) > 0.7:
                        var1 = corr_matrix.index[i]
                        var2 = corr_matrix.columns[j]
                        print(f"   {var1:12s} ↔ {var2:12s} : {corr:+.3f}")

            return corr_matrix
        else:
            print("⚠️  Not enough data to calculate correlations")
            return pd.DataFrame()

    def generate_summary_report(self) -> str:
        """Generate comprehensive summary report"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("BLOOMBERG DATA SUMMARY REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Overall stats
        report.append("📊 OVERALL STATISTICS:")
        report.append("-" * 80)
        report.append(f"Total datasets loaded: {len(self.data)}")

        total_rows = sum(len(df) for df in self.data.values() if not df.empty)
        report.append(f"Total data points: {total_rows:,}")

        # Validation summary
        report.append("\n✅ VALIDATION SUMMARY:")
        report.append("-" * 80)

        passed = sum(1 for v in self.validation_results.values() if v['status'] == 'PASSED')
        warnings = sum(1 for v in self.validation_results.values() if v['status'] == 'WARNING')
        empty = sum(1 for v in self.validation_results.values() if v['status'] == 'EMPTY')

        report.append(f"Passed:   {passed}")
        report.append(f"Warnings: {warnings}")
        report.append(f"Empty:    {empty}")

        # Datasets with issues
        if warnings > 0:
            report.append("\n⚠️  DATASETS WITH ISSUES:")
            report.append("-" * 80)
            for name, result in self.validation_results.items():
                if result['status'] == 'WARNING':
                    report.append(f"\n{name}:")
                    for issue in result['issues']:
                        report.append(f"  - {issue}")

        # Date coverage
        report.append("\n📅 DATE COVERAGE:")
        report.append("-" * 80)
        for name, df in self.data.items():
            if not df.empty and 'date' in df.columns:
                start = df['date'].min().strftime('%Y-%m-%d')
                end = df['date'].max().strftime('%Y-%m-%d')
                days = (df['date'].max() - df['date'].min()).days
                report.append(f"{name:25s} : {start} to {end} ({days:,} days)")

        report.append("\n" + "=" * 80)

        return "\n".join(report)

    def save_to_csv(self, output_dir: str = None):
        """Save all datasets to CSV for easy inspection"""
        if output_dir is None:
            output_dir = self.base_path / "processed"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True, parents=True)

        print(f"\n💾 Saving processed data to {output_dir}...")

        for name, df in self.data.items():
            if not df.empty:
                filepath = output_dir / f"{name}.csv"
                df.to_csv(filepath, index=False)
                print(f"  ✓ Saved {name}.csv")

        print(f"\n✅ Saved {len(self.data)} files to {output_dir}")


def main():
    """Main execution function"""
    # Initialize loader
    loader = BloombergDataLoader()

    # Load all data
    data = loader.load_all_data()

    # Validate data
    validation = loader.validate_data()

    # Calculate correlations
    correlations = loader.calculate_correlations()

    # Generate summary report
    report = loader.generate_summary_report()
    print(report)

    # Save processed data
    loader.save_to_csv()

    # Save validation results
    output_dir = loader.base_path / "processed"
    output_dir.mkdir(exist_ok=True, parents=True)

    with open(output_dir / "validation_results.json", 'w') as f:
        json.dump(loader.validation_results, f, indent=2)
    print(f"\n💾 Saved validation_results.json")

    if not correlations.empty:
        correlations.to_csv(output_dir / "correlation_matrix.csv")
        print(f"💾 Saved correlation_matrix.csv")

    print("\n" + "=" * 80)
    print("✅ DATA LOAD AND VALIDATION COMPLETE!")
    print("=" * 80)

    return loader


if __name__ == "__main__":
    loader = main()
