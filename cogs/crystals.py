# cogs/crystals.py
from collections import defaultdict
from io import BytesIO

from common import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from utils.crystal_instances import *
from utils.image_utils import *
from utils.prestige import *


from utils.check_channel_access import access_check

# _________
# \_   ___ \  ____   ____
# /    \  \/ /  _ \ / ___\
# \     \___(  <_> ) /_/  >
#  \______  /\____/\___  /
#         \/      /_____/
class Crystals(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.REPLICATION_ENGAGE_VERBIAGES = [
      'Discharging the Enerjons',
      'Overloading the EPS conduits',
      'Transfering all power from the Life Support Systems',
      'Ejecting the Warp Core',
      'Placing something dangerous in the middle of Main Engineering',
      'Diverting power from the Holodeck Safety Protocol Enforcer',
      'Flooding the Jefferies Tubes with Omicron Radiation',
      'Disabling that uh, Level 10 Force Field',
      'Destabilizing a localized pocket of subspace',
      'Injecting way too much Trilithium resin into the Reaction Chamber',
      'Overriding all Safety Containment Recommendations',
      'Deactivating the Heisenberg Compensators',
      'Shunting main power through the Deflector Dish... again...',
      'Venting plasma through the Bussard Collectors',
    ]

  # .____    .__          __
  # |    |   |__| _______/  |_  ____   ____   ___________  ______
  # |    |   |  |/  ___/\   __\/ __ \ /    \_/ __ \_  __ \/  ___/
  # |    |___|  |\___ \  |  | \  ___/|   |  \  ___/|  | \/\___ \
  # |_______ \__/____  > |__|  \___  >___|  /\___  >__|  /____  >
  #         \/       \/            \/     \/     \/           \/
  @commands.Cog.listener()
  async def on_ready(self):
    # Some of these load emoji so need to wait for on_ready() for make sure they're in the config
    self.RARITY_SUCCESS_MESSAGES = {
      'common': [
        "Another day, another Crystal for {user}.",
        "One more for {user}.",
        "That's a decent one {user}.",
        "A decent *crystal* for {user}, but an incredible *member* of The Hood!",
        "A fresh steaming Crystal for {user}!",
        "I'd rate that a 3.6... Not great, not terrible {user}."
      ],
      'uncommon': [
        "Heyyy! Lookin pretty good {user}.",
        "Oo, not bad {user}!",
        "Sweet {user}! Purty.",
      ],
      'rare': [
        "SHINY! Congrats {user}! Hold onto that one!",
        "SPARKLY! {user}'s in rare Form!",
        "SCINTILATING! Spectacular too, very nice {user}!"
      ],
      'legendary': [
        "Whoa!!! Legen-dairy! Is this some kind of milk-based crystal {user}!?",
        "Well GOTDAYUM!!! That's some shiny shiny shiny {user}!",
        "FIYAH!!! Crystalline Goodness for {user}!"
      ],
      'mythic': [
        "HOLY **FUCKING** SHIT!!!!! {user} got a ***MYTHIC*** Crystal!?! INCREDIBLE! " + get_emoji('drunk_shimoda_smile_happy'),
        "SWEET JESUS!!!!! Are you kiddin me {user}, *MYTHIC*!? " + get_emoji('zephram_sweet_jesus_wow_whoa'),
        "OH DEAR LORD!!!!!! One freshly minted **MYTHIC** Crystal for {user}!? " + get_emoji('barclay_omg_wow_shock')
      ]
    }

  #    _____          __                                     .__          __
  #   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____   ______
  #  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \ /  ___/
  # /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/ \___ \
  # \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >____  >
  #         \/                        \/            \/|__|             \/          \/     \/
  async def autocomplete_harmonizable_user_badges(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id

    prestige_level = int(ctx.options['prestige'])
    badge_records = await db_get_badge_instances_with_attuned_crystals(user_id, prestige=prestige_level)

    if not badge_records:
      return [discord.OptionChoice(name="🔒 You don't appear to have any Badges that have any Crystals currently attuned to them!", value='none')]

    choices = [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in badge_records if ctx.value.lower() in b['badge_name'].lower()
    ]
    return choices

  async def autocomplete_badges_without_crystal_type(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    crystal_instance_id = ctx.options.get('crystal')
    if not crystal_instance_id:
      return [discord.OptionChoice(name="🔒 You must select a Crystal!", value='none')]

    crystal_instance = await db_get_crystal_by_id(crystal_instance_id)
    prestige_level = int(ctx.options['prestige'])

    badge_instances = await db_get_badge_instances_without_crystal_type(user_id, crystal_instance['crystal_type_id'], prestige=prestige_level)

    if not badge_instances:
      return [discord.OptionChoice(name="🔒 You don't possess any valid Badges for this Crystal Type!", value='none')]

    return [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in badge_instances if ctx.value.lower() in b['badge_name'].lower()
    ]

  async def autocomplete_user_badge_crystals(ctx: discord.AutocompleteContext):
    badge_instance_id = ctx.options.get('badge')
    if not badge_instance_id:
      return []

    badge_instance = await db_get_badge_instance_by_id(badge_instance_id)

    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    none_option = discord.OptionChoice(name="[None]", value=None)
    choices = [
      discord.OptionChoice(
        name=f"{c['emoji']}  {c['crystal_name']}" ,
        value=str(c['crystal_instance_id'])
      )
      for c in crystals if ctx.value.lower() in c['crystal_name'].lower()
    ]
    return [none_option] + choices

  async def autocomplete_user_crystal_rarities(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    rarities = await db_get_user_unattuned_crystal_rarities(user_id)

    if not rarities:
      return [discord.OptionChoice(name="🔒 You don't possess any unattuned Crystals", value='none')]

    return [
      discord.OptionChoice(
        name=f"{r['emoji']}  {r['name']}" if r.get('emoji') else r['name'],
        value=r['name']
      )
      for r in rarities
    ]

  async def autocomplete_user_crystals_by_rarity(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    rarity = ctx.options.get('rarity')
    if not rarity:
      return [discord.OptionChoice(name="🔒 No valid Rarity selected", value='none')]

    crystals = await db_get_unattuned_crystals_by_rarity(user_id, rarity)
    if not crystals:
      return [discord.OptionChoice(name="🔒 You don't possess any unattuned Crystals", value='none')]

    filtered_crystals = [c for c in crystals if ctx.value.lower() in c['crystal_name']]

    seen = set()
    options = []
    for c in filtered_crystals:
      if c['crystal_type_id'] in seen:
        continue
      seen.add(c['crystal_type_id'])

      emoji = c.get('emoji', '')
      label = f"{emoji}  {c['crystal_name']} (×{c['count']})"
      options.append(discord.OptionChoice(name=label, value=str(c['crystal_instance_id'])))

    return options


  # _________                                           .___
  # \_   ___ \  ____   _____   _____ _____    ____    __| _/______
  # /    \  \/ /  _ \ /     \ /     \\__  \  /    \  / __ |/  ___/
  # \     \___(  <_> )  Y Y  \  Y Y  \/ __ \|   |  \/ /_/ |\___ \
  #  \______  /\____/|__|_|  /__|_|  (____  /___|  /\____ /____  >
  #         \/             \/      \/     \/     \/      \/    \/
  crystals_group = discord.SlashCommandGroup("crystals", "Crystals Management.")

  # __________              .__  .__               __
  # \______   \ ____ ______ |  | |__| ____ _____ _/  |_  ____
  #  |       _// __ \\____ \|  | |  |/ ___\\__  \\   __\/ __ \
  #  |    |   \  ___/|  |_> >  |_|  \  \___ / __ \|  | \  ___/
  #  |____|_  /\___  >   __/|____/__|\___  >____  /__|  \___  >
  #         \/     \/|__|                \/     \/          \/
  @crystals_group.command(name='replicate', description='Roll up to the Crystal Replicator, consume a Pattern Buffer, get a new Crystal!')
  @commands.check(access_check)
  async def replicate(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    cog = self
    user = ctx.user
    user_id = user.id

    buffer_credits = await db_get_user_crystal_buffer_count(user_id)
    if not buffer_credits:
      # TODO: Find an appopriate GIF for this...
      embed = discord.Embed(
        title='No Pattern Buffers!',
        description=f"Sorry {user.mention}, you don't currently possess any Crystal Pattern Buffers to redeem!\n\nBetter get out of here before O'Brien calls security... {get_emoji('obrien_omg_jaysus')}",
        color=discord.Color.orange()
      )
      embed.set_footer(text="You can earn more buffer credits through leveling up!")
      await ctx.respond(embed=embed, ephemeral=True)
      return

    unattuned_crystal_count = await db_get_user_unattuned_crystal_count(user_id)
    attuned_badges_count = await db_get_user_attuned_badge_count(user_id)

    replicator_embed = discord.Embed(
      title=f"Crystallization Replication Station!",
      description=f"You currently possess **{buffer_credits}** Crystal Pattern Buffer{'s' if buffer_credits > 1 else ''}. You may redeem **one** Pattern Buffer in exchange for **one** randomized Crystal.\n\nAre you ready to smack this thing and see what falls out?",
      color=discord.Color.teal()
    )
    replicator_embed.add_field(name="Unattuned Crystals", value=f"You possess **{unattuned_crystal_count}** Crystals which have not yet been attuned a Badge.", inline=False)
    replicator_embed.add_field(name=f"Attuned Badges", value=f"You possess **{attuned_badges_count}** Badges with Crystals attuned to them.", inline=False)
    replicator_embed.set_footer(
      text="Use `/crystals inventory` to view your currently unattuned Crystals\nUse `/crystals attune` attach them to your Badges!"
    )
    replicator_embed.set_image(url="https://i.imgur.com/bbdDUfo.gif")

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=60)

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound:
            pass

      @discord.ui.button(label="Engage", style=discord.ButtonStyle.blurple)
      async def engage(self, button, interaction):
        ranks = await db_get_crystal_rarity_weights()
        rolled_rank = weighted_random_choice({r['rarity_rank']: r['drop_chance'] for r in ranks})

        crystal_type = await db_select_random_crystal_type_by_rarity_rank(rolled_rank)

        crystal = await create_new_crystal_instance(user_id, crystal_type['id'])
        await db_decrement_user_crystal_buffer(user_id)

        confirmation_embed = discord.Embed(
          title='Crystal Replication In Progress!',
          description=f"{random.choice(cog.REPLICATION_ENGAGE_VERBIAGES)}, results incoming momentarily!",
          color=discord.Color.teal()
        )
        lcars_slider_gifs = [
          "https://i.imgur.com/jQBRK9N.gif",
          "https://i.imgur.com/sVaOYLs.gif",
          "https://i.imgur.com/IaC8ovb.gif"
        ]
        confirmation_embed.set_image(url=random.choice(lcars_slider_gifs))
        await interaction.response.edit_message(embed=confirmation_embed, attachments=[], view=None)

        discord_file, replicator_confirmation_filename = await generate_crystal_replicator_confirmation_frames(crystal)

        success_message = random.choice(cog.RARITY_SUCCESS_MESSAGES[crystal['rarity_name'].lower()]).format(user=user.mention)
        channel_embed = discord.Embed(
          title='CRYSTAL MATERIALIZATION COMPLETE',
          description=f"A fresh Crystal Pattern Buffer shunts into the replicator, the familiar hum fills the air, and the result is...\n\n> **{crystal['crystal_name']}**!\n\n{success_message}",
          color=discord.Color.teal()
        )
        channel_embed.add_field(name=f"Rank", value=f"> {crystal['emoji']}  {crystal['rarity_name']}", inline=False)
        channel_embed.add_field(name=f"Description", value=f"> {crystal['description']}", inline=False)
        channel_embed.set_image(url=f"attachment://{replicator_confirmation_filename}")
        channel_embed.set_footer(
          text="Use `/crystals attune` to attach it to one of your Badges!"
        )

        gelrak_v = await cog.bot.fetch_channel(get_channel_id("gelrak-v"))
        await gelrak_v.send(embed=channel_embed, files=[discord_file])
        await interaction.delete_original_response()

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Replication Canceled',
          description="No Pattern Buffers expended.",
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    #   ___                          _
    #  | _ \___ ____ __  ___ _ _  __| |
    #  |   / -_|_-< '_ \/ _ \ ' \/ _` |
    #  |_|_\___/__/ .__/\___/_||_\__,_|
    #             |_|
    view = ConfirmCancelView()
    await ctx.respond(embed=replicator_embed, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()



  #    _____                .__  _____                __
  #   /     \ _____    ____ |__|/ ____\____   _______/  |_
  #  /  \ /  \\__  \  /    \|  \   __\/ __ \ /  ___/\   __\
  # /    Y    \/ __ \|   |  \  ||  | \  ___/ \___ \  |  |
  # \____|__  (____  /___|  /__||__|  \___  >____  > |__|
  #         \/     \/     \/              \/     \/
  @crystals_group.command(name="manifest", description="Review your unattuned Crystal Manifest.")
  async def manifest(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id
    crystals = await db_get_user_unattuned_crystals(user_id)

    if not crystals:
      embed = discord.Embed(
        title="Crystal Manifest",
        description="You currently have no unattuned crystals in your manifest!",
        color=discord.Color.dark_teal()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    pending_message = await ctx.respond(
      embed=discord.Embed(
        title="Pulling up your Crystal Manifest...",
        description="🎶 Jazzy Hold Music 🎶",
        color=discord.Color.teal()
      ),
      ephemeral=True
    )

    grouped = defaultdict(list)
    for c in crystals:
      grouped[c['rarity_rank']].append(c)

    class ManifestPaginator(pages.Paginator):
      def __init__(self, *args, buffers: list[BytesIO], **kwargs):
        self.buffers = buffers
        super().__init__(*args, **kwargs)

      async def on_timeout(self):
        for buf in self.buffers:
          try:
            buf.close()
          except Exception:
            pass
        self.buffers.clear()
        await super().on_timeout()

    all_buffers = []
    page_groups = []

    for crystal_rank in sorted(grouped):
      rarity_name = grouped[crystal_rank][0]['rarity_name']
      rarity_emoji = grouped[crystal_rank][0]['emoji']

      collapsed = {}
      for c in grouped[crystal_rank]:
        type_id = c['crystal_type_id']
        if type_id not in collapsed:
          collapsed[type_id] = dict(c)
          collapsed[type_id]['instance_count'] = 1
        else:
          collapsed[type_id]['instance_count'] += 1

      sorted_crystals = sorted(collapsed.values(), key=lambda c: c['crystal_name'].lower())
      crystal_rank_manifest_images = await generate_crystal_manifest_images(ctx.user, sorted_crystals, rarity_name, rarity_emoji)

      crystal_rank_pages = []
      for buffer, filename in crystal_rank_manifest_images:
        all_buffers.append(buffer)  # collect buffer for cleanup
        crystal_rank_pages.append(
          pages.Page(
            embeds=[
              discord.Embed(
                title=f"Crystal Manifest - {rarity_name}",
                color=discord.Color.teal()
              ).set_image(url=f"attachment://{filename}")
            ],
            files=[
              discord.File(fp=buffer, filename=filename)
            ]
          )
        )

      page_groups.append(
        pages.PageGroup(
          pages=crystal_rank_pages,
          label=rarity_name,
          description=f"{len(sorted_crystals)} Crystals",
        )
      )

    paginator = ManifestPaginator(
      pages=page_groups,
      buffers=all_buffers,
      show_menu=True,
      menu_placeholder="Select a Crystal Rarity Tier",
      show_disabled=False,
      loop_pages=True,
      use_default_buttons=False,
      custom_buttons=[
        pages.PaginatorButton("prev", label="⬅", style=discord.ButtonStyle.primary, row=1),
        pages.PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1),
        pages.PaginatorButton("next", label="➡", style=discord.ButtonStyle.primary, row=1),
      ],
    )
    await paginator.respond(ctx.interaction, ephemeral=True)
    await pending_message.delete()


  #    _____   __    __
  #   /  _  \_/  |__/  |_ __ __  ____   ____
  #  /  /_\  \   __\   __\  |  \/    \_/ __ \
  # /    |    \  |  |  | |  |  /   |  \  ___/
  # \____|__  /__|  |__| |____/|___|  /\___  >
  #         \/                      \/     \/
  @crystals_group.command(name="attune", description="Attune (attach) a Crystal to one of your Badges.")
  @option(
    'rarity',
    str,
    required=True,
    description="Rarity of the Crystal to attune",
    autocomplete=autocomplete_user_crystal_rarities
  )
  @option(
    'crystal',
    str,
    required=True,
    description="Crystal to Attune",
    autocomplete=autocomplete_user_crystals_by_rarity
  )
  @option(
    name="prestige",
    description="Which Prestige Tier of Badge?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'badge',
    str,
    required=True,
    description="Badge to Attune to",
    autocomplete=autocomplete_badges_without_crystal_type
  )
  async def attune(self, ctx: discord.ApplicationContext, rarity: str, crystal: str, prestige: str, badge: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    if rarity == 'none' or crystal == 'none' or badge == 'none':
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Selection!",
          description=f"You don't appear to be entering authorized Command options. Someone call the Dustbuster Club!",
          color=discord.Color.red()
        )
      )
      return

    # 'badge' - badge_instance_id passed back from the autocomplete
    badge_instance = await db_get_badge_instance_by_id(badge)
    if not badge_instance:
      await ctx.respond(
        embed=discord.Embed(
          title="Badged Not Owned!",
          description=f"You don't appear to have that Badge in your {PRESTIGE_TIERS[prestige]} inventory!",
          color=discord.Color.red()
        )
      )
      return

    # 'crystal' - crystal_instance_id passed back from the autocomplete
    crystal_instance = await db_get_crystal_by_id(crystal)

    if not crystal_instance:
      await ctx.respond(
        embed=discord.Embed(
          title="Crystal Not Owned!",
          description=f"You don't appear to have that Crystal in your unattuned inventory.",
          color=discord.Color.red()
        )
      )
      return

    # Get already-attuned crystal types for this badge
    already_attuned_type_ids = await db_get_attuned_crystal_type_ids(badge_instance['badge_instance_id'])

    if crystal_instance['crystal_type_id'] in already_attuned_type_ids:
      await ctx.respond(
        embed=discord.Embed(
          title="Whoops!",
          description=f"This Badge already has a {crystal_instance['crystal_name']} Crystal attuned to it!",
          color=discord.Color.red()
        )
      )
      return

    # Generate a preview of what the badge would look like if they decide to Harmonize it after attunement
    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal=crystal_instance)

    landing_embed = discord.Embed(
      title="Crystal Attunement",
      description=f"Are you sure you want to attune *{crystal_instance['crystal_name']}* to your **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]} badge?\n### ⚠️ THIS CANNOT BE UNDONE! ⚠️",
      color=discord.Color.teal()
    )
    landing_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    landing_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    landing_embed.set_image(url="https://i.imgur.com/Pu6H9ep.gif")

    preview_embed = discord.Embed(
      title=f"Harmonization Preview",
      description=f"Here's what **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]} would look like with *{crystal_instance['crystal_name']}* applied to it *once Harmonized.*",
      color=discord.Color.teal()
    )
    preview_embed.set_footer(
      text="Click Confirm to Attune this Crystal, or Cancel."
    )
    preview_embed.set_image(url=attachment_url)

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=120)

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound as e:
            # Workaround for current issue with timeout 404s
            pass

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await attune_crystal_to_badge(crystal_instance['crystal_instance_id'], badge_instance['badge_instance_id'])

        embed_description = f"You have successfully attuned **{crystal_instance['crystal_name']}** to your **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]} Badge!"

        user_data = await get_user(user_id)
        auto_harmonize_enabled = user_data.get('crystal_autoharmonize', False)

        if auto_harmonize_enabled:
          badge_crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])
          matching = next((c for c in badge_crystals if c['crystal_instance_id'] == crystal_instance['crystal_instance_id']), None)
          if matching:
            await db_set_harmonized_crystal(badge_instance['badge_instance_id'], matching['badge_crystal_id'])
            embed_description += "\n\nYou've enabled `Crystallization Auto-Harmonize` so it has now been activated as well!"

        embed = discord.Embed(
          title='Crystal Attuned!',
          description=embed_description,
          color=discord.Color.teal()
        )
        embed.set_image(url="https://i.imgur.com/lP883bg.gif")
        embed.set_footer(
          text="Now you can `/crystals harmonize` to select your activated Crystal at any time!"
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    #   ___                          _
    #  | _ \___ ____ __  ___ _ _  __| |
    #  |   / -_|_-< '_ \/ _ \ ' \/ _` |
    #  |_|_\___/__/ .__/\___/_||_\__,_|
    #             |_|
    view = ConfirmCancelView()
    await ctx.respond(embeds=[landing_embed, preview_embed], file=discord_file, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()


  #   ___ ___                                    .__
  #  /   |   \_____ _______  _____   ____   ____ |__|_______ ____
  # /    ~    \__  \\_  __ \/     \ /  _ \ /    \|  \___   // __ \
  # \    Y    // __ \|  | \/  Y Y  (  <_> )   |  \  |/    /\  ___/
  #  \___|_  /(____  /__|  |__|_|  /\____/|___|  /__/_____ \\___  >
  #        \/      \/            \/            \/         \/    \/
  @crystals_group.command(name='harmonize', description='Select which Crystal to Harmonize (activate) for display on a Badge.')
  @option(
    name="prestige",
    description="Which Prestige Tier of Badge?",
    required=True,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    'badge',
    str,
    description='Choose a badge from your collection',
    autocomplete=autocomplete_harmonizable_user_badges,
    required=True
  )
  @option(
    'crystal',
    str,
    description="Select an attuned Crystal to harmonize (activate)",
    autocomplete=autocomplete_user_badge_crystals,
    required=True
  )
  @commands.check(access_check)
  async def harmonize(self, ctx: discord.ApplicationContext, prestige: str, badge: str, crystal: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige = int(prestige)

    badge_instance = await db_get_badge_instance_by_id(badge)

    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    # Deactivation if selected
    if crystal == 'none':
      if badge_instance.get('active_crystal_id') is None:
        embed = discord.Embed(
          title='Already Deactivated!',
          description=f"No Crystal is currently harmonized to **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]}).",
          color=discord.Color.orange()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

      previous = next((c for c in crystals if c['badge_crystal_id'] == badge_instance['active_crystal_id']), None)
      prev_label = f"{previous['emoji']} {previous['crystal_name']}" if previous else "Unknown Crystal"

      await db_set_harmonized_crystal(badge_instance['badge_instance_id'], None)
      embed = discord.Embed(
        title='Crystal Removed',
        description=f"Deactivated **{prev_label}** on **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]}.",
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)  # ← This was missing!
      return

    crystal_instance = await db_get_crystal_by_id(crystal)

    if badge_instance.get('active_crystal_id') == crystal_instance.get('badge_crystal_id'):
      embed = discord.Embed(
        title='Already Harmonized!',
        description=f"**{crystal_instance['crystal_name']}** is already the harmonized Crystal on **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]}.",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Everything looks good to go for actual Harmonization
    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal=crystal_instance)

    preview_embed = discord.Embed(
      title=f"Crystallization Preview",
      description=f"Here's what **{badge_instance['badge_name']}** ({PRESTIGE_TIERS[prestige]} would look like with *{crystal_instance['crystal_name']}* applied.",
      color=discord.Color.teal()
    )
    preview_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    preview_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    preview_embed.set_footer(
      text="Click Confirm to Harmonize this Crystal, or Cancel."
    )
    preview_embed.set_image(url=attachment_url)

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=120)

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound as e:
            # Workaround for current issue with timeout 404s
            pass

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await db_set_harmonized_crystal(badge_instance['badge_instance_id'], crystal_instance['badge_crystal_id'])
        embed = discord.Embed(
          title='Crystal Harmonized!',
          description=f"Harmonized **{crystal_instance['crystal_name']}**! It is now the active Crystal for your **{badge_instance['badge_name']}** badge.",
          color=discord.Color.teal()
        )
        embed.set_image(url="https://i.imgur.com/cr2m5It.gif")
        embed.set_footer(
          text="CRYSTALS!"
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    #   ___                          _
    #  | _ \___ ____ __  ___ _ _  __| |
    #  |   / -_|_-< '_ \/ _ \ ' \/ _` |
    #  |_|_\___/__/ .__/\___/_||_\__,_|
    #             |_|
    view = ConfirmCancelView()
    await ctx.respond(embed=preview_embed, file=discord_file, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()


#    _____                .__  _____                __    ____   ____.__
#   /     \ _____    ____ |__|/ ____\____   _______/  |_  \   \ /   /|__| ______  _  __
#  /  \ /  \\__  \  /    \|  \   __\/ __ \ /  ___/\   __\  \   Y   / |  |/ __ \ \/ \/ /
# /    Y    \/ __ \|   |  \  ||  | \  ___/ \___ \  |  |     \     /  |  \  ___/\     /
# \____|__  (____  /___|  /__||__|  \___  >____  > |__|      \___/   |__|\___  >\/\_/
#         \/     \/     \/              \/     \/                            \/
class CrystalManifestPage(pages.Page):
  def __init__(self, embed: discord.Embed, buffer: BytesIO, filename: str, rarity: str):
    super().__init__(embeds=[embed])
    self.buffer = buffer
    self.filename = filename
    self.rarity = rarity

  def update_files(self):
    self.buffer.seek(0)
    return [discord.File(fp=self.buffer, filename=self.filename)]

class RaritySelect(discord.ui.Select):
  def __init__(self, paginator: pages.Paginator, rarity_order: list[str]):
    self.paginator = paginator
    options = [
      discord.SelectOption(label=rarity.title(), value=rarity)
      for rarity in rarity_order
    ]
    super().__init__(placeholder="Select Rarity", options=options)

  async def callback(self, interaction: discord.Interaction):
    selected_rarity = self.values[0]
    for i, page in enumerate(self.paginator.pages):
      if getattr(page, 'rarity', None) == selected_rarity:
        self.paginator.current_page = i
        await self.paginator.update_page(interaction)
        break

class CrystalManifestView(discord.ui.View):
  def __init__(self, paginator: pages.Paginator, rarity_order: list[str]):
    super().__init__(timeout=180)
    self.add_item(RaritySelect(paginator, rarity_order))
