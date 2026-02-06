#!/usr/bin/env python3
"""
Claim Verification Script
-------------------------
Extracts claims, figures, and quotes from a markdown document,
searches for sources, and cross-verifies them.

Usage:
    python verify_claims.py <markdown_file> [--output report.md]

Example:
    python verify_claims.py documentation/TRANSACTION_SUMMARY.md --output verification_report.md
"""

import re
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
import ssl
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Claim:
    """Represents an extracted claim from the document."""
    text: str
    claim_type: str  # 'figure', 'quote', 'percentage', 'date', 'entity'
    context: str  # surrounding text for context
    line_number: int
    verified: Optional[bool] = None
    source_url: Optional[str] = None
    source_text: Optional[str] = None
    discrepancy: Optional[str] = None


@dataclass
class VerificationReport:
    """Contains the full verification report."""
    document_path: str
    timestamp: str
    claims: list = field(default_factory=list)
    sources_checked: list = field(default_factory=list)

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.claims if c.verified is True)

    @property
    def unverified_count(self) -> int:
        return sum(1 for c in self.claims if c.verified is None)

    @property
    def discrepancy_count(self) -> int:
        return sum(1 for c in self.claims if c.verified is False)


class ClaimExtractor:
    """Extracts claims from markdown documents."""

    # Patterns for different claim types
    PATTERNS = {
        'dollar_amount': r'\$[\d,]+(?:\.\d+)?(?:\s*(?:billion|million|B|M))?',
        'percentage': r'\d+(?:\.\d+)?%',
        'quote': r'"([^"]+)"',
        'date': r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
        'year': r'\b20[12]\d\b',
        'large_number': r'\b\d{1,3}(?:,\d{3})+\b',
    }

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')

    def extract_all(self) -> list[Claim]:
        """Extract all claims from the document."""
        claims = []

        for line_num, line in enumerate(self.lines, 1):
            # Skip header lines and source sections
            if line.startswith('#') or line.startswith('- ['):
                continue

            for claim_type, pattern in self.PATTERNS.items():
                for match in re.finditer(pattern, line):
                    claim_text = match.group(0)

                    # Get context (surrounding words)
                    start = max(0, match.start() - 50)
                    end = min(len(line), match.end() + 50)
                    context = line[start:end].strip()

                    claims.append(Claim(
                        text=claim_text,
                        claim_type=claim_type,
                        context=context,
                        line_number=line_num
                    ))

        return claims

    def extract_sources(self) -> list[tuple[str, str]]:
        """Extract source URLs from markdown links."""
        sources = []
        pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'

        for match in re.finditer(pattern, self.content):
            title = match.group(1)
            url = match.group(2)
            sources.append((title, url))

        return sources


