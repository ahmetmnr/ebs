"""
Proje Dosyası analyzer.
"""

from .base_analyzer import BaseAnalyzer


class ProjeAnalyzer(BaseAnalyzer):
    """Proje dosyası analiz sınıfı"""

    def get_document_type(self) -> str:
        return "Proje Dosyası"

    def get_prompt_template(self) -> str:
        return """Sen bir proje belgesi analiz uzmanısın. Proje bilgilerini çıkar.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN BİLGİLER ===

PROJE BİLGİSİ:
- tur: "TÜBİTAK Projesi|BAP|Horizon 2020|Sanayi|Diğer"
- baslik: Proje başlığı
- yil: Proje yılı (sayı)

=== ÇIKTI FORMATI ===
{{
  "tur": "TÜBİTAK Projesi",
  "baslik": "Yeşil Enerji Dönüşümü",
  "yil": 2022
}}

=== KURALLAR ===
1. **SADECE BELGEDE YAZANI ÇıKAR!**
2. Belgede yoksa → null
3. Birden fazla proje varsa → SADECE İLKİNİ
4. JSON geçerli olmalı

🚨 UYDURMA YAPMA! BİLMİYORSAN NULL YAZ! 🚨

SADECE JSON DÖNDÜR!
"""
