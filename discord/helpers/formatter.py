import discord

def format_job(job: dict) -> discord.Embed:
    """
    Converts a job dictionary into a strictly formatted Discord Embed.
    """
    title = job['title']  # Embed titles are bold by default in Discord

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
        color=0x14a800  # Upwork green
    )

    embed.add_field(name="💰 Budget", value=f"`{budget}`", inline=True)
    embed.add_field(name="🕐 Posted", value=posted_on, inline=True)
    embed.add_field(name="🛠 Skills", value=skills_text, inline=False)
    embed.set_footer(text="Upwork Job Feed • Job Hunt Bot")
    return embed
