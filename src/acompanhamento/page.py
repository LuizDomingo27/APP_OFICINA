"""Página do dashboard de Acompanhamento dentro do sistema unificado.

Filtros solicitados:
  - datas (usando a coluna ENVIO)
  - MP (Matéria Prima)
  - Departamento
  - PDV

Métricas solicitadas:
  - Peças a receber (PECAS)
  - Minutos a receber (MINUTOS)
  - Agrupamentos por MP, oficina, mês, dia e semanas.
  - Gráficos de MP, Departamento e Série temporal.
"""

import html
import pandas as pd
import streamlit as st
from datetime import date
from src.shared.echarts_utils import safe_st_echarts, JsCode
from src.shared.state import resetar_sessao
from src.shared.date_presets import render_date_presets

# Configurações de layout/estilo
COLOR_PRIMARY = "#0E9F6E"  # Verde neon-aqua (padrão visual do Painel de Recebimento)
COLOR_DARK = "#0F1B2D"
COLOR_MUTED = "#6B7A90"
COLOR_BORDER = "#E6ECEF"
COLOR_CARD = "#FFFFFF"

# JS formatters para ECharts
_NUM_FMT_JS = (
    "function (value) {"
    "  if (value !== null && typeof value === 'object') {"
    "    value = Array.isArray(value.value) ? value.value[value.value.length - 1] : value.value;"
    "  }"
    "  if (value === null || value === undefined || value === '') return '';"
    "  var num = Number(value);"
    "  if (isNaN(num)) return '';"
    "  return num.toLocaleString('pt-BR', {maximumFractionDigits: 0});"
    "}"
)

