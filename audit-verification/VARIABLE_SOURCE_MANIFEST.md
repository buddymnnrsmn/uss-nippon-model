# Variable & Source Document Manifest

**Last Updated:** 2026-02-06
**Purpose:** Complete inventory of every variable/assumption driving the USS/Nippon Steel DCF model, with supporting source documents.

---

## 1. WACC Inputs

**Source file:** `wacc-calculations/uss/inputs.json`

| Variable | Value | Source |
|----------|-------|--------|
| Risk-Free Rate | 3.88% | Federal Reserve H.15 (10Y Treasury, 12/29/2023) |
| Equity Beta | 1.45 | Consensus: Bloomberg 1.42, Yahoo 1.48, CapIQ 1.44 |
| Equity Risk Premium | 5.5% | Duff & Phelps 2023 Cost of Capital |
| Size Premium | 1.0% | Duff & Phelps Size Premium Study 2023 |
| Cost of Debt (Pre-Tax) | 7.2% | Weighted avg: 6.625% Notes ($650M), 6.125% Notes ($400M), Term Loan B ($800M) |
| Credit Rating | BB- / Ba3 | S&P / Moody's (stable outlook) |
| Tax Rate | 25% | US statutory: 21% federal + 4% state (PA/IN/AL blend) |
| Total Debt | $3,913M | USS 10-K / WRDS Compustat (verified vs CIQ $4,339M incl leases) |
| Cash | $2,547M | USS 10-K / WRDS Compustat (verified vs CIQ $2,948M) |
| Net Debt | $1,366M | Calculated (CIQ confirms $1,391M, within 1.8%) |
| Shares Outstanding | 225M | USS 10-K (CIQ: 223.7M, within 1%) |
| Share Price | $42.73 | NYSE 12/29/2023 |
| Analyst WACC (Barclays) | 11.5-13.5% | USS DEFM14A Fairness Opinion (filed 2024-03-12) |
| Analyst WACC (Goldman) | 11.5-13.0% | USS DEFM14A Fairness Opinion |
| Analyst WACC (JPM) | 10.0-12.0% | Equity Research |

---

## 2. Steel Price Benchmarks (through-cycle equilibrium)

**Source file:** `price_volume_model.py` lines 160-189

| Product | Price | Derivation | Source |
|---------|-------|------------|--------|
| HRC US | $738/ton | Avg(Pre-COVID $625, Post-Spike $850) | Bloomberg historical |
| CRC US | $994/ton | Avg(Pre-COVID $820, Post-Spike $1,130) | Bloomberg historical |
| Coated US | $1,113/ton | Avg(Pre-COVID $920, Post-Spike $1,266) | Bloomberg historical |
| HRC EU | $611/ton | Avg(Pre-COVID $512, Post-Spike $710) | Bloomberg historical |
| OCTG | $2,388/ton | Avg(Pre-COVID $1,350, Post-Spike $3,228) | Bloomberg historical |

---

## 3. Section 232 Tariff Parameters

**Source file:** `price_volume_model.py` lines 176-188

| Variable | Value | Source |
|----------|-------|--------|
| Current tariff rate | 25% | Section 232 (2018-present) |
| Model HRC uplift | 15% | Conservative between OLS 7% and empirical 18% |
| EU indirect share | 30% | Trade diversion analysis |
| OCTG share | 60% | Separate trade dynamics |
| MC tariff probability | Beta(8,2) ~80% | Expert judgment (political inertia) |
| MC tariff rate if changed | Tri(0%, 10%, 25%) | Expert judgment (trade policy) |

---

## 4. Segment Configurations

**Source file:** `price_volume_model.py` lines 1885-1977
**Primary source:** USS 2023 10-K (`references/uss_10k_2023.htm`)

