# Source Data Collection Tracker

## Instructions
1. Download each source document listed below
2. Save to `../evidence/` folder
3. Extract relevant data into corresponding CSV templates
4. Mark status as "Complete" when done
5. Note page numbers for audit trail

---

## USS 2023 10-K Filing

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Download URL:** https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K

**Data to Extract:**

| Item | Template File | 10-K Page | Status | Notes |
|------|--------------|-----------|--------|-------|
| Segment shipment volumes (2023) | uss_2023_data.csv | Pg ___ | [ ] | Flat-Rolled, Mini Mill, USSE, Tubular |
| Segment realized prices (2023) | uss_2023_data.csv | Pg ___ | [ ] | Revenue/volume by segment |
| Total debt | balance_sheet_items.csv | Pg ___ | [ ] | Long-term + short-term |
| Cash & equivalents | balance_sheet_items.csv | Pg ___ | [ ] | Balance sheet |
| Pension liability | balance_sheet_items.csv | Pg ___ | [ ] | Off-balance sheet |
| Operating leases | balance_sheet_items.csv | Pg ___ | [ ] | Note disclosures |
| Equity investments | balance_sheet_items.csv | Pg ___ | [ ] | Other assets |
| Shares outstanding | balance_sheet_items.csv | Pg ___ | [ ] | Weighted average diluted |
| Effective tax rate | uss_2023_data.csv | Pg ___ | [ ] | Cash taxes paid / pre-tax income |
| D&A expense by segment | uss_2023_data.csv | Pg ___ | [ ] | Cash flow statement |
| CapEx by segment | uss_2023_data.csv | Pg ___ | [ ] | Cash flow statement |

**File Path:** `../evidence/USS_10K_2023.pdf`

---

## Steel Price Benchmarks (2023)

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Sources:**
- S&P Global Platts: https://www.spglobal.com/platts (subscription required)
- CME Group HRC Futures: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.html
- SteelBenchmarker: http://www.steelbenchmarker.com/ (free data available)

**Data to Extract:**

| Benchmark | Template File | Source | 2023 Avg | Status |
|-----------|--------------|--------|----------|--------|
| US HRC Midwest ($/ton) | steel_prices_2023.csv | Platts | ___ | [ ] |
| US CRC Midwest ($/ton) | steel_prices_2023.csv | Platts | ___ | [ ] |
| US Coated Midwest ($/ton) | steel_prices_2023.csv | Platts | ___ | [ ] |
| EU HRC ($/ton) | steel_prices_2023.csv | Platts | ___ | [ ] |
| OCTG ($/ton) | steel_prices_2023.csv | Industry reports | ___ | [ ] |

**File Paths:**
- `../evidence/Platts_Steel_Prices_2023.csv`
- `../evidence/CME_HRC_Futures_2023.csv`

---

## NSA Capital Projects Filing

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Download URL:** [Insert CFIUS/regulatory filing URL when available]

**Alternative Sources:**
- USS investor presentations (https://www.ussteel.com/investors)
- Nippon Steel press releases
- News articles (WSJ, Bloomberg, etc.)

**Data to Extract:**

| Project | Template File | Source | CapEx ($M) | EBITDA Impact | Status |
|---------|--------------|--------|------------|---------------|--------|
| BR2 Mini Mill Phase 2 | capital_projects.csv | ___ | ___ | ___ | [ ] |
| Gary Works BF Modernization | capital_projects.csv | ___ | ___ | ___ | [ ] |
| Mon Valley Hot Strip Mill | capital_projects.csv | ___ | ___ | ___ | [ ] |
| Greenfield Mini Mill | capital_projects.csv | ___ | ___ | ___ | [ ] |
| Mining Investment (Keetac/Minntac) | capital_projects.csv | ___ | ___ | ___ | [ ] |
| Fairfield Works Tubular | capital_projects.csv | ___ | ___ | ___ | [ ] |

**Key Metrics to Verify:**
- Total NSA commitment: $14.0B (confirm)
- Incremental EBITDA target: $2.5B (confirm)
- Timeline: Through 2035 (confirm)

**File Paths:**
- `../evidence/NSA_Agreement_2023.pdf`
- `../evidence/USS_Investor_Presentation_Q4_2023.pdf`

---

## Barclays Fairness Opinion

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Source:** Proxy statement filed with SEC (14A filing)

**Data to Extract:**

| Metric | Value Range | Page | Status |
|--------|-------------|------|--------|
| DCF valuation range ($/share) | $___-$___ | Pg ___ | [ ] |
| WACC range used | ___%-___% | Pg ___ | [ ] |
| Terminal growth assumption | ___% | Pg ___ | [ ] |
| Exit multiple range | ___x-___x | Pg ___ | [ ] |
| Management EBITDA projections (2024-2029) | See table | Pg ___ | [ ] |
| Comparable company multiples | See table | Pg ___ | [ ] |

**File Path:** `../evidence/Barclays_Fairness_Opinion.pdf`

---

## Goldman Sachs Fairness Opinion

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Source:** Proxy statement filed with SEC (14A filing)

**Data to Extract:**

| Metric | Value Range | Page | Status |
|--------|-------------|------|--------|
| DCF valuation range ($/share) | $___-$___ | Pg ___ | [ ] |
| WACC range used | ___%-___% | Pg ___ | [ ] |
| Management projections used | See table | Pg ___ | [ ] |
| Precedent transactions analysis | See table | Pg ___ | [ ] |

**File Path:** `../evidence/Goldman_Fairness_Opinion.pdf`

---

## Management Projections (Dec 2023)

**Status:** [ ] Not Started | [ ] In Progress | [ ] Complete

**Source:** Included in fairness opinions or investor presentations

**Data to Extract:**

| Year | Revenue ($M) | EBITDA ($M) | CapEx ($M) | FCF ($M) | Source | Status |
|------|-------------|-------------|------------|----------|--------|--------|
| 2024 | ___ | ___ | ___ | ___ | ___ | [ ] |
| 2025 | ___ | ___ | ___ | ___ | ___ | [ ] |
| 2026 | ___ | ___ | ___ | ___ | ___ | [ ] |
| 2027 | ___ | ___ | ___ | ___ | ___ | [ ] |
| 2028 | ___ | ___ | ___ | ___ | ___ | [ ] |

**Key Assumptions:**
- HRC price assumption: $___/ton
- Volume trajectory: ___
- Plant closures assumed: ___

---

## Completion Checklist

- [ ] All source documents downloaded
- [ ] All CSV templates populated
- [ ] Page numbers noted for audit trail
- [ ] Data anomalies flagged
- [ ] Ready for automated verification

**Date Completed:** _______________
**Completed By:** _______________

---

## Notes & Anomalies

Use this section to note any issues encountered during data collection:

1.
2.
3.

