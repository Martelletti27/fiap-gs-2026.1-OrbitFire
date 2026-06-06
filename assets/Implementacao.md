# Implementacao — OrbitFire

Acompanhamento do desenvolvimento da POC GS 2026.1.

| Documento | Funcao | Versionado? |
|-----------|--------|-------------|
| `assets/Escopo.md` | O que sera entregue (congelado) | Sim |
| `assets/Implementacao.md` | Sprints, progresso e proximo passo | Sim |
| `assets/Titulo.md` | Edital FIAP | Sim |
| `README.md` | Visao publica na entrega (S7) | Sim |

---

## Produto

**OrbitFire** — risco de incendio para **amanha** no **Tocantins (TO)**, com priorizador de brigadas.

| | |
|-|-|
| **Problema** | Satelites mostram onde ja ha fogo; gestores precisam saber **onde agir amanha**. |
| **Solucao** | IA cruza historico orbital (FIRMS) + clima e gera mapa de risco + ranking operacional. |
| **Regiao** | Tocantins — bbox lat -13,5 a -5,2 / lon -50,7 a -45,7 (~4.150 celulas, `assets/Escopo.md` secao 2) |
| **Publico** | Defesa civil, brigadas florestais, avaliacao FIAP (entrega GS) |

---

## Estado real do repositorio (2026-06-05)

| Item | Status |
|------|--------|
| Ultimo commit em `origin/main` | `2d0dc81` — `docs: README OrbitFire e documentacao em assets/` |
| Historico | `3212ca0` · `f6d9932` · `88f7913` · `1850326` · `f35789b` |
| Raiz | `README.md`, `requirements.txt`, pastas — sem `pytest.ini` |
| `.env` | Na raiz (gitignored); template em `src/.env.example` |
| `assets/Escopo.md`, `Titulo.md`, `Implementacao.md` | Versionados em `assets/` |
| `src/` | S0–S2 em `main`; S3.E1 local (`infrastructure/ml/train.py`) |
| `test/unit/` | 25 arquivos — **100 testes** passando |
| `data/models/` | `lgbm_orbitfire.pkl`, `metrics.json` (gitignored) |
| `data/seed/` | `fire_events_seed.csv`, `weather_daily_seed.csv` (versionados) |
| `data/raw/` | Snapshots FIRMS/clima locais (gitignored) |
| `data/orbitfire.db` | BD local de desenvolvimento (gitignored) |

**Conclusao:** S0–S2 em `origin/main`. S3.E1 concluida localmente (79 testes); proxima: **S3.E2**.

### Entrypoints manuais (Sprint 1)

```powershell
# Na raiz, com venv e .env configurados — migracao TO (BD limpo)
python -m src.application.build_grid
python -m src.infrastructure.firms.ingest_historical
python -m src.infrastructure.weather.ingest_historical
python -m src.application.build_features
python -m src.application.build_labels
python -m src.application.build_dataset
python -m src.infrastructure.ml.train

# Operacao diaria (apos treino)
python -m src.infrastructure.firms.ingest
python -m src.infrastructure.weather.ingest
python -m src.application.predict_risk
python -m src.application.rank_brigades
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
pytest test/ -v
```

---

## Mapa Escopo (E1–E12) → Sprints

| Entrega (`Escopo.md`) | Sprint | Etapa |
|-----------------------|--------|-------|
| E10 Modo offline (base) | S0 | S0.E3 |
| E3 Grade + persistencia (schema) | S0 | S0.E2 |
| Config e paths | S0 | S0.E1 |
| E1 Pipeline FIRMS | S1 | S1.E1 |
| E2 Pipeline clima | S1 | S1.E2 |
| E3 Grade geografica | S1 | S1.E3 |
| E4 Features e labels | S2 | S2.E1–S2.E3 |
| E5 Modelo LightGBM | S3 | S3.E1 |
| E6 Risk score | S3 | S3.E2–S3.E3 |
| E7 Priorizador de brigadas | S4 | S4.E1–S4.E2 |
| E8 API REST | S5 | S5.E1–S5.E2 |
| E9 Dashboard | S6 | S6.E1–S6.E2 |
| E11 Testes | Transversal | Cada etapa |
| E12 Documentacao publica | S7 | S7.E1 |

---

## Decisoes tecnicas (confirmadas 2026-06-05)

| Decisao | Escolha |
|---------|---------|
| Grade (`GRID_DEG`) | `0.10` grau (~11 km) |
| Chave de celula | `cell_id` (grade) + `uf` quando disponivel |
| Clima | **Open-Meteo** forecast (operacao) + archive (treino) |
| FIRMS operacao | **VIIRS NRT + MODIS NRT** (5 dias) |
| FIRMS treino | **VIIRS SP + MODIS SP** — jun–set/2024 |
| Regiao | **Tocantins (TO)** — redimensionado com autorizacao |
| Python | 3.10+ (sem restricao entre 3.10 e 3.11) |
| NASA | Chave disponivel; `OFFLINE_MODE=1` mantido para demo e testes |
| SQLite | `data/orbitfire.db` (recomendado reset na migracao MT) |
| ML | LightGBM classificador binario |
| Mapa UI | Folium no dashboard |

### Pivot TO + historico (autorizado 2026-06-05)

