from common import *

from cogs.profile import (
  db_get_user_profile_styles_from_inventory,
  db_get_user_profile_stickers_from_inventory,
  db_get_user_profile_photos_from_inventory
)

# cogs.shop


def _shop_color() -> discord.Color:
  return discord.Color(0xFFFFFF)

#   _________.__                ____   ____.__               
#  /   _____/|  |__   ____ _____\   \ /   /|__| ______  _  __
#  \_____  \ |  |  \ /  _ \\____ \   Y   / |  |/ __ \ \/ \/ /
#  /        \|   Y  (  <_> )  |_> >     /  |  \  ___/\     / 
# /_______  /|___|  /\____/|   __/ \___/   |__|\___  >\/\_/  
#         \/      \/       |__|                    \/        
class ShopView(discord.ui.DesignerView):
  def __init__(self, *, cog, category: str, user: discord.Member | discord.User):
    super().__init__(timeout=360)
    self.cog = cog
    self.category = category  # photos | stickers | roles | styles
    self.user = user
    self.user_discord_id = str(user.id)

    self._interaction_lock = asyncio.Lock()
    self._ack = False
    self._ui_locked = False

    self.items: list[dict] = []
    self.owned_names: set[str] = set()
    self.role_owned = False
    self.page = 0

    self.notice: str | None = None
    self.message: discord.Message | None = None

  async def start(self, ctx: discord.ApplicationContext):
    self.items = self.cog._get_items_for_category(self.category)
    self.owned_names = await self.cog._get_owned_names(self.category, self.user.id)

    player = await get_user(self.user.id)
    self.balance = int(player['score']) if player else 0
    if self.category == "roles":
      self.role_owned = await self.cog._role_is_owned(self.user.id)
    self._rebuild_view()

    self.message = await ctx.followup.send(view=self, ephemeral=True)

  def _page_indicator_label(self) -> str:
    total = len(self.items)
    if total == 0:
      return "0/0"
    idx = (self.page % total) + 1
    return f"{idx}/{total}"

  def _current_item(self) -> dict | None:
    if not self.items:
      return None
    return self.items[self.page % len(self.items)]

  def _is_purchased(self, item: dict) -> bool:
    if self.category == "roles":
      # Right now only High Roller is supported.
      return self.role_owned
    return item["name"] in self.owned_names

  def _item_cost(self, item: dict) -> int:
    if self.category == "photos":
      return 100
    if self.category == "stickers":
      return 25
    if self.category == "roles":
      return int(item["price"])
    if self.category == "styles":
      return int(item["price"])
    raise ValueError(f"Unknown shop category: {self.category}")

  def _title_for_category(self) -> str:
    if self.category == "photos":
      return "💳  Profile Photo Shop  💳"
    if self.category == "stickers":
      return "🎖️ Profile Sticker Shop 🎖️"
    if self.category == "roles":
      return "✨ Profile Roles Shop ✨"
    if self.category == "styles":
      return "📱 Profile Styles Shop 📱"
    return "Shop"

  def _build_container(self) -> discord.ui.Container:
    item = self._current_item()

    container = discord.ui.Container(color=_shop_color().value)
    container.add_item(discord.ui.TextDisplay(f"# {self._title_for_category()}"))
    container.add_item(discord.ui.Separator())

    if not item:
      container.add_item(discord.ui.TextDisplay("No items found."))
      container.add_item(discord.ui.Separator())
      nav_row, action_row = self._build_controls(disabled=True)
      container.add_item(nav_row)
      container.add_item(action_row)
      return container

    purchased = self._is_purchased(item)
    cost = self._item_cost(item)

    container.add_item(discord.ui.TextDisplay(f"## {item['name']}"))
    if purchased:
      container.add_item(discord.ui.TextDisplay(
        f"> ✅ **Already Purchased** (~~{cost:,} Points~~)"
      ))
    else:
      container.add_item(discord.ui.TextDisplay(
        f"> 💵 **{cost:,} Points**"
      ))

    container.add_item(discord.ui.TextDisplay(
      f"-# You currently have {self.balance:,} Points to spend."
    ))

    container.add_item(discord.ui.Separator())

    preview_url = item.get("preview_url")
    if preview_url:
      container.add_gallery(
        discord.MediaGalleryItem(
          url=preview_url,
          description=item["name"]
        )
      )

    if self.notice:
      container.add_item(discord.ui.TextDisplay(f"-# {self.notice}"))

    container.add_item(discord.ui.Separator())
    nav_row, action_row = self._build_controls(disabled=False, buy_disabled=purchased)
    container.add_item(nav_row)
    container.add_item(action_row)
    return container

  def _build_controls(
    self,
    *,
    disabled: bool,
    buy_disabled: bool = False
  ) -> tuple[discord.ui.ActionRow, discord.ui.ActionRow]:
    nav_row = discord.ui.ActionRow()

    nav_disabled = disabled or self._ui_locked or (len(self.items) <= 1)

    prev_btn = discord.ui.Button(
      label="Prev",
      style=discord.ButtonStyle.secondary,
      disabled=nav_disabled
    )
    indicator = discord.ui.Button(
      label=self._page_indicator_label(),
      style=discord.ButtonStyle.secondary,
      disabled=True
    )
    next_btn = discord.ui.Button(
      label="Next",
      style=discord.ButtonStyle.secondary,
      disabled=nav_disabled
    )

    async def _nav(delta: int, interaction: discord.Interaction):
      async with self._interaction_lock:
        if self._ack:
          return
        self._ack = True
        try:
          await self._lock_ui(interaction)
          self.notice = None
          self.page = (self.page + delta) % len(self.items)
          # Unlock before rendering the new page so controls are immediately usable.
          self._ui_locked = False
          self._rebuild_view()
          # Revert: do not use self.message.edit here.
          await interaction.followup.edit_message(self.message.id, view=self)
        finally:
          self._ack = False
          self._ui_locked = False

    async def _prev_cb(interaction: discord.Interaction):
      await _nav(-1, interaction)

    async def _next_cb(interaction: discord.Interaction):
      await _nav(1, interaction)

    prev_btn.callback = _prev_cb
    next_btn.callback = _next_cb

    nav_row.add_item(prev_btn)
    nav_row.add_item(indicator)
    nav_row.add_item(next_btn)

    action_row = discord.ui.ActionRow()

    buy_is_disabled = disabled or buy_disabled or self._ui_locked or (self._current_item() is None)
    close_is_disabled = disabled or self._ui_locked

    close_btn = discord.ui.Button(
      label="Close",
      style=discord.ButtonStyle.secondary,
      disabled=close_is_disabled
    )
    buy_btn = discord.ui.Button(
      label="Buy",
      style=discord.ButtonStyle.primary,
      disabled=buy_is_disabled
    )

    async def _buy_cb(interaction: discord.Interaction):
      async with self._interaction_lock:
        if self._ack:
          return
        self._ack = True
        try:
          await self._lock_ui(interaction)

          item = self._current_item()
          if not item:
            return

          details = await self.cog._fire_purchase(
            interaction=interaction,
            category=self.category,
            item=item,
            owned_names=self.owned_names
          )

          # Keep the balance synced to the DB.
          player = await get_user(self.user.id)
          self.balance = int(player["score"]) if player else 0

          self.notice = details.get("notice")

          if details.get("success"):
            if self.category == "roles":
              self.role_owned = True
            else:
              self.owned_names.add(item["name"])

          # Unlock before rendering so the Buy/Prev/Next buttons don't stay disabled.
          self._ui_locked = False
          self._rebuild_view()
          await interaction.followup.edit_message(self.message.id, view=self)
        finally:
          self._ack = False
          self._ui_locked = False

    async def _close_cb(interaction: discord.Interaction):
      async with self._interaction_lock:
        if self._ack:
          return
        self._ack = True
        try:
          await self._lock_ui(interaction)
          await self._render_thanks(interaction)
        finally:
          self._ack = False

    buy_btn.callback = _buy_cb
    close_btn.callback = _close_cb

    # Active actions belong on the right.
    action_row.add_item(close_btn)
    action_row.add_item(buy_btn)
    return nav_row, action_row

  async def _lock_ui(self, interaction: discord.Interaction):
    self._ui_locked = True
    self._rebuild_view()
    if not interaction.response.is_done():
      await interaction.response.edit_message(view=self)

  def _unlock_ui(self):
    # The callback already edited the message; do not edit again here.
    self._ui_locked = False
    self._rebuild_view()

  async def _render_thanks(self, interaction: discord.Interaction):
    thanks = discord.ui.DesignerView(timeout=60)
    container = discord.ui.Container(color=_shop_color().value)
    container.add_item(discord.ui.TextDisplay("## Thank you for visiting The Shop!"))
    thanks.add_item(container)
    thanks.disable_all_items()

    await interaction.followup.edit_message(self.message.id, view=thanks)

  def _rebuild_view(self):
    container = self._build_container()
    self.clear_items()
    self.add_item(container)

  async def on_timeout(self):
    async with self._interaction_lock:
      self._ack = True
      self._ui_locked = True
      self._rebuild_view()
      if self.message:
        await self.message.edit(view=self)

