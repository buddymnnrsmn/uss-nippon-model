#!/usr/bin/env python3
"""
Fetch additional economic indicators from FRED (Federal Reserve Economic Data).

FRED API is free — requires an API key from https://fred.stlouisfed.org/docs/api/api_key.html
Falls back to bulk CSV download URLs if no API key is available.

Indicators fetched:
  - INDPRO: Industrial Production Index (monthly)
  - TLNRESCONS: Non-residential Construction Spending (monthly)
  - DGORDER: Durable Goods Orders (monthly)
  - IMP0811: Steel Imports value (monthly, Census via FRED)
  - CAPUTLG3311A2S: Steel Capacity Utilization (quarterly)
  - GDP: Real GDP (quarterly)
  - IPMAN: Manufacturing Industrial Production (monthly)
  - PERMIT: Building Permits (monthly, leading indicator)
"""

import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / 'local' / '.env'
load_dotenv(env_path)

OUTPUT_DIR = Path(__file__).parent.parent / 'market-data' / 'exports' / 'processed'

# FRED series definitions
FRED_SERIES = {
    'industrial_production': {
        'series_id': 'INDPRO',
        'description': 'Industrial Production Index (2017=100)',
        'frequency': 'monthly',
        'filename': 'industrial_production.csv',
    },
    'nonres_construction': {
        'series_id': 'TLNRESCONS',
        'description': 'Total Non-Residential Construction Spending ($M)',
        'frequency': 'monthly',
        'filename': 'nonres_construction.csv',
    },
    'durable_goods_orders': {
        'series_id': 'DGORDER',
        'description': 'Durable Goods Orders ($M)',
        'frequency': 'monthly',
        'filename': 'durable_goods_orders.csv',
    },
    'mfg_industrial_production': {
        'series_id': 'IPMAN',
        'description': 'Manufacturing Industrial Production Index (2017=100)',
        'frequency': 'monthly',
        'filename': 'mfg_industrial_production.csv',
    },
    'building_permits': {
        'series_id': 'PERMIT',
        'description': 'New Private Housing Units Authorized (thousands)',
        'frequency': 'monthly',
        'filename': 'building_permits.csv',
    },
    'gdp_real': {
        'series_id': 'GDPC1',
        'description': 'Real GDP (Billions of Chained 2017 Dollars)',
        'frequency': 'quarterly',
        'filename': 'gdp_real.csv',
    },
    'steel_capacity_util': {
        'series_id': 'CAPUTLG3311A2S',
        'description': 'Iron and Steel Capacity Utilization (%)',
        'frequency': 'monthly',
        'filename': 'steel_capacity_util.csv',
    },
    'steel_imports': {
        'series_id': 'BOPGSTB',
        'description': 'US Trade Balance: Goods (proxy for import pressure, $M)',
        'frequency': 'monthly',
        'filename': 'trade_balance_goods.csv',
    },
}


def fetch_fred_series(series_id: str, api_key: str, start_date: str = '2000-01-01') -> pd.DataFrame:
    """Fetch a single FRED series via API."""
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start_date,
        'sort_order': 'asc',
    }

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if 'observations' not in data:
        print(f"  WARNING: No observations for {series_id}")
        return pd.DataFrame()

    df = pd.DataFrame(data['observations'])
    df = df[['date', 'value']].copy()
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value'])

    return df


def fetch_fred_csv_fallback(series_id: str, start_date: str = '2000-01-01') -> pd.DataFrame:
    """Fetch FRED series via public CSV download (no API key needed)."""
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}'
    try:
        df = pd.read_csv(url)
        df.columns = ['date', 'value']
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df = df.dropna(subset=['value'])
        return df
    except Exception as e:
        print(f"  CSV fallback failed for {series_id}: {e}")
        return pd.DataFrame()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fetch FRED economic indicators')
    parser.add_argument('--api-key', default=None, help='FRED API key (or set FRED_API_KEY env var)')
    parser.add_argument('--start-date', default='2000-01-01')
    parser.add_argument('--series', nargs='*', default=None, help='Specific series to fetch (default: all)')
    args = parser.parse_args()

    api_key = args.api_key or os.getenv('FRED_API_KEY')
    use_api = bool(api_key)

    if use_api:
        print(f"Using FRED API with key ...{api_key[-6:]}")
    else:
        print("No FRED_API_KEY found — using CSV download fallback (slower, may be rate-limited)")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    series_to_fetch = args.series or list(FRED_SERIES.keys())
    results = {}

    for name in series_to_fetch:
        if name not in FRED_SERIES:
            print(f"  Unknown series: {name}")
            continue

        info = FRED_SERIES[name]
        out_path = OUTPUT_DIR / info['filename']
        print(f"Fetching {name} ({info['series_id']}: {info['description']})...")

        if use_api:
            df = fetch_fred_series(info['series_id'], api_key, args.start_date)
        else:
            df = fetch_fred_csv_fallback(info['series_id'], args.start_date)

        if df.empty:
            print(f"  FAILED — no data returned")
            continue

        df.to_csv(out_path, index=False)
        print(f"  Saved {out_path} ({len(df)} rows, {df.date.min().date()} to {df.date.max().date()})")
        results[name] = len(df)

        time.sleep(0.5)  # Rate limiting

    print(f"\nDone. Fetched {len(results)}/{len(series_to_fetch)} series.")
    for name, n in results.items():
        print(f"  {name}: {n} observations")


if __name__ == '__main__':
    main()
