#!/usr/bin/env python3
"""
Monte Carlo Simulation Engine for USS / Nippon Steel Merger Model
==================================================================

Implements probabilistic valuation using Monte Carlo simulation with:
- Latin Hypercube Sampling for efficient coverage
- Correlation modeling via Cholesky decomposition
- Risk metrics (VaR, CVaR, percentiles)
- Integration with existing PriceVolumeModel

Usage:
    from monte_carlo.monte_carlo_engine import MonteCarloEngine

    mc = MonteCarloEngine(n_simulations=10000)
    results = mc.run_simulation()
    mc.print_summary()
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from scipy import stats
from scipy.linalg import cholesky
import time
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from price_volume_model import (
    PriceVolumeModel, ModelScenario, ScenarioType,
    SteelPriceScenario, VolumeScenario, get_scenario_presets,
    BENCHMARK_PRICES_2023
)


# =============================================================================
# DISTRIBUTION DEFINITIONS
# =============================================================================

@dataclass
class Distribution:
    """Base class for probability distributions"""
    name: str
    dist_type: str  # 'normal', 'lognormal', 'triangular', 'beta', 'uniform'
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
    """

    def __init__(
        self,
        n_simulations: int = 10000,
        random_seed: int = 42,
        use_lhs: bool = True,
        base_scenario: Optional[ModelScenario] = None
    ):
        """
        Initialize Monte Carlo engine

        Args:
            n_simulations: Number of Monte Carlo iterations
            random_seed: Random seed for reproducibility
            use_lhs: Use Latin Hypercube Sampling (recommended)
            base_scenario: Base scenario to modify (default: Base Case)
        """
        self.n_simulations = n_simulations
        self.random_seed = random_seed
        self.use_lhs = use_lhs
        self.rng = np.random.RandomState(random_seed)

        # Base scenario
        if base_scenario is None:
            self.base_scenario = get_scenario_presets()[ScenarioType.BASE_CASE]
        else:
            self.base_scenario = base_scenario

        # Define input variables and distributions
        self.variables = self._define_input_variables()

        # Results storage
        self.simulation_inputs = None
        self.simulation_results = None
        self.summary_stats = None

    def _define_input_variables(self) -> Dict[str, InputVariable]:
        """
        Define all uncertain input variables with their distributions

        Calibrated to USS historical data and industry benchmarks
        """
        variables = {}

        # =====================================================================
        # STEEL PRICES - Most critical driver
        # =====================================================================

        variables['hrc_price_factor'] = InputVariable(
            name='hrc_price_factor',
            description='HRC Steel Price Factor (vs 2023 baseline)',
            distribution=Distribution(
                name='HRC Price Factor',
                dist_type='lognormal',
                params={
                    'mean': np.log(0.95),  # Log-space mean for 95% factor
                    'std': 0.18,  # ~18% volatility in log-space
                }
            ),
            base_value=0.95,
            correlations={
                'crc_price_factor': 0.95,
                'coated_price_factor': 0.93,
                'octg_price_factor': 0.65,
                'flat_rolled_volume': 0.40,
                'uss_wacc': -0.20,
            }
        )

        variables['crc_price_factor'] = InputVariable(
            name='crc_price_factor',
            description='CRC Steel Price Factor',
            distribution=Distribution(
                name='CRC Price Factor',
                dist_type='lognormal',
                params={
                    'mean': np.log(0.95),
                    'std': 0.16,  # Slightly lower volatility than HRC (value-added product)
                }
            ),
            base_value=0.95,
            correlations={
                'hrc_price_factor': 0.95,  # High correlation with HRC
                'coated_price_factor': 0.92,  # High correlation with other value-added
                'flat_rolled_volume': 0.35,  # Moderate demand linkage
            }
        )

        variables['coated_price_factor'] = InputVariable(
            name='coated_price_factor',
            description='Coated Steel Price Factor',
            distribution=Distribution(
                name='Coated Price Factor',
                dist_type='lognormal',
                params={
                    'mean': np.log(0.95),
                    'std': 0.15,  # Lower volatility (more stable premium product)
                }
            ),
            base_value=0.95,
            correlations={
                'hrc_price_factor': 0.93,  # High correlation with HRC
                'crc_price_factor': 0.92,  # High correlation with CRC
                'flat_rolled_volume': 0.30,  # Moderate demand linkage
            }
        )

        variables['octg_price_factor'] = InputVariable(
            name='octg_price_factor',
            description='OCTG Price Factor',
            distribution=Distribution(
                name='OCTG Price Factor',
                dist_type='lognormal',
                params={
                    'mean': np.log(0.95),
                    'std': 0.22,  # Higher volatility for tubular products
                }
            ),
            base_value=0.95,
            correlations={
                'tubular_volume': 0.75,  # Strong oil/gas linkage
            }
        )

        # =====================================================================
        # VOLUMES - Moderate impact
        # =====================================================================

        variables['flat_rolled_volume'] = InputVariable(
            name='flat_rolled_volume',
            description='Flat-Rolled Volume Factor',
            distribution=Distribution(
                name='Flat-Rolled Volume',
                dist_type='normal',
                params={
                    'mean': 1.00,
                    'std': 0.08,
                }
            ),
            base_value=1.00,
        )

        variables['mini_mill_volume'] = InputVariable(
            name='mini_mill_volume',
            description='Mini Mill Volume Factor',
            distribution=Distribution(
                name='Mini Mill Volume',
                dist_type='normal',
                params={
                    'mean': 1.00,
                    'std': 0.06,
                }
            ),
            base_value=1.00,
        )

        variables['tubular_volume'] = InputVariable(
            name='tubular_volume',
            description='Tubular Volume Factor',
            distribution=Distribution(
                name='Tubular Volume',
                dist_type='triangular',
                params={
                    'min': 0.70,
                    'mode': 1.00,
                    'max': 1.25,
                }
            ),
            base_value=1.00,
        )

        # =====================================================================
        # DISCOUNT RATE - High impact
        # =====================================================================

        variables['uss_wacc'] = InputVariable(
            name='uss_wacc',
            description='USS WACC (%)',
            distribution=Distribution(
                name='USS WACC',
                dist_type='normal',
                params={
                    'mean': 10.9,
                    'std': 0.8,
                }
            ),
            base_value=10.9,
        )

        variables['japan_rf_rate'] = InputVariable(
            name='japan_rf_rate',
            description='Japan Risk-Free Rate (%)',
            distribution=Distribution(
                name='Japan RF Rate',
                dist_type='normal',
                params={
                    'mean': 0.75,
                    'std': 0.30,
                }
            ),
            base_value=0.75,
            correlations={
                'uss_wacc': -0.30,  # Flight to safety
            }
        )

        # =====================================================================
        # TERMINAL VALUE ASSUMPTIONS
        # =====================================================================

        variables['terminal_growth'] = InputVariable(
            name='terminal_growth',
            description='Terminal Growth Rate (%)',
            distribution=Distribution(
                name='Terminal Growth',
                dist_type='triangular',
                params={
                    'min': -0.5,
                    'mode': 1.0,
                    'max': 2.5,
                }
            ),
            base_value=1.0,
        )

        variables['exit_multiple'] = InputVariable(
            name='exit_multiple',
            description='Exit EV/EBITDA Multiple',
            distribution=Distribution(
                name='Exit Multiple',
                dist_type='triangular',
                params={
                    'min': 3.5,
                    'mode': 4.5,
                    'max': 6.5,
                }
            ),
            base_value=4.5,
        )

        # =====================================================================
        # EXECUTION RISK (for NSA Mandated CapEx scenario)
        # =====================================================================

        variables['gary_works_execution'] = InputVariable(
            name='gary_works_execution',
            description='Gary Works BF Execution Success',
            distribution=Distribution(
                name='Gary Works Success',
                dist_type='beta',
                params={
                    'alpha': 8,
                    'beta': 3,
                    'min': 0.40,
                    'max': 1.00,
                }
            ),
            base_value=0.75,
        )

        variables['mon_valley_execution'] = InputVariable(
            name='mon_valley_execution',
            description='Mon Valley HSM Execution Success',
            distribution=Distribution(
                name='Mon Valley Success',
                dist_type='beta',
                params={
                    'alpha': 9,
                    'beta': 2,
                    'min': 0.50,
                    'max': 1.00,
                }
            ),
            base_value=0.80,
            correlations={
                'gary_works_execution': 0.60,  # Common management capability
            }
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

        # Run model for each sample
        results = []

        for i in range(self.n_simulations):
            if verbose and (i % 1000 == 0):
                print(f"  Completed {i:,} / {self.n_simulations:,} iterations...")

            # Build scenario from sampled inputs
            scenario = self._build_scenario_from_sample(
                input_samples.iloc[i],
                include_projects=include_projects,
                execution_factor_override=execution_factor_override
            )

            # Run model
            try:
                model = PriceVolumeModel(scenario)
                analysis = model.run_full_analysis()

                # Extract key results (using correct key names from model output)
                results.append({
                    'iteration': i,
                    'uss_enterprise_value': analysis['val_uss']['ev_blended'],
                    'uss_share_price': analysis['val_uss']['share_price'],
                    'nippon_enterprise_value': analysis['val_nippon']['ev_blended'],
                    'nippon_share_price': analysis['val_nippon']['share_price'],
                    'total_fcf_10y': analysis['consolidated']['FCF'].sum(),
                    'avg_ebitda': analysis['consolidated']['Total_EBITDA'].mean(),
                    'avg_ebitda_margin': analysis['consolidated']['EBITDA_Margin'].mean(),
                    'terminal_ebitda': analysis['val_uss']['terminal_ebitda'],
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

    def _build_scenario_from_sample(
        self,
        sample: pd.Series,
        include_projects: Optional[List[str]] = None,
        execution_factor_override: Optional[float] = None
    ) -> ModelScenario:
        """Build ModelScenario from sampled inputs"""

        # Price scenario
        price_scenario = SteelPriceScenario(
            name="Monte Carlo Sample",
            description="Sampled from distributions",
            hrc_us_factor=sample['hrc_price_factor'],
            crc_us_factor=sample['crc_price_factor'],
            coated_us_factor=sample['coated_price_factor'],
            hrc_eu_factor=sample['hrc_price_factor'],  # Assume same as US for simplicity
            octg_factor=sample['octg_price_factor'],
            annual_price_growth=0.015,  # Could also sample this
        )

        # Volume scenario
        volume_scenario = VolumeScenario(
            name="Monte Carlo Sample",
            description="Sampled from distributions",
            flat_rolled_volume_factor=sample['flat_rolled_volume'],
            mini_mill_volume_factor=sample['mini_mill_volume'],
            usse_volume_factor=1.00,  # Could add sampling
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

        # Build scenario with all required IRP parameters
        # Use base scenario IRP values if available, otherwise use defaults
        base_us_10yr = self.base_scenario.us_10yr if self.base_scenario else 0.0425
        base_japan_10yr = self.base_scenario.japan_10yr if self.base_scenario else 0.0075
        base_erp = self.base_scenario.nippon_equity_risk_premium if self.base_scenario else 0.0475
        base_credit_spread = self.base_scenario.nippon_credit_spread if self.base_scenario else 0.0075
        base_debt_ratio = self.base_scenario.nippon_debt_ratio if self.base_scenario else 0.35
        base_tax_rate = self.base_scenario.nippon_tax_rate if self.base_scenario else 0.30

        # Apply Japan rate sample if available
        japan_10yr = sample.get('japan_risk_free', base_japan_10yr * 100) / 100

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
            us_10yr=base_us_10yr,
            japan_10yr=japan_10yr,
            nippon_equity_risk_premium=base_erp,
            nippon_credit_spread=base_credit_spread,
            nippon_debt_ratio=base_debt_ratio,
            nippon_tax_rate=base_tax_rate,
            include_projects=include_projects,
            synergies=None,  # Could add synergy sampling
        )

        return scenario

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

        print("\n" + "=" * 80)
        print("MONTE CARLO SIMULATION SUMMARY")
        print("USS / Nippon Steel Merger - Valuation Distribution")
        print("=" * 80)

        print(f"\nSimulations: {len(self.simulation_results):,}")
        print(f"Sampling: {'Latin Hypercube' if self.use_lhs else 'Random'}")

        print("\n" + "-" * 80)
        print("CENTRAL TENDENCY")
        print("-" * 80)
        print(f"  Mean:                ${s['mean']:.2f} per share")
        print(f"  Median:              ${s['median']:.2f} per share")
        print(f"  Mode (estimated):    ${s['mode']:.2f} per share")
        print(f"  Std Deviation:       ${s['std']:.2f}")
        print(f"  Coefficient of Var:  {s['cv']:.2%}")

        print("\n" + "-" * 80)
        print("PERCENTILES")
        print("-" * 80)
        print(f"  P1  (1st percentile):   ${s['p01']:.2f}")
        print(f"  P5  (5th percentile):   ${s['p05']:.2f}")
        print(f"  P10 (10th percentile):  ${s['p10']:.2f}")
        print(f"  P25 (25th percentile):  ${s['p25']:.2f}")
        print(f"  P50 (Median):           ${s['p50']:.2f}")
        print(f"  P75 (75th percentile):  ${s['p75']:.2f}")
        print(f"  P90 (90th percentile):  ${s['p90']:.2f}")
        print(f"  P95 (95th percentile):  ${s['p95']:.2f}")
        print(f"  P99 (99th percentile):  ${s['p99']:.2f}")

        print("\n" + "-" * 80)
        print("CONFIDENCE INTERVALS")
        print("-" * 80)
        print(f"  80% CI (P10-P90):    ${s['ci_80_lower']:.2f} - ${s['ci_80_upper']:.2f}")
        print(f"  90% CI (P5-P95):     ${s['ci_90_lower']:.2f} - ${s['ci_90_upper']:.2f}")
        print(f"  95% CI (P2.5-P97.5): ${s['ci_95_lower']:.2f} - ${s['ci_95_upper']:.2f}")

        print("\n" + "-" * 80)
        print("RISK METRICS")
        print("-" * 80)
        print(f"  VaR (95%):           ${s['var_95']:.2f}")
        print(f"  VaR (99%):           ${s['var_99']:.2f}")
        print(f"  CVaR (95%):          ${s['cvar_95']:.2f}")
        print(f"  CVaR (99%):          ${s['cvar_99']:.2f}")
        print(f"\n  (VaR = Value at Risk: max loss at confidence level)")
        print(f"  (CVaR = Expected loss given we're in the worst X% of cases)")

        print("\n" + "-" * 80)
        print("PROBABILITY METRICS")
        print("-" * 80)
        print(f"  P(Value < $40):      {s['prob_below_40']:.1%}")
        print(f"  P(Value < $50):      {s['prob_below_50']:.1%}")
        print(f"  P(Value < $55):      {s['prob_below_55']:.1%}  ← vs Nippon $55 offer")
        print(f"  P(Value > $75):      {s['prob_above_75']:.1%}")
        print(f"  P(Value > $100):     {s['prob_above_100']:.1%}")

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
            print(f"  - Only {s['prob_below_55']:.1%} chance value is below offer")
            print(f"  - Expected value is ${s['mean']:.2f} (${s['mean']-55:.2f} above offer)")
            print(f"  - Significant upside potential ({s['prob_above_75']:.0%} chance of >$75)")
        elif s['prob_below_55'] < 0.40:
            print(f"\nThe $55 offer is REASONABLE:")
            print(f"  - {s['prob_below_55']:.1%} chance value is below offer")
            print(f"  - Expected value is ${s['mean']:.2f}")
            print(f"  - Some upside potential ({s['prob_above_75']:.0%} chance of >$75)")
        else:
            print(f"\nThe $55 offer looks GENEROUS:")
            print(f"  - {s['prob_below_55']:.1%} chance value is below offer")
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
