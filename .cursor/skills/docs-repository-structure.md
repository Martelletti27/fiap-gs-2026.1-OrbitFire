---
name: docs-repository-structure
description: Places OrbitFire documentation in correct README and assets paths with pt-BR standards. Use when writing or reorganizing documentation.
---

# Estrutura de documentacao

## Onde escrever

| Conteudo | Local |
|----------|--------|
| Install e como rodar | `/README.md` |
| Entrega final (congelado) | `assets/Escopo.md` |
| Sprints e progresso | `assets/Implementacao.md` |
| Edital FIAP | `assets/Titulo.md` |
| Arquitetura | `assets/arquitetura.md` (quando criado) |
| Contrato API | `assets/api.md` (quando criado) |
| Pitch | `assets/pitch.md` (quando criado) |

## Regras

- `Escopo.md`, `Implementacao.md` e `Titulo.md` versionados em `assets/`
- Nao usar pasta `docs/` — foi substituida por `assets/` no commit `2d0dc81`
- pt-BR, alinhado a `src/`
- Sem emoji em titulos ou listas
- Narrativa: satelite FIRMS → clima → IA → score → brigadas → dashboard

Agent dono: `agent-documentation`
