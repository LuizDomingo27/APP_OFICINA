"""
ui/goal.py
==========
Componente de Meta / Objetivo.

Responsabilidades:
  - Renderizar o campo de input da meta
  - Exibir cards de progresso (realizado, falta, percentual)
  - Exibir badge de conquista quando meta é batida
"""

from __future__ import annotations

import streamlit as st
from src.shared.echarts_utils import safe_st_echarts

from ..config import COLOR_PRIMARY, COLOR_TEXT, COLOR_TEXT_MUTED
from ..metrics import GoalProgress
from ..charts import build_gauge_meta


def render_goal_section(total_pecas: int, total_minutos: float) -> tuple[str, float]:
    """
    Renderiza o seletor de tipo de meta + campo de input e retorna a seleção.

    Parâmetros
    ----------
    total_pecas   : total de peças já recebidas (para referência)
    total_minutos : total de minutos já recebidos (para referência)

    Retorna
    -------
    tuple[str, float] : (tipo escolhido — "Peças" ou "Minutos", valor da meta inserido pelo usuário)
    """
    st.markdown(
        f"""
        <div style="
            font-size:22px; font-weight:900;
            color:#1A2E25; letter-spacing:-0.5px;
            margin-bottom:4px;
        "> Controle de Meta</div>
        <div style="width:48px;height:3px;background:{COLOR_PRIMARY};border-radius:2px;margin-bottom:14px;"></div>
        """,
        unsafe_allow_html=True,
    )

    col_tipo, col_input, col_info = st.columns([1, 1, 2])

    with col_tipo:
        tipo = st.radio(
            "Tipo de meta",
            ["Peças", "Minutos"],
            horizontal=True,
            key="recebimento_meta_tipo",
        )

    valor_key = "recebimento_meta_valor_pecas" if tipo == "Peças" else "recebimento_meta_valor_minutos"

    with col_input:
        meta = st.number_input(
            f"Defina a meta de {tipo.lower()}",
            min_value=0,
            value=int(st.session_state.get(valor_key, 0)),
            step=1000,
            help=f"Informe o total de {tipo.lower()} a ser recebido no período selecionado.",
            key=valor_key,
        )

    with col_info:
        st.markdown(
            f"""
            <div style="
                background:#F0FDF8;
                border:1.5px solid #D0F0E5;
                border-radius:12px;
                padding:14px 18px;
                margin-top:26px;
                font-size:13px;
                color:{COLOR_TEXT_MUTED};
            ">
                💡 Escolha se deseja acompanhar a meta por <strong>peças</strong> ou
                <strong>minutos</strong> e informe o valor desejado para o período.
                O sistema calculará automaticamente o percentual atingido
                e quanto ainda falta para bater a meta.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return tipo, float(meta)


def render_goal_progress(gp: GoalProgress, unidade: str = "pçs") -> None:
    """
    Renderiza os cards de progresso e o gauge de meta.

    Parâmetros
    ----------
    gp      : GoalProgress (de metrics.calc_goal_progress)
    unidade : sufixo exibido nos cards — "pçs" (peças) ou "min" (minutos)
    """
    if gp.meta == 0:
        st.info("ℹ️ Informe a meta acima para visualizar o progresso.")
        return

    # — Badge de conquista
    if gp.bateu_meta:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #0E9F6E 0%, #0C8560 100%);
                border-radius: 14px;
                padding: 14px 22px;
                text-align: center;
                margin-bottom: 16px;
                box-shadow: 0 4px 20px rgba(14,159,110,0.4);
            ">
                <span style="font-size:28px;">🏆</span>
                <span style="
                    font-size:18px; font-weight:900;
                    color:#fff; margin-left:10px;
                ">META ATINGIDA! Parabéns!</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # — Cards de progresso
    c1, c2, c3 = st.columns(3)

    def _prog_card(icon, label, value, color):
        return f"""
        <div style="
            background:#FFFFFF;
            border:1.5px solid #D0F0E5;
            border-left:5px solid {color};
            border-radius:14px;
            padding:18px;
            text-align:center;
            box-shadow:0 2px 10px rgba(14,159,110,0.08);
        ">
            <div style="font-size:26px;">{icon}</div>
            <div style="font-size:11px;color:{COLOR_TEXT_MUTED};font-weight:700;
                        text-transform:uppercase;letter-spacing:0.5px;margin:4px 0;">{label}</div>
            <div style="font-size:26px;font-weight:900;color:{color};">{value}</div>
        </div>
        """

    with c1:
        st.markdown(
            _prog_card("📦", "Meta", f"{gp.meta:,.0f}".replace(",", ".") + f" {unidade}", "#0E9F6E"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _prog_card("✅", "Realizado", f"{gp.realizado:,.0f}".replace(",", ".") + f" {unidade}", "#0E9F6E"),
            unsafe_allow_html=True,
        )
    with c3:
        color_faltam = "#FF6B6B" if not gp.bateu_meta else "#0E9F6E"
        label_faltam = "Faltam" if not gp.bateu_meta else "Excedente"
        valor_faltam = (
            f"{gp.faltam:,.0f}".replace(",", ".") + f" {unidade}"
            if not gp.bateu_meta
            else f"+{gp.realizado - gp.meta:,.0f}".replace(",", ".") + f" {unidade}"
        )
        st.markdown(
            _prog_card("🎯", label_faltam, valor_faltam, color_faltam),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # — Gauge
    col_gauge, col_txt = st.columns([1, 1])
    with col_gauge:
        safe_st_echarts(
            options=build_gauge_meta(gp.percentual, gp.bateu_meta),
            height="260px",
        )
    with col_txt:
        dias_restantes_text = ""
        st.markdown(
            f"""
            <div style="padding:20px 0;">
                <div style="font-size:13px;color:{COLOR_TEXT_MUTED};
                            font-weight:700;text-transform:uppercase;
                            letter-spacing:0.5px;margin-bottom:8px;">
                    Resumo do Progresso
                </div>
                <div style="font-size:42px;font-weight:900;
                            color:{'#0E9F6E' if gp.bateu_meta else '#FFB347'};
                            line-height:1;">
                    {gp.percentual:.1f}%
                </div>
                <div style="font-size:14px;color:{COLOR_TEXT_MUTED};margin-top:8px;">
                    da meta concluído
                </div>
                <div style="margin-top:18px;
                            background:#F0FDF8;
                            border-radius:10px;
                            padding:12px 16px;
                            font-size:13px;color:{COLOR_TEXT_MUTED};">
                    {"🏆 Meta superada!" if gp.bateu_meta else f"📉 Ainda faltam <strong style='color:#FF6B6B;'>{gp.faltam:,.0f} {unidade}</strong>".replace(",", ".")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
