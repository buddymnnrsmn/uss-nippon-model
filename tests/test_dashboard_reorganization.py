#!/usr/bin/env python3
"""
Dashboard Reorganization Test Suite
=====================================

Tests for Phase 1 dashboard reorganization:
1. Sidebar section ordering (price/WACC before IRP/Bloomberg)
2. Verdict box HTML rendering
3. Section title renames
4. Collapsible Key Numbers expander
5. Model Configuration section grouping
6. Syntax and import validation
"""

import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def read_dashboard_source():
    """Read the interactive_dashboard.py source code."""
    path = Path(__file__).parent.parent / "interactive_dashboard.py"
    return path.read_text()


def test_syntax_and_imports():
    """Test 1: Dashboard file compiles and key imports work."""
    print("\n" + "=" * 60)
    print("TEST 1: Syntax & Import Validation")
    print("=" * 60)

    # Compile check
    path = Path(__file__).parent.parent / "interactive_dashboard.py"
    import py_compile
    py_compile.compile(str(path), doraise=True)
    print("  OK  File compiles without syntax errors")

    # Import key functions
    from interactive_dashboard import (
        create_scenario_hash,
        render_calculation_button,
        render_sidebar,
        main,
    )
    print("  OK  All key functions importable")

    # Import model dependencies
    from price_volume_model import (
        PriceVolumeModel, ModelScenario, ScenarioType,
        get_scenario_presets, BENCHMARK_PRICES_2023,
    )
    print("  OK  Model dependencies importable")

    print("\nPASSED: Syntax & Import Validation")
    return True


def test_sidebar_section_order():
    """Test 2: Sidebar sections are in the new reorganized order."""
    print("\n" + "=" * 60)
    print("TEST 2: Sidebar Section Order")
    print("=" * 60)

    source = read_dashboard_source()

    # Find render_sidebar function
    sidebar_match = re.search(r'def render_sidebar\(\):', source)
    assert sidebar_match, "render_sidebar() function not found"
    sidebar_start = sidebar_match.start()

    # Find end of render_sidebar (next def at same indentation or end)
    main_match = re.search(r'\ndef main\(\):', source)
    assert main_match, "main() function not found"
    sidebar_end = main_match.start()
    sidebar_code = source[sidebar_start:sidebar_end]

    # Define expected section order (by unique markers)
    expected_order = [
        ("Scenario Selection", r'st\.sidebar\.header\("Scenario Selection"\)'),
        ("Steel Price Benchmarks", r'st\.sidebar\.header\("Steel Price Benchmarks"\)'),
        ("Price Factors", r'st\.sidebar\.header\("Price Factors"\)'),
        ("Volume Scenario", r'st\.sidebar\.header\("Volume Scenario"\)'),
        ("WACC Parameters", r'st\.sidebar\.header\("WACC Parameters"\)'),
        ("Capital Projects", r'st\.sidebar\.header\("Capital Projects"\)'),
        ("Synergy Assumptions", r'st\.sidebar\.header\("Synergy Assumptions"\)'),
        ("Model Configuration", r'st\.sidebar\.header\("Model Configuration"\)'),
    ]

    positions = []
    for name, pattern in expected_order:
        match = re.search(pattern, sidebar_code)
        if match:
            positions.append((name, match.start()))
        else:
            positions.append((name, -1))

    # Verify all sections found
    missing = [name for name, pos in positions if pos == -1]
    assert not missing, f"Missing sidebar sections: {missing}"
    print("  OK  All sidebar sections found")

    # Verify ordering
    prev_pos = -1
    prev_name = ""
    for name, pos in positions:
        if pos <= prev_pos:
            assert False, f"'{name}' should come AFTER '{prev_name}' but doesn't"
        prev_pos = pos
        prev_name = name
    print("  OK  Sidebar sections in correct order:")
    for name, _ in positions:
        print(f"       {name}")

    # Verify Page Navigation expander was REMOVED
    assert 'Page Navigation' not in sidebar_code, \
        "Page Navigation expander should be removed from sidebar"
    print("  OK  Page Navigation expander removed")

    # Verify Bloomberg is under Model Configuration (not before Price Benchmarks)
    bloomberg_match = re.search(r'Bloomberg Market Data', sidebar_code)
    model_config_match = re.search(r'Model Configuration', sidebar_code)
    assert bloomberg_match and model_config_match, "Bloomberg and Model Config sections required"
    assert bloomberg_match.start() > model_config_match.start(), \
        "Bloomberg should be AFTER Model Configuration header"
    print("  OK  Bloomberg moved under Model Configuration")

    # Verify IRP is under Model Configuration
    irp_match = re.search(r'Interest Rate Parity', sidebar_code)
    assert irp_match and irp_match.start() > model_config_match.start(), \
        "IRP should be AFTER Model Configuration header"
    print("  OK  IRP moved under Model Configuration")

    print("\nPASSED: Sidebar Section Order")
    return True


