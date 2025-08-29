import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots
from pathlib import Path


# Configuração da página

st.set_page_config(
    page_title="Evolução do Ethereum (2017–2025)",
    page_icon="🟣",
    layout="wide",
)

# CSS
st.markdown("""
<style>
/* Fonte um pouco menor e cards com sombra suave */
[data-testid="stMetricValue"] { font-weight: 700; }
.block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }
div[data-testid="stMetric"] { border-radius: 16px; padding: 10px 12px; background: #fafafa; box-shadow: 0 1px 8px rgba(0,0,0,0.06); }
hr { margin: 1.5rem 0; }
</style>
""", unsafe_allow_html=True)


# Funções utilitárias

@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Tipos corretos
    df["Open time"] = pd.to_datetime(df["Open time"], errors="coerce")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # Limpeza e índice
    df = (
        df.dropna(subset=["Open time", "Close"])
          .sort_values("Open time")
          .set_index("Open time")
    )
    return df

def safe_image(path: str, width: int = 900):
    p = Path(path)
    if p.exists():
        img = Image.open(p)
        st.image(img, width=width)
    else:
        st.info("Imagem de capa não encontrada. Você pode adicionar **ethereum.jpeg** na raiz do app.")

labels = {
    "Close":  "Preço de fechamento",
    "Open":   "Preço de abertura",
    "High":   "Máxima do período",
    "Low":    "Mínima do período",
    "Volume": "Volume negociado"
}


# Header

col_h1, col_h2 = st.columns([3, 2], vertical_alignment="center")
with col_h1:
    st.title("Dashboard • Gabriel Ferreira")
    st.header("Análise dos valores do Ethereum")
    st.caption("Série histórica 2017–2025 com filtros de período, métricas e visualizações técnicas.")
    st.caption("*Valores representados em USD. Dados de fonte pública (Kaggle).")
with col_h2:
    safe_image("ethereum.jpeg", width=480)


# Dados

df = load_data("eth_1d_data_2017_to_2025.csv")
if df.empty:
    st.error("Não foi possível carregar os dados.")
    st.stop()


# Sidebar com controles

st.sidebar.header("Controles")
periodicidade = st.sidebar.radio("Periodicidade", ["Dia", "Mês", "Ano"], horizontal=False, index=1)
metrica = st.sidebar.selectbox(
    "Métrica",
    options=list(labels.keys()),
    index=0,
    format_func=lambda k: labels[k]
)

min_d, max_d = df.index.min().date(), df.index.max().date()
dt_ini, dt_fim = st.sidebar.date_input(
    "Intervalo de datas",
    value=(min_d, max_d),
    min_value=min_d,
    max_value=max_d
)

df = df.loc[str(dt_ini):str(dt_fim)]
if df.empty:
    st.warning("Sem dados para o intervalo selecionado.")
    st.stop()

freq_map = {"Dia": "D", "Mês": "M", "Ano": "Y"}
freq = freq_map[periodicidade]
agg = "sum" if metrica == "Volume" else "last"
serie = df[metrica].resample(freq).agg(agg).dropna()
if serie.empty:
    st.warning("Sem dados para a métrica selecionada neste intervalo.")
    st.stop()

# KPIs (último valor, variação, volume médio)
with st.container():
    st.header("Valores de 2017 a 2025")
    c1, c2, c3 = st.columns(3)
    ultimo = serie.iloc[-1]
    primeiro = serie.iloc[0]
    var_pct = (ultimo - primeiro) / primeiro * 100 if primeiro != 0 else 0.0

    c1.metric(f"{labels[metrica]} (início)", f"US$ {primeiro:,.2f}" if metrica != "Volume" else f"{primeiro:,.0f}")
    c2.metric(f"{labels[metrica]} (fim)", f"US$ {ultimo:,.2f}" if metrica != "Volume" else f"{ultimo:,.0f}")
    c3.metric("Variação no período", f"{var_pct:,.2f}%")

st.divider()


# Abas principais

tab_evo, tab_candle, tab_outros = st.tabs(
    ["📈 Evolução", "🕯️ Candlestick anual", "🧮 Retornos / Correlação / Médias"]
)


# Aba 1 — Evolução (barras coloridas)

