---
name: plan-end-to-end-impact
description: Analyzes end-to-end impact across OrbitFire before isolated changes. Use when planning refactors, features, or cross-layer work.
---

# Impacto ponta a ponta

## Objetivo

Evitar mudancas locais que quebram FIRMS, clima, BD, ML, API ou dashboard.

## Perguntas

1. Qual fluxo completo?
2. `data/` (raw, processed, models) ou seed afetados?
3. Quais camadas? (`domain`, `application`, `infrastructure`, `api`, `dashboard`)
4. Precisa migration, teste, doc ou seed?
5. Demo offline (`OFFLINE_MODE`) continua ok?
6. Qual agent dono? (`agents-routing.mdc`)

## Saida

- mapa do fluxo
- riscos e ordem segura de mudanca
