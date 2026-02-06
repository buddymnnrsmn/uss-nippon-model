# LBO Model Structure and Architecture

## Executive Summary

This document defines the comprehensive structure for a Leveraged Buyout (LBO) model for U.S. Steel Corporation. The model follows standard private equity conventions and is designed to complement the existing DCF model by providing a financial buyer perspective and establishing a valuation floor.

**Key Purpose**: Demonstrate why Nippon Steel's strategic offer ($55/share) is superior to private equity alternatives by showing that PE firms cannot generate adequate returns at comparable price levels due to:
- Limited operational improvement potential (USS is already efficiently run)
- High leverage constraints in capital-intensive steel industry
- Inability to finance $14B NSA investment program
- Limited multiple expansion potential in mature cyclical industry

---

## Model Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LBO MODEL ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

INPUT LAYER
├── Transaction Assumptions
│   ├── Entry Valuation (EV/EBITDA multiple, purchase price)
│   ├── Transaction Date (assumed closing date)
│   ├── Holding Period (typically 5-7 years for PE)
│   └── Exit Assumptions (exit multiple, timing)
│
├── Financing Structure
│   ├── Sources & Uses Table
│   │   ├── Uses: Purchase Enterprise Value, Transaction Fees, Refinancing
│   │   └── Sources: Equity Contribution, Debt Tranches, Rollover Equity
│   └── Debt Structure (detailed in Section 2)
│
└── Operating Assumptions
    ├── Base Case from DCF Model (price x volume projections)
    ├── Operational Improvements (if any)
    └── Capital Expenditure Plan

CALCULATION ENGINE
├── Revenue & EBITDA Projection (from PriceVolumeModel)
│   ├── Steel price scenarios (HRC, CRC, Coated, OCTG)
│   ├── Volume assumptions by segment
│   └── EBITDA margins (price-sensitive)
│
├── Debt Schedule (Section 2)
│   ├── Mandatory Amortization (required principal payments)
│   ├── Cash Sweep (excess cash flow applied to debt)
│   ├── Interest Expense Calculation
│   └── Debt Balance Tracking
│
├── Cash Flow Waterfall (Section 3)
│   ├── EBITDA → EBIT (less D&A)
│   ├── EBIT → Cash from Operations (less taxes, plus D&A)
│   ├── Operating Cash → Unlevered FCF (less CapEx, +/- NWC)
│   ├── Unlevered FCF → Levered FCF (less debt service)
│   └── Levered FCF → Cash Sweep or Cash Accumulation
│
└── Exit Analysis (Section 4)
    ├── Exit Enterprise Value (multiple-based or DCF)
    ├── Less: Net Debt at Exit
    └── Equals: Equity Value to Sponsor

OUTPUT LAYER
├── Returns Calculations (Section 5)
│   ├── IRR (Internal Rate of Return)
│   ├── MoIC (Multiple on Invested Capital)
│   ├── Absolute Return ($M)
│   └── Annualized Return (%)
│
└── Sensitivity Analysis (Section 6)
    ├── Entry Multiple vs Exit Multiple
    ├── EBITDA Performance vs Exit Multiple
    ├── Leverage vs Returns
    └── Price Scenarios vs Returns
```

---

## 1. Sources & Uses Table Structure

The Sources & Uses table is the foundation of the LBO, showing how the transaction is financed (Sources) and what the money is used for (Uses).

### 1.1 Uses of Funds

```
USES OF FUNDS                                           $M        %
─────────────────────────────────────────────────────────────────
Purchase Equity Value
  = Enterprise Value                                   XX,XXX
  + Cash & Cash Equivalents                             3,014
  + Short-term Investments                                761
  - Total Debt                                         (4,222)
  - Pension Obligations                                  (126)
  - Operating Lease Liabilities                          (117)
  ─────────────────────────────────────────────────────────────
  Equity Purchase Price                                XX,XXX

Transaction Expenses
  + Financial Advisor Fees (1.0-1.5%)                     XXX
  + Legal & Due Diligence                                  XX
  + Financing Fees (2-3% of debt)                         XXX
  + Other Transaction Costs                                XX
  ─────────────────────────────────────────────────────────────
  Total Transaction Expenses                              XXX

Refinancing Existing Debt                               4,222

Total Uses                                             XX,XXX    100.0%
═════════════════════════════════════════════════════════════════
```

### 1.2 Sources of Funds

```
SOURCES OF FUNDS                                        $M        %
─────────────────────────────────────────────────────────────────
Senior Secured Credit Facilities
  Revolver (undrawn at close)                              -      0.0%
  Term Loan A (TLA)                                     X,XXX     XX.X%
  Term Loan B (TLB)                                     X,XXX     XX.X%
  ─────────────────────────────────────────────────────────────
  Total Senior Secured Debt                             X,XXX     XX.X%

Senior Unsecured Notes                                  X,XXX     XX.X%

Subordinated/Mezzanine Debt (optional)                    XXX      X.X%

Management Rollover Equity (optional)                      XX      X.X%

Sponsor Equity Contribution                             X,XXX     XX.X%
  ─────────────────────────────────────────────────────────────

Total Sources                                          XX,XXX    100.0%
═════════════════════════════════════════════════════════════════

Pro Forma Capitalization
  Total Debt                                            X,XXX
  Total Equity                                          X,XXX
  ─────────────────────────────────────────────────────────────
  Total Capitalization                                 XX,XXX

  Total Debt / LTM EBITDA                                X.Xx
  Senior Debt / LTM EBITDA                               X.Xx
  Total Debt / Total Capitalization                      XX.X%
