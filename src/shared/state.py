"""
state.py
========
Gerenciamento de estado da sessão do sistema unificado.

Regras de negócio deste módulo:
  - As bases (Envio, Recebimento e Acompanhamento) ficam persistidas em
    SQLite (`database/app.db`, ver `src/shared/sql_store.py`). Ao abrir o
    app numa sessão nova, se as bases já estiverem salvas, elas são
    carregadas automaticamente — sem precisar de upload.
  - A navegação entre os dashboards é feita via "view" guardada na sessão.
  - Substituir uma base (planilha atualizada) só acontece de forma explícita,
    pela tela "⚙️ Atualizar Bases" — nunca automaticamente.
"""

from __future__ import annotations

import streamlit as st

VIEW_HOME = "home"
VIEW_ENVIO = "envio"
VIEW_RECEBIMENTO = "recebimento"
VIEW_RELATORIOS = "relatorios"
VIEW_ACOMPANHAMENTO = "acompanhamento"
VIEW_GERENCIAR_BASES = "gerenciar_bases"

_STATE_KEYS = (
    "view",
    "envio_dataset",
    "recebimento_df",
    "acompanhamento_df",
)


def _carregar_bases_existentes_do_disco() -> None:
    """Para cada base ainda não carregada nesta sessão, tenta carregar do
    banco (`database/app.db`, ver `src/shared/sql_store.py`).

    Importa os loaders aqui dentro (e não no topo do arquivo) para evitar
    import circular, já que os módulos de cada painel também importam
    coisas de `src.shared`.
    """
    from src.shared import sql_store

    if st.session_state.get("envio_dataset") is None and sql_store.existe_tabela("envio"):
        try:
            from src.envio.data.loader import load_from_db
            st.session_state["envio_dataset"] = load_from_db()
        except Exception:
            pass  # base no banco corrompida/inválida: segue como se não existisse

    if st.session_state.get("recebimento_df") is None and sql_store.existe_tabela("recebimento"):
        try:
            from src.recebimento.data_loader import load_from_db
            st.session_state["recebimento_df"] = load_from_db()
        except Exception:
            pass

    if st.session_state.get("acompanhamento_df") is None and sql_store.existe_tabela("acompanhamento"):
        try:
            from src.acompanhamento.loader import load_from_db
            st.session_state["acompanhamento_df"] = load_from_db()
        except Exception:
            pass


def init_state() -> None:
    """Garante que as chaves de estado existem e tenta carregar bases do disco.

    A navegação automática para o primeiro painel (sem precisar clicar em
    nada) só acontece UMA vez, exatamente na primeira execução desta sessão
    do navegador — nunca como efeito colateral de uma interação (ex.: trocar
    o arquivo selecionado num file_uploader), que era a causa do bug antigo
    de navegação "fantasma".
    """
    primeira_carga_da_sessao = "view" not in st.session_state

    st.session_state.setdefault("view", VIEW_HOME)
    st.session_state.setdefault("envio_dataset", None)
    st.session_state.setdefault("recebimento_df", None)
    st.session_state.setdefault("acompanhamento_df", None)
    st.session_state.setdefault("navigation_radio", "📤 Painel de Envios")

    _carregar_bases_existentes_do_disco()

    if primeira_carga_da_sessao and bases_prontas():
        # Já existe tudo salvo em disco: abre direto no primeiro painel,
        # sem exigir clique — só nesta primeira execução da sessão.
        ir_para(VIEW_ENVIO)


def bases_prontas() -> bool:
    """True somente quando TODAS as bases foram carregadas com sucesso."""
    return (
        st.session_state.get("envio_dataset") is not None
        and st.session_state.get("recebimento_df") is not None
        and st.session_state.get("acompanhamento_df") is not None
    )


def ir_para(view: str) -> None:
    """Troca a view atual.

    Importante: esta função NÃO toca em `st.session_state["navigation_radio"]`.
    Esse valor (ligado ao widget do rádio na sidebar) só pode ser alterado
    em app.py, antes do widget ser instanciado nesse ciclo de execução —
    se ele for alterado depois (ex.: dentro do callback de um botão chamado
    após o rádio já ter sido renderizado), o Streamlit lança
    `StreamlitAPIException`. Por isso a sincronização do rótulo do rádio
    fica centralizada em app.py.
    """
    st.session_state["view"] = view


def resetar_sessao() -> None:
    """Limpa a SESSÃO (memória) e volta para a tela inicial.

    Não apaga nada do disco (`database/`) — é só um reset da sessão do
    navegador. Se as bases continuarem salvas em disco, `init_state()` vai
    recarregá-las normalmente na próxima execução. Para realmente apagar
    uma base do disco, use a tela "⚙️ Atualizar Bases".
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()
  