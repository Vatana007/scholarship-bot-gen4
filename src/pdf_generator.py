import os
import shutil
import subprocess
from datetime import datetime
from src.config import DATA_DIR, TIMEZONE, logger
from src.parser import HistoricalReportData
from src.report_builder import KHMER_MONTHS, to_khmer_num

def find_chromium_binary() -> str | None:
    """Finds installed Chrome or Edge binary for headless PDF printing across Windows, Linux, and Cloud (Render)."""
    # 1. Check explicit environment variables
    for env_var in ["CHROME_BIN", "GOOGLE_CHROME_BIN", "CHROMIUM_PATH", "PUPPETEER_EXECUTABLE_PATH"]:
        val = os.environ.get(env_var)
        if val and os.path.exists(val):
            return val

    # 2. Check standard Linux/Docker & Windows candidate paths
    candidates = [
        # Linux standard paths (Docker / Render / Ubuntu)
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/opt/google/chrome/chrome",
        "/opt/google/chrome/google-chrome",
        "/opt/render/project/.render/chrome/opt/google/chrome/google-chrome",
        os.path.join(os.getcwd(), ".chrome", "opt", "google", "chrome", "google-chrome"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chrome", "opt", "google", "chrome", "google-chrome"),
        # Windows standard paths
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        # PATH lookups
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("msedge"),
        shutil.which("chrome"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path

    # 3. Check Playwright cache if installed
    import glob
    home = os.path.expanduser("~")
    pw_patterns = [
        os.path.join(home, ".cache", "ms-playwright", "chromium-*", "chrome-linux", "chrome"),
        os.path.join(home, "AppData", "Local", "ms-playwright", "chromium-*", "chrome-win", "chrome.exe"),
    ]
    for pattern in pw_patterns:
        matches = glob.glob(pattern)
        if matches and os.path.exists(matches[0]):
            return matches[0]

    return None

def build_monthly_html(hist_data: HistoricalReportData, target_month: int = None, target_year: int = None) -> str:
    now = datetime.now(TIMEZONE)
    month = target_month or now.month
    year = target_year or now.year
    month_name = KHMER_MONTHS.get(month, f"ខែ {month}")
    
    # Calculate sources totals
    source_keys = ["E-School", "ក្រសួងអប់រំ", "បងប្អូន", "DUC"]
    source_totals = {s: 0 for s in source_keys}
    
    rows_html = ""
    # Sort categories with highest registrations first
    sorted_cats = sorted(hist_data.categories, key=lambda c: c.registered, reverse=True)
    
    for idx, cat in enumerate(sorted_cats, 1):
        s_counts = [cat.sources.get(s, 0) for s in source_keys]
        for s, cnt in zip(source_keys, s_counts):
            source_totals[s] += cnt
            
        highlight = "style='background-color: #f8fafc;'" if cat.registered > 0 else ""
        num_style = "font-weight: 700; color: #1e3a8a;" if cat.registered > 0 else "color: #94a3b8;"
        female_style = "font-weight: 700; color: #be185d;" if cat.female > 0 else "color: #94a3b8;"
        dropped_style = "font-weight: 700; color: #b91c1c;" if cat.dropped > 0 else "color: #94a3b8;"
        female_dropped_style = "font-weight: 700; color: #be185d;" if cat.female_dropped > 0 else "color: #94a3b8;"
        
        rows_html += f"""
        <tr {highlight}>
            <td style="text-align: center; color: #64748b;">{idx}</td>
            <td class="major-name">{cat.name}</td>
            <td style="{num_style}">{cat.registered}</td>
            <td style="{female_style}">{cat.female}</td>
            <td style="{dropped_style}">{cat.dropped}</td>
            <td style="{female_dropped_style}">{cat.female_dropped}</td>
            <td>{s_counts[0]}</td>
            <td>{s_counts[1]}</td>
            <td>{s_counts[2]}</td>
            <td>{s_counts[3]}</td>
        </tr>
        """
        
    date_str_kh = f"ថ្ងៃទី {to_khmer_num(now.day)} ខែ{month_name} ឆ្នាំ {to_khmer_num(year)}"

    html = f"""<!DOCTYPE html>
<html lang="km">
<head>
    <meta charset="UTF-8">
    <title>របាយការណ៍ប្រចាំខែ</title>
    <link href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;500;600;700&family=Moul&display=swap" rel="stylesheet">
    <style>
        @page {{
            size: A4 portrait;
            margin: 12mm 12mm;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Kantumruy Pro', sans-serif;
            background: #ffffff;
            color: #1e293b;
            padding: 10px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 16px;
            border-bottom: 2px solid #1e3a8a;
            padding-bottom: 12px;
        }}
        .title {{
            font-family: 'Moul', 'Kantumruy Pro', cursive;
            font-size: 22px;
            color: #1e3a8a;
            margin-bottom: 6px;
        }}
        .subtitle {{
            font-size: 13px;
            color: #475569;
            font-weight: 600;
        }}
        .meta-info {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 10px;
            color: #334155;
            font-weight: 600;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}
        th, td {{
            border: 1px solid #334155;
            padding: 5px 6px;
            text-align: center;
        }}
        th {{
            background-color: #f1f5f9;
            color: #0f172a;
            font-weight: 700;
        }}
        .th-source {{
            background-color: #e2e8f0;
            color: #1e293b;
        }}
        td.major-name {{
            text-align: left;
            font-weight: 600;
            padding-left: 8px;
        }}
        .total-row td {{
            font-weight: 700;
            background-color: #e0f2fe;
            color: #0369a1;
            font-size: 12px;
        }}
        .footer-signatures {{
            margin-top: 25px;
            display: flex;
            justify-content: flex-end;
            text-align: center;
            font-size: 12px;
            color: #1e293b;
        }}
        .sig-box {{
            width: 250px;
        }}
        .sig-space {{
            height: 50px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">របាយការណ៍ប្រចាំខែ</div>
        <div class="subtitle">ស្ថិតិសិស្ស-និស្សិតចុះឈ្មោះស្នើសុំអាហារូបករណ៍ • ខែ{month_name} ឆ្នាំ{to_khmer_num(year)}</div>
    </div>

    <div class="meta-info">
        <div>📊 កាលបរិច្ឆេទរបាយការណ៍៖ <b>{date_str_kh}</b></div>
        <div>👥 និស្សិតដាក់ពាក្យសរុប៖ <b>{hist_data.grand_total} នាក់</b> (ស្រី <b>{hist_data.total_female}</b> នាក់) • បោះបង់៖ <b>{hist_data.total_dropped} នាក់</b> (ស្រី <b>{hist_data.total_female_dropped}</b> នាក់)</div>
    </div>

    <table>
        <thead>
            <tr>
                <th rowspan="2" style="width: 4%;">ល.រ</th>
                <th rowspan="2" style="width: 28%;">ជំនាញ</th>
                <th colspan="2" style="background-color: #dbeafe; color: #1e40af;">ចំនួនសរុប</th>
                <th colspan="2" style="background-color: #fee2e2; color: #b91c1c;">បោះបង់</th>
                <th colspan="4" class="th-source">ប្រភព (Sources)</th>
            </tr>
            <tr>
                <th style="width: 8%; background-color: #eff6ff; color: #1e3a8a;">សរុប</th>
                <th style="width: 7%; background-color: #fce7f3; color: #9d174d;">ស្រី</th>
                <th style="width: 7%; background-color: #fef2f2; color: #b91c1c;">សរុប</th>
                <th style="width: 7%; background-color: #fce7f3; color: #9d174d;">ស្រី</th>
                <th style="width: 7.25%;">E-School</th>
                <th style="width: 7.25%;">ក្រសួងអប់រំ</th>
                <th style="width: 7.25%;">បងប្អូន</th>
                <th style="width: 7.25%;">DUC</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
            <tr class="total-row">
                <td colspan="2" style="text-align: center; font-size: 12px;">សរុបទាំងអស់ (Grand Total)</td>
                <td style="font-size: 13px; font-weight: 800;">{hist_data.grand_total}</td>
                <td style="font-size: 13px; font-weight: 800; color: #be185d;">{hist_data.total_female}</td>
                <td style="font-size: 13px; font-weight: 800; color: #b91c1c;">{hist_data.total_dropped}</td>
                <td style="font-size: 13px; font-weight: 800; color: #be185d;">{hist_data.total_female_dropped}</td>
                <td>{source_totals['E-School']}</td>
                <td>{source_totals['ក្រសួងអប់រំ']}</td>
                <td>{source_totals['បងប្អូន']}</td>
                <td>{source_totals['DUC']}</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""
    return html

def generate_monthly_report_pdf(hist_data: HistoricalReportData, target_month: int = None, target_year: int = None, force_refresh: bool = False) -> str:
    """
    Generates an official PDF report matching the user's layout sketch without headers or footers,
    with fast caching and returns the absolute file path to the generated PDF.
    """
    import time
    now = datetime.now(TIMEZONE)
    month = target_month or now.month
    year = target_year or now.year

    pdf_filename = f"Monthly_Report_{year}_{month:02d}.pdf"
    pdf_path = os.path.join(DATA_DIR, pdf_filename)
    html_path = os.path.join(DATA_DIR, f"temp_report_{year}_{month:02d}.html")

    # Fast caching check (within 3 minutes)
    if not force_refresh and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        file_age = time.time() - os.path.getmtime(pdf_path)
        if file_age < 180:  # 3 minutes
            logger.info(f"Using cached Monthly Report PDF ({file_age:.1f}s old): {pdf_path}")
            return pdf_path

    html_content = build_monthly_html(hist_data, month, year)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    browser_bin = find_chromium_binary()
    if not browser_bin:
        raise RuntimeError(
            "No Chrome/Chromium browser found to render PDF. "
            "On Render, please deploy using Docker (Dockerfile) or install Chromium."
        )

    import pathlib
    file_uri = pathlib.Path(html_path).resolve().as_uri()
    abs_pdf_path = os.path.abspath(pdf_path)

    base_flags = [
        "--no-sandbox",
        "--no-zygote",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--disable-translate",
        "--no-first-run",
        "--no-default-browser-check",
        "--hide-scrollbars",
        "--mute-audio",
        "--allow-file-access-from-files",
        "--enable-local-file-accesses",
        "--virtual-time-budget=4000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={abs_pdf_path}",
        file_uri
    ]

    # Try modern headless mode first (--headless=new), with fallback to classic (--headless)
    cmd_attempts = [
        [browser_bin, "--headless=new"] + base_flags,
    ]

    last_error = "Unknown error"
    for cmd in cmd_attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0 and os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                logger.info(f"Generated Monthly Report PDF (no headers/footers) successfully: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
                return pdf_path
            last_error = result.stderr.decode(errors='ignore') if result.stderr else f"Browser returned exit code {result.returncode}"
        except subprocess.TimeoutExpired:
            last_error = "Browser command timed out after 10 seconds"
            break
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"Browser PDF generation failed: {last_error}")
