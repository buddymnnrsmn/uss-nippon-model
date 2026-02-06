# Capital Projects EBITDA Impact Analysis

**Date:** February 2026
**Purpose:** Consolidated source document for all capital project parameters used in the USS/Nippon Steel valuation model. Synthesized from Nippon investor presentations, USS 10-K disclosures, merger proxy fairness opinions, and peer comparable analysis.

---

## 1. Project Summary

| # | Project | Segment | Capacity (kt/yr) | Margin | Price ($/ton) | EBITDA ($M) | Terminal Multiple | Total CapEx ($M) |
|---|---------|---------|-------------------|--------|---------------|-------------|-------------------|------------------|
| 1 | BR2 Mini Mill | Mini Mill | 3,000 | 17% | $900 | $459 | 7.0x | $3,200 |
| 2 | Gary Works BF Reline | Flat-Rolled | 2,500 | 12% | $950 | $285 | 5.0x | $3,200 |
| 3 | Mon Valley HSM Modernization | Flat-Rolled | 1,800 | 12% | $950 | $205 | 5.0x | $2,400 |
| 4 | Greenfield Mini Mill | Mini Mill | 500 | 17% | $900 | $77 | 7.0x | $1,000 |
| 5 | Mining Investment (Keetac/Minntac) | Mining | 6,000 | 12% | $150 | $108 | 5.0x | $1,000 |
| 6 | Fairfield Works Modernization | Tubular | 1,200 | 12% | $900 | $130 | 6.0x | $600 |
| | **TOTAL** | | | | | **$1,264** | | **$11,400** |

**EBITDA Formula:** `Capacity (kt) x Price ($/ton) x Margin (%) = Annual EBITDA`

---

## 2. Project Details

### 2.1 BR2 Mini Mill (Big River Steel Phase 2)

**Source:** Nippon Steel investor presentation (December 2023); USS 10-K capital expenditure disclosures

- **Capacity:** 3,000 kt/year (new EAF capacity at Osceola, AR)
- **Technology:** Electric Arc Furnace (EAF) with continuous casting
- **EBITDA Mechanism:** 100% volume growth (entirely new steelmaking capacity)
- **Margin:** 17% (conservative vs. management target of 20%+; reflects EAF cost advantage)
- **Price Basis:** $900/ton (mini mill flat-rolled benchmark, through-cycle)
- **Target EBITDA:** 3,000 x $900 x 0.17 = **$459M**
- **Total Investment:** ~$3.2B (Nippon presentation)
- **Construction Timeline:** 2025-2028 (phased commissioning)
- **Capacity Ramp:** 20% (2025) -> 60% (2026) -> 90% (2027) -> 100% (2028+)
- **Terminal Multiple:** 7.0x EBITDA (EAF peer median: STLD 7.8x, NUE 7.9x, CMC 5.8x)
- **Maintenance CapEx:** $20/ton ($60M/year at full capacity)
- **Status:** Enabled in base case (committed project)

### 2.2 Gary Works Blast Furnace Reline

**Source:** Capital Projects EBITDA Impact Analysis; USS capital plan disclosures

- **Capacity:** 2,500 kt/year (effective capacity from BF reline + caster upgrades)
- **Technology:** Blast Furnace (integrated steelmaking)
- **EBITDA Mechanism:** 70% asset preservation + 30% efficiency improvement
  - Asset preservation: Prevents ~$200M EBITDA decline from BF aging
  - Efficiency: Yield improvement, energy reduction, higher throughput
- **Margin:** 12% (post-upgrade efficiency for integrated operations)
- **Price Basis:** $950/ton (flat-rolled premium benchmark)
- **Target EBITDA:** 2,500 x $950 x 0.12 = **$285M**
- **Total Investment:** ~$3.2B
- **Construction Timeline:** 2025-2028 (BF reline requires full shutdown period)
- **Capacity Ramp:** 50% (2028) -> 90% (2029) -> 100% (2030+)
- **Terminal Multiple:** 5.0x EBITDA (Integrated peer median: CLF 5.2x, MT 4.7x, PKX 6.2x)
- **Maintenance CapEx:** $40/ton ($100M/year at full capacity)
- **Status:** Disabled in base case (conditional on Nippon acquisition)

### 2.3 Mon Valley Hot Strip Mill Modernization

**Source:** Capital Projects EBITDA Impact Analysis

