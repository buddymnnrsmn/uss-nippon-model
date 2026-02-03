#!/usr/bin/env python3
"""
Test suite for WACC module integration with the main financial model.

Tests:
1. WACC module availability and imports
2. USS WACC calculation (~10.76%)
3. Nippon USD WACC calculation (~7.95%)
4. Model integration with use_verified_wacc=True
5. Backward compatibility without module
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import copy


class TestWACCModuleAvailability(unittest.TestCase):
    """Test that the WACC module is available and imports correctly."""

    def test_module_flag_available(self):
        """Test WACC_MODULE_AVAILABLE flag is exposed."""
        from price_volume_model import WACC_MODULE_AVAILABLE
        self.assertIsInstance(WACC_MODULE_AVAILABLE, bool)

    def test_module_imports(self):
        """Test that WACC module imports work."""
        from price_volume_model import (
            WACC_MODULE_AVAILABLE,
            get_verified_uss_wacc,
            get_verified_nippon_wacc,
            get_wacc_module_status
        )
        # Functions should exist regardless of module availability
        self.assertTrue(callable(get_verified_uss_wacc))
        self.assertTrue(callable(get_verified_nippon_wacc))
        self.assertTrue(callable(get_wacc_module_status))

    def test_module_status(self):
        """Test get_wacc_module_status returns correct structure."""
        from price_volume_model import get_wacc_module_status
        status = get_wacc_module_status()

        self.assertIn('available', status)
        self.assertIn('uss_wacc', status)
        self.assertIn('nippon_jpy_wacc', status)
        self.assertIn('nippon_usd_wacc', status)
        self.assertIn('data_as_of_date', status)


class TestUSSWACCCalculation(unittest.TestCase):
    """Test USS WACC calculation values."""

    def setUp(self):
        """Skip tests if WACC module not available."""
        from price_volume_model import WACC_MODULE_AVAILABLE
        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

    def test_uss_wacc_value(self):
        """Test USS WACC is approximately 10.76%."""
        from price_volume_model import get_verified_uss_wacc
        wacc, audit = get_verified_uss_wacc()

        self.assertIsNotNone(wacc)
        # USS WACC should be between 10% and 12%
        self.assertGreater(wacc, 0.10)
        self.assertLess(wacc, 0.12)
        # More specifically, should be close to 10.70%
        self.assertAlmostEqual(wacc, 0.107, delta=0.01)

    def test_uss_wacc_has_audit_trail(self):
        """Test USS WACC returns audit trail."""
        from price_volume_model import get_verified_uss_wacc
        wacc, audit = get_verified_uss_wacc()

        self.assertIsNotNone(audit)
        self.assertIn('data_as_of_date', audit)
        self.assertIn('calculated_wacc', audit)

    def test_uss_wacc_components(self):
        """Test USS WACC components are reasonable."""
        # Import directly from the wacc module for detailed checks
        try:
            sys.path.insert(0, os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'wacc-calculations'
            ))
            from uss.uss_wacc import calculate_uss_wacc

            result = calculate_uss_wacc()

            # Risk-free rate should be ~3.88%
            self.assertAlmostEqual(result.risk_free_rate, 0.0388, delta=0.01)

            # Beta should be ~1.45
            self.assertAlmostEqual(result.levered_beta, 1.45, delta=0.1)

            # Equity risk premium should be ~5.5%
            self.assertAlmostEqual(result.equity_risk_premium, 0.055, delta=0.01)

            # Cost of equity should be > risk-free rate
            self.assertGreater(result.cost_of_equity, result.risk_free_rate)

        except ImportError:
            self.skipTest("WACC module not available for detailed checks")


class TestNipponWACCCalculation(unittest.TestCase):
    """Test Nippon WACC calculation values."""

    def setUp(self):
        """Skip tests if WACC module not available."""
        from price_volume_model import WACC_MODULE_AVAILABLE
        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

    def test_nippon_wacc_values(self):
        """Test Nippon WACC values are approximately correct."""
        from price_volume_model import get_verified_nippon_wacc
        jpy_wacc, usd_wacc, audit = get_verified_nippon_wacc()

        self.assertIsNotNone(jpy_wacc)
        self.assertIsNotNone(usd_wacc)

        # JPY WACC should be between 4% and 6%
        self.assertGreater(jpy_wacc, 0.04)
        self.assertLess(jpy_wacc, 0.06)

        # USD WACC should be between 7% and 9%
        self.assertGreater(usd_wacc, 0.07)
        self.assertLess(usd_wacc, 0.09)

        # More specifically, USD WACC should be close to 7.95%
        self.assertAlmostEqual(usd_wacc, 0.0795, delta=0.01)

    def test_nippon_irp_adjustment(self):
        """Test IRP adjustment increases JPY WACC to USD WACC."""
        from price_volume_model import get_verified_nippon_wacc
        jpy_wacc, usd_wacc, audit = get_verified_nippon_wacc()

        # IRP adjustment should increase WACC (US rates > Japan rates)
        self.assertGreater(usd_wacc, jpy_wacc)

        # Difference should be roughly the rate differential (~3%)
        irp_adjustment = usd_wacc - jpy_wacc
        self.assertGreater(irp_adjustment, 0.02)
        self.assertLess(irp_adjustment, 0.05)

    def test_nippon_wacc_has_audit_trail(self):
        """Test Nippon WACC returns audit trail."""
        from price_volume_model import get_verified_nippon_wacc
        jpy_wacc, usd_wacc, audit = get_verified_nippon_wacc()

        self.assertIsNotNone(audit)
        self.assertIn('data_as_of_date', audit)


class TestModelIntegration(unittest.TestCase):
    """Test WACC module integration with the main model."""

    def test_model_scenario_has_verified_wacc_field(self):
        """Test ModelScenario has use_verified_wacc field."""
        from price_volume_model import ModelScenario, get_scenario_presets, ScenarioType

        presets = get_scenario_presets()
        scenario = presets[ScenarioType.BASE_CASE]

        # Field should exist with default True
        self.assertTrue(hasattr(scenario, 'use_verified_wacc'))
        self.assertTrue(scenario.use_verified_wacc)  # Default is now True

    def test_model_runs_with_verified_wacc(self):
        """Test model runs successfully with use_verified_wacc=True."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType,
            WACC_MODULE_AVAILABLE
        )

        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

        presets = get_scenario_presets()
        scenario = copy.deepcopy(presets[ScenarioType.BASE_CASE])
        scenario.use_verified_wacc = True

        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        # Results should include all expected keys
        self.assertIn('uss_wacc', results)
        self.assertIn('usd_wacc', results)
        self.assertIn('jpy_wacc', results)
        self.assertIn('wacc_audit_trail', results)

        # WACC values should be valid
        self.assertIsNotNone(results['uss_wacc'])
        self.assertIsNotNone(results['usd_wacc'])

    def test_verified_wacc_differs_from_scenario(self):
        """Test verified WACC may differ from scenario preset."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType,
            WACC_MODULE_AVAILABLE
        )

        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

        presets = get_scenario_presets()
        scenario = copy.deepcopy(presets[ScenarioType.BASE_CASE])
        original_uss_wacc = scenario.uss_wacc

        scenario.use_verified_wacc = True
        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        # Verified WACC should be the one from the module
        # (which may differ from the scenario preset)
        verified_uss_wacc = results['uss_wacc']

        # Both should be reasonable values
        self.assertGreater(original_uss_wacc, 0.08)
        self.assertLess(original_uss_wacc, 0.15)
        self.assertGreater(verified_uss_wacc, 0.08)
        self.assertLess(verified_uss_wacc, 0.15)

    def test_audit_trail_populated(self):
        """Test audit trail is populated when use_verified_wacc=True."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType,
            WACC_MODULE_AVAILABLE
        )

        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

        presets = get_scenario_presets()
        scenario = copy.deepcopy(presets[ScenarioType.BASE_CASE])
        scenario.use_verified_wacc = True

        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        audit = results.get('wacc_audit_trail')
        self.assertIsNotNone(audit)
        self.assertEqual(audit['source'], 'wacc-calculations module')


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility without WACC module."""

    def test_model_runs_without_verified_wacc(self):
        """Test model runs normally with use_verified_wacc=False."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType
        )

        presets = get_scenario_presets()
        scenario = copy.deepcopy(presets[ScenarioType.BASE_CASE])
        scenario.use_verified_wacc = False

        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        # Should have all standard results
        self.assertIn('val_uss', results)
        self.assertIn('val_nippon', results)
        self.assertIn('consolidated', results)

        # USS WACC should match scenario
        self.assertEqual(results['uss_wacc'], scenario.uss_wacc)

        # Audit trail should be None when not using verified WACC
        self.assertIsNone(results.get('wacc_audit_trail'))

    def test_all_scenarios_run_without_verified_wacc(self):
        """Test all preset scenarios run with verified WACC disabled."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets
        )

        presets = get_scenario_presets()

        for scenario_type, scenario in presets.items():
            with self.subTest(scenario=scenario_type.value):
                # Explicitly disable verified WACC for this test
                scenario_copy = copy.deepcopy(scenario)
                scenario_copy.use_verified_wacc = False

                model = PriceVolumeModel(scenario_copy)
                results = model.run_full_analysis()

                # Should complete without error
                self.assertIsNotNone(results['val_uss'])
                self.assertIsNotNone(results['val_nippon'])

    def test_graceful_fallback_if_module_unavailable(self):
        """Test graceful fallback when WACC module functions return None."""
        from price_volume_model import (
            get_verified_uss_wacc,
            get_verified_nippon_wacc
        )

        # These should either return valid values or (None, None)
        uss_wacc, uss_audit = get_verified_uss_wacc()
        jpy_wacc, usd_wacc, nippon_audit = get_verified_nippon_wacc()

        # If module is unavailable, should return None without error
        # If available, should return valid values
        if uss_wacc is not None:
            self.assertIsInstance(uss_wacc, float)
        if usd_wacc is not None:
            self.assertIsInstance(usd_wacc, float)


class TestWACCAdvantage(unittest.TestCase):
    """Test WACC advantage calculations."""

    def test_wacc_advantage_calculation(self):
        """Test WACC advantage is correctly calculated."""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType,
            WACC_MODULE_AVAILABLE
        )

        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

        presets = get_scenario_presets()
        scenario = copy.deepcopy(presets[ScenarioType.BASE_CASE])
        scenario.use_verified_wacc = True

        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        uss_wacc = results['uss_wacc']
        usd_wacc = results['usd_wacc']
        wacc_advantage = results['wacc_advantage']

        # WACC advantage should be USS WACC - Nippon USD WACC
        expected_advantage = uss_wacc - usd_wacc
        self.assertAlmostEqual(wacc_advantage, expected_advantage, places=6)

        # Nippon should have lower cost of capital (positive advantage for Nippon)
        self.assertGreater(wacc_advantage, 0)

    def test_wacc_advantage_positive(self):
        """Test Nippon has cost of capital advantage (lower WACC)."""
        from price_volume_model import get_wacc_module_status, WACC_MODULE_AVAILABLE

        if not WACC_MODULE_AVAILABLE:
            self.skipTest("WACC module not available")

        status = get_wacc_module_status()

        uss_wacc = status['uss_wacc']
        nippon_usd_wacc = status['nippon_usd_wacc']

        # Nippon should have lower cost of capital
        self.assertLess(nippon_usd_wacc, uss_wacc)

        # Advantage should be 2-4%
        advantage = uss_wacc - nippon_usd_wacc
        self.assertGreater(advantage, 0.02)
        self.assertLess(advantage, 0.05)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
