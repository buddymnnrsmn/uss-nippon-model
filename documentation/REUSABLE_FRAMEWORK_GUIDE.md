# Reusable Framework Guide
## Applying USS/Nippon Model Architecture to Other Investment Types

**Last Updated:** 2026-01-31

---

## Executive Summary

This USS/Nippon Steel financial model demonstrates a **highly generalizable architecture** that can be adapted to real estate, private equity, and distressed debt investing. Approximately **80-85% of the codebase is directly reusable**, requiring only industry-specific customization of data structures and business logic.

**Total Implementation Time for New Investment Type:** 15-22 hours

---

## What's Reusable (80-85% of Framework)

### 1. Core Valuation Engine ✅

**Components:**
- DCF calculation (`price_volume_model.py:1653-1750`)
- Terminal value calculation (Gordon Growth + Exit Multiple)
- Enterprise to equity value bridge
- Working capital modeling
- Tax calculations

**Directly Applicable To:**
- Real Estate: Property NOI → DCF
- Private Equity: Portfolio company EBITDA → DCF
- Distressed Debt: Enterprise value → Recovery value

**Example:**
```python
# Current (Steel)
def calculate_dcf(self, df: pd.DataFrame, wacc: float) -> Dict:
    """Calculate DCF valuation"""
    fcf = df['FCF'].values
    discount_factors = [(1 + wacc) ** -i for i in range(1, len(fcf) + 1)]
    pv_fcf = sum(fcf * discount_factors)
    terminal_value = fcf[-1] * (1 + g) / (wacc - g)
    ev = pv_fcf + terminal_value / (1 + wacc) ** len(fcf)
    return ev

# Real Estate (same pattern)
def calculate_property_dcf(self, noi_projections: pd.DataFrame, wacc: float) -> Dict:
    """Calculate property DCF - IDENTICAL LOGIC"""
    # Just replace FCF with NOI, same calculation
```

---

### 2. Scenario Framework ✅

**Components:**
- Preset scenario factory pattern (`get_scenario_presets()`)
- Probability-weighted valuation
- Scenario comparison
- Historical calibration methodology

**Directly Applicable To:**
- Real Estate: Market cycles (Recession, Mid-Cycle, Expansion)
- Private Equity: Exit scenarios (Strategic Sale, IPO, Secondary)
- Distressed Debt: Restructuring outcomes (Liquidation, Ch11 Plan, Out-of-Court)

**Example Adaptation:**

| Investment Type | Scenarios | Probability Calibration |
|----------------|-----------|------------------------|
| **Steel (Current)** | Severe Downturn (25%), Downside (30%), Base (30%), Above Avg (10%), Optimistic (5%) | Historical steel price distribution 1990-2023 |
| **Real Estate** | Recession (20%), Mid-Cycle (60%), Expansion (20%) | CoStar market data 1985-2024 |
| **Private Equity** | Distressed Exit (15%), Base Case (50%), Strategic Premium (35%) | Industry transaction multiples |
| **Distressed Debt** | Liquidation (30%), Ch11 Reorg (50%), Out-of-Court (20%) | Historical recovery rates by industry |

---

### 3. Audit & Testing Infrastructure ✅

**Components:**
- Automated audit framework (`audits/model_audit.py`)
- 8 test categories with 23 tests
- Input traceability audit
- Calculation verification
- Consolidation integrity checks

**Test Categories (100% Reusable):**

| Category | Steel Test | Real Estate Test | PE Test | Distressed Test |
|----------|-----------|------------------|---------|----------------|
| **Input Validation** | Verify segment volumes vs 10-K | Verify property NOI vs lease abstracts | Verify EBITDA vs mgmt presentations | Verify claim balances vs bankruptcy schedules |
| **Calculation** | Revenue = Volume × Price | NOI = Rent × Occupancy × SF | EBITDA = Revenue × Margin | Recovery = EV × Allocation % |
| **Consolidation** | Segment EBITDA sums to total | Property NOI sums to portfolio | BU EBITDA sums to company | Claim recoveries sum to EV |
| **Logic Checks** | Higher WACC → Lower value | Higher cap rate → Lower value | Higher leverage → Lower equity value | Higher priority → Higher recovery |
| **Sensitivity** | Price +10% → EBITDA +X% | Cap rate +50bps → Value -8% | Revenue +10% → IRR +Xbps | EV +10% → Recovery +X¢/$1 |
| **Boundary** | Margins floored at 2% | Occupancy capped at 100% | Leverage capped at covenant | Recovery capped at par |
| **Financing** | NSA triggers financing gap | Refi triggers prepayment penalty | Dividend recap impact | DIP financing cost |
| **Scenario** | Downside < Base < Optimistic | Recession < Base < Expansion | Distressed < Base < Strategic | Liquidation < Ch11 < OOC |

