#       __ ____              _                 _____                          _        _    _
#      / /|  _ \            | |               / ____|                        | |      | |  (_)
#     / / | |_) |  __ _   __| |  __ _   ___  | |      ___   _ __ ___   _ __  | |  ___ | |_  _   ___   _ __
#    / /  |  _ <  / _` | / _` | / _` | / _ \ | |     / _ \ | '_ ` _ \ | '_ \ | | / _ \| __|| | / _ \ | '_ \
#   / /   | |_) || (_| || (_| || (_| ||  __/ | |____| (_) || | | | | || |_) || ||  __/| |_ | || (_) || | | |
#  /_/    |____/  \__,_| \__,_| \__, | \___|  \_____|\___/ |_| |_| |_|| .__/ |_| \___| \__||_| \___/ |_| |_|
#                                __/ |                                | |
#                               |___/                                 |_|

from common import *

def execute_and_return(sql, user_id):

    # Execute query
    db = getDB()
    query = db.cursor(dictionary=True)
    query.execute(sql, (user_id,))
    rows = query.fetchall()
    query.close()
    db.close()

    # Deliver results
    results = [
        {
            "name": r['name'],
            "owned": r['ownedBadgeCount'],
            'total': r['totalBadgeCount'],
            'percentage': 0 if r['ownedBadgeCount'] == 0 else int((r['ownedBadgeCount'] / r['totalBadgeCount']) * 100)
        } for r in rows
    ]
    results = sorted(results, key=lambda r: r['percentage'], reverse=True)
    return results

def by_affiliation(user_id):
    sql = '''
      SELECT
          affiliation_name AS name,
          count(DISTINCT b_i.badge_filename) as totalBadgeCount,
          count(DISTINCT b.badge_filename) as ownedBadgeCount
      FROM badge_info AS b_i
      INNER JOIN badge_affiliation AS b_a
          ON b_i.badge_filename = b_a.badge_filename
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_a.affiliation_name;
    '''
    return execute_and_return(sql, user_id)

def by_franchise(user_id):
    sql = '''
      SELECT
          b_i.franchise AS name,
          count(DISTINCT b_i.badge_filename) as totalBadgeCount,
          count(DISTINCT b.badge_filename) as ownedBadgeCount
      FROM badge_info AS b_i
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_i.franchise;
    '''
    return execute_and_return(sql, user_id)

def by_time_period(user_id):
    sql = '''
      SELECT
          b_i.time_period AS name,
          count(DISTINCT b_i.badge_filename) as totalBadgeCount,
          count(DISTINCT b.badge_filename) as ownedBadgeCount
      FROM badge_info AS b_i
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_i.time_period;
    '''
    return execute_and_return(sql, user_id)

def by_type(user_id):
    sql = '''
      SELECT
          type_name AS name,
          count(DISTINCT b_i.badge_filename) as totalBadgeCount,
          count(DISTINCT b.badge_filename) as ownedBadgeCount
      FROM badge_info AS b_i
      INNER JOIN badge_type AS b_t
          ON b_i.badge_filename = b_t.badge_filename
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_t.type_name;
    '''
    return execute_and_return(sql, user_id)