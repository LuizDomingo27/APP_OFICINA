"""
ui/cards.py
===========
Componentes de UI para os KPI cards do painel.

Responsabilidades:
  - Renderizar os cards de métricas com CSS customizado
  - Receber apenas valores já calculados (sem acesso a dados brutos)

Depende de: config.py, streamlit
"""

import streamlit as st
from ..config import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_TEXT, COLOR_TEXT_MUTED


def _metric_card(
    icon: str,
    label: str,
    value: str,
    subtitle: str = "",
    accent: str = COLOR_PRIMARY,
) -> str:
    """
    Retorna o HTML de um card de métrica estilizado.
    """
    return f"""
    <div style="
        background: #FFFFFF;
        border: 1.5px solid #D0F0E5;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 2px 12px rgba(14,159,110,0.10);
        border-left: 5px solid {accent};
        transition: box-shadow 0.2s;
        height: 100%;
    ">
        <div style="font-size:28px; margin-bottom:6px;">{icon}</div>
        <div style="
            font-size: 13px;
            color: {COLOR_TEXT_MUTED};
            font-weight: 600;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 4px;
        ">{label}</div>
        <div style="
            font-size: 32px;
            font-weight: 900;
            color: {COLOR_TEXT};
            line-height: 1.1;
            margin-bottom: 4px;
        ">{value}</div>
        <div style="
            font-size: 12px;
            color: {COLOR_TEXT_MUTED};
        ">{subtitle}</div>
    </div>
    """


def render_kpi_cards(kpi) -> None:
    """
    Renderiza a fila de cards KPI na tela principal.

    Parâmetros
    ----------
    kpi : KPISummary  (de metrics.calc_kpis)
    """
    cols = st.columns(4)

    cards = [
        {
            "icon": "",
            "label": "Total de Peças",
            "value": f"{kpi.total_pecas:,}".replace(",", "."),
            "subtitle": f"{kpi.dias_trabalhados} dias registrados",
            "accent": "#0E9F6E",
        },
        {
            "icon": "",
            "label": "Total de Minutos",
            "value": f"{kpi.total_minutos:,.0f}".replace(",", "."),
            "subtitle": f"≈ {kpi.total_minutos/60:,.0f}h trabalhadas".replace(",", "."),
            "accent": "#0E9F6E",
        },
        {
            "icon": "",
            "label": "Média Diária",
            "value": f"{kpi.media_diaria_pecas:,.0f}".replace(",", "."),
            "subtitle": "peças / dia",
            "accent": "#0E9F6E",
        },
        {
            "icon": "",
            "label": "Média Semanal",
            "value": f"{kpi.media_semanal_pecas:,.0f}".replace(",", "."),
            "subtitle": f"{kpi.semanas_trabalhadas} semanas no período",
            "accent": "#0E9F6E",
        },
    ]

    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                _metric_card(
                    icon=card["icon"],
                    label=card["label"],
                    value=card["value"],
                    subtitle=card["subtitle"],
                    accent=card["accent"],
                ),
                unsafe_allow_html=True,
            )
