"""
page.py — Painel "Detalhe do Recebimento" (planilha STATUS.xlsx).

Pedido original do gestor:
  1. Total de peças e minutos em cada operação (status de RECEBIMENTO) — cards.
  2. Esses totais agrupados por MP e Oficinas.
  3. Tabela com esses dados, no mesmo layout das demais tabelas do app.
  4. Botão de download em PDF, com layout moderno no mesmo padrão de
     cor/tabela do app.
  5. Filtro por data usando a coluna ENVIO como parâmetro.

Arquitetura em camadas (idêntica aos demais módulos do app):
  page.py → ui/ (cards, filters) → metrics.py → data_loader.py
"""

from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from .config import (
    COL_ENVIO, COL_MP, COL_MINUTOS, COL_OFICINA, COL_ORDEM_MESTRE, COL_QTD,
    COL_RECEBIMENTO, COLOR_PRIMARY,
)
from .data_loader import apply_filters, get_filter_options
from .metrics import agg_by_operacao, agg_detalhado, calc_resumo_geral
from .pdf_export import gerar_pdf_detalhe_recebimento
from .ui.cards import render_operacao_cards, render_resumo_cards
from .ui.filters import render_filters


# ===========================================================================
# CSS — mesmo tema neon-aqua / mesma classe .custom-table do Painel de
# Recebimento (src/recebimento/page.py), para manter o layout idêntico.
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
        [data-testid="stSidebar"] {{
            background: #FFFFFF !important;
            border-right: 1.5px solid #D0F0E5;
        }}
        [data-testid="stSidebar"] * {{
            color: #1A2E25 !important;
        }}
        .stButton > button, .stDownloadButton > button {{
            background: linear-gradient(135deg, {COLOR_PRIMARY} 0%, #0C8560 100%) !important;
            color: #1A2E25 !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            opacity: 0.85; transform: translateY(-1px);
        }}
        .stDateInput input {{
            background: #FFFFFF !important;
            color: #1A2E25 !important;
            border: 1.5px solid #C8E8D8 !important;
            border-radius: 8px !important;
        }}
        [data-baseweb="select"] > div {{ background: #FFFFFF !important; border-color: #C8E8D8 !important; }}
        [data-baseweb="tag"] {{ background: {COLOR_PRIMARY} !important; color: #1A2E25 !important; }}
        hr {{ border-top: 1.5px solid #D0F0E5 !important; margin: 20px 0 !important; }}
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
        .custom-table-wrapper {{
            background: #FFFFFF;
            border: 1.5px solid #D0F0E5;
            border-radius: 14px;
            overflow: auto;
            max-height: 460px;
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
        .custom-table tbody tr.total-row {{ background: #E8F5EE !important; font-weight: 800; }}
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
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title: str) -> None:
    st.markdown(
        f"""
        <div class="section-title">{title}</div>
        <div class="section-bar"></div>
        """,
        unsafe_allow_html=True,
    )


def _fmt_int(v) -> str:
    return f"{int(round(float(v))):,}".replace(",", ".")


def _fmt_data(v) -> str:
    if pd.isna(v):
        return "-"
    try:
        return pd.Timestamp(v).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return "-"


def _render_table_detalhada(df_detalhe: pd.DataFrame) -> None:
    """Tabela 'Operação | MP | Oficina | OM | Data do Envio | Peças | Minutos'
    — 1 linha por ordem (sem agregação), no mesmo padrão visual
    (.custom-table) usado nas demais telas."""
    if df_detalhe.empty:
        st.info("Sem dados para os filtros selecionados.")
        return

    headers = ["Operação", "MP", "Oficina", "OM", "Data do Envio", "Peças", "Minutos"]
    thead = "".join(
        f"<th class='num'>{h}</th>" if h in ("Peças", "Minutos") else f"<th>{h}</th>"
        for h in headers
    )

    rows_html = []
    for idx, row in enumerate(df_detalhe.itertuples(index=False)):
        op, mp, oficina, om, envio, pecas, minutos = row
        cls = "even" if idx % 2 == 0 else "odd"
        rows_html.append(
            f"<tr class='{cls}'>"
            f"<td>{html.escape(str(op))}</td>"
            f"<td>{html.escape(str(mp))}</td>"
            f"<td>{html.escape(str(oficina))}</td>"
            f"<td>{html.escape(str(om)) if om else '-'}</td>"
            f"<td>{_fmt_data(envio)}</td>"
            f"<td class='num'>{_fmt_int(pecas)}</td>"
            f"<td class='num'>{_fmt_int(minutos)}</td>"
            f"</tr>"
        )

    total_pecas = df_detalhe[COL_QTD].sum()
    total_minutos = df_detalhe[COL_MINUTOS].sum()
    rows_html.append(
        "<tr class='total-row'>"
        "<td><strong>TOTAL GERAL</strong></td><td></td><td></td><td></td><td></td>"
        f"<td class='num'><strong>{_fmt_int(total_pecas)}</strong></td>"
        f"<td class='num'><strong>{_fmt_int(total_minutos)}</strong></td>"
        "</tr>"
    )

    table_html = (
        '<div class="custom-table-wrapper">'
        '<table class="custom-table">'
        f'<thead><tr>{thead}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


def render_detalhe_recebimento_page(df_full) -> None:
    """Renderiza o painel a partir do DataFrame já carregado na sessão.

    `df_full` pode ser `None` quando a planilha STATUS ainda não foi
    enviada — nesse caso exibimos uma orientação para usar a tela
    "⚙️ Atualizar Bases" em vez de quebrar a página.
    """
    _inject_css()

    st.title("🧾 Detalhe do Recebimento")
    st.caption("Acompanhamento das ordens em aberto por status de recebiment")

    if df_full is None or df_full.empty:
        st.info(
            "Ainda não há dados de **Detalhe do Recebimento** carregados. "
            "Envie a planilha STATUS.xlsx pela tela **⚙️ Atualizar Bases** "
            "(seção \"Detalhe do Recebimento\") para liberar este painel."
        )
        return

    options = get_filter_options(df_full)
    filtros = render_filters(options)

    df = apply_filters(
        df_full,
        date_start=filtros.date_start,
        date_end=filtros.date_end,
        mps=filtros.mps,
        oficinas=filtros.oficinas,
        operacoes=filtros.operacoes,
    )

    if df.empty:
        st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados. Ajuste os filtros na barra lateral.")
        st.stop()

    resumo = calc_resumo_geral(df)
    df_op = agg_by_operacao(df)
    df_detalhe = agg_detalhado(df)

    _section_header("Indicadores Gerais")
    render_resumo_cards(resumo)
    st.markdown("<br>", unsafe_allow_html=True)

    st.divider()
    _section_header("Total de Peças e Minutos por Operação")
    render_operacao_cards(df_op)
    st.divider()
    
    _section_header("Detalhamento por Operação, MP, Oficina, OM e Data do Envio")
    st.markdown(
        f"""
        <div style="
            background:#F0FDF8;border:1.5px solid #D0F0E5;
            border-radius:10px;padding:10px 18px;
            font-size:13px;color:#6B8F7E;margin-bottom:12px;
        ">
            Exibindo <strong style='color:#1A2E25;'>{len(df_detalhe):,}</strong> ordens filtradas,
            com OM e Data do Envio individuais
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )
    _render_table_detalhada(df_detalhe)

    st.markdown("<br>", unsafe_allow_html=True)

    # — Período / filtros em texto, para exibir no cabeçalho do PDF
    d_ini = filtros.date_start or df[COL_ENVIO].min().date()
    d_fim = filtros.date_end or df[COL_ENVIO].max().date()
    periodo_label = f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}"

    partes_filtro = []
    if filtros.operacoes:
        partes_filtro.append(f"Operações: {', '.join(filtros.operacoes)}")
    if filtros.mps:
        partes_filtro.append(f"MP: {', '.join(filtros.mps)}")
    if filtros.oficinas:
        partes_filtro.append(f"Oficinas: {len(filtros.oficinas)} selecionada(s)")
    filtros_label = " · ".join(partes_filtro)

    pdf_bytes = gerar_pdf_detalhe_recebimento(
        df_op=df_op,
        df_detalhe=df_detalhe,
        resumo=resumo,
        periodo_label=periodo_label,
        filtros_label=filtros_label,
        col_recebimento=COL_RECEBIMENTO,
        col_mp=COL_MP,
        col_oficina=COL_OFICINA,
        col_ordem_mestre=COL_ORDEM_MESTRE,
        col_envio=COL_ENVIO,
        col_qtd=COL_QTD,
        col_minutos=COL_MINUTOS,
    )

    st.download_button(
        label="📄 Baixar PDF — Detalhe do Recebimento",
        data=pdf_bytes,
        file_name=f"Detalhe_Recebimento_{date.today().strftime('%d_%m_%Y')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
