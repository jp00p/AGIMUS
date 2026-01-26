from common import *

from queries.crystal_instances import *
from queries.rematerialization import *
from utils.crystal_instances import *
from utils.image_utils import *
from utils.check_channel_access import access_check

# cogs.rematerialization

# _____________________   _____      _____________________________________.___   _____  .____    ._____________  ________________.___________    _______
# \______   \_   _____/  /     \    /  _  \__    ___/\_   _____/\______   \   | /  _  \ |    |   |   \____    / /  _  \__    ___/|   \_____  \   \      \
#  |       _/|    __)_  /  \ /  \  /  /_\  \|    |    |    __)_  |       _/   |/  /_\  \|    |   |   | /     / /  /_\  \|    |   |   |/   |   \  /   |   \
#  |    |   \|        \/    Y    \/    |    \    |    |        \ |    |   \   /    |    \    |___|   |/     /_/    |    \    |   |   /    |    \/    |    \
#  |____|_  /_______  /\____|__  /\____|__  /____|   /_______  / |____|_  /___\____|__  /_______ \___/_______ \____|__  /____|   |___\_______  /\____|__  /
#         \/        \/         \/         \/                 \/         \/            \/        \/           \/       \/                     \/         \/
class RematerializationView(discord.ui.DesignerView):
  def __init__(self, cog, user: discord.User):
    super().__init__(timeout=360)
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
    self.selected_type_effective_available = 0

    self.contents_target = 10
    self.contents = {}  # crystal_type_id -> qty

    # Active session support (rejoin)
    self.rematerialization_id = None
    self.selected_instance_ids = set()

    # Optional notice shown in UI
    self.notice = None

    self.message = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return interaction.user.id == self.user.id

  async def on_timeout(self):
    self.disable_all_items()
    if self.message:
      try:
        self.notice = 'Session expired.'
        self._render_end_state_ui('Crystal Rematerialization', 'Session expired.')
        await self.message.edit(view=self)
      except Exception:
        pass

  async def _hard_stop(self, interaction: discord.Interaction, title: str, description: str, color: discord.Color):
    embed = discord.Embed(title=title, description=description, color=color)

    try:
      await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
      try:
        await interaction.followup.send(embed=embed, ephemeral=True)
      except Exception:
        pass

    try:
      if interaction.message:
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

  def _effective_available_for_row(self, row: dict) -> int:
    chosen = self.contents.get(row['crystal_type_id'], 0)
    return max(0, row['count'] - chosen)

  def _get_type_row(self, crystal_type_id: int | None) -> dict | None:
    if not crystal_type_id:
      return None
    return next((r for r in self.type_rows if r['crystal_type_id'] == crystal_type_id), None)

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

  def _ui_body(self) -> str | None:
    if self.state == 'RARITY':
      if not self.rarity_rows:
        return 'You do not have enough unattuned Crystals in any tier to Rematerialize (requires 10).'
      return 'This will Dematerialize 10 Crystals from the selected tier to Materialize 1 Crystal of the next tier.'

    if self.state == 'TYPE':
      if not self.type_rows:
        return 'No Crystal Types available for that rarity.'
      return None

    if self.state == 'QUANTITY':
      return 'Select how many Crystals to add to this Rematerialization.'

    if self.state == 'CONFIRM':
      return (
        f'Confirm to Dematerialize these Crystals and '
        f'Materialize 1 new `{self.cog.rarity_emoji(self.target_rarity_rank)} {self.cog.rarity_name(self.target_rarity_rank)}` Crystal.'
      )

    return None

  def _build_status_block(self) -> str:
    if self.state != 'CONFIRM':
      return ''

    src = f"{self.cog.rarity_emoji(self.source_rarity_rank)} {self.cog.rarity_name(self.source_rarity_rank)}"
    dst = f"{self.cog.rarity_emoji(self.target_rarity_rank)} {self.cog.rarity_name(self.target_rarity_rank)}"
    return f'## Rarity\n`{src}` to `{dst}`'

  def _selected_rows_sorted(self) -> list[dict]:
    rows = []
    for type_id, qty in self.contents.items():
      row = self._get_type_row(type_id)
      name = row['crystal_name'] if row else f'Type {type_id}'
      icon = row.get('icon') if row else None
      description = row.get('description') if row else ''
      rows.append({
        'crystal_type_id': type_id,
        'qty': qty,
        'crystal_name': name,
        'icon': icon,
        'description': description
      })
    return sorted(rows, key=lambda r: r['crystal_name'].lower())

  def _build_selected_header(self) -> str:
    return f'## Selected ({self._contents_total()}/{self.contents_target})'

  def _build_selected_sections(self, container: discord.ui.Container) -> list[discord.File]:
    files: list[discord.File] = []

    if self._contents_total() > 0:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(self._build_selected_header()))

    selected = self._selected_rows_sorted()
    if not selected:
      # Show a gif when the queue is empty (Selected (0/10))
      try:
        container.add_gallery(
          discord.MediaGalleryItem(
            url='https://i.imgur.com/rtlG2aV.gif',
            description='No crystals queued yet'
          )
        )
      except Exception:
        pass

      return files

    for r in selected:
      name = r['crystal_name']
      qty = r['qty']
      icon = r.get('icon')
      description = r.get('description') or ''

      text = f'### {name} (*x{qty}*)\n{description}'.strip()

      if icon:
        icon_path = f'./images/templates/crystals/icons/{icon}'
        filename = f"crystal_type_{r['crystal_type_id']}.png"

        try:
          files.append(discord.File(icon_path, filename=filename))

          thumb = discord.ui.Thumbnail(
            url=f'attachment://{filename}',
            description=name
          )

          section = discord.ui.Section(
            discord.ui.TextDisplay(text),
            accessory=thumb
          )

          container.add_item(section)
          continue
        except Exception:
          pass

      container.add_item(discord.ui.TextDisplay(text))

    return files

  def _build_selected_type_section(self, container: discord.ui.Container) -> list[discord.File]:
    files: list[discord.File] = []

    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay('## Selected Crystal Type'))

    row = self._get_type_row(self.selected_crystal_type_id)
    if not row:
      return files

    name = row.get('crystal_name') or 'Unknown Crystal Type'
    description = row.get('description') or ''
    icon = row.get('icon')

    text = f'### {name}\n{description}'.strip()

    if icon:
      icon_path = f'./images/templates/crystals/icons/{icon}'
      filename = f"crystal_type_{row['crystal_type_id']}.png"

      try:
        files.append(discord.File(icon_path, filename=filename))

        thumb = discord.ui.Thumbnail(
          url=f'attachment://{filename}',
          description=name
        )

        section = discord.ui.Section(
          discord.ui.TextDisplay(text),
          accessory=thumb
        )

        container.add_item(section)
        return files
      except Exception:
        pass

    container.add_item(discord.ui.TextDisplay(text))
    return files

  def _build_container(self) -> tuple[discord.ui.Container, list[discord.File]]:
    container = discord.ui.Container(color=discord.Color.teal().value)
    files: list[discord.File] = []

    header_lines = [f'# {self._ui_title()}']
    if self.notice:
      header_lines.append(f'Note: {self.notice}')
    container.add_item(discord.ui.TextDisplay('\n'.join(header_lines)))

    # Media gallery ONLY on initial rarity screen
    if self.state == 'RARITY':
      container.add_item(discord.ui.Separator())
      container.add_gallery(
        discord.MediaGalleryItem(
          url='https://i.imgur.com/YSwvM4T.gif',
          description='Crystal Rematerialization'
        )
      )

    status = self._build_status_block()
    if status:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(status))

    if self.state in ('TYPE', 'CONFIRM'):
      files.extend(self._build_selected_sections(container))
    elif self.state == 'QUANTITY':
      files.extend(self._build_selected_type_section(container))

    body = self._ui_body()
    if body:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(body))

    if self.state == 'TYPE' and self._type_total_pages() > 1:
      container.add_item(
        discord.ui.TextDisplay(
          f'Page {self.type_page + 1}/{self._type_total_pages()}'
        )
      )

    return container, files

  def _build_end_container(self, title: str, body: str, color: discord.Color) -> discord.ui.Container:
    container = discord.ui.Container(color=color.value)
    container.add_item(discord.ui.TextDisplay(f'# {title}'))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(body))
    return container

  def _render_end_state_ui(self, title: str, body: str):
    self._clear_components()
    self.add_item(self._build_end_container(title, body, discord.Color.dark_grey()))
    self.disable_all_items()

  def _build_rarity_select_options(self) -> list[discord.SelectOption]:
    opts = []
    for row in self.rarity_rows:
      source_rank = row['rarity_rank']
      label = row['name']
      emoji = row.get('emoji')
      desc = f"Unattuned: {row['count']}"
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
      desc = f'Available: {shown}'

      opts.append(discord.SelectOption(label=label, value=value, description=desc, emoji=emoji))

    if not opts:
      opts.append(discord.SelectOption(
        label='No Crystal Types available',
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
      back_btn = discord.ui.Button(label='❮ Back', style=discord.ButtonStyle.secondary)
      back_btn.callback = self._on_back
      row.add_item(back_btn)

    can_remove = bool(self.rematerialization_id) and self._contents_total() > 0 and self.state == 'TYPE'
    if can_remove:
      rm_btn = discord.ui.Button(label='Remove Last Batch Added', style=discord.ButtonStyle.secondary)
      rm_btn.callback = self._on_remove_last
      row.add_item(rm_btn)

    cancel_btn = discord.ui.Button(label='Cancel', style=discord.ButtonStyle.danger)
    cancel_btn.callback = self._on_cancel
    row.add_item(cancel_btn)

    if self.state == 'CONFIRM':
      confirm_btn = discord.ui.Button(label='Confirm', style=discord.ButtonStyle.primary)
      confirm_btn.disabled = (self._contents_total() != self.contents_target)
      confirm_btn.callback = self._on_confirm
      row.add_item(confirm_btn)

    container.add_item(discord.ui.Separator())
    container.add_item(row)

  def _rebuild(self) -> list[discord.File]:
    self._clear_components()
    container, files = self._build_container()

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
      return files

    if self.state == 'TYPE':
      # Hide dropdown/pager if already full (eg user hit Back from CONFIRM)
      if self._contents_total() < self.contents_target:
        select = discord.ui.Select(
          placeholder='Select a Crystal Type to Add',
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
      else:
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
          f'You are at {self._contents_total()}/{self.contents_target}. Remove Last Batch Added to make space.'
        ))

      self._add_footer_row(container)
      self.add_item(container)
      return files

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
      return files

    if self.state == 'CONFIRM':
      self._add_footer_row(container)
      self.add_item(container)
      return files

    self._add_footer_row(container)
    self.add_item(container)
    return files

  async def _swap_message_with_files(self, interaction: discord.Interaction, files: list[discord.File]):
    try:
      await interaction.response.defer(ephemeral=True)
    except Exception:
      pass

    try:
      new_msg = await interaction.followup.send(view=self, files=files, ephemeral=True)
    except TypeError:
      if len(files) == 1:
        new_msg = await interaction.followup.send(view=self, file=files[0], ephemeral=True)
      else:
        new_msg = await interaction.followup.send(view=self, ephemeral=True)

    try:
      await interaction.message.delete()
    except Exception:
      pass

    self.message = new_msg

  async def _render(self, interaction: discord.Interaction):
    files = self._rebuild()

    if files:
      await self._swap_message_with_files(interaction, files)
      return

    # If we have a stored message, edit it and return.
    if self.message:
      try:
        await self.message.edit(view=self)
        return
      except discord.NotFound:
        self.message = None
      except Exception:
        logger.error(traceback.format_exc())
        return

    # No stored message: if interaction response not done, edit it.
    if not interaction.response.is_done():
      try:
        await interaction.response.edit_message(view=self)
        return
      except Exception:
        pass

    # Last resort: followup and store it.
    try:
      self.message = await interaction.followup.send(view=self, ephemeral=True)
    except Exception:
      pass


  async def start(self, ctx: discord.ApplicationContext):
    files = self._rebuild()

    try:
      if files:
        await ctx.interaction.edit_original_response(view=self, attachments=files)
      else:
        await ctx.interaction.edit_original_response(view=self)
      self.message = await ctx.interaction.original_response()
      return
    except Exception:
      pass

    # Fallback: followup
    try:
      if files:
        self.message = await ctx.followup.send(view=self, files=files, ephemeral=True)
      else:
        self.message = await ctx.followup.send(view=self, ephemeral=True)
    except TypeError:
      if files and len(files) == 1:
        self.message = await ctx.followup.send(view=self, file=files[0], ephemeral=True)
      else:
        self.message = await ctx.followup.send(view=self, ephemeral=True)

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

  async def _refresh_type_rows(self):
    if not self.source_rarity_rank:
      return

    self.type_rows = await db_get_user_unattuned_crystal_type_counts_by_rarity_rank(
      self.user_discord_id,
      self.source_rarity_rank
    )

    self.type_page = min(self.type_page, max(0, self._type_total_pages() - 1))

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

  async def _add_instances_to_session(self, interaction: discord.Interaction, crystal_type_id: int, add_qty: int):
    ids = await self._select_instance_ids(crystal_type_id, add_qty)
    if len(ids) < add_qty:
      await db_cancel_rematerialization(self.rematerialization_id)
      self.rematerialization_id = None
      await self._hard_stop(
        interaction,
        'Inventory Changed',
        'Your Crystal inventory changed. The session was cancelled. Please run `/rematerialize engage` again.',
        discord.Color.orange()
      )
      return False

    for cid in ids:
      await db_add_crystal_to_rematerialization(self.rematerialization_id, cid)
      self.selected_instance_ids.add(cid)

    self.contents[crystal_type_id] = self.contents.get(crystal_type_id, 0) + len(ids)

    await self._refresh_type_rows()
    return True

  async def _on_select_rarity(self, interaction: discord.Interaction):
    self.notice = None

    source_rank = int(interaction.data['values'][0])
    self.source_rarity_rank = source_rank
    self.target_rarity_rank = source_rank + 1

    self.contents = {}
    self.selected_instance_ids = set()
    self.type_page = 0

    if self.rematerialization_id:
      await db_cancel_rematerialization(self.rematerialization_id)
      self.rematerialization_id = None

    self.rematerialization_id = await db_create_rematerialization(
      self.user_discord_id,
      self.source_rarity_rank,
      self.target_rarity_rank
    )

    await self._refresh_type_rows()

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
    row = self._get_type_row(crystal_type_id)
    if not row:
      await self._render(interaction)
      return

    effective = self._effective_available_for_row(row)
    remaining = self._contents_remaining()
    max_pick = min(effective, remaining)
    if max_pick <= 0:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active Rematerialization session was found. Please run `/rematerialize engage` again.',
        discord.Color.red()
      )
      return

    if effective == 1 and remaining > 0:
      ok = await self._add_instances_to_session(interaction, crystal_type_id, 1)
      if not ok:
        return

      self.state = 'CONFIRM' if self._contents_total() >= self.contents_target else 'TYPE'
      await self._render(interaction)
      return

    self.selected_crystal_type_id = crystal_type_id
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
        'No active Rematerialization session was found. Please run `/rematerialize engage` again.',
        discord.Color.red()
      )
      return

    remaining = self._contents_remaining()
    add_qty = min(qty, remaining)

    row = self._get_type_row(self.selected_crystal_type_id)
    if not row:
      await self._render(interaction)
      return

    effective = self._effective_available_for_row(row)
    add_qty = min(add_qty, effective)

    if add_qty <= 0:
      await self._render(interaction)
      return

    ok = await self._add_instances_to_session(interaction, self.selected_crystal_type_id, add_qty)
    if not ok:
      return

    self.selected_crystal_type_id = None
    self.selected_type_effective_available = 0

    self.state = 'CONFIRM' if self._contents_total() >= self.contents_target else 'TYPE'
    await self._render(interaction)

  async def _on_remove_last(self, interaction: discord.Interaction):
    self.notice = None

    if not self.rematerialization_id:
      self.notice = 'No active session.'
      await self._render(interaction)
      return

    removed = await db_remove_last_rematerialization_type_batch(self.rematerialization_id)
    if not removed:
      self.notice = 'Nothing to remove.'
      await self._render(interaction)
      return

    tid = removed[0]['crystal_type_id']

    removed_count = 0
    for row in removed:
      cid = row['crystal_instance_id']
      if cid in self.selected_instance_ids:
        self.selected_instance_ids.remove(cid)
      removed_count += 1

    if tid in self.contents:
      self.contents[tid] = max(0, self.contents[tid] - removed_count)
      if self.contents[tid] <= 0:
        del self.contents[tid]

    if self.state == 'CONFIRM' and self._contents_total() < self.contents_target:
      self.state = 'TYPE'

    await self._refresh_type_rows()

    row = self._get_type_row(tid)
    type_name = row['crystal_name'] if row else 'that type'
    self.notice = f'Removed {removed_count}x from {type_name}.'
    await self._render(interaction)

  async def _on_back(self, interaction: discord.Interaction):
    self.notice = None

    if self.state == 'QUANTITY':
      self.selected_crystal_type_id = None
      self.selected_type_effective_available = 0
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

    self.rematerialization_id = None
    self.contents = {}
    self.selected_instance_ids = set()

    self._render_end_state_ui('Rematerialization Cancelled', 'Session ended. No changes were made.')
    await interaction.response.edit_message(view=self)

  async def _post_public_animation(
    self,
    *,
    session_id: int,
    items: list[dict],
    created_crystal: dict,
    icon_bytes: bytes | None,
    source_rarity_text: str,
    target_rarity_text: str,
    display_name: str,
    user_mention: str
  ):
    try:
      channel_id = get_channel_id('gelrak-v')
      gelrak_v = self.cog.bot.get_channel(channel_id)
      if not gelrak_v:
        gelrak_v = await self.cog.bot.fetch_channel(channel_id)

      pile_buf = None
      try:
        bg_path = './images/templates/rematerialize/rematerializer.png'
        with Image.open(bg_path) as bg:
          canvas_size = bg.size

        seed = abs(hash(str(session_id))) % (2**31)

        pile_buf = await asyncio.to_thread(
          build_rematerialization_pile_bytes,
          items=items,
          canvas_size=canvas_size,
          seed=seed
        )

        try:
          pile_buf.seek(0)
        except Exception:
          pass
      except Exception:
        logger.error(traceback.format_exc())
        pile_buf = None

      anim_buf = None
      icon_name = created_crystal.get('icon')
      if pile_buf and icon_name:
        result_path = f'./images/templates/crystals/icons/{icon_name}'
        if os.path.exists(result_path):
          try:
            anim_buf = await build_rematerialization_success_animation(
              pile_bytes=pile_buf,
              result_crystal_path=result_path
            )
            try:
              anim_buf.seek(0)
            except Exception:
              pass
          except Exception:
            logger.error(traceback.format_exc())
            anim_buf = None

      if not anim_buf:
        return

      result_id = created_crystal['crystal_type_id']
      result_name = created_crystal['crystal_name']
      result_icon = created_crystal['icon']
      result_description = created_crystal.get('description') or ''
      result_text = f'### {result_name}\n{result_description}'.strip()

      result_filename = f'crystal_type_{result_id}.png'
      animation_filename = f'rematerialization_{session_id}.webp'

      try:
        anim_buf.seek(0)
      except Exception:
        pass
      animation_file = discord.File(anim_buf, filename=animation_filename)

      public_view = discord.ui.DesignerView(timeout=None, store=False)

      container = discord.ui.Container(color=discord.Color.green().value)
      container.add_item(discord.ui.TextDisplay(
        f'# {display_name} CRYSTAL REMATERIALIZATION\n'
        f'{user_mention} has converted **{self.contents_target}** {source_rarity_text} Crystals '
        f'into a new {target_rarity_text} Crystal!'
      ))

      public_thumb = discord.ui.Thumbnail(
        url=f'attachment://{result_filename}',
        description=result_name
      )
      public_section = discord.ui.Section(
        discord.ui.TextDisplay(result_text),
        accessory=public_thumb
      )
      container.add_item(discord.ui.Separator())
      container.add_item(public_section)

      container.add_item(discord.ui.Separator())
      container.add_gallery(
        discord.MediaGalleryItem(
          url=f'attachment://{animation_filename}',
          description='Rematerialization Sequence'
        )
      )

      public_view.add_item(container)

      public_files = [animation_file]

      if icon_bytes:
        buf2 = io.BytesIO(icon_bytes)
        try:
          buf2.seek(0)
        except Exception:
          pass
        public_files.append(discord.File(buf2, filename=result_filename))
      else:
        # If we failed to read icon_bytes earlier, try a last-resort disk read
        try:
          result_filepath = f'./images/templates/crystals/icons/{result_icon}'
          with open(result_filepath, 'rb') as f:
            b = f.read()
          buf2 = io.BytesIO(b)
          buf2.seek(0)
          public_files.append(discord.File(buf2, filename=result_filename))
        except Exception:
          pass

      await gelrak_v.send(
        view=public_view,
        files=public_files
      )
    except Exception:
      logger.info(traceback.format_exc())
      return

  async def _on_confirm(self, interaction: discord.Interaction):
    self.notice = None

    try:
      await interaction.response.defer(ephemeral=True)
    except Exception as e:
      logger.info(traceback.format_exc())
      pass

    self.disable_all_items()
    if self.message:
      try:
        await self.message.edit(view=self)
      except discord.NotFound:
        self.message = None
      except Exception:
        logger.error(traceback.format_exc())

    if self._contents_total() != self.contents_target:
      await self._render(interaction)
      return

    if not self.rematerialization_id:
      await self._hard_stop(
        interaction,
        'Rematerialization Error',
        'No active Rematerialization session was found. Please run `/rematerialize engage` again.',
        discord.Color.red()
      )
      return

    session_id = self.rematerialization_id

    items = await db_get_rematerialization_items(session_id)

    for it in items:
      if str(it['owner_discord_id']) != self.user_discord_id:
        await db_cancel_rematerialization(session_id)
        self.rematerialization_id = None
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your Crystal inventory changed. The session was cancelled. Please run `/rematerialize engage` again.',
          discord.Color.orange()
        )
        return
      if it['crystal_status'] != 'available':
        await db_cancel_rematerialization(session_id)
        self.rematerialization_id = None
        await self._hard_stop(
          interaction,
          'Inventory Changed',
          'Your Crystal inventory changed. The session was cancelled. Please run `/rematerialize engage` again.',
          discord.Color.orange()
        )
        return
      if it['rarity_rank'] != self.source_rarity_rank:
        await db_cancel_rematerialization(session_id)
        self.rematerialization_id = None
        await self._hard_stop(
          interaction,
          'Session Invalid',
          'This Rematerialization session is no longer valid and was cancelled. Please run `/rematerialize engage` again.',
          discord.Color.orange()
        )
        return

    if len(items) != self.contents_target:
      self._rehydrate_from_items(items)
      await self._refresh_type_rows()
      self.state = 'CONFIRM' if self._contents_total() >= self.contents_target else 'TYPE'
      self.notice = 'Your selection was refreshed. Please confirm again.'
      await self._render(interaction)
      return

    all_ids = [it['crystal_instance_id'] for it in items]

    await db_mark_crystals_dematerialized(all_ids)

    crystal_type = await db_select_random_crystal_type_by_rarity_rank(self.target_rarity_rank)
    if not crystal_type:
      await db_cancel_rematerialization(session_id)
      self.rematerialization_id = None
      await self._hard_stop(
        interaction,
        'Rematerialization Failed',
        'No Crystal Types exist for the target rarity. The session was cancelled.',
        discord.Color.red()
      )
      return

    created_crystal = await create_new_crystal_instance(
      self.user_discord_id,
      crystal_type['id'],
      event_type='rematerialization'
    )

    await db_finalize_rematerialization(session_id)

    result_id = created_crystal['crystal_type_id']
    result_name = created_crystal['crystal_name']
    result_icon = created_crystal['icon']
    result_description = created_crystal.get('description') or ''
    result_text = f'### {result_name}\n{result_description}'.strip()

    result_filepath = f'./images/templates/crystals/icons/{result_icon}'
    result_filename = f'crystal_type_{result_id}.png'

    icon_bytes = None
    try:
      with open(result_filepath, 'rb') as f:
        icon_bytes = f.read()
    except Exception:
      icon_bytes = None

    source_rarity_text = f"`{self.cog.rarity_emoji(self.source_rarity_rank)} {self.cog.rarity_name(self.source_rarity_rank)}`"
    target_rarity_text = f"`{self.cog.rarity_emoji(self.target_rarity_rank)} {self.cog.rarity_name(self.target_rarity_rank)}`"

    # Build success UI immediately and swap message right now.
    self.rematerialization_id = None
    self.contents = {}
    self.selected_instance_ids = set()
    self._clear_components()

    success = discord.ui.Container(color=discord.Color.green().value)
    success.add_item(discord.ui.TextDisplay(
      '# REMATERIALIZATION COMPLETE!\n'
      f'Dematerialized {self.contents_target} {source_rarity_text} Crystals and '
      f'Materialized a new **{created_crystal["crystal_name"]}** Crystal at {target_rarity_text}!'
    ))

    result_thumb = discord.ui.Thumbnail(
      url=f'attachment://{result_filename}',
      description=result_name
    )
    result_section = discord.ui.Section(
      discord.ui.TextDisplay(result_text),
      accessory=result_thumb
    )
    success.add_item(result_section)

    self.add_item(success)
    self.disable_all_items()

    ephemeral_files = []
    if icon_bytes:
      buf = io.BytesIO(icon_bytes)
      try:
        buf.seek(0)
      except Exception:
        pass
      ephemeral_files = [discord.File(buf, filename=result_filename)]

    await self._swap_message_with_files(interaction, ephemeral_files)

    # Kick off public animation work without blocking the user.
    # Do NOT reference the interaction object inside the task.
    display_name = interaction.user.display_name
    user_mention = self.user.mention

    self.cog.bot.loop.create_task(
      self._post_public_animation(
        session_id=session_id,
        items=items,
        created_crystal=created_crystal,
        icon_bytes=icon_bytes,
        source_rarity_text=source_rarity_text,
        target_rarity_text=target_rarity_text,
        display_name=display_name,
        user_mention=user_mention
      )
    )


class Rematerialization(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  rematerialize = discord.SlashCommandGroup('rematerialize', 'Crystal Rematerialization Commands.')

  def rarity_name(self, rarity_rank: int) -> str:
    return {
      1: 'Common',
      2: 'Uncommon',
      3: 'Rare',
      4: 'Legendary',
      5: 'Mythic'
    }.get(rarity_rank) or f'Rank {rarity_rank}'

  def rarity_emoji(self, rarity_rank: int) -> str:
    return {
      1: '⚪',
      2: '🟢',
      3: '🟣',
      4: '🔥',
      5: '💎'
    }.get(rarity_rank) or ''

  @rematerialize.command(name='select', description='Exchange 10 Crystals for 1 of the next Rarity!')
  @commands.check(access_check)
  async def select(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
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
          description='Your active Rematerialization session was invalid (inventory changed). Please run `/rematerialize engage` again.',
          color=discord.Color.orange()
        ),
        ephemeral=True
      )
      return

    view._rehydrate_from_items(items)
    await view._refresh_type_rows()

    view.state = 'CONFIRM' if view._contents_total() >= view.contents_target else 'TYPE'
    view.notice = 'Resumed your active Rematerialization session.'
    await view.start(ctx)
