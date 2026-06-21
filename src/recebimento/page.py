"""
page.py — Painel de Recebimento dentro do sistema unificado.

Adaptado do app.py original do projeto APP_RECEBIMENTO: a única
mudança estrutural é que o DataFrame completo (df_full) chega já
carregado da tela inicial (src/shared/home.py), em vez de ser lido
de um arquivo fixo em disco.

Arquitetura em camadas (preservada do projeto original):
  ┌─────────────────────────────────────────┐
  │  page.py        (orquestração / UI raiz) │
  ├─────────────────────────────────────────┤
  │  ui/            (componentes visuais)    │
  │    ├─ cards.py   (KPI cards)             │
  │    ├─ filters.py (sidebar de filtros)    │
  │    └─ goal.py    (meta / progresso)      │
  ├─────────────────────────────────────────┤
  │  charts.py      (opções ECharts)         │
  ├─────────────────────────────────────────┤
  │  metrics.py     (lógica de negócio)      │
  ├─────────────────────────────────────────┤
  │  data_loader.py (acesso a dados)         │
  └─────────────────────────────────────────┘
"""

import html
import pandas as pd
import streamlit as st
from src.shared.echarts_utils import safe_st_echarts

from src.recebimento.config import APP_VERSION, COLOR_PRIMARY, COL_DIA
from src.recebimento.data_loader import get_filter_options, apply_filters
from src.recebimento.metrics import (
    calc_kpis,
    calc_goal_progress,
    agg_by_day,
    agg_by_week,
    agg_by_mp,
    agg_by_oficina,
    agg_by_mp_day,
)
from src.recebimento.charts import (
    build_line_daily,
    build_line_weekly,
    build_bar_mp,
    build_pie_mp,
    build_bar_oficinas,
    build_stacked_mp_day,
)
from src.recebimento.ui.cards import render_kpi_cards
from src.recebimento.ui.filters import render_filters
from src.recebimento.ui.goal import render_goal_section, render_goal_progress
from src.shared.state import resetar_sessao


# ===========================================================================
# CSS — tema neon-aqua / clean light (idêntico ao projeto original)
# ===========================================================================

