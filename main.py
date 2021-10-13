import discord
from discord.ext import tasks
import os
import random
import tmdbsimple as tmdb
import requests
#import asyncio
import string
#import json
from PIL import Image, ImageFont, ImageDraw, ImageColor
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import mysql.connector
from tabulate import tabulate
import treys
from treys import evaluator
from trivia import trivia
import numpy as np
from treys import Card, Evaluator, Deck

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
POKER_GAMES = {}

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
      "custom_jackpots" : [
        ["caveman_riker", "spider_barclay", "devolved_worf"],
        ["merry_picard", "merry_q", "merry_vash"],
      ],
      "matches" : {
        "Villains" : ["armus", "pakled", "lore", "gul_madred", "romyarlin", "locutus", "ardra"],
        "Federation Captains" : ["picard", "jellico", "castillo"],
        "Olds" : ["pulaski", "jellico", "picard", "kevin"],
        "No Law to fit your Crime" : ["picard", "kevin"],
        "Music Box Torture" : ["kevin", "troi"],
        "Ensigns" : ["ro", "wesley", "robin_lefler"],
        "Omnipotent" : ["q", "armus", "kevin"],
        "Bros" : ["data", "lore"],
        "Doctors" : ["beverly", "pulaski"],
        "Drunkards" : ["obrien", "pulaski", "scotty"],
        "Rascals" : ["ro", "guinan", "picard", "keiko"],
        "Baby Delivery Team" : ["worf", "keiko"],
        "Robot Fuck Team" : ["data", "honry_tasha"],
        "Loving Couple" : ["obrien", "keiko"],
        "Best Friends" : ["geordi", "data"],
        "Jazz Funeral" : ["geordi", "ro"],
        "Engineers" : ["geordi", "obrien", "scotty"],
        "Nexus Travellers" : ["guinan", "picard"],
        "Related to Jack Crusher" : ["beverly", "wesley"],
        "Eggs for Breakfast" : ["riker", "pulaski", "worf"],
        "Humanity on Trial" : ["judge_q", "picard"],
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
        "\"I don't need your fantasy women\"" : ["riker", "q"],
        "Faces of Q": ["archeologist_q", "data_q", "french_q", "general_q", "merry_q", "q"],
        "Nottingham Friends" : ["merry_q", "merry_riker", "merry_troi", "merry_vash", "merry_worf", "merry_geordi", "merry_beverly", "merry_picard"],
        "Unsure about number of Lights" : ["gul_madred", "picard"],
        "Head Asplode" : ["remmick", "riker", "picard"],
        "Horny Mom" : ["lwaxana", "picard"],
        "Play Dom-Jot Hu-man" : ["afterlife_q", "cadet_picard"],
        "Heh, I don't believe this!" : ["angel_one_riker", "yar"],
        "I can show you the world..." : ["archeologist_q", "vash"],
        "Triangle of Jealousy" : ["picard", "vash", "beverly"],
        "Double the Consent" : ["riker", "thomas_riker"],
        "One-Time Visitors" : ["vash", "mendron", "maddox", "kevin", "hugh", "one_zero_zero_one", "okona", "scotty", "robin_lefler", "jellico", "dr_reyga"],
        "Murder She Wrote" : ["beverly", "dr_reyga"],
        "The First Duty" : ["nick_locarno", "wesley"],
        "Borgs!" : ["locutus", "hugh"],
        "Genesis" : ["caveman_riker", "spider_barclay", "devolved_worf"],
        "Measure of a Man" : ["maddox", "data"],
        "Doppelganger" : ["data", "data_q"],
        "Before and After" : ["wesley", "traveler_wesley"],
        "Faces of Yar" : ["temporal_tasha", "romyarlin", "yar", "horny_tasha"],
        "Let's do the Timewarp Again": ["temporal_tasha", "castillo"],
        "What Could Have Been" : ["temporal_tasha", "cadet_picard", "flute_picard"],
        "False Gods" : ["ardra", "kahless"],
        "Murder Chip Stress Test" : ["fajo", "data"],
        "Travel Who?" : ["the_traveler", "wesley"],
        "Jazz Trap" : ["riker", "one_zero_zero_one"],
        "Faces of Riker" : ["riker", "angel_one_riker", "caveman_riker", "merry_riker"],
        "Faces of Beverly" : ["beverly", "merry_beverly"],
        "Faces of Worf" : ["devolved_worf", "worf", "merry_worf"],
        "Faces of Picard" : ["cadet_picard", "picard", "merry_picard", "locutus"],
        "Those are Klingons?!" : ["worf", "kahless", "gowron"],
        "The Eyes have it" : ["gowron", "spider_barclay"],
        "His Eyes Uncovered!" : ["dathon", "picard"],
        "Suck Disk Averse" : ["robin_lefler", "wesley"],
        "Blueshirts" : ["maddox", "beverly", "pulaski", "troi"],
        "Lieutenants" : ["maddox", "barclay", "yar"]
        
      }
    },
    "DS9" : {
      "files" : "./slots/ds9/",
      "payout" : 1.5,
      "custom_jackpots" : [
        ["weyoun4", "weyoun5", "weyoun6"]
      ],
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
      "custom_jackpots" : [
        ["neelix", "tuvok", "tuvix"]
      ],
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
        "Double Doc Z" : ["doctor", "president_doctor", "teetime_doctor"],
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
      "custom_jackpots" : [
        ["musketeer_picard", "musketeer_data", "musketeer_geordi"]
      ],
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
        "Investigators" : ["sherlock_data", "spy_bashir", "sherrif_worf"],
        "Faces of Geordi" : ["sailor_laroge", "musketeer_geordi"],
        "Faces of Beverly": ["sailor_beverly", "doc_beverly"],
        "Faces of Worf" : ["duchamps_worf", "sailor_worf", "sherrif_worf"],
        "Faces of Data" : ["sherlock_data", "sailor_data", "musketeer_data"],
        "Faces of Picard" : ["dixon_hill", "musketeer_picard"],
        "Faces of Tuvok" : ["bartender_tuvok", "warship_tuvok"],
        "Faces of Troi" : ["troi_goddess_of_empathy", "durango_troi"],
        "Smoke Break" : ["anastasia_kira", "duchamps_worf", "gloria_guinan"],
        "Cute Bowtie" : ["bartender_tuvok", "duchamps_worf", "spy_bashir", "teetime_doctor"],
        "Trapped in a Cube" : ["moriarity", "regina_bartholomew"],
        "Redshirts" : ["ech", "warship_janeway", "warship_chakotay", "hippocrates_sisko"],
      }
    },
    "SHIPS": {
      "files" : "./slots/ships/",
      "payout" : 1,
      "custom_jackpots" : [
        ["enterprise_d", "borg_cube", "borg_sphere"]
      ],
      "matches" : {
        "First Contact" : ["enterprise_d", "borg_sphere"],
        "Q Who?" : ["enterprise_d", "borg_sphere"],
        "Entrepreneurs" : ["enterprise", "enterprise_d", "pikes_enterprise", "iss_enterprise"],
        "Ticks" : ["jemhadar_battleship", "jemhadar_fighter"],
        "Retro Classics" : ["discovery", "enterprise", "klingon_bird_of_prey", "pikes_enterprise"],
        "Something-Class" : ["constellation_class", "constitution_class", "galaxy_class", "intrepid_class", "miranda_class"],
        "Ships of Primetime" : ["enterprise", "enterprise_d", "voyager"],
        "Borgs!" : ["borg_cube", "borg_sphere"],
        "DS9 Dockers" : ["defiant", "ferengi_warship", "carassian_cruiser", "breen_warship"],
        "Pointy" : ["defiant", "hirogen", "orion_syndicate", "romulan_warbird", "vulcan_battlecruiser"],
        "Mysterious" : ["breen_warship", "orion_syndicate"],
        "Named but not the Star" : ["uss_reliant", "shenzou", "defiant"],
        "Badlands Battlers" : ["cardassian_cruiser", "maquis_raider"],
        "SCREE!!!" : ["klingon_bird_of_prey", "romulan_warbird"],
        "Dominion Lovers" : ["jemhadar_battleship", "jemhadar_fighter", "cardassian_cruiser", "breen_warship"],
        "Everyday Annoyance" : ["voyager", "borg_cube"],
        "WW2 Re-enactment" : ["hirogen", "voyager"],
        "Chakotay Go Home" : ["maquis_raider", "voyager"],
        "The Die is Cast" : ["defiant", "jemhadar_battleship", "jemhadar_fighter"],
        "Disco Inferno" : ["shenzou", "discovery", "pikes_enterprise"]
      }
    },
    "TEST" : {
      "files" : "./slots/test/",
      "custom_jackpots" : [],
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


PROFILE_CARDS = ["Archer", "Bashir", "Boimler", "Brunt", "Data", "EMH", "Garak", "Gowron", "Janeway", "Jeffrey Combs", "Mariner", "Mark Twain", "Picard", "Q", "Quark", "Rain", "Ransom", "Rutherford", "Seven of Nine", "Shran", "Sisko", "Spock", "Tilly", "Weyoun", "Worf"]
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


POKER_PAYOUTS = {
  "high card" : 0,
  "pair" : 1,
  "two pair" : 1.5,
  "three of a kind" : 2,
  "straight" : 4,
  "flush" : 5,
  "full house" : 6,
  "four of a kind" : 10,
  "royal flush" : 1000
}


SLOTS_CHANNEL = 891412391026360320
QUIZ_CHANNEL = 891412585646268486
CONVO_CHANNEL = 891412924193726465
SHOP_CHANNEL = 895480382680596510
TEST_CHANNEL = 897126055289159711
CAFE_CHANNEL = 892527375181570059
POKER_CHANNEL = 897517722227855422


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
  global TRIVIA_ANSWERS, POKER_GAMES

  if payload.user_id != client.user.id:
    # poker reacts
    if payload.message_id in POKER_GAMES:
      if payload.user_id == POKER_GAMES[payload.message_id]["user"]:
        if payload.emoji.name == "✅":
          await resolve_poker(payload.message_id)
      else:
        user = await client.fetch_user(payload.user_id)
        await POKER_GAMES[payload.message_id]["message"].remove_reaction(payload.emoji, user)
        

    # trivia reacts
    if TRIVIA_MESSAGE and payload.message_id == TRIVIA_MESSAGE.id:
      
        #emoji = await discord.utils.get(TRIVIA_MESSAGE.reactions, emoji=payload.emoji.name)
        user = await client.fetch_user(payload.user_id)
        await TRIVIA_MESSAGE.remove_reaction(payload.emoji, user)
        TRIVIA_ANSWERS[payload.user_id] = payload.emoji.name






@client.event
async def on_message(message:discord.Message):
  
  global QUIZ_EPISODE, CORRECT_ANSWERS, FUZZ, EMOJI, LOG, SLOTS_RUNNING, ALL_PLAYERS, POKER_GAMES
  
  

  if message.author == client.user:
    return

  if message.channel.id not in [888090476404674570, CAFE_CHANNEL, POKER_CHANNEL, SLOTS_CHANNEL, QUIZ_CHANNEL, CONVO_CHANNEL, SHOP_CHANNEL, TEST_CHANNEL, 696430310144999554, 847142552699273257]:
    return

  if int(message.author.id) not in ALL_PLAYERS:
    register_player(message.author)

  if message.content.lower().startswith("!profile"):
    await generate_profile_card(message.author, message.channel)

  if message.channel.id in [CAFE_CHANNEL, TEST_CHANNEL] and message.content.lower().startswith("!ping"):
    await message.channel.send("Pong! {}ms".format(round(client.latency * 1000)))

  if message.channel.id == POKER_CHANNEL and message.content.lower().startswith('!poker'):

    # don't let players start 2 poker games
    poker_players = []
    for c in POKER_GAMES:
      poker_players.append(POKER_GAMES[c]["user"])

    if message.author.id in poker_players:
      await message.channel.send("{}: you have a poker game running already! Be patient!".format(message.author.mention))

    else:

      player = get_player(message.author.id)
      if player["score"] >= player["wager"]:
        
        set_player_score(str(message.author.id), -player["wager"])
        deck = Deck()
        hand = deck.draw(5) # draw 5 cards
        
        # generate hand image
        hand_image = await generate_poker_image(hand, message.author.id)
        hand_file = discord.File(hand_image, filename=str(message.author.id)+".png")
        
        embed = discord.Embed(
          title="{}'s Poker hand".format(message.author.display_name),
          color=discord.Color(0x1abc9c),
          description="{}: Starting a round of poker with a `{}` point wager. Here's your hand!".format(message.author.mention, player["wager"]),
        )

        embed.set_image(url="attachment://{0}".format(str(message.author.id)+".png"))
        embed.set_footer(text="React below with the numbers to discard the corresponding card.\n\nUse the 🤑 react to double your bet.\nUse the ✅ react to draw.")
        
        pmessage = await message.channel.send(embed=embed, file=hand_file)

        poker_reacts = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "🤑", "✅"]
        for p in poker_reacts:
          await pmessage.add_reaction(p)
        
        POKER_GAMES[pmessage.id] = { 
          "user" : message.author.id, 
          "hand" : hand, 
          "discards": [False,False,False,False,False], 
          "deck" : deck, 
          "message": pmessage, 
          "mention" : message.author.mention, 
          "username": message.author.display_name,
          "wager" : player["wager"]
        }

      else:

        await message.channel.send("{}: You don't have enough points to play! Try lowering your wager or playing the quiz games.".format(message.author.mention))


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
`!shop roles` - list all the roles for sale
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
`!slots ds9` - run a specific slot machine! (try `tng` `ds9` or `voy` or `holodeck` or `ships`)
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
    if message.channel.id == POKER_CHANNEL:
      msg = '''
**POKER INFO**
Just plain, basic poker -- Riker style.

**COMMANDS**
`!poker` - play a round
`!setwager 1` set your wager to 1! try a different number!

**PAYOUTS**
'''
      for p in POKER_PAYOUTS:
        msg += "{} - x{}\n".format(p.title(), POKER_PAYOUTS[p])


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

      if message.content.lower().replace("!testslots ", "") in ["ds9", "tng", "voy", "holodeck", "ships"]:
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
    
    if message.content.lower().replace("!slots ", "") in ["ds9", "tng", "voy", "holodeck", "ships"]:
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


  if message.channel.id in [SLOTS_CHANNEL, POKER_CHANNEL] and message.content.lower().startswith("!setwager"):

    min_wager = 1
    max_wager = 25
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
    


  if message.channel.id in [CONVO_CHANNEL, 696430310144999554, 847142552699273257] and message.content.lower().startswith("!randomep"):
    series = random.choice(TREK_SHOWS)
    ep = random.choice(series[2]).split("|")
    series_name = series[0]
    ep_title = ep[0]
    ep_season = ep[2]
    ep_episode = ep[3]
    msgs = ["Picking an episode from all Trek, everywhere. <:kevin_flirty:760229418676912168>", "Random Trek episode for you! <a:tomsmart:814897427370475580>", "Here's a random Trek episode! <:quark_smile_happy:871831721031630868>"]
    msg = "{} - {}\n> *{}* - **{}** - (Season {} Episode {})".format(message.author.mention, random.choice(msgs), series_name, ep_title, ep_season, ep_episode)
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

  

  if message.content.lower().startswith('!scores') and message.channel.id in [QUIZ_CHANNEL, SLOTS_CHANNEL, SHOP_CHANNEL, TEST_CHANNEL, POKER_CHANNEL]:
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
    maybe_newline = ""
    if i == 3:
      maybe_newline = "\n ** ** \n"
    embed.add_field(name="** **", value="{}: {} {}".format(reactions[i],ans,maybe_newline), inline=False)
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
  
  #await asyncio.sleep(2)
  LOG = [] # reset the log
  await quiz_channel.send(file=discord.File("ep.jpg"))
  await quiz_channel.send("Which episode of **__"+str(show_name)+"__** is this? <a:horgahn_dance:844351841017921597>")


