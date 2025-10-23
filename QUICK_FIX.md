# Hızlı Çözüm - Migration Tamamlanana Kadar

## Sorun

Mevcut veritabanınız eski şemayı kullanıyor. Yeni kod yeni şema bekliyor.

## Seçenek 1: Migration Tamamlanmasını Bekle (ÖNERİLEN)

Migration şu an çalışıyor. Tamamlandığında:

```bash
# 1. Kontrol et
python scripts/check_db_schema.py

# 2. Yeni DB'yi görüntüle
ls -lh data/*.db

# 3. Yeni DB'yi aktif et (migration başarılıysa)
mv data/basvurular.db data/basvurular_old.db
mv data/basvurular_v2.db data/basvurular.db

# 4. Test et
python main.py --analyze --limit 5
```

## Seçenek 2: Hızlı Test İçin Yeni Boş DB Oluştur

Migration beklemek istemiyorsanız:

```bash
# 1. Eski DB'yi yedekle
mv data/basvurular.db data/basvurular_old_backup.db

# 2. Yeni boş DB oluştur
python scripts/init_database.py --force

# 3. Test et (boş olacak)
python main.py --analyze --limit 5

# 4. Eski DB'yi geri yükle
mv data/basvurular_old_backup.db data/basvurular.db
```

## Seçenek 3: Migration'ı Manuel Kontrol Et

```bash
# Migration durumunu kontrol et
ps aux | grep migrate_database.py

# Migration loglarını gör
tail -f logs/database.log
```

## Migration Süresi

- **2,088 başvuru** için beklenen süre: **5-10 dakika**
- **9.77 GB** veritabanı için: **10-15 dakika**

## Migration Sonrası

Migration tamamlandığında şu dosyalar oluşacak:

- `data/basvurular_v2.db` - Yeni şema ile DB
- `data/basvurular_backup_YYYYMMDD_HHMMSS.db` - Otomatik yedek
- `data/basvurular.db` - Eski DB (değişmedi)

**Yeni DB'yi aktif etmek için:**

```bash
# Güvenlik için ekstra yedek
cp data/basvurular.db data/basvurular_SAFE_BACKUP.db

# Eski DB'yi kenara koy
mv data/basvurular.db data/basvurular_old.db

# Yeni DB'yi aktif et
mv data/basvurular_v2.db data/basvurular.db

# Test et
python main.py --analyze --limit 2
```

## Sorun Devam Ederse

Migration başarısız olursa:

```bash
# Hataları gör
cat logs/error.log

# Manuel migration dene (Python interactive)
python
>>> from scripts.migrate_database import *
>>> main()
```
