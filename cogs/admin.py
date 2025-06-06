from common import *
import random
from collections import defaultdict

from handlers.echelon_xp import *
from queries.badge_info import *
from queries.badge_instances import *
from queries.crystal_instances import *
from queries.echelon_xp import *
from queries.tongo import *
from utils.badge_instances import *
from utils.crystal_effects import *
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
    target_user_id = ctx.options.get("user")
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


  admin_group = discord.SlashCommandGroup("zed_ops", "Admin-only commands for Badge and Tongo Management.")


  @admin_group.command(name="grant_random_badge", description="(ADMIN RESTRICTED) Grant a random badge to a user.")
  @option("prestige", int, description="Prestige Tier", required=True, autocomplete=autocomplete_prestige_for_user)
  @option("user", discord.User, description="The user to receive a random badge.", required=True)
  @option(
    name="public",
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value=False
      ),
      discord.OptionChoice(
        name="Yes",
        value=True
      )
    ]
  )
  @option("reason", str, description="Reason for Grant", required=False)
  @commands.check(user_check)
  async def grant_random_badge(self, ctx, user: discord.User, prestige: str, public: bool, reason: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)

    all_badges = await db_get_all_badge_info()
    owned = await db_get_user_badge_instances(user.id, prestige=prestige)
    owned_ids = {b['badge_info_id'] for b in owned}

    candidates = [b for b in all_badges if b['id'] not in owned_ids]
    if not candidates:
      return await ctx.respond("❌ User already owns every badge at this Prestige level.", ephemeral=True)

    chosen = random.choice(candidates)
    new_badge = await create_new_badge_instance(user.id, chosen['id'], prestige, event_type='admin')
    if public:
      await post_badge_grant_embed(user, new_badge, reason=reason)

    embed = discord.Embed(
      title="Random Badge Granted",
      description=f"✅ Granted **{chosen['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}** [{new_badge['badge_instance_id']}].",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="grant_specific_badge", description="(ADMIN RESTRICTED) Grant a specific badge to a user.")
  @option("user", discord.User, description="The user to receive the badge.", required=True)
  @option("prestige", int, description="Prestige Tier", required=True, autocomplete=autocomplete_prestige_for_user)
  @option("badge", int, description="Badge", required=True, autocomplete=autocomplete_all_badges)
  @option(
    name="public",
    description="Show to public?",
    required=True,
    choices=[
      discord.OptionChoice(
        name="No",
        value=False
      ),
      discord.OptionChoice(
        name="Yes",
        value=True
      )
    ]
  )
  @option("reason", str, description="Reason for Grant", required=False)
  @commands.check(user_check)
  async def grant_specific_badge(self, ctx, user: discord.User, prestige: str, badge: str, public: bool, reason:str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)
    badge_info = await db_get_badge_info_by_id(badge)

    if not badge_info:
      return await ctx.respond(f"❌ No badge found with name '{badge_info['badge_name']}'", ephemeral=True)

    existing = await db_get_badge_instance_by_badge_info_id(user.id, badge_info['id'], prestige)
    if existing:
      return await ctx.respond(f"⚠️ {user.mention} already owns **{badge_info['badge_name']}** at **{PRESTIGE_TIERS[prestige]}**.", ephemeral=True)

    new_badge = await create_new_badge_instance(user.id, badge_info['id'], prestige, event_type='admin')
    if public:
      await post_badge_grant_embed(user, new_badge, reason=reason)

    embed = discord.Embed(
      title="Badge Granted",
      description=f"✅ Granted **{badge_info['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}** [{new_badge['badge_instance_id']}].",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="transfer_badge_instance", description="(ADMIN RESTRICTED) Transfer a specific badge instance to a user.")
  @option("badge_instance_id", int, description="The ID of the badge instance to transfer")
  @option("to_user", discord.Member, description="User who should receive the badge")
  @commands.check(user_check)
  async def admin_transfer_badge_instance(self, ctx, badge_instance_id: int, to_user: discord.Member):
    await ctx.defer(ephemeral=True)

    instance = await db_get_badge_instance_by_id(badge_instance_id)
    if not instance:
      return await ctx.respond(embed=discord.Embed(
        title="❌ Badge Not Found",
        description=f"Badge instance ID `{badge_instance_id}` does not exist.",
        color=discord.Color.red()
      ), ephemeral=True)

    try:
      # Transfer badge to new user (logs history, wishlist logic included)
      await transfer_badge_instance(badge_instance_id, to_user.id, event_type="admin")

      # Remove from continuum if present (safe to run even if not there)
      await db_remove_from_continuum(badge_instance_id)

      # Final confirmation
      embed = discord.Embed(
        title="✅ Badge Transferred",
        description=(
          f"Badge `{instance['badge_name']}` (ID `{badge_instance_id}`) has been transferred to {to_user.mention}.\n"
          f"Status set to `active`. Removed from Continuum if present."
        ),
        color=discord.Color.green()
      )
      await ctx.respond(embed=embed, ephemeral=True)

    except Exception as e:
      await log_manual_exception("ADMIN_TRANSFER_BADGE", e)
      return await ctx.respond(embed=discord.Embed(
        title="⚠️ Error",
        description="An unexpected error occurred while transferring the badge.",
        color=discord.Color.orange()
      ), ephemeral=True)

  @admin_group.command(name="grant_crystal_buffer_patterns", description="(ADMIN RESTRICTED) Grant crystal pattern buffers to a user.")
  @option("user", discord.User, description="The user to receive buffers.", required=True)
  @option("amount", int, description="How many to grant.", required=True, min_value=1, max_value=50)
  @commands.check(user_check)
  async def grant_crystal_buffer_patterns(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)
    await db_increment_user_crystal_buffer(user.id, amount)

    new_total = await db_get_user_crystal_buffer_count(user.id)

    embed = discord.Embed(
      title="Pattern Buffer(s) Granted",
      description=(
        "✨ Granted {amount} Crystal Pattern Buffer(s) to {user.mention}.\n\n"
        f"They now have **{new_total}** total."
      ),
      color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="check_tongo_games", description="(ADMIN RESTRICTED) Check recent Tongo games with details.")
  @commands.check(user_check)
  async def check_tongo_games(self, ctx):
    await ctx.defer(ephemeral=True)

    async with AgimusDB(dictionary=True) as db:
      await db.execute("SELECT * FROM tongo_games ORDER BY created_at DESC LIMIT 10")
      games = await db.fetchall()

    if not games:
      return await ctx.respond("No Tongo games found.", ephemeral=True)

    throws_by_game = defaultdict(lambda: defaultdict(list))
    for game in games:
      game_id = game['id']
      created_at = game['created_at']
      throw_rows = await db_get_throws_for_game(game_id, created_at)
      for row in throw_rows:
        throws_by_game[game_id][row['from_user_id']].append(row['badge_name'])

    game_groups = []

    for game in games:
      game_id = game['id']
      players = await db_get_all_game_player_ids(game_id)
      rewards = await db_get_rewards_for_game(game_id)

      try:
        chair_member = await bot.current_guild.fetch_member(game['chair_user_id'])
        chair_name = f"{chair_member.display_name} ({chair_member.mention})"
      except:
        chair_name = f"<@{game['chair_user_id']}>"

      embed = discord.Embed(
        title=f"Tongo Game ID: {game_id}",
        description=(
          f"**Status:** {game['status'].capitalize()}\n"
          f"**Chair:** {chair_name}\n"
          f"**Created:** {discord.utils.format_dt(game['created_at'], 'R')}\n"
          f"**Players:** {len(players)}\n"
          f"**Rewards:** {len(rewards)}"
        ),
        color=discord.Color.teal()
      )

      pages_for_game = [pages.Page(embeds=[embed])]

      # Badge Throws — 1 field per user, 5 users per embed
      user_throws = throws_by_game.get(game_id, {})
      throw_user_ids = list(user_throws.keys())

      for i in range(0, len(throw_user_ids), 5):
        embed = discord.Embed(title="Badge Throws", color=discord.Color.teal())
        for uid in throw_user_ids[i:i + 5]:
          badge_names = user_throws[uid]
          try:
            member = await bot.current_guild.fetch_member(uid)
            name = f"{member.display_name} ({member.mention})"
          except:
            name = f"<@{uid}>"

          value = "\n".join(f"- {b}" for b in badge_names)
          embed.add_field(name=name, value=value or "*No badges*", inline=False)

        pages_for_game.append(pages.Page(embeds=[embed]))

      # Rewards — 1 field per user, 5 users per embed
      if rewards:
        rewards_by_user = defaultdict(list)
        for reward in rewards:
          rewards_by_user[reward['user_discord_id']].append(reward)

        reward_user_ids = list(rewards_by_user.keys())
        for i in range(0, len(reward_user_ids), 5):
          embed = discord.Embed(title="Game Rewards", color=discord.Color.teal())

          for uid in reward_user_ids[i:i + 5]:
            entries = []
            for reward in rewards_by_user[uid]:
              badge_id = reward.get('badge_instance_id')
              crystal_id = reward.get('crystal_id')

              desc = ""
              if badge_id:
                badge_instance = await db_get_badge_instance_by_id(badge_id)
                if badge_instance:
                  desc += f"Badge {badge_id} - {badge_instance['badge_name']} (Prestige {badge_instance['prestige_level']})"
                else:
                  desc += f"Badge {badge_id} (Unknown)"
              if crystal_id:
                desc += f" + Crystal {crystal_id}"

              entries.append(desc or "Unknown Reward")

            embed.add_field(
              name=f"<@{uid}>",
              value="\n".join(f"- {entry}" for entry in entries),
              inline=False
            )

          pages_for_game.append(pages.Page(embeds=[embed]))

      group = pages.PageGroup(pages=pages_for_game, label=f"Game {game_id}")
      game_groups.append(group)

    paginator = pages.Paginator(pages=game_groups, show_menu=True, show_indicator=True, loop_pages=True)
    await paginator.respond(ctx.interaction, ephemeral=True)


  @admin_group.command(name="examine_tongo_continuum", description="(ADMIN RESTRICTED) View the full details of the Tongo Continuum.")
  @commands.check(user_check)
  async def debug_tongo_pot(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

    # Get all badges currently in the continuum
    continuum = await db_get_full_continuum_badges()
    if not continuum:
      return await ctx.respond("ℹ️ The Tongo continuum is currently empty.", ephemeral=True)

    # Chunk the data for pagination
    chunks = [continuum[i:i + 10] for i in range(0, len(continuum), 10)]
    continuum_pages = []

    for idx, chunk in enumerate(chunks, start=1):
      embed = discord.Embed(
        title=f"Tongo Continuum Snapshot (Page {idx} of {len(chunks)})",
        description="Current badge instances in the continuum:",
        color=discord.Color.dark_gold()
      )

      for badge in chunk:
        badge_name = badge['badge_name']
        prestige = PRESTIGE_TIERS[badge['prestige_level']]
        player_mention = "**Unknown Member**"
        if badge['thrown_by_user_id'] is None:
          player_mention = "**Grand Nagus Zek**"
        else:
          try:
            player = await self.bot.current_guild.fetch_member(badge['thrown_by_user_id'])
            player_mention = player.mention
          except discord.NotFound:
            pass

        embed.add_field(
          name=f"{badge_name} ({prestige})",
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


  @admin_group.command(name="manage_tongo_game_players", description="(ADMIN RESTRICTED) Manage a given Tongo Game's players.")
  @option("game_id", int, description="Game.", required=True)
  @commands.check(user_check)
  async def manage_tongo_game_players(self, ctx: discord.ApplicationContext, game_id: int):
    await ctx.defer(ephemeral=True)

    tongo_cog = ctx.bot.get_cog("Tongo")
    if not tongo_cog:
      return await ctx.respond("❌ Tongo cog not loaded.", ephemeral=True)

    players = await db_get_players_for_game(game_id)
    if not players:
      return await ctx.respond("⚠️ No players found for that game ID.", ephemeral=True)

    members = []
    for p in players:
      try:
        member = await self.bot.current_guild.fetch_member(int(p['user_discord_id']))
        members.append(member)
      except Exception as e:
        logger.warning(f"Could not fetch member {p['user_discord_id']} for game #{game_id}: {e}")

    if not members:
      return await ctx.respond("❌ No valid Discord members found for the given game.", ephemeral=True)

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
            placeholder="Select players to remove...",
            min_values=1, max_values=len(options),
            options=options
          )
          self.view_ref = view

        async def callback(self, interaction):
          self.view_ref.selected_ids = self.values
          await interaction.response.send_message(
            f"✅ Selected {len(self.values)} player(s) for removal. Click confirm to proceed.",
            ephemeral=True
          )

      @discord.ui.button(label="Confirm Removal", style=discord.ButtonStyle.red, row=1)
      async def confirm_removal(self, button, interaction):
        if not self.selected_ids:
          return await interaction.response.send_message("⚠️ No players selected.", ephemeral=True)

        removed_mentions = []
        refunded_badges = []

        for uid in self.selected_ids:
          uid_int = int(uid)
          await db_remove_player_from_game(self.game_id, uid_int)
          removed_mentions.append(f"<@{uid}>")

          game = await db_get_game_by_id(self.game_id)
          if not game:
            continue

          badge_ids = await db_get_thrown_badge_instance_ids_by_user_for_game(self.game_id, game['created_at'], uid_int)
          if badge_ids:
            await restore_thrown_badges_to_user(uid_int, badge_ids)
            member = await self.cog.bot.current_guild.fetch_member(uid_int)
            refunded_badges.append(f"{member.display_name} – {len(badge_ids)} badge(s) refunded")

        desc = "The following players were removed:\n" + "\n".join(removed_mentions)
        if refunded_badges:
          desc += "\n\nThe following badge throws were refunded:\n" + "\n".join(refunded_badges)

        await interaction.response.send_message(
          embed=discord.Embed(
            title=f"Tongo Game #{self.game_id} Updated",
            description=desc,
            color=discord.Color.orange()
          ),
          ephemeral=True
        )

        self.stop()

    await ctx.respond(
      embed=discord.Embed(
        title=f"Manage Tongo Game Players #{game_id}",
        description="Remove players.",
        color=discord.Color.teal()
      ),
      view=ManageTongoGamesView(tongo_cog, game_id, members),
      ephemeral=True
    )


  @admin_group.command(name="set_tongo_game_status", description="(ADMIN RESTRICTED) Manually set the status of a Tongo game.")
  @option("game_id", int, description="The ID of the Tongo game.", required=True)
  @option("status", str, description="The new status.", required=True, choices=[
    discord.OptionChoice(name="Open", value="open"),
    discord.OptionChoice(name="In Progress", value="in_progress"),
    discord.OptionChoice(name="Resolved", value="resolved"),
    discord.OptionChoice(name="Cancelled", value="cancelled")
  ])
  @commands.check(user_check)
  async def set_tongo_game_status(self, ctx, game_id: int, status: str):
    await ctx.defer(ephemeral=True)
    await db_update_game_status(game_id, status)
    await ctx.respond(f"✅ Tongo game **#{game_id}** status set to **{status}**.", ephemeral=True)


  @admin_group.command(name="clear_crystal_effects_cache", description="(ADMIN RESTRICTED) Clear the crystal effects disk cache")
  @commands.check(user_check)
  async def clear_crystal_images_cache(self, ctx):
    delete_crystal_effects_cache()
    embed = discord.Embed(
      title="Crystal Image Caches Cleared",
      description="🧹 All cached crystal effect images, and replicator animations, have been deleted.",
      color=discord.Color.orange()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  # @admin_group.command(name="repair_levels", description="(ADMIN RESTRICTED) Correct Missing Levels.")
  # @commands.check(user_check)
  # async def repair_levels(self, ctx):
  #   await ctx.defer(ephemeral=True)

  #   sql = "SELECT user_discord_id, current_xp, current_level FROM echelon_progress"

  #   async with AgimusDB(dictionary=True) as db:
  #     await db.execute(sql)
  #     users = await db.fetchall()

  #   total_users = 0
  #   total_levels_awarded = 0
  #   failed_users = []

  #   for row in users:
  #     user_id = row['user_discord_id']
  #     xp = row['current_xp']
  #     stored_level = row['current_level']
  #     correct_level = level_for_total_xp(xp)

  #     if correct_level > stored_level:
  #       try:
  #         user_obj = await self.bot.fetch_user(int(user_id))
  #         for lvl in range(stored_level + 1, correct_level + 1):
  #           await handle_user_level_up(user_obj, lvl, source="Level Repair (XP Exceeds Stored Level)")
  #           await asyncio.sleep(0.9)
  #           total_levels_awarded += 1
  #         total_users += 1
  #       except Exception as e:
  #         failed_users.append(user_id)

  #   summary = discord.Embed(
  #     title="🛠 Level-Up Repair Complete",
  #     description=(
  #       f"* Checked `{len(users)}` users.\n"
  #       f"* `{total_users}` users had missed level-ups.\n"
  #       f"* {total_levels_awarded}` total levels granted.\n"
  #     ),
  #     color=discord.Color.teal()
  #   )

  #   if failed_users:
  #     summary.add_field(
  #       name="⚠️ Users Not Processed",
  #       value=", ".join(failed_users),
  #       inline=False
  #     )

  #   await ctx.respond(embed=summary, ephemeral=True)


  # @admin_group.command(name="repair_levelup_badges", description="(ADMIN RESTRICTED) Correct Missing Badges.")
  # @commands.check(user_check)
  # async def repair_missing_levelup_badges(self, ctx):
  #   await ctx.defer(ephemeral=True)

  #   async with AgimusDB(dictionary=True) as db:
  #     await db.execute("SELECT user_discord_id, current_xp, current_level FROM echelon_progress")
  #     users = await db.fetchall()

  #   total_users_fixed = 0
  #   total_badges_granted = 0
  #   failed = []

  #   for row in users:
  #     user_id = row['user_discord_id']
  #     expected = row['current_level']
  #     xp = row['current_xp']

  #     xp_enabled = bool(await db_get_current_xp_enabled_value(user_id))
  #     if not xp_enabled:
  #       continue

  #     if xp == 0:
  #       continue

  #     actual = await db_get_levelup_badge_count(user_id)
  #     missing = expected - actual

  #     if missing <= 0:
  #       continue

  #     logger.info(f">  [{user_id}]: User Found With Missing Badges")
  #     logger.info(f">> [{user_id}]: Expected: {expected}; Actual: {actual}")
  #     logger.info(f">> [{user_id}]: Missing: {missing}")

  #     try:
  #       user_obj = await self.bot.fetch_user(int(user_id))
  #       for _ in range(missing):
  #         badge_data = await award_level_up_badge(user_obj)

  #         if row['current_level'] == 1:
  #           await post_first_level_welcome_embed(user_obj, badge_data, source_details=None)
  #           await db_increment_user_crystal_buffer(user_id, amount=3)
  #           await post_buffer_pattern_acquired_embed(user_obj, 1, 3)
  #         else:
  #           await post_badge_repair_embed(user_obj, badge_data)
  #           await award_possible_crystal_pattern_buffer(user_obj)

  #         await asyncio.sleep(0.5)
  #         total_badges_granted += 1
  #       total_users_fixed += 1
  #     except Exception as e:
  #       logger.info(f"Error: Problem with `repair_missing_levelup_badges` for {user_id}", exc_info=True)
  #       failed.append(user_id)

  #   summary = discord.Embed(
  #     title="🛠 Missing Level-Up Badges Repaired",
  #     description=(
  #       f"🔍 Scanned `{len(users)}` users.\n"
  #       f"✅ `{total_users_fixed}` users had missing badges.\n"
  #       f"🎖 `{total_badges_granted}` badges granted via repair.\n"
  #     ),
  #     color=discord.Color.teal()
  #   )
  #   if failed:
  #     summary.add_field(name="⚠️ Failed Users", value=f"{len(failed)}", inline=False)

  #   await ctx.respond(embed=summary, ephemeral=True)


  # @admin_group.command(name="repair_badges_special_grant", description="(ADMIN RESTRICTED) Address Erroneous Special Badge Grants.")
  # @commands.check(user_check)
  # async def repair_special_badge_levelup_bug(self, ctx):
  #   await ctx.defer(ephemeral=True)

  #   # Step 1: Query affected badge_instance IDs
  #   query = """
  #     SELECT bi.id AS instance_id, bi.owner_discord_id, bi.badge_info_id, binfo.badge_name
  #     FROM badge_instances bi
  #     JOIN badge_info binfo ON bi.badge_info_id = binfo.id
  #     WHERE binfo.special = 1
  #       AND bi.status = 'active'
  #       AND EXISTS (
  #         SELECT 1 FROM badge_instance_history h
  #         WHERE h.badge_instance_id = bi.id
  #           AND h.event_type = 'level_up'
  #       )
  #       AND NOT EXISTS (
  #         SELECT 1 FROM badge_instance_history h2
  #         WHERE h2.badge_instance_id = bi.id
  #           AND h2.event_type = 'prestige_echo'
  #       )
  #   """

  #   async with AgimusDB(dictionary=True) as db:
  #     await db.execute(query)
  #     rows = await db.fetchall()

  #   if not rows:
  #     return await ctx.respond("✅ No invalid special badges found to archive.", ephemeral=True)

  #   summary = defaultdict(lambda: {'display_name': None, 'archived': [], 'granted': []})
  #   total_archived = 0
  #   total_granted = 0

  #   # Step 2: Archive bugged badges
  #   for row in rows:
  #     user_id = row['owner_discord_id']
  #     badge_name = row['badge_name']
  #     try:
  #       await archive_badge_instance(row['instance_id'])
  #       summary[user_id]['archived'].append(badge_name)
  #       total_archived += 1
  #     except Exception as e:
  #       logger.warning(f"Error archiving badge_instance_id {row['instance_id']}: {e}")

  #   # Step 3: Fetch display names + grant replacements
  #   for user_id, data in summary.items():
  #     try:
  #       user_obj = await self.bot.fetch_user(int(user_id))
  #       summary[user_id]['display_name'] = user_obj.display_name
  #       for _ in data['archived']:
  #         new_badge = await award_level_up_badge(user_obj)
  #         await post_badge_repair_embed(user_obj, new_badge, reason="Had been erroneously granted a 'Special' restricted badge due to an award system bug!")
  #         summary[user_id]['granted'].append(new_badge['badge_name'])
  #         await asyncio.sleep(0.4)
  #         total_granted += 1
  #     except Exception as e:
  #       logger.warning(f"Error compensating user {user_id}: {e}")

  #   # Step 4: Build .txt report
  #   lines = ["AGIMUS Special Badge Level-Up Bug Repair Log\n"]
  #   for user_id, info in summary.items():
  #     lines.append(f"{info['display_name']} ({user_id})")
  #     lines.append("  Archived Badges:")
  #     for badge in info['archived']:
  #       lines.append(f"    - {badge}")
  #     lines.append("  Replacement Badges Granted:")
  #     for badge in info['granted']:
  #       lines.append(f"    + {badge}")
  #     lines.append("")
  #   report_text = "\n".join(lines)
  #   buffer = io.BytesIO()
  #   buffer.write(report_text.encode('utf-8'))
  #   buffer.seek(0)
  #   buffer.name = "special_badge_bug_repair_report.txt"

  #   # Step 5: Respond with summary + file
  #   embed = discord.Embed(
  #     title="🧹 Special Badge Repair Complete",
  #     description=(
  #       f"Archived `{total_archived}` improperly granted **special** badge(s).\n"
  #       f"Affected users: `{len(summary)}`\n"
  #       f"Replacement badges granted: `{total_granted}`\n\n"
  #       "See attached file for full user breakdown."
  #     ),
  #     color=discord.Color.red()
  #   )

  #   await ctx.respond(embed=embed, file=discord.File(fp=buffer), ephemeral=True)
