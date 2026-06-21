"""Cálculo de métricas e agregações do dashboard."""

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.envio.config.settings import TOP_MP, TOP_OFICINAS


@dataclass(frozen=True)
class DashboardMetrics:
    total_pecas: float
    total_minutos: float
    hoje_pecas: float
    hoje_minutos: float
    semana_pecas: float
    semana_minutos: float
    oficinas_ativas: int
    mp_count: int
    pdv_count: int
    referencia_dia: date
    semana_inicio: date


@dataclass(frozen=True)
class GoalProgress:
    """Progresso em relação à meta informada (peças ou minutos)."""
    meta: float
    realizado: float
    faltam: float
    percentual: float          # 0–100 +
    bateu_meta: bool


def calc_goal_progress(realizado: float, meta: float) -> GoalProgress:
    """
    Calcula o progresso em relação à meta de Envio.

    Parâmetros
    ----------
    realizado : total já enviado (peças ou minutos, conforme o tipo escolhido)
    meta      : meta definida pelo usuário, na mesma unidade de `realizado`

    Retorna
    -------
    GoalProgress com faltam, percentual e flag bateu_meta.
    """
    faltam     = max(0.0, meta - realizado)
    percentual = min((realizado / meta * 100), 999.0) if meta > 0 else 0.0
    bateu_meta = realizado >= meta and meta > 0

    return GoalProgress(
        meta=meta,
        realizado=realizado,
        faltam=faltam,
        percentual=round(percentual, 1),
        bateu_meta=bateu_meta,
    )


@st.cache_data(show_spinner=False)
def compute_metrics(df: pd.DataFrame, fallback_date: date) -> DashboardMetrics:
    """Calcula KPIs principais a partir do dataframe filtrado."""
    if df.empty:
        ref = fallback_date
        return DashboardMetrics(
            total_pecas=0,
            total_minutos=0,
            hoje_pecas=0,
            hoje_minutos=0,
            semana_pecas=0,
            semana_minutos=0,
            oficinas_ativas=0,
            mp_count=0,
            pdv_count=0,
            referencia_dia=ref,
            semana_inicio=ref - timedelta(days=ref.weekday()),
        )

    referencia = df["ENVIO"].max().date()
    semana_inicio = referencia - timedelta(days=referencia.weekday())
    dia_mask = df["ENVIO"].dt.date == referencia
    semana_mask = (df["ENVIO"].dt.date >= semana_inicio) & (df["ENVIO"].dt.date <= referencia)

    return DashboardMetrics(
        total_pecas=df["QTD"].sum(),
        total_minutos=df["MINUTOS"].sum(),
        hoje_pecas=df.loc[dia_mask, "QTD"].sum(),
        hoje_minutos=df.loc[dia_mask, "MINUTOS"].sum(),
        semana_pecas=df.loc[semana_mask, "QTD"].sum(),
        semana_minutos=df.loc[semana_mask, "MINUTOS"].sum(),
        oficinas_ativas=df["OFICINA"].nunique(),
        mp_count=df["MP"].nunique(),
        pdv_count=df["PDV"].nunique(),
        referencia_dia=referencia,
        semana_inicio=semana_inicio,
    )


@st.cache_data(show_spinner=False)
def aggregate_oficinas(df: pd.DataFrame) -> pd.DataFrame:
    """Top oficinas por quantidade de peças (ordem decrescente para colunas)."""
    return (
        df.groupby("OFICINA", as_index=False)
        .agg(QTD=("QTD", "sum"), MIN=("MINUTOS", "sum"))
        .sort_values("QTD", ascending=False)
        .head(TOP_OFICINAS)
    )


@st.cache_data(show_spinner=False)
def aggregate_mp(df: pd.DataFrame) -> pd.DataFrame:
    """Distribuição por matéria-prima."""
    if "MP" not in df.columns:
        return pd.DataFrame(columns=["MP", "QTD"])
    return (
        df.groupby("MP", as_index=False)
        .agg(QTD=("QTD", "sum"))
        .sort_values("QTD", ascending=False)
        .head(TOP_MP)
    )


@st.cache_data(show_spinner=False)
def aggregate_frete(df: pd.DataFrame) -> pd.DataFrame:
    """Peças enviadas por tipo de frete."""
    if "FRETE" not in df.columns:
        return pd.DataFrame(columns=["FRETE", "QTD", "MIN", "Envios"])
    count_col = "ORDEM" if "ORDEM" in df.columns else "QTD"
    return (
        df.groupby("FRETE", as_index=False)
        .agg(QTD=("QTD", "sum"), MIN=("MINUTOS", "sum"), Envios=(count_col, "count"))
        .sort_values("QTD", ascending=False)
    )


@st.cache_data(show_spinner=False)
def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Série temporal diária de peças e minutos."""
    return (
        df.groupby(df["ENVIO"].dt.date)
        .agg(QTD=("QTD", "sum"), MIN=("MINUTOS", "sum"))
        .reset_index()
        .rename(columns={"ENVIO": "DATA"})
    )
