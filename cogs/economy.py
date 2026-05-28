import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime, date
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import get_conn

DAILY_AMOUNT = 200
LEVEL_UP_XP = 500

SHOP_ITEMS = [
    {"id": 1, "name": "🌟 Shiny Hunter",    "description": "Cosmetic role for shiny enthusiasts",  "price": 800},
    {"id": 2, "name": "🏆 Tournament Ace",  "description": "Cosmetic role for tournament winners",  "price": 1200},
    {"id": 3, "name": "🎯 Event Entry",     "description": "Guaranteed slot in the next event",     "price": 300},
    {"id": 4, "name": "🍀 Lucky Charm",     "description": "Doubles your next trivia coin reward",  "price": 500},
]

def ensure_user(user_id: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, coins) VALUES (?, 0)", (user_id,)
    )
    conn.commit()
    conn.close()

def add_coins(user_id: str, amount: int):
    ensure_user(user_id)
    conn = get_conn()
    conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_user(user_id: str):
    ensure_user(user_id)
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_xp(user_id: str, xp: int):
    ensure_user(user_id)
    conn = get_conn()
    user = dict(conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone())
    new_xp = user["xp"] + xp
    new_level = user["trainer_level"]
    leveled_up = False
    while new_xp >= LEVEL_UP_XP:
        new_xp -= LEVEL_UP_XP
        new_level += 1
        leveled_up = True
    conn.execute(
        "UPDATE users SET xp = ?, trainer_level = ? WHERE user_id = ?",
        (new_xp, new_level, user_id)
    )
    conn.commit()
    conn.close()
    return leveled_up, new_level

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your PokéCoin balance")
    async def balance(self, interaction: discord.Interaction):
        user = get_user(str(interaction.user.id))
        embed = discord.Embed(title="💰 PokéCoin Balance", color=0xFFD700)
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Coins", value=f"**{user['coins']}** PokéCoins", inline=True)
        embed.add_field(name="Trainer Level", value=f"**Lv. {user['trainer_level']}**", inline=True)
        embed.add_field(
            name="XP Progress",
            value=f"{user['xp']} / {LEVEL_UP_XP} XP",
            inline=True
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="checkin", description="Daily check-in for PokéCoins!")
    async def checkin(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        user = get_user(uid)
        today = str(date.today())
        if user["last_checkin"] == today:
            await interaction.response.send_message("⏰ You've already checked in today! Come back tomorrow.", ephemeral=True)
            return
        conn = get_conn()
        conn.execute(
            "UPDATE users SET coins = coins + ?, last_checkin = ? WHERE user_id = ?",
            (DAILY_AMOUNT, today, uid)
        )
        conn.commit()
        conn.close()
        leveled_up, level = add_xp(uid, 50)
        msg = f"✅ Daily check-in! You received **{DAILY_AMOUNT} PokéCoins**."
        if leveled_up:
            msg += f"\n🎉 You leveled up to **Trainer Lv. {level}**!"
        await interaction.response.send_message(msg)

    @app_commands.command(name="give", description="Send PokéCoins to a friend")
    @app_commands.describe(member="Who to send coins to", amount="How many coins")
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        user = get_user(uid)
        if user["coins"] < amount:
            await interaction.response.send_message("❌ You don't have enough PokéCoins!", ephemeral=True)
            return
        conn = get_conn()
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (amount, uid))
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, str(member.id)))
        conn.commit()
        conn.close()
        ensure_user(str(member.id))
        await interaction.response.send_message(
            f"💸 **{interaction.user.display_name}** sent **{amount} PokéCoins** to **{member.display_name}**!"
        )

    @app_commands.command(name="shop", description="Browse the PokéNode shop")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 PokéNode Shop", description="Spend your hard-earned PokéCoins!", color=0x00CED1)
        for item in SHOP_ITEMS:
            embed.add_field(
                name=f"`#{item['id']}` {item['name']} — {item['price']} coins",
                value=item["description"],
                inline=False
            )
        embed.set_footer(text="Use /buy [item_id] to purchase")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_id="Item number from /shop")
    async def buy(self, interaction: discord.Interaction, item_id: int):
        item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
        if not item:
            await interaction.response.send_message("❌ Invalid item ID. Use `/shop` to see available items.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        user = get_user(uid)
        if user["coins"] < item["price"]:
            await interaction.response.send_message(
                f"❌ You need **{item['price']} coins** but only have **{user['coins']}**.", ephemeral=True
            )
            return
        conn = get_conn()
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (item["price"], uid))
        conn.commit()
        conn.close()
        await interaction.response.send_message(
            f"✅ You bought **{item['name']}** for **{item['price']} PokéCoins**!\n"
            f"📬 Contact a server admin to have your reward applied."
        )

    @app_commands.command(name="trade", description="Propose an item trade with another player")
    @app_commands.describe(
        member="Who you want to trade with",
        offer="What you're offering (e.g. Masterball)",
        want="What you want in return (e.g. 300 PokéCoins)"
    )
    async def trade(self, interaction: discord.Interaction, member: discord.Member, offer: str, want: str):
        uid = str(interaction.user.id)
        now = datetime.utcnow().isoformat()
        conn = get_conn()
        conn.execute(
            "INSERT INTO trades (offerer_id, offerer_name, target_id, offer, want, created_at) VALUES (?,?,?,?,?,?)",
            (uid, interaction.user.display_name, str(member.id), offer, want, now)
        )
        trade_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        conn.close()

        embed = discord.Embed(title="🤝 Trade Proposal", color=0x32CD32)
        embed.add_field(name="From", value=interaction.user.mention, inline=True)
        embed.add_field(name="To", value=member.mention, inline=True)
        embed.add_field(name="📦 Offering", value=offer, inline=False)
        embed.add_field(name="🎯 Wants", value=want, inline=False)
        embed.set_footer(text=f"Trade #{trade_id} • Both players must agree in-game to complete")
        await interaction.response.send_message(content=member.mention, embed=embed)

    @app_commands.command(name="profile", description="View your or another player's trainer profile")
    @app_commands.describe(member="Leave blank to see your own profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        user = get_user(str(target.id))
        embed = discord.Embed(title=f"🎮 Trainer Profile — {target.display_name}", color=0x9B59B6)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 PokéCoins", value=user["coins"], inline=True)
        embed.add_field(name="⭐ Trainer Level", value=f"Lv. {user['trainer_level']}", inline=True)
        embed.add_field(name="✨ Shinies Found", value=user["shiny_count"], inline=True)
        embed.add_field(name="🌱 Starter", value=user["starter"] or "Not chosen yet", inline=True)
        embed.add_field(name="📈 XP", value=f"{user['xp']} / {LEVEL_UP_XP}", inline=True)
        embed.set_footer(text="PokéNode • Use /starter to pick your starter!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))