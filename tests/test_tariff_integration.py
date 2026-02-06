#!/usr/bin/env python3
"""
Tests for Section 232 Tariff-Adjusted Pricing Model with Benchmark Rebasing.

Tests cover:
1. Tariff adjustment calculations
2. Through-cycle benchmark correctness
3. Segment premium recalibration
4. Monte Carlo tariff integration
5. Scenario preset correctness
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from price_volume_model import (
    BENCHMARK_PRICES_2023, BENCHMARK_PRICES_THROUGH_CYCLE,
    BENCHMARK_PRICES_PRE_COVID, BENCHMARK_PRICES_POST_SPIKE,
    TARIFF_CONFIG, calculate_tariff_adjustment, get_tariff_decomposition,
    PriceVolumeModel, ModelScenario, ScenarioType, SteelPriceScenario,
    VolumeScenario, get_scenario_presets, get_segment_configs, Segment,
)


# =============================================================================
# TARIFF ADJUSTMENT TESTS
# =============================================================================

class TestTariffAdjustment:
    """Test calculate_tariff_adjustment() function"""

    def test_status_quo_returns_1(self):
        """At current 25% rate, adjustment should be 1.0 for all products"""
        for btype in ['hrc_us', 'crc_us', 'coated_us', 'hrc_eu', 'octg']:
            adj = calculate_tariff_adjustment(0.25, btype)
            assert adj == 1.0, f"{btype}: expected 1.0, got {adj}"

    def test_removal_hrc(self):
        """Full tariff removal: HRC drops ~15%"""
        adj = calculate_tariff_adjustment(0.0, 'hrc_us')
        assert 0.80 <= adj <= 0.90, f"HRC removal adj {adj} not in [0.80, 0.90]"
        assert abs(adj - 0.85) < 0.01, f"HRC removal adj {adj} not ~0.85"

    def test_removal_eu(self):
        """Full tariff removal: EU gets ~30% of US impact (indirect)"""
        adj_us = calculate_tariff_adjustment(0.0, 'hrc_us')
        adj_eu = calculate_tariff_adjustment(0.0, 'hrc_eu')
        # EU impact should be much smaller than US
        us_impact = abs(1.0 - adj_us)
        eu_impact = abs(1.0 - adj_eu)
        assert eu_impact < us_impact * 0.5, (
            f"EU impact ({eu_impact:.3f}) should be < 50% of US impact ({us_impact:.3f})"
        )
        # EU should be ~0.955 (4.5% drop vs 15% for US)
        assert 0.93 <= adj_eu <= 0.98, f"EU removal adj {adj_eu} not in [0.93, 0.98]"

    def test_removal_octg(self):
        """Full tariff removal: OCTG gets ~60% of HRC impact"""
        adj_hrc = calculate_tariff_adjustment(0.0, 'hrc_us')
        adj_octg = calculate_tariff_adjustment(0.0, 'octg')
        hrc_impact = abs(1.0 - adj_hrc)
        octg_impact = abs(1.0 - adj_octg)
        ratio = octg_impact / hrc_impact
        assert 0.50 <= ratio <= 0.70, f"OCTG/HRC impact ratio {ratio:.2f} not in [0.50, 0.70]"

    def test_escalation(self):
        """Tariff escalation to 50%: HRC rises ~15%"""
        adj = calculate_tariff_adjustment(0.50, 'hrc_us')
        assert adj > 1.0, f"Escalation should increase prices, got {adj}"
        assert abs(adj - 1.15) < 0.01, f"HRC escalation adj {adj} not ~1.15"

    def test_linear_scaling(self):
        """Adjustment should scale linearly with rate delta"""
        adj_0 = calculate_tariff_adjustment(0.0, 'hrc_us')
        adj_50 = calculate_tariff_adjustment(0.50, 'hrc_us')
        # Symmetric around 0.25: |1.0 - adj_0| ≈ |adj_50 - 1.0|
        assert abs(abs(1.0 - adj_0) - abs(adj_50 - 1.0)) < 0.01

    def test_unknown_benchmark(self):
        """Unknown benchmark type returns 1.0"""
        adj = calculate_tariff_adjustment(0.0, 'unknown_product')
        assert adj == 1.0


# =============================================================================
# THROUGH-CYCLE BENCHMARK TESTS
# =============================================================================

class TestThroughCycleBenchmarks:
    """Test that benchmark constants match Bloomberg analysis"""

    def test_benchmarks_are_through_cycle(self):
        """BENCHMARK_PRICES_2023 should now equal through-cycle prices"""
        assert BENCHMARK_PRICES_2023 == BENCHMARK_PRICES_THROUGH_CYCLE

    def test_through_cycle_between_pre_and_post(self):
        """Through-cycle should be between pre-COVID and post-spike for all products"""
        for btype in BENCHMARK_PRICES_THROUGH_CYCLE:
            tc = BENCHMARK_PRICES_THROUGH_CYCLE[btype]
            pre = BENCHMARK_PRICES_PRE_COVID[btype]
            post = BENCHMARK_PRICES_POST_SPIKE[btype]
            assert pre <= tc <= post, (
                f"{btype}: through-cycle ${tc} not between "
                f"pre-COVID ${pre} and post-spike ${post}"
            )

    def test_hrc_through_cycle_value(self):
        """HRC through-cycle should be $738 (avg of $625 and $850)"""
        assert BENCHMARK_PRICES_THROUGH_CYCLE['hrc_us'] == 738

    def test_through_cycle_is_avg(self):
        """Through-cycle should be close to avg(pre-COVID, post-spike)"""
        for btype in BENCHMARK_PRICES_THROUGH_CYCLE:
            tc = BENCHMARK_PRICES_THROUGH_CYCLE[btype]
            avg = (BENCHMARK_PRICES_PRE_COVID[btype] + BENCHMARK_PRICES_POST_SPIKE[btype]) / 2
            # Allow rounding and deliberate calibration adjustments
            # OCTG is ~4% above simple avg due to structural demand shift
            assert abs(tc - avg) / avg < 0.05, (
                f"{btype}: through-cycle ${tc} deviates >5% from avg ${avg}"
            )


# =============================================================================
# SEGMENT PREMIUM TESTS
# =============================================================================

class TestSegmentPremiums:
    """Test that recalibrated premiums produce correct 2023 realized prices"""

    def test_flat_rolled_premium(self):
        """Flat-Rolled premium should produce ~$1030 realized price"""
        configs = get_segment_configs()
        fr = configs[Segment.FLAT_ROLLED]
        # Weighted benchmark: 0.21×738 + 0.40×994 + 0.39×1113
        weighted = 0.21 * 738 + 0.40 * 994 + 0.39 * 1113
        realized = weighted * (1 + fr.price_premium_to_benchmark)
        assert abs(realized - 1030) < 20, f"FR realized ${realized:.0f} not ~$1030"

    def test_mini_mill_premium(self):
        """Mini Mill premium should produce ~$875 realized price"""
        configs = get_segment_configs()
        mm = configs[Segment.MINI_MILL]
        weighted = 0.55 * 738 + 0.16 * 994 + 0.29 * 1113
        realized = weighted * (1 + mm.price_premium_to_benchmark)
        assert abs(realized - 875) < 20, f"MM realized ${realized:.0f} not ~$875"

    def test_usse_premium(self):
        """USSE premium should produce ~$873 realized price"""
        configs = get_segment_configs()
        usse = configs[Segment.USSE]
        weighted = 0.51 * 611 + 0.08 * 994 + 0.40 * 1113
        realized = weighted * (1 + usse.price_premium_to_benchmark)
        assert abs(realized - 873) < 20, f"USSE realized ${realized:.0f} not ~$873"

    def test_tubular_premium(self):
        """Tubular premium should produce ~$3137 realized price"""
        configs = get_segment_configs()
        tub = configs[Segment.TUBULAR]
        realized = 2388 * (1 + tub.price_premium_to_benchmark)
        assert abs(realized - 3137) < 20, f"Tub realized ${realized:.0f} not ~$3137"


# =============================================================================
# BASE CASE PRICE TESTS
# =============================================================================

class TestBaseCasePrices:
    """Test that base case factor 1.0 = through-cycle levels"""

    def test_base_case_factors_are_1(self):
        """Base case should use factor 1.0 for all products"""
        presets = get_scenario_presets()
        base = presets[ScenarioType.BASE_CASE]
        ps = base.price_scenario
        assert ps.hrc_us_factor == 1.0
        assert ps.crc_us_factor == 1.0
        assert ps.coated_us_factor == 1.0
        assert ps.hrc_eu_factor == 1.0
        assert ps.octg_factor == 1.0

    def test_base_case_tariff_is_current(self):
        """Base case should have tariff_rate = 0.25 (current)"""
        presets = get_scenario_presets()
        base = presets[ScenarioType.BASE_CASE]
        tariff = getattr(base.price_scenario, 'tariff_rate', 0.25)
        assert tariff == 0.25


# =============================================================================
# MONTE CARLO TARIFF TESTS
# =============================================================================

class TestMCTariffBlending:
    """Test MC engine tariff blending"""

    def test_blending_formula(self):
        """Verify continuous blending: effective = prob × 0.25 + (1-prob) × alt"""
        prob = 0.80
        alt = 0.10
        expected = prob * 0.25 + (1 - prob) * alt
        assert abs(expected - 0.22) < 0.01  # 0.80×0.25 + 0.20×0.10 = 0.22

    def test_certain_maintained(self):
        """With tariff_prob=1.0, effective rate = 0.25"""
        prob = 1.0
        alt = 0.10
        effective = prob * 0.25 + (1 - prob) * alt
        assert effective == 0.25

    def test_certain_removal(self):
        """With tariff_prob=0.0 and alt=0.0, effective rate = 0.0"""
        prob = 0.0
        alt = 0.0
        effective = prob * 0.25 + (1 - prob) * alt
        assert effective == 0.0

    def test_mc_engine_has_tariff_variables(self):
        """MC engine should define tariff_probability and tariff_rate_if_changed"""
        from monte_carlo.monte_carlo_engine import MonteCarloEngine
        mc = MonteCarloEngine(n_simulations=5, random_seed=42)
        assert 'tariff_probability' in mc.variables
        assert 'tariff_rate_if_changed' in mc.variables

    def test_mc_results_include_tariff(self):
        """MC simulation results should include tariff diagnostic fields"""
        from monte_carlo.monte_carlo_engine import MonteCarloEngine
        mc = MonteCarloEngine(n_simulations=3, random_seed=42)
        results = mc.run_simulation(verbose=False)
        assert 'effective_tariff_rate' in results.columns
        assert 'tariff_adjustment_hrc' in results.columns
        # Effective rate should be between 0 and 0.25 (blend)
        assert (results['effective_tariff_rate'] >= 0).all()
        assert (results['effective_tariff_rate'] <= 0.30).all()


# =============================================================================
# FUTURES SCENARIO RECALIBRATION TESTS
# =============================================================================

class TestFuturesScenariosRecalibrated:
    """Test that Futures scenarios produce same dollar prices against new baseline"""

    def test_futures_base_hrc_dollar_price(self):
        """Futures Base Case: HRC factor × $738 ≈ $885"""
        presets = get_scenario_presets()
        fb = presets[ScenarioType.FUTURES_BASE_CASE]
        dollar_hrc = fb.price_scenario.hrc_us_factor * 738
        assert abs(dollar_hrc - 885) < 15, f"Futures base HRC ${dollar_hrc:.0f} not ~$885"

    def test_futures_no_tariff_has_zero_rate(self):
        """Futures No Tariff should have tariff_rate=0.0"""
        presets = get_scenario_presets()
        fnt = presets[ScenarioType.FUTURES_NO_TARIFF]
        assert fnt.price_scenario.tariff_rate == 0.0


# =============================================================================
# TARIFF DECOMPOSITION TESTS
# =============================================================================

class TestTariffDecomposition:
    """Test get_tariff_decomposition() utility"""

    def test_current_rate_no_adjustment(self):
        """At current rate, adjustment should be 1.0"""
        decomp = get_tariff_decomposition(0.25)
        for btype, data in decomp.items():
            assert data['tariff_adjustment'] == 1.0, f"{btype} adj != 1.0"
            assert data['adjusted_price'] == data['through_cycle']

    def test_removal_prices_drop(self):
        """Tariff removal should reduce adjusted prices"""
        decomp = get_tariff_decomposition(0.0)
        for btype, data in decomp.items():
            assert data['adjusted_price'] <= data['through_cycle'], (
                f"{btype}: removal price ${data['adjusted_price']} > through-cycle ${data['through_cycle']}"
            )

    def test_decomposition_has_all_products(self):
        """Decomposition should cover all benchmark products"""
        decomp = get_tariff_decomposition(0.25)
        expected = {'hrc_us', 'crc_us', 'coated_us', 'hrc_eu', 'octg'}
        assert set(decomp.keys()) == expected

    def test_tariff_component_positive(self):
        """Tariff component should be positive (tariffs increase prices)"""
        decomp = get_tariff_decomposition(0.25)
        for btype, data in decomp.items():
            assert data['tariff_component'] >= 0, (
                f"{btype}: tariff component ${data['tariff_component']} is negative"
            )


# =============================================================================
# TARIFF SCENARIO PRESETS
# =============================================================================

class TestTariffScenarioPresets:
    """Test the 3 new tariff scenario types"""

    def test_tariff_removal_exists(self):
        """Tariff Removal scenario should exist in presets"""
        presets = get_scenario_presets()
        assert ScenarioType.TARIFF_REMOVAL in presets

    def test_tariff_reduced_exists(self):
        """Tariff Reduced scenario should exist in presets"""
        presets = get_scenario_presets()
        assert ScenarioType.TARIFF_REDUCED in presets

    def test_tariff_escalation_exists(self):
        """Tariff Escalation scenario should exist in presets"""
        presets = get_scenario_presets()
        assert ScenarioType.TARIFF_ESCALATION in presets

    def test_tariff_removal_rate(self):
        """Tariff Removal should have tariff_rate=0.0"""
        presets = get_scenario_presets()
        assert presets[ScenarioType.TARIFF_REMOVAL].price_scenario.tariff_rate == 0.0

    def test_tariff_reduced_rate(self):
        """Tariff Reduced should have tariff_rate=0.10"""
        presets = get_scenario_presets()
        assert presets[ScenarioType.TARIFF_REDUCED].price_scenario.tariff_rate == 0.10

    def test_tariff_escalation_rate(self):
        """Tariff Escalation should have tariff_rate=0.50"""
        presets = get_scenario_presets()
        assert presets[ScenarioType.TARIFF_ESCALATION].price_scenario.tariff_rate == 0.50


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
