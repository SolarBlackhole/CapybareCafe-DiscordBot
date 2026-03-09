import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import chat_exporter
import io

class StaffAppLauncher(discord.ui.View):
    def __init__(self, is_open = False):
        super().__init__(timeout=None)
        
        btn_style = discord.ButtonStyle.green if is_open else discord.ButtonStyle.grey
        btn_label = "Apply for Staff" if is_open else "Applications Closed"

        self.apply_button = discord.ui.Button(
            label=btn_label,
            style=btn_style,
            disabled=not is_open,
            custom_id="persistent:apply_button"
        )
        self.apply_button.callback = self.on_apply_click
        self.add_item(self.apply_button)

    async def on_apply_click(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StaffAppModal())

class StaffAppModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Staff Application")

    # Field 1: Basic Info
    basics = discord.ui.TextInput(
        label="SteamID64 & Age", 
        placeholder="SteamID: 7656119xxxxxxxxxx | Age: 25",
        min_length=20, 
        max_length=50
    )
    
    availability = discord.ui.TextInput(
        label="Timezone & Microphone", 
        placeholder="Timezone: UTC+0 | Mic: Yes",
        min_length=10, 
        max_length=40
    )
    
    experience = discord.ui.TextInput(
        label="Prior Experience", 
        style=discord.TextStyle.paragraph, 
        placeholder="What is your experience with moderation roles?", 
        min_length=10, 
        max_length=1000
    )
    
    fit_bias = discord.ui.TextInput(
        label="Fit & Biases", 
        style=discord.TextStyle.paragraph, 
        placeholder="Why are you a good fit? Any biases we should know?", 
        min_length=10, 
        max_length=1500
    )

    agreement = discord.ui.TextInput(
        label="Do you agree to follow the code of conduct?", 
        placeholder="Yes/No", 
        min_length=2, 
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        list_applications_channel = guild.get_channel(int(os.getenv('APPLICATION_CHANNEL_ID')))
        applicant_category = list_applications_channel.category

        # Crete a private channel for the applicant
        channel = await guild.create_text_channel(f"application-{interaction.user.name}", category=applicant_category, overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(int(os.getenv('STAFF_MANAGER_ROLE_ID'))): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        })

        await interaction.client.db.execute(
            "INSERT INTO tickets (channel_id, user_id, ticket_type, status) VALUES (%s, %s, 'staff_app', 'open')",
            channel.id, interaction.user.id
        )

        embed = discord.Embed(title="New Staff Application", color=discord.Color.blue())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        embed.add_field(name="Applicant", value=interaction.user.mention, inline=True)
        embed.add_field(name="Basics (SteamID/Age)", value=self.basics.value, inline=True)
        embed.add_field(name="Availability (TZ/Mic)", value=self.availability.value, inline=True)
    
        embed.add_field(name="Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Fit & Biases", value=self.fit_bias.value, inline=False)
        embed.add_field(name="Staff Agreement", value=self.agreement.value, inline=False)

        await channel.send(embed=embed, view=AppReviewActions(interaction.user))

        await interaction.response.send_message(f"Your application has been submitted! A staff member will review it shortly. You can view your application here: {channel.mention}", ephemeral=True)

        embed = discord.Embed(description=f"{interaction.user.mention} has submitted a staff application! Click the button below to view their application.", color=discord.Color.green())
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Application", style=discord.ButtonStyle.primary, url=channel.jump_url))
        await list_applications_channel.send(embed=embed, view=view)

