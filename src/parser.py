import hashlib
import json
import re
from dataclasses import dataclass, field
from src.config import logger

@dataclass
class CategoryItem:
    name: str
    registered: int = 0
    arrived: int = 0
    returned: int = 0
    dropped: int = 0
    female: int = 0
    female_dropped: int = 0
    sources: dict[str, int] = field(default_factory=dict)

@dataclass
class TodayReportData:
    title: str
    date_str: str
    sources_summary: dict[str, int]
    categories: list[CategoryItem]
    grand_total: int
    total_arrived: int
    total_returned: int
    total_dropped: int
    data_hash: str

@dataclass
class HistoricalReportData:
    title: str
    sources_summary: dict[str, int]
    dates: list[str]
    categories: list[CategoryItem]
    grand_total: int
    total_arrived: int
    total_dropped: int
    total_female: int = 0
    total_female_dropped: int = 0

def parse_int_safe(val: str, default: int = 0) -> int:
    if not val:
        return default
    val_clean = re.sub(r"[^0-9]", "", str(val).strip())
    if not val_clean:
        return default
    try:
        return int(val_clean)
    except ValueError:
        return default

def compute_rows_hash(rows: list[list[str]]) -> str:
    """Computes SHA256 hash of sheet rows to detect any changes."""
    serialized = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

MONTH_NAME_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def parse_date_dmy(s: str) -> tuple[int, int, int] | None:
    if not s:
        return None
    s_clean = str(s).strip()
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s_clean)
    if m_iso:
        return int(m_iso.group(3)), int(m_iso.group(2)), int(m_iso.group(1))
    parts = s_clean.replace("-", "/").split("/")
    if len(parts) == 3:
        try:
            p0 = int(parts[0])
            p1_raw = parts[1].strip().lower()
            m = MONTH_NAME_MAP.get(p1_raw, int(p1_raw) if p1_raw.isdigit() else 0)
            y = int(parts[2])
            return p0, m, y
        except Exception:
            pass
    return None

def count_registration_statuses(reg_rows: list[list[str]], target_date: str = None) -> tuple[int, int, int]:
    """
    Counts arrival statuses from 'Part 2 -Registrations' sheet:
    - Matches non-empty student name in Column D (index 3).
    - Checks Column CI (index 86):
        - Contains 'OK' -> count as 'មកដល់' (arrived)
        - Contains 'ទៅផ្ទះវិញ' -> count as 'ត្រឡប់ទៅវិញ' (returned)
        - Contains 'បោះបង់' -> count as 'បោះបង់' (dropped)
    - If target_date matches specific rows in Date Column CH (index 85), returns that date's counts.
    - Otherwise returns the cumulative counts across all registered students.
    """
    if not reg_rows or len(reg_rows) < 2:
        return 0, 0, 0

    header = reg_rows[0]
    name_col = 3 # Col D
    status_col = 86 # Col CI
    date_col = 85 # Col CH

    for idx, h in enumerate(header):
        h_clean = h.strip()
        if "គោត្តនាម" in h_clean or "ឈ្មោះ" in h_clean:
            name_col = idx
        elif "ស្ថានភាពមកដល់" in h_clean:
            status_col = idx
        elif h_clean.lower() == "date" or "កាលបរិច្ឆេទ" in h_clean:
            date_col = idx

    t_dmy = parse_date_dmy(target_date) if target_date and target_date.lower() not in ["all", "សរុប"] else None

    tot_arr, tot_ret, tot_drp = 0, 0, 0
    d_arr, d_ret, d_drp = 0, 0, 0
    d_matched = False

    for r in reg_rows[1:]:
        if len(r) <= name_col or not r[name_col].strip():
            continue
        status = r[status_col].strip() if len(r) > status_col else ""
        d_str = r[date_col].strip() if len(r) > date_col else ""

        is_ok = "ok" in status.lower()
        is_ret = "ទៅផ្ទះវិញ" in status
        is_drp = "បោះបង់" in status

        if is_ok:
            tot_arr += 1
        elif is_ret:
            tot_ret += 1
        elif is_drp:
            tot_drp += 1

        if t_dmy and d_str:
            r_dmy = parse_date_dmy(d_str)
            if r_dmy and r_dmy == t_dmy:
                d_matched = True
                if is_ok:
                    d_arr += 1
                elif is_ret:
                    d_ret += 1
                elif is_drp:
                    d_drp += 1

    if t_dmy and d_matched:
        return d_arr, d_ret, d_drp

    return tot_arr, tot_ret, tot_drp

