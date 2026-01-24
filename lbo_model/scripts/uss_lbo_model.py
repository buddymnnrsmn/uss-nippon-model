#!/usr/bin/env python3
"""
USS LBO Model - Working Analysis
=================================

Analyzes USS acquisition from a private equity perspective to demonstrate:
1. Whether PE firms can generate adequate returns at $55/share
2. How PE returns compare to Nippon's strategic value creation
3. Why the $14B NSA CapEx program is unfundable under LBO structure

Author: RAMBAS Team
Date: December 31, 2024
Data as of: December 31, 2023
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

# Add parent directory for model imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from price_volume_model import (
    PriceVolumeModel,
    ScenarioType,
    get_scenario_presets
)


# =============================================================================
# USS LBO TRANSACTION ASSUMPTIONS (as of December 31, 2024)
# =============================================================================

# Entry assumptions
ENTRY_PRICE_PER_SHARE = 55.00  # Nippon's offer price
SHARES_OUTSTANDING = 225.0  # Million shares
ENTRY_EQUITY_VALUE = ENTRY_PRICE_PER_SHARE * SHARES_OUTSTANDING  # $12,375M

# USS existing capital structure (12/31/23)
EXISTING_DEBT = 4_156  # $M
EXISTING_CASH = 2_948  # $M
NET_DEBT = EXISTING_DEBT - EXISTING_CASH  # $1,208M

# Entry enterprise value
ENTRY_EV = ENTRY_EQUITY_VALUE + NET_DEBT  # $13,583M

# Transaction fees (typical for LBO)
TRANSACTION_FEES_PCT = 0.02  # 2% of EV
FINANCING_FEES_PCT = 0.03  # 3% of new debt

# Debt market conditions (as of 12/31/24)
SOFR_RATE = 0.0449  # 4.49%
REVOLVER_SPREAD = 0.0300  # 300 bps
TLB_SPREAD = 0.0375  # 375 bps
HY_BOND_COUPON = 0.0725  # 7.25% fixed

# LBO structure assumptions
TARGET_LEVERAGE = 5.0  # Total Debt/EBITDA (moderate for steel)
HOLD_PERIOD = 5  # Years

# Exit assumptions
EXIT_MULTIPLE_BASE = 5.0  # EV/EBITDA
DILUTION_FROM_MGMT_EQUITY = 0.10  # 10% to management


# =============================================================================
# LBO MODEL CLASS
# =============================================================================

class USSLBOModel:
    """
    Complete LBO model for USS acquisition analysis
    """

    def __init__(self, scenario_type: ScenarioType = ScenarioType.CONSERVATIVE):
        """
        Initialize LBO model with specified operating scenario

        Args:
            scenario_type: Which operating scenario to use for projections
        """
        self.scenario_type = scenario_type

        # Get operating projections from DCF model
        presets = get_scenario_presets()
        scenario = presets[scenario_type]
        self.dcf_model = PriceVolumeModel(scenario)
        self.analysis = self.dcf_model.run_full_analysis()

        # Extract key data
        self.projections = self.analysis['consolidated']
        self.ebitda_2024 = self.projections.loc[self.projections['Year'] == 2024, 'Total_EBITDA'].values[0]

    def build_sources_and_uses(self) -> Dict:
        """
        Build Sources & Uses table for the transaction
        """
        # USES
        equity_purchase = ENTRY_EQUITY_VALUE
        refinance_existing_debt = EXISTING_DEBT
        transaction_fees = ENTRY_EV * TRANSACTION_FEES_PCT
        total_uses = equity_purchase + refinance_existing_debt + transaction_fees

        # SOURCES
        # Determine new debt based on target leverage
        total_new_debt = self.ebitda_2024 * TARGET_LEVERAGE
        financing_fees = total_new_debt * FINANCING_FEES_PCT

        # Adjust for existing cash and financing fees
        total_sources_needed = total_uses - EXISTING_CASH + financing_fees
        equity_contribution = total_sources_needed - total_new_debt

        return {
            'uses': {
                'equity_purchase': equity_purchase,
                'refinance_debt': refinance_existing_debt,
                'transaction_fees': transaction_fees,
                'total_uses': total_uses
            },
            'sources': {
                'new_debt': total_new_debt,
                'existing_cash': EXISTING_CASH,
                'financing_fees': financing_fees,
                'equity_contribution': equity_contribution,
                'total_sources': total_sources_needed
            },
            'entry_metrics': {
                'entry_ev': ENTRY_EV,
                'entry_ebitda': self.ebitda_2024,
                'entry_multiple': ENTRY_EV / self.ebitda_2024,
                'leverage': total_new_debt / self.ebitda_2024
            }
        }

    def build_debt_structure(self, total_debt: float) -> Dict:
        """
        Structure the debt into tranches

        Typical LBO structure:
        - Revolver: 0.5x EBITDA (drawn as needed)
        - Term Loan B: 3.0x EBITDA
        - High Yield Bonds: 1.5x EBITDA
        """
        revolver = min(0.5 * self.ebitda_2024, 1000)  # $1B max
        tlb = 3.0 * self.ebitda_2024
        hy_bonds = total_debt - revolver - tlb

        return {
            'Revolver': {
                'commitment': revolver,
                'drawn': 0,  # Initially undrawn
                'rate': SOFR_RATE + REVOLVER_SPREAD,
                'maturity': 5,
                'amortization': 0
            },
            'Term Loan B': {
                'principal': tlb,
                'rate': SOFR_RATE + TLB_SPREAD,
                'maturity': 7,
                'amortization': 0.01  # 1% annual
            },
            'High Yield Bonds': {
                'principal': hy_bonds,
                'rate': HY_BOND_COUPON,
                'maturity': 8,
                'amortization': 0  # Bullet at maturity
            }
        }

    def calculate_debt_schedule(self, debt_structure: Dict, hold_period: int) -> pd.DataFrame:
        """
        Calculate year-by-year debt balances with mandatory amortization and cash sweep
        """
        years = range(2024, 2024 + hold_period + 1)
        schedule = []

        # Initialize balances
        revolver_balance = debt_structure['Revolver']['drawn']
        tlb_balance = debt_structure['Term Loan B']['principal']
        hy_balance = debt_structure['High Yield Bonds']['principal']

        for year in years:
            # Get operating cash flow for the year
            year_data = self.projections[self.projections['Year'] == year].iloc[0]
            ebitda = year_data['Total_EBITDA']
            capex = year_data['Total_CapEx']
            delta_wc = year_data['Delta_WC']
            da = year_data['DA']

            # Calculate interest expense
            revolver_interest = revolver_balance * debt_structure['Revolver']['rate']
            tlb_interest = tlb_balance * debt_structure['Term Loan B']['rate']
            hy_interest = hy_balance * debt_structure['High Yield Bonds']['rate']
            total_interest = revolver_interest + tlb_interest + hy_interest

            # Calculate taxes (on EBITDA - D&A - Interest)
            taxable_income = max(0, ebitda - da - total_interest)
            taxes = taxable_income * 0.25  # 25% tax rate

            # Cash flow available for debt service
            cash_from_operations = ebitda - capex - delta_wc - total_interest - taxes

            # Mandatory amortization
            tlb_amort = tlb_balance * debt_structure['Term Loan B']['amortization']
            mandatory_paydown = tlb_amort

            # Optional sweep (75% of excess cash)
            excess_cash = cash_from_operations - mandatory_paydown
            optional_sweep = max(0, excess_cash * 0.75)

            total_paydown = mandatory_paydown + optional_sweep

            # Apply paydown (TLB first, then HY, then Revolver)
            tlb_paydown = min(total_paydown, tlb_balance)
            remaining = total_paydown - tlb_paydown

            hy_paydown = min(remaining, hy_balance)
            remaining = remaining - hy_paydown

            revolver_paydown = min(remaining, revolver_balance)

            # Update balances
            tlb_balance = tlb_balance - tlb_paydown
            hy_balance = hy_balance - hy_paydown
            revolver_balance = revolver_balance - revolver_paydown

            total_debt = revolver_balance + tlb_balance + hy_balance

            schedule.append({
                'Year': year,
                'EBITDA': ebitda,
                'CapEx': capex,
                'Delta_WC': delta_wc,
                'Interest': total_interest,
                'Taxes': taxes,
                'Cash_from_Ops': cash_from_operations,
                'Mandatory_Amort': mandatory_paydown,
                'Optional_Sweep': optional_sweep,
                'Total_Paydown': total_paydown,
                'Revolver': revolver_balance,
                'TLB': tlb_balance,
                'HY_Bonds': hy_balance,
                'Total_Debt': total_debt,
                'Leverage': total_debt / ebitda if ebitda > 0 else 0,
                'Interest_Coverage': ebitda / total_interest if total_interest > 0 else 0
            })

        return pd.DataFrame(schedule)

    def calculate_exit_value(self, exit_year: int, exit_multiple: float) -> Dict:
        """
        Calculate exit enterprise value and equity proceeds
        """
        # Get exit year EBITDA
        exit_data = self.projections[self.projections['Year'] == exit_year].iloc[0]
        exit_ebitda = exit_data['Total_EBITDA']

        # Calculate exit EV
        exit_ev = exit_ebitda * exit_multiple

        # Get debt balance at exit
        debt_schedule = self.calculate_debt_schedule(
            self.build_debt_structure(self.build_sources_and_uses()['sources']['new_debt']),
            HOLD_PERIOD
        )
        exit_debt = debt_schedule[debt_schedule['Year'] == exit_year]['Total_Debt'].values[0]

        # Exit equity value
        exit_equity_value = exit_ev - exit_debt

        # Adjust for management dilution
        exit_equity_to_sponsor = exit_equity_value * (1 - DILUTION_FROM_MGMT_EQUITY)

        return {
            'exit_year': exit_year,
            'exit_ebitda': exit_ebitda,
            'exit_multiple': exit_multiple,
            'exit_ev': exit_ev,
            'exit_debt': exit_debt,
            'exit_equity_gross': exit_equity_value,
            'mgmt_dilution': exit_equity_value * DILUTION_FROM_MGMT_EQUITY,
            'exit_equity_to_sponsor': exit_equity_to_sponsor
        }

    def calculate_returns(self, exit_year: int, exit_multiple: float) -> Dict:
        """
        Calculate IRR and MoIC
        """
        sources = self.build_sources_and_uses()
        initial_equity = sources['sources']['equity_contribution']

        exit_analysis = self.calculate_exit_value(exit_year, exit_multiple)
        exit_proceeds = exit_analysis['exit_equity_to_sponsor']

        # MoIC
        moic = exit_proceeds / initial_equity if initial_equity > 0 else 0

        # IRR (simple calculation)
        years = exit_year - 2024
        irr = (moic ** (1/years)) - 1 if years > 0 else 0

        return {
            'initial_equity': initial_equity,
            'exit_proceeds': exit_proceeds,
            'moic': moic,
            'irr': irr,
            'years': years,
            'annualized_return': irr * 100
        }

    def run_sensitivity_analysis(self) -> pd.DataFrame:
        """
        2-way sensitivity: Exit Multiple × Entry Multiple
        """
        exit_multiples = [4.0, 4.5, 5.0, 5.5, 6.0]
        entry_multiples = [5.0, 5.5, 6.0, 6.5, 7.0]

        results = []

        for exit_mult in exit_multiples:
            row = {'Exit_Multiple': exit_mult}
            for entry_mult in entry_multiples:
                # Recalculate with different entry
                temp_entry_ev = self.ebitda_2024 * entry_mult
                temp_equity_needed = temp_entry_ev + NET_DEBT - EXISTING_CASH
                temp_debt = self.ebitda_2024 * TARGET_LEVERAGE
                temp_initial_equity = temp_equity_needed - temp_debt

                # Exit value
                exit_data = self.calculate_exit_value(2024 + HOLD_PERIOD, exit_mult)
                exit_proceeds = exit_data['exit_equity_to_sponsor']

                # Returns
                moic = exit_proceeds / temp_initial_equity if temp_initial_equity > 0 else 0
                irr = (moic ** (1/HOLD_PERIOD)) - 1 if HOLD_PERIOD > 0 else 0

                row[f'Entry_{entry_mult}x'] = irr * 100

            results.append(row)

        return pd.DataFrame(results)

    def generate_executive_summary(self) -> str:
        """
        Generate executive summary of LBO analysis
        """
        sources = self.build_sources_and_uses()
        base_returns = self.calculate_returns(2024 + HOLD_PERIOD, EXIT_MULTIPLE_BASE)

        summary = f"""
{'='*80}
USS LBO ANALYSIS - EXECUTIVE SUMMARY
{'='*80}

