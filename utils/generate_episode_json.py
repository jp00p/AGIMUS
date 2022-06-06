import feedparser
import json
from dotenv import load_dotenv
import asyncio
import re
import sys, getopt
import os
import pprint
import tmdbsimple as tmdb

from datetime import timedelta
from dateutil import parser
from googleapiclient.discovery import build
from ratelimit import limits, sleep_and_retry

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CX = os.getenv('GOOGLE_CX')
tmdb.API_KEY = os.getenv('TMDB_KEY')
TMDB_IMG_PATH = "https://image.tmdb.org/t/p/original"

shows = {
  "tng": {
    "tvdb":655,
    "title": "Star Trek: The Next Generation",
    "trek": True,
    "animated": False,
    "imdb": "tt0092455"
  },
  "ds9": {
    "tvdb":580,
    "title": "Star Trek: Deep Space Nine",
    "trek": True,
    "animated": False,
    "imdb": ""
  },
  "voy": {
    "tvdb":1855,
    "title": "Star Trek: Voyager",
    "trek": True,
    "animated": False,
    "imdb": "",
    "episodes": [],
  }
}

# To Do: The Greatest Discovery
# TGD Podcast feed: https://feeds.simplecast.com/d1rbEtgZ
# This uses a different naming convention for episodes, so we need to filter
# ,
#   "enterprise": {
#     "tvdb":314,
#     "title": "Star Trek: Enterprise",
#     "trek": True,
#     "animated": False,
#     "imdb": ""
#   },
#   "tos": {
#     "tvdb":253,
#     "title": "Star Trek: The Original Series",
#     "trek": True,
#     "animated": False,
#     "imdb": ""
#   },
#   "lowerdecks": {
#     "tvdb":85948,
#     "title": "Star Trek: Lower Decks",
#     "trek": True,
#     "animated": True,
#     "imdb": ""
#   },
#   "disco": {
#     "tvdb":67198,
#     "title": "Star Trek: Discovery",
#     "trek": True,
#     "animated": False,
#     "imdb": ""
#   },
#   "picard": {
#     "tvdb":85949,
#     "title": "Star Trek: Picard",
#     "trek": True,
#     "animated": False,
#     "imdb": ""
#   },
#   "tas": {
#     "tvdb":1992,
#     "title": "Star Trek: The Animated Series",
#     "trek": True,
#     "animated": True,
#     "imdb": ""
#   }


tgg_rss_url = "https://feeds.simplecast.com/_mp2DeJd"
feed = feedparser.parse(tgg_rss_url)



def gather_filtered_rss_entries(series_prefix, tseason, tepisode):
  # pprint.pprint(f"series_prefix: {series_prefix} S{tseason}E{tepisode}")
  filtered_entries = []
  for entry in feed['entries']:
    entry_title = entry['title']
    regex_result = re.search('(.+) \((\w+)\sS(\d+)E(\d+)\)', entry_title, re.IGNORECASE)
    if not regex_result:
      continue
    series_tag = regex_result.group(2).upper()
    # hackerman
    if series_tag == "VOYAGER":
        series_tag = "VOY"
    this_season = regex_result.group(3)
    this_episode = regex_result.group(4)
    if series_tag != series_prefix:
      continue
    # pprint.pprint(f"Series Tag: {series_tag} S{this_season}E{this_episode} : S{tseason}E{tepisode}")
    if int(tseason) == int(this_season) and int(tepisode) == int(this_episode):
      # print("Entry Title: " + entry_title)
      filtered_entries.append(entry)
    else:
      continue

  filtered_entries.reverse()
  # pprint.pprint(filtered_entries)
  return filtered_entries[0]



def generate_index(recordset):
  indecies = {}
  tep = 0
  for episode in recordset["episodes"]:
    tkey = "s" + episode["season"] + "e" + episode["episode"]
    indecies[tkey] = tep
    tep += 1
  return indecies



