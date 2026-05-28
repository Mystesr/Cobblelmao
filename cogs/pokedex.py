import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

# Type color mapping for embeds
TYPE_COLORS = {
    "fire": 0xFF4500, "water": 0x1E90FF, "grass": 0x228B22,
    "electric": 0xFFD700, "psychic": 0xFF69B4, "ice": 0xADD8E6,
    "dragon": 0x8B008B, "dark": 0x2F2F2F, "fairy": 0xFFB6C1,
    "normal": 0xA8A878, "fighting": 0xC03028, "flying": 0xA890F0,
    "poison": 0xA040A0, "ground": 0xE0C068, "rock": 0xB8A038,
    "bug": 0xA8B820, "ghost": 0x705898, "steel": 0xB8B8D0,
}

TYPE_WEAKNESSES = {
    "fire":     {"weak": ["water","rock","ground"], "strong": ["grass","ice","bug","steel","fairy"]},
    "water":    {"weak": ["electric","grass"], "strong": ["fire","rock","ground"]},
    "grass":    {"weak": ["fire","ice","poison","flying","bug"], "strong": ["water","rock","ground"]},
    "electric": {"weak": ["ground"], "strong": ["water","flying"]},
    "psychic":  {"weak": ["bug","ghost","dark"], "strong": ["fighting","poison"]},
    "ice":      {"weak": ["fire","fighting","rock","steel"], "strong": ["grass","ground","flying","dragon"]},
    "dragon":   {"weak": ["ice","dragon","fairy"], "strong": ["fire","water","grass","electric"]},
    "dark":     {"weak": ["fighting","bug","fairy"], "strong": ["ghost","psychic"]},
    "fairy":    {"weak": ["poison","steel"], "strong": ["fighting","dragon","dark"]},
    "normal":   {"weak": ["fighting"], "strong": []},
    "fighting": {"weak": ["flying","psychic","fairy"], "strong": ["normal","rock","steel","ice","dark"]},
    "flying":   {"weak": ["electric","ice","rock"], "strong": ["grass","fighting","bug"]},
    "poison":   {"weak": ["ground","psychic"], "strong": ["grass","fairy"]},
    "ground":   {"weak": ["water","grass","ice"], "strong": ["fire","electric","poison","rock","steel"]},
    "rock":     {"weak": ["water","grass","fighting","ground","steel"], "strong": ["fire","ice","flying","bug"]},
    "bug":      {"weak": ["fire","flying","rock"], "strong": ["grass","psychic","dark"]},
    "ghost":    {"weak": ["ghost","dark"], "strong": ["normal","fighting"]},
    "steel":    {"weak": ["fire","fighting","ground"], "strong": ["ice","rock","fairy"]},
}

class Pokedex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_pokemon(self, name: str):
        """Fetch data from PokeAPI (base stats/types, works for Cobblemon too)."""
        async with aiohttp.ClientSession() as session:
            url = f"https://pokeapi.co/api/v2/pokemon/{name.lower()}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()

    @app_commands.command(name="dex", description="Look up a Cobblemon Pokémon's info")
    @app_commands.describe(pokemon="Name of the Pokémon (e.g. charmander)")
    async def dex(self, interaction: discord.Interaction, pokemon: str):
        await interaction.response.defer()
        data = await self.fetch_pokemon(pokemon)
        if not data:
            await interaction.followup.send(f"❌ Couldn't find **{pokemon}**. Check the spelling and try again!")
            return

        types = [t["type"]["name"].capitalize() for t in data["types"]]
        stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
        sprite = data["sprites"]["front_default"]
        color = TYPE_COLORS.get(types[0].lower(), 0x7289DA)

        embed = discord.Embed(
            title=f"#{data['id']} — {data['name'].capitalize()}",
            color=color
        )
        embed.set_thumbnail(url=sprite)
        embed.add_field(name="🏷️ Type", value=" / ".join(types), inline=True)
        embed.add_field(name="⚖️ Weight", value=f"{data['weight'] / 10}kg", inline=True)
        embed.add_field(name="📏 Height", value=f"{data['height'] / 10}m", inline=True)
        embed.add_field(
            name="📊 Base Stats",
            value=(
                f"HP: **{stats.get('hp', '?')}** | ATK: **{stats.get('attack', '?')}** | DEF: **{stats.get('defense', '?')}**\n"
                f"SP.ATK: **{stats.get('special-attack', '?')}** | SP.DEF: **{stats.get('special-defense', '?')}** | SPD: **{stats.get('speed', '?')}**"
            ),
            inline=False
        )
        moves = [m["move"]["name"].replace("-", " ").title() for m in data["moves"][:10]]
        embed.add_field(name="⚔️ Sample Moves", value=", ".join(moves), inline=False)
        embed.set_footer(text="PokéNode • Data via PokéAPI")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="weakness", description="Check a type's weaknesses and strengths")
    @app_commands.describe(type_name="The Pokémon type (e.g. fire, water, dragon)")
    async def weakness(self, interaction: discord.Interaction, type_name: str):
        t = type_name.lower()
        if t not in TYPE_WEAKNESSES:
            await interaction.response.send_message(f"❌ Unknown type **{type_name}**. Try: fire, water, grass, electric, etc.")
            return
        info = TYPE_WEAKNESSES[t]
        embed = discord.Embed(title=f"🔬 Type Chart — {type_name.capitalize()}", color=TYPE_COLORS.get(t, 0x7289DA))
        embed.add_field(
            name="⚠️ Weak to",
            value=", ".join(info["weak"]).capitalize() if info["weak"] else "Nothing!",
            inline=False
        )
        embed.add_field(
            name="💪 Strong against",
            value=", ".join(info["strong"]).capitalize() if info["strong"] else "Nothing notable",
            inline=False
        )
        embed.set_footer(text="PokéNode Type Chart")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="compare", description="Compare two Pokémon side by side")
    @app_commands.describe(pokemon1="First Pokémon", pokemon2="Second Pokémon")
    async def compare(self, interaction: discord.Interaction, pokemon1: str, pokemon2: str):
        await interaction.response.defer()
        d1 = await self.fetch_pokemon(pokemon1)
        d2 = await self.fetch_pokemon(pokemon2)
        if not d1 or not d2:
            await interaction.followup.send("❌ Couldn't find one or both Pokémon. Check names and try again.")
            return

        def get_stats(d):
            return {s["stat"]["name"]: s["base_stat"] for s in d["stats"]}

        s1, s2 = get_stats(d1), get_stats(d2)
        stat_keys = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]

        lines = []
        for key in stat_keys:
            v1, v2 = s1.get(key, 0), s2.get(key, 0)
            winner = "◀" if v1 > v2 else ("▶" if v2 > v1 else "=")
            lines.append(f"`{key.upper():<15}` {v1:>4} {winner} {v2:<4}")

        embed = discord.Embed(
            title=f"⚔️ {d1['name'].capitalize()} vs {d2['name'].capitalize()}",
            description="\n".join(lines),
            color=0x7289DA
        )
        embed.set_footer(text="◀ = left wins  ▶ = right wins  = = tie")
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Pokedex(bot))