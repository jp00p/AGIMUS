from common import *

# show points
# jackpots ???

class SlotsGame(discord.ui.View):
  def __init__(self, player, cog):
    self.player = player
    self.cog = cog
    super().__init__()
    self.add_item(SlotsPlayButton)
    self.add_item(SlotsShopButton)
    self.add_item(SlotsStatusButton)

    self.embeds = [
      discord.Embed(
        title="Slots slots slots",
        description="Lets play a game."
      )
    ]

class SlotsPlayButton(discord.ui.Button["SlotsGame"]):
  async def callback(self, interaction: discord.Interaction):
    return await super().callback(interaction)

class SlotsShopButton(discord.ui.Button["SlotsGame"]):
  async def callback(self, interaction: discord.Interaction):
    return await super().callback(interaction)

class SlotsStatusButton(discord.ui.Button["SlotsGame"]):
  async def callback(self, interaction: discord.Interaction):
    return await super().callback(interaction)
  

class SlotsShop(discord.ui.View):
  def __init__(self, player):
    self.player = player
    super().__init__()


class SlotsInventoryView(discord.ui.View):
  def __init__(self, player):
    self.player = player
    super().__init__()


class SlotsInventoryPaginator(pages.Paginator):
  pass

class InventoryDestroyButton(discord.ui.Button):
  pass

class CancelButton(discord.ui.Button):
  pass