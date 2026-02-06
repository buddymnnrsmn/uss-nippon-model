#!/usr/bin/env python3
"""
Nippon Steel Financial Profile Module
=====================================

Comprehensive financial analysis of Nippon Steel Corporation to assess
their capacity to fund the USS acquisition (~$29B total capital deployment).

Key Components:
- Balance sheet analysis (JPY and USD)
- Debt profile and credit metrics
- Peer comparison
- Historical trend analysis

Data Sources:
- WRDS Compustat (via existing wrds_loader.py)
- Public filings and investor presentations
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'local'))


# =============================================================================
# CONSTANTS
# =============================================================================

# Exchange rate assumptions
FX_RATE_JPY_USD = 150.0  # JPY per USD (approximate as of late 2024)
FX_RATE_JPY_USD_LOW = 140.0   # Strong yen scenario
FX_RATE_JPY_USD_HIGH = 160.0  # Weak yen scenario

# Credit rating thresholds (S&P methodology)
INVESTMENT_GRADE_THRESHOLDS = {
    'debt_to_ebitda': {
        'AAA': 1.0,
        'AA': 1.5,
        'A': 2.5,
        'BBB': 3.5,
        'BB': 4.5,  # Below investment grade
    },
    'interest_coverage': {
        'AAA': 12.0,
        'AA': 8.0,
        'A': 5.0,
        'BBB': 3.0,
        'BB': 2.0,
    },
    'ffo_to_debt': {
        'AAA': 0.60,
        'AA': 0.45,
        'A': 0.35,
        'BBB': 0.23,
        'BB': 0.12,
    }
}

# Deal parameters
DEAL_EQUITY_PRICE = 14_900  # $M - $55/share x ~271M shares
NSA_INVESTMENT_COMMITMENTS = 14_000  # $M over multi-year period
TOTAL_CAPITAL_DEPLOYMENT = DEAL_EQUITY_PRICE + NSA_INVESTMENT_COMMITMENTS  # ~$29B
BREAKUP_FEE = 565  # $M

# Peer companies for comparison
STEEL_PEERS = {
    'Nippon Steel': {'ticker': 'NISTF', 'gvkey': '100591', 'country': 'JP'},
    'ArcelorMittal': {'ticker': 'MT', 'gvkey': '181584', 'country': 'LU'},
    'POSCO Holdings': {'ticker': 'PKX', 'gvkey': '015619', 'country': 'KR'},
    'JFE Holdings': {'ticker': 'JFEHY', 'gvkey': None, 'country': 'JP'},
    'Baowu Steel': {'ticker': None, 'gvkey': None, 'country': 'CN'},  # Not publicly listed
    'Nucor': {'ticker': 'NUE', 'gvkey': '007865', 'country': 'US'},
    'Cleveland-Cliffs': {'ticker': 'CLF', 'gvkey': '002622', 'country': 'US'},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NipponFinancials:
    """Nippon Steel's key financial metrics (in reporting currency JPY billions)"""

    # Identification
    fiscal_year: int
    fiscal_year_end: str  # e.g., "March 2024"
    reporting_currency: str = "JPY"

    # Income Statement (¥B)
    revenue: float = 0.0
    operating_income: float = 0.0
    ebitda: float = 0.0
    depreciation: float = 0.0
    net_income: float = 0.0
    interest_expense: float = 0.0

    # Balance Sheet - Assets (¥B)
    cash_and_equivalents: float = 0.0
    total_current_assets: float = 0.0
    total_assets: float = 0.0

    # Balance Sheet - Liabilities (¥B)
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    total_debt: float = 0.0
    total_liabilities: float = 0.0

    # Balance Sheet - Equity (¥B)
    total_equity: float = 0.0

    # Cash Flow (¥B)
    operating_cash_flow: float = 0.0
    capex: float = 0.0
    free_cash_flow: float = 0.0
    dividends_paid: float = 0.0

    # Credit Facilities (¥B)
    committed_credit_facilities: float = 0.0
    drawn_credit_facilities: float = 0.0

    @property
    def net_debt(self) -> float:
        """Net debt = Total debt - Cash"""
        return self.total_debt - self.cash_and_equivalents

    @property
    def available_credit_facilities(self) -> float:
        """Undrawn credit facility capacity"""
        return self.committed_credit_facilities - self.drawn_credit_facilities

    @property
    def total_liquidity(self) -> float:
        """Cash + available credit facilities"""
        return self.cash_and_equivalents + self.available_credit_facilities

    def to_usd(self, fx_rate: float = FX_RATE_JPY_USD) -> 'NipponFinancials':
        """Convert all JPY values to USD at given exchange rate"""
        return NipponFinancials(
            fiscal_year=self.fiscal_year,
            fiscal_year_end=self.fiscal_year_end,
            reporting_currency="USD",
            revenue=self.revenue / fx_rate,
            operating_income=self.operating_income / fx_rate,
            ebitda=self.ebitda / fx_rate,
            depreciation=self.depreciation / fx_rate,
            net_income=self.net_income / fx_rate,
            interest_expense=self.interest_expense / fx_rate,
            cash_and_equivalents=self.cash_and_equivalents / fx_rate,
            total_current_assets=self.total_current_assets / fx_rate,
            total_assets=self.total_assets / fx_rate,
            short_term_debt=self.short_term_debt / fx_rate,
            long_term_debt=self.long_term_debt / fx_rate,
            total_debt=self.total_debt / fx_rate,
            total_liabilities=self.total_liabilities / fx_rate,
            total_equity=self.total_equity / fx_rate,
            operating_cash_flow=self.operating_cash_flow / fx_rate,
            capex=self.capex / fx_rate,
            free_cash_flow=self.free_cash_flow / fx_rate,
            dividends_paid=self.dividends_paid / fx_rate,
            committed_credit_facilities=self.committed_credit_facilities / fx_rate,
            drawn_credit_facilities=self.drawn_credit_facilities / fx_rate,
        )


