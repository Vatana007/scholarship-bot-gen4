import html
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.parser import TodayReportData, HistoricalReportData

DIVIDER = "──────────"

KHMER_NUMS = {
    '0': '០', '1': '១', '2': '២', '3': '៣', '4': '៤',
    '5': '៥', '6': '៦', '7': '៧', '8': '៨', '9': '៩'
}

KHMER_MONTHS = {
    1: "មករា", 2: "កុម្ភៈ", 3: "មីនា", 4: "មេសា",
    5: "ឧសភា", 6: "មិថុនា", 7: "កក្កដា", 8: "សីហា",
    9: "កញ្ញា", 10: "តុលា", 11: "វិច្ឆិកា", 12: "ធ្នូ"
}

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def to_khmer_num(num: int | str) -> str:
    s = str(num)
    return "".join(KHMER_NUMS.get(c, c) for c in s)

def format_khmer_date(date_str: str) -> str:
    """Formats 11/Sep/2026, 10/9/2026, or 'ថ្ងៃនេះ' into ថ្ងៃទី ១១ ខែកញ្ញា ឆ្នាំ ២០២៦ (11/09/2026)."""
    now = datetime.now()
    day = now.day
    month = now.month
    year = now.year

    if date_str and date_str.strip() not in ["ថ្ងៃនេះ", "today", "Today"]:
        clean_str = date_str.strip().replace("-", "/")
        parts = clean_str.split("/")
        if len(parts) == 3:
            try:
                day = int(parts[0])
                m_raw = parts[1].strip().lower()
                if m_raw in MONTH_MAP:
                    month = MONTH_MAP[m_raw]
                else:
                    month = int(m_raw)
                year = int(parts[2])
            except (ValueError, KeyError):
                pass

    month_kh = KHMER_MONTHS.get(month, f"ខែ {month}")
    return f"ថ្ងៃទី {to_khmer_num(day)} ខែ{month_kh} ឆ្នាំ {to_khmer_num(year)}"

