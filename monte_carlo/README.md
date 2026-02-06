# Sensitivity Analysis Package

Advanced sensitivity analysis tools for the USS / Nippon Steel merger DCF model.

## Features

### Current (v1.0)

- **Monte Carlo Simulation**: Probabilistic valuation with 10,000+ iterations
- **Latin Hypercube Sampling**: Efficient coverage of probability space
- **Correlation Modeling**: Preserves relationships between variables via Cholesky decomposition
- **Risk Metrics**: VaR, CVaR, percentiles, probability distributions
- **Multiple Distributions**: Normal, lognormal, triangular, beta, uniform

### Planned (Future Releases)

- **Tornado Diagrams**: Variable importance ranking
- **Two-Way Sensitivity**: Heat maps for variable interactions
- **Time-Series Models**: Mean-reverting steel price paths
- **Regime Switching**: Economic cycle modeling
- **Real Options**: Valuation of flexibility
- **Dashboard Integration**: Streamlit interface

## Quick Start

```bash
# Run demo (1,000 iterations)
python scripts/run_monte_carlo_demo.py

# Run with more iterations
python scripts/run_monte_carlo_demo.py -n 10000
```

## Python Usage

```python
from sensitivity_analysis import MonteCarloEngine

# Initialize engine
mc = MonteCarloEngine(n_simulations=10000, use_lhs=True)

# Run simulation
results = mc.run_simulation(verbose=True)

# Print summary
mc.print_summary()

# Access results
stats = mc.calculate_statistics()
print(f"Expected value: ${stats['mean']:.2f}")
print(f"P(Value < $55): {stats['prob_below_55']:.1%}")
```

## Files

```
sensitivity_analysis/
├── __init__.py                 # Package initialization
├── monte_carlo_engine.py       # Core Monte Carlo simulation engine
└── README.md                   # This file
```

## Documentation

- **User Guide**: `documentation/MONTE_CARLO_USER_GUIDE.md`
- **Strategy**: `documentation/ADVANCED_SENSITIVITY_ANALYSIS_STRATEGY.md`
- **Methodology**: `documentation/MODEL_METHODOLOGY.md`

## Key Concepts

### Input Variables

The Monte Carlo engine models uncertainty in:
- **Steel Prices**: HRC, CRC, Coated, OCTG, HRC EU (lognormal distributions)
- **Volumes**: Flat-Rolled, Mini Mill, USSE, Tubular (normal/triangular)
- **Discount Rate**: USS WACC, Japan risk-free rate, US 10Y, Nippon ERP (normal)
- **Terminal Value**: Growth rate, exit multiple (triangular)
- **Execution Risk**: Project success rates (beta)
- **Tariff Risk**: Tariff probability (beta), alternative rate (triangular)
- **Other**: Annual price growth, margin factor, capex intensity, working capital

### Correlation Structure

Preserves relationships:
- HRC ↔ CRC prices: 0.97 correlation
- HRC price ↔ Volume: 0.56 correlation
- OCTG ↔ Tubular volume: 0.73 correlation
- HRC US ↔ HRC EU: 0.70 correlation
- US 10Y ↔ USS WACC: 0.60 correlation
- Tariff Prob ↔ HRC Price: -0.35 (tariff removal → lower prices)
- Tariff Prob ↔ FR Volume: -0.25 (tariff removal → lower demand)

### Latest Results (10,000 sims, 25 variables incl. tariff risk, 2026-02-06)

| Metric | USS Standalone | Nippon View |
|--------|---------------|-------------|
| Mean | $61.2 | $85.0 |
| Median | $57.3 | $79.8 |
| P5 / P95 | $25 / $111 | $36 / $152 |
| P(< $55 offer) | 46.3% | 20.6% |
| Synergy Premium | — | ~$23/share |

### Output Metrics

- **Central Tendency**: Mean, median, mode
- **Percentiles**: P1, P5, P10, P25, P50, P75, P90, P95, P99
- **Confidence Intervals**: 80%, 90%, 95%
- **Risk Metrics**: VaR(95%), CVaR(95%)
- **Probability Metrics**: P(Value < $55), P(Value > $100)
- **Distribution Shape**: Skewness, kurtosis

## Performance

Typical runtime (4-worker parallel execution):
- 1,000 iterations: ~20 seconds
- 5,000 iterations: ~100 seconds
- 10,000 iterations: ~3.5 minutes

Latin Hypercube Sampling provides 95% accuracy with 10,000 iterations (vs 50,000+ for random sampling).

## Customization

### Adjusting Distributions

Edit `monte_carlo_engine.py`, method `_define_input_variables()`:

```python
variables['hrc_price_factor'] = InputVariable(
    name='hrc_price_factor',
    description='HRC Steel Price Factor',
    distribution=Distribution(
        name='HRC Price Factor',
        dist_type='lognormal',
        params={
            'mean': np.log(0.95),  # Adjust mean
            'std': 0.25,           # Adjust volatility
        }
    ),
    base_value=0.95,
    correlations={
        'crc_price_factor': 0.95,  # Adjust correlations
    }
)
```

### Adding New Variables

```python
variables['new_variable'] = InputVariable(
    name='new_variable',
    description='Description',
    distribution=Distribution(
        name='Display Name',
        dist_type='normal',
        params={'mean': 100, 'std': 10}
    ),
    base_value=100,
    correlations={'other_var': 0.5}
)
```

## Validation

The engine includes validation checks:
- Correlation matrix positive semi-definite
- Distribution parameters valid
- Model convergence diagnostics
- Monte Carlo mean vs deterministic base case

## Roadmap

### Phase 1: Foundation (Complete)
- [x] Monte Carlo core engine
- [x] Latin Hypercube Sampling
- [x] Correlation modeling
- [x] Risk metrics

### Phase 2: Enhanced Analytics (Complete)
- [x] Tornado diagrams (correlation-based sensitivity)
- [x] Dual-perspective distributions (USS vs Nippon)
- [x] 13 automated visualization charts
- [x] Through-cycle distribution calibration
- [ ] Export to Excel/PDF

### Phase 3: Time-Series (Planned)
- [ ] Mean-reverting price paths
- [ ] Jump-diffusion processes
- [ ] Regime-switching models

### Phase 4: Dashboard (Planned)
- [ ] Streamlit integration
- [ ] Interactive controls
- [ ] Real-time simulation
- [ ] Report generation

### Phase 5: Advanced (Future)
- [ ] Real options analysis
- [ ] Scenario trees
- [ ] Copula modeling
- [ ] GPU acceleration

## Contributing

To add features:
1. Create new module in `sensitivity_analysis/`
2. Update `__init__.py` to export new classes
3. Add documentation to `documentation/`
4. Add tests to `tests/`

## License

Internal use only - RAMBAS Team Capstone Project

## Contact

Questions or issues? Contact the RAMBAS team.

**Last Updated:** 2026-02-06