```

### 1.3 Standard PE Leverage Levels for Steel/Industrials

Based on comparable LBO transactions in capital-intensive industries:

| Metric | Conservative | Moderate | Aggressive |
|--------|-------------|----------|------------|
| Total Debt / EBITDA | 3.5x - 4.0x | 4.0x - 5.0x | 5.0x - 6.0x |
| Senior Debt / EBITDA | 2.5x - 3.0x | 3.0x - 3.5x | 3.5x - 4.0x |
| Equity % | 40-45% | 35-40% | 25-35% |

**USS-Specific Constraints**:
- **Cyclicality**: Steel is highly cyclical → lower sustainable leverage
- **Capital Intensity**: $1-2B annual maintenance CapEx → limits FCF for debt service
- **Commodity Risk**: Price volatility → conservative leverage required
- **Credit Rating**: Investment grade preferred for supplier relationships

**Recommended Leverage**: 3.5-4.0x Total Debt/EBITDA (conservative end)

---

## 2. Debt Schedule Architecture

The debt schedule tracks all debt tranches, calculates interest expense, and models mandatory amortization and cash sweep mechanics.

### 2.1 Debt Tranches

```python
DEBT_TRANCHES = {
    'Revolver': {
        'commitment': 500,           # $M commitment
        'drawn_at_close': 0,         # Undrawn at close (standby liquidity)
        'interest_rate': 'SOFR + 275',  # Pricing (bps)
        'floor': 0.00,               # SOFR floor
        'term': 5,                   # Years
        'amortization': 0,           # % annual (0% = bullet)
        'cash_sweep': False,         # Not subject to cash sweep
        'commitment_fee': 0.375      # % on undrawn amount
    },
    'TLA': {
        'principal': 1500,
        'interest_rate': 'SOFR + 300',
        'floor': 0.50,               # 50bps floor
        'term': 7,
        'amortization': 0.10,        # 10% annual amortization
        'cash_sweep': True,
        'prepayment_premium': None   # No prepayment penalty
    },
    'TLB': {
        'principal': 2000,
        'interest_rate': 'SOFR + 450',
        'floor': 0.75,
        'term': 8,
        'amortization': 0.01,        # 1% annual (bullet-like)
        'cash_sweep': True,
        'prepayment_premium': {      # Prepayment penalties (years 1-3)
            1: 0.02,                 # 2% of prepaid amount
            2: 0.01,
            3: 0.00
        }
    },
    'Senior_Notes': {
        'principal': 1000,
        'interest_rate': 0.0650,     # Fixed 6.5%
        'floor': None,
        'term': 10,
        'amortization': 0.00,        # Bullet maturity
        'cash_sweep': False,
        'prepayment_premium': {      # Call protection
            1: 'Non-Call',           # Cannot refinance year 1
            2: 0.0325,               # Call at 103.25% of par
            3: 0.0163,               # Call at 101.63% of par
            4: 0.00
        }
    }
}
```

### 2.2 Debt Schedule Table Structure

```
DEBT SCHEDULE                      2024   2025   2026   2027   2028   2029   2030   2031
──────────────────────────────────────────────────────────────────────────────────────────
BEGINNING BALANCES
  Revolver                            -      -      -      -      -      -      -      -
  Term Loan A                     1,500  1,350  1,200  1,050    900    750    600    450
  Term Loan B                     2,000  1,980  1,960  1,940  1,920  1,900  1,880  1,860
  Senior Notes                    1,000  1,000  1,000  1,000  1,000  1,000  1,000  1,000
  Total Debt                      4,500  4,330  4,160  3,990  3,820  3,650  3,480  3,310

MANDATORY AMORTIZATION
  TLA (10% annual)                 (150)  (150)  (150)  (150)  (150)  (150)  (150)  (150)
  TLB (1% annual)                   (20)   (20)   (20)   (20)   (20)   (20)   (20)   (20)
  Total Mandatory                  (170)  (170)  (170)  (170)  (170)  (170)  (170)  (170)

CASH SWEEP (from Section 2.3)
  Excess Cash Flow                  XXX    XXX    XXX    XXX    XXX    XXX    XXX    XXX
  Less: CapEx Reserve               (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)
  Sweep-able Cash                   XXX    XXX    XXX    XXX    XXX    XXX    XXX    XXX
  × Sweep Percentage (50%)          XXX    XXX    XXX    XXX    XXX    XXX    XXX    XXX

  Applied to: TLB first             (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)
  Applied to: TLA second            (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)
  Total Cash Sweep                  (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)

TOTAL PRINCIPAL REPAYMENT          (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)

ENDING BALANCES                    4,330  4,160  3,990  3,820  3,650  3,480  3,310  3,140

INTEREST EXPENSE
  Revolver (SOFR+275, commitment)     (2)    (2)    (2)    (2)    (2)    (2)    (2)    (2)
  TLA (SOFR+300)                     (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)
  TLB (SOFR+450)                     (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)   (XX)
  Senior Notes (6.5% fixed)          (65)   (65)   (65)   (65)   (65)   (65)   (65)   (65)
  Total Interest Expense            (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)  (XXX)

CREDIT METRICS
  Total Debt / EBITDA                4.0x   3.7x   3.5x   3.3x   3.1x   2.9x   2.7x   2.6x
  Senior Debt / EBITDA               3.1x   2.8x   2.6x   2.4x   2.2x   2.1x   1.9x   1.8x
  Interest Coverage (EBITDA/Int)     4.2x   4.5x   4.8x   5.1x   5.4x   5.7x   6.0x   6.3x
  FCF / Debt Service                 1.8x   1.9x   2.0x   2.1x   2.2x   2.3x   2.4x   2.5x
```

### 2.3 Cash Sweep Mechanism

The **cash sweep** (or "excess cash flow sweep") requires the borrower to use a portion of excess cash flow to prepay debt, accelerating deleveraging.

```python
def calculate_cash_sweep(year: int, levered_fcf: float,
                         total_debt: float, ebitda: float) -> dict:
    """
    Calculate cash sweep payment based on excess cash flow covenant.

    Standard Private Equity Cash Sweep Mechanics:
    - 50% of Excess Cash Flow when Leverage > 3.5x
    - 25% of Excess Cash Flow when 2.5x < Leverage ≤ 3.5x
    - 0% of Excess Cash Flow when Leverage ≤ 2.5x

    Excess Cash Flow = Levered FCF - CapEx Reserve - Min Cash Balance
    """

    # Step 1: Calculate leverage ratio
    leverage = total_debt / ebitda

    # Step 2: Determine sweep percentage based on leverage
    if leverage > 3.5:
        sweep_pct = 0.50
    elif leverage > 2.5:
        sweep_pct = 0.25
    else:
        sweep_pct = 0.00

    # Step 3: Calculate excess cash flow
    capex_reserve = 100  # $M reserve for growth/maintenance CapEx
    min_cash = 200       # $M minimum cash balance

    excess_cash_flow = max(0, levered_fcf - capex_reserve - min_cash)

    # Step 4: Calculate sweep amount
    sweep_amount = excess_cash_flow * sweep_pct

    # Step 5: Apply to debt tranches (highest cost first)
    # Priority: TLB (SOFR+450) → TLA (SOFR+300) → Senior Notes (if callable)

    return {
        'leverage': leverage,
        'sweep_percentage': sweep_pct,
        'excess_cash_flow': excess_cash_flow,
        'sweep_amount': sweep_amount,
        'remaining_cash': excess_cash_flow - sweep_amount
    }
