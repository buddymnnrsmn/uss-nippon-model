# USS Demand Driver Analysis: Macro Indicators vs Revenue

*Generated: 2026-02-07 21:41*

## 1. Overview

This analysis correlates USS quarterly revenue (WRDS, FY2015-2024, 40 observations) with
macroeconomic demand indicators to identify drivers beyond steel prices. The goal is to
decompose revenue into **price effects** (already captured by the price-volume model) and
**volume/demand effects** driven by end-market activity.

## 2. Indicator Correlations with Revenue (Best Lag)

| Indicator | Category | Best Lag | r | p-value | n | Channel |
|-----------|----------|:-------:|:--:|:-------:|:-:|---------|
| Steel Import Price | price | 0Q | 0.94*** | 0.0000 | 40 | Import competition / global price |
| Scrap PPI | cost | 1Q | 0.93*** | 0.0000 | 40 | EAF cost input / price co-movement |
| WTI Crude | energy | 0Q | 0.87*** | 0.0000 | 40 | Energy capex → OCTG/tubular demand |
| Trade Balance (Goods) | trade | 1Q | -0.83*** | 0.0000 | 40 | Trade deficit → import pressure |
| Building Permits | demand | 2Q | 0.81*** | 0.0000 | 40 | Leading indicator for housing/construction |
| Housing Starts | demand | 2Q | 0.77*** | 0.0000 | 40 | Construction (~40% of steel demand) |
| Durable Goods Orders | demand | 0Q | 0.77*** | 0.0000 | 40 | Forward-looking mfg demand |
| Auto Production | demand | 4Q | -0.69*** | 0.0000 | 40 | Auto (~25% of steel demand) |
| Real GDP | activity | 0Q | 0.67*** | 0.0000 | 40 | Macro backdrop |
| Mfg Industrial Prod | activity | 4Q | -0.59*** | 0.0001 | 40 | Manufacturing-specific output |
| Auto Sales | demand | 4Q | -0.57*** | 0.0001 | 40 | Auto (leading indicator for production) |
| Rig Count | energy | 4Q | -0.57*** | 0.0001 | 40 | Drilling activity → OCTG demand |
| Industrial Production | activity | 4Q | -0.53*** | 0.0005 | 40 | Broad manufacturing output |
| Steel Capacity Util | supply | 0Q | 0.51*** | 0.0009 | 40 | Supply tightness → pricing power |
| ISM PMI | activity | 2Q | 0.45** | 0.0033 | 40 | Manufacturing activity (broad demand) |
| Non-Res Construction | demand | 0Q | 0.45** | 0.0036 | 40 | Commercial/infrastructure steel |

*Significance: \*p<0.05, \*\*p<0.01, \*\*\*p<0.001*

## 3. Price vs Volume Decomposition

**HRC US price alone explains 73% of revenue variance.**
The remaining variance is driven by volume changes and other factors.

| Indicator | Full r | Partial r (price removed) | Volume r | Interpretation |
|-----------|:------:|:------------------------:|:--------:|----------------|
| WTI Crude | 0.87 | 0.69* | -0.02 | Predicts volume independently of price |
| Durable Goods Orders | 0.76 | 0.65* | 0.04 | Predicts volume independently of price |
| Non-Res Construction | 0.44 | 0.55* | 0.14 | Predicts volume independently of price |
| Real GDP | 0.67 | 0.54* | -0.03 | Predicts volume independently of price |
| Steel Import Price | 0.94 | 0.51* | -0.20 | Predicts volume independently of price |
| ISM PMI | 0.19 | -0.44* | -0.62* | Predicts volume independently of price |
| Industrial Production | 0.36 | 0.43* | 0.21 | Predicts volume independently of price |
| Trade Balance (Goods) | -0.76 | -0.41* | 0.21 | Predicts volume independently of price |
| Rig Count | 0.04 | 0.34* | 0.32* | Predicts volume independently of price |
| Auto Production | -0.59 | -0.25 | 0.31 | Weak or ambiguous signal |
| Auto Sales | -0.54 | -0.22 | 0.22 | Weak or ambiguous signal |
| Scrap PPI | 0.88 | 0.21 | -0.56* | Volume signal present |
| Building Permits | 0.72 | 0.13 | -0.47* | Driven by price co-movement, not volume |
| Mfg Industrial Prod | 0.08 | 0.12 | 0.14 | Weak or ambiguous signal |
| Steel Capacity Util | 0.50 | 0.12 | -0.24 | Driven by price co-movement, not volume |
| Housing Starts | 0.70 | 0.11 | -0.47* | Driven by price co-movement, not volume |

### Key Volume Predictors (independent of price)

- **WTI Crude** (partial r=0.69): Energy capex → OCTG/tubular demand
- **Durable Goods Orders** (partial r=0.65): Forward-looking mfg demand
- **Non-Res Construction** (partial r=0.55): Commercial/infrastructure steel
- **Real GDP** (partial r=0.54): Macro backdrop
- **Steel Import Price** (partial r=0.51): Import competition / global price
- **ISM PMI** (partial r=-0.44): Manufacturing activity (broad demand)
- **Industrial Production** (partial r=0.43): Broad manufacturing output
- **Trade Balance (Goods)** (partial r=-0.41): Trade deficit → import pressure
- **Rig Count** (partial r=0.34): Drilling activity → OCTG demand

## 4. Multivariate Model

**Price-only model:** R² = 0.734 (adj R² = 0.727)
**Price + macro model:** R² = 0.949 (adj R² = 0.939)
**Incremental R²:** +0.215 (21.5pp additional variance explained)
**Observations:** 38

**Features used:**
- hrc_price: coefficient = 1.97
- Auto Production: coefficient = 1.32
- Auto Sales: coefficient = -48.67
- Housing Starts: coefficient = -0.43
- ISM PMI: coefficient = -24.61
- WTI Crude: coefficient = 33.49

**Conclusion:** Macro indicators add meaningful explanatory power beyond steel prices. Volume/demand effects account for a significant portion of revenue variation.

## 5. Implications for the Model

1. **Steel prices remain the dominant driver** — the price-volume model's core assumption is validated
2. **Volume effects exist but are secondary** — end-market indicators can refine volume forecasts
3. **Leading indicators identified:**
   - Rig Count (volume r=0.32): Drilling activity → OCTG demand
   - Auto Production (volume r=0.31): Auto (~25% of steel demand)
   - Auto Sales (volume r=0.22): Auto (leading indicator for production)
4. **OCTG/Tubular demand** is best predicted by rig count and WTI crude (lagged 2Q)
5. **Construction steel** demand links to housing starts and building permits
