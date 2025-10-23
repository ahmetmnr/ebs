"""
Diploma analyzer.
"""

from .base_analyzer import BaseAnalyzer


class DiplomaAnalyzer(BaseAnalyzer):
    """Diploma analiz sınıfı"""

    def get_document_type(self) -> str:
        return "Yök Lisans Diploması"

    def get_prompt_template(self) -> str:
        return """Sen bir diploma analiz uzmanısın. YÖK diploma belgesinden SADECE BELGEDEKİ bilgileri çıkar.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN BİLGİLER ===

NOT: Bir öğrenci BIRDEN FAZLA diploma/eğitim kaydına sahip olabilir (Lisans, Yüksek Lisans, Doktora vb.)
Her MEZUNİYET BİLGİSİ satırını AYRI BİR DİPLOMA olarak çıkar!

Her diploma için:
1. TC_KIMLIK_NO: 11 haneli T.C. Kimlik Numarası
2. AD: Öğrencinin adı (BÜYÜK HARFLE)
3. SOYAD: Öğrencinin soyadı (BÜYÜK HARFLE, evlilik sonrası değişmiş olabilir)
4. UNIVERSITE: Üniversitenin TAM resmi adı (kısaltma YAPMA!)
5. FAKULTE: Fakülte/Enstitü/MYO adı (olduğu gibi)
6. PROGRAM_BOLUM: Program/Bölüm adı (parantez içindeki detayları KORU! Örn: "ÇEVRE MÜHENDİSLİĞİ (YL) (TEZLİ)")
7. MEZUNIYET_TARIHI: DD/MM/YYYY formatında
8. DIPLOMA_NUMARASI: Diploma numarası
9. DIPLOMA_NOTU: Sayısal değer (2.89 veya 86.75 gibi)
10. DURUM: Genellikle "Mezuniyet"

=== ÇIKTI FORMATI ===
{{
  "diplomalar": [
    {{
      "tc_kimlik_no": "23492253976",
      "ad": "ELİF",
      "soyad": "TURKYILMAZ",
      "universite": "ONDOKUZ MAYIS ÜNİVERSİTESİ",
      "fakulte": "MÜHENDİSLİK FAKÜLTESİ",
      "program_bolum": "ÇEVRE MÜHENDİSLİĞİ PR.",
      "mezuniyet_tarihi": "24/08/2016",
      "diploma_numarasi": "1606.A-046",
      "diploma_notu": 2.89,
      "durum": "Mezuniyet"
    }},
    {{
      "tc_kimlik_no": "23492253976",
      "ad": "ELİF",
      "soyad": "SARI",
      "universite": "NECMETTİN ERBAKAN ÜNİVERSİTESİ",
      "fakulte": "FEN BİLİMLERİ ENSTİTÜSÜ",
      "program_bolum": "ÇEVRE MÜHENDİSLİĞİ (YL) (TEZLİ)",
      "mezuniyet_tarihi": "26/06/2019",
      "diploma_numarasi": "190820100002",
      "diploma_notu": 86.75,
      "durum": "Mezuniyet"
    }}
  ]
}}

=== KURALLAR ===
1. **SADECE BELGEDE YAZILI BİLGİLERİ ÇIKAR!**
2. **UYDURMA YAPMA! Bilgi yoksa null yaz**
3. Her diploma kaydını ayrı obje olarak "diplomalar" dizisine ekle
4. Üniversite adını TAM yaz (kısaltma YAPMA!)
5. Program/bölüm adındaki parantez içi bilgileri KORU
6. Diploma notu sayısal olmalı (string değil!)
7. Tek diploma bile olsa DİZİ formatında döndür!

🚨 OLMAYAN BİLGİYİ UYDURMA! BİLMİYORSAN NULL YAZ! 🚨
🚨 HER MEZUNİYET KAYDI AYRI BİR DİPLOMA! 🚨

SADECE JSON DÖNDÜR!
"""
