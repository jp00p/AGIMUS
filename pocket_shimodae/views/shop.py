from common import *
from ..ui import *
from ..objects import PoshimoShop

class ShoppingScreen(PoshimoView):
  def __init__(self, cog, trainer, shop:PoshimoShop, message=""):
    super().__init__(cog, trainer)
    self.shop = shop
    
    description = ""
    if message:
      description = message + "\n"
    description += shop.list_inventory()

    shop_embed = discord.Embed(
      title="Welcome to the shop!",
      description=f"{description}"
    )
    shop_embed.set_footer(text=f"Your Scarves: {self.trainer.scarves}")
    self.embeds = [shop_embed]
    
    


