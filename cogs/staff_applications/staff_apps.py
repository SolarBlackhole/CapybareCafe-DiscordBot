import discord
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
    steam_id = discord.ui.TextInput(label="SteamID64", placeholder="7656119xxxxxxxxxx", min_length=17, max_length=17)
    age = discord.ui.TextInput(label="Age", placeholder="", min_length=2, max_length=2)
    timezone = discord.ui.TextInput(label="Timezone", placeholder="UTC+X", min_length=4, max_length=6)
    has_microphone = discord.ui.TextInput(label="Do you have a microphone?", placeholder="Yes/No", min_length=2, max_length=3)
    experience = discord.ui.TextInput(label="What is your experience with staff roles?", style=discord.TextStyle.paragraph, placeholder="", min_length=10, max_length=2000)
    fit = discord.ui.TextInput(label="Why do you think you'd be a good fit for the staff team?", style=discord.TextStyle.paragraph, placeholder="", min_length=10, max_length=2000)
    bias = discord.ui.TextInput(label="Do you have any biases that would affect your ability to be a fair staff member?", style=discord.TextStyle.paragraph, placeholder="", min_length=10, max_length=2000)
    agreement = discord.ui.TextInput(label="Do you understand that abusing permissions, showing overt toxicity towards community members, or simply not being a good fit for the role may have your role revoked at any time?", placeholder="Yes/No", min_length=2, max_length=3)

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

        embed = discord.Embed(title="New Staff Application", color=discord.Color.blue())
        embed.add_field(name="Applicant", value=interaction.user.mention)
        embed.add_field(name="SteamID64", value=self.steam_id.value)
        embed.add_field(name="Age", value=self.age.value)
        embed.add_field(name="Timezone", value=self.timezone.value)
        embed.add_field(name="Does the applicant have a microphone?", value=self.has_microphone.value)
        embed.add_field(name="Applicant's Experience", value=self.experience.value, inline=False)
        embed.add_field(name="Why they're a good fit", value=self.fit.value, inline=False)
        embed.add_field(name="Potential Biases", value=self.bias.value, inline=False)
        embed.add_field(name="Staff Agreement", value=self.agreement.value)

        await channel.send(embed=embed, view=AppReviewActions(interaction.user))

        await interaction.response.send_message(f"Your application has been submitted! A staff member will review it shortly. You can view your application here: {channel.mention}", ephemeral=True)

        embed = discord.Embed(description=f"{interaction.user.mention} has submitted a staff application! Click the button below to view their application.", color=discord.Color.green())
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Application", style=discord.ButtonStyle.primary, url=channel.jump_url))
        await list_applications_channel.send(embed=embed)

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
        await interaction.response.send_message(f" {self.applicant.mention} you have passed the initial review stage! A staff member will contact you soon.")

        await interaction.message.edit(view=AppFinalActions(self.applicant))

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="deny_screen")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.applicant:
            await interaction.response.send_message("You cannot take action on your own application.", ephemeral=True)
            return
        await self.applicant.send("We've reviewed your app and decided not to move forward. Thank you for your interest in joining the Capybara Cafe staff team!")

        await self.close_with_transcript(interaction, "DENIED")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_application")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Your application has been cancelled.", ephemeral=True)
        await self.close_with_transcript(interaction, "CANCELLED")

    async def close_with_transcript(self, interaction, decision):
        await interaction.channel.send(f"Closing application and generating transcript... Decision: {decision}")
        await interaction.response.defer()

        transcript = await chat_exporter.export(interaction.channel)
        log_channel = interaction.guild.get_channel(int(os.getenv('APPLICATION_LOG_CHANNEL_ID')))

        if transcript:
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"application-{self.applicant.name}.html")
            await log_channel.send(f"Application for {self.applicant.mention} has been {decision}. Transcript attached.", file=transcript_file)
        
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

        if transcript:
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"application-{self.applicant.name}.html")
            await log_channel.send(f"Application for {self.applicant.mention} has been {decision}. Transcript attached.", file=transcript_file)
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

class StaffApplications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bot.tree.command(
            name="toggle_apps", 
            description="Toggle staff applications open/closed"
    )
    @app_commands.checks.has_role(int(os.getenv('STAFF_MANAGER_ROLE_ID')))
    async def toggle_apps(interaction: discord.Interaction, open_status: bool):
        channel = interaction.guild.get_channel(int(os.getenv('BUTTON_CHANNEL_ID')))
        view = StaffAppLauncher(is_open=open_status)
        embed = discord.Embed(
            title="Staff Recruitment",
            description="We are currently accepting applications for new staff members! If you're interested in joining our team, please click the button below to apply. We look forward to reviewing your application and potentially welcoming you to the team!"
        )
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Staff applications have been {'opened' if open_status else 'closed'}.", ephemeral=True)   
