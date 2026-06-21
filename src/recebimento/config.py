"""
config.py
=========
Centraliza todas as constantes da aplicação:
  - caminhos de arquivo
  - mapeamentos de colunas
  - paleta de cores e tema
  - parâmetros de negócio

Altere aqui para propagar mudanças em todo o sistema.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Column names
# ---------------------------------------------------------------------------
COL_DIA           = "DIA"
COL_OFICINA       = "OFICINA"
COL_ORDEM_MESTRE  = "ORDEM MESTRE"
COL_MP            = "MP"
COL_PECAS         = "REAL CORTADO"
COL_MINUTOS       = "MINUTOS"

# ---------------------------------------------------------------------------
# MP normalisation map  (raw → padronizado)
# ---------------------------------------------------------------------------
MP_NORM = {
    "Malha": "MALHA",
    "Tear":  "TEAR",
}

# ---------------------------------------------------------------------------
# Colour palette  (neon-aqua green accent on clean white)
# ---------------------------------------------------------------------------
COLOR_PRIMARY     = "#0E9F6E"   # neon-aqua green
COLOR_SECONDARY   = "#0C8560"   # darker green accent
COLOR_BG          = "#F8FFFE"   # near-white background
COLOR_CARD_BG     = "#FFFFFF"
COLOR_TEXT        = "#1A2E25"   # dark text
COLOR_TEXT_MUTED  = "#6B8F7E"
COLOR_BORDER      = "#D0F0E5"
COLOR_DANGER      = "#FF6B6B"
COLOR_WARNING     = "#FFB347"
COLOR_SUCCESS     = "#0E9F6E"

# ECharts palettes per MP — paleta padronizada verde / neon-aqua
MP_COLORS = {
    "JEANS":   "#0E9F6E",   # verde neon (cor principal)
    "MALHA":   "#00B4D8",   # aqua
    "TEAR":    "#14B8A6",   # teal
    "POLO":    "#2DD4BF",   # turquesa
    "ECOBAGS": "#00897B",   # verde-petróleo
}
DEFAULT_CHART_COLOR = "#0E9F6E"

CHART_COLORS = [
    "#0E9F6E", "#00B4D8", "#14B8A6", "#2DD4BF",
    "#00897B", "#5EEAD4", "#0C8560", "#43AA8B",
]

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_TITLE   = "Painel de Recebimento"
APP_VERSION = "1.0.0"
PAGE_ICON   = "📦"
