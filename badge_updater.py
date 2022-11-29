import aiohttp
from bs4 import BeautifulSoup
import urllib
import shutil

from common import *
from utils.badge_utils import db_get_all_badge_info

# save all images from a webpage to disk
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
page_url = "https://startrekdesignproject.com/symbols/"
destination_path = f"./badge_updates/{timestamp}/"

# Determine the next minor version we should use for our migration script
# stream = os.popen()
with os.popen('make version') as current:
  current_version = current.readlines()[1].strip()
logger.info(f"Current version: {current_version}")
with os.popen(f'semver bump minor {current_version}') as new:
  new_version = new.read().strip()
logger.info(f"New version: v{new_version}")

# Load the current badge data for doing comparisons
current_badges = db_get_all_badge_info()

# Create directory to store badge files/json
os.makedirs(destination_path)

async def get_badges_and_metadata():
  async with aiohttp.ClientSession() as session:
    async with session.get(page_url) as response:
      html = await response.text()
      soup = BeautifulSoup(html, 'html.parser')
      cards = soup.select('.card')

      badge_data = {}

      for card in cards:
        badge_name = card.select(".name")[0].text.strip().replace(".png", "")
        if badge_name in [b['badge_name'] for b in current_badges]:
          # The STDP symbols page by default lists the newest badges added to the project to the top
          # So if we hit a badge we already have then we can just exit 🤞
          print(f"\n\nWe already have {badge_name}, end of new badges found.")
          break

        symbol_url = card.parent["href"]
        image = card.select(".thumbnail img")[0]
        image_url = image["data-srcset"].split(" ")[0]
        print(f"Downloading {image_url}...")
        image_name = image_url.split('/')[-1]
        badge_data[badge_name] = { "badge_url" : symbol_url, "image_url" : image_url.replace("w_300", "w_1200"), "filename" : image_name }
        image_path = os.path.join(destination_path, image_name)
        async with session.get(image_url) as image_response:
          urllib.request.urlretrieve(image_url, image_path)
        print(f'Saved {badge_name}')

        async with session.get(symbol_url) as meta_response:
          print(f'Opening url: {symbol_url}')
          meta_html = await meta_response.text()
          meta_soup = BeautifulSoup(meta_html, 'html.parser')
          meta_cells = meta_soup.select(".third")
          for cell in meta_cells:
            cell_name = cell.get_text().strip().replace(":", "").lower()
            celldata = cell.find_next_sibling("div")
            if celldata:
              cell_value = celldata.get_text().replace(":", "").replace(u"\u2019", "'").replace(u'\u201c', '"').replace(u'\u201d', '"').strip()
              if "\n\n" in cell_value:
                cell_value = cell_value.split("\n\n")
            print(f"Adding {cell_name}:{cell_value} to {badge_name}")
            badge_data[badge_name][cell_name] = cell_value
          reference_images = meta_soup.select(".post-content picture")
          ref_images_list = []
          for ref in reference_images:
            ref_img = ref.select("img")[0]
            if ref_img:
              ref_img_src = ref_img["data-srcset"].split(" ")[0]
              ref_images_list.append(ref_img_src)
          print(f"Adding reference images to {badge_name}: {ref_images_list}")
          badge_data[badge_name]["reference_images"] = ref_images_list

  if not len(badge_data):
    return False

  config_json = json.dumps(badge_data, indent=2, sort_keys=True)
  try:
    # Write metadata file
    with open(f"{destination_path}/badges-metadata.json", 'w') as f:
      f.write(config_json)
  except FileNotFoundError as e:
    print(f"Unable to write config file: {e}")

  return True


async def generate_sql_file():
  f = open(f"{destination_path}/badges-metadata.json")
  badges = json.load(f)
  f.close()

  with open(f"migrations/v{new_version}.sql", "a") as migration_file:

    for badge_key in badges.keys():
      badge_name = badge_key.replace('"', '""')

      badge_info = badges[badge_key]

      badge_filename = badge_info['filename']
      badge_url = badge_info['badge_url'].replace('"', '""')
      quadrant = badge_info.get('quadrant').replace('"', '""')

      reference = badge_info.get('reference').replace('"', '""')

      time_period = badge_info.get('time period')
      if type(time_period) is tuple:
        time_period = time_period[0].replace('"', '""')

      franchise = badge_info.get('franchise')
      if type(franchise) is tuple:
        franchise = franchise[0].replace('"', '""')

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

      # Check if badge already exists and if so skip
      with AgimusDB(dictionary=True) as query:
        sql = '''
          SELECT * FROM badge_info WHERE badge_filename = %s
        '''
        vals = (badge_filename,)
        query.execute(sql, vals)
        result = query.fetchone()
        if result is not None:
          logger.info(f">> {badge_name} already exists in database, skipping...")
          continue

      # Badge name is not present, go ahead and generate SQL
      logger.info(f">> Generating SQL for badge_name: {badge_name}")

      # Insert basic info into badge_info
      sql = f'INSERT INTO badge_info (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference) VALUES ("{badge_name}", "{badge_filename}", "{badge_url}", "{quadrant}", "{time_period}", "{franchise}", "{reference}");\n'
      migration_file.write(sql)

      # Now create the badge_affiliation row(s)
      if affiliations_list is not None:
        for a in affiliations_list:
          a = a.replace("'", "''").replace('"', '""')
          sql = f'INSERT IGNORE INTO badge_affiliation (badge_filename, affiliation_name) VALUES ("{badge_filename}", "{a}");\n'
          migration_file.write(sql)

      # Same for types
      if types_list is not None:
        for t in types_list:
          t = t.replace("'", "''").replace('"', '""')
          sql = f'INSERT IGNORE INTO badge_type (badge_filename, type_name) VALUES ("{badge_filename}", "{t}");\n'
          migration_file.write(sql)

      # Same for universes
      if universes_list is not None:
        for u in universes_list:
          u = u.replace("'", "''").replace('"', '""')
          sql = f'INSERT IGNORE INTO badge_universe (badge_filename, universe_name) VALUES ("{badge_filename}", "{u}");\n'
          migration_file.write(sql)

  migration_file.close()


async def copy_images_to_directory():
  for file in os.listdir(destination_path):
    if file.endswith(".png"):
      print(f"Moving {file}")
      shutil.copy(f"{destination_path}/{file}", f"./images/badges/{file}")

# DO THE THINGS
async def main():
  new_badges_found = await get_badges_and_metadata()
  if new_badges_found:
    await generate_sql_file()
    await copy_images_to_directory()
    print("\n\nAll done. :D")
  else:
    print("\n\nNo new badges found. Exiting.")

asyncio.run(main())