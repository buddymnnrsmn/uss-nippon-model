# Model Audit Project
## USS / Nippon Steel DCF Model - Data Verification & Quality Assurance

This folder contains all audit-related materials for the USS/Nippon Steel DCF model.

---

## Audit Status

**Last Run:** February 6, 2026
**Automated Tests:** 128 passed, 5 failed (pre-existing Bloomberg calibration issue)
**Input Audit (run_audit.py):** 82.6% pass rate
**Comprehensive Audit:** CIQ vs 10-K reconciliation complete
**Source Documents:** 7/8 acquired
**Status:** PASS WITH COMMENTS

See `AUDIT_SUMMARY.md` for full results.

---

## Quick Start

### Run All Audits
```bash
# Main automated audit (model checks)
python audit-verification/run_audit.py

# Comprehensive audit (CIQ vs 10-K + model assumptions + outputs)
python audit-verification/input_traceability/comprehensive_audit.py

# All tests
python -m pytest tests/ -q
```

### Download Source Documents
```bash
# Download USS 10-K and DEFM14A from SEC EDGAR
python scripts/fetch_sec_filings.py

# Extract financial data from 10-K
python scripts/extract_10k_data.py

# Extract peer capex benchmarks
python scripts/extract_peer_capex.py

# Run margin sensitivity regression
python scripts/extract_margin_sensitivity.py
```

---

## Folder Structure

```
audit-verification/
├── README.md                                  # This file
├── AUDIT_SUMMARY.md                           # Overall audit results
├── MODEL_AUDIT_PLAN.md                        # 100+ checkpoint audit plan
├── MISSING_DOCUMENTS_TRACKER.md               # Source document acquisition status
├── CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md # Consolidated project parameters
├── model_audit.py                             # Automated test suite
├── run_audit.py                               # Main audit runner
├── audit_results.csv                          # Test results export
│
├── data_collection/                           # Extracted verification data
│   ├── uss_10k_extracted_data.json           # Parsed 10-K (debt, cash, pension, shares, segments)
│   ├── maintenance_capex_benchmarks.csv      # Peer capex/ton from 10-K filings
│   ├── margin_sensitivity_analysis.csv       # Empirical margin vs price regression
│   ├── source_data_tracker.md                # Checklist of required documents
│   ├── uss_2023_data.csv                     # 10-K data entry
│   ├── steel_prices_2023.csv                 # Price benchmarks
│   ├── capital_projects.csv                  # Project data
│   └── balance_sheet_items.csv               # B/S verification
│
├── input_traceability/                        # Comprehensive audit
│   ├── comprehensive_audit.py                # Full audit: CIQ vs 10-K + assumptions + outputs
│   ├── audit_report.md                       # Generated audit report
│   ├── audit_inputs.csv                      # Input audit results
│   ├── audit_assumptions.csv                 # Assumptions audit results
│   └── audit_outputs.csv                     # Output audit results
│
├── evidence/                                  # Source documents
│   ├── uss_defm14a_2024.htm                  # USS merger proxy (DEFM14A, 2.9 MB)
│   ├── uss_sec_download_results.json         # Download metadata
│   ├── Schedule 14A - USS Merger Proxy Report.txt  # Full proxy text
│   ├── USS Financial Statements.xlsx         # Capital IQ multi-sheet export
│   └── ...
│
└── verification_scripts/                      # Automated comparison tools
    ├── verify_inputs.py                      # Compare model vs source data
    ├── data_scraper.py                       # Data collection helper
    └── fetch_free_data.py                    # Free data source fetcher
```

### Related Files (outside audit-verification/)

| File | Purpose |
|------|---------|
| `references/uss_10k_2023.htm` | USS 10-K FY2023 (4.7 MB, from SEC EDGAR) |
| `references/uss_capital_iq_export_2023.xls` | Capital IQ balance sheet export |
| `references/steel_comps/wrds_peer_ev_ebitda.csv` | Peer EV/EBITDA multiples (FY2022-2023) |
| `references/steel_comps/sec_filings/` | Peer 10-K/20-F filings (9 companies) |
| `scripts/fetch_sec_filings.py` | Download USS filings from SEC EDGAR |
| `scripts/extract_10k_data.py` | Parse 10-K for debt/cash/pension/shares/segments |
| `scripts/extract_peer_capex.py` | Parse peer 10-Ks for capex/ton |
| `scripts/extract_margin_sensitivity.py` | Regress USS segment margin vs price |

---

## Source Documents

| # | Document | Priority | Status | Location |
|---|----------|----------|--------|----------|
| 1 | USS 10-K FY2023 | Critical | ACQUIRED | `references/uss_10k_2023.htm` |
| 2 | Capital Projects EBITDA Analysis | Critical | CREATED | `CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md` |
| 3 | USS DEFM14A Fairness Opinion | Critical | ACQUIRED | `evidence/uss_defm14a_2024.htm` |
| 4 | Nippon Investor Presentation | Important | ACQUIRED | `references/Deck - Nippon Steel...pdf` |
| 5 | WRDS Peer EV/EBITDA Export | Important | ACQUIRED | `references/steel_comps/wrds_peer_ev_ebitda.csv` |
| 6 | Maintenance CapEx Benchmarks | Important | ACQUIRED | `data_collection/maintenance_capex_benchmarks.csv` |
| 7 | S&P Capital IQ Balance Sheet | Nice to have | ACQUIRED | `references/uss_capital_iq_export_2023.xls` |
| 8 | Margin Sensitivity Source | Nice to have | ACQUIRED | `data_collection/margin_sensitivity_analysis.csv` |

See `MISSING_DOCUMENTS_TRACKER.md` for detailed status and acquisition history.

---

## Key Findings

### Capital IQ vs Model Reconciliation
Net debt difference is only $25M (1.8%) — validates equity bridge. Component differences (debt +$426M, cash +$401M) are due to CIQ including lease obligations in debt and broader cash definitions.

### Margin Sensitivity Validation
Empirical margin sensitivity (2.1-4.3% per $100) exceeds model calibration (1.0-2.5%) by 1.1-2.1x, as expected since empirical includes volume and operating leverage effects. Model conservatism is appropriate for forward projection.

### Peer Capex Benchmarks
Model's sustaining capex ($20-40/ton) is conservative vs peer total capex ($49-165/ton). Sustaining is typically 40-60% of total, placing model assumptions at the low end of the range.
