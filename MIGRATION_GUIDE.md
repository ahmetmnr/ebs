# Migration Rehberi - Eski Şemadan Yeni Şemaya Geçiş

## 📌 Özet

Bu dokümantasyon, mevcut projenizi **rapordaki yeni veritabanı şemasına** geçirmek için adım adım rehberdir.

## 🎯 Neler Değişti?

### Eski Yapı (Mevcut)
```
data/basvurular.db
├── basvurular (takip_no, hizmet_id, json_data, cekme_tarihi)
└── analiz_sonuclari (takip_no, cv_analiz, sgk_analiz, ...)
```

### Yeni Yapı (Rapor)
```
data/basvurular.db
├── basvurular (normalize edilmiş, 15 kolon)
├── belgeler (ayrı tablo, json_data'dan çıkarıldı)
├── analiz_sonuclari (detaylı kolonlar, 40+ kolon)
├── proje_yayinlar (1-N ilişki)
├── belge_analiz_log (performans takibi)
├── chunk_sonuclari (LLM chunk tracking)
├── sistem_config (runtime config)
├── belge_tipi_kurallar (otomatik tahmin)
└── zorunlu_belgeler (validation matrix)
```

## 🔧 Yeni Özellikler

1. **Normalize Edilmiş Veritabanı**
   - JSON'dan alanlar ayrı kolonlara taşındı
   - Foreign key ilişkileri eklendi
   - Indexler optimize edildi

2. **Belge Takibi**
   - Her belge ayrı satır
   - Analiz durumu tracking
   - Performans metrikleri

3. **Otomatik Belge Tipi Tahmini**
   - Regex-based pattern matching
   - Öncelik sistemi
   - Özelleştirilebilir kurallar

4. **Zorunlu Belge Kontrolü**
   - Hizmet tipi bazlı matrix
   - Otomatik eksik belge tespiti
   - Validation API

5. **Chunk Management**
   - Büyük belgeleri chunk'lara böl
   - Her chunk ayrı track edilir
   - Retry mekanizması

6. **View'lar**
   - Hazır raporlama view'ları
   - Performans metrikleri
   - Sektör dağılımı

## 📋 Migration Adımları

### Adım 1: Mevcut Veriyi Kontrol Et

```bash
# Mevcut şemayı incele
python scripts/check_db_schema.py
```

Çıktı:
```
[OK] Veritabani bulundu: data\basvurular.db
[INFO] Boyut: 9.77 GB

TABLOLAR:
[TABLO] basvurular (2,088 satir)
[TABLO] analiz_sonuclari (6 satir)
```

### Adım 2: Yedek Al

```bash
# Otomatik yedekleme (migration script içinde)
# Manuel yedek:
cp data/basvurular.db data/basvurular_backup_$(date +%Y%m%d).db
```

### Adım 3: Migration Çalıştır

```bash
# Interaktif migration
python scripts/migrate_database.py
```

