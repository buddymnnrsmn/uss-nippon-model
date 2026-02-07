# USS / Nippon Steel DCF Dashboard: User Guide

**Version:** 3.0
**Last Updated:** February 7, 2026
**Purpose:** Interactive tool for analyzing the proposed USS/Nippon Steel merger using scenario analysis, valuation, and stress testing

---

## 1. Getting Started

### Running the Dashboard

#### Option 1: Local Installation
```bash
# Navigate to project directory
cd /path/to/FinancialModel

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run the dashboard
streamlit run interactive_dashboard.py
```

The dashboard will automatically open in your browser at `http://localhost:8501`

#### Option 2: Cloud Deployment
Deploy to Streamlit Community Cloud:
1. Push repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and deploy `interactive_dashboard.py`

### System Requirements

| Requirement | Specification |
|-------------|---------------|
| Python | 3.9+ |
| Main Dependencies | streamlit, pandas, numpy, plotly |
| Optional | Bloomberg terminal access (for advanced data features) |
| Browser | Modern browser (Chrome, Safari, Firefox, Edge) |
| RAM | Minimum 2GB (recommended 4GB for Monte Carlo) |

### First Run Checklist

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] No data import errors appear in console
- [ ] Dashboard loads within 5 seconds
- [ ] Base Case scenario calculates and displays USS/Nippon valuations
- [ ] All chart visualizations render properly

---

## 2. Scenario Selection

The dashboard offers **12 pre-built scenarios** plus a **Custom option** for tailored analysis.

### Core Scenarios (7)

#### Severe Downturn — Historical Crisis
- **Steel Prices:** 0.70x benchmarks with -2% annual decline
- **WACC:** 13.5% (USS)
- **Probability:** 25% (recession frequency)
- **Use Case:** Downside stress test; 2008-2009 GFC comparable

**Key Assumptions:**
- HRC: $516/ton | CRC: $696/ton | Coated: $779/ton
- Utilization 75% | Revenue headwinds | Margin compression
- Expected USS Value: ~$0/share (equity value at floor; debt service stressed)

---

#### Downside — Weak Markets
- **Steel Prices:** 0.85x benchmarks, flat (no growth)
- **WACC:** 12.0%
- **Probability:** 30% (weak cycle frequency)
- **Use Case:** Conservative base for risk analysis

**Key Assumptions:**
- HRC: $627/ton | CRC: $844/ton | Coated: $946/ton
- Utilization 85% | Stable margin | Modest operational challenges
- Expected USS Value: ~$15/share

---

#### Mid-Cycle Base Case
- **Steel Prices:** 0.90x benchmarks with +1% annual growth
- **WACC:** 10.9%
- **Probability:** 30% (most frequent market regime)
- **Use Case:** Central scenario for fair value analysis

**Key Assumptions:**
- HRC: $664/ton | CRC: $895/ton | Coated: $1,001/ton
- Utilization 90% | Moderate margin expansion | Orderly execution
- Expected USS Value: ~$39/share
- **This is the primary valuation reference point**

---

#### Above Average — Strong Cycle
- **Steel Prices:** 0.95x benchmarks with +1.5% annual growth
- **WACC:** 10.9% (same as base case — assumes cyclical strength not permanent)
- **Probability:** 10% (extended strong cycle)
- **Use Case:** Bull case for strong market conditions

**Key Assumptions:**
- HRC: $705/ton | CRC: $950/ton | Coated: $1,057/ton
- Utilization 92% | Margin expansion from volume leverage | Strong capex execution
- Expected USS Value: ~$67/share

---

#### Wall Street — Analyst Views
- **Steel Prices:** 1.02x benchmarks (~$753 HRC), 0% growth
- **WACC:** 12.5% (analyst midpoint; uses scenario WACC, not verified WACC)
- **Terminal Growth:** 0% (no perpetual real price appreciation)
- **Exit Multiple:** 4.75x EBITDA
- **Probability:** Reference only (not included in probability weighting)
- **Use Case:** Reconciliation to DEFM14A fairness opinions

**Key Assumptions:**
- **Calibrated to DEFM14A fairness opinions** (proxy filed March 2024)
  - Barclays: WACC 11.5%–13.5%, perpetuity growth (1.0)%–1.0% → **$39–$50/share**
  - Goldman Sachs: WACC 10.75%–12.5%, exit multiple 3.5x–6.0x → **$38–$52/share**
  - Our midpoint: **$43/share** (within both ranges)
- Banks used management December 2023 projections with HRC **$700/ton** long-term
- Our 1.02x factor (~$753 HRC) approximates blended near-term ($750) / long-term ($700) pricing
- EU HRC factor 0.87x (lower due to carbon tax headwinds noted in management projections)
- **Uses analyst WACC (12.5%), not model's verified WACC (10.7%)** — toggle "Use Verified WACC" to honor scenario
- Flat growth (0%) matches banks' through-cycle normalization assumption
- Expected USS Value: ~$43/share | Nippon: ~$75/share
- **Offer Price ($55/share) was 27% above this fairness opinion midpoint**

---

#### Optimistic — Sustained Growth
- **Steel Prices:** 1.00x benchmarks with +2% annual growth
- **WACC:** 10.9%
- **Probability:** 5% (sustained favorable conditions)
- **Use Case:** Long-term upside from structural improvements

**Key Assumptions:**
- HRC: $738/ton | CRC: $994/ton | Coated: $1,113/ton
- Utilization 95% | Continued margin expansion | Technology synergies realized
- Volume growth from Nippon projects (if selected)
- Expected USS Value: ~$97/share

---

#### Management Dec 2023 Guidance
- **Maps to:** Optimistic scenario (same assumptions)
- **Steel Prices:** 1.00x benchmarks
- **WACC:** 10.9%
- **Purpose:** Transparency to management internal projections
- **Note:** Uses same parameters as Optimistic; this naming clarifies the source

---

