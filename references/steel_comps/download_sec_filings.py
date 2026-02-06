#!/usr/bin/env python3
"""
Download SEC EDGAR filings for steel industry comparable companies.
"""

import gzip
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime
from io import BytesIO

BASE_DIR = "/tmp/claude/-workspaces-claude-in-docker-FinancialModel/2ef84a2d-9cc0-45dc-a52e-0fcd930735c2/scratchpad/steel_comps"
SEC_FILINGS_DIR = os.path.join(BASE_DIR, "sec_filings")

# User-Agent required by SEC EDGAR
USER_AGENT = "FinancialModelProject research@example.com"

# Company definitions with SEC details
SEC_COMPANIES = [
    # 10-K Filers (U.S. GAAP)
    {
        "company_name": "Cleveland-Cliffs Inc.",
        "ticker": "CLF",
        "cik": "0000764065",
        "filing_type": "10-K",
        "fy_end": "2023-12-31",
        "accounting_standard": "GAAP",
        "target_year": 2023
    },
    {
        "company_name": "Nucor Corporation",
        "ticker": "NUE",
        "cik": "0000073309",
        "filing_type": "10-K",
        "fy_end": "2023-12-31",
        "accounting_standard": "GAAP",
        "target_year": 2023
    },
    {
        "company_name": "Steel Dynamics, Inc.",
        "ticker": "STLD",
        "cik": "0001022671",
        "filing_type": "10-K",
        "fy_end": "2023-12-31",
        "accounting_standard": "GAAP",
        "target_year": 2023
    },
    {
        "company_name": "Olympic Steel, Inc.",
        "ticker": "ZEUS",
        "cik": "0000917470",
        "filing_type": "10-K",
        "fy_end": "2023-12-31",
        "accounting_standard": "GAAP",
        "target_year": 2023
    },
    {
        "company_name": "Commercial Metals Company",
        "ticker": "CMC",
        "cik": "0000022444",
        "filing_type": "10-K",
        "fy_end": "2023-08-31",  # Fiscal year ends August 31
        "accounting_standard": "GAAP",
        "target_year": 2023  # FY2023 ending Aug 31, 2023
    },
    # 20-F Filers (IFRS)
    {
        "company_name": "ArcelorMittal S.A.",
        "ticker": "MT",
        "cik": "0001243429",
        "filing_type": "20-F",
        "fy_end": "2023-12-31",
        "accounting_standard": "IFRS",
        "target_year": 2023
    },
    {
        "company_name": "POSCO Holdings Inc.",
        "ticker": "PKX",
        "cik": "0000889132",
        "filing_type": "20-F",
        "fy_end": "2023-12-31",
        "accounting_standard": "IFRS",
        "target_year": 2023
    },
    {
        "company_name": "Ternium S.A.",
        "ticker": "TX",
        "cik": "0001342874",
        "filing_type": "20-F",
        "fy_end": "2023-12-31",
        "accounting_standard": "IFRS",
        "target_year": 2023
    },
    {
        "company_name": "Gerdau S.A.",
        "ticker": "GGB",
        "cik": "0001073404",
        "filing_type": "20-F",
        "fy_end": "2023-12-31",
        "accounting_standard": "IFRS",
        "target_year": 2023
    },
]


