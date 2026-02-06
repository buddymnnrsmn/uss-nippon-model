#!/usr/bin/env python3
"""
USS-Nippon Steel: Stakeholder Analysis
======================================

Analyzes value creation for all stakeholder groups:
- USS Shareholders: Premium, certainty value, liquidity
- Nippon Shareholders: Accretion/dilution, IRR, strategic value
- Employees/USW: Jobs, investment, skills
- Bondholders: Credit implications
- Communities: Economic impact

Author: RAMBAS Team
Date: January 2025
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Add parent directory for model imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from price_volume_model import (
    PriceVolumeModel,
    ScenarioType,
    get_scenario_presets,
)


# =============================================================================
# CONSTANTS - STAKEHOLDER PARAMETERS
# =============================================================================

# USS Shareholders
USS_SHARES_OUTSTANDING = 271.0  # Million (diluted)
DEAL_PRICE_PER_SHARE = 55.00
USS_STANDALONE_VALUE = 50.14  # From DCF model
USS_PRE_ANNOUNCEMENT_PRICE = 33.00  # Before merger news (Aug 2023)

# Nippon Shareholders
NIPPON_SHARES_OUTSTANDING = 950.0  # Million
NIPPON_CURRENT_EPS_JPY = 654.0  # FY2024 (annualized)
NIPPON_SHARE_PRICE_JPY = 3_200  # Current price
FX_RATE_JPY_USD = 150.0

# Employee/USW
USS_EMPLOYEES = 22_053  # Total as of 2023
USS_HOURLY_EMPLOYEES = 11_700  # USW-represented
NSA_JOB_GUARANTEE_YEARS = 12  # Through 2035
NSA_CAPEX_COMMITMENT = 14_000  # $M

# Bondholders
USS_TOTAL_DEBT = 4_156  # $M
USS_DEBT_RATING_SP = "BB+"
USS_DEBT_RATING_MOODY = "Ba1"
NIPPON_DEBT_RATING_SP = "A-"
NIPPON_DEBT_RATING_MOODY = "A3"


# =============================================================================
# STAKEHOLDER DATACLASSES
# =============================================================================

@dataclass
class USSShareholderValue:
    """Value analysis for USS shareholders."""
    deal_price: float = DEAL_PRICE_PER_SHARE
    standalone_value: float = USS_STANDALONE_VALUE
    pre_announcement_price: float = USS_PRE_ANNOUNCEMENT_PRICE

    @property
    def premium_to_standalone(self) -> float:
        """Premium vs DCF standalone value."""
        return (self.deal_price - self.standalone_value) / self.standalone_value

    @property
    def premium_to_pre_announcement(self) -> float:
        """Premium vs pre-announcement trading price."""
        return (self.deal_price - self.pre_announcement_price) / self.pre_announcement_price

    @property
    def total_premium_value_M(self) -> float:
        """Total premium value in $M."""
        return (self.deal_price - self.standalone_value) * USS_SHARES_OUTSTANDING

    def certainty_value_analysis(self) -> Dict[str, float]:
        """
        Analyze certainty value - premium for eliminating execution risk.

        USS standalone faces risks:
        - Steel price volatility (±30-50% EBITDA swings)
        - Capex funding constraints
        - Pension obligations (~$4B underfunded)
        - Labor negotiations uncertainty
        """
        # Probability-weighted standalone scenarios
        scenarios = {
            'bull': {'probability': 0.25, 'value': 75.00},
            'base': {'probability': 0.50, 'value': 50.14},
            'bear': {'probability': 0.20, 'value': 25.00},
            'distress': {'probability': 0.05, 'value': 10.00},
        }

        expected_standalone = sum(
            s['probability'] * s['value']
            for s in scenarios.values()
        )

        # Certainty equivalent (assumes shareholders are risk-averse)
        variance = sum(
            s['probability'] * (s['value'] - expected_standalone) ** 2
            for s in scenarios.values()
        )
        risk_aversion_coefficient = 0.5
        certainty_equivalent = expected_standalone - risk_aversion_coefficient * variance / expected_standalone

        return {
            'expected_standalone': expected_standalone,
            'certainty_equivalent': certainty_equivalent,
            'deal_price': self.deal_price,
            'certainty_premium': self.deal_price - certainty_equivalent,
            'certainty_premium_pct': (self.deal_price - certainty_equivalent) / certainty_equivalent,
        }


@dataclass
class NipponShareholderValue:
    """Value analysis for Nippon Steel shareholders."""
    deal_equity_value_M: float = DEAL_PRICE_PER_SHARE * USS_SHARES_OUTSTANDING
    capex_commitment_M: float = NSA_CAPEX_COMMITMENT
    nippon_wacc: float = 0.075
    target_irr: float = 0.10

    @property
    def total_investment_M(self) -> float:
        """Total capital deployed."""
        return self.deal_equity_value_M + self.capex_commitment_M

    def accretion_analysis(self, synergy_run_rate_M: float = 450) -> Dict[str, float]:
        """
        Analyze EPS accretion/dilution for Nippon shareholders.

        Args:
            synergy_run_rate_M: Annual synergy EBITDA at full run-rate

        Returns:
            Dict with accretion metrics by year
        """
        # USS projected EBITDA (from model)
        uss_ebitda_y1 = 2_800  # $M Year 1
        uss_ebitda_y3 = 3_100  # $M Year 3
        uss_ebitda_y5 = 3_400  # $M Year 5

        # Synergy ramp (% of run-rate)
        synergy_ramp = {1: 0.20, 2: 0.45, 3: 0.70, 4: 0.90, 5: 1.00}

        # Interest cost on incremental debt
        incremental_debt = self.deal_equity_value_M * 0.5  # Assume 50% debt-funded
        interest_rate = 0.035  # 3.5% (Nippon's borrowing cost)
        interest_cost = incremental_debt * interest_rate

        # Depreciation from capex
        capex_annual = self.capex_commitment_M / 10
        depreciation = capex_annual * 0.10  # 10-year depreciation

        # Calculate by year
        results = {}
        for year in [1, 2, 3, 4, 5]:
            # USS EBITDA contribution
            if year == 1:
                uss_ebitda = uss_ebitda_y1
            elif year <= 3:
                uss_ebitda = uss_ebitda_y1 + (uss_ebitda_y3 - uss_ebitda_y1) * (year - 1) / 2
            else:
                uss_ebitda = uss_ebitda_y3 + (uss_ebitda_y5 - uss_ebitda_y3) * (year - 3) / 2

            # Synergies
            synergies = synergy_run_rate_M * synergy_ramp.get(year, 1.0)

            # EBIT
            uss_ebit = (uss_ebitda + synergies) * 0.85  # 85% EBITDA-to-EBIT

            # Pre-tax income
            pre_tax = uss_ebit - interest_cost - depreciation

            # After-tax (25% rate)
            net_income = pre_tax * 0.75

            # EPS contribution (in JPY)
            eps_contribution_usd = net_income / NIPPON_SHARES_OUTSTANDING * 1000  # Convert to per-share
            eps_contribution_jpy = eps_contribution_usd * FX_RATE_JPY_USD

            # Accretion vs dilution
            accretion_pct = eps_contribution_jpy / NIPPON_CURRENT_EPS_JPY

            results[year] = {
                'uss_ebitda_M': uss_ebitda,
                'synergies_M': synergies,
                'net_income_M': net_income,
                'eps_contribution_jpy': eps_contribution_jpy,
                'accretion_pct': accretion_pct,
                'accretive': accretion_pct > 0,
            }

        return results

    def irr_analysis(
        self,
        synergy_run_rate_M: float = 450,
        exit_multiple: float = 5.5,
        hold_years: int = 10,
    ) -> Dict[str, float]:
        """
        Calculate IRR on Nippon's investment.

        Unlike PE, Nippon:
        - Uses lower discount rate (7.5% vs 20%)
        - Has longer investment horizon (perpetual vs 5 years)
        - Values strategic benefits not in cash flows
        """
        # Initial investment
        initial = -self.total_investment_M

        # Annual cash flows (simplified)
        uss_fcf_base = 1_500  # $M Year 1 FCF
        fcf_growth = 0.03  # 3% annual growth

        # Synergy ramp
        synergy_ramp = {1: 0.20, 2: 0.45, 3: 0.70, 4: 0.90, 5: 1.00}

        cash_flows = [initial]
        for year in range(1, hold_years + 1):
            base_fcf = uss_fcf_base * ((1 + fcf_growth) ** (year - 1))
            synergy_fcf = synergy_run_rate_M * 0.6 * synergy_ramp.get(year, 1.0)  # 60% FCF conversion
            annual_cf = base_fcf + synergy_fcf
            cash_flows.append(annual_cf)

        # Terminal value
        terminal_ebitda = 3_500  # $M
        terminal_synergies = synergy_run_rate_M
        terminal_value = (terminal_ebitda + terminal_synergies) * exit_multiple
        cash_flows[-1] += terminal_value

        # Calculate IRR using scipy (np.irr deprecated)
        from scipy.optimize import brentq

        def npv_func(rate, cfs):
            return sum(cf / (1 + rate) ** i for i, cf in enumerate(cfs))

        try:
            irr = brentq(lambda r: npv_func(r, cash_flows), -0.99, 1.0)
        except ValueError:
            irr = 0.0  # Fallback if no root found

        # Calculate NPV at target return
        npv_at_target = npv_func(self.target_irr, cash_flows)

        return {
            'irr': irr,
            'irr_pct': irr * 100,
            'target_irr': self.target_irr,
            'exceeds_target': irr > self.target_irr,
            'npv_at_target_M': npv_at_target,
            'payback_years': self._calculate_payback(cash_flows),
        }

    def _calculate_payback(self, cash_flows: List[float]) -> float:
        """Calculate simple payback period."""
        cumulative = 0
        for i, cf in enumerate(cash_flows):
            cumulative += cf
            if cumulative >= 0:
                # Interpolate
                prev_cumulative = cumulative - cf
                return i - 1 + abs(prev_cumulative) / cf
        return len(cash_flows)


@dataclass
class EmployeeValue:
    """Value analysis for USS employees and USW."""
    total_employees: int = USS_EMPLOYEES
    hourly_employees: int = USS_HOURLY_EMPLOYEES
    job_guarantee_years: int = NSA_JOB_GUARANTEE_YEARS
    capex_commitment_M: float = NSA_CAPEX_COMMITMENT

    def job_security_analysis(self) -> Dict[str, any]:
        """Analyze job security provisions in NSA."""
        return {
            'total_jobs_protected': self.total_employees,
            'usw_jobs_protected': self.hourly_employees,
            'guarantee_period': f"Through 2035 ({self.job_guarantee_years} years)",
            'headquarters_commitment': "Pittsburgh headquarters maintained",
            'uss_name_preserved': True,
            'no_layoff_provision': True,
            'key_terms': [
                f"No layoffs or plant closures through 2035",
                f"Maintain USS as operating company name",
                f"Keep Pittsburgh as headquarters",
                f"Honor all existing USW contracts",
                f"No workforce reductions for synergies",
            ]
        }

    def investment_benefits(self) -> Dict[str, any]:
        """Analyze benefits from $14B capex commitment."""
        annual_capex = self.capex_commitment_M / 10

        return {
            'total_investment_M': self.capex_commitment_M,
            'annual_investment_M': annual_capex,
            'investment_per_employee': self.capex_commitment_M * 1_000_000 / self.total_employees,
            'key_projects': [
                "Mon Valley Works modernization",
                "Gary Works blast furnace upgrades",
                "Big River Steel expansion (Phase 2+)",
                "Decarbonization investments",
                "Advanced coating lines",
            ],
            'job_creation_potential': f"{int(annual_capex * 0.5)} construction jobs/year",
            'skill_development': [
                "Access to Nippon's technical training programs",
                "Advanced manufacturing skills",
                "Digital/automation expertise",
                "Japanese management techniques (kaizen, 5S)",
            ]
        }


@dataclass
class BondholderValue:
    """Value analysis for USS bondholders."""
    uss_debt_M: float = USS_TOTAL_DEBT
    uss_rating_sp: str = USS_DEBT_RATING_SP
    nippon_rating_sp: str = NIPPON_DEBT_RATING_SP

    def credit_impact_analysis(self) -> Dict[str, any]:
        """Analyze credit implications for USS bondholders."""
        return {
            'current_uss_rating': f"{self.uss_rating_sp} (S&P) / {USS_DEBT_RATING_MOODY} (Moody's)",
            'nippon_rating': f"{self.nippon_rating_sp} (S&P) / {NIPPON_DEBT_RATING_MOODY} (Moody's)",
            'rating_uplift_potential': "2-3 notches (to BBB+/Baa1)",
            'spread_compression': "50-100 bps potential tightening",
            'implicit_support': True,
            'analysis': {
                'positive_factors': [
                    "Implicit parent credit support from Nippon",
                    "Stronger combined balance sheet",
                    "Reduced standalone refinancing risk",
                    "Access to Japanese capital markets",
                    "Lower weighted-average cost of debt",
                ],
                'considerations': [
                    "Nippon leverage rises from 1.84x to ~2.5x",
                    "No explicit guarantee on existing USS bonds",
                    "Subordination risk if new debt raised",
                ],
            },
            'yield_impact': {
                'current_uss_spread': 275,  # bps over Treasury
                'expected_post_merger': 175,  # bps over Treasury
                'spread_tightening': 100,  # bps
            }
        }


@dataclass
class CommunityValue:
    """Value analysis for local communities."""
    capex_commitment_M: float = NSA_CAPEX_COMMITMENT
    major_facilities: List[str] = field(default_factory=lambda: [
        "Mon Valley Works (PA)",
        "Gary Works (IN)",
        "Granite City Works (IL)",
        "Fairfield Works (AL)",
        "Big River Steel (AR)",
        "Tubular Operations (TX, OH)",
    ])

    def economic_impact_analysis(self) -> Dict[str, any]:
        """Analyze economic impact on communities."""
        # Economic multiplier (steel industry typically 2.5-3.0x)
        multiplier = 2.7

        return {
            'direct_investment_M': self.capex_commitment_M,
            'total_economic_impact_M': self.capex_commitment_M * multiplier,
            'economic_multiplier': multiplier,
            'affected_communities': self.major_facilities,
            'tax_base_stability': True,
            'impacts_by_category': {
                'direct_employment': "22,000+ jobs preserved",
                'indirect_employment': "~60,000 supplier/service jobs supported",
                'induced_employment': "~40,000 jobs from worker spending",
                'tax_revenue': "Property, income, and sales tax stability",
                'supplier_base': "Thousands of domestic suppliers supported",
            },
            'long_term_commitments': [
                f"${self.capex_commitment_M:,}M investment over 10 years",
                "No plant closures through 2035",
                "Headquarters remains in Pittsburgh",
                "Commitment to domestic steel production",
                "Investment in decarbonization",
            ],
            'alternative_scenario': {
                'description': "Without deal, standalone USS would likely cut capex and workforce",
                'risk_factors': [
                    "Underfunded pension obligations (~$4B)",
                    "Aging integrated mills require investment",
                    "Competition from mini-mills",
                    "PE alternative would cut costs aggressively",
                ],
            }
        }


# =============================================================================
# STAKEHOLDER ANALYSIS CLASS
# =============================================================================

class StakeholderAnalysis:
    """
    Comprehensive stakeholder analysis for USS-Nippon merger.

    Analyzes value creation for all stakeholder groups.
    """

    def __init__(self, scenario_type: ScenarioType = ScenarioType.BASE_CASE):
        """Initialize stakeholder analysis."""
        self.scenario_type = scenario_type

        # Get model projections
        presets = get_scenario_presets()
        self.scenario = presets[scenario_type]
        self.model = PriceVolumeModel(self.scenario)
        self.analysis = self.model.run_full_analysis()

        # Initialize stakeholder analyses
        self.uss_shareholders = USSShareholderValue(
            standalone_value=self.analysis['val_uss']['share_price']
        )
        self.nippon_shareholders = NipponShareholderValue()
        self.employees = EmployeeValue()
        self.bondholders = BondholderValue()
        self.communities = CommunityValue()

    def get_uss_shareholder_summary(self) -> Dict:
        """Get USS shareholder value summary."""
        certainty = self.uss_shareholders.certainty_value_analysis()
        return {
            'deal_price': self.uss_shareholders.deal_price,
            'standalone_value': self.uss_shareholders.standalone_value,
            'premium_to_standalone': f"{self.uss_shareholders.premium_to_standalone:.1%}",
            'premium_to_pre_announcement': f"{self.uss_shareholders.premium_to_pre_announcement:.1%}",
            'total_premium_M': self.uss_shareholders.total_premium_value_M,
            'certainty_analysis': certainty,
        }

    def get_nippon_shareholder_summary(self, synergy_run_rate: float = 450) -> Dict:
        """Get Nippon shareholder value summary."""
        accretion = self.nippon_shareholders.accretion_analysis(synergy_run_rate)
        irr = self.nippon_shareholders.irr_analysis(synergy_run_rate)

        return {
            'total_investment_M': self.nippon_shareholders.total_investment_M,
            'accretion_year_1': f"{accretion[1]['accretion_pct']:.1%}",
            'accretion_year_3': f"{accretion[3]['accretion_pct']:.1%}",
            'accretion_year_5': f"{accretion[5]['accretion_pct']:.1%}",
            'breakeven_year': next(
                (y for y, data in accretion.items() if data['accretive']),
                "N/A"
            ),
            'irr': f"{irr['irr_pct']:.1f}%",
            'exceeds_target': irr['exceeds_target'],
        }

    def get_employee_summary(self) -> Dict:
        """Get employee value summary."""
        job_security = self.employees.job_security_analysis()
        investment = self.employees.investment_benefits()
        return {
            'job_security': job_security,
            'investment_benefits': investment,
        }

    def get_bondholder_summary(self) -> Dict:
        """Get bondholder value summary."""
        return self.bondholders.credit_impact_analysis()

    def get_community_summary(self) -> Dict:
        """Get community value summary."""
        return self.communities.economic_impact_analysis()

    def generate_stakeholder_matrix(self) -> pd.DataFrame:
        """
        Generate stakeholder value matrix.

        Returns:
            DataFrame with value creation by stakeholder
        """
        data = [
            {
                'Stakeholder': 'USS Shareholders',
                'Value_Driver': 'Acquisition Premium',
                'Quantified_Benefit': f"${DEAL_PRICE_PER_SHARE - USS_STANDALONE_VALUE:.2f}/share (+{(DEAL_PRICE_PER_SHARE/USS_STANDALONE_VALUE-1)*100:.0f}%)",
                'Certainty': 'High (cash at close)',
                'Timing': 'Immediate',
            },
            {
                'Stakeholder': 'USS Shareholders',
                'Value_Driver': 'Certainty Value',
                'Quantified_Benefit': 'Eliminates standalone execution risk',
                'Certainty': 'High',
                'Timing': 'Immediate',
            },
            {
                'Stakeholder': 'Nippon Shareholders',
                'Value_Driver': 'Strategic Access',
                'Quantified_Benefit': 'US market entry (largest steel market outside China)',
                'Certainty': 'High',
                'Timing': 'Immediate',
            },
            {
                'Stakeholder': 'Nippon Shareholders',
                'Value_Driver': 'EPS Accretion',
                'Quantified_Benefit': 'Accretive by Year 3-4',
                'Certainty': 'Medium',
                'Timing': '3-4 years',
            },
            {
                'Stakeholder': 'Nippon Shareholders',
                'Value_Driver': 'Synergy Value',
                'Quantified_Benefit': f'${450 * 10:.0f}M NPV',
                'Certainty': 'Medium',
                'Timing': '5-7 years',
            },
            {
                'Stakeholder': 'Employees/USW',
                'Value_Driver': 'Job Security',
                'Quantified_Benefit': '22,000+ jobs guaranteed through 2035',
                'Certainty': 'High (NSA terms)',
                'Timing': '12 years',
            },
            {
                'Stakeholder': 'Employees/USW',
                'Value_Driver': 'Investment',
                'Quantified_Benefit': f'${NSA_CAPEX_COMMITMENT/1000:.0f}B facility investment',
                'Certainty': 'High (NSA terms)',
                'Timing': '10 years',
            },
            {
                'Stakeholder': 'Bondholders',
                'Value_Driver': 'Credit Support',
                'Quantified_Benefit': 'Implicit IG parent backing',
                'Certainty': 'Medium-High',
                'Timing': 'Immediate',
            },
            {
                'Stakeholder': 'Communities',
                'Value_Driver': 'Economic Stability',
                'Quantified_Benefit': f'${NSA_CAPEX_COMMITMENT * 2.7 / 1000:.0f}B total economic impact',
                'Certainty': 'High',
                'Timing': '10 years',
            },
        ]

        return pd.DataFrame(data)

    def generate_summary_report(self) -> str:
        """Generate comprehensive stakeholder analysis report."""
        uss = self.get_uss_shareholder_summary()
        nippon = self.get_nippon_shareholder_summary()
        employee = self.get_employee_summary()
        bondholder = self.get_bondholder_summary()
        community = self.get_community_summary()

        report = f"""
{'='*80}
USS-NIPPON STEEL: STAKEHOLDER VALUE ANALYSIS
{'='*80}

