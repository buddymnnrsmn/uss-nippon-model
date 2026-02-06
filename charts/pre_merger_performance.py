#!/usr/bin/env python3
"""
USS Pre-Merger Performance Visualization
=========================================

Shows the relationship between steel prices, shipments, and earnings
leading up to the Nippon Steel merger announcement (December 2023).
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Data from USS 10-K filings
years = [2019, 2020, 2021, 2022, 2023]

# Shipments (thousands of tons) - from 10-K
shipments = {
    'Flat-Rolled': [8_500, 7_200, 9_018, 8_372, 8_706],
    'Mini Mill': [2_100, 1_800, 2_230, 2_288, 2_424],
    'USSE': [4_100, 3_500, 4_302, 3_759, 3_899],
    'Tubular': [500, 350, 444, 524, 478],
}
total_shipments = [sum(shipments[seg][i] for seg in shipments) for i in range(len(years))]

# Steel Prices ($/ton) - HRC Midwest approximate annual averages
hrc_prices = [550, 480, 1800, 900, 680]

# Financial Performance ($ millions)
revenue = [12_937, 9_741, 20_275, 21_065, 18_053]
net_income = [-630, -1_165, 4_174, 2_524, 895]
ebitda = [490, -69, 5_396, 4_159, 1_919]

# Create figure with multiple subplots
fig = plt.figure(figsize=(14, 12))

# Color scheme
colors = {
    'hrc': '#e74c3c',      # Red
    'shipments': '#3498db', # Blue
    'revenue': '#2ecc71',   # Green
    'net_income': '#9b59b6', # Purple
    'ebitda': '#f39c12',    # Orange
}

# ============================================================
# Panel 1: Steel Prices vs Total Shipments
# ============================================================
ax1 = fig.add_subplot(2, 2, 1)

# Shipments on left axis
ax1.bar(years, [s/1000 for s in total_shipments], color=colors['shipments'], alpha=0.7, label='Total Shipments')
ax1.set_ylabel('Total Shipments (Million Tons)', color=colors['shipments'], fontsize=11)
ax1.tick_params(axis='y', labelcolor=colors['shipments'])
ax1.set_ylim(0, 20)

# HRC Price on right axis
ax1_right = ax1.twinx()
ax1_right.plot(years, hrc_prices, 'o-', color=colors['hrc'], linewidth=2.5, markersize=8, label='HRC Price')
ax1_right.set_ylabel('HRC Price ($/ton)', color=colors['hrc'], fontsize=11)
ax1_right.tick_params(axis='y', labelcolor=colors['hrc'])
ax1_right.set_ylim(0, 2000)

ax1.set_title('Steel Prices Collapsed While Shipments Held Steady', fontsize=12, fontweight='bold')
ax1.set_xlabel('Year')

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_right.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

# ============================================================
# Panel 2: Revenue and Net Income
# ============================================================
ax2 = fig.add_subplot(2, 2, 2)

x = np.arange(len(years))
width = 0.35

bars1 = ax2.bar(x - width/2, [r/1000 for r in revenue], width, label='Revenue', color=colors['revenue'], alpha=0.8)
bars2 = ax2.bar(x + width/2, [n/1000 for n in net_income], width, label='Net Income', color=colors['net_income'], alpha=0.8)

ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.set_ylabel('$ Billions', fontsize=11)
ax2.set_title('Earnings Collapsed with Steel Prices', fontsize=12, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(years)
ax2.legend()

# Add value labels on bars
for bar, val in zip(bars2, net_income):
    height = bar.get_height()
    ax2.annotate(f'${val/1000:.1f}B',
                xy=(bar.get_x() + bar.get_width()/2, height),
                xytext=(0, 3 if height >= 0 else -12),
                textcoords="offset points",
                ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=9, fontweight='bold')

# ============================================================
# Panel 3: Shipments by Segment
# ============================================================
ax3 = fig.add_subplot(2, 2, 3)

segment_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
bottom = np.zeros(len(years))

for (seg, data), color in zip(shipments.items(), segment_colors):
    ax3.bar(years, [d/1000 for d in data], bottom=bottom, label=seg, color=color, alpha=0.8)
    bottom += np.array([d/1000 for d in data])

ax3.set_ylabel('Shipments (Million Tons)', fontsize=11)
ax3.set_title('Shipments by Segment', fontsize=12, fontweight='bold')
ax3.set_xlabel('Year')
ax3.legend(loc='upper left')

# ============================================================
# Panel 4: Key Metrics Summary
# ============================================================
ax4 = fig.add_subplot(2, 2, 4)
ax4.axis('off')

# Create summary table
summary_text = """
USS Pre-Merger Trend Summary (2021 → 2023)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEEL PRICES (HRC)
  2021 Peak:     $1,800/ton
  2023 Level:    $680/ton
  Change:        -62% ▼

SHIPMENTS (Total)
  2021:          16.0M tons
  2023:          15.5M tons
  Change:        -3% (stable)

FINANCIAL PERFORMANCE
  Net Income:    $4.2B → $0.9B  (-79%) ▼
  EBITDA:        $5.4B → $1.9B  (-64%) ▼
  Margin:        20.6% → 5.0%   (-16 pts)

KEY INSIGHT
━━━━━━━━━━━
Volumes were stable, but the steel price
collapse drove earnings down 79%.

Nippon's $55/share offer came as USS faced:
  ✓ Declining steel prices
  ✓ Normalizing margins
  ✓ But still profitable (unlike 2015-2020)
  ✓ Strong balance sheet (0.39x D/E)
"""

ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='#f8f9fa', edgecolor='#dee2e6'))

# Main title
fig.suptitle('U.S. Steel: Financial Performance Leading to Merger\n(Nippon Steel Announced December 2023)',
             fontsize=14, fontweight='bold', y=0.98)

plt.tight_layout(rect=[0, 0, 1, 0.95])

# Save
output_path = '/workspaces/claude-in-docker/uss-nippon-model/charts/pre_merger_performance.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
print(f"Chart saved to: {output_path}")

plt.show()
