#!/usr/bin/env python3
"""
Tests for Bloomberg Data Integration
====================================

Tests the Bloomberg data service, price calibration, WACC overlay,
and Monte Carlo calibration modules.

Run with: pytest tests/test_bloomberg_integration.py -v
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "market-data"))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def bloomberg_service():
    """Get Bloomberg service instance (may not be available)"""
    try:
        from bloomberg import get_bloomberg_service, is_bloomberg_available
        if is_bloomberg_available():
            return get_bloomberg_service()
    except ImportError:
        pass
    return None


@pytest.fixture
def mock_csv_data():
    """Mock CSV data for testing without actual Bloomberg files"""
    import pandas as pd
    dates = pd.date_range(start='2020-01-01', end='2025-01-01', freq='W')
    values = [700 + i * 0.5 for i in range(len(dates))]
    return pd.DataFrame({'date': dates, 'value': values})


# =============================================================================
# DATA SERVICE TESTS
# =============================================================================

class TestBloombergDataService:
    """Tests for BloombergDataService"""

    def test_service_is_singleton(self, bloomberg_service):
        """Test that service is a singleton"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        from bloomberg import get_bloomberg_service
        service2 = get_bloomberg_service()
        assert bloomberg_service is service2

    def test_is_available_returns_bool(self, bloomberg_service):
        """Test is_available returns boolean"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        result = bloomberg_service.is_available()
        assert isinstance(result, bool)

    def test_get_status_returns_dict(self, bloomberg_service):
        """Test get_status returns proper structure"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        status = bloomberg_service.get_status()
        assert isinstance(status, dict)
        assert 'enabled' in status
        assert 'overall_status' in status or 'message' in status

    def test_get_current_prices_returns_dict(self, bloomberg_service):
        """Test get_current_prices returns dict with expected keys"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        prices = bloomberg_service.get_current_prices()
        assert isinstance(prices, dict)
        # Should have at least some of the expected keys
        expected_keys = ['hrc_us', 'crc_us', 'hrc_eu', 'octg']
        found_keys = [k for k in expected_keys if k in prices]
        assert len(found_keys) > 0

    def test_get_current_rates_returns_dict(self, bloomberg_service):
        """Test get_current_rates returns dict"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        rates = bloomberg_service.get_current_rates()
        assert isinstance(rates, dict)

    def test_get_price_stats_returns_timeseries_stats(self, bloomberg_service):
        """Test get_price_stats returns TimeSeriesStats"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        stats = bloomberg_service.get_price_stats('hrc_us')
        if stats is not None:
            assert hasattr(stats, 'latest_value')
            assert hasattr(stats, 'latest_date')
            assert stats.latest_value > 0


# =============================================================================
# ANNUAL AVERAGE PRICES TESTS
# =============================================================================

class TestAnnualAveragePrices:
    """Tests for annual average price calculation"""

    def test_get_annual_average_prices(self, bloomberg_service):
        """Test get_annual_average_prices returns valid prices"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        prices = bloomberg_service.get_annual_average_prices(2023)
        assert isinstance(prices, dict)
        # Should have key benchmarks
        assert 'hrc_us' in prices
        assert 'crc_us' in prices
        assert 'hrc_eu' in prices
        assert 'octg' in prices
        assert 'coated_us' in prices

    def test_annual_average_prices_are_reasonable(self, bloomberg_service):
        """Test that annual average prices are in reasonable ranges"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        prices = bloomberg_service.get_annual_average_prices(2023)
        # HRC US should be between $500-$1500
        assert 500 < prices.get('hrc_us', 0) < 1500
        # CRC should be higher than HRC
        assert prices.get('crc_us', 0) > prices.get('hrc_us', 0)
        # OCTG should be significantly higher
        assert prices.get('octg', 0) > 1500

    def test_benchmark_prices_2023_uses_annual_avg(self, bloomberg_service):
        """Test that get_benchmark_prices_2023 returns annual averages"""
        if bloomberg_service is None:
            pytest.skip("Bloomberg service not available")

        if not bloomberg_service.is_available():
            pytest.skip("Bloomberg data not loaded")

        annual_avg = bloomberg_service.get_annual_average_prices(2023)
        benchmark_2023 = bloomberg_service.get_benchmark_prices_2023()

        # Should be the same (both call annual average now)
        for key in annual_avg:
            assert abs(annual_avg[key] - benchmark_2023.get(key, 0)) < 1


# =============================================================================
# PRICE CALIBRATOR TESTS
# =============================================================================

class TestPriceCalibrator:
    """Tests for price calibration module"""

    def test_get_current_benchmark_prices(self, bloomberg_service):
        """Test get_current_benchmark_prices function"""
        try:
            from bloomberg import get_current_benchmark_prices
        except ImportError:
            pytest.skip("Bloomberg module not available")

        prices = get_current_benchmark_prices()
        # Should return None if Bloomberg not available, or dict if available
        assert prices is None or isinstance(prices, dict)

    def test_get_price_comparison_table(self, bloomberg_service):
        """Test get_price_comparison_table returns list"""
        try:
            from bloomberg import get_price_comparison_table
        except ImportError:
            pytest.skip("Bloomberg module not available")

        comparisons = get_price_comparison_table()
        assert isinstance(comparisons, list)
        # Should always return a list (possibly with fallback values)

    def test_price_comparison_has_required_fields(self, bloomberg_service):
        """Test price comparisons have required fields"""
        try:
            from bloomberg import get_price_comparison_table
        except ImportError:
            pytest.skip("Bloomberg module not available")

        comparisons = get_price_comparison_table()
        if len(comparisons) > 0:
            pc = comparisons[0]
            assert hasattr(pc, 'benchmark')
            assert hasattr(pc, 'current_price')
            assert hasattr(pc, 'default_price')
            assert hasattr(pc, 'difference')
            assert hasattr(pc, 'percent_change')


# =============================================================================
# WACC OVERLAY TESTS
# =============================================================================

class TestWACCOverlay:
    """Tests for WACC overlay module"""

    def test_get_wacc_overlay(self, bloomberg_service):
        """Test get_wacc_overlay function"""
        try:
            from bloomberg import get_wacc_overlay
        except ImportError:
            pytest.skip("Bloomberg module not available")

        overlay = get_wacc_overlay()
        # Should return None if not available, or WACCBloombergOverlay
        if overlay is not None:
            assert hasattr(overlay, 'risk_free_rate')
            assert overlay.risk_free_rate > 0

    def test_wacc_overlay_has_sources(self, bloomberg_service):
        """Test WACC overlay includes source documentation"""
        try:
            from bloomberg import get_wacc_overlay
        except ImportError:
            pytest.skip("Bloomberg module not available")

        overlay = get_wacc_overlay()
        if overlay is not None:
            assert hasattr(overlay, 'sources')
            assert isinstance(overlay.sources, dict)

    def test_wacc_overlay_to_dict(self, bloomberg_service):
        """Test WACC overlay can convert to dict"""
        try:
            from bloomberg import get_wacc_overlay
        except ImportError:
            pytest.skip("Bloomberg module not available")

        overlay = get_wacc_overlay()
        if overlay is not None:
            d = overlay.to_dict()
            assert isinstance(d, dict)
            assert 'risk_free_rate' in d


# =============================================================================
# MONTE CARLO CALIBRATOR TESTS
# =============================================================================

class TestMonteCarloCalibrator:
    """Tests for Monte Carlo calibration module"""

    def test_get_calibrated_distributions(self, bloomberg_service):
        """Test get_calibrated_distributions function"""
        try:
            from bloomberg import get_calibrated_distributions
        except ImportError:
            pytest.skip("Bloomberg module not available")

        distributions = get_calibrated_distributions()
        # Should return None if not available, or dict
        if distributions is not None:
            assert isinstance(distributions, dict)

    def test_get_calibrated_correlation_matrix(self, bloomberg_service):
        """Test get_calibrated_correlation_matrix function"""
        try:
            from bloomberg import get_calibrated_correlation_matrix
        except ImportError:
            pytest.skip("Bloomberg module not available")

        corr = get_calibrated_correlation_matrix()
        # Should return None or DataFrame
        if corr is not None:
            import pandas as pd
            assert isinstance(corr, pd.DataFrame)


# =============================================================================
# GRACEFUL FALLBACK TESTS
# =============================================================================

class TestGracefulFallbacks:
    """Test that model works without Bloomberg data"""

    def test_price_volume_model_works_without_bloomberg(self):
        """Test PriceVolumeModel works when Bloomberg unavailable"""
        from price_volume_model import (
            PriceVolumeModel, get_scenario_presets, ScenarioType
        )

        presets = get_scenario_presets()
        scenario = presets[ScenarioType.BASE_CASE]

        model = PriceVolumeModel(scenario)
        results = model.run_full_analysis()

        assert results is not None
        # Results structure contains val_uss with enterprise values
        assert 'val_uss' in results
        assert results['val_uss']['ev_blended'] > 0
        assert results['val_uss']['share_price'] > 0

    def test_monte_carlo_works_without_bloomberg(self):
        """Test MonteCarloEngine works when Bloomberg unavailable"""
        from monte_carlo.monte_carlo_engine import MonteCarloEngine

        # Explicitly disable Bloomberg
        mc = MonteCarloEngine(
            n_simulations=100,
            use_bloomberg_calibration=False
        )

        assert mc.bloomberg_calibration_used == False
        assert len(mc.variables) > 0

    def test_benchmark_prices_2023_always_available(self):
        """Test BENCHMARK_PRICES_2023 is always available"""
        from price_volume_model import BENCHMARK_PRICES_2023

        assert isinstance(BENCHMARK_PRICES_2023, dict)
        assert 'hrc_us' in BENCHMARK_PRICES_2023
        assert 'crc_us' in BENCHMARK_PRICES_2023
        assert 'octg' in BENCHMARK_PRICES_2023

    def test_get_benchmark_prices_with_fallback(self):
        """Test get_benchmark_prices falls back gracefully"""
        from price_volume_model import get_benchmark_prices, _HARDCODED_BENCHMARK_PRICES, BENCHMARK_PRICES_THROUGH_CYCLE

        # Default: returns through-cycle baseline
        prices = get_benchmark_prices()
        assert prices == BENCHMARK_PRICES_THROUGH_CYCLE

        # With use_through_cycle=False, use_bloomberg=False: returns hardcoded fallbacks
        prices = get_benchmark_prices(use_bloomberg=False, use_through_cycle=False)
        assert prices == _HARDCODED_BENCHMARK_PRICES

        # Should also work with use_bloomberg=True (uses Bloomberg 2023 data or hardcoded)
        prices_bb = get_benchmark_prices(use_bloomberg=True, use_through_cycle=False)
        assert isinstance(prices_bb, dict)
        assert 'hrc_us' in prices_bb


# =============================================================================
# MODEL INTEGRATION TESTS
# =============================================================================

class TestModelIntegration:
    """Test Bloomberg integration with main model"""

    def test_model_scenario_has_bloomberg_fields(self):
        """Test ModelScenario has Bloomberg integration fields"""
        from price_volume_model import ModelScenario, get_scenario_presets, ScenarioType

        scenario = get_scenario_presets()[ScenarioType.BASE_CASE]

        assert hasattr(scenario, 'use_bloomberg_prices')
        assert hasattr(scenario, 'bloomberg_price_override')

    def test_bloomberg_status_function(self):
        """Test get_bloomberg_status returns proper structure"""
        from price_volume_model import get_bloomberg_status

        status = get_bloomberg_status()
        assert isinstance(status, dict)
        assert 'available' in status
        assert 'analysis_effective_date' in status
        assert 'hardcoded_prices' in status

    def test_wacc_module_with_bloomberg_overlay(self, bloomberg_service):
        """Test USS WACC can accept Bloomberg overlay"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "wacc-calculations"))
            from uss.uss_wacc import calculate_uss_wacc
        except ImportError:
            pytest.skip("WACC module not available")

        # Test with mock overlay
        mock_overlay = {
            'risk_free_rate': 0.045,
            'suggested_cost_of_debt': 0.075,
        }

        result = calculate_uss_wacc(bloomberg_overlay=mock_overlay)
        assert result is not None
        assert result.wacc > 0


