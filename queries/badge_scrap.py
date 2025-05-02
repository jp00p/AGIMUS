# from common import *

# async def db_get_scrap_last_timestamp(user_discord_id):
#   async with AgimusDB(dictionary=True) as query:
#     sql = "SELECT time_created FROM badge_scraps WHERE user_discord_id = %s ORDER BY time_created DESC"
#     vals = (user_discord_id, )
#     await query.execute(sql, vals)
#     row = await query.fetchone()

#   timestamp = None
#   if row is not None:
#     timestamp = row['time_created']

#   return timestamp

# async def db_perform_badge_scrap(user_discord_id, badge_to_add, badges_to_scrap):
#   badge_filename_to_add = badge_to_add['badge_filename']
#   badge_filenames_to_scrap = [b['badge_filename'] for b in badges_to_scrap]

#   async with AgimusDB(dictionary=True) as query:

#     # Create scrap record
#     sql = '''
#       INSERT INTO badge_scraps (user_discord_id, badge_filename)
#         VALUES (%s, %s)
#     '''
#     vals = (user_discord_id, badge_filename_to_add)
#     await query.execute(sql, vals)

#     # Associate badges scrapped with scrap record
#     # Create scrap record
#     sql = '''
#       INSERT INTO badge_scrapped (scrap_id, badge_filename)
#         VALUES
#         (%s, %s),
#         (%s, %s),
#         (%s, %s)
#     '''
#     vals = (
#       query.lastrowid, badge_filenames_to_scrap[0],
#       query.lastrowid, badge_filenames_to_scrap[1],
#       query.lastrowid, badge_filenames_to_scrap[2],
#     )
#     await query.execute(sql, vals)

#     # Give user new badge
#     sql = '''
#       INSERT INTO badges (user_discord_id, badge_filename)
#         VALUES (%s, %s)
#     '''
#     vals = (user_discord_id, badge_filename_to_add)
#     await query.execute(sql, vals)

#     # Remove scraped badges from user's inventory'
#     sql = '''
#       DELETE FROM badges
#         WHERE (user_discord_id, badge_filename)
#         IN (
#           (%s,%s),
#           (%s,%s),
#           (%s,%s)
#         )
#     '''
#     vals = (
#       user_discord_id, badge_filenames_to_scrap[0],
#       user_discord_id, badge_filenames_to_scrap[1],
#       user_discord_id, badge_filenames_to_scrap[2],
#     )
#     await query.execute(sql, vals)
