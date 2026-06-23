# Sistema Unificado — Envio & Recebimento

Unificação dos projetos `APP_ENVIO` e `APP_RECEBIMENTO` em um único app
Streamlit, cada um mantido como camada independente em `src/`.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fluxo de uso

1. A tela inicial (`src/shared/home.py`) exige o upload das **3** planilhas
   (Envio, Recebimento e Acompanhamento) — só na primeira vez. Cada uma é
   validada na hora (colunas obrigatórias, datas, etc.) e o erro aparece
   embaixo do uploader correspondente.
2. Só quando **as três** bases estiverem válidas, aparecem os 3 cards de
   navegação: **Abrir Painel de Envios**, **Abrir Painel de Recebimento**
   e **Abrir Acompanhamento Oficina**.
3. Dentro de cada painel há um botão **"🏠 Início — trocar bases"** na
   sidebar — ele reseta a SESSÃO (não o banco) e volta para a tela inicial.
4. Para substituir uma base já carregada (planilha nova de produção), use a
   tela **"⚙️ Atualizar Bases"** — é o único lugar onde uma substituição
   de verdade acontece, e só depois de clicar em "Salvar e Substituir".
5. A base de **Detalhe do Recebimento** (planilha STATUS.xlsx) é
   **opcional** e não faz parte do upload inicial: ela é enviada a
   qualquer momento pela própria tela "⚙️ Atualizar Bases", liberando o
   painel **"🧾 Detalhe do Recebimento"** na navegação.

**Persistência:** as 3 bases obrigatórias (+ a base opcional de Detalhe do
Recebimento, quando enviada) ficam salvas em `database/app.db` (SQLite,
ver `src/shared/sql_store.py`). Ao reabrir o app numa sessão nova, as
bases já carregam automaticamente — sem precisar reenviar os `.xlsx`.
Antes de qualquer substituição, o `.db` inteiro é copiado para
`database/_backup/` como rede de segurança.

## Arquitetura

```
app.py                      → entrypoint / router (home | envio | recebimento | acompanhamento | detalhe_recebimento | gerenciar_bases)
src/
├── shared/
│   ├── state.py             → estado de sessão (view atual, bases carregadas, reset)
│   ├── home.py               → tela inicial: upload + validação + cards de navegação
│   ├── manage_bases.py       → tela "⚙️ Atualizar Bases" (substituição explícita de uma base)
│   ├── sql_store.py          → persistência em SQLite (database/app.db) — usada por todas as bases
│   └── database.py           → legado (.xlsx); hoje só `info_base()` ainda é usada (metadata compartilhada)
├── envio/                    → camada do projeto APP_ENVIO
│   ├── config/                 settings.py, theme.py
│   ├── data/                   loader.py (lê bytes de upload OU `load_from_db()` do SQLite), filters.py, metrics.py
│   ├── charts/                  builders.py, theme.py
│   ├── ui/                      sidebar.py, dashboard.py, components.py, styles.py
│   ├── utils/                   excel_export.py, formatters.py
│   └── page.py                  ponto de entrada da página (chamado pelo router)
├── recebimento/               → camada do projeto APP_RECEBIMENTO
│   ├── config.py
│   ├── data_loader.py           (lê bytes de upload OU `load_from_db()` do SQLite)
│   ├── metrics.py / charts.py
│   ├── ui/                      cards.py, filters.py, goal.py
│   └── page.py                  ponto de entrada da página (chamado pelo router)
├── acompanhamento/            → painel de acompanhamento de oficina (filtro "Costura")
│   ├── loader.py                normalização + `load_from_db()` do SQLite
│   └── page.py                  ponto de entrada da página (chamado pelo router)
└── detalhe_recebimento/       → painel "🧾 Detalhe do Recebimento" (planilha STATUS.xlsx) — base OPCIONAL
    ├── config.py                 colunas + paleta de cores
    ├── data_loader.py            normalização + `load_from_db()` do SQLite (tabela `detalhe_recebimento`)
    ├── metrics.py                 totais por operação / detalhamento por Operação+MP+Oficina
    ├── pdf_export.py              geração do PDF executivo (reportlab)
    ├── ui/                        cards.py, filters.py
    └── page.py                    ponto de entrada da página (chamado pelo router)
```

