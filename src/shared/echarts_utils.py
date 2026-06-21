"""Renderização de gráficos ECharts — sem depender do pacote ``streamlit-echarts``.

Por que isso existe
--------------------
O projeto usava ``streamlit-echarts==0.4.0``, fixado de propósito porque
versões mais novas (>=0.6.0) migraram para a API de componentes v2 do
Streamlit. O problema é que a 0.4.0 não sabe converter ``formatter``
construídos com ``JsCode(...)`` de volta em função JavaScript real no
front-end — esse mecanismo só foi implementado a partir da 0.6.0. Resultado
prático: o ``formatter`` chegava ao ECharts como uma *string literal*
qualquer, e o gráfico exibia nos tooltips o texto/código da função em vez do
valor calculado.

Em vez de depender de mais uma versão (ou de outro pacote de terceiros com o
mesmo tipo de ponte Python→JS), este módulo renderiza o gráfico ECharts
**diretamente em HTML/JS**, via ``st.components.v1.html``. O ``option`` do
ECharts continua sendo um dict Python normal (igual antes); a única
diferença é que os formatters/callbacks (``JsCode``) são embutidos como
função JavaScript real dentro do HTML gerado — sem qualquer "tradução"
intermediária que possa falhar.

Uso
---
A API pública é a mesma de antes, então os call-sites não mudam:

    from src.shared.echarts_utils import safe_st_echarts, JsCode

    safe_st_echarts(options=meu_option_dict, height="340px")

``JsCode`` agora é definido aqui (e não mais importado de
``streamlit_echarts``) — ver ``src/envio/charts/builders.py`` e
``src/recebimento/charts.py``.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

# A partir de certas versões do Streamlit, ``st.components.v1.html`` foi
# substituído por ``st.iframe`` (mais simples, suporta HTML string direto).
# Detectamos em runtime para funcionar tanto em instalações novas quanto em
# instalações mais antigas — sem repetir o problema de pin de versão frágil
# que motivou trocar o streamlit-echarts.
_HAS_ST_IFRAME = hasattr(st, "iframe")

# ECharts servido via CDN (carregado no navegador do usuário, não no
# servidor). Versão travada para estabilidade visual.
_ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"


class JsCode:
    """Marca uma string como código JavaScript literal (função/callback).

    Mantém a mesma interface usada anteriormente com
    ``streamlit_echarts.JsCode`` (atributo ``.js_code``), para que
    ``builders.py`` / ``charts.py`` precisem alterar apenas o import.
    """

    __slots__ = ("js_code", "_placeholder")

    def __init__(self, js_code: str) -> None:
        self.js_code = js_code.strip()
        # Placeholder único por instância — evita colisão entre múltiplos
        # formatters/callbacks no mesmo gráfico.
        self._placeholder = f"__JSCODE_{uuid.uuid4().hex}__"

    def __repr__(self) -> str:  # pragma: no cover - apenas debug
        return f"JsCode({self.js_code!r})"


def _collect_and_strip_jscode(value: Any, registry: dict[str, str]) -> Any:
    """Percorre o options dict, troca cada ``JsCode`` por um placeholder
    string e guarda o JS real em ``registry`` (placeholder -> código).
    """
    if isinstance(value, JsCode):
        registry[value._placeholder] = value.js_code
        return value._placeholder
    if isinstance(value, dict):
        return {k: _collect_and_strip_jscode(v, registry) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_collect_and_strip_jscode(v, registry) for v in value]
    return value


def _options_to_js_literal(options: dict) -> str:
    """Serializa ``options`` para um literal de objeto JavaScript válido,
    com os ``JsCode`` embutidos como função real (não como string)."""
    registry: dict[str, str] = {}
    safe_options = _collect_and_strip_jscode(options, registry)
    json_str = json.dumps(safe_options, ensure_ascii=False)

    # Cada placeholder aparece no JSON como uma string entre aspas
    # ("__JSCODE_xxx__"); substituímos pelo código JS puro, removendo as
    # aspas, para que vire uma função de fato no objeto final.
    for placeholder, js_code in registry.items():
        json_str = json_str.replace(f'"{placeholder}"', js_code)
    return json_str


def _height_to_px(height: Any) -> int:
    """Aceita "340px", "340", ou int — sempre retorna um int em pixels."""
    if isinstance(height, (int, float)):
        return int(height)
    return int(str(height).strip().lower().replace("px", "") or 400)


def safe_st_echarts(
    options: dict,
    height: Any = "400px",
    width: Any = "100%",
    renderer: str = "canvas",
    theme: str | None = None,
    key: str | None = None,
) -> None:
    """Renderiza um gráfico ECharts a partir de um ``options`` dict.

    Aceita os mesmos parâmetros usados anteriormente com
    ``streamlit_echarts.st_echarts`` (height, width, renderer, theme, key) —
    os call-sites existentes (``page.py``, ``goal.py``, ``components.py``)
    não precisam ser alterados.
    """
    height_px = _height_to_px(height)
    width_css = width if isinstance(width, str) else f"{width}px"
    div_id = f"echarts_{(key or uuid.uuid4().hex)}"
    option_js = _options_to_js_literal(options)
    theme_js = json.dumps(theme) if theme else "null"

    html_code = f"""
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background-color: transparent;
        }}
    </style>
    <div id="{div_id}" style="width:{width_css};height:{height_px}px;"></div>
    <script src="{_ECHARTS_CDN}"></script>
    <script>
    (function() {{
        function renderChart() {{
            var el = document.getElementById("{div_id}");
            if (!el || typeof echarts === "undefined") {{
                setTimeout(renderChart, 50);
                return;
            }}
            var existing = echarts.getInstanceByDom(el);
            if (existing) {{
                existing.dispose();
            }}
            var chart = echarts.init(el, {theme_js}, {{renderer: "{renderer}"}});
            var option = {option_js};
            chart.setOption(option);

            // Reage a mudanças de tamanho do container (sidebar, abas,
            // resize de janela) — mitiga o problema clássico de componentes
            // em iframe medirem largura 0 no momento do mount.
            var resizeObserver = new ResizeObserver(function() {{
                chart.resize();
            }});
            resizeObserver.observe(el);
            window.addEventListener("resize", function() {{ chart.resize(); }});
        }}
        renderChart();
    }})();
    </script>
    """
    if _HAS_ST_IFRAME:
        st.iframe(html_code, height=height_px + 4, width="stretch")
    else:
        components.html(html_code, height=height_px + 4, width=None)