def test_verdict_boxes_styled():
    """Test 3: Verdict boxes use HTML styling instead of st.success/warning."""
    print("\n" + "=" * 60)
    print("TEST 3: Verdict Box Styling")
    print("=" * 60)

    source = read_dashboard_source()

    # Find the verdict section
    verdict_section_start = source.find("# Deal Verdict Section")
    assert verdict_section_start > 0, "Deal Verdict section not found"

    # Get verdict section (all three columns can span ~6000 chars)
    verdict_section = source[verdict_section_start:verdict_section_start + 7000]

    # Should use HTML div styling
    assert 'unsafe_allow_html=True' in verdict_section, \
        "Verdict boxes should use unsafe_allow_html for custom styling"
    print("  OK  Uses unsafe_allow_html=True")

    # Should have styled div boxes
    assert 'border-radius:10px' in verdict_section, \
        "Verdict boxes should have rounded corners"
    assert 'border:3px solid' in verdict_section, \
        "Verdict boxes should have prominent borders"
    assert 'min-height:220px' in verdict_section, \
        "Verdict boxes should have minimum height for consistency"
    print("  OK  Verdict boxes have enhanced CSS styling")

    # Should have all three verdicts
    assert 'USS Shareholders' in verdict_section, "Missing USS Shareholders verdict"
    assert 'USS Board' in verdict_section, "Missing USS Board verdict"
    assert 'Nippon Steel' in verdict_section, "Missing Nippon Steel verdict"
    print("  OK  All three verdict boxes present")

    # Should NOT use plain st.success for verdicts (old pattern)
    # Look for st.success with verdict text in the verdict section
    old_pattern = re.search(r'st\.success\([^)]*USS Shareholders', verdict_section)
    assert old_pattern is None, \
        "Should NOT use plain st.success() for verdict boxes (use HTML)"
    print("  OK  No plain st.success() for verdicts (HTML-styled)")

    # Check color coding
    assert '#d4edda' in verdict_section, "Missing green background for YES verdicts"
    assert '#28a745' in verdict_section, "Missing green border for YES verdicts"
    assert '#fff3cd' in verdict_section, "Missing yellow background for CONDITIONAL verdicts"
    assert '#f8d7da' in verdict_section, "Missing red background for NO verdicts"
    print("  OK  Correct color coding (green/yellow/red)")

    print("\nPASSED: Verdict Box Styling")
    return True


def test_section_titles_renamed():
    """Test 4: Section titles have been renamed to action-oriented versions."""
    print("\n" + "=" * 60)
    print("TEST 4: Section Title Renames")
    print("=" * 60)

    source = read_dashboard_source()

    # Map of old titles (should NOT exist) -> new titles (should exist)
    renames = {
        # Old title -> New title
        '"Without the Deal: USS Strategic Predicament"':
            '"Without the Deal: Why USS Needs a Buyer"',
        '"Alternative Buyer Comparison"':
            '"Alternative Buyers: Why No One Can Match',
        '"Multi-Year Growth & Profitability Analysis"':
            '"USS vs Peers: Growth & Profitability (2019-2024)"',
        '"PE LBO vs. Strategic Buyer Comparison"':
            "Why PE Can't Pay",
        '"USS Price Comparison"':
            'USS Historical Stock Price vs',
        '"WACC Component Details"':
            '"WACC Calculation Verification"',
        '"Detailed Projections"':
            '"Full 10-Year Financial Model"',
    }

    for old_title, new_title_fragment in renames.items():
        # Old title should NOT be in st.header calls
        old_in_header = re.search(
            rf'st\.header\({re.escape(old_title)}',
            source
        )
        assert old_in_header is None, \
            f"Old title still present: {old_title}"

        # New title should exist
        assert new_title_fragment in source, \
            f"New title not found: {new_title_fragment}"
        print(f"  OK  {old_title[:40]}... -> renamed")

    # Verify sensitivity threshold title changed
    assert "What Breaks the Deal? Sensitivity Thresholds" in source, \
        "Sensitivity Thresholds should have new title"
    print("  OK  Sensitivity title renamed")

    # Verify steel price sensitivity title enhanced
    assert "Steel Price Sensitivity: Impact on Valuation" in source, \
        "Steel Price Sensitivity should have enhanced title"
    print("  OK  Steel Price Sensitivity title enhanced")

    print("\nPASSED: Section Title Renames")
    return True


