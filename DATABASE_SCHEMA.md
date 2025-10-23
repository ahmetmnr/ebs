# Database Schema

## Database: `data/basvurular.db` (SQLite)

---

## Tables

### 1. `basvurular` (Applications)

Stores raw application data pulled from CSB API.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `takip_no` | TEXT | PRIMARY KEY | Application tracking number (unique ID) |
| `hizmet_id` | TEXT | NOT NULL | Service ID (10307-10312 for SYD services) |
| `json_data` | TEXT | NOT NULL | Complete JSON from API |
| `cekme_tarihi` | TEXT | NOT NULL | Pull timestamp (ISO format) |

**Row count:** 2088 applications

**json_data Structure:**
```json
{
  "basvuruId": "12345",
  "takipNo": "5972438",
  "basvuruTarihi": "2025-01-15",
  "hizmetAdi": "Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)",
  "basvuruYapanVatandasTC": "12345678901",
  "basvuruYapanAd": "Ahmet",
  "basvuruYapanSoyad": "Yılmaz",
  "basvuruDurum": "Onaylandı",
  "kararDurum": "Beklemede",
  "basvuruBelgeListesi": [
    {
      "belgeAdi": "ozgecmis.pdf",
      "belgeTipi": "Özgeçmiş/CV",
      "dosyaByte": "base64_encoded_data..."
    }
  ]
}
```

**Service IDs (hizmet_id):**
- `10307` - Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)
- `10308` - Sanayide Yeşil Dönüşüm Baş Sorumlusu (Akademisyen)
- `10309` - Sanayide Yeşil Dönüşüm Sorumlusu (Bakanlık Personeli)
- `10310` - Sanayide Yeşil Dönüşüm Baş Sorumlusu (Bakanlık Personeli)
- `10311` - Sanayide Yeşil Dönüşüm Sorumlusu (Sektör Çalışanı)
- `10312` - Sanayide Yeşil Dönüşüm Baş Sorumlusu (Sektör Çalışanı)

---

### 2. `analiz_sonuclari` (Analysis Results)

Stores analysis results for each application (OLD SCHEMA - DEPRECATED).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `takip_no` | TEXT | PRIMARY KEY, FK → basvurular | Application tracking number |
| `cv_analiz` | TEXT | NULL | JSON: CV/Resume analysis result |
| `sgk_analiz` | TEXT | NULL | JSON: SGK service record analysis |
| `diploma_analiz` | TEXT | NULL | JSON: Diploma analysis |
| `sicil_analiz` | TEXT | NULL | JSON: Criminal record analysis |
| `diger_belgeler` | TEXT | NULL | JSON: Other documents array |
| `analiz_tarihi` | TEXT | NOT NULL | Analysis timestamp (ISO format) |
| `durum` | TEXT | NOT NULL | Status: `basarili` or `hata` |

**Row count:** 6 applications analyzed

**⚠️ NOTE:** This table schema is **DEPRECATED**. The new `analyze_from_db.py` script uses a different schema:

```sql
CREATE TABLE IF NOT EXISTS analiz_sonuclari (
    takip_no TEXT PRIMARY KEY,
    master_json TEXT NOT NULL,        -- Complete Master JSON
    analiz_tarihi TEXT NOT NULL,      -- Analysis timestamp
    durum TEXT NOT NULL,              -- Status: basarili/hata
    FOREIGN KEY (takip_no) REFERENCES basvurular(takip_no)
)
```

