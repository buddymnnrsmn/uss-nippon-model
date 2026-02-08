"""Tests for centralized segment data module and bootstrap CIs."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.uss_segment_data import (
    USS_SEGMENT_DATA, SEGMENT_PRICE_MAP, MODEL_ASSUMPTIONS,
    get_segment_dataframe, get_segment_summary, load_wrds_quarterly,
)


class TestUSSSegmentData:
    """Tests for the hardcoded segment data."""

    def test_all_four_segments_present(self):
        assert set(USS_SEGMENT_DATA.keys()) == {"Flat-Rolled", "Mini Mill", "USSE", "Tubular"}

    def test_minimum_observations_per_segment(self):
        expected_min = {"Flat-Rolled": 11, "Mini Mill": 4, "USSE": 11, "Tubular": 11}
        for seg, data in USS_SEGMENT_DATA.items():
            assert len(data) >= expected_min[seg], f"{seg} should have {expected_min[seg]}+ obs, got {len(data)}"

    def test_year_ranges(self):
        for seg, data in USS_SEGMENT_DATA.items():
            years = [d[0] for d in data]
            assert years == sorted(years), f"{seg} years not sorted"
            if seg == "Mini Mill":
                assert min(years) == 2021, "Mini Mill should start 2021 (BRS acquisition)"
            else:
                assert min(years) == 2014, f"{seg} should start 2014"
            assert max(years) == 2024, f"{seg} should end 2024"

    def test_revenue_positive(self):
        for seg, data in USS_SEGMENT_DATA.items():
            for year, rev, ebitda, ship, price in data:
                assert rev > 0, f"{seg} FY{year} revenue should be positive"

    def test_segment_price_map_keys_match(self):
        assert set(SEGMENT_PRICE_MAP.keys()) == set(USS_SEGMENT_DATA.keys())

    def test_model_assumptions_keys_match(self):
        assert set(MODEL_ASSUMPTIONS.keys()) == set(USS_SEGMENT_DATA.keys())

    def test_realization_premiums(self):
        """Verify realization premiums match expected values."""
        assert MODEL_ASSUMPTIONS["Flat-Rolled"]["realization_premium"] == pytest.approx(0.044)
        assert MODEL_ASSUMPTIONS["Mini Mill"]["realization_premium"] == pytest.approx(-0.014)
        assert MODEL_ASSUMPTIONS["Tubular"]["realization_premium"] == pytest.approx(0.314)


class TestGetSegmentDataframe:
    """Tests for get_segment_dataframe convenience function."""

    def test_returns_dataframe_for_known_segment(self):
        df = get_segment_dataframe("Flat-Rolled", frequency="annual")
        assert len(df) >= 5
        assert "revenue" in df.columns

    def test_returns_empty_for_unknown_segment(self):
        df = get_segment_dataframe("Nonexistent")
        assert len(df) == 0

    def test_annual_fallback_has_margin(self):
        df = get_segment_dataframe("Tubular", frequency="annual")
        assert "margin" in df.columns
        assert "realized_price" in df.columns


class TestGetSegmentSummary:
    """Tests for get_segment_summary."""

    def test_returns_all_segments(self):
        summary = get_segment_summary()
        assert len(summary) == 4
        assert "Flat-Rolled" in summary

    def test_hardcoded_counts(self):
        summary = get_segment_summary()
        for seg, info in summary.items():
            assert info['hardcoded_annual'] >= 4, f"{seg} should have 4+ annual obs"


class TestWRDSQuarterly:
    """Tests for WRDS quarterly data loading."""

    def test_wrds_quarterly_csv_columns(self):
        """If WRDS CSV exists, check expected columns."""
        path = Path(__file__).parent.parent / 'data' / 'uss_segment_quarterly.csv'
        if not path.exists():
            pytest.skip("WRDS quarterly CSV not available")

        import pandas as pd
        df = pd.read_csv(path)
        assert 'segment' in df.columns
        assert 'revenue' in df.columns
        assert 'fiscal_year' in df.columns
        assert 'fiscal_quarter' in df.columns

    def test_wrds_quarterly_segment_coverage(self):
        """If WRDS CSV exists, FR/USSE/Tubular should have 60+ obs."""
        path = Path(__file__).parent.parent / 'data' / 'uss_segment_quarterly.csv'
        if not path.exists():
            pytest.skip("WRDS quarterly CSV not available")

        import pandas as pd
        df = pd.read_csv(path)
        for seg in ['Flat-Rolled', 'USSE', 'Tubular']:
            n = len(df[df['segment'] == seg])
            assert n >= 10, f"{seg} should have 10+ quarterly obs, got {n}"

    def test_wrds_annual_cross_validation(self):
        """If WRDS CSV exists, FY2019-2023 should match hardcoded ±5%."""
        path = Path(__file__).parent.parent / 'data' / 'uss_segment_quarterly.csv'
        if not path.exists():
            pytest.skip("WRDS quarterly CSV not available")

        import pandas as pd
        df = pd.read_csv(path)

        for seg_name, data in USS_SEGMENT_DATA.items():
            for year, rev_10k, _, _, _ in data:
                wrds_year = df[(df['segment'] == seg_name) & (df['fiscal_year'] == year)]
                if len(wrds_year) == 0:
                    continue
                wrds_rev = wrds_year['revenue'].sum()
                pct_diff = abs(wrds_rev - rev_10k) / rev_10k * 100
                assert pct_diff < 5, f"{seg_name} FY{year}: WRDS {wrds_rev:.0f} vs 10-K {rev_10k:.0f} ({pct_diff:.1f}%)"

    def test_fallback_when_csv_absent(self):
        """Fallback to hardcoded dict works when WRDS CSV is absent."""
        df = get_segment_dataframe("Flat-Rolled", frequency="annual")
        assert len(df) >= 5


class TestBootstrapCI:
    """Tests for bootstrap confidence interval function."""

    def test_bootstrap_ci_contains_point_estimate(self):
        from scripts.revenue_price_correlation import bootstrap_correlation_ci
        rng = np.random.RandomState(42)
        x = rng.randn(50)
        y = 0.7 * x + 0.3 * rng.randn(50)
        ci_lo, ci_hi = bootstrap_correlation_ci(x, y, n_boot=5000, rng=rng)
        r = np.corrcoef(x, y)[0, 1]
        assert ci_lo <= r <= ci_hi, f"Point estimate {r:.3f} outside CI [{ci_lo:.3f}, {ci_hi:.3f}]"

    def test_bootstrap_ci_width_decreases_with_n(self):
        from scripts.revenue_price_correlation import bootstrap_correlation_ci
        rng = np.random.RandomState(123)

        # Small sample
        x_small = rng.randn(10)
        y_small = 0.5 * x_small + rng.randn(10)
        lo_s, hi_s = bootstrap_correlation_ci(x_small, y_small, n_boot=5000, rng=rng)
        width_small = hi_s - lo_s

        # Larger sample
        rng2 = np.random.RandomState(123)
        x_large = rng2.randn(100)
        y_large = 0.5 * x_large + rng2.randn(100)
        lo_l, hi_l = bootstrap_correlation_ci(x_large, y_large, n_boot=5000, rng=rng2)
        width_large = hi_l - lo_l

        assert width_large < width_small, (
            f"Larger n should have narrower CI: {width_large:.3f} vs {width_small:.3f}"
        )

    def test_bootstrap_ci_small_sample(self):
        from scripts.revenue_price_correlation import bootstrap_correlation_ci
        ci_lo, ci_hi = bootstrap_correlation_ci([1, 2], [3, 4])
        assert np.isnan(ci_lo) and np.isnan(ci_hi)
