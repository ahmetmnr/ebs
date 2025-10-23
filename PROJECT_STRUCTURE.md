# Proje Yapısı

```
ebasvuru/
│
├── 📁 app/                           # Mevcut uygulama (eski yapı - uyumlu)
│   ├── 📁 api/                       # API endpoints (gelecekte kullanılacak)
│   ├── 📁 core/                      # İşleme mantığı
│   │   ├── document_classifier.py
│   │   ├── document_processor.py
│   │   ├── document_requirements.py
│   │   └── document_validator.py
│   ├── 📁 models/                    # Pydantic şemalar
│   │   ├── external_api.py
│   │   └── schemas.py
│   ├── 📁 prompts/                   # LLM prompt şablonları
│   │   ├── adli_sicil_prompt.py
│   │   ├── akademik_proje_prompt.py
│   │   ├── diploma_prompt.py
│   │   ├── hitap_prompt.py
│   │   ├── ozgecmis_prompt.py
│   │   ├── sektor_belge_prompt.py
│   │   └── prompt_factory.py
│   ├── 📁 services/                  # External services
│   │   └── (boş - gelecekte eklenecek)
│   ├── 📁 utils/                     # Yardımcı fonksiyonlar
│   │   └── (boş - gelecekte eklenecek)
│   └── config.py                     # Eski config (deprecated)
│
├── 📁 config/                        # ✨ YENİ: Merkezi konfigürasyon
│   ├── __init__.py
│   └── settings.py                   # Global ayarlar, env vars
│
├── 📁 database/                      # ✨ YENİ: Veritabanı şemaları
│   ├── __init__.py
│   ├── schema.sql                    # Tam SQL şeması (9 tablo, 3 view)
│   └── 📁 migrations/                # Migration scriptleri (gelecek)
│       └── (boş)
│
├── 📁 models/                        # ✨ YENİ: ORM-benzeri model sınıfları
│   ├── __init__.py                   # Model exports
│   ├── database.py                   # DatabaseManager, BaseModel
│   ├── basvuru.py                    # Basvuru CRUD
│   ├── belge.py                      # Belge CRUD
│   └── analiz_sonuc.py               # AnalizSonuc CRUD
│
├── 📁 scripts/                       # Yönetim ve işlem scriptleri
│   ├── init_database.py              # ✨ YENİ: Veritabanı başlat
│   ├── migrate_database.py           # ✨ YENİ: Eski DB -> Yeni şema
│   ├── check_db_schema.py            # ✨ YENİ: Şema kontrolü
│   ├── sync_data_to_db.py            # API'den veri çek
│   ├── analyze_from_db.py            # Başvuruları analiz et
│   └── test_external_api.py          # API test
│
├── 📁 data/                          # Veriler (gitignore)
│   ├── basvurular.db                 # SQLite DB (9.77 GB)
│   ├── 📁 imports/                   # Import edilecek dosyalar
│   └── 📁 exports/                   # Raporlar
│
├── 📁 logs/                          # Log dosyaları (gitignore)
│   ├── app.log
│   ├── error.log
│   ├── ollama.log
│   └── database.log
│
├── 📁 llm_logs/                      # LLM request/response logs
│   └── 📁 {takip_no}/                # Başvuru bazlı loglar
│       └── {document_type}_{timestamp}.json
│
├── 📁 temp/                          # Geçici dosyalar (gitignore)
│   └── 📁 analiz/
│       └── 📁 {takip_no}/            # Geçici belge dosyaları
│
├── 📁 viewer/                        # Streamlit web arayüzü
│   ├── viewer_app.py
│   └── 📁 static/                    # Statik dosyalar
│
├── 📁 prompts/                       # Prompt şablonları (gelecekte kullanılacak)
│   └── (boş)
│
├── 📁 services/                      # Servis sınıfları (gelecekte kullanılacak)
│   └── (boş)
│
├── 📁 analyzers/                     # Analyzer sınıfları (gelecekte kullanılacak)
│   └── (boş)
│
├── 📁 utils/                         # Yardımcı fonksiyonlar (gelecekte kullanılacak)
│   └── (boş)
│
├── 📁 tests/                         # Unit testler (gelecekte)
│   └── (boş)
│
├── 📄 .env                           # Konfigürasyon (gitignore)
├── 📄 .env.example                   # Örnek konfigürasyon
├── 📄 .gitignore                     # Git ignore kuralları
│
├── 📄 requirements.txt               # Python bağımlılıkları
├── 📄 README.md                      # ✨ Güncellenmiş ana dokümantasyon
├── 📄 SETUP.md                       # Kurulum rehberi
├── 📄 ARCHITECTURE.md                # Mimari dokümantasyonu
├── 📄 DATABASE_SCHEMA.md             # ✨ Güncellenmiş veritabanı şeması
├── 📄 AKIS_DIYAGRAMI.md              # İş akışı diyagramları
├── 📄 MIGRATION_GUIDE.md             # ✨ YENİ: Migration rehberi
└── 📄 CHANGELOG.md                   # ✨ YENİ: Değişiklik kayıtları
```

## 📊 Dosya ve Klasör Sayıları

| Kategori | Sayı | Notlar |
|----------|------|--------|
| Python dosyaları | 35+ | app/ + models/ + scripts/ |
| Konfigürasyon | 5 | settings.py, .env, vb. |
| Dokümantasyon | 8 | .md dosyaları |
| SQL şemaları | 1 | schema.sql |
| Toplam kod satırı | ~8,000+ | Yorumlar dahil |

## 🎯 Kullanılan Klasörler

### Aktif Kullanımda
- ✅ `app/core/` - Belge işleme
- ✅ `app/prompts/` - LLM promptları
- ✅ `config/` - Konfigürasyon
- ✅ `database/` - SQL şemaları
- ✅ `models/` - Model sınıfları
- ✅ `scripts/` - Yönetim scriptleri
- ✅ `data/` - Veritabanı ve veriler
- ✅ `logs/` - Log dosyaları
- ✅ `viewer/` - Web arayüzü

### Gelecekte Kullanılacak
- 📋 `app/api/` - REST API endpoints
- 📋 `services/` - Yeni servis sınıfları
- 📋 `analyzers/` - Belge analyzer'ları
- 📋 `utils/` - Yardımcı fonksiyonlar
- 📋 `tests/` - Unit testler
- 📋 `database/migrations/` - Migration'lar

## 📦 Modüler Yapı

### Core Modules
```python
from config import settings              # Global ayarlar
from models import db, Basvuru, Belge    # Veritabanı modelleri
```

### Legacy Modules (Eski yapı - hala çalışır)
```python
from app.core import document_processor  # Belge işleme
from app.prompts import prompt_factory   # Prompt üretimi
```

## 🔗 Bağımlılıklar

### Harici Bağımlılıklar
- CSB eBasvuru API
- Ollama (LLM)
- EasyOCR (OCR)
- SQLite (Veritabanı)

### Python Packages
- fastapi, pydantic (API)
- requests, httpx (HTTP)
- easyocr, pdf2image (OCR)
- streamlit (Web UI)
- python-dotenv (Config)
- tenacity (Retry)
- colorlog (Logging)

## 📝 Notlar

- **✨ YENİ**: v2.0 ile eklenen dosyalar/klasörler
- **📁**: Klasör
- **📄**: Dosya
- **gitignore**: Git'e commit edilmez (data/, logs/, temp/, .env)
- **Eski yapı**: `app/` klasörü eski yapıyı korur (geriye dönük uyumluluk)
- **Yeni yapı**: `config/`, `models/`, `database/` yeni yapı
