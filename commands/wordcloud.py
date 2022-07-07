from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator


@bot.slash_command(
  name="wordcloud",
  description="Show your own wordcloud!"
)
@option(
  name="enable_logging",
  description="Set the bot to log your messages, or stop logging and erase all your messages",
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

async def wordcloud(ctx, enable_logging):

  if enable_logging == "Yes":
    db = getDB()
    query = db.cursor(dictionary=True)
    sql = "UPDATE users SET log_messages = 1 WHERE discord_id = %s"
    vals = (ctx.author.id,)
    query.execute(sql, vals)
    db.commit()
    query.close()
    db.close()
    await ctx.respond("Your messages will now be logged so we can generate a word cloud for you!")
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
    query.close()
    db.commit()
    db.close()
    await ctx.respond("Your messages will no longer be logged and all previous data has been removed.")
    return

  user_details = get_wordcloud_text_for_user(ctx.author.id)
  
  if user_details is None:
    await ctx.respond("No user data is available for you.  Try opting-in to the wordcloud by typing `/wordcloud enable_logging yes`")
    return
  
  mask = np.array(Image.open("./images/cloud_masks/combadge_mask.png"))
  wc = WordCloud(contour_color="#000044", contour_width=5, max_words=350, min_font_size=14, stopwords=STOPWORDS, mask=mask, font_path="./images/tng_font.ttf", background_color="black", mode="RGB", width=822, height=800, min_word_length=4).generate(user_details['full_message_text'])
  image = wc.to_image()
  image.save(f"./images/reports/wordcloud-{user_details['name']}.png")
  discord_image = discord.File(f"./images/reports/wordcloud-{user_details['name']}.png")
  await ctx.respond(file=discord_image, ephemeral=False)

# get user's message history and return it in a dict
def get_wordcloud_text_for_user(user_discord_id:int):
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s LIMIT 500"
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