### Merger-Specific Scenarios (2)

#### Nippon Investment Case — $14B Capital Program
- **Trigger:** Check "Include Nippon Projects" on sidebar
- **Project Portfolio:**
  - BR2 Mini Mill (3,000 kt, $459M EBITDA) — committed
  - Gary Works BF Reline (2,500 kt, $285M EBITDA) — conditional
  - Mon Valley HSM (1,800 kt, $205M EBITDA) — conditional
  - Greenfield Mini Mill (500 kt, $77M EBITDA) — optional
  - Mining Investment (6,000 kt, $108M EBITDA) — optional
  - Fairfield Works (1,200 kt, $130M EBITDA) — optional
- **Total Capacity:** ~15,000 kt/year incremental
- **Total EBITDA at full run-rate:** $1,264M annually (by 2033)
- **Construction Timeline:** 2025–2031 (phased)
- **Valuation Impact:** +$15–25/share depending on execution

**How to Use:**
1. Select any core scenario (Base Case recommended)
2. Check "Include Nippon Projects" on sidebar
3. Adjust **Execution Factor** (50%–100%) to model downside scenarios
4. Result shows full potential merger value with capex investment

---

### Stress Tests (3)

These test model robustness and extreme outcomes:

#### Extreme Downside (2008-Style Crisis)
- **Steel Prices:** 0.60x benchmarks (–40% impact)
- **Volume Impact:** –20% utilization reduction
- **WACC:** 13.9% (credit stress assumptions)
- **Expected USS Value:** Near zero (equity wiped out)
- **Purpose:** Tail risk assessment; regulatory stress testing

---

#### Extreme Upside (Boom Scenario)
- **Steel Prices:** 1.30x benchmarks (+30% impact)
- **Volume Impact:** 95% utilization sustainably maintained
- **WACC:** 10.9% (no credit benefit from upside)
- **Expected USS Value:** ~$150/share
- **Purpose:** Upside scenario for equity holder optionality; check value creation limits

---

#### Project Execution Failure
- **Nippon Projects:** 50% EBITDA delivery vs. plan
- **Core Scenario:** Mid-Cycle Base Case
- **Execution Factor:** Fixed at 50%
- **Expected USS Value:** ~$29/share (vs. $47 with full execution)
- **Purpose:** Assess downside if capital projects underdeliver on EBITDA targets

---

### Custom Scenario

Select "Custom" to manually adjust **all parameters:**
- Price factors (HRC, CRC, Coated, OCTG, EU HRC, Billet)
- Annual growth rate (–2% to +5%)
- WACC (5% to 15%)
- Terminal growth rate (1% to 3%)
- Exit multiple (3x to 9x EBITDA)
- Execution factor for projects (0% to 100%)
- Capital project selection

**Use Case:** One-off analysis for board presentations, client requests, or hypothesis testing

---

## 3. Price Controls

Control commodity prices and market assumptions via the **Price Controls** section.

### Benchmark Prices (Through-Cycle Equilibrium)

Reference prices are rebased to long-term equilibrium, not 2023 spot levels:

| Commodity | Equilibrium Price | Range | Updated |
|-----------|------------------|-------|---------|
| **HRC (Flat-Rolled)** | $738/ton | $516–$900 | Q4 2023 |
| **CRC (Cold-Rolled)** | $994/ton | $696–$1,293 | Q4 2023 |
| **Coated** | $1,113/ton | $779–$1,447 | Q4 2023 |
| **OCTG (Oil & Gas)** | $2,388/ton | $1,871–$3,105 | Q4 2023 |
| **EU HRC** | $611/ton | $427–$793 | Q4 2023 |
| **Billet (Mini Mill)** | $450/ton | $315–$585 | Q4 2023 |

**Sources:** Platts, S&P Global, archival steel price databases (2019–2023 normalized)

### Price Factors

Adjust prices as percentage of benchmark:

| Factor | Range | Effect |
|--------|-------|--------|
| **Price Factor** | 60%–130% | Multiplies all benchmarks uniformly |
| **Annual Growth** | –2% to +5% | Adds year-over-year price escalation (compounding) |

**Example:**
- Base Case: 0.90x factor, +1% growth
- Year 1: HRC = $738 × 0.90 × 1.00 = $664/ton
- Year 2: HRC = $738 × 0.90 × 1.01 = $671/ton
- Year 10: HRC = $738 × 0.90 × 1.01^9 = $728/ton

### Tariff Rate (Section 232 Steel Tariffs)

**Model Feature:** Explicit tariff adjustment system for U.S. trade policy scenarios

| Control | Options | Effect |
|---------|---------|--------|
| **Tariff Policy** | 0%, 25%, 50% | Applied to HRC US, CRC US, Coated US prices only |

**Discrete Tariff Scenarios:**

The dashboard offers three Section 232 policy scenarios:

- **0% — Tariff Removal:** HRC US = $738 × 0.85 = **$627/ton** (free trade baseline)
- **25% — Current Policy:** HRC US = $738 × 1.00 = **$738/ton** (no adjustment, through-cycle already embeds 25%)
- **50% — Tariff Escalation:** HRC US = $738 × 1.15 = **$848/ton** (maximum 15% uplift from current)

**Key Insights:**
- Tariffs create **pricing power** for domestic mills (USS, Nippon) if competitors import
- Tariffs also increase **input costs** for USS customers (auto OEMs, appliance makers)
- Net effect on USS EBITDA is **positive ~$30–80M** at 25% tariffs
- EU HRC and OCTG are **unaffected** (not subject to 232 tariffs)

**Use Case:** Policy scenario analysis for investor presentations

---

### Foreign Exchange: EUR/USD Rate (New)

**Model Feature:** Exchange rate adjustment for USSE (Europe) segment profitability

| Control | Range | Default |
|---------|-------|---------|
| **EUR/USD Rate** | 0.80–1.30 | 1.10 |