1. USS SHAREHOLDERS
{'-'*80}
Deal Price:                 ${uss['deal_price']:.2f}/share
Standalone Value:           ${uss['standalone_value']:.2f}/share
Premium to Standalone:      {uss['premium_to_standalone']}
Premium to Pre-Announcement: {uss['premium_to_pre_announcement']}
Total Premium Value:        ${uss['total_premium_M']:,.0f}M

Certainty Analysis:
- Expected Standalone Value: ${uss['certainty_analysis']['expected_standalone']:.2f}
- Certainty Equivalent:      ${uss['certainty_analysis']['certainty_equivalent']:.2f}
- Certainty Premium:         ${uss['certainty_analysis']['certainty_premium']:.2f}/share

Key Benefits:
- Immediate cash liquidity vs uncertain 10-year DCF
- Eliminates steel price volatility risk
- Avoids pension funding challenges
- No labor negotiation risk

2. NIPPON SHAREHOLDERS
{'-'*80}
Total Investment:           ${nippon['total_investment_M']:,.0f}M
IRR:                        {nippon['irr']}
Exceeds 10% Target:         {'Yes' if nippon['exceeds_target'] else 'No'}

Accretion Schedule:
- Year 1: {nippon['accretion_year_1']}
- Year 3: {nippon['accretion_year_3']}
- Year 5: {nippon['accretion_year_5']}
- Breakeven Year: {nippon['breakeven_year']}

