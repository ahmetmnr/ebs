"""
CV/Özgeçmiş analyzer.
"""

from .base_analyzer import BaseAnalyzer


class CVAnalyzer(BaseAnalyzer):
    """CV analiz sınıfı"""

    def get_document_type(self) -> str:
        return "Özgeçmiş/CV"

    def get_prompt_template(self) -> str:
        return """Sen bir CV analiz uzmanısın. Aşağıdaki CV/Özgeçmiş belgesini analiz et ve SADECE BELGEDEKİ bilgileri JSON formatında çıkar.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN BİLGİLER ===

1. KİŞİSEL BİLGİ:
   - ad_soyad: Tam adı

2. EĞİTİM:
   - universite: En yüksek mezuniyet üniversitesi
   - bolum: Bölüm adı
   - mezuniyet_yili: Mezuniyet yılı (sayı)

3. İŞ DENEYİMİ:
   - toplam_is_deneyimi_yil: Toplam yıl
   - toplam_is_deneyimi_ay: Kalan ay (0-11)

4. SEKTÖR TECRÜBELERİ (SADECE BELGEDEKİ):
   - tecrube_enerji: Enerji sektörü yıl (belgede yoksa null)
   - tecrube_metal: Metal sektörü yıl (belgede yoksa null)
   - tecrube_kimya: Kimya sektörü yıl (belgede yoksa null)
   - tecrube_mineral: Mineral sektörü yıl (belgede yoksa null)
   - tecrube_atik: Atık sektörü yıl (belgede yoksa null)
   - tecrube_diger: Diğer sektör yıl (belgede yoksa null)

5. PROJELER (SADECE BAŞLIK, TÜR, YIL):
   - projeler: [
       {{
         "tur": "TÜBİTAK Projesi",
         "baslik": "Proje adı",
         "yil": 2022
       }}
     ]

=== ÇIKTI FORMATI ===
{{
  "ad_soyad": "YAVUZ DEMİRCİ",
  "universite": "İstanbul Teknik Üniversitesi",
  "bolum": "Çevre Mühendisliği",
  "mezuniyet_yili": 2010,
  "toplam_is_deneyimi_yil": 10,
  "toplam_is_deneyimi_ay": 6,
  "tecrube_enerji": 8,
  "tecrube_metal": 5,
  "tecrube_kimya": 6,
  "tecrube_mineral": 4,
  "tecrube_atik": 7,
  "tecrube_diger": 3,
  "projeler": [
    {{
      "tur": "TÜBİTAK Projesi",
      "baslik": "Yeşil Enerji Dönüşümü",
      "yil": 2022
    }}
  ]
}}

=== KRİTİK KURALLAR ===
1. **SADECE BELGEDE AÇIKÇA YAZILI BİLGİLERİ ÇIKAR!**
2. **SEKTÖR TECRÜBESİ BİLİNMİYORSA: null (0 DEĞIL!)**
   - CV'de "enerji sektöründe 8 yıl" yazmıyorsa → tecrube_enerji: null
   - ASLA TAHMİN ETME!
3. **İŞ DENEYİMİ SADECE TARİHLERDEN:**
   - 2015-2023 = 8 yıl (SADECE bu!)
   - Fazla ekleme!
4. **PROJELER SADECE BELGEDEKİLER:**
   - Başlık, tür, yıl varsa ekle
   - Yoksa boş array: []
5. Belgede yoksa → null
6. JSON geçerli olmalı

🚨 OLMAYAN BİLGİYİ UYDURMA! BİLMİYORSAN NULL YAZ! 🚨

SADECE JSON DÖNDÜR!
"""
