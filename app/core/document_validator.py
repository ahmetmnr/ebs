"""
Belge doğrulama ve tutarlılık kontrolü
"""
import logging
from typing import Dict, List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Belgeler arası tutarlılık kontrolü"""

    def __init__(self):
        self.warnings = []
        self.errors = []

    def validate_application(
        self,
        basvuran_info: Dict,
        processed_documents: List[Dict]
    ) -> Dict:
        """
        Tüm belgeleri doğrula ve tutarlılık kontrol et

        Returns:
            {
                "valid": bool,
                "warnings": List[str],
                "errors": List[str],
                "consistency_score": float  # 0-100
            }
        """
        self.warnings = []
        self.errors = []

        # 1. İsim kontrolü (tüm belgelerde aynı kişi olmalı)
        self._check_name_consistency(basvuran_info, processed_documents)

        # 2. TC Kimlik kontrolü
        self._check_tc_consistency(basvuran_info, processed_documents)

        # 3. Diploma-Eğitim tutarlılığı
        self._check_education_consistency(processed_documents)

        # 4. SGK-Özgeçmiş tutarlılığı
        self._check_experience_consistency(processed_documents)

        # 5. Adli sicil kontrolü
        self._check_criminal_record(processed_documents)

        # Tutarlılık skoru hesapla
        total_checks = 10  # Toplam kontrol sayısı
        passed_checks = total_checks - len(self.errors) - (len(self.warnings) * 0.5)
        consistency_score = max(0, (passed_checks / total_checks) * 100)

        return {
            "valid": len(self.errors) == 0,
            "warnings": self.warnings,
            "errors": self.errors,
            "consistency_score": round(consistency_score, 2)
        }

    def _check_name_consistency(self, basvuran_info: Dict, documents: List[Dict]):
        """İsim tutarlılığı kontrolü - TÜM belgelerde isim aynı kişiye ait olmalı"""
        basvuru_ad = (basvuran_info.get("ad") or "").strip().lower()
        basvuru_soyad = (basvuran_info.get("soyad") or "").strip().lower()
        basvuru_tam_ad = f"{basvuru_ad} {basvuru_soyad}"

        if not basvuru_ad or not basvuru_soyad:
            self.warnings.append("⚠️  Başvuran ad/soyad bilgisi eksik")
            return

        # Tüm belgelerden isimleri topla
        belgelerden_isimler = []

        for doc in documents:
            doc_type = doc.get("belge_tipi", "")
            doc_data = doc.get("veri", {})

            # Her belgeden isim çıkar
            belge_ismi = None
            original_isim = None  # Orijinal hali (küçük harfe çevrilmemiş)

            if "özgeçmiş" in doc_type or "cv" in doc_type:
                kisisel = doc_data.get("kisisel_bilgiler", {})
                doc_ad = (kisisel.get("ad") or "").strip()
                doc_soyad = (kisisel.get("soyad") or "").strip()
                if doc_ad and doc_soyad:
                    original_isim = f"{doc_ad} {doc_soyad}"
                    belge_ismi = original_isim.lower()

            elif "diploma" in doc_type:
                ogrenci = doc_data.get("ogrenci_bilgileri", {})
                original_isim = (ogrenci.get("ad_soyad") or "").strip()
                if original_isim:
                    belge_ismi = original_isim.lower()

            elif "sgk" in doc_type:
                kisi = doc_data.get("kisi_bilgileri", {})
                original_isim = (kisi.get("ad_soyad") or "").strip()
                if original_isim:
                    belge_ismi = original_isim.lower()

            elif "adli sicil" in doc_type:
                kisi = doc_data.get("kisi_bilgileri", {})
                original_isim = (kisi.get("ad_soyad") or "").strip()
                if original_isim:
                    belge_ismi = original_isim.lower()

            # Belge ismini listeye ekle
            if belge_ismi and original_isim:
                belgelerden_isimler.append({
                    "belge_tipi": doc_type,
                    "isim": belge_ismi,
                    "original": original_isim
                })

                # Başvuru sahibi ile karşılaştır
                similarity = self._calculate_similarity(basvuru_tam_ad, belge_ismi)
                if similarity < 0.8:  # %80'den düşükse hata
                    self.errors.append(
                        f"❌ {doc_type.upper()} - İsim uyuşmazlığı: "
                        f"Başvuru='{basvuran_info.get('ad')} {basvuran_info.get('soyad')}' "
                        f"vs Belge='{original_isim}' "
                        f"(Benzerlik: %{similarity*100:.0f})"
                    )

        # Belgeler kendi aralarında tutarlı mı kontrol et
        if len(belgelerden_isimler) >= 2:
            for i in range(len(belgelerden_isimler)):
                for j in range(i + 1, len(belgelerden_isimler)):
                    isim1 = belgelerden_isimler[i]
                    isim2 = belgelerden_isimler[j]

                    similarity = self._calculate_similarity(isim1["isim"], isim2["isim"])
                    if similarity < 0.8:  # Belgeler birbirine uyuşmuyor
                        self.warnings.append(
                            f"⚠️  Belgeler arası isim tutarsızlığı: "
                            f"{isim1['belge_tipi'].upper()}='{isim1['original']}' "
                            f"vs {isim2['belge_tipi'].upper()}='{isim2['original']}' "
                            f"(Benzerlik: %{similarity*100:.0f})"
                        )

    def _check_tc_consistency(self, basvuran_info: Dict, documents: List[Dict]):
        """TC Kimlik tutarlılığı - SADECE TC içeren belgelerde kontrol et"""
        basvuru_tc = (basvuran_info.get("tc_kimlik_no") or "").strip()

        if not basvuru_tc:
            self.warnings.append("⚠️  TC Kimlik No eksik")
            return

        for doc in documents:
            doc_type = doc.get("belge_tipi", "")
            doc_data = doc.get("veri", {})

            doc_tc = None

            # SADECE TC içeren belgeler (SGK belgesi TC içermez, SGK sicil numarası içerir!)
            if "özgeçmiş" in doc_type or "cv" in doc_type:
                doc_tc = (doc_data.get("kisisel_bilgiler", {}).get("tc_kimlik_no") or "").strip()
            elif "diploma" in doc_type:
                doc_tc = (doc_data.get("ogrenci_bilgileri", {}).get("tc_kimlik_no") or "").strip()
            elif "adli sicil" in doc_type:
                doc_tc = (doc_data.get("kisi_bilgileri", {}).get("tc_kimlik_no") or "").strip()
            # NOT: SGK belgesi TC içermez, o yüzden kontrol etme!

            if doc_tc and doc_tc != basvuru_tc:
                self.errors.append(
                    f"❌ {doc_type.upper()} - TC uyuşmazlığı: "
                    f"Başvuru='{basvuru_tc}' vs Belge='{doc_tc}'"
                )

    def _check_education_consistency(self, documents: List[Dict]):
        """Diploma ve özgeçmişteki eğitim bilgisi tutarlılığı - DETAYLI CROSS-VALIDATION"""
        diploma_data = None
        ozgecmis_data = None

        for doc in documents:
            doc_type = doc.get("belge_tipi", "")
            if "diploma" in doc_type:
                diploma_data = doc.get("veri", {})
            elif "özgeçmiş" in doc_type or "cv" in doc_type:
                ozgecmis_data = doc.get("veri", {})

        if not diploma_data or not ozgecmis_data:
            return

        diploma_bilgileri = diploma_data.get("diploma_bilgileri", {})
        if not isinstance(diploma_bilgileri, dict):
            return

        ozgecmis_egitim = ozgecmis_data.get("egitim", [])
        if not isinstance(ozgecmis_egitim, list):
            return

        # 1. Üniversite kontrolü
        diploma_uni = diploma_bilgileri.get("universite", "").lower().strip()
        diploma_bolum = diploma_bilgileri.get("bolum", "").lower().strip()
        diploma_yil = diploma_bilgileri.get("mezuniyet_yili", "")

        if diploma_uni and ozgecmis_egitim:
            # Özgeçmişteki eğitimlerde diplomadaki üniversiteyi ara
            uni_found = False
            bolum_found = False
            yil_uyumlu = False

            for egitim in ozgecmis_egitim:
                if not isinstance(egitim, dict):
                    continue

                cv_okul = egitim.get("okul_adi", "").lower().strip()
                cv_bolum = egitim.get("bolum", "").lower().strip()
                cv_yil = str(egitim.get("bitis_yili", "")).strip()

                # Üniversite benzerliği (kısaltmalar için)
                if diploma_uni and cv_okul:
                    similarity = self._calculate_similarity(diploma_uni, cv_okul)
                    if similarity > 0.7:  # %70 benzerlik yeterli
                        uni_found = True

                        # Aynı üniversitede bölüm kontrolü
                        if diploma_bolum and cv_bolum:
                            bolum_similarity = self._calculate_similarity(diploma_bolum, cv_bolum)
                            if bolum_similarity > 0.6:  # %60 benzerlik yeterli
                                bolum_found = True

                        # Mezuniyet yılı kontrolü (±1 yıl tolerans)
                        if diploma_yil and cv_yil:
                            try:
                                diploma_yil_int = int(diploma_yil)
                                cv_yil_int = int(cv_yil)
                                if abs(diploma_yil_int - cv_yil_int) <= 1:
                                    yil_uyumlu = True
                            except (ValueError, TypeError):
                                pass

            # Uyarı mesajları
            if not uni_found:
                self.warnings.append(
                    f"⚠️  Diplomadaki üniversite ('{diploma_bilgileri.get('universite')}') "
                    f"özgeçmişte bulunamadı"
                )

            if uni_found and diploma_bolum and not bolum_found:
                self.warnings.append(
                    f"⚠️  Diplomadaki bölüm ('{diploma_bilgileri.get('bolum')}') "
                    f"özgeçmişte bulunamadı veya eşleşmiyor"
                )

            if uni_found and diploma_yil and not yil_uyumlu:
                self.warnings.append(
                    f"⚠️  Diploma mezuniyet yılı ({diploma_yil}) "
                    f"özgeçmişteki eğitim yıllarıyla uyuşmuyor (±1 yıl tolerans)"
                )

    def _check_experience_consistency(self, documents: List[Dict]):
        """SGK ve özgeçmiş iş deneyimi tutarlılığı - DETAYLI CROSS-VALIDATION"""
        sgk_data = None
        ozgecmis_data = None

        for doc in documents:
            doc_type = doc.get("belge_tipi", "")
            if "sgk" in doc_type:
                sgk_data = doc.get("veri", {})
            elif "özgeçmiş" in doc_type or "cv" in doc_type:
                ozgecmis_data = doc.get("veri", {})

        if not sgk_data or not ozgecmis_data:
            return

        # 1. Toplam süre karşılaştırması
        sgk_toplam = sgk_data.get("toplam_calisma_suresi", {}).get("toplam_gun", 0)
        sgk_yil = sgk_toplam / 365 if sgk_toplam else 0

        ozgecmis_deneyim = ozgecmis_data.get("is_deneyimi", [])
        # Özgeçmişteki toplam süreyi hesapla (gerçek tarihlerden)
        ozgecmis_toplam_gun = 0
        for deneyim in ozgecmis_deneyim:
            if isinstance(deneyim, dict):
                sure_gun = deneyim.get("sure_gun", 0)
                ozgecmis_toplam_gun += sure_gun if sure_gun else 0

        ozgecmis_yil = ozgecmis_toplam_gun / 365 if ozgecmis_toplam_gun else 0

        # Toplam süre farkı (±6 ay tolerans)
        if abs(sgk_yil - ozgecmis_yil) > 0.5:  # 0.5 yıl = 6 ay
            self.warnings.append(
                f"⚠️  Toplam iş deneyimi tutarsızlığı: "
                f"SGK={sgk_yil:.1f} yıl vs Özgeçmiş={ozgecmis_yil:.1f} yıl "
                f"(Fark: {abs(sgk_yil - ozgecmis_yil):.1f} yıl)"
            )

        # 2. Şirket eşleştirmesi
        sgk_calisma_gecmisi = sgk_data.get("calisma_gecmisi", [])

        # SGK'daki şirketler
        sgk_sirketler = []
        for sgk_is in sgk_calisma_gecmisi:
            if isinstance(sgk_is, dict):
                sirket_adi = sgk_is.get("isyeri_adi") or ""
                sirket = sirket_adi.strip().lower() if sirket_adi else ""
                if sirket:
                    sgk_sirketler.append({
                        "sirket": sirket,
                        "giris": sgk_is.get("ise_giris_tarihi"),
                        "cikis": sgk_is.get("isten_cikis_tarihi")
                    })

        # Özgeçmişteki şirketler
        cv_sirketler = []
        for cv_is in ozgecmis_deneyim:
            if isinstance(cv_is, dict):
                sirket_adi = cv_is.get("sirket_adi") or ""
                sirket = sirket_adi.strip().lower() if sirket_adi else ""
                if sirket:
                    cv_sirketler.append({
                        "sirket": sirket,
                        "baslangic": cv_is.get("baslangic_tarihi"),
                        "bitis": cv_is.get("bitis_tarihi")
                    })

        # Şirket sayısı karşılaştırması
        if len(sgk_sirketler) > 0 and len(cv_sirketler) > 0:
            # Her CV şirketinin SGK'da karşılığını ara
            eslesmeyen_cv = []
            for cv_s in cv_sirketler:
                found = False
                for sgk_s in sgk_sirketler:
                    similarity = self._calculate_similarity(cv_s["sirket"], sgk_s["sirket"])
                    if similarity > 0.7:  # %70 benzerlik yeterli
                        found = True
                        break
                if not found:
                    eslesmeyen_cv.append(cv_s["sirket"])

            if eslesmeyen_cv:
                self.warnings.append(
                    f"⚠️  Özgeçmişte olan ama SGK'da bulunmayan şirketler: "
                    f"{', '.join(eslesmeyen_cv[:3])}" +
                    (f" (+{len(eslesmeyen_cv)-3} diğer)" if len(eslesmeyen_cv) > 3 else "")
                )

            # Şirket sayısı çok farklı ise
            if abs(len(sgk_sirketler) - len(cv_sirketler)) > max(len(sgk_sirketler), len(cv_sirketler)) * 0.5:
                self.warnings.append(
                    f"⚠️  Şirket sayısı tutarsızlığı: "
                    f"SGK={len(sgk_sirketler)} şirket vs Özgeçmiş={len(cv_sirketler)} şirket"
                )

    def _check_criminal_record(self, documents: List[Dict]):
        """Adli sicil belgesi kontrolü"""
        for doc in documents:
            doc_type = doc.get("belge_tipi", "")
            if "adli sicil" in doc_type:
                doc_data = doc.get("veri", {})
                belge_bilgileri = doc_data.get("belge_bilgileri", {})

                sabika = belge_bilgileri.get("sabika_kaydi")

                if sabika is True:
                    self.errors.append(
                        "❌ Adli sicil kaydı var! Başvuru uygun değil."
                    )
                elif sabika is None:
                    self.warnings.append(
                        "⚠️  Adli sicil kaydı belirlenemedi"
                    )

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """İki string arasındaki benzerlik oranı (0-1)"""
        return SequenceMatcher(None, str1, str2).ratio()
