# 📊 DCF Multi-Stage Valuation — Streamlit Interactive App

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Engineering the traditional Excel-based DCF workflow into a programmatic valuation tool** — replacing manual, opaque, single-point estimates with automated, auditable, multi-dimensional analysis.

> 🚀 **Live Demo**: [Hugging Face Spaces](https://huggingface.co/spaces/guliguliguigui/dcf-valuation)

---

## ✨ Features

### 🔬 Core Valuation
- **Two-stage DCF model**: high-growth period + Gordon Growth perpetuity, fully vectorized with NumPy
- **WACC calculator**: integrated CAPM model with waterfall chart for cost-of-capital decomposition
- **Input validation**: automatic guardrails (e.g., g ≥ WACC, FCF ≤ 0) with descriptive errors rather than silent failures

### 📈 Sensitivity Analysis
- **Tornado chart**: impact ranking of each parameter at ±30% perturbation
- **Dual-parameter heatmap**: interactive X/Y parameter selection with contour overlays
- **Continuous sensitivity curves**: observe valuation response as a single parameter varies

### 🎯 Scenario Analysis
- Three preset scenarios: Bull / Base / Bear
- Outputs valuation **ranges** rather than point estimates
- Terminal value warning highlight when TV exceeds 80% of intrinsic value

### 📁 Batch Excel Valuation
- Upload one spreadsheet, value multiple companies in one run
- **Intelligent column-name mapping**: auto-detects Chinese/English headers
- Row-level error isolation — one bad row won't block the rest
- Results exportable as Excel/CSV with comparison bar charts

### 📄 Report Export
- One-click **PDF valuation report** generation (fpdf2, Chinese text supported)
- Includes parameter summary, valuation results, cash flow breakdown, and scenario comparison

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

---

## 🏗️ Architecture

```
streamlit_app.py                     # Single-file app (~50KB)
├── DCFParams / DCFResult            # Core data structures (dataclass)
├── dcf_valuation()                  # Multi-stage DCF (NumPy vectorization)
├── dcf_valuation_batch()            # Batch valuation engine
├── calc_wacc() / calc_cost_of_equity()  # WACC & CAPM
├── sensitivity_analysis()           # Single-parameter sensitivity
├── sensitivity_heatmap()            # Dual-parameter sensitivity matrix
├── scenario_analysis()              # Multi-scenario comparison
├── generate_pdf_report()            # PDF report (fpdf2)
├── map_columns()                    # Smart Excel column-name mapping
├── Plotly chart functions           # Tornado / heatmap / waterfall / pie / line
└── Streamlit UI                     # Sidebar + 3-mode page layout
```

**Core dependencies**: Streamlit · Pandas · NumPy · Plotly · openpyxl · fpdf2

---

## 📊 Valuation Formulas

### Two-Stage DCF

$$V_0 = \sum_{t=1}^{n} \frac{FCF_0 \cdot (1+g_1)^t}{(1+WACC)^t} + \frac{FCF_n \cdot (1+g_\infty)}{(WACC - g_\infty) \cdot (1+WACC)^n}$$

- Left term: present value of explicit high-growth cash flows
- Right term: terminal value discounted to present (Gordon Growth Model)

### WACC

$$WACC = \frac{E}{V} \cdot R_e + \frac{D}{V} \cdot R_d \cdot (1-T)$$

### CAPM

$$R_e = R_f + \beta \cdot (R_m - R_f)$$

---

## 📝 License

MIT License. Not financial advice.

---

<p align="center">
  <sub>Built with Python, Streamlit, Plotly & fpdf2</sub>
</p>