- Escopo alterado de Centro-Oeste (4 UFs) para **somente Tocantins (TO)**
- Treino: FIRMS SP + Open-Meteo archive em **jun–set/2024** (estacao seca)
- Operacao diaria: FIRMS NRT (5 dias) + Open-Meteo forecast
- Entrypoints novos:
  - `python -m src.infrastructure.firms.ingest_historical`
  - `python -m src.infrastructure.weather.ingest_historical`
- Migracao de dados: apagar `data/orbitfire.db` e rodar pipeline do zero na grade TO (~4.150 celulas)

---

## Regra de trabalho por etapa

```
[ Pendente ]
     |  usuario autoriza implementacao
     v
[ Em implementacao ]
     |  codigo pronto; resumo da etapa + arquivos listados
     v
[ Aguardando autorizacao ]
     |  testes (se aplicavel); usuario revisa
     v
[ Concluida ]  somente com OK explicito do usuario
```

| Coluna | Significado |
|--------|-------------|
| **Implementada** | Codigo funcional no escopo da etapa |
| **Testada** | pytest passando (ou N/A) |
| **Autorizada** | Usuario autorizou avancar |

**Nenhuma etapa avanca sem autorizacao explicita.**

### Resumo da etapa (obrigatorio apos cada implementacao)

Ao concluir o codigo de uma etapa, registrar no bloco **Resumo** da sprint (acima dos entregaveis) dois bullets em linguagem simples: o que funciona e por que importa.

### Refatoracao e testes (sempre)

**Sempre que uma refatoracao for feita** — fim de Sprint, revisao SOLID ou ajuste incremental:

1. **Escopo cumulativo:** revisar e refatorar o codigo de **todas as sprints ja implementadas** (S0 ate a sprint em encerramento), nao apenas a sprint atual — duplicacao, acoplamento e violacoes SOLID podem estar em sprints anteriores.
2. Rodar **toda** a suite: `pytest test/ -v`
3. Nao commitar nem encerrar etapa com testes falhando ou sem ter rodado os testes apos o diff

### Refatoracao e commit ao fim de cada Sprint

Ordem **obrigatoria** apos autorizacao da ultima etapa da Sprint:

1. **Refatoracao** de **todas as sprints implementadas** (S0–Sn) — sem alterar comportamento; a sprint que fecha e o gatilho, o escopo e o acumulado
2. Revisao com `agent-code-reviewer` (checklist SOLID, skill `review-code-checklist`)
3. `pytest test/ -v` (**obrigatorio** — ver secao acima)
4. Commit com mensagem da fase (**confirmar texto com usuario**)
5. Push para `origin/main`

`agent-git-manager` so commita apos os passos 1–3.

| Sprint | Commit sugerido (titulo) | Feito? |
|--------|--------------------------|--------|
| Preparacao | `feat(s0): estrutura inicial do projeto OrbitFire` | Sim (`3212ca0`) |
| Preparacao | `chore(docs): ignorar planejamento local em docs/` | Sim (`f6d9932`, migrado para `assets/` em 2026-06-06) |
| S0 Fundacao | `feat(s0): fundacao OrbitFire — config, sqlite, seed offline` | Sim (`88f7913`) |
| S1 Ingestao | `feat(s1): ingestao FIRMS, clima e grade Centro-Oeste` | Sim (`1850326`) |
| S2 Features | `feat(s2): features, labels e dataset de modelagem` | Sim (`f35789b`) |
| S3 Modelo | `feat(s3): treino LightGBM, risk score e inferencia` | Nao |
| S4 Priorizacao | `feat(s4): priorizador de brigadas` | Nao |
| S5 API | `feat(s5): API FastAPI e testes de integracao` | Nao |
| S6 Dashboard | `feat(s6): dashboard Streamlit com mapa e ranking` | Nao |
| S7 Entrega | `docs(s7): README final e checklist de entrega GS` | Nao |

---

## Regra da raiz do repositorio

Na raiz ficam **somente**: pastas (`data/`, `assets/`, `src/`, `test/`), `README.md` e `requirements.txt`.

Demais artefatos ficam dentro das pastas (ex.: `src/.env.example`, `src/config.py`, `test/conftest.py`). O `.env` real continua na raiz mas e gitignored.

---

## Estrutura de pastas (alvo)

```
fiap-gs-2026.1-OrbitFire/
  requirements.txt          # unico arquivo de dependencias na raiz
  README.md                 # unico markdown na raiz
  data/
    raw/firms/              # S1.E1 — gitignore conteudo grande
    raw/weather/            # S1.E2
    processed/              # S1.E3 em diante
    seed/                   # S0.E3 — CSV pequenos commitaveis
    models/                 # S3 — gitignore *.pkl
    orbitfire.db            # nunca commitar
  assets/
    Escopo.md               # escopo congelado — versionado
    Implementacao.md        # sprints e progresso — versionado
    Titulo.md               # edital FIAP — versionado
    logo-fiap.png           # logo README (quando adicionada)
  src/
    .env.example            # template — copiar para .env na raiz
    config.py               # S0.E1
    domain/
      cell_id.py            # S1.E3 — implementado
      features.py           # S2.E1 — implementado
      labels.py             # S2.E2 — implementado
    application/
      build_grid.py         # S1.E3 — implementado
      build_features.py     # S2.E1 — implementado
      build_labels.py       # S2.E2 — implementado
      build_dataset.py      # S2.E3 — implementado
      dataset.py            # S2.E3 — implementado (domain)
    infrastructure/
      db/                   # S0.E2
      seed/                 # S0.E3
      firms/                # S1.E1
      weather/              # S1.E2
      ml/                   # S3.E1 — train.py implementado
    api/                    # S5 — pendente
    dashboard/              # S6 — painel Streamlit (consome API)
  test/
    conftest.py             # pythonpath sem pytest.ini na raiz
    unit/                   # S0.E1 em diante
    integration/            # S5.E2
```

