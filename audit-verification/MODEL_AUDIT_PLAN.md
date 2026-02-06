# Financial Model Audit Plan
## USS / Nippon Steel Merger DCF Model

**Audit Objective:** Validate the accuracy, consistency, and reliability of the price x volume DCF model used for USS/Nippon Steel merger valuation.

**Scope:** Full model review including inputs, calculations, assumptions, and outputs.

---

## 1. INPUT VALIDATION & DATA INTEGRITY

### 1.1 Historical Data Verification
**Objective:** Verify all 2023 base data matches source documents

| Test ID | Test Description | Source Document | Pass/Fail | Notes |
|---------|------------------|-----------------|-----------|-------|
| IV-01 | Verify 2023 segment volumes match 10-K | USS 2023 10-K pg XX | [ ] | |
| IV-02 | Verify 2023 realized prices match 10-K | USS 2023 10-K pg XX | [ ] | |
| IV-03 | Verify steel price benchmarks vs market data | S&P Global Platts, 2023 avg | [ ] | |
| IV-04 | Verify balance sheet items (debt, cash, pension) | USS 2023 10-K pg XX | [ ] | |
| IV-05 | Verify shares outstanding | USS 2023 10-K pg XX | [ ] | |
| IV-06 | Verify effective tax rate 16.9% | USS 2023 10-K cash tax calc | [ ] | |

**Expected Result:** All inputs within ±2% of source documents

### 1.2 Capital Project Data Validation
**Objective:** Verify project CapEx and EBITDA schedules match disclosed commitments

| Test ID | Test Description | Source | Pass/Fail | Notes |
|---------|------------------|--------|-----------|-------|
| IV-07 | BR2 Mini Mill total CapEx $3B | USS investor presentations | [ ] | |
| IV-08 | Gary Works BF $3.1B matches NSA commitment | NSA filing | [ ] | |
| IV-09 | Total NSA commitment = $14B | NSA filing | [ ] | |
| IV-10 | BR2 volume addition 3M tons matches capacity | Company disclosure | [ ] | |

**Expected Result:** All project data matches public disclosures within ±5%

### 1.3 Premium Calibration Check
**Objective:** Verify segment price premiums are correctly calibrated

| Test ID | Test Description | Formula | Expected | Actual | Pass/Fail |
|---------|------------------|---------|----------|--------|-----------|
| IV-11 | Flat-Rolled premium: $1,030 vs $680 HRC | (1030/680) - 1 | 51.5% | [ ] | [ ] |
| IV-12 | Mini Mill premium: $875 vs $680 HRC | (875/680) - 1 | 28.7% | [ ] | [ ] |
| IV-13 | USSE premium: $873 vs $620 EU HRC | (873/620) - 1 | 40.8% | [ ] | [ ] |
| IV-14 | Tubular premium: $3,137 vs $2,800 OCTG | (3137/2800) - 1 | 12.0% | [ ] | [ ] |

**Expected Result:** All premiums match actual 2023 realized prices

---

## 2. CALCULATION VERIFICATION

### 2.1 Formula Accuracy Tests
**Objective:** Verify all formulas calculate correctly

| Test ID | Test Description | Method | Pass/Fail | Notes |
|---------|------------------|--------|-----------|-------|
| CV-01 | Revenue = Volume × Price | Manual calc 2024 | [ ] | |
| CV-02 | EBITDA margin formula accuracy | Test with known price change | [ ] | |
| CV-03 | NOPAT = EBIT × (1 - 16.9%) | Spot check 3 years | [ ] | |
| CV-04 | Working capital calculation | Verify DSO/DIH/DPO formula | [ ] | |
| CV-05 | FCF = Gross CF - CapEx + ΔWC | Trace full waterfall | [ ] | |
| CV-06 | DCF discount factors | Manual PV calc for year 5 | [ ] | |
| CV-07 | Gordon Growth terminal value | Verify g < WACC check | [ ] | |
| CV-08 | Exit multiple terminal value | Cross-check vs Gordon | [ ] | |
| CV-09 | Equity bridge math | Manual reconstruction | [ ] | |
| CV-10 | IRP WACC conversion | Independent calculation | [ ] | |

**Expected Result:** All formulas produce mathematically correct results

### 2.2 Consolidation Integrity
**Objective:** Ensure segment-to-consolidated aggregation is correct

| Test ID | Test Description | Pass/Fail | Notes |
|---------|------------------|-----------|-------|
| CV-11 | Sum of segment revenues = consolidated revenue (all years) | [ ] | |
| CV-12 | Sum of segment EBITDA = consolidated EBITDA (all years) | [ ] | |
| CV-13 | Sum of segment CapEx = consolidated CapEx (all years) | [ ] | |
| CV-14 | Sum of segment FCF = consolidated FCF (all years) | [ ] | |
| CV-15 | Weighted avg volume/price matches consolidated | [ ] | |

