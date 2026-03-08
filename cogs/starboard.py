import discord
from discord.ext import commands
import os

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.star_emoji = '⭐'
        self.threshold = int(os.getenv("STARBOARD_THRESHOLD", 5))
        self.starboard_channel_id = int(os.getenv("STARBOARD_CHANNEL_ID")) 

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) != self.star_emoji:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if not channel: return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        if message.author.bot or message.author.id == payload.user_id:
            return
        
        starboard_channel = self.bot.get_channel(self.starboard_channel_id)
        if not starboard_channel:
            return

        entry = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE original_message_id = %s", message.id)
        
        reaction = discord.utils.get(message.reactions, emoji=self.star_emoji)
        star_count = reaction.count if reaction else 0

        content = f"{self.star_emoji} **{star_count}** | {channel.mention}"
        embed = discord.Embed(description=message.content, color=discord.Color.gold())
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="Original Message", value=f"[Jump to message]({message.jump_url})", inline=False)
        embed.set_footer(text=f"ID: {message.id}")
        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        if entry:
            try:
                starboard_msg = await starboard_channel.fetch_message(entry["starboard_message_id"])
                await starboard_msg.edit(content=content, embed=embed)
                await self.bot.db.execute("UPDATE starboard SET stars = %s WHERE original_message_id = %s", star_count, message.id)
            except discord.NotFound:
                # If the post was deleted manually, let it be recreated if threshold is met
                if star_count >= self.threshold:
                    new_msg = await starboard_channel.send(content=content, embed=embed)
                    await self.bot.db.execute("UPDATE starboard SET starboard_message_id = %s, stars = %s WHERE original_message_id = %s", new_msg.id, star_count, message.id)
        
        elif star_count >= self.threshold:
            starboard_msg = await starboard_channel.send(content=content, embed=embed)
            await self.bot.db.execute("INSERT INTO starboard (original_message_id, starboard_message_id, stars) VALUES (%s, %s, %s)", message.id, starboard_msg.id, star_count)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if str(payload.emoji) != self.star_emoji:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel: return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        entry = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE original_message_id = %s", message.id)
        if not entry: return 

        starboard_channel = self.bot.get_channel(self.starboard_channel_id)
        reaction = discord.utils.get(message.reactions, emoji=self.star_emoji)
        star_count = reaction.count if reaction else 0

        try:
            starboard_msg = await starboard_channel.fetch_message(entry["starboard_message_id"])
            
            content = f"{self.star_emoji} **{star_count}** | {channel.mention}"
            await starboard_msg.edit(content=content)
            await self.bot.db.execute("UPDATE starboard SET stars = %s WHERE original_message_id = %s", star_count, message.id)
        except discord.NotFound:
            pass 

async def setup(bot):
    await bot.add_cog(Starboard(bot))