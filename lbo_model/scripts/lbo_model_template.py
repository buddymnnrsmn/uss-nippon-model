#!/usr/bin/env python3
"""
LBO Model Template: U.S. Steel Corporation
===========================================

This template provides the complete structure for an LBO model that integrates
with the existing PriceVolumeModel to analyze USS from a private equity perspective.

Purpose:
    - Demonstrate why Nippon's $55/share offer is superior to PE alternatives
    - Show that PE firms cannot generate adequate returns at this price
    - Prove that $14B NSA CapEx program is unfundable by financial buyers

Key Components:
    1. Sources & Uses table
    2. Debt schedule (amortization, sweep, interest)
    3. Cash flow waterfall (EBITDA → Levered FCF)
    4. Exit analysis
    5. Returns calculations (IRR, MoIC)
    6. Sensitivity analysis

Integration:
    - Imports PriceVolumeModel for operating projections (EBITDA, CapEx, NWC)
    - Layers LBO-specific financing structure on top
    - Uses conservative scenarios (PE underwriting standards)
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import pandas as pd
import numpy as np
from scipy.optimize import newton

# Add parent directory to path for PriceVolumeModel import
sys.path.append(str(Path(__file__).parent.parent.parent))

from price_volume_model import (
    PriceVolumeModel,
    ScenarioType,
    get_scenario_presets,
    ModelScenario
)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class DebtTranche(Enum):
    """Debt tranche types in typical LBO capital structure"""
    REVOLVER = "Revolver"
    TERM_LOAN_A = "Term Loan A"
    TERM_LOAN_B = "Term Loan B"
    SENIOR_NOTES = "Senior Notes"
    SUBORDINATED = "Subordinated Notes"


class ExitMethod(Enum):
    """Exit methodology for terminal value calculation"""
    COMP_MULTIPLE = "Comparable Company Multiple"
    PRECEDENT_MULTIPLE = "Precedent Transaction Multiple"
    ENTRY_MULTIPLE = "Entry Multiple (No Expansion)"
    DCF_TERMINAL = "DCF Terminal Value"


# Standard LBO assumptions for steel/industrial LBOs
STEEL_INDUSTRY_BENCHMARKS = {
    'leverage': {
        'conservative': {'total_debt_ebitda': 3.5, 'senior_debt_ebitda': 2.5},
        'moderate': {'total_debt_ebitda': 4.5, 'senior_debt_ebitda': 3.0},
        'aggressive': {'total_debt_ebitda': 5.5, 'senior_debt_ebitda': 3.5},
    },
    'exit_multiples': {
        'bear': 4.0,      # Trough cycle
        'base': 5.0,      # Mid-cycle
        'bull': 6.0,      # Peak cycle
    },
    'pe_return_thresholds': {
        'minimum': 0.15,  # 15% IRR (below this, would not pursue)
        'target': 0.20,   # 20% IRR (standard PE target)
        'excellent': 0.25 # 25%+ IRR (outstanding returns)
    }
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DebtTrancheConfig:
    """Configuration for a single debt tranche"""
    name: str
    tranche_type: DebtTranche

    # Size and maturity
    principal: float  # $M (or commitment for revolver)
    drawn_at_close: float  # $M (for revolver, typically 0)
    term_years: int

    # Pricing
    is_floating_rate: bool
    interest_rate: float  # Absolute rate (e.g., 0.065 for 6.5%)
    sofr_spread: Optional[float] = None  # bps spread over SOFR (if floating)
    sofr_floor: Optional[float] = None  # SOFR floor (if floating)

    # Amortization
    annual_amortization_pct: float = 0.0  # % of original principal per year
    is_bullet: bool = False  # True = no amortization until maturity

    # Cash sweep
    subject_to_sweep: bool = True

    # Fees
    commitment_fee_pct: float = 0.0  # For undrawn revolver (% annual)
    prepayment_penalty: Dict[int, float] = field(default_factory=dict)  # {year: penalty_pct}

    # Other
    is_callable: bool = True  # Can be refinanced/repaid early


@dataclass
class LBOTransactionInputs:
    """Inputs for the LBO transaction structure"""

    # Entry valuation
    entry_price_per_share: float  # Purchase price ($/share)
    entry_ev_ebitda_multiple: float  # Implied EV/EBITDA at entry
    shares_outstanding: float  # M shares
    transaction_date: str  # e.g., "2024-01-01"

    # Exit assumptions
    exit_method: ExitMethod
    exit_ev_ebitda_multiple: float  # Exit multiple
    exit_year: int  # Which projection year (5-7 typical)

    # Transaction expenses (as % of transaction size)
    financial_advisory_fee_pct: float = 0.012  # 1.2%
    legal_due_diligence_fee: float = 25.0  # $M flat fee
    financing_fee_pct: float = 0.025  # 2.5% of debt raised

    # Management rollover
    mgmt_rollover_pct: float = 0.0  # % of equity rolled over by management


@dataclass
class CashSweepConfig:
    """Configuration for cash sweep covenant"""

    # Leverage-based sweep percentages
    sweep_pct_high_leverage: float = 0.50  # When leverage > threshold_high
    sweep_pct_mid_leverage: float = 0.25   # When threshold_mid < leverage ≤ threshold_high
    sweep_pct_low_leverage: float = 0.00   # When leverage ≤ threshold_mid

    # Leverage thresholds (Debt/EBITDA)
    threshold_high: float = 3.5
    threshold_mid: float = 2.5

    # Reserves before sweep is calculated
    capex_reserve: float = 100.0  # $M
    min_cash_balance: float = 200.0  # $M


@dataclass
class LBOScenario:
    """Complete LBO scenario combining operating model and financing"""
    name: str
    description: str

    # Operating model (from PriceVolumeModel)
    operating_scenario: ModelScenario
    execution_haircut: float = 0.75  # Haircut on projections (0.75 = 25% cut)

    # Transaction inputs
    transaction: LBOTransactionInputs

    # Debt structure
    debt_tranches: List[DebtTrancheConfig]

    # Cash sweep
    cash_sweep: CashSweepConfig

    # SOFR forward curve (for floating rate debt)
    sofr_forward_curve: Dict[int, float] = field(default_factory=dict)  # {year: rate}


# =============================================================================
# SOURCES & USES TABLE
# =============================================================================

class SourcesUsesTable:
    """Builds the Sources & Uses table for the LBO transaction"""

    def __init__(self, scenario: LBOScenario, base_financials: dict):
        """
        Args:
            scenario: LBO scenario configuration
            base_financials: Dict with current balance sheet items
                - cash: Current cash & equivalents
                - investments: Short-term investments
                - total_debt: Existing debt to refinance
                - pension: Pension obligations
                - leases: Operating lease liabilities
        """
        self.scenario = scenario
        self.base_financials = base_financials

    def calculate_uses(self) -> Dict[str, float]:
        """
        Calculate Uses of Funds

        Returns:
            Dict with breakdown of all uses
        """
        txn = self.scenario.transaction
        bf = self.base_financials

        # Purchase equity value = EV - Net Debt
        # For LBO, we calculate EV from entry multiple × LTM EBITDA
        # (Will get LTM EBITDA from PriceVolumeModel)

        uses = {}

        # TODO: Get LTM EBITDA from operating model
        ltm_ebitda = 2500.0  # $M - PLACEHOLDER, replace with actual

        # Enterprise Value at entry
        enterprise_value = ltm_ebitda * txn.entry_ev_ebitda_multiple
        uses['enterprise_value'] = enterprise_value

        # Equity bridge
        uses['plus_cash'] = bf['cash']
        uses['plus_investments'] = bf['investments']
        uses['less_debt'] = -bf['total_debt']
        uses['less_pension'] = -bf['pension']
        uses['less_leases'] = -bf['leases']

        equity_purchase_price = (enterprise_value + bf['cash'] + bf['investments']
                                - bf['total_debt'] - bf['pension'] - bf['leases'])
        uses['equity_purchase_price'] = equity_purchase_price

        # Transaction expenses
        transaction_size = enterprise_value  # Base fees on EV
        uses['financial_advisory'] = transaction_size * txn.financial_advisory_fee_pct
        uses['legal_dd'] = txn.legal_due_diligence_fee

        # Financing fees (calculated on new debt)
        total_new_debt = sum(dt.principal for dt in self.scenario.debt_tranches
                            if dt.tranche_type != DebtTranche.REVOLVER)
        uses['financing_fees'] = total_new_debt * txn.financing_fee_pct

        # Refinance existing debt
        uses['refinance_existing_debt'] = bf['total_debt']

        # Total uses
        uses['total_uses'] = (uses['equity_purchase_price'] +
                             uses['financial_advisory'] +
                             uses['legal_dd'] +
                             uses['financing_fees'] +
                             uses['refinance_existing_debt'])

        return uses

    def calculate_sources(self) -> Dict[str, float]:
        """
        Calculate Sources of Funds

        Returns:
            Dict with breakdown of all sources
        """
        sources = {}

        # Debt tranches
        for dt in self.scenario.debt_tranches:
            if dt.tranche_type == DebtTranche.REVOLVER:
                sources[f'revolver_commitment'] = dt.principal
                sources[f'revolver_drawn'] = dt.drawn_at_close
            else:
                sources[dt.name] = dt.principal

        # Total debt
        total_debt = sum(dt.principal for dt in self.scenario.debt_tranches
                        if dt.tranche_type != DebtTranche.REVOLVER)
        total_debt += sum(dt.drawn_at_close for dt in self.scenario.debt_tranches
                         if dt.tranche_type == DebtTranche.REVOLVER)
        sources['total_debt'] = total_debt

        # Management rollover
        uses = self.calculate_uses()
        mgmt_rollover = uses['equity_purchase_price'] * self.scenario.transaction.mgmt_rollover_pct
        sources['mgmt_rollover'] = mgmt_rollover

        # Sponsor equity = plug to make sources = uses
        sponsor_equity = uses['total_uses'] - total_debt - mgmt_rollover
        sources['sponsor_equity'] = sponsor_equity

        # Total sources
        sources['total_sources'] = uses['total_uses']

        return sources

    def build_table(self) -> pd.DataFrame:
        """
        Build formatted Sources & Uses table

        Returns:
            DataFrame with Sources & Uses
        """
        uses = self.calculate_uses()
        sources = self.calculate_sources()

        # Format as table
        data = []

        # Uses section
        data.append({'Category': 'USES OF FUNDS', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Enterprise Value', 'Amount ($M)': uses['enterprise_value'],
                    '% of Total': None})
        data.append({'Category': '  + Cash', 'Amount ($M)': uses['plus_cash'], '% of Total': None})
        data.append({'Category': '  + Investments', 'Amount ($M)': uses['plus_investments'],
                    '% of Total': None})
        data.append({'Category': '  - Total Debt', 'Amount ($M)': uses['less_debt'], '% of Total': None})
        data.append({'Category': '  - Pension', 'Amount ($M)': uses['less_pension'], '% of Total': None})
        data.append({'Category': '  - Leases', 'Amount ($M)': uses['less_leases'], '% of Total': None})
        data.append({'Category': '  Equity Purchase Price', 'Amount ($M)': uses['equity_purchase_price'],
                    '% of Total': uses['equity_purchase_price']/uses['total_uses']*100})
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Transaction Expenses', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '    Financial Advisory', 'Amount ($M)': uses['financial_advisory'],
                    '% of Total': uses['financial_advisory']/uses['total_uses']*100})
        data.append({'Category': '    Legal & DD', 'Amount ($M)': uses['legal_dd'],
                    '% of Total': uses['legal_dd']/uses['total_uses']*100})
        data.append({'Category': '    Financing Fees', 'Amount ($M)': uses['financing_fees'],
                    '% of Total': uses['financing_fees']/uses['total_uses']*100})
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Refinance Existing Debt', 'Amount ($M)': uses['refinance_existing_debt'],
                    '% of Total': uses['refinance_existing_debt']/uses['total_uses']*100})
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': 'Total Uses', 'Amount ($M)': uses['total_uses'],
                    '% of Total': 100.0})

        # Separator
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})

        # Sources section
        data.append({'Category': 'SOURCES OF FUNDS', 'Amount ($M)': None, '% of Total': None})
        for dt in self.scenario.debt_tranches:
            if dt.tranche_type != DebtTranche.REVOLVER:
                data.append({'Category': f'  {dt.name}', 'Amount ($M)': dt.principal,
                           '% of Total': dt.principal/sources['total_sources']*100})

        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Management Rollover', 'Amount ($M)': sources['mgmt_rollover'],
                    '% of Total': sources['mgmt_rollover']/sources['total_sources']*100})
        data.append({'Category': '  Sponsor Equity', 'Amount ($M)': sources['sponsor_equity'],
                    '% of Total': sources['sponsor_equity']/sources['total_sources']*100})
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': 'Total Sources', 'Amount ($M)': sources['total_sources'],
                    '% of Total': 100.0})

        # Credit statistics
        ltm_ebitda = uses['enterprise_value'] / self.scenario.transaction.entry_ev_ebitda_multiple
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': 'PRO FORMA CAPITALIZATION', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Total Debt', 'Amount ($M)': sources['total_debt'], '% of Total': None})
        data.append({'Category': '  Total Equity', 'Amount ($M)': sources['sponsor_equity'] + sources['mgmt_rollover'],
                    '% of Total': None})
        data.append({'Category': '', 'Amount ($M)': None, '% of Total': None})
        data.append({'Category': '  Total Debt / LTM EBITDA',
                    'Amount ($M)': f"{sources['total_debt']/ltm_ebitda:.2f}x", '% of Total': None})
        data.append({'Category': '  Equity % of Total Cap',
                    'Amount ($M)': None,
                    '% of Total': (sources['sponsor_equity'] + sources['mgmt_rollover'])/(sources['total_debt'] + sources['sponsor_equity'] + sources['mgmt_rollover'])*100})

        return pd.DataFrame(data)


# =============================================================================
# DEBT SCHEDULE
# =============================================================================

class DebtSchedule:
    """Manages debt balances, amortization, interest, and cash sweep"""

    def __init__(self, scenario: LBOScenario, cash_flow_projection: pd.DataFrame):
        """
        Args:
            scenario: LBO scenario with debt structure
            cash_flow_projection: DataFrame with yearly Levered FCF (before sweep)
        """
        self.scenario = scenario
        self.cash_flow_projection = cash_flow_projection
        self.years = cash_flow_projection['Year'].tolist()

    def calculate_sofr_rate(self, year: int) -> float:
        """Get SOFR rate for a given year from forward curve"""
        return self.scenario.sofr_forward_curve.get(year, 0.045)  # Default 4.5%

    def calculate_interest_expense(self, year: int, beginning_balance: float,
                                   tranche: DebtTrancheConfig) -> float:
        """
        Calculate interest expense for a tranche in a given year

        Args:
            year: Projection year
            beginning_balance: Beginning debt balance
            tranche: Debt tranche configuration

        Returns:
            Interest expense ($M)
        """
        if tranche.is_floating_rate:
            # Floating rate: max(SOFR, floor) + spread
            sofr = self.calculate_sofr_rate(year)
            rate = max(sofr, tranche.sofr_floor or 0) + (tranche.sofr_spread or 0)
        else:
            # Fixed rate
            rate = tranche.interest_rate

        interest = beginning_balance * rate

        # Add commitment fee for undrawn revolver
        if tranche.tranche_type == DebtTranche.REVOLVER:
            undrawn = tranche.principal - beginning_balance
            interest += undrawn * tranche.commitment_fee_pct

        return interest

    def calculate_mandatory_amortization(self, tranche: DebtTrancheConfig,
                                        beginning_balance: float,
                                        year_index: int) -> float:
        """
        Calculate mandatory amortization payment

        Args:
            tranche: Debt tranche configuration
            beginning_balance: Beginning balance
            year_index: Index of year (0 = first year)

        Returns:
            Mandatory amortization payment ($M)
        """
        if tranche.is_bullet and year_index < tranche.term_years - 1:
            return 0.0

        if tranche.is_bullet and year_index == tranche.term_years - 1:
            # Bullet maturity - pay all remaining balance
            return beginning_balance

        # Linear amortization based on original principal
        return tranche.principal * tranche.annual_amortization_pct

    def calculate_cash_sweep(self, year: int, levered_fcf: float,
                            total_debt: float, ebitda: float) -> Dict[str, float]:
        """
        Calculate cash sweep payment based on excess cash flow

        Args:
            year: Projection year
            levered_fcf: Levered FCF before sweep
            total_debt: Total debt balance
            ebitda: EBITDA for the year

        Returns:
            Dict with sweep details
        """
        sweep_config = self.scenario.cash_sweep

        # Calculate leverage ratio
        leverage = total_debt / ebitda if ebitda > 0 else 99.9

        # Determine sweep percentage based on leverage
        if leverage > sweep_config.threshold_high:
            sweep_pct = sweep_config.sweep_pct_high_leverage
        elif leverage > sweep_config.threshold_mid:
            sweep_pct = sweep_config.sweep_pct_mid_leverage
        else:
            sweep_pct = sweep_config.sweep_pct_low_leverage

        # Calculate excess cash flow (after reserves)
        excess_cash_flow = max(0, levered_fcf - sweep_config.capex_reserve
                                              - sweep_config.min_cash_balance)

        # Calculate sweep amount
        sweep_amount = excess_cash_flow * sweep_pct

        return {
            'year': year,
            'leverage': leverage,
            'sweep_percentage': sweep_pct,
            'levered_fcf': levered_fcf,
            'excess_cash_flow': excess_cash_flow,
            'sweep_amount': sweep_amount,
            'remaining_cash': levered_fcf - sweep_amount
        }

    def build_schedule(self) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Build complete debt schedule with amortization, sweep, and interest

        Returns:
            Tuple of (debt_schedule_df, sweep_details_list)
        """
        schedule_data = []
        sweep_details = []

        # Initialize balances
        balances = {}
        for tranche in self.scenario.debt_tranches:
            if tranche.tranche_type == DebtTranche.REVOLVER:
                balances[tranche.name] = tranche.drawn_at_close
            else:
                balances[tranche.name] = tranche.principal

        # Project each year
        for year_idx, year in enumerate(self.years):
            row = {'Year': year}

            # Beginning balances
            for tranche in self.scenario.debt_tranches:
                row[f'{tranche.name}_Beginning'] = balances[tranche.name]

            total_beginning_debt = sum(balances.values())
            row['Total_Debt_Beginning'] = total_beginning_debt

            # Mandatory amortization
            total_mandatory = 0
            for tranche in self.scenario.debt_tranches:
                amort = self.calculate_mandatory_amortization(
                    tranche, balances[tranche.name], year_idx
                )
                row[f'{tranche.name}_Mandatory_Amort'] = -amort
                total_mandatory += amort

            row['Total_Mandatory_Amort'] = -total_mandatory

            # Interest expense
            total_interest = 0
            for tranche in self.scenario.debt_tranches:
                interest = self.calculate_interest_expense(
                    year, balances[tranche.name], tranche
                )
                row[f'{tranche.name}_Interest'] = -interest
                total_interest += interest

            row['Total_Interest'] = -total_interest

            # TODO: Get EBITDA and Levered FCF from cash flow waterfall
            # For now, use placeholders
            ebitda = 2500.0  # PLACEHOLDER
            levered_fcf = 500.0  # PLACEHOLDER (before sweep)

            # Calculate cash sweep
            sweep_result = self.calculate_cash_sweep(
                year,
                levered_fcf,
                total_beginning_debt - total_mandatory,  # Debt after mandatory
                ebitda
            )
            sweep_details.append(sweep_result)

            # Apply sweep to tranches (highest cost first)
            # Sort tranches by cost (floating: SOFR+spread, fixed: rate)
            sweep_remaining = sweep_result['sweep_amount']

            # Priority: TLB → TLA → Senior Notes
            sweep_priority = sorted(
                [t for t in self.scenario.debt_tranches if t.subject_to_sweep],
                key=lambda t: (t.sofr_spread or t.interest_rate),
                reverse=True
            )

            for tranche in self.scenario.debt_tranches:
                if tranche in sweep_priority and sweep_remaining > 0:
                    # Apply sweep to this tranche
                    sweep_to_tranche = min(sweep_remaining,
                                          balances[tranche.name] - row.get(f'{tranche.name}_Mandatory_Amort', 0))
                    row[f'{tranche.name}_Sweep'] = -sweep_to_tranche
                    sweep_remaining -= sweep_to_tranche
                else:
                    row[f'{tranche.name}_Sweep'] = 0

            row['Total_Sweep'] = -sweep_result['sweep_amount']

            # Ending balances
            for tranche in self.scenario.debt_tranches:
                ending = (balances[tranche.name]
                         + row.get(f'{tranche.name}_Mandatory_Amort', 0)
                         + row.get(f'{tranche.name}_Sweep', 0))
                row[f'{tranche.name}_Ending'] = ending
                balances[tranche.name] = ending  # Update for next year

            row['Total_Debt_Ending'] = sum(balances.values())

            # Credit metrics
            row['Leverage_Ratio'] = row['Total_Debt_Ending'] / ebitda if ebitda > 0 else 0
            row['Interest_Coverage'] = ebitda / total_interest if total_interest > 0 else 999

            schedule_data.append(row)

        return pd.DataFrame(schedule_data), sweep_details


