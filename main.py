"""
main.py — Market Breadth & Trend Dashboard (Streamlit Cloud Edition)
=====================================================================
Kurumsal düzeyde piyasa sağlığı analiz aracı.
Tek dosyada tüm sistem: veri çekme, hesaplama, görselleştirme, export.

★ v3.0 — yahooquery backend:
  yfinance yerine yahooquery kullanır. yahooquery tek bir oturum üzerinden
  toplu (batch) istek gönderir, böylece Yahoo'nun rate-limit sorununu ortadan
  kaldırır. 100+ ticker tek bir Ticker() nesnesiyle çekilir.

Çalıştırmak için:
    streamlit run main.py

Deployment:
    1) GitHub repo'ya push et (main.py + requirements.txt + .streamlit/)
    2) share.streamlit.io → Deploy → repo/branch/main.py
    3) Canlı!
"""

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

# ─── Renk Paleti (Dark Theme) ───
C = {
    "bg":      "#0a0e14",
    "paper":   "#131820",
    "card":    "#1a1f2e",
    "grid":    "#1e2536",
    "border":  "#2a3142",
    "text":    "#c8d0e0",
    "muted":   "#6b7894",
    "green":   "#00e676",
    "red":     "#ff3d5a",
    "blue":    "#448aff",
    "cyan":    "#18ffff",
    "yellow":  "#ffea00",
    "orange":  "#ff9100",
    "purple":  "#b388ff",
    "white":   "#edf0f7",
}

# ─── Ticker Evrenleri ───
SP500_UNIVERSE = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","META","BRK-B","UNH","XOM","JNJ",
    "JPM","V","PG","MA","HD","CVX","MRK","ABBV","LLY","PEP",
    "KO","COST","AVGO","WMT","MCD","CSCO","CRM","TMO","ACN","ABT",
    "DHR","LIN","CMCSA","NKE","TXN","PM","NEE","RTX","HON","UNP",
    "AMGN","IBM","LOW","QCOM","SPGI","GE","BA","CAT","INTC","AMAT",
    "DE","ISRG","BKNG","ADP","MDLZ","GILD","ADI","SYK","MMC","PLD",
    "TJX","VRTX","LRCX","CB","CI","REGN","ZTS","BDX","SO","DUK",
    "SHW","BSX","MO","CL","CME","PNC","USB","SCHW","MS","GS",
    "MMM","FDX","GM","F","WBA","T","VZ","TMUS","CCI","AMT",
    "PSA","O","SPG","WELL","DLR","EQIX","EMR","APD","ECL","SRE",
]

NASDAQ_UNIVERSE = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","GOOG","META","AVGO","TSLA","COST",
    "ASML","AMD","NFLX","AZN","PEP","ADBE","LIN","CSCO","TXN","QCOM",
    "AMGN","ISRG","CMCSA","AMAT","BKNG","HON","INTC","INTU","LRCX","ADI",
    "VRTX","REGN","KLAC","MDLZ","ADP","SNPS","CDNS","PANW","PYPL","MRVL",
    "GILD","MNST","FTNT","CTAS","MAR","ORLY","ABNB","CSX","DXCM","NXPI",
]

INDEX_MAP = {
    "S&P 500": {"etf": "SPY", "tickers": SP500_UNIVERSE, "label": "S&P 500"},
    "Nasdaq 100": {"etf": "QQQ", "tickers": NASDAQ_UNIVERSE, "label": "Nasdaq 100"},
}


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 2: ÖZEL CSS STİLLERİ
# ═══════════════════════════════════════════════════════════════

