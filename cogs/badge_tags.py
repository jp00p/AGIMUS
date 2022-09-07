from common import *
# from queries.badge_tags import *
from utils.badge_utils import *
from utils.check_channel_access import access_check

all_badge_info = db_get_all_badge_info()

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
def user_badges_autocomplete(ctx:discord.AutocompleteContext):
  user_badges = [b['badge_name'] for b in db_get_user_badges(ctx.interaction.user.id)]
  if len(user_badges) == 0:
    user_badges = ["You don't have any badges yet!"]

  return [result for result in user_badges if ctx.value.lower() in result.lower()]


async def tags_autocomplete(ctx:discord.AutocompleteContext):
  current_user_tags = [t['tag_name'] for t in db_get_user_badge_tags(ctx.interaction.user.id)]
  current_user_tags.sort()

  return [t for t in current_user_tags if ctx.value.lower() in t.lower()]

# ____   ____.__
# \   \ /   /|__| ______  _  ________
#  \   Y   / |  |/ __ \ \/ \/ /  ___/
#   \     /  |  \  ___/\     /\___ \
#    \___/   |__|\___  >\/\_//____  >
#                    \/           \/
class TagSelector(discord.ui.Select):
  def __init__(self, user_discord_id, badge_name):
    user_badge_tags = db_get_user_badge_tags(user_discord_id)
    associated_tags = db_get_associated_badge_tags(user_discord_id, badge_name)
    associated_tag_names = [t['tag_name'] for t in associated_tags]
    options = [
      discord.SelectOption(
        label=t['tag_name'],
        value=str(t['id']),
        default=t['tag_name'] in associated_tag_names
      )
      for t in user_badge_tags
    ]

    super().__init__(
      placeholder="Select the tags you'd like to associate with this badge",
      min_values=0,
      max_values=len(user_badge_tags),
      options=options,
      row=1
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.defer()
    self.view.tag_ids = self.values


class TagButton(discord.ui.Button):
  def __init__(self, cog, user_discord_id, badge_name):
    self.cog = cog
    self.user_discord_id = user_discord_id
    self.badge_name = badge_name
    super().__init__(
      label="           Tag Badge           ",
      style=discord.ButtonStyle.primary,
      row=2
    )

  async def callback(self, interaction:discord.Interaction):
    associated_tags = db_get_associated_badge_tags(self.user_discord_id, self.badge_name)
    logger.info(associated_tags)
    tag_ids_to_delete = [t['id'] for t in associated_tags if t['id'] not in self.view.tag_ids]
    logger.info(tag_ids_to_delete)
    db_delete_badge_tags_associations(tag_ids_to_delete)
    if len(self.view.tag_ids):
      db_create_badge_tags_associations(self.user_discord_id, self.badge_name, self.view.tag_ids)

    new_associated_tags = db_get_associated_badge_tags(self.user_discord_id, self.badge_name)
    associated_tag_names = [t['tag_name'] for t in new_associated_tags]

    if len(associated_tag_names):
      description = f"**{self.badge_name}** is now tagged with:" + "\n\n" + "\n".join(associated_tag_names)
    else:
      description = f"**{self.badge_name}** no longer has any tags associated!"

    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Tags Updated",
        description=description,
        color=discord.Color.green()
      ),
      view=None,
      files=[]
    )


class TagBadgeView(discord.ui.View):
  def __init__(self, cog, user_discord_id, badge_name):
    super().__init__()

    self.tag_ids = []
    self.add_item(TagSelector(user_discord_id, badge_name))
    self.add_item(TagButton(cog, user_discord_id, badge_name))

