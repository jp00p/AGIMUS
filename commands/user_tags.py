from common import *

# class UserTagsDropdown(discord.ui.Select):
#   def __init__(self, cog):
#     self.cog = cog
#     options = [
#       discord.SelectOption(label="Enable XP", description="Opt-in to the XP and Badge System"),
#       discord.SelectOption(label="Disable XP", description="Opt-out of the XP and Badge System"),
#     ]

#     super().__init__(
#       placeholder="Choose your preference",
#       min_values=1,
#       max_values=1,
#       options=options,
#       row=1
#     )

tag_user = discord.SlashCommandGroup("tag_user", "Commands for managing user tags")

@tag_user.command(
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
  "description",
  str,
  description="Name of the badge to tag",
  required=True
)
async def tag_user(ctx:discord.ApplicationContext, user:discord.User, tag:str):
  user_tags = db_get_user_tags(user.id)

  tags = [t['text'] for t in user_tags]
  if tag in tags:
    await ctx.respond(
      embed=discord.Embed(
        title="This Tag Already Exists!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  db_add_user_tag(user.id, ctx.author.id, tag)
  await ctx.respond(
      embed=discord.Embed(
        title=f"{ctx.author.display_name} Added A Tag To {user.display_name}",
        description=f"**Tag:** {tag}"
        color=discord.Color.red()
      )
  )

@tag_user.command(
  name="display_tags",
  description="Display all tags for a user"
)
@option(
  "user",
  discord.User,
  description="The user for which you wish display tags",
  required=True
)
async def display_tags(ctx:discord.ApplicationContext, user:discord.User):
  user_tags = db_get_user_tags(user.id)

  if not user_tags:
    await ctx.respond(
      embed=discord.Embed(
        title="User has no tags yet!",
        description="You can use `/user_tags tag` to add one!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  if len(user_tags) >= 50:
    await ctx.respond(
      embed=discord.Embed(
        title=f"{user.display_name} Already Has Maximum Number of Tags!",
        description="They're at the limit of 50 tags! You may want to let them know, and see if they want to manage and delete some!",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return

  await ctx.respond(
    embed=discord.Embed(
      title=f"{user.display_name}'s Tags",
      description=f"{user.mention} is tagged with the following:\n\n"
                   "\n".join([f"* {t['text']}" for t in user_tags]),
      color=discord.Color.blurple()
    )
  )



def db_add_user_tag(target_user_id, tagger_user_id, tag):
  with AgimusDB() as query:
    sql = "INSERT INTO user_tags (tagged_user_id, tagger_user_id, tag) VALUES (%s, %s)"
    vals = (target_user_id, tagger_user_id, tag)
    query.execute(sql, vals)

def db_get_user_tags(user_discord_id):
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT * FROM user_tags WHERE tagged_user_id = %s ORDER BY tag_name ASC"
    vals = (user_discord_id,)
    query.execute(sql, vals)
    results = query.fetchall()
  return results
