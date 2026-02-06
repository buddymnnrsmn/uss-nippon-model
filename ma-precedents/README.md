# M&A Precedent Transactions Analysis

**Analysis Date:** February 2, 2026
**Purpose:** Independent verification of US steel industry M&A transactions (2018-2023) for Nippon-USS merger analysis

---

## Folder Structure

```
ma-precedents/
├── README.md                                      # This file
├── PRECEDENT_TRANSACTIONS_TABLE.md                # ⭐ Quick reference table + valuation
├── USS_INTRINSIC_VALUE_ANALYSIS.md                # ⭐ Full intrinsic value calculation
├── MERGER_PRECEDENT_TRANSACTIONS_SUMMARY.md       # Detailed transaction documentation
├── documentation/
│   └── MA_TRANSACTIONS_WRDS_VERIFICATION.md       # WRDS Compustat data verification
└── data/
    ├── wrds_AKS_data.csv                          # AK Steel financials 2017-2019
    ├── wrds_CLF_data.csv                          # Cleveland-Cliffs financials 2017-2021
    ├── wrds_X_data.csv                            # U.S. Steel financials 2017-2021
    └── wrds_STLD_data.csv                         # Steel Dynamics financials 2017-2021
```

---

## ⭐ Start Here

### New to this analysis? Read these first:

1. **PRECEDENT_TRANSACTIONS_TABLE.md** - Master table with all transactions + USS valuation reconciliation
2. **USS_INTRINSIC_VALUE_ANALYSIS.md** - Complete intrinsic value calculation with sensitivity tables

### For detailed research:

3. **MERGER_PRECEDENT_TRANSACTIONS_SUMMARY.md** - Full transaction documentation with sources
4. **documentation/MA_TRANSACTIONS_WRDS_VERIFICATION.md** - WRDS financial data verification

---

## Quick Reference

### Transactions Analyzed (5 Total)

| # | Transaction | Year | Deal Value | Multiple | Status |
|---|-------------|------|------------|----------|---------|
| 1 | Cleveland-Cliffs / AK Steel | 2020 | $3.0B EV | 5.6x | WRDS Verified ✓ |
| 2 | Cleveland-Cliffs / ArcelorMittal USA | 2020 | $3.3B EV | 6.0x | Acquirer data only |
| 3 | U.S. Steel / Big River Steel | 2019-2021 | $1.5B | N/D | Acquirer data only |
| 4 | Steel Dynamics / CSN Heartland | 2018 | $400M | N/D | Acquirer data only |
| 5 | Steel Dynamics / Kentucky Electric Steel | 2018 | $5M | N/A | Distressed asset |

---

## Key Files

### 1. MERGER_PRECEDENT_TRANSACTIONS_SUMMARY.md
**Primary transaction documentation**

Contains for each transaction:
- Basic deal information (acquirer, target, dates, values)
- Financial metrics (EBITDA multiples, target revenue/EBITDA)
- Deal structure (cash/stock, exchange ratios)
- Regulatory approval timeline (HSR filings, clearance dates)
- Strategic rationale
- **Source links** to SEC filings and press releases

**Best for:** Understanding deal terms, structures, and strategic context

---

### 2. documentation/MA_TRANSACTIONS_WRDS_VERIFICATION.md
**WRDS Compustat data verification**

Contains:
- Full financial statements for public companies (2017-2021)
- Verification of announced deal multiples
- Post-merger performance analysis
- Acquirer financial capacity assessment
- Comparative analysis across transactions
- Implications for Nippon-USS merger

**Best for:** Financial analysis, multiple verification, trend analysis

---

### 3. data/*.csv Files
**Raw WRDS Compustat data**

Each CSV contains annual fundamentals:
- Revenue, EBITDA, operating income, net income
- Total assets, liabilities, equity
- Debt metrics (long-term, current, total, net debt)
- Cash flow items (operating CF, capex)
- Market data (shares outstanding, stock price)
- Calculated ratios (EBITDA margin, debt/EBITDA, EV/EBITDA)

**Best for:** Building custom analyses, Excel integration, modeling

---

## Key Findings

