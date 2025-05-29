from common import *

from utils.thread_utils import to_thread

import io
import textwrap
from moviepy import *
from moviepy.video.fx.FadeIn import FadeIn
from moviepy.video.fx.FadeOut import FadeOut
from moviepy.video.fx.Resize import Resize


wrapped_year = datetime.utcnow().year - 1

def wrapped_generation_task(bot):
  async def wrapped_generation():
    enabled = config["tasks"]["wrapped_generation"]["enabled"]
    if not enabled:
      return

    job = await db_get_top_wrapped_job()
    if job:
      user = await bot.current_guild.fetch_member(int(job['user_discord_id']))
      maintainer_user = await bot.current_guild.fetch_member(int(config["tasks"]["wrapped_generation"]["maintainer_user_id"]))
      if not user:
        await db_delete_wrapped_job(int(job['job_id']))
        return

      await db_update_wrapped_job_status(job['job_id'], 'processing')
      try:
        video_path = await _generate_wrapped(job['user_discord_id'])
        await db_update_wrapped_job_status(job['job_id'], 'complete', video_path=video_path)
        wrapped_embed = discord.Embed(
          title=f"Your AGIMUS Wrapped {wrapped_year}",
          description=f"A look back at {wrapped_year}! Ahhh, memories. The fun, the laughter, the screams as I... wait what were we talking about again?",
          color=discord.Color.dark_red()
        )
        wrapped_embed.set_footer(
          text="Note: Best viewed in full screen!",
          icon_url="https://i.imgur.com/DTyVWL2.png"
        )
        await user.send(
          embed=wrapped_embed,
          file=discord.File(video_path, filename=f"AGIMUS_Wrapped_{wrapped_year}.mp4")
        )
        await maintainer_user.send(f"Successfully processed job for {user.display_name}")
      except Exception as e:
        stacktrace = traceback.format_exc()
        print(stacktrace)
        error_message = str(e)
        await maintainer_user.send(f"Error processing Wrapped video for {user.display_name}:")
        # Split the stacktrace into chunks of 1994 characters
        stacktrace_chunks = textwrap.wrap(stacktrace, width=1994, replace_whitespace=False)

        for chunk in stacktrace_chunks:
            await maintainer_user.send(f"```{chunk}```")
        await db_update_wrapped_job_status(job['job_id'], 'error', error_message=error_message)

  return {
    "task": wrapped_generation,
    "crontab": config["tasks"]["wrapped_generation"]["crontab"]
  }


async def _generate_wrapped(user_discord_id):
  user_member = await bot.current_guild.fetch_member(user_discord_id)
  # Presave User's Avatar
  avatar = user_member.display_avatar.with_size(256).with_static_format("png")
  avatar_path = f"./images/profiles/{user_discord_id}_a_256.png"
  await avatar.save(f"./images/profiles/{user_discord_id}_a_256.png")
  if not os.path.exists(avatar_path):
    raise FileNotFoundError(f"Avatar file not found at {avatar_path}")

  wrapped_data = {
    'top_channels': await _generate_wrapped_top_channels(user_discord_id),
    'total_xp': await db_get_wrapped_total_xp(user_discord_id),
    'total_messages': await db_get_wrapped_total_messages(user_discord_id),
    'total_reacts': await db_get_wrapped_total_reacts(user_discord_id),
    'top_xp_day': await db_get_wrapped_top_xp_day(user_discord_id),
    'badges_collected': await db_get_wrapped_total_badges_collected(user_discord_id),
    'total_trades': await db_get_wrapped_total_trades(user_discord_id),
    'total_tongos': await db_get_wrapped_total_tongos(user_discord_id),
    'rarest_badge': await db_get_wrapped_rarest_badge(user_discord_id),
  }

  video_path = await _generate_wrapped_mp4(user_discord_id, user_member.display_name, wrapped_data)
  return video_path

async def _generate_wrapped_top_channels(user_discord_id):
  data = await db_get_wrapped_top_channels(user_discord_id) or []
  # Filter out blocked channels
  channels = {v:k for k,v in config["channels"].items()}
  blocked_channel_names = [
    'friends-of-kareel'
    'lieutenants-lounge',
    'mclaughlin-group',
    'mo-pips-mo-problems',
    'code-47'
  ]
  blocked_channel_ids = [get_channel_id(c) for c in blocked_channel_names]
  blocked_channel_ids = [c for c in blocked_channel_ids if c is not None]

  filtered_data = [d for d in data if int(d['channel_id']) not in blocked_channel_ids and channels.get(int(d['channel_id'])) is not None]
  top_3_filtered_data = filtered_data[:3][::-1]

  top_channels = [{'channel_name': channels[int(d['channel_id'])], 'total': d['total']} for d in top_3_filtered_data]
  return top_channels