def parse_today_sheet(rows: list[list[str]], reg_rows: list[list[str]] = None) -> TodayReportData:
    """
    Parses 'ស្ថិតិថ្ងៃនឹង' sheet layout:
    Row 1: Title
    Row 2: Category, 'មកពី', Date header (e.g. 10/9/2026 at Col F/5)
    Row 3: 'សរុប'
    Row 4: Subheaders: E-School (B), ក្រសួងអប់រំ (C), បងប្អូន (D), DUC (E),
                       ចំនួនសរុបដាក់ពាក្យ (F), ចំនួនមកដល់ (G), ត្រឡប់ទៅផ្ទះវិញ (H), បោះបង់ (I)
    Rows 5 to 26: Category data rows
    Row 27: Grand total row: 'សរុបទាំងអស់៖ 14 នាក់'
    """
    if not rows or len(rows) < 5:
        raise ValueError("សន្លឹកស្ថិតិថ្ងៃនឹង គ្មានទិន្នន័យគ្រប់គ្រាន់។")

    title = rows[0][0].strip() if rows[0] else "របាយការណ៍ស្ថិតិប្រចាំថ្ងៃ"

    # Extract date header from Row 2
    date_str = ""
    if len(rows) > 1:
        for cell in rows[1]:
            c_strip = cell.strip()
            # Match date patterns like 11/Sep/2026, 10/9/2026, or 10-09-2026
            if re.search(r"\d{1,2}[/-][A-Za-z0-9]+[/-]\d{2,4}", c_strip):
                date_str = c_strip
                break
    if not date_str:
        date_str = "ថ្ងៃនេះ"

    # Extract source headers from Row 4 (Cols 1 to 4)
    source_names = ["E-School", "ក្រសួងអប់រំ", "បងប្អូន", "DUC"]
    if len(rows) > 3:
        for idx, col_idx in enumerate([1, 2, 3, 4]):
            if col_idx < len(rows[3]) and rows[3][col_idx].strip():
                source_names[idx] = rows[3][col_idx].strip()

    sources_summary = {s: 0 for s in source_names}
    categories = []

    grand_total_calc = 0
    total_arrived = 0
    total_returned = 0
    total_dropped = 0

    # Parse rows starting from Row 5 (index 4) until total row
    for r_idx in range(4, len(rows)):
        row = rows[r_idx]
        if not row or not any(c.strip() for c in row):
            continue

        col0 = row[0].strip() if len(row) > 0 else ""

        # Check if it's the grand total row
        if "សរុបទាំងអស់" in col0:
            continue

        if not col0:
            continue

        # Extract source counts for this category
        cat_sources = {}
        for s_idx, col_idx in enumerate([1, 2, 3, 4]):
            val = parse_int_safe(row[col_idx]) if col_idx < len(row) else 0
            cat_sources[source_names[s_idx]] = val
            sources_summary[source_names[s_idx]] += val

        # Extract date counts (Cols 5: registered, 6: arrived, 7: returned, 8: dropped)
        reg_count = parse_int_safe(row[5]) if len(row) > 5 else 0
        arr_count = parse_int_safe(row[6]) if len(row) > 6 else 0
        ret_count = parse_int_safe(row[7]) if len(row) > 7 else 0
        drp_count = parse_int_safe(row[8]) if len(row) > 8 else 0

        grand_total_calc += reg_count
        total_arrived += arr_count
        total_returned += ret_count
        total_dropped += drp_count

        categories.append(CategoryItem(
            name=col0,
            registered=reg_count,
            arrived=arr_count,
            returned=ret_count,
            dropped=drp_count,
            sources=cat_sources
        ))

    data_hash = compute_rows_hash(rows)

    if reg_rows:
        arr_reg, ret_reg, drp_reg = count_registration_statuses(reg_rows, date_str)
        total_arrived = arr_reg
        total_returned = ret_reg
        total_dropped = drp_reg

    return TodayReportData(
        title=title,
        date_str=date_str,
        sources_summary=sources_summary,
        categories=categories,
        grand_total=grand_total_calc,
        total_arrived=total_arrived,
        total_returned=total_returned,
        total_dropped=total_dropped,
        data_hash=data_hash
    )

