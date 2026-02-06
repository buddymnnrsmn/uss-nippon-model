#!/usr/bin/env python3
"""
USS (United States Steel Corporation) WACC Calculator
=====================================================

Calculates USS's weighted average cost of capital using:
1. CAPM for cost of equity
2. Yield-to-maturity approach for cost of debt
3. Market value capital structure weights

All inputs are loaded from inputs.json for auditability and verification.

Key Considerations:
- USS is a cyclical integrated steel producer
- Higher beta than market (steel industry cyclicality)
- Below investment grade credit (BB/Ba2) = higher cost of debt
- Significant operating leverage amplifies earnings volatility

Verification Priority:
1. Compare to analyst estimates in merger proxy (Barclays, Goldman)
2. Cross-check beta with peer companies (CLF, NUE, STLD)
3. Verify cost of debt against actual bond yields
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_wacc import WACCInputs, WACCResult, WACCCalculator


# =============================================================================
# LOAD INPUTS FROM JSON (Single Source of Truth)
# =============================================================================

def _get_inputs_path() -> Path:
    """Get path to inputs.json file"""
    return Path(__file__).parent / "inputs.json"


def load_uss_inputs() -> Dict:
    """
    Load USS WACC inputs from inputs.json

    This is the SINGLE SOURCE OF TRUTH for all USS WACC inputs.
    All values should be verified against this file.
    """
    inputs_path = _get_inputs_path()
    if not inputs_path.exists():
        raise FileNotFoundError(f"USS inputs file not found: {inputs_path}")

    with open(inputs_path, 'r') as f:
        return json.load(f)


def get_input_with_source(inputs: Dict, *keys) -> Tuple[any, str]:
    """
    Get an input value along with its source documentation

    Args:
        inputs: The loaded inputs dict
        *keys: Path to the value (e.g., 'risk_free_rate', 'value')

    Returns:
        Tuple of (value, source_description)
    """
    current = inputs
    for key in keys[:-1]:
        current = current[key]

    value = current[keys[-1]]
    source = current.get('source', 'See inputs.json')

    return value, source


# Load inputs at module level for convenience
_INPUTS = None

def _get_inputs() -> Dict:
    """Lazy load inputs"""
    global _INPUTS
    if _INPUTS is None:
        _INPUTS = load_uss_inputs()
    return _INPUTS


# =============================================================================
# CONVENIENCE ACCESSORS (all read from inputs.json)
# =============================================================================

def get_risk_free_rate() -> Tuple[float, Dict]:
    """Get risk-free rate with full metadata"""
    inputs = _get_inputs()
    rf_data = inputs['risk_free_rate']
    return rf_data['value'], rf_data


def get_beta() -> Tuple[float, Dict]:
    """Get levered beta with full metadata"""
    inputs = _get_inputs()
    beta_data = inputs['equity_beta']
    return beta_data['levered_beta'], beta_data


def get_equity_risk_premium() -> Tuple[float, Dict]:
    """Get ERP with full metadata"""
    inputs = _get_inputs()
    erp_data = inputs['equity_risk_premium']
    return erp_data['value'], erp_data


def get_size_premium() -> Tuple[float, Dict]:
    """Get size premium with full metadata"""
    inputs = _get_inputs()
    size_data = inputs['size_premium']
    return size_data['value'], size_data


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
    """Get marginal tax rate with full metadata"""
    inputs = _get_inputs()
    tax_data = inputs['tax_rate']
    return tax_data['marginal_rate'], tax_data


def get_analyst_estimates() -> Dict:
    """Get analyst WACC estimates for comparison"""
    inputs = _get_inputs()
    return inputs.get('analyst_wacc_estimates', {})


def get_verification_checklist() -> Dict:
    """Get verification checklist"""
    inputs = _get_inputs()
    return inputs.get('verification_checklist', {})


def get_data_as_of_date() -> str:
    """Get the as-of date for all inputs"""
    inputs = _get_inputs()
    return inputs.get('_data_as_of_date', 'Unknown')


# =============================================================================
# USS WACC RESULT CLASS
# =============================================================================

@dataclass
class USSWACCResult:
    """Extended WACC result for USS with comparison to analyst estimates"""

    # WACC
    wacc: float
    cost_of_equity: float
    cost_of_debt_aftertax: float

    # Components
    risk_free_rate: float
    levered_beta: float
    equity_risk_premium: float
    size_premium: float
    credit_spread: float

    # Capital structure
    equity_weight: float
    debt_weight: float
    market_cap: float
    total_debt: float
    enterprise_value: float

    # Comparison
    analyst_comparison: Dict[str, Dict]

    # Input sources (for audit trail)
    input_sources: Dict[str, str]
    data_as_of_date: str

    # Full result object
    base_result: WACCResult

    def summary(self) -> str:
        """Generate summary output"""
        lines = [
            "=" * 65,
            f"USS (UNITED STATES STEEL) WACC CALCULATION",
            f"Data As Of: {self.data_as_of_date}",
            "=" * 65,
            "",
            "COST OF EQUITY (CAPM)",
            "-" * 45,
            f"  Risk-free rate (10Y UST):    {self.risk_free_rate*100:6.2f}%",
            f"    Source: {self.input_sources.get('risk_free_rate', 'inputs.json')}",
            f"  Levered Beta:                {self.levered_beta:6.2f}",
            f"    Source: {self.input_sources.get('beta', 'inputs.json')}",
            f"  Equity Risk Premium:         {self.equity_risk_premium*100:6.2f}%",
            f"    Source: {self.input_sources.get('erp', 'inputs.json')}",
            f"  Beta x ERP:                  {(self.levered_beta * self.equity_risk_premium)*100:6.2f}%",
            f"  Size Premium:                {self.size_premium*100:6.2f}%",
            f"    Source: {self.input_sources.get('size_premium', 'inputs.json')}",
            f"  = Cost of Equity:            {self.cost_of_equity*100:6.2f}%",
            "",
            "COST OF DEBT",
            "-" * 45,
            f"  Risk-free rate:              {self.risk_free_rate*100:6.2f}%",
            f"  Credit spread:               {self.credit_spread*100:6.2f}%",
            f"  Pre-tax Cost of Debt:        {(self.risk_free_rate + self.credit_spread)*100:6.2f}%",
            f"    Source: {self.input_sources.get('cost_of_debt', 'inputs.json')}",
            f"  Tax Rate:                    {self.base_result.tax_shield / self.base_result.pretax_cost_of_debt * 100 if self.base_result.pretax_cost_of_debt > 0 else 0:6.2f}%",
            f"  = After-tax Cost of Debt:    {self.cost_of_debt_aftertax*100:6.2f}%",
            "",
            "CAPITAL STRUCTURE",
            "-" * 45,
            f"  Market Cap:                  ${self.market_cap:,.0f}M",
            f"  Total Debt:                  ${self.total_debt:,.0f}M",
            f"  Enterprise Value:            ${self.enterprise_value:,.0f}M",
            f"    Source: {self.input_sources.get('capital_structure', 'inputs.json')}",
            f"  Equity Weight:               {self.equity_weight*100:6.2f}%",
            f"  Debt Weight:                 {self.debt_weight*100:6.2f}%",
            "",
            "WACC CALCULATION",
            "-" * 45,
            f"  Equity component:            {(self.equity_weight * self.cost_of_equity)*100:6.2f}%",
            f"  + Debt component:            {(self.debt_weight * self.cost_of_debt_aftertax)*100:6.2f}%",
            f"  = WACC:                      {self.wacc*100:6.2f}%",
            "",
            "COMPARISON TO ANALYST ESTIMATES",
            "-" * 45,
        ]

        for analyst, data in self.analyst_comparison.items():
            mid = data.get('wacc_midpoint', data.get('wacc_mid', 0))
            if mid > 0:
                diff = (self.wacc - mid) * 100
                diff_str = f"+{diff:.1f}%" if diff > 0 else f"{diff:.1f}%"
                lines.append(f"  {analyst:25s} {mid*100:.1f}% ({diff_str})")

        lines.extend([
            "",
            "=" * 65,
            f"USS WACC:                      {self.wacc*100:.2f}%",
            "=" * 65,
            "",
            "Input file: wacc-calculations/uss/inputs.json",
        ])

        return "\n".join(lines)

    def get_audit_trail(self) -> Dict:
        """Get full audit trail of inputs and sources"""
        return {
            'data_as_of_date': self.data_as_of_date,
            'calculated_wacc': self.wacc,
            'inputs': {
                'risk_free_rate': {
                    'value': self.risk_free_rate,
                    'source': self.input_sources.get('risk_free_rate'),
                },
                'levered_beta': {
                    'value': self.levered_beta,
                    'source': self.input_sources.get('beta'),
                },
                'equity_risk_premium': {
                    'value': self.equity_risk_premium,
                    'source': self.input_sources.get('erp'),
                },
                'size_premium': {
                    'value': self.size_premium,
                    'source': self.input_sources.get('size_premium'),
                },
                'pretax_cost_of_debt': {
                    'value': self.risk_free_rate + self.credit_spread,
                    'source': self.input_sources.get('cost_of_debt'),
                },
                'market_cap': {
                    'value': self.market_cap,
                    'source': self.input_sources.get('capital_structure'),
                },
                'total_debt': {
                    'value': self.total_debt,
                    'source': self.input_sources.get('capital_structure'),
                },
            },
            'analyst_comparison': self.analyst_comparison,
        }


# =============================================================================
# WACC CALCULATOR
# =============================================================================

def get_uss_wacc_inputs(
    us_10y: Optional[float] = None,
    levered_beta: Optional[float] = None,
    erp: Optional[float] = None,
    size_premium: Optional[float] = None,
    pretax_cod: Optional[float] = None,
    market_cap: Optional[float] = None,
    total_debt: Optional[float] = None,
    tax_rate: Optional[float] = None,
) -> Tuple[WACCInputs, Dict[str, str]]:
    """
    Get USS WACC inputs - loads from inputs.json with optional overrides

    All parameters default to values from inputs.json.
    Override parameters only for sensitivity analysis.

    Returns:
        Tuple of (WACCInputs, sources_dict)
    """
    # Load from JSON
    rf_val, rf_meta = get_risk_free_rate()
    beta_val, beta_meta = get_beta()
    erp_val, erp_meta = get_equity_risk_premium()
    size_val, size_meta = get_size_premium()
    cod_val, cod_meta = get_cost_of_debt()
    cap_struct = get_capital_structure()
    tax_val, tax_meta = get_tax_rate()

    # Use JSON values unless overridden
    final_rf = us_10y if us_10y is not None else rf_val
    final_beta = levered_beta if levered_beta is not None else beta_val
    final_erp = erp if erp is not None else erp_val
    final_size = size_premium if size_premium is not None else size_val
    final_cod = pretax_cod if pretax_cod is not None else cod_val
    final_mc = market_cap if market_cap is not None else cap_struct['market_cap_mm']
    final_debt = total_debt if total_debt is not None else cap_struct['total_debt_mm']
    final_tax = tax_rate if tax_rate is not None else tax_val

    # Track sources
    sources = {
        'risk_free_rate': rf_meta.get('source', 'inputs.json') if us_10y is None else 'Override',
        'beta': beta_meta.get('selection_rationale', 'inputs.json') if levered_beta is None else 'Override',
        'erp': erp_meta.get('source', 'inputs.json') if erp is None else 'Override',
        'size_premium': size_meta.get('source', 'inputs.json') if size_premium is None else 'Override',
        'cost_of_debt': cod_meta.get('calculation_method', 'inputs.json') if pretax_cod is None else 'Override',
        'capital_structure': cap_struct.get('source', 'inputs.json') if market_cap is None else 'Override',
        'tax_rate': tax_meta.get('source', 'inputs.json') if tax_rate is None else 'Override',
    }

    inputs = WACCInputs(
        company_name="United States Steel Corporation",
        ticker="X",
        currency="USD",

        # Risk-free rate
        risk_free_rate=final_rf,
        rf_source=rf_meta.get('source', ''),
        rf_as_of_date=rf_meta.get('as_of_date', ''),

        # Beta
        levered_beta=final_beta,
        beta_source="inputs.json (consensus of Bloomberg, Yahoo, Capital IQ)",
        beta_lookback_period="5-year monthly through 12/2023",
        beta_benchmark="S&P 500",

        # Equity risk premium
        equity_risk_premium=final_erp,
        erp_source=erp_meta.get('source', ''),

        # Size premium
        size_premium=final_size,
        size_premium_source=size_meta.get('source', ''),

        # Cost of debt
        pretax_cost_of_debt=final_cod,
        cod_source=cod_meta.get('calculation_method', ''),
        credit_spread=cod_meta.get('credit_spread', final_cod - final_rf),
        credit_rating=f"{cod_meta.get('credit_rating', {}).get('sp', 'BB')} / {cod_meta.get('credit_rating', {}).get('moodys', 'Ba2')}",

        # Capital structure
        market_cap=final_mc,
        total_debt=final_debt,
        cash_and_equivalents=cap_struct.get('cash_mm', 0),
        market_cap_source=cap_struct.get('source', ''),
        market_cap_as_of_date=cap_struct.get('as_of_date', ''),

        # Tax rate
        marginal_tax_rate=final_tax,
        tax_rate_source=tax_meta.get('source', ''),

        # Metadata
        data_as_of_date=get_data_as_of_date(),
        notes=f"USS WACC inputs loaded from inputs.json. Data as of {get_data_as_of_date()}.",
    )

    return inputs, sources


class USSWACCCalculator:
    """
    USS specific WACC calculator

    Loads all inputs from inputs.json for auditability.
    Includes comparison to analyst estimates and peer benchmarking.
    """

    def __init__(self, **overrides):
        """
        Initialize calculator

        Args:
            **overrides: Override any input (us_10y, levered_beta, etc.)
                        Only use for sensitivity analysis
        """
        self.inputs, self.sources = get_uss_wacc_inputs(**overrides)
        self.base_calculator = WACCCalculator(self.inputs)
        self.overrides = overrides

    def calculate(self) -> USSWACCResult:
        """
        Calculate USS WACC with analyst comparison

        Returns USSWACCResult with full breakdown and audit trail
        """
        # Calculate base WACC
        base_result = self.base_calculator.calculate()

        # Get cost of debt data for credit spread
        _, cod_meta = get_cost_of_debt()

        return USSWACCResult(
            wacc=base_result.wacc,
            cost_of_equity=base_result.cost_of_equity,
            cost_of_debt_aftertax=base_result.aftertax_cost_of_debt,
            risk_free_rate=self.inputs.risk_free_rate,
            levered_beta=self.inputs.levered_beta,
            equity_risk_premium=self.inputs.equity_risk_premium,
            size_premium=self.inputs.size_premium,
            credit_spread=cod_meta.get('credit_spread', self.inputs.pretax_cost_of_debt - self.inputs.risk_free_rate),
            equity_weight=base_result.equity_weight,
            debt_weight=base_result.debt_weight,
            market_cap=base_result.market_cap,
            total_debt=base_result.total_debt,
            enterprise_value=base_result.enterprise_value,
            analyst_comparison=get_analyst_estimates(),
            input_sources=self.sources,
            data_as_of_date=get_data_as_of_date(),
            base_result=base_result,
        )

    def sensitivity_to_beta(self, beta_values: list) -> Dict[float, float]:
        """Sensitivity of WACC to beta changes"""
        results = {}
        for beta in beta_values:
            calc = USSWACCCalculator(levered_beta=beta)
            result = calc.calculate()
            results[beta] = result.wacc
        return results

    def sensitivity_to_market_cap(self, market_cap_values: list) -> Dict[float, float]:
        """Sensitivity of WACC to market cap (capital structure) changes"""
        results = {}
        for mc in market_cap_values:
            calc = USSWACCCalculator(market_cap=mc)
            result = calc.calculate()
            results[mc] = result.wacc
        return results

    def sensitivity_to_cost_of_debt(self, cod_values: list) -> Dict[float, float]:
        """Sensitivity of WACC to cost of debt changes"""
        results = {}
        for cod in cod_values:
            calc = USSWACCCalculator(pretax_cod=cod)
            result = calc.calculate()
            results[cod] = result.wacc
        return results


def calculate_uss_wacc(bloomberg_overlay: Optional[dict] = None, **kwargs) -> USSWACCResult:
    """
    Convenience function to calculate USS WACC

    Args:
        bloomberg_overlay: Optional dict with Bloomberg-sourced WACC components.
                          If provided, these values will override inputs.json.
                          Expected keys: risk_free_rate, suggested_cost_of_debt
        **kwargs: Override any input parameters (for sensitivity analysis only)

    Returns:
        USSWACCResult with full WACC breakdown and audit trail

    Note:
        The bloomberg_overlay allows using current market rates from Bloomberg
        while preserving the ability to audit which values came from Bloomberg
        vs the verified inputs.json file.
    """
    # If Bloomberg overlay is provided, merge it into kwargs
    if bloomberg_overlay:
        # Map Bloomberg overlay fields to kwargs
        if 'risk_free_rate' in bloomberg_overlay and 'us_10y' not in kwargs:
            kwargs['us_10y'] = bloomberg_overlay['risk_free_rate']
        if 'suggested_cost_of_debt' in bloomberg_overlay and 'pretax_cod' not in kwargs:
            kwargs['pretax_cod'] = bloomberg_overlay['suggested_cost_of_debt']
        # Note: beta is not overridden from Bloomberg as it requires SPY data

    calc = USSWACCCalculator(**kwargs)
    result = calc.calculate()

    # Add Bloomberg overlay info to audit trail
    if bloomberg_overlay:
        audit = result.get_audit_trail()
        audit['bloomberg_overlay'] = {
            'applied': True,
            'overrides': bloomberg_overlay,
        }
        # Update sources to indicate Bloomberg
        if 'us_10y' in kwargs:
            result.input_sources['risk_free_rate'] = 'Bloomberg (current)'
        if 'pretax_cod' in kwargs:
            result.input_sources['cost_of_debt'] = 'Bloomberg (current)'

    return result


def calculate_uss_wacc_with_bloomberg() -> Optional[USSWACCResult]:
    """
    Calculate USS WACC using current Bloomberg market data.

    Loads current Treasury yields and credit spreads from Bloomberg data
    and uses them for the WACC calculation. Falls back to verified inputs
    if Bloomberg data is unavailable.

    Returns:
        USSWACCResult with Bloomberg-current inputs, or None if Bloomberg unavailable.
    """
    try:
        import sys
        from pathlib import Path as BloombergPath
        _bloomberg_path = BloombergPath(__file__).parent.parent.parent / "market-data" / "bloomberg"
        if str(_bloomberg_path.parent) not in sys.path:
            sys.path.insert(0, str(_bloomberg_path.parent))

        from bloomberg import get_wacc_overlay, is_bloomberg_available

        if not is_bloomberg_available():
            return None

        overlay = get_wacc_overlay()
        if not overlay:
            return None

        # Convert overlay to dict
        overlay_dict = {
            'risk_free_rate': overlay.risk_free_rate,
        }
        if overlay.suggested_cost_of_debt:
            overlay_dict['suggested_cost_of_debt'] = overlay.suggested_cost_of_debt

        return calculate_uss_wacc(bloomberg_overlay=overlay_dict)

    except ImportError:
        return None
    except Exception as e:
        print(f"Warning: Failed to calculate WACC with Bloomberg: {e}")
        return None


def compare_to_analyst_estimates(calculated_wacc: float) -> Dict[str, Dict]:
    """
    Compare calculated WACC to analyst estimates

    Returns comparison dict with deltas
    """
    estimates = get_analyst_estimates()
    comparison = {}
    for analyst, data in estimates.items():
        mid = data.get('wacc_midpoint', 0)
        low = data.get('wacc_range', [0, 0])[0] if 'wacc_range' in data else data.get('wacc_low', 0)
        high = data.get('wacc_range', [0, 0])[1] if 'wacc_range' in data else data.get('wacc_high', 0)
        comparison[analyst] = {
            **data,
            'delta_to_mid': calculated_wacc - mid if mid > 0 else None,
            'within_range': low <= calculated_wacc <= high if low > 0 and high > 0 else None,
        }
    return comparison


def get_wacc_at_share_price(share_price: float, shares_outstanding: float = 225.0) -> USSWACCResult:
    """
    Calculate WACC at a given share price

    Useful for sensitivity analysis as market cap affects capital structure weights.

    Args:
        share_price: USS share price ($)
        shares_outstanding: Shares outstanding (millions), default from inputs.json

    Returns:
        USSWACCResult at that share price
    """
    cap_struct = get_capital_structure()
    shares = cap_struct.get('shares_outstanding_mm', shares_outstanding)
    market_cap = share_price * shares
    return calculate_uss_wacc(market_cap=market_cap)


def print_input_sources():
    """Print all input sources for verification"""
    inputs = _get_inputs()

    print("=" * 70)
    print("USS WACC INPUT SOURCES")
    print(f"Data As Of: {inputs.get('_data_as_of_date', 'Unknown')}")
    print("=" * 70)

    print("\nRisk-Free Rate:")
    rf = inputs['risk_free_rate']
    print(f"  Value: {rf['value']*100:.2f}%")
    print(f"  Source: {rf['source']}")
    print(f"  URL: {rf.get('url', 'N/A')}")

    print("\nEquity Beta:")
    beta = inputs['equity_beta']
    print(f"  Selected: {beta['levered_beta']}")
    print(f"  Rationale: {beta['selection_rationale']}")
    for src, data in beta['sources'].items():
        print(f"    {src}: {data.get('beta', 'N/A')}")

    print("\nEquity Risk Premium:")
    erp = inputs['equity_risk_premium']
    print(f"  Value: {erp['value']*100:.1f}%")
    print(f"  Source: {erp['source']}")

    print("\nCost of Debt:")
    cod = inputs['cost_of_debt']
    print(f"  Pre-tax Rate: {cod['pretax_rate']*100:.2f}%")
    print(f"  Method: {cod['calculation_method']}")
    print(f"  Credit Rating: {cod['credit_rating']['sp']} / {cod['credit_rating']['moodys']}")

    print("\nCapital Structure:")
    cap = inputs['capital_structure']
    print(f"  Market Cap: ${cap['market_cap_mm']:,}M (@ ${cap['share_price']}/share)")
    print(f"  Total Debt: ${cap['total_debt_mm']:,}M")
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
    print("Calculating USS WACC from inputs.json...\n")

    # Print input sources first
    print_input_sources()
    print()

    # Default calculation
    result = calculate_uss_wacc()
    print(result.summary())

    # Sensitivity analysis
    print("\n" + "=" * 65)
    print("SENSITIVITY ANALYSIS")
    print("=" * 65)

    calc = USSWACCCalculator()

    print("\nBeta Sensitivity:")
    print("-" * 45)
    beta_sensitivity = calc.sensitivity_to_beta([1.2, 1.35, 1.45, 1.55, 1.7])
    for beta, wacc in beta_sensitivity.items():
        print(f"  Beta {beta:.2f}: WACC {wacc*100:.2f}%")

    print("\nShare Price Sensitivity (Capital Structure):")
    print("-" * 45)
    for price in [25, 35, 45, 55, 65]:
        result = get_wacc_at_share_price(price)
        print(f"  ${price}/share (${price*225/1000:.1f}B mkt cap): WACC {result.wacc*100:.2f}%")
