from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator


@bot.slash_command(
  name="wordcloud",
  description="Show your own wordcloud!"
)
async def wordcloud(ctx):
  user_details = get_wordcloud_text_for_user(ctx.author.id)
  
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
  response = {
    "name" : results[0]["name"],
    "num_messages" : len(results),
    "full_message_text" : ""
  }
  for row in results:
    response["full_message_text"] += " " + row["text"]

  return response