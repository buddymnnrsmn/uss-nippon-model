#!/usr/bin/env python3
"""
USS-Nippon Steel: Value Creation Charts
=======================================

Visualization functions for value creation analysis:
- Value bridge waterfall chart
- Synergy ramp visualization
- Stakeholder value matrix
- Competitive positioning spider chart

Author: RAMBAS Team
Date: January 2025
"""

import sys
from pathlib import Path
from typing import Dict
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

# Add parent directory for model imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from value_creation.value_creation_analysis import (
    ValueCreationAnalysis,
    build_value_creation_sources,
    build_multi_year_value_bridge,
    calculate_synergy_npv,
    DEAL_PRICE_PER_SHARE,
    SHARES_OUTSTANDING,
)
from value_creation.stakeholder_analysis import StakeholderAnalysis
from value_creation.competitive_positioning import (
    CompetitivePositioning,
    get_competitor_profiles,
)


# =============================================================================
# CHART STYLE CONSTANTS
# =============================================================================

# Colors
COLORS = {
    'standalone': '#3498db',  # Blue
    'integration': '#e74c3c',  # Red
    'cost_synergy': '#27ae60',  # Green
    'tech_synergy': '#9b59b6',  # Purple
    'rev_synergy': '#f39c12',  # Orange
    'capex': '#1abc9c',  # Teal
    'deal_price': '#2c3e50',  # Dark blue
    'positive': '#27ae60',
    'negative': '#e74c3c',
}

# Style
plt.style.use('seaborn-v0_8-whitegrid')


# =============================================================================
# VALUE BRIDGE WATERFALL CHART
# =============================================================================

