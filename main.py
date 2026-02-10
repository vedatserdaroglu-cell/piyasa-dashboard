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
import traceback

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

# Hız ve stabilite için listeyi optimize ettik
SP500_UNIVERSE = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","BRK-B","UNH","XOM","JNJ",
    "JPM","V","PG","MA","HD","CVX","MRK","ABBV","LLY","PEP",
    "KO","COST","AVGO","WMT","MCD","CSCO","CRM","TMO","ACN","ABT"
]

NASDAQ_UNIVERSE = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","TSLA","AVGO","COST","NFLX",
    "AMD","ADBE","TXN","QCOM","AMGN","ISRG","INTC","INTU","PYPL","MU"
]

INDEX_MAP = {
    "S&P 500": {"etf": "SPY", "tickers": SP500_UNIVERSE, "label": "S&P 500"},
    "Nasdaq 100": {"etf": "QQQ", "tickers": NASDAQ_UNIVERSE, "label": "Nasdaq 100"},
}

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2: VERİ ÇEKME YARDIMCI FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Yahooquery formatını standart formata çevirir."""
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    # Sütun isimlerini düzelt (close -> Close vb.)
    rename_map = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'adj_close': 'Close', 'volume': 'Volume'
    }
    df.rename(columns=rename_map, inplace=True)
    # Sadece gerekli sütunları tut
    cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
    return df[cols]

def fetch_data_batch(tickers: List[str], start: datetime, end: datetime) -> Dict[str, pd.DataFrame]:
    """Yahooquery ile toplu veri çeker."""
    try:
        t = Ticker(tickers, asynchronous=True)
        df = t.history(start=start, end=end)
        
        results = {}
        if isinstance(df, pd.DataFrame) and not df.empty:
            # Yahooquery multi-index döner: (symbol, date)
            for ticker in tickers:
                try:
                    if ticker in df.index.get_level_values(0):
                        temp = df.xs(ticker, level=0)
                        temp = normalize_df(temp)
                        if not temp.empty:
                            results[ticker] = temp
                except:
                    continue
        return results
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        return {}

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3: HESAPLAMA MANTIKLARI (Önceki kodunla uyumlu)
# ═══════════════════════════════════════════════════════════════

def calc_distribution_days(idx_df: pd.DataFrame, lookback: int = 25) -> pd.DataFrame:
    df = idx_df.copy()
    df["PctChg"] = df["Close"].pct_change() * 100
    df["VolChg"] = df["Volume"].pct_change()
    df["IsDistDay"] = (df["PctChg"] <= -0.2) & (df["VolChg"] > 0)
    df["DistCount25"] = df["IsDistDay"].rolling(window=lookback, min_periods=1).sum()
    return df

def calc_advance_decline(all_data: Dict[str, pd.DataFrame], date_range: pd.DatetimeIndex) -> pd.DataFrame:
    returns = {t: df["Close"].pct_change() for t, df in all_data.items()}
    records = []
    for date in date_range:
        adv, dec = 0, 0
        for t, ret_series in returns.items():
            if date in ret_series.index:
                val = ret_series.loc[date]
                if val > 0: adv += 1
                elif val < 0: dec += 1
        records.append({"Date": date, "Advances": adv, "Declines": dec, "NetAD": adv - dec})
    ad = pd.DataFrame(records).set_index("Date")
    ad["AD_Line"] = ad["NetAD"].cumsum()
    return ad

# ... (Diğer hesaplama fonksiyonları basitleştirilerek eklendi) ...

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4: ANA PİPELİNE
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=900)
def run_pipeline(index_choice, start_date, end_date):
    cfg = INDEX_MAP[index_choice]
    
    # 1. Ana Endeks Verisi
    idx_dict = fetch_data_batch([cfg["etf"]], start_date, end_date)
    idx_df = idx_dict.get(cfg["etf"])
    
    if idx_df is None or idx_df.empty:
        return None

    # 2. Evren Verisi
    all_data = fetch_data_batch(cfg["tickers"], start_date, end_date)
    
    # 3. Makro Veriler
    macro_data = fetch_data_batch(["^VIX", "^TNX", "^IRX"], start_date, end_date)
    
    # Hesaplamalar
    dist_df = calc_distribution_days(idx_df)
    ad_df = calc_advance_decline(all_data, idx_df.index)
    
    return {
        "idx_df": idx_df,
        "dist": dist_df,
        "ad": ad_df,
        "vix": macro_data.get("^VIX"),
        "count": len(all_data),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

# ═══════════════════════════════════════════════════════════════
# BÖLÜM 5: ARAYÜZ (UI)
# ═══════════════════════════════════════════════════════════════

st.markdown(f"""<style>.stApp {{ background: {C["bg"]}; color: {C["text"]}; }}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("📊 Market Pulse")
    index_choice = st.radio("Endeks:", list(INDEX_MAP.keys()))
    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()

start_date = datetime.now() - timedelta(days=365)
end_date = datetime.now()

with st.spinner("Piyasa verileri çekiliyor..."):
    R = run_pipeline(index_choice, start_date, end_date)

if R:
    st.success(f"Bağlantı Başarılı! {R['count']} hisse analiz edildi. (Son Güncelleme: {R['timestamp']})")
    
    col1, col2, col3 = st.columns(3)
    idx_df = R["idx_df"]
    
    with col1:
        st.metric("Fiyat", f"{idx_df['Close'].iloc[-1]:.2f}")
    with col2:
        dist_val = int(R["dist"]["DistCount25"].iloc[-1])
        st.metric("Dist. Days", dist_val, delta=-dist_val, delta_color="inverse")
    with col3:
        if R["vix"] is not None:
            st.metric("VIX", f"{R['vix']['Close'].iloc[-1]:.2f}")

    # Ana Grafik
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=idx_df.index, y=idx_df['Close'], name=index_choice, line=dict(color=C["blue"])))
    fig.update_layout(template="plotly_dark", paper_bgcolor=C["paper"], plot_bgcolor=C["bg"])
    st.plotly_chart(fig, use_container_width=True)

    # A/D Line Grafiği
    fig_ad = go.Figure()
    fig_ad.add_trace(go.Scatter(x=R["ad"].index, y=R["ad"]["AD_Line"], name="A/D Line", line=dict(color=C["cyan"])))
    fig_ad.update_layout(title="Advance-Decline Line", template="plotly_dark", paper_bgcolor=C["paper"])
    st.plotly_chart(fig_ad, use_container_width=True)

else:
    st.error("Veri alınamadı. Yahoo Finance geçici olarak erişimi engellemiş olabilir.")
