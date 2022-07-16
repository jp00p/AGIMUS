from numpy import full
from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

from handlers.xp import increment_user_xp

# wordcloud() - Entrypoint for `/wordcloud` command
# generates a wordcloud image based on users most-used words
# also allows users to opt-in or out of logging their messages
@bot.slash_command(
  name="wordcloud",
  description="Show your own most popular words in a wordcloud! Enable logging to be able to generate a cloud."
)
@option(
  name="enable_logging",
  description="Enable message logging to be able to generate wordclouds",
  required=False,
  choices=[
    discord.OptionChoice(
      name="Yes - save words in my public messages to your database",
      value="Yes"
    ),
    discord.OptionChoice(
      name="No - and please delete all my data",
      value="No"
    )
  ]
)

async def wordcloud(ctx:discord.ApplicationContext, enable_logging:str):

  # handle logging toggle on/off
  if enable_logging == "Yes":
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "UPDATE users SET log_messages = 1 WHERE discord_id = %s"
    vals = (ctx.author.id,)
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond(content=f"Now logging your messages in the database! Once you have posted a few messages, check your wordcloud by typing `/wordcloud`! Disable logging and delete all your saved data by selecting \"No\" instead to /wordcloud.", ephemeral=True)
    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has {Fore.GREEN}enabled{Fore.RESET} {Fore.CYAN}message logging!{Fore.RESET}")
    return
  
  if enable_logging == "No":
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "UPDATE users SET log_messages = 0 WHERE discord_id = %s"
    vals = (ctx.author.id,)
    query.execute(sql, vals)
    sql = "DELETE FROM message_history WHERE user_discord_id = %s"
    vals = (ctx.author.id,)
    query.execute(sql, vals)
    deleted_row_count = query.rowcount
    query.close()
    db.commit()
    db.close()
    await ctx.respond(content=f"Your messages will no longer be logged and all previous data has been removed. ({deleted_row_count} messages deleted from the database)", ephemeral=True)
    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has {Fore.RED}disabled{Fore.RESET} {Fore.CYAN}message logging!{Fore.RESET}")
    return

  user = get_user(ctx.author.id)

  # if they have previously disabled logging
  if user["log_messages"] and user["log_messages"] != 1:
    await ctx.respond(content="You do not have logging enabled. Use `/wordcloud enable_logging Yes` to start logging so AGIMUS can generate a wordcloud for you!", ephemeral=True)
    return
  
  await ctx.defer()
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
  
  # mask image (combadge in this case, something else might work better)
  mask = np.array(Image.open("./images/cloud_masks/combadge_mask.png"))

  # build wordcloud with magic of wordcloud lib
  wc = WordCloud(scale=2, contour_color="#000000", color_func=lambda *args, **kwargs: random.choice(["#6688CC", "#BB4411", "#9977AA", "#774466", "#DD6644", "#EE9955"]), contour_width=1, max_words=800, stopwords=STOPWORDS, mask=mask, font_path="./images/lcars2.ttf", background_color="black", mode="RGB", width=822, height=800, min_word_length=3).generate(full_wordlist)

  # create PIL image 
  image = wc.to_image()
  image.save(f"./images/reports/wordcloud-{user_details['name']}.png")

  # create discord image
  discord_image = discord.File(f"./images/reports/wordcloud-{user_details['name']}.png")

  # send the image!
  await ctx.followup.send(content=f"(Based on your last {user_details['num_messages']} messages)", file=discord_image, ephemeral=False)
  logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has generated a {Fore.CYAN}wordcloud!{Fore.RESET}")

# get user's message history and return it in a dict
def get_wordcloud_text_for_user(user_discord_id:int):
  db = getDB()
  query = db.cursor(dictionary=True)
  max_limit = 1701
  sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s LIMIT %s"
  vals = (user_discord_id,max_limit)
  query.execute(sql, vals)
  results = query.fetchall()
  db.commit()
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