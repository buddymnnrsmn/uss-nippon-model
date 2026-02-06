#!/usr/bin/env python3
"""
Data Scraper for Model Audit
=============================

Automatically collects publicly available data for model verification:
- SEC EDGAR filings (USS 10-K, proxy statements)
- Steel price indices (where available via public APIs)
- Company press releases and investor presentations

Usage:
    python data_scraper.py --all
    python data_scraper.py --sec-filings
    python data_scraper.py --steel-prices
    python data_scraper.py --analyst-data

Requirements:
    pip install requests beautifulsoup4 sec-edgar-downloader pandas
"""

import argparse
import requests
from pathlib import Path
import json
import csv
from datetime import datetime
import time


class DataScraper:
    """Scrape publicly available data for audit verification"""

    def __init__(self):
        self.evidence_dir = Path(__file__).parent.parent / "evidence"
        self.evidence_dir.mkdir(exist_ok=True)
        self.headers = {
            'User-Agent': 'Model Audit Bot / research@example.com'  # SEC requires user agent
        }

    def fetch_sec_filing(self, cik, filing_type='10-K', year=2023):
        """Fetch USS SEC filings from EDGAR

        Args:
            cik: Central Index Key (USS = '0001163302')
            filing_type: '10-K', 'DEF 14A' (proxy), '8-K', etc.
            year: Filing year
        """
        print(f"\nFetching {filing_type} for CIK {cik} ({year})...")

        # SEC EDGAR API endpoint
        base_url = "https://www.sec.gov/cgi-bin/browse-edgar"

        # Search for filings
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': f'{year}1231',
            'owner': 'exclude',
            'output': 'atom',
            'count': '10'
        }

        try:
            response = requests.get(base_url, params=params, headers=self.headers)
            response.raise_for_status()

            # Parse XML/Atom feed to find filing URL
            # For now, just save the response and provide manual instructions
            output_file = self.evidence_dir / f"USS_{filing_type}_{year}_search.xml"
            with open(output_file, 'w') as f:
                f.write(response.text)

            print(f"✓ Filing search results saved to: {output_file}")
            print(f"  Manual step: Visit https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type}")
            print(f"  Download the {year} {filing_type} and save to: {self.evidence_dir}/USS_{filing_type}_{year}.pdf")

            # Create a metadata file
            metadata = {
                'cik': cik,
                'filing_type': filing_type,
                'year': year,
                'search_url': f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={filing_type}",
                'scraped_date': datetime.now().isoformat(),
                'status': 'Manual download required'
            }

            metadata_file = self.evidence_dir / f"USS_{filing_type}_{year}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            return True

        except Exception as e:
            print(f"✗ Error fetching SEC filing: {e}")
            return False

    def fetch_steel_price_estimates(self):
        """Fetch publicly available steel price data

        Note: Most steel price indices (Platts, CRU, MEPS) are subscription-only.
        This function provides links to free/public data sources.
        """
        print("\nFetching steel price reference data...")

        sources = [
            {
                'name': 'CME HRC Futures (Settlement Prices)',
                'url': 'https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html',
                'description': 'Historical settlement prices for HRC futures (free)',
                'data_type': 'US HRC Midwest',
                'instructions': 'Download CSV from website, calculate 2023 average'
            },
            {
                'name': 'SteelBenchmarker',
                'url': 'http://www.steelbenchmarker.com/files/history.pdf',
                'description': 'Historical composite steel prices (free monthly data)',
                'data_type': 'Composite steel price index',
                'instructions': 'Check PDF for 2023 monthly averages'
            },
            {
                'name': 'World Steel Association',
                'url': 'https://worldsteel.org/steel-topics/statistics/prices/',
                'description': 'Global steel price trends (limited free data)',
                'data_type': 'Multiple products',
                'instructions': 'Review public charts, may need to estimate'
            },
            {
                'name': 'FRED Economic Data (PPI Steel)',
                'url': 'https://fred.stlouisfed.org/series/WPU101',
                'description': 'Producer Price Index for steel mill products',
                'data_type': 'PPI Index (not direct prices)',
                'instructions': 'Download CSV, use as relative indicator'
            }
        ]

        # Save source list to file
        output_file = self.evidence_dir / "steel_price_sources.json"
        with open(output_file, 'w') as f:
            json.dump(sources, indent=2, fp=f)

        print(f"\n✓ Steel price sources saved to: {output_file}")
        print("\nPUBLICLY AVAILABLE SOURCES:")
        print("-" * 80)
        for source in sources:
            print(f"\n{source['name']}")
            print(f"  URL: {source['url']}")
            print(f"  Data: {source['data_type']}")
            print(f"  Instructions: {source['instructions']}")

        # Try to fetch CME data (if available via their API)
        print("\n" + "-" * 80)
        print("Attempting to fetch CME HRC Futures data...")
        try:
            # Note: CME doesn't have a simple public API, would need web scraping
            # For now, just provide instructions
            print("⚠ CME data requires manual download:")
            print("  1. Visit: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html")
            print("  2. Select date range: Jan 1, 2023 - Dec 31, 2023")
            print("  3. Export to CSV")
            print("  4. Save to: audits/evidence/CME_HRC_Futures_2023.csv")
            print("  5. Calculate average of settlement prices")

        except Exception as e:
            print(f"✗ Error: {e}")

        return True

    def fetch_company_presentations(self):
        """Fetch USS investor presentations and press releases"""
        print("\nFetching company presentation links...")

        # USS Investor Relations page
        ir_url = "https://www.ussteel.com/investors"

        sources = [
            {
                'name': 'USS Q4 2023 Earnings Presentation',
                'url': 'https://www.ussteel.com/investors/events-presentations',
                'instructions': 'Download Q4 2023 earnings deck, look for capital project details'
            },
            {
                'name': 'Nippon Steel - USS Acquisition Press Release',
                'url': 'https://www.nipponsteel.com/en/news/',
                'instructions': 'Search for December 2023 USS acquisition announcement'
            },
            {
                'name': 'USS Press Releases',
                'url': 'https://www.ussteel.com/newsroom/press-releases',
                'instructions': 'Search for Big River Steel Phase 2, Gary Works, Mon Valley announcements'
            }
        ]

        output_file = self.evidence_dir / "company_sources.json"
        with open(output_file, 'w') as f:
            json.dump(sources, indent=2, fp=f)

        print(f"✓ Company sources saved to: {output_file}")
        print("\nCOMPANY DATA SOURCES:")
        print("-" * 80)
        for source in sources:
            print(f"\n{source['name']}")
            print(f"  URL: {source['url']}")
            print(f"  Instructions: {source['instructions']}")

        return True

    def fetch_analyst_data(self):
        """Provide links to analyst report sources"""
        print("\nFetching analyst report information...")

        sources = [
            {
                'name': 'Barclays Fairness Opinion',
                'location': 'USS Proxy Statement (DEF 14A)',
                'sec_filing': 'DEF 14A',
                'instructions': 'Download proxy from SEC EDGAR, Barclays opinion is typically in Annex A or B'
            },
            {
                'name': 'Goldman Sachs Fairness Opinion',
                'location': 'USS Proxy Statement (DEF 14A)',
                'sec_filing': 'DEF 14A',
                'instructions': 'Download proxy from SEC EDGAR, Goldman opinion is typically in Annex A or B'
            },
            {
                'name': 'Wall Street Research (if available)',
                'location': 'Bloomberg, FactSet, or Capital IQ',
                'sec_filing': 'N/A',
                'instructions': 'Requires subscription access to Bloomberg/FactSet'
            }
        ]

        output_file = self.evidence_dir / "analyst_sources.json"
        with open(output_file, 'w') as f:
            json.dump(sources, indent=2, fp=f)

        print(f"✓ Analyst sources saved to: {output_file}")
        print("\nANALYST REPORT SOURCES:")
        print("-" * 80)
        for source in sources:
            print(f"\n{source['name']}")
            print(f"  Location: {source['location']}")
            print(f"  Instructions: {source['instructions']}")

        return True

    def create_checklist(self):
        """Create a comprehensive data collection checklist"""
        checklist = {
            'sec_filings': [
                {'item': 'USS 2023 10-K', 'status': 'pending', 'priority': 'high'},
                {'item': 'USS 2024 Proxy Statement (DEF 14A)', 'status': 'pending', 'priority': 'high'},
                {'item': 'USS Q4 2023 8-K (earnings)', 'status': 'pending', 'priority': 'medium'},
            ],
            'steel_prices': [
                {'item': 'CME HRC Futures 2023 data', 'status': 'pending', 'priority': 'high'},
                {'item': 'SteelBenchmarker 2023 averages', 'status': 'pending', 'priority': 'medium'},
                {'item': 'FRED PPI Steel data', 'status': 'pending', 'priority': 'low'},
            ],
            'company_data': [
                {'item': 'USS Q4 2023 earnings presentation', 'status': 'pending', 'priority': 'high'},
                {'item': 'BR2 Phase 2 press release', 'status': 'pending', 'priority': 'medium'},
                {'item': 'NSA announcement press release', 'status': 'pending', 'priority': 'high'},
            ],
            'analyst_data': [
                {'item': 'Barclays fairness opinion (in proxy)', 'status': 'pending', 'priority': 'high'},
                {'item': 'Goldman fairness opinion (in proxy)', 'status': 'pending', 'priority': 'high'},
            ]
        }

        output_file = self.evidence_dir / "data_collection_checklist.json"
        with open(output_file, 'w') as f:
            json.dump(checklist, indent=2, fp=f)

        print(f"\n✓ Checklist created: {output_file}")
        return True