Script şunları yapar:
1. ✅ Otomatik yedek alır
2. ✅ Yeni DB oluşturur (`data/basvurular_v2.db`)
3. ✅ `basvurular` tablosunu migrate eder
4. ✅ `belgeler` tablosunu oluşturur (JSON'dan)
5. ✅ Belge tiplerini tahmin eder
6. ✅ Doğrulama yapar

Çıktı:
```
================================================================================
MIGRATION DOGRULAMA
================================================================================

Basvuru sayisi:
  Eski DB: 2088
  Yeni DB: 2088
  Durum: [OK]

Belgeler tablosu: 15,234 kayit

[BASARILI] Migration tamamlandi!
```

### Adım 4: Yeni DB'yi Test Et

```bash
# Yeni DB'yi kontrol et
SKIP_CONFIG_VALIDATION=true python -c "
from models.database import DatabaseManager
from pathlib import Path

db = DatabaseManager(Path('data/basvurular_v2.db'))
print(f'Basvurular: {db.get_row_count(\"basvurular\")}')
print(f'Belgeler: {db.get_row_count(\"belgeler\")}')
print(f'Analiz Sonuclari: {db.get_row_count(\"analiz_sonuclari\")}')
"
```

### Adım 5: Eski DB'yi Değiştir (Opsiyonel)

```bash
# Sadece migration başarılıysa!

# Eski DB'yi yedekle
mv data/basvurular.db data/basvurular_old.db

# Yeni DB'yi aktif et
mv data/basvurular_v2.db data/basvurular.db
```

## 🔄 Geri Dönüş (Rollback)

Eğer bir sorun olursa:

```bash
# Yeni DB'yi sil
rm data/basvurular_v2.db

# Yedekten geri yükle
cp data/basvurular_backup_YYYYMMDD_HHMMSS.db data/basvurular.db
```

## 🧪 Test Senaryoları

### Test 1: Veri Bütünlüğü

```python
from models import Basvuru, Belge

# Başvuru sayısı eşit mi?
old_count = 2088  # Eski DB'den
new_count = Basvuru.count()
assert old_count == new_count, f"Başvuru sayısı uyuşmuyor: {old_count} != {new_count}"

# Her başvurunun belgeleri var mı?
for basvuru in Basvuru.get_all(limit=10):
    belgeler = Belge.get_by_basvuru_id(basvuru['basvuruId'])
    print(f"Başvuru {basvuru['takipNo']}: {len(belgeler)} belge")
```

### Test 2: Belge Tipi Tahmini

```python
from models import Belge

# Tahmin edilen belge tipleri
belgeler = Belge.get_all(limit=20)
for belge in belgeler:
    if belge['belgeTipi']:
        print(f"✅ {belge['belgeAdi']}: {belge['belgeTipi']}")
    elif belge['belgeTipi_tahmini']:
        print(f"🔍 {belge['belgeAdi']}: {belge['belgeTipi_tahmini']} (tahmin)")
    else:
        print(f"❌ {belge['belgeAdi']}: Bilinmiyor")
```

### Test 3: View'lar

```python
from models.database import db

# Başvuru özeti
ozet = db.fetchall("SELECT * FROM v_basvuru_ozet LIMIT 5")
for row in ozet:
    print(f"{row['takipNo']}: {row['toplam_belge_sayisi']} belge, "
          f"{row['analiz_edilen_belge_sayisi']} analiz edildi")

# Sektör dağılımı
sektor = db.fetchall("SELECT * FROM v_sektor_dagilim LIMIT 5")
for row in sektor:
    print(f"Başvuru {row['basvuruId']}: "
          f"Enerji={row['enerji_sayisi']}, Metal={row['metal_sayisi']}")
```

## 🎯 Yeni Model Kullanımı

### Eski Kod (SQL)

```python
import sqlite3

conn = sqlite3.connect('data/basvurular.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM basvurular WHERE takip_no = ?", (takip_no,))
row = cursor.fetchone()
conn.close()
```

### Yeni Kod (Model)

```python
from models import Basvuru

basvuru = Basvuru.get_by_takip_no(takip_no)
if basvuru:
    print(f"Başvuru ID: {basvuru['basvuruId']}")
    print(f"Ad Soyad: {basvuru['basvuruYapanAd']} {basvuru['basvuruYapanSoyad']}")

    # Belgeleri getir
    belgeler = basvuru.get_belgeler(basvuru['basvuruId'])
    print(f"Belge sayısı: {len(belgeler)}")
```

## 📊 Performans Karşılaştırması

| Özellik | Eski Şema | Yeni Şema |
|---------|-----------|-----------|
| Tablo sayısı | 2 | 9 |
| Index sayısı | 2 | 15+ |
| Normalize edilmiş | ❌ | ✅ |
| Foreign keys | ❌ | ✅ |
| View'lar | ❌ | 3 |
| Trigger'lar | ❌ | 3 |
| Belge tracking | ❌ | ✅ |
| Performans metrikleri | ❌ | ✅ |

## 🚨 Dikkat Edilmesi Gerekenler

1. **Disk Alanı**: Yeni DB eski DB ile aynı boyutta olacak (~10 GB)
2. **Migration Süresi**: 2,088 başvuru için ~5-10 dakika
3. **Bellek Kullanımı**: Migration sırasında ~500 MB RAM
4. **Eski Kod Uyumluluğu**: Eski `app/` klasörü kodu etkilenmez
5. **Yedekleme**: Mutlaka yedek alın!

## ✅ Checklist

- [ ] Mevcut DB'yi kontrol ettim (`check_db_schema.py`)
- [ ] Yedek aldım (otomatik veya manuel)
- [ ] Migration çalıştırdım (`migrate_database.py`)
- [ ] Doğrulama testlerini yaptım
- [ ] Yeni model sınıflarını test ettim
- [ ] View'ları kontrol ettim
- [ ] Eski kod hala çalışıyor
- [ ] Yeni kod ile entegrasyon tamam

## 🆘 Sorun Giderme

### Sorun: Migration hatası

```
[HATA] JSON parse error: ...
```

**Çözüm**: `check_db_schema.py` ile JSON formatını kontrol edin.

### Sorun: Belge tipi tahmin edilemiyor

```
❌ belge.pdf: Bilinmiyor
```

**Çözüm**: `belge_tipi_kurallar` tablosuna yeni kural ekleyin:

```python
from models.database import db

db.execute("""
    INSERT INTO belge_tipi_kurallar (dosya_adi_pattern, tahmin_edilen_tip, oncelik)
    VALUES ('(?i).*yeni_pattern.*', 'Yeni Belge Tipi', 8)
""")
```

### Sorun: Foreign key hatası

```
FOREIGN KEY constraint failed
```

**Çözüm**: `PRAGMA foreign_keys = ON` ayarlandığından emin olun.

## 📞 Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin: `logs/`
2. DEBUG modunu açın: `.env` → `DEBUG=true`
3. Detaylı log için: `LOG_LEVEL=DEBUG`

## 📚 İlgili Dökümanlar

- [database/schema.sql](database/schema.sql) - Tam SQL şeması
- [models/database.py](models/database.py) - DB yönetim sınıfı
- [config/settings.py](config/settings.py) - Konfigürasyon
- [README.md](README.md) - Ana dokümantasyon
