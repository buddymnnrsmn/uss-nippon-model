#!/usr/bin/env python3
"""
Fetch Free Public Data
======================

Automatically fetch and extract data from free public sources:
1. SEC EDGAR filings (USS 10-K)
2. FRED economic data (Steel PPI)
3. Web scraping for public steel prices

Usage:
    python fetch_free_data.py --all
"""

import requests
import json
import csv
from datetime import datetime
from pathlib import Path
import time


class FreeDataFetcher:
    """Fetch data from free public sources"""

    def __init__(self):
        self.evidence_dir = Path(__file__).parent.parent / "evidence"
        self.data_dir = Path(__file__).parent.parent / "data_collection"
        self.headers = {
            'User-Agent': 'Model Audit Research / educational@example.com'
        }

    def fetch_sec_edgar_10k(self):
        """Fetch USS 10-K from SEC EDGAR"""
        print("\n" + "=" * 80)
        print("FETCHING USS 2023 10-K FROM SEC EDGAR")
        print("=" * 80)

        # USS CIK
        cik = "0001163302"

        # SEC EDGAR API - get company filings
        print("\nSearching for 2023 10-K filing...")

        # Get recent filings
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            # Find 10-K filings
            filings = data.get('filings', {}).get('recent', {})
            forms = filings.get('form', [])
            dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])

            # Find 2023 10-K
            tenk_2023 = None
            for i, form in enumerate(forms):
                if form == '10-K' and dates[i].startswith('2024'):  # 2023 10-K filed in early 2024
                    tenk_2023 = {
                        'form': form,
                        'date': dates[i],
                        'accession': accession_numbers[i]
                    }
                    break

            if tenk_2023:
                print(f"✓ Found 2023 10-K filed on {tenk_2023['date']}")
                print(f"  Accession: {tenk_2023['accession']}")

                # Build document URL
                accession_clean = tenk_2023['accession'].replace('-', '')
                doc_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={tenk_2023['accession']}&xbrl_type=v"

                print(f"\n📄 10-K Document URL:")
                print(f"  {doc_url}")

                # Save metadata
                metadata = {
                    'company': 'United States Steel Corporation',
                    'cik': cik,
                    'filing_type': '10-K',
                    'fiscal_year': 2023,
                    'filing_date': tenk_2023['date'],
                    'accession_number': tenk_2023['accession'],
                    'document_url': doc_url,
                    'viewer_url': f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={tenk_2023['accession']}&xbrl_type=v",
                    'html_url': f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{tenk_2023['accession'].replace('-', '')}-index.htm"
                }

                metadata_file = self.evidence_dir / "USS_10K_2023_filing_info.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, indent=2, fp=f)

                print(f"\n✓ Filing info saved to: {metadata_file}")

                # Provide manual instructions
                print("\n" + "-" * 80)
                print("MANUAL DATA EXTRACTION REQUIRED")
                print("-" * 80)
                print("\nThe 10-K is available, but automatic extraction is complex.")
                print("Please visit the document URL above and extract:")
                print("\n1. Segment Data (typically in 'Business' or 'Segment Information' section):")
                print("   - Flat-Rolled shipments (000 tons)")
                print("   - Mini Mill shipments (000 tons)")
                print("   - USSE shipments (000 tons)")
                print("   - Tubular shipments (000 tons)")
                print("\n2. Balance Sheet (typically near end of document):")
                print("   - Total debt")
                print("   - Cash and equivalents")
                print("   - Shares outstanding (from cover page or equity section)")
                print("\n3. Then fill into: data_collection/uss_2023_data.csv")

                return metadata
            else:
                print("⚠ 2023 10-K not found in recent filings")
                return None

        except Exception as e:
            print(f"✗ Error fetching SEC data: {e}")
            return None

    def fetch_fred_steel_ppi(self):
        """Fetch FRED Steel PPI data"""
        print("\n" + "=" * 80)
        print("FETCHING FRED STEEL PPI DATA")
        print("=" * 80)

        # FRED API endpoint (public data, no API key needed for download)
        series_id = "WPU101"  # Producer Price Index: Steel Mill Products

        print(f"\nFetching PPI data for series {series_id}...")

        # Provide CSV download URL
        csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2023-01-01&coed=2023-12-31"

        try:
            response = requests.get(csv_url, headers=self.headers)
            response.raise_for_status()

            # Save CSV
            output_file = self.evidence_dir / "FRED_Steel_PPI_2023.csv"
            with open(output_file, 'w') as f:
                f.write(response.text)

            # Parse and calculate average
            lines = response.text.strip().split('\n')
            if len(lines) > 1:
                header = lines[0]
                data_lines = lines[1:]

                values = []
                for line in data_lines:
                    parts = line.split(',')
                    if len(parts) >= 2 and parts[1] != '.':
                        try:
                            values.append(float(parts[1]))
                        except:
                            pass

                if values:
                    avg_ppi = sum(values) / len(values)
                    print(f"✓ Data downloaded: {len(values)} monthly observations")
                    print(f"✓ 2023 Average PPI: {avg_ppi:.2f}")
                    print(f"✓ Saved to: {output_file}")

                    # Save summary
                    summary = {
                        'series_id': series_id,
                        'series_name': 'Producer Price Index - Steel Mill Products',
                        'year': 2023,
                        'observations': len(values),
                        'average_index': avg_ppi,
                        'min_index': min(values),
                        'max_index': max(values),
                        'source': 'Federal Reserve Economic Data (FRED)',
                        'note': 'PPI is an index, not absolute prices. Use for relative comparison.',
                        'csv_file': str(output_file)
                    }

                    summary_file = self.evidence_dir / "FRED_Steel_PPI_2023_summary.json"
                    with open(summary_file, 'w') as f:
                        json.dump(summary, indent=2, fp=f)

                    return summary

            print("⚠ Could not parse PPI data")
            return None

        except Exception as e:
            print(f"✗ Error fetching FRED data: {e}")
            print(f"\nManual download URL: {csv_url}")
            return None

    def get_cme_instructions(self):
        """Provide CME HRC futures download instructions"""
        print("\n" + "=" * 80)
        print("CME HRC FUTURES DATA - MANUAL DOWNLOAD")
        print("=" * 80)

        print("\nCME Group provides free historical futures data, but requires manual download.")
        print("\nSTEP-BY-STEP INSTRUCTIONS:")
        print("-" * 80)

        print("\n1. Visit CME HRC Futures page:")
        print("   https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html")

        print("\n2. Set date range:")
        print("   - Start Date: 01/01/2023")
        print("   - End Date: 12/31/2023")

        print("\n3. Click 'Apply' to filter dates")

        print("\n4. Look for 'Export' or 'Download' button (usually top-right)")
        print("   - Select CSV format")
        print("   - Download file")

        print("\n5. Save as:")
        print(f"   {self.evidence_dir / 'CME_HRC_Futures_2023.csv'}")

        print("\n6. Calculate 2023 average:")
        print("   - Open CSV in Excel/Python")
        print("   - Average the 'Settle' column")
        print("   - This gives you 2023 HRC average price")

        print("\n7. Fill into:")
        print(f"   {self.data_dir / 'steel_prices_2023.csv'}")
        print("   - Row: US_HRC_Midwest")
        print("   - Column: Source_Value")

        print("\nNOTE: CME futures prices are a good proxy for spot prices.")
        print("      They typically track within 5-10% of actual realized prices.")
        print()

    def get_steelbenchmarker_instructions(self):
        """Provide SteelBenchmarker download instructions"""
        print("\n" + "=" * 80)
        print("STEELBENCHMARKER DATA - MANUAL DOWNLOAD")
        print("=" * 80)

        print("\nSteelBenchmarker provides free historical composite steel prices.")
        print("\nSTEP-BY-STEP INSTRUCTIONS:")
        print("-" * 80)

        print("\n1. Visit SteelBenchmarker history page:")
        print("   http://www.steelbenchmarker.com/files/history.pdf")

        print("\n2. The PDF will download automatically")

        print("\n3. Save as:")
        print(f"   {self.evidence_dir / 'SteelBenchmarker_History.pdf'}")

        print("\n4. Open PDF and find 2023 section")

        print("\n5. Extract monthly composite prices for 2023:")
        print("   - January 2023: $___")
        print("   - February 2023: $___")
        print("   - ... (all 12 months)")

        print("\n6. Calculate 2023 average")

        print("\n7. Fill into:")
        print(f"   {self.data_dir / 'steel_prices_2023.csv'}")
        print("   - Use as reference for US HRC if CME not available")

        print("\nNOTE: SteelBenchmarker is a composite index.")
        print("      It may differ from specific product prices (HRC, CRC, etc.)")
        print()

    def generate_collection_script(self):
        """Generate a helper script for data collection"""
        print("\n" + "=" * 80)
        print("GENERATING DATA COLLECTION HELPER")
        print("=" * 80)

        script = """#!/bin/bash
# Data Collection Helper Script
# Run this after manually downloading files

echo "==================================================================="
echo "DATA COLLECTION STATUS CHECK"
echo "==================================================================="
echo ""

# Check for SEC 10-K
if [ -f "../evidence/USS_10K_2023.pdf" ]; then
    echo "✓ USS 10-K downloaded"
else
    echo "⚠ USS 10-K missing - download from SEC EDGAR"
    echo "  URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K"
fi

# Check for CME data
if [ -f "../evidence/CME_HRC_Futures_2023.csv" ]; then
    echo "✓ CME HRC Futures downloaded"
else
    echo "⚠ CME HRC Futures missing - download from CME Group"
    echo "  URL: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html"
fi

# Check for SteelBenchmarker
if [ -f "../evidence/SteelBenchmarker_History.pdf" ]; then
    echo "✓ SteelBenchmarker downloaded"
else
    echo "⚠ SteelBenchmarker missing - download from SteelBenchmarker.com"
    echo "  URL: http://www.steelbenchmarker.com/files/history.pdf"
fi

# Check for Proxy
if [ -f "../evidence/USS_Proxy_2024.pdf" ]; then
    echo "✓ USS Proxy downloaded"
else
    echo "⚠ USS Proxy missing - download from SEC EDGAR"
    echo "  URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=DEF%2014A"
fi

echo ""
echo "==================================================================="
echo "CSV TEMPLATE STATUS"
echo "==================================================================="
echo ""

# Check if templates are filled
python3 << 'EOF'
import csv
from pathlib import Path

templates = {
    'USS 2023 Data': '../data_collection/uss_2023_data.csv',
    'Steel Prices': '../data_collection/steel_prices_2023.csv',
    'Balance Sheet': '../data_collection/balance_sheet_items.csv',
}

for name, path in templates.items():
    p = Path(path)
    if p.exists():
        with open(p, 'r') as f:
            content = f.read()
            has_data = 'Source_Value' in content and ',,' not in content[:200]
            status = "✓ Data filled" if has_data else "⚠ Template empty"
    else:
        status = "✗ Missing"
    print(f"{name:.<30} {status}")
EOF

echo ""
echo "Next step: Run python verify_inputs.py"
echo ""
"""

        script_file = Path(__file__).parent / "check_data_status.sh"
        with open(script_file, 'w') as f:
            f.write(script)

        # Make executable
        import os
        os.chmod(script_file, 0o755)

        print(f"✓ Helper script created: {script_file}")
        print(f"\nRun with: bash {script_file}")
        print()


