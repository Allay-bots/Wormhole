
from LRFutils import logs
from allay.core.src.discord import Bot
from .src.wormhole import *

version = "0.0.1"
icon = "🌀"
name = "Wormhole"

class Test(commands.Cog):
    def __init__(self, bot: Bot):
        print("Ca charge ?")
        self.bot = bot
    
    @commands.command(name="test")
    async def test(self, ctx: Context):
        print("Ca détecte la commande ?")
        await ctx.send("test")

async def setup(bot:Bot):
    logs.info(f"Loading {icon} {name} v{version}...")
    await bot.add_cog(Test(bot), icon=icon)
    await bot.add_cog(Wormholes(bot), icon=icon)