# Yapılacaklar — Istanbul Transit Demand

Repo gizli. Herkese açık yapmadan önce bu dosyayı İngilizceye çevir veya kaldır.

## Faz 1 — Veri pipeline'ı ve baseline (1. hafta)
- [x] Proje iskeleti, pyproject, testler, CI
- [x] İBB CKAN indirici (`src/transit/data/ibb.py`)
- [x] Temizleme ve saatlik panel (`clean.py`), eksik saatleri 0 ile doldurma
- [x] Hava durumu (Open-Meteo) ve tatil/arife takvimi (`external.py`)
- [x] Lag/rolling özellikleri + geleceğe bakma (leakage) testi
- [x] Walk-forward validasyon ve seasonal-naive baseline
- [ ] `python scripts/run_phase1.py --months 12` komutunu kendi bilgisayarında çalıştır (İBB portalı bazı ağlardan erişilemiyor)
- [ ] Gerçek CSV kolon adlarını kontrol et; farklıysa `clean.py` içindeki `RENAME` sözlüğüne ekle
- [ ] COVID dönemini (2020–2021) dahil edip etmeyeceğine karar ver, gerekçesini README'ye yaz

## Faz 2 — EDA ve istatistik (2. hafta)
- [ ] `notebooks/01_eda.ipynb`: saatlik/haftalık desenler, mod bazında dağılımlar, aykırı değerler
- [ ] Yağmur etkisi: yağmurlu ve kuru saatlerde talep farkı, bootstrap %95 güven aralığı
- [ ] Bayram ve arife etkisi: olay çalışması (event study) grafiği
- [ ] Mann-Whitney U ve permütasyon testleri; çoklu karşılaştırma düzeltmesi (Benjamini-Hochberg)
- [ ] Ücretsiz ulaşım günleri (1 Mayıs, okulun ilk günü vb.) için ayrı bir özellik ekle
- [ ] Bulguları README'nin "Results" bölümüne kısa grafiklerle ekle

## Faz 3 — Modelleme (3. hafta)
- [ ] Ridge / Poisson regresyon baseline'ı (scikit-learn pipeline)
- [ ] XGBoost; Optuna ile hiperparametre araması (yalnızca train fold'larında)
- [ ] Modelleri tek tabloda karşılaştır: MAE, sMAPE, WAPE, fold bazında
- [ ] SHAP: en önemli özellikler, yağmur ve tatil etkisi
- [ ] Hata analizi: model en çok hangi saatlerde/günlerde yanılıyor?
- [ ] (Opsiyonel) Hat bazında tahmine genişlet

## Faz 4 — MLOps ve Cloud (4. hafta)
- [ ] MLflow ile deney takibi ve model kaydı
- [ ] Dockerfile ile pipeline'ı containerize et
- [ ] GitHub Actions: her push'ta ruff + pytest (hazır), haftalık veri tazeleme işi
- [ ] AWS: S3'te veri, EC2 veya ECS'te zamanlanmış günlük yeniden eğitim (ücretsiz katmanı aşma)
- [ ] Veri kalitesi kontrolleri: beklenmeyen sıfırlar, şema değişikliği uyarısı
- [ ] Basit model izleme: günlük hata metriğini kaydet, eşik aşılırsa uyar

## Faz 5 — Sunum (5. hafta)
- [ ] Streamlit dashboard: "Yarın saat 08:00'de raylı sistemde kaç yolcu bekleniyor?"
- [ ] Dashboard'u yayına al ve linkini README'ye ekle
- [ ] README: mimari diyagramı, sonuç grafikleri, sınırlamalar
- [ ] Medium yazısı (Türkçe veya İngilizce)
- [ ] Repoyu herkese açık yap, pin'le, CV'ye ve portfolyoya ekle

## CV maddesi (bittiğinde metrikle güncelle)
> Built an end-to-end demand forecasting system for Istanbul public transport on İBB open data (Pandas, scikit-learn, XGBoost, SHAP); quantified weather and holiday effects with bootstrap tests; automated daily retraining with MLflow, Docker, GitHub Actions and AWS; reduced WAPE by __% over a seasonal-naive baseline.
