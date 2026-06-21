"""Construtores de gráficos ECharts — visual moderno e profissional."""

from __future__ import annotations

from src.shared.echarts_utils import JsCode

from src.envio.charts.theme import (
    axis_label,
    grid,
    linear_gradient,
    split_line,
    tooltip_dark,
)

# ── Paleta do donut ────────────────────────────────────────────────────────────
PALETTE_DONUT = [
    "#0C8560", "#0E9F6E", "#06B281", "#6FC3A8",
    "#047857", "#34D399", "#10B981", "#A7F3D0",
]

# ── JS helpers reutilizáveis ───────────────────────────────────────────────────
_FMT_K = JsCode(
    "function(v){"
    "  if(v>=1000000) return (v/1000000).toFixed(1).replace('.',',')+' M';"
    "  if(v>=1000)    return (v/1000).toFixed(1).replace('.',',')+' k';"
    "  return v;"
    "}"
)
_FMT_BR = JsCode("function(p){return p.value.toLocaleString('pt-BR');}")


def _bar_label() -> dict:
    return {
        "show": True,
        "position": "top",
        "fontSize": 11,
        "fontWeight": "bold",
        "color": "#1E293B",
        "fontFamily": "Inter, sans-serif",
        "formatter": _FMT_BR,
    }


# ── Barras: Oficinas ───────────────────────────────────────────────────────────

def build_oficinas_column_chart(df) -> dict:
    """Gráfico de colunas — top oficinas com rótulos e tooltip rico."""
    names = df["OFICINA"].tolist()
    qtd   = [int(v) for v in df["QTD"]]
    mins  = [int(v) for v in df["MIN"]]
    max_v = max(qtd) if qtd else 1

    fmt = JsCode("""
    function(params) {
        var p = params[0], m = params[1];
        return '<div style="font-weight:600;margin-bottom:5px">' + p.name + '</div>' +
            p.marker + ' Peças: <b>' + p.value.toLocaleString('pt-BR') + '</b><br/>' +
            '<span style="opacity:.75">&#9201; Minutos: <b>' +
            (m ? m.value.toLocaleString('pt-BR') : '—') + '</b></span>';
    }
    """)

    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": fmt,
            **tooltip_dark(),
        },
        "grid": grid(bottom="14%"),
        "xAxis": {
            "type": "category",
            "data": names,
            "axisLabel": axis_label(rotate=35),
            "axisLine": {"lineStyle": {"color": "#E2E8F0"}},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "name": "Peças",
            "nameTextStyle": {"color": "#94A3B8", "fontSize": 12},
            "axisLabel": {**axis_label(), "formatter": _FMT_K},
            "splitLine": split_line(),
            "max": int(max_v * 1.22),
        },
        "series": [
            {
                "name": "Peças",
                "type": "bar",
                "data": qtd,
                "barMaxWidth": 54,
                "itemStyle": {
                    "borderRadius": [5, 5, 0, 0],
                    "color": linear_gradient("#0C8560", "#A7F3D0"),
                },
                "label": _bar_label(),
                "emphasis": {
                    "itemStyle": {"color": linear_gradient("#047857", "#6EE7B7")},
                },
            },
            {
                "name": "Minutos",
                "type": "line",
                "data": mins,
                "lineStyle": {"opacity": 0},
                "itemStyle": {"opacity": 0},
                "symbol": "none",
                "emphasis": {"disabled": True},
            },
        ],
    }


# ── Barras: Frete ──────────────────────────────────────────────────────────────

