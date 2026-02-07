#!/usr/bin/env python3
"""
Scenario Calibrator
===================
Provides three calibration modes for price scenario factors:
- FIXED: Hardcoded symmetric factors (current behavior)
- BLOOMBERG: Full percentile-based factors from historical data
- HYBRID: Bloomberg downside with conservative capped upside

Usage:
    from bloomberg import ScenarioCalibrationMode, get_scenario_factors, get_all_scenarios_for_mode

    # Get all scenarios for a mode
    factors = get_all_scenarios_for_mode(ScenarioCalibrationMode.BLOOMBERG)

    # Get a specific scenario
    downturn = get_scenario_factors('severe_downturn', ScenarioCalibrationMode.HYBRID)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

try:
    from .bloomberg_data_service import get_bloomberg_service, is_bloomberg_available
except ImportError:
    # For standalone execution
    from bloomberg_data_service import get_bloomberg_service, is_bloomberg_available


class ScenarioCalibrationMode(Enum):
    """Scenario calibration approach"""
    FIXED = "fixed"           # Hardcoded ±15% symmetric
    BLOOMBERG = "bloomberg"   # Full percentile-based
    HYBRID = "hybrid"         # Bloomberg downside, capped upside


@dataclass
class ScenarioFactors:
    """Price factors for a scenario.

    All factors are multipliers relative to the 2023 annual average baseline.
    A factor of 1.0 means "same as 2023 average", 0.85 means "15% below", etc.

    Attributes:
        name: Human-readable scenario name
        hrc_us: HRC US price factor (e.g., 0.85 = 15% below baseline)
        crc_us: CRC US price factor
        coated_us: Coated US price factor
        hrc_eu: HRC EU price factor
        octg: OCTG price factor
        annual_price_growth: Annual price growth rate (e.g., 0.01 = 1%)
        description: Brief description of the scenario
        percentile: Historical percentile this scenario represents (for documentation)
    """
    name: str
    hrc_us: float
    crc_us: float
    coated_us: float
    hrc_eu: float
    octg: float
    annual_price_growth: float
    description: str
    percentile: Optional[int] = None  # For documentation

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'hrc_us': self.hrc_us,
            'crc_us': self.crc_us,
            'coated_us': self.coated_us,
            'hrc_eu': self.hrc_eu,
            'octg': self.octg,
            'annual_price_growth': self.annual_price_growth,
            'description': self.description,
            'percentile': self.percentile,
        }


# =============================================================================
# OPTION A: FIXED FACTORS (recalibrated based on 2024-2025 actuals)
# =============================================================================
# BASELINE: YE 2023 annual averages (HRC $916, CRC $1,127, EU $717, OCTG $2,750)
# FACTORS: Recalibrated based on actual 2024-2025 Bloomberg data vs 2023 baseline
#
# Key observations from 2024-2025 actuals:
# - CRC held up better than HRC (+5-7% relative performance)
# - EU HRC underperformed US HRC by ~5-10%
# - OCTG 2023 was an energy-cycle peak; 2024-2025 ran at ~0.66-0.75x of 2023
FIXED_FACTORS = {
    'severe_downturn': ScenarioFactors(
        name='Severe Downturn',
        hrc_us=0.70,       # $641/ton - crisis levels
        crc_us=0.75,       # CRC more resilient than HRC
        coated_us=0.75,    # Follows CRC
        hrc_eu=0.60,       # EU hit harder in downturns ($430/ton)
        octg=0.40,         # $1,100/ton - energy bust (vs $2,750 baseline)
        annual_price_growth=-0.02,
        description='Crisis (2009/2015/2020 levels)',
        percentile=None
    ),
    'downside': ScenarioFactors(
        name='Downside',
        hrc_us=0.85,       # $779/ton - matched 2024 actual ($775)
        crc_us=0.91,       # CRC premium (2024 actual was 0.96x)
        coated_us=0.91,    # Follows CRC
        hrc_eu=0.78,       # EU underperformed (2024 actual 0.88x)
        octg=0.66,         # $1,815/ton - matched 2024 actual ($1,813)
        annual_price_growth=0.00,
        description='Weak markets (calibrated to 2024 actuals)',
        percentile=None
    ),
    'base_case': ScenarioFactors(
        name='Base Case',
        hrc_us=0.94,       # $861/ton - matched 2025 actual ($861)
        crc_us=0.94,       # CRC similar to HRC in stable markets
        coated_us=0.94,    # Follows CRC
        hrc_eu=0.84,       # EU structurally weaker (2025 actual 0.84x)
        octg=0.76,         # $2,090/ton - mid-cycle (2025 actual $2,060)
        annual_price_growth=0.01,
        description='Mid-cycle (calibrated to 2025 actuals)',
        percentile=50
    ),
    'upside': ScenarioFactors(
        name='Upside',
        hrc_us=1.00,       # Return to 2023 levels
        crc_us=1.02,       # CRC slight premium
        coated_us=1.02,    # Follows CRC
        hrc_eu=0.92,       # EU lags US even in upside
        octg=0.90,         # $2,475/ton - strong but below 2023 peak
        annual_price_growth=0.015,
        description='Strong markets',
        percentile=None
    ),
    'optimistic': ScenarioFactors(
        name='Optimistic',
        hrc_us=1.10,       # Above 2023 levels
        crc_us=1.12,       # CRC premium maintained
        coated_us=1.12,    # Follows CRC
        hrc_eu=1.00,       # EU reaches 2023 parity
        octg=1.00,         # $2,750/ton - back to 2023 peak
        annual_price_growth=0.02,
        description='Boom conditions',
        percentile=None
    ),
}


# =============================================================================
# OPTION B: FULL BLOOMBERG PERCENTILE FACTORS (recalibrated based on 2024-2025 actuals)
# =============================================================================
# BASELINE: YE 2023 annual averages (HRC $916, CRC $1,127, EU $717, OCTG $2,750)
# FACTORS: Data-driven from Bloomberg historical percentiles, adjusted for:
# - CRC resilience vs HRC (+5-7%)
# - EU structural underperformance (-5-10% vs US)
# - OCTG normalization from 2023 energy-cycle peak
BLOOMBERG_FACTORS = {
    'severe_downturn': ScenarioFactors(
        name='Severe Downturn',
        hrc_us=0.56,       # P10: $513/ton
        crc_us=0.64,       # P10: $721/ton
        coated_us=0.64,    # Follows CRC
        hrc_eu=0.50,       # EU hit harder: $359/ton
        octg=0.36,         # $990/ton - energy bust (vs $2,750 baseline)
        annual_price_growth=-0.02,
        description='P10 crisis (2009/2015/2020)',
        percentile=10
    ),
    'downside': ScenarioFactors(
        name='Downside',
        hrc_us=0.68,       # P25: $623/ton
        crc_us=0.75,       # CRC resilience: $845/ton
        coated_us=0.75,    # Follows CRC
        hrc_eu=0.62,       # EU weaker: $445/ton
        octg=0.50,         # $1,375/ton - weak energy
        annual_price_growth=0.00,
        description='P25 recession',
        percentile=25
    ),
    'modest_decline': ScenarioFactors(
        name='Modest Decline',
        hrc_us=0.79,       # P50: $724/ton
        crc_us=0.86,       # CRC premium: $969/ton
        coated_us=0.86,    # Follows CRC
        hrc_eu=0.72,       # EU lags: $516/ton
        octg=0.62,         # $1,705/ton
        annual_price_growth=0.00,
        description='P50 median',
        percentile=50
    ),
    'base_case': ScenarioFactors(
        name='Base Case',
        hrc_us=0.94,       # $861/ton - calibrated to 2025 actual
        crc_us=0.94,       # $1,059/ton
        coated_us=0.94,    # Follows CRC
        hrc_eu=0.84,       # EU weaker: $602/ton (2025 actual $603)
        octg=0.76,         # $2,090/ton - mid-cycle (2025 actual $2,060)
        annual_price_growth=0.01,
        description='Mid-cycle (calibrated to 2025 actuals)',
        percentile=None
    ),
    'upside': ScenarioFactors(
        name='Upside',
        hrc_us=1.00,       # P75: $916/ton (2023 level)
        crc_us=1.03,       # CRC premium: $1,161/ton
        coated_us=1.03,    # Follows CRC
        hrc_eu=0.92,       # EU lags: $660/ton
        octg=0.90,         # $2,475/ton
        annual_price_growth=0.015,
        description='P75 strong',
        percentile=75
    ),
    'boom': ScenarioFactors(
        name='Boom',
        hrc_us=1.40,       # P90: $1,282/ton
        crc_us=1.46,       # CRC premium: $1,645/ton
        coated_us=1.46,    # Follows CRC
        hrc_eu=1.10,       # EU lags: $789/ton
        octg=1.20,         # $3,300/ton - near 2022 peaks
        annual_price_growth=0.02,
        description='P90 shortage',
        percentile=90
    ),
}


# =============================================================================
# OPTION C: HYBRID (Bloomberg downside, capped upside)
# =============================================================================
# BASELINE: YE 2023 annual averages (HRC $916, CRC $1,127, EU $717, OCTG $2,750)
# Conservative approach for board presentations:
# - Uses Bloomberg percentiles for downside (data-driven risk)
# - Caps upside to avoid overly optimistic projections
# - CRC premium reflects observed resilience vs HRC
# - EU discount reflects structural underperformance
# - OCTG upside capped (doesn't assume 2023 energy boom repeats)
HYBRID_FACTORS = {
    'severe_downturn': ScenarioFactors(
        name='Severe Downturn',
        hrc_us=0.56,       # P10: $513/ton
        crc_us=0.64,       # CRC resilience: $721/ton
        coated_us=0.64,    # Follows CRC
        hrc_eu=0.50,       # EU hit harder: $359/ton
        octg=0.36,         # $990/ton - energy bust
        annual_price_growth=-0.02,
        description='P10 from Bloomberg',
        percentile=10
    ),
    'downside': ScenarioFactors(
        name='Downside',
        hrc_us=0.68,       # P25: $623/ton
        crc_us=0.75,       # CRC premium: $845/ton
        coated_us=0.75,    # Follows CRC
        hrc_eu=0.62,       # EU weaker: $445/ton
        octg=0.50,         # $1,375/ton
        annual_price_growth=0.00,
        description='P25 from Bloomberg',
        percentile=25
    ),
    'base_case': ScenarioFactors(
        name='Base Case',
        hrc_us=0.94,       # $861/ton (2025 actual)
        crc_us=0.94,       # $1,059/ton
        coated_us=0.94,    # Follows CRC
        hrc_eu=0.84,       # $602/ton (2025 actual $603)
        octg=0.76,         # $2,090/ton (2025 actual $2,060)
        annual_price_growth=0.01,
        description='Mid-cycle (calibrated to 2025 actuals)',
        percentile=None
    ),
    'modest_upside': ScenarioFactors(
        name='Modest Upside',
        hrc_us=1.00,       # $916/ton - return to 2023
        crc_us=1.02,       # CRC slight premium
        coated_us=1.02,    # Follows CRC
        hrc_eu=0.92,       # EU lags: $660/ton
        octg=0.85,         # $2,338/ton (capped below 2023)
        annual_price_growth=0.015,
        description='Strong markets (capped upside)',
        percentile=None
    ),
    'optimistic': ScenarioFactors(
        name='Optimistic',
        hrc_us=1.10,       # $1,008/ton
        crc_us=1.12,       # CRC premium: $1,262/ton
        coated_us=1.12,    # Follows CRC
        hrc_eu=1.00,       # EU reaches 2023 parity
        octg=0.95,         # $2,613/ton (capped - no 2022 repeat)
        annual_price_growth=0.02,
        description='Boom (capped upside)',
        percentile=None
    ),
}


# =============================================================================
# PUBLIC API
# =============================================================================

def get_scenario_factors(
    scenario_name: str,
    mode: ScenarioCalibrationMode = ScenarioCalibrationMode.BLOOMBERG
) -> Optional[ScenarioFactors]:
    """
    Get scenario factors for the specified calibration mode.

    Args:
        scenario_name: e.g., 'severe_downturn', 'downside', 'base_case'
        mode: FIXED, BLOOMBERG, or HYBRID

    Returns:
        ScenarioFactors or None if not found

    Example:
        >>> factors = get_scenario_factors('downside', ScenarioCalibrationMode.HYBRID)
        >>> print(f"HRC factor: {factors.hrc_us:.2f}x")
        HRC factor: 0.68x
    """
    factor_map = {
        ScenarioCalibrationMode.FIXED: FIXED_FACTORS,
        ScenarioCalibrationMode.BLOOMBERG: BLOOMBERG_FACTORS,
        ScenarioCalibrationMode.HYBRID: HYBRID_FACTORS,
    }
    return factor_map[mode].get(scenario_name)


def get_all_scenarios_for_mode(
    mode: ScenarioCalibrationMode = ScenarioCalibrationMode.BLOOMBERG
) -> Dict[str, ScenarioFactors]:
    """
    Get all scenarios for a calibration mode.

    Args:
        mode: FIXED, BLOOMBERG, or HYBRID

    Returns:
        Dict mapping scenario names to ScenarioFactors

    Example:
        >>> factors = get_all_scenarios_for_mode(ScenarioCalibrationMode.FIXED)
        >>> for name, f in factors.items():
        ...     print(f"{name}: {f.hrc_us:.2f}x")
    """
    factor_map = {
        ScenarioCalibrationMode.FIXED: FIXED_FACTORS,
        ScenarioCalibrationMode.BLOOMBERG: BLOOMBERG_FACTORS,
        ScenarioCalibrationMode.HYBRID: HYBRID_FACTORS,
    }
    return factor_map[mode].copy()


def get_scenario_names_for_mode(
    mode: ScenarioCalibrationMode = ScenarioCalibrationMode.BLOOMBERG
) -> list:
    """
    Get list of scenario names available for a mode.

    Useful for populating dropdowns/selectors.

    Args:
        mode: FIXED, BLOOMBERG, or HYBRID

    Returns:
        List of scenario name strings
    """
    return list(get_all_scenarios_for_mode(mode).keys())


def recalculate_bloomberg_factors() -> Dict[str, ScenarioFactors]:
    """
    Dynamically recalculate Bloomberg factors from current data.

    Call this when Bloomberg data is refreshed to update factors.
    Returns updated BLOOMBERG_FACTORS dict (does not modify global).

    Note: This is a placeholder for dynamic recalculation.
    In practice, the percentile-based factors are pre-computed and
    stored in the BLOOMBERG_FACTORS constant above.

    Returns:
        Dict of scenario factors calculated from current Bloomberg data,
        or the static BLOOMBERG_FACTORS if Bloomberg is unavailable.
    """
    if not is_bloomberg_available():
        return BLOOMBERG_FACTORS.copy()

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return BLOOMBERG_FACTORS.copy()

        baseline = service.get_annual_average_prices(2023)
        if not baseline:
            return BLOOMBERG_FACTORS.copy()

        # Get percentile values for each product
        new_factors = {}

        # Calculate factors for each scenario percentile
        percentile_scenarios = [
            ('severe_downturn', 10),
            ('downside', 25),
            ('modest_decline', 50),
            ('upside', 75),
            ('boom', 90),
        ]

        for scenario_name, pct in percentile_scenarios:
            # Get percentile prices from Bloomberg stats
            hrc_stats = service.get_price_stats('hrc_us')
            crc_stats = service.get_price_stats('crc_us')
            hrc_eu_stats = service.get_price_stats('hrc_eu')
            octg_stats = service.get_price_stats('octg_us')

            # Calculate factors relative to 2023 baseline
            hrc_pct_val = getattr(hrc_stats, f'percentile_{pct}', None)
            crc_pct_val = getattr(crc_stats, f'percentile_{pct}', None)
            hrc_eu_pct_val = getattr(hrc_eu_stats, f'percentile_{pct}', None)
            octg_pct_val = getattr(octg_stats, f'percentile_{pct}', None)

            if all([hrc_pct_val, crc_pct_val, hrc_eu_pct_val, octg_pct_val]):
                # Use static factors as fallback for growth rate
                static = BLOOMBERG_FACTORS.get(scenario_name, BLOOMBERG_FACTORS['base_case'])

                new_factors[scenario_name] = ScenarioFactors(
                    name=static.name,
                    hrc_us=hrc_pct_val / baseline['hrc_us'],
                    crc_us=crc_pct_val / baseline['crc_us'],
                    coated_us=crc_pct_val / baseline['crc_us'],  # Derive from CRC
                    hrc_eu=hrc_eu_pct_val / baseline['hrc_eu'],
                    octg=octg_pct_val / baseline['octg'],
                    annual_price_growth=static.annual_price_growth,
                    description=f'P{pct} from Bloomberg (recalculated)',
                    percentile=pct
                )

        # Always include base case
        new_factors['base_case'] = BLOOMBERG_FACTORS['base_case']

        return new_factors

    except Exception:
        return BLOOMBERG_FACTORS.copy()


# =============================================================================
# PROBABILITY DISTRIBUTIONS
# =============================================================================

class ProbabilityDistributionMode(Enum):
    """Probability distribution approach for scenario weighting"""
    FIXED = "fixed"           # Hardcoded symmetric weights (current behavior)
    BLOOMBERG = "bloomberg"   # Derived from historical percentile frequency


@dataclass
class ScenarioProbability:
    """Probability weight for a scenario with documentation."""
    scenario_type: str        # e.g., 'severe_downturn', 'downside', 'base_case'
    probability: float        # 0.0 to 1.0
    percentile_range: str     # e.g., 'P0-P10', 'P10-P25'
    description: str          # Human-readable explanation


# Option A: Fixed probabilities (current hardcoded approach)
# Symmetric distribution centered on base case
FIXED_PROBABILITIES = {
    'severe_downturn': ScenarioProbability(
        'severe_downturn', 0.10, 'N/A',
        'Fixed 10% - severe recession/crisis'
    ),
    'downside': ScenarioProbability(
        'downside', 0.25, 'N/A',
        'Fixed 25% - below-average conditions'
    ),
    'base_case': ScenarioProbability(
        'base_case', 0.35, 'N/A',
        'Fixed 35% - mid-cycle/normal conditions'
    ),
    'above_average': ScenarioProbability(
        'above_average', 0.20, 'N/A',
        'Fixed 20% - above-average conditions'
    ),
    'optimistic': ScenarioProbability(
        'optimistic', 0.10, 'N/A',
        'Fixed 10% - boom/strong growth'
    ),
}


# Option B: Bloomberg-derived probabilities
# Based on historical percentile analysis of steel prices
# Key insight: 2023 was an ELEVATED year (~P75 historically)
# This means downside scenarios are MORE likely than symmetric weights suggest
BLOOMBERG_PROBABILITIES = {
    'severe_downturn': ScenarioProbability(
        'severe_downturn', 0.10, 'P0-P10',
        'Historical crisis levels (2009, 2015, 2020)'
    ),
    'downside': ScenarioProbability(
        'downside', 0.20, 'P10-P30',
        'Recession/weak demand (below P30)'
    ),
    'base_case': ScenarioProbability(
        'base_case', 0.40, 'P30-P70',
        'Mid-cycle conditions (P30-P70 range)'
    ),
    'above_average': ScenarioProbability(
        'above_average', 0.20, 'P70-P90',
        'Strong markets (P70-P90 range)'
    ),
    'optimistic': ScenarioProbability(
        'optimistic', 0.10, 'P90-P100',
        'Boom/shortage conditions (above P90)'
    ),
}


def get_probability_weights(
    mode: ProbabilityDistributionMode = ProbabilityDistributionMode.BLOOMBERG
) -> Dict[str, float]:
    """
    Get probability weights for scenarios.

    Args:
        mode: FIXED or BLOOMBERG

    Returns:
        Dict mapping scenario names to probability weights (sum to 1.0)
    """
    prob_map = {
        ProbabilityDistributionMode.FIXED: FIXED_PROBABILITIES,
        ProbabilityDistributionMode.BLOOMBERG: BLOOMBERG_PROBABILITIES,
    }
    probs = prob_map[mode]
    return {name: p.probability for name, p in probs.items()}


def get_probability_details(
    mode: ProbabilityDistributionMode = ProbabilityDistributionMode.BLOOMBERG
) -> Dict[str, ScenarioProbability]:
    """
    Get full probability details including percentile ranges and descriptions.

    Args:
        mode: FIXED or BLOOMBERG

    Returns:
        Dict mapping scenario names to ScenarioProbability objects
    """
    prob_map = {
        ProbabilityDistributionMode.FIXED: FIXED_PROBABILITIES,
        ProbabilityDistributionMode.BLOOMBERG: BLOOMBERG_PROBABILITIES,
    }
    return prob_map[mode].copy()


def get_probability_distribution_description(mode: ProbabilityDistributionMode) -> str:
    """Get human-readable description of probability distribution mode."""
    descriptions = {
        ProbabilityDistributionMode.FIXED: "Fixed symmetric weights (traditional approach)",
        ProbabilityDistributionMode.BLOOMBERG: "Bloomberg historical percentiles (data-driven)",
    }
    return descriptions[mode]


def apply_probability_weights_to_scenarios(
    scenarios: Dict,
    probability_mode: ProbabilityDistributionMode = ProbabilityDistributionMode.BLOOMBERG
) -> Dict:
    """
    Apply probability weights from the specified mode to a dict of scenarios.

    This modifies the probability_weight attribute of each ModelScenario.

    Args:
        scenarios: Dict of ScenarioType -> ModelScenario
        probability_mode: FIXED or BLOOMBERG

    Returns:
        Modified scenarios dict with updated probability weights
    """
    weights = get_probability_weights(probability_mode)

    # Map ScenarioType values to probability keys
    # The scenario names in weights are lowercase with underscores
    type_to_weight_key = {
        'Severe Downturn': 'severe_downturn',
        'Downside': 'downside',
        'Base Case': 'base_case',
        'Above Average': 'above_average',
        'Optimistic': 'optimistic',
        # Handle variations
        'Severe Downturn (Historical Crisis)': 'severe_downturn',
        'Downside (Weak Markets)': 'downside',
        'Base Case (Mid-Cycle)': 'base_case',
        'Above Average (Strong Cycle)': 'above_average',
        'Optimistic (Sustained Growth)': 'optimistic',
    }

    for scenario_type, scenario in scenarios.items():
        # Try to match by scenario type value first
        weight_key = type_to_weight_key.get(scenario_type.value)

        if weight_key and weight_key in weights:
            scenario.probability_weight = weights[weight_key]
        else:
            # Scenarios like WALL_STREET, NIPPON_COMMITMENTS stay at 0
            pass

    return scenarios


def get_mode_description(mode: ScenarioCalibrationMode) -> str:
    """
    Get human-readable description of calibration mode.

    Args:
        mode: The calibration mode

    Returns:
        Description string suitable for UI display
    """
    descriptions = {
        ScenarioCalibrationMode.FIXED: "Fixed ±15% symmetric factors (simple, stable)",
        ScenarioCalibrationMode.BLOOMBERG: "Full Bloomberg percentiles (data-driven, volatile)",
        ScenarioCalibrationMode.HYBRID: "Bloomberg downside, capped upside (conservative)",
    }
    return descriptions[mode]


def get_mode_short_description(mode: ScenarioCalibrationMode) -> str:
    """
    Get short description for dropdown display.

    Args:
        mode: The calibration mode

    Returns:
        Short description string
    """
    descriptions = {
        ScenarioCalibrationMode.FIXED: "Fixed (±15%)",
        ScenarioCalibrationMode.BLOOMBERG: "Full Bloomberg",
        ScenarioCalibrationMode.HYBRID: "Hybrid (Conservative)",
    }
    return descriptions[mode]


def compare_calibration_modes() -> Dict[str, Dict[str, float]]:
    """
    Compare HRC US factors across all calibration modes.

    Useful for displaying comparison tables in dashboards.

    Returns:
        Dict mapping scenario names to dict of mode -> factor
    """
    result = {}

    # Get all unique scenario names across modes
    all_scenarios = set()
    for mode in ScenarioCalibrationMode:
        all_scenarios.update(get_scenario_names_for_mode(mode))

    for scenario in sorted(all_scenarios):
        result[scenario] = {}
        for mode in ScenarioCalibrationMode:
            factors = get_scenario_factors(scenario, mode)
            if factors:
                result[scenario][mode.value] = factors.hrc_us
            else:
                result[scenario][mode.value] = None

    return result


# =============================================================================
# DEMO / CLI
# =============================================================================

if __name__ == '__main__':
    print("Scenario Calibration Modes")
    print("=" * 60)

    for mode in ScenarioCalibrationMode:
        print(f"\n{mode.value.upper()}: {get_mode_description(mode)}")
        print("-" * 60)

        factors = get_all_scenarios_for_mode(mode)
        print(f"{'Scenario':<20} {'HRC':>8} {'CRC':>8} {'OCTG':>8} {'Desc'}")
        print("-" * 60)

        for name, f in factors.items():
            print(f"{name:<20} {f.hrc_us:>7.2f}x {f.crc_us:>7.2f}x {f.octg:>7.2f}x  {f.description}")

    # Comparison table
    print("\n\nHRC US Factors by Mode:")
    print("=" * 60)
    print(f"{'Scenario':<20} {'Fixed':>10} {'Bloomberg':>12} {'Hybrid':>10}")
    print("-" * 60)

    comparison = compare_calibration_modes()
    for scenario, modes in comparison.items():
        fixed = f"{modes.get('fixed', 0):.2f}x" if modes.get('fixed') else "-"
        bb = f"{modes.get('bloomberg', 0):.2f}x" if modes.get('bloomberg') else "-"
        hybrid = f"{modes.get('hybrid', 0):.2f}x" if modes.get('hybrid') else "-"
        print(f"{scenario:<20} {fixed:>10} {bb:>12} {hybrid:>10}")
