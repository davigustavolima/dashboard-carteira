"""
Dashboard de Carteira de Investimentos
----------------------------------------
Projeto de Análise de Dados aplicado ao mercado financeiro.
Autor: Davi Gustavo de Lima
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ------------------------------------------------------------------
st.set_page_config(page_title="Dashboard de Carteira", layout="wide", page_icon="📊")

st.title("📊 Dashboard de Carteira de Investimentos")
st.caption("Monte sua carteira, compare com o mercado e analise o risco — tudo em tempo real.")

BENCHMARKS_DISPONIVEIS = {
    "Ibovespa": "^BVSP",
    "S&P 500 (em R$)": "^GSPC",
    "Ouro (em R$)": "GC=F",
    "Dólar": "BRL=X",
}

# ------------------------------------------------------------------
# FUNÇÕES DE APOIO (com cache para não bater na API toda hora)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def pegar_cotacoes(lista_tickers, data_inicio, data_fim):
    df = yf.download(lista_tickers, start=data_inicio, end=data_fim, auto_adjust=False, progress=False)
    df = df["Adj Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame()
    df = df.ffill().dropna(how="all")
    return df


def normalizar_ticker(t):
    t = t.strip().upper()
    if not t:
        return t
    # ETFs e ações brasileiras terminam em número; se o usuário não colocar .SA, isso é adicionado 
    if not t.endswith(".SA") and not t.startswith("^") and "=" not in t and t[-1].isdigit():
        t += ".SA"
    return t


def calcular_indicadores_tecnicos(df):
    df = df.copy()
    df["MM50"] = df["Close"].rolling(50).mean()
    df["MM200"] = df["Close"].rolling(200).mean()

    # RSI (14 dias)
    delta = df["Close"].diff()
    ganho = delta.clip(lower=0).rolling(14).mean()
    perda = -delta.clip(upper=0).rolling(14).mean()
    rs = ganho / perda
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Bandas de Bollinger (20 dias, 2 desvios)
    media20 = df["Close"].rolling(20).mean()
    desvio20 = df["Close"].rolling(20).std()
    df["BB_Superior"] = media20 + 2 * desvio20
    df["BB_Inferior"] = media20 - 2 * desvio20
    df["BB_Media"] = media20

    return df


def max_drawdown(serie_valor):
    pico = serie_valor.cummax()
    drawdown = serie_valor / pico - 1
    return drawdown.min()


# ------------------------------------------------------------------
# BARRA LATERAL — MONTAGEM DA CARTEIRA PELO USUÁRIO
# ------------------------------------------------------------------
st.sidebar.header("⚙️ Monte sua carteira")

st.sidebar.markdown(
    "Edite a tabela abaixo: adicione linhas (➕ no rodapé), troque o ticker "
    "e o valor investido em cada ativo. Ações da B3 podem ser digitadas sem o "
    "sufixo `.SA` (ex: `PETR4`)."
)

carteira_padrao = pd.DataFrame(
    {
        "Ticker": ["ITUB4", "VALE3", "PETR4", "BBAS3", "IVVB11"],
        "Valor Investido (R$)": [5000, 3000, 4000, 2000, 6000],
    }
)

tabela_carteira = st.sidebar.data_editor(
    carteira_padrao,
    num_rows="dynamic",
    use_container_width=True,
    key="editor_carteira",
)

benchmarks_escolhidos = st.sidebar.multiselect(
    "Comparar carteira com:",
    options=list(BENCHMARKS_DISPONIVEIS.keys()),
    default=["Ibovespa", "S&P 500 (em R$)"],
)

anos_historico = st.sidebar.slider("Anos de histórico", 1, 5, 2)
data_inicio = datetime.now() - timedelta(days=365 * anos_historico)
data_fim = datetime.now().strftime("%Y-%m-%d")

rf_anual = st.sidebar.number_input(
    "Taxa livre de risco anual (%) — ex: CDI",
    min_value=0.0, max_value=30.0, value=10.5, step=0.5,
) / 100

calcular = st.sidebar.button("🔄 Calcular carteira", type="primary", use_container_width=True)

# ------------------------------------------------------------------
# VALIDAÇÃO E PREPARO DOS DADOS
# ------------------------------------------------------------------
tabela_carteira = tabela_carteira.dropna(subset=["Ticker", "Valor Investido (R$)"])
tabela_carteira = tabela_carteira[tabela_carteira["Ticker"].str.strip() != ""]
tabela_carteira["Ticker"] = tabela_carteira["Ticker"].apply(normalizar_ticker)

if tabela_carteira.empty:
    st.warning("Adicione pelo menos um ativo na barra lateral para começar.")
    st.stop()

dic_carteira = dict(zip(tabela_carteira["Ticker"], tabela_carteira["Valor Investido (R$)"]))
acoes = list(dic_carteira.keys())
tickers_benchmark = [BENCHMARKS_DISPONIVEIS[b] for b in benchmarks_escolhidos]
lista_tickers = list(set(acoes + tickers_benchmark + ["^BVSP"]))  # ^BVSP sempre entra p/ cálculo de Beta

with st.spinner("Buscando cotações..."):
    try:
        df_cotacoes = pegar_cotacoes(lista_tickers, data_inicio, data_fim)
    except Exception as e:
        st.error(f"Não foi possível baixar as cotações. Verifique os tickers digitados. Detalhe: {e}")
        st.stop()

tickers_invalidos = [t for t in acoes if t not in df_cotacoes.columns]
if tickers_invalidos:
    st.error(f"Ticker(s) não encontrado(s): {', '.join(tickers_invalidos)}. Corrija na tabela.")
    st.stop()

# ------------------------------------------------------------------
# CÁLCULO DA CARTEIRA
# ------------------------------------------------------------------
df_carteira = pd.DataFrame(index=df_cotacoes.index)
for ativo, valor in dic_carteira.items():
    preco_inicial = df_cotacoes[ativo].iloc[0]
    qtd_acoes = valor / preco_inicial
    df_carteira[ativo] = df_cotacoes[ativo] * qtd_acoes
df_carteira["Total"] = df_carteira.sum(axis=1)

total_investido = sum(dic_carteira.values())
valor_atual = df_carteira["Total"].iloc[-1]
retorno_total = (valor_atual / total_investido - 1) * 100

# ------------------------------------------------------------------
# TOPO — MÉTRICAS RESUMO (dashboard)
# ------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total investido", f"R$ {total_investido:,.2f}")
col2.metric("📈 Valor atual", f"R$ {valor_atual:,.2f}", f"{retorno_total:.2f}%")
col3.metric("📅 Período analisado", f"{anos_historico} ano(s)")

st.divider()

# ------------------------------------------------------------------
# ABAS
# ------------------------------------------------------------------
aba1, aba2, aba3, aba4 = st.tabs(
    ["🥧 Composição", "📈 Comparação com o mercado", "🔬 Análise de Risco", "🕯️ Análise Técnica"]
)

# ---- ABA 1: COMPOSIÇÃO ----
with aba1:
    st.subheader("Composição da carteira")
    df_pizza = pd.DataFrame({"Ativo": list(dic_carteira.keys()), "Valor": list(dic_carteira.values())})
    grafico_pizza = px.pie(df_pizza, names="Ativo", values="Valor", hole=0.4)
    grafico_pizza.update_layout(template="plotly_dark")
    st.plotly_chart(grafico_pizza, use_container_width=True)

    with st.expander("📖 O que isso significa?"):
        st.write(
            "Esse gráfico mostra o peso (%) de cada ativo dentro do total investido. "
            "Uma carteira muito concentrada em um único ativo tende a ser mais arriscada."
            "Quanto maior a diversificação, menor o risco"
        )

# ---- ABA 2: COMPARAÇÃO ----
with aba2:
    st.subheader("Rentabilidade da carteira vs. mercado")

    df_comp = pd.DataFrame(index=df_cotacoes.index)
    df_comp["Carteira"] = df_carteira["Total"]

    for nome in benchmarks_escolhidos:
        ticker = BENCHMARKS_DISPONIVEIS[nome]
        if nome in ["S&P 500 (em R$)", "Ouro (em R$)"]:
            df_comp[nome] = df_cotacoes[ticker] * df_cotacoes["BRL=X"] if "BRL=X" in df_cotacoes.columns else df_cotacoes[ticker]
        else:
            df_comp[nome] = df_cotacoes[ticker]

    df_comp = df_comp.dropna()
    df_comp_normalizado = (df_comp / df_comp.iloc[0] - 1) * 100

    grafico = px.line(df_comp_normalizado, x=df_comp_normalizado.index, y=df_comp_normalizado.columns,
                       labels={"value": "Retorno (%)", "index": "Data", "variable": "Ativo"})
    grafico.update_layout(template="plotly_dark", legend_title_text="")
    st.plotly_chart(grafico, use_container_width=True)

    with st.expander("📖  O que isso significa?"):
        st.write(
            "Todas as séries começam em 0% para ficar fácil comparar quem rendeu mais no período, "
            "independentemente do preço de cada ativo."
        )

# ---- ABA 3: RISCO ----
with aba3:
    st.subheader("Correlação entre os ativos")
    df_risco = df_cotacoes[acoes + ["^BVSP"]].copy()
    df_risco["Carteira"] = df_carteira["Total"]
    retornos_log = np.log(df_risco / df_risco.shift(1)).dropna()

    tabela_correlacao = retornos_log.corr()
    grafico_corr = px.imshow(tabela_correlacao, text_auto=".2f", color_continuous_scale="Greens")
    grafico_corr.update_layout(template="plotly_dark")
    st.plotly_chart(grafico_corr, use_container_width=True)

    with st.expander("📖  O que isso significa?"):
        st.write(
            "Valores perto de 1 indicam que os ativos se movem juntos (pouca diversificação real). "
            "Valores perto de 0 ou negativos indicam que um ativo pode compensar o outro."
        )

    st.subheader("Indicadores de risco e retorno")

    volatilidade_anual = retornos_log.std() * np.sqrt(252)
    retorno_anual = retornos_log.mean() * 252
    sharpe = (retorno_anual - rf_anual) / volatilidade_anual
    beta_carteira = retornos_log["Carteira"].cov(retornos_log["^BVSP"]) / retornos_log["^BVSP"].var()
    dd_carteira = max_drawdown(df_carteira["Total"])

    df_indicadores = pd.DataFrame({
        "Volatilidade anual": volatilidade_anual.map("{:.1%}".format),
        "Retorno anual (médio)": retorno_anual.map("{:.1%}".format),
        "Sharpe Ratio": sharpe.round(2),
    })
    st.dataframe(df_indicadores, use_container_width=True)

    colr1, colr2 = st.columns(2)
    colr1.metric("Beta da carteira (vs. Ibovespa)", f"{beta_carteira:.2f}")
    colr2.metric("Drawdown máximo da carteira", f"{dd_carteira:.1%}")

    with st.expander("📖 O que significam esses indicadores?"):
        st.markdown(
            """
