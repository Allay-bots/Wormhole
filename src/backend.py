from typing import Optional
import discord
from LRFutils import logs
import allay

class Wormhole:
    def __init__(self, id:int, name:str, sync_threads:bool):
        self.id = int(id)
        self.name = str(name)
        self.sync_threads = bool(sync_threads)

    #==========================================================================
    # Database Getters
    #==========================================================================

    # Get wormhole by ID
    @staticmethod
    def get_by_id(id) -> Optional["Wormhole"]:
        try:
            return Wormhole(**allay.Database.query(f"SELECT * FROM wormholes WHERE id={id}")[0])
        except IndexError:
            return None

    # Get all active wormholes
    @staticmethod
    def get_all() -> list[int]:
        return [Wormhole(**data) for data in allay.Database.query(f"SELECT id FROM wormholes")]

    # Get wormholes the user is admin of
    @staticmethod
    def get_accessible_by(user:discord.User) -> list["Wormhole"]:
        return [Wormhole(**data) for data in allay.Database.query(f"SELECT * FROM wormholes WHERE id IN (SELECT wormhole_id FROM wormhole_admins WHERE user_id = {user.id})")] 

    # Get wormholes linked to a specific channel
    @staticmethod
    def get_linked_to(channel:discord.abc.GuildChannel, filter_can_read=False, filter_can_write=False) -> list["Wormhole"]:

        filters = " AND can_read = true" if filter_can_read else ""
        filters += " AND can_write = true" if filter_can_write else ""

        return [Wormhole(**data) for data in allay.Database.query(f"SELECT * FROM wormholes WHERE id IN (SELECT wormhole_id FROM wormhole_links WHERE channel_id = {channel.id}{filters})")]


    # Get wormholes linked somewhere in the guild
    @staticmethod
    def get_linked_in(guild:discord.Guild) -> list["Wormhole"]:
        return [Wormhole(**data) for data in allay.Database.query(f"SELECT * FROM wormholes WHERE id IN (SELECT wormhole_id FROM wormhole_links WHERE channel_id IN (SELECT id FROM channels WHERE guild_id = {guild.id}))")]

    #==========================================================================
    # Database Setters
    #==========================================================================
    
    @staticmethod
    def open(name:str, sync_threads:bool=True) -> int:
        wormhole_id = allay.Database.query(f"INSERT INTO wormholes (name, sync_threads) VALUES (?,?)", (name, sync_threads))
        return wormhole_id
    
    #==========================================================================
    # Others
    #==========================================================================

    @property
    def links(self) -> list["WormholeLink"]:
        return WormholeLink.get_from(self)

    @property
    def linked_channels_id(self) -> list[int]:
        return [int(link['channel_id']) for link in allay.Database.query(f"SELECT channel_id FROM wormhole_links WHERE wormhole_id={self.id}")]
    
    @property
    def reading_channels_id(self):
        return [int(link['channel_id']) for link in allay.Database.query(f"SELECT channel_id FROM wormhole_links WHERE wormhole_id={self.id} AND can_read=true")]
    
    @property
    def writing_channels_id(self):
        return [int(link['channel_id']) for link in allay.Database.query(f"SELECT channel_id FROM wormhole_links WHERE wormhole_id={self.id} AND can_write=true")]
    
    @staticmethod
    def set(wormholes:list["Wormhole"]) -> list["Wormhole"]:
        new_set = []
        seen = []
        for wormhole in wormholes:
            if wormhole.id not in seen:
                seen.append(wormhole.id)
                new_set.append(wormhole)
        return new_set

    @staticmethod
    def is_in(wormhole, wormholes:list["Wormhole"]) -> bool:
        return wormhole.id in [w.id for w in wormholes]

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

    #==========================================================================
    # Database Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WormholeLink"]:
        return [WormholeLink(**data) for data in allay.Database.query(f"SELECT * FROM wormhole_links WHERE wormhole_id={wormhole.id}")]

    #==========================================================================
    # Database Setters
    #==========================================================================

    @staticmethod
    def add(wormhole:int|Wormhole, channel:int|discord.abc.GuildChannel, read:bool=True, write:bool=False):
        if isinstance(wormhole, Wormhole):
            wormhole = wormhole.id
        if isinstance(channel, discord.abc.GuildChannel):
            channel = channel.id
        allay.Database.query("INSERT INTO wormhole_links (wormhole_id, channel_id, can_read, can_write) VALUES (?,?,?,?)", (wormhole, channel, read, write))

    @staticmethod
    def remove(wormhole:int|Wormhole, channel:int|discord.abc.GuildChannel):
        if isinstance(wormhole, Wormhole):
            wormhole = wormhole.id
        if isinstance(channel, discord.abc.GuildChannel):
            channel = channel.id
        allay.Database.query(f"DELETE FROM wormhole_links WHERE wormhole_id={wormhole} AND channel_id={channel}")

class WormholeAdmin:

    def __init__(self, user_id:int|discord.abc.User, wormhole_id:int|Wormhole):
        self.wormhole_id = wormhole_id.id if isinstance(wormhole_id, Wormhole) else int(wormhole_id)
        self.user_id = user_id.id if isinstance(user_id, discord.abc.User) else int(user_id)

    #==========================================================================
    # Database Getters
    #==========================================================================

    @staticmethod
    def get_from(wormhole:Wormhole) -> list["WormholeAdmin"]:
        return [WormholeAdmin(**data) for data in allay.Database.query(f"SELECT * FROM wormhole_admins WHERE wormhole_id={wormhole.id}")]

    #==========================================================================
    # Database Setters
    #==========================================================================

    @staticmethod
    def add(wormhole_id:int|Wormhole, user_id:int|discord.abc.User):
        if isinstance(user_id, discord.abc.User):
            user_id = user_id.id
        if isinstance(wormhole_id, Wormhole):
            wormhole_id = wormhole_id.id
        allay.Database.query("INSERT INTO wormhole_admins (wormhole_id, user_id) VALUES (?,?)", (wormhole_id, user_id))
        return WormholeAdmin(user_id, wormhole_id)

    #==========================================================================
    # Others
    #==========================================================================

    def __str__(self):
        return f"{self.user_id} (Admin of wormhole {self.wormhole_id})"

    def __repr__(self):
        return f"<WormholeAdmin user_id:{self.user_id} wormhole_id:{self.wormhole_id}>"