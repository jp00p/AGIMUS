from common import *

from queries.badge_info import *
from utils.string_utils import strip_bullshit

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_selections(ctx:discord.AutocompleteContext):
  category = ctx.options["category"]

  selections = []

  if category == 'affiliation':
    selections = await db_get_all_affiliations()
  elif category == 'franchise':
    selections = await db_get_all_franchises()
  elif category == 'time_period':
    selections = await db_get_all_time_periods()
  elif category == 'type':
    selections = await db_get_all_types()

  return [result for result in selections if strip_bullshit(ctx.value.lower()) in strip_bullshit(result.lower())]