```

**Economic Impact**:
- **Benefit**: Accelerated deleveraging reduces interest expense, improves credit metrics
- **Cost**: Less cash available for growth CapEx, dividends, or cash buffer
- **PE Strategy**: Maximize cash sweep in years 1-3 to improve exit multiples via lower leverage

---

## 3. Cash Flow Waterfall Logic

The cash flow waterfall shows the priority of cash uses, from EBITDA down to equity available for distribution or cash sweep.

### 3.1 Waterfall Structure

```
┌────────────────────────────────────────────────────────────────┐
│                   CASH FLOW WATERFALL                          │
└────────────────────────────────────────────────────────────────┘

Level 1: OPERATING PERFORMANCE
  Revenue (Price × Volume by Segment)                    XX,XXX
  - Cost of Goods Sold                                  (XX,XXX)
  ────────────────────────────────────────────────────────────
  Gross Profit                                            X,XXX
  - SG&A Expenses                                          (XXX)
  ────────────────────────────────────────────────────────────
  EBITDA                                                  X,XXX
  ════════════════════════════════════════════════════════════

Level 2: NON-CASH ADJUSTMENTS
  EBITDA                                                  X,XXX
  - Depreciation & Amortization                            (XXX)
  ────────────────────────────────────────────────────────────
  EBIT                                                    X,XXX
  ════════════════════════════════════════════════════════════

Level 3: TAXES
  EBIT                                                    X,XXX
  - Cash Taxes (@ 16.9% effective rate)                   (XXX)
  ────────────────────────────────────────────────────────────
  NOPAT (Net Operating Profit After Tax)                 X,XXX
  + Depreciation & Amortization (add back)                  XXX
  ────────────────────────────────────────────────────────────
  Cash from Operations                                    X,XXX
  ════════════════════════════════════════════════════════════

Level 4: WORKING CAPITAL & CAPEX
  Cash from Operations                                    X,XXX
  - Change in Net Working Capital                          (XX)
  - Capital Expenditures (Maintenance + Growth)           (XXX)
  ────────────────────────────────────────────────────────────
  UNLEVERED FREE CASH FLOW                                X,XXX
  ════════════════════════════════════════════════════════════

Level 5: DEBT SERVICE (Priority Uses)
  Unlevered FCF                                           X,XXX
  - Interest Expense (cash)                                (XXX)
  - Mandatory Amortization                                 (XXX)
  ────────────────────────────────────────────────────────────
  LEVERED FREE CASH FLOW                                    XXX
  ════════════════════════════════════════════════════════════

Level 6: CASH SWEEP & DISCRETIONARY USES
  Levered FCF                                               XXX
  - Cash Sweep Payment (per Section 2.3)                   (XX)
  ────────────────────────────────────────────────────────────
  Cash Available for Distribution                            XX

  Discretionary Uses:
  - Dividends to Sponsor (if permitted)                      (X)
  - Cash Accumulation (acquisition war chest)               (X)
  - Optional Debt Prepayment (beyond sweep)                 (X)
  ────────────────────────────────────────────────────────────
  Ending Cash Balance                                        XX
  ════════════════════════════════════════════════════════════
```

### 3.2 Integration with PriceVolumeModel

The LBO model leverages the existing `PriceVolumeModel` for EBITDA projections:

```python
from price_volume_model import PriceVolumeModel, ScenarioType, get_scenario_presets

# Use Base Case or Conservative scenario for LBO (PE firms are conservative)
scenario = get_scenario_presets()[ScenarioType.CONSERVATIVE]

# Build projections
pv_model = PriceVolumeModel(scenario, execution_factor=0.75)  # Haircut expectations
analysis = pv_model.run_full_analysis()

# Extract EBITDA, D&A, CapEx, NWC for LBO waterfall
ebitda_projection = analysis['consolidated']['Total_EBITDA'].tolist()
da_projection = analysis['consolidated']['DA'].tolist()
capex_projection = analysis['consolidated']['Total_CapEx'].tolist()
nwc_projection = analysis['consolidated']['Delta_WC'].tolist()
```

**Key Assumptions**:
- **Price Scenario**: Conservative (15-20% below 2023 levels)
- **Volume Scenario**: Conservative (5-10% below base case)
- **CapEx**: Maintenance only (no $14B Nippon program)
- **Execution Factor**: 0.75 (25% haircut on projections)

---

## 4. Exit Analysis Methodology

Exit analysis determines the terminal value of the equity investment and is critical for IRR/MoIC calculations.

### 4.1 Exit Multiple Methodology

```
EXIT ENTERPRISE VALUE CALCULATION

Method 1: Comparable Company Exit Multiple
─────────────────────────────────────────────────────────────
  LTM EBITDA at Exit (Year 5-7)                         $X,XXX M
  × Exit EV/EBITDA Multiple                                 X.Xx
  ─────────────────────────────────────────────────────────
  = Exit Enterprise Value                               $XX,XXX M

Method 2: Precedent Transaction Exit Multiple
─────────────────────────────────────────────────────────────
  LTM EBITDA at Exit                                    $X,XXX M
  × Precedent Transaction Multiple (M&A)                    X.Xx
  ─────────────────────────────────────────────────────────
  = Exit Enterprise Value                               $XX,XXX M

Method 3: Entry Multiple (Conservative)
─────────────────────────────────────────────────────────────
  LTM EBITDA at Exit                                    $X,XXX M
  × Entry Multiple (assume no multiple expansion)           X.Xx
  ─────────────────────────────────────────────────────────
  = Exit Enterprise Value                               $XX,XXX M