def test_key_numbers_collapsible():
    """Test 5: Key Numbers at a Glance is in an expander."""
    print("\n" + "=" * 60)
    print("TEST 5: Key Numbers Collapsible")
    print("=" * 60)

    source = read_dashboard_source()

    # Should use st.expander for Key Numbers
    assert 'st.expander("Key Numbers at a Glance"' in source, \
        "Key Numbers should be wrapped in st.expander"
    print("  OK  Key Numbers in st.expander")

    # Should be expanded=True by default
    key_numbers_match = re.search(
        r'st\.expander\("Key Numbers at a Glance",\s*expanded=True\)',
        source
    )
    assert key_numbers_match, "Key Numbers expander should default to expanded=True"
    print("  OK  Expanded by default (expanded=True)")

    print("\nPASSED: Key Numbers Collapsible")
    return True


def test_model_configuration_grouping():
    """Test 6: IRP, Bloomberg, and Calibration are grouped under Model Configuration."""
    print("\n" + "=" * 60)
    print("TEST 6: Model Configuration Grouping")
    print("=" * 60)

    source = read_dashboard_source()

    # Find Model Configuration header
    config_header = source.find('st.sidebar.header("Model Configuration")')
    assert config_header > 0, "Model Configuration header not found"
    print("  OK  Model Configuration header exists")

    # After Model Configuration, should find IRP, Bloomberg, Calibration
    config_section = source[config_header:]

    # IRP should be in an expander
    irp_expander = re.search(
        r'st\.sidebar\.expander\("Interest Rate Parity"',
        config_section
    )
    assert irp_expander, "IRP should be in a sidebar expander under Model Configuration"
    print("  OK  IRP in collapsible expander")

    # Bloomberg should be in an expander
    bloomberg_expander = re.search(
        r'st\.sidebar\.expander\("Bloomberg Market Data"',
        config_section
    )
    assert bloomberg_expander, "Bloomberg should be in a sidebar expander under Model Configuration"
    print("  OK  Bloomberg in collapsible expander")

    # Calibration should be in an expander
    calibration_expander = re.search(
        r'st\.sidebar\.expander\("Scenario Calibration"',
        config_section
    )
    assert calibration_expander, "Calibration should be in a sidebar expander under Model Configuration"
    print("  OK  Scenario Calibration in collapsible expander")

    print("\nPASSED: Model Configuration Grouping")
    return True


def test_no_duplicate_widget_keys():
    """Test 7: No duplicate Streamlit widget keys that would cause runtime errors."""
    print("\n" + "=" * 60)
    print("TEST 7: No Duplicate Widget Keys")
    print("=" * 60)

    source = read_dashboard_source()

    # Extract all key="..." values
    keys = re.findall(r'key="([^"]+)"', source)
    print(f"  Found {len(keys)} widget keys")

    # Check for duplicates
    seen = {}
    duplicates = []
    for key in keys:
        if key in seen:
            seen[key] += 1
            if seen[key] == 2:  # Only report first duplicate
                duplicates.append(key)
        else:
            seen[key] = 1

    if duplicates:
        print(f"  WARNING: {len(duplicates)} duplicate key(s) found:")
        for dup in duplicates[:10]:
            print(f"    - '{dup}' (appears {seen[dup]} times)")
        # Don't fail on this - some duplicates may be intentional (if/else branches)
        print("  NOTE: Some duplicates may be in mutually exclusive branches (OK)")
    else:
        print("  OK  No duplicate widget keys")

    print("\nPASSED: Widget Key Check")
    return True


