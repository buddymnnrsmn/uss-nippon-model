# USS / Nippon Steel Merger Model: Methodology and Data Sources

## Conceptual Approach

The model uses a **bottom-up Price × Volume methodology** built on three core principles:

### 1. Revenue Construction (The "Building Blocks")
Instead of forecasting total revenue directly, the model builds revenue for each of USS's four business segments by multiplying:
- **Steel shipment volumes** (thousands of tons shipped per year)
- **Realized prices per ton** (what USS actually gets paid)

This approach anchors the model to physical realities (steel production capacity, customer demand) and observable market prices (HRC futures, industry benchmarks), making assumptions more transparent and testable than traditional "revenue growth rate" models.

### 2. Price Sensitivity Architecture
The model recognizes that steel companies don't just passively accept commodity prices—they earn premiums or discounts based on product mix and quality:
- **Flat-Rolled** earns 51% premium over benchmark HRC (because they sell higher-value cold-rolled and coated products, not just hot-rolled)
- **Mini Mill** earns 29% premium (cleaner EAF steel commands a quality premium)
- **USSE** earns 41% premium over EU HRC (European product mix)
- **Tubular** earns 12% premium over OCTG (specialized oil country tubular goods)

These premiums were **calibrated from 2023 actuals**: USS's 10-K disclosed realized prices of $1,030/ton for Flat-Rolled when HRC benchmark was $680/ton, yielding the 51% premium factor.

### 3. Margin Dynamics
EBITDA margins aren't fixed percentages—they flex with steel prices because:
- **Variable costs** (scrap steel, energy, labor) don't move 1:1 with output prices
- When HRC rises $100/ton, Flat-Rolled margin improves ~4 percentage points
- This "operating leverage" drives the wide valuation ranges ($25-110/share)

### 4. Capital Investment Framework
The model explicitly tracks six major capital projects with distinct cash flow profiles:
- **CapEx schedules** (when money goes out: Gary Works = $3.1B over 2024-2027)
- **EBITDA schedules** (when benefits come in: Gary adds $402M/year starting 2027)
- **Volume additions** (new production capacity from BR2 and Greenfield)

This allows scenario analysis: Base Case includes only BR2 (committed), while Nippon Commitments scenario activates all six projects.

### 5. Cross-Border Valuation via Interest Rate Parity (IRP)
The model calculates two separate valuations using different discount rates:

**USS Standalone:** 10.9% WACC (US dollar-denominated cost of capital)

**Nippon's View:** 7.55% WACC calculated as:
```
Nippon JPY WACC = 3.94%
IRP-adjusted USD WACC = (1.0394 × 1.0425) / 1.0075 - 1 = 7.55%
```

This 3.35% WACC advantage adds ~$25/share to Nippon's valuation of the same cash flows—explaining why they can afford to pay $55 when USS standalone value is only $50.

### 6. Financing Reality Check
The model's most sophisticated insight: it calculates what would happen if USS tried to execute the $14B NSA program alone:
- Identifies cumulative negative FCF years → $3.5B financing gap
- Models 50/50 debt/equity issuance → 17.8% dilution + higher WACC
- Applies these penalties to valuation → destroys $20.55/share

This proves the merger creates value specifically through Nippon's balance sheet capacity, not just through operational synergies.

---

## Data Sources and Input Derivation

### Primary Source: USS 2023 10-K (SEC Filing)
**What was extracted:**
- **Segment shipment volumes:** 8,706k tons (Flat-Rolled), 2,424k tons (Mini Mill), 3,899k tons (USSE), 478k tons (Tubular) - from segment disclosures
- **Segment revenues:** Combined with volumes to calculate 2023 realized prices per ton
- **Balance sheet items:** $4.2B debt, $3.0B cash, 225M shares outstanding
- **Tax rates:** 16.9% cash tax rate (actual taxes paid / pre-tax income from cash flow statement)
- **Capacity utilization:** 71.2% (Flat-Rolled), 89.5% (Mini Mill) - from production capacity disclosures

### Secondary Source: USS 2024 Proxy Statement (DEF 14A)
**What was extracted:**
- **Barclays fairness opinion:** WACC range 11.5-13.5%, valuation $39-52/share, exit multiples 3.5-6.0x
- **Goldman Sachs fairness opinion:** Same WACC range, valuation $40-51/share
- **Management projections (Dec 2023):** HRC $750/ton (2024), $700/ton (2025+), EBITDA $2.4-3.1B, FCF $1.6-1.9B annually
- **Capital program details:** Confirmed BR2 Mini Mill commitment

### Steel Price Benchmarks (2023)
**CME HRC Futures + SteelBenchmarker composite:**
- US HRC: $680/ton (2023 average)
- CRC: $850/ton
- Coated: $950/ton
- EU HRC: $620/ton
- OCTG: $2,800/ton

These became the "base prices" that scenario factors are applied to (e.g., Conservative scenario = 85% of base → $578/ton HRC).

### NSA Investment Program Details
**Nippon Steel public announcements (May 2025):**
- Total commitment: $14B over 10 years
- Project breakdown: Gary Works BF ($3.1B), BR2 ($3.0B), Mon Valley HSM ($1.0B), Greenfield Mini Mill ($1.0B), Mining ($0.8B), Fairfield ($0.5B), Basic Labor Agreement ($1.4B)
- Constraints: No plant closures through 2035, 27,000-28,000 jobs guaranteed, US CEO + board majority
- Target: $2.5B incremental EBITDA

### Interest Rate Data
**Federal Reserve / Bank of Japan (current as of model date):**
- US 10-year Treasury: 4.25%
- Japan 10-year JGB: 0.75%
- These drive the IRP conversion formula

