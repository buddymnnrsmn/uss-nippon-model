#!/usr/bin/env python3
"""
Dashboard Testing Script
========================

Tests the Streamlit dashboard using Playwright for automated browser testing.
Verifies scenario switching, synergy controls, and checks for JavaScript errors.

Usage:
    python scripts/test_dashboard.py

Requirements:
    - Playwright: pip install playwright && playwright install chromium
    - Dashboard running: streamlit run interactive_dashboard.py
"""

from playwright.sync_api import sync_playwright
import time
import sys


def test_dashboard(url="http://localhost:8501", verbose=True):
    """
    Test the dashboard for functionality and errors.

    Returns:
        dict: Test results with pass/fail status and error details
    """
    results = {
        "passed": True,
        "tests": [],
        "delta_errors": [],
        "total_js_errors": 0
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        errors = []
        def handle_console(msg):
            if msg.type == 'error':
                errors.append(msg.text)
        page.on('console', handle_console)

        if verbose:
            print("=" * 60)
            print("DASHBOARD TEST SUITE")
            print("=" * 60)

        # Load page
        if verbose:
            print("\nLoading dashboard...")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(5)
            results["tests"].append(("Page Load", True, None))
            if verbose:
                print(f"  ✓ Page loaded. Initial errors: {len(errors)}")
        except Exception as e:
            results["tests"].append(("Page Load", False, str(e)))
            results["passed"] = False
            if verbose:
                print(f"  ✗ Page load failed: {e}")
            browser.close()
            return results

        # Test 1: Initial state
        if verbose:
            print("\n1. Checking initial state (Base Case)...")
        page_text = page.locator('body').inner_text()
        base_ok = "10.9" in page_text
        results["tests"].append(("Initial WACC 10.9%", base_ok, None))
        if verbose:
            print(f"  {'✓' if base_ok else '✗'} Base Case WACC (10.9%)")

        # Test 2: Scenario switching
        scenarios = [
            ("Severe Downturn", 0, "13.5"),
            ("Optimistic", 5, "10.9"),
            ("Base Case", 2, "10.9"),
        ]

        if verbose:
            print("\n2. Testing scenario switching...")

        for name, idx, expected_wacc in scenarios:
            try:
                dropdown = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').first
                dropdown.click()
                time.sleep(0.5)
                page.keyboard.press("Home")
                for _ in range(idx):
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.1)
                page.keyboard.press("Enter")
                time.sleep(4)

                page_text = page.locator('body').inner_text()
                wacc_ok = expected_wacc in page_text
                delta_errors = [e for e in errors if 'delta' in e.lower() or 'Cannot set' in e]

                test_ok = wacc_ok and len(delta_errors) == 0
                results["tests"].append((f"Scenario: {name}", test_ok,
                    None if test_ok else f"WACC={expected_wacc} found: {wacc_ok}, errors: {len(delta_errors)}"))

                if verbose:
                    print(f"  {'✓' if test_ok else '✗'} {name}: WACC={expected_wacc}%, errors={len(delta_errors)}")

            except Exception as e:
                results["tests"].append((f"Scenario: {name}", False, str(e)))
                if verbose:
                    print(f"  ✗ {name}: {str(e)[:50]}")

        # Test 3: Synergy switching
        synergies = [
            ("Base Case Synergies", 2),
            ("None", 0),
        ]

        if verbose:
            print("\n3. Testing synergy switching...")

        for name, idx in synergies:
            try:
                synergy_dd = page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').nth(1)
                synergy_dd.click()
                time.sleep(0.5)
                page.keyboard.press("Home")
                for _ in range(idx):
                    page.keyboard.press("ArrowDown")
                    time.sleep(0.1)
                page.keyboard.press("Enter")
                time.sleep(4)

                delta_errors = [e for e in errors if 'delta' in e.lower() or 'Cannot set' in e]
                test_ok = len(delta_errors) == 0
                results["tests"].append((f"Synergy: {name}", test_ok,
                    None if test_ok else f"errors: {len(delta_errors)}"))

                if verbose:
                    print(f"  {'✓' if test_ok else '✗'} {name}: errors={len(delta_errors)}")

            except Exception as e:
                results["tests"].append((f"Synergy: {name}", False, str(e)))
                if verbose:
                    print(f"  ✗ {name}: {str(e)[:50]}")

        # Final results
        delta_errors = [e for e in errors if 'delta' in e.lower() or 'Cannot set' in e]
        results["delta_errors"] = delta_errors
        results["total_js_errors"] = len(errors)
        results["passed"] = all(t[1] for t in results["tests"]) and len(delta_errors) == 0

        if verbose:
            print("\n" + "=" * 60)
            print("RESULTS")
            print("=" * 60)
            print(f"Total tests: {len(results['tests'])}")
            print(f"Passed: {sum(1 for t in results['tests'] if t[1])}")
            print(f"Failed: {sum(1 for t in results['tests'] if not t[1])}")
            print(f"Delta-path errors: {len(delta_errors)}")
            print(f"Total JS errors: {len(errors)}")

            if results["passed"]:
                print("\n✓ ALL TESTS PASSED!")
            else:
                print("\n✗ SOME TESTS FAILED")
                for name, passed, error in results["tests"]:
                    if not passed:
                        print(f"  - {name}: {error}")

        browser.close()

    return results


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
    results = test_dashboard(url)
    sys.exit(0 if results["passed"] else 1)
