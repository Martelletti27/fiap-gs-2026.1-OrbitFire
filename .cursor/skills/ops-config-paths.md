---
name: ops-config-paths
description: Configures src/config.py, .env, data paths, seed offline and local runtime for OrbitFire. Use for operational paths or local run issues.
---

# Configuracao e paths

## Objetivo

Um unico lugar para paths, bbox e flags de execucao.

## `src/config.py`

- `PROJECT_ROOT`, `DATA_DIR`, `DB_PATH`
- `REGION`, `BBOX` (Centro-Oeste: GO, MT, MS, DF)
- `GRID_DEG`, paths `data/raw/`, `data/processed/`, `data/models/`
- `FIRMS_MAP_KEY`, `OFFLINE_MODE`
- `API_HOST`, `API_PORT`

## `src/.env.example`

Copiar para `.env` na raiz (gitignored):

```
FIRMS_MAP_KEY=
OFFLINE_MODE=0
DB_PATH=data/orbitfire.db
```

## Gitignore

- `data/*.db`, `.env`
- Permitir `data/seed/*.csv` pequeno

## Demo offline

1. Amostra em `data/seed/`
2. `OFFLINE_MODE=1`
3. Ingestao, API e dashboard sem internet

Agent dono: `agent-devops`