def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800;900&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            color: {COLOR_DARK} !important;
        }}
        .stApp, .main, .block-container {{
            background-color: #FAFCFB !important;
        }}
        .section-title {{
            font-family: 'Poppins', sans-serif;
            font-size: 22px;
            font-weight: 800;
            color: {COLOR_DARK};
            letter-spacing: -0.5px;
            margin-bottom: 4px;
        }}
        .section-bar {{
            width: 48px;
            height: 3px;
            background: {COLOR_PRIMARY};
            border-radius: 2px;
            margin-bottom: 16px;
        }}
        .metric-card {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-left: 6px solid {COLOR_PRIMARY};
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 4px 18px rgba(15,27,45,0.04);
            height: 100%;
        }}
        .metric-card .label {{
            color: {COLOR_MUTED};
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .metric-card .value {{
            font-family: 'Poppins', sans-serif;
            font-weight: 900;
            font-size: 1.9rem;
            color: {COLOR_DARK};
            margin-top: 4px;
            line-height: 1.1;
        }}
        .metric-card .sub {{
            font-size: 0.8rem;
            color: {COLOR_MUTED};
            margin-top: 4px;
        }}
        .metric-card .accent {{ color: {COLOR_PRIMARY}; font-weight: 700; }}

        /* Estilização para as Abas Customizadas */
        [data-testid="stRadio"] > div[role="radiogroup"] {{
            gap: 4px;
            background: #E8F5EE !important;
            border-radius: 12px;
            padding: 4px;
            display: inline-flex;
            flex-wrap: wrap;
        }}
        [data-testid="stRadio"] label {{
            border-radius: 9px;
            font-weight: 600;
            color: #4A6B5A !important;
            padding: 7px 20px;
            background: transparent !important;
            margin: 0 !important;
            transition: background 0.15s ease;
        }}
        [data-testid="stRadio"] label > div:first-child {{
            display: none !important;
        }}
        [data-testid="stRadio"] label:has(input:checked) {{
            background: {COLOR_PRIMARY} !important;
        }}
        [data-testid="stRadio"] label:has(input:checked) div {{
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }}

        /* Tabelas Customizadas */
        .custom-table-wrapper {{
            background: {COLOR_CARD};
            border: 1px solid {COLOR_BORDER};
            border-radius: 14px;
            overflow: auto;
            max-height: 520px;
        }}
        .custom-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.84rem;
        }}
        .custom-table thead th {{
            background: {COLOR_PRIMARY} !important;
            color: #FFFFFF !important;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.68rem;
            letter-spacing: 0.07em;
            padding: 13px 14px;
            border-bottom: 2px solid #0C8560;
            position: sticky;
            top: 0;
            z-index: 2;
            white-space: nowrap;
            text-align: left;
        }}
        .custom-table thead th.num {{
            text-align: center;
        }}
        .custom-table tbody tr.even {{ background: #FAFCFB; }}
        .custom-table tbody tr.odd  {{ background: {COLOR_CARD}; }}
        .custom-table tbody tr:hover {{ background: #F2FFF9 !important; }}
        .custom-table td {{
            padding: 11px 14px;
            border-bottom: 1px solid #ECEFF3;
            color: {COLOR_DARK};
            vertical-align: middle;
            text-align: left;
        }}
        .custom-table td.num {{
            font-variant-numeric: tabular-nums;
            font-weight: 600;
            color: {COLOR_PRIMARY};
            text-align: center;
        }}
        .custom-table td.date {{
            color: {COLOR_MUTED};
            font-size: 0.8rem;
            text-align: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def fmt_number(val: float) -> str:
    """Formatador no padrão brasileiro (123456 -> 123.456)"""
    return f"{int(val):,}".replace(",", ".")

def render_kpi_cards(df: pd.DataFrame, df_full: pd.DataFrame) -> None:
    total_pecas = df['PECAS'].sum()
    total_minutos = df['MINUTOS'].sum()
    registros = len(df)
    #oficinas = df['OFICINA'].nunique()

    cards = [
        ("Peças a Receber", fmt_number(total_pecas), "Total sob os filtros"),
        ("Minutos a Receber", fmt_number(total_minutos), f"{fmt_number(total_minutos / 60)} horas"),
        ("Nº Ordens", fmt_number(registros), f"De {fmt_number(len(df_full))} no total"),
        #("Oficinas Ativas", fmt_number(oficinas), f"{df['MP'].nunique()} MPs · {df['PDV'].nunique()} PDVs"),
    ]

    cols = st.columns(4)
    for col, (label, value, sub) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{value}</div>
                    <div class="sub"><span class="accent">●</span> {sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

def _chart_card_header(title: str) -> None:
    st.markdown(
        f"""
        <div style="font-size: 15px; font-weight: 700; color: {COLOR_DARK}; margin-bottom: 8px; margin-top: 10px;">
            {title}
        </div>
        """,
        unsafe_allow_html=True
    )

def _render_chart(option: dict, height: str = "320px") -> None:
    st.markdown(
        '<div style="background:#FFFFFF;border-radius:14px;border:1.5px solid #E6ECEF;padding:16px;box-shadow:0 4px 18px rgba(15,27,45,0.02);">',
        unsafe_allow_html=True,
    )
    safe_st_echarts(options=option, height=height)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ECharts Option Builders
# ─────────────────────────────────────────────────────────────────────────────

def build_bar_mp(df: pd.DataFrame) -> dict:
    df_grouped = df.groupby('MP')['PECAS'].sum().reset_index().sort_values(by='PECAS', ascending=False)
    categories = df_grouped['MP'].tolist()
    values = df_grouped['PECAS'].tolist()

    return {
        "backgroundColor": "#FFFFFF",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(10,22,18,0.88)",
            "borderColor": COLOR_PRIMARY,
            "textStyle": {"color": "#EAFBF3"}
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"color": COLOR_DARK, "fontWeight": "600"}
        },
        "yAxis": {
            "type": "value",
            "show": False,
            "splitLine": {"show": False}
        },
        "series": [{
            "data": values,
            "type": "bar",
            "itemStyle": {"color": COLOR_PRIMARY, "borderRadius": [6, 6, 0, 0]},
            "label": {
                "show": True,
                "position": "top",
                "color": COLOR_DARK,
                "fontWeight": "600",
                "formatter": JsCode(_NUM_FMT_JS)
            }
        }]
    }

def build_bar_depto(df: pd.DataFrame) -> dict:
    df_grouped = df.groupby('DEPARTAMENTO')['PECAS'].sum().reset_index().sort_values(by='PECAS', ascending=False).head(15)
    categories = df_grouped['DEPARTAMENTO'].tolist()
    values = df_grouped['PECAS'].tolist()

    return {
        "backgroundColor": "#FFFFFF",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(10,22,18,0.88)",
            "borderColor": COLOR_PRIMARY,
            "textStyle": {"color": "#EAFBF3"}
        },
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"color": COLOR_DARK, "fontWeight": "600", "interval": 0, "rotate": 25}
        },
        "yAxis": {
            "type": "value",
            "show": False,
            "splitLine": {"show": False}
        },
        "series": [{
            "data": values,
            "type": "bar",
            "itemStyle": {"color": "#00B4D8", "borderRadius": [6, 6, 0, 0]},
            "label": {
                "show": True,
                "position": "top",
                "color": COLOR_DARK,
                "fontWeight": "600",
                "formatter": JsCode(_NUM_FMT_JS)
            }
        }]
    }

def build_line_temporal(df: pd.DataFrame, group_by: str) -> dict:
    """Monta gráfico de linha temporal para peças e minutos a receber.

    Estilo alinhado ao painel de Recebimento: linhas suaves, área em gradiente,
    sem rótulos de dados poluindo o gráfico — os valores aparecem apenas em
    uma tooltip elegante ao passar o mouse.
    """
    if group_by == "dia":
        df_g = df.groupby('DIA')[['PECAS', 'MINUTOS']].sum().reset_index()
        x_data = [d.strftime('%d/%m/%Y') for d in df_g['DIA']]
    else: # semana
        df_g = df.groupby('SEMANA_STR')[['PECAS', 'MINUTOS']].sum().reset_index()
        x_data = df_g['SEMANA_STR'].tolist()

    values_pecas = df_g['PECAS'].tolist()
    values_minutos = df_g['MINUTOS'].tolist()

    tooltip_formatter = JsCode(
        "function (params) {"
        "  var html = '<div style=\"font-weight:700;margin-bottom:4px;\">' + params[0].axisValueLabel + '</div>';"
        "  params.forEach(function (p) {"
        "    var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
        "    html += '<div>' + p.marker + ' ' + p.seriesName + ': <b>' + v + '</b></div>';"
        "  });"
        "  return html;"
        "}"
    )

    return {
        "backgroundColor": "#FFFFFF",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(10,22,18,0.88)",
            "borderColor": COLOR_PRIMARY,
            "borderWidth": 1,
            "padding": [10, 14],
            "textStyle": {"color": "#EAFBF3", "fontSize": 12, "fontWeight": "bold"},
            "extraCssText": (
                "box-shadow:0 6px 20px rgba(0,0,0,0.35);"
                "border-radius:10px;"
                "backdrop-filter:blur(4px);"
            ),
            "axisPointer": {"lineStyle": {"color": COLOR_PRIMARY}},
            "formatter": tooltip_formatter,
        },
        "legend": {
            "data": ["Peças a Receber", "Minutos a Receber"],
            "textStyle": {"color": COLOR_DARK, "fontWeight": "600"},
            "top": 8,
            "icon": "roundRect",
            "itemWidth": 14,
            "itemHeight": 9,
            "itemGap": 18,
        },
        "grid": {"left": 50, "right": 50, "bottom": 60, "top": 50},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": COLOR_BORDER, "width": 1.5}},
            "axisTick": {"lineStyle": {"color": COLOR_BORDER}},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Peças",
                "nameTextStyle": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
                "show": False,
                "splitLine": {"show": False}
            },
            {
                "type": "value",
                "name": "Minutos",
                "nameTextStyle": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
                "show": False,
                "splitLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": "Peças a Receber",
                "type": "line",
                "data": values_pecas,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 5,
                "lineStyle": {"color": COLOR_PRIMARY, "width": 2.5},
                "itemStyle": {"color": COLOR_PRIMARY, "borderColor": "#FFFFFF", "borderWidth": 2},
                "areaStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(14,159,110,0.28)"},
                            {"offset": 1, "color": "rgba(14,159,110,0.02)"},
                        ],
                    }
                },
            },
            {
                "name": "Minutos a Receber",
                "type": "line",
                "yAxisIndex": 1,
                "data": values_minutos,
                "smooth": True,
                "symbol": "diamond",
                "symbolSize": 6,
                "lineStyle": {"color": "#FFB347", "width": 2, "type": "dashed"},
                "itemStyle": {"color": "#FFB347", "borderColor": "#FFFFFF", "borderWidth": 2},
            }
        ]
    }

