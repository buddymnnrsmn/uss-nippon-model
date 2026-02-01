# Roadmap: Multi-Year Competitor Growth & Profitability Analysis

**Status:** Planned for future implementation
**Estimated Effort:** ~1,136 lines of code across 3 files
**Priority:** Medium-High
**Dependencies:** Existing WRDS data (2019-2025), USS historical data

---

## Executive Summary

Add comprehensive multi-year CAGR (Compound Annual Growth Rate) analysis to compare USS vs 11 peer steel companies across profitability and operational metrics. This feature provides two analysis dimensions:

1. **Rolling Period Analysis (2019-2025):** Shows how USS and peer growth rates evolved over time
2. **USS Long-Term Historical:** Shows USS-only trends going back to 1990s

## Business Value

**For Investment Decision Making:**
- Identify whether USS is accelerating or decelerating vs peers
- Benchmark USS growth against industry leaders over multiple time horizons
- Assess competitive positioning across profitability, investment, and balance sheet metrics

**For Strategic Planning:**
- Understand long-term USS growth trajectory across business cycles
- Compare recent performance (2019-2025) vs historical patterns
- Identify structural changes in growth dynamics

**For Valuation Analysis:**
- Validate DCF growth assumptions against historical peer growth
- Assess whether exit multiples reflect growth differentials
- Support go/no-go decision on Nippon Steel merger

---

## Feature Scope

### High Confidence Metrics (>90% data coverage)
- Net Income
- CapEx
- Depreciation
- Total Assets
- Total Debt
- Stock Price

### Medium Confidence Metrics (~53% coverage)
- Revenue
- EBITDA
- EBIT
- Margins

### Time Period Analysis

**1. Point-in-Time CAGRs (Peer Comparisons)**
- 3-year: 2021-2023
- 5-year: 2019-2023
- 6-year: 2019-2024 (where data available)

**2. Rolling Period Analysis (USS vs Peers)**
- 3-year rolling: 2019-2021, 2020-2022, 2021-2023, 2022-2024
- 5-year rolling: 2019-2023, 2020-2024
- Shows growth acceleration/deceleration trends

**3. USS Long-Term Historical (USS only)**
- 5-year periods: 1995-2000, 2000-2005, 2005-2010, 2010-2015, 2015-2020
- Decades-long view of USS growth trajectory
- No peer comparisons (data unavailable pre-2019)

---

## Technical Implementation Plan

### Phase 1: Data Layer (benchmark_data.py)

**Location:** Add after line 710

**New Methods (8 total):**

1. **`_get_wrds_fundamentals()`** - Loads WRDS peer fundamentals from CSV cache
   - Source: `local/wrds_cache/peer_fundamentals.csv`
   - 107 records, 10 companies, 2019-2025
   - Caches in `_cache` dictionary

2. **`get_uss_timeseries(start_year)`** - Extracts USS historical metrics
   - Parses income statement and balance sheet Excel files
   - Returns DataFrame matching WRDS structure
   - Calculates EBITDA from operating income + depreciation if needed

3. **`calculate_cagr(values, periods)`** - Core CAGR calculator
   - Formula: `(end_value / start_value) ^ (1 / periods) - 1`
   - Handles NaN gracefully (dropna before calculation)
   - Returns NaN for negative/zero starting values

4. **`GrowthStats` dataclass** - Statistical summary container
   - Fields: metric, period, companies, cagrs, min/q1/median/mean/q3/max, count
   - USS-specific: uss_cagr, uss_percentile

5. **`get_multiyear_growth_analysis(metrics, periods)`** - Main analysis engine
   - Calculates CAGR for each peer + USS across specified periods
   - Returns: Dict[metric_name, List[GrowthStats]]
   - Skips companies with <2 data points

6. **`get_peer_timeseries(metric, start_year, end_year, include_uss)`**
   - Returns long-format DataFrame for trend charts
   - Columns: ticker, company_name, year, value

7. **`get_rolling_period_analysis(metrics, window_years)`** - NEW
   - Calculates overlapping period CAGRs (e.g., 2019-2021, 2020-2022, 2021-2023)
   - Returns: DataFrame with period_start, period_end, ticker, cagr, peer_median
   - Shows growth evolution over time

8. **`get_uss_longterm_historical(metrics, periods)`** - NEW
   - USS-only CAGRs for pre-2019 periods
   - Returns: Dict[metric_name, List[Tuple[period_label, cagr]]]
   - Example: [(1995-2000, 0.08), (2000-2005, -0.02), ...]

**Estimated Code:** ~500 lines

---

### Phase 2: Visualization Layer (interactive_dashboard.py)

