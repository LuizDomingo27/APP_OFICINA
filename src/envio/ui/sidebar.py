"""Sidebar: upload e filtros."""

import streamlit as st

from src.envio.data.filters import FilterState
from src.envio.data.loader import LoadedDataset
from src.shared.date_presets import render_date_presets


def render_sidebar(dataset: LoadedDataset) -> FilterState:
    st.markdown("### Filtros")

    min_d, max_d = dataset.date_min, dataset.date_max
    date_key = "date_range_filter"

    # Se um novo arquivo foi carregado, descarta o período salvo da planilha
    # anterior (poderia ficar fora do intervalo min/max do novo dataset).
    if st.session_state.get("_dataset_cache_key") != dataset.cache_key:
        st.session_state["_dataset_cache_key"] = dataset.cache_key
        st.session_state.pop(date_key, None)

    render_date_presets(st.sidebar, min_d, max_d, marker="envio_preset", range_key=date_key)

    date_range = st.date_input(
        "Período de envio",
        value=st.session_state.get(date_key, (min_d, max_d)),
        min_value=min_d,
        max_value=max_d,
        format="DD/MM/YYYY",
        key=date_key,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        d_ini, d_fim = date_range
    else:
        d_ini, d_fim = min_d, max_d

    sel_mp = st.multiselect("Matéria-Prima (MP)", dataset.mp_options)
    sel_pdv = st.multiselect("PDV", dataset.pdv_options)
    sel_of = st.multiselect("Oficina", dataset.oficina_options)

    filters = FilterState(
        date_start=d_ini,
        date_end=d_fim,
        mp=tuple(sel_mp),
        pdv=tuple(sel_pdv),
        oficina=tuple(sel_of),
    )
    return filters
