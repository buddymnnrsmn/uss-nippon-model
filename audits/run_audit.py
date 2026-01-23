#!/usr/bin/env python3
"""
Master Audit Orchestration Script
==================================

Runs the complete audit workflow:
1. Automated tests (model_audit.py)
2. Input verification (verify_inputs.py)
3. Generates comprehensive report

Usage:
    python run_audit.py              # Run all tests
    python run_audit.py --quick      # Skip manual verification
    python run_audit.py --report     # Generate report only

Output:
    - results/audit_report_{timestamp}.md
    - results/audit_results.csv
"""

import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class AuditOrchestrator:
    """Run complete audit workflow"""

    def __init__(self):
        self.audit_dir = Path(__file__).parent
        self.results_dir = self.audit_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def run_automated_tests(self):
        """Run automated test suite"""
        print("\n" + "=" * 80)
        print("STEP 1: RUNNING AUTOMATED TESTS")
        print("=" * 80)

        test_script = self.audit_dir / "model_audit.py"

        try:
            result = subprocess.run(
                [sys.executable, str(test_script)],
                cwd=self.audit_dir,
                capture_output=True,
                text=True
            )

            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)

            return result.returncode == 0

        except Exception as e:
            print(f"✗ Error running automated tests: {e}")
            return False

    def run_input_verification(self):
        """Run input verification against source data"""
        print("\n" + "=" * 80)
        print("STEP 2: RUNNING INPUT VERIFICATION")
        print("=" * 80)

        verify_script = self.audit_dir / "verification_scripts" / "verify_inputs.py"

        try:
            result = subprocess.run(
                [sys.executable, str(verify_script)],
                cwd=self.audit_dir / "verification_scripts",
                capture_output=True,
                text=True
            )

            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)

            return True  # Return True even if no data filled (just report status)

        except Exception as e:
            print(f"⚠ Warning: Input verification not completed: {e}")
            print("   This is expected if source data has not been collected yet.")
            return True  # Not a failure, just incomplete

    def check_data_collection_status(self):
        """Check which source documents have been collected"""
        print("\n" + "=" * 80)
        print("DATA COLLECTION STATUS")
        print("=" * 80)

        data_dir = self.audit_dir / "data_collection"
        evidence_dir = self.audit_dir / "evidence"

        # Check CSV templates
        templates = {
            'USS 2023 Data': data_dir / "uss_2023_data.csv",
            'Steel Prices 2023': data_dir / "steel_prices_2023.csv",
            'Balance Sheet Items': data_dir / "balance_sheet_items.csv",
            'Capital Projects': data_dir / "capital_projects.csv",
        }

        print("\nCSV Templates Status:")
        print("-" * 60)
        for name, path in templates.items():
            if path.exists():
                # Check if any data filled in
                with open(path, 'r') as f:
                    content = f.read()
                    # Simple check: does it have data beyond headers?
                    lines = [l for l in content.split('\n') if l and not l.startswith('#')]
                    if len(lines) > 1:
                        # Check if Source_Value column has any data
                        has_data = 'Source_Value' in content and content.count('Source_Value,') < content.count(',')
                        status = "✓ Data filled" if has_data else "⚠ Template only"
                    else:
                        status = "✗ Empty"
            else:
                status = "✗ Missing"

            print(f"  {name:<30} {status}")

        # Check evidence documents
        print("\nEvidence Documents Status:")
        print("-" * 60)

        expected_docs = [
            'USS_10K_2023.pdf',
            'USS_Proxy_2024.pdf',
            'CME_HRC_Futures_2023.csv',
            'USS_Q4_2023_Earnings_Deck.pdf',
        ]

        docs_found = 0
        for doc in expected_docs:
            path = evidence_dir / doc
            status = "✓ Downloaded" if path.exists() else "⚠ Missing"
            if path.exists():
                docs_found += 1
            print(f"  {doc:<40} {status}")

        print(f"\nDocuments collected: {docs_found}/{len(expected_docs)}")

        if docs_found == 0:
            print("\n⚠ No source documents found.")
            print("  Run: python verification_scripts/data_scraper.py --all")
            print("  Then manually download required documents.")

        return docs_found > 0

    def generate_master_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "=" * 80)
        print("GENERATING MASTER AUDIT REPORT")
        print("=" * 80)

        report_path = self.results_dir / f"audit_report_{self.timestamp}.md"

        with open(report_path, 'w') as f:
            f.write(f"# Model Audit Report\n")
            f.write(f"## USS / Nippon Steel DCF Model\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%B %d, %Y %H:%M:%S')}\n")
            f.write(f"**Auditor:** Automated Audit Suite\n\n")
            f.write("---\n\n")

            f.write("## Executive Summary\n\n")

            # Check if automated tests ran
            auto_results = self.audit_dir / "audit_results.csv"
            if auto_results.exists():
                import pandas as pd
                df = pd.read_csv(auto_results)
                passed = len(df[df['Result'] == 'PASS'])
                total = len(df)
                pass_rate = passed / total * 100

                f.write(f"**Automated Tests:** {passed}/{total} passed ({pass_rate:.1f}%)\n\n")

                if pass_rate == 100:
                    f.write("✓ All automated tests passed.\n\n")
                elif pass_rate >= 90:
                    f.write("⚠ Minor issues identified in automated tests.\n\n")
                else:
                    f.write("✗ Significant issues found in automated tests.\n\n")
            else:
                f.write("⚠ Automated tests not run or results not found.\n\n")

            # Check manual verification status
            input_issues = self.results_dir / "input_verification_issues.csv"
            if input_issues.exists():
                import pandas as pd
                df = pd.read_csv(input_issues)
                high_severity = len(df[df['Severity'] == 'High'])
                medium_severity = len(df[df['Severity'] == 'Medium'])

                f.write(f"**Input Verification:**\n")
                f.write(f"- High severity issues: {high_severity}\n")
                f.write(f"- Medium severity issues: {medium_severity}\n\n")
            else:
                f.write("**Input Verification:** Not completed (source data not collected)\n\n")

            f.write("---\n\n")
            f.write("## Detailed Results\n\n")
            f.write("See individual result files:\n")
            f.write("- `audit_results.csv` - Automated test results\n")
            f.write("- `input_verification_issues.csv` - Input variance analysis\n\n")

            f.write("---\n\n")
            f.write("## Next Steps\n\n")
            f.write("1. Review flagged issues in detail\n")
            f.write("2. Complete source data collection if not done\n")
            f.write("3. Re-run verification after data updates\n")
            f.write("4. Document resolution of all issues\n\n")

        print(f"✓ Master report generated: {report_path}")
        return report_path

    def run_full_audit(self, skip_manual=False):
        """Run complete audit workflow"""
        print("=" * 80)
        print("MODEL AUDIT - COMPLETE WORKFLOW")
        print("=" * 80)

        # Step 1: Automated tests
        auto_success = self.run_automated_tests()

        # Step 2: Check data collection status
        has_data = self.check_data_collection_status()

        # Step 3: Input verification (if data available)
        if not skip_manual and has_data:
            self.run_input_verification()
        elif not skip_manual:
            print("\n⚠ Skipping input verification - no source data collected")
            print("  Run data_scraper.py and fill CSV templates to enable verification")

        # Step 4: Generate master report
        report_path = self.generate_master_report()

        # Final summary
        print("\n" + "=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)
        print(f"\n✓ Results saved to: {self.results_dir}/")
        print(f"✓ Master report: {report_path}")
        print()

        if auto_success and has_data:
            print("✓ Audit completed successfully")
        elif auto_success:
            print("⚠ Automated tests passed, but manual verification pending")
        else:
            print("✗ Issues found - review results")

        print()


def main():
    parser = argparse.ArgumentParser(description='Run model audit workflow')
    parser.add_argument('--quick', action='store_true',
                       help='Skip manual verification (automated tests only)')
    parser.add_argument('--report', action='store_true',
                       help='Generate report only (no tests)')

    args = parser.parse_args()

    orchestrator = AuditOrchestrator()

    if args.report:
        orchestrator.generate_master_report()
    else:
        orchestrator.run_full_audit(skip_manual=args.quick)


if __name__ == "__main__":
    main()
