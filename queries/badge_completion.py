#       __ ____              _                 _____                          _        _    _
#      / /|  _ \            | |               / ____|                        | |      | |  (_)
#     / / | |_) |  __ _   __| |  __ _   ___  | |      ___   _ __ ___   _ __  | |  ___ | |_  _   ___   _ __
#    / /  |  _ <  / _` | / _` | / _` | / _ \ | |     / _ \ | '_ ` _ \ | '_ \ | | / _ \| __|| | / _ \ | '_ \
#   / /   | |_) || (_| || (_| || (_| ||  __/ | |____| (_) || | | | | || |_) || ||  __/| |_ | || (_) || | | |
#  /_/    |____/  \__,_| \__,_| \__, | \___|  \_____|\___/ |_| |_| |_|| .__/ |_| \___| \__||_| \___/ |_| |_|
#                                __/ |                                | |
#                               |___/                                 |_|

import math
from common import *

def execute_and_return(sql, user_id):

    # Execute query
    with AgimusDB(dictionary=True) as query:
      query.execute(sql, (user_id,))
      rows = query.fetchall()

    # Deliver results
    results = [
        {
            "name": r['name'],
            "owned": r['owned'],
            'total': r['total'],
            'percentage': math.ceil(r['percentage'])
        } for r in rows
    ]
    return results

def by_affiliation(user_id):
    sql = '''
      SELECT
          affiliation_name AS name,
          count(DISTINCT b_i.badge_filename) as total,
          count(DISTINCT b.badge_filename) as owned,
          count(DISTINCT b.badge_filename) * 100 / count(DISTINCT b_i.badge_filename) as percentage
      FROM badge_info AS b_i
      INNER JOIN badge_affiliation AS b_a
          ON b_i.badge_filename = b_a.badge_filename
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_a.affiliation_name
      ORDER BY percentage DESC, affiliation_name
    '''
    return execute_and_return(sql, user_id)

def by_franchise(user_id):
    sql = '''
      SELECT
          b_i.franchise AS name,
          count(DISTINCT b_i.badge_filename) as total,
          count(DISTINCT b.badge_filename) as owned,
          count(DISTINCT b.badge_filename) * 100 / count(DISTINCT b_i.badge_filename) as percentage
      FROM badge_info AS b_i
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_i.franchise
      ORDER BY percentage DESC, b_i.franchise
    '''
    return execute_and_return(sql, user_id)

def by_time_period(user_id):
    sql = '''
      SELECT
          b_i.time_period AS name,
          count(DISTINCT b_i.badge_filename) as total,
          count(DISTINCT b.badge_filename) as owned,
          count(DISTINCT b.badge_filename) * 100 / count(DISTINCT b_i.badge_filename) as percentage
      FROM badge_info AS b_i
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_i.time_period
      ORDER BY percentage DESC, b_i.time_period
    '''
    return execute_and_return(sql, user_id)

def by_type(user_id):
    sql = '''
      SELECT
          type_name AS name,
          count(DISTINCT b_i.badge_filename) as total,
          count(DISTINCT b.badge_filename) as owned,
          count(DISTINCT b.badge_filename) * 100 / count(DISTINCT b_i.badge_filename) as percentage
      FROM badge_info AS b_i
      INNER JOIN badge_type AS b_t
          ON b_i.badge_filename = b_t.badge_filename
      LEFT JOIN badges AS b
          ON b_i.badge_filename = b.badge_filename
          AND b.user_discord_id = %s
      GROUP BY b_t.type_name
      ORDER BY percentage DESC, type_name
    '''
    return execute_and_return(sql, user_id)