**How FX Affects USSE Segment:**

USSE generates revenue in EUR but USS consolidates results in USD.

- **Higher EUR/USD (e.g., 1.20):** USSE revenue worth more in USD → ↑ consolidated revenue
- **Lower EUR/USD (e.g., 0.95):** USSE revenue worth less in USD → ↓ consolidated revenue

**Example:**
- USSE EBITDA: €200M per year
- EUR/USD = 1.10: Consolidated = $220M
- EUR/USD = 1.20: Consolidated = $240M (+9%)

**Historical Range:** 0.98–1.17 (2019–2024)
**IMM Forecast (Q1 2026):** 1.08–1.12

---

## 4. WACC Parameters

Discount rates for present value calculations. The dashboard integrates verified WACC calculations from the `wacc-calculations` module.

### USS WACC (United States Steel)

| Parameter | Base Case | Range | Notes |
|-----------|-----------|-------|-------|
| **WACC** | 10.70% | 5%–15% | Verified from Federal Reserve data, Bloomberg |
| **Terminal Growth Rate** | 2.0% | 1%–3% | Long-term nominal GDP growth |
| **Exit Multiple** | 5.0x | 3.0x–9.0x | Terminal value calculation method |

**WACC Breakdown (for reference):**
- Cost of Equity: ~12.0% (USS equity beta 1.4x)
- Cost of Debt: ~4.5% (A-rated credit spreads)
- Tax Rate: 21%
- Debt/Total Capital: ~30%

**Use Verified WACC Toggle:**

By default, the dashboard loads the verified USS WACC (10.7%) from the `wacc-calculations` module. This override can be disabled to honor the scenario's WACC setting.

- **Most scenarios:** Keep "Use Verified WACC" checked (default) for consistency
- **Wall Street scenario:** Automatically unchecks "Use Verified WACC" to use analyst WACC (12.5%) from fairness opinions
- **Custom scenario:** User choice — check for model consistency, uncheck to test sensitivity

**Interpretation:**
- **Lower WACC (8%)** → Higher valuation (more optimistic on USS creditworthiness)
- **Higher WACC (13%)** → Lower valuation (distress/bankruptcy scenarios)
- **Wall Street (12.5%)** → Matches Barclays/Goldman fairness opinion midpoint

### Nippon WACC — Interest Rate Parity Adjustment

**Model Feature:** Converts Nippon's yen WACC to USD for cross-border comparison

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Nippon JPY WACC** | 5.80% | Verified from Bank of Japan data |
| **Nippon USD WACC (IRP-adjusted)** | 7.95% | Accounts for currency risk premium |
| **IRP Adjustment** | +2.15% | USD risk premium over JPY |

**Why This Matters:**
- Nippon borrows cheaply in JPY (lower rates)
- When funding US assets, adds currency risk premium
- 7.95% reflects Nippon's true cost of capital for USS acquisition
- Lower than USS WACC reflects: (a) Nippon's better credit ratings, (b) scale advantages

**How to Use:**
- USS perspective uses 10.70% WACC
- Nippon perspective uses 7.95% WACC
- Difference creates ~$8–15/share valuation delta

---

## 5. Capital Projects

The **Nippon Investment Case** includes six major capital projects totaling $11.4B in construction capex (2025–2031).

### Project Controls

| Control | Type | Default | Effect |
|---------|------|---------|--------|
| **Include Nippon Projects** | Checkbox | OFF | Enables all selected projects |
| **Execution Factor** | Slider | 100% | % of project EBITDA actually delivered |

**How Execution Factor Works:**

Execution risk on large capital projects: "What if projects underdeliver by 20% due to construction delays, cost overruns, or market headwinds?"

- **100% execution:** Projects deliver promised EBITDA
- **80% execution:** Projects deliver 80% of EBITDA; 20% lost to risk
- **50% execution:** High-risk scenario; projects deliver half expected value

**Example (BR2 Mini Mill):**
- Planned EBITDA: $459M/year (at full capacity)
- At 80% execution: $367M/year (–$92M risk buffer)
- At 50% execution: $230M/year (stress test)

### Project Portfolio Details

#### 1. BR2 Mini Mill (Big River Steel Phase 2)
| Metric | Value |
|--------|-------|
| Segment | Mini Mill (EAF) |
| Capacity | 3,000 kt/year (new) |
| Technology | Electric Arc Furnace (competitive cost) |
| Margin | 17% (EAF advantage) |
| Price Basis | $900/ton |
| Annual EBITDA | $459M (at 100% utilization) |
| Construction Timeline | 2025–2028 |
| Capex | $3,200M |
| Terminal Multiple | 7.0x |
| Status | **COMMITTED** (moves forward regardless) |
| Maintenance CapEx | $20/ton ($60M/year at full run-rate) |

---

#### 2. Gary Works Blast Furnace Reline
| Metric | Value |
|--------|-------|
| Segment | Flat-Rolled (BF integrated) |
| Capacity | 2,500 kt/year (asset preservation + efficiency) |
| Technology | Blast Furnace relined + caster upgrades |
| Margin | 12% (post-upgrade efficiency) |
| Price Basis | $950/ton (flat-rolled premium) |
| Annual EBITDA | $285M |
| Construction Timeline | 2025–2028 |
| Capex | $3,200M |
| Terminal Multiple | 5.0x |
| Status | **CONDITIONAL** (tied to Nippon acquisition) |
| Maintenance CapEx | $40/ton ($100M/year) |

**Why Conditional?** Without Nippon's balance sheet, USS cannot justify a multi-year BF reline (massive capex, execution risk).

---

#### 3. Mon Valley Hot Strip Mill Modernization
| Metric | Value |
|--------|-------|
| Segment | Flat-Rolled (downstream HSM) |
| Capacity | 1,800 kt/year (efficiency gain + premium product) |
| Technology | Hot Strip Mill upgrades for AHSS (auto steel) |
| Margin | 12% (integrated margin) |
| Price Basis | $950/ton |
| Annual EBITDA | $205M |
| Construction Timeline | 2025–2028 |
| Capex | $2,400M |
| Terminal Multiple | 5.0x |
| Status | **CONDITIONAL** |
| Maintenance CapEx | $35/ton ($63M/year) |