def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            color: #1A2E25 !important;
        }}
        .stApp, .main, .block-container {{
            background-color: #F4FBF8 !important;
        }}
        iframe {{
            background: #FFFFFF !important;
            border-radius: 14px;
            border: 1.5px solid #D0F0E5;
        }}
        [data-testid="stCustomComponentV1"] > div {{
            background: #FFFFFF !important;
            border-radius: 14px;
            overflow: hidden;
        }}
        [data-testid="stSidebar"] {{
            background: #FFFFFF !important;
            border-right: 1.5px solid #D0F0E5;
        }}
        [data-testid="stSidebar"] * {{
            color: #1A2E25 !important;
        }}
        .stButton > button {{
            background: linear-gradient(135deg, {COLOR_PRIMARY} 0%, #0C8560 100%) !important;
            color: #1A2E25 !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}
        .stButton > button:hover {{ opacity: 0.85; transform: translateY(-1px); }}
        .stNumberInput input, .stDateInput input, input[type="number"] {{
            background: #FFFFFF !important;
            color: #1A2E25 !important;
            border: 1.5px solid #C8E8D8 !important;
            border-radius: 8px !important;
        }}
        .stNumberInput input:focus, .stDateInput input:focus {{
            border-color: {COLOR_PRIMARY} !important;
            box-shadow: 0 0 0 2px rgba(14,159,110,0.2) !important;
        }}
        [data-baseweb="select"] > div {{ background: #FFFFFF !important; border-color: #C8E8D8 !important; }}
        [data-baseweb="tag"] {{ background: {COLOR_PRIMARY} !important; color: #1A2E25 !important; }}
        /* Pills de navegação (substituem st.tabs — ver render_recebimento_page,
           bloco "Análise Visual", onde o st.radio é montado).
           Sem prefixo de classe porque streamlit==1.38.0 ainda não expõe a
           classe `.st-key-<key>` (chegou só na 1.39+). Seguro ficar global
           aqui pois app.py só renderiza uma "view" por vez (if/elif/else),
           então o único <div role="radiogroup"> na tela quando esta página
           está ativa é o desta navegação. */
        [data-testid="stRadio"] > div[role="radiogroup"] {{
            gap: 4px; background: #E8F5EE !important;
            border-radius: 12px; padding: 4px;
            display: inline-flex; flex-wrap: wrap;
        }}
        [data-testid="stRadio"] label {{
            border-radius: 9px; font-weight: 600;
            color: #4A6B5A !important; padding: 7px 20px;
            background: transparent !important;
            margin: 0 !important; transition: background 0.15s ease;
        }}
        [data-testid="stRadio"] label > div:first-child {{
            display: none !important;
        }}
        [data-testid="stRadio"] label:has(input:checked) {{
            background: {COLOR_PRIMARY} !important;
        }}
        [data-testid="stRadio"] label:has(input:checked) div {{
            color: #1A2E25 !important; font-weight: 800 !important;
        }}
        hr {{ border-top: 1.5px solid #D0F0E5 !important; margin: 20px 0 !important; }}
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-track {{ background: #F0FDF8; }}
        ::-webkit-scrollbar-thumb {{ background: #BFE8D9; border-radius: 4px; }}
        .section-title {{
            font-size: 22px; font-weight: 900;
            color: #1A2E25; letter-spacing: -0.5px; margin-bottom: 4px;
        }}
        .section-bar {{
            width: 48px; height: 3px;
            background: {COLOR_PRIMARY}; border-radius: 2px; margin-bottom: 16px;
        }}
        .stAlert {{
            background: #F0FDF8 !important;
            border-left: 4px solid {COLOR_PRIMARY} !important;
            border-radius: 10px !important; color: #1A2E25 !important;
        }}
        :root {{
            --gdg-bg-header: #0C8560;
            --gdg-bg-header-has-focus: #009C68;
            --gdg-bg-header-hovered: #009C68;
            --gdg-text-header: #FFFFFF;
            --gdg-text-header-selected: #FFFFFF;
            --gdg-border-color: #D0F0E5;
            --gdg-horizontal-border-color: #E5F5EE;
            --gdg-bg-cell: #FFFFFF;
            --gdg-bg-cell-medium: #F0FDF8;
            --gdg-bg-bubble: #F0FDF8;
            --gdg-text-dark: #1A2E25;
            --gdg-text-medium: #4A6B5A;
            --gdg-accent-color: {COLOR_PRIMARY};
            --gdg-accent-light: rgba(14,159,110,0.18);
            --gdg-header-font-style: 700 13px Inter, sans-serif;
        }}
        [data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {{
            border-radius: 14px !important;
            border: 1.5px solid #D0F0E5 !important;
            box-shadow: 0 2px 12px rgba(0,180,120,0.08) !important;
            overflow: hidden !important;
        }}
        .custom-table-wrapper {{
            background: #FFFFFF;
            border: 1.5px solid #D0F0E5;
            border-radius: 14px;
            overflow: auto;
            max-height: 420px;
        }}
        .custom-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.84rem;
        }}
        .custom-table thead th {{
            background: #0E9F6E !important;
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
        .custom-table tbody tr.odd  {{ background: #FFFFFF; }}
        .custom-table tbody tr:hover {{ background: #F0FDF8 !important; }}
        .custom-table td {{
            padding: 11px 14px;
            border-bottom: 1px solid #ECEFF3;
            color: #1A2E25;
            vertical-align: middle;
            text-align: left;
        }}
        .custom-table td.num {{
            font-variant-numeric: tabular-nums;
            font-weight: 600;
            color: #0E9F6E;
            text-align: center;
        }}
        .custom-table td.date {{
            color: #6B8F7E;
            text-align: center;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title: str, icon: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-title">{icon} {title}</div>
        <div class="section-bar"></div>
        """,
        unsafe_allow_html=True,
    )


def _echarts(options: dict, height: str = "340px") -> None:
    st.markdown(
        '<div style="background:#FFFFFF;border-radius:14px;'
        'border:1.5px solid #D0F0E5;padding:16px;'
        'box-shadow:0 2px 12px rgba(0,180,120,0.08);">',
        unsafe_allow_html=True,
    )
    safe_st_echarts(options=options, height=height)
    st.markdown("</div>", unsafe_allow_html=True)


def _chart_card(title: str) -> None:
    st.markdown(
        f"""
        <div style="
            font-size:15px; font-weight:700;
            color:#1A2E25; margin-bottom:8px;
        ">{title}</div>
        """,
        unsafe_allow_html=True,
    )


def render_recebimento_page(df_full: pd.DataFrame) -> None:
    """Renderiza o painel de Recebimento a partir do DataFrame já carregado na sessão."""
    _inject_css()

    options = get_filter_options(df_full)
    filtros = render_filters(options)


    df = apply_filters(
        df_full,
        date_start=filtros.date_start,
        date_end=filtros.date_end,
        mps=filtros.mps,
        oficinas=filtros.oficinas,
    )

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados. Ajuste os filtros na barra lateral.")
        st.stop()

    kpi = calc_kpis(df)

    _section_header("Indicadores Gerais", "")
    render_kpi_cards(kpi)
    st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    tipo_meta, meta_valor = render_goal_section(kpi.total_pecas, kpi.total_minutos)
    if meta_valor > 0:
        atual = kpi.total_pecas if tipo_meta == "Peças" else kpi.total_minutos
        gp = calc_goal_progress(atual, meta_valor)
        unidade = "pçs" if tipo_meta == "Peças" else "min"
        render_goal_progress(gp, unidade)

    st.divider()
    _section_header("Análise Visual", "")

    tab_temporal, tab_mp, tab_oficinas, tab_detalhe = (
        " Evolução Temporal",
        " Matérias-Primas",
        " Oficinas",
        " Detalhamento",
    )
    # NOTA: usamos st.radio (estilizado em CSS para parecer abas) em vez de
    # st.tabs propositalmente. st.tabs mantém o conteúdo de TODAS as abas no
    # DOM, só escondendo as inativas com display:none. Componentes baseados
    # em iframe (como os gráficos ECharts renderizados via
    # src/shared/echarts_utils.py) medem a largura do container no momento em
    # que são montados — se isso acontece dentro de uma aba escondida, a
    # largura lida é 0 e o gráfico fica em branco, mesmo depois de a aba
    # ficar visível (é uma limitação conhecida de componentes baseados em
    # iframe dentro do Streamlit, não bug nosso — por isso o helper de
    # renderização também usa um ResizeObserver como mitigação extra). Com
    # st.radio, só o bloco da
    # aba selecionada é executado a cada rerun, então o gráfico só é criado
    # quando o container já está visível — nunca nasce com largura 0.
    aba = st.radio(
        "Análise Visual",
        [tab_temporal, tab_mp, tab_oficinas, tab_detalhe],
        horizontal=True,
        label_visibility="collapsed",
        key="recebimento_aba_visual",
    )

    if aba == tab_temporal:
        _chart_card(" Peças Recebidas por Dia")
        df_day = agg_by_day(df)
        if not df_day.empty:
            _echarts(build_line_daily(df_day), "340px")
        else:
            st.info("Sem dados para o período.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        _chart_card(" Peças por Semana")
        df_week = agg_by_week(df)
        if not df_week.empty:
            _echarts(build_line_weekly(df_week), "340px")
        else:
            st.info("Sem dados para o período.")

    elif aba == tab_mp:
        df_mp = agg_by_mp(df)
        _chart_card(" Total de Peças por MP")
        _echarts(build_bar_mp(df_mp), "320px")
        
        st.markdown("<br>", unsafe_allow_html=True)
        _chart_card(" Participação de cada MP (%)")
        _echarts(build_pie_mp(df_mp), "320px")

        st.markdown("<br>", unsafe_allow_html=True)
        _chart_card(" Distribuição Diária por MP (Empilhado)")
        df_pivot = agg_by_mp_day(df)
        if not df_pivot.empty:
            _echarts(build_stacked_mp_day(df_pivot), "320px")

    elif aba == tab_oficinas:
        _chart_card(" Top 15 Oficinas por Peças Recebidas")
        df_ofic = agg_by_oficina(df, top_n=15)
        if not df_ofic.empty:
            _echarts(build_bar_oficinas(df_ofic), "420px")
        else:
            st.info("Sem dados de oficinas para o período.")

    elif aba == tab_detalhe:
        _chart_card(" Dados Detalhados")
        st.markdown(
            f"""
            <div style="
                background:#F0FDF8;border:1.5px solid #D0F0E5;
                border-radius:10px;padding:10px 18px;
                font-size:13px;color:#6B8F7E;margin-bottom:12px;
            ">
                Exibindo <strong style='color:#1A2E25;'>{len(df):,}</strong> registros
            </div>
            """.replace(",", "."),
            unsafe_allow_html=True,
        )
        # Tabela executiva de Recebimento com cabeçalho verde
        from src.recebimento.config import COL_OFICINA, COL_MP, COL_PECAS, COL_MINUTOS
        df_table = df.drop(columns=["SEMANA", "ANO", "ANO_SEM"], errors="ignore")
        cols = df_table.columns.tolist()
        thead_cells = []
        for c in cols:
            if c in [COL_PECAS, COL_MINUTOS]:
                thead_cells.append(f"<th class='num'>{html.escape(str(c))}</th>")
            elif c == COL_DIA:
                thead_cells.append(f"<th style='text-align: center;'>{html.escape(str(c))}</th>")
            else:
                thead_cells.append(f"<th>{html.escape(str(c))}</th>")
        thead = "".join(thead_cells)
        
        rows_html = []
        for idx, row in enumerate(df_table.head(400).itertuples(index=False)):
            cells = []
            for col_idx, val in enumerate(row):
                col_name = cols[col_idx]
                if col_name == COL_DIA and pd.notna(val):
                    cell = f"<td class='date'>{pd.Timestamp(val).strftime('%d/%m/%Y')}</td>"
                elif col_name in [COL_PECAS, COL_MINUTOS]:
                    cell = f"<td class='num'>{int(val):,}".replace(",", ".") + "</td>"
                else:
                    cell = f"<td>{html.escape(str(val)) if pd.notna(val) else ''}</td>"
                cells.append(cell)
            row_cls = "even" if idx % 2 == 0 else "odd"
            rows_html.append(f"<tr class='{row_cls}'>{''.join(cells)}</tr>")
            
        table_html = (
            '<div class="custom-table-wrapper">'
            '<table class="custom-table">'
            f'<thead><tr>{thead}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody>'
            '</table>'
            '</div>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    #st.markdown(
    #    f"""
    #    <div style="
    #        text-align:center;
    #        font-size:12px;
    #        color:#A0C4B3;
    #        padding:12px;
    #        border-top:1.5px solid #D0F0E5;
    #    ">
    #        Painel de Recebimento — v{APP_VERSION} · Desenvolvido com Streamlit & ECharts
    #    </div>
    #    """,
    #    unsafe_allow_html=True,
    #)