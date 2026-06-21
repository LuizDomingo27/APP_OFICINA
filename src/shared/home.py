"""
home.py
=======
Tela inicial do sistema unificado.

Regra de negócio (RF):
  - O acesso aos painéis é liberado depois que as 3 planilhas (Envio,
    Recebimento e Acompanhamento) estiverem disponíveis — seja por upload
    nesta tela, seja porque já estavam salvas em disco (database/) de uma
    sessão anterior.
  - Uma base só é exibida com uploader aqui se AINDA NÃO existir (nem em
    disco, nem na sessão). Bases já carregadas mostram um cartão de status,
    em vez do uploader — substituir uma base existente é feito exclusivamente
    pela tela "⚙️ Atualizar Bases", nunca por aqui.
  - A navegação para os dashboards é feita por cliques explícitos nos
    cards/botões desta tela — nunca automaticamente.
"""

import streamlit as st

from src.envio.data.loader import load_dataset_from_bytes, PlanilhaInvalidaError, load_from_db as load_envio_from_db
from src.recebimento.data_loader import _normalize_raw, load_from_db, DataLoadError
from src.acompanhamento.loader import (
    load_acompanhamento,
    AcompanhamentoLoadError,
    select_canonical_columns,
    load_from_db as load_acompanhamento_from_db,
)
from src.shared import database as db
from src.shared import sql_store
from src.shared.state import (
    VIEW_ENVIO,
    VIEW_RECEBIMENTO,
    VIEW_ACOMPANHAMENTO,
    bases_prontas,
    ir_para,
)


def _cartao_base_carregada(base_key: str) -> None:
    nome, horario = db.info_base(base_key)
    if nome:
        st.markdown(
            f"<div style='background:#F0FDF8;border:1.5px solid #D0F0E5;"
            f"border-radius:10px;padding:14px 14px;font-size:12.5px;color:#4A6B5A;'>"
            f"✅ <b>Já carregada</b><br>"
            f"<span style='color:#0F1B2D;font-weight:600;'>{nome}</span><br>"
            f"<span style='color:#8FAFA0;'>Salva em {horario}</span><br><br>"
            f"<span style='color:#8FAFA0;'>Para atualizar, use ⚙️ Atualizar Bases.</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:#F0FDF8;border:1.5px solid #D0F0E5;"
            "border-radius:10px;padding:14px 14px;font-size:12.5px;color:#4A6B5A;'>"
            "✅ <b>Já carregada nesta sessão</b>"
            "</div>",
            unsafe_allow_html=True,
        )


def _upload_envio() -> None:
    st.markdown("#### 🧵 Base de Envios")

    if st.session_state.get("envio_dataset") is not None:
        _cartao_base_carregada("envio")
        return

    st.caption("Colunas obrigatórias: ENVIO, QTD, MINUTOS, MP, PDV, OFICINA")
    arquivo = st.file_uploader(
        "Planilha de Envios (.xlsx)", type=["xlsx"], key="uploader_envio"
    )
    if arquivo is None:
        st.info("Aguardando upload.")
        return

    try:
        dataset = load_dataset_from_bytes(arquivo.getvalue())
    except PlanilhaInvalidaError as exc:
        st.error(f"Planilha inválida: {exc}")
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        return

    st.session_state["envio_dataset"] = dataset
    if not sql_store.existe_tabela("envio"):
        sql_store.substituir_tabela("envio", dataset.df, indices=["ENVIO", "MP", "PDV", "OFICINA"])
        sql_store.registrar_metadata("envio", arquivo.name)
        load_envio_from_db.clear()
    st.success(f"✅ {len(dataset.df):,} linhas carregadas e salvas.".replace(",", "."))


def _upload_recebimento() -> None:
    st.markdown("#### 📦 Base de Recebimento")

    if st.session_state.get("recebimento_df") is not None:
        _cartao_base_carregada("recebimento")
        return

    st.caption("Colunas obrigatórias: DIA, MP, OFICINA, REAL CORTADO, MINUTOS")
    arquivo = st.file_uploader(
        "Planilha de Recebimento (.xlsx)", type=["xlsx"], key="uploader_recebimento"
    )
    if arquivo is None:
        st.info("Aguardando upload.")
        return

    try:
        import pandas as pd
        from io import BytesIO
        df = _normalize_raw(pd.read_excel(BytesIO(arquivo.getvalue())))
    except DataLoadError as exc:
        st.error(f"⚠️ {exc}")
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        return

    st.session_state["recebimento_df"] = df
    if not sql_store.existe_tabela("recebimento"):
        sql_store.substituir_tabela("recebimento", df, indices=["DIA", "MP", "OFICINA"])
        sql_store.registrar_metadata("recebimento", arquivo.name)
        load_from_db.clear()
    st.success(f"✅ {len(df):,} linhas carregadas e salvas.".replace(",", "."))


def _upload_acompanhamento() -> None:
    st.markdown("#### 📋 Base de Acompanhamento")

    if st.session_state.get("acompanhamento_df") is not None:
        _cartao_base_carregada("acompanhamento")
        return

    st.caption("Colunas: SITUACAO, DEADLINE, ENVIO, MP, OFICINA, DEPARTAMENTO, PDV, PECAS, MINUTOS")
    arquivo = st.file_uploader(
        "Planilha de Acompanhamento (.xlsx)", type=["xlsx"], key="uploader_acompanhamento"
    )
    if arquivo is None:
        st.info("Aguardando upload.")
        return

    try:
        df = load_acompanhamento(arquivo.getvalue())
    except AcompanhamentoLoadError as exc:
        st.error(f"⚠️ {exc}")
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        return

    st.session_state["acompanhamento_df"] = df
    if not sql_store.existe_tabela("acompanhamento"):
        df_para_salvar = select_canonical_columns(df)
        sql_store.substituir_tabela(
            "acompanhamento", df_para_salvar, indices=["ENVIO", "MP", "OFICINA", "DEPARTAMENTO"]
        )
        sql_store.registrar_metadata("acompanhamento", arquivo.name)
        load_acompanhamento_from_db.clear()
    st.success(f"✅ {len(df):,} linhas carregadas e salvas (Costura).".replace(",", "."))


def render_home() -> None:
    st.title("📊 Sistema de Gestão — Envio & Recebimento")
    st.write(
        "Envie as planilhas que ainda estiverem faltando. Uma vez enviada, "
        "cada base fica salva e, nas próximas vezes que o sistema for aberto, "
        "ela já estará disponível automaticamente — sem precisar reenviar."
    )
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        _upload_envio()
    with col2:
        _upload_recebimento()
    with col3:
        _upload_acompanhamento()

    st.divider()

    if bases_prontas():
        st.success("Tudo certo! As três bases estão prontas. Escolha um painel para abrir:")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📤  Abrir Painel de Envios", use_container_width=True, type="primary"):
                ir_para(VIEW_ENVIO)
                st.rerun()
        with c2:
            if st.button("📦  Abrir Painel de Recebimento", use_container_width=True, type="primary"):
                ir_para(VIEW_RECEBIMENTO)
                st.rerun()
        with c3:
            if st.button("📋  Abrir Acompanhamento Oficina", use_container_width=True, type="primary"):
                ir_para(VIEW_ACOMPANHAMENTO)
                st.rerun()
    else:
        faltando = []
        if st.session_state.get("envio_dataset") is None:
            faltando.append("Envios")
        if st.session_state.get("recebimento_df") is None:
            faltando.append("Recebimento")
        if st.session_state.get("acompanhamento_df") is None:
            faltando.append("Acompanhamento")
        st.warning(f"Aguardando o upload de: **{', '.join(faltando)}**.")