def build_line_recebimento(df_receb: pd.DataFrame) -> dict:
    """Monta gráfico de linha temporal de Peças/Minutos a Receber, agrupado por
    dia de Recebimento (apenas linhas com data válida nessa coluna).

    Estilo alinhado ao painel de Recebimento/Análise Gráfica: linhas suaves,
    área em gradiente, sem rótulos de dados — valores aparecem apenas na
    tooltip ao passar o mouse.
    """
    df_g = (
        df_receb.assign(RECEBIMENTO=df_receb['RECEBIMENTO'].dt.date)
        .groupby('RECEBIMENTO')[['PECAS', 'MINUTOS']]
        .sum()
        .reset_index()
        .sort_values(by='RECEBIMENTO')
    )
    x_data = [d.strftime('%d/%m/%Y') for d in df_g['RECEBIMENTO']]
    values_pecas = df_g['PECAS'].tolist()
    values_minutos = df_g['MINUTOS'].tolist()

    tooltip_formatter = JsCode(
        "function (params) {"
        "  var html = '<div style=\"font-weight:700;margin-bottom:4px;\">' + params[0].axisValueLabel + '</div>';"
        "  params.forEach(function (p) {"
        "    var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
        "    html += '<div>' + p.marker + ' ' + p.seriesName + ': <b>' + v + '</b></div>';"
        "  });"
        "  return html;"
        "}"
    )

    return {
        "backgroundColor": "#FFFFFF",
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(10,22,18,0.88)",
            "borderColor": COLOR_PRIMARY,
            "borderWidth": 1,
            "padding": [10, 14],
            "textStyle": {"color": "#EAFBF3", "fontSize": 12, "fontWeight": "bold"},
            "extraCssText": (
                "box-shadow:0 6px 20px rgba(0,0,0,0.35);"
                "border-radius:10px;"
                "backdrop-filter:blur(4px);"
            ),
            "axisPointer": {"lineStyle": {"color": COLOR_PRIMARY}},
            "formatter": tooltip_formatter,
        },
        "legend": {
            "data": ["Peças a Receber", "Minutos a Receber"],
            "textStyle": {"color": COLOR_DARK, "fontWeight": "600"},
            "top": 8,
            "icon": "roundRect",
            "itemWidth": 14,
            "itemHeight": 9,
            "itemGap": 18,
        },
        "grid": {"left": 50, "right": 50, "bottom": 60, "top": 50},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": COLOR_BORDER, "width": 1.5}},
            "axisTick": {"lineStyle": {"color": COLOR_BORDER}},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Peças",
                "nameTextStyle": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
                "show": False,
                "splitLine": {"show": False}
            },
            {
                "type": "value",
                "name": "Minutos",
                "nameTextStyle": {"color": COLOR_MUTED, "fontWeight": "600", "fontSize": 11},
                "show": False,
                "splitLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": "Peças a Receber",
                "type": "line",
                "data": values_pecas,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 5,
                "lineStyle": {"color": COLOR_PRIMARY, "width": 2.5},
                "itemStyle": {"color": COLOR_PRIMARY, "borderColor": "#FFFFFF", "borderWidth": 2},
                "areaStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(14,159,110,0.28)"},
                            {"offset": 1, "color": "rgba(14,159,110,0.02)"},
                        ],
                    }
                },
            },
            {
                "name": "Minutos a Receber",
                "type": "line",
                "yAxisIndex": 1,
                "data": values_minutos,
                "smooth": True,
                "symbol": "diamond",
                "symbolSize": 6,
                "lineStyle": {"color": "#FFB347", "width": 2, "type": "dashed"},
                "itemStyle": {"color": "#FFB347", "borderColor": "#FFFFFF", "borderWidth": 2},
            }
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# Tabela Customizada
# ─────────────────────────────────────────────────────────────────────────────