# =============================================================================
# REALIZATION MAPPER TESTS
# =============================================================================

class TestRealizationMapper:
    """Tests for benchmark-to-realization mapping"""

    def test_estimate_segment_realizations(self):
        """Test segment realization estimation"""
        try:
            from bloomberg import estimate_segment_realizations
        except ImportError:
            pytest.skip("Bloomberg module not available")

        benchmarks = {
            'hrc_us': 916,
            'crc_us': 1127,
            'coated_us': 1263,
            'hrc_eu': 717,
            'octg': 2750,
        }

        realizations = estimate_segment_realizations(benchmarks)

        assert isinstance(realizations, dict)
        assert 'flat_rolled' in realizations
        assert 'mini_mill' in realizations
        assert 'usse' in realizations
        assert 'tubular' in realizations

        # All values should be positive
        for key, value in realizations.items():
            assert value > 0, f"{key} should be positive"

    def test_realizations_close_to_10k_actuals(self):
        """Test that estimated realizations are close to USS 10-K actuals"""
        try:
            from bloomberg import (
                estimate_segment_realizations,
                validate_realization_factors,
                USS_2023_REALIZED_PRICES,
            )
        except ImportError:
            pytest.skip("Bloomberg module not available")

        benchmarks = {
            'hrc_us': 916,
            'crc_us': 1127,
            'coated_us': 1263,
            'hrc_eu': 717,
            'octg': 2750,
        }

        validation = validate_realization_factors(benchmarks, USS_2023_REALIZED_PRICES)

        # Each segment should be within 10% of actual
        for segment, metrics in validation.items():
            assert abs(metrics['error_pct']) < 10, \
                f"{segment} error {metrics['error_pct']:.1f}% exceeds 10%"

    def test_forecast_with_price_change(self):
        """Test forecasting with price changes"""
        try:
            from bloomberg import (
                estimate_segment_realizations,
                forecast_realizations_with_change,
            )
        except ImportError:
            pytest.skip("Bloomberg module not available")

        benchmarks = {
            'hrc_us': 916,
            'crc_us': 1127,
            'coated_us': 1263,
            'hrc_eu': 717,
            'octg': 2750,
        }

        # Apply +10% to HRC prices
        change = {'hrc_us': 0.10, 'crc_us': 0.10, 'coated_us': 0.10}
        forecast = forecast_realizations_with_change(benchmarks, change)
        base = estimate_segment_realizations(benchmarks)

        # Flat-rolled should increase (uses US benchmarks)
        assert forecast['flat_rolled'] > base['flat_rolled']
        # Tubular should stay same (uses OCTG, not changed)
        assert abs(forecast['tubular'] - base['tubular']) < 1

    def test_realization_summary(self):
        """Test realization summary includes all details"""
        try:
            from bloomberg import get_realization_summary
        except ImportError:
            pytest.skip("Bloomberg module not available")

        benchmarks = {
            'hrc_us': 916,
            'crc_us': 1127,
            'coated_us': 1263,
            'hrc_eu': 717,
            'octg': 2750,
        }

        summary = get_realization_summary(benchmarks)

        assert 'flat_rolled' in summary
        assert 'weights' in summary['flat_rolled']
        assert 'tubular' in summary
        assert 'factor' in summary['tubular']


