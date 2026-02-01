# Bloomberg Terminal Data Gathering Guide

## USS / Nippon Steel Merger Model - Monte Carlo Calibration

**Purpose:** Gather historical data for Monte Carlo simulation calibration, correlation analysis, and scenario validation.

**Estimated Time:** 2-3 hours for complete data pull

---

## Prerequisites

1. Bloomberg Terminal access
2. Bloomberg Excel Add-In installed (for bulk exports)
3. Export folder ready: `bloomberg_data/exports/`

---

## Phase 1: Steel Prices (Critical - Do First)

### Step 1.1: US HRC Midwest (Primary Price Driver)

```
Terminal Command: MWST1MCA Index <GO>
```

1. Type `MWST1MCA Index` and press `<GO>`
2. Press `GP` for price graph
3. Click **Actions** → **Export to Excel**
4. Set date range: `01/01/1990` to `12/31/2025`
5. Select: Daily frequency
6. Save as: `exports/steel_hrc_us_daily.xlsx`

**Alternative via Excel Add-In:**
```excel
=BDH("MWST1MCA Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P","Days=A")
```

### Step 1.2: US CRC (Cold-Rolled Coil)

```
Terminal Command: MWST1MCR Index <GO>
```

1. Follow same steps as HRC
2. Save as: `exports/steel_crc_us_daily.xlsx`

### Step 1.3: US Hot-Dip Galvanized (Coated)

```
Terminal Command: MWST1MHD Index <GO>
```

1. Follow same steps
2. Save as: `exports/steel_hdg_us_daily.xlsx`

### Step 1.4: EU HRC

```
Terminal Command: SPGSTHRC Index <GO>
```

If not available, try:
```
Terminal Command: MWST1EHR Index <GO>
```

1. Save as: `exports/steel_hrc_eu_daily.xlsx`

### Step 1.5: OCTG (Oil Country Tubular Goods)

```
Terminal Command: ALLX OCTG <GO>
```

1. Search for OCTG seamless pipe prices
2. Select most liquid contract
3. Export daily data from 2005-2025
4. Save as: `exports/steel_octg_daily.xlsx`

### Step 1.6: Scrap Prices (Cost Input)

```
Terminal Command: STLSCRBR Index <GO>
```

1. Export daily data from 2000-2025
2. Save as: `exports/scrap_busheling_daily.xlsx`

### Step 1.7: Iron Ore (Cost Input)

```
Terminal Command: IABORUSE Index <GO>
```

1. Export daily data from 2005-2025
2. Save as: `exports/iron_ore_62fe_daily.xlsx`

### Step 1.8: Natural Gas (Energy Cost)

```
Terminal Command: NG1 Comdty <GO>
```

1. Export daily data from 1990-2025
2. Save as: `exports/natgas_henry_hub_daily.xlsx`

### Step 1.9: Coking Coal (BF Feedstock)

```
Terminal Command: XAL1 Comdty <GO>
```

Or search: `ALLX MET COAL <GO>`

1. Export daily data from 2010-2025
2. Save as: `exports/coking_coal_daily.xlsx`

---

## Phase 2: Interest Rates & Credit Spreads

### Step 2.1: US Treasury Rates

```
Terminal Commands:
USGG10YR Index <GO>   (10-Year)
USGG30YR Index <GO>   (30-Year)
```

1. Export each separately, daily, 1990-2025
2. Save as: `exports/ust_10y_daily.xlsx`, `exports/ust_30y_daily.xlsx`

### Step 2.2: Japan Government Bonds

```
Terminal Commands:
JGBS10 Index <GO>   (10-Year JGB)
JGBS30 Index <GO>   (30-Year JGB)
```

1. Export each separately, daily, 1990-2025
2. Save as: `exports/jgb_10y_daily.xlsx`, `exports/jgb_30y_daily.xlsx`

### Step 2.3: Credit Spreads

```
Terminal Commands:
LUACOAS Index <GO>    (BBB Corporate Spread)
LF98OAS Index <GO>    (High Yield Spread)
```

1. Export daily, 2000-2025
2. Save as: `exports/credit_spread_bbb_daily.xlsx`, `exports/credit_spread_hy_daily.xlsx`

### Step 2.4: SOFR Rate (LBO Pricing)

```
Terminal Command: SOFRRATE Index <GO>
```

1. Export daily, 2018-2025
2. Save as: `exports/sofr_rate_daily.xlsx`

### Step 2.5: Fed Funds Rate

```
Terminal Command: FDTR Index <GO>
```

1. Export daily, 1990-2025
2. Save as: `exports/fed_funds_daily.xlsx`

---

## Phase 3: Peer Company Data

### Step 3.1: Peer Company List

| Ticker | Company | Type |
|--------|---------|------|
| X US | U.S. Steel | Target |
| NUE US | Nucor | Primary Comp |
| STLD US | Steel Dynamics | Primary Comp |
| CLF US | Cleveland-Cliffs | Primary Comp |
| CMC US | Commercial Metals | Secondary |
| 5401 JP | Nippon Steel | Acquirer |
| MT NA | ArcelorMittal | Global |
| PKX US | POSCO (ADR) | Global |

