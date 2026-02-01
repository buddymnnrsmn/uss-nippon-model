# Documentation Index

This folder contains all documentation for the USS / Nippon Steel Merger Financial Model—a DCF valuation tool analyzing the $55/share acquisition offer.

---

## Quick Reference

**What is this project?** A Python-based financial model that values U.S. Steel Corporation under various scenarios to evaluate Nippon Steel's $55/share acquisition offer.

**Key files:**
- `price_volume_model.py` — Core DCF engine using Price × Volume methodology
- `interactive_dashboard.py` — Streamlit web interface for interactive analysis

**Start here:** [Dashboard User Guide](#dashboard-user-guide) or [Executive Summary](#executive-summary)

---

## Getting Started

### [Dashboard User Guide](DASHBOARD_USER_GUIDE.md)

How to use the interactive Streamlit dashboard. Covers on-demand calculations with intelligent caching, where the page loads in 2-5 seconds (vs 30+ seconds previously). Users control which analyses run via buttons. Features include scenario comparison (5-15 sec), probability-weighted valuation, steel price sensitivity, and WACC sensitivity. Results persist across browser refreshes via disk caching.

### [Sensitivity Analysis Quick Start](SENSITIVITY_ANALYSIS_QUICK_START.md)

Run your first Monte Carlo simulation in 30 seconds. The framework transforms deterministic DCF output ("Base case = $75.80") into probabilistic statements ("Expected value $75.80 with 80% confidence between $52-$103, only 18.5% chance below $55 offer"). Run `python scripts/run_monte_carlo_demo.py -n 1000` to generate 1,000 iterations with statistics, CSV output, and visualization plots.

### [Visual Guide](VISUAL_GUIDE.md)

Explains the three architecture diagrams (model_architecture.png/svg/dot). Shows the five-layer model structure: (1) Inputs (scenarios, steel prices, volumes, WACC, capital projects), (2) Segment Processing (Flat-Rolled, Mini Mill, USSE, Tubular), (3) Calculations (Price × Volume → Revenue → EBITDA → FCF), (4) Consolidation (10-year projections 2024-2033), (5) Dual Valuation (USS standalone at 10.9% WACC vs Nippon at 7.5% IRP-adjusted WACC).

---

## Model Documentation

### [Model Methodology](MODEL_METHODOLOGY.md)

Core technical documentation for the Price × Volume methodology. Revenue is built bottom-up by multiplying steel shipment volumes (tons/year) by realized prices ($/ton) for each of four business segments. Key concepts: (1) Price premiums calibrated from 2023 actuals (Flat-Rolled earns 51% premium over HRC benchmark), (2) Margin dynamics flex with steel prices (HRC +$100/ton → margin +4 percentage points), (3) Six capital projects with distinct CapEx/EBITDA schedules, (4) Interest Rate Parity converts Nippon's 3.94% JPY WACC to 7.55% USD WACC, creating $25/share valuation advantage, (5) Financing reality check shows USS standalone would face 17.8% dilution funding $14B NSA program.

### [Scenario Assumptions](SCENARIO_ASSUMPTIONS.md)

Detailed assumptions for seven valuation scenarios, calibrated to 34-year historical data (1990-2023). Scenarios map to historical percentiles: Severe Downturn (0-25th, 25% probability, $5-8/share), Downside (25-40th, 30% probability, $25-43/share), Base Case (50th, 30% probability, $16-27/share), Above Average (75-90th, 10% probability, $50-75/share), Optimistic (90th+, 5% probability, $38-56/share). Also includes Wall Street Consensus and NSA Mandated CapEx reference scenarios. Probability-weighted expected value: USS standalone $23.91, Nippon view $38.67, vs $55 offer.

### [Steel Price Methodology](STEEL_PRICE_METHODOLOGY.md)

Steel prices are the single most important valuation driver with 5.5x elasticity (1% price change → 5.5% equity value change). A ±10% steel price swing moves valuation by $20-30/share. Three-layer price system: (1) Benchmark prices (2023 HRC = $680/ton), (2) Price factors (scenario adjustments 70%-120%), (3) Price premiums (product mix: Flat-Rolled +51%, Mini Mill +29%). Breakeven for $55 offer requires ~88% price factor. Historical context: 70% = 2015-16 trough, 100% = 2023 average, 120% = 2021 peak.

### [Sensitivity Analysis](SENSITIVITY_ANALYSIS.md)

One-way sensitivity tables for key valuation drivers. Steel price sensitivity shows value range from $7.71 (70% factor) to $190.81 (120% factor). WACC sensitivity shows Nippon's 3.4% advantage (7.5% vs 10.9%) adds ~$25/share. Volume sensitivity, terminal growth, and exit multiple impacts also quantified. Each 5% price change = ~$12-15/share value change.

### [Monte Carlo User Guide](MONTE_CARLO_USER_GUIDE.md)

Comprehensive guide to probabilistic valuation. Explains why point estimates hide uncertainty and how Monte Carlo addresses this by running thousands of iterations with random inputs drawn from probability distributions. Output includes mean/median values, confidence intervals (P10-P90), Value at Risk (VaR), Conditional VaR (CVaR), and probability metrics (chance above $55, chance below $40). Covers input distributions, correlation modeling, and interpretation of results.

### [Reusable Framework Guide](REUSABLE_FRAMEWORK_GUIDE.md)

How to adapt this model architecture for other investment types (real estate, private equity, distressed debt). Approximately 80-85% of the codebase is directly reusable. Reusable components: DCF engine, terminal value calculation, scenario framework, Monte Carlo engine, dashboard infrastructure. Industry-specific customization needed: data structures (segments → properties/portfolio companies), revenue drivers (steel price → rent/EBITDA), risk factors. Implementation time for new investment type: 15-22 hours.

---

## Analysis & Research

### [Executive Summary](EXECUTIVE_SUMMARY.md)

Transaction overview: Nippon Steel acquiring USS for $55/share (~$14.9B equity) plus $14B NSA investment commitments = $29B total capital deployment. Valuation summary across scenarios shows USS standalone $25-69/share, Nippon IRP-adjusted view $44-110/share. Key findings: (1) $55 offer falls within reasonable range, (2) IRP creates 3.35% WACC advantage adding ~$25/share to Nippon's view, (3) NSA investment program adds $35-55/share vs base case if executed successfully.

### [USS Historical Analysis (1990-2023)](USS_HISTORICAL_ANALYSIS_1990_2023.md)

34-year financial performance analysis revealing extreme cyclicality. Key findings: Only 56% of years profitable (19/34), net income volatility with $1.2B standard deviation, revenue range $4.9B-$23.8B. Five distinct eras identified. Recent transformation: 2020-23 period shows best 4-year average ($1.6B profit, 6.4% margin). Peak: 2021 record profit $4.2B (20.6% margin, 46% ROE). Critical context for understanding scenario probability weights.

### [USS Standalone Analysis](USS_STANDALONE_ANALYSIS.md)

"What if the merger doesn't happen?" analysis. Key finding: Even under most optimistic standalone scenario ($50.14/share), USS trades at discount to $55 offer. Limited FCF generation: 2024 shows negative FCF across all scenarios due to BR2 investment. Capital constraints: Only $4.4B excess for growth after maintenance CapEx, leaving $6.4B of NSA program unfunded. Projects that cannot be funded without merger: Gary Works BF ($3.1B), Mon Valley HSM ($1.0B), Greenfield Mini Mill ($1.0B).

### [Cleveland-Cliffs Offer Analysis](Cleveland-Cliffs_Final_Offer_Analysis.md)

Analysis of competing $54/share bid (50% cash / 50% stock). Company D (Cleveland-Cliffs) submitted December 15, 2023 proposal. Despite $1.5B reverse termination fee and claimed $6.50/share synergy value, USS Board rejected due to: (1) Antitrust concerns—combined entity would control 65%+ of US integrated steel, (2) Stock component uncertainty—value depends on Cliffs share price, (3) Execution risk from stockholder vote requirement, (4) Regulatory timeline uncertainty vs Nippon's cleaner approval path.

### [Risks and Challenges](RISKS_AND_CHALLENGES.md)

Comprehensive risk assessment across four categories. Execution risks: $14B deployment in 14 months, 6 simultaneous projects, construction inflation (historically 20-30% over budget), 100,000+ workers needed. Operational risks: Japanese management + US workforce integration, USW union opposition, technology transfer learning curve. Market risks: Steel price volatility ($20-30/share per 10% swing), import competition, demand cyclicality. Regulatory/political risks: CFIUS review, political opposition, Buy America provisions.

### [Model Validation](MODEL_VALIDATION_HISTORICAL_CORRELATION.md)

Critical finding: Original model scenarios were calibrated to 82nd-97th percentiles (optimistic), not representative outcomes. Conservative scenario was actually at 82nd percentile, Base case at 91st percentile. Historical reality: 15/34 years unprofitable (44%), EBITDA range -$1,032M to +$5,396M, 120% coefficient of variation. Recalibration added Severe Downturn scenario (25% probability) to capture 24% of historical outcomes that were previously missing from analysis.

---

## Feature Documentation

### [Breakup Fee Summary](BREAKUP_FEE_SUMMARY.md)

Dashboard feature analyzing $565M breakup fee from 8-K filing ($2.51/share). Three deal outcome scenarios: (1) Deal Closes (70% probability) → shareholders receive $55, (2) Nippon Walks (20% probability) → standalone value + $2.51, (3) USS Walks (10% probability) → standalone value - $2.51. Expected value calculation shows deal premium of $3.15/share (6.2%) over expected no-deal value.

### [Breakup Fee Enhancements](BREAKUP_FEE_ENHANCEMENTS.md)

Three dashboard enhancements for breakup fee analysis: (1) Adjustable probability sliders in sidebar—customize deal close, Nippon walks, USS walks probabilities with real-time recalculation, (2) Interactive visualizations—probability sensitivity chart showing expected value vs deal close probability, scenario comparison bars, (3) Dynamic recommendations that change based on user assumptions. All calculations update instantly when sliders move.

### [Advanced Sensitivity Strategy](ADVANCED_SENSITIVITY_ANALYSIS_STRATEGY.md)

Strategic roadmap for advanced analytics. Current state: one-way sensitivities, 7 discrete scenarios, deterministic outputs. Target state: Monte Carlo with 10,000+ iterations, correlated inputs, VaR/CVaR risk metrics, tornado diagrams, dynamic scenario generation. Architecture: MonteCarloEngine with input distributions, correlation matrix, Latin Hypercube sampling, and visualization suite. Covers implementation for real options (delay, expand, abandon, switch) as advanced extension.

---

## Development & Implementation

### [Implementation Summary](IMPLEMENTATION_SUMMARY.md)

Model corrections based on historical data analysis (January 25, 2026). Changes: (1) Added SEVERE_DOWNTURN scenario (0-25th percentile, 25% probability), (2) Added ABOVE_AVERAGE scenario (75-90th percentile, 10% probability), (3) Recalibrated Base Case to true 50th percentile (was 91st), (4) Added probability_weight field to all scenarios, (5) Created probability-weighted valuation framework. All scenarios now include historical calibration with explicit percentile mappings.

### [Implementation Complete](IMPLEMENTATION_COMPLETE.md)

Breakup fee enhancements completion status (all three features delivered). Enhancement 1: Probability sliders working—move "Deal Closes" to 50% and watch Expected Deal Value drop from $53.79 to $52.03. Enhancement 2: Interactive charts—probability sensitivity (green line vs orange dashed with red vertical marker) and scenario comparison bars. Enhancement 3: Dynamic recommendations updating based on user assumptions.

### [Dashboard Enhancements Summary](DASHBOARD_ENHANCEMENTS_SUMMARY.md)

Dashboard transformation from auto-calculating (30+ second load) to responsive, efficient tool (2-5 second load). Completed features: Real-time progress bars for 7 operations (main model, scenario comparison, probability-weighted valuation, football field chart, steel price sensitivity, WACC sensitivity, bulk operations), on-demand calculations with caching, disk persistence across sessions, memory management. 85% implementation complete.

### [Sensitivity Implementation Summary](SENSITIVITY_ANALYSIS_IMPLEMENTATION_SUMMARY.md)

Monte Carlo implementation delivery. Delivered: (1) 60-page strategy document covering framework architecture, (2) Working monte_carlo_engine.py with Latin Hypercube Sampling, Cholesky decomposition for correlations, multiple distribution types (normal, lognormal, triangular, beta), integration with PriceVolumeModel. Output: Statistics, percentiles, VaR, CVaR, histograms, CDFs, tornado charts.

### [Changes Summary](CHANGES_SUMMARY.md)

Recent dashboard changes log (January 28, 2026). Removed time estimates from buttons (cleaner interface). Removed all emojis (professional appearance, cross-platform compatibility). Examples: "✓ All sections calculated successfully!" → "All sections calculated successfully", button text simplified from "Click to compare scenarios (5-15 second calculation)" to "Click to compare scenarios".

### [Test Results](TEST_RESULTS.md)

Dashboard enhancement test results—all 6 tests passed. Tests cover: (1) Progress callbacks—18 updates captured 0-100%, (2) Cache invalidation—hashing correctly detects scenario changes, (3) Disk persistence—save/load/clear operations verified, (4) Scenario comparison—7 scenarios with progress tracking, (5) Probability-weighted valuation—5 scenarios evaluated, (6) Memory tracking—cache size accurate.

### [Audit Analysis](AUDIT_TEST_ANALYSIS_2026_01_31.md)

Audit and test updates following project reorganization. Division error tests: 6/6 passing (equity floor, probability weighting, premium calculations). Dashboard feature tests: 6/6 passing after import path fixes (cache_persistence.py moved to scripts/). Model audit: All checks passing—margin dynamics, financing impact, scenario consistency verified.

### [Roadmap: Competitor Analysis](ROADMAP_MultiYear_Competitor_Analysis.md)

Future feature: Multi-year CAGR analysis comparing USS vs 11 peer steel companies. Two dimensions: (1) Rolling period analysis 2019-2025 showing growth rate evolution, (2) USS long-term historical trends back to 1990s. Metrics: Net income, CapEx, depreciation, total assets, total debt, stock price (>90% coverage); revenue, EBITDA, EBIT, margins (~53% coverage). Estimated effort: ~1,136 lines across 3 files.

---

## Architecture Diagrams

Visual representations of model structure:

- **[model_architecture.dot](model_architecture.dot)** — GraphViz source file for editing
- **[model_architecture.png](model_architecture.png)** — Raster image for documents/presentations
- **[model_architecture.svg](model_architecture.svg)** — Scalable vector for web/zoom
