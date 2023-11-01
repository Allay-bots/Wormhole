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
from .wormhole_selector import WormholeSelectorView

#==============================================================================
# Plugin
#==============================================================================

class Wormhole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    wormhole = discord.app_commands.Group(
        name="wormhole",
        description="Connect several points between space and time",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True
    )

    #==========================================================================
    # Commands
    #==========================================================================

    # Create ------------------------------------------------------------------

    @wormhole.command(name="create", description="Create a new wormhole that will connect several channels")
    async def create(self, interaction, name: str,  sync_threads:bool=True):

        if len(self.get_user_wormholes(interaction.user)) >= 5:
            await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.too-many-wormholes"))
            return

        # Create a new wormhole and get it's ID
        allay.Database.query("INSERT INTO wormholes (name, sync_threads) VALUES (?, ?)", (name, sync_threads))
        id = allay.Database.query("SELECT MAX(id) FROM wormholes")[0]['MAX(id)']

        # Add the creator as an admin
        allay.Database.query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (id, interaction.user.id))

        # Confirm the creation
        await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.success.wormhole-created"))

    # List --------------------------------------------------------------------

    @wormhole.command(name="list", description="List all wormholes you are admin of")
    async def wh_list(self, interaction):
        wormholes = self.get_user_wormholes(interaction.user)
        if len(wormholes) == 0:
            await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.no-wormhole"))
            return
        else:
            await interaction.response.send_message(
                await allay.I18N.tr(interaction, "wormhole.list.user"),
                embeds=await self.wormhole_list_as_embeds(wormholes)
            )

    # Secret list (all existing wormholes)
    @discord.ext.commands.command(name="wormholes", description="List all wormholes managed by this bot")
    async def wh_full_list(self, ctx):
        embeds = await self.wormhole_list_as_embeds(self.get_wormholes())
        for i in range(0, len(embeds), 10):
            await ctx.send("All wormholes:" if i==0 else "", embeds=embeds[i:i+10])

    # Link --------------------------------------------------------------------

    @wormhole.command(name="link", description="Link a channel to a wormhole")
    async def link(self, interaction, wormhole_id:int=None, read:bool=True, write:bool=False, channel:discord.abc.GuildChannel=None):

        if channel is None:
            channel = interaction.channel

        # Apply routine for a given wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        async def link_apply(interaction, wormhole_id:int):

            # Check if the source user is admin of the wormhole
            if wormhole_id not in self.get_user_wormholes(interaction.user):
                await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.not-admin"))
                return
            
            # Check if the channel is already linked to the wormhole
            if channel.id in [int(link['channel_id']) for link in allay.Database.query(f"SELECT channel_id FROM wormhole_links WHERE wormhole_id={wormhole_id}")]:
                await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.already-linked"))
                return
            
            # TODO: Check if the user can see & manage messages in the channel

            # Create the link
            allay.Database.query("INSERT INTO wormhole_links (wormhole_id, channel_id, can_read, can_write) VALUES (?,?,?,?)", (wormhole_id, channel.id, read, write))

            # Confirm the addition
            await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.success.channel-linked"))

        # Ask for the wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Wormhole selection if no ID is specified
        if wormhole_id is None:
            await interaction.response.send_message(view=WormholeSelectorView(
                wormholes_id = self.get_user_wormholes(interaction.user),
                callback = link_apply
            ))
        else:
            await self.link_apply(interaction, wormhole_id)

    # Add admin ---------------------------------------------------------------

    @wormhole.command(name="admin-add", description="Add an admin to a wormhole")
    async def add_admin(self, interaction, user:discord.User, wormhole_id:int=None):

        # Apply routine for a given wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        async def add_admin_apply(interaction, wormhole_id:int):

            # Check if the source user is admin of the wormhole
            if wormhole_id not in self.get_user_wormholes(interaction.user):
                await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.not-admin"))
                return
            
            # Check if the target user is already admin of the wormhole
            if user.id in [int(admin['user_id']) for admin in allay.Database.query(f"SELECT user_id FROM wormhole_admins WHERE wormhole_id={wormhole_id}")]:
                await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.already-admin", user=user.display_name))
                return
            
            # Check if the target user already have 5 wormholes
            if len(self.get_user_wormholes(user)) >= 5:
                await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.error.target-has-too-many-wormholes", user=user.display_name))
                return

            # Add the user as an admin
            allay.Database.query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (wormhole_id, user.id))

            # Confirm the addition
            wormhole_name = allay.Database.query(f"SELECT name FROM wormholes WHERE id={wormhole_id}")[0]['name']
            await interaction.response.send_message(await allay.I18N.tr(interaction, "wormhole.success.admin-added", user=user.mention, wormhole=wormhole_name))

        # Ask for the wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Wormhole selection if no ID is specified
        if wormhole_id is None:
            await interaction.response.send_message(view=WormholeSelectorView(
                wormholes_id = self.get_user_wormholes(interaction.user),
                callback = add_admin_apply
            ))
        else:
            await self.add_admin_apply(interaction, wormhole_id)

    #==========================================================================
    # Utils
    #==========================================================================

    # Get wormholes -----------------------------------------------------------

    # Get all active wormholes
    def get_wormholes(self) -> list[int]:
        wormholes_id = [int(wh['id']) for wh in allay.Database.query("SELECT id FROM wormholes")]
        return wormholes_id

    # Get wormhole ID the user is admin of
    def get_user_wormholes(self, user:discord.User) -> list[int]:
        wormholes_id = [int(wh['wormhole_id']) for wh in allay.Database.query(f"SELECT wormhole_id FROM wormhole_admins WHERE user_id={user.id}")]
        return wormholes_id
    
    # Get wormhole ID matching the name
    def get_wormholes_by_name(self, name:str) -> list[int]:
        wormholes_id = [int(wh['id']) for wh in allay.Database.query(f"SELECT id FROM wormholes WHERE name LIKE '{name}'")]
        return wormholes_id

    # Get wormhole ID matching the name & the user is admin of
    def get_user_wormholes_by_name(self, name:str, user:discord.User) -> list[int]:
        return list(set(self.get_user_wormholes(user) + self.get_wormholes_by_name(name, user)))

    # List wormholes as embeds -------------------------------------------------
    
    async def wormhole_list_as_embeds(self, wormholes_id:list[int]) -> list[discord.Embed]:
        list_embeds = []
        for wh_id in wormholes_id:

            # Get wormhole data
            wh = allay.Database.query(f"SELECT * FROM wormholes WHERE id={wh_id}")[0]
            admins = allay.Database.query(f"SELECT user_id FROM wormhole_admins WHERE wormhole_id={wh_id}")
            admin_names = ", ".join([self.bot.get_user(int(admin['user_id'])).mention for admin in admins])

            # Create embed
            embed = discord.Embed(title=wh['name'], description=f"Admins: {admin_names}")
            sync_threads = "✅ Sync threads" if wh['sync_threads'] else "❌ Doesn't sync threads"
            embed.set_footer(text=f"Id: {wh['id']} - {sync_threads}")

            # Add embed to list
            list_embeds.append(embed)

        return list_embeds

    # Get webhook if exist or create one --------------------------------------

    async def get_webhook(self, channel) -> Optional[discord.Webhook]:
        
        webhook = allay.Database.query(f"SELECT * FROM wormhole_webhooks WHERE channel_id={channel.id}")

        if len(webhook) > 1:
            logs.error(f"Channel {channel.name} ({channel.id}) have more than one wormhole webhook: {', '.join(w['id'] for w in webhook)}")

        if webhook:
            for w in await channel.guild.webhooks():
                if w.id == webhook[0]['id']:
                    webhook = w
                    break
        else:
            # TODO: Check if the bot have the permission to create a webhook
            webhook = await channel.create_webhook(name="Allay Wormhole")
            allay.Database.query(f"INSERT INTO wormhole_webhooks (id, token, channel_id) VALUES (?,?,?)",(webhook.id, webhook.token, channel.id))

        return webhook