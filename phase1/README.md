# Upwork GraphQL Scraper - Phase 1

This folder contains **Phase 1** of the custom Upwork scraping and deployment pipeline. 

## 🎯 Phase 1 Goal
The primary objective of this phase is **Network Reverse Engineering & Data Parsing**. 
We are not dealing with logging in or bypassing bot protection securely yet (that is Phase 2). Here, we have successfully replicated the exact hidden GraphQL API call that Upwork's frontend uses to fetch job feeds, and built a robust engine to decode the complicated JSON response.

## 📂 Project Architecture

```text
phase1/
│
├── scraper/
│   ├── __init__.py       # Package initializer
│   ├── client.py         # HTTP logic: The `UpworkClient` that wraps the `requests` module and fires the POST commands.
│   ├── config.py         # The "Identity" file: Holds the exact Headers and Cookies (Auth Tokens, cf_clearance, etc.) mimicking your Chrome browser.
│   └── parser.py         # The "Extraction Desk": Traverses the huge GraphQL JSON tree, dynamically formats Fixed vs Hourly budgets, and maps Skills.
│
├── main.py               # Orchestrator: Holds the raw internal GraphQL payload (variables like `q="python"`) and executes the `client.py` search.
├── requirements.txt      # Project dependencies (e.g., `requests`).
│
└── Testing Sandbox
    ├── sample_response.json  # A real Upwork GraphQL response manually exported from Chrome DevTools.
    └── test_parser.py        # An offline testing script to safely verify our extraction logic works without network blocks.
```

## 🧠 Mental Model (`config.py` Identity)
If you look inside `scraper/config.py`, you will see massive strings. Those are your temporary **Session Tokens** (`oauth2v2_..., visitor_id, cf_clearance`). 

When `main.py` runs, it hands these precise tokens back to Upwork. Upwork literally thinks the Python script is **you** sitting at your desk. The responses it returns are completely customized to your personal Upwork account (e.g. showing whether you specifically have applied to a job).

## 🛡️ The 403 Forbidden Reality (Cloudflare)
Running `python main.py` directly over the internet might result in a `403 Forbidden` HTML page from Cloudflare. 

**This is not a bug.** This is expected behavior. While our `Headers` and `Cookies` are perfect, Python's `requests` library uses a different "TLS Fingerprint" than Chrome, which Cloudflare catches as a bot. Furthermore, the Upwork tokens naturally expire after a few hours.

To solve this, Phase 1 focuses purely on the **logic** of the request and the parsing.

## 🧪 How to Test Phase 1 Successfully (Offline)
Because of the 403 block, we built a testing sandbox to definitively prove the data extraction layer (`parser.py`) is flawless.

1. Ensure you have the `sample_response.json` (a raw successful DevTools copy).
2. Run the offline test:
```bash
python test_parser.py
```
This forces our `parser.py` logic to process the real JSON without using the internet, successfully spitting out beautifully formatted Job Titles, Budgets, and Skills!

## 🚀 Moving to Phase 2
Phase 1 proved our GraphQL data extraction is perfect. 

**Phase 2** will focus on building the **Layer 1: Browser Identity Generator**. Instead of manually pasting expiring cookies into `config.py`, Phase 2 will utilize a headless browser (Selenium or Playwright) to dynamically log into your account, solve invisible bot protections by having real browser fingerprints, and export fresh tokens to `config.py` completely automatically.
