import requests
from os.path import exists

from .common import *
from utils.check_channel_access import *

command_config = config["commands"]["clip"]
emojis = config["emojis"]

# Load JSON Data
f = open(command_config["data"])
clip_data = json.load(f)
f.close()

# clip() - Entrypoint for /clip command
# List the available clips by key and send to user as ephemeral
@slash.slash(
  name="clips",
  description="Retrieve the List of Clips.",
  guild_ids=config["guild_ids"]
)
async def clips(ctx:SlashContext):
  clips_list = "\n".join(clip_data)
  embed = discord.Embed(
    title="List of Clips",
    description=clips_list,
    color=discord.Color.blue()
  )
  try:
    await ctx.author.send(embed=embed)
    await ctx.reply(f"{emojis['tendi_smile_happy']} Sent you a DM with the full List of Clips!", hidden=True)
  except:
    await ctx.reply(embed=embed, hidden=True)


# clip() - Entrypoint for /clip command
# Parses a query, determines if it's allowed in the channel,
# and if allowed retrieve from metadata to do matching and
# then send the .mp4 file
@slash.slash(
  name="clip",
  description="Send a clip to the channel!",
  guild_ids=config["guild_ids"],
  options=[
    create_option(
      name="query",
      description="Which clip?",
      required=True,
      option_type=3
    ),
    create_option(
      name="private",
      description="Send clip to just yourself?",
      required=False,
      option_type=5,
    )
  ]
)
@check_channel_access(command_config)
async def clip(ctx:SlashContext, **kwargs):
  query = kwargs.get('query')
  private = kwargs.get('private')

  # Private drops are not on the timer
  clip_allowed = True
  if not private:
    clip_allowed = await check_timekeeper(ctx)

  if (clip_allowed):  
    q = query.lower().strip()
    clip_metadata = get_clip_metadata(q)

    if clip_metadata:
      try:
        filename = get_mp4(clip_metadata)
        await ctx.send(file=discord.File(filename), hidden=private)
        if not private:
          set_timekeeper(ctx)
      except BaseException as err:
        logger.info(f"ERROR LOADING CLIP: {err}")
        userid = command_config.get("error_contact_id")
        if userid:
          await ctx.send(f"{emojis['emh_doctor_omg_wtf_zoom']} Something has gone horribly awry, we may have a coolant leak. Contact Lieutenant Engineer <@{userid}>", hidden=True)  
    else:
      await ctx.send(f"{emojis['ezri_frown_sad']} Clip not found! To get a list of clips run: /clips", hidden=True)

# get_clip_metadata() - Logic to try to fuzzy-match user query to a clip
# query[required] - String
fuzz_threshold = 72
def get_clip_metadata(query):
  query = strip_punctuation(query)

  top_score = [0,None]

  for key in clip_data:
    # If they nail a key directly, immediate return
    if (query == strip_punctuation(key)):
      return clip_data.get(key)

    # Otherwise do fuzzy-match on drop description
    description = strip_punctuation(clip_data.get(key)["description"])

    ratio = fuzz.ratio(description, query)
    pratio = fuzz.partial_ratio(description, query)
    score = round((ratio + pratio) / 2)
    # logger.info("key: {}, ratio: {}, pratio: {}, score: {}".format(key, ratio, pratio, score))
    if ((ratio > fuzz_threshold) or (pratio > fuzz_threshold)) and (score > top_score[0]):
      top_score = [score, key]

  if (top_score[0] != 0):
    return clip_data.get(top_score[1])
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
        await ctx.reply(f"{emojis['ohno']} Someone in the channel has already posted a clip too recently. Please wait a minute before another clip!", hidden=True)
        last_record[1] = True
      return False

  # If a timekeeper entry for the channel hasn't been set yet, go ahead and allow
  return True


def set_timekeeper(ctx:SlashContext):
  current_channel = ctx.channel.id
  TIMEKEEPER[current_channel] = [ctx.created_at, False]


# Utility Functions
punct_regex = r'[' + string.punctuation + ']'
def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()

def get_mp4(clip_metadata):
  filename = clip_metadata['file']
  if exists(filename):
    return filename
  else:
    url = clip_metadata['url']
    r = requests.get(url, allow_redirects=True)
    open(filename, 'wb').write(r.content)
    return filename

