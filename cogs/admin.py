from common import *
import random
from collections import defaultdict

from handlers.echelon_xp import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from queries.echelon_xp import *
from queries.server_settings import *
from queries.tongo import *
from utils.badge_instances import *
from utils.crystal_effects import *
from utils.crystal_instances import *
from utils.echelon_rewards import *
from utils.exception_logger import log_manual_exception
from utils.prestige import PRESTIGE_TIERS
from utils.settings_utils import db_get_current_xp_enabled_value
from utils.string_utils import strip_bullshit

from utils.check_user_access import user_check


class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def autocomplete_prestige_for_user(ctx: discord.AutocompleteContext):
    target_user_id = ctx.options.get('user')
    if not target_user_id:
      return [discord.OptionChoice(name='Standard', value=0)]

    progress = await db_get_echelon_progress(int(target_user_id))
    max_prestige = progress['current_prestige_tier'] if progress else 0
    return [discord.OptionChoice(name=PRESTIGE_TIERS[i], value=str(i)) for i in range(max_prestige + 1)]

  async def autocomplete_all_badges(ctx: discord.AutocompleteContext):
    badge_records = await db_get_all_badge_info()
    choices = [
      discord.OptionChoice(
        name=b['badge_name'],
        value=str(b['id'])
      )
      for b in badge_records if strip_bullshit(ctx.value.lower()) in strip_bullshit(b['badge_name'].lower())
    ]
    return choices

  admin_group = discord.SlashCommandGroup('zed_ops', 'Admin-only commands for Badge and Tongo Management.')

  @admin_group.command(name='set_bonus_xp', description='(ADMIN RESTRICTED)')
  @option('enabled', bool, description='Enabled', required=True)
  @option('bonus', int, description='Bonus', required=False)
  @commands.check(user_check)
  async def set_bonus_xp(self, ctx: discord.ApplicationContext, enabled: bool, bonus: int):
    await db_toggle_bonus_xp(enabled)
    bonus_set = None
    if bonus is not None:
      await db_set_bonus_xp(bonus)
      bonus_set = bonus
    else:
      bonus_set = 2
      await db_set_bonus_xp(2)

    embed = discord.Embed(
      title='Bonus XP Has Been Set/Reset',
      description='Custom Bonus Updated',
      color=discord.Color.blurple()
    )
    embed.add_field(name='Enabled', value=f"{'On' if enabled else 'Off'}")
    embed.add_field(name='Bonus Amount', value=f'{bonus_set}')

    await ctx.respond(
      embed=embed,
      ephemeral=True
    )

  @admin_group.command(name='grant_random_badge', description='(ADMIN RESTRICTED) Grant a random badge to a user.')
  @option('prestige', int, description='Prestige Tier', required=True, autocomplete=autocomplete_prestige_for_user)
  @option('user', discord.User, description='The user to receive a random badge.', required=True)
  @option(
    name='public',
    description='Show to public?',
    required=True,
    choices=[
      discord.OptionChoice(
        name='No',
        value=False
      ),
      discord.OptionChoice(
        name='Yes',
        value=True
      )
    ]
  )
  @option('reason', str, description='Reason for Grant', required=False)
  @commands.check(user_check)
  async def grant_random_badge(self, ctx, user: discord.User, prestige: str, public: bool, reason: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)

    all_badges = await db_get_all_badge_info()
    owned = await db_get_user_badge_instances(user.id, prestige=prestige)
    owned_ids = {b['badge_info_id'] for b in owned}

    candidates = [b for b in all_badges if b['id'] not in owned_ids]
    if not candidates:
      embed = discord.Embed(
        title='No Eligible Badges',
        description='User already owns every badge at this Prestige level.',
        color=discord.Color.red()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    chosen = random.choice(candidates)
    new_badge = await create_new_badge_instance(user.id, chosen['id'], prestige, event_type='admin')
    if public:
      await post_badge_grant_embed(user, new_badge, reason=reason)

    embed = discord.Embed(
      title='Random Badge Granted',
      description=f"Granted **{chosen['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}** [{new_badge['badge_instance_id']}].",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name='grant_specific_badge', description='(ADMIN RESTRICTED) Grant a specific badge to a user.')
  @option('user', discord.User, description='The user to receive the badge.', required=True)
  @option('prestige', int, description='Prestige Tier', required=True, autocomplete=autocomplete_prestige_for_user)
  @option('badge', int, description='Badge', required=True, autocomplete=autocomplete_all_badges)
  @option(
    name='public',
    description='Show to public?',
    required=True,
    choices=[
      discord.OptionChoice(
        name='No',
        value=False
      ),
      discord.OptionChoice(
        name='Yes',
        value=True
      )
    ]
  )
  @option('reason', str, description='Reason for Grant', required=False)
  @commands.check(user_check)
  async def grant_specific_badge(self, ctx, user: discord.User, prestige: str, badge: str, public: bool, reason: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)
    badge_info = await db_get_badge_info_by_id(badge)

    if not badge_info:
      embed = discord.Embed(
        title='Badge Not Found',
        description='No badge found for that selection.',
        color=discord.Color.red()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    existing = await db_get_badge_instance_by_badge_info_id(user.id, badge_info['id'], prestige)
    if existing:
      embed = discord.Embed(
        title='Already Owned',
        description=f"{user.mention} already owns **{badge_info['badge_name']}** at **{PRESTIGE_TIERS[prestige]}**.",
        color=discord.Color.orange()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    new_badge = await create_new_badge_instance(user.id, badge_info['id'], prestige, event_type='admin')
    if public:
      await post_badge_grant_embed(user, new_badge, reason=reason)

    embed = discord.Embed(
      title='Badge Granted',
      description=f"Granted **{badge_info['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}** [{new_badge['badge_instance_id']}].",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(
    name='grant_random_crystals',
    description='(ADMIN RESTRICTED) Grant X random crystals to a user at a specific rarity.'
  )
  @option('user', discord.User, description='The user to receive crystals.', required=True)
  @option(
    'rarity_rank',
    int,
    description='Crystal rarity rank.',
    required=True,
    choices=[
      discord.OptionChoice(name='Common (1)', value=1),
      discord.OptionChoice(name='Uncommon (2)', value=2),
      discord.OptionChoice(name='Rare (3)', value=3),
      discord.OptionChoice(name='Legendary (4)', value=4),
      discord.OptionChoice(name='Mythic (5)', value=5)
    ]
  )
  @option('amount', int, description='How many to grant.', required=True, min_value=1, max_value=250)
  @commands.check(user_check)
  async def grant_random_crystals(self, ctx: discord.ApplicationContext, user: discord.User, rarity_rank: int, amount: int):
    await ctx.defer(ephemeral=True)

    user_discord_id = str(user.id)

    counts_by_type: dict[str, int] = {}
    created_ids: list[int] = []

    for _ in range(amount):
      crystal_type = await db_select_random_crystal_type_by_rarity_rank(rarity_rank)
      if not crystal_type:
        embed = discord.Embed(
          title='No Crystal Types Found',
          description=f'No crystal types exist for rarity rank `{rarity_rank}`.',
          color=discord.Color.red()
        )
        return await ctx.respond(embed=embed, ephemeral=True)

      created = await create_new_crystal_instance(
        user_discord_id,
        crystal_type['id'],
        event_type='admin'
      )

      created_ids.append(created['crystal_instance_id'])
      key = created.get('crystal_name') or f"Type {crystal_type['id']}"
      counts_by_type[key] = counts_by_type.get(key, 0) + 1

    rarity = await db_get_crystal_rank_by_rarity_rank(rarity_rank)
    rarity_name = rarity['name'] if rarity else f'Rank {rarity_rank}'
    rarity_emoji = rarity.get('emoji') if rarity else None

    embed = discord.Embed(
      title='Crystals Granted',
      description=f"Granted **{amount}** {rarity_name} crystal(s) to {user.mention}.",
      color=discord.Color.green()
    )

    if rarity_emoji:
      embed.add_field(name='Rarity', value=f'{rarity_emoji} {rarity_name}', inline=True)
    else:
      embed.add_field(name='Rarity', value=rarity_name, inline=True)

    embed.add_field(name='Created', value=str(len(created_ids)), inline=True)

    top = sorted(counts_by_type.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    lines = []
    for name, cnt in top[:15]:
      lines.append(f'{cnt}x {name}')
    if len(top) > 15:
      lines.append(f'...and {len(top) - 15} more types')

    if lines:
      embed.add_field(name='Breakdown', value='\n'.join(lines), inline=False)

    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name='transfer_badge_instance', description='(ADMIN RESTRICTED) Transfer a specific badge instance to a user.')
  @option('badge_instance_id', int, description='The ID of the badge instance to transfer')
  @option('to_user', discord.Member, description='User who should receive the badge')
  @commands.check(user_check)
  async def admin_transfer_badge_instance(self, ctx, badge_instance_id: int, to_user: discord.Member):
    await ctx.defer(ephemeral=True)

    instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not instance:
      return await ctx.respond(embed=discord.Embed(
        title='Badge Not Found',
        description=f"Badge instance ID `{badge_instance_id}` does not exist.",
        color=discord.Color.red()
      ), ephemeral=True)

    existing = await db_get_badge_instance_by_badge_info_id(
      to_user.id,
      instance['badge_info_id'],
      instance['prestige_level']
    )
    if existing:
      return await ctx.respond(embed=discord.Embed(
        title='Transfer Blocked',
        description=f"{to_user.mention} already owns **{instance['badge_name']}** at the {PRESTIGE_TIERS[instance['prestige_level']]} Prestige Tier.",
        color=discord.Color.red()
      ), ephemeral=True)

    try:
      await transfer_badge_instance(badge_instance_id, to_user.id, event_type='admin')
      await db_remove_from_continuum(badge_instance_id)

      embed = discord.Embed(
        title='Badge Transferred',
        description=(
          f"Badge `{instance['badge_name']} {PRESTIGE_TIERS[instance['prestige_level']]}` (ID `{badge_instance_id}`) has been transferred to {to_user.mention}.\n"
          "Status set to `active`. Removed from Continuum if present."
        ),
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)

    except Exception as e:
      await log_manual_exception(e, 'Error transfering badge via admin command')
      return await ctx.respond(embed=discord.Embed(
        title='Error',
        description='An unexpected error occurred while transferring the badge.',
        color=discord.Color.orange()
      ), ephemeral=True)

  @admin_group.command(name='grant_crystal_buffer_patterns', description='(ADMIN RESTRICTED) Grant crystal pattern buffers to a user.')
  @option('user', discord.User, description='The user to receive buffers.', required=True)
  @option('amount', int, description='How many to grant.', required=True, min_value=1, max_value=50)
  @commands.check(user_check)
  async def grant_crystal_buffer_patterns(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)

    user_discord_id = str(user.id)
    await db_increment_user_crystal_buffer(user_discord_id, amount)

    new_total = await db_get_user_crystal_buffer_count(user_discord_id)

    embed = discord.Embed(
      title='Pattern Buffer(s) Granted',
      description=(
        f"Granted {amount} Crystal Pattern Buffer(s) to {user.mention}.\n\n"
        f"They now have **{new_total}** total."
      ),
      color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name='check_tongo_games', description='(ADMIN RESTRICTED) Check recent Tongo games with details.')
  @commands.check(user_check)
  async def check_tongo_games(self, ctx):
    await ctx.defer(ephemeral=True)

    async with AgimusDB(dictionary=True) as db:
      sql = 'SELECT * FROM tongo_games ORDER BY created_at DESC LIMIT 3'
      await db.execute(sql)
      games = await db.fetchall()

    if not games:
      embed = discord.Embed(
        title='No Tongo Games Found',
        description='No Tongo games found.',
        color=discord.Color.orange()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    throws_by_game = defaultdict(lambda: defaultdict(list))
    for game in games:
      game_id = game['id']
      created_at = game['created_at']
      throw_rows = await db_get_throws_for_game(game_id, created_at)
      for row in throw_rows:
        throws_by_game[game_id][row['from_user_id']].append((row['badge_name'], row['badge_instance_id']))

    game_groups = []

    for game in games:
      game_id = game['id']
      players = await db_get_players_for_game(game_id)
      rewards = await db_get_rewards_for_game(game_id)

      try:
        chair_member = await self.bot.current_guild.fetch_member(game['chair_user_id'])
        chair_name = f"{chair_member.display_name} ({chair_member.mention})"
      except Exception:
        chair_name = f"<@{game['chair_user_id']}>"

      embed = discord.Embed(
        title=f'Tongo Game ID: {game_id}',
        description=(
          f"Status: {game['status'].capitalize()}\n"
          f"Chair: {chair_name}\n"
          f"Created: {discord.utils.format_dt(game['created_at'], 'R')}\n"
          f"Players: {len(players)}\n"
          f"Rewards: {len(rewards)}"
        ),
        color=discord.Color.teal()
      )

      pages_for_game = [pages.Page(embeds=[embed])]

      user_throws = throws_by_game.get(game_id, {})
      throw_user_ids = list(user_throws.keys())

      for i in range(0, len(throw_user_ids), 5):
        embed = discord.Embed(title='Badge Throws', color=discord.Color.teal())
        for uid in throw_user_ids[i:i + 5]:
          data = user_throws[uid]
          try:
            member = await self.bot.current_guild.fetch_member(uid)
            name = f"{member.display_name} ({member.mention})"
          except Exception:
            name = uid

          value = '\n'.join(f"- {name} [{instance_id}]" for name, instance_id in data)
          embed.add_field(name=name, value=value or '*No badges*', inline=False)

        pages_for_game.append(pages.Page(embeds=[embed]))

      if rewards:
        rewards_by_user = defaultdict(list)
        for reward in rewards:
          rewards_by_user[reward['user_discord_id']].append(reward)

        reward_user_ids = list(rewards_by_user.keys())
        for i in range(0, len(reward_user_ids), 5):
          embed = discord.Embed(title='Game Rewards', color=discord.Color.teal())

          for uid in reward_user_ids[i:i + 5]:
            try:
              player = await self.bot.current_guild.fetch_member(int(uid))
              player_name = f"{player.display_name} ({uid})"
            except discord.NotFound:
              player_name = f'User ID: {uid}'
            except Exception:
              player_name = f'User ID: {uid}'

            entries = []
            for reward in rewards_by_user[uid]:
              badge_id = reward.get('badge_instance_id')
              crystal_id = reward.get('crystal_id')

              desc = ''
              if badge_id:
                badge_instance = await db_get_badge_instance_by_id(badge_id)
                if badge_instance:
                  desc += f"Badge {badge_id} - {badge_instance['badge_name']} (Prestige {badge_instance['prestige_level']})"
                else:
                  desc += f'Badge {badge_id} (Unknown)'
              if crystal_id:
                desc += f' + Crystal {crystal_id}'

              entries.append(desc or 'Unknown Reward')

            embed.add_field(
              name=player_name,
              value='\n'.join(f'- {entry}' for entry in entries),
              inline=False
            )

          pages_for_game.append(pages.Page(embeds=[embed]))

      group = pages.PageGroup(pages=pages_for_game, label=f'Game {game_id}')
      game_groups.append(group)

    paginator = pages.Paginator(pages=game_groups, show_menu=True, show_indicator=True, loop_pages=True)
    await paginator.respond(ctx.interaction, ephemeral=True)

  @admin_group.command(name='examine_tongo_continuum', description='(ADMIN RESTRICTED) View the full details of the Tongo Continuum.')
  @commands.check(user_check)
  async def debug_tongo_pot(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

    continuum = await db_get_full_continuum_badges()
    if not continuum:
      embed = discord.Embed(
        title='Tongo Continuum Empty',
        description='The Tongo continuum is currently empty.',
        color=discord.Color.orange()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    chunks = [continuum[i:i + 10] for i in range(0, len(continuum), 10)]
    continuum_pages = []

    for idx, chunk in enumerate(chunks, start=1):
      embed = discord.Embed(
        title=f'Tongo Continuum Snapshot (Page {idx} of {len(chunks)})',
        description='Current badge instances in the continuum:',
        color=discord.Color.dark_gold()
      )

      for badge in chunk:
        badge_name = badge['badge_name']
        prestige = PRESTIGE_TIERS[badge['prestige_level']]
        player_mention = '**Unknown Member**'
        if badge['thrown_by_user_id'] is None:
          player_mention = '**Grand Nagus Zek**'
        else:
          try:
            player = await self.bot.current_guild.fetch_member(badge['thrown_by_user_id'])
            player_mention = player.mention
          except discord.NotFound:
            pass
          except Exception:
            pass

        embed.add_field(
          name=f'{badge_name} ({prestige})',
          value=f"Instance: `{badge['badge_instance_id']}`\nRisked by: {player_mention}",
          inline=False
        )

      continuum_pages.append(embed)

    paginator = pages.Paginator(
      pages=continuum_pages,
      show_indicator=True,
      loop_pages=True,
      use_default_buttons=True
    )

    await paginator.respond(ctx.interaction, ephemeral=True)

  @admin_group.command(name='manage_tongo_game_players', description="(ADMIN RESTRICTED) Manage a given Tongo Game's players.")
  @option('game_id', int, description='Game.', required=True)
  @commands.check(user_check)
  async def manage_tongo_game_players(self, ctx: discord.ApplicationContext, game_id: int):
    await ctx.defer(ephemeral=True)

    tongo_cog = ctx.bot.get_cog('Tongo')
    if not tongo_cog:
      embed = discord.Embed(
        title='Tongo Cog Missing',
        description='Tongo cog not loaded.',
        color=discord.Color.red()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    players = await db_get_players_for_game(game_id)
    if not players:
      embed = discord.Embed(
        title='No Players Found',
        description='No players found for that game ID.',
        color=discord.Color.orange()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    members = []
    for p in players:
      try:
        member = await self.bot.current_guild.fetch_member(int(p['user_discord_id']))
        members.append(member)
      except Exception as e:
        logger.warning(f"Could not fetch member {p['user_discord_id']} for game #{game_id}: {e}")

    if not members:
      embed = discord.Embed(
        title='No Valid Members Found',
        description='No valid Discord members found for the given game.',
        color=discord.Color.red()
      )
      return await ctx.respond(embed=embed, ephemeral=True)

    class ManageTongoGamesView(discord.ui.View):
      def __init__(self, cog, game_id: int, members: list[discord.Member]):
        super().__init__(timeout=120)
        self.cog = cog
        self.game_id = game_id
        self.members = members
        self.selected_ids = []
        self.add_item(self.PlayerSelect(self))

      class PlayerSelect(discord.ui.Select):
        def __init__(self, view):
          options = [
            discord.SelectOption(label=m.display_name, value=str(m.id))
            for m in view.members
          ]
          super().__init__(
            placeholder='Select players to remove...',
            min_values=1,
            max_values=len(options),
            options=options
          )
          self.view_ref = view

        async def callback(self, interaction):
          self.view_ref.selected_ids = self.values
          await interaction.response.send_message(
            f'Selected {len(self.values)} player(s) for removal. Click confirm to proceed.',
            ephemeral=True
          )

      @discord.ui.button(label='Confirm Removal', style=discord.ButtonStyle.red, row=1)
      async def confirm_removal(self, button, interaction):
        if not self.selected_ids:
          return await interaction.response.send_message('No players selected.', ephemeral=True)

        removed_mentions = []
        refunded_badges = []

        for uid in self.selected_ids:
          uid_int = int(uid)
          await db_remove_player_from_game(self.game_id, uid_int)
          removed_mentions.append(f'<@{uid}>')

          game = await db_get_game_by_id(self.game_id)
          if not game:
            continue

          badge_ids = await db_get_thrown_badge_instance_ids_by_user_for_game(self.game_id, game['created_at'], uid_int)
          if badge_ids:
            await restore_thrown_badges_to_user(uid_int, badge_ids)
            member = await self.cog.bot.current_guild.fetch_member(uid_int)
            refunded_badges.append(f"{member.display_name} - {len(badge_ids)} badge(s) refunded")

        desc = 'The following players were removed:\n' + '\n'.join(removed_mentions)
        if refunded_badges:
          desc += '\n\nThe following badge throws were refunded:\n' + '\n'.join(refunded_badges)

        await interaction.response.send_message(
          embed=discord.Embed(
            title=f'Tongo Game #{self.game_id} Updated',
            description=desc,
            color=discord.Color.orange()
          ),
          ephemeral=True
        )

        self.stop()

    await ctx.respond(
      embed=discord.Embed(
        title=f'Manage Tongo Game Players #{game_id}',
        description='Remove players.',
        color=discord.Color.teal()
      ),
      view=ManageTongoGamesView(tongo_cog, game_id, members),
      ephemeral=True
    )

  @admin_group.command(name='set_tongo_game_status', description='(ADMIN RESTRICTED) Manually set the status of a Tongo game.')
  @option('game_id', int, description='The ID of the Tongo game.', required=True)
  @option('status', str, description='The new status.', required=True, choices=[
    discord.OptionChoice(name='Open', value='open'),
    discord.OptionChoice(name='In Progress', value='in_progress'),
    discord.OptionChoice(name='Resolved', value='resolved'),
    discord.OptionChoice(name='Cancelled', value='cancelled')
  ])
  @commands.check(user_check)
  async def set_tongo_game_status(self, ctx, game_id: int, status: str):
    await ctx.defer(ephemeral=True)
    await db_update_game_status(game_id, status)
    embed = discord.Embed(
      title='Tongo Status Updated',
      description=f'Tongo game #{game_id} status set to **{status}**.',
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)

  @admin_group.command(name='clear_crystal_effects_cache', description='(ADMIN RESTRICTED) Clear the crystal effects disk cache')
  @commands.check(user_check)
  async def clear_crystal_images_cache(self, ctx):
    delete_crystal_effects_cache()
    embed = discord.Embed(
      title='Crystal Image Caches Cleared',
      description='All cached crystal effect images, and replicator animations, have been deleted.',
      color=discord.Color.orange()
    )
    await ctx.respond(embed=embed, ephemeral=True)
