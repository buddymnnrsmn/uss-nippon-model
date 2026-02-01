# Bloomberg Data Directory

Data repository for Bloomberg Terminal exports used in Monte Carlo calibration and scenario validation.

## Quick Start

```bash
# 1. After downloading Bloomberg data, place files in exports/
cp ~/Downloads/*.xlsx bloomberg_data/exports/

# 2. Load and process all data
python bloomberg_data/bloomberg_loader.py --load-all --save

# 3. Calibrate Monte Carlo parameters
python bloomberg_data/bloomberg_loader.py --calibrate --correlations

# 4. Generate calibration report
python bloomberg_data/bloomberg_loader.py --report

# 5. Integrate with model (dry run first)
python bloomberg_data/integrate_with_model.py

# 6. Apply to model
python bloomberg_data/integrate_with_model.py --apply
```

## Directory Structure

```
bloomberg_data/
├── README.md                    # This file
├── BLOOMBERG_DATA_GUIDE.md      # Step-by-step terminal instructions
├── QUICK_REFERENCE.md           # Ticker list and Excel formulas
├── bloomberg_loader.py          # Main data loading script
├── integrate_with_model.py      # Model integration script
├── exports/                     # Place raw Bloomberg exports here
│   └── *.xlsx                   # Your Bloomberg files
├── raw/                         # Processed data (parquet/csv)
│   ├── steel_hrc_us.parquet
│   ├── statistics.csv
│   └── correlations.csv
└── cache/                       # Temporary cache files
```

## Workflow

### Step 1: Gather Data from Bloomberg Terminal

1. Review `QUICK_REFERENCE.md` for ticker list
2. Follow `BLOOMBERG_DATA_GUIDE.md` for step-by-step instructions
3. Export files to Excel format
4. Transfer to `exports/` folder

### Step 2: Load and Process Data

```bash
# Load all available data
python bloomberg_loader.py --load-all

# Or load specific categories
python bloomberg_loader.py --steel-prices
python bloomberg_loader.py --rates
```

### Step 3: Validate Data

```bash
python bloomberg_loader.py --validate
```

Expected output:
```
✓ steel_hrc_us: 8,234 obs
✓ steel_crc_us: 6,102 obs
✓ rates_ust_10y: 8,891 obs
⚠ demand_rig_count: 1,203 obs (expected ≥2000)
```

### Step 4: Calibrate Parameters

```bash
python bloomberg_loader.py --calibrate
```

This calculates:
- Historical mean, std for each series
- Annualized volatility
- Distribution parameters for Monte Carlo

### Step 5: Calculate Correlations

```bash
python bloomberg_loader.py --correlations
```

Produces correlation matrix between:
- HRC ↔ CRC (expected: ~0.95)
- HRC ↔ OCTG (expected: ~0.65)
- OCTG ↔ Rig Count (expected: ~0.75)

### Step 6: Save Processed Data

```bash
python bloomberg_loader.py --save
```

Saves to `raw/`:
- `steel_hrc_us.parquet` - Time series data
- `statistics.csv` - Summary statistics
- `correlations.csv` - Correlation matrix

### Step 7: Generate Report

```bash
python bloomberg_loader.py --report
```

Creates `CALIBRATION_REPORT.md` with:
- Data summary
- Calibrated parameters
- Recommended Monte Carlo settings

### Step 8: Integrate with Model

```bash
# Preview changes (dry run)
python integrate_with_model.py

# Apply to monte_carlo_engine.py
python integrate_with_model.py --apply
```

## File Naming Convention

The loader recognizes these patterns:

| Pattern | Example |
|---------|---------|
| `steel_hrc_us*.xlsx` | `steel_hrc_us_daily.xlsx` |
| `MWST1MCA*.xlsx` | `MWST1MCA_export.xlsx` |
| `rates_ust_10y*.xlsx` | `rates_ust_10y_daily.xlsx` |
| `peer_*_financials*.xlsx` | `peer_nue_financials.xlsx` |

## Data Categories

| Category | Files | Model Use |
|----------|-------|-----------|
| Steel Prices | `steel_*.xlsx` | Monte Carlo distributions |
| Interest Rates | `rates_*.xlsx` | WACC calibration |
| Credit Spreads | `credit_*.xlsx` | LBO pricing |
| Peer Data | `peer_*.xlsx` | Benchmark validation |
| Demand Drivers | `demand_*.xlsx` | Correlation matrix |
| Macro | `macro_*.xlsx` | Scenario mapping |

## CLI Reference

```bash
bloomberg_loader.py [OPTIONS]

Options:
  --load-all        Load all available data
  --steel-prices    Load steel price data only
  --rates           Load interest rate data only
  --calibrate       Calibrate Monte Carlo parameters
  --correlations    Calculate correlation matrix
  --validate        Validate loaded data
  --save            Save processed data to raw/
  --report          Generate calibration report
  --exports-dir     Custom exports directory
```

## Troubleshooting

### "No Excel files found"
- Ensure files are in `exports/` folder
- Check file extension is `.xlsx` (not `.xls` or `.csv`)

### "Failed to parse"
- Check Excel file format (Date in column A, Value in column B)
- Try re-exporting from Bloomberg with standard format

### Volatility seems wrong
- Verify daily data (not monthly)
- Check for data gaps or holidays
- Ensure price units are consistent ($/ton, not $/lb)

### Correlations don't match expected
- Increase date overlap between series
- Check for different trading calendars
- Consider using returns instead of levels

## Expected Results

After full calibration, you should see:

| Series | Observations | Ann. Volatility |
|--------|-------------|-----------------|
| HRC US | 8,000+ | 15-25% |
| CRC US | 6,000+ | 15-25% |
| OCTG | 4,000+ | 20-30% |
| UST 10Y | 8,000+ | N/A (rate) |
| JGB 10Y | 8,000+ | N/A (rate) |

## Integration with Model

The calibrated parameters integrate with:

1. **monte_carlo_engine.py** - Distribution parameters
2. **price_volume_model.py** - Scenario presets
3. **benchmark_data.py** - Peer validation

See `integrate_with_model.py --help` for details.