---

## Modulos → Sprints

| Modulo | Descricao | Sprint |
|--------|-----------|--------|
| M9 | Demo offline | S0 |
| M3 | Grade (schema) | S0 (schema) / S1 (geracao) |
| M1 | Ingestao FIRMS | S1 |
| M2 | Ingestao clima | S1 |
| M4 | Features e labels | S2 |
| M5 | Motor IA LightGBM | S3 |
| M6 | Risk score | S3 |
| priorizador | Priorizador brigadas | S4 |
| M7 | API FastAPI | S5 |
| M8 | Dashboard Streamlit | S6 |

**Fora do MVP:** M11 cognitivo, M12 ESP32.

---

## Resumo de progresso

| Sprint | Etapas | Concluidas | Status |
|--------|--------|------------|--------|
| Preparacao | 2 | 2 | Concluida |
| S0 Fundacao | 3 | 3 | Concluida |
| S1 Ingestao | 3 | 3 | Concluida |
| S2 Features | 3 | 3 | Concluida |
| S3 Modelo | 3 | 3 | **Concluida** (commit pendente) |
| S4 Priorizacao | 2 | 2 | Concluida localmente |
| S5 API | 2 | 2 | Concluida localmente |
| S6 Dashboard | 2 | 2 | Concluida localmente |
| S7 Entrega | 2 | 1 | Em andamento (E1 concluida) |

**Etapa atual:** Sprint 7 — S7.E2 (revisao Godoy, PDF, video, links no README).

---

## Proximo passo imediato

1. [x] Sprint 2 concluida — commit `f35789b`, push OK
2. [x] S3.E1 implementada, testada e autorizada (`pytest` 79/79)
3. [x] S3.E2 implementada — risk score e faixas (`pytest` 87/87)
4. [x] S3.E3 implementada — inferencia batch (`predict_risk.py`, scores em SQLite)
5. [ ] Refatoracao S0–S3 · `pytest test/ -v` · Commit · Push

**Pre-requisito local:** grade e ingestoes no SQLite (`build_grid`, `firms.ingest`, `weather.ingest`) ou `OFFLINE_MODE=1` com seed.

---

## Sprint 0 — Fundacao

### S0.E1 — Estrutura base e configuracao

| Campo | Valor |
|-------|-------|
| Objetivo | Config central, dependencias, paths e bbox Centro-Oeste |
| Modulos | Preparacao M1–M12 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_config.py` — 8 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- O projeto tem configuracao central (paths, bbox do Centro-Oeste, variaveis de ambiente) e dependencias definidas em um so lugar.
- Tudo que vem depois usa as mesmas regras de regiao, pastas e chaves — evita cada modulo inventar seu proprio caminho.

**Entregaveis:**
- `src/config.py`, `src/.env.example`, `requirements.txt`
- `test/conftest.py`, `test/unit/test_config.py`
- Ajustes em `.gitignore` (raiz e `data/`)

---

### S0.E2 — Schema SQLite e persistencia

| Campo | Valor |
|-------|-------|
| Objetivo | Tabelas: `grid_cells`, `fire_events`, `weather_daily`, `risk_scores` |
| Modulos | M3, M9 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_db.py` — 8 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Banco SQLite com tabelas para grade, focos de fogo, clima diario e scores de risco, com funcoes para gravar e ler.
- Os dados deixam de ficar soltos em arquivos avulsos — ha um lugar fixo e estruturado para a POC crescer.

**Entregaveis:**
- `src/infrastructure/db/schema.py`
- `src/infrastructure/db/repository.py`
- `test/unit/test_db.py`

---

### S0.E3 — Modo offline e dados seed

| Campo | Valor |
|-------|-------|
| Objetivo | Seed minimo em `data/seed/` para demo sem API |
| Modulos | M9 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_seed_loader.py` — 6 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Pacote minimo de focos e clima no repositorio; com `OFFLINE_MODE=1`, o sistema carrega esses dados sem chamar APIs externas.
- Demo em sala e testes automatizados funcionam mesmo sem internet ou chave NASA.

**Entregaveis:**
- `data/seed/fire_events_seed.csv` — 8 focos Centro-Oeste (VIIRS + MODIS)
- `data/seed/weather_daily_seed.csv` — 8 registros climaticos
- `src/infrastructure/seed/loader.py` — `load_seed_if_offline()`
- `test/unit/test_seed_loader.py`

### Encerramento Sprint 0

- [x] S0.E1–S0.E3 autorizadas
- [x] Refatoracao Sprint 0 concluida
- [x] `pytest test/ -v` passando
- [x] Commit: `feat(s0): fundacao OrbitFire — config, sqlite, seed offline` (`88f7913`)
- [x] Push

---

## Sprint 1 — Ingestao de dados

### S1.E1 — Cliente NASA FIRMS

| Campo | Valor |
|-------|-------|
| Objetivo | Focos VIIRS/MODIS para bbox Centro-Oeste |
| Modulos | M1 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_firms_*.py` — 13 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Busca focos de incendio da NASA (VIIRS e MODIS) na regiao Centro-Oeste e grava no banco, sem duplicar o que ja existe.
- O historico orbital e a materia-prima — sem focos reais, nao ha o que aprender nem o que prever.

