"""
charts.py
=========
Camada de construção de gráficos ECharts — tema LIGHT.

Regras de ouro aplicadas aqui:
  - backgroundColor: "#FFFFFF" em TODOS os gráficos (evita herança do tema escuro)
  - Todo texto de legenda/rótulo usa cor escura explícita (#1A2E25 ou #4A6B5A)
  - Gráficos de colunas verticais (não horizontais)
  - Labels de valor sempre visíveis com cor sólida
  - Zero transparência em textos dos eixos/legendas
  - Tooltips: fundo escuro translúcido, fonte clara (padrão único em todos os gráficos)
  - Sem linhas de grade (splitLine) em nenhum gráfico
  - Números sempre formatados no padrão BR (ex.: 341100 → 341.100)
"""

from __future__ import annotations
import pandas as pd
from src.shared.echarts_utils import JsCode
from .config import CHART_COLORS, COLOR_PRIMARY, COLOR_TEXT, COLOR_TEXT_MUTED, MP_COLORS

# Cores fixas — nunca deixar herdar do tema
_WHITE      = "#FFFFFF"
_DARK_TEXT  = "#1A2E25"
_MUTED_TEXT = "#4A6B5A"
_AXIS_LINE  = "#C8E8D8"

# Tooltip — dark transparente padrão em todos os gráficos
_TOOLTIP_BG    = "rgba(10,22,18,0.88)"
_TOOLTIP_TEXT  = "#EAFBF3"
_TOOLTIP_MUTED = "#9FE8C9"


# ─────────────────────────────────────────────────────────────────────────────
# Formatação numérica padrão (pt-BR) — usada em TODOS os gráficos
# ─────────────────────────────────────────────────────────────────────────────

# Ex.: 341100 -> "341.100"  |  5.5 -> "5,5"
_NUM_FMT_JS = (
    "function (value) {"
    "  if (value === null || value === undefined || value === '') return '';"
    "  return Number(value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
    "}"
)


def _num_axis_formatter():
    """Formatter de eixo de valores — aplica padrão BR (341.100)."""
    return JsCode(_NUM_FMT_JS)


