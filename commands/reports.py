from os import system
from common import *
import platform
from datetime import date as dtdate
from utils.check_channel_access import access_check
from prettytable import PrettyTable, MARKDOWN, PLAIN_COLUMNS, ORGMODE
from prettytable.colortable import ColorTable, Themes

@bot.slash_command(
  name="reports",
  description="Show various AGIMUS reports"
)
@option(
  name="report",
  description="Choose a report",
  required=True,
  choices=[
    discord.OptionChoice(
      name="XP overall",
      value="xp"
    ),
    discord.OptionChoice(
      name="Total scores",
      value="scores"
    ),
    discord.OptionChoice(
      name="Channel Activity",
      value="activity"
    ),
    discord.OptionChoice(
      name="XP gains in the last hour",
      value="gains"
    ),
    discord.OptionChoice(
      name="Level 1 Diagnostic",
      value="diagnostic"
    )
  ]
)
@option(
  name="report_style",
  description="Fancy report or markdown report?",
  required=True,
  choices=[
    discord.OptionChoice(
      name="Fancy",
      value="fancy"
    ),
    discord.OptionChoice(
      name="Markdown",
      value="markdown"
    )
  ]
)
@commands.check(access_check)
async def reports(ctx:discord.ApplicationContext, report:str, report_style:str):
  """
  entrypoint for /reports command
  will help us build fancy looking reports for administration and fun
  """
  await ctx.defer()
  try:
    if report == "xp":
      response = generate_xp_report_card(report_style)
    elif report == "scores":
      response = generate_scores_report_card(report_style)
    elif report == "gains":
      response = generate_gainers_report_card(report_style)
    elif report == "diagnostic":
      response = generate_diagnostic_card(report_style)
    elif report == "activity":
      response = generate_channel_activity_report_card(report_style)
    if response:
      # send an image-based report
      if report_style == "fancy":
        await ctx.followup.send(file=response, ephemeral=False)
      # send a markdown text-based report
      if report_style == "markdown":
        await ctx.followup.send(response)
    else:
      await ctx.followup.send("There was an issue generating your report, sorry!")
  except Exception as e:
    logger.info(traceback.format_exc())
    logger.info(f"Error generating report: {e}")
    


def get_xp_report():
  """
  returns a dictionary of overall top xp users
  """
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT name,level,xp FROM users ORDER BY xp DESC LIMIT 25"
    query.execute(sql)
    results = query.fetchall()
  return results

def get_scores_report():
  """
  returns a dictionary of users sorted by top scores
  """
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT name,score FROM users ORDER BY score DESC LIMIT 25"
    query.execute(sql)
    results = query.fetchall()
  return results

def get_channel_activity_report():
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT SUM(amount) as xp_amount, channel_id FROM xp_history WHERE time_created > NOW() - INTERVAL 1 DAY GROUP BY channel_id ORDER BY SUM(amount) DESC LIMIT 15"
    query.execute(sql)
    results = query.fetchall()
  return results

def get_gainers_report():
  """
  returns a dictionary of users who gained the most xp in the last hour
  """
  with AgimusDB(dictionary=True) as query:
    sql = "SELECT xp_history.user_discord_id, SUM(xp_history.amount) as amt, users.name FROM xp_history LEFT JOIN users ON xp_history.user_discord_id = users.discord_id WHERE xp_history.time_created > now() - interval 1 hour GROUP BY users.name, xp_history.user_discord_id ORDER BY amt DESC LIMIT 25;"
    query.execute(sql)
    results = query.fetchall()
  return results
    

def generate_channel_activity_report_card(type:str):
  channel_names = {v:k for k,v in config["channels"].items()}
  activity_data = get_channel_activity_report()
  title = "AGIMUS REPORT"
  description = "Most active channels in the last day"
  rank = 1
  table = PrettyTable()
  table.field_names = ["Rank", "Channel", "XP gains"] 
  for row in activity_data:
    channel_name = channel_names[int(row["channel_id"])]
    table.add_row([rank, channel_name, row["xp_amount"]])
    rank += 1
  return generate_report_card(title, description, table, type)

def generate_xp_report_card(type:str):
  """
  process the xp data and generate an image
  """
  xp_data = get_xp_report()
  title = "AGIMUS REPORT"
  description = "Total XP Overall"
  rank = 1
  table = PrettyTable()
  table.field_names = ["Rank", "XP", "Level", "Name"]
  for row in xp_data:
    truncated_name = row["name"][:31]
    table.add_row([rank, row["xp"], row["level"], truncated_name])
    rank += 1
  return generate_report_card(title, description, table, type)


