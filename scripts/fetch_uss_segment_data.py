#!/usr/bin/env python3
"""
Fetch USS (ticker: X) quarterly segment data from WRDS Compustat (comp.segq).

Downloads business segment revenue and operating profit at quarterly frequency,
providing ~80 observations for FR/USSE/Tubular (from ~2003) and ~16 for Mini Mill
(from ~2021). Cross-validates against hardcoded FY2019-2023 values.

Usage:
    python scripts/fetch_uss_segment_data.py [--refresh] [--start-year 2003]
"""

import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Load env from local/.env
env_path = Path(__file__).parent.parent / 'local' / '.env'
load_dotenv(env_path)

BASE_URL = "https://wrds-api.wharton.upenn.edu/data"
CACHE_DIR = Path(__file__).parent.parent / 'local' / 'wrds_cache'
OUTPUT_DIR = Path(__file__).parent.parent / 'data'

# USS segment name mapping: WRDS snms -> canonical names
SEGMENT_NAME_MAP = {
    'flat-rolled': 'Flat-Rolled',
    'flat rolled': 'Flat-Rolled',
    'flat-rolled products': 'Flat-Rolled',
    'flat rolled products': 'Flat-Rolled',
    'u. s. steel europe': 'USSE',
    'u.s. steel europe': 'USSE',
    'usse': 'USSE',
    'european': 'USSE',
    'europe': 'USSE',
    'tubular products': 'Tubular',
    'tubular': 'Tubular',
    'big river steel': 'Mini Mill',
    'mini mill': 'Mini Mill',
    'mini-mill': 'Mini Mill',
}


def normalize_segment_name(raw_name: str) -> str:
    """Map WRDS segment name to canonical name."""
    if not raw_name:
        return raw_name
    lower = raw_name.strip().lower()
    return SEGMENT_NAME_MAP.get(lower, raw_name.strip())