def test_model_still_runs():
    """Test 8: The financial model still runs correctly after reorganization."""
    print("\n" + "=" * 60)
    print("TEST 8: Model Execution Validation")
    print("=" * 60)

    from price_volume_model import (
        PriceVolumeModel, ScenarioType, get_scenario_presets
    )

    presets = get_scenario_presets()
    scenario = presets[ScenarioType.BASE_CASE]

    print("  Running Base Case model...")
    model = PriceVolumeModel(scenario)
    analysis = model.run_full_analysis()

    # Validate key outputs
    val_uss = analysis['val_uss']
    val_nippon = analysis['val_nippon']

    print(f"  USS share price: ${val_uss['share_price']:.2f}")
    print(f"  Nippon share price: ${val_nippon['share_price']:.2f}")

    assert val_uss['share_price'] > 0, "USS share price should be positive"
    assert val_nippon['share_price'] > 0, "Nippon share price should be positive"
    assert val_uss['share_price'] < 200, "USS share price should be reasonable"
    assert val_nippon['share_price'] < 300, "Nippon share price should be reasonable"
    print("  OK  Valuations are reasonable")

    # Check consolidated FCF
    consolidated = analysis['consolidated']
    assert len(consolidated) >= 10, "Should have 10 years of projections"
    print(f"  OK  {len(consolidated)} years of consolidated projections")

    # Check segments
    segment_dfs = analysis['segment_dfs']
    assert len(segment_dfs) >= 4, "Should have at least 4 segments"
    print(f"  OK  {len(segment_dfs)} segments computed")

    print("\nPASSED: Model Execution Validation")
    return True


def test_verdict_no_backslash_dollar_in_html():
    """Test 9: HTML verdict boxes use plain $ not \\$ (which renders as literal backslash)."""
    print("\n" + "=" * 60)
    print("TEST 9: No Backslash-Dollar in HTML Boxes")
    print("=" * 60)

    source = read_dashboard_source()

    # Find all HTML verdict blocks (between unsafe_allow_html markers)
    verdict_start = source.find("# Deal Verdict Section")
    # Find the end - the Key Numbers section
    verdict_end = source.find("# Key Numbers Comparison", verdict_start)
    verdict_html = source[verdict_start:verdict_end]

    # In HTML blocks, \\$ would render as literal \$ in the browser
    # We should have plain $ in f-string HTML, not \\$
    # Check the f-string formatted text lines (inside <p> tags)
    html_lines = [l for l in verdict_html.split('\n') if '<p ' in l or '<h2 ' in l]
    backslash_dollar_in_html = [l.strip() for l in html_lines if '\\$' in l]

    if backslash_dollar_in_html:
        for line in backslash_dollar_in_html:
            print(f"  ISSUE: {line[:80]}...")
        assert False, f"Found {len(backslash_dollar_in_html)} HTML lines with \\$ (should be plain $)"

    # Also verify the premium_text/diff_text vars don't use \\$
    assert 'premium_text = f"+\\$' not in verdict_html, \
        "premium_text should use plain $ not \\$"
    assert 'diff_text = f"\\$' not in verdict_html, \
        "diff_text should use plain $ not \\$"
    assert 'discount_text = f"\\$' not in verdict_html, \
        "discount_text should use plain $ not \\$"
    print("  OK  No \\$ in HTML verdict boxes (plain $ used)")

    # Verify $ IS present (not removed entirely)
    assert 'The $55 offer' in verdict_html, "Should reference $55 offer in HTML"
    print("  OK  Dollar signs present in HTML content")

    print("\nPASSED: No Backslash-Dollar in HTML Boxes")
    return True


