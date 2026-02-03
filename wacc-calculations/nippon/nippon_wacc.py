#!/usr/bin/env python3
"""
Nippon Steel WACC Calculator
============================

Calculates Nippon Steel's cost of capital with:
1. JPY-denominated WACC using Japanese market inputs
2. IRP adjustment to USD for comparison with USS valuation

All inputs are loaded from inputs.json for auditability and verification.

Key Considerations:
- Japanese risk-free rate (JGB 10-year) is significantly lower than US Treasury
- Nippon has investment-grade credit (BBB+/Baa1) with low borrowing costs
- IRP adjustment accounts for interest rate differential
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_wacc import WACCInputs, WACCResult, WACCCalculator


# =============================================================================
# LOAD INPUTS FROM JSON (Single Source of Truth)
# =============================================================================

def _get_inputs_path() -> Path:
    """Get path to inputs.json file"""
    return Path(__file__).parent / "inputs.json"


def load_nippon_inputs() -> Dict:
    """
    Load Nippon WACC inputs from inputs.json

    This is the SINGLE SOURCE OF TRUTH for all Nippon WACC inputs.
    All values should be verified against this file.
    """
    inputs_path = _get_inputs_path()
    if not inputs_path.exists():
        raise FileNotFoundError(f"Nippon inputs file not found: {inputs_path}")

    with open(inputs_path, 'r') as f:
        return json.load(f)


# Load inputs at module level for convenience
_INPUTS = None

def _get_inputs() -> Dict:
    """Lazy load inputs"""
    global _INPUTS
    if _INPUTS is None:
        _INPUTS = load_nippon_inputs()
    return _INPUTS


# =============================================================================
# CONVENIENCE ACCESSORS (all read from inputs.json)
# =============================================================================

def get_risk_free_rate() -> Tuple[float, Dict]:
    """Get JGB 10-year yield with full metadata"""
    inputs = _get_inputs()
    rf_data = inputs['risk_free_rate']
    return rf_data['value'], rf_data


def get_us_risk_free_rate() -> Tuple[float, Dict]:
    """Get US Treasury 10-year yield for IRP adjustment"""
    inputs = _get_inputs()
    irp_data = inputs['irp_adjustment']
    return irp_data['us_10y_treasury'], irp_data


def get_beta() -> Tuple[float, Dict]:
    """Get levered beta with full metadata"""
    inputs = _get_inputs()
    beta_data = inputs['equity_beta']
    return beta_data['levered_beta'], beta_data


def get_equity_risk_premium() -> Tuple[float, Dict]:
    """Get Japan ERP with full metadata"""
    inputs = _get_inputs()
    erp_data = inputs['equity_risk_premium']
    return erp_data['value'], erp_data


def get_cost_of_debt() -> Tuple[float, Dict]:
    """Get pre-tax cost of debt with full metadata"""
    inputs = _get_inputs()
    cod_data = inputs['cost_of_debt']
    return cod_data['pretax_rate'], cod_data


def get_capital_structure() -> Dict:
    """Get capital structure data"""
    inputs = _get_inputs()
    return inputs['capital_structure']


def get_tax_rate() -> Tuple[float, Dict]:
    """Get Japan marginal tax rate with full metadata"""
    inputs = _get_inputs()
    tax_data = inputs['tax_rate']
    return tax_data['marginal_rate'], tax_data


def get_data_as_of_date() -> str:
    """Get the as-of date for all inputs"""
    inputs = _get_inputs()
    return inputs.get('_data_as_of_date', 'Unknown')


def get_verification_checklist() -> Dict:
    """Get verification checklist"""
    inputs = _get_inputs()
    return inputs.get('verification_checklist', {})


# =============================================================================
# NIPPON WACC RESULT CLASS
# =============================================================================

@dataclass
class NipponWACCResult:
    """Extended WACC result for Nippon with JPY and USD views"""

    # JPY WACC
    jpy_wacc: float
    jpy_cost_of_equity: float
    jpy_cost_of_debt_aftertax: float

    # USD WACC (IRP-adjusted)
    usd_wacc: float

    # Components
    equity_weight: float
    debt_weight: float
    levered_beta: float

    # Capital structure
    market_cap_usd: float
    total_debt_usd: float
    enterprise_value_usd: float

    # Reference rates
    jgb_10y: float
    us_10y: float
    irp_differential: float

    # Input sources (for audit trail)
    input_sources: Dict[str, str]
    data_as_of_date: str

    # Full result object
    base_result: WACCResult

    def summary(self) -> str:
        """Generate summary output"""
        inputs = _get_inputs()
        erp_val, _ = get_equity_risk_premium()
        cod_val, cod_meta = get_cost_of_debt()
        tax_val, _ = get_tax_rate()

        lines = [
            "=" * 65,
            f"NIPPON STEEL WACC CALCULATION",
            f"Data As Of: {self.data_as_of_date}",
            "=" * 65,
            "",
            "JAPANESE MARKET INPUTS",
            "-" * 45,
            f"  10-Year JGB Yield:           {self.jgb_10y*100:6.3f}%",
            f"    Source: {self.input_sources.get('risk_free_rate', 'inputs.json')}",
            f"  10-Year US Treasury:         {self.us_10y*100:6.3f}%",
            f"    Source: {self.input_sources.get('us_10y', 'inputs.json')}",
            f"  Rate Differential:           {(self.us_10y - self.jgb_10y)*100:6.3f}%",
            "",
            "COST OF EQUITY (JPY)",
            "-" * 45,
            f"  Risk-free (JGB):             {self.jgb_10y*100:6.3f}%",
            f"  Beta:                        {self.levered_beta:6.2f}",
            f"    Source: {self.input_sources.get('beta', 'inputs.json')}",
            f"  Equity Risk Premium:         {erp_val*100:6.2f}%",
            f"    Source: {self.input_sources.get('erp', 'inputs.json')}",
            f"  Beta x ERP:                  {(self.levered_beta * erp_val)*100:6.2f}%",
            f"  = Cost of Equity (JPY):      {self.jpy_cost_of_equity*100:6.2f}%",
            "",
            "COST OF DEBT (JPY)",
            "-" * 45,
            f"  Pre-tax Cost of Debt:        {cod_val*100:6.3f}%",
            f"    Source: {self.input_sources.get('cost_of_debt', 'inputs.json')}",
            f"  Tax Rate:                    {tax_val*100:6.2f}%",
            f"  = After-tax Cost of Debt:    {self.jpy_cost_of_debt_aftertax*100:6.3f}%",
            "",
            "CAPITAL STRUCTURE",
            "-" * 45,
            f"  Market Cap:                  ${self.market_cap_usd/1000:,.1f}B",
            f"  Total Debt:                  ${self.total_debt_usd/1000:,.1f}B",
            f"  Enterprise Value:            ${self.enterprise_value_usd/1000:,.1f}B",
            f"    Source: {self.input_sources.get('capital_structure', 'inputs.json')}",
            f"  Equity Weight:               {self.equity_weight*100:6.2f}%",
            f"  Debt Weight:                 {self.debt_weight*100:6.2f}%",
            "",
            "WACC CALCULATION",
            "-" * 45,
            f"  JPY WACC:                    {self.jpy_wacc*100:6.2f}%",
            "",
            "IRP ADJUSTMENT TO USD",
            "-" * 45,
            f"  Formula: (1 + WACC_JPY) x (1 + Rf_USD) / (1 + Rf_JPY) - 1",
            f"  = (1 + {self.jpy_wacc*100:.2f}%) x (1 + {self.us_10y*100:.2f}%) / (1 + {self.jgb_10y*100:.3f}%) - 1",
            f"  = USD WACC:                  {self.usd_wacc*100:6.2f}%",
            "",
            "=" * 65,
            f"NIPPON STEEL USD WACC:         {self.usd_wacc*100:.2f}%",
            "=" * 65,
            "",
            "Input file: wacc-calculations/nippon/inputs.json",
        ]
        return "\n".join(lines)

    def get_audit_trail(self) -> Dict:
        """Get full audit trail of inputs and sources"""
        return {
            'data_as_of_date': self.data_as_of_date,
            'calculated_jpy_wacc': self.jpy_wacc,
            'calculated_usd_wacc': self.usd_wacc,
            'inputs': self.input_sources,
        }


# =============================================================================
# WACC CALCULATOR
# =============================================================================

def get_nippon_wacc_inputs(
    jgb_10y: Optional[float] = None,
    us_10y: Optional[float] = None,
    levered_beta: Optional[float] = None,
    erp: Optional[float] = None,
    credit_spread: Optional[float] = None,
    market_cap_usd: Optional[float] = None,
    total_debt_usd: Optional[float] = None,
    tax_rate: Optional[float] = None,
) -> Tuple[WACCInputs, Dict[str, str], float]:
    """
    Get Nippon WACC inputs - loads from inputs.json with optional overrides

    All parameters default to values from inputs.json.
    Override parameters only for sensitivity analysis.

    Returns:
        Tuple of (WACCInputs, sources_dict, us_10y_rate)
    """
    # Load from JSON
    rf_val, rf_meta = get_risk_free_rate()
    us_rf_val, us_rf_meta = get_us_risk_free_rate()
    beta_val, beta_meta = get_beta()
    erp_val, erp_meta = get_equity_risk_premium()
    cod_val, cod_meta = get_cost_of_debt()
    cap_struct = get_capital_structure()
    tax_val, tax_meta = get_tax_rate()

    # Use JSON values unless overridden
    final_rf = jgb_10y if jgb_10y is not None else rf_val
    final_us_rf = us_10y if us_10y is not None else us_rf_val
    final_beta = levered_beta if levered_beta is not None else beta_val
    final_erp = erp if erp is not None else erp_val
    final_spread = credit_spread if credit_spread is not None else cod_meta.get('credit_spread', 0.008)
    final_mc = market_cap_usd if market_cap_usd is not None else cap_struct['market_cap_usd_millions']
    final_debt = total_debt_usd if total_debt_usd is not None else cap_struct['total_debt_usd_millions']
    final_tax = tax_rate if tax_rate is not None else tax_val

    # Track sources
    sources = {
        'risk_free_rate': rf_meta.get('source', 'inputs.json') if jgb_10y is None else 'Override',
        'us_10y': us_rf_meta.get('us_10y_source', 'inputs.json') if us_10y is None else 'Override',
        'beta': f"{beta_meta.get('source', 'inputs.json')} vs {beta_meta.get('benchmark', 'TOPIX')}" if levered_beta is None else 'Override',
        'erp': erp_meta.get('source', 'inputs.json') if erp is None else 'Override',
        'cost_of_debt': cod_meta.get('calculation', 'inputs.json') if credit_spread is None else 'Override',
        'capital_structure': cap_struct.get('source', 'inputs.json') if market_cap_usd is None else 'Override',
        'tax_rate': tax_meta.get('source', 'inputs.json') if tax_rate is None else 'Override',
    }

    inputs = WACCInputs(
        company_name="Nippon Steel Corporation",
        ticker="5401.T / NISTF",
        currency="JPY",

        # Risk-free rate (JGB)
        risk_free_rate=final_rf,
        rf_source=rf_meta.get('source', ''),
        rf_as_of_date=rf_meta.get('as_of_date', ''),

        # Beta
        levered_beta=final_beta,
        beta_source=beta_meta.get('source', ''),
        beta_lookback_period=beta_meta.get('lookback_period', ''),
        beta_benchmark=beta_meta.get('benchmark', 'TOPIX'),

        # Equity risk premium
        equity_risk_premium=final_erp,
        erp_source=erp_meta.get('source', ''),

        # Cost of debt
        pretax_cost_of_debt=final_rf + final_spread,
        cod_source="JGB + credit spread",
        credit_spread=final_spread,
        credit_rating=f"{cod_meta.get('credit_rating', {}).get('sp', 'BBB+')}",

        # Capital structure (in USD millions for consistency)
        market_cap=final_mc,
        total_debt=final_debt,
        cash_and_equivalents=cap_struct.get('cash_usd_millions', 0),
        market_cap_source=cap_struct.get('source', ''),
        market_cap_as_of_date=cap_struct.get('as_of_date', ''),

        # Tax rate
        marginal_tax_rate=final_tax,
        tax_rate_source=tax_meta.get('source', ''),

        # Metadata
        data_as_of_date=get_data_as_of_date(),
        notes=f"Nippon Steel inputs loaded from inputs.json. Data as of {get_data_as_of_date()}.",
    )

    return inputs, sources, final_us_rf


class NipponWACCCalculator:
    """
    Nippon Steel specific WACC calculator

    Loads all inputs from inputs.json for auditability.
    Calculates both JPY WACC and IRP-adjusted USD WACC.
    """

    def __init__(self, **overrides):
        """
        Initialize calculator

        Args:
            **overrides: Override any input (jgb_10y, levered_beta, etc.)
                        Only use for sensitivity analysis
        """
        self.inputs, self.sources, self.us_10y = get_nippon_wacc_inputs(**overrides)
        self.jgb_10y = self.inputs.risk_free_rate
        self.base_calculator = WACCCalculator(self.inputs)
        self.overrides = overrides

    def calculate(self) -> NipponWACCResult:
        """
        Calculate Nippon WACC in JPY and USD

        Returns NipponWACCResult with both currency views and audit trail
        """
        # Calculate base JPY WACC
        base_result = self.base_calculator.calculate()
        jpy_wacc = base_result.wacc

        # Apply IRP adjustment to get USD WACC
        usd_wacc = self.base_calculator.apply_irp_adjustment(
            domestic_rf=self.jgb_10y,
            foreign_rf=self.us_10y,
            target_currency="USD"
        )

        return NipponWACCResult(
            jpy_wacc=jpy_wacc,
            jpy_cost_of_equity=base_result.cost_of_equity,
            jpy_cost_of_debt_aftertax=base_result.aftertax_cost_of_debt,
            usd_wacc=usd_wacc,
            equity_weight=base_result.equity_weight,
            debt_weight=base_result.debt_weight,
            levered_beta=self.inputs.levered_beta,
            market_cap_usd=base_result.market_cap,
            total_debt_usd=base_result.total_debt,
            enterprise_value_usd=base_result.enterprise_value,
            jgb_10y=self.jgb_10y,
            us_10y=self.us_10y,
            irp_differential=self.us_10y - self.jgb_10y,
            input_sources=self.sources,
            data_as_of_date=get_data_as_of_date(),
            base_result=base_result,
        )

    def sensitivity_to_jgb(self, jgb_values: list) -> Dict[float, Tuple[float, float]]:
        """
        Sensitivity of JPY and USD WACC to JGB yield changes

        Returns dict mapping JGB yield to (JPY WACC, USD WACC)
        """
        results = {}
        for jgb in jgb_values:
            calc = NipponWACCCalculator(jgb_10y=jgb)
            result = calc.calculate()
            results[jgb] = (result.jpy_wacc, result.usd_wacc)
        return results

    def sensitivity_to_beta(self, beta_values: list) -> Dict[float, Tuple[float, float]]:
        """
        Sensitivity of WACC to beta changes

        Returns dict mapping beta to (JPY WACC, USD WACC)
        """
        results = {}
        for beta in beta_values:
            calc = NipponWACCCalculator(levered_beta=beta)
            result = calc.calculate()
            results[beta] = (result.jpy_wacc, result.usd_wacc)
        return results


def calculate_nippon_wacc(**kwargs) -> NipponWACCResult:
    """
    Convenience function to calculate Nippon WACC

    Args:
        **kwargs: Override any input parameters (for sensitivity analysis only)

    Returns:
        NipponWACCResult with JPY and USD WACC and audit trail
    """
    calc = NipponWACCCalculator(**kwargs)
    return calc.calculate()


def print_input_sources():
    """Print all input sources for verification"""
    inputs = _get_inputs()

    print("=" * 70)
    print("NIPPON STEEL WACC INPUT SOURCES")
    print(f"Data As Of: {inputs.get('_data_as_of_date', 'Unknown')}")
    print("=" * 70)

    print("\nJGB 10-Year Yield:")
    rf = inputs['risk_free_rate']
    print(f"  Value: {rf['value']*100:.3f}%")
    print(f"  Source: {rf['source']}")
    print(f"  URL: {rf.get('url', 'N/A')}")

    print("\nUS 10-Year Treasury (for IRP):")
    irp = inputs['irp_adjustment']
    print(f"  Value: {irp['us_10y_treasury']*100:.2f}%")
    print(f"  Source: {irp['us_10y_source']}")

    print("\nEquity Beta:")
    beta = inputs['equity_beta']
    print(f"  Value: {beta['levered_beta']}")
    print(f"  Source: {beta['source']}")
    print(f"  Benchmark: {beta['benchmark']}")
    print(f"  Period: {beta['lookback_period']}")

    print("\nEquity Risk Premium:")
    erp = inputs['equity_risk_premium']
    print(f"  Value: {erp['value']*100:.1f}%")
    print(f"  Source: {erp['source']}")

    print("\nCost of Debt:")
    cod = inputs['cost_of_debt']
    print(f"  Pre-tax Rate: {cod['pretax_rate']*100:.3f}%")
    print(f"  Calculation: {cod['calculation']}")
    cr = cod['credit_rating']
    print(f"  Credit Rating: {cr['sp']} / {cr['moodys']} / {cr['fitch']}")

    print("\nCapital Structure:")
    cap = inputs['capital_structure']
    print(f"  Stock Price: ¥{cap['stock_price_jpy']:,} (on {cap['stock_price_date']})")
    print(f"  Market Cap: ${cap['market_cap_usd_millions']:,}M")
    print(f"  Total Debt: ${cap['total_debt_usd_millions']:,}M")
    print(f"  FX Rate: {cap['fx_rate_jpy_usd']} JPY/USD")
    print(f"  Source: {cap['source']}")

    print("\nVerification Checklist:")
    checklist = inputs.get('verification_checklist', {})
    for item in checklist.get('items', []):
        status = item.get('status', 'unknown')
        print(f"  [{status}] {item['item']}")
        print(f"           Expected: {item['expected_value']}")


# =============================================================================
# CLI / Testing
# =============================================================================

if __name__ == '__main__':
    print("Calculating Nippon Steel WACC from inputs.json...\n")

    # Print input sources first
    print_input_sources()
    print()

    # Default calculation
    result = calculate_nippon_wacc()
    print(result.summary())

    # Sensitivity analysis
    print("\n" + "=" * 65)
    print("SENSITIVITY ANALYSIS")
    print("=" * 65)

    calc = NipponWACCCalculator()

    print("\nJGB Yield Sensitivity:")
    print("-" * 45)
    jgb_sensitivity = calc.sensitivity_to_jgb([0.003, 0.0061, 0.01, 0.015, 0.02])
    for jgb, (jpy_wacc, usd_wacc) in jgb_sensitivity.items():
        print(f"  JGB {jgb*100:.2f}%: JPY WACC {jpy_wacc*100:.2f}%, USD WACC {usd_wacc*100:.2f}%")

    print("\nBeta Sensitivity:")
    print("-" * 45)
    beta_sensitivity = calc.sensitivity_to_beta([0.9, 1.0, 1.15, 1.3, 1.5])
    for beta, (jpy_wacc, usd_wacc) in beta_sensitivity.items():
        print(f"  Beta {beta:.2f}: JPY WACC {jpy_wacc*100:.2f}%, USD WACC {usd_wacc*100:.2f}%")
