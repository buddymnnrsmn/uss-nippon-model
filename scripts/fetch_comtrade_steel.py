#!/usr/bin/env python3
"""
Fetch US steel import data from UN Comtrade API by HS code.

HS Codes for flat-rolled steel products:
  7208: Hot-rolled flat products, width >= 600mm
  7209: Cold-rolled flat products, width >= 600mm
  7210: Flat-rolled, plated/coated (galvanized, etc.)
  7211: Flat-rolled, width < 600mm (narrow strip)
  7212: Flat-rolled, plated/coated, width < 600mm
  7304: Seamless tubes/pipes (includes OCTG)
  7305: Other tubes/pipes >406.4mm (large welded)
  7306: Other tubes/pipes (welded, riveted)

US reporter code: 842
Partner: 0 (World aggregate)
Flow: M (imports)
"""

import json
import time
import requests
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / 'data'

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Financial Model Research)',
    'Accept': 'application/json',
})

BASE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# HS codes to fetch
HS_CODES = {
    '7208': 'HRC_flat_wide',       # Hot-rolled flat, >= 600mm
    '7209': 'CRC_flat_wide',       # Cold-rolled flat, >= 600mm
    '7210': 'Coated_flat_wide',    # Coated/galvanized flat, >= 600mm
    '7211': 'HRC_flat_narrow',     # Hot-rolled flat, < 600mm
    '7212': 'Coated_flat_narrow',  # Coated flat, < 600mm
    '7304': 'Tube_seamless',       # Seamless tubes (incl OCTG)
    '7305': 'Tube_large_welded',   # Large welded tubes
    '7306': 'Tube_other_welded',   # Other welded tubes
}

# Aggregate product categories
PRODUCT_GROUPS = {
    'HRC': ['7208', '7211'],           # Hot-rolled (wide + narrow)
    'CRC': ['7209'],                    # Cold-rolled
    'Coated': ['7210', '7212'],         # Coated/galvanized (wide + narrow)
    'Tubular': ['7304', '7305', '7306'], # All tubular
}

years = list(range(2014, 2025))
all_records = []

print("Fetching US steel import data from UN Comtrade...")
print(f"Years: {years[0]}-{years[-1]}")
print(f"HS codes: {list(HS_CODES.keys())}")
print()

for year in years:
    year_count = 0
    for hs_code, name in HS_CODES.items():
        url = f"{BASE_URL}?reporterCode=842&partnerCode=0&flowCode=M&cmdCode={hs_code}&period={year}"
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get('data', [])
                if records:
                    rec = records[0]
                    qty_kg = rec.get('qty', 0) or 0
                    net_wgt_kg = rec.get('netWgt', 0) or 0
                    value_usd = rec.get('primaryValue', 0) or 0

                    weight_kg = qty_kg if qty_kg > 0 else net_wgt_kg
                    weight_mt = weight_kg / 1000

                    all_records.append({
                        'year': year,
                        'hs_code': hs_code,
                        'product': name,
                        'weight_mt': weight_mt,
                        'value_usd': value_usd,
                        'unit_value': value_usd / weight_mt if weight_mt > 0 else 0,
                    })
                    year_count += 1
            elif resp.status_code == 429:
                print(f"  {year}/{hs_code}: Rate limited, waiting 5s...")
                time.sleep(5)
                # Retry once
                resp = session.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get('data', [])
                    if records:
                        rec = records[0]
                        qty_kg = rec.get('qty', 0) or rec.get('netWgt', 0) or 0
                        value_usd = rec.get('primaryValue', 0) or 0
                        weight_mt = qty_kg / 1000
                        all_records.append({
                            'year': year, 'hs_code': hs_code, 'product': name,
                            'weight_mt': weight_mt, 'value_usd': value_usd,
                            'unit_value': value_usd / weight_mt if weight_mt > 0 else 0,
                        })
                        year_count += 1
        except Exception as e:
            print(f"  {year}/{hs_code}: Error - {e}")

        time.sleep(1.2)  # Rate limit between requests

    yr_total = sum(r['weight_mt'] for r in all_records if r['year'] == year)
    print(f"  {year}: {year_count} codes, {yr_total/1e6:.2f}M MT total")

# Build DataFrame
df = pd.DataFrame(all_records)
if len(df) == 0:
    print("\nERROR: No data retrieved")
    exit(1)

print(f"\nTotal records: {len(df)}")

# =========================================================================
# Aggregate by product group
# =========================================================================
print("\n" + "=" * 80)
print("US STEEL IMPORTS BY PRODUCT GROUP (thousand metric tons)")
print("=" * 80)

group_data = []
for year in years:
    yr_df = df[df['year'] == year]
    row = {'year': year}
    for group_name, codes in PRODUCT_GROUPS.items():
        mask = yr_df['hs_code'].isin(codes)
        row[f'{group_name}_kt'] = yr_df.loc[mask, 'weight_mt'].sum() / 1000
        row[f'{group_name}_uv'] = (
            yr_df.loc[mask, 'value_usd'].sum() / yr_df.loc[mask, 'weight_mt'].sum()
            if yr_df.loc[mask, 'weight_mt'].sum() > 0 else 0
        )
    row['total_flat_kt'] = row['HRC_kt'] + row['CRC_kt'] + row['Coated_kt']
    group_data.append(row)

group_df = pd.DataFrame(group_data)

