from common import *

# @commands.check decorator function
# Can be injected in between @commands.check and your slash function to
# restrict access to the "allowed_roles" from the command config by matching it with the function name
async def role_check(ctx):
  ctx_type = type(ctx).__name__
  try:
    command_config = config["commands"][f"{ctx.command}"]
    allowed_roles = command_config.get('allowed_roles')
    if not allowed_roles:
      return True

    allowed_role_ids = get_role_ids_list(allowed_roles)
    user_role_ids = [r.id for r in ctx.author.roles]

    allowed = any(user_rid in allowed_role_ids for user_rid in user_role_ids)
    if not allowed:
      if ctx_type == 'ApplicationContext':
        embed = discord.Embed(
          title="Aw hell nah dawg.",
          description=f"{get_emoji('guinan_beanflick_stance_threat')} You don't have the proper security clearance to use this command.",
          color=discord.Color.red()
        )
        embed.set_image(url="https://i.imgur.com/QeUW4fV.gif")
        await ctx.respond(embed=embed, ephemeral=True)
    else:
      return True
  except Exception as e:
    logger.info(e)