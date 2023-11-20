import discord
from typing import Optional
from LRFutils import logs
import allay

#==============================================================================
# Webhook
#==============================================================================

class WhWebhook:

    def __init__(
            self,
            id:int|discord.Webhook,
            token:str,
            channel_id:int|discord.abc.GuildChannel
        ):
        self.id = id.id if isinstance(id, discord.Webhook) else int(id)
        self.token = str(token)

        if isinstance(channel_id, discord.abc.GuildChannel):
            self.channel_id = channel_id.id
        else:
            self.channel_id = int(channel_id)

    # Get webhook if exist or create one --------------------------------------

    @staticmethod
    async def get_in(channel) -> Optional[discord.Webhook]:
        """--------------------------------------------------------------------
        Get the wormhole webhook in a specific channel.
        If the webhook does not exist, create it.
        
        Parameters
        ----------
        - `channel` : The channel where the webhook should be.
            
        Returns
        -------
        - The wormhole webhook.
        --------------------------------------------------------------------"""
        
        webhook = allay.Database.query(
            f"SELECT * FROM wormhole_webhooks WHERE channel_id={channel.id}"
        )

        if len(webhook) > 1:
            logs.error(
                f"Channel {channel.name} ({channel.id}) "\
                + "have more than one wormhole webhook: "\
                + ', '.join(w['id'] for w in webhook)
            )

        if webhook:
            for w in await channel.guild.webhooks():
                if w.id == webhook[0]['id']:
                    webhook = w
                    break
        else:
            
            if not channel.permissions_for(channel.guild.me).manage_webhooks:
                try:
                    channel.send(
                        allay.I18N.tr(
                            channel,
                            "wormhole.webhook.missing-permissions"
                        )
                    )
                except discord.Forbidden:
                    logs.warning(
                        "Wormhole > Missing permissions to send message in "\
                        + f"{channel.name} ({channel.id}) "\
                        + f"of guild {channel.guild.name} "\
                        + f"({channel.guild.id})")
                return None

            webhook = await channel.create_webhook(name="Allay Wormhole")
            allay.Database.query(
                f"INSERT INTO wormhole_webhooks "\
                + "(id, token, channel_id) VALUES (?,?,?)",
                (webhook.id, webhook.token, channel.id)
            )

        return webhook

    @staticmethod
    def all():
        return [
            WhWebhook(**data)
            for data in allay.Database.query(
                f"SELECT * FROM wormhole_webhooks"
            )
        ]

#==============================================================================
# Message
#==============================================================================

