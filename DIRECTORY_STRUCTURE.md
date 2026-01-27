# Directory Structure Guide

This document explains the organization of the USS Financial Model project.

**Last Updated:** 2026-01-26

## Root Directory - Core Files

The main directory contains only the most crucial files needed to run the model:

```
FinancialModel/
├── README.md                    # Project overview and quick start guide
├── DIRECTORY_STRUCTURE.md       # This file
├── requirements.txt             # Python dependencies
├── interactive_dashboard.py     # Main interactive dashboard (Streamlit)
├── price_volume_model.py        # Core DCF financial model
└── data_loader.py               # Data loading utilities
```

## Subdirectories

### `/reference_materials/`
Source data files and reference documents:

**Excel Data (Capital IQ Exports):**
- `United States Steel Corporation Financials.xls` - Historical financials, ratios, multiples
- `Company Comparable Analysis United States Steel Corporation.xls` - Peer company comparisons
- `United States Steel Corporation Comparable M A Transactions.xls` - M&A transaction comps

**PDF Documents:**
- `USS Financial Report 2023_pages.pdf` - 2023 10-K Annual Report
- `Deck - Nippon Steel Corporation to Acquire U. S. Steel.pdf` - Deal presentation

**Research Notes:**
- `Global Steel Industry Overview.md`
- `Steel Industry.md`
- `The Economics of Steel - What Drives Industry Behavior.md`
- `Nippon US Steel Merger Overview.md`
- `Nippon US Steel History.md`
- `USS Business Segment Analysis.md`

---

### `/audits/`
Data validation, verification, and audit infrastructure:

```
audits/
├── run_audit.py                 # Master audit orchestration script
├── model_audit.py               # Model validation logic
├── README.md                    # Audit documentation
├── QUICK_START.md               # Quick reference guide
├── audit_results.csv            # Automated test results
│
├── /input_traceability/         # ★ INPUT TRACEABILITY AUDIT
│   ├── input_audit_comparison.xlsx    # Main Excel workbook (view this!)
│   ├── comprehensive_audit.py         # Full audit script
│   ├── input_traceability_audit.py    # Input tracing script
│   ├── create_audit_excel.py          # Excel generation script
│   ├── audit_report.md                # Markdown report
│   ├── audit_inputs.csv               # Input validation data
│   ├── audit_assumptions.csv          # Assumptions data
│   ├── audit_outputs.csv              # Output validation data
│   └── input_traceability.csv         # Traceability data
│
├── /evidence/                   # Source documents
│   ├── USS Financial Statements.xlsx
│   ├── FRED_Steel_PPI_2023.csv
│   └── README.md
│
├── /data_collection/            # Collected data templates
│   ├── uss_2023_data.csv
│   ├── steel_prices_2023.csv
│   ├── balance_sheet_items.csv
│   ├── capital_projects.csv
│   └── source_data_tracker.md
│
├── /results/                    # Generated audit reports
│   ├── audit_report_*.md
│   └── input_verification_issues.csv
│
├── /verification_scripts/       # Data validation scripts
│   ├── data_scraper.py
│   ├── fetch_free_data.py
│   └── verify_inputs.py
│
└── Various summary documents (*.md)
```

---

### `/documentation/`
All project documentation and analysis reports:

**Core Documentation:**
- `EXECUTIVE_SUMMARY.md` - High-level project overview
- `MODEL_METHODOLOGY.md` - Detailed methodology and calculations
- `SCENARIO_ASSUMPTIONS.md` - Assumptions for different scenarios
- `SENSITIVITY_ANALYSIS.md` - Sensitivity analysis documentation
- `STEEL_PRICE_METHODOLOGY.md` - Steel price modeling approach

**Analysis Reports:**
- `USS_STANDALONE_ANALYSIS.md` - Standalone USS analysis
- `USS_HISTORICAL_ANALYSIS_1990_2023.md` - Historical performance analysis
- `MODEL_VALIDATION_HISTORICAL_CORRELATION.md` - Model validation
- `Cleveland-Cliffs_Final_Offer_Analysis.md` - Alternative bidder analysis
- `RISKS_AND_CHALLENGES.md` - Risk assessment