**Direct Reusability:**
```python
# Steel test
test = AuditTest("CV-01", "Revenue = Volume × Price (2024)", "Calculation")
calculated = year_2024['Volume'] * year_2024['Price'] / 1000
expected = year_2024['Revenue']
test.passed = abs(expected - calculated) < 1.0

# Real Estate test (identical pattern)
test = AuditTest("CV-01", "NOI = Rent × Occupancy × SF", "Calculation")
calculated = property['Rent_PSF'] * property['Occupancy'] * property['SF'] / 1000000
expected = property['NOI']
test.passed = abs(expected - calculated) < 0.01
```

---

### 4. Dashboard Architecture ✅

**Components:**
- State-managed Streamlit interface
- Calculation button pattern with status tracking
- Cache invalidation on parameter change
- Progress bars for long calculations
- Export to Excel/CSV

**Reusable Patterns:**

```python
# Generic calculation button with state management
def render_calculation_button(section_name: str, button_label: str) -> bool:
    """
    DIRECTLY REUSABLE pattern for:
    - Run Property Analysis
    - Run Portfolio Valuation
    - Run Recovery Analysis
    """
    is_calculated = st.session_state[section_name] is not None
    is_stale = section_name in st.session_state.get('stale_sections', set())

    button_text = "Recalculate" if is_calculated else button_label
    clicked = st.button(button_text, type="primary" if is_stale else "secondary")

    if is_stale:
        st.warning("Parameters changed. Click to update.")
    elif is_calculated:
        st.success(f"Calculated at {result['timestamp']}")

    return clicked
```

---

### 5. Data Loading & Validation ✅

**Components:**
- Generic data loader with caching (`scripts/data_loader.py`)
- Column header cleaning
- Numeric conversion with error handling
- Source document traceability

**Example Adaptation:**

```python
# Steel data loader
class USSteelDataLoader:
    def load_income_statement(self) -> pd.DataFrame:
        df = pd.read_excel(self.financials_file, sheet_name='Income Statement')
        df = self._clean_column_headers(df, header_row=4)
        df = self._clean_numeric(df)
        return df

# Real Estate data loader (same pattern)
class PropertyDataLoader:
    def load_rent_roll(self) -> pd.DataFrame:
        df = pd.read_excel(self.property_file, sheet_name='Rent Roll')
        df = self._clean_column_headers(df, header_row=2)  # Just change row
        df = self._clean_numeric(df)
        return df

# Methods _clean_column_headers() and _clean_numeric() are 100% reusable
```

---

### 6. Cache Persistence ✅

**Components:**
- Hash-based cache invalidation (`scripts/cache_persistence.py`)
- Pickle serialization for complex objects
- Metadata tracking (timestamp, size)
- Automatic cleanup of stale caches

**100% Reusable Across All Investment Types:**

```python
# Save any calculation with scenario tracking
save_calculation_cache('property_dcf', dcf_results, scenario_hash)

# Load if parameters unchanged
cached = load_calculation_cache('property_dcf', scenario_hash)
if cached:
    return cached  # Skip expensive recalculation
```

---

### 7. Documentation Framework ✅

**Templates (100% Reusable):**
- `MODEL_METHODOLOGY.md` - How the model works
- `SCENARIO_ASSUMPTIONS.md` - Scenario calibration
- `SENSITIVITY_ANALYSIS.md` - What-if analysis
- `AUDIT_TEST_ANALYSIS.md` - Test results
- `DIRECTORY_STRUCTURE.md` - File organization

Just search/replace industry terms:
- "Steel Price" → "Cap Rate" / "EBITDA Multiple" / "Credit Spread"
- "Segment" → "Property" / "Business Unit" / "Claim Class"
- "USS" → Your target company

---

## What's Industry-Specific (15-20%)

### 1. Commodity/Market Drivers

**Current (Steel):**
```python
@dataclass
class SteelPriceScenario:
    hrc_us_factor: float        # Hot-rolled coil
    crc_us_factor: float        # Cold-rolled coil
    coated_us_factor: float     # Coated steel
    octg_factor: float          # Oil country tubular goods
    annual_price_growth: float
```

**Real Estate Version:**
```python
@dataclass
class RealEstateMarketScenario:
    cap_rate_basis: float           # Market cap rate (e.g., 5.5%)
    cap_rate_change_bps: float      # Scenario adjustment (+100bps in downturn)
    rent_growth_annual: float       # Annual rent escalation
    occupancy_stress_factor: float  # Occupancy reduction in downturn
    tenant_credit_stress: float     # % tenant defaults
```