st.markdown(f"""
<style>
    .stApp {{
        background: {C["bg"]};
    }}
    section[data-testid="stSidebar"] {{
        background: {C["paper"]};
        border-right: 1px solid {C["border"]};
    }}
    div[data-testid="stMetric"] {{
        background: linear-gradient(160deg, {C["card"]} 0%, {C["paper"]} 100%);
        border: 1px solid {C["border"]};
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.5);
    }}
    div[data-testid="stMetric"] label {{
        color: {C["muted"]} !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 1.7rem !important;
        font-weight: 800 !important;
        color: {C["white"]} !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: {C["paper"]};
        border-radius: 12px;
        padding: 5px;
        border: 1px solid {C["border"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 10px 22px;
        color: {C["muted"]};
        font-weight: 600;
        font-size: 0.88rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: {C["blue"]} !important;
        color: white !important;
    }}
    .health-banner {{
        padding: 22px 32px;
        border-radius: 16px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 900;
        letter-spacing: 1.5px;
        margin-bottom: 12px;
        border: 2px solid;
        backdrop-filter: blur(8px);
    }}
    .health-uptrend {{
        background: linear-gradient(135deg, rgba(0,230,118,0.08), rgba(0,230,118,0.02));
        border-color: {C["green"]};
        color: {C["green"]};
    }}
    .health-pressure {{
        background: linear-gradient(135deg, rgba(255,234,0,0.08), rgba(255,234,0,0.02));
        border-color: {C["yellow"]};
        color: {C["yellow"]};
    }}
    .health-correction {{
        background: linear-gradient(135deg, rgba(255,61,90,0.08), rgba(255,61,90,0.02));
        border-color: {C["red"]};
        color: {C["red"]};
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.4; }}
    }}
    .live-dot {{
        display: inline-block;
        width: 10px; height: 10px;
        background: {C["green"]};
        border-radius: 50%;
        animation: pulse 1.5s infinite;
        margin-right: 8px;
        vertical-align: middle;
    }}
    .gauge-container {{
        text-align: center;
        padding: 15px;
        background: {C["card"]};
        border-radius: 14px;
        border: 1px solid {C["border"]};
    }}
    .gauge-label {{
        font-size: 0.75rem;
        color: {C["muted"]};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }}
    .gauge-value {{
        font-size: 2.8rem;
        font-weight: 900;
        line-height: 1.1;
    }}
    .gauge-desc {{
        font-size: 0.95rem;
        font-weight: 700;
        margin-top: 2px;
    }}
    hr {{
        border-color: {C["border"]};
        margin: 16px 0;
    }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 3: HATA YÖNETİMİ
# ═══════════════════════════════════════════════════════════════

def safe_fetch(func):
    """
    Dekoratör: Veri çekme fonksiyonlarını try/except ile sarar.
    Bağlantı hatası, timeout veya veri hatası durumunda
    şık uyarı gösterir, sistemi çökertmez.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError:
            st.warning(
                f"⚠️ **Bağlantı Hatası** — `{func.__name__}`: "
                f"Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin.",
                icon="🌐"
            )
            return None
        except TimeoutError:
            st.warning(
                f"⏱️ **Zaman Aşımı** — `{func.__name__}` yanıt vermedi. "
                f"Birkaç dakika sonra tekrar deneyin.",
                icon="⏱️"
            )
            return None
        except Exception as e:
            st.error(
                f"❌ **Hata** — `{func.__name__}` → {type(e).__name__}: {str(e)[:200]}",
                icon="🔧"
            )
            return None
    return wrapper


def show_data_warning(indicator_name: str):
    """Veri yoksa kullanıcıya bilgi mesajı."""
    st.info(
        f"📭 **{indicator_name}** verisi alınamadı. Sonraki yenilemede tekrar denenecek.",
        icon="📭",
    )


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 4: VERİ ÇEKME MOTORU (yahooquery — BATCH API)
# ═══════════════════════════════════════════════════════════════
#
# ★ KRİTİK FARK: yfinance her ticker için ayrı HTTP isteği atar
#   (100 ticker = 100 istek → Yahoo rate limit).
#   yahooquery ise Ticker(["AAPL","MSFT",...]) ile TEK bir
#   oturum/session üzerinden toplu veri çeker. Rate limit yok.
#

def _yq_history_to_dict(
    raw_df: pd.DataFrame, tickers: List[str]
) -> Dict[str, pd.DataFrame]:
    """
    yahooquery'nin Ticker.history() çıktısını
    {ticker: DataFrame} dict'ine dönüştürür.

    yahooquery MultiIndex döndürür: (symbol, date).
    Bu fonksiyon her sembolü ayrı bir DataFrame olarak ayırır.
    """
    result = {}
    if raw_df is None or not isinstance(raw_df, pd.DataFrame) or raw_df.empty:
        return result

    # Index tipini kontrol et — MultiIndex(symbol, date) olmalı
    if isinstance(raw_df.index, pd.MultiIndex):
        for ticker in raw_df.index.get_level_values(0).unique():
            try:
                sub = raw_df.loc[ticker].copy()
                # Sütun isimlerini standartlaştır
                col_map = {}
                for col in sub.columns:
                    cl = col.lower()
                    if cl == "open": col_map[col] = "Open"
                    elif cl == "high": col_map[col] = "High"
                    elif cl == "low": col_map[col] = "Low"
                    elif cl in ("close", "adjclose"): col_map[col] = "Close"
                    elif cl == "volume": col_map[col] = "Volume"
                if col_map:
                    sub = sub.rename(columns=col_map)
                # Close sütunu olduğundan emin ol
                if "Close" not in sub.columns and "adjclose" in [c.lower() for c in sub.columns]:
                    for c in sub.columns:
                        if c.lower() == "adjclose":
                            sub = sub.rename(columns={c: "Close"})
                            break
                if "Close" in sub.columns and len(sub) > 0:
                    sub.index = pd.to_datetime(sub.index)
                    sub.index.name = "Date"
                    result[ticker] = sub
            except Exception:
                continue
    else:
        # Tek ticker gelmiş olabilir — index sadece date
        try:
            raw_df.index = pd.to_datetime(raw_df.index)
            col_map = {}
            for col in raw_df.columns:
                cl = col.lower()
                if cl == "open": col_map[col] = "Open"
                elif cl == "high": col_map[col] = "High"
                elif cl == "low": col_map[col] = "Low"
                elif cl in ("close", "adjclose"): col_map[col] = "Close"
                elif cl == "volume": col_map[col] = "Volume"
            if col_map:
                raw_df = raw_df.rename(columns=col_map)
            if "Close" in raw_df.columns:
                # Tek ticker olduğu için tickers[0] kullan
                if len(tickers) == 1:
                    result[tickers[0]] = raw_df
        except Exception:
            pass

    return result


@safe_fetch
def fetch_universe_batch(
    tickers: List[str], start: str, end: str
) -> Dict[str, pd.DataFrame]:
    """
    ★ ANA VERİ ÇEKME FONKSİYONU ★
    yahooquery.Ticker ile TÜM hisseleri TEK istekte çeker.
    100+ ticker → 1 batch request → rate limit riski yok.
    """
    # Ticker nesnesini oluştur (tüm semboller tek seferde)
    t = Ticker(
        tickers,
        asynchronous=True,     # Async HTTP — daha hızlı
        max_workers=8,         # Dahili paralellik
        progress=False,
    )

    # Geçmiş veriyi çek
    raw = t.history(start=start, end=end, adj_ohlc=True)

    # String dönerse hata var demektir
    if isinstance(raw, str):
        st.warning(f"⚠️ yahooquery uyarısı: {raw[:200]}")
        return {}

    return _yq_history_to_dict(raw, tickers)


@safe_fetch
def fetch_index_etf(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """Endeks ETF verisini (SPY/QQQ) tek ticker olarak çeker."""
    t = Ticker(ticker, asynchronous=False)
    raw = t.history(start=start, end=end, adj_ohlc=True)

    if isinstance(raw, str):
        st.warning(f"⚠️ {ticker} verisi alınamadı: {raw[:200]}")
        return None

    data = _yq_history_to_dict(raw, [ticker])
    return data.get(ticker)


@safe_fetch
def fetch_macro_instruments(start: str, end: str) -> Dict[str, Optional[pd.DataFrame]]:
    """
    VIX, 10Y Treasury, 13W Treasury verilerini TEK batch istekle çeker.
    yahooquery ^ prefix'li sembolleri de destekler.
    """
    symbols = ["^VIX", "^TNX", "^IRX"]
    label_map = {"^VIX": "VIX", "^TNX": "TNX", "^IRX": "IRX"}

    t = Ticker(symbols, asynchronous=True, max_workers=4, progress=False)
    raw = t.history(start=start, end=end, adj_ohlc=True)

    result = {"VIX": None, "TNX": None, "IRX": None}

    if isinstance(raw, str):
        return result

    data = _yq_history_to_dict(raw, symbols)
    for yq_sym, label in label_map.items():
        result[label] = data.get(yq_sym)

    return result


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 5: İNDİKATÖR HESAPLAMA FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════

# ─── 5a. IBD Distribution Days ───

def calc_distribution_days(idx_df: pd.DataFrame, lookback: int = 25) -> pd.DataFrame:
    """
    IBD Distribution Day: Fiyat >= %0.2 düşüş VE hacim önceki günden yüksek.
    Son 25 günde toplam kaç dağıtım günü (kayan pencere).
    """
    df = idx_df.copy()
    df["PctChg"] = df["Close"].pct_change() * 100
    df["VolChg"] = df["Volume"].pct_change()
    df["IsDistDay"] = (df["PctChg"] <= -0.2) & (df["VolChg"] > 0)
    df["DistCount25"] = df["IsDistDay"].rolling(window=lookback, min_periods=1).sum()
    return df


# ─── 5b. IBD Follow-Through Day ───

def calc_follow_through(idx_df: pd.DataFrame) -> pd.DataFrame:
    """Follow-Through Day: Rally 4+ gün, günlük >= %1.25, hacim artışı."""
    df = idx_df.copy()
    df["PctChg"] = df["Close"].pct_change() * 100
    df["ConsUp"] = 0
    count = 0
    for i in range(len(df)):
        count = count + 1 if df["PctChg"].iloc[i] > 0 else 0
        df.iloc[i, df.columns.get_loc("ConsUp")] = count
    df["IsFTD"] = (
        (df["ConsUp"] >= 4) &
        (df["PctChg"] >= 1.25) &
        (df["Volume"] > df["Volume"].shift(1))
    )
    return df


# ─── 5c. Advance-Decline Line ───

def calc_advance_decline(
    all_data: Dict[str, pd.DataFrame], date_range: pd.DatetimeIndex
) -> pd.DataFrame:
    """Günlük Advances/Declines ve kümülatif A/D Line."""
    # Önceden return serilerini hesapla
    returns = {}
    for ticker, df in all_data.items():
        returns[ticker] = df["Close"].pct_change()

    records = []
    for date in date_range:
        adv, dec = 0, 0
        for ticker, ret_s in returns.items():
            if date in ret_s.index:
                val = ret_s.get(date, np.nan)
                if pd.notna(val):
                    if val > 0: adv += 1
                    elif val < 0: dec += 1
        records.append({"Date": date, "Advances": adv, "Declines": dec, "NetAD": adv - dec})

    ad = pd.DataFrame(records).set_index("Date")
    ad["AD_Line"] = ad["NetAD"].cumsum()
    return ad


# ─── 5d. McClellan Oscillator ───

def calc_mcclellan(ad_df: pd.DataFrame) -> pd.DataFrame:
    """McClellan Oscillator = EMA19(NetAD) - EMA39(NetAD)"""
    df = ad_df.copy()
    df["EMA19"] = df["NetAD"].ewm(span=19, adjust=False).mean()
    df["EMA39"] = df["NetAD"].ewm(span=39, adjust=False).mean()
    df["McClellan"] = df["EMA19"] - df["EMA39"]
    df["McCSummation"] = df["McClellan"].cumsum()
    return df


# ─── 5e. % Stocks Above MA ───

def calc_pct_above_ma(
    all_data: Dict[str, pd.DataFrame], date_range: pd.DatetimeIndex, period: int
) -> pd.DataFrame:
    """Belirtilen MA üzerindeki hisse yüzdesi."""
    ma_cache = {}
    for ticker, df in all_data.items():
        ma_cache[ticker] = df["Close"].rolling(window=period, min_periods=period).mean()

    records = []
    for date in date_range:
        above, total = 0, 0
        for ticker, df in all_data.items():
            if date in df.index and ticker in ma_cache and date in ma_cache[ticker].index:
                price = df.loc[date, "Close"]
                ma = ma_cache[ticker].get(date, np.nan)
                if pd.notna(price) and pd.notna(ma):
                    total += 1
                    if price > ma:
                        above += 1
        pct = (above / total * 100) if total > 0 else np.nan
        records.append({"Date": date, f"PctAbove{period}": pct})

    return pd.DataFrame(records).set_index("Date")


# ─── 5f. Coppock Curve (Aylık) ───

def calc_coppock(idx_df: pd.DataFrame) -> pd.DataFrame:
    """Coppock Curve = 10-Aylık WMA(14-Ay ROC + 11-Ay ROC)"""
    monthly = idx_df["Close"].resample("ME").last().dropna()
    roc14 = monthly.pct_change(14) * 100
    roc11 = monthly.pct_change(11) * 100
    roc_sum = roc14 + roc11
    weights = np.arange(1, 11)
    coppock = roc_sum.rolling(10).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    return pd.DataFrame({"Close": monthly, "Coppock": coppock})


# ─── 5g. Zweig Breadth Thrust ───

def calc_zbt(ad_df: pd.DataFrame) -> pd.DataFrame:
    """ZBT: 10-gün EMA 0.40 altından 0.615 üzerine çıkarsa sinyal."""
    df = ad_df.copy()
    total = (df["Advances"] + df["Declines"]).replace(0, np.nan)
    df["ZBTRatio"] = df["Advances"] / total
    df["ZBTEMA"] = df["ZBTRatio"].ewm(span=10, adjust=False).mean()
    df["ZBTSignal"] = False
    for i in range(10, len(df)):
        window = df["ZBTEMA"].iloc[i-10:i+1]
        if window.min() < 0.40 and window.iloc[-1] > 0.615:
            df.iloc[i, df.columns.get_loc("ZBTSignal")] = True
    return df


# ─── 5h. 52-Week New Highs / Lows ───

def calc_new_highs_lows(
    all_data: Dict[str, pd.DataFrame], date_range: pd.DatetimeIndex, lookback: int = 252
) -> pd.DataFrame:
    """Her gün 52-haftalık yeni zirve/dip yapan hisse farkı."""
    records = []
    for date in date_range:
        nh, nl = 0, 0
        for ticker, df in all_data.items():
            if date not in df.index:
                continue
            idx = df.index.get_loc(date)
            if idx < lookback:
                continue
            window = df["Close"].iloc[idx - lookback : idx]
            current = df["Close"].iloc[idx]
            if len(window) > 0:
                if current >= window.max(): nh += 1
                if current <= window.min(): nl += 1
        records.append({"Date": date, "NewHighs": nh, "NewLows": nl, "Net": nh - nl})
    return pd.DataFrame(records).set_index("Date")


# ─── 5i. Yield Curve ───

def calc_yield_curve(macro: Dict[str, Optional[pd.DataFrame]]) -> Optional[pd.DataFrame]:
    """Yield Spread = 10Y Treasury - 13W Treasury"""
    tnx = macro.get("TNX")
    irx = macro.get("IRX")
    if tnx is None or irx is None:
        return None
    combined = pd.DataFrame({"Y10": tnx["Close"], "YShort": irx["Close"]}).dropna()
    if combined.empty:
        return None
    combined["Spread"] = combined["Y10"] - combined["YShort"]
    return combined


# ─── 5j. Fear & Greed Skoru ───

def calc_fear_greed_score(
    dist_count: int, pct50: float, pct200: float,
    mcclellan: float, vix: float, net_hl: float,
) -> Tuple[int, str, str]:
    """0-100 Fear & Greed skoru → (score, label, color)"""
    def norm(val, lo, hi, invert=False):
        s = max(0, min(100, (val - lo) / (hi - lo) * 100))
        return 100 - s if invert else s

    components = [
        norm(pct50, 0, 100),
        norm(pct200, 0, 100),
        norm(mcclellan, -150, 150),
        norm(dist_count, 0, 8, invert=True),
        norm(vix, 10, 45, invert=True),
        norm(net_hl, -40, 40),
    ]
    score = int(np.mean(components))

    if score >= 75:   return score, "Extreme Greed", C["green"]
    elif score >= 55: return score, "Greed", "#66bb6a"
    elif score >= 45: return score, "Neutral", C["yellow"]
    elif score >= 25: return score, "Fear", C["orange"]
    else:             return score, "Extreme Fear", C["red"]


# ─── 5k. Market Health Status ───

def determine_market_health(
    dist_count: int, pct50: float, pct200: float,
    mcclellan: float, vix: float,
) -> Tuple[str, str]:
    """IBD tarzı durum → (text, css_class)"""
    score = 0
    score += 2 if dist_count <= 3 else (1 if dist_count <= 5 else -2)
    score += 2 if pct50 > 60 else (1 if pct50 > 40 else -1)
    score += 2 if pct200 > 65 else (1 if pct200 > 45 else -1)
    score += 1 if mcclellan > 50 else (-1 if mcclellan < -50 else 0)
    score += 1 if vix < 15 else (-1 if vix > 25 else 0)
    if vix > 30:
        score -= 1

    if score >= 5:   return "CONFIRMED UPTREND", "health-uptrend"
    elif score >= 2: return "UPTREND UNDER PRESSURE", "health-pressure"
    else:            return "MARKET IN CORRECTION", "health-correction"


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 6: PLOTLY GRAFİK FONKSİYONLARI
# ═══════════════════════════════════════════════════════════════

def _dark_layout(fig: go.Figure, title: str = "", h: int = 420) -> go.Figure:
    """Tüm grafiklere ortak dark layout."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=C["text"]), x=0.01),
        template="plotly_dark",
        paper_bgcolor=C["paper"],
        plot_bgcolor=C["bg"],
        font=dict(color=C["text"], size=11),
        margin=dict(l=50, r=30, t=45, b=35),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor=C["border"], font=dict(size=10)),
        xaxis=dict(gridcolor=C["grid"], showgrid=True, gridwidth=0.5),
        yaxis=dict(gridcolor=C["grid"], showgrid=True, gridwidth=0.5),
        height=h,
    )
    return fig


def chart_price_with_breadth(idx_df, ad_df, idx_name):
    """Endeks fiyatı + A/D Line + McClellan overlay (3 panel)."""
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        row_heights=[0.50, 0.25, 0.25],
        subplot_titles=[
            f"{idx_name} Price + 50/200 DMA",
            "Advance-Decline Line",
            "McClellan Oscillator",
        ],
    )
    fig.add_trace(go.Scatter(
        x=idx_df.index, y=idx_df["Close"], name=idx_name,
        line=dict(color=C["blue"], width=1.8),
    ), row=1, col=1)

    ma50 = idx_df["Close"].rolling(50).mean()
    ma200 = idx_df["Close"].rolling(200).mean()
    fig.add_trace(go.Scatter(
        x=idx_df.index, y=ma50, name="50 DMA",
        line=dict(color=C["orange"], width=1, dash="dot"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=idx_df.index, y=ma200, name="200 DMA",
        line=dict(color=C["purple"], width=1, dash="dash"),
    ), row=1, col=1)

    if "AD_Line" in ad_df.columns:
        fig.add_trace(go.Scatter(
            x=ad_df.index, y=ad_df["AD_Line"], name="A/D Line",
            line=dict(color=C["cyan"], width=2),
        ), row=2, col=1)

    if "McClellan" in ad_df.columns:
        mc_colors = [C["green"] if v >= 0 else C["red"] for v in ad_df["McClellan"]]
        fig.add_trace(go.Bar(
            x=ad_df.index, y=ad_df["McClellan"], name="McClellan Osc.",
            marker_color=mc_colors, opacity=0.85,
        ), row=3, col=1)
        fig.add_hline(y=0, line_color=C["muted"], line_width=0.7, row=3, col=1)

    _dark_layout(fig, f"Canlı Görünüm — {idx_name} + Breadth Overlay", h=650)
    return fig


def chart_distribution(dist_df, name):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.6, 0.4], subplot_titles=[f"{name} Price", "Distribution Day Count"],
    )
    fig.add_trace(go.Scatter(
        x=dist_df.index, y=dist_df["Close"], name="Close",
        line=dict(color=C["blue"], width=1.5),
    ), row=1, col=1)
    dd = dist_df[dist_df["IsDistDay"]]
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd["Close"], mode="markers", name="Dist. Day",
        marker=dict(color=C["red"], size=7, symbol="triangle-down"),
    ), row=1, col=1)
    bar_colors = [C["red"] if v >= 5 else C["yellow"] if v >= 3 else C["green"]
                  for v in dist_df["DistCount25"]]
    fig.add_trace(go.Bar(
        x=dist_df.index, y=dist_df["DistCount25"], name="Count",
        marker_color=bar_colors, opacity=0.8,
    ), row=2, col=1)
    fig.add_hline(y=5, line_dash="dash", line_color=C["red"],
                  annotation_text="Danger (5+)", row=2, col=1)
    _dark_layout(fig, f"IBD Distribution Day Analysis — {name}", h=500)
    return fig


def chart_ftd(ftd_df, name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ftd_df.index, y=ftd_df["Close"], name="Close",
        line=dict(color=C["blue"], width=1.5),
    ))
    signals = ftd_df[ftd_df["IsFTD"]]
    fig.add_trace(go.Scatter(
        x=signals.index, y=signals["Close"], mode="markers", name="FTD",
        marker=dict(color=C["green"], size=12, symbol="star"),
    ))
    _dark_layout(fig, f"Follow-Through Day Detection — {name}")
    return fig


def chart_pct_above(p50, p200):
    fig = go.Figure()
    if "PctAbove50" in p50.columns:
        fig.add_trace(go.Scatter(
            x=p50.index, y=p50["PctAbove50"], name="% > 50 DMA",
            fill="tozeroy", fillcolor="rgba(68,138,255,0.12)",
            line=dict(color=C["blue"], width=2),
        ))
    if "PctAbove200" in p200.columns:
        fig.add_trace(go.Scatter(
            x=p200.index, y=p200["PctAbove200"], name="% > 200 DMA",
            fill="tozeroy", fillcolor="rgba(0,230,118,0.08)",
            line=dict(color=C["green"], width=2),
        ))
    fig.add_hline(y=50, line_dash="dash", line_color=C["muted"], line_width=0.7)
    fig.add_hline(y=70, line_dash="dot", line_color=C["green"], annotation_text="Bullish >70%")
    fig.add_hline(y=30, line_dash="dot", line_color=C["red"], annotation_text="Bearish <30%")
    _dark_layout(fig, "Market Participation — % Stocks Above DMA")
    fig.update_yaxes(range=[0, 100])
    return fig


def chart_coppock(cop_df):
    fig = go.Figure()
    vals = cop_df["Coppock"].dropna()
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    fig.add_trace(go.Bar(x=vals.index, y=vals, marker_color=colors, opacity=0.85, name="Coppock"))
    fig.add_hline(y=0, line_color=C["muted"], line_width=0.8)
    _dark_layout(fig, "Coppock Curve (Monthly) — Long-Term Momentum")
    return fig


def chart_zbt(zbt_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=zbt_df.index, y=zbt_df["ZBTEMA"], name="ZBT 10-EMA",
        line=dict(color=C["purple"], width=2),
    ))
    signals = zbt_df[zbt_df["ZBTSignal"]]
    if not signals.empty:
        fig.add_trace(go.Scatter(
            x=signals.index, y=signals["ZBTEMA"], mode="markers", name="Signal!",
            marker=dict(color=C["yellow"], size=14, symbol="star-diamond"),
        ))
    fig.add_hline(y=0.615, line_dash="dash", line_color=C["green"], annotation_text="Thrust (0.615)")
    fig.add_hline(y=0.40, line_dash="dash", line_color=C["red"], annotation_text="Oversold (0.40)")
    _dark_layout(fig, "Zweig Breadth Thrust Indicator")
    return fig


def chart_highslows(hl_df):
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Net (Highs - Lows)", "Breakdown"])
    colors = [C["green"] if v >= 0 else C["red"] for v in hl_df["Net"]]
    fig.add_trace(go.Bar(x=hl_df.index, y=hl_df["Net"], marker_color=colors, name="Net"), row=1, col=1)
    fig.add_trace(go.Bar(x=hl_df.index, y=hl_df["NewHighs"], marker_color=C["green"],
                         opacity=0.7, name="Highs"), row=1, col=2)
    fig.add_trace(go.Bar(x=hl_df.index, y=-hl_df["NewLows"], marker_color=C["red"],
                         opacity=0.7, name="Lows"), row=1, col=2)
    fig.add_hline(y=0, line_color=C["muted"], line_width=0.7, row=1, col=1)
    fig.add_hline(y=0, line_color=C["muted"], line_width=0.7, row=1, col=2)
    _dark_layout(fig, "52-Week New Highs vs New Lows", h=380)
    fig.update_layout(barmode="overlay")
    return fig


def chart_vix(vix_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=vix_df.index, y=vix_df["Close"], name="VIX",
        fill="tozeroy", fillcolor="rgba(255,61,90,0.08)",
        line=dict(color=C["orange"], width=2),
    ))
    fig.add_hline(y=20, line_dash="dash", line_color=C["yellow"], annotation_text="Elevated")
    fig.add_hline(y=30, line_dash="dash", line_color=C["red"], annotation_text="Fear")
    fig.add_hline(y=12, line_dash="dot", line_color=C["green"], annotation_text="Complacency")
    _dark_layout(fig, "CBOE Volatility Index (VIX)")
    return fig


def chart_yield(yc_df):
    if yc_df is None or yc_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Data unavailable", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="gray"))
        _dark_layout(fig, "Yield Curve Spread")
        return fig
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yc_df.index, y=yc_df["Spread"], name="10Y - Short Spread",
        fill="tozeroy", fillcolor="rgba(68,138,255,0.08)",
        line=dict(color=C["cyan"], width=2),
    ))
    fig.add_hline(y=0, line_color=C["red"], line_width=1.5, annotation_text="Inversion")
    _dark_layout(fig, "Yield Curve Spread (10Y - Short Rate)")
    return fig


def chart_radar(metrics: dict):
    cats = list(metrics.keys())
    vals = list(metrics.values())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself", fillcolor="rgba(68,138,255,0.15)",
        line=dict(color=C["blue"], width=2), name="Score",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=C["grid"]),
            bgcolor=C["bg"], angularaxis=dict(gridcolor=C["grid"]),
        ),
        paper_bgcolor=C["paper"], font=dict(color=C["text"]),
        title=dict(text="Market Health Radar", font=dict(size=14), x=0.5),
        height=400, showlegend=False,
    )
    return fig


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 7: EXCEL EXPORT
# ═══════════════════════════════════════════════════════════════

def generate_excel(data: dict) -> BytesIO:
    """Tüm sonuçları çok sekmeli Excel dosyasına yazar."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for sheet_name, df in data.items():
            if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                df.to_excel(w, sheet_name=sheet_name[:31])
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 8: ANA ANALİZ PİPELİNE (CACHED)
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=900, show_spinner=False)
def run_pipeline(index_choice: str, start_str: str, end_str: str) -> Optional[Dict]:
    """
    Tüm analizi çalıştırır. 15 dakika (ttl=900) cache.
    ★ yahooquery batch API ile veri çeker — rate limit yok.
    """
    try:
        cfg = INDEX_MAP[index_choice]
        etf_ticker = cfg["etf"]
        tickers = cfg["tickers"]

        # 1) Endeks ETF verisi (tek ticker)
        idx_df = fetch_index_etf(etf_ticker, start_str, end_str)
        if idx_df is None:
            st.error("❌ Endeks verisi alınamadı. Lütfen tekrar deneyin.")
            return None

        # 2) Tüm hisseleri TOPLU çek — tek batch request!
        all_data = fetch_universe_batch(tickers, start_str, end_str)
        if all_data is None or len(all_data) == 0:
            st.error("❌ Hisse verileri alınamadı.")
            return None

        date_range = idx_df.index

        # 3) İndikatörleri hesapla
        dist_df = calc_distribution_days(idx_df)
        ftd_df = calc_follow_through(idx_df)
        ad_df = calc_advance_decline(all_data, date_range)
        mc_df = calc_mcclellan(ad_df)
        p50 = calc_pct_above_ma(all_data, date_range, 50)
        p200 = calc_pct_above_ma(all_data, date_range, 200)
        cop = calc_coppock(idx_df)
        zbt = calc_zbt(mc_df)
        hl = calc_new_highs_lows(all_data, date_range)
        macro = fetch_macro_instruments(start_str, end_str)
        yc = calc_yield_curve(macro) if macro else None

        return {
            "idx_df": idx_df,
            "all_data": all_data,
            "dist": dist_df,
            "ftd": ftd_df,
            "ad": ad_df,
            "mc": mc_df,
            "p50": p50,
            "p200": p200,
            "coppock": cop,
            "zbt": zbt,
            "hl": hl,
            "macro": macro,
            "yc": yc,
            "etf_name": etf_ticker,
            "fetched_count": len(all_data),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        st.error(f"❌ Pipeline hatası: {type(e).__name__}: {str(e)[:300]}")
        st.code(traceback.format_exc(), language="python")
        return None


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 9: SIDEBAR KONTROLLERİ
# ═══════════════════════════════════════════════════════════════

_w = C["white"]
_m = C["muted"]
_t = C["text"]
_g = C["green"]

with st.sidebar:
    st.markdown(
        f"<h2 style='color:{_w};margin-bottom:0;'>📊 Market Pulse</h2>"
        f"<p style='color:{_m};font-size:0.85rem;'>Quant Dashboard v3.0 — yahooquery</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown(f"<p style='color:{_t};font-weight:700;'>🏛️ Endeks Seçimi</p>",
                unsafe_allow_html=True)
    index_choice = st.radio(
        "Analiz edilecek endeks:",
        list(INDEX_MAP.keys()),
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown(f"<p style='color:{_t};font-weight:700;'>📅 Tarih Aralığı</p>",
                unsafe_allow_html=True)
    period = st.selectbox(
        "Dönem", ["Son 6 Ay", "Son 1 Yıl", "Son 2 Yıl", "Özel Aralık"],
        index=1, label_visibility="collapsed",
    )
    today = datetime.today()
    period_map = {"Son 6 Ay": 180, "Son 1 Yıl": 365, "Son 2 Yıl": 730}

    if period == "Özel Aralık":
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Başlangıç", today - timedelta(365))
        with c2:
            end_date = st.date_input("Bitiş", today)
    else:
        start_date = today - timedelta(days=period_map[period])
        end_date = today

    st.markdown("---")

    st.markdown(f"<p style='color:{_t};font-weight:700;'>⚡ Canlı Güncelleme</p>",
                unsafe_allow_html=True)
    live_mode = st.toggle("Live Update (15 dk)", value=True)
    if live_mode:
        st.markdown(
            f'<span class="live-dot"></span>'
            f'<span style="color:{_g};font-size:0.85rem;font-weight:600;">CANLI</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<span style="color:{_m};font-size:0.85rem;">Pasif — Manuel yenile</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    refresh_btn = st.button("🔄 Verileri Şimdi Yenile", use_container_width=True, type="primary")
    if refresh_btn:
        st.cache_data.clear()

    st.markdown("---")
    st.markdown(
        f"<small style='color:{_m};'>"
        f"📐 yahooquery (batch) • Plotly • Streamlit<br>"
        f"Rate-limit free veri çekme<br>"
        f"Cache TTL: 15 dakika</small>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 10: ANA SAYFA LAYOUT
# ═══════════════════════════════════════════════════════════════

st.markdown(
    f"<h1 style='text-align:center;color:{_w};margin:0;font-size:2rem;'>"
    f"📊 Market Breadth & Trend Dashboard</h1>"
    f"<p style='text-align:center;color:{_m};margin-top:2px;font-size:0.92rem;'>"
    f"IBD Methodology • Institutional Breadth • {INDEX_MAP[index_choice]['label']}</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

start_str = str(start_date)
end_str = str(end_date)

with st.spinner("🔄 Piyasa verileri yükleniyor (yahooquery batch)..."):
    R = run_pipeline(index_choice, start_str, end_str)

if R is None:
    st.markdown(
        f"""<div style="text-align:center;padding:80px;background:{C['card']};
        border-radius:20px;border:1px solid {C['border']};margin-top:30px;">
        <h2 style="color:{C['red']};">Veri Yüklenemedi</h2>
        <p style="color:{C['muted']};">
        Sidebar'dan <strong>🔄 Verileri Şimdi Yenile</strong> butonuna tıklayın.<br>
        İnternet bağlantınızı kontrol edin.
        </p></div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Kısaltmalar ───
idx_df   = R["idx_df"]
dist_df  = R["dist"]
ftd_df   = R["ftd"]
mc_df    = R["mc"]
p50_df   = R["p50"]
p200_df  = R["p200"]
cop_df   = R["coppock"]
zbt_df   = R["zbt"]
hl_df    = R["hl"]
macro    = R["macro"] or {}
yc_df    = R["yc"]
etf_name = R["etf_name"]

def safe_last(df, col, default=0):
    """DataFrame'den son değeri güvenli alır."""
    try:
        if df is not None and not df.empty and col in df.columns:
            s = df[col].dropna()
            return float(s.iloc[-1]) if len(s) > 0 else default
    except Exception:
        pass
    return default

dist_count = int(safe_last(dist_df, "DistCount25", 0))
pct50_val  = safe_last(p50_df, "PctAbove50", 50)
pct200_val = safe_last(p200_df, "PctAbove200", 50)
mc_val     = safe_last(mc_df, "McClellan", 0)
vix_df_raw = macro.get("VIX")
vix_val    = safe_last(vix_df_raw, "Close", 20) if vix_df_raw is not None else 20
net_hl     = safe_last(hl_df, "Net", 0)


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 11: MARKET HEALTH STATUS BANNER
# ═══════════════════════════════════════════════════════════════

health_text, health_css = determine_market_health(dist_count, pct50_val, pct200_val, mc_val, vix_val)
fg_score, fg_label, fg_color = calc_fear_greed_score(
    dist_count, pct50_val, pct200_val, mc_val, vix_val, net_hl
)

col_banner, col_fg = st.columns([3, 1])
with col_banner:
    st.markdown(
        f'<div class="health-banner {health_css}">{health_text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="text-align:center;color:{C["muted"]};font-size:0.78rem;margin-top:2px;">'
        f'Son güncelleme: {R["timestamp"]} • {R["fetched_count"]} hisse analiz edildi</p>',
        unsafe_allow_html=True,
    )

with col_fg:
    st.markdown(
        f"""<div class="gauge-container">
            <div class="gauge-label">Fear & Greed</div>
            <div class="gauge-value" style="color:{fg_color};">{fg_score}</div>
            <div class="gauge-desc" style="color:{fg_color};">{fg_label}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 12: DEV METRİK KARTLARI
# ═══════════════════════════════════════════════════════════════

st.markdown("")
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)

spy_close = idx_df["Close"].iloc[-1] if not idx_df.empty else 0
spy_chg = idx_df["Close"].pct_change().iloc[-1] * 100 if not idx_df.empty else 0

with m1:
    st.metric(etf_name, f"${spy_close:.2f}", f"{spy_chg:+.2f}%")
with m2:
    st.metric("Dist. Days", f"{dist_count}",
              "DANGER" if dist_count >= 5 else "OK", delta_color="inverse")
with m3:
    st.metric("% > 50 DMA", f"{pct50_val:.1f}%",
              f"{'↑' if pct50_val > 50 else '↓'}")
with m4:
    st.metric("% > 200 DMA", f"{pct200_val:.1f}%",
              f"{'↑' if pct200_val > 50 else '↓'}")
with m5:
    st.metric("McClellan", f"{mc_val:.1f}",
              "Bullish" if mc_val > 0 else "Bearish")
with m6:
    st.metric("VIX", f"{vix_val:.1f}",
              "Fear" if vix_val > 25 else "Calm" if vix_val < 15 else "Normal")
with m7:
    st.metric("Net H/L", f"{int(net_hl)}",
              "Bullish" if net_hl > 0 else "Bearish")

st.markdown("---")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 13: CANLI GRAFİK — PRİCE + BREADTH OVERLAY
# ═══════════════════════════════════════════════════════════════

st.plotly_chart(
    chart_price_with_breadth(idx_df, mc_df, etf_name),
    use_container_width=True,
)
st.markdown("---")


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 14: SEKMELER (5 TAB)
# ═══════════════════════════════════════════════════════════════

tabs = st.tabs([
    "🔍 IBD Metrics",
    "📈 Breadth & Participation",
    "🚀 Momentum",
    "😰 Sentiment & Macro",
    "📊 Radar Scorecard",
])

# ─── TAB 1: IBD Metrics ───
with tabs[0]:
    st.subheader("IBD Distribution Day & Follow-Through Analysis")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.plotly_chart(chart_distribution(dist_df, etf_name), use_container_width=True)
    with col_b:
        st.markdown("#### 📖 Nasıl Okunur?")
        _cr = C["red"]
        st.markdown(f"""
        **Distribution Day:**
        Endeks ≥%0.2 düşüp, hacim artarsa sayılır.
        25 günde **5+** = <span style="color:{_cr};">tehlike bölgesi</span>.

        **Follow-Through Day:**
        Düzeltme sonrası rallinin 4-7. gününde
        ≥%1.25 hacimli yükseliş = yeni trend onayı.
        """, unsafe_allow_html=True)

        ftd_dates = ftd_df[ftd_df["IsFTD"]]
        if not ftd_dates.empty:
            st.success(f"Son FTD: {ftd_dates.index[-1].strftime('%Y-%m-%d')}")
        else:
            st.info("Bu dönemde FTD yok.")

    st.plotly_chart(chart_ftd(ftd_df, etf_name), use_container_width=True)


# ─── TAB 2: Breadth & Participation ───
with tabs[1]:
    st.subheader("Market Breadth & Participation")
    st.plotly_chart(chart_pct_above(p50_df, p200_df), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        mc_colors = [C["green"] if v >= 0 else C["red"] for v in mc_df["McClellan"]]
        fig_mc = go.Figure()
        fig_mc.add_trace(go.Bar(
            x=mc_df.index, y=mc_df["McClellan"], marker_color=mc_colors, opacity=0.85,
            name="McClellan Osc.",
        ))
        fig_mc.add_hline(y=0, line_color=C["muted"])
        fig_mc.add_hline(y=100, line_dash="dot", line_color=C["green"], annotation_text="OB")
        fig_mc.add_hline(y=-100, line_dash="dot", line_color=C["red"], annotation_text="OS")
        _dark_layout(fig_mc, "McClellan Oscillator")
        st.plotly_chart(fig_mc, use_container_width=True)
    with c2:
        if hl_df is not None and not hl_df.empty:
            st.plotly_chart(chart_highslows(hl_df), use_container_width=True)
        else:
            show_data_warning("Highs/Lows")


# ─── TAB 3: Momentum ───
with tabs[2]:
    st.subheader("Momentum Indicators")
    c1, c2 = st.columns(2)
    with c1:
        if cop_df is not None and not cop_df.empty:
            st.plotly_chart(chart_coppock(cop_df), use_container_width=True)
            st.caption("🟢 Sıfır altından yukarı geçiş = uzun vadeli alım sinyali")
        else:
            show_data_warning("Coppock Curve")
    with c2:
        if zbt_df is not None and not zbt_df.empty:
            st.plotly_chart(chart_zbt(zbt_df), use_container_width=True)
            st.caption("⭐ ZBT sinyali tarihsel olarak çok nadir ama güçlüdür")
        else:
            show_data_warning("Zweig Breadth Thrust")


# ─── TAB 4: Sentiment & Macro ───
with tabs[3]:
    st.subheader("Sentiment & Macro Indicators")
    c1, c2 = st.columns(2)
    with c1:
        if vix_df_raw is not None and not vix_df_raw.empty:
            st.plotly_chart(chart_vix(vix_df_raw), use_container_width=True)
        else:
            show_data_warning("VIX")
    with c2:
        st.plotly_chart(chart_yield(yc_df), use_container_width=True)

    if vix_df_raw is not None and not vix_df_raw.empty:
        vc1, vc2, vc3, vc4 = st.columns(4)
        v = vix_df_raw["Close"]
        with vc1: st.metric("VIX Son", f"{v.iloc[-1]:.2f}")
        with vc2: st.metric("VIX Ort.", f"{v.mean():.2f}")
        with vc3: st.metric("VIX Min", f"{v.min():.2f}")
        with vc4: st.metric("VIX Max", f"{v.max():.2f}")


# ─── TAB 5: Radar Scorecard ───
with tabs[4]:
    st.subheader("Market Health Radar")

    def norm(val, lo, hi, inv=False):
        s = max(0, min(100, (val - lo) / (hi - lo) * 100))
        return 100 - s if inv else s

    radar = {
        "Breadth 50": norm(pct50_val, 0, 100),
        "Breadth 200": norm(pct200_val, 0, 100),
        "McClellan": norm(mc_val, -150, 150),
        "Low Dist": norm(dist_count, 0, 8, inv=True),
        "Low VIX": norm(vix_val, 10, 40, inv=True),
        "Net Highs": norm(net_hl, -40, 40),
    }

    c_r, c_d = st.columns([2, 1])
    with c_r:
        st.plotly_chart(chart_radar(radar), use_container_width=True)
    with c_d:
        st.markdown("#### Skor Detayları")
        for k, v in radar.items():
            bar_c = C["green"] if v >= 60 else C["yellow"] if v >= 40 else C["red"]
            filled = int(v / 10)
            st.markdown(
                f"**{k}:** `{v:.0f}`/100 "
                f"<span style='color:{bar_c};'>{'●' * filled}{'○' * (10-filled)}</span>",
                unsafe_allow_html=True,
            )
        avg = np.mean(list(radar.values()))
        avg_c = C["green"] if avg >= 60 else C["yellow"] if avg >= 40 else C["red"]
        st.markdown(f"---\n**Toplam:** <span style='color:{avg_c};font-size:1.5rem;'>"
                    f"**{avg:.0f}/100**</span>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 15: EXCEL EXPORT
# ═══════════════════════════════════════════════════════════════

st.markdown("---")

excel_sheets = {
    "Index_Price": idx_df[["Open","High","Low","Close","Volume"]] if idx_df is not None else None,
    "Distribution": dist_df[["Close","PctChg","DistCount25","IsDistDay"]] if dist_df is not None else None,
    "FTD": ftd_df[["Close","PctChg","ConsUp","IsFTD"]] if ftd_df is not None else None,
    "AD_McClellan": mc_df[["Advances","Declines","AD_Line","McClellan"]] if mc_df is not None else None,
    "PctAbove50": p50_df,
    "PctAbove200": p200_df,
    "Coppock": cop_df,
    "ZBT": zbt_df[["ZBTRatio","ZBTEMA","ZBTSignal"]] if zbt_df is not None and "ZBTRatio" in zbt_df.columns else None,
    "HighsLows": hl_df,
    "VIX": vix_df_raw[["Close"]].rename(columns={"Close":"VIX"}) if vix_df_raw is not None else None,
    "YieldCurve": yc_df,
}

ce1, ce2, ce3 = st.columns([1, 2, 1])
with ce2:
    excel_buf = generate_excel(excel_sheets)
    st.download_button(
        label="📥 Tüm Verileri Excel'e Aktar — market_pulse_data.xlsx",
        data=excel_buf,
        file_name="market_pulse_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )


# ═══════════════════════════════════════════════════════════════
# BÖLÜM 16: AUTO-REFRESH MEKANİZMASI
# ═══════════════════════════════════════════════════════════════

if live_mode:
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = time.time()

    elapsed = time.time() - st.session_state["last_refresh"]
    remaining = max(0, 900 - elapsed)

    st.markdown(
        f'<p style="text-align:center;color:{C["muted"]};font-size:0.75rem;margin-top:8px;">'
        f'Sonraki otomatik yenileme: {int(remaining // 60)}dk {int(remaining % 60)}sn</p>',
        unsafe_allow_html=True,
    )

    if elapsed >= 900:
        st.session_state["last_refresh"] = time.time()
        st.cache_data.clear()
        st.rerun()
