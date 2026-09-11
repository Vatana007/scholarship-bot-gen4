import asyncio
from src.config import POLLING_INTERVAL_SECONDS, REPORT_CHAT_ID, logger
from src.sheets_client import SheetsClient
from src.parser import parse_today_sheet, parse_student_registrations
from src.storage import Storage
from src.report_builder import format_diff_alert, format_new_registration_alert

class ChangeWatcher:
    def __init__(self, bot, sheets_client: SheetsClient, storage: Storage):
        self.bot = bot
        self.sheets_client = sheets_client
        self.storage = storage
        self.is_running = False
        self.is_paused = (self.storage.get_setting("bot_paused") == "true")

    def pause(self):
        self.is_paused = True
        self.storage.set_setting("bot_paused", "true")
        logger.info("Bot alerts and watcher PAUSED.")

    def resume(self):
        self.is_paused = False
        self.storage.set_setting("bot_paused", "false")
        logger.info("Bot alerts and watcher RESUMED.")

    async def start(self):
        self.is_running = True
        logger.info(f"Real-time change watcher started (polling every {POLLING_INTERVAL_SECONDS}s).")
        
        # Prime initial state for Today Sheet without sending alert
        try:
            rows = self.sheets_client.get_today_sheet_rows()
            data = parse_today_sheet(rows)
            prev_hash = self.storage.get("today_sheet_hash")
            if not prev_hash:
                self.storage.set("today_sheet_hash", data.data_hash)
                self.storage.set_json("today_sheet_snapshot", {
                    "grand_total": data.grand_total,
                    "categories": {c.name: c.registered for c in data.categories},
                    "sources": data.sources_summary
                })
                logger.info(f"Initialized base state for sheet hash: {data.data_hash[:8]}...")
        except Exception as e:
            logger.error(f"Error priming today sheet watcher state: {e}")

        # Prime initial state for 'Part 2 -Registrations' without sending alerts
        try:
            known_reg_keys = self.storage.get_json("known_reg_keys")
            if known_reg_keys is None:
                reg_rows = self.sheets_client.get_registrations_sheet_rows(force_refresh=True)
                students = parse_student_registrations(reg_rows)
                initial_keys = [s["key"] for s in students]
                self.storage.set_json("known_reg_keys", initial_keys)
                logger.info(f"Initialized base state for {len(initial_keys)} registered students in 'Part 2 -Registrations'.")
            else:
                logger.info(f"Loaded {len(known_reg_keys)} known registration keys from storage.")
        except Exception as e:
            logger.error(f"Error priming registrations watcher state: {e}")

        while self.is_running:
            try:
                await asyncio.sleep(POLLING_INTERVAL_SECONDS)
                await self.check_for_changes()
                await self.check_for_new_registrations()
            except asyncio.CancelledError:
                logger.info("Change watcher task was cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in change watcher loop: {e}")

    def stop(self):
        self.is_running = False

    async def check_for_changes(self, is_manual: bool = False):
        if not is_manual and self.is_paused:
            return
        if not REPORT_CHAT_ID:
            return

        try:
            rows = self.sheets_client.get_today_sheet_rows()
            curr_data = parse_today_sheet(rows)
            curr_hash = curr_data.data_hash

            last_hash = self.storage.get("today_sheet_hash")
            if not last_hash:
                # First time seeing data
                self.storage.set("today_sheet_hash", curr_hash)
                self.storage.set_json("today_sheet_snapshot", {
                    "grand_total": curr_data.grand_total,
                    "categories": {c.name: c.registered for c in curr_data.categories},
                    "sources": curr_data.sources_summary
                })
                return

            if curr_hash == last_hash:
                return  # No changes detected

            logger.info("Google Sheet change detected! Calculating differences...")

            last_snapshot = self.storage.get_json("today_sheet_snapshot", {})
            old_cats = last_snapshot.get("categories", {})
            old_total = last_snapshot.get("grand_total", 0)

            changes = []
            for cat in curr_data.categories:
                old_val = old_cats.get(cat.name, 0)
                if cat.registered != old_val:
                    changes.append({
                        "name": cat.name,
                        "old": old_val,
                        "new": cat.registered
                    })

            # Also check if any category disappeared
            curr_cat_names = {c.name for c in curr_data.categories}
            for name, old_val in old_cats.items():
                if name not in curr_cat_names and old_val > 0:
                    changes.append({
                        "name": name,
                        "old": old_val,
                        "new": 0
                    })

            if changes:
                # Diff alerts for general category changes are muted per user request (alerts only for individual students)
                logger.info(f"Google Sheet today changes recorded ({len(changes)} changes). Diff push alert muted per user preference.")

            # Update stored state
            self.storage.set("today_sheet_hash", curr_hash)
            self.storage.set_json("today_sheet_snapshot", {
                "grand_total": curr_data.grand_total,
                "categories": {c.name: c.registered for c in curr_data.categories},
                "sources": curr_data.sources_summary
            })

        except Exception as e:
            logger.error(f"Error checking for changes: {e}")

    async def check_for_new_registrations(self, is_manual: bool = False):
        """
        Monitors 'Part 2 -Registrations' sheet.
        When new students (new names/keys) are detected, sends an instant alert to Telegram.
        """
        if not is_manual and self.is_paused:
            return
        if not REPORT_CHAT_ID or not self.bot:
            return

        try:
            reg_rows = self.sheets_client.get_registrations_sheet_rows(force_refresh=True)
            students = parse_student_registrations(reg_rows)
            if not students:
                return

            stored_keys = self.storage.get_json("known_reg_keys")
            if stored_keys is None:
                # First time initialization
                initial_keys = [s["key"] for s in students]
                self.storage.set_json("known_reg_keys", initial_keys)
                logger.info(f"Initialized registration keys ({len(initial_keys)} students).")
                return

            known_keys_set = set(stored_keys)
            new_students = [s for s in students if s["key"] not in known_keys_set]

            if not new_students:
                return

            logger.info(f"Detected {len(new_students)} new student registration(s)! Sending Telegram alerts...")

            for student in new_students:
                alert_text = format_new_registration_alert(student)
                try:
                    await self.bot.send_message(
                        chat_id=REPORT_CHAT_ID,
                        text=alert_text,
                        parse_mode="HTML"
                    )
                    logger.info(f"New registration alert sent for '{student.get('name')}' ({student.get('skill')}) to chat {REPORT_CHAT_ID}")
                except Exception as e:
                    logger.error(f"Failed to send new registration alert for '{student.get('name')}': {e}")

                known_keys_set.add(student["key"])
                # Small pause to avoid Telegram rate limits if multiple students arrive at once
                await asyncio.sleep(0.5)

            # Persist updated keys
            self.storage.set_json("known_reg_keys", list(known_keys_set))

        except Exception as e:
            logger.error(f"Error checking for new registrations: {e}")

    async def send_test_registration_alert(self, chat_id: int = None, custom_student: dict = None) -> bool:
        """
        Sends a test registration alert to verify Telegram formatting and delivery.
        """
        target_chat = chat_id or REPORT_CHAT_ID
        if not target_chat or not self.bot:
            logger.warning("Cannot send test registration alert: bot or chat_id not configured.")
            return False

        if custom_student:
            student = custom_student
        else:
            try:
                reg_rows = self.sheets_client.get_registrations_sheet_rows()
                students = parse_student_registrations(reg_rows)
                student = students[-1] if students else None
            except Exception:
                student = None

            if not student:
                student = {
                    "name": "ជន លិញលិញ",
                    "latang": "CHORN LINHLINH",
                    "gender": "ស្រី",
                    "phone": "0887490135",
                    "pob": "ស្រុកឯកភ្នំ ខេត្តបាត់ដំបង",
                    "skill": "ក្រាហ្វិកឌីហ្សាញ"
                }

        alert_text = format_new_registration_alert(student)
        try:
            await self.bot.send_message(
                chat_id=target_chat,
                text=alert_text,
                parse_mode="HTML"
            )
            logger.info(f"Test registration alert sent to chat {target_chat}")
            return True
        except Exception as e:
            logger.error(f"Failed to send test registration alert: {e}")
            return False

