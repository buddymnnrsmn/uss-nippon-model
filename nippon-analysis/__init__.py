"""
Nippon Steel Financial Analysis Module

Provides comprehensive financial analysis of Nippon Steel Corporation
to assess their capacity to fund the USS acquisition.
"""

from .nippon_financial_profile import (
    NipponFinancials,
    DebtProfile,
    CreditMetrics,
    CreditRating,
    PeerCompanyData,
    NipponFinancialProfile,
    build_nippon_financial_profile,
    get_balance_sheet_summary,
    get_leverage_trend,
    get_peer_comparison_table,
    FX_RATE_JPY_USD,
    DEAL_EQUITY_PRICE,
    NSA_INVESTMENT_COMMITMENTS,
    TOTAL_CAPITAL_DEPLOYMENT,
)

from .nippon_capacity_analysis import (
    FinancingStructure,
    NSACommitmentSchedule,
    ProFormaMetrics,
    FundingGapAnalysis,
    StressTestResult,
    DealCapacityVerdict,
    create_financing_structure,
    calculate_pro_forma_metrics,
    analyze_funding_gap,
    run_stress_test,
    assess_deal_capacity,
    get_pro_forma_summary_table,
    get_stress_test_table,
    export_capacity_analysis,
)

__version__ = "1.0.0"
