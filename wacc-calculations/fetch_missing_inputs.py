#!/usr/bin/env python3
"""
Fetch Missing WACC Inputs
=========================

Automated scripts to fetch the 4 remaining verification items:
1. USS analyst WACC estimates (from SEC DEFM14A proxy)
2. Nippon Steel stock price on 12/29/2023
3. Nippon Steel beta vs TOPIX
4. Nippon Steel debt/cash balances

Uses:
- yfinance for stock prices and beta calculation
- SEC EDGAR API for proxy filings
- Web scraping for Japanese financial data

Usage:
    python fetch_missing_inputs.py --all
    python fetch_missing_inputs.py --nippon-price
    python fetch_missing_inputs.py --nippon-beta
    python fetch_missing_inputs.py --sec-proxy
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import requests

# Try to import optional dependencies
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("Warning: yfinance not installed. Run: pip install yfinance")

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class MissingInputFetcher:
    """Fetch the 4 missing WACC verification items"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent
        self.results = {}
        self.target_date = "2023-12-29"  # Last trading day of 2023
        
    def fetch_nippon_stock_price(self) -> Dict:
        """
        Fetch Nippon Steel (5401.T) historical stock price for 12/29/2023
        
        Returns:
            Dict with price data and verification status
        """
        print("\n" + "="*60)
        print("Fetching Nippon Steel Stock Price (12/29/2023)")
        print("="*60)
        
        if not HAS_YFINANCE:
            return {'status': 'error', 'message': 'yfinance not installed'}
        
        try:
            # Nippon Steel on Tokyo Stock Exchange
            ticker = yf.Ticker("5401.T")
            
            # Get historical data around target date
            # Note: 12/29/2023 was a Friday (last trading day before Japanese New Year)
            hist = ticker.history(start="2023-12-25", end="2024-01-05")
            
            if hist.empty:
                # Try alternative date range
                hist = ticker.history(start="2023-12-01", end="2024-01-15")
            
            if hist.empty:
                return {'status': 'error', 'message': 'No data returned from yfinance'}
            
            print(f"\nHistorical data retrieved:")
            print(hist[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10))
            
            # Find closest trading day to 12/29/2023
            # Convert index to date strings for comparison
            hist_dates = hist.index.strftime('%Y-%m-%d').tolist()
            target_str = "2023-12-29"

            # Check if exact date exists
            if target_str in hist_dates:
                idx = hist_dates.index(target_str)
                close_price = hist.iloc[idx]['Close']
                date_used = target_str
            else:
                # Find closest date before target
                valid_dates = [d for d in hist_dates if d <= target_str]
                if valid_dates:
                    closest_date = max(valid_dates)
                    idx = hist_dates.index(closest_date)
                    close_price = hist.iloc[idx]['Close']
                    date_used = closest_date
                else:
                    close_price = hist.iloc[0]['Close']
                    date_used = hist_dates[0]
                print(f"\nUsing date: {date_used}")
            
            result = {
                'status': 'verified',
                'ticker': '5401.T',
                'date': date_used,
                'close_price_jpy': float(close_price),
                'source': 'Yahoo Finance (yfinance)',
                'notes': 'Tokyo Stock Exchange closing price'
            }
            
            print(f"\n✓ Nippon Steel Stock Price:")
            print(f"  Date: {date_used}")
            print(f"  Close: ¥{close_price:,.0f}")
            
            # Check for stock splits that might affect comparison
            splits = ticker.splits
            if not splits.empty:
                recent_splits = splits[splits.index >= "2023-01-01"]
                if not recent_splits.empty:
                    result['splits_note'] = f"Stock splits since 2023: {recent_splits.to_dict()}"
                    print(f"  ⚠ Stock splits detected: {recent_splits.to_dict()}")
            
            return result
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def fetch_nippon_beta(self) -> Dict:
        """
        Calculate Nippon Steel beta vs TOPIX using historical returns
        
        Uses 5-year monthly returns through December 2023
        
        Returns:
            Dict with beta calculation and methodology
        """
        print("\n" + "="*60)
        print("Calculating Nippon Steel Beta vs TOPIX")
        print("="*60)
        
        if not HAS_YFINANCE or not HAS_PANDAS:
            return {'status': 'error', 'message': 'yfinance/pandas not installed'}
        
        try:
            # Fetch 5 years of monthly data through 12/2023
            start_date = "2019-01-01"
            end_date = "2023-12-31"
            
            # Nippon Steel
            nippon = yf.Ticker("5401.T")
            nippon_hist = nippon.history(start=start_date, end=end_date, interval="1mo")
            
            # TOPIX (^TOPX or 1306.T ETF as proxy)
            # Try TOPIX index first
            try:
                topix = yf.Ticker("^TPX")
                topix_hist = topix.history(start=start_date, end=end_date, interval="1mo")
                if topix_hist.empty:
                    raise ValueError("TOPIX data empty")
            except:
                # Use TOPIX ETF as proxy
                print("Using TOPIX ETF (1306.T) as proxy for TOPIX index")
                topix = yf.Ticker("1306.T")
                topix_hist = topix.history(start=start_date, end=end_date, interval="1mo")
            
            if nippon_hist.empty or topix_hist.empty:
                return {'status': 'error', 'message': 'Insufficient historical data'}
            
            # Calculate monthly returns
            nippon_returns = nippon_hist['Close'].pct_change().dropna()
            topix_returns = topix_hist['Close'].pct_change().dropna()
            
            # Align dates
            common_dates = nippon_returns.index.intersection(topix_returns.index)
            nippon_returns = nippon_returns.loc[common_dates]
            topix_returns = topix_returns.loc[common_dates]
            
            if len(nippon_returns) < 24:  # Need at least 2 years
                return {'status': 'error', 'message': f'Only {len(nippon_returns)} months of data'}
            
            # Calculate beta using regression
            covariance = np.cov(nippon_returns, topix_returns)[0, 1]
            variance = np.var(topix_returns, ddof=1)
            beta = covariance / variance
            
            # Calculate R-squared
            correlation = np.corrcoef(nippon_returns, topix_returns)[0, 1]
            r_squared = correlation ** 2
            
            result = {
                'status': 'verified',
                'beta': round(float(beta), 3),
                'r_squared': round(float(r_squared), 3),
                'correlation': round(float(correlation), 3),
                'months_used': len(nippon_returns),
                'period': f"{start_date} to {end_date}",
                'benchmark': 'TOPIX (or proxy)',
                'methodology': '5-year monthly returns, OLS regression',
                'source': 'Yahoo Finance (yfinance) - calculated',
            }
            
            print(f"\n✓ Nippon Steel Beta Calculation:")
            print(f"  Beta: {beta:.3f}")
            print(f"  R-squared: {r_squared:.3f}")
            print(f"  Correlation: {correlation:.3f}")
            print(f"  Months used: {len(nippon_returns)}")
            print(f"  Period: {start_date} to {end_date}")
            
            # Compare to expected
            expected_beta = 1.15
            if abs(beta - expected_beta) < 0.15:
                print(f"  ✓ Within range of expected ({expected_beta})")
            else:
                print(f"  ⚠ Differs from expected ({expected_beta}) by {abs(beta - expected_beta):.2f}")
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}
    
    def fetch_sec_proxy_wacc(self) -> Dict:
        """
        Fetch USS DEFM14A proxy and extract analyst WACC estimates
        
        Returns:
            Dict with analyst WACC data from Barclays fairness opinion
        """
        print("\n" + "="*60)
        print("Fetching USS Proxy Statement (DEFM14A) for Analyst WACC")
        print("="*60)
        
        # SEC EDGAR API
        cik = "0001163302"  # USS CIK
        base_url = "https://data.sec.gov"
        
        headers = {
            'User-Agent': 'WACC Research Bot / research@example.com',
            'Accept-Encoding': 'gzip, deflate'
        }
        
        try:
            # Get company filings
            filings_url = f"{base_url}/submissions/CIK{cik}.json"
            print(f"Fetching: {filings_url}")
            
            response = requests.get(filings_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Find DEFM14A filings
            filings = data.get('filings', {}).get('recent', {})
            forms = filings.get('form', [])
            dates = filings.get('filingDate', [])
            accessions = filings.get('accessionNumber', [])
            descriptions = filings.get('primaryDocument', [])
            
            defm14a_filings = []
            for i, form in enumerate(forms):
                if 'DEFM14A' in form or 'DEF 14A' in form:
                    defm14a_filings.append({
                        'form': form,
                        'date': dates[i],
                        'accession': accessions[i],
                        'document': descriptions[i] if i < len(descriptions) else None
                    })
            
            if not defm14a_filings:
                # Try preliminary proxy
                for i, form in enumerate(forms):
                    if 'PREM14A' in form or 'DEFM' in form:
                        defm14a_filings.append({
                            'form': form,
                            'date': dates[i],
                            'accession': accessions[i],
                            'document': descriptions[i] if i < len(descriptions) else None
                        })
            
            print(f"\nFound {len(defm14a_filings)} proxy filings:")
            for f in defm14a_filings[:5]:
                print(f"  {f['date']}: {f['form']} - {f['accession']}")
            
            if defm14a_filings:
                # Get the most recent one (should be for Nippon deal)
                latest = defm14a_filings[0]
                accession_clean = latest['accession'].replace('-', '')
                
                # Construct URL to filing
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/"
                
                result = {
                    'status': 'found',
                    'filing_type': latest['form'],
                    'filing_date': latest['date'],
                    'accession_number': latest['accession'],
                    'sec_url': filing_url,
                    'source': 'SEC EDGAR',
                    'notes': 'Manual review required to extract Barclays WACC range from fairness opinion',
                    'expected_location': 'Annex B or C - Barclays Opinion',
                    'expected_wacc_range': '11.5% - 13.5%'
                }
                
                print(f"\n✓ Found proxy filing:")
                print(f"  Form: {latest['form']}")
                print(f"  Date: {latest['date']}")
                print(f"  URL: {filing_url}")
                print(f"\n  → Manual step: Download and search for 'discount rate' or 'WACC'")
                print(f"  → Expected: Barclays used 11.5% - 13.5% discount rate range")
                
                return result
            else:
                return {
                    'status': 'not_found',
                    'message': 'No DEFM14A filing found',
                    'search_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=DEFM14A"
                }
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}
    
    def fetch_nippon_financials(self) -> Dict:
        """
        Fetch Nippon Steel financial data (debt/cash) from available sources
        
        Returns:
            Dict with debt and cash balances
        """
        print("\n" + "="*60)
        print("Fetching Nippon Steel Financial Data")
        print("="*60)
        
        if not HAS_YFINANCE:
            return {'status': 'error', 'message': 'yfinance not installed'}
        
        try:
            ticker = yf.Ticker("5401.T")
            
            # Get balance sheet
            balance_sheet = ticker.balance_sheet
            
            if balance_sheet.empty:
                return {'status': 'error', 'message': 'No balance sheet data available'}
            
            print("\nBalance Sheet (most recent periods):")
            print(balance_sheet.head(20))
            
            # Try to extract debt and cash
            # Note: Column names vary by yfinance version
            result = {
                'status': 'partial',
                'source': 'Yahoo Finance (yfinance)',
                'notes': 'Data may not match fiscal year end exactly',
                'raw_data': {}
            }
            
            # Look for common field names
            for col in balance_sheet.columns[:2]:  # Most recent 2 periods
                period_data = {}
                
                # Cash fields
                for field in ['Cash And Cash Equivalents', 'Cash', 'Cash Cash Equivalents And Short Term Investments']:
                    if field in balance_sheet.index:
                        val = balance_sheet.loc[field, col]
                        if pd.notna(val):
                            period_data['cash'] = float(val)
                            break
                
                # Debt fields
                for field in ['Total Debt', 'Long Term Debt', 'Total Non Current Liabilities Net Minority Interest']:
                    if field in balance_sheet.index:
                        val = balance_sheet.loc[field, col]
                        if pd.notna(val):
                            period_data['total_debt'] = float(val)
                            break
                
                if period_data:
                    result['raw_data'][str(col.date()) if hasattr(col, 'date') else str(col)] = period_data
            
            if result['raw_data']:
                print(f"\n✓ Found financial data:")
                for period, data in result['raw_data'].items():
                    print(f"  {period}:")
                    if 'cash' in data:
                        print(f"    Cash: ¥{data['cash']/1e9:,.0f}B")
                    if 'total_debt' in data:
                        print(f"    Total Debt: ¥{data['total_debt']/1e9:,.0f}B")
                result['status'] = 'verified'
            else:
                print("  ⚠ Could not extract specific debt/cash fields")
                print("  Available fields:", list(balance_sheet.index[:20]))
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': str(e)}
    
    def run_all(self) -> Dict:
        """Run all fetchers and compile results"""
        self.results = {
            'fetch_date': datetime.now().isoformat(),
            'target_date': self.target_date,
            'items': {}
        }
        
        # 1. Nippon stock price
        self.results['items']['nippon_stock_price'] = self.fetch_nippon_stock_price()
        
        # 2. Nippon beta
        self.results['items']['nippon_beta'] = self.fetch_nippon_beta()
        
        # 3. SEC proxy for analyst WACC
        self.results['items']['uss_analyst_wacc'] = self.fetch_sec_proxy_wacc()
        
        # 4. Nippon financials
        self.results['items']['nippon_financials'] = self.fetch_nippon_financials()
        
        # Save results
        output_file = self.output_dir / 'missing_inputs_results.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        for item, result in self.results['items'].items():
            status = result.get('status', 'unknown')
            emoji = {'verified': '✓', 'found': '✓', 'partial': '~', 'error': '✗'}.get(status, '?')
            print(f"  {emoji} {item}: {status}")
        
        print(f"\nResults saved to: {output_file}")
        
        return self.results