| Variable | Flat-Rolled | Mini Mill | USSE | Tubular |
|----------|-------------|-----------|------|---------|
| Shipments (kt) | 8,706 | 2,424 | 3,899 | 478 |
| Volume Growth | -0.5% | +2.5% | 0.0% | +1.5% |
| Utilization | 71.2% | 89.5% | 87.9% | 63.1% |
| Max Utilization | 85% | 95% | 90% | 85% |
| Realized Price ($/ton) | $1,030 | $875 | $873 | $3,137 |
| Premium to Benchmark | +4.4% | -1.4% | +4.4% | +31.4% |
| EBITDA Margin | 12% | 17% | 9% | 26% |
| Margin Sensitivity/$100 | 2.0% | 2.5% | 2.0% | 1.0% |
| D&A % Revenue | 5.5% | 4.5% | 5.0% | 6.0% |
| Maint CapEx % | 4.5% | 3.4% | 2.7% | 4.0% |
| DSO / DIH / DPO | 28/55/60 | 22/40/70 | 30/50/65 | 35/60/55 |
| Margin Floor / Cap | 2% / 22% | 2% / 22% | 2% / 22% | 2% / 22% |

**Margin sensitivity validation:** Empirical regression (USS 10-K 2019-2023) shows FR 4.3%, MM 2.8%, USSE 3.8%, Tub 2.1% per $100 — model uses ~50% of empirical since empirical includes volume/leverage effects. See `audit-verification/data_collection/margin_sensitivity_analysis.csv`.

---

## 5. Capital Projects

**Source file:** `price_volume_model.py` lines 1979-2133
**Source doc:** `audit-verification/CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md`

| Variable | BR2 | Gary BF | Mon Valley | Greenfield | Mining | Fairfield |
|----------|-----|---------|------------|------------|--------|-----------|
| Capacity (kt) | 3,000 | 2,500 | 1,800 | 500 | 6,000 | 1,200 |
| Margin | 17% | 12% | 12% | 17% | 12% | 12% |
| Price ($/ton) | $900 | $950 | $950 | $900 | $150 | $900 |
| EBITDA ($M) | $459 | $285 | $205 | $77 | $108 | $130 |
| Total CapEx ($M) | $3,200 | $3,200 | $2,400 | $1,000 | $1,000 | $600 |
| Terminal Multiple | 7.0x | 5.0x | 5.0x | 7.0x | 5.0x | 6.0x |
| Maint $/ton | $20 | $40 | $35 | $20 | $8 | $25 |
| Maint % EBITDA | 13% | 35% | 31% | 13% | 44% | 23% |
| Enabled (base) | Yes | No | No | No | No | No |

**Sources by project:**
- **BR2** capacity/investment: Nippon investor presentation (Dec 2023)
- **Gary/Mon Valley/Fairfield** mechanisms: CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md
- **Greenfield:** NSA commitments filing
- **Mining:** USS 10-K iron ore operations
- **Terminal multiples:** WRDS peer EV/EBITDA (`references/steel_comps/wrds_peer_ev_ebitda.csv`) — EAF median 6.7x, Integrated median 4.8x
- **Maintenance capex:** Peer 10-K extraction (`audit-verification/data_collection/maintenance_capex_benchmarks.csv`) — NUE $119/ton, CLF $49/ton total

### Terminal Multiple Peer Basis

| Peer | Ticker | Technology | EV/EBITDA FY2023 | EV/EBITDA FY2022 | Average |
|------|--------|------------|------------------|------------------|---------|
| Nucor | NUE | EAF | 7.9x | 4.8x | 6.4x |
| Steel Dynamics | STLD | EAF | 7.8x | 4.5x | 6.2x |
| Commercial Metals | CMC | EAF | 5.8x | 5.2x | 5.5x |
| **EAF Median** | | | | | **6.7x** |
| Cleveland-Cliffs | CLF | Integrated | 5.2x | 3.8x | 4.5x |
| ArcelorMittal | MT | Integrated | 4.7x | 3.1x | 3.9x |
| POSCO | PKX | Integrated | 6.2x | 4.5x | 5.4x |
| Ternium | TX | Integrated | 3.3x | 2.8x | 3.1x |
| **Integrated Median** | | | | | **4.8x** |

---

## 6. Scenario Presets

**Source file:** `price_volume_model.py` lines 1296-1589

