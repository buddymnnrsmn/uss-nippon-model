# Advanced Sensitivity Analysis Strategy
## USS / Nippon Steel Merger Model

**Date:** 2026-01-31
**Status:** Strategy & Implementation Roadmap

---

## Executive Summary

This document outlines strategies for implementing robust sensitivity analysis for the USS/Nippon Steel DCF model, with focus on Monte Carlo simulation and multi-dimensional risk assessment. The goal is to move beyond deterministic scenario analysis to probabilistic valuation that captures the full range of potential outcomes.

### Current State

- **One-way sensitivities**: Steel price benchmarks (70%-130%)
- **Pre-defined scenarios**: 7 discrete scenarios (Severe Downturn → Optimistic)
- **Limited correlation modeling**: Independent variable assumptions
- **Deterministic outputs**: Point estimates for each scenario

### Target State

- **Probabilistic valuation**: Monte Carlo simulation with 10,000+ iterations
- **Correlated inputs**: Model relationships between steel prices, volumes, and macro conditions
- **Risk metrics**: VaR, CVaR, probability distributions
- **Multi-way sensitivity**: Tornado diagrams, scenario matrices
- **Dynamic scenarios**: Scenario generation based on economic conditions

---

## Strategy 1: Monte Carlo Simulation Framework

### 1.1 Objective

Replace deterministic scenarios with probabilistic distributions to generate a range of valuation outcomes with associated probabilities.

### 1.2 Architecture

```
MonteCarloEngine
├── Input Distributions (define probability distributions for each variable)
├── Correlation Matrix (model dependencies between variables)
├── Sampling Engine (Latin Hypercube or Sobol sequences)
├── Model Execution (run DCF for each iteration)
├── Output Analysis (statistics, percentiles, distributions)
└── Visualization (histograms, CDFs, tornado charts)
```

### 1.3 Key Input Variables & Distributions

#### Primary Drivers (High Impact)

| Variable | Distribution Type | Parameters | Rationale |
|----------|------------------|------------|-----------|
| HRC Steel Price | Lognormal | μ=$680, σ=$150 | Prevents negative prices, right-skewed |
| CRC Steel Price | Lognormal | μ=$850, σ=$175 | Linked to HRC with premium |
| OCTG Price | Lognormal | μ=$2800, σ=$600 | Higher volatility in oil/gas markets |
| Flat-Rolled Volume | Normal | μ=10,500k tons, σ=800k | Bounded by capacity |
| Mini Mill Volume | Normal | μ=4,200k tons, σ=400k | More stable production |
| Tubular Volume | Triangular | min=1,200k, mode=1,800k, max=2,200k | Oil/gas cyclicality |

#### Secondary Drivers (Moderate Impact)

| Variable | Distribution Type | Parameters | Rationale |
|----------|------------------|------------|-----------|
| USS WACC | Normal | μ=10.9%, σ=0.8% | Market risk premium variation |
| Japan Risk-Free Rate | Normal | μ=0.75%, σ=0.3% | BOJ policy uncertainty |
| Terminal Growth | Triangular | min=-0.5%, mode=1.0%, max=2.5% | Industry maturity |
| Exit Multiple | Triangular | min=3.5x, mode=4.5x, max=6.5x | Peer trading ranges |

#### Project Execution Factors (NSA Mandated CapEx)

| Variable | Distribution Type | Parameters | Rationale |
|----------|------------------|------------|-----------|
| Gary Works BF Success | Beta | α=8, β=3 (70% mean) | Large capex execution risk |
| Mon Valley HSM Success | Beta | α=9, β=2 (80% mean) | Smaller, less complex |
| Greenfield Mini Mill | Beta | α=7, β=4 (65% mean) | Greenfield risk |
| Technology Transfer | Beta | α=6, β=4 (60% mean) | Cross-border knowledge transfer |

### 1.4 Correlation Matrix

Model key relationships between variables:

