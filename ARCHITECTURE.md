# Belge İşleme Servisi - Mimari Dokümantasyon

## 🏗️ SOLID Prensipleri

Proje SOLID prensiplerine göre tasarlanmıştır:

### 1. Single Responsibility Principle (SRP)

Her sınıf tek bir sorumluluğa sahiptir:

```
FileService          → Base64 ↔ Dosya dönüşümü
OCRService           → PDF/DOCX'ten metin çıkarma
OllamaService        → LLM entegrasyonu
DocumentClassifier   → Belge tipi tespiti
DocumentProcessor    → Ana pipeline orchestration
ExternalAPIClient    → CSB eBasvuru API iletişimi
```

### 2. Open/Closed Principle (OCP)

Sistem yeni özelliklere açık, değişikliklere kapalı:

**Yeni Belge Tipi Ekleme:**
```python
# 1. Yeni prompt template oluştur
class YeniPromptTemplate(BasePromptTemplate):
    def get_system_prompt(self) -> str:
        return "..."

    def get_user_prompt(self, text, schema) -> str:
        return f"..."

# 2. Factory'ye kaydet
PromptFactory.register_prompt("yeni_tip", YeniPromptTemplate)

# 3. Şema ekle
DOCUMENT_SCHEMAS["yeni_tip"] = YENI_SCHEMA
```

Mevcut kodu değiştirmeye gerek yok! ✅

### 3. Liskov Substitution Principle (LSP)

Tüm prompt template'leri `BasePromptTemplate`'den türer:

```python
# Her türlü prompt aynı interface'i implement eder
def process_with_prompt(prompt: BasePromptTemplate, text: str):
    system = prompt.get_system_prompt()
    user = prompt.get_user_prompt(text, schema)
    # ...
```

### 4. Interface Segregation Principle (ISP)

Servisler sadece ihtiyaç duydukları methodlara sahip:

```python
# OCRService sadece metin çıkarma ile ilgilenir
class OCRService:
    def extract_text(self, file_path) -> str
    def extract_text_from_pdf(self, file_path) -> str
    def extract_text_from_docx(self, file_path) -> str
    def extract_text_from_image(self, file_path) -> str

# LLM işlemleri ayrı bir serviste
class OllamaService:
    def generate(...) -> Dict
    def extract_structured_data(...) -> Dict
```

### 5. Dependency Inversion Principle (DIP)

Üst seviye modüller, soyutlamalara bağımlı:

```python
# DocumentProcessor → PromptFactory'ye bağımlı (concrete değil)
# PromptFactory → BasePromptTemplate'e bağımlı (abstract)

# OllamaService → PromptFactory kullanır
def extract_structured_data(self, text, document_type, schema):
    prompt_template = PromptFactory.create_prompt(document_type)
    # prompt_template: BasePromptTemplate (interface)
```

---

## 📐 Mimari Katmanlar

```
┌─────────────────────────────────────────────────────────┐
│                   API / Script Layer                     │
│  (FastAPI endpoints, Pull script, Test scripts)         │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Core Business Logic                     │
│                                                           │
│  DocumentProcessor  ─────→  DocumentClassifier          │
│         │                            │                   │
│         │                            ↓                   │
│         │                   PromptFactory                │
│         │                            │                   │
│         ↓                            ↓                   │
│   [Orchestrates]           BasePromptTemplate           │
│                                      │                   │
│                     ┌────────────────┼────────────┐     │
│                     │                │            │     │
│              OzgecmisPrompt   SGKPrompt   DiplomaPrompt │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                         │
│                                                           │
│  FileService  │  OCRService  │  OllamaService            │
│  ExternalAPIClient                                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  External Systems                        │
│                                                           │
│  CSB eBasvuru API  │  Ollama LLM  │  File System        │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 Veri Akışı

### 1. Başvuru Çekme
```
ExternalAPIClient.get_basvuru_listesi()
         ↓
API: /BasvuruListesiExternal
         ↓
[{takipNo, durum, belgeler: [base64]}]
```

### 2. Belge İşleme Pipeline
```
DocumentProcessor.process_application()
         ↓
FOR EACH belge:
         ↓
    FileService.base64_to_file()
         ↓
    OCRService.extract_text()
         ↓
    DocumentClassifier.classify()
         ↓
    PromptFactory.create_prompt(doc_type)
         ↓
    OllamaService.extract_structured_data()
         ↓
    {belge_id, belge_tipi, veri}
         ↓
