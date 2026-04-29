import discord
from discord.ext import commands
from discord import app_commands
from helpers.tickets_helper import TicketsHelper
import asyncio
import os

class TicketsLauncher(discord.ui.View):
    def __init__(self, helper):
        super().__init__(timeout=None)
        self.helper = helper

    # Create Ticket Button - Support
    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(int(os.getenv('TICKETS_CATEGORY_ID')))
        if not category:
            category = await guild.create_category("Tickets")

        ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", 
                                                         category=category,
                                                         overwrites={
                                                                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                                                                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                                                                guild.get_role(int(os.getenv('STAFF_ROLE_ID'))): discord.PermissionOverwrite(read_messages=True, send_messages=True)
                                                            }
                                                        )
        await self.helper.create_ticket_record(interaction.user.id, ticket_channel.id)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await ticket_channel.set_permissions(guild.default_role, read_messages=False)

        await interaction.followup.send(f"Ticket created: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(f"{interaction.user.mention} Welcome to your support ticket! A staff member will be with you shortly. To close this ticket, use the 'Close Ticket' button below.", view=CloseTicketView(self.helper))

    # Create Ticket Button - Report
    @discord.ui.button(label="Report User", style=discord.ButtonStyle.danger, custom_id="report_user")
    async def report_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReportPlayerModal())

class CloseTicketView(discord.ui.View):
    def __init__(self, helper):
        super().__init__(timeout=None)
        self.helper = helper

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.gray, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(description="Are you sure you want to close this ticket?", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, view=ConfirmClose(self.helper), ephemeral=True)

class ConfirmClose(discord.ui.View):
    def __init__(self, helper):
        super().__init__(timeout=180)
        self.helper = helper

    @discord.ui.button(label="Yes, Close", style=discord.ButtonStyle.danger, custom_id="confirm_close")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        channel = interaction.channel
        transcripts_channel= interaction.guild.get_channel(int(os.getenv('APPLICATION_LOG_CHANNEL_ID')))
        await channel.send("Closing ticket and generating transcript...")
        transcript_file = await self.helper.generate_transcript(channel)
        if transcript_file:
            await channel.send("Here is the transcript of your ticket:", file=transcript_file)
            await transcripts_channel.send(f"Transcript for ticket {channel.name} (ID: {channel.id}):", file=transcript_file)
        else:
            await channel.send("Failed to generate transcript.")
        await channel.send("Thank you for contacting support! This ticket will now be closed in 10 seconds.")
        await self.helper.close_ticket_record(channel.id)
        await asyncio.sleep(10)
        await channel.delete()

    @discord.ui.button(label="No, Keep Open", style=discord.ButtonStyle.secondary, custom_id="cancel_close")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ticket closure cancelled.", embed=None, view=None)

class ReportPlayerModal(discord.ui.Modal, title="Report a Player"):
    player_name = discord.ui.TextInput(label="Player Name / Steam ID", placeholder="Enter the player's name or Steam ID", required=True)
    report_reason = discord.ui.TextInput(label="Reason for Report", placeholder="Describe the reason for reporting this player", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = await guild.create_text_channel(name=f"report-{interaction.user.name}", category=guild.get_channel(int(os.getenv('TICKETS_CATEGORY_ID'))))
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(guild.default_role, read_messages=False)
        await channel.set_permissions(guild.get_role(int(os.getenv('STAFF_ROLE_ID'))), read_messages=True, send_messages=True)

        embed = discord.Embed(title="New Player Report", color=discord.Color.red())
        embed.add_field(name="Reporter", value=interaction.user.mention, inline=False)
        embed.add_field(name="Player Name / Steam ID", value=self.player_name.value, inline=False)
        embed.add_field(name="Reason for Report", value=self.report_reason.value, inline=False)
        await channel.send(embed=embed, content=f"{interaction.user.mention} Your report has been submitted. A staff member will review it shortly. To close this report, use the 'Close Ticket' button below.", view=CloseTicketView(TicketsHelper(interaction.client.db_pool)))
        await interaction.response.send_message(f"Report submitted: {channel.mention}", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = TicketsHelper(bot.db_pool)

    @app_commands.command(
        name="setup_tickets", 
        description="Sends the persistent ticket buttons to the designated support channel."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        
        # 1. Initialize the View
        view = TicketsLauncher(self.helper)
        
        # 2. Get the target channel from .env
        channel_id = os.getenv('BUTTON_CHANNEL_ID')
        if not channel_id:
            return await interaction.response.send_message(
                "Error: BUTTON_CHANNEL_ID not found in .env", ephemeral=True
            )
            
        target_channel = interaction.guild.get_channel(int(channel_id))
        
        if target_channel:
            embed = discord.Embed(
                title="Support Center",
                description="Click the buttons below to open a private ticket with our staff.",
                color=discord.Color.blue()
            )
            await target_channel.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                f"✅ Ticket system deployed to {target_channel.mention}!", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Error: Could not find the specified channel. Check your ID.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Tickets(bot))