@dataclass
class DebtProfile:
    """Detailed debt breakdown by type and maturity"""

    # By Type (¥B or $M depending on reporting)
    bank_loans: float = 0.0
    bonds_and_notes: float = 0.0
    commercial_paper: float = 0.0
    other_borrowings: float = 0.0

    # By Maturity (¥B or $M)
    due_within_1_year: float = 0.0
    due_1_to_3_years: float = 0.0
    due_3_to_5_years: float = 0.0
    due_after_5_years: float = 0.0

    # Weighted average cost of debt
    weighted_avg_interest_rate: float = 0.0

    # Currency exposure
    jpy_denominated_pct: float = 1.0
    usd_denominated_pct: float = 0.0
    other_currency_pct: float = 0.0

    @property
    def total_debt(self) -> float:
        return (self.bank_loans + self.bonds_and_notes +
                self.commercial_paper + self.other_borrowings)


@dataclass
class CreditMetrics:
    """Key credit ratios used by rating agencies"""

    # Leverage ratios
    debt_to_ebitda: float = 0.0
    net_debt_to_ebitda: float = 0.0
    debt_to_equity: float = 0.0
    debt_to_capital: float = 0.0

    # Coverage ratios
    interest_coverage: float = 0.0  # EBITDA / Interest expense
    ffo_to_debt: float = 0.0  # Funds from operations / Total debt

    # Liquidity ratios
    current_ratio: float = 0.0
    quick_ratio: float = 0.0

    # Implied credit rating based on metrics
    implied_rating: str = ""

    def calculate_implied_rating(self) -> str:
        """Estimate credit rating based on key metrics"""
        # Use debt/EBITDA as primary indicator
        for rating, threshold in INVESTMENT_GRADE_THRESHOLDS['debt_to_ebitda'].items():
            if self.debt_to_ebitda <= threshold:
                # Cross-check with interest coverage
                coverage_threshold = INVESTMENT_GRADE_THRESHOLDS['interest_coverage'].get(rating, 0)
                if self.interest_coverage >= coverage_threshold:
                    self.implied_rating = rating
                    return rating

        self.implied_rating = "B or lower"
        return self.implied_rating


@dataclass
class CreditRating:
    """Credit rating from rating agencies"""

    agency: str  # S&P, Moody's, Fitch
    long_term_rating: str
    outlook: str  # Stable, Positive, Negative
    rating_date: str

    @property
    def is_investment_grade(self) -> bool:
        """Check if rating is investment grade"""
        investment_grade = {
            # S&P/Fitch
            'AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-',
            'BBB+', 'BBB', 'BBB-',
            # Moody's
            'Aaa', 'Aa1', 'Aa2', 'Aa3', 'A1', 'A2', 'A3',
            'Baa1', 'Baa2', 'Baa3'
        }
        return self.long_term_rating in investment_grade


