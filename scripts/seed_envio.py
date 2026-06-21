"""
seed_envio.py
=============
Migração única (seed) da base de Envios: lê o `.xlsx` que já está salvo
em `database/envio.xlsx` (mecanismo antigo, ver `src/shared/database.py`),
aplica a MESMA normalização de negócio que o app já usa (`_normalize`, em
`src/envio/data/loader.py`) e grava o resultado em `database/app.db`
(SQLite, ver `src/shared/sql_store.py`).

Roda fora do Streamlit de propósito (nenhuma das funções de normalização
chamadas aqui depende de cache rodando dentro de uma sessão ativa) — é só:

    python scripts/seed_envio.py

Depois de rodar, a tela "⚙️ Atualizar Bases" e a sessão normal do app já
vão ler do banco automaticamente (ver `src/shared/state.py`).

Importante: este script NÃO apaga `database/envio.xlsx` — o arquivo
antigo continua intacto, como uma cópia de segurança adicional até você
se sentir confortável com o novo mecanismo.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar como `python scripts/seed_envio.py` a partir da raiz do projeto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envio.data.loader import _normalize, _read_excel, PlanilhaInvalidaError
from src.shared import sql_store

XLSX_ANTIGO = ROOT / "database" / "envio.xlsx"


def main() -> int:
    if not XLSX_ANTIGO.exists():
        print(f"[ERRO] Arquivo não encontrado: {XLSX_ANTIGO}")
        return 1

    print(f"Lendo {XLSX_ANTIGO} ...")
    df_bruto = _read_excel(XLSX_ANTIGO.read_bytes())
    print(f"  {len(df_bruto):,} linhas brutas lidas.".replace(",", "."))

    try:
        df_limpo = _normalize(df_bruto)
    except PlanilhaInvalidaError as exc:
        print(f"[ERRO] Planilha inválida: {exc}")
        return 1

    print(f"  {len(df_limpo):,} linhas após normalização.".replace(",", "."))

    print("Gravando em database/app.db (tabela 'envio')...")
    sql_store.substituir_tabela(
        "envio", df_limpo, indices=["ENVIO", "MP", "PDV", "OFICINA"]
    )
    sql_store.registrar_metadata("envio", XLSX_ANTIGO.name)

    print("Validando leitura de volta do banco...")
    df_volta = sql_store.carregar_tabela("envio")
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
