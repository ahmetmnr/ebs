"""
Ollama LLM servisi
"""
import requests
import json
import logging
import urllib3
from typing import Dict, Optional, List
from app.config import settings

# SSL uyarılarını sustur
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class OllamaService:
    """Ollama LLM servisi"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT

        logger.info(f"Ollama initialized: {self.base_url} | Model: {self.model}")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        format: str = "json",
        max_retries: int = 2
    ) -> Dict:
        """
        Ollama'dan yanıt al (retry mekanizması ile)

        Args:
            prompt: User prompt
            system: System prompt
            temperature: 0.0-1.0 (düşük = deterministik)
            format: "json" veya None
            max_retries: Maksimum deneme sayısı

        Returns:
            Dict with 'response' key
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            payload["system"] = system

        if format == "json":
            payload["format"] = "json"

        logger.info(f"Ollama request: {self.model}")
        logger.debug(f"Prompt length: {len(prompt)} chars")

        # Retry loop
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    verify=False  # SSL doğrulamasını devre dışı bırak
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"Ollama response received")
                return result

            except requests.Timeout:
                logger.error(f"Ollama timeout ({self.timeout}s) - attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    raise
                continue

            except requests.HTTPError as e:
                # 504 Gateway Timeout - retry
                if e.response.status_code == 504:
                    logger.warning(f"504 Gateway Timeout - attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        raise
                    continue
                else:
                    logger.error(f"Ollama HTTP error: {e.response.status_code}")
                    logger.error(f"Response: {e.response.text[:500]}")
                    raise

            except Exception as e:
                logger.error(f"Ollama error: {str(e)}")
                raise

    def extract_json(self, response_text: str) -> Dict:
        """Yanıttan JSON çıkar"""
        try:
            # Direkt JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Markdown code block içinde olabilir
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
            else:
                raise

    def extract_structured_data(
        self,
        text: str,
        document_type: str,
        schema: Dict,
        basvuru_turu: str = None,
        basvuru_id: int = None
    ) -> Dict:
        """
        Metinden yapılandırılmış veri çıkar

        SOLID: Bu method artık PromptFactory kullanıyor (Dependency Inversion)

        Args:
            text: Belge metni
            document_type: Belge tipi (özgeçmiş, sgk, diploma, vs.)
            schema: JSON schema
            basvuru_turu: Başvuru türü (Akademisyen, Bakanlık Personeli, Sektör Çalışanı)
            basvuru_id: Başvuru ID (loglama için)

        Returns:
            Çıkarılan veriler
        """
        from app.prompts import PromptFactory
        import os
        from datetime import datetime

        # Factory'den uygun prompt al (başvuru türü ile)
        prompt_template = PromptFactory.create_prompt(document_type, basvuru_turu)

        if prompt_template:
            # Özelleştirilmiş prompt kullan
            system_prompt = prompt_template.get_system_prompt()
            user_prompt = prompt_template.get_user_prompt(text, schema)
        else:
            # Fallback: Generic prompt
            logger.warning(f"Özel prompt bulunamadı: {document_type}, generic kullanılıyor")
            system_prompt = f"""Sen Türk kamu idaresinde çalışan bir belge işleme uzmanısın.
Verilen {document_type} belgesinden bilgileri JSON formatında çıkaracaksın.
Sadece belgede açıkça yazılı bilgileri kullan. Tahmin yapma.
Eğer bir bilgi belgede yoksa, null döndür."""

            user_prompt = f"""Aşağıdaki {document_type} belgesinden bilgileri çıkar ve verilen JSON şemasına göre döndür.

BELGE METNİ:
{text}

JSON ŞEMA:
{json.dumps(schema, indent=2, ensure_ascii=False)}

ÖNEMLİ:
- Sadece belgede yazılı bilgileri kullan
- Tarih formatı: YYYY-MM-DD
- Boş alanlar için null kullan
- Türkçe karakterleri koru

Yanıtını sadece JSON olarak ver, başka açıklama ekleme:"""

        # LLM çağrısı
        response = self.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.1,
            format="json"
        )

        # JSON çıkar
        response_text = response.get('response', '{}')
        extracted_data = self.extract_json(response_text)

        # ===== LOGLAMA SİSTEMİ =====
        # llm_logs/{takip_no}/ klasörüne kaydet
        try:
            if basvuru_id:
                log_dir = f"llm_logs/{basvuru_id}"
            else:
                log_dir = "llm_logs/genel"
            os.makedirs(log_dir, exist_ok=True)

            # Dosya adından / karakterini kaldır (özgeçmiş/cv → ozgecmis_cv)
            safe_document_type = document_type.replace("/", "_").replace("\\", "_")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            log_filename = f"{log_dir}/{safe_document_type}_{timestamp}.json"

            log_data = {
                "timestamp": datetime.now().isoformat(),
                "basvuru_id": basvuru_id,
                "document_type": document_type,
                "basvuru_turu": basvuru_turu,
                "model": self.model,
                "request": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "text_length": len(text),
                    "text_preview": text[:500]  # İlk 500 karakter
                },
                "response": {
                    "raw_text": response_text,
                    "extracted_data": extracted_data,
                    "response_length": len(response_text)
                }
            }

            with open(log_filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"LLM log kaydedildi: {log_filename}")
        except Exception as e:
            logger.warning(f"LLM log kaydedilemedi: {str(e)}")
        # ===========================

        return extracted_data

    def test_connection(self) -> bool:
        """Ollama bağlantısını test et"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            models = response.json().get('models', [])
            logger.info(f"✅ Ollama bağlantısı başarılı: {len(models)} model")

            # Seçili model var mı kontrol et
            model_names = [m['name'] for m in models]
            if self.model in model_names:
                logger.info(f"✅ Model mevcut: {self.model}")
                return True
            else:
                logger.warning(f"⚠️  Model bulunamadı: {self.model}")
                logger.info(f"Mevcut modeller: {', '.join(model_names)}")
                return False

        except Exception as e:
            logger.error(f"❌ Ollama bağlantı hatası: {str(e)}")
            return False
