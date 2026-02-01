#!/bin/bash
# Data Collection Helper Script
# Run this after manually downloading files

echo "==================================================================="
echo "DATA COLLECTION STATUS CHECK"
echo "==================================================================="
echo ""

# Check for SEC 10-K
if [ -f "../evidence/USS_10K_2023.pdf" ]; then
    echo "✓ USS 10-K downloaded"
else
    echo "⚠ USS 10-K missing - download from SEC EDGAR"
    echo "  URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=10-K"
fi

# Check for CME data
if [ -f "../evidence/CME_HRC_Futures_2023.csv" ]; then
    echo "✓ CME HRC Futures downloaded"
else
    echo "⚠ CME HRC Futures missing - download from CME Group"
    echo "  URL: https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.settlements.html"
fi

# Check for SteelBenchmarker
if [ -f "../evidence/SteelBenchmarker_History.pdf" ]; then
    echo "✓ SteelBenchmarker downloaded"
else
    echo "⚠ SteelBenchmarker missing - download from SteelBenchmarker.com"
    echo "  URL: http://www.steelbenchmarker.com/files/history.pdf"
fi

# Check for Proxy
if [ -f "../evidence/USS_Proxy_2024.pdf" ]; then
    echo "✓ USS Proxy downloaded"
else
    echo "⚠ USS Proxy missing - download from SEC EDGAR"
    echo "  URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001163302&type=DEF%2014A"
fi

echo ""
echo "==================================================================="
echo "CSV TEMPLATE STATUS"
echo "==================================================================="
echo ""

# Check if templates are filled
python3 << 'EOF'
import csv
from pathlib import Path

templates = {
    'USS 2023 Data': '../data_collection/uss_2023_data.csv',
    'Steel Prices': '../data_collection/steel_prices_2023.csv',
    'Balance Sheet': '../data_collection/balance_sheet_items.csv',
}

for name, path in templates.items():
    p = Path(path)
    if p.exists():
        with open(p, 'r') as f:
            content = f.read()
            has_data = 'Source_Value' in content and ',,' not in content[:200]
            status = "✓ Data filled" if has_data else "⚠ Template empty"
    else:
        status = "✗ Missing"
    print(f"{name:.<30} {status}")
EOF

echo ""
echo "Next step: Run python verify_inputs.py"
echo ""
