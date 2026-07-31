import discord
from discord.ext import commands, tasks
import config
import database
import bridge
from helpers.filters import filter_jobs
from helpers.dedupe import is_new_job
from helpers.formatter import format_job
import datetime
import logging
import asyncio
import random
import importlib

logger = logging.getLogger("jobhunt")

# Setup Discord Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Startup Event ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    logger.info(f"Bot is online! Logged in as {bot.user} (ID: {bot.user.id})")

    # Startup check: If session is missing or empty, trigger solver immediately
    from core.client import load_session
    headers, _ = load_session()
    
    if not headers or not headers.get("authorization"):
        logger.warning("Startup check: session.json is empty or has no token. Triggering solver now...")
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, bridge.get_jobs, "startup_check", 1)

    # Announce in default channel if configured
    if config.CHANNEL_ID:
        channel = bot.get_channel(config.CHANNEL_ID)
        if channel:
            await channel.send("Job Hunt Bot is active 🚀")

    # Resume all trackers
    trackers = database.get_all_trackers()
    if trackers:
        logger.info(f"[BOT] Resuming {len(trackers)} tracked keyword(s) from database...")
        for t in trackers:
            logger.info(f"  -> #{t['keyword']}-jobs (channel: {t['channel_id']})")

    # Start background loops
    if not hasattr(bot, 'poll_task') or bot.poll_task.done():
        bot.poll_task = asyncio.create_task(job_poll_loop_manual())
    
    if not token_refresh_check.is_running():
        token_refresh_check.start()
    if not database_cleanup_loop.is_running():
        database_cleanup_loop.start()


# ── Background Tasks ──────────────────────────────────────────────────────────

async def job_poll_loop_manual():
    """Manual polling loop with human-like jitter."""
    await bot.wait_until_ready()
    logger.info("[BOT] Starting human-like job poll loop...")
    
    while not bot.is_closed():
        try:
            trackers = database.get_all_trackers()
            if trackers:
                logger.info(f"[POLL] Starting scan for {len(trackers)} keywords...")
                for tracker in trackers:
                    channel = bot.get_channel(tracker['channel_id'])
                    if channel:
                        await _fetch_and_post(tracker['keyword'], channel)
                    await asyncio.sleep(random.uniform(2, 5)) # Keyword jitter
                logger.info("[POLL] Scan complete.")
            
            sleep_time = random.uniform(30, 60) # Loop jitter
            logger.info(f"[POLL] Sleeping for {sleep_time:.1f}s...")
            await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.error(f"[POLL] Error in manual poll loop: {e}")
            await asyncio.sleep(60)

@tasks.loop(minutes=15)
async def token_refresh_check():
    """Proactively checks token age and refreshes if > 10h."""
    now = datetime.datetime.now().astimezone()
    last_refresh = database.get_latest_token_refresh()
    if not last_refresh:
        last_refresh = now
        database.add_token_refresh(now)

    age = now - last_refresh
    if age.total_seconds() > (10 * 3600):
        logger.info(f"Token is {age.total_seconds() / 3600:.1f}h old. Triggering proactive refresh...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, bridge.get_jobs, "proactive_refresh", 1, True)
        logger.info("Proactive token refresh complete.")

@tasks.loop(hours=2)
async def database_cleanup_loop():
    """Prunes jobs older than 50 hours."""
    try:
        count = database.prune_old_jobs(hours=50)
        if count > 0:
            logger.info(f"[CLEANUP] Pruned {count} old job(s) from database.")
    except Exception as e:
        logger.error(f"[CLEANUP] Error during database pruning: {e}")


# ── Internal Engine ───────────────────────────────────────────────────────────

async def _fetch_and_post(keyword: str, channel: discord.TextChannel):
    """Fetch jobs and post new ones to channel."""
    try:
        loop = asyncio.get_event_loop()
        raw_jobs = await loop.run_in_executor(None, bridge.get_jobs, keyword, 50)
        filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)
        filtered_jobs.sort(key=lambda x: x.get("created_at_raw") or "")
        
        # Check if this is the first scan (0 jobs in DB for this keyword)
        is_initial = database.count_jobs_by_keyword(keyword) == 0
        
        posted_new = 0
        posted_updated = 0

        if is_initial:
            logger.info(f"[{keyword}] Initial scan detected. Saving all {len(filtered_jobs)} matching jobs, but only posting the 5 newest to prevent spam.")
            # Save all jobs to DB so they are marked as seen, but only post the 5 newest
            for job in filtered_jobs:
                job["keyword"] = keyword
                is_new_job(job, keyword)
            
            # Post only the 5 newest
            to_post_initial = filtered_jobs[-5:]
            for job in to_post_initial:
                embed = format_job(job, is_update=False)
                await channel.send(embed=embed)
                posted_new += 1
        else:
            # Process all matching jobs and post everything that is new or updated
            for job in filtered_jobs:
                job["keyword"] = keyword
                status = is_new_job(job, keyword)
                if status:
                    embed = format_job(job, is_update=(status == "updated"))
                    await channel.send(embed=embed)
                    if status == "new":
                        posted_new += 1
                    else:
                        posted_updated += 1

        logger.info(f"[{keyword}] Posted {posted_new} new, {posted_updated} updated job(s).")
    except Exception as e:
        logger.error(f"[{keyword}] Polling error: {e}")



# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

@bot.command()
async def status(ctx):
    trackers = database.get_all_trackers()
    lines = "\n".join([f"• `{t['keyword']}` → <#{t['channel_id']}>" for t in trackers]) if trackers else "No trackers."
    embed = discord.Embed(title="📊 Job Hunt Bot Status", description=lines, color=0x14a800)
    embed.add_field(name="🔁 Interval", value="45-90s (Jitter)", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def track(ctx, *, keyword: str):
    keyword = keyword.lower().strip()
    if database.tracker_exists(keyword):
        await ctx.send(f"⚠️ Already tracking `{keyword}`.")
        return
    
    try:
        new_channel = await ctx.guild.create_text_channel(name=f"{keyword.replace(' ', '-')}-jobs")
        database.add_tracker(keyword, new_channel.id, ctx.guild.id)
        await ctx.send(f"✅ Now tracking `{keyword}` in {new_channel.mention}.")
        await _fetch_and_post(keyword, new_channel)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def untrack(ctx, *, keyword: str):
    keyword = keyword.lower().strip()
    trackers = database.get_all_trackers()
    existing = next((t for t in trackers if t['keyword'] == keyword), None)
    if not existing:
        await ctx.send(f"⚠️ `{keyword}` not tracked.")
        return
    
    channel = bot.get_channel(existing['channel_id'])
    if channel: await channel.delete()
    database.remove_tracker(keyword)
    await ctx.send(f"🗑️ Stopped tracking `{keyword}`.")

@bot.command()
async def tracking(ctx):
    trackers = database.get_all_trackers()
    if not trackers:
        await ctx.send("📭 No active trackers.")
        return
    embed = discord.Embed(title="📡 Active Job Trackers", color=0x14a800)
    for t in trackers:
        embed.add_field(name=f"`{t['keyword']}`", value=f"<#{t['channel_id']}>", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def search(ctx, *, keyword: str):
    await ctx.send(f"🔍 Searching Upwork for: `{keyword}`...")
    try:
        loop = asyncio.get_event_loop()
        raw_jobs = await loop.run_in_executor(None, bridge.get_jobs, keyword, 50)
        filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)
        filtered_jobs.sort(key=lambda x: x.get("created_at_raw") or "")
        
        # Display the 10 newest jobs directly without calling is_new_job.
        # This prevents filtering out already-scraped jobs or modifying DB.
        to_post = filtered_jobs[-10:]
        
        if not to_post:
            await ctx.send("No matching jobs found on Upwork.")
            return
            
        for job in to_post:
            await ctx.send(embed=format_job(job, is_update=False))
    except Exception as e:
        await ctx.send(f"❌ Search failed: {e}")