```python
correlation_matrix = {
    ('hrc_price', 'crc_price'): 0.95,        # CRC follows HRC closely
    ('hrc_price', 'coated_price'): 0.93,     # Coated follows HRC
    ('hrc_price', 'octg_price'): 0.65,       # OCTG linked but more volatile
    ('hrc_price', 'flat_rolled_volume'): 0.40,  # Higher prices → better margins → more production
    ('octg_price', 'tubular_volume'): 0.75,  # Strong oil/gas linkage
    ('us_wacc', 'japan_rf'): -0.30,          # Flight to safety dynamics
    ('hrc_price', 'volume_growth'): 0.55,    # Economic cycle drives both
    ('execution_gary', 'execution_mv'): 0.60,  # Common management capability
}
```

### 1.5 Sampling Strategy

**Latin Hypercube Sampling (LHS)** recommended over simple random sampling:
- Ensures better coverage of probability space
- Fewer iterations needed for convergence (5,000-10,000 vs 50,000+)
- Maintains correlation structure

**Alternative: Sobol Sequences** for quasi-random low-discrepancy sampling

### 1.6 Output Metrics

Generate comprehensive statistics on valuation outputs:

#### Point Estimates
- Mean, Median, Mode
- Standard Deviation
- Coefficient of Variation

#### Percentiles
- P5, P10, P25, P50, P75, P90, P95
- 80% Confidence Interval (P10-P90)
- 95% Confidence Interval (P2.5-P97.5)

#### Risk Metrics
- **VaR (Value at Risk)**: Maximum loss at 95% confidence
- **CVaR (Conditional VaR)**: Expected loss in worst 5% of cases
- **Probability of Loss**: P(Value < $55 offer)
- **Probability of Upside**: P(Value > $75)

#### Distribution Analysis
- Skewness (asymmetry)
- Kurtosis (tail risk)
- Percentile value bands

### 1.7 Implementation Phases

**Phase 1: Core Engine (Week 1-2)**
- Build Monte Carlo sampling infrastructure
- Implement correlation matrix via Cholesky decomposition
- Create wrapper for PriceVolumeModel execution

**Phase 2: Input Calibration (Week 2-3)**
- Calibrate distributions to historical steel prices (1990-2023)
- Validate correlation assumptions with data
- Implement Latin Hypercube sampling

**Phase 3: Output Analytics (Week 3-4)**
- Generate distribution visualizations
- Calculate risk metrics
- Build tornado diagrams

**Phase 4: Dashboard Integration (Week 4-5)**
- Add Monte Carlo tab to Streamlit dashboard
- Interactive distribution parameter controls
- Real-time simulation runner

---

## Strategy 2: Multi-Way Sensitivity Analysis

### 2.1 Objective

Understand interaction effects between key variables through systematic multi-dimensional analysis.

### 2.2 Two-Way Sensitivity Tables

Generate heat maps showing interaction effects:

#### Steel Price × WACC Matrix

```
              WACC 6.5%  7.5%  8.5%  9.5%  10.5%  11.5%
Price 70%      $15.2   $12.8  $10.9  $9.4   $8.2   $7.2
Price 80%      $32.6   $27.1  $22.8  $19.3  $16.6  $14.4
Price 90%      $69.0   $59.0  $51.3  $45.2  $40.1  $35.9
Price 100%    $112.7   $97.4  $85.7  $76.3  $68.6  $62.2
Price 110%    $164.0  $142.4 $125.9 $112.7 $101.9  $92.9
```

**Color coding**: Green (>$70), Yellow ($50-70), Orange ($40-50), Red (<$40)

#### Volume × Price Matrix

Show how volume assumptions interact with price realizations.

#### Execution Factor × Capital Investment

Model the relationship between execution success and investment magnitude.

### 2.3 Three-Way Analysis

Create scenario cubes for the most critical variables:

**Dimensions**: Steel Price × WACC × Volume Growth
- 5 × 5 × 5 = 125 scenarios
- Present as interactive 3D visualization
- Show iso-value surfaces

### 2.4 Tornado Diagrams

Rank variables by impact on valuation variance:

```
Variable                 Low Value    Base    High Value    Swing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Steel Price Factor         $42      $75.8      $118        $76.0
WACC                      $90.2     $75.8      $62.5       $27.7
US Interest Rates         $91.2     $75.8      $63.3       $27.9
Execution Factor          $92.3     $75.8     $109.9       $17.6
Volume Growth             $68.4     $75.8      $83.7       $15.3
Terminal Growth           $71.0     $75.8      $80.5        $9.5
Exit Multiple             $71.8     $75.8      $79.5        $7.7
```