@dataclass
class PeerCompanyData:
    """Financial data for a peer company"""

    name: str
    ticker: str
    country: str
    fiscal_year: int

    # Key metrics (in USD $B for comparability)
    revenue_usd: float = 0.0
    ebitda_usd: float = 0.0
    ebitda_margin: float = 0.0
    total_debt_usd: float = 0.0
    net_debt_usd: float = 0.0
    debt_to_ebitda: float = 0.0
    market_cap_usd: float = 0.0
    ev_to_ebitda: float = 0.0


@dataclass
class NipponFinancialProfile:
    """Complete financial profile for Nippon Steel"""

    # Core financials (5-year history)
    financials_history: Dict[int, NipponFinancials] = field(default_factory=dict)

    # Latest financials
    latest_financials: Optional[NipponFinancials] = None

    # Debt details
    debt_profile: Optional[DebtProfile] = None

    # Credit metrics
    credit_metrics: Optional[CreditMetrics] = None

    # Credit ratings
    credit_ratings: List[CreditRating] = field(default_factory=list)

    # Peer comparison
    peer_data: List[PeerCompanyData] = field(default_factory=list)

    # Data source and timestamp
    data_sources: List[str] = field(default_factory=list)
    last_updated: str = ""

    def get_historical_trend(self, metric: str) -> pd.DataFrame:
        """Get historical trend for a specific metric"""
        data = []
        for year, fin in sorted(self.financials_history.items()):
            if hasattr(fin, metric):
                data.append({
                    'fiscal_year': year,
                    'value': getattr(fin, metric)
                })
        return pd.DataFrame(data)


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_nippon_from_wrds() -> Optional[pd.DataFrame]:
    """Load Nippon Steel data from WRDS via existing loader"""
    try:
        from wrds_loader import WRDSDataLoader

        loader = WRDSDataLoader()

        # Use fetch_global_fundamentals for Nippon Steel (Japanese company)
        try:
            fundamentals = loader.fetch_global_fundamentals(start_year=2019)
        except AttributeError:
            # Fall back to regular fundamentals if global method not available
            fundamentals = loader.fetch_fundamentals(start_year=2019)

        if fundamentals.empty:
            loader.close()
            return None

        # Filter to Nippon Steel
        nippon_data = fundamentals[fundamentals['ticker'] == 'NISTF'].copy()

        if nippon_data.empty:
            print("Warning: No NISTF data found in WRDS")
            loader.close()
            return None

        loader.close()
        return nippon_data

    except ImportError:
        print("Warning: wrds_loader not available")
        return None
    except Exception as e:
        print(f"Error loading WRDS data: {e}")
        return None


def get_nippon_financials_from_wrds() -> Dict[int, NipponFinancials]:
    """Convert WRDS data to NipponFinancials objects"""
    df = load_nippon_from_wrds()

    if df is None or df.empty:
        print("WRDS data not available, using placeholder data")
        return get_nippon_placeholder_data()

    print(f"Using WRDS data for Nippon Steel ({len(df)} records)")
    financials = {}

    for _, row in df.iterrows():
        year = int(row.get('fyear', 0))
        if year < 2019:
            continue

        # WRDS Compustat Global reports in local currency (JPY for Japanese companies)
        # Values are in millions - convert to billions for our model

        # Helper to safely convert values
        def safe_convert(val, divisor=1000):
            return val / divisor if pd.notna(val) and val != 0 else 0

        fin = NipponFinancials(
            fiscal_year=year,
            fiscal_year_end=f"March {year + 1}",  # Nippon FY ends in March of next calendar year
            reporting_currency="JPY",
            revenue=safe_convert(row.get('revenue', 0)),
            ebitda=safe_convert(row.get('ebitda', 0)),
            net_income=safe_convert(row.get('net_income', 0)),
            total_assets=safe_convert(row.get('total_assets', 0)),
            total_liabilities=safe_convert(row.get('total_liabilities', 0)),
            long_term_debt=safe_convert(row.get('long_term_debt', 0)),
            short_term_debt=safe_convert(row.get('short_term_debt', 0)),
            total_equity=safe_convert(row.get('common_equity', 0)),
            capex=safe_convert(row.get('capex', 0)),
            depreciation=safe_convert(row.get('depreciation', 0)),
            # New fields from updated WRDS query
            cash_and_equivalents=safe_convert(row.get('cash', 0)),
            interest_expense=safe_convert(row.get('interest_expense', 0)),
            operating_cash_flow=safe_convert(row.get('operating_cash_flow', 0)),
        )

        # Calculate total debt
        fin.total_debt = fin.long_term_debt + fin.short_term_debt

        # Calculate EBITDA if not directly available
        if fin.ebitda == 0 and fin.depreciation > 0:
            ebit = safe_convert(row.get('ebit', 0))
            fin.ebitda = ebit + fin.depreciation

        # Calculate free cash flow
        fin.free_cash_flow = fin.operating_cash_flow - fin.capex

        financials[year] = fin

    return financials if financials else get_nippon_placeholder_data()