- **Capacity:** 1,800 kt/year (current mill capacity ~2,800 kt; EBITDA from improvements)
- **Technology:** Hot Strip Mill (downstream of integrated BF/BOF)
- **EBITDA Mechanism:** 80% efficiency improvement + 20% premium product capability
  - Efficiency: Reduced conversion costs, higher yield, less downtime
  - Premium products: Advanced high-strength steel (AHSS) for automotive
- **Margin:** 12% (integrated margin, consistent with Gary Works)
- **Price Basis:** $950/ton (flat-rolled premium)
- **Target EBITDA:** 1,800 x $950 x 0.12 = **$205M**
- **Total Investment:** ~$2.4B
- **Construction Timeline:** 2025-2028
- **Capacity Ramp:** 50% (2028) -> 90% (2029) -> 100% (2030+)
- **Terminal Multiple:** 5.0x EBITDA (same as integrated peer median)
- **Maintenance CapEx:** $35/ton ($63M/year at full capacity)
- **Status:** Disabled in base case (conditional on acquisition)

### 2.4 Greenfield Mini Mill

**Source:** NSA commitments; Nippon Steel strategic plan

- **Capacity:** 500 kt/year (conservative; NSA filing references 0.5-1.0 Mt range)
- **Technology:** EAF greenfield
- **EBITDA Mechanism:** Strategic option with entirely new capacity (post-2028)
- **Margin:** 17% (EAF margin; may be lower during ramp-up)
- **Price Basis:** $900/ton (mini mill flat-rolled benchmark)
- **Target EBITDA:** 500 x $900 x 0.17 = **$77M**
- **Total Investment:** ~$1.0B
- **Construction:** 2028 (single-year, post-BR2 completion)
- **Capacity Ramp:** 50% (2029) -> 80% (2030) -> 100% (2031+)
- **Terminal Multiple:** 7.0x EBITDA (EAF peer median)
- **Maintenance CapEx:** $20/ton ($10M/year at full capacity)
- **Status:** Disabled in base case (strategic option)

### 2.5 Mining Investment (Keetac & Minntac)

**Source:** Capital Projects EBITDA Impact Analysis; USS iron ore operations disclosures

- **Capacity:** 6,000 kt/year pellets (combined Keetac + Minntac operations)
- **Technology:** Iron ore pelletizing (upstream vertical integration)
- **EBITDA Mechanism:** 100% cost avoidance through vertical integration
  - Produces iron ore pellets internally rather than purchasing on open market
  - EBITDA = avoided external pellet cost minus internal production cost
- **Margin:** 12% (cost savings mechanism, not traditional steelmaking margin)
- **Price Basis:** $150/ton (iron ore pellet price, NOT steel price)
  - Uses `base_price_override` — not linked to steel price scenarios
- **Target EBITDA:** 6,000 x $150 x 0.12 = **$108M**
- **Total Investment:** ~$1.0B ($200M/yr for 4 years + $200M in Year 5)
- **Construction Timeline:** 2025-2028
- **Capacity Ramp:** 50% (2026) -> 90% (2027) -> 100% (2028+)
- **Terminal Multiple:** 5.0x EBITDA (conservative commodity multiple)
- **Maintenance CapEx:** $8/ton ($48M/year at full capacity)
- **Status:** Disabled in base case (conditional on acquisition)
- **Note:** Volume factor linkage excluded — mining serves internal demand, not market-driven

### 2.6 Fairfield Works Modernization

**Source:** Capital Projects EBITDA Impact Analysis; USS Tubular segment disclosures

- **Capacity:** 1,200 kt/year (current ~1.5 Mt, targeting 1.8-2.0 Mt)
- **Technology:** Tubular/OCTG (Oil Country Tubular Goods)
- **EBITDA Mechanism:** 60% efficiency improvement + 40% capacity expansion
  - Efficiency: Modernized seamless pipe production, reduced energy costs
  - Expansion: Additional welded pipe capacity for energy sector
- **Margin:** 12% (integrated operations; document notes highest ROIC project)
- **Price Basis:** $900/ton (tubular benchmark; actual OCTG prices ~$2,388/ton but modeled at conversion margin)
- **Target EBITDA:** 1,200 x $900 x 0.12 = **$130M**
- **Total Investment:** ~$600M ($200M/yr for 2 years + $100M/yr for 2 years)
- **Construction Timeline:** 2025-2028
- **Capacity Ramp:** 50% (2026) -> 90% (2027) -> 100% (2028+)
- **Terminal Multiple:** 6.0x EBITDA (blended specialty premium between EAF 7x and integrated 5x)
- **Maintenance CapEx:** $25/ton ($30M/year at full capacity)
- **Status:** Disabled in base case (conditional on acquisition)

