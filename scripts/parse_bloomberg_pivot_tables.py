"""
Custom parser for Bloomberg pivot table exports
Handles non-standard formats: EV forecasts, steel demand/costs, macro aggregates
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class BloombergPivotParser:
    """Parse Bloomberg pivot table exports into usable formats"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            self.base_path = Path(__file__).parent.parent / "market-data" / "exports"
        else:
            self.base_path = Path(base_path)

        self.parsed_data = {}

    def parse_all(self):
        """Parse all pivot table files"""
        print("=" * 80)
        print("BLOOMBERG PIVOT TABLE PARSER")
        print("=" * 80)
        print()

        # Parse each file type
        self.parse_ev_forecast()
        self.parse_steel_demand()
        self.parse_steel_costs()
        self.parse_macro_aggregate()

        print("\n" + "=" * 80)
        print(f"✅ Parsing complete! Parsed {len(self.parsed_data)} datasets")
        print("=" * 80)

        return self.parsed_data

    def parse_ev_forecast(self):
        """Parse EV production forecast (wide format → long format)"""
        print("\n📊 Parsing EV Forecast...")
        print("-" * 80)

        filepath = self.base_path / "06_synergy_validation" / "bloomberg_ev_forecast_us_annual_2024-2035.xlsx"

        try:
            # Read the Excel file
            df = pd.read_excel(filepath)

            # First column is vehicle type, rest are years
            vehicle_types = df.iloc[:, 0].values
            years = df.columns[1:].astype(int).tolist()

            # Create long format dataframe
            records = []
            for i, vehicle_type in enumerate(vehicle_types):
                for year in years:
                    value = df.loc[i, year]
                    if pd.notna(value):
                        records.append({
                            'year': year,
                            'vehicle_type': vehicle_type,
                            'units': int(value)
                        })

            result = pd.DataFrame(records)
            result = result.sort_values(['year', 'vehicle_type']).reset_index(drop=True)

            # Calculate totals and EV share
            yearly_totals = result.groupby('year')['units'].sum().to_dict()
            result['total_production'] = result['year'].map(yearly_totals)
            result['market_share_pct'] = (result['units'] / result['total_production'] * 100).round(2)

            # Add EV flag
            ev_types = ['BEV', 'PHEV', 'HEV']
            result['is_ev'] = result['vehicle_type'].isin(ev_types)

            self.parsed_data['ev_forecast'] = result

            print(f"  ✓ Parsed {len(result)} records")
            print(f"  ✓ Years: {result['year'].min()} to {result['year'].max()}")
            print(f"  ✓ Vehicle types: {', '.join(result['vehicle_type'].unique())}")

            # Calculate EV penetration
            ev_penetration = result[result['is_ev']].groupby('year')['market_share_pct'].sum()
            print(f"\n  📈 EV Penetration Forecast:")
            for year in [2024, 2026, 2028, 2030]:
                if year in ev_penetration.index:
                    print(f"     {year}: {ev_penetration[year]:.1f}%")

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            self.parsed_data['ev_forecast'] = pd.DataFrame()

    def parse_steel_demand(self):
        """Parse US/EU steel demand data (quarterly)"""
        print("\n📊 Parsing Steel Demand...")
        print("-" * 80)

        filepath = self.base_path / "06_synergy_validation" / "bloomberg_steel_demand_us_eu_2015-2026.xlsx"

        try:
            # Read the full file to inspect structure
            df = pd.read_excel(filepath)

            # Find data sections by looking for ticker/description patterns
            # Row 0: Description, Ticker
            # Subsequent rows have series names and data

            # Extract column headers (quarters/years)
            # Skip first 2 columns (Description, Ticker)
            time_cols = df.columns[2:].tolist()

            # Parse each data row
            records = []
            for idx in range(len(df)):
                description = df.iloc[idx, 0]
                ticker = df.iloc[idx, 1] if pd.notna(df.iloc[idx, 1]) else None

                # Skip header rows and empty rows
                if pd.isna(description) or description in ['Description', 'US Steel Demand', 'EU Steel Demand']:
                    continue

                # Extract time series data
                for col_idx, time_col in enumerate(time_cols):
                    value = df.iloc[idx, col_idx + 2]

                    if pd.notna(value) and str(value).replace('.', '').replace('-', '').isdigit():
                        # Parse time period (e.g., "2024 Q1")
                        time_str = str(time_col)

                        records.append({
                            'series_name': description,
                            'ticker': ticker,
                            'period': time_str,
                            'value': float(value)
                        })

            if records:
                result = pd.DataFrame(records)
                result = result.sort_values(['series_name', 'period']).reset_index(drop=True)

                self.parsed_data['steel_demand'] = result

                print(f"  ✓ Parsed {len(result)} data points")
                print(f"  ✓ Series: {result['series_name'].nunique()} different metrics")
                print(f"  ✓ Periods: {result['period'].nunique()} time periods")

                # Show key series
                print(f"\n  📊 Available Series:")
                for series in result['series_name'].unique()[:10]:
                    count = len(result[result['series_name'] == series])
                    print(f"     - {series}: {count} observations")

            else:
                print("  ⚠️  No data extracted")
                self.parsed_data['steel_demand'] = pd.DataFrame()

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            self.parsed_data['steel_demand'] = pd.DataFrame()

    def parse_steel_costs(self):
        """Parse steel cost/profitability indices"""
        print("\n📊 Parsing Steel Costs...")
        print("-" * 80)

        filepath = self.base_path / "06_synergy_validation" / "bloomberg_steel_costs_us_eu_2015-2026.xlsx"

        try:
            df = pd.read_excel(filepath)

            # Skip header rows with notes
            start_row = 0
            for idx in range(len(df)):
                cell_value = str(df.iloc[idx, 0])
                if 'North America' in cell_value or 'Europe' in cell_value:
                    start_row = idx
                    break

            # Extract time columns (skip first column which is description)
            time_cols = df.columns[1:].tolist()

            # Parse data rows
            records = []
            current_region = None

            for idx in range(start_row, len(df)):
                description = str(df.iloc[idx, 0])

                # Track region
                if 'North America' in description:
                    current_region = 'North America'
                    continue
                elif 'Europe' in description:
                    current_region = 'Europe'
                    continue
                elif pd.isna(description) or description == 'nan':
                    continue

                # Extract time series
                for col_idx, time_col in enumerate(time_cols):
                    value = df.iloc[idx, col_idx + 1]

                    if pd.notna(value) and str(value).replace('.', '').replace('-', '').isdigit():
                        records.append({
                            'region': current_region,
                            'metric': description,
                            'period': str(time_col),
                            'value': float(value)
                        })

            if records:
                result = pd.DataFrame(records)
                result = result[result['region'].notna()]  # Remove rows without region
                result = result.sort_values(['region', 'metric', 'period']).reset_index(drop=True)

                self.parsed_data['steel_costs'] = result

                print(f"  ✓ Parsed {len(result)} data points")
                print(f"  ✓ Regions: {', '.join(result['region'].unique())}")
                print(f"  ✓ Metrics: {result['metric'].nunique()} different cost indices")

                # Show key metrics by region
                print(f"\n  📊 Available Metrics:")
                for region in result['region'].unique():
                    region_data = result[result['region'] == region]
                    print(f"\n     {region}:")
                    for metric in region_data['metric'].unique()[:5]:
                        count = len(region_data[region_data['metric'] == metric])
                        print(f"       - {metric}: {count} observations")

            else:
                print("  ⚠️  No data extracted")
                self.parsed_data['steel_costs'] = pd.DataFrame()

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            self.parsed_data['steel_costs'] = pd.DataFrame()

    def parse_macro_aggregate(self):
        """Parse macro aggregate time series data"""
        print("\n📊 Parsing Macro Aggregate...")
        print("-" * 80)

        filepath = self.base_path / "07_macro" / "bloomberg_macro_aggregate_us_2015-2026.xlsx"

        try:
            df = pd.read_excel(filepath)

            # First column is description, rest are time periods
            time_cols = df.columns[1:].tolist()

            # Parse each series
            records = []
            current_category = None

            for idx in range(len(df)):
                description = str(df.iloc[idx, 0])

                # Track categories
                if pd.isna(description) or description == 'nan':
                    continue
                if description == 'Description':
                    continue

                # Check if it's a category header (all caps or ends with dash)
                if description.isupper() or description.endswith('-'):
                    current_category = description
                    continue

                # Extract time series data
                for col_idx, time_col in enumerate(time_cols):
                    value = df.iloc[idx, col_idx + 1]

                    if pd.notna(value) and str(value).replace('.', '').replace('-', '').isdigit():
                        records.append({
                            'category': current_category,
                            'series_name': description,
                            'period': str(time_col),
                            'value': float(value)
                        })

            if records:
                result = pd.DataFrame(records)
                result = result.sort_values(['series_name', 'period']).reset_index(drop=True)

                self.parsed_data['macro_aggregate'] = result

                print(f"  ✓ Parsed {len(result)} data points")
                print(f"  ✓ Series: {result['series_name'].nunique()} different metrics")

                # Show key series
                print(f"\n  📊 Available Series:")
                for series in result['series_name'].unique()[:10]:
                    count = len(result[result['series_name'] == series])
                    latest = result[result['series_name'] == series]['value'].iloc[-1]
                    print(f"     - {series}: {count} obs, latest={latest:.2f}")

            else:
                print("  ⚠️  No data extracted")
                self.parsed_data['macro_aggregate'] = pd.DataFrame()

        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
            self.parsed_data['macro_aggregate'] = pd.DataFrame()

    def save_to_csv(self, output_dir: str = None):
        """Save parsed data to CSV files"""
        if output_dir is None:
            output_dir = self.base_path / "processed"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True, parents=True)

        print(f"\n💾 Saving parsed data to {output_dir}...")

        for name, df in self.parsed_data.items():
            if not df.empty:
                filepath = output_dir / f"{name}.csv"
                df.to_csv(filepath, index=False)
                print(f"  ✓ Saved {name}.csv ({len(df)} rows)")

        print(f"\n✅ Saved {len(self.parsed_data)} parsed files")

    def generate_summary_report(self) -> str:
        """Generate summary report of parsed data"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("PARSED DATA SUMMARY REPORT")
        report.append("=" * 80)
        report.append("")

        for name, df in self.parsed_data.items():
            if df.empty:
                continue

            report.append(f"\n📊 {name.upper().replace('_', ' ')}")
            report.append("-" * 80)
            report.append(f"Total records: {len(df):,}")
            report.append(f"Columns: {', '.join(df.columns)}")

            if name == 'ev_forecast':
                # EV-specific summary
                total_2030 = df[df['year'] == 2030]['units'].sum()
                ev_2030 = df[(df['year'] == 2030) & (df['is_ev'])]['units'].sum()
                ev_share = ev_2030 / total_2030 * 100 if total_2030 > 0 else 0

                report.append(f"\n2030 Forecast:")
                report.append(f"  Total Production: {total_2030:,} units")
                report.append(f"  EV Production: {ev_2030:,} units")
                report.append(f"  EV Share: {ev_share:.1f}%")

            elif name == 'steel_demand':
                # Steel demand summary
                series_count = df['series_name'].nunique()
                report.append(f"\nAvailable series: {series_count}")

            elif name == 'steel_costs':
                # Steel costs summary
                regions = df['region'].unique()
                report.append(f"\nRegions: {', '.join(regions)}")

        report.append("\n" + "=" * 80)
        return "\n".join(report)


def main():
    """Main execution"""
    parser = BloombergPivotParser()

    # Parse all files
    data = parser.parse_all()

    # Save to CSV
    parser.save_to_csv()

    # Generate report
    report = parser.generate_summary_report()
    print(report)

    print("\n" + "=" * 80)
    print("✅ PIVOT TABLE PARSING COMPLETE!")
    print("=" * 80)

    return parser


if __name__ == "__main__":
    parser = main()