# Print table
print(f"\n{'Year':>6} {'HRC':>8} {'CRC':>8} {'Coated':>8} {'Flat Tot':>8} {'Tubular':>8}")
print(f"{'':>6} {'(kt)':>8} {'(kt)':>8} {'(kt)':>8} {'(kt)':>8} {'(kt)':>8}")
print("-" * 54)
for _, r in group_df.iterrows():
    print(f"{int(r['year']):>6} {r['HRC_kt']:>8.0f} {r['CRC_kt']:>8.0f} "
          f"{r['Coated_kt']:>8.0f} {r['total_flat_kt']:>8.0f} {r['Tubular_kt']:>8.0f}")

# =========================================================================
# Product mix proportions (within flat-rolled)
# =========================================================================
print("\n" + "=" * 80)
print("IMPORT PRODUCT MIX (% of flat-rolled imports)")
print("=" * 80)

print(f"\n{'Year':>6} {'HRC %':>8} {'CRC %':>8} {'Coated %':>8} {'Check':>8}")
print("-" * 42)
for _, r in group_df.iterrows():
    total = r['total_flat_kt']
    if total > 0:
        hrc_pct = r['HRC_kt'] / total * 100
        crc_pct = r['CRC_kt'] / total * 100
        coat_pct = r['Coated_kt'] / total * 100
        print(f"{int(r['year']):>6} {hrc_pct:>8.1f} {crc_pct:>8.1f} {coat_pct:>8.1f} {hrc_pct+crc_pct+coat_pct:>8.1f}")

# Average
avg_years = group_df[group_df['year'].between(2019, 2023)]
total_flat = avg_years['total_flat_kt'].sum()
print(f"\n{'Avg 19-23':>6} {avg_years['HRC_kt'].sum()/total_flat*100:>8.1f} "
      f"{avg_years['CRC_kt'].sum()/total_flat*100:>8.1f} "
      f"{avg_years['Coated_kt'].sum()/total_flat*100:>8.1f}")

avg_all = group_df[group_df['year'].between(2014, 2023)]
total_all = avg_all['total_flat_kt'].sum()
print(f"{'Avg 14-23':>6} {avg_all['HRC_kt'].sum()/total_all*100:>8.1f} "
      f"{avg_all['CRC_kt'].sum()/total_all*100:>8.1f} "
      f"{avg_all['Coated_kt'].sum()/total_all*100:>8.1f}")

# =========================================================================
# Unit values (proxy for product pricing)
# =========================================================================
print("\n" + "=" * 80)
print("IMPORT UNIT VALUES ($/metric ton)")
print("=" * 80)

print(f"\n{'Year':>6} {'HRC':>8} {'CRC':>8} {'Coated':>8} {'Tubular':>8} {'CRC/HRC':>8} {'Coat/HRC':>8}")
print("-" * 60)
for _, r in group_df.iterrows():
    crc_rat = r['CRC_uv'] / r['HRC_uv'] if r['HRC_uv'] > 0 else 0
    coat_rat = r['Coated_uv'] / r['HRC_uv'] if r['HRC_uv'] > 0 else 0
    print(f"{int(r['year']):>6} {r['HRC_uv']:>8.0f} {r['CRC_uv']:>8.0f} "
          f"{r['Coated_uv']:>8.0f} {r['Tubular_uv']:>8.0f} {crc_rat:>8.2f}x {coat_rat:>8.2f}x")

# =========================================================================
# Save raw data
# =========================================================================
df.to_csv(OUTPUT_DIR / 'us_steel_imports_comtrade.csv', index=False)
group_df.to_csv(OUTPUT_DIR / 'us_steel_imports_by_product.csv', index=False)
print(f"\nSaved: data/us_steel_imports_comtrade.csv ({len(df)} rows)")
print(f"Saved: data/us_steel_imports_by_product.csv ({len(group_df)} rows)")

# =========================================================================
# Compare with model assumptions
# =========================================================================
print("\n" + "=" * 80)
print("COMPARISON WITH MODEL SEGMENT_PRICE_MAP")
print("=" * 80)

from data.uss_segment_data import SEGMENT_PRICE_MAP

# Import mix (2019-2023 average)
imp_hrc = avg_years['HRC_kt'].sum() / total_flat
imp_crc = avg_years['CRC_kt'].sum() / total_flat
imp_coat = avg_years['Coated_kt'].sum() / total_flat

print(f"\n  Import product mix (2019-2023):")
print(f"    HRC: {imp_hrc:.1%}, CRC: {imp_crc:.1%}, Coated: {imp_coat:.1%}")
print(f"\n  Note: Import mix ≠ domestic production mix.")
print(f"  US domestic mills are MORE value-added (higher CRC+Coated share)")
print(f"  because commodity HRC is easier to import.")

print(f"\n  Model segment weights:")
for seg, weights in SEGMENT_PRICE_MAP.items():
    print(f"    {seg}: {weights}")

print(f"\n  Key insight: If imports are {imp_hrc:.0%} HRC / {imp_crc:.0%} CRC / {imp_coat:.0%} Coated,")
print(f"  domestic mills (including USS) should have LOWER HRC share and HIGHER")
print(f"  CRC+Coated share, because value-added products are harder to import.")
print(f"  This is consistent with USS Flat-Rolled model: 21% HRC / 79% CRC+Coated.")