def build_frete_column_chart(df) -> dict:
    """Gráfico de colunas — transportes por tipo de frete."""
    names  = df["FRETE"].tolist()
    qtd    = [int(v) for v in df["QTD"]]
    envios = [int(v) for v in df["Envios"]]
    max_v  = max(qtd) if qtd else 1

    fmt = JsCode("""
    function(params) {
        var p = params[0], e = params[1];
        return '<div style="font-weight:600;margin-bottom:5px">' + p.name + '</div>' +
            p.marker + ' Peças: <b>' + p.value.toLocaleString('pt-BR') + '</b><br/>' +
            '<span style="opacity:.75">&#128230; Envios: <b>' +
            (e ? e.value.toLocaleString('pt-BR') : '—') + '</b></span>';
    }
    """)

    return {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": fmt,
            **tooltip_dark(),
        },
        "grid": grid(bottom="10%"),
        "xAxis": {
            "type": "category",
            "data": names,
            "axisLabel": axis_label(rotate=20),
            "axisLine": {"lineStyle": {"color": "#E2E8F0"}},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value",
            "name": "Peças",
            "nameTextStyle": {"color": "#94A3B8", "fontSize": 12},
            "axisLabel": {**axis_label(), "formatter": _FMT_K},
            "splitLine": split_line(),
            "max": int(max_v * 1.22),
        },
        "series": [
            {
                "name": "Peças",
                "type": "bar",
                "data": qtd,
                "barMaxWidth": 60,
                "itemStyle": {
                    "borderRadius": [5, 5, 0, 0],
                    "color": linear_gradient("#06B281", "#A7F3D0"),
                },
                "label": _bar_label(),
                "emphasis": {
                    "itemStyle": {"color": linear_gradient("#047857", "#6EE7B7")},
                },
            },
            {
                "name": "Envios",
                "type": "line",
                "data": envios,
                "lineStyle": {"opacity": 0},
                "itemStyle": {"opacity": 0},
                "symbol": "none",
                "emphasis": {"disabled": True},
            },
        ],
    }


# ── Donut: MP ──────────────────────────────────────────────────────────────────

def build_mp_donut_chart(df) -> dict:
    """Donut profissional com total central e legenda lateral."""
    total     = int(df["QTD"].sum())
    total_str = f"{total:,}".replace(",", ".")

    items = [
        {"name": str(row["MP"]), "value": int(row["QTD"])}
        for _, row in df.iterrows()
    ]

    tip_fmt = JsCode("""
    function(p) {
        return '<div style="font-weight:600;margin-bottom:4px">' + p.name + '</div>' +
            p.marker +
            ' Peças: <b>' + p.value.toLocaleString('pt-BR') + '</b><br/>' +
            'Participação: <b>' + p.percent.toFixed(1) + '%</b>';
    }
    """)

    lbl_fmt = JsCode(
        "function(p){ return p.name + '\\n' + p.percent.toFixed(1) + '%'; }"
    )

    return {
        "backgroundColor": "transparent",
        "color": PALETTE_DONUT,
        "tooltip": {
            "trigger": "item",
            "formatter": tip_fmt,
            **tooltip_dark(),
        },
        "legend": {
            "orient": "vertical",
            "right": "3%",
            "top": "center",
            "icon": "circle",
            "itemWidth": 10,
            "itemHeight": 10,
            "itemGap": 12,
            "textStyle": {
                "fontSize": 12,
                "color": "#475569",
                "fontFamily": "Inter, sans-serif",
            },
        },
        "graphic": [
            {
                "type": "text",
                "left": "36%",
                "top": "50%",
                "z": 10,
                "style": {
                    "text": "{value|" + total_str + "}\n{label|peças}",
                    "textAlign": "center",
                    "textVerticalAlign": "middle",
                    "fontFamily": "Inter, sans-serif",
                    "rich": {
                        "value": {
                            "fontSize": 22,
                            "fontWeight": "bold",
                            "fill": "#0F1B2D",
                            "lineHeight": 26,
                            "align": "center",
                        },
                        "label": {
                            "fontSize": 12,
                            "fill": "#94A3B8",
                            "lineHeight": 16,
                            "align": "center",
                        },
                    },
                },
            },
        ],
        "series": [
            {
                "name": "MP",
                "type": "pie",
                "radius": ["52%", "72%"],
                "center": ["39.7%", "52%"],
                "data": items,
                "label": {
                    "show": True,
                    "formatter": lbl_fmt,
                    "fontSize": 12,
                    "color": "#334155",
                    "lineHeight": 18,
                    "fontFamily": "Inter, sans-serif",
                },
                "labelLine": {
                    "length": 14,
                    "length2": 8,
                    "lineStyle": {"color": "#CBD5E1", "width": 1.2},
                },
                "itemStyle": {
                    "borderRadius": 4,
                    "borderColor": "#FFFFFF",
                    "borderWidth": 2,
                },
                "emphasis": {
                    "scaleSize": 6,
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0,0,0,.15)",
                    },
                },
            }
        ],
    }


