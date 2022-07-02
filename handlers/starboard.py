from commands.common import *

react_threshold = 5
blocked_channels = get_channel_ids_list(config["handlers"]["starboard"]["blocked_channels"])
boards = get_channel_ids_list(config["handlers"]["starboard"]["boards"].keys())

async def handle_starboard_reactions(reaction:discord.Reaction, user:discord.User):
  
  # don't watch blocked channels, or the actual starboard channels
  if reaction.message.channel in blocked_channels or reaction.message.channel in boards or reaction.message.author.bot:
    return

  # logger.info("REACTION:")
  # logger.info(reaction.emoji)

  #if reaction.count >= react_threshold:
  #pass

# ensure custom AGIMUS emoji is present and ready

# watch reactions on all messages

# if reactions reach threshold, post the message in the approparite starboard channel

# add special reaction to original message and new message

# reply to the original post letting them know it has gone into the starboard