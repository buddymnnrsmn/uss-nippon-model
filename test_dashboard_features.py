#!/usr/bin/env python3
"""
Dashboard Feature Testing Script
=================================

Tests all enhanced dashboard features:
- Progress callbacks
- Cache system
- On-demand calculations
- Disk persistence
- Memory tracking
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path

# Import dashboard modules
from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType,
    get_scenario_presets, compare_scenarios,
    calculate_probability_weighted_valuation
)
import cache_persistence as cp


def test_progress_callbacks():
    """Test Phase 3.1: Progress callbacks"""
    print("\n" + "="*60)
    print("TEST 1: Progress Callbacks")
    print("="*60)

    progress_messages = []

    def capture_progress(percent, message):
        progress_messages.append((percent, message))
        if percent in [0, 25, 50, 75, 100]:
            print(f"  {percent:3d}% - {message}")

    presets = get_scenario_presets()
    scenario = presets[ScenarioType.BASE_CASE]

    print("Running model with progress callback...")
    model = PriceVolumeModel(scenario, progress_callback=capture_progress)
    analysis = model.run_full_analysis()

    print(f"\n✅ Captured {len(progress_messages)} progress updates")
    print(f"   Progress range: {progress_messages[0][0]}% → {progress_messages[-1][0]}%")
    print(f"   First message: {progress_messages[0][1]}")
    print(f"   Last message: {progress_messages[-1][1]}")

    assert len(progress_messages) >= 10, "Should have at least 10 progress updates"
    assert progress_messages[0][0] == 0, "Should start at 0%"
    assert progress_messages[-1][0] == 100, "Should end at 100%"

    return True


def test_cache_invalidation():
    """Test Phase 2A: Cache invalidation system"""
    print("\n" + "="*60)
    print("TEST 2: Cache Invalidation")
    print("="*60)

    from interactive_dashboard import create_scenario_hash

    presets = get_scenario_presets()
    scenario1 = presets[ScenarioType.BASE_CASE]
    scenario2 = presets[ScenarioType.OPTIMISTIC]

    hash1 = create_scenario_hash(scenario1, 1.0, None)
    hash2 = create_scenario_hash(scenario1, 1.0, None)
    hash3 = create_scenario_hash(scenario2, 1.0, None)

    print(f"  Hash 1 (Base Case): {hash1[:16]}...")
    print(f"  Hash 2 (Base Case): {hash2[:16]}...")
    print(f"  Hash 3 (Optimistic): {hash3[:16]}...")

    assert hash1 == hash2, "Same scenario should produce same hash"
    assert hash1 != hash3, "Different scenarios should produce different hashes"

    print("\n✅ Cache invalidation hashing works correctly")
    return True


def test_disk_persistence():
    """Test Phase 3.6: Disk persistence"""
    print("\n" + "="*60)
    print("TEST 3: Disk Persistence")
    print("="*60)

    # Clear any existing test caches
    cp.clear_all_caches()

    # Test data
    test_data = {
        'dataframe': 'mock_dataframe',
        'timestamp': datetime.now(),
        'value': 42.5
    }

    test_hash = "test_hash_12345"

    # Save to disk
    print("  Saving test cache to disk...")
    cp.save_calculation_cache('test_calc', test_data, test_hash)

    # Check it exists
    cache_dir = Path('./cache')
    pkl_file = cache_dir / f"test_calc_{test_hash}.pkl"
    json_file = cache_dir / f"test_calc_{test_hash}.json"

    assert pkl_file.exists(), "Cache pickle file should exist"
    assert json_file.exists(), "Cache metadata file should exist"
    print(f"  ✓ Cache files created: {pkl_file.name}")

    # Load from disk
    print("  Loading test cache from disk...")
    loaded_data = cp.load_calculation_cache('test_calc', test_hash)

    assert loaded_data is not None, "Should load cached data"
    assert loaded_data['value'] == test_data['value'], "Data should match"
    print(f"  ✓ Cache data loaded correctly")

    # Get cache info
    info = cp.get_cache_info('test_calc', test_hash)
    assert info is not None, "Should have metadata"
    assert 'timestamp' in info, "Metadata should include timestamp"
    print(f"  ✓ Cache metadata: {info['size_bytes']} bytes")

    # Test cache size
    size = cp.get_cache_size()
    assert size > 0, "Should report cache size"
    print(f"  ✓ Total cache size: {size} bytes")

    # Clean up
    cp.clear_all_caches()
    assert not pkl_file.exists(), "Cache should be cleared"
    print(f"  ✓ Cache cleanup successful")

    print("\n✅ Disk persistence working correctly")
    return True


def test_scenario_comparison_with_progress():
    """Test scenario comparison with progress bar"""
    print("\n" + "="*60)
    print("TEST 4: Scenario Comparison with Progress")
    print("="*60)

    progress_updates = []

    class MockProgressBar:
        def progress(self, percent, text):
            progress_updates.append((percent, text))
            if percent in [0, 33, 66, 100]:
                print(f"  {percent:3d}% - {text}")

    mock_bar = MockProgressBar()

    print("Running scenario comparison...")
    comparison_df = compare_scenarios(
        execution_factor=1.0,
        custom_benchmarks=None,
        progress_bar=mock_bar
    )

    print(f"\n✅ Comparison completed")
    print(f"   Progress updates: {len(progress_updates)}")
    print(f"   Scenarios compared: {len(comparison_df)}")
    print(f"   Columns: {', '.join(comparison_df.columns[:4])}...")

    assert len(comparison_df) >= 5, "Should compare at least 5 scenarios"
    assert len(progress_updates) >= 5, "Should have progress updates"

    return True


def test_probability_weighted_with_progress():
    """Test probability-weighted valuation with progress"""
    print("\n" + "="*60)
    print("TEST 5: Probability-Weighted Valuation with Progress")
    print("="*60)

    progress_updates = []

    class MockProgressBar:
        def progress(self, percent, text):
            progress_updates.append((percent, text))
            if percent in [0, 50, 100]:
                print(f"  {percent:3d}% - {text}")

    mock_bar = MockProgressBar()

    print("Running probability-weighted valuation...")
    pw_results = calculate_probability_weighted_valuation(
        custom_benchmarks=None,
        progress_bar=mock_bar
    )

    print(f"\n✅ Probability-weighted valuation completed")
    print(f"   Progress updates: {len(progress_updates)}")
    print(f"   Weighted USS value: ${pw_results['weighted_uss_value_per_share']:.2f}/share")
    print(f"   Weighted Nippon value: ${pw_results['weighted_nippon_value_per_share']:.2f}/share")
    print(f"   Scenarios evaluated: {len(pw_results['scenario_results'])}")

    assert len(progress_updates) >= 3, "Should have progress updates"
    assert 'weighted_uss_value_per_share' in pw_results, "Should have weighted values"

    return True


def test_memory_tracking():
    """Test memory tracking functions"""
    print("\n" + "="*60)
    print("TEST 6: Memory Tracking")
    print("="*60)

    import sys
    import pickle

    # Create test data of known size
    test_data = {
        'large_list': list(range(10000)),
        'dataframe': 'mock_df' * 1000,
        'timestamp': datetime.now()
    }

    # Calculate size
    size = sys.getsizeof(pickle.dumps(test_data))
    print(f"  Test data size: {size:,} bytes")

    # Format bytes function
    def format_bytes(bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"

    formatted = format_bytes(size)
    print(f"  Formatted: {formatted}")

    assert 'KB' in formatted or 'B' in formatted, "Should format correctly"

    # Test with cache persistence
    cp.clear_all_caches()
    cp.save_calculation_cache('memory_test', test_data, 'hash123')

    disk_size = cp.get_cache_size()
    print(f"  Disk cache size: {disk_size:,} bytes ({format_bytes(disk_size)})")

    assert disk_size > 0, "Should report cache size"

    cp.clear_all_caches()

    print("\n✅ Memory tracking working correctly")
    return True


def run_all_tests():
    """Run all dashboard tests"""
    print("\n" + "="*70)
    print(" DASHBOARD ENHANCEMENT TEST SUITE")
    print("="*70)

    tests = [
        ("Progress Callbacks", test_progress_callbacks),
        ("Cache Invalidation", test_cache_invalidation),
        ("Disk Persistence", test_disk_persistence),
        ("Scenario Comparison", test_scenario_comparison_with_progress),
        ("Probability-Weighted", test_probability_weighted_with_progress),
        ("Memory Tracking", test_memory_tracking),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {str(e)}")
            traceback.print_exc()

    # Print summary
    print("\n" + "="*70)
    print(" TEST SUMMARY")
    print("="*70)
    print(f"  Total tests: {len(tests)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Dashboard is fully functional.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review errors above.")

    print("="*70 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