def fetch_segment_quarterly(start_year: int = 2003, end_year: int = 2024,
                             use_cache: bool = True) -> pd.DataFrame:
    """Fetch USS quarterly segment data from WRDS comp.segq."""
    cache_path = CACHE_DIR / 'uss_segment_quarterly.parquet'

    if use_cache and cache_path.exists():
        from datetime import datetime
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        if age_days <= 30:
            print(f"Loading USS segment quarterly from cache ({age_days} days old)")
            return pd.read_parquet(cache_path)

    api_token = os.getenv('WRDS_API_TOKEN')
    if not api_token or api_token == 'your_api_token_here':
        print("WARNING: WRDS_API_TOKEN not set. Using fallback data.", file=sys.stderr)
        return pd.DataFrame()

    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {api_token}',
        'Accept': 'application/json'
    })

    print(f"Fetching USS segment quarterly data from WRDS (FY{start_year}-{end_year})...")

    params = {
        'tic': 'X',
        'stype': 'BUSSEG',
        'datadate__gte': f'{start_year}-01-01',
        'datadate__lte': f'{end_year}-12-31',
        'limit': 2000,
    }

    all_results = []
    url = f"{BASE_URL}/comp.segq/"

    while url:
        try:
            resp = session.get(url, params=params if '?' not in url else None)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get('results', []))
            url = data.get('next')
            params = None
        except requests.RequestException as e:
            print(f"WARNING: WRDS API request failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    if not all_results:
        print("WARNING: No segment data returned from WRDS", file=sys.stderr)
        return pd.DataFrame()

    df = pd.DataFrame(all_results)
    print(f"  Fetched {len(df)} segment-quarter records")

    # Select key columns
    column_map = {
        'snms': 'segment_raw',
        'sales': 'revenue',
        'ops': 'operating_profit',
        'datadate': 'datadate',
        'fyr': 'fiscal_year_end_month',
        'fyearq': 'fiscal_year',
        'fqtr': 'fiscal_quarter',
    }

    available = {k: v for k, v in column_map.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    # Convert types
    for col in ['revenue', 'operating_profit', 'fiscal_year', 'fiscal_quarter']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['datadate'] = pd.to_datetime(df['datadate'])
    df['segment'] = df['segment_raw'].apply(normalize_segment_name)

    # Filter to known segments
    known_segments = {'Flat-Rolled', 'USSE', 'Tubular', 'Mini Mill'}
    df = df[df['segment'].isin(known_segments)].copy()

    df = df.sort_values(['segment', 'fiscal_year', 'fiscal_quarter']).reset_index(drop=True)

    # Cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path)
    print(f"  Cached to {cache_path}")

    return df


def fetch_segment_annual(start_year: int = 2003, end_year: int = 2024,
                          use_cache: bool = True) -> pd.DataFrame:
    """Fetch USS annual segment data from WRDS comp.wrds_segmerged (cross-validation)."""
    cache_path = CACHE_DIR / 'uss_segment_annual.parquet'

    if use_cache and cache_path.exists():
        from datetime import datetime
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        if age_days <= 30:
            print(f"Loading USS segment annual from cache ({age_days} days old)")
            return pd.read_parquet(cache_path)

    api_token = os.getenv('WRDS_API_TOKEN')
    if not api_token or api_token == 'your_api_token_here':
        return pd.DataFrame()

    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {api_token}',
        'Accept': 'application/json'
    })

    print(f"Fetching USS segment annual data from WRDS...")

    params = {
        'tic': 'X',
        'stype': 'BUSSEG',
        'datadate__gte': f'{start_year}-01-01',
        'datadate__lte': f'{end_year}-12-31',
        'limit': 500,
    }

    all_results = []
    url = f"{BASE_URL}/comp.wrds_segmerged/"

    while url:
        try:
            resp = session.get(url, params=params if '?' not in url else None)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get('results', []))
            url = data.get('next')
            params = None
        except requests.RequestException as e:
            print(f"WARNING: WRDS annual segment API failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    if not all_results:
        return pd.DataFrame()

    df = pd.DataFrame(all_results)

    column_map = {
        'snms': 'segment_raw',
        'sales': 'revenue',
        'ops': 'operating_profit',
        'datadate': 'datadate',
        'fyear': 'fiscal_year',
    }

    available = {k: v for k, v in column_map.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    for col in ['revenue', 'operating_profit', 'fiscal_year']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df['datadate'] = pd.to_datetime(df['datadate'])
    df['segment'] = df['segment_raw'].apply(normalize_segment_name)

    known_segments = {'Flat-Rolled', 'USSE', 'Tubular', 'Mini Mill'}
    df = df[df['segment'].isin(known_segments)].copy()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path)

    return df


def save_csvs(quarterly_df: pd.DataFrame, annual_df: pd.DataFrame):
    """Save segment data as CSVs."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if len(quarterly_df) > 0:
        quarterly_df['quarter'] = (
            quarterly_df['fiscal_year'].astype(int).astype(str) + 'Q' +
            quarterly_df['fiscal_quarter'].astype(int).astype(str)
        )
        cols = ['quarter', 'datadate', 'segment', 'fiscal_year', 'fiscal_quarter',
                'revenue', 'operating_profit']
        cols = [c for c in cols if c in quarterly_df.columns]
        quarterly_df[cols].to_csv(OUTPUT_DIR / 'uss_segment_quarterly.csv', index=False)
        print(f"  Saved {OUTPUT_DIR / 'uss_segment_quarterly.csv'} ({len(quarterly_df)} rows)")

    if len(annual_df) > 0:
        cols = ['datadate', 'segment', 'fiscal_year', 'revenue', 'operating_profit']
        cols = [c for c in cols if c in annual_df.columns]
        annual_df[cols].to_csv(OUTPUT_DIR / 'uss_segment_annual.csv', index=False)
        print(f"  Saved {OUTPUT_DIR / 'uss_segment_annual.csv'} ({len(annual_df)} rows)")


def cross_validate(quarterly_df: pd.DataFrame):
    """Cross-validate WRDS quarterly sums against known 10-K segment values."""
    from data.uss_segment_data import USS_SEGMENT_DATA

    print("\n--- Cross-Validation: WRDS vs 10-K Segment Data ---")

    for seg_name, data in USS_SEGMENT_DATA.items():
        print(f"\n  {seg_name}:")
        for year, rev_10k, ebitda_10k, shipments_10k, price_10k in data:
            if len(quarterly_df) == 0:
                print(f"    FY{year}: No WRDS data available")
                continue

            wrds_year = quarterly_df[
                (quarterly_df['segment'] == seg_name) &
                (quarterly_df['fiscal_year'] == year)
            ]
            if len(wrds_year) == 0:
                print(f"    FY{year}: No WRDS data")
                continue

            wrds_rev = wrds_year['revenue'].sum()
            diff_pct = (wrds_rev - rev_10k) / rev_10k * 100 if rev_10k else 0
            status = 'OK' if abs(diff_pct) < 5 else 'REVIEW'
            print(f"    FY{year}: WRDS ${wrds_rev:,.0f}M vs 10-K ${rev_10k:,.0f}M "
                  f"({diff_pct:+.1f}%) [{status}]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch USS segment data from WRDS')
    parser.add_argument('--refresh', action='store_true', help='Force refresh')
    parser.add_argument('--start-year', type=int, default=2003)
    parser.add_argument('--end-year', type=int, default=2024)
    args = parser.parse_args()

    quarterly_df = fetch_segment_quarterly(
        args.start_year, args.end_year, use_cache=not args.refresh
    )
    annual_df = fetch_segment_annual(
        args.start_year, args.end_year, use_cache=not args.refresh
    )

    save_csvs(quarterly_df, annual_df)

    if len(quarterly_df) > 0:
        cross_validate(quarterly_df)

        print("\n--- Segment Coverage ---")
        for seg in quarterly_df['segment'].unique():
            n = len(quarterly_df[quarterly_df['segment'] == seg])
            years = quarterly_df[quarterly_df['segment'] == seg]['fiscal_year']
            print(f"  {seg}: {n} quarterly obs (FY{int(years.min())}-FY{int(years.max())})")
    else:
        print("\nNo WRDS data available. Hardcoded fallback will be used.")

    print("\nDone.")


if __name__ == '__main__':
    main()
