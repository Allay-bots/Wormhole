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
from .backend import Wormhole, WormholeLink, WormholeAdmin

#==============================================================================
# Plugin
#==============================================================================

class WormholeCog(commands.Cog):
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

    # Wormhole selector
    async def wormhole_autocomplete(self, interaction, current:str):
        possible_choices = []
        for wormhole in Wormhole.get_accessible_by(interaction.user):
            if current.lower() in str(wormhole).lower():
                possible_choices.append(discord.app_commands.Choice(name=str(wormhole), value=wormhole.id))
        return possible_choices

    # Admin action selector
    async def action_autocomplete(self, interaction, current:str):
        possible_choices = []
        for action in ["add", "remove"]:
            if current.lower() in action.lower():
                possible_choices.append(discord.app_commands.Choice(name=action, value=action))
        return possible_choices

    # What to list selector
    async def which_one_to_list_autocomplete(self, interaction, current:str):
        possible_choices = []
        for what in ["I'm admin of", "are linked to this channel", "are linked somewhere in this guild"]:
            if current.lower() in what.lower():
                possible_choices.append(discord.app_commands.Choice(name=what, value=what))
        return possible_choices
    
    # List wormholes as embeds ------------------------------------------------

    async def wormhole_list_as_embeds(self, wormholes:list[Wormhole]) -> list[discord.Embed]:
        list_embeds = []
        for wormhole in wormholes:
            admins = WormholeAdmin.get_from(wormhole)
            admin_names = ", ".join([self.bot.get_user(admin.user_id).mention for admin in admins])
            channels = ", ".join([self.bot.get_channel(link.channel_id).mention + " 👀" if link.can_read else "" + " ✍️" if link.can_write else "" for link in wormhole.links])

            # Create embed
            embed = discord.Embed(title=wormhole.name, description=f"Channels: {channels}\nAdmins: {admin_names}")
            sync_threads = "✅ Sync threads" if wormhole.sync_threads else "❌ Doesn't sync threads"
            embed.set_footer(text=f"Id: {wormhole.id} - {sync_threads}")

            # Add embed to list
            list_embeds.append(embed)
        return list_embeds

    #==========================================================================
    # Commands
    #==========================================================================

    # Create ------------------------------------------------------------------

    @wormhole.command(name="open", description="Create a new wormhole that will connect several channels")
    async def wh_open(self, interaction, name: str,  sync_threads:bool=True):

        if len(Wormhole.get_accessible_by(interaction.user)) >= 5:
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.open.reach-limit"))
            return

        wormhole_id = Wormhole.open(name, sync_threads)
        WormholeAdmin.add(wormhole_id, interaction.user.id)

        await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.open.success"))

    # List --------------------------------------------------------------------

    @wormhole.command(name="list", description="List all wormholes you are admin of")
    @discord.app_commands.autocomplete(which=which_one_to_list_autocomplete)
    async def wh_list(self, interaction, which:str):

        if which not in ["I'm admin of", "are linked to this channel", "are linked somewhere in this guild"]:
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.list.invalid-predicate"))
            return

        if which == "I'm admin of":
            wormholes = Wormhole.get_accessible_by(interaction.user)
            if len(wormholes) == 0:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.list.user-have-no-wormhole"))
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.user")
                embeds = await self.wormhole_list_as_embeds(wormholes)
                

        elif which == "are linked to this channel":
            wormholes = Wormhole.get_linked_to(interaction.channel)
            if len(wormholes) == 0:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.list.channel-have-no-wormhole"))
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.channel")
                embeds = await self.wormhole_list_as_embeds(wormholes)

        elif which == "are linked somewhere in this guild":
            wormholes = []
            for channel in interaction.guild.channels:
                wormholes += Wormhole.get_linked_to(channel)
            if len(wormholes) == 0:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.list.guild-have-no-wormhole"))
                return
            else:
                message = allay.I18N.tr(interaction, "wormhole.list.guild")
                embeds = await self.wormhole_list_as_embeds(Wormhole.set(wormholes))

        await interaction.response.send_message(message, embeds=embeds)


    # Secret list (all existing wormholes)
    @discord.ext.commands.command(name="wormholes", description="List all wormholes managed by this bot")
    async def wh_full_list(self, ctx):
        embeds = await self.wormhole_list_as_embeds(Wormhole.get_all_wormholes())
        for i in range(0, len(embeds), 10):
            await ctx.send("All wormholes:" if i==0 else "", embeds=embeds[i:i+10])

    # Link --------------------------------------------------------------------

    @wormhole.command(name="link", description="Link a channel to a wormhole")
    @discord.app_commands.autocomplete(wormhole=wormhole_autocomplete, action=action_autocomplete)
    async def link(self, interaction, action:str, wormhole:int, read:bool=True, write:bool=True, channel:discord.abc.GuildChannel=None):

        if channel is None:
            channel = interaction.channel

        wormhole = Wormhole.get_by_id(wormhole)

        # Apply routine for a given wormhole ID ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Check if the source user is admin of the wormhole
        if not Wormhole.is_in(wormhole, Wormhole.get_accessible_by(interaction.user)):
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.generic.not-admin"))
            return
        
        # Check if the user has the required permissions
        if not channel.permissions_for(interaction.user).manage_messages or not channel.permissions_for(interaction.user).read_messages:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.link.missing-permissions", channel=channel.mention))
                return
        
        if action == "add":

            # Check if the channel is already linked to the wormhole
            if channel.id in wormhole.linked_channels_id:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.link.add.already-linked", channel=channel.mention, wormhole=wormhole.name))
                return
        
            # Create the link
            WormholeLink.add(wormhole, channel.id, read, write)  

            # Confirm the addition
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.link.add.success", channel=channel.mention, wormhole=wormhole.name))
            
            
        if action == "remove":
            
            # Check if the channel is not linked to the wormhole
            if channel.id not in wormhole.linked_channels_id:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.link.remove.not-linked", channel=channel.mention, wormhole=wormhole.name))
                return
            
            # Remove the link
            WormholeLink.remove(wormhole, channel.id)

            # Confirm the removal
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.link.remove.success", channel=channel.mention, wormhole=wormhole.name))
    
    # Add admin ---------------------------------------------------------------

    @wormhole.command(name="admin", description="Add an admin to a wormhole")
    @discord.app_commands.autocomplete(wormhole=wormhole_autocomplete, action=action_autocomplete)
    async def add_admin(self, interaction, action:str, user:discord.User, wormhole:int):

        wormhole = Wormhole.get_by_id(wormhole)

        # Run checks ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # Check if the action is valid
        if action not in ["add", "remove"]:
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.invalid-action"))
            return

        # Check if the wormhole exist
        if wormhole is None:
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.generic.not-exist"))
            return

        # Check if the source user is admin of the wormhole
        if wormhole.id not in [wh.id for wh in Wormhole.get_accessible_by(interaction.user)]:
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.generic.not-admin"))
            return
        
        # Add ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if action == "add":

            # Check if the target user is already admin of the wormhole
            if user.id in [admin.user_id for admin in WormholeAdmin.get_from(wormhole)]:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.add.target-is-already-admin", user=user.display_name, wormhole=wormhole.name))
                return
        
            # Check if the target user already have 5 wormholes
            if len(Wormhole.get_accessible_by(user)) >= 5:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.add.target-has-too-many-wormholes", user=user.display_name))
                return
            
            # Applye
            WormholeAdmin.add(wormhole, user)
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.add.success", user=user.mention, wormhole=wormhole.name))

        # Remove ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        elif action == "remove":

            # Check if the target user is admin of the wormhole
            if user.id not in [admin.user_id for admin in WormholeAdmin.get_from(wormhole)]:
                await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.remove.target-is-not-admin", user=user.display_name))
                return

            # Apply
            WormholeAdmin.remove(wormhole, user)
            await interaction.response.send_message(allay.I18N.tr(interaction, "wormhole.admin.remove.success", user=user.mention, wormhole=wormhole.name))

    #==========================================================================
    # Events
    #==========================================================================

    # On message --------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message):

        # Check if the message is in a wormhole channel
        wormholes = Wormhole.get_linked_to(message.channel, filter_can_write=True)
        if len(wormholes) == 0:
            return
        
        webhook = await WormholeWebhook.get_in(message.channel)

        # Check if the message is from the wormhole webhook
        if message.author.id == webhook.id:
            return
        
        # Send the message to all linked channels
        for wormhole in wormholes:
            for link in wormhole.links:

                # Remove channels that can't read the new messages
                if not link.can_read:
                    continue

                # Remove the channel where the message was sent
                if link.channel_id == message.channel.id:
                    continue

                channel = self.bot.get_channel(link.channel_id)
                
                if channel is None:
                    WormholeLink.remove(wormhole, link.channel_id)
                    continue

                # Get the webhook
                webhook = await WormholeWebhook.get_in(channel)

                # Composing the miror message content
                content = message.content

                def crop_reference_content(content):
                    if content.startswith("**╭┄** 💬 [**"):
                        content = "\n".join(content.split("\n")[1:])
                    if len(content) > 1000:
                        content = content[:1000]
                    return content

                def reference_match(content1:str, content2:str) -> str:
                    return crop_reference_content(content1) == crop_reference_content(content2)
            
                # Get the reference in the destination channel
                async def get_miror_reference(channel: discord.abc.Messageable, message: discord.Message) -> discord.Message:
                    date = message.created_at

                    async for msg in channel.history(limit=10, after=date, oldest_first=True):
                        if reference_match(msg.content, message.content):
                            return msg
                    async for msg in channel.history(limit=10, before=date, oldest_first=False):
                        if reference_match(msg.content, message.content):
                            return msg
                    return None

                # Include the start of the message that was answered
                if message.reference is not None:
                    reference = await message.channel.fetch_message(message.reference.message_id)
                    if reference is not None:
                        miror_reference = await get_miror_reference(channel, reference)
                        if miror_reference is None:
                            miror_reference = reference

                        reference_content = crop_reference_content(miror_reference.content)
                        if len(reference_content) > 50:
                            reference_content = reference_content[:47] + "..."

                        content = f"**╭┄** 💬 [**{reference.author.display_name}**](<{miror_reference.jump_url}>) : {reference_content}\n" + message.content
                
                # Limit the message length
                if len(content) > 2000:
                    trunc = f" [[...]](<{message.jump_url}>)"
                    content = content[:2000-len(trunc)] + trunc

                # Send the miror message
                await webhook.send(content, username=message.author.display_name, avatar_url=message.author.avatar.url, allowed_mentions=discord.AllowedMentions.none(), files=[await attachment.to_file() for attachment in message.attachments], embeds=message.embeds)

