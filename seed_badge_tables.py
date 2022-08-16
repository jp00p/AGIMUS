from common import *

def seed_badge_tables():
  f = open("./data/badges-metadata.json")
  badges = json.load(f)
  f.close()

  db = getDB()
  for badge_key in badges.keys():
    badge_name = badge_key
    badge_filename = f"{badge_key.replace(' ', '_')}.png"

    badge_info = badges[badge_key]

    logger.info(f">> Inserting badge_name: {badge_name}")

    badge_url = badge_info['badge_url']
    quadrant = badge_info.get('quadrant')
    time_period = badge_info.get('time period'),
    franchise = badge_info.get('franchise'),
    reference = badge_info.get('reference')

    if type(time_period) is tuple:
      time_period = time_period[0]

    if type(franchise) is tuple:
      franchise = franchise[0]

    # Affiliations may be a list
    affiliations = badge_info.get('affiliations')
    affiliations_list = []
    if affiliations is not None:
      if (type(affiliations) is list):
        affiliations_list = affiliations
      elif (type(affiliations) is tuple):
        affiliations_list = [affiliations[0]]
      elif (type(affiliations) is str):
        affiliations_list = [affiliations]

    # Types may be a list
    types = badge_info.get('types')
    types_list = []
    if types is not None:
      if (type(types) is list):
        types_list = types
      elif (type(types) is tuple):
        types_list = [types[0]]
      elif (type(types) is str):
        types_list = [types]

    # Universes may be a list
    universes = badge_info.get('universes')
    universes_list = []
    if universes is not None:
      if (type(universes) is list):
        universes_list = universes
      elif (type(universes) is tuple):
        universes_list = [universes[0]]
      elif (type(universes) is str):
        universes_list = [universes]


    query = db.cursor(dictionary=True, buffered=True)
    # Insert basic info into badge_info
    sql = '''
      INSERT INTO badge_info
        (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    '''
    vals = (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference)
    query.execute(sql, vals)

    # Now get the id of the new badge_info row
    # sql = "SELECT id FROM badge_info WHERE badge_name = %s"
    # vals = (badge_name,)
    # query.execute(sql, vals)
    # badge_row = query.fetchone()
    # badge_info_row_id = badge_row['id']

    # Now create the badge_affiliation row(s)
    if affiliations_list is not None:
      for a in affiliations_list:
        sql = '''INSERT IGNORE INTO badge_affiliation
          (badge_filename, affiliation_name)
          VALUES (%s, %s)
        '''
        vals = (badge_filename, a)
        query.execute(sql, vals)

    # Same for types
    if types_list is not None:
      for t in types_list:
        sql = '''INSERT IGNORE INTO badge_type
          (badge_filename, type_name)
          VALUES (%s, %s)
        '''
        vals = (badge_filename, t)
        query.execute(sql, vals)

    # Same for universes
    if universes_list is not None:
      for u in universes_list:
        sql = '''INSERT IGNORE INTO badge_universe
          (badge_filename, universe_name)
          VALUES (%s, %s)
        '''
        vals = (badge_filename, u)
        query.execute(sql, vals)

    db.commit()
    query.close()

# Run
if __name__ == "__main__":
  seed_badge_tables()