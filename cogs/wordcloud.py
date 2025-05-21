from numpy import full
from common import *
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
from utils import string_utils

class Wordcloud(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

    # mask images
    self.image_masks = [
      Image.open("./images/cloud_masks/combadge_mask.png"),
      Image.open("./images/cloud_masks/ds9_mask.png"),
      Image.open("./images/cloud_masks/enterprise_d_mask.png"),
      Image.open("./images/cloud_masks/exocomp_mask.png"),
      Image.open("./images/cloud_masks/llap_mask.png"),
      Image.open("./images/cloud_masks/spock_mask.png")
    ]

    self.hmasks = [
      "./images/cloud_masks/halloween/bat_mask.png",
      "./images/cloud_masks/halloween/cat_mask.png",
      "./images/cloud_masks/halloween/coffin_mask.png",
      "./images/cloud_masks/halloween/graveyard_mask.png",
      "./images/cloud_masks/halloween/house_mask.png",
      "./images/cloud_masks/halloween/pumpkin1_mask.png",
      "./images/cloud_masks/halloween/pumpkin2_mask.png",
      "./images/cloud_masks/halloween/skull_mask.png",
      "./images/cloud_masks/halloween/wizard_mask.png"
    ]

    self.common_words = string_utils.common_words
    self.more_stopwords = string_utils.more_stopwords

    # how many messages to pull from the database
    self.max_query_limit = 1701

  @commands.slash_command(
    name="wordcloud",
    description="Show your own most popular words in a wordcloud! Enable logging with `/settings`"
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
  async def wordcloud(self, ctx:discord.ApplicationContext, public:str):
    """
    Entrypoint for `/wordcloud` command
    generates a wordcloud image based on users most-used words
    """
    user = await get_user(ctx.author.id)

    # if they have previously disabled logging
    if user.get("log_messages") != 1:
      await ctx.respond(content="You do not have logging enabled. Use `/settings` to enable logging!", ephemeral=True)
      return

    public = bool(public == "yes")

    await ctx.defer(ephemeral=not public)
    # get their message data
    user_details = await self.db_get_wordcloud_text_for_user(ctx.author.id)

    # if they have no data yet
    if user_details is None:
      await ctx.respond(content="No user data is available for you yet. Post some messages around the server!", ephemeral=True)
      return

    # performing these modifications to the user's data again (in case they have old, uncleaned up data)
    full_wordlist = user_details['full_message_text'].lower().split(' ')
    full_wordlist = " ".join(full_wordlist)
    remove_emoji = re.compile('<.*?>')
    special_chars = re.escape(string.punctuation)
    full_wordlist = re.sub(remove_emoji, '', full_wordlist) # strip discord emoji from message
    full_wordlist = re.sub(r'https?:\/\/\S*', '', full_wordlist) # strip all URLs from the content
    full_wordlist = re.sub(r'['+special_chars+']', '', full_wordlist) # strip any remaining special characters
    full_wordlist = full_wordlist.replace("  ", " ").strip() # convert double spaces to single space

    for word in self.more_stopwords+self.common_words:
      STOPWORDS.add(word)

    # mask image
    mask_choice = random.choice(self.image_masks)
    #mask_choice = Image.open(mask_choice)
    mask = np.array(mask_choice)

    # build wordcloud with magic of wordcloud lib
    wc = WordCloud(
      scale=1,
      contour_color="#000000",
      contour_width=0,
      color_func=lambda *args, **kwargs: random.choice(["#ff9a00", "#09ff00", "#c900ff", "#fbfaf4", "#CC0000"]),
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
    filename = f"./images/reports/wordcloud-{string_utils.strip_punctuation(user_details['name'])}.png"
    image.save(filename)

    # create discord image
    discord_image = discord.File(filename)

    # send the image!
    await ctx.followup.send(content=f"(Based on your last {user_details['num_messages']} messages)", file=discord_image, ephemeral=not public)
    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has generated a {Fore.CYAN}wordcloud!{Fore.RESET}")

  async def db_get_wordcloud_text_for_user(self, user_discord_id:int):
    """
    get user's message history and return it in a dict
    """
    async with AgimusDB(dictionary=True) as query:
      sql = "SELECT message_history.user_discord_id, message_history.message_text as text, users.name FROM message_history LEFT JOIN users ON message_history.user_discord_id = users.discord_id WHERE message_history.user_discord_id = %s ORDER BY message_history.time_created DESC LIMIT %s"
      vals = (user_discord_id,self.max_query_limit)
      await query.execute(sql, vals)
      results = await query.fetchall()

    if len(results) < 1:
      response = None
    else:
      response = {
        "name" : results[0]["name"],
        "num_messages" : len(results),
        "full_message_text" : ""
      }
      for row in results:
        # strip out duplicate words (in old messages)
        response["full_message_text"] += " " + " ".join(set(row["text"].split(" ")))
    return response
