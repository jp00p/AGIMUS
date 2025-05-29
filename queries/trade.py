from common import *

from queries.common import BADGE_INSTANCE_COLUMNS
from utils.badge_instances import transfer_badge_instance

# queries.trade

# Offered
async def db_get_trade_offered_badge_instances(trade):
  trade_id = trade['id']
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}
      FROM badge_instances AS b
      JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
      LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
      LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
      JOIN trade_offered_badge_instances AS t_o ON t_o.badge_instance_id = b.id
      WHERE t_o.trade_id = %s
    '''
    await query.execute(sql, (trade_id,))
    return await query.fetchall()

async def db_add_offered_instance(trade_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO trade_offered_badge_instances (trade_id, badge_instance_id)
      VALUES (%s, %s)
    '''
    await query.execute(sql, (trade_id, badge_instance_id))

async def db_remove_offered_instance(trade_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM trade_offered_badge_instances
      WHERE trade_id = %s AND badge_instance_id = %s
    '''
    await query.execute(sql, (trade_id, badge_instance_id))

# Requested
async def db_get_trade_requested_badge_instances(trade):
  trade_id = trade['id']
  async with AgimusDB(dictionary=True) as query:
    sql = f'''
      SELECT {BADGE_INSTANCE_COLUMNS}
      FROM badge_instances AS b
      JOIN badge_info AS b_i ON b.badge_info_id = b_i.id
      LEFT JOIN badge_crystals AS c ON b.active_crystal_id = c.id
      LEFT JOIN crystal_instances AS ci ON c.crystal_instance_id = ci.id
      LEFT JOIN crystal_types AS t ON ci.crystal_type_id = t.id
      JOIN trade_requested_badge_instances AS t_r ON t_r.badge_instance_id = b.id
      WHERE t_r.trade_id = %s
    '''
    await query.execute(sql, (trade_id,))
    return await query.fetchall()

async def db_add_requested_instance(trade_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      INSERT INTO trade_requested_badge_instances (trade_id, badge_instance_id)
      VALUES (%s, %s)
    '''
    await query.execute(sql, (trade_id, badge_instance_id))

async def db_remove_requested_instance(trade_id, badge_instance_id):
  async with AgimusDB() as query:
    sql = '''
      DELETE FROM trade_requested_badge_instances
      WHERE trade_id = %s AND badge_instance_id = %s
    '''
    await query.execute(sql, (trade_id, badge_instance_id))


# Trade Lifecycle
async def db_get_active_requestor_trade(requestor_id):
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT * FROM badge_instance_trades
      WHERE requestor_id = %s AND (status = 'active' OR status = 'pending')
      LIMIT 1
    """
    await query.execute(sql, (requestor_id,))
    return await query.fetchone()


async def db_get_active_requestee_trades(requestee_id):
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT * FROM badge_instance_trades
      WHERE requestee_id = %s AND status = 'active'
    """
    await query.execute(sql, (requestee_id,))
    return await query.fetchall()


async def db_get_active_trade_between_requestor_and_requestee(requestor_id, requestee_id):
  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT * FROM badge_instance_trades
      WHERE requestor_id = %s AND requestee_id = %s AND status = 'active'
      LIMIT 1
    """
    await query.execute(sql, (requestor_id, requestee_id))
    return await query.fetchone()

async def db_initiate_trade(requestor_id: int, requestee_id: int, prestige_level:int) -> int:
  async with AgimusDB() as query:
    sql = """
      INSERT INTO badge_instance_trades (requestor_id, requestee_id, prestige_level, status)
      VALUES (%s, %s, %s, 'pending')
    """
    await query.execute(sql, (requestor_id, requestee_id, prestige_level))
    return query.lastrowid


async def db_activate_trade(active_trade):
  async with AgimusDB() as query:
    sql = "UPDATE badge_instance_trades SET status = 'active' WHERE id = %s"
    await query.execute(sql, (active_trade['id'],))


async def db_cancel_trade(trade):
  async with AgimusDB() as query:
    sql = "UPDATE badge_instance_trades SET status = 'canceled' WHERE id = %s"
    await query.execute(sql, (trade['id'],))


async def db_complete_trade(active_trade):
  async with AgimusDB() as query:
    sql = "UPDATE badge_instance_trades SET status = 'complete' WHERE id = %s"
    await query.execute(sql, (active_trade['id'],))


async def db_decline_trade(active_trade):
  async with AgimusDB() as query:
    sql = "UPDATE badge_instance_trades SET status = 'declined' WHERE id = %s"
    await query.execute(sql, (active_trade['id'],))

# Transfer
async def db_perform_badge_transfer(active_trade):
  trade_id = active_trade['id']
  requestor_id = active_trade['requestor_id']
  requestee_id = active_trade['requestee_id']

  # Get instance IDs from both sides of the trade
  async with AgimusDB(dictionary=True) as db:
    await db.execute("""
      SELECT badge_instance_id
      FROM trade_requested_badge_instances
      WHERE trade_id = %s
    """, (trade_id,))
    requested_ids = [row['badge_instance_id'] for row in await db.fetchall()]

    await db.execute("""
      SELECT badge_instance_id
      FROM trade_offered_badge_instances
      WHERE trade_id = %s
    """, (trade_id,))
    offered_ids = [row['badge_instance_id'] for row in await db.fetchall()]

  # Requestee to Requestor
  for instance_id in requested_ids:
    await transfer_badge_instance(instance_id, requestor_id, event_type='trade')

  # Requestor to Requestee
  for instance_id in offered_ids:
    await transfer_badge_instance(instance_id, requestee_id, event_type='trade')

# Related
async def db_get_related_badge_instance_trades(active_trade):
  trade_id = active_trade['id']
  requestor_id = active_trade['requestor_id']
  requestee_id = active_trade['requestee_id']

  async with AgimusDB(dictionary=True) as query:
    sql = """
      SELECT t.*
      FROM badge_instance_trades AS t

      LEFT JOIN trade_offered_badge_instances AS TOF ON t.id = TOF.trade_id
      LEFT JOIN trade_requested_badge_instances AS TRQ ON t.id = TRQ.trade_id

      INNER JOIN (
        SELECT badge_instance_id
        FROM trade_offered_badge_instances
        WHERE trade_id = %s
        UNION ALL
        SELECT badge_instance_id
        FROM trade_requested_badge_instances
        WHERE trade_id = %s
      ) AS active_badges ON active_badges.badge_instance_id IN (
        TOF.badge_instance_id, TRQ.badge_instance_id
      )

      WHERE t.id != %s
        AND t.status IN ('pending', 'active')
        AND (
          t.requestor_id IN (%s, %s)
          OR t.requestee_id IN (%s, %s)
        )

      GROUP BY t.id
    """
    await query.execute(sql, (
      trade_id, trade_id,
      trade_id,
      requestor_id, requestee_id,
      requestor_id, requestee_id
    ))
    return await query.fetchall()