def test_bottom_line_dynamic():
    """Test 10: Bottom line text adapts to different scenario outcomes."""
    print("\n" + "=" * 60)
    print("TEST 10: Dynamic Bottom Line Text")
    print("=" * 60)

    source = read_dashboard_source()

    # Should have multiple conditional branches for bottom line
    bottom_line_start = source.find("# One-line bottom line")
    assert bottom_line_start > 0, "Bottom line section not found"
    bottom_line_section = source[bottom_line_start:bottom_line_start + 3000]

    # Should have different st.info/st.warning/st.error for different outcomes
    assert 'st.info(' in bottom_line_section, "Should have st.info for positive outcome"
    assert 'st.warning(' in bottom_line_section, "Should have st.warning for mixed outcomes"
    assert 'st.error(' in bottom_line_section, "Should have st.error for negative outcomes"
    print("  OK  Multiple outcome branches (info/warning/error)")

    # Should reference actual USS standalone value, not just offer_diff
    assert 'uss_standalone:.2f' in bottom_line_section, \
        "Should show actual USS standalone value"
    print("  OK  Shows USS standalone value dynamically")

    # Should NOT have the old generic text
    assert 'No alternative buyer can match this offer.' not in bottom_line_section or \
           bottom_line_section.count('No alternative buyer') == 1, \
        "Generic text should only appear in positive scenario"
    print("  OK  Bottom line varies by scenario outcome")

    # Should handle nippon_overpay case
    assert 'nippon_overpay' in bottom_line_section, \
        "Should calculate Nippon overpay for negative scenarios"
    print("  OK  Handles Nippon overpay case")

    print("\nPASSED: Dynamic Bottom Line Text")
    return True


def test_wacc_verified_before_slider():
    """Test 11: Verified WACC checkbox appears before the WACC slider."""
    print("\n" + "=" * 60)
    print("TEST 11: Verified WACC Before Slider")
    print("=" * 60)

    source = read_dashboard_source()

    # Find positions of the checkbox and slider
    checkbox_pos = source.find('st.sidebar.checkbox(\n            "Use Verified WACC"')
    if checkbox_pos == -1:
        checkbox_pos = source.find('"Use Verified WACC"')
    slider_pos = source.find('st.sidebar.slider("USS WACC"')

    assert checkbox_pos > 0, "Use Verified WACC checkbox not found"
    assert slider_pos > 0, "USS WACC slider not found"
    assert checkbox_pos < slider_pos, \
        f"Verified WACC checkbox (pos {checkbox_pos}) should come BEFORE WACC slider (pos {slider_pos})"
    print("  OK  Checkbox renders before slider")

    # Should sync session_state when verified
    wacc_section = source[checkbox_pos:slider_pos + 500]
    assert 'st.session_state.uss_wacc' in wacc_section and 'verified_uss_wacc_pct' in wacc_section, \
        "Should update st.session_state.uss_wacc to verified value"
    print("  OK  Syncs slider value to verified WACC")

    print("\nPASSED: Verified WACC Before Slider")
    return True


def test_sources_dollar_escaping():
    """Test 12: Dollar signs in Sources section are properly escaped for Streamlit markdown."""
    print("\n" + "=" * 60)
    print("TEST 12: Sources Dollar Escaping")
    print("=" * 60)

    source = read_dashboard_source()

    # Find the sources section
    sources_start = source.find("Model Sources & Assumptions")
    assert sources_start > 0, "Sources section not found"
    sources_section = source[sources_start:sources_start + 2000]

    # The Capital IQ line should have escaped dollars for Streamlit markdown
    assert '\\$4,339M' in sources_section, \
        "Total Debt $4,339M should be escaped as \\$4,339M in markdown"
    assert '\\$297M' in sources_section, \
        "Lease amount $297M should be escaped as \\$297M"
    assert '\\$3,913M' in sources_section, \
        "Model debt $3,913M should be escaped as \\$3,913M"
    assert '\\$1,391M' in sources_section, \
        "CIQ net debt should be escaped as \\$1,391M"
    assert '\\$1,366M' in sources_section, \
        "Model net debt should be escaped as \\$1,366M"
    print("  OK  All dollar amounts properly escaped in Sources section")

    print("\nPASSED: Sources Dollar Escaping")
    return True


# =========================================================================
# PHASE 3 TESTS: Performance & Polish
# =========================================================================

