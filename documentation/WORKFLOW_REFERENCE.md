# Workflow Reference Guide
## Documentation and Export Workflows for USS/Nippon Financial Model

*Reference for future documentation updates and exports*

---

## 1. Running Model Scenarios and Extracting Valuations

### Get All Scenario Valuations
```python
from price_volume_model import PriceVolumeModel, get_scenario_presets, ScenarioType

scenarios = get_scenario_presets()

# Canonical scenario types (excludes aliases)
canonical_types = [
    ScenarioType.SEVERE_DOWNTURN,
    ScenarioType.DOWNSIDE,
    ScenarioType.BASE_CASE,
    ScenarioType.ABOVE_AVERAGE,
    ScenarioType.OPTIMISTIC,
    ScenarioType.WALL_STREET,
    ScenarioType.NIPPON_COMMITMENTS
]

for scenario_type in canonical_types:
    scenario = scenarios[scenario_type]
    model = PriceVolumeModel(scenario)
    analysis = model.run_full_analysis()

    # Key outputs
    uss_price = analysis['val_uss']['share_price']
    nippon_price = analysis['val_nippon']['share_price']

    # Financials
    df = analysis['consolidated']
    y1_ebitda = df[df['Year'] == 2024].iloc[0]['Total_EBITDA']
    avg_ebitda = df['Total_EBITDA'].mean()
```

### Calculate Probability-Weighted Expected Value
```python
prob_weighted_uss = 0
prob_weighted_nippon = 0

for scenario_type in canonical_types:
    scenario = scenarios[scenario_type]
    if scenario.probability_weight > 0:
        model = PriceVolumeModel(scenario)
        analysis = model.run_full_analysis()
        prob_weighted_uss += analysis['val_uss']['share_price'] * scenario.probability_weight
        prob_weighted_nippon += analysis['val_nippon']['share_price'] * scenario.probability_weight
```

### Get Scenario Parameters (Price/Volume Factors)
```python
for scenario_type in canonical_types:
    s = scenarios[scenario_type]
    ps = s.price_scenario  # SteelPriceScenario
    vs = s.volume_scenario  # VolumeScenario

    # Price factors
    print(f"HRC US: {ps.hrc_us_factor}")
    print(f"CRC US: {ps.crc_us_factor}")
    print(f"Coated US: {ps.coated_us_factor}")
    print(f"HRC EU: {ps.hrc_eu_factor}")
    print(f"OCTG: {ps.octg_factor}")
    print(f"Annual Growth: {ps.annual_price_growth}")

    # Volume factors
    print(f"Flat-Rolled: {vs.flat_rolled_volume_factor}")
    print(f"Mini Mill: {vs.mini_mill_volume_factor}")
    print(f"USSE: {vs.usse_volume_factor}")
    print(f"Tubular: {vs.tubular_volume_factor}")
```

---

## 2. WACC Verification and Audit Trail

### Check WACC Module Status
```python
from price_volume_model import (
    WACC_MODULE_AVAILABLE,
    get_verified_uss_wacc,
    get_verified_nippon_wacc,
    get_wacc_module_status
)

# Quick status check
status = get_wacc_module_status()
print(f"Module Available: {status['available']}")
print(f"USS WACC: {status['uss_wacc']}")
print(f"Nippon USD WACC: {status['nippon_usd_wacc']}")

# Full audit trail
uss_wacc, uss_audit = get_verified_uss_wacc()
# uss_audit contains: data_as_of_date, inputs (with sources), analyst_comparison

jpy_wacc, usd_wacc, nippon_audit = get_verified_nippon_wacc()
# nippon_audit contains: data_as_of_date, inputs (with sources)
```

### WACC Data Sources (for documentation)

**USS WACC Inputs:**
| Input | Source |
|-------|--------|
| Risk-Free Rate | Federal Reserve H.15 Statistical Release |
| Levered Beta | Consensus, aligned with fairness opinions |
| Equity Risk Premium | Duff & Phelps Cost of Capital |
| Size Premium | Duff & Phelps Size Premium Study |
| Pre-tax Cost of Debt | Weighted average of USS debt instruments |
| Market Cap / Debt | USS 10-K, NYSE market data |

