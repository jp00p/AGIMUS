from .common import *

# poker() - Entrypoint for !poker command
# message[required]: discord.Message
# This function is the main entrypoint of the !poker command
async def poker(message:discord.Message):
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


async def generate_poker_image(hand:treys.Card, filename:str):
  channel = client.get_channel(config["commands"]["poker"]["channels"][0])
  base = Image.new("RGBA", (1120,350), (0,0,0,0))
  value_font = ImageFont.truetype("images/lcars3.ttf", 64)
  smaller_font = ImageFont.truetype("images/lcars3.ttf", 32)
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
  #await channel.send(file=file)


async def resolve_poker(game_id):
  global POKER_GAMES
  f = open(config["commands"]["poker"]["data"])
  poker_data = json.load(f)
  f.close()
  POKER_PAYOUTS = poker_data["payouts"]
  channel = client.get_channel(config["commands"]["poker"]["channels"][0])
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


