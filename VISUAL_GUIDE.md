# Visual Guide to the USS/Nippon Steel Financial Model

This guide explains the three visual diagrams created to illustrate how the Python financial model works.

## Overview

The model consists of two main Python files:
1. **price_volume_model.py** - Core financial model engine
2. **interactive_dashboard.py** - Streamlit web interface

## Diagram 1: Model Architecture (`model_architecture.png`)

### What it shows:
A complete top-to-bottom view of the model's architecture, from inputs to final valuations.

### Key Layers:

**Layer 1: INPUTS**
- **Scenario Selection**: 5 pre-built scenarios (Base Case, Conservative, Wall Street, Management, Nippon Commitments)
- **Steel Prices**: Benchmark prices for HRC, CRC, OCTG (2023 base levels)
- **Volume Factors**: Multipliers and growth rates by segment
- **WACC Parameters**: Discount rates, terminal growth, exit multiples
- **Capital Projects**: $14B investment program options

**Layer 2: SEGMENT PROCESSING**
- 4 business segments modeled separately:
  - **Flat-Rolled**: Integrated steel mills (Gary, Mon Valley) - 8.7M tons/year
  - **Mini Mill**: Electric arc furnaces (Big River Steel) - 2.4M tons/year
  - **USSE**: European operations (Slovakia) - 3.9M tons/year
  - **Tubular**: Oil country tubular goods - 0.5M tons/year

**Layer 3: CALCULATIONS**
- **Price × Volume Revenue Model**: Core methodology
  1. Calculate Volume = Base × Factor × (1 + Growth)^years + Projects
  2. Calculate Price = Benchmark × (1 + Premium) × (1 + Inflation)^years
  3. Revenue = Volume × Price
  4. EBITDA = Revenue × Margin (adjusted for price level)
  5. FCF = EBITDA - D&A - Tax - CapEx - ΔWC

- **Capital Project Impact**: Incremental EBITDA and volume from investments

**Layer 4: CONSOLIDATION**
- Sum all 4 segments to create consolidated 10-year FCF projection (2024-2033)