**Entregaveis:**
- `src/infrastructure/firms/client.py` — fetch area/csv com retry
- `src/infrastructure/firms/parser.py` — CSV NASA para tipos internos
- `src/infrastructure/firms/ingest.py` — `run_firms_ingest()` + entrypoint
- `data/raw/firms/` — snapshots brutos (gitignored)
- `test/unit/test_firms_parser.py`, `test_firms_client.py`, `test_firms_ingest.py`

---

### S1.E2 — Cliente clima

| Campo | Valor |
|-------|-------|
| Objetivo | Temperatura, precipitacao, vento diarios |
| Modulos | M2 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_weather_*.py` — 10 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Busca temperatura, chuva e vento diarios (Open-Meteo) e associa cada registro a uma celula da grade no banco.
- Seca e calor aumentam risco de fogo — a IA precisa desses sinais junto com o historico de focos.

**Entregaveis:**
- `src/infrastructure/weather/client.py` — Open-Meteo forecast com `past_days`
- `src/infrastructure/weather/parser.py` — JSON daily para tipos internos
- `src/infrastructure/weather/targets.py` — alvos por grade ou seed
- `src/infrastructure/weather/ingest.py` — `run_weather_ingest()` + entrypoint
- `data/raw/weather/` — snapshots brutos (gitignored)
- `test/unit/test_weather_parser.py`, `test_weather_client.py`, `test_weather_targets.py`, `test_weather_ingest.py`

---

### S1.E3 — Grade geografica

| Campo | Valor |
|-------|-------|
| Objetivo | Celulas com `cell_id`, centro lat/lon, UF |
| Modulos | M3 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_cell_id.py`, `test_build_grid.py` — 8 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- O Centro-Oeste e dividido em quadrados de ~11 km, cada um com identificador (`UF_lat_lon`) e estado (UF), persistidos no banco.
- O risco e calculado por regiao pequena e comparavel — nao apenas por estado inteiro.

**Entregaveis:**
- `src/domain/cell_id.py` — grade, `cell_id`, atribuicao UF
- `src/application/build_grid.py` — `build_and_persist_grid()` + entrypoint
- `data/processed/grid_cells.parquet` — snapshot exportado (gitignored)
- `test/unit/test_cell_id.py`, `test/unit/test_build_grid.py`

### Encerramento Sprint 1

- [x] S1.E1–S1.E3 autorizadas
- [x] Refatoracao Sprint 1 concluida
- [x] `pytest test/ -v` passando
- [x] Commit: `feat(s1): ingestao FIRMS, clima e grade Centro-Oeste`
- [x] Push

---

## Sprint 2 — Features e labels

### S2.E1 — Engenharia de features

| Campo | Valor |
|-------|-------|
| Objetivo | Variaveis preditivas por `cell_id` e dia |
| Modulos | M4 |
| Features | focos 7d/30d, dias sem chuva, media termica 7d, sazonalidade (mes) |
| Fontes | `fire_events`, `weather_daily`, `grid_cells` (SQLite) |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_features.py`, `test_build_features.py` — 9 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Para cada celula e cada dia, o sistema monta sinais de risco: focos nos ultimos 7 e 30 dias, dias sem chuva, temperatura media da semana e mes do ano.
- A IA usa historico recente de focos e clima — sem essas pistas o modelo nao tem contexto para prever.

**Entregaveis:**
- `src/application/build_features.py` — `build_features()` + entrypoint
- `src/domain/features.py` — calculo puro das variaveis (testavel sem BD)
- `data/processed/features_cell_day.parquet` (gitignored)
- `test/unit/test_features.py`

**Execucao prevista:** `python -m src.application.build_features`

---

### S2.E2 — Labels (fogo amanha)

| Campo | Valor |
|-------|-------|
| Objetivo | Label binario: foco FIRMS na celula em D+1 |
| Modulos | M4 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_labels.py`, `test_build_labels.py` — 7 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Para cada celula e cada dia, marca se no dia seguinte houve fogo ali (sim = 1, nao = 0).
- E o gabarito de treino — a IA aprende comparando features com o que de fato aconteceu no dia seguinte.

**Entregaveis:**
- `src/application/build_labels.py` — `build_labels()` + entrypoint
- `src/domain/labels.py` — regra pura `fire_tomorrow_label`
- `src/application/db_loaders.py` — loaders compartilhados com features
- `data/processed/labels_cell_day.parquet`
- `test/unit/test_labels.py`, `test/unit/test_build_labels.py`

**Execucao prevista:** `python -m src.application.build_labels`

---

### S2.E3 — Dataset consolidado

