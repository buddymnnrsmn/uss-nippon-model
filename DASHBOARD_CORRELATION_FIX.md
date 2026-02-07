# Dashboard Correlation Section Replacement

## Date: 2026-02-07

## Problem Identified

The interactive dashboard's "Steel Price Correlation Analysis" section was showing misleading correlations, including:
- **CRC US vs FCF: -0.86** (counterintuitive negative correlation)
- Based on only **3 data points** (2024-2026)
- Spurious correlation driven by capital project timing, not actual price relationships

## Root Cause

1. **Insufficient data**: Historical/forward price data only overlaps with projections for 3 years (2024-2026)
2. **Confounding variables**: FCF drops in 2024 & 2026 due to high capex (Gary Works BF reline, Mon Valley HSM), not due to CRC prices
3. **Circular logic**: Projections already incorporate price assumptions, creating artificial patterns

## Solution: Monte Carlo Simulation Results Section

The entire "Steel Price Correlation Analysis" section (~430 lines) was **replaced** with a new "Monte Carlo Simulation Results" section that loads pre-computed simulation data from CSV files.

### New Section Components

| Component | Chart Type | Purpose |
|-----------|-----------|---------|
| **Summary Statistics** | `st.metric()` in 3 columns | USS mean/median/P5-P95, Nippon same, synergy premium |
| **Dual Distribution** | Overlaid `go.Histogram()` x 2 | USS (blue) + Nippon (green), $55 offer line, medians |
| **Tornado Sensitivity** | Horizontal `go.Bar()`, top 10 | Correlation of each input with Nippon share price |
| **CDF Comparison** | Overlaid `go.Scatter()` x 2 | Empirical CDF, P(< $55) annotation, median crosshairs |

### Data Sources

- `data/monte_carlo_results.csv` — N x 13 output columns (dynamic row count)
- `data/monte_carlo_inputs.csv` — N x 26 input variables (dynamic row count)
- Iteration count derived dynamically from `len(results_df)`

### Changes to `interactive_dashboard.py`

1. **Removed import**: `create_correlation_matrix` (orphaned after correlation matrix removal)
2. **Added**: `load_monte_carlo_data()` cached loader function
3. **Added**: `MC_VARIABLE_LABELS` dict mapping 26 column names to human-readable labels
4. **Replaced**: Entire Steel Price Correlation Analysis section with Monte Carlo Results section

### True Correlations (from Monte Carlo)

Based on 1,000 simulations (top 5 drivers of Nippon share price):

| Input Variable | Correlation | Direction |
|----------------|-------------|-----------|
| **HRC Price Factor** | **+0.43** | Positive (as expected) |
| **Coated Price Factor** | **+0.38** | Positive |
| **CRC Price Factor** | **+0.35** | Positive |
| **Annual Price Growth** | **+0.24** | Positive |
| **Tariff Probability** | **-0.18** | Negative |

## Verification

```bash
streamlit run interactive_dashboard.py
```

Navigate to "Monte Carlo Simulation Results" section:
- 4 charts render without errors
- Statistics: USS median ~$55, Nippon median ~$78
- Tornado top drivers: HRC, Coated, CRC (matches prior analysis)
- Header displays actual iteration count from CSV