with tab_evo:
    st.subheader(f"{labels[metrica]} por {periodicidade.lower()}")
    delta = serie.diff()
    colors = np.where(delta > 0, "green", np.where(delta < 0, "red", "lightgray")).tolist()
    if len(colors): colors[0] = "lightgray"

    fig = go.Figure(
        go.Bar(
            x=serie.index,
            y=serie.values,
            marker_color=colors,
            hovertemplate="%{x}<br>"+labels[metrica]+": %{y}<extra></extra>"
        )
    )
    fig.update_layout(
        title=f"{labels[metrica]} por {periodicidade.lower()}",
        xaxis_title="Tempo",
        yaxis_title=labels[metrica],
        bargap=0.15,
        margin=dict(l=10, r=10, t=60, b=10),
        height=480,
        template="plotly_white",
    )
    if periodicidade == "Mês":
        fig.update_xaxes(tickformat="%Y-%m")
    elif periodicidade == "Dia":
        fig.update_xaxes(tickformat="%Y-%m-%d")
    else:
        fig.update_xaxes(tickformat="%Y")
    st.plotly_chart(fig, use_container_width=True)


# Aba 2 — Candlestick por ano

with tab_candle:
    st.subheader("Desempenho anual — Candlestick")
    anos = sorted(df.index.year.unique().tolist())
    ano_sel = st.selectbox("Selecione o ano", options=anos, index=len(anos)-1, key="ano_candle")

    df_year = df.loc[df.index.year == int(ano_sel)].copy()
    if df_year.empty or df_year["Close"].dropna().empty:
        st.warning("Não há dados de fechamento para o ano selecionado.")
    else:
        first_close = df_year["Close"].iloc[0]
        last_close  = df_year["Close"].iloc[-1]
        retorno_pct = (last_close - first_close) / first_close * 100 if first_close else 0.0

        k1, k2, k3 = st.columns(3)
        k1.metric("Fechamento (início do ano)", f"US$ {first_close:,.2f}")
        k2.metric("Fechamento (final do ano)", f"US$ {last_close:,.2f}")
        k3.metric("Variação no ano", f"{retorno_pct:,.2f}%")

        fig_c = go.Figure(data=[go.Candlestick(
            x=df_year.index,
            open=df_year["Open"],
            high=df_year["High"],
            low=df_year["Low"],
            close=df_year["Close"],
            increasing_line_color="green",
            decreasing_line_color="red",
            name="Candlestick"
        )])
        fig_c.update_layout(
            title=f"Candlestick {ano_sel}",
            xaxis_title="Data",
            yaxis_title="Preço",
            xaxis_rangeslider_visible=False,
            height=560,
            margin=dict(l=10, r=10, t=60, b=10),
            template="plotly_white"
        )
        st.plotly_chart(fig_c, use_container_width=True)


# Aba 3 — Retornos / Correlação / Médias móveis