**Expected Result:** Perfect consolidation (zero rounding errors)

### 2.3 Year-over-Year Continuity
**Objective:** Check for unexplained jumps or breaks in trends

| Test ID | Test Description | Threshold | Pass/Fail | Notes |
|---------|------------------|-----------|-----------|-------|
| CV-16 | Revenue growth YoY consistency | No >20% jumps | [ ] | |
| CV-17 | Volume changes align with growth assumptions | Within ±3% | [ ] | |
| CV-18 | Price inflation consistency | Matches annual growth rate | [ ] | |
| CV-19 | Margin changes explainable by price | Per sensitivity param | [ ] | |
| CV-20 | Working capital Δ reasonable | No >$1B unexplained swings | [ ] | |

**Expected Result:** Smooth transitions except where projects ramp

---

## 3. LOGIC & REASONABLENESS CHECKS

### 3.1 Economic Logic Tests
**Objective:** Verify model follows economic principles

| Test ID | Test Description | Expected Behavior | Pass/Fail | Notes |
|---------|------------------|-------------------|-----------|-------|
| LC-01 | Higher steel prices → higher margins | Positive correlation | [ ] | |
| LC-02 | Higher WACC → lower valuation | Negative correlation | [ ] | |
| LC-03 | Volume × price changes → revenue changes | Linear relationship | [ ] | |
| LC-04 | Higher CapEx → lower FCF (same year) | Negative impact | [ ] | |
| LC-05 | Project EBITDA lags project CapEx | Timing makes sense | [ ] | |
| LC-06 | Terminal growth < WACC | No perpetual explosion | [ ] | |
| LC-07 | Mini Mill margins > Flat-Rolled | Industry convention | [ ] | |
| LC-08 | OCTG prices > HRC prices | Tubular premium | [ ] | |

**Expected Result:** All economic relationships behave as expected

### 3.2 Industry Benchmarking
**Objective:** Compare outputs to industry standards

| Test ID | Metric | Model Output | Industry Range | Pass/Fail | Notes |
|---------|--------|--------------|----------------|-----------|-------|
| LC-09 | EBITDA margin (avg) | 15.5% | 10-20% for steel | [ ] | |
| LC-10 | FCF/EBITDA conversion | 52% | 40-60% typical | [ ] | |
| LC-11 | CapEx as % revenue | 5.3% | 4-8% for steel | [ ] | |
| LC-12 | D&A as % revenue | 5.1% | 4-6% for steel | [ ] | |
| LC-13 | EV/EBITDA multiple | Check calc | 4-6x for steel | [ ] | |
| LC-14 | P/E multiple (implied) | Check calc | 8-12x for steel | [ ] | |

**Expected Result:** All metrics within reasonable industry ranges

### 3.3 Cross-Scenario Consistency
**Objective:** Verify scenario differences make logical sense

| Test ID | Test Description | Pass/Fail | Notes |
|---------|------------------|-----------|-------|
| LC-15 | Conservative < Base < Management (valuations) | [ ] | |
| LC-16 | Higher price scenarios → higher valuations | [ ] | |
| LC-17 | More projects → higher CapEx | [ ] | |
| LC-18 | NSA scenario has all 6 projects enabled | [ ] | |
| LC-19 | Execution factor reduces non-BR2 benefits | [ ] | |

**Expected Result:** Scenarios rank in sensible order

---

## 4. SENSITIVITY & STRESS TESTING

### 4.1 Single-Variable Sensitivity
**Objective:** Test model behavior to key input changes

| Test ID | Variable | Test Range | Expected Impact | Pass/Fail | Notes |
|---------|----------|------------|-----------------|-----------|-------|
| ST-01 | HRC price | $500-$900/ton | ~$2-3/share per $100 | [ ] | |
| ST-02 | Volume (all segments) | -20% to +20% | Linear to revenue/FCF | [ ] | |
| ST-03 | USS WACC | 8% to 14% | Inverse to valuation | [ ] | |
| ST-04 | Terminal growth | 0% to 3% | ~$5-10/share impact | [ ] | |
| ST-05 | Exit multiple | 3x to 7x | ~$3-5/share per 1x | [ ] | |
| ST-06 | EBITDA margin | -200bps to +200bps | Major FCF impact | [ ] | |
| ST-07 | CapEx intensity | -50% to +50% | Direct FCF impact | [ ] | |

