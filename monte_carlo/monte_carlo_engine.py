#!/usr/bin/env python3
"""
Monte Carlo Simulation Engine for USS / Nippon Steel Merger Model
==================================================================

Implements probabilistic valuation using Monte Carlo simulation with:
- Latin Hypercube Sampling for efficient coverage
- Correlation modeling via Cholesky decomposition
- Risk metrics (VaR, CVaR, percentiles)
- Integration with existing PriceVolumeModel
- Configurable distributions from distributions_config.json

Usage:
    from monte_carlo.monte_carlo_engine import MonteCarloEngine

    mc = MonteCarloEngine(n_simulations=10000)
    results = mc.run_simulation()
    mc.print_summary()
"""

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from scipy import stats
from scipy.linalg import cholesky
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import sys

# Config file location
DISTRIBUTIONS_CONFIG_PATH = Path(__file__).parent / 'distributions_config.json'

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType,
    SteelPriceScenario, VolumeScenario, get_scenario_presets,
    BENCHMARK_PRICES_2023, calculate_tariff_adjustment
)


# =============================================================================
# DISTRIBUTION DEFINITIONS
# =============================================================================

@dataclass
class Distribution:
    """Base class for probability distributions"""
    name: str
    dist_type: str  # 'normal', 'lognormal', 'triangular', 'beta', 'uniform', 'truncnorm'
    params: Dict[str, float]

    def sample(self, n: int, random_state: Optional[np.random.RandomState] = None) -> np.ndarray:
        """Generate n samples from this distribution"""
        if random_state is None:
            random_state = np.random.RandomState()

        if self.dist_type == 'normal':
            return random_state.normal(
                self.params['mean'],
                self.params['std'],
                n
            )
        elif self.dist_type == 'lognormal':
            return random_state.lognormal(
                self.params['mean'],
                self.params['std'],
                n
            )
        elif self.dist_type == 'triangular':
            return random_state.triangular(
                self.params['min'],
                self.params['mode'],
                self.params['max'],
                n
            )
        elif self.dist_type == 'beta':
            # Beta distribution scaled to [min, max]
            beta_samples = random_state.beta(
                self.params['alpha'],
                self.params['beta'],
                n
            )
            return self.params['min'] + beta_samples * (self.params['max'] - self.params['min'])
        elif self.dist_type == 'uniform':
            return random_state.uniform(
                self.params['min'],
                self.params['max'],
                n
            )
        elif self.dist_type == 'truncnorm':
            # Truncated normal distribution
            mean = self.params['mean']
            std = self.params['std']
            min_val = self.params['min']
            max_val = self.params['max']
            # Convert to scipy's truncnorm parameterization
            a = (min_val - mean) / std
            b = (max_val - mean) / std
            return stats.truncnorm.rvs(a, b, loc=mean, scale=std, size=n, random_state=random_state)
        else:
            raise ValueError(f"Unknown distribution type: {self.dist_type}")


@dataclass
class InputVariable:
    """Defines an input variable with its distribution and correlation info"""
    name: str
    description: str
    distribution: Distribution
    base_value: float  # Base case deterministic value
    correlations: Dict[str, float] = field(default_factory=dict)


# =============================================================================
# MULTIPROCESSING WORKER (module-level for pickling)
# =============================================================================

def _simulate_batch(args):
    """Process a batch of Monte Carlo iterations in a worker process.

    Must be at module level (not a method) so ProcessPoolExecutor can pickle it.
    Mirrors the logic in MonteCarloEngine._build_scenario_from_sample and the
    sequential run_simulation loop.
    """
    input_chunk, base_scenario, include_projects, execution_factor_override = args

    results = []
    for idx in range(len(input_chunk)):
        sample = input_chunk.iloc[idx]
        iteration_id = int(input_chunk.index[idx])

        # --- Build scenario (mirrors _build_scenario_from_sample) ---
        annual_price_growth = sample.get('annual_price_growth', 1.5) / 100
        hrc_eu_factor = sample.get('hrc_eu_factor', sample['hrc_price_factor'])
        usse_volume = sample.get('usse_volume', 1.0)

        # Tariff blending: continuous expected tariff rate
        tariff_prob = sample.get('tariff_probability', 0.80)
        tariff_alt = sample.get('tariff_rate_if_changed', 0.10)
        effective_tariff = tariff_prob * 0.25 + (1 - tariff_prob) * tariff_alt

        price_scenario = SteelPriceScenario(
            name="MC Sample", description="Sampled",
            hrc_us_factor=sample['hrc_price_factor'],
            crc_us_factor=sample['crc_price_factor'],
            coated_us_factor=sample['coated_price_factor'],
            hrc_eu_factor=hrc_eu_factor,
            octg_factor=sample['octg_price_factor'],
            annual_price_growth=annual_price_growth,
            tariff_rate=effective_tariff,
        )
        volume_scenario = VolumeScenario(
            name="MC Sample", description="Sampled",
            flat_rolled_volume_factor=sample['flat_rolled_volume'],
            mini_mill_volume_factor=sample['mini_mill_volume'],
            usse_volume_factor=usse_volume,
            tubular_volume_factor=sample['tubular_volume'],
            flat_rolled_growth_adj=0.0, mini_mill_growth_adj=0.0,
            usse_growth_adj=0.0, tubular_growth_adj=0.0,
        )

        # Rate parameters
        base_us_10yr = base_scenario.us_10yr if base_scenario else 0.0425
        base_japan_10yr = base_scenario.japan_10yr if base_scenario else 0.0075
        base_erp = base_scenario.nippon_equity_risk_premium if base_scenario else 0.0475
        base_credit_spread = base_scenario.nippon_credit_spread if base_scenario else 0.0075
        base_debt_ratio = base_scenario.nippon_debt_ratio if base_scenario else 0.35
        base_tax_rate = base_scenario.nippon_tax_rate if base_scenario else 0.30

        us_10yr = sample.get('us_10yr', base_us_10yr * 100) / 100
        japan_10yr = sample.get('japan_rf_rate', base_japan_10yr * 100) / 100
        nippon_erp = sample.get('nippon_erp', base_erp * 100) / 100

        proj_list = include_projects
        if proj_list is None:
            proj_list = list(base_scenario.include_projects) if base_scenario else []

        scenario = ModelScenario(
            name="MC Sample", scenario_type=ScenarioType.CUSTOM,
            description="Sampled from distributions",
            price_scenario=price_scenario, volume_scenario=volume_scenario,
            uss_wacc=sample['uss_wacc'] / 100,
            terminal_growth=sample['terminal_growth'] / 100,
            exit_multiple=sample['exit_multiple'],
            us_10yr=us_10yr, japan_10yr=japan_10yr,
            nippon_equity_risk_premium=nippon_erp,
            nippon_credit_spread=base_credit_spread,
            nippon_debt_ratio=base_debt_ratio,
            nippon_tax_rate=base_tax_rate,
            include_projects=proj_list,
            synergies=None,
        )

        margin_factor = sample.get('flat_rolled_margin_factor', 1.0)
        capex_factor = sample.get('capex_intensity_factor', 1.0)

        # --- Run model and extract results ---
        try:
            model = PriceVolumeModel(scenario)
            analysis = model.run_full_analysis()

            adj_ebitda = analysis['consolidated']['Total_EBITDA'].mean() * margin_factor
            adj_terminal_ebitda = analysis['val_uss']['terminal_ebitda'] * margin_factor
            capex_drag = 1.0 - 0.30 * (capex_factor - 1.0)
            ev_adjustment = margin_factor * capex_drag
            adj_uss_ev = analysis['val_uss']['ev_blended'] * ev_adjustment
            adj_nippon_ev = analysis['val_nippon']['ev_blended'] * ev_adjustment

            shares = 225.0
            equity_bridge = analysis['val_uss'].get('equity_bridge', -4000)
            adj_uss_share = max(0, adj_uss_ev + equity_bridge) / shares
            adj_nippon_share = max(0, adj_nippon_ev + equity_bridge) / shares

            results.append({
                'iteration': iteration_id,
                'uss_enterprise_value': adj_uss_ev,
                'uss_share_price': adj_uss_share,
                'nippon_enterprise_value': adj_nippon_ev,
                'nippon_share_price': adj_nippon_share,
                'total_fcf_10y': analysis['consolidated']['FCF'].sum() * margin_factor,
                'avg_ebitda': adj_ebitda,
                'avg_ebitda_margin': analysis['consolidated']['EBITDA_Margin'].mean() * margin_factor,
                'terminal_ebitda': adj_terminal_ebitda,
                'margin_factor': margin_factor,
                'capex_factor': capex_factor,
                'effective_tariff_rate': effective_tariff,
                'tariff_adjustment_hrc': calculate_tariff_adjustment(effective_tariff, 'hrc_us'),
            })
        except Exception:
            results.append({
                'iteration': iteration_id,
                'uss_enterprise_value': np.nan, 'uss_share_price': np.nan,
                'nippon_enterprise_value': np.nan, 'nippon_share_price': np.nan,
                'total_fcf_10y': np.nan, 'avg_ebitda': np.nan,
                'avg_ebitda_margin': np.nan, 'terminal_ebitda': np.nan,
                'margin_factor': np.nan, 'capex_factor': np.nan,
                'effective_tariff_rate': np.nan, 'tariff_adjustment_hrc': np.nan,
            })

    return results