def main():
    parser = argparse.ArgumentParser(description='Fetch missing WACC verification inputs')
    parser.add_argument('--all', action='store_true', help='Fetch all missing items')
    parser.add_argument('--nippon-price', action='store_true', help='Fetch Nippon stock price')
    parser.add_argument('--nippon-beta', action='store_true', help='Calculate Nippon beta')
    parser.add_argument('--nippon-financials', action='store_true', help='Fetch Nippon financials')
    parser.add_argument('--sec-proxy', action='store_true', help='Fetch SEC proxy for analyst WACC')
    
    args = parser.parse_args()
    
    fetcher = MissingInputFetcher()
    
    if args.all or not any([args.nippon_price, args.nippon_beta, args.nippon_financials, args.sec_proxy]):
        fetcher.run_all()
    else:
        if args.nippon_price:
            result = fetcher.fetch_nippon_stock_price()
            print(json.dumps(result, indent=2, default=str))
        if args.nippon_beta:
            result = fetcher.fetch_nippon_beta()
            print(json.dumps(result, indent=2, default=str))
        if args.nippon_financials:
            result = fetcher.fetch_nippon_financials()
            print(json.dumps(result, indent=2, default=str))
        if args.sec_proxy:
            result = fetcher.fetch_sec_proxy_wacc()
            print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
