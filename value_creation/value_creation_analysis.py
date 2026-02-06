#!/usr/bin/env python3
"""
USS-Nippon Steel: Value Creation Analysis
==========================================

Core module for analyzing value creation from the USS-Nippon merger.
Builds on existing synergy infrastructure in price_volume_model.py.

Key Components:
- Multi-year value bridge from deal close through Year 10
- Synergy NPV calculations with confidence-weighted estimates
- Value creation waterfall analysis

Reference Precedent Transactions:
- ArcelorMittal/Mittal Steel (2006): $1.0B synergies on $34B deal
- CLF/AK Steel (2020): $120M synergies on $1.1B deal
- Nucor/Gallatin (2014): Achieved $200M+ synergies
- JSW Steel/Bhushan Steel (2018): $400M+ synergies

Author: RAMBAS Team
Date: January 2025
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Add parent directory for model imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from price_volume_model import (
    PriceVolumeModel,
    ScenarioType,
    get_scenario_presets,
    SynergyAssumptions,
    OperatingSynergies,
    TechnologyTransfer,
    RevenueSynergies,
    IntegrationCosts,
    SynergyRampSchedule,
)


# =============================================================================
# CONSTANTS - DEAL PARAMETERS
# =============================================================================

# Deal terms
DEAL_PRICE_PER_SHARE = 55.00  # Nippon's offer
SHARES_OUTSTANDING = 271.0  # Million shares (diluted)
DEAL_EQUITY_VALUE = DEAL_PRICE_PER_SHARE * SHARES_OUTSTANDING  # ~$14.9B

# USS Net Debt at close (estimated)
USS_NET_DEBT = 1_200  # $M
DEAL_ENTERPRISE_VALUE = DEAL_EQUITY_VALUE + USS_NET_DEBT  # ~$16.1B

# Nippon's total capital deployment
NSA_CAPEX_COMMITMENT = 14_000  # $M over multi-year period
TOTAL_CAPITAL_DEPLOYMENT = DEAL_EQUITY_VALUE + NSA_CAPEX_COMMITMENT  # ~$29B

# Breakup fee
BREAKUP_FEE = 565  # $M

# Valuation parameters
USS_STANDALONE_WACC = 0.109  # 10.9%
NIPPON_COMBINED_WACC = 0.075  # 7.5% (lower cost of capital)
TERMINAL_GROWTH = 0.02  # 2%

# Synergy timing
FULL_SYNERGY_RUN_RATE_YEAR = 5  # Years to achieve full run-rate


# =============================================================================
# SYNERGY SOURCES - RESEARCH-BASED ESTIMATES
# =============================================================================

@dataclass
class SynergySource:
    """Individual synergy source with value drivers and confidence levels."""
    name: str
    category: str  # 'cost', 'technology', 'revenue', 'capital', 'strategic'
    run_rate_ebitda: float  # $M annual at full run-rate
    run_rate_low: float  # $M low estimate
    run_rate_high: float  # $M high estimate
    confidence: float  # 0.0-1.0
    ramp_years: int  # Years to full realization
    description: str
    value_drivers: List[str] = field(default_factory=list)
    precedent_reference: str = ""


def build_value_creation_sources() -> List[SynergySource]:
    """
    Build comprehensive list of synergy sources based on research.

    Methodology:
    - Cost synergies: 1.5-2.5% of combined revenue (industry standard)
    - Technology transfer: Based on Nippon's historical improvements
    - Revenue synergies: Conservative, harder to achieve
    - Capital efficiency: WACC differential impact on valuation

    Returns:
        List of SynergySource objects with detailed assumptions
    """
    sources = []

    # =========================================================================
    # COST SYNERGIES ($200-300M run-rate)
    # =========================================================================

    # Procurement - largest single synergy category
    sources.append(SynergySource(
        name="Procurement Scale",
        category="cost",
        run_rate_ebitda=120.0,
        run_rate_low=90.0,
        run_rate_high=150.0,
        confidence=0.80,
        ramp_years=3,
        description="Volume discounts on iron ore, coking coal, alloys, energy",
        value_drivers=[
            "Combined steel production ~75 Mt/year (2nd globally)",
            "Iron ore: 3-5% savings on ~$4B combined spend",
            "Coking coal: Similar scale benefits",
            "Alloys/electrodes: Supplier consolidation",
        ],
        precedent_reference="ArcelorMittal achieved $1.0B+ synergies, ~40% from procurement"
    ))

    # Logistics optimization
    sources.append(SynergySource(
        name="Logistics Optimization",
        category="cost",
        run_rate_ebitda=50.0,
        run_rate_low=35.0,
        run_rate_high=70.0,
        confidence=0.75,
        ramp_years=4,
        description="Optimized shipping routes, shared fleet, warehouse consolidation",
        value_drivers=[
            "Nippon's shipping expertise (NYK, MOL relationships)",
            "Cross-Pacific freight optimization",
            "Shared slab/coil inventory management",
            "Reduced demurrage and handling costs",
        ],
        precedent_reference="CLF/AK Steel achieved ~$30M logistics synergies"
    ))

    # Overhead consolidation
    sources.append(SynergySource(
        name="Overhead Consolidation",
        category="cost",
        run_rate_ebitda=80.0,
        run_rate_low=60.0,
        run_rate_high=100.0,
        confidence=0.85,
        ramp_years=3,
        description="Corporate functions, IT systems, shared services",
        value_drivers=[
            "Eliminate duplicate corporate functions",
            "IT system consolidation (ERP, planning)",
            "Shared R&D infrastructure",
            "Insurance and professional services",
        ],
        precedent_reference="Typical 1-2% of acquired SG&A"
    ))

    # =========================================================================
    # TECHNOLOGY TRANSFER ($150-250M run-rate)
    # =========================================================================

    # Yield improvement
    sources.append(SynergySource(
        name="Yield Improvement",
        category="technology",
        run_rate_ebitda=100.0,
        run_rate_low=70.0,
        run_rate_high=140.0,
        confidence=0.70,
        ramp_years=5,
        description="Nippon's advanced process control and quality systems",
        value_drivers=[
            "USS current yield: ~92-94% (integrated), ~96% (mini-mill)",
            "Nippon best practice: 97-98%",
            "2-3% yield gain = ~$100M EBITDA (on ~$15B revenue)",
            "Key tech: AI-based process control, predictive maintenance",
        ],
        precedent_reference="Nippon improved yield at NSSMC Thailand by 2.5pp"
    ))

    # Quality premiums
    sources.append(SynergySource(
        name="Quality Premiums",
        category="technology",
        run_rate_ebitda=75.0,
        run_rate_low=50.0,
        run_rate_high=100.0,
        confidence=0.65,
        ramp_years=6,
        description="Access to Nippon's advanced grades (AHSS, coated)",
        value_drivers=[
            "Automotive AHSS: $100-200/ton premium vs standard",
            "High-end coated products for EV applications",
            "Energy products for green transition",
            "USS flat-rolled positioned for upgrade",
        ],
        precedent_reference="Nippon's AHSS products command 15-20% premiums"
    ))

    # Conversion cost reduction
    sources.append(SynergySource(
        name="Conversion Cost Reduction",
        category="technology",
        run_rate_ebitda=50.0,
        run_rate_low=30.0,
        run_rate_high=70.0,
        confidence=0.65,
        ramp_years=5,
        description="Energy efficiency, labor productivity improvements",
        value_drivers=[
            "Nippon's best-in-class energy intensity",
            "Advanced automation and robotics",
            "Predictive maintenance reducing downtime",
            "3-5% conversion cost reduction achievable",
        ],
        precedent_reference="Japanese steel tech typically saves $10-20/ton"
    ))

    # =========================================================================
    # REVENUE SYNERGIES ($50-100M run-rate)
    # =========================================================================

    # Cross-selling
    sources.append(SynergySource(
        name="Cross-Selling",
        category="revenue",
        run_rate_ebitda=40.0,
        run_rate_low=25.0,
        run_rate_high=60.0,
        confidence=0.55,
        ramp_years=5,
        description="Nippon products through USS channels, vice versa",
        value_drivers=[
            "USS automotive relationships for Nippon specialty grades",
            "Nippon Asian relationships for USS products",
            "Joint product development with OEMs",
            "Energy sector cross-referrals",
        ],
        precedent_reference="Revenue synergies typically 20-30% of cost synergies"
    ))

    # Product mix improvement
    sources.append(SynergySource(
        name="Product Mix Improvement",
        category="revenue",
        run_rate_ebitda=35.0,
        run_rate_low=20.0,
        run_rate_high=50.0,
        confidence=0.60,
        ramp_years=6,
        description="Shift to higher-margin specialty products",
        value_drivers=[
            "Move 5-10% of volume to higher-value products",
            "Automotive: AHSS over standard grades",
            "Energy: Premium OCTG products",
            "Electrical steel for EV motors",
        ],
        precedent_reference="Nucor product mix shift added $150M+ EBITDA"
    ))

    # =========================================================================
    # CAPITAL EFFICIENCY (Valuation multiplier, not direct EBITDA)
    # =========================================================================

    sources.append(SynergySource(
        name="WACC Advantage",
        category="capital",
        run_rate_ebitda=0.0,  # Not direct EBITDA, affects valuation multiple
        run_rate_low=0.0,
        run_rate_high=0.0,
        confidence=0.90,
        ramp_years=0,  # Immediate
        description="3.4pp lower discount rate (7.5% vs 10.9%)",
        value_drivers=[
            "USS standalone WACC: 10.9%",
            "Nippon combined WACC: 7.5%",
            "3.4pp spread = ~35% higher present value",
            "Implicit multiple expansion from cost of capital",
        ],
        precedent_reference="Japanese steel companies trade at 0.7-0.8x book vs US 0.5-0.6x"
    ))

    sources.append(SynergySource(
        name="Balance Sheet Strength",
        category="capital",
        run_rate_ebitda=0.0,  # Enables capex, not direct EBITDA
        run_rate_low=0.0,
        run_rate_high=0.0,
        confidence=0.90,
        ramp_years=0,
        description="Nippon's investment-grade balance sheet backs USS capex",
        value_drivers=[
            "Nippon debt/EBITDA: 1.84x (pre-deal)",
            "Combined leverage: ~2.5x (still IG)",
            "Enables $14B capex program PE cannot fund",
            "Maintains access to low-cost Japanese debt markets",
        ],
        precedent_reference="Nippon A-/A3 credit rating maintained"
    ))

    # =========================================================================
    # STRATEGIC VALUE (Long-term, hard to quantify)
    # =========================================================================

    sources.append(SynergySource(
        name="Capacity Discipline",
        category="strategic",
        run_rate_ebitda=50.0,
        run_rate_low=25.0,
        run_rate_high=100.0,
        confidence=0.50,
        ramp_years=3,
        description="Coordinated production reduces industry overcapacity",
        value_drivers=[
            "Combined 75 Mt = 5% global capacity",
            "Rational capacity decisions vs fragmented players",
            "Counter Chinese overcapacity",
            "Market-wide pricing support",
        ],
        precedent_reference="ArcelorMittal consolidation supported prices 2006-2008"
    ))

    sources.append(SynergySource(
        name="Green Steel Leadership",
        category="strategic",
        run_rate_ebitda=30.0,
        run_rate_low=0.0,
        run_rate_high=75.0,
        confidence=0.45,
        ramp_years=8,
        description="Combined R&D for hydrogen-based steelmaking",
        value_drivers=[
            "Nippon leading COURSE50 hydrogen project",
            "Combined R&D budget >$500M annually",
            "First-mover in green steel premiums",
            "ESG-driven customer preferences",
        ],
        precedent_reference="Green steel premiums of $50-100/ton emerging"
    ))

    sources.append(SynergySource(
        name="Market Access",
        category="strategic",
        run_rate_ebitda=25.0,
        run_rate_low=10.0,
        run_rate_high=50.0,
        confidence=0.55,
        ramp_years=5,
        description="Nippon's Asian relationships + USS's Americas presence",
        value_drivers=[
            "Serve multinational OEMs globally",
            "Automotive: Toyota, Honda as anchor customers",
            "Trade barrier optimization",
            "Supply chain resilience for customers",
        ],
        precedent_reference="ArcelorMittal global footprint value"
    ))

    return sources


@dataclass
class ValueBridgeResult:
    """Result of multi-year value bridge calculation."""
    year: int
    standalone_value: float  # USS standalone DCF value
    integration_costs: float  # Cumulative integration costs
    operating_synergies: float  # Cumulative cost synergies
    technology_synergies: float  # Cumulative tech transfer value
    revenue_synergies: float  # Cumulative revenue synergies
    capex_benefits: float  # Value from $14B capex program
    total_value: float  # Sum of all components
    value_per_share: float  # Total value / shares outstanding


def build_multi_year_value_bridge(
    years: List[int] = None,
    standalone_value_per_share: float = 50.14,
    nippon_wacc: float = 0.075,
    uss_wacc: float = 0.109,
) -> List[ValueBridgeResult]:
    """
    Build year-by-year value bridge from deal close through Year 10.

    Shows how value evolves as synergies ramp up and integration costs end.

    Args:
        years: List of years (0 = deal close)
        standalone_value_per_share: USS standalone DCF value
        nippon_wacc: Nippon's cost of capital
        uss_wacc: USS standalone cost of capital

    Returns:
        List of ValueBridgeResult for each year
    """
    if years is None:
        years = [0, 1, 2, 3, 4, 5, 7, 10]

    # Get synergy sources
    sources = build_value_creation_sources()

    # Categorize synergies by type
    cost_synergies = [s for s in sources if s.category == 'cost']
    tech_synergies = [s for s in sources if s.category == 'technology']
    rev_synergies = [s for s in sources if s.category == 'revenue']

    # Total run-rate EBITDA by category (probability-weighted)
    cost_run_rate = sum(s.run_rate_ebitda * s.confidence for s in cost_synergies)
    tech_run_rate = sum(s.run_rate_ebitda * s.confidence for s in tech_synergies)
    rev_run_rate = sum(s.run_rate_ebitda * s.confidence for s in rev_synergies)

    # Integration costs (front-loaded)
    total_integration_cost = 1_500  # $M total over 3 years
    integration_schedule = {0: 0.5, 1: 0.35, 2: 0.15}  # 50/35/15 split

    # Capex value ramp ($14B over 10 years, value accrues over time)
    # Assume each $1B capex creates $100M EBITDA run-rate at 10% ROIC
    capex_annual = 1_400  # $M average
    capex_roic = 0.10  # 10% return on invested capital

    # Synergy ramp schedule (% of run-rate achieved)
    def synergy_ramp(year: int, ramp_years: int) -> float:
        if year >= ramp_years:
            return 1.0
        return year / ramp_years

    # Build value bridge
    results = []
    cumulative_capex = 0
    cumulative_integration = 0

    for year in years:
        # Integration costs (one-time)
        year_integration = total_integration_cost * integration_schedule.get(year, 0.0)
        cumulative_integration += year_integration

        # Synergy realization by category
        cost_realized = sum(
            s.run_rate_ebitda * s.confidence * synergy_ramp(year, s.ramp_years)
            for s in cost_synergies
        )
        tech_realized = sum(
            s.run_rate_ebitda * s.confidence * synergy_ramp(year, s.ramp_years)
            for s in tech_synergies
        )
        rev_realized = sum(
            s.run_rate_ebitda * s.confidence * synergy_ramp(year, s.ramp_years)
            for s in rev_synergies
        )

        # Convert EBITDA synergies to equity value
        # Use perpetuity method: Value = EBITDA / (WACC - g)
        synergy_multiple = 1 / (nippon_wacc - TERMINAL_GROWTH)  # ~18x at 7.5% WACC

        cost_value = cost_realized * synergy_multiple / SHARES_OUTSTANDING
        tech_value = tech_realized * synergy_multiple / SHARES_OUTSTANDING
        rev_value = rev_realized * synergy_multiple / SHARES_OUTSTANDING

        # Capex benefits (value of invested capital at ROIC)
        if year > 0:
            cumulative_capex += capex_annual
        capex_ebitda = cumulative_capex * capex_roic  # EBITDA from capex program
        capex_value = capex_ebitda * synergy_multiple / SHARES_OUTSTANDING

        # Integration cost impact on value (one-time, not perpetuity)
        integration_value_impact = cumulative_integration / SHARES_OUTSTANDING

        # Total value per share
        total_value = (
            standalone_value_per_share
            - integration_value_impact
            + cost_value
            + tech_value
            + rev_value
            + capex_value
        )

        results.append(ValueBridgeResult(
            year=year,
            standalone_value=standalone_value_per_share,
            integration_costs=-integration_value_impact,
            operating_synergies=cost_value,
            technology_synergies=tech_value,
            revenue_synergies=rev_value,
            capex_benefits=capex_value,
            total_value=total_value,
            value_per_share=total_value,
        ))

    return results


def calculate_synergy_npv(
    discount_rate: float = 0.075,
    projection_years: int = 10,
) -> Dict[str, float]:
    """
    Calculate NPV of all synergy streams.

    Args:
        discount_rate: Discount rate for NPV calculation
        projection_years: Number of years to project

    Returns:
        Dict with NPV by synergy category and total
    """
    sources = build_value_creation_sources()

    # Categorize
    cost_synergies = [s for s in sources if s.category == 'cost']
    tech_synergies = [s for s in sources if s.category == 'technology']
    rev_synergies = [s for s in sources if s.category == 'revenue']
    strategic_synergies = [s for s in sources if s.category == 'strategic']

    def synergy_ramp(year: int, ramp_years: int) -> float:
        if year >= ramp_years:
            return 1.0
        return year / ramp_years

    def npv_of_synergies(synergies: List[SynergySource]) -> float:
        """Calculate NPV of synergy stream."""
        total_npv = 0
        for s in synergies:
            for year in range(1, projection_years + 1):
                annual_ebitda = s.run_rate_ebitda * s.confidence * synergy_ramp(year, s.ramp_years)
                pv = annual_ebitda / ((1 + discount_rate) ** year)
                total_npv += pv
            # Terminal value at year 10
            terminal_ebitda = s.run_rate_ebitda * s.confidence
            terminal_value = terminal_ebitda / (discount_rate - TERMINAL_GROWTH)
            terminal_pv = terminal_value / ((1 + discount_rate) ** projection_years)
            total_npv += terminal_pv
        return total_npv

    # Integration costs NPV
    integration_schedule = {1: 750, 2: 525, 3: 225}  # $M per year
    integration_npv = sum(
        cost / ((1 + discount_rate) ** year)
        for year, cost in integration_schedule.items()
    )

    results = {
        'cost_synergies_npv': npv_of_synergies(cost_synergies),
        'technology_synergies_npv': npv_of_synergies(tech_synergies),
        'revenue_synergies_npv': npv_of_synergies(rev_synergies),
        'strategic_synergies_npv': npv_of_synergies(strategic_synergies),
        'integration_costs_npv': -integration_npv,
    }

    results['total_synergy_npv'] = (
        results['cost_synergies_npv'] +
        results['technology_synergies_npv'] +
        results['revenue_synergies_npv'] +
        results['strategic_synergies_npv'] +
        results['integration_costs_npv']
    )

    return results


# =============================================================================
# VALUE CREATION ANALYSIS CLASS
# =============================================================================

class ValueCreationAnalysis:
    """
    Comprehensive value creation analysis for USS-Nippon merger.

    Integrates with existing PriceVolumeModel synergy infrastructure
    and adds forward-looking value creation metrics.
    """

    def __init__(self, scenario_type: ScenarioType = ScenarioType.BASE_CASE):
        """
        Initialize value creation analysis.

        Args:
            scenario_type: Base operating scenario for USS projections
        """
        self.scenario_type = scenario_type

        # Get operating projections from DCF model
        presets = get_scenario_presets()
        self.scenario = presets[scenario_type]
        self.model = PriceVolumeModel(self.scenario)
        self.analysis = self.model.run_full_analysis()

        # Extract key values
        self.uss_standalone_value = self.analysis['val_uss']['share_price']
        self.nippon_value = self.analysis['val_nippon']['share_price']

        # Build synergy sources
        self.synergy_sources = build_value_creation_sources()

    def get_value_bridge_df(self) -> pd.DataFrame:
        """
        Get value bridge as a DataFrame.

        Returns:
            DataFrame with year-by-year value components
        """
        bridge = build_multi_year_value_bridge(
            standalone_value_per_share=self.uss_standalone_value
        )

        data = []
        for result in bridge:
            data.append({
                'Year': result.year,
                'Standalone': result.standalone_value,
                'Integration_Costs': result.integration_costs,
                'Operating_Synergies': result.operating_synergies,
                'Technology_Synergies': result.technology_synergies,
                'Revenue_Synergies': result.revenue_synergies,
                'CapEx_Benefits': result.capex_benefits,
                'Total_Value': result.total_value,
            })

        return pd.DataFrame(data)

    def get_synergy_summary(self) -> pd.DataFrame:
        """
        Get summary of all synergy sources.

        Returns:
            DataFrame with synergy details
        """
        data = []
        for s in self.synergy_sources:
            data.append({
                'Name': s.name,
                'Category': s.category.title(),
                'Run_Rate_EBITDA_Low': s.run_rate_low,
                'Run_Rate_EBITDA_Mid': s.run_rate_ebitda,
                'Run_Rate_EBITDA_High': s.run_rate_high,
                'Confidence': f"{s.confidence:.0%}",
                'Ramp_Years': s.ramp_years,
                'Weighted_Run_Rate': s.run_rate_ebitda * s.confidence,
            })

        return pd.DataFrame(data)

    def get_synergy_npv(self) -> Dict[str, float]:
        """Get NPV of synergy streams."""
        return calculate_synergy_npv()

    def get_total_value_creation(self) -> Dict[str, float]:
        """
        Calculate total value creation from the deal.

        Returns:
            Dict with value creation metrics
        """
        npv = self.get_synergy_npv()

        # Premium paid
        premium_per_share = DEAL_PRICE_PER_SHARE - self.uss_standalone_value
        premium_total = premium_per_share * SHARES_OUTSTANDING

        # WACC benefit (value from lower discount rate)
        # DCF at 7.5% vs 10.9% creates significant value
        wacc_benefit = self.nippon_value - self.uss_standalone_value
        wacc_benefit_total = wacc_benefit * SHARES_OUTSTANDING

        return {
            'premium_per_share': premium_per_share,
            'premium_total_M': premium_total,
            'synergy_npv_M': npv['total_synergy_npv'],
            'wacc_benefit_per_share': wacc_benefit,
            'wacc_benefit_total_M': wacc_benefit_total,
            'total_value_created_M': npv['total_synergy_npv'] + wacc_benefit_total,
            'value_created_per_share': (npv['total_synergy_npv'] + wacc_benefit_total) / SHARES_OUTSTANDING,
        }

    def generate_summary_report(self) -> str:
        """
        Generate executive summary of value creation analysis.

        Returns:
            Formatted string report
        """
        npv = self.get_synergy_npv()
        value = self.get_total_value_creation()
        bridge = self.get_value_bridge_df()

        report = f"""
{'='*80}
USS-NIPPON STEEL: VALUE CREATION ANALYSIS
{'='*80}