**Private Equity Version:**
```python
@dataclass
class PEMarketScenario:
    entry_multiple: float           # Purchase price / EBITDA
    exit_multiple: float            # Exit valuation / EBITDA
    leverage_multiple: float        # Debt / EBITDA at entry
    spread_to_libor: float          # Debt pricing
    ebitda_growth_rate: float       # Annual EBITDA growth
```

---

### 2. Asset Segments

**Current (Steel):**
- Flat-Rolled (51% of revenue)
- Mini Mill (28%)
- USSE (13%)
- Tubular (8%)

**Real Estate:**
- Office
- Retail
- Industrial
- Multifamily

**Private Equity:**
- Business Unit A
- Business Unit B
- Business Unit C

**Distressed Debt:**
- Senior Secured
- Senior Unsecured
- Subordinated Debt
- Equity Claims

---

### 3. Operating Metrics Calculation

**Current (Steel):**
```python
def calculate_segment_margin(self, segment: Segment, price: float) -> float:
    """Margin = Base Margin + (Price Change / 100) * Price Elasticity"""
    price_change = price - base_price
    margin_adj = (price_change / 100) * margin_sensitivity
    margin = base_margin + margin_adj
    return max(0.02, min(0.30, margin))  # Floor 2%, cap 30%
```

**Real Estate Version:**
```python
def calculate_noi_margin(self, property_id: str, cap_rate: float) -> float:
    """NOI Margin = Base Margin - (Cap Rate Change / 100) * Cap Rate Sensitivity"""
    # Higher cap rates → compressed margins (inverse relationship)
    cap_rate_change = cap_rate - base_cap_rate
    margin_adj = -(cap_rate_change / 100) * cap_rate_sensitivity
    margin = base_noi_margin + margin_adj
    return max(0.60, min(0.85, margin))  # Floor 60%, cap 85%
```

**Pattern:** Same elasticity formula, just different drivers

---

## Implementation Roadmap for New Investment Type

### Example: Adapting to Distressed Debt Investing

**Time Estimate: 15-22 hours**

#### Phase 1: Define Data Structures (2-3 hours)

```python
# 1.1 Define market scenario (replaces SteelPriceScenario)
@dataclass
class DistressedMarketScenario:
    """Market conditions for distressed debt"""
    name: str
    recovery_environment: str  # "Liquidation", "Reorganization", "Out-of-Court"
    time_to_emergence: int     # Months in bankruptcy
    dip_financing_rate: float  # DIP loan interest rate
    exit_financing_multiple: float  # Exit debt / EBITDA
    professional_fees_pct: float    # % of claims consumed by fees

# 1.2 Define claim classes (replaces SegmentVolumePrice)
@dataclass
class ClaimClass:
    """Individual claim class in capital structure"""
    name: str
    claim_amount: float        # Face value of claim
    priority: int              # 1 = highest priority (DIP), 10 = equity
    secured: bool
    collateral_value: float    # For secured claims
    base_recovery_rate: float  # Historical recovery for this class
    recovery_elasticity: float # Sensitivity to EV changes

# 1.3 Define complete scenario (replaces ModelScenario)
@dataclass
class DistressedDebtScenario:
    """Complete distressed debt analysis scenario"""
    name: str
    scenario_type: ScenarioType
    market_scenario: DistressedMarketScenario
    enterprise_value_estimate: float
    claim_classes: List[ClaimClass]
    wacc: float
    probability_weight: float
```

#### Phase 2: Implement Calculation Engine (4-6 hours)

