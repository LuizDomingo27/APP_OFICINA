"""
metrics.py
==========
Camada de lógica de negócio / cálculo de KPIs.

Responsabilidades:
  - Calcular totais, médias, projeções
  - Calcular progresso de meta
  - Produzir agregações por dia / semana / MP / Oficina

Não depende de Streamlit nem de código de UI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional
import streamlit as st
import pandas as pd

from .config import COL_DIA, COL_MP, COL_OFICINA, COL_PECAS, COL_MINUTOS


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KPISummary:
    """Resumo dos principais indicadores de desempenho."""
    total_pecas: int
    total_minutos: float
    dias_trabalhados: int
    semanas_trabalhadas: int
    media_diaria_pecas: float
    media_semanal_pecas: float
    media_diaria_minutos: float


@dataclass
class GoalProgress:
    """Progresso em relação à meta informada."""
    meta: int
    realizado: int
    faltam: int
    percentual: float          # 0–100 +
    bateu_meta: bool


# ---------------------------------------------------------------------------
# KPI calculation
# ---------------------------------------------------------------------------
@st.cache_data
def calc_kpis(df: pd.DataFrame) -> KPISummary:
    """
    Calcula os KPIs principais a partir do DataFrame filtrado.

    Retorna KPISummary com os campos calculados.
    """
    if df.empty:
        return KPISummary(0, 0.0, 0, 0, 0.0, 0.0, 0.0)

    total_pecas   = int(df[COL_PECAS].sum())
    total_minutos = float(df[COL_MINUTOS].sum())

    dias_series     = df[COL_DIA].dt.date.unique()
    dias_trabalhados = len(dias_series)

    # Semanas únicas baseadas no par ANO/SEMANA
    semanas_trabalhadas = df["ANO_SEM"].nunique()

    media_diaria_pecas   = total_pecas   / dias_trabalhados   if dias_trabalhados   else 0.0
    media_semanal_pecas  = total_pecas   / semanas_trabalhadas if semanas_trabalhadas else 0.0
    media_diaria_minutos = total_minutos / dias_trabalhados   if dias_trabalhados   else 0.0

    return KPISummary(
        total_pecas=total_pecas,
        total_minutos=total_minutos,
        dias_trabalhados=dias_trabalhados,
        semanas_trabalhadas=semanas_trabalhadas,
        media_diaria_pecas=round(media_diaria_pecas, 1),
        media_semanal_pecas=round(media_semanal_pecas, 1),
        media_diaria_minutos=round(media_diaria_minutos, 1),
    )


def calc_goal_progress(realizado: int, meta: int) -> GoalProgress:
    """
    Calcula o progresso em relação à meta.

    Parâmetros
    ----------
    realizado : total de peças já recebidas
    meta      : meta em peças definida pelo usuário

    Retorna
    -------
    GoalProgress com faltam, percentual e flag bateu_meta.
    """
    faltam     = max(0, meta - realizado)
    percentual = min((realizado / meta * 100), 999.0) if meta > 0 else 0.0
    bateu_meta = realizado >= meta

    return GoalProgress(
        meta=meta,
        realizado=realizado,
        faltam=faltam,
        percentual=round(percentual, 1),
        bateu_meta=bateu_meta,
    )


# ---------------------------------------------------------------------------
# Aggregation helpers (usados pelos gráficos)
# ---------------------------------------------------------------------------
@st.cache_data
def agg_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega peças e minutos por dia."""
    return (
        df.groupby(df[COL_DIA].dt.date)
        .agg(pecas=(COL_PECAS, "sum"), minutos=(COL_MINUTOS, "sum"))
        .reset_index()
        .rename(columns={COL_DIA: "dia"})
        .sort_values("dia")
    )


@st.cache_data
def agg_by_week(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega peças e minutos por semana (ANO-Wnn)."""
    return (
        df.groupby("ANO_SEM")
        .agg(pecas=(COL_PECAS, "sum"), minutos=(COL_MINUTOS, "sum"))
        .reset_index()
        .rename(columns={"ANO_SEM": "semana"})
        .sort_values("semana")
    )


@st.cache_data
def agg_by_mp(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega peças e minutos por Matéria-Prima."""
    return (
        df.groupby(COL_MP)
        .agg(pecas=(COL_PECAS, "sum"), minutos=(COL_MINUTOS, "sum"))
        .reset_index()
        .rename(columns={COL_MP: "mp"})
        .sort_values("pecas", ascending=False)
    )


@st.cache_data
def agg_by_oficina(df: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    """Agrega peças por Oficina, retornando o top N."""
    return (
        df.groupby(COL_OFICINA)
        .agg(pecas=(COL_PECAS, "sum"))
        .reset_index()
        .rename(columns={COL_OFICINA: "oficina"})
        .sort_values("pecas", ascending=False)
        .head(top_n)
    )


@st.cache_data
def agg_by_mp_day(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega peças por dia e por MP (para gráfico empilhado)."""
    pivot = (
        df.assign(dia=df[COL_DIA].dt.date)
        .groupby(["dia", COL_MP])[COL_PECAS]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    pivot.columns.name = None
    return pivot.sort_values("dia")
