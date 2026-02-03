# Project Status

**Last Updated:** 2026-02-03

---

## What This Project Is

A Python-based DCF valuation model analyzing Nippon Steel's $55/share acquisition offer for U.S. Steel Corporation. Built for the RAMBAS Team Capstone Project.

**Core Capabilities:**
- **Valuation Engine** — Price × Volume methodology across 4 business segments (Flat-Rolled, Mini Mill, USSE, Tubular), projecting 5-year cash flows with dual valuation: USS standalone (10.7% verified WACC) vs Nippon view (7.95% IRP-adjusted WACC). WACC calculations sourced from verifiable public data with full audit trails.
- **Scenario Framework** — 7 scenarios calibrated to 34-year historical data with probability weights, from Severe Downturn (25% probability) to Optimistic (5%)
- **Interactive Dashboard** — Streamlit interface with on-demand calculations, caching, and real-time progress tracking
- **Monte Carlo Simulation** — Probabilistic valuation with Latin Hypercube Sampling, correlation modeling, and risk metrics (VaR, CVaR)
- **Breakup Fee Analysis** — $565M fee modeling with adjustable probability sliders and expected value calculations
- **LBO Analysis** — Leveraged buyout perspective establishing valuation floor
- **Audit Infrastructure** — Input traceability, source verification, and automated validation

Run with: `streamlit run interactive_dashboard.py`

---

## Currently Working On

### Active

| Item | Status | Notes |
|------|--------|-------|
| Nippon analysis dashboard integration | In Progress | Add buyer capacity section to interactive dashboard |

### Queued

| Item | Blocked By | Notes |
|------|------------|-------|
| **Premium Steel Market Opportunity** | Bloomberg data | Model 5 premium segments (EV automotive, electrical, green, offshore wind, aerospace/defense) as Nippon technology synergies. Design spec in `market-data/premium-steel-market-opportunity.md`. Ready for implementation once data is gathered. |
| Monte Carlo Phase 2: Enhanced Analytics | — | Tornado diagrams, two-way sensitivity tables, Excel/PDF export. Ready to start. |
| Bloomberg data integration | Data access | Infrastructure built (`market-data/`). Comprehensive guide in `market-data/BLOOMBERG_DATA_GUIDE.md`. |
| Source data audit completion | Manual effort | Tracker in `audit-verification/data_collection/`. Requires extracting values from 10-K, steel price sources. |
| Monte Carlo dashboard integration | Phase 2 completion | Add interactive Monte Carlo controls to Streamlit dashboard. |

---

## Market Data Infrastructure

**Location:** `market-data/`

| File | Purpose |
|------|---------|
| `BLOOMBERG_DATA_GUIDE.md` | Complete data gathering guide with 13 phases: Monte Carlo calibration data (steel prices, rates, peers, demand drivers, macro, M&A) + premium steel segment research (EV, green, wind, electrical, aerospace). |
| `premium-steel-market-opportunity.md` | Technical spec for modeling 5 premium steel segments as technology transfer synergies. Includes dataclass design, dashboard layout, integration points. |
| `bloomberg_loader.py` | Python loader for Bloomberg exports |
| `integrate_with_model.py` | Integration with main valuation model |
| `QUICK_REFERENCE.md` | Bloomberg ticker reference |

**Premium Segment Priority:**
1. EV Automotive Steel — AHSS, ultra-high tensile, battery case (largest TAM)
2. Green Steel — verdeX, COURSE50, low-carbon premium (clearest differentiation)
3. Offshore Wind — Monopile plate, corrosion-resistant
4. Electrical Steel — NOES for EV motors, GOES for grid
5. Aerospace/Defense — Specialty alloys, tight tolerances

---

## Nippon Steel Buyer Analysis

**Location:** `nippon-analysis/` and `documentation/`

| File | Purpose |
|------|---------|
| `nippon-analysis/README.md` | Module overview, data sources, integration guide |
| `nippon-analysis/nippon_financial_profile.py` | Core financials, balance sheet, credit metrics |
| `nippon-analysis/nippon_capacity_analysis.py` | Pro forma, funding gap, stress tests |
| `documentation/NIPPON_FINANCIAL_ASSESSMENT.md` | Executive assessment of deal capacity (placeholder data) |
| `documentation/NIPPON_STEEL_FINANCIAL_ANALYSIS.md` | WRDS-verified financial analysis (FY2019-2024) |
| `documentation/USS_CURRENT_STATE_ANALYSIS.md` | Detailed analysis of USS's structural challenges |

**Key Findings:**
- **Deal Capacity Verdict:** CONDITIONAL (Medium Confidence)
- **Pre-Deal Leverage:** 2.69x Debt/EBITDA (strong position)
- **Post-Deal Leverage:** 3.21x (near investment grade threshold)
- **Funding Gap:** ~$3.1B shortfall on $29B deployment (manageable at 10%)
- **Rating Impact:** Likely 1-notch downgrade to BBB with negative outlook

**Data Sources:**
- WRDS Compustat Global (gvkey: 100155) - verified against official filings
- Nippon Steel FY2024 Annual Report (決算短信)
- S&P, Moody's, Fitch credit ratings
- USS Merger Proxy (SEC Schedule 14A)

**Integration Status:**
- Python modules ready in `nippon-analysis/` directory
- Documentation completed with full source citations
- Dashboard integration pending (will add "Nippon Buyer Capacity Analysis" section)

---

## Future Goals

| Item | Priority | Description |
|------|----------|-------------|
| Time-series price models | Medium | Mean-reverting steel prices, jump-diffusion, regime-switching for Monte Carlo. |
| Real options analysis | Low | Value optionality: delay, expand, abandon, switch. Advanced Monte Carlo extension. |
| LBO model refinement | Low | Stress testing, sensitivity analysis for PE buyer perspective. |
| GPU acceleration | Low | Speed up Monte Carlo for 50,000+ iterations. |

---

## Recently Completed

| Item | Date | Notes |
|------|------|-------|
| SCENARIO_RATIONALE documentation update | 2026-02-03 | Updated all scenario valuations with current model outputs. Added WACC data sources section (S.5) with verifiable inputs from Federal Reserve, Duff & Phelps, USS 10-K, Bank of Japan. Exported to PDF and Word formats. |
| Documentation export workflows | 2026-02-03 | Created `WORKFLOW_REFERENCE.md` documenting how to run model scenarios, export to PDF (WeasyPrint), export to Word (python-docx), and access WACC audit trails. |
| Nippon Steel buyer capacity analysis | 2026-02-02 | WRDS-verified financials, pro forma leverage, funding gap analysis, stress tests. Three comprehensive documentation files + Python modules. |
| USS current state analysis | 2026-02-02 | Detailed 34-year historical analysis confirming structural decline (56% profitable years, 3.4% revenue CAGR, aging infrastructure). |
| Multi-year competitor analysis | 2026-02-01 | CAGR comparison vs 11 steel peers (2019-2024). Dashboard + Excel export. |

---

## Key Contacts

RAMBAS Team Capstone Project — Internal use only.