## Migração de Excel para SQLite

As 3 bases originais foram migradas de planilhas `.xlsx` em disco para
SQLite (`database/app.db`). Os `.xlsx` antigos (`database/envio.xlsx`,
`database/recebimento.xlsx`, `database/acompanhamento.xlsx`) continuam no
disco como cópia de segurança, mas não são mais lidos pelo app — só pelos
scripts de migração única (`scripts/seed_envio.py`,
`scripts/seed_recebimento.py`, `scripts/seed_acompanhamento.py`), que já
foram executados e não precisam rodar de novo em condições normais.

A base de **Detalhe do Recebimento** (planilha STATUS.xlsx) já nasceu
direto em SQLite (tabela `detalhe_recebimento`) — não existe versão
legada em `.xlsx` fixo. O script `scripts/seed_detalhe_recebimento.py`
existe só como atalho de linha de comando para quem preferir popular a
tabela sem passar pela tela "⚙️ Atualizar Bases":

```bash
python scripts/seed_detalhe_recebimento.py /caminho/para/STATUS.xlsx
```

Detalhes de implementação (estratégia de troca atômica de tabela, cuidado
com WAL no backup, etc.) estão documentados nos comentários de
`src/shared/sql_store.py`.

## Painel "🧾 Detalhe do Recebimento"

Painel dedicado à planilha STATUS.xlsx — a coluna `RECEBIMENTO` traz o
status/operação de cada ordem em aberto (ex.: "Agua. Reposição",
"Coletando datas", "Procurando" etc.).

- **Cards de indicadores**: total de peças e minutos por operação (um
  card por status), além de um resumo geral do período filtrado.
- **Tabela de detalhamento**: mesmos totais agrupados por
  Operação + MP + Oficina, no mesmo layout (`.custom-table`) usado nos
  demais painéis.
- **Exportação em PDF**: botão abaixo da tabela gera um PDF executivo
  (`src/detalhe_recebimento/pdf_export.py`, via `reportlab`) com o mesmo
  padrão de cor/tabela do app — cabeçalho repetido em todas as páginas,
  linha de total e paginação automática.
- **Filtros**: período com base na coluna `ENVIO` (conforme pedido), e
  filtros adicionais por Operação, MP e Oficina, seguindo o mesmo padrão
  de filtros das demais telas.

Essa base é a única **opcional** do app: sem ela, os outros 4 painéis
funcionam normalmente, e o próprio painel exibe uma orientação para
enviar a planilha pela tela "⚙️ Atualizar Bases" em vez de quebrar.

## O que mudou em relação aos projetos originais

- **`src/envio/data/loader.py`**: removido o cache em disco (`.cache/data/*.parquet`)
  e o fallback de arquivo padrão (`ENVIOS_OFICINAS.xlsx`). Agora só lê bytes
  de upload, com cache em memória via `st.cache_data`.
- **`src/recebimento/data_loader.py`**: removida a leitura de caminho fixo
  (`data/RECEBIMENTO.xlsx`). Agora também só lê bytes de upload.
- Toda regra de negócio, cálculo de métricas, gráficos ECharts e estilo
  visual (tema verde água) foram preservados exatamente como nos projetos
  originais — só a camada de **entrada de dados** e **navegação** mudou.

## Atenção (ambiente)

`streamlit-echarts` tem quebrado compatibilidade em versões recentes do
`streamlit` (>=1.5x mudou a API de componentes). Por isso o
`requirements.txt` já está com versões **travadas** (`==`), não `>=`:
`streamlit==1.38.0` e `streamlit-echarts==0.4.0` — testadas e funcionando.
Não atualize essas duas libs sem testar antes em outro ambiente.
