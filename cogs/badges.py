from dateutil import tz
from io import BytesIO

from common import *

from utils.echelon_rewards import *
from utils.badge_trades import *
from utils.badge_utils import *
from utils.check_channel_access import access_check
from utils.encode_utils import encode_webp
from utils.image_utils import *
from utils.prestige import PRESTIGE_TIERS, autocomplete_prestige_tiers, is_prestige_valid
from utils.string_utils import *

from queries.badge_completion import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.badge_scrap import *
from queries.crystal_instances import *
from queries.wishlists import *
from queries.trade import *

# -> cogs.badges

class Badges(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  #    _____          __                                     .__          __
  #   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
  #  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
  # /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
  # \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
  #         \/                        \/            \/|__|             \/          \/
  async def all_badges_autocomplete(ctx:discord.AutocompleteContext):
    return [badge['badge_name'] for badge in await db_get_all_badge_info() if strip_bullshit(ctx.value.lower()) in strip_bullshit(badge['badge_name'].lower())]

  async def autocomplete_users_badges(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    prestige_level = int(ctx.options['prestige'])

    user_badge_instances = await db_get_user_badge_instances(user_id, prestige=prestige_level)

    results = [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in user_badge_instances
    ]

    filtered = [r for r in results if strip_bullshit(ctx.value.lower()) in strip_bullshit(r.name.lower())]
    if not filtered:
      filtered = [
        discord.OptionChoice(
          name="[ No Valid Options ]",
          value="none"
        )
      ]
    return filtered

  # async def scrapper_autocomplete(ctx:discord.AutocompleteContext):
  #   first_badge = ctx.options["first_badge"]
  #   second_badge = ctx.options["second_badge"]
  #   third_badge = ctx.options["third_badge"]

  #   user_badges = await db_get_user_badge_instances(ctx.interaction.user.id, locked=False)

  #   filtered_badges = [first_badge, second_badge, third_badge] + [b['badge_name'] for b in await db_get_special_badge_info()]
  #   filtered_badge_names = [badge['badge_name'] for badge in user_badges if badge['badge_name'] not in filtered_badges]

  #   return [b for b in filtered_badge_names if ctx.value.lower() in b.lower()]

  badge_group = discord.SlashCommandGroup("badges", "Badge Commands!")


  # _________        .__  .__                 __  .__
  # \_   ___ \  ____ |  | |  |   ____   _____/  |_|__| ____   ____
  # /    \  \/ /  _ \|  | |  | _/ __ \_/ ___\   __\  |/  _ \ /    \
  # \     \___(  <_> )  |_|  |_\  ___/\  \___|  | |  (  <_> )   |  \
  #  \______  /\____/|____/____/\___  >\___  >__| |__|\____/|___|  /
  #         \/                      \/     \/                    \/
  @badge_group.command(
    name="collection",
    description="Show off all your badges! Please be mindful of posting very large collections publicly."
  )
  @option(
    'public',
    str,
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  @option(
    'prestige',
    str,
    description="Which Prestige Tier to display?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'filter',
    str,
    description="Show only Locked, Unlocked, or Special badges?",
    required=False,
    choices=[
      discord.OptionChoice(
        name="Unlocked",
        value="unlocked"
      ),
      discord.OptionChoice(
        name="Locked",
        value="locked"
      ),
      discord.OptionChoice(
        name="Special",
        value="special"
      ),
      discord.OptionChoice(
        name="Crystallized",
        value="crystallized"
      ),
    ]
  )
  @option(
    'sortby',
    str,
    description="Sort your collection",
    required=False,
    choices=[
      discord.OptionChoice(
        name="Date Ascending",
        value="date_ascending"
      ),
      discord.OptionChoice(
        name="Date Descending",
        value="date_descending"
      ),
      discord.OptionChoice(
        name="Locked First",
        value="locked_first"
      ),
      discord.OptionChoice(
        name="Special First",
        value="special_first"
      ),
    ]
  )
  @option(
    'color',
    str,
    description="Which colorscheme would you like? (Applies to Standard Tier)",
    required=False,
    choices = [
      discord.OptionChoice(name=color_choice, value=color_choice.lower())
      for color_choice in ["Green", "Orange", "Purple", "Teal"]
    ]
  )
  async def collection(self, ctx:discord.ApplicationContext, prestige:str, public:str, filter:str, sortby:str, color:str):
    public = (public == "yes")
    logger.info(f"{ctx.author.display_name} is pulling up their {Style.BRIGHT}`/badges collection`{Style.RESET_ALL}!")

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    pending_message = await ctx.respond(
      embed=discord.Embed(
        title="Collection Display Request Received!",
        description=f"If you have a large collection this miiiiiight take a while...\n\nDon't worry, AGIMUS is on it! {get_emoji('agimus_smile_happy')}",
        color=discord.Color.dark_green()
      ),
      ephemeral=True
    )

    if filter is not None:
      max_collected = await db_get_badge_instances_count_for_user(ctx.author.id, prestige=prestige)
      if filter == 'unlocked':
        user_badges = await db_get_user_badge_instances(ctx.author.id, prestige=prestige, locked=False, sortby=sortby)
        max_collected = await db_get_badge_instances_count_for_user(ctx.author.id, prestige=prestige, special=False)
      elif filter == 'locked':
        user_badges = await db_get_user_badge_instances(ctx.author.id, prestige=prestige, locked=True, sortby=sortby)
        max_collected = await db_get_badge_instances_count_for_user(ctx.author.id, prestige=prestige, special=False)
      elif filter == 'special':
        user_badges = await db_get_user_badge_instances(ctx.author.id, prestige=prestige, special=True, sortby=sortby)
      elif filter == 'crystallized':
        user_badges = await db_get_user_badge_instances(ctx.author.id, prestige=prestige, crystallized=True, sortby=sortby)
      collection_label = filter.title()
    else:
      user_badges = await db_get_user_badge_instances(ctx.author.id, prestige=prestige, sortby=sortby)
      max_collected = await db_get_max_badge_count()
      collection_label = None

    if not user_badges:
      await ctx.followup.send(embed=discord.Embed(
          title="No Badges To Display!",
          description="You don't appear to either have any badges, or any that match this filter!",
          color=discord.Color.red()
        )
      )
      return

    title = f"{remove_emoji(ctx.author.display_name)}'s Badge Collection [{PRESTIGE_TIERS[prestige]}]"
    if collection_label:
      title += f": {collection_label}"

    if sortby is not None:
      if collection_label:
        collection_label += f" [{PRESTIGE_TIERS[prestige]}] - {sortby.replace('_', ' ').title()}"
      title += f" - {sortby.replace('_', ' ').title()}"

    if color:
      await db_set_user_badge_page_color_preference(ctx.author.id, "collection", color)

    badge_images = await generate_badge_collection_images(ctx.author, prestige, user_badges, 'collection', collection_label, discord_message=pending_message)

    await pending_message.edit(
      embed=discord.Embed(
        title="Collection Display Request Complete!",
        description="Phew, here you go!",
        color=discord.Color.dark_green()
      )
    )

    # Generation complete, do the thing!
    embed = discord.Embed(
      title=title,
      description=f"{ctx.author.mention} has {len(user_badges)} of {max_collected}!",
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, disabled=bool(len(user_badges) <= 30), row=1),
        pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1),
        pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, disabled=bool(len(user_badges) <= 30), row=1),
      ]

      class CollectionPaginator(pages.Paginator):
        def __init__(self, *args, badge_files: list[discord.File], **kwargs):
          self.badge_files = badge_files
          super().__init__(*args, **kwargs)

        async def on_timeout(self):
          # Close all buffers after timeout
          for f in self.badge_files:
            try:
              f.fp.close()
            except Exception:
              pass
          self.badge_files.clear()
          gc.collect()

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]

      paginator = CollectionPaginator(
        pages=pages_list,
        badge_files=badge_images,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True,
        timeout=600
      )
      await paginator.respond(ctx.interaction, ephemeral=True)

    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk)
        else:
          await ctx.followup.send(files=chunk)
        # Immediately close files after sending
        for f in chunk:
          try:
            f.fp.close()
          except Exception:
            pass
    badge_images.clear()
    gc.collect()


  # ____ ___                                     .___
  # |    |   \____   ______  _  ______   ____   __| _/
  # |    |   /    \ /  _ \ \/ \/ /    \_/ __ \ / __ |
  # |    |  /   |  (  <_> )     /   |  \  ___// /_/ |
  # |______/|___|  /\____/ \/\_/|___|  /\___  >____ |
  #             \/                  \/     \/     \/
  @badge_group.command(
    name="unowned",
    description="See which badges you're still missing at a given Prestige Tier."
  )
  @option(
    'public',
    str,
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(name="No", value="no"),
      discord.OptionChoice(name="Yes", value="yes")
    ]
  )
  @option(
    'prestige',
    str,
    description="Which Prestige Tier to check?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'color',
    str,
    description="Which colorscheme would you like? (Only applies to Standard Tier)",
    required=False,
    choices = [
      discord.OptionChoice(name=color_choice, value=color_choice.lower())
      for color_choice in ["Green", "Orange", "Purple", "Teal"]
    ]
  )
  @commands.check(access_check)
  async def unowned(self, ctx: discord.ApplicationContext, public: str, prestige: str, color: str = None):
    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)
    public = (public == "yes")

    logger.info(f"{ctx.author.display_name} is pulling up their {Style.BRIGHT}`/badges unowned`{Style.RESET_ALL} badges for their {Style.BRIGHT}{PRESTIGE_TIERS[prestige]}{Style.RESET_ALL} Tier!")

    unowned_badges = await db_get_unowned_user_badge_instances(ctx.author.id, prestige)

    if not unowned_badges:
      await ctx.respond(
        embed=discord.Embed(
          title="You've Collected Them All!",
          description="You already own every badge available at this Prestige Tier! Wowzers.",
          color=discord.Color.green()
        ),
        ephemeral=True
      )
      return

    pending_message = await ctx.respond(
      embed=discord.Embed(
        title="Unowned Badge List Request Received!",
        description=f"Compiling your uncollected badge records...\nStand by! {get_emoji('badgey_smile_happy')}",
        color=discord.Color.dark_teal()
      ),
      ephemeral=not public
    )

    if color:
      await db_set_user_badge_page_color_preference(ctx.author.id, "collection", color)

    collection_label = "Unowned"
    badge_images = await generate_badge_collection_images(
      user=ctx.author,
      prestige=prestige,
      badge_data=unowned_badges,
      collection_type="collection",
      collection_label=collection_label,
      discord_message=pending_message
    )

    await pending_message.edit(embed=discord.Embed(
      title="Unowned Badges Displayed!",
      description="Here's your current missing badges list!",
      color=discord.Color.dark_teal()
    ))

    max_badge_count = await db_get_max_badge_count()
    special_badge_count = len(await db_get_special_badge_info())
    collection_count = max_badge_count - special_badge_count
    embed = discord.Embed(
      title=f"{ctx.author.display_name}'s Unowned Badges [{PRESTIGE_TIERS[prestige]}]",
      description=f"Missing {len(unowned_badges)} of {collection_count}",
      color=discord.Color.blurple()
    )

    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, disabled=(len(unowned_badges) <= 30), row=1),
        pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1),
        pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, disabled=(len(unowned_badges) <= 30), row=1),
      ]

      class UnownedPaginator(pages.Paginator):
        def __init__(self, *args, badge_files: list[discord.File], **kwargs):
          self.badge_files = badge_files
          super().__init__(*args, **kwargs)

        async def on_timeout(self):
          for f in self.badge_files:
            try: f.fp.close()
            except: pass
          self.badge_files.clear()
          gc.collect()

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]

      paginator = UnownedPaginator(
        pages=pages_list,
        badge_files=badge_images,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True,
        timeout=600
      )
      await paginator.respond(ctx.interaction, ephemeral=True)

    else:
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for i, chunk in enumerate(file_chunks):
        if i == len(file_chunks) - 1:
          await ctx.followup.send(embed=embed, files=chunk)
        else:
          await ctx.followup.send(files=chunk)
        for f in chunk:
          try: f.fp.close()
          except: pass

    badge_images.clear()
    gc.collect()


  #   _________       __
  #  /   _____/ _____/  |_  ______
  #  \_____  \_/ __ \   __\/  ___/
  #  /        \  ___/|  |  \___ \
  # /_______  /\___  >__| /____  >
  #         \/     \/          \/
  @badge_group.command(
    name="sets",
    description="Show off sets of your badges! Please be mindful of posting very large sets publicly."
  )
  @option(
    'public',
    str,
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  @option(
    'prestige',
    str,
    description="Which Prestige Tier to display?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'category',
    str,
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Affiliation",
        value="affiliation"
      ),
      discord.OptionChoice(
        name="Franchise",
        value="franchise"
      ),
      discord.OptionChoice(
        name="Time Period",
        value="time_period"
      ),
      discord.OptionChoice(
        name="Type",
        value="type"
      )
    ]
  )
  @option(
    'selection',
    str,
    description="Which one?",
    required=True,
    autocomplete=autocomplete_selections
  )
  @option(
    'color',
    str,
    description="Which colorscheme would you like? (Only applies to Standard Tier)",
    required=False,
    choices = [
      discord.OptionChoice(name=color_choice, value=color_choice.lower())
      for color_choice in ["Green", "Orange", "Purple", "Teal"]
    ]
  )
  @commands.check(access_check)
  async def sets(self, ctx:discord.ApplicationContext, public:str, prestige:str, category:str, selection:str, color:str):
    public = bool(public == "yes")

    logger.info(f"{ctx.author.display_name} is pulling up a {Style.BRIGHT}`/badges sets`{Style.RESET_ALL}!")

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    category_title = category.replace("_", " ").title()

    if category == 'affiliation':
      user_set_badges = await db_get_badges_user_has_from_affiliation(ctx.author.id, selection, prestige=prestige)
      all_set_badges = await db_get_all_affiliation_badges(selection)
    elif category == 'franchise':
      user_set_badges = await db_get_badges_user_has_from_franchise(ctx.author.id, selection, prestige=prestige)
      all_set_badges = await db_get_all_franchise_badges(selection)
    elif category == 'time_period':
      user_set_badges = await db_get_badges_user_has_from_time_period(ctx.author.id, selection, prestige=prestige)
      all_set_badges = await db_get_all_time_period_badges(selection)
    elif category == 'type':
      user_set_badges = await db_get_badges_user_has_from_type(ctx.author.id, selection, prestige=prestige)
      all_set_badges = await db_get_all_type_badges(selection)
    else:
      await ctx.followup.send("Select a category", ephemeral=True)
      return

    if not all_set_badges:
      await ctx.respond(
        embed=discord.Embed(
          title=f"Your entry was not in the list of {category_title}s!",
          color=discord.Color.red()
        ), ephemeral=True
      )
      return

    user_badge_map = {badge['badge_name']: badge for badge in user_set_badges}

    set_badges = []
    for badge in all_set_badges:
      user_badge = user_badge_map.get(badge['badge_name'])
      record = {
        'badge_info_id': badge['id'],
        'badge_name': badge['badge_name'],
        'badge_filename': badge['badge_filename'],
        'special': badge['special'],
        'in_user_collection': bool(user_badge),
        'locked': user_badge.get('locked', False) if user_badge else False,
        'crystal_id': user_badge.get('active_crystal_id') if user_badge else None,
        'crystal_effect': user_badge.get('crystal_effect') if user_badge else None
      }
      set_badges.append(record)

    pending_message = await ctx.respond(
      embed=discord.Embed(
        title="Sets Display Request Received!",
        description=f"If this is a large set this miiiiiight take a while...\n\nFear not, AGIMUS shall provide! {get_emoji('agimus_flail')}",
        color=discord.Color.dark_green()
      ), ephemeral=True
    )

    if color:
      await db_set_user_badge_page_color_preference(ctx.author.id, "sets", color)

    collection_label = f"{category_title} - {selection}"
    badge_images = await generate_badge_collection_images(ctx.author, prestige, set_badges, 'sets', collection_label, discord_message=pending_message)

    await pending_message.edit(
      embed=discord.Embed(
        title="Sets Display Request Complete!",
        description="I did it!",
        color=discord.Color.dark_green()
      )
    )

    embed = discord.Embed(
      title=f"Badge Sets: **{category_title}** - **{selection}**",
      description=f"{ctx.author.mention} has collected {len([b for b in set_badges if b['in_user_collection']])} of {len(set_badges)}!",
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, disabled=bool(len(set_badges) <= 30), row=1),
        pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
        ),
        pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, disabled=bool(len(set_badges) <= 30), row=1),
      ]

      class SetsPaginator(pages.Paginator):
        def __init__(self, *args, badge_files: list[discord.File], **kwargs):
          self.badge_files = badge_files
          super().__init__(*args, **kwargs)

        async def on_timeout(self):
          # Close all buffers after timeout
          for f in self.badge_files:
            try:
              f.fp.close()
            except Exception:
              pass
          self.badge_files.clear()
          gc.collect()

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]

      paginator = SetsPaginator(
        pages=pages_list,
        badge_files=badge_images,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True,
        timeout=600
      )
      await paginator.respond(ctx.interaction, ephemeral=True)

    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk)
        else:
          await ctx.followup.send(files=chunk)
        # Immediately close files after sending
        for f in chunk:
          try:
            f.fp.close()
          except Exception:
            pass
    badge_images.clear()
    gc.collect()


  # _________                       .__          __  .__
  # \_   ___ \  ____   _____ ______ |  |   _____/  |_|__| ____   ____
  # /    \  \/ /  _ \ /     \\____ \|  | _/ __ \   __\  |/  _ \ /    \
  # \     \___(  <_> )  Y Y  \  |_> >  |_\  ___/|  | |  (  <_> )   |  \
  #  \______  /\____/|__|_|  /   __/|____/\___  >__| |__|\____/|___|  /
  #         \/             \/|__|             \/                    \/
  @badge_group.command(
    name="completion",
    description="Get a report of how close to completion you are on various sets."
  )
  @option(
    'public',
    str,
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value="no"
      ),
      discord.OptionChoice(
        name="Yes",
        value="yes"
      )
    ]
  )
  @option(
    'prestige',
    str,
    description="Which Prestige Tier to display?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'category',
    str,
    description="Which category of set?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="Affiliation",
        value="affiliation"
      ),
      discord.OptionChoice(
        name="Franchise",
        value="franchise"
      ),
      discord.OptionChoice(
        name="Time Period",
        value="time_period"
      ),
      discord.OptionChoice(
        name="Type",
        value="type"
      )
    ]
  )
  @option(
    'color',
    str,
    description="Which colorscheme would you like?",
    required=False,
    choices = [
      discord.OptionChoice(name=color_choice, value=color_choice.lower())
      for color_choice in ["Green", "Orange", "Purple", "Teal"]
    ]
  )
  @commands.check(access_check)
  async def completion(self, ctx:discord.ApplicationContext, prestige:str, public:str, category:str, color:str):
    public = bool(public == "yes")

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    # Pull data using the queries.
    all_rows = []
    if category == 'affiliation':
      all_rows = await db_completion_by_affiliation(ctx.author.id, prestige=prestige)
    elif category == 'franchise':
      all_rows = await db_completion_by_franchise(ctx.author.id, prestige=prestige)
    elif category == 'time_period':
      all_rows = await db_completion_by_time_period(ctx.author.id, prestige=prestige)
    elif category == 'type':
      all_rows = await db_completion_by_type(ctx.author.id, prestige=prestige)
    all_rows = await self._append_featured_completion_badges(ctx.author.id, all_rows, category, prestige)

    category_title = category.replace('_', ' ').title()

    if color:
      await db_set_user_badge_page_color_preference(ctx.author.id, 'sets', color)

    pending_message = await ctx.respond(
      embed=discord.Embed(
        title=f"{category_title}s Display Request Received!",
        description=f"This may take a second or two...\n\nACCESSING DATABANKS! {get_emoji('agimus')}",
        color=discord.Color.dark_green()
      ), ephemeral=True
    )

    completion_images = await generate_badge_set_completion_images(ctx.author, prestige, all_rows, category, discord_message=pending_message)

    await pending_message.edit(
      embed=discord.Embed(
        title=f"{category_title}s Display Request Complete!",
        description="BEHOLD AND BE AMAZED!",
        color=discord.Color.dark_green()
      )
    )

    embed = discord.Embed(
      title=f"Badge Set Completion [{PRESTIGE_TIERS[prestige]}]: {category_title}",
      description=f"{ctx.author.mention}'s current {category_title} set completion progress",
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, disabled=bool(len(completion_images) <= 1), row=1),
        pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
        ),
        pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, disabled=bool(len(completion_images) <= 1), row=1),
      ]

      class CompletionPaginator(pages.Paginator):
        def __init__(self, *args, badge_files: list[discord.File], **kwargs):
          self.badge_files = badge_files
          super().__init__(*args, **kwargs)

        async def on_timeout(self):
          # Close all buffers after timeout
          for f in self.badge_files:
            try:
              f.fp.close()
            except Exception:
              pass
          self.badge_files.clear()
          gc.collect()

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in completion_images
      ]

      paginator = CompletionPaginator(
        pages=pages_list,
        badge_files=completion_images,
        show_disabled=True,
        show_indicator=True,
        use_default_buttons=False,
        custom_buttons=buttons,
        loop_pages=True,
        timeout=600
      )
      await paginator.respond(ctx.interaction, ephemeral=True)

    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [completion_images[i:i + 10] for i in range(0, len(completion_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk)
        else:
          await ctx.followup.send(files=chunk)
        # Immediately close files after sending
        for f in chunk:
          try:
            f.fp.close()
          except Exception:
            pass
    completion_images.clear()
    gc.collect()


  async def _append_featured_completion_badges(self, user_id, rows, category, prestige):
    if category == "affiliation":
      badges = await db_get_random_badges_from_user_by_affiliations(user_id, prestige=prestige)
    elif category == "franchise":
      badges = await db_get_random_badges_from_user_by_franchises(user_id, prestige=prestige)
    elif category == "time_period":
      badges = await db_get_random_badges_from_user_by_time_periods(user_id, prestige=prestige)
    elif category == "type":
      badges = await db_get_random_badges_from_user_by_types(user_id, prestige=prestige)
    else:
      badges = {}

    for r in rows:
      if r['name'] in badges:
        r['featured_badge'] = badges.get(r['name'])

    return rows

  @badge_group.command(
    name="spotlight",
    description="Show off one of your badges."
  )
  @option(
    'prestige',
    str,
    description="Which Prestige Tier?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'badge',
    str,
    description="Which Badge?",
    required=True,
    autocomplete=autocomplete_users_badges
  )
  @option(
    'public',
    str,
    description="Should others see this?",
    required=True,
    choices=[
      discord.OptionChoice(name="No", value="no"),
      discord.OptionChoice(name="Yes", value="yes")
    ]
  )
  @option(
    'full_metadata',
    str,
    description="Include all metadata ()?",
    required=False,
    choices=[
      discord.OptionChoice(name="No", value="no"),
      discord.OptionChoice(name="Yes", value="yes")
    ]
  )
  async def spotlight(self, ctx: discord.ApplicationContext, prestige: str, badge: str, public: str, full_metadata: str):
    user_id = str(ctx.author.id)

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    try:
      badge_instance_id = int(badge)
    except ValueError:
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Badge",
          description="That badge doesn't seem to be valid.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    badge_instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not badge_instance or badge_instance['owner_discord_id'] != user_id or badge_instance['prestige_level'] != prestige:
      await ctx.respond(
        embed=discord.Embed(
          title="Badge Not Found",
          description="It doesn't appear that you own that one?",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    await ctx.defer(ephemeral=(public == "no"))
    full_metadata = full_metadata == "yes"

    main_color_tuple = discord.Color.blurple().to_rgb()
    if prestige > 0:
      prestige_color = PRESTIGE_THEMES[prestige]['primary']
      main_color_tuple = prestige_color
    else:
      pref = await db_get_user_badge_page_color_preference(user_id) or "green"
      colors = get_theme_colors(pref)
      main_color_tuple = colors.highlight

    badge_frames = await generate_singular_badge_slot(badge_instance, border_color=main_color_tuple, show_crystal_icon=False)

    discord_file = None
    if len(badge_frames) > 1:
      buf = await encode_webp(badge_frames)
      discord_file = discord.File(buf, filename='spotlight.webp')
    else:
      discord_file = buffer_image_to_discord_file(badge_frames[0], 'spotlight.png')

    # Metadata
    badge_info = await db_get_full_badge_metadata_by_filename(badge_instance['badge_filename'])
    if not badge_info:
      await ctx.followup.send(embed=discord.Embed(
        title="Badge Metadata Error",
        description="We couldn't fetch data for this badge.",
        color=discord.Color.red()
      ), ephemeral=True)
      return

    embed = discord.Embed(
      title=f"Badge Spotlight",
      description=f"## {badge_instance['badge_name']} [{PRESTIGE_TIERS[prestige]}]",
      color=discord.Color.from_rgb(*main_color_tuple)
    )
    embed.set_image(url=f"attachment://{discord_file.filename}")

    embed.add_field(name="Badge Name", value=badge_instance['badge_name'], inline=False)
    embed.add_field(name="Owned By", value=f"{ctx.author.mention}", inline=False)
    embed.add_field(name="Prestige Tier", value=PRESTIGE_TIERS[prestige], inline=False)
    if badge_instance.get('crystal_instance_id'):
      crystal_instance = await db_get_crystal_by_id(badge_instance['crystal_instance_id'])
      embed.add_field(name="Crystal", value=f"{crystal_instance['emoji']}  {crystal_instance['crystal_name']} ({crystal_instance['rarity_name']})", inline=False)
      embed.add_field(name="Crystal Description", value=crystal_instance['description'], inline=False)
    if full_metadata:
      if badge_info['affiliations']:
        embed.add_field(name="Affiliations", value=", ".join(badge_info['affiliations']), inline=False)
      if badge_info['types']:
        embed.add_field(name="Types", value=", ".join(badge_info['types']), inline=False)
      embed.add_field(name="Time Period", value=badge_info['time_period'] or "Unknown", inline=False)
      embed.add_field(name="Quadrant", value=badge_info['quadrant'] or "Unknown", inline=False)
      embed.add_field(name="Franchise", value=badge_info['franchise'] or "Unknown", inline=False)
      embed.add_field(name="Reference", value=badge_info['reference'] or "Unknown", inline=False)
      embed.add_field(name="URL", value=f"{badge_info['badge_url']}", inline=False)

    await ctx.followup.send(
      embed=embed,
      file=discord_file,
      ephemeral=(public == "no")
    )

  # .____                  __
  # |    |    ____   ____ |  | ____ ________
  # |    |   /  _ \ /  _ \|  |/ /  |  \____ \
  # |    |__(  <_> |  <_> )    <|  |  /  |_> >
  # |_______ \____/ \____/|__|_ \____/|   __/
  #         \/                 \/     |__|
  @badge_group.command(
    name="lookup",
    description="Look up information about a specific badge"
  )
  @option(
    'public',
    str,
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(name="No", value="no"),
      discord.OptionChoice(name="Yes", value="yes")
    ]
  )
  @option(
    'name',
    str,
    description="Which badge do you want to look up?",
    required=True,
    autocomplete=all_badges_autocomplete
  )
  async def badge_lookup(self, ctx: discord.ApplicationContext, public: str, name: str):
    """
    This function executes the lookup for the /badge lookup command.
    :param ctx:
    :param name: The name of the badge to be looked up.
    :return:
    """
    public = bool(public == "yes")
    await ctx.defer(ephemeral=not public)

    logger.info(f"{Fore.CYAN}Firing /badge lookup command for '{name}'!{Fore.RESET}")

    badge = await db_get_badge_info_by_name(name)
    if not badge:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Could Not Find This Badge",
          description=f"**{name}** does not appear to exist!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    prestige_badge_counts = await db_get_badge_instances_prestige_count_by_filename(badge['badge_filename'])

    # Build prestige tier breakdown
    prestige_count_lines = [
      f"* **{PRESTIGE_TIERS[row['prestige_level']]}: {row['count']}**"
      for row in prestige_badge_counts
    ]

    affiliations = [
      a['affiliation_name']
      for a in await db_get_badge_affiliations_by_badge_name(name)
    ]
    types = [
      t['type_name']
      for t in await db_get_badge_types_by_badge_name(name)
    ]

    description = f"Quadrant: **{badge['quadrant']}**\n"
    description += f"Time Period: **{badge['time_period']}**\n"
    if affiliations:
      description += f"Affiliations: **{', '.join(affiliations)}**\n"
    if types:
      description += f"Types: **{', '.join(types)}**\n"
    description += f"Franchise: **{badge['franchise']}**\n"
    description += f"Reference: **{badge['reference']}**\n"
    description += f"Total Collected on The USS Hood:\n"
    if prestige_count_lines:
      description += "\n".join(prestige_count_lines) + "\n"
    else:
      description += "* **None Collected Yet!**\n"
    description += "URL:\n"
    description += f"{badge['badge_url']}"

    embed = discord.Embed(
      title=f"{badge['badge_name']}",
      description=description,
      color=discord.Color.random()  # jp00p made me do it
    )
    discord_image = discord.File(fp=f"./images/badges/{badge['badge_filename']}", filename=badge['badge_filename'].replace(',', '_'))
    embed.set_image(url=f"attachment://{badge['badge_filename'].replace(',', '_')}")

    if not public:
      user_discord_id = ctx.author.id
      badge_info_id = badge['id']

      # Fetch all active instances the user owns
      user_instances = await db_get_user_badge_instances(user_discord_id, prestige=None)

      # Filter to this badge's instances
      matching_instances = [
        i for i in user_instances
        if i['badge_info_id'] == badge_info_id and i['active']
      ]

      # Track per-tier ownership and lock status
      owned_tiers = {i['prestige_level'] for i in matching_instances}
      locked_tiers = {i['prestige_level'] for i in matching_instances if i['locked']}

      # Get wishlist
      wishlist_badges = await db_get_simple_wishlist_badges(user_discord_id)
      wishlisted = badge_info_id in {w['badge_info_id'] for w in wishlist_badges}

      # Determine user prestige cap
      echelon_progress = await db_get_echelon_progress(user_discord_id)
      max_tier = echelon_progress['current_prestige_tier']

      # Build footer showing per-tier status
      status_lines = []
      for tier in range(max_tier + 1):
        if tier in owned_tiers:
          if tier in locked_tiers:
            symbol = "🔒"
            note = "Locked"
          else:
            symbol = "🔓"
            note = "Unlocked"
        else:
          if wishlisted:
            symbol = "📜"
            note = "Wishlisted"
          else:
            symbol = "❌"
            note = "Not Owned"
        status_lines.append(f"{PRESTIGE_TIERS[tier]}: {symbol} {note}")

      embed.set_footer(text=f"Badge Status for {ctx.author.display_name}\n" + "\n".join(status_lines))

    await ctx.followup.send(embed=embed, file=discord_image, ephemeral=not public)

  # #   _________ __          __  .__          __  .__
  # #  /   _____//  |______ _/  |_|__| _______/  |_|__| ____   ______
  # #  \_____  \\   __\__  \\   __\  |/  ___/\   __\  |/ ___\ /  ___/
  # #  /        \|  |  / __ \|  | |  |\___ \  |  | |  \  \___ \___ \
  # # /_______  /|__| (____  /__| |__/____  > |__| |__|\___  >____  >
  # #         \/           \/             \/               \/     \/
  # @badge_group.command(
  #   name="statistics",
  #   description="See the server-wide badge statistics"
  # )
  # async def badge_statistics(ctx:discord.ApplicationContext):
  #   """
  #   slash command to get common badge stats
  #   """
  #   emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
  #   results = {}
  #   results = await run_badge_stats_queries()
  #   total_badges = "".join(emoji_numbers[int(n)] for n in list(str(results['total_badges'][0]['count'])))
  #   badges_today = "".join(emoji_numbers[int(n)] for n in list(str(results['badges_today'][0]['count'])))
  #   top_collectors = [res for res in results["top_collectors"]]
  #   top_collected = [res for res in results["most_collected"]]
  #   top_wishlisted = [res for res in results["most_wishlisted"]]
  #   top_locked = [res for res in results["most_locked"]]
  #   embed = discord.Embed(color=discord.Color.random(), description="", title="")
  #   embed.add_field(name=f"{get_emoji('combadge')} Total badges collected\non the USS Hood", value=f"{total_badges}\n⠀", inline=True)
  #   embed.add_field(name="⠀", value="⠀", inline=True)
  #   embed.add_field(name=f"{get_emoji('combadge')} Badges collected in\nthe last 24 hours", value=f"{badges_today}\n⠀", inline=True)
  #   embed.add_field(name=f"{get_emoji('combadge')} Top 5 most collected", value=str("\n".join(f"{t['badge_name']} ({t['count']})" for t in top_collected)), inline=True)
  #   embed.add_field(name="⠀", value="⠀", inline=True)
  #   embed.add_field(name=f"{get_emoji('combadge')} Top 5 badge collectors", value=str("\n".join(f"{t['name']} ({t['count']})" for t in top_collectors)), inline=True)
  #   embed.add_field(name=f"{get_emoji('combadge')} Top 5 most wishlisted", value=str("\n".join(f"{t['badge_name']} ({t['count']})" for t in top_wishlisted)), inline=True)
  #   embed.add_field(name="⠀", value="⠀", inline=True)
  #   embed.add_field(name=f"{get_emoji('combadge')} Top 5 most locked", value=str("\n".join(f"{t['badge_name']} ({t['count']})" for t in top_locked)), inline=True)
  #   await ctx.respond(embed=embed, ephemeral=False)

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
# async def run_badge_stats_queries():
#   queries = {
#     "total_badges" : "SELECT COUNT(id) as count FROM badges;",
#     "badges_today" : "SELECT COUNT(id) as count FROM badges WHERE time_created > NOW() - INTERVAL 1 DAY;",
#     "top_collectors" : "SELECT name, COUNT(badges.id) as count FROM users JOIN badges ON users.discord_id = badges.user_discord_id GROUP BY discord_id ORDER BY COUNT(badges.id) DESC LIMIT 5;",
#     "most_wishlisted" : "SELECT b_i.badge_name, COUNT(b_w.id) as count FROM badge_info AS b_i JOIN badge_wishlists AS b_w WHERE b_i.badge_filename = b_w.badge_filename GROUP BY b_w.badge_filename ORDER BY COUNT(b_w.badge_filename) DESC, b_i.badge_name ASC LIMIT 5;",
#     "most_locked" : "SELECT b_i.badge_name, COUNT(b.locked) as count FROM badge_info AS b_i JOIN badges AS b ON b_i.badge_filename = b.badge_filename WHERE b.locked = 1 GROUP BY b.badge_filename ORDER BY COUNT(b.locked) DESC, b_i.badge_name ASC LIMIT 5;",
#   }

#   results = {}
#   async with AgimusDB(dictionary=True) as query:
#     # Run most collected while filtering out special badges
#     special_badge_filenames = [b['badge_filename'] for b in await db_get_special_badge_info()]
#     format_strings = ','.join(['%s'] * len(special_badge_filenames))
#     sql = '''
#       SELECT b_i.badge_name, COUNT(b.id) AS count
#         FROM badges as b
#           LEFT JOIN badge_info AS b_i
#             ON b.badge_filename = b_i.badge_filename
#           WHERE b.badge_filename NOT IN (%s)
#           GROUP BY b.badge_filename
#           ORDER BY count
#           DESC LIMIT 5;
#     '''
#     await query.execute(sql % format_strings, tuple(special_badge_filenames))
#     results["most_collected"] = await query.fetchall()

#     # Run remaining queries
#     for name,sql in queries.items():
#       await query.execute(sql)
#       results[name] = await query.fetchall()

#   return results