Strategic Benefits (not quantified in IRR):
- #2 global steel producer (with AM/China SOEs)
- US market access (Section 232 protected)
- Technology deployment platform
- Diversification from Japan/Asia

3. EMPLOYEES / USW
{'-'*80}
Jobs Protected:             {employee['job_security']['total_jobs_protected']:,}
USW Members Protected:      {employee['job_security']['usw_jobs_protected']:,}
Guarantee Period:           {employee['job_security']['guarantee_period']}

Key Commitments:
"""
        for term in employee['job_security']['key_terms']:
            report += f"- {term}\n"

        report += f"""
Investment Benefits:
- Total Investment: ${employee['investment_benefits']['total_investment_M']:,}M
- Investment per Employee: ${employee['investment_benefits']['investment_per_employee']:,.0f}

4. BONDHOLDERS
{'-'*80}
Current USS Rating:         {bondholder['current_uss_rating']}
Nippon Rating:              {bondholder['nippon_rating']}
Rating Uplift Potential:    {bondholder['rating_uplift_potential']}

Spread Impact:
- Current USS Spread: {bondholder['yield_impact']['current_uss_spread']} bps
- Expected Post-Merger: {bondholder['yield_impact']['expected_post_merger']} bps
- Spread Tightening: {bondholder['yield_impact']['spread_tightening']} bps

5. COMMUNITIES
{'-'*80}
Direct Investment:          ${community['direct_investment_M']:,}M
Total Economic Impact:      ${community['total_economic_impact_M']:,.0f}M
Economic Multiplier:        {community['economic_multiplier']}x

Affected Facilities:
"""
        for facility in community['affected_communities']:
            report += f"- {facility}\n"

        report += f"""
Employment Impact:
- Direct: {community['impacts_by_category']['direct_employment']}
- Indirect: {community['impacts_by_category']['indirect_employment']}
- Induced: {community['impacts_by_category']['induced_employment']}

{'='*80}
STAKEHOLDER VALUE MATRIX
{'='*80}
"""
        matrix = self.generate_stakeholder_matrix()
        report += matrix.to_string(index=False)

        report += f"""

{'='*80}
CONCLUSION: Deal creates value across ALL stakeholder groups
{'='*80}
"""
        return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run stakeholder analysis and print summary."""
    print("\nInitializing Stakeholder Analysis...")

    analysis = StakeholderAnalysis(ScenarioType.BASE_CASE)

    # Print summary report
    print(analysis.generate_summary_report())

    return analysis


if __name__ == "__main__":
    analysis = main()
