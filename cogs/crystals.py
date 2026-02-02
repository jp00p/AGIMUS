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
class CrystalManifestView(discord.ui.DesignerView):
  def __init__(
    self,
    *,
    cog: "Crystals",
    user: discord.User,
    user_id: int,
    manifest_groups: list[dict],
    preview_badge: dict | None,
    pending_message: discord.Message | None = None
  ):
    super().__init__(timeout=300)

    self.cog = cog
    self.user = user
    self.user_id = user_id

    self.manifest_groups = manifest_groups
    self.preview_badge = preview_badge
    self.pending_message = pending_message

    self.message: discord.Message | None = None

    self.state = "MANIFEST"  # MANIFEST | ATTACH_CONFIRM | SUCCESS

    self.group_index = 0
    self.page_index = 0

    self.selected_crystal_type_id: int | None = None

    self._interaction_lock = asyncio.Lock()
    self._ui_frozen = False

    self._attach_target_crystal_instance: dict | None = None
    self._attach_preview_bytes: bytes | None = None
    self._attach_preview_filename: str | None = None

    self._unavailable_attach_labels: list[str] = []

  def _log_exc(self, label: str):
    logger.exception(f"[crystals.manifest] {label}")

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    return interaction.user.id == self.user.id

  def _is_component_interaction(self, interaction: discord.Interaction | None) -> bool:
    try:
      return bool(interaction and getattr(interaction, "message", None))
    except Exception:
      self._log_exc("_is_component_interaction")
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
      self._log_exc("_freeze_current_message:disable_all_items")

    try:
      if self._is_component_interaction(interaction) and not interaction.response.is_done():
        try:
          await interaction.response.edit_message(view=self)
        except discord.errors.NotFound:
          return
        except Exception:
          self._log_exc("_freeze_current_message:interaction.response.edit_message")
        return
    except Exception:
      self._log_exc("_freeze_current_message:interaction.response.edit_message_outer")

    try:
      if interaction.message:
        try:
          await interaction.message.edit(view=self)
        except discord.errors.NotFound:
          return
        except Exception:
          self._log_exc("_freeze_current_message:interaction.message.edit")
    except Exception:
      self._log_exc("_freeze_current_message:interaction.message.edit_outer")

  async def _delete_pending_message(self):
    if not self.pending_message:
      return
    try:
      await self.pending_message.delete()
    except discord.errors.NotFound:
      pass
    except Exception:
      pass
    self.pending_message = None

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

  def _wrap_indices(self):
    if not self.manifest_groups:
      self.group_index = 0
      self.page_index = 0
      return

    if self.group_index < 0:
      self.group_index = len(self.manifest_groups) - 1
    if self.group_index >= len(self.manifest_groups):
      self.group_index = 0

    pages = self._current_pages()
    max_pages = len(pages)

    if max_pages <= 0:
      self.page_index = 0
      return

    if self.page_index < 0:
      self.page_index = max_pages - 1
    if self.page_index >= max_pages:
      self.page_index = 0

  def _current_group(self) -> dict:
    return self.manifest_groups[self.group_index]

  def _current_pages(self) -> list[dict]:
    return self._current_group().get("pages") or []

  def _current_page(self) -> dict | None:
    pages = self._current_pages()
    if not pages:
      return None
    return pages[self.page_index]

  def _page_total(self) -> int:
    total = len(self._current_pages())
    return total if total > 0 else 1

  def _page_label(self) -> str:
    return f"Page {self.page_index + 1}/{self._page_total()}"

  def _rarity_label(self) -> str:
    g = self._current_group()
    emoji = g.get("emoji") or ""
    name = g.get("label") or "Unknown"
    return f"{emoji} {name}".strip()

  def _build_manifest_rarity_select(self) -> discord.ui.Select | None:
    if len(self.manifest_groups) <= 1:
      return None

    options = []
    for i, g in enumerate(self.manifest_groups):
      label = g.get("label") or f"Rank {g.get('rarity_rank')}"
      emoji = g.get("emoji")
      desc = g.get("description") or ""
      options.append(discord.SelectOption(
        label=str(label),
        value=str(i),
        description=str(desc)[:100] if desc else None,
        emoji=emoji
      ))

    select = discord.ui.Select(
      placeholder="Select a Crystal Rarity Tier",
      min_values=1,
      max_values=1,
      options=options[:25]
    )
    select.callback = self._on_select_rarity
    return select

  async def _compute_already_attuned_type_ids(self) -> set[int]:
    if not self.preview_badge:
      return set()

    try:
      already_type_ids = await db_get_attuned_crystal_type_ids(self.preview_badge["badge_instance_id"])
    except Exception:
      already_type_ids = []
    return set(already_type_ids or [])

  async def _compute_unavailable_attach_labels(self) -> list[str]:
    already_type_ids = await self._compute_already_attuned_type_ids()

    page = self._current_page() or {}
    labels = []

    for c in (page.get("page_crystals") or []):
      try:
        if c.get("crystal_type_id") in already_type_ids:
          emoji = c.get("emoji") or ""
          name = c.get("crystal_name") or "Unknown"
          labels.append(f"{emoji} {name}".strip())
      except Exception:
        continue

    labels = sorted(set(labels), key=lambda s: s.lower())
    return labels

  async def _build_manifest_crystal_select(self) -> discord.ui.Select | None:
    if not self.preview_badge:
      return None

    already_type_ids = await self._compute_already_attuned_type_ids()
    self._unavailable_attach_labels = await self._compute_unavailable_attach_labels()

    page = self._current_page()
    options = []

    if page:
      for c in page.get("page_crystals", []):
        try:
          type_id = c.get("crystal_type_id")
          if type_id in already_type_ids:
            continue

          label = f"{c.get('crystal_name', 'Unknown')} (x{c.get('instance_count', 1)})"
          options.append(discord.SelectOption(
            label=label,
            value=str(type_id),
            emoji=c.get("emoji")
          ))
        except Exception:
          continue

    if not options:
      options = [discord.SelectOption(label="No valid crystals on this page", value="none")]

    select = discord.ui.Select(
      placeholder="Select a Crystal to Attach",
      min_values=1,
      max_values=1,
      options=options[:25]
    )
    select.callback = self._on_select_crystal
    return select

  def _build_manifest_nav_row(self) -> discord.ui.ActionRow:
    row = discord.ui.ActionRow()

    prev_btn = discord.ui.Button(label="⬅", style=discord.ButtonStyle.primary)
    next_btn = discord.ui.Button(label="➡", style=discord.ButtonStyle.primary)
    close_btn = discord.ui.Button(label="Close", style=discord.ButtonStyle.danger)

    prev_btn.callback = self._on_prev
    next_btn.callback = self._on_next
    close_btn.callback = self._on_close

    row.add_item(prev_btn)

    page_label_btn = discord.ui.Button(
      label=self._page_label(),
      style=discord.ButtonStyle.secondary,
      disabled=True
    )
    row.add_item(page_label_btn)

    row.add_item(next_btn)
    row.add_item(close_btn)
    return row

  def _bytes_from_discord_file(self, discord_file: discord.File | None) -> tuple[bytes | None, str | None]:
    if not discord_file:
      return None, None

    fp = getattr(discord_file, "fp", None)
    filename = getattr(discord_file, "filename", None)

    if not fp:
      return None, filename

    data = None
    try:
      if hasattr(fp, "getvalue"):
        data = fp.getvalue()
      elif hasattr(fp, "read"):
        try:
          fp.seek(0)
        except Exception:
          pass
        data = fp.read()
    except Exception:
      data = None

    return data, filename

  def _build_manifest_container(self, *, unavailable_note: str | None = None) -> tuple[discord.ui.Container, list[discord.File]]:
    files: list[discord.File] = []

    container = discord.ui.Container(color=discord.Color.teal().value)

    container.add_item(discord.ui.TextDisplay("# Crystal Manifest"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(
      f"### Rarity Tier\n-# {self._rarity_label()}"
    ))
    container.add_item(discord.ui.Separator())

    page = self._current_page()
    if page:
      filename = page.get("filename") or f"manifest_{self.group_index}_{self.page_index}.png"
      data = page.get("data")
      if data:
        try:
          buf = BytesIO(data)
          buf.seek(0)
          files.append(discord.File(buf, filename=filename))
          container.add_gallery(
            discord.MediaGalleryItem(
              url=f"attachment://{filename}",
              description="Crystal Manifest"
            )
          )
        except Exception:
          self._log_exc("_build_manifest_container:add_gallery")

    if self.preview_badge:
      container.add_item(discord.ui.Separator())
      badge_name = self.preview_badge.get("badge_name") or "Selected Badge"
      prestige_level = self.preview_badge.get("prestige_level", 0)
      prestige_label = PRESTIGE_TIERS.get(prestige_level, "Standard")
      container.add_item(discord.ui.TextDisplay(
        f"## Preview Badge\n`{badge_name} [{prestige_label}]`"
      ))

    if unavailable_note:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(unavailable_note))

    return container, files

  def _build_attach_confirm_container(self) -> tuple[discord.ui.Container, list[discord.File]]:
    files: list[discord.File] = []

    container = discord.ui.Container(color=discord.Color.teal().value)
    container.add_item(discord.ui.TextDisplay("# Crystal Attunement"))

    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(
      "## ⚠️ WARNING ⚠️\n"
      "### This cannot be undone."
    ))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(
      "-# You can have multiple crystals attached to a badge, but once a crystal is attuned to a badge it cannot be attached to a different badge."
    ))
    container.add_item(discord.ui.Separator())

    try:
      container.add_gallery(
        discord.MediaGalleryItem(
          url="https://i.imgur.com/Pu6H9ep.gif",
          description="Crystal Attunement"
        )
      )
    except Exception:
      pass

    if self._attach_preview_bytes and self._attach_preview_filename:
      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay("## Crystal Preview"))
      container.add_item(discord.ui.Separator())
      try:
        buf = BytesIO(self._attach_preview_bytes)
        buf.seek(0)
        files.append(discord.File(buf, filename=self._attach_preview_filename))
        container.add_gallery(
          discord.MediaGalleryItem(
            url=f"attachment://{self._attach_preview_filename}",
            description="Attachment Preview"
          )
        )
      except Exception:
        self._log_exc("_build_attach_confirm_container:add_preview_gallery")

    if self._attach_target_crystal_instance and self.preview_badge:
      crystal_name = self._attach_target_crystal_instance.get("crystal_name") or "Unknown Crystal"
      crystal_emoji = self._attach_target_crystal_instance.get("emoji") or ""
      badge_name = self.preview_badge.get("badge_name") or "Selected Badge"
      prestige_level = self.preview_badge.get("prestige_level", 0)
      prestige_label = PRESTIGE_TIERS.get(prestige_level, "Standard")

      container.add_item(discord.ui.Separator())
      container.add_item(discord.ui.TextDisplay(
        f"## Confirm\nAttach `{crystal_emoji} {crystal_name}` to `{badge_name} [{prestige_label}]`?"
      ))

    container.add_item(discord.ui.Separator())

    row = discord.ui.ActionRow()

    back_btn = discord.ui.Button(label="❮ Back", style=discord.ButtonStyle.secondary)
    confirm_btn = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.primary)

    back_btn.callback = self._on_back_to_manifest
    confirm_btn.callback = self._on_confirm_attach

    row.add_item(back_btn)
    row.add_item(confirm_btn)

    container.add_item(row)

    return container, files

  def _build_success_container(self, text: str) -> discord.ui.Container:
    container = discord.ui.Container(color=discord.Color.green().value)
    container.add_item(discord.ui.TextDisplay("# Crystal Attuned!"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(text))
    container.add_item(discord.ui.Separator())
    container.add_gallery(
      discord.MediaGalleryItem(
        url="https://i.imgur.com/lP883bg.gif",
        description="Crystal Attuned"
      )
    )
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay("-# Session Ended"))
    return container

  async def _rebuild_async(self) -> list[discord.File]:
    try:
      self.clear_items()
    except Exception:
      pass

    self._wrap_indices()

    if self.state == "MANIFEST":
      self._unavailable_attach_labels = []
      if self.preview_badge:
        try:
          self._unavailable_attach_labels = await self._compute_unavailable_attach_labels()
        except Exception:
          self._unavailable_attach_labels = []

      unavailable_note = None
      if self.preview_badge and self._unavailable_attach_labels:
        shown_lines = ""
        for label in self._unavailable_attach_labels[:12]:
          shown_lines += f"* {label}\n"

        more_line = ""
        if len(self._unavailable_attach_labels) > 12:
          more_line = f"-# (+{len(self._unavailable_attach_labels) - 12} more)"

        unavailable_note = (
          "### Unavailable\n"
          "-# The following are unavailable for attachment because your Badge already has one of the same type attuned:\n"
          f"{shown_lines}{more_line}".rstrip()
        )

      container, files = self._build_manifest_container(unavailable_note=unavailable_note)

      rarity_select = self._build_manifest_rarity_select()
      if rarity_select:
        r = discord.ui.ActionRow()
        r.add_item(rarity_select)
        container.add_item(r)

      crystal_select = await self._build_manifest_crystal_select()
      if crystal_select:
        r2 = discord.ui.ActionRow()
        r2.add_item(crystal_select)
        container.add_item(r2)

      container.add_item(self._build_manifest_nav_row())
      self.add_item(container)
      return files

    if self.state == "ATTACH_CONFIRM":
      container, files = self._build_attach_confirm_container()
      self.add_item(container)
      return files

    if self.state == "SUCCESS":
      self.add_item(self._build_success_container("Attunement complete.\n\n-# Session ended."))
      return []

    container, files = self._build_manifest_container()
    container.add_item(self._build_manifest_nav_row())
    self.add_item(container)
    return files

  async def _send_new_and_delete_old(self, interaction: discord.Interaction, files: list[discord.File]):
    old_msg = None
    try:
      old_msg = interaction.message
    except Exception:
      old_msg = None

    if not old_msg:
      old_msg = self.message

    if old_msg:
      try:
        try:
          await old_msg.edit(view=None)
        except discord.errors.NotFound:
          pass
        except Exception:
          pass
      except Exception:
        pass

      await self._delete_message_safely(interaction, old_msg)

    new_msg = None

    try:
      if not interaction.response.is_done():
        if files:
          try:
            await interaction.response.send_message(view=self, files=files, ephemeral=True)
          except TypeError:
            if len(files) == 1:
              await interaction.response.send_message(view=self, file=files[0], ephemeral=True)
            else:
              await interaction.response.send_message(view=self, ephemeral=True)
        else:
          await interaction.response.send_message(view=self, ephemeral=True)

        try:
          new_msg = await interaction.original_response()
        except Exception:
          new_msg = None
      else:
        if files:
          try:
            new_msg = await interaction.followup.send(view=self, files=files, ephemeral=True)
          except TypeError:
            if len(files) == 1:
              new_msg = await interaction.followup.send(view=self, file=files[0], ephemeral=True)
            else:
              new_msg = await interaction.followup.send(view=self, ephemeral=True)
        else:
          new_msg = await interaction.followup.send(view=self, ephemeral=True)
    except Exception:
      self._log_exc("_send_new_and_delete_old:send")
      raise

    if new_msg:
      self.message = new_msg

  async def _render(self, interaction: discord.Interaction):
    await self._freeze_current_message(interaction)

    acked = await self._ack(interaction)
    if not acked:
      return

    try:
      self._ui_frozen = False
      files = await self._rebuild_async()
    except Exception:
      self._log_exc("_render:_rebuild_async")
      return

    try:
      await self._send_new_and_delete_old(interaction, files)
    except Exception:
      self._log_exc("_render:_send_new_and_delete_old")

  async def start(self, ctx: discord.ApplicationContext):
    try:
      files = await self._rebuild_async()
    except Exception:
      self._log_exc("start:_rebuild_async")
      return

    msg = None
    try:
      already_done = bool(ctx.interaction and ctx.interaction.response and ctx.interaction.response.is_done())

      if already_done:
        if files:
          try:
            msg = await ctx.followup.send(view=self, files=files, ephemeral=True)
          except TypeError:
            if len(files) == 1:
              msg = await ctx.followup.send(view=self, file=files[0], ephemeral=True)
            else:
              msg = await ctx.followup.send(view=self, ephemeral=True)
        else:
          msg = await ctx.followup.send(view=self, ephemeral=True)
      else:
        if files:
          try:
            await ctx.respond(view=self, files=files, ephemeral=True)
          except TypeError:
            if len(files) == 1:
              await ctx.respond(view=self, file=files[0], ephemeral=True)
            else:
              await ctx.respond(view=self, ephemeral=True)
        else:
          await ctx.respond(view=self, ephemeral=True)

        try:
          msg = await ctx.interaction.original_response()
        except Exception:
          msg = None
    except Exception:
      self._log_exc("start:send")
      return

    self.message = msg

    try:
      await self._delete_pending_message()
    except Exception:
      pass

  async def on_timeout(self):
    try:
      self.disable_all_items()
    except Exception:
      pass

    try:
      if self.message:
        try:
          await self.message.edit(view=self)
        except discord.errors.NotFound:
          pass
        except Exception:
          pass
    except Exception:
      pass

    try:
      await self._delete_pending_message()
    except Exception:
      pass

    try:
      self.stop()
    except Exception:
      pass

  def _normalize_rows(self, rows):
    if not rows:
      return []
    if isinstance(rows, list):
      return rows
    if isinstance(rows, dict):
      if "crystal_instance_id" in rows:
        return [rows]
      return list(rows.values())
    return []

  async def _prepare_attach_state(self, interaction: discord.Interaction, crystal_type_id: int) -> bool:
    if not self.preview_badge:
      return False

    raw = await db_get_unattuned_crystals_by_type(self.user_id, crystal_type_id)
    crystals = self._normalize_rows(raw)

    if not crystals:
      await interaction.followup.send(
        embed=discord.Embed(
          title="No Crystals Available",
          description="You no longer have any unattuned crystals of that type available.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return False

    crystal_instance = crystals[0]

    already_attuned_type_ids = await self._compute_already_attuned_type_ids()
    if crystal_instance.get("crystal_type_id") in already_attuned_type_ids:
      await interaction.followup.send(
        embed=discord.Embed(
          title="Unavailable",
          description="That crystal type is already attuned to this Badge.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return False

    self._attach_target_crystal_instance = crystal_instance

    discord_file, _attachment_url = await generate_badge_preview(
      self.user_id,
      self.preview_badge,
      crystal=crystal_instance
    )

    data, filename = self._bytes_from_discord_file(discord_file)
    if data:
      self._attach_preview_bytes = data
      self._attach_preview_filename = filename or "attachment_preview.png"
    else:
      self._attach_preview_bytes = None
      self._attach_preview_filename = None

    return True

  async def _on_select_rarity(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        vals = (interaction.data or {}).get("values") or []
        if not vals:
          await self._render(interaction)
          return

        try:
          self.group_index = int(vals[0])
        except Exception:
          self.group_index = 0

        self.page_index = 0
        self.selected_crystal_type_id = None

        await self._render(interaction)
      except Exception:
        self._log_exc("_on_select_rarity")
        await self._render(interaction)

  async def _on_select_crystal(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        vals = (interaction.data or {}).get("values") or []
        val = vals[0] if vals else None

        if not val or val == "none":
          self.selected_crystal_type_id = None
          await self._render(interaction)
          return

        try:
          self.selected_crystal_type_id = int(val)
        except Exception:
          self.selected_crystal_type_id = None

        if not self.preview_badge or not self.selected_crystal_type_id:
          await self._render(interaction)
          return

        await self._ack(interaction)

        ok = await self._prepare_attach_state(interaction, self.selected_crystal_type_id)
        if not ok:
          self.selected_crystal_type_id = None
          await self._render(interaction)
          return

        self.state = "ATTACH_CONFIRM"
        await self._render(interaction)
      except Exception:
        self._log_exc("_on_select_crystal")
        await self._render(interaction)

  async def _on_prev(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        self.page_index -= 1
        if self.page_index < 0:
          self.page_index = self._page_total() - 1
        self.selected_crystal_type_id = None
        await self._render(interaction)
      except Exception:
        self._log_exc("_on_prev")
        await self._render(interaction)

  async def _on_next(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        self.page_index += 1
        if self.page_index >= self._page_total():
          self.page_index = 0
        self.selected_crystal_type_id = None
        await self._render(interaction)
      except Exception:
        self._log_exc("_on_next")
        await self._render(interaction)

  async def _on_close(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        await self._freeze_current_message(interaction)
        await self._ack(interaction)

        try:
          await self._delete_message_safely(interaction, interaction.message or self.message)
        except Exception:
          pass

        try:
          await self._delete_pending_message()
        except Exception:
          pass

        self.stop()
      except Exception:
        self._log_exc("_on_close")
        self.stop()

  async def _on_back_to_manifest(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        self.state = "MANIFEST"
        self._attach_target_crystal_instance = None
        self._attach_preview_bytes = None
        self._attach_preview_filename = None
        await self._render(interaction)
      except Exception:
        self._log_exc("_on_back_to_manifest")
        await self._render(interaction)

  async def _on_confirm_attach(self, interaction: discord.Interaction):
    async with self._interaction_lock:
      try:
        if not self.preview_badge or not self._attach_target_crystal_instance:
          self.state = "MANIFEST"
          await self._render(interaction)
          return

        crystal_instance = self._attach_target_crystal_instance
        badge_instance = self.preview_badge

        await attune_crystal_to_badge(crystal_instance["crystal_instance_id"], badge_instance["badge_instance_id"])

        user_data = await get_user(self.user_id)
        auto_harmonize_enabled = user_data.get("crystal_autoharmonize", False)

        extra = ""
        if auto_harmonize_enabled:
          badge_crystals = await db_get_attuned_crystals(badge_instance["badge_instance_id"])
          matching = next((c for c in (badge_crystals or []) if c.get("crystal_instance_id") == crystal_instance.get("crystal_instance_id")), None)
          if matching:
            await db_set_harmonized_crystal(badge_instance["badge_instance_id"], matching["badge_crystal_id"])
            extra = "\n\n-# `Crystallization Auto-Harmonize` is enabled so it has now been activated as well!"

        self.state = "SUCCESS"
        self._attach_target_crystal_instance = None
        self._attach_preview_bytes = None
        self._attach_preview_filename = None

        try:
          self.clear_items()
        except Exception:
          pass

        self.add_item(self._build_success_container(
          f"Attuned successfully.{extra}"
        ))

        await self._freeze_current_message(interaction)
        acked = await self._ack(interaction)
        if not acked:
          self.stop()
          return

        try:
          await self._send_new_and_delete_old(interaction, [])
        except Exception:
          self._log_exc("_on_confirm_attach:_send_new_and_delete_old")

        self.stop()
      except Exception:
        self._log_exc("_on_confirm_attach")
        self.state = "MANIFEST"
        await self._render(interaction)
