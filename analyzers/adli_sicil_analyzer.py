"""
Adli Sicil Kaydı analyzer.
"""

from .base_analyzer import BaseAnalyzer


class AdliSicilAnalyzer(BaseAnalyzer):
    """Adli sicil analiz sınıfı"""

    def get_document_type(self) -> str:
        return "Adli Sicil Kaydı"

    def get_prompt_template(self) -> str:
        return """Sen bir adli sicil belgesi analiz uzmanısın. Adli sicil durumunu tespit et.

=== BELGE İÇERİĞİ ===
{document_text}

=== ÇIKARILMASı GEREKEN BİLGİ ===

ADLİ SİCİL DURUMU:
- var_mi: Sabıka kaydı var mı? (true/false)
  * "Sabıka kaydı bulunmamaktadır" → false
  * "Sabıka kaydı yoktur" → false
  * Suç kaydı varsa → true
- kod: Belgede yazan kod (varsa)

=== ÇIKTI FORMATI ===
{{
  "var_mi": false,
  "kod": null
}}

=== KURALLAR ===
1. **SADECE BELGEDE YAZANI ÇıKAR!**
2. var_mi: true veya false (string değil!)
3. Belgede yoksa → null

🚨 UYDURMA YAPMA! 🚨

SADECE JSON DÖNDÜR!
"""