---

#### 4. Greenfield Mini Mill
| Metric | Value |
|--------|-------|
| Segment | Mini Mill (EAF new facility) |
| Capacity | 500 kt/year (pure new capacity) |
| Technology | EAF greenfield |
| Margin | 17% (EAF margin) |
| Price Basis | $900/ton |
| Annual EBITDA | $77M |
| Construction Timeline | 2028 (post-BR2 completion) |
| Capex | $1,000M |
| Terminal Multiple | 7.0x |
| Status | **OPTIONAL** |
| Maintenance CapEx | $20/ton ($10M/year) |

---

#### 5. Mining Investment (Keetac & Minntac Iron Ore Mines)
| Metric | Value |
|--------|-------|
| Segment | Mining (iron ore supply) |
| Capacity | 6,000 kt/year |
| Product | Iron ore pellets (feed for BF) |
| Margin | 12% |
| Price Basis | $150/ton (ore price) |
| Annual EBITDA | $108M |
| Capex | $1,000M |
| Terminal Multiple | 5.0x |
| Status | **OPTIONAL** |
| Maintenance CapEx | $8/ton ($48M/year) |

---

#### 6. Fairfield Works Modernization
| Metric | Value |
|--------|-------|
| Segment | Tubular (oil & gas pipes) |
| Capacity | 1,200 kt/year (efficiency upgrades) |
| Technology | Finishing line upgrades for premium OCTG |
| Margin | 12% |
| Price Basis | $900/ton (tubular average) |
| Annual EBITDA | $130M |
| Capex | $600M |
| Terminal Multiple | 6.0x |
| Status | **OPTIONAL** |
| Maintenance CapEx | $25/ton ($30M/year) |

---

### How Projects Are Modeled

**Capex Schedule:**
- 2025–2028: Ramp up construction capex (phased)
- 2028 onwards: Shift to maintenance capex (sustaining investment)

**Revenue & EBITDA Ramp:**
- Projects ramp gradually as commissioning completes
- BR2: 20% (Y1) → 60% (Y2) → 90% (Y3) → 100% (Y4+)
- Gary Works & Mon Valley: 50% (Y4) → 90% (Y5) → 100% (Y6+) [relines require shutdown]

**FCF Calculation:**
```
FCF = (Base EBITDA + Project EBITDA) × Tax Rate - Capex
```

---

## 6. Reading Results

### Executive Summary Card

Top of dashboard shows key metrics at a glance:

| Card | Meaning | How to Use |
|------|---------|-----------|
| **USS Per Share** | Fair value from USS shareholder perspective | Compare to Nippon Offer ($55) and pre-deal price ($39) |
| **Nippon Per Share** | Fair value from Nippon buyer perspective | Shows deal NPV from buyer viewpoint |
| **Nippon Offer Price** | Acquisition price ($55/share) | Reference line; if USS Fair Value > $55, deal attractive to sellers |
| **Probability Weighted** | Expected value across all scenarios | Central estimate for fair value; most useful for board consensus |

---

### Valuation Details Tab

Shows full DCF output:

| Section | What It Shows | Interpretation |
|---------|--------------|-----------------|
| **Scenario Details** | Selected price, WACC, volume assumptions | Confirms you're modeling the right case |
| **Base Year Financials** | 2024 revenue, EBITDA, FCF by segment | Sanity check on current profitability |
| **10-Year Projection** | Year-by-year revenue, EBITDA, FCF (2024–2033) | Trend analysis; spot check major jumps |
| **Terminal Value** | 2033 EBITDA × exit multiple | Typically 60–80% of total value |
| **Enterprise Value** | Sum of PV(FCF) + PV(Terminal Value) | What the business is worth today |
| **Share Price** | EV ÷ Shares Outstanding | Per-share fair value |

**Red Flags:**
- Negative FCF in early years → execution risk
- Steeply declining terminal EBITDA → business model questioned
- Enterprise Value < 0 → bankruptcy scenario
- Share price < $0 → shows floor of $0 (equity is junior claim)

---

### Covenant Analysis (New)

Credit metrics for lenders and debt holders:

| Metric | Target | Typical Covenant |
|--------|--------|------------------|
| **Debt / EBITDA** | < 4.0x | Leverage ratio; red cells indicate breach |
| **Interest Coverage** | > 2.5x | EBITDA ÷ Interest Expense; measures debt service capacity |
| **Net Debt / EBITDA** | < 3.5x | Adjusts debt for cash on hand |

**How to Read:**
- **Green:** Healthy covenant headroom
- **Yellow:** Approaching threshold (100–110% of limit)
- **Red:** Covenant breach (>110% of limit); refinancing risk

**Example:**
- Year 3 Debt/EBITDA: 3.8x → **Green** (under 4.0x limit)
- Year 5 Debt/EBITDA: 4.2x → **Red** (over 4.0x; breach)

**Why This Matters:**
- Breaches trigger accelerated repayment clauses
- Refinancing costs rise (higher interest rate)
- Limits ability to pay dividends

**For Merger Analysis:**
- Nippon perspective: Better leverage ratios (post-acquisition)
- USS standalone with capex: Worse ratios (financing gap)

---

### Scenario Comparison Tab

Side-by-side table of all scenarios:

| Column | What It Shows | Use |
|--------|---------------|-----|
| **Scenario Name** | Which case | Identify the row |
| **Price Factor** | 0.60x–1.30x | Commodity assumption |
| **WACC** | 5%–15% | Discount rate used |
| **USS $/share** | Valuation per scenario | Compare across cases |
| **Nippon $/share** | Buyer perspective per scenario | Deal value creation |
| **Probability** | % weight in blended average | Central scenario gets 30%, stress tests lower |

