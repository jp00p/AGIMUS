import aiohttp
import argparse
import asyncio
import json
import os
import urllib

async def download_badges(data_dir, badge_data):
  async with aiohttp.ClientSession() as session:
    badge_number = 1
    for badge in badge_data:
      print(f"Badge {badge_number} of {len(badge_data)}")
      image_url = badge['featuredImage']['asset']['url']
      image_name = strip_bullshit(badge['title']).replace(" ", "-")
      image_path = os.path.join(data_dir, f"{image_name}.png")
      async with session.get(image_url) as image_response:
        urllib.request.urlretrieve(image_url, image_path)
      badge_number = badge_number + 1

async def generate_sql(version, badge_data):
  with open(f"migrations/{version}.sql", "a") as migration_file:

    for badge in badge_data:
      badge_name = strip_bullshit(badge['title'])
      print(f">> Generating SQL for badge_name: {badge_name}")

      badge_filename = f"{badge_name.replace(' ', '-').replace(':', '_')}.png"

      badge_url = f"https://www.startrekdesignproject.com/symbols/{badge['slug']}"

      quadrant = badge.get('quadrant')

      reference = ""
      references = badge.get('references')
      if references:
        children = references[0]['children']
        if len(children) == 1:
          film_title = children[0]['text']
          reference = strip_bullshit(film_title)
        elif len(children) >= 2:
          episode_number = children[0]['text']
          episode_title = children[1]['text']
          reference = strip_bullshit(f"{episode_number}{episode_title}")

      time_period = badge.get('timePeriod')

      franchise = badge.get('franchise')

      affiliations = badge.get('affiliations')
      if not affiliations:
        affiliations = []

      types = badge.get('types')
      if not types:
        types = []

      universes = badge.get('universes')
      if not universes:
        universes = []


      # Insert basic info into badge_info
      sql = f'INSERT INTO badge_info (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference) VALUES ("{badge_name}", "{badge_filename}", "{badge_url}", "{quadrant}", "{time_period}", "{franchise}", "{reference}");\n'
      migration_file.write(sql)

      # Now create the badge_affiliation row(s)
      for a in affiliations:
        a = a.replace("'", "''").replace('"', '""')
        sql = f'INSERT IGNORE INTO badge_affiliation (badge_filename, affiliation_name) VALUES ("{badge_filename}", "{a}");\n'
        migration_file.write(sql)

      # Same for types
      for t in types:
        t = t.replace("'", "''").replace('"', '""')
        sql = f'INSERT IGNORE INTO badge_type (badge_filename, type_name) VALUES ("{badge_filename}", "{t}");\n'
        migration_file.write(sql)

      # Same for universes
      for u in universes:
        u = u.replace("'", "''").replace('"', '""')
        sql = f'INSERT IGNORE INTO badge_universe (badge_filename, universe_name) VALUES ("{badge_filename}", "{u}");\n'
        migration_file.write(sql)

  migration_file.close()

def strip_bullshit(text):
  text.replace(u"\u2019", "'").replace(u'\u201c', '"').replace(u'\u201d', '"').strip()
  return text

# DO THE THINGS
async def main():
  parser = argparse.ArgumentParser(description='Update badges for a project.')
  parser.add_argument('--dir', type=str, required=True, help='The path to the dir containing badges-metadata.json')
  parser.add_argument('--version', type=str, required=True, help='The version number to bump to (e.g. v2.10.0)')
  args = parser.parse_args()

  f = open(f"{args.dir}/badges-metadata.json")
  badge_data = json.load(f)
  f.close()

  print(f"Starting Badge Generation for {len(badge_data)} entries...")
  print("Downloading badge image files...")
  await download_badges(args.dir, badge_data)
  print("Generating SQL...")
  await generate_sql(args.version, badge_data)
  print("\n\nAll done. :D")


asyncio.run(main())