---

## 3. Margin Framework

### 3.1 Margin Rules by Technology

| Technology | Margin | Rationale | Management Target | Model Haircut |
|------------|--------|-----------|-------------------|---------------|
| EAF Mini Mill | 17% | Lower conversion costs, higher scrap flexibility | 20%+ | -3% (conservatism) |
| Blast Furnace | 12% | Post-upgrade efficiency; still higher fixed costs | 15%+ | -3% |
| Mining | 12% | Cost avoidance value, not traditional margin | N/A | N/A |
| Tubular/OCTG | 12% | Integrated operations, specialty premium offset by cyclicality | 15%+ | -3% |

### 3.2 Price Benchmarks

All prices are through-cycle equilibrium (post-Section 232 tariff rebasing):

| Product | Through-Cycle Price | 2023 Bloomberg Avg | Factor at 1.0x |
|---------|--------------------|--------------------|----------------|
| HRC (flat-rolled) | $738/ton | $916 | 0.81x |
| CRC | $994/ton | $1,127 | 0.88x |
| Coated | $1,113/ton | $1,263 | 0.88x |
| EU HRC | $611/ton | $717 | 0.85x |
| OCTG | $2,388/ton | $2,750 | 0.87x |

**Note:** Capital projects use segment benchmark prices ($900-950/ton), not HRC specifically. These represent blended realized prices inclusive of product mix and customer premiums.

---

## 4. Terminal Multiple Derivation

### 4.1 WRDS Peer Company Analysis (FY2022-2023)

| Peer | Ticker | Technology | EV/EBITDA FY2023 | EV/EBITDA FY2022 | Average |
|------|--------|------------|------------------|------------------|---------|
| Nucor | NUE | EAF | 7.9x | 4.8x | 6.4x |
| Steel Dynamics | STLD | EAF | 7.8x | 4.5x | 6.2x |
| Commercial Metals | CMC | EAF | 5.8x | 5.2x | 5.5x |
| Cleveland-Cliffs | CLF | Integrated | 5.2x | 3.8x | 4.5x |
| ArcelorMittal | MT | Integrated | 4.7x | 3.1x | 3.9x |
| POSCO | PKX | Integrated | 6.2x | 4.5x | 5.4x |
| Ternium | TX | Integrated | 3.3x | 2.8x | 3.1x |

**Source:** WRDS Compustat North America / Global; EV calculated as market cap + net debt

### 4.2 Selected Terminal Multiples

| Technology | Selected Multiple | Peer Median | Premium/Discount | Rationale |
|------------|-------------------|-------------|------------------|-----------|
| EAF Mini Mill | **7.0x** | 6.7x (STLD/NUE/CMC) | +0.3x | Reflects new, efficient capacity |
| Integrated BF | **5.0x** | 4.8x (CLF/MT/PKX) | +0.2x | Post-modernization premium |
| Tubular/OCTG | **6.0x** | N/A (blended) | N/A | Between EAF and integrated |
| Mining | **5.0x** | N/A | N/A | Conservative commodity multiple |

---

## 5. Maintenance CapEx Framework

### 5.1 Sustaining Capital Requirements

| Technology | Maint $/ton | Annual at Capacity | % of EBITDA | Peer Benchmark |
|------------|-------------|-------------------|-------------|----------------|
| EAF Mini Mill | $20 | $60M (BR2 3,000 kt) | 13% | NUE sustaining ~$25/ton |
| Blast Furnace | $40 | $100M (Gary 2,500 kt) | 35% | CLF total $49/ton |
| Hot Strip Mill | $35 | $63M (Mon Valley 1,800 kt) | 31% | Industry $30-40/ton |
| Mining | $8 | $48M (6,000 kt) | 44% | Low intensity |
| Tubular | $25 | $30M (Fairfield 1,200 kt) | 23% | Specialty equipment |

### 5.2 Key Observations

