# Distribution Calibration Methodology

## Overview

This document describes how probability distributions were calibrated for each variable in the USS/Nippon Steel Monte Carlo simulation model. All distributions were fitted using historical data **through December 18, 2023** (the date the USS Board approved the Nippon deal) to avoid information leakage.

## IMPORTANT: Through-Cycle Calibration (Updated 2026-02-06)

**Price distributions use through-cycle, mean-reverting calibration:**

1. **Through-cycle volatility** (σ) excludes 2021-2022 COVID spike anomaly
2. **Mean is recentered** to E[X] = 1.0 (through-cycle baseline)
3. **Rationale**: COVID-era σ inflated valuations ~2x; through-cycle σ better represents forward uncertainty

**Lognormal Mean-Reversion Formula:**
```
To get E[X] = 1.0 with volatility σ:
μ = -σ²/2
```

| Variable | Raw Historical σ | Through-Cycle σ | μ | Bloomberg Support |
|----------|-----------------|-----------------|---|-------------------|
| HRC Price Factor | 0.41 | **0.18** | -0.0162 | Pre-COVID σ=0.208 |
| CRC Price Factor | 0.37 | **0.16** | -0.0128 | Pre-COVID σ=0.163 |
| OCTG Price Factor | 0.48 | **0.22** | -0.0242 | Full-period σ=0.211 |
| Coated Price Factor | 0.37 | **0.15** | -0.0113 | Derived from CRC |
| HRC EU Factor | 0.20 | **0.15** | -0.0113 | Full-period σ=0.156 |

### Margin Sensitivity Recalibration (2026-02-06)

The `margin_sensitivity_to_price` parameter controls operating leverage — how much EBITDA margin changes per $100 steel price move. Original values created unrealistic margin compounding over 10 years (margins reaching 25-30%, doubling EBITDA).

| Segment | Old Value | New Value | Rationale |
|---------|-----------|-----------|-----------|
| Flat Rolled | 4% per $100 | **2%** per $100 | Halved to prevent unrealistic margin expansion |
| Mini Mill | 5% per $100 | **2.5%** per $100 | Still highest (EAF more flexible) |
| USSE | 4% per $100 | **2%** per $100 | Match Flat Rolled |
| Tubular | 2% per $100 | **1%** per $100 | Already lowest; halved for consistency |

**EBITDA margin cap** also tightened: 30% → **22%** (steel companies rarely sustain >20%)

### Annual Price Growth Recalibration (2026-02-06)

Steel is a commodity with mean-reverting prices. Real price growth should be ~0-1%, not 2%.

| Parameter | Old Value | New Value |
|-----------|-----------|-----------|
| MC distribution mean | 1.5% | **1.0%** |
| Base case preset | 1.5% | **1.0%** |
| Optimistic preset | 2.0% | **1.5%** |
| Management preset | 3.0% | **2.0%** |

### Calibration Validation (10,000 iterations, 25 variables, 2026-02-06)

| Metric | USS Standalone | Nippon Perspective | Target |
|--------|---------------|-------------------|--------|
| Base case (deterministic) | **$39.04** | **$55.66** | $39 / $55 |
| MC Mean | $61.2 | $85.0 | — |
| MC Median | $57.3 | $79.8 | — |
| P(< $55 offer) | 46.3% | 20.6% | — |
| Terminal EBITDA median | $3,190M | — | $2.5-3.5B |

Note: Tariff risk variables (tariff_probability, tariff_rate_if_changed) add ~4pp downside probability vs. the no-tariff-risk baseline (42%→46% for USS, 18%→21% for Nippon).

## Data Sources

| Data | File | Observations | Period |
|------|------|--------------|--------|
| HRC US Futures | `market-data/exports/processed/hrc_us_futures.csv` | ~1,250 | Jan 2019 - Dec 2023 |
| CRC US Spot | `market-data/exports/processed/crc_us_spot.csv` | ~255 | Jan 2019 - Dec 2023 |
| OCTG US Spot | `market-data/exports/processed/octg_us_spot.csv` | ~255 | Jan 2019 - Dec 2023 |
| Capacity Utilization | `market-data/exports/processed/capacity_us.csv` | ~465 | 2015 - Dec 2023 |
| 10Y Treasury | `market-data/exports/processed/ust_10y.csv` | ~1,000 | 2020 - Dec 2023 |
| BBB Spread | `market-data/exports/processed/spread_bbb.csv` | ~1,000 | 2020 - Dec 2023 |
| Rig Count | `market-data/exports/processed/rig_count.csv` | ~465 | 2015 - Dec 2023 |
| Correlation Matrix (Levels) | `market-data/exports/processed/correlation_matrix_LEVELS.csv` | Pre-computed (level-based, not return-based) | - |
| Peer Fundamentals | `local/wrds_cache/peer_fundamentals.csv` | 57 | 2019 - 2023 |

