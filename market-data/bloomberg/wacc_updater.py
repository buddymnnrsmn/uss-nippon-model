#!/usr/bin/env python3
"""
WACC Updater
============

Generates WACC overlay data from Bloomberg market rates.
Provides current Treasury yields, credit spreads, and beta calculations
without modifying the verified inputs.json files.

Usage:
    from market_data.bloomberg import get_wacc_overlay

    overlay = get_wacc_overlay()
    if overlay:
        # Use Bloomberg data for WACC components
        rf_rate = overlay.risk_free_rate
        credit_spread = overlay.credit_spread
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

from .bloomberg_data_service import get_bloomberg_service, is_bloomberg_available


@dataclass
class WACCBloombergOverlay:
    """
    Bloomberg-sourced WACC components as overlay to verified inputs.

    This dataclass provides current market data that can optionally be used
    to update WACC calculations. It does NOT modify inputs.json directly.
    """
    # Risk-free rate
    risk_free_rate: float           # 10Y UST yield (decimal, e.g., 0.0425)
    risk_free_rate_30y: Optional[float] = None  # 30Y UST for reference

    # Credit spreads
    bbb_spread: Optional[float] = None     # Investment grade spread
    high_yield_spread: Optional[float] = None  # HY spread

    # Derived cost of debt
    suggested_cost_of_debt: Optional[float] = None  # RF + credit spread

    # Beta from stock data
    calculated_beta: Optional[float] = None
    beta_r_squared: Optional[float] = None
    beta_period_days: int = 252

    # SOFR for reference
    sofr_rate: Optional[float] = None

    # Metadata
    data_as_of_date: Optional[datetime] = None
    sources: Dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate summary text"""
        lines = [
            "Bloomberg WACC Overlay",
            "=" * 50,
            f"Data As Of: {self.data_as_of_date.strftime('%Y-%m-%d') if self.data_as_of_date else 'Unknown'}",
            "",
            "Risk-Free Rate Components:",
            f"  10Y UST:        {self.risk_free_rate*100:.2f}%",
        ]

        if self.risk_free_rate_30y:
            lines.append(f"  30Y UST:        {self.risk_free_rate_30y*100:.2f}%")

        lines.extend([
            "",
            "Credit Spreads:",
        ])

        if self.bbb_spread:
            lines.append(f"  BBB Spread:     {self.bbb_spread*100:.2f}%")
        if self.high_yield_spread:
            lines.append(f"  HY Spread:      {self.high_yield_spread*100:.2f}%")

        if self.suggested_cost_of_debt:
            lines.extend([
                "",
                f"Suggested Pre-tax CoD: {self.suggested_cost_of_debt*100:.2f}%",
                f"  (10Y UST + BB spread estimate)",
            ])

        if self.calculated_beta:
            lines.extend([
                "",
                f"Calculated Beta: {self.calculated_beta:.2f}",
                f"  R-squared: {self.beta_r_squared:.2f}" if self.beta_r_squared else "",
                f"  Period: {self.beta_period_days} trading days",
            ])

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'risk_free_rate': self.risk_free_rate,
            'risk_free_rate_30y': self.risk_free_rate_30y,
            'bbb_spread': self.bbb_spread,
            'high_yield_spread': self.high_yield_spread,
            'suggested_cost_of_debt': self.suggested_cost_of_debt,
            'calculated_beta': self.calculated_beta,
            'beta_r_squared': self.beta_r_squared,
            'beta_period_days': self.beta_period_days,
            'sofr_rate': self.sofr_rate,
            'data_as_of_date': self.data_as_of_date.isoformat() if self.data_as_of_date else None,
            'sources': self.sources,
        }


