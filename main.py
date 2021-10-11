import discord
from discord.ext import tasks
import os
import random
import tmdbsimple as tmdb
import requests
import asyncio
import string
import json
from PIL import Image, ImageFont, ImageDraw, ImageColor
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import mysql.connector
from tabulate import tabulate
from trivia import trivia
import numpy as np

load_dotenv()
tmdb.API_KEY = os.getenv('TMDB_KEY')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')

TMDB_IMG_PATH = "https://image.tmdb.org/t/p/original"

client = discord.Client()

# globals
CORRECT_ANSWERS = {}
FUZZ = {}
QUIZ_EPISODE = False
TRIVIA_RUNNING = False
TRIVIA_DATA = {}
TRIVIA_MESSAGE = None
TRIVIA_ANSWERS = {}
LAST_SHOW = False
PREVIOUS_EPS = {}
EMOJI = {}
QUIZ_SHOW = False
LOG = []
SLOTS_RUNNING = False

TNG_ID = 655
VOY_ID = 1855
DS9_ID = 580
XFILES_ID = 4087
FRIENDS_ID = 1668
FF_ID = 1437
SIMPSONS_ID = 456
ENTERPRISE_ID = 314
TOS_ID = 253
LDX_ID = 85948
DISCO_ID = 67198
PICARD_ID = 85949
TAS_ID = 1992
SUNNY_ID = 2710

TRIVIA_CATEGORIES = [
  { "id":"1",	"name":"General Knowledge"},
  { "id":"2",	"name":"Entertainment: Books"},
  { "id":"3",	"name":"Entertainment: Film"},
  { "id":"4",	"name":"Entertainment: Music"},
  { "id":"5",	"name":"Entertainment: Musicals & Theatres"},
  { "id":"6",	"name":"Entertainment: Television"},
  { "id":"7",	"name":"Entertainment: Video Games"},
  { "id":"8",	"name":"Entertainment: Board Games"},
  { "id":"9",	"name":"Science & Nature"},
  { "id":"10",	"name":"Science: Computers"},
  { "id":"11",	"name":"Science: Mathematics"},
  { "id":"12",	"name":"Mythology"},
  { "id":"13",	"name":"Sports"},
  { "id":"14",	"name":"Geography"},
  { "id":"15",	"name":"History"},
  { "id":"16",	"name":"Politics"},
  { "id":"17",	"name":"Art"},
  { "id":"18",	"name":"Celebrities"},
  { "id":"19",	"name":"Animals"},
  { "id":"20",	"name":"Vehicles"},
  { "id":"21",	"name":"Entertainment: Comics"},
  { "id":"22",	"name":"Science: Gadgets"},
  { "id":"23",	"name":"Entertainment: Japanese Anime & Manga"},
  { "id":"24",	"name":"Entertainment: Cartoon & Animations"},
]