def generate_gainers_report_card(type:str):
  """
  process the gainers data and generate an image
  """
  gainers_data = get_gainers_report()
  title = "AGIMUS REPORT"
  description = "Top XP gains in the last hour"
  rows = []
  rank = 1
  table = PrettyTable()
  if len(gainers_data) < 1:
    rows = ["No data found for the last hour"]
  else:
    table.field_names = ["Rank", "XP Gained", "Name"]
    for row in gainers_data:
      truncated_name = row["name"][:31]
      table.add_row([rank, row["amt"], truncated_name])
      #rows.append("#{:>02d}{spacer:^2}{:>03d}{spacer:^2}{}".format(rank, int(row["amt"]), truncated_name, spacer="•"))
      rank += 1
  return generate_report_card(title, description, table, type, rows)


def get_num_users():
  """
  get number of users registered to the database
  """
  with AgimusDB(dictionary=True) as query:
    sql = "select count(id) as `num_users` from users;"
    query.execute(sql)
    results = query.fetchall()
  return results

def generate_diagnostic_card(type:str):
  arch_info = []
  free = []
  os_info = []
  version_raw = []
  storage = []
  system_info = ""
  num_users_raw = get_num_users()
  for row in num_users_raw:
    num_users = row["num_users"]
  intro_data = [] # data that will appear above the table in the report
  with os.popen("uname -m") as line:
    arch_info = line.readlines()  
  with os.popen("uname | tr [[:upper:]] [[:lower:]]") as line:
    os_info = line.readlines()
  with os.popen("free -h | grep Mem: | awk '{print $3 \"/\" $2}'") as line:
    free = line.readlines()
  system_info = arch_info[0].replace("\n", " ").strip() + " • " + os_info[0].replace("\n", " ").strip() + " • RAM " + free[0].replace("\n", " ").strip()
  with os.popen("make --no-print-directory version") as line:
    version_raw = line.readlines()
  version = version_raw[0].replace("\n", "").replace("\t"," ").strip()
  intro_data.append("AGIMUS " + version + " • " + str(num_users) + " users • " + datetime.now().isoformat())
  intro_data.append("HOST: " + platform.node() + " • " + system_info)
  intro_data.append("DATABASE: " + DB_HOST)
  with os.popen("df -h") as line:
    storage = line.readlines()
  table = PrettyTable()
  table.field_names = ["Filesystem", "Size", "Used", "Avail", "Use%", "Mounted on"]
  for row in storage[1:]:
    # remove all whitespace, all double whitespace, and turn into a list
    row = row.replace("\n", "").replace("\t", "").strip()
    row = re.sub(" +", " ", row)
    row = row.split()
    # add to prettytable
    table.add_row([row[0], row[1], row[2], row[3], row[4], row[5]])
  title = "LEVEL 1 DIAGNOSTIC"
  description = "AGIMUS System Information"
  return generate_report_card(title, description, table, type, intro_data)

def generate_scores_report_card(type:str):
  """
  process the scores data and generate an image
  """
  score_data = get_scores_report()
  title = "AGIMUS REPORT"
  description = "Top scores"
  rows = []
  rank = 1
  table = PrettyTable()
  logger_table = ColorTable(theme=Themes.OCEAN)
  logger_table.align = "l"
  table.field_names = ["Rank", "Score", "Name"]
  for row in score_data:
    truncated_name = row["name"][:31]
    table.add_row([rank, row["score"], truncated_name])
    logger_table.add_row([rank, row["score"], truncated_name])
    rank += 1
  logger_table.field_names = table.field_names
  logger.info(f"\n{logger_table.get_string()}\n")
  return generate_report_card(title, description, table, type)