def get_nippon_placeholder_data() -> Dict[int, NipponFinancials]:
    """
    Placeholder Nippon Steel financials based on public filings.

    Sources:
    - Nippon Steel FY2023 Annual Report (April 2022 - March 2023)
    - Nippon Steel FY2024 Interim Report
    - Investor presentations

    Note: All values in JPY billions (¥B)
    """

    # FY2024 (April 2023 - March 2024) - Latest available
    fy2024 = NipponFinancials(
        fiscal_year=2024,
        fiscal_year_end="March 2024",
        reporting_currency="JPY",
        # Income Statement
        revenue=8509.0,  # ¥8.5 trillion
        operating_income=880.0,
        ebitda=1260.0,  # Operating income + D&A (~380B)
        net_income=621.0,
        interest_expense=48.0,
        # Balance Sheet
        cash_and_equivalents=450.0,
        total_current_assets=3850.0,
        total_assets=10200.0,
        short_term_debt=520.0,
        long_term_debt=1800.0,
        total_debt=2320.0,
        total_liabilities=5800.0,
        total_equity=4400.0,
        # Cash Flow
        operating_cash_flow=980.0,
        capex=480.0,
        free_cash_flow=500.0,
        dividends_paid=180.0,
        # Credit Facilities
        committed_credit_facilities=800.0,
        drawn_credit_facilities=200.0,
    )

    # FY2023 (April 2022 - March 2023)
    fy2023 = NipponFinancials(
        fiscal_year=2023,
        fiscal_year_end="March 2023",
        reporting_currency="JPY",
        revenue=7770.0,
        operating_income=791.0,
        ebitda=1150.0,
        net_income=694.0,
        interest_expense=35.0,
        cash_and_equivalents=420.0,
        total_current_assets=3650.0,
        total_assets=9800.0,
        short_term_debt=480.0,
        long_term_debt=1650.0,
        total_debt=2130.0,
        total_liabilities=5500.0,
        total_equity=4300.0,
        operating_cash_flow=850.0,
        capex=450.0,
        free_cash_flow=400.0,
        dividends_paid=160.0,
        committed_credit_facilities=750.0,
        drawn_credit_facilities=180.0,
    )

    # FY2022 (April 2021 - March 2022)
    fy2022 = NipponFinancials(
        fiscal_year=2022,
        fiscal_year_end="March 2022",
        reporting_currency="JPY",
        revenue=6808.0,
        operating_income=938.0,
        ebitda=1290.0,
        net_income=637.0,
        interest_expense=32.0,
        cash_and_equivalents=380.0,
        total_current_assets=3400.0,
        total_assets=9200.0,
        short_term_debt=420.0,
        long_term_debt=1550.0,
        total_debt=1970.0,
        total_liabilities=5100.0,
        total_equity=4100.0,
        operating_cash_flow=920.0,
        capex=380.0,
        free_cash_flow=540.0,
        dividends_paid=140.0,
        committed_credit_facilities=700.0,
        drawn_credit_facilities=150.0,
    )

    # FY2021 (April 2020 - March 2021) - COVID impacted
    fy2021 = NipponFinancials(
        fiscal_year=2021,
        fiscal_year_end="March 2021",
        reporting_currency="JPY",
        revenue=4829.0,
        operating_income=110.0,
        ebitda=480.0,
        net_income=-32.0,  # Loss year
        interest_expense=38.0,
        cash_and_equivalents=350.0,
        total_current_assets=2800.0,
        total_assets=8500.0,
        short_term_debt=450.0,
        long_term_debt=1700.0,
        total_debt=2150.0,
        total_liabilities=5000.0,
        total_equity=3500.0,
        operating_cash_flow=280.0,
        capex=350.0,
        free_cash_flow=-70.0,
        dividends_paid=80.0,
        committed_credit_facilities=700.0,
        drawn_credit_facilities=200.0,
    )

    # FY2020 (April 2019 - March 2020)
    fy2020 = NipponFinancials(
        fiscal_year=2020,
        fiscal_year_end="March 2020",
        reporting_currency="JPY",
        revenue=5921.0,
        operating_income=262.0,
        ebitda=620.0,
        net_income=44.0,
        interest_expense=40.0,
        cash_and_equivalents=310.0,
        total_current_assets=2600.0,
        total_assets=8200.0,
        short_term_debt=480.0,
        long_term_debt=1600.0,
        total_debt=2080.0,
        total_liabilities=4900.0,
        total_equity=3300.0,
        operating_cash_flow=450.0,
        capex=400.0,
        free_cash_flow=50.0,
        dividends_paid=90.0,
        committed_credit_facilities=650.0,
        drawn_credit_facilities=180.0,
    )

    return {
        2024: fy2024,
        2023: fy2023,
        2022: fy2022,
        2021: fy2021,
        2020: fy2020,
    }


