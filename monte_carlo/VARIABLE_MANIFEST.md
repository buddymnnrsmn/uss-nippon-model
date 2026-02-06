# Monte Carlo Variable Manifest

**25 variables | Last calibrated: 2026-02-06 | Data cutoff: 2023-12-18**

This is the single-page master index for all Monte Carlo simulation variables. For detailed methodology, see `DISTRIBUTION_CALIBRATION.md`. For programmatic parameters, see `distributions_config.json`.

---

## Price Factors (5 variables)

All use **lognormal** distributions with mean-reversion: μ = -σ²/2 → E[X] = 1.0 (through-cycle baseline).

| # | Variable | σ | μ | P5 | P95 | Benchmark | Source |
|---|----------|---|---|-----|------|-----------|--------|
| 1 | `hrc_price_factor` | 0.18 | -0.0162 | 0.73 | 1.32 | $738/ton | Bloomberg HRC US spot (pre-COVID σ=0.208) |
| 2 | `crc_price_factor` | 0.16 | -0.0128 | 0.76 | 1.29 | $994/ton | Bloomberg CRC US spot (pre-COVID σ=0.163) |
| 3 | `coated_price_factor` | 0.15 | -0.0113 | 0.78 | 1.27 | $1,113/ton | Derived from HRC/CRC avg |
| 4 | `hrc_eu_factor` | 0.15 | -0.0113 | 0.78 | 1.27 | $611/ton | Bloomberg HRC EU spot (σ=0.156) |
| 5 | `octg_price_factor` | 0.22 | -0.0242 | 0.67 | 1.40 | $2,388/ton | Bloomberg OCTG US spot (σ=0.211) |

**Key correlations:** HRC↔CRC 0.97, HRC↔OCTG 0.50, HRC US↔EU 0.70

---

## Volume Factors (4 variables)

| # | Variable | Distribution | Parameters | Mean | σ/Range | Source |
|---|----------|-------------|------------|------|---------|--------|
| 6 | `flat_rolled_volume` | Normal | μ=1.0, σ=0.081 | 1.00 | ±8.1% | US capacity utilization (2015-2023) |
| 7 | `mini_mill_volume` | Normal | μ=1.0, σ=0.061 | 1.00 | ±6.1% | Derived: FR × 0.75 (less cyclical) |
| 8 | `usse_volume` | Normal | μ=1.0, σ=0.10 | 1.00 | ±10% | EU demand data |
| 9 | `tubular_volume` | Triangular | [0.65, 1.0, 1.35] | 1.00 | 0.65-1.35 | US rig count (tightened from raw) |

**Key correlations:** HRC↔FR Volume 0.56, OCTG↔Tubular Volume 0.73

---

## Discount Rate Components (3 variables)

| # | Variable | Distribution | Parameters | Mean | 99% CI | Source |
|---|----------|-------------|------------|------|--------|--------|
| 10 | `uss_wacc` | Normal | μ=10.9%, σ=0.8% | 10.9% | 8.8-13.0% | CAPM (Fed H.15, Duff & Phelps, USS 10-K) |
| 11 | `us_10yr` | Normal | μ=4.25%, σ=0.50% | 4.25% | 2.95-5.55% | Bloomberg UST 10Y (affects IRP WACC) |
| 12 | `nippon_erp` | Normal | μ=4.75%, σ=0.50% | 4.75% | 3.45-6.05% | Damodaran Japan ERP estimate |

**Key correlations:** US 10Y↔USS WACC 0.60

**IRP Formula:** `USD_WACC = (1 + JPY_WACC) × (1 + US_10Y) / (1 + Japan_10Y) - 1`

---

## Terminal Value (2 variables)

| # | Variable | Distribution | Parameters | Mean | Source |
|---|----------|-------------|------------|------|--------|
| 13 | `terminal_growth` | Triangular | [-0.5%, 1.0%, 2.5%] | 1.0% | Expert judgment (GDP growth match) |
| 14 | `exit_multiple` | Triangular | [3.5x, 4.5x, 6.5x] | 4.83x | Bloomberg peer trading comps |

---

## Execution Risk (2 variables)

Both use **Beta** distributions (bounded [0,1], right-skewed toward success).

| # | Variable | Distribution | Range | Mean | Mode | Source |
|---|----------|-------------|-------|------|------|--------|
| 15 | `gary_works_execution` | Beta(8,3) | [0.40, 1.0] | 83.6% | ~87% | BF reline track record |
| 16 | `mon_valley_execution` | Beta(9,2) | [0.50, 1.0] | 90.9% | ~94% | HSM upgrade (simpler) |

**Key correlation:** Gary↔Mon Valley 0.60 (common management capability)

---

## Synergy Factors (2 variables)

| # | Variable | Distribution | Range | Mean | Source |
|---|----------|-------------|-------|------|--------|
| 17 | `operating_synergy_factor` | Beta(8,3) | [0.50, 1.0] | 86.4% | McKinsey/BCG M&A synergy lit |
| 18 | `revenue_synergy_factor` | Beta(3,4) | [0.30, 0.9] | 55.7% | Revenue synergies harder (40-60% typ) |

