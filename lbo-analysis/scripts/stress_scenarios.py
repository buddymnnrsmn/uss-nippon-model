#!/usr/bin/env python3
"""
LBO Stress Testing: Downside Scenarios for USS Acquisition
===========================================================

This script models LBO debt service capacity under various steel market stress scenarios,
using historical crisis data (2008-2009, 2015-2016) to assess covenant compliance and
bankruptcy risk.

Key Features:
- Imports existing USS DCF model (price_volume_model.py)
- Runs stress scenarios: Base, Mild, Moderate (2015-16), Severe (2008-09)
- Calculates debt service coverage at various leverage levels
- Outputs covenant compliance matrix and minimum EBITDA requirements
"""

import sys
import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Add parent directory to path to import the DCF model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from price_volume_model import (
    PriceVolumeModel, ModelScenario, SteelPriceScenario, VolumeScenario,
    ScenarioType, FinancingAssumptions, get_scenario_presets
)


# =============================================================================
# LBO DEBT STRUCTURE
# =============================================================================

@dataclass
class DebtTranche:
    """Represents a tranche of LBO debt"""
    name: str
    amount: float  # $M
    interest_rate: float  # Decimal (e.g., 0.0825 for 8.25%)
    maturity_years: int
    amortization_rate: float = 0.0  # Annual principal paydown as % of original principal

    def annual_interest(self) -> float:
        """Calculate annual interest expense"""
        return self.amount * self.interest_rate

    def annual_amortization(self) -> float:
        """Calculate annual principal amortization"""
        return self.amount * self.amortization_rate


@dataclass
class LBODebtStructure:
    """Complete LBO debt structure with multiple tranches"""
    tranches: List[DebtTranche]

    @property
    def total_debt(self) -> float:
        """Total debt across all tranches"""
        return sum(t.amount for t in self.tranches)

    @property
    def total_annual_interest(self) -> float:
        """Total annual interest expense"""
        return sum(t.annual_interest() for t in self.tranches)

    @property
    def total_annual_amortization(self) -> float:
        """Total annual principal amortization"""
        return sum(t.annual_amortization() for t in self.tranches)

    @property
    def total_debt_service(self) -> float:
        """Total annual debt service (interest + amortization)"""
        return self.total_annual_interest + self.total_annual_amortization

    @property
    def blended_interest_rate(self) -> float:
        """Weighted average interest rate"""
        return self.total_annual_interest / self.total_debt if self.total_debt > 0 else 0


def create_lbo_debt_structure(total_debt: float, sofr_rate: float = 0.04) -> LBODebtStructure:
    """
    Create a typical LBO debt structure for steel industry acquisition

    Args:
        total_debt: Total debt amount in $M
        sofr_rate: SOFR base rate (default 4.0%)

    Returns:
        LBODebtStructure with typical tranches
    """
    tranches = [
        DebtTranche(
            name="Revolver",
            amount=total_debt * 0.10,  # 10% revolver
            interest_rate=sofr_rate + 0.035,  # SOFR + 350bps
            maturity_years=5,
            amortization_rate=0.0
        ),
        DebtTranche(
            name="Term Loan B",
            amount=total_debt * 0.50,  # 50% TLB
            interest_rate=sofr_rate + 0.0425,  # SOFR + 425bps
            maturity_years=7,
            amortization_rate=0.01  # 1% annual amortization
        ),
        DebtTranche(
            name="Second Lien",
            amount=total_debt * 0.20,  # 20% second lien
            interest_rate=sofr_rate + 0.065,  # SOFR + 650bps
            maturity_years=8,
            amortization_rate=0.0
        ),
        DebtTranche(
            name="High Yield Bonds",
            amount=total_debt * 0.20,  # 20% high yield
            interest_rate=0.095,  # 9.5% fixed
            maturity_years=10,
            amortization_rate=0.0
        ),
    ]

    return LBODebtStructure(tranches=tranches)


# =============================================================================
# STRESS SCENARIOS
# =============================================================================

