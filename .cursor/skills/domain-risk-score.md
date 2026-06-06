---
name: domain-risk-score
description: Guides risk_score, faixas e priorizacao de brigadas para OrbitFire. Use for ranking and brigade priority rules.
---

# Score de risco e priorizacao (OrbitFire)

## Objetivo

Risco preditivo explicavel para o dia seguinte no Centro-Oeste, com ranking operacional de brigadas.

## Pipeline

1. LightGBM gera probabilidade por celula/data (`infrastructure/ml/`)
2. `domain/risk_score.py` converte em score 0–100 e faixa (baixo/medio/alto/critico)
3. `domain/prioritization.py` ranqueia celulas para alocacao de brigadas

## Faixas de risco

- Definidas em `data/models/thresholds.json` apos treino
- Logica pura em `src/domain/risk_score.py` — testavel sem BD

## priorizacao de brigadas

- Combina: `risk_score` + recencia de focos + peso por UF
- Saida: Top-N com justificativa legivel (`application/rank_brigades.py`)

## Referencia

- Escopo: `docs/Escopo.md` (E5, E6, E7)
- Sprints: `docs/Implementacao.md` (S3, S4)

Agent dono: `agent-domain-engineer`
