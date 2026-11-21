# Yapılacaklar — Istanbul Transit Demand

Repo gizli. Herkese açık yapmadan önce bu dosyayı İngilizceye çevir veya kaldır.

## Faz 1 — Veri pipeline'ı ve baseline (1. hafta)
- [x] Proje iskeleti, pyproject, testler, CI
- [x] İBB CKAN indirici (`src/transit/data/ibb.py`)
- [x] Temizleme ve saatlik panel (`clean.py`), eksik saatleri 0 ile doldurma
- [x] Hava durumu (Open-Meteo) ve tatil/arife takvimi (`external.py`)
- [x] Lag/rolling özellikleri + geleceğe bakma (leakage) testi
- [x] Walk-forward validasyon ve seasonal-naive baseline
- [x] Gerçek veri: Ocak–Temmuz 2024 (7 ay, ~120 milyon satır) tarayıcıda akış halinde okunup saatlik toplamlara indirildi → `data/aggregated/`
- [x] Gerçek CSV kolon adları kontrol edildi, `clean.py` ile birebir uyumlu
- [x] Bulgu: Ağustos–Ekim 2024 dosyaları eksik (Ekim'de 18 gün), Kasım–Aralık 2024 boş yayımlanmış → indirici 1 MB altı dosyaları atlıyor
- [ ] Daha uzun geçmiş için 2023 aylarını da ekle (COVID dönemi 2020–2021 hariç tutulmalı mı? gerekçesini yaz)

## Faz 2 — EDA ve istatistik (2. hafta)
- [ ] `notebooks/01_eda.ipynb`: saatlik/haftalık desenler, mod bazında dağılımlar, aykırı değerler
- [x] Yağmur etkisi: yağmurlu ve kuru iş günleri, bootstrap %95 güven aralığı + Mann-Whitney (`analysis/stats.py`)
- [ ] Bayram ve arife etkisi: olay çalışması (event study) grafiği
- [x] Mann-Whitney U testi
- [ ] Permütasyon testi ve çoklu karşılaştırma düzeltmesi (Benjamini-Hochberg)
- [ ] Ücretsiz ulaşım günleri (1 Mayıs, okulun ilk günü vb.) için ayrı bir özellik ekle
- [x] Bulgular `reports/results.md`'de, GitHub Actions her güncellemede yeniden üretiyor

## Faz 3 — Modelleme (3. hafta)
- [x] Ridge baseline (scikit-learn pipeline, one-hot saat/gün)
- [x] XGBoost ve HistGradientBoosting
- [ ] Optuna ile hiperparametre araması (yalnızca train fold'larında)
- [x] Modelleri tek tabloda karşılaştır: MAE, sMAPE, WAPE (`reports/results.md`)
- [x] Permütasyon önemi (özellik katkıları)
- [ ] SHAP grafikleri
- [ ] Hata analizi: model en çok hangi saatlerde/günlerde yanılıyor?
- [ ] Okul takvimi özelliği ekle (Haziran sonundan itibaren talep belirgin düşüyor)
- [ ] Gece saatlerinde sMAPE yüksek: log1p hedef veya metro kapalı saatler için kural dene
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
