import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
import src.config as config
from src.config import (
    BOT_TOKEN, is_chat_allowed, REPORT_CHAT_ID, TIMEZONE, logger
)
from src.sheets_client import SheetsClient
from src.storage import Storage
from src.parser import parse_today_sheet, parse_historical_sheet
from src.report_builder import (
    format_daily_report, format_monthly_report, format_categories_page,
    format_help, format_welcome, get_report_keyboard, DIVIDER
)
from src.change_watcher import ChangeWatcher
from src.scheduler import BotScheduler
from src.web_server import start_web_server_background, init_web_context

sheets_client = SheetsClient()
storage = Storage()
watcher = None
scheduler = None

# Load persistent settings from database on startup
saved_settings = storage.get_all_settings()
if saved_settings:
    config.apply_runtime_settings(saved_settings)
    logger.info(f"Loaded {len(saved_settings)} persistent settings from database.")

async def check_access(update: Update) -> bool:

    chat_id = update.effective_chat.id
    if not is_chat_allowed(chat_id):
        await update.effective_message.reply_text(
            "⛔️ <b>សូមអភ័យទោស!</b> លោកអ្នកមិនមានសិទ្ធិចូលមើលទិន្នន័យស្ថិតិនេះទេ។",
            parse_mode="HTML"
        )
        logger.warning(f"Unauthorized command attempt from Chat ID: {chat_id}")
        return False
    return True

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    text = format_welcome()
    keyboard = [
        [
            InlineKeyboardButton("📊 ស្ថិតិថ្ងៃនេះ", callback_data="action_today"),
            InlineKeyboardButton("📅 របាយការណ៍ប្រចាំខែ", callback_data="action_monthly")
        ],
        [
            InlineKeyboardButton("📂 បញ្ជីមុខជំនាញទាំងអស់", callback_data="action_categories_p1"),
            InlineKeyboardButton("📖 ជំនួយ (Help)", callback_data="action_help")
        ]
    ]
    await update.effective_message.reply_text(
        text=text,
        parse_mode="HTML"
    )

