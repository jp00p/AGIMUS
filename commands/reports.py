from common import *
from utils.check_channel_access import access_check

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
      name="XP gains in the last hour",
      value="gains"
    ),
    discord.OptionChoice(
      name="Level 1 Diagnostic",
      value="diagnostic"
    )
  ]
)

@commands.check(access_check)
# reports() - entrypoint for /reports command
# will help us build fancy looking reports for administration and fun
async def reports(ctx:discord.ApplicationContext, report:str):
  if report == "xp":
    image = generate_xp_report_card()
  elif report == "scores":
    image = generate_scores_report_card()
  elif report == "gains":
    image = generate_gainers_report_card()
  elif report == "diagnostic":
    image = generate_diagnostic_card()
  if image:
    await ctx.respond(file=image, ephemeral=False)


# get_xp_report() - returns a dictionary of overall top xp users
def get_xp_report():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT name,xp FROM users ORDER BY xp DESC LIMIT 10"
  query.execute(sql)
  results = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return results

# get_scores_report() - returns a dictionary of users sorted by top scores
def get_scores_report():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT name,score FROM users ORDER BY score DESC LIMIT 10"
  query.execute(sql)
  results = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return results

# get_gainers_report() - returns a dictionary of users who gained the most xp in the last hour
def get_gainers_report():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "SELECT xp_history.user_discord_id, SUM(xp_history.amount) as amt, users.name FROM xp_history LEFT JOIN users ON xp_history.user_discord_id = users.discord_id WHERE xp_history.time_created > now() - interval 1 hour GROUP BY users.name, xp_history.user_discord_id ORDER BY amt DESC LIMIT 10;"
  query.execute(sql)
  results = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return results
    

# process the xp data and generate an image
def generate_xp_report_card():
  xp_data = get_xp_report()
  title = "AGIMUS REPORT"
  description = "Total XP Overall"
  rows = []
  rank = 1
  for row in xp_data:
    truncated_name = row["name"][:31]
    rows.append("#{:>02d}{spacer:^8}{:>08d}{spacer:^8}{}".format(rank, row["xp"], truncated_name, spacer="•"))
    rank += 1
  return generate_report_card(title, description, rows)


# process the gainers data and generate an image
def generate_gainers_report_card():
  gainers_data = get_gainers_report()
  title = "AGIMUS REPORT"
  description = "Top XP gains in the last hour"
  rows = []
  rank = 1
  if len(gainers_data) < 1:
    rows = ["No data found for the last hour"]
  else:
    for row in gainers_data:
      truncated_name = row["name"][:31]
      rows.append("#{:>02d}{spacer:^2}{:>03d}{spacer:^2}{}".format(rank, int(row["amt"]), truncated_name, spacer="•"))
      rank += 1
  return generate_report_card(title, description, rows)


def get_tables():
  db = getDB()
  query = db.cursor(dictionary=True)
  sql = "show tables;"
  query.execute(sql)
  results = query.fetchall()
  db.commit()
  query.close()
  db.close()
  return results

def generate_diagnostic_card():
  logger.info("generate_diagnostic_card()")
  arows = []
  brows = []
  crows = []
  rows = []
  with os.popen("hostname") as line:
    arows = line.readlines()
  with os.popen("make --no-print-directory version") as line:
    brows = line.readlines()
  with os.popen("df -h") as line:
    crows = line.readlines()
  for row in arows:
    rows.append("Container Name: " + row.replace("\n", "").replace("\t"," "))
  for row in brows:
    rows.append("Version: " + row.replace("\n", "").replace("\t"," "))
  rows.append("DB_HOST: " + DB_HOST)
  for row in crows:
    row = row.replace("Mounted on", "Mounted_on").strip().split()
    cleaned_up_string = f"{row[0]:<11s}{row[1]:<6s}{row[2]:<6s}{row[3]:<6s}{row[4]:<6s}{row[5]:<14s}".replace("Mounted_on", "Mounted on")
    rows.append(cleaned_up_string)
  logger.info(f"rows: '{rows}'")
  title = "LEVEL 1 DIAGNOSTIC"
  description = "AGIMUS System Information"
  return generate_report_card(title, description, rows)

# process the scores data and generate an image
def generate_scores_report_card():
  score_data = get_scores_report()
  title = "AGIMUS REPORT"
  description = "Top scores"
  rows = []
  rank = 1
  for row in score_data:
    truncated_name = row["name"][:31]
    rows.append("#{:>02d}{spacer:^2}{:>08d}{spacer:^2}{}".format(rank, row["score"], truncated_name, spacer="•"))
    rank += 1
  return generate_report_card(title, description, rows)


# generate_report_card(title:str, description:str, rows:list) - generate a generic report - returns a discord.File ready for embedding
# title[required]: the report title
# description[required]: the report description
# rows[required]: a list of rows for the report (max 10 items)
def generate_report_card(title:str, description:str, rows:list):

  normal_font = ImageFont.truetype("images/fixed_width.otf", 18)
  title_font = ImageFont.truetype("images/context.ttf", 63)
  deco_font = ImageFont.truetype("images/context.ttf", 20)

  template_image = "report-template.png" # the base image for all reports (for now)
  image = Image.open(f"./images/{template_image}", "r")
  image = image.convert("RGBA") # just in case

  draw = ImageDraw.Draw(image) # prepare thy pencil!

  # draw title and report description at the top right
  draw.text( (715, 6), title, fill="#ff0000", font=title_font, anchor="rt", align="right")
  draw.text( (715, 70), description, fill="white", font=normal_font, anchor="rt", align="right")

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

  stream_x = 127 # start here
  stream_y = 6
  stream_line_height = 24 # jump this much each line
  stream_colors = ["#882211", "#BB6622", "#BB4411"] # each line could be one of these colors

  # actually draw the random stream of data
  for counter, stream in bit_stream.items():
    stream_line_y = stream_y + (stream_line_height * counter)
    stream_text = " ".join(stream.values())
    draw.text( (stream_x, stream_line_y), stream_text, fill=random.choice(stream_colors), font=deco_font )
    counter += 1

  # done making the silly numbers at the top
  # now draw the actual data in the rows
  text_x = 127 # start here
  text_y = 178
  line_height = 38 # jump this much each line
  counter = 0
  for row in rows[:10]:
    line_y = text_y + (line_height * counter) # calculate our y position for this line
    draw.text( (text_x, line_y), row, fill="white", font=normal_font, anchor="lt", align="left")
    counter += 1

  image.save("./images/reports/report.png")
  return discord.File("./images/reports/report.png")