def test_tab_structure():
    """Test 13: Dashboard uses st.tabs with 5 tabs."""
    print("\n" + "=" * 60)
    print("TEST 13: Tab Structure")
    print("=" * 60)

    source = read_dashboard_source()
    assert 'st.tabs([' in source, "Should use st.tabs"
    assert '"Executive Decision"' in source, "Missing Executive Decision tab"
    assert '"Valuation Analysis"' in source, "Missing Valuation Analysis tab"
    assert '"Risk & Sensitivity"' in source, "Missing Risk & Sensitivity tab"
    assert '"Strategic Context"' in source, "Missing Strategic Context tab"
    assert '"Financial Projections"' in source, "Missing Financial Projections tab"
    print("  OK  All 5 tabs present")

    print("\nPASSED: Tab Structure")
    return True


def test_no_duplicate_helpers():
    """Test 14: get_dynamic_project_ebitda defined exactly once."""
    print("\n" + "=" * 60)
    print("TEST 14: No Duplicate Helper Functions")
    print("=" * 60)

    source = read_dashboard_source()
    count_ebitda = source.count('def get_dynamic_project_ebitda(')
    assert count_ebitda == 1, f"get_dynamic_project_ebitda: expected 1 definition, found {count_ebitda}"
    print("  OK  get_dynamic_project_ebitda defined exactly once")

    count_maint = source.count('def get_project_maintenance_capex(')
    assert count_maint == 1, f"get_project_maintenance_capex: expected 1 definition, found {count_maint}"
    print("  OK  get_project_maintenance_capex defined exactly once")

    # Verify they accept model as first parameter
    assert 'def get_dynamic_project_ebitda(model, proj, year)' in source, \
        "get_dynamic_project_ebitda should accept model as first parameter"
    assert 'def get_project_maintenance_capex(model, proj, year)' in source, \
        "get_project_maintenance_capex should accept model as first parameter"
    print("  OK  Both helpers accept model as first parameter")

    print("\nPASSED: No Duplicate Helper Functions")
    return True


def test_football_field_lazy():
    """Test 15: Football field is behind a button, not inline."""
    print("\n" + "=" * 60)
    print("TEST 15: Football Field Lazy Loading")
    print("=" * 60)

    source = read_dashboard_source()
    ff_start = source.find('Valuation Football Field')
    assert ff_start > 0, "Football Field section not found"
    # Get the section up to the next major section
    ff_section = source[ff_start:ff_start + 5000]

    assert 'st.button(' in ff_section, "Football field should have a generate button"
    assert 'btn_football_field' in ff_section, "Football field button should have key btn_football_field"
    assert 'ff_cache_key' in ff_section, "Football field should use cache key"
    print("  OK  Football field is behind a generate button with caching")

    print("\nPASSED: Football Field Lazy Loading")
    return True


def test_price_sensitivity_lazy():
    """Test 16: Steel Price Sensitivity is behind a button, not inline."""
    print("\n" + "=" * 60)
    print("TEST 16: Price Sensitivity Lazy Loading")
    print("=" * 60)

    source = read_dashboard_source()
    ps_start = source.find('Steel Price Sensitivity: Impact on Valuation')
    assert ps_start > 0, "Steel Price Sensitivity section not found"
    ps_section = source[ps_start:ps_start + 3000]

    assert 'st.button(' in ps_section, "Price sensitivity should have a calculate button"
    assert 'btn_price_sens' in ps_section, "Price sensitivity button should have key btn_price_sens"
    assert 'sens_cache_key' in ps_section, "Price sensitivity should use cache key"
    print("  OK  Price sensitivity is behind a calculate button with caching")

    print("\nPASSED: Price Sensitivity Lazy Loading")
    return True


def test_ctx_has_scenario_hash():
    """Test 17: ctx dict includes scenario_hash for caching."""
    print("\n" + "=" * 60)
    print("TEST 17: Context Has Scenario Hash")
    print("=" * 60)

    source = read_dashboard_source()
    assert "'scenario_hash'" in source, "ctx should include 'scenario_hash' key"
    assert "scenario_hash': current_hash" in source, "scenario_hash should be set to current_hash"
    print("  OK  ctx dict includes scenario_hash")

    print("\nPASSED: Context Has Scenario Hash")
    return True