### Valuation Multiples
- **Range:** 5.6x - 6.0x EBITDA for strategic steel M&A (2020)
- **Nippon-USS:** 7.6x falls within reasonable strategic premium range
- **Justification:** All-cash certainty, investment commitments, national security terms

### Regulatory Environment (2018-2020)
- **Speed:** 2-2.5 months to HSR early termination
- **Conditions:** No divestitures required
- **Concentration:** Cleveland-Cliffs reached ~50% market share with no DOJ challenge
- **Contrast:** Nippon-USS faced unprecedented national security review (2023-2025)

### Deal Structures
- **All-Stock:** Cleveland-Cliffs / AK Steel (preserve cash, tax-efficient)
- **Mixed:** Cleveland-Cliffs / ArcelorMittal USA (balance seller needs, buyer liquidity)
- **All-Cash:** U.S. Steel / Big River Steel, Steel Dynamics deals (strategic conviction)

### Post-Merger Performance
- **U.S. Steel:** EBITDA margin 4.4% (2019) → 26.2% (2021) after Big River acquisition
- **Cleveland-Cliffs:** Revenue $2.0B → $20.4B via two mega-deals in 10 months
- **Steel Dynamics:** Maintained low leverage (1.2x) while deploying $400M

---

## Data Sources

### Primary Sources (All Transactions)
✓ SEC EDGAR filings (8-K, S-4, 424B3, proxy statements)
✓ Company press releases (investor relations sites)
✓ FTC early termination notices
✓ Reputable financial news (WSJ, Bloomberg, Reuters)

### Verification Source (Public Companies Only)
✓ WRDS Compustat Fundamentals Annual (comp.funda)
✓ Retrieved via WRDS REST API
✓ Audited financial statements

---

## Data Limitations

### What's Available
✓ **AK Steel (AKS):** Full financials 2017-2019 (only public target)
✓ **All Acquirers:** Complete financials 2017-2021
✓ **Deal Terms:** From SEC filings and press releases
✓ **Regulatory Timelines:** HSR filing and clearance dates

### What's NOT Available (Need Capital IQ Pro)
❌ **Private Targets:** Big River Steel, ArcelorMittal USA, CSN Heartland standalone financials
❌ **M&A Database:** Transaction comps, deal multiples database
❌ **Synergy Tracking:** Realized vs. projected synergies
❌ **Detailed Pro Formas:** Management projections

**Note:** SEC merger proxy statements (Schedule 14A, S-4) disclose some target financials even for private companies - these have been cited where available.

---

## How to Use This Data

### For Academic/Professional Analysis
1. **Start with:** `MERGER_PRECEDENT_TRANSACTIONS_SUMMARY.md` for deal overview
2. **Deep dive:** `documentation/MA_TRANSACTIONS_WRDS_VERIFICATION.md` for financials
3. **Custom analysis:** Import `data/*.csv` files into Excel/Python/R
4. **Verify:** Cross-reference source links in documentation
5. **Supplement:** Use Capital IQ Pro for private target data

### For Nippon-USS Merger Analysis
- **Valuation Benchmarking:** Compare 7.6x vs. 5.6x-6.0x precedents
- **Deal Structure:** All-cash certainty vs. stock consideration risk
- **Regulatory Context:** 2-month clearance (2020) vs. 18-month review (2023-2025)
- **Strategic Rationale:** Technology + scale + vertical integration themes
- **Financial Capacity:** Zero leverage vs. leveraged acquisitions

---

## Updates & Maintenance

**Last Updated:** February 2, 2026
**Data Current Through:** 2021 fiscal year financials
**WRDS Cache:** 30-day refresh cycle

**To Refresh WRDS Data:**
```bash
cd /workspaces/claude-in-docker/FinancialModel
python local/wrds_loader.py --fetch-all --refresh
```

---

## Contact & Questions

For questions about this analysis:
- **Data Source Issues:** Check WRDS subscription and API token
- **Missing Transactions:** Additional deals can be researched using same methodology
- **Custom Analysis:** CSV files are ready for import into any analytical tool

---

**Analysis Prepared By:** Claude Code
**Methodology:** Web research + WRDS Compustat verification
**Quality Standard:** All data traceable to primary sources (SEC filings, WRDS)
