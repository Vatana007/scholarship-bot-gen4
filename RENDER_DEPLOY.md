# 🌐 ការបើកមើលលើ Web និងការដាក់ឱ្យដំណើរការលើ Render ដោយឥតគិតថ្លៃ (Free Tier)

ឯកសារនេះណែនាំលម្អិតអំពី៖
1. **របៀបបើកមើល Bot និង Dashboard លើ Web Browser**
2. **របៀប Host Bot លើ Render.com ដោយឥតគិតថ្លៃ (100% Free Tier)**

---

## 1. របៀបបើកមើលលើ Web (How to open it on Web)

Bot នេះត្រូវបានបំពាក់ដោយ **Web Server & Live Dashboard** ភ្ជាប់ស្រាប់ ដែលអនុញ្ញាតឱ្យលោកអ្នកបើកមើលស្ថិតិតាម Browser បានយ៉ាងងាយស្រួល៖

### ជម្រើសទី ១៖ បើកមើល Live Web Dashboard
នៅពេល Bot កំពុងដំណើរការ (ទាំងនៅលើកុំព្យូទ័ររបស់អ្នក ឬលើ Render)៖
- **លើកុំព្យូទ័រផ្ទាល់ (Localhost)**៖ បើក Browser ហើយចូលទៅកាន់៖
  👉 `http://localhost:8080`
- **នៅលើ Render (បន្ទាប់ពី Deploy រួច)**៖
  👉 `https://your-bot-name.onrender.com`

**មុខងារលើ Web Dashboard៖**
- 🟢 បង្ហាញស្ថានភាព Bot (Online/Offline)
- 📊 បង្ហាញចំនួននិស្សិតចុះឈ្មោះសរុប និងបែងចែកតាមប្រភព (Sources)
- 📚 បង្ហាញតារាងស្ថិតិតាមមុខជំនាញទាំងអស់
- 🔄 ធ្វើបច្ចុប្បន្នភាពទិន្នន័យស្វ័យប្រវត្តិរៀងរាល់ ៣០ វិនាទី
- 🚀 មានប៊ូតុងចុចដើម្បីចូលទៅកាន់ Telegram ផ្ទាល់

