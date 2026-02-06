#!/usr/bin/env python3
"""
USS-Nippon Steel: Competitive Positioning Analysis
==================================================

Analyzes USS's post-merger competitive position vs:
- Nucor (largest US steelmaker)
- Cleveland-Cliffs (integrated competitor)
- ArcelorMittal (global competitor)
- Mini-mills (SDI, CMC, etc.)

Key dimensions:
- Capacity and scale
- Cost position
- Technology and products
- Financial strength
- Market position

Author: RAMBAS Team
Date: January 2025
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# Add parent directory for model imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# COMPETITOR DATA (FY2023)
# =============================================================================

@dataclass
class CompetitorProfile:
    """Financial and operational profile of a steel competitor."""
    name: str
    ticker: str

    # Scale
    us_capacity_mt: float  # Million tonnes US capacity
    global_capacity_mt: float  # Million tonnes global
    employees: int

    # Financials ($M)
    revenue_M: float
    ebitda_M: float
    net_debt_M: float

    # Cost position
    cost_quartile: int  # 1=lowest, 4=highest
    ebitda_margin: float  # %

    # Technology/Products
    technology_rating: str  # 'Leading', 'Average', 'Lagging'
    product_mix: str  # 'Commodity', 'Mixed', 'Premium'
    mini_mill_pct: float  # % capacity from EAF

    # Balance sheet
    debt_to_ebitda: float
    credit_rating: str


def get_competitor_profiles() -> Dict[str, CompetitorProfile]:
    """
    Get competitor profiles for major US/global steel players.

    Data as of FY2023.
    """
    return {
        'uss_standalone': CompetitorProfile(
            name="U.S. Steel (Standalone)",
            ticker="X",
            us_capacity_mt=22.0,
            global_capacity_mt=26.0,
            employees=22_053,
            revenue_M=18_052,
            ebitda_M=2_850,
            net_debt_M=1_200,
            cost_quartile=3,
            ebitda_margin=0.158,
            technology_rating='Lagging',
            product_mix='Mixed',
            mini_mill_pct=0.30,
            debt_to_ebitda=0.42,
            credit_rating='BB+',
        ),
        'uss_combined': CompetitorProfile(
            name="U.S. Steel (Post-Nippon)",
            ticker="X",
            us_capacity_mt=25.0,
            global_capacity_mt=75.0,  # Combined with Nippon
            employees=22_053,  # US only
            revenue_M=18_052,  # US only initially
            ebitda_M=3_300,  # With synergies
            net_debt_M=1_200,
            cost_quartile=2,  # Improved with Nippon tech
            ebitda_margin=0.183,
            technology_rating='Leading',
            product_mix='Premium',
            mini_mill_pct=0.30,
            debt_to_ebitda=0.36,
            credit_rating='A-',  # Nippon support
        ),
        'nucor': CompetitorProfile(
            name="Nucor Corporation",
            ticker="NUE",
            us_capacity_mt=27.0,
            global_capacity_mt=27.0,
            employees=32_800,
            revenue_M=34_714,
            ebitda_M=6_500,
            net_debt_M=-2_000,  # Net cash
            cost_quartile=1,
            ebitda_margin=0.187,
            technology_rating='Leading',
            product_mix='Mixed',
            mini_mill_pct=1.00,
            debt_to_ebitda=-0.31,  # Net cash
            credit_rating='A',
        ),
        'cleveland_cliffs': CompetitorProfile(
            name="Cleveland-Cliffs",
            ticker="CLF",
            us_capacity_mt=20.0,
            global_capacity_mt=20.0,
            employees=27_000,
            revenue_M=21_997,
            ebitda_M=2_100,
            net_debt_M=4_800,
            cost_quartile=2,
            ebitda_margin=0.095,
            technology_rating='Average',
            product_mix='Premium',
            mini_mill_pct=0.15,
            debt_to_ebitda=2.29,
            credit_rating='BB-',
        ),
        'arcelormittal': CompetitorProfile(
            name="ArcelorMittal",
            ticker="MT",
            us_capacity_mt=10.0,
            global_capacity_mt=68.0,
            employees=155_000,
            revenue_M=68_275,
            ebitda_M=10_200,
            net_debt_M=2_900,
            cost_quartile=2,
            ebitda_margin=0.149,
            technology_rating='Leading',
            product_mix='Mixed',
            mini_mill_pct=0.25,
            debt_to_ebitda=0.28,
            credit_rating='BBB',
        ),
        'steel_dynamics': CompetitorProfile(
            name="Steel Dynamics",
            ticker="STLD",
            us_capacity_mt=16.0,
            global_capacity_mt=16.0,
            employees=12_400,
            revenue_M=18_795,
            ebitda_M=3_200,
            net_debt_M=1_500,
            cost_quartile=1,
            ebitda_margin=0.170,
            technology_rating='Leading',
            product_mix='Mixed',
            mini_mill_pct=1.00,
            debt_to_ebitda=0.47,
            credit_rating='BBB',
        ),
    }


# =============================================================================
# MARKET POSITION METRICS
# =============================================================================

@dataclass
class MarketPositionMetrics:
    """Comprehensive market position assessment."""
    company: str
    us_market_share: float
    global_rank: int
    cost_position_score: float  # 1-10 (10=best)
    technology_score: float  # 1-10
    product_quality_score: float  # 1-10
    financial_strength_score: float  # 1-10
    overall_competitive_score: float  # Weighted average


def calculate_competitive_scores(profiles: Dict[str, CompetitorProfile]) -> Dict[str, MarketPositionMetrics]:
    """
    Calculate competitive positioning scores for each company.

    Scoring methodology:
    - Cost Position: Lower quartile = higher score
    - Technology: Based on rating + R&D investment
    - Product Quality: Based on mix and margins
    - Financial Strength: Based on leverage and ratings
    """
    total_us_capacity = sum(p.us_capacity_mt for p in profiles.values() if 'combined' not in p.name.lower())

    scores = {}

    for key, profile in profiles.items():
        # US market share
        if 'combined' in key:
            us_share = profile.us_capacity_mt / total_us_capacity
        else:
            us_share = profile.us_capacity_mt / total_us_capacity

        # Cost position score (quartile 1 = 10, quartile 4 = 2.5)
        cost_score = 10 - (profile.cost_quartile - 1) * 2.5

        # Technology score
        tech_scores = {'Leading': 9.0, 'Average': 6.0, 'Lagging': 3.0}
        tech_score = tech_scores.get(profile.technology_rating, 5.0)

        # Product quality score
        mix_scores = {'Premium': 9.0, 'Mixed': 6.0, 'Commodity': 3.0}
        quality_score = mix_scores.get(profile.product_mix, 5.0)
        # Adjust for margin
        quality_score = quality_score * (1 + (profile.ebitda_margin - 0.15) * 2)

        # Financial strength score
        if profile.debt_to_ebitda < 0:  # Net cash
            fin_score = 10.0
        elif profile.debt_to_ebitda < 1.0:
            fin_score = 9.0
        elif profile.debt_to_ebitda < 2.0:
            fin_score = 7.0
        elif profile.debt_to_ebitda < 3.0:
            fin_score = 5.0
        else:
            fin_score = 3.0

        # Adjust for credit rating
        rating_adj = {
            'A': 1.0, 'A-': 0.9, 'BBB+': 0.8, 'BBB': 0.7, 'BBB-': 0.6,
            'BB+': 0.5, 'BB': 0.4, 'BB-': 0.3, 'B+': 0.2,
        }
        fin_score *= rating_adj.get(profile.credit_rating, 0.5)

        # Overall score (weighted average)
        weights = {
            'cost': 0.30,
            'technology': 0.25,
            'quality': 0.20,
            'financial': 0.25,
        }
        overall = (
            cost_score * weights['cost'] +
            tech_score * weights['technology'] +
            quality_score * weights['quality'] +
            fin_score * weights['financial']
        )

        # Global rank (simplified)
        global_ranks = {
            'arcelormittal': 1,
            'nucor': 4,
            'uss_combined': 2,  # Combined with Nippon
            'uss_standalone': 8,
            'cleveland_cliffs': 9,
            'steel_dynamics': 10,
        }

        scores[key] = MarketPositionMetrics(
            company=profile.name,
            us_market_share=us_share,
            global_rank=global_ranks.get(key, 20),
            cost_position_score=cost_score,
            technology_score=tech_score,
            product_quality_score=quality_score,
            financial_strength_score=fin_score,
            overall_competitive_score=overall,
        )

    return scores


# =============================================================================
# COMPETITIVE POSITIONING CLASS
# =============================================================================

class CompetitivePositioning:
    """
    Analyze USS's competitive position pre- and post-merger.

    Compares across multiple dimensions:
    - Scale and capacity
    - Cost competitiveness
    - Technology and products
    - Financial strength
    """

    def __init__(self):
        """Initialize competitive positioning analysis."""
        self.profiles = get_competitor_profiles()
        self.scores = calculate_competitive_scores(self.profiles)

    def get_comparison_table(self) -> pd.DataFrame:
        """
        Generate comparison table across all competitors.

        Returns:
            DataFrame with key metrics for each competitor
        """
        data = []
        for key, profile in self.profiles.items():
            score = self.scores[key]
            data.append({
                'Company': profile.name,
                'US_Capacity_Mt': profile.us_capacity_mt,
                'Global_Capacity_Mt': profile.global_capacity_mt,
                'Revenue_$B': profile.revenue_M / 1000,
                'EBITDA_Margin': f"{profile.ebitda_margin:.1%}",
                'Cost_Quartile': f"Q{profile.cost_quartile}",
                'Technology': profile.technology_rating,
                'Debt/EBITDA': f"{profile.debt_to_ebitda:.1f}x" if profile.debt_to_ebitda > 0 else "Net Cash",
                'Credit_Rating': profile.credit_rating,
                'Overall_Score': f"{score.overall_competitive_score:.1f}",
            })

        return pd.DataFrame(data)

    def get_pre_vs_post_merger(self) -> pd.DataFrame:
        """
        Compare USS standalone vs post-merger position.

        Returns:
            DataFrame showing improvement in each dimension
        """
        pre = self.profiles['uss_standalone']
        post = self.profiles['uss_combined']
        pre_score = self.scores['uss_standalone']
        post_score = self.scores['uss_combined']

        data = [
            {
                'Metric': 'US Capacity (Mt)',
                'Pre-Merger': f"{pre.us_capacity_mt:.0f}",
                'Post-Merger': f"{post.us_capacity_mt:.0f}",
                'Change': f"+{post.us_capacity_mt - pre.us_capacity_mt:.0f}",
            },
            {
                'Metric': 'Global Capacity (Mt)',
                'Pre-Merger': f"{pre.global_capacity_mt:.0f}",
                'Post-Merger': f"{post.global_capacity_mt:.0f}",
                'Change': f"+{post.global_capacity_mt - pre.global_capacity_mt:.0f}",
            },
            {
                'Metric': 'Cost Position',
                'Pre-Merger': f"Q{pre.cost_quartile}",
                'Post-Merger': f"Q{post.cost_quartile}",
                'Change': f"Improved {pre.cost_quartile - post.cost_quartile} quartile(s)",
            },
            {
                'Metric': 'Technology',
                'Pre-Merger': pre.technology_rating,
                'Post-Merger': post.technology_rating,
                'Change': f"{pre.technology_rating} → {post.technology_rating}",
            },
            {
                'Metric': 'Product Mix',
                'Pre-Merger': pre.product_mix,
                'Post-Merger': post.product_mix,
                'Change': f"{pre.product_mix} → {post.product_mix}",
            },
            {
                'Metric': 'EBITDA Margin',
                'Pre-Merger': f"{pre.ebitda_margin:.1%}",
                'Post-Merger': f"{post.ebitda_margin:.1%}",
                'Change': f"+{(post.ebitda_margin - pre.ebitda_margin)*100:.1f}pp",
            },
            {
                'Metric': 'Credit Rating',
                'Pre-Merger': pre.credit_rating,
                'Post-Merger': post.credit_rating,
                'Change': f"{pre.credit_rating} → {post.credit_rating}",
            },
            {
                'Metric': 'Global Rank',
                'Pre-Merger': f"#{pre_score.global_rank}",
                'Post-Merger': f"#{post_score.global_rank}",
                'Change': f"+{pre_score.global_rank - post_score.global_rank} positions",
            },
            {
                'Metric': 'Overall Score',
                'Pre-Merger': f"{pre_score.overall_competitive_score:.1f}",
                'Post-Merger': f"{post_score.overall_competitive_score:.1f}",
                'Change': f"+{post_score.overall_competitive_score - pre_score.overall_competitive_score:.1f}",
            },
        ]

        return pd.DataFrame(data)

    def get_vs_nucor_comparison(self) -> Dict[str, any]:
        """
        Detailed comparison vs Nucor (largest US competitor).

        Returns:
            Dict with competitive analysis
        """
        uss = self.profiles['uss_combined']
        nucor = self.profiles['nucor']

        return {
            'scale': {
                'uss_capacity': f"{uss.us_capacity_mt:.0f} Mt",
                'nucor_capacity': f"{nucor.us_capacity_mt:.0f} Mt",
                'difference': f"{uss.us_capacity_mt - nucor.us_capacity_mt:.0f} Mt",
                'assessment': 'Comparable' if abs(uss.us_capacity_mt - nucor.us_capacity_mt) < 5 else 'Gap exists',
            },
            'cost_position': {
                'uss_quartile': f"Q{uss.cost_quartile}",
                'nucor_quartile': f"Q{nucor.cost_quartile}",
                'assessment': 'Nucor advantage (mini-mill cost structure)',
                'mitigation': 'Nippon technology can close 30-50% of gap',
            },
            'technology': {
                'uss_rating': uss.technology_rating,
                'nucor_rating': nucor.technology_rating,
                'assessment': 'Now comparable with Nippon technology',
                'uss_advantages': [
                    'Nippon AHSS grades',
                    'Japanese process control',
                    'Yield optimization',
                ],
                'nucor_advantages': [
                    'EAF flexibility',
                    'Lower capital intensity',
                    'Faster product changes',
                ],
            },
            'financial_strength': {
                'uss_leverage': f"{uss.debt_to_ebitda:.1f}x",
                'nucor_leverage': 'Net cash position',
                'uss_rating': uss.credit_rating,
                'nucor_rating': nucor.credit_rating,
                'assessment': 'Nucor advantage but USS significantly improved',
            },
            'strategic_position': {
                'uss_advantages': [
                    'Integrated model flexibility (HRC, plate)',
                    'Section 232 protection on imports',
                    'Nippon R&D pipeline',
                    'Global scale through Nippon',
                ],
                'nucor_advantages': [
                    'Best-in-class mini-mill efficiency',
                    'Decentralized culture',
                    'M&A track record',
                    'Employee ownership culture',
                ],
            },
        }

    def get_vs_cliffs_comparison(self) -> Dict[str, any]:
        """
        Detailed comparison vs Cleveland-Cliffs (integrated competitor).

        Returns:
            Dict with competitive analysis
        """
        uss = self.profiles['uss_combined']
        clf = self.profiles['cleveland_cliffs']

        return {
            'scale': {
                'uss_capacity': f"{uss.us_capacity_mt:.0f} Mt",
                'clf_capacity': f"{clf.us_capacity_mt:.0f} Mt",
                'difference': f"+{uss.us_capacity_mt - clf.us_capacity_mt:.0f} Mt",
                'assessment': 'USS larger',
            },
            'cost_position': {
                'uss_quartile': f"Q{uss.cost_quartile}",
                'clf_quartile': f"Q{clf.cost_quartile}",
                'assessment': 'Now comparable with Nippon improvements',
            },
            'financial_strength': {
                'uss_leverage': f"{uss.debt_to_ebitda:.1f}x",
                'clf_leverage': f"{clf.debt_to_ebitda:.1f}x",
                'assessment': 'USS significantly stronger',
                'implication': 'Can invest while CLF deleverages',
            },
            'automotive_focus': {
                'both_focused': 'Both heavily focused on automotive',
                'uss_advantage': 'Nippon AHSS technology and Toyota relationship',
                'clf_advantage': 'Deeper US OEM integration post-AM USA acquisition',
            },
        }

    def generate_spider_chart_data(self) -> pd.DataFrame:
        """
        Generate data for competitive positioning spider chart.

        Returns:
            DataFrame with scores by dimension for each competitor
        """
        data = []
        for key, score in self.scores.items():
            data.append({
                'Company': score.company,
                'Cost_Position': score.cost_position_score,
                'Technology': score.technology_score,
                'Product_Quality': score.product_quality_score,
                'Financial_Strength': score.financial_strength_score,
                'Overall': score.overall_competitive_score,
            })

        return pd.DataFrame(data)

    def generate_summary_report(self) -> str:
        """Generate comprehensive competitive positioning report."""
        comparison = self.get_comparison_table()
        pre_post = self.get_pre_vs_post_merger()
        vs_nucor = self.get_vs_nucor_comparison()
        vs_cliffs = self.get_vs_cliffs_comparison()

        report = f"""
{'='*80}
USS-NIPPON STEEL: COMPETITIVE POSITIONING ANALYSIS
{'='*80}

