---
name: dashboard-data-contract
description: KPIs, agregacoes, escopo geografico TO e contrato API-dashboard OrbitFire. Use com agent-data-analyst e agent-ux-ui em qualquer ajuste de mapa, filtros ou metricas do painel.
---

# Contrato de dados — dashboard OrbitFire

## Objetivo

Alinhar **Analista de Dados** (`agent-data-analyst`) e **UX** (`agent-ux-ui`) sobre o que o painel exibe, sem acoplar Streamlit ao SQLite.

**Fluxo obrigatorio em ajustes pos-S6:** Analista valida regras de dados → UX aplica em `src/dashboard/` → pytest verde.

## Fontes (via API)

| Recurso | Campos principais | Uso no painel |
|---------|-------------------|---------------|
| Mapa de risco | `cell_id`, `lat`, `lon`, `score`, `band`, `uf`, `reference_date` | grade no TO |
| Ranking brigadas | `rank`, `cell_id`, `priority_score`, `risk_score`, `band`, `justificativa` | tabela Top-N |
| Focos ativos | `lat`, `lon`, `acq_datetime`, `source`, `frp` | overlay no mapa (so dentro do TO) |
| Health | status, `reference_date`, modo offline, contagens | sidebar e KPIs |
| Resumo de focos | `daily_counts`, `by_source`, `monthly_counts` | graficos pos-mapa (`GET /fires/summary`) |

## Escopo geografico (TO)

- Bbox retangular da grade **nao** equivale ao estado: cantos incluem PA/MA.
- **Regra:** exibir e agregar apenas celulas dentro do poligono `src/domain/to_boundary.py` (`is_in_tocantins`).
- Funcao de apoio no dashboard: `filter_risk_map_to_to()` em `map_view.py` — recalcula `total_cells` e `band_counts`.
- KPI **Celulas monitoradas** = celulas no poligono TO (~2.285), nao total da grade (~4.150).
- Focos no mapa: filtrar com `is_in_tocantins` antes de plotar.

## Filtros — editabilidade

| Filtro | Comportamento | Quem define |
|--------|---------------|-------------|
| UF | Fixo `TO — Tocantins` (somente leitura) | Analista (escopo MVP) |
| Data de referencia | Somente leitura quando ha **uma** data em `risk_scores`; formato **dd/mm/aa** | Analista (consulta API/BD) |
| Faixa de risco | Editavel (`Todos`, baixo, medio, alto, critico) | Analista + UX |
| Top-N | Editavel (10, 20, 50) | UX |
| Focos no mapa | Checkbox | UX |

Antes de liberar seletor de data ou UF: Analista confirma quantas datas/UFs existem no banco.

## KPIs (barra superior)

1. **Celulas monitoradas** — total **dentro do poligono TO** na data selecionada
2. **Alto + critico** — contagem `band in (alto, critico)` no mesmo recorte
3. **Focos 24h** — eventos FIRMS nas ultimas 24h (API `/fires/active`)
4. **Data de referencia** — dia da inferencia (`risk_scores.reference_date`)

KPIs devem usar o **mesmo recorte** do mapa (evitar mapa filtrado e KPI com total da bbox).

## Agregacoes

- Distribuicao por faixa: `baixo`, `medio`, `alto`, `critico`
- Top-N default: 10 celulas (configuravel na sidebar)
- Filtro por faixa afeta mapa; ranking usa data fixa + Top-N

## Metricas do modelo (copy honesta)

- AUC/F1 de `metrics.json` como **referencia de treino**, nao KPI operacional diario
- Evitar destacar acuracia isolada (classe rara ~9% positivos)
- Matriz de confusao: `assets/confusion_matrix.png`, threshold documentado no README

## Graficos de focos (pos-mapa)

Graficos com **significado operacional** para o TO (definidos pelo Analista):

1. **Sazonalidade por mes** — picos em estiagem (`monthly_counts`, ordem cronologica)
2. **Ranking por quadrante** — Top-N celulas com mais focos historicos (`cell_ranking`)

Fonte: `GET /fires/summary?days=30&top_cells=15`. Focos filtrados pelo poligono TO.
Render: **Altair** (`st.altair_chart`); meses em ordem cronologica.

## Ordem visual (UX)

1. Subtitulo explicando o projeto (tagline)
2. KPIs
3. Mapa de risco preditivo (celulas transparentes)
4. Graficos de comportamento de focos
5. Ranking de brigadas + export CSV

## Donos

| Atividade | Agente |
|-----------|--------|
| Escopo TO, KPIs, filtros editaveis, recorte geografico | `agent-data-analyst` |
| Mapa Folium, sidebar, layout, copy, retangulos/zoom | `agent-ux-ui` |
| Endpoints e payloads | `agent-system-architect` / API |
