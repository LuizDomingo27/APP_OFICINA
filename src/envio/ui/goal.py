"""
ui/goal.py
==========
Componente de Meta / Objetivo do Painel de Envio.

Visual replicado do Painel de Recebimento (src/recebimento/ui/goal.py),
adaptado à paleta NEON/ACCENT do Envio e com suporte a meta por
**Peças** ou **Minutos** (seletor que antes ficava na sidebar).

Responsabilidades:
  - Renderizar o seletor de tipo de meta (Peças/Minutos) e o campo de input
  - Exibir cards de progresso (realizado, falta, percentual)
  - Exibir badge de conquista quando a meta é batida
"""

from __future__ import annotations

import streamlit as st

from src.shared.echarts_utils import safe_st_echarts
from src.envio.config.theme import ACCENT, NEON, INK, MUTED
from src.envio.config.settings import DEFAULT_META_PECAS, DEFAULT_META_MINUTOS
from src.envio.data.filters import MetaState
from src.envio.data.metrics import GoalProgress
from src.envio.charts.builders import build_gauge_meta
from src.envio.utils.formatters import fmt_number


def render_goal_section() -> MetaState:
    """
    Renderiza o seletor de tipo de meta + campo de input e retorna o estado.

    Retorna
    -------
    MetaState : tipo ("Peças" ou "Minutos") e valor informado pelo usuário.
    """
    st.markdown(
        f"""
        <div style="
            font-size:22px; font-weight:900;
            color:{INK}; letter-spacing:-0.5px;
            margin-bottom:4px;
        ">🎯 Controle de Meta</div>
        <div style="width:48px;height:3px;background:{ACCENT};border-radius:2px;margin-bottom:14px;"></div>
        """,
        unsafe_allow_html=True,
    )

    col_tipo, col_input, col_info = st.columns([1, 1, 2])

    with col_tipo:
        tipo = st.radio(
            "Tipo de meta",
            ["Peças", "Minutos"],
            horizontal=True,
            key="envio_meta_tipo",
        )

    valor_key = "envio_meta_valor_pecas" if tipo == "Peças" else "envio_meta_valor_minutos"
    default_valor = DEFAULT_META_PECAS if tipo == "Peças" else DEFAULT_META_MINUTOS

    with col_input:
        meta_valor = st.number_input(
            f"Meta de {tipo.lower()}",
            min_value=0,
            value=int(st.session_state.get(valor_key, default_valor)),
            step=1000,
            help=f"Informe o total de {tipo.lower()} a ser enviado no período selecionado.",
            key=valor_key,
        )

    with col_info:
        st.markdown(
            f"""
            <div style="
                background:#F2FFF9;
                border:1.5px solid {NEON}55;
                border-radius:12px;
                padding:14px 18px;
                margin-top:26px;
                font-size:13px;
                color:{MUTED};
            ">
                💡 Escolha se deseja acompanhar a meta por <strong>peças</strong> ou
                <strong>minutos</strong> e informe o valor desejado para o período.
                O sistema calculará automaticamente o percentual atingido
                e quanto ainda falta para bater a meta.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return MetaState(tipo=tipo, valor=float(meta_valor))


def render_goal_progress(gp: GoalProgress, unidade: str) -> None:
    """
    Renderiza os cards de progresso e o gauge de meta.

    Parâmetros
    ----------
    gp      : GoalProgress (de envio.data.metrics.calc_goal_progress)
    unidade : "pçs" ou "min" — sufixo exibido nos cards
    """
    if gp.meta == 0:
        st.info("ℹ️ Informe a meta acima para visualizar o progresso.")
        return

    # — Badge de conquista
    if gp.bateu_meta:
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, {NEON} 0%, {ACCENT} 100%);
                border-radius: 14px;
                padding: 14px 22px;
                text-align: center;
                margin-bottom: 16px;
                box-shadow: 0 4px 20px rgba(57,255,156,0.4);
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
            border:1.5px solid #E6ECEF;
            border-left:5px solid {color};
            border-radius:14px;
            padding:18px;
            text-align:center;
            box-shadow:0 2px 10px rgba(14,159,110,0.08);
        ">
            <div style="font-size:26px;">{icon}</div>
            <div style="font-size:11px;color:{MUTED};font-weight:700;
                        text-transform:uppercase;letter-spacing:0.5px;margin:4px 0;">{label}</div>
            <div style="font-size:26px;font-weight:900;color:{color};">{value}</div>
        </div>
        """

    with c1:
        st.markdown(
            _prog_card("🎯", "Meta", f"{fmt_number(gp.meta)} {unidade}", NEON),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            _prog_card("✅", "Realizado", f"{fmt_number(gp.realizado)} {unidade}", NEON),
            unsafe_allow_html=True,
        )
    with c3:
        color_faltam = "#FF6B6B" if not gp.bateu_meta else NEON
        label_faltam = "Faltam" if not gp.bateu_meta else "Excedente"
        valor_faltam = (
            f"{fmt_number(gp.faltam)} {unidade}"
            if not gp.bateu_meta
            else f"+{fmt_number(gp.realizado - gp.meta)} {unidade}"
        )
        st.markdown(
            _prog_card("📊", label_faltam, valor_faltam, color_faltam),
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
        st.markdown(
            f"""
            <div style="padding:20px 0;">
                <div style="font-size:13px;color:{MUTED};
                            font-weight:700;text-transform:uppercase;
                            letter-spacing:0.5px;margin-bottom:8px;">
                    Resumo do Progresso
                </div>
                <div style="font-size:42px;font-weight:900;
                            color:{ACCENT if gp.bateu_meta else '#FFB347'};
                            line-height:1;">
                    {gp.percentual:.1f}%
                </div>
                <div style="font-size:14px;color:{MUTED};margin-top:8px;">
                    da meta concluído
                </div>
                <div style="margin-top:18px;
                            background:#F2FFF9;
                            border-radius:10px;
                            padding:12px 16px;
                            font-size:13px;color:{MUTED};">
                    {"🏆 Meta superada!" if gp.bateu_meta else f"📉 Ainda faltam <strong style='color:#FF6B6B;'>{fmt_number(gp.faltam)} {unidade}</strong>"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
