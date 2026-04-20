import discord

def format_job(job: dict) -> discord.Embed:
    """
    Converts a job dictionary into a strictly formatted Discord Embed.
    """
    title = f"**{job['title']}**"
    
    # Truncate description strictly to 300 chars
    desc = job['description']
    if len(desc) > 300:
        desc = desc[:297] + "..."
        
    budget = f"`{job.get('budget', 'N/A')}`"
    link = job.get('link', 'https://www.upwork.com')
    
    embed = discord.Embed(
        title=title,
        url=link,
        description=desc,
        color=0x14a800
    )
    
    embed.add_field(name="💰 Budget", value=budget, inline=False)
    
    embed.set_footer(text="Upwork Phase 4 Pipeline")
    return embed