**Expected Result:** Sensitivities are smooth, monotonic, and proportional

### 4.2 Multi-Variable Stress Tests
**Objective:** Test extreme scenarios

| Test ID | Scenario | Inputs | Expected Result | Pass/Fail | Notes |
|---------|----------|--------|-----------------|-----------|-------|
| ST-08 | 2008-style downturn | Price -40%, Volume -20%, WACC +300bps | Valuation < $30/sh | [ ] | |
| ST-09 | Perfect storm | Conservative price + vol + max WACC | Valuation < offer | [ ] | |
| ST-10 | Boom scenario | Price +30%, Volume +15%, low WACC | Valuation > $100/sh | [ ] | |
| ST-11 | All projects fail | Execution factor = 0% | Back to base case | [ ] | |
| ST-12 | Infinite WACC test | WACC = 99% | Valuation → 0 | [ ] | |
| ST-13 | Zero growth test | All growth = 0% | Stable volumes | [ ] | |

**Expected Result:** Model handles extremes without errors

### 4.3 Boundary Testing
**Objective:** Test model at extreme parameter values

| Test ID | Boundary | Test Value | Expected Behavior | Pass/Fail | Notes |
|---------|----------|------------|-------------------|-----------|-------|
| ST-14 | WACC = terminal growth | 1.0% both | Error/warning | [ ] | |
| ST-15 | WACC < terminal growth | Invalid case | Error/warning | [ ] | |
| ST-16 | Negative volumes | -100 tons | Error/warning | [ ] | |
| ST-17 | Zero price | $0/ton | Revenue = 0 | [ ] | |
| ST-18 | Negative prices | -$100/ton | Error/warning | [ ] | |
| ST-19 | 100% margin | Unrealistic | Caps at 30% | [ ] | |
| ST-20 | Negative margin | Price crash | Floors at 2% | [ ] | |

**Expected Result:** Model has appropriate guards/limits

---

## 5. FINANCING IMPACT VALIDATION

### 5.1 USS Standalone Financing Logic
**Objective:** Verify financing impact calculations are reasonable

| Test ID | Test Description | Pass/Fail | Notes |
|---------|------------------|-----------|-------|
| FI-01 | BR2-only scenario has zero financing impact | [ ] | |
| FI-02 | NSA scenario triggers financing gap calculation | [ ] | |
| FI-03 | Financing gap = cumulative negative FCF | [ ] | |
| FI-04 | Debt/equity split = 50/50 per assumptions | [ ] | |
| FI-05 | Interest expense = avg debt × 7.5% × (1-25% tax) | [ ] | |
| FI-06 | Equity dilution math correct (discount + costs) | [ ] | |
| FI-07 | WACC adjustment = leverage increase × 50bps/turn | [ ] | |
| FI-08 | Nippon valuation excludes financing impact | [ ] | |

**Expected Result:** Financing impact only applies to USS standalone with projects

### 5.2 Financing Impact Reasonableness
**Objective:** Check if financing penalty is realistic

| Test ID | Metric | Expected Range | Actual | Pass/Fail |
|---------|--------|----------------|--------|-----------|
| FI-09 | Debt-to-EBITDA ratio | < 4.0x | [ ] | [ ] |
| FI-10 | Interest coverage | > 3.0x | [ ] | [ ] |
| FI-11 | Dilution % (NSA scenario) | 10-25% | [ ] | [ ] |
| FI-12 | WACC increase | 50-150bps | [ ] | [ ] |

**Expected Result:** Financing terms are realistic for USS credit profile

---

## 6. DOCUMENTATION & TRANSPARENCY

### 6.1 Code Quality Review
**Objective:** Assess model maintainability and auditability

| Test ID | Criterion | Pass/Fail | Notes |
|---------|-----------|-----------|-------|
| DT-01 | All formulas clearly commented | [ ] | |
| DT-02 | Variable names are descriptive | [ ] | |
| DT-03 | No "magic numbers" - all constants defined | [ ] | |
| DT-04 | Assumptions documented with sources | [ ] | |
| DT-05 | Calculation flow is logical and traceable | [ ] | |
| DT-06 | Error handling for invalid inputs | [ ] | |

**Expected Result:** Code is readable and maintainable

### 6.2 Output Validation
**Objective:** Verify dashboard displays match underlying calculations

| Test ID | Test Description | Pass/Fail | Notes |
|---------|------------------|-----------|-------|
| DT-07 | Dashboard FCF = model consolidated FCF | [ ] | |
| DT-08 | Dashboard valuation = DCF output | [ ] | |
| DT-09 | Segment charts sum to consolidated | [ ] | |
| DT-10 | Scenario comparison table matches individual runs | [ ] | |
| DT-11 | No rounding errors in displayed metrics | [ ] | |