MARKET OVERVIEW
{'-'*80}
The US steel market is ~100 Mt/year capacity, dominated by:
1. Nucor: 27 Mt (mini-mill leader, lowest cost)
2. USS-Nippon: 25 Mt (integrated + mini-mill, technology leader post-merger)
3. Cleveland-Cliffs: 20 Mt (integrated, automotive focused, high leverage)
4. Steel Dynamics: 16 Mt (mini-mill, strong margins)
5. ArcelorMittal: 10 Mt US (global leader, divesting US assets)

COMPETITOR COMPARISON
{'-'*80}
{comparison.to_string(index=False)}

USS PRE-MERGER VS POST-MERGER
{'-'*80}
{pre_post.to_string(index=False)}

VS NUCOR (PRIMARY COMPETITOR)
{'-'*80}
Scale:
- USS: {vs_nucor['scale']['uss_capacity']}
- Nucor: {vs_nucor['scale']['nucor_capacity']}
- Assessment: {vs_nucor['scale']['assessment']}

Cost Position:
- USS: {vs_nucor['cost_position']['uss_quartile']}
- Nucor: {vs_nucor['cost_position']['nucor_quartile']}
- Assessment: {vs_nucor['cost_position']['assessment']}
- Mitigation: {vs_nucor['cost_position']['mitigation']}

