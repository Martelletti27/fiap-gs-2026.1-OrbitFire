---
name: plan-task-decomposition
description: Breaks requests into ordered verifiable slices with clear agent ownership. Use when planning multi-step implementation.
---

# Decomposicao de tarefas

## Objetivo

Entregas pequenas, ordenadas e verificaveis.

## Passos

1. Resultado — o que o usuario pode fazer ao final?
2. Criterios de pronto — testes, doc, smoke
3. Fatias — um agent dono por fatia (`agents-routing.mdc`)
4. Dependencias — schema, ingestao, features, modelo, priorizacao, API, dashboard
5. Plano — sprints em `docs/Implementacao.md`
6. Primeiro passo — menor validacao (ex.: uma celula no BD)
7. Ao concluir fatia — bloco **Resumo** em `Implementacao.md` (acima de Entregaveis, tres bullets simples)

## Anti-padrao

- fatia unica "refatorar tudo"
- implementar sem criterio de sucesso
