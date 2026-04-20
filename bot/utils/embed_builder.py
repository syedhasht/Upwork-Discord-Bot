import discord

def create_job_embed(title: str, description: str, budget: str, link: str) -> discord.Embed:
    """
    Constructs a rich Discord Embed specifically designed for displaying job postings.
    """
    # Upwork green color: #14a800 -> 0x14a800
    embed = discord.Embed(
        title=title,
        url=link,
        description=description,
        color=0x14a800
    )
    
    embed.add_field(name="💰 Budget", value=budget, inline=False)
    embed.add_field(name="🔗 Link", value=link, inline=False)
    
    embed.set_footer(text="Upwork Job Scraper")
    return embed