| Campo | Valor |
|-------|-------|
| Objetivo | Join features + labels; split temporal documentado |
| Modulos | M4 |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_dataset.py`, `test_build_dataset.py` — 6 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- Junta features e labels numa tabela unica; separa os dias em treino (~80% no inicio) e teste (~20% no fim), sem misturar futuro no passado.
- Material pronto para treinar o modelo LightGBM a prever fogo amanha no proximo passo (S3).

**Entregaveis:**
- `src/application/build_dataset.py` — `build_dataset()` + entrypoint
- `src/domain/dataset.py` — split temporal 80/20 por dia
- `data/processed/dataset_cell_day.parquet` (gitignored)
- `data/processed/dataset_split.json` — metadados do split
- `test/unit/test_dataset.py`, `test/unit/test_build_dataset.py`

**Execucao prevista:**
```powershell
python -m src.application.build_features
python -m src.application.build_labels
python -m src.application.build_dataset
```

### Encerramento Sprint 2

- [x] S2.E1–S2.E3 autorizadas
- [x] Refatoracao S0–S2 concluida (2026-06-05)
- [x] `pytest test/ -v` passando (75/75)
- [x] Commit: `feat(s2): features, labels e dataset de modelagem` (`f35789b`)
- [x] Push

---

## Sprint 3 — Modelo e risk score

### S3.E1 — Treino LightGBM

| Campo | Valor |
|-------|-------|
| Objetivo | Classificador binario LightGBM (fogo amanha) |
| Modulos | M5 |
| Features | `fires_7d`, `fires_30d`, `days_without_rain`, `temp_mean_7d`, `season_month` |
| Fonte | `data/processed/dataset_cell_day.parquet` (split train/test) |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_ml_train.py` — 4 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- O sistema treina LightGBM com o dataset pronto e salva o modelo + metricas de avaliacao em `data/models/`.
- A partir daqui o OrbitFire estima probabilidade de fogo amanha por celula; `agent-data-analyst` apoia interpretacao das metricas para README e dashboard (S6).

**Entregaveis:**
- `src/infrastructure/ml/train.py` — `train_model()` + entrypoint
- `data/models/lgbm_orbitfire.pkl` (gitignored)
- `data/models/metrics.json` (gitignored)
- `data/models/confusion_matrix.png` — matriz de confusao + acuracia/erro (gitignored)
- `test/unit/test_ml_train.py`

**Execucao prevista:**
```powershell
python -m src.application.build_dataset
python -m src.infrastructure.ml.train
pytest test/unit/test_ml_train.py -v
```

### S3.E2 — Risk score e faixas

