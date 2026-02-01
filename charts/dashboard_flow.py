#!/usr/bin/env python3
"""
Interactive Dashboard Flow Diagram
Shows how users interact with the Streamlit dashboard
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import matplotlib.patches as mpatches

# Set up the figure
fig, ax = plt.subplots(1, 1, figsize=(18, 12))
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis('off')

# Colors
COLOR_USER = '#FFE5E5'
COLOR_SIDEBAR = '#E3F2FD'
COLOR_MAIN = '#F1F8E9'
COLOR_VIZ = '#FFF9C4'
COLOR_OUTPUT = '#E1BEE7'

# Title
ax.text(9, 11.5, 'Interactive Dashboard User Flow',
        fontsize=22, weight='bold', ha='center')
ax.text(9, 11, 'Streamlit Dashboard Architecture',
        fontsize=12, ha='center', style='italic')

# ===== USER ENTRY POINT =====
y_start = 10
user_circle = Circle((1.5, y_start), 0.4, color='#FF6B6B', ec='black', linewidth=2)
ax.add_patch(user_circle)
ax.text(1.5, y_start, 'USER', fontsize=9, weight='bold', ha='center', va='center', color='white')

arrow_entry = FancyArrowPatch((2, y_start), (4, y_start),
                             arrowstyle='->', mutation_scale=25, linewidth=2, color='black')
ax.add_patch(arrow_entry)
ax.text(3, y_start + 0.3, 'Launch', fontsize=8, ha='center')

# Entry box
box_entry = FancyBboxPatch((4, y_start - 0.5), 3, 1,
                          boxstyle="round,pad=0.1",
                          edgecolor='black', facecolor=COLOR_USER, linewidth=2)
ax.add_patch(box_entry)
ax.text(5.5, y_start + 0.3, 'RUN DASHBOARD', fontsize=10, weight='bold', ha='center')
ax.text(5.5, y_start, 'streamlit run', fontsize=8, ha='center')
ax.text(5.5, y_start - 0.25, 'interactive_dashboard.py', fontsize=7, ha='center', style='italic')

# ===== SIDEBAR CONTROLS =====
y_sidebar = 7.5

arrow_to_sidebar = FancyArrowPatch((5.5, y_start - 0.6), (3, y_sidebar + 2.5),
                                  arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow_to_sidebar)

box_sidebar = FancyBboxPatch((0.5, y_sidebar), 5, 2.3,
                            boxstyle="round,pad=0.1",
                            edgecolor='black', facecolor=COLOR_SIDEBAR, linewidth=3)
ax.add_patch(box_sidebar)
ax.text(3, y_sidebar + 2.1, 'SIDEBAR CONTROLS', fontsize=11, weight='bold', ha='center')

# Sidebar sections
sidebar_items = [
    ('1. Select Scenario', '• Base Case, Conservative, etc.'),
    ('2. Adjust Steel Prices', '• HRC, CRC, OCTG factors'),
    ('3. Modify Volumes', '• Segment volume multipliers'),
    ('4. Set WACC', '• Discount rates, terminal growth'),
    ('5. Enable Projects', '• Select capital investments'),
    ('6. Execution Factor', '• Project success rate')
]

y_item = y_sidebar + 1.7
for title, desc in sidebar_items:
    ax.text(0.8, y_item, title, fontsize=8, weight='bold')
    ax.text(1.2, y_item - 0.15, desc, fontsize=7, style='italic')
    y_item -= 0.3

# ===== MODEL ENGINE =====
y_engine = 7.5

arrow_to_engine = FancyArrowPatch((5.5, y_sidebar + 1.15), (7, y_engine + 1.15),
                                 arrowstyle='->', mutation_scale=25, linewidth=3, color='#FF6B6B')
ax.add_patch(arrow_to_engine)
ax.text(6.25, y_sidebar + 1.5, 'Parameters', fontsize=8, ha='center', color='#FF6B6B')

box_engine = FancyBboxPatch((7, y_engine), 4.5, 2.3,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=COLOR_MAIN, linewidth=3)
ax.add_patch(box_engine)
ax.text(9.25, y_engine + 2.1, 'MODEL ENGINE', fontsize=11, weight='bold', ha='center')
ax.text(9.25, y_engine + 1.8, 'PriceVolumeModel', fontsize=9, ha='center', style='italic')

engine_steps = [
    '1. Build scenario from inputs',
    '2. Calculate segment projections',
    '   • Price × Volume → Revenue',
    '   • Margins → EBITDA',
    '   • CapEx, WC → FCF',
    '3. Consolidate 4 segments',
    '4. Run dual DCF:',
    '   • USS standalone (10.9%)',
    '   • Nippon view (7.5% IRP)'
]

y_step = y_engine + 1.5
for step in engine_steps:
    ax.text(7.3, y_step, step, fontsize=7.5)
    y_step -= 0.18

# ===== VISUALIZATION LAYER =====
y_viz = 4

arrow_to_viz = FancyArrowPatch((9.25, y_engine - 0.15), (9.25, y_viz + 2.3),
                              arrowstyle='->', mutation_scale=25, linewidth=3, color='#4CAF50')
ax.add_patch(arrow_to_viz)
ax.text(9.6, 6, 'Results', fontsize=8, ha='left', color='#4CAF50')

box_viz = FancyBboxPatch((6, y_viz), 7, 2.2,
                        boxstyle="round,pad=0.1",
                        edgecolor='black', facecolor=COLOR_VIZ, linewidth=3)
ax.add_patch(box_viz)
ax.text(9.5, y_viz + 2, 'VISUALIZATION LAYER', fontsize=11, weight='bold', ha='center')

viz_items = [
    ('Charts (Plotly)', '• FCF by segment over time\n• Valuation comparison bars\n• Sensitivity curves'),
    ('Tables (Pandas)', '• Consolidated financials\n• Scenario comparison\n• Project NPV analysis'),
    ('Metrics (Streamlit)', '• Share price valuations\n• WACC advantage\n• 10Y total FCF')
]

y_viz_item = y_viz + 1.6
x_viz_cols = [6.5, 9, 11.5]
for i, (title, desc) in enumerate(viz_items):
    ax.text(x_viz_cols[i], y_viz_item, title, fontsize=8, weight='bold', ha='center')
    for j, line in enumerate(desc.split('\n')):
        ax.text(x_viz_cols[i], y_viz_item - 0.25 - j*0.15, line, fontsize=6.5, ha='center')

# ===== OUTPUT SECTIONS =====
y_out = 1.2

arrow_to_out = FancyArrowPatch((9.5, y_viz - 0.15), (9.5, y_out + 1.8),
                              arrowstyle='->', mutation_scale=25, linewidth=3, color='purple')
ax.add_patch(arrow_to_out)
ax.text(9.8, 2.5, 'Display', fontsize=8, ha='left', color='purple')

# Output sections
output_sections = [
    ('Executive\nSummary', 1.5),
    ('Valuation\nDetails', 3.5),
    ('Scenario\nComparison', 5.5),
    ('FCF\nProjection', 7.5),
    ('Segment\nAnalysis', 9.5),
    ('Sensitivity\nAnalysis', 11.5),
    ('IRP\nAdjustment', 13.5),
    ('Detailed\nTables', 15.5)
]

for title, x_pos in output_sections:
    box_out = FancyBboxPatch((x_pos - 0.8, y_out), 1.6, 1.6,
                            boxstyle="round,pad=0.05",
                            edgecolor='black', facecolor=COLOR_OUTPUT, linewidth=1.5)
    ax.add_patch(box_out)
    for i, line in enumerate(title.split('\n')):
        ax.text(x_pos, y_out + 1.2 - i*0.25, line, fontsize=7.5, weight='bold', ha='center')

# ===== FEEDBACK LOOP =====
arrow_feedback = FancyArrowPatch((1, y_out + 0.8), (1, y_sidebar - 0.15),
                                arrowstyle='->', mutation_scale=25, linewidth=2.5,
                                color='#FF9800', linestyle='dashed')
ax.add_patch(arrow_feedback)
ax.text(0.3, 4.5, 'User adjusts\nassumptions', fontsize=7, ha='center',
        color='#FF9800', weight='bold', rotation=90)

# ===== KEY FEATURES BOX =====
box_features = FancyBboxPatch((13.5, y_sidebar), 4, 2.3,
                             boxstyle="round,pad=0.1",
                             edgecolor='black', facecolor='#E8F5E9', linewidth=2)
ax.add_patch(box_features)
ax.text(15.5, y_sidebar + 2.1, 'KEY FEATURES', fontsize=10, weight='bold', ha='center')

features = [
    '✓ Real-time recalculation',
    '✓ 5+ pre-built scenarios',
    '✓ Interactive sliders',
    '✓ Dual perspective toggle',
    '✓ WACC sensitivity',
    '✓ Steel price scenarios',
    '✓ Capital project selector',
    '✓ Execution risk haircut'
]

y_feat = y_sidebar + 1.8
for feat in features:
    ax.text(13.8, y_feat, feat, fontsize=7.5)
    y_feat -= 0.23

# ===== LEGEND/NOTES =====
ax.text(0.5, 0.4, 'INTERACTION FLOW:', fontsize=9, weight='bold')
ax.text(0.5, 0.2, '1. User selects scenario and adjusts parameters in sidebar', fontsize=7)
ax.text(0.5, 0.05, '2. Model engine recalculates entire 10-year projection with new assumptions', fontsize=7)
ax.text(0.5, -0.1, '3. Visualization layer generates charts, tables, and metrics', fontsize=7)
ax.text(0.5, -0.25, '4. User reviews output sections and can iterate by adjusting sidebar controls', fontsize=7)

# Add "LIVE" indicator
live_box = FancyBboxPatch((16, 10.5), 1.5, 0.6,
                         boxstyle="round,pad=0.05",
                         edgecolor='red', facecolor='#FFEBEE', linewidth=2)
ax.add_patch(live_box)
ax.text(16.75, 10.8, 'LIVE', fontsize=10, weight='bold', ha='center', color='red')
ax.text(16.75, 10.6, 'Updates', fontsize=7, ha='center')

plt.tight_layout()
plt.savefig('dashboard_flow.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Dashboard flow diagram saved as 'dashboard_flow.png'")
plt.close()
