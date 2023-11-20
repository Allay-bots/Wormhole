from typing import Optional
import discord
from LRFutils import logs
import allay

class Wormhole:

    def __init__(self, id:int, name:str, sync_threads:bool):
        self.id = int(id)
        self.name = str(name)
        self.sync_threads = bool(sync_threads)

    @staticmethod
    def open(name:str, sync_threads:bool=True) -> int:
        """--------------------------------------------------------------------
        Open a new wormhole (add it to the database) and return its ID
        
        Parameters
        ----------
        - `name` : The name of the wormhole
        - `sync_threads` : Whether or not the wormhole should sync threads
        
        Returns
        -------
        - The ID of the newly created wormhole
        --------------------------------------------------------------------"""

        wormhole_id = allay.Database.query(
            f"INSERT INTO wormholes (name, sync_threads) VALUES (?,?)",
            (name, sync_threads)
        ) 

        return Wormhole(wormhole_id, name, sync_threads)
    
    @staticmethod
    def all():
        """--------------------------------------------------------------------
        Return a list of all wormholes in the database
        
        Returns
        -------
        - A list of all wormholes in the database
        --------------------------------------------------------------------"""

        return [
            Wormhole(**data) for data in allay.Database.query(
                f"SELECT * FROM wormholes"
            )
        ]

    #==========================================================================
    # Getters
    #==========================================================================

    @staticmethod
    def get_by_id(id) -> Optional["Wormhole"]:
        """--------------------------------------------------------------------
        Return a wormhole by its ID
        
        Parameters
        ----------
        - `id` : The ID of the wormhole
        
        Returns
        -------
        - The wormhole with the given ID, or None if it doesn't exist
        --------------------------------------------------------------------"""

        for wormhole in Wormhole.all():
            if wormhole.id == id:
                return wormhole
            
        return None

    @staticmethod
    def get_accessible_by(user:discord.User) -> list["Wormhole"]:
        """--------------------------------------------------------------------
        Return a list of all wormholes the user is admin of
        
        Parameters
        ----------
        - `user` : The user to check
        
        Returns
        -------
        - A list of all wormholes the user is admin of
        --------------------------------------------------------------------"""

        wormholes = []
        for admin in WhAdmin.all():
            if admin.user_id == user.id:
                wormholes.append(Wormhole.get_by_id(admin.wormhole_id))

        return wormholes

    # Get wormholes linked to a specific channel
    @staticmethod
    def get_linked_to(
            channel:discord.abc.GuildChannel,
            filter_can_read=False,
            filter_can_write=False
        ) -> list["Wormhole"]:
        """--------------------------------------------------------------------
        Return a list of all wormholes linked to a specific channel
        
        Parameters
        ----------
        - `channel` : The channel to check
        - `filter_can_read` : Whether or not to filter the wormholes to only
        return the ones the bot can read
        - `filter_can_write` : Whether or not to filter the wormholes to only
        return the ones the bot can write
        
        Returns
        -------
        - A list of all wormholes linked to the channel
        --------------------------------------------------------------------"""

        wormholes = []
        for link in WhLink.all():

            if link.channel_id != channel.id:
                continue

            wormhole = Wormhole.get_by_id(link.wormhole_id)
            if wormhole:
                if (
                    not filter_can_read
                    or (filter_can_read and link.can_read)
                    ) and (
                    not filter_can_write
                    or (filter_can_write and link.can_write)
                ):
                    wormholes.append(wormhole)

        return wormholes

    @staticmethod
    def get_linked_in(guild:discord.Guild) -> list["Wormhole"]:
        """--------------------------------------------------------------------
        Return a list of all wormholes linked in a specific guild
        
        Parameters
        ----------
        - `guild` : The guild to check
        
        Returns
        -------
        - A list of all wormholes linked in the guild
        --------------------------------------------------------------------"""

        wormholes = []
        for link in WhLink.all():
            if guild.get_channel(link.channel_id):
                wormhole = Wormhole.get_by_id(link.wormhole_id)
                if wormhole:
                    wormholes.append(wormhole)

        return wormholes
    
    #==========================================================================
    # Others
    #==========================================================================

    @property
    def links(self) -> list["WhLink"]:
        """--------------------------------------------------------------------
        Return a list of all links of the wormhole
        
        Returns
        -------
        - A list of all links of the wormhole
        --------------------------------------------------------------------"""

        return WhLink.get_from(self)

    @property
    def linked_channels_id(self) -> list[int]:
        """--------------------------------------------------------------------
        Return a list of all channels linked to the wormhole
        
        Returns
        -------
        - A list of all channels linked to the wormhole
        --------------------------------------------------------------------"""

        channels_id = []
        for link in self.links:
            channels_id.append(link.channel_id)

        return channels_id
    
    @property
    def reading_channels_id(self):
        """--------------------------------------------------------------------
        Return a list of all channels that can read in the wormhole
        
        Returns
        -------
        - A list of all channels that can read in the wormhole
        --------------------------------------------------------------------"""

        channels_id = []
        for link in self.links:
            if link.can_read:
                channels_id.append(link.channel_id)

        return channels_id
    
    @property
    def writing_channels_id(self):
        """--------------------------------------------------------------------
        Return a list of all channels that can write in the wormhole
        
        Returns
        -------
        - A list of all channels that can write in the wormhole
        --------------------------------------------------------------------"""

        channels_id = []
        for link in self.links:
            if self.id and link.can_write:
                channels_id.append(link.channel_id)

        return channels_id

    def __str__(self) -> str:
        """--------------------------------------------------------------------
        Return a string representation of the wormhole
        
        Returns
        -------
        - A string representation of the wormhole for display purpose
        --------------------------------------------------------------------"""

        return self.name + f" (id:{self.id})"

    def __repr__(self) -> str:
        """--------------------------------------------------------------------
        Return a string representation of the wormhole
        
        Returns
        -------
        - A string representation of the wormhole for debugging purpose
        --------------------------------------------------------------------"""

        return f"<Wormhole id:{self.id} "\
            + "name:{self.name} "\
            + "sync_threads:{self.sync_threads}>"