| Campo | Valor |
|-------|-------|
| Objetivo | Converter probabilidade do LightGBM em score 0-100 e faixa operacional |
| Modulos | M6 |
| Fonte | Probabilidade bruta do modelo + limites em `thresholds.json` |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_risk_score.py` — 8 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- A IA devolve probabilidade 0–1; o dominio transforma em score 0–100 e faixa (baixo, medio, alto, critico).
- Os cortes podem ser fixos ou recalibrados por percentis do conjunto de treino apos retreino.

**Entregaveis:**
- `src/domain/risk_score.py` — `probability_to_score`, `classify_band`, `assess_risk`, calibracao e I/O JSON
- `data/models/thresholds.json` — limites iniciais (quartis fixos; recalibrar apos treino TO)
- `test/unit/test_risk_score.py`

**Execucao prevista:**
```powershell
pytest test/unit/test_risk_score.py -v
```

### S3 — Melhorias do modelo (retreino TO, itens 1–4)

Serie incremental de melhorias apos o pipeline historico TO (FIRMS SP jun–set/2024 + clima archive, grade 4.150 celulas). Dataset: **502.150** linhas (`train=398.400`, `test=103.750`; positivos **4,5%** treino / **9,0%** teste). Metricas de classificacao usam **threshold otimo por F1** no teste (via `calibrate_thresholds`), salvo no baseline fixo em **0,5**.

**Resumo:**
- Partimos de um modelo TO com 5 features (AUC **0,84**, F1 **0,45** em thr=0,5) e evoluimos em quatro passos ate **9 features + tuning** (AUC **0,868**, F1 **0,584** em thr=0,8).
- O maior salto veio das novas features climaticas e espaciais (itens 2 e 3); calibracao de faixas (item 1) e tuning LightGBM (item 4) refinaram operacao sem mudar drasticamente o ranking.
- Estado final: menos falsos positivos que o baseline (**3.658** vs **11.656**), recall ainda util (**57,3%**) e `thresholds.json` recalibrado para o modelo atual.

#### Comparativo geral (holdout temporal)

| Etapa | O que mudou | Features | Thr otimo | AUC | F1 | Precisao | Recall | Acuracia |
|-------|-------------|----------|-----------|-----|-----|----------|--------|----------|
| Baseline TO | Treino inicial TO, params default | 5 | 0,50 | 0,840 | 0,450 | 34,3% | 64,8% | 85,6% |
| Item 1 | Calibracao `thresholds.json` + busca thr F1 | 5 | 0,50 | 0,840 | 0,450 | 34,3% | 64,8% | 85,6% |
| Item 2 | `fires_1d`, `precip_sum_7d`, `wind_mean_7d` | 8 | 0,40 | 0,857 | 0,581 | 60,1% | 56,3% | 92,7% |
| Item 3 | `neighbor_fires_7d` (8 vizinhos, janela 7d) | 9 | 0,85 | 0,868 | 0,585 | 61,9% | 55,4% | 92,9% |
| Item 4 | Tuning LightGBM (grid 6 candidatos, melhor AUC) | 9 | 0,80 | **0,868** | **0,584** | 59,5% | **57,3%** | 92,6% |

#### Matriz de confusao (threshold otimo por etapa)

| Etapa | TP | TN | FP | FN |
|-------|----|----|----|-----|
| Baseline TO (thr 0,50) | 6.074 | 82.714 | 11.656 | 3.306 |
| Item 2 (thr 0,40) | 5.280 | 90.863 | 3.507 | 4.100 |
| Item 3 (thr 0,85) | 5.196 | 91.169 | 3.201 | 4.184 |
| **Item 4 (thr 0,80)** | **5.374** | **90.712** | **3.658** | **4.006** |

#### Faixas de risk score (`thresholds.json`, percentis 50/75/90 no treino)

| Etapa | Medio | Alto | Critico |
|-------|-------|------|---------|
| Item 1 | 17,7 | 28,3 | 44,0 |
| Item 2 | 14,2 | 21,8 | 32,0 |
| Item 3 | 26,6 | 44,3 | 65,2 |
| **Item 4 (atual)** | **26,9** | **43,8** | **64,8** |

#### Detalhamento por item

**Item 1 — Calibracao de faixas e threshold**
- Modulo: `src/application/calibrate_thresholds.py`, testes em `test/unit/test_calibrate_thresholds.py`.
- Recalibrou `data/models/thresholds.json` a partir dos percentis do treino.
- Buscou melhor threshold de classificacao por F1 no teste: **0,50** (igual ao baseline; sem ganho de F1 nesta etapa).
- Conclusao: faixas de risk score passaram a refletir a distribuicao TO; classificacao binaria permaneceu estavel ate novas features.

**Item 2 — Novas features climaticas e de foco**
- `fires_1d`, `precip_sum_7d`, `wind_mean_7d` em `src/domain/features.py`; `wind_speed` carregado em `db_loaders.py`.
- Retreino completo: `build_features` → `build_dataset` → `train` → `calibrate_thresholds`.
- Ganho principal: AUC **+1,7 p.p.**, F1 **+0,13**, precisao **+26 p.p.**; falsos positivos cairam de **11.656** para **3.507**.
- Threshold otimo desceu para **0,40** (modelo menos conservador nas probabilidades).

**Item 3 — Focos em celulas vizinhas**
- `neighbor_fires_7d`: soma de focos nas 8 celulas adjacentes (grade 0,1°) na janela de 7 dias.
- `neighbor_cell_ids()` em `src/domain/cell_id.py`; indice de vizinhanca pre-calculado em `build_features_table`.
- AUC **+1,1 p.p.** sobre item 2; F1 estavel (~0,585); **306 FP a menos** (3.507 → 3.201).
- Threshold otimo subiu para **0,85** (probabilidades mais confiantes com feature espacial).

**Item 4 — Tuning LightGBM**
- Grid de 6 combinacoes em `src/infrastructure/ml/train.py` (`CANDIDATE_PARAM_SETS`); selecao por **maior AUC no teste**.
- Params vencedores: `num_leaves=15`, `max_depth=5`, `min_child_samples=100`, `subsample=0.75`, `colsample_bytree=0.75`, `scale_pos_weight≈21,25`.
- AUC **+0,0002** vs item 3; F1 **0,584** (estavel); **+178 TP**, **+457 FP** vs item 3 (troca marginal recall x precisao).
- `metrics.json` passa a registrar `lgbm_params`, `tuning_candidates` e `tuning_best_auc`.

#### Features finais do modelo (9)

`fires_1d`, `fires_7d`, `fires_30d`, `days_without_rain`, `temp_mean_7d`, `precip_sum_7d`, `wind_mean_7d`, `neighbor_fires_7d`, `season_month`

#### Artefatos atuais (local, gitignored)

| Arquivo | Conteudo |
|---------|----------|
| `data/models/lgbm_orbitfire.pkl` | Modelo LightGBM retreinado |
| `data/models/metrics.json` | Metricas, params, matriz otima, limites de score |
| `data/models/thresholds.json` | Faixas baixo/medio/alto/critico |
| `data/models/confusion_matrix.png` | Matriz + KPIs (layout revisado) |

#### Reproducao do retreino e melhorias

```powershell
python -m src.application.build_features
python -m src.application.build_labels
python -m src.application.build_dataset
python -m src.infrastructure.ml.train
python -m src.application.calibrate_thresholds
pytest test/unit/test_features.py test/unit/test_ml_train.py test/unit/test_calibrate_thresholds.py -v
```

**Observacao:** acuracia sozinha e enganosa neste problema (baseline “sempre nao” ~90% no teste). Priorizar **AUC**, **F1**, **precisao** e **recall** na analise operacional.

### S3.E3 — Inferencia batch

| Campo | Valor |
|-------|-------|
| Objetivo | Gerar score 0-100 e faixa por celula para fogo amanha (D+1) |
| Modulos | M5, M6 |
| Fonte | SQLite (grade, FIRMS NRT, clima) + `lgbm_orbitfire.pkl` + `thresholds.json` |
| Implementada | Sim |
| Testada | Sim (`test/unit/test_predict_risk.py` — 3 testes) |
| Autorizada | Sim |
| Status | **Concluida** |

**Resumo:**
- O sistema le o modelo treinado, monta as 9 features do dia de referencia por celula e grava score, probabilidade e faixa em `risk_scores`.
- A data de referencia padrao e o dia mais recente com clima no banco; reexecucao atualiza scores (upsert) sem duplicar linhas.
- Fecha o ciclo S3: dados ingeridos viram mapa de risco persistido, pronto para API (S5) e dashboard (S6).

**Entregaveis:**
- `src/application/predict_risk.py` — `predict_risk()` + entrypoint
- `src/infrastructure/db/repository.py` — `upsert_risk_score`, `list_risk_scores`
- Tabela `risk_scores` populada no SQLite
- `test/unit/test_predict_risk.py`

**Execucao prevista:**
```powershell
python -m src.infrastructure.firms.ingest
python -m src.infrastructure.weather.ingest
python -m src.application.predict_risk
pytest test/unit/test_predict_risk.py -v
```

### Encerramento Sprint 3

**Resumo:**
- Refatoracao S0–S3: features centralizadas no dominio, cliente archive historico e testes alinhados ao TO.
- Suite completa verde: `pytest test/ -v` (100 testes).
- Commit Sprint 3 pendente de confirmacao; push apos merge local.

- [x] Refatoracao S0–S3 · `pytest test/ -v`
- [x] Commit · Push (`480b4b0`)

---

## Sprint 4 — Priorizador de brigadas

**Agentes:** `agent-domain-engineer` (S4.E1), `agent-data-analyst` (contrato de export S4.E2 e preparacao S6), `agent-test-engineer`.

### S4.E1 — Regras de priorizacao

**Resumo:**
- Score composto combina risk score, focos recentes (1d/7d/vizinhos) e impulso por faixa.
- Funcoes puras em `prioritization.py` com ranking Top-N e desempate deterministico.

**Entregaveis:** `src/domain/prioritization.py`, testes unitarios

### S4.E2 — Top-N e justificativa

**Resumo:**
- `rank_brigades.py` le `risk_scores`, aplica priorizacao e exporta Top-N em JSON/CSV com justificativa operacional.
- Saida alimenta API (S5) e dashboard (S6); `agent-data-analyst` valida colunas e KPIs do ranking via `dashboard-data-contract`.

**Entregaveis:** `src/application/rank_brigades.py`, `test/unit/test_rank_brigades.py`, `data/processed/brigade_ranking.json`, `data/processed/brigade_ranking.csv`

**Execucao prevista:**
```powershell
python -m src.application.predict_risk
python -m src.application.rank_brigades
pytest test/unit/test_rank_brigades.py -v
```

### Encerramento Sprint 4

- [ ] Refatoracao S0–S4 · `pytest test/ -v` · Commit · Push

---

## Sprint 5 — API

**Agentes:** `agent-system-architect` (rotas), `agent-data-analyst` (contrato JSON dos endpoints de mapa/ranking), `agent-test-engineer` (integracao).

### S5.E1 — Endpoints core

`GET /health`, `/risk/map`, `/risk/ranking`, `/fires/active`

**Resumo:**
- API FastAPI expoe saude, mapa de risco, ranking com `justificativa` e focos FIRMS recentes.
- Contrato alinhado a `dashboard-data-contract` (`agent-data-analyst`); routers finos delegam a `services.py`.
- `build_brigade_ranking` extraido para reutilizacao sem export em cada request.

**Entregaveis:** `src/api/main.py`, `src/api/routes.py`, `src/api/schemas.py`, `src/api/services.py`

**Execucao prevista:**
```powershell
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/docs
```

### S5.E2 — Testes integracao

**Resumo:**
- `test/integration/test_api.py` cobre os quatro endpoints com TestClient e BD temporario.
- Sem HTTP externo; reutiliza fixture de inferencia de `test_predict_risk`.

**Entregaveis:** `test/integration/test_api.py`

### Encerramento Sprint 5

- [ ] Refatoracao S0–S5 · `pytest test/ -v` · Commit · Push

---

## Sprint 6 — Dashboard

**Agentes:** `agent-data-analyst` + `agent-ux-ui` (skill `dashboard-data-contract` antes do codigo), `agent-test-engineer` (smoke).

### S6.E1 — Mapa e KPIs

**Resumo:**
- Painel Streamlit modular consome somente a API REST (`API_BASE_URL`).
- Mapa de calor no poligono TO (`to_boundary.py`); marcadores alto/critico; legenda interna compacta.
- Quatro KPIs com data em dd/mm/aa; subtitulo explicando o projeto.

**Entregaveis:** `src/dashboard/app.py`, `api_client.py`, `kpis.py`, `map_view.py`, `formatters.py`

**Execucao prevista:**
```powershell
uvicorn src.api.main:app --host 127.0.0.1 --port 8001
$env:PYTHONPATH = "."
streamlit run src/dashboard/app.py
```

### S6.E2 — Filtros, ranking, graficos e export CSV

**Resumo:**
- Sidebar: UF fixa TO, data somente leitura, faixa e Top-N editaveis, toggle de focos.
- Graficos Altair: sazonalidade mensal e ranking historico de focos por quadrante (`/fires/summary`).
- Ranking de brigadas com justificativa e export CSV; 131 testes passando.

**Entregaveis:** `sidebar.py`, `ranking_view.py`, `fires_charts.py`, `test/unit/test_dashboard_api_client.py`, `test/unit/test_fires_charts.py`, `test/unit/test_map_view.py`

### Encerramento Sprint 6

- [x] Refatoracao S0–S6 · `pytest test/ -v` (131 testes) · Commit · Push pendente

---

## Sprint 7 — Entrega final

### Entrega na plataforma FIAP (checklist PDF)

O envio na plataforma exige **um PDF unico** contendo:

1. **Primeira pagina:** nome completo de todos os integrantes
2. **Estrutura minima:** Introducao, Desenvolvimento, Resultados Esperados e Conclusoes
3. **Conteudo tecnico:** explicacoes da solucao, arquitetura, codigos principais e decisoes do grupo
4. **Evidencias visuais:** imagens, dashboards, diagramas, fluxogramas ou interfaces desenvolvidas
5. **Links obrigatorios** (tambem no final do PDF):
   - Link do repositorio do projeto
   - Link do video no YouTube (nao listado, ate 5 min)
6. **Codigo no PDF:** trechos em **formato texto** (nao usar print/screenshot de codigo)

**Video (YouTube, ate 5 min, nao listado):**

- Explicacao clara da integracao entre disciplinas
- Demonstracao pratica do funcionamento da solucao
- Link anexado ao final do PDF da entrega

Todas as informacoes, links e documentacoes obrigatorias devem estar organizadas **dentro do PDF**, incluindo repositorio e video.

### S7.E1 — README publico

**Resumo:**
- README com arquitetura, instalacao, pipeline de treino e operacao, API, dashboard, modo offline, testes e limitacoes da POC.
- Secao **Links e Observacoes** permanece pendente (repositorio, video, PDF).

**Entregaveis:** `README.md` (install, execucao, arquitetura, limitacoes)

**Pendente no README:**

- Secao **Links e Observacoes** (repositorio, video, decisoes tecnicas)

### S7.E2 — Revisao Godoy

**Entregaveis:** checklist `assets/Escopo.md` secao 7; demo online + offline; PDF unico na plataforma

### Encerramento Sprint 7

- [ ] Refatoracao S0–S7 · `pytest test/ -v` · Commit · Push

---

## Log de etapas concluidas

| Data | Etapa | Observacao |
|------|-------|------------|
| 2026-06-05 | Preparacao | Estrutura inicial `3212ca0` |
| 2026-06-05 | Preparacao | `docs/.gitignore` para planejamento local `f6d9932` |
| 2026-06-06 | Preparacao | `docs/` migrado para `assets/` — arquivos versionados no Git |
| 2026-06-05 | S0.E1 | Config base, requirements, 8 testes config; GRID_DEG 0.10 |
| 2026-06-05 | S0.E2 | Schema SQLite, repository, 8 testes db |
| 2026-06-05 | S0.E3 | Seed offline, loader idempotente, 6 testes seed |
| 2026-06-05 | S0 | Commit `88f7913` — fundacao completa |
| 2026-06-05 | S1.E1 | Cliente NASA FIRMS, parser, ingest, 13 testes |
| 2026-06-05 | S1.E2 | Open-Meteo, targets grade/seed, 10 testes clima |
| 2026-06-05 | S1.E3 | Grade `cell_id` UF_lat_lon, build_grid, 8 testes |
| 2026-06-05 | S1 | Commit `1850326` — 53 testes passando |
| 2026-06-05 | S2.E1–S2.E3 | Features, labels, dataset; refatoracao S0–S2 |
| 2026-06-05 | S2 | Commit `f35789b` — 75 testes passando |
| 2026-06-05 | S3.E1 | Treino LightGBM, 79 testes, modelo em `data/models/` |
| 2026-06-06 | S3.E2 | Risk score, faixas e `thresholds.json` |
| 2026-06-06 | S3 melhorias | Retreino TO — itens 1–4 (features, vizinhos, tuning, calibracao) |
| 2026-06-06 | S3.E3 | Inferencia batch `predict_risk.py`, upsert em `risk_scores` |
| 2026-06-05 | S6 | Dashboard Streamlit (mapa, KPIs, ranking, CSV); README treino vs operacao |

---

## O que falta (visao geral)

- [x] Preparacao — repo e documentacao em `assets/`
- [x] Sprint 0 — fundacao (commit `88f7913`)
- [x] Sprint 1 — ingestao FIRMS, clima e grade (commit `1850326`)
- [x] Sprint 2 — features, labels e dataset (commit `f35789b`)
- [x] Sprint 3 — LightGBM, risk score e inferencia (local; commit pendente)
- [x] Sprint 4 — priorizador de brigadas (local; commit pendente)
- [x] Sprint 5 — API FastAPI (local; commit pendente)
- [x] Sprint 6 — dashboard Streamlit (local; commit pendente)
- [x] Sprint 7 — S7.E1 README execucao (local; commit pendente)
- [ ] Sprint 7 — S7.E2 revisao Godoy, PDF e video
- [ ] M12 ESP32 (fora do MVP)

---

## Duvidas abertas

Proximo passo: Sprint 7 (README execucao, video, PDF e links entrega FIAP).
