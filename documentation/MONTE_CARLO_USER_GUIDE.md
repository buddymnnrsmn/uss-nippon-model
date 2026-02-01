# Monte Carlo Sensitivity Analysis - User Guide
## USS / Nippon Steel Merger Model

**Last Updated:** 2026-01-31

---

## Quick Start

### Running Your First Monte Carlo Simulation

```bash
# From the FinancialModel directory
python scripts/run_monte_carlo_demo.py
```

This will:
- Run 1,000 Monte Carlo iterations
- Print summary statistics
- Save results to CSV files
- Generate visualization plots

### Understanding the Output

The simulation will produce:

1. **Console Output**: Summary statistics including mean, percentiles, VaR, and probability metrics
2. **CSV Files**: Detailed results for every iteration
3. **Plots**: Histogram, CDF, box plot, and risk metrics summary

---

## What is Monte Carlo Simulation?

### The Problem with Deterministic Models

Traditional DCF models use single point estimates:
- Steel price = $680/ton
- WACC = 10.9%
- Volume = 10,500k tons

But in reality:
- Steel prices fluctuate ±20% year-to-year
- Interest rates change based on macro conditions
- Volume depends on demand cycles

**Point estimates hide uncertainty.**

### The Monte Carlo Solution

Instead of single values, we use **probability distributions**:

```
Steel Price:  Not just $680, but Normal($680, $150)
WACC:         Not just 10.9%, but Normal(10.9%, 0.8%)
Volume:       Not just 100%, but range 85%-115%
```

Then we:
1. Sample from these distributions 10,000 times
2. Run the DCF model for each sample
3. Analyze the distribution of outcomes

Result: **"There's an 85% chance value is between $52 and $103"**

---

## Key Concepts

### Input Distributions

Each uncertain variable is modeled with a probability distribution:

#### Normal Distribution
Used for: WACC, terminal growth (symmetric uncertainty)
```
mean = expected value
std = measure of uncertainty
```