### 2.5 Spider/Radar Charts

Show sensitivity to simultaneous movements in multiple variables:
- Base case at center
- Radial axes for each variable
- Contour lines for value iso-curves

---

## Strategy 3: Scenario Analysis Enhancements

### 3.1 Economic Regime Framework

Define macro scenarios that drive correlated input assumptions:

#### Scenario Archetypes

| Scenario | GDP Growth | Steel Demand | Price Level | WACC | Probability |
|----------|-----------|--------------|-------------|------|-------------|
| **Severe Recession** | -2.0% | -15% | 70% | 12.5% | 5% |
| **Mild Recession** | -0.5% | -5% | 85% | 11.0% | 15% |
| **Sluggish Growth** | 1.5% | +2% | 92% | 10.5% | 25% |
| **Base Case** | 2.5% | +5% | 100% | 10.0% | 30% |
| **Above Trend** | 3.5% | +8% | 108% | 9.5% | 15% |
| **Strong Cycle** | 4.5% | +12% | 120% | 9.0% | 8% |
| **Super Cycle** | 5.0% | +18% | 135% | 8.5% | 2% |

### 3.2 Conditional Scenario Trees

Build decision trees for path-dependent outcomes:

```
Initial State → Year 1-3 Outcome → Year 4-7 Outcome → Year 8-10 Outcome
     ↓              ↓                  ↓                    ↓
  Base Case    Strong (40%)      Sustained (60%)      Terminal Value
                Weak (40%)       Recovery (30%)       Adjusted Values
                Neutral (20%)    Decline (10%)
```

### 3.3 Stress Testing

Define extreme but plausible scenarios:

#### Downside Stress Tests

| Stress Test | Description | Key Assumptions |
|------------|-------------|-----------------|
| **1970s Stagflation** | High inflation, low growth | Price +50%, Volume -20%, WACC +400bp |
| **2008 Financial Crisis** | Demand collapse | Price -45%, Volume -30%, WACC +300bp |
| **China Dumping** | Global oversupply | Price -30%, Volume +5%, Margin -500bp |
| **Failed Integration** | Execution failure | Projects 0% success, Synergies 0% |
| **Trade War** | Tariff retaliation | Volume -15%, Costs +10% |

#### Upside Stress Tests

| Stress Test | Description | Key Assumptions |
|------------|-------------|-----------------|
| **Infrastructure Boom** | Biden/IRA super cycle | Price +40%, Volume +25% |
| **Supply Shock** | Capacity closures | Price +60%, Volume flat |
| **Perfect Execution** | All projects succeed | Execution 100%, Synergies 120% |
| **Rate Convergence** | US/Japan rate parity | WACC -200bp |

### 3.4 Reverse Stress Testing

Ask: "What would have to happen for value to fall below $X?"

- Below $55 offer price
- Below $40 (severe loss)
- Below $25 (catastrophic)

Identify the specific combination of events required.

---

## Strategy 4: Time-Series & Dynamic Analysis

### 4.1 Steel Price Path Modeling

Rather than static price assumptions, model price evolution:

#### Mean-Reverting Process (Ornstein-Uhlenbeck)

```python
dP = θ(μ - P)dt + σdW
```

Where:
- P = steel price
- θ = mean reversion speed (calibrate to historical data)
- μ = long-run equilibrium price ($680 HRC)
- σ = volatility (estimate from 1990-2023 data)
- dW = Brownian motion

**Benefits**:
- Captures cyclicality of steel prices
- Prevents perpetual boom/bust
- More realistic than constant growth

#### Jump-Diffusion Process

Model sudden price shocks (COVID, financial crisis):

```python
dP = μPdt + σPdW + JPdq
```

Where:
- J = jump size distribution (normal, μ=-0.3, σ=0.2)
- dq = Poisson process (λ=0.15, i.e., 15% chance of jump per year)

### 4.2 Autoregressive Scenario Generation

