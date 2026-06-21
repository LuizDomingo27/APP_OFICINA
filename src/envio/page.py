"""Página do dashboard de Envios dentro do sistema unificado.

A planilha já foi validada e carregada na tela inicial (src/shared/home.py).
Esta página apenas renderiza o painel a partir do LoadedDataset em sessão.
"""

import streamlit as st

from src.envio.data.loader import LoadedDataset
from src.envio.ui.dashboard import render_dashboard
from src.envio.ui.sidebar import render_sidebar
from src.envio.ui.styles import build_global_css
#from src.shared.state import resetar_sessao


def render_envio_page(dataset: LoadedDataset) -> None:
    st.markdown(build_global_css(), unsafe_allow_html=True)

    with st.sidebar:
        filters = render_sidebar(dataset)

    render_dashboard(dataset.df, filters)
