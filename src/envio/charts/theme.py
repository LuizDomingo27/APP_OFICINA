"""Configurações base compartilhadas para os gráficos ECharts."""

from src.envio.config.settings import CHART_HEIGHT

# Altura padrão usada em st_echarts(height=...)
ECHART_HEIGHT = f"{CHART_HEIGHT}px"


def tooltip_dark() -> dict:
    """Tooltip escuro moderno, padrão para todos os gráficos."""
    return {
        "backgroundColor": "#1A2B40",
        "borderColor": "#334155",
        "borderWidth": 1,
        "textStyle": {
            "color": "#F8FAFC",
            "fontSize": 13,
            "fontFamily": "Inter, sans-serif",
        },
        "extraCssText": (
            "border-radius:8px;"
            "box-shadow:0 4px 16px rgba(0,0,0,.28);"
            "padding:10px 14px;"
        ),
    }


def axis_label(rotate: int = 0, interval: int = 0) -> dict:
    return {
        "fontSize": 12,
        "color": "#475569",
        "fontFamily": "Inter, sans-serif",
        "rotate": rotate,
        "interval": interval,
    }


def split_line() -> dict:
    return {"lineStyle": {"type": "dashed", "color": "rgba(148,163,184,0.22)"}}


def grid(left="2%", right="3%", bottom="12%", top="14%") -> dict:
    return {
        "left": left,
        "right": right,
        "bottom": bottom,
        "top": top,
        "containLabel": True,
    }


def linear_gradient(top_color: str, bottom_color: str) -> dict:
    return {
        "type": "linear",
        "x": 0, "y": 0, "x2": 0, "y2": 1,
        "colorStops": [
            {"offset": 0, "color": top_color},
            {"offset": 1, "color": bottom_color},
        ],
    }
