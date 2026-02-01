# Directory Structure Guide

This document explains the organization of the USS Financial Model project.

**Last Updated:** 2026-02-01

## Root Directory - Core Files Only

The main directory contains only the essential files needed to run the model:

```
FinancialModel/
├── README.md                    # Project overview and quick start guide
├── DIRECTORY_STRUCTURE.md       # This file
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── interactive_dashboard.py     # Main interactive dashboard (Streamlit)
└── price_volume_model.py        # Core DCF financial model
```

## Subdirectories

### `/scripts/`
Analysis scripts, utilities, and core modules:

**Core Modules:**
- `data_loader.py` - Data loading utilities for USS financial data
- `benchmark_data.py` - Benchmark data and industry comparisons
- `cache_persistence.py` - Caching utilities for performance
- `export_model.py` - Model export and serialization

**Analysis Scripts:**
- `benchmark_sensitivity.py` - Benchmark sensitivity analysis
- `breakup_fee_analysis.py` - Breakup fee calculations
- `capex_analysis.py` - Capital expenditure analysis
- `check_value_alignment.py` - Value alignment verification
- `verify_synergies.py` - Synergy verification
- `run_monte_carlo_demo.py` - Monte Carlo simulation demo

**Dashboard Scripts:**
- `run_dashboard.py` - Dashboard launcher
- `test_dashboard.py` - Dashboard testing

**Utilities:**
- `generate_toc.py` - Table of contents generator

---

### `/tests/`
Test files and test utilities:

```
tests/
├── test_division_errors.py      # Division error tests
├── test_dashboard_features.py   # Dashboard feature tests
└── __pycache__/                 # Python cache (auto-generated)
```

---

### `/documentation/`
All project documentation, analysis reports, and diagrams. See `documentation/README.md` for a complete index with summaries.

**Core Documentation:**
- `EXECUTIVE_SUMMARY.md` - High-level project overview
- `MODEL_METHODOLOGY.md` - Detailed methodology and calculations
- `SCENARIO_ASSUMPTIONS.md` - Assumptions for different scenarios
- `SENSITIVITY_ANALYSIS.md` - Sensitivity analysis documentation
- `STEEL_PRICE_METHODOLOGY.md` - Steel price modeling approach

**User Guides:**
- `DASHBOARD_USER_GUIDE.md` - Interactive dashboard guide
- `MONTE_CARLO_USER_GUIDE.md` - Monte Carlo simulation guide
- `SENSITIVITY_ANALYSIS_QUICK_START.md` - Quick start for simulations

**Analysis Reports:**
- `USS_STANDALONE_ANALYSIS.md` - Standalone USS analysis
- `USS_HISTORICAL_ANALYSIS_1990_2023.md` - Historical performance (1990-2023)
- `Cleveland-Cliffs_Final_Offer_Analysis.md` - Alternative bidder analysis
- `RISKS_AND_CHALLENGES.md` - Risk assessment

**Diagrams:**
- `model_architecture.png/svg/dot` - Model architecture diagrams

---

### `/references/`
Source data files and reference documents:

**Excel Data (Capital IQ Exports):**
- `United States Steel Corporation Financials.xls` - Historical financials, ratios, multiples
- `Company Comparable Analysis United States Steel Corporation.xls` - Peer company comparisons
- `United States Steel Corporation Comparable M A Transactions.xls` - M&A transaction comps

**PDF Documents:**
- `USS Financial Report 2023_pages.pdf` - 2023 10-K Annual Report
- `Deck - Nippon Steel Corporation to Acquire U. S. Steel.pdf` - Deal presentation

**Research Notes:**
- `Global Steel Industry Overview.md` - Global steel industry analysis
- `Steel Industry.md` - Steel industry overview
- `The Economics of Steel - What Drives Industry Behavior.md` - Steel economics
- `Nippon US Steel Merger Overview.md` - Merger overview
- `USS Business Segment Analysis.md` - Business segment breakdown

**Comparable Company Data:**
- `steel_comps/` - Steel company comparable data (large files, git-ignored)

---

### `/audit-verification/`
Data validation, verification, and audit infrastructure:

```
audit-verification/
├── run_audit.py                 # Master audit orchestration script
├── model_audit.py               # Model validation logic
├── README.md                    # Audit documentation
├── audit_results.csv            # Automated test results
│
├── /input_traceability/         # INPUT TRACEABILITY AUDIT
│   ├── input_audit_comparison.xlsx    # Main Excel workbook
│   ├── comprehensive_audit.py         # Full audit script
│   ├── input_traceability_audit.py    # Input tracing script
│   └── create_audit_excel.py          # Excel generation script
│
├── /evidence/                   # Source documents
├── /data_collection/            # Collected data templates
├── /results/                    # Generated audit reports
└── /verification_scripts/       # Data validation scripts
```

---

### `/monte_carlo/`
Monte Carlo simulation engine (Python package):