@to_thread
def _generate_wrapped_mp4(user_discord_id, user_display_name, wrapped_data):
  # Load the base video
  video = VideoFileClip(f"./videos/wrapped/agimus_wrapped_template_{wrapped_year}.mp4")
  video_width = video.size[0]
  video_width = video_width - 40 # Give us a little padding on each side

  # User Avatar and Name
  profile_name = TextClip(text=user_display_name, font_size=100, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  profile_name = profile_name.with_duration(4.375).with_start(5.1667).with_position(("center", 200))
  profile_name = profile_name.with_effects([FadeIn(duration=0.4167)])
  profile_name = profile_name.with_mask(profile_name.mask.with_effects([FadeOut(duration=0.8333)]))
  profile_name_size = profile_name.size[0]
  if profile_name_size > video_width:
    scale_factor = video_width / profile_name_size
    profile_name = profile_name.with_effects([Resize(scale_factor)])

  avatar_path = f"./images/profiles/{user_discord_id}_a_256.png"
  if not os.path.exists(avatar_path):
    raise FileNotFoundError(avatar_path)

  profile_image = ImageClip(avatar_path)
  profile_image = profile_image.with_effects([Resize(width=400), FadeIn(duration=0.4167)])
  profile_image = profile_image.with_duration(4.375).with_start(5.1667).with_position(("center", 350))
  profile_image = profile_image.with_effects([FadeOut(duration=0.8333)])

  # Channels
  first_channel_y = 450
  first_channel = TextClip(text=f"#{wrapped_data['top_channels'][0]['channel_name']}", font_size=50, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  first_channel = first_channel.with_duration(4.875).with_start(10.7917).with_position(("center", first_channel_y))
  first_channel = first_channel.with_mask(
    first_channel.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )
  first_channel_size = first_channel.size[0]
  if first_channel_size > video_width:
    scale_factor = video_width / first_channel_size
    first_channel = first_channel.with_effects([Resize(scale_factor)])

  first_channel_xp = TextClip(text=f"{wrapped_data['top_channels'][0]['total']:,}xp", font_size=40, color="white", stroke_color="black", stroke_width=1, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  first_channel_xp = first_channel_xp.with_duration(4.875).with_start(10.7917).with_position(
      lambda clip: ("center", first_channel.size[1] + first_channel_y - 20)
  )
  first_channel_xp = first_channel_xp.with_mask(
    first_channel_xp.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )

  second_channel_y = 600
  second_channel = TextClip(text=f"#{wrapped_data['top_channels'][1]['channel_name']}", font_size=50, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  second_channel = second_channel.with_duration(4.875).with_start(10.7917).with_position(("center", second_channel_y))
  second_channel = second_channel.with_mask(
    second_channel.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )
  second_channel_size = second_channel.size[0]
  if second_channel_size > video_width:
    scale_factor = video_width / second_channel_size
    second_channel = second_channel.with_effects([Resize(scale_factor)])

  second_channel_xp = TextClip(text=f"{wrapped_data['top_channels'][1]['total']:,}xp", font_size=40, color="white", stroke_color="black", stroke_width=1, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  second_channel_xp = second_channel_xp.with_duration(4.875).with_start(10.7917).with_position(
      lambda clip: ("center", second_channel.size[1] + second_channel_y - 20)
  )
  second_channel_xp = second_channel_xp.with_mask(
    second_channel_xp.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )

  final_channel_y = 420
  final_channel = TextClip(text=f"#{wrapped_data['top_channels'][2]['channel_name']}", font_size=60, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  final_channel = final_channel.with_duration(2.8333).with_start(16.2).with_position(("center", final_channel_y))
  final_channel = final_channel.with_mask(
    final_channel.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )
  final_channel_size = final_channel.size[0]
  if final_channel_size > video_width:
    scale_factor = video_width / final_channel_size
    final_channel = final_channel.with_effects([Resize(scale_factor)])

  final_channel_xp = TextClip(text=f"{wrapped_data['top_channels'][2]['total']:,}xp", font_size=40, color="white", stroke_color="black", stroke_width=1, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  final_channel_xp = final_channel_xp.with_duration(2.8333).with_start(16.2).with_position(
      lambda clip: ("center", final_channel.size[1] + final_channel_y - 20)
  )
  final_channel_xp = final_channel_xp.with_mask(
    final_channel_xp.mask.with_effects([
      FadeIn(duration=0.2917),
      FadeOut(duration=0.2917)
    ])
  )

  # XP / Message
  total_xp = TextClip(text=wrapped_data['total_xp'], font_size=140, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  total_xp = total_xp.with_duration(2.5417).with_start(20.625).with_position(("center", 570))
  total_xp = total_xp.with_mask(
    total_xp.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  total_xp_size = total_xp.size[0]
  if total_xp_size > video_width:
    scale_factor = video_width / total_xp_size
    total_xp = total_xp.with_effects([Resize(scale_factor)])


  total_messages = TextClip(text=wrapped_data['total_messages'], font_size=140, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  total_messages = total_messages.with_duration(2.5417).with_start(24.4583).with_position(("center", 520))
  total_messages = total_messages.with_mask(
    total_messages.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  total_messages_size = total_messages.size[0]
  if total_messages_size > video_width:
    scale_factor = video_width / total_messages_size
    total_messages = total_messages.with_effects([Resize(scale_factor)])


  total_reacts = TextClip(text=wrapped_data['total_reacts'], font_size=140, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  total_reacts = total_reacts.with_duration(2.5417).with_start(28.25).with_position(("center", 520))
  total_reacts = total_reacts.with_mask(
    total_reacts.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  total_reacts_size = total_reacts.size[0]
  if total_reacts_size > video_width:
    scale_factor = video_width / total_reacts_size
    total_reacts = total_reacts.with_effects([Resize(scale_factor)])


  top_xp_day_y = 550
  top_xp_day = TextClip(text=wrapped_data['top_xp_day']['day'], font_size=140, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  top_xp_day = top_xp_day.with_duration(2.5417).with_start(32.03).with_position(("center", top_xp_day_y))
  top_xp_day = top_xp_day.with_mask(
    top_xp_day.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  top_xp_day_size = top_xp_day.size[0]
  if top_xp_day_size > video_width:
    scale_factor = video_width / top_xp_day_size
    top_xp_day = top_xp_day.with_effects([Resize(scale_factor)])


  top_xp_day_total = TextClip(text=f"{wrapped_data['top_xp_day']['total']:,}xp", font_size=40, color="black", stroke_color="white", stroke_width=2, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  top_xp_day_total = top_xp_day_total.with_duration(2.5417).with_start(32.03).with_position(
    lambda clip: ("center", top_xp_day.size[1] + top_xp_day_y - 20)
  )
  top_xp_day_total = top_xp_day_total.with_mask(
    top_xp_day_total.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  top_xp_day_total_size = top_xp_day_total.size[0]
  if top_xp_day_total_size > video_width:
    scale_factor = video_width / top_xp_day_total_size
    top_xp_day_total = top_xp_day_total.with_effects([Resize(scale_factor)])


  # Badge Stats
  badges_collected = TextClip(text=f"{wrapped_data['badges_collected']}", font_size=200, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  badges_collected = badges_collected.with_duration(3.25).with_start(39.41).with_position(("center", 350))
  badges_collected = badges_collected.with_mask(
    badges_collected.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  badges_collected_size = badges_collected.size[0]
  if badges_collected_size > video_width:
    scale_factor = video_width / badges_collected_size
    badges_collected = badges_collected.with_effects([Resize(scale_factor)])

  total_trades = TextClip(text=f"{wrapped_data['total_trades']}", font_size=200, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  total_trades = total_trades.with_duration(2.5417).with_start(45.4583).with_position(("center", "center"))
  total_trades = total_trades.with_mask(
    total_trades.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  total_trades_size = total_trades.size[0]
  if total_trades_size > video_width:
    scale_factor = video_width / total_trades_size
    total_trades = total_trades.with_effects([Resize(scale_factor)])

  total_tongos = TextClip(text=f"{wrapped_data['total_tongos']}", font_size=200, color="black", stroke_color="white", stroke_width=3, font="fonts/DS9_Credits.ttf", margin=(20, 20))
  total_tongos = total_tongos.with_duration(2.5417).with_start(48.33).with_position(("center", "center"))
  total_tongos = total_tongos.with_mask(
    total_tongos.mask.with_effects([
      FadeOut(duration=0.625)
    ])
  )
  total_tongos_size = total_tongos.size[0]
  if total_tongos_size > video_width:
    scale_factor = video_width / total_tongos_size
    total_tongos = total_tongos.with_effects([Resize(scale_factor)])

  # Rarest Badge
  rarest_badge_filepath = f"./images/badges/{wrapped_data['rarest_badge']['badge_filename']}"
  if not os.path.exists(rarest_badge_filepath):
      raise FileNotFoundError(f"Rarest Badge file not found at {rarest_badge_filepath}")

  # Load the image from the filesystem
  badge_image = Image.open(rarest_badge_filepath)

  # Convert the image to RGBA
  badge_image = badge_image.convert("RGBA")

  # Create an ImageClip from the resulting numpy array here
  rarest_badge_image = ImageClip(np.array(badge_image))

  if rarest_badge_image:
    rarest_badge_image = rarest_badge_image.with_effects([Resize(width=500)])
    rarest_badge_image = rarest_badge_image.with_duration(3.25).with_start(54.375).with_position(("center", "center"))
    rarest_badge_image = rarest_badge_image.with_effects([FadeOut(duration=0.625)])

    rarest_badge_name = TextClip(text=f"{wrapped_data['rarest_badge']['badge_name']}", font_size=50, color="white", stroke_color="black", stroke_width=2, font="fonts/DS9_Credits.ttf", margin=(20, 20))
    rarest_badge_name = rarest_badge_name.with_duration(3.25).with_start(54.375).with_position(("center", 200))
    rarest_badge_name = rarest_badge_name.with_mask(
      rarest_badge_name.mask.with_effects([
        FadeOut(duration=0.625)
      ])
    )
    rarest_badge_name_size = rarest_badge_name.size[0]
    if rarest_badge_name_size > video_width:
      scale_factor = video_width / rarest_badge_name_size
      rarest_badge_name = rarest_badge_name.with_effects([Resize(scale_factor)])

    owner_count = wrapped_data['rarest_badge']['owner_count']
    rarest_badge_text = f"Only owned by {owner_count} users!"
    if owner_count == 1:
      rarest_badge_text = f"You were the sole owner!"
    rarest_badge_owner_rarity = TextClip(text=rarest_badge_text, font_size=50, color="white", stroke_color="black", stroke_width=2, font="fonts/DS9_Credits.ttf", margin=(20, 20))
    rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_duration(3.25).with_start(54.375).with_position(("center", 700))
    rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_mask(
      rarest_badge_owner_rarity.mask.with_effects([
        FadeOut(duration=0.625)
      ])
    )
    rarest_badge_owner_rarity_size = rarest_badge_owner_rarity.size[0]
    if rarest_badge_owner_rarity_size > video_width:
      scale_factor = video_width / rarest_badge_owner_rarity_size
      rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_effects([Resize(scale_factor)])
  else:
    rarest_badge_image = ImageClip("./images/badges/Friends_Of_DeSoto.png", transparent=False)
    rarest_badge_image = rarest_badge_image.with_effects([Resize(width=500)])
    rarest_badge_image = rarest_badge_image.with_duration(3.25).with_start(54.375).with_position(("center", "center"))
    rarest_badge_image = rarest_badge_image.with_effects([FadeOut(duration=0.625)])

    rarest_badge_name = TextClip(text="Whoops, you didn't collect a rare badge this year!", font_size=50, color="white", stroke_color="black", stroke_width=2, font="fonts/DS9_Credits.ttf", margin=(20, 20))
    rarest_badge_name = rarest_badge_name.with_duration(3.25).with_start(54.375).with_position(("center", 200))
    rarest_badge_name = rarest_badge_name.with_mask(
      rarest_badge_name.mask.with_effects([
        FadeOut(duration=0.625)
      ])
    )
    rarest_badge_name_size = rarest_badge_name.size[0]
    if rarest_badge_name_size > video_width:
      scale_factor = video_width / rarest_badge_name_size
      rarest_badge_name = rarest_badge_name.with_effects([Resize(scale_factor)])

    rarest_badge_owner_rarity = TextClip(text="But make no mistake, you're a valued FoD!", font_size=50, color="white", stroke_color="black", stroke_width=2, font="fonts/DS9_Credits.ttf", margin=(20, 20))
    rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_duration(3.25).with_start(54.375).with_position(("center", 700))
    rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_mask(
      rarest_badge_owner_rarity.mask.with_effects([
        FadeOut(duration=0.625)
      ])
    )
    rarest_badge_owner_rarity_size = rarest_badge_owner_rarity.size[0]
    if rarest_badge_owner_rarity_size > video_width:
      scale_factor = video_width / rarest_badge_owner_rarity_size
      rarest_badge_owner_rarity = rarest_badge_owner_rarity.with_effects([Resize(scale_factor)])

  # Combine all elements
  final = CompositeVideoClip([
    video,
    profile_image, profile_name,
    first_channel, first_channel_xp, second_channel, second_channel_xp, final_channel, final_channel_xp,
    total_xp, total_messages, total_reacts, top_xp_day, top_xp_day_total,
    badges_collected, total_trades, total_tongos,
    rarest_badge_image, rarest_badge_name, rarest_badge_owner_rarity
  ])

  # Write the final video
  video_path = f"./videos/wrapped/{wrapped_year}/{user_discord_id}.mp4"
  final.write_videofile(video_path, codec="libx264", fps=24)
  return video_path

async def _get_image_bytes(file_path) -> bytes:
    """Read a badge image from the filesystem and return its bytes."""

    # Use aiofiles to read the file asynchronously
    async with aiofiles.open(file_path, mode="rb") as f:
        image_bytes = await f.read()

    return image_bytes

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

# Task Queue Queries
async def db_get_top_wrapped_job():
  async with AgimusDB(dictionary=True) as db:
    sql = '''
      SELECT id as job_id, user_discord_id
      FROM wrapped_queue
      WHERE status = 'pending'
        AND wrapped_year = %s
      ORDER BY time_created ASC
      LIMIT 1
    '''
    vals = (wrapped_year,)
    await db.execute(sql, vals)
    job = await db.fetchone()
  return job

async def db_update_wrapped_job_status(job_id, status, video_path=None, error_message=None):
  async with AgimusDB(dictionary=True) as db:
    if status == 'complete':
      sql = '''
        UPDATE wrapped_queue
        SET status = %s, video_path = %s, error = NULL
        WHERE id = %s AND wrapped_year = %s
      '''
      vals = (status, video_path, job_id, wrapped_year)
    elif status == 'error':
      sql = '''
        UPDATE wrapped_queue
        SET status = %s, error = %s
        WHERE id = %s
      '''
      vals = (status, error_message, job_id)
    else:
      sql = '''
        UPDATE wrapped_queue
        SET status = %s
        WHERE id = %s
      '''
      vals = (status, job_id)
    await db.execute(sql, vals)

async def db_delete_wrapped_job(job_id):
  async with AgimusDB(dictionary=True) as db:
    sql = "DELETE FROM wrapped_queue WHERE id = %s"
    await db.execute(sql, (job_id,))

## Stats Queries
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
  return f"{row['total_xp']:,}"

async def db_get_wrapped_total_messages(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS total_messages
      FROM xp_history
      WHERE user_discord_id = %s
        AND reason = 'posted_message'
        AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return f"{row['total_messages']:,}"

async def db_get_wrapped_total_reacts(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS total_reactions
      FROM xp_history
      WHERE user_discord_id = %s
        AND reason = 'added_reaction'
        AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return f"{row['total_reactions']:,}"

async def db_get_wrapped_top_xp_day(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT CONCAT(
               MONTHNAME(MIN(time_created)), ' ',
               DAY(MIN(time_created)),
               CASE
                 WHEN DAY(MIN(time_created)) IN (11, 12, 13) THEN 'th'
                 WHEN DAY(MIN(time_created)) %% 10 = 1 THEN 'st'
                 WHEN DAY(MIN(time_created)) %% 10 = 2 THEN 'nd'
                 WHEN DAY(MIN(time_created)) %% 10 = 3 THEN 'rd'
                 ELSE 'th'
               END
             ) AS day,
             SUM(amount) AS total
        FROM xp_history
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        GROUP BY DATE(time_created)
        ORDER BY total DESC
        LIMIT 1;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row

async def db_get_wrapped_top_channels(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT channel_id, COUNT(*) AS 'total'
        FROM xp_history
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        GROUP BY channel_id
        ORDER BY total DESC;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

async def db_get_wrapped_total_badges_collected(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS total
      FROM badges
      WHERE user_discord_id = %s
        AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
    return row['total'] or 0

async def db_get_wrapped_total_trades(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(*) AS total
      FROM trades
      WHERE (requestor_id = %s OR requestee_id = %s)
        AND status = 'complete'
        AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id, user_discord_id)
    await query.execute(sql, vals)
    row = await query.fetchone()
    return row['total'] or 0

async def db_get_wrapped_total_tongos(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT COUNT(DISTINCT tongo_id) AS total
      FROM tongo_players
      WHERE user_discord_id = %s
        AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'));
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
    return row['total'] or 0

async def db_get_wrapped_rarest_badge(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.badge_name, b.badge_filename, COUNT(DISTINCT b.user_discord_id) AS owner_count
      FROM badges AS b
      JOIN badge_info AS b_i ON b.badge_filename = b_i.badge_filename
      WHERE b.badge_filename IN (
        SELECT badge_filename
        FROM badges
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
      )
        AND b.time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND b.time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
      GROUP BY b_i.badge_name, b.badge_filename
      ORDER BY owner_count ASC, b_i.badge_name ASC
      LIMIT 1;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    rarest_badge = await query.fetchone()
    return rarest_badge