# This view will be used by staff members to take action on applications after reviewing them
class AppReviewActions(discord.ui.View):
    def __init__(self, applicant):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="Move to Interview Stage", style=discord.ButtonStyle.primary, custom_id="move_to_interview")
    async def interview_stage(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.applicant:
            await interaction.response.send_message("You cannot take action on your own application.", ephemeral=True)
            return
        await interaction.message.edit(view=AppFinalActions(self.applicant))
        await interaction.response.send_message(f" {self.applicant.mention} you have passed the initial review stage! A staff member will contact you soon.")

        

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_screen")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.applicant:
            await interaction.response.send_message("You cannot take action on your own application.", ephemeral=True)
            return
        await self.applicant.send("We've reviewed your app and decided not to move forward. Thank you for your interest in joining the Capybara Cafe staff team!")

        await self.close_with_transcript(interaction, "DENIED")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_application")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_with_transcript(interaction, "CANCELLED")

    async def close_with_transcript(self, interaction, decision):
        if not interaction.response.is_done():
            await interaction.response.defer()

        await interaction.channel.send(f"Closing application and generating transcript... Decision: {decision}")

        transcript = await chat_exporter.export(interaction.channel)
        log_channel = interaction.guild.get_channel(int(os.getenv('APPLICATION_LOG_CHANNEL_ID')))
        await interaction.client.db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = %s", interaction.channel.id)

        if transcript:
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"application-{self.applicant.name}.html")
            await log_channel.send(f"Application for {self.applicant.mention} has been {decision}. Transcript attached.", file=transcript_file)
        
        await interaction.followup.send("The application channel will be deleted in 5 seconds.")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class AppFinalActions(discord.ui.View):
    def __init__(self, applicant):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="Accept Application", style=discord.ButtonStyle.success, custom_id="accept_final")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        trial_mod_role = interaction.guild.get_role(int(os.getenv('TRIAL_MODERATOR_ROLE_ID')))
        await self.applicant.send("Congratulations! Your application has been accepted and you've been given the Trial Moderator role. A staff member will contact you soon with more information.")
        await interaction.guild.get_member(self.applicant.id).add_roles(trial_mod_role)
        await self.close_with_transcript(interaction, "ACCEPTED")

    @discord.ui.button(label="Deny Application", style=discord.ButtonStyle.danger, custom_id="deny_final")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.applicant.send("After further review, we've decided not to move forward with your application. Thank you for your interest in joining the Capybara Cafe staff team!")
        await self.close_with_transcript(interaction, "DENIED")

    async def close_with_transcript(self, interaction, decision):
        await interaction.channel.send(f"Closing application and generating transcript... Decision: {decision}")
        await interaction.response.defer()

        transcript = await chat_exporter.export(interaction.channel)
        log_channel = interaction.guild.get_channel(int(os.getenv('APPLICATION_LOG_CHANNEL_ID')))
        await interaction.client.db.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = %s", interaction.channel.id)

        if transcript:
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"application-{self.applicant.name}.html")
            await log_channel.send(f"Application for {self.applicant.mention} has been {decision}. Transcript attached.", file=transcript_file)
        
        await interaction.followup.send("The application channel will be deleted in 5 seconds.")
        await asyncio.sleep(5)
        await interaction.channel.delete()

class StaffApplications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
            name="toggle_apps", 
            description="Toggle staff applications open/closed"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_apps(self, interaction: discord.Interaction, open_status: bool):
        await interaction.response.defer(ephemeral=True) # Defer because of multiple DB calls
        
        status_val = "open" if open_status else "closed"
        
        # 1. Update the status in DB
        await self.bot.db.execute(
            "INSERT INTO server_settings (setting_key, setting_value) VALUES ('staff_apps', %s) "
            "ON DUPLICATE KEY UPDATE setting_value = %s", status_val, status_val
        )

        channel = interaction.guild.get_channel(int(os.getenv('BUTTON_CHANNEL_ID')))
        
        # 2. Prepare the Embed and View
        if open_status:
            embed = discord.Embed(
                title="Staff Recruitment",
                description="We are currently accepting applications! Click the button below to apply.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Staff Recruitment",
                description="Applications are currently closed. Please check back later!",
                color=discord.Color.red()
            )
        view = StaffAppLauncher(is_open=open_status)

        # 3. Check MariaDB for an existing message ID
        msg_record = await self.bot.db.fetchrow(
            "SELECT setting_value FROM server_settings WHERE setting_key = 'staff_app_msg_id'"
        )

        success_action = "updated"
        if msg_record:
            try:
                # Try to fetch and edit the existing message
                message = await channel.fetch_message(int(msg_record['setting_value']))
                await message.edit(embed=embed, view=view)
            except (discord.NotFound, discord.HTTPException):
                # If message was deleted manually, send a new one
                new_msg = await channel.send(embed=embed, view=view)
                await self.bot.db.execute(
                    "UPDATE server_settings SET setting_value = %s WHERE setting_key = 'staff_app_msg_id'",
                    str(new_msg.id)
                )
                success_action = "re-created (old one missing)"
        else:
            # First time setup: Send message and save ID
            new_msg = await channel.send(embed=embed, view=view)
            await self.bot.db.execute(
                "INSERT INTO server_settings (setting_key, setting_value) VALUES ('staff_app_msg_id', %s)",
                str(new_msg.id)
            )
            success_action = "created"

        await interaction.followup.send(
            content=f"Staff applications have been **{status_val}** and the recruitment message was **{success_action}**.", 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(StaffApplications(bot))
