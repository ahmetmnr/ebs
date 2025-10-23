"""
Ana belge işleme pipeline'ı
"""
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from app.services.file_service import FileService
from app.services.ocr_service import OCRService
from app.services.ollama_service import OllamaService
from app.core.document_classifier import DocumentClassifier
from app.core.document_validator import DocumentValidator
from app.core.document_requirements import DocumentRequirementsChecker
from app.models.schemas import DOCUMENT_SCHEMAS, MASTER_SCHEMA

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Ana belge işleme sınıfı"""

    def __init__(self):
        self.file_service = FileService()
        self.ocr_service = OCRService()
        self.ollama_service = OllamaService()
        self.classifier = DocumentClassifier()
        self.validator = DocumentValidator()
        self.requirements_checker = DocumentRequirementsChecker()

    async def process_application(self, basvuru_data: Dict) -> Dict:
        """
        Başvuruyu işle

        Args:
            basvuru_data: get_basvuru_with_belgeler() çıktısı

        Returns:
            Master JSON
        """
        logger.info(f"▶️  Başvuru işleniyor: {basvuru_data['takip_no']}")

        # Başvuru bilgileri
        basvuru_info = {
            "basvuru_id": basvuru_data["basvuru_id"],
            "takip_no": basvuru_data["takip_no"],
            "basvuru_tarihi": basvuru_data["basvuru_tarihi"],
            "hizmet_adi": basvuru_data["hizmet_adi"]
        }

        # Başvuran bilgileri (API'den)
        basvuran_info = {
            "ad": basvuru_data.get("basvuru_yapan_ad"),
            "soyad": basvuru_data.get("basvuru_yapan_soyad"),
            "tc_kimlik_no": basvuru_data.get("basvuru_yapan_tc"),
            "dogum_tarihi": None,
            "telefon": None,
            "email": None
        }

        # Başvuru türünü tespit et (hizmet adından)
        basvuru_turu = self._detect_application_type(basvuru_info.get("hizmet_adi", ""))

        # Her belgeyi işle
        belgeler = basvuru_data["belgeler"]
        processed_documents = []

        for i, belge in enumerate(belgeler, 1):
            try:
                logger.info(f"📄 Belge {i}/{len(belgeler)}: {belge['belge_adi']}")

                # Başvuru ID'yi belgeye ekle (loglama için)
                belge["basvuru_id"] = basvuru_info["basvuru_id"]

                # Belgeyi işle (başvuru türü bilgisi ile)
                result = await self.process_document(belge, basvuru_turu)
                processed_documents.append(result)

            except Exception as e:
                logger.error(f"❌ Belge işleme hatası ({belge['belge_adi']}): {str(e)}")
                continue

        # Master JSON oluştur
        master_json = self.create_master_json(
            basvuru_info,
            basvuran_info,
            processed_documents,
            basvuru_turu  # Başvuru türü bilgisini de gönder
        )

        logger.info(f"✅ Başvuru tamamlandı: {basvuru_data['takip_no']}")
        return master_json

    async def process_document(self, belge: Dict, basvuru_turu: str = None) -> Dict:
        """
        Tek bir belgeyi işle

        Args:
            belge: Belge bilgileri (base64, ad, tip vs.)
            basvuru_turu: Başvuru türü (Akademisyen, Bakanlık, Sektör)

        Returns:
            İşlenmiş belge verisi
        """
        belge_adi = belge["belge_adi"]
        base64_data = belge["base64"]

        # 1. Base64 → Dosya
        file_path, _ = self.file_service.base64_to_file(
            base64_data,
            belge_adi
        )

        try:
            # 2. Belge tipini tespit et (OCR'dan önce!)
            doc_type = self.classifier.classify(
                filename=belge_adi,
                text=None,
                belge_tipi=belge.get("belge_tipi")
            )

            # ÖZEL DURUM: Fotoğraf belgelerini OCR'a sokma!
            if doc_type == "fotoğraf (vesikalık)":
                logger.info(f"📷 Fotoğraf belgesi - OCR atlanıyor")
                return {
                    "belge_id": belge["belge_id"],
                    "belge_adi": belge_adi,
                    "belge_tipi": doc_type,
                    "api_belge_tipi": belge.get("belge_tipi"),
                    "durum": "fotograf_belge",
                    "base64": base64_data,
                    "veri": {}
                }

            # 3. Metin çıkar (OCR)
            text = self.ocr_service.extract_text(file_path)
            logger.info(f"✅ Metin çıkarıldı: {len(text)} karakter")

            if not text or len(text) < 50:
                logger.warning(f"⚠️  Çok az metin: {belge_adi}")
                return {
                    "belge_id": belge["belge_id"],
                    "belge_adi": belge_adi,
                    "belge_tipi": doc_type,
                    "api_belge_tipi": belge.get("belge_tipi"),
                    "durum": "metin_yetersiz",
                    "base64": base64_data,  # Viewer için base64 içeriği
                    "veri": {}
                }

            # 4. LLM ile veri çıkar (başvuru türü ile)
            extracted_data = {}
            if doc_type in DOCUMENT_SCHEMAS:
                schema = DOCUMENT_SCHEMAS[doc_type]
                # basvuru_id'yi al (eğer varsa)
                basvuru_id = belge.get("basvuru_id")
                # NOT: extract_structured_data SYNC bir fonksiyon - await kullanma!
                extracted_data = self.ollama_service.extract_structured_data(
                    text=text,
                    document_type=doc_type,
                    schema=schema,
                    basvuru_turu=basvuru_turu,  # Başvuru türü bilgisi
                    basvuru_id=basvuru_id  # Loglama için
                )
                logger.info(f"✅ Veri çıkarıldı: {doc_type}")
            else:
                logger.warning(f"⚠️  Şema bulunamadı: {doc_type}")

            return {
                "belge_id": belge["belge_id"],
                "belge_adi": belge_adi,
                "belge_tipi": doc_type,  # İçerikten tespit edilen
                "api_belge_tipi": belge.get("belge_tipi"),  # API'den gelen
                "durum": "basarili",
                "base64": base64_data,  # Viewer için base64 içeriği
                "veri": extracted_data
            }

        finally:
            # 5. Geçici dosyayı temizle
            self.file_service.cleanup_temp_files(file_path)

    def create_master_json(
        self,
        basvuru_info: Dict,
        basvuran_info: Dict,
        processed_documents: List[Dict],
        basvuru_turu_hint: str = None  # Başvuru türü ipucu (erken tespit için)
    ) -> Dict:
        """
        Tüm belgelerden Master JSON oluştur

        Args:
            basvuru_info: Başvuru bilgileri
            basvuran_info: Başvuran bilgileri
            processed_documents: İşlenmiş belgeler
            basvuru_turu_hint: Başvuru türü ipucu (Akademisyen/Sektör/Bakanlık)

        Returns:
            Master JSON
        """
        logger.info("📊 Master JSON oluşturuluyor...")

        # Belgelerden verileri birleştir
        ustyazi_data = None
        ozgecmis_data = None
        sgk_data = None
        diploma_data = None
        adli_sicil_data = None
        hitap_data = None
        akademik_proje_data = []
        sektor_belge_data = []

        for doc in processed_documents:
            doc_type = doc.get("belge_tipi", "")
            doc_data = doc.get("veri", {})
            api_belge_tipi = doc.get("api_belge_tipi", "")

            if "ustyazi" in doc_type or "üst yazı" in doc_type or "başvuru formu" in doc_type:
                ustyazi_data = doc_data
            elif "özgeçmiş" in doc_type or "cv" in doc_type:
                ozgecmis_data = doc_data
            elif "sgk" in doc_type:
                sgk_data = doc_data
            elif "diploma" in doc_type:
                diploma_data = doc_data
            elif "adli sicil" in doc_type:
                adli_sicil_data = doc_data
            elif "hitap" in doc_type:
                hitap_data = doc_data
            elif "proje" in doc_type or "akademik proje" in doc_type:
                akademik_proje_data.append(doc_data)
            elif any(x in doc_type for x in ["endüstrisi", "iş deneyim", "çalışma belgesi", "sektör belgesi"]):
                sektor_belge_data.append(doc_data)

        # Başvuran bilgilerini güncelle (özgeçmişten)
        if ozgecmis_data:
            kisisel = ozgecmis_data.get("kisisel_bilgiler", {})
            if kisisel.get("ad"):
                basvuran_info["ad"] = kisisel["ad"]
            if kisisel.get("soyad"):
                basvuran_info["soyad"] = kisisel["soyad"]
            if kisisel.get("tc_kimlik_no"):
                basvuran_info["tc_kimlik_no"] = kisisel["tc_kimlik_no"]
            if kisisel.get("dogum_tarihi"):
                basvuran_info["dogum_tarihi"] = kisisel["dogum_tarihi"]
            if kisisel.get("telefon"):
                basvuran_info["telefon"] = kisisel["telefon"]
            if kisisel.get("email"):
                basvuran_info["email"] = kisisel["email"]

        # Eğitim durumu (diploma veya özgeçmişten)
        egitim_durumu = self._extract_education_info(diploma_data, ozgecmis_data)

        # İş deneyimi (SGK veya özgeçmişten)
        is_deneyimi = self._extract_experience_info(sgk_data, ozgecmis_data)

        # Sektör dağılımı hesapla
        sektor_dagilimi = self._calculate_sector_distribution(is_deneyimi)

        # Başvurulan sektörler (iş deneyiminden tespit et)
        basvurulan_sektorler = self._detect_applied_sectors(is_deneyimi)

        # Sektör belge durumu (hangi sektörler için belge var)
        sektor_belge_durumu = self._check_sector_documents(sektor_dagilimi)

        # Proje ve yayınlar (özgeçmişten)
        projeler_yayinlar = self._extract_projects_publications(ozgecmis_data)

        # Adli sicil bilgileri (detay) - Yüz kızartıcı suç dahil
        adli_sicil_bilgileri = self._extract_adli_sicil_info(adli_sicil_data)

        # Başvuru türünü tespit et (önce ustYazi'dan, yoksa hizmet adından)
        if ustyazi_data and ustyazi_data.get("basvuran_bilgileri"):
            basvuran_bilg = ustyazi_data["basvuran_bilgileri"]
            basvuru_turu = basvuran_bilg.get("basvuru_turu") or self._detect_application_type(basvuru_info.get("hizmet_adi", ""))
            basvurulan_alan = basvuran_bilg.get("basvurulan_alan") or self._detect_application_level(basvuru_info.get("hizmet_adi", ""))
            basvurulan_sektor_listesi = basvuran_bilg.get("basvurulan_sektorler", [])
        else:
            basvuru_turu = self._detect_application_type(basvuru_info.get("hizmet_adi", ""))
            basvurulan_alan = self._detect_application_level(basvuru_info.get("hizmet_adi", ""))
            basvurulan_sektor_listesi = []

        # Başvuru bilgilerini güncelle
        basvuru_info_full = basvuru_info.copy()
        basvuru_info_full["basvuru_turu"] = basvuru_turu
        basvuru_info_full["basvurulan_alan"] = basvurulan_alan
        basvuru_info_full["basvurulan_sektor_listesi"] = basvurulan_sektor_listesi

        # VALIDATION: Belgeler arası tutarlılık kontrolü (ÖNCE BU!)
        validation_result = self.validator.validate_application(
            basvuran_info,
            processed_documents
        )

        # REQUIREMENTS: Gerekli belgeler var mı kontrol et (hizmetAdi'ye göre)
        hizmet_adi = basvuru_info.get("hizmet_adi", "")
        requirements_result = self.requirements_checker.check_requirements(
            hizmet_adi,
            processed_documents
        )

        # Uygunluk değerlendirmesi (validation sonuçlarını da dikkate al)
        uygunluk = self._evaluate_eligibility(
            adli_sicil_data,
            adli_sicil_bilgileri,  # Detaylı adli sicil (yüz kızartıcı suç dahil)
            egitim_durumu,
            is_deneyimi,
            validation_result,  # VALIDATION SONUÇLARI
            basvuru_turu,       # Başvuru tipi (Akademisyen/Bakanlık/Sektör)
            basvurulan_alan,    # Pozisyon (Sorumlu/Başsorumlu)
            projeler_yayinlar,  # Projeler ve yayınlar
            sektor_dagilimi,    # Sektör deneyimi
            hitap_data          # Bakanlık deneyimi (Eski Bakanlık için)
        )

        # TABLO OLUŞTURMA (Tablo 1-8)
        logger.info("📋 Tablolar oluşturuluyor...")
        tablo1 = self._generate_tablo1_temel_bilgiler(ustyazi_data, basvuran_info, basvuru_info_full)
        tablo2 = self._generate_tablo2_basvurulan_sektorler(ustyazi_data, basvuru_turu)
        tablo3 = self._generate_tablo3_sektor_tecrubesi(sektor_dagilimi, basvuru_turu, basvurulan_alan)
        tablo4 = self._generate_tablo4_adli_sicil(adli_sicil_bilgileri)
        tablo5 = self._generate_tablo5_sektor_belge_durumu(sektor_belge_data, basvuru_turu)
        tablo6 = self._generate_tablo6_proje_yayin(akademik_proje_data, projeler_yayinlar, basvuru_turu, basvurulan_alan)
        tablo7 = self._generate_tablo7_mezuniyet(egitim_durumu)
        tablo8 = self._generate_tablo8_sonuc(uygunluk, validation_result, requirements_result, tablo1, tablo2, tablo3, tablo4, tablo5, tablo6, tablo7)

        # Tablo sonuçlarını logla
        for tablo in [tablo1, tablo2, tablo3, tablo4, tablo5, tablo6, tablo7, tablo8]:
            status_emoji = "✅" if tablo["validation_status"] == "green" else "❌" if tablo["validation_status"] == "red" else "⚠️" if tablo["validation_status"] == "yellow" else "⏸️" if tablo["validation_status"] == "pending" else "⏭️"
            logger.info(f"{status_emoji} {tablo['tablo_adi']}: {tablo.get('aciklama', tablo['validation_status'])}")

        # Master JSON
        master = {
            "basvuru_bilgileri": basvuru_info_full,
            "basvuran": basvuran_info,
            "basvurulan_sektorler": basvurulan_sektorler,
            "egitim_durumu": egitim_durumu,
            "is_deneyimi": is_deneyimi,
            "sektor_dagilimi": sektor_dagilimi,
            "sektor_belge_durumu": sektor_belge_durumu,
            "adli_sicil": adli_sicil_bilgileri,  # Adli sicil detay bilgileri (yüz kızartıcı suç dahil)
            "projeler_ve_yayinlar": projeler_yayinlar,
            "bakanlik_deneyimi": hitap_data,  # Hitap belgesi (Eski Bakanlık için)
            "akademik_projeler": akademik_proje_data,  # Akademik proje belgeleri (Akademisyen için)
            "sektor_belgeleri": sektor_belge_data,  # Sektör iş deneyim belgeleri
            "uygunluk": uygunluk,
            "validation": validation_result,  # Belgeler arası tutarlılık
            "requirements": requirements_result,  # Gerekli belgeler kontrolü
            "tablolar": {  # Tablo 1-8 (UI için)
                "tablo1_temel_bilgiler": tablo1,
                "tablo2_basvurulan_sektorler": tablo2,
                "tablo3_sektor_tecrubesi": tablo3,
                "tablo4_adli_sicil": tablo4,
                "tablo5_sektor_belge_durumu": tablo5,
                "tablo6_proje_yayin": tablo6,
                "tablo7_mezuniyet": tablo7,
                "tablo8_sonuc": tablo8
            },
            "isleme_zamani": datetime.now().isoformat(),
            "belgeler": [
                {
                    "belge_id": doc["belge_id"],
                    "belge_adi": doc["belge_adi"],
                    "belge_tipi": doc["belge_tipi"],
                    "api_belge_tipi": doc.get("api_belge_tipi"),
                    "durum": doc["durum"],
                    "base64": doc.get("base64")  # Viewer için base64 içeriği
                }
                for doc in processed_documents
            ]
        }

        # Validation sonuçlarını logla
        if not validation_result["valid"]:
            logger.error(f"❌ VALIDATION HATASI! Tutarlılık: %{validation_result['consistency_score']}")
            for error in validation_result["errors"]:
                logger.error(f"   {error}")

        if validation_result["warnings"]:
            logger.warning(f"⚠️  VALIDATION UYARILARI:")
            for warning in validation_result["warnings"]:
                logger.warning(f"   {warning}")

        # Requirements sonuçlarını logla
        if not requirements_result["valid"]:
            logger.error(f"❌ EKSİK BELGELER! Tamamlık: %{requirements_result['completeness_score']}")
            for error in requirements_result["errors"]:
                logger.error(f"   {error}")

        if requirements_result["warnings"]:
            logger.warning(f"⚠️  BELGE UYARILARI:")
            for warning in requirements_result["warnings"]:
                logger.warning(f"   {warning}")

        logger.info(f"✅ Master JSON oluşturuldu (Tutarlılık: %{validation_result['consistency_score']}, Tamamlık: %{requirements_result['completeness_score']})")
        return master

    def _extract_education_info(self, diploma_data: Dict, ozgecmis_data: Dict) -> Dict:
        """Eğitim bilgilerini çıkar"""
        if diploma_data and diploma_data.get("diploma_bilgileri"):
            dip = diploma_data["diploma_bilgileri"]
            # Eğer liste gelirse (boş liste olabilir), dictionary kontrolü yap
            if isinstance(dip, dict):
                return {
                    "en_yuksek_egitim": dip.get("diploma_turu"),
                    "universite": dip.get("universite"),
                    "bolum": dip.get("bolum"),
                    "mezuniyet_yili": dip.get("mezuniyet_tarihi", "")[:4] if dip.get("mezuniyet_tarihi") else None
                }
        if ozgecmis_data and ozgecmis_data.get("egitim"):
            egitimler = ozgecmis_data["egitim"]
            if egitimler and isinstance(egitimler, list):
                en_son = egitimler[0]  # İlk eğitim en yüksek olmalı
                if isinstance(en_son, dict):
                    return {
                        "en_yuksek_egitim": en_son.get("seviye"),
                        "universite": en_son.get("okul_adi"),
                        "bolum": en_son.get("bolum"),
                        "mezuniyet_yili": en_son.get("bitis_yili")
                    }

        return {
            "en_yuksek_egitim": None,
            "universite": None,
            "bolum": None,
            "mezuniyet_yili": None
        }

    def _extract_experience_info(self, sgk_data: Dict, ozgecmis_data: Dict) -> Dict:
        """İş deneyimi bilgilerini çıkar"""
        detaylar = []
        toplam_gun = 0

        # SGK'dan al (öncelikli)
        if sgk_data and sgk_data.get("calisma_gecmisi"):
            for calisma in sgk_data["calisma_gecmisi"]:
                isyeri_adi = calisma.get("isyeri_adi") or ""
                sure_gun = calisma.get("calisma_suresi_gun") or 0  # None güvenli
                detaylar.append({
                    "sirket": calisma.get("isyeri_adi"),
                    "pozisyon": calisma.get("meslek"),
                    "sektor": self._detect_sector(isyeri_adi),
                    "baslangic": calisma.get("ise_giris_tarihi"),
                    "bitis": calisma.get("isten_cikis_tarihi"),
                    "sure_gun": sure_gun,
                    "cevre_ile_ilgili": False  # SGK'da bu bilgi yok
                })
                toplam_gun += sure_gun

        # Özgeçmişten al (SGK yoksa)
        elif ozgecmis_data and ozgecmis_data.get("is_deneyimi"):
            for deneyim in ozgecmis_data["is_deneyimi"]:
                sure_gun = self._calculate_days_between(
                    deneyim.get("baslangic_tarihi"),
                    deneyim.get("bitis_tarihi")
                )
                sirket_adi = deneyim.get("sirket_adi") or ""
                detaylar.append({
                    "sirket": deneyim.get("sirket_adi"),
                    "pozisyon": deneyim.get("pozisyon"),
                    "sektor": deneyim.get("sektor") or self._detect_sector(sirket_adi),
                    "baslangic": deneyim.get("baslangic_tarihi"),
                    "bitis": deneyim.get("bitis_tarihi"),
                    "sure_gun": sure_gun,
                    "cevre_ile_ilgili": deneyim.get("cevre_ile_ilgili", False)
                })
                toplam_gun += sure_gun

        return {
            "toplam_sure_yil": round(toplam_gun / 365, 2) if toplam_gun > 0 else 0,
            "toplam_sure_gun": toplam_gun,
            "detaylar": detaylar
        }

    def _calculate_sector_distribution(self, is_deneyimi: Dict) -> List[Dict]:
        """Sektör dağılımını hesapla"""
        sektor_sureler = {}

        for detay in is_deneyimi.get("detaylar", []):
            sektor = detay.get("sektor", "Diğer")
            sure_gun = detay.get("sure_gun") or 0  # None güvenli

            if sektor in sektor_sureler:
                sektor_sureler[sektor] += sure_gun
            else:
                sektor_sureler[sektor] = sure_gun

        toplam_gun = is_deneyimi.get("toplam_sure_gun", 0)
        if toplam_gun == 0:
            return []

        dagilim = []
        for sektor, sure_gun in sektor_sureler.items():
            dagilim.append({
                "sektor_adi": sektor,
                "sure_gun": sure_gun,
                "sure_yil": round(sure_gun / 365, 2),
                "oran": round((sure_gun / toplam_gun) * 100, 2)
            })

        # Oranına göre sırala
        dagilim.sort(key=lambda x: x["oran"], reverse=True)
        return dagilim

    def _extract_adli_sicil_info(self, adli_sicil_data: Dict) -> Dict:
        """Adli sicil bilgilerini çıkar (yüz kızartıcı suç dahil)"""
        if not adli_sicil_data:
            return {
                "sabika_kaydi": None,
                "yuz_kizartici_suc": None,
                "belge_no": None,
                "aciklama": None,
                "suc_detaylari": []
            }

        belge_bilgileri = adli_sicil_data.get("belge_bilgileri", {})
        if isinstance(belge_bilgileri, dict):
            return {
                "sabika_kaydi": belge_bilgileri.get("sabika_kaydi"),
                "yuz_kizartici_suc": belge_bilgileri.get("yuz_kizartici_suc"),
                "belge_no": belge_bilgileri.get("belge_no"),
                "aciklama": belge_bilgileri.get("aciklama"),
                "suc_detaylari": belge_bilgileri.get("suc_detaylari", [])
            }

        return {
            "sabika_kaydi": None,
            "yuz_kizartici_suc": None,
            "belge_no": None,
            "aciklama": None,
            "suc_detaylari": []
        }

    def _evaluate_eligibility(
        self,
        adli_sicil_data: Dict,
        adli_sicil_bilgileri: Dict,
        egitim_durumu: Dict,
        is_deneyimi: Dict,
        validation_result: Dict,
        basvuru_turu: str,
        basvurulan_alan: str,
        projeler_yayinlar: Dict,
        sektor_dagilimi: list,
        hitap_data: Dict = None
    ) -> Dict:
        """
        Uygunluk bilgilerini topla (DEĞERLENDİRME YAPMAZ)

        ÖNEMLİ: Bu fonksiyon sadece bilgi çıkarımı yapar, hiçbir onay/red kararı vermez!

        Belgelerden çıkarılan bilgileri organize eder:
        - Akademisyen: İlgili sektörde makale/proje sayısı
        - Eski Bakanlık Personeli:
            * Bakanlık deneyim süresi (Sorumlu: 7 yıl, Başsorumlu: 10 yıl)
        - Sektör Çalışanı:
            * İlgili sektörde deneyim süresi (Sorumlu: 5 yıl, Başsorumlu: 10 yıl)

        Returns:
            Sadece çıkarılan bilgileri içeren dict (karar içermez)
        """

        # Validation hataları - sadece uyarı amaçlı, içerik değerlendirmesini etkilemez
        validation_errors = validation_result.get("errors", [])
        has_name_mismatch = any("isim" in err.lower() or "İsim" in err for err in validation_errors)
        has_tc_mismatch = any("tc" in err.lower() for err in validation_errors)
        has_diploma_tc_error = any("diploma" in err.lower() and "tc" in err.lower() for err in validation_errors)
        has_criminal_tc_error = any("adli sicil" in err.lower() and "tc" in err.lower() for err in validation_errors)

        # 1. Adli sicil kontrolü - SADECE belge içeriğine bak
        adli_sicil_temiz = True
        yuz_kizartici_suc_var = False

        if adli_sicil_bilgileri:
            # Belge içeriğinden sabıka kaydı var mı kontrol et
            sabika_kaydi = adli_sicil_bilgileri.get("sabika_kaydi", False)
            yuz_kizartici_suc_var = adli_sicil_bilgileri.get("yuz_kizartici_suc", False)

            # Sabıka kaydı varsa temiz değil
            if sabika_kaydi:
                adli_sicil_temiz = False
            # Yüz kızartıcı suç varsa mutlaka uygun değil
            if yuz_kizartici_suc_var:
                adli_sicil_temiz = False
        else:
            # Adli sicil belgesi yoksa veya okunamadıysa
            adli_sicil_temiz = None  # Bilinmiyor

        # 2. Eğitim kontrolü - SADECE eğitim seviyesine bak
        egitim_uygun = False
        en_yuksek = egitim_durumu.get("en_yuksek_egitim") or ""
        en_yuksek_lower = en_yuksek.lower() if en_yuksek else ""

        if any(x in en_yuksek_lower for x in ["lisans", "yüksek lisans", "doktora", "master"]):
            egitim_uygun = True
        elif not en_yuksek:
            # Eğitim bilgisi çekilemedi
            egitim_uygun = None  # Bilinmiyor

        # 3. Deneyim/Proje kontrolü (başvuru tipine göre değişir)
        deneyim_uygun = False
        deneyim_mesaji = ""

        basvuru_turu_lower = basvuru_turu.lower() if basvuru_turu else ""
        basvurulan_alan_lower = basvurulan_alan.lower() if basvurulan_alan else ""

        if "akademisyen" in basvuru_turu_lower:
            # AKADEMİSYEN: İlgili sektörde makale/proje olmalı
            proje_sayi = projeler_yayinlar.get("toplam_sayi", 0)
            if proje_sayi > 0:
                deneyim_uygun = True
                deneyim_mesaji = f"{proje_sayi} makale/proje mevcut"
            else:
                deneyim_mesaji = "İlgili sektörde makale/proje bulunamadı"

        elif "bakanlık" in basvuru_turu_lower or "çşib" in basvuru_turu_lower or "eski bakanlık" in basvuru_turu_lower:
            # ESKİ BAKANLIK PERSONELİ: Sorumlu 7 yıl, Başsorumlu 10 yıl
            gerekli_yil = 10 if "başsorumlu" in basvurulan_alan_lower or "baş sorumlu" in basvurulan_alan_lower else 7

            # Önce Hitap belgesinden Bakanlık deneyimini al
            bakanlik_yil = 0
            if hitap_data and hitap_data.get("cevre_bakanlik_suresi"):
                cevre_sure = hitap_data["cevre_bakanlik_suresi"]
                bakanlik_yil = cevre_sure.get("yil", 0)
                # Ay varsa yıla ekle
                if cevre_sure.get("ay"):
                    bakanlik_yil += cevre_sure.get("ay", 0) / 12

            # Hitap yoksa SGK'dan tahmin et (eski yöntem)
            if bakanlik_yil == 0:
                for detay in is_deneyimi.get("detaylar", []):
                    sirket = (detay.get("sirket") or "").lower()
                    if any(x in sirket for x in ["çevre", "bakanlık", "bakanligi", "çşib"]):
                        sure_yil = detay.get("sure_gun", 0) / 365 if detay.get("sure_gun") else 0
                        bakanlik_yil += sure_yil

            if bakanlik_yil >= gerekli_yil:
                deneyim_uygun = True
                deneyim_mesaji = f"Çevre Bakanlığı'nda {bakanlik_yil:.1f} yıl ({gerekli_yil} yıl gerekli)"
            else:
                deneyim_mesaji = f"Çevre Bakanlığı'nda {bakanlik_yil:.1f} yıl - {gerekli_yil} yıl gerekli"

        else:
            # SEKTÖR ÇALIŞANI: İlgili sektörde deneyim
            # Başsorumlu: 10 yıl, Sorumlu: 5 yıl
            gerekli_yil = 10 if "başsorumlu" in basvurulan_alan_lower or "baş sorumlu" in basvurulan_alan_lower else 5

            # İlgili 6 sektörden birinde deneyim var mı?
            ilgili_sektor_yili = 0
            ilgili_sektorler = ["Kimya", "Enerji", "Atık", "Mineral", "Metal", "Diğer"]

            for sektor_item in sektor_dagilimi:
                sektor_adi = sektor_item.get("sektor_adi", "")
                if any(s.lower() in sektor_adi.lower() for s in ilgili_sektorler):
                    sure_yil = sektor_item.get("sure_yil") or 0
                    ilgili_sektor_yili += sure_yil

            if ilgili_sektor_yili >= gerekli_yil:
                deneyim_uygun = True
                deneyim_mesaji = f"İlgili sektörde {ilgili_sektor_yili:.1f} yıl ({gerekli_yil} yıl gerekli)"
            else:
                deneyim_mesaji = f"İlgili sektörde {ilgili_sektor_yili:.1f} yıl - {gerekli_yil} yıl gerekli"

        # 4. Genel bilgi özeti (KARAR VERİCİ DEĞİL, sadece bilgilendirme)
        # Öncelikle kritik bilgiler var mı kontrol et
        bilgi_ozeti = []

        if adli_sicil_temiz is None:
            bilgi_ozeti.append("⚠️ Adli sicil belgesi bulunamadı veya okunamadı")
        elif yuz_kizartici_suc_var:
            suc_detay = adli_sicil_bilgileri.get("suc_detaylari", [])
            if suc_detay:
                bilgi_ozeti.append(f"❌ Yüz kızartıcı suç kaydı: {', '.join(suc_detay)}")
            else:
                bilgi_ozeti.append("❌ Yüz kızartıcı suç kaydı mevcut")
        elif adli_sicil_temiz == False:
            bilgi_ozeti.append("❌ Adli sicil kaydı mevcut")
        else:
            bilgi_ozeti.append("✓ Adli sicil temiz")

        if egitim_uygun is None:
            bilgi_ozeti.append("⚠️ Eğitim bilgisi çıkarılamadı")
        elif egitim_uygun == False:
            bilgi_ozeti.append("❌ Eğitim seviyesi: Minimum lisans gerekli")
        else:
            bilgi_ozeti.append(f"✓ Eğitim seviyesi: {egitim_durumu.get('en_yuksek_egitim', 'Lisans')}")

        if not deneyim_uygun:
            bilgi_ozeti.append(f"⚠️ Deneyim: {deneyim_mesaji}")
        else:
            bilgi_ozeti.append(f"✓ Deneyim: {deneyim_mesaji}")

        if not validation_result.get("valid", True):
            if has_tc_mismatch or has_name_mismatch:
                bilgi_ozeti.append("⚠️ Belge tutarsızlıkları mevcut (manuel kontrol gerekli)")
            else:
                bilgi_ozeti.append("⚠️ Küçük tutarsızlıklar mevcut")

        # Bilgi özetini metin olarak birleştir
        genel = " | ".join(bilgi_ozeti) if bilgi_ozeti else "Bilgi çıkarıldı"

        return {
            # Sadece çıkarılan bilgiler (karar yok!)
            "adli_sicil_durumu": {
                "sabika_kaydi": adli_sicil_temiz,
                "yuz_kizartici_suc": yuz_kizartici_suc_var
            },
            "egitim_durumu": {
                "uygun_seviye": egitim_uygun,
                "en_yuksek_egitim": egitim_durumu.get("en_yuksek_egitim")
            },
            "deneyim_durumu": {
                "yeterli": deneyim_uygun,
                "detay": deneyim_mesaji
            },
            "belge_tutarliligi": {
                "durum": "TUTARLI" if validation_result.get("valid", True) else "TUTARSIZ",
                "uyarilar": validation_errors if validation_errors else []
            },
            "genel_bilgi_ozeti": genel,  # Sadece bilgilendirme (karar değil!)
            "sistem_notu": "Bu bilgiler sadece personel için yardımcı bilgilerdir. Hiçbir şekilde otomatik karar verilmemiştir."
        }

    def _detect_sector(self, company_name: str) -> str:
        """Şirket adından sektör tahmini"""
        if not company_name:
            return "Diğer"

        company_lower = company_name.lower()

        if any(x in company_lower for x in ["enerji", "elektrik", "güneş", "rüzgar"]):
            return "Enerji"
        elif any(x in company_lower for x in ["inşaat", "yapı", "müteahhit"]):
            return "İnşaat"
        elif any(x in company_lower for x in ["teknoloji", "yazılım", "bilişim", "software"]):
            return "Teknoloji"
        elif any(x in company_lower for x in ["otomotiv", "automotive"]):
            return "Otomotiv"
        elif any(x in company_lower for x in ["kimya", "chemical"]):
            return "Kimya"
        elif any(x in company_lower for x in ["gıda", "food"]):
            return "Gıda"
        elif any(x in company_lower for x in ["tekstil", "textile"]):
            return "Tekstil"
        else:
            return "Diğer"

    def _calculate_days_between(self, start_date: str, end_date: str) -> int:
        """İki tarih arası gün sayısı"""
        try:
            from datetime import datetime

            if not start_date:
                return 0

            start = datetime.strptime(start_date[:10], "%Y-%m-%d")

            if not end_date:
                end = datetime.now()
            elif "devam" in str(end_date).lower():
                end = datetime.now()
            else:
                end = datetime.strptime(end_date[:10], "%Y-%m-%d")

            delta = end - start
            return max(0, delta.days)

        except Exception:
            return 0

    def _detect_applied_sectors(self, is_deneyimi: Dict) -> Dict:
        """İş deneyiminden başvurulan sektörleri tespit et"""
        sektorler = {
            "enerji": False,
            "metal": False,
            "mineral": False,
            "kimya": False,
            "atik": False,
            "diger": False
        }

        for detay in is_deneyimi.get("detaylar", []):
            sektor = (detay.get("sektor") or "").lower()
            if "enerji" in sektor or "elektrik" in sektor:
                sektorler["enerji"] = True
            elif "metal" in sektor or "demir" in sektor or "çelik" in sektor:
                sektorler["metal"] = True
            elif "mineral" in sektor or "çimento" in sektor or "seramik" in sektor:
                sektorler["mineral"] = True
            elif "kimya" in sektor or "petrokimya" in sektor:
                sektorler["kimya"] = True
            elif "atık" in sektor or "atik" in sektor or "geri dönüşüm" in sektor:
                sektorler["atik"] = True
            else:
                sektorler["diger"] = True

        return sektorler

    def _check_sector_documents(self, sektor_dagilimi: List[Dict]) -> Dict:
        """Hangi sektörler için belge var?"""
        belge_durumu = {
            "enerji": False,
            "metal": False,
            "mineral": False,
            "kimya": False,
            "atik": False,
            "diger": False
        }

        for sektor in sektor_dagilimi:
            sektor_adi = (sektor.get("sektor_adi") or "").lower()
            if "enerji" in sektor_adi or "elektrik" in sektor_adi:
                belge_durumu["enerji"] = True
            elif "metal" in sektor_adi or "demir" in sektor_adi or "çelik" in sektor_adi:
                belge_durumu["metal"] = True
            elif "mineral" in sektor_adi or "çimento" in sektor_adi or "seramik" in sektor_adi:
                belge_durumu["mineral"] = True
            elif "kimya" in sektor_adi or "petrokimya" in sektor_adi:
                belge_durumu["kimya"] = True
            elif "atık" in sektor_adi or "atik" in sektor_adi or "geri dönüşüm" in sektor_adi:
                belge_durumu["atik"] = True
            else:
                belge_durumu["diger"] = True

        return belge_durumu

    def _extract_projects_publications(self, ozgecmis_data: Dict) -> Dict:
        """Özgeçmişten proje ve yayınları çıkar"""
        if not ozgecmis_data:
            return {
                "toplam_sayi": 0,
                "liste": []
            }

        projeler = ozgecmis_data.get("projeler_ve_yayinlar", [])

        return {
            "toplam_sayi": len(projeler),
            "liste": projeler
        }

    def _detect_application_type(self, hizmet_adi: str) -> str:
        """Başvuru türünü tespit et"""
        if not hizmet_adi:
            return "Bilinmiyor"

        hizmet_lower = hizmet_adi.lower()

        if "sektör çalışanı" in hizmet_lower:
            return "Sektör Çalışanı"
        elif "akademisyen" in hizmet_lower:
            return "Akademisyen"
        elif "bakanlık" in hizmet_lower or "kamu" in hizmet_lower:
            return "Eski Bakanlık"
        else:
            return "Sektör Çalışanı"  # Default

    def _detect_application_level(self, hizmet_adi: str) -> str:
        """Başvurulan alanı tespit et (Sorumlu/Başsorumlu)"""
        if not hizmet_adi:
            return "Bilinmiyor"

        hizmet_lower = hizmet_adi.lower()

        if "baş sorumlu" in hizmet_lower or "başsorumlu" in hizmet_lower:
            return "Başsorumlu"
        elif "sorumlu" in hizmet_lower:
            return "Sorumlu"
        else:
            return "Sorumlu"  # Default

    # =============================================================================
    # TABLO OLUŞTURMA METODLARİ (Tablo 1-8)
    # =============================================================================

    def _generate_tablo1_temel_bilgiler(
        self,
        ustyazi_data: Dict,
        basvuran_info: Dict,
        basvuru_info: Dict
    ) -> Dict:
        """
        Tablo 1: Temel Bilgiler
        - Evrak no, tarih, başvuru türü, alan, ad, soyad
        """
        evrak_bilgileri = {}
        if ustyazi_data and ustyazi_data.get("evrak_bilgileri"):
            evrak_bilgileri = ustyazi_data["evrak_bilgileri"]

        basvuran_bilgileri = {}
        if ustyazi_data and ustyazi_data.get("basvuran_bilgileri"):
            basvuran_bilgileri = ustyazi_data["basvuran_bilgileri"]

        # Validasyon: Tüm bilgiler mevcut mu?
        evrak_no = evrak_bilgileri.get("evrak_no")
        evrak_tarihi = evrak_bilgileri.get("evrak_tarihi")
        ad = basvuran_info.get("ad") or basvuran_bilgileri.get("ad")
        soyad = basvuran_info.get("soyad") or basvuran_bilgileri.get("soyad")
        basvuru_turu = basvuru_info.get("basvuru_turu")
        basvurulan_alan = basvuru_info.get("basvurulan_alan")

        eksik_alanlar = []
        if not evrak_no:
            eksik_alanlar.append("Evrak No")
        if not evrak_tarihi:
            eksik_alanlar.append("Evrak Tarihi")
        if not ad:
            eksik_alanlar.append("Ad")
        if not soyad:
            eksik_alanlar.append("Soyad")
        if not basvuru_turu or basvuru_turu == "Bilinmiyor":
            eksik_alanlar.append("Başvuru Türü")
        if not basvurulan_alan or basvurulan_alan == "Bilinmiyor":
            eksik_alanlar.append("Başvurulan Alan")

        validation_status = "green" if not eksik_alanlar else "red"

        return {
            "tablo_adi": "Tablo 1: Temel Bilgiler",
            "validation_status": validation_status,
            "eksik_alanlar": eksik_alanlar,
            "data": {
                "evrak_no": evrak_no,
                "evrak_tarihi": evrak_tarihi,
                "ad": ad,
                "soyad": soyad,
                "tc_kimlik_no": basvuran_info.get("tc_kimlik_no"),
                "basvuru_turu": basvuru_turu,
                "basvurulan_alan": basvurulan_alan,
                "basvuru_tarihi": basvuru_info.get("basvuru_tarihi")
            }
        }

    def _generate_tablo2_basvurulan_sektorler(
        self,
        ustyazi_data: Dict,
        basvuru_turu: str
    ) -> Dict:
        """
        Tablo 2: Başvurulan Sektörler
        - X işaretleme, Diğer restrictions
        - Akademisyen için bu tabloya bakılmaz (skip edilir)
        """
        # Akademisyen ise tablo oluşturma
        if "akademisyen" in basvuru_turu.lower():
            return {
                "tablo_adi": "Tablo 2: Başvurulan Sektörler",
                "validation_status": "skip",
                "aciklama": "Akademisyen başvurular için bu tablo değerlendirilmez",
                "data": None
            }

        basvurulan_sektor_listesi = []
        if ustyazi_data and ustyazi_data.get("basvuran_bilgileri"):
            basvurulan_sektor_listesi = ustyazi_data["basvuran_bilgileri"].get("basvurulan_sektorler", [])

        # Sektör listesi
        sektorler = {
            "Enerji": False,
            "Metal": False,
            "Kimya": False,
            "Mineral": False,
            "Atık": False,
            "Diğer Üretim Faaliyetleri": False
        }

        # İşaretle
        for sektor in basvurulan_sektor_listesi:
            if sektor in sektorler:
                sektorler[sektor] = True

        # Validasyon: En az 1 sektör seçilmiş mi?
        secili_sektor_sayisi = sum(1 for v in sektorler.values() if v)
        validation_status = "green" if secili_sektor_sayisi > 0 else "red"

        # "Diğer" seçilmişse uyarı
        diger_uyari = None
        if sektorler["Diğer Üretim Faaliyetleri"]:
            diger_uyari = "UYARI: 'Diğer Üretim Faaliyetleri' sadece Gıda, Otomotiv, Tekstil, Deri, Atıksu Arıtma için geçerlidir"

        return {
            "tablo_adi": "Tablo 2: Başvurulan Sektörler",
            "validation_status": validation_status,
            "aciklama": f"{secili_sektor_sayisi} sektör seçilmiş" if secili_sektor_sayisi > 0 else "Hiç sektör seçilmemiş",
            "diger_uyari": diger_uyari,
            "data": sektorler
        }

    def _generate_tablo3_sektor_tecrubesi(
        self,
        sektor_dagilimi: List[Dict],
        basvuru_turu: str,
        basvurulan_alan: str
    ) -> Dict:
        """
        Tablo 3: Sektördeki İş Tecrübesi
        - Her sektör için yıl hesabı
        - Akademisyen için bu tabloya bakılmaz (skip edilir)
        """
        # Akademisyen ise tablo oluşturma
        if "akademisyen" in basvuru_turu.lower():
            return {
                "tablo_adi": "Tablo 3: Sektördeki İş Tecrübesi",
                "validation_status": "skip",
                "aciklama": "Akademisyen başvurular için bu tablo değerlendirilmez",
                "data": None
            }

        # Gerekli deneyim süresi
        gerekli_yil = 10 if "başsorumlu" in basvurulan_alan.lower() or "baş sorumlu" in basvurulan_alan.lower() else 5

        # İlgili 6 sektörden deneyimleri topla
        ilgili_sektorler = ["Kimya", "Enerji", "Atık", "Mineral", "Metal", "Diğer"]
        sektor_tecrubesi = {
            "Enerji": 0,
            "Metal": 0,
            "Kimya": 0,
            "Mineral": 0,
            "Atık": 0,
            "Diğer Üretim Faaliyetleri": 0
        }

        toplam_ilgili_yil = 0
        for sektor_item in sektor_dagilimi:
            sektor_adi = sektor_item.get("sektor_adi", "")
            sure_yil = sektor_item.get("sure_yil", 0)

            # Sektör eşleştirme
            if "enerji" in sektor_adi.lower() or "elektrik" in sektor_adi.lower():
                sektor_tecrubesi["Enerji"] += sure_yil
                toplam_ilgili_yil += sure_yil
            elif "metal" in sektor_adi.lower() or "demir" in sektor_adi.lower() or "çelik" in sektor_adi.lower():
                sektor_tecrubesi["Metal"] += sure_yil
                toplam_ilgili_yil += sure_yil
            elif "kimya" in sektor_adi.lower() or "petrokimya" in sektor_adi.lower():
                sektor_tecrubesi["Kimya"] += sure_yil
                toplam_ilgili_yil += sure_yil
            elif "mineral" in sektor_adi.lower() or "çimento" in sektor_adi.lower() or "seramik" in sektor_adi.lower():
                sektor_tecrubesi["Mineral"] += sure_yil
                toplam_ilgili_yil += sure_yil
            elif "atık" in sektor_adi.lower() or "atik" in sektor_adi.lower() or "geri dönüşüm" in sektor_adi.lower():
                sektor_tecrubesi["Atık"] += sure_yil
                toplam_ilgili_yil += sure_yil
            else:
                sektor_tecrubesi["Diğer Üretim Faaliyetleri"] += sure_yil
                toplam_ilgili_yil += sure_yil

        # Validasyon: Gerekli deneyim var mı?
        validation_status = "green" if toplam_ilgili_yil >= gerekli_yil else "red"

        return {
            "tablo_adi": "Tablo 3: Sektördeki İş Tecrübesi",
            "validation_status": validation_status,
            "gerekli_yil": gerekli_yil,
            "toplam_yil": round(toplam_ilgili_yil, 2),
            "aciklama": f"{toplam_ilgili_yil:.1f} yıl deneyim ({gerekli_yil} yıl gerekli)" if toplam_ilgili_yil >= gerekli_yil else f"YETERSİZ: {toplam_ilgili_yil:.1f} yıl - {gerekli_yil} yıl gerekli",
            "data": sektor_tecrubesi
        }

    def _generate_tablo4_adli_sicil(
        self,
        adli_sicil_bilgileri: Dict
    ) -> Dict:
        """
        Tablo 4: Adli Sicil Bilgileri
        - Adli Sicil Kaydı (Var/Yok)
        - Adli Sicil Kaydı Kodu (belge numarası)
        """
        sabika_kaydi = adli_sicil_bilgileri.get("sabika_kaydi")
        yuz_kizartici_suc = adli_sicil_bilgileri.get("yuz_kizartici_suc")
        suc_detaylari = adli_sicil_bilgileri.get("suc_detaylari", [])
        belge_no = adli_sicil_bilgileri.get("belge_no")

        # Adli sicil kaydı var mı? (Var/Yok formatında)
        adli_sicil_kaydi_var = "Var" if sabika_kaydi or yuz_kizartici_suc else "Yok" if sabika_kaydi is not None else None

        # Validasyon: Sabıka kaydı veya yüz kızartıcı suç varsa red
        if yuz_kizartici_suc:
            validation_status = "red"
            aciklama = "Yüz kızartıcı suç kaydı mevcut - UYGUN DEĞİL"
        elif sabika_kaydi:
            validation_status = "red"
            aciklama = "Sabıka kaydı mevcut - UYGUN DEĞİL"
        elif sabika_kaydi is None:
            validation_status = "red"
            aciklama = "Adli sicil belgesi bulunamadı veya okunamadı"
        else:
            validation_status = "green"
            aciklama = "Adli sicil temiz"

        return {
            "tablo_adi": "Tablo 4: Adli Sicil Bilgileri",
            "validation_status": validation_status,
            "aciklama": aciklama,
            "data": {
                "adli_sicil_kaydi": adli_sicil_kaydi_var,  # Var/Yok
                "adli_sicil_kaydi_kodu": belge_no,  # Belge numarası
                "yuz_kizartici_suc": yuz_kizartici_suc,
                "suc_detaylari": suc_detaylari
            }
        }

    def _generate_tablo5_sektor_belge_durumu(
        self,
        sektor_belge_data: List[Dict],
        basvuru_turu: str
    ) -> Dict:
        """
        Tablo 5: Başvurulan Sektörde Çalıştığı Kanıtlıyan Doküman Eki Bilgileri
        - Her sektör için Var/Yok formatında belge durumu
        - Akademisyen için bu tabloya bakılmaz (skip edilir)
        """
        # Akademisyen ise tablo oluşturma
        if "akademisyen" in basvuru_turu.lower():
            return {
                "tablo_adi": "Tablo 5: Başvurulan Sektörde Çalıştığı Kanıtlıyan Doküman Eki Bilgileri",
                "validation_status": "skip",
                "aciklama": "Akademisyen başvurular için bu tablo değerlendirilmez",
                "data": None
            }

        # Sektör belge durumu (Var/Yok formatında)
        sektor_belge_durumu = {
            "Enerji": "Yok",
            "Metal": "Yok",
            "Kimya": "Yok",
            "Mineral": "Yok",
            "Atık": "Yok",
            "Diğer Üretim Faaliyetleri": "Yok"
        }

        # Her belgeyi sektörüne göre işaretle
        for belge in sektor_belge_data:
            firma_bilgileri = belge.get("firma_bilgileri", {})
            sektor = firma_bilgileri.get("sektor", "Diğer Üretim Faaliyetleri")

            # Sektör eşleştirme
            if "enerji" in sektor.lower() or "elektrik" in sektor.lower():
                sektor_belge_durumu["Enerji"] = "Var"
            elif "metal" in sektor.lower() or "demir" in sektor.lower() or "çelik" in sektor.lower():
                sektor_belge_durumu["Metal"] = "Var"
            elif "kimya" in sektor.lower() or "petrokimya" in sektor.lower():
                sektor_belge_durumu["Kimya"] = "Var"
            elif "mineral" in sektor.lower() or "çimento" in sektor.lower() or "seramik" in sektor.lower():
                sektor_belge_durumu["Mineral"] = "Var"
            elif "atık" in sektor.lower() or "atik" in sektor.lower() or "geri dönüşüm" in sektor.lower():
                sektor_belge_durumu["Atık"] = "Var"
            else:
                sektor_belge_durumu["Diğer Üretim Faaliyetleri"] = "Var"

        # Validasyon: Bu tablo opsiyonel (sarı)
        toplam_var = sum(1 for v in sektor_belge_durumu.values() if v == "Var")
        validation_status = "yellow"  # Opsiyonel belgeler
        aciklama = f"{toplam_var} sektör için belge mevcut" if toplam_var > 0 else "Sektör belgesi yok (opsiyonel)"

        return {
            "tablo_adi": "Tablo 5: Başvurulan Sektörde Çalıştığı Kanıtlıyan Doküman Eki Bilgileri",
            "validation_status": validation_status,
            "aciklama": aciklama,
            "data": sektor_belge_durumu
        }

    def _generate_tablo6_proje_yayin(
        self,
        akademik_proje_data: List[Dict],
        projeler_yayinlar: Dict,
        basvuru_turu: str,
        basvurulan_alan: str
    ) -> Dict:
        """
        Tablo 6: Proje/Yayın/Bildiri Bilgileri
        - Proje/Yayın/Bildiri Sayısı
        - Proje/Yayın/Bildiri 1, 2, 3 (detaylı açıklama)
        - Akademisyen için: Sorumlu min 1, Başsorumlu min 3
        - Sektör ve Bakanlık için bu tabloya bakılmaz (skip edilir)
        """
        # Sektör veya Bakanlık ise tablo oluşturma
        if "akademisyen" not in basvuru_turu.lower():
            return {
                "tablo_adi": "Tablo 6: Proje/Yayın/Bildiri Bilgileri",
                "validation_status": "skip",
                "aciklama": "Sadece Akademisyen başvurular için değerlendirilir",
                "data": None
            }

        # Gerekli minimum proje sayısı
        min_proje = 3 if "başsorumlu" in basvurulan_alan.lower() or "baş sorumlu" in basvurulan_alan.lower() else 1

        # Proje/yayın listesi (APA 7 format)
        proje_listesi = []

        # Akademik proje belgelerinden
        for proje in akademik_proje_data:
            # Schema'da apa7_format ana seviyede
            apa7_format = proje.get("apa7_format")
            sektor_uygunlugu = proje.get("sektor_uygunlugu", [])

            if apa7_format:
                proje_listesi.append({
                    "tip": "Proje",
                    "apa_format": apa7_format,
                    "sektor": sektor_uygunlugu
                })

            # Proje çıktılarını da ekle
            ciktilar = proje.get("ciktilar", {})
            yayinlar = ciktilar.get("yayinlar", [])
            for yayin in yayinlar:
                proje_listesi.append({
                    "tip": "Yayın",
                    "apa_format": yayin,
                    "sektor": sektor_uygunlugu
                })

        # Özgeçmişten proje/yayınlar
        ozgecmis_projeler = projeler_yayinlar.get("liste", [])
        for item in ozgecmis_projeler:
            # Eğer APA formatında değilse atla
            if isinstance(item, str) and len(item) > 20:
                proje_listesi.append({
                    "tip": "Proje/Yayın",
                    "apa_format": item,
                    "sektor": []
                })

        toplam_sayi = len(proje_listesi)

        # İlk 3 proje/yayın detayı
        proje_yayin_1 = proje_listesi[0]["apa_format"] if len(proje_listesi) > 0 else None
        proje_yayin_2 = proje_listesi[1]["apa_format"] if len(proje_listesi) > 1 else None
        proje_yayin_3 = proje_listesi[2]["apa_format"] if len(proje_listesi) > 2 else None

        # Validasyon
        validation_status = "green" if toplam_sayi >= min_proje else "red"
        aciklama = f"{toplam_sayi} proje/yayın ({min_proje} gerekli)" if toplam_sayi >= min_proje else f"YETERSİZ: {toplam_sayi} proje/yayın - {min_proje} gerekli"

        return {
            "tablo_adi": "Tablo 6: Proje/Yayın/Bildiri Bilgileri",
            "validation_status": validation_status,
            "min_gerekli": min_proje,
            "aciklama": aciklama,
            "data": {
                "proje_yayin_bildiri_sayisi": toplam_sayi,
                "proje_yayin_bildiri_1": proje_yayin_1,
                "proje_yayin_bildiri_2": proje_yayin_2,
                "proje_yayin_bildiri_3": proje_yayin_3,
                "tum_liste": proje_listesi  # Tüm liste (görünür değil ama veri kaybı olmasın diye)
            }
        }

    def _generate_tablo7_mezuniyet(
        self,
        egitim_durumu: Dict
    ) -> Dict:
        """
        Tablo 7: Mezuniyet Bilgileri
        - Tüm başvurular için minimum lisans gerekli
        """
        en_yuksek_egitim = egitim_durumu.get("en_yuksek_egitim", "")
        universite = egitim_durumu.get("universite", "")
        bolum = egitim_durumu.get("bolum", "")
        mezuniyet_yili = egitim_durumu.get("mezuniyet_yili", "")

        # Validasyon: Minimum lisans gerekli
        en_yuksek_lower = en_yuksek_egitim.lower() if en_yuksek_egitim else ""
        lisans_uygun = any(x in en_yuksek_lower for x in ["lisans", "yüksek lisans", "doktora", "master"])

        if lisans_uygun:
            validation_status = "green"
            aciklama = f"{en_yuksek_egitim} mezunu - UYGUN"
        elif not en_yuksek_egitim:
            validation_status = "red"
            aciklama = "Eğitim bilgisi bulunamadı"
        else:
            validation_status = "red"
            aciklama = f"{en_yuksek_egitim} - Minimum lisans gerekli"

        return {
            "tablo_adi": "Tablo 7: Mezuniyet Bilgileri",
            "validation_status": validation_status,
            "aciklama": aciklama,
            "data": {
                "en_yuksek_egitim": en_yuksek_egitim,
                "universite": universite,
                "bolum": bolum,
                "mezuniyet_yili": mezuniyet_yili
            }
        }

    def _generate_tablo8_sonuc(
        self,
        uygunluk: Dict,
        validation_result: Dict,
        requirements_result: Dict,
        tablo1: Dict,
        tablo2: Dict,
        tablo3: Dict,
        tablo4: Dict,
        tablo5: Dict,
        tablo6: Dict,
        tablo7: Dict
    ) -> Dict:
        """
        Tablo 8: Sonuç

        ÖNEMLİ: Bu tablo SİSTEM TARAFIND AN DOLDURULMAZ!

        Sistem yalnızca bilgi çıkarımı yapar, hiçbir değerlendirme veya karar verme
        işlemi gerçekleştirmez. Tablo 8, değerlendirme personeli tarafından
        Tablo 1-7'deki bilgileri inceledikten sonra manuel olarak doldurulacaktır.

        Bu yaklaşım:
        - Yanlış pozitif/negatif sonuçların önüne geçer
        - Personelin gereksiz yere sistem değerlendirmelerini kontrol etme
          ihtiyacını ortadan kaldırır
        - Tüm karar verme yetkisini uzman personelde tutar
        """
        # Personel için yardımcı bilgiler topla (karar vermeden)
        onemli_uyarilar = []
        kritik_eksikler = []

        # Tablo 1: Temel Bilgiler
        if tablo1["validation_status"] == "red":
            eksik = ", ".join(tablo1.get("eksik_alanlar", []))
            kritik_eksikler.append(f"Temel Bilgiler: Eksik alanlar - {eksik}")

        # Tablo 2: Başvurulan Sektörler (Akademisyen hariç)
        if tablo2["validation_status"] == "red":
            kritik_eksikler.append(f"Başvurulan Sektörler: {tablo2['aciklama']}")

        # Tablo 3: Sektör Tecrübesi (Akademisyen hariç)
        if tablo3["validation_status"] == "red":
            kritik_eksikler.append(f"Sektör Tecrübesi: {tablo3['aciklama']}")

        # Tablo 4: Adli Sicil (KRİTİK)
        if tablo4["validation_status"] == "red":
            kritik_eksikler.append(f"Adli Sicil: {tablo4['aciklama']}")

        # Tablo 5: Sektör Belge (Opsiyonel - sadece bilgilendirme)
        if tablo5["validation_status"] == "yellow":
            onemli_uyarilar.append(f"Sektör Belgesi: {tablo5['aciklama']}")

        # Tablo 6: Proje/Yayın (Akademisyen için kritik)
        if tablo6["validation_status"] == "red":
            kritik_eksikler.append(f"Proje/Yayın: {tablo6['aciklama']}")

        # Tablo 7: Mezuniyet (KRİTİK)
        if tablo7["validation_status"] == "red":
            kritik_eksikler.append(f"Mezuniyet: {tablo7['aciklama']}")

        # Validation uyarıları
        if not validation_result.get("valid", True):
            for error in validation_result.get("errors", []):
                onemli_uyarilar.append(f"Belge Tutarsızlığı: {error}")

        # Requirements eksikleri
        if not requirements_result.get("valid", True):
            for error in requirements_result.get("errors", []):
                kritik_eksikler.append(f"Eksik Belge: {error}")

        # Sistem BİR KARAR VERMİYOR, sadece özet bilgi sunuyor
        return {
            "tablo_adi": "Tablo 8: Sonuç",
            "validation_status": "pending",  # Personel değerlendirmesi bekleniyor
            "aciklama": "Bu tablo değerlendirme personeli tarafından doldurulacaktır",
            "sistem_notu": "Sistem hiçbir onay/red kararı vermez. Tüm değerlendirme ve karar verme yetkisi uzman personeldedir.",
            "data": {
                # Personel tarafından doldurulacak alanlar
                "basvuru_sonucu": None,  # Personel "Onaylandı" veya "Reddedildi" yazacak
                "personel_aciklama": None,  # Personel açıklama yazacak

                # Personel için yardımcı bilgiler (sadece bilgilendirme amaçlı)
                "yardimci_bilgiler": {
                    "kritik_eksikler": kritik_eksikler,  # Personelin dikkat etmesi gereken eksikler
                    "onemli_uyarilar": onemli_uyarilar,  # Personelin değerlendirmesi gereken uyarılar
                    "tutarlilik_skoru": validation_result.get("consistency_score", 0),
                    "tamamlik_skoru": requirements_result.get("completeness_score", 0),
                    "genel_bilgi": uygunluk.get("genel_bilgi_ozeti", "")  # Sadece bilgilendirme
                }
            }
        }
