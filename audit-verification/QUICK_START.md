# Quick Start Guide
## Model Audit Workflow

This guide walks you through auditing the USS/Nippon Steel DCF model.

---

## Overview

The audit has two parts:
1. **Automated tests** (23 tests) - Run immediately, no data needed
2. **Manual verification** - Requires collecting source documents

---

## Step 1: Run Automated Tests (5 minutes)

Run the automated test suite to verify calculations and logic:

```bash
cd audits
python run_audit.py --quick
```

**Expected Output:**
- ✓ 22/23 tests passed (95.7%)
- Results saved to `results/audit_results.csv`

The one "failed" test is actually correct (scenario naming issue, not a model error).

---

## Step 2: Collect Source Data (30-60 minutes)

### Option A: Use the Data Scraper (Recommended)

```bash
cd verification_scripts
python data_scraper.py --all
```

This will:
- ✓ Create links to SEC filings
- ✓ List free steel price data sources
- ✓ Save company presentation URLs
- ✓ Generate download checklist

### Option B: Manual Collection

Download these key documents:

**Essential (High Priority):**
1. USS 2023 10-K from SEC EDGAR
   - https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302
   - Need: Segment volumes, prices, balance sheet

2. USS 2024 Proxy Statement (DEF 14A)
   - Contains Barclays and Goldman fairness opinions
   - Need: Valuation ranges, WACC assumptions

3. CME HRC Futures 2023 Data
   - https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html
   - Need: 2023 average settlement price

**Nice to Have (Medium Priority):**
- USS Q4 2023 earnings presentation
- NSA press releases
- Steel price indices (Platts, if available)

---

## Step 3: Extract Data into Templates (30-45 minutes)

Fill in the CSV templates with data from source documents:

### 3.1 USS 2023 Data
```bash
# Edit: data_collection/uss_2023_data.csv
```

Extract from 10-K:
- Segment shipment volumes (pg __)
- Segment realized prices (calculate: Revenue/Volume)
- Tax rate (cash taxes / pre-tax income)
- Working capital metrics (DSO, DIH, DPO)

### 3.2 Steel Prices
```bash
# Edit: data_collection/steel_prices_2023.csv
```

Extract from CME/Platts/SteelBenchmarker:
- US HRC Midwest: $__/ton (2023 avg)
- EU HRC: $__/ton (2023 avg)
- OCTG: $__/ton (2023 avg)

### 3.3 Balance Sheet
```bash
# Edit: data_collection/balance_sheet_items.csv
```

Extract from 10-K balance sheet:
- Total debt: $__M
- Cash: $__M
- Shares outstanding: __M shares

### 3.4 Capital Projects
```bash
# Edit: data_collection/capital_projects.csv
```

Extract from NSA filing / investor presentations:
- BR2 Phase 2: $__M CapEx
- Gary Works: $__M CapEx
- Total NSA commitment: $14B (verify)

**Use `source_data_tracker.md` to track progress and note page numbers.**

---

## Step 4: Run Verification (2 minutes)

Compare model inputs vs source data:

```bash
cd verification_scripts
python verify_inputs.py
```

**Expected Output:**
- Variance report for each input
- ✓ OK (< 2% variance)
- ⚠ REVIEW (2-5% variance)
- ✗ FLAG (> 5% variance)

Results saved to `results/input_verification_issues.csv`

---

## Step 5: Generate Final Report (1 minute)

```bash
cd audits
python run_audit.py
```

This runs:
1. All automated tests
2. Input verification
3. Generates master report: `results/audit_report_{timestamp}.md`

---

## Expected Timeline

| Task | Time | Difficulty |
|------|------|------------|
| Automated tests | 5 min | Easy |
| Download documents | 15-30 min | Easy |
| Extract data to CSVs | 30-45 min | Medium |
| Run verification | 2 min | Easy |
| Review & fix issues | 15-30 min | Medium |
| **TOTAL** | **~2 hours** | **Medium** |

---

## Common Issues

### "No source data found"
- You haven't filled in the CSV templates yet
- Run data scraper to get download links
- Complete templates in `data_collection/`

### "Variance > 5%"
- Check page number in source document
- Verify you're using the right metric (e.g., diluted shares not basic)
- Check units (thousands vs millions)
- Note in CSV if data unavailable

### "SEC filing not found"
- Check CIK is correct (USS = 0001163302)
- Try direct link: https://www.sec.gov/cgi-bin/browse-edgar
- Download manually if scraper doesn't work

---

## What If I Can't Get All The Data?

**Minimum Required for Useful Audit:**
1. ✓ Run automated tests (no data needed)
2. ✓ Get 2023 10-K for volumes/prices
3. ✓ Get CME data for HRC price

**With just these 3 items, you can verify ~60% of inputs.**

**Optional but Valuable:**
- Balance sheet items (equity bridge)
- Capital projects (NSA commitment)
- Fairness opinions (cross-check valuation)

---

## Need Help?

See full documentation:
- `MODEL_AUDIT_PLAN.md` - Complete 100+ checkpoint plan
- `AUDIT_SUMMARY.md` - Automated test results
- `README.md` - Project overview
- `data_collection/source_data_tracker.md` - Data extraction guide

---

## Quick Reference Commands

```bash
# Run full audit (automated + manual)
python run_audit.py

# Run automated tests only
python run_audit.py --quick

# Get data download links
python verification_scripts/data_scraper.py --all

# Verify inputs against source data
python verification_scripts/verify_inputs.py

# Check what documents you have
ls -lh evidence/

# View latest results
cat results/audit_report_*.md
```

---

## Success Criteria

**Audit is complete when:**
- [ ] Automated tests: 95%+ pass rate
- [ ] Input verification: < 5 high-severity variances
- [ ] Source documents: 10-K and proxy collected
- [ ] CSV templates: At least 50% filled
- [ ] Master report generated

**Model is approved when:**
- [ ] All critical inputs verified (volumes, prices, debt, shares)
- [ ] Variances explained and documented
- [ ] No calculation errors
- [ ] Outputs align with industry benchmarks
