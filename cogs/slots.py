import math

from common import *
from utils.check_channel_access import access_check

command_config = config["commands"]["slots spin"]

# Set up Slot Choices
slot_choices = []
for show in command_config["parameters"][0]["allowed"]:
  slot_option = discord.OptionChoice(
    name=show,
    value=show.upper()
  )
  slot_choices.append(slot_option)

class Slots(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.slot_results_dir = f"{ROOT_DIR}/images/slot_results/"
    if not os.path.exists(self.slot_results_dir):
      os.makedirs(self.slot_results_dir)

    # self.bot.application_command(name="spin", cls=discord.SlashCommand)(self.spin)

  # Create slots Slash Command Group
  slots = discord.SlashCommandGroup("slots", "Slots Commands!")

  @slots.command(
    name="spin",
    description="Spin a random or a show-specific Slot Machine!"
  )
  @option(
    name="show",
    description="Which Show?",
    required=False,
    choices=slot_choices
  )
  @commands.check(access_check)
  async def spin(self, ctx:discord.ApplicationContext, show:str):
    logger.info(f"{Fore.YELLOW}Rolling the slots!{Fore.RESET}")
    
    # Load slots data
    f = open(config["commands"]["slots spin"]["data"])
    SLOTS = json.load(f)
    f.close()

    logger.info(f"SLOTS: {pprint(SLOTS)}")
    
    # Use the option the user selected or pick a random show
    if show not in command_config["parameters"][0]["allowed"]:
      show = random.choice(["TNG", "DS9", "VOY", "HOLODECK"])
    
    logger.info(f"{Fore.LIGHTRED_EX}Rolling slot theme:{Fore.RESET} {Style.BRIGHT}{show}{Style.RESET_ALL}")
    # player data  
    player_id = ctx.author.id
    player = get_user(player_id)
    #logger.info(player)
    free_spin = player["spins"] < 5 # true or false
    wager = player["wager"]
    score_mult = wager
    
    # if they have less than 5 total spins, give em a free one
    if free_spin:
      wager = 0
      score_mult = 1
    
    total_rewards = 0
    themed_payout = SLOTS[show]["payout"]
    #logger.info("payout" + str(themed_payout))

    if player["score"] < wager and not free_spin:
      # if they don't have enough bits to play
      await ctx.respond(embed=discord.Embed(
        title="Not Enough Points!",
        description=f"You need at least {wager} point(s) to spin! Play the quiz to get more points or try changing your wager"
      ))
      return
    else:
      self.increment_player_spins(player_id)

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
    spin_msg = f"{ctx.author.mention}: "
    # build the rest of the message
    if free_spin:
      spin_msg += "**This one's on the house!** (after 5 free spins, they will cost you points!)"
    else:
      spin_msg += f"Spending `{wager}` of your points!"

    spin_embed = discord.Embed(
      title=random.choice(spinnin).title(),
      description=spin_msg,
      color=discord.Color.gold()
    )
    spin_embed.set_footer(text=f"This is spin #{player['spins']+1} for you.")
    await ctx.respond(embed=spin_embed)

    # roll the slots!
    silly_matches, matching_chars, jackpot, symbol_matches = self.roll_slot(show, SLOTS[show], filename=str(ctx.author.id))
    try:
      file = discord.File(f"{self.slot_results_dir}{player_id}.png", filename=str(ctx.author.id)+".png")
    except:
      logger.info(f"{Fore.RED}Error generating discord file placeholder{Fore.RESET}")
    match_msg = f"{ctx.author.mention}'s spin results: \n\n"

    if len(symbol_matches) > 0:
      match_msg += "**"+symbol_matches[0].upper()+":** "
      match_msg += "`{0} points`\n".format(round(score_mult * symbol_matches[1]))
      total_rewards += int(math.ceil(score_mult * symbol_matches[1]))

    if len(silly_matches) > 0:
      match_msg += "**Discovered Bits: ** "
      match_msg += "; ".join(silly_matches)
      match_msg += f" `{str(len(silly_matches)*score_mult)} point(s)`\n"
      total_rewards += len(silly_matches) * score_mult

    # matching characters (transporter clones)  
    if len(matching_chars) > 0:
      match_msg += "**Transporter clones: ** "
      match_msg += ", ".join(matching_chars).replace("_", " ").title()
      match_msg += " `({0} points)`\n".format(3 * score_mult)
      total_rewards += 3 * score_mult

    title = "Results"
    embed_color = discord.Color(0x1abc9c)
    if jackpot:
      title = "**JACKPOT!!!**"
      embed_color = discord.Color.dark_gold()

      jackpot_amt = self.get_jackpot()
      total_rewards += round(jackpot_amt * themed_payout)
      match_msg += "\n "+ctx.author.mention+" wins the pot of: `{0}` ...multiplied by the slots' jackpot payout rate of x{1}... **for a total winnings of `{2}`**\n\nJackpot has been reset to: **`250`**\n\n".format(jackpot_amt, themed_payout, round(jackpot_amt*themed_payout))
      win_jackpot(ctx.author.display_name, ctx.author.id)
      jackpot_embed = discord.Embed(color=embed_color)
      jackpot_embed.set_image(url="https://i.imgur.com/S7Pv9lM.jpg")
      await ctx.respond(embed=jackpot_embed)

    if total_rewards != 0:
      # WIN
      total_profit = total_rewards - wager
      match_msg += f"**Total Profit:** `{total_profit} point(s)`.\n"
      embed = discord.Embed(
        title=title,
        color=embed_color,
        description=match_msg,
      )
      embed.set_image(url="attachment://{0}.png".format(ctx.author.id))
      embed.set_footer(text="{}'s score: {}".format(player["name"], player["score"]+total_profit))
      set_player_score(ctx.author, total_profit)
      await ctx.respond(embed=embed, file=file)

    else:
      # LOSS
      increase_jackpot(score_mult)
      set_player_score(ctx.author, -wager)
      loser = ["No dice!", "Bust!", "No matches!", "Better luck next time!", "Sad trombone!", "You didn't win!", "We have no prize to fit your loss -- ", "You may have won in the mirror universe, but not here!", "Sensors detect no matches.", "JACKP-- no wait, that's a loss.", "Close, but no cigar.", "Not a win!", "You would have won if it were opposite day!"]
      embed = discord.Embed(
        title="Results",
        color=discord.Color(0xe74c3c),
        description="{0}: {1}\n\n`{2}` point(s) added to the jackpot, increasing its bounty to `{3}`.".format(ctx.author.mention, random.choice(loser), score_mult, self.get_jackpot()),
      )
      embed.set_footer(text="{}'s score: {}".format(player["name"], player["score"]-wager))
      embed.set_image(url="attachment://{0}.png".format(ctx.author.id))
      await ctx.respond(embed=embed, file=file)

  # increment_player_spins(discord_id)
  # discord_id[required]: int
  # This function increases the number of a
  # user's spin value by one
  def increment_player_spins(self, discord_id):
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
  def roll_slot(self, slot_series, slot_to_roll, generate_image=True, filename="slot_results.png"):

    # pull out image files for selected slot
    files = os.listdir(f"{ROOT_DIR}{slot_to_roll['files']}")
    results = []

    # slot machine symbols - standard across all slots
    # name, weight, payout
    symbols = {
      "cherry": [10000, 1.25],
      "bell": [7500, 1.75],
      "grapes": [6500, 2],
      "lemon": [5500, 4],
      "plum": [4500, 5],
      "watermelon": [3500, 6],
      "horseshoe": [2000, 10],
      "clover": [1000, 20],
      "coin": [500, 100],
      "diamond": [250, 500],
      "heart": [100, 10000]
    }

    roll_weights = []
    for symbol in symbols:
      roll_weights.append(symbols[symbol][0])
    symbol_roll = random.choices(list(symbols.keys()), weights=roll_weights, k=3)
    symbol_matches = set(symbol_roll)
    symbol_result = []

    fruits = ["cherry", "grapes", "lemon", "plum", "watermelon"]

    # check the symbols winnings  
    if len(symbol_matches) == 1:
      win_sym = list(symbol_matches)[0]
      win_string = f"3 {win_sym}"
      symbol_result = [win_string, symbols[win_sym][1]]
    elif list(symbol_roll).count("cherry") == 2:
      # 2 cherries in the result give them their winnings back
      symbol_result = ["2 Cherries", 1]
    elif len(symbol_matches) == 3 and all(fruit in fruits for fruit in list(symbol_roll)):
      # if they get 3 different fruits
      symbol_result = ["Fruit Salad", 1.5]

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
      image1 = Image.open(f"{ROOT_DIR}{slot_to_roll['files']}" + results[0]).resize((150,150))
      image2 = Image.open(f"{ROOT_DIR}{slot_to_roll['files']}" + results[1]).resize((150,150))
      image3 = Image.open(f"{ROOT_DIR}{slot_to_roll['files']}" + results[2]).resize((150,150))


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
      self.generate_slot_image(image1,image2,image3,symbol_roll,color,logo).save(f"{ROOT_DIR}/images/slot_results/{str(filename)}.png")

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
  def generate_slot_image(self, im1, im2, im3, symbols, color, logo):
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

  # jackpot() - Entrypoint for `/slots jackpot` command
  # ctx[required]: discord.ApplicationContext
  # Sends the current jackpot bounty value
  @slots.command(
    name="jackpot",
    description="Get the current Slots Jackpot!"
  )
  @commands.check(access_check)
  async def jackpot(self, ctx:discord.ApplicationContext):
    await ctx.respond(embed=discord.Embed(
      description=f"Current jackpot bounty is: **{self.get_jackpot()}**",
      color=discord.Color.dark_gold()
    ))

  # jackpots() - Entrypoint for `/slots jackpots`` command
  # ctx[required]: discord.ApplicationContext
  # Sends a list of the current top 10 jackpots
  @slots.command(
    name="jackpots",
    description="Get the Top 10 Slots Jackpots and Winners!"
  )
  async def jackpots(self, ctx:discord.ApplicationContext):
    jackpots = self.get_top_jackpots()
    embed = discord.Embed(
      title="**Top Jackpots!**",
      color=discord.Color.dark_gold()
    )
    embed.add_field(
      name="VALUE",
      value="\n".join([str(j['jackpot_value']) for j in jackpots])
    )

    # These are a little more complicated
    winners = []
    lifespans = []
    for jackpot in jackpots:
      winner = jackpot["winner"]
      winner_str = (winner[:24] + '...') if len(winner) > 24 else winner
      winners.append(winner_str)

      lifespan = jackpot["time_won"] - jackpot["time_created"]
      lifespan_str = humanize.naturaltime(datetime.now() - jackpot['time_created'])
      lifespan_str += " ({}d {}h {}m)".format(lifespan.days, lifespan.seconds//3600, (lifespan.seconds//60)%60)
      lifespans.append(lifespan_str)

    embed.add_field(
      name="WINNER",
      value="\n".join(winners)
    )
    embed.add_field(
      name="WHEN/LIFESPAN",
      value="\n".join(lifespans)
    )

    await ctx.respond(embed=embed)

  # get_jackpot(config)
  # This function takes no arguments
  # and returns the most recent jackpot_value from the jackpots table
  def get_jackpot(self):
    # get the current jackpot
    db = getDB()
    query = db.cursor()
    sql = "SELECT jackpot_value FROM jackpots ORDER BY id DESC LIMIT 1"
    query.execute(sql)
    jackpot_amt = query.fetchone()
    db.commit()
    query.close()
    db.close()
    return jackpot_amt[0]

  # get_top_jackpots(config)
  # This function takes no arguments
  # and returns the 10 most recent jackpot_value from the jackpots table
  def get_top_jackpots(self):
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "SELECT * FROM jackpots WHERE winner IS NOT NULL ORDER BY id DESC LIMIT 10"
    query.execute(sql)
    jackpot_data = query.fetchall()
    query.close()
    db.close()
    return jackpot_data