#   _________.__                  _________                
#  /   _____/|  |__   ____ ______ \_   ___ \  ____   ____  
#  \_____  \ |  |  \ /  _ \\____ \/    \  \/ /  _ \ / ___\ 
#  /        \|   Y  (  <_> )  |_> >     \___(  <_> ) /_/  >
# /_______  /|___|  /\____/|   __/ \______  /\____/\___  / 
#         \/      \/       |__|           \/      /_____/  
class Shop(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    with open(config["commands"]["shop"]["data"], "r") as f:
      self.shop_data = json.load(f)

  shop = discord.SlashCommandGroup("shop", "Commands for purchasing /profile items")

  def _get_items_for_category(self, category: str) -> list[dict]:
    raw = self.shop_data[category]
    out: list[dict] = []
    for row in raw:
      out.append({
        "name": row["name"],
        "preview_url": row.get("preview_url"),
        "price": row.get("price"),
        "id": row.get("id")
      })
    return out

  async def _get_owned_names(self, category: str, user_id: int) -> set[str]:
    if category == "photos":
      rows = await db_get_user_profile_photos_from_inventory(user_id)
      return {r["item_name"] for r in rows}
    if category == "stickers":
      rows = await db_get_user_profile_stickers_from_inventory(user_id)
      return {r["item_name"] for r in rows}
    if category == "styles":
      rows = await db_get_user_profile_styles_from_inventory(user_id)
      return {r["item_name"] for r in rows}
    if category == "roles":
      return set()
    raise ValueError(f"Unknown shop category: {category}")

  async def _role_is_owned(self, user_id: int) -> bool:
    user = await get_user(user_id)
    return bool(user and user.get("high_roller"))

  async def _fire_purchase(
    self,
    *,
    interaction: discord.Interaction,
    category: str,
    item: dict,
    owned_names: set[str]
  ) -> dict:
    player = await get_user(interaction.user.id)
    if not player:
      return {"success": False, "notice": "❌ Player record not found."}

    cost = 0
    if category in ("photos", "stickers"):
      cost = 100 if category == "photos" else 25
    else:
      cost = int(item["price"])

    if player["score"] < cost:
      return {"success": False, "notice": f"❌ You need `{cost:,} points` to buy that item!"}

    name = item["name"]

    if category == "photos":
      if name in owned_names:
        return {"success": False, "notice": None, "reason": "already_owned"}
      await purchase_player_photo(interaction.user, name)
      await set_player_score(interaction.user, -cost)
      return {"success": True, "notice": f"Purchased **{name}**. Use `/profile set photo:` to apply it. 🎉"}

    if category == "stickers":
      if name in owned_names:
        return {"success": False, "notice": None, "reason": "already_owned"}
      await purchase_player_sticker(interaction.user, name)
      await set_player_score(interaction.user, -cost)
      return {"success": True, "notice": f"Purchased **{name}**. Use `/profile set sticker:` to apply it. 🎉"}

    if category == "styles":
      if name in owned_names:
        return {"success": False, "notice": None, "reason": "already_owned"}
      await purchase_player_style(interaction.user, name)
      await set_player_score(interaction.user, -cost)
      return {"success": True, "notice": f"Purchased **{name}**. Use `/profile set style:` to apply it. 🎉"}

    if category == "roles":
      if await self._role_is_owned(interaction.user.id):
        return {"success": False, "notice": None, "reason": "already_owned"}

      await update_player_role(interaction.user, item)
      await set_player_score(interaction.user, -cost)
      return {"success": True, "notice": f"Purchased **{name}**. Use `/profile display` to check it out. 🎉"}

    raise ValueError(f"Unknown shop category: {category}")

  @shop.command(name="photos", description="Shop for Profile photos!")
  async def photos(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    view = ShopView(cog=self, category="photos", user=ctx.user)
    await view.start(ctx)

  @shop.command(name="stickers", description="Shop for profile stickers!")
  async def stickers(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    view = ShopView(cog=self, category="stickers", user=ctx.user)
    await view.start(ctx)

  @shop.command(name="roles", description="Shop for Profile Roles!")
  async def roles(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    view = ShopView(cog=self, category="roles", user=ctx.user)
    await view.start(ctx)

  @shop.command(name="styles", description="Shop for Profile PADD Styles!")
  async def styles(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    view = ShopView(cog=self, category="styles", user=ctx.user)
    await view.start(ctx)


# ________ __________    ___ ___         .__                              
# \______ \\______   \  /   |   \   ____ |  | ______   ___________  ______
#  |    |  \|    |  _/ /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
#  |    `   \    |   \ \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \ 
# /_______  /______  /  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#         \/       \/         \/       \/     |__|        \/           \/ 
async def purchase_player_photo(user: discord.Member | discord.User, photo_name: str):
  logger.info(
    f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Photo: {Fore.CYAN}{photo_name}{Fore.RESET}"
  )
  async with AgimusDB() as db:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (str(user.id), "photo", photo_name)
    await db.execute(sql, vals)


async def purchase_player_sticker(user: discord.Member | discord.User, sticker_name: str):
  logger.info(
    f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Sticker: {Fore.CYAN}{sticker_name}{Fore.RESET}"
  )
  async with AgimusDB() as db:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (str(user.id), "sticker", sticker_name)
    await db.execute(sql, vals)


async def purchase_player_style(user: discord.Member | discord.User, style_name: str):
  logger.info(
    f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Style: {Fore.CYAN}{style_name}{Fore.RESET}"
  )
  async with AgimusDB() as db:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (str(user.id), "style", style_name)
    await db.execute(sql, vals)


async def update_player_role(user: discord.Member, role: dict):
  logger.info(
    f"Updating user {Style.BRIGHT}{user.id}{Style.RESET_ALL} with new role: {Fore.CYAN}{role['name']}{Fore.RESET}"
  )

  if role["name"] == "High Roller":
    await add_high_roller(str(user.id))

  role_id = int(role["id"])
  guild_role = user.guild.get_role(role_id)
  if guild_role and guild_role not in user.roles:
    await user.add_roles(guild_role)


async def add_high_roller(discord_id: str):
  async with AgimusDB() as db:
    sql = "UPDATE users SET high_roller = 1 WHERE discord_id = %s"
    vals = (str(discord_id),)
    await db.execute(sql, vals)
