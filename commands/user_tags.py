import re

import discord
from discord import option

from common import logger, bot, get_user, commands, Style
from utils.check_channel_access import access_check
from utils.database import AgimusDB

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_user_tags(ctx: discord.AutocompleteContext):
  user_discord_id = ctx.interaction.user.id
  user_tags = await db_get_user_tags(user_discord_id)

  if not user_tags:
    return ['No Tags Present']

  return [t['tag'] for t in user_tags if ctx.value.lower() in t['tag'].lower()]


# __________        __    __
# \______   \__ ___/  |__/  |_  ____   ____   ______
#  |    |  _/  |  \   __\   __\/  _ \ /    \ /  ___/
#  |    |   \  |  /|  |  |  | (  <_> )   |  \\___ \
#  |______  /____/ |__|  |__|  \____/|___|  /____  >
#         \/                              \/     \/
class ClearConfirmButton(discord.ui.Button):
  def __init__(self, user_id):
    self.user_id = user_id
    super().__init__(
      label="Confirm",
      style=discord.ButtonStyle.primary
    )

  async def callback(self, interaction: discord.Interaction):
    await db_clear_all_user_tags(self.user_id)
    await interaction.response.edit_message(
      embed=discord.Embed(
        title="User Tags Cleared Successfully!",
        description=f"You have removed ALL of your user tags. Daymum.\n\nYou may want to now encourage more tagging, or disable tagging entirely with `/settings`!",
        color=discord.Color.green()
      ),
      view=None
    )

class ClearCancelButton(discord.ui.Button):
  def __init__(self):
    super().__init__(
      label="Cancel",
      style=discord.ButtonStyle.red,
    )

  async def callback(self, interaction:discord.Interaction):
    await interaction.response.edit_message(
      embed=discord.Embed(
        title="Clear Cancelled!",
        description="No action taken.",
        color=discord.Color.red()
      ),
      view=None,
      attachments=[]
    )

class ClearConfirmView(discord.ui.View):
  def __init__(self, user_id):
    super().__init__()
    self.add_item(ClearConfirmButton(user_id))
    self.add_item(ClearCancelButton())


# _________                                           .___
# \_   ___ \  ____   _____   _____ _____    ____    __| _/______
# /    \  \/ /  _ \ /     \ /     \\__  \  /    \  / __ |/  ___/
# \     \___(  <_> )  Y Y  \  Y Y  \/ __ \|   |  \/ /_/ |\___ \
#  \______  /\____/|__|_|  /__|_|  (____  /___|  /\____ /____  >
#         \/             \/      \/     \/     \/      \/    \/
user_tags = bot.create_group("user_tags", "Commands for managing user tags")

