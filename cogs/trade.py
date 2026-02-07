import io
import json

from common import *

from queries.badge_instances import db_get_user_badge_instances
from queries.crystal_instances import db_get_attuned_crystals
from queries.echelon_xp import db_get_echelon_progress
from queries.trade import *
from queries.wishlists import db_get_wishlist_matches

from utils.badge_trades import *
from utils.check_channel_access import access_check
from utils.image_utils import *
from utils.prestige import PRESTIGE_TIERS, autocomplete_prestige_tiers, is_prestige_valid
from utils.string_utils import strip_bullshit


# cogs.trade

with open("./data/rules_of_acquisition.txt", "r") as f:
  rules_of_acquisition = f.read().split("\n")


def _trade_color_ok() -> discord.Color:
  # Unified non-error color for Trade UX.
  return discord.Color.dark_purple()


def _trade_color_error() -> discord.Color:
  return discord.Color.red()


def _pick_active_crystal(
  crystals: list[dict] | None,
  *,
  active_crystal_id: int | None
) -> dict | None:
  """
  Select the slotted/active crystal for a badge instance.

  Per schema:
  - badge_instances.active_crystal_id -> crystal_instances.id
  """
  if not crystals:
    return None

  try:
    active_id = int(active_crystal_id or 0)
  except Exception:
    active_id = 0

  if not active_id:
    return None

  for c in crystals:
    try:
      cid = c.get("id")
      if cid is None:
        cid = c.get("crystal_instance_id")
      cid = int(cid or 0)
    except Exception:
      cid = 0

    if cid == active_id:
      return c

  return None

async def trade_has_attuned_crystals(active_trade: dict) -> bool:
  """
  Returns True if any badge instance in the trade has 1+ attuned crystals.
  """
  if not active_trade:
    return False

  try:
    offered = await db_get_trade_offered_badge_instances(active_trade)
  except Exception:
    offered = []

  try:
    requested = await db_get_trade_requested_badge_instances(active_trade)
  except Exception:
    requested = []

  for b in (offered or []) + (requested or []):
    try:
      badge_instance_id = int(b.get("badge_instance_id") or 0)
    except Exception:
      badge_instance_id = 0

    if not badge_instance_id:
      continue

    try:
      crystals = await db_get_attuned_crystals(badge_instance_id)
    except Exception:
      crystals = []

    if crystals:
      return True

  return False


async def autocomplete_use_matches(ctx: discord.AutocompleteContext):
  """
  Autocomplete for the 'use_matches' option.

  - If a valid wishlist match with addable badges exists for the selected partner at the chosen prestige:
    return Yes/No
  - If partner is selected but prestige is not:
    return [ Select Prestige First ]
  - Otherwise:
    return N/A (treated as no-op / standard badge lists)

  Works for both /trade start (uses requestee + prestige) and /trade propose (uses active trade).
  """
  requestor_id = ctx.interaction.user.id

  partner_id = None
  prestige_level = None

  if "requestee" in ctx.options:
    partner = ctx.options.get("requestee")
    try:
      partner_id = int(getattr(partner, "id", partner))
    except Exception:
      partner_id = None

  if "prestige" in ctx.options:
    try:
      prestige_level = int(ctx.options.get("prestige"))
    except Exception:
      prestige_level = None

  if partner_id is None or prestige_level is None:
    active_trade = await db_get_active_requestor_trade(requestor_id)
    if active_trade:
      partner_id = partner_id or int(active_trade.get("requestee_id"))
      try:
        prestige_level = prestige_level if prestige_level is not None else int(active_trade.get("prestige_level"))
      except Exception:
        prestige_level = None

  if partner_id is not None and prestige_level is None:
    return [discord.OptionChoice(name="[ Select Prestige First ]", value="na")]

  if partner_id is None or prestige_level is None:
    return [discord.OptionChoice(name="N/A", value="na")]

  matches = await db_get_wishlist_matches(str(requestor_id), int(prestige_level))
  match_row = next((m for m in matches if str(m.get("match_discord_id")) == str(partner_id)), None)
  if not match_row:
    return [discord.OptionChoice(name="N/A", value="na")]

  try:
    you_want = set(json.loads(match_row.get("badge_ids_you_want_that_they_have") or "[]"))
    they_want = set(json.loads(match_row.get("badge_ids_they_want_that_you_have") or "[]"))
  except Exception:
    you_want, they_want = set(), set()

  if you_want or they_want:
    return [
      discord.OptionChoice(name="Yes", value="yes"),
      discord.OptionChoice(name="No", value="no"),
    ]

  return [discord.OptionChoice(name="N/A", value="na")]


async def autocomplete_offering_badges(ctx: discord.AutocompleteContext):
  requestor_user_id = ctx.interaction.user.id

  requestee_user_id = None
  prestige_level = None
  offered_instance_ids = set()

  if "requestee" in ctx.options and "prestige" in ctx.options:
    partner = ctx.options.get("requestee")
    try:
      requestee_user_id = int(getattr(partner, "id", partner))
    except Exception:
      requestee_user_id = None

    prestige = ctx.options.get("prestige")
    try:
      prestige_level = int(prestige)
    except Exception:
      return [discord.OptionChoice(name="[ Invalid Prestige ]", value="none")]
  else:
    active_trade = await db_get_active_requestor_trade(requestor_user_id)
    if active_trade:
      requestee_user_id = int(active_trade["requestee_id"])
      prestige_level = int(active_trade["prestige_level"])
      offered_instances = await db_get_trade_offered_badge_instances(active_trade)
      offered_instance_ids = {b["badge_instance_id"] for b in offered_instances}
    else:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

  requestor_instances = await db_get_user_badge_instances(requestor_user_id, prestige=prestige_level)
  requestee_instances = await db_get_user_badge_instances(requestee_user_id, prestige=prestige_level)

  requestee_filenames = {b["badge_filename"] for b in requestee_instances}

  use_matches = str(ctx.options.get("use_matches", "no")).lower() == "yes"
  matched_badge_info_ids = None
  if use_matches:
    matches = await db_get_wishlist_matches(str(requestor_user_id), int(prestige_level))
    match_row = next((m for m in matches if str(m.get("match_discord_id")) == str(requestee_user_id)), None)
    if not match_row:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

    matched_badge_info_ids = set(json.loads(match_row.get("badge_ids_they_want_that_you_have") or "[]"))
    if not matched_badge_info_ids:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

  results = []
  for b in requestor_instances:
    if b["special"]:
      continue
    if b["badge_filename"] in requestee_filenames:
      continue
    if b["badge_instance_id"] in offered_instance_ids:
      continue
    if matched_badge_info_ids is not None and b.get("badge_info_id") not in matched_badge_info_ids:
      continue
    results.append(discord.OptionChoice(name=b["badge_name"], value=str(b["badge_instance_id"])))

  filtered = [r for r in results if strip_bullshit(ctx.value.lower()) in strip_bullshit(r.name.lower())]
  if not filtered:
    return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]
  return filtered[:25]


async def autocomplete_requesting_badges(ctx: discord.AutocompleteContext):
  requestor_user_id = ctx.interaction.user.id

  requestee_user_id = None
  prestige_level = None
  requested_instance_ids = set()

  if "requestee" in ctx.options and "prestige" in ctx.options:
    partner = ctx.options.get("requestee")
    try:
      requestee_user_id = int(getattr(partner, "id", partner))
    except Exception:
      requestee_user_id = None

    prestige = ctx.options.get("prestige")
    try:
      prestige_level = int(prestige)
    except Exception:
      return [discord.OptionChoice(name="[ Invalid Prestige ]", value="none")]
  else:
    active_trade = await db_get_active_requestor_trade(requestor_user_id)
    if active_trade:
      requestee_user_id = int(active_trade["requestee_id"])
      prestige_level = int(active_trade["prestige_level"])
      requested_instances = await db_get_trade_requested_badge_instances(active_trade)
      requested_instance_ids = {b["badge_instance_id"] for b in requested_instances}
    else:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

  requestor_instances = await db_get_user_badge_instances(requestor_user_id, prestige=prestige_level)
  requestee_instances = await db_get_user_badge_instances(requestee_user_id, prestige=prestige_level)

  requestor_filenames = {b["badge_filename"] for b in requestor_instances}

  matched_badge_info_ids = None
  use_matches = str(ctx.options.get("use_matches", "no")).lower() == "yes"
  if use_matches:
    matches = await db_get_wishlist_matches(str(requestor_user_id), int(prestige_level))
    match_row = next((m for m in matches if str(m.get("match_discord_id")) == str(requestee_user_id)), None)
    if not match_row:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

    matched_badge_info_ids = set(json.loads(match_row.get("badge_ids_you_want_that_they_have") or "[]"))
    if not matched_badge_info_ids:
      return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]

  results = []
  for b in requestee_instances:
    if b["special"]:
      continue
    if b["badge_filename"] in requestor_filenames:
      continue
    if b["badge_instance_id"] in requested_instance_ids:
      continue
    if matched_badge_info_ids is not None and b.get("badge_info_id") not in matched_badge_info_ids:
      continue
    results.append(discord.OptionChoice(name=b["badge_name"], value=str(b["badge_instance_id"])))

  filtered = [r for r in results if strip_bullshit(ctx.value.lower()) in strip_bullshit(r.name.lower())]
  if not filtered:
    return [discord.OptionChoice(name="[ No Valid Options ]", value="none")]
  return filtered[:25]


