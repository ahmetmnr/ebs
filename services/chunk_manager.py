"""
Chunk yönetim servisi.
Büyük belgeleri chunk'lara böler ve yönetir.
"""

import hashlib
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_SIZE, CHARS_PER_TOKEN

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Chunk veri sınıfı"""
    index: int
    text: str
    start: int
    end: int
    hash: str


class ChunkManager:
    """Belge chunk yönetim servisi"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        """
        Args:
            chunk_size: Chunk karakter sayısı
            overlap: Overlap karakter sayısı
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(self, text: str) -> List[Chunk]:
        """
        PHASE 2.4: Metni chunk'lara böl (cümle sınırında).

        Args:
            text: Bölünecek metin

        Returns:
            List[Chunk]: Chunk listesi
        """
        # Çok küçükse chunk'lama
        if len(text) < MIN_CHUNK_SIZE:
            return [Chunk(
                index=0,
                text=text,
                start=0,
                end=len(text),
                hash=""  # Hash hesaplamayı devre dışı bırak (performans)
            )]

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            # Chunk sonu (hedef)
            target_end = start + self.chunk_size

            # Son chunk
            if target_end >= len(text):
                target_end = len(text)
                chunk_text = text[start:target_end]
            else:
                # PHASE 2.4: Cümle sınırında böl
                # Hedef nokta çevresinde cümle sonu ara (., !, ?)
                search_range = 200  # Hedefin ±200 karakter çevresinde ara
                search_start = max(start, target_end - search_range)
                search_end = min(len(text), target_end + search_range)
                search_text = text[search_start:search_end]

                # Cümle sonu karakterleri ara
                import re
                sentence_endings = list(re.finditer(r'[.!?]\s+', search_text))

                if sentence_endings:
                    # En yakın cümle sonunu bul
                    best_match = min(sentence_endings,
                                   key=lambda m: abs((search_start + m.end()) - target_end))
                    actual_end = search_start + best_match.end()
                    chunk_text = text[start:actual_end]
                else:
                    # Cümle sonu bulunamadıysa, kelime sınırında böl
                    space_pos = text.rfind(' ', target_end - 100, target_end + 100)
                    if space_pos != -1:
                        chunk_text = text[start:space_pos]
                    else:
                        # Kelime sınırı da bulunamadıysa normal böl
                        chunk_text = text[start:target_end]

            # Chunk oluştur
            chunks.append(Chunk(
                index=index,
                text=chunk_text.strip(),
                start=start,
                end=start + len(chunk_text),
                hash=""  # Hash hesaplamayı devre dışı bırak (performans)
            ))

            # Son chunk ise döngüden çık
            if start + len(chunk_text) >= len(text):
                break

            # Sonraki chunk başlangıcı (overlap ile)
            start = start + len(chunk_text) - self.overlap
            index += 1

        logger.info(f"Metin {len(chunks)} chunk'a bölündü (cümle sınırında)")
        return chunks

    def merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Chunk sonuçlarını birleştir.

        Args:
            chunk_results: Her chunk'ın analiz sonucu

        Returns:
            Dict: Birleştirilmiş sonuç
        """
        if not chunk_results:
            return {}

        # İlk chunk'ı base al
        merged = chunk_results[0].copy()

        # Diğer chunk'ları merge et
        for result in chunk_results[1:]:
            merged = self._merge_two_dicts(merged, result)

        return merged

    def _merge_two_dicts(self, dict1: Dict, dict2: Dict) -> Dict:
        """
        İki dictionary'yi merge et.

        Strategy:
        - Sayısal değerler: Topla
        - String değerler: Boş olmayanı al
        - Boolean değerler: OR işlemi
        - List değerler: Birleştir (tekrar eden olmadan)

        Args:
            dict1: İlk dictionary
            dict2: İkinci dictionary

        Returns:
            Dict: Merge edilmiş dictionary
        """
        merged = dict1.copy()

        # Validation rules for year fields (reject impossible values)
        YEAR_VALIDATION = {
            'mezuniyet_yili': (1950, 2030),
            'dogum_yili': (1930, 2015),
            'dogum_tarihi_yil': (1930, 2015),
        }

        for key, value in dict2.items():
            if key not in merged:
                merged[key] = value
                continue

            val1 = merged[key]
            val2 = value

            # Sayısal değerler
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Özel durum: Yıl field'ları için validation
                if key in YEAR_VALIDATION:
                    min_year, max_year = YEAR_VALIDATION[key]
                    val1_valid = min_year <= val1 <= max_year
                    val2_valid = min_year <= val2 <= max_year

                    if val1_valid and val2_valid:
                        # Her ikisi de geçerli, en küçüğü al (daha muhafazakar)
                        merged[key] = min(val1, val2)
                    elif val1_valid:
                        # Sadece val1 geçerli
                        merged[key] = val1
                    elif val2_valid:
                        # Sadece val2 geçerli
                        merged[key] = val2
                    else:
                        # Her ikisi de geçersiz, None yap
                        merged[key] = None
                else:
                    # Normal sayısal değerler: topla
                    merged[key] = val1 + val2

            # String değerler
            elif isinstance(val1, str) and isinstance(val2, str):
                # Boş olmayanı al, her ikisi de doluysa ilkini tut
                if not val1:
                    merged[key] = val2
                # val1 zaten dolu, değiştirme

            # Boolean değerler
            elif isinstance(val1, bool) and isinstance(val2, bool):
                merged[key] = val1 or val2

            # List değerler
            elif isinstance(val1, list) and isinstance(val2, list):
                # Birleştir (dict içerebilir, set kullanma!)
                merged[key] = val1 + val2

            # Dict değerler (recursive)
            elif isinstance(val1, dict) and isinstance(val2, dict):
                merged[key] = self._merge_two_dicts(val1, val2)

        return merged

    def estimate_tokens(self, text: str) -> int:
        """
        Token sayısını tahmin et.

        Args:
            text: Metin

        Returns:
            int: Tahmini token sayısı
        """
        return len(text) // CHARS_PER_TOKEN

    def _calculate_hash(self, text: str) -> str:
        """
        Metin için SHA256 hash hesapla.

        Args:
            text: Metin

        Returns:
            str: Hash (hex)
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def get_chunk_stats(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """
        Chunk istatistikleri.

        Args:
            chunks: Chunk listesi

        Returns:
            Dict: İstatistikler
        """
        if not chunks:
            return {}

        total_chars = sum(len(c.text) for c in chunks)
        total_tokens = self.estimate_tokens(''.join(c.text for c in chunks))

        return {
            'chunk_count': len(chunks),
            'total_chars': total_chars,
            'avg_chunk_size': total_chars // len(chunks),
            'estimated_tokens': total_tokens,
            'overlap': self.overlap,
        }
