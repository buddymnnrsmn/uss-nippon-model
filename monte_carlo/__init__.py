"""
Sensitivity Analysis Package for USS / Nippon Steel Merger Model
=================================================================

This package provides advanced sensitivity analysis tools including:
- Monte Carlo simulation with configurable distributions
- Distribution fitting to historical data
- Multi-way sensitivity analysis
- Risk metrics (VaR, CVaR)
- Tornado diagrams
- Scenario analysis

Usage:
    from monte_carlo import MonteCarloEngine

    mc = MonteCarloEngine(n_simulations=10000)
    results = mc.run_simulation()
    mc.print_summary()

Distribution Fitting:
    from monte_carlo.distribution_fitter import DistributionFitter, fit_distribution

    fitter = DistributionFitter()
    result = fitter.fit_distribution(data, 'lognormal')
"""

from .monte_carlo_engine import MonteCarloEngine, Distribution, InputVariable
from .distribution_fitter import (
    DistributionFitter,
    FitResult,
    fit_distribution,
    select_best_distribution,
    validate_distribution_params
)

__all__ = [
    'MonteCarloEngine',
    'Distribution',
    'InputVariable',
    'DistributionFitter',
    'FitResult',
    'fit_distribution',
    'select_best_distribution',
    'validate_distribution_params'
]
__version__ = '1.1.0'
