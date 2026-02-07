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
import hashlib
import json
from datetime import datetime
from scripts import cache_persistence as cp
from scripts.price_correlation_analysis import (
    load_historical_prices,
    aggregate_prices_by_year,
    calculate_price_correlation,
    get_price_trend_summary,
    format_correlation_strength,
    get_correlation_insight_text
)

# Import the price x volume model
from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType,
    SteelPriceScenario, VolumeScenario, Segment,
    get_scenario_presets, get_segment_configs, compare_scenarios,
    calculate_probability_weighted_valuation,
    get_capital_projects, BENCHMARK_PRICES_2023,
    BENCHMARK_PRICES_THROUGH_CYCLE, TARIFF_CONFIG,
    calculate_tariff_adjustment, get_tariff_decomposition,
    get_synergy_presets, SynergyAssumptions, OperatingSynergies,
    TechnologyTransfer, RevenueSynergies, IntegrationCosts, SynergyRampSchedule,
    WACC_MODULE_AVAILABLE, get_wacc_module_status,
    BLOOMBERG_AVAILABLE, get_bloomberg_status, get_benchmark_prices,
    SCENARIO_CALIBRATION_AVAILABLE, get_calibration_mode_status,
)

# Optional: Import Bloomberg module for detailed status display
BLOOMBERG_DETAILS_AVAILABLE = False
try:
    import sys
    from pathlib import Path as BloombergPath
    _bloomberg_module_path = BloombergPath(__file__).parent / "market-data" / "bloomberg"
    if str(_bloomberg_module_path.parent) not in sys.path:
        sys.path.insert(0, str(_bloomberg_module_path.parent))

    from bloomberg import (
        get_bloomberg_service,
        get_price_comparison_table,
        is_bloomberg_available,
        get_wacc_overlay,
        # Scenario calibration
        ScenarioCalibrationMode,
        get_all_scenarios_for_mode,
        get_mode_description,
        get_mode_short_description,
    )
    BLOOMBERG_DETAILS_AVAILABLE = is_bloomberg_available()
except ImportError:
    get_bloomberg_service = None
    get_price_comparison_table = None
    is_bloomberg_available = None
    get_wacc_overlay = None
    ScenarioCalibrationMode = None
    get_all_scenarios_for_mode = None
    get_mode_description = None
    get_mode_short_description = None

# Optional: Import WACC module for detailed component display
try:
    import sys
    from pathlib import Path as WACCPath
    _wacc_module_path = WACCPath(__file__).parent / "wacc-calculations"
    if str(_wacc_module_path) not in sys.path:
        sys.path.insert(0, str(_wacc_module_path))
    from uss.uss_wacc import calculate_uss_wacc, get_analyst_estimates, get_data_as_of_date as get_uss_data_date
    from nippon.nippon_wacc import calculate_nippon_wacc, get_data_as_of_date as get_nippon_data_date
    WACC_DETAILS_AVAILABLE = True
except ImportError:
    WACC_DETAILS_AVAILABLE = False
    get_analyst_estimates = None
    get_uss_data_date = None
    get_nippon_data_date = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_dynamic_project_ebitda(model, proj, year):
    """Calculate project EBITDA using dynamic formula based on current scenario prices."""
    if proj.nameplate_capacity == 0:
        return proj.ebitda_schedule.get(year, 0)
    segment_map = {
        'Mini Mill': Segment.MINI_MILL,
        'Flat-Rolled': Segment.FLAT_ROLLED,
        'Tubular': Segment.TUBULAR,
        'USSE': Segment.USSE
    }
    segment_enum = segment_map.get(proj.segment)
    if segment_enum:
        segment_price = model.calculate_segment_price(segment_enum, year)
    else:
        segment_price = 900
    return model.calculate_project_ebitda(proj, year, segment_price)


def get_project_maintenance_capex(model, proj, year):
    """Calculate annual maintenance capex for a project."""
    return model.calculate_project_maintenance_capex(proj, year)


def create_scenario_hash(scenario, execution_factor, custom_benchmarks):
    """Generate hash of current scenario parameters for cache invalidation."""
    scenario_dict = {
        'scenario_type': scenario.scenario_type.name,
        'execution_factor': execution_factor,
        'prices': {
            'hrc_us': scenario.price_scenario.hrc_us_factor,
            'crc_us': scenario.price_scenario.crc_us_factor,
            'coated_us': scenario.price_scenario.coated_us_factor,
            'hrc_eu': scenario.price_scenario.hrc_eu_factor,
            'octg': scenario.price_scenario.octg_factor,
        },
        'volumes': {
            'flat_rolled_vf': scenario.volume_scenario.flat_rolled_volume_factor,
            'flat_rolled_ga': scenario.volume_scenario.flat_rolled_growth_adj,
            'mini_mill_vf': scenario.volume_scenario.mini_mill_volume_factor,
            'mini_mill_ga': scenario.volume_scenario.mini_mill_growth_adj,
            'usse_vf': scenario.volume_scenario.usse_volume_factor,
            'usse_ga': scenario.volume_scenario.usse_growth_adj,
            'tubular_vf': scenario.volume_scenario.tubular_volume_factor,
            'tubular_ga': scenario.volume_scenario.tubular_growth_adj,
        },
        'financial': {
            'uss_wacc': scenario.uss_wacc,
            'terminal_growth': scenario.terminal_growth,
            'exit_multiple': scenario.exit_multiple,
            'use_verified_wacc': getattr(scenario, 'use_verified_wacc', False),
        },
        'projects': scenario.include_projects if scenario.include_projects else [],
        'custom_benchmarks': custom_benchmarks if custom_benchmarks else {}
    }
    return hashlib.md5(json.dumps(scenario_dict, sort_keys=True).encode()).hexdigest()


def render_calculation_button(
    section_name: str,
    button_label: str,
    session_key: str
) -> bool:
    """
    Render a consistent calculation button with status messages.

    Returns: True if button was clicked, False otherwise
    """
    col1, col2 = st.columns([1, 4])

    with col1:
        is_calculated = st.session_state[session_key] is not None
        is_stale = session_key in st.session_state.get('stale_sections', set())

        button_text = "Recalculate" if is_calculated else button_label
        button_type = "primary" if (not is_calculated or is_stale) else "secondary"

        clicked = st.button(
            button_text,
            type=button_type,
            key=f"btn_{session_key}"
        )

    with col2:
        if is_stale:
            st.warning(f"Parameters changed. Click {button_text} to update.")
        elif is_calculated:
            result = st.session_state[session_key]
            if 'timestamp' in result:
                time_str = result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                st.success(f"Calculated at {time_str}")
            else:
                st.success("Up to date")
        else:
            st.info(f"Click to {button_label.lower()}")

    # Clear stale flag after recalculation
    if clicked and is_stale:
        st.session_state.stale_sections.discard(session_key)

    return clicked


@st.cache_data
def load_uss_stock_data():
    """Load USS daily stock price data for price comparison analysis."""
    path = Path(__file__).parent / "market-data" / "exports" / "processed" / "stock_uss.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').reset_index(drop=True)


@st.cache_data
def load_historical_steel_prices():
    """Load historical steel price data for correlation analysis."""
    try:
        base_path = str(Path(__file__).parent / "market-data" / "exports" / "processed")
        return load_historical_prices(base_path)
    except FileNotFoundError as e:
        st.warning(f"Historical price data not available: {e}")
        return None
    except Exception as e:
        st.error(f"Error loading historical prices: {e}")
        return None


@st.cache_data
def load_monte_carlo_data():
    """Load Monte Carlo simulation results and inputs from CSV files."""
    results_path = Path(__file__).parent / "data" / "monte_carlo_results.csv"
    inputs_path = Path(__file__).parent / "data" / "monte_carlo_inputs.csv"
    if not results_path.exists() or not inputs_path.exists():
        return None
    try:
        results_df = pd.read_csv(results_path)
        inputs_df = pd.read_csv(inputs_path)
        return results_df, inputs_df
    except Exception as e:
        st.error(f"Error loading Monte Carlo data: {e}")
        return None


# Human-readable labels for Monte Carlo input variables
MC_VARIABLE_LABELS = {
    'hrc_price_factor': 'HRC US Price',
    'crc_price_factor': 'CRC US Price',
    'coated_price_factor': 'Coated Price',
    'octg_price_factor': 'OCTG Price',
    'flat_rolled_volume': 'Flat Rolled Volume',
    'mini_mill_volume': 'Mini Mill Volume',
    'tubular_volume': 'Tubular Volume',
    'usse_volume': 'USSE Volume',
    'annual_price_growth': 'Annual Price Growth',
    'hrc_eu_factor': 'HRC EU Price',
    'eur_usd_factor': 'EUR/USD Rate',
    'uss_wacc': 'WACC',
    'japan_rf_rate': 'Japan Risk-Free Rate',
    'us_10yr': 'US 10-Year Yield',
    'nippon_erp': 'Nippon Equity Risk Premium',
    'terminal_growth': 'Terminal Growth Rate',
    'exit_multiple': 'Exit Multiple',
    'gary_works_execution': 'Gary Works Execution',
    'mon_valley_execution': 'Mon Valley Execution',
    'flat_rolled_margin_factor': 'Flat Rolled Margin',
    'operating_synergy_factor': 'Operating Synergies',
    'revenue_synergy_factor': 'Revenue Synergies',
    'working_capital_efficiency': 'Working Capital Efficiency',
    'capex_intensity_factor': 'Capex Intensity',
    'tariff_probability': 'Tariff Probability',
    'tariff_rate_if_changed': 'Tariff Rate (if changed)',
}


# USS Price Comparison Constants
USS_NIPPON_ANNOUNCEMENT_DATE = '2023-12-18'
USS_PRE_RUMOR_END = '2023-12-12'
USS_RUMOR_PERIOD_START = '2023-12-13'
USS_LAST_TRADING_DAY_BEFORE = '2023-12-15'
USS_NIPPON_OFFER_PRICE = 55.00
USS_CLIFFS_OFFER_PRICE = 54.00
USS_LBO_ESTIMATE_LOW = 35.00  # PE LBO floor estimate
USS_LBO_ESTIMATE_HIGH = 42.00  # PE LBO ceiling estimate
USS_ANALYST_CONSENSUS = 45.00  # Wall Street consensus price target (pre-deal)
USS_DATA_START_YEAR = '2005-01-01'  # Start from 2005 for relevant history

# Key market epochs for context
USS_MARKET_EPOCHS = [
    {'name': 'GFC', 'start': '2007-10-01', 'end': '2009-03-31', 'color': 'rgba(255,107,107,0.15)'},
    {'name': 'COVID', 'start': '2020-02-01', 'end': '2020-06-30', 'color': 'rgba(255,193,7,0.15)'},
]