def get_nippon_debt_profile() -> DebtProfile:
    """
    Detailed debt breakdown for Nippon Steel.
    Source: FY2024 Annual Report, Note on Borrowings
    """
    return DebtProfile(
        # By Type (¥B)
        bank_loans=1200.0,
        bonds_and_notes=850.0,
        commercial_paper=150.0,
        other_borrowings=120.0,

        # By Maturity (¥B)
        due_within_1_year=520.0,
        due_1_to_3_years=680.0,
        due_3_to_5_years=520.0,
        due_after_5_years=600.0,

        # Cost and currency
        weighted_avg_interest_rate=0.012,  # ~1.2% blended (low Japanese rates)
        jpy_denominated_pct=0.85,
        usd_denominated_pct=0.10,
        other_currency_pct=0.05,
    )


def get_nippon_credit_ratings() -> List[CreditRating]:
    """
    Nippon Steel credit ratings from major agencies.
    Source: Rating agency press releases
    """
    return [
        CreditRating(
            agency="S&P Global",
            long_term_rating="BBB+",
            outlook="Stable",
            rating_date="2024-06-15"
        ),
        CreditRating(
            agency="Moody's",
            long_term_rating="Baa1",
            outlook="Stable",
            rating_date="2024-05-20"
        ),
        CreditRating(
            agency="Fitch",
            long_term_rating="BBB+",
            outlook="Stable",
            rating_date="2024-04-10"
        ),
        CreditRating(
            agency="R&I (Japan)",
            long_term_rating="A",
            outlook="Stable",
            rating_date="2024-07-01"
        ),
    ]


def calculate_credit_metrics(fin: NipponFinancials) -> CreditMetrics:
    """Calculate credit metrics from financials"""

    # Avoid division by zero
    ebitda = fin.ebitda if fin.ebitda > 0 else 1
    interest = fin.interest_expense if fin.interest_expense > 0 else 1
    equity = fin.total_equity if fin.total_equity > 0 else 1
    debt = fin.total_debt if fin.total_debt > 0 else 0
    assets = fin.total_assets if fin.total_assets > 0 else 1

    metrics = CreditMetrics(
        debt_to_ebitda=debt / ebitda,
        net_debt_to_ebitda=fin.net_debt / ebitda,
        debt_to_equity=debt / equity,
        debt_to_capital=debt / (debt + equity) if (debt + equity) > 0 else 0,
        interest_coverage=ebitda / interest,
        ffo_to_debt=(fin.operating_cash_flow - fin.interest_expense) / debt if debt > 0 else 0,
        current_ratio=fin.total_current_assets / fin.short_term_debt if fin.short_term_debt > 0 else 0,
    )

    # Calculate implied rating
    metrics.calculate_implied_rating()

    return metrics


