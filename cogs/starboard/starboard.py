import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import aiomysql

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.star_emoji = '⭐'
        self.threshold = 5
        self.starboard_channel_id = int(os.getenv("STARBOARD_CHANNEL_ID"))  # Replace with your starboard channel ID

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if str(reaction.emoji) == self.star_emoji:
            channel = self.bot.get_channel(reaction.message.channel.id)
            messsage = await channel.fetch_message(reaction.message.id)

            reaction = discord.utils.get(messsage.reactions, emoji=self.star_emoji)
            if reaction and reaction.count == self.threshold:
                target_channel = self.bot.get_channel(self.starboard_channel_id)

                # TODO: Check if the message is already in the starboard to prevent duplicates
                # Check MariaDB for existing entry before posting

                embed = discord.Embed(description=messsage.content, color=discord.Color.gold())
                embed.set_author(name=messsage.author.display_name, icon_url=messsage.author.avatar.url)
                embed.add_field(name="Original Message", value=f"[Jump to message]({messsage.jump_url})")

                await target_channel.send(content=f" 🌟 **{reaction.count}** | { channel.mention}", embed=embed)

async def setup(bot):
    await bot.add_cog(Starboard(bot))