class WhLink:

    def __init__(
            self,
            wormhole_id:int|Wormhole,
            channel_id:int|discord.abc.GuildChannel,
            can_read:bool,
            can_write:bool,
            webhook_name:str=None,
            webhook_avatar:str=None
        ):
        """--------------------------------------------------------------------
        Create a new link between a wormhole and a channel
        
        Parameters
        ----------
        - `wormhole_id` : The ID of the wormhole to link
        - `channel_id` : The ID of the channel to link
        - `can_read` : Whether or not the channel can read in the wormhole
        - `can_write` : Whether or not the channel can write in the wormhole
        - `webhook_name` : The name of the webhook to use for the channel
        - `webhook_avatar` : The avatar of the webhook to use for the channel
        --------------------------------------------------------------------"""

        if isinstance(wormhole_id, Wormhole):
            wormhole_id = wormhole_id.id
        else:
            wormhole_id = int(wormhole_id)

        if isinstance(channel_id, discord.abc.GuildChannel):
            channel_id = channel_id.id
        else:
            channel_id = int(channel_id)

        self.can_read = bool(can_read)
        self.can_write = bool(can_write)
        self.webhook_name = str(webhook_name)
        self.webhook_avatar = str(webhook_avatar)

    @staticmethod
    def add(
            wormhole:int|Wormhole,
            channel:int|discord.abc.GuildChannel,
            read:bool=True,
            write:bool=False
        ) -> "WhLink":
        """--------------------------------------------------------------------
        Create a new link between a wormhole and a channel
        
        Parameters
        ----------
        - `wormhole` : The wormhole to link
        - `channel` : The channel to link
        - `read` : Whether or not the channel can read in the wormhole
        - `write` : Whether or not the channel can write in the wormhole
        
        Returns
        -------
        - The newly created link
        --------------------------------------------------------------------"""

        # Check if the link already exist
        for link in WhLink.all():
            if link.wormhole_id == wormhole and link.channel_id == channel:
                return link
        
        # If not, create it
        if isinstance(wormhole, Wormhole):
            wormhole = wormhole.id
        if isinstance(channel, discord.abc.GuildChannel):
            channel = channel.id

        query = "INSERT INTO wormhole_links "\
            + "(wormhole_id, channel_id, can_read, can_write) VALUES (?,?,?,?)"
        allay.Database.query(query, (wormhole, channel, read, write))

        link = WhLink(wormhole, channel, read, write)
        WhLink.all().append(link)

        return link

    def remove(self):
        allay.Database.query(
            f"DELETE FROM wormhole_links WHERE "\
                + "wormhole_id={self.wormhole_id} "\
                + "AND channel_id={self.channel_id}"
            )
        if self in WhLink.all():
            WhLink.all().remove(self)
        del self

    @staticmethod
    def all() -> list["WhLink"]:
        """--------------------------------------------------------------------
        Return a list of all links in the database
        
        Returns
        -------
        - A list of all links in the database
        --------------------------------------------------------------------"""

        return [
            WhLink(**data) for data in allay.Database.query(
                f"SELECT * FROM wormhole_links"
            )
        ]

    #==========================================================================
    # Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WhLink"]:
        """--------------------------------------------------------------------
        Return a list of all links of a wormhole
        
        Parameters
        ----------
        - `wormhole` : The wormhole to check
        
        Returns
        -------
        - A list of all links of the wormhole
        --------------------------------------------------------------------"""

        links = []
        for link in WhLink.all():
            if link.wormhole_id == wormhole.id:
                links.append(link)

        return links

