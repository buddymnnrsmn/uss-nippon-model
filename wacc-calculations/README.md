# WACC Calculations

Weighted Average Cost of Capital (WACC) calculations for the USS / Nippon Steel merger analysis.

**Data As Of: December 31, 2023**

All inputs (risk-free rates, betas, market caps, etc.) are collected as of 12/31/2023 to provide a consistent snapshot at the time of the Nippon Steel acquisition announcement (12/18/2023).

## Overview

This module provides bottom-up, verifiable WACC calculations for:
- **USS** (United States Steel Corporation) - US domestic WACC
- **Nippon Steel** - JPY WACC with IRP adjustment to USD
- **Peer Comparison** - Industry benchmarking and cross-validation

## Quick Start

```bash
# Calculate USS WACC
cd /workspaces/claude-in-docker/FinancialModel
python -m wacc-calculations.uss.uss_wacc

# Calculate Nippon WACC
python -m wacc-calculations.nippon.nippon_wacc

# Run peer comparison
python -m wacc-calculations.peer_comparison.peer_wacc_analysis
```

## Module Structure

```
wacc-calculations/
├── README.md                    # This file
├── __init__.py
├── base_wacc.py                 # Base WACC calculator (CAPM + cost of debt)
│
├── nippon/
│   ├── __init__.py
│   ├── nippon_wacc.py           # Nippon Steel WACC with IRP adjustment
│   └── inputs.json              # ** SINGLE SOURCE OF TRUTH ** for Nippon inputs
│
├── uss/
│   ├── __init__.py
│   ├── uss_wacc.py              # USS WACC with analyst comparison
│   └── inputs.json              # ** SINGLE SOURCE OF TRUTH ** for USS inputs
│
└── peer_comparison/
    ├── __init__.py
    └── peer_wacc_analysis.py    # Industry peer benchmarking
```

## Input Architecture

**All inputs are loaded from `inputs.json` files** - the Python code contains NO hardcoded values.

Each `inputs.json` contains:
- **Values**: The actual input values (risk-free rate, beta, etc.)
- **Sources**: Where each value came from (Federal Reserve, Bloomberg, etc.)
- **URLs**: Links to verify the data
- **Verification Checklist**: Items to verify with expected values and status

To modify inputs, edit the JSON files - NOT the Python code.

## Methodology

### WACC Formula

```
WACC = (E/V) × Re + (D/V) × Rd × (1 - T)

Where:
- E = Market value of equity
- D = Market value of debt
- V = E + D (enterprise value)
- Re = Cost of equity
- Rd = Pre-tax cost of debt
- T = Marginal tax rate
```

### Cost of Equity (CAPM)

```
Re = Rf + β × ERP + Size Premium + Country Premium

Where:
- Rf = Risk-free rate (10-year government bond)
- β = Levered equity beta
- ERP = Equity risk premium (5.5% standard)
```

### Cost of Debt

```
Rd = Rf + Credit Spread

Based on:
- Company's credit rating (S&P, Moody's)
- Observed bond yields
- Bank debt rates
```

### Interest Rate Parity (for Nippon)

For cross-border valuations, we convert JPY WACC to USD using IRP:

```
WACC_USD = (1 + WACC_JPY) × (1 + Rf_USD) / (1 + Rf_JPY) - 1
```

This maintains economic equivalence across currencies.

## Key Results (as of 12/31/2023)

### USS WACC

| Component | Value | Source |
|-----------|-------|--------|
| Risk-free rate | 3.88% | 10-Year Treasury (12/29/2023) |
| Beta | 1.45 | Bloomberg consensus |
| ERP | 5.50% | Duff & Phelps |
| Size premium | 1.00% | Duff & Phelps |
| **Cost of Equity** | **12.86%** | Calculated |
| Pre-tax cost of debt | 7.50% | Weighted avg bonds |
| Tax rate | 25.0% | US statutory |
| **After-tax CoD** | **5.62%** | Calculated |
| Market cap | $9,614M | $42.73/share x 225M |
| Total debt | $3,913M | 2023 10-K |
| Equity weight | 71.1% | Market cap / EV |
| Debt weight | 28.9% | Debt / EV |
| **WACC** | **10.76%** | Calculated |

### Nippon WACC

| Component | JPY | USD (IRP) |
|-----------|-----|-----------|
| Risk-free rate | 0.61% | 3.88% |
| Beta | 1.15 | 1.15 |
| ERP | 5.50% | 5.50% |
| Cost of Equity | 6.93% | - |
| Pre-tax CoD | 1.41% | - |
| After-tax CoD | 0.98% | - |
| Equity weight | 60.0% | - |
| Debt weight | 40.0% | - |
| **WACC** | **4.55%** | **7.95%** |

