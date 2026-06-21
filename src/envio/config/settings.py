"""Constantes e configurações globais da aplicação."""

from pathlib import Path

# Caminho absoluto, independente do diretório de onde o Streamlit é iniciado.
APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = APP_ROOT / "ENVIOS_OFICINAS.xlsx"

# Versão do esquema de normalização. Incremente sempre que `_normalize`
# (em app/data/loader.py) mudar de comportamento, para invalidar o cache
# em disco de planilhas já processadas com a lógica antiga.
SCHEMA_VERSION = "v2"

REQUIRED_COLUMNS = ("ENVIO", "QTD", "MINUTOS", "MP", "PDV", "OFICINA")
TEXT_COLUMNS = ("MP", "PDV", "OFICINA", "FRETE", "ORIGEM", "SITUAÇÃO")
HIDDEN_COLUMNS = frozenset({"ORDEM"})
STATUS_OK = frozenset({"OK", "ENTREGUE", "FINALIZADO"})

# Limites para o cache em disco de planilhas processadas (.cache/data).
CACHE_MAX_FILES = 30
CACHE_MAX_AGE_DAYS = 14

TABLE_ROW_OPTIONS = (50, 80, 150, 300)
DEFAULT_TABLE_ROWS = 80
TOP_OFICINAS = 15
TOP_MP = 8

DEFAULT_META_PECAS = 0
DEFAULT_META_MINUTOS = 0

CHART_HEIGHT = 420
