#!/usr/bin/env python3
"""
Model Audit Test Suite: USS / Nippon Steel DCF Model
=====================================================

Automated testing framework to validate model integrity, accuracy, and reliability.
Implements tests from MODEL_AUDIT_PLAN.md

Run with: python model_audit.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import sys
from pathlib import Path

# Add parent directory to path to import model
sys.path.insert(0, str(Path(__file__).parent.parent))

from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, ScenarioType,
    get_segment_configs, BENCHMARK_PRICES_2023, Segment,
    get_capital_projects
)


class AuditTest:
    """Single audit test"""
    def __init__(self, test_id: str, description: str, category: str):
        self.test_id = test_id
        self.description = description
        self.category = category
        self.passed = None
        self.actual_value = None
        self.expected_value = None
        self.notes = ""


class ModelAuditor:
    """Main audit framework"""

    def __init__(self):
        self.tests: List[AuditTest] = []
        self.base_model = None
        self.base_analysis = None

    def run_all_tests(self):
        """Execute all audit tests"""
        print("=" * 80)
        print("MODEL AUDIT TEST SUITE - USS / NIPPON STEEL DCF MODEL")
        print("=" * 80)
        print()

        # Initialize base case model
        print("Initializing base case model...")
        base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]
        self.base_model = PriceVolumeModel(base_scenario)
        self.base_analysis = self.base_model.run_full_analysis()
        print("✓ Model initialized\n")

        # Run test categories
        self._test_input_validation()
        self._test_calculation_verification()
        self._test_consolidation_integrity()
        self._test_logic_checks()
        self._test_sensitivity_analysis()
        self._test_boundary_conditions()
        self._test_financing_impact()
        self._test_scenario_consistency()

        # Generate report
        self._generate_report()

    def _test_input_validation(self):
        """Category 1: Input Validation & Data Integrity"""
        print("\n" + "=" * 80)
        print("CATEGORY 1: INPUT VALIDATION & DATA INTEGRITY")
        print("=" * 80)

        # Test IV-11: Flat-Rolled premium calibration
        test = AuditTest("IV-11", "Flat-Rolled premium calibration", "Input Validation")
        segments = get_segment_configs()
        fr_seg = segments[Segment.FLAT_ROLLED]
        calculated_premium = (fr_seg.base_price_2023 / BENCHMARK_PRICES_2023['hrc_us']) - 1
        test.expected_value = fr_seg.price_premium_to_benchmark
        test.actual_value = calculated_premium
        test.passed = abs(test.expected_value - test.actual_value) < 0.001
        test.notes = f"Expected: {test.expected_value:.1%}, Actual: {test.actual_value:.1%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test IV-12: Mini Mill premium calibration
        test = AuditTest("IV-12", "Mini Mill premium calibration", "Input Validation")
        mm_seg = segments[Segment.MINI_MILL]
        calculated_premium = (mm_seg.base_price_2023 / BENCHMARK_PRICES_2023['hrc_us']) - 1
        test.expected_value = mm_seg.price_premium_to_benchmark
        test.actual_value = calculated_premium
        test.passed = abs(test.expected_value - test.actual_value) < 0.001
        test.notes = f"Expected: {test.expected_value:.1%}, Actual: {test.actual_value:.1%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test IV-13: USSE premium calibration
        test = AuditTest("IV-13", "USSE premium calibration", "Input Validation")
        usse_seg = segments[Segment.USSE]
        calculated_premium = (usse_seg.base_price_2023 / BENCHMARK_PRICES_2023['hrc_eu']) - 1
        test.expected_value = usse_seg.price_premium_to_benchmark
        test.actual_value = calculated_premium
        test.passed = abs(test.expected_value - test.actual_value) < 0.001
        test.notes = f"Expected: {test.expected_value:.1%}, Actual: {test.actual_value:.1%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test IV-14: Tubular premium calibration
        test = AuditTest("IV-14", "Tubular premium calibration", "Input Validation")
        tub_seg = segments[Segment.TUBULAR]
        calculated_premium = (tub_seg.base_price_2023 / BENCHMARK_PRICES_2023['octg']) - 1
        test.expected_value = tub_seg.price_premium_to_benchmark
        test.actual_value = calculated_premium
        test.passed = abs(test.expected_value - test.actual_value) < 0.001
        test.notes = f"Expected: {test.expected_value:.1%}, Actual: {test.actual_value:.1%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_calculation_verification(self):
        """Category 2: Calculation Verification"""
        print("\n" + "=" * 80)
        print("CATEGORY 2: CALCULATION VERIFICATION")
        print("=" * 80)

        df = self.base_analysis['consolidated']

        # Test CV-01: Revenue = Volume × Price (2024)
        test = AuditTest("CV-01", "Revenue = Volume × Price (2024)", "Calculation")
        year_2024 = df[df['Year'] == 2024].iloc[0]
        calculated_revenue = (year_2024['Total_Volume_000tons'] * year_2024['Avg_Price_per_ton']) / 1000
        test.expected_value = year_2024['Revenue']
        test.actual_value = calculated_revenue
        test.passed = abs(test.expected_value - test.actual_value) < 1.0  # Within $1M
        test.notes = f"Expected: ${test.expected_value:,.0f}M, Calculated: ${test.actual_value:,.0f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-03: NOPAT = EBIT × (1 - 16.9%)
        test = AuditTest("CV-03", "NOPAT = EBIT × (1 - 16.9%)", "Calculation")
        ebit = year_2024['Total_EBITDA'] - year_2024['DA']
        expected_nopat = ebit * (1 - 0.169)
        test.expected_value = expected_nopat
        test.actual_value = year_2024['NOPAT']
        test.passed = abs(test.expected_value - test.actual_value) < 0.1
        test.notes = f"EBIT: ${ebit:,.0f}M → NOPAT: ${test.actual_value:,.0f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-05: FCF = Gross CF - CapEx + ΔWC
        test = AuditTest("CV-05", "FCF = Gross CF - CapEx + ΔWC", "Calculation")
        expected_fcf = year_2024['Gross_CF'] - year_2024['Total_CapEx'] + year_2024['Delta_WC']
        test.expected_value = expected_fcf
        test.actual_value = year_2024['FCF']
        test.passed = abs(test.expected_value - test.actual_value) < 0.1
        test.notes = f"Expected: ${test.expected_value:,.0f}M, Actual: ${test.actual_value:,.0f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-07: Gordon Growth terminal value constraint (g < WACC)
        test = AuditTest("CV-07", "Terminal growth < WACC", "Calculation")
        scenario = self.base_analysis['scenario']
        test.expected_value = True
        test.actual_value = scenario.terminal_growth < scenario.uss_wacc
        test.passed = test.actual_value
        test.notes = f"g={scenario.terminal_growth:.1%} < WACC={scenario.uss_wacc:.1%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-10: IRP WACC conversion
        test = AuditTest("CV-10", "IRP WACC conversion formula", "Calculation")
        jpy_wacc = self.base_analysis['jpy_wacc']
        us_10yr = scenario.us_10yr
        jp_10yr = scenario.japan_10yr
        manual_usd_wacc = (1 + jpy_wacc) * (1 + us_10yr) / (1 + jp_10yr) - 1
        test.expected_value = manual_usd_wacc
        test.actual_value = self.base_analysis['usd_wacc']
        test.passed = abs(test.expected_value - test.actual_value) < 0.0001
        test.notes = f"JPY {jpy_wacc:.2%} → USD {test.actual_value:.2%}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_consolidation_integrity(self):
        """Category 2.2: Consolidation Integrity"""
        print("\n" + "=" * 80)
        print("CATEGORY 2.2: CONSOLIDATION INTEGRITY")
        print("=" * 80)

        consolidated = self.base_analysis['consolidated']
        segment_dfs = self.base_analysis['segment_dfs']

        # Test CV-11: Sum of segment revenues = consolidated revenue
        test = AuditTest("CV-11", "Segment revenues sum to consolidated (all years)", "Consolidation")
        all_years_pass = True
        max_error = 0
        for year in range(2024, 2034):
            seg_total = sum(df[df['Year'] == year]['Revenue'].values[0] for df in segment_dfs.values())
            cons_total = consolidated[consolidated['Year'] == year]['Revenue'].values[0]
            error = abs(seg_total - cons_total)
            max_error = max(max_error, error)
            if error > 0.01:  # More than 1 cent
                all_years_pass = False
        test.passed = all_years_pass
        test.notes = f"Max error across all years: ${max_error:,.2f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-12: Sum of segment EBITDA = consolidated EBITDA
        test = AuditTest("CV-12", "Segment EBITDA sum to consolidated (all years)", "Consolidation")
        all_years_pass = True
        max_error = 0
        for year in range(2024, 2034):
            seg_total = sum(df[df['Year'] == year]['Total_EBITDA'].values[0] for df in segment_dfs.values())
            cons_total = consolidated[consolidated['Year'] == year]['Total_EBITDA'].values[0]
            error = abs(seg_total - cons_total)
            max_error = max(max_error, error)
            if error > 0.01:
                all_years_pass = False
        test.passed = all_years_pass
        test.notes = f"Max error across all years: ${max_error:,.2f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test CV-14: Sum of segment FCF = consolidated FCF
        test = AuditTest("CV-14", "Segment FCF sum to consolidated (all years)", "Consolidation")
        all_years_pass = True
        max_error = 0
        for year in range(2024, 2034):
            seg_total = sum(df[df['Year'] == year]['FCF'].values[0] for df in segment_dfs.values())
            cons_total = consolidated[consolidated['Year'] == year]['FCF'].values[0]
            error = abs(seg_total - cons_total)
            max_error = max(max_error, error)
            if error > 0.01:
                all_years_pass = False
        test.passed = all_years_pass
        test.notes = f"Max error across all years: ${max_error:,.2f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_logic_checks(self):
        """Category 3: Logic & Reasonableness Checks"""
        print("\n" + "=" * 80)
        print("CATEGORY 3: LOGIC & REASONABLENESS CHECKS")
        print("=" * 80)

        df = self.base_analysis['consolidated']

        # Test LC-02: Higher WACC → lower valuation
        test = AuditTest("LC-02", "Higher WACC → lower valuation", "Logic")
        val_low_wacc = self.base_model.calculate_dcf(df, 0.08)
        val_high_wacc = self.base_model.calculate_dcf(df, 0.14)
        test.passed = val_low_wacc['share_price'] > val_high_wacc['share_price']
        test.notes = f"8% WACC: ${val_low_wacc['share_price']:.2f}, 14% WACC: ${val_high_wacc['share_price']:.2f}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test LC-09: EBITDA margin in industry range
        test = AuditTest("LC-09", "Avg EBITDA margin 10-20% (industry range)", "Logic")
        avg_margin = df['EBITDA_Margin'].mean()
        test.actual_value = avg_margin
        test.passed = 0.10 <= avg_margin <= 0.20
        test.notes = f"Average margin: {avg_margin*100:.1f}% (industry: 10-20%)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test LC-10: FCF/EBITDA conversion 40-60%
        test = AuditTest("LC-10", "FCF/EBITDA conversion 40-60%", "Logic")
        fcf_total = df['FCF'].sum()
        ebitda_total = df['Total_EBITDA'].sum()
        conversion = fcf_total / ebitda_total
        test.actual_value = conversion
        test.passed = 0.40 <= conversion <= 0.60
        test.notes = f"Conversion: {conversion*100:.1f}% (industry: 40-60%)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test LC-07: Mini Mill margins > Flat-Rolled
        test = AuditTest("LC-07", "Mini Mill margins > Flat-Rolled margins", "Logic")
        seg_dfs = self.base_analysis['segment_dfs']
        mm_margin = seg_dfs['Mini Mill']['EBITDA_Margin'].mean()
        fr_margin = seg_dfs['Flat-Rolled']['EBITDA_Margin'].mean()
        test.passed = mm_margin > fr_margin
        test.notes = f"Mini Mill: {mm_margin*100:.1f}%, Flat-Rolled: {fr_margin*100:.1f}%"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_sensitivity_analysis(self):
        """Category 4: Sensitivity & Stress Testing"""
        print("\n" + "=" * 80)
        print("CATEGORY 4: SENSITIVITY & STRESS TESTING")
        print("=" * 80)

        # Test ST-02: Volume sensitivity is monotonic
        test = AuditTest("ST-02", "Volume changes have linear impact on FCF", "Sensitivity")
        base_fcf = self.base_analysis['consolidated']['FCF'].sum()

        # Test 10% volume reduction
        from price_volume_model import VolumeScenario, ModelScenario
        scenario = self.base_analysis['scenario']
        vol_down = VolumeScenario(
            name="Test", description="Test",
            flat_rolled_volume_factor=0.9,
            mini_mill_volume_factor=0.9,
            usse_volume_factor=0.9,
            tubular_volume_factor=0.9,
            flat_rolled_growth_adj=0, mini_mill_growth_adj=0,
            usse_growth_adj=0, tubular_growth_adj=0
        )
        test_scenario = ModelScenario(
            name="Test", scenario_type=ScenarioType.CUSTOM, description="Test",
            price_scenario=scenario.price_scenario, volume_scenario=vol_down,
            uss_wacc=scenario.uss_wacc, terminal_growth=scenario.terminal_growth,
            exit_multiple=scenario.exit_multiple, us_10yr=scenario.us_10yr,
            japan_10yr=scenario.japan_10yr, nippon_cost_of_equity=scenario.nippon_cost_of_equity,
            nippon_cost_of_debt=scenario.nippon_cost_of_debt, nippon_debt_ratio=scenario.nippon_debt_ratio,
            nippon_tax_rate=scenario.nippon_tax_rate, include_projects=scenario.include_projects
        )
        test_model = PriceVolumeModel(test_scenario)
        test_consolidated, _ = test_model.build_consolidated()
        low_vol_fcf = test_consolidated['FCF'].sum()

        test.passed = low_vol_fcf < base_fcf
        test.notes = f"Base FCF: ${base_fcf:,.0f}M, -10% vol: ${low_vol_fcf:,.0f}M ({(low_vol_fcf/base_fcf-1)*100:.1f}%)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_boundary_conditions(self):
        """Category 4.3: Boundary Testing"""
        print("\n" + "=" * 80)
        print("CATEGORY 4.3: BOUNDARY CONDITIONS")
        print("=" * 80)

        # Test ST-20: Negative margin floors at 2%
        test = AuditTest("ST-20", "Negative margins floor at 2%", "Boundary")
        segments = get_segment_configs()
        fr_seg = segments[Segment.FLAT_ROLLED]
        # Test with very low price (-50%)
        low_price = fr_seg.base_price_2023 * 0.5
        margin = self.base_model.calculate_segment_margin(Segment.FLAT_ROLLED, low_price)
        test.passed = margin >= 0.02
        test.notes = f"Margin at ${low_price:.0f}/ton: {margin*100:.1f}% (floor: 2%)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test ST-19: High margin caps at 30%
        test = AuditTest("ST-19", "High margins cap at 30%", "Boundary")
        # Test with very high price (+100%)
        high_price = fr_seg.base_price_2023 * 2.0
        margin = self.base_model.calculate_segment_margin(Segment.FLAT_ROLLED, high_price)
        test.passed = margin <= 0.30
        test.notes = f"Margin at ${high_price:.0f}/ton: {margin*100:.1f}% (cap: 30%)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_financing_impact(self):
        """Category 5: Financing Impact Validation"""
        print("\n" + "=" * 80)
        print("CATEGORY 5: FINANCING IMPACT VALIDATION")
        print("=" * 80)

        # Test FI-01: BR2-only scenario has zero financing impact
        test = AuditTest("FI-01", "BR2-only scenario has zero financing impact", "Financing")
        base_financing = self.base_analysis['financing_impact']
        test.passed = base_financing['financing_gap'] == 0
        test.notes = f"Financing gap: ${base_financing['financing_gap']:,.0f}M (expected: $0M)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test FI-02: NSA scenario triggers financing
        test = AuditTest("FI-02", "NSA scenario triggers financing impact", "Financing")
        nsa_scenario = get_scenario_presets()[ScenarioType.NIPPON_COMMITMENTS]
        nsa_model = PriceVolumeModel(nsa_scenario)
        nsa_analysis = nsa_model.run_full_analysis()
        nsa_financing = nsa_analysis['financing_impact']
        test.passed = nsa_financing['financing_gap'] > 0
        test.notes = f"NSA financing gap: ${nsa_financing['financing_gap']:,.0f}M"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

        # Test FI-08: Nippon valuation excludes financing impact
        test = AuditTest("FI-08", "Nippon valuation excludes financing impact", "Financing")
        nippon_val = nsa_analysis['val_nippon']
        test.passed = nippon_val['financing_impact'] is None
        test.notes = "Nippon view has no financing penalty (deep balance sheet)"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _test_scenario_consistency(self):
        """Category 3.3: Cross-Scenario Consistency"""
        print("\n" + "=" * 80)
        print("CATEGORY 3.3: CROSS-SCENARIO CONSISTENCY")
        print("=" * 80)

        # Test LC-15: Conservative < Base < Management
        test = AuditTest("LC-15", "Scenario valuations rank correctly", "Scenario")

        from price_volume_model import compare_scenarios
        comparison = compare_scenarios()

        conservative_val = comparison[comparison['Scenario'] == 'Conservative']['Value to Nippon ($/sh)'].values[0]
        base_val = comparison[comparison['Scenario'] == 'Base Case']['Value to Nippon ($/sh)'].values[0]
        management_val = comparison[comparison['Scenario'] == 'Management']['Value to Nippon ($/sh)'].values[0]

        test.passed = conservative_val < base_val < management_val
        test.notes = f"Conservative: ${conservative_val:.2f} < Base: ${base_val:.2f} < Management: ${management_val:.2f}"
        self.tests.append(test)
        print(f"  {test.test_id}: {test.description}")
        print(f"    {'✓ PASS' if test.passed else '✗ FAIL'} - {test.notes}")

    def _generate_report(self):
        """Generate final audit report"""
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)

        total_tests = len(self.tests)
        passed_tests = sum(1 for t in self.tests if t.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\nTotal Tests Executed: {total_tests}")
        print(f"Passed: {passed_tests} ({pass_rate:.1f}%)")
        print(f"Failed: {failed_tests}")
        print()

        # Category breakdown
        categories = {}
        for test in self.tests:
            if test.category not in categories:
                categories[test.category] = {'total': 0, 'passed': 0}
            categories[test.category]['total'] += 1
            if test.passed:
                categories[test.category]['passed'] += 1

        print("Breakdown by Category:")
        print("-" * 60)
        for category, stats in categories.items():
            rate = stats['passed'] / stats['total'] * 100
            print(f"  {category:<25} {stats['passed']:>3}/{stats['total']:<3} ({rate:>5.1f}%)")

        # Failed tests detail
        if failed_tests > 0:
            print("\n" + "=" * 80)
            print("FAILED TESTS DETAIL")
            print("=" * 80)
            for test in self.tests:
                if not test.passed:
                    print(f"\n✗ {test.test_id}: {test.description}")
                    print(f"  Category: {test.category}")
                    print(f"  Notes: {test.notes}")

        # Overall assessment
        print("\n" + "=" * 80)
        print("OVERALL ASSESSMENT")
        print("=" * 80)

        if pass_rate == 100:
            status = "✓ PASS - All tests passed"
        elif pass_rate >= 90:
            status = "⚠ PASS WITH COMMENTS - Minor issues identified"
        elif pass_rate >= 70:
            status = "⚠ REVIEW REQUIRED - Significant issues found"
        else:
            status = "✗ FAIL - Major issues require resolution"

        print(f"\n{status}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print()

        # Export results to CSV
        results_df = pd.DataFrame([{
            'Test ID': t.test_id,
            'Description': t.description,
            'Category': t.category,
            'Result': 'PASS' if t.passed else 'FAIL',
            'Notes': t.notes
        } for t in self.tests])

        results_df.to_csv('audit_results.csv', index=False)
        print("Results exported to: audit_results.csv")
        print()


def main():
    """Run the audit"""
    auditor = ModelAuditor()
    auditor.run_all_tests()


if __name__ == "__main__":
    main()
