# USS / Nippon Steel Merger Financial Model

Interactive DCF valuation model analyzing the proposed merger between United States Steel Corporation and Nippon Steel.

## Quick Start

### Option 1: Run Locally

```bash
# Clone the repository
git clone <repository-url>
cd FinancialModel

# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run interactive_dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Option 2: Run Sensitivity Analysis Dashboard

```bash
# Run the sensitivity analysis dashboard
streamlit run sensitivity_dashboard.py
```

This dashboard provides:
- M&A comparables reference (precedent transactions + public peers)
- 2D sensitivity grids (EBITDA×Multiple, HRC×Volume, Margin×WACC)
- Value driver tornado charts
- Scenario comparison (8 scenarios)
- Real-time valuation with adjustable parameters

### Option 3: Generate Static Reports

```bash
# Generate all sensitivity analysis reports
python ma-precedents/scripts/generate_sensitivity_report.py
```

Outputs:
- `ma-precedents/outputs/comparables_summary.md` - M&A and peer comparables tables
- `ma-precedents/outputs/comprehensive_sensitivity_report.md` - Sensitivity analysis
- `ma-precedents/outputs/unified_sensitivity_report.md` - Master report combining all analyses
- `ma-precedents/outputs/*.xlsx` - Excel workbooks (4-8 sheets each)
- `ma-precedents/outputs/charts/*.png` - 9 publication-quality charts

### Option 4: Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Deploy `interactive_dashboard.py` or `sensitivity_dashboard.py`

## Project Structure

### Core Model Files

| File | Description |
|------|-------------|
| `price_volume_model.py` | Main DCF model with Price x Volume methodology |
| `interactive_dashboard.py` | Streamlit dashboard interface |
| `sensitivity_dashboard.py` | Streamlit sensitivity analysis dashboard |
| `wacc-calculations/` | WACC calculation module with verified inputs and audit trail |
| `requirements.txt` | Python dependencies |

### Sensitivity Analysis Tools

| File | Description |
|------|-------------|
| `ma-precedents/scripts/generate_comparables_summary.py` | M&A transaction and peer comparables analysis |
| `ma-precedents/scripts/comprehensive_sensitivity_analysis.py` | Multi-dimensional sensitivity and scenario analysis |
| `ma-precedents/scripts/generate_sensitivity_report.py` | Master report generator (runs all analyses) |
| `ma-precedents/outputs/` | Generated reports, Excel workbooks, and charts |

### Analysis Documents

| Document | Purpose |
|----------|---------|
| `EXECUTIVE_SUMMARY.md` | One-page deal overview |
| `SCENARIO_ASSUMPTIONS.md` | Detailed assumptions for each scenario |
| `SENSITIVITY_ANALYSIS.md` | Sensitivity tables and tornado analysis |
| `RISKS_AND_CHALLENGES.md` | Risk assessment framework |
| `USS_STANDALONE_ANALYSIS.md` | What-if analysis without merger |

### Supporting Files

| File | Description |
|------|-------------|
| `Nippon_USS_Merger_Model_v14.xlsx` | Source data (2023 segment financials) |
| `NSA_Investment_Program_Analysis.md` | NSA investment commitments detail |

## Key Features

### Interactive Dashboard
- Scenario selection (Base Case, Conservative, Wall Street, Management, Nippon Commitments)
- Steel price factor adjustment (70%-120%)
- WACC sensitivity slider
- Execution factor for investment program (50%-100%)
- USS vs Nippon valuation perspective toggle

### Scenarios Modeled

| Scenario | Steel Prices | WACC | Key Assumptions | Probability | USS Value |
|----------|-------------|------|-----------------|-------------|-----------|
| **Severe Downturn** | 0.70x, -2% | 13.5% | Recession: 2009/2015/2020 conditions | 25% | ~$0/share* |
| **Downside** | 0.85x flat | 12.0% | Weak markets, flat pricing | 30% | $15/share |
| **Base Case** | 0.90x, +1% | 10.9% | Mid-cycle, modest growth | 30% | $38/share |
| **Above Average** | 0.95x, +1.5% | 10.9% | Strong cycle, good growth | 10% | $67/share |
| **Optimistic** | 1.00x, +2% | 10.9% | Sustained favorable markets | 5% | $97/share |
| Wall Street | 0.97x flat | 12.5% | Barclays/Goldman calibrated ($39-52 range) | - | $46/share |
| Nippon Case | 0.95x | 10.5% | $14B CapEx, all 6 projects | - | $47/share** |

*Severe downturn produces negative equity value (floored at $0)
**Baseline NSA scenario; value increases with execution factor and synergies

**Probability-Weighted Expected Value:** Varies based on scenario mix (typically $20-35/share range)

### Sensitivity Analysis Features

**M&A Comparables Analysis:**
- 5 steel M&A precedent transactions (2018-2021) with EV/EBITDA multiples of 5.6x-6.0x
- 8 public peer companies (EAF: 7.8x median, Integrated: 4.7x median)
- Technology premium analysis (EAF vs Integrated mills)
- Historical and current valuation multiples

**Multi-Dimensional Sensitivity:**
- **2D Grids**: EBITDA×Multiple, HRC×Volume, Margin×WACC
- **Tornado Charts**: Value drivers ranked by elasticity (±10% perturbation)
- **Scenario Analysis**: 8 scenarios from Extreme Downside ($22) to Extreme Upside ($188)
- **Dual Perspective**: USS standalone vs Nippon acquirer (with synergies)

**Key Findings:**
- Base Case: USS $65 standalone, Nippon $78 with synergies
- Nippon $55 offer represents 18-32% premium vs precedent M&A multiples
- Top value drivers: Margins (±$14/share), HRC price (±$11/share), WACC (±$19/share)
- Downside protection: Severe Downturn still delivers $41/share (Nippon)
- Upside potential: NSA Full Execution could reach $118/share

### Valuation Methodology
- 10-year explicit DCF forecast (2024-2033)
- Segment-level Price x Volume model
- Terminal value via Gordon Growth and Exit Multiple
- Interest Rate Parity (IRP) adjustment for cross-border valuation
- Verified WACC calculations with audit trail (USS: 10.70%, Nippon USD: 7.95%)
- Monte Carlo simulation (26 variables, return-based correlations)

### Comprehensive Correlation Analysis (New)

**All-Variable Correlation Dashboard:**
The Steel Price Sensitivity section now includes a comprehensive correlation analysis showing USS stock price vs. 8 key market variables simultaneously:

- **Correlation Summary Table:** All 8 variables ranked by correlation strength with USS stock price
  - Steel Prices: HRC US, CRC US, OCTG US
  - Input Costs: Scrap PPI
  - End Markets: Housing Starts, Auto Production
  - Economic Indicators: ISM PMI, Rig Count

- **Full-Width Correlation Charts:** All 8 dual-axis charts displayed in a single view
  - Each chart shows variable (left axis) vs USS stock price (right axis)
  - Charts sorted by correlation strength (strongest first)
  - 550px height for easy readability
  - Annual average data with historical correlation coefficients

**Key Features:**
- **No dropdown menus:** All correlations visible at once for easy comparison
- **Automatic ranking:** Variables sorted by absolute correlation strength
- **Strength indicators:** Strong (|r| > 0.7), Moderate (0.4-0.7), Weak (< 0.4)
- **Clean design:** No emojis, professional presentation
- **Full-width layout:** Charts use entire screen width for optimal visibility

**Typical Correlations Found:**
- HRC US, CRC US: Strong positive (r > 0.7) - primary steel prices drive equity value
- Housing Starts, Auto Production: Moderate positive (r = 0.4-0.7) - end market demand
- Scrap PPI: Moderate positive (r = 0.4-0.7) - input costs correlated with output prices
- ISM PMI, Rig Count: Variable strength - broader economic and sector-specific indicators

**Interactive Price Overlays:**
- Add steel price trends to FCF projection charts (HRC, CRC, HRC EU, OCTG)
- Visualize synergy ramp-up alongside HRC price environment
- Dual-axis charts show relationship between prices and financial metrics

**Documentation:** See [`docs/PRICE_CORRELATION_QUICK_START.md`](docs/PRICE_CORRELATION_QUICK_START.md) for usage details.

**Test Suite:**
```bash
# Run price correlation unit tests
pytest tests/test_price_correlation.py -v

# Run integration tests
python test_price_correlation_integration.py
```

## Model Outputs

The dashboard displays:
- Share price valuations (USS and Nippon perspectives)
- 10-year FCF projections by segment
- EBITDA margins and revenue trends
- Scenario comparison charts
- Sensitivity analysis

## Data Sources

- USS 10-K FY2023 (segment disclosures)
- Barclays/Goldman Sachs fairness opinions (December 2023)
- NSA Investment Program commitments (May 2025)
- Platts steel price benchmarks

## Requirements

- Python 3.9+
- See `requirements.txt` for package dependencies

## License

Internal use only. Contains proprietary financial analysis.

---

RAMBAS Team Capstone Project | January 2026
