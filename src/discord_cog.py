#==============================================================================
# Requirements
#==============================================================================

# Standard libs ---------------------------------------------------------------

import difflib
from typing import Optional, Union
import asyncio

# Third party libs ------------------------------------------------------------

import discord
from discord.ext import commands
from LRFutils import logs

# Project modules -------------------------------------------------------------

import allay
from .wormhole_selector import WormholeSelectorView
from .backend import Wormhole, WhLink, WhAdmin
from . import discord_utils

#==============================================================================
# Plugin
#==============================================================================

class WhCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    wormhole = discord.app_commands.Group(
        name="wormhole",
        description="Connect several points between space and time",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True
    )

    #==========================================================================
    # Utils
    #==========================================================================

    # Autocompleters ----------------------------------------------------------

    async def wormhole_autocomplete(
            self,
            interaction:discord.Interaction,
            current:str
        ) -> list[discord.app_commands.Choice]:
        """--------------------------------------------------------------------
        Autocompleter for wormhole ID

        Parameters
        ----------
        - `interaction` : The interaction
        - `current` : The current value of the argument
        
        Returns
        -------
        - The list of possible choices
        --------------------------------------------------------------------"""

        possible_choices = []
        for wormhole in Wormhole.get_accessible_by(interaction.user):
            if current.lower() in str(wormhole).lower():
                possible_choices.append(
                    discord.app_commands.Choice(
                        name=str(wormhole),
                        value=wormhole.id
                    )
                )

        return possible_choices

    async def action_autocomplete(self, interaction, current:str):
        """--------------------------------------------------------------------
        Autocompleter for action

        Parameters
        ----------
        - `interaction` : The interaction
        - `current` : The current value of the argument
        
        Returns
        ------
        - The list of possible choices
        --------------------------------------------------------------------"""

        possible_choices = []
        for action in ["add", "remove"]:
            if current.lower() in action.lower():
                possible_choices.append(
                    discord.app_commands.Choice(
                        name=action,
                        value=action
                    )
                )
        
        return possible_choices

    async def which_one_to_list_autocomplete(
            self,
            interaction:discord.Interaction,
            current:str
        ) -> list[discord.app_commands.Choice]:
        """--------------------------------------------------------------------
        Autocompleter for "which" wormhole to list

        Parameters
        ----------
        - `interaction` : The interaction
        - `current` : The current value of the argument
        
        Returns
        -------
        - The list of possible choices
        --------------------------------------------------------------------"""

        possible_choices = []
        for what in [
                "I'm admin of",
                "are linked to this channel",
                "are linked somewhere in this guild"
            ]:
            if current.lower() in what.lower():
                possible_choices.append(
                    discord.app_commands.Choice(
                        name=what,
                        value=what
                    )
                )
        
        return possible_choices
    
    # List wormholes as embeds ------------------------------------------------

    async def wormhole_list_as_embeds(
            self,
            wormholes:list[Wormhole]
        ) -> list[discord.Embed]:
        """--------------------------------------------------------------------
        List wormholes as embeds

        Parameters
        ----------
        - `wormholes` : The list of wormholes to list

        Returns
        -------
        - The list of embeds
        --------------------------------------------------------------------"""

        list_embeds = []
        for wormhole in wormholes:
            admins = WhAdmin.get_from(wormhole)
            admin_names = ", ".join(
                [self.bot.get_user(admin.user_id).mention for admin in admins]
            )
            channels = ", ".join(
                [
                    self.bot.get_channel(link.channel_id).mention
                    + " 👀" if link.can_read else ""
                    + " ✍️" if link.can_write else ""
                    for link in wormhole.links
                ]
            )

            # Create embed
            embed = discord.Embed(
                title=wormhole.name,
                description=f"Channels: {channels}\nAdmins: {admin_names}"
            )
            if wormhole.sync_threads:
                sync_threads = "✅ Sync threads"
            else:
                sync_threads = "❌ Doesn't sync threads"
            embed.set_footer(text=f"Id: {wormhole.id} - {sync_threads}")

            # Add embed to list
            list_embeds.append(embed)
        
        return list_embeds

    #==========================================================================
    # Commands
    #==========================================================================

    # Create ------------------------------------------------------------------

    @wormhole.command(
        name="open",
        description="Create a new wormhole that will connect several channels"
    )
    async def wh_open(
            self,
            interaction:discord.Interaction,
            name: str,
            sync_threads:bool=True
        ) -> None:
        """--------------------------------------------------------------------
        Create a new wormhole that will connect several channels

        Parameters
        ----------
        - `name` : The name of the wormhole
        - `sync_threads` : If the threads should be synced
        --------------------------------------------------------------------"""

        if len(Wormhole.get_accessible_by(interaction.user)) >= 5:
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.open.reach-limit"
                )
            )
            return

        wormhole_id = Wormhole.open(name, sync_threads)
        WhAdmin.add(wormhole_id, interaction.user.id)

        await interaction.response.send_message(
            allay.I18N.tr(
                interaction,
                "wormhole.open.success"
            )
        )

    # List --------------------------------------------------------------------

    @wormhole.command(
        name="list",
        description="List all wormholes you are admin of"
    )
    @discord.app_commands.autocomplete(which=which_one_to_list_autocomplete)
    async def wh_list(
            self,
            interaction:discord.Interaction,
            which:str
        ) -> None:
        """--------------------------------------------------------------------
        List all wormholes you are admin of

        Parameters
        ----------
        - `interaction` : The interaction
        - `which` : Which wormholes to list
        --------------------------------------------------------------------"""

        if which not in [
                "I'm admin of",
                "are linked to this channel",
                "are linked somewhere in this guild"
            ]:
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction, "wormhole.list.invalid-predicate"
                )
            )
            return

        if which == "I'm admin of":
            wormholes = Wormhole.get_accessible_by(interaction.user)
            if len(wormholes) == 0:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction, "wormhole.list.user-have-no-wormhole"
                    )
                )
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.user")
                embeds = await self.wormhole_list_as_embeds(wormholes)
                

        elif which == "are linked to this channel":
            wormholes = Wormhole.get_linked_to(interaction.channel)
            if len(wormholes) == 0:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.list.channel-have-no-wormhole"
                    )
                )
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.channel")
                embeds = await self.wormhole_list_as_embeds(wormholes)

        elif which == "are linked somewhere in this guild":
            wormholes = []
            for channel in interaction.guild.channels:
                wormholes += Wormhole.get_linked_to(channel)
            if len(wormholes) == 0:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.list.guild-have-no-wormhole"
                    )
                )
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.guild")
                embeds = await self.wormhole_list_as_embeds(
                    Wormhole.set(wormholes)
                )

        await interaction.response.send_message(message, embeds=embeds)

    @discord.ext.commands.command(
        name="wormholes",
        description="List all wormholes managed by this bot"
    )
    async def wh_full_list(self, ctx:discord.ext.commands.Context) -> None:
        """--------------------------------------------------------------------
        Secret command to list all wormholes managed by this bot

        Parameters
        ----------
        - `ctx` : The discord context
        --------------------------------------------------------------------"""
        embeds = await self.wormhole_list_as_embeds(
            Wormhole.get_all_wormholes()
        )
        for i in range(0, len(embeds), 10):
            await ctx.send(
                "All wormholes:" if i==0 else "",
                embeds=embeds[i:i+10]
            )

    # Link --------------------------------------------------------------------

    @wormhole.command(name="link", description="Link a channel to a wormhole")
    @discord.app_commands.autocomplete(
        wormhole=wormhole_autocomplete,
        action=action_autocomplete
    )
    async def link(
            self,
            interaction:discord.Interaction,
            action:str,
            wormhole:int,
            read:bool=True,
            write:bool=True,
            channel:discord.abc.GuildChannel=None
        ) -> None:
        """--------------------------------------------------------------------
        Link a channel to a wormhole

        Parameters
        ----------
        - `interaction` : The interaction
        - `action` : The action to do
        - `wormhole` : The wormhole ID
        - `read` : If the channel should be able to read the wormhole
        - `write` : If the channel should be able to write in the wormhole
        - `channel` : The channel to link
        --------------------------------------------------------------------"""

        if channel is None:
            channel = interaction.channel

        wormhole = Wormhole.get_by_id(wormhole)

        # Apply routine for a given wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Check if the source user is admin of the wormhole
        if not Wormhole.is_in(
                wormhole,
                Wormhole.get_accessible_by(interaction.user)
            ):
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.generic.not-admin"
                )
            )
            return
        
        # Check if the user has the required permissions
        if not channel.permissions_for(interaction.user).manage_messages \
            or not channel.permissions_for(interaction.user).read_messages:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.link.missing-permissions",
                        channel=channel.mention
                    )
                )
                return
        
        if action == "add":

            # Check if the channel is already linked to the wormhole
            if channel.id in wormhole.linked_channels_id:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.link.add.already-linked",
                        channel=channel.mention,
                        wormhole=wormhole.name
                    )
                )
                return
        
            # Create the link
            WhLink.add(wormhole, channel.id, read, write)  

            # Confirm the addition
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.link.add.success",
                    channel=channel.mention,
                    wormhole=wormhole.name
                )
            )
            
            
        if action == "remove":
            
            # Check if the channel is not linked to the wormhole
            if channel.id not in wormhole.linked_channels_id:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.link.remove.not-linked",
                        channel=channel.mention,
                        wormhole=wormhole.name
                    )
                )
                return
            
            # Remove the link
            WhLink.remove(wormhole, channel.id)

            # Confirm the removal
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.link.remove.success",
                    channel=channel.mention,
                    wormhole=wormhole.name
                )
            )
    
    # Add admin ---------------------------------------------------------------

    @wormhole.command(name="admin", description="Add an admin to a wormhole")
    @discord.app_commands.autocomplete(
        wormhole=wormhole_autocomplete,
        action=action_autocomplete
    )
    async def add_admin(
            self,
            interaction,
            action:str,
            user:discord.User,
            wormhole:int
        ):
        """--------------------------------------------------------------------
        Add an admin to a wormhole

        Parameters
        ----------
        - `interaction` : The interaction
        - `action` : The action to do
        - `user` : The user to add
        - `wormhole` : The wormhole ID
        --------------------------------------------------------------------"""

        wormhole = Wormhole.get_by_id(wormhole)

        # Run checks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Check if the action is valid
        if action not in ["add", "remove"]:
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.admin.invalid-action"
                )
            )
            return

        # Check if the wormhole exist
        if wormhole is None:
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.generic.not-exist"
                )
            )
            return

        # Check if the source user is admin of the wormhole
        if wormhole.id not in [
                wh.id for wh in Wormhole.get_accessible_by(interaction.user)
            ]:
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.generic.not-admin"
                )
            )
            return
        
        # Add ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if action == "add":

            # Check if the target user is already admin of the wormhole
            if user.id in [
                    admin.user_id for admin in WhAdmin.get_from(wormhole)
                ]:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.admin.add.target-is-already-admin",
                        user=user.display_name,
                        wormhole=wormhole.name
                    )
                )
                return
        
            # Check if the target user already have 5 wormholes
            if len(Wormhole.get_accessible_by(user)) >= 5:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.admin.add.target-has-too-many-wormholes",
                        user=user.display_name
                    )
                )
                return
            
            # Applye
            WhAdmin.add(wormhole, user)
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.admin.add.success",
                    user=user.mention,
                    wormhole=wormhole.name
                )
            )

        # Remove ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        elif action == "remove":

            # Check if the target user is admin of the wormhole
            if user.id not in [
                    admin.user_id for admin in WhAdmin.get_from(wormhole)
                ]:
                await interaction.response.send_message(
                    allay.I18N.tr(
                        interaction,
                        "wormhole.admin.remove.target-is-not-admin",
                        user=user.display_name
                    )
                )
                return

            # Apply
            WhAdmin.remove(wormhole, user)
            await interaction.response.send_message(
                allay.I18N.tr(
                    interaction,
                    "wormhole.admin.remove.success",
                    user=user.mention,
                    wormhole=wormhole.name
                )
            )

    #==========================================================================
    # Events
    #==========================================================================

    # On message --------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """--------------------------------------------------------------------
        When a new message is sent, send it to all linked channels

        Parameters
        ----------
        - `message` : The message
        --------------------------------------------------------------------"""

        print("\n----------\n")
        logs.info(f"New message detected!")

        logs.info(f"Getting wormholes...")

        # Check if the message is in a wormhole channel
        wormholes = Wormhole.get_linked_to(
            message.channel,
            filter_can_write=True
        )
        if len(wormholes) == 0:
            logs.info(f"Message is not in a wormhole channel ⛔")
            return
        
        logs.info("Wormhole found ✅")
        logs.info("Getting associated webhook...")

        webhook = await discord_utils.WhWebhook.get_in(message.channel)

        # Check if the message is from the wormhole webhook
        if message.author.id == webhook.id:
            logs.info(f"Message is from the wormhole webhook ⛔")
            return
        
        logs.info(f"Message come from a human ✅")
        
        # Send the message to all linked channels
        for wormhole in wormholes:
            for link in wormhole.links:

                # Remove channels that can't read the new messages
                if not link.can_read:
                    continue

                # Remove the channel where the message was sent
                if link.channel_id == message.channel.id:
                    continue
                
                # If the channel is no longer accessible (or was deleted)
                # Then remove the link
                destination_channel = self.bot.get_channel(link.channel_id)
                if destination_channel is None:
                    link.remove()
                    continue

                # Send the miror message
                webhook = await discord_utils.WhWebhook.get_in(
                    destination_channel
                )
                content = await discord_utils.WhMessage\
                .compose_miror_content(
                    message,
                    channel=destination_channel
                )
                await webhook.send(
                    content,
                    username=message.author.display_name,
                    avatar_url=message.author.avatar.url,
                    allowed_mentions=discord.AllowedMentions.none(),
                    files=[
                        await attachment.to_file()
                        for attachment in message.attachments
                    ],
                    embeds=message.embeds)

    # On message deleted ------------------------------------------------------

    supression_cache = []

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """--------------------------------------------------------------------
        When a message is deleted, delete the miror message in all linked
        channels

        Parameters
        ----------
        - `message` : The message
        --------------------------------------------------------------------"""
                    
        print("Message deleted\n", message.content)
        
        # Check if the message is in a wormhole channel
        wormholes = Wormhole.get_linked_to(
            message.channel,
            filter_can_write=True
        )
        if len(wormholes) == 0:
            return
        
        # If the message is already in supression process, then ignore it
        message_hash = await discord_utils.WhMessage.get_hash(message) 
        if message_hash in WhCog.supression_cache:
            logs.info("Message is already in supression process ⛔")
            return
        
        # Add the message to the supression cache
        WhCog.supression_cache.append(message_hash)
        
        for wormhole in wormholes:
            for link in wormhole.links:
                
                # Ignore channels that can't see the wormhole activity
                if not link.can_read:
                    continue
                
                # If the channel is no longer accessible (or was deleted)
                # Then remove the link
                destination_channel = self.bot.get_channel(link.channel_id)
                if destination_channel is None:
                    link.remove()
                    continue

                # Ignore the channel where the message was deleted
                if destination_channel.id == message.channel.id:
                    continue
                
                # Get the miror message
                miror_message = await discord_utils.WhMessage\
                .get_miror_in(message, channel=destination_channel)
                
                # If the miror message is not accessible, then ignore it
                if miror_message is None:
                    continue
                
                # Delete the miror message
                await miror_message.delete()
        
        await asyncio.sleep(5)
        WhCog.supression_cache.remove(message_hash)

