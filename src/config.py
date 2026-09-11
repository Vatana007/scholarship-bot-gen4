import os
import logging
from logging.handlers import RotatingFileHandler
import pytz
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
REPORT_CHAT_ID_STR = os.getenv("REPORT_CHAT_ID", "").strip()
try:
    REPORT_CHAT_ID = int(REPORT_CHAT_ID_STR) if REPORT_CHAT_ID_STR else None
except ValueError:
    REPORT_CHAT_ID = None

ALLOWED_CHAT_IDS_STR = os.getenv("ALLOWED_CHAT_IDS", "").strip()
ALLOWED_CHAT_IDS = set()
if ALLOWED_CHAT_IDS_STR:
    for cid in ALLOWED_CHAT_IDS_STR.split(","):
        cid = cid.strip()
        if cid:
            try:
                ALLOWED_CHAT_IDS.add(int(cid))
            except ValueError:
                pass
if REPORT_CHAT_ID:
    ALLOWED_CHAT_IDS.add(REPORT_CHAT_ID)

# Google Sheets Config
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "14XY1kCjb8znDeKWLqYrPJJhH2P7BQwo9ciqeRlh8qC8").strip()
TODAY_SHEET_NAME = os.getenv("TODAY_SHEET_NAME", "ស្ថិតិថ្ងៃនឹង").strip()
TODAY_SHEET_GID = os.getenv("TODAY_SHEET_GID", "330658001").strip()
HISTORICAL_SHEET_NAME = os.getenv("HISTORICAL_SHEET_NAME", "ស្ថិតិប្រចាំថ្ងៃ").strip()
HISTORICAL_SHEET_GID = os.getenv("HISTORICAL_SHEET_GID", "360162816").strip()
REGISTRATIONS_SHEET_NAME = os.getenv("REGISTRATIONS_SHEET_NAME", "Part 2 -Registrations").strip()
REGISTRATIONS_SHEET_GID = os.getenv("REGISTRATIONS_SHEET_GID", "987839961").strip()
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH", "credentials/service_account.json").strip()

# Timezone & Schedule
TIMEZONE_STR = os.getenv("TIMEZONE", "Asia/Phnom_Penh").strip()
try:
    TIMEZONE = pytz.timezone(TIMEZONE_STR)
except Exception:
    TIMEZONE = pytz.timezone("Asia/Phnom_Penh")

DAILY_REPORT_TIME = os.getenv("DAILY_REPORT_TIME", "17:00").strip()
MONTHLY_REPORT_DAY = int(os.getenv("MONTHLY_REPORT_DAY", "1").strip())
MONTHLY_REPORT_TIME = os.getenv("MONTHLY_REPORT_TIME", "08:00").strip()

# Watcher Config
POLLING_INTERVAL_SECONDS = int(os.getenv("POLLING_INTERVAL_SECONDS", "60").strip())

# Paths
BASE_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_PROJECT_DIR, "data")
LOG_DIR = os.path.join(BASE_PROJECT_DIR, "logs")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "state.db")
LOG_PATH = os.path.join(LOG_DIR, "bot.log")

# Setup Logging
logger = logging.getLogger("telegram_bot")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(LOG_PATH, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Suppress noisy library logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)

# Admin PIN for Web UI management (default: 123456)
ADMIN_PIN = os.getenv("ADMIN_PIN", "123456").strip()

def is_chat_allowed(chat_id: int) -> bool:
    """Checks if a Telegram chat ID is authorized to run bot commands."""
    if not ALLOWED_CHAT_IDS:
        return True  # If not configured, allow all
    return chat_id in ALLOWED_CHAT_IDS

