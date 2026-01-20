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

### Option 2: Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Deploy `interactive_dashboard.py`

## Project Structure

### Core Model Files

| File | Description |
|------|-------------|
| `price_volume_model.py` | Main DCF model with Price x Volume methodology |
| `interactive_dashboard.py` | Streamlit dashboard interface |
| `requirements.txt` | Python dependencies |

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

| Scenario | Description | USS Value |
|----------|-------------|-----------|
| Base Case | Mid-cycle pricing, BR2 only | $50/share |
| Conservative | Downside stress test | $25/share |
| Wall Street | Barclays/Goldman consensus | $34/share |
| Management | December 2023 projections | $38/share |
| Nippon Commitments | Full $14B investment program | $69/share |

### Valuation Methodology
- 10-year explicit DCF forecast (2024-2033)
- Segment-level Price x Volume model
- Terminal value via Gordon Growth and Exit Multiple
- Interest Rate Parity (IRP) adjustment for cross-border valuation

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