def render_custom_table(df_table: pd.DataFrame, num_cols: list, date_cols: list) -> None:
    cols = df_table.columns.tolist()
    thead_cells = []
    
    for c in cols:
        if c in num_cols:
            thead_cells.append(f"<th class='num'>{html.escape(str(c))}</th>")
        elif c in date_cols:
            thead_cells.append(f"<th style='text-align: center;'>{html.escape(str(c))}</th>")
        else:
            thead_cells.append(f"<th>{html.escape(str(c))}</th>")
    thead = "".join(thead_cells)
    
    rows_html = []
    for idx, row in enumerate(df_table.itertuples(index=False)):
        cells = []
        for col_idx, val in enumerate(row):
            col_name = cols[col_idx]
            if col_name in date_cols and pd.notna(val):
                # Se for objeto de data ou Timestamp
                if isinstance(val, (pd.Timestamp, date)):
                    cell = f"<td class='date'>{val.strftime('%d/%m/%Y')}</td>"
                else:
                    cell = f"<td class='date'>{html.escape(str(val))}</td>"
            elif col_name in num_cols:
                cell = f"<td class='num'>{fmt_number(float(val))}</td>"
            else:
                cell = f"<td>{html.escape(str(val)) if pd.notna(val) else ''}</td>"
            cells.append(cell)
        row_cls = "even" if idx % 2 == 0 else "odd"
        rows_html.append(f"<tr class='{row_cls}'>{''.join(cells)}</tr>")
        
    table_html = f"""
    <div class="custom-table-wrapper">
        <table class="custom-table">
            <thead><tr>{thead}</tr></thead>
            <tbody>{"".join(rows_html)}</tbody>
        </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Página Principal
# ─────────────────────────────────────────────────────────────────────────────

def render_acompanhamento_page(df_full: pd.DataFrame) -> None:
    _inject_css()
    
    df_full = df_full.copy()
    if 'OM' not in df_full.columns:
        df_full['OM'] = 'N/A'


    # Barra lateral de filtros
    with st.sidebar:
        st.markdown("### 🔍 Filtros")
        
        # 1. Período de data baseado na coluna ENVIO
        dates = sorted(df_full['ENVIO'].dt.date.dropna().unique())
        
        date_key = "acomp_date_range_filter"
        
        if len(dates) >= 2:
            render_date_presets(st.sidebar, dates[0], dates[-1], marker="acomp_preset", range_key=date_key)
            date_range = st.date_input(
                "Período de Envio",
                value=st.session_state.get(date_key, [dates[0], dates[-1]]),
                min_value=dates[0],
                max_value=dates[-1],
                key=date_key,
                format="DD/MM/YYYY",
            )
            
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                d_start, d_end = date_range
            elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
                d_start = d_end = date_range[0]
            else:
                d_start = d_end = date_range
        elif len(dates) == 1:
            d_start = d_end = st.date_input("Período de Envio", value=dates[0])
        else:
            d_start = d_end = None

        # 2. MP filter
        mps = sorted(df_full['MP'].dropna().unique())
        selected_mps = st.multiselect("Matéria-Prima (MP)", options=mps, default=[])

        # 3. Departamento filter
        departamentos = sorted(df_full['DEPARTAMENTO'].dropna().unique())
        selected_deps = st.multiselect("Departamento", options=departamentos, default=[])

        # 4. PDV filter
        pdvs = sorted(df_full['PDV'].dropna().unique())
        selected_pdvs = st.multiselect("PDV", options=pdvs, default=[])


    # Aplicação de filtros
    df = df_full.copy()
    if d_start and d_end:
        df = df[(df['ENVIO'].dt.date >= d_start) & (df['ENVIO'].dt.date <= d_end)]
    if selected_mps:
        df = df[df['MP'].isin(selected_mps)]
    if selected_deps:
        df = df[df['DEPARTAMENTO'].isin(selected_deps)]
    if selected_pdvs:
        df = df[df['PDV'].isin(selected_pdvs)]

    # Metragem filtrados
    st.sidebar.markdown(
        f"""
        <div style="
            background:#F0FDF8;border:1.5px solid #D0F0E5;
            border-radius:10px;padding:10px 14px;
            font-size:12px;color:#6B8F7E;margin-top:8px;
        ">
            <strong style='color:{COLOR_DARK};'>{len(df):,}</strong> registros exibidos<br>
            de <strong style='color:{COLOR_DARK};'>{len(df_full):,}</strong> no total
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados. Ajuste os filtros na barra lateral.")
        st.stop()

    # Cards de KPIs
    st.markdown("## Indicadores Gerais")
    render_kpi_cards(df, df_full)
    st.markdown("<br>", unsafe_allow_html=True)

    # Abas visuais
    tab_charts = " Gráficos & Evolução"
    #tab_groups = "🗂️ Tabelas Agrupadas"
    tab_receb = " A Receber (Recebimento)"

    aba = st.radio(
        "Visualização",
        [tab_charts, tab_receb],
        horizontal=True,
        label_visibility="collapsed",
        key="acompanhamento_aba_principal"
    )

    st.divider()

    if aba == tab_charts:
        st.markdown("## Análise Gráfica")
        
        # Série Temporal
        _chart_card_header("Evolução Temporal de Recebimento (Peças & Minutos)")
        line_granularity = st.radio("Granularidade", ["Por Dia", "Por Semana"], horizontal=True, label_visibility="collapsed")
        
        if line_granularity == "Por Dia":
            _render_chart(build_line_temporal(df, "dia"), "340px")
        else:
            _render_chart(build_line_temporal(df, "semana"), "340px")

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            _chart_card_header("Volume a Receber por Matéria-Prima (MP)")
            _render_chart(build_bar_mp(df), "320px")
        with col_c2:
            _chart_card_header("Volume a Receber por Departamento")
            _render_chart(build_bar_depto(df), "320px")


        st.markdown("#### Selecione uma Opção para Agrupar os Dados")
        
        group_option = st.selectbox(
            "",
            options=["Matéria-Prima (MP)", "Oficina", "Mês", "Semana", "Dia"], width=300
        )
        
        if group_option == "Matéria-Prima (MP)":
            df_g = df.groupby('MP')[['PECAS', 'MINUTOS']].sum().reset_index().sort_values(by='PECAS', ascending=False)
            render_custom_table(df_g, num_cols=['PECAS', 'MINUTOS'], date_cols=[])
            
        elif group_option == "Oficina":
            df_g = df.groupby('OFICINA')[['PECAS', 'MINUTOS']].sum().reset_index().sort_values(by='PECAS', ascending=False)
            render_custom_table(df_g, num_cols=['PECAS', 'MINUTOS'], date_cols=[])
            
        elif group_option == "Mês":
            df_g = df.groupby('MES_STR')[['PECAS', 'MINUTOS']].sum().reset_index().sort_values(by='MES_STR', ascending=False)
            df_g = df_g.rename(columns={'MES_STR': 'MÊS'})
            render_custom_table(df_g, num_cols=['PECAS', 'MINUTOS'], date_cols=[])
            
        elif group_option == "Semana":
            df_g = df.groupby('SEMANA_STR')[['PECAS', 'MINUTOS']].sum().reset_index().sort_values(by='SEMANA_STR', ascending=False)
            df_g = df_g.rename(columns={'SEMANA_STR': 'SEMANA'})
            render_custom_table(df_g, num_cols=['PECAS', 'MINUTOS'], date_cols=[])
            
        elif group_option == "Dia":
            df_g = df.groupby('DIA')[['PECAS', 'MINUTOS']].sum().reset_index().sort_values(by='DIA', ascending=False)
            render_custom_table(df_g, num_cols=['PECAS', 'MINUTOS'], date_cols=['DIA'])

        st.divider()

        # Tabela detalhada por semana (Semana / Ordem / MP / Peças / Minutos)
        _chart_card_header("Detalhamento por Semana")
        df_semana_detalhe = (
            df.groupby(['SEMANA_STR', 'OM', 'MP'])[['PECAS', 'MINUTOS']]
            .sum()
            .reset_index()
            .sort_values(by=['SEMANA_STR', 'OM', 'MP'], ascending=[False, True, True])
        )
        df_semana_detalhe = df_semana_detalhe.rename(columns={'SEMANA_STR': 'SEMANA', 'OM': 'ORDEM'})
        df_semana_detalhe = df_semana_detalhe[['SEMANA', 'ORDEM', 'MP', 'PECAS', 'MINUTOS']]
        render_custom_table(df_semana_detalhe, num_cols=['PECAS', 'MINUTOS'], date_cols=[])

        st.divider()

        # Tabelas de Recebimento (apenas registros com data válida na coluna Recebimento)
        _chart_card_header("Recebimento por OM / MP (por Data de Recebimento)")
        st.caption(
            "Considera apenas os registros (dentro dos filtros aplicados) que possuem "
            "uma data válida na coluna Recebimento. Textos de status como 'À programar' "
            "ou 'Almoxarifado' são ignorados nesta visão."
        )
        df_receb = df[df['RECEBIMENTO'].notna()].copy()

        if df_receb.empty:
            st.warning(
                "⚠️ Nenhum registro com data de Recebimento válida foi encontrado "
                "para os filtros selecionados."
            )
        else:
            df_g_receb = (
                df_receb.assign(RECEBIMENTO=df_receb['RECEBIMENTO'].dt.date)
                .groupby(['RECEBIMENTO', 'OM', 'MP'])[['PECAS', 'MINUTOS']]
                .sum()
                .reset_index()
                .sort_values(by=['RECEBIMENTO', 'OM', 'MP'], ascending=[False, True, True])
            )
            df_g_receb = df_g_receb[['RECEBIMENTO', 'OM', 'MP', 'PECAS', 'MINUTOS']]
            render_custom_table(df_g_receb, num_cols=['PECAS', 'MINUTOS'], date_cols=['RECEBIMENTO'])

            st.markdown("<br>", unsafe_allow_html=True)

            # Resumo agrupado por semana de Recebimento (visão consolidada, sem
            # quebra por OM/MP — total de peças e minutos recebidos em cada semana).
            _chart_card_header(" Resumo Semanal de Recebimento")
            semana_receb = df_receb['RECEBIMENTO'].dt.isocalendar()
            df_resumo_semana = (
                df_receb.assign(
                    SEMANA_STR=(
                        semana_receb['year'].astype(str)
                        + "-W"
                        + semana_receb['week'].astype(int).astype(str).str.zfill(2)
                    )
                )
                .groupby('SEMANA_STR')[['PECAS', 'MINUTOS']]
                .sum()
                .reset_index()
                .sort_values(by='SEMANA_STR', ascending=False)
            )
            df_resumo_semana = df_resumo_semana.rename(columns={'SEMANA_STR': 'SEMANA'})
            render_custom_table(df_resumo_semana, num_cols=['PECAS', 'MINUTOS'], date_cols=[])

        st.divider()

        # Detalhamento dos dados brutos (linhas individuais)
        _chart_card_header(" Dados Detalhados")
        columns_to_show = ['ENVIO', 'DEADLINE', 'OM', 'MP', 'OFICINA', 'DEPARTAMENTO', 'PECAS', 'MINUTOS']
        df_table = df[columns_to_show].head(400)
        render_custom_table(df_table, num_cols=['PECAS', 'MINUTOS'], date_cols=['ENVIO', 'DEADLINE'])

    elif aba == tab_receb:
        st.markdown("### Visão por Data de Recebimento")
        st.caption(
            "Considera apenas os registros (dentro dos filtros aplicados) que possuem "
            "uma data válida na coluna Recebimento. Textos de status como 'À programar' "
            "ou 'Almoxarifado' são ignorados nesta visão."
        )

        df_receb = df[df['RECEBIMENTO'].notna()].copy()

        if df_receb.empty:
            st.warning(
                "⚠️ Nenhum registro com data de Recebimento válida foi encontrado "
                "para os filtros selecionados."
            )
        else:
            total_pecas_receb = df_receb['PECAS'].sum()
            total_min_receb = df_receb['MINUTOS'].sum()
            total_ordens_receb = df_receb['OM'].nunique()

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="label">Peças a Receber</div>
                        <div class="value">{fmt_number(total_pecas_receb)}</div>
                        <div class="sub"><span class="accent">●</span> Por data de Recebimento</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_r2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="label">Minutos a Receber</div>
                        <div class="value">{fmt_number(total_min_receb)}</div>
                        <div class="sub"><span class="accent">●</span> {fmt_number(total_min_receb / 60)} horas</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_r3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="label">Total de Ordens</div>
                        <div class="value">{fmt_number(total_ordens_receb)}</div>
                        <div class="sub"><span class="accent">●</span> OMs distintas a receber</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            _chart_card_header("Evolução Temporal de Recebimento (Peças & Minutos)")
            _render_chart(build_line_recebimento(df_receb), "340px")

            st.markdown("<br>", unsafe_allow_html=True)

            # Tabela consolidada por dia de previsão de Recebimento
            _chart_card_header(" Consolidado por Data de Recebimento")
            df_receb_dia = (
                df_receb.assign(DATA=df_receb['RECEBIMENTO'].dt.date)
                .groupby('DATA')
                .agg(
                    PECAS=('PECAS', 'sum'),
                    MINUTOS=('MINUTOS', 'sum'),
                    ORDENS=('OM', 'nunique'),
                )
                .reset_index()
                .sort_values(by='DATA', ascending=False)
            )
            df_receb_dia = df_receb_dia.rename(columns={
                'DATA': 'DATA',
                'PECAS': 'TOTAL PEÇAS',
                'MINUTOS': 'TOTAL MINUTOS',
                'ORDENS': 'TOTAL DE ORDENS',
            })
            render_custom_table(
                df_receb_dia,
                num_cols=['TOTAL PEÇAS', 'TOTAL MINUTOS', 'TOTAL DE ORDENS'],
                date_cols=['DATA'],
            )
            

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    #st.markdown(
    #    f"""
    #    <div style="text-align:center; font-size:12px; color:#A0C4B3; padding:12px; border-top:1.5px solid #D0F0E5;">
    #        Painel de Acompanhamento · Desenvolvido com Streamlit & ECharts
    #    </div>
    #    """,
    #    unsafe_allow_html=True,
    #)
