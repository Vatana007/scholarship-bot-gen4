import sys
import os
import time
import json
import urllib.request
import threading

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"d:\DUC-Work\Coding\Project DUC\Bot\Bot-Scholarship\New Bot_UI"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.web_server import run_web_server
import src.config as config
from src.storage import Storage

# Start web server on test port 8899
TEST_PORT = 8899
server_thread = threading.Thread(target=run_web_server, args=(TEST_PORT,), daemon=True)
server_thread.start()
time.sleep(1.5)

base_url = f"http://127.0.0.1:{TEST_PORT}"

def get_url(path):
    req = urllib.request.Request(f"{base_url}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")

def post_json(path, data, pin="123456"):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Admin-PIN": pin
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

print("=" * 60)
print("RUNNING WEB MANAGEMENT PORTAL API TESTS")
print("=" * 60)

# 1. Test Dashboard HTML
status, html = get_url("/")
assert status == 200
assert "Bot ស្ថិតិអាហារូបករណ៍" in html
assert "tab-dashboard" in html
assert "tab-actions" in html
assert "tab-settings" in html
assert "tab-history" in html
print("PASS: 1. Dashboard HTML rendered successfully with all tabs!")

# 2. Test /api/stats
status, body = get_url("/api/stats")
stats_data = json.loads(body)
assert status == 200
assert stats_data["status"] == "ok"
assert "today" in stats_data
assert "historical" in stats_data
assert stats_data["today"]["grand_total"] >= 0
print(f"PASS: 2. /api/stats returned: Today {stats_data['today']['grand_total']} students, Historical {stats_data['historical']['grand_total']} students!")

# 3. Test /api/settings GET
status, body = get_url("/api/settings")
cfg = json.loads(body)
assert status == 200
assert "REPORT_CHAT_ID" in cfg
assert "DAILY_REPORT_TIME" in cfg
print(f"PASS: 3. /api/settings returned runtime config: Daily at {cfg['DAILY_REPORT_TIME']}, Interval {cfg['POLLING_INTERVAL_SECONDS']}s")

# 4. Test /api/settings POST
new_settings = {
    "DAILY_REPORT_TIME": "17:45",
    "POLLING_INTERVAL_SECONDS": "90"
}
status, res = post_json("/api/settings", new_settings)
assert status == 200
assert res["status"] == "ok"

# Verify update took effect in runtime config
status, body = get_url("/api/settings")
updated_cfg = json.loads(body)
assert updated_cfg["DAILY_REPORT_TIME"] == "17:45"
assert updated_cfg["POLLING_INTERVAL_SECONDS"] == "90"
print("PASS: 4. /api/settings updated runtime configuration successfully!")

# Reset back
post_json("/api/settings", {"DAILY_REPORT_TIME": "18:00", "POLLING_INTERVAL_SECONDS": "60"})

# 5. Test /api/history
status, body = get_url("/api/history")
history_data = json.loads(body)
assert status == 200
assert isinstance(history_data, list)
print(f"PASS: 5. /api/history returned {len(history_data)} logged reports!")

# 6. Test /api/logs
status, logs_text = get_url("/api/logs")
assert status == 200
assert len(logs_text) > 0
print(f"PASS: 6. /api/logs returned {len(logs_text.splitlines())} lines of logs!")

# 7. Test /api/summary-preview
status, sum_body = get_url("/api/summary-preview?date=all")
assert status == 200
sum_data = json.loads(sum_body)
assert sum_data["status"] == "ok"
assert sum_data["is_overall"] is True
assert sum_data["total_applied"] == 45
assert sum_data["female_applied"] == 21
assert sum_data["total_arrived"] == 18
assert sum_data["female_arrived"] == 6
assert sum_data["total_returned"] == 26
assert sum_data["female_returned"] == 15
assert sum_data["total_dropped"] == 1
assert sum_data["female_dropped"] == 0
assert "ដាក់ពាក្យសរុប" in sum_data["text"]
assert "ស្រី" in sum_data["text"]
assert "មកដល់" in sum_data["text"]
assert "ទៅផ្ទះវិញ" in sum_data["text"]
assert "បោះបង់" in sum_data["text"]
print("PASS: 7. /api/summary-preview (all-time) returned correct metrics and formatted text!")

# 8. Test /api/summary-preview with specific date
status, sum_date_body = get_url("/api/summary-preview?date=10/Sep/2026")
assert status == 200
sum_date_data = json.loads(sum_date_body)
assert sum_date_data["status"] == "ok"
assert sum_date_data["total_applied"] == 19
assert sum_date_data["female_applied"] == 5
assert sum_date_data["total_arrived"] == 8
assert sum_date_data["female_arrived"] == 1
assert sum_date_data["total_returned"] == 10
assert sum_date_data["female_returned"] == 4
assert sum_date_data["total_dropped"] == 1
assert sum_date_data["female_dropped"] == 0
print("PASS: 8. /api/summary-preview (10/Sep/2026) returned accurate date-filtered metrics!")

# 9. Test /api/actions/send-summary endpoint structure
try:
    post_json("/api/actions/send-summary", {"date": "all"})
except urllib.error.HTTPError as he:
    # 503 is expected because Bot instance is not initialized in standalone test
    assert he.code in [503, 400]
print("PASS: 9. /api/actions/send-summary routed correctly!")

print("\nALL WEB MANAGEMENT TESTS PASSED 100%!")