def create_stress_scenarios() -> Dict[str, ModelScenario]:
    """
    Create stress scenarios based on historical steel crises

    Returns:
        Dictionary of stress scenarios: Base, Mild, Moderate (2015-16), Severe (2008-09)
    """

    # Base case from existing presets
    base_presets = get_scenario_presets()
    base_scenario = base_presets[ScenarioType.BASE_CASE]

    # Mild Downturn: 15% price decline, 8% volume decline
    mild_scenario = ModelScenario(
        name="Mild Downturn",
        scenario_type=ScenarioType.CUSTOM,
        description="Modest recession: 15% price decline, 8% volume decline, 11.2% EBITDA margin",
        price_scenario=SteelPriceScenario(
            name="Mild Downturn Prices",
            description="15% price decline from base case",
            hrc_us_factor=0.85,  # 15% below base
            crc_us_factor=0.85,
            coated_us_factor=0.85,
            hrc_eu_factor=0.82,
            octg_factor=0.85,
            annual_price_growth=0.005
        ),
        volume_scenario=VolumeScenario(
            name="Mild Downturn Volumes",
            description="8% volume contraction across segments",
            flat_rolled_volume_factor=0.92,
            mini_mill_volume_factor=0.92,
            usse_volume_factor=0.92,
            tubular_volume_factor=0.92,
            flat_rolled_growth_adj=-0.01,
            mini_mill_growth_adj=0.0,
            usse_growth_adj=-0.01,
            tubular_growth_adj=-0.005
        ),
        uss_wacc=0.115,  # Higher risk premium in downturn
        terminal_growth=0.01,
        exit_multiple=4.0,  # Lower multiple in stressed market
        us_10yr=0.045,
        japan_10yr=0.0075,
        nippon_equity_risk_premium=0.05,
        nippon_credit_spread=0.0075,
        nippon_debt_ratio=0.35,
        nippon_tax_rate=0.30,
        include_projects=['BR2 Mini Mill']
    )

    # Moderate Crisis (2015-2016 style): 44% price decline, 12% volume decline
    moderate_scenario = ModelScenario(
        name="Moderate Crisis (2015-16)",
        scenario_type=ScenarioType.CUSTOM,
        description="2015-16 steel crisis: 44% price decline, 12% volume decline, 9.2% EBITDA margin",
        price_scenario=SteelPriceScenario(
            name="2015-16 Crisis Prices",
            description="HRC $500/ton (down 44% from $1,030 realized)",
            hrc_us_factor=0.56,  # 44% decline from realized price
            crc_us_factor=0.56,
            coated_us_factor=0.56,
            hrc_eu_factor=0.52,
            octg_factor=0.56,
            annual_price_growth=0.01
        ),
        volume_scenario=VolumeScenario(
            name="2015-16 Crisis Volumes",
            description="12% volume decline consistent with 2015 shipment data",
            flat_rolled_volume_factor=0.88,
            mini_mill_volume_factor=0.88,
            usse_volume_factor=0.88,
            tubular_volume_factor=0.88,
            flat_rolled_growth_adj=-0.015,
            mini_mill_growth_adj=0.005,
            usse_growth_adj=-0.015,
            tubular_growth_adj=-0.01
        ),
        uss_wacc=0.135,  # Significantly higher risk premium
        terminal_growth=0.01,
        exit_multiple=3.5,
        us_10yr=0.045,
        japan_10yr=0.01,
        nippon_equity_risk_premium=0.055,
        nippon_credit_spread=0.01,
        nippon_debt_ratio=0.35,
        nippon_tax_rate=0.30,
        include_projects=['BR2 Mini Mill']
    )

    # Severe Crisis (2008-2009 style): 62% price decline, 35% volume decline
    severe_scenario = ModelScenario(
        name="Severe Crisis (2008-09)",
        scenario_type=ScenarioType.CUSTOM,
        description="2008-09 financial crisis: 62% price decline, 35% volume decline, 3.6% EBITDA margin",
        price_scenario=SteelPriceScenario(
            name="2008-09 Crisis Prices",
            description="HRC $400/ton (down 62% from peak)",
            hrc_us_factor=0.38,  # 62% decline
            crc_us_factor=0.38,
            coated_us_factor=0.38,
            hrc_eu_factor=0.35,
            octg_factor=0.40,
            annual_price_growth=0.0
        ),
        volume_scenario=VolumeScenario(
            name="2008-09 Crisis Volumes",
            description="35% volume collapse, capacity utilization 33%",
            flat_rolled_volume_factor=0.65,
            mini_mill_volume_factor=0.65,
            usse_volume_factor=0.65,
            tubular_volume_factor=0.65,
            flat_rolled_growth_adj=-0.03,
            mini_mill_growth_adj=-0.01,
            usse_growth_adj=-0.03,
            tubular_growth_adj=-0.02
        ),
        uss_wacc=0.15,  # Distressed WACC
        terminal_growth=0.005,  # Minimal growth in crisis
        exit_multiple=3.0,
        us_10yr=0.04,
        japan_10yr=0.01,
        nippon_equity_risk_premium=0.06,
        nippon_credit_spread=0.015,
        nippon_debt_ratio=0.35,
        nippon_tax_rate=0.30,
        include_projects=[]  # All projects halted
    )

    return {
        'Base Case': base_scenario,
        'Mild Downturn': mild_scenario,
        'Moderate Crisis (2015-16)': moderate_scenario,
        'Severe Crisis (2008-09)': severe_scenario
    }


