"""Tests for composite indicator scoring function."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.advanced_demand_analysis import compute_composite_indicator_score


@pytest.fixture
def sample_granger_df():
    return pd.DataFrame({
        'indicator': ['WTI Crude', 'Durable Goods', 'Housing Starts', 'Building Permits', 'ISM PMI'],
        'lag': [2, 1, 0, 0, 1],
        'f_stat': [15.2, 9.8, 2.1, 1.5, 3.8],
        'f_pvalue': [0.0002, 0.0024, 0.15, 0.25, 0.08],
        'n': [38, 39, 40, 40, 39],
    })


@pytest.fixture
def sample_stability_df():
    return pd.DataFrame({
        'indicator': ['WTI Crude', 'Durable Goods', 'Housing Starts', 'Building Permits', 'ISM PMI'],
        'pre_covid_r': [0.10, 0.15, 0.70, 0.65, -0.30],
        'post_covid_r': [0.69, 0.65, 0.11, 0.08, -0.44],
        'sign_flip': [False, False, False, False, False],
        'magnitude_change': [0.59, 0.50, 0.59, 0.57, 0.14],
        'stable': [False, False, False, False, True],
    })


@pytest.fixture
def sample_decomp_df():
    return pd.DataFrame({
        'indicator': ['WTI Crude', 'Durable Goods', 'Housing Starts', 'Building Permits', 'ISM PMI'],
        'r_full': [0.75, 0.68, 0.77, 0.72, -0.44],
        'r_partial': [0.69, 0.65, 0.11, 0.08, -0.44],
        'p_partial': [0.001, 0.003, 0.50, 0.65, 0.01],
        'r_volume': [0.55, 0.50, 0.05, 0.03, -0.30],
    })


class TestCompositeScoring:
    """Tests for compute_composite_indicator_score."""

    def test_returns_dataframe(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5

    def test_scores_non_negative(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        assert (result['composite_score'] >= 0).all()

    def test_scores_bounded(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        # Max possible: |partial_r|=1.0 * granger=1.0 * stability=1.0 = 1.0
        assert (result['composite_score'] <= 1.0).all()

    def test_spurious_indicators_score_low(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        """Housing Starts/Building Permits should score near zero (low partial r + no Granger)."""
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        hs_score = result[result['indicator'] == 'Housing Starts']['composite_score'].values[0]
        bp_score = result[result['indicator'] == 'Building Permits']['composite_score'].values[0]
        assert hs_score < 0.05, f"Housing Starts should score near 0, got {hs_score}"
        assert bp_score < 0.05, f"Building Permits should score near 0, got {bp_score}"

    def test_sign_flip_reduces_score(self, sample_granger_df, sample_decomp_df):
        """Sign-flip indicators should get stability_weight=0.25."""
        stability_with_flip = pd.DataFrame({
            'indicator': ['WTI Crude', 'Durable Goods', 'Housing Starts', 'Building Permits', 'ISM PMI'],
            'sign_flip': [True, False, False, False, False],
            'stable': [False, True, True, True, True],
        })
        result = compute_composite_indicator_score(sample_granger_df, stability_with_flip, sample_decomp_df)
        wti_row = result[result['indicator'] == 'WTI Crude'].iloc[0]
        assert wti_row['stability_weight'] == 0.25

    def test_sorted_descending(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        scores = result['composite_score'].values
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    def test_empty_decomposition_returns_empty(self, sample_granger_df, sample_stability_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, pd.DataFrame())
        assert len(result) == 0

    def test_granger_weight_thresholds(self, sample_granger_df, sample_stability_df, sample_decomp_df):
        result = compute_composite_indicator_score(sample_granger_df, sample_stability_df, sample_decomp_df)
        # WTI: p=0.0002 -> granger_weight=1.0
        wti = result[result['indicator'] == 'WTI Crude'].iloc[0]
        assert wti['granger_weight'] == 1.0
        # ISM PMI: p=0.08 -> granger_weight=0.5
        ism = result[result['indicator'] == 'ISM PMI'].iloc[0]
        assert ism['granger_weight'] == 0.5
        # Housing Starts: p=0.15 -> granger_weight=0.0
        hs = result[result['indicator'] == 'Housing Starts'].iloc[0]
        assert hs['granger_weight'] == 0.0
