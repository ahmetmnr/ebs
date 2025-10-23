# Changelog

## [2.0.0] - 2025-10-21

### ✨ Yeni Özellikler

#### Veritabanı Yapısı
- **Yeni SQL Şeması**: 9 tablo, 3 view, 3 trigger ile tam normalize edilmiş veritabanı
- **Belgeler Tablosu**: JSON'dan ayrıştırılmış belge yönetimi
- **Analiz Sonuçları**: 40+ kolonlu detaylı analiz sonucu tablosu
- **Proje/Yayın Takibi**: 1-N ilişkisi ile proje detayları
- **Belge Analiz Logları**: Performans metrikleri ve chunk tracking
- **Sistem Konfigürasyonu**: Runtime ayarlar için dinamik tablo
- **Belge Tipi Tahmin**: Regex-based otomatik belge tipi belirleme
- **Zorunlu Belgeler**: Hizmet tipi bazlı validation matrix

#### Model Sınıfları
- `models/database.py`: SQLite yönetim sınıfı ve BaseModel
- `models/basvuru.py`: Başvuru CRUD operasyonları
- `models/belge.py`: Belge yönetimi ve tipi tahmini
- `models/analiz_sonuc.py`: Analiz sonucu yönetimi ve güncelleme

#### Konfigürasyon
- `config/settings.py`: Merkezi konfigürasyon sistemi
- Environment variable desteği (.env)
- Validation ve hata yönetimi
- Chunk ayarları ve Ollama parametreleri

#### Migration
- `scripts/migrate_database.py`: Eski şemadan yeni şemaya otomatik migration
- `scripts/check_db_schema.py`: Veritabanı şema kontrolü
- `scripts/init_database.py`: Yeni veritabanı başlatma
- Otomatik yedekleme ve rollback desteği

#### Dokümantasyon
- Güncellenmiş README.md
- MIGRATION_GUIDE.md: Detaylı migration rehberi
- DATABASE_SCHEMA.md: Güncellenmiş şema dokümantasyonu
- CHANGELOG.md: Değişiklik kayıtları

### 🔧 İyileştirmeler

- **Performans**: Optimize edilmiş indexler ve view'lar
- **Veri Bütünlüğü**: Foreign key constraints ve trigger'lar
- **Kod Organizasyonu**: Daha modüler yapı
- **Hata Yönetimi**: Kapsamlı logging ve error handling
- **Test Edilebilirlik**: Model-based yaklaşım ile unit test desteği

### 📊 Veritabanı Şeması

**Yeni Tablolar:**
1. `basvurular` - Normalize edilmiş başvuru bilgileri
2. `belgeler` - Ayrı belge yönetimi
3. `analiz_sonuclari` - Detaylı analiz sonuçları
4. `proje_yayinlar` - Proje/yayın detayları
5. `belge_analiz_log` - Analiz performans logları
6. `chunk_sonuclari` - LLM chunk tracking
7. `sistem_config` - Runtime konfigürasyon
8. `belge_tipi_kurallar` - Belge tipi tahmin kuralları
9. `zorunlu_belgeler` - Hizmet bazlı zorunlu belgeler

**View'lar:**
- `v_basvuru_ozet` - Başvuru özet raporu
- `v_sektor_dagilim` - Sektör dağılımı
- `v_analiz_performans` - Analiz performans metrikleri

**Trigger'lar:**
- `trg_basvurular_updated` - Otomatik updated_at güncelleme
- `trg_analiz_updated` - Analiz sonuçları güncelleme
- `trg_belge_silme` - Cascade delete cleanup

### 🔄 Değişiklikler

#### Eski Yapı (v1.x)
```
data/basvurular.db
├── basvurular (4 kolon, denormalize)
│   └── json_data (tüm veri JSON'da)
└── analiz_sonuclari (8 kolon, basit)
```

#### Yeni Yapı (v2.0)
```
data/basvurular.db
├── basvurular (17 kolon, normalize)
├── belgeler (ayrı tablo)
├── analiz_sonuclari (40+ kolon)
├── proje_yayinlar (1-N)
├── belge_analiz_log
├── chunk_sonuclari
├── sistem_config
├── belge_tipi_kurallar
└── zorunlu_belgeler
```

### 📦 Bağımlılıklar

**Yeni:**
- `python-dotenv==1.0.0` - Environment variables
- `pdfplumber==0.10.0` - Gelişmiş PDF işleme
- `tenacity==8.2.3` - Retry logic
- `click==8.1.7` - CLI tools
- `rich==13.5.0` - Pretty CLI output
- `tqdm==4.66.0` - Progress bars
- `chardet==5.2.0` - Encoding detection
- `pytest-cov==4.1.0` - Test coverage
- `pytest-mock==3.11.1` - Mocking

### ⚠️ Breaking Changes

**Veritabanı Şeması:**
- Eski şema artık desteklenmiyor
- Migration zorunlu (scripts/migrate_database.py)
- JSON field'lar normalize edildi

**API Değişiklikleri:**
- Yok (mevcut `app/` kodu etkilenmedi)
- Yeni model sınıfları eklendi (geriye dönük uyumlu)

### 🐛 Düzeltmeler

- UTF-8 encoding sorunları (Windows)
- Emoji karakterleri kaldırıldı (Windows uyumluluğu)
- Base64 decode buffer overflow
- JSON parse hataları

### 📈 İstatistikler

- **Kod Satırları**: +2,500 (models, config, scripts)
- **Dosya Sayısı**: +15 yeni dosya
- **Test Coverage**: 0% → TBD
- **Dokümantasyon**: +500 satır

### 🎯 Sonraki Adımlar (v2.1)

- [ ] Services klasörü implementasyonu
- [ ] Analyzers klasörü implementasyonu
- [ ] Utils klasörü implementasyonu
- [ ] Unit testler (%80+ coverage)
- [ ] REST API endpoints
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Performance benchmarks

### 📝 Migration Notları

**Mevcut veri korunur:**
- ✅ Tüm başvurular (2,088 kayıt)
- ✅ JSON ham verileri
- ✅ Mevcut analizler
- ✅ Belge içerikleri (Base64)

**Yeni veriler:**
- ✅ Belgeler ayrı tabloya taşındı
- ✅ Belge tipleri tahmin edildi
- ✅ Sistem konfigürasyonu eklendi
- ✅ Zorunlu belge matrisi oluşturuldu

**Migration süreci:**
1. Otomatik yedekleme
2. Yeni şema oluşturma
3. Veri kopyalama
4. Doğrulama
5. Toplam süre: ~5-10 dakika

### 🙏 Teşekkürler

Bu güncelleme "Sanayide Yeşil Dönüşüm Başvuru Değerlendirme Sistemi - Detaylı Teknik Dokümantasyon" raporuna göre hazırlanmıştır.

---

## [1.0.0] - 2025-10-10

### İlk Sürüm

- CSB eBasvuru API entegrasyonu
- Otomatik belge çekme
- OCR ile metin çıkarma
- Ollama LLM ile bilgi çıkarma
- Basit SQLite veritabanı
- Streamlit viewer