async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    target_date = "today"
    if context and context.args and len(context.args) > 0:
        target_date = context.args[0].strip()

    status_msg = await update.effective_message.reply_text("⏳ កំពុងទាញយកទិន្នន័យ...")
    try:
        from src.parser import parse_date_report
        t_rows = sheets_client.get_today_sheet_rows()
        h_rows = sheets_client.get_historical_sheet_rows()
        reg_rows = sheets_client.get_registrations_sheet_rows()
        data = parse_date_report(h_rows, t_rows, target_date, reg_rows=reg_rows)
        text = format_daily_report(data)
        await status_msg.edit_text(text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /today: {e}")
        await status_msg.edit_text(f"❌ បរាជ័យក្នុងការទាញទិន្នន័យ៖ {e}")

async def monthly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    status_msg = await update.effective_message.reply_text("⏳ កំពុងទាញយកទិន្នន័យ និងរៀបចំឯកសារ PDF ប្រចាំខែ...")
    try:
        from src.report_builder import KHMER_MONTHS, to_khmer_num, format_monthly_report
        rows = sheets_client.get_historical_sheet_rows()
        reg_rows = sheets_client.get_registrations_sheet_rows()
        hist_data = parse_historical_sheet(rows, reg_rows=reg_rows)

        pdf_path = None
        try:
            from src.pdf_generator import generate_monthly_report_pdf
            pdf_path = generate_monthly_report_pdf(hist_data, force_refresh=True)
        except Exception as pdf_err:
            logger.warning(f"Browser PDF generation failed/unavailable: {pdf_err}. Falling back to formatted text report.")

        if pdf_path and os.path.exists(pdf_path):
            now = datetime.now(TIMEZONE)
            dropped_caption = f"បោះបង់ <b>{hist_data.total_dropped}</b> នាក់" if hist_data.total_dropped > 0 else ""
            female_caption = f"ស្រី <b>{hist_data.total_female}</b> នាក់" if hist_data.total_female > 0 else ""
            extra_parts = [p for p in [dropped_caption, female_caption] if p]
            extra_str = f" ({' • '.join(extra_parts)})" if extra_parts else ""
            caption = f"📈 <b>របាយការណ៍ស្ថិតិប្រចាំខែ (Monthly Report PDF)</b>\n🗓 <b>ខែ{KHMER_MONTHS.get(now.month, 'កញ្ញា')} ឆ្នាំ {to_khmer_num(now.year)}</b>\n👥 និស្សិតដាក់ពាក្យសរុប៖ <b>{hist_data.grand_total} នាក់</b>{extra_str}"
            await status_msg.delete()
            with open(pdf_path, "rb") as doc:
                await update.effective_message.reply_document(
                    document=doc,
                    filename=f"Monthly_Scholarship_Report_{now.year}_{now.month:02d}.pdf",
                    caption=caption,
                    parse_mode="HTML"
                )
        else:
            # Seamless fallback to rich formatted text report
            text = format_monthly_report(hist_data)
            await status_msg.edit_text(text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /monthly: {e}")
        await update.effective_message.reply_text(f"❌ បរាជ័យក្នុងការទាញទិន្នន័យប្រចាំខែ៖ {e}")

async def categories_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    status_msg = await update.effective_message.reply_text("⏳ កំពុងរៀបចំបញ្ជីមុខជំនាញ...")
    try:
        rows = sheets_client.get_today_sheet_rows()
        data = parse_today_sheet(rows)
        import html
        lines = ["📂 <b>បញ្ជីមុខជំនាញទាំងអស់</b>", DIVIDER]
        for idx, cat in enumerate(data.categories, 1):
            lines.append(f"{idx}. <b>{html.escape(cat.name)}</b>: <code>{cat.registered} នាក់</code>")
        await status_msg.edit_text(text="\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error in /categories: {e}")
        await status_msg.edit_text(f"❌ មានបញ្ហាក្នុងការទាញទិន្នន័យ៖ {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    text = format_help()
    await update.effective_message.reply_text(text=text, parse_mode="HTML")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_chat_allowed(update.effective_chat.id):
        await query.edit_message_text("⛔️ គ្មានសិទ្ធិចូលប្រើប្រាស់ទេ។")
        return

    data = query.data

    try:
        if data in ["action_today", "action_refresh"]:
            rows = sheets_client.get_today_sheet_rows()
            reg_rows = sheets_client.get_registrations_sheet_rows()
            parsed = parse_today_sheet(rows, reg_rows=reg_rows)
            text = format_daily_report(parsed, show_all=False)
            markup = get_report_keyboard("daily")
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=markup)

        elif data == "action_show_all":
            rows = sheets_client.get_today_sheet_rows()
            reg_rows = sheets_client.get_registrations_sheet_rows()
            parsed = parse_today_sheet(rows, reg_rows=reg_rows)
            text = format_daily_report(parsed, show_all=True)
            markup = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 ធ្វើបច្ចុប្បន្នភាព", callback_data="action_refresh"),
                    InlineKeyboardButton("🔹 បង្ហាញតែជំនាញមានទិន្នន័យ", callback_data="action_today")
                ],
                [InlineKeyboardButton("📅 មើលប្រចាំខែ", callback_data="action_monthly")]
            ])
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=markup)

        elif data == "action_monthly":
            from src.pdf_generator import generate_monthly_report_pdf
            from src.report_builder import KHMER_MONTHS, to_khmer_num
            await query.answer("⏳ កំពុងរៀបចំឯកសារ PDF...")
            rows = sheets_client.get_historical_sheet_rows()
            reg_rows = sheets_client.get_registrations_sheet_rows()
            hist_data = parse_historical_sheet(rows, reg_rows=reg_rows)
            pdf_path = generate_monthly_report_pdf(hist_data, force_refresh=True)
            now = datetime.now(TIMEZONE)
            dropped_caption = f"បោះបង់ <b>{hist_data.total_dropped}</b> នាក់" if hist_data.total_dropped > 0 else ""
            female_caption = f"ស្រី <b>{hist_data.total_female}</b> នាក់" if hist_data.total_female > 0 else ""
            extra_parts = [p for p in [dropped_caption, female_caption] if p]
            extra_str = f" ({' • '.join(extra_parts)})" if extra_parts else ""
            caption = (
                f"📈 <b>របាយការណ៍ស្ថិតិប្រចាំខែ (Monthly Report PDF)</b>\n"
                f"🗓 <b>ខែ{KHMER_MONTHS.get(now.month, 'កញ្ញា')} ឆ្នាំ {to_khmer_num(now.year)}</b>\n"
                f"👥 និស្សិតដាក់ពាក្យសរុប៖ <b>{hist_data.grand_total} នាក់</b>{extra_str}"
            )
            with open(pdf_path, "rb") as doc:
                await query.message.reply_document(
                    document=doc,
                    filename=f"Monthly_Scholarship_Report_{now.year}_{now.month:02d}.pdf",
                    caption=caption,
                    parse_mode="HTML"
                )

        elif data == "action_help":
            text = format_help()
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ", callback_data="action_start")]
            ])
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=markup)

        elif data == "action_start":
            text = format_welcome()
            keyboard = [
                [
                    InlineKeyboardButton("📊 ស្ថិតិថ្ងៃនេះ", callback_data="action_today"),
                    InlineKeyboardButton("📅 របាយការណ៍ប្រចាំខែ", callback_data="action_monthly")
                ],
                [
                    InlineKeyboardButton("📂 បញ្ជីមុខជំនាញទាំងអស់", callback_data="action_categories_p1"),
                    InlineKeyboardButton("📖 ជំនួយ (Help)", callback_data="action_help")
                ]
            ]
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("action_cat_p_") or data == "action_categories_p1":
            page = 1
            if data.startswith("action_cat_p_"):
                try:
                    page = int(data.split("_")[-1])
                except ValueError:
                    page = 1
            rows = sheets_client.get_today_sheet_rows()
            parsed = parse_today_sheet(rows)
            text, markup = format_categories_page(parsed.categories, page=page)
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        logger.error(f"Callback query error ({data}): {e}")
        await query.answer(f"មានបញ្ហា៖ {e}", show_alert=True)