#### Lognormal Distribution
Used for: Steel prices (can't be negative, right-skewed)
```
Prevents negative prices
Models commodities well
```

#### Triangular Distribution
Used for: Volume ranges, exit multiples (bounded with most likely)
```
min = worst case
mode = most likely
max = best case
```

#### Beta Distribution
Used for: Execution success rates (bounded 0-1 with shape)
```
alpha, beta = shape parameters
Flexible for success probabilities
```

### Correlation

Variables don't move independently:
- When HRC prices rise, CRC prices usually rise too (correlation = 0.95)
- When steel prices rise, volumes often increase (correlation = 0.40)
- When US rates rise, Japan rates may diverge (correlation = -0.30)

The Monte Carlo engine preserves these relationships using **Cholesky decomposition**.

### Latin Hypercube Sampling (LHS)

Better than simple random sampling:
- **Random sampling**: May miss parts of the distribution
- **LHS**: Ensures even coverage across entire probability space
- **Result**: Need only 5,000-10,000 iterations instead of 50,000+

---

## Output Metrics Explained

### Central Tendency

| Metric | Definition | When to Use |
|--------|------------|-------------|
| **Mean** | Average of all outcomes | Expected value, probability-weighted |
| **Median** | Middle value (50th percentile) | Typical outcome, less affected by extremes |
| **Mode** | Most frequent value | Most likely single outcome |

For **skewed distributions** (common in valuations), median ≠ mean.

### Percentiles

| Percentile | Interpretation |
|------------|----------------|
| P5 (5th) | Only 5% of outcomes are worse than this |
| P10 | Only 10% of outcomes are worse than this |
| P50 | Median - half above, half below |
| P90 | 90% of outcomes are below this |
| P95 | 95% of outcomes are below this |

**Confidence Intervals**:
- 80% CI (P10-P90): "We're 80% confident the value falls in this range"
- 90% CI (P5-P95): Wider range, higher confidence
- 95% CI (P2.5-P97.5): Even wider, highest confidence

### Risk Metrics

#### Value at Risk (VaR)

**VaR(95%) = $48.20** means:
- "We're 95% confident the value will be at least $48.20"
- Or: "Only 5% chance of value below $48.20"
- Industry standard risk metric

#### Conditional Value at Risk (CVaR)

**CVaR(95%) = $44.50** means:
- "If we're in the worst 5% of outcomes, the expected value is $44.50"
- Answers: "How bad is the downside if things go wrong?"
- More informative than VaR alone

#### Downside Risk

Focus on losses below a target (e.g., $55 offer):
- **P(Value < $55)**: Probability offer looks good
- **Expected Shortfall**: Average loss when below target

### Distribution Shape

#### Skewness
- **Positive skew** (>0.5): Long right tail → upside potential
- **Negative skew** (<-0.5): Long left tail → downside risk
- **Symmetric** (≈0): Balanced risk/reward

#### Kurtosis
- **High kurtosis** (>1): Fat tails → higher probability of extremes
- **Low kurtosis** (<-1): Thin tails → outcomes clustered near mean
- **Normal** (≈0): Normal distribution tails

---

## Customizing Your Analysis

### Adjusting Input Distributions

Edit `sensitivity_analysis/monte_carlo_engine.py`, method `_define_input_variables()`:

#### Example: Increase steel price uncertainty

```python
variables['hrc_price_factor'] = InputVariable(
    name='hrc_price_factor',
    description='HRC Steel Price Factor',
    distribution=Distribution(
        name='HRC Price Factor',
        dist_type='lognormal',
        params={
            'mean': np.log(0.95),
            'std': 0.25,  # Changed from 0.18 to 0.25 (more volatile)
        }
    ),
    base_value=0.95,
)
```

#### Example: Change WACC distribution

```python
variables['uss_wacc'] = InputVariable(
    name='uss_wacc',
    description='USS WACC (%)',
    distribution=Distribution(
        name='USS WACC',
        dist_type='triangular',  # Changed from normal to triangular
        params={
            'min': 9.5,
            'mode': 10.9,
            'max': 12.5,
        }
    ),
    base_value=10.9,
)
```

### Adjusting Correlations

Edit the `correlations` dictionary in variable definitions:

```python
variables['hrc_price_factor'] = InputVariable(
    # ... other params ...
    correlations={
        'crc_price_factor': 0.95,      # Keep high correlation
        'flat_rolled_volume': 0.60,    # Increased from 0.40
        'uss_wacc': -0.35,             # Stronger negative correlation
    }
)
```

### Running Different Scenarios

```python
from sensitivity_analysis import MonteCarloEngine
from price_volume_model import get_scenario_presets, ScenarioType

# Use Wall Street scenario as base
wall_street = get_scenario_presets()[ScenarioType.WALL_STREET]

mc = MonteCarloEngine(
    n_simulations=10000,
    base_scenario=wall_street
)

results = mc.run_simulation()
mc.print_summary()
```

### Including Capital Projects

```python
# Run MC with NSA mandated CapEx projects
results = mc.run_simulation(
    include_projects=[
        'Gary Works BF',
        'Mon Valley HSM',
        'Greenfield Mini Mill',
        # etc.
    ],
    execution_factor_override=0.75  # Or None to sample
)
```

---

## Interpreting Results

### Case Study: Example Output

```
MONTE CARLO SIMULATION SUMMARY
================================================================================
Simulations: 10,000
Sampling: Latin Hypercube

CENTRAL TENDENCY
--------------------------------------------------------------------------------
  Mean:                $75.80 per share
  Median:              $73.20 per share
  Mode (estimated):    $71.50 per share
  Std Deviation:       $18.45
  Coefficient of Var:  24.3%

PERCENTILES
--------------------------------------------------------------------------------
  P10 (10th percentile):  $52.30
  P50 (Median):           $73.20
  P90 (90th percentile):  $103.40

RISK METRICS
--------------------------------------------------------------------------------
  VaR (95%):           $48.20
  CVaR (95%):          $44.50

PROBABILITY METRICS
--------------------------------------------------------------------------------
  P(Value < $55):      18.5%  ← vs Nippon $55 offer
  P(Value > $75):      48.3%
  P(Value > $100):     12.7%
```

### What This Tells Us

1. **Expected value ($75.80) exceeds $55 offer**
   - Mean is $20.80 above offer price
   - Suggests offer is conservative

2. **But there's uncertainty**
   - 80% of outcomes fall between $52-$103 (wide range!)
   - Std dev of $18.45 is 24% of mean (significant)

3. **Downside is limited**
   - Only 18.5% chance value is below $55 offer
   - VaR(95%) = $48.20 means 95% chance of >$48.20
   - Offer provides downside protection

4. **Upside potential exists**
   - 48% chance of value >$75
   - 13% chance of value >$100
   - Right tail opportunity

5. **Distribution is right-skewed**
   - Mean ($75.80) > Median ($73.20) > Mode ($71.50)
   - Long right tail = upside potential
   - Positive skew is good for buyers

### Decision Framework

| Condition | Interpretation | Action Implication |
|-----------|----------------|-------------------|
| P(Value < Offer) < 20% | Offer is conservative | Negotiate higher or accept |
| P(Value < Offer) = 20-40% | Offer is fair | Accept if downside protection valued |
| P(Value < Offer) > 40% | Offer is generous | Strong accept |
| VaR(95%) > $40 | Limited downside | Lower risk |
| P(Value > $100) > 20% | Significant upside | May want to hold |

---

## Advanced Usage

### Calibrating to Historical Data

To improve accuracy, calibrate distributions to historical steel prices:

```python
import pandas as pd
from scipy import stats

# Load historical HRC prices (1990-2023)
hrc_prices = pd.read_csv('historical_hrc_prices.csv')['price']

# Fit lognormal distribution
shape, loc, scale = stats.lognorm.fit(hrc_prices)

# Use fitted parameters
variables['hrc_price_factor'] = InputVariable(
    # ...
    distribution=Distribution(
        name='HRC Price Factor',
        dist_type='lognormal',
        params={
            'mean': np.log(scale),
            'std': shape,
        }
    ),
)
```

### Stress Testing Specific Scenarios

Run Monte Carlo conditional on specific events:

```python
# Recession scenario: Force low prices and high WACC
# (modify distributions before creating engine)
```

### Combining with Scenario Analysis

```python
from price_volume_model import ScenarioType

scenarios = [ScenarioType.CONSERVATIVE, ScenarioType.BASE_CASE, ScenarioType.OPTIMISTIC]

for scenario_type in scenarios:
    scenario = get_scenario_presets()[scenario_type]
    mc = MonteCarloEngine(base_scenario=scenario, n_simulations=5000)
    results = mc.run_simulation(verbose=False)
    stats = mc.calculate_statistics()
    print(f"\n{scenario.name}:")
    print(f"  Expected Value: ${stats['mean']:.2f}")
    print(f"  P(Value < $55): {stats['prob_below_55']:.1%}")
```

---

## Performance Tips

### Runtime Optimization

Typical runtime:
- 1,000 iterations: ~1 minute
- 10,000 iterations: ~10 minutes
- 50,000 iterations: ~50 minutes

To speed up:

1. **Use fewer iterations for testing**
   ```python
   mc = MonteCarloEngine(n_simulations=1000)  # Quick test
   ```

2. **Use LHS instead of random sampling**
   ```python
   mc = MonteCarloEngine(use_lhs=True)  # Already default
   ```

3. **Profile slow parts** (future enhancement: vectorization)

### When to Use How Many Iterations

| Purpose | Iterations | Runtime | Accuracy |
|---------|-----------|---------|----------|
| Quick test | 1,000 | 1 min | ±5% |
| Analysis | 5,000 | 5 min | ±2% |
| Presentation | 10,000 | 10 min | ±1% |
| Publication | 50,000 | 50 min | ±0.5% |

---

## Troubleshooting

### Common Issues

#### "Correlation matrix not positive definite"

**Cause**: Inconsistent correlations (A→B=0.9, B→C=0.9, C→A=-0.8)

**Fix**: Review correlation matrix for logical consistency

#### "Too many failed iterations"

**Cause**: Distributions generating invalid inputs (negative prices, WACC >100%)

**Fix**:
- Add bounds to distributions
- Use lognormal for prices (can't be negative)
- Validate sampled values before running model

#### Results don't match deterministic base case

**Cause**: Mean of distributions ≠ base case values

**Fix**: Ensure distribution means match base scenario

---

## Next Steps

### Immediate Actions

1. **Run the demo** to understand the output
2. **Review distributions** - do they match your beliefs?
3. **Adjust correlations** based on industry knowledge
4. **Run full analysis** with 10,000 iterations

### Advanced Enhancements

See `ADVANCED_SENSITIVITY_ANALYSIS_STRATEGY.md` for:
- Time-series price paths (mean reversion models)
- Regime-switching scenarios
- Real options analysis
- Dashboard integration

---

## References

### Academic

- Hull, J. (2018). *Options, Futures, and Other Derivatives*. Chapter 21: Monte Carlo Simulation.
- Savage, S. (2009). *The Flaw of Averages*. Wiley.

### Industry

- CFA Institute: "Monte Carlo Simulation in Financial Modeling"
- McKinsey: "The use of Monte Carlo simulation in merger valuation"

### Model Documentation

- See `MODEL_METHODOLOGY.md` for DCF model details
- See `SENSITIVITY_ANALYSIS.md` for deterministic sensitivity analysis

---

**Questions or Issues?**

Contact: RAMBAS Team
Last Updated: 2026-01-31