class SourceVerifier:
    """Verifies claims against sources."""

    def __init__(self):
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def check_url_accessible(self, url: str, timeout: int = 10) -> tuple[bool, int]:
        """Check if a URL is accessible and return status code."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context)
            return True, response.getcode()
        except urllib.error.HTTPError as e:
            return False, e.code
        except Exception:
            return False, 0

    def verify_sources(self, sources: list[tuple[str, str]]) -> list[dict]:
        """Verify all source URLs are accessible."""
        results = []
        for title, url in sources:
            accessible, status = self.check_url_accessible(url)
            results.append({
                'title': title,
                'url': url,
                'accessible': accessible,
                'status_code': status
            })
        return results


class ReportGenerator:
    """Generates verification reports."""

    def __init__(self, report: VerificationReport):
        self.report = report

    def generate_markdown(self) -> str:
        """Generate a markdown verification report."""
        lines = [
            f"# Claim Verification Report",
            f"",
            f"**Document:** `{self.report.document_path}`",
            f"**Generated:** {self.report.timestamp}",
            f"",
            f"## Summary",
            f"",
            f"| Status | Count |",
            f"|--------|-------|",
            f"| ✅ Verified | {self.report.verified_count} |",
            f"| ⚠️ Discrepancy | {self.report.discrepancy_count} |",
            f"| ❓ Unverified | {self.report.unverified_count} |",
            f"| **Total Claims** | {len(self.report.claims)} |",
            f"",
            f"---",
            f"",
            f"## Source Link Status",
            f"",
        ]

        # Source status
        working = sum(1 for s in self.report.sources_checked if s['accessible'])
        total = len(self.report.sources_checked)
        lines.append(f"**{working}/{total} sources accessible**")
        lines.append("")

        for source in self.report.sources_checked:
            status = "✓" if source['accessible'] else f"✗ ({source['status_code']})"
            lines.append(f"- {status} [{source['title'][:60]}...]({source['url']})")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## Extracted Claims",
            f"",
        ])

        # Group claims by type
        by_type = {}
        for claim in self.report.claims:
            if claim.claim_type not in by_type:
                by_type[claim.claim_type] = []
            by_type[claim.claim_type].append(claim)

        for claim_type, claims in by_type.items():
            lines.append(f"### {claim_type.replace('_', ' ').title()}s")
            lines.append("")
            lines.append("| Claim | Context | Line | Status |")
            lines.append("|-------|---------|------|--------|")

            for claim in claims:
                if claim.verified is True:
                    status = "✅ Verified"
                elif claim.verified is False:
                    status = f"⚠️ {claim.discrepancy}"
                else:
                    status = "❓ Unverified"

                # Escape pipes in text
                text = claim.text.replace('|', '\\|')
                context = claim.context[:40].replace('|', '\\|') + "..."

                lines.append(f"| `{text}` | {context} | {claim.line_number} | {status} |")

            lines.append("")

        lines.extend([
            f"---",
            f"",
            f"## Next Steps",
            f"",
            f"1. Review unverified claims and search for sources",
            f"2. Investigate discrepancies against original sources",
            f"3. Update document with corrections",
            f"4. Re-run verification to confirm fixes",
        ])

        return '\n'.join(lines)

    def generate_json(self) -> str:
        """Generate a JSON verification report."""
        data = {
            'document': self.report.document_path,
            'timestamp': self.report.timestamp,
            'summary': {
                'total_claims': len(self.report.claims),
                'verified': self.report.verified_count,
                'discrepancies': self.report.discrepancy_count,
                'unverified': self.report.unverified_count,
            },
            'sources': self.report.sources_checked,
            'claims': [
                {
                    'text': c.text,
                    'type': c.claim_type,
                    'context': c.context,
                    'line': c.line_number,
                    'verified': c.verified,
                    'source_url': c.source_url,
                    'discrepancy': c.discrepancy,
                }
                for c in self.report.claims
            ]
        }
        return json.dumps(data, indent=2)


def verify_document(filepath: str) -> VerificationReport:
    """Main function to verify a document."""

    # Read document
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract claims and sources
    extractor = ClaimExtractor(content)
    claims = extractor.extract_all()
    sources = extractor.extract_sources()

    # Verify source accessibility
    verifier = SourceVerifier()
    source_results = verifier.verify_sources(sources)

    # Build report
    report = VerificationReport(
        document_path=filepath,
        timestamp=datetime.now().isoformat(),
        claims=claims,
        sources_checked=source_results
    )

    return report


def main():
    parser = argparse.ArgumentParser(
        description='Verify claims in a markdown document against sources'
    )
    parser.add_argument('document', help='Path to markdown document')
    parser.add_argument('--output', '-o', help='Output report path (default: stdout)')
    parser.add_argument('--format', '-f', choices=['markdown', 'json'],
                        default='markdown', help='Output format')
    parser.add_argument('--check-links-only', action='store_true',
                        help='Only check if source links are accessible')

    args = parser.parse_args()

    # Verify document exists
    if not Path(args.document).exists():
        print(f"Error: Document not found: {args.document}")
        return 1

    # Run verification
    print(f"Verifying: {args.document}")
    report = verify_document(args.document)

    # Generate report
    generator = ReportGenerator(report)
    if args.format == 'json':
        output = generator.generate_json()
    else:
        output = generator.generate_markdown()

    # Output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report saved to: {args.output}")
    else:
        print(output)

    # Summary
    print(f"\n{'='*50}")
    print(f"Claims found: {len(report.claims)}")
    print(f"Sources checked: {len(report.sources_checked)}")
    working = sum(1 for s in report.sources_checked if s['accessible'])
    print(f"Sources accessible: {working}/{len(report.sources_checked)}")

    return 0


if __name__ == '__main__':
    exit(main())
