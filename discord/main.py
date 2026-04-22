import discord
from discord.ext import commands, tasks
import config
import database
import bridge
from helpers.filters import filter_jobs
from helpers.dedupe import is_new_job
from helpers.formatter import format_job
import datetime

# Initialize SQLite database tables on startup
database.init_db()

# Setup Discord Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Startup ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user} (ID: {bot.user.id})")

    # Announce in default channel if configured
    if config.CHANNEL_ID:
        channel = bot.get_channel(config.CHANNEL_ID)
        if channel:
            await channel.send("Job Hunt Bot is active 🚀")

    # Resume all trackers that were active before restart
    trackers = database.get_all_trackers()
    if trackers:
        print(f"[BOT] Resuming {len(trackers)} tracked keyword(s) from database...")
        for t in trackers:
            print(f"  -> #{t['keyword']}-jobs (channel: {t['channel_id']})")

    # Start the unified background loop
    if not job_poll_loop.is_running():
        job_poll_loop.start()


# ── Utility Commands ──────────────────────────────────────────────────────────

@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")


@bot.command()
async def status(ctx):
    trackers = database.get_all_trackers()
    if trackers:
        lines = "\n".join([f"• `{t['keyword']}` → <#{t['channel_id']}>" for t in trackers])
    else:
        lines = "No keywords being tracked yet. Use `!track <keyword>` to start!"
    embed = discord.Embed(
        title="📊 Job Hunt Bot Status",
        description=lines,
        color=0x14a800
    )
    embed.add_field(name="🔁 Poll Interval", value=f"Every {config.REFRESH_INTERVAL} minute(s)", inline=True)
    embed.add_field(name="⚙️ Loop Running", value=str(job_poll_loop.is_running()), inline=True)
    await ctx.send(embed=embed)


# ── Tracker Commands ──────────────────────────────────────────────────────────

@bot.command()
async def track(ctx, *, keyword: str):
    """
    Create a dedicated channel for a keyword and begin auto-fetching Upwork jobs.
    Usage: !track python
    """
    keyword = keyword.lower().strip()

    # Check if already tracking
    if database.tracker_exists(keyword):
        trackers = database.get_all_trackers()
        existing = next((t for t in trackers if t['keyword'] == keyword), None)
        if existing:
            await ctx.send(f"⚠️ Already tracking `{keyword}` in <#{existing['channel_id']}>!")
            return

    # Sanitize the channel name (Discord rules: lowercase, hyphens, no spaces)
    channel_name = f"{keyword.replace(' ', '-')}-jobs"

    await ctx.send(f"⚙️ Setting up tracker for `{keyword}`...")

    try:
        # Create the channel in the same guild
        new_channel = await ctx.guild.create_text_channel(
            name=channel_name,
            topic=f"🤖 Auto-updated Upwork job feed for: {keyword}",
            reason=f"Job Hunt Bot tracker for keyword: {keyword}"
        )

        # Save to database so it survives bot restarts
        database.add_tracker(keyword, new_channel.id, ctx.guild.id)

        await ctx.send(
            f"✅ Now tracking `{keyword}`!\n"
            f"📢 Jobs will appear in {new_channel.mention} every {config.REFRESH_INTERVAL} minute(s).\n"
            f"Use `!untrack {keyword}` to stop."
        )

        # Post an initial batch immediately without waiting for the loop
        await _fetch_and_post(keyword, new_channel)

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create channels. Please grant me the `Manage Channels` permission.")
    except Exception as e:
        await ctx.send(f"❌ Failed to set up tracker: {e}")
        print(f"[ERROR] track command failed: {e}")


@bot.command()
async def untrack(ctx, *, keyword: str):
    """
    Stop tracking a keyword and delete its dedicated channel.
    Usage: !untrack python
    """
    keyword = keyword.lower().strip()

    trackers = database.get_all_trackers()
    existing = next((t for t in trackers if t['keyword'] == keyword), None)

    if not existing:
        await ctx.send(f"⚠️ `{keyword}` is not currently being tracked.")
        return

    # Delete the channel
    channel = bot.get_channel(existing['channel_id'])
    if channel:
        try:
            await channel.delete(reason=f"Job Hunt Bot: untracking {keyword}")
        except discord.Forbidden:
            await ctx.send("⚠️ Could not delete the channel (missing permissions), but removed from tracker list.")

    # Remove from database
    database.remove_tracker(keyword)
    await ctx.send(f"🗑️ Stopped tracking `{keyword}` and deleted its channel.")


@bot.command()
async def tracking(ctx):
    """List all actively tracked keywords."""
    trackers = database.get_all_trackers()
    if not trackers:
        await ctx.send("📭 No keywords are being tracked. Use `!track <keyword>` to start!")
        return

    embed = discord.Embed(
        title="📡 Active Job Trackers",
        color=0x14a800
    )
    for t in trackers:
        embed.add_field(
            name=f"`{t['keyword']}`",
            value=f"<#{t['channel_id']}>",
            inline=True
        )
    embed.set_footer(text=f"Polling every {config.REFRESH_INTERVAL} minute(s) • Use !untrack <keyword> to stop")
    await ctx.send(embed=embed)


@bot.command()
async def search(ctx, *, keyword: str):
    """
    One-off search that posts results directly to the current channel.
    Usage: !search machine learning
    """
    await ctx.send(f"🔍 Searching Upwork for: `{keyword}`...")
    try:
        raw_jobs = bridge.get_jobs(keyword=keyword)
        filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)

        posted_count = 0
        for job in filtered_jobs:
            if is_new_job(job):
                embed = format_job(job)
                await ctx.send(embed=embed)
                posted_count += 1

        if posted_count == 0:
            await ctx.send(f"⚠️ No new jobs found for `{keyword}` (all were duplicates or filtered out).")
        else:
            await ctx.send(f"✅ Found and posted {posted_count} new job(s) for `{keyword}`.")

    except Exception as e:
        await ctx.send(f"❌ Search failed: `{e}`")
        print(f"[ERROR] search command: {e}")


# ── Core Polling Engine ───────────────────────────────────────────────────────

async def _fetch_and_post(keyword: str, channel: discord.TextChannel):
    """
    Shared helper: fetch jobs for a keyword and post new ones to the given channel.
    """
    try:
        raw_jobs = bridge.get_jobs(keyword=keyword)
        filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)

        posted_count = 0
        for job in filtered_jobs:
            if is_new_job(job):
                embed = format_job(job)
                await channel.send(embed=embed)
                posted_count += 1

        if posted_count > 0:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [{keyword}] Posted {posted_count} new job(s).")
        else:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [{keyword}] No new jobs.")

    except Exception as e:
        print(f"[ERROR] Polling '{keyword}': {e}")


@tasks.loop(minutes=config.REFRESH_INTERVAL)
async def job_poll_loop():
    """
    Master background loop. Iterates every tracked keyword and posts new jobs
    to each keyword's dedicated channel.
    """
    trackers = database.get_all_trackers()
    if not trackers:
        return  # Nothing to do yet

    for tracker in trackers:
        channel = bot.get_channel(tracker['channel_id'])
        if not channel:
            print(f"[WARN] Channel {tracker['channel_id']} for '{tracker['keyword']}' not found, skipping.")
            continue
        await _fetch_and_post(tracker['keyword'], channel)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_discord_bot_token_here":
        print("Error: BOT_TOKEN missing in .env!")
    else:
        print("Initializing bot...")
        bot.run(config.BOT_TOKEN)