def generate_report_card(title:str, description:str, table:PrettyTable, type:str, additional_rows:list=[]):
  table.align = "l"
  table.set_style(ORGMODE)
  table_text = table.get_string()
  if type == "markdown":
    # generate markdown report
    md_message  = f"{get_emoji('agimus')} **{title}** {get_emoji('agimus')}\n"
    md_message += f"- {description}\n"
    md_message += f"```"
    if additional_rows:
      md_message += "\n".join(additional_rows) + "\n"
    md_message += table_text
    md_message += f"```"
    return md_message
  else:
    # generate fancy report
    normal_font = ImageFont.truetype("fonts/FiraCode-SemiBold.ttf", 24)
    title_font = ImageFont.truetype("fonts/context.ttf", 63)
    deco_font = ImageFont.truetype("fonts/context.ttf", 22)
    table_rows = table_text.split("\n")

    image_padding = 15
    image_min_width = 712
    image_min_height = 460
    additional_row_width = 0
    
    # do all the base image size calculations
    row_text_height = (len(table_rows) * 18)
    
    if len(additional_rows) > 0:
      row_text_height += (len(additional_rows) * 18) + 44

    row_text_width = len(max(table_rows, key=len).rstrip()) * 19 + 100
    
    if len(additional_rows) > 0:
      additional_row_width = len(max(additional_rows, key=len).rstrip()) * 19 + 100

    if row_text_width > image_min_width:
      image_min_width = row_text_width
    
    if additional_row_width > image_min_width:
      image_min_width = additional_row_width
    
    image_base_width = image_min_width + (image_padding*2) 
    image_base_height = image_min_height + (image_padding*2) + row_text_height

    # done calculating size of image, now create the image
    base_image = Image.new("RGBA", (image_base_width, image_base_height), (0, 0, 0))

    # paste the template parts on the image
    template_part_top_left = Image.open("./images/templates/report_template_top_left.png")
    base_image.paste(template_part_top_left, (image_padding, image_padding), template_part_top_left)

    template_part_top_right = Image.open("./images/templates/report_template_top_right.png")
    tr_w, tr_h = template_part_top_right.size
    base_image.paste(template_part_top_right, (image_base_width-tr_w-image_padding, 120), template_part_top_right)

    template_part_bottom_left = Image.open("./images/templates/report_template_bottom_left.png")
    bl_w, bl_h = template_part_bottom_left.size
    base_image.paste(template_part_bottom_left, (image_padding, image_base_height-bl_h-image_padding), template_part_bottom_left)
    # done pasting
    
    # get ready to draw a bunch of text
    draw = ImageDraw.Draw(base_image) 
    base_w, base_h = base_image.size

    # generate a bunch of fancy random numbers for the top, why not!
    deco_rows = 4 # 4 rows of number
    bit_stream = {} # this will hold the actual strings at the end
    for i in range(deco_rows):
      # number grouping based on a random LCARS image i saw
      random_bits = {} # this holds the ints for formatting
      bit_stream[i] = {}
      for x in range(1,6):
        random_bits[x] = random.randint(0, 999) # random int
        bit_stream[i][x] = "{:03}".format(random_bits[x]) # format the string
      for x in [0, 6, 8]:    
        random_bits[x] = random.randint(0, 99)
        bit_stream[i][x] = f"{random_bits[x]:02}" 
      for x in [7, 11]:
        random_bits[x] = random.randint(0, 999) 
        bit_stream[i][x] = f"{random_bits[x]:03}"
      random_bits[9] = "•"
      random_bits[10] = random.randint(0, 9999)
      bit_stream[i][9] = f"{random_bits[9]}"
      bit_stream[i][10] = f"{random_bits[10]:04}"

    # calculate lines and spacing and colors for stream
    stream_x = 135 # start here
    stream_y = image_padding
    stream_line_height = 24 # jump this much each line
    stream_colors = ["#882211", "#BB6622", "#BB4411"] # each line could be one of these colors

    # actually draw the random stream of data
    for counter, stream in bit_stream.items():
      stream_line_y = stream_y + (stream_line_height * counter)
      stream_text = " ".join(stream.values())
      draw.text( (stream_x, stream_line_y), stream_text, fill=random.choice(stream_colors), font=deco_font )
      counter += 1

    # done making the silly numbers at the top

    # draw title and report description at the top right
    # after data stream so it's "on-top"
    draw.text( (base_w-image_padding, image_padding), title, fill="#ff0000", font=title_font, anchor="rt", align="right")
    draw.text( (base_w-image_padding, 73), description, fill="white", font=normal_font, anchor="rt", align="right")

    # now draw the actual data in the rows
    # calculate lines and spacing for row data
    text_x = 135 # start here
    text_y = 188
    line_height = 44 # jump this much each line
    counter = 0
    for row in additional_rows:
      line_y = text_y + (line_height * counter) # calculate our y position for this line
      draw.text( (text_x, line_y), row, fill="white", font=normal_font, anchor="lt", align="left")
      counter += 1
    if len(table.rows) > 0:
      line_y = text_y + (line_height * counter)
      # now draw the pretty table in the report
      draw.text( (text_x, line_y), table_text, fill="white", font=normal_font, align="left")
    if not os.path.exists("./images/reports"):
      os.makedirs("./images/reports")
    # save it
    base_image.save("./images/reports/report.png")
    # all done
    return discord.File("./images/reports/report.png")