### WACC Advantage

Nippon's lower USD WACC (7.95%) vs USS standalone (10.76%) creates **~280bps valuation advantage**.

## Comparison to Analyst Estimates

| Source | USS WACC Range | Notes |
|--------|---------------|-------|
| Barclays (USS advisor) | 11.5% - 13.5% | Fairness opinion (from proxy) |
| Goldman Sachs | 11.5% - 13.0% | Equity research |
| JP Morgan | 10.0% - 12.0% | Equity research |
| **This Model** | **10.76%** | Bottom-up CAPM |

Model results (10.76%) are at the lower end of analyst ranges, primarily due to:
- Consensus beta (1.45) vs some analysts using 1.5-1.6
- Lower risk-free rate at 12/31/2023 (3.88% vs 4.25%+ in some analyst models)
- Size premium (1%) partially offsets the lower base rate

## Verification Checklist

### USS Inputs
- [ ] 10-Year Treasury yield - [Federal Reserve H.15](https://www.federalreserve.gov/releases/h15/)
- [ ] USS beta - Bloomberg terminal or Yahoo Finance
- [ ] USS credit rating - S&P/Moody's press releases
- [ ] USS bond yields - FINRA TRACE
- [ ] USS market cap - NYSE
- [ ] Analyst WACC estimates - SEC EDGAR (DEFM14A proxy)

### Nippon Inputs
- [ ] 10-Year JGB yield - [Bank of Japan](https://www.boj.or.jp/en/)
- [ ] Nippon beta vs TOPIX - Bloomberg
- [ ] Nippon credit ratings - S&P/Moody's/Fitch/R&I
- [ ] Nippon debt profile - Annual Report (有価証券報告書)
- [ ] JPY/USD exchange rate - for capital structure conversion

## Usage in Model

The WACC calculations integrate with `price_volume_model.py`:

```python
from wacc_calculations.uss import calculate_uss_wacc
from wacc_calculations.nippon import calculate_nippon_wacc

# Get USS WACC (all inputs loaded from inputs.json)
uss_result = calculate_uss_wacc()
print(f"USS WACC: {uss_result.wacc:.2%}")
print(f"Data as of: {uss_result.data_as_of_date}")

# Get Nippon USD WACC (IRP-adjusted)
nippon_result = calculate_nippon_wacc()
print(f"Nippon USD WACC: {nippon_result.usd_wacc:.2%}")

# View full audit trail
audit = uss_result.get_audit_trail()
print(audit)
```

### Viewing Input Sources

```python
from wacc_calculations.uss.uss_wacc import print_input_sources
print_input_sources()  # Shows all inputs with sources and verification status
```

### Sensitivity Analysis (with overrides)

```python
# Override specific inputs for sensitivity analysis
# (overrides are tracked in the audit trail)
result_high_beta = calculate_uss_wacc(levered_beta=1.6)
result_low_rf = calculate_uss_wacc(us_10y=0.035)
```

## Sensitivity Analysis

Both calculators support sensitivity analysis:

```python
from wacc_calculations.uss import USSWACCCalculator

calc = USSWACCCalculator()

# Beta sensitivity
beta_sensitivity = calc.sensitivity_to_beta([1.2, 1.35, 1.45, 1.55, 1.7])
for beta, wacc in beta_sensitivity.items():
    print(f"Beta {beta:.2f}: WACC {wacc:.2%}")
```

## Data Sources

| Data Point | Primary Source | Backup Source |
|------------|---------------|---------------|
| US Treasury yields | Federal Reserve | Bloomberg |
| JGB yields | Bank of Japan | Bloomberg |
| Equity betas | Bloomberg | Capital IQ, Yahoo |
| Credit ratings | S&P, Moody's | Company filings |
| Bond yields | TRACE | Bloomberg |
| ERP | Duff & Phelps | Damodaran |

## Caveats

1. **Beta Estimation**: Different lookback periods and frequencies yield different betas. We use 5-year monthly as standard.

2. **Market Cap Volatility**: USS share price (and thus capital structure weights) fluctuates significantly. WACC should be recalculated at different price levels.

3. **Credit Spread Assumption**: Actual bond yields may differ from rating-implied spreads.

4. **IRP Assumption**: IRP holds in theory but may not perfectly reflect actual currency hedging costs.

5. **Tax Rate**: Effective tax rates may differ from statutory rates used.

## Future Enhancements

- [ ] Real-time market data integration (via Bloomberg API)
- [ ] Monte Carlo simulation of WACC inputs
- [ ] Automatic beta calculation from return data
- [ ] Integration with WRDS for historical analysis
