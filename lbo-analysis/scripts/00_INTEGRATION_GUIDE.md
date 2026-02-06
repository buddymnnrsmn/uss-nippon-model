# LBO Model Integration Guide

## Overview

The LBO model (`lbo_model_template.py`) integrates seamlessly with the existing DCF model (`price_volume_model.py`) to provide a complete valuation framework.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    VALUATION FRAMEWORK                   │
└─────────────────────────────────────────────────────────┘

STRATEGIC BUYER (DCF)                FINANCIAL BUYER (LBO)
price_volume_model.py                lbo_model_template.py
─────────────────────                ─────────────────────

Operating Projections                Operating Projections
├── Price × Volume                   ├── SAME (from DCF)
├── Segment-level EBITDA             ├── Conservative haircut
├── CapEx ($14B NSA program)         └── Maintenance only
├── NWC changes                      
└── Unlevered FCF                    Financing Structure
                                     ├── Sources & Uses
Valuation                            ├── Debt Schedule
├── WACC discount                    ├── Interest expense
├── IRP-adjusted WACC                └── Cash sweep
├── Terminal value
└── $/share value                    Levered Cash Flows
                                     ├── Unlevered FCF
OUTPUT: Intrinsic value              ├── - Interest
  to strategic buyer                 ├── - Amortization
  (Nippon perspective)               └── = Levered FCF

                                     Exit Analysis
                                     ├── Exit EV (multiple)
                                     ├── Exit equity value
                                     └── Returns (IRR, MoIC)

                                     OUTPUT: PE returns
                                       (financial buyer perspective)
```

## Usage Example

```python
from price_volume_model import PriceVolumeModel, ScenarioType, get_scenario_presets
from lbo_model_template import LBOModel, build_example_scenario

# Step 1: Get conservative scenario from DCF model
dcf_scenario = get_scenario_presets()[ScenarioType.CONSERVATIVE]

# Step 2: Build LBO scenario (layers financing on top)
lbo_scenario = build_example_scenario()  # Uses dcf_scenario internally

# Step 3: Run LBO analysis
base_financials = {
    'cash': 3013.9,
    'investments': 761.0,
    'total_debt': 4222.0,
    'pension': 126.0,
    'leases': 117.0
}

model = LBOModel(lbo_scenario, base_financials)
results = model.run()

# Step 4: Compare DCF vs LBO
print(f"DCF Value (Nippon): ${dcf_value:.2f}/share")
print(f"LBO IRR (PE): {results['returns']['irr']*100:.1f}%")
print(f"Nippon Offer: $55.00/share")
```

## Key Integration Points

### 1. Operating Projections
- LBO imports `PriceVolumeModel` class
- Uses conservative/base scenarios
- Applies additional execution haircut (0.75)
- Restricts to maintenance CapEx only

### 2. Scenario Selection
- DCF uses all scenarios (Base, Conservative, Wall Street, Management, Nippon)
- LBO uses ONLY Conservative scenario (PE underwriting standards)
- LBO removes $14B growth CapEx (PE cannot fund)

### 3. Discount Rates
- DCF: WACC (10.9%) or IRP-adjusted WACC (5.5%)
- LBO: IRR hurdle (20%+ required for PE)

### 4. Terminal Value
- DCF: Gordon Growth or Exit Multiple
- LBO: Exit Multiple only (no growth assumption)

### 5. Output Metrics
- DCF: $/share equity value
- LBO: IRR, MoIC, absolute return ($M)

## Data Flow

```python
# Data flows from PriceVolumeModel into LBOModel

PriceVolumeModel Output          LBOModel Input
─────────────────────          ───────────────
consolidated['Total_EBITDA']  → waterfall['EBITDA']
consolidated['DA']            → waterfall['DA']
consolidated['Total_CapEx']   → waterfall['CapEx']
consolidated['Delta_WC']      → waterfall['Delta_NWC']
consolidated['FCF']           → debt_schedule['Levered_FCF']
```

## Scenario Comparison

| Dimension | DCF Model | LBO Model |
|-----------|-----------|-----------|
| **Buyer Type** | Strategic (Nippon) | Financial (PE firm) |
| **Holding Period** | Indefinite | 5-7 years |
| **CapEx Assumption** | $14B NSA program | Maintenance only |
| **Execution Factor** | 1.0 (full credit) | 0.75 (25% haircut) |
| **Financing** | All equity (balance sheet) | High leverage (4x) |
| **Return Metric** | NPV, $/share | IRR, MoIC |
| **Typical Output** | $55-65/share | 12-16% IRR |

## Next Steps

1. **Calibrate Entry Multiple**: Use actual USS trading multiples
2. **Finalize Debt Structure**: Confirm leverage ratios and pricing
3. **Run Sensitivities**: Entry/exit multiples, EBITDA scenarios
4. **Compare to Nippon Offer**: Show PE cannot compete at $55/share

## Files

- **Documentation**: `/lbo_model/research/05_lbo_model_structure.md`
- **Template Code**: `/lbo_model/scripts/lbo_model_template.py`
- **DCF Model**: `/price_volume_model.py`

## Contact

For questions on integration, see model documentation or review the inline comments in `lbo_model_template.py`.
