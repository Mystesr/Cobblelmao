import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_conn
from cogs.economy import add_coins, add_xp

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="event_create", description="[Admin] Create a new event")
    @app_commands.describe(
        name="Event name",
        event_type="Type of event (catching/shiny/tournament/challenge)",
        description="What players need to do",
        hours="How many hours the event lasts"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def event_create(self, interaction: discord.Interaction, name: str, event_type: str, description: str, hours: int):
        now = datetime.utcnow()
        from datetime import timedelta
        ends_at = (now + timedelta(hours=hours)).isoformat()
        conn = get_conn()
        conn.execute(
            "INSERT INTO events (name, event_type, description, created_by, ends_at) VALUES (?,?,?,?,?)",
            (name, event_type, description, str(interaction.user.id), ends_at)
        )
        event_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        embed = discord.Embed(
            title=f"🎉 New Event: {name}",
            description=description,
            color=0xFF6347
        )
        embed.add_field(name="Type", value=event_type.capitalize(), inline=True)
        embed.add_field(name="Duration", value=f"{hours} hours", inline=True)
        embed.add_field(name="Event ID", value=f"#{event_id}", inline=True)
        embed.set_footer(text="Use /event_join to participate!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="event_join", description="Join the current active event")
    async def event_join(self, interaction: discord.Interaction):
        conn = get_conn()
        event = conn.execute(
            "SELECT * FROM events WHERE active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not event:
            conn.close()
            await interaction.response.send_message("❌ There's no active event right now. Stay tuned!", ephemeral=True)
            return
        event = dict(event)
        uid = str(interaction.user.id)
        existing = conn.execute(
            "SELECT * FROM event_participants WHERE event_id = ? AND user_id = ?",
            (event["id"], uid)
        ).fetchone()
        if existing:
            conn.close()
            await interaction.response.send_message(f"✅ You're already joined in **{event['name']}**!", ephemeral=True)
            return
        conn.execute(
            "INSERT INTO event_participants (event_id, user_id, username) VALUES (?,?,?)",
            (event["id"], uid, interaction.user.display_name)
        )
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"🎮 You've joined **{event['name']}**!\n📋 {event['description']}"
        )

    @app_commands.command(name="event_info", description="See the current active event")
    async def event_info(self, interaction: discord.Interaction):
        conn = get_conn()
        event = conn.execute(
            "SELECT * FROM events WHERE active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not event:
            conn.close()
            await interaction.response.send_message("📭 No active event right now. Check back later!")
            return
        event = dict(event)
        participants = conn.execute(
            "SELECT username FROM event_participants WHERE event_id = ?", (event["id"],)
        ).fetchall()
        conn.close()

        names = [p["username"] for p in participants] if participants else ["No one yet..."]
        embed = discord.Embed(title=f"🏆 {event['name']}", description=event["description"], color=0xFF6347)
        embed.add_field(name="Type", value=event["event_type"].capitalize(), inline=True)
        embed.add_field(name="Ends At", value=event["ends_at"][:16] + " UTC", inline=True)
        embed.add_field(name=f"👥 Participants ({len(participants)})", value=", ".join(names), inline=False)
        embed.set_footer(text="Use /event_join to participate!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="event_end", description="[Admin] End the current event and award a winner")
    @app_commands.describe(winner="The member who won the event", prize="Coin prize amount")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def event_end(self, interaction: discord.Interaction, winner: discord.Member, prize: int):
        conn = get_conn()
        conn.execute("UPDATE events SET active = 0 WHERE active = 1")
        conn.commit()
        conn.close()
        add_coins(str(winner.id), prize)
        add_xp(str(winner.id), 200)
        embed = discord.Embed(title="🏆 Event Over!", color=0xFFD700)
        embed.add_field(name="🥇 Winner", value=winner.mention, inline=True)
        embed.add_field(name="💰 Prize", value=f"{prize} PokéCoins", inline=True)
        embed.set_footer(text="Thanks everyone for participating!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shiny_claim", description="Claim a shiny Pokémon you found!")
    @app_commands.describe(pokemon="The Pokémon that was shiny")
    async def shiny_claim(self, interaction: discord.Interaction, pokemon: str):
        uid = str(interaction.user.id)
        now = datetime.utcnow().isoformat()
        conn = get_conn()
        conn.execute(
            "INSERT INTO shinies (user_id, username, pokemon, claimed_at) VALUES (?,?,?,?)",
            (uid, interaction.user.display_name, pokemon.capitalize(), now)
        )
        conn.execute(
            "UPDATE users SET shiny_count = shiny_count + 1 WHERE user_id = ?", (uid,)
        )
        conn.commit()
        conn.close()
        add_coins(uid, 150)
        embed = discord.Embed(
            title="✨ Shiny Found!",
            description=f"**{interaction.user.display_name}** found a shiny **{pokemon.capitalize()}**! 🌟",
            color=0xFFD700
        )
        embed.add_field(name="Bonus", value="+150 PokéCoins added to your balance!", inline=False)
        embed.set_footer(text="Don't forget to post a screenshot as proof!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shinydex", description="See the server's shiny hall of fame")
    async def shinydex(self, interaction: discord.Interaction):
        conn = get_conn()
        rows = conn.execute(
            "SELECT username, pokemon, claimed_at FROM shinies ORDER BY id DESC LIMIT 15"
        ).fetchall()
        conn.close()
        if not rows:
            await interaction.response.send_message("✨ No shinies claimed yet! Be the first with `/shiny_claim`.")
            return
        embed = discord.Embed(title="✨ Shiny Hall of Fame", color=0xFFD700)
        lines = [f"⭐ **{r['pokemon']}** — caught by {r['username']} on {r['claimed_at'][:10]}" for r in rows]
        embed.description = "\n".join(lines)
        embed.set_footer(text="Use /shiny_claim when you find one!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Events(bot))