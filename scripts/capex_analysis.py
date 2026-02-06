#!/usr/bin/env python3
"""
CapEx Analysis - Show breakdown by scenario
"""

import pandas as pd
from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, ScenarioType,
    get_capital_projects
)

def analyze_capex():
    """Analyze CapEx across scenarios"""

    presets = get_scenario_presets()
    all_projects = get_capital_projects()

    print("=" * 100)
    print("CAPEX ANALYSIS BY SCENARIO")
    print("=" * 100)

    for scenario_type in [ScenarioType.BASE_CASE, ScenarioType.NIPPON_COMMITMENTS]:
        scenario = presets[scenario_type]
        model = PriceVolumeModel(scenario)
        analysis = model.run_full_analysis()

        consolidated = analysis['consolidated']
        segment_dfs = analysis['segment_dfs']

        print(f"\n{'='*100}")
        print(f"SCENARIO: {scenario.name}")
        print(f"{'='*100}")

        # Show projects included
        print(f"\nCapital Projects Included: {', '.join(scenario.include_projects) if scenario.include_projects else 'None'}")

        # Calculate maintenance vs project CapEx
        total_capex = consolidated['Total_CapEx'].sum()

        # Calculate maintenance CapEx (sum across segments)
        maintenance_capex = 0
        for seg_name, df in segment_dfs.items():
            revenue = df['Revenue'].sum()
            # Get maintenance % for this segment
            if 'Flat-Rolled' in seg_name:
                maint_pct = 0.045
            elif 'Mini Mill' in seg_name:
                maint_pct = 0.034
            elif 'USSE' in seg_name:
                maint_pct = 0.027
            elif 'Tubular' in seg_name:
                maint_pct = 0.040
            else:
                maint_pct = 0.04
            maintenance_capex += revenue * maint_pct

        project_capex = total_capex - maintenance_capex

        print(f"\n10-Year CapEx Breakdown:")
        print(f"  Total CapEx:           ${total_capex:,.0f}M")
        if total_capex > 0:
            print(f"  Maintenance CapEx:     ${maintenance_capex:,.0f}M ({maintenance_capex/total_capex*100:.1f}%)")
            print(f"  Project CapEx:         ${project_capex:,.0f}M ({project_capex/total_capex*100:.1f}%)")
        else:
            print(f"  Maintenance CapEx:     ${maintenance_capex:,.0f}M (N/A)")
            print(f"  Project CapEx:         ${project_capex:,.0f}M (N/A)")

        # Show annual CapEx by year
        print(f"\nAnnual CapEx by Year:")
        print("-" * 80)
        print(f"{'Year':<8} {'Total CapEx':<15} {'as % Revenue':<15} {'FCF':<15}")
        print("-" * 80)
        for _, row in consolidated.iterrows():
            capex_pct = row['Total_CapEx'] / row['Revenue'] * 100
            print(f"{int(row['Year']):<8} ${row['Total_CapEx']:>7,.0f}M       {capex_pct:>6.1f}%          ${row['FCF']:>7,.0f}M")

        # Show project-by-project CapEx
        if scenario.include_projects:
            print(f"\nProject-Specific CapEx:")
            print("-" * 80)
            for proj_name in scenario.include_projects:
                if proj_name in all_projects:
                    proj = all_projects[proj_name]
                    proj_total = sum(proj.capex_schedule.values())
                    print(f"  {proj_name:<25} ${proj_total:>6,.0f}M")

        print()

    # Compare maintenance intensity
    print("\n" + "=" * 100)
    print("MAINTENANCE CAPEX INTENSITY BY SEGMENT")
    print("=" * 100)

    print("\n% of Revenue required for maintenance:")
    print("  Flat-Rolled:  4.5% (highest - old blast furnaces)")
    print("  Tubular:      4.0%")
    print("  Mini Mill:    3.4%")
    print("  USSE:         2.7% (lowest)")

    print("\nInterpretation:")
    print("  - Integrated steel (Flat-Rolled) has 67% higher maintenance intensity than USSE")
    print("  - This is why USS struggles: aging assets require constant reinvestment")
    print("  - Mini mills are more capital-efficient (newer technology)")

    # Show impact on FCF
    print("\n" + "=" * 100)
    print("CAPEX IMPACT ON FREE CASH FLOW")
    print("=" * 100)

    base_scenario = presets[ScenarioType.BASE_CASE]
    base_model = PriceVolumeModel(base_scenario)
    base_analysis = base_model.run_full_analysis()
    base_cons = base_analysis['consolidated']

    print("\nBase Case (BR2 only):")
    print(f"  10Y Gross Cash Flow:   ${base_cons['Gross_CF'].sum():,.0f}M")
    print(f"  10Y Total CapEx:       ${base_cons['Total_CapEx'].sum():,.0f}M")
    print(f"  10Y Free Cash Flow:    ${base_cons['FCF'].sum():,.0f}M")
    print(f"  CapEx Consumes:        {base_cons['Total_CapEx'].sum() / base_cons['Gross_CF'].sum() * 100:.1f}% of Gross CF")

    nippon_scenario = presets[ScenarioType.NIPPON_COMMITMENTS]
    nippon_model = PriceVolumeModel(nippon_scenario)
    nippon_analysis = nippon_model.run_full_analysis()
    nippon_cons = nippon_analysis['consolidated']

    print("\nNippon Commitments (All 6 projects):")
    print(f"  10Y Gross Cash Flow:   ${nippon_cons['Gross_CF'].sum():,.0f}M")
    print(f"  10Y Total CapEx:       ${nippon_cons['Total_CapEx'].sum():,.0f}M")
    print(f"  10Y Free Cash Flow:    ${nippon_cons['FCF'].sum():,.0f}M")
    print(f"  CapEx Consumes:        {nippon_cons['Total_CapEx'].sum() / nippon_cons['Gross_CF'].sum() * 100:.1f}% of Gross CF")

    print("\nKey Insight:")
    print(f"  - Adding $14B projects increases CapEx from ${base_cons['Total_CapEx'].sum()/1000:.1f}B to ${nippon_cons['Total_CapEx'].sum()/1000:.1f}B")
    print(f"  - But EBITDA increases from ${base_cons['Total_EBITDA'].sum()/1000:.1f}B to ${nippon_cons['Total_EBITDA'].sum()/1000:.1f}B")
    print(f"  - Net effect on FCF: ${base_cons['FCF'].sum()/1000:.1f}B → ${nippon_cons['FCF'].sum()/1000:.1f}B")
    print()

if __name__ == "__main__":
    analyze_capex()
