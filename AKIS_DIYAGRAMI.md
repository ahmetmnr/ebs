# E-BAŞVURU ANALİZ SİSTEMİ - AKIŞ DİYAGRAMI

## 📋 İÇİNDEKİLER
1. [Genel Sistem Akışı](#genel-sistem-akışı)
2. [Veri Çekme Akışı](#veri-çekme-akışı)
3. [Belge İşleme Akışı](#belge-i̇şleme-akışı)
4. [Master JSON Oluşturma Akışı](#master-json-oluşturma-akışı)
5. [Validation & Requirements Akışı](#validation--requirements-akışı)

---

## 📊 GENEL SİSTEM AKIŞI

```
┌─────────────────────────────────────────────────────────────────────┐
│                         E-BAŞVURU SİSTEMİ                           │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
        ┌──────────────────┐          ┌──────────────────┐
        │  VERI ÇEKME      │          │  MANUEL IMPORT   │
        │  (API'den)       │          │  (JSON files)    │
        └────────┬─────────┘          └────────┬─────────┘
                 │                             │
                 └──────────┬──────────────────┘
                            ▼
                ┌─────────────────────┐
                │  SQLite Veritabanı  │
                │  - basvurular       │
                │  - belgeler         │
                │  - analiz_sonuclari │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  BELGE ANALİZİ      │
                │  (OCR + LLM)        │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  MASTER JSON        │
                │  Oluşturma          │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  WEB VIEWER         │
                │  (Streamlit)        │
                └─────────────────────┘
```

---

## 🔄 VERI ÇEKME AKIŞI

### Script: `scripts/sync_data_to_db.py`

```
START
  │
  ├─► init_db()
  │   └─► Tablo oluştur (basvurular, belgeler)
  │
  ├─► Her hizmet_id için DÖNGÜ:
  │   │
  │   ├─► api_client.get_basvuru_listesi(hizmet_id)
  │   │   │
  │   │   └─► CSB API: /BasvuruListesiGetir
  │   │       └─► Response: [{basvuruId, takipNo, ...}, ...]
  │   │
  │   ├─► Her başvuru için DÖNGÜ:
  │   │   │
  │   │   ├─► basvuru_var_mi(takip_no)?
  │   │   │   ├─► EVET ─► ATLA
  │   │   │   └─► HAYIR ─► Devam
  │   │   │
  │   │   ├─► api_client.get_basvuru_detay(basvuru_id)
  │   │   │   │
  │   │   │   └─► CSB API: /BasvuruDetayGetir
  │   │   │       └─► Response: {basvuruBilgileri, belgeler: [...]}
  │   │   │
  │   │   ├─► Her belge için DÖNGÜ:
  │   │   │   │
  │   │   │   ├─► api_client.get_belge(belge_id)
  │   │   │   │   │
  │   │   │   │   └─► CSB API: /BelgeIndir
  │   │   │   │       └─► Response: {dosyaByte: base64}
  │   │   │   │
  │   │   │   └─► Belge listesine ekle
  │   │   │
  │   │   └─► basvuru_kaydet(takip_no, detay, belgeler)
  │   │       │
  │   │       ├─► INSERT INTO basvurular
  │   │       └─► INSERT INTO belgeler (her belge için)
  │   │
  │   └─► Sonraki hizmet
  │
  └─► get_stats()
      └─► İstatistikleri göster
```

---

## 📄 BELGE İŞLEME AKIŞI

### Script: `scripts/analyze_from_db_v2.py`

```
START
  │
  ├─► init_analiz_table()
  │   └─► CREATE TABLE analiz_sonuclari
  │
  ├─► get_analiz_edilmemis(limit=10)
  │   └─► SELECT FROM basvurular WHERE NOT IN analiz_sonuclari
  │
  └─► Her başvuru için DÖNGÜ:
      │
      ├─► Başvuru JSON'unu parse et
      │   └─► basvuruBelgeListesi → belgeler[]
      │
      └─► Her belge için DÖNGÜ:
          │
          ├─► api_belge_tipi = belge.get("belgeTipi")  ← API'den
          │   base64_data = belge.get("dosyaByte")
          │
          ├─► DocumentClassifier.classify()
          │   │
          │   ├─► belge_tipi == null?
          │   │   ├─► EVET ─► return "ustyazi"
          │   │   └─► HAYIR ─► turkish_lower(belge_tipi)
          │   │
          │   └─► Örnek: "Proje Dosyası (1)" → "proje dosyası (1)"
          │
          ├─► belge_kaydet(takip_no, belge_adi, base64_data)
          │   │
          │   ├─► base64.b64decode(base64_data)
          │   └─► Dosyayı temp/ klasörüne yaz
          │
          ├─► OCR İşlemi:
          │   │
          │   ├─► OCRService.extract_text(belge_path)
          │   │   │
          │   │   ├─► Dosya türü?
          │   │   │   ├─► PDF ─► PyMuPDF (fitz)
          │   │   │   ├─► Image ─► Tesseract OCR
          │   │   │   └─► Diğer ─► textract
          │   │   │
          │   │   └─► return text (string)
          │   │
          │   └─► Metin < 50 karakter?
          │       ├─► EVET ─► SKIP (çok az metin)
          │       └─► HAYIR ─► Devam
          │
          ├─► PromptFactory.create_prompt(belge_tipi)
          │   │
          │   ├─► _PROMPT_MAP'ten prompt_class bul
          │   │   │
          │   │   ├─► "özgeçmiş/cv" ─► OzgecmisPromptTemplate
          │   │   ├─► "sgk hizmet dökümü" ─► SGKPromptTemplate
          │   │   ├─► "proje dosyası (1)" ─► AkademikProjePromptTemplate
          │   │   ├─► "enerji üretimi" ─► SektorBelgePromptTemplate
          │   │   └─► ... (diğer tipler)
          │   │
          │   └─► return prompt_instance
          │
          ├─► DOCUMENT_SCHEMAS[belge_tipi] ─► schema
          │
          ├─► Prompt hazırla:
          │   │
          │   ├─► system_prompt = prompt.get_system_prompt()
          │   └─► user_prompt = prompt.get_user_prompt(text, schema)
          │
          ├─► OllamaService.generate()
          │   │
          │   ├─► POST llm.csb.gov.tr/api/generate
          │   ├─► model: "gemma3:27b"
          │   ├─► prompt: system + user
          │   ├─► format: "json"
          │   └─► temperature: 0.0
          │   │
          │   └─► return JSON response
          │
          ├─► Sonucu kaydet:
          │   │
          │   ├─► belge_tipi == "özgeçmiş/cv"?
          │   │   └─► sonuclar["cv_analiz"] = json
          │   ├─► belge_tipi == "sgk hizmet dökümü"?
          │   │   └─► sonuclar["sgk_analiz"] = json
          │   ├─► belge_tipi == "adli sicil kaydı"?
          │   │   └─► sonuclar["sicil_analiz"] = json
          │   └─► ... (diğer tipler)
          │
          └─► analiz_kaydet(takip_no, sonuclar)
              │
              └─► INSERT INTO analiz_sonuclari
```

---

## 🏗️ MASTER JSON OLUŞTURMA AKIŞI

### Class: `DocumentProcessor.create_master_json()`

```
START: create_master_json(basvuru_info, belgeler)
  │
  ├─► ADIM 1: Belgeleri İşle
  │   │
  │   └─► Her belge için process_document():
  │       │
  │       ├─► OCR ─► text
  │       │
  │       ├─► DocumentClassifier.classify(belge_tipi)
  │       │   └─► Normalized belge_tipi
  │       │
  │       ├─► ÖZEL DURUM: "Proje Dosyası (1/2/3)"?
  │       │   └─► doc_type = "akademik proje"
  │       │
  │       ├─► PromptFactory.create_prompt(doc_type, basvuru_turu)
  │       │   │
  │       │   ├─► Özgeçmiş için başvuru türüne göre:
  │       │   │   ├─► "akademisyen" ─► OzgecmisAkademisyenPrompt
  │       │   │   ├─► "bakanlık" ─► OzgecmisBakanlikPrompt
  │       │   │   └─► "sektör" ─► OzgecmisSektorPrompt
  │       │   │
  │       │   └─► Diğer belgeler için standart prompt
  │       │
  │       ├─► DOCUMENT_SCHEMAS[doc_type] ─► schema
  │       │
  │       ├─► OllamaService.extract_structured_data()
  │       │   └─► LLM ile veri çıkar
  │       │
  │       └─► return {
  │               belge_id, belge_adi, belge_tipi,
  │               api_belge_tipi, durum, veri, base64
  │           }
  │
  ├─► ADIM 2: Verileri Gruplama
  │   │
  │   └─► Her işlenmiş belge için:
  │       │
  │       ├─► "ustyazi" ─► ustyazi_data
  │       ├─► "özgeçmiş" ─► ozgecmis_data
  │       ├─► "sgk" ─► sgk_data
  │       ├─► "diploma" ─► diploma_data
  │       ├─► "adli sicil" ─► adli_sicil_data
  │       ├─► "hitap" ─► hitap_data
  │       ├─► "proje" ─► akademik_proje_data[]
  │       └─► "sektör" ─► sektor_belge_data[]
  │
  ├─► ADIM 3: Başvuran Bilgilerini Güncelle
  │   │
  │   └─► Özgeçmişten:
  │       ├─► ad, soyad, tc_kimlik_no
  │       ├─► dogum_tarihi, telefon, email
  │       └─► basvuran_info güncelle
  │
  ├─► ADIM 4: Türetilmiş Veriler
  │   │
  │   ├─► _extract_education_info()
  │   │   └─► Diploma + Özgeçmiş ─► egitim_durumu
  │   │
  │   ├─► _extract_experience_info()
  │   │   └─► SGK + Özgeçmiş ─► is_deneyimi
  │   │
  │   ├─► _calculate_sector_distribution()
  │   │   └─► is_deneyimi ─► sektor_dagilimi
  │   │
  │   ├─► _detect_applied_sectors()
  │   │   └─► is_deneyimi ─► basvurulan_sektorler
  │   │
  │   ├─► _check_sector_documents()
  │   │   └─► sektor_dagilimi ─► sektor_belge_durumu
  │   │
  │   ├─► _extract_projects_publications()
  │   │   └─► Özgeçmiş ─► projeler_yayinlar
  │   │
  │   └─► _extract_adli_sicil_info()
  │       └─► adli_sicil_data ─► adli_sicil_bilgileri
  │
  ├─► ADIM 5: Başvuru Türünü Tespit Et
  │   │
  │   ├─► ustYazi var mı?
  │   │   ├─► EVET ─► ustYazi.basvuran_bilgileri.basvuru_turu
  │   │   └─► HAYIR ─► hizmet_adi'den tespit et
  │   │
  │   ├─► _detect_application_type(hizmet_adi)
  │   │   │
  │   │   ├─► "Akademisyen" ─► "Akademisyen"
  │   │   ├─► "Eski Bakanlık" ─► "Eski Bakanlık Personeli"
  │   │   └─► "Sektör" ─► "Sektör Çalışanı"
  │   │
  │   └─► _detect_application_level(hizmet_adi)
  │       │
  │       ├─► "Baş Sorumlusu" ─► "Başsorumlu"
  │       └─► "Sorumlusu" ─► "Sorumlu"
  │
  ├─► ADIM 6: VALIDATION (Tutarlılık Kontrolü)
  │   │
  │   └─► DocumentValidator.validate_application()
  │       │
  │       ├─► İsim Tutarlılığı:
  │       │   │
  │       │   └─► Her belgedeki isim aynı mı?
  │       │       ├─► Özgeçmiş ismi
  │       │       ├─► Diploma ismi
  │       │       ├─► SGK ismi
  │       │       ├─► Adli Sicil ismi
  │       │       └─► Benzerlik < %80 ─► HATA
  │       │
  │       ├─► TC Kimlik Tutarlılığı:
  │       │   └─► TC numarası her yerde aynı mı?
  │       │
  │       ├─► Tarih Tutarlılığı:
  │       │   └─► Mezuniyet < İş başlangıç < Bugün?
  │       │
  │       ├─► SGK vs Özgeçmiş Tutarlılığı:
  │       │   │
  │       │   └─► Özgeçmişteki şirketler SGK'da var mı?
  │       │       └─► Yoksa ─► UYARI
  │       │
  │       └─► return {
  │               valid: bool,
  │               consistency_score: 0-100,
  │               errors: [...],
  │               warnings: [...]
  │           }
  │
  ├─► ADIM 7: REQUIREMENTS (Zorunlu Belgeler)
  │   │
  │   └─► DocumentRequirementsChecker.check_requirements()
  │       │
  │       ├─► hizmet_adi ─► normalize (turkish_lower)
  │       │
  │       ├─► REQUIREMENTS_BY_HIZMET[hizmet_adi]
  │       │   │
  │       │   └─► {
  │       │         "yök lisans diploması": True,
  │       │         "sgk hizmet dökümü": True,
  │       │         "proje dosyası (1)": True,
  │       │         ...
  │       │       }
  │       │
  │       ├─► Her zorunlu belge için:
  │       │   │
  │       │   └─► processed_documents'ta var mı?
  │       │       ├─► EVET ─► total_found++
  │       │       └─► HAYIR ─► HATA (Eksik belge)
  │       │
  │       ├─► completeness_score = (found/required) * 100
  │       │
  │       └─► return {
  │               valid: bool,
  │               missing_documents: [...],
  │               completeness_score: 0-100
  │           }
  │
  ├─► ADIM 8: UYGUNLUK DEĞERLENDİRMESİ
  │   │
  │   └─► _evaluate_eligibility()
  │       │
  │       ├─► Adli Sicil Kontrolü:
  │       │   │
  │       │   ├─► sabika_kaydi == true?
  │       │   │   └─► UYGUN DEĞİL
  │       │   │
  │       │   └─► yuz_kizartici_suc == true?
  │       │       └─► UYGUN DEĞİL
  │       │
  │       ├─► Eğitim Kontrolü:
  │       │   │
  │       │   └─► Lisans diploması var mı?
  │       │       └─► YOKSA ─► UYGUN DEĞİL
  │       │
  │       ├─► Deneyim Kontrolü (Başvuru türüne göre):
  │       │   │
  │       │   ├─► Akademisyen:
  │       │   │   │
  │       │   │   ├─► Sorumlu: 1 proje zorunlu
  │       │   │   └─► Başsorumlu: 3 proje zorunlu
  │       │   │
  │       │   ├─► Eski Bakanlık:
  │       │   │   │
  │       │   │   └─► Hitap deneyimi > 0?
  │       │   │
  │       │   └─► Sektör Çalışanı:
  │       │       │
  │       │       └─► SGK sektör deneyimi > 0?
  │       │
  │       ├─► Validation Kontrolü:
  │       │   │
  │       │   └─► consistency_score < %50?
  │       │       └─► UYARI (Tutarsızlık)
  │       │
  │       └─► return {
  │               uygun: "Uygun" / "Uygun Değil" / "Şartlı Uygun",
  │               uygunluk_skoru: 0-100,
  │               eksiklikler: [...],
  │               oneriler: [...]
  │           }
  │
  └─► ADIM 9: MASTER JSON Oluştur
      │
      └─► return {
              basvuru_bilgileri: {
                  takip_no, hizmet_adi, basvuru_tarihi,
                  basvuru_turu, basvurulan_alan
              },
              basvuran_bilgileri: {
                  ad, soyad, tc_kimlik_no, telefon, email
              },
              basvurulan_sektorler: [...],

              egitim_durumu: {...},
              is_deneyimi: [...],
              sektor_dagilimi: {...},
              sektor_belge_durumu: {...},
              projeler_yayinlar: {...},

              validation: {
                  tutarli: bool,
                  consistency_score: 0-100,
                  errors: [...],
                  warnings: [...]
              },

              requirements: {
                  tamamlanma: bool,
                  completeness_score: 0-100,
                  eksik_belgeler: [...]
              },

              uygunluk: {
                  uygun: "Uygun",
                  uygunluk_skoru: 85,
                  eksiklikler: [...],
                  oneriler: [...]
              },

              belgeler: [
                  {
                      belge_id, belge_adi, belge_tipi,
                      api_belge_tipi, durum, base64
                  },
                  ...
              ]
          }
```

---

## ✅ VALIDATION & REQUIREMENTS AKIŞI

```
┌─────────────────────────────────────────────────────────────┐
│              VALIDATION & REQUIREMENTS AKIŞI                 │
└─────────────────────────────────────────────────────────────┘

┌───────────────────┐
│  MASTER JSON      │
│  Oluşturma        │
└─────────┬─────────┘
          │
          ├─► 1. VALIDATION (Tutarlılık)
          │   │
          │   ├─► İsim Kontrolü
          │   │   │
          │   │   ├─► Başvuru.ad_soyad
          │   │   ├─► Özgeçmiş.ad_soyad
          │   │   ├─► Diploma.ad_soyad
          │   │   ├─► SGK.ad_soyad
          │   │   └─► Adli Sicil.ad_soyad
          │   │       │
          │   │       ├─► Benzerlik Hesapla (Levenshtein)
          │   │       │
          │   │       ├─► Benzerlik > %80 ─► OK
          │   │       └─► Benzerlik < %80 ─► HATA
          │   │
          │   ├─► TC Kimlik Kontrolü
          │   │   │
          │   │   └─► Tüm belgelerde aynı TC?
          │   │       ├─► EVET ─► OK
          │   │       └─► HAYIR ─► HATA
          │   │
          │   ├─► Tarih Tutarlılığı
          │   │   │
          │   │   └─► mezuniyet < iş_başlangıç < bugün?
          │   │       ├─► EVET ─► OK
          │   │       └─► HAYIR ─► HATA
          │   │
          │   ├─► SGK vs Özgeçmiş
          │   │   │
          │   │   └─► CV'deki şirketler SGK'da var mı?
          │   │       ├─► EVET ─► OK
          │   │       └─► HAYIR ─► UYARI
          │   │
          │   └─► Consistency Score Hesapla
          │       │
          │       └─► (doğru_kontrol / toplam_kontrol) * 100
          │
          ├─► 2. REQUIREMENTS (Zorunlu Belgeler)
          │   │
          │   ├─► hizmet_adi normalize
          │   │   │
          │   │   └─► "Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)"
          │   │       ↓
          │   │       "sanayide yeşil dönüşüm sorumlusu (akademisyen)"
          │   │
          │   ├─► REQUIREMENTS_BY_HIZMET[hizmet_adi]
          │   │   │
          │   │   └─► {
          │   │         "yök lisans diploması": True,
          │   │         "sgk hizmet dökümü": True,
          │   │         "adli sicil kaydı": True,
          │   │         "hitap hizmet dökümü": True,
          │   │         "özgeçmiş/cv": True,
          │   │         "fotoğraf (vesikalık)": True,
          │   │         "proje dosyası (1)": True,
          │   │         "enerji üretimi": False,  ← Zorunlu değil
          │   │         ...
          │   │       }
          │   │
          │   ├─► Belgeleri Kontrol Et
          │   │   │
          │   │   └─► Her zorunlu belge için:
          │   │       │
          │   │       ├─► processed_documents'ta var mı?
          │   │       │   ├─► VAR ─► total_found++
          │   │       │   └─► YOK ─► missing_documents.append()
          │   │       │
          │   │       └─► Sonraki belge
          │   │
          │   └─► Completeness Score Hesapla
          │       │
          │       └─► (total_found / total_required) * 100
          │
          └─► 3. UYGUNLUK DEĞERLENDİRMESİ
              │
              ├─► Kritik Kontroller:
              │   │
              │   ├─► Adli sicil var mı? ─► UYGUN DEĞİL
              │   ├─► Lisans diploması yok? ─► UYGUN DEĞİL
              │   └─► Consistency < %50? ─► ŞARTLı UYGUN
              │
              ├─► Başvuru Türüne Göre:
              │   │
              │   ├─► Akademisyen Sorumlu:
              │   │   └─► 1 proje var mı?
              │   │
              │   ├─► Akademisyen Başsorumlu:
              │   │   └─► 3 proje var mı?
              │   │
              │   ├─► Eski Bakanlık:
              │   │   └─► Hitap deneyimi var mı?
              │   │
              │   └─► Sektör Çalışanı:
              │       └─► SGK sektör deneyimi var mı?
              │
              └─► Sonuç:
                  │
                  ├─► uygun: "Uygun" / "Uygun Değil" / "Şartlı Uygun"
                  ├─► uygunluk_skoru: 0-100
                  ├─► eksiklikler: [...]
                  └─► oneriler: [...]
```

---

## 📊 VERİ AKIŞ TABLOSU

| Katman | Input | İşlem | Output |
|--------|-------|-------|--------|
| **API Layer** | CSB API | Başvuru + Belge çekme | JSON + Base64 |
| **Database Layer** | JSON + Base64 | SQLite kayıt | basvurular, belgeler |
| **OCR Layer** | Base64 → File | PyMuPDF/Tesseract | Text |
| **Classifier Layer** | belgeTipi (API) | turkish_lower | Normalized tip |
| **Prompt Layer** | belge_tipi | PromptFactory | Prompt Template |
| **LLM Layer** | Text + Prompt | Ollama (Gemma3:27b) | Structured JSON |
| **Processor Layer** | Tüm belgeler | DocumentProcessor | Master JSON |
| **Validation Layer** | Master JSON | Tutarlılık kontrolü | Scores + Errors |
| **Requirements Layer** | hizmet_adi | Zorunlu belgeler | Completeness |
| **UI Layer** | Master JSON | Streamlit viewer | Web görünüm |

---

## 🔑 ÖNEMLİ NOKTALAR

### 1. Belge Tipi Belirleme
```
API belgeTipi ─► turkish_lower ─► DOCUMENT_SCHEMAS/PROMPT_MAP
```
- **ASLA** dosya adından tahmin yapılmıyor
- **SADECE** API'den gelen değer kullanılıyor

### 2. Belge Zorunlulukları
```
hizmetAdi ─► REQUIREMENTS_BY_HIZMET[hizmet_adi] ─► {belge: True/False}
```
- **Hizmet adı** bazlı (başvuru türü + alan ayrı değil)
- Kullanıcının verdiği tabloya %100 uygun

### 3. OCR → LLM Pipeline
```
PDF/Image ─► OCR ─► Text ─► Prompt + Schema ─► LLM ─► JSON
```
- OCR başarısız ─► SKIP
- Text < 50 karakter ─► SKIP
- Prompt bulunamadı ─► SKIP
- Schema bulunamadı ─► SKIP

### 4. Validation Mekanizması
```
İsim + TC + Tarih tutarlılığı ─► Consistency Score
SGK vs CV karşılaştırma ─► Warnings
```
- Score < %50 ─► HATA
- Score %50-80 ─► UYARI
- Score > %80 ─► OK

---

## 🎯 ÖRNEK SENARYO

### Senaryo: Akademisyen Sorumlu Başvurusu

```
1. API'den Veri Çekme:
   └─► takip_no: 5946315
   └─► hizmet_adi: "Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)"
   └─► belgeler: [
         {belgeTipi: null, belgeAdi: "5946315-ustYazi.pdf"},
         {belgeTipi: "Özgeçmiş/CV", belgeAdi: "cv.pdf"},
         {belgeTipi: "SGK Hizmet Dökümü", belgeAdi: "sgk.pdf"},
         {belgeTipi: "Yök Lisans Diploması", belgeAdi: "diploma.pdf"},
         {belgeTipi: "Proje Dosyası (1)", belgeAdi: "proje1.pdf"}
       ]

2. Belge İşleme:
   ├─► ustYazi: belgeTipi=null → "ustyazi" → UstYaziPrompt
   ├─► cv.pdf: belgeTipi="Özgeçmiş/CV" → "özgeçmiş/cv" → OzgecmisAkademisyenPrompt
   ├─► sgk.pdf: belgeTipi="SGK Hizmet Dökümü" → "sgk hizmet dökümü" → SGKPrompt
   ├─► diploma.pdf: belgeTipi="Yök Lisans Diploması" → "yök lisans diploması" → DiplomaPrompt
   └─► proje1.pdf: belgeTipi="Proje Dosyası (1)" → "proje dosyası (1)" → AkademikProjePrompt

3. LLM Analizi:
   └─► Her belge için OCR → Text → LLM → JSON

4. Requirements Check:
   └─► hizmet_adi: "sanayide yeşil dönüşüm sorumlusu (akademisyen)"
   └─► Zorunlu: [cv, sgk, diploma, hitap, adli sicil, fotoğraf, proje(1)]
   └─► Bulunan: [cv, sgk, diploma, proje(1)]
   └─► Eksik: [hitap, adli sicil, fotoğraf]
   └─► Completeness: 57%

5. Validation:
   └─► İsim tutarlılığı: OK (%95)
   └─► TC tutarlılığı: OK
   └─► Consistency Score: 85%

6. Uygunluk:
   └─► Eksik belgeler var ─► "Şartlı Uygun"
   └─► Uygunluk Skoru: 65%
   └─► Öneriler: "Hitap, Adli Sicil ve Fotoğraf ekleyin"
```

---

## 📁 DOSYA YAPILARı

### Veritabanı Şeması
```sql
basvurular (
    takip_no TEXT PRIMARY KEY,
    hizmet_id TEXT,
    hizmet_adi TEXT,
    json_data TEXT  -- Full JSON
)

belgeler (
    id INTEGER PRIMARY KEY,
    takip_no TEXT,
    belge_id TEXT,
    belge_tipi TEXT,  -- API'den gelen
    belge_adi TEXT,
    base64_data TEXT,
    FOREIGN KEY (takip_no)
)

analiz_sonuclari (
    takip_no TEXT PRIMARY KEY,
    cv_analiz TEXT,
    sgk_analiz TEXT,
    diploma_analiz TEXT,
    analiz_tarihi TEXT,
    FOREIGN KEY (takip_no)
)
```

### Master JSON Yapısı
```json
{
  "basvuru_bilgileri": {},
  "basvuran_bilgileri": {},
  "basvurulan_sektorler": [],
  "egitim_durumu": {},
  "is_deneyimi": [],
  "sektor_dagilimi": {},
  "projeler_yayinlar": {},
  "validation": {
    "tutarli": true,
    "consistency_score": 85
  },
  "requirements": {
    "tamamlanma": false,
    "completeness_score": 57,
    "eksik_belgeler": ["hitap", "adli sicil"]
  },
  "uygunluk": {
    "uygun": "Şartlı Uygun",
    "uygunluk_skoru": 65
  },
  "belgeler": []
}
```

---

## 🚀 SCRIPT'LER VE KULLANIM

| Script | Amaç | Kullanım |
|--------|------|----------|
| `sync_data_to_db.py` | API'den veri çek | `python scripts/sync_data_to_db.py` |
| `import_existing_to_db.py` | JSON dosyalarını import et | `python scripts/import_existing_to_db.py` |
| `analyze_from_db_v2.py` | Belgeleri analiz et | `python scripts/analyze_from_db_v2.py` |
| `viewer/app.py` | Web arayüzü | `streamlit run viewer/app.py` |
| `viewer/app_optimized.py` | Optimize edilmiş viewer | `streamlit run viewer/app_optimized.py` |

---

**Son Güncelleme:** 2025-01-20
**Versiyon:** 2.0