@episode_quiz.after_loop
async def quiz_finished():
  global QUIZ_EPISODE, CORRECT_ANSWERS, FUZZ, EMOJI, QUIZ_SHOW, PREVIOUS_EPS, db
  #await asyncio.sleep(1)
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
  

  #print(results)
  
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
  if len(result_set) == 1:
    matching_chars.append(results[0].replace(".png", ""))
    jackpot = True

  for jackpot_match in slot_to_roll["custom_jackpots"]:
    if set(jackpot_match) == set(matching_results):
      jackpot = True

  if len(result_set) == 2:
    for r in result_set:
      if results.count(r) > 1:
        matching_chars.append(r.replace(".png", ""))

  logo = slot_series + "_logo.png"
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

  

  top_role = user.top_role
  image = Image.fromarray(image_data)
  image = image.convert("RGBA")
  #color = ImageColor.getcolor(f"#{r}{g}{b}", "RGB")

  user_name = f"{user.display_name}"
  user_name_encode = user_name.encode("ascii", errors="ignore")
  user_name = user_name_encode.decode().strip()
  
  top_role_name = top_role.name.encode("ascii", errors="ignore")
  top_role = top_role_name.decode().strip()

  user_join = user.joined_at.strftime("%Y.%m.%d")
  score = "SCORE: {}".format(player["score"])
  avatar = user.avatar_url_as(format='jpg', size=128)
  await avatar.save("./profiles/"+str(user.id)+"_a.jpg")

  name_font = ImageFont.truetype("lcars3.ttf", 56)

  rank_font = ImageFont.truetype("lcars3.ttf", 26)
  spins_font = ImageFont.truetype("lcars3.ttf", 20)
  rank_value_font = ImageFont.truetype("lcars3.ttf", 28)
  spins_value_font = ImageFont.truetype("lcars3.ttf", 24)

  avatar_image = Image.open("./profiles/"+str(user.id)+"_a.jpg")
  avatar_image.resize((128,128))
  image.paste(avatar_image, (12, 142))

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
    vip_template.paste(vip_badge, (56, 327))
    image = Image.alpha_composite(image, vip_template)
  
  draw = ImageDraw.Draw(image)
  
  draw.line([(0, 0), (600, 0)], fill=(r2,g2,b2), width=5)

  draw.text( (546, 15), user_name[0:15], fill="white", font=name_font, anchor="rt", align="right")

  draw.text( (62, 83), "RANK", fill="black", font=rank_font, align="right", anchor="rt")
  draw.text( (77, 83), top_role, fill="white", font=rank_value_font, anchor="lt", align="left")
  draw.text( (62, 114), "JOINED", fill="black", font=rank_font, align="right", anchor="rt")
  draw.text( (77, 113), user_join, fill="white", font=rank_value_font, anchor="lt", align="left")

  draw.text( (65, 278), "SPINS", fill="black", font=spins_font, align="right", anchor="rt")
  draw.text( (73, 276), str(player["spins"]), fill="white", font=spins_value_font, anchor="lt", align="left")
  draw.text( (65, 304), "JACKPOTS", fill="black", font=spins_font, align="right", anchor="rt")
  draw.text( (73, 302), str(player["jackpots"]), fill="white", font=spins_value_font, anchor="lt", align="left")
  
  draw.text( (321, 366), score, fill="white", font=rank_value_font)
  
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




