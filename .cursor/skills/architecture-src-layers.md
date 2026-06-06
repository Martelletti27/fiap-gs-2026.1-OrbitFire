---
name: architecture-src-layers
description: Enforces OrbitFire layer boundaries between domain, application, infrastructure, api and dashboard. Use when structuring code under src/.
---

# Arquitetura em camadas (`src/`)

## Objetivo

Garantir que mudancas respeitem as camadas do OrbitFire.

## Mapa

```
src/dashboard/       -> UI (Streamlit, so HTTP a API)
src/api/             -> HTTP REST (routers finos)
src/application/     -> casos de uso (grade, features, inferencia, ranking)
src/domain/          -> region_key, risk_score, priorizacao de brigadas (puro)
src/infrastructure/  -> FIRMS, clima, SQLite, ML
src/config.py        -> env, bbox Centro-Oeste, paths
```

## Regras

- `domain/` nao importa FastAPI, SQLAlchemy, LightGBM nem `requests`.
- `api/` nao chama NASA FIRMS nem APIs de clima diretamente.
- `dashboard/` nao abre SQLite.
- `application/` orquestra dominio e infrastructure; nao contem regras de negocio puras.

## Checklist

- [ ] Router so delega?
- [ ] Score e priorizacao testaveis sem BD?
- [ ] FIRMS e clima isolados em `infrastructure/`?

Agent dono: `agent-system-architect`
