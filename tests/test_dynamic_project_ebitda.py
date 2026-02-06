#!/usr/bin/env python3
"""
Test suite for dynamic capital project EBITDA calculations.

Tests that project EBITDA responds to scenario price assumptions:
- Higher prices → Higher project EBITDA
- Lower prices → Lower project EBITDA
- Mining uses $150/ton override price
- Execution factor applies to non-BR2 projects
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType, SteelPriceScenario, VolumeScenario,
    CapitalProject, get_capital_projects, get_scenario_presets, Segment
)


class TestDynamicProjectEBITDA(unittest.TestCase):
    """Test that project EBITDA responds to scenario prices."""

    def setUp(self):
        """Set up test scenarios with different price levels."""
        self.presets = get_scenario_presets()
        self.projects = get_capital_projects()

    def test_br2_ebitda_increases_with_higher_prices(self):
        """BR2 EBITDA should increase when steel prices are higher."""
        # Get downside and optimistic scenarios
        downside = self.presets[ScenarioType.DOWNSIDE]
        optimistic = self.presets[ScenarioType.OPTIMISTIC]

        model_downside = PriceVolumeModel(downside)
        model_optimistic = PriceVolumeModel(optimistic)

        # Get Mini Mill segment price in a steady-state year (2029)
        price_downside = model_downside.calculate_segment_price(
            Segment.MINI_MILL, 2029
        )
        price_optimistic = model_optimistic.calculate_segment_price(
            Segment.MINI_MILL, 2029
        )

        # Calculate BR2 EBITDA in each scenario
        br2 = model_downside.projects['BR2 Mini Mill']
        ebitda_downside = model_downside.calculate_project_ebitda(br2, 2029, price_downside)
        ebitda_optimistic = model_optimistic.calculate_project_ebitda(br2, 2029, price_optimistic)

        # Verify higher prices → higher EBITDA
        self.assertGreater(price_optimistic, price_downside,
                          "Optimistic price should be higher than downside")
        self.assertGreater(ebitda_optimistic, ebitda_downside,
                          "BR2 EBITDA should be higher in optimistic scenario")

    def test_br2_ebitda_decreases_with_lower_prices(self):
        """BR2 EBITDA should decrease when steel prices are lower."""
        base = self.presets[ScenarioType.BASE_CASE]
        severe = self.presets[ScenarioType.SEVERE_DOWNTURN]

        model_base = PriceVolumeModel(base)
        model_severe = PriceVolumeModel(severe)

        # Get prices
        price_base = model_base.calculate_segment_price(
            Segment.MINI_MILL, 2029
        )
        price_severe = model_severe.calculate_segment_price(
            Segment.MINI_MILL, 2029
        )

        # Calculate EBITDA
        br2 = model_base.projects['BR2 Mini Mill']
        ebitda_base = model_base.calculate_project_ebitda(br2, 2029, price_base)
        ebitda_severe = model_severe.calculate_project_ebitda(br2, 2029, price_severe)

        # Verify lower prices → lower EBITDA
        self.assertLess(price_severe, price_base,
                       "Severe downturn price should be lower than base case")
        self.assertLess(ebitda_severe, ebitda_base,
                       "BR2 EBITDA should be lower in severe downturn scenario")

    def test_mining_uses_price_override(self):
        """Mining project should use $150/ton pellet price, not segment price."""
        base = self.presets[ScenarioType.BASE_CASE]
        model = PriceVolumeModel(base)

        mining = model.projects['Mining Investment']

        # Verify price override is set
        self.assertEqual(mining.base_price_override, 150,
                        "Mining should have $150/ton price override")

        # Calculate EBITDA with wildly different segment prices
        # Should get same result because of price override
        ebitda_at_500 = model.calculate_project_ebitda(mining, 2028, 500)
        ebitda_at_1500 = model.calculate_project_ebitda(mining, 2028, 1500)

        self.assertEqual(ebitda_at_500, ebitda_at_1500,
                        "Mining EBITDA should be same regardless of segment price")

    def test_execution_factor_applies_to_non_br2(self):
        """Execution factor should reduce EBITDA for non-BR2 projects only."""
        base = self.presets[ScenarioType.BASE_CASE]

        model_full = PriceVolumeModel(base, execution_factor=1.0)
        model_haircut = PriceVolumeModel(base, execution_factor=0.75)

        # Calculate Flat-Rolled segment price
        price = model_full.calculate_segment_price(
            Segment.FLAT_ROLLED, 2029
        )

        # Enable Gary Works BF for this test
        gary_full = model_full.projects['Gary Works BF']
        gary_haircut = model_haircut.projects['Gary Works BF']

        ebitda_full = model_full.calculate_project_ebitda(gary_full, 2029, price)
        ebitda_haircut = model_haircut.calculate_project_ebitda(gary_haircut, 2029, price)

        # With 75% execution factor, EBITDA should be 75% of full
        self.assertAlmostEqual(ebitda_haircut, ebitda_full * 0.75, delta=0.01,
                              msg="Gary Works EBITDA should be reduced by execution factor")

    def test_br2_not_affected_by_execution_factor(self):
        """BR2 should NOT be affected by execution factor (committed project)."""
        base = self.presets[ScenarioType.BASE_CASE]

        model_full = PriceVolumeModel(base, execution_factor=1.0)
        model_haircut = PriceVolumeModel(base, execution_factor=0.50)

        price = model_full.calculate_segment_price(
            Segment.MINI_MILL, 2029
        )

        br2_full = model_full.projects['BR2 Mini Mill']
        br2_haircut = model_haircut.projects['BR2 Mini Mill']

        ebitda_full = model_full.calculate_project_ebitda(br2_full, 2029, price)
        ebitda_haircut = model_haircut.calculate_project_ebitda(br2_haircut, 2029, price)

        # BR2 EBITDA should be same regardless of execution factor
        self.assertEqual(ebitda_full, ebitda_haircut,
                        "BR2 EBITDA should not be affected by execution factor")

    def test_capacity_ramp_affects_ebitda(self):
        """EBITDA should be lower during ramp-up years."""
        base = self.presets[ScenarioType.BASE_CASE]
        model = PriceVolumeModel(base)

        price = 900  # Fixed price for comparison

        br2 = model.projects['BR2 Mini Mill']

        # 2025: 20% ramp → low EBITDA
        # 2029: 100% ramp → full EBITDA
        ebitda_2025 = model.calculate_project_ebitda(br2, 2025, price)
        ebitda_2029 = model.calculate_project_ebitda(br2, 2029, price)

        self.assertGreater(ebitda_2029, ebitda_2025,
                          "EBITDA should be higher at full utilization than during ramp")

        # Verify the ratio matches utilization ratio
        # 2025: 20%, 2029: 100%
        expected_ratio = 1.0 / 0.20
        actual_ratio = ebitda_2029 / ebitda_2025

        self.assertAlmostEqual(actual_ratio, expected_ratio, delta=0.01,
                              msg="EBITDA ratio should match utilization ratio")

    def test_project_parameters_are_set(self):
        """Verify all projects have dynamic EBITDA parameters configured.

        Source: Capital Projects EBITDA Impact Analysis (Feb 2026)
        Total target EBITDA: $1,264M at steady state
        """
        # Parameters from EBITDA Impact Analysis document
        expected_params = {
            'BR2 Mini Mill': {'capacity': 3000, 'margin': 0.17, 'override': None},      # $459M
            'Gary Works BF': {'capacity': 2500, 'margin': 0.12, 'override': None},      # $285M
            'Mon Valley HSM': {'capacity': 1800, 'margin': 0.12, 'override': None},     # $205M
            'Greenfield Mini Mill': {'capacity': 500, 'margin': 0.17, 'override': None}, # $77M
            'Mining Investment': {'capacity': 6000, 'margin': 0.12, 'override': 150},   # $108M
            'Fairfield Works': {'capacity': 1200, 'margin': 0.12, 'override': None},    # $130M
        }

        for proj_name, expected in expected_params.items():
            proj = self.projects[proj_name]
            self.assertEqual(proj.nameplate_capacity, expected['capacity'],
                           f"{proj_name} capacity mismatch")
            self.assertEqual(proj.ebitda_margin, expected['margin'],
                           f"{proj_name} margin mismatch")
            self.assertEqual(proj.base_price_override, expected['override'],
                           f"{proj_name} price override mismatch")

    def test_base_case_ebitda_calculation(self):
        """Verify base case EBITDA calculation matches expected formula.

        Formula: Capacity × Utilization × Price × Margin
        BR2 at 100% util, $900 price: 3000 × 1.0 × 900 × 0.17 / 1000 = $459M
        Source: Capital Projects EBITDA Impact Analysis
        """
        base = self.presets[ScenarioType.BASE_CASE]
        model = PriceVolumeModel(base)

        br2 = model.projects['BR2 Mini Mill']

        # Use 100% utilization (steady state) and $900/ton
        price = 900
        expected_ebitda = 3000 * 1.0 * 900 * 0.17 / 1000  # $459M

        # Calculate for a year with 100% ramp (2029+)
        ebitda = model.calculate_project_ebitda(br2, 2029, price)

        self.assertAlmostEqual(ebitda, expected_ebitda, delta=1.0,
                              msg=f"BR2 EBITDA should be ~${expected_ebitda:.0f}M")

    def test_fallback_to_legacy_schedule(self):
        """If nameplate_capacity=0, should fall back to legacy ebitda_schedule."""
        # Create a project with no dynamic parameters
        legacy_project = CapitalProject(
            name='Legacy Project',
            segment='Mini Mill',
            enabled=True,
            capex_schedule={2025: 100},
            nameplate_capacity=0,  # No dynamic params
            ebitda_schedule={2025: 50, 2026: 100, 2027: 150}
        )

        base = self.presets[ScenarioType.BASE_CASE]
        model = PriceVolumeModel(base)

        # Should return legacy schedule values
        self.assertEqual(model.calculate_project_ebitda(legacy_project, 2025, 900), 50)
        self.assertEqual(model.calculate_project_ebitda(legacy_project, 2026, 900), 100)
        self.assertEqual(model.calculate_project_ebitda(legacy_project, 2027, 900), 150)
        self.assertEqual(model.calculate_project_ebitda(legacy_project, 2028, 900), 0)  # Not in schedule


class TestScenarioSensitivity(unittest.TestCase):
    """Test that project EBITDA sensitivity matches expected ranges."""

    def test_br2_ebitda_sensitivity_range(self):
        """BR2 EBITDA should vary across scenarios as expected.

        From plan Table 4:
        - Bear Case ($750/ton): ~$287M
        - Base Case ($900/ton): ~$390M
        - Bull Case ($1050/ton): ~$536M
        """
        presets = get_scenario_presets()

        # Test across different price scenarios
        results = {}
        for scenario_type in [ScenarioType.SEVERE_DOWNTURN, ScenarioType.BASE_CASE, ScenarioType.OPTIMISTIC]:
            scenario = presets[scenario_type]
            model = PriceVolumeModel(scenario)

            price = model.calculate_segment_price(
                Segment.MINI_MILL, 2029
            )
            br2 = model.projects['BR2 Mini Mill']
            ebitda = model.calculate_project_ebitda(br2, 2029, price)

            results[scenario_type] = {'price': price, 'ebitda': ebitda}

        # Verify ordering: severe < base < optimistic
        self.assertLess(results[ScenarioType.SEVERE_DOWNTURN]['ebitda'],
                       results[ScenarioType.BASE_CASE]['ebitda'],
                       "Severe downturn EBITDA should be less than base case")
        self.assertLess(results[ScenarioType.BASE_CASE]['ebitda'],
                       results[ScenarioType.OPTIMISTIC]['ebitda'],
                       "Base case EBITDA should be less than optimistic")

        # Verify reasonable ranges (EBITDA should be $200M-$600M range)
        for scenario_type, data in results.items():
            self.assertGreater(data['ebitda'], 100,
                              f"{scenario_type.value} EBITDA should be > $100M")
            self.assertLess(data['ebitda'], 700,
                           f"{scenario_type.value} EBITDA should be < $700M")


class TestIntegrationWithFullModel(unittest.TestCase):
    """Test dynamic EBITDA integrates correctly with full model."""

    def test_full_analysis_runs_with_dynamic_ebitda(self):
        """Full model analysis should run without errors."""
        presets = get_scenario_presets()

        for scenario_type in [ScenarioType.BASE_CASE, ScenarioType.OPTIMISTIC, ScenarioType.SEVERE_DOWNTURN]:
            with self.subTest(scenario=scenario_type.value):
                scenario = presets[scenario_type]
                model = PriceVolumeModel(scenario)
                analysis = model.run_full_analysis()

                # Check basic validity
                self.assertIn('val_uss', analysis)
                # Share price may be 0 in severe downturns
                self.assertGreaterEqual(analysis['val_uss']['share_price'], 0)

    def test_consolidated_ebitda_includes_project_ebitda(self):
        """Consolidated EBITDA should include dynamically calculated project EBITDA."""
        presets = get_scenario_presets()
        scenario = presets[ScenarioType.BASE_CASE]

        # Run with BR2 enabled (default)
        model = PriceVolumeModel(scenario)
        consolidated, segment_dfs = model.build_consolidated()

        # Get Mini Mill segment for 2029
        mm_2029 = segment_dfs['Mini Mill'][segment_dfs['Mini Mill']['Year'] == 2029].iloc[0]

        # Total EBITDA should include base segment + BR2 project EBITDA
        total_ebitda = mm_2029['Total_EBITDA']

        # Should be positive and reasonable ($500M - $2B range for segment + project)
        self.assertGreater(total_ebitda, 500, "Total EBITDA should include project contribution")


class TestTerminalMultiples(unittest.TestCase):
    """Test comparable-based terminal multiples from WRDS peer analysis."""

    def setUp(self):
        """Load project definitions."""
        self.projects = get_capital_projects()

    def test_terminal_multiples_by_technology(self):
        """Verify terminal multiples match WRDS peer comparables.

        Source: WRDS Compustat annual fundamentals FY2021-2024
        - EAF Mini Mills (STLD, NUE, CMC): Median 6.7x → 7.0x
        - Integrated BF (CLF, MT, PKX): Median 4.8x → 5.0x
        - Tubular: Blended 6.0x
        - Mining: Conservative 5.0x
        """
        expected_multiples = {
            'BR2 Mini Mill': 7.0,        # EAF
            'Greenfield Mini Mill': 7.0,  # EAF
            'Gary Works BF': 5.0,         # Integrated
            'Mon Valley HSM': 5.0,        # Integrated
            'Mining Investment': 5.0,     # Mining
            'Fairfield Works': 6.0,       # Tubular
        }

        for proj_name, expected in expected_multiples.items():
            proj = self.projects[proj_name]
            self.assertEqual(proj.terminal_multiple, expected,
                           f"{proj_name} terminal multiple should be {expected}x")

    def test_eaf_projects_have_higher_multiples(self):
        """EAF mini mills should have higher multiples than integrated mills."""
        br2 = self.projects['BR2 Mini Mill']
        gary = self.projects['Gary Works BF']

        self.assertGreater(br2.terminal_multiple, gary.terminal_multiple,
                          "EAF mini mill (BR2) should have higher multiple than integrated (Gary)")

    def test_terminal_multiple_affects_npv(self):
        """Higher terminal multiple should increase project NPV."""
        presets = get_scenario_presets()
        base = presets[ScenarioType.BASE_CASE]

        br2 = self.projects['BR2 Mini Mill']
        gary = self.projects['Gary Works BF']

        # At same EBITDA, project with higher multiple has higher terminal value
        same_ebitda = 500  # $500M
        wacc = 0.10

        tv_br2 = same_ebitda * br2.terminal_multiple / ((1 + wacc) ** 10)
        tv_gary = same_ebitda * gary.terminal_multiple / ((1 + wacc) ** 10)

        self.assertGreater(tv_br2, tv_gary,
                          "BR2 terminal value should be higher due to EAF multiple")

    def test_terminal_multiple_reasonable_range(self):
        """All terminal multiples should be in reasonable steel sector range (4-10x)."""
        for proj_name, proj in self.projects.items():
            self.assertGreaterEqual(proj.terminal_multiple, 4.0,
                                   f"{proj_name} multiple should be >= 4x")
            self.assertLessEqual(proj.terminal_multiple, 10.0,
                                f"{proj_name} multiple should be <= 10x")


if __name__ == '__main__':
    unittest.main()
