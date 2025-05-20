# blizzard_api.py
import aiohttp
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Blizzard API credentials from environment variables
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing Blizzard API credentials. Please check your .env file.")

# Current Season 2 dungeons for The War Within (pre-sorted)
CURRENT_DUNGEONS = sorted([
    "Operation: Floodgate",
    "Cinderbrew Meadery",
    "Darkflame Cleft",
    "The Rookery",
    "Priory of the Sacred Flame",
    "The MOTHERLODE!!",
    "Theater of Pain",
    "Operation: Mechagon: Workshop"
])

async def get_access_token():
    url = "https://oauth.battle.net/token"
    data = {"grant_type": "client_credentials"}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, auth=aiohttp.BasicAuth(CLIENT_ID, CLIENT_SECRET)) as resp:
            result = await resp.json()
            return result["access_token"]

async def get_current_dungeons():
    try:
        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"📜 Current dungeon pool: {json.dumps(CURRENT_DUNGEONS, indent=2)}")
        return CURRENT_DUNGEONS

    except Exception as e:
        print(f"❌ Error fetching dungeons: {e}")
        # Return pre-sorted list as fallback
        return CURRENT_DUNGEONS
