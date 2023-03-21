from common import *
from ..ui import *
from ..objects import Poshimo
from . import main_menu as mm

class Shimodaepaedia(PoshimoView):
  def __init__(self, cog, trainer):
    super().__init__(cog, trainer)

    self.embeds = [
      discord.Embed(
        title="Poshimodaepaedia",
        description="This is the pokedex"
      )
    ]
    
    # pokedex
    # list of places
    # list of fish
    

    # travel log:
    # show list of found pokemon
    # show list of unknown pokemon
    # exits, etc