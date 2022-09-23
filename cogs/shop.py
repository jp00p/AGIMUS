from common import *

from cogs.profile import db_get_user_profile_styles_from_inventory, db_get_user_profile_stickers_from_inventory, db_get_user_profile_photos_from_inventory


#   _________.__                 __________
#  /   _____/|  |__   ____ ______\______   \_____     ____   ____
#  \_____  \ |  |  \ /  _ \\____ \|     ___/\__  \   / ___\_/ __ \
#  /        \|   Y  (  <_> )  |_> >    |     / __ \_/ /_/  >  ___/
# /_______  /|___|  /\____/|   __/|____|    (____  /\___  / \___  >
#         \/      \/       |__|                  \//_____/      \/
class ShopPage(pages.Page):
  def __init__(self, cog, embed, category, page_id):
    self.category = category
    self.page_id = page_id
    super().__init__(
      embeds=[embed]
    )
    self.cog = cog

  # When page is loaded, set the purchase record with page-info
  async def callback(self, interaction):
    try:
      self.cog.upsert_purchase_record(interaction.user.id, {
        "category": self.category,
        "page": self.page_id,
        "page_interaction": interaction
      })
    except Exception:
      logger.info(traceback.format_exc())


# __________              __________        __    __
# \______   \__ __ ___.__.\______   \__ ___/  |__/  |_  ____   ____
#  |    |  _/  |  <   |  | |    |  _/  |  \   __\   __\/  _ \ /    \
#  |    |   \  |  /\___  | |    |   \  |  /|  |  |  | (  <_> )   |  \
#  |______  /____/ / ____| |______  /____/ |__|  |__|  \____/|___|  /
#         \/       \/             \/                              \/
class BuyButton(discord.ui.Button):
  def __init__(self, cog):
    self.cog = cog
    super().__init__(
      label="      Buy      ",
      style=discord.ButtonStyle.primary,
      row=0
    )

  async def callback(self, interaction: discord.Interaction):
    await self.cog.buy_button_callback(interaction)