# ___________                  .___       _________ __          __               ____   ____.__
# \__    ___/___________     __| _/____  /   _____//  |______ _/  |_ __ __  _____\   \ /   /|__| ______  _  __
#   |    |  \_  __ \__  \   / __ |/ __ \ \_____  \\   __\__  \\   __\  |  \/  ___/\   Y   / |  |/ __ \ \/ \/ /
#   |    |   |  | \// __ \_/ /_/ \  ___/ /        \|  |  / __ \|  | |  |  /\___ \  \     /  |  \  ___/\     /
#   |____|   |__|  (____  /\____ |\___  >_______  /|__| (____  /__| |____//____  >  \___/   |__|\___  >\/\_/
#                       \/      \/    \/        \/           \/                \/                   \/
class TradeStatusView(discord.ui.DesignerView):
  HOME_ASSET_DIR = "./images/trades/assets"

  def __init__(
    self,
    *,
    cog,
    active_trade: dict,
    mode: str
  ):
    super().__init__(timeout=360)

    self.cog = cog
    self.active_trade = active_trade
    self.mode = mode  # incoming | outgoing | view_only

    self.pages: list[dict] = []
    self.page = 0

    self._interaction_lock = asyncio.Lock()
    self._ack = False
    self._ui_locked = False
    self.message = None

  async def start(self, interaction: discord.Interaction):
    await self._build_pages()
    await self._render(interaction, first=True)

  async def _build_pages(self):
    requestor = None
    requestee = None
    try:
      requestor = await self.cog.bot.current_guild.fetch_member(self.active_trade["requestor_id"])
    except Exception:
      requestor = None

    try:
      requestee = await self.cog.bot.current_guild.fetch_member(self.active_trade["requestee_id"])
    except Exception:
      requestee = None

    prestige_tier = PRESTIGE_TIERS.get(int(self.active_trade.get("prestige_level") or 0)) or "Unknown"

    offered_instances = await db_get_trade_offered_badge_instances(self.active_trade)
    requested_instances = await db_get_trade_requested_badge_instances(self.active_trade)

    requestor_id = str(self.active_trade.get("requestor_id") or "")
    requestee_id = str(self.active_trade.get("requestee_id") or "")

    offered_meta = await self._build_badge_meta(offered_instances, owner_id=requestor_id)
    requested_meta = await self._build_badge_meta(requested_instances, owner_id=requestee_id)

    has_any_crystals = any((m.get("crystal_count") or 0) > 0 for m in (offered_meta + requested_meta))

    offered_names = "\n".join([
      f"- {m['badge_name']}{' `(⚠️)`' if (m.get('crystal_count') or 0) > 0 else ''}"
      for m in offered_meta
    ]) or "(none)"

    requested_names = "\n".join([
      f"- {m['badge_name']}{' `(⚠️)`' if (m.get('crystal_count') or 0) > 0 else ''}"
      for m in requested_meta
    ]) or "(none)"

    home_asset = "trade_offer.png" if self.active_trade.get("status") == "active" else "trade_pending.png"
    home_path = f"{self.HOME_ASSET_DIR}/{home_asset}"
    home_bytes = self._read_file_bytes(home_path)

    self.pages = [
      {
        "key": "home",
        "title": "Trade Summary",
        "prestige_tier": prestige_tier,
        "requestor_mention": requestor.mention,
        "requestee_mention": requestee.mention,
        "offered_names": offered_names,
        "requested_names": requested_names,
        "has_any_crystals": has_any_crystals,
        "file_bytes": home_bytes,
        "filename": home_asset
      },
      {
        "key": "offered",
        "title": "Offered Badges",
        "badges": offered_meta,
        "requestor_mention": requestor.mention
      },
      {
        "key": "requested",
        "title": "Requested Badges",
        "badges": requested_meta,
        "requestee_mention": requestee.mention
      }
    ]

  async def _build_badge_meta(self, instances: list[dict], *, owner_id: str) -> list[dict]:
    out: list[dict] = []

    for b in (instances or []):
      badge_instance_id = int(b.get("badge_instance_id") or 0)
      badge_name = b.get("badge_name") or "Unknown Badge"

      crystals = []
      try:
        crystals = await db_get_attuned_crystals(badge_instance_id)
      except Exception:
        crystals = []

      crystal_count = len(crystals or [])

      slotted = _pick_active_crystal(crystals, active_crystal_id=b.get("active_crystal_id"))

      preview_bytes, preview_filename = await self._try_build_badge_preview_bytes(
        owner_id=owner_id,
        badge=b,
        badge_instance_id=badge_instance_id,
        crystal=slotted
      )

      out.append({
        "badge_instance_id": badge_instance_id,
        "badge_name": badge_name,
        "crystal_count": crystal_count,
        "thumb_bytes": preview_bytes,
        "thumb_filename": preview_filename
      })

    return out

  async def _try_build_badge_preview_bytes(
    self,
    *,
    owner_id: str,
    badge: dict,
    badge_instance_id: int,
    crystal: dict | None
  ) -> tuple[bytes | None, str | None]:
    if not owner_id or not badge_instance_id or not badge:
      return None, None

    try:
      file, _url = await generate_badge_preview(
        owner_id,
        badge,
        crystal=crystal,
        theme=None,
        disable_overlays=False
      )
      if not file:
        return None, None

      filename = getattr(file, "filename", None)
      fp = getattr(file, "fp", None)
      if not filename or not fp:
        return None, None

      try:
        fp.seek(0)
      except Exception:
        pass

      data = fp.read()
      if not data:
        return None, None

      ext = "png"
      try:
        if "." in filename:
          ext = filename.rsplit(".", 1)[-1].lower() or "png"
      except Exception:
        ext = "png"

      safe_name = f"trade_{badge_instance_id}_preview.{ext}"
      return data, safe_name
    except Exception:
      return None, None

  def _read_file_bytes(self, path: str | None) -> bytes | None:
    if not path:
      return None
    try:
      with open(path, "rb") as rf:
        return rf.read()
    except Exception:
      return None

  def _build_file_from_bytes(self, file_bytes: bytes | None, filename: str) -> discord.File | None:
    if not file_bytes or not filename:
      return None
    fp = io.BytesIO(file_bytes)
    try:
      fp.seek(0)
    except Exception:
      pass
    return discord.File(fp=fp, filename=filename)

  def _page_indicator_label(self) -> str:
    return f"{self.page + 1}/{len(self.pages)}"

  def _is_component_interaction(self, interaction: discord.Interaction | None) -> bool:
    try:
      return bool(interaction and getattr(interaction, "message", None))
    except Exception:
      return False

  async def _ack_interaction(self, interaction: discord.Interaction) -> bool:
    if interaction.response.is_done():
      return True

    if self._is_component_interaction(interaction):
      try:
        fn = getattr(interaction.response, "defer_update", None)
        if fn:
          await fn()
          return True
      except Exception:
        pass

    try:
      await interaction.response.defer(ephemeral=True)
      return True
    except TypeError:
      pass
    except Exception:
      return False
    try:
      await interaction.response.defer()
      return True
    except Exception:
      return False

  def _build_body_text(self, page: dict) -> str:
    key = page.get("key")
    if key != "home":
      return ""

    prestige_tier = page.get("prestige_tier") or "Unknown"
    requestor_mention = page.get("requestor_mention") or ""
    requestee_mention = page.get("requestee_mention") or ""

    if self.mode == "outgoing":
      header = f"You are making a ***{prestige_tier}*** offer to {requestee_mention} with the following..."
    else:
      header = f"{requestor_mention} has made you a ***{prestige_tier}*** offer involving the following..."

    lines = [
      header,
      "### Offered",
      page.get("offered_names") or "`(none)`",
      "### Requested",
      page.get("requested_names") or "`(none)`"
    ]
    return "\n".join([l for l in lines if l is not None]).strip()

  def _build_controls(self) -> tuple[discord.ui.ActionRow, discord.ui.ActionRow]:
    nav = discord.ui.ActionRow()

    nav_disabled = self._ui_locked or (len(self.pages) <= 1)

    prev_btn = discord.ui.Button(
      label="Prev",
      style=discord.ButtonStyle.secondary,
      disabled=nav_disabled
    )
    next_btn = discord.ui.Button(
      label="Next",
      style=discord.ButtonStyle.secondary,
      disabled=nav_disabled
    )
    indicator = discord.ui.Button(
      label=self._page_indicator_label(),
      style=discord.ButtonStyle.secondary,
      disabled=True
    )

    async def _nav(delta: int, interaction: discord.Interaction):
      async with self._interaction_lock:
        if self._ack:
          return
        self._ack = True
        try:
          ok = await self._lock_interaction(interaction)
          if not ok:
            return

          self.page = (self.page + delta) % len(self.pages)
          await self._render(interaction)
        finally:
          self._ack = False

    async def _prev_cb(interaction: discord.Interaction):
      await _nav(-1, interaction)

    async def _next_cb(interaction: discord.Interaction):
      await _nav(1, interaction)

    prev_btn.callback = _prev_cb
    next_btn.callback = _next_cb

    nav.add_item(prev_btn)
    nav.add_item(indicator)
    nav.add_item(next_btn)

    actions = discord.ui.ActionRow()

    close_btn = discord.ui.Button(
      label="Close",
      style=discord.ButtonStyle.secondary,
      disabled=self._ui_locked
    )

    async def _close_cb(interaction: discord.Interaction):
      async with self._interaction_lock:
        if self._ack:
          return
        self._ack = True
        try:
          ok = await self._lock_interaction(interaction)
          if not ok:
            return
        finally:
          try:
            await self._delete_message(interaction)
          except Exception:
            pass
          self._ack = False

    close_btn.callback = _close_cb
    actions.add_item(close_btn)

    if self.mode == "incoming":
      decline_btn = discord.ui.Button(
        label="Decline",
        style=discord.ButtonStyle.danger,
        disabled=self._ui_locked
      )
      accept_btn = discord.ui.Button(
        label="Accept",
        style=discord.ButtonStyle.blurple,
        disabled=self._ui_locked
      )

      async def _decline_cb(interaction: discord.Interaction):
        async with self._interaction_lock:
          if self._ack:
            return
          self._ack = True
          try:
            ok = await self._lock_interaction(interaction)
            if not ok:
              return
            await self.cog._decline_trade_callback(interaction, self.active_trade)
          finally:
            try:
              await self._delete_message(interaction)
            except Exception:
              pass
            self._ack = False

      async def _accept_cb(interaction: discord.Interaction):
        async with self._interaction_lock:
          if self._ack:
            return
          self._ack = True
          try:
            ok = await self._lock_interaction(interaction)
            if not ok:
              return
            await self.cog._accept_trade_callback(interaction, self.active_trade)
          finally:
            try:
              await self._delete_message(interaction)
            except Exception:
              pass
            self._ack = False

      decline_btn.callback = _decline_cb
      accept_btn.callback = _accept_cb

      actions.add_item(decline_btn)
      actions.add_item(accept_btn)

    if self.mode == "outgoing":
      cancel_btn = discord.ui.Button(
        label="Cancel Trade",
        style=discord.ButtonStyle.danger,
        disabled=self._ui_locked
      )
      send_btn = discord.ui.Button(
        label="Send",
        style=discord.ButtonStyle.primary,
        disabled=self._ui_locked
      )

      async def _send_cb(interaction: discord.Interaction):
        async with self._interaction_lock:
          if self._ack:
            return
          self._ack = True
          try:
            ok = await self._lock_interaction(interaction)
            if not ok:
              return
            await self.cog._send_trade_callback(interaction, self.active_trade)
          finally:
            try:
              await self._delete_message(interaction)
            except Exception:
              pass
            self._ack = False

      async def _cancel_cb(interaction: discord.Interaction):
        async with self._interaction_lock:
          if self._ack:
            return
          self._ack = True
          try:
            ok = await self._lock_interaction(interaction)
            if not ok:
              return
            await self.cog._cancel_trade_callback(interaction, self.active_trade)
          finally:
            try:
              await self._delete_message(interaction)
            except Exception:
              pass
            self._ack = False

      send_btn.callback = _send_cb
      cancel_btn.callback = _cancel_cb

      actions.add_item(cancel_btn)
      actions.add_item(send_btn)

    if self.mode == "view_only":
      cancel_btn = discord.ui.Button(
        label="Cancel Trade",
        style=discord.ButtonStyle.danger,
        disabled=self._ui_locked
      )

      async def _cancel_cb(interaction: discord.Interaction):
        async with self._interaction_lock:
          if self._ack:
            return
          self._ack = True
          try:
            ok = await self._lock_interaction(interaction)
            if not ok:
              return
            await self.cog._cancel_trade_callback(interaction, self.active_trade)
          finally:
            try:
              await self._delete_message(interaction)
            except Exception:
              pass
            self._ack = False

      cancel_btn.callback = _cancel_cb
      actions.add_item(cancel_btn)

    return nav, actions

  def _build_container_for_page(self, page: dict) -> discord.ui.Container:
    container = discord.ui.Container(color=_trade_color_ok().value)

    container.add_item(discord.ui.TextDisplay(f"# {page.get('title') or 'Trade'}"))
    container.add_item(discord.ui.Separator())

    key = page.get("key")

    if key == "home":
      container.add_item(discord.ui.TextDisplay(self._build_body_text(page)))
      container.add_item(discord.ui.Separator())

      if page.get("file_bytes") and page.get("filename"):
        try:
          container.add_gallery(
            discord.MediaGalleryItem(
              url=f"attachment://{page['filename']}",
              description="Trade"
            )
          )
        except Exception:
          pass

      if page.get("has_any_crystals"):
        container.add_item(discord.ui.TextDisplay(
          "This trade contains badges which have crystals attached `(indicated by ⚠️)`"
        ))

      container.add_item(discord.ui.Separator())
      nav_row, action_row = self._build_controls()
      container.add_item(nav_row)
      container.add_item(action_row)
      return container

    badges = page.get("badges") or []

    rendered_any = False
    for b in badges[:6]:
      title = b.get("badge_name") or "Unknown Badge"
      crystal_count = int(b.get("crystal_count") or 0)

      thumb_name = b.get("thumb_filename")
      has_thumb = bool(thumb_name and b.get("thumb_bytes"))

      if not has_thumb:
        container.add_item(discord.ui.TextDisplay(f"### {title}"))
        if crystal_count > 0:
          container.add_item(discord.ui.TextDisplay(
            f"There are {crystal_count} Crystals attuned to this badge!"
          ))
        container.add_item(discord.ui.Separator())
        rendered_any = True
        continue

      section = discord.ui.Section(
        discord.ui.TextDisplay(f"### {title}")
      )

      if crystal_count > 0:
        section.add_item(discord.ui.TextDisplay(
          f"There are {crystal_count} Crystals attuned to this badge!"
        ))

      section.set_thumbnail(
        url=f"attachment://{thumb_name}",
        description="Badge"
      )

      container.add_item(section)
      rendered_any = True

    if not rendered_any:
      container.add_item(discord.ui.TextDisplay("`(none)`"))

    container.add_item(discord.ui.Separator())
    nav_row, action_row = self._build_controls()
    container.add_item(nav_row)
    container.add_item(action_row)
    return container

  def _rebuild_view(self):
    page = self.pages[self.page]
    container = self._build_container_for_page(page)
    self.clear_items()
    self.add_item(container)

  def _build_files_for_page(self, page: dict) -> list[discord.File]:
    files: list[discord.File] = []

    if page.get("key") == "home":
      dfile = self._build_file_from_bytes(page.get("file_bytes"), page.get("filename") or "trade_home.png")
      if dfile:
        files.append(dfile)
      return files

    for b in (page.get("badges") or [])[:6]:
      thumb_bytes = b.get("thumb_bytes")
      thumb_name = b.get("thumb_filename")
      if not thumb_bytes or not thumb_name:
        continue

      dfile = self._build_file_from_bytes(thumb_bytes, thumb_name)
      if dfile:
        files.append(dfile)

    return files

  async def _lock_interaction(self, interaction: discord.Interaction) -> bool:
    self._ui_locked = True
    self._rebuild_view()

    if self._is_component_interaction(interaction) and not interaction.response.is_done():
      try:
        await interaction.response.edit_message(view=self)
        return True
      except Exception:
        pass

    try:
      msg = None
      try:
        msg = interaction.message if interaction else None
      except Exception:
        msg = None
      if not msg:
        msg = self.message
      if msg:
        await msg.edit(view=self)
    except Exception:
      pass

    return await self._ack_interaction(interaction)

  async def _unlock_new_message(self):
    self._ui_locked = False
    self._rebuild_view()
    try:
      if self.message:
        await self.message.edit(view=self)
    except Exception:
      pass

  async def _delete_message(self, interaction: discord.Interaction | None):
    msg = None
    try:
      msg = interaction.message if interaction else None
    except Exception:
      msg = None

    if not msg:
      msg = self.message

    if not msg:
      return

    try:
      await msg.delete()
      if msg == self.message:
        self.message = None
      return
    except Exception:
      pass

    try:
      if interaction:
        await interaction.followup.delete_message(msg.id)
        if msg == self.message:
          self.message = None
    except Exception:
      pass

  async def _render(self, interaction: discord.Interaction, *, first: bool = False):
    page = self.pages[self.page]
    files = self._build_files_for_page(page)

    self._rebuild_view()

    if first:
      self._ui_locked = False
      self._rebuild_view()

      try:
        if not interaction.response.is_done():
          await interaction.response.defer(ephemeral=True)
      except Exception:
        pass

      try:
        if files:
          try:
            self.message = await interaction.followup.send(view=self, files=files, ephemeral=True)
          except TypeError:
            if len(files) == 1:
              self.message = await interaction.followup.send(view=self, file=files[0], ephemeral=True)
            else:
              self.message = await interaction.followup.send(view=self, ephemeral=True)
        else:
          self.message = await interaction.followup.send(view=self, ephemeral=True)
      except Exception:
        logger.exception("[trade] TradeStatusView:_render:first send failed")
      return

    try:
      await self._delete_message(interaction)
    except Exception:
      pass

    try:
      if files:
        try:
          self.message = await interaction.followup.send(view=self, files=files, ephemeral=True)
        except TypeError:
          if len(files) == 1:
            self.message = await interaction.followup.send(view=self, file=files[0], ephemeral=True)
          else:
            self.message = await interaction.followup.send(view=self, ephemeral=True)
      else:
        self.message = await interaction.followup.send(view=self, ephemeral=True)
    except Exception:
      logger.exception("[trade] TradeStatusView:_render resend failed")
      return

    await self._unlock_new_message()

  async def on_timeout(self):
    try:
      async with self._interaction_lock:
        self._ack = True
        self._ui_locked = True
        try:
          self._rebuild_view()
        except Exception:
          pass

        try:
          if self.message:
            await self.message.edit(view=self)
        except Exception:
          pass
    finally:
      pass