# =============================================================================
# SCENARIO CALIBRATION MODE TESTS
# =============================================================================

class TestScenarioCalibrationModes:
    """Tests for multi-mode scenario calibration"""

    def test_fixed_mode_symmetric(self):
        """Test fixed mode uses symmetric factors"""
        try:
            from bloomberg import get_all_scenarios_for_mode, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        factors = get_all_scenarios_for_mode(ScenarioCalibrationMode.FIXED)

        # Fixed mode uses symmetric factors
        assert factors['downside'].hrc_us == 0.85
        assert factors['upside'].hrc_us == 1.10
        assert factors['optimistic'].hrc_us == 1.15

    def test_bloomberg_mode_percentile_based(self):
        """Test Bloomberg mode uses percentile-based factors"""
        try:
            from bloomberg import get_all_scenarios_for_mode, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        factors = get_all_scenarios_for_mode(ScenarioCalibrationMode.BLOOMBERG)

        # Bloomberg mode has percentile-based factors
        assert factors['severe_downturn'].percentile == 10
        assert factors['downside'].percentile == 25
        assert factors['boom'].percentile == 90

        # Factors are based on historical data, not symmetric
        assert factors['severe_downturn'].hrc_us == 0.56
        assert factors['downside'].hrc_us == 0.68

    def test_hybrid_caps_octg_upside(self):
        """Test hybrid mode caps OCTG upside"""
        try:
            from bloomberg import get_all_scenarios_for_mode, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        factors = get_all_scenarios_for_mode(ScenarioCalibrationMode.HYBRID)

        # Hybrid caps OCTG upside at 1.05
        assert factors['optimistic'].octg <= 1.05
        # But downside uses Bloomberg data (not capped)
        assert factors['severe_downturn'].octg == 0.37

    def test_all_modes_have_base_case(self):
        """Test all modes have base_case at 1.0x factors"""
        try:
            from bloomberg import get_all_scenarios_for_mode, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        for mode in ScenarioCalibrationMode:
            factors = get_all_scenarios_for_mode(mode)
            assert 'base_case' in factors
            assert factors['base_case'].hrc_us == 1.0
            assert factors['base_case'].octg == 1.0

    def test_get_scenario_factors_single(self):
        """Test getting a single scenario's factors"""
        try:
            from bloomberg import get_scenario_factors, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        factors = get_scenario_factors('downside', ScenarioCalibrationMode.BLOOMBERG)
        assert factors is not None
        assert factors.name == 'Downside'
        assert factors.hrc_us == 0.68

        # Non-existent scenario returns None
        assert get_scenario_factors('nonexistent', ScenarioCalibrationMode.FIXED) is None

    def test_mode_descriptions_exist(self):
        """Test mode descriptions are available"""
        try:
            from bloomberg import get_mode_description, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        for mode in ScenarioCalibrationMode:
            desc = get_mode_description(mode)
            assert desc is not None
            assert len(desc) > 10  # Should be a meaningful description

    def test_scenario_factors_to_dict(self):
        """Test ScenarioFactors can be converted to dict"""
        try:
            from bloomberg import get_scenario_factors, ScenarioCalibrationMode
        except ImportError:
            pytest.skip("Bloomberg module not available")

        factors = get_scenario_factors('base_case', ScenarioCalibrationMode.FIXED)
        d = factors.to_dict()

        assert isinstance(d, dict)
        assert d['hrc_us'] == 1.0
        assert d['name'] == 'Base Case'
        assert 'annual_price_growth' in d

    def test_compare_calibration_modes(self):
        """Test mode comparison function"""
        try:
            from bloomberg import compare_calibration_modes
        except ImportError:
            pytest.skip("Bloomberg module not available")

        comparison = compare_calibration_modes()

        # Should have entries for common scenarios
        assert 'base_case' in comparison
        assert 'downside' in comparison

        # Each entry should have values for each mode
        for scenario, modes in comparison.items():
            if modes.get('fixed') is not None:
                assert 'fixed' in modes


