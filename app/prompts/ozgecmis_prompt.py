"""
Özgeçmiş prompt template
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class OzgecmisPromptTemplate(BasePromptTemplate):
    """Özgeçmiş belgesi için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "özgeçmiş"

    def get_system_prompt(self) -> str:
        return """Sen Çevre, Şehircilik ve İklim Değişikliği Bakanlığı'nın "Sanayide Yeşil Dönüşüm Sorumlusu" başvurularını değerlendiren bir uzmansın.
Özgeçmiş belgelerini analiz edip yapılandırılmış bilgi çıkarmada uzmansın.

GÖREVIN:
- Özgeçmiş belgesinden kişisel bilgiler, eğitim, iş deneyimi, akademik yayınlar, projeler, dil ve sertifika bilgilerini çıkar
- Sadece belgede açıkça yazılı bilgileri kullan
- Tarih formatını YYYY-MM-DD olarak standartlaştır
- İş deneyimlerini sektörlere göre sınıflandır
- Akademik yayınları APA 7 formatında düzenle
- Eksik bilgiler için null kullan
- Türkçe karakterleri koru

ÖNEMLİ KURALLAR:
1. Tahmin yapma, sadece belgede gördüğün bilgileri yaz
2. Ad-Soyad bilgisi ZORUNLU - bu referans bilgidir!
3. Şirket isimleri ve pozisyonları aynen kopyala
4. Eğitim seviyelerini: "Lisans", "Yüksek Lisans", "Doktora", "Önlisans" olarak standartlaştır
5. Tarihleri gün/ay/yıl formatından YYYY-MM-DD formatına çevir
6. "Devam ediyor" veya benzeri ifadeleri "Devam Ediyor" olarak standartlaştır
7. Her iş deneyiminin sektörünü belirle: Enerji, Metal, Mineral, Kimya, Atık, Diğer Üretim Faaliyetleri
8. Akademik yayınları APA 7 formatında tam kaynak olarak çıkar"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Aşağıdaki ÖZGEÇMİŞ belgesinden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== ÖZGEÇMİŞ METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Kişisel bilgileri dikkatli çıkar (ad, soyad, TC, doğum tarihi, iletişim)
   - **Ad-Soyad ZORUNLU ve DOĞRU olmalı (referans bilgidir!)**

2. Eğitim geçmişini kronolojik sırala (en yüksek eğitim en üstte)
   - Üniversite adını tam ve doğru yaz
   - Bölüm/program bilgilerini eksiksiz al
   - Mezuniyet yıllarını kaydet

3. İş deneyimlerini kronolojik sırala (en son iş en üstte)
   - Her iş deneyimi için:
     * Şirket adı (tam ve doğru)
     * Pozisyon/ünvan
     * Başlangıç ve bitiş tarihleri (YYYY-MM-DD formatında)
     * **Sektörü belirle**: Enerji, Metal, Mineral, Kimya, Atık veya Diğer Üretim Faaliyetleri
     * Çevre ile ilgili olup olmadığını belirt (cevre_ile_ilgili: true/false)
     * Görev tanımını özetle

4. Yabancı dil seviyelerini belirt (Başlangıç, Orta, İleri, Ana Dili)

5. Sertifikaları detaylı çıkar (sertifika adı, veren kurum, tarih)

6. **ÇOK ÖNEMLİ - Projeler ve Yayınlar (Özellikle Akademisyen başvurular için)**:
   - Tüm bilimsel makaleleri, bildirileri, kitap bölümlerini çıkar
   - Her yayın için:
     * Tip: Makale, Bildiri, Kitap Bölümü, Proje, Teknik Rapor
     * Başlık
     * Açıklama/özet
     * Tarih
     * Kurum/dergi
     * **APA 7 formatında tam kaynak** (apa7_format alanına)
     * Hangi sektöre uygun: Enerji, Metal, Kimya, Mineral, Atık, Diğer
     * Çevre alanıyla ilgili mi? (cevre_ile_ilgili: true/false)

7. **Akademik Yayınlar** (Akademisyen için özel):
   - Tüm makaleleri "makaleler" dizisine APA 7 formatında ekle
   - Tüm bildirileri "bildiriler" dizisine APA 7 formatında ekle
   - Kitap/kitap bölümlerini "kitaplar" dizisine APA 7 formatında ekle
   - Toplam sayıyı hesapla

=== SEKTÖR TANIMLAMA KURALLARI ===
- **Enerji**: Elektrik üretimi, yenilenebilir enerji, termik santraller, güneş/rüzgar enerjisi, enerji verimliliği, enerji tesisleri
- **Metal**: Demir-çelik, metalurji, dökümhaneler, metal işleme, haddehaneler, metal endüstrisi
- **Mineral**: Çimento, seramik, cam, madencilik, kireç üretimi, mineral işleme
- **Kimya**: Kimyasal üretim, petrokimya, ilaç, boya, kimyasal işleme, kimya endüstrisi
- **Atık**: Atık yönetimi, geri dönüşüm, bertaraf tesisleri, tehlikeli atık, katı atık
- **Diğer Üretim Faaliyetleri**: Yukarıdakilere girmeyen sanayi tesisleri, üretim faaliyetleri

=== APA 7 FORMAT ÖRNEKLERİ ===
**Makale**:
Yazar, A. A., & Yazar, B. B. (Yıl). Makale başlığı. Dergi Adı, Cilt(Sayı), sayfa-sayfa. https://doi.org/xxx

**Bildiri**:
Yazar, A. A. (Yıl). Bildiri başlığı. Konferans Adı, Yer.

**Kitap Bölümü**:
Yazar, A. A. (Yıl). Bölüm başlığı. In Editör, E. (Ed.), Kitap Adı (ss. sayfa-sayfa). Yayınevi.

**Proje**:
Yazar, A. A. (Yıl). Proje başlığı. Kurum/Fon Kaynağı. Proje No: XXX.

=== ÖNEMLİ NOTLAR ===
- Ad-Soyad bilgisi referans olarak kullanılacak, MUTLAKA doğru çıkar
- Sektör bilgileri SGK belgesiyle karşılaştırılacak, tutarlı olmalı
- Eğitim bilgileri Diploma belgesiyle karşılaştırılacak
- Akademik yayınlar varsa tümünü APA 7 formatında çıkar
- İş deneyimlerinde sektör ve tarih bilgileri eksiksiz olmalı

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver, başka açıklama ekleme:"""
