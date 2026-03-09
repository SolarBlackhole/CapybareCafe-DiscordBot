import discord
from discord.ext import commands
import os

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pull from .env
        self.join_role_id = int(os.getenv("WELCOME_JOIN_ROLE_ID"))
        self.welcome_channel_id = int(os.getenv("WELCOME_CHANNEL_ID"))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = member.guild.get_role(self.join_role_id)
        if role:
            await member.add_roles(role)
            print(f"Assigned role to {member.display_name}")
        
        embed = discord.Embed(title="Welcome to the server!", description=f"Hello {member.mention}, welcome to the {member.guild.name}! We hope you enjoy your stay.", color=discord.Color.green())
        embed.set_thumbnail(url=member.avatar.url)
        channel = self.bot.get_channel(self.welcome_channel_id)
        if channel:
            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))