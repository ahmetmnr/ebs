"""
SQLite veritabanı yönetimi ve base model sınıfı.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from datetime import datetime
import logging

from config.settings import (
    DATABASE_PATH,
    SQLITE_PRAGMAS,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite veritabanı yönetim sınıfı"""

    def __init__(self, db_path: Path = DATABASE_PATH):
        """
        Args:
            db_path: Veritabanı dosya yolu
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Veritabanına bağlan ve pragmaları ayarla.

        Returns:
            sqlite3.Connection: Veritabanı bağlantısı
        """
        if self._connection is None:
            logger.info(f"Veritabanına bağlanılıyor: {self.db_path}")
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )

            # Row factory ayarla (dict gibi erişim için)
            self._connection.row_factory = sqlite3.Row

            # Pragmaları ayarla
            for pragma, value in SQLITE_PRAGMAS.items():
                self._connection.execute(f"PRAGMA {pragma} = {value}")

            logger.info("Veritabanı bağlantısı başarılı")

        return self._connection

    def close(self):
        """Veritabanı bağlantısını kapat"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Veritabanı bağlantısı kapatıldı")

    @contextmanager
    def get_cursor(self):
        """
        Context manager ile cursor al.

        Yields:
            sqlite3.Cursor: Veritabanı cursor'u

        Example:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM basvurular")
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Veritabanı işlem hatası: {e}")
            raise
        finally:
            cursor.close()

    def execute(self, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """
        SQL sorgusu çalıştır.

        Args:
            query: SQL sorgusu
            params: Parametreler (tuple)

        Returns:
            sqlite3.Cursor: Sonuç cursor'u
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor

    def executemany(self, query: str, params_list: List[tuple]) -> int:
        """
        Çoklu SQL sorgusu çalıştır.

        Args:
            query: SQL sorgusu
            params_list: Parametre listesi

        Returns:
            int: Etkilenen satır sayısı
        """
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount

    def fetchone(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """
        Tek satır getir.

        Args:
            query: SQL sorgusu
            params: Parametreler

        Returns:
            Dict or None: Sonuç dictionary
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetchall(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """
        Tüm satırları getir.

        Args:
            query: SQL sorgusu
            params: Parametreler

        Returns:
            List[Dict]: Sonuç listesi
        """
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def init_database(self, schema_path: Optional[Path] = None):
        """
        Veritabanını başlat (schema'yı çalıştır).

        Args:
            schema_path: Schema SQL dosya yolu
        """
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "database" / "schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema dosyası bulunamadı: {schema_path}")

        logger.info(f"Veritabanı schema'sı çalıştırılıyor: {schema_path}")

        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        conn = self.connect()
        conn.executescript(schema_sql)
        conn.commit()

        logger.info("Veritabanı başarıyla oluşturuldu")

    def table_exists(self, table_name: str) -> bool:
        """
        Tablo var mı kontrol et.

        Args:
            table_name: Tablo adı

        Returns:
            bool: Tablo varsa True
        """
        query = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name=?
        """
        result = self.fetchone(query, (table_name,))
        return result is not None

    def get_row_count(self, table_name: str) -> int:
        """
        Tablodaki satır sayısını getir.

        Args:
            table_name: Tablo adı

        Returns:
            int: Satır sayısı
        """
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        result = self.fetchone(query)
        return result['count'] if result else 0


# Global database instance
db = DatabaseManager()


class BaseModel:
    """
    Tüm model sınıflarının base class'ı.
    CRUD operasyonları için temel metodlar sağlar.
    """

    table_name: str = None  # Alt sınıflarda override edilmeli

    @classmethod
    def insert(cls, data: Dict[str, Any]) -> int:
        """
        Yeni kayıt ekle.

        Args:
            data: Eklenecek veri dictionary

        Returns:
            int: Eklenen kaydın ID'si

        Example:
            basvuru_id = Basvuru.insert({
                'basvuruId': 123,
                'takipNo': '5931381',
                'basvuruTarihi': '2025-04-29T15:46:26',
                ...
            })
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"""
            INSERT INTO {cls.table_name} ({columns})
            VALUES ({placeholders})
        """

        with db.get_cursor() as cursor:
            cursor.execute(query, tuple(data.values()))
            return cursor.lastrowid

    @classmethod
    def update(cls, record_id: int, data: Dict[str, Any], id_column: str = 'id') -> bool:
        """
        Kayıt güncelle.

        Args:
            record_id: Kayıt ID'si
            data: Güncellenecek veri dictionary
            id_column: ID kolonunun adı

        Returns:
            bool: Başarılı ise True
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"""
            UPDATE {cls.table_name}
            SET {set_clause}
            WHERE {id_column} = ?
        """

        with db.get_cursor() as cursor:
            cursor.execute(query, (*data.values(), record_id))
            return cursor.rowcount > 0

    @classmethod
    def delete(cls, record_id: int, id_column: str = 'id') -> bool:
        """
        Kayıt sil.

        Args:
            record_id: Kayıt ID'si
            id_column: ID kolonunun adı

        Returns:
            bool: Başarılı ise True
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        query = f"DELETE FROM {cls.table_name} WHERE {id_column} = ?"

        with db.get_cursor() as cursor:
            cursor.execute(query, (record_id,))
            return cursor.rowcount > 0

    @classmethod
    def get_by_id(cls, record_id: int, id_column: str = 'id') -> Optional[Dict]:
        """
        ID'ye göre kayıt getir.

        Args:
            record_id: Kayıt ID'si
            id_column: ID kolonunun adı

        Returns:
            Dict or None: Kayıt dictionary
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        query = f"SELECT * FROM {cls.table_name} WHERE {id_column} = ?"
        return db.fetchone(query, (record_id,))

    @classmethod
    def get_all(cls, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        """
        Tüm kayıtları getir.

        Args:
            limit: Maksimum kayıt sayısı
            offset: Başlangıç offset'i

        Returns:
            List[Dict]: Kayıt listesi
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        query = f"SELECT * FROM {cls.table_name}"

        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        return db.fetchall(query)

    @classmethod
    def count(cls) -> int:
        """
        Toplam kayıt sayısı.

        Returns:
            int: Kayıt sayısı
        """
        if cls.table_name is None:
            raise NotImplementedError("table_name tanımlanmalı")

        return db.get_row_count(cls.table_name)