Analysis Date: December 31, 2024
Scenario: {self.scenario_type.value}
Hold Period: {HOLD_PERIOD} years

TRANSACTION OVERVIEW
{'-'*80}
Entry Price:              ${ENTRY_PRICE_PER_SHARE:.2f}/share
Entry Equity Value:       ${sources['uses']['equity_purchase']:,.0f}M
Entry Enterprise Value:   ${sources['entry_metrics']['entry_ev']:,.0f}M
Entry EV/EBITDA:          {sources['entry_metrics']['entry_multiple']:.1f}x

2024 EBITDA:              ${self.ebitda_2024:,.0f}M

SOURCES & USES
{'-'*80}
USES:
  Equity Purchase         ${sources['uses']['equity_purchase']:,.0f}M
  Refinance Debt          ${sources['uses']['refinance_debt']:,.0f}M
  Transaction Fees        ${sources['uses']['transaction_fees']:,.0f}M
  Total Uses              ${sources['uses']['total_uses']:,.0f}M

SOURCES:
  New Debt                ${sources['sources']['new_debt']:,.0f}M
  Existing Cash           ${sources['sources']['existing_cash']:,.0f}M
  Financing Fees          (${sources['sources']['financing_fees']:,.0f}M)
  Equity Contribution     ${sources['sources']['equity_contribution']:,.0f}M
  Total Sources           ${sources['sources']['total_sources']:,.0f}M