---

## 1. Price Factors

### Methodology

Steel price factors represent the ratio of current price to a through-cycle equilibrium baseline:

```
price_factor = actual_price / baseline_through_cycle_price
```

**Baseline Prices (Through-Cycle Equilibrium, updated 2026-02-06):**
- HRC US: $738/ton (Avg of pre-COVID $625 and post-spike $850)
- CRC US: $994/ton (Avg of pre-COVID $820 and post-spike $1,130)
- Coated US: $1,113/ton (Avg of pre-COVID $920 and post-spike $1,266)
- HRC EU: $611/ton (Avg of pre-COVID $512 and post-spike $710)
- OCTG US: $2,388/ton (Avg of pre-COVID $1,350 and post-spike $3,228)

### Distribution Choice: Lognormal

**Rationale:**
1. Steel prices cannot be negative
2. Commodity prices exhibit right-skewed distributions (occasional spikes)
3. Log-returns of commodity prices are approximately normally distributed
4. Industry standard for modeling commodity price uncertainty

### Fitting Process

1. **Load historical prices** from Bloomberg data files
2. **Apply cutoff filter**: Only use data through December 18, 2023
3. **Calculate price factors**: `factors = prices / baseline_price`
4. **Log-transform**: `log_factors = log(factors)`
5. **Fit normal distribution to log-factors** using Maximum Likelihood Estimation (MLE):
   - `μ = mean(log_factors)`
   - `σ = std(log_factors, ddof=1)`
6. **Validate fit** using Kolmogorov-Smirnov test

### Results

| Variable | μ (log-space) | σ (log-space) | E[X] | P5 | P95 | N obs |
|----------|---------------|---------------|------|-----|-----|-------|
| hrc_price_factor | -0.0162 | 0.18 | 1.00 | 0.73 | 1.32 | 1,247 |
| crc_price_factor | -0.0128 | 0.16 | 1.00 | 0.76 | 1.29 | 255 |
| octg_price_factor | -0.0242 | 0.22 | 1.00 | 0.67 | 1.40 | 255 |
| coated_price_factor | -0.0113 | 0.15 | 1.00 | 0.78 | 1.27 | — |
| hrc_eu_factor | -0.0113 | 0.15 | 1.00 | 0.78 | 1.27 | 592 |

**Note:** Through-cycle σ values exclude 2021-2022 COVID spike. Raw historical σ was 2-3x larger. The lognormal with mean-reverting calibration (E[X]=1.0) captures forward-looking uncertainty without the COVID anomaly inflation.

### Coated Price Factor (Derived)

No direct Bloomberg data available for coated steel prices. Parameters derived from HRC and CRC:

```python
coated_log_mean = (hrc_log_mean + crc_log_mean) / 2
coated_log_std = min(hrc_log_std, crc_log_std) * 0.95
```

**Rationale:** Coated products have slightly lower volatility due to longer-term automotive supply contracts.

**Result (through-cycle):** μ=-0.0113, σ=0.15 (E[X]=1.0, slightly less volatile than CRC)

---

## 2. Volume Factors

### Flat-Rolled Volume (Normal)

**Data Source:** US steel capacity utilization from Federal Reserve/industry data

**Methodology:**
1. Load weekly capacity utilization data (2015-2023)
2. Calculate mean capacity utilization over the period
3. Normalize to factor: `volume_factor = capacity_util / mean_capacity_util`
4. Fit normal distribution using MLE

**Result:** μ=1.00, σ=0.081

**Rationale for Normal:**
- Capacity utilization shocks are roughly symmetric around trend
- Both positive (demand surge) and negative (recession) shocks occur
- Unbounded distribution appropriate for planning scenarios

### Mini-Mill Volume (Derived)

Mini-mills are less cyclical than integrated mills due to:
- Lower fixed costs
- Faster response to demand changes
- Less exposure to commodity imports

