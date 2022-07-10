#import asyncio

from common import *


class CardPage(pages.Page):
  def __init__(self, cog, embed, page_id):
    self.page_id = page_id
    super().__init__(
      embeds=[self.get_title_embed(), embed]
    )
    self.cog = cog
  
  def get_title_embed(self):
    return discord.Embed(
      title="💳  Profile Shop  💳",
      description="`100 points` each.",
      color=discord.Color(0xFFFFFF)
    ).set_footer(
      text="All proceeds go directly to the jackpot"
    )

  async def callback(self, interaction):
    try:
      self.cog.set_current_category('cards')
      self.cog.set_current_page(self.page_id)
      self.cog.set_current_page_interaction(interaction)
    except Exception:
      logger.info(traceback.format_exc())


class BuyButton(discord.ui.Button):
  def __init__(self, cog):
    self.cog = cog
    super().__init__(
      label="      Buy      ",
      style=discord.ButtonStyle.primary,
      row=0
    )

  async def callback(self, interaction: discord.Interaction):
    try:
      # Make the actual DB Purchase
      details = self.cog.fire_purchase(interaction)

      purchase_embed = discord.Embed(
        title="Purchase Complete!",
        description=details["message"],
        color=discord.Color.green()
      )
      if not details["success"]:
        purchase_embed = discord.Embed(
          title="Transaction Declined!",
          description=details["message"],
          color=discord.Color.red()
        )

      # Determine how we need to reply
      # (initial Paginator interaction load is an 'InteractionMessage',
      # while subsequent are 'Interaction'... Bleh)
      current_interaction = self.cog.current_page_interaction
      current_interaction_type = type(current_interaction).__name__

      if current_interaction_type == 'Interaction':
        await current_interaction.edit_original_message(
          embed=purchase_embed,
          view=None
        )
      elif current_interaction_type == 'InteractionMessage':
        await current_interaction.edit(
          embed=purchase_embed,
          view=None
        )

      await interaction.response.send_message(embed=discord.Embed(
        title="Thank you for visiting The Shop!",
        color=discord.Color(0xFFFFFF)
      ), ephemeral=True)
    except Exception as e:
      logger.exception("FAIL")