### ជម្រើសទី ២៖ បើកប្រើ Bot លើ Telegram Web
លោកអ្នកអាចជជែក និងបញ្ជា Bot លើ Web Browser តាម Telegram Web បានគ្រប់ពេលវេលា៖
1. ចូលទៅកាន់៖ [https://web.telegram.org/](https://web.telegram.org/)
2. ស្វែងរកឈ្មោះ Bot របស់អ្នក (Username)
3. វាយពាក្យ `/start`, `/today`, ឬ `/monthly`

---

## 2. របៀប Host លើ Render ដោយឥតគិតថ្លៃ (Render Free Hosting Guide)

Render ផ្ដល់សេវាកម្ម **Web Service** ដោយឥតគិតថ្លៃ (Free Tier) ដែលអាចរត់ Bot របស់យើងបានយ៉ាងរលូន ២៤ ម៉ោង។

### ជំហានទី ១៖ Push Code របស់អ្នកទៅកាន់ GitHub
1. បង្កើត Repository ថ្មីមួយនៅលើ [GitHub](https://github.com/new) (ដាក់ជា Private ឬ Public)
2. បើក Terminal ក្នុងថត `New Bot_UI` រួចវាយ៖
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Scholarship Telegram Bot"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

### ជំហានទី ២៖ បង្កើតគណនី និង Web Service លើ Render
1. ចូលទៅកាន់គេហទំព័រ [Render.com](https://render.com/) ហើយចុះឈ្មោះ (Sign Up with GitHub)
2. នៅ Dashboard ចុចប៊ូតុង **New +** ➔ ជ្រើសរើស **Web Service**
3. ជ្រើសរើស Repository GitHub របស់ Bot ដែលទើប Push អម្បាញ់មិញ រួចចុច **Connect**

### ជំហានទី ៣៖ កំណត់ការ Settings លើ Render (ណែនាំជ្រើសរើស Docker)
> [!IMPORTANT]
> ដោយសារតែ Bot របស់យើងមានមុខងារបង្កើត **ឯកសារ PDF ប្រចាំខែ (Monthly Report PDF)** ជាមួយនឹងពុម្ពអក្សរខ្មែរស្អាតឥតខ្ចោះ យើងត្រូវជ្រើសរើស **Docker** (Render គាំទ្រ Docker ដោយឥតគិតថ្លៃ 100% Free) ដើម្បីឱ្យ Render ដំឡើង Chromium និង Khmer Fonts ដោយស្វ័យប្រវត្តិ។

បំពេញព័ត៌មានដូចខាងក្រោម៖
- **Name**: ដាក់ឈ្មោះ Bot (ឧ. `scholarship-bot`)
- **Region**: ជ្រើសរើស `Singapore` (ជិតប្រទេសកម្ពុជាបំផុត)
- **Language / Runtime**: ជ្រើសរើស **`Docker`** *(Render នឹងចាប់យក Dockerfile ក្នុងគម្រោងដោយស្វ័យប្រវត្តិ)*
- **Branch**: `main`
- *(ចំណាំ៖ នៅពេលជ្រើស Docker មិនបាច់កំណត់ Build Command ឬ Start Command ឡើយ ព្រោះ Dockerfile បានរៀបចំស្រេច)*
- **Instance Type**: ជ្រើសរើស **Free** ($0/month)

> [!TIP]
> **សម្រាប់សេវាដែលបានបង្កើតរួចហើយ (Changing existing Web Service to Docker)៖**
> ប្រសិនបើលោកអ្នកធ្លាប់បានបង្កើត Web Service ជា `Python 3` រួចហើយ ហើយជួបបញ្ហា *No Chrome/Edge browser found*:
> 1. ចូលទៅកាន់ Render Dashboard ➔ ចុចលើ Service របស់អ្នក
> 2. ចុចចូលផ្ទាំង **Settings**
> 3. ត្រង់កន្លែង **Runtime** ឬ **Environment** ➔ ប្តូរពី `Python 3` ទៅជា **`Docker`**
> 4. ចុច **Save Changes** ➔ Render នឹងធ្វើការ Re-deploy ជាមួយ Chromium និងពុម្ពអក្សរខ្មែរភ្លាមៗ!


### ជំហានទី ៤៖ បញ្ចូល Environment Variables (Secrets)
នៅផ្នែកខាងក្រោម ចុចលើ **Advanced** ➔ **Add Environment Variable** ហើយចម្លងតម្លៃពី `.env` មកដាក់៖

| Key | Value |
|---|---|
| `BOT_TOKEN` | *Token របស់ Bot អ្នក* (ឧ. `8771472898:AAG...`) |
| `ALLOWED_CHAT_IDS` | `-1005564248093` |
| `REPORT_CHAT_ID` | `-1005564248093` |
| `SPREADSHEET_ID` | `14XY1kCjb8znDeKWLqYrPJJhH2P7BQwo9ciqeRlh8qC8` |
| `TODAY_SHEET_GID` | `330658001` |
| `HISTORICAL_SHEET_GID` | `360162816` |
| `TIMEZONE` | `Asia/Phnom_Penh` |
| `DAILY_REPORT_TIME` | `17:00` |
| `MONTHLY_REPORT_DAY` | `1` |
| `MONTHLY_REPORT_TIME` | `08:00` |
| `POLLING_INTERVAL_SECONDS` | `60` |

*(ចំណាំ៖ Render នឹងផ្ដល់ `PORT` ដោយស្វ័យប្រវត្តិ ដែល Web Server របស់យើងបានរៀបចំស្គាល់ស្រាប់)*

រួចចុចប៊ូតុង **Create Web Service**! Render នឹងចាប់ផ្តើម Build និង Deploy ភ្លាមៗ។

---

## 3. គន្លឹះសំខាន់៖ របៀបកុំឱ្យ Render Free Tier ដេកលក់ (Keep-Alive 24/7)

> [!NOTE]
> Render Free Tier នឹងចូលទៅកាន់ Sleep Mode (Spin Down) បើសិនជាគ្មានអ្នកបើកមើល Web រយៈពេល ១៥ នាទី។

ដើម្បីកុំឱ្យវាដេកលក់ និងធានាថា Bot ផ្ញើរបាយការណ៍ និង Watch Google Sheet បាន ២៤ ម៉ោង៖
1. ចម្លងយក URL របស់ Render (ឧ. `https://scholarship-bot.onrender.com`)
2. ចូលទៅកាន់គេហទំព័រឥតគិតថ្លៃ [UptimeRobot.com](https://uptimerobot.com/) ឬ [cron-job.org](https://cron-job.org/)
3. ចុះឈ្មោះ Free Account រួចចុច **Add New Monitor**
4. ជ្រើសរើស Monitor Type: **HTTP(s)**
5. ដាក់ URL របស់ Render ចូល (ឧ. `https://scholarship-bot.onrender.com/health`)
6. កំណត់ Monitoring Interval: **Every 10 minutes**
7. ចុច **Create Monitor**

👉 រាល់ ១០ នាទី UptimeRobot នឹងហៅទៅកាន់ Web Server របស់ Bot ម្តង ធ្វើឱ្យ Render គិតថាមានអ្នកប្រើប្រាស់ជានិច្ច ដូច្នេះ Bot នឹង**រត់ ២៤/៧ ដោយមិនដេកលក់ និងមិនអស់លុយឡើយ (100% Free)**!
