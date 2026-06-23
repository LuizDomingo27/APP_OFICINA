"""
seed_detalhe_recebimento.py
============================
Migração (seed) da base "Detalhe do Recebimento": lê a planilha STATUS.xlsx,
aplica a mesma normalização de negócio que o app já usa
(`_normalize_raw`, em `src/detalhe_recebimento/data_loader.py`) e grava em
`database/app.db` (SQLite, ver `src/shared/sql_store.py`), na tabela
`detalhe_recebimento`.

Diferente dos demais scripts de seed (envio/recebimento/acompanhamento),
não existe um `.xlsx` legado fixo em `database/` para esta base — ela é
nova. Por isso o caminho do arquivo é informado por parâmetro:

    python scripts/seed_detalhe_recebimento.py /caminho/para/STATUS.xlsx

Se nenhum caminho for passado, tenta usar `database/status.xlsx` por
padrão (caso você prefira copiar o arquivo pra lá antes de rodar).

Depois de rodar, a tela "⚙️ Atualizar Bases" e a sessão normal do app já
vão ler do banco automaticamente (ver `src/shared/state.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar como `python scripts/seed_detalhe_recebimento.py` a partir da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.detalhe_recebimento.data_loader import _normalize_raw, DataLoadError
from src.detalhe_recebimento.config import SQL_TABLE_NAME
from src.shared import sql_store

XLSX_PADRAO = ROOT / "database" / "status.xlsx"


def main() -> int:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else XLSX_PADRAO

    if not caminho.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}")
        print("Uso: python scripts/seed_detalhe_recebimento.py /caminho/para/STATUS.xlsx")
        return 1

    print(f"Lendo {caminho} ...")
    df_bruto = pd.read_excel(caminho)
    print(f"  {len(df_bruto):,} linhas brutas lidas.".replace(",", "."))

    try:
        # dayfirst=True: planilha original traz ENVIO como texto "DD/MM/AAAA"
        df_limpo = _normalize_raw(df_bruto, dayfirst=True)
    except DataLoadError as exc:
        print(f"[ERRO] Planilha inválida: {exc}")
        return 1

    print(f"  {len(df_limpo):,} linhas após normalização.".replace(",", "."))

    print(f"Gravando em database/app.db (tabela '{SQL_TABLE_NAME}')...")
    sql_store.substituir_tabela(
        SQL_TABLE_NAME, df_limpo, indices=["ENVIO", "MP", "OFICINA", "RECEBIMENTO"]
    )
    sql_store.registrar_metadata(SQL_TABLE_NAME, caminho.name)

    print("Validando leitura de volta do banco...")
    df_volta = sql_store.carregar_tabela(SQL_TABLE_NAME)
    if len(df_volta) != len(df_limpo):
        print(
            f"[AVISO] Linhas gravadas ({len(df_limpo)}) != linhas lidas de volta "
            f"({len(df_volta)}). Verifique antes de seguir."
        )
        return 1

    print(f"✅ Seed concluído: {len(df_volta):,} linhas em database/app.db.".replace(",", "."))
    print(f"   Backup do .db (se já existisse) em: database/_backup/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