def make_sec_request(url):
    """Make a request to SEC EDGAR with proper headers and rate limiting."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov" if "data.sec.gov" in url else "www.sec.gov"
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
            # Check if response is gzip compressed
            if data[:2] == b'\x1f\x8b':
                data = gzip.decompress(data)
            return data
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"  URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def get_company_filings(cik):
    """Get filing history for a company from SEC EDGAR."""
    # Pad CIK to 10 digits
    padded_cik = cik.lstrip('0').zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"

    print(f"  Fetching submissions from: {url}")

    data = make_sec_request(url)
    if data:
        return json.loads(data)
    return None


def find_target_filing(submissions, filing_type, target_year, fy_end_month=12):
    """Find the target filing in the submissions data."""
    if not submissions or "filings" not in submissions:
        return None

    recent = submissions["filings"]["recent"]

    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    # For CMC with August FY end, we look for filings in late 2023
    # For others with December FY end, we look for filings in early 2024

    for i, form in enumerate(forms):
        if form == filing_type:
            filing_date = filing_dates[i]
            filing_year = int(filing_date[:4])
            filing_month = int(filing_date[5:7])

            # Logic for finding the right filing:
            # - 10-K/20-F for Dec 31 FY2023 would be filed in early 2024
            # - 10-K for Aug 31 FY2023 would be filed in late Oct/Nov 2023

            if fy_end_month == 12:
                # December fiscal year end - filing should be in early next year
                if filing_year == target_year + 1 and filing_month <= 6:
                    return {
                        "accession": accessions[i],
                        "filing_date": filing_date,
                        "primary_doc": primary_docs[i]
                    }
            elif fy_end_month == 8:
                # August fiscal year end (CMC) - filing should be in late same year
                if filing_year == target_year and filing_month >= 9:
                    return {
                        "accession": accessions[i],
                        "filing_date": filing_date,
                        "primary_doc": primary_docs[i]
                    }

    # Fallback: return the most recent filing of the target type
    for i, form in enumerate(forms):
        if form == filing_type:
            print(f"  Warning: Using fallback - most recent {filing_type} from {filing_dates[i]}")
            return {
                "accession": accessions[i],
                "filing_date": filing_dates[i],
                "primary_doc": primary_docs[i]
            }

    return None


def download_filing(cik, accession, primary_doc, output_path):
    """Download the actual filing document."""
    # Format accession number for URL (remove dashes)
    accession_no_dash = accession.replace("-", "")

    # Construct the URL to the primary document
    url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_no_dash}/{primary_doc}"

    print(f"  Downloading from: {url}")

    data = make_sec_request(url)
    if data:
        with open(output_path, "wb") as f:
            f.write(data)
        return url
    return None


def main():
    results = []

    print("="*60)
    print("SEC EDGAR Filing Download Script")
    print("="*60)
    print()

    for company in SEC_COMPANIES:
        print(f"\nProcessing: {company['company_name']} ({company['ticker']})")
        print("-" * 50)

        result = {
            "company_name": company["company_name"],
            "ticker": company["ticker"],
            "cik": company["cik"],
            "filing_type": company["filing_type"],
            "fiscal_year_end": company["fy_end"],
            "accounting_standard": company["accounting_standard"],
            "file_path": None,
            "source_url": None,
            "download_status": "failed",
            "notes": ""
        }

        # Get company submissions
        submissions = get_company_filings(company["cik"])
        time.sleep(0.15)  # Rate limiting

        if not submissions:
            result["notes"] = "Failed to retrieve submissions data"
            results.append(result)
            continue

        # Determine fiscal year end month
        fy_end_month = 12
        if company["ticker"] == "CMC":
            fy_end_month = 8

        # Find the target filing
        filing = find_target_filing(
            submissions,
            company["filing_type"],
            company["target_year"],
            fy_end_month
        )

        if not filing:
            result["notes"] = f"Could not find {company['filing_type']} for FY{company['target_year']}"
            results.append(result)
            continue

        print(f"  Found filing: {filing['accession']} dated {filing['filing_date']}")

        # Determine output filename
        ext = os.path.splitext(filing["primary_doc"])[1] or ".htm"
        output_filename = f"{company['ticker']}_{company['filing_type']}_FY{company['target_year']}{ext}"
        output_path = os.path.join(SEC_FILINGS_DIR, output_filename)

        # Download the filing
        time.sleep(0.15)  # Rate limiting
        source_url = download_filing(company["cik"], filing["accession"], filing["primary_doc"], output_path)

        if source_url:
            file_size = os.path.getsize(output_path)
            print(f"  Downloaded: {output_filename} ({file_size:,} bytes)")

            result["file_path"] = output_path
            result["source_url"] = source_url
            result["download_status"] = "success"
            result["notes"] = f"Filed {filing['filing_date']}, {file_size:,} bytes"
        else:
            result["notes"] = "Download failed"

        results.append(result)
        time.sleep(0.15)  # Rate limiting between companies

    # Save results
    output_file = os.path.join(BASE_DIR, "metadata", "sec_download_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("SEC DOWNLOAD SUMMARY")
    print("="*60)

    success_count = sum(1 for r in results if r["download_status"] == "success")
    print(f"\nSuccessfully downloaded: {success_count}/{len(results)} filings")

    for r in results:
        status = "✓" if r["download_status"] == "success" else "✗"
        print(f"  {status} {r['ticker']}: {r['notes']}")

    return results


if __name__ == "__main__":
    main()