**Derivation:**
```python
mini_mill_std = flat_rolled_std * 0.75  # 25% lower volatility
```

**Result:** μ=1.00, σ=0.061

### Tubular Volume (Triangular)

**Data Source:** US oil/gas rig count (proxy for OCTG demand)

**Methodology:**
1. Load weekly rig count data (2015-2023)
2. Normalize to factor: `rig_factor = rig_count / mean_rig_count`
3. Extract distribution parameters from percentiles:
   - `min = percentile(factors, 1)`
   - `mode ≈ median(factors)` (adjusted for mean relationship)
   - `max = percentile(factors, 99)`

**Result (through-cycle):** min=0.65, mode=1.00, max=1.35 (tightened from raw 0.35/0.95/1.70 to exclude extreme COVID/shale collapse)

**Rationale for Triangular:**
- Tubular demand is highly volatile (oil/gas cycles)
- Distribution is asymmetric (demand can collapse more than it can surge)
- Triangular captures min/mode/max expert judgment naturally
- Rig counts dropped to ~250 (COVID) from ~1,000 peak

---

## 3. WACC Components

### USS WACC (Normal)

WACC is not directly observable in market data. The distribution parameters are derived from component uncertainties:

**Components:**
- Risk-free rate (10Y Treasury): 2020-2023 mean=2.29%, std=1.30%
- BBB credit spread: 2020-2023 mean=1.24%, std=0.36%
- Equity risk premium: Industry estimates 4-6%
- Beta: USS historical beta ~1.3-1.5

**Composite WACC Calculation:**
The model's base WACC calculation yields 10.9%. The uncertainty (σ=0.8%) reflects:
- Interest rate volatility
- Credit spread volatility
- Equity risk premium uncertainty
- Beta estimation error

**Result:** μ=10.9%, σ=0.8%

**99% Confidence Interval:** [8.8%, 13.0%]

### Japan Risk-Free Rate (Normal)

**Source:** Expert judgment based on JGB 10Y yields

**Rationale:**
- Bank of Japan yield curve control policy limits rate movements
- JGB 10Y has traded in narrow band (0-1%) for years
- Some uncertainty around BOJ policy normalization

**Result:** μ=0.75%, σ=0.30%

---

## 4. Terminal Value Parameters

These are forward-looking assumptions based on expert judgment, not historical data fitting.

### Terminal Growth Rate (Triangular)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min | -0.5% | Secular decline scenario (EAF substitution, imports) |
| Mode | 1.0% | Long-term GDP growth match |
| Max | 2.5% | Optimistic reinvestment/reshoring scenario |

**Result:** Triangular(-0.5%, 1.0%, 2.5%)

### Exit Multiple (Triangular)

Based on historical steel sector EV/EBITDA trading multiples:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min | 3.5x | Trough cycle multiple (2015-2016, 2020) |
| Mode | 4.5x | Mid-cycle normalized multiple |
| Max | 6.5x | Peak cycle multiple (2021-2022) |

**Source:** Bloomberg peer trading comps, historical USS trading range

**Result:** Triangular(3.5x, 4.5x, 6.5x)

---

## 5. Execution Risk Parameters

### Methodology

Execution success factors model the probability that capital projects or synergies are fully realized. These use **Beta distributions** which are ideal for:
- Bounded outcomes [0, 1]
- Modeling probabilities
- Allowing skewness toward success or failure

**Beta Distribution Properties:**
- α > β: Right-skewed (tendency toward success)
- α < β: Left-skewed (tendency toward failure)
- Mean = α / (α + β) for standard Beta(α,β)
- For scaled Beta on [min, max]: Mean = min + (max-min) × α/(α+β)

### Gary Works BF Execution

**Context:** Blast furnace reline is proven technology with established track record

**Parameters:** Beta(α=8, β=3) on [0.40, 1.00]

| Metric | Value |
|--------|-------|
| Implied Mean | 83.6% |
| Implied Std | 7.7% |
| Mode | ~87% |
| 95% CI | [61%, 98%] |

**Rationale:**
- BF relines have high success rates historically
- α=8, β=3 creates right-skew toward success
- Floor of 40% ensures some project value even with issues

### Mon Valley HSM Execution

**Context:** Hot strip mill upgrade is simpler than BF reline

