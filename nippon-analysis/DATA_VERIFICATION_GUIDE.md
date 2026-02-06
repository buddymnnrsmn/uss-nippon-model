# Nippon Steel Data Verification Guide

## Overview

This document provides a systematic approach to verify and update the placeholder financial data for Nippon Steel Corporation used in the `nippon_financial_profile.py` module.

**Current Status:** Placeholder data based on publicly available estimates. Requires verification against official sources.

---

## 1. Priority Data Points to Verify

### Tier 1 - Critical (Affects Deal Capacity Verdict)

| Data Point | Current Value | Source to Check | Impact |
|------------|---------------|-----------------|--------|
| FY2024 Revenue | ¥8,509B | FY2024 Annual Report | High |
| FY2024 EBITDA | ¥1,260B | FY2024 Annual Report | High |
| Total Debt | ¥2,320B | Balance Sheet | High |
| Cash & Equivalents | ¥450B | Balance Sheet | High |
| Interest Expense | ¥48B | Income Statement | Medium |
| Operating Cash Flow | ¥980B | Cash Flow Statement | High |

### Tier 2 - Important (Affects Credit Analysis)

| Data Point | Current Value | Source to Check | Impact |
|------------|---------------|-----------------|--------|
| Short-term Debt | ¥520B | Balance Sheet | Medium |
| Long-term Debt | ¥1,800B | Balance Sheet | Medium |
| Total Equity | ¥4,400B | Balance Sheet | Medium |
| Credit Facility Capacity | ¥800B | Notes to Financials | Medium |

### Tier 3 - Contextual (Affects Peer Comparison)

| Data Point | Current Value | Source to Check | Impact |
|------------|---------------|-----------------|--------|
| Net Income | ¥621B | Income Statement | Low |
| CapEx | ¥480B | Cash Flow Statement | Low |
| Dividends | ¥180B | Cash Flow Statement | Low |

---

## 2. Primary Data Sources

### 2.1 Nippon Steel Official IR

**URL:** https://www.nipponsteel.com/en/ir/library/

**Documents to Download:**

1. **決算短信 (Kessan Tanshin)** - Quarterly Earnings Release
   - FY2024 Q4 (April 2024)
   - Contains: Revenue, Operating Income, Net Income, Assets, Liabilities
   - Format: PDF (Japanese/English)

2. **有価証券報告書 (Yukashoken Hokokusho)** - Annual Securities Report
   - FY2024 Full Year (June 2024)
   - Contains: Complete financial statements, notes, debt details
   - Format: PDF/XBRL (primarily Japanese)

3. **Investor Presentations**
   - FY2024 Results Presentation
   - Contains: Key metrics, strategic outlook, debt profile
   - Format: PDF (English available)

### 2.2 SEC EDGAR (for ADR filings)

**URL:** https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=nippon+steel&type=20-F

**Documents:**
- Form 20-F (Annual Report for foreign private issuers)
- May have English translations of key financials

### 2.3 Rating Agency Reports

| Agency | URL | Document |
|--------|-----|----------|
| S&P Global | https://www.spglobal.com/ratings/ | Search "Nippon Steel" |
| Moody's | https://www.moodys.com/ | Search "Nippon Steel" |
| Fitch | https://www.fitchratings.com/ | Search "Nippon Steel" |

**Note:** Full reports require subscription; press releases are often free.

### 2.4 WRDS (Automated)

If WRDS API is configured in `local/.env`:

```bash
cd /workspaces/claude-in-docker/uss-nippon-model
python local/wrds_loader.py --test  # Test API connection
python local/wrds_loader.py --fetch-all --summary  # Fetch data
```

Data will be cached in `local/wrds_cache/` as Parquet files.

---

## 3. Verification Workflow

### Step 1: Download Official Documents

```bash
# Create a downloads directory
mkdir -p nippon-analysis/verification/downloads

# Manual downloads required:
# 1. Go to https://www.nipponsteel.com/en/ir/library/
# 2. Download FY2024 Annual Report (English if available)
# 3. Download FY2024 Investor Presentation
# 4. Save to nippon-analysis/verification/downloads/
```

### Step 2: Extract Key Figures

Create a verification checklist:

