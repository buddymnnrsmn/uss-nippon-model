# Bloomberg Quick Reference Card

## Essential Tickers - Copy/Paste Ready

### Steel Prices
```
MWST1MCA Index    US HRC Midwest
MWST1MCR Index    US CRC
MWST1MHD Index    US HDG (Galvanized)
SPGSTHRC Index    EU HRC
STLSCRBR Index    Scrap #1 Busheling
IABORUSE Index    Iron Ore 62% Fe
NG1 Comdty        Natural Gas
XAL1 Comdty       Coking Coal
```

### Interest Rates
```
USGG10YR Index    US 10Y Treasury
USGG30YR Index    US 30Y Treasury
JGBS10 Index      Japan 10Y JGB
JGBS30 Index      Japan 30Y JGB
SOFRRATE Index    SOFR Rate
FDTR Index        Fed Funds Rate
```

### Credit Spreads
```
LUACOAS Index     BBB Corporate Spread
LF98OAS Index     High Yield Spread
```

### Peer Companies
```
X US Equity       U.S. Steel
NUE US Equity     Nucor
STLD US Equity    Steel Dynamics
CLF US Equity     Cleveland-Cliffs
CMC US Equity     Commercial Metals
5401 JP Equity    Nippon Steel
MT NA Equity      ArcelorMittal
PKX US Equity     POSCO (ADR)
```

### Demand Drivers
```
SAABORWT Index    US Auto Production
NHSPSTOT Index    Housing Starts
IP CHNG Index     Industrial Production
NAPMPMI Index     ISM Manufacturing PMI
RIGSUA Index      US Oil Rig Count
CNSTTMOM Index    Construction Spending
```

### Macro
```
GDP CQOQ Index    US GDP QoQ
CPI YOY Index     US CPI YoY
USURTOT Index     Unemployment Rate
CONCCONF Index    Consumer Confidence
```

### Steel Industry
```
AISIUTIL Index    AISI Capacity Utilization
WSTLPROD Index    World Steel Production
```

---

## Excel BDH Template

Paste into Excel with Bloomberg Add-In:

```excel
' === STEEL PRICES (Daily, 1990-2025) ===
=BDH("MWST1MCA Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P")
=BDH("MWST1MCR Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P")
=BDH("MWST1MHD Index","PX_LAST","1/1/2000","12/31/2025","Dir=V","Fill=P")
=BDH("IABORUSE Index","PX_LAST","1/1/2005","12/31/2025","Dir=V","Fill=P")
=BDH("STLSCRBR Index","PX_LAST","1/1/2000","12/31/2025","Dir=V","Fill=P")
=BDH("NG1 Comdty","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P")

' === INTEREST RATES (Daily, 1990-2025) ===
=BDH("USGG10YR Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P")
=BDH("JGBS10 Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Fill=P")
=BDH("LUACOAS Index","PX_LAST","1/1/2000","12/31/2025","Dir=V","Fill=P")
=BDH("SOFRRATE Index","PX_LAST","1/1/2018","12/31/2025","Dir=V","Fill=P")

' === PEER FINANCIALS (Quarterly, 2015-2025) ===
=BDH("NUE US Equity","SALES_REV_TURN,EBITDA,EBITDA_MARGIN,CAPITAL_EXPEND","1/1/2015","12/31/2025","Dir=V","Per=Q")
=BDH("STLD US Equity","SALES_REV_TURN,EBITDA,EBITDA_MARGIN,CAPITAL_EXPEND","1/1/2015","12/31/2025","Dir=V","Per=Q")
=BDH("CLF US Equity","SALES_REV_TURN,EBITDA,EBITDA_MARGIN,CAPITAL_EXPEND","1/1/2015","12/31/2025","Dir=V","Per=Q")
=BDH("X US Equity","SALES_REV_TURN,EBITDA,EBITDA_MARGIN,CAPITAL_EXPEND","1/1/2015","12/31/2025","Dir=V","Per=Q")

' === DEMAND DRIVERS (Monthly, 1990-2025) ===
=BDH("SAABORWT Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Per=M")
=BDH("NHSPSTOT Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Per=M")
=BDH("NAPMPMI Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Per=M")
=BDH("RIGSUA Index","PX_LAST","1/1/2000","12/31/2025","Dir=V","Per=W")

' === MACRO (Various frequencies) ===
=BDH("GDP CQOQ Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Per=Q")
=BDH("CPI YOY Index","PX_LAST","1/1/1990","12/31/2025","Dir=V","Per=M")
```

---

## Priority Order (If Time Limited)

### Must Have (30 min)
1. `MWST1MCA Index` - HRC prices
2. `USGG10YR Index` - US 10Y rates
3. `JGBS10 Index` - Japan 10Y rates
4. `LUACOAS Index` - Credit spreads

### Should Have (30 min)
5. `MWST1MCR Index` - CRC prices
6. `IABORUSE Index` - Iron ore
7. `STLSCRBR Index` - Scrap prices
8. Peer financials (NUE, STLD, CLF)

### Nice to Have (30 min)
9. Demand drivers (auto, housing, PMI)
10. Rig count for OCTG correlation
11. M&A transactions
12. Capacity utilization

---

## Common Commands

| Action | Command |
|--------|---------|
| Security search | `SECF <GO>` |
| Commodity search | `ALLX {keyword} <GO>` |
| Steel industry | `BI STEEL <GO>` |
| M&A database | `MA <GO>` |
| Economic data | `ECST <GO>` |
| Excel help | `API <GO>` |
| Help desk | `<HELP> <HELP>` |
