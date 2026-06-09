# OrbitFire

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="assets/logo-fiap.png"
         alt="FIAP - Faculdade de Informática e Administração Paulista"
         width="35%">
  </a>
</p>

## 👥 Integrantes:
- [Everton Marinho Souza](https://github.com/Emarinhos) — RM568137@fiap.com.br
- [Julia Gutierres Fernandes Souza](https://github.com/Juliagutierres29) — RM568296@fiap.com.br
- [Raimunda Nayara Mendes dos Santos](https://github.com/rm567718) — RM567718@fiap.com.br
- [Felipe de Souza Lourenco](https://github.com/Xaramandas) — RM567521@fiap.com.br
- [Matheus Ribeiro Martelletti](https://github.com/Martelletti27) — RM566767@fiap.com.br

## 👩‍🏫 Professores:
### Tutor(a)
- [Sabrina Otoni](https://www.linkedin.com/in/sabrina-otoni-22525519b/)
### Coordenador(a)
- [Andre Godoy, PhD](https://www.linkedin.com/company/inova-fusca)


## 📜 Descrição

O **OrbitFire** é a solução da Global Solution FIAP 2026.1 para prever **risco de incêndio no dia seguinte** no **Tocantins (TO)**. A NASA FIRMS mostra onde há fogo hoje; o sistema combina essas detecções com clima local (Open-Meteo) e indica **onde priorizar brigadas amanhã**, com **score de risco (0–100)** e ranking. A grade tem ~4.150 células de 0,1°, os dados ficam em SQLite e o resultado é exposto por API FastAPI e dashboard Streamlit.

Um único modelo LightGBM atende treino e operação diária, trocando apenas as fontes de dados:

| Etapa | NASA FIRMS | Open-Meteo | Papel |
|-------|------------|------------|-------|
| Treino | VIIRS/MODIS **SP** (jun–set/2024) | **Archive** | Gerar features, labels e treinar o classificador |
| Operação | VIIRS/MODIS **NRT** (5 dias) | **Forecast** | Atualizar features e inferir risco para amanhã |

Na operação, `predict_risk` grava os scores em `risk_scores`; a API (`/risk/map`, `/risk/ranking`) e o dashboard consomem esse resultado.

### Modelo e calibragem

O classificador prevê **fogo amanhã** por célula. O holdout é temporal: jun–ago/2024 para treino, set/2024 para teste (502.150 linhas; ~9% de positivos). Duas calibragens pós-treino:

1. **Faixas de risk score** — limites `medio`, `alto` e `critico` em `thresholds.json` (percentis 50/75/90 do treino, escala 0–100).
2. **Threshold de classificação** — ponto que maximiza **F1** no teste (**0,80**), usado na matriz abaixo.

| Métrica | Baseline | Modelo atual |
|---------|----------|--------------|
| AUC-ROC | 0,84 | **0,868** |
| F1 (thr ótimo) | 0,45 | **0,58** |
| Falsos positivos (teste) | 11.656 | **3.658** |

### Por que o recall é ~57%?

O modelo prevê **condições favoráveis ao incêndio**, não o incêndio em si.
O fogo depende de um fator humano (ignição) que nenhum dado orbital ou
climático consegue antecipar. Quando o modelo prevê alto risco e não há fogo,
não significa erro — significa que as condições estavam presentes, mas o
fator humano não ocorreu.

Operacionalmente, isso é aceitável: o objetivo é **posicionar brigadas**
em regiões propensas ao fogo, não prever com certeza onde ele vai acontecer.
A métrica mais relevante para esse objetivo é o **AUC-ROC (0,868)**, que
mede a capacidade de separar regiões de alto e baixo risco independentemente
do limiar de decisão.

#### Matriz de confusão (teste set/2024)

![Matriz de confusão do modelo OrbitFire no conjunto de teste set/2024 — threshold 0,80, AUC 0,868, F1 0,58](assets/confusion_matrix.png)

*103.750 amostras: TN 90.712 · FP 3.658 · FN 4.006 · TP 5.374. KPIs à esquerda do gráfico.*

Detalhes do retreino em `assets/Implementacao.md`.


## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>assets</b>: Materiais do projeto (logo, escopo, implementação, edital FIAP, matriz de confusão do modelo).

- <b>src</b>: Código-fonte em camadas:
  - <b>application</b> — casos de uso (grade, features, labels, dataset)
  - <b>domain</b> — regras puras (células, features, labels, risk score)
  - <b>infrastructure</b> — adaptadores (SQLite, FIRMS, clima, ML, seed)
  - <b>api</b> — REST FastAPI (mapa, ranking, focos, health)
  - <b>dashboard</b> — painel Streamlit (consome API)
  - <b>config.py</b> — configuração central (bbox TO, paths, flags)

- <b>data</b>: Dados do OrbitFire:
  - <b>raw</b> — snapshots FIRMS (CSV) e clima (JSON)
  - <b>processed</b> — parquets de features, labels e dataset
  - <b>models</b> — modelo LightGBM, métricas, thresholds e gráficos
  - <b>seed</b> — dados para modo demo offline
  - <b>logs</b> — registros de execução local

- <b>test</b>: Testes automatizados com pytest (`test/unit/`).

- <b>README.md</b>: Guia geral do projeto (este arquivo).


## 🏗 Arquitetura

Fluxo ponta a ponta:

```
NASA FIRMS + Open-Meteo
        ↓
   Ingestão (SQLite)
        ↓
 Features + Labels → Dataset → LightGBM (treino)
        ↓
 Inferência (predict_risk) → risk_scores
        ↓
 Priorização de brigadas → API FastAPI → Dashboard Streamlit
```

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| Domínio | `src/domain/` | Células, features, labels, risk score, contorno do TO |
| Aplicação | `src/application/` | Grade, dataset, treino, inferência, ranking |
| Infraestrutura | `src/infrastructure/` | FIRMS, clima, SQLite, ML |
| API | `src/api/` | REST: mapa, ranking, focos, saúde |
| Dashboard | `src/dashboard/` | Painel Streamlit (somente HTTP à API) |

O dashboard **não** acessa o banco diretamente — consome `API_BASE_URL`.


## 📎 Links e Observações

> **Pendente para entrega (S7):** preencher esta seção antes do envio na plataforma.

- <b>Repositório do projeto</b>: _(link do GitHub — inserir na entrega)_
- <b>Vídeo no YouTube (até 5 min, não listado)</b>: _(inserir link)_
  - Explicação clara da integração entre disciplinas
  - Demonstração prática do funcionamento da solução
  - Postagem como **não listado**, com link anexado ao final do PDF
- <b>Decisões técnicas</b>: _(resumo das escolhas do grupo — inserir na entrega)_
- <b>Observações gerais</b>: _(competições ou demais observações, se houver)_


## 🔧 Como executar o código

### Pré-requisitos

- **Python 3.10+**
- Chave NASA FIRMS ([cadastro MAP_KEY](https://firms.modaps.eosdis.nasa.gov/api/map_key/))
- Conexão com internet (ingestão e treino) ou modo demo offline

### Instalação

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configuração

Copie o template e preencha a chave FIRMS:

```powershell
copy src\.env.example .env
```

| Variável | Descrição |
|----------|-----------|
| `FIRMS_MAP_KEY` | Chave da API NASA FIRMS |
| `OFFLINE_MODE` | `1` = usa dados seed (sem internet) |
| `DB_PATH` | Caminho do SQLite (padrão `data/orbitfire.db`) |
| `API_BASE_URL` | URL da API para o dashboard (padrão `http://127.0.0.1:8000`) |

### Pipeline de treino (uma vez)

Gera o modelo a partir do histórico jun–set/2024 (FIRMS SP + clima Archive):

```powershell
python -m src.application.build_grid
python -m src.infrastructure.firms.ingest_historical
python -m src.infrastructure.weather.ingest_historical
python -m src.application.build_features
python -m src.application.build_labels
python -m src.application.build_dataset
python -m src.infrastructure.ml.train
python -m src.application.calibrate_thresholds
```

Saídas: `data/models/lgbm_orbitfire.pkl`, `thresholds.json`, `metrics.json`.

### Operação diária (predição)

Atualiza dados recentes (FIRMS NRT + clima Forecast) e grava scores no banco:

```powershell
python -m src.infrastructure.firms.ingest
python -m src.infrastructure.weather.ingest
python -m src.application.predict_risk
```

### API e dashboard

## O que o dashboard mostra

Ao abrir o painel em `http://localhost:8501`, o usuário vê:

- **4 KPIs no topo**: células monitoradas dentro do TO (~2.285),
  contagem de células em nível alto ou crítico, focos ativos nas
  últimas 24h e a data de referência da inferência mais recente.
- **Mapa de calor interativo**: risco preditivo por célula dentro
  do polígono do Tocantins. Células com risco alto ou crítico recebem
  marcadores. Focos FIRMS ativos podem ser sobrepostos via checkbox.
- **Gráficos de comportamento**: sazonalidade histórica de focos por
  mês e ranking das células com maior incidência histórica.
- **Ranking de brigadas**: Top-N células priorizadas com justificativa
  operacional (ex.: "faixa crítico com 2 focos nas últimas 24h e
  3 focos em células vizinhas"). Exportável em CSV.

O dashboard **não acessa o banco diretamente** — consome exclusivamente
a API REST em `API_BASE_URL`.

Com scores no SQLite, suba a API e o painel em **dois terminais** (na raiz do projeto):

```powershell
# Terminal 1 — API (Swagger em http://127.0.0.1:8000/docs)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Dashboard (http://localhost:8501)
$env:PYTHONPATH = "."
streamlit run src/dashboard/app.py
```

Se a porta 8000 estiver ocupada, use outra (ex.: `8001`) e ajuste `API_BASE_URL` no `.env`.

**Reinicie a API** após alterar código do backend — o dashboard depende dos endpoints atualizados (ex.: `/fires/summary`).

### Modo demo offline

> **Para a banca:** o modo offline permite apresentar toda a solução
> (ingestão → inferência → API → dashboard) sem internet e sem chave
> NASA FIRMS. Os dados seed representam focos e clima reais do Tocantins
> e são suficientes para demonstrar o funcionamento completo do sistema.

Para apresentação sem internet nem chave FIRMS:

```powershell
# No .env: OFFLINE_MODE=1
python -m src.application.build_grid
python -m src.infrastructure.firms.ingest
python -m src.infrastructure.weather.ingest
python -m src.application.predict_risk
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

### Testes

```powershell
pytest test/ -v
```


## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/SabrinaOtoni/TEMPLATE-FIAP-GRAD-ON-IA">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
