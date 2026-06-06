# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="../../../assets/logo-fiap.png" 
       alt="FIAP - Faculdade de Informática e Administração Paulista" 
       width="40%">
</a>
</p>

<br>

# OrbitFire

## OrbitFire

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

O **OrbitFire** é uma POC da Global Solution FIAP 2026.1 que prevê **risco de incêndio para o dia seguinte** no **Tocantins (TO)**, cruzando detecções orbitais da NASA FIRMS com dados climáticos locais e apoiando a priorização de brigadas.

Satélites mostram onde já há fogo; gestores de defesa civil e brigadas florestais precisam saber **onde agir amanhã**. O OrbitFire responde a essa pergunta com um pipeline de dados e um modelo de machine learning (LightGBM) que estima, para cada célula geográfica do estado, a probabilidade de incêndio no dia seguinte. Esse resultado é convertido em **score de risco de 0 a 100** com faixas operacionais (baixo, médio, alto e crítico) e alimenta um ranking de áreas prioritárias para alocação de recursos (módulo M10).

A solução conecta a **economia espacial** a impacto positivo na Terra: dados de órbita (VIIRS e MODIS) deixam de ser apenas monitoramento reativo e passam a orientar **ação preventiva** antes do fogo se espalhar.

**Dados e estratégia:** para treino, o sistema usa histórico FIRMS SP e Open-Meteo Archive (jun–set/2024); em operação, FIRMS NRT (5 dias) e previsão climática. A grade cobre aproximadamente 4.150 células de 0,1 grau sobre o TO.

### Modelo e calibragem

O classificador LightGBM prevê **fogo amanhã** por célula. Após o treino no holdout temporal (jun–ago/2024 treino, set/2024 teste), aplicamos duas calibragens:

1. **Faixas de risk score** — limites `medio`, `alto` e `critico` em `thresholds.json`, derivados dos percentis 50/75/90 das probabilidades do conjunto de treino (escala 0–100).
2. **Threshold de classificação** — busca do ponto que maximiza **F1** no teste (atualmente **0,80**), usado na matriz abaixo e distinto do corte fixo 0,50.

O modelo evoluiu em quatro etapas incrementais (features climáticas, focos em vizinhança e tuning de hiperparâmetros). Em relação ao baseline inicial do TO (5 features, threshold 0,50):

| Métrica | Baseline | Modelo atual |
|---------|----------|--------------|
| AUC-ROC | 0,84 | **0,868** |
| F1 (thr ótimo) | 0,45 | **0,58** |
| Precisão | 34% | **60%** |
| Recall | 65% | 57% |
| Falsos positivos | 11.656 | **3.658** |

O ganho operacional mais relevante foi a **queda de falsos alarmes** (menos de um terço do volume anterior), mantendo recall útil para priorização. A acurácia isolada não é a métrica principal: o teste tem ~9% de positivos e um modelo que sempre prevê “sem fogo” já alcançaria ~90% de acurácia.

<p align="center">
  <img src="assets/confusion_matrix.png"
       alt="Matriz de confusão do modelo OrbitFire no conjunto de teste (set/2024)"
       width="85%">
</p>

*Matriz de confusão no teste (103.750 amostras): threshold 0,80, AUC 0,868, F1 0,58. KPIs à esquerda; células TN 90.712 · FP 3.658 · FN 4.006 · TP 5.374.*

**Entregas previstas:** ingestão FIRMS e clima, grade em SQLite, engenharia de features e labels, modelo preditivo, risk score, priorizador de brigadas, API REST (FastAPI), dashboard Streamlit e modo demo offline com dados seed para apresentação sem internet.


## 📁 Estrutura de pastas

Dentre os arquivos e pastas presentes na raiz do projeto, definem-se:

- <b>assets</b>: Materiais do projeto (logo, escopo, implementação, edital FIAP, matriz de confusão do modelo).

- <b>src</b>: Código-fonte em camadas:
  - <b>application</b> — casos de uso (grade, features, labels, dataset)
  - <b>domain</b> — regras puras (células, features, labels, risk score)
  - <b>infrastructure</b> — adaptadores (SQLite, FIRMS, clima, ML, seed)
  - <b>config.py</b> — configuração central (bbox TO, paths, flags)

- <b>data</b>: Dados do OrbitFire:
  - <b>raw</b> — snapshots FIRMS (CSV) e clima (JSON)
  - <b>processed</b> — parquets de features, labels e dataset
  - <b>models</b> — modelo LightGBM, métricas, thresholds e gráficos
  - <b>seed</b> — dados para modo demo offline
  - <b>logs</b> — registros de execução local

- <b>test</b>: Testes automatizados com pytest (`test/unit/`).

- <b>README.md</b>: Guia geral do projeto (este arquivo).


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

> **Pendente para entrega (S7):** documentar passo a passo antes do envio na plataforma.

Incluir:

- Pré-requisitos (Python 3.10+, venv, `.env`, chaves FIRMS/MAP_KEY)
- Instalação (`requirements.txt`)
- Comandos para ingestão, pipeline de modelagem, API e dashboard
- Modo demo offline (`OFFLINE_MODE`)


## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/SabrinaOtoni/TEMPLATE-FIAP-GRAD-ON-IA">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