class WhAdmin:

    def __init__(self, user_id:int|discord.abc.User, wormhole_id:int|Wormhole):
        """--------------------------------------------------------------------
        Create a virtual wormhole admin (not stored in the database)
        
        Parameters
        ----------
        - `user_id` : The ID of the user to make admin
        - `wormhole_id` : The ID of the wormhole to make admin of
        --------------------------------------------------------------------"""

        if isinstance(wormhole_id, Wormhole):
            wormhole_id = wormhole_id.id
        else:
            wormhole_id = int(wormhole_id)

        if isinstance(user_id, discord.abc.User):
            user_id = user_id.id
        else:
            user_id = int(user_id)

    @staticmethod
    def add(
            wormhole_id:int|Wormhole,
            user_id:int|discord.abc.User
        ) -> "WhAdmin":
        """--------------------------------------------------------------------
        Create a new wormhole admin (stored in the database)
        
        Parameters
        ----------
        - `wormhole_id` : The ID of the wormhole to make admin of
        - `user_id` : The ID of the user to make admin
        
        Returns
        -------
        - The newly created admin
        --------------------------------------------------------------------"""

        # Check if the admin already exist
        for admin in WhAdmin.all():
            if admin.wormhole_id == wormhole_id and admin.user_id == user_id:
                return admin
        
        # If not, create it
        if isinstance(user_id, discord.abc.User):
            user_id = user_id.id
        if isinstance(wormhole_id, Wormhole):
            wormhole_id = wormhole_id.id

        query = "INSERT INTO wormhole_admins "\
            + "(wormhole_id, user_id) VALUES (?,?)"
        allay.Database.query(query, (wormhole_id, user_id))

        return WhAdmin(user_id, wormhole_id)   
    
    @staticmethod
    def all():
        """--------------------------------------------------------------------
        Return a list of all wormhole admins in the database
        
        Returns
        -------
        - A list of all wormhole admins in the database
        --------------------------------------------------------------------"""

        return [
            WhAdmin(**data) for data in allay.Database.query(
                f"SELECT * FROM wormhole_admins"
            )
        ]

    #==========================================================================
    # Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WhAdmin"]:
        """--------------------------------------------------------------------
        Return a list of all admins of a wormhole
        
        Parameters
        ----------
        - `wormhole` : The wormhole to check
        
        Returns
        -------
        - A list of all admins of the wormhole
        --------------------------------------------------------------------"""

        admins = []
        for admin in WhAdmin.all():
            if admin.wormhole_id == wormhole.id:
                admins.append(admin)

        return admins

    #==========================================================================
    # Others
    #==========================================================================

    def __str__(self):
        """--------------------------------------------------------------------
        Return a string representation of an admin for display purpose
        
        Returns
        -------
        - A string representation of the wormhole admin for display purpose
        --------------------------------------------------------------------"""
        
        return f"{self.user_id} (Admin of wormhole {self.wormhole_id})"

    def __repr__(self):
        """--------------------------------------------------------------------
        Return a string representation of an admin for debugging purpose
        
        Returns
        -------
        - A string representation of the wormhole admin for debugging purpose
        --------------------------------------------------------------------"""

        return f"<WhAdmin "\
            + "user_id:{self.user_id} "\
            + "wormhole_id:{self.wormhole_id}>"