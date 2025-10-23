"""
Analysis Orchestrator - Gelişmiş Analiz İş Akışı Yöneticisi

PHASE 1 - KRİTİK ÖZELLİKLER:
- Başvuru ön kontrol (zorunlu belgeler, hizmet tipi)
- Belge tipi tahmini (pattern matching)
- Belge tipi sıralaması (Diploma → CV → SGK...)
- Detaylı log kayıtları (chunk + belge)
- Aynı tip belgeleri birleştirme
- Çoklu belge tipi merge + çelişki çözümü
- Kaynak izleme
- Final sonuç kaydetme
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from models.database import db
from models import Basvuru, Belge
from analyzers import CVAnalyzer, DiplomaAnalyzer, SGKAnalyzer, AdliSicilAnalyzer, ProjeAnalyzer
from analyzers.sektor_belge_analyzer import SektorBelgeAnalyzer
from services.ust_yazi_parser import UstYaziParser
from services.cross_validator import CrossValidator
from services.document_processor import DocumentProcessor
from services.document_validator import DocumentValidator

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """Gelişmiş analiz orkestrasyon servisi"""

    # Belge tipi öncelik sıralaması (Diploma en güvenilir)
    BELGE_TIPI_ONCELIK = {
        'Diploma': 1,
        'CV': 2,
        'Özgeçmiş': 2,
        'SGK': 3,
        'Hitap': 4,
        'Adli Sicil': 5,
        'Proje': 6,
        'Enerji': 7,
        'Metal': 7,
        'Mineral': 7,
        'Kimya': 7,
        'Atık': 7,
        'Diğer': 8
    }

    # Çelişki çözüm stratejileri
    CONFLICT_STRATEGIES = {
        'mezuniyet_yili': 'diploma_priority',  # Diploma > CV > SGK
        'mezun_universite': 'diploma_priority',
        'mezun_bolum': 'diploma_priority',
        'tecrube_enerji': 'max',  # En yüksek değer
        'tecrube_metal': 'max',
        'tecrube_mineral': 'max',
        'tecrube_kimya': 'max',
        'tecrube_atik': 'max',
        'toplam_is_deneyimi_yil': 'max',
        'toplam_is_deneyimi_ay': 'max',
        'adli_sicil_varmi': 'or',  # Varsa VAR
        'yeşil_donusum_tecrubesi': 'or',
        'cevre_mevzuati_bilgisi': 'or',
    }

    def __init__(self, basvuru_id: int):
        """
        Args:
            basvuru_id: Başvuru ID
        """
        self.basvuru_id = basvuru_id
        self.basvuru = None
        self.hizmet_tipi = None
        self.zorunlu_belgeler = []
        self.belgeler = []
        self.belge_analizleri = {}  # {belge_tipi: [sonuç1, sonuç2, ...]}
        self.celiski_notlari = {}
        self.kaynak_bilgileri = {}
        self.start_time = time.time()
        # Cross-validation
        self.ground_truth = None  # Üst yazıdan gelen bilgiler
        self.validator = None  # CrossValidator instance
        self.validation_report = None

    # ========== 0. BAŞVURU ÖN KONTROL ==========

    def load_basvuru(self) -> bool:
        """0.1. Başvuruyu yükle"""
        query = "SELECT * FROM basvurular WHERE basvuruId = ?"
        self.basvuru = db.fetchone(query, (self.basvuru_id,))

        if not self.basvuru:
            logger.error(f"Başvuru bulunamadı: {self.basvuru_id}")
            return False

        logger.info(f"Başvuru yüklendi: {self.basvuru['takipNo']}")
        return True

    def determine_hizmet_tipi(self) -> str:
        """0.2. Hizmet tipini belirle"""
        hizmet_id = self.basvuru.get('hizmetId', '')
        hizmet_adi = self.basvuru.get('hizmetAdi', '')

        # Hizmet tipini belirle
        if 'Akademisyen' in hizmet_adi or 'Öğretim Üyesi' in hizmet_adi:
            self.hizmet_tipi = 'Akademisyen'
        elif 'Bakanlık' in hizmet_adi or 'Kamu' in hizmet_adi:
            self.hizmet_tipi = 'Eski Bakanlık'
        elif 'Sektör' in hizmet_adi or 'Özel Sektör' in hizmet_adi:
            self.hizmet_tipi = 'Sektör Çalışanı'
        else:
            self.hizmet_tipi = 'Diğer'

        # Sorumlu mu, Baş Sorumlu mu?
        if 'Baş Sorumlu' in hizmet_adi or 'Başsorumlu' in hizmet_adi:
            self.hizmet_tipi += ' - Baş Sorumlu'
        elif 'Sorumlu' in hizmet_adi:
            self.hizmet_tipi += ' - Sorumlu'

        logger.info(f"Hizmet tipi belirlendi: {self.hizmet_tipi}")
        return self.hizmet_tipi

    def load_zorunlu_belgeler(self) -> List[str]:
        """0.3. Zorunlu belge listesini al"""
        hizmet_id = self.basvuru.get('hizmetId', '10307')

        query = """
            SELECT belgeTipi, zorunlu, aciklama
            FROM zorunlu_belgeler
            WHERE hizmetId = ? AND zorunlu = 1
        """

        rows = db.fetchall(query, (hizmet_id,))
        self.zorunlu_belgeler = [r['belgeTipi'] for r in rows]

        logger.info(f"Zorunlu belgeler yüklendi: {len(self.zorunlu_belgeler)} adet")
        return self.zorunlu_belgeler

    def mark_processing_started(self):
        """0.5. Başvuru işleme alındı işaretle"""
        query = """
            UPDATE basvurular
            SET islenme_baslangic = ?,
                basvuruDurum = 'İşleniyor'
            WHERE basvuruId = ?
        """
        db.execute(query, (datetime.now().isoformat(), self.basvuru_id))
        logger.info(f"Başvuru işleme başladı: {self.basvuru['takipNo']}")

    # ========== 2. BELGE TİPİ TAHMİNİ ==========

    def estimate_belge_tipi(self, belge: Dict) -> str:
        """2.5. Belge tipi tahmini yap"""
        belge_id = belge['belgeId']
        dosya_adi = belge.get('belgeAdi', '')
        mevcut_tip = belge.get('belgeTipi') or belge.get('belgeTipi_tahmini')

        # 1. Öncelik: JSON'dan gelen belgeTipi
        if mevcut_tip:
            return mevcut_tip

        # 2. belgeTipi null ise → ÜST YAZI'dır!
        logger.info(f"belgeTipi null, Üst Yazı olarak işaretleniyor: {dosya_adi}")

        # belgeTipi_tahmini'ni güncelle
        update_query = "UPDATE belgeler SET belgeTipi_tahmini = ? WHERE belgeId = ?"
        db.execute(update_query, ("Üst Yazı", belge_id))

        return "Üst Yazı"

    def load_and_estimate_belgeler(self) -> List[Dict]:
        """Belgeleri yükle ve tip tahmini yap"""
        self.belgeler = Belge.get_by_basvuru_id(self.basvuru_id)

        for belge in self.belgeler:
            belge_tipi = self.estimate_belge_tipi(belge)
            belge['belgeTipi_final'] = belge_tipi

        logger.info(f"{len(self.belgeler)} belge yüklendi ve tip tahmini yapıldı")
        return self.belgeler

    def check_belge_uyumluluk(self) -> Tuple[bool, List[str]]:
        """2.6. Belge uyumluluk kontrolü"""
        mevcut_tipler = set([b['belgeTipi_final'] for b in self.belgeler])
        eksik_belgeler = []

        for zorunlu_tip in self.zorunlu_belgeler:
            # Kısmi eşleşme kontrolü (örn: "Diploma" in "Yök Lisans Diploması")
            found = any(zorunlu_tip in tip for tip in mevcut_tipler)
            if not found:
                eksik_belgeler.append(zorunlu_tip)

        zorunlu_belgeler_tam = len(eksik_belgeler) == 0

        if eksik_belgeler:
            logger.warning(f"Eksik zorunlu belgeler: {eksik_belgeler}")
        else:
            logger.info("Tüm zorunlu belgeler mevcut")

        return zorunlu_belgeler_tam, eksik_belgeler

    # ========== 3. BELGE ANALİZİ ==========

    def sort_belgeler_by_priority(self) -> List[Dict]:
        """3.0. Belgeleri öncelik sırasına göre sırala"""
        def get_priority(belge):
            belge_tipi = belge['belgeTipi_final']

            # Öncelik tablosundan bul
            for key, priority in self.BELGE_TIPI_ONCELIK.items():
                if key in belge_tipi:
                    return priority

            return 99  # Bilinmeyen tipler en sona

        sorted_belgeler = sorted(self.belgeler, key=get_priority)

        logger.info("Belgeler öncelik sırasına göre sıralandı:")
        for b in sorted_belgeler:
            logger.info(f"  - {b['belgeTipi_final']}")

        return sorted_belgeler

    def get_analyzer(self, belge_tipi: str):
        """Belge tipine göre analyzer seç"""
        if 'Özgeçmiş' in belge_tipi or 'CV' in belge_tipi:
            return CVAnalyzer()

        elif 'Diploma' in belge_tipi:
            return DiplomaAnalyzer()

        elif 'SGK' in belge_tipi or 'Hitap' in belge_tipi:
            return SGKAnalyzer()

        elif 'Adli Sicil' in belge_tipi:
            return AdliSicilAnalyzer()

        elif 'Proje' in belge_tipi:
            return ProjeAnalyzer()

        elif any(sektor in belge_tipi for sektor in ['Enerji', 'Metal', 'Mineral', 'Kimya', 'Atık', 'Diğer', 'Üretim']):
            sektor_adi = "Diğer"
            if 'Enerji' in belge_tipi:
                sektor_adi = "Enerji"
            elif 'Metal' in belge_tipi:
                sektor_adi = "Metal"
            elif 'Mineral' in belge_tipi:
                sektor_adi = "Mineral"
            elif 'Kimya' in belge_tipi:
                sektor_adi = "Kimya"
            elif 'Atık' in belge_tipi:
                sektor_adi = "Atık"
            return SektorBelgeAnalyzer(sektor=sektor_adi)

        return None

    def analyze_all_belgeler(self):
        """Tüm belgeleri analiz et"""
        sorted_belgeler = self.sort_belgeler_by_priority()

        # ÖNCE: Üst yazıyı parse et (ground truth için)
        for belge in sorted_belgeler:
            belge_tipi = belge['belgeTipi_final']
            if any(ust_yazi in belge_tipi for ust_yazi in ['Üst Yazı', 'ustYazi']):
                logger.info(f"Üst yazı parse ediliyor (ground truth kaynağı)...")
                self._parse_ust_yazi(belge)
                break

        # SONRA: Diğer belgeleri analiz et
        for belge in sorted_belgeler:
            belge_tipi = belge['belgeTipi_final']
            belge_id = belge['belgeId']

            # Fotoğraf - varlık kontrolü yap
            if any(skip in belge_tipi for skip in ['Fotoğraf', 'vesikalık']):
                logger.info(f"Fotoğraf belgesi - varlık kontrolü yapılıyor: {belge_tipi}")
                self._validate_photo(belge)
                continue

            if any(skip in belge_tipi for skip in ['Üst Yazı', 'ustYazi']):
                logger.info(f"Üst yazı zaten parse edildi, atlanıyor")
                continue

            # Analyzer seç
            analyzer = self.get_analyzer(belge_tipi)

            if not analyzer:
                logger.warning(f"Analyzer bulunamadı: {belge_tipi}")
                continue

            # Analiz et
            logger.info(f"Analiz ediliyor: {belge_tipi} (belgeId={belge_id})")
            result = analyzer.analyze(belge_id)

            if result:
                # Cross-validate (eğer validator varsa)
                self._validate_analysis_result(belge_tipi, result)

                # Sonucu kaydet
                if belge_tipi not in self.belge_analizleri:
                    self.belge_analizleri[belge_tipi] = []

                self.belge_analizleri[belge_tipi].append({
                    'belgeId': belge_id,
                    'result': result,
                    'kaynak': belge_tipi
                })

                logger.info(f"✓ Analiz başarılı: {belge_tipi}")
            else:
                logger.error(f"✗ Analiz başarısız: {belge_tipi}")

        # SONUNDA: Validation raporunu tamamla
        self._finalize_validation()

    # ========== 4. SONUÇLARI BİRLEŞTİR ==========

    def merge_same_type_results(self, belge_tipi: str, results: List[Dict]) -> Dict:
        """3.10. Aynı tipteki belgeleri birleştir"""
        if len(results) == 1:
            return results[0]['result']

        logger.info(f"Aynı tip belgeler birleştiriliyor: {belge_tipi} ({len(results)} adet)")

        merged = {}

        # Her alan için birleştirme stratejisi uygula
        all_keys = set()
        for r in results:
            all_keys.update(r['result'].keys())

        for key in all_keys:
            values = [(r['result'].get(key), r['belgeId']) for r in results if key in r['result']]

            if not values:
                continue

            # Strateji uygula
            if key in self.CONFLICT_STRATEGIES:
                strategy = self.CONFLICT_STRATEGIES[key]

                if strategy == 'max':
                    # En yüksek sayısal değer
                    numeric_values = [(v, bid) for v, bid in values if isinstance(v, (int, float))]
                    if numeric_values:
                        max_val, max_bid = max(numeric_values, key=lambda x: x[0])
                        merged[key] = max_val
                        self.kaynak_bilgileri[key] = {'belgeId': max_bid, 'kaynak': belge_tipi, 'strategi': 'max'}

                elif strategy == 'or':
                    # Boolean OR (True öncelikli)
                    bool_values = [v for v, _ in values if isinstance(v, bool)]
                    if bool_values:
                        merged[key] = any(bool_values)
                        true_sources = [bid for v, bid in values if v is True]
                        self.kaynak_bilgileri[key] = {
                            'belgeIds': true_sources,
                            'kaynak': belge_tipi,
                            'strategi': 'or'
                        }

            else:
                # Default: İlk NULL olmayan değer
                for val, bid in values:
                    if val is not None and val != '':
                        merged[key] = val
                        self.kaynak_bilgileri[key] = {'belgeId': bid, 'kaynak': belge_tipi, 'strategi': 'first'}
                        break

        return merged

    def merge_all_belge_types(self) -> Dict:
        """4.1. Tüm belge tiplerini birleştir"""
        # Önce her belge tipini kendi içinde birleştir
        type_merged = {}

        for belge_tipi, results in self.belge_analizleri.items():
            type_merged[belge_tipi] = self.merge_same_type_results(belge_tipi, results)

        # Şimdi tüm tipleri birleştir
        final_result = {}

        all_keys = set()
        for merged in type_merged.values():
            all_keys.update(merged.keys())

        for key in all_keys:
            # Tüm kaynaklardan değerleri topla
            values_by_type = {}
            for belge_tipi, merged in type_merged.items():
                if key in merged:
                    values_by_type[belge_tipi] = merged[key]

            if not values_by_type:
                continue

            # Çelişki kontrolü
            unique_values = set([str(v) for v in values_by_type.values()])

            if len(unique_values) > 1:
                # ÇELİŞKİ VAR!
                self.celiski_notlari[key] = {
                    'values': values_by_type,
                    'strategi': self.CONFLICT_STRATEGIES.get(key, 'diploma_priority')
                }

                logger.warning(f"Çelişki tespit edildi: {key} = {values_by_type}")

            # Strateji uygula
            if key in self.CONFLICT_STRATEGIES:
                strategy = self.CONFLICT_STRATEGIES[key]

                if strategy == 'diploma_priority':
                    # Diploma > CV > SGK önceliği
                    for priority_type in ['Diploma', 'CV', 'Özgeçmiş', 'SGK', 'Hitap']:
                        for belge_tipi, value in values_by_type.items():
                            if priority_type in belge_tipi:
                                final_result[key] = value
                                self.kaynak_bilgileri[key] = {
                                    'kaynak': belge_tipi,
                                    'strategi': 'diploma_priority',
                                    'alternatifler': values_by_type
                                }
                                break
                        if key in final_result:
                            break

                elif strategy == 'max':
                    numeric_values = [(v, bt) for bt, v in values_by_type.items() if isinstance(v, (int, float))]
                    if numeric_values:
                        max_val, max_type = max(numeric_values, key=lambda x: x[0])
                        final_result[key] = max_val
                        self.kaynak_bilgileri[key] = {
                            'kaynak': max_type,
                            'strategi': 'max',
                            'alternatifler': values_by_type
                        }

                elif strategy == 'or':
                    final_result[key] = any([v for v in values_by_type.values() if isinstance(v, bool)])
                    true_sources = [bt for bt, v in values_by_type.items() if v is True]
                    self.kaynak_bilgileri[key] = {
                        'kaynaklar': true_sources,
                        'strategi': 'or'
                    }

            else:
                # Default: İlk değer
                first_type = list(values_by_type.keys())[0]
                final_result[key] = values_by_type[first_type]
                self.kaynak_bilgileri[key] = {'kaynak': first_type, 'strategi': 'first'}

        # ===== POST-PROCESSING: VALIDATION & NORMALIZATION =====

        # 1. Ay normalizasyonu (ay >= 12 ise yıla çevir)
        if final_result.get('toplam_is_deneyimi_ay', 0) and final_result['toplam_is_deneyimi_ay'] >= 12:
            extra_years = final_result['toplam_is_deneyimi_ay'] // 12
            final_result['toplam_is_deneyimi_yil'] = final_result.get('toplam_is_deneyimi_yil', 0) + extra_years
            final_result['toplam_is_deneyimi_ay'] = final_result['toplam_is_deneyimi_ay'] % 12
            logger.info(f"✓ Ay değeri normalize edildi: +{extra_years} yıl -> {final_result['toplam_is_deneyimi_yil']}y {final_result['toplam_is_deneyimi_ay']}a")

        # 2. Mantıksız değerleri temizle
        VALIDATION_RULES = {
            'mezuniyet_yili': (1950, 2030, 'Diploma'),
            'dogum_yili': (1930, 2015, None),
            'toplam_is_deneyimi_yil': (0, 50, 'SGK'),
        }

        for field, (min_val, max_val, preferred_source) in VALIDATION_RULES.items():
            if field in final_result and final_result[field] is not None:
                value = final_result[field]
                if value < min_val or value > max_val:
                    logger.warning(f"⚠️ Mantıksız değer tespit edildi: {field}={value} (beklenen: {min_val}-{max_val})")

                    # Eğer preferred source varsa ondan al
                    if preferred_source:
                        for belge_tipi, merged in type_merged.items():
                            if preferred_source in belge_tipi and field in merged:
                                fallback_value = merged[field]
                                if fallback_value and min_val <= fallback_value <= max_val:
                                    logger.info(f"✓ {preferred_source}'dan düzeltildi: {field}={fallback_value}")
                                    final_result[field] = fallback_value
                                    break
                        else:
                            # Preferred source'ta da yok veya geçersiz, null yap
                            logger.warning(f"✗ Düzeltilemedi, null yapıldı: {field}")
                            final_result[field] = None
                    else:
                        final_result[field] = None

        # 3. "Belirsiz" değerlerini temizle
        for field, value in list(final_result.items()):
            if isinstance(value, str) and value.lower() in ['belirsiz', 'bilinmiyor', 'yok', 'n/a']:
                logger.debug(f"'Belirsiz' değer temizlendi: {field}='{value}' -> None")
                final_result[field] = None

        # 4. TC Kimlik No validation ve düzeltme
        if 'tc_kimlik_no' in final_result and final_result['tc_kimlik_no']:
            tc = str(final_result['tc_kimlik_no']).strip()

            # TC 11 hane olmalı
            if len(tc) == 10:
                # 10 hane ise, ground truth'tan ilk rakamı al
                if self.ground_truth and self.ground_truth.get('tc_kimlik_no'):
                    correct_tc = str(self.ground_truth['tc_kimlik_no']).strip()
                    if len(correct_tc) == 11 and correct_tc.endswith(tc):
                        logger.info(f"✓ TC kimlik düzeltildi: {tc} -> {correct_tc}")
                        final_result['tc_kimlik_no'] = correct_tc
                    else:
                        logger.warning(f"⚠️ TC 10 hane ama ground truth ile uyuşmuyor: {tc} vs {correct_tc}")
                else:
                    logger.warning(f"⚠️ TC 10 hane ({tc}) ama ground truth yok, düzeltilemedi")
            elif len(tc) != 11:
                logger.warning(f"⚠️ TC geçersiz uzunluk ({len(tc)} hane): {tc}")
                final_result['tc_kimlik_no'] = None

        return final_result

    # ========== 5. VERİTABANINA KAYDET ==========

    def save_to_database(self, final_result: Dict, zorunlu_belgeler_tam: bool, eksik_belgeler: List[str]):
        """5. Final sonuçları veritabanına kaydet"""

        # Kaynak bayraqları
        kaynak_cv = 1 if 'CV' in self.belge_analizleri or 'Özgeçmiş' in self.belge_analizleri else 0
        kaynak_sgk = 1 if 'SGK' in self.belge_analizleri or 'Hitap' in self.belge_analizleri else 0
        kaynak_diploma = 1 if 'Diploma' in self.belge_analizleri else 0
        kaynak_adli_sicil = 1 if 'Adli Sicil' in self.belge_analizleri else 0
        kaynak_proje = 1 if 'Proje' in self.belge_analizleri else 0
        kaynak_sektor = 1 if any('Enerji' in k or 'Metal' in k or 'Mineral' in k or 'Kimya' in k or 'Atık' in k for k in self.belge_analizleri.keys()) else 0

        # Proje sayısı
        proje_yayin_sayisi = len(final_result.get('projeler', [])) if 'projeler' in final_result else 0

        # analiz_sonuclari tablosuna INSERT/UPDATE
        query = """
            INSERT OR REPLACE INTO analiz_sonuclari (
                basvuruId,
                ad_soyad, tc_kimlik_no, dogum_tarihi, dogum_yeri,
                mezun_universite, mezun_bolum, mezuniyet_yili, egitim_seviyesi,
                toplam_is_deneyimi_yil, toplam_is_deneyimi_ay,
                tecrube_enerji, tecrube_metal, tecrube_mineral, tecrube_kimya, tecrube_atik,
                adli_sicil_varmi, yeşil_donusum_tecrubesi, cevre_mevzuati_bilgisi,
                proje_yayin_sayisi,
                zorunlu_belgeler_tam, eksik_belgeler,
                kaynak_cv, kaynak_sgk, kaynak_diploma, kaynak_adli_sicil, kaynak_proje_dosyasi, kaynak_sektor_belgeleri,
                kaynak_detay, celiski_notlari,
                analiz_tarihi, analiz_suresi_sn
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """

        params = (
            self.basvuru_id,
            final_result.get('ad_soyad'),
            final_result.get('tc_kimlik_no'),
            final_result.get('dogum_tarihi'),
            final_result.get('dogum_yeri'),
            final_result.get('mezun_universite'),
            final_result.get('mezun_bolum'),
            final_result.get('mezuniyet_yili'),
            final_result.get('egitim_seviyesi'),
            final_result.get('toplam_is_deneyimi_yil', 0),
            final_result.get('toplam_is_deneyimi_ay', 0),
            final_result.get('tecrube_enerji', 0),
            final_result.get('tecrube_metal', 0),
            final_result.get('tecrube_mineral', 0),
            final_result.get('tecrube_kimya', 0),
            final_result.get('tecrube_atik', 0),
            final_result.get('adli_sicil_varmi', 0),
            final_result.get('yeşil_donusum_tecrubesi', 0),
            final_result.get('cevre_mevzuati_bilgisi', 0),
            proje_yayin_sayisi,
            1 if zorunlu_belgeler_tam else 0,
            json.dumps(eksik_belgeler, ensure_ascii=False),
            kaynak_cv, kaynak_sgk, kaynak_diploma, kaynak_adli_sicil, kaynak_proje, kaynak_sektor,
            json.dumps(self.kaynak_bilgileri, ensure_ascii=False),
            json.dumps(self.celiski_notlari, ensure_ascii=False),
            datetime.now().isoformat(),
            time.time() - self.start_time
        )

        db.execute(query, params)
        logger.info("analiz_sonuclari tablosuna kaydedildi")

        # Proje/yayınları ayrı tabloya kaydet
        if 'projeler' in final_result and final_result['projeler']:
            self.save_projeler(final_result['projeler'])

    def save_projeler(self, projeler: List[Dict]):
        """4.3. Proje bilgilerini ayrı tabloya kaydet"""
        query = """
            INSERT INTO proje_yayinlar (
                basvuruId, sira_no, tur, baslik, aciklama, yil, kurum, butce, rol, kaynak_belgeId
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for i, proje in enumerate(projeler, 1):
            params = (
                self.basvuru_id,
                i,
                proje.get('tur'),
                proje.get('baslik'),
                proje.get('aciklama'),
                proje.get('yil'),
                proje.get('kurum'),
                proje.get('butce'),
                proje.get('rol'),
                proje.get('kaynak_belgeId')
            )
            db.execute(query, params)

        logger.info(f"{len(projeler)} proje kaydedildi")

    def mark_processing_completed(self, success: bool = True, error_msg: str = None):
        """5.5. Başvuru durumu güncelle"""
        query = """
            UPDATE basvurular
            SET islendiMi = ?,
                islenme_bitis = ?,
                islenme_suresi_sn = ?,
                basvuruDurum = ?,
                hata_mesaji = ?
            WHERE basvuruId = ?
        """

        duration = time.time() - self.start_time
        status = 'İşleme Tamamlandı' if success else 'İşlem Hatası'

        params = (
            1 if success else 0,
            datetime.now().isoformat(),
            duration,
            status,
            error_msg,
            self.basvuru_id
        )

        db.execute(query, params)
        logger.info(f"Başvuru durumu güncellendi: {status} ({duration:.2f}s)")

    # ========== ANA İŞ AKIŞI ==========

    def run(self) -> bool:
        """Ana iş akışını çalıştır"""
        try:
            # 0. BAŞVURU ÖN KONTROL
            logger.info("=" * 60)
            logger.info("BAŞVURU ANALİZ SÜRECİ BAŞLIYOR")
            logger.info("=" * 60)

            if not self.load_basvuru():
                return False

            self.determine_hizmet_tipi()
            self.load_zorunlu_belgeler()
            self.mark_processing_started()

            # 2. BELGE TİPİ TAHMİNİ
            self.load_and_estimate_belgeler()
            zorunlu_belgeler_tam, eksik_belgeler = self.check_belge_uyumluluk()

            # 3. BELGE ANALİZİ
            self.analyze_all_belgeler()

            # 4. SONUÇLARI BİRLEŞTİR
            final_result = self.merge_all_belge_types()

            # 5. VERİTABANINA KAYDET
            self.save_to_database(final_result, zorunlu_belgeler_tam, eksik_belgeler)

            # 6. BAŞARIYLA TAMAMLA
            self.mark_processing_completed(success=True)

            logger.info("=" * 60)
            logger.info("BAŞVURU ANALİZ SÜRECİ TAMAMLANDI")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"Analiz hatası: {e}", exc_info=True)
            self.mark_processing_completed(success=False, error_msg=str(e))
            return False

    # ========== CROSS-VALIDATION MET ODLARI ==========

    def _parse_ust_yazi(self, belge: Dict):
        """
        Üst yazıyı parse et ve ground truth bilgilerini çıkar.
        """
        try:
            belge_id = belge['belgeId']

            # PDF'den metin çıkar
            belge_row = Belge.get_by_id(belge_id)
            if not belge_row or not belge_row.get('belgeIcerik'):
                logger.warning("Üst yazı belgesi içeriği boş")
                return

            import base64
            pdf_bytes = base64.b64decode(belge_row['belgeIcerik'])

            # Metin çıkar
            text = DocumentProcessor.extract_text_from_pdf(pdf_bytes, use_ocr=False)

            if not text or len(text) < 100:
                logger.warning(f"Üst yazı metni çok kısa: {len(text) if text else 0} karakter")
                return

            # Parse et
            parser = UstYaziParser()
            self.ground_truth = parser.parse_ust_yazi(text)

            if self.ground_truth and self.ground_truth.get('ad_soyad'):
                logger.info(f"✓ Ground truth yüklendi: {self.ground_truth['ad_soyad']} ({self.ground_truth.get('tc_kimlik_no', 'TC yok')})")
                logger.info(f"✓ Belge listesi: {self.ground_truth.get('toplam_belge_sayisi', 0)} belge bekleniyor")

                # Cross-validator başlat
                self.validator = CrossValidator(self.ground_truth)

                # Belge listesi kontrolü
                actual_files = [b.get('belgeAdi', '') for b in self.belgeler if b.get('belgeAdi')]
                doc_list_check = self.validator.validate_document_list(actual_files)

                logger.info(f"Belge listesi kontrolü: {doc_list_check['expected_count']} beklenen, {doc_list_check['actual_count']} mevcut")

            else:
                logger.warning("Üst yazı parse edildi ama bilgi çıkarılamadı")

        except Exception as e:
            logger.error(f"Üst yazı parse hatası: {e}", exc_info=True)
            self.ground_truth = None
            self.validator = None

    def _validate_analysis_result(self, belge_tipi: str, result: Dict):
        """
        Analiz sonucunu cross-validate et.
        """
        if not self.validator or not result:
            return

        # TC Kimlik No (kritik)
        if 'tc_kimlik_no' in result and result['tc_kimlik_no']:
            self.validator.validate_field(
                'tc_kimlik_no',
                result['tc_kimlik_no'],
                belge_tipi,
                severity='CRITICAL'
            )

        # Ad Soyad (uyarı - evlilik sonrası değişebilir)
        if 'ad_soyad' in result and result['ad_soyad']:
            self.validator.validate_field(
                'ad_soyad',
                result['ad_soyad'],
                belge_tipi,
                severity='WARNING'
            )

        # Email
        if 'iletisim_email' in result and result['iletisim_email']:
            self.validator.validate_field(
                'email',
                result['iletisim_email'],
                belge_tipi,
                ground_truth_key='email',
                severity='WARNING'
            )

        # GSM
        if 'gsm' in result and result['gsm']:
            self.validator.validate_field(
                'gsm',
                result['gsm'],
                belge_tipi,
                severity='WARNING'
            )

    def _finalize_validation(self):
        """
        Cross-validation raporunu tamamla ve logla.
        """
        if not self.validator:
            return

        self.validation_report = self.validator.get_validation_report()

        if self.validation_report['status'] == 'FAIL':
            logger.error(f"🔴 DOĞRULAMA BAŞARISIZ!")
            logger.error(f"   {self.validation_report['total_errors']} kritik hata")
            logger.error(f"   {self.validation_report['total_warnings']} uyarı")

            for error in self.validation_report['errors']:
                logger.error(f"   - {error}")

        else:
            logger.info(f"✓ Doğrulama başarılı!")
            if self.validation_report['total_warnings'] > 0:
                logger.info(f"   {self.validation_report['total_warnings']} uyarı")

        logger.info(f"   Özet: {self.validation_report['summary']}")

    def _validate_photo(self, belge: Dict):
        """
        Fotoğraf varlık kontrolü (LLM analizi YOK).
        """
        try:
            belge_id = belge['belgeId']
            belge_adi = belge.get('belgeAdi', 'unknown.jpg')

            validator = DocumentValidator()

            # Belge içeriğini al
            belge_row = Belge.get_by_id(belge_id)
            if not belge_row or not belge_row.get('belgeIcerik'):
                logger.error(f"Fotoğraf içeriği bulunamadı: {belge_id}")
                return

            import base64
            photo_bytes = base64.b64decode(belge_row['belgeIcerik'])

            # Validate et
            result = validator.validate_photo(photo_bytes, belge_adi)

            if result['valid']:
                logger.info(f"✓ Fotoğraf geçerli: {belge_adi} ({result['size_kb']:.1f} KB, {result['mime_type']})")

                # Veritabanına kaydet (analiz edildi olarak işaretle)
                update_query = """
                    UPDATE belgeler
                    SET analiz_edildi = 1,
                        analiz_notu = ?
                    WHERE belgeId = ?
                """
                db.execute(update_query, (
                    f"Fotograf mevcut - {result['mime_type']} - {result['size_kb']:.1f} KB",
                    belge_id
                ))

            else:
                logger.error(f"✗ Fotoğraf geçersiz: {', '.join(result['errors'])}")

                # Hata olarak kaydet
                update_query = """
                    UPDATE belgeler
                    SET analiz_edildi = 1,
                        analiz_notu = ?
                    WHERE belgeId = ?
                """
                db.execute(update_query, (
                    f"Gecersiz fotograf: {', '.join(result['errors'])}",
                    belge_id
                ))

        except Exception as e:
            logger.error(f"Fotoğraf validation hatası: {e}", exc_info=True)
