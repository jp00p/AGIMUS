# cogs/crystals.py
from __future__ import annotations

import random
from collections import defaultdict
from io import BytesIO

from common import *

from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from utils.crystal_instances import *
from utils.image_utils import *
from utils.prestige import *
from utils.string_utils import strip_bullshit
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
      "Discharging the Enerjons",
      "Overloading the EPS conduits",
      "Transfering all power from the Life Support Systems",
      "Ejecting the Warp Core",
      "Placing something dangerous in the middle of Main Engineering",
      "Diverting power from the Holodeck Safety Protocol Enforcer",
      "Flooding the Jefferies Tubes with Omicron Radiation",
      "Disabling that uh, Level 10 Force Field",
      "Destabilizing a localized pocket of subspace",
      "Injecting way too much Trilithium resin into the Reaction Chamber",
      "Overriding all Safety Containment Recommendations",
      "Deactivating the Heisenberg Compensators",
      "Shunting main power through the Deflector Dish... again...",
      "Venting plasma through the Bussard Collectors",
    ]

  #    _____          __                                     .__          __
  #   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____   ______
  #  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \ /  ___/
  # /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/ \___ \
  # \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >____  >
  #         \/                        \/            \/|__|             \/          \/     \/
  async def autocomplete_harmonizable_user_badges(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id

    prestige = ctx.options['prestige']
    if not prestige or not prestige.isdigit():
      return [discord.OptionChoice(name="🔒 Invalid prestige tier", value='none')]

    badge_records = await db_get_badge_instances_with_attuned_crystals(user_id, prestige=prestige)

    if not badge_records:
      return [discord.OptionChoice(name="🔒 You don't appear to have any Badges that have any Crystals currently attuned to them!", value='none')]

    choices = [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in badge_records if strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
    ]
    return choices

  async def autocomplete_badges_without_crystal_type(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id

    crystal_instance_id = ctx.options.get('crystal')
    if not crystal_instance_id or not crystal_instance_id.isdigit():
      return [discord.OptionChoice(name="🔒 You must select a Crystal!", value='none')]
    crystal_instance = await db_get_crystal_by_id(crystal_instance_id)

    prestige = ctx.options.get('prestige')
    if not prestige or not prestige.isdigit():
      return [discord.OptionChoice(name="🔒 Invalid prestige tier", value='none')]

    badge_instances = await db_get_badge_instances_without_crystal_type(user_id, crystal_instance['crystal_type_id'], prestige=prestige)
    if not badge_instances:
      return [discord.OptionChoice(name="🔒 You don't possess any valid Badges for this Crystal Type!", value='none')]

    return [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['badge_instance_id'])
      )
      for b in badge_instances if strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
    ]

  async def autocomplete_user_badge_crystals(ctx: discord.AutocompleteContext):
    badge_instance_id = ctx.options.get('badge')
    if not badge_instance_id or not badge_instance_id.isdigit():
      return [discord.OptionChoice(name="🔒 Invalid badge input.", value='none')]

    badge_instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not badge_instance:
      return [discord.OptionChoice(name="🔒 That Badge does not exist or is not in your collection.", value='none')]

    active_crystal_type_id = badge_instance.get('crystal_type_id')
    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    none_option = discord.OptionChoice(name="[None]", value='none')
    choices = [
      discord.OptionChoice(
        name=f"{c['emoji']}  {c['crystal_name']}",
        value=str(c['crystal_instance_id'])
      )
      for c in crystals
      if c['crystal_type_id'] != active_crystal_type_id
      and strip_bullshit(ctx.value.lower()) in strip_bullshit(c['crystal_name'].lower())
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

    filtered_crystals = [c for c in crystals if strip_bullshit(ctx.value.lower()) in strip_bullshit(c['crystal_name'].lower())]

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

  async def autocomplete_previewable_badges(ctx: discord.AutocompleteContext):
    user_id = ctx.interaction.user.id

    prestige = ctx.options.get('prestige')
    if not prestige or not prestige.isdigit():
      return [discord.OptionChoice(name="🔒 Invalid prestige tier.", value='none')]

    user_badge_instances = await db_get_user_badge_instances(user_id, prestige=prestige)

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
          name="🔒 No Valid Badges Found",
          value='none'
        )
      ]
    return filtered

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

    logger.info(f"{ctx.user.display_name} is using the {Style.BRIGHT}Crystal Pattern Buffer Replicator{Style.RESET_ALL} with {Style.BRIGHT}`/crystals replicate`{Style.RESET_ALL}!")

    unattuned_crystal_count = await db_get_user_unattuned_crystal_count(user_id)
    attuned_badges_count = await db_get_user_attuned_badge_count(user_id)

    buffer_credits = await db_get_user_crystal_buffer_count(user_id)
    if not buffer_credits:
      embed = discord.Embed(
        title='No Pattern Buffers!',
        description=f"Sorry {user.mention}, you don't currently possess any Crystal Pattern Buffers to redeem!\n\nBetter get out of here before O'Brien calls security... {get_emoji('obrien_omg_jaysus')}",
        color=discord.Color.orange()
      )
      embed.add_field(name="Crystal Pattern Buffers", value=f"You possess **ZERO** *Crystal Pattern Buffers*!", inline=False)
      embed.add_field(name="Unattuned Crystals", value=f"You possess **{unattuned_crystal_count}** *Crystal{'s' if unattuned_crystal_count > 1 else ''}* which have not yet been attached to a Badge.", inline=False)
      embed.add_field(name=f"Attuned Badges", value=f"You possess **{attuned_badges_count}** *Badges* with Crystals attached to them.", inline=False)
      embed.set_footer(text="You can earn more buffer credits through leveling up!")
      embed.set_image(url="https://i.imgur.com/q6Wls8n.gif")
      await ctx.respond(embed=embed, ephemeral=True)
      return

    replicator_embed = discord.Embed(
      title=f"Crystallization Replication Station!",
      description=f"You may redeem **one** Pattern Buffer in exchange for **one** randomized Crystal.\n\nAre you ready to smack this thing and see what falls out?",
      color=discord.Color.teal()
    )
    replicator_embed.add_field(name="Crystal Pattern Buffers", value=f"You possess **{buffer_credits}** *Crystal Pattern Buffer{'s' if buffer_credits > 1 else ''}* to redeem!", inline=False)
    replicator_embed.add_field(name="Unattuned Crystals", value=f"You possess **{unattuned_crystal_count}** *Crystal{'s' if unattuned_crystal_count > 1 else ''}* which have not yet been attached to a Badge.", inline=False)
    replicator_embed.add_field(name=f"Attuned Badges", value=f"You possess **{attuned_badges_count}** *Badge{'s' if attuned_badges_count > 1 else ''}* with Crystals attached to them.", inline=False)
    replicator_embed.set_footer(
      text="Use `/crystals manifest` to view your currently unattuned Crystals\nUse `/crystals attach` attach them to your Badges!"
    )
    replicator_embed.set_image(url="https://i.imgur.com/bbdDUfo.gif")

    #  __   ___
    #  \ \ / (_)_____ __ __
    #   \ V /| / -_) V  V /
    #    \_/ |_\___|\_/\_/
    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=120)
        self.RARITY_SUCCESS_MESSAGES = {
          'common': [
            "Another day, another Crystal for {user}.",
            "One more for {user}.",
            "That's a decent one {user}.",
            "A decent *crystal* for {user}, but an incredible *member* of The Hood!",
            "A fresh steaming Crystal for {user}!",
            "I'd rate that a 3.6... Not great, not terrible {user}.",
            "Routine extraction complete. Crystal secured, {user}.",
            "That's a Crystal alright, {user}.",
            "Wouldn't write home about it, but it *is* shiny, {user}.",
            "Keep stackin' 'em, {user}!",
            "{user}, it's not much, but it is *yours*.",
            "A humble addition to your manifest, {user}.",
            "Could be worse {user}!",
            "Catalogued and stored. Good hustle, {user}."
          ],
          'uncommon': [
            "Heyyy! Lookin pretty good {user}.",
            "Oo, not bad {user}!",
            "Sweet {user}! Purty.",
            "Not too shabby, {user}!",
            "That's a little something special, {user}!",
            "Ooooh, now *that's* got some shimmer {user}!",
            "Subtle. Sleek. Stylish. Just like {user}.",
            "This one's got a vibe. Good grab, {user}.",
            "Not gonna lie, that one's hella cute. Well done, {user}.",
            "{user}, you pulled a classy one!",
            "Respectable find, {user}!",
            "Almost Rare, definitely Rad. Nice {user}!",
            "Decent, decent, {user}."
          ],
          'rare': [
            "SHINY! Congrats {user}! Hold onto that one!",
            "SPARKLY! {user}'s in rare Form!",
            "GLITTERY! Spectacular too, very nice {user}!",
            "FLASHY! And it's a beaut, {user}.",
            "GLIMMERY! You see that sparkle? That's *taste*, {user}.",
            "GLEAMY! You've got the touch, {user}!",
            "GLOWY! Rare, refined, and ready to radiate {user}!",
            "FLASHY! That one's sharp. Lookin' good, {user}."
          ],
          'legendary': [
            "Whoa!!! Legen-dairy! Is this some kind of milk-based crystal {user}!?",
            "Well GOTDAYUM!!! That's some shiny shiny shiny {user}!",
            "FIYAH!!! Crystalline Goodness for {user}!",
            "LORD HAVE MERCY!!! That's a LEGENDARY for {user}!!!",
            "BEJESUS!!! This one's burnin' with glory {user}!",
            "Hooo MAMA! The replicator paused for a sec, it knew this was a big one, {user}!",
            "Heyyyyo! Everyone stand back! {user}'s got a hot one!!!",
            "WHA WHA WHA!?! Legendary stuff, {user}."
          ],
          'mythic': [
            "HOLY **FUCKING** SHIT!!!!! {user} got a ***MYTHIC*** Crystal!?! INCREDIBLE! " + f"{get_emoji('drunk_shimoda_smile_happy')}",
            "SWEET JESUS!!!!! Are you kiddin me {user}, *MYTHIC*!? " + f"{get_emoji('zephram_sweet_jesus_wow_whoa')}",
            "OH DEAR LORD!!!!!! One freshly minted **MYTHIC** Crystal for {user}!? " + f"{get_emoji('barclay_omg_wow_shock')}",
            "PELDOR JOI!!! {user} got a MYTHIC!?!?! " + f"{get_emoji('kira_smile_lol_happy')}",
            "OMFG!!!!! A **MYTHIC** just materialized and it's in {user}'s inventory. " + f"{get_emoji('kira_omg_headexplode')}",
            "CHRIKEY ON A CRACKER!!! The latest **MYTHIC** on the server is here, {user}'s got a sick Crystal! " + f"{get_emoji('jadzia_happy_smile')}"
          ],
          'unobtainium': [
            "∴ [anomaly detected] ∷→∷ {user} receives pattern buffer overflow ∴",
            "∷⧗∷ [symmetry broken] ∷⧗∷ receipt:{user} ∷⧗∷",
            "↯↯↯ [core leak] ↯↯↯ placement target: {user} ↯↯↯"
          ]
        }

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound:
            pass

      @discord.ui.button(label='Cancel', style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Replication Canceled',
          description='No Pattern Buffers expended.',
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label='Engage', style=discord.ButtonStyle.blurple)
      async def engage(self, button, interaction):
        # Roll rarity and mint crystal
        ranks = await db_get_crystal_rarity_weights()
        rolled_rank = weighted_random_choice({r['rarity_rank']: float(r['drop_chance']) for r in ranks})
        crystal_type = await db_select_random_crystal_type_by_rarity_rank(rolled_rank)
        crystal = await create_new_crystal_instance(user_id, crystal_type['id'])
        await db_decrement_user_crystal_buffer(user_id)

        logger.info(f"{ctx.user.display_name} received the {Style.BRIGHT}{crystal['crystal_name']}{Style.RESET_ALL} Crystal from the {Style.BRIGHT}Crystal Replicator{Style.RESET_ALL}!")

        # Show in-progress animation on the ephemeral message and clear controls
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

        # Build and post the public completion message in #gelrak-v
        discord_file, replicator_confirmation_filename = await generate_crystal_replicator_confirmation_frames(crystal)
        success_message = random.choice(self.RARITY_SUCCESS_MESSAGES[crystal['rarity_name'].lower()]).format(user=user.mention)

        channel_embed = discord.Embed(
          title='CRYSTAL MATERIALIZATION COMPLETE',
          description=(
            "A fresh Crystal Pattern Buffer shunts into the replicator, the familiar hum fills the air, and the result is...\n\n"
            f"> **{crystal['crystal_name']}**!\n\n{success_message}"
          ),
          color=discord.Color.teal()
        )
        channel_embed.add_field(name='Rank', value=f"> {crystal['emoji']}  {crystal['rarity_name']}", inline=False)
        channel_embed.add_field(name='Description', value=f"> {crystal['description']}", inline=False)
        channel_embed.set_image(url=f"attachment://{replicator_confirmation_filename}")
        channel_embed.set_footer(text="Use `/crystals attach` to attune it to one of your Badges, then `/crystals activate` to harmonize it!")

        gelrak_v = await cog.bot.fetch_channel(get_channel_id('gelrak-v'))
        await gelrak_v.send(embed=channel_embed, files=[discord_file])

        # Remove the ephemeral "in progress" message to keep the flow clean
        try:
          await interaction.delete_original_response()
        except discord.errors.NotFound:
          pass

        # Recompute counts and either re-open Replicator or show No Buffers
        remaining_buffers = await db_get_user_crystal_buffer_count(user_id)
        unattuned_crystal_count = await db_get_user_unattuned_crystal_count(user_id)
        attuned_badges_count = await db_get_user_attuned_badge_count(user_id)

        if remaining_buffers:
          # Fresh Replicator panel so the user can immediately roll again
          replicator_embed = discord.Embed(
            title='Crystallization Replication Station!',
            description='You may redeem **one** Pattern Buffer in exchange for **one** randomized Crystal.\n\nAre you ready to smack this thing and see what falls out?',
            color=discord.Color.teal()
          )
          replicator_embed.add_field(
            name='Crystal Pattern Buffers',
            value=f"You possess **{remaining_buffers}** *Crystal Pattern Buffer{'s' if remaining_buffers > 1 else ''}* to redeem!",
            inline=False
          )
          replicator_embed.add_field(
            name='Unattuned Crystals',
            value=f"You possess **{unattuned_crystal_count}** *Crystal{'s' if unattuned_crystal_count > 1 else ''}* which have not yet been attached to a Badge.",
            inline=False
          )
          replicator_embed.add_field(
            name='Attuned Badges',
            value=f"You possess **{attuned_badges_count}** *Badge{'s' if attuned_badges_count > 1 else ''}* with Crystals attached to them.",
            inline=False
          )
          replicator_embed.set_footer(
            text="Use `/crystals manifest` to view your currently unattuned Crystals\nUse `/crystals attach` attach them to your Badges!"
          )
          replicator_embed.set_image(url='https://i.imgur.com/bbdDUfo.gif')

          new_view = ConfirmCancelView()
          followup_msg = await interaction.followup.send(embed=replicator_embed, view=new_view, ephemeral=True)
          new_view.message = followup_msg
        else:
          # No buffers left - show a final "No Pattern Buffers Left!" panel
          no_buffer_embed = discord.Embed(
            title='No Pattern Buffers Left!',
            description=(
              f"Welp {user.mention}, you've run out of Crystal Pattern Buffers to redeem... {get_emoji('beverly_frustrated')}\n\n"
              "Better go get some more!"
            ),
            color=discord.Color.from_rgb(0, 77, 77)
          )
          no_buffer_embed.add_field(name='\nCrystal Pattern Buffers', value='You now possess **ZERO** *Crystal Pattern Buffers*!', inline=False)
          no_buffer_embed.add_field(
            name='Unattuned Crystals',
            value=f"You possess **{unattuned_crystal_count}** *Crystal{'s' if unattuned_crystal_count > 1 else ''}* which have not yet been attached to a Badge.",
            inline=False
          )
          no_buffer_embed.add_field(
            name='Attuned Badges',
            value=f"You possess **{attuned_badges_count}** *Badges* with Crystals attached to them.",
            inline=False
          )
          no_buffer_embed.set_footer(text='You can earn more buffer credits through leveling up!')
          no_buffer_embed.set_image(url='https://i.imgur.com/rtlG2aV.gif')

          await interaction.followup.send(embed=no_buffer_embed, ephemeral=True)

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
  @option(
    "prestige",
    str,
    description="Which Prestige Tier of preview Badge?",
    required=False,
    autocomplete=autocomplete_prestige_tiers
  )
  @option(
    "badge",
    str,
    required=False,
    description="Badge to preview Crystal effects on",
    autocomplete=autocomplete_previewable_badges
  )
  async def manifest(self, ctx: discord.ApplicationContext, prestige=None, badge=None):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    logger.info(f"{ctx.user.display_name} is pulling up their {Style.BRIGHT}Crystal Manifest{Style.RESET_ALL} with {Style.BRIGHT}`/crystals manifest`{Style.RESET_ALL}!")

    crystals = await db_get_user_unattuned_crystals(user_id)

    if not crystals:
      embed = discord.Embed(
        title="Crystal Manifest",
        description="You currently have no unattuned crystals in your manifest!",
        color=discord.Color.dark_teal()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    badge_instance = None
    if prestige:
      if not await is_prestige_valid(ctx, prestige):
        return
      prestige_int = int(prestige)

      if not badge or badge == "none":
        await ctx.respond(
          embed=discord.Embed(
            title="Invalid Preview Badge!",
            description="Please select a Badge to preview Crystal effects on.",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

      badge_instance = await db_get_badge_instance_by_id(badge)
      if not badge_instance:
        await ctx.respond(
          embed=discord.Embed(
            title="Invalid Preview Badge!",
            description=f"You don't appear to have that Badge in your {PRESTIGE_TIERS[prestige_int]} inventory!",
            color=discord.Color.red()
          ),
          ephemeral=True
        )
        return

    music_types = [
      "Jazzy",
      "Defiant Jazz",
      "Smooth and Sultry",
      "Bossa Nova",
      "Easy Listening",
      "Lo-Fi Hip Hop",
      "Chillwave",
      "Saxxy",
      "Soft Rock"
    ]
    await ctx.respond(
      embed=discord.Embed(
        title="Pulling up your Crystal Manifest...",
        description=f"🎶 {random.choice(music_types)} Hold Music 🎶",
        color=discord.Color.teal()
      ),
      ephemeral=True
    )
    pending_message = await ctx.interaction.original_response()

    grouped = defaultdict(list)
    for c in crystals:
      grouped[c['rarity_rank']].append(c)

    manifest_groups: list[dict] = []

    for rarity_rank in sorted(grouped):
      rarity_name = grouped[rarity_rank][0].get('rarity_name') or f'Rank {rarity_rank}'
      rarity_emoji = grouped[rarity_rank][0].get('emoji')

      # Collapse by crystal_type_id, keep instance_count
      collapsed: dict[int, dict] = {}
      for c in grouped[rarity_rank]:
        type_id = c['crystal_type_id']
        if type_id not in collapsed:
          collapsed[type_id] = dict(c)
          collapsed[type_id]['instance_count'] = 1
        else:
          collapsed[type_id]['instance_count'] += 1

      sorted_crystals = sorted(collapsed.values(), key=lambda r: (r.get('crystal_name') or '').lower())

      # Generate page images for this rarity
      crystal_rank_manifest_images = await generate_crystal_manifest_images(
        ctx.user,
        sorted_crystals,
        rarity_name,
        rarity_emoji,
        preview_badge=badge_instance,
        discord_message=pending_message
      )

      pages: list[dict] = []
      for buffer, filename in crystal_rank_manifest_images:
        try:
          buffer.seek(0)
        except Exception:
          pass

        # IMPORTANT: store raw bytes so the view can recreate discord.File safely
        try:
          data = buffer.getvalue()
        except Exception:
          data = buffer.read()

        pages.append({
          'filename': filename,
          'data': data,
          # for the attach dropdown, this must match what _sync_attach_options() expects
          'page_crystals': []  # filled below
        })

      # Map crystals -> pages (7 per page, matches your generator paging)
      per_page = 7
      for i in range(len(pages)):
        pages[i]['page_crystals'] = sorted_crystals[i * per_page:(i + 1) * per_page]

      # This is the shape CrystalManifestView expects.
      manifest_groups.append({
        'rarity_rank': rarity_rank,
        'label': rarity_name,
        'emoji': rarity_emoji,
        'description': f'{len(sorted_crystals)} types',
        'pages': pages
      })

    view = CrystalManifestView(
      cog=self,
      user=ctx.user,
      user_id=user_id,
      manifest_groups=manifest_groups,
      preview_badge=badge_instance,
      pending_message=pending_message
    )

    await view.start(ctx)

  #    _____   __    __
  #   /  _  \_/  |__/  |_ __ __  ____   ____
  #  /  /_\  \   __\   __\  |  \/    \_/ __ \
  # /    |    \  |  |  | |  |  /   |  \  ___/
  # \____|__  /__|  |__| |____/|___|  /\___  >
  #         \/                      \/     \/
  @crystals_group.command(name="attach", description="Attune (attach) a Crystal to a Badges. (Will ask for confirmation!)")
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
    'prestige',
    str,
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
  async def attach(self, ctx: discord.ApplicationContext, rarity: str, crystal: str, prestige: str, badge: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_int = int(prestige)

    if rarity == 'none' or crystal == 'none' or badge == 'none':
      await ctx.respond(
        embed=discord.Embed(
          title="Invalid Selection!",
          description="You don't appear to be entering authorized Command options. Someone call the Dustbuster Club!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    badge_instance = await db_get_badge_instance_by_id(badge)
    if not badge_instance:
      await ctx.respond(
        embed=discord.Embed(
          title="Badge Not Owned!",
          description=f"You don't appear to have that Badge in your {PRESTIGE_TIERS[prestige_int]} inventory!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    crystal_instance = await db_get_crystal_by_id(crystal)

    if not crystal_instance:
      await ctx.respond(
        embed=discord.Embed(
          title="Crystal Not Owned!",
          description="You don't appear to have that Crystal in your unattuned inventory.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    logger.info(f"{ctx.user.display_name} is {Style.BRIGHT}Attuning{Style.RESET_ALL} the Crystal {Style.BRIGHT}{crystal_instance['crystal_name']}{Style.RESET_ALL} to {Style.BRIGHT}{badge_instance['badge_name']}{Style.RESET_ALL} with {Style.BRIGHT}`/crystals attach`{Style.RESET_ALL}!")

    already_attuned_type_ids = await db_get_attuned_crystal_type_ids(badge_instance['badge_instance_id'])

    if crystal_instance['crystal_type_id'] in already_attuned_type_ids:
      await ctx.respond(
        embed=discord.Embed(
          title="Whoops!",
          description=f"This Badge already has a {crystal_instance['crystal_name']} Crystal attuned to it!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal=crystal_instance)

    landing_embed = discord.Embed(
      title="Crystal Attunement",
      description=f"Are you sure you want to **attach** *{crystal_instance['crystal_name']}* to your **{badge_instance['badge_name']} [{PRESTIGE_TIERS[prestige_int]}]** badge?\n"
                  "### ⚠️ THIS CANNOT BE UNDONE! ⚠️\n\n"
                  "-# You can have multiple crystals attached to a badge, but once an individual crystal is attuned to a badge it cannot be attached to a *different* badge!",
      color=discord.Color.teal()
    )
    landing_embed.add_field(name="Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    landing_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    landing_embed.set_image(url="https://i.imgur.com/Pu6H9ep.gif")

    preview_embed = discord.Embed(
      title="Attachment Preview",
      description=f"Here's what **{badge_instance['badge_name']} [{PRESTIGE_TIERS[prestige_int]}]** would look like with *{crystal_instance['crystal_name']}* applied to it *once Harmonized.*",
      color=discord.Color.teal()
    )
    preview_embed.set_footer(text="Click Confirm to Attune this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=240)
        self.message = None
        self.RARITY_SUCCESS_MESSAGES = { ... }

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound:
            pass

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await attune_crystal_to_badge(crystal_instance['crystal_instance_id'], badge_instance['badge_instance_id'])

        embed_description = f"You have successfully attuned **{crystal_instance['crystal_name']}** to your **{badge_instance['badge_name']}** [{PRESTIGE_TIERS[prestige_int]}] Badge!"

        user_data = await get_user(user_id)
        auto_harmonize_enabled = user_data.get('crystal_autoharmonize', False)

        if auto_harmonize_enabled:
          badge_crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])
          matching = next((c for c in badge_crystals if c['crystal_instance_id'] == crystal_instance['crystal_instance_id']), None)
          if matching:
            await db_set_harmonized_crystal(badge_instance['badge_instance_id'], matching['badge_crystal_id'])
            embed_description += "\n\n-# `Crystallization Auto-Harmonize` is enabled so it has now been activated as well! (Note that you can change this behavior with `/settings` if so desired)"

        embed = discord.Embed(
          title='Crystal Attuned!',
          description=embed_description,
          color=discord.Color.teal()
        )
        embed.set_image(url="https://i.imgur.com/lP883bg.gif")
        embed.set_footer(text="Now you can use `/crystals activate` to select your harmonized Crystal at any time!")
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    view = ConfirmCancelView()
    await ctx.respond(embeds=[landing_embed, preview_embed], file=discord_file, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()

  #   ___ ___                                    .__
  #  /   |   \_____ _______  _____   ____   ____ |__|_______ ____
  # /    ~    \__  \\_  __ \/     \ /  _ \ /    \|  \___   // __ \
  # \    Y    // __ \|  | \/  Y Y  (  <_> )   |  \  |/    /\  ___/
  #  \___|_  /(____  /__|  |__|_|  /\____/|___|  /__/_____ \\___  >
  #        \/      \/            \/            \/         \/    \/
  @crystals_group.command(name='activate', description='Select which Crystal to Harmonize (activate) for display on a Badge.')
  @option(
    'prestige',
    str,
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
  async def activate(self, ctx: discord.ApplicationContext, prestige: str, badge: str, crystal: str):
    await ctx.defer(ephemeral=True)
    user_id = ctx.user.id

    if not await is_prestige_valid(ctx, prestige):
      return
    prestige_int = int(prestige)

    badge_instance = await db_get_badge_instance_by_id(badge)
    crystals = await db_get_attuned_crystals(badge_instance['badge_instance_id'])

    if crystal == 'none':
      if badge_instance.get('active_crystal_id') is None:
        embed = discord.Embed(
          title='Already Deactivated!',
          description=f"No Crystal is currently harmonized to **{badge_instance['badge_name']}** [{PRESTIGE_TIERS[prestige_int]}].",
          color=discord.Color.orange()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return

      previous = next((c for c in crystals if c['badge_crystal_id'] == badge_instance['active_crystal_id']), None)
      prev_label = f"{previous['emoji']} {previous['crystal_name']}" if previous else "Unknown Crystal"

      await db_set_harmonized_crystal(badge_instance['badge_instance_id'], None)
      embed = discord.Embed(
        title='Crystal Removed',
        description=f"Deactivated **{prev_label}** on **{badge_instance['badge_name']}** [{PRESTIGE_TIERS[prestige_int]}].",
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    try:
      crystal_id = int(crystal)
    except ValueError:
      await ctx.respond(
        embed=discord.Embed(
          title='Invalid Crystal',
          description='That does not appear to be a valid Crystal selection.',
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    crystal_instance = next((c for c in crystals if c['crystal_instance_id'] == crystal_id), None)

    if crystal_instance is None:
      await ctx.respond(
        embed=discord.Embed(
          title='Crystal Not Found',
          description='That Crystal is not attuned to the selected Badge.',
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    logger.info(f"{ctx.user.display_name} is {Style.BRIGHT}Harmonizing{Style.RESET_ALL} the Crystal {Style.BRIGHT}{crystal_instance['crystal_name']}{Style.RESET_ALL} to {Style.BRIGHT}{badge_instance['badge_name']}{Style.RESET_ALL} with {Style.BRIGHT}`/crystals activate`{Style.RESET_ALL}!")

    if badge_instance.get('active_crystal_id') == crystal_instance.get('crystal_instance_id'):
      embed = discord.Embed(
        title='Already Harmonized!',
        description=f"**{crystal_instance['crystal_name']}** is already the harmonized Crystal on **{badge_instance['badge_name']}** [{PRESTIGE_TIERS[prestige_int]}].",
        color=discord.Color.orange()
      )
      await ctx.respond(embed=embed, ephemeral=True)
      return

    discord_file, attachment_url = await generate_badge_preview(user_id, badge_instance, crystal=crystal_instance)

    preview_embed = discord.Embed(
      title="Activation Preview",
      description=f"Here's what **{badge_instance['badge_name']} [{PRESTIGE_TIERS[prestige_int]}]** would look like with *{crystal_instance['crystal_name']}* applied.",
      color=discord.Color.teal()
    )
    preview_embed.add_field(name=f"{crystal_instance['crystal_name']}", value=crystal_instance['description'], inline=False)
    preview_embed.add_field(name="Rank", value=f"{crystal_instance['emoji']}  {crystal_instance['rarity_name']}", inline=False)
    preview_embed.set_footer(text="Click Confirm to Harmonize this Crystal, or Cancel.")
    preview_embed.set_image(url=attachment_url)

    class ConfirmCancelView(discord.ui.View):
      def __init__(self):
        super().__init__(timeout=240)
        self.message = None

      async def on_timeout(self):
        for child in self.children:
          child.disabled = True
        if self.message:
          try:
            await self.message.edit(view=self)
          except discord.errors.NotFound:
            pass

      @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
      async def confirm(self, button, interaction):
        await db_set_harmonized_crystal(badge_instance['badge_instance_id'], crystal_instance['badge_crystal_id'])
        embed = discord.Embed(
          title='Crystal Harmonized!',
          description=f"Harmonized **{crystal_instance['crystal_name']}**! It is now the active Crystal for your **{badge_instance['badge_name']} [{PRESTIGE_TIERS[badge_instance['prestige_level']]}]** badge.",
          color=discord.Color.teal()
        )
        embed.set_image(url="https://i.imgur.com/cr2m5It.gif")
        embed.set_footer(text="CRYSTALS!")
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

      @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
      async def cancel(self, button, interaction):
        embed = discord.Embed(
          title='Canceled',
          description="No changes made to your Badge.",
          color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, attachments=[], view=None)

    view = ConfirmCancelView()
    await ctx.respond(embed=preview_embed, file=discord_file, view=view, ephemeral=True)
    view.message = await ctx.interaction.original_response()

# _________                         __         .__      _____                .__  _____                __ ____   ____.__
# \_   ___ \_______ ___.__. _______/  |______  |  |    /     \ _____    ____ |__|/ ____\____   _______/  |\   \ /   /|__| ______  _  __
# /    \  \/\_  __ <   |  |/  ___/\   __\__  \ |  |   /  \ /  \\__  \  /    \|  \   __\/ __ \ /  ___/\   __\   Y   / |  |/ __ \ \/ \/ /
# \     \____|  | \/\___  |\___ \  |  |  / __ \|  |__/    Y    \/ __ \|   |  \  ||  | \  ___/ \___ \  |  |  \     /  |  \  ___/\     /
#  \______  /|__|   / ____/____  > |__| (____  /____/\____|__  (____  /___|  /__||__|  \___  >____  > |__|   \___/   |__|\___  >\/\_/
#         \/        \/         \/            \/              \/     \/     \/              \/     \/                         \/
class WishlistPartnerView(discord.ui.DesignerView):
  PAGE_SIZE = 30

  def __init__(
    self,
    *,
    cog,
    author_id: str,
    prestige_level: int,
    mode: str,
    partners: list[dict]
  ):
    super().__init__(timeout=360)

    self.cog = cog
    self.author_id = str(author_id)
    self.prestige_level = int(prestige_level)
    self.mode = mode  # "matches" | "dismissals"
    self.partners = partners or []

    self.partner_idx = 0
    self.tab = "intro"  # "intro" | "has" | "wants"
    self.page = 0

    self.message: discord.Message | None = None

    self._interaction_lock = asyncio.Lock()
    self._ui_frozen = False
    self._status: str | None = None  # optional status line like "Saving..."

    self._build_controls()
    self._sync_controls()

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return str(interaction.user.id) == self.author_id

  def _is_component_interaction(self, interaction: discord.Interaction | None) -> bool:
    try:
      return bool(interaction and getattr(interaction, "message", None))
    except Exception:
      return False

  async def _ack(self, interaction: discord.Interaction) -> bool:
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
        await interaction.response.defer(invisible=True)
        return True
      except TypeError:
        pass
      except Exception:
        return False

      try:
        await interaction.response.defer(thinking=False)
        return True
      except TypeError:
        pass
      except Exception:
        return False

    try:
      await interaction.response.defer(ephemeral=True)
      return True
    except TypeError:
      pass
    except Exception:
      return False

    try:
      await interaction.response.defer(invisible=True)
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

  async def _freeze_current_message(self, interaction: discord.Interaction):
    if self._ui_frozen:
      return

    self._ui_frozen = True
    try:
      self.disable_all_items()
    except Exception:
      pass

    if self._is_component_interaction(interaction) and not interaction.response.is_done():
      try:
        await interaction.response.edit_message(view=self)
        return
      except discord.errors.NotFound:
        return
      except Exception:
        pass

    try:
      if interaction.message:
        await interaction.message.edit(view=self)
    except discord.errors.NotFound:
      return
    except Exception:
      pass

  async def _delete_message_safely(self, interaction: discord.Interaction, msg: discord.Message | None):
    if not msg:
      return

    try:
      try:
        await interaction.delete_original_response()
        return
      except Exception:
        pass

      try:
        await msg.delete()
        return
      except Exception:
        pass

      try:
        await interaction.followup.delete_message(msg.id)
        return
      except Exception:
        pass
    except Exception:
      pass

  def _iter_controls(self):
    for row in self.children:
      if isinstance(row, discord.ui.ActionRow):
        for item in row.children:
          yield item

  def _build_controls(self):
    self.clear_items()

    self.partner_select = discord.ui.Select(
      placeholder="Select a partner...",
      min_values=1,
      max_values=1,
      options=self._build_partner_options()
    )
    self.partner_select.callback = self._on_partner_select

    self.tab_select = discord.ui.Select(
      placeholder="Select a view...",
      min_values=1,
      max_values=1,
      options=[
        discord.SelectOption(label="Intro", value="intro"),
        discord.SelectOption(label="What you want", value="has"),
        discord.SelectOption(label="What they want", value="wants")
      ]
    )
    self.tab_select.callback = self._on_tab_select

    self.prev_button = discord.ui.Button(
      label="Prev",
      style=discord.ButtonStyle.secondary
    )
    self.prev_button.callback = self._on_prev

    self.next_button = discord.ui.Button(
      label="Next",
      style=discord.ButtonStyle.secondary
    )
    self.next_button.callback = self._on_next

    action_label = "Dismiss Match" if self.mode == "matches" else "Revoke Dismissal"
    action_style = discord.ButtonStyle.danger if self.mode == "matches" else discord.ButtonStyle.primary
    self.action_button = discord.ui.Button(
      label=action_label,
      style=action_style
    )
    self.action_button.callback = self._on_action

    self.close_button = discord.ui.Button(
      label="Close",
      style=discord.ButtonStyle.secondary
    )
    self.close_button.callback = self._on_close

    self.add_item(discord.ui.ActionRow(self.partner_select))
    self.add_item(discord.ui.ActionRow(self.tab_select))
    self.add_item(discord.ui.ActionRow(
      self.prev_button,
      self.next_button,
      self.action_button,
      self.close_button
    ))

  def _build_partner_options(self) -> list[discord.SelectOption]:
    options = []
    for idx, p in enumerate(self.partners):
      label = p.get("partner_name") or "Unknown"
      desc = f"{len(p.get('has_lines') or [])} has / {len(p.get('wants_lines') or [])} wants"
      options.append(discord.SelectOption(
        label=str(label)[:100],
        description=str(desc)[:100],
        value=str(idx)
      ))
    return options

  def _current_partner(self) -> dict | None:
    if not self.partners:
      return None
    if self.partner_idx < 0 or self.partner_idx >= len(self.partners):
      return None
    return self.partners[self.partner_idx]

  def _get_total_pages_for_tab(self, tab: str) -> int:
    partner = self._current_partner()
    if not partner:
      return 1

    if tab == "has":
      n = len(partner.get("has_lines") or [])
    elif tab == "wants":
      n = len(partner.get("wants_lines") or [])
    else:
      return 1

    return max(1, math.ceil(n / self.PAGE_SIZE))

  def _slice_lines(self, lines: list[str], page: int) -> list[str]:
    start = page * self.PAGE_SIZE
    end = start + self.PAGE_SIZE
    return lines[start:end]

  def _sync_controls(self):
    try:
      for opt in self.partner_select.options:
        opt.default = (opt.value == str(self.partner_idx))

      for opt in self.tab_select.options:
        opt.default = (opt.value == self.tab)

      self.partner_select.disabled = (not self.partners or len(self.partners) <= 1)

      if self.tab == "intro":
        self.prev_button.disabled = True
        self.next_button.disabled = True
      else:
        total_pages = self._get_total_pages_for_tab(self.tab)
        self.prev_button.disabled = (self.page <= 0)
        self.next_button.disabled = (self.page >= max(0, total_pages - 1))

      self.action_button.disabled = (self._current_partner() is None)

      if self._ui_frozen:
        for item in self._iter_controls():
          item.disabled = True
    except Exception:
      pass

  def _build_screen_container(self) -> discord.ui.Container:
    partner = self._current_partner()
    tier_name = PRESTIGE_TIERS[self.prestige_level]

    header_title = "Wishlist Matches" if self.mode == "matches" else "Wishlist Dismissals"
    header = discord.ui.Section(
      discord.ui.TextDisplay(f"## {header_title} [{tier_name}] Tier")
    )

    if self._status:
      status = discord.ui.Section(discord.ui.TextDisplay(self._status))
    else:
      status = None

    if not partner:
      empty = discord.ui.Section(discord.ui.TextDisplay("Nothing to display."))
      if status:
        return discord.ui.Container(header, status, empty)
      return discord.ui.Container(header, empty)

    partner_name = partner.get("partner_name") or "Unknown"
    partner_mention = partner.get("partner_mention") or f"<@{partner.get('partner_id')}>"

    has_total = len(partner.get("has_lines") or [])
    wants_total = len(partner.get("wants_lines") or [])

    summary_lines = [
      f"**Partner:** {partner_mention} ({partner_name})",
      f"**What you want:** {has_total} badge(s)",
      f"**What they want:** {wants_total} badge(s)"
    ]

    if self.mode == "matches":
      summary_lines.append("Use Dismiss Match to hide this partner from matches.")
    else:
      summary_lines.append("Use Revoke Dismissal to restore this partner to matches.")

    summary = discord.ui.Section(discord.ui.TextDisplay("\n".join(summary_lines)))

    if self.tab == "intro":
      if status:
        return discord.ui.Container(header, status, summary)
      return discord.ui.Container(header, summary)

    if self.tab == "has":
      title = "### What you want"
      lines = partner.get("has_lines") or []
      total_pages = self._get_total_pages_for_tab("has")
    else:
      title = "### What they want"
      lines = partner.get("wants_lines") or []
      total_pages = self._get_total_pages_for_tab("wants")

    page_lines = self._slice_lines(lines, self.page)
    body = "\n".join(page_lines) if page_lines else "_No matching badges._"
    footer = f"Page {self.page + 1} of {total_pages}"

    page_section = discord.ui.Section(
      discord.ui.TextDisplay(f"{title}\n{body}\n\n{footer}")
    )

    if status:
      return discord.ui.Container(header, status, summary, page_section)
    return discord.ui.Container(header, summary, page_section)

  async def render(self, interaction: discord.Interaction | None = None):
    self._sync_controls()
    container = self._build_screen_container()

    if interaction:
      if interaction.response.is_done():
        try:
          await interaction.edit_original_response(components=[container], view=self)
        except discord.NotFound:
          if self.message:
            try:
              await self.message.edit(components=[container], view=self)
            except Exception:
              pass
      else:
        try:
          await interaction.response.edit_message(components=[container], view=self)
        except Exception:
          if self.message:
            try:
              await self.message.edit(components=[container], view=self)
            except Exception:
              pass
      return

    if self.message:
      try:
        await self.message.edit(components=[container], view=self)
      except Exception:
        pass

  async def _run_locked(self, interaction: discord.Interaction, fn, *, status: str | None = None):
    async with self._interaction_lock:
      ok = await self._ack(interaction)
      if not ok:
        return

      self._status = status
      await self._freeze_current_message(interaction)
      await self.render(interaction)

      try:
        await fn()
      finally:
        self._status = None
        self._ui_frozen = False
        try:
          for item in self._iter_controls():
            item.disabled = False
        except Exception:
          pass
        await self.render(interaction)

  async def _on_partner_select(self, interaction: discord.Interaction):
    async def _do():
      try:
        self.partner_idx = int(self.partner_select.values[0])
      except Exception:
        self.partner_idx = 0
      self.page = 0
      self.tab = "intro"
      await self.render(interaction)

    await self._run_locked(interaction, _do)

  async def _on_tab_select(self, interaction: discord.Interaction):
    async def _do():
      self.tab = self.tab_select.values[0]
      self.page = 0
      await self.render(interaction)

    await self._run_locked(interaction, _do)

  async def _on_prev(self, interaction: discord.Interaction):
    async def _do():
      self.page = max(0, self.page - 1)
      await self.render(interaction)

    await self._run_locked(interaction, _do)

  async def _on_next(self, interaction: discord.Interaction):
    async def _do():
      total_pages = self._get_total_pages_for_tab(self.tab)
      self.page = min(total_pages - 1, self.page + 1)
      await self.render(interaction)

    await self._run_locked(interaction, _do)

  async def _on_action(self, interaction: discord.Interaction):
    partner = self._current_partner()
    if not partner:
      await self._ack(interaction)
      return

    async def _do():
      if self.mode == "matches":
        await self.cog._dismiss_partner_match(
          user_id=self.author_id,
          partner_id=str(partner.get("partner_id")),
          prestige_level=self.prestige_level,
          has_ids=partner.get("has_ids") or [],
          wants_ids=partner.get("wants_ids") or []
        )
      else:
        await self.cog._revoke_partner_dismissal(
          user_id=self.author_id,
          partner_id=str(partner.get("partner_id")),
          prestige_level=self.prestige_level
        )

      removed_name = partner.get("partner_name") or "Unknown"
      self.partners.pop(self.partner_idx)

      if self.partner_idx >= len(self.partners):
        self.partner_idx = max(0, len(self.partners) - 1)

      self.page = 0
      self.tab = "intro"

      if not self.partners:
        try:
          await interaction.edit_original_response(
            components=[
              discord.ui.Container(
                discord.ui.Section(
                  discord.ui.TextDisplay("## Nothing Left To Review\nAll partners have been cleared from this view.")
                )
              )
            ],
            view=None
          )
        except Exception:
          if self.message:
            try:
              await self.message.edit(
                components=[
                  discord.ui.Container(
                    discord.ui.Section(
                      discord.ui.TextDisplay("## Nothing Left To Review\nAll partners have been cleared from this view.")
                    )
                  )
                ],
                view=None
              )
            except Exception:
              pass
        return

      self._build_controls()
      await interaction.followup.send(
        content=f"Saved - updated records for {removed_name}.",
        ephemeral=True
      )
      await self.render(interaction)

    await self._run_locked(interaction, _do, status="Saving...")

  async def _on_close(self, interaction: discord.Interaction):
    async def _do():
      msg = self.message or getattr(interaction, "message", None)
      await self._delete_message_safely(interaction, msg)

    await self._run_locked(interaction, _do, status="Closing...")

  async def on_timeout(self):
    self._ui_frozen = True
    self._sync_controls()
    if self.message:
      try:
        await self.message.edit(view=self)
      except discord.NotFound:
        pass
      except Exception:
        pass
