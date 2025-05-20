# handlers.py
import discord
from discord import app_commands
from discord.ext import commands
from blizzard_api import get_current_dungeons
from enum import Enum

class Role(str, Enum):
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"

# Custom Discord emoji IDs
ROLE_ICONS = {
    "tank": "<:tank:1310400665239027813>",
    "healer": "<:heal:1310400663485943848>",
    "dps": "<:dps:1310400661569146890>"
}

# Discord Role IDs
ROLE_IDS = {
    "tank": 1374336518495146095,
    "healer": 1374336572538753104,
    "dps": 1374336600703762543
}

active_groups = {}

@app_commands.guild_only()
class DungeonCommands(commands.Cog):
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.dungeon_pool = []

    async def cog_load(self):
        self.dungeon_pool = await get_current_dungeons()
        print(f"🔁 Dungeon pool loaded: {self.dungeon_pool}")

    @app_commands.command(name="startdungeon", description="Start a Mythic+ group")
    @app_commands.describe(
        dungeon="Dungeon name",
        key_level="Key level (0-20)",
        your_role="Your role in the group"
    )
    async def startdungeon(
        self,
        interaction: discord.Interaction,
        dungeon: str,
        key_level: app_commands.Range[int, 0, 20],
        your_role: Role
    ):
        if dungeon not in self.dungeon_pool:
            await interaction.response.send_message(f"❌ Invalid dungeon. Available: {', '.join(self.dungeon_pool)}", ephemeral=True)
            return

        # Check if there's already an active group in this channel
        if interaction.channel_id in active_groups:
            await interaction.response.send_message("❌ There's already an active group in this channel. Use `/canceldungeon` to remove it first.", ephemeral=True)
            return

        group_info = {
            "dungeon": dungeon,
            "key_level": key_level,
            "tank": None,
            "healer": None,
            "dps": [],
            "players": set(),  # Track all players in group
            "creator": interaction.user  # Track who created the group
        }

        # Auto-assign creator to their selected role
        if your_role == Role.TANK:
            group_info["tank"] = interaction.user
        elif your_role == Role.HEALER:
            group_info["healer"] = interaction.user
        elif your_role == Role.DPS:
            group_info["dps"].append(interaction.user)
        group_info["players"].add(interaction.user)
        
        # Create initial status message
        status_embed = self.create_group_status(group_info)
        view = RoleButtons(interaction.channel_id)
        
        # Create ping message for needed roles
        ping_message = self.create_role_ping_message(your_role)
        
        # Send and store message
        await interaction.response.send_message(
            f"{ping_message}\n🌀 Group started for **{dungeon}** at **+{key_level}**!",
            embed=status_embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        
        # Add group to active groups
        active_groups[interaction.channel_id] = group_info

    def create_role_ping_message(self, filled_role: Role) -> str:
        """Create a message that pings all needed roles except the one already filled."""
        needed_roles = []
        
        if filled_role != Role.TANK:
            needed_roles.append(f"<@&{ROLE_IDS['tank']}>")
        if filled_role != Role.HEALER:
            needed_roles.append(f"<@&{ROLE_IDS['healer']}>")
        if filled_role != Role.DPS:
            needed_roles.append(f"<@&{ROLE_IDS['dps']}>")
            
        return " ".join(needed_roles)

    @app_commands.command(name="canceldungeon", description="Cancel the current Mythic+ group")
    async def canceldungeon(self, interaction: discord.Interaction):
        group = active_groups.get(interaction.channel_id)
        
        if not group:
            await interaction.response.send_message("❌ No active group in this channel.", ephemeral=True)
            return

        # Only allow the group creator or administrators to cancel
        if interaction.user != group["creator"] and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only the group creator or administrators can cancel the group.", ephemeral=True)
            return

        # Remove the group
        del active_groups[interaction.channel_id]
        
        # Send confirmation
        embed = discord.Embed(
            title="Group Cancelled",
            description=f"The group for **{group['dungeon']} +{group['key_level']}** has been cancelled.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)

    @startdungeon.autocomplete('dungeon')
    async def dungeon_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=dungeon, value=dungeon)
            for dungeon in self.dungeon_pool
            if current.lower() in dungeon.lower()
        ][:25]

    def create_group_status(self, group):
        status = discord.Embed(
            title=f"{group['dungeon']} +{group['key_level']}",
            color=discord.Color.blue()
        )
        
        # Tank status (Shield icon for tank)
        tank_name = group['tank'].display_name if group['tank'] else "Not filled"
        tank_status = "✅" if group['tank'] else "❌"
        status.add_field(name=f"{ROLE_ICONS['tank']} Tank", value=f"{tank_status} {tank_name}", inline=False)
        
        # Healer status (Green cross for healer)
        healer_name = group['healer'].display_name if group['healer'] else "Not filled"
        healer_status = "✅" if group['healer'] else "❌"
        status.add_field(name=f"{ROLE_ICONS['healer']} Healer", value=f"{healer_status} {healer_name}", inline=False)
        
        # DPS status (Crossed swords for DPS)
        dps_list = "\n".join([f"✅ {dps.display_name}" for dps in group['dps']])
        if not dps_list:
            dps_list = "❌ No DPS signed up"
        status.add_field(name=f"{ROLE_ICONS['dps']} DPS ({len(group['dps'])}/3)", value=dps_list, inline=False)
        
        # Add group creator
        status.set_footer(text=f"Created by {group['creator'].display_name}")
        
        return status

