---
name: test-pytest-api-etl
description: Writes OrbitFire tests with pytest, in-memory SQLite and mocked clients. Use when adding or fixing tests under test/.
---

# Testes pytest (API e ingestao)

## Objetivo

Regressao sem APIs NASA ou clima ao vivo.

## Padrões

```python
# Fixture: BD em memoria
# Mock: firms/weather client retorna fixture CSV
# TestClient: rotas FastAPI
```

## Casos MVP

- Parser CSV FIRMS
- Dedup idempotente
- `region_key` Centro-Oeste
- `risk_score` e faixas deterministicas
- priorizacao de brigadas
- `GET /health`, `/risk/map`, `/risk/ranking`, `/fires/active`

## Proibido

- Gravar em banco SQLite de dev em `data/`
- HTTP real para FIRMS ou clima em CI

```bash
pytest test/ -v
```

Agent dono: `agent-test-engineer`
