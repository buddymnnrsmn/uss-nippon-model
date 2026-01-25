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
    calculate_probability_weighted_valuation,
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

    # Page Navigation
    with st.sidebar.expander("Page Navigation", expanded=False):
        st.markdown("""
        **Executive Analysis**
        - [Executive Decision Summary](#executive-decision-summary)
        - [Risk-Adjusted Decision Matrix](#risk-adjusted-decision-matrix)
        - [Board Fiduciary Checklist](#board-fiduciary-checklist)

        **Strategic Context**
        - [Without the Deal](#without-the-deal)
        - [Golden Share & NSA Commitments](#golden-share-nsa)
        - [Alternative Buyer Comparison](#alternative-buyer-comparison)
        - [Sensitivity Thresholds](#sensitivity-thresholds)

        **Valuation Details**
        - [Valuation Details](#valuation-details)
        - [USS Standalone Financing Impact](#uss-standalone-financing)
        - [Scenario Comparison](#scenario-comparison)
        - [Probability-Weighted Expected Value](#probability-weighted-value)
        - [Capital Projects Analysis](#capital-projects)
        - [PE LBO Comparison](#pe-lbo-comparison)
        - [Valuation Football Field](#valuation-football-field)
        - [Value Bridge](#value-bridge)

        **Financial Projections**
        - [FCF Projection](#fcf-projection)
        - [Segment Analysis](#segment-analysis)

        **Sensitivity Analysis**
        - [Steel Price Sensitivity](#steel-price-sensitivity)
        - [WACC Sensitivity Analysis](#wacc-sensitivity)
        - [Interest Rate Parity Adjustment](#irp-adjustment)
        - [Detailed Projections](#detailed-projections)
        """, unsafe_allow_html=True)

    st.sidebar.markdown("---")

    # Initialize session state for reset triggers and scenario tracking
    if 'reset_section' not in st.session_state:
        st.session_state.reset_section = None
    if 'previous_scenario' not in st.session_state:
        st.session_state.previous_scenario = None

    # Scenario Selection
    st.sidebar.header("Scenario Selection")

    scenario_options = {
        "Severe Downturn - Historical Crisis": ScenarioType.SEVERE_DOWNTURN,
        "Downside - Weak Markets": ScenarioType.DOWNSIDE,
        "Base Case - Mid-Cycle": ScenarioType.BASE_CASE,
        "Above Average - Strong Cycle": ScenarioType.ABOVE_AVERAGE,
        "Wall Street - Analyst Views": ScenarioType.WALL_STREET,
        "Optimistic - Peak Cycle": ScenarioType.OPTIMISTIC,
        "Nippon Investment Case": ScenarioType.NIPPON_COMMITMENTS,
        "Custom": ScenarioType.CUSTOM
    }

    selected_scenario_name = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_options.keys()),
        index=2,  # Default to Base Case
        help="Pre-built scenarios with different assumptions. Select 'Custom' to manually adjust all parameters."
    )
    selected_scenario_type = scenario_options[selected_scenario_name]

    # Check if scenario changed - if so, trigger reset to load new defaults
    if st.session_state.previous_scenario != selected_scenario_name and selected_scenario_type != ScenarioType.CUSTOM:
        st.session_state.reset_section = "all"
        st.session_state.previous_scenario = selected_scenario_name

    # Show scenario description
    scenario_descriptions = {
        "Severe Downturn - Historical Crisis": "Recession scenario (0.68x prices, -20% volumes, 13.5% WACC) - Historical frequency: 24%",
        "Downside - Weak Markets": "Below-average cycle (0.85x prices, 12% WACC) - Historical frequency: 30%",
        "Base Case - Mid-Cycle": "Historical median performance (0.88x prices, 10.9% WACC) - Historical frequency: 30%",
        "Above Average - Strong Cycle": "Good markets like 2017-18 (0.95x prices, 10.9% WACC) - Historical frequency: 10%",
        "Wall Street - Analyst Views": "Barclays/Goldman DCF assumptions (0.92x prices, 12.5% WACC)",
        "Optimistic - Peak Cycle": "2021-22 boom conditions (mgmt projections) - Historical frequency: 5%",
        "Nippon Investment Case": "$14B capital program, all 6 projects, no plant closures through 2035",
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
        st.session_state.n_erp = preset.nippon_equity_risk_premium * 100
        st.session_state.n_cs = preset.nippon_credit_spread * 100
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
        help=f"Applied to ${hrc_us}/ton benchmark. Multiplies your custom benchmark price."
    )

    eu_factor = st.sidebar.slider(
        "EU HRC Price Factor",
        0.5, 1.5, st.session_state.get('eu_factor', preset.price_scenario.hrc_eu_factor), 0.05,
        format="%.2fx",
        key="eu_factor",
        help=f"Applied to ${hrc_eu}/ton benchmark for European operations"
    )

    octg_factor = st.sidebar.slider(
        "OCTG Price Factor",
        0.5, 1.5, st.session_state.get('octg_factor', preset.price_scenario.octg_factor), 0.05,
        format="%.2fx",
        key="octg_factor",
        help=f"Applied to ${octg}/ton benchmark for Tubular segment"
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
        fr_vol_factor = st.slider("Flat-Rolled", 0.5, 1.2, st.session_state.get('fr_vf', preset.volume_scenario.flat_rolled_volume_factor), 0.05, key="fr_vf",
                                   help="Integrated steel mills (Gary, Mon Valley). Facing structural decline without investment.")
        mm_vol_factor = st.slider("Mini Mill", 0.5, 1.3, st.session_state.get('mm_vf', preset.volume_scenario.mini_mill_volume_factor), 0.05, key="mm_vf",
                                   help="Electric Arc Furnace operations (Big River Steel). Highest growth segment.")
        usse_vol_factor = st.slider("USSE", 0.5, 1.2, st.session_state.get('usse_vf', preset.volume_scenario.usse_volume_factor), 0.05, key="usse_vf",
                                     help="U.S. Steel Europe (Slovakia). Exposed to EU market conditions.")
        tub_vol_factor = st.slider("Tubular", 0.5, 1.3, st.session_state.get('tub_vf', preset.volume_scenario.tubular_volume_factor), 0.05, key="tub_vf",
                                    help="Oil Country Tubular Goods (OCTG). Tied to energy sector drilling activity.")

    with st.sidebar.expander("Volume Growth Adjustments", expanded=False):
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

    # Handle IRP reset
    if st.session_state.reset_section == "irp":
        st.session_state.us_10yr = preset.us_10yr * 100
        st.session_state.japan_10yr = preset.japan_10yr * 100
        st.session_state.n_erp = preset.nippon_equity_risk_premium * 100
        st.session_state.n_cs = preset.nippon_credit_spread * 100
        st.session_state.n_dr = preset.nippon_debt_ratio * 100
        st.session_state.n_tr = preset.nippon_tax_rate * 100
        st.session_state.reset_section = None

    us_10yr = st.sidebar.slider("US 10-Year Treasury", 2.0, 6.0, st.session_state.get('us_10yr', preset.us_10yr * 100), 0.25, format="%.2f%%",
                                 key="us_10yr",
                                 help="Current US government bond yield. Used to calculate interest rate differential with Japan.") / 100
    japan_10yr = st.sidebar.slider("Japan 10-Year JGB", 0.0, 2.0, st.session_state.get('japan_10yr', preset.japan_10yr * 100), 0.25, format="%.2f%%",
                                    key="japan_10yr",
                                    help="Japanese Government Bond yield. Nippon's cost of capital rises with this rate.") / 100

    with st.sidebar.expander("Nippon WACC Components", expanded=False):
        nippon_erp = st.slider("Equity Risk Premium", 3.0, 6.0, st.session_state.get('n_erp', preset.nippon_equity_risk_premium * 100), 0.25, format="%.2f%%", key="n_erp",
                                help="Premium over JGB rate for equity. Cost of Equity = JGB + This Premium.") / 100
        nippon_cs = st.slider("Credit Spread", 0.25, 2.0, st.session_state.get('n_cs', preset.nippon_credit_spread * 100), 0.25, format="%.2f%%", key="n_cs",
                                help="Spread over JGB rate for debt. Cost of Debt = JGB + This Spread.") / 100
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
        nippon_equity_risk_premium=nippon_erp,
        nippon_credit_spread=nippon_cs,
        nippon_debt_ratio=nippon_debt_ratio,
        nippon_tax_rate=nippon_tax_rate,
        include_projects=include_projects
    )

    # Build custom benchmarks dictionary
    custom_benchmarks = {
        'hrc_us': hrc_us,
        'crc_us': crc_us,
        'coated_us': coated_us,
        'hrc_eu': hrc_eu,
        'octg': octg
    }

    return custom_scenario, selected_scenario_name, execution_factor, custom_benchmarks


# =============================================================================
# MAIN CONTENT
# =============================================================================

