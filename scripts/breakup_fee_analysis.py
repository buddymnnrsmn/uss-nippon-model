#!/usr/bin/env python3
"""
Breakup Fee Analysis
Shows impact of $565M breakup fee on deal value
"""

import pandas as pd
from price_volume_model import (
    PriceVolumeModel, get_scenario_presets, ScenarioType
)

def analyze_breakup_fee():
    """Analyze breakup fee scenarios"""

    BREAKUP_FEE = 565  # $M
    SHARES_OUTSTANDING = 225  # M
    BREAKUP_FEE_PER_SHARE = BREAKUP_FEE / SHARES_OUTSTANDING
    OFFER_PRICE = 55  # $/share

    print("=" * 100)
    print("BREAKUP FEE ANALYSIS")
    print("=" * 100)
    print(f"\nBreakup Fee: ${BREAKUP_FEE:,.0f}M")
    print(f"Shares Outstanding: {SHARES_OUTSTANDING:.0f}M")
    print(f"Breakup Fee per Share: ${BREAKUP_FEE_PER_SHARE:.2f}")
    print(f"Nippon Offer: ${OFFER_PRICE:.2f}/share")

    # Get base case valuation
    base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]
    model = PriceVolumeModel(base_scenario)
    analysis = model.run_full_analysis()

    uss_standalone = analysis['val_uss']['share_price']
    nippon_view = analysis['val_nippon']['share_price']

    print("\n" + "=" * 100)
    print("SCENARIO 1: DEAL CLOSES (Most Likely)")
    print("=" * 100)
    print(f"\nUSS Shareholders Receive: ${OFFER_PRICE:.2f}/share")
    print(f"No breakup fee impact (deal closes successfully)")

    print("\n" + "=" * 100)
    print("SCENARIO 2: DEAL FAILS - USS RECEIVES BREAKUP FEE")
    print("=" * 100)
    print(f"\nTriggers:")
    print(f"  - Nippon walks away (financing failure, regulatory block)")
    print(f"  - Material adverse change on Nippon's side")
    print(f"  - Failure to obtain required approvals (not USS's fault)")
    print(f"\nUSS Outcome:")
    print(f"  Standalone Value:          ${uss_standalone:.2f}/share")
    print(f"  Plus: Breakup Fee:         +${BREAKUP_FEE_PER_SHARE:.2f}/share")
    print(f"  Adjusted Standalone Value: ${uss_standalone + BREAKUP_FEE_PER_SHARE:.2f}/share")

    print("\n" + "=" * 100)
    print("SCENARIO 3: DEAL FAILS - USS PAYS BREAKUP FEE")
    print("=" * 100)
    print(f"\nTriggers:")
    print(f"  - USS accepts superior proposal from another bidder")
    print(f"  - USS shareholders vote down the deal")
    print(f"  - USS board changes recommendation")
    print(f"\nUSS Outcome:")
    print(f"  Standalone Value:          ${uss_standalone:.2f}/share")
    print(f"  Less: Breakup Fee:         -${BREAKUP_FEE_PER_SHARE:.2f}/share")
    print(f"  Adjusted Standalone Value: ${uss_standalone - BREAKUP_FEE_PER_SHARE:.2f}/share")
    print(f"\nNote: Only relevant if USS found a better bid (>$55/share)")

    print("\n" + "=" * 100)
    print("PROBABILITY-WEIGHTED ANALYSIS")
    print("=" * 100)

    # Estimated probabilities (illustrative)
    prob_closes = 0.70
    prob_nippon_walks = 0.20
    prob_uss_walks = 0.10

    deal_value = OFFER_PRICE
    uss_gets_fee = uss_standalone + BREAKUP_FEE_PER_SHARE
    uss_pays_fee = uss_standalone - BREAKUP_FEE_PER_SHARE

    expected_value = (
        prob_closes * deal_value +
        prob_nippon_walks * uss_gets_fee +
        prob_uss_walks * uss_pays_fee
    )

    print(f"\nEstimated Probabilities:")
    print(f"  Deal Closes:            {prob_closes:.0%}")
    print(f"  Nippon Walks (USS gets fee): {prob_nippon_walks:.0%}")
    print(f"  USS Walks (USS pays fee):     {prob_uss_walks:.0%}")

    print(f"\nOutcomes:")
    print(f"  Deal Closes:            {prob_closes:.0%} × ${deal_value:.2f} = ${prob_closes * deal_value:.2f}")
    print(f"  USS Gets Fee:           {prob_nippon_walks:.0%} × ${uss_gets_fee:.2f} = ${prob_nippon_walks * uss_gets_fee:.2f}")
    print(f"  USS Pays Fee:           {prob_uss_walks:.0%} × ${uss_pays_fee:.2f} = ${prob_uss_walks * uss_pays_fee:.2f}")
    print(f"\n  Expected Value:         ${expected_value:.2f}/share")

    print("\n" + "=" * 100)
    print("DEAL COMPARISON")
    print("=" * 100)

    print(f"\nDeal Option (with breakup risk):")
    print(f"  Expected Value:         ${expected_value:.2f}/share")

    standalone_expected = uss_standalone + (prob_nippon_walks * BREAKUP_FEE_PER_SHARE)
    print(f"\nNo-Deal Option (with breakup fee upside):")
    print(f"  Standalone Value:       ${uss_standalone:.2f}/share")
    print(f"  Expected Breakup Fee:   +${prob_nippon_walks * BREAKUP_FEE_PER_SHARE:.2f}/share")
    print(f"  Expected Value:         ${standalone_expected:.2f}/share")

    spread = expected_value - standalone_expected
    if abs(standalone_expected) > 0.01:
        premium_pct = f"{spread/standalone_expected*100:+.1f}%"
    else:
        premium_pct = "N/A (standalone near zero)"
    print(f"\nDeal Premium:             ${spread:.2f}/share ({premium_pct})")

    if spread > 0:
        print(f"\nRecommendation: ACCEPT DEAL (${expected_value:.2f} > ${standalone_expected:.2f})")
    else:
        print(f"\nRecommendation: REJECT DEAL (${standalone_expected:.2f} > ${expected_value:.2f})")

    print("\n" + "=" * 100)
    print("SENSITIVITY: PROBABILITY OF DEAL CLOSING")
    print("=" * 100)

    print(f"\nHow 'expected deal value' changes with deal close probability:")
    print(f"{'P(Close)':<12} {'Expected Value':<20} {'vs No-Deal':<15}")
    print("-" * 50)

    for p_close in [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]:
        p_nippon_walk = (1 - p_close) * 0.67  # 2/3 of failures = Nippon walks
        p_uss_walk = (1 - p_close) * 0.33      # 1/3 of failures = USS walks

        ev = (
            p_close * OFFER_PRICE +
            p_nippon_walk * uss_gets_fee +
            p_uss_walk * uss_pays_fee
        )

        standalone_ev = uss_standalone + (p_nippon_walk * BREAKUP_FEE_PER_SHARE)
        diff = ev - standalone_ev

        print(f"{p_close:.0%}         ${ev:>6.2f}/share       ${diff:+6.2f}")

    print("\n" + "=" * 100)
    print("KEY INSIGHTS")
    print("=" * 100)

    print(f"\n1. Breakup Fee Impact: $2.51/share")
    print(f"   - Protects USS if Nippon walks (~20% probability)")
    print(f"   - Penalizes USS if they accept superior bid (~10% probability)")
    print(f"   - Net expected impact: +$0.25/share (0.20×$2.51 - 0.10×$2.51)")

    print(f"\n2. Deal Makes Sense Even Without Fee")
    print(f"   - $55 offer vs. $50 standalone = $5 premium")
    print(f"   - Breakup fee is secondary consideration")

    print(f"\n3. Downside Protection")
    print(f"   - If deal fails through no fault of USS: ${uss_gets_fee:.2f}/share")
    print(f"   - Only ~$3 below the $55 offer")
    print(f"   - Provides cushion if regulatory issues arise")

    print(f"\n4. Superior Proposal Economics")
    print(f"   - Another bidder would need to offer >$57.51/share")
    print(f"   - ($55 current + $2.51 breakup fee)")
    print(f"   - Sets a high bar for competing bids")

    print()

if __name__ == "__main__":
    analyze_breakup_fee()
