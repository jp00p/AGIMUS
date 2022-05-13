from .common import *

f = open(config["commands"]["drop"]["data"])
drop_data = json.load(f)
f.close()

fuzz_threshold = 72

# drop() - Entrypoint for !drop command
# message[required]: discord.Message
# This function is the main entrypoint of the !drop command
#
# We try to match up the query from the user to a drop from our list
# and then send it back to the channel
async def drop(message:discord.Message):
  query = message.content.lower().replace("!drop", "").strip()
  drop_metadata = get_drop_metadata(query)

  if drop_metadata:
    await message.channel.send(file=discord.File(drop_metadata.get("file")))
  else:
    await message.channel.send("I'm sorry, I didn't find a drop that matched your prompt...")

# get_drop_metadata() - Logic to try to fuzzy-match user query to a drop
# query[required] - String
def get_drop_metadata(query):
  top_score = [0,None]

  for key in drop_data:
    description = drop_data.get(key)["description"].lower()
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
