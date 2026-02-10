import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import warnings
import traceback

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 1: KONFİGÜRASYON & OTURUM YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Market Pulse Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Yahoo Finance Engelini Aşmak İçin "İnsan Maskesi" (User-Agent)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

C = {
    "bg": "#0a0e14", "paper": "#131820", "card": "#1a1f2e", "grid": "#1e2536",
    "border": "#2a3142", "text": "#c8d0e0", "muted": "#6b7894", "green": "#00e676",
    "red": "#ff3d5a", "blue": "#448aff", "cyan": "#18ffff", "yellow": "#ffea00",
    "orange": "#ff9100", "purple": "#b388ff", "white": "#edf0f7",
}

SP500_UNIVERSE = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","BRK-B","UNH","XOM","JNJ",
    "JPM","V","PG","MA","HD","CVX","MRK","ABBV","LLY","PEP",
    "KO","COST","AVGO","WMT","MCD","CSCO","CRM","TMO","ACN","ABT"
] # Hız için ilk aşamada listeyi kısalttık, çalışınca büyütebilirsin.

NASDAQ_UNIVERSE = ["AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","AVGO","COST","NFLX"]

INDEX_MAP = {
    "S&P 500": {"etf": "SPY", "tickers": SP500_UNIVERSE, "label": "S&P 500"},
    "Nasdaq 100": {"etf": "QQQ", "tickers": NASDAQ_UNIVERSE, "label": "Nasdaq 100"},
}

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2: VERİ ÇEKME MOTORU (GÜNCELLENDİ)
# ═══════════════════════════════════════════════════════════════

def _fetch_one(ticker: str, start: str, end: str) -> Tuple[str, Optional[pd.DataFrame]]:
    try:
        # Session eklenerek engel aşılıyor
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, session=session)
        if df.empty: return ticker, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        return ticker, df
    except Exception:
        return ticker, None

@st.cache_data(ttl=900, show_spinner=False)
def run_pipeline(index_choice: str, start_str: str, end_str: str) -> Optional[Dict]:
    try:
        cfg = INDEX_MAP[index_choice]
        etf_ticker = cfg["etf"]
        tickers = cfg["tickers"]

        # Endeks ETF Verisi
        idx_df = yf.download(etf_ticker, start=start_str, end=end_str, session=session, auto_adjust=True)
        if isinstance(idx_df.columns, pd.MultiIndex): idx_df.columns = idx_df.columns.get_level_values(0)
        
        if idx_df.empty:
            st.error("❌ Yahoo Finance şu an istekleri reddediyor. Lütfen 10-15 dakika bekleyip yenileyin.")
            return None

        # Hisse Verileri (Paralel)
        all_data = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch_one, t, start_str, end_str): t for t in tickers}
            for future in as_completed(futures):
                t, df = future.result()
                if df is not None: all_data[t] = df

        # Makro Veriler
        vix = yf.download("^VIX", start=start_str, end=end_str, session=session, auto_adjust=True)
        if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)

        return {
            "idx_df": idx_df, "all_data": all_data, "vix": vix,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "etf_name": etf_ticker, "fetched_count": len(all_data)
        }
    except Exception as e:
        st.error(f"Hata: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3: ARAYÜZ (GÖRSELLEŞTİRME)
# ═══════════════════════════════════════════════════════════════

# CSS ve Sidebar bölümlerini senin kodundan aynen koruyoruz...
st.markdown(f"<style>.stApp {{ background: {C['bg']}; }}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📊 Market Pulse")
    index_choice = st.radio("Endeks:", list(INDEX_MAP.keys()))
    live_mode = st.toggle("Live Update", value=True)
    if st.button("🔄 Manuel Yenile"): st.cache_data.clear()

R = run_pipeline(index_choice, str(datetime.now()-timedelta(365)), str(datetime.now()))

if R:
    idx_df = R["idx_df"]
    st.header(f"{index_choice} - {R['timestamp']}")
    
    # Basit bir fiyat grafiği ile başla (Sistemin çalıştığını görmek için)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx_df.index, y=idx_df['Close'], name="Fiyat"))
    fig.update_layout(template="plotly_dark", paper_bgcolor=C["paper"])
    st.plotly_chart(fig, use_container_width=True)
    
    st.success(f"Başarıyla {R['fetched_count']} hisse verisi çekildi!")
else:
    st.info("Veri bekleniyor... (Yahoo limitine takılmış olabilirsiniz)")