```python
# nippon-analysis/verification/verification_checklist.py

OFFICIAL_DATA = {
    "source": "Nippon Steel FY2024 Annual Report",
    "source_url": "https://www.nipponsteel.com/en/ir/library/...",
    "download_date": "2026-02-02",

    # Income Statement
    "revenue_jpy_b": None,          # Fill from official source
    "operating_income_jpy_b": None,
    "ebitda_jpy_b": None,           # May need to calculate: OI + D&A
    "net_income_jpy_b": None,
    "interest_expense_jpy_b": None,

    # Balance Sheet
    "cash_jpy_b": None,
    "total_current_assets_jpy_b": None,
    "total_assets_jpy_b": None,
    "short_term_debt_jpy_b": None,
    "long_term_debt_jpy_b": None,
    "total_debt_jpy_b": None,       # Calculate: ST + LT
    "total_liabilities_jpy_b": None,
    "total_equity_jpy_b": None,

    # Cash Flow
    "operating_cf_jpy_b": None,
    "capex_jpy_b": None,
    "fcf_jpy_b": None,              # Calculate: OCF - CapEx
    "dividends_jpy_b": None,

    # Credit
    "committed_facilities_jpy_b": None,
    "drawn_facilities_jpy_b": None,
}
```

### Step 3: Compare with Placeholder Data

```python
# nippon-analysis/verification/compare_data.py

import sys
sys.path.insert(0, '..')
from nippon_financial_profile import get_nippon_placeholder_data

def compare_with_official(official_data: dict):
    """Compare placeholder data with verified official data."""

    placeholder = get_nippon_placeholder_data()
    fy2024 = placeholder[2024]

    discrepancies = []

    # Compare each field
    comparisons = [
        ("Revenue", fy2024.revenue, official_data.get("revenue_jpy_b")),
        ("EBITDA", fy2024.ebitda, official_data.get("ebitda_jpy_b")),
        ("Total Debt", fy2024.total_debt, official_data.get("total_debt_jpy_b")),
        ("Cash", fy2024.cash_and_equivalents, official_data.get("cash_jpy_b")),
        ("Total Equity", fy2024.total_equity, official_data.get("total_equity_jpy_b")),
        ("Operating CF", fy2024.operating_cash_flow, official_data.get("operating_cf_jpy_b")),
    ]

    print("Data Verification Report")
    print("=" * 60)

    for name, placeholder_val, official_val in comparisons:
        if official_val is None:
            status = "PENDING"
            diff = "N/A"
        else:
            diff = placeholder_val - official_val
            pct_diff = (diff / official_val * 100) if official_val != 0 else 0
            status = "OK" if abs(pct_diff) < 5 else "DISCREPANCY"

        print(f"{name:20s} | Placeholder: {placeholder_val:,.0f} | Official: {official_val or 'TBD':>10} | {status}")

        if official_val and abs(pct_diff) >= 5:
            discrepancies.append((name, placeholder_val, official_val, pct_diff))

    return discrepancies
```

### Step 4: Update Placeholder Data

If discrepancies are found, update `nippon_financial_profile.py`:

```python
# Location: nippon-analysis/nippon_financial_profile.py
# Function: get_nippon_placeholder_data()

# Update FY2024 values:
fy2024 = NipponFinancials(
    fiscal_year=2024,
    fiscal_year_end="March 2024",
    reporting_currency="JPY",
    # UPDATE THESE VALUES with verified data:
    revenue=VERIFIED_VALUE,  # Previously: 8509.0
    operating_income=VERIFIED_VALUE,  # Previously: 880.0
    ebitda=VERIFIED_VALUE,  # Previously: 1260.0
    # ... etc
)
```

### Step 5: Document Changes

Add to `DATA_VERIFICATION_LOG.md`:

```markdown
## Verification Log

### 2026-02-02: Initial Verification

**Sources Used:**
- Nippon Steel FY2024 Annual Report (downloaded [date])
- [URL]

**Changes Made:**
| Field | Old Value | New Value | Source Page |
|-------|-----------|-----------|-------------|
| Revenue | ¥8,509B | ¥X,XXXB | p. 12 |
| EBITDA | ¥1,260B | ¥X,XXXB | calculated |

**Verified By:** [Name/Claude]
```

---

