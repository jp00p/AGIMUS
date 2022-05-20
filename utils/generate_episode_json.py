import feedparser
import json
from dotenv import load_dotenv
import re
import sys, getopt
import os
import pprint

from datetime import timedelta
from dateutil import parser
from googleapiclient.discovery import build
from ratelimit import limits, sleep_and_retry

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CX = os.getenv('GOOGLE_CX')

def gather_filtered_rss_entries(series_prefix):
  tgg_rss_url = "https://feeds.simplecast.com/_mp2DeJd"
  feed = feedparser.parse(tgg_rss_url)

  filtered_entries = []
  for entry in feed['entries']:
    entry_title = entry['title']
    regex_result = re.search('(.+) \((\w+)\sS(\d+)E(\d+)\)', entry_title, re.IGNORECASE)
    if not regex_result:
      continue
    series_tag = regex_result.group(2)
    if series_tag != series_prefix:
      continue
    filtered_entries.append(entry)

  filtered_entries.reverse()

  return filtered_entries

def generate_recordset(series_prefix):
  recordset = {}
  pod_entries = gather_filtered_rss_entries(series_prefix)

  for entry in pod_entries:
    entry_title = entry['title']
    regex_result = re.search('(.+) \((\w+)\sS(\d+)E(\d+)\)', entry_title, re.IGNORECASE)
    pod_title = regex_result.group(1)
    series_tag = regex_result.group(2)
    season_number = regex_result.group(3).rjust(2, '0')
    episode_number = regex_result.group(4).rjust(2, '0')

    record_key = f"s{season_number}e{episode_number}"
    pprint.pprint(f"Working on \"{pod_title}\" ({series_tag} {record_key})")

    # Get Episode Title from Memory Alpha Google Search based on the SXXEXX Key
    memory_alpha_search = google_search(f"Memory Alpha {series_tag} {record_key}")
    memory_alpha_title = memory_alpha_search['pagemap']['metatags'][0]['og:title']
    episode_title = memory_alpha_title.replace(" (episode)", "")
    # pprint.pprint(episode_title)

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

    recordset[record_key] = {
      "title": episode_title,
      "memoryalpha": memory_alpha_title,
      "podcasts": [pod_entry]
    }

  return recordset

# NOTE: seconds here could probably be lowered a bit, but had run into
# Google giving a 429 "Too Many Requests per Minute" error a few times 
# prior to adding this
@sleep_and_retry
@limits(calls=1, period=timedelta(seconds=5).total_seconds())
def google_search(query):
  service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
  res = service.cse().list(q=query, cx=GOOGLE_CX).execute()
  return res['items'][0]


# Execute
def main(argv):
  series_prefix = ''
  output_file = ''
  try:
    opts, args = getopt.getopt(argv,"hp:o:",["series_prefix=","output="])
  except getopt.GetoptError:
    print("generate_episode_json.py -p <VOY|DS9|etc> -o <path to output file>")
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      print("generate_episode_json.py -p <VOY|DS9|etc> -o <path to output file>")
      sys.exit()
    elif opt in ("-p", "--series_prefix"):
      series_prefix = arg
    elif opt in ("-o", "--output"):
      output_file = arg
  
  # Perform parsing/filtering of RSS entries, Searches to gather Metadata
  try:
    recordset = generate_recordset(series_prefix)
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