```python
class DistressedDebtModel:
    """Distressed debt recovery analysis model"""

    def __init__(self, scenario: DistressedDebtScenario):
        self.scenario = scenario

    def calculate_recovery_waterfall(self) -> pd.DataFrame:
        """
        Calculate recovery waterfall from EV down through claims

        Steps:
        1. Start with Enterprise Value
        2. Subtract professional fees
        3. Allocate to claims by priority
        4. Calculate recovery % for each class
        """
        ev = self.scenario.enterprise_value_estimate
        fees = ev * self.scenario.market_scenario.professional_fees_pct
        distributable = ev - fees

        # Sort claims by priority
        claims = sorted(self.scenario.claim_classes, key=lambda c: c.priority)

        waterfall = []
        remaining = distributable

        for claim in claims:
            if claim.secured:
                # Secured claims: min(claim amount, collateral value)
                recovery_amount = min(claim.claim_amount, claim.collateral_value)
            else:
                # Unsecured: allocate from remaining pool
                recovery_amount = min(claim.claim_amount, remaining)

            recovery_rate = recovery_amount / claim.claim_amount
            remaining -= recovery_amount

            waterfall.append({
                'Claim Class': claim.name,
                'Claim Amount': claim.claim_amount,
                'Recovery Amount': recovery_amount,
                'Recovery Rate': recovery_rate,
                'Priority': claim.priority
            })

        return pd.DataFrame(waterfall)

    def run_full_analysis(self) -> Dict:
        """Run complete distressed debt analysis"""
        # Calculate recovery waterfall
        waterfall = self.calculate_recovery_waterfall()

        # Calculate sensitivity to EV
        sensitivity = self.calculate_ev_sensitivity()

        # Compare to historical recoveries
        historical_comp = self.compare_to_historical_recoveries()

        return {
            'waterfall': waterfall,
            'sensitivity': sensitivity,
            'historical_comparison': historical_comp,
            'scenario': self.scenario
        }
```

#### Phase 3: Adapt Audit Framework (2-3 hours)

```python
class DistressedDebtAuditor(ModelAuditor):
    """Audit framework for distressed debt model"""

    def _test_input_validation(self):
        """Verify claim balances match bankruptcy schedules"""
        test = AuditTest("IV-01", "Claim balances match bankruptcy schedule", "Input")
        # Compare model claims vs. court filings

    def _test_calculation_verification(self):
        """Verify recovery waterfall calculation"""
        test = AuditTest("CV-01", "Recovery waterfall sums correctly", "Calculation")
        # Verify sum of recoveries <= EV - fees

    def _test_logic_checks(self):
        """Verify claim priority and recovery logic"""
        test = AuditTest("LC-01", "Higher priority → higher recovery", "Logic")
        # Verify senior claims recover more than junior
```

#### Phase 4: Build Dashboard (4-6 hours)

```python
# Streamlit dashboard for distressed debt
st.title("Distressed Debt Recovery Analysis")

# Sidebar inputs
with st.sidebar:
    st.header("Scenario Inputs")

    # Enterprise value estimate
    ev_estimate = st.number_input(
        "Enterprise Value Estimate ($M)",
        min_value=0.0,
        value=500.0,
        step=10.0
    )

    # Recovery scenario
    scenario_type = st.selectbox(
        "Recovery Scenario",
        ["Liquidation", "Chapter 11 Reorganization", "Out-of-Court Restructuring"]
    )

    # Professional fees
    prof_fees_pct = st.slider(
        "Professional Fees (% of EV)",
        min_value=0.0,
        max_value=0.15,
        value=0.05,
        step=0.01,
        format="%.1f%%"
    )

# Main content - waterfall visualization
if st.button("Calculate Recovery Waterfall", type="primary"):
    model = DistressedDebtModel(scenario)
    results = model.run_full_analysis()

    st.subheader("Recovery Waterfall")
    st.dataframe(results['waterfall'])

    # Waterfall chart
    fig = create_waterfall_chart(results['waterfall'])
    st.plotly_chart(fig)
```

#### Phase 5: Documentation (3-4 hours)

Adapt templates:
- `MODEL_METHODOLOGY.md` → Explain recovery waterfall, priority rules
- `SCENARIO_ASSUMPTIONS.md` → Document liquidation vs reorganization scenarios
- `SENSITIVITY_ANALYSIS.md` → EV sensitivity, time-to-emergence impact
- `AUDIT_TEST_ANALYSIS.md` → Document test results

---

## Key Architectural Patterns to Reuse

### Pattern 1: Dataclass Composition Hierarchy

```
ModelScenario (Top Level)
├── MarketScenario (Market/Commodity Layer)
├── AssetScenario (Asset-Specific Layer)
├── SynergyScenario (Value Creation Layer)
└── FinancingScenario (Capital Structure Layer)
```

**Why This Works:**
- Each layer is self-contained and testable
- Layers compose without tight coupling
- Easy to swap implementations (e.g., replace SteelPriceScenario with RealEstateMarketScenario)

### Pattern 2: Scenario Preset Factory

```python
def get_scenario_presets() -> Dict[ScenarioType, ModelScenario]:
    """Pre-built scenarios calibrated to historical data"""
    return {
        ScenarioType.PESSIMISTIC: create_pessimistic_scenario(),
        ScenarioType.BASE: create_base_scenario(),
        ScenarioType.OPTIMISTIC: create_optimistic_scenario()
    }
```

**Benefits:**
- Ensures consistency across analyses
- Historical calibration prevents arbitrary assumptions
- Easy to add new scenarios without changing core code

