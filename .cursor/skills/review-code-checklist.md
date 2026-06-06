---
name: review-code-checklist
description: Reviews OrbitFire code for SOLID, DRY, KISS and comment style before merge. Use for code review or quality checks on diffs.
---

# Checklist de revisao de codigo

## Objetivo

Revisao consistente antes de commit ou PR. **Obrigatoria** ao encerrar cada Sprint (refatoracao incremental antes do commit da fase).

## Escopo da refatoracao (cumulativo)

Ao encerrar a sprint Sn, revisar e refatorar o codigo de **todas as sprints ja implementadas** (S0 ate Sn) — nao apenas os arquivos novos da sprint atual. Buscar duplicacao, acoplamento e violacoes SOLID no acumulado.

## Apos refatoracao (sempre)

**Sempre que o diff incluir refatoracao**, rodar a suite completa antes de commit ou merge:

```bash
pytest test/ -v
```

Nao avancar com testes falhando ou sem ter executado os testes apos a refatoracao.

## Ordem

1. Comportamento — atende escopo em `docs/Escopo.md`?
2. Camadas — score e priorizacao fora de router e Streamlit?
3. SOLID, DRY, KISS
4. Comentarios — funcoes e blocos nao triviais com comentario breve?
5. Sem emoji — codigo, comentarios e strings de UI?
6. Dados — dedup idempotente; migration documentada?
7. Testes — mock FIRMS/clima; sem banco real de dev?
8. Segredos — sem `.env`, `.db` ou MAP_KEY no commit?
9. Suite completa — `pytest test/ -v` verde **apos** a refatoracao?

## Formato do feedback

```
Problema: ...
Principio: (ex. SRP)
Sugestao: ...
```

## Nao fazer

- reescrever feature inteira
- exigir abstracao especulativa

Agent dono: `agent-code-reviewer`
