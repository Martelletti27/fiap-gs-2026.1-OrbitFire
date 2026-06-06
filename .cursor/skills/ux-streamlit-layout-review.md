---
name: ux-streamlit-layout-review
description: >-
  Audits OrbitFire Streamlit dashboard layout for hierarchy, scanability and
  operator friction. Use before UX changes or dashboard sprint reviews.
---

# Revisao de layout — Streamlit OrbitFire

## Objetivo

Avaliar o painel como **gestor de defesa civil** ou avaliador FIAP: encontra risco, KPIs, mapa e ranking de brigadas em poucos segundos?

Em ajustes de mapa/filtros/KPIs: acionar `agent-data-analyst` antes deste checklist (`dashboard-data-contract`).

Agent dono: `agent-ux-ui`

## Checklist (ordem de leitura na tela)

### 0. Subtitulo

| Item | OK se |
|------|--------|
| Tagline | Frase clara: FIRMS + clima → risco amanha → priorizacao no TO |
| Sem jargao | Operador entende o proposito sem abrir README |

### 1. Topo — KPIs

| Item | OK se |
|------|--------|
| Ordem logica | Celulas criticas → focos ativos → data de referencia |
| Fallback | API falha: placeholders (`—`) sem quebrar linha inteira |
| Sem duplicar | Mesmo numero nao aparece com rotulos diferentes |

### 2. Sidebar

| Item | OK se |
|------|--------|
| Status visivel | Offline/online no topo |
| Filtros | UF/data fixos quando contrato exige; faixa e Top-N editaveis |
| Export | Botao CSV acessivel |
| Sem ruido | Sem URL da API, sem credenciais |

### 3. Mapa de risco

| Item | OK se |
|------|--------|
| Titulo claro | "Mapa de risco preditivo" |
| Tocantins | Apenas celulas dentro do poligono TO; sem cantos PA/MA |
| Transparencia | Grade ~35–40% opaca; nomes de cidades visiveis no mapa base |
| Legenda | Fora do mapa (Streamlit), compacta; nao cobrir area geografica |
| Hotspots | Alto/critico visiveis (marcadores ou calor com contraste) |
| Zoom | Retangulos de grade escalam; sem bolhas sobrepostas em zoom afastado |
| KPI vs mapa | Contagem de celulas bate com o recorte exibido |
| Data | Formato dd/mm/aa em KPI e sidebar |

### 3b. Graficos de focos

| Item | OK se |
|------|--------|
| Posicao | Apos o mapa, antes do ranking |
| Relevancia | Serie diaria, satelite e sazonalidade — nao graficos decorativos |
| Escopo TO | Dados de `/fires/summary` filtrados pelo poligono |
| Erro API | `st.warning` / `st.error` acionavel |

### 4. ranking de brigadas

| Item | OK se |
|------|--------|
| Justificativa | Coluna legivel para operador |
| Sync API | Indicador se ranking desatualizado |
| Top-N | Configuravel ou fixo conforme escopo |

### 5. Hierarquia

| Item | OK se |
|------|--------|
| `st.divider` entre blocos | Sim, entre KPIs / mapa / ranking |
| Wide layout | `set_page_config(layout="wide")` |
| pt-BR | Rotulos sem emoji |

## Severidade

| Nivel | Acao |
|-------|------|
| **Bloqueante** | Operador nao sabe qual data/UF esta vendo; KPI contradiz mapa |
| **Importante** | Metricas duplicadas; filtros inconsistentes |
| **Polish** | Espacamento, texto de `help` |

Agent dono: `agent-ux-ui`
