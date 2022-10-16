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

os.makedirs(destination_path)

current_badges = db_get_all_badge_info()

async def get_badges_and_metadata():
  async with aiohttp.ClientSession() as session:
    async with session.get(page_url) as response:
      html = await response.text()
      soup = BeautifulSoup(html, 'html.parser')
      cards = soup.select('.card')

      config_json = {}

      for card in cards:
        badge_name = card.select(".name")[0].text.strip().replace(".png", "")
        if badge_name in [b['badge_name'] for b in current_badges]:
          # The STDP symbols page by default lists the newest badges added to the project to the top
          # So if we hit a badge we already have then we can just exit 🤞
          print(f"\n\nWe already have {badge_name}, halting import.")
          break

        symbol_url = card.parent["href"]
        image = card.select(".thumbnail img")[0]
        image_url = image["data-srcset"].split(" ")[0]
        print(f"Downloading {image_url}...")
        image_name = image_url.split('/')[-1]
        config_json[badge_name] = { "badge_url" : symbol_url, "image_url" : image_url.replace("w_300", "w_1200"), "filename" : image_name }
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
            config_json[badge_name][cell_name] = cell_value
          reference_images = meta_soup.select(".post-content picture")
          ref_images_list = []
          for ref in reference_images:
            ref_img = ref.select("img")[0]
            if ref_img:
              ref_img_src = ref_img["data-srcset"].split(" ")[0]
              ref_images_list.append(ref_img_src)
          print(f"Adding reference images to {badge_name}: {ref_images_list}")
          config_json[badge_name]["reference_images"] = ref_images_list


  config_json = json.dumps(config_json, indent=2, sort_keys=True)
  try:
    with open(f"{destination_path}/badges-metadata.json", 'w') as f:
      f.write(config_json)
  except FileNotFoundError as e:
    print(f"Unable to write config file: {e}")


async def seed_badge_tables():
  f = open(f"{destination_path}/badges-metadata.json")
  badges = json.load(f)
  f.close()

  for badge_key in badges.keys():
    badge_name = badge_key
    badge_filename = f"{badge_key.replace(' ', '_').replace(':', '-').replace('/', '-')}.png"

    badge_info = badges[badge_key]

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


    with AgimusDB(dictionary=True) as query:
      # Check if badge already exists and if so skip
      sql = '''
        SELECT * FROM badge_info WHERE badge_filename = %s
      '''
      vals = (badge_filename,)
      query.execute(sql, vals)
      result = query.fetchone()
      if result is not None:
        continue

      logger.info(f">> Inserting badge_name: {badge_name}")

      # Insert basic info into badge_info
      sql = '''
        INSERT INTO badge_info
          (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference)
          VALUES (%s, %s, %s, %s, %s, %s, %s)
      '''
      vals = (badge_name, badge_filename, badge_url, quadrant, time_period, franchise, reference)
      query.execute(sql, vals)

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


async def copy_images_to_directory():
  for file in os.listdir(destination_path):
    if file.endswith(".png"):
      print(f"Moving {file}")
      shutil.copy(f"{destination_path}/{file}", f"./images/badges/{file}")

# DO THE THINGS
async def main():
  await get_badges_and_metadata()
  #await seed_badge_tables()
  await copy_images_to_directory()
  print("\n\nAll done. :D")

asyncio.run(main())