#!/usr/bin/env python3
"""
Nippon Steel Capacity Analysis Module
=====================================

Assesses Nippon Steel's capacity to fund and execute the USS acquisition,
including pro forma leverage analysis, funding gap assessment, and stress testing.

Key Components:
- Pro forma leverage calculations
- Funding gap analysis
- Stress testing (downturn, interest rates, currency)
- Deal capacity verdict
"""

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import pandas as pd
import numpy as np

# Import financial profile module
sys.path.insert(0, str(Path(__file__).parent))
from nippon_financial_profile import (
    NipponFinancialProfile, NipponFinancials, CreditMetrics,
    build_nippon_financial_profile, calculate_credit_metrics,
    FX_RATE_JPY_USD, FX_RATE_JPY_USD_LOW, FX_RATE_JPY_USD_HIGH,
    DEAL_EQUITY_PRICE, NSA_INVESTMENT_COMMITMENTS, TOTAL_CAPITAL_DEPLOYMENT,
    INVESTMENT_GRADE_THRESHOLDS
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Financing assumptions
DEBT_FINANCING_PCT = 0.60  # 60% debt / 40% equity for acquisition
BRIDGE_LOAN_SPREAD = 0.015  # 150bps over SOFR for bridge financing
TERM_LOAN_SPREAD = 0.0175   # 175bps over SOFR for term loan
BOND_SPREAD = 0.0125        # 125bps over treasuries

# Assumed market rates
SOFR_RATE = 0.053           # ~5.3% as of late 2024
US_10YR_TREASURY = 0.043    # ~4.3% as of late 2024
JGB_10YR = 0.009            # ~0.9% Japan govt bond

# Pro forma assumptions
EBITDA_DILUTION_YEAR_1 = 0.05  # 5% EBITDA dilution from integration costs
SYNERGY_RAMP_YEARS = 3         # Years to full synergy realization

# Investment grade thresholds
MAX_DEBT_TO_EBITDA_IG = 3.5    # Maximum for solid investment grade
COMFORTABLE_COVERAGE = 4.0     # Comfortable interest coverage

# Stress test parameters
STEEL_DOWNTURN_EBITDA_DROP = 0.25   # 25% EBITDA decline in downturn
SEVERE_DOWNTURN_EBITDA_DROP = 0.40  # 40% EBITDA decline in severe downturn
INTEREST_RATE_SHOCK = 0.02          # +200bps rate shock
YEN_DEPRECIATION_SHOCK = 0.15       # 15% yen weakening


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FinancingStructure:
    """Proposed financing structure for the acquisition"""

    # Sources of funds ($M)
    cash_on_hand: float = 0.0
    new_term_loan: float = 0.0
    new_bonds: float = 0.0
    bridge_loan: float = 0.0
    equity_issuance: float = 0.0
    asset_sales: float = 0.0
    credit_facility_draw: float = 0.0

    # Uses of funds ($M)
    acquisition_price: float = DEAL_EQUITY_PRICE
    transaction_costs: float = 200.0  # ~1.3% of deal value
    debt_refinancing: float = 0.0
    breakup_fee_escrow: float = 565.0

    @property
    def total_sources(self) -> float:
        return (self.cash_on_hand + self.new_term_loan + self.new_bonds +
                self.bridge_loan + self.equity_issuance + self.asset_sales +
                self.credit_facility_draw)

    @property
    def total_uses(self) -> float:
        return (self.acquisition_price + self.transaction_costs +
                self.debt_refinancing + self.breakup_fee_escrow)

    @property
    def funding_surplus_deficit(self) -> float:
        return self.total_sources - self.total_uses


@dataclass
class NSACommitmentSchedule:
    """NSA investment commitment schedule"""

    # Annual capex commitments ($M)
    year_1: float = 2800.0
    year_2: float = 3200.0
    year_3: float = 3000.0
    year_4: float = 2500.0
    year_5: float = 2500.0

    @property
    def total_commitment(self) -> float:
        return self.year_1 + self.year_2 + self.year_3 + self.year_4 + self.year_5

    def get_annual_schedule(self) -> Dict[int, float]:
        return {
            1: self.year_1,
            2: self.year_2,
            3: self.year_3,
            4: self.year_4,
            5: self.year_5,
        }


@dataclass
class ProFormaMetrics:
    """Pro forma credit metrics post-acquisition"""

    # Pre-deal metrics
    pre_deal_debt_usd: float = 0.0
    pre_deal_ebitda_usd: float = 0.0
    pre_deal_debt_to_ebitda: float = 0.0
    pre_deal_interest_coverage: float = 0.0

    # Deal impact
    new_debt_usd: float = 0.0
    uss_ebitda_contribution: float = 0.0
    integration_costs_year_1: float = 0.0
    synergy_value_year_1: float = 0.0

    # Post-deal metrics (Year 1)
    post_deal_debt_usd: float = 0.0
    post_deal_ebitda_usd: float = 0.0
    post_deal_debt_to_ebitda: float = 0.0
    post_deal_interest_expense: float = 0.0
    post_deal_interest_coverage: float = 0.0

    # Post-deal metrics (Stabilized - Year 3)
    stabilized_ebitda_usd: float = 0.0
    stabilized_debt_usd: float = 0.0
    stabilized_debt_to_ebitda: float = 0.0

    # Rating impact assessment
    pre_deal_implied_rating: str = ""
    post_deal_implied_rating: str = ""
    rating_notches_change: int = 0

    @property
    def leverage_increase(self) -> float:
        return self.post_deal_debt_to_ebitda - self.pre_deal_debt_to_ebitda


@dataclass
class FundingGapAnalysis:
    """Analysis of funding gap and sources"""

    # Total capital requirement ($M)
    acquisition_capital: float = DEAL_EQUITY_PRICE
    nsa_investment_year_1: float = 2800.0
    nsa_investment_total: float = NSA_INVESTMENT_COMMITMENTS
    total_requirement: float = TOTAL_CAPITAL_DEPLOYMENT

    # Available resources ($M)
    cash_available: float = 0.0
    operating_fcf_annual: float = 0.0
    credit_facility_headroom: float = 0.0
    debt_capacity_to_ig_threshold: float = 0.0
    equity_raise_potential: float = 0.0

    # Gap analysis
    immediate_funding_gap: float = 0.0
    multi_year_funding_gap: float = 0.0
    sources_identified: float = 0.0
    gap_coverage_ratio: float = 0.0

    # Funding assessment
    can_fund_acquisition: bool = True
    can_fund_nsa_commitments: bool = True
    requires_equity_issuance: bool = False
    rating_at_risk: bool = False


@dataclass
class StressTestResult:
    """Results from a stress test scenario"""

    scenario_name: str
    scenario_description: str

    # Stressed metrics
    stressed_ebitda_usd: float = 0.0
    stressed_debt_to_ebitda: float = 0.0
    stressed_interest_coverage: float = 0.0

    # Impact assessment
    breaches_ig_threshold: bool = False
    liquidity_adequate: bool = True
    covenant_breach_risk: str = "Low"

    # Recovery analysis
    years_to_recover: int = 0
    recovery_path: str = ""


@dataclass
class DealCapacityVerdict:
    """Final assessment of Nippon's deal capacity"""

    # Overall verdict
    verdict: str  # "Yes", "Conditional", "No"
    confidence_level: str  # "High", "Medium", "Low"

    # Key findings
    balance_sheet_capacity: str
    funding_adequacy: str
    credit_impact: str
    stress_resilience: str

    # Risk factors
    key_risks: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Supporting metrics
    pro_forma_leverage: float = 0.0
    funding_gap_coverage: float = 0.0
    downside_leverage: float = 0.0


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def create_financing_structure(profile: NipponFinancialProfile,
                                debt_pct: float = DEBT_FINANCING_PCT,
                                fx_rate: float = FX_RATE_JPY_USD) -> FinancingStructure:
    """Create proposed financing structure for the acquisition"""

    fin_usd = profile.latest_financials.to_usd(fx_rate)

    # Acquisition financing
    debt_component = DEAL_EQUITY_PRICE * debt_pct
    equity_component = DEAL_EQUITY_PRICE * (1 - debt_pct)

    # Use available cash for part of equity portion
    cash_contribution = min(fin_usd.cash_and_equivalents * 1000 * 0.5, equity_component * 0.3)  # Use max 50% of cash

    # Financing structure
    financing = FinancingStructure(
        # Sources
        cash_on_hand=cash_contribution,
        new_term_loan=debt_component * 0.4,  # 40% of debt as term loan
        new_bonds=debt_component * 0.5,      # 50% of debt as bonds
        bridge_loan=debt_component * 0.1,    # 10% as bridge (to be refinanced)
        equity_issuance=equity_component - cash_contribution,
        credit_facility_draw=0.0,  # Keep credit facility as backup
        asset_sales=0.0,

        # Uses
        acquisition_price=DEAL_EQUITY_PRICE,
        transaction_costs=200.0,
        debt_refinancing=0.0,
        breakup_fee_escrow=565.0,
    )

    return financing


def calculate_pro_forma_metrics(profile: NipponFinancialProfile,
                                 financing: FinancingStructure,
                                 uss_ebitda: float = 2100.0,  # $M estimated USS EBITDA (based on 2023 actuals)
                                 synergy_run_rate: float = 300.0,  # $M annual synergies at run rate
                                 fx_rate: float = FX_RATE_JPY_USD) -> ProFormaMetrics:
    """Calculate pro forma credit metrics post-acquisition"""

    fin_usd = profile.latest_financials.to_usd(fx_rate)

    # Pre-deal metrics (convert to $M)
    pre_debt = fin_usd.total_debt * 1000  # $B to $M
    pre_ebitda = fin_usd.ebitda * 1000
    pre_interest = fin_usd.interest_expense * 1000

    # New debt from acquisition
    new_debt = financing.new_term_loan + financing.new_bonds + financing.bridge_loan

    # Post-deal debt
    post_debt = pre_debt + new_debt

    # Post-deal EBITDA Year 1 (with integration costs, minimal synergies)
    integration_costs = 400.0  # $M Year 1 integration costs
    synergy_year_1 = synergy_run_rate * 0.2  # 20% of synergies realized Year 1
    post_ebitda_y1 = pre_ebitda + uss_ebitda - integration_costs + synergy_year_1

    # Interest expense calculation
    # Weighted average cost of new debt
    new_debt_rate = (
        (financing.new_term_loan * (SOFR_RATE + TERM_LOAN_SPREAD) +
         financing.new_bonds * (US_10YR_TREASURY + BOND_SPREAD) +
         financing.bridge_loan * (SOFR_RATE + BRIDGE_LOAN_SPREAD)) /
        max(new_debt, 1)
    )
    new_interest = new_debt * new_debt_rate
    post_interest = pre_interest + new_interest

    # Stabilized metrics (Year 3)
    post_debt_y3 = post_debt - 1000  # Assume $1B debt paydown over 3 years
    synergy_y3 = synergy_run_rate  # Full synergies realized
    stabilized_ebitda = pre_ebitda + uss_ebitda + synergy_y3

    # Calculate implied ratings
    pre_metrics = calculate_credit_metrics(profile.latest_financials)

    return ProFormaMetrics(
        # Pre-deal
        pre_deal_debt_usd=pre_debt,
        pre_deal_ebitda_usd=pre_ebitda,
        pre_deal_debt_to_ebitda=pre_debt / pre_ebitda if pre_ebitda > 0 else 0,
        pre_deal_interest_coverage=pre_ebitda / pre_interest if pre_interest > 0 else 0,

        # Deal impact
        new_debt_usd=new_debt,
        uss_ebitda_contribution=uss_ebitda,
        integration_costs_year_1=integration_costs,
        synergy_value_year_1=synergy_year_1,

        # Post-deal Year 1
        post_deal_debt_usd=post_debt,
        post_deal_ebitda_usd=post_ebitda_y1,
        post_deal_debt_to_ebitda=post_debt / post_ebitda_y1 if post_ebitda_y1 > 0 else 0,
        post_deal_interest_expense=post_interest,
        post_deal_interest_coverage=post_ebitda_y1 / post_interest if post_interest > 0 else 0,

        # Stabilized Year 3
        stabilized_ebitda_usd=stabilized_ebitda,
        stabilized_debt_usd=post_debt_y3,
        stabilized_debt_to_ebitda=post_debt_y3 / stabilized_ebitda if stabilized_ebitda > 0 else 0,

        # Rating impact
        pre_deal_implied_rating=pre_metrics.implied_rating,
        post_deal_implied_rating="BBB" if post_debt / post_ebitda_y1 < 3.5 else "BBB-",
        rating_notches_change=-1 if post_debt / post_ebitda_y1 > 2.5 else 0,
    )


def analyze_funding_gap(profile: NipponFinancialProfile,
                         pro_forma: ProFormaMetrics,
                         nsa_schedule: NSACommitmentSchedule = None,
                         fx_rate: float = FX_RATE_JPY_USD) -> FundingGapAnalysis:
    """Analyze funding gap and sources"""

    if nsa_schedule is None:
        nsa_schedule = NSACommitmentSchedule()

    fin_usd = profile.latest_financials.to_usd(fx_rate)

    # Available resources (convert to $M)
    cash = fin_usd.cash_and_equivalents * 1000

    # Use actual FCF if available, otherwise estimate from EBITDA
    if fin_usd.free_cash_flow > 0:
        fcf_annual = fin_usd.free_cash_flow * 1000
    else:
        # Estimate FCF as EBITDA * 40% (after capex, interest, taxes, working capital)
        fcf_annual = fin_usd.ebitda * 1000 * 0.40

    # Credit facility headroom - use actual if available, otherwise estimate
    # Based on Nippon Steel disclosures, they have ~¥600B ($4B) undrawn facilities
    if fin_usd.available_credit_facilities > 0:
        credit_headroom = fin_usd.available_credit_facilities * 1000
    else:
        credit_headroom = 4000.0  # $4B estimated based on public disclosures

    # Debt capacity to maintain investment grade
    # At 3.5x Debt/EBITDA threshold
    max_ig_debt = pro_forma.post_deal_ebitda_usd * MAX_DEBT_TO_EBITDA_IG
    debt_capacity = max(0, max_ig_debt - pro_forma.post_deal_debt_usd)

    # Equity raise potential (assume up to 10% of market cap)
    market_cap_usd = 25_000  # ~$25B market cap
    equity_potential = market_cap_usd * 0.10

    # Immediate funding needs (acquisition)
    immediate_need = DEAL_EQUITY_PRICE

    # Multi-year needs (acquisition + 5-year NSA)
    multi_year_need = DEAL_EQUITY_PRICE + nsa_schedule.total_commitment

    # 5-year cumulative FCF
    fcf_5yr = fcf_annual * 5

    # Total resources
    total_resources = cash + fcf_5yr + credit_headroom + debt_capacity + equity_potential

    # Gap analysis
    immediate_gap = max(0, immediate_need - cash - credit_headroom)
    multi_year_gap = max(0, multi_year_need - total_resources)

    return FundingGapAnalysis(
        acquisition_capital=DEAL_EQUITY_PRICE,
        nsa_investment_year_1=nsa_schedule.year_1,
        nsa_investment_total=nsa_schedule.total_commitment,
        total_requirement=TOTAL_CAPITAL_DEPLOYMENT,

        cash_available=cash,
        operating_fcf_annual=fcf_annual,
        credit_facility_headroom=credit_headroom,
        debt_capacity_to_ig_threshold=debt_capacity,
        equity_raise_potential=equity_potential,

        immediate_funding_gap=immediate_gap,
        multi_year_funding_gap=multi_year_gap,
        sources_identified=total_resources,
        gap_coverage_ratio=total_resources / multi_year_need if multi_year_need > 0 else 0,

        can_fund_acquisition=immediate_gap == 0 or debt_capacity > immediate_gap,
        can_fund_nsa_commitments=multi_year_gap == 0,
        requires_equity_issuance=immediate_gap > debt_capacity + credit_headroom,
        rating_at_risk=pro_forma.post_deal_debt_to_ebitda > MAX_DEBT_TO_EBITDA_IG,
    )


def run_stress_test(profile: NipponFinancialProfile,
                     pro_forma: ProFormaMetrics,
                     scenario: str = "downturn") -> StressTestResult:
    """Run stress test on pro forma metrics"""

    scenarios = {
        "downturn": {
            "name": "Steel Downturn",
            "description": "25% EBITDA decline (comparable to 2015-2016)",
            "ebitda_factor": 1 - STEEL_DOWNTURN_EBITDA_DROP,
        },
        "severe_downturn": {
            "name": "Severe Downturn",
            "description": "40% EBITDA decline (comparable to 2008-2009)",
            "ebitda_factor": 1 - SEVERE_DOWNTURN_EBITDA_DROP,
        },
        "rate_shock": {
            "name": "Interest Rate Shock",
            "description": "+200bps across all rates",
            "rate_increase": INTEREST_RATE_SHOCK,
        },
        "yen_weak": {
            "name": "Yen Depreciation",
            "description": "15% yen weakening vs USD",
            "fx_factor": 1 + YEN_DEPRECIATION_SHOCK,
        },
    }

    if scenario not in scenarios:
        scenario = "downturn"

    config = scenarios[scenario]

    # Apply stress
    if "ebitda_factor" in config:
        stressed_ebitda = pro_forma.post_deal_ebitda_usd * config["ebitda_factor"]
        stressed_debt = pro_forma.post_deal_debt_usd  # Debt unchanged
        stressed_interest = pro_forma.post_deal_interest_expense
    elif "rate_increase" in config:
        stressed_ebitda = pro_forma.post_deal_ebitda_usd
        stressed_debt = pro_forma.post_deal_debt_usd
        # Higher interest expense
        additional_interest = stressed_debt * config["rate_increase"]
        stressed_interest = pro_forma.post_deal_interest_expense + additional_interest
    elif "fx_factor" in config:
        # Yen weakening increases USD debt value but also USD earnings
        # Net effect on Japanese company with USD debt is mixed
        stressed_ebitda = pro_forma.post_deal_ebitda_usd  # Assume earnings hedge
        stressed_debt = pro_forma.post_deal_debt_usd * (1 + 0.05)  # Small debt increase
        stressed_interest = pro_forma.post_deal_interest_expense * 1.05
    else:
        stressed_ebitda = pro_forma.post_deal_ebitda_usd
        stressed_debt = pro_forma.post_deal_debt_usd
        stressed_interest = pro_forma.post_deal_interest_expense

    stressed_leverage = stressed_debt / stressed_ebitda if stressed_ebitda > 0 else 999
    stressed_coverage = stressed_ebitda / stressed_interest if stressed_interest > 0 else 0

    return StressTestResult(
        scenario_name=config["name"],
        scenario_description=config["description"],
        stressed_ebitda_usd=stressed_ebitda,
        stressed_debt_to_ebitda=stressed_leverage,
        stressed_interest_coverage=stressed_coverage,
        breaches_ig_threshold=stressed_leverage > MAX_DEBT_TO_EBITDA_IG,
        liquidity_adequate=stressed_coverage > 2.0,
        covenant_breach_risk="High" if stressed_leverage > 4.0 else "Medium" if stressed_leverage > 3.5 else "Low",
        years_to_recover=2 if stressed_leverage < 4.0 else 3,
        recovery_path="FCF generation + asset sales" if stressed_leverage > 3.5 else "Normal FCF generation",
    )


def assess_deal_capacity(profile: NipponFinancialProfile,
                          fx_rate: float = FX_RATE_JPY_USD) -> DealCapacityVerdict:
    """Generate final deal capacity assessment"""

    # Run full analysis
    financing = create_financing_structure(profile, fx_rate=fx_rate)
    pro_forma = calculate_pro_forma_metrics(profile, financing, fx_rate=fx_rate)
    funding_gap = analyze_funding_gap(profile, pro_forma, fx_rate=fx_rate)

    # Run stress tests
    downturn = run_stress_test(profile, pro_forma, "downturn")
    severe = run_stress_test(profile, pro_forma, "severe_downturn")

    # Assess balance sheet capacity
    if pro_forma.post_deal_debt_to_ebitda < 2.5:
        balance_sheet = "Strong - ample capacity for deal leverage"
    elif pro_forma.post_deal_debt_to_ebitda < 3.0:
        balance_sheet = "Adequate - manageable leverage increase"
    elif pro_forma.post_deal_debt_to_ebitda < 3.5:
        balance_sheet = "Stretched - near investment grade threshold"
    else:
        balance_sheet = "Strained - risk of rating downgrade"

    # Assess funding adequacy
    if funding_gap.gap_coverage_ratio > 1.5:
        funding_adequacy = "Sufficient - multiple funding sources available"
    elif funding_gap.gap_coverage_ratio > 1.2:
        funding_adequacy = "Adequate - needs execution discipline"
    elif funding_gap.gap_coverage_ratio > 1.0:
        funding_adequacy = "Tight - limited margin for error"
    else:
        funding_adequacy = "Insufficient - funding gap identified"

    # Assess credit impact
    if pro_forma.rating_notches_change == 0:
        credit_impact = "Minimal - rating expected to be maintained"
    elif pro_forma.rating_notches_change == -1:
        credit_impact = "Moderate - 1 notch downgrade possible"
    else:
        credit_impact = "Significant - multi-notch downgrade risk"

    # Assess stress resilience
    if not downturn.breaches_ig_threshold:
        stress_resilience = "Strong - maintains IG in downturn"
    elif not severe.breaches_ig_threshold:
        stress_resilience = "Moderate - maintains IG except severe stress"
    else:
        stress_resilience = "Weak - downturn would breach IG threshold"

    # Determine verdict
    # Note: For large M&A, funding gaps are common and can be addressed through
    # additional equity, asset sales, or extended timelines
    if (pro_forma.post_deal_debt_to_ebitda < 3.0 and
        funding_gap.gap_coverage_ratio > 1.2 and
        not downturn.breaches_ig_threshold):
        verdict = "Yes"
        confidence = "High"
    elif (pro_forma.post_deal_debt_to_ebitda < 3.5 and
          funding_gap.gap_coverage_ratio > 0.85 and
          downturn.stressed_debt_to_ebitda < 4.5):
        # Conditional: Deal is financeable with some adjustments
        verdict = "Conditional"
        confidence = "Medium"
    elif (pro_forma.post_deal_debt_to_ebitda < 4.0 and
          funding_gap.gap_coverage_ratio > 0.75):
        # Stretched but possible with significant equity/asset sales
        verdict = "Conditional"
        confidence = "Low"
    else:
        verdict = "No"
        confidence = "Low"

    # Key risks
    risks = []
    if pro_forma.post_deal_debt_to_ebitda > 3.0:
        risks.append("Elevated leverage post-close")
    if downturn.breaches_ig_threshold:
        risks.append("Downturn could breach IG threshold")
    if funding_gap.requires_equity_issuance:
        risks.append("May require equity issuance")
    if pro_forma.post_deal_interest_coverage < 5.0:
        risks.append("Interest coverage below comfortable level")

    # Mitigating factors
    mitigants = []
    mitigants.append(f"Strong pre-deal balance sheet (Debt/EBITDA: {pro_forma.pre_deal_debt_to_ebitda:.1f}x)")
    mitigants.append("Committed financing arrangements likely in place")
    mitigants.append(f"USS adds significant EBITDA (${pro_forma.uss_ebitda_contribution/1000:.1f}B)")
    mitigants.append("Can increase equity component to improve funding gap")
    mitigants.append("Asset sale capacity (has sold POSCO, Kobe Steel stakes)")
    mitigants.append("Combined entity has stronger FCF generation")
    if funding_gap.gap_coverage_ratio > 1.2:
        mitigants.append("Multiple funding sources available")

    # Recommendations
    recommendations = []
    recommendations.append("Confirm committed financing arrangements")
    if pro_forma.post_deal_debt_to_ebitda > 2.5:
        recommendations.append("Prioritize deleveraging post-close")
    recommendations.append("Hedge JPY/USD exposure on acquisition debt")
    recommendations.append("Maintain credit facility availability as liquidity buffer")
    recommendations.append("Sequence NSA investments based on steel cycle conditions")

    return DealCapacityVerdict(
        verdict=verdict,
        confidence_level=confidence,
        balance_sheet_capacity=balance_sheet,
        funding_adequacy=funding_adequacy,
        credit_impact=credit_impact,
        stress_resilience=stress_resilience,
        key_risks=risks,
        mitigating_factors=mitigants,
        recommendations=recommendations,
        pro_forma_leverage=pro_forma.post_deal_debt_to_ebitda,
        funding_gap_coverage=funding_gap.gap_coverage_ratio,
        downside_leverage=downturn.stressed_debt_to_ebitda,
    )


# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

def get_pro_forma_summary_table(pro_forma: ProFormaMetrics) -> pd.DataFrame:
    """Generate pro forma comparison table"""

    data = [
        {"Metric": "Total Debt ($B)", "Pre-Deal": pro_forma.pre_deal_debt_usd / 1000,
         "Post-Deal (Y1)": pro_forma.post_deal_debt_usd / 1000,
         "Stabilized (Y3)": pro_forma.stabilized_debt_usd / 1000},
        {"Metric": "EBITDA ($B)", "Pre-Deal": pro_forma.pre_deal_ebitda_usd / 1000,
         "Post-Deal (Y1)": pro_forma.post_deal_ebitda_usd / 1000,
         "Stabilized (Y3)": pro_forma.stabilized_ebitda_usd / 1000},
        {"Metric": "Debt/EBITDA", "Pre-Deal": f"{pro_forma.pre_deal_debt_to_ebitda:.2f}x",
         "Post-Deal (Y1)": f"{pro_forma.post_deal_debt_to_ebitda:.2f}x",
         "Stabilized (Y3)": f"{pro_forma.stabilized_debt_to_ebitda:.2f}x"},
        {"Metric": "Interest Coverage", "Pre-Deal": f"{pro_forma.pre_deal_interest_coverage:.1f}x",
         "Post-Deal (Y1)": f"{pro_forma.post_deal_interest_coverage:.1f}x",
         "Stabilized (Y3)": "-"},
        {"Metric": "Implied Rating", "Pre-Deal": pro_forma.pre_deal_implied_rating,
         "Post-Deal (Y1)": pro_forma.post_deal_implied_rating,
         "Stabilized (Y3)": pro_forma.pre_deal_implied_rating},
    ]

    return pd.DataFrame(data)


def get_funding_gap_table(gap: FundingGapAnalysis) -> pd.DataFrame:
    """Generate funding gap analysis table"""

    data = [
        {"Category": "CAPITAL REQUIREMENTS", "Amount ($M)": ""},
        {"Category": "  Acquisition Price", "Amount ($M)": f"{gap.acquisition_capital:,.0f}"},
        {"Category": "  NSA Investment (Year 1)", "Amount ($M)": f"{gap.nsa_investment_year_1:,.0f}"},
        {"Category": "  NSA Investment (5-Year Total)", "Amount ($M)": f"{gap.nsa_investment_total:,.0f}"},
        {"Category": "  Total Capital Deployment", "Amount ($M)": f"{gap.total_requirement:,.0f}"},
        {"Category": "", "Amount ($M)": ""},
        {"Category": "AVAILABLE RESOURCES", "Amount ($M)": ""},
        {"Category": "  Cash on Hand", "Amount ($M)": f"{gap.cash_available:,.0f}"},
        {"Category": "  Annual Operating FCF", "Amount ($M)": f"{gap.operating_fcf_annual:,.0f}"},
        {"Category": "  Credit Facility Headroom", "Amount ($M)": f"{gap.credit_facility_headroom:,.0f}"},
        {"Category": "  Debt Capacity (to IG threshold)", "Amount ($M)": f"{gap.debt_capacity_to_ig_threshold:,.0f}"},
        {"Category": "  Equity Raise Potential", "Amount ($M)": f"{gap.equity_raise_potential:,.0f}"},
        {"Category": "", "Amount ($M)": ""},
        {"Category": "GAP ANALYSIS", "Amount ($M)": ""},
        {"Category": "  Immediate Funding Gap", "Amount ($M)": f"{gap.immediate_funding_gap:,.0f}"},
        {"Category": "  Multi-Year Funding Gap", "Amount ($M)": f"{gap.multi_year_funding_gap:,.0f}"},
        {"Category": "  Gap Coverage Ratio", "Amount ($M)": f"{gap.gap_coverage_ratio:.2f}x"},
    ]

    return pd.DataFrame(data)


def get_stress_test_table(profile: NipponFinancialProfile,
                           pro_forma: ProFormaMetrics) -> pd.DataFrame:
    """Generate stress test comparison table"""

    scenarios = ["downturn", "severe_downturn", "rate_shock", "yen_weak"]
    results = [run_stress_test(profile, pro_forma, s) for s in scenarios]

    data = []
    for r in results:
        data.append({
            "Scenario": r.scenario_name,
            "Description": r.scenario_description,
            "Debt/EBITDA": f"{r.stressed_debt_to_ebitda:.2f}x",
            "Coverage": f"{r.stressed_interest_coverage:.1f}x",
            "IG Breach": "Yes" if r.breaches_ig_threshold else "No",
            "Risk Level": r.covenant_breach_risk,
        })

    return pd.DataFrame(data)


def export_capacity_analysis(output_dir: Path = None) -> Dict[str, Path]:
    """Export all capacity analysis to CSV files"""

    if output_dir is None:
        output_dir = Path(__file__).parent / 'data'

    output_dir.mkdir(exist_ok=True)

    # Build profile and run analysis
    profile = build_nippon_financial_profile()
    financing = create_financing_structure(profile)
    pro_forma = calculate_pro_forma_metrics(profile, financing)
    funding_gap = analyze_funding_gap(profile, pro_forma)
    verdict = assess_deal_capacity(profile)

    exports = {}

    # Pro forma metrics
    df = get_pro_forma_summary_table(pro_forma)
    path = output_dir / 'pro_forma_metrics.csv'
    df.to_csv(path, index=False)
    exports['pro_forma'] = path

    # Funding gap
    df = get_funding_gap_table(funding_gap)
    path = output_dir / 'funding_gap_analysis.csv'
    df.to_csv(path, index=False)
    exports['funding_gap'] = path

    # Stress tests
    df = get_stress_test_table(profile, pro_forma)
    path = output_dir / 'stress_tests.csv'
    df.to_csv(path, index=False)
    exports['stress_tests'] = path

    # Peer comparison (from profile)
    from nippon_financial_profile import get_peer_comparison_table
    df = get_peer_comparison_table(profile)
    path = output_dir / 'peer_comparison.csv'
    df.to_csv(path, index=False)
    exports['peer_comparison'] = path

    return exports


# =============================================================================
# MAIN / CLI
# =============================================================================

def main():
    """Run full capacity analysis and print summary"""

    print("=" * 70)
    print("NIPPON STEEL ACQUISITION CAPACITY ANALYSIS")
    print("=" * 70)

    # Build profile
    profile = build_nippon_financial_profile()

    # Create financing structure
    financing = create_financing_structure(profile)

    print("\n" + "=" * 70)
    print("PROPOSED FINANCING STRUCTURE")
    print("=" * 70)
    print(f"\nSources of Funds:")
    print(f"  Cash on Hand:          ${financing.cash_on_hand:,.0f}M")
    print(f"  New Term Loan:         ${financing.new_term_loan:,.0f}M")
    print(f"  New Bonds:             ${financing.new_bonds:,.0f}M")
    print(f"  Bridge Loan:           ${financing.bridge_loan:,.0f}M")
    print(f"  Equity Issuance:       ${financing.equity_issuance:,.0f}M")
    print(f"  Total Sources:         ${financing.total_sources:,.0f}M")
    print(f"\nUses of Funds:")
    print(f"  Acquisition Price:     ${financing.acquisition_price:,.0f}M")
    print(f"  Transaction Costs:     ${financing.transaction_costs:,.0f}M")
    print(f"  Breakup Fee Escrow:    ${financing.breakup_fee_escrow:,.0f}M")
    print(f"  Total Uses:            ${financing.total_uses:,.0f}M")
    print(f"\n  Surplus/(Deficit):     ${financing.funding_surplus_deficit:,.0f}M")

    # Calculate pro forma metrics
    pro_forma = calculate_pro_forma_metrics(profile, financing)

    print("\n" + "=" * 70)
    print("PRO FORMA CREDIT METRICS")
    print("=" * 70)
    print(f"\n{'Metric':<25} {'Pre-Deal':>12} {'Post-Deal':>12} {'Stabilized':>12}")
    print("-" * 70)
    print(f"{'Total Debt ($B)':<25} {pro_forma.pre_deal_debt_usd/1000:>12.1f} {pro_forma.post_deal_debt_usd/1000:>12.1f} {pro_forma.stabilized_debt_usd/1000:>12.1f}")
    print(f"{'EBITDA ($B)':<25} {pro_forma.pre_deal_ebitda_usd/1000:>12.1f} {pro_forma.post_deal_ebitda_usd/1000:>12.1f} {pro_forma.stabilized_ebitda_usd/1000:>12.1f}")
    print(f"{'Debt/EBITDA':<25} {pro_forma.pre_deal_debt_to_ebitda:>11.2f}x {pro_forma.post_deal_debt_to_ebitda:>11.2f}x {pro_forma.stabilized_debt_to_ebitda:>11.2f}x")
    print(f"{'Interest Coverage':<25} {pro_forma.pre_deal_interest_coverage:>11.1f}x {pro_forma.post_deal_interest_coverage:>11.1f}x {'N/A':>12}")
    print(f"{'Implied Rating':<25} {pro_forma.pre_deal_implied_rating:>12} {pro_forma.post_deal_implied_rating:>12} {pro_forma.pre_deal_implied_rating:>12}")

    # Funding gap analysis
    funding_gap = analyze_funding_gap(profile, pro_forma)

    print("\n" + "=" * 70)
    print("FUNDING GAP ANALYSIS")
    print("=" * 70)
    print(f"\nCapital Requirements:")
    print(f"  Acquisition Price:          ${funding_gap.acquisition_capital:,.0f}M")
    print(f"  NSA Investment (5-year):    ${funding_gap.nsa_investment_total:,.0f}M")
    print(f"  Total Capital Deployment:   ${funding_gap.total_requirement:,.0f}M")
    print(f"\nAvailable Resources:")
    print(f"  Cash Available:             ${funding_gap.cash_available:,.0f}M")
    print(f"  Annual FCF (x5 years):      ${funding_gap.operating_fcf_annual * 5:,.0f}M")
    print(f"  Credit Facility Headroom:   ${funding_gap.credit_facility_headroom:,.0f}M")
    print(f"  Debt Capacity to IG:        ${funding_gap.debt_capacity_to_ig_threshold:,.0f}M")
    print(f"\nGap Coverage Ratio:           {funding_gap.gap_coverage_ratio:.2f}x")
    print(f"Can Fund Acquisition:         {'Yes' if funding_gap.can_fund_acquisition else 'No'}")
    print(f"Can Fund NSA Commitments:     {'Yes' if funding_gap.can_fund_nsa_commitments else 'No'}")

    # Stress tests
    print("\n" + "=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)

    for scenario in ["downturn", "severe_downturn", "rate_shock", "yen_weak"]:
        result = run_stress_test(profile, pro_forma, scenario)
        print(f"\n{result.scenario_name}:")
        print(f"  {result.scenario_description}")
        print(f"  Debt/EBITDA: {result.stressed_debt_to_ebitda:.2f}x")
        print(f"  Coverage: {result.stressed_interest_coverage:.1f}x")
        print(f"  IG Breach: {'Yes' if result.breaches_ig_threshold else 'No'}")
        print(f"  Risk Level: {result.covenant_breach_risk}")

    # Final verdict
    verdict = assess_deal_capacity(profile)

    print("\n" + "=" * 70)
    print("DEAL CAPACITY VERDICT")
    print("=" * 70)
    print(f"\n  VERDICT: {verdict.verdict}")
    print(f"  Confidence: {verdict.confidence_level}")
    print(f"\nAssessments:")
    print(f"  Balance Sheet:    {verdict.balance_sheet_capacity}")
    print(f"  Funding:          {verdict.funding_adequacy}")
    print(f"  Credit Impact:    {verdict.credit_impact}")
    print(f"  Stress Resilience: {verdict.stress_resilience}")
    print(f"\nKey Risks:")
    for risk in verdict.key_risks:
        print(f"  - {risk}")
    print(f"\nMitigating Factors:")
    for mitigant in verdict.mitigating_factors:
        print(f"  + {mitigant}")
    print(f"\nRecommendations:")
    for rec in verdict.recommendations:
        print(f"  > {rec}")

    # Export data
    exports = export_capacity_analysis()
    print(f"\nExported analysis to: {list(exports.values())[0].parent}")

    return verdict


if __name__ == '__main__':
    main()
