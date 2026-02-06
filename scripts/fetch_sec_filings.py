#!/usr/bin/env python3
"""
Download USS 10-K and DEFM14A filings from SEC EDGAR.

Uses the same pattern as references/steel_comps/download_sec_filings.py.
Rate-limited to comply with SEC EDGAR fair access policy.
"""

import gzip
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Output locations
REFERENCES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "references")
EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit-verification", "evidence")

# SEC EDGAR configuration
USER_AGENT = "FinancialModelProject research@example.com"
USS_CIK = "0001163302"

# Known filings
FILINGS = [
    {
        "name": "USS 10-K FY2023",
        "filing_type": "10-K",
        "target_year": 2023,
        "output_path": os.path.join(REFERENCES_DIR, "uss_10k_2023.htm"),
    },
    {
        "name": "USS DEFM14A (Merger Proxy)",
        "filing_type": "DEFM14A",
        "target_year": 2024,  # Filed in 2024, relates to merger
        "output_path": os.path.join(EVIDENCE_DIR, "uss_defm14a_2024.htm"),
    },
]


def make_sec_request(url):
    """Make a request to SEC EDGAR with proper headers."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov" if "data.sec.gov" in url else "www.sec.gov",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read()
            if data[:2] == b"\x1f\x8b":
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


def get_submissions(cik):
    """Get filing history for a company from SEC EDGAR."""
    padded_cik = cik.lstrip("0").zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
    print(f"  Fetching submissions: {url}")

    data = make_sec_request(url)
    if data:
        return json.loads(data)
    return None


def find_filing(submissions, filing_type, target_year):
    """Find a specific filing in submissions data.

    For 10-K: FY2023 filed in early 2024
    For DEFM14A: Filed in 2024
    """
    if not submissions or "filings" not in submissions:
        return None

    recent = submissions["filings"]["recent"]
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    # For DEFM14A, also match PREM14A variants
    type_matches = [filing_type]
    if filing_type == "DEFM14A":
        type_matches.extend(["PREM14A", "DEFM14A/A"])

    for i, form in enumerate(forms):
        if form in type_matches:
            filing_date = filing_dates[i]
            filing_year = int(filing_date[:4])

            if filing_type == "10-K":
                # FY2023 10-K filed in early 2024
                if filing_year == target_year + 1 and int(filing_date[5:7]) <= 6:
                    return {
                        "accession": accessions[i],
                        "filing_date": filing_date,
                        "primary_doc": primary_docs[i],
                        "form": form,
                    }
            else:
                # DEFM14A filed in target_year
                if filing_year == target_year:
                    return {
                        "accession": accessions[i],
                        "filing_date": filing_date,
                        "primary_doc": primary_docs[i],
                        "form": form,
                    }

    # Fallback: most recent of target type
    for i, form in enumerate(forms):
        if form in type_matches:
            print(f"  Warning: Using fallback - most recent {form} from {filing_dates[i]}")
            return {
                "accession": accessions[i],
                "filing_date": filing_dates[i],
                "primary_doc": primary_docs[i],
                "form": form,
            }

    return None


def download_filing(cik, filing_info, output_path):
    """Download a filing document from SEC EDGAR."""
    accession_no_dash = filing_info["accession"].replace("-", "")
    cik_stripped = cik.lstrip("0")

    url = (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_stripped}/{accession_no_dash}/{filing_info['primary_doc']}"
    )

    print(f"  Downloading: {url}")

    data = make_sec_request(url)
    if data:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
        size = len(data)
        print(f"  Saved: {output_path} ({size:,} bytes)")
        return url, size
    return None, 0


def main():
    print("=" * 60)
    print("USS SEC EDGAR Filing Download")
    print("=" * 60)

    # Get USS submissions once
    submissions = get_submissions(USS_CIK)
    if not submissions:
        print("ERROR: Failed to retrieve USS submissions from SEC EDGAR")
        sys.exit(1)

    time.sleep(0.15)

    results = {}

    for filing_spec in FILINGS:
        print(f"\n--- {filing_spec['name']} ---")

        # Check if already downloaded
        if os.path.exists(filing_spec["output_path"]):
            size = os.path.getsize(filing_spec["output_path"])
            print(f"  Already exists: {filing_spec['output_path']} ({size:,} bytes)")
            results[filing_spec["name"]] = {
                "status": "already_exists",
                "path": filing_spec["output_path"],
                "size": size,
            }
            continue

        # Find the filing
        filing_info = find_filing(
            submissions, filing_spec["filing_type"], filing_spec["target_year"]
        )

        if not filing_info:
            print(f"  ERROR: Could not find {filing_spec['filing_type']} filing")
            results[filing_spec["name"]] = {"status": "not_found"}
            continue

        print(
            f"  Found: {filing_info['form']} filed {filing_info['filing_date']} "
            f"(accession: {filing_info['accession']})"
        )

        time.sleep(0.15)

        # Download
        source_url, size = download_filing(
            USS_CIK, filing_info, filing_spec["output_path"]
        )

        if source_url:
            results[filing_spec["name"]] = {
                "status": "downloaded",
                "path": filing_spec["output_path"],
                "source_url": source_url,
                "filing_date": filing_info["filing_date"],
                "accession": filing_info["accession"],
                "size": size,
            }
        else:
            results[filing_spec["name"]] = {"status": "download_failed"}

        time.sleep(0.15)

    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    for name, result in results.items():
        status_icon = {
            "downloaded": "OK",
            "already_exists": "OK (cached)",
            "not_found": "FAIL",
            "download_failed": "FAIL",
        }.get(result["status"], "?")

        size_str = f" ({result.get('size', 0):,} bytes)" if result.get("size") else ""
        print(f"  [{status_icon}] {name}{size_str}")

    # Save metadata
    metadata_path = os.path.join(EVIDENCE_DIR, "uss_sec_download_results.json")
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nMetadata saved to: {metadata_path}")

    return results


if __name__ == "__main__":
    main()