SLOTS =  {
    "TNG" : {
      "files" : "./slots/tng/",
      "payout" : 1,
      "custom_jackpot" : ["picard", "picard", "picard"],
      "matches" : {
        "Villains" : ["armus", "pakled", "lore"],
        "Federation Captains" : ["picard", "jellico"],
        "Olds" : ["pulaski", "jellico", "picard", "kevin"],
        "No Law to fit your Crime" : ["picard", "kevin"],
        "Music Box Torture" : ["kevin", "troi"],
        "Ensigns" : ["ro", "wesley"],
        "Omnipotent" : ["q", "armus", "kevin"],
        "Bros" : ["data", "lore"],
        "Doctors" : ["beverly", "pulaski"],
        "Drunkards" : ["obrien", "pulaski"],
        "Rascals" : ["ro", "guinan", "picard", "keiko"],
        "Baby Delivery Team" : ["worf", "keiko"],
        "Robot Fuck Team" : ["data", "yar"],
        "Loving Couple" : ["obrien", "keiko"],
        "Best Friends" : ["geordi", "data"],
        "Jazz Funeral" : ["geordi", "ro"],
        "Engineers" : ["geordi", "obrien"],
        "Nexus Travellers" : ["guinan", "picard"],
        "Related to Jack Crusher" : ["beverly", "wesley"],
        "Eggs for Breakfast" : ["riker", "pulaski", "worf"],
        "Humanity on Trial" : ["q", "picard"],
        "Delta Shift" : ["riker", "jellico"],
        "Imzadi" : ["troi", "riker"],
        "\"Nice house, good tea\"" : ["worf", "kevin"],
        "Empty Death" : ["yar", "armus"],
        "Butting Heads" : ["riker", "ro"],
        "Leotard Buddies" : ["beverly", "troi"],
        "Security Squad" : ["worf", "yar"],
        "Coffee and Croissants" : ["picard", "beverly"],
        "Uncomfortable with Children" : ["picard", "wesley"],
        "Bean Flicking Stance" : ["guinan", "q"],
        "\"I don't need your fantasy women\"" : ["riker", "q"]
      }
    },
    "DS9" : {
      "files" : "./slots/ds9/",
      "payout" : 1.5,
      "custom_jackpot" : ["weyoun4", "weyoun5", "weyoun6"],
      "matches": {
        "The Dominion" : ["weyoun4", "weyoun5", "weyoun6", "yelgrun", "keevan", "kilana", "flakeleader", "goranagar", "ikatika"],
        "\"Old Man\"" : ["jadzia", "sisko"],
        "Slug Buddies" : ["ezri", "jadzia"],
        "Bajoran Spiritual Leaders" : ["bareil", "opaka", "winn", "sisko"],
        "Sisko's Lovers" : ["jennifer", "kasidy"],
        "Love is Blind" : ["winn", "dukat"],
        "Lunch Date" : ["bashir", "garak"],
        "Holodeck Date" : ["bashir", "obrien"],
        "Villains" : ["winn", "dukat", "flakeleader"],
        "Jeffreys" : ["weyoun4", "weyoun5", "weyoun6", "brunt"],
        "Enterprise officers" : ["worf", "obrien"],
        "Bell rioters" : ["sisko", "bashir", "jadzia"],
        "Promenade hangin'" : ["jake", "nog"],
        "Golden liquid" : ["bashir", "odo", "flakeleader"],
        "Secret Societies" : ["sloan", "garak", "flakeleader"],
        "Search for the Cure" : ["bashir", "goranagar"],
        "Violent Love" : ["worf", "jadzia"],
        "Dance in my Golden Sparkles" : ["odo", "kira"],
        "Niners" : ["sisko", "worf", "rom", "ezri", "kira", "bashir", "nog", "quark"],
        "Take me out to the Imaginary Ball Game" : ["sisko", "bokai"],
        "Not Corporeal" : ["bokai", "vic"],
        "Breaking the Ferengi Mold" : ["rom", "nog", "ishka"],
        "Nagusii" : ["brunt", "zek", "rom", "quark"],
        "Affectionate Touches" : ["jake", "sisko"],
        "Drinking Buddies" : ["gowron", "jadzia"],
        "Love Conquers Mountains" : ["quark", "odo"],
        "Did he Fuck her Mom?" : ["kira", "dukat"],
        "Cardassians" : ["dukat", "garak", "damar", "ziyal"],
        "Piano Lessons" : ["vic", "odo"],
        "Wounded Lounge Lizard" : ["vic", "nog"],
        "You Forgot their Name" : ["goranagar", "ikatika", "yelgrun", "keevan"],
        "Possible Changeling Spy" : ["gowron", "bashir"],
        "Prison Pals" : ["obrien", "ezri", "martok", "bashir", "garak"],
        "Battled the Pah'wraiths" : ["winn", "jake", "sisko", "obrien"],
        "Senator Killers" : ["garak", "sisko"],
        "Engineers and Unionmen" : ["obrien", "rom"],
        "Starfleet Intelligence" : ["obrien", "bashir", "sloan"],
        "*Probably* Unmodified Humans" : ["jake", "jennifer", "sisko", "obrien"],
        "Smugglers" : ["quark", "kasidy"],
        "Quark-haters" : ["kira", "brunt", "odo"],
        "Cardassian Freedom Fighters" : ["garak", "damar", "kira"],
        "RSVP" : ["jennifer", "jadzia", "bareil", "winn", "dukat", "weyoun4", "weyoun5", "weyoun6", "keevan", "sloan", "damar", "ziyal"],
        "Profitable Lovers" : ["ishka", "zek"],
        "A Father's Love" : ["ziyal", "dukat"],
        "Profit & Honor": ["quark", "grilka"],
        "Barflies":["obrien", "morn", "bashir", "damar", "jadzia"],
        "Klingons":["gowron", "worf", "grilka"],
        "Leeta Lovers":["bashir", "rom"],
        "Bajoran-Ferengi Romance": ["leeta", "rom"],
        
      }
    },
    "VOY" : {
      "files" : "./slots/voy/",
      "payout" : 1.25,
      "custom_jackpot" : ["neelix", "tuvok", "tuvix"],
      "matches" : {
        "D-Quad Born" : ["borg_queen", "culluh", "danara_pei", "fesek", "icheb", "karr", "kes", "kurros", "naomi_wildman", "neelix", "penk", "sulan", "tuvix"],
        "Bride of Chaotica" : ["arachnia", "chaotica", "captain_proton", "president_doctor"],
        "Goes Great Together" : ["neelix", "tuvok"],
        "Janeway's Choice" : ["janeway", "tuvix"],
        "Relationship: Gross" : ["neelix", "kes"],
        "Tried to Kill The Voyager" : ["seven", "chaotica", "borg_queen", "braxton", "species_8472"],
        "LA Residents" : ["rain", "braxton"],
        "LA Tourists" : ["janeway", "tom_paris", "tuvox", "chakotay"],
        "Kids in the Voy" : ["naomi_wildman", "kes", "icheb"],
        "Daddy Issues" : ["tom_paris", "owen_paris"],
        "Royal Rumble" : ["penk", "seven"],
        "Mayqueese?" : ["chakotay", "seska", "torres", "suder"],
        "Doctor's proteges" : ["kes", "seven", "tom_paris"],
        "Long-distance Rates May Apply" : ["barclay", "rain"],
        "Season 3 Torch Pass" : ["kes", "seven"],
        "Murder Meld" : ["tuvok", "suder"],
        "Faces of Janeway" : ["janeway", "arachnia", "evolved_janeway"],
        "Relationship: Why?" : ["chakotay", "seven"],
        "Relationship: Purely Professional" : ["chakotay", "janeway"],
        "Relationship: Success" : ["tom_paris", "torres"],
        "Relationship: Kissed in a Nightmare Once" : ["harry_kim", "seven"],
        "Perv Patrol" : ["harry_kim", "tom_paris"],
        "Expecting Parents" : ["chakotay", "seska"],
        "Same Stylist" : ["culluh", "arachnia"],
        "Borgified" : ["janeway", "borg_queen", "seven", "tuvok", "torres", "icheb"],
        "Double Doc Z" : ["doctor", "president_doctor"],
        "Relationship: Holographic" : ["doctor", "danara_pei"],
        "Murderers" : ["sulan", "suder", "borg_queen", "janeway", "species_8472", "karr"],
        "Relationship: Kissed Once in 1996" : ["tom_paris", "rain"],
        "IRL Comedians" : ["rain", "kurros"],
        "\"Comb that Hair!\"" : ["tom_paris", "chakotay"],
        "Relationship: Not Healthy" : ["chulluh", "seska"],
        "Imposters" : ["species_8472", "seska"]
      }
    },
    "HOLODECK" : {
      "files" : "./slots/holodeck/",
      "payout" : 1.5,
      "custom_jackpot" : ["musketeer_picard", "musketeer_data", "musketeer_geordi"],
      "matches": {
        "Warship: Voyager" : ["warship_chakotay", "warship_janeway", "warship_tuvok", "warship_doctor"],
        "Big Dix" : ["dixon_hill", "doc_beverly", "gloria_guinan", "cyrus_redblock"],
        "The Spy who Soaked Me" : ["duchamps_worf", "anastasia_kira", "falcon_obrien", "hippocrates_sisko", "spy_bashir", "honeybare_jadzia"],
        "The Age of Sail" : ["sailor_beverly", "sailor_data", "sailor_lagorge", "sailor_riker"],
        "Hollow Pursuits" : ["little_boy_blue_wesley", "musketeer_picard", "musketeer_data", "musketeer_geordi", "troi_goddess_of_empathy"],
        "Holo-Girlfriends" : ["minuet", "troi_goddess_of_empathy", "leah_brahams", "regina_bartholomew"],
        "Fistful of Datas" : ["sherrif_worf", "frank_hollander_data", "durango_troi"],
        "Elementary, my Dear Data" : ["sherlock_data", "moriarity", "regina_bartholomew"],
        "Doctor's Fantasies" : ["ech", "author_emh", "teetime_doctor"],
        "Villains" : ["moriarity", "hippocrates_sisko", "frank_hollander_data", "cyrus_redblock", "anastasia_kira", "falcon_obrien"],
        "State Enforcers" : ["sherrif_worf", "spy_bashir"],
        "Faces of Geordi" : ["sailor_laroge", "musketeer_geordi"],
        "Faces of Beverly": ["sailor_beverly", "doc_beverly"],
        "Faces of Worf" : ["duchamps_worf", "sailor_worf", "sherrif_worf"],
        "Faces of Data" : ["sherlock_data", "sailor_data", "musketeer_data"],
        "Faces of Picard" : ["dixon_hill", "musketeer_picard"],
        "Faces of Tuvok" : ["bartender_tuvok", "warship_tuvok"],
        "Faces of Troi" : ["troi_goddess_of_empathy", "durango_troi"],
        "Smoke Break" : ["anastasia_kira", "duchamps_worf", "gloria_guinan"],
        "Cute Bowtie" : ["bartender_tuvok", "duchamps_worf", "spy_bashir", "teetime_doctor"]
        
      }
    },
    "TEST" : {
      "files" : "./slots/test/",
      "payout" : 0,
      "matches" : {
        "armus" : ["oops all armus"]
      }
    }
}



def load_file_into_array(file_name):
  file_obj = open(file_name, "r") 
  lines = file_obj.read().splitlines()
  file_obj.close()
  return lines

prompts = load_file_into_array("./data/prompts")
characters = load_file_into_array("./data/characters")
fmk_characters = load_file_into_array("./data/fmk_chars")
tuvixes = load_file_into_array("./data/tuvixes")
duelists = load_file_into_array("./data/duel_characters")
tng_eps = load_file_into_array("./data/tng_episode_list")
ds9_eps = load_file_into_array("./data/ds9_episode_list")
friends_eps = load_file_into_array("./data/friends_episodes")
ff_eps = load_file_into_array("./data/firefly_episodes")
simpsons_eps = load_file_into_array("./data/simpsons_episodes")
community_eps = load_file_into_array("./data/community_eps")
buffy_eps = load_file_into_array("./data/buffy_eps")
futurama_eps = load_file_into_array("./data/futurama_eps")
supernatural_eps = load_file_into_array("./data/supernatural_eps")
seinfeld_eps = load_file_into_array("./data/seinfeld_eps")
bab5_eps = load_file_into_array("./data/bab5_eps")
tas_eps = load_file_into_array("./data/tas_eps")
tos_eps = load_file_into_array("./data/tos_eps")
enterprise_eps = load_file_into_array("./data/enterprise_eps")
ldx_eps = load_file_into_array("./data/lowerdecks_eps")
picard_eps = load_file_into_array("./data/picard_eps")
disco_eps = load_file_into_array("./data/disco_eps")
voy_eps = load_file_into_array("./data/voy_eps")
sunny_eps = load_file_into_array("./data/sunny_eps")

