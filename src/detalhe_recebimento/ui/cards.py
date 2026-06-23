"""
ui/cards.py
===========
Componentes de UI para os cards de indicadores do painel "Detalhe do
Recebimento".

Dois conjuntos de cards:
  - `render_resumo_cards`: 4 cards gerais (peças, minutos, ordens, operações).
  - `render_operacao_cards`: 1 card por operação (status de RECEBIMENTO),
    com o total de peças e minutos daquela operação — exatamente o que
    foi pedido pelo gestor (item 1).

Mesmo visual dos cards já usados no Painel de Recebimento
(`src/recebimento/ui/cards.py`) — borda esquerda colorida, fundo branco,
sombra leve.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..config import COLOR_PRIMARY, COLOR_TEXT, COLOR_TEXT_MUTED, CHART_COLORS


def _fmt_int(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", ".")


def _metric_card(label: str, value: str, subtitle: str = "", accent: str = COLOR_PRIMARY) -> str:
    return f"""
    <div style="
        background: #FFFFFF;
        border: 1.5px solid #D0F0E5;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 2px 12px rgba(14,159,110,0.10);
        border-left: 5px solid {accent};
        height: 100%;
    ">
        <div style="
            font-size: 12.5px;
            color: {COLOR_TEXT_MUTED};
            font-weight: 600;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        " title="{label}">{label}</div>
        <div style="
            font-size: 28px;
            font-weight: 900;
            color: {COLOR_TEXT};
            line-height: 1.15;
            margin-bottom: 4px;
        ">{value}</div>
        <div style="
            font-size: 12px;
            color: {COLOR_TEXT_MUTED};
        ">{subtitle}</div>
    </div>
    """


def render_resumo_cards(resumo) -> None:
    """4 cards de resumo geral do período filtrado."""
    cols = st.columns(4)
    cards = [
        ("Total de Peças", _fmt_int(resumo.total_pecas), f"{resumo.total_ordens} ordens no período"),
        ("Total de Minutos", _fmt_int(resumo.total_minutos), f"≈ {resumo.total_minutos/60:,.0f}h".replace(",", ".")),
        ("Operações em Aberto", str(resumo.qtd_operacoes), "status distintos de recebimento"),
        ("Dias no Período", str(resumo.dias_periodo), "dias com envio registrado"),
    ]
    
    for col, (label, value, subtitle) in zip(cols, cards):
        with col:
            st.markdown(_metric_card(label, value, subtitle), unsafe_allow_html=True)
            

def render_operacao_cards(df_op: pd.DataFrame) -> None:
    """1 card por operação (status de RECEBIMENTO) com total de peças e minutos.

    Layout em grade de até 4 colunas por linha, igual ao padrão dos
    demais cards do app.
    """
    if df_op.empty:
        st.info("Sem dados de operação para o período selecionado.")
        return

    registros = df_op.to_dict("records")
    n_cols = 4

    for inicio in range(0, len(registros), n_cols):
        bloco = registros[inicio: inicio + n_cols]
        cols = st.columns(n_cols)
        for col, reg in zip(cols, bloco):
            accent = CHART_COLORS[(inicio + bloco.index(reg)) % len(CHART_COLORS)]
            with col:
                st.markdown(
                    _metric_card(
                        label=str(reg["operacao"]),
                        value=f"{_fmt_int(reg['pecas'])} pçs",
                        subtitle=f"{_fmt_int(reg['minutos'])} min · {int(reg['ordens'])} ordens",
                        accent=accent,
                    ),
                    unsafe_allow_html=True,
                )
        st.markdown("<br>", unsafe_allow_html=True)  # Linha divisória entre blocos de cards
                
        # Preenche colunas vazias da última linha (visual apenas)
        for col in cols[len(bloco):]:
            with col:
                st.empty()