Use ARIMA models to generate realistic price paths based on historical patterns:

```python
P(t) = c + φ₁P(t-1) + φ₂P(t-2) + ... + ε(t)
```

Estimate coefficients from 1990-2023 HRC price data.

### 4.3 Regime-Switching Models

Model transitions between distinct market states:

- **Boom Regime**: High prices, high volatility (30% of time)
- **Normal Regime**: Mid-cycle prices, moderate volatility (50% of time)
- **Bust Regime**: Low prices, high volatility (20% of time)

Transition probabilities estimated from historical data.

---

## Strategy 5: Value at Risk (VaR) & Downside Risk

### 5.1 VaR Metrics

Calculate maximum loss at various confidence levels:

| Confidence Level | Metric | Interpretation |
|------------------|--------|----------------|
| 95% VaR | $48.20 | 95% confident value ≥ $48.20 |
| 99% VaR | $42.15 | 99% confident value ≥ $42.15 |
| 99.9% VaR | $35.80 | 99.9% confident value ≥ $35.80 |

### 5.2 Conditional Value at Risk (CVaR)

Expected loss given we're in the worst X% of outcomes:

```
CVaR₉₅ = E[Value | Value < VaR₉₅]
```

Example: CVaR₉₅ = $44.50 means if we're in worst 5% of cases, expected value is $44.50.

### 5.3 Downside Deviation

Standard deviation of returns below a target (e.g., $55 offer):

```python
DD = sqrt(mean([min(0, r - target)² for r in returns]))
```

### 5.4 Probability of Loss

Calculate specific threshold probabilities:

- P(Value < $55) = Probability offer looks good
- P(Value < $40) = Probability of significant loss
- P(Value > $100) = Probability of major upside

### 5.5 Expected Shortfall Distribution

Visualize the distribution of losses in the tail:

```
For outcomes where Value < $55:
  - Mean shortfall: $8.20
  - Median shortfall: $6.50
  - P90 worst case: -$22.30
```

---

## Strategy 6: Correlation Analysis & Dependencies

### 6.1 Correlation Structure

Implement multi-variate normal sampling with full correlation matrix:

```python
# Define correlation matrix
corr_matrix = np.array([
    #  HRC   CRC  OCTG  Vol  WACC Growth
    [1.00, 0.95, 0.65, 0.40, -0.20, 0.55],  # HRC
    [0.95, 1.00, 0.60, 0.38, -0.18, 0.52],  # CRC
    [0.65, 0.60, 1.00, 0.20, -0.10, 0.35],  # OCTG
    [0.40, 0.38, 0.20, 1.00, -0.15, 0.60],  # Volume
    [-0.20,-0.18,-0.10,-0.15, 1.00, -0.40], # WACC
    [0.55, 0.52, 0.35, 0.60, -0.40, 1.00],  # Growth
])

# Use Cholesky decomposition for sampling
L = np.linalg.cholesky(corr_matrix)
uncorrelated = np.random.normal(0, 1, (n_sims, n_vars))
correlated = uncorrelated @ L.T
```

### 6.2 Copula Methods

For non-normal distributions, use copulas to model correlation:

**Gaussian Copula**: Normal correlation with arbitrary marginals
**t-Copula**: Captures tail dependence (crisis periods)
**Archimedean Copulas**: Flexible dependency structures

### 6.3 Conditional Distributions

Model relationships where one variable depends on another:

```python
# Volume conditional on price level
if hrc_price > $800:
    volume_factor ~ Normal(1.15, 0.10)  # High price → high volume
elif hrc_price < $600:
    volume_factor ~ Normal(0.85, 0.15)  # Low price → low volume
else:
    volume_factor ~ Normal(1.00, 0.12)  # Normal volume
```

### 6.4 Factor Models

Decompose variables into common factors:

```
HRC Price = β₁ * MacroGrowth + β₂ * AutoDemand + β₃ * ChinaSupply + ε₁
Volume = γ₁ * MacroGrowth + γ₂ * CapacityUtil + ε₂
WACC = δ₁ * FedFunds + δ₂ * CreditSpread + ε₃
```

