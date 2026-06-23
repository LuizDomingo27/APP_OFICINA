"""
metrics.py
==========
Camada de lógica de negócio / cálculo de KPIs do painel "Detalhe do
Recebimento".

Responsabilidades:
  - Totais de peças (QTD) e minutos por operação (status de RECEBIMENTO)
    — usado nos cards.
  - Detalhamento dos mesmos totais agrupados por Operação + MP + Oficina
    — usado na tabela executiva.

Não depende de código de UI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from .config import (
    COL_ENVIO, COL_MP, COL_OFICINA, COL_ORDEM_MESTRE, COL_QTD, COL_MINUTOS,
    COL_RECEBIMENTO,
)


@dataclass
class ResumoGeral:
    """Totais gerais do período filtrado."""
    total_pecas: int
    total_minutos: float
    total_ordens: int
    qtd_operacoes: int
    dias_periodo: int


@st.cache_data
def calc_resumo_geral(df: pd.DataFrame) -> ResumoGeral:
    if df.empty:
        return ResumoGeral(0, 0.0, 0, 0, 0)

    return ResumoGeral(
        total_pecas=int(df[COL_QTD].sum()),
        total_minutos=float(df[COL_MINUTOS].sum()),
        total_ordens=int(len(df)),
        qtd_operacoes=int(df[COL_RECEBIMENTO].nunique()),
        dias_periodo=int(df[COL_ENVIO].dt.date.nunique()),
    )


@st.cache_data
def agg_by_operacao(df: pd.DataFrame) -> pd.DataFrame:
    """Total de peças e minutos por operação (status de RECEBIMENTO).

    Usado para os cards de indicadores — um card por operação.
    """
    if df.empty:
        return pd.DataFrame(columns=["operacao", "pecas", "minutos", "ordens"])

    return (
        df.groupby(COL_RECEBIMENTO)
        .agg(pecas=(COL_QTD, "sum"), minutos=(COL_MINUTOS, "sum"), ordens=(COL_QTD, "count"))
        .reset_index()
        .rename(columns={COL_RECEBIMENTO: "operacao"})
        .sort_values("pecas", ascending=False)
        .reset_index(drop=True)
    )


@st.cache_data
def agg_detalhado(df: pd.DataFrame) -> pd.DataFrame:
    """Detalhamento por Operação, MP, Oficina, OM e Data do Envio.

    Pedido do gestor (sem agregação): 1 linha por ordem, trazendo o
    número da Ordem Mestre (OM) e a Data do Envio de cada ordem — ao
    contrário da versão anterior, que somava Peças/Minutos por
    combinação de Operação + MP + Oficina.

    Usado na tabela executiva (item 2/3 do pedido do gestor) e na
    exportação em PDF.
    """
    colunas = [
        COL_RECEBIMENTO, COL_MP, COL_OFICINA, COL_ORDEM_MESTRE, COL_ENVIO,
        COL_QTD, COL_MINUTOS,
    ]
    if df.empty:
        return pd.DataFrame(columns=colunas)

    out = df.copy()
    if COL_ORDEM_MESTRE not in out.columns:
        out[COL_ORDEM_MESTRE] = ""

    return (
        out[colunas]
        .sort_values([COL_RECEBIMENTO, COL_ENVIO], ascending=[True, False])
        .reset_index(drop=True)
    )
