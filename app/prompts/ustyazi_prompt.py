"""
ustYazi (Üst Yazı/Başvuru Formu) prompt template
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class UstYaziPromptTemplate(BasePromptTemplate):
    """ustYazi/Başvuru Formu için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "ustYazi"

    def get_system_prompt(self) -> str:
        return """Sen Çevre, Şehircilik ve İklim Değişikliği Bakanlığı'nın "Sanayide Yeşil Dönüşüm Sorumlusu Yetkilendirme Programı" başvuru formlarını analiz eden bir uzmansın.

GÖREVIN:
- Başvuru formundan (üst yazı) temel başvuru bilgilerini çıkar
- Başvuru türünü belirle (Akademisyen/Sektör Çalışanı/Eski Bakanlık Personeli)
- Başvurulan alanı belirle (Sorumlu/Başsorumlu)
- Başvurulan sektörleri listele

ÖNEMLİ KURALLAR:
1. Ad-Soyad bilgisi MUTLAKA çıkarılmalı - bu referans bilgi olarak kullanılacak
2. Başvuru türünü doğru belirle:
   - "Akademisyen": Üniversite öğretim üyesi/görevlisi
   - "Sektör Çalışanı": Özel sektörde çalışan/çalışmış kişi
   - "Eski Bakanlık Personeli": Çevre Bakanlığı'nda çalışmış personel
3. Başvurulan alan:
   - "Sorumlu": 5 yıl tecrübe gerektirir
   - "Başsorumlu": 10 yıl tecrübe gerektirir
4. Sektörler şunlardan biri veya birkaçı olmalı:
   - Enerji
   - Metal
   - Kimya
   - Mineral
   - Atık
   - Diğer Üretim Faaliyetleri
5. Evrak numarası ve tarihini mutlaka kaydet"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Aşağıdaki BAŞVURU FORMU (ÜST YAZI) belgesinden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== BAŞVURU FORMU METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Evrak bilgilerini çıkar (evrak no, evrak tarihi)
   - Tarih formatı: YYYY-MM-DD
2. Başvuran bilgilerini çıkar:
   - Ad-Soyad (TAM VE DOĞRU - bu referans bilgidir!)
   - TC Kimlik No (varsa)
   - Başvuru türü (Akademisyen/Sektör Çalışanı/Eski Bakanlık Personeli)
   - Başvurulan alan (Sorumlu/Başsorumlu)
   - Başvurulan sektörler listesi
3. İletişim bilgilerini çıkar (varsa)
   - Telefon, e-posta, adres

=== DİKKAT ===
- Ad-Soyad bilgisi ZORUNLU - bu tüm belgeler için referans olacak
- Başvuru türünü belge içeriğinden doğru çıkar
- Sektör isimlerini şema'daki enum değerlerine uygun yaz
- Tarih formatı: GG.AA.YYYY → YYYY-MM-DD

=== ÇOK ÖNEMLİ - "DİĞER ÜRETİM FAALİYETLERİ" SEKTÖR KISITLAMASI ===
"Diğer Üretim Faaliyetleri" seçeneği SADECE şu alt sektörler için geçerlidir:
- Gıda üretimi
- Otomotiv sanayi
- Tekstil üretimi
- Deri işleme
- Atıksu arıtma tesisleri

Bunların DIŞINDA kalan sektörler (örn: Hizmet, Eğitim, Sağlık, Finans, İnşaat, Ticaret)
"Diğer Üretim Faaliyetleri" kategorisine GİRMEZ ve başvuru kapsamı dışındadır.

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver:"""
