# Bloomberg Data Integration

This module integrates 24 Bloomberg datasets into the USS/Nippon Steel financial model, enabling:

1. **Dynamic benchmark prices** - Replace hardcoded 2023 prices with current market data
2. **WACC updates** - Current Treasury yields and credit spreads
3. **Monte Carlo calibration** - Fitted distributions from historical data
4. **Correlation matrix** - Data-driven correlations for simulation
5. **Synergy validation** - EV forecasts to validate assumptions
6. **Tariff model** - Historical price data for Section 232 tariff impact estimation

## Quick Start

```python
from market_data.bloomberg import get_bloomberg_service, is_bloomberg_available

# Check if Bloomberg data is available
if is_bloomberg_available():
    service = get_bloomberg_service()

    # Get current prices
    prices = service.get_current_prices()
    print(f"HRC US: ${prices['hrc_us']:,.0f}/ton")

    # Get current rates
    rates = service.get_current_rates()
    print(f"10Y UST: {rates['risk_free_rate']*100:.2f}%")
```

## Architecture

```
market-data/bloomberg/
├── __init__.py                 # Module exports
├── bloomberg_data_service.py   # Central data service (singleton)
├── price_calibrator.py         # Calibrate benchmark prices
├── wacc_updater.py             # WACC overlay generation
├── monte_carlo_calibrator.py   # MC distribution fitting
└── config.json                 # Configuration mapping
```

## Key Design Decisions

1. **Explicit refresh over auto-update** - Reproducibility requires user control
2. **Overlay pattern for WACC** - Don't modify inputs.json; create Bloomberg overlay
3. **Graceful fallbacks** - Model works identically without Bloomberg data
4. **Dashboard integration** - Status display, manual toggle, price comparison
5. **Config priority** - `distributions_config.json` overrides Bloomberg-fitted parameters

## Bloomberg → Model Variable Mapping

### How Bloomberg Data Feeds Into the 25 MC Variables

| MC Variable | Bloomberg Dataset | File | Mapping |
|-------------|------------------|------|---------|
| `hrc_price_factor` | HRC US Spot | `01_steel_prices/bloomberg_hrc_us_spot_weekly_*.xlsx` | `spot / $738 benchmark` |
| `crc_price_factor` | CRC US Spot | `01_steel_prices/bloomberg_crc_us_spot_weekly_*.xlsx` | `spot / $994 benchmark` |
| `coated_price_factor` | Derived | CRC + $119 spread | `(CRC + 119) / $1,113` |
| `hrc_eu_factor` | HRC EU Spot | `01_steel_prices/bloomberg_hrc_eu_spot_weekly_*.xlsx` | `(EUR × FX) / $611` |
| `octg_price_factor` | OCTG US Spot | `01_steel_prices/bloomberg_octg_us_spot_weekly_*.xlsx` | `spot / $2,388` |
| `flat_rolled_volume` | Capacity Utilization | `01_steel_prices/bloomberg_capacity_us_aisi_weekly_*.xlsx` | `util / mean_util` |
| `mini_mill_volume` | Derived | Capacity × 0.75 damping | Less cyclical than FR |
| `usse_volume` | EU Steel Demand | `06_synergy_validation/bloomberg_steel_demand_us_eu_*.xlsx` | EU demand index |
| `tubular_volume` | Rig Count | `04_energy/bloomberg_rig_count_us_weekly_*.xlsx` | `rigs / mean_rigs` |
| `uss_wacc` | UST 10Y + BBB Spread | `02_rates_credit/bloomberg_ust_10y_*.xlsx` + `spread_bbb_*.xlsx` | CAPM composite |
| `us_10yr` | UST 10Y | `02_rates_credit/bloomberg_ust_10y_daily_*.xlsx` | Direct read |
| `nippon_erp` | — | Expert judgment | Not Bloomberg-sourced |
| `terminal_growth` | — | Expert judgment | Not Bloomberg-sourced |
| `exit_multiple` | Peer Comps | `references/steel_comps/` (SEC filings) | Peer EV/EBITDA |
| `gary_works_execution` | — | Expert judgment | Not Bloomberg-sourced |
| `mon_valley_execution` | — | Expert judgment | Not Bloomberg-sourced |
| `operating_synergy_factor` | — | M&A literature | Not Bloomberg-sourced |
| `revenue_synergy_factor` | — | M&A literature | Not Bloomberg-sourced |
| `working_capital_efficiency` | — | Peer data | Not Bloomberg-sourced |
| `capex_intensity_factor` | — | Expert judgment | Not Bloomberg-sourced |
| `annual_price_growth` | HRC Futures Curve | `01_steel_prices/bloomberg_hrc_us_futures_daily_*.xlsx` | Implied growth rate |
| `flat_rolled_margin_factor` | Peer Fundamentals | `local/wrds_cache/peer_fundamentals.csv` | Margin variation |
| `tariff_probability` | — | Political analysis | Not Bloomberg-sourced |
| `tariff_rate_if_changed` | — | Policy analysis | Not Bloomberg-sourced |
| `margin_factor` | Peer Fundamentals | `local/wrds_cache/peer_fundamentals.csv` | Overall margin |