def create_value_bridge_waterfall(
    output_path: str = None,
    standalone_value: float = 50.14,
) -> plt.Figure:
    """
    Create waterfall chart showing value bridge from standalone to combined value.

    Shows:
    - Starting point (USS standalone DCF)
    - Integration costs (negative)
    - Operating synergies (positive)
    - Technology synergies (positive)
    - Revenue synergies (positive)
    - CapEx benefits (positive)
    - Final combined value

    Args:
        output_path: Path to save chart (optional)
        standalone_value: USS standalone value per share

    Returns:
        matplotlib Figure object
    """
    # Get value bridge at Year 5 (full synergy realization)
    bridge = build_multi_year_value_bridge(
        years=[0, 1, 2, 3, 4, 5],
        standalone_value_per_share=standalone_value,
    )

    # Get Year 5 values
    y5 = bridge[-1]

    # Build waterfall data
    categories = [
        'USS Standalone',
        'Integration Costs',
        'Cost Synergies',
        'Technology Synergies',
        'Revenue Synergies',
        'CapEx Benefits',
        'Combined Value',
    ]

    values = [
        y5.standalone_value,
        y5.integration_costs,
        y5.operating_synergies,
        y5.technology_synergies,
        y5.revenue_synergies,
        y5.capex_benefits,
        y5.total_value,
    ]

    # Calculate running totals for waterfall positioning
    running_total = [values[0]]
    for i in range(1, len(values) - 1):
        running_total.append(running_total[-1] + values[i])
    running_total.append(0)  # Final bar starts at 0

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    # Draw bars
    bar_width = 0.6
    for i, (cat, val, start) in enumerate(zip(categories, values, running_total)):
        if i == 0:  # First bar
            color = COLORS['standalone']
            bottom = 0
            height = val
        elif i == len(categories) - 1:  # Last bar
            color = COLORS['deal_price']
            bottom = 0
            height = val
        else:  # Intermediate bars
            if val >= 0:
                color = COLORS['positive']
                bottom = running_total[i-1]
                height = val
            else:
                color = COLORS['negative']
                bottom = running_total[i-1] + val
                height = abs(val)

        bar = ax.bar(i, height, bar_width, bottom=bottom, color=color, alpha=0.8,
                     edgecolor='white', linewidth=2)

        # Add value labels
        label_y = bottom + height/2 if i > 0 and i < len(categories)-1 else height/2
        if i == len(categories) - 1:
            label_y = height/2
        sign = '' if val < 0 or i == 0 or i == len(categories)-1 else '+'
        ax.annotate(f'{sign}${val:.2f}',
                   xy=(i, label_y + bottom if i not in [0, len(categories)-1] else label_y),
                   ha='center', va='center', fontsize=11, fontweight='bold',
                   color='white' if i in [0, len(categories)-1] else 'black')

    # Connect bars with lines
    for i in range(len(categories) - 2):
        if i == 0:
            y_val = values[0]
        else:
            y_val = running_total[i]
        ax.plot([i + bar_width/2, i + 1 - bar_width/2],
               [y_val, y_val], 'k--', linewidth=1, alpha=0.5)

    # Add deal price reference line
    ax.axhline(y=DEAL_PRICE_PER_SHARE, color='red', linestyle='--',
              linewidth=2, alpha=0.7, label=f'Deal Price (${DEAL_PRICE_PER_SHARE})')

    # Formatting
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=30, ha='right', fontsize=11)
    ax.set_ylabel('Value per Share ($)', fontsize=12, fontweight='bold')
    ax.set_title('USS-Nippon Value Creation Bridge\n(Year 5 - Full Synergy Run-Rate)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)

    # Add grid
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Set y-axis limits
    ax.set_ylim(0, max(values) * 1.2)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Value bridge waterfall saved to: {output_path}")

    return fig


# =============================================================================
# SYNERGY RAMP CHART
# =============================================================================

def create_synergy_ramp_chart(output_path: str = None) -> plt.Figure:
    """
    Create chart showing synergy realization over time.

    Shows:
    - Cost synergies ramp
    - Technology synergies ramp
    - Revenue synergies ramp
    - Integration costs (front-loaded)
    - Net synergy impact

    Args:
        output_path: Path to save chart (optional)

    Returns:
        matplotlib Figure object
    """
    # Get value bridge for years 0-10
    years = list(range(11))
    bridge = build_multi_year_value_bridge(years=years)

    # Extract data
    year_data = [b.year for b in bridge]
    cost_syn = [b.operating_synergies for b in bridge]
    tech_syn = [b.technology_synergies for b in bridge]
    rev_syn = [b.revenue_synergies for b in bridge]
    integration = [b.integration_costs for b in bridge]

    # Calculate total synergy
    total_syn = [c + t + r for c, t, r in zip(cost_syn, tech_syn, rev_syn)]
    net_syn = [c + t + r + i for c, t, r, i in zip(cost_syn, tech_syn, rev_syn, integration)]

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Stacked area chart of synergies
    ax1.fill_between(year_data, 0, cost_syn, alpha=0.7, color=COLORS['cost_synergy'],
                     label='Cost Synergies')
    ax1.fill_between(year_data, cost_syn,
                     [c + t for c, t in zip(cost_syn, tech_syn)],
                     alpha=0.7, color=COLORS['tech_synergy'], label='Technology Synergies')
    ax1.fill_between(year_data,
                     [c + t for c, t in zip(cost_syn, tech_syn)],
                     [c + t + r for c, t, r in zip(cost_syn, tech_syn, rev_syn)],
                     alpha=0.7, color=COLORS['rev_synergy'], label='Revenue Synergies')

    ax1.set_xlabel('Year', fontsize=11)
    ax1.set_ylabel('Value per Share ($)', fontsize=11)
    ax1.set_title('Synergy Value Ramp by Category', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=10)
    ax1.set_xlim(0, 10)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Net synergy with integration costs
    ax2.bar(year_data, total_syn, alpha=0.7, color=COLORS['positive'],
            label='Gross Synergies', edgecolor='white')
    ax2.bar(year_data, integration, alpha=0.7, color=COLORS['negative'],
            label='Integration Costs', edgecolor='white')
    ax2.plot(year_data, net_syn, 'ko-', linewidth=2, markersize=6,
            label='Net Value Creation')

    ax2.set_xlabel('Year', fontsize=11)
    ax2.set_ylabel('Value per Share ($)', fontsize=11)
    ax2.set_title('Net Value Creation (Synergies - Integration Costs)', fontsize=13, fontweight='bold')
    ax2.legend(loc='upper left', fontsize=10)
    ax2.set_xlim(-0.5, 10.5)
    ax2.axhline(y=0, color='black', linewidth=1)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Synergy ramp chart saved to: {output_path}")

    return fig


# =============================================================================
# STAKEHOLDER VALUE MATRIX
# =============================================================================

def create_stakeholder_value_matrix(output_path: str = None) -> plt.Figure:
    """
    Create visualization of value by stakeholder group.

    Shows:
    - Quantified benefits per stakeholder
    - Certainty level
    - Timing

    Args:
        output_path: Path to save chart (optional)

    Returns:
        matplotlib Figure object
    """
    # Stakeholder data
    stakeholders = [
        'USS Shareholders',
        'Nippon Shareholders',
        'Employees/USW',
        'Bondholders',
        'Communities',
    ]

    # Quantified value ($B or qualitative score 1-10)
    values = [
        1.3,   # ~$4.86/share * 271M shares
        3.5,   # Synergy NPV + strategic value
        14.0,  # $14B capex commitment
        0.1,   # Spread tightening value
        38.0,  # Economic multiplier impact
    ]

    # Certainty (1-10 scale)
    certainty = [10, 6, 9, 7, 8]

    # Timing (years to realize)
    timing = [0, 5, 10, 1, 10]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))

    # Bubble chart: x=certainty, y=timing, size=value
    colors = plt.cm.Set2(np.linspace(0, 1, len(stakeholders)))

    for i, (stake, val, cert, time) in enumerate(zip(stakeholders, values, certainty, timing)):
        # Scale bubble size
        size = val * 50

        ax.scatter(cert, time, s=size, c=[colors[i]], alpha=0.6, edgecolors='black',
                  linewidth=2, label=f'{stake} (${val:.1f}B)')

        # Add label
        ax.annotate(stake, xy=(cert, time), xytext=(cert+0.3, time+0.3),
                   fontsize=10, ha='left')

    ax.set_xlabel('Certainty (1-10, 10=highest)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Years to Full Realization', fontsize=12, fontweight='bold')
    ax.set_title('Stakeholder Value Matrix\n(Bubble size = Value magnitude)',
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9, title='Value ($B)')
    ax.set_xlim(4, 11)
    ax.set_ylim(-1, 12)
    ax.grid(True, alpha=0.3)

    # Invert y-axis (0 at top = immediate value)
    ax.invert_yaxis()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Stakeholder value matrix saved to: {output_path}")

    return fig


