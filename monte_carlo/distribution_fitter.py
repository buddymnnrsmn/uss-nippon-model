#!/usr/bin/env python3
"""
Distribution Fitting Module for Monte Carlo Simulation
========================================================

Statistical engine for fitting probability distributions to historical data.
Supports multiple distribution types with goodness-of-fit testing and
automated selection based on AIC/BIC criteria.

Usage:
    from monte_carlo.distribution_fitter import DistributionFitter, fit_distribution

    fitter = DistributionFitter()
    result = fitter.fit_distribution(data, 'lognormal')
    best = fitter.select_best_distribution(data, ['normal', 'lognormal', 'triangular'])
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Union
from scipy import stats
from scipy.optimize import minimize_scalar
import warnings


# =============================================================================
# FIT RESULT DATACLASS
# =============================================================================

@dataclass
class FitResult:
    """
    Result of fitting a distribution to data

    Attributes:
        distribution_type: Type of distribution ('normal', 'lognormal', etc.)
        parameters: Distribution parameters (varies by type)
        n_observations: Number of data points used for fitting
        goodness_of_fit: Dict with KS statistic, p-value, AIC, BIC
        rationale: Human-readable explanation of the fit
        data_source: Optional source file path
        warnings: List of any warnings generated during fitting
    """
    distribution_type: str
    parameters: Dict[str, float]
    n_observations: int
    goodness_of_fit: Dict[str, float]
    rationale: str
    data_source: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'distribution_type': self.distribution_type,
            'parameters': self.parameters,
            'n_observations': self.n_observations,
            'goodness_of_fit': self.goodness_of_fit,
            'rationale': self.rationale,
            'data_source': self.data_source,
            'warnings': self.warnings
        }


# =============================================================================
# DISTRIBUTION FITTER CLASS
# =============================================================================

class DistributionFitter:
    """
    Statistical engine for fitting distributions to historical data

    Supports:
    - Normal distribution
    - Lognormal distribution
    - Triangular distribution
    - Beta distribution
    - Uniform distribution
    - Truncated normal distribution
    """

    # Distribution selection criteria weights
    SELECTION_WEIGHTS = {
        'aic_bic': 0.40,      # Statistical fit quality
        'domain_logic': 0.30,  # E.g., prices must be non-negative
        'ks_pvalue': 0.20,     # Distribution shape match
        'parsimony': 0.10      # Prefer simpler distributions
    }

    # Parsimony scores (lower = simpler, preferred)
    PARSIMONY_SCORES = {
        'uniform': 1,
        'triangular': 2,
        'normal': 2,
        'lognormal': 2,
        'truncnorm': 3,
        'beta': 3
    }

    def __init__(self, random_seed: int = 42):
        """Initialize fitter with optional random seed"""
        self.rng = np.random.RandomState(random_seed)

    def fit_distribution(
        self,
        data: np.ndarray,
        dist_type: str,
        bounds: Optional[Tuple[float, float]] = None
    ) -> FitResult:
        """
        Fit a specific distribution type to data

        Args:
            data: Array of historical observations
            dist_type: Distribution type ('normal', 'lognormal', 'triangular', 'beta', 'uniform', 'truncnorm')
            bounds: Optional (min, max) bounds for bounded distributions

        Returns:
            FitResult with fitted parameters and statistics
        """
        data = np.asarray(data).flatten()
        data = data[~np.isnan(data)]  # Remove NaN values
        n = len(data)

        if n < 10:
            raise ValueError(f"Need at least 10 observations, got {n}")

        warnings_list = []

        if dist_type == 'normal':
            params, gof, rationale = self._fit_normal(data)
        elif dist_type == 'lognormal':
            params, gof, rationale, warnings_list = self._fit_lognormal(data)
        elif dist_type == 'triangular':
            params, gof, rationale = self._fit_triangular(data)
        elif dist_type == 'beta':
            params, gof, rationale = self._fit_beta(data, bounds)
        elif dist_type == 'uniform':
            params, gof, rationale = self._fit_uniform(data)
        elif dist_type == 'truncnorm':
            params, gof, rationale = self._fit_truncnorm(data, bounds)
        else:
            raise ValueError(f"Unknown distribution type: {dist_type}")

        return FitResult(
            distribution_type=dist_type,
            parameters=params,
            n_observations=n,
            goodness_of_fit=gof,
            rationale=rationale,
            warnings=warnings_list
        )

    def _fit_normal(self, data: np.ndarray) -> Tuple[dict, dict, str]:
        """Fit normal distribution using MLE"""
        mean = np.mean(data)
        std = np.std(data, ddof=1)  # Sample standard deviation

        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = stats.kstest(data, 'norm', args=(mean, std))

        # Log-likelihood, AIC, BIC
        n = len(data)
        k = 2  # Number of parameters
        ll = np.sum(stats.norm.logpdf(data, mean, std))
        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        params = {'mean': float(mean), 'std': float(std)}
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        rationale = f"Normal fit: mean={mean:.4f}, std={std:.4f}. KS p-value={ks_pvalue:.3f}"
        if ks_pvalue < 0.05:
            rationale += " (Warning: data may not be normally distributed)"

        return params, gof, rationale

    def _fit_lognormal(self, data: np.ndarray) -> Tuple[dict, dict, str, List[str]]:
        """Fit lognormal distribution using MLE on log-transformed data"""
        warnings_list = []

        # Filter to positive values only
        positive_data = data[data > 0]
        if len(positive_data) < len(data):
            n_removed = len(data) - len(positive_data)
            warnings_list.append(f"Removed {n_removed} non-positive values for lognormal fit")

        if len(positive_data) < 10:
            raise ValueError("Insufficient positive values for lognormal fit")

        log_data = np.log(positive_data)

        # MLE for lognormal is MLE for normal on log-transformed data
        mu = np.mean(log_data)
        sigma = np.std(log_data, ddof=1)

        # Kolmogorov-Smirnov test on log-transformed data
        ks_stat, ks_pvalue = stats.kstest(log_data, 'norm', args=(mu, sigma))

        # Log-likelihood, AIC, BIC
        n = len(positive_data)
        k = 2
        ll = np.sum(stats.lognorm.logpdf(positive_data, s=sigma, scale=np.exp(mu)))
        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        # Parameters in log-space (compatible with numpy.random.lognormal)
        params = {'mean': float(mu), 'std': float(sigma)}
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        # Also report the implied real-space mean/std for clarity
        real_mean = np.exp(mu + sigma**2 / 2)
        real_std = real_mean * np.sqrt(np.exp(sigma**2) - 1)

        rationale = (
            f"Lognormal fit: log-space mu={mu:.4f}, sigma={sigma:.4f}. "
            f"Real-space mean={real_mean:.4f}, std={real_std:.4f}. "
            f"KS p-value (on log data)={ks_pvalue:.3f}"
        )

        return params, gof, rationale, warnings_list

    def _fit_triangular(self, data: np.ndarray) -> Tuple[dict, dict, str]:
        """
        Fit triangular distribution

        Uses percentiles for min/max and mode estimation
        """
        # Estimate parameters from percentiles
        min_val = np.percentile(data, 1)   # Use 1st percentile to avoid outliers
        max_val = np.percentile(data, 99)  # Use 99th percentile

        # Estimate mode: use sample mode approximation
        # For triangular, mode can be estimated from mean and bounds
        # mean = (min + mode + max) / 3, so mode = 3*mean - min - max
        mean = np.mean(data)
        mode_est = 3 * mean - min_val - max_val

        # Clamp mode to be within [min, max]
        mode_val = np.clip(mode_est, min_val, max_val)

        # If mode is at boundary, use median-based estimate
        if mode_val == min_val or mode_val == max_val:
            mode_val = np.median(data)

        # Calculate c parameter for scipy
        if max_val > min_val:
            c = (mode_val - min_val) / (max_val - min_val)
        else:
            c = 0.5

        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = stats.kstest(
            data, 'triang',
            args=(c, min_val, max_val - min_val)
        )

        # Log-likelihood, AIC, BIC
        n = len(data)
        k = 3  # min, mode, max
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ll = np.sum(stats.triang.logpdf(data, c, loc=min_val, scale=max_val - min_val))

        # Handle -inf in log-likelihood (data outside bounds)
        if np.isinf(ll):
            ll = -1e10  # Large negative value

        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        params = {
            'min': float(min_val),
            'mode': float(mode_val),
            'max': float(max_val)
        }
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        rationale = (
            f"Triangular fit: min={min_val:.4f}, mode={mode_val:.4f}, max={max_val:.4f}. "
            f"KS p-value={ks_pvalue:.3f}"
        )

        return params, gof, rationale

    def _fit_beta(
        self,
        data: np.ndarray,
        bounds: Optional[Tuple[float, float]] = None
    ) -> Tuple[dict, dict, str]:
        """
        Fit beta distribution (scaled to optional bounds)

        Uses method of moments for initial estimate, then MLE
        """
        # Determine bounds
        if bounds is None:
            min_val = np.min(data)
            max_val = np.max(data)
        else:
            min_val, max_val = bounds

        # Scale data to [0, 1]
        if max_val <= min_val:
            raise ValueError("max_val must be greater than min_val")

        scaled_data = (data - min_val) / (max_val - min_val)

        # Clip to (0, 1) for beta distribution (exclusive)
        scaled_data = np.clip(scaled_data, 1e-10, 1 - 1e-10)

        # Method of moments for initial estimates
        mean = np.mean(scaled_data)
        var = np.var(scaled_data, ddof=1)

        # Beta method of moments
        # mean = alpha / (alpha + beta)
        # var = alpha*beta / ((alpha+beta)^2 * (alpha+beta+1))
        if var < mean * (1 - mean):
            common = mean * (1 - mean) / var - 1
            alpha_init = mean * common
            beta_init = (1 - mean) * common
        else:
            alpha_init = 2.0
            beta_init = 2.0

        # MLE fitting
        try:
            alpha, beta_param, _, _ = stats.beta.fit(scaled_data, floc=0, fscale=1)
        except:
            alpha, beta_param = alpha_init, beta_init

        # Ensure valid parameters
        alpha = max(0.1, alpha)
        beta_param = max(0.1, beta_param)

        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = stats.kstest(scaled_data, 'beta', args=(alpha, beta_param))

        # Log-likelihood, AIC, BIC
        n = len(data)
        k = 4  # alpha, beta, min, max
        ll = np.sum(stats.beta.logpdf(scaled_data, alpha, beta_param))
        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        params = {
            'alpha': float(alpha),
            'beta': float(beta_param),
            'min': float(min_val),
            'max': float(max_val)
        }
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        # Interpret alpha/beta
        if alpha > beta_param:
            skew_desc = "right-skewed (tendency toward upper bound)"
        elif alpha < beta_param:
            skew_desc = "left-skewed (tendency toward lower bound)"
        else:
            skew_desc = "symmetric"

        rationale = (
            f"Beta fit: alpha={alpha:.2f}, beta={beta_param:.2f} ({skew_desc}), "
            f"scaled to [{min_val:.4f}, {max_val:.4f}]. "
            f"KS p-value={ks_pvalue:.3f}"
        )

        return params, gof, rationale

    def _fit_uniform(self, data: np.ndarray) -> Tuple[dict, dict, str]:
        """Fit uniform distribution"""
        min_val = np.min(data)
        max_val = np.max(data)

        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = stats.kstest(
            data, 'uniform',
            args=(min_val, max_val - min_val)
        )

        # Log-likelihood, AIC, BIC
        n = len(data)
        k = 2
        ll = np.sum(stats.uniform.logpdf(data, loc=min_val, scale=max_val - min_val))
        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        params = {'min': float(min_val), 'max': float(max_val)}
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        rationale = f"Uniform fit: [{min_val:.4f}, {max_val:.4f}]. KS p-value={ks_pvalue:.3f}"

        return params, gof, rationale

    def _fit_truncnorm(
        self,
        data: np.ndarray,
        bounds: Optional[Tuple[float, float]] = None
    ) -> Tuple[dict, dict, str]:
        """Fit truncated normal distribution"""
        # Determine bounds
        if bounds is None:
            min_val = np.percentile(data, 0.5)
            max_val = np.percentile(data, 99.5)
        else:
            min_val, max_val = bounds

        # Fit normal first
        mu = np.mean(data)
        sigma = np.std(data, ddof=1)

        # Convert to scipy's truncnorm parameterization
        a = (min_val - mu) / sigma
        b = (max_val - mu) / sigma

        # Kolmogorov-Smirnov test
        ks_stat, ks_pvalue = stats.kstest(
            data, 'truncnorm',
            args=(a, b, mu, sigma)
        )

        # Log-likelihood, AIC, BIC
        n = len(data)
        k = 4  # mean, std, min, max
        ll = np.sum(stats.truncnorm.logpdf(data, a, b, loc=mu, scale=sigma))
        aic = 2 * k - 2 * ll
        bic = k * np.log(n) - 2 * ll

        params = {
            'mean': float(mu),
            'std': float(sigma),
            'min': float(min_val),
            'max': float(max_val)
        }
        gof = {
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pvalue),
            'aic': float(aic),
            'bic': float(bic),
            'log_likelihood': float(ll)
        }

        rationale = (
            f"Truncated normal fit: mean={mu:.4f}, std={sigma:.4f}, "
            f"bounds=[{min_val:.4f}, {max_val:.4f}]. KS p-value={ks_pvalue:.3f}"
        )

        return params, gof, rationale

    def select_best_distribution(
        self,
        data: np.ndarray,
        candidates: List[str],
        bounds: Optional[Tuple[float, float]] = None,
        domain_constraint: Optional[str] = None
    ) -> FitResult:
        """
        Select best distribution from candidates using weighted criteria

        Args:
            data: Array of historical observations
            candidates: List of distribution types to test
            bounds: Optional (min, max) bounds for bounded distributions
            domain_constraint: 'non_negative', 'bounded_01', or None

        Returns:
            FitResult for the best distribution
        """
        results = []

        for dist_type in candidates:
            try:
                result = self.fit_distribution(data, dist_type, bounds)
                results.append(result)
            except Exception as e:
                # Skip distributions that fail to fit
                pass

        if not results:
            raise ValueError("No distributions could be fit to the data")

        # Score each distribution
        scores = []
        for result in results:
            score = self._score_distribution(result, data, domain_constraint)
            scores.append(score)

        # Select best
        best_idx = np.argmax(scores)
        best_result = results[best_idx]

        # Add selection rationale
        best_result.rationale += f"\n  Selected from {candidates} with score {scores[best_idx]:.3f}"

        return best_result

    def _score_distribution(
        self,
        result: FitResult,
        data: np.ndarray,
        domain_constraint: Optional[str]
    ) -> float:
        """
        Score a distribution fit using weighted criteria

        Higher score = better fit
        """
        gof = result.goodness_of_fit

        # 1. AIC/BIC score (lower is better, so negate and normalize)
        # Normalize relative to data variance
        data_var = np.var(data)
        aic_score = -gof['aic'] / (len(data) * np.log(data_var + 1))

        # 2. KS p-value (higher is better)
        ks_score = gof['ks_p_value']

        # 3. Domain logic score
        domain_score = self._domain_logic_score(result, domain_constraint)

        # 4. Parsimony score (lower complexity is better)
        parsimony = 1.0 - (self.PARSIMONY_SCORES.get(result.distribution_type, 3) - 1) / 3

        # Weighted combination
        w = self.SELECTION_WEIGHTS
        total_score = (
            w['aic_bic'] * aic_score +
            w['ks_pvalue'] * ks_score +
            w['domain_logic'] * domain_score +
            w['parsimony'] * parsimony
        )

        return total_score

    def _domain_logic_score(
        self,
        result: FitResult,
        constraint: Optional[str]
    ) -> float:
        """Score based on domain constraints"""
        dist_type = result.distribution_type

        if constraint == 'non_negative':
            # Lognormal is ideal for non-negative data
            if dist_type == 'lognormal':
                return 1.0
            elif dist_type in ('beta', 'truncnorm'):
                params = result.parameters
                if params.get('min', 0) >= 0:
                    return 0.8
            elif dist_type == 'triangular':
                if result.parameters.get('min', 0) >= 0:
                    return 0.7
            elif dist_type == 'normal':
                return 0.3  # Can go negative
            return 0.5

        elif constraint == 'bounded_01':
            # Beta is ideal for [0,1] bounded data
            if dist_type == 'beta':
                return 1.0
            elif dist_type == 'truncnorm':
                return 0.7
            elif dist_type == 'triangular':
                return 0.6
            return 0.3

        # No constraint - all equally valid
        return 0.7

    def compute_goodness_of_fit(
        self,
        data: np.ndarray,
        result: FitResult
    ) -> dict:
        """
        Compute additional goodness-of-fit statistics

        Returns dict with KS, Anderson-Darling, Cramer-von Mises statistics
        """
        dist_type = result.distribution_type
        params = result.parameters

        gof = dict(result.goodness_of_fit)  # Copy existing

        # Generate samples from fitted distribution for comparison
        n = len(data)
        if dist_type == 'normal':
            theoretical = stats.norm.rvs(params['mean'], params['std'], size=n*10)
        elif dist_type == 'lognormal':
            theoretical = stats.lognorm.rvs(
                s=params['std'],
                scale=np.exp(params['mean']),
                size=n*10
            )
        else:
            # Skip advanced tests for other distributions
            return gof

        # Anderson-Darling (only for normal and lognormal)
        if dist_type == 'normal':
            ad_result = stats.anderson(data, dist='norm')
            gof['anderson_darling_statistic'] = float(ad_result.statistic)
            gof['anderson_darling_critical_5pct'] = float(ad_result.critical_values[2])

        # Cramér-von Mises (two-sample)
        try:
            cvm_result = stats.cramervonmises_2samp(data, theoretical)
            gof['cvm_statistic'] = float(cvm_result.statistic)
            gof['cvm_p_value'] = float(cvm_result.pvalue)
        except:
            pass

        return gof


# =============================================================================
# PARAMETER VALIDATION
# =============================================================================

def validate_distribution_params(dist_type: str, params: dict) -> List[str]:
    """
    Validate distribution parameters

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


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def fit_distribution(
    data: Union[np.ndarray, pd.Series, List[float]],
    dist_type: str,
    bounds: Optional[Tuple[float, float]] = None
) -> FitResult:
    """
    Convenience function to fit a distribution

    Args:
        data: Historical observations
        dist_type: Distribution type
        bounds: Optional bounds for bounded distributions

    Returns:
        FitResult with fitted parameters
    """
    fitter = DistributionFitter()
    if isinstance(data, pd.Series):
        data = data.values
    return fitter.fit_distribution(np.asarray(data), dist_type, bounds)