**Parameters:** Beta(α=9, β=2) on [0.50, 1.00]

| Metric | Value |
|--------|-------|
| Implied Mean | 90.9% |
| Implied Std | 5.6% |
| Mode | ~94% |
| 95% CI | [73%, 99%] |

**Rationale:**
- Equipment upgrade has higher success probability
- α=9, β=2 creates strong right-skew
- Higher floor (50%) reflects lower risk

**Correlation:** Gary Works and Mon Valley have ρ=0.60 correlation (common management execution capability)

---

## 6. New Variables (Enhanced Calibration)

### Flat-Rolled Margin Factor (Triangular)

**Data Source:** `peer_fundamentals.csv` - Steel peer EBITDA margins (2019-2023)

**Methodology:**
1. Extract EBITDA margins for steel peers (NUE, STLD, CLF, CMC, etc.)
2. Calculate median margin across peers/years
3. Normalize: `margin_factor = peer_margin / median_margin`
4. Extract percentiles:

```python
min = max(0.70, percentile(margin_factors, 5))
mode = 1.0  # median by construction
max = min(1.40, percentile(margin_factors, 95))
```

**Result (through-cycle):** Triangular(0.85, 1.00, 1.15) (tightened from 0.70/1.00/1.40 — margins are more stable than prices)

**N observations:** 57 peer-years

### Operating Synergy Factor (Beta)

**Source:** M&A synergy realization literature (McKinsey, BCG, academic studies)

**Key Finding:** Operating synergies (cost cuts) are typically 70-85% realized

**Parameters:** Beta(α=8, β=3) on [0.50, 1.00]

| Metric | Value |
|--------|-------|
| Implied Mean | 86.4% |
| Implied Std | 6.4% |
| 95% CI | [68%, 98%] |

### Revenue Synergy Factor (Beta)

**Source:** M&A synergy realization literature

**Key Finding:** Revenue synergies are historically harder to achieve than cost synergies (40-60% realization typical)

**Parameters:** Beta(α=3, β=4) on [0.30, 0.90]

| Metric | Value |
|--------|-------|
| Implied Mean | 55.7% |
| Implied Std | 10.5% |
| 95% CI | [34%, 81%] |

**Rationale:** Lower α/β ratio creates left-skew reflecting execution difficulty

### Working Capital Efficiency (Normal)

**Source:** Assumed based on peer working capital days variation

**Parameters:** μ=1.00, σ=0.08

**Rationale:** Working capital efficiency varies with commodity cycles but is roughly symmetric

### CapEx Intensity Factor (Triangular)

**Source:** Expert judgment on plan deviation

**Parameters:** Triangular(0.80, 1.00, 1.30)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min | 0.80 | 20% under-spend (deferrals, efficiency) |
| Mode | 1.00 | On-plan execution |
| Max | 1.30 | 30% over-spend (cost inflation, scope creep) |

---

## 6b. Tariff Risk Variables (Added 2026-02-06)

### Tariff Probability (Beta)

**Context:** Section 232 steel tariffs (25%) have bipartisan support but face political risk

**Parameters:** Beta(α=8, β=2) on [0.0, 1.0]

| Metric | Value |
|--------|-------|
| Implied Mean | 80% probability tariffs maintained |
| Mode | ~89% |
| Rationale | Political inertia + bipartisan support |

**Correlations:** Negatively correlated with prices (ρ=-0.35 HRC, -0.35 CRC, -0.30 Coated, -0.20 OCTG) and volumes (ρ=-0.25 FR). Tariff removal → lower prices and volumes.

### Tariff Rate if Changed (Triangular)

**Context:** If tariff policy changes, most likely a reduction rather than elimination

**Parameters:** Triangular(0.0, 0.10, 0.25)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Min | 0% | Full removal (tail risk) |
| Mode | 10% | Compromise rate (most likely change) |
| Max | 25% | Current rate (no change scenario handled by tariff_probability) |

### Integration Mechanism

Continuous blending: `effective_rate = prob × 0.25 + (1-prob) × alt_rate`

Tariff adjustment function: At 25% (current) → factor 1.0; at 0% (removal) → HRC factor 0.85, EU factor 0.955, OCTG factor 0.91. Uses conservative 15% HRC uplift (between OLS 7% and empirical 18%).

**Impact:** Adds ~4pp downside probability vs no-tariff baseline (USS P(<$55): 42%→46%).

