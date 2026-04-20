import discord
from discord.ext import commands, tasks
import config
import pipeline
from utils.filters import filter_jobs
from utils.dedupe import is_new_job
from utils.formatter import format_job
import datetime

# Setup Discord Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Send startup message
    if config.CHANNEL_ID:
        channel = bot.get_channel(config.CHANNEL_ID)
        if channel:
            await channel.send("Job bot online 🚀")
        else:
            print(f"Warning: Channel {config.CHANNEL_ID} not found.")
            
    # Start the background pipeline loop
    if not job_pipeline_loop.is_running():
        job_pipeline_loop.start()


@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.command()
async def status(ctx):
    await ctx.send(f"Status: Fully operational.\nPipeline Loop Running: {job_pipeline_loop.is_running()}")


@bot.command()
async def search(ctx, *, keyword: str):
    """
    Manually override and trigger a targeted job scrape!
    Usage: !search react frontend
    """
    await ctx.send(f"🔍 Spinning up scraper to search Upwork for: `{keyword}`...")
    
    try:
        # 1. Scrape 10 jobs natively
        raw_jobs = pipeline.get_jobs(keyword=keyword)
        
        # 2. Filter securely
        filtered_jobs = filter_jobs(raw_jobs, min_budget=0, keyword=keyword)
        
        posted_count = 0
        for job in filtered_jobs:
            if is_new_job(job['id']):
                embed = format_job(job)
                await ctx.send(embed=embed)
                posted_count += 1
                
        if posted_count == 0:
            await ctx.send(f"⚠️ Found jobs for `{keyword}`, but all were either duplicates or filtered out.")
        else:
            await ctx.send(f"✅ Successfully exported {posted_count} new jobs for `{keyword}`.")
            
    except Exception as e:
        await ctx.send(f"❌ Scraper pipeline crashed: {e}")
        print(f"[ERROR] search command failed: {e}")

@tasks.loop(minutes=5)
async def job_pipeline_loop():
    """
    The core automated pipeline loop tracking 'python' by default.
    """
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Triggering active pipeline loop...")
    
    if not config.CHANNEL_ID:
        return
        
    channel = bot.get_channel(config.CHANNEL_ID)
    if not channel:
        return

    try:
        raw_jobs = pipeline.get_jobs(keyword="python")
        filtered_jobs = filter_jobs(raw_jobs, min_budget=50, keyword="python")
        
        posted_count = 0
        for job in filtered_jobs:
            if is_new_job(job['id']):
                embed = format_job(job)
                await channel.send(embed=embed)
                posted_count += 1
                
        print(f"[OK] Pipeline hit complete. Posted {posted_count} new jobs.")
        
    except Exception as e:
        print(f"[ERROR] Pipeline experienced an unhandled exception: {e}")

if __name__ == "__main__":
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_discord_bot_token_here":
        print("Error: BOT_TOKEN missing!")
    else:
        print("Initializing bot...")
        bot.run(config.BOT_TOKEN)
