"""Ponto de entrada do sistema unificado — Envio & Recebimento.

Fluxo:
  1. As bases (Envio, Recebimento, Acompanhamento) são persistidas em disco
     (`database/`, ver src/shared/database.py). Numa sessão nova, se já
     estiverem salvas, o app abre direto no primeiro painel — sem upload.
  2. Se faltar alguma base, a tela inicial (home) pede só o que falta.
  3. Substituir uma base por uma planilha atualizada é feito exclusivamente
     pela tela "⚙️ Atualizar Bases" (acessível pela sidebar), nunca de forma
     automática — evita sobrescrever dados de produção por engano.
"""

import streamlit as st

from src.envio.page import render_envio_page
from src.recebimento.page import render_recebimento_page
from src.relatorios.page import render_relatorios_page
from src.acompanhamento.page import render_acompanhamento_page
from src.shared.home import render_home
from src.shared.manage_bases import render_gerenciar_bases
from src.shared.state import (
    VIEW_ENVIO,
    VIEW_HOME,
    VIEW_RECEBIMENTO,
    VIEW_RELATORIOS,
    VIEW_ACOMPANHAMENTO,
    VIEW_GERENCIAR_BASES,
    bases_prontas,
    init_state,
    ir_para,
)

st.set_page_config(
    page_title="Sistema de Gestão — Envio & Recebimento",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_state()

# Trava de segurança: sem as bases carregadas (disco ou sessão), força a tela inicial.
# IMPORTANTE: não existe mais redirecionamento automático para um painel a cada
# rerun — isso só acontece uma vez, dentro de init_state(), na primeira execução
# da sessão. Aqui só tratamos o caso de faltar alguma base.
if not bases_prontas() and st.session_state["view"] != VIEW_GERENCIAR_BASES:
    ir_para(VIEW_HOME)

view = st.session_state["view"]

# Barra lateral de navegação unificada quando as bases já estão prontas
if bases_prontas():
    with st.sidebar:
        # Estilização CSS customizada para que as opções do st.radio pareçam botões/pills executivos
        # e fiquem marcados corretamente (com fundo verde e texto destacado) em ambos os painéis.
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {
                gap: 6px; 
                background: #F0F5F2 !important;
                border-radius: 12px; 
                padding: 6px;
                display: flex; 
                flex-direction: column;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label {
                border-radius: 9px; 
                font-weight: 600;
                color: #4A6B5A !important; 
                padding: 10px 14px;
                background: transparent !important;
                margin: 0 !important; 
                transition: background 0.15s ease;
                width: 100%;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
                display: none !important;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
                background: linear-gradient(135deg, #0E9F6E 0%, #0C8560 100%) !important;
                box-shadow: 0 2px 8px rgba(14,159,110,0.3) !important;
            }
            [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) div {
                color: #1A2E25 !important; 
                font-weight: 800 !important;
            }
            /* Botão "Atualizar Bases" — mesmo padrão visual (gradiente
               verde neon-aqua) usado nos demais botões do app, isolado
               via marcador para não afetar outros botões da sidebar. */
            div[data-testid="element-container"]:has(.btn_atualizar_bases_marker)
              + div[data-testid="element-container"] .stButton > button {
                background: linear-gradient(135deg, #0E9F6E 0%, #0C8560 100%) !important;
                color: #1A2E25 !important;
                border: none !important;
                font-weight: 700 !important;
                box-shadow: none !important;
                transition: opacity 0.15s ease, transform 0.15s ease;
            }
            div[data-testid="element-container"]:has(.btn_atualizar_bases_marker)
              + div[data-testid="element-container"] .stButton > button:hover {
                opacity: 0.85 !important;
                transform: translateY(-1px);
                color: #1A2E25 !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### 🧭 Navegação")
        view_map = {
            "📤 Painel de Envios": VIEW_ENVIO,
            "📦 Painel de Recebimento": VIEW_RECEBIMENTO,
            "📋 Acompanhamento Oficina": VIEW_ACOMPANHAMENTO,
            "📊 Relatório Executivo": VIEW_RELATORIOS,
        }

        current_view = st.session_state["view"]

        # Importante: o switch automático só pode acontecer quando a view atual
        # já É um dos 4 painéis do mapa abaixo. Se a view atual for "home" ou
        # "gerenciar_bases" (fora do mapa), o radio sempre vai "diferir" da view
        # atual só por estar fora do mapa — e trocar de tela nesse caso é
        # exatamente o bug de navegação automática que já corrigimos antes.
        opcao = st.radio(
            "Selecione a visualização:",
            options=list(view_map.keys()),
            key="navigation_radio"
        )

        selected_view = view_map[opcao]
        if current_view in view_map.values() and selected_view != current_view:
            st.session_state["view"] = selected_view
            st.rerun()

        st.markdown("---")

        st.markdown('<span class="btn_atualizar_bases_marker" style="display:none"></span>', unsafe_allow_html=True)
        if st.button("⚙️ Atualizar Bases", use_container_width=True):
            if st.session_state["view"] != VIEW_GERENCIAR_BASES:
                st.session_state["view_antes_gerenciar"] = st.session_state["view"]
            ir_para(VIEW_GERENCIAR_BASES)
            st.rerun()

        st.markdown("---")

if view == VIEW_ENVIO:
    render_envio_page(st.session_state["envio_dataset"])
elif view == VIEW_RECEBIMENTO:
    render_recebimento_page(st.session_state["recebimento_df"])
elif view == VIEW_ACOMPANHAMENTO:
    render_acompanhamento_page(st.session_state["acompanhamento_df"])
elif view == VIEW_RELATORIOS:
    render_relatorios_page(st.session_state["envio_dataset"], st.session_state["recebimento_df"])
elif view == VIEW_GERENCIAR_BASES:
    render_gerenciar_bases()
else:
    render_home()