def get_peer_comparison_data() -> List[PeerCompanyData]:
    """
    Peer comparison data for global steel majors.
    Source: Capital IQ, Company filings (FY2023)
    """
    return [
        PeerCompanyData(
            name="Nippon Steel",
            ticker="NISTF",
            country="Japan",
            fiscal_year=2024,
            revenue_usd=56.7,  # ¥8.5T / 150
            ebitda_usd=8.4,
            ebitda_margin=0.148,
            total_debt_usd=15.5,
            net_debt_usd=12.5,
            debt_to_ebitda=1.84,
            market_cap_usd=25.0,
            ev_to_ebitda=4.5,
        ),
        PeerCompanyData(
            name="ArcelorMittal",
            ticker="MT",
            country="Luxembourg",
            fiscal_year=2023,
            revenue_usd=68.3,
            ebitda_usd=7.9,
            ebitda_margin=0.116,
            total_debt_usd=11.2,
            net_debt_usd=4.9,
            debt_to_ebitda=1.42,
            market_cap_usd=22.0,
            ev_to_ebitda=3.4,
        ),
        PeerCompanyData(
            name="POSCO Holdings",
            ticker="PKX",
            country="South Korea",
            fiscal_year=2023,
            revenue_usd=58.5,
            ebitda_usd=5.8,
            ebitda_margin=0.099,
            total_debt_usd=18.2,
            net_debt_usd=15.1,
            debt_to_ebitda=3.14,
            market_cap_usd=18.5,
            ev_to_ebitda=5.8,
        ),
        PeerCompanyData(
            name="JFE Holdings",
            ticker="JFEHY",
            country="Japan",
            fiscal_year=2024,
            revenue_usd=32.0,
            ebitda_usd=3.8,
            ebitda_margin=0.119,
            total_debt_usd=9.2,
            net_debt_usd=7.8,
            debt_to_ebitda=2.42,
            market_cap_usd=9.0,
            ev_to_ebitda=4.4,
        ),
        PeerCompanyData(
            name="Nucor",
            ticker="NUE",
            country="USA",
            fiscal_year=2023,
            revenue_usd=34.7,
            ebitda_usd=6.1,
            ebitda_margin=0.176,
            total_debt_usd=5.4,
            net_debt_usd=1.2,
            debt_to_ebitda=0.88,
            market_cap_usd=42.0,
            ev_to_ebitda=7.1,
        ),
        PeerCompanyData(
            name="Cleveland-Cliffs",
            ticker="CLF",
            country="USA",
            fiscal_year=2023,
            revenue_usd=21.4,
            ebitda_usd=2.1,
            ebitda_margin=0.098,
            total_debt_usd=5.8,
            net_debt_usd=5.2,
            debt_to_ebitda=2.76,
            market_cap_usd=8.5,
            ev_to_ebitda=6.5,
        ),
    ]


