# Dataset Reliability Remediation — Audit Log

*Date: 2026-02-07*

## Summary

Implemented 5-phase remediation addressing 7 reliability risks identified in the dataset audit. Changes affect uncertainty bounds and demand attribution; central estimates (USS ~$39 WA, Nippon ~$55) unchanged.

## Audits That May Need Updating

### 1. `audit-verification/REVENUE_PRICE_CORRELATION_ANALYSIS.md`
- **Status:** Needs regeneration
- **Reason:** `revenue_price_correlation.py` now includes bootstrap CIs in segment annual correlations and can produce quarterly segment correlations (WRDS). Report text updated but output CSV format changed (new columns: `ci_lo_boot`, `ci_hi_boot`, `ci_width`, `quality`).
- **Action:** Re-run `python scripts/revenue_price_correlation.py` to regenerate.

### 2. `audit-verification/segment_annual_correlations.csv`
- **Status:** Needs regeneration
- **Reason:** Now includes bootstrap CI columns (`ci_lo_boot`, `ci_hi_boot`, `ci_width`, `ci_method`, `quality`). Old file lacks these.
- **Action:** Re-run `python scripts/revenue_price_correlation.py`.

### 3. `audit-verification/ADVANCED_DEMAND_ANALYSIS.md`
- **Status:** Needs regeneration
- **Reason:** `advanced_demand_analysis.py` now computes composite indicator scores and saves `composite_indicator_scores.csv`. Report should reference these.
- **Action:** Re-run `python scripts/advanced_demand_analysis.py`.

### 4. `audit-verification/data_collection/margin_sensitivity_analysis.csv`
- **Status:** Needs verification
- **Reason:** `extract_margin_sensitivity.py` now imports `USS_SEGMENT_DATA` from shared module instead of inline dict. Values should be identical, but output should be verified.
- **Action:** Re-run `python scripts/extract_margin_sensitivity.py` and verify output matches.

### 5. `monte_carlo/DISTRIBUTION_CALIBRATION.md`
- **Status:** Partially updated
- **Reason:** Updated correlation_matrix filename reference. However, the document does not yet describe the 4 new realization factor variables or the updated 33-variable count.
- **Action:** Add section documenting `fr_realization_factor`, `mm_realization_factor`, `usse_realization_factor`, `tubular_realization_factor` distributions.

### 6. `data/monte_carlo_inputs.csv` and `data/monte_carlo_results.csv`
- **Status:** Needs regeneration
- **Reason:** MC engine now has 33 variables (was 29). Input sample CSV will have 4 new columns. Results may show slightly wider distributions due to realization factor uncertainty.
- **Action:** Re-run `python scripts/run_monte_carlo_analysis.py`.

### 7. `audit-verification/DATA_SOURCES_SUMMARY.md`
- **Status:** May need update
- **Reason:** New data sources added (WRDS segment quarterly, composite indicator scores). Correlation matrix renamed.
- **Action:** Review and update source inventory.

### 8. Dashboard (`interactive_dashboard.py`)
- **Status:** Updated but needs visual verification
- **Reason:** New sections added: composite indicator ranking bar chart, data quality panel (MC calibration, segment coverage, method notes), forest plot for segment CIs.
- **Action:** Run `streamlit run interactive_dashboard.py` and verify all new sections render correctly.

## Changes Made (Summary)

| Phase | Files Changed | Key Change |
|-------|--------------|------------|
| 1 | `scripts/fetch_uss_segment_data.py` (NEW), `data/uss_segment_data.py` (NEW), `scripts/revenue_price_correlation.py`, `scripts/extract_margin_sensitivity.py` | Centralized segment data, bootstrap CIs, quarterly segment analysis |
| 2 | `monte_carlo/distributions_config.json`, `price_volume_model.py`, `monte_carlo/monte_carlo_engine.py` | 4 realization factor triangular MC variables |
| 3 | `scripts/advanced_demand_analysis.py`, `scripts/demand_driver_analysis.py`, `interactive_dashboard.py` | Composite scoring, partial r rankings, stability warnings |
| 4 | `market-data/exports/processed/correlation_matrix_LEVELS.csv` (renamed), `scripts/load_bloomberg_data.py`, `scripts/analyze_distributions.py`, `market-data/bloomberg/config.json`, `monte_carlo/DISTRIBUTION_CALIBRATION.md`, `scripts/run_monte_carlo_analysis.py` | Correlation matrix renamed, calibration quality reporting |
| 5 | `interactive_dashboard.py`, 4 new test files | Data quality dashboard panel, forest plot, 51 new tests |

## Test Results

- **51 passed, 3 skipped** (WRDS quarterly tests skipped — require API token)
- Existing test suite should be re-run for regression: `python -m pytest tests/ -v`