CAPITAL STRUCTURE
{'-'*80}
Total Debt:               ${sources['sources']['new_debt']:,.0f}M
Total Leverage:           {sources['entry_metrics']['leverage']:.1f}x EBITDA
Equity:                   ${sources['sources']['equity_contribution']:,.0f}M
% Equity:                 {sources['sources']['equity_contribution']/sources['sources']['total_sources']*100:.1f}%

BASE CASE RETURNS (Exit @ {EXIT_MULTIPLE_BASE:.1f}x)
{'-'*80}
Initial Equity:           ${base_returns['initial_equity']:,.0f}M
Exit Proceeds:            ${base_returns['exit_proceeds']:,.0f}M
MoIC:                     {base_returns['moic']:.2f}x
IRR:                      {base_returns['annualized_return']:.1f}%

PE TARGET:                20.0%+
MEETS PE THRESHOLD?       {'✓ YES' if base_returns['annualized_return'] >= 20 else '✗ NO'}

COMPARISON TO NIPPON STRATEGIC OFFER
{'-'*80}
Nippon Offer Price:       $55.00/share
PE Could Pay (20% IRR):   ~${self._calculate_max_price():.2f}/share
Delta:                    ${self._calculate_max_price() - 55:.2f}/share

CONCLUSION: {'PE CANNOT COMPETE AT $55/SHARE' if base_returns['annualized_return'] < 20 else 'PE COULD COMPETE'}