class RoleButtons(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Tank", style=discord.ButtonStyle.primary, custom_id="join_tank", emoji=ROLE_ICONS['tank'])
    async def tank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "tank")

    @discord.ui.button(label="Healer", style=discord.ButtonStyle.success, custom_id="join_healer", emoji=ROLE_ICONS['healer'])
    async def healer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "healer")

    @discord.ui.button(label="DPS", style=discord.ButtonStyle.secondary, custom_id="join_dps", emoji=ROLE_ICONS['dps'])
    async def dps(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.assign_role(interaction, "dps")

    async def assign_role(self, interaction: discord.Interaction, role):
        group = active_groups.get(self.channel_id)

        if not group:
            await interaction.response.send_message("❌ No active group.", ephemeral=True)
            return

        user = interaction.user

        # Check if user is already in the group
        if user in group["players"]:
            await interaction.response.send_message("❌ You're already in this group.", ephemeral=True)
            return

        response_text = None

        if role == "tank":
            if group["tank"]:
                await interaction.response.send_message(f"{ROLE_ICONS['tank']} Tank slot already filled.", ephemeral=True)
                return
            group["tank"] = user
            response_text = f"{user.display_name} joined as **Tank** {ROLE_ICONS['tank']}"

        elif role == "healer":
            if group["healer"]:
                await interaction.response.send_message(f"{ROLE_ICONS['healer']} Healer slot already filled.", ephemeral=True)
                return
            group["healer"] = user
            response_text = f"{user.display_name} joined as **Healer** {ROLE_ICONS['healer']}"

        elif role == "dps":
            if len(group["dps"]) >= 3:
                await interaction.response.send_message(f"{ROLE_ICONS['dps']} All DPS slots are filled.", ephemeral=True)
                return
            group["dps"].append(user)
            response_text = f"{user.display_name} joined as **DPS** {ROLE_ICONS['dps']}"

        # Add user to players set
        group["players"].add(user)

        # Update the embed in the message
        status_embed = DungeonCommands.create_group_status(None, group)
        await interaction.message.edit(embed=status_embed)
        
        # Send confirmation to user
        await interaction.response.send_message(response_text, ephemeral=True)

        # Check if group is ready
        if group["tank"] and group["healer"] and len(group["dps"]) == 3:
            await interaction.channel.send(
                f"✅ Group for **{group['dungeon']} +{group['key_level']}** is ready!\n"
                "```\n"
                f"{ROLE_ICONS['tank']} Tank:   {group['tank'].display_name}\n"
                f"{ROLE_ICONS['healer']} Healer: {group['healer'].display_name}\n"
                f"{ROLE_ICONS['dps']} DPS:    {', '.join([dps.display_name for dps in group['dps']])}\n"
                "```"
            )
            del active_groups[self.channel_id]
