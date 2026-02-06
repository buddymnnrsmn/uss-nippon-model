# Data Sources Summary
## Audit Data Collection - Ready to Download

**Generated:** January 21, 2026
**Status:** All public data source links collected ✓

---

## 📊 What Was Collected

The data scraper has identified and cataloged **15+ public data sources** for model verification.

### ✅ Ready for Download (Free/Public)

| Priority | Source | URL | Data Needed |
|----------|--------|-----|-------------|
| **HIGH** | USS 2023 10-K | [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K) | Segment volumes, prices, financials |
| **HIGH** | USS 2024 Proxy (DEF 14A) | [SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=DEF%2014A) | Barclays & Goldman fairness opinions |
| **HIGH** | CME HRC Futures 2023 | [CME Group](https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html) | Daily settlement prices for 2023 avg |
| **MEDIUM** | SteelBenchmarker | [PDF History](http://www.steelbenchmarker.com/files/history.pdf) | Monthly composite steel prices |
| **MEDIUM** | USS Q4 2023 Earnings | [USS Investor Relations](https://www.ussteel.com/investors/events-presentations) | Capital project guidance |
| **MEDIUM** | Nippon Acquisition PR | [Nippon News](https://www.nipponsteel.com/en/news/) | NSA $14B commitment details |
| **LOW** | FRED Steel PPI | [FRED WPU101](https://fred.stlouisfed.org/series/WPU101) | Producer price index (relative) |
| **LOW** | World Steel Assoc | [WSA Prices](https://worldsteel.org/steel-topics/statistics/prices/) | Global price trends |

---

## 📁 Files Generated

All reference files saved to: `audits/evidence/`

```
evidence/
├── steel_price_sources.json        # 4 free steel price data sources
├── company_sources.json            # 3 USS/Nippon presentation links
├── analyst_sources.json            # Fairness opinion locations
├── data_collection_checklist.json  # 13-item download checklist
├── USS_10-K_2023_metadata.json    # SEC filing metadata
└── USS_DEF 14A_2024_metadata.json # Proxy filing metadata
```

---

## 🎯 Quick Action Plan

### Step 1: Download SEC Filings (10 minutes)

**USS 2023 10-K:**
1. Visit: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K
2. Click on the most recent 2023 filing (filed Feb 2024)
3. Download the full 10-K PDF
4. Save as: `audits/evidence/USS_10K_2023.pdf`

**What to extract:**
- Page __: Segment shipment volumes (Flat-Rolled, Mini Mill, USSE, Tubular)
- Page __: Segment revenues (calculate price = revenue/volume)
- Page __: Balance sheet (debt, cash, shares)
- Page __: Tax rate (cash taxes / pre-tax income)

**USS 2024 Proxy Statement:**
1. Visit: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=DEF%2014A
2. Download 2024 proxy (DEF 14A)
3. Save as: `audits/evidence/USS_Proxy_2024.pdf`

**What to extract:**
- Annex A or B: Barclays fairness opinion
  - DCF valuation range: $__-$__/share
  - WACC range: __-__%
  - Management projections (2024-2029)
- Annex: Goldman fairness opinion
  - DCF valuation range: $__-$__/share
  - Comparable transactions

### Step 2: Download Steel Prices (15 minutes)

**CME HRC Futures (Priority #1):**
1. Visit: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html
2. Set date range: Jan 1, 2023 - Dec 31, 2023
3. Click "Export" or download CSV
4. Save as: `audits/evidence/CME_HRC_Futures_2023.csv`
5. Calculate 2023 average settlement price

**SteelBenchmarker (Priority #2):**
1. Visit: http://www.steelbenchmarker.com/files/history.pdf
2. Download the PDF
3. Find 2023 section
4. Extract monthly averages for composite price
5. Calculate 2023 average

**FRED Steel PPI (Priority #3):**
1. Visit: https://fred.stlouisfed.org/series/WPU101
2. Set date range: Jan 2023 - Dec 2023
3. Download CSV
4. Use as relative indicator (not absolute price)

### Step 3: Download Company Data (Optional - 10 minutes)

**USS Earnings Presentation:**
1. Visit: https://www.ussteel.com/investors/events-presentations
2. Find Q4 2023 earnings presentation
3. Download PDF
4. Look for: BR2 CapEx, capital projects guidance

**Press Releases:**
1. Visit: https://www.ussteel.com/newsroom/press-releases
2. Search for "Big River Steel Phase 2"
3. Search for "Gary Works"
4. Download relevant press releases

---

## 📝 Data Entry Workflow

After downloading documents:

### 1. Fill USS 2023 Data
```bash
# Edit: data_collection/uss_2023_data.csv
```

Extract from 10-K:
- Flat-Rolled shipments: ____ thousand tons (pg __)
- Mini Mill shipments: ____ thousand tons (pg __)
- USSE shipments: ____ thousand tons (pg __)
- Tubular shipments: ____ thousand tons (pg __)
- Calculate prices: Revenue / Volume

### 2. Fill Steel Prices
```bash
# Edit: data_collection/steel_prices_2023.csv
```

From CME/SteelBenchmarker:
- US HRC 2023 avg: $____/ton
- US CRC 2023 avg: $____/ton (or estimate from HRC)
- EU HRC 2023 avg: $____/ton
- OCTG 2023 avg: $____/ton

### 3. Fill Balance Sheet
```bash
# Edit: data_collection/balance_sheet_items.csv
```

From 10-K:
- Total debt: $____M
- Cash: $____M
- Shares outstanding: ____M shares

### 4. Fill Capital Projects
```bash
# Edit: data_collection/capital_projects.csv
```

From proxy/presentations:
- BR2 total CapEx: $____M
- Gary Works CapEx: $____M
- Total NSA commitment: $____M (should be ~$14B)

### 5. Note Page Numbers
```bash
# Edit: data_collection/source_data_tracker.md
```

Document where each number came from for audit trail.

---

## ✅ Verification

After filling CSVs, run:

```bash
cd audits/verification_scripts
python verify_inputs.py
```

**Expected Results:**
- ✓ OK: Variance < 2%
- ⚠ REVIEW: Variance 2-5%
- ✗ FLAG: Variance > 5%

**Acceptable Variances:**
- Segment data: < 2% (should match exactly)
- Steel prices: < 10% (volatile commodity)
- Balance sheet: < 1% for debt/cash/shares
- Capital projects: < 10% (estimates)

---

## 🚫 What We CAN'T Get (Subscription Required)

| Source | Cost | Alternative |
|--------|------|-------------|
| Platts Steel Prices | $$$ | Use CME + SteelBenchmarker |
| Bloomberg Terminal | $$$ | Fairness opinions have enough |
| FactSet | $$$ | Not needed for audit |
| Wall Street Research | $$$ | Use consensus from proxy |

---

## 📊 Success Metrics

**Minimum Viable Audit:**
- [ ] USS 10-K downloaded
- [ ] 10-K segment data extracted (4 segments)
- [ ] CME HRC data downloaded and averaged
- [ ] Balance sheet items verified
- [ ] Run verify_inputs.py
- [ ] < 5 high-severity variances

**Full Audit:**
- [ ] All SEC filings collected
- [ ] All steel price sources checked
- [ ] Company presentations downloaded
- [ ] All CSV templates filled
- [ ] Fairness opinions reviewed
- [ ] All variances < 5%
- [ ] Audit report generated

---

## 🎯 Time Estimate

| Task | Time | Difficulty |
|------|------|------------|
| Download SEC filings | 10 min | Easy |
| Download steel prices | 15 min | Easy |
| Extract 10-K data | 30 min | Medium |
| Extract steel prices | 15 min | Easy |
| Fill CSV templates | 20 min | Easy |
| Run verification | 2 min | Easy |
| Review variances | 10 min | Easy |
| **TOTAL** | **~1.5 hours** | **Easy-Medium** |

---

## 📞 Support

**Documentation:**
- Full guide: `QUICK_START.md`
- Audit plan: `MODEL_AUDIT_PLAN.md`
- Results: `AUDIT_SUMMARY.md`

**Files:**
- Templates: `data_collection/*.csv`
- Sources: `evidence/*.json`
- Scripts: `verification_scripts/*.py`

**Questions?**
- Check `data_collection/source_data_tracker.md` for extraction hints
- Review `evidence/README.md` for file naming conventions

---

## 🔄 Update This File

As you download documents, update the checklist:

```bash
cd audits/evidence
# Edit data_collection_checklist.json
# Change status from "pending" to "complete"
```

---

**Next Step:** Download USS 2023 10-K from SEC EDGAR (takes 5 minutes)

**URL:** https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K
