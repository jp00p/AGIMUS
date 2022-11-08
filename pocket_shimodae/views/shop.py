from common import *

from ..objects import PoshimoItem, PoshimoShop
from ..ui import *
from . import main_menu as mm

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
      description=fill_embed_text(f"{description}")
    )
    shop_embed.set_footer(text=f"Your Scarves: {self.trainer.scarves}")
    self.embeds = [shop_embed]
    self.add_item(ShopBuyMenu(self.cog, self.trainer, self.shop))
    if len(self.trainer.inventory) > 0:
      self.add_item(ShopSellMenu(self.cog, self.trainer, self.shop))
    self.add_item(mm.BackToMainMenu(self.cog, self.trainer))
    
class ShopBuyMenu(discord.ui.Select):
  def __init__(self, cog, trainer:PoshimoTrainer, shop:PoshimoShop, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.shop = shop
    options = []
    for key, stockitem in enumerate(shop.stock):
      options.append(discord.SelectOption(
        label=f"{stockitem[0].name.title()} - {stockitem[1]} Scarves",
        value=f"{key}"
      ))
    
    super().__init__(
      placeholder="Choose an item to purchase",
      options=options,
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    item_choice = self.shop.stock[int(self.values[0])]
    item = item_choice[0]
    response = ""
    purchase = self.shop.buy(self.trainer, int(self.values[0]))
    if purchase:
      title = "Purchase complete"
      response = f"**You purchased one {item}!**\n"
    else:
      title = "What are you thinking?"
      response = "__You don't enough scarves!__\n"
    view = ShoppingScreen(self.cog, self.trainer, self.shop)
    view.add_notification(title, response)
    
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())


class ShopSellMenu(discord.ui.Select):
  def __init__(self, cog, trainer:PoshimoTrainer, shop:PoshimoShop, **kwargs):
    self.cog = cog
    self.trainer = trainer
    self.shop = shop
    options = []
    
    for i in self.trainer.inventory.values():
      options.append(discord.SelectOption(
        label=f'{i["item"].sell_price} - {i["item"].name}',
        value=i["item"].name
      ))
    super().__init__(
      placeholder="Choose an item to sell",
      options=options,
      **kwargs
    )
  async def callback(self, interaction:discord.Interaction):
    choice = self.values[0]
    item:PoshimoItem = self.trainer.inventory[choice]["item"]
    self.trainer.scarves += item.sell_price
    self.trainer.remove_item(item)
    title = f"Item sold"
    response = f"You sold one {item} for {item.sell_price} Scarves!"    
    view = ShoppingScreen(self.cog, self.trainer, self.shop)
    view.add_notification(title, response)
    await interaction.response.edit_message(view=view, embeds=view.get_embeds())
