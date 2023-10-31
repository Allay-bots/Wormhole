
import discord

import allay

class WormholeSelector(discord.ui.Select):
    def __init__(self, wormholes_id:list[int], callback):
        self.wormholes_id = sorted(wormholes_id)
        self.custom_callback = callback

        options = []
        for wh in allay.Database.query("SELECT * FROM wormholes ORDER BY id ASC"):
            if wh['id'] in self.wormholes_id:
                options.append(discord.SelectOption(label=wh['name'], value=str(wh['id'])))

        super().__init__(placeholder='Select a wormhole', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction, int(self.values[0]))

class WormholeSelectorView(discord.ui.View):
    def __init__(self, wormholes_id:list[int], callback):
        super().__init__()
        self.add_item(WormholeSelector(wormholes_id, callback))