# =============================================================================
# CASH FLOW WATERFALL
# =============================================================================

class CashFlowWaterfall:
    """Builds cash flow waterfall from EBITDA to Levered FCF"""

    def __init__(self, operating_projections: pd.DataFrame,
                 debt_schedule: pd.DataFrame):
        """
        Args:
            operating_projections: From PriceVolumeModel (EBITDA, D&A, CapEx, NWC)
            debt_schedule: Debt schedule with interest expense
        """
        self.operating_projections = operating_projections
        self.debt_schedule = debt_schedule

    def build_waterfall(self) -> pd.DataFrame:
        """
        Build complete cash flow waterfall

        Waterfall:
            EBITDA
            - D&A
            = EBIT
            - Cash Taxes
            = NOPAT
            + D&A (add back)
            = Cash from Operations
            - Change in NWC
            - CapEx
            = UNLEVERED FCF
            - Interest Expense
            - Mandatory Debt Amortization
            = LEVERED FCF (before sweep)
            - Cash Sweep
            = LEVERED FCF (after sweep)

        Returns:
            DataFrame with complete waterfall
        """
        waterfall = []

        for _, op_row in self.operating_projections.iterrows():
            year = op_row['Year']

            # Get debt schedule row for this year
            debt_row = self.debt_schedule[self.debt_schedule['Year'] == year].iloc[0]

            row = {
                'Year': year,

                # Level 1: Operating Performance
                'Revenue': op_row.get('Revenue', 0),
                'EBITDA': op_row.get('Total_EBITDA', 0),

                # Level 2: Non-cash adjustments
                'DA': op_row.get('DA', 0),
                'EBIT': op_row.get('Total_EBITDA', 0) - op_row.get('DA', 0),

                # Level 3: Taxes
                'Cash_Tax_Rate': 0.169,  # 16.9% effective cash tax rate
            }

            row['Cash_Taxes'] = -row['EBIT'] * row['Cash_Tax_Rate']
            row['NOPAT'] = row['EBIT'] + row['Cash_Taxes']  # Taxes already negative

            # Level 4: Add back D&A
            row['Cash_from_Operations'] = row['NOPAT'] + row['DA']

            # Level 5: Working Capital & CapEx
            row['Delta_NWC'] = op_row.get('Delta_WC', 0)  # Positive = source of cash
            row['CapEx'] = -op_row.get('Total_CapEx', 0)  # Negative = use of cash
            row['Unlevered_FCF'] = row['Cash_from_Operations'] + row['Delta_NWC'] + row['CapEx']

            # Level 6: Debt Service
            row['Interest_Expense'] = debt_row.get('Total_Interest', 0)  # Already negative
            row['Mandatory_Amortization'] = debt_row.get('Total_Mandatory_Amort', 0)  # Already negative
            row['Levered_FCF_Before_Sweep'] = (row['Unlevered_FCF'] +
                                               row['Interest_Expense'] +
                                               row['Mandatory_Amortization'])

            # Level 7: Cash Sweep
            row['Cash_Sweep'] = debt_row.get('Total_Sweep', 0)  # Already negative
            row['Levered_FCF_After_Sweep'] = row['Levered_FCF_Before_Sweep'] + row['Cash_Sweep']

            # Cash accumulation
            if len(waterfall) == 0:
                row['Cash_Balance'] = row['Levered_FCF_After_Sweep']
            else:
                row['Cash_Balance'] = waterfall[-1]['Cash_Balance'] + row['Levered_FCF_After_Sweep']

            waterfall.append(row)

        return pd.DataFrame(waterfall)