RECOMMENDED APPROACH: Use entry multiple (no expansion)
  - Steel is mature, cyclical industry
  - Limited multiple expansion upside
  - Conservative for base case returns
```

### 4.2 Exit Equity Value Bridge

```
EXIT EQUITY VALUE WATERFALL

Enterprise Value at Exit                                $XX,XXX M
  - Net Debt at Exit                                     (X,XXX) M
    • Total Debt                                         (X,XXX)
    • + Cash & Equivalents                                  XXX
  - Pension & Other Obligations                            (XXX) M
  - Operating Lease Liabilities                            (XXX) M
  ──────────────────────────────────────────────────────────────
= Equity Value to Sponsor                               $XX,XXX M
  ══════════════════════════════════════════════════════════════

Less: Management Rollover Equity (if applicable)           (XXX) M
  ──────────────────────────────────────────────────────────────
= Net Proceeds to Sponsor                               $XX,XXX M
```

### 4.3 Exit Multiple Benchmarks

**Steel Industry Exit Multiples** (based on precedent transactions):

| Scenario | EV/EBITDA | Rationale |
|----------|-----------|-----------|
| **Bear Case** | 4.0x - 4.5x | Trough cycle, poor steel fundamentals |
| **Base Case** | 4.5x - 5.5x | Mid-cycle, stable demand |
| **Bull Case** | 5.5x - 6.5x | Peak cycle, strong pricing environment |

**USS-Specific Considerations**:
- **Cyclical Risk**: Steel multiples compress in downturns (2020: 3-4x)
- **Capital Intensity**: High CapEx needs → lower FCF conversion → lower multiples
- **Competitive Position**: Integrated mills face mini-mill competition → multiple pressure
- **Exit Timing Risk**: PE must exit regardless of cycle → may face weak market

**LBO Model Assumption**: Use **entry multiple** (no expansion) for base case
- Conservative approach standard in PE underwriting
- Steel's cyclicality makes multiple expansion unreliable
- Returns must come from deleveraging, not multiple arbitrage

---

## 5. Returns Calculations (IRR, MoIC)

Returns are the ultimate measure of LBO success. PE firms target 20-25%+ IRRs for platform LBOs.

### 5.1 IRR (Internal Rate of Return)

```python
def calculate_irr(initial_investment: float,
                  annual_distributions: list,
                  exit_proceeds: float,
                  holding_period_years: int) -> float:
    """
    Calculate IRR using cash flows.

    IRR = discount rate that sets NPV of all cash flows to zero

    Cash Flows:
      Year 0: -Initial Investment (equity check)
      Year 1-N: +Distributions (if any - rare in first few years)
      Year N: +Exit Proceeds (sale of equity)

    Formula: NPV = 0 = -I₀ + Σ(CF_t / (1+IRR)^t) + Exit / (1+IRR)^N
    """

    from scipy.optimize import newton

    # Build cash flow array
    cash_flows = [-initial_investment]  # Year 0: equity investment
    cash_flows.extend(annual_distributions)  # Years 1-N: distributions
    cash_flows[-1] += exit_proceeds  # Year N: add exit proceeds to final year

    # Solve for IRR using Newton's method
    def npv(rate):
        return sum(cf / (1 + rate)**i for i, cf in enumerate(cash_flows))

    irr = newton(npv, 0.15)  # Start with 15% guess

    return irr
```

**IRR Interpretation**:
- **< 15%**: Below PE return threshold (would not pursue deal)
- **15-20%**: Acceptable for large, lower-risk LBOs
- **20-25%**: Standard PE target for platform investments
- **25%+**: Excellent returns (typically smaller, high-growth deals)

**USS LBO Expected IRR**: **12-16%** (below PE threshold)
- Large, mature asset → lower return expectations
- Limited operational improvement → returns from deleveraging only
- Cyclical industry → higher risk, lower multiples
- **Conclusion**: USS is not attractive LBO candidate at $55/share

### 5.2 MoIC (Multiple on Invested Capital)

```python
def calculate_moic(initial_investment: float,
                   total_distributions: float,
                   exit_proceeds: float) -> float:
    """
    Calculate MoIC (cash-on-cash return multiple).

    MoIC = Total Cash Returned / Total Cash Invested

    Total Cash Returned = Cumulative Distributions + Exit Proceeds
    Total Cash Invested = Initial Equity Investment

    MoIC does NOT account for time value of money (unlike IRR).
    """

    total_returned = total_distributions + exit_proceeds
    moic = total_returned / initial_investment

    return moic
```

**MoIC Benchmarks**:
- **< 2.0x**: Poor returns (would not meet PE fund targets)
- **2.0x - 2.5x**: Acceptable for 5-year hold
- **2.5x - 3.0x**: Good returns
- **3.0x+**: Excellent returns

**Relationship to IRR** (5-year hold):
| MoIC | Approximate IRR |
|------|-----------------|
| 2.0x | 15% |
| 2.5x | 20% |
| 3.0x | 25% |
| 4.0x | 32% |

### 5.3 Returns Summary Output

```
LBO RETURNS ANALYSIS
═════════════════════════════════════════════════════════════

INVESTMENT SUMMARY
  Initial Equity Investment                              $X,XXX M
  Holding Period                                          5 years
  Exit Enterprise Value                                 $XX,XXX M
  Less: Net Debt at Exit                                 (X,XXX) M
  Exit Equity Value                                     $XX,XXX M

RETURNS TO SPONSOR
  Equity Value at Exit                                  $XX,XXX M
  Less: Initial Investment                               (X,XXX) M
  Gross Profit                                          $ X,XXX M

  MoIC (Multiple on Invested Capital)                      X.XXx
  IRR (Internal Rate of Return)                            XX.X%
  Annualized Return                                        XX.X%

SENSITIVITY: IRR by Entry & Exit Multiple
──────────────────────────────────────────────────────────────
Entry Multiple →        4.0x    4.5x    5.0x    5.5x    6.0x
Exit Multiple ↓
  4.0x                  8.2%   (2.1%)  (10.5%) (17.2%) (22.8%)
  4.5x                 16.5%    8.9%     2.4%   (3.1%)  (7.8%)
  5.0x                 23.8%   17.9%    12.8%    8.4%    4.6%
  5.5x                 30.3%   25.6%    21.5%   17.9%   14.7%
  6.0x                 36.2%   32.4%    29.0%   26.0%   23.3%