This ensures macro factors drive correlated movements.

---

## Strategy 7: Real Options Analysis (Optional Advanced)

### 7.1 Option to Delay Investment

Value of waiting to invest in Gary Works BF until steel prices improve:

- Option value = E[max(NPV_delay - NPV_now, 0)]
- Binomial tree for price evolution
- Optimal exercise boundary

### 7.2 Option to Expand

Value of option to build additional mini mill capacity if demand exceeds forecasts:

- Trigger: Volume > 12,000k tons for 2 consecutive years
- Investment: $1.8B for 3M ton capacity
- Option premium ≈ $150M

### 7.3 Option to Abandon

Value of being able to shut down Tubular segment if OCTG prices collapse:

- Trigger: OCTG < $2,000/ton for 18 months
- Salvage value: $800M
- Avoided losses: $100M/year

### 7.4 Switching Options

Value of flexibility to shift product mix between segments:

- Flat-Rolled ↔ Coated (relatively easy)
- Integrated ↔ Mini Mill (difficult, long timeframe)

---

## Strategy 8: Implementation Architecture

### 8.1 Modular Design

```
/sensitivity_analysis/
├── __init__.py
├── core/
│   ├── monte_carlo_engine.py       # Core MC simulation
│   ├── distributions.py            # Probability distributions
│   ├── correlation.py              # Correlation handling
│   └── sampling.py                 # LHS, Sobol sampling
├── analysis/
│   ├── risk_metrics.py             # VaR, CVaR, downside risk
│   ├── tornado.py                  # Tornado diagrams
│   ├── two_way.py                  # 2D sensitivity tables
│   └── scenario_generator.py      # Dynamic scenario creation
├── time_series/
│   ├── price_paths.py              # Stochastic price models
│   ├── mean_reversion.py           # Ornstein-Uhlenbeck
│   └── regime_switching.py        # Markov regime models
├── real_options/
│   ├── binomial_tree.py            # Option pricing
│   └── optimal_timing.py           # Timing options
├── visualization/
│   ├── distributions.py            # Histograms, CDFs
│   ├── heatmaps.py                 # 2D sensitivity heat maps
│   └── waterfall.py                # Contribution analysis
└── dashboard/
    ├── monte_carlo_tab.py          # Streamlit MC interface
    ├── sensitivity_tab.py          # Interactive sensitivities
    └── risk_dashboard.py           # Risk metrics display
```

### 8.2 Data Flow

```
Input Distributions → Sampling Engine → Correlation → Model Execution
                                                            ↓
Outputs Database ← Statistics Engine ← Results Collection
     ↓
Dashboard Visualization + Export (PDF, Excel)
```

### 8.3 Performance Optimization

**Challenges**:
- 10,000 iterations × 10-year projections = 100,000 model runs
- Current model execution: ~50ms per run
- Total runtime: ~8-10 minutes

**Optimizations**:

1. **Vectorization**: Run batches of scenarios simultaneously
2. **Caching**: Cache intermediate calculations (D&A, working capital)
3. **JIT Compilation**: Use Numba for hot loops
4. **Parallel Processing**: Use multiprocessing.Pool for CPU parallelization
5. **GPU Acceleration**: Use CuPy for massive parallelization (optional)

Target: <30 seconds for 10,000 iterations

### 8.4 Validation Framework

**Statistical Tests**:
- Convergence diagnostics (running mean stability)
- Correlation matrix verification
- Distribution goodness-of-fit (KS test, Q-Q plots)

**Model Validation**:
- Compare MC mean to deterministic base case
- Verify percentiles match scenario presets
- Backtest against historical valuations

### 8.5 User Interface

**Streamlit Dashboard Tabs**:

1. **Monte Carlo Simulation**
   - Input distribution controls (sliders for μ, σ)
   - Correlation matrix editor
   - Run button with progress bar
   - Results summary (mean, percentiles, VaR)

2. **Distribution Viewer**
   - Histogram of valuation outcomes
   - CDF plot
   - Box plot by scenario type
   - Probability of success metrics

3. **Sensitivity Explorer**
   - Interactive tornado chart
   - Two-way heat maps with hover
   - Spider chart for multi-variable

