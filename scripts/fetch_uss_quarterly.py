#!/usr/bin/env python3
"""
Fetch USS (ticker: X) quarterly fundamentals from WRDS Compustat (comp.fundq).

Uses the existing local/.env WRDS_API_TOKEN and wrds_cache infrastructure.
Saves output to local/wrds_cache/uss_quarterly.parquet and data/uss_quarterly_revenue.csv.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Load env from local/.env (same as wrds_loader.py)
env_path = Path(__file__).parent.parent / 'local' / '.env'
load_dotenv(env_path)

BASE_URL = "https://wrds-api.wharton.upenn.edu/data"
CACHE_DIR = Path(__file__).parent.parent / 'local' / 'wrds_cache'
OUTPUT_DIR = Path(__file__).parent.parent / 'data'


def fetch_uss_quarterly(start_year: int = 2015, end_year: int = 2024, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch USS quarterly fundamentals from comp.fundq.

    Returns DataFrame with quarterly revenue, EBITDA, sales, assets, debt, cash.
    """
    cache_path = CACHE_DIR / 'uss_quarterly.parquet'

    if use_cache and cache_path.exists():
        from datetime import datetime
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        if age_days <= 30:
            print(f"Loading USS quarterly from cache ({age_days} days old)")
            return pd.read_parquet(cache_path)

    api_token = os.getenv('WRDS_API_TOKEN')
    if not api_token or api_token == 'your_api_token_here':
        print("ERROR: WRDS_API_TOKEN not set. Check local/.env", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {api_token}',
        'Accept': 'application/json'
    })

    print(f"Fetching USS quarterly data from WRDS (FY{start_year}-{end_year})...")

    params = {
        'tic': 'X',
        'fyearq__gte': start_year,
        'fyearq__lte': end_year,
        'indfmt': 'INDL',
        'datafmt': 'STD',
        'popsrc': 'D',
        'consol': 'C',
        'limit': 1000,
    }

    all_results = []
    url = f"{BASE_URL}/comp.fundq/"

    while url:
        resp = session.get(url, params=params if '?' not in url else None)
        resp.raise_for_status()
        data = resp.json()
        all_results.extend(data.get('results', []))
        url = data.get('next')
        params = None  # pagination URL includes params

    if not all_results:
        print("ERROR: No data returned from WRDS", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(all_results)
    print(f"  Fetched {len(df)} quarterly records")

    # Select and rename key columns
    column_map = {
        'tic': 'ticker',
        'conm': 'company_name',
        'datadate': 'datadate',
        'fyearq': 'fiscal_year',
        'fqtr': 'fiscal_quarter',
        'revtq': 'revenue',
        'saleq': 'sales',
        'oibdpq': 'ebitda',
        'niq': 'net_income',
        'atq': 'total_assets',
        'ltq': 'total_liabilities',
        'dlttq': 'long_term_debt',
        'dlcq': 'short_term_debt',
        'cheq': 'cash',
        'cshoq': 'shares_outstanding',
        'prccq': 'stock_price',
        'capxy': 'capex_ytd',
        'oancfy': 'operating_cf_ytd',
    }

    available = {k: v for k, v in column_map.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    # Convert numeric columns
    for col in df.columns:
        if col not in ('ticker', 'company_name', 'datadate'):
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['datadate'] = pd.to_datetime(df['datadate'])
    df = df.sort_values(['fiscal_year', 'fiscal_quarter']).reset_index(drop=True)

    # Cache
    CACHE_DIR.mkdir(exist_ok=True)
    df.to_parquet(cache_path)
    print(f"  Cached to {cache_path}")

    return df


def save_csv(df: pd.DataFrame):
    """Save a clean CSV for the analysis script."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / 'uss_quarterly_revenue.csv'

    # Create quarter label (e.g., "2015Q1")
    df = df.copy()
    df['quarter'] = df['fiscal_year'].astype(int).astype(str) + 'Q' + df['fiscal_quarter'].astype(int).astype(str)

    cols = ['quarter', 'datadate', 'fiscal_year', 'fiscal_quarter',
            'revenue', 'ebitda', 'net_income', 'cash', 'long_term_debt', 'short_term_debt',
            'total_assets', 'shares_outstanding', 'stock_price']
    cols = [c for c in cols if c in df.columns]
    df[cols].to_csv(out_path, index=False)
    print(f"  Saved {out_path} ({len(df)} rows)")


def validate(df: pd.DataFrame):
    """Cross-check annual sums against known totals."""
    print("\n--- Validation: Annual Revenue Sums ---")
    annual = df.groupby('fiscal_year')['revenue'].sum()
    known = {2023: 18048, 2022: 21065, 2021: 20275, 2020: 9741, 2019: 12937}

    for year, expected in sorted(known.items()):
        actual = annual.get(year, 0)
        diff_pct = (actual - expected) / expected * 100 if expected else 0
        status = 'OK' if abs(diff_pct) < 5 else 'MISMATCH'
        print(f"  FY{year}: WRDS ${actual:,.0f}M vs 10-K ${expected:,.0f}M  ({diff_pct:+.1f}%)  [{status}]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch USS quarterly data from WRDS')
    parser.add_argument('--refresh', action='store_true', help='Force refresh (ignore cache)')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)
    args = parser.parse_args()

    df = fetch_uss_quarterly(args.start_year, args.end_year, use_cache=not args.refresh)
    save_csv(df)
    validate(df)

    print(f"\nDone. {len(df)} quarterly observations ({df['fiscal_year'].min()}-{df['fiscal_year'].max()})")
    print(f"Revenue range: ${df['revenue'].min():,.0f}M - ${df['revenue'].max():,.0f}M")
    print(f"EBITDA range: ${df['ebitda'].min():,.0f}M - ${df['ebitda'].max():,.0f}M")


if __name__ == '__main__':
    main()
