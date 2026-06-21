"""
seed_acompanhamento.py
=======================
Migração única (seed) da base de Acompanhamento: lê o `.xlsx` que já está
salvo em `database/acompanhamento.xlsx` (mecanismo antigo, ver
`src/shared/database.py`), aplica a MESMA normalização de negócio que o
app já usa (`_normalize_acompanhamento`, em `src/acompanhamento/loader.py`)
e grava em `database/app.db` (SQLite, ver `src/shared/sql_store.py`).

Só as colunas de `CANONICAL_COLUMNS` vão para o banco — a planilha real
traz ~30 colunas extras (nomes com acento, duplicadas, 100% vazias) que
o app nunca usa e que não fazem sentido morar no esquema do SQLite (ver
`select_canonical_columns` em `src/acompanhamento/loader.py`).

Roda fora do Streamlit de propósito. É só:

    python scripts/seed_acompanhamento.py

Depois de rodar, a tela "⚙️ Atualizar Bases" e a sessão normal do app já
vão ler do banco automaticamente (ver `src/shared/state.py`).

Importante: este script NÃO apaga `database/acompanhamento.xlsx` — o
arquivo antigo continua intacto, como uma cópia de segurança adicional
até você se sentir confortável com o novo mecanismo.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar como `python scripts/seed_acompanhamento.py` a partir da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.acompanhamento.loader import (
    _normalize_acompanhamento,
    select_canonical_columns,
    AcompanhamentoLoadError,
)
from src.shared import sql_store

XLSX_ANTIGO = ROOT / "database" / "acompanhamento.xlsx"


def main() -> int:
    if not XLSX_ANTIGO.exists():
        print(f"[ERRO] Arquivo não encontrado: {XLSX_ANTIGO}")
        return 1

    print(f"Lendo {XLSX_ANTIGO} ...")
    df_bruto = pd.read_excel(XLSX_ANTIGO)
    print(f"  {len(df_bruto):,} linhas brutas lidas.".replace(",", "."))

    try:
        df_normalizado = _normalize_acompanhamento(df_bruto)
    except AcompanhamentoLoadError as exc:
        print(f"[ERRO] Planilha inválida: {exc}")
        return 1

    df_limpo = select_canonical_columns(df_normalizado)
    print(f"  {len(df_limpo):,} linhas após normalização (Costura).".replace(",", "."))
    print(f"  {len(df_limpo.columns)} colunas canônicas selecionadas para o banco "
          f"(de {len(df_normalizado.columns)} colunas brutas).")

    print("Gravando em database/app.db (tabela 'acompanhamento')...")
    sql_store.substituir_tabela(
        "acompanhamento", df_limpo, indices=["ENVIO", "MP", "OFICINA", "DEPARTAMENTO"]
    )
    sql_store.registrar_metadata("acompanhamento", XLSX_ANTIGO.name)

    print("Validando leitura de volta do banco...")
    df_volta = sql_store.carregar_tabela("acompanhamento")
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