TREK_SHOWS = [
  ["The Next Generation", TNG_ID, tng_eps],
  ["Deep Space Nine", DS9_ID, ds9_eps],
  ["Voyager", VOY_ID, voy_eps],
  ["Enterprise", ENTERPRISE_ID, enterprise_eps],
  ["Discovery", DISCO_ID, disco_eps],
  ["Picard", PICARD_ID, picard_eps],
  ["The Original Series", TOS_ID, tos_eps],
  ["Lower Decks", LDX_ID, ldx_eps],
  ["The Animated Series", TAS_ID, tas_eps]
]

TREK_WEIGHTS = []
for i in range(len(TREK_SHOWS)):
  # weights are how many eps in the total show (favors 90s trek)
  TREK_WEIGHTS.append(len(TREK_SHOWS[i][2]))

NON_TREK_SHOWS = [
  ["Friends", 1668, friends_eps],
  ["Firefly", 1437, ff_eps],
  ["The Simpsons", 456, simpsons_eps],
  ["Community", 18347, community_eps],
  ["Futurama", 615, futurama_eps],
  ["Buffy the Vampire Slayer", 95, buffy_eps],
  ["Supernatural", 1622, supernatural_eps],
  ["Seinfeld", 1400, seinfeld_eps],
  ["Babylon 5", 3137, bab5_eps],
  ["It's Always Sunny in Philidelphia", SUNNY_ID, sunny_eps]
]

war_intros = ["War! Hoo! Good god y'all!", "War! We're going to war!", "That nonsense is *centuries* behind us!", "There's been no formal declaration, sir.", "Time to pluck a pigeon!"]

# fill this in with DB on init
# add new players during gameplay as needed
# prevent reading from db for simple lookups

# set this from db on init
JACKPOT = 0
ALL_PLAYERS = []


PROFILE_CARDS = ["Archer", "Bashir", "Boimler", "Brunt", "Data", "EMH", "Garak", "Gowron", "Janeway", "Mark Twain", "Picard", "Q", "Quark", "Ransom", "Sisko", "Shran", "Tilly", "Worf"]
PROFILE_BADGES = {
  "TGG TNG Logo" : "TGG_TNG_logo.jpg",
  "TGG DS9 Logo" : "TGG_DS9_logo.png",
  "TGD Logo" : "TGD_logo.png",
  "Adam Pranica" : "adam_lmao.png",
  "Ben Harrison" : "ben420laughlmao.png",
  "Card Daddy" : "bill_cardaddy_thumbsup.png",
  "Heart" : "heart.png",
  "Horgahn" : "horgahn.png",
  "Banger" : "icon_banger_no_background_small.png",
  "Mr. Bucket" : "mr-bucket.png",
  "Ding!" : "ding_bell.png",
  "Bashir's Special" : "bashir_splash.png"
}
SHOP_ROLES = {
  "High Roller" : {
    "id" : 894594667893641236,
    "price" : 9999
  }
}

@client.event
async def on_ready():
  global EMOJI, ALL_PLAYERS
  random.seed()
  EMOJI["shocking"] = discord.utils.get(client.emojis, name="qshocking")
  EMOJI["chula"] = discord.utils.get(client.emojis, name="chula_game")
  EMOJI["allamaraine"] = discord.utils.get(client.emojis, name="allamaraine")
  EMOJI["love"] = discord.utils.get(client.emojis, name="love_heart_tgg")
  print('We have logged in as {0.user}'.format(client))
  ALL_PLAYERS = get_all_players()
  print("Current registered players", ALL_PLAYERS)
  

@client.event
async def on_raw_reaction_add(payload:discord.RawReactionActionEvent):
  global TRIVIA_ANSWERS
  if TRIVIA_MESSAGE and payload.message_id == TRIVIA_MESSAGE.id:
    if payload.user_id != client.user.id:
      #emoji = await discord.utils.get(TRIVIA_MESSAGE.reactions, emoji=payload.emoji.name)
      user = await client.fetch_user(payload.user_id)
      await TRIVIA_MESSAGE.remove_reaction(payload.emoji, user)
      TRIVIA_ANSWERS[payload.user_id] = payload.emoji.name


