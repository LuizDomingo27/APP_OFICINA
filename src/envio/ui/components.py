"""Componentes reutilizáveis da interface."""

import html
from datetime import date

import pandas as pd
import streamlit as st

from src.envio.config.settings import HIDDEN_COLUMNS, STATUS_OK
from src.envio.config.theme import INK, MUTED
from src.envio.data.metrics import DashboardMetrics
from src.envio.utils.formatters import fmt_number


def render_hero(title: str, date_start: date, date_end: date, total_envios: int) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>Visão executiva — período de <b>{date_start.strftime('%d/%m/%Y')}</b>
            até <b>{date_end.strftime('%d/%m/%Y')}</b> · {total_envios:,} envios</p>
        </div>
        """.replace(",", "."),
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: DashboardMetrics) -> None:
    cards = [
        ("Total de Peças", fmt_number(metrics.total_pecas), f"{fmt_number(metrics.total_minutos)} minutos"),
        (
            "Envio do Dia",
            fmt_number(metrics.hoje_pecas),
            f"{fmt_number(metrics.hoje_minutos)} min · {metrics.referencia_dia.strftime('%d/%m')}",
        ),
        (
            "Semana Atual",
            fmt_number(metrics.semana_pecas),
            f"{fmt_number(metrics.semana_minutos)} min · desde {metrics.semana_inicio.strftime('%d/%m')}",
        ),
        (
            "Grupos Abastecidos",
            fmt_number(metrics.oficinas_ativas),
            f"{metrics.mp_count} MPs · {metrics.pdv_count} PDVs",
        ),
    ]
    cols = st.columns(4)
    for col, (label, value, sub) in zip(cols, cards):
        with col:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="label">{label}</div>
                    <div class="value">{value}</div>
                    <div class="sub"><span class="accent">●</span> {sub}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def render_chart(option: dict) -> None:
    """Exibe gráfico ECharts em largura total."""
    from src.shared.echarts_utils import safe_st_echarts
    from src.envio.charts.theme import ECHART_HEIGHT
    safe_st_echarts(options=option, height=ECHART_HEIGHT, renderer="canvas")


def render_custom_table(df: pd.DataFrame, max_rows: int) -> None:
    visible = [c for c in df.columns if c not in HIDDEN_COLUMNS]
    display = df[visible].head(max_rows)
    cols = display.columns.tolist()
    
    thead_cells = []
    for c in cols:
        if c in ["QTD", "MINUTOS"]:
            thead_cells.append(f"<th class='num'>{html.escape(str(c))}</th>")
        elif c in ["ENVIO"]:
            thead_cells.append(f"<th style='text-align: center;'>{html.escape(str(c))}</th>")
        else:
            thead_cells.append(f"<th>{html.escape(str(c))}</th>")
    thead = "".join(thead_cells)

    rows_html = []
    col_index = {col: idx for idx, col in enumerate(cols)}
    envio_i = col_index.get("ENVIO")
    qtd_i = col_index.get("QTD")
    min_i = col_index.get("MINUTOS")
    sit_i = col_index.get("SITUAÇÃO")

    for i, row in enumerate(display.itertuples(index=False, name=None)):
        cells = []
        for col_idx, col in enumerate(cols):
            val = row[col_idx]
            if col_idx == envio_i and pd.notna(val):
                cell = f"<td class='date'>{pd.Timestamp(val).strftime('%d/%m/%Y')}</td>"
            elif col_idx == qtd_i or col_idx == min_i:
                cell = f"<td class='num'>{fmt_number(float(val))}</td>"
            elif col_idx == sit_i:
                safe_val = html.escape(str(val))
                badge_cls = "badge badge-warn" if str(val).upper() not in STATUS_OK else "badge"
                cell = f"<td><span class='{badge_cls}'>{safe_val}</span></td>"
            else:
                cell = f"<td>{html.escape(str(val)) if pd.notna(val) else ''}</td>"
            cells.append(cell)
        row_cls = "even" if i % 2 == 0 else "odd"
        rows_html.append(f"<tr class='{row_cls}'>{''.join(cells)}</tr>")

    st.markdown(
        f"""
        <div class="custom-table-wrapper">
            <table class="custom-table">
                <thead><tr>{thead}</tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