### Pattern 3: Calculation with Progress Callbacks

```python
def run_analysis(self, progress_callback=None) -> Dict:
    """Run analysis with optional progress tracking"""
    if progress_callback:
        progress_callback(0, "Starting analysis...")

    # Step 1
    result1 = self.step1()
    if progress_callback:
        progress_callback(25, "Step 1 complete")

    # Step 2
    result2 = self.step2(result1)
    if progress_callback:
        progress_callback(50, "Step 2 complete")

    # ...
```

**Benefits:**
- Long-running calculations show progress
- Works seamlessly with Streamlit progress bars
- Doesn't break when used without progress callback

### Pattern 4: Hash-Based Cache Invalidation

```python
def create_scenario_hash(scenario: ModelScenario) -> str:
    """Create unique hash of scenario parameters"""
    scenario_dict = {
        'type': scenario.scenario_type.name,
        'param1': scenario.param1,
        'param2': scenario.param2,
        # ... all parameters ...
    }
    return hashlib.md5(json.dumps(scenario_dict, sort_keys=True).encode()).hexdigest()

# Use hash for caching
scenario_hash = create_scenario_hash(scenario)
cached = load_calculation_cache('analysis', scenario_hash)
if cached:
    return cached  # Parameters unchanged, use cache
```

**Benefits:**
- Automatically recalculates when inputs change
- No manual cache management needed
- Works with any serializable data structure

---

## Real-World Application Examples

### Example 1: Multifamily Real Estate Portfolio Analysis

**Components Reused (85%):**
- Scenario framework (Recession / Mid-Cycle / Expansion)
- DCF calculation (NOI → property value)
- Probability-weighted valuation across market cycles
- Audit framework (verify rent roll, NOI calculations)
- Dashboard interface (select properties, run analysis)
- Cache persistence (save calculations)

**Components Customized (15%):**
- Property metrics (rent PSF, occupancy, cap rates)
- Market scenarios (cap rate spreads, occupancy stress)
- Portfolio aggregation (sum property NOI)

**Implementation Time: ~18 hours**

---

### Example 2: Private Equity Leveraged Buyout Model

**Components Reused (80%):**
- Scenario framework (Downside / Base / Upside exit)
- DCF calculation (EBITDA → equity value)
- Synergy calculation (cost reduction, revenue synergies)
- Financing impact (debt schedule, interest expense)
- Audit framework (verify EBITDA, debt covenants)
- Dashboard interface (input assumptions, run model)

**Components Customized (20%):**
- Operating metrics (revenue growth, margin expansion)
- Leverage structure (debt tranches, amortization)
- Exit scenarios (strategic sale, IPO multiples)

**Implementation Time: ~20 hours**

---

### Example 3: Distressed Debt Recovery Analysis

**Components Reused (75%):**
- Scenario framework (Liquidation / Ch11 / Out-of-Court)
- Probability-weighted recovery across scenarios
- Sensitivity analysis (EV sensitivity to recovery)
- Audit framework (verify claim balances, priorities)
- Dashboard interface (input EV estimate, view waterfall)

**Components Customized (25%):**
- Claim structure (priority, secured vs unsecured)
- Recovery waterfall (allocate EV to claims)
- Court/legal assumptions (professional fees, timeline)

**Implementation Time: ~22 hours**

---

## Conclusion

This USS/Nippon Steel financial model demonstrates **production-grade financial modeling architecture** with:

✅ **80-85% reusable core framework**
✅ **Comprehensive audit infrastructure**
✅ **Interactive dashboard with caching**
✅ **Probability-weighted scenario analysis**
✅ **Fully documented methodology**

The framework successfully abstracts the common patterns in financial modeling while maintaining flexibility for industry-specific customization. With 15-22 hours of implementation time, you can adapt this architecture to virtually any investment type.

**Key Insight:** The majority of financial modeling complexity is in the **infrastructure** (scenarios, auditing, dashboards, documentation)—not in the industry-specific calculations. This codebase has already solved the hard infrastructure problems.

---

## Next Steps

1. **Identify Target Investment Type** - Real estate, PE, distressed debt, etc.
2. **Define Data Structures** - Create industry-specific dataclasses
3. **Implement Calculation Logic** - Adapt price/volume derivation to your metrics
4. **Adapt Audit Tests** - Customize test cases for your domain
5. **Build Dashboard** - Customize UI for your workflow
6. **Document Methodology** - Adapt documentation templates

**Recommended Starting Point:** Begin with the scenario framework and DCF calculation, as these are the most universal components. Once those work, add auditing and dashboard incrementally.
