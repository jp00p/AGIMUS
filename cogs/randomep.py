from common import *
from utils.show_utils import get_show_embed

all_shows = ["tos", "tas", "tng", "ds9", "voy", "enterprise", "lowerdecks", "disco", "picard", "friends", "firefly", "simpsons", "sunny"]

# Util
def generate_random_ep_embed(shows):
  selected_show = random.choice(shows)
  f = open("./data/episodes/" + selected_show + ".json")
  show_data = json.load(f)
  f.close()
  episode = random.randrange(len(show_data["episodes"]))
  show_embed = get_show_embed(show_data, episode, selected_show)
  return show_embed

# ____   ____.__
# \   \ /   /|__| ______  _  ________
#  \   Y   / |  |/ __ \ \/ \/ /  ___/
#   \     /  |  \  ___/\     /\___ \
#    \___/   |__|\___  >\/\_//____  >
#                    \/           \/
class ShowSelector(discord.ui.Select):
  def __init__(self, user_discord_id):
    selected_shows = db_get_user_randomep_shows(user_discord_id)
    options = [
      discord.SelectOption(
        label=s,
        value=s,
        default=s in selected_shows
      )
      for s in all_shows
    ]

    super().__init__(
      placeholder="Select/Deselect Shows",
      min_values=1,
      max_values=len(all_shows),
      options=options,
      row=1
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.defer()
    self.view.selected_shows = self.values

class PublicSelector(discord.ui.Select):
  def __init__(self):
    options = [
      discord.SelectOption(
        label="Public",
        value="public",
        default=True
      ),
      discord.SelectOption(
        label="Private",
        value="private"
      )
    ]

    super().__init__(
      placeholder="Select Public or Private",
      min_values=1,
      max_values=1,
      options=options,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.defer()
    self.view.private = self.values[0]

class RollButton(discord.ui.Button):
  def __init__(self, user_discord_id):
    self.user_discord_id = user_discord_id
    super().__init__(
      label="      Roll      ",
      style=discord.ButtonStyle.primary,
      row=3
    )

  async def callback(self, interaction:discord.Interaction):
    if len(self.view.selected_shows):
      await interaction.response.defer(ephemeral=True)
      db_set_user_randomep_shows(self.user_discord_id, self.view.selected_shows)
      embed = generate_random_ep_embed(self.view.selected_shows)
      logger.info(self.view.private)
      await interaction.followup.send(
        embed=embed,
        ephemeral=self.view.private == "private"
      )
    else:
      await interaction.response.send_message(
        embed=discord.Embed(
          title="You must select at least one show.",
          color=discord.Color.red()
        ),
        ephemeral=True
      )

class RandomEpSelectView(discord.ui.View):
  def __init__(self, cog, user_discord_id):
    super().__init__()
    self.cog = cog
    self.private = "public"
    self.selected_shows = db_get_user_randomep_shows(user_discord_id)

    self.add_item(ShowSelector(user_discord_id))
    self.add_item(PublicSelector())
    self.add_item(RollButton(user_discord_id))



class RandomEp(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(
    name="randomep",
    description="Select your shows and roll for a random episode!"
  )
  async def randomep(self, ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)

    view = RandomEpSelectView(self, ctx.author.id)
    embed = discord.Embed(
      title="🎲 Random Episode 🎲",
      description="Choose one or more Shows and Roll!",
      color=discord.Color.dark_purple()
    )
    embed.set_footer(text="Your selections will be saved for the next time you use the command!")

    await ctx.followup.send(embed=embed, view=view, ephemeral=True)



# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_get_user_randomep_shows(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = '''
      SELECT shows FROM randomep_selections WHERE user_discord_id = %s;
    '''
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchone()

  if results:
    results = json.loads(results['shows'])
  else:
    results = []
  return results

def db_set_user_randomep_shows(user_discord_id, shows):
  shows = json.dumps(shows)
  with AgimusDB() as query:
    sql = '''
      INSERT INTO randomep_selections (user_discord_id, shows)
        VALUES (%s, %s)
      ON DUPLICATE KEY UPDATE
        user_discord_id = %s, shows = %s
    '''
    vals = (user_discord_id, shows, user_discord_id, shows)
    query.execute(sql, vals)
