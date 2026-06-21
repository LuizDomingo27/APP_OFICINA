"""
sql_store.py
============
Persistência em SQLite (substitui, base a base, a persistência em .xlsx
de `src/shared/database.py`).

Por quê:
  - Cada base sobe por COMPLETO todo dia (histórico inteiro até hoje, não
    incremental) — então a operação de "atualizar uma base" é sempre uma
    SUBSTITUIÇÃO TOTAL da tabela correspondente, nunca um merge/append.
  - Ler de SQLite em vez de reabrir o .xlsx a cada sessão é mais rápido
    (sem reparsing de Excel) e abre caminho para outros consumidores da
    mesma base (ex.: Power BI via conector SQL), sem depender de
    exportações manuais.

Migração (ver README / histórico de decisões):
  - As 3 bases (envio, recebimento, acompanhamento) já usam este arquivo
    para persistência. `database.py` (.xlsx) ficou só como histórico —
    ver docstring de `database.py` para detalhes do que ainda é usado
    de lá (basicamente nada, fora a leitura de metadata compartilhada).
  - Migração feita base a base, com os scripts `scripts/seed_*.py`
    fazendo a carga única de cada `.xlsx` legado para dentro do `app.db`.

Segurança da substituição (igual em espírito ao `database.py`):
  - Backup do arquivo .db inteiro ANTES de qualquer escrita (mesmo
    esquema de timestamp + `_MAX_BACKUPS` que já existia para os .xlsx).
  - A tabela nova é escrita com outro nome (`<tabela>_new`) e só então
    promovida via RENAME dentro de uma transação — nunca existe um
    instante em que a tabela "real" esteja ausente ou pela metade,
    mesmo que o processo seja interrompido no meio da escrita.
  - `metadata.json` é compartilhado com `database.py` (mesmo arquivo,
    mesmo formato — só muda quem escreve a entrada de cada base).

Cache em memória (st.cache_data) NÃO mora aqui de propósito: cada
módulo (ex.: `src/recebimento/data_loader.py`) decide como e quando
cachear sua própria leitura — este arquivo só fala com o disco.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent / "database"
DB_PATH = BASE_DIR / "app.db"
BACKUP_DIR = BASE_DIR / "_backup"
METADATA_PATH = BASE_DIR / "metadata.json"  # mesmo arquivo usado por database.py

_MAX_BACKUPS = 5  # quantos backups antigos do .db manter


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    # WAL: permite leitura concorrente (telas abertas) enquanto uma
    # substituição de tabela está em andamento, sem "database is locked".
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _tabela_existe(conn: sqlite3.Connection, nome: str) -> bool:
    r = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nome,)
    ).fetchone()
    return r is not None


# ---------------------------------------------------------------------------
# Backup do arquivo .db
# ---------------------------------------------------------------------------

def _checkpoint_wal() -> None:
    """Força a gravação do conteúdo do WAL no arquivo principal do .db.

    Necessário porque o banco roda em modo WAL: dados já comitados podem
    viver só no arquivo `<db>-wal`, não no `.db` principal, até um
    checkpoint acontecer. Copiar o arquivo principal sem isso pode gerar
    um backup vazio ou incompleto — comportamento testado e reproduzido
    (uma cópia feita assim pode nem ter a tabela mais recente).
    """
    with _conn() as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")


def _backup_arquivo_db() -> None:
    if not DB_PATH.exists():
        return  # nada a fazer na primeira escrita (app.db ainda não existe)
    try:
        _checkpoint_wal()
    except sqlite3.Error:
        # Se o checkpoint falhar (ex.: outra conexão concorrente impedindo
        # o TRUNCATE), seguimos com o melhor estado disponível em vez de
        # bloquear a operação — backup "menos perfeito" ainda é melhor que
        # nenhum backup.
        pass
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(DB_PATH, BACKUP_DIR / f"app_{timestamp}.db")
    _limpar_backups_antigos()


def _limpar_backups_antigos() -> None:
    backups = sorted(
        BACKUP_DIR.glob("app_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for antigo in backups[_MAX_BACKUPS:]:
        antigo.unlink(missing_ok=True)


def listar_backups() -> list[Path]:
    """Lista os backups do app.db, do mais recente para o mais antigo."""
    return sorted(
        BACKUP_DIR.glob("app_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Metadata (nome do arquivo original + horário) — mesmo formato de database.py
# ---------------------------------------------------------------------------

def _ler_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_metadata(meta: dict) -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def info_tabela(base_key: str) -> tuple[str | None, str | None]:
    """Retorna (nome_original_do_arquivo, horario_iso) da última carga
    desta base, ou (None, None) se nunca foi carregada."""
    meta = _ler_metadata()
    entrada = meta.get(base_key, {})
    return entrada.get("filename"), entrada.get("loaded_at")


def registrar_metadata(base_key: str, nome_original: str) -> None:
    meta = _ler_metadata()
    meta[base_key] = {
        "filename": nome_original,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    }
    _salvar_metadata(meta)


# ---------------------------------------------------------------------------
# Operações de tabela
# ---------------------------------------------------------------------------

def existe_tabela(nome_tabela: str) -> bool:
    """True se a tabela já existe no banco (equivalente a `existe_base`
    do database.py, mas para SQLite)."""
    if not DB_PATH.exists():
        return False
    with _conn() as conn:
        return _tabela_existe(conn, nome_tabela)


def substituir_tabela(
    nome_tabela: str,
    df: pd.DataFrame,
    indices: list[str] | None = None,
) -> None:
    """Substitui o CONTEÚDO INTEIRO de uma tabela, de forma atômica.

    Estratégia "swap": grava em `<tabela>_new`, cria os índices ali, e só
    troca de nome (RENAME) dentro de uma transação. Isso garante que a
    tabela "real" nunca fica ausente ou pela metade, mesmo se o processo
    cair no meio — diferente de um DROP + CREATE direto na tabela final.

    Como cada base sobe por completo todo dia (sem incremento/dedup),
    esta é a única operação de escrita que este módulo precisa oferecer.

    Cuidado de implementação (testado e comprovado na prática):
      - `df.to_sql(...)` NÃO pode ficar dentro da mesma transação manual
        do swap. O pandas abre e comita sua própria transação interna ao
        escrever — então um `BEGIN` feito antes do `to_sql` é "engolido"
        por esse commit interno, e o swap deixa de estar protegido.
        Também, com um DataFrame vazio (0 linhas), `to_sql` não dispara
        nenhum INSERT, e o `sqlite3` do Python não abre transação
        implícita nenhuma — cada ALTER TABLE seguinte comitaria isolado.
      - Por isso, aqui o staging (escrever `_new`) e o swap (renomear)
        são duas etapas SEPARADAS: a primeira pode falhar/comitar sozinha
        sem risco (o peor caso é uma tabela `_new` órfã, que a próxima
        chamada substitui de qualquer forma via `if_exists="replace"`);
        a segunda usa só `conn.execute()` puro dentro de um
        `BEGIN IMMEDIATE` explícito, sem nenhuma chamada do pandas no
        meio — garantindo que o swap em si é tudo ou nada.
    """
    _backup_arquivo_db()  # cópia do .db ANTES de qualquer escrita

    tmp = f"{nome_tabela}_new"
    conn = _conn()
    try:
        # Etapa 1 — staging: se isto falhar, a tabela real nem chega a
        # ser tocada. Deixado fora da transação manual de propósito
        # (ver docstring acima do porquê).
        # if_exists="replace": garante que _new comece sempre limpo,
        # mesmo que uma escrita anterior tenha sido interrompida.
        df.to_sql(tmp, conn, if_exists="replace", index=False)

        # Etapa 2 — swap: bloco atômico real, só com conn.execute() puro,
        # nenhuma chamada do pandas no meio.
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute(f'DROP TABLE IF EXISTS "{nome_tabela}_old"')
        if _tabela_existe(conn, nome_tabela):
            conn.execute(f'ALTER TABLE "{nome_tabela}" RENAME TO "{nome_tabela}_old"')
        conn.execute(f'ALTER TABLE "{tmp}" RENAME TO "{nome_tabela}"')
        # DROP da tabela antiga também remove os índices que ainda apontavam
        # para ela — por isso os índices novos só são criados DEPOIS desta
        # linha (evita colisão de nome e evita índice com sufixo "_new" preso).
        conn.execute(f'DROP TABLE IF EXISTS "{nome_tabela}_old"')

        for col in (indices or []):
            if col in df.columns:
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{nome_tabela}_{col}" ON "{nome_tabela}"("{col}")'
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def carregar_tabela(nome_tabela: str) -> pd.DataFrame:
    """Lê uma tabela inteira do banco. Sem cache aqui de propósito — cada
    módulo decide sua própria política de cache (ver
    `src/recebimento/data_loader.py::load_from_db`)."""
    with _conn() as conn:
        return pd.read_sql(f'SELECT * FROM "{nome_tabela}"', conn)
