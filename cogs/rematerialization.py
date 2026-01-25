from common import *

from queries.crystal_instances import *
from queries.rematerialization import *
from utils.crystal_instances import *

from utils.check_channel_access import access_check

class RematerializationView(discord.ui.DesignerView):
  def __init__(self, cog, user: discord.User):
    super().__init__(timeout=180)
    self.cog = cog
    self.user = user
    self.user_discord_id = str(user.id)

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

    self.contents_target = 10
    self.contents = {}  # crystal_type_id -> qty

    self.rematerialization_id = None
    self.selected_instance_ids = set()

    self.notice = None
    self.message = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return interaction.user.id == self.user.id

  async def on_timeout(self):
    self.disable_all_items()
    self.notice = 'Session expired.'
    if self.message:
      try:
        self._rebuild()
        await self.message.edit(view=self)
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
      name = row['crystal_name'] if row else 'Type {type_id}'.format(type_id=type_id)
      parts.append('{name} x{qty}'.format(name=name, qty=qty))
    return ', '.join(parts)

  def _effective_available_for_row(self, row: dict) -> int:
    chosen = self.contents.get(row['crystal_type_id'], 0)
    return max(0, row['count'] - chosen)

  def _ui_title(self) -> str:
    if self.state == 'RARITY':
      return 'Crystal Rematerialization'
    if self.state == 'TYPE':
      return 'Select Crystal Type'
    if self.state == 'QUANTITY':
      return 'Select Quantity'
    if self.state == 'CONFIRM':
      return 'Confirm Rematerialization'
    return 'Crystal Rematerialization'

  def _ui_body(self) -> str:
    if self.state == 'RARITY':
      if not self.rarity_rows:
        return 'You do not have enough unattuned crystals in any tier to Rematerialize (requires 10).'
      return 'Select a rarity tier. You will Dematerialize 10 crystals from that tier to Materialize 1 Crystal of the next tier.'

    if self.state == 'TYPE':
      if not self.type_rows:
        return 'No Crystal types available for that rarity.'
      return 'Select a crystal type to add.'

    if self.state == 'QUANTITY':
      return 'Select how many crystals to add.'

    if self.state == 'CONFIRM':
      return 'Confirm to Dematerialize these crystals and Materialize 1 new Crystal.'

    return '...'

  def _build_container(self) -> discord.ui.Container:
    container = discord.ui.Container(color=discord.Color.teal().value)

    # Header section
    header_text = '**{title}**'.format(title=self._ui_title())
    if self.notice:
      header_text += '\nNote: {msg}'.format(msg=self.notice)

    header = discord.ui.Section(
      discord.ui.TextDisplay(header_text)
    )
    container.add_item(header)
    container.add_item(discord.ui.Separator())

    # Status section (contents / remaining / selected + rarity path)
    status_lines = []
    if self.state in ('TYPE', 'QUANTITY', 'CONFIRM'):
      status_lines.append('Contents: {cur}/{target}'.format(cur=self._contents_total(), target=self.contents_target))
      status_lines.append('Remaining: {rem}'.format(rem=self._contents_remaining()))
      status_lines.append('Selected: {sel}'.format(sel=self._format_contents_summary()))

    if self.state == 'CONFIRM':
      status_lines.append(
        'Rarity: {src} -> {dst}'.format(
          src=self.cog.rarity_name(self.source_rarity_rank),
          dst=self.cog.rarity_name(self.target_rarity_rank)
        )
      )

    if status_lines:
      status = discord.ui.Section(
        discord.ui.TextDisplay('\n'.join(status_lines))
      )
      container.add_item(status)
      container.add_item(discord.ui.Separator())

    # Main instruction section
    main = discord.ui.Section(
      discord.ui.TextDisplay(self._ui_body())
    )
    container.add_item(main)

    # Page text (small)
    if self.state == 'TYPE' and self._type_total_pages() > 1:
      page_line = 'Page {cur}/{total}'.format(cur=self.type_page + 1, total=self._type_total_pages())
      container.add_item(discord.ui.TextDisplay(page_line))

    return container

  def _build_rarity_select_options(self) -> list[discord.SelectOption]:
    opts = []
    for row in self.rarity_rows:
      source_rank = row['rarity_rank']
      label = row['name']
      emoji = row.get('emoji')
      desc = 'Unattuned: {count}'.format(count=row['count'])
      opts.append(discord.SelectOption(label=label, value=str(source_rank), description=desc, emoji=emoji))
    return opts[:25]

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
      desc = 'Available: {shown}'.format(shown=shown)

      opts.append(discord.SelectOption(label=label, value=value, description=desc, emoji=emoji))

    if not opts:
      opts.append(discord.SelectOption(
        label='No crystal types available',
        value='none',
        description='You have nothing left to add.'
      ))

    return opts[:25]

  def _build_quantity_select_options(self) -> list[discord.SelectOption]:
    remaining_needed = self._contents_remaining()
    max_pick = min(self.selected_type_effective_available, remaining_needed)

    opts = []
    for i in range(1, max_pick + 1):
      opts.append(discord.SelectOption(label=str(i), value=str(i)))
    return opts[:25]

  def _add_footer_row(self, container: discord.ui.Container):
    row = discord.ui.ActionRow()

    if self.state in ('QUANTITY', 'CONFIRM'):
      back_btn = discord.ui.Button(label='<- Back', style=discord.ButtonStyle.secondary)
      back_btn.callback = self._on_back
      row.add_item(back_btn)

    # Remove Last Added is only useful once selection started.
    can_remove = bool(self.rematerialization_id) and self._contents_total() > 0 and self.state in ('TYPE', 'QUANTITY', 'CONFIRM')
    if can_remove:
      rm_btn = discord.ui.Button(label='Remove Last Added', style=discord.ButtonStyle.secondary)
      rm_btn.callback = self._on_remove_last
      row.add_item(rm_btn)

    cancel_btn = discord.ui.Button(label='Cancel', style=discord.ButtonStyle.secondary)
    cancel_btn.callback = self._on_cancel
    row.add_item(cancel_btn)

    if self.state == 'CONFIRM':
      confirm_btn = discord.ui.Button(label='Confirm', style=discord.ButtonStyle.primary)
      confirm_btn.disabled = (self._contents_total() != self.contents_target)
      confirm_btn.callback = self._on_confirm
      row.add_item(confirm_btn)

    container.add_item(discord.ui.Separator())
    container.add_item(row)

  def _rebuild(self):
    self._clear_components()

    container = self._build_container()

    if self.state == 'RARITY':
      options = self._build_rarity_select_options()
      if options:
        select = discord.ui.Select(
          placeholder='Choose a rarity tier',
          min_values=1,
          max_values=1,
          options=options
        )
        select.callback = self._on_select_rarity
        r = discord.ui.ActionRow()
        r.add_item(select)
        container.add_item(r)

      self._add_footer_row(container)
      self.add_item(container)
      return

    if self.state == 'TYPE':
      select = discord.ui.Select(
        placeholder='Choose a crystal type',
        min_values=1,
        max_values=1,
        options=self._build_type_select_options()
      )
      select.callback = self._on_select_type
      r = discord.ui.ActionRow()
      r.add_item(select)
      container.add_item(r)

      if self._type_total_pages() > 1:
        pager = discord.ui.ActionRow()

        prev_btn = discord.ui.Button(label='Prev', style=discord.ButtonStyle.primary)
        next_btn = discord.ui.Button(label='Next', style=discord.ButtonStyle.primary)

        prev_btn.disabled = (self.type_page <= 0)
        next_btn.disabled = (self.type_page >= self._type_total_pages() - 1)

        prev_btn.callback = self._on_prev_type_page
        next_btn.callback = self._on_next_type_page

        pager.add_item(prev_btn)
        pager.add_item(next_btn)
        container.add_item(pager)

      self._add_footer_row(container)
      self.add_item(container)
      return

    if self.state == 'QUANTITY':
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
      r = discord.ui.ActionRow()
      r.add_item(select)
      container.add_item(r)

      self._add_footer_row(container)
      self.add_item(container)
      return

    if self.state == 'CONFIRM':
      self._add_footer_row(container)
      self.add_item(container)
      return

    self._add_footer_row(container)
    self.add_item(container)

  async def _render(self, interaction: discord.Interaction):
    self._rebuild()
    await interaction.response.edit_message(view=self)

  async def start(self, ctx: discord.ApplicationContext):
    self._rebuild()
    await ctx.respond(view=self, ephemeral=True)
    self.message = await ctx.interaction.original_response()

  async def _load_rarity_rows(self) -> list[dict]:
    rows = await db_get_user_unattuned_crystal_rarities(self.user_discord_id)

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
    ids = await db_get_unattuned_crystal_instance_ids_by_type(self.user_discord_id, crystal_type_id, limit)
    ids = [cid for cid in ids if cid not in self.selected_instance_ids]

    if len(ids) < qty:
      ids = await db_get_unattuned_crystal_instance_ids_by_type(self.user_discord_id, crystal_type_id, 200)
      ids = [cid for cid in ids if cid not in self.selected_instance_ids]

    return ids[:qty]

  def _rehydrate_from_items(self, items: list[dict]):
    self.contents = {}
    self.selected_instance_ids = set()

    for it in items:
      tid = it['crystal_type_id']
      self.contents[tid] = self.contents.get(tid, 0) + 1
      self.selected_instance_ids.add(it['crystal_instance_id'])

  async def _on_select_rarity(self, interaction: discord.Interaction):
    self.notice = None

    source_rank = int(interaction.data['values'][0])
    self.source_rarity_rank = source_rank
    self.target_rarity_rank = source_rank + 1

    self.contents = {}
    self.selected_instance_ids = set()
    self.type_page = 0

    self.rematerialization_id = await db_create_rematerialization(
      self.user_discord_id,
      self.source_rarity_rank,
      self.target_rarity_rank
    )

    self.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      self.user_discord_id,
      self.source_rarity_rank
    )

    self.state = 'TYPE'
    await self._render(interaction)

  async def _on_prev_type_page(self, interaction: discord.Interaction):
    self.notice = None
    if self.type_page > 0:
      self.type_page -= 1
    await self._render(interaction)

  async def _on_next_type_page(self, interaction: discord.Interaction):
    self.notice = None
    if self.type_page < self._type_total_pages() - 1:
      self.type_page += 1
    await self._render(interaction)

  async def _on_select_type(self, interaction: discord.Interaction):
    self.notice = None

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

    self.state = 'QUANTITY'
    await self._render(interaction)

  async def _on_select_quantity(self, interaction: discord.Interaction):
    self.notice = None

    qty = int(interaction.data['values'][0])
    if qty <= 0:
      await self._render(interaction)
      return

    if not self.selected_crystal_type_id:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active rematerialization session was found. Please run `/rematerialize engage` again.',
        discord.Color.red()
      )
      return

    remaining = self._contents_remaining()
    add_qty = min(qty, remaining)

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
        'Your crystal inventory changed. The session was cancelled. Please run `/rematerialize engage` again.',
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

    if self._contents_total() >= self.contents_target:
      self.state = 'CONFIRM'
    else:
      self.state = 'TYPE'

    await self._render(interaction)

  async def _on_remove_last(self, interaction: discord.Interaction):
    self.notice = None

    if not self.rematerialization_id:
      self.notice = 'No active session.'
      await self._render(interaction)
      return

    removed = await db_remove_last_rematerialization_item(self.rematerialization_id)
    if not removed:
      self.notice = 'Nothing to remove.'
      await self._render(interaction)
      return

    tid = removed['crystal_type_id']
    cid = removed['crystal_instance_id']

    if cid in self.selected_instance_ids:
      self.selected_instance_ids.remove(cid)

    if tid in self.contents:
      self.contents[tid] = max(0, self.contents[tid] - 1)
      if self.contents[tid] <= 0:
        del self.contents[tid]

    # If we were on CONFIRM and now dropped below target, go back to TYPE.
    if self.state == 'CONFIRM' and self._contents_total() < self.contents_target:
      self.state = 'TYPE'

    self.notice = 'Removed the last added crystal.'
    await self._render(interaction)

  async def _on_back(self, interaction: discord.Interaction):
    self.notice = None
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

    self.disable_all_items()
    self.notice = 'Rematerialization cancelled. No changes were made.'
    self._rebuild()
    await interaction.response.edit_message(view=self)

  async def _on_confirm(self, interaction: discord.Interaction):
    self.notice = None

    if self._contents_total() != self.contents_target:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active rematerialization session was found. Please run `/rematerialize engage` again.',
        discord.Color.red()
      )
      return

    items = await db_get_rematerialization_items(self.rematerialization_id)

    for it in items:
      if str(it['owner_discord_id']) != self.user_discord_id:
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your crystal inventory changed. The session was cancelled. Please run /rematerialize engage again.',
          discord.Color.orange()
        )
        return
      if it['crystal_status'] != 'available':
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your crystal inventory changed. The session was cancelled. Please run /rematerialize engage again.',
          discord.Color.orange()
        )
        return
      if it['rarity_rank'] != self.source_rarity_rank:
        await db_cancel_rematerialization(self.rematerialization_id)
        await self._hard_stop(
          interaction,
          'Session Invalid',
          'This rematerialization session is no longer valid and was cancelled. Please run /rematerialize engage again.',
          discord.Color.orange()
        )
        return

    if len(items) != self.contents_target:
      self._rehydrate_from_items(items)
      self.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
        self.user_discord_id,
        self.source_rarity_rank
      )
      if self._contents_total() >= self.contents_target:
        self.state = 'CONFIRM'
      else:
        self.state = 'TYPE'
      self.notice = 'Your selection was refreshed. Please confirm again.'
      await self._render(interaction)
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

    created_crystal = await create_new_crystal_instance(
      self.user_discord_id,
      crystal_type['id'],
      event_type='rematerialization'
    )

    await db_finalize_rematerialization(self.rematerialization_id)

    self.clear_items()
    success = discord.ui.Container(color=discord.Color.green().value)
    success.add_item(discord.ui.Section(
      discord.ui.TextDisplay('**REMATERIALIZATION COMPLETE!**')
    ))
    success.add_item(discord.ui.Separator())
    success.add_item(discord.ui.TextDisplay(
      'Dematerialized {n} {src} crystals.\n'
      'Materialized a new {name} at {rarity}!'.format(
        n=self.contents_target,
        src=self.cog.rarity_name(self.source_rarity_rank),
        name=created_crystal['crystal_name'],
        rarity=created_crystal['rarity_name']
      )
    ))
    self.add_item(success)

    await interaction.response.edit_message(view=self)


class Rematerialization(commands.Cog):
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
    return name or 'Rank {rank}'.format(rank=rarity_rank)

  async def create_output_crystal_instance(self, user_id: int, target_rarity_rank: int, source_crystal_type_id: int) -> int:
    crystal_type = await db_select_random_crystal_type_by_rarity_rank(target_rarity_rank)
    crystal = await create_new_crystal_instance(user_id, crystal_type['id'], event_type='rematerialization')
    return crystal['crystal_instance_id']

  @rematerialize.command(name='engage', description='Begin crystal rematerialization.')
  @commands.check(access_check)
  async def start(self, ctx: discord.ApplicationContext):
    user_discord_id = str(ctx.user.id)
    active = await db_get_active_rematerialization(user_discord_id)

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
      if str(it['owner_discord_id']) != user_discord_id:
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
          description='Your active rematerialization session was invalid (inventory changed). Please run /rematerialize engage again.',
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    view._rehydrate_from_items(items)

    view.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      user_discord_id,
      view.source_rarity_rank
    )

    if view._contents_total() >= view.contents_target:
      view.state = 'CONFIRM'
    else:
      view.state = 'TYPE'

    view.notice = 'Resumed your active rematerialization session.'
    await view.start(ctx)
