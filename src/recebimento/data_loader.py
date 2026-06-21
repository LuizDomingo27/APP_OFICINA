"""
data_loader.py
==============
Camada de acesso a dados.

Responsabilidades:
  - Leitura do arquivo Excel (recebido como bytes do upload na tela de
    "Atualizar Bases") ou leitura da tabela já persistida em SQLite
  - Normalização e limpeza de dados (datas, MPs)
  - Cache em memória via st.cache_data
  - Filtragem por data / MP / Oficina

Não contém lógica de negócio nem código de UI.

Persistência (migrado para SQLite — ver `src/shared/sql_store.py`):
  - A base de Recebimento sobe por COMPLETO todo dia (histórico inteiro,
    não incremental). Por isso a tela de "Atualizar Bases" lê o Excel
    novo, normaliza com `_normalize_raw` e grava a tabela inteira de
    uma vez via `sql_store.substituir_tabela("recebimento", df)`.
  - No dia a dia (sessão nova, sem upload), os dados vêm de
    `load_from_db()`, que lê a tabela já normalizada do `app.db` —
    mais rápido que reabrir o .xlsx, porque não há mais reparsing de
    Excel a cada sessão.
  - `load_raw(file_bytes)` continua existindo (e cacheada por conteúdo
    do arquivo) para o caso de upload direto de um .xlsx — ela só chama
    `_normalize_raw` por dentro, então a regra de negócio de limpeza
    fica num único lugar.
"""

from io import BytesIO
from typing import List, Optional

import pandas as pd
import streamlit as st

from .config import (
    COL_DIA, COL_MP, COL_OFICINA,
    COL_PECAS, COL_MINUTOS, MP_NORM,
)


class DataLoadError(Exception):
    """Erro amigável para falhas no carregamento do arquivo de dados."""


def _normalize_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica a limpeza/normalização de negócio a um DataFrame já lido
    (de Excel OU de SQLite). Função pura, sem I/O e sem `st.cache_data`
    — por isso pode ser chamada tanto pelo app (dentro de `load_raw`)
    quanto por scripts fora do Streamlit (ex.: `scripts/seed_recebimento.py`).
    """
    colunas_esperadas = {COL_DIA, COL_MP, COL_OFICINA, COL_PECAS, COL_MINUTOS}
    colunas_faltantes = colunas_esperadas - set(df.columns)
    if colunas_faltantes:
        raise DataLoadError(
            f"A planilha de recebimento está faltando as colunas: "
            f"{', '.join(sorted(colunas_faltantes))}."
        )

    df = df.copy()

    # — Garantir que DIA é datetime
    df[COL_DIA] = pd.to_datetime(df[COL_DIA], errors="coerce")

    # — Normalizar MP (ex.: "Malha" → "MALHA")
    df[COL_MP] = (
        df[COL_MP]
        .astype(str)
        .str.strip()
        .replace(MP_NORM)
        .str.upper()
    )

    # — Converter numéricos com segurança
    df[COL_PECAS]   = pd.to_numeric(df[COL_PECAS],   errors="coerce").fillna(0)
    df[COL_MINUTOS] = pd.to_numeric(df[COL_MINUTOS], errors="coerce").fillna(0)

    # — Garantir que OFICINA é sempre string (evita NaN float)
    df[COL_OFICINA] = df[COL_OFICINA].fillna("").astype(str).str.strip()

    # — Remover linhas com data inválida
    df = df.dropna(subset=[COL_DIA])

    # — Adicionar colunas auxiliares de tempo
    df["SEMANA"]  = df[COL_DIA].dt.isocalendar().week.astype(int)
    df["ANO"]     = df[COL_DIA].dt.isocalendar().year.astype(int)
    df["ANO_SEM"] = df["ANO"].astype(str) + "-W" + df["SEMANA"].astype(str).str.zfill(2)

    return df


@st.cache_data(show_spinner="Lendo planilha de recebimento...")
def load_raw(file_bytes: bytes) -> pd.DataFrame:
    """
    Carrega o Excel a partir dos bytes do upload e aplica `_normalize_raw`.
    Resultado é cacheado (em memória) enquanto o conteúdo do arquivo for o mesmo.

    Levanta DataLoadError com mensagem amigável caso o arquivo
    esteja vazio, corrompido ou com colunas faltantes.
    """
    try:
        df = pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise DataLoadError(
            "Não foi possível ler a planilha de recebimento. "
            "Verifique se ela não está corrompida e se está no formato .xlsx válido. "
            f"Detalhe técnico: {exc}"
        ) from exc

    return _normalize_raw(df)


@st.cache_data(show_spinner="Carregando Recebimento do banco...")
def load_from_db() -> pd.DataFrame:
    """Lê a tabela 'recebimento' já normalizada do SQLite (`app.db`).

    Os dados já chegam normalizados (foram normalizados antes de serem
    gravados, em `_normalize_raw`), mas o SQLite não preserva dtype de
    datetime — por isso reconvertemos DIA aqui após a leitura.

    Invalidação: depois de uma substituição de base bem-sucedida (tela
    "Atualizar Bases"), o código chama `load_from_db.clear()` para que
    a próxima chamada já reflita os dados novos, em vez de esperar o
    cache expirar.
    """
    from src.shared import sql_store

    df = sql_store.carregar_tabela("recebimento")
    df[COL_DIA] = pd.to_datetime(df[COL_DIA], errors="coerce")
    df[COL_OFICINA] = df[COL_OFICINA].astype(str)
    df[COL_MP] = df[COL_MP].astype(str)
    return df


@st.cache_data(show_spinner=False)
def get_filter_options(df: pd.DataFrame) -> dict:
    """
    Retorna as opções únicas disponíveis para cada filtro,
    já ordenadas para exibição.
    """
    return {
        "datas":    sorted(df[COL_DIA].dt.date.unique()),
        "mps":      sorted(df[COL_MP].dropna().unique()),
        "oficinas": sorted(
            df[COL_OFICINA]
            .dropna()                  # remove NaN (float) antes do sort
            .astype(str)
            .str.strip()
            .unique()
        ),
    }


def apply_filters(
    df: pd.DataFrame,
    date_start: Optional[object] = None,
    date_end: Optional[object] = None,
    mps: Optional[List[str]] = None,
    oficinas: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Aplica os filtros selecionados pelo usuário ao DataFrame.

    Parâmetros
    ----------
    df         : DataFrame completo (saída de load_raw)
    date_start : data inicial (inclusive), ou None para sem limite
    date_end   : data final   (inclusive), ou None para sem limite
    mps        : lista de MPs selecionadas; None ou lista vazia = todas
    oficinas   : lista de oficinas;         None ou lista vazia = todas

    Retorna
    -------
    DataFrame filtrado.
    """
    mask = pd.Series(True, index=df.index)

    if date_start:
        mask &= df[COL_DIA].dt.date >= date_start
    if date_end:
        mask &= df[COL_DIA].dt.date <= date_end
    if mps:
        mask &= df[COL_MP].isin(mps)
    if oficinas:
        mask &= df[COL_OFICINA].str.strip().isin(oficinas)

    return df[mask].copy()