**Summary:** 12 of 25 variables are Bloomberg-sourced; 13 use expert judgment, M&A literature, or WRDS peer data.

### Through-Cycle Benchmarks (from Bloomberg)

The model uses through-cycle equilibrium prices as baselines (not spot):

| Product | Through-Cycle | Formula | 2023 Bloomberg Avg |
|---------|--------------|---------|-------------------|
| HRC US | $738/ton | Avg(Pre-COVID $625, Post-Spike $850) | $916 |
| CRC US | $994/ton | Avg(Pre-COVID $820, Post-Spike $1,130) | $1,127 |
| Coated | $1,113/ton | Avg(Pre-COVID $920, Post-Spike $1,266) | $1,263 |
| HRC EU | $611/ton | Avg(Pre-COVID $512, Post-Spike $710) | $717 |
| OCTG | $2,388/ton | Avg(Pre-COVID $1,350, Post-Spike $3,228) | $2,750 |

Factor 1.0x = through-cycle normal. The 2023 averages were ~1.13-1.24x.

## Tariff Model Integration

### How Bloomberg Data Supports the Tariff Model

The Section 232 tariff adjustment function uses Bloomberg historical prices to estimate price uplift:

1. **Empirical estimation:** Compare HRC prices before tariffs (pre-2018) vs after (2018+), controlling for scrap costs and demand
2. **Conservative uplift:** 15% HRC price uplift at 25% tariff (between OLS regression 7% and raw empirical 18%)
3. **Linear scaling:** `adjustment = uplift × (rate - 0.25) / 0.25`

### Tariff-Adjusted Price Factors

At different tariff rates, the model adjusts price factors multiplicatively:

| Tariff | HRC Adj | CRC Adj | Coated Adj | EU Adj | OCTG Adj |
|--------|---------|---------|------------|--------|----------|
| 0% | 0.850 | 0.850 | 0.880 | 0.955 | 0.910 |
| 10% | 0.910 | 0.910 | 0.928 | 0.973 | 0.946 |
| 25% | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 50% | 1.150 | 1.150 | 1.120 | 1.045 | 1.090 |

### Bloomberg Datasets Used for Tariff Calibration

| Dataset | Purpose | File |
|---------|---------|------|
| HRC US Spot (weekly) | Pre/post tariff price comparison | `bloomberg_hrc_us_spot_weekly_*.xlsx` |
| Scrap US PPI (monthly) | Cost control variable | `bloomberg_scrap_us_ppi_monthly_*.xlsx` |
| Capacity Utilization | Demand control variable | `bloomberg_capacity_us_aisi_weekly_*.xlsx` |
| HRC EU Spot | International pass-through | `bloomberg_hrc_eu_spot_weekly_*.xlsx` |

## Usage

### Price Integration

```python
from market_data.bloomberg import get_current_benchmark_prices

# Get current prices (returns None if Bloomberg unavailable)
prices = get_current_benchmark_prices()

if prices:
    # Use Bloomberg prices
    hrc_price = prices['hrc_us']  # $/ton
else:
    # Fall back to through-cycle defaults
    hrc_price = 738  # Through-cycle baseline
```

### WACC Overlay

