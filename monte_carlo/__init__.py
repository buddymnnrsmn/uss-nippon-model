"""
Sensitivity Analysis Package for USS / Nippon Steel Merger Model
=================================================================

This package provides advanced sensitivity analysis tools including:
- Monte Carlo simulation
- Multi-way sensitivity analysis
- Risk metrics (VaR, CVaR)
- Tornado diagrams
- Scenario analysis

Usage:
    from monte_carlo import MonteCarloEngine

    mc = MonteCarloEngine(n_simulations=10000)
    results = mc.run_simulation()
    mc.print_summary()
"""

from .monte_carlo_engine import MonteCarloEngine, Distribution, InputVariable

__all__ = ['MonteCarloEngine', 'Distribution', 'InputVariable']
__version__ = '1.0.0'
