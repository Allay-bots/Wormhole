
#==============================================================================
# Requirements
#==============================================================================

# Standard libs ---------------------------------------------------------------

# Thrid party libs ------------------------------------------------------------

import discord
from discord.ext import commands
from LRFutils import logs

# Project modules -------------------------------------------------------------

import allay
from .src.discord_cog import *

#==============================================================================
# Plugin
#==============================================================================

# Infos -----------------------------------------------------------------------

version = "0.0.1"
icon = "🌀"
name = "Wormhole"

# Cog -------------------------------------------------------------------------

async def setup(bot:allay.Bot):
    logs.info(f"Loading {icon} {name} v{version}...")
    await bot.add_cog(WhCog(bot), icon=icon, display_name=name)
