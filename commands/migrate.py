from .common import *
import inspect
from os.path import exists

def load_file_into_array(file_name):
  file_obj = open(file_name, "r") 
  lines = file_obj.read().splitlines()
  file_obj.close()
  return lines


# migrate() - Entrypoint for !migrate command
# message[required]: discord.Message
# This function is the main entrypoint of the !migrate command
async def migrate(message:discord.Message):

  shows = {
    "tng": {
      "tvdb":655,
      "title": "Star Trek: The Next Generation",
      "trek": True,
      "animated": False,
      "imdb": "tt0092455"
    },
    "voy": {
      "tvdb":1855,
      "title": "Star Trek: Voyager",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "ds9": {
      "tvdb":580,
      "title": "Star Trek: Deep Space Nine",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "friends": {
      "tvdb":1668,
      "title": "Friends",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "firefly": {
      "tvdb":1437,
      "title": "Firefly",
      "trek": False,
      "animated": False,
      "imdb": ""
    },
    "simpsons": {
      "tvdb":456,
      "title": "The Simpsons",
      "trek": False,
      "animated": True,
      "imdb": ""
    },
    "enterprise": {
      "tvdb":314,
      "title": "Star Trek: Enterprise",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "tos": {
      "tvdb":253,
      "title": "Star Trek: The Original Series",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "lowerdecks": {
      "tvdb":85948,
      "title": "Star Trek: Lower Decks",
      "trek": True,
      "animated": True,
      "imdb": ""
    },
    "disco": {
      "tvdb":67198,
      "title": "Star Trek: Discovery",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "picard": {
      "tvdb":85949,
      "title": "Star Trek: Picard",
      "trek": True,
      "animated": False,
      "imdb": ""
    },
    "tas": {
      "tvdb":1992,
      "title": "Star Trek: The Animated Series",
      "trek": True,
      "animated": True,
      "imdb": ""
    },
    "sunny": {
      "tvdb":2710,
      "title": "It's Always Sunny in Philidelphia",
      "trek": False,
      "animated": False,
      "imdb": ""
    },
  }
  migrate_spl = message.content.lower().replace("!migrate ", "").split()
  these_shows = []
  if migrate_spl[0] == "all":
    these_shows = shows.keys()
  else:
    these_shows.append(migrate_spl[0])
  for this_show in these_shows:
    this_show_id = shows[this_show]["tvdb"]
    logger.info(f'Migrating: {shows[this_show]["title"]}')
    episodes = []
    track_episode = 0
    track_season = 0
    track = 0
    max = 10000
    failed = 0
    moveon = 0
    tgg = {}
    if exists("./data/episodes/tgg_" + this_show + ".json"):
      f = open("./data/episodes/tgg_" + this_show + ".json")
      tgg = json.load(f)
      f.close()
    for track_season in range(1,40):
      failed = 0
      if moveon > 1:
        break
      for track_episode in range(1,40):

        this_episode = {}
        tseason = str(track_season)
        if track_season < 10:
          tseason = "0" + str(track_season)
        tepisode = str(track_episode)
        if track_episode < 10:
          tepisode = "0" + str(track_episode)
        tgg_key = "s" + tseason + "e" + tepisode

        tmdb_episode = tmdb.TV_Episodes(this_show_id,track_season,track_episode)

        this_episode["airdate"] = ""
        this_episode["description"] = ""
        try:
          episode_details = tmdb_episode.info()
          # logger.info(f"key: {tgg_key}")
          logger.info(f'Title[{episode_details["id"]}][s{tseason}e{tepisode}]: {episode_details["name"]}')
          logger.debug(f">>> Info: {episode_details}")
          this_episode["airdate"] = episode_details["air_date"].replace("-", ".")
          this_episode["description"] = episode_details["overview"]
          this_episode["title"] = episode_details["name"]
          this_episode["tvdb"] = episode_details["id"]

        except:
          failed = failed + 1
          logger.warning("This episode does not exist[" + str(failed) + "][" + str(moveon) + "]: s" + tseason + "e" + tepisode)
          await asyncio.sleep(.3)
          if failed > 0:
            moveon = moveon + 1
            break
        # await message.channel.send('Migrating[' + eps[1] + '][s' + tseason + 'e' + tepisode + ']:' + eps[0])
        this_episode["season"] = tseason
        this_episode["episode"] = tepisode
        
        this_episode["memoryalpha"] = ""
        this_episode["podcasts"] = []
        if tgg_key in tgg:
          this_episode["memoryalpha"] = tgg[tgg_key]["memoryalpha"].replace(" ", "_")
          this_episode["podcasts"] = tgg[tgg_key]["podcasts"]
        this_episode["imdb"] = ""
        this_episode["stills"] = []
        tmdb_episode = tmdb.TV_Episodes(this_show_id,int(tseason),int(tepisode))
        try:
          episode_external_ids = tmdb_episode.external_ids()
          logger.debug(f">>> external: {episode_external_ids}")
          this_episode["imdb"]=episode_external_ids["imdb_id"]
          if len(episode_external_ids) > 0:
            moveon = 0
          episode_stills = tmdb_episode.images()
          logger.debug(f">>> images: {episode_stills}")
          tstills = []
          for s in episode_stills["stills"]:
            tstills.append(TMDB_IMG_PATH + s["file_path"])
          this_episode["stills"] = tstills
        except:
            pass

        episodes.append(this_episode)
        await asyncio.sleep(.1)
        if track > max:
          break
        track=track+1

    logger.debug(f"Episodes: {episodes}")
    show = {
      "title": shows[this_show]["title"],
      "tvdb": this_show_id,
      "trek": shows[this_show]["trek"],
      "animated": shows[this_show]["animated"],
      "imdb": shows[this_show]["imdb"],
      "episodes": episodes
    }
    with open('./data/episodes/' + this_show + '.json', 'w') as f:
      json.dump(show, f, indent=4, sort_keys=True)
    logger.info("Written: /data/episodes/" + this_show + ".json")

