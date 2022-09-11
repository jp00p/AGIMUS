from common import *

class PoshimoButton(discord.ui.Button):
  def __init__(self, cog, _label, _color="blurple", _row=2, callback_func="pass"):
    self.cog = cog
    self._label = _label
    self._color = _color
    self._row = _row
    self.callback_func = callback_func
    super().__init__(
      label=self._label,
      style=getattr(discord.ButtonStyle, self._color),
      row=self._row
    )
  async def callback(self, interaction: discord.Interaction):
    try:
      callback_method = getattr(self.cog, self.callback_func)
    except AttributeError:
      raise NotImplementedError("Cog {} has not implemented the {} method".format(self.cog.__class__.__name__, self.callback_func))
    await callback_method(interaction) # fire callback (should be in the cog)