# __________             .___           ___________                    _________
# \______   \_____     __| _/ ____   ___\__    ___/____     ____  _____\_   ___ \  ____   ____
#  |    |  _/\__  \   / __ | / ___\_/ __ \|    |  \__  \   / ___\/  ___/    \  \/ /  _ \ / ___\
#  |    |   \ / __ \_/ /_/ |/ /_/  >  ___/|    |   / __ \_/ /_/  >___ \\     \___(  <_> ) /_/  >
#  |______  /(____  /\____ |\___  / \___  >____|  (____  /\___  /____  >\______  /\____/\___  /
#         \/      \/      \/_____/      \/             \//_____/     \/        \/      /_____/
class BadgeTags(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.max_tags = 25 # We can only have 25 items in a Discord select component

  tags_group = discord.SlashCommandGroup("tags", "Badge Tags Commands!")

  @tags_group.command(
    name="create",
    description="Create a new badge tag. (NOTE: You can have a max of 25 tags)"
  )
  @option(
    name="tag",
    description="Name of the tag to create",
    required=True,
    min_length=1,
    max_length=24
  )
  async def create(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)

    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Already Exists",
          description=f"You've already created **{tag}**!\n\nYou can associate your badges with this tag via `/tags tag_badge`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    if len(current_user_tags) >= self.max_tags:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Maximum Tags Allowed Reached",
          description=f"You've reached the maximum number of tags allowed ({self.max_tags})!\n\nYou can remove a tag if desired via `/tags delete`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and create the new tag for the user
    db_create_user_tag(ctx.author.id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Created Successfully!",
        description=f"You've created a new tag: **{tag}**!\n\nYou can associate your badges with this tag now via `/tags tag_badge`",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return

  @tags_group.command(
    name="delete",
    description="Delete an existing badge tag"
  )
  @option(
    name="tag",
    description="Name of the tag to delete",
    required=True,
    autocomplete=tags_autocomplete
  )
  async def create(self, ctx:discord.ApplicationContext, tag:str):
    await ctx.defer(ephemeral=True)

    tag = tag.strip()
    if len(tag) == 0:
      await ctx.followup.send(
        embed=discord.Embed(
          title="You Must Enter A Tag!",
          description=f"Tag name cannot be empty!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    current_user_tags = db_get_user_badge_tags(ctx.author.id)
    current_user_tag_names = [t['tag_name'] for t in current_user_tags]

    if tag not in current_user_tag_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="This Tag Does Not Exist",
          description=f"**{tag}** is not a tag you have created!\n\nYou can create a new tag via `/tags create`!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    # If checks pass, go ahead and delete the tag for the user
    db_delete_user_tag(ctx.author.id, tag)
    await ctx.followup.send(
      embed=discord.Embed(
        title="Tag Deleted Successfully!",
        description=f"You've deleted the tag: **{tag}**!\n\nNote that any badges that were previously associated with the tag have been disassociated as well.",
        color=discord.Color.green()
      ),
      ephemeral=True
    )
    return

  @tags_group.command(
    name="tag_badge",
    description="Tag one of your badges!"
  )
  @option(
    name="badge",
    description="Name of the badge to tag",
    required=True,
    autocomplete=user_badges_autocomplete
  )
  async def tag_badge(self, ctx:discord.ApplicationContext, badge:str):
    await ctx.defer(ephemeral=True)

    user_badges = db_get_user_badges(ctx.author.id)
    user_badge_names = [b['badge_name'] for b in user_badges]
    if badge not in user_badge_names:
      await ctx.followup.send(
        embed=discord.Embed(
          title="Badge Not Present In Inventory",
          description=f"You don't own this badge!",
          color=discord.Color.red()
        ),
        ephemeral=True
      )
      return

    badge_info = db_get_badge_info_by_name(badge)

    view = TagBadgeView(self, ctx.author.id, badge)
    embed = discord.Embed(
      title=badge,
      color=discord.Color.dark_purple()
    )
    badge_image = discord.File(fp=f"./images/badges/{badge_info['badge_filename']}", filename=badge_info['badge_filename'])
    embed.set_image(url=f"attachment://{badge_info['badge_filename']}")

    await ctx.followup.send(embed=embed, file=badge_image, view=view, ephemeral=True)

  @tags_group.command(
    name="showcase",
    description="Display a showcase of tagged badges"
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
  @option(
    name="tag",
    description="Name of the tag to showcase",
    required=True,
    autocomplete=tags_autocomplete
  )
  async def showcase(self, ctx:discord.ApplicationContext, public:str, tag:str):
    public = (public == "yes")
    await ctx.defer(ephemeral=not public)

    title = f"{ctx.author.display_name.encode('ascii', errors='ignore').decode().strip()}'s Tagged Badges - {tag}"
    tagged_badges = db_get_user_tagged_badges(ctx.author.id, tag)

    logger.info(tagged_badges)

    # Set up text values for paginated pages
    total_badges_cnt = len(all_badge_info)
    tagged_badges_cnt = len(tagged_badges)
    collected = f"{tagged_badges_cnt} TAGGED ON THE USS HOOD"
    filename_prefix = f"badge_list_tagged_{ctx.author.id}-page-"

    badge_images = await generate_paginated_badge_images(ctx.author, 'showcase', tagged_badges, total_badges_cnt, title, collected, filename_prefix)

    embed = discord.Embed(
      title=f"Tagged Badges",
      description=f'{ctx.author.mention} has tagged {tagged_badges_cnt} "{tag}" badges!',
      color=discord.Color.blurple()
    )

    # If we're doing a public display, use the images directly
    # Otherwise private displays can use the paginator
    if not public:
      buttons = [
        pages.PaginatorButton("prev", label="   ⬅   ", style=discord.ButtonStyle.primary, disabled=bool(user_badges_cnt <= 30), row=1),
        pages.PaginatorButton(
          "page_indicator", style=discord.ButtonStyle.gray, disabled=True, row=1
        ),
        pages.PaginatorButton("next", label="   ➡   ", style=discord.ButtonStyle.primary, disabled=bool(user_badges_cnt <= 30), row=1),
      ]

      pages_list = [
        pages.Page(files=[image], embeds=[embed])
        for image in badge_images
      ]
      paginator = pages.Paginator(
          pages=pages_list,
          show_disabled=True,
          show_indicator=True,
          use_default_buttons=False,
          custom_buttons=buttons,
          loop_pages=True
      )
      await paginator.respond(ctx.interaction, ephemeral=True)
    else:
      # We can only attach up to 10 files per message, so if it's public send them in chunks
      file_chunks = [badge_images[i:i + 10] for i in range(0, len(badge_images), 10)]
      for chunk_index, chunk in enumerate(file_chunks):
        # Only post the embed on the last chunk
        if chunk_index + 1 == len(file_chunks):
          await ctx.followup.send(embed=embed, files=chunk, ephemeral=False)
        else:
          await ctx.followup.send(files=chunk, ephemeral=False)

# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/

# TODO: Move this into queries.badge_tags

def db_get_user_badge_tags(user_discord_id) -> list:
  """
  returns a list of the users's current custom badge tags
  """
  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = "SELECT * FROM badge_tags WHERE user_discord_id = %s ORDER BY tag_name ASC"
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchall()
  return results


def db_create_user_tag(user_discord_id, tag) -> None:
  """
  creates a new tag for the user in question
  """
  with getDB() as db:
    query = db.cursor()
    sql = "INSERT INTO badge_tags (user_discord_id, tag_name) VALUES (%s, %s)"
    vals = (user_discord_id, tag)
    query.execute(sql, vals)
    db.commit()


def db_delete_user_tag(user_discord_id, tag) -> None:
  """
  delete a tag for the user in question
  """
  with getDB() as db:
    query = db.cursor()
    sql = "DELETE FROM badge_tags WHERE user_discord_id = %s AND tag_name = %s"
    vals = (user_discord_id, tag)
    query.execute(sql, vals)
    db.commit()


def db_get_associated_badge_tags(user_discord_id, badge_name) -> list:
  """
  returns a list of the current tags the user has associated with a given badge
  """
  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = '''
      SELECT b_t.* FROM badge_tags AS b_t
        JOIN badge_tags_associations AS t_a ON b_t.id = t_a.badge_tags_id
        JOIN badges AS b ON t_a.badges_id = b.id
        JOIN badge_info AS b_i ON b_i.badge_filename = b.badge_filename
          WHERE b_i.badge_name = %s AND b_t.user_discord_id = %s
    '''
    vals = (badge_name, user_discord_id)
    query.execute(sql, vals)
    results = query.fetchall()
  return results


def db_create_badge_tags_associations(user_discord_id, badge_name, tag_ids):
  """
  associates a list of tags with a user's specific badge
  """
  tags_values_list = []
  for id in tag_ids:
    tuple = (id, badge_name, user_discord_id)
    tags_values_list.append(tuple)

  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = '''
      INSERT INTO badge_tags_associations (badges_id, badge_tags_id)
        SELECT b.id, %s
          FROM badges AS b
          JOIN badge_info AS b_i ON b_i.badge_filename = b.badge_filename
            WHERE b_i.badge_name = %s AND b.user_discord_id = %s
    '''
    query.executemany(sql, tags_values_list)
    db.commit()

def db_delete_badge_tags_associations(tag_ids):
  """
  deletes a list of tags from association with a user's specific badge
  """
  tags_values_list = []
  for id in tag_ids:
    tuple = (id,)
    tags_values_list.append(tuple)

  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = '''
      DELETE FROM badge_tags_associations WHERE badge_tags_id = %s
    '''
    query.executemany(sql, tags_values_list)
    db.commit()

def db_get_user_tagged_badges(user_discord_id, tag):
  '''
    get_user_badges(user_discord_id)
    user_discord_id[required]: int
    returns a list of badges the user has
  '''
  with getDB() as db:
    query = db.cursor(dictionary=True)
    sql = '''
      SELECT b_i.badge_name, b_i.badge_filename, b.locked, b_i.special FROM badges b
        JOIN badge_info AS b_i
          ON b.badge_filename = b_i.badge_filename
        JOIN badge_tags_associations AS t_a
          ON t_a.badges_id = b.id
        JOIN badge_tags AS b_t
          ON b.user_discord_id = b_t.user_discord_id AND t_a.badge_tags_id = b_t.id
        WHERE b.user_discord_id = %s AND b_t.tag_name = %s
          ORDER BY b_i.badge_filename ASC
    '''
    vals = (user_discord_id, tag)
    query.execute(sql, vals)
    badges = query.fetchall()
  return badges