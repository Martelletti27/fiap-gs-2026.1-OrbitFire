---
name: ux-streamlit-dashboard-orbitfire
description: >-
  OrbitFire Streamlit dashboard structure, TO risk map, ranking de brigadas and API-only
  constraints. Use when implementing or adjusting src/dashboard layout, map or filters.
---

# Padroes do dashboard OrbitFire

## Objetivo

Implementar UI alinhada ao escopo (E9, sprint S6+) sem violar `orbitfire-dashboard.mdc`.

**Parceria obrigatoria:** ajustes de mapa, filtros ou KPIs comecam com `agent-data-analyst` (skill `dashboard-data-contract`); implementacao em `agent-ux-ui`.

## Arquitetura de UI (somente HTTP)

```
sidebar → filtros (faixa, Top-N, focos; UF e data fixos)
app.py
  ├── KPIs (celulas TO, alto+critico, focos 24h, data)
  ├── map_view (mapa TO — retangulos Folium)
  └── ranking_view (Top-N brigadas + justificativa)
```

- **Proibido:** SQLite, `risk_score` local, MAP_KEY no Streamlit.
- **Config:** `API_BASE_URL` via `src.config`; `PYTHONPATH=.` na raiz ao rodar Streamlit.

## Layout canonico

Ordem vertical em `app.py`:

1. **Titulo** + **subtitulo** (frase que explica o projeto)
2. **KPIs**
3. **Divisor**
4. **Mapa de risco preditivo** — Tocantins com grade transparente
5. **Divisor**
6. **Graficos de focos** — serie diaria, satelite, sazonalidade (`fires_charts.py`)
7. **Divisor**
8. **Prioridade de brigadas** — tabela Top-N
9. **Export CSV** — na secao de ranking

## Filtros (sidebar)

| Controle | Tipo |
|----------|------|
| UF | `text_input` desabilitado: `TO — Tocantins` |
| Data de referencia | `text_input` desabilitado quando unica data no banco |
| Nivel de risco | `selectbox` editavel |
| Top-N | `selectbox` editavel |
| Focos no mapa | `checkbox` |

Mudanca de faixa atualiza mapa e KPIs (apos `filter_risk_map_to_to`).

## Mapa (regras de renderizacao)

- Dados: `GET /risk/map` + `filter_risk_map_to_to()`
- **Nao** plotar bbox retangular inteiro — apenas celulas em `is_in_tocantins()`
- Risco: `folium.plugins.HeatMap` com pontos pequenos (`radius` ~4) e peso = score/100
- Gradiente verde → amarelo → laranja → vermelho; legenda compacta **dentro** do mapa (canto inferior direito)
- Marcadores alto/critico pequenos, borda na cor do preenchimento, sombra colorida (`DivIcon`)
- **Evitar** retangulos opacos ou `CircleMarker` grande para a grade inteira
- Contorno do estado: `folium.Polygon` com `TO_BOUNDARY`
- `fit_bounds` no poligono TO; legenda com **alto contraste** (fundo branco, borda escura, texto #111)
- Focos: `CircleMarker` pequeno, somente dentro do TO
- Caption com contagem de celulas e percentual de transparencia

## Ranking de brigadas

- Dados: `GET /risk/ranking`
- Colunas: celula, score, faixa, justificativa
- Ordenacao identica a API — nao recalcular no dashboard

## Execucao local (validar UX)

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
# se 8000 ocupada: --port 8001 e API_BASE_URL=http://127.0.0.1:8001
PYTHONPATH=. streamlit run src/dashboard/app.py
```

API deve responder `/health` antes de avaliar KPIs e mapa.

Agent dono: `agent-ux-ui` · Contrato de dados: `agent-data-analyst`
