"""
Tum analiz sonuclarini temizle
"""
import sys
import io

# Windows encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from models.database import db

# Analiz sonuclarini sil
db.execute('DELETE FROM analiz_sonuclari')
db.execute('DELETE FROM belge_analiz_log')
db.execute('DELETE FROM chunk_sonuclari')
db.execute('DELETE FROM proje_yayinlar')

# Basvurulari sifirla
db.execute('UPDATE basvurular SET islendiMi=0, basvuruDurum="Bekliyor"')
db.execute('UPDATE belgeler SET analiz_edildi=0')

print('[OK] Tum analiz sonuclari temizlendi!')
print('[OK] Basvurular sifirlandi')
print('[OK] Belgeler sifirlandi')
print('\nSimdi sunu calistir: python main.py --analyze --limit 1')
