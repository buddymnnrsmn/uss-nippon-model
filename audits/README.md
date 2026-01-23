# Model Audit Project
## USS / Nippon Steel DCF Model - Data Verification & Quality Assurance

This folder contains all audit-related materials for the USS/Nippon Steel DCF model.

---

## Folder Structure

```
audits/
├── README.md                      # This file
├── MODEL_AUDIT_PLAN.md            # Complete 100+ checkpoint audit plan
├── AUDIT_SUMMARY.md               # Automated test results summary
├── model_audit.py                 # Automated test suite
├── audit_results.csv              # Test results export
│
├── data_collection/               # Manual verification data
│   ├── source_data_tracker.md    # Checklist of required documents
│   ├── uss_2023_data.csv         # Template for 10-K data entry
│   ├── steel_prices_2023.csv     # Template for price benchmarks
│   ├── capital_projects.csv      # Template for project data
│   └── balance_sheet_items.csv   # Template for B/S verification
│
├── verification_scripts/          # Automated comparison tools
│   ├── verify_inputs.py          # Compare model vs source data
│   ├── verify_calculations.py    # Spot-check formulas
│   └── verify_outputs.py         # Cross-check against analyst reports
│
└── evidence/                      # Store source documents here
    ├── README.md                 # Instructions for document collection
    └── .gitkeep
```

---

## Quick Start

### Step 1: Collect Source Documents
```bash
cd evidence/
# Download and store the following:
# - USS 2023 10-K (PDF or HTML)
# - NSA filing documents
# - Steel price data (Platts, CME, etc.)
# - Analyst reports (Barclays, Goldman fairness opinions)
```

### Step 2: Enter Data
```bash
cd data_collection/
# Fill in the CSV templates with data from source documents
```

### Step 3: Run Verification
```bash
cd verification_scripts/
python3 verify_inputs.py
python3 verify_calculations.py
python3 verify_outputs.py
```

### Step 4: Review Results
```bash
# Check the generated reports in audits/results/
```

---

## Required Source Documents

| Document | Purpose | Status |
|----------|---------|--------|
| USS 2023 10-K | Verify volumes, prices, financials | [ ] |
| USS 2023 Q4 Earnings | Verify latest guidance | [ ] |
| NSA Filing (Dec 2023) | Verify capital projects | [ ] |
| Barclays Fairness Opinion | Cross-check valuation | [ ] |
| Goldman Fairness Opinion | Cross-check valuation | [ ] |
| S&P Platts Steel Prices 2023 | Verify price benchmarks | [ ] |
| CME HRC Futures Data | Alternative price source | [ ] |

---

## Audit Status

**Last Run:** January 21, 2026
**Pass Rate:** 95.7% (22/23 tests)
**Status:** ✓ PASS WITH COMMENTS

See `AUDIT_SUMMARY.md` for full results.

---

## Contact

For questions about the audit process, see `MODEL_AUDIT_PLAN.md` for detailed test descriptions.
