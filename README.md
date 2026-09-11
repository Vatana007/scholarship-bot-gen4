# 🤖 Telegram Bot សម្រាប់របាយការណ៍ស្ថិតិអាហារូបករណ៍ (Student Registration Statistics Bot)

ប្រព័ន្ធ Telegram Bot ស្វ័យប្រវត្តិ សម្រាប់ទាញយក និងរៀបចំរបាយការណ៍ស្ថិតិនានាពី **Google Sheet** (ស្ថិតិថ្ងៃនឹង និង ស្ថិតិប្រចាំថ្ងៃ) បំលែងទៅជាសាររាយការណ៍ដ៏ស្រស់ស្អាតជាភាសាខ្មែរ (Telegram HTML Mode) ដោយស្វ័យប្រវត្តិតាមកាលវិភាគ ព្រមទាំងរុញដំណឹង (Real-time Push Alerts) ភ្លាមៗនៅពេលមានការកែប្រែទិន្នន័យក្នុង Sheet។

---

## 🌟 លក្ខណៈពិសេសសំខាន់ៗ (Features)

1. **របាយការណ៍ប្រចាំថ្ងៃស្វ័យប្រវត្តិ (Daily Scheduled Report)**:
   - ផ្ញើរៀងរាល់ម៉ោង 17:00 (ម៉ោង ៥:០០ ល្ងាច ភ្នំពេញ) ទៅកាន់ Telegram Group/Channel។
   - បង្ហាញចំនួនតាមប្រភព (`E-School`, `ក្រសួងអប់រំ`, `បងប្អូន`, `DUC`) និងតាមមុខជំនាញទាំង ២២។
   - បង្ហាញតែជំនាញដែលមានការចុះឈ្មោះ (> 0) ដើម្បីសន្សំសំចៃទំហំសារ និងមានប៊ូតុង `[📂 មើលគ្រប់ជំនាញ]` សម្រាប់មើលទាំងអស់។
2. **របាយការណ៍ប្រចាំខែស្វ័យប្រវត្តិ (Monthly Scheduled Rollup)**:
   - ផ្ញើរៀងរាល់ថ្ងៃទី ១ នៃខែថ្មីវេលាម៉ោង 08:00 ព្រឹក។
   - បង្ហាញចំណាត់ថ្នាក់មុខជំនាញដែលមានសិស្សដាក់ពាក្យច្រើនជាងគេ (🥇, 🥈, 🥉) និងសរុបរួម។
3. **ការរុញដំណឹងភ្លាមៗ (Real-time Change Watcher)**:
   - ត្រួតពិនិត្យ Sheet រៀងរាល់ ៦០ វិនាទី (Hash Diffing)។
   - នៅពេលមានការប្រែប្រួលទិន្នន័យ វានឹងផ្ញើសារ `🔔 បច្ចុប្បន្នភាពថ្មី` ដោយបង្ហាញតែជំនាញណាដែលបានកែប្រែ (`ចាស់ ➔ ថ្មី (+N)`)។
4. **បញ្ជាតាមតម្រូវការ (On-Demand Commands)**:
   - `/start` - បង្ហាញផ្ទាំងស្វាគមន៍ និង Menu ប៊ូតុងចុច
   - `/today` - មើលស្ថិតិថ្ងៃនេះភ្លាមៗ
   - `/report` ឬ `/daily` - មើលរបាយការណ៍ប្រចាំថ្ងៃ
   - `/monthly` - មើលរបាយការណ៍សរុបប្រចាំខែ
   - `/categories` - មើលបញ្ជីមុខជំនាញទាំងអស់តាមទំព័រ (Pagination: Prev/Next)
   - `/help` - ការណែនាំរបៀបប្រើប្រាស់
