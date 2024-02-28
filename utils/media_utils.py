# Media Util Helper Functions
from os.path import exists

import requests
from fuzzywuzzy import fuzz

from utils.string_utils import *

FUZZ_THRESHOLD = 72
def get_media_metadata(media_data, query):
  query = strip_punctuation(query)

  top_score = [0,None]

  for key in media_data:
    # If they nail a key directly, immediate return
    if (query == strip_punctuation(key)):
      return media_data.get(key)

    # Otherwise do fuzzy-match on drop description
    description = strip_punctuation(media_data.get(key)["description"])

    ratio = fuzz.ratio(description, query)
    pratio = fuzz.partial_ratio(description, query)
    score = round((ratio + pratio) / 2)
    # logger.info("key: {}, ratio: {}, pratio: {}, score: {}".format(key, ratio, pratio, score))
    if ((ratio > FUZZ_THRESHOLD) or (pratio > FUZZ_THRESHOLD)) and (score > top_score[0]):
      top_score = [score, key]

  if (top_score[0] != 0):
    return media_data.get(top_score[1])
  else:
    return False


def get_media_file(media_metadata):
  filename = media_metadata['file']
  if exists(filename):
    return filename
  else:
    url = media_metadata['url']
    headers = {
      'user-agent': 'curl/7.84.0',
      'accept': '*/*'
    }
    r = requests.get(url, headers=headers, allow_redirects=True)
    if not r.ok:
      raise Exception(f"Imgur request failed: {r.status_code} : {r.reason}")
    else:
      open(filename, 'wb').write(r.content)
    return filename
