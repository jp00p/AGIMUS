from common import *

from queries.rematerialization import *
from queries.crystal_instances import *
from utils.crystal_instances import *

from utils.check_channel_access import access_check

class RematerializationView(discord.ui.View):
  def __init__(self, cog, user: discord.User):
    super().__init__(timeout=180)
    self.cog = cog
    self.user = user

    self.state = 'RARITY'

    self.source_rarity_rank = None
    self.target_rarity_rank = None

    self.rarity_rows = []
    self.type_rows = []
    self.type_page = 0
    self.type_per_page = 25

    self.selected_crystal_type_id = None
    self.selected_crystal_type_name = None
    self.selected_crystal_type_count = 0

    self.quantity = 1

    self.message = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return interaction.user.id == self.user.id

  async def on_timeout(self):
    for item in self.children:
      item.disabled = True
    if self.message:
      try:
        await self.message.edit(
          embed=discord.Embed(
            title='Crystal Rematerialization',
            description='Session expired.',
            color=discord.Color.dark_grey()
          ),
          view=self
        )
      except Exception:
        pass

  def _clear_components(self):
    self.clear_items()

  def _type_total_pages(self) -> int:
    if not self.type_rows:
      return 1
    return max(1, (len(self.type_rows) - 1) // self.type_per_page + 1)

  def _type_page_slice(self) -> list[dict]:
    start = self.type_page * self.type_per_page
    end = start + self.type_per_page
    return self.type_rows[start:end]

  def _clamp_quantity(self):
    if self.quantity < 1:
      self.quantity = 1
    if self.selected_crystal_type_count and self.quantity > self.selected_crystal_type_count:
      self.quantity = self.selected_crystal_type_count

  def _embed(self) -> discord.Embed:
    if self.state == 'RARITY':
      desc = 'Select a rarity to rematerialize into the next tier.'
      if not self.rarity_rows:
        desc = 'You have no unattuned crystals available for rematerialization.'
      return discord.Embed(
        title='Crystal Rematerialization',
        description=desc,
        color=discord.Color.teal()
      )

    if self.state == 'TYPE':
      pages = self._type_total_pages()
      desc = 'Select a crystal type to consume.'
      if pages > 1:
        desc += f'\nPage {self.type_page + 1}/{pages}'
      if not self.type_rows:
        desc = 'No crystal types available for that rarity.'
      return discord.Embed(
        title='Choose Crystal Type',
        description=desc,
        color=discord.Color.teal()
      )

    if self.state == 'QUANTITY':
      return discord.Embed(
        title='Choose Quantity',
        description=(
          f'Crystal Type: **{self.selected_crystal_type_name}**\n'
          f'Available: **{self.selected_crystal_type_count}**\n'
          f'Quantity to consume: **{self.quantity}**'
        ),
        color=discord.Color.teal()
      )

    if self.state == 'CONFIRM':
      return discord.Embed(
        title='Confirm Rematerialization',
        description=(
          f'Rarity: **{self.cog.rarity_name(self.source_rarity_rank)}** -> **{self.cog.rarity_name(self.target_rarity_rank)}**\n'
          f'Type: **{self.selected_crystal_type_name}**\n'
          f'Consume: **{self.quantity}** crystal(s)\n\n'
          'Confirm to proceed.'
        ),
        color=discord.Color.orange()
      )

    return discord.Embed(title='Crystal Rematerialization', color=discord.Color.teal())

  def _add_cancel_button(self):
    btn = discord.ui.Button(label='Cancel', style=discord.ButtonStyle.secondary, row=2)
    btn.callback = self._on_cancel
    self.add_item(btn)

  def _add_back_button(self):
    btn = discord.ui.Button(label='Back', style=discord.ButtonStyle.secondary, row=2)
    btn.callback = self._on_back
    self.add_item(btn)

  def _build_rarity_select_options(self) -> list[discord.SelectOption]:
    opts = []
    for row in self.rarity_rows:
      source_rank = row['rarity_rank']
      label = row['name']
      emoji = row.get('emoji')
      desc = f"Unattuned: {row['count']}"
      opts.append(discord.SelectOption(label=label, value=str(source_rank), description=desc, emoji=emoji))
    return opts[:25]

  def _add_rarity_select(self):
    options = self._build_rarity_select_options()
    if not options:
      return
    select = discord.ui.Select(
      placeholder='Choose a rarity to rematerialize',
      min_values=1,
      max_values=1,
      options=options
    )
    select.callback = self._on_select_rarity
    self.add_item(select)

  def _build_type_select_options(self) -> list[discord.SelectOption]:
    opts = []
    for row in self._type_page_slice():
      label = row['crystal_name']
      value = str(row['crystal_type_id'])
      count = row['count']
      emoji = row.get('emoji')
      desc = f'Unattuned: {count}'
      opts.append(discord.SelectOption(label=label, value=value, description=desc, emoji=emoji))
    if not opts:
      opts.append(discord.SelectOption(
        label='No crystal types found',
        value='none',
        description='You have none to rematerialize.'
      ))
    return opts[:25]

  def _add_type_select(self):
    total_pages = self._type_total_pages()
    placeholder = 'Choose a crystal type'
    if total_pages > 1:
      placeholder = f'Choose a crystal type (Page {self.type_page + 1}/{total_pages})'

    select = discord.ui.Select(
      placeholder=placeholder,
      min_values=1,
      max_values=1,
      options=self._build_type_select_options()
    )
    select.callback = self._on_select_type
    self.add_item(select)

  def _add_type_pagination_buttons(self):
    if self._type_total_pages() <= 1:
      return

    prev_btn = discord.ui.Button(label='Prev', style=discord.ButtonStyle.primary, row=1)
    next_btn = discord.ui.Button(label='Next', style=discord.ButtonStyle.primary, row=1)

    prev_btn.disabled = (self.type_page <= 0)
    next_btn.disabled = (self.type_page >= self._type_total_pages() - 1)

    prev_btn.callback = self._on_prev_type_page
    next_btn.callback = self._on_next_type_page

    self.add_item(prev_btn)
    self.add_item(next_btn)

  def _add_quantity_buttons(self):
    minus = discord.ui.Button(label='-1', style=discord.ButtonStyle.secondary, row=0)
    plus = discord.ui.Button(label='+1', style=discord.ButtonStyle.secondary, row=0)
    minus10 = discord.ui.Button(label='-10', style=discord.ButtonStyle.secondary, row=1)
    plus10 = discord.ui.Button(label='+10', style=discord.ButtonStyle.secondary, row=1)
    max_btn = discord.ui.Button(label='Max', style=discord.ButtonStyle.primary, row=1)

    minus.callback = self._on_qty_minus
    plus.callback = self._on_qty_plus
    minus10.callback = self._on_qty_minus10
    plus10.callback = self._on_qty_plus10
    max_btn.callback = self._on_qty_max

    self.add_item(minus)
    self.add_item(plus)
    self.add_item(minus10)
    self.add_item(plus10)
    self.add_item(max_btn)

  def _add_continue_button(self):
    btn = discord.ui.Button(label='Continue', style=discord.ButtonStyle.success, row=2)
    btn.callback = self._on_continue_to_confirm
    self.add_item(btn)

  def _add_confirm_button(self):
    btn = discord.ui.Button(label='Confirm Rematerialization', style=discord.ButtonStyle.danger, row=2)
    btn.callback = self._on_confirm
    self.add_item(btn)

  def _rebuild(self):
    self._clear_components()

    if self.state == 'RARITY':
      self._add_rarity_select()
      self._add_cancel_button()
      return

    if self.state == 'TYPE':
      self._add_type_select()
      self._add_type_pagination_buttons()
      self._add_back_button()
      self._add_cancel_button()
      return

    if self.state == 'QUANTITY':
      self._add_quantity_buttons()
      self._add_back_button()
      self._add_cancel_button()
      self._add_continue_button()
      return

    if self.state == 'CONFIRM':
      self._add_confirm_button()
      self._add_back_button()
      self._add_cancel_button()
      return

  async def _render(self, interaction: discord.Interaction):
    self._rebuild()
    await interaction.response.edit_message(embed=self._embed(), view=self)

  async def start(self, ctx: discord.ApplicationContext):
    await ctx.respond(embed=self._embed(), view=self, ephemeral=True)
    self.message = await ctx.interaction.original_response()

  async def _load_rarity_rows(self) -> list[dict]:
    rows = await db_get_user_unattuned_crystal_rarities(self.user.id)

    # Only allow rarities that have a next tier.
    filtered = []
    for row in rows:
      source_rank = row['rarity_rank']
      target_rank = source_rank + 1
      target = await db_get_crystal_rank_by_rarity_rank(target_rank)
      if target:
        filtered.append(row)
    return filtered

  async def _on_select_rarity(self, interaction: discord.Interaction):
    source_rank = int(interaction.data['values'][0])
    self.source_rarity_rank = source_rank
    self.target_rarity_rank = source_rank + 1

    self.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      self.user.id,
      self.source_rarity_rank
    )
    self.type_page = 0
    self.state = 'TYPE'
    await self._render(interaction)

  async def _on_prev_type_page(self, interaction: discord.Interaction):
    if self.type_page > 0:
      self.type_page -= 1
    await self._render(interaction)

  async def _on_next_type_page(self, interaction: discord.Interaction):
    if self.type_page < self._type_total_pages() - 1:
      self.type_page += 1
    await self._render(interaction)

  async def _on_select_type(self, interaction: discord.Interaction):
    val = interaction.data['values'][0]
    if val == 'none':
      await self._render(interaction)
      return

    crystal_type_id = int(val)
    row = next((r for r in self.type_rows if r['crystal_type_id'] == crystal_type_id), None)
    if not row:
      await self._render(interaction)
      return

    self.selected_crystal_type_id = crystal_type_id
    self.selected_crystal_type_name = row['crystal_name']
    self.selected_crystal_type_count = row['count']

    self.quantity = 1
    self.state = 'QUANTITY'
    await self._render(interaction)

  async def _on_qty_minus(self, interaction: discord.Interaction):
    self.quantity -= 1
    self._clamp_quantity()
    await self._render(interaction)

  async def _on_qty_plus(self, interaction: discord.Interaction):
    self.quantity += 1
    self._clamp_quantity()
    await self._render(interaction)

  async def _on_qty_minus10(self, interaction: discord.Interaction):
    self.quantity -= 10
    self._clamp_quantity()
    await self._render(interaction)

  async def _on_qty_plus10(self, interaction: discord.Interaction):
    self.quantity += 10
    self._clamp_quantity()
    await self._render(interaction)

  async def _on_qty_max(self, interaction: discord.Interaction):
    self.quantity = self.selected_crystal_type_count or 1
    self._clamp_quantity()
    await self._render(interaction)

  async def _on_continue_to_confirm(self, interaction: discord.Interaction):
    self.state = 'CONFIRM'
    await self._render(interaction)

  async def _on_back(self, interaction: discord.Interaction):
    if self.state == 'TYPE':
      self.state = 'RARITY'
      await self._render(interaction)
      return

    if self.state == 'QUANTITY':
      self.state = 'TYPE'
      await self._render(interaction)
      return

    if self.state == 'CONFIRM':
      self.state = 'QUANTITY'
      await self._render(interaction)
      return

    await self._render(interaction)

  async def _on_cancel(self, interaction: discord.Interaction):
    for item in self.children:
      item.disabled = True

    await interaction.response.edit_message(
      embed=discord.Embed(
        title='Rematerialization Cancelled',
        description='No changes were made.',
        color=discord.Color.dark_grey()
      ),
      view=self
    )

  async def _on_confirm(self, interaction: discord.Interaction):
    active = await db_get_active_rematerialization(str(self.user.id))
    if active:
      await interaction.response.edit_message(
        embed=discord.Embed(
          title='Rematerialization Already Active',
          description='You already have an active rematerialization session.',
          color=discord.Color.orange()
        ),
        view=self
      )
      return

    crystal_ids = await db_get_unattuned_crystal_instance_ids_by_type(
      self.user.id,
      self.selected_crystal_type_id,
      self.quantity
    )

    if len(crystal_ids) < self.quantity:
      self.selected_crystal_type_count = len(crystal_ids)
      self.quantity = min(self.quantity, self.selected_crystal_type_count or 1)
      self.state = 'QUANTITY'
      self._rebuild()
      await interaction.response.edit_message(
        embed=discord.Embed(
          title='Inventory Changed',
          description='You no longer have enough unattuned crystals of that type. Please pick a new quantity.',
          color=discord.Color.orange()
        ),
        view=self
      )
      return

    rematerialization_id = await db_create_rematerialization(
      str(self.user.id),
      self.source_rarity_rank,
      self.target_rarity_rank
    )

    for cid in crystal_ids:
      await db_add_crystal_to_rematerialization(rematerialization_id, cid)

    await db_mark_crystals_rematerialized(crystal_ids)

    new_crystal_instance_id = await self.cog.create_output_crystal_instance(
      user_id=self.user.id,
      target_rarity_rank=self.target_rarity_rank,
      source_crystal_type_id=self.selected_crystal_type_id
    )

    await db_finalize_rematerialization(rematerialization_id, new_crystal_instance_id)

    for item in self.children:
      item.disabled = True

    await interaction.response.edit_message(
      embed=discord.Embed(
        title='Rematerialization Complete',
        description=(
          f'Consumed **{self.quantity}** crystal(s) of **{self.selected_crystal_type_name}**.\n'
          f'Created a new **{self.cog.rarity_name(self.target_rarity_rank)}** crystal.'
        ),
        color=discord.Color.green()
      ),
      view=self
    )


class Rematerialize(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  rematerialize = discord.SlashCommandGroup('rematerialize', 'Crystal Rematerialization Commands.')

  def rarity_name(self, rarity_rank: int) -> str:
    name = {
      1: 'Common',
      2: 'Uncommon',
      3: 'Rare',
      4: 'Legendary',
      5: 'Mythic'
    }.get(rarity_rank)
    return name or f'Rank {rarity_rank}'

  async def create_output_crystal_instance(self, user_id: int, target_rarity_rank: int, source_crystal_type_id: int) -> int:
    return await db_create_random_crystal_instance_by_rarity_rank(user_id, target_rarity_rank)

  @rematerialize.command(name='start', description='Begin crystal rematerialization.')
  @access_check()
  async def start(self, ctx: discord.ApplicationContext):
    view = RematerializationView(self, ctx.user)
    view.rarity_rows = await view._load_rarity_rows()
    await view.start(ctx)