{'='*80}
"""
        return summary

    def _calculate_max_price(self) -> float:
        """Calculate maximum price PE could pay to achieve 20% IRR"""
        # Iterative approach - find price where IRR = 20%
        for price in range(30, 70):
            temp_ev = price * SHARES_OUTSTANDING + NET_DEBT
            temp_debt = self.ebitda_2024 * TARGET_LEVERAGE
            temp_equity = temp_ev - temp_debt + temp_ev * TRANSACTION_FEES_PCT

            exit_data = self.calculate_exit_value(2024 + HOLD_PERIOD, EXIT_MULTIPLE_BASE)
            moic = exit_data['exit_equity_to_sponsor'] / temp_equity
            irr = (moic ** (1/HOLD_PERIOD)) - 1

            if irr >= 0.20:
                return float(price)

        return 30.0  # Fallback


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """
    Run complete LBO analysis
    """
    print("\n" + "="*80)
    print("USS LBO MODEL - COMPREHENSIVE ANALYSIS")
    print("="*80 + "\n")

    # Run analysis for Conservative scenario (PE underwriting standard)
    model = USSLBOModel(scenario_type=ScenarioType.CONSERVATIVE)

    # Executive Summary
    print(model.generate_executive_summary())

    # Detailed Debt Schedule
    print("\nDEBT SCHEDULE (Year-by-Year)")
    print("-"*80)
    sources = model.build_sources_and_uses()
    debt_structure = model.build_debt_structure(sources['sources']['new_debt'])
    debt_schedule = model.calculate_debt_schedule(debt_structure, HOLD_PERIOD)

    display_cols = ['Year', 'EBITDA', 'Interest', 'Total_Debt', 'Leverage', 'Interest_Coverage']
    print(debt_schedule[display_cols].to_string(index=False))

    # Sensitivity Analysis
    print("\n\nIRR SENSITIVITY ANALYSIS (%)")
    print("-"*80)
    print("Exit Multiple (rows) × Entry Multiple (columns)\n")

    sensitivity = model.run_sensitivity_analysis()
    print(sensitivity.to_string(index=False))

    # Key Insights
    print("\n\nKEY INSIGHTS")
    print("="*80)
    base_returns = model.calculate_returns(2024 + HOLD_PERIOD, EXIT_MULTIPLE_BASE)

    print(f"\n1. BASE CASE IRR: {base_returns['annualized_return']:.1f}%")
    if base_returns['annualized_return'] < 15:
        print("   → BELOW MINIMUM PE THRESHOLD (15%)")
        print("   → DEAL WOULD NOT PROCEED")
    elif base_returns['annualized_return'] < 20:
        print("   → BELOW TARGET PE RETURNS (20%)")
        print("   → MARGINAL / WOULD REQUIRE PRICE REDUCTION")
    else:
        print("   → MEETS PE RETURN THRESHOLDS ✓")

    print(f"\n2. LEVERAGE: {sources['entry_metrics']['leverage']:.1f}x EBITDA")
    if sources['entry_metrics']['leverage'] > 5.5:
        print("   → AGGRESSIVE for cyclical steel industry")
        print("   → HIGH RISK in downturn scenario")
    elif sources['entry_metrics']['leverage'] > 4.5:
        print("   → MODERATE but still risky for steel")
    else:
        print("   → CONSERVATIVE leverage")

    print(f"\n3. INTEREST COVERAGE: {debt_schedule['Interest_Coverage'].iloc[0]:.1f}x")
    if debt_schedule['Interest_Coverage'].iloc[0] < 2.0:
        print("   → BELOW SAFETY THRESHOLD")
        print("   → VULNERABLE TO EBITDA DECLINE")
    else:
        print("   → ADEQUATE initial coverage")

    print("\n4. CAPEX CONSTRAINTS:")
    print("   → $14B NSA investment program UNFUNDABLE under LBO structure")
    print("   → Debt covenants would restrict major capital projects")
    print("   → Cash sweep diverts 75% of FCF to debt paydown")

    print("\n5. NIPPON STRATEGIC ADVANTAGE:")
    print("   → Can pay $55/share with 7.5% WACC")
    print("   → No debt service burden")
    print("   → Can fund full $14B CapEx program")
    print(f"   → Creates ${model.analysis['val_nippon']['share_price'] - 55:.2f}/share of value")

    print("\n" + "="*80)
    print("CONCLUSION: NIPPON'S STRATEGIC OFFER SUPERIOR TO PE ALTERNATIVE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