| Parameter | Severe | Downside | Base | Above Avg | Optimistic | Wall St | NSA |
|-----------|--------|----------|------|-----------|------------|---------|-----|
| HRC Factor | 0.75 | 0.90 | 1.00 | 0.95 | 1.25 | 1.24 | 1.05 |
| Price Growth | -2.0% | 0.0% | 1.0% | 1.0% | 1.5% | 0.0% | 1.0% |
| FR Vol Factor | 0.80 | 0.95 | 0.90 | 1.00 | 0.95 | 1.00 | 1.00 |
| USS WACC | 13.5% | 12.0% | 10.9% | 10.9% | 10.9% | 12.5% | 10.5% |
| Term Growth | 0.5% | 1.0% | 1.0% | 1.0% | 1.5% | 1.0% | 1.5% |
| Exit Multiple | 3.5x | 4.0x | 4.5x | 5.0x | 5.5x | 4.75x | 5.0x |
| Projects | None | BR2 | BR2 | BR2 | BR2 | BR2 | All 6 |
| Prob Weight | 25% | 30% | 30% | 10% | 5% | 0% | 0% |

**Source:** Wall Street Consensus uses Barclays WACC midpoint (12.5%) from DEFM14A. NSA uses all 6 projects per NSA commitments filing.

---

## 7. Monte Carlo Distributions (25 variables)

**Source file:** `monte_carlo/distributions_config.json`
**Calibration date:** 2026-02-05 | **Data cutoff:** 2023-12-18 | **Lookback:** 2019-01-01 to 2023-12-18

### Price Factors (Lognormal, μ=-σ²/2 for E[X]=1.0)

| Variable | σ | Source |
|----------|---|--------|
| HRC US Factor | 0.18 | Bloomberg through-cycle vol (excl COVID) |
| CRC US Factor | 0.16 | Bloomberg |
| Coated US Factor | 0.15 | Derived from CRC |
| HRC EU Factor | 0.15 | Bloomberg EU spot |
| OCTG Factor | 0.22 | Bloomberg tubular (higher oil/gas vol) |

### Volume Factors

| Variable | Distribution | Key Param | Source |
|----------|-------------|-----------|--------|
| FR Volume | Normal | σ=0.08 | Bloomberg capacity_us.csv (464 obs) |
| MM Volume | Normal | σ=0.06 | Derived (25% less volatile) |
| USSE Volume | Normal | σ=0.10 | European steel demand data |
| Tubular Volume | Triangular | 0.65/1.0/1.35 | Bloomberg rig_count.csv (107 obs) |

### Pricing & Market

| Variable | Distribution | Key Param | Source |
|----------|-------------|-----------|--------|
| Annual Price Growth | Normal | μ=1%, σ=1% | Historical steel price trends |
| USS WACC | Normal | μ=10.9%, σ=0.8% | Bloomberg ust_10y.csv + spread_bbb.csv |
| US 10-Year | Normal | μ=4.25%, σ=0.50% | Bloomberg ust_10y.csv |
| Japan RF Rate | Normal | μ=0.75%, σ=0.30% | JGB 10Y |
| Nippon ERP | Normal | μ=4.75%, σ=0.50% | Expert judgment |
| Terminal Growth | Triangular | -0.5%/1.0%/2.5% | Expert judgment |
| Exit Multiple | Triangular | 3.5x/4.5x/6.5x | Peer trading analysis |

### Execution & Operating

| Variable | Distribution | Key Param | Source |
|----------|-------------|-----------|--------|
| Gary Execution | Beta(8,3) | mean ~73% | M&A execution literature |
| Mon Valley Execution | Beta(9,2) | mean ~82% | M&A execution literature |
| Operating Synergy | Beta(8,3) | mean ~73% | M&A synergy studies |
| Revenue Synergy | Beta(3,4) | mean ~55% | M&A synergy studies |
| FR Margin Factor | Triangular | 0.85/1.0/1.15 | Bloomberg peer_fundamentals.csv |
| Working Capital | Normal | μ=1.0, σ=0.08 | Peer analysis |
| CapEx Intensity | Triangular | 0.8/1.0/1.3 | Peer capex analysis |

### Tariff

| Variable | Distribution | Key Param | Source |
|----------|-------------|-----------|--------|
| Tariff Probability | Beta(8,2) | mean ~80% | Expert judgment (policy risk) |
| Tariff Rate if Changed | Triangular | 0%/10%/25% | Expert judgment (trade policy) |