**Note:** These are MC-only variables — they don't vary by deterministic scenario.

---

## Tariff Risk (2 variables, added 2026-02-06)

| # | Variable | Distribution | Parameters | Mean | Source |
|---|----------|-------------|------------|------|--------|
| 19 | `tariff_probability` | Beta(8,2) | [0.0, 1.0] | 80% maintained | Political analysis (bipartisan support) |
| 20 | `tariff_rate_if_changed` | Triangular | [0%, 10%, 25%] | ~12% | Policy scenario analysis |

**Integration:** `effective_rate = prob × 0.25 + (1-prob) × alt_rate`
**Correlations:** Tariff Prob ↔ HRC -0.35, ↔ CRC -0.35, ↔ FR Volume -0.25
**Impact:** Adds ~4pp downside probability vs no-tariff baseline

---

## Other Factors (5 variables)

| # | Variable | Distribution | Parameters | Mean | Source |
|---|----------|-------------|------------|------|--------|
| 21 | `annual_price_growth` | Normal | μ=1.0%, σ=1.0% | 1.0% | Steel is mean-reverting commodity |
| 22 | `flat_rolled_margin_factor` | Triangular | [0.85, 1.0, 1.15] | 1.00 | Peer EBITDA margins (57 peer-yrs) |
| 23 | `capex_intensity_factor` | Triangular | [0.80, 1.0, 1.30] | 1.03 | Expert judgment on cost overruns |
| 24 | `working_capital_efficiency` | Normal | μ=1.0, σ=0.08 | 1.00 | Peer WC days variation |
| 25 | `margin_factor` | Triangular | [0.85, 1.0, 1.15] | 1.00 | Overall margin uncertainty |

**Note:** Variables 22-25 are MC-only — they modulate the base case but don't appear in deterministic scenario tables.

---

## Correlation Matrix (Key Pairs)

| Variable 1 | Variable 2 | ρ | Rationale |
|------------|------------|---|-----------|
| HRC Price | CRC Price | 0.97 | Same steel market |
| HRC Price | Coated Price | 0.95 | CRC + coating premium |
| HRC Price | OCTG Price | 0.50 | Different end markets |
| HRC Price | FR Volume | 0.56 | Demand drives both |
| HRC US | HRC EU | 0.70 | Global linkage |
| OCTG Price | Tubular Vol | 0.73 | Common driver (drilling) |
| US 10Y | USS WACC | 0.60 | Rate pass-through |
| Gary Exec | Mon Valley Exec | 0.60 | Common management |
| Tariff Prob | HRC Price | -0.35 | Removal → lower prices |
| Tariff Prob | CRC Price | -0.35 | Removal → lower prices |
| Tariff Prob | Coated Price | -0.30 | Removal → lower prices |
| Tariff Prob | OCTG Price | -0.20 | Less affected |
| Tariff Prob | FR Volume | -0.25 | Removal → lower demand |

Total: 31 defined correlations. Matrix is adjusted to positive semi-definite via eigenvalue correction before Cholesky decomposition.

---

## Configuration Priority

1. **`distributions_config.json`** — Primary source (deliberate calibration choices)
2. **Bloomberg fitted distributions** — Secondary (raw historical fit)
3. **Hardcoded defaults in engine** — Fallback only

---

## File Cross-Reference

| File | What It Contains |
|------|-----------------|
| `monte_carlo/distributions_config.json` | All 25 variable parameters + rationale strings |
| `monte_carlo/DISTRIBUTION_CALIBRATION.md` | Full methodology, fitting process, validation |
| `monte_carlo/monte_carlo_engine.py` | Engine code (`_define_input_variables()`) |
| `monte_carlo/distribution_fitter.py` | Statistical fitting from Bloomberg data |
| `documentation/SCENARIO_ASSUMPTIONS.md` | Deterministic scenario parameters |
| `documentation/SCENARIO_RATIONALE.md` | WACC sources (Section S.5), scenario logic |
| `price_volume_model.py` | Margin sensitivity, benchmarks, tariff functions |
| `scripts/validate_distributions.py` | Validation checks (25/25 pass) |

---

## Calibration History

| Date | Change | Variables Affected |
|------|--------|--------------------|
| 2026-02-06 | Tariff model added | +2 (tariff_probability, tariff_rate_if_changed) |
| 2026-02-06 | Through-cycle σ calibration | 5 price factors |
| 2026-02-06 | Margin sensitivity halved | Model parameter (not MC variable) |
| 2026-02-06 | Annual price growth reduced | annual_price_growth (1.5%→1.0%) |
| 2026-02-06 | Margin cap tightened | Model parameter (30%→22%) |
| 2026-02-05 | Distribution tightening | tubular_volume, margin_factor |
| 2026-02-05 | Config priority over Bloomberg | All variables |
| 2026-01-21 | Initial 23-variable calibration | All original variables |

---

RAMBAS Team Capstone Project | Last Updated: February 2026