### Step 3.2: Pull Financials for Each Peer

For each ticker, run:

```
Terminal Command: {TICKER} Equity FA <GO>
```

Example: `NUE US Equity FA <GO>`

**Export these fields (quarterly, 2015-2025):**

1. In FA screen, customize columns to show:
   - Total Revenue
   - EBITDA
   - EBITDA Margin
   - Capital Expenditure
   - Total Debt
   - Total Assets
   - Net Income

2. Click **Actions** → **Export to Excel**
3. Save as: `exports/peer_{ticker}_financials.xlsx`

### Step 3.3: Pull Valuation Multiples

```
Terminal Command: {TICKER} Equity RV <GO>
```

Export:
- EV/EBITDA (LTM and NTM)
- EV/Revenue
- P/E Ratio

Save as: `exports/peer_{ticker}_multiples.xlsx`

### Step 3.4: Pull Beta and WACC

```
Terminal Command: {TICKER} Equity BETA <GO>
Terminal Command: {TICKER} Equity WACC <GO>
```

Record manually or export:
- Raw Beta (2Y Weekly)
- Adjusted Beta
- WACC components

Save as: `exports/peer_{ticker}_wacc.xlsx`

### Step 3.5: Bulk Pull via Excel Add-In

Create a new Excel workbook with this formula for each peer:

```excel
' Row 1: Headers
' Column A: Date, B: Revenue, C: EBITDA, D: Margin, E: CapEx, F: Debt

' NUE Financials (Quarterly)
=BDH("NUE US Equity","SALES_REV_TURN,EBITDA,EBITDA_MARGIN,CAPITAL_EXPEND,TOT_DEBT_TO_TOT_EQY","1/1/2015","12/31/2025","Dir=V","Per=Q","Fill=P")

' Repeat for each peer ticker
```

Save as: `exports/all_peers_financials.xlsx`

---

## Phase 4: Demand Drivers

### Step 4.1: US Auto Production

```
Terminal Command: SAABORWT Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/auto_production_saar_monthly.xlsx`

### Step 4.2: Housing Starts

```
Terminal Command: NHSPSTOT Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/housing_starts_monthly.xlsx`

### Step 4.3: Industrial Production

```
Terminal Command: IP CHNG Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/industrial_production_monthly.xlsx`

### Step 4.4: ISM Manufacturing PMI

```
Terminal Command: NAPMPMI Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/ism_pmi_monthly.xlsx`

### Step 4.5: Oil Rig Count (OCTG Demand)

```
Terminal Command: RIGSUA Index <GO>
```

Or search: `BAKR <GO>` for Baker Hughes data

1. Export weekly, 2000-2025
2. Save as: `exports/rig_count_weekly.xlsx`

### Step 4.6: Construction Spending

```
Terminal Command: CNSTTMOM Index <GO>
```

1. Export monthly, 2000-2025
2. Save as: `exports/construction_spending_monthly.xlsx`

---

## Phase 5: Macro Data

### Step 5.1: GDP Growth

```
Terminal Command: GDP CQOQ Index <GO>
```

1. Export quarterly, 1990-2025
2. Save as: `exports/gdp_qoq_quarterly.xlsx`

### Step 5.2: CPI Inflation

```
Terminal Command: CPI YOY Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/cpi_yoy_monthly.xlsx`

### Step 5.3: Unemployment Rate

```
Terminal Command: USURTOT Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/unemployment_monthly.xlsx`

### Step 5.4: Consumer Confidence

```
Terminal Command: CONCCONF Index <GO>
```

1. Export monthly, 1990-2025
2. Save as: `exports/consumer_confidence_monthly.xlsx`

---

## Phase 6: Steel Industry Data

### Step 6.1: AISI Capacity Utilization

```
Terminal Command: AISIUTIL Index <GO>
```

If not available, try: `BI STEEL <GO>` → Industry Data

1. Export monthly, 2000-2025
2. Save as: `exports/steel_capacity_util_monthly.xlsx`

### Step 6.2: World Steel Production

```
Terminal Command: WSTLPROD Index <GO>
```

1. Export monthly, 2000-2025
2. Save as: `exports/world_steel_production_monthly.xlsx`

### Step 6.3: US Steel Imports

```
Terminal Command: STLDUSGC Index <GO>
```

Or search in `ECST <GO>` for trade data

1. Export monthly, 2000-2025
2. Save as: `exports/us_steel_imports_monthly.xlsx`

### Step 6.4: China Steel Exports

```
Terminal Command: CHSTLEXP Index <GO>
```

1. Export monthly, 2010-2025
2. Save as: `exports/china_steel_exports_monthly.xlsx`

---

## Phase 7: M&A Transactions

### Step 7.1: Access M&A Database

```
Terminal Command: MA <GO>
```

### Step 7.2: Set Screening Criteria

