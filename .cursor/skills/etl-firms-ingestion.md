---
name: etl-firms-ingestion
description: Guides NASA FIRMS API ingestion through validation, dedup and fire_events persistence. Use for FIRMS ingest, MAP_KEY, or CSV parsing.
---

# Ingestao FIRMS

## Objetivo

Pipeline confiavel da API NASA ate `fire_events` no Centro-Oeste.

## Passos

1. Config — `FIRMS_MAP_KEY`, bbox Centro-Oeste, `OFFLINE_MODE`
2. Fetch — `infrastructure/firms/client.py` com timeout e retry
3. Parse — CSV para tipos (`acq_datetime`, lat, lon, confidence, frp)
4. Validate — coordenadas dentro do bbox e datetime
5. region_key — `domain/region_key.py`
6. Dedup — nao reinserir mesma deteccao
7. Persist — insert transacional em SQLite

## Offline

`OFFLINE_MODE=1` le `data/seed/` com o mesmo parser.

## Dados brutos

Salvar em `data/raw/firms/` quando ingestao online.

## Riscos

- API indisponivel: log e manter ultimo snapshot
- CSV vazio: nao apagar historico

Agents: `agent-data-engineer`, `agent-domain-engineer` (region_key)
