# handlers.py
import discord
from discord import app_commands
from discord.ext import commands
from blizzard_api import get_current_dungeons, CURRENT_DUNGEONS
from enum import Enum
from datetime import datetime, timedelta
import re

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

def parse_time(time_str: str) -> datetime:
    """Parse time string in HH:MM format and return datetime object for today/tomorrow."""
    if time_str.lower() == "now":
        return datetime.now()

    # Regular expression to match HH:MM format
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        raise ValueError("Time must be in HH:MM format (e.g., 14:30)")

    # Parse the time
    hour, minute = map(int, time_str.split(':'))
    now = datetime.now()
    scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the time is in the past, assume it's for tomorrow
    if scheduled_time < now:
        scheduled_time += timedelta(days=1)

    return scheduled_time

@app_commands.guild_only()
class DungeonCommands(commands.Cog):
    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.dungeon_pool = CURRENT_DUNGEONS  # Use pre-sorted list immediately

    async def cog_load(self):
        # Update dungeon pool from API if possible
        try:
            self.dungeon_pool = await get_current_dungeons()
            print(f"🔁 Dungeon pool loaded: {self.dungeon_pool}")
        except Exception as e:
            print(f"Using default dungeon pool due to error: {e}")
            pass  # Keep using CURRENT_DUNGEONS if API fails

    @app_commands.command(name="startdungeon", description="Start a Mythic+ group")
    @app_commands.describe(
        dungeon="Dungeon name",
        key_level="Key level (0-20)",
        your_role="Your role in the group",
        start_time="When to start (e.g., 14:30 or 'now'). Default is now."
    )
    async def startdungeon(
        self,
        interaction: discord.Interaction,
        dungeon: str,
        key_level: app_commands.Range[int, 0, 20],
        your_role: Role,
        start_time: str = "now"
    ):
        try:
            scheduled_time = parse_time(start_time)
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
            return

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
            "creator": interaction.user,  # Track who created the group
            "start_time": scheduled_time  # Store the start time
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
        view = GroupView(interaction.channel_id)
        
        # Create ping message for needed roles
        ping_message = self.create_role_ping_message(your_role)
        
        # Create start time message
        time_msg = "Starting now!" if start_time.lower() == "now" else f"Scheduled for: {scheduled_time.strftime('%H:%M')}"
        
        # Send and store message
        await interaction.response.send_message(
            f"{ping_message}\n🌀 Group started for **{dungeon}** at **+{key_level}**!\n⏰ {time_msg}",
            embed=status_embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        
        # Add group to active groups
        active_groups[interaction.channel_id] = group_info

    def create_role_ping_message(self, filled_role: Role) -> str:
        """Create a message that pings all needed roles except the one already filled."""
        needed_roles = []
        
        # Always include Tank and Healer if not filled
        if filled_role != Role.TANK:
            needed_roles.append(f"<@&{ROLE_IDS['tank']}>")
        if filled_role != Role.HEALER:
            needed_roles.append(f"<@&{ROLE_IDS['healer']}>")
            
        # Always include DPS role, even if creator is DPS (since we need 3)
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
        # Fast, case-insensitive filtering
        current_lower = current.lower()
        return [
            app_commands.Choice(name=dungeon, value=dungeon)
            for dungeon in self.dungeon_pool
            if current_lower in dungeon.lower()
        ][:25]

    def create_group_status(self, group):
        status = discord.Embed(
            title=f"{group['dungeon']} +{group['key_level']}",
            color=discord.Color.blue()
        )

        # Add start time as first field if it's not "now"
        if (group['start_time'] - datetime.now()).total_seconds() > 60:  # If more than 1 minute in the future
            time_str = group['start_time'].strftime('%H:%M')
            status.add_field(
                name="⏰ Start Time",
                value=f"**{time_str}**",
                inline=False
            )
        
        # Tank status
        tank_name = group['tank'].display_name if group['tank'] else "Not filled"
        tank_status = "✅" if group['tank'] else "❌"
        status.add_field(name=f"{ROLE_ICONS['tank']} Tank", value=f"{tank_status} {tank_name}", inline=False)
        
        # Healer status
        healer_name = group['healer'].display_name if group['healer'] else "Not filled"
        healer_status = "✅" if group['healer'] else "❌"
        status.add_field(name=f"{ROLE_ICONS['healer']} Healer", value=f"{healer_status} {healer_name}", inline=False)
        
        # DPS status
        dps_list = "\n".join([f"✅ {dps.display_name}" for dps in group['dps']])
        if not dps_list:
            dps_list = "❌ No DPS signed up"
        status.add_field(name=f"{ROLE_ICONS['dps']} DPS ({len(group['dps'])}/3)", value=dps_list, inline=False)
        
        # Add group creator
        status.set_footer(text=f"Created by {group['creator'].display_name}")
        
        return status

class GroupView(discord.ui.View):
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

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, custom_id="leave_group", emoji="🚪")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.leave_group(interaction)

    async def leave_group(self, interaction: discord.Interaction):
        group = active_groups.get(self.channel_id)

        if not group:
            await interaction.response.send_message("❌ No active group.", ephemeral=True)
            return

        user = interaction.user

        # Check if user is in the group
        if user not in group["players"]:
            await interaction.response.send_message("❌ You're not in this group.", ephemeral=True)
            return

        # Remove user from their role
        role_left = None
        if group["tank"] == user:
            group["tank"] = None
            role_left = "Tank"
        elif group["healer"] == user:
            group["healer"] = None
            role_left = "Healer"
        elif user in group["dps"]:
            group["dps"].remove(user)
            role_left = "DPS"

        # Remove from players set
        group["players"].remove(user)

        # Don't allow creator to leave unless they're the last person
        if user == group["creator"] and len(group["players"]) > 0:
            await interaction.response.send_message("❌ As the group creator, you can't leave while others are in the group. Use `/canceldungeon` instead.", ephemeral=True)
            return

        # If creator leaves and they're the last person, remove the group
        if user == group["creator"] and len(group["players"]) == 0:
            del active_groups[self.channel_id]
            await interaction.message.delete()
            await interaction.response.send_message("Group has been removed as the creator left.", ephemeral=True)
            return

        # Update the embed in the message
        status_embed = DungeonCommands.create_group_status(None, group)
        await interaction.message.edit(embed=status_embed)
        
        # Send confirmation to user
        await interaction.response.send_message(f"You have left the group (was {role_left}).", ephemeral=True)

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
            # Get time info for completion message
            time_info = ""
            if (group['start_time'] - datetime.now()).total_seconds() > 60:
                time_info = f"\n⏰ Starting at: {group['start_time'].strftime('%H:%M')}"

            await interaction.channel.send(
                f"✅ Group for **{group['dungeon']} +{group['key_level']}** is ready!{time_info}\n"
                "```\n"
                f"{ROLE_ICONS['tank']} Tank:   {group['tank'].display_name}\n"
                f"{ROLE_ICONS['healer']} Healer: {group['healer'].display_name}\n"
                f"{ROLE_ICONS['dps']} DPS:    {', '.join([dps.display_name for dps in group['dps']])}\n"
                "```"
            )
            del active_groups[self.channel_id]