1. Click **Screen** or **New Search**
2. Set filters:
   - **Industry:** Metals & Mining → Steel
   - **Region:** North America, Europe, Japan
   - **Announced Date:** 01/01/2015 to 12/31/2025
   - **Deal Value:** > $500 million
   - **Deal Status:** Completed

### Step 7.3: Export Fields

Select columns:
- Announced Date
- Target Company
- Acquirer Company
- Deal Value ($M)
- Enterprise Value ($M)
- EV/EBITDA
- EV/Revenue
- Premium Paid (%)
- Strategic vs Financial Buyer

### Step 7.4: Export

1. Click **Actions** → **Export to Excel**
2. Save as: `exports/steel_ma_transactions.xlsx`

---

## Phase 8: Correlation Matrix (Optional but Recommended)

### Step 8.1: Build Correlation Matrix in Excel

Use Bloomberg Excel Add-In to calculate correlations:

```excel
' 60-day correlation between HRC and Iron Ore
=BDP("MWST1MCA Index","CORRELATION","CORR_SECURITY=IABORUSE Index","CORR_PERIOD=60D")

' 252-day (1 year) correlation
=BDP("MWST1MCA Index","CORRELATION","CORR_SECURITY=IABORUSE Index","CORR_PERIOD=252D")
```

### Step 8.2: Key Correlations to Calculate

| Variable 1 | Variable 2 | Expected |
|-----------|-----------|----------|
| HRC Price | CRC Price | ~0.95 |
| HRC Price | Coated Price | ~0.93 |
| HRC Price | OCTG Price | ~0.65 |
| OCTG Price | Rig Count | ~0.75 |
| HRC Price | Iron Ore | ~0.60 |
| HRC Price | Auto Production | ~0.40 |
| US 10Y | Japan 10Y | ~0.50 |
| HRC Price | S&P 500 | ~0.30 |

Save as: `exports/correlation_matrix.xlsx`

---

## Data Validation Checklist

After completing all exports, verify:

### Steel Prices
- [ ] HRC US: 8,000+ daily observations (1990-2025)
- [ ] CRC US: 6,000+ daily observations
- [ ] HDG/Coated: 5,000+ daily observations
- [ ] OCTG: 4,000+ daily observations
- [ ] Scrap: 5,000+ daily observations
- [ ] Iron Ore: 4,000+ daily observations

### Rates
- [ ] US 10Y: 8,000+ daily observations
- [ ] Japan 10Y: 8,000+ daily observations
- [ ] BBB Spread: 5,000+ daily observations
- [ ] SOFR: 1,500+ daily observations

### Peers
- [ ] All 8 peers have quarterly financials (40+ quarters each)
- [ ] All peers have valuation multiples
- [ ] All peers have beta/WACC data

### Demand Drivers
- [ ] Auto production: 400+ monthly observations
- [ ] Housing starts: 400+ monthly observations
- [ ] PMI: 400+ monthly observations
- [ ] Rig count: 1,000+ weekly observations

### Macro
- [ ] GDP: 140+ quarterly observations
- [ ] CPI: 400+ monthly observations
- [ ] Unemployment: 400+ monthly observations

---

## File Naming Convention

Use this naming pattern for all exports:

```
{category}_{subcategory}_{frequency}.xlsx

Examples:
steel_hrc_us_daily.xlsx
rates_ust_10y_daily.xlsx
peer_nue_financials_quarterly.xlsx
macro_gdp_quarterly.xlsx
demand_auto_production_monthly.xlsx
```

---

## Next Steps After Data Collection

1. **Transfer files** to model directory:
   ```bash
   cp exports/*.xlsx /path/to/FinancialModel/bloomberg_data/raw/
   ```

2. **Run data loader** (to be created):
   ```bash
   python bloomberg_data/load_bloomberg_data.py
   ```

3. **Validate data quality**:
   ```bash
   python bloomberg_data/validate_data.py
   ```

4. **Calibrate Monte Carlo distributions**:
   ```bash
   python sensitivity_analysis/calibrate_distributions.py
   ```

---

## Troubleshooting

### Ticker Not Found
- Try `SECF <GO>` to search for securities
- Use `ALLX {keyword} <GO>` for commodity search
- Check `BI STEEL <GO>` for industry-specific data

### Data Gaps
- Use `Fill=P` in BDH to carry forward previous values
- Check if market was closed (holidays)
- Verify ticker was trading during requested period

### Excel Add-In Issues
- Ensure Bloomberg is logged in
- Check API limits (max 500 fields per request)
- Split large requests into multiple queries

### Export Size Limits
- For >65,000 rows, split date ranges
- Use CSV export for very large datasets
- Consider Bloomberg Data License for bulk data

---

## Support

- Bloomberg Help Desk: Press `<HELP>` twice on terminal
- Bloomberg University: `BU <GO>`
- Excel Add-In Guide: `API <GO>`

---

**Document Version:** 1.0
**Created:** 2026-02-01
**Author:** RAMBAS Financial Model Team
