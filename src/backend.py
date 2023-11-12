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
        wormhole_id = allay.Database.query(f"INSERT INTO wormholes (name, sync_threads) VALUES (?,?)", (name, sync_threads)) 
        return Wormhole(wormhole_id, name, sync_threads)
    
    @staticmethod
    def all():
        return [Wormhole(**data) for data in allay.Database.query(f"SELECT * FROM wormholes")]

    #==========================================================================
    # Getters
    #==========================================================================

    # Get wormhole by ID
    @staticmethod
    def get_by_id(id) -> Optional["Wormhole"]:
        for wormhole in Wormhole.all():
            if wormhole.id == id:
                return wormhole
        return None

    # Get wormholes the user is admin of
    @staticmethod
    def get_accessible_by(user:discord.User) -> list["Wormhole"]:
        wormholes = []
        for admin in WormholeAdmin.all():
            if admin.user_id == user.id:
                wormholes.append(Wormhole.get_by_id(admin.wormhole_id))
        return wormholes

    # Get wormholes linked to a specific channel
    @staticmethod
    def get_linked_to(channel:discord.abc.GuildChannel, filter_can_read=False, filter_can_write=False) -> list["Wormhole"]:
        wormholes = []
        for link in WormholeLink.all():
            if link.channel_id == channel.id:
                wormhole = Wormhole.get_by_id(link.wormhole_id)
                if wormhole:
                    if (not filter_can_read or (filter_can_read and link.can_read)) and (not filter_can_write or (filter_can_write and link.can_write)):
                        wormholes.append(wormhole)
        return wormholes

    # Get wormholes linked somewhere in the guild
    @staticmethod
    def get_linked_in(guild:discord.Guild) -> list["Wormhole"]:
        wormholes = []
        for link in WormholeLink.all():
            if guild.get_channel(link.channel_id):
                wormhole = Wormhole.get_by_id(link.wormhole_id)
                if wormhole:
                    wormholes.append(wormhole)
        return wormholes
    
    #==========================================================================
    # Others
    #==========================================================================

    @property
    def links(self) -> list["WormholeLink"]:
        return WormholeLink.get_from(self)

    @property
    def linked_channels_id(self) -> list[int]:
        channels_id = []
        for link in self.links:
            channels_id.append(link.channel_id)
        return channels_id
    
    @property
    def reading_channels_id(self):
        channels_id = []
        for link in self.links:
            if link.can_read:
                channels_id.append(link.channel_id)
        return channels_id
    
    @property
    def writing_channels_id(self):
        channels_id = []
        for link in self.links:
            if self.id and link.can_write:
                channels_id.append(link.channel_id)
        return channels_id

    def __str__(self):
        return self.name + f" (id:{self.id})"

    def __repr__(self):
        return f"<Wormhole id:{self.id} name:{self.name} sync_threads:{self.sync_threads}>"

class WormholeLink:

    def __init__(self, wormhole_id:int|Wormhole, channel_id:int|discord.abc.GuildChannel, can_read:bool, can_write:bool, webhook_name:str=None, webhook_avatar:str=None):
        self.wormhole_id = wormhole_id.id if isinstance(wormhole_id, Wormhole) else int(wormhole_id)
        self.channel_id = channel_id.id if isinstance(channel_id, discord.abc.GuildChannel) else int(channel_id)
        self.can_read = bool(can_read)
        self.can_write = bool(can_write)
        self.webhook_name = str(webhook_name)
        self.webhook_avatar = str(webhook_avatar)

    @staticmethod
    def add(wormhole:int|Wormhole, channel:int|discord.abc.GuildChannel, read:bool=True, write:bool=False)->"WormholeLink":

        # Check if the link already exist
        for link in WormholeLink.all():
            if link.wormhole_id == wormhole and link.channel_id == channel:
                return link
        
        # If not, create it
        if isinstance(wormhole, Wormhole):
            wormhole = wormhole.id
        if isinstance(channel, discord.abc.GuildChannel):
            channel = channel.id
        allay.Database.query("INSERT INTO wormhole_links (wormhole_id, channel_id, can_read, can_write) VALUES (?,?,?,?)", (wormhole, channel, read, write))
        link = WormholeLink(wormhole, channel, read, write)
        WormholeLink.all().append(link)
        return link

    def remove(self):
        allay.Database.query(f"DELETE FROM wormhole_links WHERE wormhole_id={self.wormhole_id} AND channel_id={self.channel_id}")
        if self in WormholeLink.all():
            WormholeLink.all().remove(self)
        del self

    @staticmethod
    def all():
        return [WormholeLink(**data) for data in allay.Database.query(f"SELECT * FROM wormhole_links")]

    #==========================================================================
    # Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WormholeLink"]:
        links = []
        for link in WormholeLink.all():
            if link.wormhole_id == wormhole.id:
                links.append(link)
        return links

class WormholeAdmin:

    def __init__(self, user_id:int|discord.abc.User, wormhole_id:int|Wormhole):
        self.wormhole_id = wormhole_id.id if isinstance(wormhole_id, Wormhole) else int(wormhole_id)
        self.user_id = user_id.id if isinstance(user_id, discord.abc.User) else int(user_id)

    @staticmethod
    def add(wormhole_id:int|Wormhole, user_id:int|discord.abc.User) -> "WormholeAdmin":

        # Check if the admin already exist
        for admin in WormholeAdmin.all():
            if admin.wormhole_id == wormhole_id and admin.user_id == user_id:
                return admin
        
        # If not, create it
        if isinstance(user_id, discord.abc.User):
            user_id = user_id.id
        if isinstance(wormhole_id, Wormhole):
            wormhole_id = wormhole_id.id
        allay.Database.query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (wormhole_id, user_id))
        return WormholeAdmin(user_id, wormhole_id)   
    
    @staticmethod
    def all():
        return [WormholeAdmin(**data) for data in allay.Database.query(f"SELECT * FROM wormhole_admins")]

    #==========================================================================
    # Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WormholeAdmin"]:
        admins = []
        for admin in WormholeAdmin.all():
            if admin.wormhole_id == wormhole.id:
                admins.append(admin)
        return admins

    #==========================================================================
    # Others
    #==========================================================================

    def __str__(self):
        return f"{self.user_id} (Admin of wormhole {self.wormhole_id})"

    def __repr__(self):
        return f"<WormholeAdmin user_id:{self.user_id} wormhole_id:{self.wormhole_id}>"