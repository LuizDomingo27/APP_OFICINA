"""Carregamento e normalização da planilha de acompanhamento.

Lógica de negócio específica:
  - Filtro: apenas linhas com SITUACAO igual a "Costura" (após normalização).
  - Ajuste de data: Qualquer ano 2025 na coluna DEADLINE é alterado para o ano atual.
  - Coluna de filtro temporal primário: ENVIO.
  - Coluna RECEBIMENTO: contém datas misturadas com textos de status (ex.:
    "À programar", "Almoxarifado"). Apenas os valores que são datas válidas
    são mantidos (convertidos para datetime); textos tornam-se NaT e não são
    removidos da base — eles apenas não entram nas visões baseadas em
    Recebimento.
"""

from io import BytesIO
import pandas as pd
import streamlit as st

class AcompanhamentoLoadError(Exception):
    """Erro amigável para falhas no carregamento do acompanhamento."""

# Colunas que o app de fato usa (ver page.py). A planilha real chega com
# ~30 colunas extras de uso interno da operação (nomes com acento,
# duplicados como "OM_1"/"OM_2", colunas 100% vazias) que não servem pra
# nada aqui. Persistir só estas no banco evita carregar lixo no esquema
# do SQLite — e evita o problema observado no round-trip: uma coluna
# float 100% vazia volta do SQLite como `object` (None) em vez de
# `float64` (NaN), porque uma coluna sem nenhum valor não-nulo não tem
# "type affinity" alguma para o SQLite inferir.
CANONICAL_COLUMNS = (
    "ENVIO", "MP", "PDV", "OFICINA", "DEPARTAMENTO", "PECAS", "MINUTOS",
    "OM", "SITUACAO", "DEADLINE", "RECEBIMENTO",
    "DIA", "SEMANA", "ANO", "SEMANA_STR", "MES_STR",
)


def select_canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém só as colunas de `CANONICAL_COLUMNS` — chamar antes de
    `sql_store.substituir_tabela`, nunca antes de devolver o dataframe
    pra tela (a UI pode querer olhar outras colunas da planilha original)."""
    cols = [c for c in CANONICAL_COLUMNS if c in df.columns]
    return df[cols].copy()

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas para mapear variações comuns para nomes padrão.
    Evita duplicatas renomeando-as com sufixo numérico.
    """
    df = df.copy()
    mapping = {}
    for col in df.columns:
        col_clean = ''.join(c for c in str(col).lower() if c.isalnum())
        
        # Mapeamentos mais restritos para evitar falsos positivos
        if col_clean in ['situacao', 'situação', 'situac', 'situa']:
            mapping[col] = 'SITUACAO'
        elif col_clean in ['deadline', 'dead']:
            mapping[col] = 'DEADLINE'
        elif col_clean in ['envio', 'dataenvio']:
            mapping[col] = 'ENVIO'
        elif col_clean in ['mp', 'materiaprima', 'materia']:
            mapping[col] = 'MP'
        elif col_clean in ['oficina', 'oficinas']:
            mapping[col] = 'OFICINA'
        elif col_clean in ['departamento', 'depto', 'dept']:
            mapping[col] = 'DEPARTAMENTO'
        elif col_clean in ['pdv']:
            mapping[col] = 'PDV'
        elif col_clean in ['pecas', 'peças', 'qtd', 'quantidade', 'realcortado']:
            mapping[col] = 'PECAS'
        elif col_clean in ['minutos', 'minuto', 'min']:
            mapping[col] = 'MINUTOS'
        elif col_clean in ['recebimento', 'datarecebimento']:
            mapping[col] = 'RECEBIMENTO'
        elif col_clean == 'om' or 'ordem' in col_clean or 'mestre' in col_clean or 'orde' in col_clean or 'omnum' in col_clean:
            mapping[col] = 'OM'
            
    df = df.rename(columns=mapping)
    
    # Deduplicar colunas renomeadas para evitar que retornem DataFrame em vez de Series
    cols = df.columns.tolist()
    seen = {}
    for idx, c in enumerate(cols):
        if c in ['SITUACAO', 'DEADLINE', 'ENVIO', 'MP', 'OFICINA', 'DEPARTAMENTO', 'PDV', 'PECAS', 'MINUTOS', 'OM', 'RECEBIMENTO']:
            if c in seen:
                seen[c] += 1
                cols[idx] = f"{c}_{seen[c]}"
            else:
                seen[c] = 0
    df.columns = cols
    return df

@st.cache_data(show_spinner="Processando planilha de acompanhamento...")
def load_acompanhamento(file_bytes: bytes) -> pd.DataFrame:
    """Carrega, limpa e normaliza a planilha de acompanhamento a partir de bytes."""
    try:
        df = pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise AcompanhamentoLoadError(
            f"Não foi possível ler a planilha de acompanhamento. Detalhe técnico: {exc}"
        )
    return _normalize_acompanhamento(df)


