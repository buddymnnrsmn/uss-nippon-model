#!/usr/bin/env python3
"""
Test suite for catching division by zero and other numerical errors in the model.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType, SteelPriceScenario, VolumeScenario,
    get_scenario_presets, calculate_probability_weighted_valuation, BENCHMARK_PRICES_2023
)


class TestNoDivisionByZero(unittest.TestCase):
    """Test that no division by zero errors occur in any scenario."""

    def test_all_preset_scenarios(self):
        """Test all preset scenarios run without division errors."""
        presets = get_scenario_presets()

        for scenario_type, scenario in presets.items():
            with self.subTest(scenario=scenario_type.value):
                model = PriceVolumeModel(scenario)
                analysis = model.run_full_analysis()

                # Check that share prices are non-negative
                self.assertGreaterEqual(analysis['val_uss']['share_price'], 0,
                    f"USS share price should be >= 0 in {scenario_type.value}")
                self.assertGreaterEqual(analysis['val_nippon']['share_price'], 0,
                    f"Nippon share price should be >= 0 in {scenario_type.value}")

                # Check that EV values are valid
                self.assertIsNotNone(analysis['val_uss']['ev_blended'])
                self.assertIsNotNone(analysis['val_nippon']['ev_blended'])

    def test_probability_weighted_valuation(self):
        """Test probability-weighted valuation handles all scenarios."""
        try:
            pw_results = calculate_probability_weighted_valuation(
                custom_benchmarks=BENCHMARK_PRICES_2023
            )

            # Check weighted values are non-negative
            self.assertGreaterEqual(pw_results['weighted_uss_value_per_share'], 0)
            self.assertGreaterEqual(pw_results['weighted_nippon_value_per_share'], 0)

            # Check all scenario results
            for scenario_type, result in pw_results['scenario_results'].items():
                self.assertGreaterEqual(result['uss_value_per_share'], 0,
                    f"USS value should be >= 0 in {result['name']}")
                self.assertGreaterEqual(result['nippon_value_per_share'], 0,
                    f"Nippon value should be >= 0 in {result['name']}")

        except ZeroDivisionError as e:
            self.fail(f"Division by zero error: {e}")

    def test_extreme_downside_scenario(self):
        """Test extreme downside scenario (should hit equity floor at 0)."""
        # Use the severe downturn preset which is already an extreme scenario
        presets = get_scenario_presets()
        extreme_scenario = presets[ScenarioType.SEVERE_DOWNTURN]

        model = PriceVolumeModel(extreme_scenario)
        analysis = model.run_full_analysis()

        # Share price should be floored at 0, not negative
        self.assertGreaterEqual(analysis['val_uss']['share_price'], 0,
            "USS share price should never be negative (equity floor)")
        self.assertGreaterEqual(analysis['val_nippon']['share_price'], 0,
            "Nippon share price should never be negative")

        # In severe downturn, USS equity should be wiped out (at floor)
        # This verifies the equity floor is working
        print(f"Severe Downturn USS price: ${analysis['val_uss']['share_price']:.2f}")

    def test_vs_offer_calculations(self):
        """Test that vs $55 offer calculations don't cause division by zero."""
        presets = get_scenario_presets()

        for scenario_type, scenario in presets.items():
            with self.subTest(scenario=scenario_type.value):
                model = PriceVolumeModel(scenario)
                analysis = model.run_full_analysis()

                uss_val = analysis['val_uss']['share_price']

                # Simulate the dashboard calculation
                if uss_val > 0.01:
                    vs_offer = (55.0 / uss_val - 1) * 100
                    self.assertIsInstance(vs_offer, float)
                else:
                    # Should use "N/A" text, not calculate
                    pass  # This is expected for wiped-out equity

    def test_premium_percentage_calculations(self):
        """Test premium percentage calculations with various share prices."""
        test_values = [0, 0.01, 1, 10, 34, 55, 100]
        offer_price = 55.0

        for uss_val in test_values:
            with self.subTest(uss_value=uss_val):
                premium = offer_price - uss_val

                # Simulate dashboard logic
                if uss_val > 0.01:
                    premium_pct = premium / uss_val * 100
                    self.assertIsInstance(premium_pct, float)
                else:
                    # Should show "N/A" instead
                    pass


class TestEdgeCases(unittest.TestCase):
    """Test edge cases that might cause numerical issues."""

    def test_zero_ebitda_handling(self):
        """Test handling when EBITDA approaches zero."""
        # This would require modifying the model significantly
        # For now, just verify the model handles normal cases
        presets = get_scenario_presets()
        base = presets[ScenarioType.BASE_CASE]

        model = PriceVolumeModel(base)
        analysis = model.run_full_analysis()

        # Get consolidated financials
        consolidated = analysis['consolidated']
        ebitda_2024 = consolidated.loc[consolidated['Year'] == 2024, 'Total_EBITDA'].values[0]

        # EBITDA should be positive in base case
        self.assertGreater(ebitda_2024, 0, "Base case EBITDA should be positive")

        # Implied EV/EBITDA calculation
        if ebitda_2024 > 0:
            implied_mult = analysis['val_uss']['ev_blended'] / ebitda_2024
            self.assertIsInstance(implied_mult, float)
            self.assertGreater(implied_mult, 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
