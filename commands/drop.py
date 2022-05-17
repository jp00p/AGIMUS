import requests
from os.path import exists

from .common import *

# Load Drop Data
f = open(config["commands"]["drop"]["data"])
drop_data = json.load(f)
f.close()

fuzz_threshold = 72
punct_regex = r'[' + string.punctuation + ']'

# drop() - Entrypoint for !drop command
# This now just informs the channel that they can use the slash command instead
async def drop(message:discord.Message):
  await message.channel.send("No need for !drop any longer, try using the slash command `/drop`! <:nechayev_point_yes:840252104056766515>")

# slash_drops() - Entrypoint for /drops command
# List the available drops by key and send to user as ephemeral
@slash.slash(
  name="drops",
  description="Retrieve the List of Drops.",
  guild_ids=config["guild_ids"]
)
async def slash_drops(ctx:SlashContext):
  drops_list = "\n".join(drop_data)
  embed = discord.Embed(
    title="List of Drops",
    description=drops_list,
    color=discord.Color.blue()
  )
  try:
    await ctx.author.send(embed=embed)
    await ctx.reply("<:tendi_smile_happy:757768236069814283> Sent you a DM with the full List of Drops!", hidden=True)
  except:
    await ctx.reply(embed=embed, hidden=True)


# slash_drop() - Entrypoint for /drops command
# Parses a query, determines if it's allowed in the channel,
# and if allowed retrieve from metadata to do matching and
# then send the .mp4 file
@slash.slash(
  name="drop",
  description="Send a drop to the channel!",
  guild_ids=config["guild_ids"],
  options=[
    create_option(
      name="query",
      description="Which drop?",
      required=True,
      option_type=3
    )
  ]
)
async def slash_drop(ctx:SlashContext, query:str):
  # Verify that we're allowed to perform drops in this channel
  allowed_channels = config["commands"]["drop"]["channels"]
  if not (ctx.channel.id in allowed_channels):
    await ctx.send("<:ezri_frown_sad:757762138176749608> Sorry! Drops are not allowed in this channel. Please try elsewhere.", hidden=True)
    return


  q = query.lower().strip()

  drop_allowed = await check_timekeeper(ctx)
  if (drop_allowed):
    drop_metadata = get_drop_metadata(q)

    if drop_metadata:
      filename = get_mp4(drop_metadata)
      await ctx.send(file=discord.File(filename))
      set_timekeeper(ctx)
    else:
      await ctx.send("<:ezri_frown_sad:757762138176749608> Drop not found! To get a list of drops run: /drops", hidden=True)

# get_drop_metadata() - Logic to try to fuzzy-match user query to a drop
# query[required] - String
def get_drop_metadata(query):
  query = strip_punctuation(query)

  top_score = [0,None]

  for key in drop_data:
    # If they nail a key directly, immediate return
    if (query == strip_punctuation(key)):
      return drop_data.get(key)

    # Otherwise do fuzzy-match on drop description
    description = strip_punctuation(drop_data.get(key)["description"])

    ratio = fuzz.ratio(description, query)
    pratio = fuzz.partial_ratio(description, query)
    score = round((ratio + pratio) / 2)
    # logger.info("key: {}, ratio: {}, pratio: {}, score: {}".format(key, ratio, pratio, score))
    if ((ratio > fuzz_threshold) or (pratio > fuzz_threshold)) and (score > top_score[0]):
      top_score = [score, key]

  if (top_score[0] != 0):
    return drop_data.get(top_score[1])
  else:
    return False

# Timekeeper Functions
# Prevent spamming a channel with too many drops in too short a period
#
# TIMEKEEPER is a dict of tuples for each channel which have the last timestamp,
# and a boolean indicating whether we've already told the channel to wait.
# If we've already sent a wait warning, we just ignore further requests until it has expired
TIMEKEEPER = {}
TIMEOUT = 15

async def check_timekeeper(ctx:SlashContext):
  current_channel = ctx.channel.id

  # Check if there's been a drop within this channel in the last TIMEOUT seconds
  last_record = TIMEKEEPER.get(current_channel)
  if (last_record != None):
    last_timestamp = last_record[0]
    diff = ctx.created_at - last_timestamp
    seconds = diff.total_seconds()
    if (seconds > TIMEOUT):
      return True
    else:
      # Check if we've notified the channel if there's a timeout active
      have_notified = last_record[1]
      if (have_notified == False):
        await ctx.reply("<:ohno:930365904657723402> Someone in the channel has already dropped too recently. Please wait a minute before another drop!", hidden=True)
        last_record[1] = True
      return False

  # If a timekeeper entry for the channel hasn't been set yet, go ahead and allow
  return True


def set_timekeeper(ctx:SlashContext):
  current_channel = ctx.channel.id
  TIMEKEEPER[current_channel] = [ctx.created_at, False]


# Utility Functions
def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()

def get_mp4(drop_metadata):
  filename = drop_metadata['file']
  if exists(filename):
    return filename
  else:
    url = drop_metadata['url']
    r = requests.get(url, allow_redirects=True)
    open(filename, 'wb').write(r.content)
    return filename