def parse_historical_sheet(rows: list[list[str]], reg_rows: list[list[str]] = None) -> HistoricalReportData:
    """
    Parses 'ស្ថិតិប្រចាំថ្ងៃ' sheet layout:
    Row 1: ជំនាញ (A), សរុបទាំងអស់ (B-D), មកពី (E-H), Title (I+)
    Row 2: Subheaders + Dates (Col 8, 12, 16, 20, ...)
    Row 3: Sources (E-H: E-School, ក្រសួងអប់រំ, បងប្អូន, DUC), Date subheaders
    Row 4 to 25: Category rows
    Row 26: Grand total row

    If reg_rows from 'Part 2 -Registrations' is provided, counts female students (Col F == 'ស្រី')
    matching each skill (Col P).
    """
    if not rows or len(rows) < 4:
        raise ValueError("សន្លឹកស្ថិតិប្រចាំថ្ងៃ គ្មានទិន្នន័យគ្រប់គ្រាន់។")

    title = "របាយការណ៍ស្ថិតិប្រចាំថ្ងៃ (Historical)"
    if len(rows[0]) > 8 and rows[0][8].strip():
        title = rows[0][8].strip()

    # Calculate female, dropped, and female_dropped counts per skill from 'Part 2 -Registrations'
    female_by_skill = {}
    dropped_by_skill = {}
    female_dropped_by_skill = {}
    total_female = 0
    total_female_dropped = 0
    if reg_rows:
        students = parse_student_registrations(reg_rows)
        for s in students:
            g = s.get("gender", "").strip()
            sk = s.get("skill", "").strip()
            st = s.get("status", "").strip()
            is_female = (g == "ស្រី")
            is_dropped = ("បោះបង់" in st)
            if is_female:
                female_by_skill[sk] = female_by_skill.get(sk, 0) + 1
                total_female += 1
            if is_dropped:
                dropped_by_skill[sk] = dropped_by_skill.get(sk, 0) + 1
            if is_female and is_dropped:
                female_dropped_by_skill[sk] = female_dropped_by_skill.get(sk, 0) + 1
                total_female_dropped += 1

    # Discover all date columns from Row 2
    dates = []
    date_col_indices = []
    if len(rows) > 1:
        for col_idx in range(8, len(rows[1]), 4):
            date_val = rows[1][col_idx].strip()
            if date_val and re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", date_val):
                dates.append(date_val)
                date_col_indices.append(col_idx)

    source_names = ["E-School", "ក្រសួងអប់រំ", "បងប្អូន", "DUC"]
    sources_summary = {s: 0 for s in source_names}
    categories = []

    grand_total = 0
    total_arrived = 0
    total_dropped = 0

    for r_idx in range(3, len(rows)):
        row = rows[r_idx]
        if not row or not any(c.strip() for c in row):
            continue

        col0 = row[0].strip() if len(row) > 0 else ""
        if "សរុបទាំងអស់" in col0:
            continue
        if not col0:
            continue

        # Overall summary columns in historical sheet:
        # Col 1: ចំនួនសរុបដាក់ពាក្យ
        # Col 2: ចំនួនមកដល់
        # Col 3: ចំនួនបោះបង់
        reg_total = parse_int_safe(row[1]) if len(row) > 1 else 0
        arr_total = parse_int_safe(row[2]) if len(row) > 2 else 0
        drp_total = parse_int_safe(row[3]) if len(row) > 3 else 0

        # Sources summary in Cols 4..7
        cat_sources = {}
        for s_idx, col_idx in enumerate([4, 5, 6, 7]):
            val = parse_int_safe(row[col_idx]) if col_idx < len(row) else 0
            cat_sources[source_names[s_idx]] = val
            sources_summary[source_names[s_idx]] += val

        # Calculate from date columns if Col 1 is 0 or needs summing
        date_sum = 0
        for c_idx in date_col_indices:
            if c_idx < len(row):
                date_sum += parse_int_safe(row[c_idx])

        # Use maximum of sheet Col 1 or date sum
        final_reg = max(reg_total, date_sum)
        grand_total += final_reg
        total_arrived += arr_total
        total_dropped += drp_total

        # Match dropped count for this skill
        cat_dropped = drp_total
        if col0 in dropped_by_skill:
            cat_dropped = max(cat_dropped, dropped_by_skill[col0])
        else:
            for sk, cnt in dropped_by_skill.items():
                if sk and (sk in col0 or col0 in sk):
                    cat_dropped = max(cat_dropped, cnt)
                    break

        # Match female count for this skill
        cat_female = female_by_skill.get(col0, 0)
        if cat_female == 0:
            for sk, cnt in female_by_skill.items():
                if sk and (sk in col0 or col0 in sk):
                    cat_female = cnt
                    break

        # Match female dropped count for this skill
        cat_female_drp = female_dropped_by_skill.get(col0, 0)
        if cat_female_drp == 0:
            for sk, cnt in female_dropped_by_skill.items():
                if sk and (sk in col0 or col0 in sk):
                    cat_female_drp = cnt
                    break

        categories.append(CategoryItem(
            name=col0,
            registered=final_reg,
            arrived=arr_total,
            returned=0,
            dropped=cat_dropped,
            female=cat_female,
            female_dropped=cat_female_drp,
            sources=cat_sources
        ))

    return HistoricalReportData(
        title=title,
        sources_summary=sources_summary,
        dates=dates,
        categories=categories,
        grand_total=grand_total,
        total_arrived=total_arrived,
        total_dropped=total_dropped,
        total_female=total_female,
        total_female_dropped=max(total_female_dropped, sum(c.female_dropped for c in categories))
    )

