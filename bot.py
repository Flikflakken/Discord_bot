import discord
from discord.ext import commands
from handlers import DungeonCommands, RoleButtons
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))  # Convert to int since env vars are strings

if not DISCORD_TOKEN or not GUILD_ID:
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Set up required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        try:
            print("Adding cogs...")
            await self.add_cog(DungeonCommands(self, GUILD_ID))
            
            # Basic test command
            @self.tree.command(description="Test if the bot is working", guild=discord.Object(id=GUILD_ID))
            async def ping(interaction: discord.Interaction):
                await interaction.response.send_message("Pong! 🏓")
            
            # Add persistent view for buttons
            self.add_view(RoleButtons(None))
            
            # Register commands for the specific guild
            print("Syncing commands...")
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Commands synced successfully!")
        except Exception as e:
            print(f"Error during setup: {e}")
            traceback.print_exc()

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}!")
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"Connected to guild: {guild.name}")
    print(f"Bot is in {len(bot.guilds)} guilds")
    print(f"Command list: {[cmd.name for cmd in bot.tree.get_commands()]}")

@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Command not found.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {str(error)}", ephemeral=True)
        print(f"Command error: {error}")
        traceback.print_exc()

bot.run(DISCORD_TOKEN)
