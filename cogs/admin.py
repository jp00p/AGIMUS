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
from utils.prestige import PRESTIGE_TIERS

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
      for b in badge_records if ctx.value.lower() in b['badge_name'].lower()
    ]
    return choices


  admin_group = discord.SlashCommandGroup("zed_ops", "Admin-only commands for Badge and Tongo Management.")


  @admin_group.command(name="grant_random_badge", description="(ADMIN RESTRICTED) Grant a random badge to a user.")
  @option("prestige", int, description="Prestige Tier", required=True, autocomplete=autocomplete_prestige_for_user)
  @option("user", discord.User, description="The user to receive a random badge.", required=True)
  @commands.check(user_check)
  async def grant_random_badge(self, ctx, user: discord.User, prestige: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)

    all_badges = await db_get_all_badge_info()
    owned = await db_get_user_badge_instances(user.id, prestige=prestige)
    owned_ids = {b['badge_info_id'] for b in owned}

    candidates = [b for b in all_badges if b['id'] not in owned_ids]
    if not candidates:
      return await ctx.respond("❌ User already owns every badge at this Prestige level.", ephemeral=True)

    chosen = random.choice(candidates)
    await create_new_badge_instance(user.id, chosen['id'], prestige, event_type='admin')

    embed = discord.Embed(
      title="Random Badge Granted",
      description=f"✅ Granted **{chosen['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}**.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="grant_specific_badge", description="(ADMIN RESTRICTED) Grant a specific badge to a user.")
  @option("user", discord.User, description="The user to receive the badge.", required=True)
  @option("prestige", int, description="Prestige Tier", required=True, autocomplete=autocomplete_prestige_for_user)
  @option("badge", int, description="Badge", required=True, autocomplete=autocomplete_all_badges)
  @commands.check(user_check)
  async def grant_specific_badge(self, ctx, user: discord.User, badge: str, prestige: str):
    await ctx.defer(ephemeral=True)
    prestige = int(prestige)
    badge_info = await db_get_badge_info_by_id(badge)

    if not badge_info:
      return await ctx.respond(f"❌ No badge found with name '{badge_info['badge_name']}'", ephemeral=True)

    existing = await db_get_badge_instance_by_badge_info_id(user.id, badge_info['id'], prestige)
    if existing:
      return await ctx.respond(f"⚠️ {user.mention} already owns **{badge_info['badge_name']}** at **{PRESTIGE_TIERS[prestige]}**.", ephemeral=True)

    await create_new_badge_instance(user.id, badge_info['id'], prestige, event_type='admin')

    embed = discord.Embed(
      title="Badge Granted",
      description=f"✅ Granted **{badge_info['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}**.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="grant_crystal_buffer_patterns", description="(ADMIN RESTRICTED) Grant crystal pattern buffers to a user.")
  @option("user", discord.User, description="The user to receive buffers.", required=True)
  @option("amount", int, description="How many to grant.", required=True, min_value=1, max_value=50)
  @commands.check(user_check)
  async def grant_crystal_buffer_patterns(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)
    await db_increment_user_crystal_buffer(user.id, amount)

    await ctx.respond(f"✨ Granted {amount} Replicator Pattern Buffer(s) to {user.mention}.", ephemeral=True)


  @admin_group.command(name="check_tongo_games", description="(ADMIN RESTRICTED) Check recent Tongo games with details.")
  @commands.check(user_check)
  async def check_tongo_games(self, ctx):
    await ctx.defer(ephemeral=True)

    async with AgimusDB(dictionary=True) as db:
      await db.execute("SELECT * FROM tongo_games ORDER BY created_at DESC LIMIT 10")
      games = await db.fetchall()

    if not games:
      return await ctx.respond("No Tongo games found.", ephemeral=True)

    # Preload all throw data per game
    throws_by_game = defaultdict(lambda: defaultdict(list))  # game_id -> user_id -> list of badge names
    for game in games:
      game_id = game['id']
      created_at = game['created_at']
      throw_rows = await db_get_throws_for_game(game_id, created_at)
      for row in throw_rows:
        throws_by_game[game_id][row['from_user_id']].append(row['badge_name'])

    # Build embeds
    embeds = []
    for game in games:
      game_id = game['id']
      players = await db_get_all_game_player_ids(game_id)
      rewards = await db_get_rewards_for_game(game_id)

      embed = discord.Embed(
        title=f"Tongo Game ID: {game_id}",
        description=(
          f"**Status:** {game['status'].capitalize()} \n"
          f"**Chair:** <@{game['chair_user_id']}> \n"
          f"**Created:** {discord.utils.format_dt(game['created_at'], 'R')} \n"
          f"**Players:** {len(players)} \n"
          f"**Rewards:** {len(rewards)}"
        ),
        color=discord.Color.teal()
      )

      # Badge throws
      user_throws = throws_by_game.get(game_id, {})
      if user_throws:
        for uid, badge_names in user_throws.items():
          member = await bot.current_guild.fetch_member(uid)
          value = "\n".join(f"- {name}" for name in badge_names)
          embed.add_field(name=f"{member.display_name} ({member.mention}) threw:", value=value, inline=False)

      # Reward summary
      if rewards:
        reward_lines = []
        for reward in rewards:
          uid = reward['user_discord_id']
          badge_id = reward.get('badge_instance_id')
          crystal_id = reward.get('crystal_id')
          badge_instance = await db_get_badge_instance_by_id(badge_id)
          desc = f"Badge {badge_id} - {badge_instance['badge_name']} ({badge_instance['prestige_level']})" if badge_id else "Unknown Badge"
          if crystal_id:
            desc += f" + Crystal {crystal_id}"
          reward_lines.append(f"<@{uid}>: {desc}")
        embed.add_field(name="Game Rewards", value="\n".join(reward_lines), inline=False)

      embeds.append(embed)

    paginator = pages.Paginator(pages=embeds, show_indicator=True, loop_pages=True)
    await paginator.respond(ctx.interaction, ephemeral=True)


  @admin_group.command(name="manage_tongo_game", description="(ADMIN RESTRICTED) Manage a given Tongo Game.")
  @option("game_id", int, description="Game.", required=True)
  @commands.check(user_check)
  async def manage_tongo_game(self, ctx: discord.ApplicationContext, game_id: int):
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

      @discord.ui.button(label="Toggle New Game Creation", style=discord.ButtonStyle.gray, row=1)
      async def toggle_new_games(self, button, interaction):
        self.cog.block_new_games = not self.cog.block_new_games
        new_status = "ENABLED ✅" if not self.cog.block_new_games else "BLOCKED ❌"
        await interaction.response.send_message(
          embed=discord.Embed(
            title="Tongo Game Creation Toggled",
            description=f"New `/tongo venture` games are now **{new_status}**.",
            color=discord.Color.green() if not self.cog.block_new_games else discord.Color.red()
          ),
          ephemeral=True
        )
        self.stop()

    await ctx.respond(
      embed=discord.Embed(
        title=f"Manage Tongo Game #{game_id}",
        description="Remove players or toggle new game creation.",
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


  @admin_group.command(name="repair_levels", description="(ADMIN RESTRICTED) Correct Missing Levels.")
  @commands.check(user_check)
  async def repair_levels(self, ctx):
    await ctx.defer(ephemeral=True)

    sql = "SELECT user_discord_id, current_xp, current_level FROM echelon_progress"

    async with AgimusDB(dictionary=True) as db:
      await db.execute(sql)
      users = await db.fetchall()

    total_users = 0
    total_levels_awarded = 0
    failed_users = []

    for row in users:
      user_id = row['user_discord_id']
      xp = row['current_xp']
      stored_level = row['current_level']
      correct_level = level_for_total_xp(xp)

      if correct_level > stored_level:
        try:
          user_obj = await self.bot.fetch_user(int(user_id))
          for lvl in range(stored_level + 1, correct_level + 1):
            await handle_user_level_up(user_obj, lvl, source="Level Repair (XP Exceeds Stored Level)")
            await asyncio.sleep(0.9)
            total_levels_awarded += 1
          total_users += 1
        except Exception as e:
          failed_users.append(user_id)

    summary = discord.Embed(
      title="🛠 Level-Up Repair Complete",
      description=(
        f"* Checked `{len(users)}` users.\n"
        f"* `{total_users}` users had missed level-ups.\n"
        f"* {total_levels_awarded}` total levels granted.\n"
      ),
      color=discord.Color.teal()
    )

    if failed_users:
      summary.add_field(
        name="⚠️ Users Not Processed",
        value=", ".join(failed_users),
        inline=False
      )

    await ctx.respond(embed=summary, ephemeral=True)


  @admin_group.command(name="repair_levelup_badges", description="(ADMIN RESTRICTED) Correct Missing Badges.")
  @commands.check(user_check)
  async def repair_missing_levelup_badges(self, ctx):
    await ctx.defer(ephemeral=True)

    async with AgimusDB(dictionary=True) as db:
      await db.execute("SELECT user_discord_id, current_level FROM echelon_progress")
      users = await db.fetchall()

    total_users_fixed = 0
    total_badges_granted = 0
    failed = []

    for row in users:
      user_id = row['user_discord_id']
      expected = row['current_level']

      actual = await db_get_levelup_badge_count(user_id)
      missing = expected - actual

      if missing <= 0:
        continue

      logger.info(f">  [{user_id}]: User Found With Missing Badges")
      logger.info(f">> [{user_id}]: Expected: {expected}; Actual: {actual}")
      logger.info(f">> [{user_id}]: Missing: {missing}")

      try:
        user_obj = await self.bot.fetch_user(int(user_id))
        for _ in range(missing):
          badge_data = await award_level_up_badge(user_obj)

          if row['current_level'] == 1:
            await post_first_level_welcome_embed(user_obj, badge_data, source_details=None)
            await db_increment_user_crystal_buffer(user_id, amount=3)
            await post_buffer_pattern_acquired_embed(user_obj, 1, 3)
          else:
            await post_badge_repair_embed(user_obj, badge_data)
            awarded_buffer_pattern = await award_possible_crystal_pattern_buffer(user_obj)
            if awarded_buffer_pattern:
              await post_buffer_pattern_acquired_embed(user_obj, 0, awarded_buffer_pattern)

          await asyncio.sleep(0.75)
          total_badges_granted += 1
        total_users_fixed += 1
      except Exception as e:
        failed.append(user_id)

    summary = discord.Embed(
      title="🛠 Missing Level-Up Badges Repaired",
      description=(
        f"🔍 Scanned `{len(users)}` users.\n"
        f"✅ `{total_users_fixed}` users had missing badges.\n"
        f"🎖 `{total_badges_granted}` badges granted via repair.\n"
      ),
      color=discord.Color.teal()
    )
    if failed:
      summary.add_field(name="⚠️ Failed Users", value=f"{len(failed)}", inline=False)

    await ctx.respond(embed=summary, ephemeral=True)
