# Steel Price Methodology

## Executive Summary

Steel prices are the **single most important driver** of valuation in this model, with an elasticity of **5.5x** - meaning a 1% change in steel prices drives a 5.5% change in equity value. This document explains how steel prices are modeled, why they matter so much, and how to interpret the results.

**Key Findings:**
- A ±10% steel price swing moves valuation by **$20-30 per share** (~50% change)
- Price elasticity: **5.5x** (highest of all model inputs)
- Valuation range across realistic scenarios: **$26/share to $142/share**
- Steel prices drive 70%+ of valuation variance across scenarios

---

## Table of Contents

1. [Model Architecture](#model-architecture)
2. [Benchmark Price System](#benchmark-price-system)
3. [Price Factor Adjustments](#price-factor-adjustments)
4. [Price Premium Structure](#price-premium-structure)
5. [Full Price Calculation](#full-price-calculation)
6. [Sensitivity Analysis](#sensitivity-analysis)
7. [Why Steel Prices Dominate Valuation](#why-steel-prices-dominate-valuation)
8. [Scenario Comparison](#scenario-comparison)
9. [Practical Implications](#practical-implications)

---

## Model Architecture

### Three-Layer Price System

The model uses a **three-layer system** to calculate realized steel prices:

```
Layer 1: Benchmark Prices (2023 actuals)
         ↓
Layer 2: Price Factors (scenario adjustments)
         ↓
Layer 3: Price Premiums (product mix)
         ↓
      Realized Price
```

**Code Location:** `price_volume_model.py:643-650`

```python
def calculate_segment_price(self, segment: Segment, year: int) -> float:
    """Calculate realized price for a segment in a given year"""
    seg = self.segments[segment]
    benchmark_price = self.get_benchmark_price(seg.benchmark_type, year)

    # Apply segment premium and specific growth
    realized_price = benchmark_price * (1 + seg.price_premium_to_benchmark)

    return realized_price
```

---

## Benchmark Price System

### What are Benchmark Prices?

**Definition:** Industry-standard spot prices for commodity steel products as of 2023.

**Source:** Market pricing data from Platts, CRU, and other steel market indices.

### 2023 Benchmark Prices (Base Year)

| Benchmark | Price ($/ton) | Product | Market |
|-----------|---------------|---------|--------|
| **HRC US** | $680 | Hot-Rolled Coil | US Midwest |
| **CRC US** | $850 | Cold-Rolled Coil | US Midwest |
| **Coated US** | $950 | Galvanized/Coated | US Midwest |
| **HRC EU** | $620 | Hot-Rolled Coil | European |
| **OCTG** | $2,800 | Oil Country Tubular Goods | Global |

**Code Location:** `price_volume_model.py:44-51`

```python
BENCHMARK_PRICES_2023 = {
    'hrc_us': 680,      # US HRC Midwest
    'crc_us': 850,      # US CRC
    'coated_us': 950,   # US Coated/Galvanized
    'hrc_eu': 620,      # EU HRC
    'octg': 2800,       # OCTG (Oil Country Tubular Goods)
}
```

### Why 2023 as Base Year?

**Pros:**
- Most recent full-year actual data
- Post-COVID market normalization
- Reflects current cost structure

**Cons:**
- 2023 prices were **elevated** coming off 2021-2022 highs
- Historical mid-cycle HRC might be $600-650 vs. $680
- Creates upward bias if not adjusted

**Model Solution:** Price factors allow scaling these benchmarks up/down for different scenarios.

---

## Price Factor Adjustments

### What are Price Factors?

**Definition:** Multipliers applied to benchmark prices to reflect different market conditions.

**Purpose:** Model different steel market scenarios (recession, mid-cycle, boom) without re-calibrating the entire model.

### Price Factor Formula

```python
adjusted_benchmark = benchmark_2023 * price_factor * (1 + annual_growth)^years
```

**Example:**
```
Base HRC = $680/ton
Price Factor = 0.95 (5% below 2023)
Year 2024 (years=0):
Adjusted HRC = $680 × 0.95 × (1.005)^0 = $646/ton
```

### Price Factor Interpretation

| Factor | Meaning | HRC Price | Market Condition |
|--------|---------|-----------|------------------|
| **0.70** | Deep recession | $476/ton | -30% from 2023 - oversupply, demand collapse |
| **0.80** | Recession | $544/ton | -20% from 2023 - weak demand |
| **0.85** | Conservative | $578/ton | -15% from 2023 - below mid-cycle |
| **0.90** | Mild downturn | $612/ton | -10% from 2023 - soft market |
| **0.95** | Base Case | $646/ton | -5% from 2023 - mid-cycle normalization |
| **1.00** | 2023 Levels | $680/ton | Maintain 2023 pricing |
| **1.05** | Management | $714/ton | +5% from 2023 - recovery |
| **1.10** | Strong market | $748/ton | +10% from 2023 - tight supply |
| **1.20** | Boom | $816/ton | +20% from 2023 - undersupply |
| **1.30** | Super cycle | $884/ton | +30% from 2023 - extreme tightness |

### Price Factors by Scenario

| Scenario | HRC Factor | EU Factor | OCTG Factor | Philosophy |
|----------|------------|-----------|-------------|------------|
| **Conservative** | 0.85 | 0.80 | 0.85 | Downside protection - weak demand |
| **Base Case** | 0.95 | 0.92 | 0.95 | Mid-cycle - slight normalization |
| **Wall Street** | 0.92 | 0.90 | 0.95 | Analyst consensus - modest weakness |
| **Management** | 0.92 | 0.90 | 0.95 | Dec 2023 projections ($700-750 HRC) |
| **Nippon** | 0.95 | 0.92 | 0.95 | Stable pricing + capacity discipline |

**Code Location:** `price_volume_model.py:195-302`

### Annual Price Growth

After applying the initial factor, prices grow annually:

```python
price_year_t = benchmark * factor * (1 + annual_growth)^t
```

**Typical Values:**
- Conservative: 1.0% (barely keeps pace with costs)
- Base Case: 0.5% (minimal real growth)
- Management: 0.0% (flat pricing assumption)
- Nippon: 1.5% (capacity discipline drives pricing power)

**Interpretation:**
- Steel is a mature, cyclical commodity
- Long-term real price growth is minimal (0-2%)
- Inflation-adjusted prices have been flat/declining for decades

---

## Price Premium Structure

### What are Price Premiums?

**Definition:** The markup USS realizes over commodity benchmarks due to:
1. Product mix (value-added products vs. commodity)
2. Customer relationships and contract pricing
3. Quality premiums and certifications
4. Geographic advantages (freight savings)

### Premium Formula

```python
realized_price = benchmark * (1 + premium_to_benchmark)
```

### Premiums by Segment

| Segment | Benchmark | 2023 Realized | Premium | Explanation |
|---------|-----------|---------------|---------|-------------|
| **Flat-Rolled** | $680 HRC | $1,030/ton | **+51.5%** | Product mix: CRC (25%), Coated (40%), HRC (35%) |
| **Mini Mill** | $680 HRC | $875/ton | **+28.7%** | High-quality HRC, some CRC, construction grades |
| **USSE** | $620 EU HRC | $873/ton | **+40.8%** | Automotive-grade, higher EU product mix |
| **Tubular** | $2,800 OCTG | $3,137/ton | **+12.0%** | Premium connections, specialized grades |

**Code Location:** `price_volume_model.py:464-531`

### How Premiums are Calibrated

**Method:** Back-calculated from 2023 actual realized prices:

```python
# Flat-Rolled example:
observed_price = $1,030/ton (from USS 10-K)
benchmark = $680 HRC
premium = ($1,030 / $680) - 1 = 0.515 = 51.5%
```

**Validation:**
- ✓ Matches product mix disclosure in USS 10-K
- ✓ Consistent with industry pricing structure
- ✓ Coated products typically trade +35-40% over HRC
- ✓ CRC typically trades +20-25% over HRC

### Why Flat-Rolled Has Highest Premium

**Product Mix Breakdown (estimated):**
- 35% Hot-Rolled Coil (HRC) - benchmark product
- 25% Cold-Rolled Coil (CRC) - +25% price premium
- 40% Coated/Galvanized - +40% price premium

**Weighted Average:**
```
= 35% × $680 + 25% × $850 + 40% × $950
= $238 + $212 + $380
= $830/ton base + USS quality premium
≈ $1,030/ton realized
```

### Premium Stability

**Key Assumption:** Premiums are **held constant** across all scenarios.

**Rationale:**
- Product mix doesn't change significantly year-to-year
- USS's value proposition (quality, service, proximity) is stable
- Historical data shows premiums compress in downturns but not dramatically

**Limitation:**
In severe recessions, premiums typically compress as customers trade down. The model doesn't capture this, which may **overstate revenue in downside scenarios**.

---

## Full Price Calculation

### Complete Formula

```python
realized_price = (
    benchmark_2023
    × price_factor
    × (1 + annual_growth)^years
    × (1 + premium_to_benchmark)
)
```

### Step-by-Step Example: Flat-Rolled, 2027, Base Case

**Step 1: Get Benchmark**
```python
benchmark_2023['hrc_us'] = $680/ton
```

**Step 2: Apply Price Factor (Base Case = 0.95)**
```python
adjusted_benchmark = $680 × 0.95 = $646/ton
```

**Step 3: Apply Annual Growth (0.5% for 3 years)**
```python
years_from_base = 2027 - 2024 = 3
price_with_growth = $646 × (1.005)^3 = $655.76/ton
```

**Step 4: Apply Premium (+51.5%)**
```python
realized_price = $655.76 × 1.515 = $993.47/ton
```

**Result:** Flat-Rolled realizes **$993/ton** in 2027 under Base Case scenario.

### Code Implementation

**Location:** `price_volume_model.py:621-650`

```python
def get_benchmark_price(self, benchmark_type: str, year: int) -> float:
    """Calculate benchmark price for a given year"""
    base_price = BENCHMARK_PRICES_2023.get(benchmark_type, 700)
    price_scenario = self.scenario.price_scenario

    # Get the factor for this benchmark
    factor_map = {
        'hrc_us': price_scenario.hrc_us_factor,
        'crc_us': price_scenario.crc_us_factor,
        'coated_us': price_scenario.coated_us_factor,
        'hrc_eu': price_scenario.hrc_eu_factor,
        'octg': price_scenario.octg_factor,
    }

    initial_factor = factor_map.get(benchmark_type, 1.0)
    years_from_base = year - 2024

    # Apply initial factor then annual growth
    price = base_price * initial_factor * ((1 + price_scenario.annual_price_growth) ** years_from_base)

    return price

def calculate_segment_price(self, segment: Segment, year: int) -> float:
    """Calculate realized price for a segment in a given year"""
    seg = self.segments[segment]
    benchmark_price = self.get_benchmark_price(seg.benchmark_type, year)

    # Apply segment premium
    realized_price = benchmark_price * (1 + seg.price_premium_to_benchmark)

    return realized_price
```

---

## Sensitivity Analysis

### Price Elasticity: 5.5x

**Definition:** % change in valuation per 1% change in steel prices.

**Measurement:**
```
Elasticity = (% Δ Valuation) / (% Δ Steel Prices)
           = (+55.6% valuation) / (+10% prices)
           = 5.56x
```

**Interpretation:**
- Steel prices are **5.5x more important** than a typical input
- Small pricing errors have **massive** valuation consequences
- This is the **#1 source of model risk**

### Impact of ±10% Price Change

| Metric | -10% Price | Base (100%) | +10% Price | Swing |
|--------|-----------|-------------|-----------|-------|
| **Avg Revenue** | $12.5B | $13.9B | $15.4B | ±10% |
| **Avg EBITDA** | $1,015M | $1,660M | $2,361M | ±63% ⚠️ |
| **10Y FCF** | $6.7B | $12.7B | $19.8B | ±56% ⚠️ |
| **USS Value** | $26.46 | $50.14 | $78.03 | ±$24/sh |
| **Nippon Value** | $41.96 | $74.87 | $113.59 | ±$32/sh |

**Key Insight:** EBITDA and FCF swing **6x more** than revenue due to operating leverage.

### Why EBITDA Amplifies Price Changes

**Reason 1: Operating Leverage**
- Revenue changes, but fixed costs stay constant
- Example: $100M revenue increase on $80M variable costs = $100M incremental EBITDA

**Reason 2: Margin Sensitivity**
The model adjusts margins based on price level (line 686-695):

```python
def calculate_segment_margin(self, segment: Segment, realized_price: float) -> float:
    seg = self.segments[segment]

    # Margin adjusts with price level
    price_change = realized_price - seg.base_price_2023
    margin_adj = (price_change / 100) * seg.margin_sensitivity_to_price

    margin = seg.ebitda_margin_at_base_price + margin_adj

    return max(0.02, min(0.30, margin))
```

**Example: Flat-Rolled**
- Base margin: 12%
- Margin sensitivity: 4% per $100 price change
- Price increases $100: Margin increases to 16%
- Price decreases $100: Margin decreases to 8%

**This creates a double effect:**
1. Revenue increases from higher prices
2. Margin % increases from pricing power

Combined impact: **EBITDA is highly sensitive** to steel prices.

### Extreme Scenario Analysis

#### Recession Case (70% Benchmarks)

**Pricing:**
- HRC: $476/ton (-30%)
- Flat-Rolled realized: $722/ton (from $1,030)

**Results:**
- Avg EBITDA Margin: 6.6% (vs. 15.5% base)
- 10Y FCF: $125M (vs. $12.7B base)
- USS Value: **-$0.29/share** (worthless)
- Nippon Value: $4.17/share (93% decline)

**Interpretation:** At 70% pricing, USS is basically insolvent on a NPV basis.

#### Boom Case (130% Benchmarks)

**Pricing:**
- HRC: $884/ton (+30%)
- Flat-Rolled realized: $1,340/ton (from $1,030)

**Results:**
- Avg EBITDA Margin: 26.8% (vs. 15.5% base)
- 10Y FCF: $36.3B (vs. $12.7B base)
- USS Value: $142.42/share
- Nippon Value: $202.23/share (2.7x the $55 offer!)

**Interpretation:** At 130% pricing, the $55 offer looks absurdly cheap.

### Valuation Range Summary

**USS Standalone:**
```
Low (70%):     -$0.29/share
Base (100%):   $50.14/share
High (130%):  $142.42/share
Total Range:  $142.71/share (infinite multiple)
```

**Value to Nippon:**
```
Low (70%):     $4.17/share
Base (100%):  $74.87/share
High (130%): $202.23/share
Total Range: $198.06/share (48.5x)
```

**Key Insight:** The entire valuation question comes down to your view on steel prices.

---

## Why Steel Prices Dominate Valuation

### 1. Revenue is Directly Tied to Price

```
Revenue = Volume × Price
```

In the Price × Volume model, steel prices are **50% of the revenue equation** (the other 50% being volume).

Unlike a DCF with fixed revenue assumptions, this model **explicitly models the price dependency**.

### 2. Operating Leverage Amplifies Price Changes

**Steel industry characteristics:**
- High fixed costs (depreciation, overhead, labor)
- Low variable costs (raw materials, energy) relative to price
- Small price changes create large margin swings

**Example:**
```
Scenario A (Low Price):
Revenue:        $1,000/ton
Variable cost:    $750/ton
Fixed cost:       $150/ton (doesn't change)
EBITDA:           $100/ton (10% margin)

Scenario B (High Price, +20%):
Revenue:        $1,200/ton
Variable cost:    $750/ton (same)
Fixed cost:       $150/ton (same)
EBITDA:           $300/ton (25% margin)
```

**Result:** 20% price increase → **200% EBITDA increase**

### 3. Margin Sensitivity Compounds the Effect

The model includes **price-dependent margins** (line 686-695), meaning:
- Higher prices → Better margins (pricing power, premium realization)
- Lower prices → Compressed margins (cost pressure, commoditization)

This creates a **double leverage effect:**
1. Direct: Revenue increases from higher prices
2. Indirect: Margin % increases from pricing dynamics

### 4. Terminal Value is Driven by Final Year Cash Flows

**Gordon Growth formula:**
```
Terminal Value = FCF_2033 × (1 + g) / (WACC - g)
```

Since FCF_2033 is heavily driven by 2033 steel prices, and terminal value is typically **60-70% of total EV**, steel prices have an **outsized impact** on the final valuation.

### 5. Steel is Cyclical - Price Variance is High

**Historical HRC volatility:**
- 2000-2003: $200-300/ton
- 2008 peak: $1,000+/ton
- 2009 trough: $400/ton
- 2021 peak: $1,900/ton
- 2023: $680/ton
- 2024: ~$600/ton

**Coefficient of variation:** ~40-50%

Contrast with:
- GDP growth: 5-10% CV
- WACC: 10-15% CV
- Volume: 15-20% CV

**Steel prices are 3-4x more volatile** than other inputs, and also 3-4x more impactful on valuation.

### Comparison to Other Drivers

| Input Variable | Elasticity | Typical Range | Valuation Impact |
|----------------|-----------|---------------|------------------|
| **Steel Prices** | **5.5x** | **±20%** | **$80-100/share** |
| WACC | 3.5x | ±2% | $30-40/share |
| Volume | 2.5x | ±10% | $15-20/share |
| Terminal Growth | 1.8x | ±1% | $10-15/share |
| CapEx Efficiency | 1.5x | ±10% | $8-12/share |

**Steel prices dominate** because they have both:
1. Highest sensitivity (5.5x elasticity)
2. Highest variance (±20-30% realistic range)

---

## Scenario Comparison

### Steel Price Assumptions by Scenario

| Scenario | HRC Factor | Implied 2024 HRC | Realized Flat-Rolled | Philosophy |
|----------|------------|------------------|----------------------|------------|
| **Conservative** | 0.85 | $578 | $876/ton | Recession pricing |
| **Wall Street** | 0.92 | $625 | $947/ton | Analyst consensus |
| **Base Case** | 0.95 | $646 | $979/ton | Mid-cycle normalization |
| **Management** | 0.92 | $625 | $947/ton | Dec 2023 guidance ($700-750) |
| **Nippon** | 0.95 | $646 | $979/ton | Stable with capacity discipline |

### Resulting Valuations

| Scenario | USS Value | Nippon Value | 10Y FCF | Notes |
|----------|-----------|--------------|---------|-------|
| **Conservative** | $26 | $42 | $6.7B | Prices 15% below 2023 |
| **Wall Street** | $34 | $56 | $8.9B | Matches fairness opinion range |
| **Base Case** | $50 | $75 | $12.7B | 5% below 2023 pricing |
| **Management** | $38 | $61 | $9.5B | Flat pricing post-2024 |
| **Nippon** | $69 | $105 | $14.1B | Same prices but $14B CapEx |

### Key Observations

1. **Wall Street vs. Base Case:** Similar price assumptions but different volume/CapEx → $16/share gap

2. **Conservative downside:** Even with 15% price decline, Nippon still sees $42/share (below $55 offer)

3. **Base Case justifies deal:** At mid-cycle pricing, Nippon sees $75/share vs. $55 offer = $20/share value creation

4. **Management is between:** More optimistic than Conservative, more realistic than Base Case

5. **Nippon upside:** Full investment program + same pricing = $105/share to Nippon (vs. $55 paid)

---

## Practical Implications

### For Model Users

**1. Steel Price Forecast is Critical**

Your valuation is **only as good as your steel price assumption**. If you believe:
- Mid-cycle HRC is $600/ton → Use 0.88x factor → USS worth $45/share
- Mid-cycle HRC is $700/ton → Use 1.03x factor → USS worth $95/share

**Recommendation:** Run **at least 3 scenarios** (bear, base, bull) to understand the range.

**2. 2023 Base May Be Too High**

The model uses 2023 benchmarks ($680 HRC) which were elevated. Consider:
- 10-year average HRC (2014-2023): ~$550-600/ton
- 20-year average HRC (2004-2023): ~$500-550/ton
- Normalized mid-cycle: $600-650/ton

**Implication:** Base Case (0.95x = $646 HRC) might actually be **above** mid-cycle, not below.

**3. Downside Risk is Asymmetric**

- Recession scenario (0.85x): USS worth $26 → **48% downside** vs. Base
- Boom scenario (1.10x): USS worth $78 → **56% upside** vs. Base

But probability-weighted:
- Recession risk: 25% probability
- Boom probability: 15% probability

**Expected Value might be below Base Case** if you weight scenarios.

**4. The $55 Offer Makes Sense**

At Base Case pricing (0.95x), Nippon sees $75/share value:
- But if prices normalize to 0.90x → Value drops to $55-60/share
- $55 offer provides **downside protection** to Nippon
- USS shareholders get **certainty** vs. cyclical risk

**5. Timing Matters**

2023-2024 saw declining steel prices:
- 2023 avg HRC: ~$680/ton
- Late 2024 HRC: ~$600-620/ton
- Early 2025 HRC: ~$580-600/ton

Deal was announced December 2023 at peak prices. By execution, prices have declined **10-15%**, making the $55 offer look **more attractive** in hindsight.

### For Analysts

**1. Stress Test Price Assumptions**

Always show:
- Bear case (0.80-0.85x): Tests downside protection
- Base case (0.90-1.00x): Most likely outcome
- Bull case (1.10-1.20x): Upside potential

Don't rely on a single point estimate.

**2. Compare to Historical Cycles**

Overlay your price assumptions on historical HRC prices:
- Are you above/below historical mid-cycle?
- Are you within 1-2 standard deviations?
- What's your implied real price growth?

**3. Triangulate with Fundamental Supply/Demand**

Price assumptions should be justified by:
- Global steel capacity utilization (normal: 70-75%)
- US steel import levels (normal: 20-25% of consumption)
- Auto/construction demand outlook
- China export dynamics

**4. Consider Premium Compression Risk**

The model holds premiums constant at +51.5% for Flat-Rolled. In severe downturns:
- Premiums historically compress to +30-40%
- This would reduce realized prices by ~$50-100/ton
- Not currently modeled → **Overstates downside revenues**

**Recommendation:** In Conservative scenario, manually reduce premiums by 5-10 percentage points.

**5. Document Your Price View**

Any valuation output should state:
- HRC price assumption ($/ton)
- Factor used (vs. 2023 base)
- Rationale (historical avg, analyst consensus, fundamental view)
- Range around base case

**Example:**
```
Base Case: $646/ton HRC (0.95x factor)
Rationale: Slight normalization from elevated 2023 levels
Range: $578-748/ton (0.85x-1.10x)
Valuation Range: $26-78/share (USS standalone)
```

### For Management/Stakeholders

**1. Understand the Exposure**

USS is a **leveraged bet on steel prices**:
- 10% price decline → 50% FCF decline
- This is structural, not avoidable

**Implication:** USS standalone is **highly risky** for public shareholders.

**2. The Nippon Deal Reduces Risk**

By selling at $55/share, USS shareholders:
- Lock in value at ~mid-cycle pricing
- Avoid downside risk (which is significant)
- Exchange cyclical exposure for certain cash

**3. Price Cycles are Inevitable**

Historical pattern:
- 3-5 year price cycles
- Peaks last 1-2 years
- Troughs last 2-3 years

**Implication:** Waiting for "better prices" may mean waiting 3-5 years, with risk of deeper trough.

**4. Volume Can't Offset Price Declines**

Some argue "we'll make it up on volume." Math doesn't work:
- 10% volume increase → 10% revenue increase
- 10% price decline → 10% revenue decrease BUT 40-50% EBITDA decrease

**Conclusion:** Price is 4-5x more important than volume for profitability.

---

## Conclusion

### Key Takeaways

1. **Steel prices are the #1 driver** of valuation with 5.5x elasticity

2. **Model uses a three-layer system:**
   - Layer 1: 2023 benchmark prices ($680 HRC base)
   - Layer 2: Price factors (0.85x-1.10x for scenarios)
   - Layer 3: Product mix premiums (+51.5% for Flat-Rolled)

3. **±10% price swing moves valuation by ±50%** ($20-30/share)

4. **Operating leverage amplifies** price changes:
   - 10% revenue change → 30-40% EBITDA change → 50-60% FCF change

5. **Price assumptions drive scenario outcomes:**
   - Conservative (0.85x): $26/share
   - Base (0.95x): $50/share
   - Boom (1.10x): $78/share

6. **The $55 offer makes sense** when considering:
   - Downside risk (prices can fall 20-30%)
   - Cyclical nature of steel
   - Certainty value vs. volatility

7. **Model users must:**
   - Carefully consider price assumptions
   - Run multiple scenarios
   - Understand 2023 base may be elevated
   - Stress test with historical ranges

### Final Thought

The model's high sensitivity to steel prices is not a bug - it's a feature that **accurately reflects the economics of the steel industry**. Steel is a cyclical commodity business where pricing drives profitability.

The model's transparency about this dependency is its strength. Rather than hiding the price sensitivity in a black box, the three-layer system makes it explicit and adjustable.

**The critical question is not "how does the model work?" but rather "what is your view on steel prices?"**

Your answer to that question will determine your valuation.

---

*Last Updated: January 2026*
*Model Version: v14*
*RAMBAS Team Capstone Project*
