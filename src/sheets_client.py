import os
import csv
import io
import time
import urllib.request
from src.config import (
    SPREADSHEET_ID, TODAY_SHEET_NAME, TODAY_SHEET_GID,
    HISTORICAL_SHEET_NAME, HISTORICAL_SHEET_GID,
    REGISTRATIONS_SHEET_NAME, REGISTRATIONS_SHEET_GID,
    SERVICE_ACCOUNT_PATH, logger
)

class SheetsClient:
    """
    Handles Google Sheets data fetching.
    Tries Google Service Account (gspread) first if credentials file exists,
    otherwise falls back to Google Sheets CSV export for public sheets.
    Includes retry and exponential backoff logic.
    """
    def __init__(self, cache_ttl: int = 60):
        self.gc = None
        self.sh = None
        self.cache_ttl = cache_ttl
        self._today_cache = None
        self._today_cache_time = 0
        self._hist_cache = None
        self._hist_cache_time = 0
        self._reg_cache = None
        self._reg_cache_time = 0
        self._init_gspread()

    def _init_gspread(self):
        if os.path.exists(SERVICE_ACCOUNT_PATH):
            try:
                import gspread
                self.gc = gspread.service_account(filename=SERVICE_ACCOUNT_PATH)
                self.sh = self.gc.open_by_key(SPREADSHEET_ID)
                logger.info("Successfully connected to Google Sheets via Service Account (gspread).")
            except Exception as e:
                logger.warning(f"Could not initialize gspread with {SERVICE_ACCOUNT_PATH}: {e}. Fallback to CSV export.")
                self.gc = None
                self.sh = None
        else:
            logger.info(f"Service account file {SERVICE_ACCOUNT_PATH} not found. Using direct Sheet CSV export.")

    def _fetch_with_retry(self, fetch_func, description: str, max_retries: int = 3, base_delay: float = 2.0):
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                return fetch_func()
            except Exception as e:
                last_error = e
                wait_time = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Error fetching {description} (Attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        logger.error(f"Failed to fetch {description} after {max_retries} attempts. Error: {last_error}")
        raise last_error

    def _fetch_csv(self, gid: str) -> list[list[str]]:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read().decode("utf-8")
        reader = csv.reader(io.StringIO(content))
        return [row for row in reader]

    def get_today_sheet_rows(self, force_refresh: bool = False) -> list[list[str]]:
        if not force_refresh and self._today_cache and (time.time() - self._today_cache_time < self.cache_ttl):
            return self._today_cache

        def _fetch():
            if self.sh:
                try:
                    worksheet = self.sh.worksheet(TODAY_SHEET_NAME)
                    return worksheet.get_all_values()
                except Exception as e:
                    logger.warning(f"gspread worksheet error ({TODAY_SHEET_NAME}): {e}. Trying CSV export fallback...")
            return self._fetch_csv(TODAY_SHEET_GID)

        rows = self._fetch_with_retry(_fetch, f"Today Sheet ({TODAY_SHEET_NAME})")
        self._today_cache = rows
        self._today_cache_time = time.time()
        return rows

    def get_historical_sheet_rows(self, force_refresh: bool = False) -> list[list[str]]:
        if not force_refresh and self._hist_cache and (time.time() - self._hist_cache_time < self.cache_ttl):
            return self._hist_cache

        def _fetch():
            if self.sh:
                try:
                    worksheet = self.sh.worksheet(HISTORICAL_SHEET_NAME)
                    return worksheet.get_all_values()
                except Exception as e:
                    logger.warning(f"gspread worksheet error ({HISTORICAL_SHEET_NAME}): {e}. Trying CSV export fallback...")
            return self._fetch_csv(HISTORICAL_SHEET_GID)

        rows = self._fetch_with_retry(_fetch, f"Historical Sheet ({HISTORICAL_SHEET_NAME})")
        self._hist_cache = rows
        self._hist_cache_time = time.time()
        return rows

    def get_registrations_sheet_rows(self, force_refresh: bool = False) -> list[list[str]]:
        if not force_refresh and self._reg_cache and (time.time() - self._reg_cache_time < self.cache_ttl):
            return self._reg_cache

        def _fetch():
            if self.sh:
                try:
                    worksheet = self.sh.worksheet(REGISTRATIONS_SHEET_NAME)
                    return worksheet.get_all_values()
                except Exception as e:
                    logger.warning(f"gspread worksheet error ({REGISTRATIONS_SHEET_NAME}): {e}. Trying CSV export fallback...")
            return self._fetch_csv(REGISTRATIONS_SHEET_GID)

        rows = self._fetch_with_retry(_fetch, f"Registrations Sheet ({REGISTRATIONS_SHEET_NAME})")
        self._reg_cache = rows
        self._reg_cache_time = time.time()
        return rows
