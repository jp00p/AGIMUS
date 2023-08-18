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
    
    -p --pod              Update the podcast information.  Useful for old shows that have only just been covered.
    -d --details          Update the episode details from TVDB.
    -m --memory-alpha     Update the link to the episode in Memory Alpha.
    
                          If -p, -d, and -m are not specified, then all of them will be updated.
                          
Examples:
    The pod has just covered Spock's Brain, and the episode is already in the file
    generate_show_json.py tos -s 3 -e 6 -p
    
    Season 3 of LDS has finished, and so it’s time to add all of them
    generate_show_json.py lowerdecks -s 3
"""
import json
import os.path
import re

import docopt

import feedparser

# Important config options that will need to be updated as new shows are added
import requests
import tmdbsimple
from dateutil import parser

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
  def __init__(self, cli_args: dict):
    self.show = cli_args['<show>']
    if self.show not in all_shows:
      print(f"{self.show} is not one of {all_shows.keys()}")
      exit(1)
    self.show_settings = all_shows[self.show]
    
    self.filename = cli_args['<filename>'] or f"../data/episodes/{self.show}.json"
    
    try:
      if cli_args['--season']:
        self.seasons = [int(s) for s in cli_args['--season'].split(',')]
      else:
        self.seasons = range(1, 8)  # So far, no show has gone beyond 7 seasons
    except ValueError:
      print(f"-s should be a number or a list of numbers with commas inbetween.  Got “{cli_args['--season']}”")
      exit(1)
    
    try:
      if cli_args['--episode']:
        self.episodes_to_update = [int(s) for s in cli_args['--episode'].split(',')]
      else:
        self.episodes_to_update = range(1, 30)  # Remember when seasons were 20+ episodes?
    except ValueError:
      print(f"-e should be a number or a list of numbers with commas inbetween.  Got “{cli_args['--episode']}”")
      exit(1)
    
    self.run_tmdb = cli_args['--details']
    self.run_pod = cli_args['--pod']
    self.run_memory_alpha = cli_args['--memory-alpha']
    if not (self.run_pod or self.run_tmdb or self.run_memory_alpha):
      self.run_pod = self.run_tmdb = self.run_memory_alpha = True
    
    self.episode_details = []
    self.episode_map = {}
  
  def run(self):
    self.load_current_file()
    if self.run_pod:
      self.load_feed()
    
    for season in self.seasons:
      for episode in self.episodes_to_update:
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
    self.podcast_episodes = {}
    show_name = self.show_settings.get('pod_name', self.show)
    podcast = podcasts[self.show_settings['pod']]
    self.podcast_name = podcast['name']
    
    feed = feedparser.parse(podcast['url'])
    regex = re.compile(fr"\({show_name} S(\d+)E(\d+)\)", re.IGNORECASE)
    
    for entry in feed['entries']:
      regex_match = regex.search(entry['title'])
      if not regex_match:
        continue
      season = int(regex_match[1])
      episode = int(regex_match[2])
      self.podcast_episodes[season, episode] = entry
  
  def get_current_details(self, season: int, episode: int) -> dict:
    if (season, episode) in self.episode_map:
      return self.episode_details[self.episode_map[season, episode]]
    
    return None
  
  def set_tmdb_details(self, details: dict, season: int, episode: int) -> dict:
    """
    Load details from TMDB
    """
    tmdb_episode = tmdbsimple.TV_Episodes(self.show_settings['tmdb'], season, episode)
    tmdb_details = tmdb_episode.info()
    
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
    for image in tmdb_episode.images():
      details['stills'].append(f"https://image.tmdb.org/t/p/original{image['file_path']}")
    
    print(f"Updated episode {self.show} S{details['season']}E{details['episode']} “{details['title']}” from TMDB")
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
    
    req = requests.get("https://maximumfun.org/search/",
                       params={"_type": "episode",
                               "_term": f"{self.podcast_name} EP {podcast['itunes_episode']} {podcast['title']}"})
    re_match = re.search(r'a href="(https://maximumfun\.org/episodes/.+/)"', req.content.decode(errors='ignore'))
    if re_match:
      page_link = re_match[1]
    else:
      page_link = None
    
    details['podcasts'] = [
      {
        "title": self.podcast_name,
        "order": int(podcast['itunes_episode']),
        "airdate": parser.parse(podcast['published']).strftime('%Y.%m.%d'),
        "episode": podcast['title'],
        "link": page_link
      }
    ]
    print(f"Updated the podcast to {podcast['title']}")
  
  def save_current_file(self):
    recordset = {
      "animated": self.show_settings["animated"],
      "episodes": self.episode_details,
      "imdb": self.show_settings.get("imdb"),
      "title": self.show_settings["title"],
      "trek": self.show_settings.get("trek"),
      "tvdb": self.show_settings.get("imdb"),
    }
    with open(self.filename, "w") as fp:
      json.dump(recordset, fp, indent=2)


if __name__ == '__main__':
  args = docopt.docopt(__doc__)
  generator = ShowGenerator(args)
  generator.run()
