from common import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from utils.crystal_instances import *
from utils.image_utils import *

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
    self.HARMONIZE_ENGAGE_FLAVORS = [
      'Discharging the Enerjons',
      'Charging up the EPS conduits',
      'Transfering all power from the Life Support Systems',
      'Ejecting the Warp Core',
      'Placing something dangerous near the Warp Core',
      'Diverting power from the Holodeck Safety Protocol Enforcer',
      'Flooding the Jefferies Tubes with Omicron Radiation',
      'Erecting a Level 10 Force Field'
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
  async def autocomplete_harmonizable_user_badge_instances(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    badge_records = await db_get_user_badge_instances_with_attuned_crystals(user_id)

    if not badge_records:
      return [discord.OptionChoice(name="🔒 You don't appear to have any Badges that have any Crystals currently attuned to them!", value=None)]

    choices = [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in badge_records if ctx.value.lower() in b['badge_name'].lower()
    ]
    return choices

  async def autocomplete_user_badge_instances_without_crystal_type(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    crystal_instance_id = ctx.options.get('crystal')
    if not crystal_instance_id:
      return []

    crystal_instance = await db_get_crystal_by_id(crystal_instance_id)

    badge_instances = await db_get_badges_without_crystal_type(user_id, crystal_instance['crystal_type_id'])

    if not badge_instances:
      return [discord.OptionChoice(name="🔒 You don't possess any valid Badges for this Crystal Type!", value=None)]

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
      return [discord.OptionChoice(name="🔒 You don't possess any unattuned Crystals", value=None)]

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
      return [discord.OptionChoice(name="🔒 No valid Rarity selected", value="none")]

    crystals = await db_get_unattuned_crystals_by_rarity(user_id, rarity)
    if not crystals:
      return [discord.OptionChoice(name="🔒 You don't possess any unattuned Crystals", value="none")]

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
  @crystals_group.command(name='replicate', description='Roll up to the Crystal Replicator, consume a Buffer Pattern, get a new Crystal!')
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
        title='No Buffer Patterns!',
        description=f"Sorry {user.mention}, you don't currently possess any Crystal Buffer Patterns to redeem!\n\nBetter get out of here before O'Brien calls security... {get_emoji('obrien_omg_jaysus')}",
        color=discord.Color.red()
      )
      embed.set_footer(text="You can earn more buffer credits through leveling up!")
      await ctx.respond(embed=embed, ephemeral=True)
      return

    unattuned_crystal_count = await db_get_user_unattuned_crystal_count(user_id)
    attuned_badges_count = await db_get_user_attuned_badge_count(user_id)

    replicator_embed = discord.Embed(
      title=f"Crystallization Replication Station!",
      description=f"You currently possess **{buffer_credits}** Crystal Buffer Pattern{'s' if buffer_credits > 1 else ''}. You may redeem **one** Buffer Pattern in exchange for **one** randomized Crystal.\n\nAre you ready to smack this thing and see what falls out?",
      color=discord.Color.teal()
    )
    replicator_embed.add_field(name="Unattuned Crystals", value=f"You possess **{unattuned_crystal_count}** Crystals which have not yet been attuned a Badge.", inline=False)
    replicator_embed.add_field(name=f"Attuned Badges", value=f"You possess **{attuned_badges_count}** Badges with Crystals attuned to them.", inline=False)
    replicator_embed.set_footer(text="Use `/crystals inventory` to view your currently unattuned Crystals\nUse `/crystals attune` attach them to your Badges!")
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
          await self.message.edit(view=self)

      @discord.ui.button(label="Engage", style=discord.ButtonStyle.blurple)
      async def engage(self, button, interaction):
        ranks = await db_get_crystal_rarity_weights()
        rolled_rank = weighted_random_choice({r['rarity_rank']: r['drop_chance'] for r in ranks})

        crystal_type = await db_select_random_crystal_type_by_rarity_rank(rolled_rank)

        crystal = await create_new_crystal_instance(user_id, crystal_type['id'])
        await db_decrement_user_crystal_buffer(user_id)

        confirmation_embed = discord.Embed(
          title='Crystal Replication In Progress!',
          description=f"{random.choice(cog.HARMONIZE_ENGAGE_FLAVORS)}, results incoming momentarily!",
          color=discord.Color.teal()
        )
        lcars_slider_gifs = [
          "https://i.imgur.com/jQBRK9N.gif",
          "https://i.imgur.com/sVaOYLs.gif",
          "https://i.imgur.com/IaC8ovb.gif"
        ]
        confirmation_embed.set_image(url=random.choice(lcars_slider_gifs))
        await interaction.response.edit_message(embed=confirmation_embed, attachments=[], view=None)

        discord_file, effect_filename = await generate_crystal_replicator_confirmation_frames(crystal)

        success_message = random.choice(cog.RARITY_SUCCESS_MESSAGES[crystal['rarity_name'].lower()]).format(user=user.mention)
        channel_embed = discord.Embed(
          title='CRYSTAL MATERIALIZATION COMPLETE',
          description=f"A fresh Crystal Buffer Pattern shunts into the replicator, the familiar hum fills the air, and the result is...\n### **{crystal['crystal_name']}**!\n\n{success_message}",
          color=discord.Color.teal()
        )
        channel_embed.add_field(name=f"Rank {crystal['emoji']}", value=f"{crystal['rarity_name']}", inline=False)
        channel_embed.add_field(name=f"Description", value=crystal['description'], inline=False)
        channel_embed.set_image(url=f"attachment://{effect_filename}")
        channel_embed.set_footer(text="Use `/crystals attune` to attach it to one of your Badges!")

        gelrak_v = await cog.bot.fetch_channel(get_channel_id("gelrak-v"))
        await gelrak_v.send(embed=channel_embed, file=discord_file)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Replication Canceled',
          description="No Pattern Buffers expended.",
          color=discord.Color.red()
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


  # ____   ____            .__   __
  # \   \ /   /____   __ __|  |_/  |_
  #  \   Y   /\__  \ |  |  \  |\   __\
  #   \     /  / __ \|  |  /  |_|  |
  #    \___/  (____  /____/|____/__|
  #                \/
  @crystals_group.slash_command(name="vault", description="Access your unattuned Crystal vault.")
  async def crystals_vault(self, ctx: discord.ApplicationContext):
    user_id = ctx.user.id
    crystals = await db_get_user_unattuned_crystals(user_id)

    if not crystals:
      embed = discord.Embed(
        title="Crystal Vault",
        description="You currently have no unattuned crystals in your vault.",
        color=discord.Color.dark_purple()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Group crystals by rarity
    crystals_by_rarity = {}
    for crystal in crystals:
      rarity = crystal['rarity_rank']
      if rarity not in crystals_by_rarity:
        crystals_by_rarity[rarity] = []
      crystals_by_rarity[rarity].append(crystal)

    # Build the initial landing embed
    embed = discord.Embed(
      title="Crystal Vault",
      description="Welcome to your Crystal Vault. Select a rarity below to view your unattuned Crystals.",
      color=discord.Color.blurple()
    )
    embed.set_image(url="https://example.com/vault_landing_image.png")  # Replace with actual asset

    view = CrystalsVaultView(user_id, crystals_by_rarity)
    await ctx.respond(embed=embed, view=view, ephemeral=True)


  #    _____   __    __
  #   /  _  \_/  |__/  |_ __ __  ____   ____
  #  /  /_\  \   __\   __\  |  \/    \_/ __ \
  # /    |    \  |  |  | |  |  /   |  \  ___/
  # \____|__  /__|  |__| |____/|___|  /\___  >
  #         \/                      \/     \/
  @crystals_group.command(name="attune", description="Attune a Crystal to one of your Badges.")
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
    description="Crystal to attune",
    autocomplete=autocomplete_user_crystals_by_rarity
  )
  @option(
    'badge',
    str,
    required=True,
    description="Badge to attune your Crystal to",
    autocomplete=autocomplete_user_badge_instances_without_crystal_type
  )
  async def attune(self, ctx: discord.ApplicationContext, rarity: str, crystal: str, badge: str):
    await ctx.defer()
    user_id = ctx.user.id

    if rarity is None or crystal is None or badge is None:
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Selection!",
          description=f"You don't appear to be entering valid Command options. Someone call the Dustbuster Club!",
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
          description=f"You don't appear to have that Badge in your inventory!",
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
      description=f"Are you sure you want to attune *{crystal_instance['crystal_name']}* to your **{badge_instance['badge_name']}** badge?\n### ⚠️ THIS CANNOT BE UNDONE! ⚠️",
      color=discord.Color.teal()
    )
    landing_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    landing_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    landing_embed.set_image(url="https://i.imgur.com/Pu6H9ep.gif")

    preview_embed = discord.Embed(
      title=f"Harmonization Preview",
      description=f"Here's what **{badge_instance['badge_name']}** would look like with *{crystal_instance['crystal_name']}* applied to it *once Harmonized.*",
      color=discord.Color.teal()
    )
    preview_embed.set_footer(text="Click Confirm to Attune this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=120)

      async def on_timeout(self):
        try:
          for child in self.children:
            child.disabled = True
          if self.message:
            await self.message.edit(view=self)
        except discord.errors.NotFound as e:
          # Workaround for current issue with timeout 404s
          pass

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await attune_crystal_to_badge(crystal_instance['crystal_instance_id'], badge_instance['badge_instance_id'])
        embed = discord.Embed(
          title='Crystal Attuned!',
          description=f"You have successfully attuned **{crystal_instance['crystal_name']}** to your **{badge_instance['badge_name']}** Badge!",
          color=discord.Color.teal()
        )
        embed.set_image(url="https://i.imgur.com/lP883bg.gif")
        embed.set_footer(text="Now you can use `/crystals activate` to apply the effect!")
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.red()
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
  @crystals_group.command(name='harmonize', description='Select which Crystal to activate for one of your Badges.')
  @option(
    'badge',
    str,
    description='Choose a badge from your collection',
    autocomplete=autocomplete_harmonizable_user_badge_instances,
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
  async def harmonize(self, ctx: discord.ApplicationContext, badge: str, crystal: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    badge_instance = await db_get_badge_instance_by_id(badge)

    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    # Deactivation if selected
    if crystal is None:
      if badge_instance.get('active_crystal_id') is None:
        embed = discord.Embed(
          title='Already Deactivated!',
          description=f"No Crystal is currently harmonized to **{badge_instance['badge_name']}**.",
          color=discord.Color.orange()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

      previous = next((c for c in crystals if c['badge_crystal_id'] == badge_instance['active_crystal_id']), None)
      prev_label = f"{previous['emoji']} {previous['crystal_name']}" if previous else "Unknown Crystal"

      await db_set_harmonized_crystal(badge_instance['badge_instance_id'], None)
      embed = discord.Embed(
        title='Crystal Removed',
        description=f"Deactivated **{prev_label}** on **{badge_instance['badge_name']}**.",
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)  # ← This was missing!
      return

    crystal_instance = await db_get_crystal_by_id(crystal)

    if badge_instance.get('active_crystal_id') == crystal_instance.get('badge_crystal_id'):
      embed = discord.Embed(
        title='Already Harmonized!',
        description=f"**{crystal_instance['crystal_name']}** is already the harmonized Crystal on **{badge_instance['badge_name']}**.",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Everything looks good to go for actual Harmonization
    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal=crystal_instance)

    preview_embed = discord.Embed(
      title=f"Crystallization Preview",
      description=f"Here's what **{badge_instance['badge_name']}** would look like with *{crystal_instance['crystal_name']}* applied.",
      color=discord.Color.teal()
    )
    preview_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    preview_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    preview_embed.set_footer(text="Click Confirm to Harmonize this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=120)

      async def on_timeout(self):
        try:
          for child in self.children:
            child.disabled = True
          if self.message:
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
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.red()
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



# ____   ____            .__   __    ____   ____.__
# \   \ /   /____   __ __|  |_/  |_  \   \ /   /|__| ______  _  __
#  \   Y   /\__  \ |  |  \  |\   __\  \   Y   / |  |/ __ \ \/ \/ /
#   \     /  / __ \|  |  /  |_|  |     \     /  |  \  ___/\     /
#    \___/  (____  /____/|____/__|      \___/   |__|\___  >\/\_/
#                \/                                     \/
class CrystalsVaultView(discord.ui.View):
  def __init__(self, user_id: int, crystals_by_rarity: dict):
    super().__init__(timeout=180)
    self.user_id = user_id
    self.crystals_by_rarity = crystals_by_rarity
    self.add_item(RaritySelect(self))

class RaritySelect(discord.ui.Select):
  def __init__(self, parent_view: CrystalsVaultView):
    self.parent_view = parent_view
    options = [
      discord.SelectOption(
        label=f"{crystals[0]['rarity_name']} ({len(crystals)})",
        emoji=crystals[0]['emoji'],
        value=rarity
      )
      for rarity, crystals in parent_view.crystals_by_rarity.items()
    ]
    super().__init__(placeholder="Choose Rarity", options=options)

  async def callback(self, interaction: discord.Interaction):
    rarity = self.values[0]
    rarity_level_crystals = self.parent_view.crystals_by_rarity[rarity]
    pages, embeds = await generate_paginated_crystal_rarity_pages(self.parent_view.user_id, rarity_level_crystals)

    paginator = CrystalsVaultPaginator(
      user_id=self.parent_view.user_id,
      rarity=rarity,
      pages=pages,
      embeds=embeds
    )
    paginator.add_item(RaritySelect(self.parent_view))
    await interaction.response.edit_message(
      embed=embeds[0],
      attachments=[pages[0]],
      view=paginator
    )

class CrystalsVaultPaginator(discord.ui.View):
  def __init__(self, user_id: int, rarity: str, pages: list[discord.File], embeds: list[discord.Embed]):
    super().__init__(timeout=180)
    self.user_id = user_id
    self.rarity = rarity
    self.pages = pages
    self.embeds = embeds
    self.current_page = 0
    self.total_pages = len(pages)

    self.prev_button = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary, disabled=self.total_pages <= 1)
    self.prev_button.callback = self.prev_page
    self.add_item(self.prev_button)

    self.page_indicator = discord.ui.Button(label=f"Page {self.current_page + 1}/{self.total_pages}", disabled=True)
    self.add_item(self.page_indicator)

    self.next_button = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary, disabled=self.total_pages <= 1)
    self.next_button.callback = self.next_page
    self.add_item(self.next_button)

  async def prev_page(self, interaction: discord.Interaction):
    self.current_page = (self.current_page - 1) % self.total_pages
    await self.update_page(interaction)

  async def next_page(self, interaction: discord.Interaction):
    self.current_page = (self.current_page + 1) % self.total_pages
    await self.update_page(interaction)

  async def update_page(self, interaction: discord.Interaction):
    self.page_indicator.label = f"Page {self.current_page + 1:02}/{self.total_pages:02}"
    await interaction.response.edit_message(
      embed=self.embeds[self.current_page],
      attachments=[self.pages[self.current_page]],
      view=self
    )

async def generate_paginated_crystal_rarity_pages(user_id: int, rarity_level_crystals: list[dict]) -> tuple[list[discord.File], list[discord.Embed]]:
  user = await bot.fetch_user(user_id)
  page_size = 5
  pages = []
  embeds = []

  if not rarity_level_crystals:
    return pages, embeds

  # We can simply get the name of the rarit and the emoji from the data embedded in the first crystal
  rarity_name = rarity_level_crystals[0]['rarity_name']
  rarity_emoji = rarity_level_crystals[0]['emoji']

  for i in range(0, len(rarity_level_crystals), page_size):
    chunk = rarity_level_crystals[i:i+page_size]
    embed = discord.Embed(
      title=f"{rarity_emoji} {rarity_name} Crystals",
      description=f"Unattuned crystals in your Vault ()",
      color=discord.Color.teal()
    )
    embed.set_footer(f"Page {(i // page_size + 1):02}")

    for crystal in chunk:
      embed.add_field(
        name=f"{crystal['emoji']} {crystal['crystal_name']}",
        value=crystal['description'],
        inline=False
      )

    embeds.append(embed)
    pages.append(discord.File(fp=b"", filename="placeholder.png"))  # Empty file placeholder for now

  return pages, embeds

#  ____ ___   __  .__.__
# |    |   \_/  |_|__|  |   ______
# |    |   /\   __\  |  |  /  ___/
# |    |  /  |  | |  |  |__\___ \
# |______/   |__| |__|____/____  >
#                              \/
def weighted_random_choice(weight_map: dict[str, float]) -> str:
    """
    Returns a single key from the dict based on its weight.
    Keys are possible values, values are weights (drop chances).
    """
    choices = list(weight_map.keys())
    weights = list(weight_map.values())
    return random.choices(choices, weights=weights, k=1)[0]