**How to Use:**
1. Look for which scenarios drive the most value
2. Identify where USS vs. Nippon valuations diverge
3. Weight by probability column to get expected value

---

## 7. Monte Carlo Simulation

Probabilistic valuation using **26 correlated variables** and 1,000+ simulations.

### In-Dashboard Monte Carlo Results

The dashboard includes a **Monte Carlo Simulation Results** section (below the Steel Price Sensitivity charts) that displays pre-computed results from the most recent simulation run:

- **Summary Statistics**: USS and Nippon mean/median/P5-P95, synergy premium
- **Share Price Distribution**: Overlaid histograms with $55 offer line and median markers
- **Key Value Drivers (Tornado)**: Top 10 inputs by correlation with Nippon share price
- **CDF Comparison**: Cumulative probability curves with $55 annotation

This section loads data from `data/monte_carlo_results.csv` and `data/monte_carlo_inputs.csv`. To regenerate:
```bash
python scripts/run_monte_carlo_analysis.py
```

### What Is Monte Carlo?

Instead of one "base case" valuation, Monte Carlo generates a **distribution** of outcomes:
- Each variable (price, margin, WACC, etc.) varies within realistic ranges
- 5,000 simulations = 5,000 possible futures
- Results show: median, percentiles (P10, P50, P90), standard deviation, tail risk

### The 25 Variables

Monte Carlo inputs fall into five categories:

#### Prices (6 variables)
| Variable | Range | Distribution | Notes |
|----------|-------|--------------|-------|
| HRC US | μ=–0.5%, σ=18% | Lognormal | Flat-rolled index |
| CRC US | μ=–0.5%, σ=16% | Lognormal | Cold-rolled index |
| Coated US | μ=–0.5%, σ=15% | Lognormal | Galvanized/painted |
| OCTG | μ=–0.5%, σ=22% | Lognormal | Oil & gas pipes (most volatile) |
| EU HRC | μ=–0.5%, σ=15% | Lognormal | USSE segment price |
| Billet | μ=–0.5%, σ=18% | Lognormal | Mini mill feedstock |

**Correlations:**
- HRC ↔ CRC: **0.88** (strong; same product family)
- HRC ↔ OCTG: **0.20** (weak; different demand drivers)
- HRC ↔ EU HRC: **0.60** (moderate; regional variation)
- Other pairs: 0.10–0.50 (calibrated to historical returns)

#### Margins (4 variables)
| Variable | Range | Notes |
|----------|-------|-------|
| Flat-Rolled Margin | 10%–15% | Integrated mill economics |
| Mini Mill Margin | 14%–20% | EAF cost advantage |
| USSE Margin | 8%–14% | European integrated operations |
| Tubular Margin | 10%–16% | Oil & gas cycle sensitivity |

**Margin Cap:** 22% (prevents unrealistic high-margin outcomes)

#### Volumes (4 variables)
| Variable | Range | Notes |
|----------|-------|-------|
| Flat-Rolled Utilization | 75%–95% | Capacity utilization rate |
| Mini Mill Utilization | 80%–97% | EAF capacity utilization |
| USSE Utilization | 70%–92% | European demand cycles |
| Tubular Utilization | 65%–90% | Oil & gas CapEx correlation |

#### Operational (7 variables)
| Variable | Range | Notes |
|----------|-------|-------|
| Annual Price Growth | –2% to +3% | Year-over-year escalation |
| SG&A as % Revenue | 5%–7% | Overhead burden |
| Tax Rate | 18%–24% | Federal + state taxes |
| Capex / Depreciation | 1.0x–1.5x | Investment intensity |
| Execution Factor | 50%–100% | Project delivery (if enabled) |
| Tariff Probability | 0%–100% | Beta(8,2) distribution ≈ 80% mean |
| Tariff Rate if Applied | 0%–25% | Triangular(0, 10%, 25%) |

#### Financial (4 variables)
| Variable | Range | Notes |
|----------|-------|-------|
| WACC | ±2% around base | Discount rate variability |
| Terminal Growth | 1%–3% | Long-term nominal growth |
| Exit Multiple | 4.0x–6.0x | Terminal value method |
| Net Debt | ±$200M | Financing assumptions |

### How to Interpret Results

#### Distribution Chart
Shows histogram of 5,000 simulated valuations:

| Feature | What It Means |
|---------|---------------|
| **Shape** | Symmetry (normal) vs. skew (tail risk) |
| **Peak** | Most probable valuation (mode) |
| **Width** | Range of outcomes (volatility) |
| **Left Tail** | Downside risk (10% worst outcomes) |
| **Right Tail** | Upside potential (10% best outcomes) |

#### Key Statistics
| Statistic | Formula | Use |
|-----------|---------|-----|
| **Mean** | Sum of all outcomes ÷ 5,000 | Average expected value |
| **Median** | 50th percentile | Middle outcome (less affected by outliers) |
| **P10 / P90** | 10th & 90th percentiles | Plausible range (80% confidence) |
| **Standard Deviation** | Volatility around mean | Model uncertainty quantification |
| **VaR (Value at Risk)** | Maximum loss at P5 | Downside tail risk |
| **CVaR (Conditional VaR)** | Average loss below P5 | Worst-case scenario magnitude |

#### Example Interpretation
```
Monte Carlo Results (5,000 simulations):

Mean:        $62.50/share
Median:      $59.75/share
P10:         $28.00/share  ← 10% of outcomes are worse
P90:         $118.50/share ← 90% of outcomes are better
Std Dev:     $28.50/share  ← ±45% volatility

"There is a 50% chance USS is worth more than $59.75.
There is a 10% chance it's worth less than $28 (bankruptcy).
There is a 10% chance it's worth more than $118 (bull case)."
```

### How Correlations Work

Example: HRC and CRC correlation = 0.88

