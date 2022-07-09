from common import *
from utils.check_channel_access import access_check

class Poker(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.poker_players = []
    self.poker_games = {}

    f = open(config["commands"]["poker"]["data"])
    self.poker_data = json.load(f)
    f.close()

    self.poker_reacts = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "🤑", "✅"]
    self.discard_reacts = {
      "1️⃣" : 0,
      "2️⃣" : 1,
      "3️⃣" : 2,
      "4️⃣" : 3,
      "5️⃣" : 4
    }

  # poker() - Entrypoint for /poker command
  # ctx: discord.ApplicationContext
  # This function is the main entrypoint of the /poker command
  @commands.slash_command(
    name="poker",
    description="Start a hand of Poker"
  )
  @commands.check(access_check)
  async def poker(self, ctx:discord.ApplicationContext):
    # don't let players start 2 poker games
    for g in self.poker_games:
      self.poker_players.append(self.poker_games[g]["user"])

    if ctx.author.id in self.poker_players:
      await ctx.respond(
        embed=discord.Embed(  
          title=f"{ctx.author.name}: you have a poker game running already! Be patient!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

    else:
      # Get (it) Player
      player_id = ctx.author.id
      player = get_user(player_id)
      if player["score"] >= player["wager"]:
        set_player_score(str(player_id), -player["wager"])

        # Instantiate Deck and Draw 5
        deck = Deck()
        hand = deck.draw(5)
        # Generate hand image
        hand_image = await self.generate_poker_image(hand, player_id)
        hand_file = discord.File(hand_image, filename=str(player_id)+".png")

        embed = discord.Embed(
          title=f"{ctx.author.display_name}'s Poker hand",
          description=f"{ctx.author.mention}: Starting a round of poker with a `{player['wager']}` point wager. Here's your hand!",
          color=discord.Color(0x1abc9c)
        )
        embed.set_image(url="attachment://{0}".format(str(player_id)+".png"))
        embed.set_footer(text="React below with the numbers to discard the corresponding card.\n\nUse the 🤑 react to double your bet.\nUse the ✅ react to draw.")

        poker_response = await ctx.respond(embed=embed, file=hand_file)
        poker_message = await poker_response.original_message()
        for p in self.poker_reacts:
          await poker_message.add_reaction(p)
        self.poker_games[poker_message.id] = { 
          "user" : player_id,
          "hand" : hand,
          "discards": [False,False,False,False,False],
          "deck" : deck,
          "message": poker_response,
          "mention" : ctx.author.mention,
          "username": ctx.author.display_name,
          "wager" : player["wager"]
        }
      else:
        embed = discord.Embed(
          title="Not Enough Points To Play!",
          description=f"Sorry {ctx.author.mention}, you don't have enough points to play! Try lowering your wager or playing the quiz games.",
          color=discord.Color(0x1abc9c)
        )
        embed.set_footer(text=f"{ctx.author.mention}'s Current Points: **{player['score']}**")
        await ctx.respond(embed=embed, ephemeral=True)


  async def generate_poker_image(self, hand:treys.Card, filename:str):
    # channel = self.bot.get_channel(config["channels"]["poker-table"])
    base = Image.new("RGBA", (1120,350), (0,0,0,0))
    value_font = ImageFont.truetype("images/lcars3.ttf", 64)
    # smaller_font = ImageFont.truetype("images/lcars3.ttf", 32)
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
      card_template = Image.open("./images/cards/card-overlay.png")
      card_base = Image.new("RGBA", (200, 300), "black")
      draw = ImageDraw.Draw(card_template)
      face_path = ""
      image_path = ""
      color = "black"
      value,suit = list(Card.int_to_str(h))
      if suit == "h":    
        image_path = "./images/cards/basic/hearts/"
        color = "red"
      if suit == "d":
        image_path = "./images/cards/basic/diamonds/"
        color = "red"
      if suit == "c":
        image_path = "./images/cards/basic/clubs/"
      if suit == "s":
        image_path = "./images/cards/basic/spades/"
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
      suit_image = Image.open("./images/cards/suits/{}".format(suit_map[suit]))
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
    base.save(f"./images/cards/users/{filename}.png")
    return f"./images/cards/users/{filename}.png"


  async def resolve_poker(self, payload:discord.RawReactionActionEvent):
    game_id = payload.message_id
    channel = self.bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(game_id)
    reactions = message.reactions

    # handle discards, build new hand
    poker_payouts = self.poker_data["payouts"]
    poker_game = self.poker_games[game_id]
    wager = poker_game["wager"]
    user_id = poker_game["user"]
    hand = poker_game["hand"]
    deck = poker_game["deck"]
    doubled = False
    #print("reactions", reactions)

    # count reactions, set discards
    # done this way to allow the user to toggle draws
    for r in reactions:
      if r.emoji == "✅": # don't count that last "draw" reaction
        continue
      users = await r.users().flatten()
      # we only want to count the game player's reactions
      for m in users:
        if m.id == user_id and r.emoji in self.discard_reacts:
          poker_game["discards"][self.discard_reacts[r.emoji]] = True
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
    profit = round(poker_payouts[score_rank] * wager)
    if profit != 0:
      set_player_score(str(poker_game["user"]), profit)

    # Generate Response
    # get new hand image
    hand_image = await self.generate_poker_image(hand, user_id)
    file = discord.File(hand_image, filename=str(poker_game["user"])+".png")

    wager_str = "Total wager: `{}`"
    if doubled:
      wager_str = "\n*You doubled your wager!* Total wager: `{}`\n"
    wager_str = wager_str.format(wager)

    embed = discord.Embed(
      title=f"{poker_game['username']}'s Final Poker hand",
      color=discord.Color(0x1abc9c),
      description=f"{poker_game['mention']}: Here's your final hand: **{str_score}**\n{wager_str}"
    )
    embed.set_image(url="attachment://{0}".format(str(poker_game["user"])+".png"))
    embed.set_footer(text="Your profit: {}".format(profit-wager))

    # send results
    await channel.send(embed=embed, file=file)

    # handle player score
    self.poker_games.pop(game_id)


  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload:discord.RawReactionActionEvent):
    if payload.user_id == self.bot.user.id:
      return

    if payload.event_type == "REACTION_ADD":
      # poker reacts
      if payload.message_id in self.poker_games:
        if payload.user_id == self.poker_games[payload.message_id]["user"]:
          if payload.emoji.name == "✅":
            await self.resolve_poker(payload)
        else:
          user = await bot.fetch_user(payload.user_id)
          await self.poker_games[payload.message_id]["message"].remove_reaction(payload.emoji, user)