**Implementation Notes:**
- `BREAKUP_FEE_SUMMARY.md` - Breakup fee analysis
- `BREAKUP_FEE_ENHANCEMENTS.md` - Enhanced breakup fee analysis
- `IMPLEMENTATION_COMPLETE.md` - Implementation completion notes
- `IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `VISUAL_GUIDE.md` - Guide to model visualizations

---

### `/scripts/`
Analysis and calculation scripts:

```
scripts/
├── data_loader.py               # USS data loading from Excel/CSV
├── benchmark_sensitivity.py     # Benchmark sensitivity analysis
├── breakup_fee_analysis.py      # Breakup fee calculations
├── capex_analysis.py            # Capital expenditure analysis
└── generate_toc.py              # Table of contents generator
```

---

### `/visualization/`
Visualization scripts and generated images:

```
visualization/
├── model_visual.py              # Model architecture diagrams
├── calculation_flow.py          # Calculation flow diagrams
├── dashboard_flow.py            # Dashboard flow diagrams
├── benchmark_sensitivity_chart.py  # Sensitivity charts
└── *.png                        # Generated images
```

---

### `/lbo_model/`
Leveraged Buyout (LBO) analysis module:

```
lbo_model/
├── README.md                    # LBO module overview
├── LBO_ANALYSIS_SUMMARY.md      # Analysis summary
├── LBO_COMPLETE_ANALYSIS.md     # Complete analysis details
├── DASHBOARD_INTEGRATION.md     # Dashboard integration guide
├── README_STRESS_TESTING.md     # Stress testing documentation
│
├── /scripts/                    # LBO calculation scripts
│   ├── uss_lbo_model.py         # Main LBO model
│   ├── lbo_model_template.py    # Template/base model
│   ├── stress_scenarios.py      # Stress testing scripts
│   └── 00_INTEGRATION_GUIDE.md
│
└── /research/                   # LBO research documents
    ├── 00_README.md
    ├── 01_debt_market_conditions.md
    ├── 02_comparable_lbo_transactions.md
    ├── 03_uss_capital_structure.md
    ├── 04_downside_scenarios.md
    ├── 05_lbo_model_structure.md
    └── CITATION_*.md
```

---

### `/tests/`
Test files:

```
tests/
└── test_division_errors.py      # Division error tests
```

---

## Quick Navigation

### Run the Model
```bash
streamlit run interactive_dashboard.py
```

### Run Input Traceability Audit
```bash
cd audits/input_traceability
python comprehensive_audit.py
python create_audit_excel.py
# Output: input_audit_comparison.xlsx
```

### Run Full Audit Suite
```bash
cd audits
python run_audit.py
```

### Generate Visualizations
```bash
cd visualization
python model_visual.py
python calculation_flow.py
python dashboard_flow.py
```

### Run Analysis Scripts
```bash
cd scripts
python benchmark_sensitivity.py
python capex_analysis.py
python breakup_fee_analysis.py
```

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `interactive_dashboard.py` | Main Streamlit dashboard |
| `price_volume_model.py` | Core DCF valuation engine |
| `scripts/data_loader.py` | Load Capital IQ Excel data |
| `audits/input_traceability/input_audit_comparison.xlsx` | **Input audit workbook** |
| `reference_materials/*.xls` | Source financial data |
| `reference_materials/*.pdf` | 10-K and deal documents |

---

## File Organization Principles

1. **Root directory** - Only essential files for running the core model
2. **reference_materials/** - All source data (Excel, PDF, research)
3. **documentation/** - All markdown documentation files
4. **scripts/** - Standalone analysis and utility scripts
5. **visualization/** - Chart and diagram generation
6. **audits/** - Complete audit infrastructure with input traceability
7. **lbo_model/** - Self-contained LBO analysis module
8. **tests/** - Test files

This structure keeps the project organized, makes files easy to find, and separates concerns clearly.
