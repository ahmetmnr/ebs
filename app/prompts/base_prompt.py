"""
Base prompt template - SOLID: Single Responsibility Principle
Her prompt sınıfı kendi belge tipine odaklanır
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BasePromptTemplate(ABC):
    """
    Abstract base class for all prompt templates
    SOLID: Open/Closed - Yeni belge tipleri için extend edilebilir
    """

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Sistem prompt'unu döndür"""
        pass

    @abstractmethod
    def get_user_prompt(self, text: str, schema: Dict) -> str:
        """Kullanıcı prompt'unu döndür"""
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        """Belge tipini döndür"""
        pass

    def format_schema(self, schema: Dict) -> str:
        """JSON şemasını formatla"""
        import json
        return json.dumps(schema, indent=2, ensure_ascii=False)

    def truncate_text(self, text: str, max_length: int = 4000) -> str:
        """Metni maksimum uzunlukta kes"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "\n\n... (metin kesildi)"