def get_wacc_overlay() -> Optional[WACCBloombergOverlay]:
    """
    Get WACC components from Bloomberg data as overlay.

    Returns:
        WACCBloombergOverlay with current market rates,
        or None if Bloomberg data unavailable.
    """
    if not is_bloomberg_available():
        return None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None

        rates = service.get_current_rates()
        sources = {}

        # Risk-free rate (10Y UST)
        rf_rate = rates.get('risk_free_rate')
        if rf_rate is None:
            return None

        sources['risk_free_rate'] = 'Bloomberg 10Y UST'

        # 30Y UST
        rf_30y = rates.get('ust_30y')
        if rf_30y:
            sources['risk_free_rate_30y'] = 'Bloomberg 30Y UST'

        # Credit spreads
        bbb_spread = rates.get('investment_grade_spread')
        if bbb_spread:
            sources['bbb_spread'] = 'Bloomberg BBB OAS'

        hy_spread = rates.get('high_yield_spread')
        if hy_spread:
            sources['high_yield_spread'] = 'Bloomberg HY OAS'

        # Estimate USS cost of debt (USS is BB rated, between BBB and HY)
        # BB spread is typically ~60-70% of the way from BBB to HY
        suggested_cod = None
        if bbb_spread and hy_spread:
            bb_spread_estimate = bbb_spread + 0.65 * (hy_spread - bbb_spread)
            suggested_cod = rf_rate + bb_spread_estimate
            sources['suggested_cost_of_debt'] = 'Estimated: RF + BB spread (interpolated BBB/HY)'

        # SOFR
        sofr = rates.get('sofr')
        if sofr:
            sources['sofr_rate'] = 'Bloomberg SOFR'

        # Calculate beta from stock data
        beta, r_squared = calculate_beta_from_stock_data()
        if beta:
            sources['calculated_beta'] = 'Bloomberg USS/SPY returns (252 trading days)'

        # Data as-of date
        data_date = service.get_data_as_of_date()

        return WACCBloombergOverlay(
            risk_free_rate=rf_rate,
            risk_free_rate_30y=rf_30y,
            bbb_spread=bbb_spread,
            high_yield_spread=hy_spread,
            suggested_cost_of_debt=suggested_cod,
            calculated_beta=beta,
            beta_r_squared=r_squared,
            sofr_rate=sofr,
            data_as_of_date=data_date,
            sources=sources,
        )

    except Exception as e:
        print(f"Warning: Failed to get WACC overlay: {e}")
        return None


def calculate_beta_from_stock_data(period_days: int = 252) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate USS beta from stock return data.

    Uses USS stock returns vs S&P 500 (proxied by market returns if available).

    Args:
        period_days: Number of trading days for calculation (default 252 = 1 year)

    Returns:
        Tuple of (beta, r_squared), or (None, None) if calculation fails.
    """
    if not is_bloomberg_available():
        return None, None

    try:
        service = get_bloomberg_service()
        if not service.is_available():
            return None, None

        # Get USS returns
        uss_returns = service.get_stock_returns('uss', period_days)
        if uss_returns is None or len(uss_returns) < 50:
            return None, None

        # For market returns, we'd need SPY data which we don't have in Bloomberg exports
        # Instead, we can use the existing beta from inputs.json as this requires SPY data
        # This function is a placeholder for when SPY data becomes available

        # For now, return None to indicate we can't calculate from Bloomberg alone
        # The model should use the verified beta from inputs.json
        return None, None

    except Exception as e:
        print(f"Warning: Failed to calculate beta: {e}")
        return None, None


def compare_to_verified_inputs() -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Compare Bloomberg overlay data to verified inputs.json values.

    Returns dict showing differences between Bloomberg current data
    and the verified inputs for review before applying.

    Returns:
        Dict with comparison for each WACC component, or None if unavailable.
    """
    overlay = get_wacc_overlay()
    if not overlay:
        return None

    try:
        # Load USS verified inputs
        inputs_path = Path(__file__).parent.parent.parent / "wacc-calculations" / "uss" / "inputs.json"
        if not inputs_path.exists():
            return None

        import json
        with open(inputs_path, 'r') as f:
            uss_inputs = json.load(f)

        comparisons = {}

        # Risk-free rate
        verified_rf = uss_inputs.get('risk_free_rate', {}).get('value', 0)
        comparisons['risk_free_rate'] = {
            'bloomberg': overlay.risk_free_rate,
            'verified': verified_rf,
            'difference': overlay.risk_free_rate - verified_rf,
            'difference_bps': (overlay.risk_free_rate - verified_rf) * 10000,
            'verified_source': uss_inputs.get('risk_free_rate', {}).get('source', 'inputs.json'),
            'verified_as_of': uss_inputs.get('risk_free_rate', {}).get('as_of_date', 'Unknown'),
        }

        # Cost of debt
        verified_cod = uss_inputs.get('cost_of_debt', {}).get('pretax_rate', 0)
        if overlay.suggested_cost_of_debt:
            comparisons['cost_of_debt'] = {
                'bloomberg': overlay.suggested_cost_of_debt,
                'verified': verified_cod,
                'difference': overlay.suggested_cost_of_debt - verified_cod,
                'difference_bps': (overlay.suggested_cost_of_debt - verified_cod) * 10000,
                'verified_source': uss_inputs.get('cost_of_debt', {}).get('calculation_method', 'inputs.json'),
            }

        # Credit spread
        verified_spread = uss_inputs.get('cost_of_debt', {}).get('credit_spread', 0)
        if overlay.bbb_spread and overlay.high_yield_spread:
            # Estimate BB spread
            bb_spread_estimate = overlay.bbb_spread + 0.65 * (overlay.high_yield_spread - overlay.bbb_spread)
            comparisons['credit_spread'] = {
                'bloomberg_bbb': overlay.bbb_spread,
                'bloomberg_hy': overlay.high_yield_spread,
                'bloomberg_bb_estimate': bb_spread_estimate,
                'verified': verified_spread,
                'difference_bps': (bb_spread_estimate - verified_spread) * 10000,
            }

        # Beta (only if we have calculated beta)
        if overlay.calculated_beta:
            verified_beta = uss_inputs.get('equity_beta', {}).get('levered_beta', 0)
            comparisons['beta'] = {
                'bloomberg': overlay.calculated_beta,
                'verified': verified_beta,
                'difference': overlay.calculated_beta - verified_beta,
                'r_squared': overlay.beta_r_squared,
            }

        return comparisons

    except Exception as e:
        print(f"Warning: Failed to compare to verified inputs: {e}")
        return None


