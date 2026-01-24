from common import *

from queries.crystal_instances import *
from queries.rematerialization import *
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
    self.selected_type_effective_available = 0
    self.selected_quantity = None

    self.contents_target = 10
    self.contents = {}  # crystal_type_id -> qty

    # Persisted session tracking for rejoin.
    self.rematerialization_id = None
    self.selected_instance_ids = set()

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

  async def _hard_stop(self, interaction: discord.Interaction, title: str, description: str, color: discord.Color):
    await interaction.response.send_message(
      embed=discord.Embed(
        title=title,
        description=description,
        color=color
      ),
      ephemeral=True
    )

    try:
      await interaction.message.delete()
    except Exception:
      pass

  def _clear_components(self):
    self.clear_items()

  def _contents_total(self) -> int:
    return sum(self.contents.values())

  def _contents_remaining(self) -> int:
    return max(0, self.contents_target - self._contents_total())

  def _type_total_pages(self) -> int:
    if not self.type_rows:
      return 1
    return max(1, (len(self.type_rows) - 1) // self.type_per_page + 1)

  def _type_page_slice(self) -> list[dict]:
    start = self.type_page * self.type_per_page
    end = start + self.type_per_page
    return self.type_rows[start:end]

  def _format_contents_summary(self) -> str:
    if not self.contents:
      return 'None'
    parts = []
    for type_id, qty in sorted(self.contents.items(), key=lambda kv: kv[0]):
      row = next((r for r in self.type_rows if r['crystal_type_id'] == type_id), None)
      name = row['crystal_name'] if row else f'Type {type_id}'
      parts.append(f'{name} x{qty}')
    return ', '.join(parts)

  def _embed(self) -> discord.Embed:
    if self.state == 'RARITY':
      desc = 'Select a rarity tier. You will dematerialize 10 crystals from that tier to create 1 crystal of the next tier.'
      if not self.rarity_rows:
        desc = 'You do not have enough unattuned crystals in any tier to rematerialize (requires 10).'
      return discord.Embed(
        title='Crystal Rematerialization',
        description=desc,
        color=discord.Color.teal()
      )

    if self.state == 'TYPE':
      pages = self._type_total_pages()
      total = self._contents_total()
      remaining = self._contents_remaining()

      desc = (
        f'Contents: **{total}/{self.contents_target}**\n'
        f'Remaining: **{remaining}**\n'
        f'Selected: **{self._format_contents_summary()}**\n\n'
        'Select a crystal type to add.'
      )
      if pages > 1:
        desc += f'\nPage {self.type_page + 1}/{pages}'

      if not self.type_rows:
        desc = 'No crystal types available for that rarity.'

      return discord.Embed(
        title='Select Crystal Type',
        description=desc,
        color=discord.Color.teal()
      )

    if self.state == 'QUANTITY':
      total = self._contents_total()
      remaining = self._contents_remaining()
      desc = (
        f'Contents: **{total}/{self.contents_target}**\n'
        f'Remaining: **{remaining}**\n'
        f'Selected: **{self._format_contents_summary()}**\n\n'
        f'Type: **{self.selected_crystal_type_name}**\n'
        f'Available: **{self.selected_type_effective_available}**\n'
        'Select how many to add.'
      )
      return discord.Embed(
        title='Select Quantity',
        description=desc,
        color=discord.Color.teal()
      )

    if self.state == 'CONFIRM':
      desc = (
        f'Rarity: **{self.cog.rarity_name(self.source_rarity_rank)}** -> **{self.cog.rarity_name(self.target_rarity_rank)}**\n'
        f'Contents: **{self._contents_total()}/{self.contents_target}**\n'
        f'Selected: **{self._format_contents_summary()}**\n\n'
        'Confirm to dematerialize these crystals and create 1 new crystal.'
      )
      return discord.Embed(
        title='Confirm Rematerialization',
        description=desc,
        color=discord.Color.orange()
      )

    return discord.Embed(title='Crystal Rematerialization', color=discord.Color.teal())

  def _add_cancel_button(self):
    btn = discord.ui.Button(label='Cancel', style=discord.ButtonStyle.secondary, row=3)
    btn.callback = self._on_cancel
    self.add_item(btn)

  def _add_back_button(self):
    btn = discord.ui.Button(label='Back', style=discord.ButtonStyle.secondary, row=3)
    btn.callback = self._on_back
    self.add_item(btn)

  def _add_confirm_button(self):
    btn = discord.ui.Button(label='Confirm', style=discord.ButtonStyle.danger, row=3)
    btn.disabled = (self._contents_total() != self.contents_target)
    btn.callback = self._on_confirm
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
      placeholder='Choose a rarity tier',
      min_values=1,
      max_values=1,
      options=options
    )
    select.callback = self._on_select_rarity
    self.add_item(select)

  def _effective_available_for_row(self, row: dict) -> int:
    chosen = self.contents.get(row['crystal_type_id'], 0)
    return max(0, row['count'] - chosen)

  def _build_type_select_options(self) -> list[discord.SelectOption]:
    remaining_needed = self._contents_remaining()
    opts = []

    for row in self._type_page_slice():
      effective = self._effective_available_for_row(row)
      if effective <= 0:
        continue

      label = row['crystal_name']
      value = str(row['crystal_type_id'])
      emoji = row.get('emoji')

      shown = min(effective, remaining_needed)
      desc = f'Available: {shown}'

      opts.append(discord.SelectOption(label=label, value=value, description=desc, emoji=emoji))

    if not opts:
      opts.append(discord.SelectOption(
        label='No crystal types available',
        value='none',
        description='You have nothing left to add.'
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

    prev_btn = discord.ui.Button(label='Prev', style=discord.ButtonStyle.primary, row=2)
    next_btn = discord.ui.Button(label='Next', style=discord.ButtonStyle.primary, row=2)

    prev_btn.disabled = (self.type_page <= 0)
    next_btn.disabled = (self.type_page >= self._type_total_pages() - 1)

    prev_btn.callback = self._on_prev_type_page
    next_btn.callback = self._on_next_type_page

    self.add_item(prev_btn)
    self.add_item(next_btn)

  def _build_quantity_select_options(self) -> list[discord.SelectOption]:
    remaining_needed = self._contents_remaining()
    max_pick = min(self.selected_type_effective_available, remaining_needed)

    opts = []
    for i in range(1, max_pick + 1):
      opts.append(discord.SelectOption(label=str(i), value=str(i)))
    return opts[:25]

  def _add_quantity_select(self):
    options = self._build_quantity_select_options()
    if not options:
      options = [discord.SelectOption(label='0', value='0', description='None available')]

    select = discord.ui.Select(
      placeholder='Choose quantity to add',
      min_values=1,
      max_values=1,
      options=options
    )
    select.callback = self._on_select_quantity
    self.add_item(select)

  def _add_add_button(self):
    btn = discord.ui.Button(label='Add', style=discord.ButtonStyle.success, row=2)
    btn.disabled = (self.selected_quantity is None or self.selected_quantity <= 0)
    btn.callback = self._on_add_quantity
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
      self._add_cancel_button()
      return

    if self.state == 'QUANTITY':
      self._add_quantity_select()
      self._add_add_button()
      self._add_back_button()
      self._add_cancel_button()
      return

    if self.state == 'CONFIRM':
      self._add_back_button()
      self._add_cancel_button()
      self._add_confirm_button()
      return

  async def _render(self, interaction: discord.Interaction):
    self._rebuild()
    await interaction.response.edit_message(embed=self._embed(), view=self)

  async def start(self, ctx: discord.ApplicationContext):
    self._rebuild()
    await ctx.respond(embed=self._embed(), view=self, ephemeral=True)
    self.message = await ctx.interaction.original_response()

  async def _load_rarity_rows(self) -> list[dict]:
    rows = await db_get_user_unattuned_crystal_rarities(self.user.id)

    filtered = []
    for row in rows:
      if row['count'] < self.contents_target:
        continue

      source_rank = row['rarity_rank']
      target_rank = source_rank + 1
      target = await db_get_crystal_rank_by_rarity_rank(target_rank)
      if not target:
        continue

      filtered.append(row)

    return filtered

  async def _select_instance_ids(self, crystal_type_id: int, qty: int) -> list[int]:
    if qty <= 0:
      return []

    limit = max(25, qty * 3)
    ids = await db_get_unattuned_crystal_instance_ids_by_type(self.user.id, crystal_type_id, limit)
    ids = [cid for cid in ids if cid not in self.selected_instance_ids]

    if len(ids) < qty:
      ids = await db_get_unattuned_crystal_instance_ids_by_type(self.user.id, crystal_type_id, 200)
      ids = [cid for cid in ids if cid not in self.selected_instance_ids]

    return ids[:qty]

  async def _on_select_rarity(self, interaction: discord.Interaction):
    source_rank = int(interaction.data['values'][0])
    target_rank = source_rank + 1

    active = await db_get_active_rematerialization(str(self.user.id))
    if active:
      await self._hard_stop(
        interaction,
        'Rematerialization Already Active',
        'You already have an active rematerialization session. Please run /rematerialize start to rejoin it.',
        discord.Color.orange()
      )
      return

    self.source_rarity_rank = source_rank
    self.target_rarity_rank = target_rank

    self.contents = {}
    self.selected_instance_ids = set()
    self.type_page = 0

    self.rematerialization_id = await db_create_rematerialization(
      str(self.user.id),
      self.source_rarity_rank,
      self.target_rarity_rank
    )

    self.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      self.user.id,
      self.source_rarity_rank
    )

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

    effective = self._effective_available_for_row(row)
    remaining = self._contents_remaining()
    max_pick = min(effective, remaining)
    if max_pick <= 0:
      await self._render(interaction)
      return

    self.selected_crystal_type_id = crystal_type_id
    self.selected_crystal_type_name = row['crystal_name']
    self.selected_type_effective_available = effective
    self.selected_quantity = None

    self.state = 'QUANTITY'
    await self._render(interaction)

  async def _on_select_quantity(self, interaction: discord.Interaction):
    qty = int(interaction.data['values'][0])
    if qty <= 0:
      self.selected_quantity = None
    else:
      self.selected_quantity = qty
    await self._render(interaction)

  async def _on_add_quantity(self, interaction: discord.Interaction):
    if not self.selected_crystal_type_id or not self.selected_quantity:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active rematerialization session was found. Please run /rematerialize start again.',
        discord.Color.red()
      )
      return

    remaining = self._contents_remaining()
    add_qty = min(self.selected_quantity, remaining)

    row = next((r for r in self.type_rows if r['crystal_type_id'] == self.selected_crystal_type_id), None)
    if not row:
      await self._render(interaction)
      return

    effective = self._effective_available_for_row(row)
    add_qty = min(add_qty, effective)

    if add_qty <= 0:
      await self._render(interaction)
      return

    ids = await self._select_instance_ids(self.selected_crystal_type_id, add_qty)
    if len(ids) < add_qty:
      await db_cancel_rematerialization(self.rematerialization_id)
      await self._hard_stop(
        interaction,
        'Inventory Changed',
        'Your crystal inventory changed. The session was cancelled. Please run /rematerialize start again.',
        discord.Color.orange()
      )
      return

    for cid in ids:
      await db_add_crystal_to_rematerialization(self.rematerialization_id, cid)
      self.selected_instance_ids.add(cid)

    self.contents[self.selected_crystal_type_id] = self.contents.get(self.selected_crystal_type_id, 0) + len(ids)

    self.selected_crystal_type_id = None
    self.selected_crystal_type_name = None
    self.selected_type_effective_available = 0
    self.selected_quantity = None

    if self._contents_total() >= self.contents_target:
      self.state = 'CONFIRM'
    else:
      self.state = 'TYPE'

    await self._render(interaction)

  async def _on_back(self, interaction: discord.Interaction):
    if self.state == 'QUANTITY':
      self.state = 'TYPE'
      await self._render(interaction)
      return

    if self.state == 'CONFIRM':
      self.state = 'TYPE'
      await self._render(interaction)
      return

    await self._render(interaction)

  async def _on_cancel(self, interaction: discord.Interaction):
    if self.rematerialization_id:
      await db_cancel_rematerialization(self.rematerialization_id)

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
    if self._contents_total() != self.contents_target:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active rematerialization session was found. Please run /rematerialize start again.',
        discord.Color.red()
      )
      return

    items = await db_get_rematerialization_items(self.rematerialization_id)

    if len(items) != self.contents_target:
      await db_cancel_rematerialization(self.rematerialization_id)
      await self._hard_stop(
        interaction,
        'Inventory Changed',
        'Your crystal inventory changed. The session was cancelled. Please run /rematerialize start again.',
        discord.Color.orange()
      )
      return

    for it in items:
      if it['owner_discord_id'] != self.user.id:
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your crystal inventory changed. The session was cancelled. Please run /rematerialize start again.',
          discord.Color.orange()
        )
        return
      if it['crystal_status'] != 'available':
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your crystal inventory changed. The session was cancelled. Please run /rematerialize start again.',
          discord.Color.orange()
        )
        return
      if it['rarity_rank'] != self.source_rarity_rank:
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Session Invalid',
          'This rematerialization session is no longer valid and was cancelled. Please run /rematerialize start again.',
          discord.Color.orange()
        )
        return

    all_ids = [it['crystal_instance_id'] for it in items]

    await db_mark_crystals_dematerialized(all_ids)

    crystal_type = await db_select_random_crystal_type_by_rarity_rank(self.target_rarity_rank)
    if not crystal_type:
      await db_cancel_rematerialization(self.rematerialization_id)
      await self._hard_stop(
        interaction,
        'Rematerialization Failed',
        'No crystal types exist for the target rarity. The session was cancelled.',
        discord.Color.red()
      )
      return

    await create_new_crystal_instance(
      self.user.id,
      crystal_type['id'],
      event_type='rematerialization'
    )

    await db_finalize_rematerialization(self.rematerialization_id)

    for item in self.children:
      item.disabled = True

    await interaction.response.edit_message(
      embed=discord.Embed(
        title='Rematerialization Complete',
        description=(
          f'Dematerialized **{self.contents_target}** crystal(s) from **{self.cog.rarity_name(self.source_rarity_rank)}**.\n'
          f'Created 1 **{self.cog.rarity_name(self.target_rarity_rank)}** crystal.'
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
    crystal_type = await db_select_random_crystal_type_by_rarity_rank(target_rarity_rank)
    crystal = await create_new_crystal_instance(user_id, crystal_type['id'], event_type='rematerialization')
    return crystal['crystal_instance_id']

  @rematerialize.command(name='engage', description='Begin crystal rematerialization.')
  @commands.check(access_check)
  async def engage(self, ctx: discord.ApplicationContext):
    view = RematerializationView(self, ctx.user)
    view.rarity_rows = await view._load_rarity_rows()
    await view.start(ctx)


    view = RematerializationView(self, ctx.user)

    if not active:
      view.rarity_rows = await view._load_rarity_rows()
      await view.start(ctx)
      return

    view.rematerialization_id = active['id']
    view.source_rarity_rank = active['source_rank_id']
    view.target_rarity_rank = active['target_rank_id']

    items = await db_get_rematerialization_items(view.rematerialization_id)

    invalid = False
    for it in items:
      if it['owner_discord_id'] != ctx.user.id:
        invalid = True
        break
      if it['crystal_status'] != 'available':
        invalid = True
        break
      if it['rarity_rank'] != view.source_rarity_rank:
        invalid = True
        break

    if invalid:
      await db_cancel_rematerialization(view.rematerialization_id)
      await ctx.respond(
        embed=discord.Embed(
          title='Session Cancelled',
          description='Your active rematerialization session was invalid (inventory changed). Please run /rematerialize start again.',
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    view.contents = {}
    view.selected_instance_ids = set()

    for it in items:
      tid = it['crystal_type_id']
      view.contents[tid] = view.contents.get(tid, 0) + 1
      view.selected_instance_ids.add(it['crystal_instance_id'])

    view.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      ctx.user.id,
      view.source_rarity_rank
    )

    if view._contents_total() >= view.contents_target:
      view.state = 'CONFIRM'
    else:
      view.state = 'TYPE'

    await view.start(ctx)