def get_runtime_config_dict() -> dict:
    """Returns the current active configuration as a dictionary."""
    return {
        "REPORT_CHAT_ID": str(REPORT_CHAT_ID or ""),
        "ALLOWED_CHAT_IDS": ",".join(str(c) for c in ALLOWED_CHAT_IDS),
        "SPREADSHEET_ID": SPREADSHEET_ID,
        "TODAY_SHEET_NAME": TODAY_SHEET_NAME,
        "TODAY_SHEET_GID": TODAY_SHEET_GID,
        "HISTORICAL_SHEET_NAME": HISTORICAL_SHEET_NAME,
        "HISTORICAL_SHEET_GID": HISTORICAL_SHEET_GID,
        "REGISTRATIONS_SHEET_NAME": REGISTRATIONS_SHEET_NAME,
        "REGISTRATIONS_SHEET_GID": REGISTRATIONS_SHEET_GID,
        "TIMEZONE": TIMEZONE_STR,
        "DAILY_REPORT_TIME": DAILY_REPORT_TIME,
        "MONTHLY_REPORT_DAY": str(MONTHLY_REPORT_DAY),
        "MONTHLY_REPORT_TIME": MONTHLY_REPORT_TIME,
        "POLLING_INTERVAL_SECONDS": str(POLLING_INTERVAL_SECONDS),
        "ADMIN_PIN": ADMIN_PIN
    }

def apply_runtime_settings(new_settings: dict):
    """Updates global in-memory settings from a dictionary."""
    global REPORT_CHAT_ID, ALLOWED_CHAT_IDS, SPREADSHEET_ID, TODAY_SHEET_NAME
    global TODAY_SHEET_GID, HISTORICAL_SHEET_NAME, HISTORICAL_SHEET_GID
    global REGISTRATIONS_SHEET_NAME, REGISTRATIONS_SHEET_GID
    global DAILY_REPORT_TIME, MONTHLY_REPORT_DAY, MONTHLY_REPORT_TIME, POLLING_INTERVAL_SECONDS, ADMIN_PIN

    if "REPORT_CHAT_ID" in new_settings and new_settings["REPORT_CHAT_ID"].strip():
        try:
            REPORT_CHAT_ID = int(new_settings["REPORT_CHAT_ID"].strip())
            ALLOWED_CHAT_IDS.add(REPORT_CHAT_ID)
        except ValueError:
            pass

    if "ALLOWED_CHAT_IDS" in new_settings:
        cids = set()
        for cid in new_settings["ALLOWED_CHAT_IDS"].split(","):
            cid = cid.strip()
            if cid:
                try:
                    cids.add(int(cid))
                except ValueError:
                    pass
        if REPORT_CHAT_ID:
            cids.add(REPORT_CHAT_ID)
        ALLOWED_CHAT_IDS = cids

    if "SPREADSHEET_ID" in new_settings and new_settings["SPREADSHEET_ID"].strip():
        SPREADSHEET_ID = new_settings["SPREADSHEET_ID"].strip()

    if "TODAY_SHEET_GID" in new_settings and new_settings["TODAY_SHEET_GID"].strip():
        TODAY_SHEET_GID = new_settings["TODAY_SHEET_GID"].strip()

    if "HISTORICAL_SHEET_GID" in new_settings and new_settings["HISTORICAL_SHEET_GID"].strip():
        HISTORICAL_SHEET_GID = new_settings["HISTORICAL_SHEET_GID"].strip()

    if "REGISTRATIONS_SHEET_GID" in new_settings and new_settings["REGISTRATIONS_SHEET_GID"].strip():
        REGISTRATIONS_SHEET_GID = new_settings["REGISTRATIONS_SHEET_GID"].strip()

    if "DAILY_REPORT_TIME" in new_settings and new_settings["DAILY_REPORT_TIME"].strip():
        DAILY_REPORT_TIME = new_settings["DAILY_REPORT_TIME"].strip()

    if "MONTHLY_REPORT_DAY" in new_settings and new_settings["MONTHLY_REPORT_DAY"].strip():
        try:
            MONTHLY_REPORT_DAY = int(new_settings["MONTHLY_REPORT_DAY"].strip())
        except ValueError:
            pass

    if "MONTHLY_REPORT_TIME" in new_settings and new_settings["MONTHLY_REPORT_TIME"].strip():
        MONTHLY_REPORT_TIME = new_settings["MONTHLY_REPORT_TIME"].strip()

    if "POLLING_INTERVAL_SECONDS" in new_settings and new_settings["POLLING_INTERVAL_SECONDS"].strip():
        try:
            POLLING_INTERVAL_SECONDS = int(new_settings["POLLING_INTERVAL_SECONDS"].strip())
        except ValueError:
            pass

    if "ADMIN_PIN" in new_settings and new_settings["ADMIN_PIN"].strip():
        ADMIN_PIN = new_settings["ADMIN_PIN"].strip()

    logger.info("Runtime settings successfully updated in memory.")

