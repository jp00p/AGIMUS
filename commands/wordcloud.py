from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

# wordcloud() - Entrypoint for `/wordcloud` command
# generates a wordcloud image based on users most-used words
# also allows users to opt-in or out of logging their messages
@bot.slash_command(
  name="wordcloud",
  description="Show your own most popular words in a wordcloud!"
)
@option(
  name="enable_logging",
  description="Choose \"Yes\" to set the bot to log your messages, or \"No\" to stop logging and erase all your logged messages.",
  required=False,
  choices=[
    discord.OptionChoice(
      name="Yes",
      value="Yes"
    ),
    discord.OptionChoice(
      name="No",
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
    await ctx.respond("Now logging your messages!  Once you have posted a few messages, check your wordcloud by typing `/wordcloud`", ephemeral=True)
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
    await ctx.respond(f"Your messages will no longer be logged and all previous data has been removed. ({deleted_row_count} messages deleted from the database)", ephemeral=True)
    return

  user = get_user(ctx.author.id)

  # if they have previously disabled logging
  if user["log_messages"] != 1:
    await ctx.respond("You do not have logging enabled. Use `/wordcloud enable_logging Yes` to start logging so we can generate a wordcloud for you.", ephemeral=True)
    return

  # get their message data
  user_details = get_wordcloud_text_for_user(ctx.author.id)

  # if they have no data yet
  if user_details is None:
    await ctx.respond("No user data is available for you yet.", ephemeral=True)
    return
  
  # mask image (combadge in this case, something else might work better)
  mask = np.array(Image.open("./images/cloud_masks/combadge_mask.png"))

  # build wordcloud with magic of wordcloud lib
  wc = WordCloud(contour_color="#000044", contour_width=5, max_words=350, min_font_size=14, stopwords=STOPWORDS, mask=mask, font_path="./images/tng_font.ttf", background_color="black", mode="RGB", width=822, height=800, min_word_length=4).generate(user_details['full_message_text'])

  # create PIL image 
  image = wc.to_image()
  image.save(f"./images/reports/wordcloud-{user_details['name']}.png")

  # create discord image
  discord_image = discord.File(f"./images/reports/wordcloud-{user_details['name']}.png")

  # send the image!
  await ctx.respond(f"(Based on your last {user_details['num_messages']} messages)", file=discord_image, ephemeral=False)

# get user's message history and return it in a dict
def get_wordcloud_text_for_user(user_discord_id:int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s LIMIT 250"
  vals = (user_discord_id,)
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