**master_json Structure:**
```json
{
  "basvuru_bilgileri": {
    "basvuru_id": "5972438",
    "takip_no": "5972438",
    "basvuru_tarihi": "2025-01-15",
    "hizmet_adi": "Sanayide Yeşil Dönüşüm Sorumlusu (Akademisyen)",
    "basvuru_turu": "Akademisyen",
    "basvurulan_alan": "Sorumlu"
  },
  "basvuran": {
    "ad": "Ahmet",
    "soyad": "Yılmaz",
    "tc_kimlik_no": "12345678901",
    "dogum_tarihi": "1985-05-15",
    "telefon": "0555 123 4567",
    "email": "ahmet@example.com"
  },
  "egitim_durumu": {
    "lisans": {
      "universite": "İTÜ",
      "bolum": "Çevre Mühendisliği",
      "mezuniyet_tarihi": "2007-06-15"
    }
  },
  "is_deneyimi": [
    {
      "sirket_adi": "ABC A.Ş.",
      "pozisyon": "Çevre Mühendisi",
      "baslangic_tarihi": "2007-09-01",
      "bitis_tarihi": "2015-12-31",
      "sektor": "Enerji Üretimi",
      "calisma_suresi_gun": 3043
    }
  ],
  "sektor_dagilimi": {
    "enerji üretimi": 3043,
    "metal üretimi ve işlemesi": 0
  },
  "adli_sicil": {
    "sabika_durumu": "temiz",
    "yuz_kizartici_suc": false
  },
  "projeler_ve_yayinlar": {
    "projeler": [],
    "yayinlar": []
  },
  "uygunluk": {
    "genel_uygunluk": "uygun",
    "eksiklikler": []
  },
  "validation": {
    "status": "valid",
    "errors": []
  },
  "requirements": {
    "status": "complete",
    "missing": []
  },
  "tablolar": {
    "tablo1_temel_bilgiler": {...},
    "tablo2_basvurulan_sektorler": {...},
    "tablo3_sektor_tecrubesi": {...},
    "tablo4_adli_sicil": {...},
    "tablo5_sektor_belge_durumu": {...},
    "tablo6_proje_yayin": {...},
    "tablo7_mezuniyet": {...},
    "tablo8_sonuc": {...}
  }
}
```

---

## Document Types (belgeTipi from API)

All possible document types from API:

1. **null** → Mapped to `ustyazi` (cover letter)
2. **Yök Lisans Diploması** → Undergraduate diploma
3. **SGK Hizmet Dökümü** → Social security service record
4. **Adli Sicil Kaydı** → Criminal record
5. **Hitap Hizmet Dökümü** → Ministry service record
6. **Özgeçmiş/CV** → Resume/CV
7. **Fotoğraf (vesikalık)** → ID photo
8. **Proje Dosyası (1)** → Academic project file 1
9. **Proje Dosyası (2)** → Academic project file 2
10. **Proje Dosyası (3)** → Academic project file 3
11. **Enerji Üretimi** → Energy production sector document
12. **Metal Üretimi ve İşlemesi** → Metal production sector document
13. **Mineral Endüstrisi** → Mineral industry sector document
14. **Kimya Endüstrisi** → Chemical industry sector document
15. **Atık Yönetimi** → Waste management sector document
16. **Diğer Üretim Faaliyetleri** → Other production activities document

---

## Relationships

```
basvurular (1) ←→ (0..1) analiz_sonuclari
     ↑
     └─ takip_no (PK)
```

- One application can have zero or one analysis result
- `analiz_sonuclari.takip_no` is a foreign key to `basvurular.takip_no`

---

## Data Flow

1. **Data Pull**: `scripts/sync_data_to_db.py` pulls applications from CSB API
   - Stores in `basvurular` table
   - `json_data` contains complete API response

2. **Analysis**: `scripts/analyze_from_db.py` processes applications
   - Reads from `basvurular`
   - Extracts documents from `json_data.basvuruBelgeListesi`
   - Decodes base64 → OCR → LLM analysis
   - Creates Master JSON with 8 tables
   - Stores result in `analiz_sonuclari.master_json`
   - Logs LLM requests/responses in `llm_logs/{takip_no}/`

3. **Viewing**: Streamlit viewer reads from `analiz_sonuclari`
   - Displays Master JSON in UI
   - Shows 8 validation tables
   - Document preview from base64

---

## Scripts

### Data Pull
- `scripts/sync_data_to_db.py` - Pull applications from CSB API to DB

### Analysis
- `scripts/analyze_from_db.py` - Analyze applications and create Master JSON
  - Usage: `python scripts/analyze_from_db.py --limit 20`
  - Processes unanalyzed applications
  - Creates Master JSON with validation tables
  - Logs to `llm_logs/{takip_no}/`

### Viewing
- `streamlit run viewer_app.py` - Web UI for viewing analysis results

---

## File Storage

- **Database**: `data/basvurular.db`
- **LLM Logs**: `llm_logs/{takip_no}/{document_type}_{timestamp}.json`
- **Temp Files**: `temp/analiz/{takip_no}/{belge_adi}`
  - Cleaned up after processing

---

## Indexes

No custom indexes. Primary keys are automatically indexed by SQLite.

To improve query performance, consider adding:
```sql
CREATE INDEX idx_hizmet_id ON basvurular(hizmet_id);
CREATE INDEX idx_durum ON analiz_sonuclari(durum);
```

---

## Backup

To backup the database:
```bash
sqlite3 data/basvurular.db ".backup data/basvurular_backup.db"
```

To export to SQL:
```bash
sqlite3 data/basvurular.db ".dump" > data/basvurular_dump.sql
```
