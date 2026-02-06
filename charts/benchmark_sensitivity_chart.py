#!/usr/bin/env python3
"""
Visual chart of steel price benchmark sensitivity
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, ScenarioType,
    BENCHMARK_PRICES_2023
)
import price_volume_model

# Generate data
benchmark_multipliers = [0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30]
base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]

uss_values = []
nippon_values = []
hrc_prices = []

for multiplier in benchmark_multipliers:
    modified_benchmarks = {
        key: value * multiplier
        for key, value in BENCHMARK_PRICES_2023.items()
    }

    original_benchmarks = price_volume_model.BENCHMARK_PRICES_2023.copy()
    price_volume_model.BENCHMARK_PRICES_2023.update(modified_benchmarks)

    model = PriceVolumeModel(base_scenario)
    analysis = model.run_full_analysis()

    price_volume_model.BENCHMARK_PRICES_2023.update(original_benchmarks)

    uss_values.append(analysis['val_uss']['share_price'])
    nippon_values.append(analysis['val_nippon']['share_price'])
    hrc_prices.append(modified_benchmarks['hrc_us'])

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Plot 1: Valuation vs HRC Price
ax1.plot(hrc_prices, uss_values, 'o-', linewidth=3, markersize=10,
         color='#2196F3', label='USS Standalone (10.9% WACC)')
ax1.plot(hrc_prices, nippon_values, 's-', linewidth=3, markersize=10,
         color='#F44336', label='Value to Nippon (7.5% WACC)')

# Add $55 offer line
ax1.axhline(y=55, color='green', linestyle='--', linewidth=2, alpha=0.7, label='$55 Nippon Offer')
ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

# Highlight base case
base_idx = 3  # 100% level
ax1.axvline(x=hrc_prices[base_idx], color='gray', linestyle=':', linewidth=1.5, alpha=0.5)
ax1.text(hrc_prices[base_idx], 150, '2023 Actual\n($680/ton)',
         ha='center', va='bottom', fontsize=9, color='gray')

ax1.set_xlabel('HRC Benchmark Price ($/ton)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Share Price ($)', fontsize=12, fontweight='bold')
ax1.set_title('Valuation Sensitivity to Steel Price Benchmarks', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10, loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(-20, 220)

# Add annotations for key points
ax1.annotate(f'Recession\n${uss_values[0]:.0f}',
             xy=(hrc_prices[0], uss_values[0]), xytext=(hrc_prices[0]-30, uss_values[0]+20),
             fontsize=9, ha='center',
             arrowprops=dict(arrowstyle='->', color='#2196F3', lw=1.5))
ax1.annotate(f'Base Case\n${uss_values[base_idx]:.0f}',
             xy=(hrc_prices[base_idx], uss_values[base_idx]), xytext=(hrc_prices[base_idx]+30, uss_values[base_idx]-25),
             fontsize=9, ha='center',
             arrowprops=dict(arrowstyle='->', color='#2196F3', lw=1.5))
ax1.annotate(f'Boom\n${uss_values[6]:.0f}',
             xy=(hrc_prices[6], uss_values[6]), xytext=(hrc_prices[6]+30, uss_values[6]-20),
             fontsize=9, ha='center',
             arrowprops=dict(arrowstyle='->', color='#2196F3', lw=1.5))

# Plot 2: Bar chart showing impact of ±10%
categories = ['Revenue', 'EBITDA', '10Y FCF', 'USS Value', 'Nippon Value']
down_10 = [-10.0, -32.1, -47.1, -47.2, -44.0]
up_10 = [+10.0, +37.4, +55.5, +55.6, +51.7]

x = range(len(categories))
width = 0.35

bars1 = ax2.bar([i - width/2 for i in x], down_10, width, label='-10% Price Drop',
                color='#F44336', alpha=0.7)
bars2 = ax2.bar([i + width/2 for i in x], up_10, width, label='+10% Price Increase',
                color='#4CAF50', alpha=0.7)

ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_ylabel('% Change', fontsize=12, fontweight='bold')
ax2.set_title('Impact of ±10% Steel Price Change', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(categories, fontsize=10)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}%', ha='center', va='top' if height < 0 else 'bottom',
             fontsize=9, fontweight='bold')

for bar in bars2:
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top',
             fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('benchmark_sensitivity_chart.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Benchmark sensitivity chart saved as 'benchmark_sensitivity_chart.png'")
plt.close()