## 4. Automated Verification Script

Create a comprehensive verification script:

```python
#!/usr/bin/env python3
"""
nippon-analysis/verification/run_verification.py

Automated data verification for Nippon Steel financials.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from nippon_financial_profile import get_nippon_placeholder_data, NipponFinancials

def load_official_data(filepath: Path) -> dict:
    """Load official data from JSON file."""
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return {}

def run_verification():
    """Run full data verification."""

    # Load placeholder data
    placeholder = get_nippon_placeholder_data()

    # Load official data (if available)
    official_file = Path(__file__).parent / "official_data.json"
    official = load_official_data(official_file)

    # Generate report
    report = {
        "verification_date": datetime.now().isoformat(),
        "status": "pending" if not official else "complete",
        "findings": [],
    }

    if official:
        fy2024 = placeholder[2024]

        checks = [
            ("revenue", fy2024.revenue, official.get("revenue_jpy_b")),
            ("ebitda", fy2024.ebitda, official.get("ebitda_jpy_b")),
            ("total_debt", fy2024.total_debt, official.get("total_debt_jpy_b")),
            ("cash", fy2024.cash_and_equivalents, official.get("cash_jpy_b")),
        ]

        for name, placeholder_val, official_val in checks:
            if official_val:
                diff_pct = abs((placeholder_val - official_val) / official_val * 100)
                report["findings"].append({
                    "field": name,
                    "placeholder": placeholder_val,
                    "official": official_val,
                    "diff_pct": diff_pct,
                    "status": "OK" if diff_pct < 5 else "UPDATE_NEEDED"
                })

    # Save report
    report_file = Path(__file__).parent / "verification_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Verification report saved to: {report_file}")
    return report

if __name__ == "__main__":
    run_verification()
```

---

## 5. WRDS Automated Update

If WRDS is configured, create an automated update process:

```python
#!/usr/bin/env python3
"""
nippon-analysis/verification/update_from_wrds.py

Update placeholder data from WRDS Compustat.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "local"))

def update_from_wrds():
    """Attempt to update financials from WRDS."""

    try:
        from wrds_loader import WRDSDataLoader

        loader = WRDSDataLoader()
        fundamentals = loader.fetch_fundamentals(start_year=2019)

        # Filter to Nippon Steel
        nippon = fundamentals[fundamentals['ticker'] == 'NISTF']

        if not nippon.empty:
            print("WRDS data available for Nippon Steel (NISTF)")
            print(nippon[['fyear', 'revenue', 'ebitda', 'total_assets']].tail())

            # Export for verification
            output_file = Path(__file__).parent / "wrds_nippon_data.csv"
            nippon.to_csv(output_file, index=False)
            print(f"Exported to: {output_file}")
        else:
            print("No NISTF data found in WRDS")

        loader.close()

    except ImportError:
        print("WRDS loader not available - configure API token in local/.env")
    except Exception as e:
        print(f"WRDS update failed: {e}")

if __name__ == "__main__":
    update_from_wrds()
```

---

## 6. Recommended Verification Schedule

| Frequency | Action | Trigger |
|-----------|--------|---------|
| Quarterly | Check for new earnings releases | After each quarter-end |
| Annually | Full verification against annual report | After FY annual report release (typically June for March FY) |
| Ad-hoc | Rating agency updates | Any rating action announcement |
| Ad-hoc | Material events | M&A announcements, debt issuances |

---

## 7. Data Quality Checklist

Before using the data for analysis, verify:

- [ ] Revenue matches official consolidated revenue
- [ ] EBITDA is correctly calculated (Operating Income + D&A)
- [ ] Debt totals reconcile (Short-term + Long-term = Total)
- [ ] Cash includes all cash equivalents
- [ ] Operating cash flow is from continuing operations
- [ ] Exchange rate assumption is documented
- [ ] Credit ratings are current (within 6 months)
- [ ] Peer data is from comparable fiscal periods

---

## 8. Contact Points for Data Issues

| Issue | Contact |
|-------|---------|
| Official IR data questions | ir@nsc.nipponsteel.com |
| WRDS data issues | support@wrds.upenn.edu |
| Rating agency data | Individual agency IR contacts |

---

*Guide created: February 2026*
*Last updated: February 2026*