4. **Risk Dashboard**
   - VaR/CVaR gauges
   - Downside risk metrics
   - Scenario probability tree

5. **Export & Reporting**
   - Generate PDF report
   - Export results to Excel
   - Save simulation configuration

---

## Strategy 9: Calibration & Data Requirements

### 9.1 Historical Data for Calibration

**Steel Prices (1990-2023)**:
- HRC Midwest spot prices (monthly)
- CRC, Coated, OCTG prices
- Calculate: mean, std dev, autocorrelation, volatility

**Volumes**:
- USS historical shipments by segment
- Industry-wide capacity utilization
- Demand correlations with GDP, auto production

**Macro Variables**:
- US Treasury rates (10Y)
- Japan JGB rates
- Credit spreads (BBB industrials)
- GDP growth rates

### 9.2 Distribution Fitting

Use statistical tools to fit distributions to data:

```python
from scipy import stats

# Fit lognormal to HRC prices
params = stats.lognorm.fit(hrc_prices)
mu, sigma = params[2], params[0]

# Goodness-of-fit test
ks_stat, p_value = stats.kstest(hrc_prices, 'lognorm', args=params)
```

### 9.3 Expert Elicitation

Where data is sparse, use structured expert judgment:

**Modified Delphi Method**:
1. Survey 5-7 industry experts
2. Ask for P10, P50, P90 estimates
3. Aggregate using weighted average
4. Fit parametric distribution to percentiles

**Variables Requiring Expert Input**:
- Technology transfer success rates
- Synergy realization probabilities
- Execution risk for greenfield projects
- Market share evolution

### 9.4 Validation Against Comparable Deals

Calibrate distributions to match observed M&A outcomes:

- Synergy realization: 50-70% in steel industry M&A
- Integration costs: 5-15% of deal value
- Execution delays: 25% probability of 6-12 month delay
- Revenue dissynergies: 10% probability of customer loss

---

## Strategy 10: Reporting & Communication

### 10.1 Executive Summary Format

**One-Page Risk Dashboard**:

