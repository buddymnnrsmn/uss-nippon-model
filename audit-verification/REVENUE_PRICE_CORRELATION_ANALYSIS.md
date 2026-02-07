# USS Revenue vs Steel Price Correlation Analysis

*Generated: 2026-02-07 16:38*

## 1. Quarterly Revenue vs HRC Price

**Observations:** 40 quarters (FY2015-FY2024)

### Lag Analysis (Revenue vs Price)

| Price Type | Best Lag (Q) | Pearson r | R² | p-value | n |
|------------|:-----------:|:---------:|:--:|:-------:|:-:|
| HRC US | 0 | 0.857*** | 0.734 | 0.0000 | 38 |
| CRC US | 0 | 0.895*** | 0.801 | 0.0000 | 38 |
| HRC EU | 0 | 0.928*** | 0.862 | 0.0000 | 40 |
| OCTG US | 2 | 0.837*** | 0.700 | 0.0000 | 39 |

*Significance: \*p<0.05, \*\*p<0.01, \*\*\*p<0.001*

**Key Finding:** Concurrent HRC US price explains **73%** of quarterly revenue variation (r=0.86, p=0.0000).
No improvement with 1-quarter lag (R²=0.404), suggesting revenue responds quickly to spot price changes.

## 2. Segment-Level Correlations (Annual, 2019-2023)

**Note:** Only 5 annual observations — directional indicators, not statistically robust.

| Segment | Metric | Benchmark | r | p-value | n |
|---------|--------|-----------|:-:|:-------:|:-:|
| Flat-Rolled | Revenue | CRC US | 0.85 | 0.071 | 5 |
| Flat-Rolled | EBITDA Margin | CRC US | 0.96* | 0.011 | 5 |
| Flat-Rolled | Rev/Ton | CRC US | 0.89* | 0.041 | 5 |
| Flat-Rolled | Realized Price | CRC US | 0.89* | 0.041 | 5 |
| Mini Mill | Revenue | HRC US | 0.73 | 0.164 | 5 |
| Mini Mill | EBITDA Margin | HRC US | 0.94* | 0.019 | 5 |
| Mini Mill | Rev/Ton | HRC US | 0.78 | 0.124 | 5 |
| Mini Mill | Realized Price | HRC US | 0.77 | 0.124 | 5 |
| USSE | Revenue | HRC EU | 0.93* | 0.023 | 5 |
| USSE | EBITDA Margin | HRC EU | 0.94* | 0.018 | 5 |
| USSE | Rev/Ton | HRC EU | 0.95* | 0.012 | 5 |
| USSE | Realized Price | HRC EU | 0.95* | 0.012 | 5 |
| Tubular | Revenue | OCTG US | 0.86 | 0.064 | 5 |
| Tubular | EBITDA Margin | OCTG US | 0.90* | 0.036 | 5 |
| Tubular | Rev/Ton | OCTG US | 0.83 | 0.081 | 5 |
| Tubular | Realized Price | OCTG US | 0.83 | 0.081 | 5 |

## 3. Model Assumption Validation

### Realization Factors (Realized Price / Benchmark Price)

| Segment | Empirical Mean | Empirical Range | Model | Difference |
|---------|:--------------:|:---------------:|:-----:|:----------:|
| Flat-Rolled | 1.02 | 0.75-1.19 | 1.04 | -0.02 |
| Mini Mill | 1.06 | 0.80-1.25 | 0.99 | +0.07 |
| USSE | 0.99 | 0.76-1.18 | 1.04 | -0.05 |
| Tubular | 1.10 | 0.77-1.36 | 1.31 | -0.21 |

### Margin Sensitivity (pp per $100 price change)

| Segment | Empirical* | Model | Ratio | Assessment |
|---------|:----------:|:-----:|:-----:|------------|
| Flat-Rolled | 4.3% | 2.0% | 2.1x | Conservative (appropriate) |
| Mini Mill | 2.8% | 2.5% | 1.1x | Conservative (appropriate) |
| USSE | 3.8% | 2.0% | 1.9x | Conservative (appropriate) |
| Tubular | 2.1% | 1.0% | 2.1x | Conservative (appropriate) |

*Empirical includes volume + operating leverage; model isolates price effect with volume constant.*

### Revenue Elasticity to HRC Price

- **Slope:** $2.6M revenue per $1/ton HRC change (SE: $0.3M)
- **Elasticity:** 0.60 (1% HRC change → 0.60% revenue change)
- **Interpretation:** USS revenue is moderately sensitive to steel prices

## 4. Conclusions

1. **Strong quarterly revenue-price correlation** validates the price-volume model's core assumption
2. **Realization factors** are empirically supported within the observed range
3. **Model margin sensitivity is conservative** (empirical 1.1-2.1x higher), appropriate for projections
4. **Limited lag effect** — revenue responds within the same quarter as price changes