```python
from market_data.bloomberg import get_wacc_overlay

overlay = get_wacc_overlay()
if overlay:
    print(f"Current 10Y UST: {overlay.risk_free_rate*100:.2f}%")
    print(f"Suggested CoD: {overlay.suggested_cost_of_debt*100:.2f}%")

    # Compare to verified inputs
    from market_data.bloomberg import compare_to_verified_inputs
    comparison = compare_to_verified_inputs()
    for field, data in comparison.items():
        print(f"{field}: Bloomberg={data['bloomberg']:.4f}, Verified={data['verified']:.4f}")
```

### Monte Carlo Calibration

```python
from market_data.bloomberg import get_calibrated_distributions

distributions = get_calibrated_distributions()
if distributions:
    hrc_dist = distributions['hrc_price_factor']
    print(f"HRC volatility: {hrc_dist['params']['std']*100:.1f}%")
```

**Important:** The config file (`distributions_config.json`) takes priority over Bloomberg-fitted parameters. Bloomberg provides raw historical fits; the config has deliberate calibration choices (e.g., through-cycle σ excluding COVID spike).

### Dashboard Integration

The Streamlit dashboard automatically shows Bloomberg status in the sidebar when available:
- Status indicator (green/yellow/red based on data freshness)
- Data as-of date
- Refresh button
- "Use Bloomberg Prices" toggle
- Price comparison table

## Available Datasets (24 total)

### Price Data (7 files)

| File | Content | Frequency | Period |
|------|---------|-----------|--------|
| `bloomberg_hrc_us_spot_weekly_*.xlsx` | US HRC Midwest spot | Weekly | 2015-2026 |
| `bloomberg_hrc_us_futures_daily_*.xlsx` | US HRC futures curve | Daily | 2008-2026 |
| `bloomberg_crc_us_spot_weekly_*.xlsx` | US CRC spot | Weekly | 2015-2026 |
| `bloomberg_hrc_eu_spot_weekly_*.xlsx` | EU HRC spot (EUR) | Weekly | 2014-2026 |
| `bloomberg_octg_us_spot_weekly_*.xlsx` | US OCTG spot | Weekly | 2015-2026 |
| `bloomberg_scrap_us_ppi_monthly_*.xlsx` | US Scrap PPI | Monthly | 2000-2026 |
| `bloomberg_capacity_us_aisi_weekly_*.xlsx` | US capacity utilization | Weekly | 1995-2026 |

### Rate & Credit Data (5 files)

| File | Content | Frequency | Period |
|------|---------|-----------|--------|
| `bloomberg_ust_10y_daily_*.xlsx` | 10Y Treasury yield | Daily | 1990-2026 |
| `bloomberg_ust_30y_daily_*.xlsx` | 30Y Treasury yield | Daily | 1990-2026 |
| `bloomberg_spread_bbb_daily_*.xlsx` | BBB credit spread | Daily | 2000-2026 |
| `bloomberg_spread_hy_daily_*.xlsx` | High yield spread | Daily | 2000-2026 |
| `bloomberg_sofr_daily_*.xlsx` | SOFR rate | Daily | 2018-2026 |

### Demand Drivers (5 files)

| File | Content | Frequency |
|------|---------|-----------|
| `bloomberg_auto_production_us_monthly_*.xlsx` | US auto production | Monthly |
| `bloomberg_auto_sales_saar_us_monthly_*.xlsx` | US auto sales (SAAR) | Monthly |
| `bloomberg_housing_starts_us_monthly_*.xlsx` | US housing starts | Monthly |
| `bloomberg_ism_pmi_us_monthly_*.xlsx` | ISM Manufacturing PMI | Monthly |
| `bloomberg_macro_aggregate_us_*.xlsx` | Macro aggregate | Annual |

### Energy (2 files)

| File | Content | Frequency |
|------|---------|-----------|
| `bloomberg_wti_crude_daily_*.xlsx` | WTI crude oil | Daily |
| `bloomberg_rig_count_us_weekly_*.xlsx` | US rig count | Weekly |

### Equities (2 files)

| File | Content | Frequency |
|------|---------|-----------|
| `bloomberg_stock_uss_daily_*.xlsx` | USS stock price | Daily |
| `bloomberg_stock_nippon_daily_*.xlsx` | Nippon Steel ADR | Daily |

### Synergy Validation (3 files)