5. **សុវត្ថិភាព និងភាពធន់ (Security & Reliability)**:
   - គាំទ្រ **Allowed Chat IDs**: មានតែ Group ឬ Admin ដែលត្រូវបានអនុញ្ញាតទើបអាចបញ្ជា Bot បាន។
   - មាន **Retry / Exponential Backoff**: ការពារកុំឱ្យ Bot គាំងពេលជួបបញ្ហា Network ឬ API Rate Limit។
   - គាំទ្រទាំង **Google Service Account (gspread)** និង **Public CSV Fallback** (ដំណើរការបានភ្លាមៗ ទោះមិនទាន់ដាក់ file credential ក៏ដោយ)។
   - រក្សាទុក State និង Log ក្នុង **SQLite Database** (`data/state.db`) ការពារការផ្ញើសារស្ទួន (Duplicate) ពេល Restart Bot។

---

## 📁 រចនាសម្ព័ន្ធ Project (Project Structure)

```
New Bot_UI/
├── .env                      # ការកំណត់សម្ងាត់ (Token, Chat ID, Sheet ID, etc.)
├── .env.example              # គំរូការកំណត់
├── .gitignore                # មិនបញ្ចូល file សម្ងាត់ទៅ GitHub
├── requirements.txt          # បណ្ណាល័យពាក់ព័ន្ធ
├── README.md                 # ឯកសារណែនាំ
├── credentials/
│   └── service_account.json  # File សោរ Google Service Account (បើមាន)
├── data/
│   └── state.db              # SQLite Database សម្រាប់កត់ត្រា Hash និងរបាយការណ៍
├── logs/
│   └── bot.log               # Log កត់ត្រាសកម្មភាព និងបញ្ហានានា (Rotating Log)
└── src/
    ├── __init__.py
    ├── config.py             # គ្រប់គ្រង Config និង Logging
    ├── storage.py            # គ្រប់គ្រង SQLite Database
    ├── sheets_client.py      # ការទាញយកទិន្នន័យពី Google Sheet
    ├── parser.py             # បំលែងទិន្នន័យ Sheet ទៅជា Python Objects
    ├── report_builder.py     # រៀបចំទម្រង់សារ Telegram HTML Format
    ├── change_watcher.py     # Background Loop សម្រាប់ Real-time Push
    ├── scheduler.py          # APScheduler សម្រាប់ម៉ោងកំណត់
    └── main.py               # Entry Point ដំណើរការ Bot ទាំងមូល
```

---

## 🚀 របៀបតម្លើង និងដំណើរការ (Setup & Installation)

### ១. បង្កើត Telegram Bot និងយក Bot Token
1. បើក Telegram ហើយស្វែងរក `@BotFather`
2. វាយ `/newbot` ហើយធ្វើតាមការណែនាំ (ដាក់ឈ្មោះ និង username របស់ bot)
3. ចម្លងយក **HTTP API Token** (ឧទាហរណ៍ `8771472898:AAG...`)

### ២. ស្វែងរក Telegram Chat ID
1. បញ្ចូល Bot ទៅក្នុង Group ឬ Channel ដែលចង់ឱ្យទទួលរបាយការណ៍
2. ផ្ញើសារ ១ ចូលទៅក្នុង Group
3. បើក Browser ចូលតំណភ្ជាប់៖ `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. ស្វែងរក `"chat":{"id": -100xxxxxxxxxx}` (នោះជា Chat ID របស់ Group)

### ៣. រៀបចំ Google Service Account (ជាជម្រើស / Optional)
*ប្រសិនបើ Google Sheet របស់អ្នកបានបើកសិទ្ធិ Public (Anyone with link can view) នោះអ្នកមិនចាំបាច់មាន Service Account ក៏ Bot អាចទាញទិន្នន័យបាន 100% ដែរ។*

ប្រសិនបើជា Private Sheet៖
1. ចូលទៅកាន់ [Google Cloud Console](https://console.cloud.google.com/)
2. បង្កើត Project ថ្មី និង Enable **Google Sheets API** និង **Google Drive API**
3. ចូលទៅកាន់ **Credentials** ➔ **Create Credentials** ➔ **Service Account**
4. បង្កើត Key ជាប្រភេទ **JSON** ហើយទាញយក file នោះមកដាក់ក្នុង Folder `credentials/service_account.json`
5. Share Google Sheet របស់អ្នកទៅកាន់ email របស់ Service Account នោះ (Viewer)

### ៤. កំណត់ `.env`
ចម្លង `.env.example` ទៅជា `.env`៖
```env
BOT_TOKEN=8771472898:AAG7ql3YKoJrm8Z6TIPemFb03_bKbwLp9OY
ALLOWED_CHAT_IDS=-1005564248093
REPORT_CHAT_ID=-1005564248093