---

## 8. Correlations (return-based, Bloomberg 2019-2023)

**Source file:** `monte_carlo/distributions_config.json`

### Price Correlations

| Pair | ρ | Notes |
|------|---|-------|
| HRC↔CRC | 0.88 | Reduced from 0.97 (return-based vs level) |
| HRC↔OCTG | 0.20 | Reduced from 0.50 (weak oil correlation) |
| HRC↔EU | 0.60 | Reduced from 0.70 (trade integration) |
| HRC↔FR Vol | 0.35 | Reduced from 0.56 |
| CRC↔Coated | 0.88 | High product substitutability |
| OCTG↔Tub Vol | 0.30 | Reduced from 0.73 (oil/gas linkage) |

### Volume Correlations

| Pair | ρ | Notes |
|------|---|-------|
| FR Vol↔MM Vol | 0.70 | Shared steel demand |
| FR Vol↔USSE Vol | 0.50 | Global steel demand |
| HRC EU↔USSE Vol | 0.40 | European market linkage |

### Rate Correlations

| Pair | ρ | Notes |
|------|---|-------|
| US 10Y↔USS WACC | 0.60 | Rate pass-through |
| US 10Y↔Japan RF | 0.40 | Global rate correlation |
| Japan RF↔USS WACC | -0.30 | BOJ divergence |

### Execution Correlations

| Pair | ρ | Notes |
|------|---|-------|
| Gary Exec↔Mon Valley Exec | 0.60 | Common execution capability |

### Tariff Correlations

| Pair | ρ | Notes |
|------|---|-------|
| Tariff Prob↔HRC | -0.35 | Tariff removal → lower US prices |
| Tariff Prob↔CRC | -0.35 | Same mechanism |
| Tariff Prob↔Coated | -0.30 | Slightly less exposed |
| Tariff Prob↔OCTG | -0.20 | Separate trade dynamics |
| Tariff Prob↔FR Vol | -0.25 | Import competition |
| Tariff Prob↔MM Vol | -0.15 | Less exposed than integrated |
| Tariff Prob↔HRC EU | -0.10 | Trade diversion effects |

---

## 9. Equity Bridge

**Source file:** `wacc-calculations/uss/inputs.json`

| Item | Value | Source |
|------|-------|--------|
| Enterprise Value | (Model output) | Sum of discounted FCF + terminal value |
| Less: Net Debt | $1,366M | Total debt $3,913M - Cash $2,547M |
| Equity Value | EV - $1,366M | Calculated |
| Shares Outstanding | 225M | USS 10-K |
| Price Per Share | Equity / 225M | Calculated |

**Note:** Prior model had separate pension/lease/investment adjustments. These are now embedded in EBITDA projections per 2026-02-06 recalibration.

---

## Summary

**Total unique parameters:** ~100+ across 9 categories

**Primary source documents (9):**

| # | Document | Location | Status |
|---|----------|----------|--------|
| 1 | USS 2023 10-K | `references/uss_10k_2023.htm` | Acquired (SEC EDGAR) |
| 2 | USS DEFM14A Fairness Opinion | `audit-verification/evidence/uss_defm14a_2024.htm` | Acquired (SEC EDGAR) |
| 3 | Nippon Investor Presentation | `references/Deck - Nippon Steel...pdf` | Acquired |
| 4 | NSA Commitments Filing | Referenced in proxy | Acquired |
| 5 | Bloomberg Terminal Data | `data/bloomberg/` | Acquired (steel prices, peer multiples) |
| 6 | WRDS Compustat | `references/steel_comps/wrds_peer_ev_ebitda.csv` | Acquired |
| 7 | Federal Reserve H.15 | Web (Treasury yields) | Verified |
| 8 | Duff & Phelps 2023 | Publication (ERP, size premium) | Referenced |
| 9 | Peer 10-K Filings | `references/steel_comps/sec_filings/` | Acquired (9 companies) |

**Verification status:** All WACC inputs verified per `inputs.json` verification checklist (2026-02-03). Capital IQ balance sheet reconciliation confirms net debt within $25M (1.8%).
