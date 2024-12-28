from common import *
from utils.settings_utils import db_get_current_xp_enabled_value

@bot.slash_command(
  name="wrapped",
  description="Get your AGIMUS Wrapped for the year!",
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
async def wrapped(ctx:discord.ApplicationContext, public:str):
  await ctx.defer(ephemeral=True)
  public = bool(public == "yes")

  user_discord_id = ctx.author.id
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

  wrapped_year = datetime.now().year - 1

  user_member = await bot.current_guild.fetch_member(user_discord_id)
  # # Presave User's Avatar if needed
  # avatar = user_member.display_avatar.with_size(128)
  # await avatar.save(f"./images/profiles/{user_discord_id}_a.png")

  # XP
  total_xp = await db_get_wrapped_total_xp(user_discord_id)
  top_xp_day = await db_get_wrapped_top_xp_day(user_discord_id)
  top_xp_month = await db_get_wrapped_top_xp_month(user_discord_id)
  if not top_xp_day:
    await ctx.followup.send(
      embed=discord.Embed(
        title=f"No {wrapped_year} Data!",
        description=f"Sorry, but we weren't able to retrieve any of your XP Info from {wrapped_year} so we can't generate an AGIMUS Wrapped for you!"
        color=discord.Color.red()
      )
    )
    return

  # Channels
  top_channels = await _generate_wrapped_top_channels(user_discord_id)

  # Words
  db_user = await get_user(ctx.author.id)
  if db_user.get("log_messages") != 1:
    top_words = await db_get_wrapped_top_words(user_discord_id)

  # Badges
  first_badge, last_badge = await db_get_wrapped_first_and_last_badges(user_discord_id)
  badges_collected = await db_get_wrapped_total_badges_collected(user_discord_id)
  rarest_badge = await db_get_wrapped_rarest_badge(user_discord_id)

  # Trades and Tongos
  total_trades = await db_get_wrapped_total_trades(user_discord_id)
  total_tongos = await db_get_wrapped_total_tongos(user_discord_id)

  wrapped_embed = discord.Embed(
    title=f"{user_member.display_name}'s AGIMUS Wrapped {wrapped_year}",
    description=f"Here's your {wrapped_year} Deets!",
    color=discord.Color.dark_red()
  )

  wrapped_embed.add_field(
    name="Total XP",
    value=total_xp
  )
  wrapped_embed.add_field(
    name="Top XP Day",
    value=f"{top_xp_day['day'].strftime("%B %d, %Y")} with {top_xp_day['amount']}xp"
  )
  wrapped_embed.add_field(
    name="Top XP Month",
    value=f"{top_xp_month['month']} with {top_xp_month['amount']}xp"
  )

  wrapped_embed.add_field(
    name="Top Channels",
    value="\n".join([f"* {c}" for c in top_channels])
  )

  if total_trades:
    wrapped_embed.add_field(
      name=f"Number of Trade Transactions",
      value=total_trades
    )

  if total_tongos:
    wrapped_embed.add_field(
      name=f"Number of Tongo Games",
      value=total_tongos
    )

  if top_words:
    wrapped_embed.add_field(
      name="Most Used Words",
      value="\n".join([f"* Used `{w['word']}` - {w['total']} times." for w in top_words])
    )

  if first_badge:
    wrapped_embed.add_field(
      name="First Badge Collected of the Year",
      value=f"{first_badge['badge_name']} on {first_badge['time_created'].strftime("%B %d, %Y")}"
    )

  if last_badge:
    wrapped_embed.add_field(
      name="Last Badge Collected of the Year",
      value=f"{last_badge['badge_name']} on {last_badge['time_created'].strftime("%B %d, %Y")}"
    )

  if badges_collected:
    wrapped_embed.add_field(
      name=f"{wrapped_year} Badges Collected",
      value=badges_collected
    )

  if rarest_badge:
    wrapped_embed.add_field(
      name="🌟 Rarest Badge 🌟",
      value=f"Your rarest badge from {wrapped_year} is **{rarest_badge['badge_name']}**, and was owned by only {rarest_badge['owner_count'] - 1} other users!",
    )

  await ctx.followup.send(embed=wrapped_embed)

async def _generate_wrapped_top_channels():
  data = db_get_wrapped_top_channels()
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
  top_5_filtered_data = filtered_data[:5]

  top_channels = [f"#{channels[int(d['channel_id'])]} - {d['total']}xp" for d in top_5_filtered_data]
  return top_channels

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
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
  return row['total_xp']

async def db_get_wrapped_top_xp_day(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT DATE(time_created) AS day, SUM(amount) AS total_xp
        FROM xp_history
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        GROUP BY DATE(time_created)
        ORDER BY total_xp DESC
        LIMIT 1;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    row = await query.fetchone()
  return row

async def db_get_wrapped_top_xp_month(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT MONTHNAME(time_created) AS month, SUM(amount) AS total_xp
        FROM xp_history
        WHERE user_discord_id = %s
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        GROUP BY MONTH(time_created)
        ORDER BY total_xp DESC
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
          AND reason = 'posted_message'
          AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
          AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        GROUP BY channel_id
        ORDER BY total DESC;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

async def db_get_wrapped_top_words(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT word, COUNT(*) AS 'total'
        FROM (
          SELECT LOWER(SUBSTRING_INDEX(SUBSTRING_INDEX(message_text, ' ', numbers.n), ' ', -1)) AS word
            FROM message_history
            JOIN (
              SELECT 1 AS n UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4 UNION ALL SELECT 5
              UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9 UNION ALL SELECT 10
            ) numbers ON CHAR_LENGTH(message_text) - CHAR_LENGTH(REPLACE(message_text, ' ', '')) >= numbers.n - 1
            WHERE user_discord_id = %s
              AND time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
              AND time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
        ) words
        WHERE word NOT IN (
          "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
          "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
          "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
          "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
          "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
          "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
          "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
          "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
          "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
          "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
          "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
          "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
          "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
          "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
          "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
        )
          AND word != ''
        GROUP BY word
        ORDER BY total DESC
        LIMIT 5;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    rows = await query.fetchall()
  return rows

async def db_get_wrapped_first_and_last_badges(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT
        b.badge_filename AS badge,
        bi.badge_name AS badge_name,
        b.time_created
      FROM badges b
      JOIN badge_info bi ON b.badge_filename = bi.badge_filename
      WHERE b.user_discord_id = %s
        AND b.time_created >= DATE(CONCAT(YEAR(CURDATE()) - 1, '-01-01'))
        AND b.time_created < DATE(CONCAT(YEAR(CURDATE()), '-01-01'))
      ORDER BY b.time_created ASC;
    '''
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    rows = await query.fetchall()

    if not rows:
      return None, None  # No badges earned

    first_badge = rows[0]
    last_badge = rows[-1]
    return first_badge, last_badge

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
