# Advanced Demand Driver Analysis

## Granger Causality, VAR Models, and Macro-Conditioned Model Integration

*Generated: 2026-02-07*

---

## 1. Overview

This analysis extends the Phase 2 demand driver correlation study with:
- **Granger causality tests** to establish temporal precedence (not true causality)
- **Subperiod stability checks** to verify robustness across market regimes
- **Rolling window analysis** to detect structural breaks
- **Parsimonious VAR models** with Impulse Response Functions and Variance Decomposition
- **Macro-conditioned Monte Carlo integration** (3 new stochastic variables)

**Key constraint:** N=40 quarterly observations (FY2015-2024). This limits VAR to 2-3 variables
with lag order p<=2. All confidence intervals are wider than ideal. Results should be interpreted
as directional, not precise point estimates.

## 2. Granger Causality Tests

**Method:** Bivariate Granger test on revenue residuals (after removing HRC price effect).
Tests whether each indicator's past values help predict future revenue beyond what
HRC price already explains.

**Key Results:**

| Indicator | Best Lag | F-stat | p-value | Significant? |
|-----------|:-------:|:------:|:-------:|:------------:|
| Scrap PPI | 1Q | 17.80 | 0.0002 | Yes (p<0.001) |
| WTI Crude | 1Q | 16.90 | 0.0002 | Yes (p<0.001) |
| Steel Import Price | 2Q | 10.25 | 0.0004 | Yes (p<0.001) |
| Durable Goods Orders | 2Q | 7.41 | 0.0024 | Yes (p<0.01) |
| Trade Balance (Goods) | 1Q | 9.36 | 0.0043 | Yes (p<0.01) |
| Rig Count | 1Q | 6.95 | 0.0125 | Yes (p<0.05) |
| Housing Starts | 1Q | 6.31 | 0.0168 | Yes (p<0.05) |
| Auto Production | 1Q | 4.63 | 0.0386 | Yes (p<0.05) |

**Interpretation:** 8 of 16 indicators Granger-cause revenue (p<0.05) after removing HRC price.
Top predictors align with economic theory:
- **WTI Crude** -> energy capex -> OCTG demand (1Q lead)
- **Durable Goods Orders** -> forward manufacturing demand (2Q lead)
- **Rig Count** -> direct OCTG demand (1Q lead)
- **Scrap PPI** -> cost channel / EAF competitiveness (1Q lead)

## 3. Subperiod Stability

Pre-COVID (2015-2019) vs Post-COVID (2020-2024) partial correlations:

- **13 of 16 indicators stable** across subperiods
- **3 unstable:** WTI Crude, Durable Goods Orders, Building Permits
- WTI and Durable Goods show *sign changes* -- their relationship with revenue shifted post-COVID
  (likely due to supply chain disruptions and OCTG market restructuring)

**Implication:** Use WTI and Durable Goods with caution in forward-looking models. Their
predictive power is real but regime-dependent. The macro-conditioned volume adjustment betas
are calibrated from full-period data with +/-15% caps to limit exposure to regime-specific effects.

## 4. VAR Model Results

### 4a. Stationarity

| Series | ADF p-value | Stationary? | Action |
|--------|:----------:|:-----------:|--------|
| Revenue | 0.252 | No | First-differenced |
| HRC Price | 0.114 | No | First-differenced |
| WTI Crude | ~0.1 | No | First-differenced |

### 4b. Model 1: Bivariate [HRC, Revenue]

- **Lag order:** p=1 (AIC-selected)
- **Observations:** 36 (after differencing)
- **Stable:** Yes (all eigenvalues inside unit circle)
- **Ljung-Box:** Pass (no residual autocorrelation)

### 4c. Model 2: Trivariate [HRC, WTI, Revenue]

- **Lag order:** p=2 (AIC-selected)
- **Observations:** ~34
- **Stable:** Yes
- Adds energy channel to capture OCTG demand dynamics

### 4d. Impulse Response Functions

**HRC Price Shock -> Revenue:**
- Peak response at Q1 (same quarter to +1Q)
- Revenue responds positively and persistently
- Consistent with existing finding: revenue elasticity ~0.60 to HRC price

**WTI Crude Shock -> Revenue (Model 2):**
- Smaller, delayed response (peaks at Q1-Q2)
- Consistent with 2Q lag in OCTG contracts
- Confirms OCTG/energy capex as separate demand channel

### 4e. Forecast Error Variance Decomposition

At 8Q horizon, HRC price explains **62%** of revenue forecast error in the bivariate VAR.
This is lower than the static R^2 (73%) because:
1. VAR uses first-differenced data (removes trend co-movement)
2. Revenue has its own autoregressive momentum
3. Adding WTI captures ~5-8% additional variance

## 5. Macro-Conditioned Model Integration

