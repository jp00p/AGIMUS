from .common import *
from .jackpot import *
import math

# slots() - Entrypoint for !slots command
# message[required]: discord.Message
# This function is the main entrypoint of the !slots command
# The goal is to display three random images and determine if
# those images are related in any special way
async def slots(message:discord.Message):
  print("> !SLOTS")
  
  # Load slots data
  f = open(config["commands"]["slots"]["data"])
  SLOTS = json.load(f)
  f.close()
  
  # Use the option the user selected or pick a random show
  if message.content.lower().replace("!slots ", "") in config["commands"]["slots"]["parameters"][0]["allowed"]:
    show = message.content.lower().replace("!slots ", "").upper()
  else:
    show = random.choice(["TNG", "DS9", "VOY", "HOLODECK"])
  
  logger.info("show: " + show)

  # player data  
  id = message.author.id
  player = get_player(id)
  logger.debug(player)
  free_spin = player["spins"] < 5 # true or false
  wager = player["wager"]
  score_mult = wager
  
  # if they have less than 5 total spins, give em a free one
  if free_spin:
    wager = 0
    score_mult = 1
  
  total_rewards = 0
  themed_payout = SLOTS[show]["payout"]
  logger.info("payout" + str(themed_payout))
  
  if player["score"] < wager and not free_spin:
    # if they don't have enough bits to play
    await message.channel.send(f"You need at least {wager} point(s) to spin! Play the quiz to get more points or try changing your wager")
  else:
    increment_player_spins(id)
  
  spinnin = [
    "All I do is *slots slots slots*!", 
    "Time to pluck a pigeon!", 
    "Rollin' with my homies...", 
    "It's time to spin!", 
    "Let's roll.", 
    "ROLL OUT!", 
    "Get it player.", 
    "Go go gadget slots!", 
    "Activating slot subroutines!", 
    "Reversing polarity on Alpha-probability particle emitters.",
  ] 
  # pick a spin message
  spin_msg = message.author.mention + ": "
  spin_msg += random.choice(spinnin)
  
  # build the rest of the message
  if free_spin:
    spin_msg += " **This one's on the house!** (after 5 free spins, they will cost you points!)"
  else:
    spin_msg += f" Spending `{wager}` of your points!"
  
  spin_msg += " This is spin #{0} for you.".format(player["spins"]+1)
  await message.channel.send(spin_msg)
  
  # roll the slots!
  silly_matches, matching_chars, jackpot, symbol_matches = roll_slot(show, SLOTS[show], filename=str(message.author.id))
  file = discord.File("./images/slot_results/{0}.png".format(message.author.id), filename=str(message.author.id)+".png")
  match_msg = message.author.mention + "'s spin results: \n"
  
  if len(symbol_matches) > 0:
    match_msg += "**"+symbol_matches[0].upper()+":** "
    match_msg += "{0} points!\n".format(round(score_mult * symbol_matches[1]))
    total_rewards += int(math.ceil(score_mult * symbol_matches[1]))

  if len(silly_matches) > 0:
    match_msg += "**Discovered Bits: ** "
    match_msg += "; ".join(silly_matches)
    match_msg += " `" + str(len(silly_matches)*score_mult) + " point(s)`\n"
    total_rewards += len(silly_matches) * score_mult

  # matching characters (transporter clones)  
  if len(matching_chars) > 0:
    match_msg += "**Transporter clones: ** "
    match_msg += ", ".join(matching_chars).replace("_", " ").title()
    match_msg += " `({0} points)`\n".format(3 * score_mult)
    total_rewards += 3 * score_mult
  
  if jackpot:
    jackpot_amt = get_jackpot()
    total_rewards += round(jackpot_amt * themed_payout)
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
    match_msg += "\n "+message.author.mention+" wins the pot of: `{0}` ...multiplied by the slots' jackpot payout rate of x{1}... **for a total winnings of `{2}`**\n\nJackpot has been reset to: **`250`**\n\n".format(jackpot_amt, themed_payout, round(jackpot_amt*themed_payout))
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


# testslots() - Entrypoint for !testslots command
# message[required]: discord.Message
# This function is the main entrypoint of the !testslots command
# and will run the !slots command 100,000 times to gather statistics
async def testslots(message:discord.Message):
  f = open(config["commands"]["testslots"]["data"])
  allowlist = json.load(f)
  f.close()

  if message.author.id in allowlist:
    f = open(config["commands"]["slots"]["data"])
    SLOTS = json.load(f)
    f.close()

    if message.content.lower().replace("!testslots ", "") in ["ds9", "tng", "voy", "holodeck", "ships"]:
      show = message.content.lower().replace("!testslots ", "").upper()
    else:
      show = "TNG"

    spins = 1000
    spin_msg = f"Testing {show} slots with {spins} spins! Nothing is going to work until this finishes sorry :)"
    await message.channel.send(spin_msg)
    jackpots = 0
    wins = 0
    profitable_wins = 0
    profits = []

    for i in range(spins):
      silly,clones,jackpot = roll_slot(show, SLOTS[show], generate_image=False)
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

