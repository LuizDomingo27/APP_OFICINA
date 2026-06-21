"""Filtros e estado de seleção do sidebar."""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class FilterState:
    date_start: date
    date_end: date
    mp: tuple[str, ...]
    pdv: tuple[str, ...]
    oficina: tuple[str, ...]


@dataclass(frozen=True)
class MetaState:
    tipo: str
    valor: float


def apply_filters(df: pd.DataFrame, filters: FilterState) -> pd.DataFrame:
    """Aplica filtros de período e dimensões sobre o dataframe base."""
    mask = (
        (df["ENVIO"].dt.date >= filters.date_start)
        & (df["ENVIO"].dt.date <= filters.date_end)
    )
    if filters.mp:
        mask &= df["MP"].isin(filters.mp)
    if filters.pdv:
        mask &= df["PDV"].isin(filters.pdv)
    if filters.oficina:
        mask &= df["OFICINA"].isin(filters.oficina)
    return df.loc[mask]