#   _________.__                    _________
#  /   _____/|  |__   ____ ______   \_   ___ \  ____   ____
#  \_____  \ |  |  \ /  _ \\____ \  /    \  \/ /  _ \ / ___\
#  /        \|   Y  (  <_> )  |_> > \     \___(  <_> ) /_/  >
# /_______  /|___|  /\____/|   __/   \______  /\____/\___  /
#         \/      \/       |__|             \/      /_____/
class Shop(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.purchase_records = {}

    f = open(config["commands"]["shop"]["data"])
    self.shop_data = json.load(f)
    f.close()

    self.init_photo_pages()
    self.init_sticker_pages()
    self.init_role_pages()
    self.init_style_pages()


  def init_photo_pages(self):
    self.photo_pages = []
    for idx, photo in enumerate(self.shop_data["photos"]):
      photo_embed = discord.Embed(
        title="💳  Profile Photo Shop  💳",
        description=f"`100 points` each.\n\n**{photo['name']}**",
        color=discord.Color(0xFFFFFF)
      )
      photo_embed.set_image(url=photo["preview_url"])
      photo_embed.set_footer(
        text="All proceeds go directly to the jackpot!"
      )
      photo_page = ShopPage(self, photo_embed, "photos", idx)
      self.photo_pages.append(photo_page)

  def get_photo_pages(self):
    return self.photo_pages


  def init_sticker_pages(self):
    self.sticker_pages = []
    for idx, sticker in enumerate(self.shop_data["stickers"]):
      sticker_embed = discord.Embed(
        title="🎖️ Profile Sticker Shop 🎖️",
        description=f"`25 points` each.\n\n**{sticker['name']}**",
        color=discord.Color(0xFFFFFF)
      )
      sticker_embed.set_image(url=sticker["preview_url"])
      sticker_embed.set_footer(
        text="All proceeds go directly to the jackpot!"
      )
      sticker_page = ShopPage(self, sticker_embed, "stickers", idx)
      self.sticker_pages.append(sticker_page)

  def get_sticker_pages(self):
    return self.sticker_pages


  def init_role_pages(self):
    self.role_pages = []
    for idx, role in enumerate(self.shop_data["roles"]):
      role_embed = discord.Embed(
        title="✨ Profile Roles Shop ✨",
        description=f"`{role['price']} points`.\n\n**{role['name']}**",
        color=discord.Color(0xFFFFFF)
      )
      role_embed.set_image(url=role["preview_url"])
      role_embed.set_footer(
        text="All proceeds go directly to the jackpot!"
      )
      card_page = ShopPage(self, role_embed, "roles", idx)
      self.role_pages.append(card_page)

  def get_role_pages(self):
    return self.role_pages

  def init_style_pages(self):
    self.style_pages = []
    for idx, style in enumerate(self.shop_data["styles"]):
      style_embed = discord.Embed(
        title="📱 Profile Styles Shop 📱",
        description=f"`{style['price']} points`.\n\n**{style['name']}**",
        color=discord.Color(0xFFFFFF)
      )
      style_embed.set_image(url=style["preview_url"])
      style_embed.set_footer(
        text="All proceeds go directly to the jackpot!"
      )
      card_page = ShopPage(self, style_embed, "styles", idx)
      self.style_pages.append(card_page)

  def get_style_pages(self):
    return self.style_pages


  def get_purchase_record(self, interaction):
    user_id = interaction.user.id
    purchase_record = self.purchase_records.get(user_id)
    return purchase_record

  def upsert_purchase_record(self, user_id, update):
    self.purchase_records[user_id] = update

  def delete_purchase_record(self, user_id):
    self.purchase_records.pop(user_id)


  async def fire_purchase(self, interaction, purchase_record):
    try:
      cost = 0
      category = purchase_record["category"]
      if category == "photos":
        cost = 100
      elif category == "stickers":
        cost = 25

      player = get_user(interaction.user.id)
      result = {}
      if player["score"] < cost:
        result["success"] = False
        result["message"] = f"You need `{cost} points` to buy that item!"

      else:
        if category == "photos":
          photo = self.shop_data["photos"][purchase_record["page"]]
          photo_name = photo["name"]
          existing_player_photos = [s['item_name'] for s in db_get_user_profile_photos_from_inventory(interaction.user.id)]

          if photo_name in existing_player_photos:
            result["success"] = False
            result["message"] = f"You already own {photo_name}! No action taken."
          else:
            await purchase_player_photo(interaction.user, photo_name)
            result["success"] = True
            result["message"] = f"You have spent `{cost} points` and purchased the **{photo_name}** profile photo!\n\nType `/profile set_photo` to apply it to your PADD!"

        elif category == "stickers":
          sticker = self.shop_data["stickers"][purchase_record["page"]]
          sticker_name = sticker["name"]
          existing_player_stickers = [s['item_name'] for s in db_get_user_profile_stickers_from_inventory(interaction.user.id)]

          if sticker_name in existing_player_stickers:
            result["success"] = False
            result["message"] = f"You already own {sticker_name}! No action taken."
          else:
            await purchase_player_sticker(interaction.user, sticker_name)
            result["success"] = True
            result["message"] = f"You have spent `{cost} points` and purchased the **{sticker_name}** sticker!\n\nType `/profile set_sticker` to apply it to your PADD!"

        elif category == "roles":
          role = self.shop_data["roles"][purchase_record["page"]]
          role_name = role["name"]
          # Special Case for Roles, they may have different prices so need to check this again here:
          cost = role["price"]
          if player["score"] < cost:
            result["success"] = False
            result["message"] = f"You need `{cost} points` to buy that item!"
          # NOTE: We'll need to clean this check up later if we add additional roles...
          elif player["high_roller"]:
            result["success"] = False
            result["message"] = f"You already have the **{role_name}** role! \nWe gotchu, no points spent.\n\nType `/profile display` to check it out!"
          else:
            await update_player_role(interaction.user, role)
            result["success"] = True
            result["message"] = f"You have spent `{cost} points` and purchased the **{role_name}** role!\n\nType `/profile display` to check it out!"

        elif category == "styles":
          style = self.shop_data["styles"][purchase_record["page"]]
          style_name = style["name"]
          # Special Case for Styles, they may have different prices so need to check this again here:
          cost = style["price"]

          existing_player_styles = [s['item_name'] for s in db_get_user_profile_styles_from_inventory(interaction.user.id)]

          if style_name in existing_player_styles:
            result["success"] = False
            result["message"] = f"You already own {style_name}! No action taken."
          elif player["score"] < cost:
            result["success"] = False
            result["message"] = f"You need `{cost} points` to buy that item!"
          else:
            await purchase_player_style(interaction.user, style_name)
            result["success"] = True
            result["message"] = f"You have spent `{cost} points` and purchased the **{style_name}** profile style!\n\nType `/profile set_style` to enable it, then `/profile display` to show it off!"

      if result["success"]:
        set_player_score(interaction.user, -cost)

      return result
    except Exception:
      logger.info(traceback.format_exc())


  async def edit_interaction_with_thanks(self, page_interaction):
    thank_you_embed = discord.Embed(
      title="Thank you for visiting The Shop!",
      color=discord.Color(0xFFFFFF)
    )

    try:
      page_interaction_type = type(page_interaction).__name__
      if page_interaction_type == 'Interaction':
        original_message = await page_interaction.original_message()
        if original_message != None:
          await original_message.edit(
            embed=thank_you_embed,
            view=None
          )
      elif page_interaction_type == 'InteractionMessage':
        await page_interaction.edit(
          embed=thank_you_embed,
          view=None
        )
    except discord.HTTPException as e:
      logger.info("Encountered error editing original shop message. Passing as okay, logging error:")
      logger.info(traceback.format_exc())
      pass



  async def buy_button_callback(self, interaction):
    # Try to make the actual DB Purchase
    purchase_record = self.get_purchase_record(interaction)
    details = await self.fire_purchase(interaction, purchase_record)

    # Edit original Shop message with a thank you before sending confirmation message
    original_interaction = purchase_record["page_interaction"]
    await self.edit_interaction_with_thanks(original_interaction)

    purchase_embed = discord.Embed(
      title="Purchase Complete!",
      description=details["message"],
      color=discord.Color(0xFFFFFF)
    )
    if not details["success"]:
      purchase_embed = discord.Embed(
        title="Transaction Declined!",
        description=details["message"],
        color=discord.Color.red()
      )

    await interaction.response.send_message(embed=purchase_embed, ephemeral=True)

    self.delete_purchase_record(interaction.user.id)

  def get_custom_buttons(self):
    return [
      pages.PaginatorButton("prev", label=" ⬅ ", style=discord.ButtonStyle.green, row=1),
      pages.PaginatorButton(
        "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label=" ➡ ", style=discord.ButtonStyle.green, row=1),
    ]


  shop = discord.SlashCommandGroup("shop", "Commands for purchasing /profile items")

  @shop.command(
    name="photos",
    description="Shop for Profile photos!"
  )
  async def photos(self, ctx: discord.ApplicationContext):
    try:
      existing_purchase_record = self.get_purchase_record(ctx)

      if existing_purchase_record:
        existing_page_interaction = existing_purchase_record["page_interaction"]
        await self.edit_interaction_with_thanks(existing_page_interaction)

      view = discord.ui.View()
      view.add_item(BuyButton(self))

      paginator = pages.Paginator(
        pages=self.get_photo_pages(),
        use_default_buttons=False,
        custom_buttons=self.get_custom_buttons(),
        trigger_on_display=True,
        custom_view=view,
        loop_pages=True
      )
      original_interaction = await paginator.respond(ctx.interaction, ephemeral=True)
      self.upsert_purchase_record(ctx.author.id, {
        "category": "photos",
        "page": 0,
        "page_interaction": original_interaction
      })
    except Exception as e:
      logger.info(traceback.format_exc())


  @shop.command(
    name="stickers",
    description="Shop for profile stickers!"
  )
  async def stickers(self, ctx: discord.ApplicationContext):
    try:
      existing_purchase_record = self.get_purchase_record(ctx)

      if existing_purchase_record:
        existing_page_interaction = existing_purchase_record["page_interaction"]
        await self.edit_interaction_with_thanks(existing_page_interaction)

      view = discord.ui.View()
      view.add_item(BuyButton(self))

      paginator = pages.Paginator(
        pages=self.get_sticker_pages(),
        use_default_buttons=False,
        custom_buttons=self.get_custom_buttons(),
        trigger_on_display=True,
        custom_view=view,
        loop_pages=True
      )
      original_interaction = await paginator.respond(ctx.interaction, ephemeral=True)
      self.upsert_purchase_record(ctx.author.id, {
        "category": "stickers",
        "page": 0,
        "page_interaction": original_interaction
      })
    except Exception as e:
      logger.info(traceback.format_exc())


  @shop.command(
    name="roles",
    description="Shop for Profile Roles!"
  )
  async def roles(self, ctx: discord.ApplicationContext):
    try:
      existing_purchase_record = self.get_purchase_record(ctx)

      if existing_purchase_record:
        existing_page_interaction = existing_purchase_record["page_interaction"]
        await self.edit_interaction_with_thanks(existing_page_interaction)

      view = discord.ui.View()
      view.add_item(BuyButton(self))

      paginator = pages.Paginator(
        pages=self.get_role_pages(),
        use_default_buttons=False,
        custom_buttons=self.get_custom_buttons(),
        trigger_on_display=True,
        custom_view=view,
        loop_pages=True
      )
      original_interaction = await paginator.respond(ctx.interaction, ephemeral=True)
      self.upsert_purchase_record(ctx.author.id, {
        "category": "roles",
        "page": 0,
        "page_interaction": original_interaction
      })
    except Exception as e:
      logger.info(traceback.format_exc())


  @shop.command(
    name="styles",
    description="Shop for Profile PADD Styles!"
  )
  async def styles(self, ctx: discord.ApplicationContext):
    try:
      existing_purchase_record = self.get_purchase_record(ctx)

      if existing_purchase_record:
        existing_page_interaction = existing_purchase_record["page_interaction"]
        await self.edit_interaction_with_thanks(existing_page_interaction)

      view = discord.ui.View()
      view.add_item(BuyButton(self))

      paginator = pages.Paginator(
        pages=self.get_style_pages(),
        use_default_buttons=False,
        custom_buttons=self.get_custom_buttons(),
        trigger_on_display=True,
        custom_view=view,
        loop_pages=True
      )
      original_interaction = await paginator.respond(ctx.interaction, ephemeral=True)
      self.upsert_purchase_record(ctx.author.id, {
        "category": "styles",
        "page": 0,
        "page_interaction": original_interaction
      })
    except Exception as e:
      logger.info(traceback.format_exc())



# ________          __        ___.
# \______ \ _____ _/  |______ \_ |__ _____    ______ ____
#  |    |  \\__  \\   __\__  \ | __ \\__  \  /  ___// __ \
#  |    `   \/ __ \|  |  / __ \| \_\ \/ __ \_\___ \\  ___/
# /_______  (____  /__| (____  /___  (____  /____  >\___  >
#         \/     \/          \/    \/     \/     \/     \/

async def purchase_player_photo(user, photo_name):
  logger.info(f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Photo: {Fore.CYAN}{photo_name}{Fore.RESET}")
  with AgimusDB() as query:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (user.id, "photo", photo_name)
    query.execute(sql, vals)


async def purchase_player_sticker(user, sticker_name):
  logger.info(f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Sticker: {Fore.CYAN}{sticker_name}{Fore.RESET}")
  with AgimusDB() as query:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (user.id, "sticker", sticker_name)
    query.execute(sql, vals)


async def purchase_player_style(user, style_name):
  logger.info(f"Granting user {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} new Profile PADD Style: {Fore.CYAN}{style_name}{Fore.RESET}")
  with AgimusDB() as query:
    sql = "INSERT INTO profile_inventory (user_discord_id, item_category, item_name) VALUES (%s, %s, %s)"
    vals = (user.id, "style", style_name)
    query.execute(sql, vals)


async def update_player_role(user, role):
  """
  update_player_role(user, role)

  user[required]: object
  role[required]: string

  This function will add a discord role to a specific user
  """
  logger.info(f"Updating user {Style.BRIGHT}{user.id}{Style.RESET_ALL} with new role: {Fore.CYAN}{role['name']}{Fore.RESET}")
  role_id = role["id"]
  if role["name"] == "High Roller":
    add_high_roller(user.id)
  guild_role = user.guild.get_role(role_id)
  if guild_role not in user.roles:
    await user.add_roles(guild_role)


def add_high_roller(discord_id):
  """
  add_high_roller(discord_id)

  discord_id[required]: int

  This function will set a specific user's high_roller value to '1' by discord user id
  """
  with AgimusDB() as query:
    sql = "UPDATE users SET high_roller = 1 WHERE discord_id = %s"
    vals = (discord_id,)
    query.execute(sql, vals)
