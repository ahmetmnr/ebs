"""
CSB eBasvuru API Client
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional
import logging
from app.models.external_api import (
    HizmetModel,
    BasvuruListeModel,
    BasvuruDetayModel,
    BelgeModel,
    BasvuruWithBelgelerModel
)

logger = logging.getLogger(__name__)


class ExternalAPIClient:
    """CSB eBasvuru API Client"""

    def __init__(self, base_url: str, username: str, password: str, timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = self.auth

    def get_hizmet_listesi(self) -> List[Dict]:
        """
        Hizmet listesini çeker

        Returns:
            Hizmet listesi
        """
        try:
            url = f"{self.base_url}/Hizmet/HizmetListesiExternal"
            logger.info(f"Hizmet listesi çekiliyor: {url}")

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            hizmetler = response.json()
            logger.info(f"✅ {len(hizmetler)} hizmet çekildi")

            return hizmetler

        except requests.HTTPError as e:
            logger.error(f"HTTP hatası (hizmet listesi): {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Hizmet listesi hatası: {str(e)}")
            raise

    def get_basvuru_listesi(
        self,
        hizmet_id: str,
        baslangic_tarih: Optional[str] = None,
        bitis_tarih: Optional[str] = None
    ) -> List[Dict]:
        """
        Başvuru listesini çeker

        Args:
            hizmet_id: Hizmet ID (örn: "10256")
            baslangic_tarih: Başlangıç tarihi (YYYY-MM-DD)
            bitis_tarih: Bitiş tarihi (YYYY-MM-DD)

        Returns:
            Başvuru listesi
        """
        try:
            url = f"{self.base_url}//Basvuru/BasvuruListesiExternal"
            payload = {
                "HizmetId": hizmet_id,
                "BasvuruBaslangicTarih": baslangic_tarih,
                "BasvuruBitisTarih": bitis_tarih
            }

            logger.info(f"Başvuru listesi çekiliyor: {url}")
            logger.debug(f"Payload: {payload}")

            # ÖNEMLİ: GET ama JSON body ile!
            response = self.session.request(
                method='GET',
                url=url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            basvurular = response.json()
            logger.info(f"✅ {len(basvurular)} başvuru çekildi")

            return basvurular

        except requests.HTTPError as e:
            logger.error(f"HTTP hatası (başvuru listesi): {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Başvuru listesi hatası: {str(e)}")
            raise

    def get_basvuru_detay(self, takip_no: str) -> Dict:
        """
        Başvuru detayını çeker

        Args:
            takip_no: Başvuru takip numarası

        Returns:
            Başvuru detayları (evrak_kayit_no, tarih, belgeler vs.)
        """
        try:
            url = f"{self.base_url}//Basvuru/BasvuruDetayExternal"
            params = {"takipNo": takip_no}

            logger.info(f"Başvuru detayı çekiliyor: {takip_no}")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            detay = response.json()
            logger.info(f"✅ Başvuru detayı çekildi: {takip_no}")

            return detay

        except requests.HTTPError as e:
            logger.error(f"HTTP hatası (başvuru detay): {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Başvuru detay hatası: {str(e)}")
            raise

    def get_belge(self, takip_no: str, belge_id: str) -> Dict:
        """
        Belge dosyasını base64 formatında çeker

        Args:
            takip_no: Başvuru takip numarası
            belge_id: Belge ID

        Returns:
            {
                "belgeId": "123",
                "belgeTipi": "özgeçmiş",
                "dosyaAdi": "cv.pdf",
                "base64": "JVBERi0x..."
            }
        """
        try:
            url = f"{self.base_url}//Basvuru/BelgeIndirExternal"
            params = {
                "takipNo": takip_no,
                "belgeId": belge_id
            }

            logger.info(f"Belge indiriliyor: {belge_id}")

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            belge = response.json()
            logger.info(f"✅ Belge indirildi: {belge_id}")

            return belge

        except requests.HTTPError as e:
            logger.error(f"HTTP hatası (belge indirme): {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Belge indirme hatası: {str(e)}")
            raise

    def get_basvuru_with_belgeler(self, basvuru_data: Dict) -> Dict:
        """
        Başvuru verisinden belgeleri çıkarır

        NOT: Belgeler zaten başvuru listesinde mevcut!
        basvuruBelgeListesi içinde dosyaByte (base64) var.

        Args:
            basvuru_data: Başvuru listesinden gelen tam veri

        Returns:
            {
                "basvuru_id": "12345",
                "takip_no": "TK-2025-001",
                "basvuru_tarihi": "2025-03-19T15:43:20.677+03:00",
                "basvuru_durum": "İşleme Alındı",
                "hizmet_adi": "...",
                "belgeler": [
                    {
                        "belge_id": "1",
                        "belge_adi": "cv.pdf",
                        "belge_tipi": "özgeçmiş",
                        "dosya_formati": "application/pdf",
                        "base64": "..."
                    }
                ]
            }
        """
        takip_no = basvuru_data.get('takipNo')
        logger.info(f"▶️  Başvuru ve belgeler işleniyor: {takip_no}")

        # Belgeleri çıkar
        belgeler = []
        belge_listesi = basvuru_data.get('basvuruBelgeListesi', [])

        logger.info(f"📄 {len(belge_listesi)} belge bulundu")

        for belge in belge_listesi:
            try:
                base64_data = belge.get('dosyaByte')

                # Base64 verisi yoksa atla
                if not base64_data:
                    logger.warning(f"⚠️  Belge {belge.get('belgeId')} için base64 verisi yok, atlanıyor")
                    continue

                belgeler.append({
                    "belge_id": str(belge.get('belgeId')),
                    "belge_adi": belge.get('belgeAdi'),
                    "belge_tipi": belge.get('belgeTipi'),
                    "dosya_formati": belge.get('dosyaFormati'),
                    "base64": base64_data
                })
            except Exception as e:
                logger.error(f"❌ Belge işleme hatası: {str(e)}")
                continue

        # Birleştir
        result = {
            "basvuru_id": str(basvuru_data.get('basvuruId')),
            "takip_no": takip_no,
            "basvuru_tarihi": basvuru_data.get('basvuruTarihi'),
            "basvuru_durum": basvuru_data.get('basvuruDurum'),
            "hizmet_adi": basvuru_data.get('hizmetAdi'),
            "basvuru_yapan_tc": basvuru_data.get('basvuruYapanVatandasTC'),
            "basvuru_yapan_ad": basvuru_data.get('basvuruYapanAd'),
            "basvuru_yapan_soyad": basvuru_data.get('basvuruYapanSoyad'),
            "belgeler": belgeler
        }

        logger.info(f"✅ Başvuru tamamlandı: {len(belgeler)} belge")

        return result

    def post_degerlendirme_sonucu(self, takip_no: str, sonuc: Dict) -> bool:
        """
        Değerlendirme sonucunu geri gönderir

        Args:
            takip_no: Başvuru takip numarası
            sonuc: Master JSON sonucu

        Returns:
            True if successful
        """
        try:
            url = f"{self.base_url}/Basvuru/DegerlendirmeSonucGonder"
            payload = {
                "takipNo": takip_no,
                "sonuc": sonuc
            }

            logger.info(f"Sonuç gönderiliyor: {takip_no}")

            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            logger.info(f"✅ Sonuç gönderildi: {takip_no}")

            return True

        except requests.HTTPError as e:
            logger.error(f"HTTP hatası (sonuç gönderme): {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Sonuç gönderme hatası: {str(e)}")
            return False
