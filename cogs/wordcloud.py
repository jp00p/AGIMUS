from collections import Counter

from common import *
from wordcloud import WordCloud, STOPWORDS
from utils import string_utils

#  __      __                .___     .__                   ._______   ____.__               
# /  \    /  \___________  __| _/____ |  |   ____  __ __  __| _/\   \ /   /|__| ______  _  __
# \   \/\/   /  _ \_  __ \/ __ |/ ___\|  |  /  _ \|  |  \/ __ |  \   Y   / |  |/ __ \ \/ \/ /
#  \        (  <_> )  | \/ /_/ \  \___|  |_(  <_> )  |  / /_/ |   \     /  |  \  ___/\     / 
#   \__/\  / \____/|__|  \____ |\___  >____/\____/|____/\____ |    \___/   |__|\___  >\/\_/  
#        \/                   \/    \/                       \/                    \/        
class WordcloudView(discord.ui.DesignerView):
  def __init__(
    self,
    *,
    user: discord.User,
    num_messages: int,
    unique_words: int,
    top_words: list[str],
    image_attachment_name: str,
  ):
    super().__init__(timeout=60)

    container = discord.ui.Container()

    container.add_text(f"## {user.mention}'s Wordcloud!")
    container.add_separator()

    container.add_gallery(
      discord.MediaGalleryItem(f"attachment://{image_attachment_name}")
    )

    container.add_separator()

    if top_words:
      top_words_display = " - ".join([w.title() for w in top_words])
    else:
      top_words_display = "N/A"

    footer_lines = [
      f"#- Top words: {top_words_display}",
      f"#- Unique words: {unique_words}",
      f"#- Based on the last {num_messages} messages.",
    ]
    container.add_text("\n".join(footer_lines))

    self.add_item(container)


#  __      __                .___     .__                   .____________                
# /  \    /  \___________  __| _/____ |  |   ____  __ __  __| _/\_   ___ \  ____   ____  
# \   \/\/   /  _ \_  __ \/ __ |/ ___\|  |  /  _ \|  |  \/ __ | /    \  \/ /  _ \ / ___\ 
#  \        (  <_> )  | \/ /_/ \  \___|  |_(  <_> )  |  / /_/ | \     \___(  <_> ) /_/  >
#   \__/\  / \____/|__|  \____ |\___  >____/\____/|____/\____ |  \______  /\____/\___  / 
#        \/                   \/    \/                       \/         \/      /_____/  
class Wordcloud(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

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
      discord.OptionChoice(name="No", value="no"),
      discord.OptionChoice(name="Yes", value="yes")
    ]
  )
  async def wordcloud(self, ctx: discord.ApplicationContext, public: str):
    user = await get_user(ctx.author.id)

    if user.get("log_messages") != 1:
      await ctx.respond(
        embed=discord.Embed(
          title="You do not have Wordcloud logging!",
          description="Use `/settings` to enable Wordcloud.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    public = bool(public == "yes")

    await ctx.defer(ephemeral=not public)

    user_details = await self.db_get_wordcloud_text_for_user(ctx.author.id)
    if user_details is None:
      await ctx.followup.send(
        embed=discord.Embed(
          title="No word data is available for you yet!",
          description="Post some messages around the server!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    full_wordlist = user_details["full_message_text"].lower().split(" ")
    full_wordlist = " ".join(full_wordlist)

    remove_emoji = re.compile("<.*?>")
    special_chars = re.escape(string.punctuation)

    full_wordlist = re.sub(remove_emoji, "", full_wordlist)
    full_wordlist = re.sub(r"https?:\/\/\S*", "", full_wordlist)
    full_wordlist = re.sub(r"[" + special_chars + r"]", "", full_wordlist)
    full_wordlist = re.sub(r"\s+", " ", full_wordlist).strip()

    for word in self.more_stopwords + self.common_words:
      STOPWORDS.add(word)

    tokens_all = [w for w in full_wordlist.split(" ") if w]
    unique_words = len(set(tokens_all))

    tokens_filtered = [
      w for w in tokens_all
      if len(w) >= 3 and w not in STOPWORDS
    ]
    word_counts = Counter(tokens_filtered)
    top_words = [w for w, _ in word_counts.most_common(3)]

    mask_choice = random.choice(self.image_masks)
    mask = np.array(mask_choice)

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
      min_word_length=3
    ).generate(full_wordlist)

    image = wc.to_image()

    safe_name = string_utils.strip_punctuation(user_details["name"])
    filepath = f"./images/reports/wordcloud-{safe_name}.png"
    image.save(filepath)

    attachment_name = f"wordcloud-{safe_name}.png"
    discord_image = discord.File(filepath, filename=attachment_name)

    view = WordcloudView(
      user=ctx.author,
      num_messages=user_details["num_messages"],
      unique_words=unique_words,
      top_words=top_words,
      image_attachment_name=attachment_name,
    )

    await ctx.followup.send(
      view=view,
      file=discord_image,
      ephemeral=not public
    )

    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} has generated a {Fore.CYAN}wordcloud!{Fore.RESET}")

  async def db_get_wordcloud_text_for_user(self, user_discord_id: int):
    async with AgimusDB(dictionary=True) as query:
      sql = """
        SELECT
          message_history.user_discord_id,
          message_history.message_text as text,
          users.name
        FROM message_history
          LEFT JOIN users ON message_history.user_discord_id = users.discord_id
        WHERE message_history.user_discord_id = %s
        ORDER BY message_history.time_created DESC
        LIMIT %s
      """
      vals = (user_discord_id, self.max_query_limit)
      await query.execute(sql, vals)
      results = await query.fetchall()

    if len(results) < 1:
      return None

    response = {
      "name": results[0]["name"],
      "num_messages": len(results),
      "full_message_text": ""
    }
    for row in results:
      response["full_message_text"] += " " + " ".join(set(row["text"].split(" ")))

    return response