async def resolve_poker(game_id):
  global POKER_GAMES
  channel = client.get_channel(POKER_CHANNEL)
  # handle discards, build new hand
  poker_game = POKER_GAMES[game_id]
  wager = poker_game["wager"]
  user_id = poker_game["user"]
  hand = poker_game["hand"]
  deck = poker_game["deck"]
  message = await channel.fetch_message(game_id)
  reactions = message.reactions
  doubled = False
  
  #print("reactions", reactions)
  

  # count reactions, set discards
  # done this way to allow the user to toggle draws
  
  discard_reactions = {
    "1️⃣" : 0,
    "2️⃣" : 1,
    "3️⃣" : 2,
    "4️⃣" : 3,
    "5️⃣" : 4
  }

  for r in reactions:
    if r.emoji == "✅": # don't count that last "draw" reaction
      continue
    users = await r.users().flatten()
    # we only want to count the game player's reactions
    for m in users:
      if m.id == user_id and r.emoji in discard_reactions:
        poker_game["discards"][discard_reactions[r.emoji]] = True
      if m.id == user_id and r.emoji == "🤑":
        doubled = True
        wager = wager * 2
  
  # re-draw hand as needed
  i = 0
  for d in poker_game["discards"]:
    if d == True:
      hand[i] = deck.draw(1)
    i += 1
  
  if doubled:
    # if they doubled their bet, take that extra out now
    set_player_score(str(user_id), -poker_game["wager"])

  # check hand
  evaluator = Evaluator()
  score = evaluator.evaluate(hand, [])
  hand_class = evaluator.get_rank_class(score)
  str_score = evaluator.class_to_string(hand_class)
  if score == 1:
    str_score = "Royal Flush"
  score_rank = str_score.lower()
  profit = round(POKER_PAYOUTS[score_rank] * wager)
  if profit != 0:
    set_player_score(str(poker_game["user"]), profit)
  

  # get new hand image
  hand_image = await generate_poker_image(hand, user_id)
  file = discord.File(hand_image, filename=str(poker_game["user"])+".png")
  wager_str = "Total wager: `{}`"
  if doubled:
    wager_str = "\n*You doubled your wager!* Total wager: `{}`\n"
  wager_str = wager_str.format(wager)

  embed = discord.Embed(
    title="{}'s Final Poker hand".format(poker_game["username"]),
    color=discord.Color(0x1abc9c),
    description="{}: Here's your final hand: **{}**\n{}".format(poker_game["mention"], str_score, wager_str),
  )

  embed.set_image(url="attachment://{0}".format(str(poker_game["user"])+".png"))
  embed.set_footer(text="Your profit: {}".format(profit-wager))
  
  # send results
  await channel.send(embed=embed, file=file)

  # handle player score
  POKER_GAMES.pop(game_id)


