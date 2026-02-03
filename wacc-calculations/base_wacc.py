#!/usr/bin/env python3
"""
Base WACC Calculator
====================

Bottom-up WACC calculation using CAPM for cost of equity and
credit spread approach for cost of debt.

WACC = (E/V) * Re + (D/V) * Rd * (1 - T)

Where:
- E = Market value of equity
- D = Market value of debt
- V = E + D (total firm value)
- Re = Cost of equity (from CAPM)
- Rd = Cost of debt (risk-free + credit spread)
- T = Marginal tax rate

Cost of Equity (CAPM):
Re = Rf + Beta * ERP + Size Premium (optional) + Country Premium (optional)

Where:
- Rf = Risk-free rate (10-year government bond)
- Beta = Levered equity beta
- ERP = Equity risk premium
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum
import json
from pathlib import Path


class BetaSource(Enum):
    """Source of beta estimate"""
    BLOOMBERG = "Bloomberg"
    CAPITAL_IQ = "Capital IQ"
    YAHOO_FINANCE = "Yahoo Finance"
    CALCULATED = "Calculated from returns"
    INDUSTRY_AVERAGE = "Industry average"


@dataclass
class WACCInputs:
    """All inputs required for WACC calculation with source tracking"""

    # === REQUIRED FIELDS (no defaults) ===

    # Company identification
    company_name: str
    ticker: str
    currency: str  # Reporting currency (USD, JPY, etc.)

    # Risk-free rate
    risk_free_rate: float  # 10-year government bond yield

    # Equity beta
    levered_beta: float

    # Cost of debt inputs
    pretax_cost_of_debt: float  # Yield on company's debt

    # Capital structure (market values preferred)
    market_cap: float  # Market value of equity ($M or local currency M)
    total_debt: float  # Book value of debt (proxy for market value)

    # Tax rate
    marginal_tax_rate: float

    # === OPTIONAL FIELDS (with defaults) ===

    # Risk-free rate sources
    rf_source: str = ""
    rf_as_of_date: str = ""

    # Beta sources
    beta_source: str = ""
    beta_lookback_period: str = ""  # e.g., "5-year monthly"
    beta_benchmark: str = ""  # e.g., "S&P 500", "TOPIX"
    unlevered_beta: Optional[float] = None

    # Equity risk premium
    equity_risk_premium: float = 0.055  # Default 5.5%
    erp_source: str = "Duff & Phelps"

    # Size premium (for smaller companies)
    size_premium: float = 0.0
    size_premium_source: str = ""

    # Country risk premium (for emerging markets or cross-border)
    country_risk_premium: float = 0.0
    country_premium_source: str = ""

    # Cost of debt sources
    cod_source: str = ""
    credit_spread: Optional[float] = None  # Spread over risk-free
    credit_rating: str = ""

    # Capital structure additional
    cash_and_equivalents: float = 0.0  # For net debt calculations
    market_cap_source: str = ""
    market_cap_as_of_date: str = ""

    # Tax rate source
    tax_rate_source: str = ""

    # Optional: Preferred stock
    preferred_stock: float = 0.0
    preferred_dividend_rate: float = 0.0

    # Metadata
    data_as_of_date: str = ""
    analyst_name: str = ""
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'company_name': self.company_name,
            'ticker': self.ticker,
            'currency': self.currency,
            'risk_free_rate': self.risk_free_rate,
            'rf_source': self.rf_source,
            'rf_as_of_date': self.rf_as_of_date,
            'levered_beta': self.levered_beta,
            'beta_source': self.beta_source,
            'beta_lookback_period': self.beta_lookback_period,
            'beta_benchmark': self.beta_benchmark,
            'unlevered_beta': self.unlevered_beta,
            'equity_risk_premium': self.equity_risk_premium,
            'erp_source': self.erp_source,
            'size_premium': self.size_premium,
            'size_premium_source': self.size_premium_source,
            'country_risk_premium': self.country_risk_premium,
            'country_premium_source': self.country_premium_source,
            'pretax_cost_of_debt': self.pretax_cost_of_debt,
            'cod_source': self.cod_source,
            'credit_spread': self.credit_spread,
            'credit_rating': self.credit_rating,
            'market_cap': self.market_cap,
            'total_debt': self.total_debt,
            'cash_and_equivalents': self.cash_and_equivalents,
            'market_cap_source': self.market_cap_source,
            'market_cap_as_of_date': self.market_cap_as_of_date,
            'marginal_tax_rate': self.marginal_tax_rate,
            'tax_rate_source': self.tax_rate_source,
            'preferred_stock': self.preferred_stock,
            'preferred_dividend_rate': self.preferred_dividend_rate,
            'data_as_of_date': self.data_as_of_date,
            'analyst_name': self.analyst_name,
            'notes': self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WACCInputs':
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, filepath: str) -> 'WACCInputs':
        """Load inputs from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_json(self, filepath: str) -> None:
        """Save inputs to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class WACCResult:
    """WACC calculation results with component breakdown"""

    # Final WACC
    wacc: float

    # Cost of equity components
    cost_of_equity: float
    rf_contribution: float
    beta_erp_contribution: float
    size_premium_contribution: float
    country_premium_contribution: float

    # Cost of debt components
    pretax_cost_of_debt: float
    aftertax_cost_of_debt: float
    tax_shield: float

    # Capital structure weights
    equity_weight: float
    debt_weight: float

    # Enterprise value components
    market_cap: float
    total_debt: float
    enterprise_value: float

    # Optional fields with defaults
    preferred_weight: float = 0.0

    # For cross-border: IRP-adjusted WACC
    irp_adjusted_wacc: Optional[float] = None
    target_currency: Optional[str] = None

    def summary_table(self) -> str:
        """Generate formatted summary table"""
        lines = [
            "=" * 60,
            "WACC CALCULATION SUMMARY",
            "=" * 60,
            "",
            "COST OF EQUITY (CAPM)",
            "-" * 40,
            f"  Risk-free rate:              {self.rf_contribution*100:6.2f}%",
            f"  + Beta x ERP:                {self.beta_erp_contribution*100:6.2f}%",
        ]

        if self.size_premium_contribution > 0:
            lines.append(f"  + Size premium:              {self.size_premium_contribution*100:6.2f}%")

        if self.country_premium_contribution > 0:
            lines.append(f"  + Country premium:           {self.country_premium_contribution*100:6.2f}%")

        lines.extend([
            f"  = Cost of Equity:            {self.cost_of_equity*100:6.2f}%",
            "",
            "COST OF DEBT",
            "-" * 40,
            f"  Pre-tax cost of debt:        {self.pretax_cost_of_debt*100:6.2f}%",
            f"  Tax shield:                  {self.tax_shield*100:6.2f}%",
            f"  = After-tax cost of debt:    {self.aftertax_cost_of_debt*100:6.2f}%",
            "",
            "CAPITAL STRUCTURE",
            "-" * 40,
            f"  Market cap:                  ${self.market_cap:,.0f}M",
            f"  Total debt:                  ${self.total_debt:,.0f}M",
            f"  Enterprise value:            ${self.enterprise_value:,.0f}M",
            f"  Equity weight:               {self.equity_weight*100:6.2f}%",
            f"  Debt weight:                 {self.debt_weight*100:6.2f}%",
            "",
            "WACC",
            "-" * 40,
            f"  Equity component:            {self.equity_weight * self.cost_of_equity * 100:6.2f}%",
            f"  + Debt component:            {self.debt_weight * self.aftertax_cost_of_debt * 100:6.2f}%",
            f"  = WACC:                      {self.wacc*100:6.2f}%",
        ])

        if self.irp_adjusted_wacc is not None:
            lines.extend([
                "",
                f"IRP-ADJUSTED WACC ({self.target_currency})",
                "-" * 40,
                f"  IRP-adjusted WACC:           {self.irp_adjusted_wacc*100:6.2f}%",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)


class WACCCalculator:
    """
    WACC Calculator with full audit trail

    Supports:
    - Standard CAPM-based cost of equity
    - Credit spread approach for cost of debt
    - Interest Rate Parity (IRP) adjustment for cross-border valuations
    - Sensitivity analysis
    """

    def __init__(self, inputs: WACCInputs):
        self.inputs = inputs
        self._result: Optional[WACCResult] = None

    def calculate_cost_of_equity(self) -> Tuple[float, Dict]:
        """
        Calculate cost of equity using CAPM

        Re = Rf + Beta * ERP + Size Premium + Country Premium

        Returns:
            Tuple of (cost_of_equity, component_breakdown)
        """
        inp = self.inputs

        # Base CAPM
        rf = inp.risk_free_rate
        beta_erp = inp.levered_beta * inp.equity_risk_premium

        # Additional premiums
        size = inp.size_premium
        country = inp.country_risk_premium

        cost_of_equity = rf + beta_erp + size + country

        components = {
            'risk_free_rate': rf,
            'beta': inp.levered_beta,
            'equity_risk_premium': inp.equity_risk_premium,
            'beta_erp_contribution': beta_erp,
            'size_premium': size,
            'country_premium': country,
            'cost_of_equity': cost_of_equity,
        }

        return cost_of_equity, components

    def calculate_cost_of_debt(self) -> Tuple[float, Dict]:
        """
        Calculate after-tax cost of debt

        Rd_aftertax = Rd_pretax * (1 - T)

        Returns:
            Tuple of (aftertax_cost_of_debt, component_breakdown)
        """
        inp = self.inputs

        pretax = inp.pretax_cost_of_debt
        tax_rate = inp.marginal_tax_rate
        tax_shield = pretax * tax_rate
        aftertax = pretax * (1 - tax_rate)

        components = {
            'pretax_cost_of_debt': pretax,
            'tax_rate': tax_rate,
            'tax_shield': tax_shield,
            'aftertax_cost_of_debt': aftertax,
        }

        return aftertax, components

    def calculate_capital_weights(self) -> Tuple[float, float, float, Dict]:
        """
        Calculate capital structure weights

        Uses market value of equity and book value of debt
        (book debt is reasonable proxy for market value for most companies)

        Returns:
            Tuple of (equity_weight, debt_weight, preferred_weight, details)
        """
        inp = self.inputs

        equity = inp.market_cap
        debt = inp.total_debt
        preferred = inp.preferred_stock

        total = equity + debt + preferred

        equity_weight = equity / total if total > 0 else 0
        debt_weight = debt / total if total > 0 else 0
        preferred_weight = preferred / total if total > 0 else 0

        details = {
            'market_cap': equity,
            'total_debt': debt,
            'preferred_stock': preferred,
            'enterprise_value': total,
            'equity_weight': equity_weight,
            'debt_weight': debt_weight,
            'preferred_weight': preferred_weight,
        }

        return equity_weight, debt_weight, preferred_weight, details

    def calculate(self) -> WACCResult:
        """
        Calculate WACC with full component breakdown

        WACC = (E/V) * Re + (D/V) * Rd * (1-T) + (P/V) * Rp
        """
        # Cost of equity
        cost_of_equity, equity_components = self.calculate_cost_of_equity()

        # Cost of debt
        aftertax_cod, debt_components = self.calculate_cost_of_debt()

        # Capital weights
        e_weight, d_weight, p_weight, cap_details = self.calculate_capital_weights()

        # Cost of preferred (if any)
        cost_of_preferred = self.inputs.preferred_dividend_rate

        # WACC calculation
        wacc = (
            e_weight * cost_of_equity +
            d_weight * aftertax_cod +
            p_weight * cost_of_preferred
        )

        self._result = WACCResult(
            wacc=wacc,
            cost_of_equity=cost_of_equity,
            rf_contribution=equity_components['risk_free_rate'],
            beta_erp_contribution=equity_components['beta_erp_contribution'],
            size_premium_contribution=equity_components['size_premium'],
            country_premium_contribution=equity_components['country_premium'],
            pretax_cost_of_debt=debt_components['pretax_cost_of_debt'],
            aftertax_cost_of_debt=debt_components['aftertax_cost_of_debt'],
            tax_shield=debt_components['tax_shield'],
            equity_weight=e_weight,
            debt_weight=d_weight,
            preferred_weight=p_weight,
            market_cap=cap_details['market_cap'],
            total_debt=cap_details['total_debt'],
            enterprise_value=cap_details['enterprise_value'],
        )

        return self._result

    def apply_irp_adjustment(self,
                             domestic_rf: float,
                             foreign_rf: float,
                             target_currency: str) -> float:
        """
        Apply Interest Rate Parity adjustment for cross-border valuation

        IRP Formula:
        WACC_foreign = (1 + WACC_domestic) * (1 + Rf_foreign) / (1 + Rf_domestic) - 1

        This converts a domestic currency WACC to a foreign currency WACC
        while maintaining economic equivalence.

        Args:
            domestic_rf: Risk-free rate in domestic currency
            foreign_rf: Risk-free rate in target currency
            target_currency: Target currency code (e.g., "USD")

        Returns:
            IRP-adjusted WACC in target currency
        """
        if self._result is None:
            self.calculate()

        domestic_wacc = self._result.wacc

        # IRP adjustment
        irp_wacc = (1 + domestic_wacc) * (1 + foreign_rf) / (1 + domestic_rf) - 1

        self._result.irp_adjusted_wacc = irp_wacc
        self._result.target_currency = target_currency

        return irp_wacc

    def sensitivity_analysis(self,
                            parameter: str,
                            values: list) -> Dict[float, float]:
        """
        Run sensitivity analysis on a single parameter

        Args:
            parameter: Name of WACCInputs attribute to vary
            values: List of values to test

        Returns:
            Dict mapping parameter values to resulting WACC
        """
        original_value = getattr(self.inputs, parameter)
        results = {}

        for val in values:
            setattr(self.inputs, parameter, val)
            result = self.calculate()
            results[val] = result.wacc

        # Restore original
        setattr(self.inputs, parameter, original_value)
        self.calculate()

        return results

    def unlever_beta(self, levered_beta: float, debt: float,
                     equity: float, tax_rate: float) -> float:
        """
        Unlever beta using Hamada equation

        Beta_unlevered = Beta_levered / (1 + (1-T) * D/E)
        """
        if equity <= 0:
            return levered_beta

        de_ratio = debt / equity
        unlevered = levered_beta / (1 + (1 - tax_rate) * de_ratio)
        return unlevered

    def relever_beta(self, unlevered_beta: float, debt: float,
                     equity: float, tax_rate: float) -> float:
        """
        Relever beta using Hamada equation

        Beta_levered = Beta_unlevered * (1 + (1-T) * D/E)
        """
        if equity <= 0:
            return unlevered_beta

        de_ratio = debt / equity
        levered = unlevered_beta * (1 + (1 - tax_rate) * de_ratio)
        return levered


def calculate_wacc_from_inputs(inputs: WACCInputs) -> WACCResult:
    """Convenience function to calculate WACC from inputs"""
    calculator = WACCCalculator(inputs)
    return calculator.calculate()


# =============================================================================
# CLI / Testing
# =============================================================================

if __name__ == '__main__':
    # Example: Generic steel company
    example_inputs = WACCInputs(
        company_name="Example Steel Co",
        ticker="XST",
        currency="USD",
        risk_free_rate=0.0425,  # 4.25% 10-year Treasury
        rf_source="Federal Reserve",
        levered_beta=1.35,
        beta_source="Bloomberg",
        beta_lookback_period="5-year monthly",
        beta_benchmark="S&P 500",
        equity_risk_premium=0.055,  # 5.5%
        erp_source="Duff & Phelps 2024",
        pretax_cost_of_debt=0.065,  # 6.5%
        cod_source="Company 10-K, weighted avg",
        credit_rating="BB+",
        market_cap=8000,  # $8B
        total_debt=4500,  # $4.5B
        marginal_tax_rate=0.25,
        tax_rate_source="Statutory US federal + state",
        data_as_of_date="2024-12-31",
    )

    calculator = WACCCalculator(example_inputs)
    result = calculator.calculate()

    print(result.summary_table())

    # Sensitivity analysis
    print("\nBeta Sensitivity:")
    beta_sensitivity = calculator.sensitivity_analysis(
        'levered_beta',
        [1.0, 1.2, 1.35, 1.5, 1.7]
    )
    for beta, wacc in beta_sensitivity.items():
        print(f"  Beta {beta:.2f}: WACC {wacc*100:.2f}%")
