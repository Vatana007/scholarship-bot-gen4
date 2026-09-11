import sqlite3
import json
import os
from datetime import datetime
from contextlib import contextmanager
from src.config import DB_PATH, logger

class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _db_cursor(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT,
                    target_date TEXT,
                    sent_at TEXT,
                    status TEXT,
                    message_id INTEGER
                )
            """)

    def get(self, key: str, default=None):
        try:
            with self._db_cursor() as cursor:
                cursor.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.error(f"Storage get error ({key}): {e}")
            return default

    def set(self, key: str, value: str):
        try:
            with self._db_cursor() as cursor:
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO kv_store (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """, (key, value, now))
        except Exception as e:
            logger.error(f"Storage set error ({key}): {e}")

    def get_json(self, key: str, default=None):
        val = self.get(key)
        if val is None:
            return default
        try:
            return json.loads(val)
        except Exception:
            return default

    def set_json(self, key: str, value):
        self.set(key, json.dumps(value, ensure_ascii=False))

    def is_report_sent(self, report_type: str, target_date: str) -> bool:
        try:
            with self._db_cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM report_logs
                    WHERE report_type = ? AND target_date = ? AND status = 'SUCCESS'
                """, (report_type, target_date))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Storage is_report_sent error: {e}")
            return False

    def log_report_sent(self, report_type: str, target_date: str, message_id: int = None, status: str = "SUCCESS"):
        try:
            with self._db_cursor() as cursor:
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO report_logs (report_type, target_date, sent_at, status, message_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (report_type, target_date, now, status, message_id))
        except Exception as e:
            logger.error(f"Storage log_report_sent error: {e}")

    def get_report_history(self, limit: int = 20) -> list[dict]:
        try:
            with self._db_cursor() as cursor:
                cursor.execute("""
                    SELECT id, report_type, target_date, sent_at, status, message_id
                    FROM report_logs
                    ORDER BY id DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [
                    {
                        "id": r[0],
                        "report_type": r[1],
                        "target_date": r[2],
                        "sent_at": r[3],
                        "status": r[4],
                        "message_id": r[5]
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Storage get_report_history error: {e}")
            return []

    def get_setting(self, key: str, default=None):
        return self.get(f"setting:{key}", default)

    def set_setting(self, key: str, value: str):
        self.set(f"setting:{key}", str(value))

    def get_all_settings(self) -> dict:
        try:
            with self._db_cursor() as cursor:
                cursor.execute("SELECT key, value FROM kv_store WHERE key LIKE 'setting:%'")
                rows = cursor.fetchall()
                settings = {}
                for k, v in rows:
                    setting_name = k.replace("setting:", "")
                    settings[setting_name] = v
                return settings
        except Exception as e:
            logger.error(f"Storage get_all_settings error: {e}")
            return {}

