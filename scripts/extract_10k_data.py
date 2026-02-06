#!/usr/bin/env python3
"""
Extract key financial data from USS 2023 10-K filing (HTML format).

Extracts:
- Debt schedule (verify $3,913M total)
- Cash and equivalents (verify $2,547M)
- Pension: PBO, plan assets, unfunded status
- Operating lease detail
- Share count: basic vs diluted
- Segment data: revenue, EBITDA, shipments by segment

Output: audit-verification/data_collection/uss_10k_extracted_data.json
"""

import json
import os
import re
import sys
from html.parser import HTMLParser


# File paths
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT_10K = os.path.join(BASE_DIR, "references", "uss_10k_2023.htm")
OUTPUT_JSON = os.path.join(
    BASE_DIR, "audit-verification", "data_collection", "uss_10k_extracted_data.json"
)

# Cross-check targets from WACC inputs.json
EXPECTED = {
    "total_debt_mm": 3913,
    "cash_mm": 2547,
    "net_debt_mm": 1366,
    "shares_outstanding_mm": 225,
}


class TextExtractor(HTMLParser):
    """Extract visible text from HTML, preserving table structure."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True
        elif tag == "tr":
            self.text_parts.append("\n|ROW|")
        elif tag in ("td", "th"):
            self.text_parts.append("|CELL|")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        elif tag in ("p", "div", "br", "tr", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.text_parts.append(data)


def extract_text_from_html(filepath):
    """Read HTML file and extract visible text."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()

    parser = TextExtractor()
    parser.feed(html)
    return "".join(parser.text_parts)


def parse_dollar_amount(text):
    """Parse a dollar amount like '3,913' or '(126)' into a number."""
    text = text.strip()
    negative = "(" in text or text.startswith("-")
    # Remove non-numeric except dots
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return None
    value = float(cleaned)
    return -value if negative else value


def search_section(text, patterns, context_lines=5):
    """Search for patterns in text and return surrounding context."""
    results = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = "\n".join(lines[start:end])
                results.append({
                    "pattern": pattern,
                    "line_number": i,
                    "matched_line": line.strip(),
                    "context": context,
                })
    return results