Technology:
- USS: {vs_nucor['technology']['uss_rating']}
- Nucor: {vs_nucor['technology']['nucor_rating']}
- Assessment: {vs_nucor['technology']['assessment']}

USS Advantages with Nippon:
"""
        for adv in vs_nucor['technology']['uss_advantages']:
            report += f"  - {adv}\n"

        report += f"""
Nucor Advantages:
"""
        for adv in vs_nucor['technology']['nucor_advantages']:
            report += f"  - {adv}\n"

        report += f"""
VS CLEVELAND-CLIFFS (INTEGRATED PEER)
{'-'*80}
Scale: USS {vs_cliffs['scale']['difference']} larger
Cost: {vs_cliffs['cost_position']['assessment']}
Financial: {vs_cliffs['financial_strength']['assessment']}
  - USS leverage: {vs_cliffs['financial_strength']['uss_leverage']}
  - CLF leverage: {vs_cliffs['financial_strength']['clf_leverage']}
Implication: {vs_cliffs['financial_strength']['implication']}

COMPETITIVE POSITIONING SCORES (1-10 scale)
{'-'*80}
"""
        spider_data = self.generate_spider_chart_data()
        report += spider_data.to_string(index=False)

        report += f"""

KEY STRATEGIC IMPLICATIONS
{'-'*80}
1. SCALE: Combined USS-Nippon becomes #2 globally and competitive with Nucor in US

2. COST: Gap vs mini-mills narrowed through:
   - Nippon process technology (yield +2-3%)
   - Procurement scale across 75 Mt global network
   - Best practice sharing on energy/maintenance

3. TECHNOLOGY: Transformed from lagging to leading through:
   - Nippon's AHSS grades for automotive
   - Japanese process control and quality systems
   - Joint R&D on hydrogen/green steel

4. FINANCIAL: Significantly strengthened through:
   - Nippon's A-/A3 credit backing
   - Access to low-cost Japanese debt markets
   - $14B committed capex program

5. MARKET POSITION: From domestic player to global competitor:
   - Part of #2 global steel network
   - Better positioned for multinational OEM supply
   - Trade barrier optimization

{'='*80}
CONCLUSION: Deal transforms USS from struggling integrated producer
to globally competitive, technology-leading, financially strong platform
{'='*80}
"""
        return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Run competitive positioning analysis and print summary."""
    print("\nInitializing Competitive Positioning Analysis...")

    analysis = CompetitivePositioning()

    # Print summary report
    print(analysis.generate_summary_report())

    return analysis


if __name__ == "__main__":
    analysis = main()
