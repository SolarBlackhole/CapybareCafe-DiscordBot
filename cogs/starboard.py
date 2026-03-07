import discord
from discord.ext import commands
import os

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.star_emoji = '⭐'
        self.threshold = 5
        self.starboard_channel_id = int(os.getenv("STARBOARD_CHANNEL_ID"))  # Replace with your starboard channel ID

    @commands.Cog.listener()
    async def on_reaction_add(self, payload):
        if str(payload.emoji) != self.star_emoji:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if message.author.bot or message.author.id == payload.user_id:
            return
        
        starboard_channel = self.bot.get_channel(self.starboard_channel_id)
        if not starboard_channel:
            print("❌ Starboard channel not found. Please check the STARBOARD_CHANNEL_ID in your .env file.")
            return
        
        # Count the number of star reactions
        reaction = discord.utils.get(message.reactions, emoji=self.star_emoji)
        star_count = reaction.count if reaction else 0
        
        if star_count >= self.threshold:

            entry = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE original_message_id = %s", message.id)

            embed = discord.Embed(description=message.content, color=discord.Color.gold())
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="Original Message", value=f"[Jump to message]({message.jump_url})", inline=False)
            embed.set_footer(text=f"{star_count} {self.star_emoji} | ID: {message.id}")
            
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)

            content = f"{self.star_emoji} **{star_count}** | {channel.mention}"

            if entry:
                starboard_msg = await starboard_channel.fetch_message(entry['starboard_message_id'])
                await starboard_msg.edit(content=content, embed=embed)
                await self.bot.db.execute("UPDATE starboard SET stars = %s WHERE original_message_id = %s", star_count, message.id)

            else:
                starboard_msg = await starboard_channel.send(content=content, embed=embed)
                await self.bot.db.execute("INSERT INTO starboard (original_message_id, starboard_message_id, stars) VALUES (%s, %s, %s)", message.id, starboard_msg.id, star_count)

async def setup(bot):
    await bot.add_cog(Starboard(bot))