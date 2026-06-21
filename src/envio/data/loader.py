"""Carregamento e normalização da planilha de envios.

Persistência (migrado para SQLite — ver `src/shared/sql_store.py`):
  - Igual ao módulo `recebimento`: a base de Envios sobe por COMPLETO
    todo dia, então "atualizar a base" é sempre uma substituição total
    da tabela `envio`, feita via `sql_store.substituir_tabela`.
  - `load_dataset_from_bytes(file_bytes)` continua existindo para ler e
    validar um .xlsx recém-enviado (tela inicial / "Atualizar Bases").
    O `LoadedDataset.df` resultante é o que é gravado no banco.
  - No dia a dia (sessão nova, sem upload), os dados vêm de
    `load_from_db()`, que lê a tabela já normalizada do `app.db`.
    O SQLite não preserva dtype `category`/datetime — por isso
    `_recast_after_db` reaplica esses tipos depois da leitura.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st

from src.envio.config.settings import REQUIRED_COLUMNS, TEXT_COLUMNS

EXCEL_ENGINE = "calamine"


class PlanilhaInvalidaError(Exception):
    """Levantado quando a planilha enviada não tem o formato esperado."""


@dataclass(frozen=True)
class LoadedDataset:
    df: pd.DataFrame
    cache_key: str
    date_min: date
    date_max: date
    mp_options: tuple[str, ...]
    pdv_options: tuple[str, ...]
    oficina_options: tuple[str, ...]


def _validate_columns(df: pd.DataFrame) -> None:
    faltantes = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if faltantes:
        colunas_lidas = ", ".join(df.columns.astype(str)) or "(nenhuma)"
        raise PlanilhaInvalidaError(
            "A planilha não contém a(s) coluna(s) obrigatória(s): "
            f"{', '.join(faltantes)}. "
            f"Colunas encontradas: {colunas_lidas}."
        )


def _normalize(df: pd.DataFrame, *, dayfirst: bool = True) -> pd.DataFrame:
    """
    `dayfirst` precisa refletir a ORIGEM da string de data, não ser sempre
    True:
      - Upload de planilha (.xlsx): a coluna ENVIO chega como texto no
        formato brasileiro "DD/MM/AAAA" (ex.: "02/01/2026" = 2 de
        janeiro) → exige dayfirst=True para não inverter dia e mês.
      - Leitura de volta do SQLite (`load_from_db`): o pandas grava
        datetime64 como string ISO "AAAA-MM-DD HH:MM:SS" ao persistir
        via `to_sql`. Reaplicar dayfirst=True nesse formato é o bug que
        causava totais errados ao filtrar por período (identificado em
        2026-06-21): "2026-01-02" (2 de janeiro) virava silenciosamente
        "2026-02-01" (1 de fevereiro) sempre que dia e mês eram ambos
        ≤12, e virava NaT nas demais combinações inválidas — embaralhando
        boa parte da base a cada leitura do banco.
    """
    df = df.copy()
    df.columns = [c.strip().upper() for c in df.columns]
    _validate_columns(df)

    df["ENVIO"] = pd.to_datetime(df["ENVIO"], dayfirst=dayfirst, errors="coerce")
    df["QTD"] = pd.to_numeric(df["QTD"], errors="coerce").fillna(0)
    df["MINUTOS"] = pd.to_numeric(df["MINUTOS"], errors="coerce").fillna(0)

    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().astype("category")

    # IMPORTANTE: linhas com ENVIO inválido/ausente (ex.: "Não informado")
    # NÃO são descartadas. Antes, um `dropna(subset=["ENVIO"])` aqui jogava
    # fora pedidos que já tinham QTD/MINUTOS reais só por não terem data de
    # envio preenchida — isso fazia os cards de Peças/Minutos do painel
    # ficarem menores que o total real da planilha (bug identificado em
    # 2026-06-21: ~463 linhas, ~376k peças e ~4,85M minutos "perdidos").
    # Essas linhas continuam no dataset (ENVIO fica NaT) para entrar nos
    # totais agregados; o que depende de uma data concreta (filtro de
    # período, série diária, "hoje"/"semana") simplesmente as ignora
    # naturalmente, pois comparações com NaT são sempre False.
    df = df.reset_index(drop=True)
    if df.empty:
        raise PlanilhaInvalidaError(
            "A planilha não contém nenhuma linha de dados."
        )
    return df


def _read_excel(file_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_excel(BytesIO(file_bytes), engine=EXCEL_ENGINE)
    except (ImportError, ValueError):
        return pd.read_excel(BytesIO(file_bytes))


def _build_metadata(df: pd.DataFrame, cache_key: str) -> LoadedDataset:
    return LoadedDataset(
        df=df,
        cache_key=cache_key,
        date_min=df["ENVIO"].min().date(),
        date_max=df["ENVIO"].max().date(),
        mp_options=tuple(sorted(df["MP"].dropna().astype(str).unique().tolist())),
        pdv_options=tuple(sorted(df["PDV"].dropna().astype(str).unique().tolist())),
        oficina_options=tuple(sorted(df["OFICINA"].dropna().astype(str).unique().tolist())),
    )


@st.cache_data(show_spinner="Lendo planilha de envios...")
def load_dataset_from_bytes(file_bytes: bytes) -> LoadedDataset:
    """Lê, valida e normaliza a planilha de envios a partir dos bytes do upload.

    Levanta PlanilhaInvalidaError com mensagem amigável caso a planilha
    não tenha as colunas obrigatórias ou não contenha linhas válidas.
    """
    cache_key = hashlib.sha256(file_bytes).hexdigest()
    raw = _read_excel(file_bytes)
    df = _normalize(raw)
    return _build_metadata(df, cache_key)


@st.cache_data(show_spinner="Carregando Envios do banco...")
def load_from_db() -> LoadedDataset:
    """Lê a tabela 'envio' já normalizada do SQLite (`app.db`).

    `_normalize` é idempotente (já é chamada em todo upload), então
    reusá-la aqui — em vez de duplicar a lógica de conversão de tipos —
    garante que o caminho "vindo do banco" e o caminho "vindo de upload"
    nunca fiquem dessincronizados.

    Invalidação: depois de uma substituição de base bem-sucedida (tela
    "Atualizar Bases"), o código chama `load_from_db.clear()` para que
    a próxima chamada já reflita os dados novos.
    """
    from src.shared import sql_store

    df_bruto = sql_store.carregar_tabela("envio")
    df = _normalize(df_bruto, dayfirst=False)

    _, loaded_at = sql_store.info_tabela("envio")
    cache_key = hashlib.sha256(f"envio::{loaded_at}::{len(df)}".encode()).hexdigest()
    return _build_metadata(df, cache_key)