DocumentProcessor.create_master_json()
         ↓
{
  basvuru_bilgileri,
  basvuran,
  egitim_durumu,
  is_deneyimi,
  sektor_dagilimi,
  uygunluk
}
```

---

## 📦 Modül Yapısı

### app/prompts/ (Yeni!)
```
prompts/
├── __init__.py                # Export all
├── base_prompt.py             # Abstract base class
├── prompt_factory.py          # Factory pattern
├── ozgecmis_prompt.py         # Özgeçmiş specific
├── sgk_prompt.py              # SGK specific
├── diploma_prompt.py          # Diploma specific
└── adli_sicil_prompt.py       # Adli sicil specific
```

**Sorumluluks:
- `BasePromptTemplate`: Interface tanımı
- `PromptFactory`: Belge tipine göre prompt seçimi
- Concrete templates: Her belge tipi için özelleştirilmiş prompt

### app/services/
```
services/
├── external_api_client.py     # CSB API integration
├── file_service.py            # Base64 ↔ File
├── ocr_service.py             # Text extraction
└── ollama_service.py          # LLM integration
```

### app/core/
```
core/
├── document_processor.py      # Main pipeline
└── document_classifier.py     # Document type detection
```

### app/models/
```
models/
├── external_api.py            # API data models
└── schemas.py                 # JSON schemas for extraction
```

---

## 🎯 Tasarım Kararları

### 1. Factory Pattern (PromptFactory)
**Neden?**
- Belge tipi → Prompt mapping merkezi
- Runtime'da yeni prompt eklenebilir
- Test edilebilir (mock factory)

**Alternatif:**
- ❌ If/else zinciri → Bakımı zor
- ❌ Hard-coded mapping → Esnek değil

### 2. Template Method Pattern (BasePromptTemplate)
**Neden?**
- Her belge tipi kendi prompt'unu özelleştirir
- Ortak davranışlar base class'ta (format_schema, truncate_text)
- Kod tekrarı önlenir

### 3. Strategy Pattern (DocumentClassifier)
**Neden?**
- Dosya adı, içerik, API verisi → 3 farklı strateji
- Öncelik sırası: API > Dosya adı > İçerik
- Her strateji bağımsız test edilebilir

### 4. Service Layer Pattern
**Neden?**
- Her external system ayrı servis
- Dependency injection kolay
- Mock'lanabilir (test için)

---

## 🧪 Test Stratejisi

### Unit Tests
```python
# Prompt factory testi
def test_prompt_factory():
    prompt = PromptFactory.create_prompt("özgeçmiş")
    assert isinstance(prompt, OzgecmisPromptTemplate)

# Document classifier testi
def test_classifier_by_filename():
    classifier = DocumentClassifier()
    doc_type = classifier.classify_by_filename("cv.pdf")
    assert doc_type == "özgeçmiş"
```

### Integration Tests
```python
# Full pipeline testi
async def test_full_pipeline():
    processor = DocumentProcessor()
    basvuru_data = {...}  # Mock data
    result = await processor.process_application(basvuru_data)
    assert "basvuran" in result
    assert "uygunluk" in result
```

---

## 🚀 Genişletme Senaryoları

### Senaryo 1: Yeni Belge Tipi (Referans Mektubu)

**Adımlar:**
1. Şema ekle (`schemas.py`)
2. Prompt template oluştur (`referans_prompt.py`)
3. Factory'ye kaydet
4. Classifier'a keyword ekle

**Değiştirilen dosyalar:** 4
**Mevcut koda dokunma:** ❌ Yok

### Senaryo 2: Farklı LLM Kullanma (GPT-4)

**Adımlar:**
1. Yeni service oluştur (`gpt_service.py`)
2. `BaseLLMService` interface tanımla
3. `OllamaService` ve `GPTService` implement et
4. `DocumentProcessor`'a dependency injection

**Değiştirilen dosyalar:** 3
**Breaking change:** ❌ Yok

### Senaryo 3: Veri Depolama (PostgreSQL)

**Adımlar:**
1. Repository pattern ekle
2. `BasvuruRepository` oluştur
3. `DocumentProcessor`'dan repository kullan

**Değiştirilen dosyalar:** 2
**Mevcut logic:** ✅ Korunur

---

## 📊 Performans Optimizasyonları

### 1. Parallel Processing
```python
# Şu an: Sequential
for belge in belgeler:
    result = await process_document(belge)

# Gelecek: Parallel
import asyncio
results = await asyncio.gather(*[
    process_document(belge)
    for belge in belgeler
])
```

### 2. Caching
```python
# Prompt caching
@lru_cache(maxsize=100)
def get_prompt(document_type: str):
    return PromptFactory.create_prompt(document_type)

# LLM response caching
# Aynı metin için tekrar LLM çağrısı yapma
```

### 3. Batch Processing
```python
# Birden fazla başvuruyu aynı anda işle
async def process_batch(basvurular: List[Dict]):
    return await asyncio.gather(*[
        process_application(b) for b in basvurular
    ])
```

---

## 🔒 Güvenlik

### 1. Input Validation
- Base64 decode güvenliği
- Dosya boyutu limiti (10MB)
- Dosya tipi kontrolü

### 2. Sensitive Data
- TC kimlik numaraları → masked logging
- API credentials → environment variables
- Geçici dosyalar → otomatik temizleme

### 3. Rate Limiting
```python
# Ollama için rate limit
class RateLimitedOllamaService(OllamaService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limiter = RateLimiter(max_calls=10, period=60)
```

---

## 📈 Metrikler ve Monitoring

### Log Seviyeleri
- `INFO`: Pipeline başlangıç/bitiş
- `DEBUG`: Detaylı veri akışı
- `WARNING`: Fallback kullanımları
- `ERROR`: İşleme hataları

### Önemli Metrikler
- Belge başına işleme süresi
- LLM yanıt süresi
- Hata oranı (belge/başvuru)
- Başarılı çıkarım oranı

---

## 🎓 Best Practices

### 1. Kod Organizasyonu
✅ Her dosya tek bir class (SRP)
✅ İlgili classlar aynı package'te
✅ Clear naming (DocumentProcessor, PromptFactory)

### 2. Error Handling
✅ Try/except her external call'da
✅ Anlamlı error messages
✅ Graceful degradation (fallback prompts)

### 3. Type Hints
✅ Tüm function signatures typed
✅ Return types açık
✅ Optional vs None explicit

### 4. Documentation
✅ Docstrings tüm public methods
✅ SOLID principles documented
✅ Architecture diagrams

---

**Güncellenme**: 2025-10-09
**Versiyon**: 1.0.0
**Durum**: Production Ready ✅