def main():
    parser = argparse.ArgumentParser(description='Scrape data for model audit')
    parser.add_argument('--all', action='store_true', help='Fetch all available data')
    parser.add_argument('--sec-filings', action='store_true', help='Fetch SEC filings')
    parser.add_argument('--steel-prices', action='store_true', help='Fetch steel price data')
    parser.add_argument('--company-data', action='store_true', help='Fetch company presentations')
    parser.add_argument('--analyst-data', action='store_true', help='Fetch analyst report info')

    args = parser.parse_args()

    scraper = DataScraper()

    print("=" * 80)
    print("DATA SCRAPER - MODEL AUDIT")
    print("=" * 80)
    print("\nThis script helps collect publicly available data for model verification.")
    print("Most data requires manual download due to paywalls/subscriptions.")
    print(f"\nEvidence will be saved to: {scraper.evidence_dir}")

    if args.all or args.sec_filings:
        # USS CIK = 1163302
        scraper.fetch_sec_filing('0001163302', '10-K', 2023)
        time.sleep(1)  # Be nice to SEC servers
        scraper.fetch_sec_filing('0001163302', 'DEF 14A', 2024)  # Proxy with fairness opinions

    if args.all or args.steel_prices:
        scraper.fetch_steel_price_estimates()

    if args.all or args.company_data:
        scraper.fetch_company_presentations()

    if args.all or args.analyst_data:
        scraper.fetch_analyst_data()

    # Always create checklist
    scraper.create_checklist()

    print("\n" + "=" * 80)
    print("DATA SCRAPING COMPLETE")
    print("=" * 80)
    print(f"\nNext steps:")
    print("1. Review files in {scraper.evidence_dir}/")
    print("2. Download required documents from provided URLs")
    print("3. Extract data into CSV templates in data_collection/")
    print("4. Run verification: python verify_inputs.py")
    print()


if __name__ == "__main__":
    main()
