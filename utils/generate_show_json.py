"""
Script for creating the .json files for the shows.  Since they need to be updated about once a week, you’ll
run this on a pretty regular basis.

Usage:
    generate_show_json.py <show> [<filename>] [options]

Arguments:
    <show>        One of tos|tas|tng|ds9|voy|enterprise|disco|picard|lowerdecks|prodigy|snw
    <filename>    The name of the file to generate.  Default: /data/episodes/<show>.json

Options:
    -h --help             Show this message.
    
    -s --season <list>    A comma separated list of seasons to update.  Default: All possible seasons.
    -e --episode <list>   A comma separated list of episodes to update.  Used with -s.  Default: All possible episodes.
    
    -p --podcast          Update the podcast information.  Useful for old shows that have only just been covered.
    -d --details          Update the episode details from TVDB.  You will need to update your .env file and put in
                          TMDB_KEY.  Details on getting one at https://developer.themoviedb.org/docs/getting-started
    -m --memory-alpha     Update the link to the episode in Memory Alpha.
    
                          If -p, -d, and -m are not specified, then all of them will be updated.
                          
Examples:
    The pod has just covered Spock's Brain, and the episode is already in the file
    generate_show_json.py tos -s 3 -e 6 -p
    
    Season 3 of LDS has finished, and so it’s time to add all of them
    generate_show_json.py lowerdecks -s 3
    
    The first two episodes of SNW season three dropped in the same week
    generate_show_json.py snw -s 3 -e 1,2
"""
import json
import os.path
import re
from typing import List, Optional

import docopt

import feedparser

# Important config options that will need to be updated as new shows are added
import requests
import tmdbsimple
from dateutil import parser
from dotenv import load_dotenv

all_shows = {
  "tng": {
    "tmdb": 655,
    "title": "Star Trek: The Next Generation",
    "trek": True,
    "animated": False,
    "pod": "tgg"
  },
  "ds9": {
    "tmdb": 580,
    "title": "Star Trek: Deep Space Nine",
    "trek": True,
    "animated": False,
    "pod": "tgg"
  },
  "voy": {
    "tmdb": 1855,
    "title": "Star Trek: Voyager",
    "trek": True,
    "animated": False,
    "pod": "tgg"
  },
  "enterprise": {
    "tmdb": 314,
    "title": "Star Trek: Enterprise",
    "trek": True,
    "animated": False,
  },
  "tos": {
    "tmdb": 253,
    "title": "Star Trek: The Original Series",
    "trek": True,
    "animated": False,
    "pod": "tgt"
  },
  "lowerdecks": {
    "tmdb": 85948,
    "title": "Star Trek: Lower Decks",
    "trek": True,
    "animated": True,
    "pod": "tgt",
    "pod_name": "Lower Decks"
  },
  "disco": {
    "tmdb": 67198,
    "title": "Star Trek: Discovery",
    "trek": True,
    "animated": False,
    "pod": "tgt",
    "pod_name": "Discovery"
  },
  "picard": {
    "tmdb": 85949,
    "title": "Star Trek: Picard",
    "trek": True,
    "animated": False,
    "pod": "tgt"
  },
  "tas": {
    "tmdb": 1992,
    "title": "Star Trek: The Animated Series",
    "trek": True,
    "animated": True,
    "pod": "tgt"
  },
  "prodigy": {
    "tmdb": 106393,
    "title": "Star Trek: Prodigy",
    "trek": True,
    "animated": True,
    "pod": "tgt"
  },
  "snw": {
    "tmdb": 103516,
    "title": "Star Trek: Strange New Worlds",
    "trek": True,
    "animated": False,
    "pod": "tgt"
  },
}

podcasts = {
  'tgg': {
    "name": "The Greatest Generation",
    "url": "http://feeds.feedburner.com/TheGreatestGeneration"
  },
  'tgt': {
    "name": "Greatest Trek",
    "url": "http://feeds.feedburner.com/GreatestDiscovery"
  }
}