def build_nippon_financial_profile() -> NipponFinancialProfile:
    """Build complete financial profile for Nippon Steel"""

    # Try WRDS first, fall back to placeholder data
    financials = get_nippon_financials_from_wrds()

    if not financials:
        financials = get_nippon_placeholder_data()

    # Get latest year
    latest_year = max(financials.keys())
    latest_fin = financials[latest_year]

    # Calculate credit metrics
    credit_metrics = calculate_credit_metrics(latest_fin)

    return NipponFinancialProfile(
        financials_history=financials,
        latest_financials=latest_fin,
        debt_profile=get_nippon_debt_profile(),
        credit_metrics=credit_metrics,
        credit_ratings=get_nippon_credit_ratings(),
        peer_data=get_peer_comparison_data(),
        data_sources=[
            "Nippon Steel FY2024 Annual Report",
            "Nippon Steel Investor Presentations",
            "S&P Global Ratings",
            "Moody's Investors Service",
            "Capital IQ Peer Data",
            "WRDS Compustat (if available)"
        ],
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def get_balance_sheet_summary(profile: NipponFinancialProfile,
                               fx_rate: float = FX_RATE_JPY_USD) -> pd.DataFrame:
    """Generate balance sheet summary table in both JPY and USD"""

    fin = profile.latest_financials
    fin_usd = fin.to_usd(fx_rate)

    data = [
        {"Item": "Cash & Equivalents", "JPY (¥B)": fin.cash_and_equivalents, "USD ($B)": fin_usd.cash_and_equivalents},
        {"Item": "Total Current Assets", "JPY (¥B)": fin.total_current_assets, "USD ($B)": fin_usd.total_current_assets},
        {"Item": "Total Assets", "JPY (¥B)": fin.total_assets, "USD ($B)": fin_usd.total_assets},
        {"Item": "", "JPY (¥B)": "", "USD ($B)": ""},
        {"Item": "Short-Term Debt", "JPY (¥B)": fin.short_term_debt, "USD ($B)": fin_usd.short_term_debt},
        {"Item": "Long-Term Debt", "JPY (¥B)": fin.long_term_debt, "USD ($B)": fin_usd.long_term_debt},
        {"Item": "Total Debt", "JPY (¥B)": fin.total_debt, "USD ($B)": fin_usd.total_debt},
        {"Item": "Total Liabilities", "JPY (¥B)": fin.total_liabilities, "USD ($B)": fin_usd.total_liabilities},
        {"Item": "", "JPY (¥B)": "", "USD ($B)": ""},
        {"Item": "Total Equity", "JPY (¥B)": fin.total_equity, "USD ($B)": fin_usd.total_equity},
        {"Item": "", "JPY (¥B)": "", "USD ($B)": ""},
        {"Item": "Net Debt", "JPY (¥B)": fin.net_debt, "USD ($B)": fin_usd.net_debt},
        {"Item": "Available Credit Facilities", "JPY (¥B)": fin.available_credit_facilities, "USD ($B)": fin_usd.available_credit_facilities},
        {"Item": "Total Liquidity", "JPY (¥B)": fin.total_liquidity, "USD ($B)": fin_usd.total_liquidity},
    ]

    return pd.DataFrame(data)


def get_leverage_trend(profile: NipponFinancialProfile) -> pd.DataFrame:
    """Get 5-year leverage ratio trend"""

    data = []
    for year in sorted(profile.financials_history.keys()):
        fin = profile.financials_history[year]
        metrics = calculate_credit_metrics(fin)

        data.append({
            'Fiscal Year': year,
            'Revenue (¥T)': fin.revenue / 1000,
            'EBITDA (¥B)': fin.ebitda,
            'Net Debt (¥B)': fin.net_debt,
            'Debt/EBITDA': metrics.debt_to_ebitda,
            'Net Debt/EBITDA': metrics.net_debt_to_ebitda,
            'Interest Coverage': metrics.interest_coverage,
        })

    return pd.DataFrame(data)


def get_peer_comparison_table(profile: NipponFinancialProfile) -> pd.DataFrame:
    """Generate peer comparison table"""

    data = []
    for peer in profile.peer_data:
        data.append({
            'Company': peer.name,
            'Country': peer.country,
            'Revenue ($B)': peer.revenue_usd,
            'EBITDA ($B)': peer.ebitda_usd,
            'EBITDA Margin': f"{peer.ebitda_margin:.1%}",
            'Debt/EBITDA': f"{peer.debt_to_ebitda:.2f}x",
            'EV/EBITDA': f"{peer.ev_to_ebitda:.1f}x",
            'Market Cap ($B)': peer.market_cap_usd,
        })

    return pd.DataFrame(data)


def export_nippon_financials_csv(profile: NipponFinancialProfile,
                                  output_dir: Path = None) -> Path:
    """Export Nippon financials to CSV"""

    if output_dir is None:
        output_dir = Path(__file__).parent / 'data'

    output_dir.mkdir(exist_ok=True)

    # Convert financials to DataFrame
    data = []
    for year, fin in profile.financials_history.items():
        fin_usd = fin.to_usd()
        metrics = calculate_credit_metrics(fin)

        data.append({
            'fiscal_year': year,
            'fiscal_year_end': fin.fiscal_year_end,
            'revenue_jpy_b': fin.revenue,
            'revenue_usd_b': fin_usd.revenue,
            'ebitda_jpy_b': fin.ebitda,
            'ebitda_usd_b': fin_usd.ebitda,
            'net_income_jpy_b': fin.net_income,
            'total_debt_jpy_b': fin.total_debt,
            'total_debt_usd_b': fin_usd.total_debt,
            'net_debt_jpy_b': fin.net_debt,
            'cash_jpy_b': fin.cash_and_equivalents,
            'total_equity_jpy_b': fin.total_equity,
            'operating_cf_jpy_b': fin.operating_cash_flow,
            'capex_jpy_b': fin.capex,
            'fcf_jpy_b': fin.free_cash_flow,
            'debt_to_ebitda': metrics.debt_to_ebitda,
            'net_debt_to_ebitda': metrics.net_debt_to_ebitda,
            'interest_coverage': metrics.interest_coverage,
            'debt_to_equity': metrics.debt_to_equity,
        })

    df = pd.DataFrame(data)
    output_path = output_dir / 'nippon_financials.csv'
    df.to_csv(output_path, index=False)

    return output_path


# =============================================================================
# MAIN / CLI
# =============================================================================

def main():
    """Test the module and print summary"""

    print("=" * 60)
    print("NIPPON STEEL FINANCIAL PROFILE")
    print("=" * 60)

    # Build profile
    profile = build_nippon_financial_profile()

    # Print latest financials
    fin = profile.latest_financials
    fin_usd = fin.to_usd()

    print(f"\nFiscal Year: {fin.fiscal_year} ({fin.fiscal_year_end})")
    print(f"Exchange Rate: ¥{FX_RATE_JPY_USD}/USD")
    print()

    print("BALANCE SHEET HIGHLIGHTS")
    print("-" * 40)
    print(f"Total Assets:          ¥{fin.total_assets:,.0f}B (${fin_usd.total_assets:,.1f}B)")
    print(f"Total Debt:            ¥{fin.total_debt:,.0f}B (${fin_usd.total_debt:,.1f}B)")
    print(f"Net Debt:              ¥{fin.net_debt:,.0f}B (${fin_usd.net_debt:,.1f}B)")
    print(f"Total Equity:          ¥{fin.total_equity:,.0f}B (${fin_usd.total_equity:,.1f}B)")
    print(f"Cash & Equivalents:    ¥{fin.cash_and_equivalents:,.0f}B (${fin_usd.cash_and_equivalents:,.1f}B)")
    print(f"Total Liquidity:       ¥{fin.total_liquidity:,.0f}B (${fin_usd.total_liquidity:,.1f}B)")
    print()

    print("INCOME & CASH FLOW")
    print("-" * 40)
    print(f"Revenue:               ¥{fin.revenue:,.0f}B (${fin_usd.revenue:,.1f}B)")
    print(f"EBITDA:                ¥{fin.ebitda:,.0f}B (${fin_usd.ebitda:,.1f}B)")
    print(f"Operating Cash Flow:   ¥{fin.operating_cash_flow:,.0f}B (${fin_usd.operating_cash_flow:,.1f}B)")
    print(f"CapEx:                 ¥{fin.capex:,.0f}B (${fin_usd.capex:,.1f}B)")
    print(f"Free Cash Flow:        ¥{fin.free_cash_flow:,.0f}B (${fin_usd.free_cash_flow:,.1f}B)")
    print()

    print("CREDIT METRICS")
    print("-" * 40)
    metrics = profile.credit_metrics
    print(f"Debt/EBITDA:           {metrics.debt_to_ebitda:.2f}x")
    print(f"Net Debt/EBITDA:       {metrics.net_debt_to_ebitda:.2f}x")
    print(f"Interest Coverage:     {metrics.interest_coverage:.1f}x")
    print(f"Debt/Equity:           {metrics.debt_to_equity:.2f}x")
    print(f"Implied Rating:        {metrics.implied_rating}")
    print()

    print("CREDIT RATINGS")
    print("-" * 40)
    for rating in profile.credit_ratings:
        print(f"{rating.agency:15s} {rating.long_term_rating:6s} ({rating.outlook})")
    print()

    print("DEAL CONTEXT")
    print("-" * 40)
    print(f"USS Acquisition Price: ${DEAL_EQUITY_PRICE/1000:.1f}B")
    print(f"NSA Investment Commitment: ${NSA_INVESTMENT_COMMITMENTS/1000:.1f}B")
    print(f"Total Capital Deployment: ${TOTAL_CAPITAL_DEPLOYMENT/1000:.1f}B")
    print(f"Nippon Total Liquidity: ${fin_usd.total_liquidity:,.1f}B")
    print()

    # Export to CSV
    csv_path = export_nippon_financials_csv(profile)
    print(f"Exported financials to: {csv_path}")

    return profile


if __name__ == '__main__':
    main()
