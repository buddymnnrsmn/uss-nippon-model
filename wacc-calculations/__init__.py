"""
WACC Calculations Module
========================

Weighted Average Cost of Capital (WACC) calculations for:
- USS (United States Steel Corporation)
- Nippon Steel Corporation

Provides verifiable, bottom-up WACC derivation from market inputs.
"""

from .base_wacc import WACCCalculator, WACCInputs, WACCResult

__all__ = ['WACCCalculator', 'WACCInputs', 'WACCResult']
