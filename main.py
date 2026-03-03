import discord
import os
import asyncio
import aiomysql
from discord.ext import commands
from dotenv import load_dotenv


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=os.getenv('COMMAND_PREFIX'), intents=intents)
        self.db_pool = None  # Placeholder for database connection pool

    async def setup_hook(self):
        self.db_pool = await aiomysql.create_pool(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            db=os.getenv('DB_NAME'),
            autocommit=True
        )

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded cog: {filename}')
    
    async def on_ready(self):
        await self.wait_until_ready()
        
        print(f'Logged in as {self.user} (ID: {self.user.id})')

bot = MyBot()

bot.run(os.getenv('BOT_TOKEN'))