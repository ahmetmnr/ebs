"""
Base analyzer sınıfı.
Tüm analyzer'ların türetileceği base class.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime

from services.ollama_service import OllamaService
from services.document_processor import DocumentProcessor
from services.chunk_manager import ChunkManager
from models import Belge
from models.database import db

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """Base analyzer sınıfı"""

    def __init__(self):
        """Initialize"""
        self.ollama = OllamaService()
        self.doc_processor = DocumentProcessor()
        self.chunk_manager = ChunkManager()

    @abstractmethod
    def get_prompt_template(self) -> str:
        """
        Analyzer için prompt template'i döndür.

        Returns:
            str: Prompt template
        """
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        """
        Belge tipini döndür.

        Returns:
            str: Belge tipi
        """
        pass

    def analyze(self, belge_id: int) -> Optional[Dict[str, Any]]:
        """
        Belgeyi analiz et.

        Args:
            belge_id: Belge ID

        Returns:
            Dict: Analiz sonucu, başarısızsa None
        """
        try:
            # Belgeyi al
            belge = Belge.get_by_id(belge_id)
            if not belge:
                logger.error(f"Belge bulunamadı: {belge_id}")
                return None

            # PHASE 2.1: Belge Format Kontrolü
            format_check = self._check_document_format(belge)
            if not format_check['valid']:
                logger.warning(f"Belge format kontrolü başarısız: {format_check['error']}")
                Belge.mark_as_analyzed(belge_id, False, format_check['error'])
                return None

            # İşleme başla
            start_time = datetime.now()
            Belge.mark_as_analyzing(belge_id)

            # Belgeyi işle (PDF veya görsel)
            processed = self.doc_processor.process_document(
                belge['belgeIcerik'],
                belge.get('belge_uzantisi')
            )

            if not processed['success']:
                logger.error(f"Belge işleme başarısız: {processed.get('error')}")
                Belge.mark_as_analyzed(belge_id, False, processed.get('error'))
                return None

            # PHASE 2.2: OCR Kalite Kontrolü
            if processed.get('text'):
                ocr_quality = self._check_ocr_quality(processed['text'])
                if not ocr_quality['acceptable']:
                    logger.warning(f"OCR kalitesi düşük: {ocr_quality['reason']}")

            # Metin varsa chunk'lara böl
            if processed.get('text'):
                result = self._analyze_text(processed['text'], belge_id)

            # Görsel varsa vision ile analiz et
            elif processed.get('image_base64'):
                result = self._analyze_image(processed['image_base64'], belge_id)

            else:
                logger.error("Ne metin ne görsel bulunamadı")
                Belge.mark_as_analyzed(belge_id, False, "Veri bulunamadı")
                return None

            # PHASE 2.6: Sonuç Validasyonu
            if result:
                validation = self._validate_result(result)
                if not validation['valid']:
                    logger.warning(f"Sonuç validasyonu uyarıları: {validation['warnings']}")
                    result['_validation_warnings'] = validation['warnings']

            # İşlem bitti
            Belge.mark_as_analyzed(belge_id, True)

            # Log kaydet
            self._save_analysis_log(belge_id, belge['basvuruId'], start_time, result, True)

            return result

        except Exception as e:
            logger.error(f"Analiz hatası: {e}")
            Belge.mark_as_analyzed(belge_id, False, str(e))
            return None

    def _analyze_text(self, text: str, belge_id: int) -> Optional[Dict[str, Any]]:
        """
        Metin analizi (chunk'larla).

        Args:
            text: Belge metni
            belge_id: Belge ID

        Returns:
            Dict: Analiz sonucu
        """
        # Chunk'lara böl
        chunks = self.chunk_manager.create_chunks(text)

        logger.info(f"Belge {belge_id}: {len(chunks)} chunk oluşturuldu")

        chunk_results = []
        chunk_data_for_db = []  # DB'ye kaydetmek için

        # Her chunk'ı analiz et
        for i, chunk in enumerate(chunks):
            chunk_result = self.ollama.analyze_document(
                document_text=chunk.text,
                document_type=self.get_document_type(),
                prompt_template=self.get_prompt_template()
            )

            # VALIDATION: chunk_result yapısını kontrol et
            if not chunk_result:
                logger.warning(f"Chunk {i} için sonuç None")
                continue

            if not isinstance(chunk_result, dict):
                logger.error(f"Chunk {i} için geçersiz sonuç tipi: {type(chunk_result)}")
                continue

            if not chunk_result.get('success'):
                logger.warning(f"Chunk {i} analizi başarısız")
                continue

            if 'data' not in chunk_result:
                logger.error(f"Chunk {i} sonucunda 'data' alanı yok: {chunk_result.keys()}")
                continue

            # Data'nın kendisi de dict olmalı
            if not isinstance(chunk_result['data'], dict):
                logger.error(f"Chunk {i} 'data' alanı dict değil: {type(chunk_result['data'])}")
                continue

            # Geçerli sonuç, ekle
            chunk_results.append(chunk_result['data'])

            # Chunk sonucunu kaydetmek için sakla
            # NOT: 'raw' alanı circular reference oluşturabilir, çıkarıyoruz
            chunk_data_for_db.append({
                'index': i,
                'start': chunk.start,
                'end': chunk.end,
                'data': chunk_result['data'],
                'model': chunk_result.get('model'),
                'duration': chunk_result.get('duration')
            })

        # Chunk sonuçlarını birleştir
        if chunk_results:
            merged = self.chunk_manager.merge_chunk_results(chunk_results)

            # ÖNEMLI: Chunk verilerini result'a ekle (kaydedilmek için)
            merged['_chunk_data'] = chunk_data_for_db

            return merged

        return None

    def _analyze_image(self, image_base64: str, belge_id: int) -> Optional[Dict[str, Any]]:
        """
        Görsel analizi (vision model ile).

        Args:
            image_base64: Base64 encoded görsel
            belge_id: Belge ID

        Returns:
            Dict: Analiz sonucu
        """
        result = self.ollama.analyze_with_vision(
            image_base64=image_base64,
            prompt_template=self.get_prompt_template(),
            document_type=self.get_document_type()
        )

        if result and result.get('success'):
            return result['data']

        return None

    def _save_analysis_log(
        self,
        belge_id: int,
        basvuru_id: int,
        start_time: datetime,
        result: Optional[Dict],
        success: bool
    ):
        """
        Analiz logunu ve chunk sonuçlarını kaydet.

        Args:
            belge_id: Belge ID
            basvuru_id: Başvuru ID
            start_time: Başlangıç zamanı
            result: Analiz sonucu
            success: Başarılı mı?
        """
        try:
            import json
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Chunk verilerini ayır
            chunk_data = result.get('_chunk_data', []) if result else []
            chunk_sayisi = len(chunk_data)

            # Log kaydı
            query = """
                INSERT INTO belge_analiz_log (
                    belgeId, basvuruId, belgeTipi,
                    ollama_url, ollama_model,
                    chunk_sayisi,
                    basarili, islem_baslangic, islem_bitis, islem_suresi_sn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL

            with db.get_cursor() as cursor:
                cursor.execute(query, (
                    belge_id,
                    basvuru_id,
                    self.get_document_type(),
                    OLLAMA_BASE_URL,
                    OLLAMA_MODEL,
                    chunk_sayisi if chunk_sayisi > 0 else 1,
                    1 if success else 0,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    duration
                ))

                # Log ID'yi al
                log_id = cursor.lastrowid

                # Chunk sonuçlarını kaydet
                if chunk_data and log_id:
                    chunk_query = """
                        INSERT INTO chunk_sonuclari (
                            log_id, chunk_index, chunk_start, chunk_end, response_json, response_valid
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """

                    for chunk in chunk_data:
                        try:
                            response_json = json.dumps(chunk['data'], ensure_ascii=False)
                            cursor.execute(chunk_query, (
                                log_id,
                                chunk['index'],
                                chunk['start'],
                                chunk['end'],
                                response_json,
                                1  # Valid JSON
                            ))
                        except Exception as e:
                            logger.error(f"Chunk {chunk['index']} kaydedilemedi: {e}")

            logger.debug(f"Analiz logu kaydedildi: {belge_id} ({chunk_sayisi} chunk)")

        except Exception as e:
            logger.error(f"Log kaydetme hatası: {e}")

    # ========== PHASE 2 İYİLEŞTİRMELER ==========

    def _check_document_format(self, belge: Dict) -> Dict[str, Any]:
        """
        PHASE 2.1: Belge Format Kontrolü

        Args:
            belge: Belge dict

        Returns:
            Dict: {'valid': bool, 'error': str}
        """
        from config.settings import MAX_FILE_SIZE
        import base64

        try:
            # Base64 decode test
            content = belge.get('belgeIcerik', '')
            if not content:
                return {'valid': False, 'error': 'Belge içeriği boş'}

            # Base64 geçerliliği
            try:
                decoded = base64.b64decode(content)
            except Exception:
                return {'valid': False, 'error': 'Base64 decode hatası'}

            # Boyut kontrolü
            if len(decoded) > MAX_FILE_SIZE:
                return {'valid': False, 'error': f'Dosya çok büyük: {len(decoded)} bytes'}

            if len(decoded) < 100:  # Çok küçük dosyalar şüpheli
                return {'valid': False, 'error': 'Dosya çok küçük, geçersiz olabilir'}

            return {'valid': True, 'error': None}

        except Exception as e:
            return {'valid': False, 'error': f'Format kontrolü hatası: {str(e)}'}

    def _check_ocr_quality(self, text: str) -> Dict[str, Any]:
        """
        PHASE 2.2: OCR Kalite Kontrolü

        Args:
            text: Çıkarılan metin

        Returns:
            Dict: {'acceptable': bool, 'reason': str, 'confidence': float}
        """
        import re

        # Boş mu?
        if not text or len(text.strip()) < 100:
            return {'acceptable': False, 'reason': 'Metin çok kısa (<100 karakter)', 'confidence': 0.0}

        # Garbled text kontrolü (çok fazla özel karakter)
        special_char_ratio = len(re.findall(r'[^a-zA-ZğüşıöçĞÜŞİÖÇ0-9\s.,;:!?()-]', text)) / len(text)
        if special_char_ratio > 0.3:
            return {'acceptable': False, 'reason': f'Çok fazla özel karakter (%{special_char_ratio*100:.1f})', 'confidence': 0.3}

        # Kelime oranı (boşluklarla bölünmüş parçalar)
        words = text.split()
        if len(words) < 20:
            return {'acceptable': False, 'reason': 'Çok az kelime (<20)', 'confidence': 0.4}

        # Ortalama kelime uzunluğu (çok uzun kelimeler OCR hatası olabilir)
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len > 15:
            return {'acceptable': False, 'reason': f'Anormal kelime uzunluğu (ort: {avg_word_len:.1f})', 'confidence': 0.5}

        # Confidence score hesapla
        confidence = min(1.0, 0.6 + (len(text) / 10000) * 0.2 + (len(words) / 100) * 0.2)

        return {'acceptable': True, 'reason': 'Kalite kabul edilebilir', 'confidence': confidence}

    def _validate_response(self, response: Dict) -> Dict[str, Any]:
        """
        PHASE 2.3: Response Validasyonu

        Args:
            response: LLM response dict

        Returns:
            Dict: {'valid': bool, 'warnings': List[str]}
        """
        warnings = []

        # Yıl kontrolü
        for key in ['mezuniyet_yili', 'dogum_yili', 'yil']:
            if key in response:
                year = response[key]
                if isinstance(year, (int, float)):
                    if year < 1950 or year > 2030:
                        warnings.append(f'{key}: {year} mantıksız (1950-2030 arası olmalı)')

        # Tecrübe kontrolü
        for key in response:
            if 'tecrube' in key or 'deneyim' in key:
                value = response[key]
                if isinstance(value, (int, float)):
                    if value < 0 or value > 50:
                        warnings.append(f'{key}: {value} mantıksız (0-50 arası olmalı)')

        # Boolean kontrolü
        for key, value in response.items():
            if isinstance(value, str) and value.lower() in ['true', 'false', 'yes', 'no']:
                warnings.append(f'{key}: String boolean değer ("{value}"), bool olmalı')

        return {'valid': len(warnings) == 0, 'warnings': warnings}

    def _validate_result(self, result: Dict) -> Dict[str, Any]:
        """
        PHASE 2.6: Final Sonuç Validasyonu

        Args:
            result: Analiz sonucu

        Returns:
            Dict: {'valid': bool, 'warnings': List[str]}
        """
        warnings = []

        # Temel response validasyonu
        response_validation = self._validate_response(result)
        warnings.extend(response_validation['warnings'])

        # Mantık kontrolleri
        mezuniyet = result.get('mezuniyet_yili')
        dogum = result.get('dogum_yili')

        if mezuniyet and dogum:
            if isinstance(mezuniyet, (int, float)) and isinstance(dogum, (int, float)):
                if mezuniyet - dogum < 16:
                    warnings.append(f'Mezuniyet ({mezuniyet}) - Doğum ({dogum}) < 16 yaş, mantıksız')
                if mezuniyet - dogum > 40:
                    warnings.append(f'Mezuniyet ({mezuniyet}) - Doğum ({dogum}) > 40 yaş, olağandışı')

        # Tecrübe vs mezuniyet
        from datetime import datetime
        current_year = datetime.now().year

        if mezuniyet:
            if isinstance(mezuniyet, (int, float)):
                max_tecrube = current_year - mezuniyet
                for key in ['toplam_is_deneyimi_yil', 'tecrube_enerji', 'tecrube_metal']:
                    if key in result:
                        tecrube = result[key]
                        if isinstance(tecrube, (int, float)) and tecrube > max_tecrube:
                            warnings.append(f'{key}: {tecrube} yıl > mezuniyetten bu yana ({max_tecrube} yıl)')

        return {'valid': len(warnings) == 0, 'warnings': warnings}
