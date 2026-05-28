from keep_alive import keep_alive
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = ["cogs.pokedex", "cogs.economy", "cogs.events", "cogs.fun"]

@bot.event
async def on_ready():
    print(f"✅ PokéNode is online as {bot.user}")
    await bot.tree.sync()
    await bot.change_presence(
        activity=discord.Game(name="Cobblemon | /dex /help")
    )

@bot.event
async def on_member_join(member):
    """Give joining members a welcome coin bonus via DiscordSRV bridge."""
    channel = discord.utils.get(member.guild.text_channels, name="welcome")
    if channel:
        await channel.send(
            f"👋 Welcome to the server, **{member.display_name}**! "
            f"You've been given 100 PokéCoins to start your journey. Use `/balance` to check!"
        )
    # Give starter coins
    from cogs.economy import add_coins
    add_coins(str(member.id), 100)

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"  ✔ Loaded {cog}")
            except Exception as e:
                print(f"  ✘ Failed to load {cog}: {e}")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    import asyncio
    keep_alive()
    asyncio.run(main())