@client.event
async def on_message(message):
  
  global QUIZ_EPISODE, CORRECT_ANSWERS, FUZZ, EMOJI, LOG, SLOTS_RUNNING, ALL_PLAYERS
  
  SLOTS_CHANNEL = 891412391026360320
  QUIZ_CHANNEL = 891412585646268486
  CONVO_CHANNEL = 891412924193726465
  SHOP_CHANNEL = 895480382680596510
  
  if message.author == client.user:
    return

  if message.channel.id not in [888090476404674570, SLOTS_CHANNEL, QUIZ_CHANNEL, CONVO_CHANNEL, SHOP_CHANNEL]:
    return

  if int(message.author.id) not in ALL_PLAYERS:
    register_player(message.author)


  if message.channel.id == SHOP_CHANNEL:
    if message.content.lower() == "!shop":
      msg = "Please use `!shop profiles` or `!shop badges` or `!shop roles`"
      await message.channel.send(msg)

    if message.content.lower().startswith("!shop roles"):
      msg = "__**Role Shop:**__\n COMMANDERS TAKE NOTE: You will be able to buy these roles, but any vanity effects will not apply to you. Sorry!\n\n"
      c = 1
      for i in SHOP_ROLES:
        msg += "`{}` - Role: *{}* - Price: `{}` points\n".format(c, i, SHOP_ROLES[i]["price"])
      msg += "\nAll proceeds go to directly to the jackpot. Type `!buy role` follow by the item number to purchase a role"
      await message.channel.send(msg)

    if message.content.lower().startswith("!shop profiles"):
      msg = "__**Profile Shop:**__\n"
      c = 1
      for i in PROFILE_CARDS:
        msg += "`{}` - Profile Card: *{}*\n".format(c, i)
        c += 1
      msg += "\n`25 points` each. All proceeds go directly to the jackpot\nType `!buy profile` followed by the item number to buy a profile card"
      await message.channel.send(msg)

    if message.content.lower().startswith("!shop badges"):
      msg = "__**Badge Shop**__\n"
      c = 1
      for i in PROFILE_BADGES:
        msg += "`{}` - Badge: *{}*\n".format(c, i)
        c += 1
      msg += "\n`100 points` each. All proceeds go directly to the jackpot\nType `!buy badge` followed by the item number to buy a badge"
      await message.channel.send(msg)

    if message.content.lower().startswith("!buy"):
      
      buy_string = message.content.lower().replace("!buy ", "").split()
      if len(buy_string) < 2:
        await message.channel.send("Invalid shop category.  Please use `!buy badge` or `!buy profile` or `!buy role`.")
      else:
        item_cat = buy_string[0]
        item_to_buy = buy_string[1]
        items = None
        msg = ""
        
        if item_cat not in ["badge", "profile", "role"]:
          msg = "Invalid shop category.  Please use `!buy badge` or `!buy profile` or `!buy role`."
        else:
          
          if item_cat == "badge":
            items = PROFILE_BADGES
            cost = 100
          if item_cat == "profile":
            items = PROFILE_CARDS
            cost = 25
          if item_cat == "role":
            items = SHOP_ROLES
            roles = list(SHOP_ROLES)
            cost = SHOP_ROLES[roles[int(item_to_buy)-1]]["price"] # uh oh...

          player = get_player(message.author.id)
          if player["score"] < cost:
            msg = "{}: You need `{} points` to buy that item!".format(message.author.mention, cost)
          else:
            if item_to_buy.isnumeric():
              if int(item_to_buy) <= len(items):
                
                item = int(item_to_buy) - 1
                
                if item_cat == "badge":
                  badges = list(PROFILE_BADGES)
                  final_item = PROFILE_BADGES[badges[item]]
                  update_player_profile_badge(message.author.id, final_item)
                  msg = "{}: You have spent `{} points` and purchased the **{}** profile badge! Type `!profile` to show it off!".format(message.author.mention, cost, badges[item])
                
                if item_cat == "profile":
                  update_player_profile_card(message.author.id, items[item].lower())
                  msg = "{}: You have spent `{} points` and purchased the **{}** profile card! Type `!profile` to show it off!".format(message.author.mention, cost, items[item])
                
                if item_cat == "role":
                  roles = list(SHOP_ROLES)
                  final_item = SHOP_ROLES[roles[item]]["id"]
                  await update_player_role(message.author, final_item)
                  msg = "{}: You have spent `{} points` and purchased the **{}** role!  You should see the role immediately, but you may need to refresh Discord to see it fully!".format(message.author.mention, cost, roles[item])

                set_player_score(message.author, -cost)
                increase_jackpot(cost)

              else:
                msg = "Not a valid item number!"
            else:
              msg = "Not a valid item number!"
        await message.channel.send(msg)

  
  # if a quiz is a running, start checking answers
  if QUIZ_EPISODE and message.channel.id == QUIZ_CHANNEL:

    threshold = 72  # fuzz threshold

    # lowercase and remove trailing spaces
    correct_answer = QUIZ_EPISODE[0].lower().strip()
    guess = message.content.lower().strip()
    
    # remove all punctuation
    correct_answer = "".join(l for l in correct_answer if l not in string.punctuation).split()
    guess = "".join(l for l in guess if l not in string.punctuation).split()

    # remove common words
    stopwords = ["the", "a", "of", "is", "teh", "th", "eht", "eth", "of", "for", "part 1", "part 2", "part ii", "part i", "in", "are", "an", "as", "and"]
    resultwords  = [word for word in correct_answer if word.lower() not in stopwords]
    guesswords = [word for word in guess if word.lower() not in stopwords]
    
    # rejoin the strings
    correct_answer = ' '.join(resultwords)
    guess = ' '.join(guesswords)

    # check ratios
    ratio = fuzz.ratio(correct_answer, guess)
    pratio = fuzz.partial_ratio(correct_answer, guess)

    # arbitrary single-number score
    normalness = round((ratio + pratio) / 2)

    # add message to the log for reporting
    if (ratio != 0) and (pratio != 0):
      LOG.append([guess, ratio, pratio])

    # check answer
    if (ratio >= threshold and pratio >= threshold) or (guess == correct_answer):
      
      # correct answer      
      award = 1
      bonus = False
      if (ratio < 80 and pratio < 80):
        # bonus
        bonus = True
        award = 2

      id = message.author.id
      if id not in CORRECT_ANSWERS:
        if not CORRECT_ANSWERS:
          award *= 10
        else:
          award *= 5

        set_player_score(message.author, award)

        if id not in FUZZ:
          score_str = "`Correctitude: " + str(normalness) +"`"
          if not bonus:
            score_str += " <:combadge:867891664886562816>"
          else:
            score_str += " <a:combadge_spin:867891818317873192>"
          FUZZ[id] = score_str

        CORRECT_ANSWERS[id] = { "name": message.author.mention, "points":award }
    else:
      if (ratio >= threshold-6 and pratio >= threshold-6):
        await message.add_reaction(EMOJI["shocking"])





  if message.content.lower().startswith("!help"):
    msg = ""

    if message.channel.id == SHOP_CHANNEL:
      msg = '''
**SHOP INFO**
A silly shop to waste your points on!
All proceeds go directly to the jackpot.

**COMMANDS**
`!shop profiles` - list all profile cards for sale
`!shop badges` - list all the badges for sale
`!buy profile 1` - buy profile number 1!  try a different number!
`!buy badge 1` - buy badge number 1!  try a different number!
`!profile` - see your profile card
      '''

    if message.channel.id == SLOTS_CHANNEL:
      msg = '''
**SLOTS INFO**
Slots have a <:bits:818571186195398677>-based matching system.
Get three of the same character to win the jackpot!
DS9 slots are harder to win a jackpot on, but pay 1.5x the bounty!

**COMMANDS**
`!slots` - run a random slot machine!
`!slots ds9` - run a specific slot machine! (try `tng` `ds9` or `voy` or `holodeck`)
`!setwager 1` - set your default wager (try a different number!)
`!jackpots` - see a history of jackpots
`!jackpot` - see the current bounty
`!scores` - see the top scores
`!profile` - see your profile card
'''
    
    if message.channel.id == CONVO_CHANNEL:
      msg = '''
**ABOUT THIS CHANNEL**
A place to generate conversation prompts!

**COMMANDS**
`!tuvix` - create your own Tuvix
`!dustbuster` - beam em down, let god sort em out
`!randomep` - pick a random episode from all trek everywhere
`!trektalk` - generate a conversation piece
`!trekduel` - who will win?
`!fmk` - you know the deal
`!profile` - see your profile card
'''

    if message.channel.id == QUIZ_CHANNEL:
      msg = '''
**QUIZ INFO**
You get bonus points for being slightly wrong!
You get bonus points for being the first to get it right!
You get extra bonus points for being first + silly!
Correctitude is calculated using: <https://en.wikipedia.org/wiki/Levenshtein_distance>
Only one quiz can be active at a time

**QUIZ COMMANDS**
`!quiz` - run a Trek quiz!
`!tvquiz` - run a non-Trek quiz!
`!simpsons` - run a Simpsons quiz!
`!scores` - see the top scores
`!report` - see the fuzziness of the last quiz answers (you want both numbers between 72-80 for the bonus)
`!profile` - see your profile card

**TRIVIA COMMANDS**
`!trivia` - get a random trivia question!
`!trivia 1` - get trivia from a specific category
`!categories` - list all the trivia categories
'''
    await message.channel.send(msg)




  if message.channel.id == SLOTS_CHANNEL and message.content.lower().startswith("!testslots"):
    
    if message.author.id == 572540272563716116:

      if message.content.lower().replace("!testslots ", "") in ["ds9", "tng", "voy", "holodeck"]:
        roll = message.content.lower().replace("!testslots ", "").upper()
      else:
        roll = "TNG"

      spins = 100000
      spin_msg = f"Testing {roll} slots with {spins} spins! Nothing is going to work until this finishes sorry :)"

      await message.channel.send(spin_msg)

      jackpots = 0
      wins = 0
      profitable_wins = 0
      profits = []
      for i in range(spins):
        
        silly,clones,jackpot = roll_slot(roll, generate_image=False)
        profit = len(silly)
        if len(silly) > 0 or len(clones) > 0:
          wins += 1
        if len(silly) > 1 or len(clones) > 0:
          profitable_wins += 1
        if len(clones) > 0:
          profit += 3
        if jackpot:
          jackpots += 1
        profits.append(profit)
        

      chance_to_win = (wins/spins)*100
      chance_to_jackpot = (jackpots/spins)*100
      chance_for_profit = (profitable_wins/spins)*100
      average_profit = sum(profits) / len(profits)

      msg = "\nOut of {0} test spins, there were a total of {1} wins, {2} of those wins being jackpots.\nAverage chance of winning per spin: {3}%.\nAverage chance of jackpot per spin: {4}%.\nNumber of profitable spins: {5}\nChance for profit: {6}%\nAverage profit per spin: {7} points (not counting jackpots)".format(spins,wins,jackpots, chance_to_win, chance_to_jackpot, profitable_wins, chance_for_profit, average_profit)

      await message.channel.send(msg)

    else:

      await message.channel.send("ah ah ah, you didn't say the magic word")


    
  if message.channel.id == SLOTS_CHANNEL and message.content.lower().startswith("!jackpots"):
    jackpots = get_all_jackpots()
    table = []
    table.append(["JACKPOT VALUE", "WINNER", "LIFESPAN", "DATE WON"])
    for jackpot in jackpots:
      lifespan = jackpot["time_won"] - jackpot["time_created"]
      lifespan_str = "{}d {}h {}m".format(lifespan.days, lifespan.seconds//3600, (lifespan.seconds//60)%60)
      table.append([jackpot["jackpot_value"], jackpot["winner"], lifespan_str, jackpot["time_won"].strftime("%x %X")])
    msg = "Last 10 jackpots:\n```"
    msg += tabulate(table, headers="firstrow")
    msg += "```"
    await message.channel.send(msg)
      


  if message.channel.id == SLOTS_CHANNEL and message.content.lower().startswith("!slots"):
    
    if message.content.lower().replace("!slots ", "") in ["ds9", "tng", "voy", "holodeck"]:
      roll = message.content.lower().replace("!slots ", "").upper()
    else:
      roll = random.choice(["TNG", "DS9", "VOY", "HOLODECK"])

    player = get_player(message.author.id)
    id = message.author.id
    free_spin = player["spins"] < 5 # true or false
    wager = player["wager"]
    score_mult = wager
    if free_spin:
      wager = 0
      score_mult = 1
    total_rewards = 0
    payout = SLOTS[roll]["payout"]
    
    if player["score"] < wager and not free_spin:
      await message.channel.send(f"You need at least {wager} point(s) to spin! Play the quiz to get more points or try changing your wager")
    else:
      increment_player_spins(id)
      
      

      spinnin = ["All I do is *slots slots slots*!", "Time to pluck a pigeon!", "Rollin' with my homies...", "It's time to spin!", "Let's roll.", "ROLL OUT!", "Get it player.", "Go go gadget slots!", "Activating slot subroutines!", "Reversing polarity on Alpha-probability particle emitters."]     
      
      spin_msg = message.author.mention + ": "
      spin_msg += random.choice(spinnin)

      if free_spin:
        spin_msg += " **This one's on the house!** (after 5 free spins, they will cost you points!)"
      else:
        spin_msg += f" Spending `{wager}` of your points!"

      spin_msg += " This is spin #{0} for you.".format(player["spins"]+1)

      await message.channel.send(spin_msg)
    
      # roll the slots!
      silly_matches, matching_chars, jackpot = roll_slot(roll, filename=str(message.author.id))
      file = discord.File("./slot_results/{0}.png".format(message.author.id), filename=str(message.author.id)+".png")
        
      match_msg = message.author.mention + "'s spin results: \n"
      
      if len(silly_matches) > 0:
        match_msg += "**Matches: ** "
        match_msg += "; ".join(silly_matches)
        match_msg += " `" + str(len(silly_matches)*score_mult) + " point(s)`\n"
        total_rewards += len(silly_matches) * score_mult
        
      if len(matching_chars) > 0:
        match_msg += "**Transporter clones: ** "
        match_msg += ", ".join(matching_chars).replace("_", " ").title()
        match_msg += " `({0} points)`\n".format(3 * score_mult)
        total_rewards += 3 * score_mult

      if jackpot:

        jackpot_amt = get_jackpot()
        total_rewards += round(jackpot_amt * payout)
        jackpot_art = '''
                     ______
                  _-' .   .`-_
              |/ /  .. . '   .\ \|
             |/ /            ..\ \|
           \|/ |: .   ._|_ .. . | \|/
            \/ |   _|_ .| . .:  | \/
           \ / |.   |  .  .    .| \ /
            \||| .  . .  _|_   .|||/
           \__| \  . :.  .|.  ./ |__/
             __| \_  .    .. _/ |__
              __|  `-______-'  |__
                 -,____  ____,-
                   ---'  `---
         UNITED FEDERATION OF JACKPOTS
'''
        match_msg += "```" + jackpot_art + "```"
        match_msg += "\n "+message.author.mention+" wins the pot of: `{0}` ...multiplied by the slots' jackpot payout rate of x{1}... **for a total winnings of `{2}`**\n\nJackpot has been reset to: **`100`**\n\n".format(jackpot_amt, payout, round(jackpot_amt*payout))
        win_jackpot(message.author.display_name, message.author.id)


      if total_rewards != 0:

        # WIN
        total_profit = total_rewards - wager
        match_msg += "**Total Profit:** `{0} point(s)`.\n".format(total_profit)
        
        embed = discord.Embed(
          title="Results",
          color=discord.Color(0x1abc9c),
          description=match_msg,
        )

        embed.set_image(url="attachment://{0}.png".format(message.author.id))
        embed.set_footer(text="{}'s score: {}".format(player["name"], player["score"]+total_profit))
        
        set_player_score(message.author, total_profit)

        await message.channel.send(embed=embed, file=file)

      else:
        
        # LOSS
        increase_jackpot(score_mult)
        set_player_score(message.author, -wager)
        
        loser = ["No dice!", "Bust!", "No matches!", "Better luck next time!", "Sad trombone!", "You didn't win!", "We have no prize to fit your loss -- ", "You may have won in the mirror universe, but not here!", "Sensors detect no matches.", "JACKP-- no wait, that's a loss.", "Close, but no cigar.", "Not a win!", "You would have won if it were opposite day!"]

        embed = discord.Embed(
          title="Results",
          color=discord.Color(0xe74c3c),
          description="{0}: {1}\n\n`{2}` point(s) added to the jackpot, increasing its bounty to `{3}`.".format(message.author.mention, random.choice(loser), score_mult, get_jackpot()),
        )
        
        embed.set_footer(text="{}'s score: {}".format(player["name"], player["score"]-wager))
        embed.set_image(url="attachment://{0}.png".format(message.author.id))
        
        await message.channel.send(embed=embed, file=file)

  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith("!categories"):
    msg = "Trivia Categories:\n"
    for c in range(len(TRIVIA_CATEGORIES)):
      msg += "`{}`. {}\n".format(c+1, TRIVIA_CATEGORIES[c]["name"])
    example = random.randint(0,len(TRIVIA_CATEGORIES))
    msg += "\n example: Type `!trivia {}` to play the {} category".format(example+1, TRIVIA_CATEGORIES[example]["name"])
    await message.channel.send(msg)
    

  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith("!trivia"):
    if TRIVIA_RUNNING:
      await message.channel.send("Trivia is in progress, please wait!")
    else:
      trivia_category = message.content.lower().replace("!trivia ", "").strip()
      if trivia_category.isnumeric() and int(trivia_category) > 0 and int(trivia_category) < len(TRIVIA_CATEGORIES):
        
        trivia_cat_id = int(TRIVIA_CATEGORIES[int(trivia_category)-1]["id"])
        print("Starting category trivia quiz ", trivia_cat_id)
        await trivia_quiz.start(category=trivia_cat_id)
      else:
        await trivia_quiz.start()


  if message.channel.id == SLOTS_CHANNEL and message.content.lower().startswith("!setwager"):

    min_wager = 1
    max_wager = 100
    wager_val = message.content.lower().replace("!setwager ", "")
    
    player = get_player(message.author.id)
    current_wager = player["wager"]

    if wager_val.isnumeric():
      wager_val = int(wager_val)
      
      

      if wager_val >= min_wager and wager_val <= max_wager:
 
        set_player_wager(message.author.id, wager_val)
        msg = f"{message.author.mention}: Your default wager has been changed from `{current_wager}` to `{wager_val}`"
        await message.channel.send(msg)
      else:
        msg = f"{message.author.mention}: Wager must be a whole number between `{min_wager}` and `{max_wager}`\nYour current wager is: `{current_wager}`"
        await message.channel.send(msg)
    else:
      msg = f"{message.author.mention}: Wager must be a whole number between `{min_wager}` and `{max_wager}`\nYour current wager is: `{current_wager}`"
      await message.channel.send(msg)
    


  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith("!randomep"):
    series = random.choice(TREK_SHOWS)
    ep = random.choice(series[2]).split("|")
    series_name = series[0]
    ep_title = ep[0]
    ep_season = ep[2]
    ep_episode = ep[3]
    msg = "Random Trek episode for you!\n> *{0}* - **{1}** - (Season {2} Episode {3})".format(series_name, ep_title, ep_season, ep_episode)
    await message.channel.send(msg)  







  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith("!report"):
    if len(LOG) != 0:
      msg = "```QUIZ REPORT: \n"
      for l in LOG:
        msg += "{0} ({1}:{2})\n".format(l[0], l[1], l[2])
      msg += "```"
    else:
      msg = "No log entries currently"
    await message.channel.send(msg)



  if message.content.lower() in ["good bot", "nice bot", "fun bot", "sexy bot", "swell bot", "smart bot", "cool bot", "attractive bot", "entertaining bot", "cute bot", "friendly bot", "rad bot", "suave bot"]:
    
    affirmations = ["Thank you!", "Very nice of you to say.", "You're pretty good, yourself!", "`BLUSHING SEQUENCE INITIATED`", "That makes me horny.", "THANKS!!!", "Yay!", "Aw shucks!", "Okay, what do you want?", "Much obliged!", "Subscribe to my OnlyFans!", "Look who's talking :)", "Oh thanks, I'm powered by BLOOD :D", "Oh, stop it, you!", "`COMPLIMENTED ACCEPTED`", "Hands off the merchandise!", "You're welcome!", "Who told you to tell me that?!", "Let's get a room!"]

    await message.add_reaction(EMOJI["love"])
    await message.channel.send(random.choice(affirmations))

  if message.content.lower() in ["bad bot"]:
    await message.channel.send("Oops it's not my fault! Blame jp00p!")




  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith('!faketngtitle'):
    titles = random.sample(tng_eps, 2)
    title1 = titles[0].split("|")
    title2 = titles[1].split("|")
    name1 = [title1[0][:len(title1[0])//2], title1[0][len(title1[0])//2:]]
    name2 = [title2[0][:len(title2[0])//2], title2[0][len(title2[0])//2:]]
    new_episodes = [str(name1[0]+name2[1]).replace(" ", "").title().strip(), str(name2[0]+name1[1]).replace(" ", "").title().strip()]
    await message.channel.send("I made up a fake episode title for you: " + str(random.choice(new_episodes)))

  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith('!quiz') and not QUIZ_EPISODE:
    await message.channel.send("Getting episode image, please stand by...")
    episode_quiz.start()

  if message.channel.id == SLOTS_CHANNEL and message.content.lower().startswith('!jackpot'):
    await message.channel.send("Current jackpot bounty is: {0}".format(get_jackpot()))

  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith('!tvquiz') and not QUIZ_EPISODE:
    await message.channel.send("Getting episode image, please stand by...")
    episode_quiz.start(non_trek=True)
  
  if message.channel.id == QUIZ_CHANNEL and message.content.lower().startswith('!simpsons') and not QUIZ_EPISODE:
    await message.channel.send("Getting episode image, please stand by...")
    episode_quiz.start(non_trek=True, simpsons=True)

  if message.content.lower().startswith("!profile"):
    await generate_profile_card(message.author, message.channel)

  if message.content.lower().startswith('!scores'):
    scores = get_high_scores()
    table = []
    table.append(["SCORE", "NAME", "SPINS", "JACKPOTS"])
    for player in scores:
      table.append([player["score"], player["name"], player["spins"], player["jackpots"]])
      #msg += "{0} - {1} (Spins: {2} Jackpots: {3})\n".format(player["score"], player["name"], player["spins"], player["jackpots"])
    msg = tabulate(table, headers="firstrow")
    await message.channel.send("```"+msg+"```")

  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith('!trekduel'):
    pick_1 = random.choice(characters)
    pick_2 = random.choice(characters)
    choose_intro = random.choice(war_intros)
    while pick_1 == pick_2:
      pick_2 = random.choice(characters)
    msg = choose_intro + "\n================\n" + message.author.mention + ": Who would win in an arbitrary Star Trek duel?!\n" + "\n> **"+pick_1+"** vs **"+pick_2+"**"
    await message.channel.send(msg)

  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith('!tuvix'):
    pick_1 = random.choice(tuvixes)
    pick_2 = random.choice(tuvixes)
    while pick_1 == pick_2:
      pick_2 = random.choice(tuvixes)
    
    name1 = [pick_1[:len(pick_1)//2], pick_1[len(pick_1)//2:]]
    name2 = [pick_2[:len(pick_2)//2], pick_2[len(pick_2)//2:]]

    tuvix1 = str(name1[0]+name2[1]).replace(" ", "").title().strip()
    tuvix2 = str(name2[0]+name1[1]).replace(" ", "").title().strip()

    msg = message.author.mention + " -- a transporter accident has combined **"+pick_1+"** and **"+pick_2+"** into a Tuvix-like creature!  Do you sacrifice the two separate characters for this new one?  Do you give this abomination the Janeway treatment? Can you come up with a line of dialog for this character? Most importantly, do you name it:\n\n> **"+tuvix1+"** or **"+tuvix2+"**???"

    await message.channel.send(msg)


  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith("!fmk"):
    choices = random.sample(fmk_characters, k=3)
    msg = message.author.mention + ": Fuck Marry Kill (or Kiss) -- \n**{}, {}, {}**".format(choices[0], choices[1], choices[2])
    await message.channel.send(msg)


  if message.channel.id == CONVO_CHANNEL and message.content.lower().startswith('!dustbuster'):
    crew = []
    msg = message.author.mention + ", what kind of mission would this Dustbuster club be suited for?  Or are you totally screwed?\n"
    crew = random.sample(characters, k=5)
    for c in crew:
      msg += "> **"+ c + "**\n"
    await message.channel.send(msg)

  
  if message.content.lower().startswith('!trektalk'):
    pick = random.choice(prompts)
    msg =  message.author.mention + "! You want to talk about Trek? Let's talk about Trek! \nPlease answer or talk about the following prompt! One word answers are highly discouraged!\n > **"+pick+"**"
    await message.channel.send(msg)

  #await client.change_presence(activity=discord.Game("Current Jackpot: {}".format(db["jackpot"]), type=3))

  ############## end of on_message function


@tasks.loop(seconds=20,count=1)
async def trivia_quiz(category=None):
  global TRIVIA_DATA, TRIVIA_RUNNING, TRIVIA_MESSAGE
  if category:
    question = await trivia.question(amount=1, quizType='multiple', category=category)
  else:
    question = await trivia.question(amount=1, quizType='multiple')
  TRIVIA_DATA = question[0]
  print("Using category ", category)
  print(TRIVIA_DATA)
  answers = TRIVIA_DATA["incorrect_answers"]
  answers.append(TRIVIA_DATA["correct_answer"])
  random.shuffle(answers)
  correct_answer_index = answers.index(TRIVIA_DATA["correct_answer"])
  embed = discord.Embed(title="Trivia Alert!".format(TRIVIA_DATA["difficulty"]), description="Category: *{}* \n⠀\n> **{}**\n⠀".format(TRIVIA_DATA["category"],TRIVIA_DATA["question"]))
  thumb = discord.File("./data/{}.png".format(TRIVIA_DATA["difficulty"]))
  embed.set_thumbnail(url="attachment://{}.png".format(TRIVIA_DATA["difficulty"]))

  i = 0
  reactions = ["1️⃣","2️⃣","3️⃣","4️⃣"]
  TRIVIA_DATA["correct_emoji"] = reactions[correct_answer_index]
  for ans in answers:
    embed.add_field(name=reactions[i], value=ans, inline=False)
    i += 1
  embed.set_footer(text="React below with your answer!")
  channel = client.get_channel(891412585646268486)
  TRIVIA_MESSAGE = await channel.send(embed=embed, file=thumb)
  for react in reactions:
    await TRIVIA_MESSAGE.add_reaction(react)
  
@trivia_quiz.after_loop
async def end_trivia():
  global TRIVIA_ANSWERS, TRIVIA_DATA, TRIVIA_RUNNING, TRIVIA_MESSAGE
  print("Trivia complete!")
  rewards = {
    "easy" : 5,
    "medium" : 10,
    "hard" : 15
  }

  reward = rewards[TRIVIA_DATA["difficulty"]]
  correct_guessers = []
  for ans in TRIVIA_ANSWERS:
    if TRIVIA_ANSWERS[ans] == TRIVIA_DATA["correct_emoji"]:
      correct_guessers.append(get_player(ans))

  channel = client.get_channel(891412585646268486)
  embed = discord.Embed(title="Trivia Complete!", description="⠀\n⠀\nThe correct answer was:\n {} **{}**\n⠀\n⠀{}".format(TRIVIA_DATA["correct_emoji"], TRIVIA_DATA["correct_answer"], " "*47))
  
  if len(correct_guessers) > 0:
    for player in correct_guessers:
      embed.add_field(name=player["name"], value="`{} point(s)`".format(reward), inline=False)
      set_player_score(player["discord_id"], reward)
  else:
    embed.add_field(name="No winners!", value="Nobody got it this time.", inline=False)
    embed.set_footer(text="Adding {} point(s) to the jackpot".format(reward))
    increase_jackpot(reward)

  TRIVIA_DATA = {}
  TRIVIA_ANSWERS = {}
  TRIVIA_RUNNING = False
  TRIVIA_MESSAGE = None
  await channel.send(embed=embed)



@tasks.loop(seconds=31,count=1)
async def episode_quiz(non_trek=False, simpsons=False):
  global QUIZ_EPISODE, TMDB_IMG_PATH, LAST_SHOW, QUIZ_SHOW, PREVIOUS_EPS, LOG

  quiz_channel = client.get_channel(891412585646268486)
  
 
  headers = {'user-agent': 'Mozilla/5.0'}
  if non_trek:
    print("TV quiz!")
    shows = NON_TREK_SHOWS
  else:
    print("Trek quiz!")
    shows = TREK_SHOWS
  
  
  # todo: why did i do this
  if simpsons:
    selected_show = shows[2]
  else:
    if non_trek:
      selected_show = random.choice(shows)
    else:
      selected_show = random.choices(shows, tuple(TREK_WEIGHTS), k=1)
      selected_show = selected_show[0]
    
    # dont pick the same show again
    while selected_show == LAST_SHOW:
      if non_trek:
        selected_show = random.choice(shows)
      else:
        selected_show = random.choices(shows, tuple(TREK_WEIGHTS), k=1)
        selected_show = selected_show[0]
    LAST_SHOW = selected_show

  
  
  # for displaying to users
  show_name = selected_show[0]
  if not non_trek:
    show_name = "Star Trek: " + show_name

  show_id = selected_show[1]
  show_eps = selected_show[2]
  
  # don't pick the same episode as last time
  episode = random.choice(show_eps)
  
  if selected_show[0] in PREVIOUS_EPS.keys():
    while episode == PREVIOUS_EPS[selected_show[0]]:
      episode = random.choice(show_eps)
  PREVIOUS_EPS[selected_show[0]] = episode
  
  episode = episode.split("|")
  QUIZ_EPISODE = episode
  QUIZ_SHOW = selected_show[0] # current show

  episode_images = tmdb.TV_Episodes(show_id, episode[2], episode[3]).images()
  image = random.choice(episode_images["stills"])
  r = requests.get(TMDB_IMG_PATH + image["file_path"], headers=headers)
  with open('ep.jpg', 'wb') as f:
    f.write(r.content)
  
  await asyncio.sleep(2)
  LOG = [] # reset the log
  await quiz_channel.send(file=discord.File("ep.jpg"))
  await quiz_channel.send("Which episode of **__"+str(show_name)+"__** is this? <a:horgahn_dance:844351841017921597>")


@episode_quiz.after_loop
async def quiz_finished():
  global QUIZ_EPISODE, CORRECT_ANSWERS, FUZZ, EMOJI, QUIZ_SHOW, PREVIOUS_EPS, db
  await asyncio.sleep(1)
  print("Ending quiz...")
  quiz_channel = client.get_channel(891412585646268486)

  msg = "The episode title was: **{0}** (Season {1} Episode {2})\n".format(QUIZ_EPISODE[0].strip(), QUIZ_EPISODE[2], QUIZ_EPISODE[3])
  
  if len(CORRECT_ANSWERS) == 0:
    roll = random.randint(5,10)
    #todo: add random lose msgs
    msg += "Did you win? Hardly! Adding `{} point(s)` to the jackpot.".format(roll)
    increase_jackpot(roll)
  else:
    #todo: add random win msgs
    msg += "Chula! These crewmembers got it:\n"
    for c in CORRECT_ANSWERS:
      msg += "{} - {} points - {}\n".format(CORRECT_ANSWERS[c]["name"], CORRECT_ANSWERS[c]["points"], FUZZ[c])
  
  await quiz_channel.send(msg)
  
  # update the quiz stuff
  CORRECT_ANSWERS = {} # winners
  FUZZ = {} # fuzz report
  QUIZ_SHOW = False 
  QUIZ_EPISODE = False # the current episode

  print("Quiz finished!")



def roll_slot(slot_series, generate_image=True, filename="slot_results.png"):
  
  global SLOTS, SLOTS_RUNNING

  SLOTS_RUNNING = True
  slot_to_roll = SLOTS[slot_series]
  files = os.listdir(slot_to_roll["files"])
  results = []
  
  for i in range(3):
    results.append(random.choice(files))

  matching_results = [s.replace(".png", "") for s in results]

  silly_matches = []

  #print("match results", matching_results)

  for match_title in slot_to_roll["matches"]:
    #print(f"Checking {match_title}...")
    matches = slot_to_roll["matches"][match_title]
    #print("matches to check", matches)
    match_count = 0
    for m in matches:
      if m in matching_results:
        match_count += 1
    if match_count >= 2:
      silly_matches.append(match_title)
  
  if generate_image:
    image1 = Image.open(slot_to_roll["files"] + results[0]).resize((150,150))
    image2 = Image.open(slot_to_roll["files"] + results[1]).resize((150,150))
    image3 = Image.open(slot_to_roll["files"] + results[2]).resize((150,150))
    
  matching_chars = []
  result_set = set(results)
  matching_results = [s.replace(".png", "") for s in result_set]
  jackpot = False
  # print(set(slot_to_roll["custom_jackpot"]))
  # print(set(result_set))
  if len(result_set) == 1 or (set(slot_to_roll["custom_jackpot"]) == result_set):
    matching_chars.append(results[0].replace(".png", ""))
    jackpot = True

  if len(result_set) == 2:
    for r in result_set:
      if results.count(r) > 1:
        matching_chars.append(r.replace(".png", ""))

  logo = slot_series + "_logo.jpg"
  color = (0,0,0,100)

  if generate_image:
    get_concat_h_blank(image1,image2,image3,color,logo).save("./slot_results/"+str(filename)+".png")
  #print("silly matches", silly_matches)
  SLOTS_RUNNING = False
  return silly_matches, matching_chars, jackpot


def get_concat_h_blank(im1, im2, im3, color, logo):
  logo_location = "./slots/" + logo
  dst = Image.new('RGBA', (im1.width + im2.width + im3.width + 32, max(im1.height, im2.height, im3.height+16)), color)
  mask = Image.open(logo_location).convert('RGBA').resize((150,150))

  final_images = []
  originals = [im1, im2, im3]

  for i in range(1,3+1):
    img = Image.new('RGBA', (150,150), (0,0,0))
    img.paste(mask)
    img.paste(originals[i-1], (0,0), originals[i-1])
    final_images.append(img)

  dst.paste(final_images[0], (8, 8))
  dst.paste(final_images[1], (im1.width+16, 8))
  dst.paste(final_images[2], (im1.width+im2.width+24, 8))

  return dst




async def generate_profile_card(user, channel):
  player = get_player(user.id)
  template_image = "template.png"
  badge_image = None
  
  if player["profile_card"] != None:
    template_image = "template_{}.png".format(player["profile_card"].replace(" ", "_"))

  if player["profile_badge"] != None:
    badge_image = "./profiles/badges/{}".format(player["profile_badge"])

  image = Image.open(f"./profiles/{template_image}", "r")
  image = image.convert("RGBA")
  
  image_data = np.array(image)
  
  # replace white with profile color
  red, green, blue = image_data[:,:,0], image_data[:,:,1], image_data[:,:,2]
  r1, g1, b1 = 255,255,255
  r2, g2, b2 = user.color.to_rgb()
  mask = (red == r1) & (green == g1) & (blue == b1)
  image_data[:,:,:3][mask] = [r2, g2, b2]

  

  spins = player["spins"]
  jackpots = player["jackpots"]

  is_mobile = user.is_on_mobile()
  image = Image.fromarray(image_data)
  image = image.convert("RGBA")
  #color = ImageColor.getcolor(f"#{r}{g}{b}", "RGB")

  user_name = f"{user.display_name}".rjust(14, " ")
  user_join = user.joined_at.strftime("%Y.%m.%d")
  score = "SCORE: {}".format(player["score"])
  avatar = user.avatar_url_as(format='jpg', size=128)
  await avatar.save("./profiles/"+str(user.id)+"_a.jpg")

  name_font = ImageFont.truetype("lcars.ttf", 56)
  score_font = ImageFont.truetype("lcars.ttf", 32)
  spins_font = ImageFont.truetype("lcars.ttf", 24)
  date_font = ImageFont.truetype("lcars.ttf", 25)
  
  avatar_image = Image.open("./profiles/"+str(user.id)+"_a.jpg")
  avatar_image.resize((128,128))
  image.paste(avatar_image, (13, 142))

  if badge_image:
    badge_template = Image.new("RGBA", (600,400))
    badge = Image.open(badge_image)
    badge = badge.convert("RGBA")
    badge = badge.resize((50,50))
    badge_template.paste(badge, (542, 341))
    image = Image.alpha_composite(image, badge_template)
  
  if player["high_roller"] == 1:
    vip_template = Image.new("RGBA", (600, 400))
    vip_badge = Image.open("./profiles/badges/ferengi.png")
    vip_badge = vip_badge.resize((64,64))
    vip_template.paste(vip_badge, (20, 300))
    image = Image.alpha_composite(image, vip_template)
  
  draw = ImageDraw.Draw(image)
  
  draw.line([(0, 0), (600, 0)], fill=(r2,g2,b2), width=5)
  draw.text( (546, 15), user_name[0:16], fill="white", font=name_font, anchor="rt", align="right")
  draw.text( (324, 364), score, fill="white", font=score_font)
  draw.text ( (22, 85), "SPINS: {}".format(player["spins"]), fill="white", font=spins_font, align="left",stroke_fill="black", stroke_width=2)
  draw.text ( (22, 110), "JACKPOTS: {}".format(player["jackpots"]), fill="white", font=spins_font, align="left",stroke_fill="black", stroke_width=2)
  if is_mobile:
    draw.text( (20, 120), "AWAY TEAM", fill="white", font=score_font)
  draw.text( (60, 282), user_join, fill="white", font=date_font, spacing=0.1, stroke_fill="black", stroke_width=2)
  
  image.save("./profiles/"+str(user.id)+".png")
  discord_image = discord.File("./profiles/"+str(user.id)+".png")
  await channel.send(file=discord_image)


def get_player(discord_id):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor(dictionary=True)
  query.execute("SELECT * FROM users WHERE discord_id = %s", (discord_id,))
  player_data = query.fetchone()
  query.close()
  db.close()
  return player_data






def set_player_wager(discord_id, amt):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  amt = max(amt, 0)
  query = db.cursor()
  sql = "UPDATE users SET wager = %s WHERE discord_id = %s"
  vals = (amt, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()






def set_player_score(user, amt):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "SELECT score FROM users WHERE discord_id = %s"
  if type(user) is str:
    vals = (user,)
  else:
    vals = (user.id,)
  query.execute(sql, vals)
  player_score = query.fetchone()
  updated_amt = max(player_score[0] + amt, 0)
  if type(user) is str:
    sql = "UPDATE users SET score = %s WHERE discord_id = %s"
    vals = (updated_amt, user)
  else:
    sql = "UPDATE users SET score = %s, name = %s WHERE discord_id = %s"
    vals = (updated_amt, user.display_name, user.id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()






def increment_player_spins(discord_id):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "UPDATE users SET spins = spins + 1 WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()






def get_all_players():
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor(dictionary=True)
  query.execute("SELECT discord_id FROM users")
  users = []
  for user in query.fetchall():
    users.append(int(user["discord_id"]))
  query.close()
  db.close()
  return users
  





def get_jackpot():
  # get the current jackpot
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "SELECT jackpot_value FROM jackpots ORDER BY id DESC LIMIT 1"
  query.execute(sql)
  jackpot_amt = query.fetchone()
  db.commit()
  query.close()
  db.close()
  return jackpot_amt[0]



def get_all_jackpots():
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM jackpots WHERE winner IS NOT NULL ORDER BY id DESC LIMIT 10"
  query.execute(sql)
  jackpot_data = query.fetchall()
  query.close()
  db.close()
  return jackpot_data



def win_jackpot(winner, id):
  global JACKPOT
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  # update current jackpot row with winning data
  sql = "UPDATE jackpots SET winner=%s, time_won=NOW() ORDER BY id DESC LIMIT 1"
  vals = (winner,)
  query.execute(sql, vals)
  new_jackpot = "INSERT INTO jackpots (jackpot_value) VALUES (250)"
  query.execute(new_jackpot)
  update_user = "UPDATE users SET jackpots = jackpots + 1 WHERE discord_id = %s"
  user_vals = (id,)
  query.execute(update_user, user_vals)
  db.commit()
  query.close()
  db.close()
  




def increase_jackpot(amt):
  global JACKPOT
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "UPDATE jackpots SET jackpot_value = jackpot_value + %s ORDER BY id DESC LIMIT 1"
  vals = (amt,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
  JACKPOT = amt






def register_player(user):
  global ALL_PLAYERS
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "INSERT INTO users (discord_id, name, mention) VALUES (%s, %s, %s)"
  vals = (user.id, user.display_name, user.mention)
  query.execute(sql, vals)
  print("Registering user to DB: {} {} {}".format(user.id, user.display_name, user.mention))
  db.commit()
  query.close()
  db.close()
  ALL_PLAYERS.append(int(user.id))



def update_player_profile_card(discord_id, card):
  print(f"Updating user {discord_id} with new card: {card}")
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "UPDATE users SET profile_card = %s WHERE discord_id = %s"
  vals = (card, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()

def update_player_profile_badge(discord_id, badge):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "UPDATE users SET profile_badge = %s WHERE discord_id = %s"
  vals = (badge, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()



async def update_player_role(user, role):
  # add crew role
  if role == 894594667893641236:
    add_high_roller(user.id)

  role = discord.utils.get(user.guild.roles, id=role)
  if role not in user.roles:
    await user.add_roles(role)
  

def add_high_roller(discord_id):
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor()
  sql = "UPDATE users SET high_roller = 1 WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()



def get_high_scores():
  db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    database=DB_USER,
    password=DB_PASS,
  )
  query = db.cursor(dictionary=True)
  sql = "SELECT * FROM users ORDER BY score DESC LIMIT 25"
  query.execute(sql)
  scores = query.fetchall()
  return scores

  

client.run(os.getenv('TOKEN'))