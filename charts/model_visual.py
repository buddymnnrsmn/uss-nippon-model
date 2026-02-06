#!/usr/bin/env python3
"""
Visual representation of the USS/Nippon Steel Financial Model
Creates an architecture diagram showing model flow and components
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set up the figure
fig, ax = plt.subplots(1, 1, figsize=(20, 14))
ax.set_xlim(0, 20)
ax.set_ylim(0, 14)
ax.axis('off')

# Color scheme
COLOR_INPUT = '#E8F4F8'  # Light blue
COLOR_PROCESS = '#FFE8CC'  # Light orange
COLOR_OUTPUT = '#D4EDDA'  # Light green
COLOR_SCENARIO = '#F8D7DA'  # Light red
COLOR_SEGMENT = '#E2E3E5'  # Light gray

# Title
ax.text(10, 13.5, 'USS / Nippon Steel Financial Model Architecture',
        fontsize=24, weight='bold', ha='center')
ax.text(10, 13, 'Price × Volume DCF Model with IRP Adjustment',
        fontsize=14, ha='center', style='italic')

# ===== LAYER 1: INPUTS =====
y_input = 11.5

# Scenario Selection Box
box1 = FancyBboxPatch((0.5, y_input), 3.5, 1.2,
                       boxstyle="round,pad=0.1",
                       edgecolor='black', facecolor=COLOR_SCENARIO, linewidth=2)
ax.add_patch(box1)
ax.text(2.25, y_input + 0.9, 'SCENARIO SELECTION', fontsize=10, weight='bold', ha='center')
ax.text(2.25, y_input + 0.6, '• Base Case', fontsize=8, ha='center')
ax.text(2.25, y_input + 0.4, '• Conservative', fontsize=8, ha='center')
ax.text(2.25, y_input + 0.2, '• Wall Street Consensus', fontsize=8, ha='center')
ax.text(2.25, y_input, '• Management', fontsize=8, ha='center')
ax.text(2.25, y_input - 0.2, '• Nippon Commitments', fontsize=8, ha='center')

# Steel Price Inputs
box2 = FancyBboxPatch((4.5, y_input), 3, 1.2,
                       boxstyle="round,pad=0.1",
                       edgecolor='black', facecolor=COLOR_INPUT, linewidth=2)
ax.add_patch(box2)
ax.text(6, y_input + 0.9, 'STEEL PRICES', fontsize=10, weight='bold', ha='center')
ax.text(6, y_input + 0.6, 'Benchmarks (2023):', fontsize=8, ha='center')
ax.text(6, y_input + 0.35, '• HRC: $680/ton', fontsize=8, ha='center')
ax.text(6, y_input + 0.1, '• CRC: $850/ton', fontsize=8, ha='center')
ax.text(6, y_input - 0.15, '• OCTG: $2,800/ton', fontsize=8, ha='center')

# Volume Inputs
box3 = FancyBboxPatch((8, y_input), 3, 1.2,
                       boxstyle="round,pad=0.1",
                       edgecolor='black', facecolor=COLOR_INPUT, linewidth=2)
ax.add_patch(box3)
ax.text(9.5, y_input + 0.9, 'VOLUME FACTORS', fontsize=10, weight='bold', ha='center')
ax.text(9.5, y_input + 0.6, 'By Segment:', fontsize=8, ha='center')
ax.text(9.5, y_input + 0.35, '• Volume Multiplier', fontsize=8, ha='center')
ax.text(9.5, y_input + 0.1, '• Growth Rate', fontsize=8, ha='center')
ax.text(9.5, y_input - 0.15, '• Capacity Utilization', fontsize=8, ha='center')

# WACC Inputs
box4 = FancyBboxPatch((11.5, y_input), 3, 1.2,
                       boxstyle="round,pad=0.1",
                       edgecolor='black', facecolor=COLOR_INPUT, linewidth=2)
ax.add_patch(box4)
ax.text(13, y_input + 0.9, 'WACC PARAMETERS', fontsize=10, weight='bold', ha='center')
ax.text(13, y_input + 0.6, '• USS WACC: 10.9%', fontsize=8, ha='center')
ax.text(13, y_input + 0.35, '• Terminal Growth: 1%', fontsize=8, ha='center')
ax.text(13, y_input + 0.1, '• Exit Multiple: 4.5-5x', fontsize=8, ha='center')
ax.text(13, y_input - 0.15, '• US/JP 10Y Rates', fontsize=8, ha='center')

# Capital Projects
box5 = FancyBboxPatch((15, y_input), 4.5, 1.2,
                       boxstyle="round,pad=0.1",
                       edgecolor='black', facecolor=COLOR_INPUT, linewidth=2)
ax.add_patch(box5)
ax.text(17.25, y_input + 0.9, 'CAPITAL PROJECTS', fontsize=10, weight='bold', ha='center')
ax.text(17.25, y_input + 0.6, '• BR2 Mini Mill ($3B)', fontsize=8, ha='center')
ax.text(17.25, y_input + 0.35, '• Gary Works BF ($3.1B)', fontsize=8, ha='center')
ax.text(17.25, y_input + 0.1, '• Mon Valley HSM ($1B)', fontsize=8, ha='center')
ax.text(17.25, y_input - 0.15, '• Greenfield Mini Mill ($1B)', fontsize=8, ha='center')

# ===== LAYER 2: SEGMENT PROCESSING =====
y_seg = 9

# Arrow from inputs to segments
arrow1 = FancyArrowPatch((10, y_input - 0.3), (10, y_seg + 1.5),
                        arrowstyle='->', mutation_scale=30, linewidth=2, color='black')
ax.add_patch(arrow1)
ax.text(10.5, 10, 'Apply to\nSegments', fontsize=9, ha='left')

# 4 Segment boxes
segments = [
    ('FLAT-ROLLED', 2, '• 8.7M tons/year\n• $1,030/ton price\n• 12% EBITDA margin\n• Gary, Mon Valley'),
    ('MINI MILL', 6.5, '• 2.4M tons/year\n• $875/ton price\n• 20% EBITDA margin\n• Big River Steel'),
    ('USSE', 11, '• 3.9M tons/year\n• $873/ton price\n• 14% EBITDA margin\n• Slovakia ops'),
    ('TUBULAR', 15.5, '• 0.5M tons/year\n• $3,137/ton price\n• 15% EBITDA margin\n• OCTG products')
]

for seg_name, x_pos, details in segments:
    box = FancyBboxPatch((x_pos - 1.75, y_seg), 3.5, 1.3,
                         boxstyle="round,pad=0.1",
                         edgecolor='black', facecolor=COLOR_SEGMENT, linewidth=2)
    ax.add_patch(box)
    ax.text(x_pos, y_seg + 1.1, seg_name, fontsize=9, weight='bold', ha='center')
    for i, line in enumerate(details.split('\n')):
        ax.text(x_pos, y_seg + 0.8 - i*0.22, line, fontsize=7, ha='center')

# ===== LAYER 3: CALCULATIONS =====
y_calc = 6.8

# Arrow from segments to calculations
for x_pos in [2, 6.5, 11, 15.5]:
    arrow = FancyArrowPatch((x_pos, y_seg - 0.15), (x_pos, y_calc + 1.8),
                           arrowstyle='->', mutation_scale=20, linewidth=1.5, color='black')
    ax.add_patch(arrow)

# Price x Volume Calculation
box_calc1 = FancyBboxPatch((1, y_calc), 7, 1.6,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=COLOR_PROCESS, linewidth=2)
ax.add_patch(box_calc1)
ax.text(4.5, y_calc + 1.35, 'PRICE × VOLUME REVENUE MODEL', fontsize=10, weight='bold', ha='center')
ax.text(4.5, y_calc + 1.05, 'For each segment, each year (2024-2033):', fontsize=8, ha='center')
ax.text(4.5, y_calc + 0.75, '1. Calculate Volume = Base × Factor × (1 + Growth)^years + Projects', fontsize=8, ha='center')
ax.text(4.5, y_calc + 0.5, '2. Calculate Price = Benchmark × (1 + Premium) × (1 + Inflation)^years', fontsize=8, ha='center')
ax.text(4.5, y_calc + 0.25, '3. Revenue = Volume × Price', fontsize=8, ha='center')
ax.text(4.5, y_calc, '4. EBITDA = Revenue × Margin (adjusted for price level)', fontsize=8, ha='center')
ax.text(4.5, y_calc - 0.25, '5. FCF = EBITDA - D&A - Tax - CapEx - ΔWC', fontsize=8, ha='center')

# Project Impact
box_calc2 = FancyBboxPatch((12, y_calc), 7, 1.6,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=COLOR_PROCESS, linewidth=2)
ax.add_patch(box_calc2)
ax.text(15.5, y_calc + 1.35, 'CAPITAL PROJECT IMPACT', fontsize=10, weight='bold', ha='center')
ax.text(15.5, y_calc + 1.05, 'Add incremental benefits:', fontsize=8, ha='center')
ax.text(15.5, y_calc + 0.75, '• Project EBITDA by year', fontsize=8, ha='center')
ax.text(15.5, y_calc + 0.5, '• Additional volume (tons)', fontsize=8, ha='center')
ax.text(15.5, y_calc + 0.25, '• Project CapEx schedule', fontsize=8, ha='center')
ax.text(15.5, y_calc, '• Execution factor applied', fontsize=8, ha='center')
ax.text(15.5, y_calc - 0.25, '  (non-BR2 projects only)', fontsize=8, ha='center', style='italic')

# ===== LAYER 4: CONSOLIDATION =====
y_consol = 4.8

# Arrow to consolidation
arrow_consol = FancyArrowPatch((10, y_calc - 0.4), (10, y_consol + 0.6),
                              arrowstyle='->', mutation_scale=30, linewidth=2, color='black')
ax.add_patch(arrow_consol)

# Consolidated FCF
box_consol = FancyBboxPatch((7, y_consol), 6, 0.5,
                           boxstyle="round,pad=0.05",
                           edgecolor='black', facecolor=COLOR_PROCESS, linewidth=2)
ax.add_patch(box_consol)
ax.text(10, y_consol + 0.35, 'CONSOLIDATED 10-YEAR FCF PROJECTION', fontsize=10, weight='bold', ha='center')
ax.text(10, y_consol + 0.05, 'Sum all segments → Annual FCF stream (2024-2033)', fontsize=8, ha='center')

# ===== LAYER 5: DUAL VALUATION =====
y_val = 2.8

# Arrow split to two valuations
arrow_left = FancyArrowPatch((9, y_consol - 0.05), (4, y_val + 1.3),
                            arrowstyle='->', mutation_scale=25, linewidth=2, color='blue')
ax.add_patch(arrow_left)
arrow_right = FancyArrowPatch((11, y_consol - 0.05), (16, y_val + 1.3),
                             arrowstyle='->', mutation_scale=25, linewidth=2, color='red')
ax.add_patch(arrow_right)

# USS Standalone Valuation
box_uss = FancyBboxPatch((0.5, y_val), 7, 1.2,
                        boxstyle="round,pad=0.1",
                        edgecolor='blue', facecolor=COLOR_OUTPUT, linewidth=3)
ax.add_patch(box_uss)
ax.text(4, y_val + 1, 'USS STANDALONE VALUATION', fontsize=10, weight='bold', ha='center', color='blue')
ax.text(4, y_val + 0.7, 'Discount Rate: 10.9% WACC (USS cost of capital)', fontsize=8, ha='center')
ax.text(4, y_val + 0.45, '• PV of 10Y FCF + Terminal Value', fontsize=8, ha='center')
ax.text(4, y_val + 0.2, '• Financing penalty if incremental projects', fontsize=8, ha='center')
ax.text(4, y_val - 0.05, '  (debt + equity dilution)', fontsize=7, ha='center', style='italic')

# Nippon Valuation
box_nippon = FancyBboxPatch((12.5, y_val), 7, 1.2,
                           boxstyle="round,pad=0.1",
                           edgecolor='red', facecolor=COLOR_OUTPUT, linewidth=3)
ax.add_patch(box_nippon)
ax.text(16, y_val + 1, 'NIPPON VALUATION (IRP-ADJUSTED)', fontsize=10, weight='bold', ha='center', color='red')
ax.text(16, y_val + 0.7, 'Discount Rate: ~7.5% USD WACC (via IRP conversion)', fontsize=8, ha='center')
ax.text(16, y_val + 0.45, '• JPY WACC converted to USD using:', fontsize=8, ha='center')
ax.text(16, y_val + 0.2, '  WACC_USD = (1+WACC_JPY)×(1+r_US)/(1+r_JP) - 1', fontsize=7, ha='center', style='italic')
ax.text(16, y_val - 0.05, '• No financing penalty (Nippon has capacity)', fontsize=8, ha='center')

# ===== LAYER 6: FINAL OUTPUTS =====
y_out = 0.8

# Arrow to final outputs
arrow_out1 = FancyArrowPatch((4, y_val - 0.15), (4, y_out + 0.9),
                            arrowstyle='->', mutation_scale=25, linewidth=2, color='blue')
ax.add_patch(arrow_out1)
arrow_out2 = FancyArrowPatch((16, y_val - 0.15), (16, y_out + 0.9),
                            arrowstyle='->', mutation_scale=25, linewidth=2, color='red')
ax.add_patch(arrow_out2)

# Final outputs
box_out1 = FancyBboxPatch((1, y_out), 6, 0.8,
                         boxstyle="round,pad=0.1",
                         edgecolor='blue', facecolor='#E3F2FD', linewidth=2)
ax.add_patch(box_out1)
ax.text(4, y_out + 0.6, 'USS - NO SALE VALUE', fontsize=10, weight='bold', ha='center', color='blue')
ax.text(4, y_out + 0.35, 'Base Case: ~$50/share', fontsize=9, ha='center')
ax.text(4, y_out + 0.05, 'What USS is worth standalone', fontsize=7, ha='center', style='italic')

box_out2 = FancyBboxPatch((13, y_out), 6, 0.8,
                         boxstyle="round,pad=0.1",
                         edgecolor='red', facecolor='#FFEBEE', linewidth=2)
ax.add_patch(box_out2)
ax.text(16, y_out + 0.6, 'VALUE TO NIPPON', fontsize=10, weight='bold', ha='center', color='red')
ax.text(16, y_out + 0.35, 'Base Case: ~$75/share', fontsize=9, ha='center')
ax.text(16, y_out + 0.05, 'What USS is worth to Nippon (vs $55 offer)', fontsize=7, ha='center', style='italic')

# Add WACC advantage arrow
arrow_wacc = FancyArrowPatch((7.5, y_out + 0.4), (12.5, y_out + 0.4),
                            arrowstyle='<->', mutation_scale=25, linewidth=3,
                            color='green', linestyle='dashed')
ax.add_patch(arrow_wacc)
ax.text(10, y_out + 0.7, 'WACC ADVANTAGE', fontsize=9, weight='bold', ha='center', color='green')
ax.text(10, y_out + 0.5, '~3.3% lower discount rate', fontsize=7, ha='center', color='green')

# Add legend/notes at bottom
ax.text(0.5, 0.2, 'KEY INSIGHTS:', fontsize=9, weight='bold')
ax.text(0.5, 0, '• Model uses Price × Volume methodology to derive revenue bottom-up from steel market fundamentals', fontsize=7)
ax.text(0.5, -0.15, '• 4 business segments modeled separately, then consolidated for enterprise valuation', fontsize=7)
ax.text(0.5, -0.3, '• Dual perspective: USS standalone (10.9% WACC) vs. Nippon acquirer view (7.5% IRP-adjusted WACC)', fontsize=7)
ax.text(0.5, -0.45, '• WACC advantage creates ~$25/share valuation gap, explaining why deal makes sense for Nippon', fontsize=7)

plt.tight_layout()
plt.savefig('model_architecture.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Model architecture diagram saved as 'model_architecture.png'")
plt.close()
