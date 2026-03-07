import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Helpers
from helpers.db_helper import Database
from helpers.tickets_helper import TicketsHelper
from helpers.leaderboard_helper import LeaderboardHelper
from helpers.roles_helper import RolesHelper

# Views for Persistence
from cogs.tickets import TicketsLauncher, CloseTicketView
from cogs.staff_apps import StaffAppLauncher, AppReviewActions, AppFinalActions
from cogs.roles import DynamicRoleView

load_dotenv()

class CapyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=os.getenv('COMMAND_PREFIX', '!'), intents=intents)
        self.db = Database()

    async def setup_hook(self):
        # 1. Connect to MariaDB
        await self.db.connect()
        # Ensure the pool is accessible via the bot object for all Cogs
        self.db_pool = self.db.pool 

        # 2. Load Cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Loaded cog: {filename}')
                except Exception as e:
                    print(f'❌ Failed to load cog {filename}: {e}')

        # 3. Register Persistent Views
        # Tickets
        self.add_view(TicketsLauncher(TicketsHelper(self.db_pool)))
        self.add_view(CloseTicketView(TicketsHelper(self.db_pool)))

        # Staff Apps Persistence
        app_status = await self.db.fetchrow("SELECT setting_value FROM server_settings WHERE setting_key = 'staff_apps'")
        is_open = (app_status['setting_value'] == "open") if app_status else False
        self.add_view(StaffAppLauncher(is_open=is_open))

        # Roles Persistence
        role_helper = RolesHelper(self.db_pool)
        menu_ids = await role_helper.get_all_menu_ids()
        for msg_id in menu_ids:
            roles_data = await role_helper.get_menu_roles(msg_id)
            self.add_view(DynamicRoleView(roles_data), message_id=msg_id)

        # 4. Sync Commands
        guild_id = os.getenv('GUILD_ID')
        if guild_id:
            guild_obj = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        
        
        print(f"{self.user} is synced and ready!")

bot = CapyBot()

@bot.event
async def on_ready(self):
    activity = discord.Activity(type=discord.ActivityType.watching, name="the cafe")
    await self.change_presence(activity=activity)
    print(f'Logged in as {self.user} (ID: {self.user.id})')
    print('------')

    

bot.run(os.getenv('BOT_TOKEN'))