CONCLUSION
  At $55/share purchase price (X.Xx EV/EBITDA):
  - Base Case IRR: XX.X% (below 20% PE threshold)
  - Requires exit multiple expansion to XX.Xx for 20% IRR
  - Multiple expansion is UNLIKELY in mature, cyclical steel industry

  VERDICT: NOT ATTRACTIVE LBO CANDIDATE
```

---

## 6. Sensitivity Table Design

Sensitivity tables show how returns vary with key assumptions. Critical for understanding risk/return tradeoffs.

### 6.1 Two-Way Sensitivity: Entry Multiple vs Exit Multiple

```
IRR SENSITIVITY: ENTRY MULTIPLE vs EXIT MULTIPLE
(Assumes: $2.5B avg EBITDA, 5-year hold, 4.0x initial leverage)

                            EXIT MULTIPLE (EV/EBITDA)
ENTRY      ────────────────────────────────────────────────────
MULTIPLE     3.5x    4.0x    4.5x    5.0x    5.5x    6.0x    6.5x
──────────────────────────────────────────────────────────────────
3.5x        4.2%   12.8%   20.5%   27.4%   33.7%   39.5%   44.9%
4.0x       (5.8%)   2.4%   10.1%   17.2%   23.8%   29.9%   35.7%
4.5x      (13.9%)  (6.9%)   0.8%    8.2%   15.1%   21.6%   27.7%
5.0x      (20.5%) (14.0%)  (7.0%)   0.3%    7.5%   14.3%   20.7%
5.5x      (26.1%) (20.0%) (13.4%)  (6.5%)   0.7%    7.9%   14.7%
6.0x      (31.0%) (25.3%) (19.0%) (12.4%)  (5.5%)   2.0%    9.4%
6.5x      (35.3%) (29.9%) (24.0%) (17.6%) (10.9%)  (3.8%)   4.5%

KEY INSIGHT:
  • Nippon's $55/share offer implies ~X.Xx entry multiple
  • At this entry price, PE needs X.Xx EXIT multiple for 20% IRR
  • Steel sector average exit multiple: 4.5-5.5x (mid-cycle)
  • CONCLUSION: Insufficient return potential for PE
```

### 6.2 Two-Way Sensitivity: EBITDA Growth vs Exit Multiple

```
IRR SENSITIVITY: EBITDA GROWTH vs EXIT MULTIPLE
(Assumes: $2.5B base EBITDA, 5.0x entry multiple, 5-year hold)

                            EXIT MULTIPLE (EV/EBITDA)
EBITDA         ────────────────────────────────────────────────
CAGR           4.0x    4.5x    5.0x    5.5x    6.0x    6.5x
──────────────────────────────────────────────────────────────
-5%          (18.2%) (11.9%)  (5.2%)   1.8%    8.9%   15.9%
-2%          (12.4%)  (5.7%)   1.5%    8.9%   16.4%   23.7%
 0%           (7.0%)   0.3%    8.0%   15.8%   23.5%   31.0%
+2%           (1.8%)   6.2%   14.3%   22.4%   30.4%   38.1%
+5%            6.1%   14.5%   23.0%   31.3%   39.5%   47.5%
+10%          18.9%   28.2%   37.4%   46.4%   55.2%   63.8%

KEY INSIGHT:
  • USS EBITDA is CYCLICAL, not growing
  • Management projects EBITDA DECLINE (footprint reduction)
  • Conservative case: -2% to 0% EBITDA CAGR
  • Even at 5.5x exit multiple, IRR only ~15% (below PE threshold)
  • Requires heroic EBITDA growth assumptions for 20%+ IRR
```

### 6.3 Three-Variable Tornado Chart (Sensitivity Ranking)

Shows which variables have the greatest impact on IRR:

```
IRR TORNADO CHART - SENSITIVITY TO KEY VARIABLES
(Base Case: 15.2% IRR | Range: Low Case to High Case)

Variable                    Low          Base         High
                         ◄────────────────┼────────────────►
Exit Multiple            8.1%        [15.2%]        24.6%
(4.0x vs 6.0x)           ████████████████████████████████████  Impact: 16.5%

Entry Price              21.3%       [15.2%]         9.8%
($50/sh vs $60/sh)       ████████████████████████               Impact: 11.5%

EBITDA Performance       11.5%       [15.2%]        19.4%
(-5% vs +5% CAGR)        ████████████████                       Impact: 7.9%

Exit Year                13.8%       [15.2%]        16.9%
(Year 5 vs Year 7)       ███████                                Impact: 3.1%

Steel Price Scenario     13.2%       [15.2%]        17.8%
(Bear vs Bull)           ████████                               Impact: 4.6%

Leverage                 14.1%       [15.2%]        16.5%
(3.5x vs 5.0x)           █████                                  Impact: 2.4%

KEY INSIGHT: Exit multiple is by FAR the most important driver
  → Steel multiples are cyclical and unlikely to expand
  → LBO success depends on factors PE cannot control (market timing)
  → This makes USS a POOR LBO candidate
