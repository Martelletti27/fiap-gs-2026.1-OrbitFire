---
name: data-sqlite-persistence
description: Manages SQLite schema for OrbitFire tables. Use when altering models or database integrity.
---

# Persistencia SQLite

## Objetivo

Schema seguro para POC local e testes.

## Tabelas

- `grid_cells` — celulas do Centro-Oeste
- `fire_events` — deteccoes FIRMS individuais
- `weather_daily` — clima diario por regiao
- `risk_scores` — score e faixa por celula/data

Detalhes: `docs/Implementacao.md` (S0.E2).

## Fluxo de mudanca

1. Alterar schema em `src/infrastructure/db/`
2. Migration ou script SQL em `docs/`
3. Testes com BD `:memory:`
4. Nunca commitar `data/*.db`

## Integridade

- Indice em `acq_datetime` (fire_events)
- Indice em `(cell_id, date)` (risk_scores)
- Unique na chave de dedup de fire_events

Agent dono: `agent-data-engineer`
