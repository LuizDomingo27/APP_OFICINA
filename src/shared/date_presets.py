"""Botões de atalho para seleção rápida de período de datas.

Usado em todas as páginas com filtro de data (Envio, Acompanhamento,
Recebimento) para manter o mesmo padrão visual e o mesmo comportamento
dos atalhos de período rápido: Hoje / 7 dias / Este mês / Tudo.

Técnica de CSS (Streamlit >= 1.38)
------------------------------------
Cada botão recebe uma ``key`` previsível com apenas caracteres ASCII
(``{marker}_Hoje``, ``{marker}_7dias``, ``{marker}_Estemes``,
``{marker}_Tudo``).

O Streamlit >= 1.38 expõe a classe ``.st-key-{key}`` no div container
do widget, tornando possível estilizá-lo diretamente pelo seletor CSS
sem depender de seletores de irmão adjacente ou de marcadores
invisíveis — abordagem mais robusta e que sobrepõe qualquer CSS global
com !important definido pelas páginas individuais.

Para empilhar os botões verticalmente na sidebar, o truque do marcador
+ seletor ``:has()`` ainda é usado para o ``stHorizontalBlock``, que
não tem uma key CSS exposta.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple


# Mapeamento label visível -> sufixo de key (apenas ASCII, sem espaços/acentos)
_PRESETS: tuple[tuple[str, str], ...] = (
    ("Hoje",      "Hoje"),
    ("7 dias",    "7dias"),
    ("Este mês",  "Estemes"),
    ("Tudo",      "Tudo"),
)


def _preset_css(marker: str) -> str:
    """Retorna o bloco <style> que:
    1. Empilha verticalmente as colunas dos botões de atalho na sidebar.
    2. Aplica o visual verde-gradiente a cada botão pelo seletor
       ``.st-key-{marker}_{key_suffix}`` — resistente a CSS global
       !important porque inclui o contexto da sidebar na especificidade.
    """
    keys = [f"{marker}_{suffix}" for _, suffix in _PRESETS]

    normal = ",\n    ".join(
        f".st-key-{k} .stButton > button" for k in keys
    )
    normal_hi = ",\n    ".join(
        f'[data-testid="stSidebar"] .st-key-{k} .stButton > button' for k in keys
    )
    hover = ",\n    ".join(
        f".st-key-{k} .stButton > button:hover" for k in keys
    )
    hover_hi = ",\n    ".join(
        f'[data-testid="stSidebar"] .st-key-{k} .stButton > button:hover' for k in keys
    )

    return (
        "<style>\n"
        # ── Layout: empilhamento vertical ──────────────────────────────
        f'    div[data-testid="element-container"]:has(.{marker}-marker)\n'
        f'      + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"] {{\n'
        f'        gap: 6px !important;\n'
        f'        flex-direction: column !important;\n'
        f'        flex-wrap: nowrap !important;\n'
        f'    }}\n'
        f'    div[data-testid="element-container"]:has(.{marker}-marker)\n'
        f'      + div[data-testid="element-container"] div[data-testid="stHorizontalBlock"]\n'
        f'      > div[data-testid="column"] {{\n'
        f'        flex: 1 1 auto !important;\n'
        f'        width: 100% !important;\n'
        f'        min-width: 0 !important;\n'
        f'    }}\n'
        # ── Cor dos botões ────────────────────────────────────────────
        f"    {normal},\n"
        f"    {normal_hi} {{\n"
        f"        background: linear-gradient(135deg, #0E9F6E 0%, #0C8560 100%) !important;\n"
        f"        color: #1A2E25 !important;\n"
        f"        border: none !important;\n"
        f"        font-weight: 700 !important;\n"
        f"        font-size: 11px !important;\n"
        f"        padding: 2px 4px !important;\n"
        f"        min-height: 28px !important;\n"
        f"        height: 28px !important;\n"
        f"        line-height: 1.1 !important;\n"
        f"        border-radius: 8px !important;\n"
        f"        white-space: nowrap !important;\n"
        f"        box-shadow: none !important;\n"
        f"        transition: opacity 0.15s ease, transform 0.15s ease;\n"
        f"    }}\n"
        f"    {hover},\n"
        f"    {hover_hi} {{\n"
        f"        opacity: 0.85 !important;\n"
        f"        background: linear-gradient(135deg, #0E9F6E 0%, #0C8560 100%) !important;\n"
        f"        box-shadow: none !important;\n"
        f"    }}\n"
        "</style>"
    )


def render_date_presets(
    st_module,
    min_d: date,
    max_d: date,
    marker: str,
    range_key: Optional[str] = None,
    start_key: Optional[str] = None,
    end_key: Optional[str] = None,
) -> None:
    """Renderiza a linha compacta de atalhos de período (Hoje/7 dias/Este mês/Tudo).

    Parâmetros
    ----------
    st_module : o módulo ``streamlit`` (ou ``st.sidebar``) usado para renderizar
        os widgets.  Passe sempre ``st.sidebar`` quando os botões devem aparecer
        na sidebar — independentemente de estar ou não dentro de ``with st.sidebar:``.
    min_d, max_d : limites de data disponíveis no dataset.
    marker : identificador único (por página/instância) usado para escopar o CSS.
        Evite reutilizar o mesmo valor em duas chamadas na mesma tela.
    range_key : se informado, grava a tupla (início, fim) escolhida em
        ``st.session_state[range_key]``, para uso em um único ``st.date_input``
        de intervalo.
    start_key, end_key : se informados, gravam separadamente o início e o fim em
        ``st.session_state``, para uso com dois ``st.date_input`` independentes.

    Importante: o valor é escrito em ``st.session_state`` ANTES dos widgets de
    data correspondentes serem criados — portanto esta função deve ser chamada
    antes do(s) ``st.date_input(...)``.
    """
    import streamlit as st

    st_module.markdown(
        f'<span class="{marker}-marker" style="display:none"></span>'
        + _preset_css(marker),
        unsafe_allow_html=True,
    )

    presets: dict[str, tuple[Tuple[date, date], str]] = {
        label: (rng, suffix)
        for (label, suffix), rng in zip(
            _PRESETS,
            [
                (max_d, max_d),
                (max(min_d, max_d - timedelta(days=6)), max_d),
                (max(min_d, max_d.replace(day=1)), max_d),
                (min_d, max_d),
            ],
        )
    }

    cols = st_module.columns(len(presets), gap="small")
    for col, (label, (rng, suffix)) in zip(cols, presets.items()):
        with col:
            if st_module.button(
                label,
                use_container_width=True,
                key=f"{marker}_{suffix}",
            ):
                if range_key:
                    st.session_state[range_key] = rng
                if start_key:
                    st.session_state[start_key] = rng[0]
                if end_key:
                    st.session_state[end_key] = rng[1]