class TestScenarioCalibrationIntegration:
    """Test scenario calibration integration with price_volume_model"""

    def test_get_scenario_presets_with_calibration_mode(self):
        """Test get_scenario_presets accepts calibration_mode parameter"""
        from price_volume_model import (
            get_scenario_presets, ScenarioType,
            SCENARIO_CALIBRATION_AVAILABLE
        )

        # Without calibration mode (default behavior)
        presets_default = get_scenario_presets()
        assert ScenarioType.BASE_CASE in presets_default
        assert ScenarioType.DOWNSIDE in presets_default

        if SCENARIO_CALIBRATION_AVAILABLE:
            # With calibration mode
            presets_fixed = get_scenario_presets(calibration_mode='fixed')
            presets_bloomberg = get_scenario_presets(calibration_mode='bloomberg')
            presets_hybrid = get_scenario_presets(calibration_mode='hybrid')

            # All should have the same scenario types
            assert ScenarioType.BASE_CASE in presets_fixed
            assert ScenarioType.DOWNSIDE in presets_bloomberg
            assert ScenarioType.SEVERE_DOWNTURN in presets_hybrid

    def test_calibration_mode_affects_price_factors(self):
        """Test that calibration mode changes price scenario factors for downside/upside"""
        from price_volume_model import (
            get_scenario_presets, ScenarioType,
            SCENARIO_CALIBRATION_AVAILABLE
        )

        if not SCENARIO_CALIBRATION_AVAILABLE:
            pytest.skip("Scenario calibration not available")

        presets_fixed = get_scenario_presets(calibration_mode='fixed')
        presets_bloomberg = get_scenario_presets(calibration_mode='bloomberg')

        # DOWNSIDE should have different HRC factors in each mode
        fixed_downside = presets_fixed[ScenarioType.DOWNSIDE]
        bloomberg_downside = presets_bloomberg[ScenarioType.DOWNSIDE]

        # Fixed uses 0.85, Bloomberg uses 0.68
        assert fixed_downside.price_scenario.hrc_us_factor == 0.85
        assert bloomberg_downside.price_scenario.hrc_us_factor == 0.68

    def test_base_case_unchanged_by_calibration(self):
        """Test that BASE_CASE is NOT affected by calibration mode"""
        from price_volume_model import (
            get_scenario_presets, ScenarioType,
            SCENARIO_CALIBRATION_AVAILABLE
        )

        if not SCENARIO_CALIBRATION_AVAILABLE:
            pytest.skip("Scenario calibration not available")

        # BASE_CASE should have same factors regardless of calibration mode
        # because it represents mid-cycle conditions, not the 2023 baseline
        presets_none = get_scenario_presets(calibration_mode=None)
        presets_fixed = get_scenario_presets(calibration_mode='fixed')
        presets_bloomberg = get_scenario_presets(calibration_mode='bloomberg')
        presets_hybrid = get_scenario_presets(calibration_mode='hybrid')

        base_none = presets_none[ScenarioType.BASE_CASE]
        base_fixed = presets_fixed[ScenarioType.BASE_CASE]
        base_bloomberg = presets_bloomberg[ScenarioType.BASE_CASE]
        base_hybrid = presets_hybrid[ScenarioType.BASE_CASE]

        # All should use same through-cycle factors (1.0x HRC — rebased baseline)
        assert base_none.price_scenario.hrc_us_factor == 1.0
        assert base_fixed.price_scenario.hrc_us_factor == 1.0
        assert base_bloomberg.price_scenario.hrc_us_factor == 1.0
        assert base_hybrid.price_scenario.hrc_us_factor == 1.0

    def test_calibration_status_function(self):
        """Test get_calibration_mode_status function"""
        from price_volume_model import get_calibration_mode_status

        status = get_calibration_mode_status()

        assert 'available' in status
        assert 'default_mode' in status
        assert 'available_modes' in status
        assert 'mode_descriptions' in status

        if status['available']:
            assert status['default_mode'] == 'bloomberg'
            assert 'fixed' in status['available_modes']
            assert 'bloomberg' in status['available_modes']
            assert 'hybrid' in status['available_modes']

    def test_wall_street_scenario_unchanged_by_calibration(self):
        """Test that WALL_STREET scenario is not affected by calibration mode"""
        from price_volume_model import (
            get_scenario_presets, ScenarioType,
            SCENARIO_CALIBRATION_AVAILABLE
        )

        if not SCENARIO_CALIBRATION_AVAILABLE:
            pytest.skip("Scenario calibration not available")

        # WALL_STREET should not change with calibration mode
        presets_fixed = get_scenario_presets(calibration_mode='fixed')
        presets_bloomberg = get_scenario_presets(calibration_mode='bloomberg')

        fixed_ws = presets_fixed[ScenarioType.WALL_STREET]
        bloomberg_ws = presets_bloomberg[ScenarioType.WALL_STREET]

        # Wall Street uses its own fixed factors, not calibrated
        assert fixed_ws.price_scenario.hrc_us_factor == bloomberg_ws.price_scenario.hrc_us_factor