SPREADSHEET_ID=14XY1kCjb8znDeKWLqYrPJJhH2P7BQwo9ciqeRlh8qC8
TODAY_SHEET_NAME=ស្ថិតិថ្ងៃនឹង
TODAY_SHEET_GID=330658001
HISTORICAL_SHEET_NAME=ស្ថិតិប្រចាំថ្ងៃ
HISTORICAL_SHEET_GID=360162816
SERVICE_ACCOUNT_PATH=credentials/service_account.json

TIMEZONE=Asia/Phnom_Penh
DAILY_REPORT_TIME=17:00
MONTHLY_REPORT_DAY=1
MONTHLY_REPORT_TIME=08:00
POLLING_INTERVAL_SECONDS=60
```

### ៥. ដំឡើង Dependencies និងដំណើរការ Bot

បើក Terminal / Command Prompt នៅក្នុង Folder គម្រោង៖
```bash
# បង្កើត និងបើក Virtual Environment (បើចង់)
python -m venv .venv
.venv\Scripts\activate  # សម្រាប់ Windows
# source .venv/bin/activate  # សម្រាប់ Linux/Mac

# ដំឡើងបណ្ណាល័យ
pip install -r requirements.txt

# ដំណើរការ Bot
python -m src.main
```

---

## 🌐 ការបើកមើលលើ Web និងការដាក់លើ Render ដោយឥតគិតថ្លៃ (Free Tier)

Bot នេះមានភ្ជាប់ **Web Dashboard** និង **Health Server** ស្រាប់ ដូច្នេះលោកអ្នកអាច៖
1. **បើកមើលលើ Web Browser ផ្ទាល់**៖ ចូលទៅ `http://localhost:8080` (ឬ URL របស់ Render) ដើម្បីមើល Live Registration Dashboard
2. **Host លើ Render Free Tier**៖ អានការណែនាំលម្អិតមួយជំហានម្តងៗក្នុងឯកសារ 👉 [RENDER_DEPLOY.md](RENDER_DEPLOY.md)

---

## 🌐 ជម្រើស Hosting ផ្សេងៗទៀតសម្រាប់ដំណើរការ ២៤/៧ (Production Hosting)

ដោយសារ Bot នេះមានមុខងារ Real-time Polling និង Scheduler ដូច្នេះវាត្រូវការកុំព្យូទ័រ ឬ Server ដែលបើកដំណើរការជាប្រចាំ (Always-on process)៖
1. **Render.com (Free Tier)**:
   - ប្រើ Web Service ដោយឥតគិតថ្លៃ (មើលការណែនាំលម្អិតក្នុង [RENDER_DEPLOY.md](RENDER_DEPLOY.md))។
2. **Cloud VPS (DigitalOcean, Hetzner, Linode)**:
   - តម្លៃប្រហែល $4 - $5/ខែ ប្រើ `systemd` ឬ `pm2` / `docker`។
3. **Raspberry Pi ឬ Mini PC ក្នុងការិយាល័យ**:
   - អាចដាក់ឱ្យរត់ក្នុងកុំព្យូទ័រតូចមួយដែលបើក ២៤ ម៉ោង មិនអស់ថ្លៃសេវា Server ប្រចាំខែឡើយ។