def get_available_dates(h_rows: list[list[str]]) -> list[dict]:
    """
    Returns list of dates available in the historical sheet,
    with normalized ISO date string, display label, and student total count.
    """
    if not h_rows or len(h_rows) < 3:
        return []

    available = []
    # Dates are in Row 1 (index 1), every 4 columns from Col 8
    for col_idx in range(8, len(h_rows[1]), 4):
        date_raw = h_rows[1][col_idx].strip()
        if not date_raw:
            continue
        parts = date_raw.replace('-', '/').split('/')
        if len(parts) == 3:
            try:
                m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                iso_date = f"{y:04d}-{m:02d}-{d:02d}"

                # Sum registrations for this column
                day_total = 0
                for r in h_rows[3:]:
                    if r and any(c.strip() for c in r) and "សរុបទាំងអស់" not in r[0]:
                        if col_idx < len(r):
                            day_total += parse_int_safe(r[col_idx])

                from src.report_builder import KHMER_MONTHS, to_khmer_num
                m_kh = KHMER_MONTHS.get(m, f"ខែ {m}")
                label = f"ថ្ងៃទី {to_khmer_num(d)} ខែ{m_kh} ឆ្នាំ {to_khmer_num(y)} ({day_total} នាក់)"
                available.append({
                    "date": iso_date,
                    "sheet_date": date_raw,
                    "day": d,
                    "month": m,
                    "year": y,
                    "total": day_total,
                    "label": label
                })
            except ValueError:
                continue

    # Return dates sorted with latest first
    return sorted(available, key=lambda x: x["date"], reverse=True)