```
monte_carlo/
├── __init__.py                  # Package exports
├── monte_carlo_engine.py        # Core simulation engine
└── README.md                    # Module documentation
```

**Usage:**
```python
from monte_carlo import MonteCarloEngine

mc = MonteCarloEngine(n_simulations=10000)
results = mc.run_simulation()
mc.print_summary()
```

---

### `/charts/`
Visualization scripts and generated images:

**Python Scripts:**
- `model_visual.py` - Model architecture diagram generation
- `calculation_flow.py` - Calculation flow diagram generation
- `dashboard_flow.py` - Dashboard flow diagram generation
- `benchmark_sensitivity_chart.py` - Sensitivity chart generation

**Generated Images:**
- `model_architecture.png` - Model architecture diagram
- `calculation_flow.png` - Calculation flow diagram
- `dashboard_flow.png` - Dashboard flow diagram
- `benchmark_sensitivity_chart.png` - Sensitivity chart
- `uss_historical_trends_1990_2023.png` - Historical trends chart

---

### `/lbo-analysis/`
Leveraged Buyout (LBO) analysis module:

```
lbo-analysis/
├── README.md                    # LBO module overview
├── README_STRESS_TESTING.md     # Stress testing documentation
├── LBO_ANALYSIS_SUMMARY.md      # Analysis summary
│
├── /scripts/                    # LBO calculation scripts
│   ├── uss_lbo_model.py         # Main LBO model
│   ├── lbo_model_template.py    # Template/base model
│   └── stress_scenarios.py      # Stress testing scripts
│
├── /research/                   # LBO research documents
│   ├── 01_debt_market_conditions.md
│   ├── 02_comparable_lbo_transactions.md
│   ├── 03_uss_capital_structure.md
│   └── 04_downside_scenarios.md
│
└── /data/                       # LBO-specific data files
```

---

### `/company-financials/`
Input data files and extracted datasets:

```
company-financials/
├── Company Comparable Analysis uss.xls  # USS comparable analysis
└── extracted_steel_metrics.csv          # Extracted steel industry metrics
```

---

### `/market-data/`
Bloomberg market data and integration:

```
market-data/
├── README.md                    # Data guide
├── BLOOMBERG_DATA_GUIDE.md      # Bloomberg data documentation
├── bloomberg_loader.py          # Data loading utilities
├── integrate_with_model.py      # Model integration script
├── /raw/                        # Raw Bloomberg exports
└── /exports/                    # Processed exports
```

---

### `/screenshots/`
Dashboard screenshots and visual analysis:

Contains screenshots from various dashboard iterations:
- `final_*.png` - Final dashboard screenshots
- `view_*.png` - Dashboard view screenshots
- `section_*.png` - Individual section screenshots

Used for documentation, testing, and visual regression analysis.

---

### `/local/` (git-ignored)
Local configuration and cached data:

```
local/
├── .env                         # Environment variables (credentials, API keys)
├── wrds_loader.py               # WRDS data loader
├── wrds_cache/                  # WRDS API response cache
└── extracted_steel_metrics.csv  # Local cached metrics
```

**Note:** This directory is git-ignored to protect credentials.

---

### `/cache/` (git-ignored)
Runtime cache for model calculations and data processing.

---

## Quick Navigation

### Run the Model
```bash
streamlit run interactive_dashboard.py
```

### Run Monte Carlo Simulation
```bash
python scripts/run_monte_carlo_demo.py -n 1000
```

### Run Input Traceability Audit
```bash
cd audit-verification/input_traceability
python comprehensive_audit.py
python create_audit_excel.py
```

### Run Full Audit Suite
```bash
cd audit-verification
python run_audit.py
```

### Generate Visualizations
```bash
cd charts
python model_visual.py
python calculation_flow.py
```

### Run Tests
```bash
pytest tests/
```

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `interactive_dashboard.py` | Main Streamlit dashboard (entry point) |
| `price_volume_model.py` | Core DCF valuation engine |
| `scripts/data_loader.py` | Load Capital IQ Excel data |
| `monte_carlo/monte_carlo_engine.py` | Monte Carlo simulation engine |
| `audit-verification/input_traceability/input_audit_comparison.xlsx` | Input audit workbook |
| `references/*.xls` | Source financial data |
| `documentation/README.md` | Documentation index |

---

## Directory Summary

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Python utilities and analysis scripts |
| `tests/` | Test files |
| `documentation/` | All markdown docs and diagrams |
| `references/` | Source data (Excel, PDF, research) |
| `audit-verification/` | Audit infrastructure and traceability |
| `monte_carlo/` | Monte Carlo simulation package |
| `charts/` | Visualization scripts and images |
| `lbo-analysis/` | LBO analysis module |
| `company-financials/` | Input data files |
| `market-data/` | Bloomberg market data |
| `screenshots/` | Dashboard screenshots |
| `local/` | Local config (git-ignored) |
| `cache/` | Runtime cache (git-ignored) |