def get_report_keyboard(current_view: str = "daily") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("🔄 ធ្វើបច្ចុប្បន្នភាព", callback_data="action_refresh"),
            InlineKeyboardButton("📅 មើលប្រចាំខែ", callback_data="action_monthly")
        ],
        [
            InlineKeyboardButton("📂 មើលគ្រប់ជំនាញ", callback_data="action_show_all"),
            InlineKeyboardButton("📋 បញ្ជីទំព័រ", callback_data="action_categories_p1")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def format_daily_report(data: TodayReportData, delta_total: int = None, show_all: bool = False) -> str:
    lines = []
    lines.append("📊 <b>របាយការណ៍ស្ថិតិប្រចាំថ្ងៃ</b>")
    lines.append(f"🗓 កាលបរិច្ឆេទ៖ {format_khmer_date(data.date_str)}")
    lines.append(DIVIDER)

    # Sources summary (Medium letter, not bold italic)
    lines.append("📌 <b>ប្រភពចុះឈ្មោះ :</b>")
    for src, count in data.sources_summary.items():
        lines.append(f"• {html.escape(src)}: {count} នាក់")
    lines.append(DIVIDER)

    # Categories breakdown (Medium letter, not bold italic)
    lines.append("📚 <b>ស្ថិតិតាមមុខជំនាញ:</b>")
    visible_cats = data.categories if show_all else [c for c in data.categories if c.registered > 0]

    if not visible_cats:
        lines.append("• មិនទាន់មានការចុះឈ្មោះថ្មីនៅថ្ងៃនេះទេ")
    else:
        for cat in visible_cats:
            cat_name = html.escape(cat.name)
            lines.append(f"• {cat_name}: {cat.registered} នាក់")

    if not show_all and len(visible_cats) < len(data.categories):
        hidden_count = len(data.categories) - len(visible_cats)
        lines.append(f"(ជំនាញផ្សេងទៀតចំនួន {hidden_count} មិនទាន់មានការចុះឈ្មោះ)")

    lines.append(DIVIDER)

    # Grand total line with trend delta
    delta_str = ""
    if delta_total is not None and delta_total != 0:
        if delta_total > 0:
            delta_str = f" ▲ (+{delta_total})"
        else:
            delta_str = f" ▼ ({delta_total})"
    elif delta_total == 0:
        delta_str = " – (គ្មានបម្រែបម្រួល)"

    date_label = format_khmer_date(data.date_str)
    lines.append(f"👥 <b>សរុប{date_label}៖ {data.grand_total} នាក់</b>{delta_str}")
    lines.append(f"[ មកដល់: {data.total_arrived} | ត្រឡប់ទៅវិញ: {data.total_returned} | បោះបង់: {data.total_dropped} ]")

    return "\n".join(lines)

def format_monthly_report(hist_data: HistoricalReportData, target_month: int = None, target_year: int = None) -> str:
    now = datetime.now()
    month = target_month or now.month
    year = target_year or now.year
    month_name = KHMER_MONTHS.get(month, str(month))

    lines = []
    lines.append(f"📈 <b>របាយការណ៍ស្ថិតិសរុបប្រចាំខែ {month_name} {to_khmer_num(year)}</b>")
    lines.append(f"🗓 <b>គិតត្រឹមថ្ងៃនេះ ({to_khmer_num(now.day)} {month_name} {to_khmer_num(year)})</b>")
    lines.append(DIVIDER)

    # Sources
    lines.append("📌 <b>ប្រភពចុះឈ្មោះសរុប :</b>")
    for src, count in hist_data.sources_summary.items():
        lines.append(f"• {html.escape(src)}: <b>{count} នាក់</b>")
    lines.append(DIVIDER)

    # Top categories
    lines.append("📚 <b>ចំណាត់ថ្នាក់ជំនាញនាំមុខ (Top Majors):</b>")
    sorted_cats = sorted(hist_data.categories, key=lambda c: c.registered, reverse=True)
    active_cats = [c for c in sorted_cats if c.registered > 0]

    if not active_cats:
        lines.append("មិនទាន់មានទិន្នន័យក្នុងខែនេះទេ")
    else:
        for idx, cat in enumerate(active_cats):
            if idx == 0:
                badge = "🥇"
            elif idx == 1:
                badge = "🥈"
            elif idx == 2:
                badge = "🥉"
            else:
                badge = "•"
            female_str = f" (ស្រី: {cat.female} នាក់)" if cat.female > 0 else ""
            lines.append(f"{badge} <b>{html.escape(cat.name)}</b>: <b>{cat.registered} នាក់</b>{female_str}")

    lines.append(DIVIDER)
    female_total_str = f" (ស្រី៖ <b>{hist_data.total_female} នាក់</b>)" if hist_data.total_female > 0 else ""
    lines.append(f"👥 <b>និស្សិតដាក់ពាក្យសរុប៖ {hist_data.grand_total} នាក់</b>{female_total_str}")
    lines.append(f"✅ ចំនួនបានមកដល់៖ <b>{hist_data.total_arrived} នាក់</b>")
    lines.append(f"❌ ចំនួនបោះបង់៖ <b>{hist_data.total_dropped} នាក់</b>")

    return "\n".join(lines)

def format_diff_alert(changes: list[dict], current_total: int, old_total: int) -> str:
    now_str = datetime.now().strftime("%I:%M %p")
    lines = []
    lines.append("🔔 <b>បច្ចុប្បន្នភាពថ្មីពី Google Sheet!</b>")
    lines.append(f"⏱ <b>វេលាម៉ោង {now_str}</b>")
    lines.append(DIVIDER)
    lines.append("មានការកែប្រែទិន្នន័យ៖")

    for ch in changes:
        cat_name = html.escape(ch["name"])
        old_v = ch["old"]
        new_v = ch["new"]
        diff = new_v - old_v
        diff_str = f"+{diff}" if diff > 0 else f"{diff}"
        lines.append(f"• <b>{cat_name}</b>៖ <b>{old_v}</b> ➔ <b>{new_v} នាក់</b> ({diff_str})")

    lines.append(DIVIDER)
    total_diff = current_total - old_total
    tot_diff_str = f" (+{total_diff})" if total_diff > 0 else (f" ({total_diff})" if total_diff < 0 else "")
    lines.append(f"👥 <b>ចំនួនសរុបបច្ចុប្បន្ន៖ {current_total} នាក់</b>{tot_diff_str}")

    return "\n".join(lines)

def format_categories_page(categories: list, page: int = 1, page_size: int = 8):
    total_pages = max(1, (len(categories) + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    current_page_items = categories[start_idx:end_idx]

    lines = []
    lines.append(f"📂 <b>បញ្ជីមុខជំនាញទាំងអស់ (ទំព័រ {page}/{total_pages})</b>")
    lines.append(DIVIDER)

    for idx, cat in enumerate(current_page_items, start=start_idx + 1):
        lines.append(f"{idx}. <b>{html.escape(cat.name)}</b>: <b>{cat.registered} នាក់</b>")

    lines.append(DIVIDER)
    lines.append(f"ចំនួនមុខជំនាញសរុប៖ <b>{len(categories)} ជំនាញ</b>")

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ ថយក្រោយ", callback_data=f"action_cat_p_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("បន្ទាប់ ➡️", callback_data=f"action_cat_p_{page+1}"))

    keyboard = [
        nav_buttons,
        [InlineKeyboardButton("🔙 ត្រឡប់ទៅរបាយការណ៍", callback_data="action_today")]
    ]

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)

def format_help() -> str:
    lines = [
        "📖 <b>ការណែនាំការប្រើប្រាស់ Bot ស្ថិតិ</b>",
        DIVIDER,
        "បញ្ជា (Commands) ដែលអាចប្រើបាន៖",
        "• /start - បង្ហាញផ្ទាំងស្វាគមន៍ និងមុខងារទូទៅ",
        "• /today - មើលស្ថិតិបច្ចុប្បន្នភាពថ្ងៃនេះ (ស្ថិតិថ្ងៃនឹង)",
        "• /report ឬ /daily - បង្ហាញរបាយការណ៍ប្រចាំថ្ងៃពេញលេញ",
        "• /monthly - បង្ហាញរបាយការណ៍សរុបប្រចាំខែ (ស្ថិតិប្រចាំថ្ងៃ)",
        "• /categories - មើលបញ្ជីមុខជំនាញទាំងអស់",
        "• /help - បង្ហាញសារជំនួយនេះ",
        DIVIDER,
        "⚡️ <b>Bot នឹងផ្ញើរបាយការណ៍ដោយស្វ័យប្រវត្តិរៀងរាល់ល្ងាច និងរុញដំណឹង (Push Alert) ភ្លាមៗនៅពេលមានការកែប្រែក្នុង Google Sheet។</b>"
    ]
    return "\n".join(lines)

def format_welcome() -> str:
    lines = [
        "👋 <b>សូមស្វាគមន៍មកកាន់ Bot របាយការណ៍ស្ថិតិអាហារូបករណ៍!</b>",
        DIVIDER,
        "ប្រព័ន្ធនេះដំណើរការដោយទាញទិន្នន័យផ្ទាល់ពី <b>Google Sheet</b> ដោយស្វ័យប្រវត្តិនឹងគ្រប់គ្រងតាមរយៈ Web Portal។"
    ]
    return "\n".join(lines)

def format_new_registration_alert(student: dict) -> str:
    """
    Formats instant alert for newly registered student in 'Part 2 -Registrations'.
    Displays only the requested fields:
      - Name: គោត្តនាម-នាម (Col D)
      - Latang: ឈ្មោះជាអក្សរឡាតាំង (Col E)
      - Gender: ភេទ (Col F)
      - Phone: លេខទូរស័ព្ទ (Col J)
      - POB: ទីកន្លែងកំណើត / ខេត្តកំណើត (Col M)
      - Skill: ជំនាញស្នើសុំ (Col P)
    Medium letter, clean layout, no heavy bold/italic walls.
    """
    now_str = datetime.now().strftime("%I:%M %p")
    lines = []
    lines.append("🎓 <b>មានការចុះឈ្មោះថ្មី!</b>")
    lines.append(DIVIDER)
    lines.append(f"• ឈ្មោះ៖ {html.escape(student.get('name', '') or '—')}")
    lines.append(f"• អក្សរឡាតាំង៖ {html.escape(student.get('latang', '') or '—')}")
    lines.append(f"• ភេទ៖ {html.escape(student.get('gender', '') or '—')}")
    lines.append(f"• លេខទូរស័ព្ទ៖ {html.escape(student.get('phone', '') or '—')}")
    lines.append(f"• ខេត្តកំណើត៖ {html.escape(student.get('pob', '') or '—')}")
    lines.append(f"• ជំនាញ៖ {html.escape(student.get('skill', '') or '—')}")
    lines.append(DIVIDER)
    lines.append(f"⏱ វេលាម៉ោង៖ {now_str}")
    return "\n".join(lines)

