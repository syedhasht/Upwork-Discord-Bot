# 🤖 Upwork Job Hunt Discord Bot

A fully automated, self-healing Upwork job scraper that delivers real-time job alerts directly into your Discord server — organized by keyword, filtered for quality, and deduplicated forever.

---

## ✨ Features

- **Live Upwork Job Feed** — Scrapes real jobs sorted by newest first
- **Dynamic Channel Tracking** — `!track python` creates a dedicated `#python-jobs` channel that auto-updates every minute
- **Multi-Keyword Support** — Track Python, React, Java, or any keyword simultaneously in separate channels
- **Self-Healing Auth** — When Cloudflare blocks the scraper, a headless browser automatically harvests fresh tokens and resumes — no human needed
- **Duplicate Prevention** — SQLite database permanently records every posted job ID so nothing is ever posted twice, even after restarts
- **Cloudflare Bypass** — Uses `curl_cffi` to impersonate Chrome at the TLS fingerprint level
- **Clean Embeds** — Upwork-branded green embed cards with clickable job titles, budget, and skills

---

## 📂 Project Structure

```
Discord Bot/
│
├── bot/                         # Discord bot application
│   ├── bot.py                   # Main bot: commands, polling loop, startup
│   ├── config.py                # Settings: token, channel ID, refresh interval
│   ├── database.py              # SQLite helpers: jobs + keyword trackers
│   ├── pipeline.py              # Bridge: connects bot to Phase 1 scraper
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Secret keys (never commit this)
│   │
│   └── utils/
│       ├── filters.py           # Keyword & budget filtering logic
│       ├── dedupe.py            # Duplicate detection via DB lookup
│       └── formatter.py         # Discord embed builder
│
├── phase1/                      # Upwork scraping engine
│   ├── main.py                  # GraphQL payload + run_scraper() entry point
│   │
│   └── scraper/
│       ├── client.py            # curl_cffi HTTP client + 401/403 auto-heal trigger
│       ├── parser.py            # Extracts title, budget, skills, ciphertext URL
│       └── config.py            # Live Upwork cookies + auth token (auto-overwritten)
│
├── phase2/                      # Cloudflare bypass engine
│   └── auth/
│       └── bootstrap.py         # Playwright headless browser: solves Cloudflare, harvests fresh tokens
│
├── Database/
│   └── jobs.db                  # SQLite database (posted_jobs + tracked_keywords tables)
│
└── README.md
```

---

## ⚙️ Setup

### 1. Install Dependencies
```bash
cd bot
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment
Create `bot/.env`:
```env
BOT_TOKEN=your_discord_bot_token_here
CHANNEL_ID=your_default_channel_id_here
```

### 3. Enable Discord Bot Intents
In the [Discord Developer Portal](https://discord.com/developers/applications/):
- Go to your app → **Bot** → Enable **Message Content Intent**

### 4. Run the Bot
```bash
cd bot
python bot.py
```

---

## 🎮 Commands

| Command | Description |
|---|---|
| `!track <keyword>` | Creates a dedicated channel and starts auto-fetching jobs every 1 minute |
| `!untrack <keyword>` | Stops tracking a keyword and deletes its channel |
| `!tracking` | Lists all active keyword trackers and their channels |
| `!search <keyword>` | One-off search posted directly to the current channel |
| `!status` | Shows bot health, loop status, and active trackers |
| `!ping` | Basic alive check |

---

## 🔄 How It Works

### Normal Flow
```
!track python
      ↓
Creates #python-jobs channel
      ↓
Every 1 minute:
  Scrape Upwork (visitorJobSearch GraphQL API, sorted by recency)
      ↓
  Strip Upwork highlight markers (H^word^H)
      ↓
  Filter by keyword + budget
      ↓
  Check SQLite for duplicate job IDs
      ↓
  Format as Discord embed with clickable Upwork link
      ↓
  Post to #python-jobs
      ↓
  Save job ID to database permanently
```

### Token Expiry & Auto-Heal
When Upwork returns `401` or `403`:
1. `client.py` intercepts the error
2. Spawns `phase2/auth/bootstrap.py` automatically
3. Headless Chrome opens Upwork, solves Cloudflare puzzles
4. Fresh `cf_clearance` cookie + `Authorization` token are extracted
5. `phase1/scraper/config.py` is overwritten with new credentials
6. Original request is retried once — jobs flow normally

### Bot Restart Recovery
All tracked keywords and channel IDs are stored in SQLite. On restart, the bot reads the `tracked_keywords` table and **resumes all polling loops automatically** without any commands needed.

---

## 🛠️ Configuration

| File | Setting | Default |
|---|---|---|
| `bot/config.py` | `REFRESH_INTERVAL` | `1` (minute) |
| `phase1/main.py` | `"sort"` | `"recency"` (newest first) |
| `phase1/main.py` | `count` | `10` jobs per fetch |

---

## 🗄️ Database

Located at `Database/jobs.db`. Two tables:

**`posted_jobs`** — Every job ever sent to Discord
| Column | Description |
|---|---|
| `job_id` | Upwork's internal job ID (primary key) |
| `title` | Job title |
| `budget` | Formatted budget string |
| `link` | Full `https://www.upwork.com/jobs/~...` URL |
| `posted_at` | ISO timestamp when posted |

**`tracked_keywords`** — Active channel trackers
| Column | Description |
|---|---|
| `keyword` | The search keyword (e.g. `python`) |
| `channel_id` | Discord channel ID |
| `guild_id` | Discord server ID |
| `created_at` | When tracking started |

---

## 🔐 Security Notes

- **Never commit `bot/.env`** — your Discord bot token is in there
- `phase1/scraper/config.py` contains temporary Upwork session cookies — it is auto-regenerated and also should not be committed
- Both files are listed in `.gitignore`

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Discord Bot | `discord.py` with `discord.ext.tasks` |
| HTTP Client | `curl_cffi` (Chrome TLS impersonation) |
| Cloudflare Bypass | `Playwright` (headless Chromium) |
| API | Upwork internal `visitorJobSearch` GraphQL |
| Database | SQLite (built into Python — no server needed) |
| Config | `python-dotenv` |
