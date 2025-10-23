"""
Ollama API servisi.
LLM ile belge analizi yapar.
"""

import requests
import json
import logging
import time
from typing import Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import (
    OLLAMA_API_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_MAX_RETRIES,
    OLLAMA_OPTIONS,
)

logger = logging.getLogger(__name__)


class OllamaService:
    """Ollama API client servisi"""

    def __init__(self, model: str = OLLAMA_MODEL):
        """
        Args:
            model: Kullanılacak Ollama model adı
        """
        self.model = model
        self.api_url = OLLAMA_API_URL
        self.timeout = OLLAMA_TIMEOUT

    @retry(
        stop=stop_after_attempt(OLLAMA_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Ollama generate API çağrısı.

        Args:
            prompt: Ana prompt
            system_prompt: Sistem promptu (opsiyonel)
            images: Base64 encoded görseller (vision model için)

        Returns:
            Dict: API response

        Raises:
            Exception: API hatası
        """
        start_time = time.time()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": OLLAMA_OPTIONS,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if images:
            payload["images"] = images

        try:
            logger.debug(f"Ollama API isteği gönderiliyor: {self.api_url}")

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()

            result = response.json()
            duration = time.time() - start_time

            logger.info(f"Ollama API başarılı (süre: {duration:.2f}s)")

            return {
                'success': True,
                'response': result.get('response', ''),
                'duration': duration,
                'model': result.get('model'),
                'context': result.get('context'),
                'raw': result,
            }

        except requests.Timeout:
            logger.error(f"Ollama API timeout ({self.timeout}s)")
            raise

        except requests.RequestException as e:
            logger.error(f"Ollama API hatası: {e}")
            raise

        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
            raise

    def analyze_document(
        self,
        document_text: str,
        document_type: str,
        prompt_template: str
    ) -> Optional[Dict[str, Any]]:
        """
        Belge analizi yap.

        Args:
            document_text: Belge metni
            document_type: Belge tipi
            prompt_template: Prompt template

        Returns:
            Dict: Analiz sonucu (JSON parse edilmiş)
        """
        try:
            # Prompt oluştur
            prompt = prompt_template.format(
                document_text=document_text,
                document_type=document_type
            )

            system_prompt = (
                "Sen bir belge analiz asistanısın. "
                "Verilen belgeyi analiz edip istenen bilgileri JSON formatında çıkar. "
                "Sadece JSON döndür, başka açıklama yapma."
            )

            # 🔍 LOG: REQUEST
            logger.info(f"{'='*80}")
            logger.info(f"📤 OLLAMA REQUEST - Belge Tipi: {document_type}")
            logger.info(f"Model: {self.model}")
            logger.info(f"Prompt uzunluğu: {len(prompt)} karakter")
            logger.info(f"Document text ilk 200 char: {document_text[:200]}...")
            logger.info(f"{'='*80}")

            # API çağrısı
            result = self.generate(
                prompt=prompt,
                system_prompt=system_prompt
            )

            if not result['success']:
                logger.error(f"❌ OLLAMA FAILED - Belge Tipi: {document_type}")
                return None

            # JSON parse
            response_text = result['response'].strip()

            # 🔍 LOG: RAW RESPONSE
            logger.info(f"{'='*80}")
            logger.info(f"📥 OLLAMA RAW RESPONSE - Belge Tipi: {document_type}")
            logger.info(f"Response uzunluğu: {len(response_text)} karakter")
            logger.info(f"Response (ilk 500 char): {response_text[:500]}...")
            logger.info(f"Süre: {result.get('duration', 0):.2f}s")
            logger.info(f"{'='*80}")

            # JSON temizleme (markdown code block varsa)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse
            parsed = json.loads(response_text)

            # 🔍 LOG: PARSED JSON
            logger.info(f"{'='*80}")
            logger.info(f"📋 PARSED JSON - Belge Tipi: {document_type}")
            logger.info(f"JSON type: {type(parsed).__name__}")
            if isinstance(parsed, dict):
                logger.info(f"JSON keys: {list(parsed.keys())}")
                for key, value in parsed.items():
                    if isinstance(value, list):
                        logger.info(f"  - {key}: list with {len(value)} items")
                    elif isinstance(value, dict):
                        logger.info(f"  - {key}: dict with keys {list(value.keys())}")
                    else:
                        logger.info(f"  - {key}: {type(value).__name__} = {str(value)[:100]}")
            elif isinstance(parsed, list):
                logger.info(f"JSON is list with {len(parsed)} items")
            logger.info(f"{'='*80}")

            # FIX: Eğer liste döndüyse ilk elemanı al
            if isinstance(parsed, list):
                if len(parsed) > 0:
                    logger.warning(f"⚠️ LLM liste döndürdü ({len(parsed)} eleman), ilk eleman alınıyor")
                    parsed = parsed[0]
                else:
                    logger.error("❌ LLM boş liste döndürdü")
                    return None

            return {
                'data': parsed,
                'duration': result['duration'],
                'model': result['model'],
                'success': True,
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
            logger.error(f"Response: {result.get('response', '')[:200]}")
            return None

        except Exception as e:
            logger.error(f"Belge analiz hatası: {e}")
            return None

    def analyze_with_vision(
        self,
        image_base64: str,
        prompt_template: str,
        document_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Görsel belge analizi (vision model ile).

        Args:
            image_base64: Base64 encoded görsel
            prompt_template: Prompt template
            document_type: Belge tipi

        Returns:
            Dict: Analiz sonucu
        """
        try:
            prompt = prompt_template.format(document_type=document_type)

            system_prompt = (
                "Sen bir belge analiz asistanısın. "
                "Görsel belgeleri okuyup analiz edebilirsin. "
                "İstenen bilgileri JSON formatında çıkar."
            )

            result = self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                images=[image_base64]
            )

            if not result['success']:
                return None

            # JSON parse
            response_text = result['response'].strip()

            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            parsed = json.loads(response_text)

            return {
                'data': parsed,
                'duration': result['duration'],
                'model': result['model'],
                'success': True,
            }

        except Exception as e:
            logger.error(f"Vision analiz hatası: {e}")
            return None

    def check_health(self) -> bool:
        """
        Ollama API sağlık kontrolü.

        Returns:
            bool: API erişilebilir mi?
        """
        try:
            # Basit bir test promptu
            result = self.generate("test", system_prompt="Say hello")
            return result['success']

        except Exception as e:
            logger.error(f"Ollama health check başarısız: {e}")
            return False
