#!/usr/bin/env python3
"""
Price x Volume DCF Model: USS / Nippon Steel Merger Analysis
=============================================================

Enhanced model that derives revenue from steel prices and shipment volumes,
enabling scenario analysis based on steel market conditions.

Key Features:
- Price x Volume revenue derivation by segment
- Steel price scenarios (HRC, CRC, Coated, OCTG benchmarks)
- Volume scenarios (capacity utilization, demand cycles)
- Pre-built scenario presets (Severe Downturn, Downside, Base Case, Above Average, Optimistic, Wall Street, Nippon Commitments)
- IRP-adjusted WACC for cross-border valuation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import pandas as pd
import numpy as np

# =============================================================================
# OPTIONAL WACC MODULE INTEGRATION
# =============================================================================

# Try to import the wacc-calculations module for verified WACC inputs
# Falls back gracefully if module is not available
try:
    import sys
    from pathlib import Path
    # Add wacc-calculations to path for imports
    _wacc_module_path = Path(__file__).parent / "wacc-calculations"
    if str(_wacc_module_path) not in sys.path:
        sys.path.insert(0, str(_wacc_module_path))

    from uss.uss_wacc import calculate_uss_wacc, USSWACCResult
    from nippon.nippon_wacc import calculate_nippon_wacc, NipponWACCResult
    WACC_MODULE_AVAILABLE = True
except ImportError:
    WACC_MODULE_AVAILABLE = False
    USSWACCResult = None
    NipponWACCResult = None


def get_verified_uss_wacc() -> Tuple[Optional[float], Optional[dict]]:
    """
    Load verified USS WACC from wacc-calculations module.

    Returns:
        Tuple of (wacc_value, audit_dict) if module available,
        (None, None) otherwise.
    """
    if not WACC_MODULE_AVAILABLE:
        return None, None

    try:
        result = calculate_uss_wacc()
        audit_trail = result.get_audit_trail()
        return result.wacc, audit_trail
    except Exception as e:
        print(f"Warning: Failed to load verified USS WACC: {e}")
        return None, None


def get_verified_nippon_wacc() -> Tuple[Optional[float], Optional[float], Optional[dict]]:
    """
    Load verified Nippon WACC from wacc-calculations module.

    Returns:
        Tuple of (jpy_wacc, usd_wacc, audit_dict) if module available,
        (None, None, None) otherwise.
    """
    if not WACC_MODULE_AVAILABLE:
        return None, None, None

    try:
        result = calculate_nippon_wacc()
        audit_trail = result.get_audit_trail()
        return result.jpy_wacc, result.usd_wacc, audit_trail
    except Exception as e:
        print(f"Warning: Failed to load verified Nippon WACC: {e}")
        return None, None, None


def get_wacc_module_status() -> dict:
    """
    Get status of WACC module integration.

    Returns dict with module availability and current values.
    """
    status = {
        'available': WACC_MODULE_AVAILABLE,
        'uss_wacc': None,
        'nippon_jpy_wacc': None,
        'nippon_usd_wacc': None,
        'data_as_of_date': None,
    }

    if WACC_MODULE_AVAILABLE:
        uss_wacc, uss_audit = get_verified_uss_wacc()
        jpy_wacc, usd_wacc, nippon_audit = get_verified_nippon_wacc()

        status['uss_wacc'] = uss_wacc
        status['nippon_jpy_wacc'] = jpy_wacc
        status['nippon_usd_wacc'] = usd_wacc

        if uss_audit:
            status['data_as_of_date'] = uss_audit.get('data_as_of_date')

    return status


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class Segment(Enum):
    FLAT_ROLLED = "Flat-Rolled"
    MINI_MILL = "Mini Mill"
    USSE = "USSE"
    TUBULAR = "Tubular"


class ScenarioType(Enum):
    SEVERE_DOWNTURN = "Severe Downturn"
    DOWNSIDE = "Downside"
    BASE_CASE = "Base Case"
    ABOVE_AVERAGE = "Above Average"
    WALL_STREET = "Wall Street Consensus"
    OPTIMISTIC = "Optimistic"
    NIPPON_COMMITMENTS = "NSA Mandated CapEx"
    CUSTOM = "Custom"
    # Legacy names for backward compatibility
    CONSERVATIVE = "Downside"  # Alias for DOWNSIDE
    MANAGEMENT = "Optimistic"  # Alias for OPTIMISTIC
    # Futures Model scenarios (post-COVID, 50% tariff regime)
    FUTURES_DOWNSIDE = "Futures: Downside"
    FUTURES_BASE_CASE = "Futures: Base Case"
    FUTURES_ABOVE_AVERAGE = "Futures: Above Average"
    FUTURES_OPTIMISTIC = "Futures: Optimistic"
    FUTURES_NO_TARIFF = "Futures: No Tariff"
    # Tariff scenario types (use base factors with varying tariff_rate)
    TARIFF_REMOVAL = "Tariff Removal"
    TARIFF_REDUCED = "Tariff Reduced"
    TARIFF_ESCALATION = "Tariff Escalation"


# Steel price benchmarks ($/ton) - hardcoded fallbacks (used only if Bloomberg unavailable)
_HARDCODED_BENCHMARK_PRICES = {
    'hrc_us': 680,      # US HRC Midwest (rough 2023 average)
    'crc_us': 850,      # US CRC
    'coated_us': 950,   # US Coated/Galvanized
    'hrc_eu': 620,      # EU HRC
    'octg': 2800,       # OCTG (Oil Country Tubular Goods)
}

# Through-cycle benchmark prices ($/ton) — Avg(Pre-COVID median, Post-Spike H2 2022+ median)
# These represent structural equilibrium, not 2023 elevated levels
BENCHMARK_PRICES_THROUGH_CYCLE = {
    'hrc_us': 738,      # Pre-COVID ~$625, Post-Spike ~$850, avg = $738
    'crc_us': 994,      # Pre-COVID ~$820, Post-Spike ~$1130, avg = $994  (CRC 35% premium to HRC)
    'coated_us': 1113,  # Pre-COVID ~$920, Post-Spike ~$1266, avg = $1113 (Coated 51% premium to HRC)
    'hrc_eu': 611,      # Pre-COVID ~$512, Post-Spike ~$710, avg = $611
    'octg': 2388,       # Pre-COVID ~$1350, Post-Spike ~$3228, avg = $2388 (OCTG 3.2x HRC)
}

# Reference: period-specific medians for decomposition
BENCHMARK_PRICES_PRE_COVID = {
    'hrc_us': 625, 'crc_us': 820, 'coated_us': 920, 'hrc_eu': 512, 'octg': 1350,
}
BENCHMARK_PRICES_POST_SPIKE = {
    'hrc_us': 850, 'crc_us': 1130, 'coated_us': 1266, 'hrc_eu': 710, 'octg': 3228,
}

# Section 232 Tariff Configuration
# OLS: ln(HRC) includes 0.0685 binary tariff coefficient → exp(0.0685) = +7.1% direct effect
# Empirical: Pre-tariff $610 → Post-tariff $720 = +18% total effect (includes indirect/sentiment)
# Model uses conservative 15% for HRC (between OLS 7% and empirical 18%)
TARIFF_CONFIG = {
    'current_rate': 0.25,             # Section 232: 25% on steel imports
    'ols_coefficient': 0.0685,        # Binary 0/1 in OLS regression
    'empirical_uplift_hrc': 0.18,     # Bloomberg: pre-tariff $610 -> post-tariff $720 = +18%
    'model_uplift_hrc': 0.15,         # Conservative: between OLS (7%) and empirical (18%)
    'us_products': ['hrc_us', 'crc_us', 'coated_us'],
    'eu_indirect_share': 0.30,        # EU gets ~30% of US tariff uplift (trade diversion)
    'octg_share': 0.60,               # OCTG gets ~60% of HRC uplift (separate trade dynamics)
}


# =============================================================================
# BLOOMBERG INTEGRATION
# =============================================================================

# Bloomberg data service provides year-end 2023 prices by default
# This matches the effective date of the DCF analysis
BLOOMBERG_AVAILABLE = False
BENCHMARK_PRICES_2023_BLOOMBERG = None  # Year-end 2023 prices from Bloomberg
BENCHMARK_PRICES_CURRENT = None         # Latest prices from Bloomberg

try:
    import sys
    from pathlib import Path as BloombergPath
    _bloomberg_module_path = BloombergPath(__file__).parent / "market-data" / "bloomberg"
    if str(_bloomberg_module_path.parent) not in sys.path:
        sys.path.insert(0, str(_bloomberg_module_path.parent))

    from bloomberg import get_bloomberg_service, is_bloomberg_available

    if is_bloomberg_available():
        _service = get_bloomberg_service()
        if _service.is_available():
            # Load year-end 2023 prices (matches analysis effective date)
            BENCHMARK_PRICES_2023_BLOOMBERG = _service.get_benchmark_prices_2023()
            # Also load current prices for comparison
            BENCHMARK_PRICES_CURRENT = _service.get_current_prices()
            BLOOMBERG_AVAILABLE = True
except ImportError:
    pass
except Exception as e:
    print(f"Warning: Failed to load Bloomberg prices: {e}")

# Scenario Calibration Mode integration
SCENARIO_CALIBRATION_AVAILABLE = False
ScenarioCalibrationMode = None
ProbabilityDistributionMode = None
_scenario_calibrator_funcs = {}
try:
    from bloomberg import (
        ScenarioCalibrationMode,
        get_scenario_factors,
        get_all_scenarios_for_mode,
        get_mode_description,
        get_mode_short_description,
        compare_calibration_modes,
        # Probability distributions
        ProbabilityDistributionMode,
        get_probability_weights,
        get_probability_details,
        get_probability_distribution_description,
        apply_probability_weights_to_scenarios,
    )
    _scenario_calibrator_funcs = {
        'get_scenario_factors': get_scenario_factors,
        'get_all_scenarios_for_mode': get_all_scenarios_for_mode,
        'get_mode_description': get_mode_description,
        'get_mode_short_description': get_mode_short_description,
        'compare_calibration_modes': compare_calibration_modes,
        'get_probability_weights': get_probability_weights,
        'get_probability_details': get_probability_details,
        'get_probability_distribution_description': get_probability_distribution_description,
        'apply_probability_weights_to_scenarios': apply_probability_weights_to_scenarios,
    }
    SCENARIO_CALIBRATION_AVAILABLE = True
except ImportError:
    pass


def get_calibration_mode_status() -> dict:
    """
    Get status of scenario calibration mode integration.

    Returns dict with:
        - available: bool, whether calibration modes are available
        - default_mode: str, the default mode (usually 'bloomberg')
        - available_modes: list of available mode strings
        - mode_descriptions: dict mapping mode to description
        - probability_modes: list of available probability distribution modes
        - probability_descriptions: dict mapping mode to description
    """
    status = {
        'available': SCENARIO_CALIBRATION_AVAILABLE,
        'default_mode': 'bloomberg' if SCENARIO_CALIBRATION_AVAILABLE else None,
        'available_modes': [],
        'mode_descriptions': {},
        'probability_modes': [],
        'probability_descriptions': {},
    }

    if SCENARIO_CALIBRATION_AVAILABLE:
        status['available_modes'] = ['fixed', 'bloomberg', 'hybrid']
        status['mode_descriptions'] = {
            'fixed': get_mode_description(ScenarioCalibrationMode.FIXED),
            'bloomberg': get_mode_description(ScenarioCalibrationMode.BLOOMBERG),
            'hybrid': get_mode_description(ScenarioCalibrationMode.HYBRID),
        }
        status['probability_modes'] = ['fixed', 'bloomberg']
        status['probability_descriptions'] = {
            'fixed': get_probability_distribution_description(ProbabilityDistributionMode.FIXED),
            'bloomberg': get_probability_distribution_description(ProbabilityDistributionMode.BLOOMBERG),
        }

    return status

# Model default: through-cycle baseline (not 2023 elevated levels)
# Factor 1.0 = through-cycle normal; 2023 = ~1.24x (recognized as elevated)
# Bloomberg 2023 prices stored separately for reference/decomposition
BENCHMARK_PRICES_2023 = BENCHMARK_PRICES_THROUGH_CYCLE.copy()
_DEFAULT_BENCHMARK_PRICES = BENCHMARK_PRICES_THROUGH_CYCLE.copy()

# Store Bloomberg 2023 prices for reference if available
if BLOOMBERG_AVAILABLE and BENCHMARK_PRICES_2023_BLOOMBERG:
    _BLOOMBERG_2023_REFERENCE = BENCHMARK_PRICES_2023_BLOOMBERG.copy()
else:
    _BLOOMBERG_2023_REFERENCE = _HARDCODED_BENCHMARK_PRICES.copy()


def get_benchmark_prices(use_bloomberg: bool = True, use_current: bool = False,
                         use_through_cycle: bool = True) -> Dict[str, float]:
    """
    Get benchmark prices for model calculations.

    By default, returns through-cycle baseline prices (structural equilibrium).
    Can also return Bloomberg 2023 or current prices for reference.

    Args:
        use_bloomberg: If True (default), use Bloomberg data when available.
        use_current: If True, return latest/current prices instead of baseline.
        use_through_cycle: If True (default), return through-cycle baseline.
                          If False, return Bloomberg 2023 or hardcoded fallback.

    Returns:
        Dict with benchmark prices (hrc_us, crc_us, coated_us, hrc_eu, octg)
    """
    if use_through_cycle:
        return BENCHMARK_PRICES_THROUGH_CYCLE.copy()
    if use_bloomberg and BLOOMBERG_AVAILABLE:
        if use_current and BENCHMARK_PRICES_CURRENT:
            return BENCHMARK_PRICES_CURRENT.copy()
        elif BENCHMARK_PRICES_2023_BLOOMBERG:
            return BENCHMARK_PRICES_2023_BLOOMBERG.copy()
    return _HARDCODED_BENCHMARK_PRICES.copy()


def get_bloomberg_status() -> dict:
    """
    Get status of Bloomberg data integration.

    Returns dict with availability, freshness, and prices.
    """
    status = {
        'available': BLOOMBERG_AVAILABLE,
        'prices_2023': None,
        'prices_current': None,
        'hardcoded_prices': _HARDCODED_BENCHMARK_PRICES.copy(),
        'analysis_effective_date': '2023-12-29',
        'freshness': 'unavailable',
    }

    if BLOOMBERG_AVAILABLE:
        status['prices_2023'] = BENCHMARK_PRICES_2023_BLOOMBERG.copy() if BENCHMARK_PRICES_2023_BLOOMBERG else None
        status['prices_current'] = BENCHMARK_PRICES_CURRENT.copy() if BENCHMARK_PRICES_CURRENT else None

        try:
            from bloomberg import get_bloomberg_service
            service = get_bloomberg_service()
            full_status = service.get_status()
            status['freshness'] = full_status.get('overall_status', 'unknown')
            data_date = service.get_data_as_of_date()
            if data_date:
                status['data_as_of_date'] = data_date.isoformat()
        except Exception:
            pass

    return status


# =============================================================================
# TARIFF ADJUSTMENT FUNCTIONS
# =============================================================================

def calculate_tariff_adjustment(tariff_rate: float, benchmark_type: str) -> float:
    """Multiplicative price adjustment for tariff rate vs embedded rate (0.25).

    The through-cycle baseline already embeds current 25% Section 232 tariffs.
    This function returns a multiplicative adjustment when tariff_rate differs
    from the embedded 0.25.

    Uses conservative empirical uplift (15% for HRC US) rather than just the
    OLS coefficient (7%), since the OLS underestimates total market impact.

    Args:
        tariff_rate: Effective Section 232 tariff rate (0.0-1.0)
        benchmark_type: Product key ('hrc_us', 'crc_us', etc.)

    Returns:
        Multiplicative price adjustment factor (1.0 = no change from baseline)
    """
    embedded_rate = TARIFF_CONFIG['current_rate']  # 0.25
    if abs(tariff_rate - embedded_rate) < 0.001:
        return 1.0

    hrc_uplift = TARIFF_CONFIG['model_uplift_hrc']  # 0.15

    # Scale uplift by product type
    if benchmark_type in TARIFF_CONFIG['us_products']:
        # US flat-rolled: full uplift
        full_uplift = hrc_uplift
    elif benchmark_type == 'hrc_eu':
        # EU: indirect effect (trade diversion)
        full_uplift = hrc_uplift * TARIFF_CONFIG['eu_indirect_share']
    elif benchmark_type == 'octg':
        # OCTG: partial (separate trade dynamics)
        full_uplift = hrc_uplift * TARIFF_CONFIG['octg_share']
    else:
        return 1.0

    # Linear scaling: full removal (0.0) = -full_uplift; double (0.50) = +full_uplift
    # At embedded rate (0.25): adjustment = 0 → factor = 1.0
    rate_delta = (tariff_rate - embedded_rate) / embedded_rate
    adjustment = full_uplift * rate_delta

    return 1.0 + adjustment


def get_tariff_decomposition(tariff_rate: float = 0.25) -> Dict[str, Dict[str, float]]:
    """Decompose price into tariff vs fundamental components per benchmark.

    Returns dict keyed by benchmark type with:
    - through_cycle: baseline price (embeds current tariff)
    - pre_tariff: estimated pre-tariff price
    - tariff_component: dollar amount attributable to tariff
    - tariff_adjustment: multiplicative factor for given tariff_rate
    - adjusted_price: price at given tariff_rate

    Args:
        tariff_rate: Section 232 tariff rate to analyze

    Returns:
        Dict of decomposition per benchmark type
    """
    result = {}
    for btype, base_price in BENCHMARK_PRICES_THROUGH_CYCLE.items():
        adj = calculate_tariff_adjustment(tariff_rate, btype)
        # Estimate pre-tariff price (what price would be without any tariff)
        no_tariff_adj = calculate_tariff_adjustment(0.0, btype)
        pre_tariff_price = base_price * no_tariff_adj

        result[btype] = {
            'through_cycle': base_price,
            'pre_tariff_est': round(pre_tariff_price, 0),
            'tariff_component': round(base_price - pre_tariff_price, 0),
            'tariff_pct_of_price': round((base_price - pre_tariff_price) / base_price * 100, 1),
            'tariff_adjustment': round(adj, 4),
            'adjusted_price': round(base_price * adj, 0),
        }
    return result


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SegmentVolumePrice:
    """Volume and price assumptions for a segment"""
    name: str

    # 2023 Base volumes (000 tons)
    base_shipments_2023: float

    # Volume growth assumptions
    volume_growth_rate: float  # Annual volume growth
    capacity_utilization_2023: float
    max_capacity_utilization: float  # Ceiling on utilization

    # 2023 Base realized price ($/ton)
    base_price_2023: float

    # Price assumptions
    price_growth_rate: float  # Annual price inflation
    price_premium_to_benchmark: float  # Premium/discount to benchmark
    benchmark_type: str  # Primary benchmark (for backward compatibility)

    # Cost structure
    ebitda_margin_at_base_price: float  # EBITDA margin at 2023 price level
    margin_sensitivity_to_price: float  # How much margin changes per $100 price change

    # Other segment parameters
    da_pct_of_revenue: float
    maintenance_capex_pct: float
    dso: float
    dih: float
    dpo: float

    # Product mix for weighted-average pricing (based on 2023 10-K revenue data)
    # Keys: 'hrc_us', 'crc_us', 'coated_us', 'hrc_eu', 'octg'
    # Values: weight (0.0-1.0), must sum to 1.0
    # Optional - if empty, falls back to benchmark_type
    product_mix: Dict[str, float] = field(default_factory=dict)


@dataclass
class SteelPriceScenario:
    """Steel price scenario assumptions"""
    name: str
    description: str

    # Price levels relative to through-cycle baseline (1.0 = through-cycle normal)
    hrc_us_factor: float
    crc_us_factor: float
    coated_us_factor: float
    hrc_eu_factor: float
    octg_factor: float

    # Annual price growth after initial adjustment
    annual_price_growth: float

    # Section 232 tariff rate (0.0 = removed, 0.25 = current, 0.50 = escalation)
    # Through-cycle baseline already embeds current 25% tariff
    # Adjustment only applies when tariff_rate != 0.25
    tariff_rate: float = 0.25


@dataclass
class VolumeScenario:
    """Volume/demand scenario assumptions"""
    name: str
    description: str

    # Volume factors by segment (1.0 = base case)
    flat_rolled_volume_factor: float
    mini_mill_volume_factor: float
    usse_volume_factor: float
    tubular_volume_factor: float

    # Annual volume growth adjustments
    flat_rolled_growth_adj: float
    mini_mill_growth_adj: float
    usse_growth_adj: float
    tubular_growth_adj: float


@dataclass
class CapitalProject:
    """Capital project with segment allocation and dynamic EBITDA calculation.

    Dynamic EBITDA Formula: Capacity × Utilization × Price × Margin
    Source: Capstone Project Analysis, Tables 1-3

    Margin Rules by Technology (sourced from industry benchmarks):
    - EAF Mini Mill: 20% (management target; peers STLD/NUE achieve 18-23%)
    - Blast Furnace: 12-15% (post-upgrade efficiency; improved from 4.4% actual)
    - Mining: 12% (conservative given captive use)

    Terminal Multiple Rules (sourced from WRDS peer EV/EBITDA analysis):
    - EAF Mini Mill: 7x EBITDA (peer median: STLD 7.8x, NUE 7.9x, CMC 5.8x)
    - Blast Furnace: 5x EBITDA (peer median: MT 4.7x, PKX 6.2x, TX 3.3x)
    - Mining: 5x EBITDA (similar to integrated assets)
    - Tubular/OCTG: 6x EBITDA (blended, specialty premium)
    """
    name: str
    segment: str
    enabled: bool
    capex_schedule: Dict[int, float]

    # Dynamic EBITDA parameters (sourced from Capstone analysis)
    nameplate_capacity: float = 0.0           # kt/year at full operation
    base_utilization: float = 0.85            # 85% base case (conservative vs. 90%+ industry)
    ebitda_margin: float = 0.12               # Project-specific EBITDA margin
    capacity_ramp: Dict[int, float] = field(default_factory=dict)  # Year → utilization %
    base_price_override: Optional[float] = None  # Use instead of segment price (e.g., $150/ton for mining)

    # Terminal value parameters (sourced from WRDS peer comparable analysis)
    terminal_multiple: float = 5.0            # EV/EBITDA exit multiple for terminal value

    # Maintenance capex (annual sustaining capital after construction)
    maintenance_capex_per_ton: float = 0.0    # $/ton annual maintenance capex

    # LEGACY: Retained for backwards compatibility and reference
    ebitda_schedule: Dict[int, float] = field(default_factory=dict)
    volume_addition: Dict[int, float] = field(default_factory=dict)  # Additional tons


# =============================================================================
# SYNERGY AND TECHNOLOGY TRANSFER DATACLASSES
# =============================================================================

@dataclass
class SynergyRampSchedule:
    """Year-by-year synergy realization (0.0-1.0)"""
    schedule: Dict[int, float] = field(default_factory=dict)

    def get_realization(self, year: int) -> float:
        """Get realization factor for a given year"""
        return self.schedule.get(year, 0.0)


@dataclass
class OperatingSynergies:
    """Cost synergies from combined operations"""
    procurement_savings_annual: float = 0.0  # $M at run-rate
    procurement_confidence: float = 0.80
    logistics_savings_annual: float = 0.0
    logistics_confidence: float = 0.75
    overhead_savings_annual: float = 0.0
    overhead_confidence: float = 0.85
    ramp_schedule: SynergyRampSchedule = field(default_factory=SynergyRampSchedule)

    def get_total_run_rate(self) -> float:
        """Get probability-weighted total run-rate savings"""
        return (
            self.procurement_savings_annual * self.procurement_confidence +
            self.logistics_savings_annual * self.logistics_confidence +
            self.overhead_savings_annual * self.overhead_confidence
        )


@dataclass
class TechnologyTransfer:
    """Technology and operational improvements from Nippon know-how"""
    yield_improvement_pct: float = 0.0       # e.g., 0.02 = 2% yield improvement
    yield_margin_impact: float = 0.008       # Margin improvement per 1% yield gain
    quality_price_premium_pct: float = 0.0   # Premium pricing from quality improvements
    conversion_cost_reduction_pct: float = 0.0  # Reduction in conversion costs
    segment_allocation: Dict[str, float] = field(default_factory=dict)  # Allocation by segment
    ramp_schedule: SynergyRampSchedule = field(default_factory=SynergyRampSchedule)
    confidence: float = 0.70


@dataclass
class RevenueSynergies:
    """Revenue enhancement opportunities"""
    cross_sell_revenue_annual: float = 0.0  # $M additional revenue at run-rate
    cross_sell_margin: float = 0.15  # EBITDA margin on cross-sell revenue
    cross_sell_confidence: float = 0.60
    product_mix_revenue_uplift: float = 0.0  # $M from better product mix
    product_mix_margin: float = 0.20  # Higher margin on improved mix
    product_mix_confidence: float = 0.65
    ramp_schedule: SynergyRampSchedule = field(default_factory=SynergyRampSchedule)

    def get_run_rate_ebitda(self) -> float:
        """Get probability-weighted EBITDA from revenue synergies at run-rate"""
        return (
            self.cross_sell_revenue_annual * self.cross_sell_margin * self.cross_sell_confidence +
            self.product_mix_revenue_uplift * self.product_mix_margin * self.product_mix_confidence
        )


@dataclass
class IntegrationCosts:
    """One-time integration and restructuring costs"""
    it_integration_cost: float = 0.0  # $M total IT integration
    it_spend_schedule: Dict[int, float] = field(default_factory=dict)  # Year -> % of total
    cultural_integration_cost: float = 0.0  # $M cultural programs, training
    cultural_spend_schedule: Dict[int, float] = field(default_factory=dict)
    restructuring_cost: float = 0.0  # $M severance, facility consolidation
    restructuring_spend_schedule: Dict[int, float] = field(default_factory=dict)

    def get_total_cost(self) -> float:
        """Get total integration costs"""
        return (
            self.it_integration_cost +
            self.cultural_integration_cost +
            self.restructuring_cost
        )

    def get_cost_for_year(self, year: int) -> float:
        """Get integration costs for a specific year"""
        it_cost = self.it_integration_cost * self.it_spend_schedule.get(year, 0.0)
        cultural_cost = self.cultural_integration_cost * self.cultural_spend_schedule.get(year, 0.0)
        restructuring_cost = self.restructuring_cost * self.restructuring_spend_schedule.get(year, 0.0)
        return it_cost + cultural_cost + restructuring_cost


@dataclass
class SynergyAssumptions:
    """Complete synergy package for the merger"""
    name: str = "Default"
    description: str = ""
    operating: OperatingSynergies = field(default_factory=OperatingSynergies)
    technology: TechnologyTransfer = field(default_factory=TechnologyTransfer)
    revenue: RevenueSynergies = field(default_factory=RevenueSynergies)
    integration: IntegrationCosts = field(default_factory=IntegrationCosts)
    enabled: bool = True
    overall_execution_factor: float = 1.0  # Additional haircut for execution risk


@dataclass
class FinancingAssumptions:
    """Assumptions for how USS would finance large capital programs standalone"""
    # Current balance sheet
    current_debt: float = 4222.0  # $M - Current total debt
    current_shares: float = 225.0  # M shares outstanding

    # Financing mix for incremental CapEx beyond FCF
    debt_financing_pct: float = 0.50  # 50% debt, 50% equity

    # Debt financing costs
    incremental_cost_of_debt: float = 0.075  # 7.5% interest rate on new debt
    max_debt_to_ebitda: float = 3.5  # Maximum leverage before credit downgrade
    wacc_increase_per_turn_leverage: float = 0.005  # WACC increases 50bps per 1x leverage

    # Equity financing costs
    equity_issuance_discount: float = 0.10  # 10% discount to market price for equity raise
    equity_issuance_costs: float = 0.03  # 3% underwriting/issuance costs


@dataclass
class ModelScenario:
    """Complete scenario combining price, volume, and WACC assumptions"""
    name: str
    scenario_type: ScenarioType
    description: str

    # Steel price scenario
    price_scenario: SteelPriceScenario

    # Volume scenario
    volume_scenario: VolumeScenario

    # WACC assumptions
    uss_wacc: float
    terminal_growth: float
    exit_multiple: float

    # IRP parameters
    us_10yr: float
    japan_10yr: float
    nippon_equity_risk_premium: float  # Added to JGB to get cost of equity
    nippon_credit_spread: float  # Added to JGB to get cost of debt
    nippon_debt_ratio: float
    nippon_tax_rate: float

    # IRP Override (optional)
    override_irp: bool = False  # If True, use manual_nippon_usd_wacc instead of IRP formula
    manual_nippon_usd_wacc: Optional[float] = None  # Manual USD WACC for Nippon (when override_irp=True)

    # Capital projects to include
    include_projects: List[str] = field(default_factory=list)

    # Probability weight for probability-weighted valuation (0.0-1.0)
    probability_weight: float = 0.0

    # Financing assumptions for USS standalone (used when calculating "USS - No Sale" value)
    financing: FinancingAssumptions = field(default_factory=FinancingAssumptions)

    # Benchmark integration (optional)
    use_benchmark_multiples: bool = False  # Toggle benchmark-driven exit multiples

    # Synergy assumptions (optional) - only applies to Nippon valuation
    synergies: Optional[SynergyAssumptions] = None

    # WACC Module Integration (optional)
    use_verified_wacc: bool = True  # If True, load WACC from wacc-calculations module (default)
    wacc_audit_trail: Optional[dict] = None  # Audit trail from WACC module (populated at runtime)

    # Bloomberg Integration (optional)
    use_bloomberg_prices: bool = False  # Toggle Bloomberg prices vs 2023 baseline
    bloomberg_price_override: Optional[Dict[str, float]] = None  # Manual price override from Bloomberg


# =============================================================================
# BENCHMARK INTEGRATION
# =============================================================================

def get_benchmark_exit_multiple(scenario_type: str, use_benchmark: bool = False) -> Optional[float]:
    """Get exit multiple from peer data or return None to use scenario default.

    Args:
        scenario_type: Scenario name (e.g., 'base_case', 'severe_downturn')
        use_benchmark: If False, returns None to use scenario default

    Returns:
        Exit multiple from peer benchmarks, or None if benchmarks not available/enabled
    """
    if not use_benchmark:
        return None

    try:
        from benchmark_data import BenchmarkData
        benchmark = BenchmarkData()
        multiples = benchmark.get_exit_multiple_range()

        # Map scenario to benchmark percentile
        mapping = {
            'severe_downturn': multiples['low'] * 0.85,  # Below Q1
            'severe downturn (historical crisis)': multiples['low'] * 0.85,
            'downside': multiples['low'],                 # Q1
            'downside (weak markets)': multiples['low'],
            'base_case': multiples['base'],               # Median
            'base case (mid-cycle)': multiples['base'],
            'above_average': multiples['base'] * 1.1,     # Above median
            'above average (strong cycle)': multiples['base'] * 1.1,
            'optimistic': multiples['high'],              # Q3
            'optimistic (sustained growth)': multiples['high'],
            'wall_street': multiples['base'],             # Use median for consensus
            'wall street consensus': multiples['base'],
            'nippon_commitments': multiples['base'] * 1.05,  # Slight premium for strategic value
            'nsa mandated capex': multiples['base'] * 1.05,
        }
        return mapping.get(scenario_type.lower(), multiples['base'])
    except Exception:
        # Fallback if benchmark data not available
        return None


def validate_margin_vs_peers(segment_margin: float, segment_name: str) -> dict:
    """Compare segment margin against peer benchmarks.

    Args:
        segment_margin: The margin to validate (e.g., 0.12 for 12%)
        segment_name: Name of the segment for context

    Returns:
        Dict with margin comparison results
    """
    try:
        from benchmark_data import BenchmarkData
        benchmark = BenchmarkData()
        peer_stats = benchmark.get_margin_stats()

        # Look for EBITDA margin in stats
        for key in ['ltm_ebitda_margin', 'ebitda_margin_ltm', 'ebitda_margin']:
            if key in peer_stats:
                stats = peer_stats[key]
                deviation = segment_margin - stats.median
                return {
                    'segment': segment_name,
                    'margin': segment_margin,
                    'peer_median': stats.median,
                    'peer_range': (stats.q1, stats.q3),
                    'deviation_from_median': deviation,
                    'vs_peers': 'above' if segment_margin > stats.median else 'below',
                    'significant_deviation': abs(deviation) > (stats.q3 - stats.q1) / 2
                }
        return {'segment': segment_name, 'margin': segment_margin, 'peer_median': None}
    except Exception:
        return {'segment': segment_name, 'margin': segment_margin, 'peer_median': None}


# =============================================================================
# SCENARIO PRESETS
# =============================================================================

def get_base_price_scenario() -> SteelPriceScenario:
    """Above Average: strong markets, ~15% above through-cycle"""
    return SteelPriceScenario(
        name="Above Average Prices",
        description="Strong markets with good pricing power and sustained growth",
        hrc_us_factor=1.15,   # ~$849 HRC (strong cycle)
        crc_us_factor=1.10,
        coated_us_factor=1.10,
        hrc_eu_factor=1.15,
        octg_factor=1.15,
        annual_price_growth=0.01
    )


def get_conservative_price_scenario() -> SteelPriceScenario:
    """Downside: 10% below through-cycle"""
    return SteelPriceScenario(
        name="Conservative Prices",
        description="Below-cycle: soft demand, import pressure, flat pricing",
        hrc_us_factor=0.90,   # ~$664 HRC (below mid-cycle)
        crc_us_factor=0.90,
        coated_us_factor=0.90,
        hrc_eu_factor=0.85,
        octg_factor=0.85,
        annual_price_growth=0.00
    )


def get_wall_street_price_scenario() -> SteelPriceScenario:
    """Wall Street Consensus: ~20% above through-cycle (2023 elevated), flat growth"""
    return SteelPriceScenario(
        name="Wall Street Consensus",
        description="Analyst consensus - calibrated to $39-52 fairness opinion range",
        hrc_us_factor=1.20,   # ~$886 HRC (analysts anchored to 2023 levels)
        crc_us_factor=1.10,
        coated_us_factor=1.10,
        hrc_eu_factor=1.15,
        octg_factor=1.10,
        annual_price_growth=0.00
    )


def get_management_price_scenario() -> SteelPriceScenario:
    """Management Guidance: above through-cycle with optimistic growth"""
    return SteelPriceScenario(
        name="Management Guidance",
        description="Management optimism - prices above mid-cycle and grow",
        hrc_us_factor=1.15,
        crc_us_factor=1.10,
        coated_us_factor=1.10,
        hrc_eu_factor=1.10,
        octg_factor=1.15,
        annual_price_growth=0.02
    )


def get_optimistic_price_scenario() -> SteelPriceScenario:
    """Optimistic: 25% above through-cycle with 1.5% growth"""
    return SteelPriceScenario(
        name="Optimistic Pricing",
        description="Sustained favorable markets: well above through-cycle with 1.5% growth",
        hrc_us_factor=1.25,   # ~$923 HRC (sustained strong markets)
        crc_us_factor=1.15,
        coated_us_factor=1.15,
        hrc_eu_factor=1.20,
        octg_factor=1.20,
        annual_price_growth=0.015
    )


def get_base_volume_scenario() -> VolumeScenario:
    return VolumeScenario(
        name="Base Case Volumes",
        description="Stable demand with modest growth",
        flat_rolled_volume_factor=1.0,
        mini_mill_volume_factor=1.0,
        usse_volume_factor=1.0,
        tubular_volume_factor=1.0,
        flat_rolled_growth_adj=0.0,
        mini_mill_growth_adj=0.02,  # Mini mill gains share
        usse_growth_adj=0.0,
        tubular_growth_adj=0.015
    )


def get_conservative_volume_scenario() -> VolumeScenario:
    return VolumeScenario(
        name="Conservative Volumes",
        description="Demand weakness across segments",
        flat_rolled_volume_factor=0.95,
        mini_mill_volume_factor=0.95,  # Aligned with 0.05 step
        usse_volume_factor=0.90,       # Aligned with 0.05 step
        tubular_volume_factor=0.90,
        flat_rolled_growth_adj=-0.01,
        mini_mill_growth_adj=0.01,
        usse_growth_adj=-0.01,
        tubular_growth_adj=0.0
    )


def get_nippon_price_scenario() -> SteelPriceScenario:
    """Nippon NSA scenario: at through-cycle with capacity discipline supporting 1% growth"""
    return SteelPriceScenario(
        name="Nippon Commitments",
        description="NSA investment case - through-cycle pricing with capacity discipline",
        hrc_us_factor=1.05,
        crc_us_factor=1.05,
        coated_us_factor=1.05,
        hrc_eu_factor=1.00,
        octg_factor=1.05,
        annual_price_growth=0.01
    )


def get_severe_downturn_price_scenario() -> SteelPriceScenario:
    """Severe downturn: 25% below through-cycle (2009, 2015, 2020 levels)"""
    return SteelPriceScenario(
        name="Severe Downturn Pricing",
        description="Historical recession levels: 25% below through-cycle",
        hrc_us_factor=0.75,      # ~$554 HRC (recession level)
        crc_us_factor=0.75,
        coated_us_factor=0.75,
        hrc_eu_factor=0.70,      # EU hit harder
        octg_factor=0.55,        # Oil crash correlation
        annual_price_growth=-0.02
    )


def get_severe_downturn_volume_scenario() -> VolumeScenario:
    """Severe downturn: Demand collapse -15% to -25% across segments"""
    return VolumeScenario(
        name="Severe Downturn Volumes",
        description="Demand collapse: -15% to -25% across segments",
        flat_rolled_volume_factor=0.80,  # -20% volume
        mini_mill_volume_factor=0.85,    # -15% (more resilient)
        usse_volume_factor=0.75,         # -25% (EU exposure)
        tubular_volume_factor=0.70,      # -30% (oil correlation)
        flat_rolled_growth_adj=-0.03,    # -3% annual decline
        mini_mill_growth_adj=-0.02,
        usse_growth_adj=-0.04,
        tubular_growth_adj=-0.05
    )


def get_true_base_case_price_scenario() -> SteelPriceScenario:
    """Mid-cycle pricing: through-cycle structural equilibrium (factor 1.0)"""
    return SteelPriceScenario(
        name="Mid-Cycle Pricing",
        description="Through-cycle structural equilibrium (Avg pre-COVID + post-spike medians)",
        hrc_us_factor=1.00,      # $738 HRC = through-cycle normal
        crc_us_factor=1.00,
        coated_us_factor=1.00,
        hrc_eu_factor=1.00,
        octg_factor=1.00,
        annual_price_growth=0.01  # 1% inflation
    )


def get_true_base_case_volume_scenario() -> VolumeScenario:
    """Mid-cycle volumes: Historical average utilization"""
    return VolumeScenario(
        name="Mid-Cycle Volumes",
        description="Historical average utilization",
        flat_rolled_volume_factor=0.90,  # Modest decline from 2023 (aligned with 0.05 step)
        mini_mill_volume_factor=1.00,    # Aligned with 0.05 step
        usse_volume_factor=0.90,
        tubular_volume_factor=0.95,
        flat_rolled_growth_adj=-0.005,
        mini_mill_growth_adj=0.005,
        usse_growth_adj=-0.005,
        tubular_growth_adj=0.00
    )


# =============================================================================
# FUTURES MODEL SCENARIOS
# =============================================================================
# These scenarios are derived from the CommodityModel Futures Model, which uses:
#   - Post-COVID training data (2022-Q3 onwards)
#   - 50% Section 232 tariff assumptions
#   - Model: ln(HRC) = -2.98 + 1.57×ln(Scrap) + 0.01×Capacity + 0.07×Tariff
#
# Key difference from original scenarios:
#   - Original: Mean reversion to ~$600-680 HRC
#   - Futures: Tariff supports ~$850-950 HRC
#
# Price factors derived from Monte Carlo with stochastic spreads:
#   - CRC = HRC + Normal($249, $79)
#   - Coated = CRC + $100
#   - EU HRC = HRC × Normal(0.79, 0.10)
#   - OCTG = HRC × Normal(2.92, 1.17)

def get_futures_downside_price_scenario() -> SteelPriceScenario:
    """Futures Model: Downside (weak demand, scrap falls)

    Inputs: Scrap $270, Capacity 70%, Tariff 50%
    HRC Forecast: ~$726/ton → factor = $726/$738 = 0.98
    """
    return SteelPriceScenario(
        name="Futures: Downside",
        description="Post-COVID downside: weak demand, scrap ~$270, capacity ~70%",
        hrc_us_factor=0.98,      # $726 / $738
        crc_us_factor=0.98,      # ($726 + $249) / $994
        coated_us_factor=0.97,   # ($726 + $249 + $100) / $1113
        hrc_eu_factor=0.94,      # $726 × 0.79 / $611
        octg_factor=0.89,        # $726 × 2.92 / $2388
        annual_price_growth=0.00,
        tariff_rate=0.25,
    )


def get_futures_base_case_price_scenario() -> SteelPriceScenario:
    """Futures Model: Base Case (normalized post-COVID market)

    Inputs: Scrap $293, Capacity 76%, Tariff 50%
    HRC Forecast: ~$885/ton → factor = $885/$738 = 1.20
    """
    return SteelPriceScenario(
        name="Futures: Base Case",
        description="Post-COVID normalized: scrap ~$293, capacity ~76%, 50% tariff",
        hrc_us_factor=1.20,      # $885 / $738
        crc_us_factor=1.14,      # ($885 + $249) / $994
        coated_us_factor=1.12,   # ($885 + $249 + $100) / $1113
        hrc_eu_factor=1.14,      # $885 × 0.79 / $611
        octg_factor=1.08,        # $885 × 2.92 / $2388
        annual_price_growth=0.01,
        tariff_rate=0.25,
    )


def get_futures_above_average_price_scenario() -> SteelPriceScenario:
    """Futures Model: Above Average (strong demand, infrastructure spending)

    Inputs: Scrap $320, Capacity 79%, Tariff 50%
    HRC Forecast: ~$1,040/ton → factor = $1040/$738 = 1.41
    """
    return SteelPriceScenario(
        name="Futures: Above Average",
        description="Post-COVID strong: scrap ~$320, capacity ~79%, infrastructure",
        hrc_us_factor=1.41,      # $1,040 / $738
        crc_us_factor=1.30,      # ($1,040 + $249) / $994
        coated_us_factor=1.25,   # ($1,040 + $249 + $100) / $1113
        hrc_eu_factor=1.34,      # $1,040 × 0.79 / $611
        octg_factor=1.27,        # $1,040 × 2.92 / $2388
        annual_price_growth=0.015,
        tariff_rate=0.25,
    )


def get_futures_optimistic_price_scenario() -> SteelPriceScenario:
    """Futures Model: Optimistic (strong demand, supply constraints)

    Inputs: Scrap $355, Capacity 82%, Tariff 50%
    HRC Forecast: ~$1,263/ton → factor = $1263/$738 = 1.71
    """
    return SteelPriceScenario(
        name="Futures: Optimistic",
        description="Post-COVID boom: scrap ~$355, capacity ~82%, tight supply",
        hrc_us_factor=1.71,      # $1,263 / $738
        crc_us_factor=1.52,      # ($1,263 + $249) / $994
        coated_us_factor=1.45,   # ($1,263 + $249 + $100) / $1113
        hrc_eu_factor=1.63,      # $1,263 × 0.79 / $611
        octg_factor=1.54,        # $1,263 × 2.92 / $2388
        annual_price_growth=0.02,
        tariff_rate=0.25,
    )


def get_futures_no_tariff_price_scenario() -> SteelPriceScenario:
    """Futures Model: No Tariff (tariff removed)

    Inputs: Scrap $293, Capacity 76%, Tariff 0%
    HRC Forecast: ~$827/ton → factor = $827/$738 = 1.12
    tariff_rate=0.0 applies additional adjustment via calculate_tariff_adjustment()
    """
    return SteelPriceScenario(
        name="Futures: No Tariff",
        description="Futures base if tariff removed: $827 HRC, with tariff adjustment",
        hrc_us_factor=1.12,      # $827 / $738
        crc_us_factor=1.08,      # ($827 + $249) / $994
        coated_us_factor=1.06,   # ($827 + $249 + $100) / $1113
        hrc_eu_factor=1.07,      # $827 × 0.79 / $611
        octg_factor=1.01,        # $827 × 2.92 / $2388
        annual_price_growth=0.01,
        tariff_rate=0.0,         # Tariff removal scenario
    )


def get_futures_base_volume_scenario() -> VolumeScenario:
    """Futures Model: Base case volumes (normalized demand)"""
    return VolumeScenario(
        name="Futures: Base Volumes",
        description="Post-COVID normalized demand",
        flat_rolled_volume_factor=0.93,
        mini_mill_volume_factor=0.98,
        usse_volume_factor=0.90,
        tubular_volume_factor=0.95,
        flat_rolled_growth_adj=-0.005,
        mini_mill_growth_adj=0.01,
        usse_growth_adj=-0.005,
        tubular_growth_adj=0.0
    )


def get_futures_downside_volume_scenario() -> VolumeScenario:
    """Futures Model: Downside volumes (weak demand)"""
    return VolumeScenario(
        name="Futures: Downside Volumes",
        description="Below-trend demand",
        flat_rolled_volume_factor=0.88,
        mini_mill_volume_factor=0.92,
        usse_volume_factor=0.85,
        tubular_volume_factor=0.85,
        flat_rolled_growth_adj=-0.01,
        mini_mill_growth_adj=0.0,
        usse_growth_adj=-0.01,
        tubular_growth_adj=-0.01
    )


def get_futures_optimistic_volume_scenario() -> VolumeScenario:
    """Futures Model: Optimistic volumes (strong demand)"""
    return VolumeScenario(
        name="Futures: Optimistic Volumes",
        description="Strong demand across segments",
        flat_rolled_volume_factor=0.98,
        mini_mill_volume_factor=1.02,
        usse_volume_factor=0.95,
        tubular_volume_factor=1.05,
        flat_rolled_growth_adj=0.0,
        mini_mill_growth_adj=0.02,
        usse_growth_adj=0.0,
        tubular_growth_adj=0.01
    )


def _apply_calibration_factors_to_scenario(
    base_scenario: ModelScenario,
    calibration_mode: str = None
) -> ModelScenario:
    """
    Apply calibration factors to a ModelScenario based on the selected mode.

    This modifies the price_scenario factors if a calibration mode is specified
    and the scenario has a matching calibration factor set.

    NOTE: BASE_CASE is NOT modified by calibration. The model's base case represents
    "mid-cycle" conditions (below 2023 levels since 2023 was elevated), not the
    2023 annual average. Calibration only affects downside and upside scenarios.

    Args:
        base_scenario: The base ModelScenario to modify
        calibration_mode: One of 'fixed', 'bloomberg', 'hybrid', or None

    Returns:
        ModelScenario with potentially updated price factors
    """
    if not calibration_mode or not SCENARIO_CALIBRATION_AVAILABLE:
        return base_scenario

    # Map scenario types to calibration scenario names
    # All core scenarios now use recalibrated factors from scenario_calibrator.py
    # Base Case uses recalibrated mid-cycle factors (0.94x HRC, 0.76x OCTG)
    # calibrated to actual 2024-2025 Bloomberg data
    scenario_type_to_calibration = {
        ScenarioType.SEVERE_DOWNTURN: 'severe_downturn',
        ScenarioType.DOWNSIDE: 'downside',
        ScenarioType.BASE_CASE: 'base_case',  # Now uses recalibrated factors
        ScenarioType.ABOVE_AVERAGE: 'upside',  # Maps to upside/modest_upside
        ScenarioType.OPTIMISTIC: 'optimistic',  # Maps to optimistic/boom
        ScenarioType.CONSERVATIVE: 'downside',  # Alias
    }

    calibration_name = scenario_type_to_calibration.get(base_scenario.scenario_type)
    if not calibration_name:
        # BASE_CASE, WALL_STREET, NIPPON_COMMITMENTS don't use calibration
        return base_scenario

    try:
        mode_enum = ScenarioCalibrationMode(calibration_mode)
        factors = get_scenario_factors(calibration_name, mode_enum)

        if factors:
            # Create a new price scenario with calibrated factors
            calibrated_price = SteelPriceScenario(
                name=base_scenario.price_scenario.name + f" ({calibration_mode})",
                description=factors.description,
                hrc_us_factor=factors.hrc_us,
                crc_us_factor=factors.crc_us,
                coated_us_factor=factors.coated_us,
                hrc_eu_factor=factors.hrc_eu,
                octg_factor=factors.octg,
                annual_price_growth=factors.annual_price_growth,
            )

            # Create a new scenario with updated price factors
            # Using dataclass replace pattern (manual since we're using @dataclass)
            return ModelScenario(
                name=base_scenario.name,
                scenario_type=base_scenario.scenario_type,
                description=base_scenario.description,
                price_scenario=calibrated_price,
                volume_scenario=base_scenario.volume_scenario,
                uss_wacc=base_scenario.uss_wacc,
                terminal_growth=base_scenario.terminal_growth,
                exit_multiple=base_scenario.exit_multiple,
                us_10yr=base_scenario.us_10yr,
                japan_10yr=base_scenario.japan_10yr,
                nippon_equity_risk_premium=base_scenario.nippon_equity_risk_premium,
                nippon_credit_spread=base_scenario.nippon_credit_spread,
                nippon_debt_ratio=base_scenario.nippon_debt_ratio,
                nippon_tax_rate=base_scenario.nippon_tax_rate,
                override_irp=base_scenario.override_irp,
                manual_nippon_usd_wacc=base_scenario.manual_nippon_usd_wacc,
                include_projects=base_scenario.include_projects,
                probability_weight=base_scenario.probability_weight,
                financing=base_scenario.financing,
                use_benchmark_multiples=base_scenario.use_benchmark_multiples,
                synergies=base_scenario.synergies,
                use_verified_wacc=base_scenario.use_verified_wacc,
                wacc_audit_trail=base_scenario.wacc_audit_trail,
                use_bloomberg_prices=base_scenario.use_bloomberg_prices,
                bloomberg_price_override=base_scenario.bloomberg_price_override,
            )
    except (ValueError, KeyError):
        pass

    return base_scenario


def get_scenario_presets(
    calibration_mode: Optional[str] = None,
    probability_mode: Optional[str] = None
) -> Dict[ScenarioType, ModelScenario]:
    """Return all pre-built scenario configurations

    Scenarios calibrated to historical data (1990-2023):
    - Severe Downturn: 0-25th percentile (historical frequency: 24%)
    - Downside: 25-40th percentile (historical frequency: 30%)
    - Base Case: 50th percentile - median (historical frequency: 30%)
    - Above Average: 75-90th percentile (historical frequency: 10%)
    - Optimistic: 90th+ percentile (historical frequency: 5%)
    - Wall Street: Analyst consensus (reference only, no probability weight)
    - Nippon Commitments: $14B NSA investment program (reference only)

    Args:
        calibration_mode: Optional calibration mode for price factors.
            One of 'fixed', 'bloomberg', 'hybrid', or None.
            - None: Use default hardcoded factors (current behavior)
            - 'fixed': Symmetric ±15% factors (simple, stable)
            - 'bloomberg': Full percentile-based from historical data
            - 'hybrid': Bloomberg downside, capped upside (conservative)
        probability_mode: Optional probability distribution mode.
            One of 'fixed', 'bloomberg', or None.
            - None: Use default hardcoded probability weights
            - 'fixed': Symmetric probability distribution
            - 'bloomberg': Percentile-based distribution from historical data
    """

    presets = {
        ScenarioType.SEVERE_DOWNTURN: ModelScenario(
            name="Severe Downturn (Historical Crisis)",
            scenario_type=ScenarioType.SEVERE_DOWNTURN,
            description="Recession scenario: 2009/2015/2020 conditions",
            price_scenario=get_severe_downturn_price_scenario(),
            volume_scenario=get_severe_downturn_volume_scenario(),
            uss_wacc=0.135,           # 13.5% (distress premium)
            terminal_growth=0.005,    # 0.5% (mature/declining)
            exit_multiple=3.5,        # Low exit multiple
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0575,  # Higher risk in downturn
            nippon_credit_spread=0.0125,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=[],      # No capex in severe downturn
            probability_weight=0.25   # 25% probability
        ),

        ScenarioType.DOWNSIDE: ModelScenario(
            name="Downside (Weak Markets)",
            scenario_type=ScenarioType.DOWNSIDE,
            description="Below-average cycle: soft demand, import pressure",
            price_scenario=get_conservative_price_scenario(),
            volume_scenario=get_conservative_volume_scenario(),
            uss_wacc=0.12,
            terminal_growth=0.01,
            exit_multiple=4.0,
            us_10yr=0.045,
            japan_10yr=0.01,
            nippon_equity_risk_premium=0.05,
            nippon_credit_spread=0.01,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.30   # 30% probability
        ),

        ScenarioType.BASE_CASE: ModelScenario(
            name="Base Case (Mid-Cycle)",
            scenario_type=ScenarioType.BASE_CASE,
            description="Historical median: normalized steel markets",
            price_scenario=get_true_base_case_price_scenario(),
            volume_scenario=get_true_base_case_volume_scenario(),
            uss_wacc=0.109,
            terminal_growth=0.01,
            exit_multiple=4.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.30   # 30% probability
        ),

        ScenarioType.ABOVE_AVERAGE: ModelScenario(
            name="Above Average (Strong Cycle)",
            scenario_type=ScenarioType.ABOVE_AVERAGE,
            description="Strong markets: 2017-2018 conditions",
            price_scenario=get_base_price_scenario(),  # Old base = 0.95x
            volume_scenario=VolumeScenario(
                name="Above Average Volumes",
                description="Modest growth, good market conditions",
                flat_rolled_volume_factor=1.00,  # Aligned with 0.05 step
                mini_mill_volume_factor=1.0,
                usse_volume_factor=1.00,         # Aligned with 0.05 step
                tubular_volume_factor=1.0,
                flat_rolled_growth_adj=-0.01,
                mini_mill_growth_adj=0.01,
                usse_growth_adj=-0.005,
                tubular_growth_adj=0.005
            ),
            uss_wacc=0.109,
            terminal_growth=0.01,
            exit_multiple=5.0,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.10   # 10% probability
        ),

        # Keep CONSERVATIVE as alias for backward compatibility
        ScenarioType.CONSERVATIVE: ModelScenario(
            name="Downside (Weak Markets)",
            scenario_type=ScenarioType.DOWNSIDE,
            description="Below-average cycle: soft demand, import pressure",
            price_scenario=get_conservative_price_scenario(),
            volume_scenario=get_conservative_volume_scenario(),
            uss_wacc=0.12,
            terminal_growth=0.01,
            exit_multiple=4.0,
            us_10yr=0.045,
            japan_10yr=0.01,
            nippon_equity_risk_premium=0.05,
            nippon_credit_spread=0.01,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.30
        ),

        ScenarioType.WALL_STREET: ModelScenario(
            name="Wall Street Consensus",
            scenario_type=ScenarioType.WALL_STREET,
            description="Barclays/Goldman DCF: 11.5-13.5% WACC, $39-52/share range",
            price_scenario=get_wall_street_price_scenario(),
            volume_scenario=get_base_volume_scenario(),
            uss_wacc=0.125,
            terminal_growth=0.01,
            exit_multiple=4.75,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.0  # Reference only, no probability weight
        ),

        ScenarioType.OPTIMISTIC: ModelScenario(
            name="Optimistic (Sustained Growth)",
            scenario_type=ScenarioType.OPTIMISTIC,
            description="Sustained favorable markets: benchmark pricing with 2% growth",
            price_scenario=get_optimistic_price_scenario(),
            volume_scenario=VolumeScenario(
                name="Strong Market Volumes",
                description="Strong demand across all segments",
                flat_rolled_volume_factor=0.95,
                mini_mill_volume_factor=1.0,
                usse_volume_factor=0.95,
                tubular_volume_factor=1.0,
                flat_rolled_growth_adj=-0.02,
                mini_mill_growth_adj=0.02,
                usse_growth_adj=-0.01,
                tubular_growth_adj=0.0
            ),
            uss_wacc=0.109,
            terminal_growth=0.015,
            exit_multiple=5.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.05  # 5% probability
        ),

        # Keep MANAGEMENT as alias for backward compatibility
        ScenarioType.MANAGEMENT: ModelScenario(
            name="Optimistic (Sustained Growth)",
            scenario_type=ScenarioType.OPTIMISTIC,
            description="Sustained favorable markets: benchmark pricing with 2% growth",
            price_scenario=get_optimistic_price_scenario(),
            volume_scenario=VolumeScenario(
                name="Strong Market Volumes",
                description="Strong demand across all segments",
                flat_rolled_volume_factor=0.95,
                mini_mill_volume_factor=1.0,
                usse_volume_factor=0.95,
                tubular_volume_factor=1.0,
                flat_rolled_growth_adj=-0.02,
                mini_mill_growth_adj=0.02,
                usse_growth_adj=-0.01,
                tubular_growth_adj=0.0
            ),
            uss_wacc=0.109,
            terminal_growth=0.015,
            exit_multiple=5.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.05
        ),

        ScenarioType.NIPPON_COMMITMENTS: ModelScenario(
            name="NSA Mandated CapEx",
            scenario_type=ScenarioType.NIPPON_COMMITMENTS,
            description="$14B government-mandated investment: Gary $3.1B, Mon Valley $1B, BRS $3B, New Mini Mill $1B",
            price_scenario=SteelPriceScenario(
                name="Nippon Investment Case",
                description="Through-cycle pricing with capacity discipline",
                hrc_us_factor=1.05,
                crc_us_factor=1.05,
                coated_us_factor=1.05,
                hrc_eu_factor=1.00,
                octg_factor=1.05,
                annual_price_growth=0.01
            ),
            volume_scenario=VolumeScenario(
                name="NSA Investment Case",
                description="$2.5B incremental EBITDA target, no plant closures through 2035",
                flat_rolled_volume_factor=1.0,
                mini_mill_volume_factor=1.05,
                usse_volume_factor=1.0,
                tubular_volume_factor=1.0,
                flat_rolled_growth_adj=0.0,
                mini_mill_growth_adj=0.02,
                usse_growth_adj=0.0,
                tubular_growth_adj=0.005
            ),
            uss_wacc=0.105,
            terminal_growth=0.015,
            exit_multiple=5.0,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill', 'Gary Works BF', 'Mon Valley HSM',
                            'Greenfield Mini Mill', 'Mining Investment', 'Fairfield Works'],
            probability_weight=0.0  # Reference only, no probability weight
        ),

        # =====================================================================
        # FUTURES MODEL SCENARIOS
        # Based on post-COVID OLS regression: ln(HRC) = -2.98 + 1.57×ln(Scrap) + 0.0105×Capacity + 0.0685×Tariff
        # Benchmarks: HRC $680, CRC $850, Coated $950 (2023)
        # =====================================================================

        ScenarioType.FUTURES_DOWNSIDE: ModelScenario(
            name="Futures: Downside",
            scenario_type=ScenarioType.FUTURES_DOWNSIDE,
            description="Recession scenario: Scrap $250, Capacity 70%, with 50% tariff. HRC ~$750",
            price_scenario=get_futures_downside_price_scenario(),
            volume_scenario=get_futures_downside_volume_scenario(),
            uss_wacc=0.115,  # Higher WACC in recession
            terminal_growth=0.005,
            exit_multiple=4.0,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0500,
            nippon_credit_spread=0.0100,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.15
        ),

        ScenarioType.FUTURES_BASE_CASE: ModelScenario(
            name="Futures: Base Case",
            scenario_type=ScenarioType.FUTURES_BASE_CASE,
            description="Current market: Scrap $293, Capacity 76%, with 50% tariff. HRC ~$888",
            price_scenario=get_futures_base_case_price_scenario(),
            volume_scenario=get_futures_base_volume_scenario(),
            uss_wacc=0.109,
            terminal_growth=0.010,
            exit_multiple=4.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.40
        ),

        ScenarioType.FUTURES_ABOVE_AVERAGE: ModelScenario(
            name="Futures: Above Average",
            scenario_type=ScenarioType.FUTURES_ABOVE_AVERAGE,
            description="Strong market: Scrap $320, Capacity 80%, with 50% tariff. HRC ~$1,005",
            price_scenario=get_futures_above_average_price_scenario(),
            volume_scenario=get_futures_base_volume_scenario(),
            uss_wacc=0.109,
            terminal_growth=0.010,
            exit_multiple=4.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475,
            nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.30
        ),

        ScenarioType.FUTURES_OPTIMISTIC: ModelScenario(
            name="Futures: Optimistic",
            scenario_type=ScenarioType.FUTURES_OPTIMISTIC,
            description="Boom conditions: Scrap $350, Capacity 84%, with 50% tariff. HRC ~$1,140",
            price_scenario=get_futures_optimistic_price_scenario(),
            volume_scenario=get_futures_optimistic_volume_scenario(),
            uss_wacc=0.105,
            terminal_growth=0.015,
            exit_multiple=5.0,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0450,
            nippon_credit_spread=0.0060,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill', 'Gary Works BF'],
            probability_weight=0.15
        ),

        ScenarioType.FUTURES_NO_TARIFF: ModelScenario(
            name="Futures: No Tariff",
            scenario_type=ScenarioType.FUTURES_NO_TARIFF,
            description="Base inputs without tariff protection. HRC ~$829 (-7% vs base)",
            price_scenario=get_futures_no_tariff_price_scenario(),
            volume_scenario=get_futures_base_volume_scenario(),
            uss_wacc=0.112,  # Higher risk without tariff
            terminal_growth=0.010,
            exit_multiple=4.5,
            us_10yr=0.0425,
            japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0500,
            nippon_credit_spread=0.0085,
            nippon_debt_ratio=0.35,
            nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.0  # Reference scenario, not in probability weighting
        ),

        # =====================================================================
        # TARIFF SCENARIO TYPES
        # Use base case factors (1.0x) with varying tariff_rate for clean
        # tariff-only impact analysis
        # =====================================================================

        ScenarioType.TARIFF_REMOVAL: ModelScenario(
            name="Tariff Removal",
            scenario_type=ScenarioType.TARIFF_REMOVAL,
            description="Section 232 tariff fully removed: HRC drops ~15%",
            price_scenario=SteelPriceScenario(
                name="Tariff Removal",
                description="Through-cycle pricing with tariff removed",
                hrc_us_factor=1.00, crc_us_factor=1.00, coated_us_factor=1.00,
                hrc_eu_factor=1.00, octg_factor=1.00,
                annual_price_growth=0.01,
                tariff_rate=0.0,
            ),
            volume_scenario=get_true_base_case_volume_scenario(),
            uss_wacc=0.112, terminal_growth=0.01, exit_multiple=4.5,
            us_10yr=0.0425, japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0500, nippon_credit_spread=0.0085,
            nippon_debt_ratio=0.35, nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.0,
        ),

        ScenarioType.TARIFF_REDUCED: ModelScenario(
            name="Tariff Reduced (10%)",
            scenario_type=ScenarioType.TARIFF_REDUCED,
            description="Section 232 tariff reduced to 10%: HRC drops ~9%",
            price_scenario=SteelPriceScenario(
                name="Tariff Reduced",
                description="Through-cycle pricing with tariff reduced to 10%",
                hrc_us_factor=1.00, crc_us_factor=1.00, coated_us_factor=1.00,
                hrc_eu_factor=1.00, octg_factor=1.00,
                annual_price_growth=0.01,
                tariff_rate=0.10,
            ),
            volume_scenario=get_true_base_case_volume_scenario(),
            uss_wacc=0.110, terminal_growth=0.01, exit_multiple=4.5,
            us_10yr=0.0425, japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475, nippon_credit_spread=0.0080,
            nippon_debt_ratio=0.35, nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.0,
        ),

        ScenarioType.TARIFF_ESCALATION: ModelScenario(
            name="Tariff Escalation (50%)",
            scenario_type=ScenarioType.TARIFF_ESCALATION,
            description="Section 232 tariff doubled to 50%: HRC rises ~15%",
            price_scenario=SteelPriceScenario(
                name="Tariff Escalation",
                description="Through-cycle pricing with tariff doubled to 50%",
                hrc_us_factor=1.00, crc_us_factor=1.00, coated_us_factor=1.00,
                hrc_eu_factor=1.00, octg_factor=1.00,
                annual_price_growth=0.01,
                tariff_rate=0.50,
            ),
            volume_scenario=get_true_base_case_volume_scenario(),
            uss_wacc=0.109, terminal_growth=0.01, exit_multiple=4.5,
            us_10yr=0.0425, japan_10yr=0.0075,
            nippon_equity_risk_premium=0.0475, nippon_credit_spread=0.0075,
            nippon_debt_ratio=0.35, nippon_tax_rate=0.30,
            include_projects=['BR2 Mini Mill'],
            probability_weight=0.0,
        ),
    }

    # Apply calibration mode if specified
    if calibration_mode and SCENARIO_CALIBRATION_AVAILABLE:
        calibrated_presets = {}
        for scenario_type, scenario in presets.items():
            calibrated_presets[scenario_type] = _apply_calibration_factors_to_scenario(
                scenario, calibration_mode
            )
        presets = calibrated_presets

    # Apply probability mode if specified
    if probability_mode and SCENARIO_CALIBRATION_AVAILABLE:
        try:
            mode_enum = ProbabilityDistributionMode(probability_mode)
            presets = apply_probability_weights_to_scenarios(presets, mode_enum)
        except (ValueError, TypeError):
            pass  # Invalid mode, keep default weights

    return presets


# =============================================================================
# SYNERGY PRESETS
# =============================================================================

def get_synergy_presets() -> Dict[str, SynergyAssumptions]:
    """Return pre-built synergy configurations

    Standard ramp schedule: 0% → 20% → 50% → 80% → 100% (Y1-Y5)
    Technology ramp (slower): 0% → 0% → 20% → 50% → 80% → 100% (Y1-Y6)
    Integration cost schedule: 40% → 40% → 20% (Y1-Y3)

    Industry benchmarks from steel M&A transactions:
    - Operating synergies: 2-4% of combined cost base
    - Technology transfer: 1-3% yield improvement typical
    - Revenue synergies: Most difficult to achieve, 60-70% confidence
    """

    # Standard synergy ramp: 0% Y1 → 20% Y2 → 50% Y3 → 80% Y4 → 100% Y5
    standard_ramp = SynergyRampSchedule(schedule={
        2024: 0.0, 2025: 0.20, 2026: 0.50, 2027: 0.80, 2028: 1.0,
        2029: 1.0, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0
    })

    # Slower technology ramp: 0% Y1-Y2 → 20% Y3 → 50% Y4 → 80% Y5 → 100% Y6
    technology_ramp = SynergyRampSchedule(schedule={
        2024: 0.0, 2025: 0.0, 2026: 0.20, 2027: 0.50, 2028: 0.80,
        2029: 1.0, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0
    })

    # Integration cost schedule: 40% Y1, 40% Y2, 20% Y3
    integration_schedule = {2024: 0.40, 2025: 0.40, 2026: 0.20}

    return {
        'none': SynergyAssumptions(
            name="None",
            description="No synergies modeled",
            enabled=False
        ),

        'conservative': SynergyAssumptions(
            name="Conservative",
            description="Low-end synergy estimates with high confidence factors",
            operating=OperatingSynergies(
                procurement_savings_annual=50.0,  # $50M
                procurement_confidence=0.85,
                logistics_savings_annual=30.0,  # $30M
                logistics_confidence=0.80,
                overhead_savings_annual=40.0,  # $40M
                overhead_confidence=0.90,
                ramp_schedule=standard_ramp
            ),
            technology=TechnologyTransfer(
                yield_improvement_pct=0.01,  # 1% yield improvement
                yield_margin_impact=0.008,
                quality_price_premium_pct=0.01,  # 1% price premium
                conversion_cost_reduction_pct=0.02,  # 2% cost reduction
                segment_allocation={'Flat-Rolled': 0.50, 'Mini Mill': 0.30, 'USSE': 0.15, 'Tubular': 0.05},
                ramp_schedule=technology_ramp,
                confidence=0.75
            ),
            revenue=RevenueSynergies(
                cross_sell_revenue_annual=100.0,  # $100M
                cross_sell_margin=0.15,
                cross_sell_confidence=0.55,
                product_mix_revenue_uplift=50.0,  # $50M
                product_mix_margin=0.20,
                product_mix_confidence=0.60,
                ramp_schedule=standard_ramp
            ),
            integration=IntegrationCosts(
                it_integration_cost=125.0,  # $125M
                it_spend_schedule=integration_schedule,
                cultural_integration_cost=50.0,  # $50M
                cultural_spend_schedule=integration_schedule,
                restructuring_cost=150.0,  # $150M
                restructuring_spend_schedule=integration_schedule
            ),
            enabled=True,
            overall_execution_factor=1.0
        ),

        'base_case': SynergyAssumptions(
            name="Base Case",
            description="Expected synergy realization based on industry benchmarks",
            operating=OperatingSynergies(
                procurement_savings_annual=100.0,  # $100M
                procurement_confidence=0.80,
                logistics_savings_annual=60.0,  # $60M
                logistics_confidence=0.75,
                overhead_savings_annual=80.0,  # $80M
                overhead_confidence=0.85,
                ramp_schedule=standard_ramp
            ),
            technology=TechnologyTransfer(
                yield_improvement_pct=0.02,  # 2% yield improvement
                yield_margin_impact=0.008,
                quality_price_premium_pct=0.02,  # 2% price premium
                conversion_cost_reduction_pct=0.04,  # 4% cost reduction
                segment_allocation={'Flat-Rolled': 0.50, 'Mini Mill': 0.30, 'USSE': 0.15, 'Tubular': 0.05},
                ramp_schedule=technology_ramp,
                confidence=0.70
            ),
            revenue=RevenueSynergies(
                cross_sell_revenue_annual=200.0,  # $200M
                cross_sell_margin=0.15,
                cross_sell_confidence=0.60,
                product_mix_revenue_uplift=150.0,  # $150M
                product_mix_margin=0.20,
                product_mix_confidence=0.65,
                ramp_schedule=standard_ramp
            ),
            integration=IntegrationCosts(
                it_integration_cost=125.0,  # $125M
                it_spend_schedule=integration_schedule,
                cultural_integration_cost=50.0,  # $50M
                cultural_spend_schedule=integration_schedule,
                restructuring_cost=150.0,  # $150M
                restructuring_spend_schedule=integration_schedule
            ),
            enabled=True,
            overall_execution_factor=1.0
        ),

        'optimistic': SynergyAssumptions(
            name="Optimistic",
            description="Aggressive synergy targets assuming excellent execution",
            operating=OperatingSynergies(
                procurement_savings_annual=150.0,  # $150M
                procurement_confidence=0.80,
                logistics_savings_annual=100.0,  # $100M
                logistics_confidence=0.75,
                overhead_savings_annual=120.0,  # $120M
                overhead_confidence=0.85,
                ramp_schedule=standard_ramp
            ),
            technology=TechnologyTransfer(
                yield_improvement_pct=0.03,  # 3% yield improvement
                yield_margin_impact=0.008,
                quality_price_premium_pct=0.04,  # 4% price premium
                conversion_cost_reduction_pct=0.06,  # 6% cost reduction
                segment_allocation={'Flat-Rolled': 0.50, 'Mini Mill': 0.30, 'USSE': 0.15, 'Tubular': 0.05},
                ramp_schedule=technology_ramp,
                confidence=0.65
            ),
            revenue=RevenueSynergies(
                cross_sell_revenue_annual=400.0,  # $400M
                cross_sell_margin=0.15,
                cross_sell_confidence=0.60,
                product_mix_revenue_uplift=300.0,  # $300M
                product_mix_margin=0.20,
                product_mix_confidence=0.65,
                ramp_schedule=standard_ramp
            ),
            integration=IntegrationCosts(
                it_integration_cost=175.0,  # $175M
                it_spend_schedule=integration_schedule,
                cultural_integration_cost=75.0,  # $75M
                cultural_spend_schedule=integration_schedule,
                restructuring_cost=200.0,  # $200M
                restructuring_spend_schedule=integration_schedule
            ),
            enabled=True,
            overall_execution_factor=1.0
        ),
    }


# =============================================================================
# SEGMENT CONFIGURATIONS
# =============================================================================

def get_segment_configs() -> Dict[Segment, SegmentVolumePrice]:
    """Return base segment configurations from Excel data

    Product mix weights from USS 2023 10-K revenue by product type:
    - Flat-Rolled: HRC 21%, CRC 40%, Coated 39% (was 100% HRC)
    - Mini Mill: HRC 55%, CRC 16%, Coated 29% (was 100% HRC)
    - USSE: HRC 51%, CRC 8%, Coated 40% (uses EU benchmarks)
    - Tubular: 100% OCTG (unchanged)

    Premium calibrations recalculated for weighted-average benchmark pricing.
    """

    return {
        Segment.FLAT_ROLLED: SegmentVolumePrice(
            name="Flat-Rolled",
            base_shipments_2023=8706,  # 000 tons
            volume_growth_rate=-0.005,  # Slight decline as mini mills gain share
            capacity_utilization_2023=0.712,
            max_capacity_utilization=0.85,
            base_price_2023=1030,  # $/ton realized from 10-K
            price_growth_rate=0.02,
            price_premium_to_benchmark=0.044,  # Premium: $1030 / $987 through-cycle weighted - 1
            benchmark_type='hrc_us',  # Fallback (not used when product_mix is set)
            # 2023 10-K: HRC $1,926M (21%), CRC $3,568M (40%), Coated $3,484M (39%)
            # Weighted benchmark: 0.21×$738 + 0.40×$994 + 0.39×$1113 = $987
            product_mix={'hrc_us': 0.21, 'crc_us': 0.40, 'coated_us': 0.39},
            ebitda_margin_at_base_price=0.12,  # ~11% actual 2023
            margin_sensitivity_to_price=0.02,  # 2% margin change per $100 price (halved from 4% to reduce unrealistic operating leverage)
            da_pct_of_revenue=0.055,
            maintenance_capex_pct=0.045,  # Reduced for better FCF
            dso=28, dih=55, dpo=60
        ),

        Segment.MINI_MILL: SegmentVolumePrice(
            name="Mini Mill",
            base_shipments_2023=2424,
            volume_growth_rate=0.025,  # Gaining share
            capacity_utilization_2023=0.895,
            max_capacity_utilization=0.95,
            base_price_2023=875,
            price_growth_rate=0.02,
            price_premium_to_benchmark=-0.014,  # Discount: $875 / $888 through-cycle weighted - 1
            benchmark_type='hrc_us',  # Fallback (not used when product_mix is set)
            # 2023 10-K: HRC $1,215M (55%), CRC $365M (16%), Coated $639M (29%)
            # Weighted benchmark: 0.55×$738 + 0.16×$994 + 0.29×$1113 = $888
            product_mix={'hrc_us': 0.55, 'crc_us': 0.16, 'coated_us': 0.29},
            ebitda_margin_at_base_price=0.17,  # ~17% actual 2023
            margin_sensitivity_to_price=0.025,  # 2.5% margin change per $100 price (halved from 5%)
            da_pct_of_revenue=0.045,
            maintenance_capex_pct=0.034,
            dso=22, dih=40, dpo=70
        ),

        Segment.USSE: SegmentVolumePrice(
            name="USSE",
            base_shipments_2023=3899,
            volume_growth_rate=0.0,
            capacity_utilization_2023=0.879,
            max_capacity_utilization=0.90,
            base_price_2023=873,
            price_growth_rate=0.01,
            price_premium_to_benchmark=0.044,  # Premium: $873 / $836 through-cycle weighted - 1
            benchmark_type='hrc_eu',  # Fallback (not used when product_mix is set)
            # 2023 10-K: HRC $1,637M (51%), CRC $269M (8%), Coated $1,278M (40%)
            # Weighted benchmark: 0.51×$611 + 0.08×$994 + 0.40×$1113 = $836
            product_mix={'hrc_eu': 0.51, 'crc_us': 0.08, 'coated_us': 0.40},
            ebitda_margin_at_base_price=0.09,  # ~9% actual 2023
            margin_sensitivity_to_price=0.02,  # 2% margin change per $100 price (halved from 4%)
            da_pct_of_revenue=0.050,
            maintenance_capex_pct=0.027,
            dso=30, dih=50, dpo=65
        ),

        Segment.TUBULAR: SegmentVolumePrice(
            name="Tubular",
            base_shipments_2023=478,
            volume_growth_rate=0.015,
            capacity_utilization_2023=0.631,
            max_capacity_utilization=0.85,
            base_price_2023=3137,
            price_growth_rate=0.02,
            price_premium_to_benchmark=0.314,  # Premium: $3137 / $2388 through-cycle OCTG - 1
            benchmark_type='octg',
            # Tubular is 100% OCTG products
            product_mix={'octg': 1.0},
            ebitda_margin_at_base_price=0.26,  # ~26% actual 2023
            margin_sensitivity_to_price=0.01,  # 1% margin change per $100 price (halved from 2%)
            da_pct_of_revenue=0.060,
            maintenance_capex_pct=0.040,
            dso=35, dih=60, dpo=55
        ),
    }


def get_capital_projects() -> Dict[str, CapitalProject]:
    """Return capital project configurations with dynamic EBITDA parameters.

    Dynamic EBITDA is calculated using:
        EBITDA = Capacity × Utilization × Price × Margin

    Terminal Value is calculated using:
        TV = Final Year EBITDA × Terminal Multiple (EV/EBITDA)

    Sources:
    - Capacity & Margins: Capital Projects EBITDA Impact Analysis (Feb 2026)
    - Terminal Multiples: WRDS peer company EV/EBITDA analysis (2019-2025)

    Target EBITDA by Project (from sourced document):
    - BR2 Mini Mill:      $459M (3,000 kt × $900 × 17%)
    - Gary Works BF:      $285M (2,500 kt × $950 × 12%)
    - Mon Valley HSM:     $205M (1,800 kt × $950 × 12%)
    - Greenfield:         $77M  (500 kt × $900 × 17%)
    - Mining Investment:  $108M (6,000 kt × $150 × 12%)
    - Fairfield Works:    $130M (1,200 kt × $900 × 12%)
    - TOTAL:              $1,264M

    Margin Rules by Technology:
    - EAF Mini Mill: 17% (conservative vs. 20%+ management target)
    - Blast Furnace: 12% (post-upgrade efficiency)
    - Mining: 12% (cost avoidance mechanism)
    - Tubular/OCTG: 12% (integrated operations)

    Terminal Multiple Rules (from WRDS peer comparables):
    - EAF Mini Mill: 7x EBITDA (peer median: STLD 7.8x, NUE 7.9x, CMC 5.8x)
    - Blast Furnace: 5x EBITDA (peer median: MT 4.7x, PKX 6.2x, TX 3.3x)
    - Mining: 5x EBITDA (similar to integrated assets)
    - Tubular/OCTG: 6x EBITDA (blended, specialty premium)

    Maintenance CapEx Rules (annual sustaining capital):
    - EAF Mini Mill: $20/ton (newer equipment, lower maintenance)
    - Blast Furnace: $40/ton (complex equipment, higher maintenance)
    - Hot Strip Mill: $35/ton (rolling equipment, moderate maintenance)
    - Mining: $8/ton (equipment replacement, pit development)
    - Tubular: $25/ton (specialized equipment)
    """

    return {
        'BR2 Mini Mill': CapitalProject(
            name='BR2 Mini Mill',
            segment='Mini Mill',
            enabled=True,
            capex_schedule={2025: 200, 2026: 800, 2027: 900, 2028: 1300},
            # Dynamic EBITDA: 3,000 kt × $900 × 17% = $459M (source: EBITDA Impact Analysis)
            nameplate_capacity=3000,      # 3,000 kt/year (Nippon presentation)
            base_utilization=1.0,         # 100% steady-state
            ebitda_margin=0.17,           # 17% EAF margin (conservative vs. 20%+ target)
            capacity_ramp={               # Ramp: 30-40% → 60-85% → 90-100%
                2025: 0.20, 2026: 0.60, 2027: 0.90,
                2028: 1.0, 2029: 1.0, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0
            },
            terminal_multiple=7.0,        # 7x EBITDA (EAF peer median from WRDS)
            maintenance_capex_per_ton=20, # $20/ton - EAF lower maintenance than BF
            # Legacy (retained for reference)
            ebitda_schedule={2024: 0, 2025: 100, 2026: 300, 2027: 450, 2028: 560,
                            2029: 560, 2030: 560, 2031: 560, 2032: 560, 2033: 560},
            volume_addition={2025: 200, 2026: 500, 2027: 750, 2028: 1000,
                            2029: 1000, 2030: 1000, 2031: 1000, 2032: 1000, 2033: 1000}
        ),
        'Gary Works BF': CapitalProject(
            name='Gary Works BF',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2025: 400, 2026: 900, 2027: 800, 2028: 1100},
            # Dynamic EBITDA: 2,500 kt × $950 × 12% = $285M (source: EBITDA Impact Analysis)
            # Mixed mechanism: 70% asset preservation + 30% efficiency improvement
            nameplate_capacity=2500,      # 2,500 kt/year incremental effective capacity
            base_utilization=1.0,         # 100% steady-state
            ebitda_margin=0.12,           # 12% BF margin (post-upgrade efficiency)
            capacity_ramp={2028: 0.50, 2029: 0.90, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0},
            terminal_multiple=5.0,        # 5x EBITDA (Integrated peer median from WRDS)
            maintenance_capex_per_ton=40, # $40/ton - BF higher maintenance than EAF
            # Legacy (retained for reference)
            ebitda_schedule={2027: 100, 2028: 300, 2029: 402, 2030: 402,
                            2031: 402, 2032: 402, 2033: 402}
        ),
        'Mon Valley HSM': CapitalProject(
            name='Mon Valley HSM',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2025: 100, 2026: 700, 2027: 700, 2028: 900},
            # Dynamic EBITDA: 1,800 kt × $950 × 12% = $205M (source: EBITDA Impact Analysis)
            # Mechanism: 80% efficiency improvement + 20% premium product capability
            nameplate_capacity=1800,      # 1,800 kt/year (current 2,800 kt, but EBITDA from improvements)
            base_utilization=1.0,         # 100% steady-state
            ebitda_margin=0.12,           # 12% integrated margin
            capacity_ramp={2028: 0.50, 2029: 0.90, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0},
            terminal_multiple=5.0,        # 5x EBITDA (Integrated peer median from WRDS)
            maintenance_capex_per_ton=35, # $35/ton - HSM slightly lower than full BF
            # Legacy (retained for reference)
            ebitda_schedule={2026: 50, 2027: 100, 2028: 130, 2029: 130,
                            2030: 130, 2031: 130, 2032: 130, 2033: 130}
        ),
        'Greenfield Mini Mill': CapitalProject(
            name='Greenfield Mini Mill',
            segment='Mini Mill',
            enabled=False,
            capex_schedule={2028: 1000},
            # Dynamic EBITDA: 500 kt × $900 × 17% = $77M (source: EBITDA Impact Analysis)
            # Strategic option with minimal near-term impact; post-2028 greenfield
            nameplate_capacity=500,       # 500 kt/year (conservative; document says 0.5-1.0 Mt)
            base_utilization=1.0,         # 100% steady-state (post-ramp)
            ebitda_margin=0.17,           # 17% EAF margin (lower during ramp per document)
            capacity_ramp={2029: 0.50, 2030: 0.80, 2031: 1.0, 2032: 1.0, 2033: 1.0},
            terminal_multiple=7.0,        # 7x EBITDA (EAF peer median from WRDS)
            maintenance_capex_per_ton=20, # $20/ton - EAF lower maintenance
            # Legacy (retained for reference)
            ebitda_schedule={2027: 50, 2028: 150, 2029: 274, 2030: 274,
                            2031: 274, 2032: 274, 2033: 274},
            volume_addition={2027: 100, 2028: 300, 2029: 500, 2030: 500,
                            2031: 500, 2032: 500, 2033: 500}
        ),
        'Mining Investment': CapitalProject(
            name='Mining Investment',
            segment='Mining',             # Iron ore pellets - uses price override, not segment price
            enabled=False,
            capex_schedule={2025: 200, 2026: 200, 2027: 300, 2028: 300},
            # Dynamic EBITDA: 6,000 kt × $150 × 12% = $108M (source: EBITDA Impact Analysis)
            # Mechanism: 100% cost avoidance through vertical integration
            nameplate_capacity=6000,      # 6,000 kt/year pellets (Keetac + Minntac)
            base_utilization=1.0,         # 100% steady-state
            ebitda_margin=0.12,           # 12% mining margin (cost savings mechanism)
            base_price_override=150,      # $150/ton pellets (not steel price)
            capacity_ramp={2026: 0.50, 2027: 0.90, 2028: 1.0, 2029: 1.0,
                          2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0},
            terminal_multiple=5.0,        # 5x EBITDA (similar to integrated assets)
            maintenance_capex_per_ton=8,  # $8/ton - mining equipment, pit development
            # Legacy (retained for reference)
            ebitda_schedule={2025: 20, 2026: 50, 2027: 80, 2028: 80,
                            2029: 80, 2030: 80, 2031: 80, 2032: 80, 2033: 80}
        ),
        'Fairfield Works': CapitalProject(
            name='Fairfield Works',
            segment='Tubular',            # Tubular segment
            enabled=False,
            capex_schedule={2025: 200, 2026: 200, 2027: 100, 2028: 100},
            # Dynamic EBITDA: 1,200 kt × $900 × 12% = $130M (source: EBITDA Impact Analysis)
            # Mechanism: 60% efficiency improvement + 40% capacity expansion
            nameplate_capacity=1200,      # 1,200 kt/year (current 1.5 Mt, targeting 1.8-2.0 Mt)
            base_utilization=1.0,         # 100% steady-state
            ebitda_margin=0.12,           # 12% margin (document notes highest ROIC project)
            capacity_ramp={2026: 0.50, 2027: 0.90, 2028: 1.0, 2029: 1.0,
                          2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0},
            terminal_multiple=6.0,        # 6x EBITDA (blended, specialty OCTG premium)
            maintenance_capex_per_ton=25, # $25/ton - tubular specialized equipment
            # Legacy (retained for reference)
            ebitda_schedule={2026: 20, 2027: 40, 2028: 60, 2029: 60,
                            2030: 60, 2031: 60, 2032: 60, 2033: 60}
        ),
    }


# =============================================================================
# MODEL ENGINE
# =============================================================================

class PriceVolumeModel:
    """Enhanced DCF model with price x volume revenue drivers

    Args:
        scenario: ModelScenario configuration
        execution_factor: Float 0.0-1.0 representing execution success rate.
                         1.0 = 100% of projected benefits achieved
                         0.75 = 75% of projected benefits achieved (25% haircut)
                         Only applies to incremental projects (not BR2 which is committed)
    """

    def __init__(self, scenario: ModelScenario, execution_factor: float = 1.0, custom_benchmarks: dict = None, progress_callback=None):
        """
        Initialize PriceVolumeModel

        Args:
            scenario: ModelScenario with all assumptions
            execution_factor: Execution risk factor for Nippon Commitments (0.5-1.0)
            custom_benchmarks: Optional custom benchmark prices dict
            progress_callback: Optional function(percent, message) for progress updates
        """
        self.scenario = scenario
        self.execution_factor = execution_factor
        self.custom_benchmarks = custom_benchmarks or BENCHMARK_PRICES_2023
        self.progress_callback = progress_callback
        self.years = list(range(2024, 2034))
        self.segments = get_segment_configs()
        self.projects = get_capital_projects()

        # Enable projects based on scenario
        for proj_name in scenario.include_projects:
            if proj_name in self.projects:
                self.projects[proj_name].enabled = True

    def _report_progress(self, percent: int, message: str):
        """Report progress via callback if provided."""
        if self.progress_callback is not None:
            self.progress_callback(percent, message)

    def get_benchmark_price(self, benchmark_type: str, year: int) -> float:
        """Calculate benchmark price for a given year, including tariff adjustment"""
        base_price = self.custom_benchmarks.get(benchmark_type, 700)
        price_scenario = self.scenario.price_scenario

        # Get the factor for this benchmark
        factor_map = {
            'hrc_us': price_scenario.hrc_us_factor,
            'crc_us': price_scenario.crc_us_factor,
            'coated_us': price_scenario.coated_us_factor,
            'hrc_eu': price_scenario.hrc_eu_factor,
            'octg': price_scenario.octg_factor,
        }

        initial_factor = factor_map.get(benchmark_type, 1.0)
        years_from_base = year - 2024

        # Tariff adjustment (1.0 when tariff_rate = embedded 0.25)
        tariff_rate = getattr(price_scenario, 'tariff_rate', 0.25)
        tariff_adj = calculate_tariff_adjustment(tariff_rate, benchmark_type)

        # Apply initial factor, tariff adjustment, then annual growth
        growth_compound = (1 + price_scenario.annual_price_growth) ** years_from_base
        price = base_price * initial_factor * tariff_adj * growth_compound

        return price

    def calculate_segment_price(self, segment: Segment, year: int) -> float:
        """Calculate realized price for a segment in a given year.

        Uses weighted-average pricing based on actual product mix if available,
        otherwise falls back to single benchmark_type for backward compatibility.
        """
        seg = self.segments[segment]

        # Use weighted-average pricing if product_mix is defined
        if seg.product_mix:
            weighted_price = 0.0
            for benchmark_type, weight in seg.product_mix.items():
                benchmark_price = self.get_benchmark_price(benchmark_type, year)
                weighted_price += benchmark_price * weight
            benchmark_price = weighted_price
        else:
            # Fallback to single benchmark for backward compatibility
            benchmark_price = self.get_benchmark_price(seg.benchmark_type, year)

        # Apply segment premium and specific growth
        realized_price = benchmark_price * (1 + seg.price_premium_to_benchmark)

        return realized_price

    def calculate_segment_volume(self, segment: Segment, year: int) -> float:
        """Calculate shipment volume for a segment in a given year"""
        seg = self.segments[segment]
        vol_scenario = self.scenario.volume_scenario

        # Get volume factor and growth adjustment for this segment
        factor_map = {
            Segment.FLAT_ROLLED: (vol_scenario.flat_rolled_volume_factor, vol_scenario.flat_rolled_growth_adj),
            Segment.MINI_MILL: (vol_scenario.mini_mill_volume_factor, vol_scenario.mini_mill_growth_adj),
            Segment.USSE: (vol_scenario.usse_volume_factor, vol_scenario.usse_growth_adj),
            Segment.TUBULAR: (vol_scenario.tubular_volume_factor, vol_scenario.tubular_growth_adj),
        }

        vol_factor, growth_adj = factor_map[segment]
        years_from_base = year - 2023

        # Base volume with factor, then growth
        effective_growth = seg.volume_growth_rate + growth_adj
        volume = seg.base_shipments_2023 * vol_factor * ((1 + effective_growth) ** years_from_base)

        # Add project volumes (apply execution factor to non-BR2 projects)
        for proj in self.projects.values():
            if proj.enabled and proj.segment == seg.name:
                vol_add = proj.volume_addition.get(year, 0)
                # BR2 is committed/in-progress, don't haircut it
                if proj.name != 'BR2 Mini Mill':
                    vol_add *= self.execution_factor
                volume += vol_add

        return volume

    def calculate_segment_margin(self, segment: Segment, realized_price: float) -> float:
        """Calculate EBITDA margin based on price level"""
        seg = self.segments[segment]

        # Margin adjusts with price level
        price_change = realized_price - seg.base_price_2023
        margin_adj = (price_change / 100) * seg.margin_sensitivity_to_price

        margin = seg.ebitda_margin_at_base_price + margin_adj

        # Floor and ceiling
        return max(0.02, min(0.22, margin))

    def get_segment_volume_factor(self, segment_name: str) -> float:
        """Get the volume factor for a segment from the scenario.

        Links capital project utilization to segment demand assumptions.

        Args:
            segment_name: Segment name (e.g., 'Mini Mill', 'Flat-Rolled')

        Returns:
            Volume factor (0.0-1.5+) from scenario's volume_scenario
        """
        vol = self.scenario.volume_scenario
        factor_map = {
            'Mini Mill': vol.mini_mill_volume_factor,
            'Flat-Rolled': vol.flat_rolled_volume_factor,
            'Tubular': vol.tubular_volume_factor,
            'USSE': vol.usse_volume_factor,
            'Mining': 1.0,  # Mining not affected by steel demand
        }
        return factor_map.get(segment_name, 1.0)

    def calculate_project_ebitda(self, project: CapitalProject, year: int,
                                  segment_price: float) -> float:
        """Calculate project EBITDA dynamically based on capacity, price, margin.

        Formula: Capacity × Utilization × Volume Factor × Price × Margin

        The volume factor links project utilization to segment demand:
        - If Mini Mill volume factor is 0.8, BR2 utilization scales to 80%
        - This reflects that lower market demand affects project performance

        Args:
            project: CapitalProject instance with capacity/margin parameters
            year: Projection year
            segment_price: $/ton price from scenario for this segment

        Returns:
            Project EBITDA in $M for the given year
        """
        # If no dynamic parameters configured, fall back to legacy schedule
        if project.nameplate_capacity == 0:
            return project.ebitda_schedule.get(year, 0)

        # Get utilization for this year from ramp schedule
        # If year is explicitly in ramp, use that value
        # If year is BEFORE first ramp year, project not yet operational (0%)
        # If year is AFTER last ramp year, use base_utilization (steady state)
        if year in project.capacity_ramp:
            utilization = project.capacity_ramp[year]
        elif project.capacity_ramp:
            min_ramp_year = min(project.capacity_ramp.keys())
            max_ramp_year = max(project.capacity_ramp.keys())
            if year < min_ramp_year:
                utilization = 0.0  # Project not yet operational
            elif year > max_ramp_year:
                utilization = project.base_utilization  # Steady state
            else:
                # Year is between min and max but not specified - interpolate or use base
                utilization = project.base_utilization
        else:
            # No ramp schedule defined, use base utilization
            utilization = project.base_utilization

        # Apply segment volume factor to link project to market demand
        volume_factor = self.get_segment_volume_factor(project.segment)
        utilization *= volume_factor

        # Effective volume: capacity × utilization (in kt)
        effective_volume = project.nameplate_capacity * utilization

        # Apply execution factor for non-BR2 projects
        if project.name != 'BR2 Mini Mill':
            effective_volume *= self.execution_factor

        # Use price override for mining (pellets are $150/ton, not steel price)
        price = project.base_price_override if project.base_price_override else segment_price

        # Revenue: volume (kt) × price ($/ton) / 1000 = $M
        project_revenue = (effective_volume * price) / 1000

        # EBITDA: revenue × margin
        return project_revenue * project.ebitda_margin

    def calculate_project_maintenance_capex(self, project: CapitalProject, year: int) -> float:
        """Calculate annual maintenance capex for a project.

        Maintenance capex is required to sustain operations after construction
        is COMPLETE. No maintenance capex during construction years.

        Formula: Effective Volume × Maintenance CapEx per Ton / 1000

        Typical values by technology:
        - EAF Mini Mill: $20/ton (newer equipment, lower maintenance)
        - Blast Furnace: $40/ton (complex equipment, higher maintenance)
        - Mining: $8/ton (equipment replacement, pit development)
        - Tubular: $25/ton (specialized equipment)

        Args:
            project: CapitalProject instance
            year: Projection year

        Returns:
            Maintenance capex in $M for the given year
        """
        if project.maintenance_capex_per_ton == 0:
            return 0.0

        # No maintenance capex until construction is complete
        if project.capex_schedule:
            last_construction_year = max(project.capex_schedule.keys())
            if year <= last_construction_year:
                return 0.0  # Still under construction

        # After construction, use steady-state utilization for maintenance
        utilization = project.base_utilization

        # Effective volume at steady state
        effective_volume = project.nameplate_capacity * utilization

        # Maintenance capex: volume (kt) × $/ton / 1000 = $M
        return (effective_volume * project.maintenance_capex_per_ton) / 1000

    def build_segment_projection(self, segment: Segment) -> pd.DataFrame:
        """Build full projection for a segment"""
        seg = self.segments[segment]
        results = []

        prev_nwc = 0

        for year in self.years:
            # Price x Volume = Revenue
            volume = self.calculate_segment_volume(segment, year)  # 000 tons
            price = self.calculate_segment_price(segment, year)  # $/ton
            revenue = (volume * price) / 1000  # $M (volume in 000 tons, price in $/ton)

            # Margin based on price level
            margin = self.calculate_segment_margin(segment, price)
            base_ebitda = revenue * margin

            # Calculate project EBITDA dynamically (responds to scenario prices)
            project_ebitda = 0
            project_capex = 0
            for proj in self.projects.values():
                if proj.enabled and proj.segment == seg.name:
                    # Use dynamic calculation based on capacity, utilization, price, margin
                    # Note: execution_factor is applied inside calculate_project_ebitda()
                    project_ebitda += self.calculate_project_ebitda(
                        project=proj,
                        year=year,
                        segment_price=price
                    )
                    project_capex += proj.capex_schedule.get(year, 0)

            total_ebitda = base_ebitda + project_ebitda

            # D&A and EBIT
            da = revenue * seg.da_pct_of_revenue
            ebit = total_ebitda - da

            # NOPAT (using 16.9% cash tax rate)
            cash_tax_rate = 0.169
            nopat = ebit * (1 - cash_tax_rate)

            # Gross Cash Flow
            gross_cf = nopat + da

            # CapEx
            maintenance_capex = revenue * seg.maintenance_capex_pct
            total_capex = maintenance_capex + project_capex

            # Working Capital
            daily_revenue = revenue / 365
            current_nwc = daily_revenue * seg.dso + daily_revenue * seg.dih - daily_revenue * seg.dpo
            delta_wc = prev_nwc - current_nwc

            # FCF
            fcf = gross_cf - total_capex + delta_wc

            results.append({
                'Year': year,
                'Segment': seg.name,
                'Volume_000tons': volume,
                'Price_per_ton': price,
                'Revenue': revenue,
                'EBITDA_Margin': margin,
                'Total_EBITDA': total_ebitda,
                'DA': da,
                'EBIT': ebit,
                'NOPAT': nopat,
                'Gross_CF': gross_cf,
                'Total_CapEx': total_capex,
                'Delta_WC': delta_wc,
                'FCF': fcf
            })

            prev_nwc = current_nwc

        return pd.DataFrame(results)

    def build_consolidated(self) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Build consolidated projection from all segments with progress tracking"""
        segment_dfs = {}
        segments_list = list(Segment)

        for i, segment in enumerate(segments_list, 1):
            # Report progress for each segment (10-40% range)
            self._report_progress(
                int(10 + (i / len(segments_list)) * 30),
                f"Projecting {segment.value.replace('_', ' ').title()} segment..."
            )
            segment_dfs[segment.value] = self.build_segment_projection(segment)

        # Consolidate
        self._report_progress(38, "Consolidating segments...")
        consolidated = []
        metrics = ['Revenue', 'Total_EBITDA', 'DA', 'NOPAT', 'Gross_CF', 'Total_CapEx', 'Delta_WC', 'FCF']

        for year in self.years:
            row = {'Year': year}
            for metric in metrics:
                row[metric] = sum(
                    df[df['Year'] == year][metric].values[0]
                    for df in segment_dfs.values()
                )

            # Weighted average volume and price
            total_volume = sum(
                df[df['Year'] == year]['Volume_000tons'].values[0]
                for df in segment_dfs.values()
            )
            row['Total_Volume_000tons'] = total_volume
            row['Avg_Price_per_ton'] = row['Revenue'] * 1000 / total_volume if total_volume > 0 else 0
            row['EBITDA_Margin'] = row['Total_EBITDA'] / row['Revenue'] if row['Revenue'] > 0 else 0

            consolidated.append(row)

        return pd.DataFrame(consolidated), segment_dfs

    def calculate_synergy_impact(self, year: int, consolidated_df: pd.DataFrame,
                                  segment_dfs: Dict[str, pd.DataFrame]) -> Dict:
        """Calculate synergy impact for a given year

        Returns dict with:
        - operating_synergy: $M EBITDA from operating synergies
        - technology_synergy: $M EBITDA from technology transfer
        - revenue_synergy: $M EBITDA from revenue synergies
        - integration_cost: $M one-time integration costs
        - total_synergy_ebitda: Net synergy EBITDA contribution
        """
        syn = self.scenario.synergies

        # If synergies not enabled, return zeros
        if syn is None or not syn.enabled:
            return {
                'operating_synergy': 0.0,
                'technology_synergy': 0.0,
                'revenue_synergy': 0.0,
                'integration_cost': 0.0,
                'total_synergy_ebitda': 0.0
            }

        exec_factor = syn.overall_execution_factor

        # Operating synergies
        op = syn.operating
        op_ramp = op.ramp_schedule.get_realization(year)
        operating_synergy = (
            op.procurement_savings_annual * op.procurement_confidence +
            op.logistics_savings_annual * op.logistics_confidence +
            op.overhead_savings_annual * op.overhead_confidence
        ) * op_ramp * exec_factor

        # Technology transfer synergies
        tech = syn.technology
        tech_ramp = tech.ramp_schedule.get_realization(year)

        # Calculate technology EBITDA impact based on segment revenues
        technology_synergy = 0.0
        year_data = consolidated_df[consolidated_df['Year'] == year]
        if len(year_data) > 0:
            total_revenue = year_data['Revenue'].values[0]
            current_ebitda = year_data['Total_EBITDA'].values[0]

            # Yield improvement: 1% yield gain = ~0.8% margin improvement (industry rule of thumb)
            # 2% yield improvement = 1.6% margin = $240M on $15B revenue
            yield_ebitda_boost = total_revenue * tech.yield_improvement_pct * tech.yield_margin_impact

            # Quality price premium: premium on revenue flows through at ~50% margin
            # 2% price premium on $15B = $300M revenue -> $150M EBITDA
            quality_ebitda_boost = total_revenue * tech.quality_price_premium_pct * 0.5

            # Conversion cost reduction: applied to cost base (~85% of revenue at 15% margin)
            # 4% reduction on $12.75B cost base = $510M -> but EBITDA impact is the savings
            cost_base = total_revenue - current_ebitda
            conversion_savings = cost_base * tech.conversion_cost_reduction_pct * 0.2  # 20% flowthrough to EBITDA

            # Combined technology synergy
            technology_synergy = (yield_ebitda_boost + quality_ebitda_boost + conversion_savings) * tech.confidence * tech_ramp * exec_factor

        # Revenue synergies
        rev = syn.revenue
        rev_ramp = rev.ramp_schedule.get_realization(year)
        revenue_synergy = (
            rev.cross_sell_revenue_annual * rev.cross_sell_margin * rev.cross_sell_confidence +
            rev.product_mix_revenue_uplift * rev.product_mix_margin * rev.product_mix_confidence
        ) * rev_ramp * exec_factor

        # Integration costs (one-time, deducted from EBITDA)
        integration_cost = syn.integration.get_cost_for_year(year)

        # Net synergy EBITDA
        total_synergy_ebitda = operating_synergy + technology_synergy + revenue_synergy - integration_cost

        return {
            'operating_synergy': operating_synergy,
            'technology_synergy': technology_synergy,
            'revenue_synergy': revenue_synergy,
            'integration_cost': integration_cost,
            'total_synergy_ebitda': total_synergy_ebitda
        }

    def build_synergy_schedule(self, consolidated_df: pd.DataFrame,
                                segment_dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Build year-by-year synergy schedule

        Returns DataFrame with columns:
        - Year
        - Operating_Synergy: $M from procurement, logistics, overhead
        - Technology_Synergy: $M from yield, quality, conversion improvements
        - Revenue_Synergy: $M from cross-sell and product mix
        - Integration_Cost: $M one-time costs
        - Total_Synergy_EBITDA: Net synergy contribution
        - Cumulative_Synergy: Running total
        """
        results = []
        cumulative = 0.0

        for year in self.years:
            impact = self.calculate_synergy_impact(year, consolidated_df, segment_dfs)
            cumulative += impact['total_synergy_ebitda']

            results.append({
                'Year': year,
                'Operating_Synergy': impact['operating_synergy'],
                'Technology_Synergy': impact['technology_synergy'],
                'Revenue_Synergy': impact['revenue_synergy'],
                'Integration_Cost': impact['integration_cost'],
                'Total_Synergy_EBITDA': impact['total_synergy_ebitda'],
                'Cumulative_Synergy': cumulative
            })

        return pd.DataFrame(results)

    def calculate_synergy_value(self, synergy_schedule: pd.DataFrame, wacc: float) -> Dict:
        """Calculate NPV of synergies

        Args:
            synergy_schedule: DataFrame from build_synergy_schedule
            wacc: Discount rate to use (typically Nippon USD WACC)

        Returns:
            Dict with synergy valuation metrics
        """
        if synergy_schedule is None or len(synergy_schedule) == 0:
            return {
                'npv_synergies': 0.0,
                'run_rate_synergies': 0.0,
                'total_integration_costs': 0.0,
                'synergy_value_per_share': 0.0
            }

        # Get FCF from synergies (EBITDA less taxes, assume 16.9% cash tax)
        synergy_fcf = synergy_schedule['Total_Synergy_EBITDA'].values * (1 - 0.169)

        # Discount synergy FCF
        n_years = len(synergy_fcf)
        discount_factors = [(1 / (1 + wacc)) ** (i + 1) for i in range(n_years)]
        pv_synergies = sum(f * d for f, d in zip(synergy_fcf, discount_factors))

        # Terminal value of run-rate synergies (at year 10 run-rate)
        terminal_synergy = synergy_fcf[-1] * (1 + self.scenario.terminal_growth)
        tv_synergy = terminal_synergy / (wacc - self.scenario.terminal_growth) if wacc > self.scenario.terminal_growth else 0
        pv_tv_synergy = tv_synergy * discount_factors[-1]

        npv_synergies = pv_synergies + pv_tv_synergy

        # Summary metrics
        run_rate = synergy_schedule['Total_Synergy_EBITDA'].iloc[-1]
        total_integration = synergy_schedule['Integration_Cost'].sum()

        return {
            'npv_synergies': npv_synergies,
            'run_rate_synergies': run_rate,
            'total_integration_costs': total_integration,
            'synergy_value_per_share': npv_synergies / 225.0  # Assuming 225M shares
        }

    def calculate_irp_wacc(self) -> Tuple[float, float, Optional[dict]]:
        """Calculate JPY WACC and IRP-adjusted USD WACC

        Now properly linked to JGB rate:
        - Cost of Equity = JGB + Equity Risk Premium
        - Cost of Debt = JGB + Credit Spread

        If use_verified_wacc is True, loads WACC from wacc-calculations module.
        If override_irp is True, uses manual_nippon_usd_wacc instead of IRP formula.

        Returns:
            Tuple of (jpy_wacc, usd_wacc, audit_trail)
            audit_trail is populated when use_verified_wacc=True
        """
        s = self.scenario
        audit_trail = None

        # Option 1: Use verified WACC from wacc-calculations module
        if s.use_verified_wacc and WACC_MODULE_AVAILABLE:
            jpy_wacc, usd_wacc, nippon_audit = get_verified_nippon_wacc()
            if jpy_wacc is not None and usd_wacc is not None:
                audit_trail = {
                    'source': 'wacc-calculations module',
                    'nippon': nippon_audit,
                }
                return jpy_wacc, usd_wacc, audit_trail

        # Option 2: Manual override
        if s.override_irp and s.manual_nippon_usd_wacc is not None:
            # Calculate JPY WACC for reference even when using override
            nippon_cost_of_equity = s.japan_10yr + s.nippon_equity_risk_premium
            nippon_cost_of_debt = s.japan_10yr + s.nippon_credit_spread
            equity_weight = 1 - s.nippon_debt_ratio
            debt_weight = s.nippon_debt_ratio
            jpy_wacc = (
                equity_weight * nippon_cost_of_equity +
                debt_weight * nippon_cost_of_debt * (1 - s.nippon_tax_rate)
            )
            return jpy_wacc, s.manual_nippon_usd_wacc, None

        # Option 3: Default calculation from scenario parameters
        # Calculate Nippon's cost of capital components from JGB rate
        nippon_cost_of_equity = s.japan_10yr + s.nippon_equity_risk_premium
        nippon_cost_of_debt = s.japan_10yr + s.nippon_credit_spread

        # JPY WACC
        equity_weight = 1 - s.nippon_debt_ratio
        debt_weight = s.nippon_debt_ratio
        jpy_wacc = (
            equity_weight * nippon_cost_of_equity +
            debt_weight * nippon_cost_of_debt * (1 - s.nippon_tax_rate)
        )

        # IRP conversion to USD
        usd_wacc = (1 + jpy_wacc) * (1 + s.us_10yr) / (1 + s.japan_10yr) - 1

        return jpy_wacc, usd_wacc, audit_trail

    def calculate_financing_impact(self, df: pd.DataFrame) -> Dict:
        """Calculate the impact of financing capital projects on USS standalone value.

        This models the reality that USS cannot fund $14B in projects from FCF alone.
        They would need to:
        1. Issue debt (increasing interest expense and WACC)
        2. Issue equity (diluting shareholders)

        The financing gap is calculated as the cumulative negative FCF in years when
        FCF is negative (i.e., when CapEx exceeds operating cash flow).

        Returns financing adjustments to apply to USS standalone valuation.
        """
        fin = self.scenario.financing

        # Calculate total incremental project CapEx (beyond BR2 which is committed/funded)
        incremental_project_capex = 0
        has_incremental_projects = False
        for proj in self.projects.values():
            if proj.enabled and proj.name != 'BR2 Mini Mill':
                incremental_project_capex += sum(proj.capex_schedule.values())
                has_incremental_projects = True

        # Only apply financing penalty if there are projects beyond BR2
        # BR2 is already committed and funded, so no financing needed for it
        if not has_incremental_projects:
            return {
                'incremental_capex': 0,
                'financing_gap': 0,
                'new_debt': 0,
                'new_equity': 0,
                'new_shares': 0,
                'total_shares': fin.current_shares,
                'dilution_pct': 0,
                'annual_interest_expense': 0,
                'cumulative_interest_expense': 0,
                'wacc_adjustment': 0,
                'adjusted_wacc': self.scenario.uss_wacc,
                'total_debt': fin.current_debt,
                'debt_to_ebitda': 0
            }

        # Calculate the financing gap as cumulative negative FCF
        # This represents actual cash shortfall that needs to be financed
        cumulative_negative_fcf = sum(min(0, fcf) for fcf in df['FCF'].tolist())
        total_financing_gap = abs(cumulative_negative_fcf)

        # If no negative FCF, minimal financing needed
        if total_financing_gap == 0:
            return {
                'incremental_capex': incremental_project_capex,
                'financing_gap': 0,
                'new_debt': 0,
                'new_equity': 0,
                'new_shares': 0,
                'total_shares': fin.current_shares,
                'dilution_pct': 0,
                'annual_interest_expense': 0,
                'cumulative_interest_expense': 0,
                'wacc_adjustment': 0,
                'adjusted_wacc': self.scenario.uss_wacc,
                'total_debt': fin.current_debt,
                'debt_to_ebitda': 0
            }

        # Split financing between debt and equity
        new_debt = total_financing_gap * fin.debt_financing_pct
        new_equity = total_financing_gap * (1 - fin.debt_financing_pct)

        # Calculate debt impact
        total_debt = fin.current_debt + new_debt
        avg_ebitda = df['Total_EBITDA'].mean()
        debt_to_ebitda = total_debt / avg_ebitda if avg_ebitda > 0 else 0

        # WACC adjustment for increased leverage
        current_debt_to_ebitda = fin.current_debt / avg_ebitda if avg_ebitda > 0 else 0
        leverage_increase = debt_to_ebitda - current_debt_to_ebitda
        wacc_adjustment = leverage_increase * fin.wacc_increase_per_turn_leverage
        adjusted_wacc = self.scenario.uss_wacc + wacc_adjustment

        # Annual interest expense (after tax shield)
        # Assume debt is paid down over 10 years, so average outstanding is 50%
        avg_debt_outstanding = new_debt * 0.5
        annual_interest_expense = avg_debt_outstanding * fin.incremental_cost_of_debt * (1 - 0.25)

        # Calculate equity dilution
        # Assume equity issued at current implied price (we'll use $50 as proxy, adjusted for discount)
        assumed_issue_price = 50 * (1 - fin.equity_issuance_discount)  # 10% discount
        net_proceeds_per_share = assumed_issue_price * (1 - fin.equity_issuance_costs)  # 3% costs
        new_shares = new_equity / net_proceeds_per_share if net_proceeds_per_share > 0 else 0
        total_shares = fin.current_shares + new_shares
        dilution_pct = new_shares / fin.current_shares if fin.current_shares > 0 else 0

        return {
            'incremental_capex': incremental_project_capex,
            'financing_gap': total_financing_gap,
            'new_debt': new_debt,
            'new_equity': new_equity,
            'new_shares': new_shares,
            'total_shares': total_shares,
            'dilution_pct': dilution_pct,
            'annual_interest_expense': annual_interest_expense,
            'cumulative_interest_expense': annual_interest_expense * 10,
            'wacc_adjustment': wacc_adjustment,
            'adjusted_wacc': adjusted_wacc,
            'total_debt': total_debt,
            'debt_to_ebitda': debt_to_ebitda
        }

    def calculate_dcf(self, df: pd.DataFrame, wacc: float,
                       financing_impact: Optional[Dict] = None) -> Dict:
        """Calculate DCF valuation

        Args:
            df: Consolidated financial projection DataFrame
            wacc: Discount rate to use
            financing_impact: Optional dict with financing adjustments (for USS standalone)
                - If provided, applies interest expense deduction and uses diluted share count
        """
        s = self.scenario

        # Get FCF list, adjust for financing costs if applicable
        fcf_list = df['FCF'].tolist()

        # Apply interest expense deduction if financing impact provided
        if financing_impact and financing_impact.get('annual_interest_expense', 0) > 0:
            annual_interest = financing_impact['annual_interest_expense']
            # Reduce FCF by interest expense in early years (when debt is outstanding)
            fcf_list = [fcf - annual_interest for fcf in fcf_list]

        n_years = len(fcf_list)

        # Use adjusted WACC if financing impact provided
        effective_wacc = wacc
        if financing_impact and financing_impact.get('wacc_adjustment', 0) > 0:
            effective_wacc = financing_impact['adjusted_wacc']

        # Discount factors
        discount_factors = [(1 / (1 + effective_wacc)) ** (i + 1) for i in range(n_years)]
        pv_fcf = [f * d for f, d in zip(fcf_list, discount_factors)]
        sum_pv_fcf = sum(pv_fcf)

        # Terminal value - Gordon Growth
        terminal_fcf = fcf_list[-1] * (1 + s.terminal_growth)
        tv_gordon = terminal_fcf / (effective_wacc - s.terminal_growth) if effective_wacc > s.terminal_growth else 0
        pv_tv_gordon = tv_gordon * discount_factors[-1]

        # Terminal value - Exit Multiple
        terminal_ebitda = df['Total_EBITDA'].iloc[-1]
        # Use benchmark multiple if enabled, otherwise scenario default
        effective_multiple = s.exit_multiple
        if s.use_benchmark_multiples:
            benchmark_mult = get_benchmark_exit_multiple(s.name.lower(), use_benchmark=True)
            if benchmark_mult is not None:
                effective_multiple = benchmark_mult
        tv_exit = terminal_ebitda * effective_multiple
        pv_tv_exit = tv_exit * discount_factors[-1]

        # Enterprise values
        ev_gordon = sum_pv_fcf + pv_tv_gordon
        ev_exit = sum_pv_fcf + pv_tv_exit
        ev_blended = (ev_gordon + ev_exit) / 2

        # Equity bridge - adjust for new debt if financing impact provided
        base_debt = 4222.0
        if financing_impact:
            total_debt = financing_impact.get('total_debt', base_debt)
        else:
            total_debt = base_debt

        pension = 126.0
        leases = 117.0
        cash = 3013.9
        investments = 761.0

        # Use diluted share count if financing impact provided
        if financing_impact:
            shares = financing_impact.get('total_shares', 225.0)
        else:
            shares = 225.0

        equity_bridge = -total_debt - pension - leases + cash + investments

        # Calculate equity value and apply floor at zero
        # Shareholders have limited liability - they can lose their entire investment but no more
        equity_value = ev_blended + equity_bridge
        equity_value_floored = max(0, equity_value)
        share_price = equity_value_floored / shares

        return {
            'wacc': effective_wacc,
            'fcf_list': fcf_list,
            'pv_fcf': pv_fcf,
            'sum_pv_fcf': sum_pv_fcf,
            'tv_gordon': tv_gordon,
            'tv_exit': tv_exit,
            'pv_tv_gordon': pv_tv_gordon,
            'pv_tv_exit': pv_tv_exit,
            'ev_gordon': ev_gordon,
            'ev_exit': ev_exit,
            'ev_blended': ev_blended,
            'equity_bridge': equity_bridge,
            'share_price': share_price,
            'terminal_ebitda': terminal_ebitda,
            'shares_used': shares,
            'financing_impact': financing_impact,
            'exit_multiple_used': effective_multiple,
            'used_benchmark_multiple': s.use_benchmark_multiples and effective_multiple != s.exit_multiple
        }

    def run_full_analysis(self) -> Dict:
        """Run complete analysis and return all results with progress tracking

        Key insight: USS standalone ("USS - No Sale") valuation must account for the cost
        of financing large capital projects. Nippon can fund $14B easily; USS cannot.

        For USS standalone:
        - Calculate financing gap (CapEx beyond FCF capacity)
        - Apply debt financing impact (higher interest expense, higher WACC)
        - Apply equity financing impact (share dilution)
        - NO synergies (USS cannot capture synergies alone)

        For Nippon view:
        - No financing adjustment (Nippon has balance sheet capacity)
        - Use IRP-adjusted WACC (lower cost of capital)
        - ADD synergies if configured (synergies apply ONLY to Nippon valuation)

        If use_verified_wacc is True:
        - Loads USS WACC from wacc-calculations module
        - Loads Nippon WACC from wacc-calculations module
        - Populates wacc_audit_trail in results
        """
        # Step 1: Build Projections (0-40%)
        self._report_progress(0, "Building segment projections...")
        consolidated, segment_dfs = self.build_consolidated()
        self._report_progress(40, "Projections complete")

        # Step 2: Calculate WACCs (40-45%)
        self._report_progress(42, "Calculating WACC...")

        # Build WACC audit trail
        wacc_audit_trail = {
            'source': 'scenario parameters',
            'uss': None,
            'nippon': None,
        }

        # USS WACC: optionally load from module
        uss_wacc = self.scenario.uss_wacc
        if self.scenario.use_verified_wacc and WACC_MODULE_AVAILABLE:
            verified_uss_wacc, uss_audit = get_verified_uss_wacc()
            if verified_uss_wacc is not None:
                uss_wacc = verified_uss_wacc
                wacc_audit_trail['uss'] = uss_audit
                wacc_audit_trail['source'] = 'wacc-calculations module'

        # Nippon WACC: calculate with optional verification
        jpy_wacc, usd_wacc, nippon_audit = self.calculate_irp_wacc()
        if nippon_audit:
            wacc_audit_trail['nippon'] = nippon_audit.get('nippon')
            wacc_audit_trail['source'] = 'wacc-calculations module'

        self._report_progress(45, "WACC calculated")

        # Step 3: Financing Impact (45-55%)
        self._report_progress(47, "Analyzing financing requirements...")
        financing_impact = self.calculate_financing_impact(consolidated)
        self._report_progress(55, "Financing analysis complete")

        # Step 4: USS DCF (55-65%)
        self._report_progress(57, "Running USS valuation...")
        val_uss = self.calculate_dcf(consolidated, uss_wacc, financing_impact)
        self._report_progress(65, "USS valuation complete")

        # Steps 5-6: Synergies (65-80%)
        synergy_schedule = None
        synergy_value = None

        if self.scenario.synergies is not None and self.scenario.synergies.enabled:
            self._report_progress(67, "Building synergy schedule...")
            synergy_schedule = self.build_synergy_schedule(consolidated, segment_dfs)
            self._report_progress(72, "Calculating synergy value...")
            synergy_value = self.calculate_synergy_value(synergy_schedule, usd_wacc)
            self._report_progress(75, "Adjusting for synergies...")

            # Create synergy-adjusted consolidated for Nippon valuation
            # Add synergy EBITDA to consolidated, recalculate FCF
            consolidated_with_synergies = consolidated.copy()
            for idx, row in consolidated_with_synergies.iterrows():
                year = row['Year']
                synergy_row = synergy_schedule[synergy_schedule['Year'] == year]
                if len(synergy_row) > 0:
                    synergy_ebitda = synergy_row['Total_Synergy_EBITDA'].values[0]
                    consolidated_with_synergies.at[idx, 'Total_EBITDA'] += synergy_ebitda
                    # Recalculate downstream metrics
                    new_ebitda = consolidated_with_synergies.at[idx, 'Total_EBITDA']
                    da = consolidated_with_synergies.at[idx, 'DA']
                    new_ebit = new_ebitda - da
                    new_nopat = new_ebit * (1 - 0.169)  # 16.9% cash tax rate
                    new_gross_cf = new_nopat + da
                    capex = consolidated_with_synergies.at[idx, 'Total_CapEx']
                    delta_wc = consolidated_with_synergies.at[idx, 'Delta_WC']
                    new_fcf = new_gross_cf - capex + delta_wc

                    consolidated_with_synergies.at[idx, 'NOPAT'] = new_nopat
                    consolidated_with_synergies.at[idx, 'Gross_CF'] = new_gross_cf
                    consolidated_with_synergies.at[idx, 'FCF'] = new_fcf
                    consolidated_with_synergies.at[idx, 'EBITDA_Margin'] = new_ebitda / row['Revenue'] if row['Revenue'] > 0 else 0

            # Step 7: Nippon DCF with synergies (80-95%)
            self._report_progress(80, "Synergies incorporated")
            self._report_progress(82, "Running Nippon valuation...")
            val_nippon = self.calculate_dcf(consolidated_with_synergies, usd_wacc, None)
            self._report_progress(95, "Nippon valuation complete")
        else:
            # Nippon view without synergies
            self._report_progress(80, "Skipping synergies")
            self._report_progress(82, "Running Nippon valuation...")
            val_nippon = self.calculate_dcf(consolidated, usd_wacc, None)
            self._report_progress(95, "Nippon valuation complete")

        # Step 8: Assembly (95-100%)
        self._report_progress(97, "Assembling results...")

        results = {
            'scenario': self.scenario,
            'consolidated': consolidated,
            'segment_dfs': segment_dfs,
            'jpy_wacc': jpy_wacc,
            'usd_wacc': usd_wacc,
            'uss_wacc': uss_wacc,  # May differ from scenario.uss_wacc if verified
            'val_uss': val_uss,
            'val_nippon': val_nippon,
            'wacc_advantage': uss_wacc - usd_wacc,
            'financing_impact': financing_impact,
            'synergy_schedule': synergy_schedule,
            'synergy_value': synergy_value,
            'wacc_audit_trail': wacc_audit_trail if self.scenario.use_verified_wacc else None,
        }

        self._report_progress(100, "Analysis complete")
        return results


# =============================================================================
# SCENARIO COMPARISON
# =============================================================================

def compare_scenarios(scenario_types: List[ScenarioType] = None,
                      execution_factor: float = 1.0,
                      custom_benchmarks: dict = None,
                      progress_bar=None) -> pd.DataFrame:
    """Run and compare multiple scenarios

    Args:
        scenario_types: List of scenarios to compare (default: all except CUSTOM)
        execution_factor: Execution factor to apply to Nippon Commitments scenario (0.5-1.0)
        custom_benchmarks: Optional custom benchmark prices dict (default: use BENCHMARK_PRICES_2023)
        progress_bar: Optional Streamlit progress bar for tracking
    """

    if scenario_types is None:
        scenario_types = list(ScenarioType)
        scenario_types.remove(ScenarioType.CUSTOM)

    presets = get_scenario_presets()
    results = []

    for i, st in enumerate(scenario_types, 1):
        if st in presets:
            # Update progress bar if provided
            if progress_bar is not None:
                progress_pct = int((i / len(scenario_types)) * 100)
                progress_bar.progress(progress_pct, text=f"Calculating scenario: {st.name} ({i}/{len(scenario_types)})")

            # Apply execution factor only to Nippon Commitments scenario
            ef = execution_factor if st == ScenarioType.NIPPON_COMMITMENTS else 1.0
            model = PriceVolumeModel(presets[st], execution_factor=ef, custom_benchmarks=custom_benchmarks)
            analysis = model.run_full_analysis()

            # Calculate implied EV/EBITDA multiple
            ebitda_2024 = analysis['consolidated'].loc[analysis['consolidated']['Year'] == 2024, 'Total_EBITDA'].values[0]
            implied_ev_ebitda = analysis['val_uss']['ev_blended'] / ebitda_2024 if ebitda_2024 > 0 else 0

            results.append({
                'Scenario': analysis['scenario'].name,
                'USS - No Sale ($/sh)': analysis['val_uss']['share_price'],
                'Value to Nippon ($/sh)': analysis['val_nippon']['share_price'],
                'vs $55 Offer': analysis['val_nippon']['share_price'] - 55,
                'WACC Advantage': analysis['wacc_advantage'] * 100,
                '10Y FCF ($B)': analysis['consolidated']['FCF'].sum() / 1000,
                'Implied EV/EBITDA': implied_ev_ebitda,
                'Avg EBITDA Margin': analysis['consolidated']['EBITDA_Margin'].mean() * 100,
                '2033 Revenue ($B)': analysis['consolidated']['Revenue'].iloc[-1] / 1000
            })

    return pd.DataFrame(results)


def calculate_probability_weighted_valuation(
    scenarios: Dict[ScenarioType, ModelScenario] = None,
    exclude_scenarios: List[ScenarioType] = None,
    custom_benchmarks: dict = None,
    progress_bar=None,
    calibration_mode: Optional[str] = None,
    probability_mode: Optional[str] = None
) -> Dict[str, any]:
    """
    Calculate probability-weighted expected value across scenarios

    Args:
        scenarios: Dict of scenarios to evaluate (default: all presets)
        exclude_scenarios: Scenarios to exclude (default: CUSTOM, WALL_STREET, NIPPON_COMMITMENTS)
        custom_benchmarks: Optional custom benchmark prices dict
        progress_bar: Optional Streamlit progress bar for tracking
        calibration_mode: Optional calibration mode ('fixed', 'bloomberg', 'hybrid')
        probability_mode: Optional probability mode ('fixed', 'bloomberg')

    Returns:
        Dict with weighted metrics and scenario breakdown
    """
    if scenarios is None:
        scenarios = get_scenario_presets(
            calibration_mode=calibration_mode,
            probability_mode=probability_mode
        )

    if exclude_scenarios is None:
        exclude_scenarios = [
            ScenarioType.CUSTOM,
            ScenarioType.WALL_STREET,
            ScenarioType.NIPPON_COMMITMENTS,
            # Exclude FUTURES scenarios (separate probability set for futures-based analysis)
            ScenarioType.FUTURES_DOWNSIDE,
            ScenarioType.FUTURES_BASE_CASE,
            ScenarioType.FUTURES_ABOVE_AVERAGE,
            ScenarioType.FUTURES_OPTIMISTIC,
            ScenarioType.FUTURES_NO_TARIFF,
        ]

    # Filter to scenarios with probability weights
    weighted_scenarios = {
        name: scenario for name, scenario in scenarios.items()
        if name not in exclude_scenarios and scenario.probability_weight > 0
    }

    if not weighted_scenarios:
        raise ValueError("No scenarios with probability weights found")

    # Validate probabilities sum to 1.0
    total_prob = sum(s.probability_weight for s in weighted_scenarios.values())
    if not (0.99 <= total_prob <= 1.01):
        raise ValueError(f"Probabilities must sum to 1.0, got {total_prob:.3f}")

    # Run each scenario
    results = {}
    for i, (scenario_type, scenario) in enumerate(weighted_scenarios.items(), 1):
        if progress_bar is not None:
            progress_pct = int((i / len(weighted_scenarios)) * 100)
            progress_bar.progress(progress_pct, text=f"Calculating scenario: {scenario.name} ({i}/{len(weighted_scenarios)})")

        model = PriceVolumeModel(scenario, custom_benchmarks=custom_benchmarks)
        analysis = model.run_full_analysis()
        results[scenario_type] = {
            'name': scenario.name,
            'uss_value_per_share': analysis['val_uss']['share_price'],
            'nippon_value_per_share': analysis['val_nippon']['share_price'],
            'ten_year_fcf': analysis['consolidated']['FCF'].sum(),
            'terminal_ebitda': analysis['consolidated']['Total_EBITDA'].iloc[-1],
            'avg_ebitda': analysis['consolidated']['Total_EBITDA'].mean(),
            'probability': scenario.probability_weight
        }

    # Calculate weighted averages
    weighted_uss_value = sum(
        r['uss_value_per_share'] * r['probability']
        for r in results.values()
    )
    weighted_nippon_value = sum(
        r['nippon_value_per_share'] * r['probability']
        for r in results.values()
    )
    weighted_fcf = sum(
        r['ten_year_fcf'] * r['probability']
        for r in results.values()
    )
    weighted_avg_ebitda = sum(
        r['avg_ebitda'] * r['probability']
        for r in results.values()
    )

    offer_price = 55.0

    # Calculate premium/discount percentages with protection against division by zero
    if weighted_uss_value > 0.01:
        uss_premium_to_offer = (offer_price / weighted_uss_value - 1) * 100
    else:
        uss_premium_to_offer = float('inf')  # Offer is infinitely better than zero equity

    nippon_discount_to_offer = (weighted_nippon_value / offer_price - 1) * 100  # offer_price is always 55

    return {
        'weighted_uss_value_per_share': weighted_uss_value,
        'weighted_nippon_value_per_share': weighted_nippon_value,
        'weighted_ten_year_fcf': weighted_fcf,
        'weighted_avg_ebitda': weighted_avg_ebitda,
        'scenario_results': results,
        'offer_price': offer_price,
        'uss_premium_to_offer': uss_premium_to_offer,
        'nippon_discount_to_offer': nippon_discount_to_offer,
        'total_probability': total_prob
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("USS / NIPPON STEEL: PRICE x VOLUME DCF MODEL")
    print("=" * 80)

    # Compare all scenarios
    comparison = compare_scenarios()
    print("\nSCENARIO COMPARISON:")
    print("-" * 80)
    print(comparison.to_string(index=False))

    # Detailed base case
    print("\n" + "=" * 80)
    print("BASE CASE DETAIL")
    print("=" * 80)

    base = get_scenario_presets()[ScenarioType.BASE_CASE]
    model = PriceVolumeModel(base)
    analysis = model.run_full_analysis()

    print(f"\nSteel Price Scenario: {base.price_scenario.name}")
    print(f"  - {base.price_scenario.description}")
    print(f"\nVolume Scenario: {base.volume_scenario.name}")
    print(f"  - {base.volume_scenario.description}")

    print("\nSEGMENT FCF CONTRIBUTION:")
    total_fcf = analysis['consolidated']['FCF'].sum()
    for seg_name, df in analysis['segment_dfs'].items():
        fcf = df['FCF'].sum()
        if abs(total_fcf) > 0.01:
            pct_str = f"({fcf/total_fcf*100:.1f}%)"
        else:
            pct_str = "(N/A - total FCF near zero)"
        print(f"  {seg_name}: ${fcf:,.0f}M {pct_str}")

    print(f"\nVALUATION:")
    print(f"  USS Standalone (@ {base.uss_wacc*100:.1f}% WACC): ${analysis['val_uss']['share_price']:.2f}/share")
    print(f"  Nippon View (@ {analysis['usd_wacc']*100:.2f}% IRP WACC): ${analysis['val_nippon']['share_price']:.2f}/share")
    print(f"  Nippon Offer: $55.00/share")
    print(f"  Gap to Offer: ${analysis['val_nippon']['share_price'] - 55:.2f}/share")