- **Volatilidade anual**: o quanto o ativo costuma oscilar por ano. Quanto maior, mais arriscado.
- **Sharpe Ratio**: retorno obtido para cada unidade de risco assumida. Acima de 1 é considerado bom.
- **Beta**: sensibilidade da carteira em relação ao Ibovespa. Beta > 1 significa que ela oscila mais que o mercado.
- **Drawdown máximo**: a maior queda que a carteira teve do topo até o fundo no período analisado.
            """
        )

# ---- ABA 4: ANÁLISE TÉCNICA ----
with aba4:
    st.subheader("Análise técnica por ativo")
    ativo_selecionado = st.selectbox("Escolha um ativo da sua carteira:", acoes)

    with st.spinner("Calculando indicadores técnicos..."):
        df_tecnico = yf.download(ativo_selecionado, start=data_inicio, end=data_fim,
                                  multi_level_index=False, progress=False)
        df_tecnico = calcular_indicadores_tecnicos(df_tecnico)

    grafico_candle = go.Figure()
    grafico_candle.add_trace(go.Candlestick(
        x=df_tecnico.index, open=df_tecnico["Open"], close=df_tecnico["Close"],
        high=df_tecnico["High"], low=df_tecnico["Low"], name="Preço"
    ))
    grafico_candle.add_trace(go.Scatter(x=df_tecnico.index, y=df_tecnico["MM50"], name="Média 50d", line={"color": "cyan", "width": 1}))
    grafico_candle.add_trace(go.Scatter(x=df_tecnico.index, y=df_tecnico["MM200"], name="Média 200d", line={"color": "orange", "width": 1}))
    grafico_candle.add_trace(go.Scatter(x=df_tecnico.index, y=df_tecnico["BB_Superior"], name="Bollinger Sup.", line={"color": "gray", "width": 1, "dash": "dot"}))
    grafico_candle.add_trace(go.Scatter(x=df_tecnico.index, y=df_tecnico["BB_Inferior"], name="Bollinger Inf.", line={"color": "gray", "width": 1, "dash": "dot"}))
    grafico_candle.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
    st.plotly_chart(grafico_candle, use_container_width=True)

    col_rsi, col_macd = st.columns(2)
    with col_rsi:
        grafico_rsi = px.line(df_tecnico, x=df_tecnico.index, y="RSI", title="RSI (14 dias)")
        grafico_rsi.add_hline(y=70, line_dash="dash", line_color="red")
        grafico_rsi.add_hline(y=30, line_dash="dash", line_color="green")
        grafico_rsi.update_layout(template="plotly_dark")
        st.plotly_chart(grafico_rsi, use_container_width=True)

    with col_macd:
        grafico_macd = px.line(df_tecnico, x=df_tecnico.index, y=["MACD", "MACD_Signal"], title="MACD")
        grafico_macd.update_layout(template="plotly_dark")
        st.plotly_chart(grafico_macd, use_container_width=True)

    with st.expander("📖 O que significam esses indicadores?"):
        st.markdown(
            """
- **Médias móveis (50 e 200)**: suavizam o preço para mostrar a tendência. Quando a MM50 cruza a MM200 para cima, é chamado de "cruzamento dourado" (sinal de alta).
- **Bandas de Bollinger**: faixa de volatilidade em torno do preço. Preço encostando na banda superior/inferior pode indicar sobrecompra/sobrevenda.
- **RSI**: mede força do movimento entre 0 e 100. Acima de 70 costuma indicar sobrecompra; abaixo de 30, sobrevenda.
- **MACD**: mostra mudanças de momentum. Cruzamentos entre a linha MACD e a linha de sinal são usados como sinais de entrada/saída.
            """
        )

st.divider()
st.caption("Dados via Yahoo Finance (yfinance). Construído para uso educacional — NÃO é recomendação de investimento.")