def generate_recordset(series_prefix, recordset):
  keymap = generate_index(recordset)
  # recordset = {}
  episodes = []
  track_episode = 0
  track_season = 0
  track = 0
  max = 10000
  failed = 0
  moveon = 0
  tgg = {}
  for track_season in range(1,100):
    for track_episode in range(1,100):
      failed = 0
      if moveon > 1:
        break
      this_episode = {}
      tseason = str(track_season).zfill(2)
      tepisode = str(track_episode).zfill(2)
      tgg_key = f"s{tseason}e{tepisode}"
      print(f"{tgg_key} ----------------------------------------")
      if tgg_key in keymap.keys():
        print("Metadata already saved for: " + tgg_key)
        # pprint.pprint(recordset["episodes"][keymap[tgg_key]])
        this_episode = recordset["episodes"][keymap[tgg_key]]
        moveon = 0
      else:
        print(f"Metadata not found {tgg_key} - Attempting to gather...")
        tmdb_episode = tmdb.TV_Episodes(shows[series_prefix.lower()]["tvdb"],track_season,track_episode)
        this_episode["airdate"] = ""
        this_episode["description"] = ""
        this_episode["memoryalpha"] = ""
        this_episode["podcasts"] = []
        try:
          episode_details = tmdb_episode.info()
          # pprint.pprint(f"key: {tgg_key}")
          # pprint.pprint(f'Title[{episode_details["id"]}][s{tseason}e{tepisode}]: {episode_details["name"]}')
          # pprint.pprint(f">>> Info: {episode_details}")
          this_episode["airdate"] = episode_details["air_date"].replace("-", ".")
          this_episode["description"] = episode_details["overview"]
          this_episode["title"] = episode_details["name"]
          this_episode["tvdb"] = episode_details["id"]
          this_episode["season"] = tseason
          this_episode["episode"] = tepisode
          episode_external_ids = tmdb_episode.external_ids()
          this_episode["imdb"]=episode_external_ids["imdb_id"]
          if len(episode_external_ids) > 0:
            moveon = 0
          episode_stills = tmdb_episode.images()
          tstills = []
          for s in episode_stills["stills"]:
            tstills.append(TMDB_IMG_PATH + s["file_path"])
          this_episode["stills"] = tstills

        except:
          failed = failed + 1
          pprint.pprint(f"This episode does not exist[{failed}][{moveon}]: s{tseason}e{tepisode}")
          if failed > 0:
            moveon = moveon + 1
            break


      if "memoryalpha" not in this_episode.keys() or this_episode["memoryalpha"] == "":
        print("Checking MemoryAlpha information...")
        # Get Episode Title from Memory Alpha Google Search based on the SXXEXX Key
        memory_alpha_search = google_search(f"Memory Alpha {series_prefix.upper()} {tgg_key}")
        memory_alpha_title = memory_alpha_search['pagemap']['metatags'][0]['og:title']
        episode_title = memory_alpha_title.replace(" ", "_")
        pprint.pprint(f"Episode title: {episode_title}")
        this_episode["memoryalpha"] = episode_title

      try:
        entry = gather_filtered_rss_entries(series_prefix, track_season, track_episode)
      except:
        # failed = failed + 1
        pprint.pprint(f"This podcast episode does not exist[{failed}][{moveon}]: s{track_season}e{track_episode}")
        if this_episode:
          episodes.append(this_episode)
        continue
      entry_title = entry['title']
      pprint.pprint(f"Pod title: {entry_title}")
      regex_result = re.search('(.+) \((\w+)\sS(\d+)E(\d+)\)', entry_title, re.IGNORECASE)
      pod_title = regex_result.group(1)
      series_tag = regex_result.group(2)
      season_number = regex_result.group(3).rjust(2, '0')
      episode_number = regex_result.group(4).rjust(2, '0')



      if "podcasts" not in this_episode.keys() or len(this_episode["podcasts"]) == 0:
        print("Checking MaximumFun information...")
        # Get MaxFun link from Google Search on Pod Title
        tgg_search = google_search(f"The Greatest Generation MaximumFun {pod_title}")
        pod_link = tgg_search['link']

        pod_entry = {
          "title": "The Greatest Generation",
          "order": int(entry['itunes_episode']),
          "airdate": parser.parse(entry['published']).strftime('%Y.%m.%d'),
          "episode": pod_title,
          "link": pod_link
        }
        this_episode["podcasts"].append(pod_entry)
      print("This Episode: " + str(this_episode))
      episodes.append(this_episode)
  recordset["episodes"] = episodes
  return recordset

# NOTE: seconds here could probably be lowered a bit, but had run into
# Google giving a 429 "Too Many Requests per Minute" error a few times 
# prior to adding this
@sleep_and_retry
@limits(calls=1, period=timedelta(seconds=5).total_seconds())
def google_search(query):
  service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
  res = service.cse().list(q=query, cx=GOOGLE_CX).execute()
  # pprint.pprint(res['items'][0])
  return res['items'][0]


# Execute
def main(argv):
  series_prefix = ''
  output_file = ''
  try:
    opts, args = getopt.getopt(argv,"hp:o:",["series_prefix=","output="])
  except getopt.GetoptError:
    print("generate_episode_json.py -p <TNG|DS9|VOY|DISCO|PICARD|LOWERDECKS> -o <path to output file>")
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      print("generate_episode_json.py -p <TNG|DS9|VOY|DISCO|PICARD|LOWERDECKS> -o <path to output file>")
      sys.exit()
    elif opt in ("-p", "--series_prefix"):
      series_prefix = arg
    elif opt in ("-o", "--output"):
      output_file = arg
  


  try:
    f = open(output_file, 'r')
    tgg = json.load(f)
    f.close()
  except BaseException as err:
    tgg = shows[series_prefix.lower()]

  # Perform parsing/filtering of RSS entries, Searches to gather Metadata
  try:
    recordset = generate_recordset(series_prefix, tgg)
  except BaseException as err:
    print("Error gathering metadata.")
    print(err)
    sys.exit(2)

  # Write to json file
  try:
    with open(output_file, "w") as fp:
      json.dump(recordset, fp, indent=2) 
  except BaseException as err:
    print(f"Error writing to file: {output_file}")
    print(err)
    sys.exit(2)

if __name__ == "__main__":
   main(sys.argv[1:])