from common import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from utils.crystal_instances import *
from utils.image_utils import *

from utils.check_channel_access import access_check

class Crystals(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  #    _____          __                                     .__          __
  #   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____   ______
  #  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \ /  ___/
  # /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/ \___ \
  # \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >____  >
  #         \/                        \/            \/|__|             \/          \/     \/
  async def autocomplete_user_badge_instance_names(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    badge_instances = await db_get_user_badge_instances(user_id)
    choices = [
      b['badge_name'] for b in badge_instances
      if b.get('badge_name') and ctx.value.lower() in b['badge_name'].lower()
    ]
    return choices

  async def autocomplete_user_badge_crystals(ctx: discord.AutocompleteContext):
    badge_name = ctx.options.get('badge_name')
    if not badge_name:
      return []

    user_id = ctx.interaction.user.id
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      return []

    badge_instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    if not badge_instance:
      return []

    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])
    return ['[None]'] + [
      f"{c['emoji']}  {c['crystal_name']}" if c.get('emoji') else c['crystal_name']
      for c in crystals if ctx.value.lower() in c['crystal_name'].lower()
    ]

  async def autocomplete_user_crystal_rarities(self, ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    rarities = await db_get_user_unattuned_crystal_rarities(user_id)
    return [r['name'] for r in rarities]  # Assuming db returns name + rank info

  async def autocomplete_user_crystals_by_rarity(self, ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id
    rarity = ctx.options.get('rarity')
    if not rarity:
      return []

    unattuned_crystals = await db_get_unattuned_crystals_by_rarity_rank(user_id, rarity)
    if not unattuned_crystals:
      return []

    badge_name = ctx.options.get('badge')
    badge_instance = await db_get_badge_instance_by_badge_name(user_id, badge_name)
    if not badge_instance:
      return []

    existing_attuned_crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])
    if not existing_attuned_crystals:
      return []

    existing_attuned_crystal_type_ids = [c['crystal_type_id'] for c in existing_attuned_crystals]

    filtered = [
      c for c in unattuned_crystals if c['crystal_type_id'] not in existing_attuned_crystal_type_ids
    ]

    grouped = {}
    for c in filtered:
      name = c['crystal_name']
      if name in grouped:
        grouped[name]['count'] += 1
      else:
        grouped[name] = {
          'count': 1,
          'crystal_instance_id': c['crystal_instance_id']
        }

    return [f"{name} ×{info['count']}" for name, info in grouped.items()]


  # _________                                           .___
  # \_   ___ \  ____   _____   _____ _____    ____    __| _/______
  # /    \  \/ /  _ \ /     \ /     \\__  \  /    \  / __ |/  ___/
  # \     \___(  <_> )  Y Y  \  Y Y  \/ __ \|   |  \/ /_/ |\___ \
  #  \______  /\____/|__|_|  /__|_|  (____  /___|  /\____ /____  >
  #         \/             \/      \/     \/     \/      \/    \/
  crystals_group = discord.SlashCommandGroup("crystals", "Badge Crystal Management.")

  # __________              .__  .__               __
  # \______   \ ____ ______ |  | |__| ____ _____ _/  |_  ____
  #  |       _// __ \\____ \|  | |  |/ ___\\__  \\   __\/ __ \
  #  |    |   \  ___/|  |_> >  |_|  \  \___ / __ \|  | \  ___/
  #  |____|_  /\___  >   __/|____/__|\___  >____  /__|  \___  >
  #         \/     \/|__|                \/     \/          \/
  @crystals_group.command(name='replicate', description='Roll up to the Crystal Replicator, consume a Buffer Pattern, and get a new Crystal!')
  @commands.check(access_check)
  async def replicate(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    cog_bot = self.bot
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
          description=f"{random.choice(ENERGIZE_ENGAGE_FLAVORS)}, results incoming momentarily!",
          color=discord.Color.teal()
        )
        confirmation_embed.set_image(url="https://i.imgur.com/jQBRK9N.gif")
        await interaction.response.edit_message(embed=confirmation_embed, attachments=[], view=None)

        discord_file, effect_filename = await generate_crystal_replicator_confirmation_frames(crystal)

        success_message = random.choice(RARITY_SUCCESS_MESSAGES[crystal['rarity_name'].lower()]).format(user=user.mention)
        channel_embed = discord.Embed(
          title='CRYSTAL MATERIALIZATION COMPLETE',
          description=f"A fresh Crystal Buffer Pattern shunts into the replicator, the familiar hum fills the air, and the result is...\n### **{crystal['crystal_name']}**!\n\n{success_message}",
          color=discord.Color.teal()
        )
        channel_embed.add_field(name=f"Rank {crystal['emoji']}", value=f"{crystal['rarity_name']}", inline=False)
        channel_embed.add_field(name=f"Description", value=crystal['description'], inline=False)
        channel_embed.set_image(url=f"attachment://{effect_filename}")
        channel_embed.set_footer(text="Use `/crystals attune` to attach it to one of your Badges!")

        gelrak_v = await cog_bot.fetch_channel(get_channel_id("gelrak-v"))
        await gelrak_v.send(embed=channel_embed, file=discord_file)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Replication Cancelled',
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


  #    _____   __    __
  #   /  _  \_/  |__/  |_ __ __  ____   ____
  #  /  /_\  \   __\   __\  |  \/    \_/ __ \
  # /    |    \  |  |  | |  |  /   |  \  ___/
  # \____|__  /__|  |__| |____/|___|  /\___  >
  #         \/                      \/     \/
  @crystals_group.command(name="attune", description="Attune a Crystal to one of your Badges.")
  @option(
    'badge',
    str,
    description="Select a badge to attune a crystal to",
    autocomplete=autocomplete_user_badge_instance_names
  )
  @option(
    'rarity',
    str,
    description="Rarity of the Crystal to attune",
    autocomplete=autocomplete_user_crystal_rarities
  )
  @option(
    'crystal',
    str,
    description="Crystal to attune",
    autocomplete=autocomplete_user_crystals_by_rarity
  )
  async def attune(self, ctx: discord.ApplicationContext, badge_name: str, rarity: str, crystal_name: str):
    await ctx.defer()
    user_id = ctx.user.id

    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(
        title='Badge Not Found!',
        description=f"Badge **{badge_name}** doesn't appear to be avalid badge...",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    badge_instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    if not badge_instance:
      embed = discord.Embed(
        title='Badge Not Owned!',
        description=f"You don't possess the **{badge_name}** badge.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Step 1: Fetch the list of crystal instances by rarity and filter by name
    all_crystals = await db_get_unattuned_crystals_by_rarity_rank(user_id, rarity)
    matching = [c for c in all_crystals if c['crystal_name'] in crystal_name]

    if not matching:
      await ctx.respond(
        embed=discord.Embed(
          title="Crystal Not Owned!",
          description=f"You don't appear to have a **{crystal_name}** in your unattuned inventory.",
          color=discord.Color.red()
        )
      )
      return

    crystal_instance = matching[0]  # Pick first match

    # Step 2: Get already-attuned crystal types for this badge
    already_attuned_type_ids = await db_get_attuned_crystal_type_ids(badge_instance['badge_instance_id'])

    if crystal_instance['crystal_type_id'] in already_attuned_type_ids:
      await ctx.respond(
        embed=discord.Embed(
          title="Error",
          description=f"This Badge already has a {crystal_name} Crystal attuned to it!",
          color=discord.Color.red()
        )
      )
      return

    # Generate a preview of what the badge would look like if they were to Energize it after attunement
    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal_instance)

    preview_embed = discord.Embed(
      title=f"Crystal Attunement",
      description=f"Are you sure you want to Attune *{crystal_instance['crystal_name']}* to your **{badge_instance['badge_name']}** badge?\n## ⚠️ THIS CANNOT BE UNDONE! ⚠️\nHowever, here's what it would look like with *{crystal_instance['crystal_name']}* once Energized.",
      color=discord.Color.teal()
    )
    preview_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    preview_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    preview_embed.set_footer(text="Click Confirm to Attune this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

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

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await attune_crystal_to_badge(crystal_instance['crystal_instance_id'], badge_instance['badge_instance_id'])
        embed = discord.Embed(
          title='Crystal Attuned!',
          description=f"You have successfully attuned **{crystal_instance['crystal_name']}** to your **{badge_instance['badge_name']}** Badge!",
          color=discord.Color.teal()
        )
        embed.set_footer(text="Now you can use `/crystals energize` to activate it!")
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Cancelled',
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


  # ___________                          .__
  # \_   _____/ ____   ___________  ____ |__|_______ ____
  #  |    __)_ /    \_/ __ \_  __ \/ ___\|  \___   // __ \
  #  |        \   |  \  ___/|  | \/ /_/  >  |/    /\  ___/
  # /_______  /___|  /\___  >__|  \___  /|__/_____ \\___  >
  #         \/     \/     \/     /_____/          \/    \/
  @crystals_group.command(name='energize', description='Select which Crystal to activate for one of your Badges.')
  @option(
    'badge_name',
    str,
    description='Choose a badge from your collection',
    autocomplete=autocomplete_user_badge_instance_names,
    required=True
  )
  @option(
    'crystal_name',
    str,
    description="Select an attuned Crystal to Energize (activate)",
    autocomplete=autocomplete_user_badge_crystals,
    required=True
  )
  @commands.check(access_check)
  async def energize(self, ctx: discord.ApplicationContext, badge_name: str, crystal_name: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    # Error Checks
    badge_info = await db_get_badge_info_by_name(badge_name)
    if not badge_info:
      embed = discord.Embed(
        title='Badge Not Found!',
        description=f"Badge **{badge_name}** not found.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    badge_instance = await db_get_badge_instance_by_badge_info_id(user_id, badge_info['id'])
    if not badge_instance:
      embed = discord.Embed(
        title='Badge Not Owned!',
        description=f"You don't own the **{badge_name}** badge.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    # Deactivation if selected
    if crystal_name.lower() == '[none]':
      if badge_instance.get('active_crystal_id') is None:
        embed = discord.Embed(
          title='Already Deactivated!',
          description=f"No crystal is currently energized on **{badge_name}**.",
          color=discord.Color.orange()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

      previous = next((c for c in crystals if c['badge_crystal_id'] == badge_instance['active_crystal_id']), None)
      prev_label = f"{previous['emoji']} {previous['crystal_name']}" if previous else "Unknown Crystal"

      await db_set_energized_crystal(badge_instance['badge_instance_id'], None)
      embed = discord.Embed(
        title='Crystal Removed',
        description=f"Deactivated **{prev_label}** on **{badge_name}**.",
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)  # ← This was missing!
      return

    selected = next((c for c in crystals if crystal_name.lower() in f"{c.get('emoji', '')}  {c['crystal_name']}".lower()), None)

    if not selected:
      embed = discord.Embed(
        title='Crystal Not Found!',
        description=f"No crystal named **{crystal_name}** found on **{badge_name}**.",
        color=discord.Color.red()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    if badge_instance.get('active_crystal_id') == selected['crystal_type_id']:
      embed = discord.Embed(
        title='Already Energized!',
        description=f"**{crystal_name}** is already your energized Crystal on **{badge_name}**.",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    # Everything looks good to go for actual Energization
    crystal_instance = selected
    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal_instance=crystal_instance)

    preview_embed = discord.Embed(
      title=f"Crystallization Preview",
      description=f"Here's what **{badge_name}** would look like with *{crystal_instance['crystal_name']}* applied.",
      color=discord.Color.teal()
    )
    preview_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    preview_embed.add_field(name=f"Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    preview_embed.set_footer(text="Click Confirm to Energize this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

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

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await db_set_energized_crystal(badge_instance['badge_instance_id'], selected['badge_crystal_id'])
        embed = discord.Embed(
          title='Crystal Energized!',
          description=f"Energized **{crystal_instance['crystal_name']}** as your active Crystal for **{badge_name}**.",
          color=discord.Color.teal()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Cancelled',
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



#  ____ ___   __  .__.__
# |    |   \_/  |_|__|  |   ______
# |    |   /\   __\  |  |  /  ___/
# |    |  /  |  | |  |  |__\___ \
# |______/   |__| |__|____/____  >
#                              \/
ENERGIZE_ENGAGE_FLAVORS = [
  'Discharging the Enerjons',
  'Charging up the EPS conduits',
  'Transfering all power from the Life Support Systems',
  'Ejecting the Warp Core',
  'Placing something dangerous near the Warp Core',
  'Diverting power from the Holodeck Safety Protocol Enforcer',
  'Flooding the Jefferies Tubes with Omicron Radiation',
  'Erecting a Level 10 Force Field'
]

RARITY_SUCCESS_MESSAGES = {
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

def weighted_random_choice(weight_map: dict[str, float]) -> str:
    """
    Returns a single key from the dict based on its weight.
    Keys are possible values, values are weights (drop chances).
    """
    choices = list(weight_map.keys())
    weights = list(weight_map.values())
    return random.choices(choices, weights=weights, k=1)[0]