def _num_label_formatter():
    """Formatter de rótulo de série (params.value) — aplica padrão BR."""
    return JsCode(
        "function (params) {"
        "  var v = params.value;"
        "  if (v === null || v === undefined) return '';"
        "  return Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
        "}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers base
# ─────────────────────────────────────────────────────────────────────────────

def _tooltip(trigger="axis"):
    """Tooltip padrão — fundo escuro translúcido, fonte clara (igual em todos os gráficos)."""
    return {
        "trigger": trigger,
        "backgroundColor": _TOOLTIP_BG,
        "borderColor": COLOR_PRIMARY,
        "borderWidth": 1,
        "padding": [10, 14],
        "textStyle": {"color": _TOOLTIP_TEXT, "fontSize": 12, "fontWeight": "bold"},
        "extraCssText": (
            "box-shadow:0 6px 20px rgba(0,0,0,0.35);"
            "border-radius:10px;"
            "backdrop-filter:blur(4px);"
        ),
    }


def _legend(data=None):
    base = {
        "show": True,
        "textStyle": {
            "color": _DARK_TEXT,
            "fontSize": 12,
            "fontWeight": "600",
        },
        "icon": "roundRect",
        "itemWidth": 14,
        "itemHeight": 9,
        "itemGap": 18,
    }
    if data:
        base["data"] = data
    return base


def _axis_label(rotate=0, font_size=11):
    return {
        "color": _MUTED_TEXT,
        "fontSize": font_size,
        "fontWeight": "600",
        "rotate": rotate,
    }


def _value_axis_label(rotate=0, font_size=11):
    """axisLabel para eixos de VALOR (Y) — oculto em todos os gráficos (mantém apenas o eixo X)."""
    return {"show": False}


def _split_line():
    """Sem linhas de grade — padrão em todos os gráficos."""
    return {"show": False}


def _axis_line():
    return {"lineStyle": {"color": _AXIS_LINE, "width": 1.5}}


def _gradient_color(color_top, color_bottom):
    return {
        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
        "colorStops": [
            {"offset": 0, "color": color_top},
            {"offset": 1, "color": color_bottom},
        ],
    }


def _fmt_date_br(d) -> str:
    """Formata datas no padrão local dd/mm/yyyy — usado em todos os eixos de gráficos."""
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m/%Y")
    return str(d)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Linha — peças por dia (duplo eixo)
# ─────────────────────────────────────────────────────────────────────────────

def build_line_daily(df_day: pd.DataFrame) -> dict:
    """Linha diária de peças + minutos. Fundo branco, texto escuro."""
    dias    = [_fmt_date_br(d) for d in df_day["dia"].tolist()]
    pecas   = df_day["pecas"].tolist()
    minutos = df_day["minutos"].tolist()

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("axis"),
            "axisPointer": {"lineStyle": {"color": COLOR_PRIMARY}},
            "formatter": JsCode(
                "function (params) {"
                "  var html = '<div style=\"font-weight:700;margin-bottom:4px;\">' + params[0].axisValueLabel + '</div>';"
                "  params.forEach(function (p) {"
                "    var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "    html += '<div>' + p.marker + ' ' + p.seriesName + ': <b>' + v + '</b></div>';"
                "  });"
                "  return html;"
                "}"
            ),
        },
        "legend": {
            **_legend(["Peças", "Minutos"]),
            "top": 8,
        },
        "grid": {"left": 60, "right": 60, "bottom": 60, "top": 50},
        "xAxis": {
            "type": "category",
            "data": dias,
            "axisLabel": {**_axis_label(rotate=35, font_size=10)},
            "axisLine": _axis_line(),
            "axisTick": {"lineStyle": {"color": _AXIS_LINE}},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Peças",
                "nameTextStyle": {"color": _MUTED_TEXT, "fontWeight": "600", "fontSize": 11},
                "axisLabel": _value_axis_label(),
                "splitLine": _split_line(),
                "axisLine": {"show": True, **_axis_line()},
            },
            {
                "type": "value",
                "name": "Minutos",
                "nameTextStyle": {"color": _MUTED_TEXT, "fontWeight": "600", "fontSize": 11},
                "axisLabel": _value_axis_label(),
                "splitLine": _split_line(),
                "axisLine": {"show": True, **_axis_line()},
            },
        ],
        "series": [
            {
                "name": "Peças",
                "type": "line",
                "data": pecas,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 5,
                "lineStyle": {"color": CHART_COLORS[0], "width": 2.5},
                "itemStyle": {"color": CHART_COLORS[0], "borderColor": _WHITE, "borderWidth": 2},
                "areaStyle": {
                    "color": _gradient_color("rgba(14,159,110,0.28)", "rgba(14,159,110,0.02)")
                },
            },
            {
                "name": "Minutos",
                "type": "line",
                "yAxisIndex": 1,
                "data": minutos,
                "smooth": True,
                "symbol": "diamond",
                "symbolSize": 6,
                "lineStyle": {"color": CHART_COLORS[1], "width": 2, "type": "dashed"},
                "itemStyle": {"color": CHART_COLORS[1], "borderColor": _WHITE, "borderWidth": 2},
            },
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Colunas — peças por MP  (vertical, não horizontal)
# ─────────────────────────────────────────────────────────────────────────────

def build_bar_mp(df_mp: pd.DataFrame) -> dict:
    """Colunas verticais por MP com rótulos visíveis."""
    mps   = df_mp["mp"].tolist()
    pecas = df_mp["pecas"].tolist()
    cores = [MP_COLORS.get(mp, CHART_COLORS[i % len(CHART_COLORS)]) for i, mp in enumerate(mps)]

    items = [
        {
            "value": v,
            "itemStyle": {
                "color": _gradient_color(c, c + "BB"),
                "borderRadius": [6, 6, 0, 0],
            },
        }
        for v, c in zip(pecas, cores)
    ]

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("item"),
            "formatter": JsCode(
                "function (p) {"
                "  var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "  return p.name + '<br/><b>' + v + '</b> peças';"
                "}"
            ),
        },
        "grid": {"left": 50, "right": 20, "bottom": 40, "top": 40},
        "xAxis": {
            "type": "category",
            "data": mps,
            "axisLabel": {**_axis_label(font_size=13), "fontWeight": "700"},
            "axisLine": _axis_line(),
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": _value_axis_label(),
            "splitLine": _split_line(),
            "axisLine": {"show": False},
        },
        "series": [
            {
                "type": "bar",
                "data": items,
                "barMaxWidth": 70,
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": _num_label_formatter(),
                    "color": _DARK_TEXT,
                    "fontSize": 12,
                    "fontWeight": "700",
                },
                "emphasis": {
                    "itemStyle": {"shadowBlur": 12, "shadowColor": "rgba(14,159,110,0.35)"}
                },
            }
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Rosca — participação % por MP
# ─────────────────────────────────────────────────────────────────────────────

