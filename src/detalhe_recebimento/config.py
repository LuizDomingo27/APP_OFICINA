"""
config.py
=========
Centraliza as constantes do painel "Detalhe do Recebimento" (planilha
STATUS.xlsx): caminhos, mapeamento de colunas e paleta de cores.

Paleta idêntica à do Painel de Recebimento (`src/recebimento/config.py`)
— mesmo padrão verde neon-aqua usado em todo o app. Os valores são
duplicados aqui (em vez de importados) seguindo o mesmo padrão já usado
por `src/relatorios/page.py`, que mantém cada módulo de painel
autocontido em relação à sua própria paleta visual.
"""

# ---------------------------------------------------------------------------
# Nomes de colunas (planilha STATUS.xlsx)
# ---------------------------------------------------------------------------
COL_ORDEM_MESTRE = "ORDEM MESTRE"
COL_OFICINA      = "OFICINA"
COL_ENVIO        = "ENVIO"
COL_QTD          = "QTD"
COL_MINUTOS      = "MINUTOS"
COL_DEADLINE     = "DEAD LINE"
COL_SITUACAO     = "SITUAÇÃO"
COL_MP           = "MP"
COL_RECEBIMENTO  = "RECEBIMENTO"   # status/operação do recebimento
COL_DIAS_ATRASO  = "Dias / Atraso"
COL_MES          = "Mês"

# ---------------------------------------------------------------------------
# Paleta de cores (neon-aqua green — idêntica ao Painel de Recebimento)
# ---------------------------------------------------------------------------
COLOR_PRIMARY     = "#0E9F6E"
COLOR_SECONDARY   = "#0C8560"
COLOR_BG          = "#F8FFFE"
COLOR_CARD_BG     = "#FFFFFF"
COLOR_TEXT        = "#1A2E25"
COLOR_TEXT_MUTED  = "#6B8F7E"
COLOR_BORDER      = "#D0F0E5"

CHART_COLORS = [
    "#0E9F6E", "#00B4D8", "#14B8A6", "#2DD4BF",
    "#00897B", "#5EEAD4", "#0C8560", "#43AA8B",
]

# ---------------------------------------------------------------------------
# App metadata
# ---------------------------------------------------------------------------
APP_TITLE = "Detalhe do Recebimento"
PAGE_ICON = "🧾"

# Nome da tabela no SQLite (database/app.db)
SQL_TABLE_NAME = "detalhe_recebimento"
