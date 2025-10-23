# Kurulum ve Test Rehberi

## ✅ Tamamlanan İşler

### 1. Proje Yapısı Oluşturuldu

```
ebasvuru/
├── app/
│   ├── models/
│   │   └── external_api.py        # API veri modelleri
│   ├── services/
│   │   └── external_api_client.py # CSB API client
│   ├── config.py                   # Konfigürasyon
│   └── core/
│
├── scripts/
│   ├── test_external_api.py       # API test
│   ├── pull_basvurular.py         # Manuel çekme
│   └── inspect_basvuru.py         # Veri inceleme
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

### 2. API Entegrasyonu Test Edildi

✅ Hizmet Listesi: **156 hizmet başarıyla çekildi**
✅ Başvuru Listesi: **2 başvuru bulundu**

```
Başvuru 1:
  Takip No: 067680
  Hizmet  : Sanayide Yeşil Dönüşüm Baş Sorumlusu
  Durum   : İşleme Alındı
  Tarih   : 2025-03-19
  Belgeler: 1 adet (067680-ustYazi.pdf)
```

### 3. Yapılandırma Hazır

- API bağlantı bilgileri
- Timeout ayarları
- Logging konfigürasyonu

## 🚀 Hızlı Başlangıç

### 1. Sanal Ortam Oluştur

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 2. Bağımlılıkları Yükle

```bash
pip install requests python-dateutil pydantic pydantic-settings
```

### 3. API Testi Yap

```bash
python scripts/test_external_api.py
```

Beklenen çıktı:
```
======================================================================
CSB eBasvuru API Test
======================================================================

1️⃣  HİZMET LİSTESİ TEST
----------------------------------------------------------------------
✅ Status: 200
✅ Toplam: 156 hizmet

2️⃣  BAŞVURU LİSTESİ TEST
----------------------------------------------------------------------
✅ Status: 200
✅ Toplam: 2 başvuru
```

### 4. Başvuru Verisini İncele

```bash
python scripts/inspect_basvuru.py
```

## 📋 Sonraki Adımlar

### Faz 1: Belge İndirme (Yapılacak)

- [ ] Belge indirme endpoint'ini bul ve test et
- [ ] Base64 decode işlemi
- [ ] PDF/DOCX dosya kaydetme

### Faz 2: OCR Entegrasyonu (Yapılacak)

- [ ] EasyOCR kurulumu
- [ ] PDF'den metin çıkarma
- [ ] DOCX'ten metin çıkarma
- [ ] OCR servisi implementasyonu

### Faz 3: LLM Entegrasyonu (Yapılacak)

- [ ] Ollama kurulumu
- [ ] Model indirme (gemma3:27b)
- [ ] Prompt şablonları
- [ ] LLM servisi implementasyonu

### Faz 4: İşleme Pipeline (Yapılacak)

- [ ] DocumentProcessor sınıfı
- [ ] Sektör hesaplama
- [ ] Validasyon
- [ ] Master JSON oluşturma

### Faz 5: Sonuç Gönderme (Yapılacak)

- [ ] Sonuç gönderme endpoint'i
- [ ] Hata yönetimi
- [ ] Retry mekanizması

## 🔍 API Endpoint Durumu

| Endpoint | Durum | Not |
|----------|-------|-----|
| `/Hizmet/HizmetListesiExternal` | ✅ | 156 hizmet |
| `/Basvuru/BasvuruListesiExternal` | ✅ | 2 başvuru |
| `/Basvuru/BasvuruDetayExternal` | ❌ | 404 - Farklı isim olabilir |
| `/Basvuru/BelgeIndirExternal` | ❓ | Test edilmedi |

## 💡 Önemli Notlar

1. **Başvuru Listesi Özelliği**: GET request ama JSON body ile gönderilmeli!

```python
response = requests.request(
    method='GET',
    url=url,
    json=payload,  # Body parametresi!
    auth=auth
)
```

2. **Windows Encoding**: Script'lerde UTF-8 encoding fix eklendi:

```python
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

3. **Belgeler Zaten Base64**: API'den gelen `dosyaByte` alanı zaten base64 encoded!

## 🐛 Bilinen Sorunlar

1. **Başvuru Detay Endpoint**: Mevcut endpoint adı çalışmıyor (404)
   - Alternatif: Başvuru listesinde zaten bazı detaylar var
   - `basvuruBelgeListesi` array'inde belgeler listeleniyor
   - Her belgede `dosyaByte` (base64) zaten mevcut!

2. **Çözüm**: Belge indirme endpoint'ine ihtiyaç olmayabilir!
   - Başvuru listesindeki `basvuruBelgeListesi` kullanılabilir
   - `dosyaByte` alanı zaten base64 encoded PDF içeriyor

## 📞 İletişim

Sorun bildirmek veya öneride bulunmak için:
- GitHub Issues
- Proje Ekibi

---

**Durum**: Temel API entegrasyonu tamamlandı ✅
**Sonraki**: OCR ve LLM entegrasyonu 🚀
