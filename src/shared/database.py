"""
database.py
============
Persistência simples em disco das planilhas (Envio, Recebimento, Acompanhamento).

⚠️ LEGADO — desde a migração completa para SQLite, as 3 bases (Envio,
Recebimento, Acompanhamento) são lidas e gravadas via
`src/shared/sql_store.py` (`database/app.db`). Este módulo não é mais
usado para salvar/carregar planilhas no fluxo normal do app.

O que ainda é usado deste arquivo:
  - `info_base()`: o card "base já carregada" (home.py) continua lendo
    daqui, porque `sql_store.py` escreve no MESMO `database/metadata.json`,
    com as mesmas chaves ("envio", "recebimento", "acompanhamento") — então
    `info_base()` funciona igual, independente de qual dos dois mecanismos
    gravou a base.

O que ficou só como histórico/rede de segurança:
  - `database/envio.xlsx`, `database/recebimento.xlsx` e
    `database/acompanhamento.xlsx` continuam no disco (não foram apagados
    de propósito), mas nada no app os lê mais — só os scripts de seed
    (`scripts/seed_*.py`), que foram a migração única para o SQLite.
  - `salvar_base`, `existe_base`, `ler_bytes_base`, `remover_base` e
    `listar_backups` seguem funcionando (não foram removidas), mas não há
    mais nenhuma chamada a elas no app — mantidas apenas por precaução.

Esta pasta NÃO deve ser versionada no Git (ver .gitignore) — dados de
produção têm ciclo de vida próprio, independente do código.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

# database/ na raiz do projeto (dois níveis acima de src/shared/database.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent / "database"
BACKUP_DIR = BASE_DIR / "_backup"
METADATA_PATH = BASE_DIR / "metadata.json"

_MAX_BACKUPS = 5  # quantos backups antigos manter por base

ARQUIVOS = {
    "envio": "envio.xlsx",
    "recebimento": "recebimento.xlsx",
    "acompanhamento": "acompanhamento.xlsx",
}

BASE_LABELS = {
    "envio": "Envios",
    "recebimento": "Recebimento",
    "acompanhamento": "Acompanhamento",
}


def _garantir_pastas() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _ler_metadata() -> dict:
    if not METADATA_PATH.exists():
        return {}
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _salvar_metadata(meta: dict) -> None:
    _garantir_pastas()
    METADATA_PATH.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def caminho_base(base_key: str) -> Path:
    return BASE_DIR / ARQUIVOS[base_key]


def existe_base(base_key: str) -> bool:
    """True se já existe uma versão salva em disco desta base."""
    _garantir_pastas()
    return caminho_base(base_key).exists()


def ler_bytes_base(base_key: str) -> bytes:
    """Lê o conteúdo binário (.xlsx) salvo em disco para a base."""
    return caminho_base(base_key).read_bytes()


def info_base(base_key: str) -> tuple[str | None, str | None]:
    """Retorna (nome_original_do_arquivo, horario_iso) salvos no metadata.json,
    ou (None, None) se a base nunca foi salva."""
    meta = _ler_metadata()
    entrada = meta.get(base_key, {})
    return entrada.get("filename"), entrada.get("loaded_at")


def salvar_base(base_key: str, conteudo: bytes, nome_original: str) -> None:
    """Salva (ou substitui) uma base no disco.

    Se já existir uma versão anterior, ela é copiada para `_backup/` com
    timestamp antes de ser sobrescrita — nunca apaga dados sem guardar
    uma cópia de segurança primeiro.
    """
    _garantir_pastas()
    destino = caminho_base(base_key)

    if destino.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"{base_key}_{timestamp}.xlsx"
        shutil.copy2(destino, backup_path)
        _limpar_backups_antigos(base_key)

    destino.write_bytes(conteudo)

    meta = _ler_metadata()
    meta[base_key] = {
        "filename": nome_original,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    }
    _salvar_metadata(meta)


def remover_base(base_key: str) -> None:
    """Remove a base do disco (sem backup) — usado apenas em reset total."""
    destino = caminho_base(base_key)
    if destino.exists():
        destino.unlink()
    meta = _ler_metadata()
    meta.pop(base_key, None)
    _salvar_metadata(meta)


def _limpar_backups_antigos(base_key: str) -> None:
    """Mantém apenas os `_MAX_BACKUPS` backups mais recentes desta base."""
    backups = sorted(
        BACKUP_DIR.glob(f"{base_key}_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for antigo in backups[_MAX_BACKUPS:]:
        antigo.unlink(missing_ok=True)


def listar_backups(base_key: str) -> list[Path]:
    """Lista os backups existentes de uma base, do mais recente para o mais antigo."""
    return sorted(
        BACKUP_DIR.glob(f"{base_key}_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