# ── Área: Evolução diária ──────────────────────────────────────────────────────

def build_daily_area_chart(df) -> dict:
    """Evolução diária — área suave com eixo duplo e marcadores."""
    # Formata datas como DD/MM para exibição no eixo
    dates = []
    for d in df["DATA"]:
        try:
            import pandas as pd
            ts = pd.Timestamp(d)
            dates.append(ts.strftime("%d/%m"))
        except Exception:
            dates.append(str(d)[:10])

    qtd  = [int(v) for v in df["QTD"]]
    mins = [int(v) for v in df["MIN"]]

    tip_fmt = JsCode("""
    function(params) {
        var out = '<div style="font-weight:600;margin-bottom:5px">' + params[0].axisValueLabel + '</div>';
        params.forEach(function(p) {
            out += p.marker + ' ' + p.seriesName +
                ': <b>' + p.value.toLocaleString('pt-BR') + '</b><br/>';
        });
        return out;
    }
    """)

    area_color = {
        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
        "colorStops": [
            {"offset": 0, "color": "rgba(14,159,110,0.22)"},
            {"offset": 1, "color": "rgba(14,159,110,0.02)"},
        ],
    }

    return {
        "backgroundColor": "transparent",
        "color": ["#0C8560", "#0E9F6E"],
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {
                "type": "cross",
                "label": {"backgroundColor": "#334155"},
            },
            "formatter": tip_fmt,
            **tooltip_dark(),
        },
        "legend": {
            "data": ["Peças", "Minutos"],
            "top": 2,
            "icon": "roundRect",
            "itemWidth": 16,
            "itemHeight": 8,
            "itemGap": 20,
            "textStyle": {
                "fontSize": 12,
                "color": "#475569",
                "fontFamily": "Inter, sans-serif",
            },
        },
        "grid": grid(bottom="10%", top="16%"),
        "xAxis": {
            "type": "category",
            "data": dates,
            "boundaryGap": False,
            "axisLabel": axis_label(rotate=30),
            "axisLine": {"lineStyle": {"color": "#E2E8F0"}},
            "axisTick": {"show": False},
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Peças",
                "nameTextStyle": {"color": "#94A3B8", "fontSize": 12},
                "axisLabel": {**axis_label(), "formatter": _FMT_K},
                "splitLine": split_line(),
            },
            {
                "type": "value",
                "name": "Minutos",
                "nameLocation": "end",
                "nameTextStyle": {"color": "#94A3B8", "fontSize": 12},
                "axisLabel": {**axis_label(), "formatter": _FMT_K},
                "splitLine": {"show": False},
                "position": "right",
            },
        ],
        "series": [
            {
                "name": "Peças",
                "type": "line",
                "smooth": True,
                "data": qtd,
                "yAxisIndex": 0,
                "symbol": "circle",
                "symbolSize": 6,
                "itemStyle": {
                    "color": "#0C8560",
                    "borderColor": "#FFFFFF",
                    "borderWidth": 2,
                },
                "lineStyle": {"width": 2.5, "color": "#0C8560"},
                "areaStyle": {"color": area_color},
            },
            {
                "name": "Minutos",
                "type": "line",
                "smooth": True,
                "data": mins,
                "yAxisIndex": 1,
                "symbol": "diamond",
                "symbolSize": 7,
                "itemStyle": {
                    "color": "#0E9F6E",
                    "borderColor": "#FFFFFF",
                    "borderWidth": 2,
                },
                "lineStyle": {"width": 2, "color": "#0E9F6E", "type": "dashed"},
            },
        ],
    }


# ── Gauge: progresso da meta (mesmo visual do Painel de Recebimento) ──────────

def build_gauge_meta(percentual: float, bateu_meta: bool) -> dict:
    """Gauge clean light com texto de detalhe escuro — paleta NEON/ACCENT do Envio."""
    cor_ativa = "#0E9F6E" if bateu_meta else "#0C8560"
    pct       = min(percentual, 100)

    return {
        "backgroundColor": "#FFFFFF",
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
                            [1, "#E6ECEF"],
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
                    "color": "#0F1B2D",
                    "fontSize": 30,
                    "fontWeight": "900",
                    "offsetCenter": [0, "35%"],
                },
                "data": [{"value": pct}],
            }
        ],
    }
