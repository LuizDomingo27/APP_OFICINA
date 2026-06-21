"""
manage_bases.py
================
Tela "⚙️ Atualizar Bases" — único lugar onde uma base já salva pode ser
substituída por uma planilha nova com registros atualizados.

Diferente da tela inicial (home.py), aqui a substituição NUNCA acontece só
por selecionar um arquivo no uploader: é preciso clicar explicitamente em
"💾 Salvar e Substituir" depois que o conteúdo for validado. Isso evita que
uma base de produção seja sobrescrita por engano.

As três bases (envio, recebimento, acompanhamento) já estão migradas para
SQLite (`database/app.db`, via `src/shared/sql_store.py`). A versão
anterior de cada base é sempre guardada em backup do `.db` (ver
`sql_store._backup_arquivo_db`) antes de qualquer substituição.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from src.envio.data.loader import load_dataset_from_bytes, PlanilhaInvalidaError, load_from_db as load_envio_from_db
from src.recebimento.data_loader import _normalize_raw, load_from_db, DataLoadError
from src.acompanhamento.loader import (
    load_acompanhamento,
    AcompanhamentoLoadError,
    select_canonical_columns,
    load_from_db as load_acompanhamento_from_db,
)
from src.shared import sql_store
from src.shared.state import VIEW_HOME, ir_para


def _cartao_base_atual(nome_atual: str | None, horario_atual: str | None) -> None:
    """Bloco visual reaproveitado pelas três seções — mostra qual é a
    base carregada no momento (vinda do `database/app.db`)."""
    if nome_atual:
        st.markdown(
            f"<div style='background:#F0FDF8;border:1.5px solid #D0F0E5;"
            f"border-radius:10px;padding:10px 12px;font-size:12.5px;color:#4A6B5A;margin-bottom:10px;'>"
            f"📄 Base atual no banco: <b>{nome_atual}</b><br>"
            f"<span style='color:#8FAFA0;'>Carregada em {horario_atual}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Nenhuma base salva no banco ainda para esta planilha.")


def _secao_base_envio() -> None:
    """Seção de Envios — migrada para SQLite (`database/app.db`)."""
    titulo = "Base de Envios"
    st.markdown(f"#### {titulo}")
    st.caption("Colunas obrigatórias: ENVIO, QTD, MINUTOS, MP, PDV, OFICINA")
    st.caption("🧪 Esta base já está migrada para SQLite (`database/app.db`).")

    _cartao_base_atual(*sql_store.info_tabela("envio"))

    arquivo = st.file_uploader(
        f"Selecionar nova planilha — {titulo}",
        type=["xlsx"],
        key="uploader_manage_envio_sqlite",
    )

    if arquivo is None:
        st.divider()
        return

    try:
        dataset = load_dataset_from_bytes(arquivo.getvalue())
    except PlanilhaInvalidaError as exc:
        st.error(f"⚠️ Planilha inválida: {exc}")
        st.divider()
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        st.divider()
        return

    st.success(f"✅ Planilha válida — {len(dataset.df):,} linhas. Nada foi alterado ainda.".replace(",", "."))

    if st.button(f"💾 Salvar e Substituir — {titulo}", key="btn_salvar_envio_sqlite", type="primary"):
        sql_store.substituir_tabela("envio", dataset.df, indices=["ENVIO", "MP", "PDV", "OFICINA"])
        sql_store.registrar_metadata("envio", arquivo.name)
        load_envio_from_db.clear()  # invalida o cache: próxima leitura já reflete os dados novos
        st.session_state["envio_dataset"] = load_envio_from_db()
        st.success(
            "Base de Envios substituída com sucesso (SQLite)! "
            "A versão anterior do banco foi guardada em backup."
        )
        st.rerun()

    st.divider()


def _secao_base_recebimento() -> None:
    """Seção de Recebimento — já migrada para SQLite (`database/app.db`).

    Diferente de `_secao_base` (versão genérica, hoje sem uso depois da
    migração completa), aqui a substituição grava a tabela inteira via
    `sql_store.substituir_tabela` e invalida o cache de `load_from_db`
    explicitamente — não há mais hash de bytes de arquivo envolvido.
    """
    titulo = "Base de Recebimento"
    st.markdown(f"#### {titulo}")
    st.caption("Colunas obrigatórias: DIA, MP, OFICINA, REAL CORTADO, MINUTOS")
    st.caption("🧪 Esta base já está migrada para SQLite (`database/app.db`).")

    _cartao_base_atual(*sql_store.info_tabela("recebimento"))

    arquivo = st.file_uploader(
        f"Selecionar nova planilha — {titulo}",
        type=["xlsx"],
        key="uploader_manage_recebimento_sqlite",
    )

    if arquivo is None:
        st.divider()
        return

    try:
        df_bruto = pd.read_excel(BytesIO(arquivo.getvalue()))
        df_limpo = _normalize_raw(df_bruto)
    except DataLoadError as exc:
        st.error(f"⚠️ Planilha inválida: {exc}")
        st.divider()
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        st.divider()
        return

    st.success(f"✅ Planilha válida — {len(df_limpo):,} linhas. Nada foi alterado ainda.".replace(",", "."))

    if st.button(f"💾 Salvar e Substituir — {titulo}", key="btn_salvar_recebimento_sqlite", type="primary"):
        sql_store.substituir_tabela("recebimento", df_limpo, indices=["DIA", "MP", "OFICINA"])
        sql_store.registrar_metadata("recebimento", arquivo.name)
        load_from_db.clear()  # invalida o cache: próxima leitura já reflete os dados novos
        st.session_state["recebimento_df"] = load_from_db()
        st.success(
            "Base de Recebimento substituída com sucesso (SQLite)! "
            "A versão anterior do banco foi guardada em backup."
        )
        st.rerun()

    st.divider()


def _secao_base_acompanhamento() -> None:
    """Seção de Acompanhamento — migrada para SQLite (`database/app.db`).

    Só as colunas de `CANONICAL_COLUMNS` (ver `acompanhamento/loader.py`)
    vão para o banco — a planilha original traz ~30 colunas extras que o
    app nunca usa, e que só geram ruído (e dtype estranho no round-trip)
    se forem persistidas junto.
    """
    titulo = "Base de Acompanhamento"
    st.markdown(f"#### {titulo}")
    st.caption("Colunas obrigatórias: SITUACAO, DEADLINE, ENVIO, MP, OFICINA, DEPARTAMENTO, PDV, PECAS, MINUTOS")
    st.caption("🧪 Esta base já está migrada para SQLite (`database/app.db`).")

    _cartao_base_atual(*sql_store.info_tabela("acompanhamento"))

    arquivo = st.file_uploader(
        f"Selecionar nova planilha — {titulo}",
        type=["xlsx"],
        key="uploader_manage_acompanhamento_sqlite",
    )

    if arquivo is None:
        st.divider()
        return

    try:
        df_completo = load_acompanhamento(arquivo.getvalue())
    except AcompanhamentoLoadError as exc:
        st.error(f"⚠️ Planilha inválida: {exc}")
        st.divider()
        return
    except Exception as exc:
        st.error(f"Não foi possível abrir a planilha: {exc}")
        st.divider()
        return

    st.success(f"✅ Planilha válida — {len(df_completo):,} linhas. Nada foi alterado ainda.".replace(",", "."))

    if st.button(f"💾 Salvar e Substituir — {titulo}", key="btn_salvar_acompanhamento_sqlite", type="primary"):
        df_para_salvar = select_canonical_columns(df_completo)
        sql_store.substituir_tabela(
            "acompanhamento", df_para_salvar, indices=["ENVIO", "MP", "OFICINA", "DEPARTAMENTO"]
        )
        sql_store.registrar_metadata("acompanhamento", arquivo.name)
        load_acompanhamento_from_db.clear()  # invalida o cache: próxima leitura já reflete os dados novos
        st.session_state["acompanhamento_df"] = load_acompanhamento_from_db()
        st.success(
            "Base de Acompanhamento substituída com sucesso (SQLite)! "
            "A versão anterior do banco foi guardada em backup."
        )
        st.rerun()

    st.divider()


def render_gerenciar_bases() -> None:
    st.title("⚙️ Atualizar Bases")
    st.write(
        "Envie uma planilha nova para substituir a base atual por registros "
        "atualizados. A substituição só acontece quando você clicar em "
        "**Salvar e Substituir** — selecionar o arquivo apenas valida o "
        "conteúdo, sem alterar nada ainda."
    )
    st.divider()

    _secao_base_envio()
    _secao_base_recebimento()
    _secao_base_acompanhamento()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ Voltar"):
        destino = st.session_state.get("view_antes_gerenciar", VIEW_HOME)
        ir_para(destino)
        st.rerun()