# ___________                  .___     .___                            .__                _________      .__                 __ ____   ____.__
# \__    ___/___________     __| _/____ |   | ____   ____  ____   _____ |__| ____    ____ /   _____/ ____ |  |   ____   _____/  |\   \ /   /|__| ______  _  __
#   |    |  \_  __ \__  \   / __ |/ __ \|   |/    \_/ ___\/  _ \ /     \|  |/    \  / ___\\_____  \_/ __ \|  | _/ __ \_/ ___\   __\   Y   / |  |/ __ \ \/ \/ /
#   |    |   |  | \// __ \_/ /_/ \  ___/|   |   |  \  \__(  <_> )  Y Y  \  |   |  \/ /_/  >        \  ___/|  |_\  ___/\  \___|  |  \     /  |  \  ___/\     /
#   |____|   |__|  (____  /\____ |\___  >___|___|  /\___  >____/|__|_|  /__|___|  /\___  /_______  /\___  >____/\___  >\___  >__|   \___/   |__|\___  >\/\_/
#                       \/      \/    \/         \/     \/            \/        \//_____/        \/     \/          \/     \/                       \/
class TradeIncomingSelectView(discord.ui.DesignerView):

  def __init__(self, *, cog, requestor_ids: list[int]):
    super().__init__(timeout=360)
    self.cog = cog
    self.requestor_ids = requestor_ids

    self._interaction_lock = asyncio.Lock()
    self._ack = False
    self._ui_locked = False
    self.message = None

  def _is_component_interaction(self, interaction: discord.Interaction | None) -> bool:
    try:
      return bool(interaction and getattr(interaction, "message", None))
    except Exception:
      return False

  async def _ack_interaction(self, interaction: discord.Interaction) -> bool:
    if interaction.response.is_done():
      return True

    if self._is_component_interaction(interaction):
      try:
        fn = getattr(interaction.response, "defer_update", None)
        if fn:
          await fn()
          return True
      except Exception:
        pass

    try:
      await interaction.response.defer(ephemeral=True)
      return True
    except TypeError:
      pass
    except Exception:
      return False

    try:
      await interaction.response.defer()
      return True
    except Exception:
      return False

  async def _delete_message(self, interaction: discord.Interaction | None):
    msg = None
    try:
      msg = interaction.message if interaction else None
    except Exception:
      msg = None

    if not msg:
      msg = self.message

    if not msg:
      return

    try:
      await msg.delete()
      if msg == self.message:
        self.message = None
      return
    except Exception:
      pass

    try:
      if interaction:
        await interaction.followup.delete_message(msg.id)
        if msg == self.message:
          self.message = None
    except Exception:
      pass

  async def on_timeout(self):
    try:
      async with self._interaction_lock:
        self._ack = True
        self._ui_locked = True
        try:
          self._rebuild_view()
        except Exception:
          pass

        try:
          if self.message:
            await self.message.edit(view=self)
        except Exception:
          pass
    finally:
      pass

  def _rebuild_view(self):
    requestor_ids = [int(i) for i in (self.requestor_ids or [])]
    requestor_ids = list(dict.fromkeys(requestor_ids))

    container = discord.ui.Container(color=_trade_color_ok().value)
    container.add_item(discord.ui.TextDisplay("# Incoming Trade Requests"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay("Select a user to review their pending trade request."))

    row = discord.ui.ActionRow()
    select = discord.ui.Select(
      placeholder="Select a user...",
      min_values=1,
      max_values=1,
      options=[discord.SelectOption(label="(timed out)", value="na")],
      disabled=True
    )

    row.add_item(select)
    container.add_item(row)

    self.clear_items()
    self.add_item(container)

  async def start(self, interaction: discord.Interaction):
    requestor_ids = [int(i) for i in (self.requestor_ids or [])]
    requestor_ids = list(dict.fromkeys(requestor_ids))

    if len(requestor_ids) > 25:
      logger.exception("[trade] too many incoming requestors: %s", len(requestor_ids))

      err_view = discord.ui.DesignerView(timeout=60)
      container = discord.ui.Container(color=_trade_color_error().value)
      container.add_item(discord.ui.TextDisplay("# Trade System Error"))
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(
        "You have more than 25 incoming trade partners.\nPlease resolve some pending trades and try again."
      ))
      err_view.add_item(container)
      try:
        err_view.disable_all_items()
      except Exception:
        pass

      try:
        await interaction.followup.send(view=err_view, ephemeral=True)
      except Exception:
        logger.exception("[trade] TradeIncomingSelectView: failed to send error view")

      raise ValueError("Too many incoming trade partners (>25)")

    ok = await self._ack_interaction(interaction)
    if not ok:
      return

    guild = getattr(interaction, "guild", None) or getattr(self.cog.bot, "current_guild", None)
    options: list[discord.SelectOption] = []

    for rid in requestor_ids:
      member = None
      try:
        if guild:
          member = guild.get_member(int(rid))
          if not member:
            member = await guild.fetch_member(int(rid))
      except Exception:
        member = None

      if member:
        label = strip_bullshit(member.display_name)[:100]
        options.append(discord.SelectOption(label=label, value=str(rid)))

    if not options:
      await interaction.followup.send(
        embed=discord.Embed(
          title="Error fetching users",
          description="We couldn't find any of the users who have open trades with you. They may have left the server.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    container = discord.ui.Container(color=_trade_color_ok().value)
    container.add_item(discord.ui.TextDisplay("# Incoming Trade Requests"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay("Select a user to review their pending trade request."))

    row = discord.ui.ActionRow()
    select = discord.ui.Select(
      placeholder="Select a user...",
      min_values=1,
      max_values=1,
      options=options[:25],
      disabled=self._ui_locked
    )

    async def _select_cb(ix: discord.Interaction):
      async with self._interaction_lock:
        if self._ack or self._ui_locked:
          return
        self._ack = True
        try:
          ok2 = await self._ack_interaction(ix)
          if not ok2:
            return

          vals = (ix.data or {}).get("values") or []
          if not vals:
            return

          try:
            await self._delete_message(ix)
          except Exception:
            pass

          await self.cog._send_pending_trade_interface(ix, int(vals[0]))
        finally:
          self._ack = False

    select.callback = _select_cb
    row.add_item(select)
    container.add_item(row)

    self.clear_items()
    self.add_item(container)

    try:
      self.message = await interaction.followup.send(view=self, ephemeral=True)
    except Exception:
      logger.exception("[trade] TradeIncomingSelectView:start send failed")
      self.message = None



class Trade(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.max_trades = 10
    self.max_badges_per_trade = 6

  trade = discord.SlashCommandGroup("trade", "Commands for trading badges")

  @trade.command(
    name="incoming",
    description="View and accept/decline incoming trades from other users"
  )
  @commands.check(access_check)
  async def incoming(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    incoming_trades = await db_get_active_requestee_trades(ctx.user.id)

    if not incoming_trades:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No Incoming Trade Requests",
          description="No one has any active trades requested from you.",
          color=_trade_color_ok()
        ),
        ephemeral=True
      )
      return

    incoming_requestor_ids = [int(t["requestor_id"]) for t in incoming_trades]
    view = TradeIncomingSelectView(cog=self, requestor_ids=incoming_requestor_ids)
    await view.start(ctx.interaction)

  async def _send_pending_trade_interface(self, interaction: discord.Interaction, requestor_id: int):
    requestee_id = interaction.user.id
    active_trade = await db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id)

    if not active_trade:
      embed = discord.Embed(
        title="Trade Not Found",
        description="There doesn't appear to be an active trade between you and this user.",
        color=_trade_color_error()
      )
      if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
      else:
        await interaction.followup.send(embed=embed, ephemeral=True)
      return

    view = TradeStatusView(cog=self, active_trade=active_trade, mode="incoming")
    await view.start(interaction)

  @trade.command(
    name="start",
    description="Start a trade with a specified user (only one outgoing trade active at a time)"
  )
  @option(
    "requestee",
    discord.User,
    description="The user you wish to start a trade with",
    required=True
  )
  @option(
    name="prestige",
    description="Which Prestige Tier to trade?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    name="use_matches",
    description="Limit to Wishlist Match Badges? (if available)",
    required=True,
    autocomplete=autocomplete_use_matches
  )
  @option(
    "offer",
    str,
    description="A badge you are offering",
    required=True,
    autocomplete=autocomplete_offering_badges
  )
  @option(
    "request",
    str,
    description="A badge you are requesting",
    required=False,
    autocomplete=autocomplete_requesting_badges
  )
  @commands.check(access_check)
  async def start(self, ctx: discord.ApplicationContext, requestee: discord.User, prestige: str, use_matches: str, offer: str, request: str):
    await ctx.defer(ephemeral=True)

    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_level = int(prestige)

    requestor_echelon_progress = await db_get_echelon_progress(requestor_id)
    requestee_echelon_progress = await db_get_echelon_progress(requestee_id)

    if requestor_echelon_progress["current_prestige_tier"] < prestige_level:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description=f"You are not eligible to trade {PRESTIGE_TIERS[prestige_level]} badges.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if requestee_echelon_progress["current_prestige_tier"] < prestige_level:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description=f"{requestee.display_name} is not eligible to trade {PRESTIGE_TIERS[prestige_level]} badges.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if not await self._is_trade_initialization_valid(ctx, requestee):
      return

    if not await self._do_participants_own_badges(ctx, requestor_id, requestee_id, prestige_level, offer, request):
      return

    trade_id = await db_initiate_trade(requestor_id, requestee_id, prestige_level)
    active_trade = {
      "id": trade_id,
      "requestor_id": requestor_id,
      "requestee_id": requestee_id,
      "prestige_level": prestige_level,
      "status": "pending"
    }

    try:
      offer_instance_id = int(offer)
    except Exception:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Badge Selection",
          description="Please select a valid badge from the dropdown.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if await self._is_untradeable(ctx, offer_instance_id, ctx.author, requestee, active_trade, "offer"):
      return
    await db_add_offered_instance(trade_id, offer_instance_id)

    if request and request != "none":
      try:
        request_instance_id = int(request)
      except Exception:
        await ctx.followup.send(
          embed=discord.Embed(
            title="Invalid Badge Selection",
            description="Please select a valid badge from the dropdown.",
            color=_trade_color_error()
          ),
          ephemeral=True
        )
        return

      if await self._is_untradeable(ctx, request_instance_id, ctx.author, requestee, active_trade, "request"):
        return
      await db_add_requested_instance(trade_id, request_instance_id)

    initiated_trade = await self.check_for_active_trade(ctx)
    view = TradeStatusView(cog=self, active_trade=initiated_trade, mode="outgoing")
    await view.start(ctx.interaction)

  async def _is_trade_initialization_valid(self, ctx: discord.ApplicationContext, requestee: discord.User):
    requestor_id = ctx.author.id
    requestee_id = requestee.id

    if requestor_id == requestee_id:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Don't be silly!",
          description="You can't request a trade from yourself!",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    if requestee_id == self.bot.user.id:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Nope",
          description="AGIMUS has no badges to trade!",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    requestee_details = await get_user(requestee_id)
    if not requestee_details or not requestee_details["xp_enabled"]:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This user is not participating.",
          description=f"Sorry, **{requestee.display_name}** has opted out of the XP system and is not available for trading.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    active_trade = await db_get_active_requestor_trade(requestor_id)
    if active_trade:
      active_trade_requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
      await ctx.followup.send(
        embed=discord.Embed(
          title="You already have an active trade!",
          description=(
            f"You have an outgoing trade open with **{active_trade_requestee.display_name}**.\n\n"
            "Use `/trade send` to check the status and cancel the current trade if desired.\n\n"
            "This must be resolved before you can open another request."
          ),
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    requestee_trades = await db_get_active_requestee_trades(requestee_id)
    if len(requestee_trades) >= self.max_trades:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"{requestee.display_name} has too many pending trades!",
          description=(
            f"Sorry, the person you've requested a trade from already has the maximum number "
            f"of incoming trade requests pending ({self.max_trades})."
          ),
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    return True

  async def _do_participants_own_badges(self, ctx, requestor_id, requestee_id, prestige_level, offer_instance_id, request_instance_id=None):
    offer_instance = await db_get_badge_instance_by_id(int(offer_instance_id))
    if (
      not offer_instance
      or offer_instance["owner_discord_id"] != str(requestor_id)
      or offer_instance["prestige_level"] != prestige_level
    ):
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Offer",
          description="You don't own that badge at the specified Prestige Tier.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return False

    if request_instance_id and request_instance_id != "none":
      request_instance = await db_get_badge_instance_by_id(int(request_instance_id))
      if (
        not request_instance
        or request_instance["owner_discord_id"] != str(requestee_id)
        or request_instance["prestige_level"] != prestige_level
      ):
        requestee = await self.bot.current_guild.fetch_member(requestee_id)
        await ctx.followup.send(
          embed=discord.Embed(
            title="Invalid Request",
            description=f"{requestee.display_name} does not own that badge at the specified Prestige Tier.",
            color=_trade_color_error()
          ),
          ephemeral=True
        )
        return False

    return True

  @trade.command(
    name="send",
    description="Check the current status and send your outgoing trade"
  )
  @commands.check(access_check)
  async def send(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    view = TradeStatusView(cog=self, active_trade=active_trade, mode="outgoing")
    await view.start(ctx.interaction)

  @trade.command(
    name="propose",
    description="Offer or request badges for your current pending trade"
  )
  @option(
    name="use_matches",
    description="Limit to Wishlist Match Badges? (if available)",
    required=True,
    autocomplete=autocomplete_use_matches
  )
  @option(
    "offer",
    str,
    description="A badge you are offering",
    required=False,
    autocomplete=autocomplete_offering_badges
  )
  @option(
    "request",
    str,
    description="A badge you are requesting",
    required=False,
    autocomplete=autocomplete_requesting_badges
  )
  @commands.check(access_check)
  async def propose(self, ctx, use_matches: str, offer: str, request: str):
    await ctx.defer(ephemeral=True)
    active_trade = await self.check_for_active_trade(ctx)
    if not active_trade:
      return

    requestor_echelon_progress = await db_get_echelon_progress(active_trade["requestor_id"])
    requestee_echelon_progress = await db_get_echelon_progress(active_trade["requestee_id"])

    if (
      requestor_echelon_progress["current_prestige_tier"] < active_trade["prestige_level"]
      or requestee_echelon_progress["current_prestige_tier"] < active_trade["prestige_level"]
    ):
      await db_cancel_trade(active_trade)
      await ctx.followup.send(
        embed=discord.Embed(
          title="Trade Invalid",
          description=f"One or both participants are not eligible for {PRESTIGE_TIERS[active_trade['prestige_level']]} badge trading.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if (not offer or offer == "none") and (not request or request == "none"):
      await ctx.followup.send(
        embed=discord.Embed(
          title="Please select a badge to offer or request",
          description="If you want to update your trade, you need to choose a badge.",
          color=discord.Color.dark_red()
        ),
        ephemeral=True
      )
      return

    requestee = await self.bot.fetch_user(active_trade["requestee_id"])

    if offer and offer != "none":
      try:
        offer_id = int(offer)
      except Exception:
        await ctx.followup.send(
          embed=discord.Embed(
            title="Invalid Badge Selection",
            description="Please select a valid badge from the dropdown.",
            color=_trade_color_error()
          ),
          ephemeral=True
        )
        return
      if await self._is_untradeable(ctx, offer_id, ctx.author, requestee, active_trade, "offer"):
        return
      await self._add_offered_badge_to_trade(ctx, active_trade, offer_id)

    if request and request != "none":
      try:
        request_id = int(request)
      except Exception:
        await ctx.followup.send(
          embed=discord.Embed(
            title="Invalid Badge Selection",
            description="Please select a valid badge from the dropdown.",
            color=_trade_color_error()
          ),
          ephemeral=True
        )
        return
      if await self._is_untradeable(ctx, request_id, ctx.author, requestee, active_trade, "request"):
        return
      await self._add_requested_badge_to_trade(ctx, active_trade, request_id)

  async def _add_offered_badge_to_trade(self, ctx, active_trade, instance_id):
    trade_id = active_trade["id"]
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    user_instances = await db_get_user_badge_instances(requestor.id, prestige=active_trade["prestige_level"])
    instance = next((b for b in user_instances if b["badge_instance_id"] == instance_id), None)
    if not instance:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Not Found",
          description=f"You don't own this {prestige_tier} badge!",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    await db_add_offered_instance(trade_id, instance_id)

    badge_name = instance["badge_name"]
    discord_file, attachment_url = await generate_badge_preview(ctx.author.id, instance, disable_overlays=True)

    embed = discord.Embed(
      title="Badge added to offer.",
      description=f"**{badge_name}** has been added to your offer to **{requestee.display_name}**.",
      color=_trade_color_ok()
    )
    embed.set_image(url=attachment_url)
    await ctx.followup.send(embed=embed, file=discord_file, ephemeral=True)

  async def _add_requested_badge_to_trade(self, ctx, active_trade, instance_id):
    trade_id = active_trade["id"]
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    user_instances = await db_get_user_badge_instances(requestee.id, prestige=active_trade["prestige_level"])
    instance = next((b for b in user_instances if b["badge_instance_id"] == instance_id), None)
    if not instance:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Not Found",
          description=f"**{requestee.display_name}** doesn't own that {prestige_tier} badge!",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    await db_add_requested_instance(trade_id, instance_id)

    badge_name = instance["badge_name"]
    discord_file, attachment_url = await generate_badge_preview(ctx.author.id, instance, disable_overlays=True)

    embed = discord.Embed(
      title="Badge added to request.",
      description=f"**{badge_name}** has been added to your request from **{requestee.display_name}**.",
      color=_trade_color_ok()
    )
    embed.set_image(url=attachment_url)
    await ctx.followup.send(embed=embed, file=discord_file, ephemeral=True)

  async def _is_untradeable(self, ctx, badge_instance_id, requestor, requestee, active_trade, direction):
    if direction == "offer":
      from_user = requestor
      to_user = requestee
      side_fetcher = db_get_trade_offered_badge_instances
    else:
      from_user = requestee
      to_user = requestor
      side_fetcher = db_get_trade_requested_badge_instances

    instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not instance:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge not found",
          description="This badge no longer exists or was already traded.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    if instance["prestige_level"] != active_trade["prestige_level"]:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Invalid Prestige",
          description="You selected a badge at the incorrect Prestige Tier.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    if str(instance["owner_discord_id"]) != str(from_user.id):
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge not available",
          description=f"{from_user.display_name} no longer has this badge.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    if instance["special"]:
      await ctx.followup.send(
        embed=discord.Embed(
          title="That badge is untradeable!",
          description=f"Sorry, you can't {direction} **{instance['badge_name']}** - it's a special one!",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    to_user_instances = await db_get_user_badge_instances(to_user.id, prestige=active_trade["prestige_level"])
    to_user_badge_filenames = {b["badge_filename"] for b in to_user_instances}
    if instance["badge_filename"] in to_user_badge_filenames:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"{to_user.display_name} already has {instance['badge_name']} at this Prestige Tier!",
          description="No need to trade this one.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    trade_badges = await side_fetcher(active_trade)
    trade_badge_ids = {b["badge_instance_id"] for b in trade_badges}
    if instance["badge_instance_id"] in trade_badge_ids:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"{instance['badge_name']} already exists in the {direction} list.",
          description="No action taken.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    if len(trade_badges) >= self.max_badges_per_trade:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"Unable to add {instance['badge_name']}",
          description=f"You're at the max number of badges allowed per side ({self.max_badges_per_trade}).",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    max_badge_count = await db_get_max_badge_count()
    to_user_count = await db_get_badge_instances_count_for_user(to_user.id, prestige=active_trade["prestige_level"])
    incoming = await side_fetcher(active_trade)

    if to_user_count + len(incoming) + 1 > max_badge_count:
      await ctx.followup.send(
        embed=discord.Embed(
          title=f"{to_user.display_name}'s inventory is full!",
          description=f"Adding **{instance['badge_name']}** would exceed the total number of badges possible at this Prestige Tier ({max_badge_count}).",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return True

    return False

  async def check_for_active_trade(self, ctx: discord.ApplicationContext):
    active_trade = await db_get_active_requestor_trade(ctx.author.id)
    if not active_trade:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You don't have a pending or active trade open!",
          description="You can start a new trade with `/trade start`.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
    return active_trade

  async def _cancel_trade_callback(self, interaction, active_trade):
    try:
      await db_cancel_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

      embed = discord.Embed(
        title=f"{prestige_tier} Trade Canceled!",
        description=f"Your {prestige_tier} trade with **{requestee.display_name}** has been canceled.",
        color=discord.Color.dark_red()
      )

      if active_trade.get("status") == "active":
        embed.set_footer(text="Because the trade was active, we've let them know you canceled the request.")

        user_settings = await get_user(requestee.id)
        if user_settings and user_settings.get("receive_notifications"):
          try:
            offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

            notification = discord.Embed(
              title=f"{prestige_tier} Trade Canceled!",
              description=f"Heads up! **{requestor.display_name}** canceled their pending {prestige_tier} trade request with you.",
              color=_trade_color_ok()
            )
            notification.add_field(
              name=f"{prestige_tier} badges offered by {requestor.display_name}",
              value=offered_badge_names
            )
            notification.add_field(
              name=f"{prestige_tier} badges requested from {requestee.display_name}",
              value=requested_badge_names
            )
            notification.set_footer(text="Note: You can use /settings to enable or disable these messages.")
            await requestee.send(embed=notification)
          except discord.Forbidden:
            pass

      if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
      else:
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception:
      logger.info(traceback.format_exc())

  async def _send_trade_callback(self, interaction, active_trade):
    try:
      await db_activate_trade(active_trade)
      requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

      embed = discord.Embed(
        title=f"{prestige_tier} Trade Sent!",
        color=_trade_color_ok()
      )
      if not interaction.response.is_done():
        await interaction.response.send_message(embed=embed, ephemeral=True)
      else:
        await interaction.followup.send(embed=embed, ephemeral=True)

      active_trade["status"] = "active"

      home_embed, home_image = await self._generate_home_embed_and_image(active_trade)
      offered_view, offered_files = await self._generate_public_summary_view(active_trade, mode="offered")
      requested_view, requested_files = await self._generate_public_summary_view(active_trade, mode="requested")

      home_message = await interaction.channel.send(embed=home_embed, file=home_image)
      await interaction.channel.send(view=offered_view, files=offered_files)
      await interaction.channel.send(view=requested_view, files=requested_files)

      user = await get_user(requestee.id)
      if user and user.get("receive_notifications"):
        try:
          offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

          description = (
            f"Hey there - **{requestor.display_name}** has requested a {prestige_tier} trade from you on The USS Hood.\n\n"
            "Use `/trade incoming` to review and either accept or decline.\n\n"
            f"You can jump to their offer here: {home_message.jump_url}"
          )

          requestee_embed = discord.Embed(
            title="Trade Offered",
            description=description,
            color=_trade_color_ok()
          )
          requestee_embed.add_field(
            name=f"{prestige_tier} badges offered by {requestor.display_name}",
            value=offered_badge_names
          )
          requestee_embed.add_field(
            name=f"{prestige_tier} badges requested from {requestee.display_name}",
            value=requested_badge_names
          )
          requestee_embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestee.send(embed=requestee_embed)
        except discord.Forbidden:
          pass

    except Exception:
      logger.info(traceback.format_exc())

  async def _accept_trade_callback(self, interaction, active_trade):
    await self._cancel_invalid_related_trades(active_trade)

    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    requested_instances = await db_get_trade_requested_badge_instances(active_trade)

    requestor_echelon_progress = await db_get_echelon_progress(active_trade["requestor_id"])
    requestee_echelon_progress = await db_get_echelon_progress(active_trade["requestee_id"])

    active_trade_prestige = active_trade["prestige_level"]

    if requestor_echelon_progress["current_prestige_tier"] < active_trade_prestige:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description=f"{requestor.display_name} is not eligible to send {PRESTIGE_TIERS[active_trade_prestige]} badges.\n\nTrade Canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if requestee_echelon_progress["current_prestige_tier"] < active_trade_prestige:
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title="Invalid Trade",
          description=f"{requestee.display_name} is not eligible to receive {PRESTIGE_TIERS[active_trade_prestige]} badges.\n\nTrade Canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      return

    if await self._requestor_already_has_badges(interaction, active_trade, requestor, requestee):
      return
    if await self._requestee_already_has_badges(interaction, active_trade, requestor, requestee):
      return
    if not await self._requestor_still_has_badges(interaction, active_trade, requestor, requestee):
      return
    if not await self._requestee_still_has_badges(interaction, active_trade, requestor, requestee):
      return

    await db_perform_badge_transfer(active_trade)
    await db_complete_trade(active_trade)

    offered_names = "\n".join([f"* {b['badge_name']}" for b in offered_instances]) or "None"
    requested_names = "\n".join([f"* {b['badge_name']}" for b in requested_instances]) or "None"

    success_embed = discord.Embed(
      title="Successful Trade!",
      description=(
        f"**{requestor.display_name}** and **{requestee.display_name}** came to a {prestige_tier} trade agreement!\n\n"
        f"{prestige_tier} badges transferred successfully!"
      ),
      color=_trade_color_ok()
    )
    success_embed.add_field(name=f"{requestor.display_name} received", value=requested_names)
    success_embed.add_field(name=f"{requestee.display_name} received", value=offered_names)
    success_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    success_image = discord.File(fp="./images/trades/assets/trade_successful.jpg", filename="trade_successful.jpg")
    success_embed.set_image(url="attachment://trade_successful.jpg")

    message = await interaction.channel.send(embed=success_embed, file=success_image)

    requestor_user = await get_user(requestor.id)
    if requestor_user and requestor_user.get("receive_notifications"):
      try:
        dm_embed = success_embed.copy()
        dm_embed.add_field(name="View Confirmation", value=message.jump_url, inline=False)
        dm_embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
        await requestor.send(embed=dm_embed)
      except discord.Forbidden:
        pass

  async def _decline_trade_callback(self, interaction, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    await db_decline_trade(active_trade)

    await interaction.followup.send(
      embed=discord.Embed(
        title="Trade Declined",
        description=f"You declined the proposed {prestige_tier} trade with **{requestor.display_name}**.",
        color=_trade_color_ok()
      ),
      ephemeral=True
    )

    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    user = await get_user(requestor.id)
    if user and user.get("receive_notifications"):
      try:
        embed = discord.Embed(
          title="Trade Declined",
          description=f"Your {prestige_tier} trade to **{requestee.display_name}** was declined.",
          color=_trade_color_ok()
        )
        embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
        embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
        embed.set_footer(text="Thank you and have a nice day!")
        await requestor.send(embed=embed)
      except discord.Forbidden:
        pass

  async def _cancel_invalid_related_trades(self, active_trade):
    related_trades = await db_get_related_badge_instance_trades(active_trade)
    trades_to_cancel = [t for t in related_trades if t["id"] != active_trade["id"]]

    for trade in trades_to_cancel:
      await db_cancel_trade(trade)

      requestor = await self.bot.current_guild.fetch_member(trade["requestor_id"])
      requestee = await self.bot.current_guild.fetch_member(trade["requestee_id"])
      prestige_tier = PRESTIGE_TIERS[trade["prestige_level"]]

      offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(trade)

      requestee_user = await get_user(requestee.id)
      if trade.get("status") == "active" and requestee_user and requestee_user.get("receive_notifications"):
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=(
              f"Your {prestige_tier} trade initiated by **{requestor.display_name}** was canceled "
              "because one or more badges were traded to someone else."
            ),
            color=_trade_color_ok()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestee.send(embed=embed)
        except discord.Forbidden:
          pass

      requestor_user = await get_user(requestor.id)
      if requestor_user and requestor_user.get("receive_notifications"):
        try:
          embed = discord.Embed(
            title="Trade Canceled",
            description=(
              f"Your {prestige_tier} trade requested from **{requestee.display_name}** was canceled "
              "because one or more badges were traded to someone else."
            ),
            color=_trade_color_ok()
          )
          embed.add_field(name=f"Offered by {requestor.display_name}", value=offered_badge_names)
          embed.add_field(name=f"Requested from {requestee.display_name}", value=requested_badge_names)
          embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
          await requestor.send(embed=embed)
        except discord.Forbidden:
          pass

  async def _dm_trade_canceled(self, *, requestor, requestee, active_trade, reason: str):
    user = await get_user(requestor.id)
    if not user or not user.get("receive_notifications"):
      return
    try:
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]
      offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

      embed = discord.Embed(
        title="Trade Canceled",
        description=(
          f"Just a heads up - your {prestige_tier} trade requested from **{requestee.display_name}** "
          f"was canceled because {reason}."
        ),
        color=_trade_color_ok()
      )
      embed.add_field(name=f"{prestige_tier} badges offered by {requestor.display_name}", value=offered_badge_names)
      embed.add_field(name=f"{prestige_tier} badges requested from {requestee.display_name}", value=requested_badge_names)
      embed.set_footer(text="Note: You can use /settings to enable or disable these messages.")
      await requestor.send(embed=embed)
    except discord.Forbidden:
      pass

  async def _requestor_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestor_instances = await db_get_user_badge_instances(active_trade["requestor_id"], prestige=active_trade["prestige_level"])
    requestor_filenames = {b["badge_filename"] for b in requestor_instances}

    requested_instances = await db_get_trade_requested_badge_instances(active_trade)
    requested_filenames = {b["badge_filename"] for b in requested_instances}

    overlap = requestor_filenames & requested_filenames

    if overlap:
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="They already received some of the badges you requested while this trade was pending.\n\nTrade has been canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      await self._dm_trade_canceled(
        requestor=requestor,
        requestee=requestee,
        active_trade=active_trade,
        reason="you already own one or more of the badges requested"
      )
      return True

    return False

  async def _requestee_already_has_badges(self, interaction, active_trade, requestor, requestee):
    requestee_instances = await db_get_user_badge_instances(active_trade["requestee_id"], prestige=active_trade["prestige_level"])
    requestee_filenames = {b["badge_filename"] for b in requestee_instances}

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    offered_filenames = {b["badge_filename"] for b in offered_instances}

    overlap = requestee_filenames & offered_filenames

    if overlap:
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="You already received some of the badges that were offered while this trade was pending.\n\nTrade has been canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      await self._dm_trade_canceled(
        requestor=requestor,
        requestee=requestee,
        active_trade=active_trade,
        reason=f"{requestee.display_name} already owns one or more of the badges offered"
      )
      return True

    return False

  async def _requestor_still_has_badges(self, interaction, active_trade, requestor, requestee):
    user_instances = await db_get_user_badge_instances(requestor.id, prestige=active_trade["prestige_level"])
    current_ids = {b["badge_instance_id"] for b in user_instances}

    offered_instances = await db_get_trade_offered_badge_instances(active_trade)
    offered_ids = {b["badge_instance_id"] for b in offered_instances}

    if not offered_ids.issubset(current_ids):
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="They no longer have some of the badges they offered.\n\nTrade has been canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      await self._dm_trade_canceled(
        requestor=requestor,
        requestee=requestee,
        active_trade=active_trade,
        reason="you no longer have one or more of the badges you offered"
      )
      return False

    return True

  async def _requestee_still_has_badges(self, interaction, active_trade, requestor, requestee):
    user_instances = await db_get_user_badge_instances(requestee.id, prestige=active_trade["prestige_level"])
    current_ids = {b["badge_instance_id"] for b in user_instances}

    requested_instances = await db_get_trade_requested_badge_instances(active_trade)
    requested_ids = {b["badge_instance_id"] for b in requested_instances}

    if not requested_ids.issubset(current_ids):
      prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]
      await db_cancel_trade(active_trade)
      await interaction.followup.send(
        embed=discord.Embed(
          title=f"Invalid {prestige_tier} Trade",
          description="You no longer have some of the badges they requested.\n\nTrade has been canceled.",
          color=_trade_color_error()
        ),
        ephemeral=True
      )
      await self._dm_trade_canceled(
        requestor=requestor,
        requestee=requestee,
        active_trade=active_trade,
        reason=f"{requestee.display_name} no longer has one or more of the badges requested"
      )
      return False

    return True

  async def _generate_home_embed_and_image(self, active_trade):
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    offered_badge_names, requested_badge_names = await get_offered_and_requested_badge_names(active_trade)

    if active_trade.get("status") == "active":
      title = "Trade Offered!"
      description = (
        "Get that, get that, gold pressed latinum!\n\n"
        f"**{requestor.display_name}** has offered a {prestige_tier} trade to **{requestee.display_name}**!"
      )
      image_filename = "trade_offer.png"
    else:
      title = "Trade Pending..."
      description = (
        f"Ready to send?\n\nThis is your pending {prestige_tier} trade with **{requestee.display_name}**.\n\n"
        "Press **Send** if it looks good to go!"
      )
      image_filename = "trade_pending.png"

    if await trade_has_attuned_crystals(active_trade):
      description += "\n\n⚠️ One or more badges in this trade have Crystals attached to them."

    home_embed = discord.Embed(
      title=title,
      description=description,
      color=_trade_color_ok()
    )
    home_embed.add_field(
      name=f"{prestige_tier} badges offered by {requestor.display_name}",
      value=offered_badge_names
    )
    home_embed.add_field(
      name=f"{prestige_tier} badges requested from {requestee.display_name}",
      value=requested_badge_names
    )
    home_embed.set_footer(
      text=f"Ferengi Rule of Acquisition {random.choice(rules_of_acquisition)}",
      icon_url="https://i.imgur.com/GTN4gQG.jpg"
    )

    home_image = discord.File(fp=f"./images/trades/assets/{image_filename}", filename=image_filename)
    home_embed.set_image(url=f"attachment://{image_filename}")

    return home_embed, home_image

  def _build_file_from_bytes(self, file_bytes: bytes | None, filename: str) -> discord.File | None:
    if not file_bytes or not filename:
      return None
    fp = io.BytesIO(file_bytes)
    try:
      fp.seek(0)
    except Exception:
      pass
    return discord.File(fp=fp, filename=filename)

  async def _try_build_badge_preview_bytes(
    self,
    *,
    owner_id: str,
    badge: dict,
    badge_instance_id: int,
    crystal: dict | None
  ) -> tuple[bytes | None, str | None]:
    if not owner_id or not badge_instance_id or not badge:
      return None, None

    try:
      file, _url = await generate_badge_preview(
        owner_id,
        badge,
        crystal=crystal,
        theme=None,
        disable_overlays=True
      )
      if not file:
        return None, None

      filename = getattr(file, "filename", None)
      fp = getattr(file, "fp", None)
      if not filename or not fp:
        return None, None

      try:
        fp.seek(0)
      except Exception:
        pass

      data = fp.read()
      if not data:
        return None, None

      ext = "png"
      try:
        if "." in filename:
          ext = filename.rsplit(".", 1)[-1].lower() or "png"
      except Exception:
        ext = "png"

      safe_name = f"trade_public_{badge_instance_id}_preview.{ext}"
      return data, safe_name
    except Exception:
      return None, None

  async def _build_badge_meta_for_public(
    self,
    instances: list[dict],
    *,
    owner_id: str
  ) -> list[dict]:
    out: list[dict] = []

    for b in (instances or []):
      badge_instance_id = int(b.get("badge_instance_id") or 0)
      badge_name = b.get("badge_name") or "Unknown Badge"

      crystals = []
      try:
        crystals = await db_get_attuned_crystals(badge_instance_id)
      except Exception:
        crystals = []

      crystal_count = len(crystals or [])
      slotted = _pick_active_crystal(crystals, active_crystal_id=b.get("active_crystal_id"))

      preview_bytes, preview_filename = await self._try_build_badge_preview_bytes(
        owner_id=owner_id,
        badge=b,
        badge_instance_id=badge_instance_id,
        crystal=slotted
      )

      out.append({
        "badge_instance_id": badge_instance_id,
        "badge_name": badge_name,
        "crystal_count": crystal_count,
        "thumb_bytes": preview_bytes,
        "thumb_filename": preview_filename
      })

    return out

  async def _generate_public_summary_view(self, active_trade: dict, *, mode: str) -> tuple[discord.ui.DesignerView, list[discord.File]]:
    """
    Builds a simple public DesignerView summary (Offered/Requested) using Sections + thumbnails.
    mode: "offered" or "requested"
    """
    requestee = await self.bot.current_guild.fetch_member(active_trade["requestee_id"])
    requestor = await self.bot.current_guild.fetch_member(active_trade["requestor_id"])
    prestige_tier = PRESTIGE_TIERS[active_trade["prestige_level"]]

    if mode == "offered":
      title = "Offered"
      subtitle = f"{prestige_tier} badges offered by **{requestor.display_name}** to **{requestee.display_name}**"
      instances = await db_get_trade_offered_badge_instances(active_trade)
      owner_id = str(active_trade.get("requestor_id") or "")
    else:
      title = "Requested"
      subtitle = f"{prestige_tier} badges requested from **{requestee.display_name}** by **{requestor.display_name}**"
      instances = await db_get_trade_requested_badge_instances(active_trade)
      owner_id = str(active_trade.get("requestee_id") or "")

    badges = await self._build_badge_meta_for_public(instances, owner_id=owner_id)

    view = discord.ui.DesignerView(timeout=None)

    container = discord.ui.Container(color=_trade_color_ok().value)
    container.add_item(discord.ui.TextDisplay(f"# {title}"))
    container.add_item(discord.ui.TextDisplay(subtitle))
    container.add_item(discord.ui.Separator())

    files: list[discord.File] = []
    rendered_any = False

    for b in (badges or [])[:self.max_badges_per_trade]:
      badge_name = b.get("badge_name") or "Unknown Badge"
      crystal_count = int(b.get("crystal_count") or 0)

      thumb_bytes = b.get("thumb_bytes")
      thumb_name = b.get("thumb_filename")
      has_thumb = bool(thumb_bytes and thumb_name)

      if has_thumb:
        dfile = self._build_file_from_bytes(thumb_bytes, thumb_name)
        if dfile:
          files.append(dfile)

      section = discord.ui.Section(
        discord.ui.TextDisplay(f"### {badge_name}")
      )

      if crystal_count > 0:
        section.add_item(discord.ui.TextDisplay(
          f"There are {crystal_count} Crystals attuned to this badge!"
        ))

      if has_thumb:
        section.set_thumbnail(
          url=f"attachment://{thumb_name}",
          description="Badge"
        )

      container.add_item(section)
      rendered_any = True

    if not rendered_any:
      container.add_item(discord.ui.TextDisplay("`(none)`"))

    view.add_item(container)
    return view, files
