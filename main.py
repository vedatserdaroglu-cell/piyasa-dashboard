import streamlit as st
import pandas as pd
import numpy as np
from yahooquery import Ticker
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import warnings

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1: KONFİGÜRASYON & SABİTLER
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Market Pulse Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

C = {
    "bg": "#0a0e14", "paper": "#131820", "card": "#1a1f2e", "grid": "#1e2536",
    "border": "#2a3142", "text": "#c8d0e0", "muted": "#6b7894", "green": "#00e676",
    "red": "#ff3d5a", "blue": "#448aff", "cyan": "#18ffff", "yellow": "#ffea00",
    "orange": "#ff9100", "purple": "#b388ff", "white": "#edf0f7",
}

# Ticker Listeleri (Stabilite için optimize edildi)
SP500_UNIVERSE = ["AAPL","MSFT","AMZN","NVDA","GOOGL","META","BRK-B","UNH","XOM","JNJ","JPM","V","PG","MA","HD","CVX","MRK","ABBV","LLY","PEP"]
NASDAQ_UNIVERSE = ["AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","AVGO","COST","NFLX","AMD","ADBE","TXN","QCOM","AMGN"]

INDEX_MAP = {
    "S&P 500": {"etf": "SPY", "tickers": SP500_UNIVERSE, "label": "S&P 500"},
    "Nasdaq 100": {"etf": "QQQ", "tickers": NASDAQ_UNIVERSE, "label": "Nasdaq 100"},
}

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2: VERİ ÇEKME MOTORU (YAHOOQUERY)
# ═══════════════════════════════════════════════════════════════

def fetch_data_safe(tickers, start, end):
    try:
        t = Ticker(tickers, asynchronous=True)
        df = t.history(start=start, end=end)
        results = {}
        if isinstance(df, pd.DataFrame) and not df.empty:
            for ticker in tickers:
                if ticker in df.index.get_level_values(0):
                    temp = df.xs(ticker, level=0).copy()
                    temp.rename(columns={'adj_close': 'Close', 'close': 'Close_Raw', 'volume': 'Volume'}, inplace=True)
                    if 'Close' not in temp.columns: temp['Close'] = temp['Close_Raw']
                    results[ticker] = temp[['Close', 'Volume']]
        return results
    except: return {}

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3: HESAPLAMA FONKSİYONLARI (COPPOCK, ZBT, BREADTH)
# ═══════════════════════════════════════════════════════════════

def calc_indicators(idx_df, all_data):
    # 1. Distribution Days
    df = idx_df.copy()
    df["PctChg"] = df["Close"].pct_change() * 100
    df["IsDistDay"] = (df["PctChg"] <= -0.2) & (df["Volume"] > df["Volume"].shift(1))
    df["DistCount25"] = df["IsDistDay"].rolling(25).sum()

    # 2. Advance-Decline Line
    returns = {t: d["Close"].pct_change() for t, d in all_data.items()}
    ad_records = []
    for date in idx_df.index:
        adv, dec = 0, 0
        for t, ret in returns.items():
            if date in ret.index:
                if ret.loc[date] > 0: adv += 1
                elif ret.loc[date] < 0: dec += 1
        ad_records.append({"Date": date, "NetAD": adv - dec})
    ad_df = pd.DataFrame(ad_records).set_index("Date")
    ad_df["AD_Line"] = ad_df["NetAD"].cumsum()

    # 3. McClellan Oscillator
    ad_df["EMA19"] = ad_df["NetAD"].ewm(span=19, adjust=False).mean()
    ad_df["EMA39"] = ad_df["NetAD"].ewm(span=39, adjust=False).mean()
    ad_df["McClellan"] = ad_df["EMA19"] - ad_df["EMA39"]

    # 4. Coppock Curve (Aylık)
    m_df = idx_df["Close"].resample("ME").last()
    roc14, roc11 = m_df.pct_change(14)*100, m_df.pct_change(11)*100
    w = np.arange(1, 11)
    coppock = (roc14 + roc11).rolling(10).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)

    return df, ad_df, coppock

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4: ANA PİPELİNE VE UI
# ═══════════════════════════════════════════════════════════════

st.markdown(f"<style>.stApp {{ background:{C['bg']}; color:{C['text']}; }}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"## 📊 Market Pulse")
    index_choice = st.radio("Endeks Seçimi:", list(INDEX_MAP.keys()))
    if st.button("🔄 Verileri Yenile"): st.cache_data.clear()

@st.cache_data(ttl=900)
def get_full_analysis(choice):
    cfg = INDEX_MAP[choice]
    start = datetime.now() - timedelta(days=500)
    data = fetch_data_safe([cfg["etf"]] + cfg["tickers"] + ["^VIX"], start, datetime.now())
    
    if cfg["etf"] not in data: return None
    
    idx_df = data.pop(cfg["etf"])
    vix_df = data.pop("^VIX", None)
    dist, ad, cop = calc_indicators(idx_df, data)
    
    return {"idx": idx_df, "dist": dist, "ad": ad, "cop": cop, "vix": vix_df, "count": len(data)}

R = get_full_analysis(index_choice)

if R:
    # --- Üst Metrikler ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(index_choice, f"{R['idx']['Close'].iloc[-1]:.2f}")
    with m2: st.metric("Dist. Days (25G)", int(R['dist']['DistCount25'].iloc[-1]))
    with m3: 
        if R['vix'] is not None: st.metric("VIX", f"{R['vix']['Close'].iloc[-1]:.2f}")
    with m4: st.metric("Analiz Edilen", f"{R['count']} Hisse")

    # --- TABLAR ---
    t1, t2, t3 = st.tabs(["📈 Ana Görünüm", "🔍 IBD & Breadth", "🚀 Uzun Vadeli (Coppock)"])

    with t1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Scatter(x=R['idx'].index, y=R['idx']['Close'], name="Fiyat", line=dict(color=C['blue'])), row=1, col=1)
        fig.add_trace(go.Scatter(x=R['ad'].index, y=R['ad']['AD_Line'], name="A/D Line", line=dict(color=C['cyan'])), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, paper_bgcolor=C['paper'])
        st.plotly_chart(fig, use_container_width=True)

    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Distribution Days")
            fig_dist = go.Figure(go.Bar(x=R['dist'].index, y=R['dist']['DistCount25'], marker_color=C['red']))
            fig_dist.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_dist, use_container_width=True)
        with c2:
            st.subheader("McClellan Oscillator")
            fig_mc = go.Figure(go.Bar(x=R['ad'].index, y=R['ad']['McClellan'], marker_color=C['green']))
            fig_mc.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_mc, use_container_width=True)

    with t3:
        st.subheader("Coppock Curve (Aylık Momentum)")
        fig_cop = go.Figure(go.Scatter(x=R['cop'].index, y=R['cop'], fill='tozeroy', name="Coppock"))
        fig_cop.add_hline(y=0, line_color="white")
        fig_cop.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_cop, use_container_width=True)
        st.info("💡 Sıfır seviyesinin altından yukarı dönüşler, tarihsel olarak büyük boğa piyasası diplerini işaret eder.")

else:
    st.error("⚠️ Veri çekme limiti veya bağlantı sorunu. Lütfen Sidebar'dan Yenile yapın.")
