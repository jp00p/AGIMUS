import inspect
from datetime import datetime

from common import *

# Timekeeper Functions
# Prevent spamming a channel with too many drops in too short a period
#
# TIMEKEEPER is a dict of tuples for each channel which have the last timestamp,
# and a boolean indicating whether we've already told the channel to wait.
# If we've already sent a wait warning, we just ignore further requests until it has expired
TIMEKEEPER = {}
TIMEOUT = 15

async def check_timekeeper(ctx):
  command = inspect.stack()[1].function
  current_channel = ctx.channel.id
  
  command_record = TIMEKEEPER.get(command)
  if (command_record == None):
    # If a timekeeper entry for this command hasn't been set yet, go ahead and allow
    return True

  # Check if there's been a command within this channel in the last TIMEOUT seconds 
  last_record = command_record.get(current_channel)
  if (last_record != None):
    last_timestamp = last_record[0]
    diff = datetime.now() - last_timestamp
    seconds = diff.total_seconds()
    if (seconds > TIMEOUT):
      return True
    else:
      # Check if we've notified the channel if there's a timeout active
      have_notified = last_record[1]
      if (have_notified == False):
        last_record[1] = True
      return False

  # If a timekeeper entry for the channel hasn't been set yet, go ahead and allow
  return True


def set_timekeeper(ctx):
  command = inspect.stack()[1].function
  current_channel = ctx.channel.id
  if TIMEKEEPER.get(command) == None:
    TIMEKEEPER[command] = {}
  TIMEKEEPER[command][current_channel] = [datetime.now(), False]