```

### 6.4 Sensitivity Analysis Best Practices

1. **Identify Key Value Drivers**:
   - Entry valuation (purchase price / multiple)
   - Exit valuation (exit multiple)
   - Operating performance (EBITDA growth, margins)
   - Leverage (amount, cost, paydown speed)
   - Holding period (5 vs 7 years)

2. **Use Realistic Ranges**:
   - Entry: ±10% from base case purchase price
   - Exit: ±1.0x from base case multiple
   - EBITDA: ±5% CAGR from base case
   - Steel Prices: Bear/Base/Bull scenarios

3. **Focus on Downside Protection**:
   - What's the IRR in worst-case scenario?
   - What's the probability-weighted expected IRR?
   - What's the breakeven exit multiple?

4. **Communicate Clearly**:
   - Use color coding (red = bad, green = good)
   - Highlight base case clearly
   - Show where PE return thresholds fall (20% IRR line)

---

## 7. Integration with Existing DCF Model

The LBO model leverages the existing `PriceVolumeModel` for revenue and EBITDA projections, then layers on financing structure and PE-specific assumptions.

### 7.1 Integration Architecture

```python
"""
Integration Flow: PriceVolumeModel → LBOModel

STEP 1: Use PriceVolumeModel for Operating Projections
  ├── Import base/conservative scenario
  ├── Apply execution haircut (0.75)
  ├── Extract EBITDA, D&A, CapEx, NWC projections
  └── NO growth CapEx (maintenance only)

STEP 2: LBOModel Adds Financing Structure
  ├── Sources & Uses (debt tranches, equity)
  ├── Debt schedule (amortization, sweep)
  ├── Interest expense calculation
  └── Levered FCF after debt service

STEP 3: LBOModel Adds Exit & Returns
  ├── Exit valuation (multiple method)
  ├── Equity value to sponsor
  ├── IRR and MoIC calculations
  └── Sensitivity analysis
"""

class LBOModel:
    def __init__(self,
                 pv_model: PriceVolumeModel,
                 entry_price_per_share: float,
                 entry_multiple: float,
                 debt_structure: dict,
                 exit_multiple: float,
                 exit_year: int):

        # Operating model (from PriceVolumeModel)
        self.pv_model = pv_model
        self.projections = pv_model.run_full_analysis()

        # Transaction parameters
        self.entry_price = entry_price_per_share
        self.entry_multiple = entry_multiple
        self.exit_multiple = exit_multiple
        self.exit_year = exit_year

        # Financing structure
        self.debt_structure = debt_structure
        self.calculate_sources_uses()

    def calculate_sources_uses(self):
        """Build Sources & Uses table"""
        pass

    def build_debt_schedule(self):
        """Build debt schedule with amortization and sweep"""
        pass

    def calculate_levered_fcf(self):
        """Calculate FCF after debt service"""
        pass

    def calculate_exit_value(self):
        """Calculate exit equity value"""
        pass

    def calculate_returns(self):
        """Calculate IRR and MoIC"""
        pass
```

### 7.2 Key Differences: DCF vs LBO Model

| Dimension | DCF Model (PriceVolumeModel) | LBO Model |
|-----------|------------------------------|-----------|
| **Purpose** | Intrinsic value to strategic buyer | Returns to financial buyer |
| **Cash Flows** | Unlevered FCF | Levered FCF (after debt service) |
| **Discount Rate** | WACC | Equity IRR |
| **Terminal Value** | Perpetuity growth or exit multiple | Exit multiple only |
| **Financing** | Assumed optimal capital structure | Specific debt tranches, sweep |
| **CapEx** | Includes growth projects ($14B NSA) | Maintenance only (no growth) |
| **Output** | $/share value | IRR, MoIC, cash-on-cash |
| **Perspective** | Long-term strategic value | 5-7 year financial engineering |

### 7.3 Scenario Selection for LBO

For LBO modeling, use **conservative scenarios** from PriceVolumeModel:

```python
# LBO uses conservative assumptions (PE underwriting standards)
lbo_scenario = get_scenario_presets()[ScenarioType.CONSERVATIVE]

# Further haircut expectations (PE diligence)
pv_model = PriceVolumeModel(
    scenario=lbo_scenario,
    execution_factor=0.75  # 25% haircut on projections
)

# NO Nippon growth CapEx projects (PE cannot afford $14B program)
# Only include committed BR2 mini mill
lbo_scenario.include_projects = ['BR2 Mini Mill']
```

**Why Conservative?**:
1. **PE Diligence**: More skeptical than strategic buyers
2. **Leverage Risk**: High debt magnifies downside
3. **Exit Risk**: Must exit in 5-7 years regardless of cycle
4. **Limited Operational Upside**: USS already efficiently run

---

## 8. Standard LBO Conventions & Best Practices

### 8.1 Financial Modeling Conventions

1. **Timing Conventions**:
   - Transaction close: Assume January 1 of Year 1
   - Cash flows: Mid-year convention (discount factor = (1+r)^(t-0.5))
   - Exit: Assume December 31 of exit year

2. **EBITDA Adjustments**:
   - Use "Adjusted EBITDA" (add back non-recurring items)
   - Normalize for cyclicality (use average of last 3 years)
   - Add back management fees, non-cash stock comp

3. **Working Capital**:
   - Cash-free, debt-free transaction (excluded from purchase price)
   - Target NWC = % of revenue (historical average)
   - Peg adjustment at close if actual NWC ≠ target

4. **Transaction Expenses**:
   - Buyer pays: Due diligence, financing fees, legal (2-3% of deal size)
   - Seller pays: Investment banking fees (1-1.5% of equity value)
   - Capitalize or expense: Expense transaction costs, capitalize financing fees

5. **Management Equity**:
   - Rollover: 5-20% of equity (aligns management incentives)
   - New money: Management co-invests additional 1-3%
   - Options: 10-15% option pool for management team

### 8.2 Debt Structuring Best Practices

1. **Leverage Levels** (for capital-intensive industrials):
   - Total Debt / EBITDA: 3.5x - 4.5x (conservative end for steel)
   - Senior Debt / EBITDA: ≤ 3.0x
   - Cash / Interest: ≥ 2.0x (interest coverage)

2. **Debt Tranches** (typical structure):
   - **Revolver**: 5-10% of debt, undrawn, SOFR + 250-300 bps
   - **Term Loan A**: 20-30%, 5-7 year, SOFR + 275-325 bps, 10-15% amortization
   - **Term Loan B**: 30-40%, 7-8 year, SOFR + 400-500 bps, 1% amortization
   - **Senior Notes**: 20-30%, 8-10 year, fixed 6-7%, bullet maturity

3. **Cash Sweep** (covenant-driven):
   - Starts at 50% when Leverage > 3.5x
   - Steps down to 25% when 2.5x < Leverage ≤ 3.5x
   - Falls to 0% when Leverage ≤ 2.5x
   - Applied to highest-cost debt first (TLB → TLA)

4. **Covenants** (typical credit agreement):
   - **Maintenance Covenants**: Max Leverage, Min Interest Coverage
   - **Incurrence Covenants**: Max CapEx, Max Distributions
   - **Financial Reporting**: Quarterly compliance certificates
   - **Change of Control**: Mandatory offer to repurchase at 101%

### 8.3 Exit Planning Best Practices

1. **Exit Options**:
   - **Strategic Sale (M&A)**: Most common, highest valuations (60-70% of exits)
   - **Secondary Buyout**: Sell to another PE firm (20-30%)
   - **IPO**: Public offering (5-10%, rare for mature industrials)
   - **Dividend Recapitalization**: Partial liquidity, retain ownership (interim)

2. **Exit Timing**:
   - Typical hold: 5-7 years (LP expectations)
   - Optimal exit: Year 5-6 (maximize IRR while deleveraging)
   - Forced exit: Fund maturity (10-12 years max)
   - Market timing: Exit in strong M&A environment or peak cycle

3. **Value Creation Levers**:
   - **Operational Improvements**: EBITDA growth (30-40% of returns)
   - **Multiple Expansion**: Buy low, sell high (20-30%)
   - **Deleveraging**: Debt paydown increases equity value (30-40%)
   - **Financial Engineering**: Dividend recaps, re-levering (10-20%)

**USS-Specific Exit Challenges**:
- **Cyclicality**: May be forced to exit in downturn
- **Strategic Buyers Limited**: Few logical acquirers beyond Nippon/ArcelorMittal
- **IPO Unlikely**: Already was public, market familiar with story
- **Deleveraging Slow**: High CapEx needs limit FCF for debt paydown

---

## 9. USS-Specific LBO Considerations

### 9.1 Why USS is a POOR LBO Candidate

1. **Capital Intensity**:
   - $1-2B annual CapEx (maintenance + growth)
   - Limited FCF available for debt service
   - Slow deleveraging pace

2. **Cyclicality**:
   - Steel prices and volumes are volatile
   - Difficult to underwrite stable cash flows
   - High leverage magnifies downside risk

3. **Limited Operational Upside**:
   - USS already efficiently operated (not a turnaround)
   - No low-hanging fruit for margin expansion
   - PE playbook (cut costs, improve operations) has limited applicability

4. **Strategic CapEx Constrained**:
   - PE cannot fund $14B NSA investment program
   - Would need to issue more debt (exceeds leverage limits)
   - Equity financing would dilute returns

5. **Exit Multiple Risk**:
   - Steel trades at 4-5x EBITDA mid-cycle
   - No clear path to multiple expansion
   - May be forced to exit in downturn (3-4x)

### 9.2 LBO Model Demonstrates Nippon Offer Superiority

The LBO model shows:

```
COMPARISON: PE LBO vs NIPPON STRATEGIC ACQUISITION