class WhMessage():

    reference_prefix = "**╭** 💬 [**"
    trunc_prefix = "[...](<https://discord.com/channels/"
    max_content_size = 1500

    async def get_hash(message):
        
        # Check if it is an original message -> keep the content
        webhook = await WhWebhook.get_in(message.channel)
        if message.author.id != webhook.id:
            content = message.content
            logs.info(f"Get original message: {content}")
        # Or a miror message -> extract the content
        else:
            content = WhMessage.extract_content_from_miror(
                message.content
            )
            logs.info(f"Get miror message: {content}")
        return content

    async def get_reference(message):
        # Check if it is an original message -> keep the content
        if message.author.id != await WhWebhook.get_in(message.channel):
            return message.reference
        # Or a miror message -> extract the content
        else:
            return WhMessage.extract_reference_from_miror(
                message.content
            )


    # Get miror message in a specific channel ---------------------------------

    async def get_miror_in(
            message:discord.Message,
            channel:discord.abc.GuildChannel
        ) -> Optional[discord.Message]:

        date = message.created_at

        logs.info(f"Searching for miror message in {channel.name}...")

        async for msg in channel.history(
                limit=5,
                after=date,
                oldest_first=True
            ):
            if await WhMessage.equal(message, msg):
                logs.info(f"Found miror message ✅")
                return msg
        logs.info(
            "Not found after the original message date, "\
            + "may be it is before..."
        )
        async for msg in channel.history(
                limit=5,
                before=date,
                oldest_first=False
            ):
            if await WhMessage.equal(message, msg):
                logs.info(f"Found miror message ✅")
                return msg
        return None
    
    # Compare two wormhole messages -------------------------------------------

    async def equal(msg1:discord.Message, msg2:discord.Message) -> bool:
        c1 = await WhMessage.get_hash(msg1) 
        c2 = await WhMessage.get_hash(msg2)
        logs.info(f"Comparing\n{c1.__repr__()}\nand\n{c2.__repr__()}")
        return c1 == c2
    
    # Compose the reference preview -------------------------------------------
    
    async def compose_reference_preview(
            message:discord.Message, 
            channel:discord.abc.GuildChannel=None
        ) -> str:

        reference = await WhMessage.get_reference(message)

        # Include the reference preview
        if reference is not None:
            
            logs.info("Reference available ✅")   
            
            # Get original reference
            reference_message = await message.channel.fetch_message(
                reference.message_id
            )

            # If the reference is is not accessible, then ignore it
            # otherwise, try to get the miror reference
            if reference_message is not None:

                logs.info("Original reference found ✅")
                logs.info("Getting the miror one...")   
                
                # Get miror reference
                miror_reference_message = await WhMessage.get_miror_in(
                    reference_message, channel
                )

                # If the miror reference is not accessible,
                # then use the original reference
                if miror_reference_message is None:
                    logs.info("Miror reference not found ❌") 
                    miror_reference_message = reference_message
                else:
                    logs.info("Miror reference found ✅") 

                # Crop the content
                # (if the refence also have a reference or if it is too long)
                reference_content = miror_reference_message.content
                if len(reference_content) > 50:
                    reference_content = reference_content[:47] + "..."

                logs.info("Composing reference preview...")

                # Add the croped reference to the miror message
                reference_preview = (
                    WhMessage.reference_prefix
                    + reference_message.author.display_name
                    + "**](<"
                    + miror_reference_message.jump_url
                    + ">) : "
                    + await WhMessage.get_hash(miror_reference_message)
                    + "\n"
                )

                logs.info(f"Reference preview: {reference_preview}")

                return reference_preview
            
            logs.info("Original reference not found ❌") 
        else:
            logs.info("No reference")
        
        return ""
    
    # Truncate the content ----------------------------------------------------

    async def truncated_content(
            message:discord.Message,
            channel:discord.abc.GuildChannel=None
        ) -> str:
        if len(message.content) > 2000:
            logs.info("Truncating message")
            trunc = f" [[...]](<{message.jump_url}>)"
            return message.content[:2000-len(trunc)] + trunc
        else:
            logs.info("No truncation")
        return message.content
    
    # Compose a miror message -------------------------------------------------
    
    async def compose_miror_content(
            message:discord.Message,
            channel:discord.abc.GuildChannel=None
        ) -> str:
        logs.info("Start composing miror message...")

        ref = await WhMessage.compose_reference_preview(message, channel)
        content = await WhMessage.truncated_content(message, channel)
        return ref + content

    @staticmethod
    def extract_content_from_miror(content):
        # Remove reference preview
        if content.startswith(WhMessage.reference_prefix):
            content = "\n".join(content.split("\n")[1:])
        # Remove truncation info
        if content.endswith(">)"):
            splitted_content = content.split(WhMessage.trunc_prefix)
            if len(splitted_content) > 1:
                content = WhMessage.trunc_prefix.join(
                    splitted_content[:-1]
                )
        return content
    
    @staticmethod
    def extract_reference_from_miror(
            content:str
        ) -> Optional[discord.MessageReference]:

        if content.startswith(WhMessage.reference_prefix):
            ref = content.split("\n")[0]
            ref = ref.split("](<")[1]
            ref = ref.split(">)")[0]
            ref_id = ref.split("/")[-1]

            reference = discord.abc.Messageable.fetch_message(ref_id)

            return discord.MessageReference(
                message_id=reference.id,
                channel_id=reference.channel.id,
                guild_id=reference.guild.id if reference.guild else None)
    
        return None