DEAL OVERVIEW
{'-'*80}
Deal Price:                 ${DEAL_PRICE_PER_SHARE:.2f}/share
USS Standalone Value:       ${self.uss_standalone_value:.2f}/share
Premium Paid:               ${value['premium_per_share']:.2f}/share ({value['premium_per_share']/self.uss_standalone_value*100:.1f}%)
Total Deal Value:           ${DEAL_EQUITY_VALUE:,.0f}M equity + ${NSA_CAPEX_COMMITMENT:,.0f}M CapEx = ${TOTAL_CAPITAL_DEPLOYMENT:,.0f}M

SYNERGY NPV (10-Year DCF @ 7.5% WACC)
{'-'*80}
Cost Synergies:             ${npv['cost_synergies_npv']:,.0f}M
Technology Synergies:       ${npv['technology_synergies_npv']:,.0f}M
Revenue Synergies:          ${npv['revenue_synergies_npv']:,.0f}M
Strategic Synergies:        ${npv['strategic_synergies_npv']:,.0f}M
Integration Costs:          (${-npv['integration_costs_npv']:,.0f}M)
{'-'*40}
TOTAL SYNERGY NPV:          ${npv['total_synergy_npv']:,.0f}M

WACC ADVANTAGE
{'-'*80}
USS Standalone WACC:        {USS_STANDALONE_WACC:.1%}
Nippon Combined WACC:       {NIPPON_COMBINED_WACC:.1%}
WACC Spread:                {(USS_STANDALONE_WACC - NIPPON_COMBINED_WACC)*100:.1f}pp
Value from WACC Benefit:    ${value['wacc_benefit_total_M']:,.0f}M

