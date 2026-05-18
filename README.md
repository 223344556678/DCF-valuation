# 📊 DCF Multi-Stage Valuation — Streamlit 交互式应用

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**将传统 Excel 估值流程工程化的交互式工具** — 把手工 DCF 建模中效率低、假设不透明、风险分析不足的问题用代码解决，让估值从单点估计升级为多维分析决策。

> 🚀 **Live Demo**: [Streamlit Cloud](https://dcf-valuation-hxbm8jxqvbmdctnxrxbv3a.streamlit.app/)

English version: [README_EN.md](README_EN.md)

---

## ✨ 功能特性

### 🔬 核心估值引擎
- **多阶段 DCF 模型**：高增长期 + 永续期（Gordon Growth），NumPy 向量化计算
- **WACC 计算器**：内置 CAPM 模型，瀑布图分解资本成本构成
- **输入校验**：自动拦截无效参数（g ≥ WACC、FCF ≤ 0 等），提示错误原因而非静默失败

### 📈 敏感性分析
- **龙卷风图**：各参数 ±30% 扰动对内在价值的影响排序
- **双参数热力图**：交互式选择 X/Y 参数，等高线叠加，定位关键驱动因子
- **连续敏感性曲线**：观察单参数连续变化时估值响应

### 🎯 情景分析
- 预设 乐观 / 基准 / 悲观 三情景
- 输出估值范围而非单点估计
- 终值占比预警：当终值超过内在价值 80% 时高亮提醒

### 📁 批量 Excel 估值
- 上传一张表，一键估值多家公司
- **智能列名识别**：自动映射中/英文列名（`fcf0` ↔ `自由现金流`）
- 逐行校验，错误隔离——单行失败不影响其他行计算
- 结果导出 Excel/CSV + 对比柱状图

### 📄 报告导出
- 一键生成 **PDF 估值报告**（fpdf2，支持中文）
- 包含参数摘要、估值结果、现金流明细、情景分析

---

## 🚀 快速开始

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

访问 `http://localhost:8501`。

---

## 🏗️ 技术架构

```
streamlit_app.py                     # 单文件应用（~50KB）
├── DCFParams / DCFResult            # 参数 & 结果数据类 (dataclass)
├── dcf_valuation()                  # 多阶段 DCF 估值（NumPy 向量化）
├── dcf_valuation_batch()            # 批量估值引擎
├── calc_wacc() / calc_cost_of_equity()  # WACC & CAPM 计算
├── sensitivity_analysis()           # 单参数敏感性
├── sensitivity_heatmap()            # 双参数敏感性矩阵
├── scenario_analysis()              # 多情景对比
├── generate_pdf_report()            # PDF 报告生成 (fpdf2)
├── map_columns()                    # Excel 智能列名映射
├── Plotly 图表集合                   # 龙卷风图 / 热力图 / 瀑布图 / 饼图 / 折线图
└── Streamlit UI                     # 侧边栏 + 3 模式切换
```

**核心依赖**：Streamlit · Pandas · NumPy · Plotly · openpyxl · fpdf2

---

## 📊 估值公式

### DCF 两阶段模型

$$V_0 = \sum_{t=1}^{n} \frac{FCF_0 \cdot (1+g_1)^t}{(1+WACC)^t} + \frac{FCF_n \cdot (1+g_\infty)}{(WACC - g_\infty) \cdot (1+WACC)^n}$$

- 左项：高增长期现金流折现（显式预测期）
- 右项：永续期终值折现（Gordon Growth Model）

### WACC

$$WACC = \frac{E}{V} \cdot R_e + \frac{D}{V} \cdot R_d \cdot (1-T)$$

### CAPM

$$R_e = R_f + \beta \cdot (R_m - R_f)$$

---

## 📝 License

MIT License — 不构成投资建议。

---

<p align="center">
  <sub>Built with Python, Streamlit, Plotly & fpdf2</sub>
</p>
