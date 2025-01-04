from common import *
from utils.settings_utils import db_get_current_xp_enabled_value
from tasks.wrapped_generation import db_update_wrapped_job_status

@bot.slash_command(
  name="wrapped",
  description="Get your AGIMUS Wrapped for the year!",
)
async def wrapped(ctx:discord.ApplicationContext):
  await ctx.defer(ephemeral=True)
  user_discord_id = ctx.author.id
  user_member = await bot.current_guild.fetch_member(user_discord_id)
  wrapped_year = datetime.utcnow().year - 1

  xp_enabled = bool(await db_get_current_xp_enabled_value(user_discord_id))
  if not xp_enabled:
    await ctx.followup.send(
      embed=discord.Embed(
        title="XP Disabled!",
        description="You have opted out of the XP system so we cannot generate your AGIMUS Wrapped for you.\n\n"
                    "To re-enable please use `/settings`! Note that it may take some time for enough data to populate for these kinds of reports so you may be out of luck for last year!",
        color=discord.Color.red()
      ).set_footer(text="You can always opt-in or opt-out again later on at any time!")
    )
    return

  total_wrapped_xp = await db_get_wrapped_total_xp(user_discord_id)
  if not total_wrapped_xp:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"No {wrapped_year} Data!",
        description=f"Sorry, but we didn't record any XP Info for you from {wrapped_year} so we can't generate an AGIMUS Wrapped for you.",
        color=discord.Color.red()
      )
    )
    return

  wrapped_job = await db_get_user_wrapped_job(user_discord_id, wrapped_year)

  if wrapped_job:
    if wrapped_job['status'] == 'complete' and wrapped_job['video_path']:
      wrapped_embed = discord.Embed(
        title=f"{user_member.display_name}'s AGIMUS Wrapped {wrapped_year}",
        description=f"A look back at {wrapped_year}! Ahhh, memories. The fun, the laughter, the screams as I... wait what were we talking about again?",
        color=discord.Color.dark_red()
      )
      wrapped_embed.set_footer(
        text="Note: Best viewed in full screen!",
        icon_url="https://i.imgur.com/DTyVWL2.png"
      )
      await ctx.followup.send(
        embed=wrapped_embed,
        file=discord.File(wrapped_job['video_path'], filename=f"AGIMUS_Wrapped_{wrapped_year}.mp4")
      )
      return
    elif wrapped_job['status'] in ['pending', 'processing']:
      queue_position = await db_get_wrapped_queue_position(wrapped_job['job_id'], wrapped_year)
      queue_embed = discord.Embed(
        title=f"Your AGIMUS Wrapped {wrapped_year} is still processing.",
        description=f"You are at position No. {queue_position + 1}.",
        color=discord.Color.dark_red()
      )
      queue_embed.set_footer(
        text="I'm working as fast as my little robo-tentacles can!",
        icon_url="https://i.imgur.com/DTyVWL2.png"
      )
      await ctx.followup.send(embed=queue_embed)
      return
    elif wrapped_job['status'] == 'error':
      error_embed = discord.Embed(
        title=f"There was an error processing your Wrapped information.",
        description=f"Don't worry, we've been notified and VZ is on it (you can DM him too if you want though)! "
                     "You can queue a new one now and hope for the best, but may want to check with him first too!",
        color=discord.Color.red()
      )
      error_embed.set_footer(
        text="... fuck.",
        icon_url="https://i.imgur.com/DTyVWL2.png"
      )
      await ctx.followup.send(embed=error_embed)

      # Reset for the next attempt
      await db_update_wrapped_job_status(wrapped_job['job_id'], 'pending')
      return

  # No job found, add a new one
  await db_add_new_wrapped_job(user_discord_id, wrapped_year)
  add_embed = discord.Embed(
    title=f"Your AGIMUS Wrapped {wrapped_year} request has been added to the queue!",
    description="I will notify you once it's ready! 🫡",
    color=discord.Color.dark_red()
  )
  add_embed.set_footer(
    text="This should be interesting!",
    icon_url="https://i.imgur.com/DTyVWL2.png"
  )
  await ctx.followup.send(embed=add_embed)


async def db_get_wrapped_total_xp(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT SUM(amount) AS total_xp
        FROM xp_history
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row['total_xp'] if row['total_xp'] else 0


async def db_get_user_wrapped_job(user_discord_id, wrapped_year):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT id as job_id, status, video_path
        FROM wrapped_queue
          WHERE user_discord_id = %s AND wrapped_year = %s
          ORDER BY time_created DESC
        LIMIT 1
    '''
    vals = (user_discord_id, wrapped_year)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row

async def db_get_wrapped_queue_position(job_id, wrapped_year):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) as count
      FROM wrapped_queue
      WHERE status = 'pending' AND time_created < (
        SELECT time_created
        FROM wrapped_queue
        WHERE id = %s
      ) AND wrapped_year = %s
    '''
    vals = (job_id, wrapped_year)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row['count']

async def db_add_new_wrapped_job(user_discord_id, wrapped_year):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      INSERT INTO wrapped_queue (user_discord_id, status, wrapped_year)
      VALUES (%s, 'pending', %s)
    '''
    vals = (user_discord_id, wrapped_year)
    await query.execute(sql, vals)