@user_tags.command(
  name="tag",
  description="Add a tag to a user (info about them)"
)
@option(
  "user",
  discord.User,
  description="The user you wish to tag",
  required=True
)
@option(
  "tag",
  str,
  description="Tag Text",
  required=True,
  max_length=64
)
@commands.check(access_check)
async def tag_user(ctx:discord.ApplicationContext, user:discord.User, tag:str):
  user_obj = await get_user(user.id)

  if user_obj.get("tagging_enabled") != 1:
    await ctx.respond(
      embed=discord.Embed(
        title=f"{user.display_name} Does Not Have Tagging Enabled!",
        description="No tagging possible.",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  # Escape the Markdown characters
  tag = re.sub(r"[*_~`\\]", r"\\\g<0>", tag)

  user_tags = await db_get_user_tags(user.id)

  tags = [t['tag'] for t in user_tags]
  if tag in tags:
    await ctx.respond(
      embed=discord.Embed(
        title="This User Tag Already Exists!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  if len(user_tags) >= 50:
    await ctx.respond(
      embed=discord.Embed(
        title=f"{user.display_name} Already Has Maximum Number of Tags!",
        description="They're at the limit of 50 tags! You may want to let them know, and see if they want to manage "
                    "and delete some!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  if ctx.author.id == user.id:
    msg = None
    description = f"{ctx.author.mention} tagged themselves with:\n\n > {tag}"
  else:
    msg = f"{user.mention}, tag! You're it!"
    description = f"{ctx.author.mention} tagged {user.mention} with:\n\n > {tag}"

  logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} just tagged {Style.BRIGHT}{user.display_name}{Style.RESET_ALL} with {Style.BRIGHT}{tag}{Style.RESET_ALL}")

  await db_add_user_tag(user.id, ctx.author.id, tag)
  await ctx.respond(msg,
    embed=discord.Embed(
      title="User Tag Added!",
      description=description,
      color=discord.Color.blurple()
    )
  )

@user_tags.command(
  name="untag",
  description="Remove one of your tags."
)
@option(
  "tag",
  str,
  description="Tag Text",
  required=True,
  autocomplete=autocomplete_user_tags,
  max_length=128
)
async def untag_user(ctx:discord.ApplicationContext, tag:str):
  user_discord_id = ctx.author.id
  user_tags = await db_get_user_tags(user_discord_id)

  if not user_tags:
    await ctx.respond(
      embed=discord.Embed(
        title="No Tags Present!",
        description="You don't have any tags present to untag!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  if tag not in [t['tag'] for t in user_tags]:
    await ctx.respond(
      embed=discord.Embed(
        title="Tag Not Present!",
        description=f"You're not currently tagged with `{tag}`!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  await db_delete_user_tag(user_discord_id, tag)
  await ctx.respond(
    embed=discord.Embed(
      title="Untag Successful!",
      description=f"You have removed the following tag:\n\n> {tag}",
      color=discord.Color.blurple()
    ),
    ephemeral=True
  )

@user_tags.command(
  name="clear_tags",
  description="Remove ALL of your tags."
)
async def clear_tags(ctx:discord.ApplicationContext):
  user_discord_id = ctx.author.id
  user_tags = await db_get_user_tags(user_discord_id)

  if not user_tags:
    await ctx.respond(
      embed=discord.Embed(
        title="No Tags Present!",
        description="You don't have any tags present to clear!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  await ctx.respond(
    embed=discord.Embed(
      title="Are you sure your want to **REMOVE ALL OF YOUR USER TAGS!?!**",
      description=f"You currently have {len(user_tags)} which would be cleared! Just double checking...",
      color=discord.Color.red()
    ),
    view=ClearConfirmView(user_discord_id),
    ephemeral=True
  )


@user_tags.command(
  name="display",
  description="Display all tags applied to a user"
)
@option(
  "user",
  discord.User,
  description="The user for which you wish display tags",
  required=True
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
  name="attribute",
  description="Include who created the tags?",
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
async def display_tags(ctx:discord.ApplicationContext, user:discord.User, public:str, attribute:str):
  public = (public == "yes")
  attribute = (attribute == "yes")
  user_obj = await get_user(user.id)

  if user_obj.get("tagging_enabled") != 1:
    await ctx.respond(
      embed=discord.Embed(
        title=f"{user.display_name} Does Not Have Tagging Enabled!",
        description="No tagging possible.",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  user_tags = await db_get_user_tags(user.id)

  if not user_tags:
    await ctx.respond(
      embed=discord.Embed(
        title="User Has No Tags Yet!",
        description="You can use `/user_tags tag` to add one!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  display_embed = discord.Embed(
    title=f"{user.display_name}'s Tags",
    description=f"{user.mention} is tagged with the following...",
    color=discord.Color.blurple()
  )
  if attribute:
    tags_by_tagger = {}
    for t in user_tags:
      tags_by_tagger.setdefault(t['tagger_user_id'], []).append(t)

    for tagger_user_id, tags in tags_by_tagger.items():
      display_embed.add_field(
        name=f"by _{tags[0]['tagger_name']}_" if user.id != int(tagger_user_id) else "_(self-described)_",
        value="\n".join(f"* **{t['tag']}**" for t in tags),
        inline=False
      )
  else:
    display_embed.add_field(
      name=f"Total Tags: {len(user_tags)}",
      value="\n".join(f"* **{t['tag']}**" for t in user_tags),
      inline=False
    )

  await ctx.respond(embed=display_embed, ephemeral=not public)


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
async def db_add_user_tag(target_user_id, tagger_user_id, tag):
  async with AgimusDB() as query:
    sql = "INSERT INTO user_tags (tagged_user_id, tagger_user_id, tag) VALUES (%s, %s, %s)"
    vals = (target_user_id, tagger_user_id, tag)
    await query.execute(sql, vals)

async def db_delete_user_tag(tagged_user_id, tag):
  async with AgimusDB() as query:
    sql = "DELETE FROM user_tags WHERE tagged_user_id = %s AND tag = %s"
    vals = (tagged_user_id, tag)
    await query.execute(sql, vals)

async def db_clear_all_user_tags(tagged_user_id):
  async with AgimusDB() as query:
    sql = "DELETE FROM user_tags WHERE tagged_user_id = %s"
    vals = (tagged_user_id)
    await query.execute(sql, vals)

async def db_get_user_tags(user_discord_id):
  async with AgimusDB(dictionary=True) as query:
    sql = "SELECT *, u.name AS tagger_name FROM user_tags ut INNER JOIN users u ON u.discord_id = ut.tagger_user_id " \
          "WHERE tagged_user_id = %s ORDER BY tag ASC"
    vals = (user_discord_id,)
    await query.execute(sql, vals)
    results = await query.fetchall()
  return results