# increment_player_spins(discord_id)
# discord_id[required]: int
# This function increases the number of a
# user's spin value by one
def increment_player_spins(discord_id):
  db = getDB()
  query = db.cursor()
  sql = "UPDATE users SET spins = spins + 1 WHERE discord_id = %s"
  vals = (discord_id,)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()


# roll_slot(slot_series, slot_to_roll, generate_image=True, filename="slot_results.png")
# slot_series[required]: string
# slot_to_roll[required]: object
# generate_image[optional]: bool (default: true)
# filename[optional]: string (default: slot_results.png)
# This function picks three random images from a target show
# and returns categories of matches (silly, character and jackpot)
def roll_slot(slot_series, slot_to_roll, generate_image=True, filename="slot_results.png"):

  # pull out image files for selected slot
  files = os.listdir(slot_to_roll["files"])
  results = []

  # slot machine symbols - standard across all slots
  # name, weight, payout
  symbols = {
    "cherry": [10000, 1.25],
    "bell": [7000, 1.75],
    "grapes": [6000, 2],
    "lemon": [5000, 4],
    "plum": [4000, 5],
    "watermelon": [3000, 6],
    "horseshoe": [2000, 10],
    "clover": [1000, 20],
    "coin": [500, 100],
    "diamond": [250, 500],
    "heart": [1, 10000]
  }

  roll_weights = []
  for symbol in symbols:
    roll_weights.append(symbols[symbol][0])
  symbol_roll = random.choices(list(symbols.keys()), weights=roll_weights, k=3)
  symbol_matches = set(symbol_roll)
  symbol_result = []

  # check the symbols winnings  
  if len(symbol_matches) == 1:
    win_sym = list(symbol_matches)[0]
    win_string = f"3 {win_sym}"
    symbol_result = [win_string, symbols[win_sym][1]]
  elif len(symbol_matches) == 2:
    if list(symbol_matches).count("cherry") == 2:
      # 2 cherries in the result give them their winnings back
      symbol_result = ["2 Cherries", 1]

  # pick 3 random themed slots
  for i in range(3):
    results.append(random.choice(files))
  
  matching_results = [s.replace(".png", "") for s in results]
  silly_matches = []
  #print("match results", matching_results)
  
  for match_title in slot_to_roll["matches"]:
    # check the silly/bits-based matches
    matches = slot_to_roll["matches"][match_title]   
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
  color = (0,0,0,100) # black bg
  
  if generate_image:
    generate_slot_image(image1,image2,image3,symbol_roll,color,logo).save("./images/slot_results/"+str(filename)+".png")

  return silly_matches, matching_chars, jackpot, symbol_result


# generate_slot_image(im1, im2, im3, color, logo)
# im1[required]: object
# im2[required]: object
# im3[required]: object
# symbols[required]: list of symbols
# color[required]: array of ints
# logo[required]: string
# returns an Image object
# This function combines three images and a logo to display to the user
def generate_slot_image(im1, im2, im3, symbols, color, logo):
  logo_location = "./images/slots/" + logo
  
  # destination image
  dst = Image.new('RGBA', (im1.width + im2.width + im3.width + 32, max(im1.height, im2.height, im3.height+16)), color)
  
  # mask image
  mask = Image.open(logo_location).convert('RGBA').resize((150,150))

  final_images = []
  originals = [im1, im2, im3]

  # paste the mask and the image on to the background
  for i in range(1,3+1):
    img = Image.new('RGBA', (150,150), (0,0,0))
    img.paste(mask)
    img.paste(originals[i-1], (0,0), originals[i-1])
    final_images.append(img)

  # combine the composite with the destination
  dst.paste(final_images[0], (8, 8))
  dst.paste(final_images[1], (im1.width+16, 8))
  dst.paste(final_images[2], (im1.width+im2.width+24, 8))

  symbols_positions = [10,176,334]

  for i,s in enumerate(symbols):
    simg = Image.open("./images/slot_symbols/"+s+".png")
    dst.paste(simg, (symbols_positions[i], 150-simg.height), simg)

  return dst