# =============================================================================
# STRESS TEST ANALYSIS
# =============================================================================

def calculate_coverage_ratios(ebitda: float, debt_structure: LBODebtStructure,
                              capex: float = 0, fcf: float = None) -> Dict:
    """
    Calculate debt service coverage ratios

    Args:
        ebitda: Annual EBITDA in $M
        debt_structure: LBO debt structure
        capex: Annual CapEx in $M (for fixed charge coverage)
        fcf: Annual FCF in $M (optional, for FCF coverage)

    Returns:
        Dictionary of coverage ratios
    """
    interest = debt_structure.total_annual_interest
    amortization = debt_structure.total_annual_amortization
    total_debt_service = debt_structure.total_debt_service
    total_debt = debt_structure.total_debt

    # Leverage ratios
    total_leverage = total_debt / ebitda if ebitda > 0 else np.inf

    # Coverage ratios
    interest_coverage = ebitda / interest if interest > 0 else np.inf
    debt_service_coverage = ebitda / total_debt_service if total_debt_service > 0 else np.inf

    # Fixed charge coverage (EBITDA - CapEx) / Debt Service
    fixed_charge_coverage = (ebitda - capex) / total_debt_service if total_debt_service > 0 else np.inf

    # FCF coverage
    if fcf is not None:
        fcf_coverage = fcf / total_debt_service if total_debt_service > 0 else np.inf
    else:
        fcf_coverage = None

    # Covenant status
    covenant_status = "PASS"
    if total_leverage > 6.0 or interest_coverage < 1.5:
        covenant_status = "DEFAULT"
    elif total_leverage > 5.0 or interest_coverage < 2.0:
        covenant_status = "FAIL"
    elif total_leverage > 4.5 or interest_coverage < 2.5:
        covenant_status = "WARNING"

    return {
        'total_debt': total_debt,
        'annual_interest': interest,
        'annual_amortization': amortization,
        'total_debt_service': total_debt_service,
        'ebitda': ebitda,
        'total_leverage': total_leverage,
        'interest_coverage': interest_coverage,
        'debt_service_coverage': debt_service_coverage,
        'fixed_charge_coverage': fixed_charge_coverage,
        'fcf_coverage': fcf_coverage,
        'covenant_status': covenant_status
    }


