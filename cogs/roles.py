import discord
from discord.ext import commands
from discord import app_commands
from helpers.roles_helper import RolesHelper

class DynamicRoleView(discord.ui.View):
    def __init__(self, roles_data):
        super().__init__(timeout=None)
        # roles_data is a list of {"role_id": int, "label": str, "style": str} from MariaDB
        for data in roles_data:
            style_value = data.get('style', 'primary').lower()
            style = getattr(discord.ButtonStyle, style_value, discord.ButtonStyle.primary)
            self.add_item(RoleButton(data['role_id'], data['label'], style))

class RoleButton(discord.ui.Button):
    def __init__(self, role_id, label, style):
        super().__init__(label=label, style=style, custom_id=f"role_btn:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("❌ This role no longer exists.", ephemeral=True)

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"✅ Removed role: **{role.name}**", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ Added role: **{role.name}**", ephemeral=True)

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helper = RolesHelper(bot.db_pool)

    @app_commands.command(name="role_menu_add", description="Add a role button to an existing menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_role(self, interaction: discord.Interaction, message_id: str, role: discord.Role, label: str):
        await interaction.response.defer(ephemeral=True)
        await self.helper.add_role_to_menu(int(message_id), role.id, label, style = "primary")

        roles_data = await self.helper.get_menu_roles(int(message_id))
        
        try:
            channel = interaction.channel
            message = await channel.fetch_message(int(message_id))
            await message.edit(view=DynamicRoleView(roles_data))
            await interaction.followup.send(f"✅ Added **{role.name}** to menu `{message_id}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to edit message: {e}", ephemeral=True)

    @app_commands.command(name="role_menu_remove", description="Remove a role button from a menu")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_role(self, interaction: discord.Interaction, message_id: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        
        await self.helper.remove_role_from_menu(int(message_id), role.id)
        
        roles_data = await self.helper.get_menu_roles(int(message_id))
        
        try:
            channel = interaction.channel
            message = await channel.fetch_message(int(message_id))
            await message.edit(view=DynamicRoleView(roles_data))
            await interaction.followup.send(f"✅ Removed **{role.name}** from menu `{message_id}`", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to edit message: {e}", ephemeral=True)

    @app_commands.command(name="role_menu_create", description="Create a new role menu message")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_menu(self, interaction: discord.Interaction, channel: discord.TextChannel, title: str, description: str):
        await interaction.response.defer(ephemeral=True)
        
        menu_message = await channel.send(content=f"**{title}**\n{description}", view=DynamicRoleView([]))
        
        await self.helper.add_role_to_menu(menu_message.id, 0, "placeholder", style="primary")
        
        await interaction.followup.send(f"✅ Created new role menu in {channel.mention} with ID `{menu_message.id}`. Use this ID to add buttons.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))