def _normalize_acompanhamento(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica toda a limpeza/normalização de negócio a um DataFrame já lido
    (de Excel OU de SQLite). Função pura, sem I/O e sem `st.cache_data` —
    por isso pode ser chamada tanto por `load_acompanhamento` (upload)
    quanto por `load_from_db` (leitura do banco) e por scripts de seed
    fora do Streamlit.
    """
    df = df.copy()

    # Normaliza colunas
    df = normalize_column_names(df)

    # Validação de colunas necessárias
    required = {'SITUACAO', 'DEADLINE', 'ENVIO', 'MP', 'OFICINA', 'DEPARTAMENTO', 'PDV', 'PECAS', 'MINUTOS'}
    missing = required - set(df.columns)
    if missing:
        raise AcompanhamentoLoadError(
            f"A planilha de acompanhamento está sem as colunas obrigatórias: {', '.join(sorted(missing))}. "
            f"Colunas identificadas na planilha: {', '.join(df.columns.tolist())}"
        )

    # 1. Filtro: SITUACAO igual a "Costura" (case-insensitive, strip)
    df['SITUACAO'] = df['SITUACAO'].fillna('').astype(str).str.strip()
    df = df[df['SITUACAO'].str.lower() == 'costura'].copy()

    if df.empty:
        raise AcompanhamentoLoadError(
            "Nenhuma linha com a situação 'Costura' foi encontrada na planilha de acompanhamento."
        )

    # 2. Tratamento da coluna DEADLINE (ano 2025 -> ano atual)
    df['DEADLINE'] = pd.to_datetime(df['DEADLINE'], errors='coerce')
    current_year = pd.Timestamp.now().year
    
    # Substituição segura
    def replace_year_2025(val):
        if pd.notna(val) and val.year == 2025:
            try:
                return val.replace(year=current_year)
            except ValueError:
                # Trata anos bissextos se aplicável
                return val.replace(year=current_year, day=28)
        return val

    df['DEADLINE'] = df['DEADLINE'].apply(replace_year_2025)

    # 3. Tratamento da coluna ENVIO (data primária para filtros)
    df['ENVIO'] = pd.to_datetime(df['ENVIO'], errors='coerce')
    df = df.dropna(subset=['ENVIO']).reset_index(drop=True)

    if df.empty:
        raise AcompanhamentoLoadError(
            "Nenhuma linha com data de ENVIO válida foi encontrada após os filtros."
        )

    # 4. Tratamento da coluna RECEBIMENTO (mistura datas com textos de status)
    # Mantém apenas os valores que são datas válidas; textos (ex.: "À programar",
    # "Almoxarifado") tornam-se NaT. Nenhuma linha é descartada aqui — o filtro
    # de "apenas datas" é aplicado na própria coluna, e cada tela decide se
    # quer considerar só as linhas com RECEBIMENTO preenchido.
    if 'RECEBIMENTO' in df.columns:
        df['RECEBIMENTO'] = pd.to_datetime(df['RECEBIMENTO'], errors='coerce')
    else:
        df['RECEBIMENTO'] = pd.NaT

    # Normalização de tipos e preenchimento de vazios
    df['MP'] = df['MP'].fillna('SEM MP').astype(str).str.strip().str.upper()
    df['OFICINA'] = df['OFICINA'].fillna('SEM OFICINA').astype(str).str.strip()
    df['DEPARTAMENTO'] = df['DEPARTAMENTO'].fillna('SEM DEPARTAMENTO').astype(str).str.strip()
    df['PDV'] = df['PDV'].fillna('SEM PDV').astype(str).str.strip()
    
    if 'OM' in df.columns:
        df['OM'] = df['OM'].fillna('').astype(str).str.strip()
    else:
        df['OM'] = 'N/A'

    df['PECAS'] = pd.to_numeric(df['PECAS'], errors='coerce').fillna(0).astype(float)
    df['MINUTOS'] = pd.to_numeric(df['MINUTOS'], errors='coerce').fillna(0).astype(float)

    # Colunas de Agrupamento Temporal
    df['DIA'] = df['ENVIO'].dt.date
    df['SEMANA'] = df['ENVIO'].dt.isocalendar().week.astype(int)
    df['ANO'] = df['ENVIO'].dt.isocalendar().year.astype(int)
    # Formato AAAA-WSS (ex: 2026-W25)
    df['SEMANA_STR'] = df['ANO'].astype(str) + "-W" + df['SEMANA'].astype(str).str.zfill(2)
    # Formato AAAA-MM (ex: 2026-06)
    df['MES_STR'] = df['ENVIO'].dt.to_period('M').astype(str)

    return df


@st.cache_data(show_spinner="Carregando Acompanhamento do banco...")
def load_from_db() -> pd.DataFrame:
    """Lê a tabela 'acompanhamento' já normalizada do SQLite (`app.db`).

    `_normalize_acompanhamento` é idempotente (filtro de SITUACAO, ajuste
    de ano da DEADLINE, recomputo de DIA/SEMANA/ANO a partir de ENVIO —
    tudo reaplicável sobre dados já normalizados sem mudar o resultado),
    então reusá-la aqui evita duplicar a lógica de negócio entre o
    caminho "vindo de upload" e o caminho "vindo do banco". Isso também
    resolve de quebra a reconversão de tipos: o SQLite devolve
    ENVIO/DEADLINE/RECEBIMENTO como texto, e `_normalize_acompanhamento`
    já faz `pd.to_datetime` sobre essas colunas.

    Invalidação: depois de uma substituição de base bem-sucedida (tela
    "Atualizar Bases"), o código chama `load_from_db.clear()`.
    """
    from src.shared import sql_store

    df_bruto = sql_store.carregar_tabela("acompanhamento")
    return _normalize_acompanhamento(df_bruto)