**Expected Result:** UI displays exactly match model outputs

---

## 7. CRITICAL ASSUMPTION REVIEW

### 7.1 Key Assumptions to Challenge
**Objective:** Identify and document critical model assumptions

| Assumption | Current Value | Risk Level | Sensitivity | Review Notes |
|------------|---------------|------------|-------------|--------------|
| Cash tax rate stays at 16.9% | 16.9% | Medium | Test 20-25% | [ ] |
| BR2 delivers 3M tons by 2028 | 3M tons | Medium | Test 2M-4M range | [ ] |
| Margin sensitivity to price | 4-5%/$100 | High | Test 2-8% range | [ ] |
| Terminal growth < GDP | 1.0% | Low | Test 0-2% | [ ] |
| Mini Mill share gains continue | +2%/yr | Medium | Test 0-4% | [ ] |
| No major plant closures (base) | Assumption | High | Test closure scenario | [ ] |
| Working capital stays stable | DSO/DIH/DPO | Low | Stress by ±20% | [ ] |
| Project execution on time/budget | 100% | High | Test 50-75% haircut | [ ] |

**Expected Result:** Document all critical assumptions and alternatives tested

---

## 8. EXTERNAL VALIDATION

### 8.1 Benchmarking vs Third-Party Valuations
**Objective:** Compare model to analyst/market estimates

| Source | Valuation Range | Model Output | Variance | Notes |
|--------|-----------------|--------------|----------|-------|
| Barclays fairness opinion | $39-52/share | [ ] Base Case | [ ] | |
| Goldman fairness opinion | $41-54/share | [ ] Base Case | [ ] | |
| Wall Street consensus (pre-deal) | $45-50/share | [ ] Base Case | [ ] | |
| Nippon offer | $55/share | [ ] Nippon view | [ ] | |

**Expected Result:** Model outputs within ±20% of third-party estimates

### 8.2 Reverse Engineering Key Metrics
**Objective:** Back-solve to validate reasonableness

| Test ID | Test Description | Pass/Fail | Notes |
|---------|------------------|-----------|-------|
| EV-01 | What steel price implies $55/share? | [ ] | Should be realistic |
| EV-02 | What WACC implies $55/share for USS? | [ ] | Should be ~8-9% |
| EV-03 | What EBITDA implies $55 at 5x multiple? | [ ] | Check vs mgmt guidance |
| EV-04 | What FCF growth implies terminal value? | [ ] | Should be achievable |

**Expected Result:** Implied assumptions are all within realistic ranges

---

## 9. ERROR TESTING

### 9.1 Data Entry Error Simulation
**Objective:** Test model resilience to input errors

| Test ID | Error Introduced | Expected Behavior | Pass/Fail | Notes |
|---------|------------------|-------------------|-----------|-------|
| ET-01 | Negative volume input | Error/warning | [ ] | |
| ET-02 | Volume in millions instead of thousands | Unrealistic output caught | [ ] | |
| ET-03 | Price in cents instead of dollars | Unrealistic output caught | [ ] | |
| ET-04 | WACC entered as 10.9 instead of 0.109 | Error/validation | [ ] | |
| ET-05 | Missing project CapEx year | Handles gracefully | [ ] | |

**Expected Result:** Model catches or flags obvious errors

---

## 10. PEER REVIEW CHECKLIST

### 10.1 Independent Model Review
**Objective:** Have second analyst review entire model

| Review Area | Reviewer Sign-off | Date | Issues Found |
|-------------|-------------------|------|--------------|
| Input data accuracy | [ ] | | |
| Formula correctness | [ ] | | |
| Scenario logic | [ ] | | |
| DCF mechanics | [ ] | | |
| Dashboard functionality | [ ] | | |
| Documentation quality | [ ] | | |

### 10.2 Executive Summary
**Reviewer Name:** _______________
**Date:** _______________

**Overall Assessment:** [ ] Pass  [ ] Pass with comments  [ ] Fail

**Critical Issues Identified:**
1.
2.
3.

**Recommended Improvements:**
1.
2.
3.

**Sign-off:** _______________

---

## AUDIT COMPLETION CHECKLIST

- [ ] All 100+ tests executed
- [ ] Issues log maintained with resolutions
- [ ] Model performs as expected under stress
- [ ] Calculations verified against independent source
- [ ] Assumptions documented and justified
- [ ] Peer review completed
- [ ] Executive summary drafted
- [ ] Model approved for use / flagged for revision

**Date Completed:** _______________
**Lead Auditor:** _______________
**Final Status:** _______________
