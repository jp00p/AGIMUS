from queries.trade import db_get_trade_offered_badge_instances, db_get_trade_requested_badge_instances

#   ___ ___         .__
#  /   |   \   ____ |  | ______   ___________  ______
# /    ~    \_/ __ \|  | \____ \_/ __ \_  __ \/  ___/
# \    Y    /\  ___/|  |_|  |_> >  ___/|  | \/\___ \
#  \___|_  /  \___  >____/   __/ \___  >__|  /____  >
#        \/       \/     |__|        \/           \/
async def does_trade_contain_badges(active_trade) -> bool:
  """
  Returns True if the trade has at least one badge in either the offered or requested list.
  """
  offered_instances = await db_get_trade_offered_badge_instances(active_trade)
  requested_instances = await db_get_trade_requested_badge_instances(active_trade)

  return bool(offered_instances or requested_instances)

async def get_offered_and_requested_badge_names(active_trade):
  offered_badges = await db_get_trade_offered_badge_instances(active_trade)
  offered_badge_names = "None"
  if offered_badges:
    offered_badge_names = "\n".join([f"* {b['badge_name']}" for b in offered_badges])

  requested_badges = await db_get_trade_requested_badge_instances(active_trade)
  requested_badge_names = "None"
  if requested_badges:
    requested_badge_names = "\n".join([f"* {b['badge_name']}" for b in requested_badges])

  return offered_badge_names, requested_badge_names