from common import *
import random
from collections import defaultdict

from queries.badge_info import db_get_all_badge_info, db_get_badge_info_by_id
from queries.badge_instances import db_get_user_badge_instances, db_get_badge_instance_by_badge_info_id
from queries.crystal_instances import db_increment_user_crystal_buffer
from queries.echelon_xp import db_get_echelon_progress
from queries.tongo import db_get_open_game, db_get_all_game_player_ids, db_get_full_continuum_badges, db_update_game_status, db_get_rewards_for_game, db_get_throws_for_game
from utils.badge_instances import create_new_badge_instance
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



  admin_group = discord.SlashCommandGroup("admin", "Admin-only commands for badge and Tongo testing.")

  @admin_group.command(name="grant_random_badge", description="Grant a random badge to a user.")
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


  @admin_group.command(name="grant_specific_badge", description="Grant a specific badge to a user.")
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

    await create_new_badge_instance(user.id, badge_info, prestige, event_type='admin')

    embed = discord.Embed(
      title="Badge Granted",
      description=f"✅ Granted **{badge_info['badge_name']}** to {user.mention} at **{PRESTIGE_TIERS[prestige]}**.",
      color=discord.Color.green()
    )
    await ctx.respond(embed=embed, ephemeral=True)


  @admin_group.command(name="grant_crystal_buffer_patterns", description="Grant crystal pattern buffers to a user.")
  @option("user", discord.User, description="The user to receive buffers.", required=True)
  @option("amount", int, description="How many to grant.", required=True, min_value=1, max_value=50)
  @commands.check(user_check)
  async def grant_crystal_buffer_patterns(self, ctx, user: discord.User, amount: int):
    await ctx.defer(ephemeral=True)
    await db_increment_user_crystal_buffer(user.id, amount)

    await ctx.respond(f"✨ Granted {amount} Replicator Pattern Buffer(s) to {user.mention}.", ephemeral=True)


  @admin_group.command(name="check_tongo_games", description="Check recent and open Tongo games with full detail.")
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
          embed.add_field(name=f"{member.display_name} (@{uid}) threw:", value=value, inline=False)

      # Reward summary
      if rewards:
        reward_lines = []
        for reward in rewards:
          uid = reward['user_discord_id']
          badge_id = reward.get('badge_instance_id')
          crystal_id = reward.get('crystal_id')
          desc = f"Badge {badge_id}" if badge_id else "Unknown Badge"
          if crystal_id:
            desc += f" + Crystal {crystal_id}"
          reward_lines.append(f"<@{uid}>: {desc}")
        embed.add_field(name="Game Rewards", value="\n".join(reward_lines), inline=False)

      embeds.append(embed)

    paginator = pages.Paginator(pages=embeds, show_indicator=True, loop_pages=True)
    await paginator.respond(ctx.interaction, ephemeral=True)


  @admin_group.command(name="set_tongo_game_status", description="Manually set the status of a Tongo game.")
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

