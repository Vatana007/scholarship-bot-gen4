from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src import config
from src.config import logger
from src.sheets_client import SheetsClient
from src.parser import parse_today_sheet, parse_historical_sheet
from src.storage import Storage
from src.report_builder import format_daily_report, format_monthly_report, get_report_keyboard

class BotScheduler:
    def __init__(self, bot, sheets_client: SheetsClient, storage: Storage):
        self.bot = bot
        self.sheets_client = sheets_client
        self.storage = storage
        self.scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)

    def _schedule_jobs(self):
        # Parse Daily Report Time (default 17:00 / 5:00 PM)
        try:
            dh, dm = config.DAILY_REPORT_TIME.split(":")
            daily_hour = int(dh)
            daily_minute = int(dm)
        except Exception:
            daily_hour, daily_minute = 17, 0

        # Parse Monthly Report Time (e.g. 08:00)
        try:
            mh, mm = config.MONTHLY_REPORT_TIME.split(":")
            monthly_hour = int(mh)
            monthly_minute = int(mm)
        except Exception:
            monthly_hour, monthly_minute = 8, 0

        # Schedule Daily Job
        self.scheduler.add_job(
            self.send_daily_scheduled_report,
            trigger=CronTrigger(hour=daily_hour, minute=daily_minute, timezone=config.TIMEZONE),
            id="daily_report_job",
            name="Daily Registration Report",
            replace_existing=True
        )
        logger.info(f"Scheduled Daily Report at {daily_hour:02d}:{daily_minute:02d} ({config.TIMEZONE}).")

        # Schedule Monthly Job (e.g. 1st of every month at 08:00)
        self.scheduler.add_job(
            self.send_monthly_scheduled_report,
            trigger=CronTrigger(day=config.MONTHLY_REPORT_DAY, hour=monthly_hour, minute=monthly_minute, timezone=config.TIMEZONE),
            id="monthly_report_job",
            name="Monthly Registration Rollup",
            replace_existing=True
        )
        logger.info(f"Scheduled Monthly Report on day {config.MONTHLY_REPORT_DAY} at {monthly_hour:02d}:{monthly_minute:02d} ({config.TIMEZONE}).")

    def start(self):
        self._schedule_jobs()
        self.scheduler.start()

    def reschedule(self):
        self._schedule_jobs()
        logger.info("Scheduler jobs successfully reloaded with updated times.")

    def shutdown(self):
        self.scheduler.shutdown()

    async def send_daily_scheduled_report(self):
        if self.storage.get_setting("bot_paused") == "true":
            logger.info("Bot auto-reports are paused. Skipping scheduled daily report.")
            return

        if not config.REPORT_CHAT_ID:
            logger.warning("REPORT_CHAT_ID not configured; skipping daily report.")
            return

        today_key = datetime.now(config.TIMEZONE).strftime("%Y-%m-%d")
        if self.storage.is_report_sent("DAILY", today_key):
            logger.info(f"Daily report for {today_key} already sent. Skipping.")
            return

        logger.info(f"Triggering scheduled daily report for {today_key}...")
        try:
            rows = self.sheets_client.get_today_sheet_rows()
            reg_rows = self.sheets_client.get_registrations_sheet_rows()
            data = parse_today_sheet(rows, reg_rows=reg_rows)
            text = format_daily_report(data)
            markup = get_report_keyboard("daily")

            msg = await self.bot.send_message(
                chat_id=config.REPORT_CHAT_ID,
                text=text,
                parse_mode="HTML"
            )
            self.storage.log_report_sent("DAILY", today_key, message_id=msg.message_id)
            logger.info(f"Scheduled daily report sent successfully (Message ID: {msg.message_id}).")
        except Exception as e:
            logger.error(f"Error sending scheduled daily report: {e}")

    async def send_monthly_scheduled_report(self):
        if self.storage.get_setting("bot_paused") == "true":
            logger.info("Bot auto-reports are paused. Skipping scheduled monthly report.")
            return

        if not config.REPORT_CHAT_ID:
            logger.warning("REPORT_CHAT_ID not configured; skipping monthly report.")
            return

        month_key = datetime.now(config.TIMEZONE).strftime("%Y-%m")
        if self.storage.is_report_sent("MONTHLY", month_key):
            logger.info(f"Monthly report for {month_key} already sent. Skipping.")
            return

        logger.info(f"Triggering scheduled monthly report for {month_key}...")
        try:
            from src.pdf_generator import generate_monthly_report_pdf
            from src.report_builder import KHMER_MONTHS, to_khmer_num
            rows = self.sheets_client.get_historical_sheet_rows()
            reg_rows = self.sheets_client.get_registrations_sheet_rows()
            hist_data = parse_historical_sheet(rows, reg_rows=reg_rows)
            pdf_path = generate_monthly_report_pdf(hist_data, force_refresh=True)
            now = datetime.now(config.TIMEZONE)
            female_caption = f" (ស្រី <b>{hist_data.total_female}</b> នាក់)" if hist_data.total_female > 0 else ""
            caption = f"📈 <b>របាយការណ៍ស្ថិតិប្រចាំខែ (Monthly Report PDF)</b>\n🗓 <b>ខែ{KHMER_MONTHS.get(now.month, 'កញ្ញា')} ឆ្នាំ {to_khmer_num(now.year)}</b>\n👥 និស្សិតដាក់ពាក្យសរុប៖ <b>{hist_data.grand_total} នាក់</b>{female_caption}"

            with open(pdf_path, "rb") as doc:
                msg = await self.bot.send_document(
                    chat_id=config.REPORT_CHAT_ID,
                    document=doc,
                    filename=f"Monthly_Scholarship_Report_{now.year}_{now.month:02d}.pdf",
                    caption=caption,
                    parse_mode="HTML"
                )
            self.storage.log_report_sent("MONTHLY_PDF", month_key, message_id=msg.message_id)
            logger.info(f"Scheduled monthly PDF report sent successfully (Message ID: {msg.message_id}).")
        except Exception as e:
            logger.error(f"Error sending scheduled monthly PDF report: {e}")
