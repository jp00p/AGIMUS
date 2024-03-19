import discord
from discord import option

from common import logger, bot, get_user
from utils.database import AgimusDB

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
def autocomplete_user_tags(ctx: discord.AutocompleteContext):
  user_discord_id = ctx.interaction.user.id
  user_tags = db_get_user_tags(user_discord_id)

  if not user_tags:
    return ['No Tags Present']

  return [t['tag'] for t in user_tags if ctx.value.lower() in t['tag'].lower()]


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
  max_length=128
)
async def tag_user(ctx:discord.ApplicationContext, user:discord.User, tag:str):
  user_obj = get_user(user.id)

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

  user_tags = db_get_user_tags(user.id)

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
    description = f"{ctx.author.mention} tagged themselves with:\n\n > {tag}"
  else:
    description = f"{ctx.author.mention} tagged {user.mention} with:\n\n > {tag}"

  logger.info(f"{ctx.author.display_name} just tagged {user.display_name} with {tag}")
  
  db_add_user_tag(user.id, ctx.author.id, tag)
  await ctx.respond(f"{user.mention}, tag! You're it!",
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
  user_tags = db_get_user_tags(user_discord_id)

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

  db_delete_user_tag(user_discord_id, tag)
  await ctx.respond(
    embed=discord.Embed(
      title="Untag Successful!",
      description=f"You have removed the following tag:\n\n> {tag}",
      color=discord.Color.blurple()
    ),
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
async def display_tags(ctx:discord.ApplicationContext, user:discord.User, public:str):
  public = (public == "yes")
  user_obj = get_user(user.id)

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

  user_tags = db_get_user_tags(user.id)

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

  tags_by_tagger = {}
  for t in user_tags:
    tags_by_tagger.setdefault(t['tagger_user_id'], []).append(t)

  display_embed = discord.Embed(
    title=f"{user.display_name}'s Tags",
    description=f"{user.mention} is tagged with the following...",
    color=discord.Color.blurple()
  )
  display_embed.add_field(
    name=f"Total Tags: {len(user_tags)}",
    value="\n".join(
                "\n". join(f"* {t['tag']}" for t in tags) +
                (f"\nby {tags[0]['tagger_name']}" if user.id != int(tagger_user_id) else "\n(self-described)")
                    for tagger_user_id, tags in tags_by_tagger.items()
              ),
    inline=False
  )

  await ctx.respond(embed=display_embed, ephemeral=not public)


# ________                      .__
# \_____  \  __ __   ___________|__| ____   ______
#  /  / \  \|  |  \_/ __ \_  __ \  |/ __ \ /  ___/
# /   \_/.  \  |  /\  ___/|  | \/  \  ___/ \___ \
# \_____\ \_/____/  \___  >__|  |__|\___  >____  >
#        \__>           \/              \/     \/
def db_add_user_tag(target_user_id, tagger_user_id, tag):
  with AgimusDB() as query:
    sql = "INSERT INTO user_tags (tagged_user_id, tagger_user_id, tag) VALUES (%s, %s, %s)"
    vals = (target_user_id, tagger_user_id, tag)
    query.execute(sql, vals)

def db_delete_user_tag(tagged_user_id, tag):
  with AgimusDB() as query:
    sql = "DELETE FROM user_tags WHERE tagged_user_id = %s AND tag = %s"
    vals = (tagged_user_id, tag)
    query.execute(sql, vals)

def db_get_user_tags(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT *, u.name AS tagger_name FROM user_tags ut INNER JOIN users u ON u.discord_id = ut.tagger_user_id " \
          "WHERE tagged_user_id = %s ORDER BY tag ASC"
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchall()
  return results