# =============================================================================
# EXIT ANALYSIS
# =============================================================================

class ExitAnalysis:
    """Calculates exit value and returns metrics"""

    def __init__(self, scenario: LBOScenario, waterfall: pd.DataFrame,
                 debt_schedule: pd.DataFrame, sources_uses: SourcesUsesTable):
        """
        Args:
            scenario: LBO scenario
            waterfall: Cash flow waterfall
            debt_schedule: Debt schedule
            sources_uses: Sources & Uses table
        """
        self.scenario = scenario
        self.waterfall = waterfall
        self.debt_schedule = debt_schedule
        self.sources_uses = sources_uses

    def calculate_exit_enterprise_value(self) -> Dict[str, float]:
        """
        Calculate exit enterprise value using specified method

        Returns:
            Dict with EV calculation details
        """
        txn = self.scenario.transaction
        exit_year = txn.exit_year

        # Get exit year EBITDA (LTM at exit)
        exit_ebitda = self.waterfall[self.waterfall['Year'] == exit_year]['EBITDA'].values[0]

        # Calculate EV based on method
        if txn.exit_method in [ExitMethod.COMP_MULTIPLE, ExitMethod.PRECEDENT_MULTIPLE,
                               ExitMethod.ENTRY_MULTIPLE]:
            exit_ev = exit_ebitda * txn.exit_ev_ebitda_multiple
            method_used = txn.exit_method.value
        else:
            # DCF terminal value method (not implemented in template)
            exit_ev = exit_ebitda * txn.exit_ev_ebitda_multiple
            method_used = "DCF Terminal Value (Not Implemented)"

        return {
            'exit_year': exit_year,
            'exit_ebitda': exit_ebitda,
            'exit_ev_ebitda_multiple': txn.exit_ev_ebitda_multiple,
            'exit_enterprise_value': exit_ev,
            'method': method_used
        }

    def calculate_exit_equity_value(self) -> Dict[str, float]:
        """
        Calculate equity value to sponsor at exit

        Returns:
            Dict with equity value bridge
        """
        ev_result = self.calculate_exit_enterprise_value()
        exit_year = ev_result['exit_year']

        # Get debt balance at exit
        exit_debt = self.debt_schedule[
            self.debt_schedule['Year'] == exit_year
        ]['Total_Debt_Ending'].values[0]

        # Get cash balance at exit
        exit_cash = self.waterfall[
            self.waterfall['Year'] == exit_year
        ]['Cash_Balance'].values[0]

        # Net debt at exit
        net_debt = exit_debt - exit_cash

        # Other liabilities (assumed constant)
        pension = 126.0  # $M
        leases = 117.0   # $M

        # Equity value
        equity_value = ev_result['exit_enterprise_value'] - net_debt - pension - leases

        # Adjust for management rollover (they get their share)
        sources = self.sources_uses.calculate_sources()
        mgmt_pct = (sources['mgmt_rollover'] /
                   (sources['mgmt_rollover'] + sources['sponsor_equity']))

        sponsor_equity_value = equity_value * (1 - mgmt_pct)

        return {
            'exit_enterprise_value': ev_result['exit_enterprise_value'],
            'exit_debt': exit_debt,
            'exit_cash': exit_cash,
            'net_debt': net_debt,
            'pension': pension,
            'leases': leases,
            'total_equity_value': equity_value,
            'mgmt_rollover_pct': mgmt_pct,
            'sponsor_equity_value': sponsor_equity_value,
            'exit_year': exit_year
        }

    def calculate_returns(self) -> Dict[str, float]:
        """
        Calculate IRR and MoIC

        Returns:
            Dict with returns metrics
        """
        equity_result = self.calculate_exit_equity_value()
        sources = self.sources_uses.calculate_sources()

        # Initial investment
        initial_investment = sources['sponsor_equity']

        # Exit proceeds
        exit_proceeds = equity_result['sponsor_equity_value']

        # Interim distributions (typically none in first few years)
        # TODO: Add dividend distributions if modeled
        interim_distributions = 0.0

        # Calculate MoIC
        total_cash_returned = exit_proceeds + interim_distributions
        moic = total_cash_returned / initial_investment

        # Calculate IRR
        holding_period = equity_result['exit_year'] - self.waterfall['Year'].min()

        # Build cash flow list for IRR calculation
        cash_flows = [-initial_investment]  # Year 0
        for i in range(1, holding_period):
            cash_flows.append(0)  # No interim distributions (typically)
        cash_flows.append(exit_proceeds)  # Exit year

        # Solve for IRR using Newton's method
        def npv(rate):
            return sum(cf / (1 + rate)**i for i, cf in enumerate(cash_flows))

        try:
            irr = newton(npv, 0.15)  # Start with 15% guess
        except:
            irr = 0.0  # Failed to converge

        # Annualized return (simple)
        annualized_return = (moic ** (1/holding_period)) - 1

        return {
            'initial_investment': initial_investment,
            'exit_proceeds': exit_proceeds,
            'interim_distributions': interim_distributions,
            'total_cash_returned': total_cash_returned,
            'moic': moic,
            'irr': irr,
            'annualized_return': annualized_return,
            'holding_period': holding_period,
            'absolute_return': exit_proceeds - initial_investment
        }


