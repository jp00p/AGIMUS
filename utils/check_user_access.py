from common import *

# @commands.check decorator function
# Can be injected in between @commands.check and your slash function to
# restrict access from the "disallowed_user_ids" from the command config by matching it with the function name
async def user_check(ctx):
  ctx_type = type(ctx).__name__
  try:
    command_config = config["commands"][f"{ctx.command}"]
    disallowed_user_ids = command_config.get('disallowed_user_ids')
    if not disallowed_user_ids:
      return True

    if ctx.author.id in disallowed_user_ids:
      if ctx_type == 'ApplicationContext':
        await ctx.respond(f"{get_emoji('guinan_beanflick_stance_threat')} Yeah, nah that's gonna be a no from me dawg. Farmer no farming. (Give me a week... 😝)", ephemeral=True)
      return False
    else:
      return True
  except Exception as e:
    logger.info(f"user_check error: {e}")
    logger.info(e)
    return False