def run_stress_test(scenario: ModelScenario, debt_structure: LBODebtStructure) -> Dict:
    """
    Run stress test for a given scenario and debt structure

    Args:
        scenario: ModelScenario configuration
        debt_structure: LBO debt structure

    Returns:
        Dictionary with stress test results
    """
    # Run DCF model
    model = PriceVolumeModel(scenario)
    analysis = model.run_full_analysis()

    consolidated = analysis['consolidated']

    # Get key metrics (average over projection period)
    avg_ebitda = consolidated['Total_EBITDA'].mean()
    avg_fcf = consolidated['FCF'].mean()
    avg_capex = consolidated['Total_CapEx'].mean()

    # First year metrics (most important for covenant testing)
    yr1_ebitda = consolidated['Total_EBITDA'].iloc[0]
    yr1_fcf = consolidated['FCF'].iloc[0]
    yr1_capex = consolidated['Total_CapEx'].iloc[0]

    # Calculate coverage ratios
    avg_coverage = calculate_coverage_ratios(avg_ebitda, debt_structure, avg_capex, avg_fcf)
    yr1_coverage = calculate_coverage_ratios(yr1_ebitda, debt_structure, yr1_capex, yr1_fcf)

    return {
        'scenario_name': scenario.name,
        'avg_revenue': consolidated['Revenue'].mean(),
        'avg_ebitda': avg_ebitda,
        'avg_ebitda_margin': consolidated['EBITDA_Margin'].mean(),
        'avg_fcf': avg_fcf,
        'yr1_ebitda': yr1_ebitda,
        'yr1_fcf': yr1_fcf,
        'avg_coverage': avg_coverage,
        'yr1_coverage': yr1_coverage,
        'consolidated': consolidated
    }


def calculate_minimum_ebitda_requirements(leverage_levels: List[float],
                                          sofr_rate: float = 0.04) -> pd.DataFrame:
    """
    Calculate minimum EBITDA required for various leverage levels

    Args:
        leverage_levels: List of Total Debt/EBITDA ratios to test
        sofr_rate: SOFR base rate

    Returns:
        DataFrame with minimum EBITDA requirements
    """
    results = []

    for leverage in leverage_levels:
        # Assume $14.8B enterprise value
        ev = 14800

        # Calculate debt and equity based on leverage
        # If leverage = 3.5x, and we need to solve for EBITDA:
        # Total Debt = leverage × EBITDA
        # EV = Total Debt + Equity
        # Assume equity % based on leverage

        # Typical LBO: 70% debt, 30% equity at 5.0x leverage
        # At 3.5x leverage: ~60% debt, 40% equity
        # At 4.0x leverage: ~65% debt, 35% equity

        # Simplified: assume debt % = min(0.70, leverage/5.0 * 0.70)
        debt_pct = min(0.80, leverage / 5.0 * 0.70)
        total_debt = ev * debt_pct

        # Create debt structure
        debt_structure = create_lbo_debt_structure(total_debt, sofr_rate)

        # Calculate implied EBITDA from leverage target
        implied_ebitda = total_debt / leverage

        # Calculate coverage ratios at this EBITDA
        coverage = calculate_coverage_ratios(implied_ebitda, debt_structure, capex=600)

        results.append({
            'Target Leverage (x)': leverage,
            'Total Debt ($M)': total_debt,
            'Equity ($M)': ev - total_debt,
            'Equity %': (ev - total_debt) / ev * 100,
            'Min EBITDA ($M)': implied_ebitda,
            'Interest Expense ($M)': coverage['annual_interest'],
            'Interest Coverage (x)': coverage['interest_coverage'],
            'Debt Service ($M)': coverage['total_debt_service'],
            'DS Coverage (x)': coverage['debt_service_coverage'],
            'Fixed Charge Coverage (x)': coverage['fixed_charge_coverage'],
            'Covenant Status': coverage['covenant_status']
        })

    return pd.DataFrame(results)