# =============================================================================
# SENSITIVITY ANALYSIS
# =============================================================================

class SensitivityAnalysis:
    """Generates sensitivity tables for key variables"""

    def __init__(self, lbo_model: 'LBOModel'):
        """
        Args:
            lbo_model: Complete LBO model instance
        """
        self.lbo_model = lbo_model

    def entry_vs_exit_multiple(self,
                               entry_multiples: List[float],
                               exit_multiples: List[float]) -> pd.DataFrame:
        """
        Generate 2-way sensitivity: Entry Multiple vs Exit Multiple

        Args:
            entry_multiples: List of entry EV/EBITDA multiples to test
            exit_multiples: List of exit EV/EBITDA multiples to test

        Returns:
            DataFrame with IRR at each combination
        """
        # TODO: Implement sensitivity by varying entry/exit multiples
        # and re-running LBO model to calculate IRR at each point

        # Placeholder structure
        results = []
        for entry_mult in entry_multiples:
            row = {'Entry_Multiple': entry_mult}
            for exit_mult in exit_multiples:
                # TODO: Re-run model with these multiples
                # irr = self.lbo_model.run_with_params(entry_mult, exit_mult)
                irr = 0.15  # PLACEHOLDER
                row[f'Exit_{exit_mult:.1f}x'] = irr
            results.append(row)

        return pd.DataFrame(results)

    def ebitda_growth_vs_exit_multiple(self,
                                       ebitda_cagrs: List[float],
                                       exit_multiples: List[float]) -> pd.DataFrame:
        """
        Generate 2-way sensitivity: EBITDA Growth vs Exit Multiple

        Args:
            ebitda_cagrs: List of EBITDA CAGRs to test (e.g., [-0.05, 0, 0.05])
            exit_multiples: List of exit multiples to test

        Returns:
            DataFrame with IRR at each combination
        """
        # TODO: Implement by varying EBITDA growth assumption
        # and exit multiple, then calculating IRR

        results = []
        for cagr in ebitda_cagrs:
            row = {'EBITDA_CAGR': f'{cagr*100:.0f}%'}
            for exit_mult in exit_multiples:
                irr = 0.15  # PLACEHOLDER
                row[f'Exit_{exit_mult:.1f}x'] = irr
            results.append(row)

        return pd.DataFrame(results)

    def tornado_chart_data(self) -> pd.DataFrame:
        """
        Generate data for tornado chart (sensitivity ranking)

        Tests impact of key variables on IRR by varying each +/- from base case

        Returns:
            DataFrame with variable name, low case IRR, base case IRR, high case IRR
        """
        # TODO: Implement by varying each key input and measuring IRR impact

        variables = [
            'Exit Multiple',
            'Entry Price',
            'EBITDA Performance',
            'Exit Year',
            'Steel Price Scenario',
            'Leverage'
        ]

        results = []
        for var in variables:
            results.append({
                'Variable': var,
                'Low_Case_IRR': 0.10,  # PLACEHOLDER
                'Base_Case_IRR': 0.15,
                'High_Case_IRR': 0.20,
                'Impact_Range': 0.10
            })

        df = pd.DataFrame(results)
        return df.sort_values('Impact_Range', ascending=False)