def parse_date_report(h_rows: list[list[str]], today_rows: list[list[str]], target_date: str, reg_rows: list[list[str]] = None) -> TodayReportData:
    """
    Generates a TodayReportData structure for any selected date.
    If target_date is today or 'today', returns today_sheet data.
    Otherwise, extracts exact category metrics from the historical sheet.
    """
    target_clean = str(target_date).strip() if target_date else ""
    today_data = parse_today_sheet(today_rows, reg_rows=reg_rows)

    if not target_clean or target_clean.lower() in ["today", "ថ្ងៃនេះ"]:
        return today_data

    # Parse target year, month, day
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", target_clean)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
    else:
        parts = target_clean.replace("-", "/").split("/")
        if len(parts) == 3:
            try:
                p0, p1, p2 = int(parts[0]), int(parts[1]), int(parts[2])
                if p2 > 1000:
                    if p0 > 12:
                        d, m, y = p0, p1, p2
                    else:
                        m, d, y = p0, p1, p2
                else:
                    d, m, y = p0, p1, p2
            except ValueError:
                return today_data
        else:
            return today_data

    # Check if target matches today_sheet
    if f"{d}" in today_data.date_str and (f"{m}" in today_data.date_str or "Sep" in today_data.date_str):
        return today_data

    # Find matching column in h_rows
    col_idx = None
    if len(h_rows) > 1:
        for idx in range(8, len(h_rows[1]), 4):
            cell_val = h_rows[1][idx].strip()
            if cell_val in [f"{m}/{d}/{y}", f"{d}/{m}/{y}", f"{m}/{d}/{y%100}"]:
                col_idx = idx
                break

    if col_idx is None:
        raise ValueError(f"រកមិនឃើញទិន្នន័យសម្រាប់ថ្ងៃទី {d}/{m}/{y} នៅក្នុង Sheet ទេ។")

    categories = []
    grand_total = 0
    total_arrived = 0
    total_returned = 0
    total_dropped = 0

    for r in h_rows[3:]:
        if not r or not any(c.strip() for c in r):
            continue
        cat_name = r[0].strip()
        if not cat_name or "សរុបទាំងអស់" in cat_name:
            continue
        reg = parse_int_safe(r[col_idx]) if col_idx < len(r) else 0
        arr = parse_int_safe(r[col_idx+1]) if col_idx+1 < len(r) else 0
        ret = parse_int_safe(r[col_idx+2]) if col_idx+2 < len(r) else 0
        drp = parse_int_safe(r[col_idx+3]) if col_idx+3 < len(r) else 0

        categories.append(CategoryItem(
            name=cat_name,
            registered=reg,
            arrived=arr,
            returned=ret,
            dropped=drp
        ))
        grand_total += reg
        total_arrived += arr
        total_returned += ret
        total_dropped += drp

    if reg_rows:
        arr_reg, ret_reg, drp_reg = count_registration_statuses(reg_rows, target_clean)
        total_arrived = arr_reg
        total_returned = ret_reg
        total_dropped = drp_reg

    date_formatted = f"{d}/{m}/{y}"
    sources = {"ទិន្នន័យពី Sheet ប្រចាំថ្ងៃ": grand_total} if grand_total > 0 else {"ប្រភព": 0}

    return TodayReportData(
        title=f"របាយការណ៍ស្ថិតិកាលបរិច្ឆេទ {date_formatted}",
        date_str=date_formatted,
        sources_summary=sources,
        categories=categories,
        grand_total=grand_total,
        total_arrived=total_arrived,
        total_returned=total_returned,
        total_dropped=total_dropped,
        data_hash=""
    )

PROVINCES_LIST = [
    "រាជធានីភ្នំពេញ", "ភ្នំពេញ", "បាត់ដំបង", "កណ្តាល", "កណ្ដាល", "សៀមរាប", 
    "កំពង់ចាម", "កំពង់ឆ្នាំង", "កំពង់ស្ពឺ", "កំពង់ធំ", "កំពត", "កែប", 
    "កោះកុង", "ក្រចេះ", "មណ្ឌលគិរី", "ឧត្តរមានជ័យ", "ប៉ៃលិន", "ព្រះសីហនុ", 
    "ព្រះវិហារ", "ព្រៃវែង", "ពោធិ៍សាត់", "រតនគិរី", "ស្ទឹងត្រែង", "ស្វាយរៀង", 
    "តាកែវ", "ត្បូងឃ្មុំ"
]

