import discord
from discord.ext import commands
from discord import app_commands
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_conn
from cogs.economy import add_coins, add_xp

TRIVIA_QUESTIONS = [
    {"q": "What type is Charmander?", "a": "fire"},
    {"q": "What type is Squirtle?", "a": "water"},
    {"q": "What type is Bulbasaur?", "a": "grass"},
    {"q": "What type is Pikachu?", "a": "electric"},
    {"q": "What type is Gengar?", "a": "ghost"},
    {"q": "What type is Machamp?", "a": "fighting"},
    {"q": "What type is Lapras?", "a": "water"},
    {"q": "What type is Eevee?", "a": "normal"},
    {"q": "What type is Mewtwo?", "a": "psychic"},
    {"q": "What evolves from Magikarp?", "a": "gyarados"},
    {"q": "What is the final evolution of Charmander?", "a": "charizard"},
    {"q": "What type is Geodude?", "a": "rock"},
    {"q": "What type is Gastly?", "a": "ghost"},
    {"q": "What type is Onix?", "a": "rock"},
    {"q": "What does Pikachu evolve into?", "a": "raichu"},
    {"q": "What type is Snorlax?", "a": "normal"},
    {"q": "What is Bulbasaur's final evolution?", "a": "venusaur"},
    {"q": "What type is Jigglypuff?", "a": "normal"},
    {"q": "What evolves from Slowpoke?", "a": "slowbro"},
    {"q": "What type is Haunter?", "a": "ghost"},
]

STARTERS = [
    "bulbasaur", "charmander", "squirtle", "chikorita", "cyndaquil", "totodile",
    "treecko", "torchic", "mudkip", "turtwig", "chimchar", "piplup",
    "snivy", "tepig", "oshawott", "chespin", "fennekin", "froakie",
    "rowlet", "litten", "popplio", "grookey", "scorbunny", "sobble",
    "sprigatito", "fuecoco", "quaxly"
]

WILD_POKEMON = [
    "Pidgey", "Rattata", "Caterpie", "Weedle", "Geodude", "Zubat",
    "Magikarp", "Tentacool", "Gastly", "Abra", "Machop", "Slowpoke",
    "Krabby", "Horsea", "Goldeen", "Staryu", "Eevee", "Porygon",
    "Larvitar", "Ralts", "Bagon", "Beldum", "Gible", "Riolu"
]

active_trivia = {}  # guild_id: {question, answer, reward}

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trivia", description="Answer a Cobblemon trivia question for PokéCoins!")
    async def trivia(self, interaction: discord.Interaction):
        gid = interaction.guild_id
        if gid in active_trivia:
            q = active_trivia[gid]["question"]
            await interaction.response.send_message(
                f"❓ There's already an active trivia question!\n**{q}**\nType your answer in chat!"
            )
            return
        picked = random.choice(TRIVIA_QUESTIONS)
        reward = random.randint(50, 150)
        active_trivia[gid] = {"question": picked["q"], "answer": picked["a"], "reward": reward}
        embed = discord.Embed(title="🧠 Cobblemon Trivia!", color=0x1E90FF)
        embed.add_field(name="Question", value=picked["q"], inline=False)
        embed.add_field(name="Reward", value=f"**{reward} PokéCoins** for the first correct answer!", inline=False)
        embed.set_footer(text="Type your answer in this channel!")
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        gid = message.guild.id
        if gid not in active_trivia:
            return
        trivia = active_trivia[gid]
        if message.content.strip().lower() == trivia["answer"]:
            uid = str(message.author.id)
            add_coins(uid, trivia["reward"])
            leveled_up, level = add_xp(uid, 30)
            del active_trivia[gid]
            msg = f"🎉 **{message.author.display_name}** got it right! The answer was **{trivia['answer'].capitalize()}**.\n+**{trivia['reward']} PokéCoins**!"
            if leveled_up:
                msg += f"\n⭐ Level up! Now **Trainer Lv. {level}**!"
            await message.channel.send(msg)

    @app_commands.command(name="roll", description="Encounter a random wild Pokémon (just for fun!)")
    async def roll(self, interaction: discord.Interaction):
        pokemon = random.choice(WILD_POKEMON)
        flavor = random.choice([
            "jumped out of the tall grass!",
            "appeared from the shadows!",
            "landed from the sky!",
            "emerged from the water!",
            "was sleeping nearby and woke up!",
        ])
        embed = discord.Embed(
            title=f"⚡ A wild **{pokemon}** appeared!",
            description=f"{pokemon} {flavor}",
            color=0x228B22
        )
        embed.set_footer(text="(This is just for fun — catch it in-game!)")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="starter", description="Choose your Cobblemon starter (shown on your profile)")
    @app_commands.describe(pokemon="Your starter Pokémon name")
    async def starter(self, interaction: discord.Interaction, pokemon: str):
        if pokemon.lower() not in STARTERS:
            await interaction.response.send_message(
                f"❌ **{pokemon}** isn't a valid starter. Try one of the main series starters!", ephemeral=True
            )
            return
        uid = str(interaction.user.id)
        conn = get_conn()
        conn.execute("UPDATE users SET starter = ? WHERE user_id = ?", (pokemon.capitalize(), uid))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"🌱 You chose **{pokemon.capitalize()}** as your starter! It'll show on your `/profile`."
        )

    @app_commands.command(name="teamshow", description="Show off your Cobblemon team!")
    @app_commands.describe(
        p1="Slot 1", p2="Slot 2", p3="Slot 3",
        p4="Slot 4", p5="Slot 5", p6="Slot 6"
    )
    async def teamshow(
        self, interaction: discord.Interaction,
        p1: str, p2: str, p3: str,
        p4: str = None, p5: str = None, p6: str = None
    ):
        team = [p for p in [p1, p2, p3, p4, p5, p6] if p]
        embed = discord.Embed(
            title=f"🎮 {interaction.user.display_name}'s Cobblemon Team",
            description=" | ".join([f"**{p.capitalize()}**" for p in team]),
            color=0xFF4500
        )
        embed.set_footer(text="PokéNode • Show off your team!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="online", description="Check who's on the Minecraft server (via DiscordSRV)")
    async def online(self, interaction: discord.Interaction):
        channel = discord.utils.get(interaction.guild.text_channels, name="mc-chat")
        if channel:
            await interaction.response.send_message(
                f"🟢 Check {channel.mention} to see who's online — DiscordSRV posts join/leave messages there!\n"
                f"*(Deep player tracking requires a server plugin beyond DiscordSRV.)*"
            )
        else:
            await interaction.response.send_message(
                "⚠️ No `#mc-chat` channel found. Ask your admin to set up DiscordSRV and link it to a channel named `mc-chat`."
            )

    @app_commands.command(name="help", description="See all PokéNode commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📖 PokéNode Commands", color=0x7289DA)
        embed.add_field(name="📚 Pokédex", value="`/dex` `/weakness` `/compare`", inline=False)
        embed.add_field(name="💰 Economy", value="`/balance` `/checkin` `/give` `/shop` `/buy` `/trade` `/profile`", inline=False)
        embed.add_field(name="🏆 Events", value="`/event_create` `/event_join` `/event_info` `/event_end` `/shiny_claim` `/shinydex`", inline=False)
        embed.add_field(name="🎉 Fun", value="`/trivia` `/roll` `/starter` `/teamshow` `/online`", inline=False)
        embed.set_footer(text="PokéNode • Your Cobblemon Discord companion!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Fun(bot))