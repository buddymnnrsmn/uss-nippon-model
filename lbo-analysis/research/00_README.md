# LBO Model Documentation Index

This directory contains comprehensive research and documentation for the USS LBO model.

## Research Documents

### Completed

- **05_lbo_model_structure.md** - Complete LBO model architecture and design
  - Sources & Uses table structure
  - Debt schedule architecture (tranches, amortization, cash sweep)
  - Cash flow waterfall logic
  - Exit analysis methodology
  - Returns calculations (IRR, MoIC)
  - Sensitivity analysis design
  - Integration with existing DCF model

### Pending

1. **01_debt_market_conditions.md** - Current debt market analysis (Task #1)
2. **02_comparable_lbo_transactions.md** - Steel/industrial LBO comps (Task #2)
3. **03_uss_capital_structure.md** - USS existing capital structure (Task #3)
4. **04_stress_scenarios.md** - Downside/stress case analysis (Task #4)

## Implementation

See `/lbo_model/scripts/lbo_model_template.py` for the complete Python implementation template.

## Purpose

The LBO model demonstrates that:
1. **PE firms cannot compete with Nippon's $55/share offer** (IRR below 20% threshold)
2. **$14B NSA CapEx program is unfundable by financial buyers** (leverage constraints)
3. **Nippon's strategic value >> PE financial engineering value**

This establishes a valuation floor and proves the $55 offer represents full and fair value.
