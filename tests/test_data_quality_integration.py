"""Integration tests for data quality remediation across all phases."""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_DIR = Path(__file__).parent.parent


class TestSegmentDataNotDuplicated:
    """Phase 1: USS_SEGMENT_DATA should only be defined in one place."""

    def test_no_inline_segment_data_in_revenue_correlation(self):
        """revenue_price_correlation.py should import, not define, USS_SEGMENT_DATA."""
        path = BASE_DIR / 'scripts' / 'revenue_price_correlation.py'
        content = path.read_text()
        # Should import from shared module
        assert 'from data.uss_segment_data import' in content
        # Should NOT have inline data definition (multi-line dict with year tuples)
        assert '(2019, 8543, 651, 9600, 890)' not in content

    def test_no_inline_segment_data_in_extract_margin(self):
        """extract_margin_sensitivity.py should import, not define, USS_SEGMENT_DATA."""
        path = BASE_DIR / 'scripts' / 'extract_margin_sensitivity.py'
        content = path.read_text()
        assert 'from data.uss_segment_data import' in content
        assert '(2019, 8543, 651, 9600, 890)' not in content


class TestDistributionsConfig:
    """Phase 2: distributions_config.json should have 33 variables."""

    def test_variable_count(self):
        path = BASE_DIR / 'monte_carlo' / 'distributions_config.json'
        with open(path) as f:
            config = json.load(f)
        assert len(config['variables']) == 33
        assert config['metadata']['n_variables'] == 33

    def test_realization_factors_present(self):
        path = BASE_DIR / 'monte_carlo' / 'distributions_config.json'
        with open(path) as f:
            config = json.load(f)
        for name in ['fr_realization_factor', 'mm_realization_factor',
                      'usse_realization_factor', 'tubular_realization_factor']:
            assert name in config['variables']


class TestCorrelationMatrixRenamed:
    """Phase 4: correlation_matrix.csv renamed to correlation_matrix_LEVELS.csv."""

    def test_old_name_does_not_exist(self):
        old_path = BASE_DIR / 'market-data' / 'exports' / 'processed' / 'correlation_matrix.csv'
        assert not old_path.exists(), "correlation_matrix.csv should be renamed to _LEVELS.csv"

    def test_new_name_exists(self):
        new_path = BASE_DIR / 'market-data' / 'exports' / 'processed' / 'correlation_matrix_LEVELS.csv'
        assert new_path.exists(), "correlation_matrix_LEVELS.csv should exist"


class TestCalibrationQualityReport:
    """Phase 4: report_calibration_quality works correctly."""

    def test_report_categorizes_all_variables(self):
        from scripts.run_monte_carlo_analysis import report_calibration_quality
        categories, score = report_calibration_quality()
        assert len(categories) == 33, f"Expected 33 categorized variables, got {len(categories)}"

    def test_quality_score_bounded(self):
        from scripts.run_monte_carlo_analysis import report_calibration_quality
        _, score = report_calibration_quality()
        assert 0 < score <= 1.0, f"Quality score {score} out of range"


class TestBaseCaseStability:
    """Phase 2+5: Base case DCF should still produce USS ~$39."""

    def test_base_case_uss_price(self):
        """Base case USS share price should be reasonable (not broken by realization factors).

        Note: Base case (50th percentile) produces ~$54 standalone.
        WA (probability-weighted across scenarios) produces ~$39.
        We check for reasonable range and non-zero value.
        """
        from price_volume_model import PriceVolumeModel, get_scenario_presets, ScenarioType

        presets = get_scenario_presets()
        scenario = presets[ScenarioType.BASE_CASE]
        model = PriceVolumeModel(scenario)
        analysis = model.run_full_analysis()

        uss_share = analysis['val_uss']['share_price']
        assert 10 <= uss_share <= 100, \
            f"Base case USS share price {uss_share:.2f} outside expected range $10-$100"


class TestDemandRankingsUsePartialR:
    """Phase 3: demand_driver_analysis.py should rank by partial r."""

    def test_partial_r_ranking_code_present(self):
        path = BASE_DIR / 'scripts' / 'demand_driver_analysis.py'
        content = path.read_text()
        assert 'abs_partial_r' in content or 'r_partial' in content, \
            "demand_driver_analysis.py should rank indicators by partial r"

    def test_composite_scoring_function_exists(self):
        from scripts.advanced_demand_analysis import compute_composite_indicator_score
        assert callable(compute_composite_indicator_score)


class TestMCEngineVariableCount:
    """Phase 2: MC engine should have 33 variables (29 + 4 realization factors)."""

    def test_engine_has_33_variables(self):
        from monte_carlo import MonteCarloEngine
        mc = MonteCarloEngine(n_simulations=10, use_config_file=True)
        assert len(mc.variables) == 33, f"Expected 33 MC variables, got {len(mc.variables)}"


class TestReferences:
    """Phase 4: All references to correlation_matrix.csv updated."""

    def test_analyze_distributions_uses_levels(self):
        path = BASE_DIR / 'scripts' / 'analyze_distributions.py'
        content = path.read_text()
        assert 'correlation_matrix_LEVELS.csv' in content

    def test_load_bloomberg_uses_levels(self):
        path = BASE_DIR / 'scripts' / 'load_bloomberg_data.py'
        content = path.read_text()
        assert 'correlation_matrix_LEVELS.csv' in content

    def test_config_json_uses_levels(self):
        path = BASE_DIR / 'market-data' / 'bloomberg' / 'config.json'
        with open(path) as f:
            config = json.load(f)
        derived = config.get('derived_data', {}).get('correlation_matrix', {})
        assert 'LEVELS' in derived.get('file', ''), \
            "config.json correlation_matrix should reference _LEVELS.csv"