### 5a. New Monte Carlo Variables

Based on this analysis, we integrated 3 macro demand driver variables (26 -> **29 total**):

| Variable | Distribution | sigma | Channel | Granger p-value |
|----------|:----------:|:--:|---------|:-----------:|
| wti_factor | Lognormal(mu=-sigma^2/2, sigma=0.25) | 0.25 | Energy capex -> OCTG | 0.0002 |
| gdp_growth_factor | Normal(1.0, 0.015) | 0.015 | Broad demand | N/A |
| durable_goods_factor | Normal(1.0, 0.10) | 0.10 | Forward mfg demand | 0.0024 |

### 5b. Volume Adjustment Mechanism

Macro variables condition volume factors through empirically-calibrated beta coefficients:

```
volume_adj = beta_gdp * (gdp_factor - 1.0) + beta_dg * (durable_factor - 1.0) + beta_wti * (wti_factor - 1.0)
adjusted_volume = base_volume * (1 + clip(volume_adj, -0.15, +0.15))
```

| Segment | beta_GDP | beta_Durable | beta_WTI | Rationale |
|---------|:-----:|:---------:|:-----:|-----------|
| Flat-Rolled | 0.8 | 0.5 | 0.1 | Auto/construction driven |
| Mini Mill | 0.6 | 0.4 | 0.1 | Mfg/construction |
| USSE | 0.5 | 0.2 | 0.05 | European macro |
| Tubular | 0.3 | 0.1 | 0.8 | Oil/gas dominant |

### 5c. New Correlations

| Variable | Correlates With | r | Source |
|----------|----------------|:-:|--------|
| wti_factor | octg_price_factor | 0.45 | WTI drives OCTG pricing |
| wti_factor | tubular_volume | 0.35 | Drilling -> OCTG volume |
| wti_factor | hrc_price_factor | 0.25 | Energy cost channel |
| gdp_growth_factor | flat_rolled_volume | 0.30 | Broad demand |
| gdp_growth_factor | hrc_price_factor | 0.20 | Price co-movement |
| durable_goods_factor | flat_rolled_volume | 0.35 | Mfg demand |
| durable_goods_factor | hrc_price_factor | 0.25 | Price co-movement |

### 5d. Pre-Built Macro Scenarios

| Scenario | GDP Factor | WTI Factor | Durables Factor | PMI | Effect |
|----------|:---------:|:----------:|:---------------:|:---:|--------|
| Recession | 0.955 | 0.60 | 0.85 | 45 | FR -15%, Tub -15% |
| Base Macro | 1.000 | 1.00 | 1.00 | 52 | No change |
| Energy Boom | 1.005 | 1.27 | 1.05 | 55 | FR +3%, Tub +12% |

### 5e. Design Decisions

1. **Additive, not replacement:** Macro adjustments add to existing volume sampling
2. **Capped at +/-15%:** Prevents macro extremes from dominating volume
3. **Backward compatible:** If new variables not in config, `sample.get()` returns 1.0
4. **wti_factor <-> tubular_volume correlation reduced to 0.35** (from theoretical 0.55) to avoid
   double-counting with beta adjustment

## 6. Limitations & Caveats

1. **N=40 is small** for time series analysis. VAR limited to 2-3 variables, lag p<=2.
2. **Granger causality != true causality.** Establishes temporal precedence only.
3. **COVID structural break** (2020Q2-Q3) may distort relationships.
4. **Price dominance:** Macro adds ~21.5pp to R^2 (73% -> 95%), but prices dominate.
5. **Segment heterogeneity:** Tubular (oil-driven) != Flat-Rolled (auto/construction).
6. **Beta calibration uncertainty:** MACRO_VOLUME_BETAS are approximate elasticities.
7. **WTI and Durable Goods unstable** across subperiods (sign changes post-COVID).

## 7. Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `scripts/advanced_demand_analysis.py` | Created | Granger, VAR, IRF, subperiod analysis |
| `price_volume_model.py` | Modified | Added MacroScenario, apply_macro_adjustments() |
| `monte_carlo/monte_carlo_engine.py` | Modified | Added 3 macro variables to sampling + adjustment |
| `monte_carlo/distributions_config.json` | Modified | Added wti/gdp/durable distributions + correlations |
| `interactive_dashboard.py` | Modified | Added demand analysis section to Risk tab |
| `audit-verification/ADVANCED_DEMAND_ANALYSIS.md` | Created | This report |
| `charts/granger_causality_summary.png` | Created | Granger p-value chart |
| `charts/subperiod_stability.png` | Created | Pre/Post-COVID comparison |
| `charts/rolling_correlations.png` | Created | 12Q rolling correlations |
| `charts/var_impulse_response.png` | Created | IRF plots |
| `charts/var_fevd.png` | Created | Variance decomposition |
