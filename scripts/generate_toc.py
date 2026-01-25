#!/usr/bin/env python3
"""
Automatically generates a Table of Contents (TOC) for the interactive dashboard
by parsing section headers with anchor IDs.

Usage:
    python scripts/generate_toc.py [--update] [--verify]

Options:
    --update    Update the dashboard file directly with the generated TOC
    --verify    Verify that all TOC links match actual anchors (returns exit code 1 if mismatch)
    (default)   Print the TOC to stdout for review
"""

import re
import sys
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parent.parent / "interactive_dashboard.py"

# Patterns to match section headers with anchor IDs
# Format 1 (legacy): st.markdown("<h2 id='anchor-id' style='text-decoration: underline;'>Title</h2>", unsafe_allow_html=True)
# Format 2 (current): st.header("Title", anchor="anchor-id")
HEADER_PATTERN_LEGACY = re.compile(
    r"st\.markdown\(\"<h2\s+id='([^']+)'\s+style='text-decoration:\s*underline;'>([^<]+)</h2>\",\s*unsafe_allow_html=True\)"
)
HEADER_PATTERN = re.compile(
    r'st\.header\("([^"]+)",\s*anchor="([^"]+)"\)'
)

# Section groupings - customize these to organize the TOC
SECTION_GROUPS = {
    "Executive Analysis": [
        "executive-decision-summary",
        "risk-adjusted-decision-matrix",
        "board-fiduciary-checklist",
    ],
    "Strategic Context": [
        "without-the-deal",
        "golden-share-nsa",
        "alternative-buyer-comparison",
        "sensitivity-thresholds",
    ],
    "Valuation Details": [
        "valuation-details",
        "uss-standalone-financing",
        "scenario-comparison",
        "probability-weighted-value",
        "capital-projects",
        "pe-lbo-comparison",
        "valuation-football-field",
        "value-bridge",
    ],
    "Financial Projections": [
        "fcf-projection",
        "segment-analysis",
    ],
    "Sensitivity Analysis": [
        "steel-price-sensitivity",
        "wacc-sensitivity",
        "irp-adjustment",
        "detailed-projections",
    ],
}


def parse_headers(content: str) -> dict[str, str]:
    """Parse all section headers from the dashboard content.

    Supports both legacy format (custom HTML) and current format (st.header with anchor).

    Returns:
        dict mapping anchor IDs to section titles
    """
    headers = {}

    # Check for current format: st.header("Title", anchor="anchor-id")
    for match in HEADER_PATTERN.finditer(content):
        title = match.group(1).strip()
        anchor_id = match.group(2)
        headers[anchor_id] = title

    # Also check legacy format for backwards compatibility
    for match in HEADER_PATTERN_LEGACY.finditer(content):
        anchor_id = match.group(1)
        title = match.group(2).strip()
        if anchor_id not in headers:  # Don't overwrite if already found
            headers[anchor_id] = title

    return headers


def generate_toc_markdown(headers: dict[str, str]) -> str:
    """Generate the TOC markdown string.

    Args:
        headers: dict mapping anchor IDs to section titles

    Returns:
        Formatted markdown TOC string
    """
    lines = []

    for group_name, anchor_ids in SECTION_GROUPS.items():
        lines.append(f"        **{group_name}**")
        for anchor_id in anchor_ids:
            if anchor_id in headers:
                title = headers[anchor_id]
                # Shorten some long titles for the TOC
                if len(title) > 35:
                    # Use a shorter version
                    short_titles = {
                        "Sensitivity Thresholds: What Breaks the Deal?": "Sensitivity Thresholds",
                        "Without the Deal: USS Strategic Predicament": "Without the Deal",
                        "Board Fiduciary Checklist (Revlon Duties)": "Board Fiduciary Checklist",
                        "PE LBO vs. Strategic Buyer Comparison": "PE LBO Comparison",
                        "Interest Rate Parity Adjustment": "Interest Rate Parity",
                    }
                    title = short_titles.get(title, title[:32] + "...")
                lines.append(f"        - [{title}](#{anchor_id})")
            else:
                # Anchor ID defined in groups but not found in file
                print(f"Warning: Anchor ID '{anchor_id}' not found in dashboard", file=sys.stderr)
        lines.append("")  # Blank line between groups

    return "\n".join(lines).rstrip()


def generate_toc_code(headers: dict[str, str]) -> str:
    """Generate the full TOC code block for the dashboard.

    Args:
        headers: dict mapping anchor IDs to section titles

    Returns:
        Complete Python code for the TOC section
    """
    toc_markdown = generate_toc_markdown(headers)

    code = f'''    # Page Navigation
    with st.sidebar.expander("Page Navigation", expanded=False):
        st.markdown("""
{toc_markdown}
        """, unsafe_allow_html=True)'''

    return code


