# Directory Structure Guide

This document explains the organization of the USS Financial Model project.

## Root Directory - Core Files

The main directory contains only the most crucial files needed to run the model:

- **README.md** - Project overview and quick start guide
- **requirements.txt** - Python dependencies
- **interactive_dashboard.py** - Main interactive dashboard application
- **price_volume_model.py** - Core financial model implementation
- **.gitignore** - Git ignore rules

## Subdirectories

### `/documentation/`
Contains all project documentation and analysis reports:

- **EXECUTIVE_SUMMARY.md** - High-level project overview
- **MODEL_METHODOLOGY.md** - Detailed methodology and calculations
- **SCENARIO_ASSUMPTIONS.md** - Assumptions for different scenarios
- **SENSITIVITY_ANALYSIS.md** - Sensitivity analysis documentation
- **RISKS_AND_CHALLENGES.md** - Risk assessment
- **USS_STANDALONE_ANALYSIS.md** - Standalone USS analysis
- **STEEL_PRICE_METHODOLOGY.md** - Steel price modeling approach
- **BREAKUP_FEE_SUMMARY.md** - Breakup fee analysis summary
- **BREAKUP_FEE_ENHANCEMENTS.md** - Enhanced breakup fee analysis
- **IMPLEMENTATION_COMPLETE.md** - Implementation completion notes
- **VISUAL_GUIDE.md** - Guide to model visualizations

### `/scripts/`
Analysis and calculation scripts:

- **benchmark_sensitivity.py** - Benchmark sensitivity analysis
- **breakup_fee_analysis.py** - Breakup fee calculations
- **capex_analysis.py** - Capital expenditure analysis

### `/visualization/`
Visualization scripts and generated images:

**Scripts:**
- **calculation_flow.py** - Generate calculation flow diagrams
- **dashboard_flow.py** - Generate dashboard flow diagrams
- **model_visual.py** - Create model architecture visualizations
- **benchmark_sensitivity_chart.py** - Create sensitivity charts

**Generated Images:**
- **benchmark_sensitivity_chart.png**
- **calculation_flow.png**
- **dashboard_flow.png**
- **model_architecture.png**

### `/audits/`
Data validation, verification, and audit infrastructure:

- **Subdirectories:**
  - `/evidence/` - Source documents and data files (SEC filings, financial statements, etc.)
  - `/data_collection/` - Collected data in CSV format
  - `/results/` - Audit reports and verification results
  - `/verification_scripts/` - Data validation and scraping scripts

- **Key Files:**
  - **run_audit.py** - Main audit execution script
  - **model_audit.py** - Model validation logic
  - **README.md** - Audit documentation
  - **QUICK_START.md** - Quick reference guide
  - Various summary and results documents

### `/lbo_model/`
Leveraged Buyout (LBO) analysis module:

- **Subdirectories:**
  - `/research/` - LBO research and methodology documents
  - `/scripts/` - LBO calculation scripts and models

- **Key Files:**
  - **README.md** - LBO module overview
  - **LBO_ANALYSIS_SUMMARY.md** - Analysis summary
  - **LBO_COMPLETE_ANALYSIS.md** - Complete analysis details
  - **DASHBOARD_INTEGRATION.md** - Dashboard integration guide
  - **README_STRESS_TESTING.md** - Stress testing documentation

### `/docs/`
Technical documentation and architecture diagrams:

- **model_architecture.dot** - GraphViz source file
- **model_architecture.png** - Architecture diagram (PNG)
- **model_architecture.svg** - Architecture diagram (SVG)

### System Directories (Do Not Modify)
- `/.git/` - Git version control data
- `/.claude/` - Claude Code configuration
- `/.devcontainer/` - Development container configuration
- `/__pycache__/` - Python compiled bytecode

## Quick Navigation

**To run the model:**
```bash
python interactive_dashboard.py
```

**To run audits:**
```bash
cd audits
python run_audit.py
```

**To generate visualizations:**
```bash
cd visualization
python model_visual.py
python calculation_flow.py
python dashboard_flow.py
```

**To run analysis scripts:**
```bash
cd scripts
python benchmark_sensitivity.py
python capex_analysis.py
python breakup_fee_analysis.py
```

## File Organization Principles

1. **Root directory** - Only essential files for running the core model
2. **documentation/** - All markdown documentation files
3. **scripts/** - Standalone analysis scripts
4. **visualization/** - Everything related to creating charts and diagrams
5. **audits/** - Complete audit infrastructure (pre-organized)
6. **lbo_model/** - Self-contained LBO analysis module
7. **docs/** - Technical architecture documentation

This structure keeps the project organized, makes files easy to find, and separates concerns clearly.