with tab_outros:
    st.subheader("Retornos, Correlação e Tendência")
    sub1, sub2, sub3 = st.tabs(["Retorno % (volatilidade)", "Preço × Volume", "Médias móveis"])

    # 1) Retorno %
    with sub1:
        st.write("Resultado mensal de valorização/desvalorização.")
        close_m = df["Close"].resample("M").last().dropna()
        ret_m = close_m.pct_change() * 100
        if ret_m.dropna().empty:
            st.info("Sem dados suficientes para calcular retornos mensais.")
        else:
            colors = ["green" if v > 0 else "red" for v in ret_m.fillna(0)]
            fig_r = go.Figure(go.Bar(
                x=ret_m.index, y=ret_m.values, marker_color=colors,
                hovertemplate="%{x|%Y-%m}<br>Retorno: %{y:.2f}%<extra></extra>",
                name="Retorno mensal (%)"
            ))
            fig_r.update_layout(
                title="Retorno mensal (%)",
                xaxis_title="Mês", yaxis_title="Retorno (%)",
                height=440, margin=dict(l=10, r=10, t=60, b=10),
                template="plotly_white"
            )
            fig_r.update_xaxes(tickformat="%Y-%m")
            st.plotly_chart(fig_r, use_container_width=True)

    # 2) Preço × Volume
    with sub2:
        st.write("Preço (linha) e Volume (barras), com média de volume (30d).")
        vol_ma = df["Volume"].rolling(30, min_periods=1).mean()
        vol_delta = df["Volume"].diff()
        vol_colors = np.where(vol_delta > 0, "green", np.where(vol_delta < 0, "red", "lightgray")).tolist()
        if vol_colors: vol_colors[0] = "lightgray"

        fig_pv = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pv.add_trace(
            go.Scatter(x=df.index, y=df["Close"], mode="lines", line=dict(color="#1f77b4", width=2.6), name="Fechamento"),
            secondary_y=False
        )
        fig_pv.add_trace(
            go.Bar(
                x=df.index, y=df["Volume"], marker=dict(color=vol_colors), name="Volume",
                customdata=vol_delta.values,
                hovertemplate="%{x|%Y-%m-%d}<br>Volume: %{y:.0f}<br>Δ vs ant.: %{customdata:.0f}<extra></extra>"
            ),
            secondary_y=True
        )
        fig_pv.add_trace(
            go.Scatter(x=df.index, y=vol_ma, mode="lines", line=dict(color="#ff7f0e", width=1.3), name="Média Vol. (30d)"),
            secondary_y=True
        )
        fig_pv.update_layout(
            title="Preço (linha) + Volume (barras)",
            template="plotly_white",
            height=480,
            margin=dict(l=10, r=10, t=60, b=10),
            hovermode="x unified",
            bargap=0.05,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_pv.update_xaxes(title="Tempo", showgrid=True)
        fig_pv.update_yaxes(title_text="Preço (fechamento)", secondary_y=False, showgrid=True)
        fig_pv.update_yaxes(title_text="Volume", secondary_y=True, showgrid=False, rangemode="tozero")
        st.plotly_chart(fig_pv, use_container_width=True)

    # 3) Médias móveis
    with sub3:
        col_a, col_b = st.columns(2)
        with col_a:
            win_short = st.number_input("Janela da média curta (dias)", min_value=2, max_value=120, value=7, step=1)
        with col_b:
            win_long = st.number_input("Janela da média longa (dias)", min_value=3, max_value=240, value=30, step=1)

        if win_short >= win_long:
            st.warning("A janela curta deve ser menor que a janela longa.")
        else:
            mm_curta = df["Close"].rolling(int(win_short)).mean()
            mm_longa = df["Close"].rolling(int(win_long)).mean()

            fig_ma = go.Figure()
            fig_ma.add_trace(go.Scatter(
                x=df.index, y=df["Close"], mode="lines",
                name="Preço de fechamento", line=dict(color="gray", width=1.1),
                hovertemplate="%{x|%Y-%m-%d}<br>Fechamento: %{y:.2f}<extra></extra>"
            ))
            fig_ma.add_trace(go.Scatter(
                x=df.index, y=mm_curta, mode="lines",
                name=f"MM {int(win_short)}d", line=dict(color="royalblue", width=2)
            ))
            fig_ma.add_trace(go.Scatter(
                x=df.index, y=mm_longa, mode="lines",
                name=f"MM {int(win_long)}d", line=dict(color="orange", width=2)
            ))

            cross_up = (mm_curta.shift(1) < mm_longa.shift(1)) & (mm_curta >= mm_longa)
            cross_dn = (mm_curta.shift(1) > mm_longa.shift(1)) & (mm_curta <= mm_longa)
            fig_ma.add_trace(go.Scatter(
                x=df.index[cross_up.fillna(False)],
                y=mm_curta[cross_up.fillna(False)],
                mode="markers", marker=dict(size=8, symbol="triangle-up", color="green"),
                name="Cruzamento de alta"
            ))
            fig_ma.add_trace(go.Scatter(
                x=df.index[cross_dn.fillna(False)],
                y=mm_curta[cross_dn.fillna(False)],
                mode="markers", marker=dict(size=8, symbol="triangle-down", color="red"),
                name="Cruzamento de baixa"
            ))

            fig_ma.update_layout(
                title="Tendência com médias móveis",
                xaxis_title="Tempo",
                yaxis_title="Preço",
                height=480,
                margin=dict(l=10, r=10, t=60, b=10),
                template="plotly_white"
            )
            st.plotly_chart(fig_ma, use_container_width=True)