def parse_toc_links(content: str) -> dict[str, str]:
    """Parse the TOC links from the dashboard navigation section.

    Returns:
        dict mapping anchor IDs to link titles
    """
    toc_pattern = re.compile(r'\[([^\]]+)\]\(#([^)]+)\)')
    toc_section_pattern = re.compile(r'Page Navigation.*?unsafe_allow_html=True\)', re.DOTALL)

    toc_links = {}
    toc_section = toc_section_pattern.search(content)
    if toc_section:
        for match in toc_pattern.finditer(toc_section.group()):
            title, anchor = match.groups()
            toc_links[anchor] = title
    return toc_links


def verify_toc(content: str) -> bool:
    """Verify that all TOC links match actual section anchors.

    Args:
        content: Dashboard file content

    Returns:
        True if all links are valid, False otherwise
    """
    # Get actual anchors from section headers
    actual_anchors = set(parse_headers(content).keys())

    # Get TOC links
    toc_links = parse_toc_links(content)

    print("TOC Link Verification")
    print("=" * 60)

    all_valid = True

    # Check each TOC link
    for anchor, title in sorted(toc_links.items()):
        if anchor in actual_anchors:
            print(f"  ✓ #{anchor} -> {title}")
        else:
            print(f"  ✗ #{anchor} -> {title} [MISSING ANCHOR]")
            all_valid = False

    # Check for anchors not in TOC
    missing_from_toc = actual_anchors - set(toc_links.keys())
    if missing_from_toc:
        print(f"\n⚠️  Anchors not in TOC (may be intentional):")
        for anchor in sorted(missing_from_toc):
            print(f"    - #{anchor}")

    print()
    if all_valid:
        print(f"✅ All {len(toc_links)} TOC links are valid!")
    else:
        print("❌ Some TOC links have no matching anchor in the dashboard")

    return all_valid


def update_dashboard(content: str, new_toc_code: str) -> str:
    """Update the dashboard content with the new TOC code.

    Args:
        content: Original dashboard file content
        new_toc_code: New TOC code to insert

    Returns:
        Updated dashboard content
    """
    # Pattern to match the existing TOC block
    toc_pattern = re.compile(
        r'(    # Page Navigation\n'
        r'    with st\.sidebar\.expander\("Page Navigation", expanded=False\):\n'
        r'        st\.markdown\(""".*?""", unsafe_allow_html=True\))',
        re.DOTALL
    )

    match = toc_pattern.search(content)
    if match:
        return content[:match.start()] + new_toc_code + content[match.end():]
    else:
        print("Warning: Could not find existing TOC block to replace", file=sys.stderr)
        return content


def main():
    """Main entry point."""
    update_mode = "--update" in sys.argv
    verify_mode = "--verify" in sys.argv

    # Read dashboard content
    if not DASHBOARD_PATH.exists():
        print(f"Error: Dashboard not found at {DASHBOARD_PATH}", file=sys.stderr)
        sys.exit(1)

    content = DASHBOARD_PATH.read_text()

    # Verify mode - just check if links are valid
    if verify_mode:
        is_valid = verify_toc(content)
        sys.exit(0 if is_valid else 1)

    # Parse headers
    headers = parse_headers(content)
    print(f"Found {len(headers)} section headers:", file=sys.stderr)
    for anchor_id, title in headers.items():
        print(f"  - {anchor_id}: {title}", file=sys.stderr)
    print(file=sys.stderr)

    # Check for missing headers
    all_expected = set()
    for ids in SECTION_GROUPS.values():
        all_expected.update(ids)

    missing = all_expected - set(headers.keys())
    if missing:
        print(f"Warning: Missing anchor IDs: {missing}", file=sys.stderr)

    extra = set(headers.keys()) - all_expected
    if extra:
        print(f"Note: Headers not in any group: {extra}", file=sys.stderr)

    # Generate TOC
    new_toc_code = generate_toc_code(headers)

    if update_mode:
        # Update the dashboard file
        updated_content = update_dashboard(content, new_toc_code)
        DASHBOARD_PATH.write_text(updated_content)
        print(f"Updated {DASHBOARD_PATH}", file=sys.stderr)
    else:
        # Print the generated TOC for review
        print("Generated TOC code:")
        print("-" * 60)
        print(new_toc_code)
        print("-" * 60)
        print("\nRun with --update to apply changes to the dashboard")
        print("Run with --verify to check if current TOC links are valid")


if __name__ == "__main__":
    main()
