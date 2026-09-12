import os
import json
import threading
import asyncio
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import src.config as config
from src.config import logger, TIMEZONE
from src.sheets_client import SheetsClient
from src.parser import parse_today_sheet, parse_historical_sheet
from src.storage import Storage
from src.report_builder import format_daily_report, format_monthly_report, get_report_keyboard

sheets_client = SheetsClient()
storage = Storage()

# Runtime references injected by main.py
BOT_INSTANCE = None
SCHEDULER_INSTANCE = None
WATCHER_INSTANCE = None
LOOP_INSTANCE = None

def init_web_context(bot, scheduler=None, watcher=None, loop=None):
    global BOT_INSTANCE, SCHEDULER_INSTANCE, WATCHER_INSTANCE, LOOP_INSTANCE
    BOT_INSTANCE = bot
    SCHEDULER_INSTANCE = scheduler
    WATCHER_INSTANCE = watcher
    LOOP_INSTANCE = loop or asyncio.get_event_loop()
    logger.info("Web context successfully initialized with Bot, Scheduler, and Watcher instances.")

def run_async_coro(coro):
    """Safely runs an async coroutine on the bot's event loop."""
    if LOOP_INSTANCE and LOOP_INSTANCE.is_running():
        return asyncio.run_coroutine_threadsafe(coro, LOOP_INSTANCE)
    else:
        new_loop = asyncio.new_event_loop()
        return new_loop.run_until_complete(coro)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="km">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, viewport-fit=cover">
    <title>ប្រព័ន្ធគ្រប់គ្រង Telegram Bot ស្ថិតិអាហារូបករណ៍ | Admin Portal</title>
    
    <!-- PWA & Mobile Web App Meta Tags -->
    <meta name="theme-color" content="#0f172a">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Bot ស្ថិតិ">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/icon-180.png">
    <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Kantumruy:wght@400;700&family=Kantumruy+Pro:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #070a12;
            --bg-elevated: #0d121f;
            --card-bg: rgba(17, 24, 39, 0.78);
            --card-border: rgba(255, 255, 255, 0.08);
            --card-hover: rgba(30, 41, 59, 0.85);
            --primary: #2563eb;
            --primary-glow: rgba(37, 99, 235, 0.25);
            --primary-hover: #1d4ed8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --warning: #f59e0b;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --font-km: 'Kantumruy Pro', 'Kantumruy', sans-serif;
            --font-en: 'Plus Jakarta Sans', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --bottom-nav-height: 68px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: var(--font-km);
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 15% 10%, rgba(37, 99, 235, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 85% 80%, rgba(56, 189, 248, 0.08) 0%, transparent 40%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* SVG Icons System */
        .icon {
            width: 1.2rem;
            height: 1.2rem;
            vertical-align: -0.2rem;
            display: inline-block;
            stroke: currentColor;
            fill: none;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
            flex-shrink: 0;
        }
        .icon-sm { width: 0.95rem; height: 0.95rem; vertical-align: -0.15rem; }
        .icon-md { width: 1.35rem; height: 1.35rem; vertical-align: -0.25rem; }
        .icon-lg { width: 1.65rem; height: 1.65rem; vertical-align: -0.32rem; }
        .icon-xl { width: 2.4rem; height: 2.4rem; }
        .icon-fill { fill: currentColor; stroke: none; }

        /* Top Header */
        header {
            background: rgba(13, 18, 31, 0.88);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--card-border);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 60;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: inherit;
        }

        .brand-logo {
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: linear-gradient(135deg, #1e3a8a, #0284c7);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            box-shadow: 0 4px 14px var(--primary-glow);
            flex-shrink: 0;
        }

        .brand-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .brand-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: -0.01em;
            line-height: 1.25;
        }

        .brand-subtitle {
            font-size: 0.75rem;
            color: var(--text-muted);
            font-family: var(--font-en);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 600;
            font-family: var(--font-en);
            white-space: nowrap;
        }

        .pulse-dot {
            width: 7px;
            height: 7px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 8px #10b981;
            animation: livePulse 1.8s infinite;
        }
        @keyframes livePulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .btn-tg {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--card-border);
            color: #38bdf8;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s ease;
        }
        .btn-tg:hover {
            background: rgba(56, 189, 248, 0.15);
            border-color: rgba(56, 189, 248, 0.4);
        }

        /* Container */
        .container {
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
            padding: 20px 16px 40px;
            flex: 1;
        }

        /* Desktop Tabs */
        .tabs-desktop {
            display: flex;
            gap: 8px;
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid var(--card-border);
            padding: 6px;
            border-radius: var(--radius-md);
            margin-bottom: 24px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        .tabs-desktop::-webkit-scrollbar { display: none; }

        .tab-btn {
            flex: 1;
            min-width: fit-content;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: var(--font-km);
            font-size: 0.92rem;
            font-weight: 600;
            padding: 10px 18px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            white-space: nowrap;
        }
        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }
        .tab-btn.active {
            color: #ffffff;
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            box-shadow: 0 4px 12px var(--primary-glow);
        }

        /* Mobile Bottom Nav Bar */
        .mobile-bottom-nav {
            display: none;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px));
            padding-bottom: env(safe-area-inset-bottom, 0px);
            background: rgba(10, 15, 26, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid var(--card-border);
            z-index: 100;
            justify-content: space-around;
            align-items: center;
        }
        .nav-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            color: var(--text-dim);
            background: transparent;
            border: none;
            padding: 8px 0;
            font-family: var(--font-km);
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            touch-action: manipulation;
        }
        .nav-item .nav-icon {
            width: 1.4rem;
            height: 1.4rem;
            transition: transform 0.2s ease;
        }
        .nav-item.active {
            color: #38bdf8;
        }
        .nav-item.active .nav-icon {
            transform: scale(1.15);
            stroke: #38bdf8;
            filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.4));
        }

        /* Tab Content */
        .tab-content { display: none; animation: fadeIn 0.25s ease; }
        .tab-content.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

        /* Modern Cards Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .metric-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 20px;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            border-color: rgba(255, 255, 255, 0.15);
        }
        .metric-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .metric-badge-icon {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: rgba(255, 255, 255, 0.05);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #38bdf8;
        }
        .metric-val {
            font-size: 2.2rem;
            font-weight: 700;
            font-family: var(--font-km);
            color: #ffffff;
            line-height: 1.1;
            margin-bottom: 8px;
        }
        #m-today-total,
        #m-monthly-total {
            font-family: var(--font-km);
            font-weight: 700;
        }
        .metric-sub {
            font-size: 0.8rem;
            color: #38bdf8;
            font-weight: 500;
        }

        /* Arrival Status Chips */
        .status-chips-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 4px;
        }
        .status-chip {
            flex: 1;
            min-width: 65px;
            padding: 8px 6px;
            border-radius: var(--radius-sm);
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 3px;
        }
        .status-chip.arrived {
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
        }
        .status-chip.returned {
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: #38bdf8;
        }
        .status-chip.dropped {
            background: rgba(239, 68, 68, 0.12);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
        }
        .status-chip-label {
            font-size: 0.7rem;
            opacity: 0.9;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 3px;
        }
        .status-chip-num {
            font-size: 1.2rem;
            font-weight: 700;
            font-family: var(--font-km);
        }

        /* Section Container */
        .section-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-lg);
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--card-border);
            flex-wrap: wrap;
            gap: 10px;
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Banner Card */
        .banner-pdf {
            background: linear-gradient(135deg, rgba(30, 58, 138, 0.4) 0%, rgba(15, 23, 42, 0.85) 100%);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: var(--radius-lg);
            padding: 20px;
            margin-bottom: 22px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            position: relative;
            overflow: hidden;
        }
        .banner-pdf::before {
            content: '';
            position: absolute;
            left: 0; top: 0; bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, #38bdf8, #2563eb);
        }
        .banner-content {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .banner-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #60a5fa;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .banner-sub {
            font-size: 0.82rem;
            color: var(--text-muted);
            line-height: 1.4;
        }
        .banner-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }

        /* Sources Grid */
        .source-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 12px;
        }
        .source-box {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid var(--card-border);
            padding: 14px 10px;
            border-radius: var(--radius-md);
            text-align: center;
            transition: background 0.2s;
        }
        .source-box:hover {
            background: rgba(30, 41, 59, 0.8);
        }
        .source-name {
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-bottom: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .source-num {
            font-size: 1.5rem;
            font-weight: 700;
            font-family: var(--font-en);
            color: #38bdf8;
        }

        /* Responsive Table Container */
        .table-responsive {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border-radius: var(--radius-md);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            text-align: left;
        }
        th {
            background: rgba(30, 41, 59, 0.6);
            color: var(--text-muted);
            font-weight: 600;
            padding: 12px 14px;
            border-bottom: 1px solid var(--card-border);
            white-space: nowrap;
        }
        td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--card-border);
        }
        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }
        .badge-count {
            font-family: var(--font-mono);
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        /* Mobile Card View for Tables */
        .mobile-cards-view {
            display: none;
            flex-direction: column;
            gap: 10px;
        }
        .mobile-card-row {
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .mobile-card-title {
            font-weight: 700;
            color: #f1f5f9;
            font-size: 0.95rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .mobile-card-metrics {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .mobile-badge {
            font-size: 0.76rem;
            padding: 4px 8px;
            border-radius: 6px;
            font-family: var(--font-km);
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .mobile-badge.reg { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
        .mobile-badge.arr { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .mobile-badge.drp { background: rgba(239, 68, 68, 0.15); color: #f87171; }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 11px 18px;
            border-radius: var(--radius-md);
            font-family: var(--font-km);
            font-size: 0.92rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            touch-action: manipulation;
            line-height: 1.2;
        }
        .btn:active {
            transform: scale(0.97);
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #1d4ed8);
            color: #ffffff;
            box-shadow: 0 4px 14px var(--primary-glow);
        }
        .btn-primary:hover {
            background: linear-gradient(135deg, #1d4ed8, #1e40af);
        }
        .btn-success {
            background: linear-gradient(135deg, #059669, #047857);
            color: #ffffff;
            box-shadow: 0 4px 14px var(--success-glow);
        }
        .btn-success:hover {
            background: linear-gradient(135deg, #047857, #065f46);
        }
        .btn-warning {
            background: linear-gradient(135deg, #d97706, #b45309);
            color: #ffffff;
        }
        .btn-secondary {
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--card-border);
            color: #e2e8f0;
        }
        .btn-secondary:hover {
            background: rgba(51, 65, 85, 0.85);
        }
        .btn-sm {
            padding: 6px 12px;
            font-size: 0.8rem;
            border-radius: var(--radius-sm);
        }

        /* Action Grid */
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }
        .action-card {
            background: rgba(30, 41, 59, 0.55);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 16px;
            transition: border-color 0.2s;
        }
        .action-card:hover {
            border-color: rgba(56, 189, 248, 0.3);
        }
        .action-title {
            font-size: 1rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .action-desc {
            font-size: 0.82rem;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* Date Picker Component */
        .date-filter-box {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-bottom: 16px;
        }
        .date-inputs-row {
            display: flex;
            gap: 12px;
            align-items: flex-end;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .date-field {
            flex: 1;
            min-width: 220px;
        }
        .date-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Form Inputs */
        .form-input {
            width: 100%;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            color: #ffffff;
            font-family: var(--font-km);
            font-size: 16px; /* Prevents mobile Safari auto-zoom */
            transition: border-color 0.2s, box-shadow 0.2s;
            outline: none;
        }
        .form-input:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
            background: #0b1120;
        }

        /* Telegram Mockup Preview */
        .telegram-preview-wrapper {
            background: #0e1621;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: var(--radius-md);
            padding: 14px;
            margin-top: 14px;
            display: none;
        }
        .tg-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .tg-title {
            font-size: 0.82rem;
            font-weight: 700;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .tg-bubble {
            background: #182533;
            border-radius: 12px;
            border-bottom-left-radius: 4px;
            padding: 14px 16px;
            color: #f1f5f9;
            font-family: var(--font-km);
            font-size: 0.86rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 320px;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* Settings Form */
        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .settings-card {
            background: rgba(30, 41, 59, 0.45);
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .settings-card-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #38bdf8;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .form-label {
            font-size: 0.82rem;
            font-weight: 600;
            color: #cbd5e1;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .form-hint {
            font-size: 0.72rem;
            color: var(--text-dim);
            margin-bottom: 2px;
        }

        /* Log Console */
        .log-console {
            background: #040711;
            border: 1px solid var(--card-border);
            border-radius: var(--radius-md);
            padding: 16px;
            font-family: var(--font-mono);
            font-size: 0.78rem;
            color: #94a3b8;
            max-height: 460px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.6;
        }

        /* Modern Toast */
        #toast {
            position: fixed;
            bottom: calc(var(--bottom-nav-height) + 16px);
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            background: rgba(15, 23, 42, 0.96);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            color: #ffffff;
            padding: 12px 20px;
            border-radius: 9999px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
            border: 1px solid var(--card-border);
            font-size: 0.88rem;
            font-weight: 600;
            display: none;
            z-index: 9999;
            white-space: nowrap;
            max-width: 90vw;
            text-overflow: ellipsis;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        #toast.show {
            display: flex;
            align-items: center;
            gap: 8px;
            transform: translateX(-50%) translateY(0);
        }

        /* Custom PIN Modal */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            padding: 16px;
            opacity: 0;
            visibility: hidden;
            transition: all 0.25s ease;
        }
        .modal-overlay.active {
            opacity: 1;
            visibility: visible;
        }
        .modal-box {
            background: #0d1322;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: var(--radius-lg);
            padding: 24px;
            max-width: 360px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
            transform: scale(0.95);
            transition: transform 0.25s ease;
        }
        .modal-overlay.active .modal-box {
            transform: scale(1);
        }

        /* Responsive Breakpoints */
        @media (max-width: 768px) {
            body {
                padding-bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px) + 16px);
            }
            .tabs-desktop {
                display: none;
            }
            .mobile-bottom-nav {
                display: flex;
            }
            .header-actions .btn-tg {
                display: none;
            }
            .brand-title {
                font-size: 0.95rem;
            }
            .brand-subtitle {
                display: none;
            }
            .container {
                padding: 14px 12px;
            }
            .metrics-grid {
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .metric-card {
                padding: 14px;
            }
            .metric-val {
                font-size: 1.7rem;
            }
            .banner-pdf {
                flex-direction: column;
                align-items: stretch;
                padding: 16px;
            }
            .banner-actions {
                flex-direction: column;
            }
            .banner-actions .btn {
                width: 100%;
            }
            .actions-grid {
                grid-template-columns: 1fr;
            }
            .date-inputs-row {
                flex-direction: column;
                align-items: stretch;
            }
            .date-field {
                width: 100%;
                min-width: unset;
            }
            /* Switch desktop table to mobile card view */
            .table-responsive {
                display: none;
            }
            .mobile-cards-view {
                display: flex;
            }
            #toast {
                bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px) + 12px);
            }
        }

        /* Mobile PWA Install Floating Banner */
        .mobile-pwa-banner {
            display: none;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.15), rgba(37, 99, 235, 0.22));
            border: 1px solid rgba(56, 189, 248, 0.35);
            backdrop-filter: blur(12px);
            border-radius: 14px;
            padding: 10px 14px;
            margin: 10px 0 16px 0;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .pwa-banner-content {
            display: flex;
            align-items: center;
            gap: 10px;
            min-width: 0;
        }
        .pwa-banner-icon {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: rgba(56, 189, 248, 0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .pwa-banner-text {
            min-width: 0;
        }
        .pwa-banner-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: #ffffff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .pwa-banner-sub {
            font-size: 0.72rem;
            color: #94a3b8;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    </style>
</head>
<body>

    <!-- SVG Symbols Sprite (Zero CDN Latency, 100% Vector Crispness) -->
    <svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
      <symbol id="icon-cap" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21.42 10.922a1 1 0 0 0-.019-.838L12.83 2.18a2 2 0 0 0-1.66 0L2.6 10.084a1 1 0 0 0 0 1.832l8.57 7.908a2 2 0 0 0 1.66 0l8.57-7.908a1 1 0 0 0 .02-.994z"/>
        <path d="M22 10v6"/>
        <path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>
      </symbol>
      <symbol id="icon-telegram" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
      </symbol>
      <symbol id="icon-dashboard" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="7" height="9" x="3" y="3" rx="1"/>
        <rect width="7" height="5" x="14" y="3" rx="1"/>
        <rect width="7" height="9" x="14" y="12" rx="1"/>
        <rect width="7" height="5" x="3" y="16" rx="1"/>
      </symbol>
      <symbol id="icon-zap" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </symbol>
      <symbol id="icon-settings" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
        <circle cx="12" cy="12" r="3"/>
      </symbol>
      <symbol id="icon-history" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
        <path d="M3 3v5h5"/>
        <path d="M12 7v5l4 2"/>
      </symbol>
      <symbol id="icon-terminal" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="4 17 10 11 4 5"/>
        <line x1="12" x2="20" y1="19" y2="19"/>
      </symbol>
      <symbol id="icon-users" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </symbol>
      <symbol id="icon-file-text" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" x2="8" y1="13" y2="13"/>
        <line x1="16" x2="8" y1="17" y2="17"/>
        <line x1="10" x2="8" y1="9" y2="9"/>
      </symbol>
      <symbol id="icon-activity" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </symbol>
      <symbol id="icon-check-circle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </symbol>
      <symbol id="icon-arrow-left-right" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 8 22 12 18 16"/>
        <polyline points="6 16 2 12 6 8"/>
        <line x1="2" x2="22" y1="12" y2="12"/>
      </symbol>
      <symbol id="icon-x-circle" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" x2="9" y1="9" y2="15"/>
        <line x1="9" x2="15" y1="9" y2="15"/>
      </symbol>
      <symbol id="icon-trending-up" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
        <polyline points="16 7 22 7 22 13"/>
      </symbol>
      <symbol id="icon-award" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="6"/>
        <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>
      </symbol>
      <symbol id="icon-download" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" x2="12" y1="15" y2="3"/>
      </symbol>
      <symbol id="icon-send" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" x2="11" y1="2" y2="13"/>
        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </symbol>
      <symbol id="icon-refresh" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
        <path d="M3 3v5h5"/>
        <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>
        <path d="M16 21h5v-5"/>
      </symbol>
      <symbol id="icon-layers" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="12 2 2 7 12 12 22 7 12 2"/>
        <polyline points="2 17 12 22 22 17"/>
        <polyline points="2 12 12 17 22 12"/>
      </symbol>
      <symbol id="icon-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </symbol>
      <symbol id="icon-calendar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
        <line x1="16" x2="16" y1="2" y2="6"/>
        <line x1="8" x2="8" y1="2" y2="6"/>
        <line x1="3" x2="21" y1="10" y2="10"/>
      </symbol>
      <symbol id="icon-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
        <circle cx="12" cy="12" r="3"/>
      </symbol>
      <symbol id="icon-copy" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
      </symbol>
      <symbol id="icon-message" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </symbol>
      <symbol id="icon-bell" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>
      </symbol>
      <symbol id="icon-shield" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </symbol>
      <symbol id="icon-clock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </symbol>
      <symbol id="icon-database" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
      </symbol>
      <symbol id="icon-save" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
        <polyline points="17 21 17 13 7 13 7 21"/>
        <polyline points="7 3 7 8 15 8"/>
      </symbol>
      <symbol id="icon-lock" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </symbol>
      <symbol id="icon-sparkles" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
      </symbol>
      <symbol id="icon-pause" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="6" y="4" width="4" height="16"/>
        <rect x="14" y="4" width="4" height="16"/>
      </symbol>
      <symbol id="icon-play" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </symbol>
      <symbol id="icon-rocket" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
        <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
        <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
        <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
      </symbol>
    </svg>

    <!-- Header -->
    <header>
        <a href="#" class="brand" onclick="switchTab('dashboard'); return false;">
            <div class="brand-logo">
                <svg class="icon icon-md" style="stroke: #ffffff;"><use href="#icon-cap"></use></svg>
            </div>
            <div class="brand-info">
                <div class="brand-title">Bot ស្ថិតិអាហារូបករណ៍</div>
                <div class="brand-subtitle">Admin Management Portal</div>
            </div>
        </a>
        <div class="header-actions">
            <div id="header-status-pill" class="status-pill">
                <span id="header-pulse-dot" class="pulse-dot"></span>
                <span id="header-status-text">Online</span>
            </div>
            <button id="header-pause-btn" class="btn btn-secondary btn-sm" onclick="togglePauseResume()" style="padding: 0.35rem 0.75rem; font-size: 0.78rem;">
                <svg class="icon icon-sm"><use id="header-pause-icon" href="#icon-pause"></use></svg>
                <span id="header-pause-text">ផ្អាក</span>
            </button>
            <a href="https://web.telegram.org/" target="_blank" class="btn-tg">
                <svg class="icon icon-sm"><use href="#icon-telegram"></use></svg>
                <span>Telegram</span>
            </a>
        </div>
    </header>

    <!-- Main Container -->
    <div class="container">
        <!-- Mobile PWA Install Floating Banner -->
        <div id="mobile-pwa-banner" class="mobile-pwa-banner">
            <div class="pwa-banner-content">
                <div class="pwa-banner-icon">
                    <svg class="icon icon-md" style="color: #38bdf8;"><use href="#icon-cap"></use></svg>
                </div>
                <div class="pwa-banner-text">
                    <div class="pwa-banner-title">ដំឡើង App លើទូរស័ព្ទ</div>
                </div>
            </div>
            <button class="btn btn-primary btn-sm" onclick="triggerPwaInstall()" style="flex-shrink: 0;">
                <svg class="icon icon-sm"><use href="#icon-download"></use></svg>
                <span>ដំឡើង</span>
            </button>
        </div>

        <!-- Desktop Horizontal Segmented Tabs -->
        <nav class="tabs-desktop">
            <button class="tab-btn active" onclick="switchTab('dashboard')">
                <svg class="icon"><use href="#icon-dashboard"></use></svg>
                <span>ផ្ទាំងស្ថិតិ (Dashboard)</span>
            </button>
            <button class="tab-btn" onclick="switchTab('actions')">
                <svg class="icon"><use href="#icon-zap"></use></svg>
                <span>បញ្ជាផ្ទាល់ (Bot Controls)</span>
            </button>
            <button class="tab-btn" onclick="switchTab('settings')">
                <svg class="icon"><use href="#icon-settings"></use></svg>
                <span>ការកំណត់ (Settings)</span>
            </button>
            <button class="tab-btn" onclick="switchTab('history')">
                <svg class="icon"><use href="#icon-history"></use></svg>
                <span>ប្រវត្តិ & Logs</span>
            </button>
        </nav>

        <!-- ==================== TAB 1: DASHBOARD ==================== -->
        <div id="tab-dashboard" class="tab-content active">
            <!-- 4 Metric Cards -->
            <div class="metrics-grid">
                <!-- Card 1: Today Grand Total -->
                <div class="metric-card">
                    <div class="metric-top">
                        <span class="metric-title">
                            <svg class="icon icon-sm"><use href="#icon-users"></use></svg>
                            <span>ចុះឈ្មោះថ្ងៃនេះ</span>
                        </span>
                        <div class="metric-badge-icon">
                            <svg class="icon icon-sm"><use href="#icon-file-text"></use></svg>
                        </div>
                    </div>
                    <div class="metric-val" id="m-today-total">...</div>
                    <div class="metric-sub" id="m-today-date">កាលបរិច្ឆេទ...</div>
                </div>

                <!-- Card 2: Real Arrival Status (Part 2) -->
                <div class="metric-card" style="border-color: rgba(56, 189, 248, 0.25);">
                    <div class="metric-top">
                        <span class="metric-title">
                            <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-activity"></use></svg>
                            <span>ស្ថានភាពជាក់ស្តែង</span>
                        </span>
                        <div class="metric-badge-icon" style="color: #34d399;">
                            <svg class="icon icon-sm"><use href="#icon-check-circle"></use></svg>
                        </div>
                    </div>
                    <div class="status-chips-row" id="m-status-chips">
                        <div class="status-chip arrived">
                            <span class="status-chip-label">
                                <svg class="icon icon-sm" style="color: #34d399;"><use href="#icon-check-circle"></use></svg>
                                <span>មកដល់</span>
                            </span>
                            <span class="status-chip-num" id="chip-arr">0</span>
                        </div>
                        <div class="status-chip returned">
                            <span class="status-chip-label">
                                <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-arrow-left-right"></use></svg>
                                <span>ត្រឡប់</span>
                            </span>
                            <span class="status-chip-num" id="chip-ret">0</span>
                        </div>
                        <div class="status-chip dropped">
                            <span class="status-chip-label">
                                <svg class="icon icon-sm" style="color: #f87171;"><use href="#icon-x-circle"></use></svg>
                                <span>បោះបង់</span>
                            </span>
                            <span class="status-chip-num" id="chip-drp">0</span>
                        </div>
                    </div>
                </div>

                <!-- Card 3: Monthly Total -->
                <div class="metric-card">
                    <div class="metric-top">
                        <span class="metric-title">
                            <svg class="icon icon-sm"><use href="#icon-trending-up"></use></svg>
                            <span>និស្សិតសរុបប្រចាំខែ</span>
                        </span>
                        <div class="metric-badge-icon" style="color: #34d399;">
                            <svg class="icon icon-sm"><use href="#icon-dashboard"></use></svg>
                        </div>
                    </div>
                    <div class="metric-val" id="m-monthly-total">...</div>
                    <div class="metric-sub" style="color: #34d399;">សន្លឹកស្ថិតិប្រចាំថ្ងៃ</div>
                </div>

                <!-- Card 4: Top Major -->
                <div class="metric-card">
                    <div class="metric-top">
                        <span class="metric-title">
                            <svg class="icon icon-sm"><use href="#icon-award"></use></svg>
                            <span>ជំនាញនាំមុខ</span>
                        </span>
                        <div class="metric-badge-icon" style="color: #f59e0b;">
                            <svg class="icon icon-sm"><use href="#icon-award"></use></svg>
                        </div>
                    </div>
                    <div class="metric-val" style="font-size: 1.25rem; font-family: var(--font-km); line-height: 1.3;" id="m-top-major">...</div>
                    <div class="metric-sub" id="m-top-major-count">...</div>
                </div>
            </div>

            <!-- Quick PDF Action Banner -->
            <div class="banner-pdf">
                <div class="banner-content">
                    <div class="banner-title">
                        <svg class="icon icon-md" style="color: #60a5fa;"><use href="#icon-file-text"></use></svg>
                        <span>របាយការណ៍ប្រចាំខែ</span>
                    </div>
                </div>
                <div class="banner-actions">
                    <button class="btn btn-primary" onclick="triggerAction('send-monthly')">
                        <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                        <span>ផ្ញើ PDF ទៅ Telegram</span>
                    </button>
                </div>
            </div>

            <!-- Sources Summary Card -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #38bdf8;"><use href="#icon-layers"></use></svg>
                        <span>ចំនួនសរុបតាមប្រភពចុះឈ្មោះ</span>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="loadStatsData()">
                        <svg class="icon icon-sm"><use href="#icon-refresh"></use></svg>
                        <span>Refresh</span>
                    </button>
                </div>
                <div class="source-grid" id="sources-container">
                    <!-- Dynamically populated -->
                </div>
            </div>

            <!-- Majors Breakdown (Desktop Table + Mobile Cards) -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #60a5fa;"><use href="#icon-book"></use></svg>
                        <span>ស្ថិតិតាមមុខជំនាញទាំងអស់</span>
                    </div>
                    <span style="font-size: 0.78rem; color: var(--text-dim);" id="majors-count-badge">...</span>
                </div>

                <!-- Desktop Table View -->
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>មុខជំនាញ</th>
                                <th style="text-align: right;">ចំនួនចុះឈ្មោះ</th>
                                <th style="text-align: right;">មកដល់</th>
                                <th style="text-align: right;">បោះបង់</th>
                            </tr>
                        </thead>
                        <tbody id="majors-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>

                <!-- Mobile Card-based List View -->
                <div class="mobile-cards-view" id="majors-mobile-list">
                    <!-- Populated dynamically on phones -->
                </div>
            </div>
        </div>

        <!-- ==================== TAB 2: BOT ACTIONS ==================== -->
        <div id="tab-actions" class="tab-content">
            <!-- Daily Report by Date -->
            <div class="section-card" style="border-color: rgba(56, 189, 248, 0.3);">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #38bdf8;"><use href="#icon-calendar"></use></svg>
                        <span>ផ្ញើរបាយការណ៍ប្រចាំថ្ងៃតាមកាលបរិច្ឆេទ</span>
                    </div>
                </div>
                <p style="font-size: 0.84rem; color: var(--text-muted); margin-bottom: 16px; line-height: 1.5;">
                    ជ្រើសរើសកាលបរិច្ឆេទណាមួយ (ថ្ងៃនេះ ឬថ្ងៃកន្លងមក) ដើម្បីបង្កើត និងផ្ញើរបាយការណ៍ស្ថិតិទៅកាន់ Telegram Group ភ្លាមៗ។
                </p>

                <!-- Date Picker Controls -->
                <div class="date-filter-box">
                    <div class="date-inputs-row">
                        <div class="date-field">
                            <label class="date-label">
                                <svg class="icon icon-sm"><use href="#icon-calendar"></use></svg>
                                <span>ជ្រើសរើសកាលបរិច្ឆេទពី Sheet៖</span>
                            </label>
                            <select id="select-report-date" class="form-input" style="color: #38bdf8; font-weight: 600;" onchange="onDateDropdownChange(this.value)">
                                <option value="today">⭐️ ថ្ងៃនេះ (Today)</option>
                            </select>
                        </div>
                        <div class="date-field" style="max-width: 220px;">
                            <label class="date-label">
                                <svg class="icon icon-sm"><use href="#icon-calendar"></use></svg>
                                <span>ឬរើសថ្ងៃលើ Calendar៖</span>
                            </label>
                            <input type="date" id="input-custom-date" class="form-input" onchange="onCustomDateChange(this.value)">
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button class="btn btn-primary" type="button" onclick="sendDailyBySelectedDate()">
                            <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                            <span>ផ្ញើទៅ Telegram ភ្លាមៗ</span>
                        </button>
                    </div>
                </div>

                <!-- Telegram Chat Bubble Mockup Preview -->
                <div class="telegram-preview-wrapper" id="preview-wrapper">
                    <div class="tg-header">
                        <div class="tg-title">
                            <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-message"></use></svg>
                            <span>Telegram Message Preview</span>
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="copyPreviewText()">
                            <svg class="icon icon-sm"><use href="#icon-copy"></use></svg>
                            <span>ចម្លងអត្ថបទ</span>
                        </button>
                    </div>
                    <div class="tg-bubble" id="preview-box">
                        កំពុងរៀបចំ Preview...
                    </div>
                </div>
            </div>

            <!-- Other Direct Bot Controls -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #f59e0b;"><use href="#icon-zap"></use></svg>
                        <span>បញ្ជាការងារផ្ទាល់ទៅកាន់ Telegram</span>
                    </div>
                </div>
                <div class="actions-grid">
                    <div class="action-card">
                        <div>
                            <div class="action-title">
                                <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-calendar"></use></svg>
                                <span>ផ្ញើរបាយការណ៍ប្រចាំថ្ងៃ</span>
                            </div>
                            <div class="action-desc">បង្កើត និងផ្ញើរបាយការណ៍ស្ថិតិថ្ងៃនេះចូល Telegram Group ភ្លាមៗ។</div>
                        </div>
                        <button class="btn btn-primary" onclick="triggerAction('send-daily')">
                            <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                            <span>ផ្ញើរបាយការណ៍ថ្ងៃនេះ</span>
                        </button>
                    </div>

                    <div class="action-card">
                        <div>
                            <div class="action-title">
                                <svg class="icon icon-sm" style="color: #34d399;"><use href="#icon-file-text"></use></svg>
                                <span>ផ្ញើរបាយការណ៍ប្រចាំខែ</span>
                            </div>
                            <div class="action-desc">បង្កើតឯកសារ PDF តារាងស្អាត រួចផ្ញើចូល Telegram Group ភ្លាមៗ។</div>
                        </div>
                        <button class="btn btn-success" onclick="triggerAction('send-monthly')">
                            <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                            <span>ផ្ញើ PDF ឥឡូវនេះ</span>
                        </button>
                    </div>

                    <div class="action-card">
                        <div>
                            <div class="action-title">
                                <svg class="icon icon-sm" style="color: #f59e0b;"><use href="#icon-refresh"></use></svg>
                                <span>Force Sync Sheet & Diff</span>
                            </div>
                            <div class="action-desc">ទាញយកទិន្នន័យ Sheet ឡើងវិញ និងត្រួតពិនិត្យបម្រែបម្រួលដើម្បីផ្ញើ Alert ភ្លាមៗ។</div>
                        </div>
                        <button class="btn btn-warning" onclick="triggerAction('force-sync')">
                            <svg class="icon icon-sm"><use href="#icon-activity"></use></svg>
                            <span>Sync Sheet & Check</span>
                        </button>
                    </div>

                    <div class="action-card">
                        <div>
                            <div class="action-title">
                                <svg class="icon icon-sm" style="color: #a78bfa;"><use href="#icon-bell"></use></svg>
                                <span>ផ្ញើសារសាកល្បង</span>
                            </div>
                            <div class="action-desc">ផ្ញើសារសាកល្បងទៅកាន់ Telegram ដើម្បីផ្ទៀងផ្ទាត់ការតភ្ជាប់។</div>
                        </div>
                        <button class="btn btn-secondary" onclick="triggerAction('test-message')">
                            <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                            <span>ផ្ញើសារតេស្ត</span>
                        </button>
                    </div>

                    <div class="action-card">
                        <div>
                            <div class="action-title">
                                <svg class="icon icon-sm" style="color: #34d399;"><use href="#icon-users"></use></svg>
                                <span>តេស្ត Alert ចុះឈ្មោះថ្មី (Part 2)</span>
                            </div>
                            <div class="action-desc">ផ្ញើសារសាកល្បងដំណឹងចុះឈ្មោះថ្មីទៅ Telegram។</div>
                        </div>
                        <button class="btn btn-secondary" onclick="triggerAction('test-reg-alert')">
                            <svg class="icon icon-sm"><use href="#icon-send"></use></svg>
                            <span>តេស្ត Alert ឈ្មោះថ្មី</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- ==================== TAB 3: SETTINGS ==================== -->
        <div id="tab-settings" class="tab-content">
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #38bdf8;"><use href="#icon-settings"></use></svg>
                        <span>ការកំណត់ប្រព័ន្ធ (Bot Settings)</span>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="saveSettingsForm()">
                        <svg class="icon icon-sm"><use href="#icon-save"></use></svg>
                        <span>រក្សាទុក (Save)</span>
                    </button>
                </div>

                <form id="settings-form">
                    <div class="settings-grid">
                        <!-- Group 1: Telegram Config -->
                        <div class="settings-card">
                            <div class="settings-card-title">
                                <svg class="icon icon-sm"><use href="#icon-shield"></use></svg>
                                <span>Telegram & Security</span>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Report Chat ID</label>
                                <div class="form-hint">ID Group ឬ Channel សម្រាប់ផ្ញើរបាយការណ៍</div>
                                <input type="text" class="form-input" id="cfg-REPORT_CHAT_ID" name="REPORT_CHAT_ID">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Allowed Chat IDs</label>
                                <div class="form-hint">Chat ID ដែលអនុញ្ញាត (បំបែកដោយក្បៀស ,)</div>
                                <input type="text" class="form-input" id="cfg-ALLOWED_CHAT_IDS" name="ALLOWED_CHAT_IDS">
                            </div>
                            <div class="form-group">
                                <label class="form-label">Admin Management PIN</label>
                                <div class="form-hint">លេខកូដ PIN សម្រាប់បញ្ជា Web UI</div>
                                <input type="password" class="form-input" id="cfg-ADMIN_PIN" name="ADMIN_PIN">
                            </div>
                        </div>

                        <!-- Group 2: Timers & Schedule -->
                        <div class="settings-card">
                            <div class="settings-card-title">
                                <svg class="icon icon-sm"><use href="#icon-clock"></use></svg>
                                <span>ពេលវេលាកំណត់ (Schedules)</span>
                            </div>
                            <div class="form-group">
                                <label class="form-label">ម៉ោងផ្ញើប្រចាំថ្ងៃ (Daily Time)</label>
                                <div class="form-hint">ទម្រង់ 24h ម៉ោង:នាទី (ឧ. 17:00 សម្រាប់ 5:00 PM)</div>
                                <input type="text" class="form-input" id="cfg-DAILY_REPORT_TIME" name="DAILY_REPORT_TIME">
                            </div>
                            <div class="form-group">
                                <label class="form-label">ថ្ងៃ និងម៉ោងផ្ញើប្រចាំខែ (Monthly)</label>
                                <div class="form-hint">ថ្ងៃទី (ឧ. 1) និងម៉ោង (ឧ. 08:00)</div>
                                <div style="display: flex; gap: 8px;">
                                    <input type="number" class="form-input" id="cfg-MONTHLY_REPORT_DAY" name="MONTHLY_REPORT_DAY" style="width: 85px;" min="1" max="31">
                                    <input type="text" class="form-input" id="cfg-MONTHLY_REPORT_TIME" name="MONTHLY_REPORT_TIME" style="flex: 1;">
                                </div>
                            </div>
                            <div class="form-group">
                                <label class="form-label">ប្រេកង់តាមដាន Sheet (Polling)</label>
                                <div class="form-hint">ចំនួនវិនាទីក្នុងការពិនិត្យមើល Sheet ម្តង</div>
                                <input type="number" class="form-input" id="cfg-POLLING_INTERVAL_SECONDS" name="POLLING_INTERVAL_SECONDS" min="15">
                            </div>
                        </div>

                        <!-- Group 3: Google Sheets -->
                        <div class="settings-card" style="grid-column: 1 / -1;">
                            <div class="settings-card-title">
                                <svg class="icon icon-sm"><use href="#icon-database"></use></svg>
                                <span>Google Sheets Integration</span>
                            </div>
                            <div class="form-group">
                                <label class="form-label">Google Spreadsheet ID</label>
                                <input type="text" class="form-input" id="cfg-SPREADSHEET_ID" name="SPREADSHEET_ID">
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                                <div class="form-group">
                                    <label class="form-label">ស្ថិតិថ្ងៃនឹង GID</label>
                                    <input type="text" class="form-input" id="cfg-TODAY_SHEET_GID" name="TODAY_SHEET_GID">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">ស្ថិតិប្រចាំថ្ងៃ GID</label>
                                    <input type="text" class="form-input" id="cfg-HISTORICAL_SHEET_GID" name="HISTORICAL_SHEET_GID">
                                </div>
                                <div class="form-group">
                                    <label class="form-label">Part 2 -Registrations GID</label>
                                    <input type="text" class="form-input" id="cfg-REGISTRATIONS_SHEET_GID" name="REGISTRATIONS_SHEET_GID">
                                </div>
                            </div>
                        </div>
                    </div>

                    <button type="button" class="btn btn-primary" onclick="saveSettingsForm()" style="width: 100%; max-width: 280px;">
                        <svg class="icon icon-sm"><use href="#icon-save"></use></svg>
                        <span>រក្សាទុកការកំណត់ទាំងអស់</span>
                    </button>
                </form>
            </div>
        </div>

        <!-- ==================== TAB 4: HISTORY & LOGS ==================== -->
        <div id="tab-history" class="tab-content">
            <!-- Sent Reports History -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #38bdf8;"><use href="#icon-history"></use></svg>
                        <span>ប្រវត្តិនៃការផ្ញើរបាយការណ៍</span>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="loadHistoryData()">
                        <svg class="icon icon-sm"><use href="#icon-refresh"></use></svg>
                        <span>Refresh</span>
                    </button>
                </div>

                <!-- Desktop Table View -->
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>ប្រភេទ</th>
                                <th>កាលបរិច្ឆេទ</th>
                                <th>ម៉ោងផ្ញើ</th>
                                <th>ស្ថានភាព</th>
                                <th>Message ID</th>
                            </tr>
                        </thead>
                        <tbody id="history-table-body">
                            <!-- Populated dynamically -->
                        </tbody>
                    </table>
                </div>

                <!-- Mobile Card List View -->
                <div class="mobile-cards-view" id="history-mobile-list">
                    <!-- Populated dynamically on phones -->
                </div>
            </div>

            <!-- Activity Logs Console -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <svg class="icon" style="color: #38bdf8;"><use href="#icon-terminal"></use></svg>
                        <span>Live System Activity Logs</span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary btn-sm" onclick="copyLogs()">
                            <svg class="icon icon-sm"><use href="#icon-copy"></use></svg>
                            <span>Copy</span>
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="loadLogsData()">
                            <svg class="icon icon-sm"><use href="#icon-refresh"></use></svg>
                            <span>Refresh</span>
                        </button>
                    </div>
                </div>
                <div class="log-console" id="log-console">កំពុងទាញយក Logs...</div>
            </div>
        </div>
    </div>

    <!-- Mobile Bottom Navigation Bar -->
    <nav class="mobile-bottom-nav">
        <button class="nav-item active" onclick="switchTab('dashboard')">
            <svg class="nav-icon"><use href="#icon-dashboard"></use></svg>
            <span>ផ្ទាំងស្ថិតិ</span>
        </button>
        <button class="nav-item" onclick="switchTab('actions')">
            <svg class="nav-icon"><use href="#icon-zap"></use></svg>
            <span>បញ្ជា Bot</span>
        </button>
        <button class="nav-item" onclick="switchTab('settings')">
            <svg class="nav-icon"><use href="#icon-settings"></use></svg>
            <span>កំណត់</span>
        </button>
        <button class="nav-item" onclick="switchTab('history')">
            <svg class="nav-icon"><use href="#icon-terminal"></use></svg>
            <span>Logs</span>
        </button>
    </nav>

    <!-- Custom PIN Entry Modal -->
    <div class="modal-overlay" id="pin-modal">
        <div class="modal-box">
            <div style="margin-bottom: 8px;">
                <svg class="icon icon-xl" style="color: #38bdf8;"><use href="#icon-lock"></use></svg>
            </div>
            <div style="font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 6px;">Admin Authentication</div>
            <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 18px;">សូមបញ្ចូលលេខកូដ Admin PIN ដើម្បីបន្ត៖</div>
            <input type="password" id="modal-pin-input" class="form-input" style="text-align: center; font-size: 1.2rem; letter-spacing: 4px; margin-bottom: 14px;" placeholder="••••••" autofocus>
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-secondary" style="flex: 1;" onclick="closePinModal(null)">
                    <svg class="icon icon-sm"><use href="#icon-x-circle"></use></svg>
                    <span>បោះបង់</span>
                </button>
                <button class="btn btn-primary" style="flex: 1;" onclick="submitPinModal()">
                    <svg class="icon icon-sm"><use href="#icon-check-circle"></use></svg>
                    <span>យល់ព្រម</span>
                </button>
            </div>
        </div>
    </div>

    <!-- PWA / Mobile Install Instructions Modal -->
    <div class="modal-overlay" id="pwa-install-modal">
        <div class="modal-box" style="max-width: 440px; text-align: left;">
            <div style="text-align: center; margin-bottom: 12px;">
                <svg class="icon icon-xl" style="color: #38bdf8;"><use href="#icon-download"></use></svg>
                <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin-top: 6px;">ដំឡើង App លើទូរស័ព្ទដៃ</div>
                <div style="font-size: 0.82rem; color: var(--text-muted);">ដំណើរការដូច App ពិតៗ ពេញអេក្រង់ និងមិនបាច់វាយ URL</div>
            </div>
            
            <div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px; margin-bottom: 16px; font-size: 0.88rem; line-height: 1.6;">
                <div style="font-weight: 600; color: #38bdf8; margin-bottom: 6px;">📱 សម្រាប់ iPhone / iPad (Safari)៖</div>
                <div style="margin-bottom: 4px;">១. ចុចប៊ូតុង <strong>Share</strong> (រូប <span style="font-size:1.05rem;">⎋</span> ឬ <svg class="icon icon-sm" style="display:inline; vertical-align:-0.15rem;"><use href="#icon-send"></use></svg>) នៅរបារក្រោម Safari</div>
                <div style="margin-bottom: 4px;">២. អូសចុះក្រោម រួចជ្រើសរើស <strong>"Add to Home Screen"</strong> (➕ បន្ថែមទៅអេក្រង់ដើម)</div>
                <div>៣. ចុចពាក្យ <strong>"Add"</strong> នៅជ្រុងខាងស្តាំខាងលើ</div>
                
                <div style="border-top: 1px solid rgba(255,255,255,0.08); margin: 10px 0;"></div>
                
                <div style="font-weight: 600; color: #34d399; margin-bottom: 6px;">🤖 សម្រាប់ Android (Chrome)៖</div>
                <div>ចុចប៊ូតុង <strong>"ដំឡើងឥឡូវនេះ"</strong> ខាងក្រោម ឬចុច Menu (⋮) ជ្រើសរើស <strong>"Install app"</strong> ឬ <strong>"Add to Home screen"</strong>។</div>
            </div>

            <div style="display: flex; gap: 10px;">
                <button class="btn btn-secondary" style="flex: 1;" onclick="closePwaModal()">
                    <span>បិទ</span>
                </button>
                <button id="pwa-native-install-btn" class="btn btn-primary" style="flex: 1; display: none;" onclick="executeNativeInstall()">
                    <svg class="icon icon-sm"><use href="#icon-download"></use></svg>
                    <span>ដំឡើងឥឡូវនេះ</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Floating Toast Notification -->
    <div id="toast"></div>

    <script>
        let pendingPinCallback = null;

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            const iconSvg = isError 
                ? '<svg class="icon icon-sm" style="color: #ef4444;"><use href="#icon-x-circle"></use></svg>'
                : '<svg class="icon icon-sm" style="color: #10b981;"><use href="#icon-check-circle"></use></svg>';
            t.innerHTML = iconSvg + '<span>' + msg + '</span>';
            t.style.borderColor = isError ? 'rgba(239, 68, 68, 0.5)' : 'rgba(16, 185, 129, 0.5)';
            t.style.background = isError ? 'rgba(35, 10, 15, 0.95)' : 'rgba(10, 30, 20, 0.95)';
            t.classList.add('show');
            setTimeout(() => { t.classList.remove('show'); }, 3500);
        }

        function promptPin(callback) {
            const savedPin = localStorage.getItem('bot_admin_pin');
            if (savedPin) {
                callback(savedPin);
                return;
            }
            pendingPinCallback = callback;
            const modal = document.getElementById('pin-modal');
            const input = document.getElementById('modal-pin-input');
            input.value = '';
            modal.classList.add('active');
            setTimeout(() => input.focus(), 100);
        }

        function closePinModal(pin) {
            document.getElementById('pin-modal').classList.remove('active');
            if (pendingPinCallback) {
                if (pin) pendingPinCallback(pin);
                pendingPinCallback = null;
            }
        }

        function submitPinModal() {
            const pin = document.getElementById('modal-pin-input').value.trim() || '123456';
            localStorage.setItem('bot_admin_pin', pin);
            closePinModal(pin);
        }

        document.getElementById('modal-pin-input').addEventListener('keyup', function(e) {
            if (e.key === 'Enter') submitPinModal();
        });

        function switchTab(tabId) {
            // Update desktop tabs
            document.querySelectorAll('.tab-btn').forEach(b => {
                const isMatch = b.getAttribute('onclick').includes(tabId);
                b.classList.toggle('active', isMatch);
            });
            // Update mobile bottom nav
            document.querySelectorAll('.nav-item').forEach(b => {
                const isMatch = b.getAttribute('onclick').includes(tabId);
                b.classList.toggle('active', isMatch);
            });
            // Update panes
            document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
            const activePane = document.getElementById('tab-' + tabId);
            if (activePane) activePane.classList.add('active');

            window.scrollTo({ top: 0, behavior: 'smooth' });

            if (tabId === 'dashboard') loadStatsData();
            if (tabId === 'actions') loadAvailableDates();
            if (tabId === 'settings') loadSettingsData();
            if (tabId === 'history') { loadHistoryData(); loadLogsData(); }
        }

        async function loadStatsData() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                if (data.status === 'ok') {
                    if (data.is_paused !== undefined) {
                        updatePausedStateUI(data.is_paused);
                    }
                    const today = data.today;
                    const hist = data.historical;

                    document.getElementById('m-today-total').innerText = today.grand_total + ' នាក់';
                    document.getElementById('m-today-date').innerText = 'កាលបរិច្ឆេទ៖ ' + today.date_str;
                    document.getElementById('m-monthly-total').innerText = hist.grand_total + ' នាក់';

                    // Update arrival chips
                    if (document.getElementById('chip-arr')) {
                        document.getElementById('chip-arr').innerText = today.total_arrived ?? 0;
                        document.getElementById('chip-ret').innerText = today.total_returned ?? 0;
                        document.getElementById('chip-drp').innerText = today.total_dropped ?? 0;
                    }

                    // Top major
                    let topMajor = '-';
                    let topCount = 0;
                    today.categories.forEach(c => {
                        if (c.registered > topCount) {
                            topCount = c.registered;
                            topMajor = c.name;
                        }
                    });
                    document.getElementById('m-top-major').innerText = topMajor;
                    document.getElementById('m-top-major-count').innerText = topCount > 0 ? (topCount + ' នាក់') : 'គ្មាន';

                    // Sources
                    const srcBox = document.getElementById('sources-container');
                    srcBox.innerHTML = '';
                    for (const [src, cnt] of Object.entries(today.sources_summary)) {
                        srcBox.innerHTML += `
                            <div class="source-box">
                                <div style="margin-bottom: 4px; color: #38bdf8;">
                                    <svg class="icon icon-sm"><use href="#icon-layers"></use></svg>
                                </div>
                                <div class="source-name">${src}</div>
                                <div class="source-num">${cnt}</div>
                            </div>
                        `;
                    }

                    // Majors table (Desktop) & Cards (Mobile)
                    const tbody = document.getElementById('majors-table-body');
                    const mlist = document.getElementById('majors-mobile-list');
                    tbody.innerHTML = '';
                    mlist.innerHTML = '';

                    const activeCats = today.categories.filter(c => c.registered > 0);
                    document.getElementById('majors-count-badge').innerText = activeCats.length + ' ជំនាញមានទិន្នន័យ';

                    today.categories.forEach(c => {
                        tbody.innerHTML += `
                            <tr>
                                <td><b>${c.name}</b></td>
                                <td style="text-align: right;"><span class="badge-count">${c.registered}</span></td>
                                <td style="text-align: right; color: #34d399;">${c.arrived}</td>
                                <td style="text-align: right; color: #f87171;">${c.dropped}</td>
                            </tr>
                        `;
                        mlist.innerHTML += `
                            <div class="mobile-card-row">
                                <div class="mobile-card-title">
                                    <span style="display: flex; align-items: center; gap: 6px;">
                                        <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-book"></use></svg>
                                        <span>${c.name}</span>
                                    </span>
                                    <span class="badge-count">${c.registered} នាក់</span>
                                </div>
                                <div class="mobile-card-metrics">
                                    <span class="mobile-badge arr">
                                        <svg class="icon icon-sm"><use href="#icon-check-circle"></use></svg>
                                        <span>មកដល់: ${c.arrived}</span>
                                    </span>
                                    <span class="mobile-badge drp">
                                        <svg class="icon icon-sm"><use href="#icon-x-circle"></use></svg>
                                        <span>បោះបង់: ${c.dropped}</span>
                                    </span>
                                </div>
                            </div>
                        `;
                    });
                }
            } catch (err) {
                console.error(err);
            }
        }

        function triggerAction(actionName) {
            promptPin(async (pin) => {
                showToast('កំពុងដំណើរការ ' + actionName + '...');
                try {
                    const res = await fetch('/api/actions/' + actionName, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-PIN': pin }
                    });
                    const resData = await res.json();
                    if (resData.status === 'ok') {
                        showToast(resData.message || 'បានបញ្ជាដោយជោគជ័យ!');
                    } else {
                        showToast('បរាជ័យ៖ ' + (resData.error || 'មានបញ្ហា'), true);
                    }
                } catch (e) {
                    showToast('បរាជ័យក្នុងការតភ្ជាប់៖ ' + e, true);
                }
            });
        }

        let isBotPaused = false;

        function updatePausedStateUI(isPaused) {
            isBotPaused = !!isPaused;

            // Update Header Status Pill and Button
            const pill = document.getElementById('header-status-pill');
            const dot = document.getElementById('header-pulse-dot');
            const txt = document.getElementById('header-status-text');
            const pIcon = document.getElementById('header-pause-icon');
            const pTxt = document.getElementById('header-pause-text');
            const pBtn = document.getElementById('header-pause-btn');

            if (pill && txt) {
                if (isBotPaused) {
                    pill.style.background = 'rgba(245, 158, 11, 0.15)';
                    pill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                    pill.style.color = '#fbbf24';
                    if (dot) {
                        dot.style.background = '#f59e0b';
                        dot.style.boxShadow = '0 0 8px rgba(245, 158, 11, 0.6)';
                    }
                    txt.innerText = 'ផ្អាក (Paused)';
                    if (pIcon) pIcon.setAttribute('href', '#icon-play');
                    if (pTxt) pTxt.innerText = 'បន្ត';
                    if (pBtn) pBtn.className = 'btn btn-success btn-sm';
                } else {
                    pill.style.background = 'rgba(16, 185, 129, 0.12)';
                    pill.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                    pill.style.color = '#34d399';
                    if (dot) {
                        dot.style.background = '#10b981';
                        dot.style.boxShadow = '0 0 8px rgba(16, 185, 129, 0.6)';
                    }
                    txt.innerText = 'Online';
                    if (pIcon) pIcon.setAttribute('href', '#icon-pause');
                    if (pTxt) pTxt.innerText = 'ផ្អាក';
                    if (pBtn) pBtn.className = 'btn btn-secondary btn-sm';
                }
            }
        }

        function togglePauseResume() {
            const action = isBotPaused ? 'resume' : 'pause';
            const actionKh = isBotPaused ? 'បន្តដំណើរការ' : 'ផ្អាក';
            promptPin(async (pin) => {
                showToast('កំពុងដំណើរការ ' + actionKh + ' Bot...');
                try {
                    const res = await fetch('/api/actions/' + action, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-PIN': pin }
                    });
                    const resData = await res.json();
                    if (resData.status === 'ok') {
                        updatePausedStateUI(resData.is_paused);
                        showToast(resData.message || (resData.is_paused ? 'បានផ្អាក Bot ជោគជ័យ!' : 'Bot បានបន្តដំណើរការវិញហើយ!'));
                    } else {
                        showToast('បរាជ័យ៖ ' + (resData.error || 'មានបញ្ហា'), true);
                    }
                } catch (e) {
                    showToast('បរាជ័យក្នុងការតភ្ជាប់៖ ' + e, true);
                }
            });
        }

        async function loadSettingsData() {
            try {
                const res = await fetch('/api/settings');
                const cfg = await res.json();
                for (const [k, v] of Object.entries(cfg)) {
                    const el = document.getElementById('cfg-' + k);
                    if (el) el.value = v;
                }
            } catch (e) {
                console.error(e);
            }
        }

        function saveSettingsForm() {
            promptPin(async (pin) => {
                const form = document.getElementById('settings-form');
                const formData = new FormData(form);
                const payload = {};
                formData.forEach((value, key) => { payload[key] = value; });

                showToast('កំពុងរក្សាទុកការកំណត់...');
                try {
                    const res = await fetch('/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-PIN': pin },
                        body: JSON.stringify(payload)
                    });
                    const resData = await res.json();
                    if (resData.status === 'ok') {
                        showToast('ការកំណត់ត្រូវបានរក្សាទុកជោគជ័យ!');
                    } else {
                        showToast('បរាជ័យ៖ ' + (resData.error || 'PIN មិនត្រឹមត្រូវ'), true);
                    }
                } catch (e) {
                    showToast('មានបញ្ហាតភ្ជាប់៖ ' + e, true);
                }
            });
        }

        async function loadHistoryData() {
            try {
                const res = await fetch('/api/history');
                const list = await res.json();
                const tbody = document.getElementById('history-table-body');
                const mlist = document.getElementById('history-mobile-list');
                tbody.innerHTML = '';
                mlist.innerHTML = '';

                if (!list || list.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #9ca3af;">មិនទាន់មានប្រវត្តិផ្ញើទេ</td></tr>';
                    mlist.innerHTML = '<div style="text-align: center; color: #9ca3af; padding: 16px;">មិនទាន់មានប្រវត្តិផ្ញើទេ</div>';
                    return;
                }

                list.forEach(r => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${r.id}</td>
                            <td><b>${r.report_type}</b></td>
                            <td>${r.target_date}</td>
                            <td>${r.sent_at}</td>
                            <td><span style="color: #34d399;">${r.status}</span></td>
                            <td><code>${r.message_id || '-'}</code></td>
                        </tr>
                    `;
                    mlist.innerHTML += `
                        <div class="mobile-card-row">
                            <div class="mobile-card-title">
                                <span style="display: flex; align-items: center; gap: 6px;">
                                    <svg class="icon icon-sm" style="color: #38bdf8;"><use href="#icon-file-text"></use></svg>
                                    <span>${r.report_type}</span>
                                </span>
                                <span style="font-size: 0.76rem; color: #34d399; font-weight: 600;">${r.status}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px;">
                                <svg class="icon icon-sm"><use href="#icon-calendar"></use></svg>
                                <span>${r.target_date} &bull; ${r.sent_at}</span>
                            </div>
                            <div style="font-size: 0.74rem; color: var(--text-dim);">Msg ID: ${r.message_id || '-'}</div>
                        </div>
                    `;
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function loadLogsData() {
            try {
                const res = await fetch('/api/logs');
                const text = await res.text();
                const el = document.getElementById('log-console');
                el.innerText = text || '(Logs Empty)';
                el.scrollTop = el.scrollHeight;
            } catch (e) {
                console.error(e);
            }
        }

        function copyLogs() {
            const text = document.getElementById('log-console').innerText;
            navigator.clipboard.writeText(text).then(() => {
                showToast('Logs ត្រូវបានចម្លង (Copied)!');
            });
        }

        async function loadAvailableDates() {
            try {
                const res = await fetch('/api/available-dates');
                const data = await res.json();
                if (data.status === 'ok') {
                    const sel = document.getElementById('select-report-date');
                    sel.innerHTML = `<option value="today">⭐️ ថ្ងៃនេះ (Today - ${data.today_date})</option>`;
                    if (data.dates && data.dates.length > 0) {
                        data.dates.forEach(d => {
                            const isStar = d.total > 0 ? '⭐️ ' : '';
                            sel.innerHTML += `<option value="${d.date}">${isStar}${d.label}</option>`;
                        });
                    }
                }
            } catch (e) {
                console.error('Error loading available dates:', e);
            }
        }

        function onDateDropdownChange(val) {
            if (val && val !== 'today') {
                document.getElementById('input-custom-date').value = val;
            } else {
                document.getElementById('input-custom-date').value = '';
            }
        }

        function onCustomDateChange(val) {
            if (val) {
                const sel = document.getElementById('select-report-date');
                for (let i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].value === val) {
                        sel.selectedIndex = i;
                        break;
                    }
                }
            }
        }

        async function previewDailyDate() {
            const dateVal = document.getElementById('input-custom-date').value || document.getElementById('select-report-date').value || 'today';
            const wrapper = document.getElementById('preview-wrapper');
            const box = document.getElementById('preview-box');
            wrapper.style.display = 'block';
            box.innerText = 'កំពុងរៀបចំ Preview សម្រាប់ថ្ងៃ ' + dateVal + '...';
            try {
                const res = await fetch('/api/daily-preview?date=' + encodeURIComponent(dateVal));
                const data = await res.json();
                if (data.status === 'ok') {
                    box.innerText = data.text;
                } else {
                    box.innerText = 'មិនមានទិន្នន័យ៖ ' + (data.error || 'Unknown error');
                }
            } catch (e) {
                box.innerText = 'បរាជ័យក្នុងការតភ្ជាប់៖ ' + e;
            }
        }

        function copyPreviewText() {
            const box = document.getElementById('preview-box');
            navigator.clipboard.writeText(box.innerText).then(() => {
                showToast('បានចម្លងអត្ថបទរបាយការណ៍!');
            });
        }

        function sendDailyBySelectedDate() {
            const dateVal = document.getElementById('input-custom-date').value || document.getElementById('select-report-date').value || 'today';
            promptPin(async (pin) => {
                showToast('កំពុងផ្ញើរបាយការណ៍ ' + dateVal + ' ទៅ Telegram...');
                try {
                    const res = await fetch('/api/actions/send-daily', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-Admin-PIN': pin },
                        body: JSON.stringify({ date: dateVal })
                    });
                    const resData = await res.json();
                    if (resData.status === 'ok') {
                        showToast(resData.message || 'បានផ្ញើដោយជោគជ័យ!');
                    } else {
                        showToast('បរាជ័យ៖ ' + (resData.error || 'មានបញ្ហា'), true);
                    }
                } catch (e) {
                    showToast('បរាជ័យក្នុងការតភ្ជាប់៖ ' + e, true);
                }
            });
        }

        // ==================== PWA INSTALLATION LOGIC ====================
        let deferredPwaPrompt = null;
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js').catch(err => {
                    console.warn('SW registration failed:', err);
                });
            });
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPwaPrompt = e;
            const banner = document.getElementById('mobile-pwa-banner');
            if (banner && !isStandalone) banner.style.display = 'flex';
            const nativeBtn = document.getElementById('pwa-native-install-btn');
            if (nativeBtn) nativeBtn.style.display = 'inline-flex';
        });

        window.addEventListener('appinstalled', () => {
            showToast('🎉 បានដំឡើង App លើទូរស័ព្ទបានជោគជ័យ!');
            const banner = document.getElementById('mobile-pwa-banner');
            if (banner) banner.style.display = 'none';
            deferredPwaPrompt = null;
        });

        function triggerPwaInstall() {
            if (deferredPwaPrompt) {
                executeNativeInstall();
            } else {
                openPwaModal();
            }
        }

        function executeNativeInstall() {
            if (deferredPwaPrompt) {
                deferredPwaPrompt.prompt();
                deferredPwaPrompt.userChoice.then((result) => {
                    if (result.outcome === 'accepted') {
                        showToast('កំពុងដំឡើង App...');
                        closePwaModal();
                    }
                    deferredPwaPrompt = null;
                });
            } else {
                openPwaModal();
            }
        }

        function openPwaModal() {
            const m = document.getElementById('pwa-install-modal');
            if (m) m.classList.add('active');
        }

        function closePwaModal() {
            const m = document.getElementById('pwa-install-modal');
            if (m) m.classList.remove('active');
        }

        // Show banner if mobile browser and not standalone
        if (!isStandalone) {
            const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
            if (isMobile) {
                setTimeout(() => {
                    const banner = document.getElementById('mobile-pwa-banner');
                    if (banner) banner.style.display = 'flex';
                }, 800);
            }
        }

        // Initialize dashboard
        loadStatsData();
        loadAvailableDates();
        setInterval(loadStatsData, 30000);
    </script>
</body>
</html>
"""

class DashboardRequestHandler(BaseHTTPRequestHandler):
    def address_string(self):
        # Disable reverse DNS lookup on Windows (avoids 2.0s delay per request)
        return str(self.client_address[0])

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            encoded = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        # PWA Manifest, Service Worker & Icons
        if self.path in ["/manifest.json", "/manifest.webmanifest"]:
            m_path = os.path.join(config.BASE_PROJECT_DIR, "assets", "manifest.json")
            if os.path.exists(m_path):
                with open(m_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if self.path == "/sw.js":
            sw_path = os.path.join(config.BASE_PROJECT_DIR, "assets", "sw.js")
            if os.path.exists(sw_path):
                with open(sw_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if self.path in ["/icon-192.png", "/icon-512.png", "/icon-180.png", "/favicon.ico"]:
            icon_file = "icon-192.png" if self.path == "/favicon.ico" else self.path.lstrip("/")
            icon_path = os.path.join(config.BASE_PROJECT_DIR, "assets", "icons", icon_file)
            if not os.path.exists(icon_path):
                icon_path = os.path.join(config.BASE_PROJECT_DIR, "assets", "icons", "icon-192.png")
            if os.path.exists(icon_path):
                with open(icon_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        if self.path in ["/health", "/healthz"]:
            self.send_json({"status": "ok", "service": "telegram-bot"})
            return

        if self.path == "/api/available-dates":
            try:
                from src.parser import get_available_dates
                h_rows = sheets_client.get_historical_sheet_rows()
                dates = get_available_dates(h_rows)
                t_rows = sheets_client.get_today_sheet_rows()
                reg_rows = sheets_client.get_registrations_sheet_rows()
                today_data = parse_today_sheet(t_rows, reg_rows=reg_rows)
                self.send_json({
                    "status": "ok",
                    "today_date": today_data.date_str,
                    "dates": dates
                })
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path.startswith("/api/daily-preview"):
            try:
                from urllib.parse import urlparse, parse_qs
                from src.parser import parse_date_report
                query = parse_qs(urlparse(self.path).query)
                target_date = query.get("date", ["today"])[0]
                t_rows = sheets_client.get_today_sheet_rows()
                h_rows = sheets_client.get_historical_sheet_rows()
                reg_rows = sheets_client.get_registrations_sheet_rows()
                t_data = parse_date_report(h_rows, t_rows, target_date, reg_rows=reg_rows)
                msg_text = format_daily_report(t_data)
                self.send_json({"status": "ok", "text": msg_text, "date": t_data.date_str})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/download-monthly-pdf":
            try:
                import time
                from src.pdf_generator import generate_monthly_report_pdf
                now = datetime.now(TIMEZONE)
                pdf_filename = f"Monthly_Report_{now.year}_{now.month:02d}.pdf"
                pdf_path = os.path.join(config.DATA_DIR, pdf_filename)

                # If cache is valid (under 3 mins), serve directly from disk instantly
                if not (os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000 and (time.time() - os.path.getmtime(pdf_path) < 180)):
                    h_rows = sheets_client.get_historical_sheet_rows()
                    reg_rows = sheets_client.get_registrations_sheet_rows()
                    h_data = parse_historical_sheet(h_rows, reg_rows=reg_rows)
                    pdf_path = generate_monthly_report_pdf(h_data, force_refresh=False)

                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", "inline; filename=Monthly_Scholarship_Report.pdf")
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/stats":
            try:
                t_rows = sheets_client.get_today_sheet_rows()
                reg_rows = sheets_client.get_registrations_sheet_rows()
                today_data = parse_today_sheet(t_rows, reg_rows=reg_rows)
                h_rows = sheets_client.get_historical_sheet_rows()
                hist_data = parse_historical_sheet(h_rows, reg_rows=reg_rows)

                self.send_json({
                    "status": "ok",
                    "is_paused": (storage.get_setting("bot_paused") == "true"),
                    "today": {
                        "date_str": today_data.date_str,
                        "grand_total": today_data.grand_total,
                        "total_arrived": today_data.total_arrived,
                        "total_returned": today_data.total_returned,
                        "total_dropped": today_data.total_dropped,
                        "sources_summary": today_data.sources_summary,
                        "categories": [
                            {
                                "name": c.name,
                                "registered": c.registered,
                                "arrived": c.arrived,
                                "dropped": c.dropped
                            }
                            for c in today_data.categories
                        ]
                    },
                    "historical": {
                        "grand_total": hist_data.grand_total,
                        "sources_summary": hist_data.sources_summary
                    }
                })
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/settings":
            cfg = config.get_runtime_config_dict()
            self.send_json(cfg)
            return

        if self.path == "/api/history":
            history = storage.get_report_history(limit=25)
            self.send_json(history)
            return

        if self.path == "/api/logs":
            log_lines = []
            if os.path.exists(config.LOG_PATH):
                try:
                    with open(config.LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        log_lines = lines[-100:]
                except Exception as e:
                    log_lines = [f"Error reading log: {e}"]
            log_text = "".join(log_lines)
            encoded = log_text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b""
        req_pin = self.headers.get("X-Admin-PIN", "").strip()

        # Validate Admin PIN
        expected_pin = config.ADMIN_PIN
        if req_pin and req_pin != expected_pin:
            self.send_json({"status": "error", "error": "Invalid Admin PIN"}, status=403)
            return

        if self.path == "/api/settings":
            try:
                new_settings = json.loads(post_body.decode("utf-8"))
                for k, v in new_settings.items():
                    storage.set_setting(k, v)
                config.apply_runtime_settings(new_settings)
                if SCHEDULER_INSTANCE and any(k in new_settings for k in ["DAILY_REPORT_TIME", "MONTHLY_REPORT_TIME", "MONTHLY_REPORT_DAY", "TIMEZONE"]):
                    SCHEDULER_INSTANCE.reschedule()
                self.send_json({"status": "ok", "message": "Settings saved successfully"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=400)
            return

        if self.path == "/api/actions/send-daily":
            if not BOT_INSTANCE:
                self.send_json({"status": "error", "error": "Bot instance not initialized yet"}, status=503)
                return
            try:
                chat_id = config.REPORT_CHAT_ID
                if not chat_id:
                    self.send_json({"status": "error", "error": "REPORT_CHAT_ID is not set in Settings"}, status=400)
                    return

                target_date = "today"
                if post_body:
                    try:
                        req_data = json.loads(post_body.decode("utf-8"))
                        if req_data.get("date"):
                            target_date = req_data["date"].strip()
                    except Exception:
                        pass

                from src.parser import parse_date_report
                t_rows = sheets_client.get_today_sheet_rows()
                h_rows = sheets_client.get_historical_sheet_rows()
                reg_rows = sheets_client.get_registrations_sheet_rows()
                t_data = parse_date_report(h_rows, t_rows, target_date, reg_rows=reg_rows)
                msg_text = format_daily_report(t_data)

                async def _send():
                    msg = await BOT_INSTANCE.send_message(
                        chat_id=chat_id,
                        text=msg_text,
                        parse_mode="HTML"
                    )
                    storage.log_report_sent("MANUAL_DAILY", t_data.date_str, message_id=msg.message_id)
                    return msg.message_id

                future = run_async_coro(_send())
                msg_id = future.result(timeout=15)
                self.send_json({"status": "ok", "message": f"របាយការណ៍ប្រចាំថ្ងៃ ({t_data.date_str}) ត្រូវបានផ្ញើទៅ Telegram រួចរាល់! (Message ID: {msg_id})"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/send-monthly":
            if not BOT_INSTANCE:
                self.send_json({"status": "error", "error": "Bot instance not initialized yet"}, status=503)
                return
            try:
                chat_id = config.REPORT_CHAT_ID
                if not chat_id:
                    self.send_json({"status": "error", "error": "REPORT_CHAT_ID is not set"}, status=400)
                    return

                import time
                from src.pdf_generator import generate_monthly_report_pdf
                from src.report_builder import KHMER_MONTHS, to_khmer_num
                now = datetime.now(TIMEZONE)
                pdf_filename = f"Monthly_Report_{now.year}_{now.month:02d}.pdf"
                pdf_path = os.path.join(config.DATA_DIR, pdf_filename)

                if not (os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000 and (time.time() - os.path.getmtime(pdf_path) < 180)):
                    h_rows = sheets_client.get_historical_sheet_rows()
                    reg_rows = sheets_client.get_registrations_sheet_rows()
                    h_data = parse_historical_sheet(h_rows, reg_rows=reg_rows)
                    pdf_path = generate_monthly_report_pdf(h_data, force_refresh=False)
                    grand_total = h_data.grand_total
                    female_total = h_data.total_female
                    dropped_total = h_data.total_dropped
                    storage.set_setting("last_monthly_total", str(grand_total))
                    storage.set_setting("last_monthly_female", str(female_total))
                    storage.set_setting("last_monthly_dropped", str(dropped_total))
                else:
                    grand_total = storage.get_setting("last_monthly_total")
                    female_total = storage.get_setting("last_monthly_female")
                    dropped_total = storage.get_setting("last_monthly_dropped")
                    if not grand_total:
                        h_rows = sheets_client.get_historical_sheet_rows()
                        reg_rows = sheets_client.get_registrations_sheet_rows()
                        h_data = parse_historical_sheet(h_rows, reg_rows=reg_rows)
                        grand_total = h_data.grand_total
                        female_total = h_data.total_female
                        dropped_total = h_data.total_dropped

                extra_parts = []
                if dropped_total and str(dropped_total) != "0":
                    extra_parts.append(f"បោះបង់ <b>{dropped_total}</b> នាក់")
                if female_total and str(female_total) != "0":
                    extra_parts.append(f"ស្រី <b>{female_total}</b> នាក់")
                extra_str = f" ({' • '.join(extra_parts)})" if extra_parts else ""
                caption = (
                    f"📈 <b>របាយការណ៍ស្ថិតិប្រចាំខែ (Monthly Report PDF)</b>\n"
                    f"🗓 <b>ខែ{KHMER_MONTHS.get(now.month, 'កញ្ញា')} ឆ្នាំ {to_khmer_num(now.year)}</b>\n"
                    f"👥 និស្សិតដាក់ពាក្យសរុប៖ <b>{grand_total} នាក់</b>{extra_str}"
                )

                async def _send_m():
                    with open(pdf_path, "rb") as doc:
                        msg = await BOT_INSTANCE.send_document(
                            chat_id=chat_id,
                            document=doc,
                            filename=f"Monthly_Scholarship_Report_{now.year}_{now.month:02d}.pdf",
                            caption=caption,
                            parse_mode="HTML"
                        )
                    now_key = datetime.now(TIMEZONE).strftime("%Y-%m")
                    storage.log_report_sent("MANUAL_MONTHLY_PDF", now_key, message_id=msg.message_id)
                    return msg.message_id

                future = run_async_coro(_send_m())
                msg_id = future.result(timeout=30)
                self.send_json({"status": "ok", "message": f"Monthly PDF report sent successfully! (Message ID: {msg_id})"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/pause":
            try:
                storage.set_setting("bot_paused", "true")
                if WATCHER_INSTANCE:
                    WATCHER_INSTANCE.pause()
                self.send_json({"status": "ok", "is_paused": True, "message": "Bot alerts and schedules paused successfully!"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/resume":
            try:
                storage.set_setting("bot_paused", "false")
                if WATCHER_INSTANCE:
                    WATCHER_INSTANCE.resume()
                self.send_json({"status": "ok", "is_paused": False, "message": "Bot alerts and schedules resumed successfully!"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/force-sync":
            if not WATCHER_INSTANCE:
                self.send_json({"status": "error", "error": "Watcher not running"}, status=503)
                return
            try:
                async def _sync_all():
                    await WATCHER_INSTANCE.check_for_changes(is_manual=True)
                    await WATCHER_INSTANCE.check_for_new_registrations(is_manual=True)
                future = run_async_coro(_sync_all())
                future.result(timeout=25)
                self.send_json({"status": "ok", "message": "Sheet sync and registration push completed successfully!"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/test-message":
            if not BOT_INSTANCE:
                self.send_json({"status": "error", "error": "Bot instance not initialized"}, status=503)
                return
            try:
                chat_id = config.REPORT_CHAT_ID
                now_str = datetime.now(TIMEZONE).strftime("%I:%M:%S %p")
                test_text = (
                    "🔔 <b>សារសាកល្បងពី Web Management Portal!</b>\n"
                    f"⏱ វេលាម៉ោង៖ {now_str}\n"
                    "✅ ការតភ្ជាប់រវាង Web UI និង Telegram Bot ដំណើរការយ៉ាងល្អឥតខ្ចោះ។"
                )

                async def _send_test():
                    msg = await BOT_INSTANCE.send_message(
                        chat_id=chat_id,
                        text=test_text,
                        parse_mode="HTML"
                    )
                    return msg.message_id

                future = run_async_coro(_send_test())
                msg_id = future.result(timeout=15)
                self.send_json({"status": "ok", "message": f"Test alert sent successfully! (Message ID: {msg_id})"})
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        if self.path == "/api/actions/test-reg-alert":
            if not WATCHER_INSTANCE:
                self.send_json({"status": "error", "error": "Watcher not running"}, status=503)
                return
            try:
                future = run_async_coro(WATCHER_INSTANCE.send_test_registration_alert())
                ok = future.result(timeout=15)
                if ok:
                    self.send_json({"status": "ok", "message": "New registration test alert sent to Telegram successfully!"})
                else:
                    self.send_json({"status": "error", "error": "Failed to send test registration alert"}, status=500)
            except Exception as e:
                self.send_json({"status": "error", "error": str(e)}, status=500)
            return

        self.send_response(404)
        self.end_headers()

def run_web_server(port: int = None):
    if port is None:
        port = int(os.getenv("PORT", "8080"))

    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardRequestHandler)
    logger.info(f"Web Management Portal running on http://0.0.0.0:{port} (PORT={port})")
    server.serve_forever()

def start_web_server_background():
    thread = threading.Thread(target=run_web_server, daemon=True)
    thread.start()
    return thread
