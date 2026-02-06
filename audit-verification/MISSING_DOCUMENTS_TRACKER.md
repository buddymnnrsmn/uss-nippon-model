# Missing Documents Tracker

**Last updated:** 2026-02-06
**Purpose:** Documents the human team needs to locate, create, or export to complete the model's audit trail.

---

## Priority 1: Critical for Audit Trail

### 1. USS 2023 10-K (Full SEC Filing with Footnotes)
- **What we have:** Summary financial statements via S&P Capital IQ (`USS Financial Statements.xlsx`)
- **What we need:** Full 10-K filing with:
  - Debt maturity schedule (Note: Long-term Debt)
  - Pension footnote (PBO, plan assets, unfunded status)
  - Operating lease detail (ROU assets, lease liabilities by year)
  - Share count reconciliation (basic vs diluted, treasury stock method)
- **Why:** Equity bridge uses $3,913M debt and $2,547M cash from WACC inputs.json. Need footnotes to verify these match the 10-K exactly.
- **Where to get:** SEC EDGAR ([USS 10-K](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K&dateb=&owner=include&count=10))
- **Save to:** `references/uss_10k_2023.pdf` or `references/uss_10k_2023.htm`

### 2. Capital Projects EBITDA Impact Analysis
- **What we have:** Parameters embedded in code comments (price_volume_model.py lines 1979-2133)
- **What we need:** Formal source document with:
  - Project capacity derivations (3,000 kt BR2, 2,500 kt Gary, etc.)
  - EBITDA margin basis (why 17% EAF, 12% integrated)
  - Project mechanism breakdowns (70/30 Gary, 80/20 Mon Valley, etc.)
  - CapEx schedule sources (NSA commitment vs Nippon presentation)
- **Why:** Cited as source for all 6 capital projects but doesn't exist as a file
- **Where to get:** Create from Nippon investor presentations + NSA filing + USS capital plan disclosures
- **Save to:** `audit-verification/CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md`

### 3. USS Merger Proxy (DEFM14A) — Fairness Opinion Section
- **What we have:** WACC range references (Barclays 11.5-13.5%, Goldman 11.5-13.0%)
- **What we need:** Barclays/Goldman DCF assumptions from the fairness opinion:
  - Discount rates used
  - Terminal growth rates
  - Projected EBITDA path
  - Per-share value ranges
- **Why:** Primary benchmark for validating our DCF methodology
- **Where to get:** SEC EDGAR — USS DEFM14A filed ~March 2024 (Annex B/C)
- **Save to:** `references/uss_defm14a_fairness_opinion.pdf`

---

## Priority 2: Important for Model Validation

### 4. Nippon Steel Investor Presentation (Dec 2023)
- **What we have:** BR2 capacity (3,000 kt), total investment commitment ($14B/5yr)
- **What we need:** Full presentation with:
  - Detailed capex breakdown by project and year
  - EBITDA improvement targets by segment
  - Synergy estimates and timeline
  - Technology strategy (EAF vs BF)
- **Why:** Primary source for BR2 Mini Mill parameters and NSA commitments
- **Where to get:** Nippon Steel IR website or SEC filing exhibits
- **Save to:** `nippon-analysis/nippon_investor_presentation_dec2023.pdf`

### 5. WRDS Peer Fundamentals Export (Terminal Multiples)
- **What we have:** Peer multiples cited in code (STLD 7.8x, NUE 7.9x, CMC 5.8x, MT 4.7x, etc.)
- **What we need:** Saved WRDS Compustat query showing:
  - Peer set: NUE, STLD, CMC, CLF, MT, PKX, TX, GGB
  - Fields: EV, EBITDA, EV/EBITDA for FY2022-2023
  - Selection criteria (why these peers, why this time period)
- **Why:** Terminal multiples (5.0x-7.0x) are critical valuation drivers; need audit trail
- **Where to get:** WRDS Compustat query (use `wrds-data-fetch` skill)
- **Save to:** `references/steel_comps/wrds_peer_ev_ebitda.csv`

### 6. Maintenance CapEx Benchmarks
- **What we have:** Per-ton assumptions ($20 EAF, $40 BF, $35 HSM, $8 Mining, $25 Tubular)
- **What we need:** Industry benchmarks from:
  - AIST (Association for Iron & Steel Technology) reports
  - Peer company capex disclosures (NUE, STLD sustaining capex)
  - Steel industry consultant reports
- **Why:** Maintenance capex directly reduces project NPV; BF maintenance ($40/ton) is 3x EAF ($20/ton)
- **Where to get:** AIST publications, peer 10-K capex footnotes, or Wood Mackenzie/CRU
- **Save to:** `audit-verification/data_collection/maintenance_capex_benchmarks.csv`

---

## Priority 3: Nice to Have

### 7. S&P Capital IQ Full Export (USS)
- **What we have:** `USS Financial Statements.xlsx` (referenced in balance_sheet_items.csv)
- **What we need:** Clarification on Capital IQ definitions:
  - "Total Debt" ($3,138M) — does this include current maturities?
  - "Debt Equivalent of Unfunded PBO" ($735M) — is this net or gross?
  - "Cash & Equivalents" ($755M) — does this include restricted cash?
- **Why:** Reconcile discrepancies between Capital IQ and WACC inputs.json figures
- **Where to get:** S&P Capital IQ terminal export with definition footnotes
- **Save to:** `references/uss_capital_iq_export_2023.xlsx`

### 8. Margin Sensitivity Academic/Industry Source
- **What we have:** Calibrated values (2-2.5% EBITDA margin per $100 price change)
- **What we need:** Empirical basis from:
  - Historical USS segment data (price vs margin regression)
  - Peer operating leverage analysis
  - Steel industry cost curve studies
- **Why:** Margin sensitivity is the key amplifier in the DCF; currently "calibrated" without external source
- **Where to get:** USS 10-K segment data (5-year history), or CRU cost curve
- **Save to:** `audit-verification/data_collection/margin_sensitivity_analysis.xlsx`

---

## Summary

| # | Document | Priority | Status | Impact |
|---|----------|----------|--------|--------|
| 1 | USS 10-K (full with footnotes) | Critical | Missing | Equity bridge verification |
| 2 | Capital Projects EBITDA Analysis | Critical | Missing (parameters in code only) | All project NPVs |
| 3 | USS DEFM14A Fairness Opinion | Critical | Missing | DCF methodology benchmark |
| 4 | Nippon Investor Presentation | Important | Missing | BR2 and NSA parameters |
| 5 | WRDS Peer EV/EBITDA Export | Important | Missing (values cited, query not saved) | Terminal multiples |
| 6 | Maintenance CapEx Benchmarks | Important | Missing | Project FCF calculations |
| 7 | S&P Capital IQ Definitions | Nice to have | Missing | Reconcile audit discrepancies |
| 8 | Margin Sensitivity Source | Nice to have | Missing | Operating leverage calibration |

**Total: 8 documents needed. 3 critical, 3 important, 2 nice-to-have.**