# =============================================================================
# MONTE CARLO ENGINE
# =============================================================================

class MonteCarloEngine:
    """
    Monte Carlo simulation engine for DCF valuation

    Features:
    - Latin Hypercube Sampling for better coverage
    - Correlation modeling via Cholesky decomposition
    - Parallel execution support
    - Comprehensive risk metrics
    - Configurable distributions from distributions_config.json
    - Bloomberg calibration support (optional)
    """

    def __init__(
        self,
        n_simulations: int = 10000,
        random_seed: int = 42,
        use_lhs: bool = True,
        base_scenario: Optional[ModelScenario] = None,
        use_config_file: bool = True,
        use_bloomberg_calibration: bool = True,
        config_path: Optional[Path] = None,
        n_workers: int = 1
    ):
        """
        Initialize Monte Carlo engine

        Args:
            n_simulations: Number of Monte Carlo iterations
            random_seed: Random seed for reproducibility
            use_lhs: Use Latin Hypercube Sampling (recommended)
            base_scenario: Base scenario to modify (default: Base Case)
            use_config_file: If True, load distributions from distributions_config.json
            use_bloomberg_calibration: If True, load calibrated distributions from
                                       Bloomberg data when available
            config_path: Optional custom path to distributions config file
            n_workers: Number of parallel worker processes (1 = sequential)
        """
        self.n_simulations = n_simulations
        self.random_seed = random_seed
        self.use_lhs = use_lhs
        self.rng = np.random.RandomState(random_seed)
        self.use_config_file = use_config_file
        self.use_bloomberg_calibration = use_bloomberg_calibration
        self.bloomberg_calibration_used = False
        self.config_file_used = False
        self.config_path = config_path or DISTRIBUTIONS_CONFIG_PATH
        self.n_workers = n_workers

        # Base scenario
        if base_scenario is None:
            self.base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]
        else:
            self.base_scenario = base_scenario

        # Load config-based correlations if available
        self.config_correlations = None

        # Define input variables and distributions (may load from config/Bloomberg)
        self.variables = self._define_input_variables()

        # Results storage
        self.simulation_inputs = None
        self.simulation_results = None
        self.summary_stats = None

    def _load_bloomberg_calibration(self) -> Optional[dict]:
        """
        Try to load calibrated distributions from Bloomberg data.

        Uses data cutoff of Dec 31, 2023 to avoid look-ahead bias
        (USS Board approved Nippon deal on Dec 18, 2023).

        Returns:
            Dict of calibrated distributions, or None if unavailable.
        """
        if not self.use_bloomberg_calibration:
            return None

        try:
            import sys
            from datetime import datetime
            from pathlib import Path as BloombergPath
            _bloomberg_module_path = BloombergPath(__file__).parent.parent / "market-data" / "bloomberg"
            if str(_bloomberg_module_path.parent) not in sys.path:
                sys.path.insert(0, str(_bloomberg_module_path.parent))

            from bloomberg import get_calibrated_distributions, is_bloomberg_available

            if is_bloomberg_available():
                # Use Dec 31, 2023 cutoff to avoid look-ahead bias
                # The USS Board approved the Nippon deal on Dec 18, 2023
                cutoff_date = datetime(2023, 12, 31)

                # Use consistent baseline prices with distributions_config.json
                baseline_prices = {
                    'hrc_us': 780,   # 2023 avg HRC price
                    'crc_us': 990,   # 2023 avg CRC price
                    'hrc_eu': 620,
                    'octg_us': 1650, # 2023 avg OCTG price
                }

                calibration = get_calibrated_distributions(
                    end_date=cutoff_date,
                    baseline_prices=baseline_prices
                )
                if calibration:
                    # Apply mean-reversion: recenter distributions to E[X]=1.0
                    # For lognormal: if we want E[X]=1.0 with volatility σ, then μ = -σ²/2
                    for var_name, var_data in calibration.items():
                        if var_data.get('dist_type') == 'lognormal':
                            sigma = var_data['params'].get('std', 0.2)
                            # Recenter to mean=1.0 (mean-reverting assumption)
                            var_data['params']['mean'] = -sigma**2 / 2

                    self.bloomberg_calibration_used = True
                    return calibration
        except ImportError:
            pass
        except Exception as e:
            print(f"Warning: Failed to load Bloomberg calibration: {e}")

        return None

    def _load_distributions_from_config(self) -> Optional[dict]:
        """
        Load calibrated distributions from distributions_config.json

        Returns:
            Dict with 'variables' and 'correlations' from config, or None if unavailable
        """
        if not self.use_config_file:
            return None

        if not self.config_path.exists():
            return None

        try:
            with open(self.config_path) as f:
                config = json.load(f)

            if 'variables' in config:
                self.config_file_used = True
                # Store correlations for later use
                self.config_correlations = config.get('correlations', {})
                return config['variables']
        except Exception as e:
            print(f"Warning: Failed to load distributions config: {e}")

        return None

    def _validate_distribution_params(self, dist_type: str, params: dict) -> List[str]:
        """
        Validate distribution parameters at runtime

        Args:
            dist_type: Distribution type
            params: Parameter dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if dist_type == 'normal':
            if 'mean' not in params:
                errors.append("Normal distribution requires 'mean' parameter")
            if 'std' not in params:
                errors.append("Normal distribution requires 'std' parameter")
            elif params['std'] <= 0:
                errors.append("Normal 'std' must be positive")

        elif dist_type == 'lognormal':
            if 'mean' not in params:
                errors.append("Lognormal distribution requires 'mean' parameter (log-space)")
            if 'std' not in params:
                errors.append("Lognormal distribution requires 'std' parameter (log-space)")
            elif params['std'] <= 0:
                errors.append("Lognormal 'std' must be positive")

        elif dist_type == 'triangular':
            required = ['min', 'mode', 'max']
            for p in required:
                if p not in params:
                    errors.append(f"Triangular distribution requires '{p}' parameter")
            if all(p in params for p in required):
                if not (params['min'] <= params['mode'] <= params['max']):
                    errors.append("Triangular requires min <= mode <= max")
                if params['min'] == params['max']:
                    errors.append("Triangular min and max cannot be equal")

        elif dist_type == 'beta':
            if 'alpha' not in params:
                errors.append("Beta distribution requires 'alpha' parameter")
            elif params['alpha'] <= 0:
                errors.append("Beta 'alpha' must be positive")
            if 'beta' not in params:
                errors.append("Beta distribution requires 'beta' parameter")
            elif params['beta'] <= 0:
                errors.append("Beta 'beta' must be positive")
            if 'min' not in params or 'max' not in params:
                errors.append("Beta distribution requires 'min' and 'max' parameters")
            elif params.get('min', 0) >= params.get('max', 1):
                errors.append("Beta 'min' must be less than 'max'")

        elif dist_type == 'uniform':
            if 'min' not in params or 'max' not in params:
                errors.append("Uniform distribution requires 'min' and 'max' parameters")
            elif params.get('min', 0) >= params.get('max', 1):
                errors.append("Uniform 'min' must be less than 'max'")

        elif dist_type == 'truncnorm':
            if 'mean' not in params or 'std' not in params:
                errors.append("Truncated normal requires 'mean' and 'std' parameters")
            if 'min' not in params or 'max' not in params:
                errors.append("Truncated normal requires 'min' and 'max' parameters")
            if params.get('std', 1) <= 0:
                errors.append("Truncated normal 'std' must be positive")
            if params.get('min', 0) >= params.get('max', 1):
                errors.append("Truncated normal 'min' must be less than 'max'")

        else:
            errors.append(f"Unknown distribution type: {dist_type}")

        return errors

    def _define_input_variables(self) -> Dict[str, InputVariable]:
        """
        Define all uncertain input variables with their distributions

        Calibrated to USS historical data and industry benchmarks.
        Priority order for calibration:
        1. Bloomberg calibration (if available)
        2. Config file (distributions_config.json)
        3. Hardcoded defaults
        """
        variables = {}

        # Try to load calibrations (config first, then Bloomberg can override)
        config_cal = self._load_distributions_from_config()
        bloomberg_cal = self._load_bloomberg_calibration()

        # Helper to get calibrated params
        def get_config_or_default(var_name: str, default_dist_type: str, default_params: dict) -> Tuple[str, dict]:
            """Get distribution type and params from config, Bloomberg, or defaults.

            Priority: config file > Bloomberg > hardcoded defaults.
            Config file contains deliberately calibrated through-cycle parameters.
            Bloomberg provides raw historical fits (may include crisis-period volatility).
            """
            # Config file takes priority (manually calibrated, through-cycle)
            if config_cal and var_name in config_cal:
                cal = config_cal[var_name]
                return (
                    cal.get('distribution_type', default_dist_type),
                    cal.get('parameters', default_params)
                )
            # Then Bloomberg (raw historical fit)
            if bloomberg_cal and var_name in bloomberg_cal:
                cal = bloomberg_cal[var_name]
                return (
                    cal.get('distribution_type', default_dist_type),
                    cal.get('params', default_params)
                )
            return (default_dist_type, default_params)

        # Helper to get correlations from config
        def get_correlations(var_name: str, default_correlations: dict) -> dict:
            """Get correlations from config or use defaults"""
            if self.config_correlations and var_name in self.config_correlations:
                return self.config_correlations[var_name]
            return default_correlations

        # =====================================================================
        # STEEL PRICES - Most critical driver
        # =====================================================================

        hrc_dist_type, hrc_params = get_config_or_default(
            'hrc_price_factor', 'lognormal', {'mean': -0.0162, 'std': 0.18}
        )
        variables['hrc_price_factor'] = InputVariable(
            name='hrc_price_factor',
            description='HRC Steel Price Factor (vs 2023 baseline)',
            distribution=Distribution(
                name='HRC Price Factor',
                dist_type=hrc_dist_type,
                params=hrc_params
            ),
            base_value=0.95,
            correlations=get_correlations('hrc_price_factor', {
                'crc_price_factor': 0.95,
                'coated_price_factor': 0.93,
                'octg_price_factor': 0.65,
                'flat_rolled_volume': 0.40,
                'uss_wacc': -0.20,
            })
        )

        crc_dist_type, crc_params = get_config_or_default(
            'crc_price_factor', 'lognormal', {'mean': -0.0128, 'std': 0.16}
        )
        variables['crc_price_factor'] = InputVariable(
            name='crc_price_factor',
            description='CRC Steel Price Factor',
            distribution=Distribution(
                name='CRC Price Factor',
                dist_type=crc_dist_type,
                params=crc_params
            ),
            base_value=0.95,
            correlations=get_correlations('crc_price_factor', {
                'hrc_price_factor': 0.95,
                'coated_price_factor': 0.92,
                'flat_rolled_volume': 0.35,
            })
        )

        coated_dist_type, coated_params = get_config_or_default(
            'coated_price_factor', 'lognormal', {'mean': -0.0113, 'std': 0.15}
        )
        variables['coated_price_factor'] = InputVariable(
            name='coated_price_factor',
            description='Coated Steel Price Factor',
            distribution=Distribution(
                name='Coated Price Factor',
                dist_type=coated_dist_type,
                params=coated_params
            ),
            base_value=0.95,
            correlations=get_correlations('coated_price_factor', {
                'hrc_price_factor': 0.93,
                'crc_price_factor': 0.92,
                'flat_rolled_volume': 0.30,
            })
        )

        octg_dist_type, octg_params = get_config_or_default(
            'octg_price_factor', 'lognormal', {'mean': -0.0242, 'std': 0.22}
        )
        variables['octg_price_factor'] = InputVariable(
            name='octg_price_factor',
            description='OCTG Price Factor',
            distribution=Distribution(
                name='OCTG Price Factor',
                dist_type=octg_dist_type,
                params=octg_params
            ),
            base_value=0.95,
            correlations=get_correlations('octg_price_factor', {
                'tubular_volume': 0.75,
            })
        )

        # =====================================================================
        # VOLUMES - Moderate impact
        # =====================================================================

        fr_vol_type, fr_vol_params = get_config_or_default(
            'flat_rolled_volume', 'normal', {'mean': 1.00, 'std': 0.08}
        )
        variables['flat_rolled_volume'] = InputVariable(
            name='flat_rolled_volume',
            description='Flat-Rolled Volume Factor',
            distribution=Distribution(
                name='Flat-Rolled Volume',
                dist_type=fr_vol_type,
                params=fr_vol_params
            ),
            base_value=1.00,
            correlations=get_correlations('flat_rolled_volume', {
                'mini_mill_volume': 0.70,
            })
        )

        mm_vol_type, mm_vol_params = get_config_or_default(
            'mini_mill_volume', 'normal', {'mean': 1.00, 'std': 0.06}
        )
        variables['mini_mill_volume'] = InputVariable(
            name='mini_mill_volume',
            description='Mini Mill Volume Factor',
            distribution=Distribution(
                name='Mini Mill Volume',
                dist_type=mm_vol_type,
                params=mm_vol_params
            ),
            base_value=1.00,
        )

        tub_vol_type, tub_vol_params = get_config_or_default(
            'tubular_volume', 'triangular', {'min': 0.65, 'mode': 1.00, 'max': 1.35}
        )
        variables['tubular_volume'] = InputVariable(
            name='tubular_volume',
            description='Tubular Volume Factor',
            distribution=Distribution(
                name='Tubular Volume',
                dist_type=tub_vol_type,
                params=tub_vol_params
            ),
            base_value=1.00,
            correlations=get_correlations('tubular_volume', {
                'octg_price_factor': 0.75,
            })
        )

        # USSE (European) Volume Factor
        usse_vol_type, usse_vol_params = get_config_or_default(
            'usse_volume', 'normal', {'mean': 1.00, 'std': 0.10}
        )
        variables['usse_volume'] = InputVariable(
            name='usse_volume',
            description='USSE (European) Volume Factor',
            distribution=Distribution(
                name='USSE Volume',
                dist_type=usse_vol_type,
                params=usse_vol_params
            ),
            base_value=1.00,
            correlations=get_correlations('usse_volume', {
                'flat_rolled_volume': 0.50,  # Global steel demand correlation
            })
        )

        # Annual Price Growth Rate
        apg_type, apg_params = get_config_or_default(
            'annual_price_growth', 'normal', {'mean': 1.5, 'std': 1.0}
        )
        variables['annual_price_growth'] = InputVariable(
            name='annual_price_growth',
            description='Annual Steel Price Growth (%)',
            distribution=Distribution(
                name='Price Growth',
                dist_type=apg_type,
                params=apg_params
            ),
            base_value=1.5,
            correlations=get_correlations('annual_price_growth', {
                'hrc_price_factor': 0.30,  # High current prices may mean lower growth
            })
        )

        # HRC EU Price Factor (independent from US)
        hrc_eu_type, hrc_eu_params = get_config_or_default(
            'hrc_eu_factor', 'lognormal', {'mean': -0.0113, 'std': 0.15}
        )
        variables['hrc_eu_factor'] = InputVariable(
            name='hrc_eu_factor',
            description='HRC EU Price Factor',
            distribution=Distribution(
                name='HRC EU Price',
                dist_type=hrc_eu_type,
                params=hrc_eu_params
            ),
            base_value=0.95,
            correlations=get_correlations('hrc_eu_factor', {
                'hrc_price_factor': 0.70,  # Correlated but not identical to US
            })
        )

        # =====================================================================
        # DISCOUNT RATE - High impact
        # =====================================================================

        wacc_type, wacc_params = get_config_or_default(
            'uss_wacc', 'normal', {'mean': 10.9, 'std': 0.8}
        )
        variables['uss_wacc'] = InputVariable(
            name='uss_wacc',
            description='USS WACC (%)',
            distribution=Distribution(
                name='USS WACC',
                dist_type=wacc_type,
                params=wacc_params
            ),
            base_value=10.9,
        )

        jp_rf_type, jp_rf_params = get_config_or_default(
            'japan_rf_rate', 'normal', {'mean': 0.75, 'std': 0.30}
        )
        variables['japan_rf_rate'] = InputVariable(
            name='japan_rf_rate',
            description='Japan Risk-Free Rate (%)',
            distribution=Distribution(
                name='Japan RF Rate',
                dist_type=jp_rf_type,
                params=jp_rf_params
            ),
            base_value=0.75,
            correlations=get_correlations('japan_rf_rate', {
                'uss_wacc': -0.30,
                'us_10yr': 0.40,  # Global rate correlation
            })
        )

        # US 10Y Treasury Rate (affects IRP calculation)
        us10y_type, us10y_params = get_config_or_default(
            'us_10yr', 'normal', {'mean': 4.25, 'std': 0.50}
        )
        variables['us_10yr'] = InputVariable(
            name='us_10yr',
            description='US 10Y Treasury Rate (%)',
            distribution=Distribution(
                name='US 10Y Treasury',
                dist_type=us10y_type,
                params=us10y_params
            ),
            base_value=4.25,
            correlations=get_correlations('us_10yr', {
                'uss_wacc': 0.60,  # Higher rates → higher WACC
                'japan_rf_rate': 0.40,
            })
        )

        # Nippon Equity Risk Premium
        nerp_type, nerp_params = get_config_or_default(
            'nippon_erp', 'normal', {'mean': 4.75, 'std': 0.50}
        )
        variables['nippon_erp'] = InputVariable(
            name='nippon_erp',
            description='Nippon Equity Risk Premium (%)',
            distribution=Distribution(
                name='Nippon ERP',
                dist_type=nerp_type,
                params=nerp_params
            ),
            base_value=4.75,
        )

        # =====================================================================
        # TERMINAL VALUE ASSUMPTIONS
        # =====================================================================

        tg_type, tg_params = get_config_or_default(
            'terminal_growth', 'triangular', {'min': -0.5, 'mode': 1.0, 'max': 2.5}
        )
        variables['terminal_growth'] = InputVariable(
            name='terminal_growth',
            description='Terminal Growth Rate (%)',
            distribution=Distribution(
                name='Terminal Growth',
                dist_type=tg_type,
                params=tg_params
            ),
            base_value=1.0,
        )

        em_type, em_params = get_config_or_default(
            'exit_multiple', 'triangular', {'min': 3.5, 'mode': 4.5, 'max': 6.5}
        )
        variables['exit_multiple'] = InputVariable(
            name='exit_multiple',
            description='Exit EV/EBITDA Multiple',
            distribution=Distribution(
                name='Exit Multiple',
                dist_type=em_type,
                params=em_params
            ),
            base_value=4.5,
        )

        # =====================================================================
        # EXECUTION RISK (for NSA Mandated CapEx scenario)
        # =====================================================================

        gw_type, gw_params = get_config_or_default(
            'gary_works_execution', 'beta', {'alpha': 8, 'beta': 3, 'min': 0.40, 'max': 1.00}
        )
        variables['gary_works_execution'] = InputVariable(
            name='gary_works_execution',
            description='Gary Works BF Execution Success',
            distribution=Distribution(
                name='Gary Works Success',
                dist_type=gw_type,
                params=gw_params
            ),
            base_value=0.75,
            correlations=get_correlations('gary_works_execution', {
                'mon_valley_execution': 0.60,
            })
        )

        mv_type, mv_params = get_config_or_default(
            'mon_valley_execution', 'beta', {'alpha': 9, 'beta': 2, 'min': 0.50, 'max': 1.00}
        )
        variables['mon_valley_execution'] = InputVariable(
            name='mon_valley_execution',
            description='Mon Valley HSM Execution Success',
            distribution=Distribution(
                name='Mon Valley Success',
                dist_type=mv_type,
                params=mv_params
            ),
            base_value=0.80,
        )

        # =====================================================================
        # NEW VARIABLES - Added for enhanced calibration
        # =====================================================================

        # Flat-rolled margin factor (peer-based variation)
        frm_type, frm_params = get_config_or_default(
            'flat_rolled_margin_factor', 'triangular', {'min': 0.85, 'mode': 1.00, 'max': 1.15}
        )
        variables['flat_rolled_margin_factor'] = InputVariable(
            name='flat_rolled_margin_factor',
            description='Flat-Rolled Margin Factor (peer variation)',
            distribution=Distribution(
                name='Margin Factor',
                dist_type=frm_type,
                params=frm_params
            ),
            base_value=1.00,
        )

        # Operating synergy realization factor
        os_type, os_params = get_config_or_default(
            'operating_synergy_factor', 'beta', {'alpha': 8, 'beta': 3, 'min': 0.50, 'max': 1.00}
        )
        variables['operating_synergy_factor'] = InputVariable(
            name='operating_synergy_factor',
            description='Operating Synergy Realization Rate',
            distribution=Distribution(
                name='Operating Synergy Factor',
                dist_type=os_type,
                params=os_params
            ),
            base_value=0.80,
            correlations={
                'gary_works_execution': 0.40,  # Common execution capability
            }
        )

        # Revenue synergy realization factor (typically harder to achieve)
        rs_type, rs_params = get_config_or_default(
            'revenue_synergy_factor', 'beta', {'alpha': 3, 'beta': 4, 'min': 0.30, 'max': 0.90}
        )
        variables['revenue_synergy_factor'] = InputVariable(
            name='revenue_synergy_factor',
            description='Revenue Synergy Realization Rate',
            distribution=Distribution(
                name='Revenue Synergy Factor',
                dist_type=rs_type,
                params=rs_params
            ),
            base_value=0.55,
        )

        # Working capital efficiency factor
        wc_type, wc_params = get_config_or_default(
            'working_capital_efficiency', 'normal', {'mean': 1.00, 'std': 0.08}
        )
        variables['working_capital_efficiency'] = InputVariable(
            name='working_capital_efficiency',
            description='Working Capital Efficiency Factor',
            distribution=Distribution(
                name='Working Capital Efficiency',
                dist_type=wc_type,
                params=wc_params
            ),
            base_value=1.00,
        )

        # CapEx intensity factor
        cx_type, cx_params = get_config_or_default(
            'capex_intensity_factor', 'triangular', {'min': 0.80, 'mode': 1.00, 'max': 1.30}
        )
        variables['capex_intensity_factor'] = InputVariable(
            name='capex_intensity_factor',
            description='CapEx Intensity Factor (vs plan)',
            distribution=Distribution(
                name='CapEx Intensity',
                dist_type=cx_type,
                params=cx_params
            ),
            base_value=1.00,
        )

        # =====================================================================
        # TARIFF VARIABLES - Section 232 policy risk
        # =====================================================================

        tp_type, tp_params = get_config_or_default(
            'tariff_probability', 'beta', {'alpha': 8, 'beta': 2, 'min': 0.0, 'max': 1.0}
        )
        variables['tariff_probability'] = InputVariable(
            name='tariff_probability',
            description='P(Section 232 tariff maintained at 25%)',
            distribution=Distribution(
                name='Tariff Probability',
                dist_type=tp_type,
                params=tp_params
            ),
            base_value=0.80,
            correlations=get_correlations('tariff_probability', {
                'hrc_price_factor': -0.35,
                'crc_price_factor': -0.35,
                'coated_price_factor': -0.30,
                'octg_price_factor': -0.20,
                'flat_rolled_volume': -0.25,
                'mini_mill_volume': -0.15,
                'hrc_eu_factor': -0.10,
            })
        )

        tr_type, tr_params = get_config_or_default(
            'tariff_rate_if_changed', 'triangular', {'min': 0.0, 'mode': 0.10, 'max': 0.25}
        )
        variables['tariff_rate_if_changed'] = InputVariable(
            name='tariff_rate_if_changed',
            description='Tariff rate if policy changes (0-25%)',
            distribution=Distribution(
                name='Alt Tariff Rate',
                dist_type=tr_type,
                params=tr_params
            ),
            base_value=0.10,
        )

        return variables

    def _build_correlation_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """
        Build correlation matrix from variable definitions

        Returns:
            correlation_matrix: NxN correlation matrix
            variable_names: List of variable names in order
        """
        var_names = list(self.variables.keys())
        n_vars = len(var_names)

        # Initialize with identity matrix
        corr_matrix = np.eye(n_vars)

        # Fill in correlations
        for i, var1 in enumerate(var_names):
            for j, var2 in enumerate(var_names):
                if i != j and var2 in self.variables[var1].correlations:
                    corr_matrix[i, j] = self.variables[var1].correlations[var2]
                    corr_matrix[j, i] = self.variables[var1].correlations[var2]

        # Ensure positive semi-definite
        # (add small value to diagonal if needed)
        min_eigenval = np.linalg.eigvalsh(corr_matrix)[0]
        if min_eigenval < 0:
            corr_matrix += np.eye(n_vars) * (abs(min_eigenval) + 0.01)
            # Rescale to unit diagonal
            D = np.diag(1.0 / np.sqrt(np.diag(corr_matrix)))
            corr_matrix = D @ corr_matrix @ D

        return corr_matrix, var_names

    def _generate_correlated_samples(self) -> pd.DataFrame:
        """
        Generate correlated samples using Latin Hypercube or random sampling

        Returns:
            DataFrame with columns for each variable
        """
        var_names = list(self.variables.keys())
        n_vars = len(var_names)

        if self.use_lhs:
            # Latin Hypercube Sampling for better coverage
            # Generate uniformly distributed LHS samples
            lhs_samples = self._latin_hypercube_sample(n_vars, self.n_simulations)

            # Transform to standard normal
            standard_normal = stats.norm.ppf(lhs_samples)
        else:
            # Simple random sampling
            standard_normal = self.rng.randn(self.n_simulations, n_vars)

        # Apply correlation structure via Cholesky decomposition
        corr_matrix, ordered_names = self._build_correlation_matrix()

        try:
            L = cholesky(corr_matrix, lower=True)
            correlated_normal = standard_normal @ L.T
        except np.linalg.LinAlgError:
            print("Warning: Correlation matrix not positive definite. Using uncorrelated samples.")
            correlated_normal = standard_normal

        # Transform from standard normal to target distributions
        samples = {}
        for i, var_name in enumerate(ordered_names):
            variable = self.variables[var_name]

            # Get correlated uniform samples via CDF
            uniform_samples = stats.norm.cdf(correlated_normal[:, i])

            # Transform to target distribution
            if variable.distribution.dist_type == 'normal':
                samples[var_name] = stats.norm.ppf(
                    uniform_samples,
                    loc=variable.distribution.params['mean'],
                    scale=variable.distribution.params['std']
                )
            elif variable.distribution.dist_type == 'lognormal':
                samples[var_name] = stats.lognorm.ppf(
                    uniform_samples,
                    s=variable.distribution.params['std'],
                    scale=np.exp(variable.distribution.params['mean'])
                )
            elif variable.distribution.dist_type == 'triangular':
                # Scipy triangular uses c = (mode - min) / (max - min)
                min_val = variable.distribution.params['min']
                max_val = variable.distribution.params['max']
                mode_val = variable.distribution.params['mode']
                c = (mode_val - min_val) / (max_val - min_val)
                samples[var_name] = stats.triang.ppf(
                    uniform_samples,
                    c=c,
                    loc=min_val,
                    scale=max_val - min_val
                )
            elif variable.distribution.dist_type == 'beta':
                # Beta distribution scaled to [min, max]
                min_val = variable.distribution.params['min']
                max_val = variable.distribution.params['max']
                alpha = variable.distribution.params['alpha']
                beta_param = variable.distribution.params['beta']
                beta_samples = stats.beta.ppf(uniform_samples, alpha, beta_param)
                samples[var_name] = min_val + beta_samples * (max_val - min_val)
            elif variable.distribution.dist_type == 'uniform':
                min_val = variable.distribution.params['min']
                max_val = variable.distribution.params['max']
                samples[var_name] = min_val + uniform_samples * (max_val - min_val)
            elif variable.distribution.dist_type == 'truncnorm':
                # Truncated normal distribution
                mean = variable.distribution.params['mean']
                std = variable.distribution.params['std']
                min_val = variable.distribution.params['min']
                max_val = variable.distribution.params['max']
                a = (min_val - mean) / std
                b = (max_val - mean) / std
                samples[var_name] = stats.truncnorm.ppf(uniform_samples, a, b, loc=mean, scale=std)

        return pd.DataFrame(samples)

    def _latin_hypercube_sample(self, n_vars: int, n_samples: int) -> np.ndarray:
        """
        Generate Latin Hypercube samples

        Args:
            n_vars: Number of variables
            n_samples: Number of samples

        Returns:
            Array of shape (n_samples, n_vars) with uniform [0,1] samples
        """
        # Generate LHS samples
        samples = np.zeros((n_samples, n_vars))

        for i in range(n_vars):
            # Divide [0,1] into n_samples bins
            bins = np.arange(n_samples) / n_samples
            # Randomly sample within each bin
            samples[:, i] = bins + self.rng.rand(n_samples) / n_samples
            # Shuffle
            self.rng.shuffle(samples[:, i])

        return samples

    def run_simulation(
        self,
        include_projects: Optional[List[str]] = None,
        execution_factor_override: Optional[float] = None,
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Run Monte Carlo simulation

        Args:
            include_projects: List of projects to include (None = none)
            execution_factor_override: Override execution factor (None = use sampled)
            verbose: Print progress

        Returns:
            DataFrame with simulation results
        """
        if verbose:
            print(f"Running Monte Carlo simulation with {self.n_simulations:,} iterations...")
            print(f"Sampling method: {'Latin Hypercube' if self.use_lhs else 'Random'}")
            start_time = time.time()

        # Generate correlated input samples
        input_samples = self._generate_correlated_samples()
        self.simulation_inputs = input_samples

        # Parallel execution path
        if self.n_workers > 1:
            return self._run_simulation_parallel(
                input_samples, include_projects, execution_factor_override, verbose
            )

        # Run model for each sample (sequential)
        results = []

        # Use tqdm progress bar if available, otherwise fall back to print
        try:
            from tqdm import tqdm
            iterator = tqdm(
                range(self.n_simulations),
                desc="Monte Carlo Simulation",
                unit="sim",
                ncols=100,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
                disable=not verbose
            )
        except ImportError:
            iterator = range(self.n_simulations)
            if verbose:
                print("  (Install tqdm for progress bar: pip install tqdm)")

        for i in iterator:
            if not hasattr(iterator, 'set_description') and verbose and (i % 1000 == 0):
                print(f"  Completed {i:,} / {self.n_simulations:,} iterations...")

            # Build scenario from sampled inputs
            scenario, adj_factors = self._build_scenario_from_sample(
                input_samples.iloc[i],
                include_projects=include_projects,
                execution_factor_override=execution_factor_override
            )

            # Run model
            try:
                model = PriceVolumeModel(scenario)
                analysis = model.run_full_analysis()

                # Apply adjustment factors to EBITDA-based metrics
                margin_factor = adj_factors['margin_factor']
                capex_factor = adj_factors['capex_factor']

                # Adjusted EBITDA (margin factor affects profitability)
                adj_ebitda = analysis['consolidated']['Total_EBITDA'].mean() * margin_factor

                # Adjusted terminal EBITDA
                adj_terminal_ebitda = analysis['val_uss']['terminal_ebitda'] * margin_factor

                # Adjust EV for margin and capex intensity
                # Higher capex_factor → higher sustaining CapEx → lower FCF → lower EV
                # Sustaining CapEx PV is ~30% of base EV for integrated steel
                capex_drag = 1.0 - 0.30 * (capex_factor - 1.0)
                ev_adjustment = margin_factor * capex_drag
                adj_uss_ev = analysis['val_uss']['ev_blended'] * ev_adjustment
                adj_nippon_ev = analysis['val_nippon']['ev_blended'] * ev_adjustment

                # Convert to share price using equity bridge
                shares = 225.0  # Default shares outstanding
                equity_bridge = analysis['val_uss'].get('equity_bridge', -4000)  # Net debt adjustment
                adj_uss_share = max(0, adj_uss_ev + equity_bridge) / shares
                adj_nippon_share = max(0, adj_nippon_ev + equity_bridge) / shares

                # Extract key results (using correct key names from model output)
                # Get effective tariff from scenario for diagnostics
                eff_tariff = getattr(scenario.price_scenario, 'tariff_rate', 0.25)
                results.append({
                    'iteration': i,
                    'uss_enterprise_value': adj_uss_ev,
                    'uss_share_price': adj_uss_share,
                    'nippon_enterprise_value': adj_nippon_ev,
                    'nippon_share_price': adj_nippon_share,
                    'total_fcf_10y': analysis['consolidated']['FCF'].sum() * margin_factor,
                    'avg_ebitda': adj_ebitda,
                    'avg_ebitda_margin': analysis['consolidated']['EBITDA_Margin'].mean() * margin_factor,
                    'terminal_ebitda': adj_terminal_ebitda,
                    # Store adjustment factors for diagnostics
                    'margin_factor': margin_factor,
                    'capex_factor': capex_factor,
                    'effective_tariff_rate': eff_tariff,
                    'tariff_adjustment_hrc': calculate_tariff_adjustment(eff_tariff, 'hrc_us'),
                })
            except Exception as e:
                if verbose:
                    print(f"  Warning: Iteration {i} failed: {e}")
                # Record NaN for failed iterations (matching column structure above)
                results.append({
                    'iteration': i,
                    'uss_enterprise_value': np.nan,
                    'uss_share_price': np.nan,
                    'nippon_enterprise_value': np.nan,
                    'nippon_share_price': np.nan,
                    'total_fcf_10y': np.nan,
                    'avg_ebitda': np.nan,
                    'avg_ebitda_margin': np.nan,
                    'terminal_ebitda': np.nan,
                    'margin_factor': np.nan,
                    'capex_factor': np.nan,
                    'effective_tariff_rate': np.nan,
                    'tariff_adjustment_hrc': np.nan,
                })

        self.simulation_results = pd.DataFrame(results)

        # Remove failed iterations
        n_failed = self.simulation_results['uss_share_price'].isna().sum()
        if n_failed > 0:
            print(f"  Warning: {n_failed} iterations failed and were removed")
            self.simulation_results = self.simulation_results.dropna()

        if verbose:
            elapsed = time.time() - start_time
            print(f"\nSimulation complete! Elapsed time: {elapsed:.1f} seconds")
            print(f"Average time per iteration: {elapsed/self.n_simulations*1000:.1f} ms")

        return self.simulation_results

    def _run_simulation_parallel(
        self,
        input_samples: pd.DataFrame,
        include_projects,
        execution_factor_override,
        verbose: bool
    ) -> pd.DataFrame:
        """Run simulation distributed across multiple worker processes."""
        start_time = time.time()
        if verbose:
            print(f"  Distributing across {self.n_workers} workers...")

        # More chunks than workers gives better progress granularity
        n_chunks = min(self.n_workers * 4, self.n_simulations)
        chunks = np.array_split(input_samples, n_chunks)

        batch_args = [
            (chunk, self.base_scenario, include_projects, execution_factor_override)
            for chunk in chunks
        ]

        results = []
        completed = 0

        # Use tqdm progress bar for parallel execution
        try:
            from tqdm import tqdm
            pbar = tqdm(
                total=self.n_simulations,
                desc="Parallel MC Simulation",
                unit="sim",
                ncols=100,
                bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
                disable=not verbose
            )
        except ImportError:
            pbar = None

        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            futures = {
                executor.submit(_simulate_batch, args): i
                for i, args in enumerate(batch_args)
            }
            for future in as_completed(futures):
                batch_results = future.result()
                results.extend(batch_results)
                completed += 1

                if pbar:
                    pbar.update(len(batch_results))
                elif verbose:
                    print(f"  Chunk {completed}/{n_chunks} done "
                          f"({len(results):,}/{self.n_simulations:,} iterations)")

        if pbar:
            pbar.close()

        self.simulation_results = pd.DataFrame(results)

        # Remove failed iterations
        n_failed = self.simulation_results['uss_share_price'].isna().sum()
        if n_failed > 0:
            print(f"  Warning: {n_failed} iterations failed and were removed")
            self.simulation_results = self.simulation_results.dropna()

        if verbose:
            elapsed = time.time() - start_time
            print(f"\nSimulation complete! Elapsed time: {elapsed:.1f} seconds")
            print(f"Average time per iteration: {elapsed/self.n_simulations*1000:.1f} ms")

        return self.simulation_results

    def _build_scenario_from_sample(
        self,
        sample: pd.Series,
        include_projects: Optional[List[str]] = None,
        execution_factor_override: Optional[float] = None
    ) -> Tuple[ModelScenario, Dict[str, float]]:
        """Build ModelScenario from sampled inputs

        Returns:
            Tuple of (ModelScenario, adjustment_factors dict)
            adjustment_factors contains multipliers to apply to results:
            - margin_factor: multiply EBITDA
            - working_capital_factor: multiply working capital changes
            - capex_factor: multiply CapEx
        """

        # Get annual price growth from sample or use default
        annual_price_growth = sample.get('annual_price_growth', 1.5) / 100

        # Get HRC EU factor from sample or default to US price
        hrc_eu_factor = sample.get('hrc_eu_factor', sample['hrc_price_factor'])

        # Tariff blending: continuous expected tariff rate
        tariff_prob = sample.get('tariff_probability', 0.80)
        tariff_alt = sample.get('tariff_rate_if_changed', 0.10)
        effective_tariff = tariff_prob * 0.25 + (1 - tariff_prob) * tariff_alt

        # Price scenario
        price_scenario = SteelPriceScenario(
            name="Monte Carlo Sample",
            description="Sampled from distributions",
            hrc_us_factor=sample['hrc_price_factor'],
            crc_us_factor=sample['crc_price_factor'],
            coated_us_factor=sample['coated_price_factor'],
            hrc_eu_factor=hrc_eu_factor,
            octg_factor=sample['octg_price_factor'],
            annual_price_growth=annual_price_growth,
            tariff_rate=effective_tariff,
        )

        # Get USSE volume from sample or use default
        usse_volume = sample.get('usse_volume', 1.0)

        # Volume scenario
        volume_scenario = VolumeScenario(
            name="Monte Carlo Sample",
            description="Sampled from distributions",
            flat_rolled_volume_factor=sample['flat_rolled_volume'],
            mini_mill_volume_factor=sample['mini_mill_volume'],
            usse_volume_factor=usse_volume,
            tubular_volume_factor=sample['tubular_volume'],
            flat_rolled_growth_adj=0.0,
            mini_mill_growth_adj=0.0,
            usse_growth_adj=0.0,
            tubular_growth_adj=0.0,
        )

        # Execution factor
        if execution_factor_override is not None:
            execution_factor = execution_factor_override
        elif 'gary_works_execution' in sample:
            # Average of project execution factors
            execution_factor = np.mean([
                sample['gary_works_execution'],
                sample['mon_valley_execution'],
            ])
        else:
            execution_factor = 0.75

        # Get sampled rate parameters (with fallbacks to base scenario)
        base_us_10yr = self.base_scenario.us_10yr if self.base_scenario else 0.0425
        base_japan_10yr = self.base_scenario.japan_10yr if self.base_scenario else 0.0075
        base_erp = self.base_scenario.nippon_equity_risk_premium if self.base_scenario else 0.0475
        base_credit_spread = self.base_scenario.nippon_credit_spread if self.base_scenario else 0.0075
        base_debt_ratio = self.base_scenario.nippon_debt_ratio if self.base_scenario else 0.35
        base_tax_rate = self.base_scenario.nippon_tax_rate if self.base_scenario else 0.30

        # Apply sampled rates (convert from % to decimal)
        us_10yr = sample.get('us_10yr', base_us_10yr * 100) / 100
        japan_10yr = sample.get('japan_rf_rate', base_japan_10yr * 100) / 100
        nippon_erp = sample.get('nippon_erp', base_erp * 100) / 100

        # Handle include_projects - use base scenario projects if not specified
        if include_projects is None:
            if self.base_scenario:
                include_projects = list(self.base_scenario.include_projects)
            else:
                include_projects = []

        scenario = ModelScenario(
            name="Monte Carlo Sample",
            scenario_type=ScenarioType.CUSTOM,
            description="Sampled from probability distributions",
            price_scenario=price_scenario,
            volume_scenario=volume_scenario,
            uss_wacc=sample['uss_wacc'] / 100,  # Convert from % to decimal
            terminal_growth=sample['terminal_growth'] / 100,
            exit_multiple=sample['exit_multiple'],
            us_10yr=us_10yr,
            japan_10yr=japan_10yr,
            nippon_equity_risk_premium=nippon_erp,
            nippon_credit_spread=base_credit_spread,
            nippon_debt_ratio=base_debt_ratio,
            nippon_tax_rate=base_tax_rate,
            include_projects=include_projects,
            synergies=None,
        )

        # Collect adjustment factors for post-hoc application
        # These affect the valuation calculation directly
        adjustment_factors = {
            'margin_factor': sample.get('flat_rolled_margin_factor', 1.0),
            'working_capital_factor': sample.get('working_capital_efficiency', 1.0),
            'capex_factor': sample.get('capex_intensity_factor', 1.0),
        }

        return scenario, adjustment_factors

    def calculate_statistics(self) -> Dict:
        """Calculate summary statistics from simulation results"""
        if self.simulation_results is None:
            raise ValueError("No simulation results. Run run_simulation() first.")

        results = self.simulation_results

        # Focus on Nippon view (IRP-adjusted WACC)
        values = results['nippon_share_price'].values

        # Calculate distribution shape metrics first (before shadowing scipy.stats)
        skewness = stats.skew(values)
        kurtosis = stats.kurtosis(values)

        summary = {
            # Central tendency
            'mean': np.mean(values),
            'median': np.median(values),
            'mode': self._estimate_mode(values),
            'std': np.std(values),
            'cv': np.std(values) / np.mean(values),  # Coefficient of variation

            # Percentiles
            'p01': np.percentile(values, 1),
            'p05': np.percentile(values, 5),
            'p10': np.percentile(values, 10),
            'p25': np.percentile(values, 25),
            'p50': np.percentile(values, 50),
            'p75': np.percentile(values, 75),
            'p90': np.percentile(values, 90),
            'p95': np.percentile(values, 95),
            'p99': np.percentile(values, 99),

            # Range
            'min': np.min(values),
            'max': np.max(values),
            'range': np.max(values) - np.min(values),

            # Risk metrics
            'var_95': np.percentile(values, 5),  # 95% VaR (5th percentile)
            'var_99': np.percentile(values, 1),  # 99% VaR (1st percentile)
            'cvar_95': np.mean(values[values <= np.percentile(values, 5)]),  # CVaR
            'cvar_99': np.mean(values[values <= np.percentile(values, 1)]),

            # Probability metrics
            'prob_below_55': np.mean(values < 55),
            'prob_below_50': np.mean(values < 50),
            'prob_below_40': np.mean(values < 40),
            'prob_above_75': np.mean(values > 75),
            'prob_above_100': np.mean(values > 100),

            # Distribution shape
            'skewness': skewness,
            'kurtosis': kurtosis,

            # Confidence intervals
            'ci_80_lower': np.percentile(values, 10),
            'ci_80_upper': np.percentile(values, 90),
            'ci_90_lower': np.percentile(values, 5),
            'ci_90_upper': np.percentile(values, 95),
            'ci_95_lower': np.percentile(values, 2.5),
            'ci_95_upper': np.percentile(values, 97.5),
        }

        self.summary_stats = summary
        return summary

    def _estimate_mode(self, values: np.ndarray, n_bins: int = 50) -> float:
        """Estimate mode using histogram"""
        hist, bin_edges = np.histogram(values, bins=n_bins)
        max_bin = np.argmax(hist)
        return (bin_edges[max_bin] + bin_edges[max_bin + 1]) / 2

    def print_summary(self):
        """Print formatted summary of simulation results"""
        if self.summary_stats is None:
            self.calculate_statistics()

        s = self.summary_stats
        results = self.simulation_results

        # Compute USS standalone stats
        uss_vals = results['uss_share_price'].values
        nip_vals = results['nippon_share_price'].values
        premium = nip_vals - uss_vals

        print("\n" + "=" * 80)
        print("MONTE CARLO SIMULATION SUMMARY")
        print("USS / Nippon Steel Merger - Dual-Perspective Valuation")
        print("=" * 80)

        print(f"\nSimulations: {len(results):,}")
        print(f"Sampling: {'Latin Hypercube' if self.use_lhs else 'Random'}")

        print("\n" + "-" * 80)
        print("DUAL-PERSPECTIVE COMPARISON")
        print("-" * 80)
        header = f"  {'Metric':<24}{'USS Standalone':>15}{'Nippon View':>15}{'Premium':>12}"
        print(header)
        print(f"  {'─' * 66}")
        print(f"  {'Mean':<24}${np.mean(uss_vals):>13.2f}  ${np.mean(nip_vals):>13.2f}  ${np.mean(premium):>10.2f}")
        print(f"  {'Median':<24}${np.median(uss_vals):>13.2f}  ${np.median(nip_vals):>13.2f}  ${np.median(premium):>10.2f}")
        print(f"  {'Std Dev':<24}${np.std(uss_vals):>13.2f}  ${np.std(nip_vals):>13.2f}  ${np.std(premium):>10.2f}")
        print(f"  {'P5':<24}${np.percentile(uss_vals,5):>13.2f}  ${np.percentile(nip_vals,5):>13.2f}")
        print(f"  {'P25':<24}${np.percentile(uss_vals,25):>13.2f}  ${np.percentile(nip_vals,25):>13.2f}")
        print(f"  {'P50':<24}${np.percentile(uss_vals,50):>13.2f}  ${np.percentile(nip_vals,50):>13.2f}")
        print(f"  {'P75':<24}${np.percentile(uss_vals,75):>13.2f}  ${np.percentile(nip_vals,75):>13.2f}")
        print(f"  {'P95':<24}${np.percentile(uss_vals,95):>13.2f}  ${np.percentile(nip_vals,95):>13.2f}")
        print(f"  {'─' * 66}")
        print(f"  {'P(< $55)':<24}{np.mean(uss_vals<55):>14.1%}  {np.mean(nip_vals<55):>14.1%}")
        print(f"  {'P(> $75)':<24}{np.mean(uss_vals>75):>14.1%}  {np.mean(nip_vals>75):>14.1%}")
        print(f"  {'P(> $100)':<24}{np.mean(uss_vals>100):>14.1%}  {np.mean(nip_vals>100):>14.1%}")

        nip_mean = np.mean(nip_vals)
        prem_pct = np.mean(premium) / nip_mean * 100 if nip_mean > 0 else 0
        print(f"\n  Synergy Premium: ${np.mean(premium):.2f}/share ({prem_pct:.1f}% of Nippon value)")

        print("\n" + "-" * 80)
        print("NIPPON PERSPECTIVE - DETAILED STATISTICS")
        print("-" * 80)
        print(f"  Mean:                ${s['mean']:.2f} per share")
        print(f"  Median:              ${s['median']:.2f} per share")
        print(f"  Mode (estimated):    ${s['mode']:.2f} per share")
        print(f"  Std Deviation:       ${s['std']:.2f}")
        print(f"  Coefficient of Var:  {s['cv']:.2%}")

        print("\n" + "-" * 80)
        print("CONFIDENCE INTERVALS (Nippon View)")
        print("-" * 80)
        print(f"  80% CI (P10-P90):    ${s['ci_80_lower']:.2f} - ${s['ci_80_upper']:.2f}")
        print(f"  90% CI (P5-P95):     ${s['ci_90_lower']:.2f} - ${s['ci_90_upper']:.2f}")
        print(f"  95% CI (P2.5-P97.5): ${s['ci_95_lower']:.2f} - ${s['ci_95_upper']:.2f}")

        print("\n" + "-" * 80)
        print("RISK METRICS (Nippon View)")
        print("-" * 80)
        print(f"  VaR (95%):           ${s['var_95']:.2f}")
        print(f"  VaR (99%):           ${s['var_99']:.2f}")
        print(f"  CVaR (95%):          ${s['cvar_95']:.2f}")
        print(f"  CVaR (99%):          ${s['cvar_99']:.2f}")

        print("\n" + "-" * 80)
        print("DISTRIBUTION SHAPE")
        print("-" * 80)
        print(f"  Skewness:            {s['skewness']:.2f}")
        if s['skewness'] > 0.5:
            print(f"                       (Positive skew: long right tail, upside potential)")
        elif s['skewness'] < -0.5:
            print(f"                       (Negative skew: long left tail, downside risk)")
        else:
            print(f"                       (Approximately symmetric)")

        print(f"  Kurtosis:            {s['kurtosis']:.2f}")
        if s['kurtosis'] > 1:
            print(f"                       (Fat tails: higher probability of extreme events)")
        elif s['kurtosis'] < -1:
            print(f"                       (Thin tails: low probability of extreme events)")
        else:
            print(f"                       (Normal-like tails)")

        print("\n" + "=" * 80)
        print("INTERPRETATION")
        print("=" * 80)

        if s['prob_below_55'] < 0.20:
            print(f"\nThe $55 offer looks CONSERVATIVE:")
            print(f"  - Only {s['prob_below_55']:.1%} chance Nippon value is below offer")
            print(f"  - USS standalone mean: ${np.mean(uss_vals):.2f} | Nippon mean: ${s['mean']:.2f}")
            print(f"  - Synergy premium: ${np.mean(premium):.2f}/share")
            print(f"  - Significant upside potential ({s['prob_above_75']:.0%} chance of >$75)")
        elif s['prob_below_55'] < 0.40:
            print(f"\nThe $55 offer is REASONABLE:")
            print(f"  - {s['prob_below_55']:.1%} chance Nippon value is below offer")
            print(f"  - USS standalone mean: ${np.mean(uss_vals):.2f} | Nippon mean: ${s['mean']:.2f}")
            print(f"  - Some upside potential ({s['prob_above_75']:.0%} chance of >$75)")
        else:
            print(f"\nThe $55 offer looks GENEROUS:")
            print(f"  - {s['prob_below_55']:.1%} chance Nippon value is below offer")
            print(f"  - USS standalone mean: ${np.mean(uss_vals):.2f}")
            print(f"  - Significant downside protection")

        print("\n")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Run basic Monte Carlo simulation
    mc = MonteCarloEngine(n_simulations=1000, use_lhs=True)

    # Run simulation
    results = mc.run_simulation(verbose=True)

    # Print summary
    mc.print_summary()

    # Save results
    output_dir = Path(__file__).parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)

    results.to_csv(output_dir / 'monte_carlo_results.csv', index=False)
    mc.simulation_inputs.to_csv(output_dir / 'monte_carlo_inputs.csv', index=False)

    print(f"\nResults saved to {output_dir}")
