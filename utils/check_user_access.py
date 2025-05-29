from common import *

# @commands.check decorator function
# Can be injected in between @commands.check and your slash function to
# only allow access from the "allowed_user_ids" from the command config by matching it with the function name
async def user_check(ctx):
  ctx_type = type(ctx).__name__
  try:
    command_config = config["commands"][f"{ctx.command}"]
    allowed_user_ids = command_config.get('allowed_user_ids')
    if not allowed_user_ids:
      return True

    if ctx.author.id not in allowed_user_ids:
      if ctx_type == 'ApplicationContext':
        await ctx.respond(f"{get_emoji('guinan_beanflick_stance_threat')} Nope, that command is restricted.", ephemeral=True)
      return False
    else:
      return True
  except Exception as e:
    logger.info(f"user_check error: {e}")
    logger.info(e)
    return False