from .common import *

f = open(config["commands"]["drop"]["data"])
drop_data = json.load(f)
f.close()

fuzz_threshold = 72
punct_regex = r'[' + string.punctuation + ']'

# drop() - Entrypoint for !drop command
# message[required]: discord.Message
# This function is the main entrypoint of the !drop command
#
# We try to match up the query from the user to a drop from our list
# and then send it back to the channel
async def drop(message:discord.Message):
  query = message.content.lower().replace("!drop", "").strip()

  if (query == ''):
    await message.channel.send("<a:riker_think_hmm:881981594271899718> You'll need to include a term to search by! To get a list of drops run: !drops")
    return

  drop_allowed = check_timekeeper(message)
  if (drop_allowed):
    drop_metadata = get_drop_metadata(query)

    if drop_metadata:
      await message.channel.send(file=discord.File(drop_metadata.get("file")))
      set_timekeeper(message)
    else:
      await message.channel.send("<:ezri_frown_sad:757762138176749608> Drop not found! To get a list of drops run: !drops")
  else:
    await message.reply("<:ohno:930365904657723402> Someone in the channel has already dropped too recently. Please wait a minute before another drop!")

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

# drops() - Entrypoint for !drops command
# message[required]: discord.Message
# This function simply returns a list to the channel of the drops that are available
async def drops(message:discord.Message):
  drops_list = "\n".join(drop_data)
  embed = discord.Embed(
    title="List of Drops",
    description=drops_list,
    color=discord.Color.blue()
  )
  await message.author.send(embed=embed)
  await message.reply("Sent you a direct DM with the full List of Drops!")


# Timekeeper Functions
# Prevent spamming a channel with too many drops in too short a period
TIMEKEEPER = {}
TIMEOUT = 45

def check_timekeeper(message:discord.Message):
  current_channel = message.channel.id

  # Check if there's been a drop within this channel in the last TIMEOUT seconds
  current_timestamp = TIMEKEEPER.get(current_channel)
  if (current_timestamp != None):
    diff = message.created_at - current_timestamp
    seconds = diff.total_seconds()
    if (seconds > TIMEOUT):
      return True
    else:
      return False
  # If a timekeeper entry for the channel hasn't been set yet, go ahead and allow
  return True

def set_timekeeper(message:discord.Message):
  current_channel = message.channel.id
  TIMEKEEPER[current_channel] = message.created_at


# Utility Functions
def strip_punctuation(string):
  return re.sub(punct_regex, '', string).lower().strip()