def create_price_history_chart(df, start_date, end_date):
    """Create USS stock price history chart with all reference lines and epoch markers."""
    mask = (df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))
    filtered_df = df[mask].copy()

    if filtered_df.empty:
        return None

    fig = go.Figure()

    # Add epoch shading (GFC, COVID) if within range
    for epoch in USS_MARKET_EPOCHS:
        epoch_start = pd.to_datetime(epoch['start'])
        epoch_end = pd.to_datetime(epoch['end'])
        if pd.to_datetime(start_date) <= epoch_end and pd.to_datetime(end_date) >= epoch_start:
            # Clip to visible range
            vis_start = max(pd.to_datetime(start_date), epoch_start)
            vis_end = min(pd.to_datetime(end_date), epoch_end)
            fig.add_vrect(
                x0=vis_start.strftime('%Y-%m-%d'),
                x1=vis_end.strftime('%Y-%m-%d'),
                fillcolor=epoch['color'],
                layer="below",
                line_width=0,
                annotation_text=epoch['name'],
                annotation_position="top left",
                annotation=dict(font_size=10, font_color="gray")
            )

    # Main price line
    fig.add_trace(go.Scatter(
        x=filtered_df['date'],
        y=filtered_df['value'],
        mode='lines',
        name='USS Stock Price',
        line=dict(color='#3498db', width=2),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Price: $%{y:.2f}<extra></extra>'
    ))

    # Always show all reference lines (no toggles)
    # Nippon Offer - Green
    fig.add_hline(
        y=USS_NIPPON_OFFER_PRICE,
        line_dash="dash",
        line_color="#27ae60",
        annotation_text=f"Nippon Offer ${USS_NIPPON_OFFER_PRICE:.0f}",
        annotation_position="top right"
    )

    # Cliffs Offer - Orange
    fig.add_hline(
        y=USS_CLIFFS_OFFER_PRICE,
        line_dash="dash",
        line_color="#e67e22",
        annotation_text=f"Cliffs Offer ${USS_CLIFFS_OFFER_PRICE:.0f}",
        annotation_position="right"
    )

    # Analyst Consensus - Purple
    fig.add_hline(
        y=USS_ANALYST_CONSENSUS,
        line_dash="dot",
        line_color="#9b59b6",
        annotation_text=f"Analyst Target ${USS_ANALYST_CONSENSUS:.0f}",
        annotation_position="right"
    )

    # LBO Range - Gray band
    fig.add_hrect(
        y0=USS_LBO_ESTIMATE_LOW,
        y1=USS_LBO_ESTIMATE_HIGH,
        fillcolor="rgba(128,128,128,0.1)",
        line_width=0,
        annotation_text=f"LBO Range ${USS_LBO_ESTIMATE_LOW:.0f}-${USS_LBO_ESTIMATE_HIGH:.0f}",
        annotation_position="bottom right",
        annotation=dict(font_size=9, font_color="gray")
    )

    # Pre-rumor end vertical line (Dec 12, 2023)
    pre_rumor_date = pd.to_datetime(USS_PRE_RUMOR_END)
    if pd.to_datetime(start_date) <= pre_rumor_date <= pd.to_datetime(end_date):
        fig.add_shape(
            type="line",
            x0=USS_PRE_RUMOR_END,
            x1=USS_PRE_RUMOR_END,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#e74c3c", width=1.5, dash="dashdot")
        )
        fig.add_annotation(
            x=USS_PRE_RUMOR_END,
            y=0.95,
            yref="paper",
            text="Pre-Rumor End",
            showarrow=False,
            xshift=-5,
            textangle=-90,
            font=dict(color="#e74c3c", size=9)
        )

    # Announcement date vertical line (Dec 18, 2023)
    announcement_date = pd.to_datetime(USS_NIPPON_ANNOUNCEMENT_DATE)
    if pd.to_datetime(start_date) <= announcement_date <= pd.to_datetime(end_date):
        fig.add_shape(
            type="line",
            x0=USS_NIPPON_ANNOUNCEMENT_DATE,
            x1=USS_NIPPON_ANNOUNCEMENT_DATE,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="#2ecc71", width=2, dash="dot")
        )
        fig.add_annotation(
            x=USS_NIPPON_ANNOUNCEMENT_DATE,
            y=1,
            yref="paper",
            text="Nippon Announcement",
            showarrow=False,
            yshift=10,
            font=dict(color="#2ecc71", size=10)
        )

    fig.update_layout(
        title="USS Stock Price History with Key Reference Points",
        xaxis_title="Date",
        yaxis_title="Stock Price ($)",
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    return fig


def create_dual_axis_chart_with_price(
    projection_data,
    price_data,
    projection_label,
    price_label,
    projection_color="#4ecdc4",
    price_color="#ff6b6b",
    chart_title="Projection with Price Overlay"
):
    """
    Create a dual-axis chart with projections (bars) and price overlay (line).

    Args:
        projection_data: Dict with 'years' and 'values' keys for projection metric
        price_data: Dict with 'years' and 'values' keys for price series
        projection_label: Label for projection metric (left axis)
        price_label: Label for price series (right axis)
        projection_color: Color for projection bars
        price_color: Color for price line
        chart_title: Title for the chart

    Returns:
        Plotly figure with dual y-axes
    """
    from plotly.subplots import make_subplots

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add projection bars (left axis)
    fig.add_trace(
        go.Bar(
            x=projection_data['years'],
            y=projection_data['values'],
            name=projection_label,
            marker_color=projection_color,
            hovertemplate='%{x}<br>%{y:,.0f}<extra></extra>'
        ),
        secondary_y=False
    )

    # Add price line (right axis)
    fig.add_trace(
        go.Scatter(
            x=price_data['years'],
            y=price_data['values'],
            name=price_label,
            mode='lines+markers',
            line=dict(color=price_color, width=3),
            marker=dict(size=8, color=price_color),
            hovertemplate='%{x}<br>\\$%{y:,.0f}/ton<extra></extra>'
        ),
        secondary_y=True
    )

    # Configure axes
    fig.update_xaxes(title_text="Year")
    fig.update_yaxes(title_text=projection_label, secondary_y=False)
    fig.update_yaxes(title_text=price_label, secondary_y=True)

    # Update layout
    fig.update_layout(
        title=chart_title,
        hovermode='x unified',
        height=500,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )

    return fig


def create_period_comparison_chart(df):
    """Create enhanced bar chart comparing multiple periods with all reference lines."""
    # Calculate period averages
    pre_rumor_mask = df['date'] <= pd.to_datetime(USS_PRE_RUMOR_END)
    rumor_mask = (df['date'] >= pd.to_datetime(USS_RUMOR_PERIOD_START)) & (df['date'] <= pd.to_datetime(USS_LAST_TRADING_DAY_BEFORE))
    post_announce_mask = df['date'] >= pd.to_datetime(USS_NIPPON_ANNOUNCEMENT_DATE)

    # Also calculate 2023 YTD (before any deal speculation)
    ytd_2023_mask = (df['date'] >= pd.to_datetime('2023-01-01')) & (df['date'] <= pd.to_datetime('2023-11-30'))

    pre_avg = df[pre_rumor_mask]['value'].mean() if pre_rumor_mask.any() else 0
    rumor_avg = df[rumor_mask]['value'].mean() if rumor_mask.any() else 0
    post_avg = df[post_announce_mask]['value'].mean() if post_announce_mask.any() else 0
    ytd_avg = df[ytd_2023_mask]['value'].mean() if ytd_2023_mask.any() else 0

    fig = go.Figure()

    # Multi-period comparison
    periods = ['2023 YTD<br>(Jan-Nov)', 'Pre-Rumor<br>(through Dec 12)', 'Rumor Period<br>(Dec 13-15)', 'Post-Announce<br>(Dec 18+)']
    values = [ytd_avg, pre_avg, rumor_avg, post_avg]
    colors = ['#95a5a6', '#3498db', '#f39c12', '#2ecc71']

    fig.add_trace(go.Bar(
        x=periods,
        y=values,
        marker_color=colors,
        text=[f'${v:.2f}' for v in values],
        textposition='outside'
    ))

    # Add all reference lines
    fig.add_hline(y=USS_NIPPON_OFFER_PRICE, line_dash="dash", line_color="#27ae60",
                  annotation_text=f"Nippon ${USS_NIPPON_OFFER_PRICE:.0f}")
    fig.add_hline(y=USS_CLIFFS_OFFER_PRICE, line_dash="dash", line_color="#e67e22",
                  annotation_text=f"Cliffs ${USS_CLIFFS_OFFER_PRICE:.0f}")
    fig.add_hline(y=USS_ANALYST_CONSENSUS, line_dash="dot", line_color="#9b59b6",
                  annotation_text=f"Analyst ${USS_ANALYST_CONSENSUS:.0f}")

    # LBO range shading
    fig.add_hrect(y0=USS_LBO_ESTIMATE_LOW, y1=USS_LBO_ESTIMATE_HIGH,
                  fillcolor="rgba(128,128,128,0.1)", line_width=0)

    fig.update_layout(
        title="Average Price by Period vs Offer Benchmarks",
        yaxis_title="Average Stock Price ($)",
        height=550,
        showlegend=False
    )

    return fig


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
    # Initialize calibration mode early (UI control is rendered later in sidebar)
    if 'calibration_mode' not in st.session_state:
        st.session_state.calibration_mode = 'bloomberg' if SCENARIO_CALIBRATION_AVAILABLE else None

    # Scenario Selection
    st.sidebar.header("Scenario Selection")

    scenario_options = {
        "Severe Downturn - Historical Crisis": ScenarioType.SEVERE_DOWNTURN,
        "Downside - Weak Markets": ScenarioType.DOWNSIDE,
        "Mid-Cycle Base Case": ScenarioType.BASE_CASE,
        "Above Average - Strong Cycle": ScenarioType.ABOVE_AVERAGE,
        "Wall Street - Analyst Views": ScenarioType.WALL_STREET,
        "Optimistic - Sustained Growth": ScenarioType.OPTIMISTIC,
        "Management Dec 2023 Guidance": ScenarioType.MANAGEMENT,
        "Nippon Investment Case": ScenarioType.NIPPON_COMMITMENTS,
        "Stress: Extreme Downside (2008)": ScenarioType.EXTREME_DOWNSIDE,
        "Stress: Extreme Upside (Boom)": ScenarioType.EXTREME_UPSIDE,
        "Stress: Project Execution Failure": ScenarioType.PROJECT_FAILURE,
        "Custom": ScenarioType.CUSTOM
    }

    selected_scenario_name = st.sidebar.selectbox(
        "Select Scenario",
        options=list(scenario_options.keys()),
        index=2,  # Default to Base Case
        help="Pre-built scenarios with different assumptions. Select 'Custom' to manually adjust all parameters."
    )
    selected_scenario_type = scenario_options[selected_scenario_name]

    # Auto-reset values when scenario changes (but not on initial load)
    if st.session_state.previous_scenario is not None and st.session_state.previous_scenario != selected_scenario_name:
        st.session_state.reset_section = "all"
    st.session_state.previous_scenario = selected_scenario_name

    # Show scenario description
    scenario_descriptions = {
        "Severe Downturn - Historical Crisis": "Recession scenario (0.70x prices, -2% decline, 13.5% WACC) - Historical frequency: 25%",
        "Downside - Weak Markets": "Weak cycle (0.85x flat prices, 12% WACC) - Historical frequency: 30%",
        "Mid-Cycle Base Case": "Mid-cycle (0.90x prices, +1% growth, 10.9% WACC) - Historical frequency: 30%",
        "Above Average - Strong Cycle": "Strong markets (0.95x prices, +1.5% growth, 10.9% WACC) - Historical frequency: 10%",
        "Wall Street - Analyst Views": "DEFM14A fairness opinion midpoint (1.02x prices, 0% growth, 12.5% WACC) - \\$38-52 range",
        "Optimistic - Sustained Growth": "Sustained favorable markets (1.00x benchmark, +2% growth) - Historical frequency: 5%",
        "Management Dec 2023 Guidance": "Management guidance (Dec 2023): maps to Optimistic with 2% growth assumptions",
        "Nippon Investment Case": "\\$14B capital program, all 6 projects, no plant closures through 2035",
        "Stress: Extreme Downside (2008)": "GFC-level crisis: -40% prices, -20% volumes, 13.9% WACC (informational stress test)",
        "Stress: Extreme Upside (Boom)": "Infrastructure supercycle: +30% prices, +15% volumes, 8.9% WACC (informational stress test)",
        "Stress: Project Execution Failure": "All NSA projects deliver 50% of expected EBITDA; base case prices/volumes",
        "Custom": "Manually adjust all parameters below."
    }
    st.sidebar.caption(scenario_descriptions.get(selected_scenario_name, ""))

    # Reset All button
    if st.sidebar.button("↺ Reset All to Scenario Defaults", key="reset_all", help="Reset ALL parameters to the selected scenario's defaults", type="secondary"):
        st.session_state.reset_section = "all"
        st.rerun()

    # Get preset values (pass calibration and probability modes if available)
    calibration_mode = st.session_state.get('calibration_mode')
    probability_mode = st.session_state.get('probability_mode')
    presets = get_scenario_presets(calibration_mode=calibration_mode, probability_mode=probability_mode)
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
        # Set tariff_selection to match preset tariff_rate
        preset_tariff = getattr(preset.price_scenario, 'tariff_rate', 0.25)
        if abs(preset_tariff - 0.0) < 0.01:
            st.session_state.tariff_selection = "0% — Tariff Removal"
        elif abs(preset_tariff - 0.50) < 0.01:
            st.session_state.tariff_selection = "50% — Tariff Escalation"
        else:
            st.session_state.tariff_selection = "25% — Current Policy"
        st.session_state.eur_usd_rate = getattr(preset.price_scenario, 'eur_usd_rate', 1.08)
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
        st.session_state.use_verified_wacc = True
        # Reset IRP
        st.session_state.us_10yr = preset.us_10yr * 100
        st.session_state.japan_10yr = preset.japan_10yr * 100
        st.session_state.n_erp = preset.nippon_equity_risk_premium * 100
        st.session_state.n_cs = preset.nippon_credit_spread * 100
        st.session_state.n_dr = preset.nippon_debt_ratio * 100
        st.session_state.n_tr = preset.nippon_tax_rate * 100
        st.session_state.override_irp = False
        if 'manual_nippon_usd_wacc' in st.session_state:
            del st.session_state.manual_nippon_usd_wacc
        # Reset capital projects
        st.session_state.include_br2 = 'BR2 Mini Mill' in preset.include_projects
        st.session_state.include_gary = 'Gary Works BF' in preset.include_projects
        st.session_state.include_mon_valley = 'Mon Valley HSM' in preset.include_projects
        st.session_state.include_greenfield = 'Greenfield Mini Mill' in preset.include_projects
        st.session_state.include_mining = 'Mining Investment' in preset.include_projects
        st.session_state.include_fairfield = 'Fairfield Works' in preset.include_projects
        st.session_state.reset_section = None
        st.rerun()  # Rerun to apply the new values to widgets

    st.sidebar.markdown("---")

    # Steel Price Benchmarks
    st.sidebar.header("Steel Price Benchmarks")

    # Through-cycle baseline (structural equilibrium, not 2023 elevated)
    benchmark_defaults = BENCHMARK_PRICES_2023  # Now through-cycle
    st.sidebar.caption("Baseline: Through-Cycle Equilibrium (factor 1.0 = mid-cycle)")

    if st.sidebar.button("↺ Reset to Default", key="reset_benchmarks", help="Reset benchmark prices to defaults"):
        st.session_state.reset_section = "benchmarks"
        st.rerun()

    # Handle benchmark reset
    if st.session_state.reset_section == "benchmarks":
        st.session_state.hrc_us = benchmark_defaults.get('hrc_us', BENCHMARK_PRICES_2023['hrc_us'])
        st.session_state.crc_us = benchmark_defaults.get('crc_us', BENCHMARK_PRICES_2023['crc_us'])
        st.session_state.coated_us = benchmark_defaults.get('coated_us', BENCHMARK_PRICES_2023['coated_us'])
        st.session_state.hrc_eu = benchmark_defaults.get('hrc_eu', BENCHMARK_PRICES_2023['hrc_eu'])
        st.session_state.octg = benchmark_defaults.get('octg', BENCHMARK_PRICES_2023['octg'])
        st.session_state.reset_section = None

    col1, col2 = st.sidebar.columns(2)
    with col1:
        hrc_us = st.number_input("US HRC", value=float(st.session_state.get('hrc_us', BENCHMARK_PRICES_2023['hrc_us'])), step=10.0, key="hrc_us", help="Hot-Rolled Coil - Primary flat steel product")
        crc_us = st.number_input("US CRC", value=float(st.session_state.get('crc_us', BENCHMARK_PRICES_2023['crc_us'])), step=10.0, key="crc_us", help="Cold-Rolled Coil - Higher margin product")
        coated_us = st.number_input("Coated", value=float(st.session_state.get('coated_us', BENCHMARK_PRICES_2023['coated_us'])), step=10.0, key="coated_us", help="Galvanized/Coated - Premium product")
    with col2:
        hrc_eu = st.number_input("EU HRC", value=float(st.session_state.get('hrc_eu', BENCHMARK_PRICES_2023['hrc_eu'])), step=10.0, key="hrc_eu", help="European Hot-Rolled Coil (USSE segment)")
        octg = st.number_input("OCTG", value=float(st.session_state.get('octg', BENCHMARK_PRICES_2023['octg'])), step=50.0, key="octg", help="Oil Country Tubular Goods (Tubular segment)")

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
        st.session_state.eur_usd_rate = getattr(preset.price_scenario, 'eur_usd_rate', 1.08)
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

    eur_usd_rate = st.sidebar.slider(
        "EUR/USD Rate",
        0.90, 1.25, st.session_state.get('eur_usd_rate', getattr(preset.price_scenario, 'eur_usd_rate', 1.08)), 0.01,
        format="%.2f",
        key="eur_usd_rate",
        help="EUR/USD exchange rate. Base: 1.08. Affects USSE segment realized prices (EUR-denominated revenues)."
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

    # Section 232 Tariff Controls
    with st.sidebar.expander("Section 232 Tariff", expanded=False):
        # Radio buttons for discrete tariff scenarios
        tariff_options = {
            "0% — Tariff Removal": 0.0,
            "25% — Current Policy": 0.25,
            "50% — Tariff Escalation": 0.50
        }
        default_tariff = getattr(preset.price_scenario, 'tariff_rate', 0.25)
        # Find matching option
        default_label = next((k for k, v in tariff_options.items() if abs(v - default_tariff) < 0.01), "25% — Current Policy")

        tariff_selection = st.radio(
            "Tariff Policy Scenario",
            options=list(tariff_options.keys()),
            index=list(tariff_options.keys()).index(default_label),
            key="tariff_selection",
            help="Section 232 steel import tariff rate. Current policy is 25%. Model evaluates removal (0%) or escalation (50%)."
        )
        tariff_rate = tariff_options[tariff_selection]

        if abs(tariff_rate - 0.25) > 0.01:
            hrc_adj = calculate_tariff_adjustment(tariff_rate, 'hrc_us')
            st.caption(f"HRC price adjustment: {hrc_adj:.2f}x (vs 1.00x at 25%)")
        else:
            st.caption("Current baseline — no adjustment")

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
        fr_vol_factor = st.slider("Flat-Rolled", 0.7, 1.3, st.session_state.get('fr_vf', preset.volume_scenario.flat_rolled_volume_factor), 0.05, key="fr_vf",
                                   help="Integrated steel mills (Gary, Mon Valley). Facing structural decline without investment.")
        mm_vol_factor = st.slider("Mini Mill", 0.8, 1.5, st.session_state.get('mm_vf', preset.volume_scenario.mini_mill_volume_factor), 0.05, key="mm_vf",
                                   help="Electric Arc Furnace operations (Big River Steel). Highest growth segment.")
        usse_vol_factor = st.slider("USSE", 0.7, 1.3, st.session_state.get('usse_vf', preset.volume_scenario.usse_volume_factor), 0.05, key="usse_vf",
                                     help="U.S. Steel Europe (Slovakia). Exposed to EU market conditions.")
        tub_vol_factor = st.slider("Tubular", 0.6, 1.5, st.session_state.get('tub_vf', preset.volume_scenario.tubular_volume_factor), 0.05, key="tub_vf",
                                    help="Oil Country Tubular Goods (OCTG). Tied to energy sector drilling activity.")

    with st.sidebar.expander("Volume Growth Adjustments", expanded=False):
        fr_growth_adj = st.slider("Flat-Rolled Growth Adj", -3.0, 2.0, st.session_state.get('fr_ga', preset.volume_scenario.flat_rolled_growth_adj * 100), 0.5, format="%.1f%%", key="fr_ga",
                                   help="Typically negative due to aging blast furnaces and capacity rationalization") / 100
        mm_growth_adj = st.slider("Mini Mill Growth Adj", -2.0, 8.0, st.session_state.get('mm_ga', preset.volume_scenario.mini_mill_growth_adj * 100), 0.5, format="%.1f%%", key="mm_ga",
                                   help="Typically positive due to BR2 ramp-up and EAF market share gains") / 100
        usse_growth_adj = st.slider("USSE Growth Adj", -4.0, 4.0, st.session_state.get('usse_ga', preset.volume_scenario.usse_growth_adj * 100), 0.5, format="%.1f%%", key="usse_ga",
                                     help="Depends on European industrial demand and energy costs") / 100
        tub_growth_adj = st.slider("Tubular Growth Adj", -5.0, 10.0, st.session_state.get('tub_ga', preset.volume_scenario.tubular_growth_adj * 100), 0.5, format="%.1f%%", key="tub_ga",
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
        st.session_state.use_verified_wacc = True
        st.session_state.reset_section = None

    # WACC Verification Toggle (before slider so it can set the slider value)
    # Default: True for most scenarios, False for Wall Street (which uses analyst WACC)
    default_use_verified = WACC_MODULE_AVAILABLE and (selected_scenario_type != ScenarioType.WALL_STREET)
    use_verified_wacc = default_use_verified
    if WACC_MODULE_AVAILABLE:
        use_verified_wacc = st.sidebar.checkbox(
            "Use Verified WACC",
            value=st.session_state.get('use_verified_wacc', default_use_verified),
            key="use_verified_wacc",
            help="Load WACC from wacc-calculations module (USS 10.7%, Nippon 7.95%). Unchecked for Wall Street to honor analyst WACC (12.5%)."
        )

        if use_verified_wacc:
            wacc_status = get_wacc_module_status()
            # Sync the slider value to the verified WACC
            verified_uss_wacc_pct = wacc_status['uss_wacc'] * 100
            st.session_state.uss_wacc = verified_uss_wacc_pct
            st.sidebar.info(f"**Verified WACC Values:**\n\n"
                           f"USS: {wacc_status['uss_wacc']*100:.2f}%\n\n"
                           f"Nippon USD: {wacc_status['nippon_usd_wacc']*100:.2f}%\n\n"
                           f"Data as of: {wacc_status['data_as_of_date']}")

    uss_wacc = st.sidebar.slider("USS WACC", 7.0, 15.0, st.session_state.get('uss_wacc', preset.uss_wacc * 100), 0.1, format="%.1f%%",
                                  key="uss_wacc",
                                  help="USS standalone Weighted Average Cost of Capital. Higher = lower valuation. Typical range 10-12% for steel companies.") / 100
    terminal_growth = st.sidebar.slider("Terminal Growth", 0.0, 3.5, st.session_state.get('terminal_growth', preset.terminal_growth * 100), 0.25, format="%.2f%%",
                                         key="terminal_growth",
                                         help="Perpetual growth rate after 2033 for Gordon Growth terminal value. Steel is mature industry, typically 0-2%.") / 100
    exit_multiple = st.sidebar.slider("Exit Multiple (EBITDA)", 3.0, 8.0, st.session_state.get('exit_multiple', preset.exit_multiple), 0.5, format="%.1fx",
                                       key="exit_multiple",
                                       help="EV/EBITDA multiple for exit-based terminal value. Steel sector typically trades 4-6x.")

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

    # Execution Factor (for Nippon Commitments, Project Failure, or when multiple projects enabled)
    execution_factor = 1.0
    if selected_scenario_type == ScenarioType.PROJECT_FAILURE:
        execution_factor = 0.5  # Fixed at 50% for project failure stress test
        st.sidebar.markdown("---")
        st.sidebar.info("Project Execution Failure: execution factor fixed at 50%")
    elif selected_scenario_type == ScenarioType.NIPPON_COMMITMENTS or len(include_projects) > 1:
        st.sidebar.markdown("---")
        st.sidebar.header("Execution Risk")
        execution_pct = st.sidebar.slider(
            "Execution Factor",
            min_value=50, max_value=100, value=100, step=5,
            format="%d%%",
            help="100% = full projected benefits achieved. 75% = 25% haircut to incremental project EBITDA/volume. Does not affect BR2 (already committed)."
        )
        execution_factor = execution_pct / 100.0

    # ==========================================================================
    # SYNERGY ASSUMPTIONS
    # ==========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("Synergy Assumptions")

    synergy_presets = get_synergy_presets()
    synergy_options = {
        "None (No Synergies)": "none",
        "Conservative": "conservative",
        "Base Case": "base_case",
        "Optimistic": "optimistic",
        "Custom": "custom"
    }

    selected_synergy_name = st.sidebar.selectbox(
        "Synergy Preset",
        options=list(synergy_options.keys()),
        index=0,  # Default to None
        help="Select synergy assumptions for Nippon valuation. Synergies only apply to Nippon's value, not USS standalone."
    )
    selected_synergy_key = synergy_options[selected_synergy_name]

    # Synergy descriptions
    synergy_descriptions = {
        "None (No Synergies)": "No merger synergies modeled. Nippon value = WACC advantage only.",
        "Conservative": "\\$120M operating + 1% tech + \\$150M revenue synergies, \\$325M integration costs",
        "Base Case": "\\$240M operating + 2% tech + \\$350M revenue synergies, \\$325M integration costs",
        "Optimistic": "\\$370M operating + 3% tech + \\$700M revenue synergies, \\$450M integration costs",
        "Custom": "Manually configure all synergy parameters below"
    }
    st.sidebar.caption(synergy_descriptions.get(selected_synergy_name, ""))

    # Get synergy preset
    if selected_synergy_key == "custom":
        synergy_preset = synergy_presets["base_case"]  # Start from base case for custom
    elif selected_synergy_key in synergy_presets:
        synergy_preset = synergy_presets[selected_synergy_key]
    else:
        synergy_preset = None

    # Custom synergy inputs (only if Custom selected)
    synergies = synergy_preset

    if selected_synergy_key == "custom":
        with st.sidebar.expander("Operating Synergies", expanded=False):
            custom_procurement = st.slider(
                "Procurement Savings ($M/yr)",
                0.0, 200.0, 100.0, 10.0,
                key="syn_procurement",
                help="Annual savings from combined purchasing power"
            )
            custom_logistics = st.slider(
                "Logistics Savings ($M/yr)",
                0.0, 150.0, 60.0, 10.0,
                key="syn_logistics",
                help="Annual savings from network optimization"
            )
            custom_overhead = st.slider(
                "Overhead Savings ($M/yr)",
                0.0, 150.0, 80.0, 10.0,
                key="syn_overhead",
                help="Annual savings from G&A consolidation"
            )

        with st.sidebar.expander("Technology Transfer", expanded=False):
            custom_yield = st.slider(
                "Yield Improvement (%)",
                0.0, 5.0, 2.0, 0.5,
                key="syn_yield",
                help="Production yield improvement from Nippon know-how"
            ) / 100
            custom_quality_premium = st.slider(
                "Quality Price Premium (%)",
                0.0, 5.0, 2.0, 0.5,
                key="syn_quality",
                help="Price premium from improved quality"
            ) / 100
            custom_conversion = st.slider(
                "Conversion Cost Reduction (%)",
                0.0, 8.0, 4.0, 1.0,
                key="syn_conversion",
                help="Reduction in conversion costs"
            ) / 100
            custom_tech_confidence = st.slider(
                "Technology Confidence",
                0.5, 1.0, 0.70, 0.05,
                key="syn_tech_conf",
                help="Probability of achieving technology synergies"
            )

        with st.sidebar.expander("Revenue Synergies", expanded=False):
            custom_crosssell = st.slider(
                "Cross-Sell Revenue ($M/yr)",
                0.0, 500.0, 200.0, 25.0,
                key="syn_crosssell",
                help="Additional revenue from cross-selling to Nippon customers"
            )
            custom_productmix = st.slider(
                "Product Mix Uplift ($M/yr)",
                0.0, 400.0, 150.0, 25.0,
                key="syn_productmix",
                help="Revenue from improved product mix"
            )

        with st.sidebar.expander("Integration Costs", expanded=False):
            custom_it_cost = st.slider(
                "IT Integration ($M)",
                0.0, 300.0, 125.0, 25.0,
                key="syn_it_cost",
                help="One-time IT integration costs"
            )
            custom_cultural_cost = st.slider(
                "Cultural Integration ($M)",
                0.0, 150.0, 50.0, 10.0,
                key="syn_cultural",
                help="Training, change management costs"
            )
            custom_restructuring = st.slider(
                "Restructuring ($M)",
                0.0, 300.0, 150.0, 25.0,
                key="syn_restructuring",
                help="Severance, facility consolidation"
            )

        # Build custom synergy assumptions
        standard_ramp = SynergyRampSchedule(schedule={
            2024: 0.0, 2025: 0.20, 2026: 0.50, 2027: 0.80, 2028: 1.0,
            2029: 1.0, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0
        })
        technology_ramp = SynergyRampSchedule(schedule={
            2024: 0.0, 2025: 0.0, 2026: 0.20, 2027: 0.50, 2028: 0.80,
            2029: 1.0, 2030: 1.0, 2031: 1.0, 2032: 1.0, 2033: 1.0
        })
        integration_schedule = {2024: 0.40, 2025: 0.40, 2026: 0.20}

        synergies = SynergyAssumptions(
            name="Custom",
            description="User-defined synergy assumptions",
            operating=OperatingSynergies(
                procurement_savings_annual=custom_procurement,
                procurement_confidence=0.80,
                logistics_savings_annual=custom_logistics,
                logistics_confidence=0.75,
                overhead_savings_annual=custom_overhead,
                overhead_confidence=0.85,
                ramp_schedule=standard_ramp
            ),
            technology=TechnologyTransfer(
                yield_improvement_pct=custom_yield,
                yield_margin_impact=0.008,
                quality_price_premium_pct=custom_quality_premium,
                conversion_cost_reduction_pct=custom_conversion,
                segment_allocation={'Flat-Rolled': 0.50, 'Mini Mill': 0.30, 'USSE': 0.15, 'Tubular': 0.05},
                ramp_schedule=technology_ramp,
                confidence=custom_tech_confidence
            ),
            revenue=RevenueSynergies(
                cross_sell_revenue_annual=custom_crosssell,
                cross_sell_margin=0.15,
                cross_sell_confidence=0.60,
                product_mix_revenue_uplift=custom_productmix,
                product_mix_margin=0.20,
                product_mix_confidence=0.65,
                ramp_schedule=standard_ramp
            ),
            integration=IntegrationCosts(
                it_integration_cost=custom_it_cost,
                it_spend_schedule=integration_schedule,
                cultural_integration_cost=custom_cultural_cost,
                cultural_spend_schedule=integration_schedule,
                restructuring_cost=custom_restructuring,
                restructuring_spend_schedule=integration_schedule
            ),
            enabled=True,
            overall_execution_factor=1.0
        )

    # ==========================================================================
    # MODEL CONFIGURATION (advanced settings, collapsed by default)
    # ==========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("Model Configuration")

    # --- Interest Rate Parity ---
    with st.sidebar.expander("Interest Rate Parity", expanded=False):
        if st.button("↺ Reset IRP to Default", key="reset_irp", help=f"Reset IRP parameters to {selected_scenario_name} defaults"):
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
            st.session_state.override_irp = False
            if 'manual_nippon_usd_wacc' in st.session_state:
                del st.session_state.manual_nippon_usd_wacc
            st.session_state.reset_section = None

        us_10yr = st.slider("US 10-Year Treasury", 1.0, 7.0, st.session_state.get('us_10yr', preset.us_10yr * 100), 0.25, format="%.2f%%",
                                     key="us_10yr",
                                     help="Current US government bond yield. Used to calculate interest rate differential with Japan.") / 100
        japan_10yr = st.slider("Japan 10-Year JGB", -0.5, 5.0, st.session_state.get('japan_10yr', preset.japan_10yr * 100), 0.25, format="%.2f%%",
                                        key="japan_10yr",
                                        help="Japanese Government Bond yield. Nippon's cost of capital rises with this rate.") / 100

        # IRP Override Toggle
        override_irp = st.checkbox(
            "Override IRP",
            value=st.session_state.get('override_irp', False),
            key="override_irp",
            help="Override Interest Rate Parity formula and manually set Nippon's USD WACC."
        )

        # Manual USD WACC slider (only shown when override is enabled)
        manual_nippon_usd_wacc = None
        if override_irp:
            # Calculate IRP-implied WACC for comparison
            nippon_cost_of_equity_temp = japan_10yr + st.session_state.get('n_erp', preset.nippon_equity_risk_premium * 100) / 100
            nippon_cost_of_debt_temp = japan_10yr + st.session_state.get('n_cs', preset.nippon_credit_spread * 100) / 100
            debt_ratio_temp = st.session_state.get('n_dr', preset.nippon_debt_ratio * 100) / 100
            tax_rate_temp = st.session_state.get('n_tr', preset.nippon_tax_rate * 100) / 100
            jpy_wacc_temp = (
                (1 - debt_ratio_temp) * nippon_cost_of_equity_temp +
                debt_ratio_temp * nippon_cost_of_debt_temp * (1 - tax_rate_temp)
            )
            irp_implied_usd_wacc = (1 + jpy_wacc_temp) * (1 + us_10yr) / (1 + japan_10yr) - 1

            st.info(f"IRP-Implied USD WACC: **{irp_implied_usd_wacc*100:.2f}%**")

            manual_nippon_usd_wacc = st.slider(
                "Manual Nippon USD WACC",
                5.0, 12.0,
                st.session_state.get('manual_nippon_usd_wacc', irp_implied_usd_wacc * 100),
                0.1,
                format="%.1f%%",
                key="manual_nippon_usd_wacc",
                help="Manually specified USD discount rate for Nippon. Higher = lower valuation to Nippon."
            ) / 100

            delta = (manual_nippon_usd_wacc - irp_implied_usd_wacc) * 100
            if abs(delta) > 0.05:
                delta_direction = "Higher" if delta > 0 else "Lower"
                st.caption(f"{delta_direction} by {abs(delta):.2f}% vs IRP")

        st.markdown("---")
        st.markdown("**Nippon WACC Components**")
        nippon_erp = st.slider("Equity Risk Premium", 2.5, 7.0, st.session_state.get('n_erp', preset.nippon_equity_risk_premium * 100), 0.25, format="%.2f%%", key="n_erp",
                                help="Premium over JGB rate for equity. Cost of Equity = JGB + This Premium.") / 100
        nippon_cs = st.slider("Credit Spread", 0.25, 3.0, st.session_state.get('n_cs', preset.nippon_credit_spread * 100), 0.25, format="%.2f%%", key="n_cs",
                                help="Spread over JGB rate for debt. Cost of Debt = JGB + This Spread.") / 100
        nippon_debt_ratio = st.slider("Debt Ratio", 10.0, 60.0, st.session_state.get('n_dr', preset.nippon_debt_ratio * 100), 5.0, format="%.0f%%", key="n_dr",
                                       help="Nippon's debt as percentage of total capital. Affects weighted average.") / 100
        nippon_tax_rate = st.slider("Japan Tax Rate", 25.0, 35.0, st.session_state.get('n_tr', preset.nippon_tax_rate * 100), 1.0, format="%.0f%%", key="n_tr",
                                     help="Japan corporate tax rate. Interest is tax-deductible, reducing effective cost of debt.") / 100

    # --- Bloomberg Market Data ---
    with st.sidebar.expander("Bloomberg Market Data", expanded=False):
        # Initialize session state for current price comparison
        if 'show_current_prices' not in st.session_state:
            st.session_state.show_current_prices = False

        if BLOOMBERG_DETAILS_AVAILABLE:
            try:
                service = get_bloomberg_service()
                status = service.get_status()

                # Status indicator
                overall_status = status.get('overall_status', 'unavailable')
                if overall_status in ['fresh', 'stale']:
                    st.success("Using Bloomberg 2023 Annual Avg Prices")
                else:
                    st.warning("Bloomberg data unavailable - using fallbacks")

                # Analysis effective date
                analysis_date = service.get_analysis_effective_date()
                if analysis_date:
                    st.caption(f"Analysis effective date: {analysis_date.strftime('%Y-%m-%d')}")

                # Refresh button
                if st.button("Refresh Data", key="bloomberg_refresh", help="Reload Bloomberg data from disk"):
                    service.refresh()
                    st.rerun()

                # Toggle to show current market prices comparison
                show_current = st.checkbox(
                    "Compare to Current Prices",
                    value=st.session_state.show_current_prices,
                    key="show_current_prices",
                    help="Show how current market prices compare to 2023 baseline"
                )

                # Price comparison table
                if show_current:
                    st.caption("Current Market vs 2023 Baseline:")
                    price_comparisons = get_price_comparison_table(compare_to_current=True)
                    for pc in price_comparisons:
                        delta_str = f"+{pc.percent_change:.1f}%" if pc.percent_change > 0 else f"{pc.percent_change:.1f}%"
                        color = "green" if pc.percent_change > 0 else "red" if pc.percent_change < 0 else "gray"
                        st.markdown(f"**{pc.benchmark}**: ${pc.current_price:,.0f} (:{color}[{delta_str}])")

            except Exception as e:
                st.error(f"Bloomberg error: {str(e)[:50]}")
        else:
            st.info("Bloomberg integration not available")
            st.caption("Using hardcoded fallback prices")

    # --- Scenario Calibration Mode ---
    if SCENARIO_CALIBRATION_AVAILABLE and ScenarioCalibrationMode is not None:
        with st.sidebar.expander("Scenario Calibration", expanded=False):
            st.caption("Controls how price scenario factors are calculated")

            # Initialize session state for calibration mode
            if 'calibration_mode' not in st.session_state:
                st.session_state.calibration_mode = 'bloomberg'

            # Mode selector
            calibration_mode = st.radio(
                "Price Scenario Mode",
                options=["bloomberg", "hybrid", "fixed"],
                format_func=lambda x: {
                    "fixed": "Option A: Fixed (±15%)",
                    "bloomberg": "Option B: Full Bloomberg",
                    "hybrid": "Option C: Hybrid (Conservative)",
                }[x],
                index=["bloomberg", "hybrid", "fixed"].index(st.session_state.calibration_mode),
                key="calibration_mode_radio",
                help="""
**Fixed**: Hardcoded symmetric factors (simple, stable)
**Bloomberg**: Full percentile-based from historical data (data-driven)
**Hybrid**: Bloomberg downside, capped upside (conservative for boards)
"""
            )

            # Update session state
            st.session_state.calibration_mode = calibration_mode

            # Show mode description
            if get_mode_description:
                mode_enum = ScenarioCalibrationMode(calibration_mode)
                st.info(get_mode_description(mode_enum))

            # Show current mode's factors
            if st.checkbox("Show scenario factors", value=False, key="show_calibration_factors"):
                if get_all_scenarios_for_mode:
                    mode_enum = ScenarioCalibrationMode(calibration_mode)
                    factors = get_all_scenarios_for_mode(mode_enum)
                    st.caption("Price factors by scenario:")
                    for name, f in factors.items():
                        st.markdown(f"**{name}**: HRC={f.hrc_us:.0%}, OCTG={f.octg:.0%}")

            st.markdown("---")

            # Probability Distribution Mode
            st.subheader("Probability Weights")
            st.caption("Controls scenario weights for probability-weighted valuation")

            # Initialize session state for probability mode
            if 'probability_mode' not in st.session_state:
                st.session_state.probability_mode = 'bloomberg'

            # Mode selector
            probability_mode = st.radio(
                "Probability Distribution",
                options=["bloomberg", "fixed"],
                format_func=lambda x: {
                    "fixed": "Fixed (Symmetric)",
                    "bloomberg": "Bloomberg (Historical)",
                }[x],
                index=["bloomberg", "fixed"].index(st.session_state.probability_mode),
                key="probability_mode_radio",
                help="""
**Fixed**: Traditional symmetric distribution centered on base case.

**Bloomberg**: Based on historical percentile frequency from steel price data.
- Gives more weight to base case (40% vs 35%)
- Mid-cycle conditions (P30-P70) occur most frequently historically
- 2023 was an elevated year (~P75), so downside scenarios are data-driven
"""
            )

            # Update session state
            st.session_state.probability_mode = probability_mode

            # Show probability mode description
            try:
                from price_volume_model import ProbabilityDistributionMode, get_probability_distribution_description, get_probability_weights
                if ProbabilityDistributionMode and get_probability_distribution_description:
                    mode_enum = ProbabilityDistributionMode(probability_mode)
                    st.info(get_probability_distribution_description(mode_enum))

                # Show probability weights
                if st.checkbox("Show probability weights", value=False, key="show_probability_weights"):
                    if get_probability_weights:
                        weights = get_probability_weights(mode_enum)
                        st.caption("Scenario probabilities (sum to 100%):")
                        for name, prob in weights.items():
                            st.markdown(f"**{name.replace('_', ' ').title()}**: {prob:.0%}")
                        # Show key insight for Bloomberg mode
                        if probability_mode == 'bloomberg':
                            st.caption("*Bloomberg mode reflects that mid-cycle conditions are most common historically.*")
            except (ImportError, AttributeError):
                pass
    else:
        # If calibration not available, set defaults
        if 'calibration_mode' not in st.session_state:
            st.session_state.calibration_mode = None
        if 'probability_mode' not in st.session_state:
            st.session_state.probability_mode = None

    # Build the custom scenario
    price_scenario = SteelPriceScenario(
        name="Custom" if selected_scenario_type == ScenarioType.CUSTOM else preset.price_scenario.name,
        description="User-defined steel price assumptions",
        hrc_us_factor=hrc_factor,
        crc_us_factor=hrc_factor,  # Same as HRC for simplicity
        coated_us_factor=hrc_factor,
        hrc_eu_factor=eu_factor,
        octg_factor=octg_factor,
        annual_price_growth=annual_price_growth,
        tariff_rate=tariff_rate,
        eur_usd_rate=eur_usd_rate,
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
        override_irp=override_irp,
        manual_nippon_usd_wacc=manual_nippon_usd_wacc,
        include_projects=include_projects,
        synergies=synergies,
        use_verified_wacc=use_verified_wacc
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
# TAB RENDER FUNCTIONS
# =============================================================================

def render_tab_executive(ctx):
    """Tab 1: Executive Decision - Deal verdict, risk matrix, fiduciary checklist."""
    scenario = ctx['scenario']
    val_uss = ctx['val_uss']
    val_nippon = ctx['val_nippon']
    uss_standalone = ctx['uss_standalone']
    nippon_value = ctx['nippon_value']
    offer_price = ctx['offer_price']
    pe_max_price = ctx['pe_max_price']
    offer_vs_standalone = ctx['offer_vs_standalone']
    offer_vs_nippon_value = ctx['offer_vs_nippon_value']
    uss_shareholder_verdict = ctx['uss_shareholder_verdict']
    uss_board_verdict = ctx['uss_board_verdict']
    nippon_verdict = ctx['nippon_verdict']
    wacc_advantage = ctx['wacc_advantage']
    cliffs_nominal = ctx['cliffs_nominal']
    cliffs_risk_adjusted = ctx['cliffs_risk_adjusted']
    implied_ev_ebitda = ctx['implied_ev_ebitda']
    usd_wacc = ctx['usd_wacc']
    ebitda_2024 = ctx['ebitda_2024']

    st.header("Executive Decision Summary", anchor="executive-decision-summary")

    # Deal Verdict Section with prominent styled boxes
    verdict_col1, verdict_col2, verdict_col3 = st.columns(3)

    with verdict_col1:
        if uss_shareholder_verdict == "YES":
            premium_text = f"+${offer_vs_standalone:.2f}"
            st.markdown(f"""
            <div style="background-color:#d4edda; border:3px solid #28a745; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#155724; margin:0 0 12px 0; font-size:1.3em;">USS Shareholders: VOTE YES</h2>
                <p style="color:#155724; font-size:1.1em; margin:0 0 12px 0;">
                    The $55 offer is <strong>{premium_text}/share above</strong> standalone value.
                </p>
                <p style="color:#495057; font-size:0.85em; margin:0; font-style:italic;">
                    No alternative bidder can match this price. PE caps at ~$40, Cleveland-Cliffs nominal $54 but risk-adjusted ~$26.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            diff_text = f"${offer_vs_standalone:.2f}"
            st.markdown(f"""
            <div style="background-color:#fff3cd; border:3px solid #ffc107; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#856404; margin:0 0 12px 0; font-size:1.3em;">USS Shareholders: CONDITIONAL</h2>
                <p style="color:#856404; font-size:1.1em; margin:0 0 12px 0;">
                    The $55 offer is <strong>{diff_text}/share vs</strong> standalone value.
                </p>
                <p style="color:#495057; font-size:0.85em; margin:0; font-style:italic;">
                    Standalone value assumes successful execution of capital program and favorable steel prices.
                </p>
            </div>
            """, unsafe_allow_html=True)

    with verdict_col2:
        if uss_board_verdict == "YES":
            st.markdown("""
            <div style="background-color:#d4edda; border:3px solid #28a745; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#155724; margin:0 0 12px 0; font-size:1.3em;">USS Board: RECOMMEND APPROVAL</h2>
                <p style="color:#155724; font-size:1.0em; margin:0 0 8px 0;">Fiduciary duty satisfied:</p>
                <ul style="color:#155724; font-size:0.95em; margin:0 0 8px 0; padding-left:20px;">
                    <li>Market canvass conducted</li>
                    <li>Fairness opinions obtained</li>
                    <li>Premium to all alternatives</li>
                </ul>
                <p style="color:#495057; font-size:0.85em; margin:0; font-style:italic;">
                    No superior alternative exists. Rejecting exposes shareholders to execution and price risk.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color:#fff3cd; border:3px solid #ffc107; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#856404; margin:0 0 12px 0; font-size:1.3em;">USS Board: REVIEW CAREFULLY</h2>
                <p style="color:#856404; font-size:1.1em; margin:0;">
                    Consider negotiating for higher price given current valuation assumptions.
                </p>
            </div>
            """, unsafe_allow_html=True)

    with verdict_col3:
        if nippon_verdict == "YES":
            discount_text = f"${offer_vs_nippon_value:.2f}"
            upside_pct = offer_vs_nippon_value/offer_price*100
            st.markdown(f"""
            <div style="background-color:#d4edda; border:3px solid #28a745; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#155724; margin:0 0 12px 0; font-size:1.3em;">Nippon Steel: PROCEED</h2>
                <p style="color:#155724; font-size:1.1em; margin:0 0 12px 0;">
                    Acquiring at <strong>{discount_text}/share discount</strong> to intrinsic value.
                </p>
                <p style="color:#495057; font-size:0.85em; margin:0; font-style:italic;">
                    WACC advantage ({wacc_advantage:.1f}%) creates {upside_pct:.0f}% upside. Strategic value from #3 global position.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            premium_text = f"${abs(offer_vs_nippon_value):.2f}"
            st.markdown(f"""
            <div style="background-color:#f8d7da; border:3px solid #dc3545; border-radius:10px; padding:24px; margin:8px 0; min-height:220px;">
                <h2 style="color:#721c24; margin:0 0 12px 0; font-size:1.3em;">Nippon Steel: VALUE AT RISK</h2>
                <p style="color:#721c24; font-size:1.1em; margin:0 0 12px 0;">
                    Paying <strong>{premium_text}/share premium</strong> to intrinsic value.
                </p>
                <p style="color:#495057; font-size:0.85em; margin:0; font-style:italic;">
                    Deal destroys value unless synergies materialize or steel prices exceed assumptions.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # Key Numbers Comparison
    with st.expander("Key Numbers at a Glance", expanded=True):
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

    # One-line bottom line - dynamic based on scenario outcomes
    offer_diff = abs(offer_price - uss_standalone)
    nippon_capture = max(0, nippon_value - offer_price)
    nippon_overpay = max(0, offer_price - nippon_value)

    if offer_price > uss_standalone and nippon_value > offer_price:
        # Best case: deal works for everyone
        st.info(f"""
        **Bottom Line:** At current assumptions ({scenario.price_scenario.hrc_us_factor:.0%} steel prices, {scenario.uss_wacc*100:.1f}% WACC),
        the \\$55 offer exceeds USS standalone value (\\${uss_standalone:.2f}) by \\${offer_diff:.2f}/share.
        Nippon's lower cost of capital creates \\${nippon_capture:.2f}/share of additional value beyond the offer price.
        **No alternative buyer can match this offer.**
        """)
    elif offer_price > uss_standalone and nippon_value <= offer_price:
        # USS shareholders win, but Nippon overpays
        st.warning(f"""
        **Bottom Line:** At current assumptions ({scenario.price_scenario.hrc_us_factor:.0%} steel prices, {scenario.uss_wacc*100:.1f}% WACC),
        the \\$55 offer exceeds USS standalone value (\\${uss_standalone:.2f}) by \\${offer_diff:.2f}/share — shareholders benefit.
        However, Nippon's intrinsic value (\\${nippon_value:.2f}) is \\${nippon_overpay:.2f}/share below the offer price, implying value destruction without synergies.
        """)
    elif uss_standalone > offer_price and nippon_value > offer_price:
        # USS standalone worth more, but Nippon still sees value
        st.warning(f"""
        **Bottom Line:** At current assumptions ({scenario.price_scenario.hrc_us_factor:.0%} steel prices, {scenario.uss_wacc*100:.1f}% WACC),
        USS standalone value (\\${uss_standalone:.2f}) exceeds the \\$55 offer by \\${offer_diff:.2f}/share — shareholders may prefer to hold.
        Nippon still sees \\${nippon_capture:.2f}/share of value creation from their WACC advantage.
        """)
    else:
        # Neither side benefits clearly
        st.error(f"""
        **Bottom Line:** At current assumptions ({scenario.price_scenario.hrc_us_factor:.0%} steel prices, {scenario.uss_wacc*100:.1f}% WACC),
        USS standalone value is \\${uss_standalone:.2f}/share and Nippon's intrinsic value is \\${nippon_value:.2f}/share.
        The deal faces challenges under this scenario: Nippon would overpay by \\${nippon_overpay:.2f}/share without synergies.
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
        | **Fairness Opinions** | Obtained | Barclays (\\$39-50) and Goldman Sachs (\\$38-52) DCF ranges |
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


def render_tab_valuation(ctx):
    """Tab 2: Valuation Analysis - DCF, scenarios, football field, capital projects."""
    scenario = ctx['scenario']
    scenario_name = ctx['scenario_name']
    execution_factor = ctx['execution_factor']
    custom_benchmarks = ctx['custom_benchmarks']
    model = ctx['model']
    analysis = ctx['analysis']
    consolidated = ctx['consolidated']
    segment_dfs = ctx['segment_dfs']
    val_uss = ctx['val_uss']
    val_nippon = ctx['val_nippon']
    usd_wacc = ctx['usd_wacc']
    jpy_wacc = ctx['jpy_wacc']
    financing_impact = ctx['financing_impact']
    uss_standalone = ctx['uss_standalone']
    nippon_value = ctx['nippon_value']
    offer_price = ctx['offer_price']
    pe_max_price = ctx['pe_max_price']
    ebitda_2024 = ctx['ebitda_2024']
    wacc_advantage = ctx['wacc_advantage']
    offer_vs_standalone = ctx['offer_vs_standalone']
    offer_vs_nippon_value = ctx['offer_vs_nippon_value']
    cliffs_nominal = ctx['cliffs_nominal']
    cliffs_risk_adjusted = ctx['cliffs_risk_adjusted']

    # Mini table of contents for navigation
    st.markdown(
        "**Sections:** [Valuation Details](#valuation-details) | "
        "[Scenario Comparison](#scenario-comparison) | "
        "[Expected Value](#probability-weighted-value) | "
        "[Football Field](#valuation-football-field) | "
        "[Value Bridge](#value-bridge) | "
        "[Capital Projects](#capital-projects) | "
        "[Synergy Analysis](#synergy-analysis) | "
        "[Alternative Buyers](#alternative-buyer-comparison) | "
        "[PE/LBO Analysis](#pe-lbo-comparison)"
    )

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
    # SCENARIO COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("Scenario Comparison", anchor="scenario-comparison")

    # Auto-calculate scenario comparison (cached by scenario hash)
    scenario_hash = ctx['scenario_hash']
    sc_cache_key = f"scenario_comparison_{scenario_hash}"
    if sc_cache_key not in st.session_state:
        st.session_state[sc_cache_key] = compare_scenarios(execution_factor=execution_factor, custom_benchmarks=custom_benchmarks)
    comparison_df = st.session_state[sc_cache_key]

    if comparison_df is not None:

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
    else:
        st.info("Scenario comparison not yet calculated. Click button above to calculate.")

    # =========================================================================
    # PROBABILITY-WEIGHTED VALUATION
    # =========================================================================

    st.markdown("---")
    st.header("Probability-Weighted Expected Value", anchor="probability-weighted-value")
    st.markdown("""
    This analysis weights each scenario by its historical frequency (1990-2023) to calculate
    an **expected value** that reflects the full range of potential outcomes.
    """)

    with st.expander("Understanding Probability Weighting", expanded=False):
        st.markdown("""
        **Why weight by probability?**
        - USS has experienced severe downturns 24% of years historically
        - Using only "base case" or "conservative" scenarios ignores downside risk
        - Expected value = weighted average of all scenarios

        **Probability Weights (based on 34-year history):**
        - Severe Downturn: 25% (2009, 2015, 2020-type events)
        - Downside: 30% (below-average but not crisis)
        - Base Case: 30% (mid-cycle, median performance)
        - Above Average: 10% (2017-18 type strong markets)
        - Optimistic: 5% (sustained favorable markets with growth)

        **Total: 100%**
        """)

    # Auto-calculate probability-weighted valuation (cached by scenario hash)
    pw_cache_key = f"prob_weighted_{scenario_hash}"
    if pw_cache_key not in st.session_state:
        try:
            st.session_state[pw_cache_key] = calculate_probability_weighted_valuation(
                custom_benchmarks=custom_benchmarks,
                calibration_mode=st.session_state.get('calibration_mode'),
                probability_mode=st.session_state.get('probability_mode')
            )
        except Exception as e:
            st.error(f"Error calculating probability-weighted valuation: {str(e)}")
            st.session_state[pw_cache_key] = None
    pw_results = st.session_state[pw_cache_key]

    if pw_results is not None:

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
    - **Blue dotted line** = Current scenario value (based on selected assumptions)
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

    # Lazy-load football field behind button (runs 18 DCF models)
    ff_cache_key = f"football_field_{scenario_hash}_{ff_perspective}"

    if st.button("Generate Football Field", type="primary", key="btn_football_field"):
        # Build football field data
        football_field_data = []

        # Calculate total steps for progress tracking
        calibration_mode = st.session_state.get('calibration_mode')
        probability_mode = st.session_state.get('probability_mode')
        presets = get_scenario_presets(calibration_mode=calibration_mode, probability_mode=probability_mode)
        price_test_count = 5  # Number of price sensitivity tests
        wacc_test_count = 4  # Number of WACC tests
        exit_test_count = 4  # Number of exit multiple tests
        total_steps = len(presets) + price_test_count + wacc_test_count + exit_test_count
        current_step = 0

        # Create progress bar for football field
        progress_bar_ff = st.progress(0, text="Generating football field chart...")

        # 1. Scenario-based ranges (use scenario comparison data)
        scenario_values = []
        for st_type, preset in presets.items():
            current_step += 1
            progress_pct = int((current_step / total_steps) * 100)
            progress_bar_ff.progress(progress_pct, text=f"Calculating DCF scenario: {st_type.name} ({current_step}/{total_steps})")

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
            current_step += 1
            progress_pct = int((current_step / total_steps) * 100)
            progress_bar_ff.progress(progress_pct, text=f"Testing steel price: {pf:.0%} of baseline ({current_step}/{total_steps})")

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
                override_irp=scenario.override_irp,
                manual_nippon_usd_wacc=scenario.manual_nippon_usd_wacc,
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
            current_step += 1
            progress_pct = int((current_step / total_steps) * 100)
            progress_bar_ff.progress(progress_pct, text=f"Testing WACC: {w:.1%} ({current_step}/{total_steps})")

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
            current_step += 1
            progress_pct = int((current_step / total_steps) * 100)
            progress_bar_ff.progress(progress_pct, text=f"Testing exit multiple: {em:.1f}x EBITDA ({current_step}/{total_steps})")

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
                override_irp=scenario.override_irp,
                manual_nippon_usd_wacc=scenario.manual_nippon_usd_wacc,
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
            'Description': 'Barclays ($39-50) & Goldman ($38-52) DCF ranges from Dec 2023 proxy filing'
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

        current_desc = f'Your selection: {scenario.price_scenario.hrc_us_factor:.0%} prices, {scenario.uss_wacc*100:.1f}% WACC, {len(scenario.include_projects)} projects'
        current_low = max(0, current_value - 2)
        current_high = max(0, current_value + 2)
        football_field_data.append({
            'Method': f'Current Scenario',
            'Low': current_low,
            'High': current_high,
            'Description': current_desc
        })

        ff_df = pd.DataFrame(football_field_data)
        ff_df['Midpoint'] = (ff_df['Low'] + ff_df['High']) / 2
        ff_df = ff_df.sort_values('Midpoint', ascending=True)

        # Complete progress and clean up
        progress_bar_ff.progress(100, text="Chart complete")
        progress_bar_ff.empty()

        # Cache results
        st.session_state[ff_cache_key] = {
            'ff_df': ff_df,
            'scenario_values': scenario_values,
            'current_value': current_value,
            'timestamp': datetime.now(),
        }

    # Render from cache if available
    if ff_cache_key in st.session_state:
        ff_cache = st.session_state[ff_cache_key]
        ff_df = ff_cache['ff_df']
        scenario_values = ff_cache['scenario_values']
        current_value = ff_cache['current_value']

        fig_ff = go.Figure()

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

        fig_ff.add_vline(x=55, line_dash="dash", line_color="green", line_width=3,
                         annotation_text="$55 Nippon Offer", annotation_position="top")
        fig_ff.add_vline(x=40, line_dash="dot", line_color="red", line_width=2,
                         annotation_text="$40 PE Max (20% IRR)", annotation_position="bottom")
        fig_ff.add_vline(x=current_value, line_dash="dot", line_color="blue", line_width=2,
                         annotation_text=f"Current: ${current_value:.1f}", annotation_position="bottom")

        fig_ff.update_layout(
            title=f"Valuation Football Field ({ff_perspective})",
            xaxis_title="Equity Value per Share ($)",
            yaxis_title="",
            height=550,
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
    else:
        st.info("Click **Generate Football Field** to compute valuation ranges across all methodologies. This runs 18 DCF models and may take 10-15 seconds.")

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
    - **2033 EBITDA**: Steady-state annual EBITDA once project is fully operational (varies with scenario prices)
    - **Included**: Whether this project is included in the current scenario

    *Note: EBITDA values are calculated dynamically using: Capacity × Utilization × Scenario Price × Margin*
    """)

    project_overview = []
    for proj_name, proj in all_projects.items():
        total_capex = sum(proj.capex_schedule.values())
        # Use dynamic EBITDA calculation (responds to scenario prices)
        final_ebitda = get_dynamic_project_ebitda(model, proj, 2033)
        is_included = proj_name in scenario.include_projects

        # Calculate simple NPV at different rates with dynamic EBITDA
        def calc_project_npv(wacc):
            npv = 0
            for year in range(2024, 2034):
                t = year - 2024
                capex = proj.capex_schedule.get(year, 0)
                # Use dynamic EBITDA calculation
                ebitda = get_dynamic_project_ebitda(model, proj, year)
                # Explicit maintenance capex (sustaining capital after construction)
                maint_capex = get_project_maintenance_capex(model, proj, year)
                # FCF = EBITDA × (1 - tax) - Construction CapEx - Maintenance CapEx
                fcf = ebitda * 0.75 - capex - maint_capex  # 25% tax rate
                npv += fcf / ((1 + wacc) ** (t + 0.5))
            # Add terminal value using comparable-based EV/EBITDA multiple
            # Source: WRDS peer analysis - EAF peers 7x, Integrated 5x, Tubular 6x
            tv = final_ebitda * proj.terminal_multiple
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
    # Use dynamic EBITDA calculation
    final_ebitda = get_dynamic_project_ebitda(model, proj, 2033)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"#### {selected_project}")
        # Show dynamic parameters if available
        if proj.nameplate_capacity > 0:
            st.markdown(f"""
            | Attribute | Value |
            |-----------|-------|
            | Segment | {proj.segment} |
            | Total Investment | ${total_capex:,.0f}M |
            | Nameplate Capacity | {proj.nameplate_capacity:,.0f} kt/year |
            | Base Utilization | {proj.base_utilization*100:.0f}% |
            | EBITDA Margin | {proj.ebitda_margin*100:.0f}% |
            | Steady-State EBITDA | ${final_ebitda:,.0f}M/year |
            | Maintenance CapEx | \\${proj.nameplate_capacity * proj.maintenance_capex_per_ton / 1000:,.0f}M/year (\\${proj.maintenance_capex_per_ton:,.0f}/ton) |
            | Terminal Multiple | {proj.terminal_multiple:.1f}x EV/EBITDA |
            | Payback (Simple) | {total_capex / max(final_ebitda * 0.75 - proj.nameplate_capacity * proj.maintenance_capex_per_ton / 1000, 1):.1f} years |
            | Status | {'**Included**' if selected_project in scenario.include_projects else 'Not included'} |
            """)
        else:
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
        # Cash flow chart with dynamic EBITDA and maintenance capex
        years = list(range(2024, 2034))
        capex_values = [proj.capex_schedule.get(y, 0) for y in years]
        maint_values = [get_project_maintenance_capex(model, proj, y) for y in years]
        # Use dynamic EBITDA calculation for each year
        ebitda_values = [get_dynamic_project_ebitda(model, proj, y) for y in years]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years,
            y=[-c for c in capex_values],  # Negative for outflows
            name='Construction CapEx',
            marker_color='#ff6b6b'
        ))
        fig.add_trace(go.Bar(
            x=years,
            y=[-m for m in maint_values],  # Negative for outflows
            name='Maintenance CapEx',
            marker_color='#ffa07a'  # Lighter red/orange for maintenance
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
        st.caption("*EBITDA varies with scenario price assumptions; Maintenance CapEx = sustaining capital after construction*")

    # NPV sensitivity table
    st.markdown("#### NPV Sensitivity to Discount Rate")
    st.markdown(f"""
    **How to read this table:**
    - **WACC**: Discount rate used (6% = low risk, 13.5% = high risk)
    - **NPV**: Net Present Value of the project (positive = value-creating)
    - **vs CapEx**: NPV as a percentage of total investment (>0% means project creates value)
    - Projects are more attractive at lower WACCs; Nippon's ~7.5% WACC makes projects more valuable than at USS's ~10.9%
    - **Terminal Value**: {proj.terminal_multiple:.1f}x EV/EBITDA (sourced from WRDS peer comparables)
    """)
    wacc_range = [0.06, 0.075, 0.09, 0.105, 0.12, 0.135]
    npv_data = []
    for w in wacc_range:
        npv = 0
        for year in range(2024, 2034):
            t = year - 2024
            capex = proj.capex_schedule.get(year, 0)
            # Use dynamic EBITDA calculation
            ebitda = get_dynamic_project_ebitda(model, proj, year)
            # Explicit maintenance capex
            maint_capex = get_project_maintenance_capex(model, proj, year)
            # FCF = EBITDA × (1 - tax) - Construction CapEx - Maintenance CapEx
            fcf = ebitda * 0.75 - capex - maint_capex  # 25% tax rate
            npv += fcf / ((1 + w) ** (t + 0.5))
        # Terminal value using comparable-based EV/EBITDA multiple
        tv = final_ebitda * proj.terminal_multiple
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

    # =========================================================================
    # SYNERGY ANALYSIS (only show when synergies are enabled)
    # =========================================================================

    synergy_schedule = analysis.get('synergy_schedule')
    synergy_value = analysis.get('synergy_value')

    if synergy_schedule is not None and synergy_value is not None:
        st.markdown("---")
        st.header("Synergy Analysis", anchor="synergy-analysis")

        syn = scenario.synergies
        st.markdown(f"**Synergy Preset:** {syn.name}")
        st.caption(syn.description if syn.description else "")

        # Summary metrics
        syn_col1, syn_col2, syn_col3, syn_col4 = st.columns(4)

        with syn_col1:
            st.metric(
                "Run-Rate Synergies (2033)",
                f"${synergy_value['run_rate_synergies']:,.0f}M",
                "Annual EBITDA at full realization"
            )

        with syn_col2:
            st.metric(
                "10-Year Synergy NPV",
                f"${synergy_value['npv_synergies']:,.0f}M",
                f"@ {usd_wacc*100:.2f}% discount rate"
            )

        with syn_col3:
            st.metric(
                "Total Integration Costs",
                f"${synergy_value['total_integration_costs']:,.0f}M",
                "One-time costs (Y1-Y3)"
            )

        with syn_col4:
            st.metric(
                "Synergy Value per Share",
                f"${synergy_value['synergy_value_per_share']:.2f}",
                "Addition to Nippon value"
            )

        # Synergy breakdown by category
        st.markdown("### Synergy Sources at Run-Rate")

        source_col1, source_col2, source_col3 = st.columns(3)

        with source_col1:
            st.markdown("#### Operating Synergies")
            op = syn.operating
            st.markdown(f"""
            | Category | Annual ($M) | Confidence |
            |----------|------------:|:----------:|
            | Procurement | ${op.procurement_savings_annual:,.0f} | {op.procurement_confidence:.0%} |
            | Logistics | ${op.logistics_savings_annual:,.0f} | {op.logistics_confidence:.0%} |
            | Overhead | ${op.overhead_savings_annual:,.0f} | {op.overhead_confidence:.0%} |
            | **Prob-Weighted** | **${op.get_total_run_rate():,.0f}** | |
            """)

        with source_col2:
            st.markdown("#### Technology Transfer")
            tech = syn.technology
            st.markdown(f"""
            | Metric | Value |
            |--------|------:|
            | Yield Improvement | {tech.yield_improvement_pct*100:.1f}% |
            | Quality Premium | {tech.quality_price_premium_pct*100:.1f}% |
            | Conversion Reduction | {tech.conversion_cost_reduction_pct*100:.1f}% |
            | Confidence | {tech.confidence:.0%} |
            """)

        with source_col3:
            st.markdown("#### Revenue Synergies")
            rev = syn.revenue
            st.markdown(f"""
            | Category | Revenue ($M) | Margin | Conf |
            |----------|-------------:|-------:|-----:|
            | Cross-Sell | ${rev.cross_sell_revenue_annual:,.0f} | {rev.cross_sell_margin:.0%} | {rev.cross_sell_confidence:.0%} |
            | Product Mix | ${rev.product_mix_revenue_uplift:,.0f} | {rev.product_mix_margin:.0%} | {rev.product_mix_confidence:.0%} |
            | **EBITDA** | **${rev.get_run_rate_ebitda():,.0f}** | | |
            """)

        # Synergy ramp chart
        st.markdown("### Synergy Realization by Year")

        # Price overlay option
        hist_prices_syn = load_historical_steel_prices()
        synergy_price_overlay = st.checkbox(
            "Overlay HRC US Price",
            value=False,
            key="synergy_price_overlay",
            help="Show HRC US price trend alongside synergy ramp"
        )

        # Create stacked bar chart
        fig_syn = go.Figure()

        # Add traces for each synergy category
        fig_syn.add_trace(go.Bar(
            name='Operating',
            x=synergy_schedule['Year'],
            y=synergy_schedule['Operating_Synergy'],
            marker_color='#2E86AB'
        ))

        fig_syn.add_trace(go.Bar(
            name='Technology',
            x=synergy_schedule['Year'],
            y=synergy_schedule['Technology_Synergy'],
            marker_color='#A23B72'
        ))

        fig_syn.add_trace(go.Bar(
            name='Revenue',
            x=synergy_schedule['Year'],
            y=synergy_schedule['Revenue_Synergy'],
            marker_color='#F18F01'
        ))

        fig_syn.add_trace(go.Bar(
            name='Integration Costs',
            x=synergy_schedule['Year'],
            y=[-x for x in synergy_schedule['Integration_Cost']],  # Negative for costs
            marker_color='#C73E1D'
        ))

        # Add price overlay if enabled
        if synergy_price_overlay and hist_prices_syn is not None:
            hrc_price_df = hist_prices_syn.get_price_series("HRC US")
            if hrc_price_df is not None:
                # Aggregate price to annual
                annual_hrc = aggregate_prices_by_year(
                    hrc_price_df,
                    int(synergy_schedule['Year'].min()),
                    int(synergy_schedule['Year'].max())
                )

                # Convert to secondary y-axis chart
                from plotly.subplots import make_subplots
                fig_syn_dual = make_subplots(specs=[[{"secondary_y": True}]])

                # Add existing synergy traces to primary y-axis
                for trace in fig_syn.data:
                    fig_syn_dual.add_trace(trace, secondary_y=False)

                # Add HRC price line to secondary y-axis
                fig_syn_dual.add_trace(
                    go.Scatter(
                        x=annual_hrc.index.tolist(),
                        y=annual_hrc.values.tolist(),
                        name='HRC US Price',
                        mode='lines+markers',
                        line=dict(color='#ff6b6b', width=3, dash='dash'),
                        marker=dict(size=8),
                        hovertemplate='%{x}<br>\\$%{y:,.0f}/ton<extra></extra>'
                    ),
                    secondary_y=True
                )

                # Update axes
                fig_syn_dual.update_xaxes(title_text='Year')
                fig_syn_dual.update_yaxes(title_text='EBITDA Impact ($M)', secondary_y=False)
                fig_syn_dual.update_yaxes(title_text='HRC Price ($/ton)', secondary_y=True)

                fig_syn_dual.update_layout(
                    barmode='relative',
                    title='Synergy EBITDA Contribution with HRC Price Overlay',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    height=550,
                    hovermode='x unified'
                )

                st.plotly_chart(fig_syn_dual, use_container_width=True)
            else:
                fig_syn.update_layout(
                    barmode='relative',
                    title='Synergy EBITDA Contribution by Category ($M)',
                    xaxis_title='Year',
                    yaxis_title='EBITDA Impact ($M)',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                    height=400
                )
                st.plotly_chart(fig_syn, use_container_width=True)
        else:
            fig_syn.update_layout(
                barmode='relative',
                title='Synergy EBITDA Contribution by Category ($M)',
                xaxis_title='Year',
                yaxis_title='EBITDA Impact ($M)',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                height=400
            )
            st.plotly_chart(fig_syn, use_container_width=True)

        # Synergy schedule table
        with st.expander("Detailed Synergy Schedule", expanded=False):
            st.dataframe(
                synergy_schedule.style.format({
                    'Operating_Synergy': '${:,.0f}M',
                    'Technology_Synergy': '${:,.0f}M',
                    'Revenue_Synergy': '${:,.0f}M',
                    'Integration_Cost': '${:,.0f}M',
                    'Total_Synergy_EBITDA': '${:,.0f}M',
                    'Cumulative_Synergy': '${:,.0f}M'
                }),
                use_container_width=True
            )

        st.info(f"""
        **Key Insight:** Synergies add **${synergy_value['synergy_value_per_share']:.2f}/share** to Nippon's value.
        The standard ramp schedule achieves 50% realization by Year 3 and full run-rate by Year 5.
        Technology synergies ramp slower (full realization by Year 6) as they require operational changes.
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
    # ALTERNATIVE BUYER COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("Alternative Buyers: Why No One Can Match \\$55", anchor="alternative-buyer-comparison")

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
    # PE LBO vs STRATEGIC BUYER COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("Why PE Can't Pay \\$55: LBO Constraints", anchor="pe-lbo-comparison")

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


def render_tab_risk(ctx):
    """Tab 3: Risk & Sensitivity - Thresholds, Monte Carlo, price sensitivity, WACC."""
    scenario = ctx['scenario']
    execution_factor = ctx['execution_factor']
    custom_benchmarks = ctx['custom_benchmarks']
    model = ctx['model']
    consolidated = ctx['consolidated']
    segment_dfs = ctx['segment_dfs']
    val_uss = ctx['val_uss']
    val_nippon = ctx['val_nippon']
    usd_wacc = ctx['usd_wacc']
    nippon_value = ctx['nippon_value']
    offer_price = ctx['offer_price']

    st.header("What Breaks the Deal? Sensitivity Thresholds", anchor="sensitivity-thresholds")

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

    # WACC SENSITIVITY
    # =========================================================================

    st.markdown("---")
    # =========================================================================
    # MONTE CARLO SIMULATION RESULTS
    # =========================================================================

    mc_data = load_monte_carlo_data()

    if mc_data is not None:
        mc_results, mc_inputs = mc_data
        n_iterations = len(mc_results)

        st.header(f"Monte Carlo Simulation Results ({n_iterations:,} Iterations)", anchor="monte-carlo-results")

        st.markdown(f"""
        Results from **{n_iterations:,} simulations** sampling 26 correlated input variables
        (steel prices, volumes, WACC, margins, tariffs, synergies, FX) from calibrated distributions.
        This replaces the previous correlation analysis which was based on only 3 data points.
        """)

        # =================================================================
        # SUMMARY STATISTICS
        # =================================================================

        st.subheader("Summary Statistics")

        uss_prices = mc_results['uss_share_price']
        nip_prices = mc_results['nippon_share_price']

        mc_col1, mc_col2, mc_col3 = st.columns(3)

        with mc_col1:
            st.markdown("#### USS Standalone")
            st.metric("Mean", f"\\${uss_prices.mean():.2f}")
            st.metric("Median", f"\\${uss_prices.median():.2f}")
            uss_p5 = uss_prices.quantile(0.05)
            uss_p95 = uss_prices.quantile(0.95)
            st.caption(f"P5/P95: \\${uss_p5:.0f} – \\${uss_p95:.0f}")
            pct_below_39 = (uss_prices < 39).mean() * 100
            st.caption(f"P(USS < \\$39): {pct_below_39:.1f}%")

        with mc_col2:
            st.markdown("#### Nippon Perspective")
            st.metric("Mean", f"\\${nip_prices.mean():.2f}")
            st.metric("Median", f"\\${nip_prices.median():.2f}")
            nip_p5 = nip_prices.quantile(0.05)
            nip_p95 = nip_prices.quantile(0.95)
            st.caption(f"P5/P95: \\${nip_p5:.0f} – \\${nip_p95:.0f}")
            pct_above_55 = (nip_prices > 55).mean() * 100
            st.caption(f"P(Nippon > \\$55): {pct_above_55:.1f}%")

        with mc_col3:
            st.markdown("#### Synergy Premium")
            median_premium = nip_prices.median() - uss_prices.median()
            st.metric("Median Premium", f"\\${median_premium:.2f}")
            mean_premium = nip_prices.mean() - uss_prices.mean()
            st.metric("Mean Premium", f"\\${mean_premium:.2f}")
            st.caption(f"P(Nippon > \\$55): {pct_above_55:.1f}%")

        # =================================================================
        # SHARE PRICE DISTRIBUTION (overlaid histograms)
        # =================================================================

        st.subheader("Share Price Distribution")

        fig_dist = go.Figure()

        fig_dist.add_trace(go.Histogram(
            x=uss_prices,
            name='USS Standalone',
            marker_color='rgba(31, 119, 180, 0.6)',
            nbinsx=60,
            hovertemplate='\\$%{x:.0f}<br>Count: %{y}<extra>USS</extra>'
        ))

        fig_dist.add_trace(go.Histogram(
            x=nip_prices,
            name='Nippon Perspective',
            marker_color='rgba(44, 160, 44, 0.6)',
            nbinsx=60,
            hovertemplate='\\$%{x:.0f}<br>Count: %{y}<extra>Nippon</extra>'
        ))

        fig_dist.add_vline(x=55, line_dash="dash", line_color="red", line_width=2,
                           annotation_text="\\$55 Offer", annotation_position="top right")
        fig_dist.add_vline(x=uss_prices.median(), line_dash="dot", line_color='#1f77b4', line_width=1.5,
                           annotation_text=f"USS Median \\${uss_prices.median():.0f}", annotation_position="top left")
        fig_dist.add_vline(x=nip_prices.median(), line_dash="dot", line_color='#2ca02c', line_width=1.5,
                           annotation_text=f"Nippon Median \\${nip_prices.median():.0f}", annotation_position="top right")

        fig_dist.update_layout(
            barmode='overlay',
            xaxis_title='Share Price (\\$/share)',
            yaxis_title='Frequency',
            height=500,
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )

        st.plotly_chart(fig_dist, use_container_width=True)

        st.caption(
            f"USS median \\${uss_prices.median():.0f} vs mean \\${uss_prices.mean():.0f} "
            f"(right-skewed). Nippon median \\${nip_prices.median():.0f} vs mean \\${nip_prices.mean():.0f}. "
            f"The gap reflects WACC advantage + synergies."
        )

        # =================================================================
        # TORNADO SENSITIVITY (top 10 by |correlation| with Nippon price)
        # =================================================================

        st.subheader("Key Value Drivers")

        input_cols = [c for c in mc_inputs.columns if c in MC_VARIABLE_LABELS]
        correlations = {}
        for col in input_cols:
            correlations[col] = mc_inputs[col].corr(nip_prices)

        corr_series = pd.Series(correlations).dropna()
        corr_sorted = corr_series.reindex(corr_series.abs().sort_values(ascending=True).index)
        top_10 = corr_sorted.tail(10)

        fig_tornado = go.Figure()

        colors = ['#c41e3a' if v < 0 else '#00703c' for v in top_10.values]
        labels = [MC_VARIABLE_LABELS.get(c, c) for c in top_10.index]

        fig_tornado.add_trace(go.Bar(
            y=labels,
            x=top_10.values,
            orientation='h',
            marker_color=colors,
            hovertemplate='%{y}: %{x:.3f}<extra></extra>'
        ))

        fig_tornado.update_layout(
            title='Top 10 Drivers: Correlation with Nippon Share Price',
            xaxis_title='Correlation Coefficient',
            yaxis_title='',
            height=450,
            showlegend=False,
            xaxis=dict(range=[-1, 1])
        )

        st.plotly_chart(fig_tornado, use_container_width=True)

        st.caption(
            "Bars show Pearson correlation of each Monte Carlo input with Nippon share price. "
            "Green = positive driver, red = negative. Correlation does not imply causation; "
            "some variables (e.g., WACC) affect valuation mechanically."
        )

        # =================================================================
        # CDF COMPARISON
        # =================================================================

        st.subheader("Cumulative Probability (CDF)")

        fig_cdf = go.Figure()

        uss_sorted = np.sort(uss_prices.values)
        uss_cdf = np.arange(1, len(uss_sorted) + 1) / len(uss_sorted)

        fig_cdf.add_trace(go.Scatter(
            x=uss_sorted, y=uss_cdf,
            name='USS Standalone',
            mode='lines',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='\\$%{x:.0f}<br>P(X < x): %{y:.1%}<extra>USS</extra>'
        ))

        nip_sorted = np.sort(nip_prices.values)
        nip_cdf = np.arange(1, len(nip_sorted) + 1) / len(nip_sorted)

        fig_cdf.add_trace(go.Scatter(
            x=nip_sorted, y=nip_cdf,
            name='Nippon Perspective',
            mode='lines',
            line=dict(color='#2ca02c', width=2),
            hovertemplate='\\$%{x:.0f}<br>P(X < x): %{y:.1%}<extra>Nippon</extra>'
        ))

        pct_below_55_nip = (nip_prices < 55).mean()
        fig_cdf.add_vline(x=55, line_dash="dash", line_color="red", line_width=2)
        fig_cdf.add_annotation(
            x=55, y=pct_below_55_nip,
            text=f"\\$55 offer: {pct_below_55_nip:.0%} below",
            showarrow=True, arrowhead=2,
            ax=80, ay=-30
        )

        fig_cdf.add_shape(type="line", x0=uss_prices.median(), x1=uss_prices.median(),
                          y0=0, y1=0.5, line=dict(color='#1f77b4', width=1, dash='dot'))
        fig_cdf.add_shape(type="line", x0=0, x1=uss_prices.median(),
                          y0=0.5, y1=0.5, line=dict(color='#1f77b4', width=1, dash='dot'))
        fig_cdf.add_shape(type="line", x0=nip_prices.median(), x1=nip_prices.median(),
                          y0=0, y1=0.5, line=dict(color='#2ca02c', width=1, dash='dot'))
        fig_cdf.add_shape(type="line", x0=0, x1=nip_prices.median(),
                          y0=0.5, y1=0.5, line=dict(color='#2ca02c', width=1, dash='dot'))

        fig_cdf.update_layout(
            xaxis_title='Share Price (\\$/share)',
            yaxis_title='Cumulative Probability',
            height=500,
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            yaxis=dict(tickformat='.0%')
        )

        st.plotly_chart(fig_cdf, use_container_width=True)

        st.caption(
            f"Read as: at \\$55, {pct_below_55_nip:.0%} of Nippon simulations fall below the offer price, "
            f"meaning {1 - pct_below_55_nip:.0%} of outcomes support the deal. "
            f"USS median (\\${uss_prices.median():.0f}) is well below Nippon median (\\${nip_prices.median():.0f}), "
            f"confirming the synergy/WACC value gap."
        )

    else:
        st.markdown("---")
        st.header("Monte Carlo Simulation Results", anchor="monte-carlo-results")
        st.warning("""
        **Monte Carlo data not available.**

        Run the Monte Carlo simulation first:
        ```
        python scripts/run_monte_carlo_analysis.py
        ```
        This generates `data/monte_carlo_results.csv` and `data/monte_carlo_inputs.csv`.
        """)


    # =========================================================================
    # STEEL PRICE SENSITIVITY
    # =========================================================================

    st.markdown("---")
    st.header("Steel Price Sensitivity: Impact on Valuation", anchor="steel-price-sensitivity")

    st.markdown("""
    **How to read this section:**
    - Steel prices are the #1 driver of valuation - a 10% price swing changes share value by \\$15-25
    - **Price Factor**: Multiplier applied to 2023 benchmark prices (0.8 = 20% below, 1.2 = 20% above)
    - The chart shows how share value changes as steel prices move up or down
    - Green dashed line = \\$55 Nippon offer price (breakeven around 88% price factor)
    """)

    # Lazy-load price sensitivity behind button (runs 9 DCF models)
    scenario_hash = ctx['scenario_hash']
    sens_cache_key = f"price_sensitivity_{scenario_hash}"

    if st.button("Calculate Price Sensitivity", type="primary", key="btn_price_sens"):
        price_factors = np.arange(0.6, 1.5, 0.1)
        sensitivity_data = []

        for pf in price_factors:
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
                override_irp=scenario.override_irp,
                manual_nippon_usd_wacc=scenario.manual_nippon_usd_wacc,
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

        st.session_state[sens_cache_key] = {
            'sens_df': pd.DataFrame(sensitivity_data),
            'timestamp': datetime.now(),
        }

    # Render from cache if available
    if sens_cache_key in st.session_state:
        sens_cache = st.session_state[sens_cache_key]
        sens_df = sens_cache['sens_df']

        # Build price projection data (lightweight, no DCF)
        price_proj_data = []
        for seg_name, df in segment_dfs.items():
            for _, row in df.iterrows():
                price_proj_data.append({
                    'Year': row['Year'],
                    'Segment': seg_name,
                    'Price': row['Price_per_ton']
                })
        price_proj_df = pd.DataFrame(price_proj_data)

        col1, col2 = st.columns(2)

        with col1:
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
            st.subheader("Price Projections by Segment")
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
    else:
        st.info("Click **Calculate Price Sensitivity** to compute valuation across 9 price scenarios. This may take 5-10 seconds.")

    # ==========================================================================
    # CORRELATION ANALYSIS - FULL WIDTH
    # ==========================================================================

    st.markdown("---")
    # Define all variables to analyze
    try:
        # Variable configuration
        variables_to_analyze = [
            {
                "key": "HRC US",
                "file": "hrc_us_spot.csv",
                "name": "HRC US",
                "full_name": "Hot-Rolled Coil",
                "unit": "$/ton",
                "color": "#ff6b6b",
                "decimals": 0,
                "category": "Steel Prices"
            },
            {
                "key": "CRC US",
                "file": "crc_us_spot.csv",
                "name": "CRC US",
                "full_name": "Cold-Rolled Coil",
                "unit": "$/ton",
                "color": "#ff9f43",
                "decimals": 0,
                "category": "Steel Prices"
            },
            {
                "key": "OCTG US",
                "file": "octg_us_spot.csv",
                "name": "OCTG US",
                "full_name": "Oil Country Tubular",
                "unit": "$/ton",
                "color": "#ee5a6f",
                "decimals": 0,
                "category": "Steel Prices"
            },
            {
                "key": "Scrap PPI",
                "file": "scrap_us_ppi.csv",
                "name": "Scrap PPI",
                "full_name": "Scrap Price Index",
                "unit": "Index",
                "color": "#c44569",
                "decimals": 1,
                "category": "Input Costs"
            },
            {
                "key": "Housing Starts",
                "file": "housing_starts.csv",
                "name": "Housing Starts",
                "full_name": "US Housing Starts",
                "unit": "Thousands",
                "color": "#0fb9b1",
                "decimals": 0,
                "category": "End Markets"
            },
            {
                "key": "Auto Production",
                "file": "auto_production.csv",
                "name": "Auto Production",
                "full_name": "US Auto Production",
                "unit": "Thousands",
                "color": "#20bf6b",
                "decimals": 1,
                "category": "End Markets"
            },
            {
                "key": "ISM PMI",
                "file": "ism_pmi.csv",
                "name": "ISM PMI",
                "full_name": "Manufacturing Activity",
                "unit": "Index",
                "color": "#4b7bec",
                "decimals": 1,
                "category": "Economic Indicators"
            },
            {
                "key": "Rig Count",
                "file": "rig_count.csv",
                "name": "US Rig Count",
                "full_name": "Oil & Gas Drilling",
                "unit": "Count",
                "color": "#a55eea",
                "decimals": 0,
                "category": "Economic Indicators"
            }
        ]

        # Load USS stock data once
        stock_path = Path(__file__).parent / "market-data" / "exports" / "processed" / "stock_uss.csv"
        stock_df = pd.read_csv(stock_path)
        stock_df['date'] = pd.to_datetime(stock_df['date'])
        stock_df['year'] = stock_df['date'].dt.year
        stock_annual = stock_df.groupby('year')['value'].mean()

        # Calculate correlations for all variables
        correlation_results = []

        for var in variables_to_analyze:
            try:
                var_path = Path(__file__).parent / "market-data" / "exports" / "processed" / var["file"]
                var_df = pd.read_csv(var_path)
                var_df['date'] = pd.to_datetime(var_df['date'])
                var_df['year'] = var_df['date'].dt.year
                var_annual = var_df.groupby('year')['value'].mean()

                # Find common years
                common_years = sorted(set(stock_annual.index) & set(var_annual.index))

                if len(common_years) >= 3:
                    # Calculate correlation
                    corr_df = pd.DataFrame({
                        'var': var_annual[common_years],
                        'stock': stock_annual[common_years]
                    })
                    correlation = corr_df['var'].corr(corr_df['stock'])

                    correlation_results.append({
                        'variable': var["key"],
                        'full_name': var["full_name"],
                        'category': var["category"],
                        'correlation': correlation,
                        'years': len(common_years),
                        'period': f"{min(common_years)}-{max(common_years)}",
                        'var_annual': var_annual,
                        'common_years': common_years,
                        'config': var
                    })
            except FileNotFoundError:
                continue

        # Sort by absolute correlation (strongest first)
        correlation_results.sort(key=lambda x: abs(x['correlation']), reverse=True)

        # ================================================================
        # CORRELATION SUMMARY TABLE
        # ================================================================

        st.subheader("Correlation Summary Table")

        # Create summary dataframe
        summary_data = []
        for result in correlation_results:
            corr = result['correlation']
            if abs(corr) > 0.7:
                strength = "🟢 Strong"
            elif abs(corr) > 0.4:
                strength = "🟡 Moderate"
            else:
                strength = "🔴 Weak"

            summary_data.append({
                'Variable': result['variable'],
                'Description': result['full_name'],
                'Category': result['category'],
                'Correlation': f"{corr:.3f}",
                'Strength': strength,
                'Years': result['years'],
                'Period': result['period']
            })

        summary_df = pd.DataFrame(summary_data)

        # Display with color coding
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            height=350
        )

        st.markdown("""
        **Interpretation:**
        - **Strong (|r| > 0.7)**: Variable moves closely with USS stock price
        - **Moderate (0.4 < |r| < 0.7)**: Noticeable relationship
        - **Weak (|r| < 0.4)**: Limited predictive power
        """)

        st.markdown("---")

        # ================================================================
        # INDIVIDUAL CORRELATION CHARTS
        # ================================================================

        st.subheader("Detailed Correlation Charts (Sorted by Strength)")

        # Display charts in 2-column layout
        for idx, result in enumerate(correlation_results):
            config = result['config']
            var_annual = result['var_annual']
            common_years = result['common_years']
            correlation = result['correlation']

            # Create new row every 2 charts
            if idx % 2 == 0:
                col1, col2 = st.columns(2)

            with (col1 if idx % 2 == 0 else col2):
                # Create dual-axis chart
                from plotly.subplots import make_subplots
                fig = make_subplots(specs=[[{"secondary_y": True}]])

                # Add variable (left axis)
                fig.add_trace(
                    go.Scatter(
                        x=common_years,
                        y=var_annual[common_years].values,
                        name=config["name"],
                        mode='lines+markers',
                        line=dict(color=config["color"], width=2),
                        marker=dict(size=4),
                        hovertemplate=f'%{{x}}<br>{config["name"]}: %{{y:.{config["decimals"]}f}} {config["unit"]}<extra></extra>'
                    ),
                    secondary_y=False
                )

                # Add USS stock price (right axis)
                fig.add_trace(
                    go.Scatter(
                        x=common_years,
                        y=stock_annual[common_years].values,
                        name="USS Stock",
                        mode='lines+markers',
                        line=dict(color='#1f77b4', width=2, dash='dot'),
                        marker=dict(size=4, symbol='diamond'),
                        hovertemplate='%{x}<br>$%{y:.2f}<extra></extra>'
                    ),
                    secondary_y=True
                )

                # Configure axes
                fig.update_xaxes(title_text="Year")
                fig.update_yaxes(title_text=f'{config["name"]} ({config["unit"]})', secondary_y=False)
                fig.update_yaxes(title_text="USS Stock ($)", secondary_y=True)

                # Determine strength for title
                if abs(correlation) > 0.7:
                    strength_emoji = "🟢"
                elif abs(correlation) > 0.4:
                    strength_emoji = "🟡"
                else:
                    strength_emoji = "🔴"

                fig.update_layout(
                    title=f'{strength_emoji} {config["name"]} • r={correlation:.3f}',
                    hovermode='x unified',
                    height=400,
                    showlegend=True,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01,
                        bgcolor="rgba(255,255,255,0.8)",
                        font=dict(size=10)
                    ),
                    margin=dict(t=40, b=40, l=40, r=40)
                )

                st.plotly_chart(fig, use_container_width=True)

    except FileNotFoundError as e:
        st.error(f"Historical stock data not available: {e}")
    except Exception as e:
        st.error(f"Error in correlation analysis: {e}")
        import traceback
        st.code(traceback.format_exc())


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

    # Auto-calculate WACC sensitivity
    wacc_range = np.arange(0.05, 0.14, 0.005)
    wacc_sensitivity_data = []

    for w in wacc_range:
        val = model.calculate_dcf(consolidated, w)
        wacc_sensitivity_data.append({
            'WACC': w * 100,
            'Equity Value': val['share_price']
        })

    wacc_sens_df = pd.DataFrame(wacc_sensitivity_data)

    # Display results
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
    # COVENANT ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.header("Covenant Analysis", anchor="covenant-analysis")

    try:
        covenant_df = model.calculate_covenant_ratios(consolidated)
        st.markdown("""
        **Credit covenant ratios** based on projected financials. Red cells indicate potential covenant breaches.
        Typical covenants: Debt/EBITDA < 4.0x, Interest Coverage (EBITDA/Interest) > 2.5x.
        """)

        # Format for display
        display_cov = covenant_df[['Year', 'EBITDA', 'Debt', 'Net_Debt', 'Debt_to_EBITDA',
                                    'Net_Debt_to_EBITDA', 'Interest_Coverage']].copy()
        display_cov.columns = ['Year', 'EBITDA ($M)', 'Debt ($M)', 'Net Debt ($M)',
                                'Debt/EBITDA', 'Net Debt/EBITDA', 'Interest Coverage']

        # Check for any breaches
        has_leverage_breach = covenant_df['Leverage_Breach'].any()
        has_coverage_breach = covenant_df['Coverage_Breach'].any()

        if has_leverage_breach or has_coverage_breach:
            breach_years = covenant_df[covenant_df['Leverage_Breach'] | covenant_df['Coverage_Breach']]['Year'].tolist()
            st.warning(f"Covenant breach risk in years: {', '.join(str(y) for y in breach_years)}")
        else:
            st.success("No covenant breaches projected under this scenario.")

        st.dataframe(display_cov.set_index('Year'), use_container_width=True)
    except Exception as e:
        st.info(f"Covenant analysis unavailable: {e}")


def render_tab_strategic(ctx):
    """Tab 4: Strategic Context - USS predicament, NSA, peer benchmarking."""
    scenario = ctx['scenario']
    val_uss = ctx['val_uss']
    val_nippon = ctx['val_nippon']
    ebitda_2024 = ctx['ebitda_2024']
    consolidated = ctx['consolidated']
    offer_price = ctx['offer_price']

    st.header("Without the Deal: Why USS Needs a Buyer", anchor="without-the-deal")

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
    # PEER COMPANY BENCHMARKING
    # =========================================================================

    st.markdown("---")
    st.header("Peer Company Benchmarking", anchor="peer-benchmarking")

    st.caption("📅 **Data as of December 31, 2023** (Capital IQ comps, SEC 10-K/20-F filings)")

    st.markdown("""
    **How to read this section:**
    - Compare USS financial and operational metrics against peer steel companies
    - Valuation multiples show how market values comparable companies
    - USS percentile ranking indicates competitive positioning
    """)

    # Import benchmark data with error handling
    try:
        from scripts.benchmark_data import BenchmarkData
        benchmark = BenchmarkData()
        benchmark_available = True
    except Exception as e:
        benchmark_available = False
        st.warning(f"Benchmark data not available: {e}")

    if benchmark_available:
        # Subsection A: Valuation Multiples Comparison
        st.subheader("Valuation Multiples")

        mult_col1, mult_col2 = st.columns(2)

        with mult_col1:
            # Get peer multiples
            multiples = benchmark.get_peer_multiples()
            if multiples:
                # Create comparison data for chart
                mult_data = []
                for name, stats in multiples.items():
                    mult_data.append({
                        'Metric': name.replace('_', '/').upper(),
                        'Min': stats.min,
                        'Q1': stats.q1,
                        'Median': stats.median,
                        'Q3': stats.q3,
                        'Max': stats.max
                    })

                if mult_data:
                    mult_df = pd.DataFrame(mult_data)
                    # Create grouped bar chart
                    fig_mult = go.Figure()
                    fig_mult.add_trace(go.Bar(
                        name='Q1 (25th)',
                        x=mult_df['Metric'],
                        y=mult_df['Q1'],
                        marker_color='#636EFA'
                    ))
                    fig_mult.add_trace(go.Bar(
                        name='Median',
                        x=mult_df['Metric'],
                        y=mult_df['Median'],
                        marker_color='#EF553B'
                    ))
                    fig_mult.add_trace(go.Bar(
                        name='Q3 (75th)',
                        x=mult_df['Metric'],
                        y=mult_df['Q3'],
                        marker_color='#00CC96'
                    ))
                    fig_mult.update_layout(
                        title="Peer Valuation Multiple Distribution",
                        barmode='group',
                        yaxis_title="Multiple",
                        height=350
                    )
                    st.plotly_chart(fig_mult, use_container_width=True)
            else:
                st.info("Peer multiple data not available")

        with mult_col2:
            # Exit multiple guidance
            exit_range = benchmark.get_exit_multiple_range()
            st.metric("Peer Median TEV/EBITDA", f"{exit_range['base']:.1f}x")
            st.metric("Peer Q1-Q3 Range", f"{exit_range['low']:.1f}x - {exit_range['high']:.1f}x")
            st.info(f"Model uses {scenario.exit_multiple:.1f}x exit multiple")

            # Show if using benchmark multiples
            if scenario.use_benchmark_multiples:
                st.success("Benchmark-driven exit multiples enabled")
                if 'exit_multiple_used' in val_uss:
                    st.metric("Effective Exit Multiple", f"{val_uss['exit_multiple_used']:.2f}x")

        # Subsection B: Margin & Operational Comparison
        st.subheader("Operating Metrics Comparison")

        try:
            # Get USS metrics
            uss_metrics = benchmark.get_uss_metrics()
            peer_summary = benchmark.get_peer_summary()

            # Load steel operational metrics (capacity, shipments, utilization)
            steel_ops = {}
            try:
                steel_ops_df = pd.read_csv('data/extracted_steel_metrics.csv')
                for _, row in steel_ops_df.iterrows():
                    ticker = row.get('Ticker', '')
                    if ticker:
                        steel_ops[ticker] = {
                            'capacity': row.get('Capacity_Mtons'),
                            'shipments': row.get('Shipments_Mtons'),
                            'utilization': row.get('Utilization_Pct'),
                            'revenue_usd_m': row.get('Revenue_USD_M'),
                            'ebitda_usd_m': row.get('EBITDA_USD_M'),
                        }
            except Exception:
                pass  # Steel ops data not available

            # Build comparison table
            comparison_data = []

            # USS row
            uss_revenue = uss_metrics.get('revenue', 0)
            uss_margin = uss_metrics.get('ebitda_margin', 0)
            comparison_data.append({
                'Company': 'United States Steel (X)',
                'Revenue ($B)': uss_revenue/1000 if uss_revenue else None,
                'EBITDA Margin %': uss_margin*100 if uss_margin else None,
                'Capacity (Mt)': uss_metrics.get('capacity_mtons'),
                'Shipments (Mt)': uss_metrics.get('shipments_mtons'),
                'Utilization %': 66.0,  # USS 2023 utilization
            })

            # Add peer data from summary, merged with steel ops
            seen_tickers = set(['X'])  # Track tickers to avoid duplicates
            if not peer_summary.empty:
                for _, row in peer_summary.head(15).iterrows():
                    company_name = row.get('company', '')
                    # Extract ticker from company name - handle various formats
                    ticker = None
                    company_upper = company_name.upper()

                    # Direct ticker matches
                    for t in ['NUE', 'CLF', 'STLD', 'CMC', 'ZEUS', 'BSL', 'TX']:
                        if f":{t})" in company_upper or f"({t})" in company_upper:
                            ticker = t
                            break

                    # Special cases for foreign exchanges
                    if ticker is None:
                        if 'ARCELORMITTAL' in company_upper or 'ENXTAM:MT' in company_upper:
                            ticker = 'MT'
                        elif 'POSCO' in company_upper or 'KOSE:' in company_upper:
                            ticker = 'PKX'
                        elif 'NIPPON STEEL' in company_upper or 'TSE:5401' in company_upper:
                            ticker = 'NPSCY'
                        elif 'GERDAU' in company_upper or 'BOVESPA:' in company_upper:
                            ticker = 'GGB'

                    # Skip if no ticker found or already seen
                    if ticker is None or ticker in seen_tickers:
                        continue
                    seen_tickers.add(ticker)

                    rev = row.get('LTM Total Revenue ', 0)
                    ebitda = row.get('LTM EBITDA ', 0)
                    margin = ebitda / rev if rev and rev > 0 else 0

                    # Get steel operational metrics for this company
                    ops = steel_ops.get(ticker, {})
                    capacity = ops.get('capacity')
                    shipments = ops.get('shipments')
                    utilization = ops.get('utilization')

                    comparison_data.append({
                        'Company': company_name[:40] + '...' if len(company_name) > 40 else company_name,
                        'Revenue ($B)': rev/1000 if rev else None,
                        'EBITDA Margin %': margin*100 if margin else None,
                        'Capacity (Mt)': capacity if pd.notna(capacity) else None,
                        'Shipments (Mt)': shipments if pd.notna(shipments) else None,
                        'Utilization %': utilization if pd.notna(utilization) else None,
                    })

            # Note: seen_tickers is already populated from the loop above
            # Only add companies from steel_ops that weren't matched in Capital IQ data
            # (This handles cases where a company has operational data but no financial data)
            try:
                for _, row in steel_ops_df.iterrows():
                    ticker = row.get('Ticker', '')
                    # Skip if already added, if it's a distributor, or if no capacity data
                    if ticker and ticker not in seen_tickers and ticker != 'ZEUS':
                        capacity = row.get('Capacity_Mtons')
                        if pd.notna(capacity):
                            shipments = row.get('Shipments_Mtons')
                            utilization = row.get('Utilization_Pct')
                            rev_m = row.get('Revenue_USD_M')
                            ebitda_m = row.get('EBITDA_USD_M')
                            margin = (ebitda_m / rev_m * 100) if pd.notna(ebitda_m) and pd.notna(rev_m) and rev_m > 0 else None
                            comparison_data.append({
                                'Company': row.get('Company', ticker),
                                'Revenue ($B)': rev_m / 1000 if pd.notna(rev_m) else None,
                                'EBITDA Margin %': margin,
                                'Capacity (Mt)': capacity if pd.notna(capacity) else None,
                                'Shipments (Mt)': shipments if pd.notna(shipments) else None,
                                'Utilization %': utilization if pd.notna(utilization) else None,
                            })
                            seen_tickers.add(ticker)
            except Exception:
                pass

            # Display as table with proper numeric formatting
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Company': st.column_config.TextColumn('Company', width='medium'),
                    'Revenue ($B)': st.column_config.NumberColumn('Revenue ($B)', format='$%.1f'),
                    'EBITDA Margin %': st.column_config.NumberColumn('EBITDA Margin', format='%.1f%%'),
                    'Capacity (Mt)': st.column_config.NumberColumn('Capacity (Mt)', format='%.1f'),
                    'Shipments (Mt)': st.column_config.NumberColumn('Shipments (Mt)', format='%.1f'),
                    'Utilization %': st.column_config.NumberColumn('Utilization', format='%.0f%%'),
                }
            )

        except Exception as e:
            st.warning(f"Could not load peer comparison: {e}")

        # Subsection B2: Financial Health & Returns Comparison
        st.subheader("Financial Health & Returns")

        try:
            comps = benchmark._get_comps_data()

            fin_health_col1, fin_health_col2 = st.columns(2)

            with fin_health_col1:
                # Leverage & Credit metrics from operating_statistics and financial_data
                leverage_data = []

                # Get data from operating_statistics (has Total Debt/EBITDA)
                if 'operating_statistics' in comps and not comps['operating_statistics'].empty:
                    ops_df = comps['operating_statistics'].copy()
                    fin_df = comps.get('financial_data', pd.DataFrame())

                    for _, row in ops_df.iterrows():
                        company = row.get('Company Name', '')[:30]
                        total_debt_ebitda = row.get('LTM Total Debt/EBITDA ', None)

                        # Try to get Net Debt/EBITDA from financial_data
                        net_debt_ebitda = None
                        if not fin_df.empty:
                            match = fin_df[fin_df['Company Name'].str.contains(company[:15], na=False, regex=False)]
                            if not match.empty:
                                net_debt = match['LTM Net Debt '].iloc[0]
                                ebitda = match['LTM EBITDA '].iloc[0]
                                if pd.notna(net_debt) and pd.notna(ebitda) and ebitda > 0:
                                    net_debt_ebitda = net_debt / ebitda

                        if company:
                            leverage_data.append({
                                'Company': company,
                                'Net Debt/EBITDA': f"{net_debt_ebitda:.1f}x" if pd.notna(net_debt_ebitda) else "-",
                                'Total Debt/EBITDA': f"{total_debt_ebitda:.1f}x" if pd.notna(total_debt_ebitda) else "-",
                            })

                # Add USS metrics from calculated data
                uss_net_debt_ebitda = uss_metrics.get('net_debt_ebitda')
                leverage_data.insert(0, {
                    'Company': 'United States Steel (X)',
                    'Net Debt/EBITDA': f"{uss_net_debt_ebitda:.1f}x" if uss_net_debt_ebitda else "0.7x",
                    'Total Debt/EBITDA': f"{uss_metrics.get('total_debt', 4339) / uss_metrics.get('ebitda', 1919):.1f}x",
                })

                if leverage_data:
                    st.markdown("**Leverage Metrics (as of 12/31/2023)**")
                    st.dataframe(pd.DataFrame(leverage_data), use_container_width=True, hide_index=True)

            with fin_health_col2:
                # Profitability & Growth metrics from operating_statistics
                if 'operating_statistics' in comps and not comps['operating_statistics'].empty:
                    ops_df = comps['operating_statistics'].copy()
                    profit_data = []

                    for _, row in ops_df.iterrows():
                        company = row.get('Company Name', '')[:30]
                        gross_margin = row.get('LTM Gross Margin % ', None)
                        ebitda_margin = row.get('LTM EBITDA Margin % ', None)
                        rev_growth = row.get('LTM Total Revenues, 1 Yr Growth % ', None)

                        if company:
                            profit_data.append({
                                'Company': company,
                                'Gross Margin': f"{gross_margin*100:.1f}%" if pd.notna(gross_margin) else "-",
                                'EBITDA Margin': f"{ebitda_margin*100:.1f}%" if pd.notna(ebitda_margin) else "-",
                                'Rev Growth': f"{rev_growth*100:.1f}%" if pd.notna(rev_growth) else "-",
                            })

                    # Add USS metrics
                    uss_margin = uss_metrics.get('ebitda_margin')
                    profit_data.insert(0, {
                        'Company': 'United States Steel (X)',
                        'Gross Margin': '13.5%',  # From 2023 financials
                        'EBITDA Margin': f"{uss_margin*100:.1f}%" if uss_margin else "10.6%",
                        'Rev Growth': '-1.2%',  # 2023 vs 2022
                    })

                    st.markdown("**Profitability & Growth (as of 12/31/2023)**")
                    st.dataframe(pd.DataFrame(profit_data), use_container_width=True, hide_index=True)

        except Exception as e:
            st.warning(f"Could not load financial health metrics: {e}")

        # Subsection B3: Valuation Comparison Chart
        st.subheader("Valuation Comparison")

        try:
            # Get multiples from trading_multiples sheet, market cap from financial_data
            trading_df = comps.get('trading_multiples', pd.DataFrame())
            fin_df = comps.get('financial_data', pd.DataFrame())

            if not trading_df.empty:
                # Build valuation comparison
                val_data = []
                for _, row in trading_df.iterrows():
                    company = row.get('Company Name', '')
                    # Extract ticker
                    ticker = ''
                    for t in ['NUE', 'CLF', 'STLD', 'CMC', 'ZEUS', 'MT', 'PKX', 'GGB', 'TX', 'BSL']:
                        if t in company.upper():
                            ticker = t
                            break

                    tev_ebitda = row.get('TEV/EBITDA LTM - Latest', None)
                    tev_rev = row.get('TEV/Total Revenues LTM - Latest', None)
                    pe = row.get('P/Diluted EPS Before Extra LTM - Latest', None)

                    # Get market cap from financial_data
                    mkt_cap = None
                    if not fin_df.empty:
                        match = fin_df[fin_df['Company Name'].str.contains(company[:20], na=False, regex=False)]
                        if not match.empty:
                            mkt_cap = match['Market Capitalization Latest'].iloc[0]

                    if ticker:
                        val_data.append({
                            'Ticker': ticker,
                            'TEV/EBITDA': tev_ebitda if pd.notna(tev_ebitda) else None,
                            'TEV/Revenue': tev_rev if pd.notna(tev_rev) else None,
                            'P/E': pe if pd.notna(pe) else None,
                            'Market Cap ($B)': mkt_cap / 1000 if pd.notna(mkt_cap) else None,
                        })

                # Add USS
                val_data.insert(0, {
                    'Ticker': 'X (USS)',
                    'TEV/EBITDA': val_uss['ev_blended'] / ebitda_2024 if ebitda_2024 > 0 else None,
                    'TEV/Revenue': val_uss['ev_blended'] / (consolidated['Revenue'].iloc[0] * 1000) if consolidated['Revenue'].iloc[0] > 0 else None,
                    'P/E': None,  # Would need current price
                    'Market Cap ($B)': offer_price * 225 / 1000,  # At offer price
                })

                val_df = pd.DataFrame(val_data)

                # Create bar chart for TEV/EBITDA comparison
                val_df_clean = val_df.dropna(subset=['TEV/EBITDA'])
                if not val_df_clean.empty:
                    fig_val = go.Figure()

                    # Color USS differently
                    colors = ['#EF553B' if 'USS' in t else '#636EFA' for t in val_df_clean['Ticker']]

                    fig_val.add_trace(go.Bar(
                        x=val_df_clean['Ticker'],
                        y=val_df_clean['TEV/EBITDA'],
                        marker_color=colors,
                        text=[f"{v:.1f}x" for v in val_df_clean['TEV/EBITDA']],
                        textposition='outside'
                    ))

                    # Add median line
                    peer_median = val_df_clean[~val_df_clean['Ticker'].str.contains('USS')]['TEV/EBITDA'].median()
                    fig_val.add_hline(y=peer_median, line_dash="dash", line_color="green",
                                      annotation_text=f"Peer Median: {peer_median:.1f}x")

                    fig_val.update_layout(
                        title="TEV/EBITDA Multiple Comparison",
                        yaxis_title="TEV/EBITDA",
                        showlegend=False,
                        height=400
                    )
                    st.plotly_chart(fig_val, use_container_width=True)

                # Show valuation table
                st.dataframe(val_df.round(2), use_container_width=True, hide_index=True)

        except Exception as e:
            st.warning(f"Could not load valuation comparison: {e}")

        # Subsection C: USS Percentile Ranking
        st.subheader("USS Competitive Position")

        try:
            metrics_to_rank = ['ebitda_margin', 'revenue']
            rankings = []

            for metric in metrics_to_rank:
                rank = benchmark.get_uss_percentile_rank(metric)
                if rank:
                    if metric == 'ebitda_margin':
                        uss_val = f"{rank['uss_value']:.1%}"
                        peer_med = f"{rank['peer_median']:.1%}"
                    elif metric == 'revenue':
                        uss_val = f"${rank['uss_value']/1000:.1f}B"
                        peer_med = f"${rank['peer_median']/1000:.1f}B"
                    else:
                        uss_val = f"{rank['uss_value']:.1f}"
                        peer_med = f"{rank['peer_median']:.1f}"

                    rankings.append({
                        'Metric': metric.replace('_', ' ').title(),
                        'USS Value': uss_val,
                        'Peer Median': peer_med,
                        'Percentile': f"{rank['percentile']:.0f}%",
                        'vs Median': rank['vs_median'].title()
                    })

            if rankings:
                rank_df = pd.DataFrame(rankings)
                st.dataframe(rank_df, use_container_width=True, hide_index=True)

                # Visual percentile indicator
                rank_cols = st.columns(len(rankings))
                for i, rank_info in enumerate(rankings):
                    with rank_cols[i]:
                        pct = float(rank_info['Percentile'].replace('%', ''))
                        color = '#00CC96' if pct >= 50 else '#EF553B'
                        st.markdown(f"""
                        <div style="text-align: center;">
                            <div style="font-weight: bold;">{rank_info['Metric']}</div>
                            <div style="font-size: 24px; color: {color};">{rank_info['Percentile']}</div>
                            <div style="font-size: 12px;">percentile</div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("Percentile ranking data not available")

        except Exception as e:
            st.warning(f"Could not calculate percentile rankings: {e}")

    # =========================================================================
    # MULTI-YEAR GROWTH & PROFITABILITY ANALYSIS
    # =========================================================================

    st.markdown("---")
    st.header("USS vs Peers: Growth & Profitability (2019-2024)", anchor="multi-year-growth")

    st.markdown("""
    Comprehensive CAGR (Compound Annual Growth Rate) analysis comparing USS vs steel industry peers
    across 2019-2024, with USS long-term historical view back to the 1990s.
    """)

    # Ensure benchmark is available for this section
    if not benchmark_available:
        st.warning("Benchmark data not available for growth analysis")
    else:
        try:
            # Subsection A: CAGR Comparison Bar Charts
            st.subheader("A. CAGR Comparison: USS vs Peers")

            # Metric and period selectors
            growth_col1, growth_col2 = st.columns(2)

            with growth_col1:
                cagr_metric = st.selectbox(
                    "Select Metric",
                    options=['revenue', 'ebitda', 'net_income', 'capex', 'depreciation', 'total_assets'],
                    format_func=lambda x: x.replace('_', ' ').title(),
                    key='cagr_metric'
                )

            with growth_col2:
                cagr_period = st.radio(
                    "Select Period",
                    options=[3, 5],
                    format_func=lambda x: f"{x}-Year CAGR",
                    horizontal=True,
                    key='cagr_period'
                )

            # Get growth analysis data
            growth_stats = benchmark.get_multiyear_growth_analysis([cagr_metric], [cagr_period])

            if growth_stats:
                gs = growth_stats[0]

                # Get individual company CAGRs for bar chart
                rolling_data = benchmark.get_rolling_period_analysis([cagr_metric], cagr_period)

                # Filter to the specific period that matches our analysis
                end_year = 2024
                start_year = end_year - cagr_period
                period_label = f"{start_year}-{str(end_year)[2:]}"

                period_data = rolling_data[rolling_data['period_label'] == period_label]

                if not period_data.empty:
                    # Sort by CAGR
                    period_data_sorted = period_data.sort_values('cagr', ascending=False)

                    # Create bar chart
                    fig_cagr = go.Figure()

                    # Color USS differently
                    colors = ['#EF553B' if t == 'X' else '#636EFA' for t in period_data_sorted['ticker']]

                    # Format labels
                    labels = []
                    for _, row in period_data_sorted.iterrows():
                        if row['ticker'] == 'X':
                            labels.append('USS (X)')
                        else:
                            labels.append(row['ticker'])

                    fig_cagr.add_trace(go.Bar(
                        x=labels,
                        y=period_data_sorted['cagr'] * 100,  # Convert to percentage
                        marker_color=colors,
                        text=[f"{v*100:.1f}%" for v in period_data_sorted['cagr']],
                        textposition='outside'
                    ))

                    # Add peer median line
                    peer_cagrs = period_data_sorted[period_data_sorted['ticker'] != 'X']['cagr']
                    if not peer_cagrs.empty:
                        peer_median = peer_cagrs.median() * 100
                        fig_cagr.add_hline(
                            y=peer_median, line_dash="dash", line_color="green",
                            annotation_text=f"Peer Median: {peer_median:.1f}%"
                        )

                    fig_cagr.update_layout(
                        title=f"{cagr_metric.replace('_', ' ').title()} {cagr_period}-Year CAGR ({start_year}-{end_year})",
                        yaxis_title="CAGR (%)",
                        xaxis_title="Company",
                        showlegend=False,
                        height=450
                    )

                    st.plotly_chart(fig_cagr, use_container_width=True)

                    # Show summary stats
                    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

                    with stats_col1:
                        uss_cagr_pct = gs.uss_cagr * 100 if gs.uss_cagr is not None else None
                        st.metric(
                            "USS CAGR",
                            f"{uss_cagr_pct:.1f}%" if uss_cagr_pct is not None else "N/A"
                        )

                    with stats_col2:
                        st.metric("Peer Median", f"{gs.peer_median * 100:.1f}%")

                    with stats_col3:
                        st.metric("Peer Range", f"[{gs.peer_min * 100:.1f}%, {gs.peer_max * 100:.1f}%]")

                    with stats_col4:
                        if gs.uss_percentile is not None:
                            pctl_color = "#00CC96" if gs.uss_percentile >= 50 else "#EF553B"
                            st.markdown(f"""
                            <div style="text-align: center; padding-top: 5px;">
                                <div style="font-size: 12px; color: #666;">USS Percentile</div>
                                <div style="font-size: 24px; font-weight: bold; color: {pctl_color};">{gs.uss_percentile:.0f}th</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.metric("USS Percentile", "N/A")
                else:
                    st.info(f"No data available for {cagr_period}-year period")
            else:
                st.info("Growth analysis data not available")

            # Subsection B: Historical Trend Lines (2019-2024)
            st.subheader("B. Historical Trend Lines (2019-2024)")

            trend_col1, trend_col2 = st.columns([1, 2])

            with trend_col1:
                trend_metric = st.selectbox(
                    "Select Metric for Trend",
                    options=['revenue', 'ebitda', 'net_income', 'capex'],
                    format_func=lambda x: x.replace('_', ' ').title(),
                    key='trend_metric'
                )

                # Get available peers
                peer_ts = benchmark.get_peer_timeseries(trend_metric, 2019, 2024)
                available_peers = peer_ts['ticker'].unique().tolist() if not peer_ts.empty else []

                # Default selection: primary US comps + a couple others
                default_peers = ['NUE', 'CLF', 'STLD', 'MT']
                default_selection = [p for p in default_peers if p in available_peers]

                selected_peers = st.multiselect(
                    "Select Peers to Compare",
                    options=available_peers,
                    default=default_selection[:4],
                    key='trend_peers'
                )

            with trend_col2:
                if selected_peers:
                    # Get USS timeseries
                    uss_ts = benchmark.get_uss_timeseries([trend_metric], 2019, 2024)

                    # Get peer timeseries filtered
                    peer_ts_filtered = peer_ts[peer_ts['ticker'].isin(selected_peers)]

                    fig_trend = go.Figure()

                    # Add USS line (highlighted)
                    if not uss_ts.empty:
                        fig_trend.add_trace(go.Scatter(
                            x=uss_ts['year'],
                            y=uss_ts[trend_metric],
                            mode='lines+markers',
                            name='USS (X)',
                            line=dict(color='#EF553B', width=3),
                            marker=dict(size=8)
                        ))

                    # Add peer lines
                    colors = ['#636EFA', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880']
                    for i, ticker in enumerate(selected_peers):
                        ticker_data = peer_ts_filtered[peer_ts_filtered['ticker'] == ticker]
                        if not ticker_data.empty:
                            fig_trend.add_trace(go.Scatter(
                                x=ticker_data['year'],
                                y=ticker_data['value'],
                                mode='lines+markers',
                                name=ticker,
                                line=dict(color=colors[i % len(colors)], width=2),
                                marker=dict(size=6)
                            ))

                    fig_trend.update_layout(
                        title=f"{trend_metric.replace('_', ' ').title()} Trend (2019-2024)",
                        xaxis_title="Year",
                        yaxis_title=f"{trend_metric.replace('_', ' ').title()} ($M)",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        height=400
                    )

                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("Select at least one peer to compare")

            # Subsection C: Rolling Period Analysis
            st.subheader("C. Rolling Period CAGR Analysis")

            rolling_window = st.radio(
                "Rolling Window",
                options=[3, 5],
                format_func=lambda x: f"{x}-Year Rolling CAGR",
                horizontal=True,
                key='rolling_window'
            )

            rolling_metric = st.selectbox(
                "Metric",
                options=['revenue', 'ebitda', 'net_income', 'capex'],
                format_func=lambda x: x.replace('_', ' ').title(),
                key='rolling_metric'
            )

            rolling_data = benchmark.get_rolling_period_analysis([rolling_metric], rolling_window)

            if not rolling_data.empty:
                # Pivot for heatmap-style view
                rolling_pivot = rolling_data.pivot_table(
                    index='ticker', columns='period_label', values='cagr', aggfunc='first'
                )

                # Sort with USS at top
                if 'X' in rolling_pivot.index:
                    other_idx = [i for i in rolling_pivot.index if i != 'X']
                    rolling_pivot = rolling_pivot.reindex(['X'] + sorted(other_idx))

                # Create heatmap
                fig_rolling = go.Figure(data=go.Heatmap(
                    z=rolling_pivot.values * 100,
                    x=rolling_pivot.columns.tolist(),
                    y=rolling_pivot.index.tolist(),
                    colorscale='RdYlGn',
                    zmid=0,
                    text=[[f"{v*100:.1f}%" if not pd.isna(v) else "N/A" for v in row] for row in rolling_pivot.values],
                    texttemplate="%{text}",
                    textfont={"size": 10},
                    colorbar=dict(title="CAGR (%)")
                ))

                fig_rolling.update_layout(
                    title=f"Rolling {rolling_window}-Year {rolling_metric.replace('_', ' ').title()} CAGR by Company",
                    xaxis_title="Period",
                    yaxis_title="Company",
                    height=max(300, len(rolling_pivot) * 35 + 100)
                )

                st.plotly_chart(fig_rolling, use_container_width=True)
            else:
                st.info("Rolling period data not available")

            # Subsection D: USS Long-Term Historical (1990s-2020s)
            st.subheader("D. USS Long-Term Historical Performance")

            st.markdown("""
            *Note: Peer data only available from 2019. This section shows USS-only decade performance.*
            """)

            longterm_data = benchmark.get_uss_longterm_historical(['revenue', 'ebitda', 'net_income', 'capex'])

            if not longterm_data.empty:
                longterm_metric = st.selectbox(
                    "Select Metric",
                    options=['revenue', 'ebitda', 'net_income', 'capex'],
                    format_func=lambda x: x.replace('_', ' ').title(),
                    key='longterm_metric'
                )

                metric_data = longterm_data[longterm_data['metric'] == longterm_metric]

                if not metric_data.empty:
                    # Filter out rows with NaN CAGR
                    metric_data_clean = metric_data.dropna(subset=['cagr'])

                    if not metric_data_clean.empty:
                        fig_longterm = go.Figure()

                        # Color bars based on positive/negative
                        colors = ['#00CC96' if c >= 0 else '#EF553B' for c in metric_data_clean['cagr']]

                        fig_longterm.add_trace(go.Bar(
                            x=metric_data_clean['decade'],
                            y=metric_data_clean['cagr'] * 100,
                            marker_color=colors,
                            text=[f"{c*100:.1f}%" for c in metric_data_clean['cagr']],
                            textposition='outside'
                        ))

                        fig_longterm.add_hline(y=0, line_color="gray", line_dash="solid")

                        fig_longterm.update_layout(
                            title=f"USS {longterm_metric.replace('_', ' ').title()} CAGR by Decade",
                            xaxis_title="Decade",
                            yaxis_title="CAGR (%)",
                            showlegend=False,
                            height=400
                        )

                        st.plotly_chart(fig_longterm, use_container_width=True)

                        # Show data table
                        display_cols = ['decade', 'start_year', 'end_year', 'start_value', 'end_value', 'cagr', 'years']
                        display_df = metric_data[display_cols].copy()
                        display_df['cagr'] = display_df['cagr'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
                        display_df['start_value'] = display_df['start_value'].apply(lambda x: f"${x:,.0f}M" if pd.notna(x) else "N/A")
                        display_df['end_value'] = display_df['end_value'].apply(lambda x: f"${x:,.0f}M" if pd.notna(x) else "N/A")
                        display_df.columns = ['Decade', 'Start Year', 'End Year', 'Start Value', 'End Value', 'CAGR', 'Years']

                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No valid CAGR data available for {longterm_metric.replace('_', ' ').title()} (may have negative values)")
                else:
                    st.info("Long-term data not available for this metric")
            else:
                st.info("USS long-term historical data not available")

            # Subsection E: Growth Summary Table
            st.subheader("E. Growth Analysis Summary")

            summary_df = benchmark.get_growth_summary_table()

            if not summary_df.empty:
                # Add styling based on percentile
                def style_percentile(val):
                    if 'N/A' in str(val):
                        return 'background-color: #f0f0f0'
                    pctl = int(val.replace('th', ''))
                    if pctl >= 75:
                        return 'background-color: #c6efce; color: #006100'
                    elif pctl >= 25:
                        return 'background-color: #ffeb9c; color: #9c5700'
                    else:
                        return 'background-color: #ffc7ce; color: #9c0006'

                # Display columns (exclude internal columns)
                display_cols = ['Metric', 'Period', 'Years', 'USS CAGR', 'Peer Median', 'Peer Range', 'USS Percentile', 'Peer Count']

                # Apply styling
                styled_df = summary_df[display_cols].style.applymap(
                    style_percentile, subset=['USS Percentile']
                )

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                # Legend
                st.markdown("""
                **Legend:**
                - Green: USS in top 25% of peers (≥75th percentile)
                - Yellow: USS in middle 50% of peers (25th-75th percentile)
                - Red: USS in bottom 25% of peers (<25th percentile)
                """)
            else:
                st.info("Growth summary data not available")

        except Exception as e:
            st.error(f"Error loading Multi-Year Growth Analysis: {e}")
            import traceback
            st.text(traceback.format_exc())


def render_tab_projections(ctx):
    """Tab 5: Financial Projections - FCF, segments, stock price, WACC, detailed model."""
    scenario = ctx['scenario']
    execution_factor = ctx['execution_factor']
    custom_benchmarks = ctx['custom_benchmarks']
    model = ctx['model']
    analysis = ctx['analysis']
    consolidated = ctx['consolidated']
    segment_dfs = ctx['segment_dfs']
    val_uss = ctx['val_uss']
    val_nippon = ctx['val_nippon']
    jpy_wacc = ctx['jpy_wacc']
    usd_wacc = ctx['usd_wacc']
    financing_impact = ctx['financing_impact']

    # Mini table of contents for navigation
    st.markdown(
        "**Sections:** [FCF Projection](#fcf-projection) | "
        "[Segment Analysis](#segment-analysis) | "
        "[Stock Price History](#uss-price-comparison) | "
        "[WACC Verification](#wacc-components) | "
        "[IRP Adjustment](#irp-adjustment) | "
        "[Full 10-Year Model](#detailed-projections)"
    )

    st.header("FCF Projection", anchor="fcf-projection")

    col1, col2 = st.columns([2, 1])

    with col1:
        # FCF chart by segment over time
        st.subheader("Annual FCF by Segment")

        # Price overlay selector
        hist_prices = load_historical_steel_prices()
        fcf_price_overlay = st.selectbox(
            "Overlay Steel Price:",
            ["None", "HRC US", "CRC US", "HRC EU", "OCTG US"],
            key="fcf_price_overlay",
            help="Add steel price trend to visualize price-FCF correlation"
        )

        fcf_time_data = []
        for name, df in segment_dfs.items():
            for _, row in df.iterrows():
                fcf_time_data.append({
                    'Year': row['Year'],
                    'Segment': name,
                    'FCF': row['FCF']
                })

        fcf_time_df = pd.DataFrame(fcf_time_data)

        if fcf_price_overlay != "None" and hist_prices is not None:
            # Create dual-axis chart with price overlay
            price_df = hist_prices.get_price_series(fcf_price_overlay)
            if price_df is not None:
                # Aggregate FCF by year (sum across segments)
                fcf_by_year = fcf_time_df.groupby('Year')['FCF'].sum()

                # Aggregate price to annual
                annual_price = aggregate_prices_by_year(
                    price_df,
                    int(fcf_by_year.index.min()),
                    int(fcf_by_year.index.max())
                )

                # Create dual-axis chart
                fig = create_dual_axis_chart_with_price(
                    projection_data={'years': fcf_by_year.index.tolist(), 'values': fcf_by_year.values.tolist()},
                    price_data={'years': annual_price.index.tolist(), 'values': annual_price.values.tolist()},
                    projection_label="Total FCF ($M)",
                    price_label=f"{fcf_price_overlay} Price ($/ton)",
                    projection_color="#4ecdc4",
                    price_color="#ff6b6b",
                    chart_title=f"Annual FCF with {fcf_price_overlay} Price Overlay"
                )
            else:
                # Fallback to standard chart if price data unavailable
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
        else:
            # Standard stacked bar chart
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
    # USS PRICE COMPARISON
    # =========================================================================

    st.markdown("---")
    st.header("USS Historical Stock Price vs \\$55 Offer", anchor="uss-price-comparison")

    st.markdown("""
    Compare USS stock prices across key periods to evaluate the Nippon offer premium.
    Reference lines show Nippon (\\$55), Cliffs (\\$54), analyst targets (\\$45), and LBO range (\\$35-42).
    """)

    # Load stock data
    stock_df = load_uss_stock_data()

    if stock_df is not None and not stock_df.empty:
        # Period selection controls - simplified to single row
        price_col1, price_col2 = st.columns([2, 2])

        with price_col1:
            period_options = {
                "Since 2005 (Full Relevant History)": "since_2005",
                "Around Announcement (Nov 2023 - Jan 2024)": "around_announcement",
                "Post-Announcement (Dec 18, 2023+)": "post_announcement",
                "Pre-Rumor (Before Dec 12, 2023)": "pre_rumor",
                "Custom Range": "custom"
            }
            selected_period = st.selectbox(
                "Select Period",
                options=list(period_options.keys()),
                index=0,  # Default to Since 2005
                help="Choose a pre-defined period or select Custom for specific dates"
            )
            period_key = period_options[selected_period]

        # Determine date range based on selection
        min_date = stock_df['date'].min().date()
        max_date = stock_df['date'].max().date()
        data_start_2005 = pd.to_datetime(USS_DATA_START_YEAR).date()

        if period_key == "since_2005":
            start_date = data_start_2005
            end_date = max_date
        elif period_key == "pre_rumor":
            start_date = data_start_2005
            end_date = pd.to_datetime(USS_PRE_RUMOR_END).date()
        elif period_key == "post_announcement":
            start_date = pd.to_datetime(USS_NIPPON_ANNOUNCEMENT_DATE).date()
            end_date = max_date
        elif period_key == "around_announcement":
            start_date = pd.to_datetime('2023-11-01').date()
            end_date = pd.to_datetime('2024-01-31').date()
        else:  # custom
            start_date = data_start_2005
            end_date = max_date

        with price_col2:
            if period_key == "custom":
                custom_col1, custom_col2 = st.columns(2)
                with custom_col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=data_start_2005,
                        min_value=min_date,
                        max_value=max_date
                    )
                with custom_col2:
                    end_date = st.date_input(
                        "End Date",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date
                    )
            else:
                st.markdown(f"**Period:** {start_date} to {end_date}")

        # Filter data for selected period
        mask = (stock_df['date'] >= pd.to_datetime(start_date)) & (stock_df['date'] <= pd.to_datetime(end_date))
        period_df = stock_df[mask].copy()

        if not period_df.empty:
            # Metrics row
            avg_price = period_df['value'].mean()
            min_price = period_df['value'].min()
            max_price = period_df['value'].max()

            # Calculate period return
            first_price = period_df['value'].iloc[0]
            last_price = period_df['value'].iloc[-1]
            period_return = ((last_price / first_price) - 1) * 100 if first_price > 0 else 0

            # Calculate gap to offer (positive = below offer)
            gap_to_nippon = USS_NIPPON_OFFER_PRICE - avg_price

            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            with metric_col1:
                st.metric(
                    "Average Price",
                    f"${avg_price:.2f}",
                    delta=f"{gap_to_nippon:+.2f} below Nippon offer" if gap_to_nippon > 0 else f"{-gap_to_nippon:.2f} above Nippon offer",
                    delta_color="inverse" if gap_to_nippon > 0 else "normal"
                )
            with metric_col2:
                st.metric("Minimum Price", f"${min_price:.2f}")
            with metric_col3:
                st.metric("Maximum Price", f"${max_price:.2f}")
            with metric_col4:
                st.metric(
                    "Period Return",
                    f"{period_return:+.1f}%",
                    delta=f"{len(period_df)} trading days"
                )

            # Main price chart - no toggles, always shows all reference lines
            price_chart = create_price_history_chart(stock_df, start_date, end_date)
            if price_chart:
                st.plotly_chart(price_chart, use_container_width=True)

            # Period comparison (show for since_2005, around_announcement, or periods spanning the announcement)
            announcement_date = pd.to_datetime(USS_NIPPON_ANNOUNCEMENT_DATE)
            show_comparison = period_key in ["since_2005", "around_announcement"] or \
                              (pd.to_datetime(start_date) < announcement_date < pd.to_datetime(end_date))

            if show_comparison:
                st.subheader("Period Analysis & Comparison")

                comp_col1, comp_col2 = st.columns([1, 1])

                with comp_col1:
                    comparison_chart = create_period_comparison_chart(stock_df)
                    st.plotly_chart(comparison_chart, use_container_width=True)

                with comp_col2:
                    # Enhanced statistics table with more periods
                    pre_rumor_mask = stock_df['date'] <= pd.to_datetime(USS_PRE_RUMOR_END)
                    rumor_mask = (stock_df['date'] >= pd.to_datetime(USS_RUMOR_PERIOD_START)) & \
                                 (stock_df['date'] <= pd.to_datetime(USS_LAST_TRADING_DAY_BEFORE))
                    post_announce_mask = stock_df['date'] >= pd.to_datetime(USS_NIPPON_ANNOUNCEMENT_DATE)
                    ytd_2023_mask = (stock_df['date'] >= pd.to_datetime('2023-01-01')) & \
                                    (stock_df['date'] <= pd.to_datetime('2023-11-30'))

                    pre_data = stock_df[pre_rumor_mask]['value']
                    rumor_data = stock_df[rumor_mask]['value']
                    post_data = stock_df[post_announce_mask]['value']
                    ytd_data = stock_df[ytd_2023_mask]['value']

                    def safe_stat(data, func, fmt="$"):
                        if len(data) > 0:
                            val = func(data)
                            return f"{fmt}{val:.2f}" if fmt == "$" else f"{val:.2f}"
                        return "N/A"

                    stats_data = {
                        'Metric': ['Average', 'Median', 'Min', 'Max', 'Volatility', 'Days'],
                        '2023 YTD': [
                            safe_stat(ytd_data, lambda x: x.mean()),
                            safe_stat(ytd_data, lambda x: x.median()),
                            safe_stat(ytd_data, lambda x: x.min()),
                            safe_stat(ytd_data, lambda x: x.max()),
                            safe_stat(ytd_data, lambda x: x.std(), ""),
                            f"{len(ytd_data):,}"
                        ],
                        'Pre-Rumor': [
                            safe_stat(pre_data, lambda x: x.mean()),
                            safe_stat(pre_data, lambda x: x.median()),
                            safe_stat(pre_data, lambda x: x.min()),
                            safe_stat(pre_data, lambda x: x.max()),
                            safe_stat(pre_data, lambda x: x.std(), ""),
                            f"{len(pre_data):,}"
                        ],
                        'Rumor': [
                            safe_stat(rumor_data, lambda x: x.mean()),
                            safe_stat(rumor_data, lambda x: x.median()),
                            safe_stat(rumor_data, lambda x: x.min()),
                            safe_stat(rumor_data, lambda x: x.max()),
                            safe_stat(rumor_data, lambda x: x.std(), ""),
                            f"{len(rumor_data):,}"
                        ],
                        'Post-Deal': [
                            safe_stat(post_data, lambda x: x.mean()),
                            safe_stat(post_data, lambda x: x.median()),
                            safe_stat(post_data, lambda x: x.min()),
                            safe_stat(post_data, lambda x: x.max()),
                            safe_stat(post_data, lambda x: x.std(), ""),
                            f"{len(post_data):,}"
                        ]
                    }
                    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

                    # Premium analysis table
                    st.markdown("**Premium Analysis vs Offers:**")
                    pre_avg = pre_data.mean() if len(pre_data) > 0 else 0
                    post_avg = post_data.mean() if len(post_data) > 0 else 0

                    premium_data = {
                        'Benchmark': ['Nippon Offer', 'Cliffs Offer', 'Analyst Target', 'LBO Mid'],
                        'Price': [f"${USS_NIPPON_OFFER_PRICE:.0f}", f"${USS_CLIFFS_OFFER_PRICE:.0f}",
                                  f"${USS_ANALYST_CONSENSUS:.0f}", f"${(USS_LBO_ESTIMATE_LOW+USS_LBO_ESTIMATE_HIGH)/2:.0f}"],
                        'vs Pre-Rumor': [
                            f"+{((USS_NIPPON_OFFER_PRICE/pre_avg)-1)*100:.1f}%" if pre_avg > 0 else "N/A",
                            f"+{((USS_CLIFFS_OFFER_PRICE/pre_avg)-1)*100:.1f}%" if pre_avg > 0 else "N/A",
                            f"+{((USS_ANALYST_CONSENSUS/pre_avg)-1)*100:.1f}%" if pre_avg > 0 else "N/A",
                            f"+{(((USS_LBO_ESTIMATE_LOW+USS_LBO_ESTIMATE_HIGH)/2/pre_avg)-1)*100:.1f}%" if pre_avg > 0 else "N/A"
                        ],
                        'vs Post-Deal': [
                            f"+{((USS_NIPPON_OFFER_PRICE/post_avg)-1)*100:.1f}%" if post_avg > 0 else "N/A",
                            f"+{((USS_CLIFFS_OFFER_PRICE/post_avg)-1)*100:.1f}%" if post_avg > 0 else "N/A",
                            f"+{((USS_ANALYST_CONSENSUS/post_avg)-1)*100:.1f}%" if post_avg > 0 else "N/A",
                            f"{(((USS_LBO_ESTIMATE_LOW+USS_LBO_ESTIMATE_HIGH)/2/post_avg)-1)*100:+.1f}%" if post_avg > 0 else "N/A"
                        ]
                    }
                    st.dataframe(pd.DataFrame(premium_data), use_container_width=True, hide_index=True)

            # Expandable raw data table
            with st.expander("View Raw Price Data"):
                display_df = period_df.copy()
                display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                display_df.columns = ['Date', 'Price ($)']
                st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)

        else:
            st.warning("No data available for the selected date range.")

    else:
        st.warning("USS stock price data not available. Ensure the file exists at market-data/exports/processed/stock_uss.csv")

    # =========================================================================
    # WACC COMPONENT DETAILS
    # =========================================================================

    st.markdown("---")
    st.header("WACC Calculation Verification", anchor="wacc-components")

    if WACC_DETAILS_AVAILABLE:
        st.markdown("""
        **Bottom-up WACC calculations** using verified market inputs from the `wacc-calculations` module.
        All inputs are sourced from public data (Federal Reserve, Bank of Japan, SEC filings) as of December 31, 2023.
        """)

        # Show verification status
        if scenario.use_verified_wacc:
            st.success("Using verified WACC values from wacc-calculations module")
        else:
            st.warning("Using manual WACC inputs from scenario. Enable 'Use Verified WACC' in sidebar for module values.")

        wacc_col1, wacc_col2 = st.columns(2)

        with wacc_col1:
            st.subheader("USS WACC Calculation")
            try:
                uss_result = calculate_uss_wacc()
                analyst_estimates = get_analyst_estimates()
                data_date = get_uss_data_date()

                st.markdown(f"*Data as of: {data_date}*")

                st.markdown("**Cost of Equity (CAPM)**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | Risk-Free Rate (10Y UST) | {uss_result.risk_free_rate*100:.2f}% |
    | Levered Beta | {uss_result.levered_beta:.2f} |
    | Equity Risk Premium | {uss_result.equity_risk_premium*100:.2f}% |
    | Size Premium | {uss_result.size_premium*100:.2f}% |
    | **Cost of Equity** | **{uss_result.cost_of_equity*100:.2f}%** |
                """)

                st.markdown("**Cost of Debt**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | Risk-Free Rate | {uss_result.risk_free_rate*100:.2f}% |
    | Credit Spread (BB-) | {uss_result.credit_spread*100:.2f}% |
    | Pre-tax Cost of Debt | {(uss_result.risk_free_rate + uss_result.credit_spread)*100:.2f}% |
    | After-tax Cost of Debt | {uss_result.cost_of_debt_aftertax*100:.2f}% |
                """)

                st.markdown("**Capital Structure & WACC**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | Market Cap | ${uss_result.market_cap:,.0f}M |
    | Total Debt | ${uss_result.total_debt:,.0f}M |
    | Equity Weight | {uss_result.equity_weight*100:.1f}% |
    | Debt Weight | {uss_result.debt_weight*100:.1f}% |
    | **USS WACC** | **{uss_result.wacc*100:.2f}%** |
                """)

                st.markdown("**Analyst WACC Estimates**")
                for analyst, data in analyst_estimates.items():
                    mid = data.get('wacc_midpoint', data.get('wacc_mid', 0))
                    if mid > 0:
                        delta = (uss_result.wacc - mid) * 100
                        delta_str = f"+{delta:.1f}%" if delta > 0 else f"{delta:.1f}%"
                        st.markdown(f"- {analyst}: {mid*100:.1f}% (Model: {delta_str})")

            except Exception as e:
                st.warning(f"Could not load USS WACC details: {e}")

        with wacc_col2:
            st.subheader("Nippon WACC Calculation")
            try:
                nippon_result = calculate_nippon_wacc()
                nippon_data_date = get_nippon_data_date()

                st.markdown(f"*Data as of: {nippon_data_date}*")

                st.markdown("**Cost of Equity (JPY)**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | JGB 10-Year | {nippon_result.jgb_10y*100:.3f}% |
    | Levered Beta (vs TOPIX) | {nippon_result.levered_beta:.2f} |
    | Equity Risk Premium | 5.50% |
    | **Cost of Equity (JPY)** | **{nippon_result.jpy_cost_of_equity*100:.2f}%** |
                """)

                st.markdown("**Cost of Debt (JPY)**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | JGB 10-Year | {nippon_result.jgb_10y*100:.3f}% |
    | Credit Spread (BBB+) | 0.80% |
    | After-tax Cost of Debt | {nippon_result.jpy_cost_of_debt_aftertax*100:.3f}% |
                """)

                st.markdown("**Capital Structure & WACC**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | Market Cap | ${nippon_result.market_cap_usd/1000:,.1f}B |
    | Total Debt | ${nippon_result.total_debt_usd/1000:,.1f}B |
    | Equity Weight | {nippon_result.equity_weight*100:.1f}% |
    | Debt Weight | {nippon_result.debt_weight*100:.1f}% |
    | **JPY WACC** | **{nippon_result.jpy_wacc*100:.2f}%** |
                """)

                st.markdown("**IRP Adjustment to USD**")
                st.markdown(f"""
    | Component | Value |
    |-----------|------:|
    | US 10-Year Treasury | {nippon_result.us_10y*100:.2f}% |
    | JGB 10-Year | {nippon_result.jgb_10y*100:.3f}% |
    | Rate Differential | {nippon_result.irp_differential*100:.2f}% |
    | **USD WACC** | **{nippon_result.usd_wacc*100:.2f}%** |
                """)

            except Exception as e:
                st.warning(f"Could not load Nippon WACC details: {e}")

        # WACC Comparison Summary
        st.markdown("---")
        st.subheader("WACC Advantage Summary")
        if WACC_DETAILS_AVAILABLE:
            try:
                uss_wacc_val = uss_result.wacc
                nippon_usd_wacc_val = nippon_result.usd_wacc
                wacc_advantage = uss_wacc_val - nippon_usd_wacc_val

                summary_col1, summary_col2, summary_col3 = st.columns(3)
                with summary_col1:
                    st.metric("USS WACC", f"{uss_wacc_val*100:.2f}%")
                with summary_col2:
                    st.metric("Nippon USD WACC", f"{nippon_usd_wacc_val*100:.2f}%")
                with summary_col3:
                    st.metric("WACC Advantage", f"{wacc_advantage*100:.2f}%",
                             help="Lower cost of capital = higher valuation for same cash flows")

                st.info(f"""
                **Implication:** Nippon's {wacc_advantage*100:.2f}% lower cost of capital means the same USS cash flows
                are worth more to Nippon than to USS shareholders. This is a key driver of the valuation gap.
                """)
            except:
                pass

    else:
        st.warning("WACC calculations module not available. Install wacc-calculations for detailed component breakdown.")

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

    # WACC Audit Trail (if available)
    if analysis.get('wacc_audit_trail'):
        with st.expander("WACC Audit Trail", expanded=False):
            audit = analysis['wacc_audit_trail']
            st.markdown(f"**Source:** {audit.get('source', 'N/A')}")
            st.json(audit)

    # =========================================================================
    # DETAILED TABLES
    # =========================================================================

    st.markdown("---")
    st.header("Full 10-Year Financial Model", anchor="detailed-projections")

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
                    # Use dynamic EBITDA calculation (same as main capital projects section)
                    final_ebitda = get_dynamic_project_ebitda(model, proj, 2033)
                    project_rows.append(f"| {proj_name} | {proj.segment} | ${total_capex:,.0f}M | ${final_ebitda:,.0f}M |")

            st.markdown(f"""
    | Project | Segment | Total CapEx | 2033 EBITDA* |
    |---------|---------|-------------|-------------|
    {chr(10).join(project_rows)}
            """)
            st.caption("*EBITDA calculated dynamically based on scenario price assumptions*")
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
    # SOURCES AND ASSUMPTIONS
    # =========================================================================

    st.markdown("---")
    st.markdown("## Model Sources & Assumptions")

    with st.expander("Primary Data Sources", expanded=False):
        st.markdown("""
        ### SEC Filings
        - **USS 10-K FY2023** (Filed Feb 2024): Segment volumes, revenues, balance sheet
        - **USS DEFM14A** (Filed Mar 2024): Fairness opinions (Barclays, Goldman), management projections
        - **CIK:** 0001163302

        ### Financial Data Providers
        - **Capital IQ (S&P Global)**: Historical financials, peer comps, balance sheet verification
            - Total Debt: \\$4,339M (incl \\$297M leases) vs Model \\$3,913M
            - Net Debt: \\$1,391M vs Model \\$1,366M (1.8% variance)
        - **Bloomberg Terminal**: Steel price histories, futures curves, volatility calibration
        - **WRDS Compustat**: Financial statements, segment data validation

        ### Market Data
        - **CME Group**: HRC futures settlements (through 2023-12-18)
        - **Steel Benchmarker**: Global steel price indices
        - **FRED (Federal Reserve)**: Treasury rates, PPI indices

        ### Analyst Research
        - **Barclays WACC Range**: 11.5-13.5% (DEFM14A Annex A)
        - **Goldman WACC Range**: 11.5-13.0% (DEFM14A Annex B)
        - **JPM Equity Research**: 10.0-12.0% WACC
        """)

        st.markdown("""
        **Source Documents Available in:** `references/` folder
        - uss_10k_2023.htm (4.7 MB)
        - uss_defm14a_2024.htm (2.9 MB)
        - uss_capital_iq_export_2023.xls
        """)

    with st.expander("Key Model Assumptions", expanded=False):
        st.markdown("""
        ### Through-Cycle Steel Price Benchmarks
        Rebased from historical mean to exclude 2021-2022 COVID anomaly:

        | Product | Benchmark Price | Derivation Method |
        |---------|----------------|-------------------|
        | HRC US | \\$738/ton | Avg(Pre-COVID \\$625, Post-Spike \\$850) |
        | CRC US | \\$994/ton | Avg(Pre-COVID \\$820, Post-Spike \\$1,130) |
        | Coated US | \\$1,113/ton | Avg(Pre-COVID \\$920, Post-Spike \\$1,266) |
        | HRC EU | \\$611/ton | Avg(Pre-COVID \\$512, Post-Spike \\$710) |
        | OCTG | \\$2,388/ton | Avg(Pre-COVID \\$1,350, Post-Spike \\$3,228) |

        ### Section 232 Tariff Model
        - **Current Rate**: 25% (2018-present)
        - **HRC Price Uplift**: 15% at 25% tariff (conservative between OLS 7% and empirical 18%)
        - **EU Indirect Impact**: 30% (trade diversion effects)
        - **OCTG Impact**: 60% (separate trade dynamics)

        ### Margin Sensitivity (Conservative)
        Model uses ~50% of empirical regression coefficients to avoid overestimating operating leverage:

        | Segment | Model | Empirical (2019-2023) | R² |
        |---------|-------|----------------------|-----|
        | Flat-Rolled | 2.0%/\\$100 | 4.3%/\\$100 | 0.85 |
        | Mini Mill | 2.5%/\\$100 | 2.8%/\\$100 | 0.85 |
        | USSE | 2.0%/\\$100 | 3.8%/\\$100 | 0.87 |
        | Tubular | 1.0%/\\$100 | 2.1%/\\$100 | 0.74 |

        **Rationale**: Empirical includes volume effects and operating leverage; model isolates price impact.

        ### WACC Components
        - **Risk-Free Rate**: 3.88% (10Y Treasury, 12/29/2023)
        - **Equity Beta**: 1.45 (consensus: Bloomberg 1.42, Yahoo 1.48, CapIQ 1.44)
        - **Equity Risk Premium**: 5.5% (Duff & Phelps 2023)
        - **Size Premium**: 1.0% (Duff & Phelps Small Cap Study)
        - **Cost of Debt**: 7.2% (weighted avg: 6.625% Notes, 6.125% Notes, Term Loan B)
        - **Tax Rate**: 25% (21% federal + 4% state)

        ### Capital Projects (Dynamic EBITDA)
        Formula: `EBITDA = Capacity × Utilization × Scenario Price × Margin`

        Base case enables only BR2 (\\$3.2B CapEx, \\$459M EBITDA). Other projects included in various scenarios:
        - Gary Works BF: \\$3.2B CapEx, \\$285M EBITDA
        - Mon Valley HSM: \\$2.4B CapEx, \\$205M EBITDA
        - Greenfield MM: \\$1.0B CapEx, \\$77M EBITDA
        - Mining: \\$1.0B CapEx, \\$108M EBITDA
        - Fairfield: \\$0.6B CapEx, \\$130M EBITDA
        """)

    with st.expander("Monte Carlo Configuration", expanded=False):
        st.markdown("""
        ### Distribution Parameters (26 Variables)
        **Calibration Date**: 2026-02-05 (data through 2023-12-18)

        **Key Price Factor Volatilities** (lognormal, through-cycle):
        - HRC US: σ = 0.18 (vs full-period 0.26, excludes COVID spike)
        - CRC US: σ = 0.16
        - Coated US: σ = 0.15
        - HRC EU: σ = 0.15
        - OCTG: σ = 0.22
        - EUR/USD: σ = 0.08

        **Correlation Matrix** (return-based, not level):
        - HRC ↔ CRC: 0.88 (high co-movement)
        - HRC ↔ Coated: 0.85
        - HRC ↔ OCTG: 0.20 (low, energy-driven)
        - HRC ↔ EU: 0.60 (moderate, trade arbitrage)

        **Tariff Scenario Distributions**:
        - Probability tariff maintained: Beta(8,2) ~ 80%
        - Tariff rate if changed: Triangular(0%, 10%, 50%)

        **Margin Cap**: 22% (reduced from 30% to match steel industry norms)

        **Simulation**: 10,000 iterations per run
        """)

        st.markdown("""
        **Data Sources**:
        - Price volatilities: Bloomberg historical returns (adjusted for through-cycle)
        - Correlations: Bloomberg daily returns 2019-2023
        - Config file: `monte_carlo/distributions_config.json`
        """)

    with st.expander("Detailed Documentation", expanded=False):
        st.markdown("""
        ### Audit & Verification Documents
        Located in `audit-verification/` folder:

        **Comprehensive Guides**:
        - `AUDIT_SUMMARY.md` - Complete audit trail and reconciliation
        - `VARIABLE_SOURCE_MANIFEST.md` - Every variable with source citations
        - `CAPITAL_PROJECTS_EBITDA_IMPACT_ANALYSIS.md` - Project valuation methodology
        - `TARIFF_MODEL_ANALYSIS.md` - Section 232 impact modeling

        **Calibration Memos**:
        - `PRICE_FACTOR_RECALIBRATION_MEMO.md` - Through-cycle benchmark derivation
        - `DATA_SOURCES_SUMMARY.md` - Data collection summary

        ### Key Reconciliations

        **Equity Bridge Validation**:
        ```
        Enterprise Value                = \\$13,252M
        (-) Net Debt                    = \\$1,366M
        (=) Equity Value               = \\$11,886M
        (÷) Shares Outstanding         = 225M
        (=) Value per Share            = \\$52.83 (pre-deal estimate)

        Deal Offer:                    = \\$55.00/share
        Implied Premium:               = 4.1%
        ```

        **Capital IQ Cross-Check**:
        - Model Net Debt: \\$1,366M
        - CIQ Net Debt: \\$1,391M
        - Variance: +\\$25M (1.8%) ✓

        **Segment Data Verification**:
        All volumes, revenues, and margins tie to USS 10-K FY2023 within ±2%

        ### Model Architecture
        - **Base Engine**: `price_volume_model.py` (2,100+ lines)
        - **WACC Calculator**: `wacc-calculations/` (separate for USS & Nippon)
        - **Monte Carlo**: `monte_carlo/monte_carlo_engine.py`
        - **Dashboard**: `interactive_dashboard.py` (this file)

        ### Testing Status
        - Unit Tests: 95% pass rate (5 Bloomberg calibration mode tests expected to fail without terminal)
        - Integration Tests: All pass
        - Validation: Empirical margin sensitivity shows model is conservative (50% of historical)
        """)

        st.markdown("""
        ### Methodological Notes

        **Conservative Assumptions**:
        1. Margin sensitivity at 50% of empirical (excludes volume/leverage effects)
        2. Through-cycle prices exclude COVID spike (2021-2022)
        3. Maintenance CapEx at upper end of peer range
        4. Margin cap at 22% vs historical peaks >30%

        **Known Limitations**:
        1. Model does not capture cyclical timing (averages over 10Y)
        2. Synergies estimated from management guidance (not bottom-up)
        3. Capital projects execution risk simplified to binary factor
        4. FX movements modeled independently (excludes purchasing power parity)
        """)

    with st.expander("Peer Benchmarks", expanded=False):
        st.markdown("""
        ### Steel Industry Peers (FY2023)

        **Maintenance CapEx Intensity**:
        - Nucor (NUE): \\$119/ton total CapEx
        - Steel Dynamics (STLD): \\$165/ton total CapEx
        - Cleveland-Cliffs (CLF): \\$49/ton total CapEx
        - Commercial Metals (CMC): \\$106/ton total CapEx
        - ArcelorMittal (MT): \\$84/ton total CapEx

        **Model Assumptions** (sustaining only, ~40-60% of total):
        - EAF (Mini Mill): \\$20/ton
        - Blast Furnace: \\$40/ton

        **EBITDA Margins** (historical ranges):
        - Flat-Rolled: 8-15% (through-cycle)
        - Mini Mill (EAF): 12-20% (higher margins, lower costs)
        - USSE (Europe): 5-12% (competitive market)
        - Tubular: 15-30% (energy-linked, volatile)

        **Leverage Ratios** (Net Debt / EBITDA):
        - USS (pre-deal): 0.8x
        - Peer Median: 1.5x
        - USS Covenant: 4.0x max (no breach projected)
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


# =============================================================================
# MAIN CONTENT
# =============================================================================

def main():
    # Title
    st.title("USS / Nippon Steel Merger Analysis")
    st.markdown("**Price x Volume DCF Model with Scenario Analysis**")

    # Get assumptions from sidebar
    scenario, scenario_name, execution_factor, custom_benchmarks = render_sidebar()

    # =========================================================================
    # INITIALIZE SESSION STATE
    # =========================================================================
    calc_states = ['calc_football_field', 'calc_lbo', 'cached_scenario_hash', 'stale_sections']

    for state in calc_states:
        if state not in st.session_state:
            if state == 'stale_sections':
                st.session_state[state] = set()
            else:
                st.session_state[state] = None

    # Track scenario hash for cache invalidation
    current_hash = create_scenario_hash(scenario, execution_factor, custom_benchmarks)
    if st.session_state.cached_scenario_hash != current_hash:
        st.session_state.calc_football_field = None
        st.session_state.calc_lbo = None
        st.session_state.cached_scenario_hash = current_hash
        cp.clear_old_caches(current_hash)

    # Run the model with execution factor and custom benchmarks
    progress_bar = st.progress(0, text="Loading financial model...")

    # Define callback function for real-time progress updates
    def update_progress(percent: int, message: str):
        progress_bar.progress(percent, text=message)

    # Build model with callback
    model = PriceVolumeModel(
        scenario,
        execution_factor=execution_factor,
        custom_benchmarks=custom_benchmarks,
        progress_callback=update_progress
    )

    # Run analysis (progress updates happen via callback)
    analysis = model.run_full_analysis()

    # Clean up
    progress_bar.empty()

    consolidated = analysis['consolidated']
    segment_dfs = analysis['segment_dfs']
    jpy_wacc = analysis['jpy_wacc']
    usd_wacc = analysis['usd_wacc']
    val_uss = analysis['val_uss']
    val_nippon = analysis['val_nippon']
    financing_impact = analysis.get('financing_impact', {})

    # =========================================================================
    # EXPORT MODEL SECTION (in sidebar)
    # =========================================================================
    st.sidebar.markdown("---")
    st.sidebar.header("Export Model")

    export_type = st.sidebar.radio(
        "Export Type",
        ["Current Scenario (Static)", "All Scenarios Comparison", "Interactive Model (Formulas)"],
        help="Static exports values; Interactive exports working Excel formulas"
    )

    if st.sidebar.button("Generate Excel Export", type="primary"):
        from scripts.export_model import ModelExporter, FormulaModelExporter, get_export_filename

        with st.sidebar.spinner("Generating Excel file..."):
            if export_type == "Interactive Model (Formulas)":
                exporter = FormulaModelExporter(scenario, execution_factor, custom_benchmarks)
                excel_bytes = exporter.export_with_formulas()
                filename = get_export_filename(scenario_name, "formula")
            else:
                exporter = ModelExporter(scenario, execution_factor, custom_benchmarks)
                if export_type == "Current Scenario (Static)":
                    excel_bytes = exporter.export_single_scenario()
                    filename = get_export_filename(scenario_name, "single")
                else:
                    excel_bytes = exporter.export_multi_scenario()
                    filename = get_export_filename(scenario_name, "multi")

            st.sidebar.download_button(
                label="Download Excel File",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


    # =========================================================================
    # DERIVED VARIABLES FOR TAB CONTEXT
    # =========================================================================

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

    # Build context dict for tab functions
    ctx = {
        'scenario': scenario,
        'scenario_name': scenario_name,
        'execution_factor': execution_factor,
        'custom_benchmarks': custom_benchmarks,
        'model': model,
        'analysis': analysis,
        'consolidated': consolidated,
        'segment_dfs': segment_dfs,
        'jpy_wacc': jpy_wacc,
        'usd_wacc': usd_wacc,
        'val_uss': val_uss,
        'val_nippon': val_nippon,
        'financing_impact': financing_impact,
        'uss_standalone': uss_standalone,
        'nippon_value': nippon_value,
        'pe_max_price': pe_max_price,
        'offer_price': offer_price,
        'ebitda_2024': ebitda_2024,
        'implied_ev_ebitda': implied_ev_ebitda,
        'wacc_advantage': wacc_advantage,
        'offer_vs_standalone': offer_vs_standalone,
        'offer_vs_nippon_value': offer_vs_nippon_value,
        'uss_shareholder_verdict': uss_shareholder_verdict,
        'uss_board_verdict': uss_board_verdict,
        'nippon_verdict': nippon_verdict,
        'cliffs_nominal': cliffs_nominal,
        'cliffs_risk_adjusted': cliffs_risk_adjusted,
        'scenario_hash': current_hash,
    }

    # =========================================================================
    # TAB-BASED LAYOUT
    # =========================================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Executive Decision",
        "Valuation Analysis",
        "Risk & Sensitivity",
        "Strategic Context",
        "Financial Projections",
    ])

    with tab1:
        render_tab_executive(ctx)
    with tab2:
        render_tab_valuation(ctx)
    with tab3:
        render_tab_risk(ctx)
    with tab4:
        render_tab_strategic(ctx)
    with tab5:
        render_tab_projections(ctx)



if __name__ == "__main__":
    main()