# 
# 
#
class Shop(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.current_category = 'cards'
    self.current_page = 0
    self.current_page_interaction = None

    f = open(config["commands"]["shop"]["data"])
    self.shop_data = json.load(f)
    f.close()

    self.card_pages = []
    for idx, card in enumerate(self.shop_data["cards"]):
      card_embed = discord.Embed(
        title=card["name"],
        color=discord.Color(0xFFFFFF)
      )
      card_embed.set_image(url=card["preview_url"])
      card_page = CardPage(self, card_embed, idx)
      self.card_pages.append(card_page)

  def set_current_category(self, category):
    self.current_category = category

  def set_current_page(self, id):
    self.current_page = id

  def set_current_page_interaction(self, interaction):
    self.current_page_interaction = interaction

  def get_pages(self):
    return self.card_pages

  def get_custom_buttons(self):
    return [
      pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.green, row=1),
      pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
      ),
      pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.green, row=1),
    ]

  def fire_purchase(self, interaction):
    cost = 100

    player = get_user(interaction.user.id)
    result = {}
    if player["score"] < cost:
      result["success"] = False
      result["message"] = f"You need `{cost} points` to buy that item!"
    else:
      current_card = self.shop_data["cards"][self.current_page]
      update_player_profile_card(interaction.user.id, current_card["name"].lower())
      result["success"] = True
      result["message"] = f"You have spent `{cost} points` and purchased the **{current_card['name']}** profile card!\n\nType `/profile` to check it out!"

    return result

  # These examples use a Slash Command Group in a cog for better organization - it's not required for using ext.pages.
  @commands.slash_command(
    name="shoptest"
  )
  async def shoptest(self, ctx: discord.ApplicationContext):
    self.set_current_page(0)

    view = discord.ui.View()
    view.add_item(BuyButton(self))

    paginator = pages.Paginator(
      pages=self.get_pages(),
      use_default_buttons=False,
      custom_buttons=self.get_custom_buttons(),
      trigger_on_display=True,
      custom_view=view
    )
    original_interaction = await paginator.respond(ctx.interaction, ephemeral=True)
    self.set_current_page_interaction(original_interaction)

    # @pagetest.command(name="hidden")
    # async def pagetest_hidden(self, ctx: discord.ApplicationContext):
    #     """Demonstrates using the paginator with disabled buttons hidden."""
    #     paginator = pages.Paginator(pages=self.get_pages(), show_disabled=False)
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="loop")
    # async def pagetest_loop(self, ctx: discord.ApplicationContext):
    #     """Demonstrates using the loop_pages option."""
    #     paginator = pages.Paginator(pages=self.get_pages(), loop_pages=True)
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="strings")
    # async def pagetest_strings(self, ctx: discord.ApplicationContext):
    #     """Demonstrates passing a list of strings as pages."""
    #     paginator = pages.Paginator(
    #         pages=["Page 1", "Page 2", "Page 3"], loop_pages=True
    #     )
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="timeout")
    # async def pagetest_timeout(self, ctx: discord.ApplicationContext):
    #     """Demonstrates having the buttons be disabled when the paginator view times out."""
    #     paginator = pages.Paginator(
    #         pages=self.get_pages(), disable_on_timeout=True, timeout=30
    #     )
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="remove_buttons")
    # async def pagetest_remove(self, ctx: discord.ApplicationContext):
    #     """Demonstrates using the default buttons, but removing some of them."""
    #     paginator = pages.Paginator(pages=self.get_pages())
    #     paginator.remove_button("first")
    #     paginator.remove_button("last")
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="init")
    # async def pagetest_init(self, ctx: discord.ApplicationContext):
    #     """Demonstrates how to pass a list of custom buttons when creating the Paginator instance."""
    #     pagelist = [
    #         pages.PaginatorButton(
    #             "first", label="<<-", style=discord.ButtonStyle.green
    #         ),
    #         pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton(
    #             "page_indicator", style=discord.ButtonStyle.gray, disabled=True
    #         ),
    #         pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton("last", label="->>", style=discord.ButtonStyle.green),
    #     ]
    #     paginator = pages.Paginator(
    #         pages=self.get_pages(),
    #         show_disabled=True,
    #         show_indicator=True,
    #         use_default_buttons=False,
    #         custom_buttons=pagelist,
    #         loop_pages=True,
    #     )
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="emoji_buttons")
    # async def pagetest_emoji_buttons(self, ctx: discord.ApplicationContext):
    #     """Demonstrates using emojis for the paginator buttons instead of labels."""
    #     page_buttons = [
    #         pages.PaginatorButton(
    #             "first", emoji="⏪", style=discord.ButtonStyle.green
    #         ),
    #         pages.PaginatorButton("prev", emoji="⬅", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton(
    #             "page_indicator", style=discord.ButtonStyle.gray, disabled=True
    #         ),
    #         pages.PaginatorButton("next", emoji="➡", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton("last", emoji="⏩", style=discord.ButtonStyle.green),
    #     ]
    #     paginator = pages.Paginator(
    #         pages=self.get_pages(),
    #         show_disabled=True,
    #         show_indicator=True,
    #         use_default_buttons=False,
    #         custom_buttons=page_buttons,
    #         loop_pages=True,
    #     )
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="custom_buttons")
    # async def pagetest_custom_buttons(self, ctx: discord.ApplicationContext):
    #     """Demonstrates adding buttons to the paginator when the default buttons are not used."""
    #     paginator = pages.Paginator(
    #         pages=self.get_pages(),
    #         use_default_buttons=False,
    #         loop_pages=False,
    #         show_disabled=False,
    #     )
    #     paginator.add_button(
    #         pages.PaginatorButton(
    #             "prev", label="<", style=discord.ButtonStyle.green, loop_label="lst"
    #         )
    #     )
    #     paginator.add_button(
    #         pages.PaginatorButton(
    #             "page_indicator", style=discord.ButtonStyle.gray, disabled=True
    #         )
    #     )
    #     paginator.add_button(
    #         pages.PaginatorButton(
    #             "next", style=discord.ButtonStyle.green, loop_label="fst"
    #         )
    #     )
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="custom_view")
    # async def pagetest_custom_view(self, ctx: discord.ApplicationContext):
    #     """Demonstrates passing a custom view to the paginator."""
    #     view = discord.ui.View()
    #     view.add_item(discord.ui.Button(label="Test Button, Does Nothing", row=1))
    #     view.add_item(
    #         discord.ui.Select(
    #             placeholder="Test Select Menu, Does Nothing",
    #             options=[
    #                 discord.SelectOption(
    #                     label="Example Option",
    #                     value="Example Value",
    #                     description="This menu does nothing!",
    #                 )
    #             ],
    #         )
    #     )
    #     paginator = pages.Paginator(pages=self.get_pages(), custom_view=view)
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="groups")
    # async def pagetest_groups(self, ctx: discord.ApplicationContext):
    #     """Demonstrates using page groups to switch between different sets of pages."""
    #     page_buttons = [
    #         pages.PaginatorButton(
    #             "first", label="<<-", style=discord.ButtonStyle.green
    #         ),
    #         pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton(
    #             "page_indicator", style=discord.ButtonStyle.gray, disabled=True
    #         ),
    #         pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.green),
    #         pages.PaginatorButton("last", label="->>", style=discord.ButtonStyle.green),
    #     ]
    #     view = discord.ui.View()
    #     view.add_item(discord.ui.Button(label="Test Button, Does Nothing", row=2))
    #     view.add_item(
    #         discord.ui.Select(
    #             placeholder="Test Select Menu, Does Nothing",
    #             options=[
    #                 discord.SelectOption(
    #                     label="Example Option",
    #                     value="Example Value",
    #                     description="This menu does nothing!",
    #                 )
    #             ],
    #         )
    #     )
    #     page_groups = [
    #         pages.PageGroup(
    #             pages=self.get_pages(),
    #             label="Main Page Group",
    #             description="Main Pages for Main Things",
    #         ),
    #         pages.PageGroup(
    #             pages=[
    #                 "Second Set of Pages, Page 1",
    #                 "Second Set of Pages, Page 2",
    #                 "Look, it's group 2, page 3!",
    #             ],
    #             label="Second Page Group",
    #             description="Secondary Pages for Secondary Things",
    #             custom_buttons=page_buttons,
    #             use_default_buttons=False,
    #             custom_view=view,
    #         ),
    #     ]
    #     paginator = pages.Paginator(pages=page_groups, show_menu=True)
    #     await paginator.respond(ctx.interaction, ephemeral=False)

    # @pagetest.command(name="update")
    # async def pagetest_update(self, ctx: discord.ApplicationContext):
    #     """Demonstrates updating an existing paginator instance with different options."""
    #     paginator = pages.Paginator(pages=self.get_pages(), show_disabled=False)
    #     await paginator.respond(ctx.interaction)
    #     await asyncio.sleep(3)
    #     await paginator.update(show_disabled=True, show_indicator=False)

    # @pagetest.command(name="target")
    # async def pagetest_target(self, ctx: discord.ApplicationContext):
    #     """Demonstrates sending the paginator to a different target than where it was invoked."""
    #     paginator = pages.Paginator(pages=self.get_pages())
    #     await paginator.respond(ctx.interaction, target=ctx.interaction.user)

    # @commands.command()
    # async def pagetest_prefix(self, ctx: commands.Context):
    #     """Demonstrates using the paginator with a prefix-based command."""
    #     paginator = pages.Paginator(pages=self.get_pages(), use_default_buttons=False)
    #     paginator.add_button(
    #         pages.PaginatorButton("prev", label="<", style=discord.ButtonStyle.green)
    #     )
    #     paginator.add_button(
    #         pages.PaginatorButton(
    #             "page_indicator", style=discord.ButtonStyle.gray, disabled=True
    #         )
    #     )
    #     paginator.add_button(
    #         pages.PaginatorButton("next", style=discord.ButtonStyle.green)
    #     )
    #     await paginator.send(ctx)

    # @commands.command()
    # async def pagetest_target(self, ctx: commands.Context):
    #     """Demonstrates sending the paginator to a different target than where it was invoked (prefix-command version)."""
    #     paginator = pages.Paginator(pages=self.get_pages())
    #     await paginator.send(ctx, target=ctx.author, target_message="Paginator sent!")

