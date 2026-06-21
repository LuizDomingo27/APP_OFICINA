"""Layout principal do dashboard."""

import streamlit as st

from src.envio.utils.excel_export import build_executive_excel_cached

from src.envio.charts.builders import (
    build_daily_area_chart,
    build_frete_column_chart,
    build_mp_donut_chart,
    build_oficinas_column_chart,
)
from src.envio.config.settings import DEFAULT_TABLE_ROWS, TABLE_ROW_OPTIONS
from src.envio.data.filters import apply_filters, FilterState
from src.envio.data.metrics import (
    aggregate_daily,
    aggregate_frete,
    aggregate_mp,
    aggregate_oficinas,
    calc_goal_progress,
    compute_metrics,
)
from src.envio.ui.components import (
    render_chart,
    render_custom_table,
    render_hero,
    render_metric_cards,
)
from src.envio.ui.goal import render_goal_section, render_goal_progress


def render_dashboard(df, filters: FilterState) -> None:
    st.markdown("-")
    fdf = apply_filters(df, filters)
    metrics = compute_metrics(fdf, filters.date_end)

    render_metric_cards(metrics)
    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.divider()

    meta = render_goal_section()
    if meta.valor > 0:
        atual = metrics.total_pecas if meta.tipo == "Peças" else metrics.total_minutos
        gp = calc_goal_progress(atual, meta.valor)
        unidade = "pçs" if meta.tipo == "Peças" else "min"
        render_goal_progress(gp, unidade)
    st.markdown("&nbsp;", unsafe_allow_html=True)

    st.divider()
    st.markdown("### Análises Visuais")

    if fdf.empty:
        st.info("Nenhum dado encontrado para os filtros selecionados.")
        return

    render_chart(build_oficinas_column_chart(aggregate_oficinas(fdf)))

    frete_df = aggregate_frete(fdf)
    if not frete_df.empty:
        render_chart(build_frete_column_chart(frete_df))

    mp_df = aggregate_mp(fdf)
    if not mp_df.empty:
        render_chart(build_mp_donut_chart(mp_df))

    render_chart(build_daily_area_chart(aggregate_daily(fdf)))

    st.markdown("### Registro de Envios")
    table_df = fdf.sort_values("ENVIO", ascending=False)
    max_rows = st.selectbox(
        "Linhas exibidas",
        options=TABLE_ROW_OPTIONS,
        index=TABLE_ROW_OPTIONS.index(DEFAULT_TABLE_ROWS),
        label_visibility="collapsed",
    )
    shown = min(len(table_df), max_rows)
    st.markdown(
        f"""
        <div class="section-card">
            <p class="section-title">Dados filtrados</p>
            <p class="section-caption">
                Exibindo <b>{shown}</b> de <b>{len(table_df)}</b> registros
                · ordenados por data mais recente
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_custom_table(table_df, max_rows=max_rows)

    st.divider()
    export_key = (
        f"{filters.date_start}|{filters.date_end}|"
        f"{filters.mp}|{filters.pdv}|{filters.oficina}|{len(table_df)}"
    )
    export_col, _ = st.columns([1, 4])
    with export_col:
        st.caption("Gere o arquivo e, em seguida, salve-o no seu computador.")

        if st.session_state.get("excel_export_key") != export_key:
            st.session_state.pop("excel_bytes", None)

        if st.button("⬇️ Preparar Excel filtrado"):
            st.session_state["excel_export_key"] = export_key
            st.session_state["excel_bytes"] = build_executive_excel_cached(
                export_key,
                table_df,
                date_start=filters.date_start,
                date_end=filters.date_end,
            )

        if (
            st.session_state.get("excel_export_key") == export_key
            and st.session_state.get("excel_bytes")
        ):
            st.download_button(
                "Salvar arquivo .xlsx",
                st.session_state["excel_bytes"],
                file_name="envios_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
