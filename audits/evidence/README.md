# Evidence Folder
## Source Documents for Model Audit

This folder stores source documents used to verify model inputs.

---

## Required Documents

### SEC Filings
- [ ] `USS_10K_2023.pdf` - USS 2023 Annual Report (10-K)
- [ ] `USS_Proxy_2024.pdf` - 2024 Proxy Statement (DEF 14A)
  - Contains Barclays fairness opinion
  - Contains Goldman Sachs fairness opinion
- [ ] `USS_8K_Q4_2023.pdf` - Q4 2023 earnings 8-K (optional)

**Download from:** https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302

### Steel Price Data
- [ ] `CME_HRC_Futures_2023.csv` - CME HRC futures settlement prices
- [ ] `SteelBenchmarker_2023.pdf` - Monthly price composite
- [ ] `Platts_Steel_Prices_2023.csv` - If subscription available

**Download from:**
- CME: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html
- SteelBenchmarker: http://www.steelbenchmarker.com/files/history.pdf

### Company Presentations
- [ ] `USS_Q4_2023_Earnings_Deck.pdf` - Quarterly earnings presentation
- [ ] `USS_Investor_Presentation_2023.pdf` - Corporate overview
- [ ] `BR2_Phase2_Press_Release.pdf` - Big River Steel announcement
- [ ] `NSA_Press_Release_Dec2023.pdf` - Nippon acquisition announcement

**Download from:**
- USS IR: https://www.ussteel.com/investors
- Nippon: https://www.nipponsteel.com/en/news/

### Analyst Reports (if available)
- [ ] `Barclays_Research_USS_2023.pdf` - Equity research (subscription)
- [ ] `Goldman_Research_USS_2023.pdf` - Equity research (subscription)
- [ ] `Bloomberg_Consensus_USS.pdf` - Analyst consensus (subscription)

**Access via:** Bloomberg Terminal, FactSet, Capital IQ (requires subscription)

---

## Automated Data Collection

Run the data scraper to get download links:

```bash
cd ../verification_scripts
python data_scraper.py --all
```

This will create:
- `steel_price_sources.json` - Links to free price data
- `company_sources.json` - Links to investor materials
- `analyst_sources.json` - Where to find fairness opinions
- `data_collection_checklist.json` - Track download progress

---

## File Naming Convention

Use the following naming format:
- SEC Filings: `USS_{FilingType}_{Year}.pdf`
- Prices: `{Source}_{Product}_{Year}.csv`
- Company: `USS_{DocType}_{Quarter}_{Year}.pdf`
- Analyst: `{Firm}_{Type}_USS_{Year}.pdf`

Examples:
- `USS_10K_2023.pdf`
- `CME_HRC_Futures_2023.csv`
- `USS_Earnings_Q4_2023.pdf`
- `Barclays_FairnessOpinion_USS_2024.pdf`

---

## Data Extraction Workflow

1. **Download** documents to this folder
2. **Extract** data into CSV templates in `../data_collection/`
3. **Document** page numbers in `source_data_tracker.md`
4. **Verify** using `python verify_inputs.py`

---

## Notes

- Keep original PDFs for audit trail
- Do not commit sensitive/proprietary data to public repos
- Note any paywalled data that couldn't be obtained
- Document assumptions if data unavailable

---

## Status

**Last Updated:** _______________
**Completed By:** _______________
**Documents Downloaded:** ___ / 15
**Ready for Verification:** [ ] Yes [ ] No
