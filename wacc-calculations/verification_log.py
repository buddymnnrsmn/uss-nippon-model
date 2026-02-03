#!/usr/bin/env python3
"""
WACC Input Verification Script
==============================

Verifies all WACC inputs against primary sources and logs results.
Uses WRDS for financial data and web sources for market data.

Outputs:
- verification_results.json: Machine-readable verification log
- verification_report.md: Human-readable verification report
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'local'))
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd


@dataclass
class VerificationResult:
    """Result of verifying a single input"""
    item: str
    expected_value: str
    verified_value: Optional[str]
    source: str
    source_url: Optional[str]
    verification_date: str
    status: str  # "verified", "mismatch", "unable_to_verify", "partial"
    notes: str = ""


class WACCVerificationLog:
    """
    Logs and verifies WACC calculation inputs
    """

    def __init__(self):
        self.results: List[VerificationResult] = []
        self.verification_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def add_result(self, result: VerificationResult):
        """Add a verification result"""
        self.results.append(result)

    def verify_from_wrds(self, ticker: str, fiscal_year: int) -> Dict:
        """
        Fetch financial data from WRDS for verification

        Returns dict with debt, cash, market cap, etc.
        """
        try:
            from wrds_loader import WRDSDataLoader

            loader = WRDSDataLoader()

            # Fetch fundamentals
            print(f"Fetching WRDS data for {ticker}, FY{fiscal_year}...")

            # Use the REST API to fetch Compustat annual data
            params = {
                'tic': ticker,
                'fyear__gte': fiscal_year,
                'fyear__lte': fiscal_year,
            }

            response = loader._session.get(
                f"{loader.BASE_URL}/comp.funda/",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    row = results[0]
                    return {
                        'source': 'WRDS Compustat',
                        'ticker': ticker,
                        'fiscal_year': fiscal_year,
                        'total_debt': row.get('dltt', 0) + row.get('dlc', 0),  # Long-term + current debt
                        'long_term_debt': row.get('dltt'),
                        'short_term_debt': row.get('dlc'),
                        'cash': row.get('che'),  # Cash and short-term investments
                        'total_assets': row.get('at'),
                        'total_equity': row.get('ceq'),  # Common equity
                        'market_cap': row.get('mkvalt'),  # Market value
                        'revenue': row.get('revt'),
                        'ebitda': row.get('ebitda') or row.get('oibdp'),
                        'shares_outstanding': row.get('csho'),
                        'price_close_fiscal_year': row.get('prcc_f'),
                        'raw_data': row,
                    }
            return {'source': 'WRDS', 'error': f"No data found for {ticker} FY{fiscal_year}"}

        except Exception as e:
            return {'source': 'WRDS', 'error': str(e)}

    def verify_uss_inputs(self) -> List[VerificationResult]:
        """Verify all USS WACC inputs"""
        results = []

        # Load USS inputs
        uss_inputs_path = Path(__file__).parent / 'uss' / 'inputs.json'
        with open(uss_inputs_path) as f:
            uss_inputs = json.load(f)

        # 1. Verify USS financial data from WRDS
        print("\n" + "="*60)
        print("Verifying USS Financial Data from WRDS...")
        print("="*60)

        wrds_data = self.verify_from_wrds('X', 2023)

        if 'error' not in wrds_data:
            # Verify total debt
            expected_debt = uss_inputs['capital_structure']['total_debt_mm']
            wrds_debt = wrds_data.get('total_debt', 0)
            # Convert to float if needed
            try:
                wrds_debt = float(wrds_debt) if wrds_debt else 0
            except (TypeError, ValueError):
                wrds_debt = 0
            if wrds_debt:
                status = "verified" if abs(wrds_debt - expected_debt) < 200 else "mismatch"
                results.append(VerificationResult(
                    item="USS Total Debt (2023 10-K)",
                    expected_value=f"${expected_debt:,.0f}M",
                    verified_value=f"${wrds_debt:,.0f}M" if wrds_debt else "N/A",
                    source="WRDS Compustat (comp.funda)",
                    source_url="https://wrds-www.wharton.upenn.edu/",
                    verification_date=self.verification_date,
                    status=status,
                    notes=f"WRDS dltt + dlc = {wrds_debt:.0f}"
                ))

            # Verify cash
            expected_cash = uss_inputs['capital_structure']['cash_mm']
            wrds_cash = wrds_data.get('cash', 0)
            try:
                wrds_cash = float(wrds_cash) if wrds_cash else 0
            except (TypeError, ValueError):
                wrds_cash = 0
            if wrds_cash:
                status = "verified" if abs(wrds_cash - expected_cash) < 200 else "mismatch"
                results.append(VerificationResult(
                    item="USS Cash & Equivalents (2023 10-K)",
                    expected_value=f"${expected_cash:,.0f}M",
                    verified_value=f"${wrds_cash:,.0f}M" if wrds_cash else "N/A",
                    source="WRDS Compustat (comp.funda)",
                    source_url="https://wrds-www.wharton.upenn.edu/",
                    verification_date=self.verification_date,
                    status=status,
                    notes=f"WRDS che = {wrds_cash:.0f}"
                ))

            # Verify shares outstanding
            expected_shares = uss_inputs['capital_structure']['shares_outstanding_mm']
            wrds_shares = wrds_data.get('shares_outstanding', 0)
            try:
                wrds_shares = float(wrds_shares) if wrds_shares else 0
            except (TypeError, ValueError):
                wrds_shares = 0
            if wrds_shares:
                status = "verified" if abs(wrds_shares - expected_shares) < 10 else "mismatch"
                results.append(VerificationResult(
                    item="USS Shares Outstanding",
                    expected_value=f"{expected_shares:.0f}M",
                    verified_value=f"{wrds_shares:.0f}M" if wrds_shares else "N/A",
                    source="WRDS Compustat (comp.funda)",
                    source_url="https://wrds-www.wharton.upenn.edu/",
                    verification_date=self.verification_date,
                    status=status,
                    notes=f"WRDS csho = {wrds_shares:.0f}"
                ))

            print(f"  Total Debt: Expected ${expected_debt:,.0f}M, WRDS ${wrds_debt:,.0f}M")
            print(f"  Cash: Expected ${expected_cash:,.0f}M, WRDS ${wrds_cash:,.0f}M")
            print(f"  Shares: Expected {expected_shares:.0f}M, WRDS {wrds_shares:.0f}M")
        else:
            print(f"  WRDS Error: {wrds_data.get('error')}")
            results.append(VerificationResult(
                item="USS Financial Data (WRDS)",
                expected_value="See inputs.json",
                verified_value=None,
                source="WRDS Compustat",
                source_url="https://wrds-www.wharton.upenn.edu/",
                verification_date=self.verification_date,
                status="unable_to_verify",
                notes=f"WRDS error: {wrds_data.get('error')}"
            ))

        # 2. Add manual verification items (require external lookup)
        manual_items = [
            {
                'item': "10-Year Treasury Yield (12/29/2023)",
                'expected': uss_inputs['risk_free_rate']['value'],
                'source': "Federal Reserve H.15",
                'url': "https://www.federalreserve.gov/releases/h15/",
                'notes': "Need to check FRED DGS10 series for 2023-12-29"
            },
            {
                'item': "USS Stock Price (12/29/2023)",
                'expected': uss_inputs['capital_structure']['share_price'],
                'source': "NYSE / Yahoo Finance",
                'url': "https://finance.yahoo.com/quote/X/history/",
                'notes': "Historical price lookup required"
            },
            {
                'item': "USS Equity Beta",
                'expected': uss_inputs['equity_beta']['levered_beta'],
                'source': "Bloomberg / Capital IQ consensus",
                'url': None,
                'notes': f"Sources: Bloomberg {uss_inputs['equity_beta']['sources']['Bloomberg']['beta']}, "
                        f"Yahoo {uss_inputs['equity_beta']['sources']['Yahoo_Finance']['beta']}, "
                        f"Capital IQ {uss_inputs['equity_beta']['sources']['Capital_IQ']['beta']}"
            },
            {
                'item': "USS Credit Rating",
                'expected': f"{uss_inputs['cost_of_debt']['credit_rating']['sp']} / {uss_inputs['cost_of_debt']['credit_rating']['moodys']}",
                'source': "S&P / Moody's",
                'url': None,
                'notes': "Check rating agency press releases"
            },
            {
                'item': "Analyst WACC Estimates (Barclays)",
                'expected': f"{uss_inputs['analyst_wacc_estimates']['Barclays']['wacc_range'][0]*100:.1f}% - {uss_inputs['analyst_wacc_estimates']['Barclays']['wacc_range'][1]*100:.1f}%",
                'source': "USS Merger Proxy (DEFM14A)",
                'url': "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=DEFM14A",
                'notes': "Fairness opinion in proxy statement"
            },
        ]

        for item in manual_items:
            results.append(VerificationResult(
                item=item['item'],
                expected_value=str(item['expected']) if not isinstance(item['expected'], str) else item['expected'],
                verified_value=None,
                source=item['source'],
                source_url=item['url'],
                verification_date=self.verification_date,
                status="needs_manual_verification",
                notes=item['notes']
            ))

        return results

    def verify_nippon_inputs(self) -> List[VerificationResult]:
        """Verify all Nippon WACC inputs"""
        results = []

        # Load Nippon inputs
        nippon_inputs_path = Path(__file__).parent / 'nippon' / 'inputs.json'
        with open(nippon_inputs_path) as f:
            nippon_inputs = json.load(f)

        print("\n" + "="*60)
        print("Verifying Nippon Steel Financial Data from WRDS...")
        print("="*60)

        # Try WRDS for Nippon (may not have data for Japanese companies)
        wrds_data = self.verify_from_wrds('NISTF', 2023)

        if 'error' not in wrds_data and wrds_data.get('total_debt'):
            print(f"  Found WRDS data for Nippon Steel")
            # Add verification results
        else:
            print(f"  WRDS data not available for Nippon Steel (Japanese company)")
            results.append(VerificationResult(
                item="Nippon Steel Financial Data (WRDS)",
                expected_value="See inputs.json",
                verified_value=None,
                source="WRDS Compustat Global",
                source_url="https://wrds-www.wharton.upenn.edu/",
                verification_date=self.verification_date,
                status="unable_to_verify",
                notes="Japanese company data may require Compustat Global subscription"
            ))

        # Manual verification items for Nippon
        manual_items = [
            {
                'item': "JGB 10-Year Yield (12/29/2023)",
                'expected': nippon_inputs['risk_free_rate']['value'],
                'source': "Bank of Japan / Ministry of Finance",
                'url': nippon_inputs['risk_free_rate']['url'],
                'notes': "Check MOF JGB statistics"
            },
            {
                'item': "US 10-Year Treasury (for IRP)",
                'expected': nippon_inputs['irp_adjustment']['us_10y_treasury'],
                'source': "Federal Reserve H.15",
                'url': "https://www.federalreserve.gov/releases/h15/",
                'notes': "Same as USS risk-free rate"
            },
            {
                'item': "Nippon Stock Price (12/29/2023)",
                'expected': f"¥{nippon_inputs['capital_structure']['stock_price_jpy']:,}",
                'source': "Tokyo Stock Exchange",
                'url': "https://www.jpx.co.jp/english/",
                'notes': "Historical price for 5401.T"
            },
            {
                'item': "USD/JPY Exchange Rate (12/29/2023)",
                'expected': nippon_inputs['capital_structure']['fx_rate_jpy_usd'],
                'source': "Federal Reserve H.10 / BOJ",
                'url': "https://www.federalreserve.gov/releases/h10/hist/",
                'notes': "Daily exchange rate"
            },
            {
                'item': "Nippon Beta vs TOPIX",
                'expected': nippon_inputs['equity_beta']['levered_beta'],
                'source': "Bloomberg",
                'url': None,
                'notes': "5401 JP Equity BETA"
            },
            {
                'item': "Nippon Credit Ratings",
                'expected': f"{nippon_inputs['cost_of_debt']['credit_rating']['sp']} / {nippon_inputs['cost_of_debt']['credit_rating']['moodys']}",
                'source': "S&P / Moody's / Fitch / R&I",
                'url': None,
                'notes': "Check rating agency websites"
            },
        ]

        for item in manual_items:
            results.append(VerificationResult(
                item=item['item'],
                expected_value=str(item['expected']) if not isinstance(item['expected'], str) else item['expected'],
                verified_value=None,
                source=item['source'],
                source_url=item['url'],
                verification_date=self.verification_date,
                status="needs_manual_verification",
                notes=item['notes']
            ))

        return results

    def run_verification(self) -> Tuple[List[VerificationResult], List[VerificationResult]]:
        """Run full verification for USS and Nippon"""
        print("\n" + "="*70)
        print("WACC INPUT VERIFICATION")
        print(f"Date: {self.verification_date}")
        print("="*70)

        uss_results = self.verify_uss_inputs()
        nippon_results = self.verify_nippon_inputs()

        self.results = uss_results + nippon_results
        return uss_results, nippon_results

    def save_results(self, output_dir: Path = None):
        """Save verification results to files"""
        if output_dir is None:
            output_dir = Path(__file__).parent

        # Save JSON
        json_path = output_dir / 'verification_results.json'
        with open(json_path, 'w') as f:
            json.dump({
                'verification_date': self.verification_date,
                'results': [asdict(r) for r in self.results]
            }, f, indent=2)
        print(f"\nSaved: {json_path}")

        # Save Markdown report
        md_path = output_dir / 'verification_report.md'
        self._write_markdown_report(md_path)
        print(f"Saved: {md_path}")

    def _write_markdown_report(self, path: Path):
        """Write human-readable markdown report"""
        lines = [
            "# WACC Input Verification Report",
            "",
            f"**Verification Date:** {self.verification_date}",
            "",
            "## Summary",
            "",
        ]

        # Count by status
        status_counts = {}
        for r in self.results:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1

        for status, count in sorted(status_counts.items()):
            emoji = {"verified": "✅", "mismatch": "❌", "needs_manual_verification": "⏳", "unable_to_verify": "⚠️"}.get(status, "❓")
            lines.append(f"- {emoji} **{status}**: {count} items")

        lines.extend([
            "",
            "## USS Verification Results",
            "",
            "| Item | Expected | Verified | Source | Status |",
            "|------|----------|----------|--------|--------|",
        ])

        for r in self.results:
            if "USS" in r.item or "Treasury" in r.item or "Analyst" in r.item:
                verified = r.verified_value or "—"
                status_emoji = {"verified": "✅", "mismatch": "❌", "needs_manual_verification": "⏳"}.get(r.status, "⚠️")
                source_link = f"[{r.source}]({r.source_url})" if r.source_url else r.source
                lines.append(f"| {r.item} | {r.expected_value} | {verified} | {source_link} | {status_emoji} |")

        lines.extend([
            "",
            "## Nippon Verification Results",
            "",
            "| Item | Expected | Verified | Source | Status |",
            "|------|----------|----------|--------|--------|",
        ])

        for r in self.results:
            if "Nippon" in r.item or "JGB" in r.item or "USD/JPY" in r.item:
                verified = r.verified_value or "—"
                status_emoji = {"verified": "✅", "mismatch": "❌", "needs_manual_verification": "⏳"}.get(r.status, "⚠️")
                source_link = f"[{r.source}]({r.source_url})" if r.source_url else r.source
                lines.append(f"| {r.item} | {r.expected_value} | {verified} | {source_link} | {status_emoji} |")

        lines.extend([
            "",
            "## Verification Notes",
            "",
        ])

        for r in self.results:
            if r.notes:
                lines.append(f"- **{r.item}**: {r.notes}")

        lines.extend([
            "",
            "## Data Sources",
            "",
            "### Primary Sources",
            "- **WRDS Compustat**: Financial statement data (debt, cash, shares)",
            "- **Federal Reserve H.15**: US Treasury yields",
            "- **Bank of Japan / MOF**: JGB yields",
            "- **NYSE / TSE**: Stock prices",
            "- **SEC EDGAR**: 10-K filings, proxy statements",
            "",
            "### Reference URLs",
        ])

        urls_seen = set()
        for r in self.results:
            if r.source_url and r.source_url not in urls_seen:
                lines.append(f"- [{r.source}]({r.source_url})")
                urls_seen.add(r.source_url)

        with open(path, 'w') as f:
            f.write('\n'.join(lines))


def main():
    """Run verification and save results"""
    verifier = WACCVerificationLog()
    uss_results, nippon_results = verifier.run_verification()

    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    print(f"\nUSS Items: {len(uss_results)}")
    for r in uss_results:
        status_emoji = {"verified": "✅", "mismatch": "❌", "needs_manual_verification": "⏳"}.get(r.status, "⚠️")
        print(f"  {status_emoji} {r.item}: {r.expected_value}")

    print(f"\nNippon Items: {len(nippon_results)}")
    for r in nippon_results:
        status_emoji = {"verified": "✅", "mismatch": "❌", "needs_manual_verification": "⏳"}.get(r.status, "⚠️")
        print(f"  {status_emoji} {r.item}: {r.expected_value}")

    verifier.save_results()

    return verifier


if __name__ == '__main__':
    main()