- **High positive correlation (0.88):** When HRC prices spike, CRC typically spikes too
  - Result: Concentrated price upside risk (broad steel bull market)
  - Risk concentration: Wide distribution tails

- **Low correlation (0.20):** HRC and OCTG prices move independently
  - Result: Diversification; some simulations have HRC strength offsetting OCTG weakness
  - Risk mitigation: Narrower distribution

**Practical Implication:** Strong steel market uplifts both flat-rolled AND tubular. Weak market hits all segments together. This is why P10 outcomes are so bad (all prices down simultaneously).

### Configuring Monte Carlo

| Control | Options | Effect |
|---------|---------|--------|
| **Number of Simulations** | 1,000–10,000 | Higher = more precision, slower runtime |
| **Correlation Mode** | Cholesky decomposition | Returns-based (not level-based) |
| **Distribution** | Lognormal | Prevents negative prices |
| **Random Seed** | Default or custom | For reproducibility |

---

## 8. Tariff Model (Section 232 Steel Tariffs)

**Background:** Section 232 of the Trade Expansion Act allows the President to impose steel tariffs for "national security." USS tariff impact modeling is critical for fair value.

### How the Tariff Model Works

#### Tariff Rate Variable (0–50%)

This is the key control. Effects:

**At 0% tariff (Free Trade):**
```
HRC US = $738 (baseline)
CRC US = $994 (baseline)
Coated US = $1,113 (baseline)
```

**At 25% tariff (Middle scenario):**
```
HRC US = $738 × 1.15 = $848/ton (+$110)
CRC US = $994 × 1.15 = $1,143/ton (+$149)
Coated US = $1,113 × 1.15 = $1,279/ton (+$166)
```

**At 50% tariff (Maximum, illustrative):**
```
HRC US = $738 × 1.15 = $848/ton (capped)
(15% is maximum historical tariff uplift)
```

#### Pricing Logic

Tariffs create a **wedge** between domestic and import prices:
- Imported steel must pay tariff → more expensive to ship to US
- Domestic mills (USS) can raise prices (less competition from imports)
- Linear scaling: Tariff rate × maximum uplift factor

**Formula:**
```
Domestic_Price_w_Tariff = Base_Price × (1 + Tariff_Rate × 0.15 / 0.25)
```
- 0.15 = maximum uplift (15% higher at 25% tariff)
- 0.25 = reference tariff rate (25%)

#### Which Prices Are Affected?

| Commodity | Tariff Applied? | Notes |
|-----------|-----------------|-------|
| HRC US | ✓ YES | Flat-rolled domestic |
| CRC US | ✓ YES | Cold-rolled domestic |
| Coated US | ✓ YES | Galvanized/painted domestic |
| OCTG | ✗ NO | Exempt from 232 (oil & gas national security exception) |
| EU HRC | ✗ NO | European prices unaffected |
| Billet | ✗ NO | Mini mill raw material (assumption: not tariffed) |

**Rationale:** OCTG is exempt because oil drilling is critical infrastructure. EU prices are set in EUR and not subject to US tariffs (trade agreement presumed).

#### Nippon Impact

If tariff is enacted, Nippon ownership of USS becomes **more valuable:**
- Nippon can supply flat-rolled and coated from Japan at premium prices
- Tariff creates $50–100M EBITDA uplift annually
- This supports valuations at tariff scenarios

### Monte Carlo Tariff Variables (2 new variables)

Monte Carlo adds uncertainty to tariff assumptions using **discrete sampling**:

| Variable | Distribution | Mean | Range | Notes |
|----------|--------------|------|-------|-------|
| **tariff_probability** | Beta(8, 2) | ~80% | 0%–100% | Probability 25% tariff maintained |
| **tariff_rate_if_changed** | Triangular(0%, 10%, 50%) | ~20% | 0%–50% | Alternative rate if policy changes |

**Effect:** Each MC iteration discretely either keeps the 25% tariff (~80% of iterations) or switches to an alternative rate drawn from Tri(0%, 10%, 50%). This produces realistic tail outcomes — some iterations see full tariff removal (0%), others see escalation (up to 50%), consistent with the dashboard's three policy scenarios. Expected effective rate: ~24%.

---

## 9. Covenant Analysis (New Feature)

**Purpose:** Assess whether USS (post-acquisition) can meet debt covenants and maintain financial flexibility.

### Key Covenant Metrics

#### Debt / EBITDA Ratio

**Formula:** Total Debt ÷ EBITDA

| Threshold | Implication |
|-----------|-------------|
| < 3.0x | Strong (investment grade) |
| 3.0x–4.0x | Acceptable (BBB-range) |
| 4.0x–5.0x | Weakened (BB+ range) |
| > 5.0x | Distressed (BB or lower) |

**Typical Covenant Limit:** 4.0x

**Example:**
- 2024 Debt: $3,913M
- 2024 EBITDA: $1,919M
- Debt/EBITDA: 2.04x ✓ Green (healthy)

---

#### Interest Coverage Ratio

**Formula:** EBITDA ÷ Interest Expense

| Threshold | Implication |
|-----------|-------------|
| > 4.0x | Very strong (can service debt easily) |
| 2.5x–4.0x | Acceptable (debt service comfortable) |
| 1.5x–2.5x | Weakened (covenant pressure) |
| < 1.5x | Distressed (coverage at risk) |

**Typical Covenant Limit:** 2.5x minimum

**Example:**
- 2024 EBITDA: $1,919M
- 2024 Interest: $240M (est.)
- Coverage: 8.0x ✓ Green (very comfortable)

---

#### Net Debt / EBITDA

**Formula:** (Total Debt – Cash) ÷ EBITDA

**Definition:** Adjusts for excess cash that can pay down debt.

**Example:**
- Gross Debt: $3,913M
- Cash: $2,547M
- Net Debt: $1,366M
- 2024 EBITDA: $1,919M
- Net Debt/EBITDA: 0.71x (very healthy)

