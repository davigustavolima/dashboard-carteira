# 📊 Dashboard de Carteira de Investimentos

Dashboard interativo em Python que permite montar uma carteira de ações e ETFs, comparar seu desempenho com o mercado (Ibovespa, S&P 500, Ouro, Dólar) e analisar risco e indicadores técnicos — tudo em tempo real, com dados do Yahoo Finance.

🔗 **Deploy:** ainda não publicado — por enquanto, rode localmente seguindo as instruções abaixo.

## ✨ Funcionalidades

- **Carteira personalizada**: tabela editável onde o usuário adiciona/remove ativos e define quanto investiu em cada um
- **Comparação com benchmarks**: Ibovespa, S&P 500 (convertido para R$), Ouro (convertido para R$) e Dólar
- **Análise de risco**: matriz de correlação, volatilidade anualizada, Sharpe Ratio, Beta em relação ao Ibovespa e Drawdown máximo
- **Análise técnica**: candlestick com Médias Móveis (50 e 200), Bandas de Bollinger, RSI e MACD
- **Explicações em linguagem simples** para cada indicador, pensadas para quem não é do mercado financeiro

## 🛠️ Tecnologias

- Python
- Streamlit (interface web)
- yfinance (cotações do Yahoo Finance)
- Pandas / NumPy (tratamento de dados e cálculos financeiros)
- Plotly (visualizações interativas)

## 🚀 Como rodar localmente

```bash
git clone https://github.com/SEU-USUARIO/dashboard-carteira.git
cd dashboard-carteira
pip install -r requirements.txt
streamlit run acoes_app.py
```

O app abre automaticamente em `http://localhost:8501`.

## 📁 Estrutura

```
├── acoes_app.py              # aplicação Streamlit
├── requirements.txt          # dependências
└── README.md
```

## 💡 Sobre este projeto

Este projeto nasceu de um script de análise financeira de um exercício da Hashtag Treinamentos e foi transformado em um dashboard interativo como exercício prático de **Análise de Dados**: da extração e limpeza dos dados (ETL com yfinance/Pandas), passando pela criação de métricas e indicadores (estatística aplicada a finanças), até a construção de visualizações que comunicam a informação de forma clara para quem for usar — a parte que, no fim das contas, mais importa em qualquer análise.

## ⚠️ Aviso

Projeto construído para fins educacionais. Não constitui recomendação de investimento.
