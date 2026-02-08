"""
Centralized USS segment data module.

Provides verified segment data from SEC 10-K filings (primary) or WRDS quarterly CSV.
Eliminates duplication of USS_SEGMENT_DATA across scripts.

Data Sources:
    FY2018 10-K (filed 2019-02-15): 2014-2018 segment data
    FY2023 10-K (filed 2024-02-02): 2019-2023 segment data
    FY2024 10-K (filed 2025-01-31): 2020-2024 segment data
    Overlapping years use most recent filing.

Usage:
    from data.uss_segment_data import (
        USS_SEGMENT_DATA, SEGMENT_PRICE_MAP, MODEL_ASSUMPTIONS,
        get_segment_dataframe, get_segment_summary, load_wrds_quarterly,
        load_mini_mill_quarterly
    )
"""

from pathlib import Path
from typing import Dict, Optional

import pandas as pd

DATA_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Verified 10-K Segment Data (FY2014-2024)
# Source: USS SEC 10-K filings (operating data tables + selected financial data)
# Format: (year, revenue_mm, ebit_mm, shipments_kt, realized_price)
#   revenue_mm = shipments_kt * realized_price / 1000 (derived)
#   ebit_mm = Segment earnings (loss) before interest and income taxes
# ---------------------------------------------------------------------------
USS_SEGMENT_DATA = {
    "Flat-Rolled": [
        # (year, revenue_mm, ebit_mm, shipments_kt, realized_price)
        # 2014 includes USSC through Sep 15, 2014
        (2014, 10737, 697, 13908, 772),   # FY2018 10-K
        (2015, 7364, -249, 10595, 695),   # FY2018 10-K
        (2016, 6723, 22, 10094, 666),     # FY2018 10-K
        (2017, 7178, 375, 9887, 726),     # FY2018 10-K
        (2018, 8524, 883, 10510, 811),    # FY2018 10-K
        (2019, 8057, 196, 10700, 753),    # FY2023 10-K
        (2020, 6254, -596, 8711, 718),    # FY2023 10-K
        (2021, 10569, 2685, 9018, 1172),  # FY2023 10-K Note 4
        (2022, 10558, 2008, 8373, 1261),  # FY2024 10-K Note 4
        (2023, 8967, 418, 8706, 1030),    # FY2024 10-K Note 4
        (2024, 7947, 399, 7845, 1013),    # FY2024 10-K Note 4 (EBIT = EBITDA 934 - DD&A 535)
    ],
    "Mini Mill": [
        # BRS acquired January 2021; no segment data prior to 2021
        (2021, 2930, 1206, 2230, 1314),   # FY2023 10-K Note 4
        (2022, 2593, 481, 2287, 1134),    # FY2024 10-K Note 4
        (2023, 2121, 215, 2424, 875),     # FY2024 10-K Note 4
        (2024, 1977, 30, 2307, 857),      # FY2024 10-K Note 4 (EBIT = EBITDA 233 - DD&A 203)
    ],
    "USSE": [
        (2014, 2787, 133, 4179, 667),     # FY2018 10-K
        (2015, 2248, 81, 4357, 516),      # FY2018 10-K
        (2016, 2172, 185, 4496, 483),     # FY2018 10-K
        (2017, 2852, 327, 4585, 622),     # FY2018 10-K
        (2018, 3089, 359, 4457, 693),     # FY2018 10-K
        (2019, 2341, -57, 3590, 652),     # FY2023 10-K
        (2020, 1904, 9, 3041, 626),       # FY2023 10-K
        (2021, 4156, 975, 4302, 966),     # FY2023 10-K Note 4
        (2022, 4097, 444, 3759, 1090),    # FY2024 10-K Note 4
        (2023, 3404, 4, 3899, 873),       # FY2024 10-K Note 4
        (2024, 2880, -54, 3578, 805),     # FY2024 10-K Note 4 (EBIT = EBITDA 71 - DD&A 125)
    ],
    "Tubular": [
        (2014, 2682, 257, 1744, 1538),    # FY2018 10-K
        (2015, 868, -181, 593, 1464),     # FY2018 10-K
        (2016, 428, -303, 400, 1071),     # FY2018 10-K
        (2017, 862, -99, 688, 1253),      # FY2018 10-K
        (2018, 1157, -58, 780, 1483),     # FY2018 10-K
        (2019, 1115, -67, 769, 1450),     # FY2023 10-K
        (2020, 590, -179, 464, 1271),     # FY2023 10-K
        (2021, 753, 1, 444, 1696),        # FY2023 10-K Note 4
        (2022, 1557, 544, 523, 2978),     # FY2024 10-K Note 4
        (2023, 1499, 589, 478, 3137),     # FY2024 10-K Note 4
        (2024, 907, 85, 476, 1905),       # FY2024 10-K Note 4 (EBIT = EBITDA 135 - DD&A 50)
    ],
}

# Segment EBITDA by year (from 10-K segment notes, where DD&A is reported separately)
# Only available for years where the segment note reports DD&A
SEGMENT_EBITDA = {
    "Flat-Rolled": {2021: 3176, 2022: 2507, 2023: 1023, 2024: 934},
    "Mini Mill": {2021: 1357, 2022: 639, 2023: 383, 2024: 233},
    "USSE": {2021: 1073, 2022: 529, 2023: 98, 2024: 71},
    "Tubular": {2021: 47, 2022: 592, 2023: 638, 2024: 135},
}

# Segment DD&A by year (from 10-K segment notes)
SEGMENT_DDA = {
    "Flat-Rolled": {2021: 491, 2022: 499, 2023: 605, 2024: 535},
    "Mini Mill": {2021: 151, 2022: 158, 2023: 168, 2024: 203},
    "USSE": {2021: 98, 2022: 85, 2023: 94, 2024: 125},
    "Tubular": {2021: 46, 2022: 48, 2023: 49, 2024: 50},
}

# Segment-to-price benchmark mappings (matching price_volume_model.py product mix)
SEGMENT_PRICE_MAP = {
    "Flat-Rolled": {"HRC US": 0.21, "CRC US": 0.40, "Coated (CRC proxy)": 0.39},
    "Mini Mill": {"HRC US": 0.55, "CRC US": 0.16, "Coated (CRC proxy)": 0.29},
    "USSE": {"HRC EU": 0.51, "CRC US": 0.08, "Coated (CRC proxy)": 0.40},
    "Tubular": {"OCTG US": 1.0},
}

# Model realization factors and margin sensitivities (from price_volume_model.py)
# NOTE: These were calibrated to produce Base Case USS=$39, Nippon=$55 valuations.
# The calibration is independent of USS_SEGMENT_DATA (used only for analysis scripts).
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


def load_mini_mill_quarterly() -> Optional[pd.DataFrame]:
    """Load Mini Mill quarterly data from build_mini_mill_quarterly.py output.

    Returns DataFrame with columns:
        year, quarter, revenue_mm, ebit_mm, shipments_kt, realized_price
    15 quarterly observations from Q1 2021 to Q3 2024.
    """
    path = DATA_DIR / 'mini_mill_quarterly.csv'
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
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
        DataFrame with revenue, ebit, shipments, realized_price, and period columns
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
        data = USS_SEGMENT_DATA[seg_name]
        years = [d[0] for d in data]
        info = {
            'hardcoded_annual': len(data),
            'year_range': (min(years), max(years)),
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

        # Mini Mill quarterly data
        if seg_name == 'Mini Mill':
            mm_q = load_mini_mill_quarterly()
            info['mini_mill_quarterly'] = len(mm_q) if mm_q is not None else 0

        summary[seg_name] = info

    return summary