---

### Reading the Covenant Table

**Dashboard displays year-by-year (2024–2033):**

| Year | EBITDA | Debt | Leverage | Interest | Coverage | Breach? |
|------|--------|------|----------|----------|----------|---------|
| 2024 | $1,919 | $3,913 | 2.04x | $240 | 8.0x | — |
| 2025 | $2,050 | $4,100 | 2.00x | $250 | 8.2x | — |
| 2026 | $2,200 | $4,300 | 1.95x | $265 | 8.3x | — |
| …    | …      | …    | …       | …        | …        | … |
| 2033 | $3,100 | $4,500 | 1.45x | $280 | 11.1x | — |

**Color Coding:**
- **Green:** Leverage < 4.0x and Coverage > 2.5x
- **Yellow:** Approaching limits (98–100% of threshold)
- **Red:** Breach (>100% of threshold)

---

### Why Covenants Matter

1. **Refinancing Risk:** If you breach, lenders may demand higher interest rates or require asset sales
2. **M&A Restrictions:** Covenants may limit integration capex or acquisitions post-close
3. **Dividend Capacity:** Covenants often prohibit dividends if leverage is above certain levels
4. **Credit Rating:** Multiple covenant breaches can trigger rating downgrade

### Using Covenants in Analysis

**For Deal Approval:**
- Check that leverage stays < 4.0x under base case for 10 years
- Verify interest coverage > 2.5x (minimum debt service capacity)

**For Stress Testing:**
- Run Severe Downturn scenario: Does leverage spike above 5.0x?
- Run Extreme Downside: What's the latest year no breach occurs?

**For Integration Planning:**
- Year 1–3: Available capex headroom (leverage room to 4.0x limit)
- Year 4+: EBITDA recovery drives leverage down → more capex capacity

---

## 10. Advanced Topics

### Understanding Terminal Value

The **terminal value** (year 2033 forward) typically accounts for **60–80%** of total DCF value.

| Method | Formula | When to Use |
|--------|---------|-------------|
| **Gordon Growth** | EBITDA₂₀₃₃ × (1+g) ÷ (WACC–g) | High-confidence margin/volume |
| **Exit Multiple** | EBITDA₂₀₃₃ × Multiple | Market-based assumption |
| **Blended** | 50% each method | Conservative (default) |

**Sensitivity:** A 0.5x change in exit multiple = ±$5/share. Significant impact.

---

### Price vs. Volume Drivers

Revenue comes from **two levers:**

| Lever | Sensitivity | Example |
|-------|-------------|---------|
| **Price** | $100/ton × 1M tons = $100M | If price ↑$50/ton = +$50M revenue |
| **Volume** | 1M tons × $600/ton = $600M | If volume ↑10% (100k tons) = +$60M revenue |

**Model Insight:** The dashboard includes **margin sensitivity analysis** — shows that USS EBITDA margins are more sensitive to price than volume (2–3% EBITDA change per $100/ton price move).

---

### Synergy Analysis

If synergies are modeled (future feature), they typically include:

1. **Procurement** (~$60–100M): Nippon's scale on raw materials
2. **Logistics** (~$30–50M): Consolidated shipping and distribution
3. **Overhead** (~$50–80M): Elimination of duplicate corporate costs
4. **Technology Transfer** (~$40–100M): Nippon's advanced steelmaking (yield, quality)
5. **Revenue Synergies** (~$50–150M): Nippon distribution channels + cross-sell

**Valuation:** Synergies add $10–25/share to deal value (depending on realization assumptions).

---

### Sensitivity Tables

**If included on dashboard**, show how one variable affects valuation:

| HRC Factor | WACC | USS Value |
|------------|------|-----------|
| 0.70x | 10.9% | $12/share |
| 0.80x | 10.9% | $28/share |
| 0.90x | 10.9% | $39/share |
| 1.00x | 10.9% | $58/share |

**Interpretation:** Value is **most sensitive** to price factors. A 10% change in HRC = ±$10/share approximately.

---

## 11. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Dashboard won't load | Dependencies missing | `pip install -r requirements.txt` |
| `ModuleNotFoundError: scripts.price_correlation_analysis` | File not committed to git | Ensure `scripts/price_correlation_analysis.py` is tracked |
| `stock_uss.csv not found` | Market data not in git | Ensure `market-data/exports/processed/` CSVs are tracked (check `.gitignore` exceptions) |
| `ScenarioType has no attribute EXTREME_DOWNSIDE` | Outdated `price_volume_model.py` | Pull latest — stress test enums were added 2026-02-07 |
| Scenario dropdown empty | Data load failure | Check market-data/ directory exists |
| Football Field blank | Not yet generated | Click "Generate Football Field" button (lazy-loaded) |
| Price Sensitivity blank | Not yet generated | Click "Calculate Price Sensitivity" button (lazy-loaded) |
| Calculations take > 10s | Large Monte Carlo size | Reduce simulations or disable MC |
| Share price shows $0 | Severe downside (negative equity) | Check model is flooring at $0; expected in stress tests |
| Covenant table empty | WACC module not available | Optional feature; can calculate manually |
| FX rate doesn't affect USSE | EUR/USD control missing | Ensure interactive_dashboard.py is latest version |

### Dashboard Tab Layout (Phase 3)

The dashboard is organized into **5 tabs** for faster navigation:

| Tab | Contents | Load Time |
|-----|----------|-----------|
| **Executive Decision** | Deal verdict boxes, risk matrix, fiduciary checklist | Instant |
| **Valuation Analysis** | DCF details, scenario comparison, football field, capital projects, synergies, alternative buyers | Instant (football field lazy-loaded) |
| **Risk & Sensitivity** | Sensitivity thresholds, Monte Carlo results, steel price sensitivity, WACC sensitivity, covenant analysis | Instant (price sensitivity lazy-loaded) |
| **Strategic Context** | USS predicament, NSA commitments, peer benchmarking | Instant |
| **Financial Projections** | FCF projection, segment analysis, stock price history, WACC verification, 10-year model | Instant |

