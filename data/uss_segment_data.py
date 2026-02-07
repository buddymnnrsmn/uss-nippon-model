"""
Centralized USS segment data module.

Provides segment data from WRDS quarterly CSV (primary) or hardcoded fallback (FY2019-2023).
Eliminates duplication of USS_SEGMENT_DATA across scripts.

Usage:
    from data.uss_segment_data import (
        USS_SEGMENT_DATA, SEGMENT_PRICE_MAP, MODEL_ASSUMPTIONS,
        get_segment_dataframe, get_segment_summary, load_wrds_quarterly
    )
"""

from pathlib import Path
from typing import Dict, Optional

import pandas as pd

DATA_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Hardcoded fallback: USS 10-K Segment Data (FY2019-2023)
# ---------------------------------------------------------------------------
USS_SEGMENT_DATA = {
    "Flat-Rolled": [
        # (year, revenue_mm, ebitda_mm, shipments_kt, realized_price)
        (2019, 8543, 651, 9600, 890),
        (2020, 5996, -106, 7200, 833),
        (2021, 11276, 3394, 8400, 1342),
        (2022, 11863, 2801, 8100, 1465),
        (2023, 9402, 1016, 8700, 1081),
    ],
    "Mini Mill": [
        (2019, 1712, 196, 2300, 744),
        (2020, 1388, 114, 2000, 694),
        (2021, 3267, 1135, 2400, 1361),
        (2022, 3852, 1143, 2500, 1541),
        (2023, 3108, 539, 2700, 1151),
    ],
    "USSE": [
        (2019, 3054, 47, 4200, 727),
        (2020, 2163, -162, 3400, 636),
        (2021, 4223, 651, 4000, 1056),
        (2022, 4460, 564, 3800, 1174),
        (2023, 3481, 150, 3900, 893),
    ],
    "Tubular": [
        (2019, 1456, 47, 900, 1618),
        (2020, 740, -167, 500, 1480),
        (2021, 1167, 64, 700, 1667),
        (2022, 2647, 832, 900, 2941),
        (2023, 2714, 701, 800, 3393),
    ],
}

# Segment-to-price benchmark mappings (matching price_volume_model.py product mix)
SEGMENT_PRICE_MAP = {
    "Flat-Rolled": {"HRC US": 0.21, "CRC US": 0.40, "Coated (CRC proxy)": 0.39},
    "Mini Mill": {"HRC US": 0.55, "CRC US": 0.16, "Coated (CRC proxy)": 0.29},
    "USSE": {"HRC EU": 0.51, "CRC US": 0.08, "Coated (CRC proxy)": 0.40},
    "Tubular": {"OCTG US": 1.0},
}

# Model realization factors and margin sensitivities (from price_volume_model.py)
MODEL_ASSUMPTIONS = {
    "Flat-Rolled": {
        "base_price": 1030, "benchmark_weighted": 987,
        "realization_premium": 0.044, "margin_sensitivity": 2.0,
        "base_margin": 0.12,
    },
    "Mini Mill": {
        "base_price": 875, "benchmark_weighted": 888,
        "realization_premium": -0.014, "margin_sensitivity": 2.5,
        "base_margin": 0.17,
    },
    "USSE": {
        "base_price": 873, "benchmark_weighted": 836,
        "realization_premium": 0.044, "margin_sensitivity": 2.0,
        "base_margin": 0.09,
    },
    "Tubular": {
        "base_price": 3137, "benchmark_weighted": 2388,
        "realization_premium": 0.314, "margin_sensitivity": 1.0,
        "base_margin": 0.26,
    },
}


def load_wrds_quarterly() -> Optional[pd.DataFrame]:
    """Load WRDS quarterly segment data CSV if available."""
    path = DATA_DIR / 'uss_segment_quarterly.csv'
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df['datadate'] = pd.to_datetime(df['datadate'])
        return df
    except Exception:
        return None


def load_wrds_annual() -> Optional[pd.DataFrame]:
    """Load WRDS annual segment data CSV if available."""
    path = DATA_DIR / 'uss_segment_annual.csv'
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df['datadate'] = pd.to_datetime(df['datadate'])
        return df
    except Exception:
        return None


def get_segment_dataframe(segment_name: str,
                           frequency: str = 'quarterly') -> pd.DataFrame:
    """Get segment data as a DataFrame.

    Args:
        segment_name: One of 'Flat-Rolled', 'Mini Mill', 'USSE', 'Tubular'
        frequency: 'quarterly' (WRDS primary) or 'annual' (hardcoded fallback)

    Returns:
        DataFrame with revenue, operating_profit/ebitda, and period columns
    """
    if frequency == 'quarterly':
        wrds_df = load_wrds_quarterly()
        if wrds_df is not None:
            seg_df = wrds_df[wrds_df['segment'] == segment_name].copy()
            if len(seg_df) > 0:
                return seg_df

    # Fallback to hardcoded annual data
    if segment_name not in USS_SEGMENT_DATA:
        return pd.DataFrame()

    data = USS_SEGMENT_DATA[segment_name]
    df = pd.DataFrame(data, columns=['year', 'revenue', 'ebitda', 'shipments', 'realized_price'])
    df['segment'] = segment_name
    df['margin'] = df['ebitda'] / df['revenue']
    df['rev_per_ton'] = df['revenue'] / df['shipments'] * 1000
    return df


def get_segment_summary() -> Dict[str, Dict]:
    """Return observation counts per segment from WRDS and hardcoded sources."""
    summary = {}

    wrds_q = load_wrds_quarterly()
    wrds_a = load_wrds_annual()

    for seg_name in USS_SEGMENT_DATA.keys():
        info = {
            'hardcoded_annual': len(USS_SEGMENT_DATA[seg_name]),
            'wrds_quarterly': 0,
            'wrds_annual': 0,
            'wrds_year_range': None,
        }

        if wrds_q is not None:
            seg = wrds_q[wrds_q['segment'] == seg_name]
            info['wrds_quarterly'] = len(seg)
            if len(seg) > 0:
                info['wrds_year_range'] = (
                    int(seg['fiscal_year'].min()),
                    int(seg['fiscal_year'].max())
                )

        if wrds_a is not None:
            seg = wrds_a[wrds_a['segment'] == seg_name]
            info['wrds_annual'] = len(seg)

        summary[seg_name] = info

    return summary