# =============================================================================
# MAIN LBO MODEL CLASS
# =============================================================================

class LBOModel:
    """
    Complete LBO model integrating all components

    This is the main class that orchestrates:
    1. Operating projections (from PriceVolumeModel)
    2. Sources & Uses
    3. Debt Schedule
    4. Cash Flow Waterfall
    5. Exit Analysis
    6. Returns Calculations
    7. Sensitivity Analysis
    """

    def __init__(self, scenario: LBOScenario, base_financials: dict):
        """
        Args:
            scenario: Complete LBO scenario configuration
            base_financials: Dict with current balance sheet items
        """
        self.scenario = scenario
        self.base_financials = base_financials

        # Initialize components (will be populated by run())
        self.pv_model = None
        self.operating_analysis = None
        self.sources_uses = None
        self.debt_schedule_obj = None
        self.waterfall_obj = None
        self.exit_analysis_obj = None
        self.sensitivity_obj = None

        # Results storage
        self.results = {}

    def build_operating_projections(self) -> pd.DataFrame:
        """
        Build operating projections using PriceVolumeModel

        Returns:
            Consolidated operating projections (EBITDA, D&A, CapEx, NWC)
        """
        # Initialize PriceVolumeModel with conservative scenario
        self.pv_model = PriceVolumeModel(
            scenario=self.scenario.operating_scenario,
            execution_factor=self.scenario.execution_haircut
        )

        # Run analysis
        self.operating_analysis = self.pv_model.run_full_analysis()

        # Return consolidated projections
        return self.operating_analysis['consolidated']

    def run(self) -> Dict:
        """
        Run complete LBO analysis

        Returns:
            Dict with all results:
                - sources_uses_table
                - debt_schedule
                - cash_flow_waterfall
                - exit_valuation
                - returns (IRR, MoIC)
                - sensitivity_tables
        """
        print("=" * 80)
        print("LBO MODEL ANALYSIS - U.S. STEEL CORPORATION")
        print("=" * 80)

        # Step 1: Build operating projections from PriceVolumeModel
        print("\n1. Building operating projections from PriceVolumeModel...")
        operating_proj = self.build_operating_projections()
        self.results['operating_projections'] = operating_proj

        # Step 2: Build Sources & Uses
        print("2. Building Sources & Uses table...")
        self.sources_uses = SourcesUsesTable(self.scenario, self.base_financials)
        sources_uses_table = self.sources_uses.build_table()
        self.results['sources_uses_table'] = sources_uses_table

        sources = self.sources_uses.calculate_sources()
        print(f"   Total Transaction Size: ${sources['total_sources']:,.0f}M")
        print(f"   Sponsor Equity: ${sources['sponsor_equity']:,.0f}M")
        print(f"   Total Debt: ${sources['total_debt']:,.0f}M")

        # Step 3: Build Debt Schedule (requires cash flow, so we need to iterate)
        # For now, build with placeholder FCF, then rebuild after waterfall
        print("3. Building debt schedule...")
        placeholder_cf = operating_proj[['Year']].copy()
        placeholder_cf['Levered_FCF'] = 500.0  # Placeholder

        self.debt_schedule_obj = DebtSchedule(self.scenario, placeholder_cf)
        debt_schedule, sweep_details = self.debt_schedule_obj.build_schedule()
        self.results['debt_schedule'] = debt_schedule
        self.results['sweep_details'] = sweep_details

        # Step 4: Build Cash Flow Waterfall
        print("4. Building cash flow waterfall...")
        self.waterfall_obj = CashFlowWaterfall(operating_proj, debt_schedule)
        waterfall = self.waterfall_obj.build_waterfall()
        self.results['cash_flow_waterfall'] = waterfall

        # TODO: Iterate back to rebuild debt schedule with actual Levered FCF
        # For production model, would loop here until convergence

        # Step 5: Calculate Exit Value and Returns
        print("5. Calculating exit valuation and returns...")
        self.exit_analysis_obj = ExitAnalysis(
            self.scenario, waterfall, debt_schedule, self.sources_uses
        )

        exit_ev = self.exit_analysis_obj.calculate_exit_enterprise_value()
        exit_equity = self.exit_analysis_obj.calculate_exit_equity_value()
        returns = self.exit_analysis_obj.calculate_returns()

        self.results['exit_enterprise_value'] = exit_ev
        self.results['exit_equity_value'] = exit_equity
        self.results['returns'] = returns

        print(f"   Exit EV: ${exit_ev['exit_enterprise_value']:,.0f}M @ {exit_ev['exit_ev_ebitda_multiple']:.1f}x")
        print(f"   Exit Equity Value to Sponsor: ${exit_equity['sponsor_equity_value']:,.0f}M")
        print(f"   IRR: {returns['irr']*100:.1f}%")
        print(f"   MoIC: {returns['moic']:.2f}x")

        # Step 6: Sensitivity Analysis
        print("6. Running sensitivity analysis...")
        self.sensitivity_obj = SensitivityAnalysis(self)

        # Generate sensitivity tables
        # TODO: Define ranges for sensitivity
        # self.results['sensitivity_entry_exit'] = self.sensitivity_obj.entry_vs_exit_multiple(...)
        # self.results['sensitivity_ebitda_exit'] = self.sensitivity_obj.ebitda_growth_vs_exit_multiple(...)
        # self.results['tornado_chart'] = self.sensitivity_obj.tornado_chart_data()

        print("\n" + "=" * 80)
        print("LBO ANALYSIS COMPLETE")
        print("=" * 80)

        return self.results

    def summary_output(self) -> str:
        """
        Generate executive summary text output

        Returns:
            Formatted string with key results
        """
        if not self.results:
            return "Model has not been run yet. Call run() first."

        returns = self.results['returns']
        exit_ev = self.results['exit_enterprise_value']
        sources = self.sources_uses.calculate_sources()

        summary = f"""
USS LBO MODEL - EXECUTIVE SUMMARY
{'=' * 80}

TRANSACTION OVERVIEW
  Target:                     U.S. Steel Corporation
  Entry Price:                ${self.scenario.transaction.entry_price_per_share:.2f} per share
  Entry Multiple:             {self.scenario.transaction.entry_ev_ebitda_multiple:.2f}x EV/EBITDA
  Transaction Size:           ${sources['total_sources']:,.0f}M
  Sponsor Equity:             ${sources['sponsor_equity']:,.0f}M
  Total Debt:                 ${sources['total_debt']:,.0f}M
  Leverage:                   {sources['total_debt']/exit_ev['exit_ebitda']:.2f}x Debt/EBITDA
  Holding Period:             {returns['holding_period']} years

RETURNS SUMMARY
  Exit Enterprise Value:      ${exit_ev['exit_enterprise_value']:,.0f}M
  Exit Multiple:              {exit_ev['exit_ev_ebitda_multiple']:.1f}x EV/EBITDA
  Exit Equity to Sponsor:     ${self.results['exit_equity_value']['sponsor_equity_value']:,.0f}M

  Initial Investment:         ${returns['initial_investment']:,.0f}M
  Exit Proceeds:              ${returns['exit_proceeds']:,.0f}M
  Absolute Return:            ${returns['absolute_return']:,.0f}M

  MoIC:                       {returns['moic']:.2f}x
  IRR:                        {returns['irr']*100:.1f}%
  Annualized Return:          {returns['annualized_return']*100:.1f}%

VERDICT
  PE Return Threshold:        20.0% IRR
  Achieved IRR:               {returns['irr']*100:.1f}%
  Status:                     {'✓ MEETS THRESHOLD' if returns['irr'] >= 0.20 else '✗ BELOW THRESHOLD'}

CONCLUSION
  {self._generate_conclusion(returns['irr'])}

{'=' * 80}
"""
        return summary

    def _generate_conclusion(self, irr: float) -> str:
        """Generate conclusion text based on IRR results"""
        if irr < 0.15:
            return ("USS is NOT an attractive LBO candidate at this price.\n"
                   "  Returns fall well short of PE thresholds.\n"
                   "  Nippon's strategic offer is clearly superior to PE alternative.")
        elif irr < 0.20:
            return ("USS is marginally attractive as an LBO.\n"
                   "  Returns are below standard PE targets (20%+).\n"
                   "  Risk-adjusted, Nippon's strategic offer is superior.")
        else:
            return ("USS could be attractive as an LBO at this price.\n"
                   "  Returns meet PE thresholds.\n"
                   "  However, PE cannot fund $14B CapEx program Nippon committed to.")