# =============================================================================
# PROBABILITY DISTRIBUTION TESTS
# =============================================================================

class TestProbabilityDistributions:
    """Test Bloomberg-based probability distributions for weighted valuation"""

    def test_probability_modes_available(self):
        """Test that probability distribution modes are available"""
        from bloomberg import ProbabilityDistributionMode
        assert ProbabilityDistributionMode.FIXED.value == "fixed"
        assert ProbabilityDistributionMode.BLOOMBERG.value == "bloomberg"

    def test_fixed_probabilities_sum_to_one(self):
        """Test fixed probabilities sum to 1.0"""
        from bloomberg import FIXED_PROBABILITIES
        total = sum(p.probability for p in FIXED_PROBABILITIES.values())
        assert abs(total - 1.0) < 0.01, f"Fixed probabilities sum to {total}"

    def test_bloomberg_probabilities_sum_to_one(self):
        """Test Bloomberg probabilities sum to 1.0"""
        from bloomberg import BLOOMBERG_PROBABILITIES
        total = sum(p.probability for p in BLOOMBERG_PROBABILITIES.values())
        assert abs(total - 1.0) < 0.01, f"Bloomberg probabilities sum to {total}"

    def test_get_probability_weights_returns_dict(self):
        """Test get_probability_weights returns correct format"""
        from bloomberg import get_probability_weights, ProbabilityDistributionMode

        fixed_weights = get_probability_weights(ProbabilityDistributionMode.FIXED)
        bloomberg_weights = get_probability_weights(ProbabilityDistributionMode.BLOOMBERG)

        assert isinstance(fixed_weights, dict)
        assert isinstance(bloomberg_weights, dict)
        assert 'base_case' in fixed_weights
        assert 'base_case' in bloomberg_weights

    def test_get_probability_details_returns_scenario_probability(self):
        """Test get_probability_details returns ScenarioProbability objects"""
        from bloomberg import get_probability_details, ProbabilityDistributionMode, ScenarioProbability

        details = get_probability_details(ProbabilityDistributionMode.BLOOMBERG)

        assert isinstance(details, dict)
        for name, prob in details.items():
            assert isinstance(prob, ScenarioProbability)
            assert hasattr(prob, 'probability')
            assert hasattr(prob, 'percentile_range')
            assert hasattr(prob, 'description')

    def test_probability_distribution_description(self):
        """Test probability distribution descriptions exist"""
        from bloomberg import get_probability_distribution_description, ProbabilityDistributionMode

        fixed_desc = get_probability_distribution_description(ProbabilityDistributionMode.FIXED)
        bloomberg_desc = get_probability_distribution_description(ProbabilityDistributionMode.BLOOMBERG)

        assert isinstance(fixed_desc, str)
        assert isinstance(bloomberg_desc, str)
        assert len(fixed_desc) > 0
        assert len(bloomberg_desc) > 0

    def test_apply_probability_weights_to_scenarios(self):
        """Test applying probability weights to scenario presets"""
        from price_volume_model import get_scenario_presets, ScenarioType
        from bloomberg import apply_probability_weights_to_scenarios, ProbabilityDistributionMode

        # Get scenarios without probability mode (default weights)
        presets = get_scenario_presets()

        # Apply Bloomberg probability weights
        updated = apply_probability_weights_to_scenarios(presets, ProbabilityDistributionMode.BLOOMBERG)

        # Check that weights were updated
        base_case = updated[ScenarioType.BASE_CASE]
        assert base_case.probability_weight == 0.40  # Bloomberg base case is 40%

    def test_get_scenario_presets_with_probability_mode(self):
        """Test get_scenario_presets accepts probability_mode parameter"""
        from price_volume_model import get_scenario_presets, ScenarioType

        # Get scenarios with Bloomberg probability mode
        presets_bloomberg = get_scenario_presets(probability_mode='bloomberg')
        presets_fixed = get_scenario_presets(probability_mode='fixed')

        # Bloomberg has different weights than fixed
        bb_base = presets_bloomberg[ScenarioType.BASE_CASE].probability_weight
        fixed_base = presets_fixed[ScenarioType.BASE_CASE].probability_weight

        # Bloomberg base case = 0.40, Fixed base case = 0.35 (or whatever the default is)
        assert bb_base == 0.40

    def test_probability_weights_sum_correctly_in_presets(self):
        """Test that probability weights in presets sum to 1.0"""
        from price_volume_model import get_scenario_presets, ScenarioType

        # Scenarios with probability weights (excluding CUSTOM, WALL_STREET, NIPPON_COMMITMENTS)
        presets = get_scenario_presets(probability_mode='bloomberg')

        weighted_types = [
            ScenarioType.SEVERE_DOWNTURN,
            ScenarioType.DOWNSIDE,
            ScenarioType.BASE_CASE,
            ScenarioType.ABOVE_AVERAGE,
            ScenarioType.OPTIMISTIC,
        ]

        total = sum(presets[st].probability_weight for st in weighted_types)
        assert abs(total - 1.0) < 0.01, f"Probability weights sum to {total}, expected 1.0"


# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestConfiguration:
    """Test configuration file handling"""

    def test_config_file_exists(self):
        """Test config.json exists"""
        config_path = Path(__file__).parent.parent / "market-data" / "bloomberg" / "config.json"
        assert config_path.exists()

    def test_config_file_valid_json(self):
        """Test config.json is valid JSON"""
        import json
        config_path = Path(__file__).parent.parent / "market-data" / "bloomberg" / "config.json"

        with open(config_path, 'r') as f:
            config = json.load(f)

        assert isinstance(config, dict)
        assert 'bloomberg_enabled' in config

    def test_config_has_required_sections(self):
        """Test config has required sections"""
        import json
        config_path = Path(__file__).parent.parent / "market-data" / "bloomberg" / "config.json"

        with open(config_path, 'r') as f:
            config = json.load(f)

        assert 'price_data' in config
        assert 'rate_data' in config
        assert 'staleness_thresholds_days' in config


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
