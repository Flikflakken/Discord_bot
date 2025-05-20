# WoW M+ Group Finder Discord Bot

A Discord bot that helps World of Warcraft players create and manage Mythic+ dungeon groups. Players can easily create groups, sign up for roles, and get notifications when the group is complete.

## Features

- 🎯 Create M+ dungeon groups with `/startdungeon`
- 📝 Autocomplete current season dungeon names
- 🎮 Interactive role buttons (Tank, Healer, DPS)
- 👥 Real-time group status updates
- ✨ Role icons using WoW-style emojis
- 🚫 Prevent duplicate role assignments
- ❌ Cancel groups with `/canceldungeon`

## Setup

1. **Create a Discord Bot**
   1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
   2. Create a "New Application"
   3. Go to the "Bot" section
   4. Click "Add Bot"
   5. Enable these Privileged Gateway Intents:
      - Message Content Intent
      - Server Members Intent

2. **Install Dependencies**
   ```bash
   # Create a virtual environment (recommended)
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Unix/macOS:
   source venv/bin/activate
   
   # Install requirements
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   1. Copy `.env.example` to `.env`
   2. Fill in your Discord bot token and server ID
   3. Add your Blizzard API credentials if you have them

4. **Invite the Bot**
   1. Go to OAuth2 > URL Generator in Discord Developer Portal
   2. Select these scopes:
      - `bot`
      - `applications.commands`
   3. Select these bot permissions:
      - Read Messages/View Channels
      - Send Messages
      - Use Slash Commands
   4. Use the generated URL to invite the bot to your server

5. **Run the Bot**
   ```bash
   python bot.py
   ```

## Usage

### Creating a Group
```
/startdungeon [dungeon] [key level] [your role]
```
- `dungeon`: Autocompletes with current season dungeons
- `key level`: Level of the Mythic+ key (0-20)
- `your role`: Your role in the group (Tank/Healer/DPS)

### Joining a Group
Click the role buttons to join as:
- 🛡️ Tank (1 slot)
- ❇️ Healer (1 slot)
- ⚔️ DPS (3 slots)

### Canceling a Group
```
/canceldungeon
```
Only the group creator or server administrators can cancel a group.

## Group Status Display

The bot shows:
- Dungeon name and key level
- Filled/unfilled roles
- Player names for each role
- DPS count (x/3)
- Group creator

When the group is full (1 Tank, 1 Healer, 3 DPS), the bot sends a completion message and automatically removes the group.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