| File | Content | Frequency |
|------|---------|-----------|
| `bloomberg_ev_forecast_us_annual_*.xlsx` | EV forecasts | Annual |
| `bloomberg_steel_demand_us_eu_*.xlsx` | Steel demand US/EU | Annual |
| `bloomberg_steel_costs_us_eu_*.xlsx` | Steel cost indices | Annual |

## Configuration

Edit `market-data/bloomberg/config.json` to:

### Enable/Disable Bloomberg

```json
{
    "bloomberg_enabled": true
}
```

### Set Staleness Thresholds

```json
{
    "staleness_thresholds_days": {
        "prices": 7,
        "rates": 7,
        "macro": 30,
        "forecasts": 90
    }
}
```

## API Reference

### BloombergDataService

```python
class BloombergDataService:
    """Singleton service for Bloomberg market data"""

    def is_available() -> bool:
        """Check if data is loaded and enabled"""

    def get_status() -> dict:
        """Get comprehensive status of all datasets"""

    def refresh() -> None:
        """Reload all data from disk"""

    def get_current_prices() -> Dict[str, float]:
        """Get current benchmark prices"""

    def get_current_rates() -> Dict[str, float]:
        """Get current interest rates and spreads"""

    def get_price_stats(key: str) -> TimeSeriesStats:
        """Get statistics for a price series"""

    def get_historical_prices(key, start, end) -> pd.DataFrame:
        """Get historical price data"""

    def get_correlation_matrix() -> pd.DataFrame:
        """Get pre-computed correlation matrix"""
```

### Price Calibrator

```python
get_current_benchmark_prices() -> Optional[Dict[str, float]]
get_scenario_price_factors(scenario_type: str) -> Optional[Dict[str, float]]
compare_current_to_historical() -> Optional[Dict[str, Dict]]
get_price_comparison_table() -> List[PriceComparison]
```

### WACC Updater

```python
get_wacc_overlay() -> Optional[WACCBloombergOverlay]
calculate_beta_from_stock_data() -> Tuple[float, float]
compare_to_verified_inputs() -> Optional[Dict[str, Dict]]
generate_wacc_overlay_report() -> str
```

### Monte Carlo Calibrator

```python
get_calibrated_distributions() -> Optional[Dict[str, Dict]]
get_calibrated_correlation_matrix() -> Optional[pd.DataFrame]
calibrate_steel_price_distributions() -> Optional[Dict[str, CalibratedDistribution]]
export_for_monte_carlo_engine() -> Optional[Dict]
```

## Rollback Strategy

### 1. Config Disable
```json
{
    "bloomberg_enabled": false
}
```

### 2. Session Toggle
Uncheck "Use Bloomberg" in the dashboard sidebar.

### 3. Module Removal
Delete the `market-data/bloomberg/` folder. The model will use defaults.

### 4. Git Revert
Each phase was committed separately for easy rollback.

## Testing

```bash
pytest tests/test_bloomberg_integration.py -v
```

Key test scenarios:
- Data service loading and singleton behavior
- Price calibration and comparison
- WACC overlay generation
- Monte Carlo calibration
- Graceful fallbacks when Bloomberg unavailable
- Configuration validation

**Known issue:** 5 pre-existing test failures in `test_bloomberg_integration.py` related to scenario calibrator using 0.94x internally. Not caused by tariff or recalibration changes.

## Related Documentation

| Document | Content |
|----------|---------|
| `monte_carlo/VARIABLE_MANIFEST.md` | Master index of all 25 MC variables |
| `monte_carlo/DISTRIBUTION_CALIBRATION.md` | Full calibration methodology |
| `monte_carlo/distributions_config.json` | Programmatic variable parameters |
| `market-data/BLOOMBERG_DATA_GUIDE.md` | Bloomberg Terminal export commands |
| `documentation/SCENARIO_ASSUMPTIONS.md` | Deterministic scenario parameters |
| `tests/test_tariff_integration.py` | Tariff model tests (34 passing) |
| `scripts/backtest_tariff_model.py` | Tariff model validation (5/5 checks) |

---

### Version History

- **1.2.0** (2026-02-06) - Tariff model integration, through-cycle benchmark rebasing, 25-variable mapping
- **1.1.0** (2026-02-05) - Config priority over Bloomberg, distribution tightening
- **1.0.0** - Initial release with 24 datasets, price/WACC/MC integration
