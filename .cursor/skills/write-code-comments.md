---
name: write-code-comments
description: Requires brief Portuguese comments on functions and non-trivial code blocks. Use when writing or reviewing Python under src/ and test/.
---

# Comentários no código

## Objetivo

Código legível para a banca e para manutenção do POC.

## Obrigatório

- **Função pública:** docstring ou comentário de uma linha com o que faz e retorno esperado.
- **Classe:** uma linha sobre responsabilidade.
- **Bloco não óbvio:** comentário breve antes do bloco (parser FIRMS, dedup, normalização, query agregada).
- **Constantes de negócio:** comentar unidade ou origem (ex.: pesos do `risk_score`).

## Estilo

- pt-BR, frase curta, sem emoji.
- Explicar **porquê**, não repetir o nome da variável.
- Evitar comentário em linha óbvia (`i += 1  # incrementa i`).

## Exemplo

```python
def normalize(values: list[float]) -> list[float]:
    """Escala valores para 0-1 usando min-max na janela atual."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    span = hi - lo or 1.0
    return [(v - lo) / span for v in values]
```

## Proibido

- Emoji em comentários, logs, mensagens de API ou UI
- Blocos longos sem nenhum comentário de seção

Agents: `agent-code-reviewer`, todos ao implementar em `src/` e `test/`
