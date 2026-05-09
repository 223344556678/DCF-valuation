# 📊 DCF 多阶段估值模型 — Streamlit 交互式应用

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**专业级贴现现金流 (DCF) 估值工具** — 支持多阶段增长模型、敏感性分析、情景分析、批量 Excel 估值、WACC 计算和 PDF 报告导出。

## ✨ 功能特性

### 🔬 核心估值
- **多阶段 DCF 模型**：高增长期 + 永续期，向量化计算
- **WACC 计算器**：集成 CAPM 模型，瀑布图分解成本构成
- **参数校验**：自动检测无效输入（如 g ≥ WACC、FCF ≤ 0）

### 📈 敏感性分析
- **龙卷风图**：一目了然各参数 ±30% 对估值的影响排序
- **双参数热力图**：交互式选择 X/Y 参数，带等高线标注
- **单参数敏感性曲线**：观察参数连续变化对估值的影响

### 🎯 情景分析
- 预设 乐观 / 基准 / 悲观 三种情景
- 对比柱状图 + 明细表格
- 终值占比预警（>80% 时高亮提示）

### 📁 批量 Excel 估值
- 上传 Excel 一键估值多家公司
- **智能列名识别**：自动映射中/英文列名 (`fcf0` ↔ `自由现金流`, `discount_rate` ↔ `折现率`)
- 校验失败行自动跳过并提示原因
- 结果 Excel/CSV 导出 + 对比柱状图

### 📄 专业报告
- 一键下载 **PDF 估值报告**（支持中文）
- 包含：参数摘要、估值结果、现金流明细、情景分析
- CSV 数据导出

### 🎨 用户体验
- 专业金融配色主题
- 响应式指标卡片 + 终值占比颜色预警
- 可折叠的业务说明引导
- 全 Plotly 交互式图表（缩放、悬停、下载）

## 🚀 快速开始

### 安装

```bash
pip install -r requirements_dcf.txt
```

### 运行

```bash
streamlit run streamlit_app.py
```

访问 `http://localhost:8501` 即可使用。

## 📖 使用方法

### 1. 单公司估值
1. 在侧边栏设置估值参数（FCF₀、增长率、折现率等）
2. 查看内在价值、终值占比等核心指标
3. 切换标签页查看敏感性分析、情景分析
4. 点击「下载 PDF 报告」导出专业报告

### 2. 批量 Excel 估值
1. 点击「下载模板」获取标准格式 Excel
2. 填入多家公司的估值参数（列名支持中英文）
3. 上传后自动识别列名并批量计算
4. 下载估值结果 Excel/CSV

### 3. WACC 计算器
1. 在侧边栏输入资本结构参数
2. 左侧展示 CAPM 理论权益成本
3. 右侧计算实际 WACC 并显示瀑布分解图
4. 将结果填入折现率用于 DCF 估值

## 🏗️ 技术架构

```
streamlit_app.py                    # 单文件 Streamlit 应用
├── DCFParams / DCFResult           # 核心数据结构 (dataclass)
├── dcf_valuation()                 # 多阶段 DCF 估值（numpy 向量化）
├── dcf_valuation_batch()           # 批量估值
├── calc_wacc() / calc_cost_of_equity()  # WACC & CAPM
├── sensitivity_analysis()          # 单参数敏感性
├── sensitivity_heatmap()           # 双参数敏感性矩阵
├── scenario_analysis()             # 多情景分析
├── generate_pdf_report()           # PDF 报告 (fpdf2)
├── map_columns()                   # Excel 列名智能映射
├── Plotly 图表函数                 # 龙卷风图 / 热力图 / 瀑布图 / 饼图 / 折线图
└── Streamlit UI                    # 侧边栏 + 3 种模式页面
```

## 📊 估值模型公式

### DCF 核心公式

$$V_0 = \sum_{t=1}^{n} \frac{FCF_0 \cdot (1+g_1)^t}{(1+WACC)^t} + \frac{FCF_n \cdot (1+g_\infty)}{(WACC - g_\infty) \cdot (1+WACC)^n}$$

- **高增长期现值** (左项)：未来 n 年高速增长现金流的折现
- **永续期现值** (右项)：Gordon 增长模型计算的终值折现

### WACC 加权平均资本成本

$$WACC = \frac{E}{V} \cdot R_e + \frac{D}{V} \cdot R_d \cdot (1-T)$$

### CAPM 权益成本

$$R_e = R_f + \beta \cdot (R_m - R_f)$$

## 📝 使用许可

MIT License — 自由使用、修改和分发。仅供研究和教育目的，不构成投资建议。

---

<p align="center">
  <sub>Built with ❤️ using Python, Streamlit, Plotly & fpdf2</sub>
</p>