def extract_province_only(val: str) -> str:
    """
    Ensures that only the province / city name is returned.
    If full district/village/commune text is provided, extracts just the province name.
    """
    if not val:
        return ""
    val_clean = str(val).strip()
    # Check exact match
    for p in PROVINCES_LIST:
        if val_clean == p:
            return val_clean
    # Check substring / prefix match
    for p in PROVINCES_LIST:
        if f"ខេត្ត{p}" in val_clean or f"ខេត្ត {p}" in val_clean or f"រាជធានី{p}" in val_clean or f"រាជធានី {p}" in val_clean or p in val_clean:
            return "រាជធានីភ្នំពេញ" if "ភ្នំពេញ" in p else (p.replace("ខេត្ត", "").strip())
    return val_clean

def parse_student_registrations(reg_rows: list[list[str]]) -> list[dict]:
    """
    Parses 'Part 2 -Registrations' sheet rows into structured student records.
    Exact requested fields:
      - name: Column D (index 3, 'គោត្តនាម-នាម')
      - latang: Column E (index 4, 'ឈ្មោះជាអក្សរឡាតាំង')
      - gender: Column F (index 5, 'ភេទ')
      - phone: Column J (index 9, 'លេខទូរស័ព្ទ')
      - pob: Column M (index 12, 'ខេត្តកំណើត' -> Province only)
      - skill: Column P (index 15, 'ជំនាញស្នើសុំ')
    Returns a list of dicts with student details and unique 'key'.
    """
    if not reg_rows or len(reg_rows) < 2:
        return []

    header = reg_rows[0]
    name_col = 3    # Col D
    latang_col = 4  # Col E
    gender_col = 5  # Col F
    phone_col = 9   # Col J
    pob_col = 12    # Col M ('ខេត្តកំណើត' - Province only)
    skill_col = 15  # Col P
    time_col = 35   # Col AJ ('កាលបរិច្ឆេទដាក់ពាក្យ')

    for idx, h in enumerate(header):
        h_clean = h.strip()
        if h_clean == "គោត្តនាម-នាម":
            name_col = idx
        elif h_clean == "ឈ្មោះជាអក្សរឡាតាំង":
            latang_col = idx
        elif h_clean == "ភេទ":
            gender_col = idx
        elif h_clean == "លេខទូរស័ព្ទ":
            phone_col = idx
        elif h_clean == "ខេត្តកំណើត" or (idx == 12 and "ខេត្ត" in h_clean):
            pob_col = idx
        elif h_clean == "ជំនាញស្នើសុំ":
            skill_col = idx
        elif h_clean == "កាលបរិច្ឆេទដាក់ពាក្យ" or idx == 35:
            time_col = idx

    students = []
    for row_idx, r in enumerate(reg_rows[1:], start=2):
        if len(r) <= name_col:
            continue
        name = r[name_col].strip()
        if not name:
            continue
        latang = r[latang_col].strip() if len(r) > latang_col else ""
        gender = r[gender_col].strip() if len(r) > gender_col else ""
        phone = r[phone_col].strip() if len(r) > phone_col else ""
        raw_pob = r[pob_col].strip() if len(r) > pob_col else ""
        pob = extract_province_only(raw_pob)
        skill = r[skill_col].strip() if len(r) > skill_col else ""
        registered_time = r[time_col].strip() if len(r) > time_col else ""

        clean_phone = phone.replace(" ", "")
        # Format phone with leading zero if 8 or 9 digits
        if clean_phone and len(clean_phone) in [8, 9] and not clean_phone.startswith("0"):
            display_phone = "0" + clean_phone
        else:
            display_phone = clean_phone

        student_key = f"{name}__{clean_phone}" if clean_phone else f"{name}__row{row_idx}"

        students.append({
            "name": name,
            "latang": latang,
            "gender": gender,
            "phone": display_phone,
            "pob": pob,
            "skill": skill,
            "registered_time": registered_time,
            "row_index": row_idx,
            "key": student_key
        })

    return students

