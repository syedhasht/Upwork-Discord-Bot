import discord

def format_job(job: dict, is_update: bool = False) -> discord.Embed:
    """
    Converts a job dictionary into a strictly formatted Discord Embed.
    """
    title = job['title']
    if is_update:
        title = f"🔄 UPDATED: {title}"

    # Truncate description strictly to 300 chars
    desc = job['description']
    if len(desc) > 300:
        desc = desc[:297] + "..."

    budget = job.get('budget', 'N/A')
    link = job.get('link', 'https://www.upwork.com')
    skills = job.get('skills', [])
    skills_text = ", ".join([s for s in skills if s][:6]) or "N/A"
    posted_on = job.get('posted_on', 'Unknown')

    embed = discord.Embed(
        title=title,
        url=link,
        description=desc,
        color=0xF1C40F if is_update else 0x14a800  # Gold for updates, Green for new
    )

    embed.add_field(name="💰 Budget", value=f"`{budget}`", inline=True)
    embed.add_field(name="🕐 Posted", value=posted_on, inline=True)
    embed.add_field(name="🛠 Skills", value=skills_text, inline=False)
    embed.set_footer(text="Upwork Job Feed • Job Hunt Bot")
    return embed
