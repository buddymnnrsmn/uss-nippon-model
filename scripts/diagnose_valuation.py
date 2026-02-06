#!/usr/bin/env python3
"""Diagnostic script: decompose valuation year-by-year to verify reasonableness.

Prints EBITDA trajectory, terminal value breakdown, and implied multiples.
"""
import sys
sys.path.insert(0, '/workspaces/claude-in-docker/FinancialModel')

from price_volume_model import (
    get_scenario_presets, PriceVolumeModel, ScenarioType
)

def run_diagnostic():
    presets = get_scenario_presets()
    base = presets[ScenarioType.BASE_CASE]

    print(f"=== DIAGNOSTIC: {base.name} ===")
    print(f"WACC: {base.uss_wacc*100:.1f}%  Terminal g: {base.terminal_growth*100:.1f}%  Exit Multiple: {base.exit_multiple}x")
    print(f"Price growth: {base.price_scenario.annual_price_growth*100:.1f}%/yr")
    print(f"Projects: {base.include_projects}")
    print()

    model = PriceVolumeModel(base)
    results = model.run_full_analysis()

    # Year-by-year consolidated
    df = results['consolidated']
    print(f"{'Year':<6} {'Revenue':>10} {'EBITDA':>10} {'Margin':>8} {'FCF':>10}")
    print("-" * 50)
    for _, row in df.iterrows():
        yr = int(row['Year'])
        rev = row['Revenue']
        ebitda = row['Total_EBITDA'] if 'Total_EBITDA' in row.index else row.get('EBITDA', 0)
        margin = ebitda / rev * 100 if rev > 0 else 0
        fcf = row['FCF']
        print(f"{yr:<6} {rev:>10,.0f} {ebitda:>10,.0f} {margin:>7.1f}% {fcf:>10,.0f}")

    # Terminal year
    yr1_ebitda = df.iloc[0]['Total_EBITDA'] if 'Total_EBITDA' in df.columns else df.iloc[0].get('EBITDA', 0)
    yr10_ebitda = df.iloc[-1]['Total_EBITDA'] if 'Total_EBITDA' in df.columns else df.iloc[-1].get('EBITDA', 0)
    cagr = (yr10_ebitda / yr1_ebitda) ** (1/9) - 1 if yr1_ebitda > 0 else 0
    print(f"\nEBITDA CAGR (Yr1→Yr10): {cagr*100:.1f}%")
    print(f"Year 1 EBITDA: ${yr1_ebitda:,.0f}M  |  Year 10 EBITDA: ${yr10_ebitda:,.0f}M")

    # Valuation breakdown
    val_uss = results['val_uss']
    val_nip = results['val_nippon']

    print(f"\n=== USS STANDALONE ===")
    print(f"Sum PV FCF: ${val_uss.get('sum_pv_fcf', 0):,.0f}M")
    print(f"TV (Gordon): ${val_uss.get('tv_gordon', 0):,.0f}M")
    print(f"TV (Exit):   ${val_uss.get('tv_exit', 0):,.0f}M")
    print(f"EV (blended): ${val_uss.get('ev_blended', 0):,.0f}M")
    print(f"Share Price: ${val_uss.get('share_price', 0):.2f}")

    # Implied multiples
    ev = val_uss.get('ev_blended', 0)
    if yr10_ebitda > 0:
        print(f"Implied EV/EBITDA (on Yr10): {ev/yr10_ebitda:.1f}x")
    if yr1_ebitda > 0:
        print(f"Implied EV/EBITDA (on Yr1):  {ev/yr1_ebitda:.1f}x")

    print(f"\n=== NIPPON PERSPECTIVE ===")
    print(f"EV (blended): ${val_nip.get('ev_blended', 0):,.0f}M")
    print(f"Share Price: ${val_nip.get('share_price', 0):.2f}")

    # Segment breakdown
    print(f"\n=== SEGMENT EBITDA (Year 1 / Year 10) ===")
    for seg_name, seg_df in results['segment_dfs'].items():
        ebitda_col = 'Total_EBITDA' if 'Total_EBITDA' in seg_df.columns else 'EBITDA'
        if ebitda_col in seg_df.columns:
            e1 = seg_df.iloc[0][ebitda_col]
            e10 = seg_df.iloc[-1][ebitda_col]
            print(f"  {seg_name:<15} ${e1:>8,.0f}M → ${e10:>8,.0f}M")

    # Sensitivity: what price growth gives $39? $55?
    print(f"\n=== PRICE GROWTH SENSITIVITY ===")
    for pg in [0.0, 0.005, 0.01, 0.015, 0.02]:
        from copy import deepcopy
        test_scenario = deepcopy(base)
        test_scenario.price_scenario.annual_price_growth = pg
        test_model = PriceVolumeModel(test_scenario)
        test_results = test_model.run_full_analysis()
        sp_uss = test_results['val_uss'].get('share_price', 0)
        sp_nip = test_results['val_nippon'].get('share_price', 0)
        print(f"  Growth {pg*100:.1f}% → USS ${sp_uss:.2f}  Nippon ${sp_nip:.2f}")

if __name__ == '__main__':
    run_diagnostic()