class WormholeWebhook:
    def __init__(self, id:int|discord.Webhook, token:str, channel_id:int|discord.abc.GuildChannel):
        self.id = id.id if isinstance(id, discord.Webhook) else int(id)
        self.token = str(token)
        self.channel_id = channel_id.id if isinstance(channel_id, discord.abc.GuildChannel) else int(channel_id)

    # Get webhook if exist or create one --------------------------------------

    @staticmethod
    async def get_in(channel) -> Optional[discord.Webhook]:
        
        webhook = allay.Database.query(f"SELECT * FROM wormhole_webhooks WHERE channel_id={channel.id}")

        if len(webhook) > 1:
            logs.error(f"Channel {channel.name} ({channel.id}) have more than one wormhole webhook: {', '.join(w['id'] for w in webhook)}")

        if webhook:
            for w in await channel.guild.webhooks():
                if w.id == webhook[0]['id']:
                    webhook = w
                    break
        else:
            
            if not channel.permissions_for(channel.guild.me).manage_webhooks:
                try:
                    channel.send(allay.I18N.tr(channel, "wormhole.webhook.missing-permissions"))
                except discord.Forbidden:
                    logs.warning(f"Wormhole > Missing permissions to send message in {channel.name} ({channel.id}) of guild {channel.guild.name} ({channel.guild.id})")
                return None

            webhook = await channel.create_webhook(name="Allay Wormhole")
            allay.Database.query(f"INSERT INTO wormhole_webhooks (id, token, channel_id) VALUES (?,?,?)",(webhook.id, webhook.token, channel.id))

        return webhook