class ShowGenerator:
  """
  Class for building a .json file to be used with other commands around the bot.
  """
  def __init__(self, show: str, filename: str = None,
               seasons: Optional[List[int]] = None, episodes: Optional[List[int]] = None,
               update_details=True, update_podcast=True, update_memory_alpha=True):
    self.show = show
    self.show_settings = all_shows[self.show]
    
    self.filename = filename or os.path.join(os.path.dirname(__file__), f"../data/episodes/{self.show}.json")
    
    self.seasons = seasons or range(1, 8)  # So far, no show has gone beyond 7 seasons
    
    self.episodes_to_update = episodes or range(1, 30)  # Remember when seasons were 20+ episodes?
    
    self.run_tmdb = update_details
    self.run_pod = update_podcast
    self.run_memory_alpha = update_memory_alpha
    
    if self.run_tmdb:
      self.get_tmdb_api()
    
    self.episode_details = []
    self.episode_map = {}
    self.podcast_episodes = {}
    self.podcast_name = None
  
  @staticmethod
  def clean_and_validate_args(cli_args: dict) -> Optional[dict]:
    """
    Takes the command line arguments from docopt and turns them into a dict that can be used as **kwargs for a new
    instance. If there are any errors, print them out and return None
    """
    args = {
      'show': cli_args['<show>'],
      'filename': cli_args['<filename>'],
    }
    
    valid = True
    if cli_args['<show>'] not in all_shows:
      print(f"{cli_args['<show>']} is not one of {all_shows.keys()}")
      valid = False
    
    try:
      if cli_args['--season']:
        args['seasons'] = [int(s) for s in cli_args['--season'].split(',')]
    except ValueError:
      print(f"-s should be a number or a list of numbers with commas inbetween.  Got “{cli_args['--season']}”")
      valid = False
    
    try:
      if cli_args['--episode']:
        args['episodes'] = [int(s) for s in cli_args['--episode'].split(',')]
    except ValueError:
      print(f"-e should be a number or a list of numbers with commas inbetween.  Got “{cli_args['--episode']}”")
      valid = False

    if cli_args['--details'] or cli_args['--podcast'] or cli_args['--memory-alpha']:
      args.update({
        'update_details': cli_args['--details'],
        'update_podcast': cli_args['--podcast'],
        'update_memory_alpha': cli_args['--memory-alpha']
      })
      
    if valid:
      return args
    else:
      return None

  def get_tmdb_api(self):
    """
    Set the TMDB API key, or disable the function if not available.
    """
    load_dotenv()
    tmdbsimple.API_KEY = os.getenv('TMDB_KEY')
    if not tmdbsimple.API_KEY:
      print("You need to setup a TMDB API key at https://www.themoviedb.org/settings/api and put it in your .env "
            "file.\nYou will not be able to add new shows or update details about existing ones until you do.")
      self.run_tmdb = False

  def run(self):
    """
    Actually update the JSON file
    """
    self.load_current_file()
    if self.run_pod:
      self.load_feed()
    
    for season in self.seasons:
      for episode in self.episodes_to_update:
        print(f"- Checking for {self.show} S{season:02}E{episode:02}")
        
        details = self.get_current_details(season, episode)
        if self.run_tmdb:
          details = self.set_tmdb_details(details, season, episode)
        
        if not details:
          # There are no more episodes in this season
          break
        
        if self.run_memory_alpha:
          self.set_memory_alpha(details)
        
        if self.run_pod:
          self.set_podcast(details, season, episode)
    
    self.save_current_file()
  
  def load_current_file(self):
    """
    Load the current file for the episodes
    """
    if not os.path.isfile(self.filename):
      return
    
    with open(self.filename, 'r') as f:
      json_data = json.load(f)
    print(f"Found existing {self.filename}")
    self.episode_details = json_data['episodes']
    for index, details in enumerate(self.episode_details):
      self.episode_map[int(details['season']), int(details['episode'])] = index
  
  def load_feed(self):
    """
    Load the feed for the show's podcast, and pull out the pod episodes that match this show.
    """
    show_name = self.show_settings.get('pod_name', self.show)
    podcast = podcasts[self.show_settings['pod']]
    self.podcast_name = podcast['name']
    
    feed = feedparser.parse(podcast['url'])
    regex = re.compile(fr"{show_name} S(\d+)E(\d+)", re.IGNORECASE)
    
    for entry in feed['entries']:
      regex_match = regex.search(entry['title'])
      if not regex_match:
        continue
      season = int(regex_match[1])
      episode = int(regex_match[2])
      self.podcast_episodes[season, episode] = entry
  
  def get_current_details(self, season: int, episode: int) -> Optional[dict]:
    """
    Load the episode details from the current website.  Or none if it doesn't exist (yet)
    """
    if (season, episode) in self.episode_map:
      return self.episode_details[self.episode_map[season, episode]]
    
    return None
  
  def set_tmdb_details(self, details: dict, season: int, episode: int) -> dict:
    """
    Load details from TMDB
    """
    tmdb_episode = tmdbsimple.TV_Episodes(self.show_settings['tmdb'], season, episode)
    try:
      tmdb_details = tmdb_episode.info()
    except requests.exceptions.HTTPError:
      print(f"Unable to find {self.show} S{season:02}E{episode:02} in TMDB")
      return details
    if not tmdb_details.get('id'):
      print(f"Unable to find {self.show} S{season:02}E{episode:02} in TMDB")
      return details
    
    if not details:
      details = {
        "airdate": None,
        "title": None,
        "description": None,
        "season": f"{season:02}",
        "episode": f"{episode:02}",
        "podcasts": [],
        "memoryalpha": None,
        "tvdb": None,
        "imdb": None,
        "stills": [],
      }
      self.episode_map[season, episode] = len(self.episode_details)
      self.episode_details.append(details)
    
    details['airdate'] = tmdb_details["air_date"].replace("-", ".")
    details['description'] = tmdb_details['overview']
    details['title'] = tmdb_details['name']
    details['tvdb'] = tmdb_details['id']  # It's tMdb, but we're keeping it for consistency
    details['imdb'] = tmdb_episode.external_ids().get('imdb_id')
    stills = []
    for image in tmdb_episode.images()['stills']:
      stills.append(f"https://image.tmdb.org/t/p/original{image['file_path']}")
    if stills:
      details['stills'] = stills
    
    print(f"Updated episode “{details['title']}” from TMDB")
    return details
  
  def set_memory_alpha(self, details: dict):
    """
    Use the Fandom API to get the title of the episode page.  That's also the slug for the page.
    """
    req = requests.get("https://memory-alpha.fandom.com/api.php",
                       params={'action': 'query', 'list': 'search', 'srlimit': '1', 'srprop': '', 'format': 'json',
                               'srsearch': f"{self.show[:3]} {details['season'].strip('0')}x{details['episode']} "
                                           f"{details['title']} (episode)"})
    results = json.loads(req.content)
    details['memoryalpha'] = results['query']['search'][0]['title'].replace(' ', '_')  # there might be more formatting
    print(f"Updated Memory Alpha link to {details['memoryalpha']}")
  
  def set_podcast(self, details, season, episode):
    """
    Get the podcast for this episode from the feed.  If there are more than one, then they will have to be added
    manually
    """
    podcast = self.podcast_episodes.get((season, episode))
    if not podcast:
      print(f"No podcast for {self.show} S{details['season']}E{details['episode']} yet")
      return
    
    # Search the maxfun website for the link to the episode. For some reason, it's not in the RSS feed
    req = requests.get("https://maximumfun.org/search/", params={"_type": "episode", "_term": podcast['title']})
    re_match = re.search(r'a href="(https://maximumfun\.org/episodes/.+/)"', req.content.decode(errors='ignore'))
    if re_match:
      page_link = re_match[1]
    else:
      page_link = None
    
    details['podcasts'] = [
      {
        "airdate": parser.parse(podcast['published']).strftime('%Y.%m.%d'),
        "episode": re.sub(r' \([^()]+\)$', '', podcast['title']),
        "link": page_link,
        "order": int(podcast['itunes_episode']),
        "title": self.podcast_name,
      }
    ]
    print(f"Updated the podcast to {podcast['title']}")
  
  def save_current_file(self):
    """
    Save the entire file, including all episodes we know about.
    """
    recordset = {
      "animated": self.show_settings["animated"],
      "episodes": self.episode_details,
      "imdb": self.show_settings.get("imdb", ""),
      "title": self.show_settings["title"],
      "trek": self.show_settings['trek'],
      "tvdb": self.show_settings.get("tmdb"),
    }
    print(f"saving file {self.filename}")
    with open(self.filename, "w") as fp:
      json.dump(recordset, fp, indent=4)


if __name__ == '__main__':
  args = docopt.docopt(__doc__)
  args = ShowGenerator.clean_and_validate_args(args)
  if args:
    generator = ShowGenerator(**args)
    generator.run()
