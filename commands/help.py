from inspect import trace
from common import *
from utils.check_channel_access import access_check

basic_commands = [
  {
    "name" : "Start a message with \"computer:\"",
    "description" : "AGIMUS will try to respond with factual information"
  },
  {
    "name" : "Start a message with \"agimus:\"",
    "description" : "AGIMUS will respond with a creative, AI-generated response"
  },
  {
    "name" : "/drop",
    "description" : "Find and post a drop (like the Geordi \"bullshit\" drop!)"
  },
  {
    "name" : "/clip",
    "description" : "Find and post a video clip (like /drop but video clips)"
  },
  {
    "name" : "/profile",
    "description" : "View your profile PADD"
  },
  {
    "name" : "/wordcloud",
    "description" : "Generate a wordcloud of your most used words"
  },
  {
    "name" : "/badges",
    "description" : "See the badges you've collected"
  }, 
  {
    "name" : "/shop",
    "description" : "Purchase items for your PADD with an interactive shop"
  },
  {
    "name" : "/set_tagline",
    "description" : "Set the tagline on your PADD"
  }
]

@bot.slash_command(
  name="help",
  description="Display a help message for the current channel-specific commands"
)
async def help(ctx:discord.ApplicationContext):
  """
  This function is the main entrypoint of the /help command
  and will display each help message in the channel that it was
  initiated, for the channel it was initiated.
  """
  try:

    logger.info(f"{Style.BRIGHT}{ctx.author.display_name}{Style.RESET_ALL} is checking out the help page in {Style.BRIGHT}{ctx.channel.name}{Style.RESET_ALL}!")

    f = open("./data/help/default.txt")
    default_help_text = f.read()
    f.close()

    f = open(config["commands"]["help"]["data"])
    help_data = json.load(f)
    f.close()

    for help_page in help_data:
      if ctx.channel.id in get_channel_ids_list(help_page["channels"]) and help_page["enabled"]:
        
        text_file = open(help_page["file"], "r")
        help_text = text_file.read()
        text_file.close()
        help_text += "\n\n**Basic commands**\nThese commands can be used mostly anywhere:"
        
        embed=discord.Embed(
          description=help_text,
          color=discord.Color.dark_gold()
        )

        for command in basic_commands:
          embed.add_field(name=f'`{command["name"]}`', value=command["description"], inline=True)

        await ctx.respond(embed=embed, ephemeral=True)
        return
    
    with os.popen("make --no-print-directory version") as line:
      version_raw = line.readlines()
    version = version_raw[0].replace("\n", "").replace("\t"," ").strip()

    message = f"__**AGIMUS {version}** - Help and About__\n"
    message += default_help_text + "\n"

    embed = discord.Embed(
      description="These commands can be used mostly anywhere:",
      title=f"**Basic commands**",
      color=discord.Color.random()
    )

    for command in basic_commands:
      embed.add_field(name=f'`{command["name"]}`', value=command["description"], inline=True)

    embed.set_footer(text="Use this /help command in specific game channels for more detailed help on those games.")

    await ctx.respond(content=message, embed=embed, ephemeral=True)

  except Exception as e:
    logger.info(">>> Encountered error in /help")
    logger.info(traceback.format_exc())