async def generate_poker_image(hand:treys.Card, filename:str):
  channel = client.get_channel(POKER_CHANNEL)
  base = Image.new("RGBA", (1120,350), (0,0,0,0))
  value_font = ImageFont.truetype("lcars3.ttf", 64)
  smaller_font = ImageFont.truetype("lcars3.ttf", 32)
  suit_map = {
    "c" : "club.png",
    "d" : "diamond.png",
    "h" : "heart.png",
    "s" : "spade.png"
  }

  i = 0

  for h in hand:
    # each card needs an image and text
    # then paste it on the card base
    card_template = Image.open("./cards/card-overlay.png")
    card_base = Image.new("RGBA", (200, 300), "black")
    draw = ImageDraw.Draw(card_template)

    face_path = ""
    image_path = ""
    color = "black"

    value,suit = list(Card.int_to_str(h))
    if suit == "h":    
      image_path = "./cards/basic/hearts/"
      color = "red"
    if suit == "d":
      image_path = "./cards/basic/diamonds/"
      color = "red"
    if suit == "c":
      image_path = "./cards/basic/clubs/"
    if suit == "s":
      image_path = "./cards/basic/spades/"
    if value == "T":
      value = "10"

    if value == "J":
      face_path = "jack.png"
    if value == "Q":
      face_path = "queen.png"
    if value == "K":
      face_path = "king.png"
    if value == "A":
      face_path = "ace.png"
    if value.isnumeric():
      face_path = "{}.png".format(value)

    suit_image = Image.open("./cards/suits/{}".format(suit_map[suit]))
    suit_image = suit_image.resize((50,50))

    if face_path != "":
      face_image = Image.open(f"{image_path}{face_path}")
      card_base.paste(face_image, (0,0))

    draw.text( (45,62), value, color, value_font, align="center", anchor="ms")
    #draw.text( (16,54), suit_map[suit], color, value_font)
    card_template.paste(suit_image, (21, 86), mask=suit_image)
    #draw.text( (163, 268), value, color, smaller_font)
    # add face card if necessary
    card_base.paste(card_template, (0,0), mask=card_template)
    margin = 10
    base.paste(card_base, (200*i+(margin*i), 13))
    i += 1

  base.save(f"./cards/users/{filename}.png")
  return f"./cards/users/{filename}.png"
  
  #await channel.send(file=file)
   
  

client.run(os.getenv('TOKEN'))