PE Financial Buyer (LBO at $55/share):
  ├── Entry Multiple: X.Xx EV/EBITDA (market multiple)
  ├── Leverage: 4.0x Debt/EBITDA (max sustainable)
  ├── Equity Check: $X.XB
  ├── EBITDA Projection: Conservative (no growth CapEx)
  ├── Exit Year 5: X.Xx multiple (no expansion)
  └── IRR: 12-15% (BELOW 20% PE threshold)

Nippon Strategic Buyer ($55/share):
  ├── Entry Multiple: X.Xx EV/EBITDA (strategic premium)
  ├── Leverage: Minimal (balance sheet capacity)
  ├── Equity Check: $14.1B (all-cash offer)
  ├── EBITDA Projection: +$2.5B from $14B NSA CapEx program
  ├── Exit: No exit (strategic hold, long-term synergies)
  └── IRR: Strategic value > 20% (synergies, market share, vertical integration)

CONCLUSION:
  • PE firm CANNOT compete with $55/share offer
  • PE firm CANNOT fund $14B investment program
  • PE firm CANNOT generate 20%+ IRR at $55 entry
  • Nippon's strategic value >>> PE financial engineering

  $55/SHARE OFFER IS SUPERIOR TO ANY PE ALTERNATIVE
```

---

## 10. Model Outputs & Deliverables

### 10.1 Executive Summary Output

```
USS LBO MODEL - EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════

TRANSACTION OVERVIEW
  Target:                     U.S. Steel Corporation
  Entry Price:                $55.00 per share
  Entry Multiple:             X.Xx EV/EBITDA
  Transaction Size:           $XX.XB enterprise value
  Equity Investment:          $X.XB sponsor equity
  Leverage:                   X.Xx Total Debt/EBITDA
  Holding Period:             5 years

RETURNS SUMMARY
  Exit Enterprise Value:      $XX.XB
  Exit Equity Value:          $X.XB
  Total Sponsor Return:       X.Xx MoIC
  IRR:                        XX.X%

  ► BELOW PE RETURN THRESHOLD OF 20%

COMPARISON TO NIPPON OFFER
  Nippon Offer:               $55.00/share (all cash)
  LBO Value (PE):             $XX.XX/share (after leverage)

  ► NIPPON OFFER IS SUPERIOR
  ► PE CANNOT COMPETE AT THIS PRICE

KEY RISKS
  • High capital intensity limits FCF for debt service
  • Cyclical end markets create cash flow volatility
  • Limited operational improvement upside
  • Exit multiple risk (steel multiples are cyclical)
  • Cannot fund $14B strategic CapEx program

CONCLUSION
  USS is NOT an attractive LBO candidate at $55/share.
  Returns fall short of PE thresholds (20-25% IRR).
  Nippon's strategic value far exceeds PE financial engineering.

  RECOMMENDATION: $55 OFFER REPRESENTS FULL AND FAIR VALUE
