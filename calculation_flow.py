#!/usr/bin/env python3
"""
Detailed Calculation Flow
Step-by-step breakdown of how the model calculates valuations
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

# Set up the figure
fig, ax = plt.subplots(1, 1, figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis('off')

# Colors
COLOR_STEP = '#E3F2FD'
COLOR_FORMULA = '#FFF3E0'
COLOR_RESULT = '#E8F5E9'

# Title
ax.text(8, 11.5, 'Detailed Calculation Flow',
        fontsize=22, weight='bold', ha='center')
ax.text(8, 11, 'Step-by-Step Model Execution (for each year 2024-2033)',
        fontsize=12, ha='center', style='italic')

# Year loop indicator
box_year = FancyBboxPatch((0.5, 10), 15, 0.6,
                         boxstyle="round,pad=0.05",
                         edgecolor='purple', facecolor='#F3E5F5', linewidth=2)
ax.add_patch(box_year)
ax.text(8, 10.4, 'FOR EACH SEGMENT (Flat-Rolled, Mini Mill, USSE, Tubular):',
        fontsize=10, weight='bold', ha='center', color='purple')
ax.text(8, 10.15, 'FOR EACH YEAR (2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033):',
        fontsize=9, ha='center', color='purple')

# Step 1: Volume Calculation
y_pos = 9
box1 = FancyBboxPatch((0.5, y_pos), 7, 1.2,
                      boxstyle="round,pad=0.1",
                      edgecolor='black', facecolor=COLOR_STEP, linewidth=2)
ax.add_patch(box1)
ax.text(4, y_pos + 1, 'STEP 1: Calculate Volume', fontsize=10, weight='bold', ha='center')
ax.text(4, y_pos + 0.7, 'Base volume × Volume factor × Growth', fontsize=8, ha='center')

# Formula box
box1_formula = FancyBboxPatch((8.5, y_pos), 7, 1.2,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=COLOR_FORMULA, linewidth=1.5)
ax.add_patch(box1_formula)
ax.text(12, y_pos + 0.95, 'Volume (000 tons) =', fontsize=8, weight='bold', ha='center')
ax.text(12, y_pos + 0.65, 'Base_2023 × Vol_Factor × (1 + Growth_Rate)^years', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.4, '+ Project_Volume_Addition', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.1, 'Example: 8,706 × 0.98 × (1 - 0.01)^1 + 0 = 8,454 tons', fontsize=7, ha='center', style='italic')

# Arrow
arrow1 = FancyArrowPatch((8, y_pos - 0.15), (8, y_pos - 0.5),
                        arrowstyle='->', mutation_scale=25, linewidth=2)
ax.add_patch(arrow1)

# Step 2: Price Calculation
y_pos = 7.4
box2 = FancyBboxPatch((0.5, y_pos), 7, 1.2,
                      boxstyle="round,pad=0.1",
                      edgecolor='black', facecolor=COLOR_STEP, linewidth=2)
ax.add_patch(box2)
ax.text(4, y_pos + 1, 'STEP 2: Calculate Price', fontsize=10, weight='bold', ha='center')
ax.text(4, y_pos + 0.7, 'Benchmark × Price factor × Premium × Inflation', fontsize=8, ha='center')

box2_formula = FancyBboxPatch((8.5, y_pos), 7, 1.2,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=COLOR_FORMULA, linewidth=1.5)
ax.add_patch(box2_formula)
ax.text(12, y_pos + 0.95, 'Price ($/ton) =', fontsize=8, weight='bold', ha='center')
ax.text(12, y_pos + 0.65, 'Benchmark_2023 × Price_Factor × (1 + Premium)', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.4, '× (1 + Annual_Growth)^years', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.1, 'Example: $680 × 0.95 × 1.515 × (1.02)^1 = $996/ton', fontsize=7, ha='center', style='italic')

arrow2 = FancyArrowPatch((8, y_pos - 0.15), (8, y_pos - 0.5),
                        arrowstyle='->', mutation_scale=25, linewidth=2)
ax.add_patch(arrow2)

# Step 3: Revenue
y_pos = 5.8
box3 = FancyBboxPatch((0.5, y_pos), 7, 1.2,
                      boxstyle="round,pad=0.1",
                      edgecolor='black', facecolor=COLOR_STEP, linewidth=2)
ax.add_patch(box3)
ax.text(4, y_pos + 1, 'STEP 3: Calculate Revenue', fontsize=10, weight='bold', ha='center')
ax.text(4, y_pos + 0.7, 'Price × Volume (the core model equation)', fontsize=8, ha='center')

box3_formula = FancyBboxPatch((8.5, y_pos), 7, 1.2,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=COLOR_FORMULA, linewidth=1.5)
ax.add_patch(box3_formula)
ax.text(12, y_pos + 0.95, 'Revenue ($M) =', fontsize=8, weight='bold', ha='center')
ax.text(12, y_pos + 0.65, '(Volume × Price) / 1000', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.35, 'Example: (8,454 tons × $996/ton) / 1000', fontsize=7, ha='center', style='italic')
ax.text(12, y_pos + 0.05, '= $8,420M revenue', fontsize=7, ha='center', weight='bold', style='italic')

arrow3 = FancyArrowPatch((8, y_pos - 0.15), (8, y_pos - 0.5),
                        arrowstyle='->', mutation_scale=25, linewidth=2)
ax.add_patch(arrow3)

# Step 4: EBITDA
y_pos = 4.2
box4 = FancyBboxPatch((0.5, y_pos), 7, 1.2,
                      boxstyle="round,pad=0.1",
                      edgecolor='black', facecolor=COLOR_STEP, linewidth=2)
ax.add_patch(box4)
ax.text(4, y_pos + 1, 'STEP 4: Calculate EBITDA', fontsize=10, weight='bold', ha='center')
ax.text(4, y_pos + 0.7, 'Apply margin (adjusted for price level)', fontsize=8, ha='center')

box4_formula = FancyBboxPatch((8.5, y_pos), 7, 1.2,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=COLOR_FORMULA, linewidth=1.5)
ax.add_patch(box4_formula)
ax.text(12, y_pos + 0.95, 'EBITDA ($M) =', fontsize=8, weight='bold', ha='center')
ax.text(12, y_pos + 0.65, 'Margin = Base_Margin + (Price_Δ/100) × Sensitivity', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.4, 'EBITDA = Revenue × Margin + Project_EBITDA', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.1, 'Example: $8,420M × 12% + $0 = $1,010M', fontsize=7, ha='center', style='italic')

arrow4 = FancyArrowPatch((8, y_pos - 0.15), (8, y_pos - 0.5),
                        arrowstyle='->', mutation_scale=25, linewidth=2)
ax.add_patch(arrow4)

# Step 5: Free Cash Flow
y_pos = 2.6
box5 = FancyBboxPatch((0.5, y_pos), 7, 1.2,
                      boxstyle="round,pad=0.1",
                      edgecolor='black', facecolor=COLOR_STEP, linewidth=2)
ax.add_patch(box5)
ax.text(4, y_pos + 1, 'STEP 5: Calculate Free Cash Flow', fontsize=10, weight='bold', ha='center')
ax.text(4, y_pos + 0.7, 'EBITDA → NOPAT → FCF', fontsize=8, ha='center')

box5_formula = FancyBboxPatch((8.5, y_pos), 7, 1.2,
                             boxstyle="round,pad=0.05",
                             edgecolor='black', facecolor=COLOR_FORMULA, linewidth=1.5)
ax.add_patch(box5_formula)
ax.text(12, y_pos + 0.95, 'FCF ($M) =', fontsize=8, weight='bold', ha='center')
ax.text(12, y_pos + 0.7, 'NOPAT = (EBITDA - D&A) × (1 - Tax_Rate)', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.45, 'Gross_CF = NOPAT + D&A', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos + 0.2, 'FCF = Gross_CF - CapEx - Δ_WorkingCapital', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos - 0.05, 'Example: $1,010M → $839M → $463M - $378M - $12M = $73M FCF', fontsize=7, ha='center', style='italic')

arrow5 = FancyArrowPatch((8, y_pos - 0.15), (8, y_pos - 0.5),
                        arrowstyle='->', mutation_scale=25, linewidth=2)
ax.add_patch(arrow5)

# Consolidation
y_pos = 1.2
box_consol = FancyBboxPatch((2, y_pos), 12, 0.8,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=COLOR_RESULT, linewidth=3)
ax.add_patch(box_consol)
ax.text(8, y_pos + 0.6, 'CONSOLIDATE: Sum all 4 segments → Annual FCF for this year', fontsize=10, weight='bold', ha='center')
ax.text(8, y_pos + 0.3, 'Repeat for years 2024-2033 → 10-year FCF stream', fontsize=9, ha='center', style='italic')
ax.text(8, y_pos + 0.05, 'Example: Flat-Rolled $73M + Mini Mill $542M + USSE $234M + Tubular $45M = $894M total FCF', fontsize=7.5, ha='center')

arrow6 = FancyArrowPatch((8, y_pos - 0.1), (8, y_pos - 0.4),
                        arrowstyle='->', mutation_scale=25, linewidth=3)
ax.add_patch(arrow6)

# DCF Valuation
y_pos = 0.2
box_dcf = FancyBboxPatch((0.5, y_pos), 7, 0.6,
                        boxstyle="round,pad=0.05",
                        edgecolor='blue', facecolor='#E3F2FD', linewidth=2)
ax.add_patch(box_dcf)
ax.text(4, y_pos + 0.45, 'USS VALUATION', fontsize=9, weight='bold', ha='center', color='blue')
ax.text(4, y_pos + 0.2, 'PV = Σ FCF/(1+WACC)^t + TV', fontsize=7.5, ha='center', family='monospace')
ax.text(4, y_pos, 'WACC = 10.9%', fontsize=7, ha='center')

box_dcf2 = FancyBboxPatch((8.5, y_pos), 7, 0.6,
                         boxstyle="round,pad=0.05",
                         edgecolor='red', facecolor='#FFEBEE', linewidth=2)
ax.add_patch(box_dcf2)
ax.text(12, y_pos + 0.45, 'NIPPON VALUATION', fontsize=9, weight='bold', ha='center', color='red')
ax.text(12, y_pos + 0.2, 'PV = Σ FCF/(1+WACC_IRP)^t + TV', fontsize=7.5, ha='center', family='monospace')
ax.text(12, y_pos, 'WACC_IRP = 7.5% (via IRP)', fontsize=7, ha='center')

# Add key formulas sidebar
box_key = FancyBboxPatch((0.2, 5.5), 0.1, 5,
                        boxstyle="round,pad=0",
                        edgecolor='none', facecolor='#FFE082', linewidth=0, alpha=0.3)
ax.add_patch(box_key)
ax.text(0.05, 8, 'KEY\nFORMULAS', fontsize=7, weight='bold', ha='left', rotation=90, va='center')

# Add execution path indicator
box_path = FancyBboxPatch((15.7, 5.5), 0.1, 5,
                         boxstyle="round,pad=0",
                         edgecolor='none', facecolor='#81C784', linewidth=0, alpha=0.3)
ax.add_patch(box_path)
ax.text(15.95, 8, 'EXECUTION\nPATH', fontsize=7, weight='bold', ha='right', rotation=90, va='center')

plt.tight_layout()
plt.savefig('calculation_flow.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Calculation flow diagram saved as 'calculation_flow.png'")
plt.close()