# =============================================================================
# EXAMPLE USAGE & SCENARIO BUILDER
# =============================================================================

def build_example_scenario() -> LBOScenario:
    """
    Build an example LBO scenario for USS

    This demonstrates how to configure a complete LBO scenario
    """

    # Get conservative operating scenario from PriceVolumeModel
    operating_scenario = get_scenario_presets()[ScenarioType.CONSERVATIVE]

    # Limit to maintenance CapEx only (PE cannot fund $14B program)
    operating_scenario.include_projects = ['BR2 Mini Mill']  # Only committed project

    # Transaction inputs
    transaction = LBOTransactionInputs(
        entry_price_per_share=55.00,
        entry_ev_ebitda_multiple=5.0,  # Approximate
        shares_outstanding=225.0,
        transaction_date="2024-01-01",
        exit_method=ExitMethod.ENTRY_MULTIPLE,  # Conservative: no multiple expansion
        exit_ev_ebitda_multiple=5.0,  # Same as entry
        exit_year=2029,  # 5-year hold
        financial_advisory_fee_pct=0.012,
        legal_due_diligence_fee=25.0,
        financing_fee_pct=0.025,
        mgmt_rollover_pct=0.10  # 10% management rollover
    )

    # Debt structure (moderate leverage for steel: 4.0x)
    debt_tranches = [
        DebtTrancheConfig(
            name="Revolver",
            tranche_type=DebtTranche.REVOLVER,
            principal=500,
            drawn_at_close=0,
            term_years=5,
            is_floating_rate=True,
            interest_rate=0.0,
            sofr_spread=0.0275,
            sofr_floor=0.0,
            commitment_fee_pct=0.00375,
            subject_to_sweep=False
        ),
        DebtTrancheConfig(
            name="Term Loan A",
            tranche_type=DebtTranche.TERM_LOAN_A,
            principal=1500,
            drawn_at_close=1500,
            term_years=7,
            is_floating_rate=True,
            interest_rate=0.0,
            sofr_spread=0.0300,
            sofr_floor=0.0050,
            annual_amortization_pct=0.10,
            subject_to_sweep=True
        ),
        DebtTrancheConfig(
            name="Term Loan B",
            tranche_type=DebtTranche.TERM_LOAN_B,
            principal=2000,
            drawn_at_close=2000,
            term_years=8,
            is_floating_rate=True,
            interest_rate=0.0,
            sofr_spread=0.0450,
            sofr_floor=0.0075,
            annual_amortization_pct=0.01,
            subject_to_sweep=True,
            prepayment_penalty={1: 0.02, 2: 0.01, 3: 0.00}
        ),
        DebtTrancheConfig(
            name="Senior Notes",
            tranche_type=DebtTranche.SENIOR_NOTES,
            principal=1000,
            drawn_at_close=1000,
            term_years=10,
            is_floating_rate=False,
            interest_rate=0.0650,
            is_bullet=True,
            subject_to_sweep=False,
            prepayment_penalty={1: 999, 2: 0.0325, 3: 0.0163, 4: 0.00}  # 999 = non-call
        )
    ]

    # Cash sweep configuration
    cash_sweep = CashSweepConfig(
        sweep_pct_high_leverage=0.50,
        sweep_pct_mid_leverage=0.25,
        sweep_pct_low_leverage=0.00,
        threshold_high=3.5,
        threshold_mid=2.5,
        capex_reserve=100.0,
        min_cash_balance=200.0
    )

    # SOFR forward curve (assume 4.5% base, slight decline)
    sofr_curve = {
        2024: 0.045,
        2025: 0.044,
        2026: 0.043,
        2027: 0.042,
        2028: 0.041,
        2029: 0.040,
        2030: 0.040,
        2031: 0.040
    }

    # Build complete scenario
    scenario = LBOScenario(
        name="USS LBO - Base Case",
        description="Conservative PE underwriting of USS at $55/share",
        operating_scenario=operating_scenario,
        execution_haircut=0.75,  # 25% haircut on projections
        transaction=transaction,
        debt_tranches=debt_tranches,
        cash_sweep=cash_sweep,
        sofr_forward_curve=sofr_curve
    )

    return scenario


def main():
    """
    Main function demonstrating LBO model usage
    """
    print("USS LBO Model Template")
    print("=" * 80)

    # Build example scenario
    scenario = build_example_scenario()

    # Base financials (current USS balance sheet)
    base_financials = {
        'cash': 3013.9,
        'investments': 761.0,
        'total_debt': 4222.0,
        'pension': 126.0,
        'leases': 117.0
    }

    # Initialize LBO model
    model = LBOModel(scenario, base_financials)

    # Run complete analysis
    results = model.run()

    # Print executive summary
    print("\n" + model.summary_output())

    # Export results to Excel (optional)
    # TODO: Implement Excel export functionality
    # export_to_excel(results, "USS_LBO_Model_Output.xlsx")

    return model, results


if __name__ == "__main__":
    model, results = main()
