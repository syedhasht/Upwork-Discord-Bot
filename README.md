# 🤖 Upwork Job Hunt: Autonomous Discord Bot

A state-of-the-art, self-healing job scraping system that delivers real-time Upwork listings directly to your Discord. Built with a "Stealth-First" architecture to bypass Cloudflare and stay under the radar.

---

## 🌊 The "Self-Healing" Workflow

The bot operates on a dynamic, high-performance cycle designed to mimic human behavior while maintaining 24/7 uptime:

1.  **The Bypass (Heavy Lifter)**: If the session expires, the bot automatically triggers an invisible **SeleniumBase UC** browser to solve Cloudflare Turnstile and extract fresh tokens into `session.json`.
2.  **The Engine (Fast & Stealthy)**: Once tokens are ready, the bot switches to a lightweight **`curl_cffi`** client. This client impersonates a **Chrome 110 TLS fingerprint**, making it invisible to anti-bot systems while fetching jobs in <1 second.
3.  **The Intelligence (Sync & Prune)**:
    *   **Deduplication**: Every job is checked against an SQLite database.
    *   **Smart Swap**: If a job is deleted and reposted (common on Upwork), the bot detects the matching description, updates the link, and notifies you of the "Fresh" version.
    *   **Auto-Cleanup**: A background task prunes jobs older than **50 hours** to keep the database lightweight.

---

## 🛠️ Key Technical Features

*   **🕵️ TLS Impersonation**: Uses `curl_cffi` to mimic real browser handshakes, bypassing low-level bot detection.
*   **🧩 Mutex Locking**: Thread-safe architecture ensures that if multiple scans need a token refresh, only one browser opens, preventing resource spikes.
*   **🔄 Intelligent Repost Detection**: Implements a "Swap Rule" that tracks job content rather than just IDs, ensuring you never miss a job that was "restarted" by a client.
*   **⏳ Human-Mode Jitter**: Random delays (45-90s) and search offsets prevent patterns that triggers rate limits.
*   **🧹 Zero-Maintenance**: Automatically handles database pruning and token rotation without human intervention.

---

## 📂 Project Structure

### 🤖 Discord Layer (`/discord`)
*   **`bot.py`**: The "Brain." Manages commands and the human-like polling loop.
*   **`database.py`**: The "Memory." Manages SQLite storage for jobs and tracking history.
*   **`helpers/dedupe.py`**: The "Filter." Handles the Smart Swap and Duplicate logic.
*   **`helpers/formatter.py`**: The "Designer." Creates premium, color-coded Discord Embeds.

### 🕷️ Scraper Layer (`/scraper`)
*   **`runner.py`**: The "Strategist." Prepares search payloads for the API.
*   **`core/client.py`**: The "Agent." Handles the actual HTTP communication and error recovery.
*   **`core/parser.py`**: The "Translator." Converts messy Upwork JSON into clean, usable data.
*   **`core/session.json`**: The "Vault." Centralized storage for active auth tokens and cookies.

### 🛡️ Cloudflare Layer (`/cloudflare`)
*   **`bypass/solver.py`**: The "Locksmith." An automated browser script that generates fresh entry keys when needed.

---

## 🎮 Discord Commands

| Command | Usage | Description |
| :--- | :--- | :--- |
| `!track` | `!track [keyword]` | Creates a new channel and starts scanning for that keyword. |
| `!untrack` | `!untrack [keyword]` | Stops scanning and deletes the dedicated channel. |
| `!status` | `!status` | Shows all active trackers and the current bot health. |
| `!search` | `!search [keyword]` | Performs a one-time instant search without adding a tracker. |
| `!tracking`| `!tracking` | Lists all keywords currently being monitored. |
| `!ping`   | `!ping` | Simple health check to see if the bot is responsive. |

---

## 🚀 Setup & Execution

### 1. Requirements
*   Python 3.9+
*   Google Chrome (installed on the host machine)

### 2. Installation
```bash
# Install dependencies
pip install -r discord/requirements.txt
```

### 3. Configuration
Create a `.env` file inside the `discord/` folder:
```env
BOT_TOKEN=your_discord_bot_token_here
```

### 4. Run
```bash
cd discord
python main.py
```

*Logs are stored in `logs/bot.log`. Check here to see real-time "Under the Hood" activity!*