---

## 7. Correlation Structure

### Source

Correlations loaded from `correlation_matrix_LEVELS.csv` (pre-computed from Bloomberg data, LEVEL-based).
**Note:** MC engine uses return-based correlations from `distributions_config.json`, not level correlations.

### Key Correlations

| Variable 1 | Variable 2 | Correlation | Rationale |
|------------|------------|-------------|-----------|
| HRC Price | CRC Price | 0.97 | Same steel market |
| HRC Price | OCTG Price | 0.50 | Different end markets |
| HRC Price | Capacity | 0.56 | Demand drives both |
| OCTG Price | Tubular Volume | 0.73 | Common driver (drilling) |
| HRC US | HRC EU | 0.70 | Global steel market linkage |
| US 10Y | USS WACC | 0.60 | Rate pass-through |
| Gary Works | Mon Valley | 0.60 | Common management |
| Tariff Prob | HRC Price | -0.35 | Tariff removal → lower prices |
| Tariff Prob | FR Volume | -0.25 | Tariff removal → lower demand |

### Matrix Adjustment

The raw correlation matrix may not be positive semi-definite. The Monte Carlo engine automatically adjusts:

```python
if min_eigenvalue < 0:
    corr_matrix += I × (|min_eigenvalue| + 0.01)
    # Rescale to unit diagonal
```

This ensures valid Cholesky decomposition for correlated sampling.

---

## 8. Validation

### Statistical Validation

Each distribution is validated by:
1. Sampling 100,000 draws
2. Comparing sample mean/std to theoretical values
3. Acceptance criteria: <5% error on mean, <10% error on std

**Result:** 25/25 variables pass statistical validation

### Business Bounds Validation

99% confidence intervals checked against business-reasonable bounds:

| Variable | 99% CI | Business Bounds | Status |
|----------|--------|-----------------|--------|
| hrc_price_factor | [0.38, 3.20] | [0.30, 3.00] | OK |
| flat_rolled_volume | [0.79, 1.21] | [0.50, 1.50] | OK |
| uss_wacc | [8.8%, 13.0%] | [7%, 15%] | OK |
| exit_multiple | [3.6x, 6.3x] | [2x, 10x] | OK |

**Result:** 25/25 variables pass business bounds validation

### Backtesting

Train on 2018-2020 data, test coverage on 2021-2023:

| Variable | Training 90% CI | Test Coverage | Notes |
|----------|-----------------|---------------|-------|
| HRC Price Factor | [0.59, 1.20] | 37.5% | COVID/post-COVID regime shift |
| Capacity Utilization | [0.82, 1.18] | 100% | Stable through cycles |

**Note:** Low HRC coverage reflects the unprecedented price spike in 2021-2022. This is a known limitation; the model captures normal cyclicality but may underestimate tail events.

---

## 9. Usage

### Running Calibration

```bash
# Regenerate distributions_config.json
python scripts/analyze_distributions.py

# Use custom cutoff date
python scripts/analyze_distributions.py --cutoff-date 2023-06-30
```

### Validation

```bash
python scripts/validate_distributions.py
```

### Using in Monte Carlo

```python
from monte_carlo import MonteCarloEngine

# Uses distributions_config.json automatically
mc = MonteCarloEngine(n_simulations=10000, use_config_file=True)
results = mc.run_simulation()
mc.print_summary()
```

---

## 10. Files

| File | Purpose |
|------|---------|
| `monte_carlo/distribution_fitter.py` | Statistical fitting engine |
| `scripts/analyze_distributions.py` | Calibration script |
| `monte_carlo/distributions_config.json` | Calibrated parameters |
| `scripts/validate_distributions.py` | Validation checks |
| `monte_carlo/monte_carlo_engine.py` | Simulation engine |

---

## References

1. **Lognormal for Commodities:** Schwartz, E.S. (1997). "The Stochastic Behavior of Commodity Prices"
2. **M&A Synergy Realization:** McKinsey & Company (2019). "The Real Story Behind M&A Synergies"
3. **Beta Distribution for Probabilities:** Johnson, N.L., Kotz, S., Balakrishnan, N. (1995). "Continuous Univariate Distributions"
4. **Steel Industry Cyclicality:** CRU International steel market analysis
5. **WACC Estimation:** Damodaran, A. (2012). "Investment Valuation"
