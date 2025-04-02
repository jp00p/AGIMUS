from common import *

async def does_trade_contain_badges(active_trade):
  offered_badges = await db_get_trade_offered_badges(active_trade)
  requested_badges = await db_get_trade_requested_badges(active_trade)

  if len(offered_badges) > 0 or len(requested_badges) > 0:
    return True
  else:
    return False

async def get_offered_and_requested_badge_names(active_trade):
  offered_badges = await db_get_trade_offered_badges(active_trade)
  offered_badge_names = "None"
  if offered_badges:
    offered_badge_names = "\n".join([f"* {b['badge_name']}" for b in offered_badges])

  requested_badges = await db_get_trade_requested_badges(active_trade)
  requested_badge_names = "None"
  if requested_badges:
    requested_badge_names = "\n".join([f"* {b['badge_name']}" for b in requested_badges])

  return offered_badge_names, requested_badge_names

async def db_get_trade_requested_badges(active_trade):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*
      FROM badge_info as b_i
        JOIN trade_requested AS t_r
        ON t_r.trade_id = %s AND t_r.badge_filename = b_i.badge_filename
    '''
    vals = (active_trade_id,)
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades

async def db_get_trade_offered_badges(active_trade):
  active_trade_id = active_trade["id"]
  async with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT b_i.*
      FROM badge_info as b_i
        JOIN trade_offered AS t_o
        ON t_o.trade_id = %s AND t_o.badge_filename = b_i.badge_filename
    '''
    vals = (active_trade_id,)
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades

async def db_cancel_trade(trade):
  trade_id = trade['id']
  async with AgimusDB() as query:
    sql = "UPDATE trades SET status = 'canceled' WHERE id = %s"
    vals = (trade_id,)
    await query.execute(sql, vals)

async def db_get_related_badge_trades(active_trade):
  active_trade_id = active_trade["id"]

  async with AgimusDB(dictionary=True) as query:
    # All credit for this query to Danma! Praise be!!!
    sql = '''
      SELECT t.*

      FROM trades as t
      LEFT JOIN trade_offered `to` ON t.id = to.trade_id
      LEFT JOIN trade_requested `tr` ON t.id = tr.trade_id

      INNER JOIN (
          SELECT trade_id, requestor_id, requestee_id, badge_filename
          FROM trade_requested
          INNER JOIN trades ON trade_requested.trade_id = trades.id AND trades.id = %s
          UNION ALL
          SELECT trade_id, requestor_id, requestee_id, badge_filename
          FROM trade_offered
          INNER JOIN trades ON trade_offered.trade_id = trades.id AND trades.id = %s
      ) as activeTrade ON 1

      -- not the active trade
      WHERE t.id != activeTrade.trade_id

      -- pending or active
      AND t.status IN ('pending','active')

      -- involves one or more of the users involved in the active trade
      AND (t.requestor_id IN (activeTrade.requestor_id, activeTrade.requestee_id) OR t.requestee_id IN (activeTrade.requestor_id, activeTrade.requestee_id))

      -- involves one or more of the badges involved in the active trade
      AND (to.badge_filename = activeTrade.badge_filename OR tr.badge_filename = activeTrade.badge_filename)
      GROUP BY t.id
    '''
    vals = (active_trade_id, active_trade_id)
    await query.execute(sql, vals)
    trades = await query.fetchall()
  return trades
