#==============================================================================
# Requirements
#==============================================================================

# Standard libs ---------------------------------------------------------------

import difflib
from typing import Optional, Union
from aiohttp import ClientSession

# Third party libs ------------------------------------------------------------

import discord
from discord.ext import commands
from LRFutils import logs

# Project modules -------------------------------------------------------------

import allay

#==============================================================================
# Plugin
#==============================================================================

class Wormhole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #==========================================================================
    # Commands
    #==========================================================================

    # Create ------------------------------------------------------------------

    @discord.app_commands.command(name="wormhole-create", description="Create a new wormhole that will connect several channels")
    async def create(self, interaction, name: str,  sync_threads:bool=True):

        if len(self.get_user_wormholes(interaction.user)) >= 5:
            await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.error.too-many-wormholes"))
            return

        # Create a new wormhole and get it's ID
        self.bot.db_query("INSERT INTO wormholes (name, sync_threads) VALUES (?, ?)", (name, sync_threads))
        id = self.bot.db_query("SELECT MAX(id) FROM wormholes")[0]['MAX(id)']

        # Add the creator as an admin
        self.bot.db_query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (id, interaction.user.id))

        # Confirm the creation
        await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.success.wormhole-created"))

    # List --------------------------------------------------------------------

    @discord.app_commands.command(name="wormhole-list", description="List all wormholes you are admin of")
    async def wh_list(self, interaction):
        await interaction.response.send_message(
            await self.bot._(interaction.user.id, "wormhole.list.user"),
            embeds=await self.wormhole_list_as_embeds(self.get_user_wormholes(interaction.user))
        )

    # Secret list (all existing wormholes)
    @discord.ext.commands.command(name="all-wormholes", description="List all wormholes managed by this bot")
    async def wh_full_list(self, ctx):
        embeds = await self.wormhole_list_as_embeds(self.get_wormholes())
        for i in range(0, len(embeds), 10):
            await ctx.send("All wormholes:" if i==0 else "", embeds=embeds[i:i+10])

    # Link --------------------------------------------------------------------

    # @discord.app_commands.command(name="wormhole-link", description="Link a channel to a wormhole")
    # async def link(self, interaction, wormhole_id:int=None, read:bool=True, write:bool=False, channel:discord.abc.GuildChannel=None):
    #     await interaction.response.send_message("Not implemented yet... 🚧")
    #     ... # TODO

    # Add admin ---------------------------------------------------------------

    @discord.app_commands.command(name="wormhole-admin-add", description="Add an admin to a wormhole")
    async def add_admin(self, interaction, user:discord.User, wormhole_id:int=None):

        # Wormhole selection if no ID is specified
        if wormhole_id is None:
            await interaction.response.send_message("Not implemented yet... 🚧 (you must specify the wormhole ID for now)")
            ... # TODO
            return

        # Check if the source user is admin of the wormhole
        if wormhole_id not in self.get_user_wormholes(interaction.user):
            await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.error.not-admin"))
            return
        
        # Check if the target user is already admin of the wormhole
        if user.id in [int(admin['user_id']) for admin in self.bot.db_query(f"SELECT user_id FROM wormhole_admins WHERE wormhole_id={wormhole_id}")]:
            await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.error.already-admin"))
            return
        
        # Check if the target user already have 5 wormholes
        if len(self.get_user_wormholes(user)) >= 5:
            await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.error.target-has-too-many-wormholes", user=user.display_name))
            return

        # Add the user as an admin
        self.bot.db_query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (wormhole_id, user.id))

        # Confirm the addition
        wormhole_name = self.bot.db_query(f"SELECT name FROM wormholes WHERE id={wormhole_id}")[0]['name']
        await interaction.response.send_message(await self.bot._(interaction.user.id, "wormhole.success.admin-added", user=user.mention, wormhole=wormhole_name))

    #==========================================================================
    # Utils
    #==========================================================================

    # Get wormholes -----------------------------------------------------------

    # Get all active wormholes
    def get_wormholes(self) -> list[int]:
        wormholes_id = [int(wh['id']) for wh in self.bot.db_query("SELECT id FROM wormholes")]
        return wormholes_id

    # Get wormhole ID the user is admin of
    def get_user_wormholes(self, user:discord.User) -> list[int]:
        wormholes_id = [int(wh['wormhole_id']) for wh in self.bot.db_query(f"SELECT wormhole_id FROM wormhole_admins WHERE user_id={user.id}")]
        return wormholes_id
    
    # Get wormhole ID matching the name
    def get_wormholes_by_name(self, name:str) -> list[int]:
        wormholes_id = [int(wh['id']) for wh in self.bot.db_query(f"SELECT id FROM wormholes WHERE name LIKE '{name}'")]
        return wormholes_id

    # Get wormhole ID matching the name & the user is admin of
    def get_user_wormholes_by_name(self, name:str, user:discord.User) -> list[int]:
        return list(set(self.get_user_wormholes(user) + self.get_wormholes_by_name(name, user)))

    # List wormholes as embeds -------------------------------------------------
    
    async def wormhole_list_as_embeds(self, wormholes_id:list[int]) -> list[discord.Embed]:
        list_embeds = []
        for wh_id in wormholes_id:

            # Get wormhole data
            wh = self.bot.db_query(f"SELECT * FROM wormholes WHERE id={wh_id}")[0]
            admins = self.bot.db_query(f"SELECT user_id FROM wormhole_admins WHERE wormhole_id={wh_id}")
            admin_names = ", ".join([self.bot.get_user(int(admin['user_id'])).mention for admin in admins])

            # Create embed
            embed = discord.Embed(title=wh['name'], description=f"Admins: {admin_names}")
            embed.set_footer(text=f"Id: {wh['id']} - Sync threads: {wh['sync_threads']}")

            # Add embed to list
            list_embeds.append(embed)

        return list_embeds