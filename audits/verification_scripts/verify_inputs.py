#!/usr/bin/env python3
"""
Input Data Verification Script
===============================

Compares model inputs against source data collected in CSV templates.
Generates variance report and flags items requiring review.

Usage:
    python verify_inputs.py

Output:
    - Console report with pass/fail status
    - CSV export: ../results/input_verification_report.csv
    - Summary statistics
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add parent directory to path to import model
sys.path.append(str(Path(__file__).parent.parent.parent))

from price_volume_model import (
    get_segment_configs, BENCHMARK_PRICES_2023, Segment,
    get_capital_projects
)


class InputVerifier:
    """Verify model inputs against source data"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data_collection"
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(exist_ok=True)

        self.issues = []
        self.passes = []

    def verify_segment_data(self):
        """Verify segment volumes, prices, and parameters"""
        print("\n" + "=" * 80)
        print("VERIFYING SEGMENT DATA (USS 2023 Actuals)")
        print("=" * 80)

        csv_path = self.data_dir / "uss_2023_data.csv"

        if not csv_path.exists():
            print(f"⚠ WARNING: {csv_path} not found. Please fill in source data.")
            return

        # Read CSV (skip comment lines)
        df = pd.read_csv(csv_path, comment='#')

        # Filter out rows with no source value
        df_filled = df[df['Source_Value'].notna()]

        if len(df_filled) == 0:
            print("⚠ WARNING: No source data filled in. Please complete uss_2023_data.csv")
            return

        print(f"\nFound {len(df_filled)} data points with source values.")
        print("-" * 80)

        # Verify each filled row
        for _, row in df_filled.iterrows():
            metric = row['Metric']
            segment = row['Segment']
            model_val = row['Model_Value']
            source_val = row['Source_Value']

            # Parse values (handle percentages)
            if isinstance(model_val, str) and '%' in model_val:
                model_val = float(model_val.strip('%')) / 100
            if isinstance(source_val, str) and '%' in source_val:
                source_val = float(source_val.strip('%')) / 100

            model_val = float(model_val)
            source_val = float(source_val)

            # Calculate variance
            variance = source_val - model_val
            variance_pct = (variance / model_val * 100) if model_val != 0 else 0

            # Determine status
            if abs(variance_pct) < 2:
                status = "✓ OK"
                self.passes.append({
                    'Category': 'Segment Data',
                    'Item': f"{segment} - {metric}",
                    'Variance': variance_pct
                })
            elif abs(variance_pct) < 5:
                status = "⚠ REVIEW"
                self.issues.append({
                    'Severity': 'Medium',
                    'Category': 'Segment Data',
                    'Item': f"{segment} - {metric}",
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })
            else:
                status = "✗ FLAG"
                self.issues.append({
                    'Severity': 'High',
                    'Category': 'Segment Data',
                    'Item': f"{segment} - {metric}",
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })

            print(f"{status} {segment:<15} {metric:<25} Model: {model_val:>10,.0f}  Source: {source_val:>10,.0f}  Var: {variance_pct:>6.1f}%")

    def verify_steel_prices(self):
        """Verify steel price benchmarks"""
        print("\n" + "=" * 80)
        print("VERIFYING STEEL PRICE BENCHMARKS (2023)")
        print("=" * 80)

        csv_path = self.data_dir / "steel_prices_2023.csv"

        if not csv_path.exists():
            print(f"⚠ WARNING: {csv_path} not found. Please fill in source data.")
            return

        df = pd.read_csv(csv_path, comment='#')
        df_filled = df[df['Source_Value'].notna()]

        if len(df_filled) == 0:
            print("⚠ WARNING: No source data filled in. Please complete steel_prices_2023.csv")
            return

        print(f"\nFound {len(df_filled)} benchmarks with source values.")
        print("-" * 80)

        for _, row in df_filled.iterrows():
            benchmark = row['Benchmark']
            model_val = float(row['Model_Value_USD_per_ton'])
            source_val = float(row['Source_Value'])

            variance = source_val - model_val
            variance_pct = (variance / model_val * 100)

            # Steel prices are volatile, allow larger variance (< 10%)
            if abs(variance_pct) < 5:
                status = "✓ OK"
                self.passes.append({
                    'Category': 'Steel Prices',
                    'Item': benchmark,
                    'Variance': variance_pct
                })
            elif abs(variance_pct) < 10:
                status = "⚠ REVIEW"
                self.issues.append({
                    'Severity': 'Medium',
                    'Category': 'Steel Prices',
                    'Item': benchmark,
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })
            else:
                status = "✗ FLAG"
                self.issues.append({
                    'Severity': 'High',
                    'Category': 'Steel Prices',
                    'Item': benchmark,
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })

            print(f"{status} {benchmark:<20} Model: ${model_val:>6,.0f}/ton  Source: ${source_val:>6,.0f}/ton  Var: {variance_pct:>6.1f}%")

    def verify_balance_sheet(self):
        """Verify balance sheet items"""
        print("\n" + "=" * 80)
        print("VERIFYING BALANCE SHEET ITEMS (Dec 31, 2023)")
        print("=" * 80)

        csv_path = self.data_dir / "balance_sheet_items.csv"

        if not csv_path.exists():
            print(f"⚠ WARNING: {csv_path} not found. Please fill in source data.")
            return

        df = pd.read_csv(csv_path, comment='#')
        df_filled = df[df['Source_Value'].notna()]

        if len(df_filled) == 0:
            print("⚠ WARNING: No source data filled in. Please complete balance_sheet_items.csv")
            return

        print(f"\nFound {len(df_filled)} items with source values.")
        print("-" * 80)

        for _, row in df_filled.iterrows():
            item = row['Item']
            model_val = float(row['Model_Value_Millions'])
            source_val = float(row['Source_Value'])

            variance = source_val - model_val
            variance_pct = (variance / model_val * 100) if model_val != 0 else 0

            # Critical items (debt, cash, shares) need tight tolerance (< 1%)
            if item in ['Total_Debt', 'Cash_and_Equivalents', 'Shares_Outstanding']:
                threshold_low, threshold_high = 1, 3
            else:
                threshold_low, threshold_high = 5, 10

            if abs(variance_pct) < threshold_low:
                status = "✓ OK"
                self.passes.append({
                    'Category': 'Balance Sheet',
                    'Item': item,
                    'Variance': variance_pct
                })
            elif abs(variance_pct) < threshold_high:
                status = "⚠ REVIEW"
                self.issues.append({
                    'Severity': 'Medium',
                    'Category': 'Balance Sheet',
                    'Item': item,
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })
            else:
                status = "✗ FLAG"
                self.issues.append({
                    'Severity': 'High',
                    'Category': 'Balance Sheet',
                    'Item': item,
                    'Model': model_val,
                    'Source': source_val,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })

            print(f"{status} {item:<30} Model: ${model_val:>8,.0f}M  Source: ${source_val:>8,.0f}M  Var: {variance_pct:>6.1f}%")

    def verify_capital_projects(self):
        """Verify capital project data"""
        print("\n" + "=" * 80)
        print("VERIFYING CAPITAL PROJECTS (NSA Commitments)")
        print("=" * 80)

        csv_path = self.data_dir / "capital_projects.csv"

        if not csv_path.exists():
            print(f"⚠ WARNING: {csv_path} not found. Please fill in source data.")
            return

        df = pd.read_csv(csv_path, comment='#')
        df_filled = df[df['Source_Total_CapEx_M'].notna()]

        if len(df_filled) == 0:
            print("⚠ WARNING: No source data filled in. Please complete capital_projects.csv")
            return

        print(f"\nFound {len(df_filled)} projects with source values.")
        print("-" * 80)

        total_model_capex = 0
        total_source_capex = 0

        for _, row in df_filled.iterrows():
            project = row['Project_Name']
            model_capex = float(row['Model_Total_CapEx_M'])
            source_capex = float(row['Source_Total_CapEx_M'])

            total_model_capex += model_capex
            total_source_capex += source_capex

            variance = source_capex - model_capex
            variance_pct = (variance / model_capex * 100)

            # Projects are estimates, allow ±10%
            if abs(variance_pct) < 10:
                status = "✓ OK"
                self.passes.append({
                    'Category': 'Capital Projects',
                    'Item': project,
                    'Variance': variance_pct
                })
            elif abs(variance_pct) < 20:
                status = "⚠ REVIEW"
                self.issues.append({
                    'Severity': 'Medium',
                    'Category': 'Capital Projects',
                    'Item': project,
                    'Model': model_capex,
                    'Source': source_capex,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })
            else:
                status = "✗ FLAG"
                self.issues.append({
                    'Severity': 'High',
                    'Category': 'Capital Projects',
                    'Item': project,
                    'Model': model_capex,
                    'Source': source_capex,
                    'Variance %': variance_pct,
                    'Notes': row.get('Notes', '')
                })

            print(f"{status} {project:<25} Model: ${model_capex:>6,.0f}M  Source: ${source_capex:>6,.0f}M  Var: {variance_pct:>6.1f}%")

        print("\n" + "-" * 80)
        print(f"TOTAL CapEx:                  Model: ${total_model_capex:>6,.0f}M  Source: ${total_source_capex:>6,.0f}M")
        print(f"NSA Commitment Target: $14,000M (may include items not in model)")

    def generate_report(self):
        """Generate summary report"""
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)

        total_checks = len(self.passes) + len(self.issues)
        passed = len(self.passes)
        flagged = len([i for i in self.issues if i['Severity'] == 'High'])
        review = len([i for i in self.issues if i['Severity'] == 'Medium'])

        print(f"\nTotal Checks: {total_checks}")
        if total_checks > 0:
            print(f"Passed: {passed} ({passed/total_checks*100:.1f}%)")
            print(f"Review: {review} ({review/total_checks*100:.1f}%)")
            print(f"Flagged: {flagged} ({flagged/total_checks*100:.1f}%)")
        else:
            print("No checks were performed.")

        if flagged > 0:
            print("\n" + "=" * 80)
            print("FLAGGED ITEMS (Variance > Threshold)")
            print("=" * 80)
            for issue in self.issues:
                if issue['Severity'] == 'High':
                    print(f"\n✗ {issue['Category']}: {issue['Item']}")
                    print(f"  Model: {issue['Model']:,.2f}")
                    print(f"  Source: {issue['Source']:,.2f}")
                    print(f"  Variance: {issue['Variance %']:.1f}%")
                    if issue.get('Notes'):
                        print(f"  Notes: {issue['Notes']}")

        # Export to CSV
        if self.issues:
            issues_df = pd.DataFrame(self.issues)
            output_path = self.results_dir / "input_verification_issues.csv"
            issues_df.to_csv(output_path, index=False)
            print(f"\n✓ Issues exported to: {output_path}")

        # Overall assessment
        print("\n" + "=" * 80)
        print("OVERALL ASSESSMENT")
        print("=" * 80)

        if flagged == 0 and review == 0:
            print("\n✓ PASS - All inputs verified against source data")
        elif flagged == 0:
            print(f"\n⚠ PASS WITH COMMENTS - {review} items require review")
        else:
            print(f"\n✗ ISSUES FOUND - {flagged} items flagged for investigation")

        print()


def main():
    """Run verification"""
    verifier = InputVerifier()

    print("=" * 80)
    print("INPUT DATA VERIFICATION")
    print("=" * 80)
    print("\nThis script compares model inputs against source data collected in CSV templates.")
    print("Ensure you have filled in the following files:")
    print("  - data_collection/uss_2023_data.csv")
    print("  - data_collection/steel_prices_2023.csv")
    print("  - data_collection/balance_sheet_items.csv")
    print("  - data_collection/capital_projects.csv")

    verifier.verify_segment_data()
    verifier.verify_steel_prices()
    verifier.verify_balance_sheet()
    verifier.verify_capital_projects()
    verifier.generate_report()


if __name__ == "__main__":
    main()