**Layer 5: DUAL VALUATION**
- **USS Standalone**: Discount at 10.9% WACC (USS's cost of capital)
  - Includes financing penalty if large projects selected (debt + equity dilution)

- **Nippon Valuation**: Discount at ~7.5% IRP-adjusted WACC
  - JPY WACC converted to USD using Interest Rate Parity formula
  - No financing penalty (Nippon has balance sheet capacity)

**Layer 6: FINAL OUTPUTS**
- **USS - No Sale Value**: ~$50/share (Base Case)
- **Value to Nippon**: ~$75/share (Base Case)
- **WACC Advantage**: ~$25/share gap from 3.3% lower discount rate

### Key Insights:
1. Model uses Price × Volume methodology to derive revenue from steel market fundamentals
2. 4 segments modeled separately, then consolidated for enterprise valuation
3. Dual perspective captures the WACC arbitrage opportunity for Nippon
4. The ~$25/share valuation gap explains why the deal makes economic sense for Nippon

---

## Diagram 2: Dashboard User Flow (`dashboard_flow.png`)

### What it shows:
How users interact with the Streamlit dashboard and the real-time calculation flow.

### Components:

**1. User Entry Point**
- User launches dashboard with `streamlit run interactive_dashboard.py`
- Dashboard loads in web browser at localhost:8501

**2. Sidebar Controls** (Left panel)
- Select Scenario (dropdown with 6 options)
- Adjust Steel Prices (sliders for price factors)
- Modify Volumes (segment volume multipliers)
- Set WACC (discount rates, terminal assumptions)
- Enable Projects (checkboxes for capital investments)
- Execution Factor (risk haircut for project benefits)

**3. Model Engine** (Center)
- PriceVolumeModel class processes inputs
- Builds scenario from user selections
- Calculates segment projections (Price × Volume → Revenue → EBITDA → FCF)
- Consolidates 4 segments
- Runs dual DCF (USS standalone 10.9% vs. Nippon IRP 7.5%)

**4. Visualization Layer** (Middle)
- **Charts (Plotly)**: FCF by segment over time, valuation bars, sensitivity curves
- **Tables (Pandas)**: Consolidated financials, scenario comparison, project NPV
- **Metrics (Streamlit)**: Share prices, WACC advantage, 10Y total FCF

**5. Output Sections** (Bottom - 8 sections)
- Executive Summary
- Valuation Details
- Scenario Comparison
- FCF Projection
- Segment Analysis
- Sensitivity Analysis
- IRP Adjustment
- Detailed Tables

**6. Feedback Loop**
- User reviews outputs
- Adjusts sidebar controls
- Model recalculates in real-time
- Dashboard updates (marked "LIVE Updates")

### Key Features:
- ✓ Real-time recalculation on any input change
- ✓ 5+ pre-built scenarios for quick analysis
- ✓ Interactive sliders for sensitivity analysis
- ✓ Dual perspective toggle (USS vs. Nippon view)
- ✓ WACC sensitivity charts
- ✓ Steel price scenario modeling
- ✓ Capital project selector
- ✓ Execution risk haircut (50%-100%)

---

## Diagram 3: Calculation Flow (`calculation_flow.png`)

### What it shows:
Step-by-step breakdown of the calculation process for a single segment in a single year.

### Execution Steps:

**FOR EACH SEGMENT (Flat-Rolled, Mini Mill, USSE, Tubular):**
**FOR EACH YEAR (2024-2033):**

**STEP 1: Calculate Volume**
```
Volume (000 tons) = Base_2023 × Vol_Factor × (1 + Growth_Rate)^years + Project_Volume_Addition
```
Example: 8,706 × 0.98 × (1 - 0.01)^1 + 0 = 8,454 tons

**STEP 2: Calculate Price**
```
Price ($/ton) = Benchmark_2023 × Price_Factor × (1 + Premium) × (1 + Annual_Growth)^years
```
Example: $680 × 0.95 × 1.515 × (1.02)^1 = $996/ton

**STEP 3: Calculate Revenue**
```
Revenue ($M) = (Volume × Price) / 1000
```
Example: (8,454 tons × $996/ton) / 1000 = $8,420M revenue

**STEP 4: Calculate EBITDA**
```
Margin = Base_Margin + (Price_Δ/100) × Sensitivity
EBITDA = Revenue × Margin + Project_EBITDA
```
Example: $8,420M × 12% + $0 = $1,010M

**STEP 5: Calculate Free Cash Flow**
```
NOPAT = (EBITDA - D&A) × (1 - Tax_Rate)
Gross_CF = NOPAT + D&A
FCF = Gross_CF - CapEx - Δ_WorkingCapital
```
Example: $1,010M → $839M → $463M - $378M - $12M = $73M FCF

**CONSOLIDATE:**
Sum all 4 segments → Annual FCF for this year
Repeat for years 2024-2033 → 10-year FCF stream

Example: Flat-Rolled $73M + Mini Mill $542M + USSE $234M + Tubular $45M = $894M total FCF

**DCF VALUATION:**

**USS Valuation (Blue):**
```
PV = Σ FCF/(1+WACC)^t + TV
WACC = 10.9%
```

**Nippon Valuation (Red):**
```
PV = Σ FCF/(1+WACC_IRP)^t + TV
WACC_IRP = 7.5% (via IRP adjustment)
```

---

## How the Model Works - Summary

### 1. Input Layer
User selects a scenario or customizes assumptions for:
- Steel price levels (via factors applied to benchmarks)
- Production volumes (by segment)
- Capital investment program
- Discount rates and terminal value assumptions

### 2. Segment Calculation (Nested Loops)
```python
for segment in [Flat-Rolled, Mini Mill, USSE, Tubular]:
    for year in range(2024, 2034):
        volume = calculate_volume(segment, year)
        price = calculate_price(segment, year)
        revenue = volume * price / 1000
        ebitda = revenue * margin + project_ebitda
        fcf = calculate_fcf(ebitda, segment)
```

### 3. Consolidation
Aggregate all segments across all years → 10-year FCF stream

### 4. Dual DCF Valuation
- **USS View**: Discount FCF at 10.9% WACC → Present value → Share price
  - Apply financing penalty if large projects enabled
- **Nippon View**: Discount FCF at 7.5% IRP-adjusted WACC → Present value → Share price
  - No financing penalty (Nippon has capacity)

### 5. Output & Visualization
Dashboard generates:
- Key metrics (share prices, WACC advantage, FCF totals)
- Charts (FCF over time, scenario comparison, sensitivity analysis)
- Tables (consolidated financials, project NPV, segment breakdown)
- Value bridge waterfall (USS → WACC advantage → Nippon → Gap to $55 offer)

---

## Key Formulas

### Price × Volume Revenue Model
```
Revenue = Volume × Price

where:
  Volume = Base_2023 × Volume_Factor × (1 + Growth)^years + Projects
  Price = Benchmark × Price_Factor × (1 + Premium) × (1 + Inflation)^years
```

### Interest Rate Parity (IRP) Adjustment
```
WACC_USD = (1 + WACC_JPY) × (1 + r_US) / (1 + r_JP) - 1

where:
  WACC_JPY = Nippon's weighted average cost of capital in yen
  r_US = US 10-year Treasury yield
  r_JP = Japan 10-year JGB yield
```

### DCF Valuation
```
EV = Σ(FCF_t / (1 + WACC)^t) + Terminal_Value

Terminal_Value = FCF_2033 × (1 + g) / (WACC - g)  [Gordon Growth]
              OR = EBITDA_2033 × Exit_Multiple       [Exit Multiple]

Share_Price = (EV + Cash + Investments - Debt - Pension - Leases) / Shares
```

---

## File Outputs

All three diagrams have been saved as high-resolution PNG files:

1. **model_architecture.png** - Complete model architecture (20" × 14")
2. **dashboard_flow.png** - Interactive dashboard user flow (18" × 12")
3. **calculation_flow.png** - Step-by-step calculation details (16" × 12")

These can be used for:
- Presentations
- Documentation
- Model walkthroughs
- Stakeholder communications
- Educational materials

---

## Running the Model

### Command Line (Python)
```bash
python price_volume_model.py
```
Outputs scenario comparison table to console.

### Interactive Dashboard (Streamlit)
```bash
streamlit run interactive_dashboard.py
```
Opens web browser with full interactive dashboard at http://localhost:8501

### Generating Visualizations
```bash
python model_visual.py        # Generate model architecture diagram
python dashboard_flow.py      # Generate dashboard flow diagram
python calculation_flow.py    # Generate calculation flow diagram
```

---

## Model Strengths

1. **Transparency**: Price × Volume methodology ties directly to observable steel market fundamentals
2. **Flexibility**: 5 pre-built scenarios + full customization via dashboard
3. **Dual Perspective**: Captures both USS standalone and Nippon acquirer views
4. **IRP Adjustment**: Properly accounts for cross-border cost of capital differences
5. **Segment Granularity**: Models 4 distinct businesses with different economics
6. **Capital Project Modeling**: Explicit treatment of $14B investment program
7. **Financing Realism**: USS standalone view accounts for debt/equity financing costs
8. **Interactive**: Real-time sensitivity analysis via web dashboard

---

*Created: January 2026*
*RAMBAS Team Capstone Project*
