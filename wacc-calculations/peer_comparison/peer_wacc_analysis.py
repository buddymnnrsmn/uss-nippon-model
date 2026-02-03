#!/usr/bin/env python3
"""
Steel Industry Peer WACC Analysis
=================================

Cross-sectional comparison of WACC across steel industry peers.
All data as of December 31, 2023.

Methodology:
1. Collect beta, leverage, and credit data for peers
2. Calculate implied WACC for each peer
3. Derive industry unlevered beta
4. Cross-check USS and Nippon WACC against peers

Peers Included:
- US: Nucor (NUE), Cleveland-Cliffs (CLF), Steel Dynamics (STLD)
- Global: ArcelorMittal (MT), POSCO (PKX), JFE Holdings (JFEHY)
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from base_wacc import WACCInputs, WACCCalculator


# =============================================================================
# PEER COMPANY DATA
# =============================================================================

@dataclass
class PeerCompanyData:
    """Financial data for peer WACC calculation"""
    name: str
    ticker: str
    country: str

    # Beta
    levered_beta: float
    beta_source: str

    # Capital structure (in USD millions)
    market_cap: float
    total_debt: float
    cash: float

    # Credit
    credit_rating: str
    pretax_cost_of_debt: float

    # Tax rate
    tax_rate: float

    # Market data
    risk_free_rate: float  # Domestic risk-free rate
    equity_risk_premium: float

    # Optional IRP adjustment
    irp_target_currency: Optional[str] = None
    irp_target_rf: Optional[float] = None


# US Peers (data as of 12/31/2023)
# US 10Y Treasury: 3.88% on 12/29/2023
US_RISK_FREE_RATE = 0.0388

US_STEEL_PEERS = {
    "Nucor": PeerCompanyData(
        name="Nucor Corporation",
        ticker="NUE",
        country="US",
        levered_beta=1.25,
        beta_source="Bloomberg through 12/2023",
        market_cap=47000,  # ~$47B at year-end 2023
        total_debt=5200,
        cash=4800,
        credit_rating="A-",
        pretax_cost_of_debt=0.052,  # Lower due to IG rating
        tax_rate=0.25,
        risk_free_rate=US_RISK_FREE_RATE,
        equity_risk_premium=0.055,
    ),
    "Cleveland-Cliffs": PeerCompanyData(
        name="Cleveland-Cliffs Inc",
        ticker="CLF",
        country="US",
        levered_beta=1.65,
        beta_source="Bloomberg through 12/2023",
        market_cap=10000,  # ~$10B at year-end 2023
        total_debt=5800,
        cash=400,
        credit_rating="BB-",
        pretax_cost_of_debt=0.082,  # Higher due to lower rating
        tax_rate=0.25,
        risk_free_rate=US_RISK_FREE_RATE,
        equity_risk_premium=0.055,
    ),
    "Steel Dynamics": PeerCompanyData(
        name="Steel Dynamics Inc",
        ticker="STLD",
        country="US",
        levered_beta=1.30,
        beta_source="Bloomberg through 12/2023",
        market_cap=20000,  # ~$20B at year-end 2023
        total_debt=2800,
        cash=1500,
        credit_rating="BBB",
        pretax_cost_of_debt=0.057,
        tax_rate=0.25,
        risk_free_rate=US_RISK_FREE_RATE,
        equity_risk_premium=0.055,
    ),
}

# Global Peers (data as of 12/31/2023)
GLOBAL_STEEL_PEERS = {
    "ArcelorMittal": PeerCompanyData(
        name="ArcelorMittal SA",
        ticker="MT",
        country="Luxembourg",
        levered_beta=1.50,
        beta_source="Bloomberg through 12/2023",
        market_cap=24000,  # ~$24B at year-end 2023
        total_debt=10500,
        cash=7200,
        credit_rating="BBB",
        pretax_cost_of_debt=0.050,
        tax_rate=0.25,
        risk_free_rate=0.020,  # Euro 10Y ~2.0% at year-end 2023
        equity_risk_premium=0.055,
        irp_target_currency="USD",
        irp_target_rf=US_RISK_FREE_RATE,
    ),
    "POSCO Holdings": PeerCompanyData(
        name="POSCO Holdings Inc",
        ticker="PKX",
        country="South Korea",
        levered_beta=1.20,
        beta_source="Bloomberg through 12/2023",
        market_cap=19000,
        total_debt=17500,
        cash=3500,
        credit_rating="BBB+",
        pretax_cost_of_debt=0.042,
        tax_rate=0.22,
        risk_free_rate=0.032,  # Korea 10Y ~3.2% at year-end 2023
        equity_risk_premium=0.060,
        irp_target_currency="USD",
        irp_target_rf=US_RISK_FREE_RATE,
    ),
    "JFE Holdings": PeerCompanyData(
        name="JFE Holdings Inc",
        ticker="JFEHY",
        country="Japan",
        levered_beta=1.10,
        beta_source="Bloomberg vs TOPIX through 12/2023",
        market_cap=8500,
        total_debt=8800,
        cash=1100,
        credit_rating="BBB+",
        pretax_cost_of_debt=0.014,  # JGB + spread
        tax_rate=0.30,
        risk_free_rate=0.0061,  # JGB 10Y ~0.61% at year-end 2023
        equity_risk_premium=0.055,
        irp_target_currency="USD",
        irp_target_rf=US_RISK_FREE_RATE,
    ),
}


def calculate_peer_wacc(peer: PeerCompanyData) -> Tuple[float, Dict]:
    """
    Calculate WACC for a peer company

    Returns:
        Tuple of (wacc, details_dict)
    """
    inputs = WACCInputs(
        company_name=peer.name,
        ticker=peer.ticker,
        currency="USD" if peer.country == "US" else peer.country,
        risk_free_rate=peer.risk_free_rate,
        levered_beta=peer.levered_beta,
        equity_risk_premium=peer.equity_risk_premium,
        pretax_cost_of_debt=peer.pretax_cost_of_debt,
        market_cap=peer.market_cap,
        total_debt=peer.total_debt,
        cash_and_equivalents=peer.cash,
        marginal_tax_rate=peer.tax_rate,
        credit_rating=peer.credit_rating,
    )

    calc = WACCCalculator(inputs)
    result = calc.calculate()

    wacc = result.wacc

    # Apply IRP adjustment for non-US companies
    if peer.irp_target_currency == "USD" and peer.irp_target_rf:
        wacc = calc.apply_irp_adjustment(
            domestic_rf=peer.risk_free_rate,
            foreign_rf=peer.irp_target_rf,
            target_currency="USD"
        )

    # Calculate unlevered beta
    de_ratio = peer.total_debt / peer.market_cap if peer.market_cap > 0 else 0
    unlevered_beta = peer.levered_beta / (1 + (1 - peer.tax_rate) * de_ratio)

    details = {
        'name': peer.name,
        'ticker': peer.ticker,
        'country': peer.country,
        'levered_beta': peer.levered_beta,
        'unlevered_beta': unlevered_beta,
        'debt_to_equity': de_ratio,
        'credit_rating': peer.credit_rating,
        'cost_of_equity': result.cost_of_equity,
        'cost_of_debt_at': result.aftertax_cost_of_debt,
        'equity_weight': result.equity_weight,
        'debt_weight': result.debt_weight,
        'wacc': wacc,
        'irp_adjusted': peer.irp_target_currency == "USD",
    }

    return wacc, details


def get_peer_wacc_data() -> Dict[str, Dict]:
    """
    Calculate WACC for all peers

    Returns:
        Dict mapping company name to WACC details
    """
    all_peers = {**US_STEEL_PEERS, **GLOBAL_STEEL_PEERS}
    results = {}

    for name, peer in all_peers.items():
        wacc, details = calculate_peer_wacc(peer)
        results[name] = details

    return results


def calculate_industry_wacc_range() -> Dict:
    """
    Calculate industry WACC statistics

    Returns:
        Dict with min, max, median, mean WACC and unlevered beta
    """
    peer_data = get_peer_wacc_data()

    waccs = [d['wacc'] for d in peer_data.values()]
    unlevered_betas = [d['unlevered_beta'] for d in peer_data.values()]

    # US-only for cleaner comparison
    us_waccs = [d['wacc'] for name, d in peer_data.items()
                if d['country'] == 'US']

    return {
        'all_peers': {
            'wacc_min': min(waccs),
            'wacc_max': max(waccs),
            'wacc_mean': sum(waccs) / len(waccs),
            'wacc_median': sorted(waccs)[len(waccs) // 2],
            'unlevered_beta_mean': sum(unlevered_betas) / len(unlevered_betas),
            'count': len(waccs),
        },
        'us_peers': {
            'wacc_min': min(us_waccs),
            'wacc_max': max(us_waccs),
            'wacc_mean': sum(us_waccs) / len(us_waccs),
            'count': len(us_waccs),
        },
        'peer_details': peer_data,
    }


def compare_uss_to_peers(uss_wacc: float) -> Dict:
    """
    Compare USS WACC to peer group

    Args:
        uss_wacc: USS calculated WACC

    Returns:
        Comparison results
    """
    industry = calculate_industry_wacc_range()

    return {
        'uss_wacc': uss_wacc,
        'vs_all_peers_mean': uss_wacc - industry['all_peers']['wacc_mean'],
        'vs_us_peers_mean': uss_wacc - industry['us_peers']['wacc_mean'],
        'percentile_all': _calculate_percentile(
            uss_wacc,
            [d['wacc'] for d in industry['peer_details'].values()]
        ),
        'percentile_us': _calculate_percentile(
            uss_wacc,
            [d['wacc'] for name, d in industry['peer_details'].items()
             if d['country'] == 'US']
        ),
        'industry_range': industry,
    }


def compare_nippon_to_peers(nippon_usd_wacc: float) -> Dict:
    """
    Compare Nippon USD WACC to peer group

    Args:
        nippon_usd_wacc: Nippon IRP-adjusted USD WACC

    Returns:
        Comparison results
    """
    industry = calculate_industry_wacc_range()

    # Compare to global peers (IRP-adjusted)
    global_waccs = [d['wacc'] for name, d in industry['peer_details'].items()
                   if d['country'] != 'US']

    return {
        'nippon_usd_wacc': nippon_usd_wacc,
        'vs_all_peers_mean': nippon_usd_wacc - industry['all_peers']['wacc_mean'],
        'vs_global_peers_mean': nippon_usd_wacc - (sum(global_waccs) / len(global_waccs)),
        'industry_range': industry,
    }


def _calculate_percentile(value: float, distribution: List[float]) -> float:
    """Calculate percentile of value within distribution"""
    sorted_dist = sorted(distribution)
    below = sum(1 for v in sorted_dist if v < value)
    return below / len(sorted_dist) * 100


def print_peer_comparison_table():
    """Print formatted peer comparison table"""
    peer_data = get_peer_wacc_data()

    print("=" * 90)
    print("STEEL INDUSTRY PEER WACC COMPARISON")
    print("=" * 90)
    print()
    print(f"{'Company':<25} {'Ticker':<8} {'Beta':<6} {'D/E':<6} {'Rating':<8} {'WACC':<8} {'IRP Adj'}")
    print("-" * 90)

    for name, data in sorted(peer_data.items(), key=lambda x: x[1]['wacc']):
        irp_str = "Yes" if data['irp_adjusted'] else "No"
        print(f"{data['name']:<25} {data['ticker']:<8} {data['levered_beta']:<6.2f} "
              f"{data['debt_to_equity']:<6.2f} {data['credit_rating']:<8} "
              f"{data['wacc']*100:<7.2f}% {irp_str}")

    print("-" * 90)

    industry = calculate_industry_wacc_range()
    print(f"\n{'All Peers Mean WACC:':<30} {industry['all_peers']['wacc_mean']*100:.2f}%")
    print(f"{'US Peers Mean WACC:':<30} {industry['us_peers']['wacc_mean']*100:.2f}%")
    print(f"{'Industry Unlevered Beta:':<30} {industry['all_peers']['unlevered_beta_mean']:.2f}")


# =============================================================================
# CLI / Testing
# =============================================================================

if __name__ == '__main__':
    print_peer_comparison_table()

    print("\n" + "=" * 90)
    print("USS COMPARISON")
    print("=" * 90)

    # Example USS WACC
    uss_wacc = 0.109
    comparison = compare_uss_to_peers(uss_wacc)

    print(f"\nUSS WACC: {uss_wacc*100:.2f}%")
    print(f"vs All Peers Mean: {comparison['vs_all_peers_mean']*100:+.2f}%")
    print(f"vs US Peers Mean: {comparison['vs_us_peers_mean']*100:+.2f}%")
    print(f"Percentile (All): {comparison['percentile_all']:.0f}th")
    print(f"Percentile (US): {comparison['percentile_us']:.0f}th")