# =============================================================================
# COMPETITIVE POSITIONING SPIDER CHART
# =============================================================================

def create_competitive_spider_chart(output_path: str = None) -> plt.Figure:
    """
    Create spider/radar chart comparing competitive positioning.

    Compares USS pre-merger, USS post-merger, Nucor, and CLF across:
    - Cost Position
    - Technology
    - Product Quality
    - Financial Strength

    Args:
        output_path: Path to save chart (optional)

    Returns:
        matplotlib Figure object
    """
    analysis = CompetitivePositioning()
    spider_data = analysis.generate_spider_chart_data()

    # Select companies to compare
    companies = ['U.S. Steel (Standalone)', 'U.S. Steel (Post-Nippon)',
                 'Nucor Corporation', 'Cleveland-Cliffs']

    # Filter data
    data = spider_data[spider_data['Company'].isin(companies)].copy()

    # Categories
    categories = ['Cost_Position', 'Technology', 'Product_Quality', 'Financial_Strength']
    category_labels = ['Cost Position', 'Technology', 'Product Quality', 'Financial Strength']

    # Number of categories
    num_vars = len(categories)

    # Compute angle for each category
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # Complete the loop

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

    # Colors for each company
    colors = ['#3498db', '#e74c3c', '#27ae60', '#f39c12']

    for idx, company in enumerate(companies):
        company_data = data[data['Company'] == company][categories].values.flatten().tolist()
        company_data += company_data[:1]  # Complete the loop

        ax.plot(angles, company_data, 'o-', linewidth=2, color=colors[idx],
               label=company, alpha=0.8)
        ax.fill(angles, company_data, color=colors[idx], alpha=0.1)

    # Set category labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(category_labels, fontsize=11)

    # Set y-axis
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9)

    # Title and legend
    ax.set_title('Competitive Positioning Comparison\n(Score 1-10, 10=Best)',
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Competitive spider chart saved to: {output_path}")

    return fig


# =============================================================================
# SYNERGY NPV BREAKDOWN CHART
# =============================================================================

def create_synergy_npv_chart(output_path: str = None) -> plt.Figure:
    """
    Create bar chart showing NPV breakdown by synergy category.

    Args:
        output_path: Path to save chart (optional)

    Returns:
        matplotlib Figure object
    """
    npv = calculate_synergy_npv()

    # Data
    categories = [
        'Cost\nSynergies',
        'Technology\nSynergies',
        'Revenue\nSynergies',
        'Strategic\nSynergies',
        'Integration\nCosts',
        'NET\nTOTAL',
    ]

    values = [
        npv['cost_synergies_npv'],
        npv['technology_synergies_npv'],
        npv['revenue_synergies_npv'],
        npv['strategic_synergies_npv'],
        npv['integration_costs_npv'],
        npv['total_synergy_npv'],
    ]

    # Colors
    colors = [
        COLORS['cost_synergy'],
        COLORS['tech_synergy'],
        COLORS['rev_synergy'],
        '#1abc9c',  # Strategic
        COLORS['negative'],
        COLORS['deal_price'],
    ]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7))

    bars = ax.bar(categories, values, color=colors, alpha=0.8,
                  edgecolor='white', linewidth=2)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        label_y = height + 50 if height > 0 else height - 150
        ax.annotate(f'${val/1000:.1f}B',
                   xy=(bar.get_x() + bar.get_width()/2, label_y),
                   ha='center', va='bottom' if height > 0 else 'top',
                   fontsize=11, fontweight='bold')

    # Formatting
    ax.axhline(y=0, color='black', linewidth=1)
    ax.set_ylabel('NPV ($M)', fontsize=12, fontweight='bold')
    ax.set_title('Synergy NPV by Category\n(10-Year DCF @ 7.5% WACC)',
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Synergy NPV chart saved to: {output_path}")

    return fig


# =============================================================================
# GENERATE ALL CHARTS
# =============================================================================

def generate_all_charts(output_dir: str = None) -> Dict[str, plt.Figure]:
    """
    Generate all value creation charts.

    Args:
        output_dir: Directory to save charts (optional)

    Returns:
        Dict mapping chart name to Figure object
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'charts'

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    charts = {}

    print("Generating value creation charts...")

    # Value bridge waterfall
    charts['value_bridge_waterfall'] = create_value_bridge_waterfall(
        output_path=str(output_dir / 'value_bridge_waterfall.png')
    )

    # Synergy ramp
    charts['synergy_ramp_chart'] = create_synergy_ramp_chart(
        output_path=str(output_dir / 'synergy_ramp_chart.png')
    )

    # Stakeholder matrix
    charts['stakeholder_value_matrix'] = create_stakeholder_value_matrix(
        output_path=str(output_dir / 'stakeholder_value_matrix.png')
    )

    # Competitive positioning
    charts['competitive_positioning'] = create_competitive_spider_chart(
        output_path=str(output_dir / 'competitive_positioning.png')
    )

    # Synergy NPV
    charts['synergy_npv_chart'] = create_synergy_npv_chart(
        output_path=str(output_dir / 'synergy_npv_chart.png')
    )

    print(f"\nAll charts saved to: {output_dir}")

    return charts


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Generate all charts."""
    charts = generate_all_charts()
    plt.close('all')  # Clean up
    return charts


if __name__ == "__main__":
    main()
