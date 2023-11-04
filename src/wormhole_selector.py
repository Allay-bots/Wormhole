
import discord

import allay

class WormholeSelector(discord.ui.Select):
    def __init__(self, wormholes_id:list[int]):
        self.wormholes_id = sorted(wormholes_id)

        options = []
        for wh in allay.Database.query("SELECT * FROM wormholes ORDER BY id ASC"):
            if wh['id'] in self.wormholes_id:
                options.append(discord.SelectOption(label=wh['name'], value=str(wh['id'])))

        super().__init__(placeholder='Select a wormhole', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.view.stop()

class WormholeSelectorView(discord.ui.View):
    def __init__(self, wormholes_id:list[int]):
        super().__init__()
        self.add_item(WormholeSelector(wormholes_id))

    @property
    def interaction(self):
        return self.children[0].interaction
    
    @property
    def values(self):
        return self.children[0].values