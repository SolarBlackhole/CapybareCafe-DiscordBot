from discord.ext import commands
from .leaderboard_helper import LeaderboardHelper

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = LeaderboardHelper(bot.db_pool)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        xp, old_level = await self.helper.add_xp(message.author.id, 10)
        new_level = self.helper.calculate_level(xp)
        if new_level > old_level:
            await message.channel.send(f"Congratulations {message.author.mention}! You've reached level {new_level}.")