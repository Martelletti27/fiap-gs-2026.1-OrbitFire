---
name: ux-streamlit-copy-controls
description: >-
  Defines pt-BR labels, help text and error messages for OrbitFire dashboard.
  Use when writing sidebar text, metrics, warnings or filter labels.
---

# Copy e controles — Streamlit OrbitFire

## Objetivo

Rotulos e mensagens **claras para gestores e banca**, sem emoji, alinhadas ao dominio (risco, celula, brigada, score).

Agent dono: `agent-ux-ui`

## Vocabulario padrao (pt-BR)

| Conceito | Rotulo preferido | Evitar |
|----------|------------------|--------|
| Score preditivo | Risco preditivo | Probabilidade (sem contexto) |
| Faixa | Nivel de risco | Classe / tier |
| Celula geografica | Celula | Pixel / grid cell |
| ranking de brigadas | Prioridade de brigadas | Top estados |
| Focos ativos | Focos ativos | Fire events |
| OFFLINE_MODE | Modo Offline / Modo Online | Seed mode |
| Centro-Oeste | Centro-Oeste (GO, MT, MS, DF) | Brasil inteiro |

## Padrao `help`

- Uma ou duas frases; explicar o que o filtro afeta (mapa e ranking).
- Explicar diferenca entre risco preditivo e focos ativos.

## Mensagens de estado

| Situacao | Componente | Tom |
|----------|------------|-----|
| API inacessivel | `st.error` | Acao: subir `uvicorn src.api.main:app` |
| Sem dados na data | `st.info` | "Nenhum score para a data selecionada" |
| Ranking desync | `st.warning` | Curto: recarregar ou mudar filtro |

Sem emoji em `st.error`, `st.warning`, `st.info`.

## Controles Streamlit

| Controle | Uso neste projeto |
|----------|-------------------|
| `st.sidebar.selectbox` | UF, nivel de risco |
| `st.sidebar.date_input` | Data de referencia |
| `st.sidebar.button` | Export CSV |
| `st.metric` | KPIs do topo |
| `st.dataframe` | ranking de brigadas — `column_config` para formatar |

## Anti-padroes

- Explicar URL da API na sidebar (ruido em demo).
- Misturar focos ativos com risco preditivo sem rotulo distinto.
- Texto longo acima do mapa (empurra visualizacao para baixo).