### Assumptions Derived from Industry Knowledge
**Not directly from filings:**
- **Working capital cycles:** DSO (days sales outstanding), DIH (days inventory held), DPO (days payables outstanding) - estimated from steel industry norms
- **Depreciation rates:** 4.5-6.0% of revenue by segment (asset-heavy integrated mills depreciate faster)
- **Maintenance CapEx:** 3.4-4.5% of revenue (industry standard for sustaining operations)
- **Financing costs:** 7.5% interest rate on new debt, 10% equity issuance discount, 3% underwriting fees (standard Wall Street terms)

### Calibration Methodology
The model "reverse-engineers" several parameters from 2023 actuals:
1. Set 2023 segment volumes/prices from 10-K
2. Calculate implied EBITDA margins from reported segment EBITDA
3. Test margin sensitivity assumptions until model reproduces 2023 EBITDA
4. Validate that price premiums (51%, 29%, 41%, 12%) correctly derive realized prices from benchmarks

This ensures the model is **anchored to reality in 2023**, then projects forward using scenario-specific growth rates, price assumptions, and capital programs.

---

## Model Flow: From Inputs to Valuation

### Step 1: Revenue Calculation (By Segment, By Year)
```
Volume (000 tons) × Price ($/ton) ÷ 1,000 = Revenue ($M)

Example (Flat-Rolled 2024):
8,532k tons × $980/ton ÷ 1,000 = $8,361M
```

### Step 2: EBITDA Calculation
```
Base EBITDA = Revenue × Base Margin
Margin Adjustment = (Price - Base Price) ÷ 100 × Sensitivity
Adjusted Margin = Base Margin + Margin Adjustment
Project EBITDA = Sum of capital project contributions
Total EBITDA = Base EBITDA + Project EBITDA
```

### Step 3: Free Cash Flow Waterfall
```
EBITDA
- D&A (4.5-6.0% of revenue)
= EBIT
- Cash Taxes (16.9% of EBIT)
= NOPAT
+ D&A (add back)
= Gross Cash Flow
- Maintenance CapEx (3.4-4.5% of revenue)
- Project CapEx (from project schedules)
+/- Change in Net Working Capital
= Free Cash Flow
```

### Step 4: Discounted Cash Flow Valuation
```
PV of FCF = Σ(FCF_t ÷ (1 + WACC)^t) for t=1 to 10

Terminal Value (Gordon Growth):
TV = FCF_10 × (1 + g) ÷ (WACC - g)

Terminal Value (Exit Multiple):
TV = EBITDA_10 × Exit Multiple

PV of Terminal Value = TV ÷ (1 + WACC)^10

Enterprise Value = PV of FCF + PV of TV
```

### Step 5: Equity Bridge
```
Enterprise Value
- Net Debt ($4,222M)
- Pension Liabilities ($126M)
- Lease Liabilities ($117M)
+ Cash ($3,014M)
+ Investments ($761M)
= Equity Value

Share Price = Equity Value ÷ Shares Outstanding
```

### Step 6: Financing Adjustment (USS Standalone Only)
```
If cumulative negative FCF > 0:
  Financing Gap = |Cumulative Negative FCF|
  New Debt = Gap × 50%
  New Equity = Gap × 50%
  New Shares = New Equity ÷ (Issue Price × 0.87)

  Adjusted Shares = Base Shares + New Shares
  Adjusted WACC = Base WACC + (Leverage Increase × 0.005)

  Re-run DCF with:
  - Higher WACC
  - Annual interest expense deduction from FCF
  - Diluted share count
```

---

## Why This Methodology Works

### Advantages Over Traditional DCF

1. **Physical Reality Anchor**: Volume capacity is observable and verifiable, not a "% growth" assumption
2. **Price Transparency**: Steel futures trade publicly; assumptions can be tested against market expectations
3. **Operational Insight**: Margin sensitivity reveals true operating leverage, not hidden in "EBITDA growth rate"
4. **Capital Discipline**: Explicit project tracking shows which investments drive value vs. destroy it
5. **Cross-Border Arbitrage**: IRP framework reveals why same assets are worth different amounts to different buyers

### Testable Predictions

The model makes falsifiable predictions:
- If HRC averages $750/ton in 2024 → Flat-Rolled revenue should be ~$8.8B
- If BR2 ramps to 3M tons by 2028 → Mini Mill FCF should exceed $1.5B/year
- If Gary Works BF revamp proceeds → Flat-Rolled margin should improve 2-3%

These can be validated against actual results as they emerge.

### Limitations

**What the model doesn't capture:**
- Synergies beyond capital projects (procurement savings, technology transfer intangibles)
- Regulatory/political risk (government blocks merger, tariffs change)
- Management execution risk beyond the "execution factor" slider
- Currency risk in USSE operations
- Pension/OPEB liability volatility

**Simplifications:**
- Straight-line project ramps (reality is lumpier)
- Constant tax rate (actually varies with jurisdiction mix)
- Terminal value assumes perpetuity (steel industry could structurally decline)
- No working capital seasonality (assumes smooth operations)

---

## Validation and Audit Trail

The genius of this approach: anyone can download the USS 10-K and CME price data to verify the foundation, then debate only the forward-looking assumptions (will prices decline 15%? can they achieve $2.5B incremental EBITDA?), making the model auditable and defensible.

**Key Validation Points:**
- 2023 segment revenues should reconcile to 10-K within 1%
- 2023 EBITDA should reconcile to 10-K within 2%
- Balance sheet items should match 10-K exactly
- Management scenario should reproduce fairness opinion projections
- Wall Street scenario WACC should match analyst range (11.5-13.5%)

See `audits/` folder for detailed verification procedures and source documentation.

---

RAMBAS Team Capstone Project | January 2026
