"""
多阶段 DCF 估值模型 — Streamlit 交互式应用
支持: 单公司估值 / 敏感性分析 / 情景分析 / 批量 Excel 估值 / WACC 计算 / PDF 报告导出
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from io import BytesIO
import os
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title='DCF 估值模型', page_icon='📊', layout='wide')

# ============================================================
# 0. 自定义 CSS 美化
# ============================================================

st.markdown("""
<style>
    /* 整体字体 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', 'Microsoft YaHei', 'PingFang SC', sans-serif;
    }

    /* 主色调变量 */
    :root {
        --primary: #1e3a5f;
        --accent: #2e86de;
        --success: #10ac84;
        --warning: #f3684c;
        --bg-light: #f8f9fb;
    }

    /* 卡片容器 */
    .dcf-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
        border: 1px solid #e8ecf1;
        margin-bottom: 0.75rem;
    }
    .dcf-card h3 {
        color: #1e3a5f;
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    .dcf-card p, .dcf-card li {
        font-size: 0.9rem;
        color: #4a5568;
        line-height: 1.6;
    }

    /* 业务说明 callout */
    .dcf-callout {
        background: linear-gradient(135deg, #eef2ff 0%, #e8f0fe 100%);
        border-left: 4px solid #2e86de;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.9rem;
        color: #2d3748;
    }
    .dcf-callout strong {
        color: #1e3a5f;
    }

    /* Metric 卡片增强 */
    [data-testid="stMetricValue"] {
        font-weight: 700;
        color: #1e3a5f;
    }
    [data-testid="stMetricLabel"] {
        font-weight: 500;
        color: #718096;
    }

    /* 按钮 */
    .stDownloadButton button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stDownloadButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(46,134,222,0.3);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fb 0%, #edf2f7 100%);
    }
    [data-testid="stSidebar"] .stRadio label {
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 1. 核心数据结构
# ============================================================

@dataclass
class DCFParams:
    """DCF 估值参数"""
    fcf0: float
    high_growth_rate: float = 0.15
    high_growth_years: int = 5
    stable_growth_rate: float = 0.03
    discount_rate: float = 0.12

    def __post_init__(self):
        if self.fcf0 <= 0:
            raise ValueError(f'基期 FCF 必须 > 0，当前值: {self.fcf0}')
        if not 0 < self.discount_rate < 1:
            raise ValueError(f'折现率需在 (0, 1) 区间，当前值: {self.discount_rate}')
        if self.stable_growth_rate >= self.discount_rate:
            raise ValueError('永续增长率必须 < 折现率，否则终值公式发散')
        if self.high_growth_years < 1:
            raise ValueError(f'高增长年数必须 >= 1，当前值: {self.high_growth_years}')


@dataclass
class DCFResult:
    """DCF 估值结果"""
    intrinsic_value: float
    terminal_value: float
    pv_high_growth: float
    pv_terminal: float
    cash_flows: List[float] = field(repr=False)
    pv_cash_flows: List[float] = field(repr=False)


# ============================================================
# 2. DCF 核心函数
# ============================================================

def dcf_valuation(params: DCFParams) -> DCFResult:
    """多阶段 DCF 估值（向量化计算）"""
    p = params
    t = np.arange(1, p.high_growth_years + 1)
    fcf_high = p.fcf0 * (1 + p.high_growth_rate) ** t
    discount_factors = (1 + p.discount_rate) ** t
    pv_high = fcf_high / discount_factors
    pv_high_growth = pv_high.sum()

    terminal_fcf = fcf_high[-1] * (1 + p.stable_growth_rate)
    terminal_value = terminal_fcf / (p.discount_rate - p.stable_growth_rate)
    pv_terminal = terminal_value / discount_factors[-1]

    return DCFResult(
        intrinsic_value=pv_high_growth + pv_terminal,
        terminal_value=terminal_value,
        pv_high_growth=pv_high_growth,
        pv_terminal=pv_terminal,
        cash_flows=fcf_high.tolist(),
        pv_cash_flows=pv_high.tolist()
    )


def dcf_valuation_batch(params_list: List[DCFParams]) -> np.ndarray:
    """批量估值"""
    n = len(params_list)
    results = np.zeros(n)
    for i in range(n):
        p = params_list[i]
        t = np.arange(1, p.high_growth_years + 1)
        fcf = p.fcf0 * (1 + p.high_growth_rate) ** t
        pv = np.sum(fcf / (1 + p.discount_rate) ** t)
        terminal_fcf = fcf[-1] * (1 + p.stable_growth_rate)
        terminal_value = terminal_fcf / (p.discount_rate - p.stable_growth_rate)
        pv_terminal = terminal_value / (1 + p.discount_rate) ** p.high_growth_years
        results[i] = pv + pv_terminal
    return results


# ============================================================
# 3. WACC 计算
# ============================================================

def calc_cost_of_equity(risk_free_rate=0.03, beta=1.0, market_premium=0.07) -> float:
    """CAPM: Re = Rf + β × (Rm - Rf)"""
    return risk_free_rate + beta * market_premium


def calc_wacc(equity_ratio=0.7, debt_ratio=0.3, cost_of_equity=0.10,
              cost_of_debt=0.05, tax_rate=0.25) -> float:
    """WACC = E/V × Re + D/V × Rd × (1 - T)"""
    total = equity_ratio + debt_ratio
    if abs(total - 1.0) > 0.01:
        raise ValueError(f'权益比例 + 债务比例应 ≈ 1.0，当前合计: {total:.2f}')
    return equity_ratio * cost_of_equity + debt_ratio * cost_of_debt * (1 - tax_rate)


# ============================================================
# 4. 敏感性分析
# ============================================================

def sensitivity_analysis(base_params: DCFParams, param_name: str,
                         range_pct=(-0.3, 0.3), steps=21) -> pd.DataFrame:
    """单参数敏感性分析"""
    base_val = getattr(base_params, param_name)
    multipliers = np.linspace(1 + range_pct[0], 1 + range_pct[1], steps)

    records = []
    for mult in multipliers:
        new_val = base_val * mult if param_name != 'high_growth_years' else int(round(base_val * mult))
        if param_name == 'high_growth_years' and new_val < 1:
            new_val = 1
        kwargs = base_params.__dict__.copy()
        kwargs[param_name] = new_val
        try:
            result = dcf_valuation(DCFParams(**kwargs))
            records.append({
                '参数值': round(new_val, 4) if param_name != 'high_growth_years' else new_val,
                '变动幅度': f'{mult - 1:+.1%}',
                '企业价值': round(result.intrinsic_value, 2),
                '终值': round(result.terminal_value, 2)
            })
        except ValueError:
            continue
    return pd.DataFrame(records)


def sensitivity_heatmap(base_params: DCFParams, x_param='discount_rate',
                        y_param='stable_growth_rate',
                        x_range=(-0.3, 0.3), y_range=(-0.3, 0.3), steps=15):
    """双参数敏感性矩阵"""
    x_base = getattr(base_params, x_param)
    y_base = getattr(base_params, y_param)
    x_vals = np.linspace(x_base * (1 + x_range[0]), x_base * (1 + x_range[1]), steps)
    y_vals = np.linspace(y_base * (1 + y_range[0]), y_base * (1 + y_range[1]), steps)
    Z = np.zeros((steps, steps))
    for i, yv in enumerate(y_vals):
        for j, xv in enumerate(x_vals):
            kwargs = base_params.__dict__.copy()
            kwargs[x_param] = xv
            kwargs[y_param] = yv
            try:
                res = dcf_valuation(DCFParams(**kwargs))
                Z[i, j] = res.intrinsic_value
            except ValueError:
                Z[i, j] = np.nan
    return x_vals, y_vals, Z


# ============================================================
# 5. 情景分析
# ============================================================

def scenario_analysis(base_params: DCFParams, scenarios=None) -> pd.DataFrame:
    """多情景分析"""
    if scenarios is None:
        scenarios = {
            '乐观 😊': {
                'high_growth_rate': base_params.high_growth_rate * 1.3,
                'stable_growth_rate': base_params.stable_growth_rate * 1.3,
                'discount_rate': base_params.discount_rate * 0.85
            },
            '基准 📊': {},
            '悲观 😟': {
                'high_growth_rate': base_params.high_growth_rate * 0.7,
                'stable_growth_rate': base_params.stable_growth_rate * 0.7,
                'discount_rate': base_params.discount_rate * 1.15
            }
        }

    records = []
    for name, overrides in scenarios.items():
        kwargs = base_params.__dict__.copy()
        kwargs.update(overrides)
        try:
            result = dcf_valuation(DCFParams(**kwargs))
            records.append({
                '情景': name,
                '企业价值 (万元)': round(result.intrinsic_value, 2),
                '永续终值 (万元)': round(result.terminal_value, 2),
                '高增长现值 (万元)': round(result.pv_high_growth, 2),
                '终值占比': f'{result.pv_terminal / result.intrinsic_value:.1%}'
            })
        except ValueError as e:
            records.append({'情景': name, '错误': str(e)})
    return pd.DataFrame(records)


# ============================================================
# 6. Plotly 可视化 (增强版)
# ============================================================

PARAM_LABELS = {
    'fcf0': '基期 FCF',
    'high_growth_rate': '高增长率',
    'high_growth_years': '高增长年数',
    'stable_growth_rate': '永续增长率',
    'discount_rate': '折现率 (WACC)'
}

FCF_COLOR = '#2e86de'
TV_COLOR = '#e74c3c'
GREEN = '#10ac84'
BLUE = '#2e86de'
RED = '#e74c3c'
NAVY = '#1e3a5f'


def plot_tornado(base_params: DCFParams) -> go.Figure:
    """龙卷风图：各参数 ±30% 对企业价值的影响"""
    base_result = dcf_valuation(base_params)
    base_value = base_result.intrinsic_value

    impacts = []
    for key, label in PARAM_LABELS.items():
        df = sensitivity_analysis(base_params, key)
        if df.empty:
            continue
        v_min = df['企业价值'].min()
        v_max = df['企业价值'].max()
        low_change = v_min - base_value
        high_change = v_max - base_value
        impacts.append((label, low_change, high_change, abs(high_change - low_change)))

    impacts.sort(key=lambda x: x[3])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[x[0] for x in impacts],
        x=[x[2] for x in impacts],
        orientation='h', name='上调 30%',
        marker=dict(color=RED, opacity=0.85, line=dict(color='#c0392b', width=0.5)),
        hovertemplate='%{y}: +%{x:,.0f} 万元<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        y=[x[0] for x in impacts],
        x=[x[1] for x in impacts],
        orientation='h', name='下调 30%',
        marker=dict(color=BLUE, opacity=0.85, line=dict(color='#2471a3', width=0.5)),
        hovertemplate='%{y}: %{x:,.0f} 万元<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text=f'敏感性龙卷风图（基准价值: {base_value:,.0f} 万元）', font=dict(color=NAVY, size=14)),
        xaxis_title='企业价值变动（万元）',
        barmode='relative',
        height=420,
        margin=dict(l=130, r=30, t=50, b=30),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        plot_bgcolor='#f8f9fb',
        paper_bgcolor='#ffffff'
    )
    fig.add_vline(x=0, line_width=1.5, line_color='#2d3748', line_dash='solid')
    return fig


def plot_heatmap(x_vals, y_vals, Z, x_label, y_label) -> go.Figure:
    """双参数敏感性热力图"""
    fig = go.Figure(data=go.Heatmap(
        x=x_vals, y=y_vals, z=Z,
        colorscale=[
            [0, '#e74c3c'], [0.25, '#f39c12'], [0.5, '#f7dc6f'],
            [0.75, '#58d68d'], [1, '#27ae60']
        ],
        colorbar=dict(
            title='企业价值 (万元)', title_font=dict(color=NAVY),
            tickformat=',.0f'
        ),
        hovertemplate=f'{x_label}: %{{x:.4f}}<br>{y_label}: %{{y:.4f}}<br>企业价值: %{{z:,.0f}} 万元<extra></extra>',
        contours=dict(
            coloring='lines', showlines=True, showlabels=True,
            labelfont=dict(size=9, color='white'),
            start=np.nanmin(Z), end=np.nanmax(Z), size=(np.nanmax(Z) - np.nanmin(Z)) / 8
        )
    ))
    fig.update_layout(
        title=dict(text='双参数敏感性分析', font=dict(color=NAVY, size=14)),
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=520,
        margin=dict(l=80, r=30, t=50, b=60),
        plot_bgcolor='#f8f9fb'
    )
    return fig


def plot_waterfall_pie(result: DCFResult) -> go.Figure:
    """现金流折现柱状图 + 价值构成饼图"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(
            f'<b>高增长期现金流</b>',
            f'<b>价值构成（合计 {result.intrinsic_value:,.0f} 万元）</b>'
        ),
        specs=[[{'type': 'xy'}, {'type': 'domain'}]],
        column_widths=[0.55, 0.45]
    )

    years_str = [f'第{y}年' for y in range(1, len(result.cash_flows) + 1)]

    fig.add_trace(go.Bar(
        x=years_str, y=result.cash_flows,
        name='预期 FCF', marker_color=GREEN, opacity=0.85,
        hovertemplate='%{x}: %{y:,.0f} 万元<extra></extra>'
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=years_str, y=result.pv_cash_flows,
        name='折现 FCF', marker_color=BLUE, opacity=0.85,
        hovertemplate='%{x}: %{y:,.0f} 万元<extra></extra>'
    ), row=1, col=1)

    fig.add_trace(go.Pie(
        labels=['高增长期现值', '永续期现值'],
        values=[result.pv_high_growth, result.pv_terminal],
        marker_colors=[BLUE, RED],
        textinfo='label+percent',
        textfont=dict(size=11),
        hole=0.35,
        hovertemplate='%{label}: %{value:,.0f} 万元 (%{percent})<extra></extra>'
    ), row=1, col=2)

    fig.update_layout(
        height=420, margin=dict(l=20, r=20, t=50, b=30),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.3),
        plot_bgcolor='#f8f9fb', paper_bgcolor='#ffffff'
    )
    return fig


def plot_sensitivity_line(base_params: DCFParams, param_name: str) -> go.Figure:
    """单参数敏感性折线图"""
    df = sensitivity_analysis(base_params, param_name)
    if df.empty:
        return go.Figure()

    base_val = getattr(base_params, param_name)
    label = PARAM_LABELS.get(param_name, param_name)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['参数值'], y=df['企业价值'],
        mode='lines+markers',
        line=dict(color=BLUE, width=2.5),
        marker=dict(size=6, color=BLUE),
        name='企业价值',
        hovertemplate=f'{label}: %{{x:.4f}}<br>企业价值: %{{y:,.0f}} 万元<extra></extra>'
    ))

    fig.add_vline(x=base_val, line_dash='dash', line_color=NAVY, line_width=1.5,
                  annotation_text=f'当前: {base_val:.4f}', annotation_position='top')

    fig.update_layout(
        title=dict(text=f'{label} 敏感性分析', font=dict(color=NAVY, size=14)),
        xaxis_title=label,
        yaxis_title='企业价值 (万元)',
        height=380, margin=dict(l=20, r=20, t=50, b=30),
        plot_bgcolor='#f8f9fb'
    )
    return fig


def plot_scenario_bars(scenario_df: pd.DataFrame) -> go.Figure:
    """情景分析柱状图"""
    valid = scenario_df[~scenario_df['情景'].astype(str).str.contains('错误')]
    if valid.empty:
        return go.Figure()

    colors = {'乐观': GREEN, '基准': BLUE, '悲观': RED}
    bar_colors = [colors.get(n.split()[0], BLUE) for n in valid['情景']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valid['情景'], y=valid['企业价值 (万元)'],
        marker_color=bar_colors, opacity=0.85,
        text=[f'{v:,.0f} 万元' for v in valid['企业价值 (万元)']],
        textposition='outside',
        hovertemplate='%{x}: %{y:,.0f} 万元<extra></extra>'
    ))

    fig.update_layout(
        title=dict(text='多情景企业价值对比', font=dict(color=NAVY, size=14)),
        yaxis_title='企业价值 (万元)',
        height=400, margin=dict(l=20, r=20, t=50, b=30),
        plot_bgcolor='#f8f9fb', showlegend=False
    )
    return fig


def plot_batch_comparison(result_df: pd.DataFrame) -> go.Figure:
    """批量估值对比图"""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=result_df['公司名称'], y=result_df['当前FCF (万元)'],
        name='当前 FCF', marker_color=BLUE, opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=result_df['公司名称'], y=result_df['内在价值 (万元)'],
        name='内在价值', marker_color=RED, opacity=0.85
    ))
    fig.update_layout(
        title=dict(text='多公司 DCF 估值对比', font=dict(color=NAVY, size=14)),
        yaxis_title='万元', height=450,
        margin=dict(l=20, r=20, t=50, b=30),
        barmode='group', plot_bgcolor='#f8f9fb'
    )
    return fig


# ============================================================
# 7. PDF 报告生成
# ============================================================

def find_chinese_font():
    """查找系统可用的中文字体"""
    candidates = [
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simsun.ttc',
        'C:/Windows/Fonts/msyhbd.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def generate_pdf_report(params: DCFParams, result: DCFResult,
                        scenario_df: pd.DataFrame):
    """生成 PDF 估值报告，若 fpdf2 未安装则返回 None"""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # 注册中文字体
    font_path = find_chinese_font()
    if font_path:
        pdf.add_font('CJK', '', font_path, uni=True)
        pdf.add_font('CJK', 'B', font_path, uni=True)
        body_font = 'CJK'
    else:
        body_font = 'Helvetica'

    # === 标题 ===
    pdf.set_font(body_font, 'B', 20)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 14, 'DCF 估值报告', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.set_draw_color(46, 134, 222)
    pdf.set_line_width(0.6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    pdf.set_font(body_font, '', 9)
    pdf.set_text_color(113, 128, 150)
    pdf.cell(0, 6, f'生成日期: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}', new_x='LMARGIN', new_y='NEXT', align='R')
    pdf.ln(4)

    # === 估值参数 ===
    pdf.set_font(body_font, 'B', 13)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 10, '一、估值参数', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    param_rows = [
        ('基期自由现金流 (FCF₀)', f'{params.fcf0:,.0f} 万元'),
        ('高增长期增长率', f'{params.high_growth_rate:.1%}'),
        ('高增长年数', f'{params.high_growth_years} 年'),
        ('永续增长率', f'{params.stable_growth_rate:.1%}'),
        ('折现率 (WACC)', f'{params.discount_rate:.1%}'),
    ]

    pdf.set_font(body_font, '', 10)
    col_w = [80, 85]
    pdf.set_fill_color(248, 249, 251)
    for i, (label, val) in enumerate(param_rows):
        if i % 2 == 0:
            pdf.set_fill_color(245, 247, 250)
        pdf.cell(col_w[0], 8, f'  {label}', border=0)
        pdf.set_font(body_font, 'B', 10)
        pdf.cell(col_w[1], 8, val, new_x='LMARGIN', new_y='NEXT')
        pdf.set_font(body_font, '', 10)
    pdf.ln(6)

    # === 估值结果 ===
    pdf.set_font(body_font, 'B', 13)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 10, '二、估值结果', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    result_rows = [
        ('企业内在价值', f'{result.intrinsic_value:,.2f} 万元'),
        ('永续期终值', f'{result.terminal_value:,.2f} 万元'),
        ('高增长期现值', f'{result.pv_high_growth:,.2f} 万元'),
        ('永续期现值', f'{result.pv_terminal:,.2f} 万元'),
        ('终值占比', f'{result.pv_terminal / result.intrinsic_value:.1%}'),
    ]

    pdf.set_font(body_font, '', 10)
    for i, (label, val) in enumerate(result_rows):
        if i % 2 == 0:
            pdf.set_fill_color(245, 247, 250)
        pdf.cell(col_w[0], 8, f'  {label}', border=0)
        pdf.set_font(body_font, 'B', 10)
        if '价值' in label or '终值' in label:
            pdf.set_text_color(46, 134, 222)
        else:
            pdf.set_text_color(30, 58, 95)
        pdf.cell(col_w[1], 8, val, new_x='LMARGIN', new_y='NEXT')
        pdf.set_text_color(30, 58, 95)
        pdf.set_font(body_font, '', 10)
    pdf.ln(6)

    # === 现金流明细 ===
    pdf.set_font(body_font, 'B', 13)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 10, '三、高增长期现金流明细', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    pdf.set_font(body_font, 'B', 9)
    pdf.set_fill_color(30, 58, 95)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(28, 7, '  年份', border=0, fill=True)
    pdf.cell(42, 7, '预期 FCF', align='R', fill=True)
    pdf.cell(42, 7, '折现因子', align='R', fill=True)
    pdf.cell(42, 7, '折现 FCF', align='R', new_x='LMARGIN', new_y='NEXT', fill=True)
    pdf.set_text_color(30, 58, 95)

    pdf.set_font(body_font, '', 9)
    for i, (fcf, pv) in enumerate(zip(result.cash_flows, result.pv_cash_flows)):
        year = i + 1
        df = 1 / (1 + params.discount_rate) ** year
        if i % 2 == 0:
            pdf.set_fill_color(248, 249, 251)
        pdf.cell(28, 7, f'  第 {year} 年', fill=True)
        pdf.cell(42, 7, f'{fcf:,.0f}', align='R', fill=True)
        pdf.cell(42, 7, f'{df:.4f}', align='R', fill=True)
        pdf.cell(42, 7, f'{pv:,.0f}', align='R', new_x='LMARGIN', new_y='NEXT', fill=True)
    pdf.ln(6)

    # === 情景分析 ===
    pdf.set_font(body_font, 'B', 13)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(0, 10, '四、情景分析', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)

    if not scenario_df.empty and '错误' not in scenario_df.columns:
        cols = ['情景', '企业价值 (万元)', '终值占比']
        pdf.set_font(body_font, 'B', 9)
        pdf.set_fill_color(30, 58, 95)
        pdf.set_text_color(255, 255, 255)
        cw = [50, 60, 50]
        for j, col_name in enumerate(cols):
            pdf.cell(cw[j], 7, f'  {col_name}', fill=True)
        pdf.ln()
        pdf.set_text_color(30, 58, 95)

        pdf.set_font(body_font, '', 9)
        for i, (_, row) in enumerate(scenario_df.iterrows()):
            if i % 2 == 0:
                pdf.set_fill_color(248, 249, 251)
            pdf.cell(cw[0], 7, f'  {row[cols[0]]}', fill=True)
            pdf.cell(cw[1], 7, f'{row[cols[1]]:,.0f}', align='R', fill=True)
            pdf.cell(cw[2], 7, f'{row[cols[2]]}', align='R', new_x='LMARGIN', new_y='NEXT', fill=True)
    pdf.ln(8)

    # === 页脚 ===
    pdf.set_font(body_font, '', 8)
    pdf.set_text_color(160, 174, 192)
    pdf.cell(0, 5, '本报告由 DCF 估值模型自动生成 | 仅供参考，不构成投资建议', align='C')

    return pdf.output()


# ============================================================
# 8. 批量 Excel — 列名映射
# ============================================================

COLUMN_MAPPING = {
    'fcf0': ['fcf0', 'fcf', 'fcff', 'fcf_0', '基期fcf', '基期自由现金流', '自由现金流', 'FCF0', 'FCF', 'FCFF'],
    'high_growth_rate': ['high_growth_rate', 'growth_rate', 'growth', '高增长率', '高增长增长率', '增长率', 'g_high'],
    'high_growth_years': ['high_growth_years', 'years', 'n_years', '高增长年数', '高增长年限', '预测年数', '增长年数'],
    'stable_growth_rate': ['stable_growth_rate', 'terminal_growth', 'g_stable', '永续增长率', '终值增长率', 'stable_g'],
    'discount_rate': ['discount_rate', 'wacc', 'discount', '折现率', '贴现率', 'WACC', 'wacc'],
    'company_name': ['公司名称', '公司名', '名称', 'company', 'name', 'company_name', '企业名称', '股票名称', '简称'],
}


def map_columns(df: pd.DataFrame) -> Dict[str, str]:
    """自动映射 Excel 列名到标准列名"""
    mapping = {}
    df_cols_lower = {c.lower().strip(): c for c in df.columns}

    for std_name, aliases in COLUMN_MAPPING.items():
        for alias in aliases:
            if alias in df.columns:
                mapping[std_name] = alias
                break
            if alias.lower() in df_cols_lower:
                mapping[std_name] = df_cols_lower[alias.lower()]
                break

    found = list(mapping.keys())
    missing = [k for k in ['fcf0', 'high_growth_rate', 'high_growth_years',
                            'stable_growth_rate', 'discount_rate'] if k not in mapping]
    return mapping, missing, found


# ============================================================
# 9. Streamlit UI
# ============================================================

def build_params_from_session() -> DCFParams:
    """从 session_state 构建 DCFParams"""
    return DCFParams(
        fcf0=st.session_state.get('fcf0', 1000.0),
        high_growth_rate=st.session_state.get('high_growth_rate', 0.15),
        high_growth_years=st.session_state.get('high_growth_years', 5),
        stable_growth_rate=st.session_state.get('stable_growth_rate', 0.03),
        discount_rate=st.session_state.get('discount_rate', 0.12),
    )


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:0.5rem 0 0.25rem 0;">
            <h2 style="color:#1e3a5f; margin:0; font-size:1.3rem;">📊 DCF 估值模型</h2>
            <p style="color:#718096; font-size:0.8rem; margin:0.2rem 0 0 0;">多阶段贴现现金流估值工具</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        mode = st.radio(
            '📋 功能选择',
            ['🏢 单公司估值', '📁 批量 Excel 估值', '🔧 WACC 计算器'],
            key='mode'
        )

        st.divider()

        if '单公司估值' in mode or 'WACC' in mode:
            st.markdown('##### 📌 估值参数')

            fcf0 = st.number_input(
                '基期 FCF（万元）', min_value=0.01, value=1000.0, step=100.0,
                format='%.1f', key='fcf0',
                help='最近一个完整财年的公司自由现金流 (Free Cash Flow to Firm)'
            )

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                high_growth_rate = st.slider(
                    '高增长期增长率', 0.0, 50.0, 15.0, 1.0,
                    format='%d%%', key='high_growth_rate_slider',
                    help='未来几年的高速增长预期'
                ) / 100.0
                st.session_state['high_growth_rate'] = high_growth_rate

                stable_growth_rate = st.slider(
                    '永续增长率', 0.0, 10.0, 3.0, 0.5,
                    format='%.1f%%', key='stable_growth_rate_slider',
                    help='长期可持续增长率，通常接近 GDP 增速'
                ) / 100.0
                st.session_state['stable_growth_rate'] = stable_growth_rate

            with col_s2:
                high_growth_years = st.slider(
                    '高增长年数', 1, 20, 5, 1,
                    key='high_growth_years',
                    help='预计能维持高增长的年限'
                )
                discount_rate = st.slider(
                    '折现率 WACC', 1.0, 30.0, 12.0, 0.5,
                    format='%.1f%%', key='discount_rate_slider',
                    help='加权平均资本成本，反映风险水平'
                ) / 100.0
                st.session_state['discount_rate'] = discount_rate

            st.caption(f'当前: FCF₀={fcf0:,.0f}万 | g₁={high_growth_rate:.1%} '
                       f'| Y={high_growth_years} | g∞={stable_growth_rate:.1%} '
                       f'| WACC={discount_rate:.1%}')

        if 'WACC' in mode:
            st.divider()
            st.markdown('##### 🔧 WACC 参数')

            col_w1, col_w2 = st.columns(2)
            with col_w1:
                equity_ratio = st.slider('权益比例 (E/V)', 0.0, 1.0, 0.7, 0.05, key='eq_ratio')  # noqa: F841
                cost_of_equity = st.slider('权益成本 (Re)', 0.0, 30.0, 10.0, 0.5,  # noqa: F841
                                           format='%.1f%%', key='cost_eq',
                                           help='股东要求的回报率') / 100
            with col_w2:
                debt_ratio = st.slider('债务比例 (D/V)', 0.0, 1.0, 0.3, 0.05, key='debt_ratio')  # noqa: F841
                cost_of_debt = st.slider('债务成本 (Rd)', 0.0, 20.0, 5.0, 0.5,  # noqa: F841
                                         format='%.1f%%', key='cost_debt',
                                         help='借款利率') / 100

            tax_rate = st.slider('所得税率 (T)', 0.0, 50.0, 25.0, 1.0,  # noqa: F841
                                 format='%.0f%%', key='tax_rate',
                                 help='企业实际所得税率') / 100

            st.divider()
            st.markdown('##### 📈 CAPM 参数')
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                risk_free_rate = st.slider('无风险利率 (Rf)', 0.0, 10.0, 3.0, 0.5,  # noqa: F841
                                           format='%.1f%%', key='rf',
                                           help='通常取 10 年期国债收益率') / 100
            with col_c2:
                beta = st.slider('β 系数', 0.1, 3.0, 1.0, 0.1, key='beta',  # noqa: F841
                                 help='个股相对市场的波动性')
            market_premium = st.slider('市场风险溢价 (Rm-Rf)', 0.0, 15.0, 7.0, 0.5,  # noqa: F841
                                       format='%.1f%%', key='mrp',
                                       help='市场平均回报与无风险利率之差') / 100

        st.divider()
        st.caption('Powered by Streamlit + Plotly | v2.0')

    return mode


def render_business_context():
    """业务说明区"""
    with st.expander('📖 关于 DCF 估值模型 — 点击展开', expanded=False):
        col_a, col_b = st.columns([1, 1])

        with col_a:
            st.markdown("""
            <div class="dcf-card">
            <h3>什么是 DCF 估值？</h3>
            <p><strong>贴现现金流模型 (Discounted Cash Flow)</strong> 是最经典的绝对估值方法。
            其核心思想是：<strong>企业的内在价值等于其未来所有可产生的自由现金流的现值之和</strong>。</p>
            <ul>
                <li><strong>高增长期：</strong>未来 3-10 年内企业可维持高于行业平均的增速</li>
                <li><strong>永续期（终值）：</strong>高增长结束后，以稳定增长率永续增长</li>
                <li><strong>折现率 (WACC)：</strong>加权平均资本成本，将未来现金流折算到今天</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown("""
            <div class="dcf-card">
            <h3>如何解读结果？</h3>
            <ul>
                <li><strong>终值占比过高 (>80%)？</strong>说明估值严重依赖远期假设，不确定性大</li>
                <li><strong>敏感性分析：</strong>折现率是最敏感参数，±1% 的变化可能带来估值 ±10% 的波动</li>
                <li><strong>情景分析：</strong>乐观/悲观情景给出估值区间，而非单一数值</li>
                <li><strong>永续增长率</strong>通常不超过长期 GDP 增速（中国约 3-4%）</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="dcf-callout">
        <strong>📌 专业提示：</strong>DCF 估值的准确性取决于输入假设的质量。建议结合
        <strong>可比公司分析</strong>和<strong>先例交易分析</strong>交叉验证。
        估值是一门艺术，而不是精确科学 —— 结果应当作为<strong>价值区间</strong>的参考，而非精准的目标价。
        </div>
        """, unsafe_allow_html=True)


def render_single_company():
    """单公司估值页面"""
    render_business_context()

    try:
        params = build_params_from_session()
        result = dcf_valuation(params)
    except ValueError as e:
        st.error(f'⚠️ 参数校验失败: {e}')
        return

    # ---- 指标卡片 ----
    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('💰 企业内在价值', f'{result.intrinsic_value:,.0f} 万元')
    with col2:
        st.metric('🏁 永续终值', f'{result.terminal_value:,.0f} 万元')
    with col3:
        st.metric('📈 高增长期现值', f'{result.pv_high_growth:,.0f} 万元')
    with col4:
        terminal_pct = result.pv_terminal / result.intrinsic_value
        delta_color = 'inverse' if terminal_pct > 0.80 else 'normal'
        st.metric('📊 终值占比', f'{terminal_pct:.1%}',
                  delta='⚠️ 偏高' if terminal_pct > 0.80 else '正常',
                  delta_color=delta_color)

    if terminal_pct > 0.80:
        st.warning('终值占比超过 80%，估值对远期假设高度敏感，建议关注高增长期现金流的改善空间。')

    # ---- 操作按钮 ----
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
    with col_btn1:
        scenario_df = scenario_analysis(params)
        pdf_bytes = generate_pdf_report(params, result, scenario_df)
        if pdf_bytes is None:
            st.warning('PDF 报告需要 fpdf2 库，请运行: pip install fpdf2')
        else:
            st.download_button(
                '📄 下载 PDF 报告', data=pdf_bytes,
                file_name=f'DCF_Valuation_Report_{pd.Timestamp.now().strftime("%Y%m%d")}.pdf',
                mime='application/pdf',
            )
    with col_btn2:
        csv_data = BytesIO()
        summary = pd.DataFrame({
            '指标': ['企业内在价值', '永续终值', '高增长期现值', '永续期现值', '终值占比'],
            '数值': [
                f'{result.intrinsic_value:,.2f} 万元',
                f'{result.terminal_value:,.2f} 万元',
                f'{result.pv_high_growth:,.2f} 万元',
                f'{result.pv_terminal:,.2f} 万元',
                f'{terminal_pct:.1%}'
            ]
        })
        summary.to_csv(csv_data, index=False)
        st.download_button('📥 导出 CSV', data=csv_data.getvalue(),
                           file_name='dcf_result.csv', mime='text/csv')

    # ---- 标签页 ----
    tab1, tab2, tab3, tab4 = st.tabs(['📊 估值明细', '🎯 敏感性分析', '📋 情景分析', '📈 敏感性曲线'])

    with tab1:
        st.plotly_chart(plot_waterfall_pie(result), use_container_width=True)

        with st.expander('📋 各年现金流数据'):
            cf_df = pd.DataFrame({
                '年份': [f'第{i}年' for i in range(1, len(result.cash_flows) + 1)],
                '预期 FCF (万元)': [f'{v:,.0f}' for v in result.cash_flows],
                '折现因子': [f'{(1 / (1 + params.discount_rate) ** i):.4f}' for i in range(1, len(result.cash_flows) + 1)],
                '折现 FCF (万元)': [f'{v:,.0f}' for v in result.pv_cash_flows],
            })
            st.dataframe(cf_df, use_container_width=True, hide_index=True)

    with tab2:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.plotly_chart(plot_tornado(params), use_container_width=True)

        with col_right:
            st.markdown('##### 双参数热力图设置')
            x_param = st.selectbox(
                'X 轴参数',
                ['discount_rate', 'stable_growth_rate', 'high_growth_rate', 'fcf0'],
                index=0, format_func=lambda x: PARAM_LABELS.get(x, x), key='heat_x'
            )
            y_param = st.selectbox(
                'Y 轴参数',
                ['stable_growth_rate', 'discount_rate', 'high_growth_rate', 'fcf0'],
                index=0, format_func=lambda x: PARAM_LABELS.get(x, x), key='heat_y'
            )

            if x_param == y_param:
                st.warning('⚠️ 请选择两个不同的参数')
            else:
                try:
                    x_vals, y_vals, Z = sensitivity_heatmap(params, x_param=x_param, y_param=y_param)
                    st.plotly_chart(
                        plot_heatmap(x_vals, y_vals, Z,
                                     PARAM_LABELS.get(x_param, x_param),
                                     PARAM_LABELS.get(y_param, y_param)),
                        use_container_width=True
                    )
                except Exception:
                    st.info('该参数组合存在无法估值区域（如 g ≥ WACC），已自动跳过')

    with tab3:
        st.dataframe(scenario_df, use_container_width=True, hide_index=True)
        st.plotly_chart(plot_scenario_bars(scenario_df), use_container_width=True)

    with tab4:
        st.markdown('选择一个参数，查看其在不同取值下的企业价值变化曲线：')
        sel_param = st.selectbox(
            '选择参数', list(PARAM_LABELS.keys()),
            format_func=lambda x: PARAM_LABELS.get(x, x), key='line_param'
        )
        st.plotly_chart(plot_sensitivity_line(params, sel_param), use_container_width=True)


def render_batch_excel():
    """批量 Excel 估值页面"""
    st.markdown("""
    <div class="dcf-callout">
    <strong>📁 批量估值说明：</strong>上传 Excel 文件，系统自动识别列名（支持中英文），一次性完成多家公司 DCF 估值。
    下载模板可查看所需的列格式。
    </div>
    """, unsafe_allow_html=True)

    # ---- 模板下载 ----
    sample_data = pd.DataFrame({
        '公司名称': ['公司A', '公司B', '公司C', '公司D', '公司E'],
        'fcf0': [1000, 2500, 500, 8000, 300],
        'high_growth_rate': [0.15, 0.12, 0.20, 0.10, 0.18],
        'high_growth_years': [5, 4, 7, 5, 3],
        'stable_growth_rate': [0.03, 0.03, 0.04, 0.025, 0.03],
        'discount_rate': [0.12, 0.10, 0.14, 0.09, 0.13]
    })

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample_data.to_excel(writer, index=False, sheet_name='DCF输入')
    output.seek(0)

    col_dl, _ = st.columns([1, 3])
    with col_dl:
        st.download_button(
            '📥 下载 Excel 模板', data=output,
            file_name='dcf_batch_template.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    st.markdown('**支持列名：** 英文 `fcf0, high_growth_rate, ...`  或  中文 `基期自由现金流, 高增长率, ...`')
    st.markdown('**必填列：** `fcf0`, `high_growth_rate`, `high_growth_years`, `stable_growth_rate`, `discount_rate`')
    st.markdown('**可选列：** `公司名称`（若缺失则自动生成编号）')

    uploaded_file = st.file_uploader('上传 Excel 文件', type=['xlsx', 'xls'])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.info(f'📋 已读取 {len(df)} 行 × {len(df.columns)} 列   |   列名: {", ".join(df.columns.tolist())}')

            # 自动映射列名
            col_map, missing, found = map_columns(df)
            if found:
                mapped_info = ', '.join([f'{k} ← "{col_map[k]}"' for k in found if k in col_map])
                st.success(f'✅ 已识别 {len(found)} 个字段: {mapped_info}')
            if missing:
                st.error(f'❌ 缺少必要列: {missing}')
                st.markdown('请确保 Excel 包含以下列名之一：')
                for k in ['fcf0', 'high_growth_rate', 'high_growth_years', 'stable_growth_rate', 'discount_rate']:
                    aliases = COLUMN_MAPPING.get(k, [k])
                    st.caption(f'  • **{k}**: {", ".join(aliases[:6])}')
                return

            # 构建参数列表
            params_list = []
            valid_indices = []
            errors = []

            for idx, row in df.iterrows():
                try:
                    p = DCFParams(
                        fcf0=float(row[col_map['fcf0']]),
                        high_growth_rate=float(row[col_map['high_growth_rate']]),
                        high_growth_years=int(row[col_map['high_growth_years']]),
                        stable_growth_rate=float(row[col_map['stable_growth_rate']]),
                        discount_rate=float(row[col_map['discount_rate']])
                    )
                    params_list.append(p)
                    valid_indices.append(idx)
                except ValueError as e:
                    name_col = col_map.get('company_name', None)
                    name = row[name_col] if name_col and name_col in df.columns else f'第{idx + 1}行'
                    errors.append({'行号': idx + 1, '公司': str(name), '错误': str(e)})

            if errors:
                st.warning(f'⚠️ {len(errors)} 条数据校验失败（已跳过）')
                st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

            if not params_list:
                st.error('没有有效数据可供估值，请检查 Excel 内容')
                return

            # 批量估值
            with st.spinner(f'正在对 {len(params_list)} 家公司进行估值...'):
                values = dcf_valuation_batch(params_list)

            # 获取公司名称
            name_col = col_map.get('company_name', None)
            if name_col and name_col in df.columns:
                company_names = [str(df.loc[i, name_col]) for i in valid_indices]
            else:
                company_names = [f'Company_{i + 1}' for i in range(len(valid_indices))]

            result_df = pd.DataFrame({
                '公司名称': company_names,
                '当前FCF (万元)': [round(p.fcf0, 2) for p in params_list],
                '内在价值 (万元)': np.round(values, 2),
                'WACC': [f'{p.discount_rate:.1%}' for p in params_list],
                '高增长率': [f'{p.high_growth_rate:.1%}' for p in params_list],
                '永续增长率': [f'{p.stable_growth_rate:.1%}' for p in params_list]
            })

            # 统计摘要
            st.divider()
            st.subheader('📊 估值结果')
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric('估值公司数', f'{len(result_df)} 家')
            with col_stat2:
                st.metric('平均内在价值', f'{values.mean():,.0f} 万元')
            with col_stat3:
                ratio_mean = (values / np.array([p.fcf0 for p in params_list])).mean()
                st.metric('平均估值倍数', f'{ratio_mean:.1f}x')

            st.dataframe(result_df, use_container_width=True, hide_index=True)

            # 下载结果
            col_rd1, col_rd2, _ = st.columns([1, 1, 3])
            result_output = BytesIO()
            with pd.ExcelWriter(result_output, engine='openpyxl') as writer:
                result_df.to_excel(writer, index=False, sheet_name='估值结果')
            result_output.seek(0)
            with col_rd1:
                st.download_button(
                    '📥 导出结果 Excel', data=result_output,
                    file_name='dcf_valuation_results.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                )
            with col_rd2:
                csv_output = BytesIO()
                result_df.to_csv(csv_output, index=False)
                st.download_button(
                    '📥 导出 CSV', data=csv_output.getvalue(),
                    file_name='dcf_valuation_results.csv', mime='text/csv'
                )

            st.plotly_chart(plot_batch_comparison(result_df), use_container_width=True)

        except Exception as e:
            st.error(f'处理失败: {e}')
            st.exception(e)


def render_wacc_calculator():
    """WACC 计算器页面"""
    st.markdown("""
    <div class="dcf-callout">
    <strong>🔧 WACC (加权平均资本成本)</strong> 是 DCF 估值中的核心折现率。
    它反映企业融资的综合成本，由<strong>权益成本 (CAPM 模型)</strong>和<strong>税后债务成本</strong>按资本结构加权计算。
    </div>
    """, unsafe_allow_html=True)

    equity_ratio = st.session_state.get('eq_ratio', 0.7)
    debt_ratio = st.session_state.get('debt_ratio', 0.3)
    cost_eq = st.session_state.get('cost_eq', 10.0) / 100
    cost_debt = st.session_state.get('cost_debt', 5.0) / 100
    tax_rate = st.session_state.get('tax_rate', 25.0) / 100
    rf = st.session_state.get('rf', 3.0) / 100
    beta = st.session_state.get('beta', 1.0)
    mrp = st.session_state.get('mrp', 7.0) / 100

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="dcf-card">
        <h3>📈 CAPM 权益成本（参考）</h3>
        </div>
        """, unsafe_allow_html=True)

        Re_capm = calc_cost_of_equity(rf, beta, mrp)
        st.metric('权益成本 Re', f'{Re_capm:.2%}',
                  delta=f'Rf={rf:.1%} + β={beta:.1f} × ({mrp:.1%})')

        st.markdown(f"""
        | 参数 | 值 |
        |------|-----|
        | 无风险利率 (Rf) | {rf:.1%} |
        | β 系数 | {beta:.1f} |
        | 市场风险溢价 (Rm−Rf) | {mrp:.1%} |
        | **CAPM 结果** | **{Re_capm:.2%}** |
        """)

    with col2:
        st.markdown("""
        <div class="dcf-card">
        <h3>🧮 WACC 计算结果</h3>
        </div>
        """, unsafe_allow_html=True)

        try:
            wacc = calc_wacc(equity_ratio, debt_ratio, cost_eq, cost_debt, tax_rate)
            after_tax_debt = cost_debt * (1 - tax_rate)
            equity_contrib = equity_ratio * cost_eq
            debt_contrib = debt_ratio * after_tax_debt

            st.metric('WACC', f'{wacc:.2%}',
                      delta=f'E贡献={equity_contrib:.2%} + D贡献={debt_contrib:.2%}')

            st.markdown(f"""
            | 组成部分 | 比例 | 成本 | 加权 |
            |---------|------|------|------|
            | 权益 | {equity_ratio:.0%} | {cost_eq:.2%} | {equity_contrib:.2%} |
            | 税后债务 | {debt_ratio:.0%} | {after_tax_debt:.2%} | {debt_contrib:.2%} |
            | **合计** | **100%** | — | **{wacc:.2%}** |
            """)

            # WACC 瀑布图
            fig = go.Figure(go.Waterfall(
                name='WACC', orientation='v',
                measure=['absolute', 'relative', 'total'],
                x=['权益成本<br>' + f'{equity_ratio:.0%}×{cost_eq:.2%}',
                   '税后债务成本<br>' + f'{debt_ratio:.0%}×{after_tax_debt:.2%}',
                   'WACC'],
                y=[equity_contrib, debt_contrib, 0],
                text=[f'{equity_contrib:.3%}', f'{debt_contrib:.3%}', f'{wacc:.3%}'],
                textposition='outside',
                connector={'line': {'color': 'rgb(63, 63, 63)'}},
                increasing={'marker': {'color': BLUE}},
                totals={'marker': {'color': RED}}
            ))
            fig.update_layout(
                title=dict(text='WACC 构成分解', font=dict(color=NAVY, size=14)),
                height=380, margin=dict(l=20, r=20, t=50, b=30),
                plot_bgcolor='#f8f9fb'
            )
            st.plotly_chart(fig, use_container_width=True)

        except ValueError as e:
            st.error(f'⚠️ {e}')
            st.caption('请确保权益比例 + 债务比例 ≈ 100%')

    st.divider()
    st.caption('💡 可将计算出的 WACC 值填入侧边栏「折现率 WACC」滑块，用于单公司估值')


# ============================================================
# 10. 主入口
# ============================================================

def main():
    mode = render_sidebar()

    if '单公司估值' in mode:
        render_single_company()
    elif '批量 Excel' in mode:
        render_batch_excel()
    elif 'WACC' in mode:
        render_wacc_calculator()


if __name__ == '__main__':
    main()