TOTAL VALUE CREATION
{'-'*80}
Synergy NPV:                ${npv['total_synergy_npv']:,.0f}M
WACC Benefit:               ${value['wacc_benefit_total_M']:,.0f}M
{'-'*40}
TOTAL VALUE CREATED:        ${value['total_value_created_M']:,.0f}M
Per Share:                  ${value['value_created_per_share']:.2f}

VALUE BRIDGE (Year 0 to Year 10)
{'-'*80}
"""
        # Add value bridge table
        report += bridge.to_string(index=False)
        report += f"""

SYNERGY RUN-RATES AT FULL REALIZATION (Year 5+)
{'-'*80}
"""
        # Add synergy summary
        synergy_df = self.get_synergy_summary()
        total_weighted = synergy_df['Weighted_Run_Rate'].sum()

        for _, row in synergy_df.iterrows():
            if row['Run_Rate_EBITDA_Mid'] > 0:
                report += f"{row['Name']:<30} ${row['Weighted_Run_Rate']:>6.0f}M (conf: {row['Confidence']})\n"

        report += f"{'-'*40}\n"
        report += f"{'TOTAL WEIGHTED RUN-RATE':<30} ${total_weighted:>6.0f}M/year\n"

        report += f"""
{'='*80}
CONCLUSION: Deal creates ${value['total_value_created_M']/1000:.1f}B in value through synergies and WACC advantage
{'='*80}
"""
        return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run value creation analysis and print summary."""
    print("\nInitializing Value Creation Analysis...")

    analysis = ValueCreationAnalysis(ScenarioType.BASE_CASE)

    # Print summary report
    print(analysis.generate_summary_report())

    # Return for further use
    return analysis


if __name__ == "__main__":
    analysis = main()
