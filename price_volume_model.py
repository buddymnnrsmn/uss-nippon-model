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
- Pre-built scenario presets (Base, Conservative, Wall Street, Management, Nippon Commitments)
- IRP-adjusted WACC for cross-border valuation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import pandas as pd
import numpy as np


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


# Steel price benchmarks ($/ton) - 2023 actuals
BENCHMARK_PRICES_2023 = {
    'hrc_us': 680,      # US HRC Midwest
    'crc_us': 850,      # US CRC
    'coated_us': 950,   # US Coated/Galvanized
    'hrc_eu': 620,      # EU HRC
    'octg': 2800,       # OCTG (Oil Country Tubular Goods)
}


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
    benchmark_type: str  # Which benchmark to reference

    # Cost structure
    ebitda_margin_at_base_price: float  # EBITDA margin at 2023 price level
    margin_sensitivity_to_price: float  # How much margin changes per $100 price change

    # Other segment parameters
    da_pct_of_revenue: float
    maintenance_capex_pct: float
    dso: float
    dih: float
    dpo: float


@dataclass
class SteelPriceScenario:
    """Steel price scenario assumptions"""
    name: str
    description: str

    # Price levels relative to 2023 (1.0 = flat, 1.1 = +10%)
    hrc_us_factor: float
    crc_us_factor: float
    coated_us_factor: float
    hrc_eu_factor: float
    octg_factor: float

    # Annual price growth after initial adjustment
    annual_price_growth: float


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
    """Capital project with segment allocation"""
    name: str
    segment: str
    enabled: bool
    capex_schedule: Dict[int, float]
    ebitda_schedule: Dict[int, float]
    volume_addition: Dict[int, float] = field(default_factory=dict)  # Additional tons


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
            'optimistic (peak cycle)': multiples['high'],
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
    return SteelPriceScenario(
        name="Base Case Prices",
        description="Mid-cycle pricing, modest inflation, no real price gains",
        hrc_us_factor=0.95,  # Slight pullback from 2023 elevated levels
        crc_us_factor=0.95,
        coated_us_factor=0.95,
        hrc_eu_factor=0.92,
        octg_factor=0.95,
        annual_price_growth=0.005  # 0.5% - barely keeps pace with costs
    )


def get_conservative_price_scenario() -> SteelPriceScenario:
    return SteelPriceScenario(
        name="Conservative Prices",
        description="Steel prices decline 15-20% from 2023 due to weak demand",
        hrc_us_factor=0.85,
        crc_us_factor=0.85,
        coated_us_factor=0.85,
        hrc_eu_factor=0.80,
        octg_factor=0.85,
        annual_price_growth=0.01
    )


def get_wall_street_price_scenario() -> SteelPriceScenario:
    return SteelPriceScenario(
        name="Wall Street Consensus",
        description="Analyst consensus - modest price weakness then recovery",
        hrc_us_factor=0.92,
        crc_us_factor=0.92,
        coated_us_factor=0.93,
        hrc_eu_factor=0.90,
        octg_factor=0.95,
        annual_price_growth=0.025
    )


def get_management_price_scenario() -> SteelPriceScenario:
    return SteelPriceScenario(
        name="Management Guidance",
        description="Management optimism - prices recover and grow",
        hrc_us_factor=1.05,
        crc_us_factor=1.05,
        coated_us_factor=1.05,
        hrc_eu_factor=1.0,
        octg_factor=1.10,
        annual_price_growth=0.03
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
        mini_mill_volume_factor=0.97,
        usse_volume_factor=0.92,
        tubular_volume_factor=0.90,
        flat_rolled_growth_adj=-0.01,
        mini_mill_growth_adj=0.01,
        usse_growth_adj=-0.01,
        tubular_growth_adj=0.0
    )


def get_management_price_scenario() -> SteelPriceScenario:
    """Management Dec 2023 projections: HRC $750/ton in 2024, $700/ton thereafter"""
    return SteelPriceScenario(
        name="Management Dec 2023",
        description="HRC $750/ton (2024), $700/ton (2025+) - per Barclays/Goldman fairness opinions",
        hrc_us_factor=0.92,  # $680 base * 0.92 = ~$626 benchmark -> realized ~$750 after premiums
        crc_us_factor=0.92,
        coated_us_factor=0.92,
        hrc_eu_factor=0.90,
        octg_factor=0.95,
        annual_price_growth=0.0  # Flat pricing assumption per management
    )


def get_nippon_price_scenario() -> SteelPriceScenario:
    """Nippon NSA scenario with modest price support from capacity discipline"""
    return SteelPriceScenario(
        name="Nippon Commitments",
        description="NSA investment case - stable pricing with capacity discipline",
        hrc_us_factor=1.0,
        crc_us_factor=1.0,
        coated_us_factor=1.0,
        hrc_eu_factor=0.95,
        octg_factor=1.0,
        annual_price_growth=0.015  # Modest 1.5% real price growth from capacity discipline
    )