def build_pie_mp(df_mp: pd.DataFrame) -> dict:
    """Rosca com legenda lateral visível em texto escuro."""
    data = [
        {
            "name": row["mp"],
            "value": int(row["pecas"]),
            "itemStyle": {
                "color": MP_COLORS.get(row["mp"], CHART_COLORS[i % len(CHART_COLORS)])
            },
        }
        for i, row in df_mp.iterrows()
    ]
    mp_names = df_mp["mp"].tolist()

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("item"),
            "formatter": JsCode(
                "function (p) {"
                "  var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "  return p.name + '<br/><b>' + v + '</b> peças &nbsp;(' + p.percent + '%)';"
                "}"
            ),
        },
        "legend": {
            **_legend(mp_names),
            "orient": "vertical",
            "right": "4%",
            "top": "center",
            "itemGap": 14,
        },
        "series": [
            {
                "type": "pie",
                "radius": ["40%", "68%"],
                "center": ["38%", "52%"],
                "data": data,
                "label": {
                    "show": True,
                    "formatter": "{b}\n{d}%",
                    "fontSize": 12,
                    "fontWeight": "700",
                    "color": _DARK_TEXT,
                },
                "labelLine": {"lineStyle": {"color": _AXIS_LINE}},
                "emphasis": {
                    "itemStyle": {"shadowBlur": 14, "shadowColor": "rgba(0,0,0,0.15)"},
                    "label": {"fontSize": 14, "fontWeight": "700"},
                },
            }
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Colunas — top 15 oficinas (vertical)
# ─────────────────────────────────────────────────────────────────────────────

def build_bar_oficinas(df_ofic: pd.DataFrame) -> dict:
    """Colunas verticais top oficinas — rótulo de valor no topo."""
    oficinas = df_ofic["oficina"].tolist()
    pecas    = df_ofic["pecas"].tolist()

    items = [
        {
            "value": v,
            "itemStyle": {
                "color": _gradient_color(CHART_COLORS[0], CHART_COLORS[1]),
                "borderRadius": [5, 5, 0, 0],
            },
        }
        for v in pecas
    ]

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("item"),
            "formatter": JsCode(
                "function (p) {"
                "  var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "  return p.name + '<br/><b>' + v + '</b> peças';"
                "}"
            ),
        },
        "grid": {"left": 50, "right": 20, "bottom": 110, "top": 30},
        "xAxis": {
            "type": "category",
            "data": oficinas,
            "axisLabel": {
                **_axis_label(rotate=40, font_size=10),
                "overflow": "truncate",
                "width": 90,
            },
            "axisLine": _axis_line(),
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": _value_axis_label(),
            "splitLine": _split_line(),
            "axisLine": {"show": False},
        },
        "series": [
            {
                "type": "bar",
                "data": items,
                "barMaxWidth": 48,
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": _num_label_formatter(),
                    "color": _DARK_TEXT,
                    "fontSize": 9,
                    "fontWeight": "700",
                },
                "emphasis": {
                    "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(14,159,110,0.35)"}
                },
            }
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Colunas empilhadas — MP por dia
# ─────────────────────────────────────────────────────────────────────────────

