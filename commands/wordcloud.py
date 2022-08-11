from numpy import full
from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from handlers.xp import increment_user_xp

image_masks = [
  Image.open("./images/cloud_masks/combadge_mask.png"),
  Image.open("./images/cloud_masks/ds9_mask.png"),
  Image.open("./images/cloud_masks/enterprise_d_mask.png"),
  Image.open("./images/cloud_masks/exocomp_mask.png"),
  Image.open("./images/cloud_masks/llap_mask.png"),
  Image.open("./images/cloud_masks/spock_mask.png")
]

@bot.slash_command(
  name="wordcloud",
  description="Show your own most popular words in a wordcloud! Enable with /settings to allow cloud generation."
)
@option(
  name="public",
  description="Show to public?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="No",
      value="no"
    ),
    discord.OptionChoice(
      name="Yes",
      value="yes"
    )
  ]
)
async def wordcloud(ctx:discord.ApplicationContext, public:str):
  """
  Entrypoint for `/wordcloud` command
  generates a wordcloud image based on users most-used words
  also allows users to opt-in or out of logging their messages
  """
  user = get_user(ctx.author.id)

  # if they have previously disabled logging
  if user.get("log_messages") != 1:
    await ctx.respond(content="You do not have logging enabled. Use `/settings` to start logging so AGIMUS can generate a wordcloud for you!", ephemeral=True)
    return

  public = bool(public == "yes")

  await ctx.defer(ephemeral=not public)
  # get their message data
  user_details = get_wordcloud_text_for_user(ctx.author.id)

  # if they have no data yet
  if user_details is None:
    await ctx.respond(content="No user data is available for you yet.", ephemeral=True)
    return
  else:
    await increment_user_xp(ctx.author, 1, "used_wordcloud", ctx.channel)

  # performing these modifications to the user's data again (in case they have old, uncleaned up data)
  full_wordlist = set(user_details['full_message_text'].lower().split(' '))
  full_wordlist = " ".join(full_wordlist)
  remove_emoji = re.compile('<.*?>')
  special_chars = re.escape(string.punctuation)

  full_wordlist = re.sub(remove_emoji, '', full_wordlist) # strip discord emoji from message
  full_wordlist = re.sub(r'https?:\/\/\S*', '', full_wordlist) # strip all URLs from the content
  full_wordlist = re.sub(r'['+special_chars+']', '', full_wordlist) # strip any remaining special characters
  full_wordlist = full_wordlist.replace("  ", " ").strip() # convert double spaces to single space
  command_words = ["profile", "help", "wordcloud", "quiz", "trivia", "slots", "poker", "set_tagline", "reports", "badges"]
  for word in command_words:
    STOPWORDS.add(word)

  # mask image (combadge in this case, something else might work better)
  mask = np.array(random.choice(image_masks))

  # build wordcloud with magic of wordcloud lib
  wc = WordCloud(
    scale=1,
    contour_color="#000000",
    color_func=lambda *args, **kwargs: random.choice(["#ffaa00", "#33cc99", "#ff2200", "#ff9966", "#cc33ff"]),
    contour_width=1,
    min_font_size=8,
    max_words=500,
    stopwords=STOPWORDS,
    mask=mask,
    font_path="./fonts/tng_credits.ttf",
    background_color="#000000",
    mode="RGB",
    width=1200,
    height=800,
    min_word_length=3).generate(full_wordlist)

  # create PIL image
  image = wc.to_image()
  image.save(f"./images/reports/wordcloud-{user_details['name']}.png")

  # create discord image
  discord_image = discord.File(f"./images/reports/wordcloud-{user_details['name']}.png")

  # send the image!
  await ctx.followup.send(content=f"(Based on your last {user_details['num_messages']} messages)", file=discord_image, ephemeral=not public)
  logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has generated a {Fore.CYAN}wordcloud!{Fore.RESET}")

def get_wordcloud_text_for_user(user_discord_id:int):
  """
  get user's message history and return it in a dict
  """
  db = getDB()
  query = db.cursor(dictionary=True)
  max_limit = 1701
  sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s ORDER BY message_history.time_created DESC LIMIT %s"
  vals = (user_discord_id,max_limit)
  query.execute(sql, vals)
  results = query.fetchall()
  query.close()
  db.close()
  if len(results) < 1:
    response = None
  else:
    response = {
      "name" : results[0]["name"],
      "num_messages" : len(results),
      "full_message_text" : ""
    }
    for row in results:
      response["full_message_text"] += " " + row["text"]
  return response