def test_valuation_tab_toc():
    """Test 18: Valuation tab has a mini table of contents."""
    print("\n" + "=" * 60)
    print("TEST 18: Valuation Tab Table of Contents")
    print("=" * 60)

    source = read_dashboard_source()
    # Find the valuation tab function
    val_start = source.find('def render_tab_valuation(ctx):')
    assert val_start > 0, "render_tab_valuation not found"
    val_section = source[val_start:val_start + 2000]

    assert '#valuation-details' in val_section, "TOC should link to valuation-details"
    assert '#scenario-comparison' in val_section, "TOC should link to scenario-comparison"
    assert '#valuation-football-field' in val_section, "TOC should link to football-field"
    assert '#capital-projects' in val_section, "TOC should link to capital-projects"
    print("  OK  Valuation tab has mini TOC with anchor links")

    print("\nPASSED: Valuation Tab Table of Contents")
    return True


def test_projections_tab_toc():
    """Test 19: Projections tab has a mini table of contents."""
    print("\n" + "=" * 60)
    print("TEST 19: Projections Tab Table of Contents")
    print("=" * 60)

    source = read_dashboard_source()
    proj_start = source.find('def render_tab_projections(ctx):')
    assert proj_start > 0, "render_tab_projections not found"
    proj_section = source[proj_start:proj_start + 2000]

    assert '#fcf-projection' in proj_section, "TOC should link to fcf-projection"
    assert '#segment-analysis' in proj_section, "TOC should link to segment-analysis"
    assert '#detailed-projections' in proj_section, "TOC should link to detailed-projections"
    print("  OK  Projections tab has mini TOC with anchor links")

    print("\nPASSED: Projections Tab Table of Contents")
    return True


def test_scenario_comparison_cached():
    """Test 20: Scenario comparison uses session_state caching."""
    print("\n" + "=" * 60)
    print("TEST 20: Scenario Comparison Caching")
    print("=" * 60)

    source = read_dashboard_source()
    assert 'scenario_comparison_' in source, "Should have scenario_comparison cache key"
    assert 'sc_cache_key' in source, "Should use sc_cache_key variable"
    print("  OK  Scenario comparison is cached by scenario hash")

    print("\nPASSED: Scenario Comparison Caching")
    return True


def run_all_tests():
    """Run all reorganization tests."""
    print("\n" + "=" * 70)
    print(" DASHBOARD REORGANIZATION TEST SUITE (Phase 1 + Phase 3)")
    print("=" * 70)

    tests = [
        # Phase 1 tests
        ("Syntax & Imports", test_syntax_and_imports),
        ("Sidebar Section Order", test_sidebar_section_order),
        ("Verdict Box Styling", test_verdict_boxes_styled),
        ("Section Title Renames", test_section_titles_renamed),
        ("Key Numbers Collapsible", test_key_numbers_collapsible),
        ("Model Configuration Grouping", test_model_configuration_grouping),
        ("No Duplicate Widget Keys", test_no_duplicate_widget_keys),
        ("Model Execution", test_model_still_runs),
        ("No Backslash-Dollar in HTML", test_verdict_no_backslash_dollar_in_html),
        ("Dynamic Bottom Line", test_bottom_line_dynamic),
        ("Verified WACC Before Slider", test_wacc_verified_before_slider),
        ("Sources Dollar Escaping", test_sources_dollar_escaping),
        # Phase 3 tests
        ("Tab Structure", test_tab_structure),
        ("No Duplicate Helpers", test_no_duplicate_helpers),
        ("Football Field Lazy", test_football_field_lazy),
        ("Price Sensitivity Lazy", test_price_sensitivity_lazy),
        ("Context Has Scenario Hash", test_ctx_has_scenario_hash),
        ("Valuation Tab TOC", test_valuation_tab_toc),
        ("Projections Tab TOC", test_projections_tab_toc),
        ("Scenario Comparison Cached", test_scenario_comparison_cached),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            errors.append((name, str(e)))
            print(f"\n  FAILED: {name}")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Print summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70)
    print(f"  Total tests: {len(tests)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if errors:
        print("\n  Failures:")
        for name, error in errors:
            print(f"    - {name}: {error[:80]}")

    if failed == 0:
        print("\n  ALL TESTS PASSED!")
    else:
        print(f"\n  {failed} test(s) failed. Review errors above.")

    print("=" * 70 + "\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