**Location:** After line 1786 (after peer benchmarking section)

**New Section: "Multi-Year Growth & Profitability Analysis"**

**Subsection A: CAGR Comparison Bar Charts**
- Metric selector: Revenue, EBITDA, Net Income, CapEx, Total Assets
- Period tabs: 3-year, 5-year, 6-year
- Plotly bar chart with USS highlighted (red), peers (blue)
- Peer median reference line (dashed green)
- Statistics: Peer Median, Range, USS CAGR, USS Percentile

**Subsection B: Historical Trend Lines**
- Line chart showing metric values over time (2019-2024)
- USS line: red, width=3
- Peer lines: standard colors, width=2
- Interactive hover with unified mode

**Subsection C: Rolling Period Analysis** - NEW
- Toggle: 3-year rolling vs 5-year rolling
- Plotly line chart:
  - X-axis: Period end year (2021, 2022, 2023, 2024)
  - Y-axis: CAGR (%)
  - Lines: USS, Peer Median, Peer Q1/Q3 bands
- Table showing all rolling period values
- **Key Insight:** Shows if USS is accelerating/decelerating vs peers

**Subsection D: USS Long-Term Historical** - NEW
- Note: "USS only - peer data unavailable before 2019"
- Bar chart showing USS CAGRs across decades
- X-axis: 1995-2000, 2000-2005, 2005-2010, 2010-2015, 2015-2020, 2019-2023
- Y-axis: CAGR (%)
- Color: Green (positive), Red (negative)
- **Key Insight:** Long-term USS growth trajectory

**Subsection E: Growth Summary Table**
- Consolidated view: all metrics × all periods
- Columns: Metric, Period, USS CAGR, Peer Median, Q1/Q3, USS vs Median, # Companies
- Streamlit dataframe with number formatting

**Error Handling:**
- Try/except wrapper for entire section
- Warning if WRDS data unavailable
- "N/A" for missing USS values
- Transparent reporting of data availability

**Estimated Code:** ~350 lines

---

### Phase 3: Excel Export Layer (export_model.py)

**Location:** Add method after line 1188

**New Method: `_create_multiyear_peer_analysis_sheet(wb)`**

**Sheet: "Multi-Year Peer Analysis"** (13th sheet in workbook)

**For each metric (Revenue, EBITDA, Net Income, CapEx, Total Assets):**