def main():
    # Title
    st.title("USS / Nippon Steel Merger Analysis")
    st.markdown("**Price x Volume DCF Model with Scenario Analysis**")

    # Get assumptions from sidebar
    scenario, scenario_name, execution_factor, custom_benchmarks = render_sidebar()

    # Run the model with execution factor and custom benchmarks
    model = PriceVolumeModel(scenario, execution_factor=execution_factor, custom_benchmarks=custom_benchmarks)
    analysis = model.run_full_analysis()

    consolidated = analysis['consolidated']
    segment_dfs = analysis['segment_dfs']
    jpy_wacc = analysis['jpy_wacc']
    usd_wacc = analysis['usd_wacc']
    val_uss = analysis['val_uss']
    val_nippon = analysis['val_nippon']
    financing_impact = analysis.get('financing_impact', {})

    # =========================================================================
    # EXECUTIVE DECISION SUMMARY
    # =========================================================================

    st.markdown("---")
    st.header("Executive Decision Summary", anchor="executive-decision-summary")

    # Calculate key metrics for decision framework
    uss_standalone = val_uss['share_price']
    nippon_value = val_nippon['share_price']
    pe_max_price = 40.0  # Maximum PE can pay at 20% IRR
    offer_price = 55.0

    # Cleveland-Cliffs offer details (per Schedule 14A and Cleveland-Cliffs_Final_Offer_Analysis.md)
    # Nominal offer: $54/share ($27 cash + 1.444 Cliffs shares worth $27 at Dec 15, 2023 price)
    # Risk-adjusted value: $21-31/share due to:
    #   - Stock volatility risk over 18+ month antitrust review: -$5-10/share
    #   - Required $7B+ divestitures impact on stock value: -$3-8/share
    #   - Probability-weighted antitrust failure: -$15-20/share
    cliffs_nominal = 54.0  # Nominal offer price
    cliffs_risk_adjusted = 26.0  # Midpoint of $21-31 risk-adjusted range

    # Calculate implied EV/EBITDA for USS Standalone
    ebitda_2024 = consolidated.loc[consolidated['Year'] == 2024, 'Total_EBITDA'].values[0]
    implied_ev_ebitda = val_uss['ev_blended'] / ebitda_2024 if ebitda_2024 > 0 else 0
    wacc_advantage = (scenario.uss_wacc - usd_wacc) * 100

    # Determine deal verdict for each stakeholder (dynamically based on model outputs)
    offer_vs_standalone = offer_price - uss_standalone
    offer_vs_nippon_value = nippon_value - offer_price
    uss_shareholder_verdict = "YES" if offer_vs_standalone > 0 else "CONDITIONAL"
    uss_board_verdict = "YES" if offer_vs_standalone >= -5 and offer_price > pe_max_price else "CONDITIONAL"  # Allow small buffer
    nippon_verdict = "YES" if offer_vs_nippon_value > 0 else "NO"

    # Deal Verdict Section with color coding
    st.markdown("### Deal Verdict")

    verdict_col1, verdict_col2, verdict_col3 = st.columns(3)

    with verdict_col1:
        if uss_shareholder_verdict == "YES":
            premium_text = f"+{offer_vs_standalone:.2f}"
            st.success(f"""
            **USS Shareholders: VOTE YES**

            The \\$55 offer is **{premium_text}/share above** standalone value.

            *Rationale: No alternative bidder can match this price. PE caps at ~\\$40, Cleveland-Cliffs nominal \\$54 but risk-adjusted ~\\$26 due to antitrust/execution risk. The 40% premium to pre-announcement price represents fair value.*
            """)
        else:
            diff_text = f"{offer_vs_standalone:.2f}"
            st.warning(f"""
            **USS Shareholders: CONDITIONAL**

            The \\$55 offer is **{diff_text}/share vs** standalone value under current assumptions.

            *Consider: Standalone value assumes successful execution of capital program and favorable steel prices.*
            """)

    with verdict_col2:
        if uss_board_verdict == "YES":
            st.success("""
            **USS Board: RECOMMEND APPROVAL**

            Fiduciary duty satisfied:
            - Market canvass conducted
            - Fairness opinions obtained
            - Premium to all alternatives

            *Rationale: No superior alternative exists. Rejecting 55 exposes shareholders to execution risk and steel price volatility without upside.*
            """)
        else:
            st.warning("""
            **USS Board: REVIEW CAREFULLY**

            Consider negotiating for higher price given current valuation assumptions.
            """)

    with verdict_col3:
        if nippon_verdict == "YES":
            discount_text = f"{offer_vs_nippon_value:.2f}"
            upside_pct = offer_vs_nippon_value/offer_price*100
            st.success(f"""
            **Nippon Steel: PROCEED**

            Acquiring at **{discount_text}/share discount** to intrinsic value.

            *Rationale: WACC advantage ({wacc_advantage:.1f}%) creates {upside_pct:.0f}% upside. Strategic value from #3 global position and US market access.*
            """)
        else:
            premium_text = f"{abs(offer_vs_nippon_value):.2f}"
            st.error(f"""
            **Nippon Steel: VALUE AT RISK**

            Paying **{premium_text}/share premium** to intrinsic value.

            *Caution: Deal destroys value unless synergies materialize or steel prices exceed assumptions.*
            """)

    # Key Numbers Comparison
    st.markdown("### Key Numbers at a Glance")

    num_col1, num_col2, num_col3, num_col4, num_col5, num_col6, num_col7 = st.columns(7)

    with num_col1:
        st.metric(
            "Nippon Offer",
            "$55.00",
            "40% premium to pre-deal"
        )
    with num_col2:
        st.metric(
            "USS Standalone",
            f"${uss_standalone:.2f}",
            f"@ {scenario.uss_wacc*100:.1f}% WACC"
        )
    with num_col3:
        # vs $55 Offer for USS Standalone
        vs_offer_delta = offer_price - uss_standalone
        st.metric(
            "vs $55 Offer",
            f"${vs_offer_delta:+.2f}",
            "Premium" if vs_offer_delta > 0 else "Discount",
            delta_color="normal" if vs_offer_delta > 0 else "inverse"
        )
    with num_col4:
        st.metric(
            "Implied EV/EBITDA",
            f"{implied_ev_ebitda:.1f}x",
            f"Exit: {scenario.exit_multiple:.1f}x"
        )
    with num_col5:
        st.metric(
            "PE Maximum",
            f"${pe_max_price:.2f}",
            f"-${offer_price - pe_max_price:.0f} gap to offer",
            delta_color="inverse"
        )
    with num_col6:
        st.metric(
            "Cliffs (Risk-Adj)",
            f"${cliffs_risk_adjusted:.2f}",
            f"Nominal: ${cliffs_nominal:.0f}",
            delta_color="inverse"
        )
    with num_col7:
        upside_text = f"+{nippon_value - offer_price:.2f}" if nippon_value > offer_price else f"{nippon_value - offer_price:.2f}"
        st.metric(
            "Value to Nippon",
            f"${nippon_value:.2f}",
            f"{upside_text} vs offer",
            delta_color="normal" if nippon_value > offer_price else "inverse"
        )

    # One-line bottom line
    offer_diff = abs(offer_price - uss_standalone)
    nippon_capture = max(0, nippon_value - offer_price)
    exceeds_or_below = "exceeds" if offer_price > uss_standalone else "falls below"
    st.info(f"""
    **Bottom Line:** At current assumptions ({scenario.price_scenario.hrc_us_factor:.0%} steel prices, {scenario.uss_wacc*100:.1f}% WACC),
    the \\$55 offer {exceeds_or_below} USS standalone value by \\${offer_diff:.2f}/share.
    Nippon captures \\${nippon_capture:.2f}/share of value creation from their lower cost of capital.
    **No alternative buyer can match this offer.**
    """)

    # =========================================================================
    # RISK-ADJUSTED DECISION MATRIX
    # =========================================================================

    st.markdown("---")
    st.header("Risk-Adjusted Decision Matrix", anchor="risk-adjusted-decision-matrix")

    st.markdown("""
    Key risks facing USS shareholders with and without the Nippon deal:
    """)

    # Risk matrix table - professional formatting
    standalone_val = f"\\${uss_standalone:.0f}"
    st.markdown(f"""
    | Risk Factor | Probability | Impact on Standalone ({standalone_val}) | Impact with Deal | Deal Protection |
    |-------------|-------------|---------------------------|------------------|-----------------|
    | **Steel Price Collapse** (HRC below \\$600/ton) | 25% (historical) | -\\$15 to -\\$25/share | Locked in at \\$55 | **Full** - Cash offer insulates from price risk |
    | **Execution Risk** on \\$14B CapEx | 30-40% | -\\$10 to -\\$20/share | Nippon absorbs risk | **Full** - Nippon's balance sheet funds projects |
    | **Chinese Overcapacity** (108% utilization) | Ongoing | -\\$5 to -\\$10/share | Combined entity stronger | **Partial** - Scale advantages, tariff protection |
    | **Integrated Asset Obsolescence** | High | -\\$20 to -\\$30/share | \\$14B reinvestment | **Full** - NSA mandates modernization |
    | **Financing Distress** | 15-20% | Potential bankruptcy | Eliminated | **Full** - All-equity deal, no leverage |
    """)

    # Expected value calculation with risk adjustment
    st.markdown("### Risk-Adjusted Expected Value")

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    with risk_col1:
        # Calculate probability-weighted downside
        prob_collapse = 0.25
        downside_impact = -20  # Average downside
        risk_adjusted_standalone_raw = uss_standalone + (prob_collapse * downside_impact)
        # Floor at zero - equity value cannot be negative
        risk_adjusted_standalone = max(0, risk_adjusted_standalone_raw)
        risk_adj_delta = uss_standalone - risk_adjusted_standalone
        st.metric(
            "Risk-Adjusted Standalone",
            f"${risk_adjusted_standalone:.2f}",
            f"-${risk_adj_delta:.2f} from base" if risk_adj_delta > 0 else "At equity floor",
            delta_color="inverse"
        )

    with risk_col2:
        st.metric(
            "Nippon Offer (Certain)",
            f"${offer_price:.2f}",
            "Cash, no execution risk"
        )

    with risk_col3:
        certainty_premium = offer_price - risk_adjusted_standalone
        # Handle edge case where risk_adjusted_standalone could be zero or negative
        if risk_adjusted_standalone > 0.01:
            certainty_pct = f"+{certainty_premium/risk_adjusted_standalone*100:.0f}% vs risk-adjusted"
        else:
            certainty_pct = "Offer provides full protection"
        st.metric(
            "Certainty Premium",
            f"${certainty_premium:.2f}/share",
            certainty_pct,
            delta_color="normal"
        )

    st.info("""
    **Key Insight:** When adjusted for realistic downside scenarios (25% probability of steel price collapse, 30% execution risk),
    the risk-adjusted standalone value is significantly lower than the headline DCF. The \\$55 cash offer eliminates this uncertainty.
    """)

    # =========================================================================
    # BOARD FIDUCIARY CHECKLIST
    # =========================================================================

    st.markdown("---")
    st.header("Board Fiduciary Checklist (Revlon Duties)", anchor="board-fiduciary-checklist")

    st.markdown("""
    When a company is being sold, the board has a duty to maximize shareholder value. This checklist confirms the USS Board satisfied its fiduciary obligations:
    """)

    check_col1, check_col2 = st.columns(2)

    # Dynamic status based on offer vs standalone
    premium_status = "SATISFIED" if offer_vs_standalone > 0 else "REVIEW"
    premium_color = "Complete" if offer_vs_standalone > 0 else "Below DCF"

    with check_col1:
        # Pre-compute values to avoid f-string parsing issues with $ signs
        standalone_str = f"{uss_standalone:.2f}"
        offer_diff_str = f"{offer_vs_standalone:+.2f}" if offer_vs_standalone >= 0 else f"{offer_vs_standalone:.2f}"

        st.markdown(f"""
        | Requirement | Status | Evidence |
        |-------------|--------|----------|
        | **Market Canvass** | Complete | Multiple bidders contacted; Cleveland-Cliffs, PE firms considered |
        | **Fairness Opinions** | Obtained | Barclays (\\$39-48) and Goldman Sachs (\\$42-52) DCF ranges |
        | **Premium to Market** | 40% Premium | \\$55 vs \\$39.33 pre-announcement (Dec 2023) |
        | **Premium to DCF** | {premium_color} | \\$55 vs \\${standalone_str} standalone ({offer_diff_str}) |
        | **Superior Alternatives** | None Exist | Cliffs bid \\$35, PE max \\$40, no other strategic interest |
        | **Deal Certainty** | High | All-cash, committed financing, regulatory path cleared |
        """)

    with check_col2:
        st.markdown("""
        | Risk Factor | Status | Mitigation |
        |-------------|--------|------------|
        | **Antitrust Risk** | Cleared | No horizontal overlap; Nippon minimal US presence |
        | **CFIUS/National Security** | Approved | Golden Share arrangement; NSA signed |
        | **Financing Risk** | None | All-equity deal; Nippon investment grade |
        | **MAE Risk** | Standard | Customary carve-outs for market conditions |
        | **Shareholder Approval** | 98% | Overwhelming shareholder support |
        """)

    # Conclusion box - dynamically updates based on scenario
    offer_diff_fid = f"+\\${offer_vs_standalone:.2f}" if offer_vs_standalone > 0 else f"\\${offer_vs_standalone:.2f}"
    if offer_vs_standalone > 0 and offer_price > pe_max_price:
        st.success(f"""
        **FIDUCIARY DUTY SATISFIED:** The USS Board has fulfilled its Revlon duties. The \\$55 offer is {offer_diff_fid}/share
        above standalone value, exceeds all alternative proposals, and has been validated by independent fairness opinions.
        """)
    elif offer_vs_standalone > -5 and offer_price > pe_max_price:
        within_val = f"\\${abs(offer_vs_standalone):.2f}"
        st.info(f"""
        **FIDUCIARY DUTY SUPPORTABLE:** The \\$55 offer is within {within_val}/share of standalone value.
        Given execution risk and deal certainty, the board can reasonably support the transaction.
        """)
    else:
        standalone_fid = f"\\${uss_standalone:.2f}"
        st.warning(f"""
        **REVIEW REQUIRED:** Under current assumptions ({standalone_fid} standalone), the board should carefully
        document the rationale for recommending the transaction. Consider execution risk and deal certainty factors.
        """)

    # =========================================================================
    # "WITHOUT THE DEAL" STRATEGIC ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.header("Without the Deal: USS Strategic Predicament", anchor="without-the-deal")

    st.markdown("""
    **The case for why USS needs this deal** - Strategic challenges USS faces as a standalone company:
    """)

    predicament_col1, predicament_col2 = st.columns(2)

    with predicament_col1:
        st.markdown("""
        ### Competitive Position Deterioration

        | Metric | USS Standalone | With Nippon |
        |--------|----------------|-------------|
        | Global Ranking | **#27** | **#3** |
        | Annual Capacity | 20M tons | 86M tons |
        | R&D Budget | ~\\$50M | \\$500M+ |
        | Balance Sheet | BBB- (weak) | A-rated |
        | Technology Access | Limited | 2,000+ patents |

        ### Flat-Rolled Segment Decline
        - Blast furnaces average **40+ years old**
        - Gary Works BF #14 needs \\$3.1B reline or closure
        - Mon Valley HSM at end of useful life
        - Without investment: **-3% to -5% volume/year**
        """)

    with predicament_col2:
        st.markdown("""
        ### Capital Requirements vs. Capacity

        | Capital Need | Amount | USS Can Fund? |
        |--------------|--------|---------------|
        | BR2 (committed) | \\$3.0B | Yes (debt-funded) |
        | Gary Works BF | \\$3.1B | No - requires equity |
        | Mon Valley HSM | \\$1.0B | No - requires equity |
        | Mining Investment | \\$0.8B | Marginal |
        | Greenfield Mill | \\$1.0B | No - not feasible |
        | **Total NSA Program** | **\\$14B** | **Cannot fund alone** |

        ### Financing Gap Analysis
        - Annual FCF: ~\\$1.2-1.5B
        - Maintenance CapEx: ~\\$800M
        - Available for growth: **\\$400-700M/year**
        - NSA requires: **\\$1.4B/year for 10 years**
        - **Gap: ~\\$700M-1B/year** (needs dilutive equity)
        """)

    # Visualization of standalone trajectory
    st.markdown("### Flat-Rolled Segment Trajectory Without Investment")

    # Create trajectory data
    years = list(range(2024, 2034))
    base_volume = 8500  # Starting volume in 000 tons
    decline_rate_no_invest = -0.04  # 4% annual decline without investment
    decline_rate_with_nippon = 0.01  # 1% growth with Nippon investment

    trajectory_data = []
    vol_no_invest = base_volume
    vol_with_nippon = base_volume
    for year in years:
        trajectory_data.append({
            'Year': year,
            'Scenario': 'Without Nippon (No Investment)',
            'Volume': vol_no_invest
        })
        trajectory_data.append({
            'Year': year,
            'Scenario': 'With Nippon ($14B Investment)',
            'Volume': vol_with_nippon
        })
        vol_no_invest *= (1 + decline_rate_no_invest)
        vol_with_nippon *= (1 + decline_rate_with_nippon)

    trajectory_df = pd.DataFrame(trajectory_data)

    fig_trajectory = px.line(
        trajectory_df,
        x='Year',
        y='Volume',
        color='Scenario',
        title='Flat-Rolled Segment Volume Projection (000 tons)',
        markers=True,
        color_discrete_map={
            'Without Nippon (No Investment)': '#ff6b6b',
            'With Nippon ($14B Investment)': '#4ecdc4'
        }
    )
    fig_trajectory.update_layout(yaxis_title='Volume (000 tons)', height=350)
    st.plotly_chart(fig_trajectory, use_container_width=True)

    st.warning("""
    **Strategic Reality:** Without Nippon's capital, USS faces a choice between:
    1. **Slow decline** - Underfund aging assets, lose market share to mini-mills and imports
    2. **Dilutive financing** - Issue equity at depressed valuations, destroying shareholder value
    3. **Asset sales** - Divest crown jewels to fund core, reducing future earnings power

    The Nippon deal provides **\\$14B of permanent capital** without these trade-offs.
    """)

    # =========================================================================
    # GOLDEN SHARE / NSA CONSTRAINTS SUMMARY
    # =========================================================================

    st.markdown("---")
    st.header("Golden Share & NSA Commitments", anchor="golden-share-nsa")

    st.markdown("""
    The National Security Agreement (NSA) includes unprecedented government oversight and binding commitments from Nippon Steel:
    """)

    nsa_col1, nsa_col2 = st.columns(2)

    with nsa_col1:
        st.markdown("""
        ### Capital Investment Commitments

        | Commitment | Amount/Timeline |
        |------------|-----------------|
        | **Total Investment** | \\$14B over 10 years |
        | By 2028 (binding) | \\$11B |
        | Gary Works BF | \\$3.1B (committed) |
        | Mon Valley HSM | \\$1.0B (committed) |
        | Big River Steel 2 | \\$3.0B (under construction) |
        | Mining Operations | \\$0.8B |
        | Greenfield Mini Mill | \\$1.0B |
        | BLA Facility Investment | \\$1.4B |

        ### Employment Guarantees

        | Commitment | Details |
        |------------|---------|
        | No layoffs | Through September 2026+ |
        | No plant closures | Through 2035 |
        | Jobs protected | 27,000-28,000 |
        | USW agreements | All honored |
        """)

    with nsa_col2:
        st.markdown("""
        ### Golden Share Veto Rights (US Government)

        The US Government holds a "Golden Share" with veto power over:

        | Decision | Requires Government Consent |
        |----------|----------------------------|
        | Reduce capital investments | Yes |
        | Change company name | Yes |
        | Move headquarters from Pittsburgh | Yes |
        | Transfer production/jobs abroad | Yes |
        | Close or idle US facilities | Yes |
        | Acquire competing US businesses | Yes |
        | Certain trade/labor/sourcing decisions | Yes |

        ### Governance Requirements

        | Requirement | Details |
        |-------------|---------|
        | CEO | Must be US citizen |
        | Board majority | Must be US citizens |
        | Trade Committee | US citizens only |
        | Security Committee | 3 independent directors |
        | Technology transfers | Government oversight |
        """)

    st.success("""
    **Unprecedented Protections:** This NSA represents the most extensive government oversight ever applied to a foreign acquisition.
    USS workers, communities, and national security interests are protected by legally binding commitments with government veto rights.
    """)

    # =========================================================================
    # ALTERNATIVE BUYER COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("Alternative Buyer Comparison", anchor="alternative-buyer-comparison")

    st.markdown("""
    **Why no alternative can match the \\$55 offer:**
    """)

    # Full comparison table - dynamic based on current standalone value
    nippon_premium = offer_price - uss_standalone
    cliffs_risk_adj_discount = uss_standalone - cliffs_risk_adjusted
    pe_discount = uss_standalone - pe_max_price

    # Pre-compute formatted strings
    standalone_int = f"{uss_standalone:.0f}"
    nippon_prem_str = f"+{nippon_premium:.2f}" if nippon_premium > 0 else f"{nippon_premium:.2f}"
    cliffs_risk_str = f"-{cliffs_risk_adj_discount:.2f}" if cliffs_risk_adj_discount > 0 else f"+{abs(cliffs_risk_adj_discount):.2f}"
    pe_disc_str = f"-{pe_discount:.2f}" if pe_discount > 0 else f"+{abs(pe_discount):.2f}"

    st.markdown(f"""
    | Factor | Nippon Steel (\\$55) | Cleveland-Cliffs (\\$54 nominal) | PE/LBO (~\\$40 max) | Standalone |
    |--------|-------------------|-------------------------------|-------------------|------------|
    | **Nominal Offer** | \\$55.00 (cash) | \\$54.00 (\\$27 cash + \\$27 stock) | \\$40.00 max | N/A |
    | **Risk-Adjusted Value** | \\$55.00 | ~\\$26 (antitrust/exec risk) | ~\\$35-38 | N/A |
    | **vs Standalone (\\${standalone_int})** | {nippon_prem_str}/sh | {cliffs_risk_str}/sh | {pe_disc_str}/sh | 0 |
    | **Deal Structure** | All-cash, all-equity | 50% cash / 50% stock | Leveraged (5x debt) | N/A |
    | **Financing Risk** | None (A-rated) | High (stock volatility) | High (covenant risk) | Ongoing |
    | **Can Fund \\$14B CapEx?** | Yes | No (leverage constrained) | No (debt limits) | No |
    | **Antitrust Issues** | None | Severe (100% BF, 65-90% auto) | None | N/A |
    | **Required Divestitures** | Minimal | \\$7B+ revenue | None | N/A |
    | **Technology Transfer** | 2,000+ patents | None | None | Limited R&D |
    | **Job Security** | 27K jobs guaranteed | Synergy cuts expected | Cost cuts for IRR | Uncertain |
    | **Closing Timeline** | 6-9 months (actual: 18) | 18+ months (antitrust litigation) | 3-6 months | N/A |
    """)

    # Individual buyer analysis
    buyer_col1, buyer_col2, buyer_col3 = st.columns(3)

    cliffs_nominal_gap = offer_price - cliffs_nominal
    cliffs_risk_gap = offer_price - cliffs_risk_adjusted
    with buyer_col1:
        st.error(f"""
        ### Cleveland-Cliffs - REJECTED

        **Nominal Bid:** \\$54/share (Dec 2023)
        - \\$27 cash + 1.444 Cliffs shares

        **Risk-Adjusted Value:** ~\\$26/share
        - Stock volatility (18+ mo review): -\\$5 to -\\$10
        - Divestiture impact: -\\$3 to -\\$8
        - Antitrust failure risk: -\\$15 to -\\$20

        **Why It Failed:**
        - Would create 100% US blast furnace monopoly
        - 65-90% of US automotive steel
        - DOJ would require \\$7B+ divestitures
        - Weak antitrust commitments (no "hell or high water")
        - Alliance for Automotive Innovation opposed

        **Risk-Adj Gap to Nippon:** \\${cliffs_risk_gap:.0f}/share
        """)

    with buyer_col2:
        st.error("""
        ### Private Equity (LBO) - NOT VIABLE

        **Maximum Price:** ~\\$40/share

        **Why PE Can't Compete:**
        - Requires 20% IRR target
        - 5.0x leverage = \\$10B debt
        - \\$920M annual interest burden
        - Cannot fund \\$14B CapEx
        - Covenant restrictions limit flexibility
        - Bankruptcy risk in steel downturn
        - Forced exit in 5-7 years

        **Returns at 55:** -7.5% to +7.3% IRR (vs 20% target) - Deal doesn't work
        """)

    nippon_value_str = f"+{offer_vs_nippon_value:.2f}" if offer_vs_nippon_value > 0 else f"{offer_vs_nippon_value:.2f}"
    with buyer_col3:
        st.success(f"""
        ### Nippon Steel - RECOMMENDED

        **Offer:** \\$55/share (cash)

        **Why Nippon Wins:**
        - 40% premium to pre-deal price
        - All-equity, no acquisition debt
        - Investment grade balance sheet
        - Can fund full \\$14B CapEx
        - No antitrust concerns
        - Permanent capital (no exit pressure)
        - Strategic synergies + technology
        - WACC advantage creates headroom

        **Value Creation:** {nippon_value_str}/share vs offer price
        """)

    # =========================================================================
    # SENSITIVITY THRESHOLDS ("WHAT BREAKS THE DEAL")
    # =========================================================================

    st.markdown("---")
    st.header("Sensitivity Thresholds: What Breaks the Deal?", anchor="sensitivity-thresholds")

    st.markdown("""
    Analysis of threshold values where the deal economics become unattractive for each party:
    """)

    # Calculate thresholds dynamically based on current scenario
    threshold_col1, threshold_col2, threshold_col3 = st.columns(3)

    with threshold_col1:
        st.markdown("### Steel Price Threshold")

        # Calculate approximate threshold
        # Linear approximation: a 10% price change = ~$15-20 value change
        price_sensitivity = 18  # $/share per 10% price change
        current_price_factor = scenario.price_scenario.hrc_us_factor
        price_threshold = current_price_factor - ((nippon_value - 55) / price_sensitivity * 0.10)

        st.metric(
            "Nippon Breakeven Price Factor",
            f"{price_threshold:.0%}",
            f"Currently {current_price_factor:.0%}",
            delta_color="normal" if current_price_factor > price_threshold else "inverse"
        )

        implied_hrc = custom_benchmarks['hrc_us'] * price_threshold
        implied_hrc_str = f"{implied_hrc:.0f}"
        price_buffer = (current_price_factor - price_threshold) * 100
        price_margin = "Adequate" if current_price_factor > price_threshold + 0.10 else "Limited"
        st.markdown(f"""
        **Interpretation:**
        - If HRC prices fall to **{price_threshold:.0%}** of benchmark (~{implied_hrc_str}/ton),
          Nippon's intrinsic value falls to 55
        - Below this level, Nippon is **overpaying**
        - Current buffer: **{price_buffer:.1f}%** of price downside

        *Margin of Safety: {price_margin}*
        """)

    with threshold_col2:
        st.markdown("### WACC Threshold")

        # Find WACC where value = $55
        wacc_sensitivity = 8  # $/share per 1% WACC change
        wacc_threshold = usd_wacc + ((nippon_value - 55) / wacc_sensitivity / 100)

        st.metric(
            "Nippon Breakeven WACC",
            f"{wacc_threshold*100:.1f}%",
            f"Currently {usd_wacc*100:.1f}%",
            delta_color="normal" if usd_wacc < wacc_threshold else "inverse"
        )

        wacc_buffer = (wacc_threshold - usd_wacc) * 100
        wacc_margin = "Adequate" if wacc_threshold > usd_wacc + 0.02 else "Limited"

        # Handle the case where buffer is negative (value already below offer)
        if wacc_buffer >= 0:
            rate_change_text = f"Japan rates to rise **{wacc_buffer:.1f}%**"
            buffer_text = f"**{wacc_buffer:.1f}%** WACC increase"
        else:
            rate_change_text = f"Japan rates to fall **{abs(wacc_buffer):.1f}%** (value already below offer)"
            buffer_text = f"**{abs(wacc_buffer):.1f}%** WACC decrease needed"

        st.markdown(f"""
        **Interpretation:**
        - If Nippon's USD WACC rises above **{wacc_threshold*100:.1f}%**,
          intrinsic value falls below \\$55 offer
        - This would require {rate_change_text}
        - Current buffer: {buffer_text}

        *Margin of Safety: {wacc_margin}*
        """)

    with threshold_col3:
        st.markdown("### Execution Threshold")

        # If execution factor < X, value falls below offer
        exec_threshold = max(0, 1.0 - ((nippon_value - 55) / 50))  # 50 = rough max impact

        st.metric(
            "Minimum Execution Factor",
            f"{exec_threshold:.0%}",
            f"Currently {execution_factor:.0%}",
            delta_color="normal" if execution_factor > exec_threshold else "inverse"
        )

        exec_margin = "Adequate" if execution_factor > exec_threshold + 0.20 else "Limited"
        st.markdown(f"""
        **Interpretation:**
        - NSA capital projects must achieve at least **{exec_threshold:.0%}** of
          projected benefits for deal to create value
        - Below this, Nippon is overpaying
        - Current assumption: **{execution_factor:.0%}** execution

        *Margin of Safety: {exec_margin}*
        """)

    # Summary threshold table with traffic light risk indicators
    # These colored circles are universally understood risk indicators
    price_risk = "Low" if current_price_factor > price_threshold + 0.10 else "Medium" if current_price_factor > price_threshold else "High"
    wacc_risk = "Low" if wacc_threshold > usd_wacc + 0.02 else "Medium" if wacc_threshold > usd_wacc else "High"
    exec_risk = "Low" if execution_factor > exec_threshold + 0.20 else "Medium" if execution_factor > exec_threshold else "High"

    st.markdown("### Threshold Summary")
    st.markdown(f"""
    | Parameter | Current Value | Breakeven Threshold | Buffer | Risk Level |
    |-----------|---------------|---------------------|--------|------------|
    | Steel Price Factor | {current_price_factor:.0%} | {price_threshold:.0%} | {(current_price_factor - price_threshold)*100:+.1f}% | {price_risk} |
    | Nippon USD WACC | {usd_wacc*100:.1f}% | {wacc_threshold*100:.1f}% | {(wacc_threshold - usd_wacc)*100:+.1f}% | {wacc_risk} |
    | Execution Factor | {execution_factor:.0%} | {exec_threshold:.0%} | {(execution_factor - exec_threshold)*100:+.1f}% | {exec_risk} |
    """)

    # Dynamic assessment based on risk levels
    high_risk_count = sum([price_risk == "High", wacc_risk == "High", exec_risk == "High"])
    if high_risk_count == 0:
        assessment_text = "Deal has adequate margin of safety under reasonable stress scenarios"
    elif high_risk_count == 1:
        assessment_text = "Deal has limited margin on one parameter - monitor closely"
    else:
        assessment_text = "Deal has elevated risk on multiple parameters - recommend scenario stress testing"

    st.info(f"""
    **What Would Break the Deal:**
    - **For USS Shareholders:** Steel prices would need to rise significantly above base case for 55 to look cheap
    - **For Nippon:** Either severe steel price collapse ({price_threshold:.0%} factor), major WACC increase (>{wacc_threshold*100:.1f}%),
      or execution failure (<{exec_threshold:.0%} benefits) would make the acquisition value-destructive
    - **Current Assessment:** {assessment_text}
    """)

    # =========================================================================
    # VALUATION DETAILS
    # =========================================================================

    st.markdown("---")
    st.header("Valuation Details", anchor="valuation-details")

    st.markdown("""
    **How to read these tables:**
    - **PV of 10Y FCF**: Present value of projected free cash flows from 2024-2033
    - **PV Terminal (Gordon)**: Terminal value using perpetual growth formula: FCF × (1+g) / (WACC-g)
    - **PV Terminal (Exit Multiple)**: Terminal value using comparable company EV/EBITDA multiple
    - **Enterprise Value**: Blended average of Gordon Growth and Exit Multiple methods (50/50 weighting)
    - **Equity Bridge**: Adjustments for debt, cash, pension, and other items to convert EV to equity value
    - **Equity Value per Share**: Equity value divided by 225M shares outstanding
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
        | **Equity Value/Share** | **${val_uss['share_price']:.2f}** |
        """)

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
        | **Equity Value/Share** | **${val_nippon['share_price']:.2f}** |
        """)

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

    # EV/EBITDA Multiple Analysis
    st.markdown("### EV/EBITDA Multiple Analysis")
    st.markdown("""
    **Implied vs Exit Multiples:**
    - **Implied Multiple**: Current EV divided by 2024 EBITDA (what you're paying today)
    - **Exit Multiple**: EV/EBITDA assumed for terminal value (future steady-state multiple)
    - Higher implied multiple suggests growth expectations baked into valuation
    """)

    terminal_ebitda = val_uss['terminal_ebitda']
    ebitda_growth = ((terminal_ebitda / ebitda_2024) ** (1/9) - 1) * 100 if ebitda_2024 > 0 else 0

    mult_col1, mult_col2, mult_col3, mult_col4 = st.columns(4)
    with mult_col1:
        st.metric("2024 EBITDA", f"${ebitda_2024:,.0f}M")
    with mult_col2:
        st.metric("2033 EBITDA", f"${terminal_ebitda:,.0f}M")
    with mult_col3:
        st.metric("EBITDA CAGR", f"{ebitda_growth:.1f}%")
    with mult_col4:
        implied_exit_mult = val_uss['ev_blended'] / terminal_ebitda if terminal_ebitda > 0 else 0
        st.metric("Implied 2033x", f"{implied_exit_mult:.1f}x")

    # Comparison table
    # Calculate multiples with zero-check
    uss_implied_mult = f"{val_uss['ev_blended']/ebitda_2024:.1f}x" if ebitda_2024 > 0 else "N/A"
    nippon_implied_mult = f"{val_nippon['ev_blended']/ebitda_2024:.1f}x" if ebitda_2024 > 0 else "N/A"

    st.markdown(f"""
    | Perspective | Enterprise Value | 2024 EBITDA | **Implied 2024x** | Terminal EBITDA | Exit Multiple |
    |-------------|------------------|-------------|-------------------|-----------------|---------------|
    | USS - No Sale | ${val_uss['ev_blended']:,.0f}M | ${ebitda_2024:,.0f}M | **{uss_implied_mult}** | ${terminal_ebitda:,.0f}M | {scenario.exit_multiple:.1f}x |
    | Value to Nippon | ${val_nippon['ev_blended']:,.0f}M | ${ebitda_2024:,.0f}M | **{nippon_implied_mult}** | ${terminal_ebitda:,.0f}M | {scenario.exit_multiple:.1f}x |

    *Steel sector typically trades at 4-6x EV/EBITDA. Higher implied multiples reflect growth expectations or lower discount rates.*
    """)

    # =========================================================================
    # FINANCING IMPACT (only show when there are incremental projects)
    # =========================================================================

    if financing_impact.get('financing_gap', 0) > 0:
        st.markdown("---")
        st.header("USS Standalone Financing Impact", anchor="uss-standalone-financing")

        st.warning("""
        **Why USS - No Sale value is lower:** USS cannot fund large capital projects from operating cash flow alone.
        To execute the selected projects without Nippon, USS would need to issue debt and equity, which:
        - Increases interest expense (reducing FCF)
        - Dilutes existing shareholders
        - Raises cost of capital (higher WACC)

        **Nippon does not face these costs** because they have the balance sheet capacity to fund \\$14B+ in investments.
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
    st.header("Scenario Comparison", anchor="scenario-comparison")

    # Run comparison across all preset scenarios (with execution factor applied to Nippon Commitments)
    comparison_df = compare_scenarios(execution_factor=execution_factor, custom_benchmarks=custom_benchmarks)

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
    fig.update_layout(showlegend=False, yaxis_title=f"Equity Value ($/sh) [{wacc_label}]")
    st.plotly_chart(fig, use_container_width=True)

    # Summary table (below chart)
    st.markdown("""
    **How to read this table:**
    - **USS - No Sale**: Share value if USS remains independent (discounted at USS's ~10.9% WACC)
    - **Value to Nippon**: Share value from Nippon's perspective (discounted at Nippon's ~7.5% IRP-adjusted WACC)
    - **Implied EV/EBITDA**: Enterprise Value divided by 2024 EBITDA (current-year implied multiple)
    - **10Y FCF**: Total free cash flow generated over the 10-year forecast period (2024-2033)
    - The difference between the two valuations reflects the "WACC advantage" Nippon gains from its lower cost of capital
    """)
    display_df = comparison_df[['Scenario', 'USS - No Sale ($/sh)', 'Value to Nippon ($/sh)', 'Implied EV/EBITDA', '10Y FCF ($B)']].copy()
    display_df['USS - No Sale ($/sh)'] = display_df['USS - No Sale ($/sh)'].apply(lambda x: f"${x:.2f}")
    display_df['Value to Nippon ($/sh)'] = display_df['Value to Nippon ($/sh)'].apply(lambda x: f"${x:.2f}")
    display_df['Implied EV/EBITDA'] = display_df['Implied EV/EBITDA'].apply(lambda x: f"{x:.1f}x")
    display_df['10Y FCF ($B)'] = display_df['10Y FCF ($B)'].apply(lambda x: f"${x:.1f}B")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # =========================================================================
    # PROBABILITY-WEIGHTED VALUATION
    # =========================================================================

    st.markdown("---")
    st.header("Probability-Weighted Expected Value", anchor="probability-weighted-value")
    st.markdown("""
    This analysis weights each scenario by its historical frequency (1990-2023) to calculate
    an **expected value** that reflects the full range of potential outcomes.
    """)

    with st.expander("ℹ️ Understanding Probability Weighting", expanded=False):
        st.markdown("""
        **Why weight by probability?**
        - USS has experienced severe downturns 24% of years historically
        - Using only "base case" or "conservative" scenarios ignores downside risk
        - Expected value = weighted average of all scenarios

        **Probability Weights (based on 34-year history):**
        - Severe Downturn: 25% (2009, 2015, 2020-type events)
        - Downside: 30% (below-average but not crisis)
        - Base Case: 30% (mid-cycle, median performance)
        - Above Average: 10% (2017-18 type conditions)
        - Optimistic: 5% (2021-22 peak conditions)

        **Total: 100%**
        """)

    # Calculate probability-weighted valuation
    with st.spinner("Calculating probability-weighted valuation..."):
        try:
            pw_results = calculate_probability_weighted_valuation(
                custom_benchmarks=custom_benchmarks
            )

            # Display results
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Expected USS Value (Standalone)",
                    f"${pw_results['weighted_uss_value_per_share']:.2f}/share",
                    delta=f"{pw_results['uss_premium_to_offer']:+.1f}% vs $55 offer",
                    delta_color="inverse"
                )

            with col2:
                st.metric(
                    "Expected Nippon Value",
                    f"${pw_results['weighted_nippon_value_per_share']:.2f}/share",
                    delta=f"{pw_results['nippon_discount_to_offer']:+.1f}% vs $55 offer"
                )

            with col3:
                st.metric(
                    "Expected 10-Year FCF",
                    f"${pw_results['weighted_ten_year_fcf']/1000:.2f}B"
                )

            # Scenario breakdown table
            st.markdown("### Scenario Breakdown")

            # Build markdown table
            md_rows = []
            md_rows.append("| Scenario | Probability | USS Value/Share | Weighted Contribution | vs $55 Offer |")
            md_rows.append("|----------|-------------|-----------------|----------------------|--------------|")

            scenario_count = 0
            for scenario_type, result in pw_results['scenario_results'].items():
                uss_val = result['uss_value_per_share']
                # Handle zero or near-zero values to avoid division by zero
                if uss_val > 0.01:
                    vs_offer_str = f"{(55.0/uss_val-1)*100:+.1f}%"
                else:
                    vs_offer_str = "N/A (equity wiped)"

                weighted_contrib = uss_val * result['probability']
                prob_pct = result['probability'] * 100
                md_rows.append(f"| {result['name']} | {prob_pct:.0f}% | ${uss_val:.2f} | ${weighted_contrib:.2f} | {vs_offer_str} |")
                scenario_count += 1

            md_table = "\n".join(md_rows)
            st.markdown(md_table)
            st.caption(f"*{scenario_count} scenarios shown*")

        except Exception as e:
            st.error(f"Error calculating probability-weighted valuation: {str(e)}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())

    # =========================================================================
    # CAPITAL PROJECTS ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.header("Capital Projects Analysis", anchor="capital-projects")

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
    # PE LBO vs STRATEGIC BUYER COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("PE LBO vs. Strategic Buyer Comparison", anchor="pe-lbo-comparison")

    st.markdown("""
    **Why This Matters:**
    A private equity LBO provides the key counterfactual - what would a financial buyer pay? This analysis demonstrates
    that PE firms cannot compete at \\$55/share, proving Nippon's strategic offer is superior to any alternative.
    """)

    # Comparison table
    lbo_col1, lbo_col2, lbo_col3 = st.columns(3)

    with lbo_col1:
        st.markdown("### PE Buyer (LBO)")
        st.markdown("""
        **Maximum Price:** ~\\$40/share

        **Structure:**
        - 5.0x Debt/EBITDA leverage
        - 30% equity, 70% debt
        - ~\\$10B total debt
        - \\$920M annual interest

        **Returns (at \\$55):**
        - IRR: -7.5% to 7.3%
        - vs. 20% target: **FAIL** ✗

        **Key Constraints:**
        - Cannot fund \\$14B CapEx
        - Covenant restrictions
        - Bankruptcy risk in downturn
        - 5-7 year forced exit
        """)

    with lbo_col2:
        st.markdown("### USS Standalone")
        st.markdown(f"""
        **Fair Value:** \\${val_uss['share_price']:.2f}/share

        **Structure:**
        - Existing capital structure
        - Moderate leverage (1.9x)
        - \\$5.2B liquidity

        **Constraints:**
        - Cannot fund NSA CapEx alone
        - Would need dilutive financing
        - Limited strategic options
        - Cyclical volatility

        **WACC:** {scenario.uss_wacc*100:.1f}%
        """)

    with lbo_col3:
        st.markdown("### Nippon Steel (Strategic)")
        st.markdown(f"""
        **Offer Price:** \\$55.00/share
        **Intrinsic Value:** \\${val_nippon['share_price']:.2f}/share

        **Structure:**
        - All-equity acquisition
        - Zero acquisition debt
        - Investment grade balance sheet

        **Advantages:**
        - Can fund full \\$14B CapEx
        - No covenant restrictions
        - Zero bankruptcy risk
        - Permanent capital
        - Strategic synergies

        **WACC:** {usd_wacc*100:.2f}% (IRP-adjusted)
        **Value Created:** \\${val_nippon['share_price'] - 55:.2f}/share
        """)

    # Key insight boxes
    st.markdown("### Key Insights")
    insight_col1, insight_col2, insight_col3 = st.columns(3)

    with insight_col1:
        pe_gap = 55 - 40
        st.metric(
            "PE Gap to $55 Offer",
            f"-${pe_gap:.0f}/share",
            f"-{pe_gap/55*100:.0f}% discount needed",
            delta_color="inverse"
        )

    with insight_col2:
        uss_share_price = val_uss['share_price']
        uss_premium = 55 - uss_share_price
        # Handle zero share price to avoid division by zero
        if uss_share_price > 0.01:
            premium_pct = f"+{uss_premium/uss_share_price*100:.0f}%"
        else:
            premium_pct = "N/A (equity wiped)"
        st.metric(
            "Premium vs. USS Standalone",
            f"+${uss_premium:.2f}/share",
            premium_pct,
            delta_color="normal"
        )

    with insight_col3:
        nippon_upside = val_nippon['share_price'] - 55
        st.metric(
            "Nippon Value Creation",
            f"${nippon_upside:.2f}/share",
            f"{nippon_upside/55*100:.0f}% upside captured",
            delta_color="normal"
        )

    st.info("""
    **Conclusion:** The \\$55 offer sits in the "fair zone" between:
    - **Floor**: PE maximum price (~\\$40, cannot compete)
    - **Mid**: USS standalone value (~\\${:.0f}, fair to shareholders)
    - **Ceiling**: Nippon intrinsic value (~\\${:.0f}, strategic value creation)

    No financial buyer can match this offer while Nippon still captures significant value.
    """.format(val_uss['share_price'], val_nippon['share_price']))

    # =========================================================================
    # VALUATION FOOTBALL FIELD
    # =========================================================================

    st.markdown("---")
    st.header("Valuation Football Field", anchor="valuation-football-field")

    st.markdown("""
    **How to read this chart:**
    - Each horizontal bar represents a valuation methodology or scenario
    - Bar length shows the valuation range (low to high) under different assumptions
    - **Green dashed line** = \\$55 Nippon offer price
    - **Red dotted line** = \\$40 PE maximum price (20% IRR threshold)
    - Toggle between USS standalone view and Nippon's acquirer view

    **Key Insight:** The \\$55 offer sits above PE alternatives and USS standalone value, yet below Nippon's full intrinsic value.
    """)

    # Toggle for perspective
    ff_col1, ff_col2 = st.columns([1, 3])
    with ff_col1:
        ff_perspective = st.radio(
            "Perspective",
            options=["Value to Nippon", "USS Standalone"],
            horizontal=True,
            key="ff_perspective",
            help="Value to Nippon uses ~7.5% WACC; USS Standalone uses ~10.9% WACC"
        )

    # Build football field data
    football_field_data = []

    # 1. Scenario-based ranges (use scenario comparison data)
    presets = get_scenario_presets()
    scenario_values = []
    for st_type, preset in presets.items():
        ef = execution_factor if st_type == ScenarioType.NIPPON_COMMITMENTS else 1.0
        temp_model = PriceVolumeModel(preset, execution_factor=ef, custom_benchmarks=custom_benchmarks)
        temp_analysis = temp_model.run_full_analysis()
        if ff_perspective == "Value to Nippon":
            scenario_values.append(temp_analysis['val_nippon']['share_price'])
        else:
            scenario_values.append(temp_analysis['val_uss']['share_price'])

    football_field_data.append({
        'Method': 'DCF Scenarios',
        'Low': min(scenario_values),
        'High': max(scenario_values),
        'Description': 'Low: Conservative (weak prices, 12% WACC) → High: Nippon Commitments ($14B CapEx, full synergies)'
    })

    # 2. Steel Price Sensitivity (85% to 115% of benchmarks - realistic range)
    price_sens_values = []
    for pf in [0.85, 0.95, 1.00, 1.05, 1.15]:
        test_price_scenario = SteelPriceScenario(
            name="Test", description="Test",
            hrc_us_factor=pf, crc_us_factor=pf, coated_us_factor=pf,
            hrc_eu_factor=pf, octg_factor=pf,
            annual_price_growth=scenario.price_scenario.annual_price_growth
        )
        test_scenario = ModelScenario(
            name="Test", scenario_type=ScenarioType.CUSTOM, description="Test",
            price_scenario=test_price_scenario,
            volume_scenario=scenario.volume_scenario,
            uss_wacc=scenario.uss_wacc,
            terminal_growth=scenario.terminal_growth,
            exit_multiple=scenario.exit_multiple,
            us_10yr=scenario.us_10yr,
            japan_10yr=scenario.japan_10yr,
            nippon_equity_risk_premium=scenario.nippon_equity_risk_premium,
            nippon_credit_spread=scenario.nippon_credit_spread,
            nippon_debt_ratio=scenario.nippon_debt_ratio,
            nippon_tax_rate=scenario.nippon_tax_rate,
            include_projects=scenario.include_projects
        )
        temp_model = PriceVolumeModel(test_scenario, custom_benchmarks=custom_benchmarks)
        temp_analysis = temp_model.run_full_analysis()
        if ff_perspective == "Value to Nippon":
            price_sens_values.append(temp_analysis['val_nippon']['share_price'])
        else:
            price_sens_values.append(temp_analysis['val_uss']['share_price'])

    football_field_data.append({
        'Method': 'Steel Price Sensitivity',
        'Low': min(price_sens_values),
        'High': max(price_sens_values),
        'Description': 'HRC $580-780/ton range (±15% from $680 benchmark). Steel prices are #1 value driver'
    })

    # 3. WACC Sensitivity
    wacc_sens_values = []
    for w in [0.08, 0.10, 0.12, 0.14]:
        test_val = model.calculate_dcf(consolidated, w)
        wacc_sens_values.append(test_val['share_price'])

    football_field_data.append({
        'Method': 'WACC Sensitivity',
        'Low': min(wacc_sens_values),
        'High': max(wacc_sens_values),
        'Description': '8% (investment grade) to 14% (distressed). USS trades ~10.9%, Nippon IRP-adjusted ~7.5%'
    })

    # 4. Exit Multiple Sensitivity
    exit_sens_values = []
    for em in [3.5, 4.5, 5.5, 6.5]:
        # Manually calculate with different exit multiple
        temp_scenario = ModelScenario(
            name="Test", scenario_type=ScenarioType.CUSTOM, description="Test",
            price_scenario=scenario.price_scenario,
            volume_scenario=scenario.volume_scenario,
            uss_wacc=scenario.uss_wacc,
            terminal_growth=scenario.terminal_growth,
            exit_multiple=em,
            us_10yr=scenario.us_10yr,
            japan_10yr=scenario.japan_10yr,
            nippon_equity_risk_premium=scenario.nippon_equity_risk_premium,
            nippon_credit_spread=scenario.nippon_credit_spread,
            nippon_debt_ratio=scenario.nippon_debt_ratio,
            nippon_tax_rate=scenario.nippon_tax_rate,
            include_projects=scenario.include_projects
        )
        temp_model = PriceVolumeModel(temp_scenario, custom_benchmarks=custom_benchmarks)
        temp_analysis = temp_model.run_full_analysis()
        if ff_perspective == "Value to Nippon":
            exit_sens_values.append(temp_analysis['val_nippon']['share_price'])
        else:
            exit_sens_values.append(temp_analysis['val_uss']['share_price'])

    football_field_data.append({
        'Method': 'Exit Multiple',
        'Low': min(exit_sens_values),
        'High': max(exit_sens_values),
        'Description': '3.5x (trough) to 6.5x (peak) EV/EBITDA. Steel sector historical range 4-6x'
    })

    # 5. Wall Street Analyst Range (from fairness opinions)
    football_field_data.append({
        'Method': 'Analyst Fairness Opinions',
        'Low': 39.0,
        'High': 52.0,
        'Description': 'Barclays ($39-48) & Goldman ($42-52) DCF ranges from Dec 2023 proxy filing'
    })

    # 6. PE LBO Alternative (maximum price to achieve 20% IRR)
    football_field_data.append({
        'Method': 'PE LBO Maximum Price',
        'Low': 35.0,
        'High': 42.0,
        'Description': 'Max price PE firms could pay at 5.0x leverage to achieve 20% IRR target. Cannot compete at $55 offer.'
    })

    # 7. Current scenario point estimate
    if ff_perspective == "Value to Nippon":
        current_value = val_nippon['share_price']
    else:
        current_value = val_uss['share_price']

    # Build current scenario description with key assumptions
    current_desc = f'Your selection: {scenario.price_scenario.hrc_us_factor:.0%} prices, {scenario.uss_wacc*100:.1f}% WACC, {len(scenario.include_projects)} projects'
    # Floor at 0 - equity cannot be negative
    current_low = max(0, current_value - 2)
    current_high = max(0, current_value + 2)
    football_field_data.append({
        'Method': f'Current Scenario',
        'Low': current_low,
        'High': current_high,
        'Description': current_desc
    })

    # Create the football field chart
    ff_df = pd.DataFrame(football_field_data)

    # Sort by midpoint for better visualization
    ff_df['Midpoint'] = (ff_df['Low'] + ff_df['High']) / 2
    ff_df = ff_df.sort_values('Midpoint', ascending=True)

    fig_ff = go.Figure()

    # Add horizontal bars for each methodology
    colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692']
    for i, row in ff_df.iterrows():
        idx = list(ff_df.index).index(i)
        fig_ff.add_trace(go.Bar(
            y=[row['Method']],
            x=[row['High'] - row['Low']],
            base=[row['Low']],
            orientation='h',
            name=row['Method'],
            marker_color=colors[idx % len(colors)],
            hovertemplate=f"<b>{row['Method']}</b><br>" +
                         f"Range: ${row['Low']:.2f} - ${row['High']:.2f}<br>" +
                         f"{row['Description']}<extra></extra>",
            showlegend=False
        ))

        # Add midpoint marker
        midpoint = (row['Low'] + row['High']) / 2
        fig_ff.add_trace(go.Scatter(
            x=[midpoint],
            y=[row['Method']],
            mode='markers',
            marker=dict(color='white', size=10, symbol='diamond',
                       line=dict(color='black', width=2)),
            hoverinfo='skip',
            showlegend=False
        ))

    # Add $55 offer line
    fig_ff.add_vline(x=55, line_dash="dash", line_color="green", line_width=3,
                     annotation_text="$55 Nippon Offer", annotation_position="top")

    # Add PE maximum price line
    fig_ff.add_vline(x=40, line_dash="dot", line_color="red", line_width=2,
                     annotation_text="$40 PE Max (20% IRR)", annotation_position="bottom")

    # Add current value line
    fig_ff.add_vline(x=current_value, line_dash="dot", line_color="blue", line_width=2,
                     annotation_text=f"Current: ${current_value:.1f}", annotation_position="bottom")

    fig_ff.update_layout(
        title=f"Valuation Football Field ({ff_perspective})",
        xaxis_title="Equity Value per Share ($)",
        yaxis_title="",
        height=400,
        xaxis=dict(range=[0, max(ff_df['High'].max() * 1.1, 120)]),
        bargap=0.3
    )

    st.plotly_chart(fig_ff, use_container_width=True)

    # Summary table below chart
    with st.expander("View Detailed Ranges", expanded=False):
        display_ff_df = ff_df[['Method', 'Low', 'High', 'Description']].copy()
        display_ff_df['Low'] = display_ff_df['Low'].apply(lambda x: f"${x:.2f}")
        display_ff_df['High'] = display_ff_df['High'].apply(lambda x: f"${x:.2f}")
        display_ff_df['Range'] = display_ff_df.apply(
            lambda r: f"{r['Low']} - {r['High']}", axis=1
        )
        st.dataframe(
            display_ff_df[['Method', 'Range', 'Description']],
            use_container_width=True,
            hide_index=True
        )

    # Key insights
    ff_insight_col1, ff_insight_col2, ff_insight_col3 = st.columns(3)
    with ff_insight_col1:
        overall_low = ff_df['Low'].min()
        st.metric("Overall Low", f"${overall_low:.2f}")
    with ff_insight_col2:
        overall_high = ff_df['High'].max()
        st.metric("Overall High", f"${overall_high:.2f}")
    with ff_insight_col3:
        pct_above_offer = len([v for v in scenario_values if v > 55]) / len(scenario_values) * 100
        st.metric("Scenarios Above $55", f"{pct_above_offer:.0f}%")

    # =========================================================================
    # VALUE BRIDGE
    # =========================================================================

    st.markdown("---")
    st.header("Value Bridge", anchor="value-bridge")

    st.markdown("""
    **How to read this chart:**
    - This waterfall shows how value builds from USS standalone to Nippon's \\$55 offer
    - **USS - No Sale**: Starting point - what USS is worth on its own
    - **WACC Advantage**: Value added because Nippon has a lower cost of capital
    - **Value to Nippon**: Total intrinsic value from Nippon's perspective
    - **Gap to Offer**: Difference between intrinsic value and \\$55 offer (negative = Nippon buying at discount)
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
        yaxis_title="Equity Value ($/sh)",
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
    st.header("FCF Projection", anchor="fcf-projection")

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
    st.header("Segment Analysis", anchor="segment-analysis")

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
    st.header("Steel Price Sensitivity", anchor="steel-price-sensitivity")

    st.markdown("""
    **How to read this section:**
    - Steel prices are the #1 driver of valuation - a 10% price swing changes share value by \\$15-25
    - **Price Factor**: Multiplier applied to 2023 benchmark prices (0.8 = 20% below, 1.2 = 20% above)
    - The chart shows how share value changes as steel prices move up or down
    - Green dashed line = \\$55 Nippon offer price (breakeven around 88% price factor)
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
                nippon_equity_risk_premium=scenario.nippon_equity_risk_premium,
                nippon_credit_spread=scenario.nippon_credit_spread,
                nippon_debt_ratio=scenario.nippon_debt_ratio,
                nippon_tax_rate=scenario.nippon_tax_rate,
                include_projects=scenario.include_projects
            )

            test_model = PriceVolumeModel(test_scenario, custom_benchmarks=custom_benchmarks)
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
        fig.update_layout(yaxis_title='Equity Value ($/sh)')
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
    st.header("WACC Sensitivity Analysis", anchor="wacc-sensitivity")

    st.markdown("""
    **How to read this chart:**
    - **WACC (Weighted Average Cost of Capital)**: The discount rate used to calculate present value
    - Lower WACC = higher valuation (future cash flows are worth more today)
    - **Blue dashed line**: USS's standalone WACC (~10.9%)
    - **Red dashed line**: Nippon's IRP-adjusted WACC (~7.5%)
    - **Green dashed line**: \\$55 offer price
    - The gap between blue and red lines shows the "WACC advantage" Nippon gains from its lower cost of capital
    """)

    wacc_range = np.arange(0.05, 0.14, 0.005)
    wacc_sensitivity_data = []

    for w in wacc_range:
        val = model.calculate_dcf(consolidated, w)
        wacc_sensitivity_data.append({
            'WACC': w * 100,
            'Equity Value': val['share_price']
        })

    wacc_sens_df = pd.DataFrame(wacc_sensitivity_data)

    fig = px.line(
        wacc_sens_df,
        x='WACC',
        y='Equity Value',
        title='Equity Value per Share vs WACC',
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
        yaxis_title='Equity Value ($/sh)',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================================================================
    # INTEREST RATE PARITY ADJUSTMENT
    # =========================================================================

    st.markdown("---")
    st.header("Interest Rate Parity Adjustment", anchor="irp-adjustment")

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
    st.header("Detailed Projections", anchor="detailed-projections")

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
        st.markdown(f"### {scenario.name}")
        st.markdown(f"*{scenario.description}*")

        # Organize into columns
        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            st.markdown("#### Steel Price Assumptions")
            st.markdown(f"""
| Parameter | Value | Implied Price |
|-----------|-------|---------------|
| US HRC Factor | {scenario.price_scenario.hrc_us_factor:.0%} | ${custom_benchmarks['hrc_us'] * scenario.price_scenario.hrc_us_factor:.0f}/ton |
| US CRC Factor | {scenario.price_scenario.crc_us_factor:.0%} | ${custom_benchmarks['crc_us'] * scenario.price_scenario.crc_us_factor:.0f}/ton |
| Coated Factor | {scenario.price_scenario.coated_us_factor:.0%} | ${custom_benchmarks['coated_us'] * scenario.price_scenario.coated_us_factor:.0f}/ton |
| EU HRC Factor | {scenario.price_scenario.hrc_eu_factor:.0%} | ${custom_benchmarks['hrc_eu'] * scenario.price_scenario.hrc_eu_factor:.0f}/ton |
| OCTG Factor | {scenario.price_scenario.octg_factor:.0%} | ${custom_benchmarks['octg'] * scenario.price_scenario.octg_factor:,.0f}/ton |
| Annual Escalation | {scenario.price_scenario.annual_price_growth:.1%} | Compounded over 10Y |
            """)

            st.markdown("#### Volume Assumptions")
            st.markdown(f"""
| Segment | Volume Factor | Growth Adj |
|---------|---------------|------------|
| Flat-Rolled | {scenario.volume_scenario.flat_rolled_volume_factor:.0%} | {scenario.volume_scenario.flat_rolled_growth_adj:+.1%}/yr |
| Mini Mill | {scenario.volume_scenario.mini_mill_volume_factor:.0%} | {scenario.volume_scenario.mini_mill_growth_adj:+.1%}/yr |
| USSE | {scenario.volume_scenario.usse_volume_factor:.0%} | {scenario.volume_scenario.usse_growth_adj:+.1%}/yr |
| Tubular | {scenario.volume_scenario.tubular_volume_factor:.0%} | {scenario.volume_scenario.tubular_growth_adj:+.1%}/yr |
            """)

        with detail_col2:
            st.markdown("#### Valuation Parameters")
            st.markdown(f"""
| Parameter | Value | Notes |
|-----------|-------|-------|
| USS WACC | {scenario.uss_wacc*100:.1f}% | Standalone cost of capital |
| Terminal Growth | {scenario.terminal_growth*100:.2f}% | Perpetuity growth rate |
| Exit Multiple | {scenario.exit_multiple:.1f}x | EV/EBITDA at terminal year |
| Shares Outstanding | 225M | Undiluted basis |
            """)

            st.markdown("#### Interest Rate Parity")
            st.markdown(f"""
| Parameter | Value |
|-----------|-------|
| US 10-Year Treasury | {scenario.us_10yr*100:.2f}% |
| Japan 10-Year JGB | {scenario.japan_10yr*100:.2f}% |
| Rate Differential | {(scenario.us_10yr - scenario.japan_10yr)*100:.2f}% |
| Nippon JPY WACC | {jpy_wacc*100:.2f}% |
| Nippon USD WACC (IRP) | {usd_wacc*100:.2f}% |
| WACC Advantage | {(scenario.uss_wacc - usd_wacc)*100:.2f}% |
            """)

        st.markdown("#### Capital Projects")
        if scenario.include_projects:
            projects_info = get_capital_projects()
            project_rows = []
            for proj_name in scenario.include_projects:
                if proj_name in projects_info:
                    proj = projects_info[proj_name]
                    total_capex = sum(proj.capex_schedule.values())
                    final_ebitda = proj.ebitda_schedule.get(2033, 0)
                    project_rows.append(f"| {proj_name} | {proj.segment} | ${total_capex:,.0f}M | ${final_ebitda:,.0f}M |")

            st.markdown(f"""
| Project | Segment | Total CapEx | 2033 EBITDA |
|---------|---------|-------------|-------------|
{chr(10).join(project_rows)}
            """)
            if execution_factor < 1.0:
                st.markdown(f"*Execution factor: {execution_factor:.0%} applied to incremental projects (excludes BR2)*")
        else:
            st.markdown("*No capital projects selected*")

        st.markdown("#### Valuation Output")
        st.markdown(f"""
| Metric | USS Standalone | Value to Nippon |
|--------|----------------|-----------------|
| Equity Value/Share | ${val_uss['share_price']:.2f} | ${val_nippon['share_price']:.2f} |
| Enterprise Value | ${val_uss['ev_blended']:,.0f}M | ${val_nippon['ev_blended']:,.0f}M |
| 10Y FCF | ${consolidated['FCF'].sum():,.0f}M | ${consolidated['FCF'].sum():,.0f}M |
| vs $55 Offer | ${val_uss['share_price'] - 55:+.2f} | ${val_nippon['share_price'] - 55:+.2f} |
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