def select_best_distribution(
    data: Union[np.ndarray, pd.Series, List[float]],
    candidates: List[str] = None,
    bounds: Optional[Tuple[float, float]] = None,
    domain_constraint: Optional[str] = None
) -> FitResult:
    """
    Convenience function to select best distribution

    Args:
        data: Historical observations
        candidates: Distribution types to test (default: all applicable)
        bounds: Optional bounds
        domain_constraint: 'non_negative', 'bounded_01', or None

    Returns:
        FitResult for best distribution
    """
    if candidates is None:
        if domain_constraint == 'non_negative':
            candidates = ['lognormal', 'triangular', 'beta']
        elif domain_constraint == 'bounded_01':
            candidates = ['beta', 'triangular', 'truncnorm']
        else:
            candidates = ['normal', 'lognormal', 'triangular', 'beta']

    fitter = DistributionFitter()
    if isinstance(data, pd.Series):
        data = data.values

    return fitter.select_best_distribution(
        np.asarray(data), candidates, bounds, domain_constraint
    )


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Generate sample data
    np.random.seed(42)

    # Lognormal data (like steel prices)
    lognormal_data = np.random.lognormal(mean=0.0, sigma=0.3, size=500)

    print("=" * 60)
    print("Testing Distribution Fitter")
    print("=" * 60)

    fitter = DistributionFitter()

    # Test lognormal fit
    print("\n1. Fitting lognormal distribution to lognormal data:")
    result = fitter.fit_distribution(lognormal_data, 'lognormal')
    print(f"   Parameters: {result.parameters}")
    print(f"   KS p-value: {result.goodness_of_fit['ks_p_value']:.4f}")
    print(f"   Rationale: {result.rationale}")

    # Test automatic selection
    print("\n2. Automatic distribution selection:")
    best = fitter.select_best_distribution(
        lognormal_data,
        ['normal', 'lognormal', 'triangular'],
        domain_constraint='non_negative'
    )
    print(f"   Best distribution: {best.distribution_type}")
    print(f"   Parameters: {best.parameters}")

    # Test normal data
    print("\n3. Fitting normal distribution to normal data:")
    normal_data = np.random.normal(loc=100, scale=15, size=500)
    result = fitter.fit_distribution(normal_data, 'normal')
    print(f"   Parameters: {result.parameters}")
    print(f"   KS p-value: {result.goodness_of_fit['ks_p_value']:.4f}")

    # Test validation
    print("\n4. Parameter validation:")
    errors = validate_distribution_params('normal', {'mean': 0})
    print(f"   Missing std: {errors}")

    errors = validate_distribution_params('triangular', {'min': 0, 'mode': 2, 'max': 1})
    print(f"   Invalid triangular: {errors}")

    print("\nDone!")