**Section 1: Historical Values Table**
- Rows: USS (first, bold red) + Peers alphabetically
- Columns: 2019, 2020, 2021, 2022, 2023, 2024
- Format: Currency ($#,##0)

**Section 2: Point-in-Time CAGR Table**
- Rows: USS + Peers
- Columns: 3-Year (2021-2023), 5-Year (2019-2023), 6-Year (2019-2024)
- Format: Percentage (0.00%)
- Conditional formatting:
  - Green fill: USS > Peer Median
  - Red fill: USS < Peer Median
- Statistics rows: Peer Median, Q1, Q3, Min, Max (yellow fill)

**Section 3: Rolling Period CAGR Table** - NEW
- Shows 3-year and 5-year rolling CAGRs
- Rows: Period windows (2019-2021, 2020-2022, 2021-2023, 2022-2024)
- Columns: USS, Peer Median, Peer Q1, Peer Q3
- Conditional formatting: USS vs median

**Section 4: USS Long-Term Historical Table** - NEW
- USS-only for pre-2019 periods
- Rows: Metrics
- Columns: 1995-2000, 2000-2005, 2005-2010, 2010-2015, 2015-2020
- Format: Percentage with color coding
- Note: "Peer data unavailable for these periods"

**Integration:**
- Call in `export_single_scenario()` (line ~170)
- Call in `export_multi_scenario()` (line ~215)
- Wrap in try/except with warning

**Estimated Code:** ~280 lines

---

### Phase 4: Export Method Updates

**File:** export_model.py

**Modifications:** Add sheet creation calls in both export methods

```python
# In export_single_scenario() (line ~170)
try:
    self._create_multiyear_peer_analysis_sheet(wb)
except Exception as e:
    print(f"Warning: Could not create multi-year peer analysis sheet: {e}")

# In export_multi_scenario() (line ~215)
try:
    self._create_multiyear_peer_analysis_sheet(wb)
except Exception as e:
    print(f"Warning: Could not create multi-year peer analysis sheet: {e}")
```

**Estimated Code:** ~6 lines

---

## Data Sources

**No new data files required.** Uses existing data:

1. **WRDS Peer Fundamentals** (existing)
   - Path: `/workspaces/claude-in-docker/FinancialModel/local/wrds_cache/peer_fundamentals.csv`
   - Coverage: 107 records, 10 companies, 2019-2025
   - Columns: ticker, fyear, revenue, ebitda, net_income, capex, depreciation, total_assets, total_debt, etc.

2. **USS Historical Data** (existing)
   - Loaded via `data_loader.py`: `load_income_statement()`, `load_balance_sheet()`
   - Coverage: Multi-decade historical data (1990s-present)
   - Format: Excel files with year columns

---

## Data Quality & Limitations

### Data Coverage by Metric
| Metric | Coverage | Confidence Level |
|--------|----------|------------------|
| Net Income | 93.5% | High |
| CapEx | 93.5% | High |
| Depreciation | 93.5% | High |
| Total Assets | 93.5% | High |
| Total Debt | 100% | High |
| Revenue | 53.3% | Medium |
| EBITDA | 53.3% | Medium |
| EBIT | 53.3% | Medium |
| Margins | 53.3% | Medium |

### Missing Data Strategy
- **Skip companies with insufficient data:** Require ≥2 data points for CAGR
- **Display "N/A" clearly:** No imputation or estimation
- **Report company counts:** E.g., "based on 7 of 10 companies"
- **Transparent communication:** Show data availability in captions

### Known Limitations
1. **Revenue/EBITDA partial coverage:** Only ~53% of company-years
2. **NISTF (Nippon Steel) minimal data:** Limited WRDS coverage
3. **Historical only:** No forward projections
4. **Annual data only:** No quarterly granularity
5. **Fiscal year variations:** Mix of Dec-31 and Aug-31 year-ends
6. **Peer data starts 2019:** Long-term analysis is USS-only pre-2019
7. **USS historical quality:** Older periods may have formatting inconsistencies

---

## Testing Strategy

### Unit Tests (Manual Python)
```python
from benchmark_data import BenchmarkData
import pandas as pd

benchmark = BenchmarkData()

# Test 1: Data loading
df = benchmark._get_wrds_fundamentals()
assert len(df) > 100, "WRDS data should have 100+ records"

# Test 2: USS timeseries
uss_df = benchmark.get_uss_timeseries(start_year=2019)
assert len(uss_df) >= 5, "USS should have 5+ years"

# Test 3: CAGR calculation accuracy
values = pd.Series([100, 110, 121])
cagr = benchmark.calculate_cagr(values, 2)
assert abs(cagr - 0.10) < 0.01, "CAGR should be ~10%"

# Test 4: Multi-year analysis
growth = benchmark.get_multiyear_growth_analysis(
    metrics=['revenue', 'net_income'],
    periods=[(2021, 2023)]
)
assert len(growth) > 0, "Should return growth stats"
```

### Dashboard Integration Test
1. Run: `streamlit run interactive_dashboard.py`
2. Navigate to "Multi-Year Growth & Profitability Analysis"
3. Verify:
   - ✅ CAGR bar charts display correctly
   - ✅ USS highlighted in red, peers in blue
   - ✅ Metric selector functional
   - ✅ Period tabs work (3yr, 5yr, 6yr)
   - ✅ Peer median reference line appears
   - ✅ Statistics display below charts
   - ✅ Trend lines show historical values
   - ✅ **Rolling period chart shows CAGR evolution**
   - ✅ **USS long-term chart shows pre-2019 periods**
   - ✅ Summary table displays all data

### Excel Export Test
1. Generate export from dashboard
2. Open "Multi-Year Peer Analysis" sheet
3. Verify:
   - ✅ Historical values table (2019-2024)
   - ✅ USS row first and highlighted
   - ✅ CAGR tables with proper formatting
   - ✅ **Rolling period table shows evolution**
   - ✅ **USS long-term table with note about peer unavailability**
   - ✅ Conditional formatting (green/red)
   - ✅ Peer statistics (Median, Q1, Q3)
   - ✅ No Excel formula errors

### Data Quality Validation
```python
# Check coverage
df = benchmark._get_wrds_fundamentals()
for col in ['revenue', 'ebitda', 'net_income', 'capex', 'total_assets']:
    coverage = df[col].notna().sum() / len(df) * 100
    print(f"{col}: {coverage:.1f}% coverage")

# Expected output:
# revenue: 53.3% coverage
# ebitda: 53.3% coverage
# net_income: 93.5% coverage
# capex: 93.5% coverage
# total_assets: 93.5% coverage
```

---

## Expected Outcomes

### Dashboard Enhancements
- **New section** with 6 subsections after peer benchmarking
- **Interactive charts** showing USS vs peer growth across multiple dimensions:
  - Point-in-time comparisons (3yr, 5yr, 6yr)
  - Historical value trends (2019-2024)
  - **Rolling period evolution (shows acceleration/deceleration)**
  - **USS long-term history (1990s-2020s)**
  - Consolidated summary table
- **Color-coded visualizations** for quick insight
- **Transparent data quality** reporting

### Excel Export Enhancements
- **13th sheet:** "Multi-Year Peer Analysis"
- **5+ metrics analyzed:** Revenue, EBITDA, Net Income, CapEx, Total Assets
- **4 table types per metric:**
  1. Historical values (2019-2024)
  2. Point-in-time CAGRs
  3. **Rolling period CAGRs (NEW)**
  4. **USS long-term historical (NEW)**
- **Professional formatting** with conditional styling
- **Peer benchmarks** where available

### Performance Targets
- Dashboard section loads in <3 seconds
- Excel export adds <2 seconds to total time
- CAGR calculations accurate to 2 decimal places

---

## Implementation Effort Estimate

| Phase | File | Lines of Code | Complexity | Effort |
|-------|------|---------------|------------|---------|
| 1 | benchmark_data.py | ~500 | Medium | 1-2 days |
| 2 | interactive_dashboard.py | ~350 | Medium | 1-2 days |
| 3 | export_model.py | ~286 | Medium | 1 day |
| Testing & Integration | All | - | Medium | 1 day |
| **Total** | **3 files** | **~1,136 lines** | - | **4-6 days** |

---

## Dependencies & Prerequisites

**Required:**
- ✅ WRDS peer fundamentals data cached (`peer_fundamentals.csv`)
- ✅ USS historical financial statements (Excel files)
- ✅ Existing `benchmark_data.py` module
- ✅ Existing dashboard and export infrastructure

**Optional:**
- Unit test framework (pytest) for automated testing
- Data validation scripts

---

## Future Enhancements (Beyond Initial Scope)

1. **Quarterly CAGRs:** If quarterly data becomes available
2. **Segment-level growth:** Compare USS segments vs peer segments
3. **Forward-looking growth:** Integrate analyst consensus estimates
4. **Statistical significance testing:** Determine if USS vs peer differences are meaningful
5. **Industry benchmarking:** Add broader steel/materials industry indices
6. **Automated data refresh:** Schedule WRDS data updates
7. **Interactive scenario analysis:** "What if USS grew at peer median rate?"

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| USS historical data parsing errors | Medium | Medium | Robust error handling, fallback to NaN |
| WRDS data cache missing | Low | High | Auto-fetch from API, clear error messages |
| Revenue/EBITDA gaps affect analysis | High | Medium | Focus on high-confidence metrics, transparent reporting |
| Performance issues with large datasets | Low | Low | Efficient pandas operations, caching |
| Excel export size/performance | Low | Low | Conditional formatting only, no duplicate data |

---

## Success Metrics

### Functional Success
- ✅ All 8 benchmark_data methods implemented and tested
- ✅ Dashboard section loads without errors
- ✅ Excel sheet generates correctly
- ✅ CAGR calculations mathematically accurate
- ✅ Rolling period analysis shows evolution trends
- ✅ USS long-term historical shows decades of data

### Business Success
- Users can quickly identify USS competitive positioning
- Growth trends (acceleration/deceleration) are visually clear
- Excel export enables offline analysis and presentations
- Analysis supports investment decision making on merger

### Performance Success
- Dashboard section loads in <3 seconds
- Excel generation adds <2 seconds
- No memory issues with full dataset

---

## Implementation Priority Justification

**Why High Priority:**
1. **Direct merger analysis value:** Supports go/no-go decision
2. **Data already available:** No new data collection required
3. **Complements existing analysis:** Natural extension of peer benchmarking
4. **Requested by user:** Specifically asked for multi-year and rolling period analysis

**Why Not Immediate Implementation:**
1. Significant code addition (~1,136 lines)
2. Requires thorough testing across metrics
3. Need to validate USS historical data quality
4. Should be implemented after current model stabilizes

---

## Related Documentation

- **Main Plan File:** `/home/vscode/.claude/plans/eager-imagining-cosmos.md`
- **WRDS Data:** `/workspaces/claude-in-docker/FinancialModel/local/wrds_cache/peer_fundamentals.csv`
- **Benchmark Module:** `/workspaces/claude-in-docker/FinancialModel/benchmark_data.py`
- **Dashboard:** `/workspaces/claude-in-docker/FinancialModel/interactive_dashboard.py`
- **Excel Export:** `/workspaces/claude-in-docker/FinancialModel/export_model.py`

---

**Last Updated:** 2026-01-28
**Status:** Ready for implementation when prioritized
**Stakeholder Approval:** Pending