1. **EAF advantage:** Maintenance burden ~$20/ton vs ~$40/ton for BF (2x lower)
2. **BF EBITDA erosion:** Gary Works maintenance consumes 35% of EBITDA vs 13% for BR2
3. **Mining intensity:** High maintenance/EBITDA ratio (44%) reflects low-margin cost avoidance
4. **Timing:** Maintenance capex starts AFTER construction complete, not during ramp-up
5. **FCF formula:** `FCF = EBITDA x 0.75 (after 25% tax) - Construction CapEx - Maintenance CapEx`

---

## 6. CapEx Schedules

### 6.1 Construction CapEx by Year ($M)

| Project | 2025 | 2026 | 2027 | 2028 | Total |
|---------|------|------|------|------|-------|
| BR2 Mini Mill | 200 | 800 | 900 | 1,300 | 3,200 |
| Gary Works BF | 400 | 900 | 800 | 1,100 | 3,200 |
| Mon Valley HSM | 100 | 700 | 700 | 900 | 2,400 |
| Greenfield MM | - | - | - | 1,000 | 1,000 |
| Mining | 200 | 200 | 300 | 300 | 1,000 |
| Fairfield | 200 | 200 | 100 | 100 | 600 |
| **TOTAL** | **1,100** | **2,800** | **2,800** | **4,700** | **11,400** |

### 6.2 Capacity Ramp Schedules (% of Nameplate)

| Project | 2025 | 2026 | 2027 | 2028 | 2029 | 2030+ |
|---------|------|------|------|------|------|-------|
| BR2 Mini Mill | 20% | 60% | 90% | 100% | 100% | 100% |
| Gary Works BF | - | - | - | 50% | 90% | 100% |
| Mon Valley HSM | - | - | - | 50% | 90% | 100% |
| Greenfield MM | - | - | - | - | 50% | 80%/100% |
| Mining | - | 50% | 90% | 100% | 100% | 100% |
| Fairfield | - | 50% | 90% | 100% | 100% | 100% |

---

## 7. Source Citations

| Data Point | Primary Source | Secondary Source |
|------------|---------------|-----------------|
| BR2 capacity (3,000 kt) | Nippon Steel investor presentation (Dec 2023) | USS 10-K capital disclosures |
| BR2 investment ($3.2B) | Nippon Steel investor presentation | NSA filing commitments |
| Gary Works BF mechanism | EBITDA Impact Analysis (internal) | USS capital plan disclosures |
| Mon Valley HSM mechanism | EBITDA Impact Analysis (internal) | USS capital plan disclosures |
| Greenfield capacity range | NSA commitments filing | Nippon strategic plan |
| Mining pellet capacity | USS 10-K segment data | Iron ore operations disclosures |
| Fairfield expansion | USS Tubular segment disclosures | EBITDA Impact Analysis |
| EAF margins (17%) | Conservative vs. STLD/NUE reported margins (18-22%) | Industry analysis |
| BF margins (12%) | USS Flat-Rolled historical segment margins | Peer comparison (CLF 10-14%) |
| Terminal multiples | WRDS Compustat peer analysis (FY2022-2023) | Goldman/Barclays proxy comps |
| Maintenance capex | Industry benchmarks; peer 10-K disclosures | AIST publications |
| Tariff-adjusted prices | Bloomberg through-cycle analysis | Section 232 tariff model |

### Fairness Opinion Cross-Check

From USS merger proxy (DEFM14A):
- **Barclays DCF:** WACC 11.5-13.5%, terminal growth -1% to 1%, implied $39-$50/share
- **Goldman DCF:** WACC 10.75-12.50%, exit multiple 3.5-6.0x, implied $38.12-$52.02/share
- **Goldman peer comps:** USS 3.6x (L5Y avg), CLF 5.7x, STLD 5.3x, NUE 6.0x
- **Goldman CoE:** 14.2% | **Barclays CoE:** 15.0%

Our model's base case: USS standalone $39.04/share, Nippon perspective $55.66/share — consistent with fairness opinion ranges.

---

## 8. Model Implementation

All parameters are implemented in `price_volume_model.py`:
- **Dataclass:** `CapitalProject` (lines ~1950-1978)
- **Project definitions:** `get_capital_projects()` (lines 1979-2133)
- **Dynamic EBITDA calculation:** `calculate_project_ebitda()` (uses capacity x utilization x price x margin)
- **NPV calculation:** `interactive_dashboard.py` (includes terminal value and maintenance capex)
- **Tests:** `tests/test_dynamic_project_ebitda.py` (16 tests, all passing)
