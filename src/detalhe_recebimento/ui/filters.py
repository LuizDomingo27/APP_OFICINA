"""
ui/filters.py
=============
Componente de filtros na sidebar do painel "Detalhe do Recebimento".

O filtro de data usa a coluna ENVIO como parâmetro, conforme pedido
pelo gestor (item 5). MP, Oficina e Operação (status de RECEBIMENTO)
são incluídos como filtros adicionais, seguindo o mesmo padrão já usado
em todas as outras telas do app.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import streamlit as st

from ..config import COLOR_PRIMARY
from src.shared.date_presets import render_date_presets


@dataclass
class FilterSelection:
    date_start: Optional[date]
    date_end: Optional[date]
    mps: List[str]
    oficinas: List[str]
    operacoes: List[str]


def render_filters(options: dict) -> FilterSelection:
    """Renderiza os filtros na sidebar e retorna a seleção.

    Parâmetros
    ----------
    options : dict com chaves 'datas', 'mps', 'oficinas', 'operacoes'
              (retorno de data_loader.get_filter_options)
    """
    st.sidebar.markdown(
        f"""
        <div style="
            font-size:20px; font-weight:900;
            color:#1A2E25; letter-spacing:-0.5px;
            margin-bottom:4px;
        "> Filtros</div>
        <div style="
            width:40px; height:3px;
            background:{COLOR_PRIMARY};
            border-radius:2px; margin-bottom:16px;
        "></div>
        """,
        unsafe_allow_html=True,
    )

    # — Datas (com base em ENVIO)
    all_dates = options["datas"]
    min_date = all_dates[0]
    max_date = all_dates[-1]

    st.sidebar.markdown("**📅 Período (Envio)**")
    render_date_presets(
        st.sidebar,
        min_date,
        max_date,
        marker="detalhe_receb_preset",
        start_key="dr_date_start",
        end_key="dr_date_end",
    )
    date_start = st.sidebar.date_input(
        "De", value=min_date, min_value=min_date, max_value=max_date,
        format="DD/MM/YYYY", key="dr_date_start",
    )
    date_end = st.sidebar.date_input(
        "Até", value=max_date, min_value=min_date, max_value=max_date,
        format="DD/MM/YYYY", key="dr_date_end",
    )

    st.sidebar.divider()

    # — Operação (status de RECEBIMENTO)
    st.sidebar.markdown("Operação")
    operacoes_selecionadas = st.sidebar.multiselect(
        "Selecione uma ou mais operações",
        options=options["operacoes"],
        default=[],
        placeholder="Todas",
        key="dr_operacoes",
    )

    st.sidebar.divider()

    # — Matérias-Primas
    st.sidebar.markdown("Matéria-Prima")
    mps_selecionadas = st.sidebar.multiselect(
        "Selecione um ou mais MPs",
        options=options["mps"],
        default=[],
        placeholder="Todas",
        key="dr_mps",
    )

    st.sidebar.divider()

    # — Oficinas
    st.sidebar.markdown("Oficina")
    oficinas_selecionadas = st.sidebar.multiselect(
        "Selecione as oficinas",
        options=options["oficinas"],
        default=[],
        placeholder="Todas",
        key="dr_oficinas",
    )

    st.sidebar.divider()

    return FilterSelection(
        date_start=date_start if date_start else None,
        date_end=date_end if date_end else None,
        mps=mps_selecionadas,
        oficinas=oficinas_selecionadas,
        operacoes=operacoes_selecionadas,
    )
