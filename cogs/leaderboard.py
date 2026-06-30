import discord
from discord.ext import commands
from discord import app_commands
from helpers.leaderboard_helper import LeaderboardHelper
import time
import random
import math

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = LeaderboardHelper(bot.db_pool)
        self.cooldowns = {} # Added: Initialize the cooldown dictionary

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
            
        user_id = message.author.id
        current_time = time.time()

        # Cooldown Check
        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 60:
            return
        
        # Database Fetch
        user_data = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE user_id = %s", user_id)
        if not user_data:
            await self.bot.db.execute("INSERT INTO leveling (user_id, xp, level) VALUES (%s, 0, 0)", user_id)
            user_data = {"xp": 0, "level": 0}

        self.cooldowns[user_id] = current_time
        xp_gain = random.randint(10, 25)
        new_xp = user_data['xp'] + xp_gain
        current_level = user_data['level']

        # Level Up Math: XP = 5 * (lvl^2) + (50 * lvl) + 100
        next_level_xp = 5 * (current_level**2) + (50 * current_level) + 100
        
        if new_xp >= next_level_xp:
            current_level += 1
            await self.bot.db.execute(
                "UPDATE leveling SET xp = %s, level = %s WHERE user_id = %s", 
                new_xp, current_level, user_id
            )
            # Send level up message
            await message.channel.send(f"🎉 Congrats {message.author.mention}, you reached **Level {current_level}**!")
        else:
            await self.bot.db.execute("UPDATE leveling SET xp = %s WHERE user_id = %s", new_xp, user_id)

    @app_commands.command(name="rank", description="Check your rank")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target_user = member or interaction.user
        await interaction.response.defer()
        
        user_data = await self.bot.db.fetchrow("SELECT xp, level FROM leveling WHERE user_id = %s", target_user.id)
        
        if not user_data:
            return await interaction.followup.send(f"{target_user.display_name} hasn't earned any XP yet.")

        xp = user_data['xp']
        level = user_data['level']
        needed_xp = 5 * (level**2) + (50 * level) + 100

        embed = discord.Embed(title=f"{target_user.display_name}'s Rank", color=discord.Color.green())
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp} / {needed_xp}", inline=True)

        progress = min(1.0, xp / needed_xp)
        bar_count = int(progress * 10)
        bar = "█" * bar_count + "░" * (10 - bar_count)
        embed.add_field(name="Progress", value=f"`{bar}`", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top 10 members")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Fetching top 10 from MariaDB
        rows = await self.bot.db.fetch("SELECT user_id, xp, level FROM leveling ORDER BY xp DESC LIMIT 10")

        embed = discord.Embed(title="The Cafe's most active members", color=discord.Color.gold())
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        leaderboard_text = ""
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row['user_id'])
            name = user.name if user else f"Unknown({row['user_id']})"
            leaderboard_text += f"**#{i}** {name} • Lvl {row['level']} ({row['xp']} XP)\n"

        embed.description = leaderboard_text or "No one on the leaderboard yet!"
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))