def generate_wacc_overlay_report() -> str:
    """
    Generate a detailed report comparing Bloomberg vs verified WACC inputs.

    Returns:
        Formatted report string for review.
    """
    lines = [
        "=" * 70,
        "WACC BLOOMBERG OVERLAY REPORT",
        "=" * 70,
        "",
    ]

    overlay = get_wacc_overlay()
    if not overlay:
        lines.append("Bloomberg WACC overlay data not available.")
        return "\n".join(lines)

    lines.append(f"Bloomberg Data As Of: {overlay.data_as_of_date.strftime('%Y-%m-%d') if overlay.data_as_of_date else 'Unknown'}")
    lines.append("")

    # Get comparison
    comparison = compare_to_verified_inputs()

    lines.extend([
        "RISK-FREE RATE",
        "-" * 50,
    ])

    if comparison and 'risk_free_rate' in comparison:
        rf = comparison['risk_free_rate']
        lines.extend([
            f"  Bloomberg (current):  {rf['bloomberg']*100:.2f}%",
            f"  Verified inputs:      {rf['verified']*100:.2f}%",
            f"  Difference:           {rf['difference_bps']:+.0f} bps",
            f"  Verified as of:       {rf['verified_as_of']}",
        ])
    else:
        lines.append(f"  Bloomberg:            {overlay.risk_free_rate*100:.2f}%")

    lines.extend([
        "",
        "CREDIT SPREADS",
        "-" * 50,
    ])

    if overlay.bbb_spread:
        lines.append(f"  BBB Spread:           {overlay.bbb_spread*100:.2f}%")
    if overlay.high_yield_spread:
        lines.append(f"  High Yield Spread:    {overlay.high_yield_spread*100:.2f}%")

    if comparison and 'credit_spread' in comparison:
        cs = comparison['credit_spread']
        lines.extend([
            f"  BB Estimate:          {cs['bloomberg_bb_estimate']*100:.2f}%",
            f"  Verified spread:      {cs['verified']*100:.2f}%",
            f"  Difference:           {cs['difference_bps']:+.0f} bps",
        ])

    lines.extend([
        "",
        "COST OF DEBT (PRE-TAX)",
        "-" * 50,
    ])

    if comparison and 'cost_of_debt' in comparison:
        cod = comparison['cost_of_debt']
        lines.extend([
            f"  Bloomberg suggested:  {cod['bloomberg']*100:.2f}%",
            f"  Verified inputs:      {cod['verified']*100:.2f}%",
            f"  Difference:           {cod['difference_bps']:+.0f} bps",
        ])
    elif overlay.suggested_cost_of_debt:
        lines.append(f"  Bloomberg suggested:  {overlay.suggested_cost_of_debt*100:.2f}%")

    lines.extend([
        "",
        "BETA",
        "-" * 50,
    ])

    if overlay.calculated_beta:
        lines.append(f"  Calculated from data: {overlay.calculated_beta:.2f}")
        if overlay.beta_r_squared:
            lines.append(f"  R-squared:            {overlay.beta_r_squared:.2f}")
    else:
        lines.append("  Not calculated (requires SPY data)")
        lines.append("  Use verified beta from inputs.json")

    lines.extend([
        "",
        "=" * 70,
        "RECOMMENDATION",
        "=" * 70,
        "",
    ])

    # Generate recommendations based on differences
    recommendations = []

    if comparison:
        rf = comparison.get('risk_free_rate', {})
        if abs(rf.get('difference_bps', 0)) > 25:
            recommendations.append(
                f"- Risk-free rate differs by {rf['difference_bps']:+.0f} bps. "
                "Consider reviewing if inputs.json needs update."
            )

        cod = comparison.get('cost_of_debt', {})
        if abs(cod.get('difference_bps', 0)) > 50:
            recommendations.append(
                f"- Cost of debt differs by {cod['difference_bps']:+.0f} bps. "
                "Market conditions may have shifted significantly."
            )

    if not recommendations:
        recommendations.append("- Bloomberg data is reasonably aligned with verified inputs.")
        recommendations.append("- No immediate updates recommended.")

    lines.extend(recommendations)
    lines.append("")

    return "\n".join(lines)


if __name__ == '__main__':
    # Demo usage
    print(generate_wacc_overlay_report())
