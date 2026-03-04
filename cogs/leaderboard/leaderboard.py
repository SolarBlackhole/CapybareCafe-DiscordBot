from discord.ext import commands
from .leaderboard_helper import LeaderboardHelper

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = LeaderboardHelper(bot.db_pool)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        user_id = message.author.id
        current_time = asyncio.get_event_loop().time()

        if user_id in self.cooldowns and current_time - self.cooldowns[user_id] < 60:
            return
        
        # SQL
        
        self.cooldowns[user_id] = current_time

    