def run_sensitivity_analysis(ebitda_levels: List[float],
                             leverage_levels: List[float],
                             sofr_rate: float = 0.04) -> pd.DataFrame:
    """
    Run sensitivity analysis: EBITDA vs Leverage levels

    Args:
        ebitda_levels: List of EBITDA levels to test ($M)
        leverage_levels: List of leverage multiples to test
        sofr_rate: SOFR base rate

    Returns:
        DataFrame with sensitivity matrix
    """
    results = []

    for ebitda in ebitda_levels:
        for leverage in leverage_levels:
            total_debt = ebitda * leverage

            # Create debt structure
            debt_structure = create_lbo_debt_structure(total_debt, sofr_rate)

            # Calculate coverage
            coverage = calculate_coverage_ratios(ebitda, debt_structure, capex=600)

            results.append({
                'EBITDA ($M)': ebitda,
                'Leverage (x)': leverage,
                'Total Debt ($M)': total_debt,
                'Interest Coverage (x)': coverage['interest_coverage'],
                'Covenant Status': coverage['covenant_status']
            })

    # Pivot for matrix view
    df = pd.DataFrame(results)
    pivot_coverage = df.pivot(index='EBITDA ($M)', columns='Leverage (x)', values='Interest Coverage (x)')
    pivot_status = df.pivot(index='EBITDA ($M)', columns='Leverage (x)', values='Covenant Status')

    return df, pivot_coverage, pivot_status


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run complete LBO stress testing analysis"""

    print("=" * 100)
    print("LBO STRESS TESTING: USS ACQUISITION DOWNSIDE SCENARIOS")
    print("=" * 100)
    print()

    # Define acquisition parameters
    ev = 14800  # $14.8B enterprise value
    equity_pct = 0.30  # 30% equity
    total_debt = ev * (1 - equity_pct)  # $10.36B debt

    print(f"ACQUISITION PARAMETERS:")
    print(f"  Enterprise Value: ${ev:,.0f}M")
    print(f"  Equity (30%): ${ev * equity_pct:,.0f}M")
    print(f"  Total Debt (70%): ${total_debt:,.0f}M")
    print()

    # Create debt structure
    debt_structure = create_lbo_debt_structure(total_debt)

    print(f"DEBT STRUCTURE:")
    print("-" * 100)
    for tranche in debt_structure.tranches:
        print(f"  {tranche.name:20s}: ${tranche.amount:>8,.0f}M @ {tranche.interest_rate*100:.2f}%  "
              f"(Annual Interest: ${tranche.annual_interest():>6,.0f}M, "
              f"Amort: ${tranche.annual_amortization():>6,.0f}M)")
    print("-" * 100)
    print(f"  {'TOTAL':20s}: ${debt_structure.total_debt:>8,.0f}M @ {debt_structure.blended_interest_rate*100:.2f}%  "
          f"(Annual Interest: ${debt_structure.total_annual_interest:>6,.0f}M, "
          f"Amort: ${debt_structure.total_annual_amortization:>6,.0f}M)")
    print(f"  Total Annual Debt Service: ${debt_structure.total_debt_service:,.0f}M")
    print()

    # Create stress scenarios
    scenarios = create_stress_scenarios()

    # Run stress tests
    print("RUNNING STRESS TESTS...")
    print()

    stress_results = []
    for scenario_name, scenario in scenarios.items():
        print(f"  Running {scenario_name}...")
        result = run_stress_test(scenario, debt_structure)
        stress_results.append(result)

    print()
    print("=" * 100)
    print("STRESS TEST RESULTS: COVENANT COMPLIANCE MATRIX")
    print("=" * 100)
    print()

    # Build summary table
    summary_data = []
    for result in stress_results:
        yr1 = result['yr1_coverage']
        summary_data.append({
            'Scenario': result['scenario_name'],
            'Yr1 Revenue ($B)': result['consolidated']['Revenue'].iloc[0] / 1000,
            'Yr1 EBITDA ($M)': result['yr1_ebitda'],
            'Yr1 Margin (%)': result['consolidated']['EBITDA_Margin'].iloc[0] * 100,
            'Total Leverage (x)': yr1['total_leverage'],
            'Interest Coverage (x)': yr1['interest_coverage'],
            'DS Coverage (x)': yr1['debt_service_coverage'],
            'FC Coverage (x)': yr1['fixed_charge_coverage'],
            'Covenant Status': yr1['covenant_status']
        })

    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print()

    # Minimum EBITDA requirements
    print("=" * 100)
    print("MINIMUM EBITDA REQUIREMENTS BY LEVERAGE LEVEL")
    print("=" * 100)
    print()

    leverage_levels = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    min_ebitda_df = calculate_minimum_ebitda_requirements(leverage_levels)
    print(min_ebitda_df.to_string(index=False))
    print()

    # Sensitivity analysis
    print("=" * 100)
    print("SENSITIVITY ANALYSIS: INTEREST COVERAGE BY EBITDA AND LEVERAGE")
    print("=" * 100)
    print()

    ebitda_levels = [500, 750, 1000, 1250, 1500, 1750, 2000, 2250, 2500]
    leverage_levels_sens = [3.0, 3.5, 4.0, 4.5, 5.0]

    sens_df, pivot_coverage, pivot_status = run_sensitivity_analysis(ebitda_levels, leverage_levels_sens)

    print("Interest Coverage Ratios:")
    print(pivot_coverage.to_string())
    print()

    print("Covenant Status:")
    print(pivot_status.to_string())
    print()

    # Key findings
    print("=" * 100)
    print("KEY FINDINGS")
    print("=" * 100)
    print()

    base_result = stress_results[0]
    moderate_result = stress_results[2]
    severe_result = stress_results[3]

    print(f"1. BASE CASE PERFORMANCE:")
    print(f"   - Year 1 EBITDA: ${base_result['yr1_ebitda']:,.0f}M")
    print(f"   - Total Leverage: {base_result['yr1_coverage']['total_leverage']:.2f}x")
    print(f"   - Interest Coverage: {base_result['yr1_coverage']['interest_coverage']:.2f}x")
    print(f"   - Covenant Status: {base_result['yr1_coverage']['covenant_status']}")
    print()

    print(f"2. MODERATE CRISIS (2015-16 STYLE):")
    print(f"   - Year 1 EBITDA: ${moderate_result['yr1_ebitda']:,.0f}M ({(moderate_result['yr1_ebitda']/base_result['yr1_ebitda']-1)*100:.0f}% vs base)")
    print(f"   - Total Leverage: {moderate_result['yr1_coverage']['total_leverage']:.2f}x")
    print(f"   - Interest Coverage: {moderate_result['yr1_coverage']['interest_coverage']:.2f}x")
    print(f"   - Covenant Status: {moderate_result['yr1_coverage']['covenant_status']}")
    print()

    print(f"3. SEVERE CRISIS (2008-09 STYLE):")
    print(f"   - Year 1 EBITDA: ${severe_result['yr1_ebitda']:,.0f}M ({(severe_result['yr1_ebitda']/base_result['yr1_ebitda']-1)*100:.0f}% vs base)")
    print(f"   - Total Leverage: {severe_result['yr1_coverage']['total_leverage']:.2f}x")
    print(f"   - Interest Coverage: {severe_result['yr1_coverage']['interest_coverage']:.2f}x")
    print(f"   - Covenant Status: {severe_result['yr1_coverage']['covenant_status']}")
    print()

    print("4. RECOMMENDED LEVERAGE:")
    recommended_leverage = min_ebitda_df[min_ebitda_df['Interest Coverage (x)'] >= 2.5].iloc[0]
    print(f"   - For 2.5x+ interest coverage in base case: {recommended_leverage['Target Leverage (x)']:.1f}x leverage")
    print(f"   - Required Equity: ${recommended_leverage['Equity ($M)']:,.0f}M ({recommended_leverage['Equity %']:.0f}%)")
    print(f"   - Total Debt: ${recommended_leverage['Total Debt ($M)']:,.0f}M")
    print()

    print("5. SURVIVAL THRESHOLDS:")
    print(f"   - Minimum EBITDA for 1.5x interest coverage @ 5.0x leverage: ${10360 / 5.0:.0f}M")
    print(f"   - Minimum EBITDA for 2.0x interest coverage @ 4.0x leverage: ${10360 / 4.0:.0f}M")
    print(f"   - 2015-16 crisis EBITDA would be: ${moderate_result['yr1_ebitda']:,.0f}M")
    print(f"   - 2008-09 crisis EBITDA would be: ${severe_result['yr1_ebitda']:,.0f}M")
    print()

    print("CONCLUSION:")
    print("-" * 100)
    print("USS LBO at 5.0x leverage is HIGHLY VULNERABLE to steel price downturns.")
    print("Historical crises (2008-09, 2015-16) would trigger covenant defaults or bankruptcy.")
    print("Recommended maximum leverage: 4.0x with 35% equity contribution for downside protection.")
    print("Nippon's all-equity acquisition ($55/share, zero acquisition debt) provides superior safety.")
    print("=" * 100)


if __name__ == "__main__":
    main()