**Lazy-Loaded Sections:**
- **Valuation Football Field:** Click "Generate Football Field" to compute (runs 18 DCF models, ~10-15 seconds). Results are cached per scenario.
- **Steel Price Sensitivity:** Click "Calculate Price Sensitivity" to compute (runs 9 DCF models, ~5-10 seconds). Results are cached per scenario.

**Within-Tab Navigation:** The Valuation and Financial Projections tabs include a mini table of contents with clickable anchor links at the top.

### Performance Tips

1. **Tab switching is instant** — expensive computations are lazy-loaded behind buttons
2. **Cached results persist** — switching away from a tab and back preserves computed charts
3. **Scenario changes invalidate caches** — changing sidebar parameters clears cached results
4. **Disable Monte Carlo** if you just need quick scenario analysis
5. **Use fewer simulations** (1,000) for interactive exploration
6. **Close other browser tabs** to free up RAM
7. **Run on laptop/desktop** (Streamlit Cloud is slower for large computations)

---

## 12. Frequently Asked Questions

**Q: Which scenario should I use for the board?**
A: Mid-Cycle Base Case (0.90x, +1% growth, 10.9% WACC) with 30% probability weighting. It represents the most likely market environment. Supplement with Wall Street scenario for credibility.

**Q: How do I model a Nippon deal with capital projects?**
A: Select Base Case → Enable "Include Nippon Projects" → Set Execution Factor (100% = full delivery, 50% = risk case) → Click Calculate.

**Q: What if USS can't execute the projects?**
A: Set Execution Factor to 50% or 75%. Reduces EBITDA per project by that percentage, showing downside scenario.

**Q: How does the tariff assumption affect valuation?**
A: Use Tariff Rate slider (0–50%). At 25% tariff, HRC prices jump from $664 to $764/ton (+$100). This adds ~$50M EBITDA annually, worth ~$3–5/share in NPV.

**Q: Is the Nippon WACC really lower than USS?**
A: Yes. Nippon is A-rated (USS is BBB). In JPY, their cost of capital is ~5.8%. Converting to USD with risk premium gives 7.95% — still <USS's 10.7%. This is why they can pay more for USS.

**Q: Can I export the valuation for a PowerPoint?**
A: Yes. Use Streamlit's built-in download feature (if enabled) or take screenshots. Alternatively, extract numbers from tables for manual insertion.

**Q: What if I disagree with an assumption?**
A: Use the Custom scenario. Override any parameter (price, WACC, margin, capex timing, etc.) and recalculate.

**Q: How should I interpret the Monte Carlo P10/P90 range?**
A: 80% of outcomes fall between P10 and P90. P10 is the 10th worst percentile (reasonable downside). P90 is the upside boundary. If your board scenario is outside this range, it's an outlier.

---

## 13. Quick Reference

### Keyboard Shortcuts

| Action | Method |
|--------|--------|
| Refresh calculations | Click "Calculate" button or change any parameter |
| Clear all inputs | Streamlit sidebar "Clear Cache" |
| View source code | GitHub or local file browser |

### Useful Links

- **SEC EDGAR:** [USS 10-K filings](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302)
- **Platts Steel:** [Price benchmarks](https://www.spglobal.com/platts/)
- **S&P Capital IQ:** Peer data (Bloomberg terminal required)

### Definition Glossary

- **DCF:** Discounted Cash Flow (valuation method)
- **WACC:** Weighted Average Cost of Capital (discount rate)
- **EBITDA:** Earnings Before Interest, Taxes, Depreciation, Amortization
- **FCF:** Free Cash Flow (cash available to debt and equity holders)
- **EV:** Enterprise Value (value of the business to all investors)
- **Capex:** Capital Expenditures (investment in PP&E)
- **Covenant:** Debt restriction (e.g., Debt/EBITDA < 4.0x)
- **IRP:** Interest Rate Parity (currency risk adjustment)
- **EAF:** Electric Arc Furnace (mini mill technology)
- **BF:** Blast Furnace (integrated steelmaking)

---

## 14. Support & Version History

### Current Version

**Dashboard Version:** 3.0 (February 2026)
**Model Version:** 10.3
**Python:** 3.9+
**Last Updated:** 2026-02-07

### Recent Updates

| Date | Change |
|------|--------|
| 2026-02-07 | **Phase 3: Performance & Polish** — 5-tab layout, lazy-loaded Football Field and Price Sensitivity (behind buttons), cached scenario comparison, mini TOC navigation in Valuation/Projections tabs, deduplicated helper functions |
| 2026-02-07 | Tracked market-data files for Streamlit Cloud (stock prices, steel prices, Bloomberg module) |
| 2026-02-07 | Replaced Steel Price Correlation section with Monte Carlo results |
| 2026-02-06 | Added covenant analysis, tariff model, FX controls |
| 2026-02-05 | Scenario calibration modes, probability distributions |
| 2026-02-03 | SCENARIO_RATIONALE documentation, WACC audit trails |
| 2026-02-02 | Nippon buyer capacity analysis, USS historical trends |
| 2026-01-28 | Section 232 tariff modeling, benchmark rebasing |

### Reporting Issues

If you encounter errors or unexpected results:
1. Check console output (Streamlit shows Python errors)
2. Verify input parameters are in expected ranges
3. Review the COMPREHENSIVE_INPUT_AUDIT.md for data quality details
4. Test with Mid-Cycle Base Case (simplest scenario)

---

## 15. Contact & Governance

**Project:** USS / Nippon Steel Merger DCF Analysis
**Owner:** RAMBAS Team
**Status:** Production
**Classification:** Internal Use Only

For questions or feedback, contact the RAMBAS team.

---

**End of User Guide**