def get_severe_downturn_price_scenario() -> SteelPriceScenario:
    """Severe downturn: Historical recession levels (2009, 2015, 2020)"""
    return SteelPriceScenario(
        name="Severe Downturn Pricing",
        description="Historical recession levels (2009, 2015, 2020)",
        hrc_us_factor=0.68,      # -32% from benchmark
        crc_us_factor=0.68,
        coated_us_factor=0.70,
        hrc_eu_factor=0.65,      # EU hit harder
        octg_factor=0.50,        # Oil crash correlation
        annual_price_growth=-0.02  # -2% deflation
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
    """Mid-cycle pricing: Historical median steel prices"""
    return SteelPriceScenario(
        name="Mid-Cycle Pricing",
        description="Historical median steel prices",
        hrc_us_factor=0.88,      # Closer to historical average
        crc_us_factor=0.88,
        coated_us_factor=0.90,
        hrc_eu_factor=0.85,
        octg_factor=0.80,
        annual_price_growth=0.01  # 1% inflation
    )


def get_true_base_case_volume_scenario() -> VolumeScenario:
    """Mid-cycle volumes: Historical average utilization"""
    return VolumeScenario(
        name="Mid-Cycle Volumes",
        description="Historical average utilization",
        flat_rolled_volume_factor=0.92,  # Modest decline from 2023
        mini_mill_volume_factor=0.98,
        usse_volume_factor=0.90,
        tubular_volume_factor=0.95,
        flat_rolled_growth_adj=-0.005,
        mini_mill_growth_adj=0.005,
        usse_growth_adj=-0.005,
        tubular_growth_adj=0.00
    )


def get_scenario_presets() -> Dict[ScenarioType, ModelScenario]:
    """Return all pre-built scenario configurations

    Scenarios calibrated to historical data (1990-2023):
    - Severe Downturn: 0-25th percentile (historical frequency: 24%)
    - Downside: 25-40th percentile (historical frequency: 30%)
    - Base Case: 50th percentile - median (historical frequency: 30%)
    - Above Average: 75-90th percentile (historical frequency: 10%)
    - Optimistic: 90th+ percentile (historical frequency: 5%)
    - Wall Street: Analyst consensus (reference only, no probability weight)
    - Nippon Commitments: $14B NSA investment program (reference only)
    """

    return {
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
                flat_rolled_volume_factor=0.98,
                mini_mill_volume_factor=1.0,
                usse_volume_factor=0.98,
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
            price_scenario=get_management_price_scenario(),
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
            name="Optimistic (Peak Cycle)",
            scenario_type=ScenarioType.OPTIMISTIC,
            description="2021-2022 conditions: peak pricing and margins",
            price_scenario=get_management_price_scenario(),
            volume_scenario=VolumeScenario(
                name="Peak Cycle Volumes",
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
            name="Optimistic (Peak Cycle)",
            scenario_type=ScenarioType.OPTIMISTIC,
            description="2021-2022 conditions: peak pricing and margins",
            price_scenario=get_management_price_scenario(),
            volume_scenario=VolumeScenario(
                name="Peak Cycle Volumes",
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
                description="Stable mid-cycle pricing with capacity discipline",
                hrc_us_factor=0.95,
                crc_us_factor=0.95,
                coated_us_factor=0.95,
                hrc_eu_factor=0.92,
                octg_factor=0.95,
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
    }


# =============================================================================
# SEGMENT CONFIGURATIONS
# =============================================================================

def get_segment_configs() -> Dict[Segment, SegmentVolumePrice]:
    """Return base segment configurations from Excel data

    Premium calibrations based on 2023 actual realized prices vs benchmarks:
    - Flat-Rolled: $1,030 realized vs $680 HRC = 51% premium (product mix: CRC, coated)
    - Mini Mill: $875 realized vs $680 HRC = 29% premium
    - USSE: $873 realized vs $620 EU HRC = 41% premium
    - Tubular: $3,137 realized vs $2,800 OCTG = 12% premium
    """

    return {
        Segment.FLAT_ROLLED: SegmentVolumePrice(
            name="Flat-Rolled",
            base_shipments_2023=8706,  # 000 tons
            volume_growth_rate=-0.005,  # Slight decline as mini mills gain share
            capacity_utilization_2023=0.712,
            max_capacity_utilization=0.85,
            base_price_2023=1030,  # $/ton realized
            price_growth_rate=0.02,
            price_premium_to_benchmark=0.515,  # Calibrated: $1030/$680 - 1
            benchmark_type='hrc_us',
            ebitda_margin_at_base_price=0.12,  # Mgmt: 16% blended margin at mid-cycle
            margin_sensitivity_to_price=0.04,  # 4% margin change per $100 price
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
            price_premium_to_benchmark=0.287,  # Calibrated: $875/$680 - 1
            benchmark_type='hrc_us',
            ebitda_margin_at_base_price=0.20,  # Mini mills are highly profitable
            margin_sensitivity_to_price=0.05,  # 5% margin change per $100 price
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
            price_premium_to_benchmark=0.408,  # Calibrated: $873/$620 - 1
            benchmark_type='hrc_eu',
            ebitda_margin_at_base_price=0.14,  # European ops have decent margins
            margin_sensitivity_to_price=0.04,  # 4% margin change per $100 price
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
            price_premium_to_benchmark=0.120,  # Calibrated: $3137/$2800 - 1
            benchmark_type='octg',
            ebitda_margin_at_base_price=0.15,  # OCTG margins are strong
            margin_sensitivity_to_price=0.02,  # 2% margin change per $100 price
            da_pct_of_revenue=0.060,
            maintenance_capex_pct=0.040,
            dso=35, dih=60, dpo=55
        ),
    }


def get_capital_projects() -> Dict[str, CapitalProject]:
    """Return capital project configurations"""

    return {
        'BR2 Mini Mill': CapitalProject(
            name='BR2 Mini Mill',
            segment='Mini Mill',
            enabled=True,
            capex_schedule={2024: 1000, 2025: 133, 2026: 133, 2027: 133, 2028: 133,
                           2029: 133, 2030: 133, 2031: 133, 2032: 133, 2033: 133},
            ebitda_schedule={2024: 0, 2025: 100, 2026: 300, 2027: 450, 2028: 560,
                            2029: 560, 2030: 560, 2031: 560, 2032: 560, 2033: 560},
            volume_addition={2025: 200, 2026: 500, 2027: 750, 2028: 1000,
                            2029: 1000, 2030: 1000, 2031: 1000, 2032: 1000, 2033: 1000}
        ),
        'Gary Works BF': CapitalProject(
            name='Gary Works BF',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2024: 400, 2025: 1200, 2026: 1001, 2027: 499},
            ebitda_schedule={2027: 100, 2028: 300, 2029: 402, 2030: 402,
                            2031: 402, 2032: 402, 2033: 402}
        ),
        'Mon Valley HSM': CapitalProject(
            name='Mon Valley HSM',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2024: 200, 2025: 500, 2026: 250, 2027: 50},
            ebitda_schedule={2026: 50, 2027: 100, 2028: 130, 2029: 130,
                            2030: 130, 2031: 130, 2032: 130, 2033: 130}
        ),
        'Greenfield Mini Mill': CapitalProject(
            name='Greenfield Mini Mill',
            segment='Mini Mill',
            enabled=False,
            capex_schedule={2025: 100, 2026: 400, 2027: 400, 2028: 100},
            ebitda_schedule={2027: 50, 2028: 150, 2029: 274, 2030: 274,
                            2031: 274, 2032: 274, 2033: 274},
            volume_addition={2027: 100, 2028: 300, 2029: 500, 2030: 500,
                            2031: 500, 2032: 500, 2033: 500}
        ),
        'Mining Investment': CapitalProject(
            name='Mining Investment',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2024: 150, 2025: 300, 2026: 250, 2027: 100},
            ebitda_schedule={2025: 20, 2026: 50, 2027: 80, 2028: 80,
                            2029: 80, 2030: 80, 2031: 80, 2032: 80, 2033: 80}
        ),
        'Fairfield Works': CapitalProject(
            name='Fairfield Works',
            segment='Flat-Rolled',
            enabled=False,
            capex_schedule={2024: 50, 2025: 200, 2026: 200, 2027: 50},
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

    def __init__(self, scenario: ModelScenario, execution_factor: float = 1.0, custom_benchmarks: dict = None):
        self.scenario = scenario
        self.execution_factor = execution_factor
        self.custom_benchmarks = custom_benchmarks or BENCHMARK_PRICES_2023
        self.years = list(range(2024, 2034))
        self.segments = get_segment_configs()
        self.projects = get_capital_projects()

        # Enable projects based on scenario
        for proj_name in scenario.include_projects:
            if proj_name in self.projects:
                self.projects[proj_name].enabled = True

    def get_benchmark_price(self, benchmark_type: str, year: int) -> float:
        """Calculate benchmark price for a given year"""
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

        # Apply initial factor then annual growth
        price = base_price * initial_factor * ((1 + price_scenario.annual_price_growth) ** years_from_base)

        return price

    def calculate_segment_price(self, segment: Segment, year: int) -> float:
        """Calculate realized price for a segment in a given year"""
        seg = self.segments[segment]
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
        return max(0.02, min(0.30, margin))

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

            # Add project EBITDA (apply execution factor to non-BR2 projects)
            project_ebitda = 0
            project_capex = 0
            for proj in self.projects.values():
                if proj.enabled and proj.segment == seg.name:
                    ebitda_add = proj.ebitda_schedule.get(year, 0)
                    # BR2 is committed/in-progress, don't haircut it
                    if proj.name != 'BR2 Mini Mill':
                        ebitda_add *= self.execution_factor
                    project_ebitda += ebitda_add
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
        """Build consolidated projection from all segments"""
        segment_dfs = {}
        for segment in Segment:
            segment_dfs[segment.value] = self.build_segment_projection(segment)

        # Consolidate
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

    def calculate_irp_wacc(self) -> Tuple[float, float]:
        """Calculate JPY WACC and IRP-adjusted USD WACC

        Now properly linked to JGB rate:
        - Cost of Equity = JGB + Equity Risk Premium
        - Cost of Debt = JGB + Credit Spread

        If override_irp is True, uses manual_nippon_usd_wacc instead of IRP formula.
        """
        s = self.scenario

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

        # USD WACC: Use manual override if specified, otherwise apply IRP
        if s.override_irp and s.manual_nippon_usd_wacc is not None:
            usd_wacc = s.manual_nippon_usd_wacc
        else:
            # IRP conversion to USD
            usd_wacc = (1 + jpy_wacc) * (1 + s.us_10yr) / (1 + s.japan_10yr) - 1

        return jpy_wacc, usd_wacc

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
        """Run complete analysis and return all results

        Key insight: USS standalone ("USS - No Sale") valuation must account for the cost
        of financing large capital projects. Nippon can fund $14B easily; USS cannot.

        For USS standalone:
        - Calculate financing gap (CapEx beyond FCF capacity)
        - Apply debt financing impact (higher interest expense, higher WACC)
        - Apply equity financing impact (share dilution)

        For Nippon view:
        - No financing adjustment (Nippon has balance sheet capacity)
        - Use IRP-adjusted WACC (lower cost of capital)
        """
        # Build projections
        consolidated, segment_dfs = self.build_consolidated()

        # Calculate WACCs
        jpy_wacc, usd_wacc = self.calculate_irp_wacc()

        # Calculate financing impact for USS standalone
        financing_impact = self.calculate_financing_impact(consolidated)

        # Run valuations
        # USS standalone: apply financing impact (debt + equity dilution)
        val_uss = self.calculate_dcf(consolidated, self.scenario.uss_wacc, financing_impact)

        # Nippon view: no financing impact (they can fund it), use lower IRP-adjusted WACC
        val_nippon = self.calculate_dcf(consolidated, usd_wacc, None)

        return {
            'scenario': self.scenario,
            'consolidated': consolidated,
            'segment_dfs': segment_dfs,
            'jpy_wacc': jpy_wacc,
            'usd_wacc': usd_wacc,
            'val_uss': val_uss,
            'val_nippon': val_nippon,
            'wacc_advantage': self.scenario.uss_wacc - usd_wacc,
            'financing_impact': financing_impact
        }


# =============================================================================
# SCENARIO COMPARISON
# =============================================================================

def compare_scenarios(scenario_types: List[ScenarioType] = None,
                      execution_factor: float = 1.0,
                      custom_benchmarks: dict = None) -> pd.DataFrame:
    """Run and compare multiple scenarios

    Args:
        scenario_types: List of scenarios to compare (default: all except CUSTOM)
        execution_factor: Execution factor to apply to Nippon Commitments scenario (0.5-1.0)
        custom_benchmarks: Optional custom benchmark prices dict (default: use BENCHMARK_PRICES_2023)
    """

    if scenario_types is None:
        scenario_types = list(ScenarioType)
        scenario_types.remove(ScenarioType.CUSTOM)

    presets = get_scenario_presets()
    results = []

    for st in scenario_types:
        if st in presets:
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
    custom_benchmarks: dict = None
) -> Dict[str, any]:
    """
    Calculate probability-weighted expected value across scenarios

    Args:
        scenarios: Dict of scenarios to evaluate (default: all presets)
        exclude_scenarios: Scenarios to exclude (default: CUSTOM, WALL_STREET, NIPPON_COMMITMENTS)
        custom_benchmarks: Optional custom benchmark prices dict

    Returns:
        Dict with weighted metrics and scenario breakdown
    """
    if scenarios is None:
        scenarios = get_scenario_presets()

    if exclude_scenarios is None:
        exclude_scenarios = [
            ScenarioType.CUSTOM,
            ScenarioType.WALL_STREET,
            ScenarioType.NIPPON_COMMITMENTS
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
    for scenario_type, scenario in weighted_scenarios.items():
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
