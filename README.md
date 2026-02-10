# 📊 Market Breadth & Trend Dashboard — Cloud Edition

**Streamlit Cloud üzerinde 7/24 çalışan, otomatik yenilenen piyasa sağlığı dashboardı.**

---

## 🚀 Deployment Rehberi (Adım Adım)

### Adım 1: GitHub Repository Oluştur

```bash
# Yeni repo oluştur
mkdir market-pulse-dashboard
cd market-pulse-dashboard

# Dosyaları kopyala
cp main.py requirements.txt .
mkdir -p .streamlit
cp .streamlit/config.toml .streamlit/

# Git başlat
git init
git add .
git commit -m "Initial: Market Breadth Dashboard v2"

# GitHub'a push et
# Önce github.com'da yeni bir repo oluştur, sonra:
git remote add origin https://github.com/KULLANICI_ADIN/market-pulse-dashboard.git
git branch -M main
git push -u origin main
```

### Adım 2: Streamlit Cloud'a Deploy Et

1. **[share.streamlit.io](https://share.streamlit.io)** adresine git
2. GitHub hesabınla giriş yap
3. **"New app"** butonuna tıkla
4. Ayarları gir:
   - **Repository:** `KULLANICI_ADIN/market-pulse-dashboard`
   - **Branch:** `main`
   - **Main file path:** `main.py`
5. **"Deploy!"** butonuna bas
6. ~2-3 dakika içinde canlı olacak!

### Adım 3: URL'ni Al

Deploy tamamlandığında şu formatta bir URL alacaksın:
```
https://KULLANICI_ADIN-market-pulse-dashboard-main-xxxxx.streamlit.app
```

---

## 📁 Dosya Yapısı

```
market-pulse-dashboard/
├── main.py                    # Tek dosyada tüm sistem (~950 satır)
├── requirements.txt           # Python bağımlılıkları
├── .streamlit/
│   └── config.toml            # Streamlit tema + sunucu ayarları
└── README.md                  # Bu dosya
```

---

## ⚡ Özellikler

| Özellik | Detay |
|---------|-------|
| **Auto-Refresh** | `st.cache_data(ttl=900)` — 15 dk'da bir otomatik yenileme |
| **Live Toggle** | Sidebar'dan canlı/pasif mod geçişi |
| **Endeks Seçimi** | S&P 500 ↔ Nasdaq 100 anlık geçiş |
| **Hata Yönetimi** | `@safe_fetch` dekoratörü — timeout/bağlantı hataları şık uyarıyla gösterilir |
| **Threading** | `ThreadPoolExecutor(max_workers=20)` — ~100+ hisse paralel çekilir |
| **Excel Export** | 11 sekmeli `.xlsx` dosyası tek tıkla indir |
| **Fear & Greed** | 6 bileşenli bileşik skor (0-100) |
| **Dark Theme** | Profesyonel koyu tema, hover animasyonları |

---

## 📊 İndikatörler

### IBD Metrics
- Distribution Days (25-gün kayan pencere)
- Follow-Through Day tespiti

### Breadth & Participation
- Advance-Decline Line + SPY overlay
- McClellan Oscillator & Summation Index
- % Stocks Above 50 DMA / 200 DMA
- 52-Week New Highs - New Lows

### Momentum
- Coppock Curve (aylık — uzun vadeli)
- Zweig Breadth Thrust (nadir sinyal)

### Sentiment & Macro
- VIX (seviye analizi)
- Yield Curve Spread (inversyon tespiti)

### Radar Scorecard
- Tüm metriklerin 0-100 normalize edilmiş radar grafiği
- Otomatik piyasa durumu sınıflandırması

---

## 🔧 Lokal Çalıştırma

```bash
pip install -r requirements.txt
streamlit run main.py
```

Tarayıcıda `http://localhost:8501` adresinde açılır.

---

## ⚠️ Notlar

- **yfinance Rate Limiting:** Çok sık yenileme yapılırsa Yahoo Finance geçici engel koyabilir. TTL=900s bu riski minimize eder.
- **Streamlit Cloud Kaynakları:** Free tier'da 1 GB RAM limiti var. ~100 hisselik örneklem bu limitin altında kalır.
- **Tam S&P 500:** Tüm 500 hisseyi çekmek isterseniz `SP500_UNIVERSE` listesini genişletin, ama Cloud'da timeout riski artar.
- **Put/Call Ratio:** yfinance'da doğrudan mevcut olmadığından VIX proxy olarak kullanılmıştır.
