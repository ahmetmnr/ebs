"""
SGK Dökümü prompt template
"""
from typing import Dict
from app.prompts.base_prompt import BasePromptTemplate


class SGKPromptTemplate(BasePromptTemplate):
    """SGK hizmet dökümü için özelleştirilmiş prompt"""

    def get_document_type(self) -> str:
        return "sgk"

    def get_system_prompt(self) -> str:
        return """Sen SGK hizmet dökümlerini analiz eden bir uzmansın.
Sadece belgede gördüğün bilgileri çıkar. Karşılaştırma yapma, tahmin etme.

GÖREVIN:
- Kişi bilgileri, çalışma geçmişi, toplam süreleri çıkar
- Her işyeri için sektör belirle
- Tarihleri YYYY-MM-DD formatına çevir
- Süreleri gün olarak hesapla"""

    def get_user_prompt(self, text: str, schema: Dict, ozgecmis_data: Dict = None) -> str:
        formatted_schema = self.format_schema(schema)

        # Özgeçmiş verisi varsa karşılaştırma talimatı ekle
        cv_instruction = ""
        if ozgecmis_data and ozgecmis_data.get("is_deneyimi"):
            cv_companies = [is_den.get("sirket_adi", "") for is_den in ozgecmis_data.get("is_deneyimi", [])]
            cv_instruction = f"""

=== ÖZGEÇMİŞ İLE KARŞILAŞTIRMA (CROSS-VALIDATION) ===
Özgeçmişte şu şirketler var: {", ".join(cv_companies)}

**CV-SGK CROSS-VALIDATION KURALLARI**:

1. **Şirket İsmi Eşleştirme**:
   - SGK'daki her işyerini özgeçmişteki şirketlerle eşleştir
   - Benzer isimleri kabul et (örn: "ABC A.Ş." = "ABC Limited Şirketi")
   - Kısaltmaları kabul et (örn: "TÜPRAŞ" = "Türkiye Petrol Rafinerileri A.Ş.")
   - %70'in üzerinde benzerlik varsa eşleşmiş say

2. **Tarih Uyumluluğu Kontrolü**:
   - İşe giriş tarihleri: ±30 gün tolerans kabul edilir
   - İşten çıkış tarihleri: ±30 gün tolerans kabul edilir
   - 3 aydan fazla fark varsa "uyumsuz_kayitlar"a ekle
   - Özgeçmişte "Devam Ediyor" ve SGK'da çıkış tarihi varsa uyumsuzluk olarak kaydet

3. **Pozisyon/Unvan Kontrolü**:
   - Özgeçmişteki pozisyon ile SGK'daki meslek alanını karşılaştır
   - Büyük uyumsuzluklar varsa (örn: Müh endis vs İşçi) uyarı ver

4. **Eksik Kayıt Tespiti**:
   - Özgeçmişte olup SGK'da olmayan şirketleri "eksik_kayitlar"a ekle
   - SGK'da olup özgeçmişte olmayan şirketleri "fazla_kayitlar"a ekle
   - Kısa süreli işler (<90 gün) için tolerans göster

5. **Sektör Uyumluluğu**:
   - Aynı şirket için özgeçmiş ve SGK'da farklı sektör varsa uyarı ver
   - Özgeçmişteki sektör bilgisi önceliklidir (daha detaylı olabilir)

6. **Genel Uyum Değerlendirmesi** ("ozgecmis_ile_uyumlu"):
   - Tüm şirketler eşleşiyor ve tarihler uyumlu: true
   - 1-2 küçük uyumsuzluk (tarih farklılıkları): true (ama uyarıyla)
   - Eksik şirket var veya büyük tarih farkları: false
   - Şirket sayısı %50'den fazla farklı: false

7. **Çalışma Süresi Hesaplama Uyumu**:
   - Özgeçmişteki toplam süre ile SGK toplam süre karşılaştırılmalı
   - ±6 ay fark kabul edilir
   - Büyük farklar varsa açıklama ekle"""

        return f"""Aşağıdaki SGK HİZMET DÖKÜMÜ belgesinden bilgileri çıkar ve verilen JSON şemasına göre döndür.

=== SGK HİZMET DÖKÜMÜ METNİ ===
{text}

=== JSON ŞEMA ===
{formatted_schema}

=== TALİMATLAR ===
1. Kişi bilgilerini çıkar (ad/soyad, SGK sicil no)
   - **NOT**: TC Kimlik No SGK belgesinde olmayabilir, varsa al
   - Ad-Soyad bilgisi REFERANS - özgeçmiş ve diğer belgelerle karşılaştırılacak

2. Çalışma geçmişindeki **TÜM** işyerlerini listele
   Her işyeri için:
   - İşyeri adı (tam ve doğru - aynen kopyala)
   - İşe giriş tarihi (YYYY-MM-DD formatında)
   - İşten çıkış tarihi (YYYY-MM-DD veya null eğer devam ediyorsa)
   - Çalışma süresi (gün sayısı - belgeden al veya hesapla)
   - Meslek/pozisyon
   - SGK kodu (varsa)
   - **Sektör**: İşyeri adından ve meslek bilgisinden sektörü belirle
   - **Çevre ile ilgili mi**: İşyeri ve meslek bilgisine göre belirle

3. Toplam çalışma süresini hesapla (yıl, ay, gün, toplam_gun)
   - Tüm işyerlerindeki toplam çalışma gününü topla

4. Sektör dağılımını hazırla
   - Her sektör için toplam çalışma süresini (gün ve yıl olarak) hesapla
   - Sadece çalışılan sektörleri listele

{cv_instruction}

=== SEKTÖR TANIMLAMA KURALLARI ===
İşyeri adından ve meslek bilgisinden sektörü belirle:

- **Enerji**: Elektrik üretimi, termik santral, hidroelektrik, yenilenebilir enerji, güneş enerjisi, rüzgar enerjisi, doğalgaz, enerji dağıtım, EÜAŞ, TEDAŞ, EPDK
- **Metal**: Demir-çelik, metalurji, dökümhane, hadde, galvaniz, metal işleme, ERDEMİR, KARDEMİR, İSDEMİR, metal sanayi
- **Mineral**: Çimento, seramik, cam, madencilik, mermer, kireç, alçı, kum, çakıl, taş ocağı, ÇIMSA, NUHÇIMENTO
- **Kimya**: Kimyasal üretim, petrokimya, ilaç, boya, gübre, plastik, deterjan, kozmetik, PETKIM, TÜPRAŞ
- **Atık**: Atık yönetimi, çöp toplama, geri dönüşüm, katı atık, tehlikeli atık, bertaraf, arıtma, İSBAK, belediye atık
- **Diğer Üretim Faaliyetleri**: Gıda, tekstil, otomotiv, makine, inşaat malzemesi, mobilya, kağıt, plastik ürünler, diğer sanayi tesisleri

=== DİKKAT ===
- Tarih formatı: GG.AA.YYYY → YYYY-MM-DD
- Devam eden işler için isten_cikis_tarihi: null
- Süreleri gün olarak kaydet (1 yıl = 365 gün)
- İşyeri isimlerini aynen kopyala, düzeltme yapma
- Her işyeri için sektör bilgisi ZORUNLU
- Sektör dağılımında sadece çalışılan sektörler olmalı

=== ÇIKTI ===
Yanıtını SADECE JSON formatında ver:"""

    def get_user_prompt_with_cv(self, text: str, schema: Dict, cv_data: Dict) -> str:
        """Özgeçmiş verisiyle birlikte prompt oluştur"""
        return self.get_user_prompt(text, schema, ozgecmis_data=cv_data)