async def post_init(application):
    global watcher, scheduler
    # Start APScheduler
    scheduler = BotScheduler(application.bot, sheets_client, storage)
    scheduler.start()

    # Start Real-time Change Watcher as async background task
    watcher = ChangeWatcher(application.bot, sheets_client, storage)
    asyncio.create_task(watcher.start())

    # Connect web management context with bot and scheduler
    loop = asyncio.get_running_loop()
    init_web_context(application.bot, scheduler, watcher, loop)
    logger.info("Bot background jobs (Scheduler & Watcher) and Web Management initialized.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles exceptions and gracefully suppresses transient deploy conflict errors."""
    import telegram.error
    if isinstance(context.error, telegram.error.Conflict):
        logger.warning(
            "Telegram polling conflict detected (temporary overlap during Render deploy). "
            "Polling will resume automatically once previous container stops."
        )
        return
    logger.error("Exception while handling an update:", exc_info=context.error)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in .env! Please configure it.")
        return

    logger.info("Starting Telegram Registration Statistics Bot...")

    # Start Web Dashboard & Health server for Render / Web access
    start_web_server_background()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler(["start"], start_cmd))
    app.add_handler(CommandHandler(["today"], today_cmd))
    app.add_handler(CommandHandler(["report", "daily"], today_cmd))
    app.add_handler(CommandHandler(["monthly"], monthly_cmd))
    app.add_handler(CommandHandler(["categories"], categories_cmd))
    app.add_handler(CommandHandler(["help"], help_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Bot handlers registered. Starting polling...")
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
