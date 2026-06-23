"""
data_loader.py
==============
Camada de acesso a dados do painel "Detalhe do Recebimento" (planilha
STATUS.xlsx — coluna RECEBIMENTO traz o status/operação de cada ordem,
ex.: "Agua. Reposição", "Coletando datas", "Procurando" etc.).

Segue exatamente o mesmo padrão dos demais módulos já migrados para
SQLite (ver `src/recebimento/data_loader.py` e
`src/acompanhamento/loader.py`):
  - `_normalize_raw()` é uma função pura (sem I/O, sem `st.cache_data`)
    que aplica toda a limpeza de negócio — chamada tanto a partir do
    Excel (upload) quanto a partir do SQLite (leitura do banco).
  - `dayfirst` só importa para a coluna ENVIO (e DEAD LINE, quando
    presente como texto): no upload a planilha traz texto brasileiro
    "DD/MM/AAAA" (exige dayfirst=True); depois de um round-trip pelo
    SQLite a mesma coluna volta como string ISO "AAAA-MM-DD HH:MM:SS"
    (exige dayfirst=False — reaplicar dayfirst=True sobre uma data ISO
    inverte dia/mês sempre que ambos são ≤12, bug já visto e corrigido
    em outros módulos deste app).
  - `load_raw()` (upload) e `load_from_db()` (sessão normal) são
    cacheadas com `st.cache_data`; a normalização pura não é.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Optional

import pandas as pd
import streamlit as st

from .config import (
    COL_DEADLINE, COL_DIAS_ATRASO, COL_ENVIO, COL_MES, COL_MP,
    COL_OFICINA, COL_ORDEM_MESTRE, COL_QTD, COL_MINUTOS,
    COL_RECEBIMENTO, COL_SITUACAO, SQL_TABLE_NAME,
)


class DataLoadError(Exception):
    """Erro amigável para falhas no carregamento da planilha de detalhe do recebimento."""


def _normalize_raw(df: pd.DataFrame, *, dayfirst: bool = True) -> pd.DataFrame:
    """Aplica a limpeza/normalização de negócio a um DataFrame já lido
    (de Excel OU de SQLite). Função pura — pode ser chamada tanto pelo
    app quanto por scripts de seed fora do Streamlit.
    """
    colunas_esperadas = {
        COL_OFICINA, COL_ENVIO, COL_QTD, COL_MINUTOS, COL_MP, COL_RECEBIMENTO,
    }
    colunas_faltantes = colunas_esperadas - set(df.columns)
    if colunas_faltantes:
        raise DataLoadError(
            f"A planilha de detalhe do recebimento está faltando as colunas: "
            f"{', '.join(sorted(colunas_faltantes))}."
        )

    df = df.copy()

    # — ENVIO é a coluna primária de filtro temporal
    df[COL_ENVIO] = pd.to_datetime(df[COL_ENVIO], dayfirst=dayfirst, errors="coerce")
    df = df.dropna(subset=[COL_ENVIO])

    # — DEAD LINE (opcional, planilha às vezes traz datetime nativo, às
    # vezes texto "DD/MM/AAAA" misturados na mesma coluna)
    if COL_DEADLINE in df.columns:
        df[COL_DEADLINE] = pd.to_datetime(df[COL_DEADLINE], dayfirst=dayfirst, errors="coerce")

    # — Texto / categorias
    df[COL_MP] = df[COL_MP].fillna("").astype(str).str.strip().str.upper()
    df[COL_OFICINA] = df[COL_OFICINA].fillna("").astype(str).str.strip()
    df[COL_RECEBIMENTO] = (
        df[COL_RECEBIMENTO].fillna("Não informado").astype(str).str.strip()
    )
    if COL_SITUACAO in df.columns:
        df[COL_SITUACAO] = df[COL_SITUACAO].fillna("").astype(str).str.strip()
    if COL_ORDEM_MESTRE in df.columns:
        df[COL_ORDEM_MESTRE] = df[COL_ORDEM_MESTRE].astype(str).str.strip()

    # — Numéricos
    df[COL_QTD] = pd.to_numeric(df[COL_QTD], errors="coerce").fillna(0)
    df[COL_MINUTOS] = pd.to_numeric(df[COL_MINUTOS], errors="coerce").fillna(0)
    if COL_DIAS_ATRASO in df.columns:
        df[COL_DIAS_ATRASO] = pd.to_numeric(df[COL_DIAS_ATRASO], errors="coerce")
    if COL_MES in df.columns:
        df[COL_MES] = pd.to_numeric(df[COL_MES], errors="coerce")

    # — Colunas auxiliares de tempo (mesmo padrão dos outros módulos)
    df["SEMANA"] = df[COL_ENVIO].dt.isocalendar().week.astype(int)
    df["ANO"] = df[COL_ENVIO].dt.isocalendar().year.astype(int)
    df["ANO_SEM"] = df["ANO"].astype(str) + "-W" + df["SEMANA"].astype(str).str.zfill(2)

    return df


@st.cache_data(show_spinner="Lendo planilha de detalhe do recebimento...")
def load_raw(file_bytes: bytes) -> pd.DataFrame:
    """Carrega o Excel a partir dos bytes do upload e aplica `_normalize_raw`."""
    try:
        df = pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise DataLoadError(
            "Não foi possível ler a planilha de detalhe do recebimento. "
            "Verifique se ela não está corrompida e se está no formato .xlsx válido. "
            f"Detalhe técnico: {exc}"
        ) from exc

    return _normalize_raw(df, dayfirst=True)


@st.cache_data(show_spinner="Carregando Detalhe do Recebimento do banco...")
def load_from_db() -> pd.DataFrame:
    """Lê a tabela já normalizada do SQLite (`app.db`).

    Invalidação: depois de uma substituição de base bem-sucedida (tela
    "Atualizar Bases"), o código chama `load_from_db.clear()`.
    """
    from src.shared import sql_store

    df_bruto = sql_store.carregar_tabela(SQL_TABLE_NAME)
    return _normalize_raw(df_bruto, dayfirst=False)


@st.cache_data(show_spinner=False)
def get_filter_options(df: pd.DataFrame) -> dict:
    """Retorna as opções únicas disponíveis para cada filtro, já ordenadas."""
    return {
        "datas": sorted(df[COL_ENVIO].dt.date.unique()),
        "mps": sorted(df[COL_MP].dropna().unique()),
        "oficinas": sorted(
            df[COL_OFICINA].dropna().astype(str).str.strip().unique()
        ),
        "operacoes": sorted(
            df[COL_RECEBIMENTO].dropna().astype(str).str.strip().unique()
        ),
    }


def apply_filters(
    df: pd.DataFrame,
    date_start: Optional[object] = None,
    date_end: Optional[object] = None,
    mps: Optional[List[str]] = None,
    oficinas: Optional[List[str]] = None,
    operacoes: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Aplica os filtros selecionados pelo usuário ao DataFrame.

    Parâmetros
    ----------
    df         : DataFrame completo (saída de load_raw / load_from_db)
    date_start : data inicial (inclusive) com base em ENVIO, ou None
    date_end   : data final   (inclusive) com base em ENVIO, ou None
    mps        : lista de MPs selecionadas; None/vazia = todas
    oficinas   : lista de oficinas;         None/vazia = todas
    operacoes  : lista de status de RECEBIMENTO; None/vazia = todos
    """
    mask = pd.Series(True, index=df.index)

    if date_start:
        mask &= df[COL_ENVIO].dt.date >= date_start
    if date_end:
        mask &= df[COL_ENVIO].dt.date <= date_end
    if mps:
        mask &= df[COL_MP].isin(mps)
    if oficinas:
        mask &= df[COL_OFICINA].str.strip().isin(oficinas)
    if operacoes:
        mask &= df[COL_RECEBIMENTO].str.strip().isin(operacoes)

    return df[mask].copy()
