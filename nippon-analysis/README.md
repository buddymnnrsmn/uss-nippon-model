# Nippon Steel Financial Analysis

Comprehensive financial analysis of Nippon Steel Corporation to assess their capacity to fund and execute the USS acquisition (~$29B total capital deployment).

## Overview

This module provides:
- **Balance sheet analysis** (JPY and USD)
- **Debt profile and credit metrics**
- **Pro forma leverage calculations**
- **Funding gap analysis**
- **Stress testing**
- **Deal capacity verdict**

## Quick Start

```bash
# Test the financial profile module
cd /workspaces/claude-in-docker/uss-nippon-model
python -m nippon-analysis.nippon_financial_profile

# Run full capacity analysis
python -m nippon-analysis.nippon_capacity_analysis
```

## Module Structure

```
nippon-analysis/
├── README.md                          # This file
├── nippon_financial_profile.py        # Core financials, balance sheet, credit metrics
├── nippon_capacity_analysis.py        # Pro forma, funding gap, stress tests
└── data/
    ├── nippon_financials.csv          # Exported historical financials
    ├── pro_forma_metrics.csv          # Pro forma comparison
    ├── funding_gap_analysis.csv       # Funding sources/uses
    ├── stress_tests.csv               # Stress scenario results
    └── peer_comparison.csv            # Global steel peer data
```

## Data Sources

### Primary Sources

| Source | Data Used | Access |
|--------|-----------|--------|
| **Nippon Steel FY2024 Annual Report** | Revenue, EBITDA, Balance Sheet | [IR Library](https://www.nipponsteel.com/en/ir/library/) |
| **Nippon Steel Investor Presentations** | Strategic context, CapEx plans | [IR Library](https://www.nipponsteel.com/en/ir/library/) |
| **S&P Global Ratings** | Credit rating (BBB+) | [S&P Global](https://www.spglobal.com/ratings/) |
| **Moody's Investors Service** | Credit rating (Baa1) | [Moody's](https://www.moodys.com/) |
| **Fitch Ratings** | Credit rating (BBB+) | [Fitch](https://www.fitchratings.com/) |

### Secondary Sources

| Source | Data Used | Access |
|--------|-----------|--------|
| **WRDS Compustat** | Historical fundamentals (when available) | Via `local/wrds_loader.py` |
| **Capital IQ** | Peer company comparisons | Subscription required |
| **USS Merger Proxy (SEC)** | Deal terms, financing commitments | [SEC EDGAR](https://www.sec.gov/edgar) |

### Data Verification

The placeholder data in `get_nippon_placeholder_data()` should be verified against:

1. **Official IR Website**: https://www.nipponsteel.com/en/ir/
2. **Earnings Reports**: 決算短信 (Kessan Tanshin)
3. **Annual Securities Report**: 有価証券報告書 (Yukashoken Hokokusho)

## Key Metrics (FY2024)

### Nippon Steel Corporation

| Metric | JPY (¥B) | USD ($B) | Notes |
|--------|----------|----------|-------|
| Revenue | 8,509 | 56.7 | FY Apr 2023 - Mar 2024 |
| EBITDA | 1,260 | 8.4 | Operating income + D&A |
| Net Income | 621 | 4.1 | |
| Total Debt | 2,320 | 15.5 | |
| Net Debt | 1,870 | 12.5 | Debt - Cash |
| Total Equity | 4,400 | 29.3 | |
| Operating Cash Flow | 980 | 6.5 | |
| Free Cash Flow | 500 | 3.3 | OCF - CapEx |

*Exchange rate: ¥150/USD*

### Credit Metrics

| Metric | Value | Investment Grade Threshold |
|--------|-------|----------------------------|
| Debt/EBITDA | 1.84x | < 3.5x |
| Net Debt/EBITDA | 1.48x | < 3.0x |
| Interest Coverage | 26.3x | > 3.0x |
| Debt/Equity | 0.53x | < 1.0x |

### Credit Ratings

| Agency | Rating | Outlook | Date |
|--------|--------|---------|------|
| S&P Global | BBB+ | Stable | Jun 2024 |
| Moody's | Baa1 | Stable | May 2024 |
| Fitch | BBB+ | Stable | Apr 2024 |
| R&I (Japan) | A | Stable | Jul 2024 |

## Deal Analysis

### Capital Deployment Required

| Component | Amount | Timing |
|-----------|--------|--------|
| USS Acquisition | $14.9B | At close |
| NSA Investment Commitment | $14.0B | Over 5 years |
| **Total** | **$28.9B** | |

### Pro Forma Impact

| Metric | Pre-Deal | Post-Deal (Y1) | Stabilized (Y3) |
|--------|----------|----------------|-----------------|
| Debt/EBITDA | 1.8x | 2.6x | 2.2x |
| Interest Coverage | 26x | 8x | 10x |
| Implied Rating | A- | BBB | BBB+ |

### Funding Sources

| Source | Available | Notes |
|--------|-----------|-------|
| Cash on Hand | ~$1.5B | Use 50% max |
| Operating FCF (5-yr) | ~$16.5B | After dividends |
| Credit Facilities | $4.0B | Undrawn capacity |
| New Debt Capacity | ~$3.0B | To IG threshold |
| Equity Potential | ~$2.5B | 10% of market cap |

### Stress Test Summary

| Scenario | Debt/EBITDA | IG Breach? | Risk Level |
|----------|-------------|------------|------------|
| Base Case | 2.6x | No | Low |
| Downturn (-25% EBITDA) | 3.5x | Borderline | Medium |
| Severe Downturn (-40%) | 4.3x | Yes | High |
| Rate Shock (+200bps) | 2.7x | No | Low |

## Integration with Dashboard

The Nippon analysis is integrated into `interactive_dashboard.py` as the **"Nippon Buyer Capacity Analysis"** section.

Features displayed:
- Deal Capacity Verdict (Yes/Conditional/No)
- Balance Sheet Summary
- Pro Forma Leverage Comparison
- Funding Gap Analysis
- Stress Test Results
- Peer Comparison Table

## Caveats and Limitations

1. **Placeholder Data**: Current financials use estimated values that should be verified against official filings
2. **Exchange Rate Sensitivity**: All USD values depend on JPY/USD rate assumption (¥150)
3. **Financing Assumptions**: Actual deal financing may differ from modeled structure
4. **Synergy Estimates**: Integration benefits are estimates with execution risk
5. **Regulatory Risk**: CFIUS/political factors not quantified

## Future Enhancements

- [ ] Integrate real-time WRDS data when API is configured
- [ ] Add bond maturity schedule analysis
- [ ] Include currency hedging impact
- [ ] Model different financing scenarios
- [ ] Add Monte Carlo stress testing