def build_stacked_mp_day(df_pivot: pd.DataFrame) -> dict:
    """Colunas verticais empilhadas por MP. Legenda no topo com texto escuro."""
    dias    = [_fmt_date_br(d) for d in df_pivot["dia"].tolist()]
    mp_cols = [c for c in df_pivot.columns if c != "dia"]

    series = [
        {
            "name": mp,
            "type": "bar",
            "stack": "total",
            "data": df_pivot[mp].tolist(),
            "itemStyle": {"color": MP_COLORS.get(mp, CHART_COLORS[i % len(CHART_COLORS)])},
            "emphasis": {"focus": "series"},
            "label": {"show": False},
        }
        for i, mp in enumerate(mp_cols)
    ]

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("axis"),
            "axisPointer": {"type": "shadow", "shadowStyle": {"color": "rgba(14,159,110,0.10)"}},
            "formatter": JsCode(
                "function (params) {"
                "  var html = '<div style=\"font-weight:700;margin-bottom:4px;\">' + params[0].axisValueLabel + '</div>';"
                "  var total = 0;"
                "  params.forEach(function (p) {"
                "    total += Number(p.value) || 0;"
                "    var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "    html += '<div>' + p.marker + ' ' + p.seriesName + ': <b>' + v + '</b></div>';"
                "  });"
                "  html += '<div style=\"margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.2);\">"
                "Total: <b>' + total.toLocaleString('pt-BR', {maximumFractionDigits: 1}) + '</b></div>';"
                "  return html;"
                "}"
            ),
        },
        "legend": {**_legend(mp_cols), "top": 8},
        "grid": {"left": 55, "right": 20, "bottom": 60, "top": 48},
        "xAxis": {
            "type": "category",
            "data": dias,
            "axisLabel": _axis_label(rotate=35, font_size=10),
            "axisLine": _axis_line(),
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": _value_axis_label(),
            "splitLine": _split_line(),
            "axisLine": {"show": False},
        },
        "series": series,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Gauge — progresso da meta
# ─────────────────────────────────────────────────────────────────────────────

def build_gauge_meta(percentual: float, bateu_meta: bool) -> dict:
    """Gauge clean light com texto de detalhe escuro."""
    cor_ativa = "#0E9F6E" if bateu_meta else "#00B4D8"
    pct       = min(percentual, 100)

    return {
        "backgroundColor": _WHITE,
        "series": [
            {
                "type": "gauge",
                "startAngle": 210,
                "endAngle": -30,
                "min": 0,
                "max": 100,
                "radius": "88%",
                "center": ["50%", "58%"],
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [
                            [pct / 100, cor_ativa],
                            [1, "#E0F5EC"],
                        ],
                    }
                },
                "progress": {"show": False},
                "pointer": {
                    "length": "55%",
                    "width": 6,
                    "itemStyle": {"color": cor_ativa},
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "title": {"show": False},
                "detail": {
                    "valueAnimation": True,
                    "formatter": f"{percentual:.1f}%",
                    "color": _DARK_TEXT,
                    "fontSize": 30,
                    "fontWeight": "900",
                    "offsetCenter": [0, "35%"],
                },
                "data": [{"value": pct}],
            }
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Linha semanal
# ─────────────────────────────────────────────────────────────────────────────

def build_line_weekly(df_week: pd.DataFrame) -> dict:
    """Linha semanal com rótulos de valor visíveis."""
    semanas = df_week["semana"].tolist()
    pecas   = df_week["pecas"].tolist()

    return {
        "backgroundColor": _WHITE,
        "tooltip": {
            **_tooltip("axis"),
            "formatter": JsCode(
                "function (params) {"
                "  var p = params[0];"
                "  var v = Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1});"
                "  return p.axisValueLabel + '<br/>' + p.marker + ' ' + p.seriesName + ': <b>' + v + '</b>';"
                "}"
            ),
        },
        "grid": {"left": 55, "right": 20, "bottom": 50, "top": 30},
        "xAxis": {
            "type": "category",
            "data": semanas,
            "axisLabel": _axis_label(rotate=30, font_size=10),
            "axisLine": _axis_line(),
            "axisTick": {"lineStyle": {"color": _AXIS_LINE}},
        },
        "yAxis": {
            "type": "value",
            "axisLabel": _value_axis_label(),
            "splitLine": _split_line(),
            "axisLine": {"show": False},
        },
        "series": [
            {
                "name": "Peças/Semana",
                "type": "line",
                "data": pecas,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 8,
                "lineStyle": {"color": CHART_COLORS[2], "width": 2.5},
                "itemStyle": {
                    "color": CHART_COLORS[2],
                    "borderColor": _WHITE,
                    "borderWidth": 2,
                },
                "areaStyle": {
                    "color": _gradient_color("rgba(20,184,166,0.22)", "rgba(20,184,166,0.01)")
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": _num_label_formatter(),
                    "color": _DARK_TEXT,
                    "fontSize": 10,
                    "fontWeight": "700",
                },
            }
        ],
    }