def main():
    print("=" * 80)
    print("FREE DATA COLLECTION - AUTOMATED FETCHING")
    print("=" * 80)
    print("\nAttempting to fetch data from free public sources...")
    print("Some sources may require manual download due to access restrictions.")

    fetcher = FreeDataFetcher()

    # Fetch what we can automatically
    print("\n" + "=" * 80)
    print("STEP 1: AUTOMATED DATA COLLECTION")
    print("=" * 80)

    # SEC EDGAR
    sec_data = fetcher.fetch_sec_edgar_10k()
    time.sleep(1)  # Be nice to servers

    # FRED
    fred_data = fetcher.fetch_fred_steel_ppi()
    time.sleep(1)

    # Provide manual instructions for remaining sources
    print("\n" + "=" * 80)
    print("STEP 2: MANUAL DOWNLOAD REQUIRED")
    print("=" * 80)

    fetcher.get_cme_instructions()
    fetcher.get_steelbenchmarker_instructions()

    # Generate helper script
    fetcher.generate_collection_script()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print("\n✓ Automated:")
    if sec_data:
        print("  - SEC 10-K location identified")
    if fred_data:
        print("  - FRED Steel PPI downloaded")

    print("\n⚠ Manual download needed:")
    print("  - USS 10-K (extract segment data)")
    print("  - CME HRC Futures CSV")
    print("  - SteelBenchmarker PDF (optional)")

    print("\nNext steps:")
    print("1. Download files from URLs provided above")
    print("2. Extract data into CSV templates")
    print("3. Run: python verify_inputs.py")
    print()


if __name__ == "__main__":
    main()