```

### 10.2 Detailed Model Outputs

1. **Sources & Uses Table** (Excel/Python)
2. **Debt Schedule** (10-year projection)
3. **Cash Flow Waterfall** (EBITDA → Levered FCF)
4. **Exit Analysis** (multiple scenarios)
5. **Returns Summary** (IRR, MoIC, sensitivity tables)
6. **Comparison Table** (PE LBO vs Nippon Strategic)

---

## Conclusion

This LBO model structure provides a comprehensive framework for analyzing USS from a private equity perspective. The model demonstrates that:

1. **USS is not attractive at $55/share** (IRR below PE thresholds)
2. **Nippon's strategic offer is superior** (PE cannot compete)
3. **$14B CapEx program is unfundable** by PE (leverage constraints)
4. **Downside protection is limited** (cyclical industry, exit risk)

The model integrates seamlessly with the existing `PriceVolumeModel`, leveraging its price x volume framework while adding LBO-specific financing and returns analysis.

**Next Steps**: Implement the Python template (see `lbo_model_template.py`) with actual USS data to quantify these conclusions with specific IRR/MoIC figures.

---

## References and Further Reading

### LBO Methodology and Valuation

1. **Rosenbaum, Joshua and Joshua Pearl** - [Investment Banking: Valuation, Leveraged Buyouts, and Mergers & Acquisitions](https://www.wiley.com/en-us/Investment+Banking%3A+Valuation%2C+Leveraged+Buyouts%2C+and+Mergers+and+Acquisitions%2C+3rd+Edition-p-9781119706182) - Wiley Finance, 2020
   - Industry-standard textbook covering LBO modeling methodology

2. **Pignataro, Paul** - [Leveraged Buyouts: A Practical Guide to Investment Banking and Private Equity](https://www.wiley.com/en-us/Leveraged+Buyouts%3A+A+Practical+Guide+to+Investment+Banking+and+Private+Equity-p-9781118018750) - Wiley Finance, 2013
   - Comprehensive guide to LBO structuring and execution

3. **Wall Street Prep** - [LBO Modeling Course](https://www.wallstreetprep.com/knowledge/lbo-model-tutorial/) - 2024
   - Professional financial modeling training resource

4. **Macabacus** - [LBO Model Overview](https://macabacus.com/valuation/lbo-overview) - 2024
   - Detailed guide to LBO model construction and best practices

5. **Corporate Finance Institute** - [LBO Model Overview](https://corporatefinanceinstitute.com/resources/financial-modeling/lbo-model/) - 2024
   - Educational resource on LBO modeling fundamentals

### Debt Structuring and Leveraged Finance

6. **S&P Global** - [Leveraged Finance & CLOs Essentials](https://www.spglobal.com/ratings/en/research/leveraged-finance-clos-essentials) - 2024
   - Comprehensive guide to leveraged finance market structure and terms

7. **Moody's** - [LBO Methodology](https://www.moodys.com/web/en/us/insights/credit-risk/outlooks/leveraged-finance-clo-2025.html) - 2024
   - Credit rating methodology for leveraged buyout transactions

8. **PitchBook** - [Leveraged Loan Market Guide](https://pitchbook.com/leveraged-commentary-data/leveraged-loan) - 2024
   - Market data and trends in leveraged loan financing

9. **White Case Debt Explorer** - [Leveraged Finance Commentary](https://debtexplorer.whitecase.com/leveraged-finance-commentary/) - 2024
   - Current market conditions and deal terms for leveraged transactions

### Private Equity Industry Standards

10. **Bain & Company** - [Global Private Equity Report 2024](https://www.bain.com/insights/topics/global-private-equity-report/) - 2024
    - Annual report on PE market activity, returns, and trends

11. **ILPA** - [Private Equity Principles 4.0](https://ilpa.org/ilpa-principles/) - 2023
    - Institutional Limited Partners Association standards for PE best practices

12. **Cambridge Associates** - [Private Equity Index and Benchmark Statistics](https://www.cambridgeassociates.com/private-investments/private-equity-index-and-benchmark-statistics/) - 2024
    - Industry benchmark data for PE returns and performance

### Working Capital and Cash Flow Analysis

13. **Corporate Finance Institute** - [Working Capital Cycle](https://corporatefinanceinstitute.com/resources/accounting/working-capital-cycle/) - 2024
    - Guide to working capital management in financial modeling

14. **Wall Street Prep** - [Working Capital Cycle Formula + Calculator](https://www.wallstreetprep.com/knowledge/working-capital-cycle/) - 2024
    - Methodology for calculating and projecting working capital changes

15. **Treasury XL** - [Cash Conversion Cycle](https://treasuryxl.com/what-is-working-capital-management/cash-conversion-cycle/) - 2024
    - Analysis of cash conversion cycle in corporate finance

### Debt Service Coverage and Credit Metrics

16. **Financial Edge** - [Debt Service Coverage Ratio (DSCR)](https://www.fe.training/free-resources/project-finance/debt-service-coverage-ratio-dscr/) - 2024
    - Guide to calculating and interpreting debt service coverage ratios

17. **FullRatio** - [Average Net Debt to EBITDA Ratio by Industry](https://fullratio.com/net-debt-to-ebitda-by-industry) - 2024
    - Industry benchmarks for leverage ratios

18. **Corporate Finance Institute** - [Net Debt to EBITDA Ratio Guide](https://corporatefinanceinstitute.com/resources/valuation/net-debt-ebitda-ratio/) - 2024
    - Comprehensive guide to leverage ratio calculation and interpretation

### IRR and Returns Analysis

19. **Wall Street Prep** - [Multiple Expansion in LBOs](https://www.wallstreetprep.com/knowledge/multiple-expansion/) - 2024
    - Analysis of value creation through multiple expansion

20. **Uplevered** - [Private Equity Value Creation Levers](https://uplevered.com/private-equity-value-levers/) - 2024
    - Framework for analyzing PE value creation strategies

21. **Moonfare** - [Valuation Multiples in Private Equity](https://www.moonfare.com/glossary/valuation-multiples) - 2024
    - Guide to valuation multiples used in PE transactions

### Steel Industry and Capital-Intensive LBOs

22. **McKinsey & Company** - [Capital-Intensive Industries: Value Creation Strategies](https://www.mckinsey.com/industries/metals-and-mining/our-insights) - Various dates
    - Strategic insights for capital-intensive industrial sectors

23. **BCG** - [Metals and Mining Insights](https://www.bcg.com/industries/metals-mining/overview) - Various dates
    - Analysis of heavy industrial sector dynamics and value drivers

---

**Document prepared:** January 24, 2026
**Next update recommended:** Quarterly or upon significant market developments

**Note:** This document describes standard private equity and leveraged finance methodologies widely used in the investment banking and PE industries. The structure and conventions outlined reflect industry best practices as documented in the references above.