**Nippon WACC Inputs:**
| Input | Source |
|-------|--------|
| Japan Risk-Free Rate | Bank of Japan / Ministry of Finance |
| US 10-Year Treasury | Federal Reserve H.15 |
| Beta | Bloomberg vs TOPIX |
| Japan ERP | Duff & Phelps / Damodaran |
| Capital Structure | Tokyo Stock Exchange, Nippon Annual Report |

---

## 3. Exporting Markdown to PDF (using WeasyPrint)

### Basic Export
```python
import markdown
from weasyprint import HTML
from pathlib import Path

md_path = Path('documentation/SCENARIO_RATIONALE.md')
md_content = md_path.read_text()

# Convert markdown to HTML
html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc'])

# Wrap in HTML document with CSS
html_doc = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ margin: 0.75in; }}
        body {{ font-family: sans-serif; font-size: 10pt; line-height: 1.5; }}
        h1 {{ font-size: 20pt; color: #1a365d; border-bottom: 2px solid #1a365d; }}
        h2 {{ font-size: 16pt; color: #2c5282; }}
        h3 {{ font-size: 13pt; color: #2d3748; }}
        table {{ border-collapse: collapse; width: 100%; font-size: 9pt; page-break-inside: avoid; }}
        th, td {{ border: 1px solid #cbd5e0; padding: 6px 8px; }}
        th {{ background-color: #edf2f7; font-weight: 600; }}
        pre {{ background-color: #2d3748; color: #e2e8f0; padding: 12px; font-size: 9pt; }}
        code {{ background-color: #edf2f7; padding: 2px 4px; font-family: monospace; }}
    </style>
</head>
<body>{html_body}</body>
</html>
"""

# Export to PDF
HTML(string=html_doc).write_pdf('output.pdf')
```

### Page Numbers (optional)
Add to `@page` CSS:
```css
@page {
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}
```

---

## 4. Exporting Markdown to Word (.docx)

### Using python-docx
```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re

doc = Document()

# Set default font
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

# Add heading
p = doc.add_paragraph()
run = p.add_run("Heading Text")
run.bold = True
run.font.size = Pt(16)
run.font.color.rgb = RGBColor(44, 82, 130)

# Add table
table = doc.add_table(rows=2, cols=3)
table.style = 'Table Grid'
# Set header row shading
for cell in table.rows[0].cells:
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), 'E8E8E8')
    cell._tc.get_or_add_tcPr().append(shading)

# Add list items
doc.add_paragraph("Item 1", style='List Bullet')
doc.add_paragraph("Item 2", style='List Number')

doc.save('output.docx')
```

---

## 5. Key File Locations

| File | Purpose |
|------|---------|
| `price_volume_model.py` | Main valuation model with all scenarios |
| `wacc-calculations/` | WACC calculation module with audit trails |
| `documentation/SCENARIO_RATIONALE.md` | Main scenario rationale document |
| `documentation/SCENARIO_RATIONALE.pdf` | PDF export |
| `documentation/SCENARIO_RATIONALE.docx` | Word export |

---

## 6. Current Model Values (as of February 2026)

| Scenario | USS Value | Nippon Value | Probability |
|----------|-----------|--------------|-------------|
| Severe Downturn | $0.00 | $2.03 | 25% |
| Downside | $19.25 | $28.51 | 30% |
| Base Case | $39.61 | $56.41 | 30% |
| Above Average | $70.10 | $97.63 | 10% |
| Optimistic | $98.68 | $138.27 | 5% |
| Wall Street | $54.52 | $74.55 | - |
| NSA Mandated CapEx | $49.18 | $103.09 | - |

**Probability-Weighted:**
- Expected USS Standalone: $29.60/share
- Expected Nippon Value: $42.66/share
- Nippon Offer: $55.00/share
- Premium to Risk-Adjusted Value: +86%

**WACC Values:**
- USS Base WACC: 10.70% (from wacc-calculations module)
- Nippon USD WACC: 7.95% (IRP-adjusted)

---

## 7. Quick Commands

### Run model comparison
```bash
cd /workspaces/claude-in-docker/FinancialModel
python3 -c "from price_volume_model import *; ..."
```

### Export to PDF
```bash
python3 << 'EOF'
import markdown
from weasyprint import HTML
# ... (see section 3)
EOF
```

### Export to Word
```bash
python3 << 'EOF'
from docx import Document
# ... (see section 4)
EOF
```

---

*Last Updated: February 2026*
