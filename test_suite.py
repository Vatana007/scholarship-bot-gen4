import os
import sys
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = r"d:\DUC-Work\Coding\Project DUC\Bot\Bot-Scholarship\New Bot_UI"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import src.config as config
from src.storage import Storage
from src.sheets_client import SheetsClient
from src.parser import (
    parse_today_sheet, parse_historical_sheet, parse_int_safe,
    compute_rows_hash, parse_status_gender_summary
)
from src.report_builder import (
    format_daily_report, format_monthly_report, format_diff_alert,
    format_categories_page, format_help, format_welcome, to_khmer_num,
    format_khmer_date, format_status_summary_report
)

def validate_telegram_html(text: str) -> bool:
    """
    Validates that Telegram HTML tags (<b>, <i>, <code>, <s>, <u>, <a>)
    are properly closed and valid XML-like structure.
    """
    wrapped = f"<root>{text}</root>"
    try:
        ET.fromstring(wrapped)
        return True
    except ET.ParseError as e:
        print(f"HTML Parse Error: {e} in text:\n{text}")
        return False

class TestBotSuite(unittest.TestCase):

    def test_01_imports_and_config(self):
        """Test configuration loading and defaults."""
        self.assertIsNotNone(config.BOT_TOKEN)
        self.assertEqual(config.SPREADSHEET_ID, "14XY1kCjb8znDeKWLqYrPJJhH2P7BQwo9ciqeRlh8qC8")
        self.assertEqual(config.TODAY_SHEET_NAME, "ស្ថិតិថ្ងៃនឹង")
        self.assertEqual(config.HISTORICAL_SHEET_NAME, "ស្ថិតិប្រចាំថ្ងៃ")
        self.assertIsNotNone(config.TIMEZONE)
        self.assertTrue(config.is_chat_allowed(config.REPORT_CHAT_ID))
        print("PASS: Test 01: Imports & Config passed")

    def test_02_storage(self):
        """Test SQLite state storage and deduplication."""
        test_db = os.path.join(config.DATA_DIR, "test_state.db")
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass
        
        storage = Storage(db_path=test_db)
        # Test basic kv
        storage.set("test_key", "test_val")
        self.assertEqual(storage.get("test_key"), "test_val")

        # Test json kv
        data = {"count": 10, "items": ["a", "b"]}
        storage.set_json("test_json", data)
        self.assertEqual(storage.get_json("test_json"), data)

        # Test report deduplication tracking
        date_key = "2026-09-10"
        self.assertFalse(storage.is_report_sent("DAILY", date_key))
        storage.log_report_sent("DAILY", date_key, message_id=12345)
        self.assertTrue(storage.is_report_sent("DAILY", date_key))
        self.assertFalse(storage.is_report_sent("DAILY", "2026-09-11"))

        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass
        print("PASS: Test 02: Storage passed")

    def test_03_sheets_client_live(self):
        """Test fetching live rows from Google Sheet."""
        client = SheetsClient()
        today_rows = client.get_today_sheet_rows()
        self.assertIsInstance(today_rows, list)
        self.assertGreater(len(today_rows), 10)

        hist_rows = client.get_historical_sheet_rows()
        self.assertIsInstance(hist_rows, list)
        self.assertGreater(len(hist_rows), 10)
        print(f"PASS: Test 03: Live Sheets fetched successfully ({len(today_rows)} today rows, {len(hist_rows)} historical rows)")

    def test_04_parser_live_data(self):
        """Test parsing live data for both sheets."""
        client = SheetsClient()
        today_rows = client.get_today_sheet_rows()
        today_data = parse_today_sheet(today_rows)

        self.assertGreater(len(today_data.categories), 15)
        self.assertIsInstance(today_data.grand_total, int)
        self.assertGreaterEqual(today_data.grand_total, 0)
        self.assertIn("DUC", today_data.sources_summary)
        self.assertIn("E-School", today_data.sources_summary)
        print(f"PASS: Test 04a: Today Sheet parsed: {today_data.grand_total} students, {len(today_data.categories)} categories, sources: {today_data.sources_summary}")

        hist_rows = client.get_historical_sheet_rows()
        hist_data = parse_historical_sheet(hist_rows)
        self.assertGreater(len(hist_data.categories), 15)
        self.assertGreater(len(hist_data.dates), 0)
        self.assertGreaterEqual(hist_data.grand_total, 0)
        print(f"PASS: Test 04b: Historical Sheet parsed: {hist_data.grand_total} students across {len(hist_data.dates)} dates")

    def test_05_report_builder_and_html_validation(self):
        """Test all reports format valid Telegram HTML."""
        client = SheetsClient()
        today_rows = client.get_today_sheet_rows()
        today_data = parse_today_sheet(today_rows)

        # 1. Daily report (default non-zero)
        daily_html = format_daily_report(today_data, delta_total=3, show_all=False)
        self.assertTrue(validate_telegram_html(daily_html), "Daily report HTML must be valid")

        # 2. Daily report (show all)
        daily_all_html = format_daily_report(today_data, delta_total=0, show_all=True)
        self.assertTrue(validate_telegram_html(daily_all_html), "Daily report (show all) HTML must be valid")

        # 3. Monthly report
        hist_rows = client.get_historical_sheet_rows()
        hist_data = parse_historical_sheet(hist_rows)
        monthly_html = format_monthly_report(hist_data)
        self.assertTrue(validate_telegram_html(monthly_html), "Monthly report HTML must be valid")

        # 4. Diff alert
        changes = [
            {"name": "រដ្ឋបាលសាធារណៈ", "old": 8, "new": 9},
            {"name": "ទីផ្សារឌីជីថល", "old": 1, "new": 2}
        ]
        diff_html = format_diff_alert(changes, current_total=16, old_total=14)
        self.assertTrue(validate_telegram_html(diff_html), "Diff alert HTML must be valid")

        # 5. Categories pagination
        cat_page_html, _ = format_categories_page(today_data.categories, page=1, page_size=8)
        self.assertTrue(validate_telegram_html(cat_page_html), "Categories page HTML must be valid")

        # 6. Help & Welcome
        self.assertTrue(validate_telegram_html(format_help()), "Help HTML must be valid")
        self.assertTrue(validate_telegram_html(format_welcome()), "Welcome HTML must be valid")

        print("PASS: Test 05: All report HTML templates strictly valid and well-formatted")

    def test_06_diff_logic(self):
        """Test simulated real-time diff detection."""
        test_db = os.path.join(config.DATA_DIR, "test_diff_state.db")
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass
        storage = Storage(db_path=test_db)

        # Base snapshot
        storage.set("today_sheet_hash", "hash_v1")
        storage.set_json("today_sheet_snapshot", {
            "grand_total": 14,
            "categories": {"រដ្ឋបាលសាធារណៈ": 8, "ទីផ្សារឌីជីថល": 1},
            "sources": {"DUC": 1}
        })

        # Check diff calculation
        old_snapshot = storage.get_json("today_sheet_snapshot")
        old_cats = old_snapshot["categories"]
        new_cats = {"រដ្ឋបាលសាធារណៈ": 10, "ទីផ្សារឌីជីថល": 1, "ក្រាហ្វិកឌីហ្សាញ": 2}

        changes = []
        for cat_name, new_val in new_cats.items():
            old_val = old_cats.get(cat_name, 0)
            if new_val != old_val:
                changes.append({"name": cat_name, "old": old_val, "new": new_val})

        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]["name"], "រដ្ឋបាលសាធារណៈ")
        self.assertEqual(changes[0]["new"] - changes[0]["old"], 2)
        self.assertEqual(changes[1]["name"], "ក្រាហ្វិកឌីហ្សាញ")
        self.assertEqual(changes[1]["new"] - changes[1]["old"], 2)

        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass
        print("PASS: Test 06: Diff logic correctly detected category modifications and new additions")

    def test_07_status_gender_summary(self):
        """Test parsing and HTML formatting of applicant summary with gender breakdown."""
        client = SheetsClient()
        reg_rows = client.get_registrations_sheet_rows()
        self.assertGreater(len(reg_rows), 10)

        # 1. Overall cumulative summary
        overall = parse_status_gender_summary(reg_rows, target_date="all")
        self.assertTrue(overall.is_overall)
        self.assertEqual(overall.total_applied, 44)
        self.assertEqual(overall.female_applied, 21)
        self.assertEqual(overall.total_arrived, 18)
        self.assertEqual(overall.female_arrived, 5)
        self.assertEqual(overall.total_returned, 25)
        self.assertEqual(overall.female_returned, 16)
        self.assertEqual(overall.total_dropped, 1)
        self.assertEqual(overall.female_dropped, 0)

        # 2. Specific date summary
        date_sum = parse_status_gender_summary(reg_rows, target_date="10/Sep/2026")
        self.assertFalse(date_sum.is_overall)
        self.assertEqual(date_sum.total_applied, 19)
        self.assertEqual(date_sum.female_applied, 5)
        self.assertEqual(date_sum.total_arrived, 8)
        self.assertEqual(date_sum.female_arrived, 1)
        self.assertEqual(date_sum.total_returned, 10)
        self.assertEqual(date_sum.female_returned, 4)
        self.assertEqual(date_sum.total_dropped, 1)
        self.assertEqual(date_sum.female_dropped, 0)

        # 3. HTML validation for Telegram
        overall_html = format_status_summary_report(overall)
        self.assertTrue(validate_telegram_html(overall_html), "Overall summary HTML must be valid Telegram HTML")
        self.assertIn("ដាក់ពាក្យសរុប", overall_html)
        self.assertIn("ស្រី", overall_html)
        self.assertIn("មកដល់", overall_html)
        self.assertIn("ទៅផ្ទះវិញ", overall_html)
        self.assertIn("បោះបង់", overall_html)

        date_html = format_status_summary_report(date_sum, overall=overall)
        self.assertTrue(validate_telegram_html(date_html), "Date summary HTML with overall footnote must be valid Telegram HTML")
        self.assertIn("ដាក់ពាក្យសរុប", date_html)

        print(f"PASS: Test 07: Status gender summary successfully verified (All: {overall.total_applied} applied, {overall.female_applied} female, {overall.total_arrived} arrived, {overall.total_returned} returned, {overall.total_dropped} dropped)")

    def test_08_daily_report_under_status_this_day(self):
        """Test that daily report arrival/returned/dropped status only displays this day's counts, not all-time cumulative."""
        from src.parser import count_registration_statuses, parse_date_report
        client = SheetsClient()
        reg_rows = client.get_registrations_sheet_rows()
        today_rows = client.get_today_sheet_rows()
        hist_rows = client.get_historical_sheet_rows()

        # 1. Today counts should reflect today (0, 0, 0), NOT all-time (18, 25, 1)
        today_counts = count_registration_statuses(reg_rows, "today")
        self.assertEqual(today_counts, (0, 0, 0))

        today_data = parse_today_sheet(today_rows, reg_rows=reg_rows)
        self.assertEqual(today_data.total_arrived, 0)
        self.assertEqual(today_data.total_returned, 0)
        self.assertEqual(today_data.total_dropped, 0)

        daily_html = format_daily_report(today_data)
        self.assertIn("[ មកដល់: 0 | ត្រឡប់ទៅវិញ: 0 | បោះបង់: 0 ]", daily_html)
        self.assertNotIn("[ មកដល់: 18 | ត្រឡប់ទៅវិញ: 25 | បោះបង់: 1 ]", daily_html)

        # 2. Specific date (10/Sep/2026) has (8, 10, 1)
        d10_counts = count_registration_statuses(reg_rows, "10/Sep/2026")
        self.assertEqual(d10_counts, (8, 10, 1))

        d10_data = parse_date_report(hist_rows, today_rows, "10/Sep/2026", reg_rows=reg_rows)
        self.assertEqual(d10_data.total_arrived, 8)
        self.assertEqual(d10_data.total_returned, 10)
        self.assertEqual(d10_data.total_dropped, 1)
        d10_html = format_daily_report(d10_data)
        self.assertIn("[ មកដល់: 8 | ត្រឡប់ទៅវិញ: 10 | បោះបង់: 1 ]", d10_html)

        # 3. Specific date (14/Sep/2026) has (0, 4, 0)
        d14_counts = count_registration_statuses(reg_rows, "14/Sep/2026")
        self.assertEqual(d14_counts, (0, 4, 0))

        # 4. Cumulative "all" should return the full cumulative counts
        all_counts = count_registration_statuses(reg_rows, "all")
        self.assertEqual(all_counts, (18, 25, 1))

        print("PASS: Test 08: Daily report 'under' status accurately displays only this day's data")

if __name__ == "__main__":
    unittest.main()
