"""
Bloomberg Data Integration Module
=================================

Provides integration with Bloomberg market data for the USS/Nippon Steel model.

Features:
- Dynamic benchmark prices from current market data
- WACC overlay with current Treasury yields and credit spreads
- Monte Carlo calibration with fitted distributions
- Correlation matrix for simulation
- Graceful fallbacks when Bloomberg data unavailable

Usage:
    from market_data.bloomberg import get_bloomberg_service

    # Check availability
    if is_bloomberg_available():
        service = get_bloomberg_service()

        # Get current prices
        prices = service.get_current_prices()

        # Get current rates
        rates = service.get_current_rates()

        # Get data status
        status = service.get_status()

For price integration:
    from market_data.bloomberg import get_current_benchmark_prices

    prices = get_current_benchmark_prices()  # Returns dict or None

For WACC overlay:
    from market_data.bloomberg import get_wacc_overlay

    overlay = get_wacc_overlay()  # Returns WACCBloombergOverlay or None

For Monte Carlo calibration:
    from market_data.bloomberg import get_calibrated_distributions

    distributions = get_calibrated_distributions()  # Returns dict or None
"""

# Core service
from .bloomberg_data_service import (
    BloombergDataService,
    get_bloomberg_service,
    reset_bloomberg_service,
    is_bloomberg_available,
    DataFreshness,
    TimeSeriesStats,
    DatasetInfo,
)

# Price calibration
from .price_calibrator import (
    get_current_benchmark_prices,
    get_latest_benchmark_prices,
    get_scenario_price_factors,
    compare_current_to_historical,
    get_price_comparison_table,
    DEFAULT_BENCHMARK_PRICES,
    BLOOMBERG_BENCHMARK_PRICES_2023,
)

# WACC overlay
from .wacc_updater import (
    WACCBloombergOverlay,
    get_wacc_overlay,
    calculate_beta_from_stock_data,
    compare_to_verified_inputs,
    generate_wacc_overlay_report,
)

# Monte Carlo calibration
from .monte_carlo_calibrator import (
    get_calibrated_distributions,
    get_calibrated_correlation_matrix,
    calibrate_steel_price_distributions,
    export_for_monte_carlo_engine,
)

# Price realization mapping
from .price_realization_mapper import (
    SegmentRealizationFactors,
    DEFAULT_REALIZATION_FACTORS,
    estimate_segment_realizations,
    forecast_realizations_with_change,
    get_realization_summary,
    validate_realization_factors,
    USS_2023_REALIZED_PRICES,
)

# Scenario calibration modes
from .scenario_calibrator import (
    ScenarioCalibrationMode,
    ScenarioFactors,
    get_scenario_factors,
    get_all_scenarios_for_mode,
    get_scenario_names_for_mode,
    recalculate_bloomberg_factors,
    get_mode_description,
    get_mode_short_description,
    compare_calibration_modes,
    FIXED_FACTORS,
    BLOOMBERG_FACTORS,
    HYBRID_FACTORS,
    # Probability distributions
    ProbabilityDistributionMode,
    ScenarioProbability,
    get_probability_weights,
    get_probability_details,
    get_probability_distribution_description,
    apply_probability_weights_to_scenarios,
    FIXED_PROBABILITIES,
    BLOOMBERG_PROBABILITIES,
)

__all__ = [
    # Core service
    'BloombergDataService',
    'get_bloomberg_service',
    'reset_bloomberg_service',
    'is_bloomberg_available',
    'DataFreshness',
    'TimeSeriesStats',
    'DatasetInfo',
    # Price calibration
    'get_current_benchmark_prices',
    'get_scenario_price_factors',
    'compare_current_to_historical',
    'get_price_comparison_table',
    # WACC overlay
    'WACCBloombergOverlay',
    'get_wacc_overlay',
    'calculate_beta_from_stock_data',
    'compare_to_verified_inputs',
    'generate_wacc_overlay_report',
    # Monte Carlo
    'get_calibrated_distributions',
    'get_calibrated_correlation_matrix',
    'calibrate_steel_price_distributions',
    'export_for_monte_carlo_engine',
    # Price realization mapping
    'SegmentRealizationFactors',
    'DEFAULT_REALIZATION_FACTORS',
    'estimate_segment_realizations',
    'forecast_realizations_with_change',
    'get_realization_summary',
    'validate_realization_factors',
    'USS_2023_REALIZED_PRICES',
    # Scenario calibration modes
    'ScenarioCalibrationMode',
    'ScenarioFactors',
    'get_scenario_factors',
    'get_all_scenarios_for_mode',
    'get_scenario_names_for_mode',
    'recalculate_bloomberg_factors',
    'get_mode_description',
    'get_mode_short_description',
    'compare_calibration_modes',
    'FIXED_FACTORS',
    'BLOOMBERG_FACTORS',
    'HYBRID_FACTORS',
    # Probability distributions
    'ProbabilityDistributionMode',
    'ScenarioProbability',
    'get_probability_weights',
    'get_probability_details',
    'get_probability_distribution_description',
    'apply_probability_weights_to_scenarios',
    'FIXED_PROBABILITIES',
    'BLOOMBERG_PROBABILITIES',
]

__version__ = '1.0.0'
