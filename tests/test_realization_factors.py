"""Tests for realization factor MC distributions and price model integration."""

import sys
import json
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDistributionsConfig:
    """Tests for realization factor entries in distributions_config.json."""

    @pytest.fixture
    def config(self):
        path = Path(__file__).parent.parent / 'monte_carlo' / 'distributions_config.json'
        with open(path) as f:
            return json.load(f)

    def test_four_realization_factors_present(self, config):
        variables = config['variables']
        rf_names = ['fr_realization_factor', 'mm_realization_factor',
                     'usse_realization_factor', 'tubular_realization_factor']
        for name in rf_names:
            assert name in variables, f"{name} missing from distributions_config.json"

    def test_distribution_type_is_triangular(self, config):
        for name in ['fr_realization_factor', 'mm_realization_factor',
                      'usse_realization_factor', 'tubular_realization_factor']:
            assert config['variables'][name]['distribution_type'] == 'triangular'

    def test_mode_matches_point_estimate(self, config):
        """Triangular mode should match current point estimates."""
        expected_modes = {
            'fr_realization_factor': 1.044,
            'mm_realization_factor': 0.986,
            'usse_realization_factor': 1.044,
            'tubular_realization_factor': 1.314,
        }
        for name, expected_mode in expected_modes.items():
            actual = config['variables'][name]['parameters']['mode']
            assert actual == pytest.approx(expected_mode, abs=0.001), \
                f"{name} mode: expected {expected_mode}, got {actual}"

    def test_min_less_than_mode_less_than_max(self, config):
        for name in ['fr_realization_factor', 'mm_realization_factor',
                      'usse_realization_factor', 'tubular_realization_factor']:
            params = config['variables'][name]['parameters']
            assert params['min'] < params['mode'] < params['max'], \
                f"{name}: min={params['min']} < mode={params['mode']} < max={params['max']}"

    def test_correlations_defined(self, config):
        corrs = config['correlations']
        assert 'fr_realization_factor' in corrs
        assert 'tubular_realization_factor' in corrs

    def test_total_variables_count(self, config):
        assert config['metadata']['n_variables'] == 33


class TestModelScenarioRealizationFactors:
    """Tests for realization_factors in ModelScenario and calculate_segment_price."""

    def _get_base_scenario(self):
        """Get a base case scenario from presets."""
        from price_volume_model import get_scenario_presets, ScenarioType
        presets = get_scenario_presets()
        return presets[ScenarioType.BASE_CASE]

    def test_default_realization_factors_none(self):
        scenario = self._get_base_scenario()
        assert scenario.realization_factors is None

    def test_realization_factors_passed_through(self):
        scenario = self._get_base_scenario()
        rf = {'flat_rolled': 1.10, 'mini_mill': 0.95, 'usse': 1.05, 'tubular': 1.40}
        scenario.realization_factors = rf
        assert scenario.realization_factors == rf

    def test_calculate_segment_price_uses_override(self):
        """When realization_factors is set, calculate_segment_price uses override premium."""
        from price_volume_model import PriceVolumeModel, Segment

        # Base scenario (no override)
        base = self._get_base_scenario()
        model_base = PriceVolumeModel(base)
        price_base = model_base.calculate_segment_price(Segment.FLAT_ROLLED, 2024)

        # Override with higher realization factor
        base_override = self._get_base_scenario()
        base_override.realization_factors = {'flat_rolled': 1.15}
        model_override = PriceVolumeModel(base_override)
        price_override = model_override.calculate_segment_price(Segment.FLAT_ROLLED, 2024)

        assert price_override > price_base, \
            f"Override price {price_override:.0f} should exceed base {price_base:.0f}"

    def test_default_behavior_unchanged_when_none(self):
        """When realization_factors=None, price calculation unchanged."""
        from price_volume_model import PriceVolumeModel, Segment

        base1 = self._get_base_scenario()
        base1.realization_factors = None
        model1 = PriceVolumeModel(base1)
        price1 = model1.calculate_segment_price(Segment.FLAT_ROLLED, 2024)

        base2 = self._get_base_scenario()
        model2 = PriceVolumeModel(base2)
        price2 = model2.calculate_segment_price(Segment.FLAT_ROLLED, 2024)

        assert price1 == pytest.approx(price2, abs=0.01)


class TestMCEngineRealizationFactors:
    """Tests for realization factor variables in MC engine."""

    def test_realization_factor_variables_in_engine(self):
        from monte_carlo import MonteCarloEngine
        mc = MonteCarloEngine(n_simulations=10, use_config_file=True)
        var_names = list(mc.variables.keys())
        for rf_name in ['fr_realization_factor', 'mm_realization_factor',
                         'usse_realization_factor', 'tubular_realization_factor']:
            assert rf_name in var_names, f"{rf_name} missing from MC engine variables"

    def test_total_variable_count(self):
        from monte_carlo import MonteCarloEngine
        mc = MonteCarloEngine(n_simulations=10, use_config_file=True)
        assert len(mc.variables) == 33, f"Expected 33 variables, got {len(mc.variables)}"
