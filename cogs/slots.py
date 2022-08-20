import math
import time
from common import *
from handlers.xp import increment_user_xp
from utils.check_channel_access import access_check

command_config = config["commands"]["slots spin"]

# Set up Slot Choices
slot_choices = [
  discord.OptionChoice(name=show, value=show.upper())
  for show in command_config["parameters"][0]["allowed"]
]


class Slots(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.slot_results_dir = f"{ROOT_DIR}/images/slot_results/"
    if not os.path.exists(self.slot_results_dir):
      os.makedirs(self.slot_results_dir)

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
  @commands.cooldown(1, 1, commands.BucketType.user)
  async def spin(self, ctx:discord.ApplicationContext, show:str):
    await ctx.defer(ephemeral=True)

    logger.info(f"{Style.BRIGHT}{ctx.author.name}{Style.RESET_ALL} is {Fore.LIGHTYELLOW_EX}rolling the slots!{Fore.RESET}")   
    
    # Load slots data
    f = open(command_config["data"])
    SLOTS = json.load(f)
    f.close()

    # Use the option the user selected or pick a random show
    if show not in command_config["parameters"][0]["allowed"]:
      show = random.choice(["TNG", "DS9", "VOY", "HOLODECK"])
    
    #logger.info(f"{Fore.LIGHTRED_EX}Rolling slot theme:{Fore.RESET} {Style.BRIGHT}{show}{Style.RESET_ALL}")
    # player data  
    player_id = ctx.author.id
    player = get_user(player_id)
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
        description=f"{ctx.author.mention}: You need at least {wager} point(s) to spin! Play the quiz to get more points or try changing your wager"
      ), ephemeral=True)
      return

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
    
    # build the spin embed (spinbed)    
    spin_msg = ""
   
    if free_spin:
      spin_msg += "**This one's on the house!** (after 5 free spins, they will cost you points!)"
    else:
      spin_msg += f"Spending `{wager}` of your points!"    

    spinbed = discord.Embed(
      title=random.choice(spinnin),
      description=spin_msg,
      color=discord.Color.random()
    )
    spinbed.set_footer(text=f"This is spin #{player['spins']+1} for you.")
    await ctx.send_followup(embed=spinbed, ephemeral=False) # first followup 

    # roll the slots!
    silly_matches, matching_chars, jackpot, symbol_matches = self.roll_slot(show, SLOTS[show], filename=str(player_id))
    self.increment_player_spins(player_id)

    try:
      file = discord.File(f"{self.slot_results_dir}{player_id}.png", filename=f"{player_id}.png")
    except Exception:
      logger.info(f"{Fore.RED}Error generating discord file placeholder{Fore.RESET}")
      file = None

    match_msg = f"\n__Results for spin #{player['spins']+1}__\n"

    if len(symbol_matches) > 0:
      match_msg += "**"+symbol_matches[0].upper()+":** "
      match_msg += f"`{round(score_mult * symbol_matches[1])} points`\n"
      total_rewards += int(math.ceil(score_mult * symbol_matches[1]))

    if len(silly_matches) > 0:
      match_msg += "**Discovered Bits:** "
      match_msg += "; ".join(silly_matches)
      match_msg += f" `{len(silly_matches) * score_mult} point(s)`\n"
      total_rewards += len(silly_matches) * score_mult

    # matching characters (transporter clones)  
    if len(matching_chars) > 0:
      match_msg += "**Transporter clones: ** "
      match_msg += ", ".join(matching_chars).replace("_", " ").title()
      match_msg += f" `({3 * score_mult} points)`\n"
      total_rewards += 3 * score_mult

    title = f"{ctx.author.display_name} wins!"
    embed_color = discord.Color(0x1abc9c)

    if jackpot:
      title = f"**{ctx.author.display_name}** won the jackpot! {get_emoji('q_shocking')}"
      embed_color = discord.Color.dark_gold()
      jackpot_amt = self.get_jackpot()
      total_rewards += round(jackpot_amt * themed_payout)
      match_msg += f"\n {ctx.author.mention} wins the pot of: `{jackpot_amt}` ...multiplied by the slots' jackpot payout rate of x{themed_payout}... **for a total winnings of `{round(jackpot_amt*themed_payout)}`**\n\nJackpot has been reset to: **`250`**\n\n"
      win_jackpot(ctx.author.display_name, player_id)
      jackpot_embed = discord.Embed(
        title=f"**{ctx.author.display_name} WINS THE JACKPOT!!!**".upper(),
        color=embed_color        
      )
      jackpot_embed.set_image(url="https://i.imgur.com/S7Pv9lM.jpg")
      await ctx.send_followup(embed=jackpot_embed, ephemeral=False)

    if total_rewards > 0:
      # WIN
      total_profit = total_rewards - wager
      if total_profit == 0:
        title = f"{player['name']} broke even!"
      match_msg += f"**Total Profit:** `{total_profit} point(s)`.\n"
      embed = discord.Embed(
        title=title,
        color=embed_color,
        description=f"{match_msg}\n",
      )
      embed.set_image(url=f"attachment://{player_id}.png")
      embed.set_footer(text=f"{player['name']}'s score: {player['score']+total_profit}")
      set_player_score(ctx.author, total_profit)
      await increment_user_xp(ctx.author, 1, "slot_win", ctx.channel)
      await ctx.send_followup(embed=embed, file=file, ephemeral=False)
      return
    else:
      # LOSS
      title = f"{ctx.author.display_name} lost!"
      increase_jackpot(score_mult)
      set_player_score(ctx.author, -wager)
      loser = ["No dice!", "Bust!", "No matches!", "Better luck next time!", "Sad trombone!", "You didn't win!",
               "We have no prize to fit your loss -- ", "You may have won in the mirror universe, but not here!",
               "Sensors detect no matches.", "JACKP-- no wait, that's a loss.", "Close, but no cigar.",
               "Not a win!", "You would have won if it were opposite day!"]
      embed = discord.Embed(
        title=title,
        color=discord.Color(0xe74c3c),
        description=f"{random.choice(loser)}\n\n`{score_mult}` point(s) added to the jackpot, increasing its bounty to `{self.get_jackpot()}`.",
      )
      embed.set_footer(text=f"{player['name']}'s score: {player['score']-wager}")
      embed.set_image(url=f"attachment://{player_id}.png")
      await ctx.send_followup(embed=embed, file=file, ephemeral=True)
      return

  @spin.error
  async def spin_error(self, ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
      await ctx.respond(f"You're spinning the slots at warp 10! To prevent you from becoming a promiscuous iguana, I've slowed you down to warp 9.5. Try spinning again in {round(error.retry_after, 2)} seconds", ephemeral=True)

  def increment_player_spins(self, discord_id: int):
    """
    This function increases the number of a
    user's spin value by one
    """
    db = getDB()
    query = db.cursor()
    sql = "UPDATE users SET spins = spins + 1 WHERE discord_id = %s"
    vals = (discord_id,)
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()

  def roll_slot(self, slot_series: str, slot_to_roll: dict, generate_image=True, filename="slot_results.png"):
    """
    This function picks three random images from a target show
    and returns categories of matches (silly, character, jackpot, symbols)
    """
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

    roll_weights = [sym[0] for sym in symbols.values()]
    symbol_roll = random.choices(list(symbols.keys()), weights=roll_weights, k=3)
    symbol_matches = set(symbol_roll)
    symbol_result = []

    fruits = ["cherry", "grapes", "lemon", "plum", "watermelon"]

    # check the symbols winnings
    if len(symbol_matches) == 1:
      win_sym = symbol_roll[0]
      win_string = f"3 {win_sym}"
      symbol_result = [win_string, symbols[win_sym][1]]
    elif list(symbol_roll).count("cherry") == 2:
      # 2 cherries in the result give them their winnings back
      symbol_result = ["2 Cherries", 1]
    elif len(symbol_matches) == 3 and all(sym in fruits for sym in symbol_roll):
      # if they get 3 different fruits
      symbol_result = ["Fruit Salad", 1.5]

    # pull out image files for selected slot
    slot_dir = f"{ROOT_DIR}{slot_to_roll['files']}"
    files = os.listdir(slot_dir)
    results = []
    # pick 3 random themed slots
    for i in range(3):
      results.append(random.choice(files))

    if generate_image:
      image1 = Image.open(slot_dir + results[0]).resize((150,150))
      image2 = Image.open(slot_dir + results[1]).resize((150,150))
      image3 = Image.open(slot_dir + results[2]).resize((150,150))
      logo = slot_series + "_logo.png"
      color = (0, 0, 0, 100)  # black bg
      self.generate_slot_image(image1, image2, image3, symbol_roll, color, logo).save(f"{self.slot_results_dir}{filename}.png")

    result_set = set(s.replace(".png", "") for s in results)
    silly_matches = []
    matching_chars = []
    jackpot = False

    for match_title, matches in slot_to_roll["matches"].items():
      # check the silly/bits-based matches
      match_count = len([m for m in matches if m in result_set])
      if match_count >= 2:
        silly_matches.append(match_title)

    if len(result_set) == 1:
      matching_chars.append(results[0].replace(".png", ""))
      jackpot = True

    for jackpot_match in slot_to_roll["custom_jackpots"]:
      if set(jackpot_match) == result_set:
        jackpot = True

    if len(result_set) == 2:
      for r in result_set:
        if results.count(f"{r}.png") > 1:
          matching_chars.append(r)

    return silly_matches, matching_chars, jackpot, symbol_result

  def generate_slot_image(self, im1: Image, im2: Image, im3: Image, symbols, color, logo: str) -> Image:
    """
    This function combines three images and a logo to display to the user
    """

    logo_location = "./images/slots/" + logo

    # destination image
    dst = Image.new('RGBA', (im1.width + im2.width + im3.width + 32, max(im1.height, im2.height, im3.height + 16)),
                    color)

    # background image
    background = Image.open(logo_location).convert('RGBA').resize((150, 150))

    final_images = []
    originals = [im1, im2, im3]

    # paste the background and the image on to the background
    for i in range(1,3+1):
      img = Image.new('RGBA', (150,150), (0,0,0))
      img.paste(background)
      img.paste(originals[i-1], (0,0), originals[i-1])
      final_images.append(img)

    # combine the composite with the destination
    dst.paste(final_images[0], (8, 8))
    dst.paste(final_images[1], (im1.width+16, 8))
    dst.paste(final_images[2], (im1.width+im2.width+24, 8))

    symbols_positions = [10,176,334]

    for i,s in enumerate(symbols):
      simg = Image.open("./images/slot_symbols/"+s+".png")
      simg = ImageOps.contain(simg, (50,50))
      dst.paste(simg, (symbols_positions[i], 150-simg.height), simg)

    return dst

  @slots.command(
    name="jackpot",
    description="Get the current Slots Jackpot!"
  )
  @commands.check(access_check)
  async def jackpot(self, ctx: discord.ApplicationContext):
    """
    Sends the current jackpot bounty value
    """
    await ctx.respond(embed=discord.Embed(
      description=f"Current jackpot bounty is: **{self.get_jackpot()}**",
      color=discord.Color.dark_gold()
    ))

  @slots.command(
    name="jackpots",
    description="Get the last 10 Slots Jackpots and Winners!"
  )
  async def jackpots(self, ctx: discord.ApplicationContext):
    """
    Sends a list of the current top 10 jackpots
    """
    jackpots = self.get_recent_jackpots()

    if not jackpots:
      await ctx.respond(embed=discord.Embed(
        title="No Current Jackpots Registered!",
        color=discord.Color.dark_gold()
      ))
      return

    embed = discord.Embed(
      title="**Recent Jackpots!**",
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
      lifespan_str += f" ({lifespan.days}d {lifespan.seconds // 3600}h {(lifespan.seconds // 60) % 60}m)"
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

  def get_jackpot(self) -> int:
    """
    get the current jackpot
    """
    db = getDB()
    query = db.cursor()
    sql = "SELECT jackpot_value FROM jackpots ORDER BY id DESC LIMIT 1"
    query.execute(sql)
    jackpot_amt = query.fetchone()
    db.commit()
    query.close()
    db.close()
    return jackpot_amt[0]

  def get_recent_jackpots(self):
    """
    returns the 10 most recent jackpot_value from the jackpots table
    """
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "SELECT * FROM jackpots WHERE winner IS NOT NULL ORDER BY id DESC LIMIT 10"
    query.execute(sql)
    jackpot_data = query.fetchall()
    query.close()
    db.close()
    return jackpot_data

  @commands.command()
  @commands.check(access_check)
  async def testslots(self, ctx: discord.Message, show=''):
    """
    will run the !slots command 1000 times to gather statistics
    """
    try:
      f = open(config["commands"]["testslots"]["data"])
      allowlist = json.load(f)
      f.close()

      if ctx.author.id in allowlist:
        f = open(config["commands"]["slots spin"]["data"])
        SLOTS = json.load(f)
        f.close()

        if show in ["ds9", "tng", "voy", "holodeck", "ships"]:
          show = show.upper()
        else:
          show = "TNG"

        spins = 1000
        await ctx.send(embed=discord.Embed(
          title="TESTING!!!",
          description=f"Testing {show} slots with {spins} spins! This will take a few seconds...",
          color=discord.Color.greyple()
        ))

        jackpots = 0
        wins = 0
        profitable_wins = 0
        profits = []

        for i in range(spins):
          #logger.info(f"Spin #{i}")
          silly,clones,jackpot,symbol_result = self.roll_slot(show, SLOTS[show], generate_image=False)
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
        msg = "> Out of **{0}** test spins, there were a total of **{1}** wins, **{2}** of those wins being jackpots.\n\n> Average chance of winning per spin: **{3}%**.\n\n> Average chance of jackpot per spin: **{4}%**.\n\n> Number of profitable spins: **{5}**\n\n> Chance for profit: **{6}%**\n\n> Average profit per spin: **{7}** points (not counting jackpots)".format(spins,wins,jackpots, chance_to_win, chance_to_jackpot, profitable_wins, chance_for_profit, average_profit)
        await ctx.send(embed=discord.Embed(
          title="RESULTS:",
          description=msg,
          color=discord.Color.greyple()
        ))
      else:
        await ctx.send("Ah ah ah, you didn't say the magic word", ephemeral=True)
    except BaseException as e:
      logger.info(traceback.format_exc())   