def extract_debt_data(text):
    """Extract debt schedule from 10-K."""
    patterns = [
        r"long.term debt",
        r"senior notes",
        r"term loan",
        r"total debt",
        r"credit facility",
        r"6\.625%",
        r"6\.125%",
    ]
    matches = search_section(text, patterns, context_lines=3)

    debt_items = []
    for m in matches:
        # Look for dollar amounts in context
        amounts = re.findall(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?", m["context"])
        if amounts:
            debt_items.append({
                "description": m["matched_line"][:100],
                "amounts_found": amounts[:5],
            })

    return {
        "search_hits": len(matches),
        "items": debt_items[:20],
        "cross_check_target": f"${EXPECTED['total_debt_mm']:,}M",
    }


def extract_cash_data(text):
    """Extract cash and equivalents."""
    patterns = [
        r"cash and cash equivalents",
        r"restricted cash",
        r"short.term investments",
    ]
    matches = search_section(text, patterns, context_lines=3)

    items = []
    for m in matches:
        amounts = re.findall(r"\$?\d{1,3}(?:,\d{3})*", m["context"])
        if amounts:
            items.append({
                "description": m["matched_line"][:100],
                "amounts_found": amounts[:5],
            })

    return {
        "search_hits": len(matches),
        "items": items[:10],
        "cross_check_target": f"${EXPECTED['cash_mm']:,}M",
    }


def extract_pension_data(text):
    """Extract pension/OPEB data."""
    patterns = [
        r"projected benefit obligation",
        r"accumulated benefit obligation",
        r"plan assets",
        r"unfunded",
        r"pension",
        r"postretirement",
    ]
    matches = search_section(text, patterns, context_lines=3)

    items = []
    seen = set()
    for m in matches:
        key = m["matched_line"][:50]
        if key not in seen:
            seen.add(key)
            amounts = re.findall(r"\$?\d{1,3}(?:,\d{3})*", m["context"])
            items.append({
                "description": m["matched_line"][:100],
                "amounts_found": amounts[:5],
            })

    return {
        "search_hits": len(matches),
        "unique_items": items[:15],
    }


def extract_share_count(text):
    """Extract share count data."""
    patterns = [
        r"shares outstanding",
        r"basic.*shares",
        r"diluted.*shares",
        r"common stock.*outstanding",
        r"treasury stock",
        r"weighted.average.*shares",
    ]
    matches = search_section(text, patterns, context_lines=2)

    items = []
    seen = set()
    for m in matches:
        key = m["matched_line"][:50]
        if key not in seen:
            seen.add(key)
            amounts = re.findall(r"\d{2,3}(?:,\d{3})*(?:\.\d+)?", m["context"])
            items.append({
                "description": m["matched_line"][:100],
                "amounts_found": amounts[:5],
            })

    return {
        "search_hits": len(matches),
        "items": items[:10],
        "cross_check_target": f"{EXPECTED['shares_outstanding_mm']}M",
    }


def extract_segment_data(text):
    """Extract segment reporting data (Flat-Rolled, Mini Mill, USSE, Tubular)."""
    patterns = [
        r"flat.rolled",
        r"mini mill",
        r"u\.?\s*s\.?\s*steel\s*europe|usse",
        r"tubular",
        r"segment.*revenue",
        r"segment.*ebitda",
        r"net sales.*segment",
        r"shipments",
    ]
    matches = search_section(text, patterns, context_lines=3)

    items = []
    seen = set()
    for m in matches:
        key = m["matched_line"][:60]
        if key not in seen:
            seen.add(key)
            items.append({
                "description": m["matched_line"][:120],
                "context_preview": m["context"][:200],
            })

    return {
        "search_hits": len(matches),
        "items": items[:20],
    }


def extract_lease_data(text):
    """Extract operating lease data."""
    patterns = [
        r"operating lease",
        r"right.of.use",
        r"lease liabilit",
        r"ROU",
    ]
    matches = search_section(text, patterns, context_lines=3)

    items = []
    seen = set()
    for m in matches:
        key = m["matched_line"][:50]
        if key not in seen:
            seen.add(key)
            amounts = re.findall(r"\$?\d{1,3}(?:,\d{3})*", m["context"])
            items.append({
                "description": m["matched_line"][:100],
                "amounts_found": amounts[:5],
            })

    return {
        "search_hits": len(matches),
        "items": items[:10],
    }


def main():
    print("=" * 60)
    print("USS 10-K Data Extraction")
    print("=" * 60)

    if not os.path.exists(INPUT_10K):
        print(f"\nERROR: 10-K file not found at {INPUT_10K}")
        print("Run scripts/fetch_sec_filings.py first to download the filing.")
        sys.exit(1)

    file_size = os.path.getsize(INPUT_10K)
    print(f"\nInput: {INPUT_10K} ({file_size:,} bytes)")

    # Extract text
    print("Extracting text from HTML...")
    text = extract_text_from_html(INPUT_10K)
    print(f"Extracted {len(text):,} characters of text")

    # Extract each category
    print("\nExtracting financial data...")

    results = {
        "source_file": INPUT_10K,
        "source_size_bytes": file_size,
        "text_length": len(text),
        "cross_check_targets": EXPECTED,
        "sections": {},
    }

    extractors = [
        ("debt", "Debt Schedule", extract_debt_data),
        ("cash", "Cash & Equivalents", extract_cash_data),
        ("pension", "Pension & OPEB", extract_pension_data),
        ("shares", "Share Count", extract_share_count),
        ("segments", "Segment Data", extract_segment_data),
        ("leases", "Operating Leases", extract_lease_data),
    ]

    for key, label, extractor in extractors:
        print(f"  {label}...", end=" ")
        data = extractor(text)
        results["sections"][key] = data
        print(f"{data['search_hits']} matches")

    # Save results
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {OUTPUT_JSON}")

    # Cross-check summary
    print("\n" + "=" * 60)
    print("CROSS-CHECK SUMMARY")
    print("=" * 60)
    print(f"  Target total debt:  ${EXPECTED['total_debt_mm']:,}M")
    print(f"  Target cash:        ${EXPECTED['cash_mm']:,}M")
    print(f"  Target net debt:    ${EXPECTED['net_debt_mm']:,}M")
    print(f"  Target shares:      {EXPECTED['shares_outstanding_mm']}M")
    print("\n  Review the extracted data in the JSON output to verify these values.")
    print("  Key debt items to look for: 6.625% Senior Notes, 6.125% Senior Notes, Term Loan B")

    return results


if __name__ == "__main__":
    main()
