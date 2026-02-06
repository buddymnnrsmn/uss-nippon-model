"""
USS-Nippon Steel: Value Creation Analysis Module
================================================

This module provides comprehensive analysis of how the USS-Nippon merger
unlocks value for all stakeholders.

Components:
- value_creation_analysis: Core value bridge and synergy NPV calculations
- stakeholder_analysis: Stakeholder-specific return analysis
- competitive_positioning: Post-merger market position assessment
- charts: Visualization functions for value creation metrics
"""

from .value_creation_analysis import (
    ValueCreationAnalysis,
    SynergySource,
    ValueBridgeResult,
    build_value_creation_sources,
    build_multi_year_value_bridge,
    calculate_synergy_npv,
)

from .stakeholder_analysis import (
    StakeholderAnalysis,
    USSShareholderValue,
    NipponShareholderValue,
    EmployeeValue,
    BondholderValue,
    CommunityValue,
)

from .competitive_positioning import (
    CompetitivePositioning,
    CompetitorProfile,
    MarketPositionMetrics,
)

__all__ = [
    # Value Creation
    'ValueCreationAnalysis',
    'SynergySource',
    'ValueBridgeResult',
    'build_value_creation_sources',
    'build_multi_year_value_bridge',
    'calculate_synergy_npv',
    # Stakeholder Analysis
    'StakeholderAnalysis',
    'USSShareholderValue',
    'NipponShareholderValue',
    'EmployeeValue',
    'BondholderValue',
    'CommunityValue',
    # Competitive Positioning
    'CompetitivePositioning',
    'CompetitorProfile',
    'MarketPositionMetrics',
]
