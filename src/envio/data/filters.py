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
    """Aplica filtros de período e dimensões sobre o dataframe base.

    Pedidos sem data de ENVIO válida (ex.: "Não informado" na planilha)
    só são incluídos quando o período selecionado cobre o intervalo
    COMPLETO da base (ou seja, quando não há de fato uma restrição de
    período em vigor — é o estado padrão ao abrir a página). Isso é o
    que faz o card de total bater com o total real da planilha quando
    nenhum filtro de data foi aplicado.

    Assim que o usuário restringe o período (ex.: "01/06 até hoje"),
    essas linhas deixam de entrar — elas não têm como pertencer a um
    período específico, então o comportamento correto é o mesmo de um
    filtro de data numa planilha: ficam de fora. Sem essa diferenciação,
    qualquer período filtrado ficava inflado pelo total das linhas sem
    data (bug identificado em 2026-06-21, validado contra filtro manual
    no Excel).
    """
    data_min = df["ENVIO"].min()
    data_max = df["ENVIO"].max()
    periodo_completo = (
        pd.notna(data_min)
        and pd.notna(data_max)
        and filters.date_start <= data_min.date()
        and filters.date_end >= data_max.date()
    )

    mask = (
        (df["ENVIO"].dt.date >= filters.date_start)
        & (df["ENVIO"].dt.date <= filters.date_end)
    )
    if periodo_completo:
        mask |= df["ENVIO"].isna()
    if filters.mp:
        mask &= df["MP"].isin(filters.mp)
    if filters.pdv:
        mask &= df["PDV"].isin(filters.pdv)
    if filters.oficina:
        mask &= df["OFICINA"].isin(filters.oficina)
    return df.loc[mask]
