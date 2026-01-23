#!/usr/bin/env python3
"""
Interactive DCF Dashboard: USS / Nippon Steel Merger Analysis
==============================================================

Streamlit dashboard with scenario analysis and steel price sensitivity:
- Pre-built scenarios (Base, Conservative, Management, Wall Street, Nippon Commitments)
- Steel price benchmarks (HRC, CRC, Coated, OCTG)
- Volume assumptions by segment
- Interest Rate Parity adjustment
- Segment-level FCF analysis

Run with: streamlit run interactive_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# Import the price x volume model
from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType,
    SteelPriceScenario, VolumeScenario, Segment,
    get_scenario_presets, get_segment_configs, compare_scenarios,
    get_capital_projects, BENCHMARK_PRICES_2023
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="USS / Nippon Steel DCF Analysis",
    page_icon="$",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# SIDEBAR - SCENARIO & ASSUMPTIONS
# =============================================================================

def render_sidebar():
    """Render sidebar with scenario and assumption inputs"""

    st.sidebar.title("Model Assumptions")

    # Initialize session state for reset triggers and scenario tracking
    if 'reset_section' not in st.session_state:
        st.session_state.reset_section = None
    if 'previous_scenario' not in st.session_state:
        st.session_state.previous_scenario = None

    # Scenario Selection
    st.sidebar.header("Scenario Selection")

    scenario_options = {
        "Base Case": ScenarioType.BASE_CASE,
        "Conservative": ScenarioType.CONSERVATIVE,
        "Wall Street Consensus": ScenarioType.WALL_STREET,
        "Management": ScenarioType.MANAGEMENT,
        "NSA Mandated CapEx": ScenarioType.NIPPON_COMMITMENTS,
        "Custom": ScenarioType.CUSTOM
    }

    selected_scenario_name = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_options.keys()),
        index=0,
        help="Pre-built scenarios with different assumptions. Select 'Custom' to manually adjust all parameters."
    )
    selected_scenario_type = scenario_options[selected_scenario_name]

    # Check if scenario changed - if so, trigger reset to load new defaults
    if st.session_state.previous_scenario != selected_scenario_name and selected_scenario_type != ScenarioType.CUSTOM:
        st.session_state.reset_section = "all"
        st.session_state.previous_scenario = selected_scenario_name

    # Show scenario description
    scenario_descriptions = {
        "Base Case": "Mid-cycle pricing (95% factor), BR2 only, 10.9% WACC. Most likely standalone outcome.",
        "Conservative": "Downside stress test. 85% prices, 12% WACC, volume contraction.",
        "Wall Street Consensus": "Based on Barclays/Goldman fairness opinions. 12.5% WACC, flat prices.",
        "Management": "December 2023 projections. Footprint reduction, $700/ton HRC.",
        "NSA Mandated CapEx": "Full $14B investment program. All 6 projects, no plant closures through 2035.",
        "Custom": "Manually adjust all parameters below."
    }
    st.sidebar.caption(scenario_descriptions.get(selected_scenario_name, ""))

    # Reset All button
    if st.sidebar.button("↺ Reset All to Scenario Defaults", key="reset_all", help="Reset ALL parameters to the selected scenario's defaults", type="secondary"):
        st.session_state.reset_section = "all"
        st.rerun()

    # Get preset values
    presets = get_scenario_presets()
    if selected_scenario_type != ScenarioType.CUSTOM:
        preset = presets[selected_scenario_type]
    else:
        preset = presets[ScenarioType.BASE_CASE]  # Start from base for custom

    # Handle Reset All (also triggered when scenario changes)
    if st.session_state.reset_section == "all":
        # Reset benchmarks
        st.session_state.hrc_us = BENCHMARK_PRICES_2023['hrc_us']
        st.session_state.crc_us = BENCHMARK_PRICES_2023['crc_us']
        st.session_state.coated_us = BENCHMARK_PRICES_2023['coated_us']
        st.session_state.hrc_eu = BENCHMARK_PRICES_2023['hrc_eu']
        st.session_state.octg = BENCHMARK_PRICES_2023['octg']
        # Reset price factors
        st.session_state.hrc_factor = preset.price_scenario.hrc_us_factor
        st.session_state.eu_factor = preset.price_scenario.hrc_eu_factor
        st.session_state.octg_factor = preset.price_scenario.octg_factor
        st.session_state.annual_price_growth = preset.price_scenario.annual_price_growth * 100
        # Reset volume
        st.session_state.fr_vf = preset.volume_scenario.flat_rolled_volume_factor
        st.session_state.mm_vf = preset.volume_scenario.mini_mill_volume_factor
        st.session_state.usse_vf = preset.volume_scenario.usse_volume_factor
        st.session_state.tub_vf = preset.volume_scenario.tubular_volume_factor
        st.session_state.fr_ga = preset.volume_scenario.flat_rolled_growth_adj * 100
        st.session_state.mm_ga = preset.volume_scenario.mini_mill_growth_adj * 100
        st.session_state.usse_ga = preset.volume_scenario.usse_growth_adj * 100
        st.session_state.tub_ga = preset.volume_scenario.tubular_growth_adj * 100
        # Reset WACC
        st.session_state.uss_wacc = preset.uss_wacc * 100
        st.session_state.terminal_growth = preset.terminal_growth * 100
        st.session_state.exit_multiple = preset.exit_multiple
        # Reset IRP
        st.session_state.us_10yr = preset.us_10yr * 100
        st.session_state.japan_10yr = preset.japan_10yr * 100
        st.session_state.n_coe = preset.nippon_cost_of_equity * 100
        st.session_state.n_cod = preset.nippon_cost_of_debt * 100
        st.session_state.n_dr = preset.nippon_debt_ratio * 100
        st.session_state.n_tr = preset.nippon_tax_rate * 100
        # Reset capital projects
        st.session_state.include_br2 = 'BR2 Mini Mill' in preset.include_projects
        st.session_state.include_gary = 'Gary Works BF' in preset.include_projects
        st.session_state.include_mon_valley = 'Mon Valley HSM' in preset.include_projects
        st.session_state.include_greenfield = 'Greenfield Mini Mill' in preset.include_projects
        st.session_state.include_mining = 'Mining Investment' in preset.include_projects
        st.session_state.include_fairfield = 'Fairfield Works' in preset.include_projects
        st.session_state.reset_section = None

    st.sidebar.markdown("---")

    # Steel Price Benchmarks
    st.sidebar.header("Steel Price Benchmarks")
    if st.sidebar.button("↺ Reset to Default", key="reset_benchmarks", help="Reset benchmark prices to 2023 defaults"):
        st.session_state.reset_section = "benchmarks"
        st.rerun()
    st.sidebar.caption("2023 Base Prices ($/ton) - Industry Reference Points")
    st.sidebar.info("These are the starting benchmark prices from 2023. The model applies price factors below to adjust these for future scenarios.")

    # Handle benchmark reset
    if st.session_state.reset_section == "benchmarks":
        st.session_state.hrc_us = BENCHMARK_PRICES_2023['hrc_us']
        st.session_state.crc_us = BENCHMARK_PRICES_2023['crc_us']
        st.session_state.coated_us = BENCHMARK_PRICES_2023['coated_us']
        st.session_state.hrc_eu = BENCHMARK_PRICES_2023['hrc_eu']
        st.session_state.octg = BENCHMARK_PRICES_2023['octg']
        st.session_state.reset_section = None

    col1, col2 = st.sidebar.columns(2)
    with col1:
        hrc_us = st.number_input("US HRC", value=st.session_state.get('hrc_us', BENCHMARK_PRICES_2023['hrc_us']), step=10, key="hrc_us", help="Hot-Rolled Coil - Primary flat steel product")
        crc_us = st.number_input("US CRC", value=st.session_state.get('crc_us', BENCHMARK_PRICES_2023['crc_us']), step=10, key="crc_us", help="Cold-Rolled Coil - Higher margin product")
        coated_us = st.number_input("Coated", value=st.session_state.get('coated_us', BENCHMARK_PRICES_2023['coated_us']), step=10, key="coated_us", help="Galvanized/Coated - Premium product")
    with col2:
        hrc_eu = st.number_input("EU HRC", value=st.session_state.get('hrc_eu', BENCHMARK_PRICES_2023['hrc_eu']), step=10, key="hrc_eu", help="European Hot-Rolled Coil (USSE segment)")
        octg = st.number_input("OCTG", value=st.session_state.get('octg', BENCHMARK_PRICES_2023['octg']), step=50, key="octg", help="Oil Country Tubular Goods (Tubular segment)")

    st.sidebar.markdown("---")

    # Price Scenario
    st.sidebar.header("Price Factors")
    if st.sidebar.button("↺ Reset to Default", key="reset_price_factors", help=f"Reset price factors to {selected_scenario_name} defaults"):
        st.session_state.reset_section = "price_factors"
        st.rerun()
    st.sidebar.markdown("""
    **How Price Factors Work:**
    - **1.00x** = Use 2023 benchmark price
    - **0.85x** = 15% below benchmark (downturn)
    - **1.10x** = 10% above benchmark (strong market)
    """)

    # Handle price factors reset
    if st.session_state.reset_section == "price_factors":
        st.session_state.hrc_factor = preset.price_scenario.hrc_us_factor
        st.session_state.eu_factor = preset.price_scenario.hrc_eu_factor
        st.session_state.octg_factor = preset.price_scenario.octg_factor
        st.session_state.annual_price_growth = preset.price_scenario.annual_price_growth * 100
        st.session_state.reset_section = None

    # Price factors (relative to benchmark)
    hrc_factor = st.sidebar.slider(
        "US HRC Price Factor",
        0.5, 1.5, st.session_state.get('hrc_factor', preset.price_scenario.hrc_us_factor), 0.05,
        format="%.2fx",
        key="hrc_factor",
        help=f"Applied to ${BENCHMARK_PRICES_2023['hrc_us']}/ton base. Current: ${BENCHMARK_PRICES_2023['hrc_us'] * preset.price_scenario.hrc_us_factor:.0f}/ton"
    )
    st.sidebar.caption(f"→ Implied HRC: ${BENCHMARK_PRICES_2023['hrc_us'] * hrc_factor:.0f}/ton")

    eu_factor = st.sidebar.slider(
        "EU HRC Price Factor",
        0.5, 1.5, st.session_state.get('eu_factor', preset.price_scenario.hrc_eu_factor), 0.05,
        format="%.2fx",
        key="eu_factor",
        help=f"Applied to ${BENCHMARK_PRICES_2023['hrc_eu']}/ton base for European operations"
    )

    octg_factor = st.sidebar.slider(
        "OCTG Price Factor",
        0.5, 1.5, st.session_state.get('octg_factor', preset.price_scenario.octg_factor), 0.05,
        format="%.2fx",
        key="octg_factor",
        help=f"Applied to ${BENCHMARK_PRICES_2023['octg']}/ton base for Tubular segment"
    )

    annual_price_growth = st.sidebar.slider(
        "Annual Price Growth",
        -3.0, 5.0, st.session_state.get('annual_price_growth', preset.price_scenario.annual_price_growth * 100), 0.5,
        format="%.1f%%",
        key="annual_price_growth",
        help="Year-over-year price escalation applied to all products"
    ) / 100

    st.sidebar.markdown("---")

    # Volume Scenario
    st.sidebar.header("Volume Scenario")
    if st.sidebar.button("↺ Reset to Default", key="reset_volume", help=f"Reset volume factors to {selected_scenario_name} defaults"):
        st.session_state.reset_section = "volume"
        st.rerun()
    st.sidebar.caption("Adjust production volumes by segment")

    # Handle volume reset
    if st.session_state.reset_section == "volume":
        st.session_state.fr_vf = preset.volume_scenario.flat_rolled_volume_factor
        st.session_state.mm_vf = preset.volume_scenario.mini_mill_volume_factor
        st.session_state.usse_vf = preset.volume_scenario.usse_volume_factor
        st.session_state.tub_vf = preset.volume_scenario.tubular_volume_factor
        st.session_state.fr_ga = preset.volume_scenario.flat_rolled_growth_adj * 100
        st.session_state.mm_ga = preset.volume_scenario.mini_mill_growth_adj * 100
        st.session_state.usse_ga = preset.volume_scenario.usse_growth_adj * 100
        st.session_state.tub_ga = preset.volume_scenario.tubular_growth_adj * 100
        st.session_state.reset_section = None

    with st.sidebar.expander("Volume Factors by Segment", expanded=False):
        st.caption("Multiplier on base 2023 volumes (1.0 = no change)")
        fr_vol_factor = st.slider("Flat-Rolled", 0.5, 1.2, st.session_state.get('fr_vf', preset.volume_scenario.flat_rolled_volume_factor), 0.05, key="fr_vf",
                                   help="Integrated steel mills (Gary, Mon Valley). Facing structural decline without investment.")
        mm_vol_factor = st.slider("Mini Mill", 0.5, 1.3, st.session_state.get('mm_vf', preset.volume_scenario.mini_mill_volume_factor), 0.05, key="mm_vf",
                                   help="Electric Arc Furnace operations (Big River Steel). Highest growth segment.")
        usse_vol_factor = st.slider("USSE", 0.5, 1.2, st.session_state.get('usse_vf', preset.volume_scenario.usse_volume_factor), 0.05, key="usse_vf",
                                     help="U.S. Steel Europe (Slovakia). Exposed to EU market conditions.")
        tub_vol_factor = st.slider("Tubular", 0.5, 1.3, st.session_state.get('tub_vf', preset.volume_scenario.tubular_volume_factor), 0.05, key="tub_vf",
                                    help="Oil Country Tubular Goods (OCTG). Tied to energy sector drilling activity.")

    with st.sidebar.expander("Volume Growth Adjustments", expanded=False):
        st.caption("Annual growth rate added/subtracted from base growth")
        fr_growth_adj = st.slider("Flat-Rolled Growth Adj", -5.0, 3.0, st.session_state.get('fr_ga', preset.volume_scenario.flat_rolled_growth_adj * 100), 0.5, format="%.1f%%", key="fr_ga",
                                   help="Typically negative due to aging blast furnaces and capacity rationalization") / 100
        mm_growth_adj = st.slider("Mini Mill Growth Adj", -3.0, 5.0, st.session_state.get('mm_ga', preset.volume_scenario.mini_mill_growth_adj * 100), 0.5, format="%.1f%%", key="mm_ga",
                                   help="Typically positive due to BR2 ramp-up and EAF market share gains") / 100
        usse_growth_adj = st.slider("USSE Growth Adj", -3.0, 3.0, st.session_state.get('usse_ga', preset.volume_scenario.usse_growth_adj * 100), 0.5, format="%.1f%%", key="usse_ga",
                                     help="Depends on European industrial demand and energy costs") / 100
        tub_growth_adj = st.slider("Tubular Growth Adj", -3.0, 5.0, st.session_state.get('tub_ga', preset.volume_scenario.tubular_growth_adj * 100), 0.5, format="%.1f%%", key="tub_ga",
                                    help="Cyclical with oil & gas drilling activity") / 100

    st.sidebar.markdown("---")

    # WACC Parameters
    st.sidebar.header("WACC Parameters")
    if st.sidebar.button("↺ Reset to Default", key="reset_wacc", help=f"Reset WACC parameters to {selected_scenario_name} defaults"):
        st.session_state.reset_section = "wacc"
        st.rerun()
    st.sidebar.caption("Discount rate and terminal value assumptions")

    # Handle WACC reset
    if st.session_state.reset_section == "wacc":
        st.session_state.uss_wacc = preset.uss_wacc * 100
        st.session_state.terminal_growth = preset.terminal_growth * 100
        st.session_state.exit_multiple = preset.exit_multiple
        st.session_state.reset_section = None

    uss_wacc = st.sidebar.slider("USS WACC", 8.0, 14.0, st.session_state.get('uss_wacc', preset.uss_wacc * 100), 0.1, format="%.1f%%",
                                  key="uss_wacc",
                                  help="USS standalone Weighted Average Cost of Capital. Higher = lower valuation. Typical range 10-12% for steel companies.") / 100
    terminal_growth = st.sidebar.slider("Terminal Growth", 0.0, 3.0, st.session_state.get('terminal_growth', preset.terminal_growth * 100), 0.25, format="%.2f%%",
                                         key="terminal_growth",
                                         help="Perpetual growth rate after 2033 for Gordon Growth terminal value. Steel is mature industry, typically 0-2%.") / 100
    exit_multiple = st.sidebar.slider("Exit Multiple (EBITDA)", 3.0, 7.0, st.session_state.get('exit_multiple', preset.exit_multiple), 0.5, format="%.1fx",
                                       key="exit_multiple",
                                       help="EV/EBITDA multiple for exit-based terminal value. Steel sector typically trades 4-6x.")

    st.sidebar.markdown("---")

    # Interest Rate Parity
    st.sidebar.header("Interest Rate Parity")
    if st.sidebar.button("↺ Reset to Default", key="reset_irp", help=f"Reset IRP parameters to {selected_scenario_name} defaults"):
        st.session_state.reset_section = "irp"
        st.rerun()
    st.sidebar.caption("Converts Nippon's JPY WACC to USD equivalent")

    # Handle IRP reset
    if st.session_state.reset_section == "irp":
        st.session_state.us_10yr = preset.us_10yr * 100
        st.session_state.japan_10yr = preset.japan_10yr * 100
        st.session_state.n_coe = preset.nippon_cost_of_equity * 100
        st.session_state.n_cod = preset.nippon_cost_of_debt * 100
        st.session_state.n_dr = preset.nippon_debt_ratio * 100
        st.session_state.n_tr = preset.nippon_tax_rate * 100
        st.session_state.reset_section = None

    us_10yr = st.sidebar.slider("US 10-Year Treasury", 2.0, 6.0, st.session_state.get('us_10yr', preset.us_10yr * 100), 0.25, format="%.2f%%",
                                 key="us_10yr",
                                 help="Current US government bond yield. Used to calculate interest rate differential with Japan.") / 100
    japan_10yr = st.sidebar.slider("Japan 10-Year JGB", 0.0, 2.0, st.session_state.get('japan_10yr', preset.japan_10yr * 100), 0.25, format="%.2f%%",
                                    key="japan_10yr",
                                    help="Current Japanese Government Bond yield. Japan's low rates give Nippon a cost of capital advantage.") / 100

    with st.sidebar.expander("Nippon WACC Components", expanded=False):
        st.caption("Build up Nippon's cost of capital in JPY")
        nippon_coe = st.slider("Cost of Equity", 3.0, 8.0, st.session_state.get('n_coe', preset.nippon_cost_of_equity * 100), 0.5, format="%.1f%%", key="n_coe",
                                help="Nippon's required return on equity in JPY. Lower than US due to Japan's lower risk-free rate.") / 100
        nippon_cod = st.slider("Cost of Debt", 0.5, 3.0, st.session_state.get('n_cod', preset.nippon_cost_of_debt * 100), 0.25, format="%.2f%%", key="n_cod",
                                help="Nippon's borrowing cost in JPY. Very low due to Japan's near-zero interest rate environment.") / 100
        nippon_debt_ratio = st.slider("Debt Ratio", 20.0, 50.0, st.session_state.get('n_dr', preset.nippon_debt_ratio * 100), 5.0, format="%.0f%%", key="n_dr",
                                       help="Nippon's debt as percentage of total capital. Affects weighted average.") / 100
        nippon_tax_rate = st.slider("Japan Tax Rate", 25.0, 35.0, st.session_state.get('n_tr', preset.nippon_tax_rate * 100), 1.0, format="%.0f%%", key="n_tr",
                                     help="Japan corporate tax rate. Interest is tax-deductible, reducing effective cost of debt.") / 100

    st.sidebar.markdown("---")

    # Capital Projects
    st.sidebar.header("Capital Projects")
    if st.sidebar.button("↺ Reset to Default", key="reset_capex", help=f"Reset capital projects to {selected_scenario_name} defaults"):
        st.session_state.reset_section = "capex"
        st.rerun()
    st.sidebar.caption("Select which investments to include in valuation")

    # Handle capital projects reset
    if st.session_state.reset_section == "capex":
        st.session_state.include_br2 = 'BR2 Mini Mill' in preset.include_projects
        st.session_state.include_gary = 'Gary Works BF' in preset.include_projects
        st.session_state.include_mon_valley = 'Mon Valley HSM' in preset.include_projects
        st.session_state.include_greenfield = 'Greenfield Mini Mill' in preset.include_projects
        st.session_state.include_mining = 'Mining Investment' in preset.include_projects
        st.session_state.include_fairfield = 'Fairfield Works' in preset.include_projects
        st.session_state.reset_section = None

    include_br2 = st.sidebar.checkbox("BR2 Mini Mill", value=st.session_state.get('include_br2', 'BR2 Mini Mill' in preset.include_projects),
                                       key="include_br2",
                                       help="$3.0B - Big River Steel Phase 2. Already committed and under construction. Adds 3M tons EAF capacity.")
    include_gary = st.sidebar.checkbox("Gary Works BF", value=st.session_state.get('include_gary', 'Gary Works BF' in preset.include_projects),
                                        key="include_gary",
                                        help="$3.1B - Blast furnace modernization. Extends life 20+ years. Required by NSA.")
    include_mon_valley = st.sidebar.checkbox("Mon Valley HSM", value=st.session_state.get('include_mon_valley', 'Mon Valley HSM' in preset.include_projects),
                                              key="include_mon_valley",
                                              help="$1.0B - Hot Strip Mill upgrade. Improves quality and efficiency.")
    include_greenfield = st.sidebar.checkbox("Greenfield Mini Mill", value=st.session_state.get('include_greenfield', 'Greenfield Mini Mill' in preset.include_projects),
                                              key="include_greenfield",
                                              help="$1.0B - New EAF mini mill at undisclosed location. Adds 1.5M tons capacity.")
    include_mining = st.sidebar.checkbox("Mining Investment", value=st.session_state.get('include_mining', 'Mining Investment' in preset.include_projects),
                                          key="include_mining",
                                          help="$0.8B - Keetac/Minntac iron ore expansion. Secures raw material supply.")
    include_fairfield = st.sidebar.checkbox("Fairfield Works", value=st.session_state.get('include_fairfield', 'Fairfield Works' in preset.include_projects),
                                             key="include_fairfield",
                                             help="$0.5B - Tubular segment modernization in Alabama.")

    include_projects = []
    if include_br2:
        include_projects.append("BR2 Mini Mill")
    if include_gary:
        include_projects.append("Gary Works BF")
    if include_mon_valley:
        include_projects.append("Mon Valley HSM")
    if include_greenfield:
        include_projects.append("Greenfield Mini Mill")
    if include_mining:
        include_projects.append("Mining Investment")
    if include_fairfield:
        include_projects.append("Fairfield Works")

    # Execution Factor (only for Nippon Commitments or when multiple projects enabled)
    execution_factor = 1.0
    if selected_scenario_type == ScenarioType.NIPPON_COMMITMENTS or len(include_projects) > 1:
        st.sidebar.markdown("---")
        st.sidebar.header("Execution Risk")
        execution_pct = st.sidebar.slider(
            "Execution Factor",
            min_value=50, max_value=100, value=100, step=5,
            format="%d%%",
            help="100% = full projected benefits achieved. 75% = 25% haircut to incremental project EBITDA/volume. Does not affect BR2 (already committed)."
        )
        execution_factor = execution_pct / 100.0
        st.sidebar.caption(f"Applies {execution_factor:.0%} to non-BR2 project benefits")

    # Breakup Fee Probabilities
    st.sidebar.markdown("---")
    st.sidebar.header("Breakup Fee Probabilities")
    st.sidebar.caption("Adjust deal outcome probabilities for risk analysis")

    with st.sidebar.expander("Deal Outcome Probabilities", expanded=False):
        st.markdown("**Customize probability assumptions:**")

        prob_deal_closes = st.slider(
            "Probability: Deal Closes",
            min_value=0.0, max_value=1.0, value=0.70, step=0.05,
            format="%.0f%%",
            help="Likelihood that deal closes successfully. Higher = less regulatory/political risk."
        )

        prob_nippon_walks = st.slider(
            "Probability: Nippon Walks",
            min_value=0.0, max_value=(1.0 - prob_deal_closes), value=min(0.20, 1.0 - prob_deal_closes), step=0.05,
            format="%.0f%%",
            help="Likelihood Nippon terminates (USS receives $565M fee). Regulatory block, financing failure, etc."
        )

        # USS walks is whatever's left
        prob_uss_walks = 1.0 - prob_deal_closes - prob_nippon_walks

        st.caption(f"**Probability: USS Walks** = {prob_uss_walks:.0%} (calculated)")
        st.caption("USS terminates (USS pays $565M fee). Superior proposal, board changes mind, etc.")

        if prob_uss_walks < 0:
            st.error("⚠️ Probabilities must sum to 100%. Adjust sliders.")
            prob_uss_walks = 0

    # Build the custom scenario
    price_scenario = SteelPriceScenario(
        name="Custom" if selected_scenario_type == ScenarioType.CUSTOM else preset.price_scenario.name,
        description="User-defined steel price assumptions",
        hrc_us_factor=hrc_factor,
        crc_us_factor=hrc_factor,  # Same as HRC for simplicity
        coated_us_factor=hrc_factor,
        hrc_eu_factor=eu_factor,
        octg_factor=octg_factor,
        annual_price_growth=annual_price_growth
    )

    volume_scenario = VolumeScenario(
        name="Custom" if selected_scenario_type == ScenarioType.CUSTOM else preset.volume_scenario.name,
        description="User-defined volume assumptions",
        flat_rolled_volume_factor=fr_vol_factor,
        mini_mill_volume_factor=mm_vol_factor,
        usse_volume_factor=usse_vol_factor,
        tubular_volume_factor=tub_vol_factor,
        flat_rolled_growth_adj=fr_growth_adj,
        mini_mill_growth_adj=mm_growth_adj,
        usse_growth_adj=usse_growth_adj,
        tubular_growth_adj=tub_growth_adj
    )

    custom_scenario = ModelScenario(
        name=selected_scenario_name,
        scenario_type=selected_scenario_type,
        description=preset.description if selected_scenario_type != ScenarioType.CUSTOM else "Custom scenario",
        price_scenario=price_scenario,
        volume_scenario=volume_scenario,
        uss_wacc=uss_wacc,
        terminal_growth=terminal_growth,
        exit_multiple=exit_multiple,
        us_10yr=us_10yr,
        japan_10yr=japan_10yr,
        nippon_cost_of_equity=nippon_coe,
        nippon_cost_of_debt=nippon_cod,
        nippon_debt_ratio=nippon_debt_ratio,
        nippon_tax_rate=nippon_tax_rate,
        include_projects=include_projects
    )

    return custom_scenario, selected_scenario_name, execution_factor


# =============================================================================
# MAIN CONTENT
# =============================================================================

def main():
    # Title
    st.title("USS / Nippon Steel Merger Analysis")
    st.markdown("**Price x Volume DCF Model with Scenario Analysis**")

    # Get assumptions from sidebar
    scenario, scenario_name, execution_factor = render_sidebar()

    # Run the model with execution factor
    model = PriceVolumeModel(scenario, execution_factor=execution_factor)
    analysis = model.run_full_analysis()

    consolidated = analysis['consolidated']
    segment_dfs = analysis['segment_dfs']
    jpy_wacc = analysis['jpy_wacc']
    usd_wacc = analysis['usd_wacc']
    val_uss = analysis['val_uss']
    val_nippon = analysis['val_nippon']
    financing_impact = analysis.get('financing_impact', {})

    # =========================================================================
    # KEY METRICS ROW
    # =========================================================================

    st.markdown("---")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "USS - No Sale",
            f"${val_uss['share_price']:.2f}",
            f"@ {scenario.uss_wacc*100:.1f}% WACC"
        )

    with col2:
        st.metric(
            "Value to Nippon",
            f"${val_nippon['share_price']:.2f}",
            f"@ {usd_wacc*100:.2f}% WACC"
        )

    with col3:
        vs_offer = val_nippon['share_price'] - 55
        st.metric(
            "vs $55 Offer",
            f"${vs_offer:+.2f}",
            "Premium" if vs_offer > 0 else "Discount"
        )

    with col4:
        wacc_advantage = (scenario.uss_wacc - usd_wacc) * 100
        st.metric(
            "WACC Advantage",
            f"{wacc_advantage:.2f}%",
            "IRP-adjusted"
        )

    with col5:
        total_fcf = consolidated['FCF'].sum()
        st.metric(
            "10Y FCF",
            f"${total_fcf/1000:.1f}B",
            f"{len(scenario.include_projects)} projects"
        )

    # =========================================================================
    # EXECUTIVE SUMMARY
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Executive Summary</h2>", unsafe_allow_html=True)

    # Quick summary metrics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **Investment Thesis**
        - $55 offer fair under conservative assumptions
        - Nippon's IRP-adjusted view: ~$75/share base case
        - WACC arbitrage: ~3.3% advantage
        """)
    with col2:
        st.markdown("""
        **Key Value Drivers**
        - Mini Mill segment: 43% of FCF
        - BR2 expansion: committed capacity
        - NSA investment: $14B if fully executed
        """)
    with col3:
        st.markdown("""
        **Key Risks**
        - Steel price volatility
        - Execution risk on capital projects
        - Golden Share constraints
        """)

    # Full executive summary in expander
    summary_path = Path(__file__).parent / "EXECUTIVE_SUMMARY.md"
    if summary_path.exists():
        with open(summary_path, 'r') as f:
            summary_content = f.read()
        with st.expander("View Full Executive Summary", expanded=False):
            st.markdown(summary_content)

    # =========================================================================
    # VALUATION DETAILS
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Valuation Details</h2>", unsafe_allow_html=True)

    st.markdown("""
    **How to read these tables:**
    - **PV of 10Y FCF**: Present value of projected free cash flows from 2024-2033
    - **PV Terminal (Gordon)**: Terminal value using perpetual growth formula: FCF × (1+g) / (WACC-g)
    - **PV Terminal (Exit Multiple)**: Terminal value using comparable company EV/EBITDA multiple
    - **Enterprise Value**: Blended average of Gordon Growth and Exit Multiple methods (50/50 weighting)
    - **Equity Bridge**: Adjustments for debt, cash, pension, and other items to convert EV to equity value
    - **Share Price**: Equity value divided by 225M shares outstanding
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("USS - No Sale")
        st.markdown(f"**WACC:** {scenario.uss_wacc*100:.1f}%")
        st.markdown(f"""
        | Component | Value |
        |-----------|------:|
        | PV of 10Y FCF | ${val_uss['sum_pv_fcf']:,.0f}M |
        | PV Terminal (Gordon) | ${val_uss['pv_tv_gordon']:,.0f}M |
        | PV Terminal (Exit Multiple) | ${val_uss['pv_tv_exit']:,.0f}M |
        | **Enterprise Value** | **${val_uss['ev_blended']:,.0f}M** |
        | Equity Bridge | ${val_uss['equity_bridge']:,.0f}M |
        | **Share Price** | **${val_uss['share_price']:.2f}** |
        """)
        st.caption("Using USS standalone cost of capital")

    with col2:
        st.subheader("Value to Nippon")
        st.markdown(f"**WACC:** {usd_wacc*100:.2f}% (IRP-adjusted)")
        st.markdown(f"""
        | Component | Value |
        |-----------|------:|
        | PV of 10Y FCF | ${val_nippon['sum_pv_fcf']:,.0f}M |
        | PV Terminal (Gordon) | ${val_nippon['pv_tv_gordon']:,.0f}M |
        | PV Terminal (Exit Multiple) | ${val_nippon['pv_tv_exit']:,.0f}M |
        | **Enterprise Value** | **${val_nippon['ev_blended']:,.0f}M** |
        | Equity Bridge | ${val_nippon['equity_bridge']:,.0f}M |
        | **Share Price** | **${val_nippon['share_price']:.2f}** |
        """)
        st.caption(f"Using Nippon's lower cost of capital ({jpy_wacc*100:.2f}% JPY → {usd_wacc*100:.2f}% USD)")

    # Key valuation assumptions
    st.markdown("### Key Assumptions")
    val_col1, val_col2, val_col3, val_col4 = st.columns(4)
    with val_col1:
        st.metric("Terminal Growth", f"{scenario.terminal_growth*100:.1f}%")
    with val_col2:
        st.metric("Exit Multiple", f"{scenario.exit_multiple:.1f}x EBITDA")
    with val_col3:
        shares_display = f"{financing_impact.get('total_shares', 225):.0f}M" if financing_impact.get('new_shares', 0) > 0 else "225M"
        st.metric("Shares Outstanding", shares_display)
    with val_col4:
        st.metric("Terminal Value Blend", "50/50 Gordon/Exit")

    # =========================================================================
    # BREAKUP FEE ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Breakup Fee Analysis</h2>", unsafe_allow_html=True)

    # Breakup fee constants
    BREAKUP_FEE = 565  # $M
    SHARES = 225  # M
    FEE_PER_SHARE = BREAKUP_FEE / SHARES
    OFFER_PRICE = 55.0

    st.info(f"""
    **Merger Agreement Terms (per 8-K filing):**
    - Breakup Fee: ${BREAKUP_FEE:,.0f}M (${FEE_PER_SHARE:.2f} per share)
    - Paid **by Nippon to USS** if deal fails due to regulatory block, financing failure, or Nippon walks
    - Paid **by USS to Nippon** if USS accepts a superior proposal, board changes recommendation, or shareholders vote down the deal
    """)

    st.markdown("### Deal Outcome Scenarios")

    bk_col1, bk_col2, bk_col3 = st.columns(3)

    with bk_col1:
        st.markdown("#### 1️⃣ Deal Closes")
        st.metric("USS Shareholders Receive", f"${OFFER_PRICE:.2f}/share",
                 help="Most likely outcome - deal closes successfully")
        st.caption(f"**Probability: {prob_deal_closes:.0%}**")
        st.caption("USS shareholders receive cash offer")

    with bk_col2:
        st.markdown("#### 2️⃣ Nippon Walks")
        uss_gets_fee_value = val_uss['share_price'] + FEE_PER_SHARE
        st.metric("USS Shareholders Get", f"${uss_gets_fee_value:.2f}/share",
                 f"+${FEE_PER_SHARE:.2f} breakup fee",
                 help="USS remains standalone but receives $565M breakup fee from Nippon")
        st.caption(f"**Probability: {prob_nippon_walks:.0%}**")
        st.caption("Regulatory block, financing failure, or Nippon backs out")

    with bk_col3:
        st.markdown("#### 3️⃣ USS Walks")
        uss_pays_fee_value = val_uss['share_price'] - FEE_PER_SHARE
        st.metric("USS Shareholders Get", f"${uss_pays_fee_value:.2f}/share",
                 f"-${FEE_PER_SHARE:.2f} breakup fee",
                 delta_color="inverse",
                 help="USS finds superior bid but must pay Nippon $565M breakup fee")
        st.caption(f"**Probability: {prob_uss_walks:.0%}**")
        st.caption("USS accepts superior proposal or shareholders vote down deal")

    # Expected value analysis
    st.markdown("### Expected Value Analysis")
    st.caption(f"Using probabilities: Deal Closes {prob_deal_closes:.0%} | Nippon Walks {prob_nippon_walks:.0%} | USS Walks {prob_uss_walks:.0%}")

    # Calculate expected values using user-adjustable probabilities
    expected_deal = (
        prob_deal_closes * OFFER_PRICE +
        prob_nippon_walks * uss_gets_fee_value +
        prob_uss_walks * uss_pays_fee_value
    )

    expected_nodeal = val_uss['share_price'] + (prob_nippon_walks * FEE_PER_SHARE)

    deal_premium = expected_deal - expected_nodeal

    ev_col1, ev_col2, ev_col3 = st.columns(3)

    with ev_col1:
        st.metric("Expected Deal Value",
                 f"${expected_deal:.2f}/share",
                 help="Probability-weighted value across all deal outcomes")
        st.caption(f"{prob_deal_closes:.0%} × ${OFFER_PRICE:.2f} + {prob_nippon_walks:.0%} × ${uss_gets_fee_value:.2f} + {prob_uss_walks:.0%} × ${uss_pays_fee_value:.2f}")

    with ev_col2:
        st.metric("Expected No-Deal Value",
                 f"${expected_nodeal:.2f}/share",
                 help="Standalone value plus expected breakup fee if Nippon walks")
        st.caption(f"${val_uss['share_price']:.2f} standalone + {prob_nippon_walks:.0%} × ${FEE_PER_SHARE:.2f} fee")

    with ev_col3:
        st.metric("Deal Premium",
                 f"${deal_premium:.2f}/share",
                 f"{deal_premium/expected_nodeal*100:+.1f}%",
                 help="How much better the deal is vs. remaining standalone")

    # Recommendation
    if deal_premium > 0:
        st.success(f"✅ **Deal is economically favorable**: Expected deal value (${expected_deal:.2f}) exceeds no-deal value (${expected_nodeal:.2f}) by ${deal_premium:.2f} per share")
    else:
        st.warning(f"⚠️ **No-deal may be better**: No-deal value (${expected_nodeal:.2f}) exceeds expected deal value (${expected_deal:.2f}) by ${abs(deal_premium):.2f} per share")

    # Key insights
    st.markdown("### Key Insights")

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:
        st.markdown("""
        **Downside Protection:**
        - If Nippon walks (regulatory/financing), USS gets breakup fee
        - Adjusted standalone value: ${:.2f}/share
        - Only ${:.2f} below the $55 offer
        - Provides cushion against deal failure
        """.format(uss_gets_fee_value, OFFER_PRICE - uss_gets_fee_value))

    with insight_col2:
        superior_bid_threshold = OFFER_PRICE + FEE_PER_SHARE
        st.markdown("""
        **Competing Bid Barrier:**
        - Another bidder must offer >${:.2f}/share
        - ($55 offer + ${:.2f} breakup fee USS would pay)
        - This is {:.1f}% above standalone value
        - Makes competing bids unlikely
        """.format(superior_bid_threshold, FEE_PER_SHARE,
                  (superior_bid_threshold/val_uss['share_price'] - 1)*100))

    # =========================================================================
    # BREAKUP FEE VISUALIZATIONS
    # =========================================================================

    st.markdown("### Deal Value Visualizations")

    viz_col1, viz_col2 = st.columns(2)

    with viz_col1:
        # Probability sensitivity chart
        st.markdown("#### Probability Sensitivity")

        prob_range = np.arange(0.50, 1.01, 0.05)
        sensitivity_data = []

        for p_close in prob_range:
            # Keep ratio of Nippon walks to USS walks constant (2:1)
            remaining = 1.0 - p_close
            p_nippon = remaining * 0.67
            p_uss = remaining * 0.33

            ev_deal = (
                p_close * OFFER_PRICE +
                p_nippon * uss_gets_fee_value +
                p_uss * uss_pays_fee_value
            )

            ev_nodeal = val_uss['share_price'] + (p_nippon * FEE_PER_SHARE)

            sensitivity_data.append({
                'P(Deal Closes)': p_close,
                'Expected Deal Value': ev_deal,
                'Expected No-Deal Value': ev_nodeal
            })

        sens_df = pd.DataFrame(sensitivity_data)

        fig_sens = go.Figure()

        fig_sens.add_trace(go.Scatter(
            x=sens_df['P(Deal Closes)'] * 100,
            y=sens_df['Expected Deal Value'],
            mode='lines+markers',
            name='Expected Deal Value',
            line=dict(color='#4CAF50', width=3),
            marker=dict(size=8)
        ))

        fig_sens.add_trace(go.Scatter(
            x=sens_df['P(Deal Closes)'] * 100,
            y=sens_df['Expected No-Deal Value'],
            mode='lines+markers',
            name='Expected No-Deal Value',
            line=dict(color='#FF9800', width=3, dash='dash'),
            marker=dict(size=8)
        ))

        # Add current probability indicator
        fig_sens.add_vline(x=prob_deal_closes * 100, line_dash="dot", line_color="red",
                          annotation_text=f"Current: {prob_deal_closes:.0%}")

        fig_sens.add_hline(y=OFFER_PRICE, line_dash="dash", line_color="green",
                          annotation_text="$55 Offer", annotation_position="right")

        fig_sens.update_layout(
            xaxis_title='Probability Deal Closes (%)',
            yaxis_title='Share Value ($)',
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig_sens, use_container_width=True)
        st.caption("How expected values change with deal completion probability")

    with viz_col2:
        # Scenario comparison with breakup fee
        st.markdown("#### Expected Deal Value by Scenario")

        # Calculate expected deal values for all scenarios
        scenario_comparison_data = []

        for scenario_type in [ScenarioType.CONSERVATIVE, ScenarioType.BASE_CASE,
                            ScenarioType.WALL_STREET, ScenarioType.MANAGEMENT,
                            ScenarioType.NIPPON_COMMITMENTS]:
            scenario_preset = get_scenario_presets()[scenario_type]
            temp_model = PriceVolumeModel(scenario_preset, execution_factor=execution_factor)
            temp_analysis = temp_model.run_full_analysis()

            standalone = temp_analysis['val_uss']['share_price']
            gets_fee = standalone + FEE_PER_SHARE
            pays_fee = standalone - FEE_PER_SHARE

            ev_deal = (
                prob_deal_closes * OFFER_PRICE +
                prob_nippon_walks * gets_fee +
                prob_uss_walks * pays_fee
            )

            scenario_comparison_data.append({
                'Scenario': scenario_preset.name,
                'USS Standalone': standalone,
                'Expected Deal Value': ev_deal,
                'vs $55 Offer': ev_deal - OFFER_PRICE
            })

        scenario_df = pd.DataFrame(scenario_comparison_data)

        fig_scenario = go.Figure()

        fig_scenario.add_trace(go.Bar(
            x=scenario_df['Scenario'],
            y=scenario_df['USS Standalone'],
            name='USS Standalone',
            marker_color='#2196F3',
            opacity=0.7
        ))

        fig_scenario.add_trace(go.Bar(
            x=scenario_df['Scenario'],
            y=scenario_df['Expected Deal Value'],
            name='Expected Deal Value',
            marker_color='#4CAF50',
            opacity=0.7
        ))

        fig_scenario.add_hline(y=OFFER_PRICE, line_dash="dash", line_color="green",
                              annotation_text="$55 Offer")

        fig_scenario.update_layout(
            xaxis_title='Scenario',
            yaxis_title='Share Value ($)',
            barmode='group',
            height=400
        )

        st.plotly_chart(fig_scenario, use_container_width=True)
        st.caption("Breakup fee impact varies by scenario (standalone value changes)")

    # =========================================================================
    # FINANCING IMPACT (only show when there are incremental projects)
    # =========================================================================

    if financing_impact.get('financing_gap', 0) > 0:
        st.markdown("---")
        st.markdown("<h2 style='text-decoration: underline;'>USS Standalone Financing Impact</h2>", unsafe_allow_html=True)

        st.warning("""
        **Why USS - No Sale value is lower:** USS cannot fund large capital projects from operating cash flow alone.
        To execute the selected projects without Nippon, USS would need to issue debt and equity, which:
        - Increases interest expense (reducing FCF)
        - Dilutes existing shareholders
        - Raises cost of capital (higher WACC)

        **Nippon does not face these costs** because they have the balance sheet capacity to fund $14B+ in investments.
        """)

        fin_col1, fin_col2, fin_col3 = st.columns(3)

        with fin_col1:
            st.markdown("#### Financing Required")
            st.markdown(f"""
            | Item | Amount |
            |------|-------:|
            | Incremental CapEx | ${financing_impact['incremental_capex']:,.0f}M |
            | Cumulative Cash Shortfall | ${financing_impact['financing_gap']:,.0f}M |
            | New Debt (50%) | ${financing_impact['new_debt']:,.0f}M |
            | New Equity (50%) | ${financing_impact['new_equity']:,.0f}M |
            """)

        with fin_col2:
            st.markdown("#### Shareholder Impact")
            st.markdown(f"""
            | Item | Value |
            |------|------:|
            | Current Shares | 225M |
            | New Shares Issued | {financing_impact['new_shares']:,.1f}M |
            | **Total Shares** | **{financing_impact['total_shares']:,.1f}M** |
            | **Dilution** | **{financing_impact['dilution_pct']*100:.1f}%** |
            """)

        with fin_col3:
            st.markdown("#### Cost of Capital Impact")
            st.markdown(f"""
            | Item | Value |
            |------|------:|
            | Base WACC | {scenario.uss_wacc*100:.1f}% |
            | WACC Adjustment | +{financing_impact['wacc_adjustment']*100:.2f}% |
            | **Adjusted WACC** | **{financing_impact['adjusted_wacc']*100:.2f}%** |
            | Annual Interest | ${financing_impact['annual_interest_expense']:,.0f}M |
            """)

        # Calculate value destruction
        # Get what value would be without financing impact
        val_uss_no_financing = model.calculate_dcf(consolidated, scenario.uss_wacc, None)
        value_destroyed = val_uss_no_financing['share_price'] - val_uss['share_price']

        st.markdown("#### Value Impact Summary")
        imp_col1, imp_col2, imp_col3 = st.columns(3)
        with imp_col1:
            st.metric("Without Financing Costs", f"${val_uss_no_financing['share_price']:.2f}")
        with imp_col2:
            st.metric("With Financing Costs", f"${val_uss['share_price']:.2f}", f"-${value_destroyed:.2f}")
        with imp_col3:
            st.metric("Total Value Destroyed", f"${value_destroyed * 225:,.0f}M", "by financing costs")

        st.info("""
        **Key Insight:** Even if USS tried to execute the NSA investment program standalone,
        the financing costs would destroy significant shareholder value. This is why the
        merger creates value - Nippon can fund the investments without these penalties.
        """)

    # =========================================================================
    # SCENARIO COMPARISON
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Scenario Comparison</h2>", unsafe_allow_html=True)

    # Run comparison across all preset scenarios (with execution factor applied to Nippon Commitments)
    comparison_df = compare_scenarios(execution_factor=execution_factor)

    # Add breakup fee expected value calculations to comparison table
    BREAKUP_FEE_SHARE = 2.51  # $565M / 225M shares
    OFFER = 55.0

    comparison_df['Expected Deal Value ($/sh)'] = comparison_df.apply(
        lambda row: (
            prob_deal_closes * OFFER +
            prob_nippon_walks * (row['USS - No Sale ($/sh)'] + BREAKUP_FEE_SHARE) +
            prob_uss_walks * (row['USS - No Sale ($/sh)'] - BREAKUP_FEE_SHARE)
        ),
        axis=1
    )

    comparison_df['Deal Premium ($/sh)'] = comparison_df['Expected Deal Value ($/sh)'] - comparison_df['USS - No Sale ($/sh)']

    # Highlight the current scenario
    comparison_df['Current'] = comparison_df['Scenario'] == scenario_name

    # View toggle for USS vs Nippon perspective
    col_toggle, col_spacer = st.columns([1, 3])
    with col_toggle:
        valuation_view = st.radio(
            "Valuation Perspective",
            options=["Value to Nippon (Acquirer's View)", "USS - No Sale (Status Quo)"],
            horizontal=True,
            help="Value to Nippon: What USS is worth to Nippon using their lower cost of capital (~7.5% WACC). USS - No Sale: What USS is worth as a standalone company (~10.9% WACC)."
        )

    # Determine which column to use for the chart
    if valuation_view == "Value to Nippon (Acquirer's View)":
        value_column = 'Value to Nippon ($/sh)'
        chart_title = 'Share Value by Scenario (Value to Nippon @ 7.5% WACC)'
        wacc_label = "~7.5% WACC"
    else:
        value_column = 'USS - No Sale ($/sh)'
        chart_title = 'Share Value by Scenario (USS - No Sale @ 10.9% WACC)'
        wacc_label = "~10.9% WACC"

    # Bar chart comparing scenarios (above table)
    fig = px.bar(
        comparison_df,
        x='Scenario',
        y=value_column,
        color='Scenario',
        title=chart_title,
        color_discrete_sequence=['#ff6b6b', '#ffa07a', '#98d8c8', '#7fcdbb', '#4ecdc4', '#45b7d1']
    )
    fig.add_hline(y=55, line_dash="dash", line_color="green", annotation_text="$55 Offer")
    fig.add_hline(y=0, line_color="black", line_width=1)
    fig.update_layout(showlegend=False, yaxis_title=f"Share Price ($) [{wacc_label}]")
    st.plotly_chart(fig, use_container_width=True)

    # Summary table (below chart)
    st.markdown("""
    **How to read this table:**
    - **USS - No Sale**: Share value if USS remains independent (discounted at USS's ~10.9% WACC)
    - **Value to Nippon**: Share value from Nippon's perspective (discounted at Nippon's ~7.5% IRP-adjusted WACC)
    - **Expected Deal Value**: Probability-weighted value accounting for breakup fee scenarios
    - **Deal Premium**: How much better the deal is vs. staying standalone
    - **10Y FCF**: Total free cash flow generated over the 10-year forecast period (2024-2033)
    - The difference between the two valuations reflects the "WACC advantage" Nippon gains from its lower cost of capital
    """)
    display_df = comparison_df[['Scenario', 'USS - No Sale ($/sh)', 'Value to Nippon ($/sh)',
                                'Expected Deal Value ($/sh)', 'Deal Premium ($/sh)', '10Y FCF ($B)']].copy()
    display_df['USS - No Sale ($/sh)'] = display_df['USS - No Sale ($/sh)'].apply(lambda x: f"${x:.2f}")
    display_df['Value to Nippon ($/sh)'] = display_df['Value to Nippon ($/sh)'].apply(lambda x: f"${x:.2f}")
    display_df['Expected Deal Value ($/sh)'] = display_df['Expected Deal Value ($/sh)'].apply(lambda x: f"${x:.2f}")
    display_df['Deal Premium ($/sh)'] = display_df['Deal Premium ($/sh)'].apply(lambda x: f"${x:+.2f}")
    display_df['10Y FCF ($B)'] = display_df['10Y FCF ($B)'].apply(lambda x: f"${x:.1f}B")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.info(f"""
    **Breakup Fee Impact on Scenario Comparison:**
    Using current probabilities ({prob_deal_closes:.0%} deal closes, {prob_nippon_walks:.0%} Nippon walks, {prob_uss_walks:.0%} USS walks),
    the Expected Deal Value accounts for all three possible outcomes. The Deal Premium shows how much better
    (or worse) taking the deal is compared to remaining standalone in each scenario.
    """)

    # =========================================================================
    # CAPITAL PROJECTS ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Capital Projects Analysis</h2>", unsafe_allow_html=True)

    # Get all capital projects
    all_projects = get_capital_projects()

    # Project overview table
    st.markdown("### Project Overview")
    st.markdown("""
    **How to read this table:**
    - **Total CapEx**: Total investment required over the project life
    - **2033 EBITDA**: Steady-state annual EBITDA once project is fully operational
    - **Included**: Whether this project is included in the current scenario
    """)

    project_overview = []
    for proj_name, proj in all_projects.items():
        total_capex = sum(proj.capex_schedule.values())
        final_ebitda = proj.ebitda_schedule.get(2033, 0)
        is_included = proj_name in scenario.include_projects

        # Calculate simple NPV at different rates
        def calc_project_npv(wacc):
            npv = 0
            for year in range(2024, 2034):
                t = year - 2024
                capex = proj.capex_schedule.get(year, 0)
                ebitda = proj.ebitda_schedule.get(year, 0)
                # Assume 25% tax, 60% EBITDA-to-FCF conversion for projects
                fcf = ebitda * 0.6 - capex
                npv += fcf / ((1 + wacc) ** (t + 0.5))
            # Add terminal value (5x 2033 EBITDA, 60% FCF conversion)
            tv = final_ebitda * 0.6 * 5
            npv += tv / ((1 + wacc) ** 10)
            return npv

        npv_uss = calc_project_npv(scenario.uss_wacc)
        npv_nippon = calc_project_npv(usd_wacc)

        project_overview.append({
            'Project': proj_name,
            'Segment': proj.segment,
            'Total CapEx ($M)': f"${total_capex:,.0f}",
            '2033 EBITDA ($M)': f"${final_ebitda:,.0f}",
            'NPV @ USS WACC': f"${npv_uss:,.0f}M",
            'NPV @ Nippon WACC': f"${npv_nippon:,.0f}M",
            'Included': '✓' if is_included else '—'
        })

    st.dataframe(pd.DataFrame(project_overview), use_container_width=True, hide_index=True)

    # Project detail selector
    st.markdown("### Project Deep Dive")
    selected_project = st.selectbox(
        "Select a project to analyze",
        options=list(all_projects.keys()),
        help="View detailed cash flow schedule and NPV sensitivity for each project"
    )

    proj = all_projects[selected_project]
    total_capex = sum(proj.capex_schedule.values())
    final_ebitda = proj.ebitda_schedule.get(2033, 0)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### {selected_project}")
        st.markdown(f"""
        | Attribute | Value |
        |-----------|-------|
        | Segment | {proj.segment} |
        | Total Investment | ${total_capex:,.0f}M |
        | Steady-State EBITDA | ${final_ebitda:,.0f}M/year |
        | Payback (Simple) | {total_capex / max(final_ebitda * 0.6, 1):.1f} years |
        | Status | {'**Included**' if selected_project in scenario.include_projects else 'Not included'} |
        """)

        # Project descriptions
        project_descriptions = {
            'BR2 Mini Mill': "Big River Steel Phase 2 expansion in Osceola, AR. Adds 3M tons EAF capacity. **Already committed** and under construction.",
            'Gary Works BF': "Blast furnace modernization at Gary Works, IN. Extends BF life 20+ years. Required by NSA to maintain integrated capacity.",
            'Mon Valley HSM': "Hot Strip Mill upgrade at Mon Valley Works. Improves quality and efficiency of existing rolling capacity.",
            'Greenfield Mini Mill': "New mini mill at undisclosed location. Adds 1.5M tons EAF capacity in underserved region.",
            'Mining Investment': "Expansion of Keetac and Minntac iron ore operations. Ensures raw material supply for integrated mills.",
            'Fairfield Works': "Tubular modernization at Fairfield, AL. Upgrades OCTG production capabilities."
        }
        st.info(project_descriptions.get(selected_project, "Capital investment project"))

    with col2:
        # Cash flow chart
        years = list(range(2024, 2034))
        capex_values = [proj.capex_schedule.get(y, 0) for y in years]
        ebitda_values = [proj.ebitda_schedule.get(y, 0) for y in years]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years,
            y=[-c for c in capex_values],  # Negative for outflows
            name='CapEx (Outflow)',
            marker_color='#ff6b6b'
        ))
        fig.add_trace(go.Bar(
            x=years,
            y=ebitda_values,
            name='EBITDA (Inflow)',
            marker_color='#4ecdc4'
        ))
        fig.update_layout(
            title=f'{selected_project}: Cash Flow Profile',
            xaxis_title='Year',
            yaxis_title='$M',
            barmode='relative',
            height=350
        )
        fig.add_hline(y=0, line_color="black", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

    # NPV sensitivity table
    st.markdown("#### NPV Sensitivity to Discount Rate")
    st.markdown("""
    **How to read this table:**
    - **WACC**: Discount rate used (6% = low risk, 13.5% = high risk)
    - **NPV**: Net Present Value of the project (positive = value-creating)
    - **vs CapEx**: NPV as a percentage of total investment (>0% means project creates value)
    - Projects are more attractive at lower WACCs; Nippon's ~7.5% WACC makes projects more valuable than at USS's ~10.9%
    """)
    wacc_range = [0.06, 0.075, 0.09, 0.105, 0.12, 0.135]
    npv_data = []
    for w in wacc_range:
        npv = 0
        for year in range(2024, 2034):
            t = year - 2024
            capex = proj.capex_schedule.get(year, 0)
            ebitda = proj.ebitda_schedule.get(year, 0)
            fcf = ebitda * 0.6 - capex
            npv += fcf / ((1 + w) ** (t + 0.5))
        tv = final_ebitda * 0.6 * 5
        npv += tv / ((1 + w) ** 10)
        npv_data.append({
            'WACC': f"{w*100:.1f}%",
            'NPV ($M)': f"${npv:,.0f}",
            'vs CapEx': f"{npv/total_capex*100:+.0f}%" if total_capex > 0 else "N/A"
        })
    st.dataframe(pd.DataFrame(npv_data), use_container_width=True, hide_index=True)

    # =========================================================================
    # VALUE BRIDGE
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Value Bridge</h2>", unsafe_allow_html=True)

    st.markdown("""
    **How to read this chart:**
    - This waterfall shows how value builds from USS standalone to Nippon's $55 offer
    - **USS - No Sale**: Starting point - what USS is worth on its own
    - **WACC Advantage**: Value added because Nippon has a lower cost of capital
    - **Value to Nippon**: Total intrinsic value from Nippon's perspective
    - **Gap to Offer**: Difference between intrinsic value and $55 offer (negative = Nippon buying at discount)
    """)

    wacc_arbitrage = val_nippon['share_price'] - val_uss['share_price']
    gap_to_offer = 55 - val_nippon['share_price']

    # Waterfall chart
    fig = go.Figure(go.Waterfall(
        name="Value Bridge",
        orientation="v",
        measure=["absolute", "relative", "total", "relative", "total"],
        x=["USS - No Sale", "WACC Advantage", "Value to Nippon", "Gap to Offer", "Nippon Offer"],
        y=[val_uss['share_price'], wacc_arbitrage, 0, gap_to_offer, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        increasing={"marker": {"color": "#4ecdc4"}},
        totals={"marker": {"color": "#45b7d1"}}
    ))

    fig.update_layout(
        title="Value Bridge: USS - No Sale → Nippon Offer",
        yaxis_title="Share Price ($)",
        showlegend=False,
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**USS - No Sale:** ${val_uss['share_price']:.2f}")
    with col2:
        st.success(f"**WACC Advantage:** +${wacc_arbitrage:.2f} ({wacc_advantage:.2f}% lower cost of capital)")
    with col3:
        if gap_to_offer < 0:
            st.warning(f"**Nippon buying at discount:** ${gap_to_offer:.2f}")
        else:
            st.warning(f"**Synergies needed:** ${gap_to_offer:.2f}")

    # =========================================================================
    # FCF PROJECTION
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>FCF Projection</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        # FCF chart by segment over time
        fcf_time_data = []
        for name, df in segment_dfs.items():
            for _, row in df.iterrows():
                fcf_time_data.append({
                    'Year': row['Year'],
                    'Segment': name,
                    'FCF': row['FCF']
                })

        fcf_time_df = pd.DataFrame(fcf_time_data)

        fig = px.bar(
            fcf_time_df,
            x='Year',
            y='FCF',
            color='Segment',
            title='Annual FCF by Segment',
            barmode='relative',
            color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        )
        fig.add_hline(y=0, line_color="black", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Consolidated metrics
        st.subheader("Consolidated Metrics")
        st.metric("2024 FCF", f"${consolidated['FCF'].iloc[0]:,.0f}M")
        st.metric("2033 FCF", f"${consolidated['FCF'].iloc[-1]:,.0f}M")
        st.metric("10Y Total", f"${consolidated['FCF'].sum():,.0f}M")
        st.metric("Avg EBITDA Margin", f"{consolidated['EBITDA_Margin'].mean()*100:.1f}%")

    # =========================================================================
    # SEGMENT ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Segment Analysis</h2>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # FCF by segment
        segment_fcf = {name: df['FCF'].sum() for name, df in segment_dfs.items()}
        fcf_df = pd.DataFrame({
            'Segment': list(segment_fcf.keys()),
            'FCF': list(segment_fcf.values())
        })

        fig = px.bar(
            fcf_df,
            x='Segment',
            y='FCF',
            color='Segment',
            title='10-Year FCF by Segment ($M)',
            color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        )
        fig.add_hline(y=0, line_color="black", line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # FCF contribution pie (only positive)
        positive_fcf = {k: v for k, v in segment_fcf.items() if v > 0}
        if positive_fcf:
            pie_df = pd.DataFrame({
                'Segment': list(positive_fcf.keys()),
                'FCF': list(positive_fcf.values())
            })
            fig = px.pie(
                pie_df,
                values='FCF',
                names='Segment',
                title='Positive FCF Contribution by Segment',
                color_discrete_sequence=['#4ecdc4', '#45b7d1', '#96ceb4', '#ff6b6b']
            )
            st.plotly_chart(fig, use_container_width=True)

    # Segment metrics table with volume and price
    st.subheader("Segment Summary")
    st.markdown("""
    **How to read this table:**
    - **2024 Volume**: Starting production volume in thousands of tons
    - **2024 Price**: Realized price per ton (includes product mix premium over benchmark)
    - **10Y Revenue/FCF**: Cumulative totals over the 2024-2033 forecast period
    - **Avg Margin**: Average EBITDA margin across the forecast period
    - Mini Mill has highest margins; Flat-Rolled faces structural headwinds
    """)

    segment_summary = []
    for name, df in segment_dfs.items():
        segment_summary.append({
            'Segment': name,
            '2024 Volume (000t)': f"{df['Volume_000tons'].iloc[0]:,.0f}",
            '2024 Price ($/t)': f"${df['Price_per_ton'].iloc[0]:,.0f}",
            '10Y Revenue ($B)': f"${df['Revenue'].sum()/1000:.1f}",
            '10Y FCF ($M)': f"${df['FCF'].sum():,.0f}",
            'Avg Margin': f"{df['EBITDA_Margin'].mean()*100:.1f}%"
        })

    st.dataframe(pd.DataFrame(segment_summary), use_container_width=True, hide_index=True)

    # =========================================================================
    # STEEL PRICE SENSITIVITY
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Steel Price Sensitivity</h2>", unsafe_allow_html=True)

    st.markdown("""
    **How to read this section:**
    - Steel prices are the #1 driver of valuation - a 10% price swing changes share value by $15-25
    - **Price Factor**: Multiplier applied to 2023 benchmark prices (0.8 = 20% below, 1.2 = 20% above)
    - The chart shows how share value changes as steel prices move up or down
    - Green dashed line = $55 Nippon offer price (breakeven around 88% price factor)
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Price factor sensitivity
        price_factors = np.arange(0.6, 1.5, 0.1)
        sensitivity_data = []

        for pf in price_factors:
            # Create modified scenario
            test_price_scenario = SteelPriceScenario(
                name="Test",
                description="Test",
                hrc_us_factor=pf,
                crc_us_factor=pf,
                coated_us_factor=pf,
                hrc_eu_factor=pf,
                octg_factor=pf,
                annual_price_growth=scenario.price_scenario.annual_price_growth
            )

            test_scenario = ModelScenario(
                name="Test",
                scenario_type=ScenarioType.CUSTOM,
                description="Test",
                price_scenario=test_price_scenario,
                volume_scenario=scenario.volume_scenario,
                uss_wacc=scenario.uss_wacc,
                terminal_growth=scenario.terminal_growth,
                exit_multiple=scenario.exit_multiple,
                us_10yr=scenario.us_10yr,
                japan_10yr=scenario.japan_10yr,
                nippon_cost_of_equity=scenario.nippon_cost_of_equity,
                nippon_cost_of_debt=scenario.nippon_cost_of_debt,
                nippon_debt_ratio=scenario.nippon_debt_ratio,
                nippon_tax_rate=scenario.nippon_tax_rate,
                include_projects=scenario.include_projects
            )

            test_model = PriceVolumeModel(test_scenario)
            test_analysis = test_model.run_full_analysis()

            sensitivity_data.append({
                'Price Factor': f"{pf:.0%}",
                'Price Factor Num': pf,
                'Nippon Value': test_analysis['val_nippon']['share_price'],
                'USS Value': test_analysis['val_uss']['share_price']
            })

        sens_df = pd.DataFrame(sensitivity_data)

        fig = px.line(
            sens_df,
            x='Price Factor',
            y='Nippon Value',
            title='Share Value vs Steel Price Level',
            markers=True
        )
        fig.add_hline(y=55, line_dash="dash", line_color="green", annotation_text="$55 Offer")
        fig.add_hline(y=0, line_color="black", line_width=1)
        fig.update_layout(yaxis_title='Share Price ($)')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Volume and price projections
        st.subheader("Price Projections by Segment")

        price_proj_data = []
        for seg_name, df in segment_dfs.items():
            for _, row in df.iterrows():
                price_proj_data.append({
                    'Year': row['Year'],
                    'Segment': seg_name,
                    'Price': row['Price_per_ton']
                })

        price_proj_df = pd.DataFrame(price_proj_data)

        fig = px.line(
            price_proj_df,
            x='Year',
            y='Price',
            color='Segment',
            title='Realized Price by Segment ($/ton)',
            markers=True,
            color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        )
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # WACC SENSITIVITY
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>WACC Sensitivity Analysis</h2>", unsafe_allow_html=True)

    st.markdown("""
    **How to read this chart:**
    - **WACC (Weighted Average Cost of Capital)**: The discount rate used to calculate present value
    - Lower WACC = higher valuation (future cash flows are worth more today)
    - **Blue dashed line**: USS's standalone WACC (~10.9%)
    - **Red dashed line**: Nippon's IRP-adjusted WACC (~7.5%)
    - **Green dashed line**: $55 offer price
    - The gap between blue and red lines shows the "WACC advantage" Nippon gains from its lower cost of capital
    """)

    wacc_range = np.arange(0.05, 0.14, 0.005)
    wacc_sensitivity_data = []

    for w in wacc_range:
        val = model.calculate_dcf(consolidated, w)
        wacc_sensitivity_data.append({
            'WACC': w * 100,
            'Share Price': val['share_price']
        })

    wacc_sens_df = pd.DataFrame(wacc_sensitivity_data)

    fig = px.line(
        wacc_sens_df,
        x='WACC',
        y='Share Price',
        title='Share Price vs WACC',
        markers=True
    )

    # Add reference lines
    fig.add_hline(y=55, line_dash="dash", line_color="green",
                  annotation_text="Nippon Offer ($55)")
    fig.add_vline(x=scenario.uss_wacc*100, line_dash="dash", line_color="blue",
                  annotation_text=f"USS WACC ({scenario.uss_wacc*100:.1f}%)")
    fig.add_vline(x=usd_wacc*100, line_dash="dash", line_color="red",
                  annotation_text=f"Nippon USD WACC ({usd_wacc*100:.2f}%)")

    fig.update_layout(
        xaxis_title='WACC (%)',
        yaxis_title='Share Price ($)',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # INTEREST RATE PARITY ADJUSTMENT
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Interest Rate Parity Adjustment</h2>", unsafe_allow_html=True)

    st.markdown("""
    **Why this matters:**
    - Nippon (a Japanese company) has a lower cost of capital in JPY than USS has in USD
    - To fairly compare, we must convert Nippon's JPY WACC to a USD-equivalent using Interest Rate Parity
    - The IRP adjustment accounts for the interest rate differential between US and Japan
    - This creates a "WACC advantage" for Nippon - the same cash flows are worth more to them
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### WACC Conversion Formula")
        st.markdown("""
        The Interest Rate Parity (IRP) formula converts Nippon's JPY-based WACC
        to a USD-equivalent rate:
        """)
        st.latex(r"\text{WACC}_{\text{USD}} = (1 + \text{WACC}_{\text{JPY}}) \cdot \frac{1 + r_{\text{US}}}{1 + r_{\text{JP}}} - 1")

        st.markdown("### Calculation")
        st.markdown(f"""
        | Input | Value |
        |-------|-------|
        | Nippon JPY WACC | {jpy_wacc*100:.2f}% |
        | US 10-Year Treasury | {scenario.us_10yr*100:.2f}% |
        | Japan 10-Year JGB | {scenario.japan_10yr*100:.2f}% |
        | Interest Rate Differential | {(scenario.us_10yr-scenario.japan_10yr)*100:.2f}% |

        **Result:**
        ```
        USD WACC = (1 + {jpy_wacc:.4f}) × (1 + {scenario.us_10yr:.4f}) / (1 + {scenario.japan_10yr:.4f}) - 1
        USD WACC = {usd_wacc*100:.2f}%
        ```
        """)

    with col2:
        # WACC comparison chart
        wacc_data = pd.DataFrame({
            'Category': ['Nippon JPY WACC\n(Naive)', 'Nippon USD WACC\n(IRP Adjusted)', 'USS WACC'],
            'WACC': [jpy_wacc * 100, usd_wacc * 100, scenario.uss_wacc * 100],
            'Color': ['#ff6b6b', '#4ecdc4', '#45b7d1']
        })

        fig = px.bar(
            wacc_data,
            x='Category',
            y='WACC',
            color='Category',
            color_discrete_sequence=['#ff6b6b', '#4ecdc4', '#45b7d1'],
            title='WACC Comparison'
        )
        fig.update_layout(showlegend=False, yaxis_title='WACC (%)')
        fig.add_hline(y=jpy_wacc*100, line_dash="dash", line_color="red",
                      annotation_text="JPY WACC (Wrong for USD CF)")
        st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # DETAILED TABLES
    # =========================================================================

    st.markdown("---")
    st.markdown("<h2 style='text-decoration: underline;'>Detailed Projections</h2>", unsafe_allow_html=True)

    st.markdown("""
    **Detailed data tables** - Click to expand:
    - **Consolidated Financial Projection**: Year-by-year Revenue, EBITDA, CapEx, and FCF for the full company
    - **Scenario Details**: Current scenario assumptions including price factors, volume factors, and included projects
    """)

    with st.expander("Consolidated Financial Projection"):
        st.markdown("""
        **Column definitions:**
        - **Revenue**: Total sales across all segments
        - **Total_EBITDA**: Earnings Before Interest, Taxes, Depreciation & Amortization
        - **DA**: Depreciation & Amortization expense
        - **NOPAT**: Net Operating Profit After Tax (EBITDA - DA - Taxes)
        - **Gross_CF**: Cash flow before capital expenditures
        - **Total_CapEx**: Capital expenditures (maintenance + growth projects)
        - **Delta_WC**: Change in working capital (negative = cash outflow)
        - **FCF**: Free Cash Flow (Gross_CF - CapEx - Delta_WC)
        """)
        display_df = consolidated.copy()
        display_df['EBITDA_Margin'] = display_df['EBITDA_Margin'].apply(lambda x: f"{x*100:.1f}%")
        display_df['Total_Volume_000tons'] = display_df['Total_Volume_000tons'].apply(lambda x: f"{x:,.0f}")
        display_df['Avg_Price_per_ton'] = display_df['Avg_Price_per_ton'].apply(lambda x: f"${x:,.0f}")
        for col in ['Revenue', 'Total_EBITDA', 'DA', 'NOPAT', 'Gross_CF', 'Total_CapEx', 'Delta_WC', 'FCF']:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}M")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with st.expander("Scenario Details"):
        st.markdown(f"""
        **Scenario:** {scenario.name}

        **Price Scenario:** {scenario.price_scenario.name}
        - {scenario.price_scenario.description}
        - US HRC Factor: {scenario.price_scenario.hrc_us_factor:.0%}
        - EU HRC Factor: {scenario.price_scenario.hrc_eu_factor:.0%}
        - OCTG Factor: {scenario.price_scenario.octg_factor:.0%}
        - Annual Price Growth: {scenario.price_scenario.annual_price_growth:.1%}

        **Volume Scenario:** {scenario.volume_scenario.name}
        - {scenario.volume_scenario.description}

        **Capital Projects Included:** {', '.join(scenario.include_projects) if scenario.include_projects else 'None'}

        **Execution Factor:** {execution_factor:.0%}
        """)

    # =========================================================================
    # FOOTER
    # =========================================================================

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px;'>
    USS / Nippon Steel Merger Analysis | RAMBAS Team Capstone Project | January 2026<br>
    Adjust assumptions in the sidebar to see real-time valuation impacts
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
