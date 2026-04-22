# 🤖 Upwork Job Hunt Discord Bot

An autonomous, self-healing Discord bot that scrapes Upwork in real-time and delivers fresh job listings directly into dedicated Discord channels — organized by keyword, filtered, and deduplicated permanently.

---

## ✨ Features

- **Keyword-Based Channel Tracking** — `!track python` creates a `#python-jobs` channel that auto-updates every minute
- **Multi-Keyword Support** — Track unlimited keywords simultaneously, each in its own isolated channel
- **Newest Jobs First** — Sorted by `recency` so you always see the latest listings
- **Self-Healing Auth** — When Cloudflare blocks the scraper, a headless browser auto-harvests fresh tokens and resumes with zero human input
- **Permanent Deduplication** — SQLite tracks every posted job ID forever, so nothing gets posted twice even after restarts
- **Cloudflare Bypass** — `curl_cffi` impersonates Chrome 110 at the TLS fingerprint level to avoid bot detection
- **Posted Time** — Every job card shows how long ago it was posted (e.g. "3h ago")
- **Restart Recovery** — All tracked keywords and channel bindings survive bot restarts via SQLite

---

## 📂 Project Structure

```
Discord Bot/
│
├── discord/                         # Discord bot application
│   ├── main.py                      # Entry point: commands, polling loop, startup logic
│   ├── bridge.py                    # Connector between bot and scraper
│   ├── database.py                  # SQLite helpers: jobs + tracked keywords
│   ├── config.py                    # Loads BOT_TOKEN, CHANNEL_ID, REFRESH_INTERVAL
│   ├── .env                         # Secret keys (never commit this)
│   ├── requirements.txt             # Python dependencies
│   │
│   └── helpers/
│       ├── filters.py               # Secondary keyword & budget filter
│       ├── dedupe.py                # Duplicate detection via database lookup
│       └── formatter.py            # Builds Discord embed cards from job data
│
├── scraper/                         # Upwork scraping engine
│   ├── runner.py                    # GraphQL payload + run_scraper() entry point
│   │
│   └── core/
│       ├── client.py                # curl_cffi HTTP client + 401/403 auto-heal trigger
│       ├── parser.py                # Extracts title, budget, skills, posted time, URL
│       └── config.py               # Live Upwork cookies + auth token (auto-overwritten)
│
├── cloudflare/                      # Cloudflare bypass engine
│   └── bypass/
│       └── solver.py               # Playwright headless browser: solves CF, harvests tokens
│
├── Database/
│   └── jobs.db                      # SQLite database (posted_jobs + tracked_keywords)
│
└── README.md
```

---

## ⚙️ Setup

### 1. Install Python Dependencies
```bash
pip install -r discord/requirements.txt
```

### 2. Install Playwright Browser
```bash
playwright install chromium
```

### 3. Configure Environment
Create `discord/.env`:
```env
BOT_TOKEN=your_discord_bot_token_here
CHANNEL_ID=your_default_channel_id_here
```

### 4. Enable Discord Bot Permissions
In the [Discord Developer Portal](https://discord.com/developers/applications/):
- Go to your app → **Bot** → Enable **Message Content Intent**
- Go to **OAuth2** → **Bot** → Enable **Manage Channels** permission

### 5. Run the Bot
```bash
cd discord
python main.py
```

---

## 🎮 Commands

| Command | Description |
|---|---|
| `!track <keyword>` | Creates a `#keyword-jobs` channel and begins auto-fetching every minute |
| `!untrack <keyword>` | Stops tracking and deletes the keyword's channel |
| `!tracking` | Lists all active keyword trackers and their bound channels |
| `!search <keyword>` | One-off search posted directly to the current channel |
| `!status` | Shows loop status, poll interval, and all active trackers |
| `!ping` | Basic alive check |

---

## 🔄 Full Workflow

### Normal Polling (Every 1 Minute)
```
Loop wakes up
    ↓
Read tracked_keywords from SQLite
    ↓
For each keyword (e.g. python, django):
    ↓
    bridge.py calls scraper/runner.py
    ↓
    runner.py reloads scraper/core/config.py fresh (picks up latest tokens)
    ↓
    runner.py injects keyword into GraphQL query
    ↓
    client.py fires POST to Upwork's visitorJobSearch GraphQL API
    ↓
    Upwork returns up to 10 newest matching jobs as JSON
    ↓
    parser.py extracts: title, budget, skills, posted_on, ciphertext URL
    ↓
    helpers/filters.py drops jobs missing the keyword
    ↓
    helpers/dedupe.py drops jobs already in posted_jobs table
    ↓
    helpers/formatter.py builds Discord embed card
    ↓
    Bot posts embed to #keyword-jobs channel
    ↓
    Job ID saved permanently to SQLite
```

### Token Expiry & Auto-Heal
```
client.py fires request
    ↓
Upwork returns 401 or 403
    ↓
client.py spawns cloudflare/bypass/solver.py as subprocess
    ↓
Playwright opens real Chromium, loads Upwork
    ↓
Cloudflare JavaScript challenges run against real browser fingerprint
    ↓
solver.py captures fresh cf_clearance cookie + Authorization token
    ↓
scraper/core/config.py is overwritten with new credentials
    ↓
Original request is retried once with fresh tokens → succeeds
```

### Bot Restart Recovery
On startup, `database.get_all_trackers()` reads the `tracked_keywords` table and the polling loop immediately resumes all keywords. No `!track` commands need to be re-run.

---

## 🗄️ Database

Located at `Database/jobs.db`. Two tables:

**`posted_jobs`** — Every job ever sent to Discord

| Column | Description |
|---|---|
| `job_id` | Upwork job ID (primary key, used for deduplication) |
| `title` | Job title |
| `budget` | Formatted budget string |
| `link` | Full `https://www.upwork.com/jobs/~...` URL |
| `posted_at` | ISO timestamp of when the bot posted it |

**`tracked_keywords`** — Active channel trackers

| Column | Description |
|---|---|
| `keyword` | Search keyword (e.g. `python`) |
| `channel_id` | Discord channel ID |
| `guild_id` | Discord server ID |
| `created_at` | When tracking started |

---

## ⚙️ Configuration

| File | Setting | Default | Description |
|---|---|---|---|
| `discord/config.py` | `REFRESH_INTERVAL` | `1` | Poll frequency in minutes |
| `discord/bridge.py` | `count` | `10` | Jobs fetched per keyword per cycle |
| `scraper/runner.py` | `"sort"` | `"recency"` | Job sort order (newest first) |

---

## 📦 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Discord Bot | `discord.py` + `discord.ext.tasks` | Commands, embeds, background loop |
| HTTP Client | `curl_cffi` | Chrome TLS impersonation to bypass Cloudflare |
| Browser Automation | `Playwright` (Chromium) | Harvests fresh tokens when blocked |
| API | Upwork `visitorJobSearch` GraphQL | Internal job search endpoint |
| Database | `SQLite3` (built into Python) | Permanent deduplication + tracker storage |
| Config | `python-dotenv` | Loads secrets from `.env` |

---

## 🔐 Security Notes

- **Never commit `discord/.env`** — contains your live Discord bot token
- **Never commit `scraper/core/config.py`** — contains live Upwork session cookies
- Both are listed in `.gitignore`
- `cloudflare/bypass/cookies.json` is created automatically after the first token refresh — it is a backup log and is also gitignored
