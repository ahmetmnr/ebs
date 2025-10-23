"""
Bakanlık personeli özgeçmiş prompt template
Bakanlık çalışanlarında kamu kurumu deneyimine odaklanır
"""
from typing import Dict
from app.prompts.ozgecmis_prompt import OzgecmisPromptTemplate


class OzgecmisBakanlikPromptTemplate(OzgecmisPromptTemplate):
    """Bakanlık personeli özgeçmişleri için özelleştirilmiş prompt"""

    def get_system_prompt(self) -> str:
        return """Sen Türk kamu idaresinde çalışan deneyimli bir İnsan Kaynakları uzmanısın.
Kamu personeli özgeçmişlerini analiz edip yapılandırılmış bilgi çıkarmada uzmansın.

GÖREVIN:
- Bakanlık personeli özgeçmişinden kişisel bilgiler, eğitim, kamu görevleri, dil ve sertifika bilgilerini çıkar
- ÖZELLİKLE Çevre, Şehircilik ve İklim Değişikliği Bakanlığı deneyimine odaklan
- Sadece belgede açıkça yazılı bilgileri kullan
- Tarih formatını YYYY-MM-DD olarak standartlaştır
- Eksik bilgiler için null kullan
- Türkçe karakterleri koru

ÖNEMLİ KURALLAR:
1. Tahmin yapma, sadece belgede gördüğün bilgileri yaz
2. Kamu kurumu isimlerini tam ve resmi olarak yaz
3. Unvan ve pozisyonları aynen kopyala
4. Görev sürelerini dikkatli hesapla (7 yıl kontrolü için önemli)
5. Tarihleri gün/ay/yıl formatından YYYY-MM-DD formatına çevir
6. "Devam ediyor" veya benzeri ifadeleri "Devam Ediyor" olarak standartlaştır"""

    def get_user_prompt(self, text: str, schema: Dict) -> str:
        # truncate_text kaldırıldı
        formatted_schema = self.format_schema(schema)

        return f"""Aşağıdaki BAKANLIK PERSONELİ ÖZGEÇMİŞİ belgesinden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== BAKANLIK PERSONELİ ÖZGEÇMİŞİ METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Kişisel bilgileri dikkatli çıkar (ad, soyad, TC, doğum tarihi, iletişim)
2. Eğitim geçmişini kronolojik sırala (en yüksek eğitim en üstte)
3. **ÇOK ÖNEMLİ - BAKANLIK DENEYİMİ KRİTERLERİ**:
   - **Yeşil Dönüşüm Sorumlusu (Eski Bakanlık)**: Çevre Bakanlığı'nda TOPLAM EN AZ 7 YIL hizmet gerekli
   - **Yeşil Dönüşüm Başsorumlusu (Eski Bakanlık)**: Çevre Bakanlığı'nda TOPLAM EN AZ 10 YIL hizmet gerekli
   - Sadece aşağıdaki bakanlıklardaki hizmetler sayılır:
     * Çevre, Şehircilik ve İklim Değişikliği Bakanlığı (güncel ad)
     * Çevre ve Şehircilik Bakanlığı (eski ad)
     * Çevre ve Orman Bakanlığı (daha eski ad)
     * Çevre Bakanlığı (en eski ad)
   - Bakanlık içinde ve dışında görev ayrımı MUTLAKA yapılmalı
   - Başlangıç tarihi: YYYY-MM-DD veya YYYY-MM formatında olmalı
   - Bitiş tarihi: YYYY-MM-DD, YYYY-MM veya "Devam Ediyor" formatında olmalı
   - Gün hesabı: (Bitiş Tarihi - Başlangıç Tarihi) + 1 gün
   - Devam eden görevler için: Bugünün tarihini bitiş tarihi olarak kullan
4. Kamu görevlerini kronolojik sırala ve ÖZELLİKLE şunlara dikkat et:
   - Çevre, Şehircilik ve İklim Değişikliği Bakanlığı görevleri (içinde/dışında)
   - Eski adı: Çevre ve Şehircilik Bakanlığı görevleri (içinde/dışında)
   - Çevre ve Orman Bakanlığı görevleri (içinde/dışında - daha eski adı)
   - Görev başlangıç ve bitiş tarihlerini kesin olarak belirle
   - Toplam hizmet süresini hesapla (7/10 yıl kriteri için)
5. Her görev için:
   - Kurum adını tam ve resmi olarak yaz
   - Unvan ve pozisyonu aynen kopyala
   - Görev tanımını özetle
   - Çevre ile ilgili olup olmadığını belirt (cevre_ile_ilgili: true/false)
5. Proje ve çalışmaları detaylı çıkar:
   - Yönetmelik hazırlama çalışmaları
   - Mevzuat hazırlama/revizyon çalışmaları
   - Ulusal veya uluslararası projeler
   - Çevre denetim ve izleme faaliyetleri
   - Eğitim ve koordinasyon çalışmaları
6. Yabancı dil seviyelerini belirt (Başlangıç, Orta, İleri, Ana Dili)
7. Sertifikaları detaylı çıkar (sertifika adı, veren kurum, tarih)

=== BAKANLIK DENEYİMİNİ BULMA İPUÇLARI ===
Belgede şu ifadelere özellikle dikkat et:
- "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı"
- "Çevre ve Şehircilik Bakanlığı"
- "Çevre ve Orman Bakanlığı"
- "ÇŞİB", "ÇŞBB", "ÇOBB" (kısaltmalar)
- "Müfettiş", "Denetçi", "Uzman", "Şef" gibi unvanlar
- "Genel Müdürlük", "Daire Başkanlığı" gibi birimler
- "Atama", "Görevlendirme" ifadeleri

=== SEKTÖR TANIMLAMA KURALLARI ===
Kamu görevlerinde sektör tanımlaması:
- Enerji: Enerji ile ilgili düzenleme, denetim, izin faaliyetleri
- Metal: Metal sanayi denetimi, çevre izinleri
- Mineral: Maden, çimento sektörü denetimi
- Kimya: Kimyasal tesisler denetimi
- Atık: Atık yönetimi, bertaraf tesisleri denetimi
- Diğer: Genel kamu hizmetleri

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver, başka açıklama ekleme:"""