```
╔═══════════════════════════════════════════════════════════════╗
║  USS/Nippon Merger - Monte Carlo Valuation Summary           ║
║  10,000 Simulations | Base Case Economic Assumptions         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  EXPECTED VALUE (Mean):              $75.80 per share        ║
║  MEDIAN VALUE:                       $73.20 per share        ║
║                                                               ║
║  CONFIDENCE INTERVALS:                                        ║
║    80% CI (P10-P90):        $52.30 - $103.40                 ║
║    95% CI (P2.5-P97.5):     $42.80 - $128.60                 ║
║                                                               ║
║  RISK METRICS:                                                ║
║    VaR (95%):                        $48.20                   ║
║    CVaR (95%):                       $44.50                   ║
║    Probability < $55 Offer:          18.5%                    ║
║    Probability > $100 Upside:        28.3%                    ║
║                                                               ║
║  TOP RISK DRIVERS:                                            ║
║    1. Steel Prices           (45% of variance)                ║
║    2. Interest Rate Spread   (22% of variance)                ║
║    3. Execution Success      (15% of variance)                ║
║    4. Volume Assumptions     (10% of variance)                ║
║    5. All Other              (8% of variance)                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

### 10.2 Distribution Visualization Best Practices

**Chart 1: Histogram with Annotations**
- Show distribution of outcomes
- Mark percentiles (P10, P25, P50, P75, P90)
- Highlight $55 offer price
- Color zones (downside red, neutral yellow, upside green)

**Chart 2: Cumulative Distribution (CDF)**
- X-axis: Valuation
- Y-axis: Cumulative probability
- Allows reading: "85% chance value exceeds $X"

**Chart 3: Tornado Chart**
- Horizontal bars showing variable impact
- Sorted by magnitude
- Show both upside and downside

**Chart 4: Scenario Fan Chart**
- Time series of projected values
- Show P10-P90 band widening over time
- Mean path through middle

### 10.3 Risk Communication

**For Management**:
- Focus on probability of meeting targets
- Emphasize downside protection
- Quantify upside potential

**For Board**:
- VaR and stress test results
- Comparison to offer price
- Risk-adjusted return metrics

**For Investors**:
- Distribution of outcomes
- Probability-weighted expected value
- Comparison to market expectations

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Build Monte Carlo engine core
- [ ] Implement Latin Hypercube sampling
- [ ] Create distribution library (normal, lognormal, triangular, beta)
- [ ] Build correlation matrix handler (Cholesky decomposition)
- [ ] Test with simple 2-variable case

### Phase 2: Integration (Weeks 2-3)
- [ ] Wrap PriceVolumeModel for batch execution
- [ ] Calibrate input distributions from historical data
- [ ] Implement full correlation matrix
- [ ] Validate MC mean matches deterministic base case
- [ ] Performance optimization (target <1 min for 10k sims)

### Phase 3: Analytics (Weeks 3-4)
- [ ] Calculate VaR, CVaR, downside risk metrics
- [ ] Generate tornado diagrams
- [ ] Build two-way sensitivity tables
- [ ] Create distribution visualizations
- [ ] Export functionality (Excel, PDF)

### Phase 4: Advanced Features (Weeks 4-6)
- [ ] Implement time-series price paths (mean reversion)
- [ ] Add regime-switching models
- [ ] Build scenario tree generator
- [ ] Create conditional distributions
- [ ] Real options framework (optional)

### Phase 5: Dashboard Integration (Weeks 6-7)
- [ ] Build Streamlit Monte Carlo tab
- [ ] Interactive distribution controls
- [ ] Real-time simulation runner
- [ ] Risk dashboard with gauges
- [ ] Reporting and export tools

### Phase 6: Validation & Documentation (Week 8)
- [ ] Statistical validation tests
- [ ] Backtest against historical data
- [ ] User acceptance testing
- [ ] Documentation (user guide, technical specs)
- [ ] Training materials

---

## Success Metrics

### Technical Metrics
- Simulation runtime: <60 seconds for 10,000 iterations
- Convergence: Mean stable within 0.1% after 5,000 iterations
- Coverage: Monte Carlo P10-P90 spans deterministic scenarios
- Correlation preservation: <5% error in realized correlations

### Business Metrics
- Valuation range narrows with better data
- Risk metrics inform decision-making
- Stakeholder confidence in valuation
- Sensitivity insights drive strategic discussions

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Model runtime too slow | Low adoption | Vectorization, caching, parallel processing |
| Distributions poorly calibrated | Unreliable results | Robust data analysis, expert elicitation |
| Too complex for users | Low usage | Simplified UI, preset configurations |
| Correlation misspecified | Unrealistic scenarios | Validate with historical data, sensitivity test |
| Black swan events | Model breaks | Stress tests, regime switching, fat tails |

---

## Next Steps

1. **Review & Approve Strategy**: Stakeholder alignment on approach
2. **Prioritize Features**: Select must-have vs nice-to-have
3. **Data Gathering**: Collect historical steel prices, rates, volumes
4. **Proof of Concept**: Build simple 3-variable MC to demonstrate
5. **Full Implementation**: Execute roadmap phases

---

## References & Further Reading

### Monte Carlo Methods
- Hull, J. (2018). *Options, Futures, and Other Derivatives* (10th ed.). Chapter on Monte Carlo simulation.
- Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer.

### Sensitivity Analysis
- Saltelli, A. et al. (2008). *Global Sensitivity Analysis: The Primer*. Wiley.
- Borgonovo, E. & Plischke, E. (2016). "Sensitivity analysis: A review of recent advances." *European Journal of Operational Research*, 248(3), 869-887.

### Real Options
- Copeland, T. & Antikarov, V. (2001). *Real Options: A Practitioner's Guide*. Texere.
- Trigeorgis, L. (1996). *Real Options: Managerial Flexibility and Strategy in Resource Allocation*. MIT Press.

### Steel Industry Analysis
- USS Historical price data (1990-2023)
- AISI Steel Industry reports
- CRU Steel Price forecasts
- World Steel Association data

---

**Document Version:** 1.0
**Last Updated:** 2026-01-31
**Authors:** RAMBAS Team
**Status:** Draft for Review
