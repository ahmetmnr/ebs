"""Veritabanını temizle"""
import sqlite3

conn = sqlite3.connect('data/basvurular.db')
cursor = conn.cursor()

print('Veritabani temizleniyor...')
print('='*60)

# 1. chunk_sonuclari
cursor.execute('SELECT COUNT(*) FROM chunk_sonuclari')
count = cursor.fetchone()[0]
cursor.execute('DELETE FROM chunk_sonuclari')
print(f'[OK] {count} chunk sonucu silindi')

# 2. belge_analiz_log
cursor.execute('SELECT COUNT(*) FROM belge_analiz_log')
count = cursor.fetchone()[0]
cursor.execute('DELETE FROM belge_analiz_log')
print(f'[OK] {count} belge analiz logu silindi')

# 3. analiz_sonuclari
cursor.execute('SELECT COUNT(*) FROM analiz_sonuclari')
count = cursor.fetchone()[0]
cursor.execute('DELETE FROM analiz_sonuclari')
print(f'[OK] {count} analiz sonucu silindi')

# 4. proje_yayinlar
cursor.execute('SELECT COUNT(*) FROM proje_yayinlar')
count = cursor.fetchone()[0]
cursor.execute('DELETE FROM proje_yayinlar')
print(f'[OK] {count} proje/yayin kaydi silindi')

# 5. basvurular reset
cursor.execute('SELECT COUNT(*) FROM basvurular WHERE islendiMi = 1')
count = cursor.fetchone()[0]
cursor.execute('UPDATE basvurular SET islendiMi = 0, basvuruDurum = "Yeni", islenme_baslangic = NULL, islenme_bitis = NULL, islenme_suresi_sn = NULL, hata_mesaji = NULL')
print(f'[OK] {count} basvuru islenmemis olarak isaretlendi')

conn.commit()
conn.close()

cursor.execute('SELECT COUNT(*) FROM basvurular')
total = cursor.fetchone()[0]

print('='*60)
print('Veritabani basariyla temizlendi!')
print(f'Toplam {total} basvuru yeniden analiz edilmeye hazir.')
