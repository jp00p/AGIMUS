from .common import *
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
      name="XP",
      value="xp"
    )
  ]
)
@commands.check(access_check)
# reports() - entrypoint for /reports command
# will help us build fancy looking reports for administration and fun
async def reports(ctx:discord.ApplicationContext, report:str):
  if report == "xp":
    image = generate_xp_report_card()
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

# generate_xp_report_card() - returns a discord.File ready for embedding
def generate_xp_report_card():
  xp_font = ImageFont.truetype("images/context.ttf", 34)
  title_font = ImageFont.truetype("images/context.ttf", 63)
  deco_font = ImageFont.truetype("images/context.ttf", 20)
  xp_data = get_xp_report()
  
  template_image = "report-template.png"
  image = Image.open(f"./images/{template_image}", "r")
  image = image.convert("RGBA") # just in case

  draw = ImageDraw.Draw(image) # prepare thy pencil!

  # draw title and report description
  draw.text( (416, 6), "AGIMUS Report: XP", fill="#ff0000", font=title_font, anchor="lt", align="left")
  draw.text( (594, 70), "Top XP Overall", fill="white", font=xp_font, anchor="lt", align="left")

  # generate a bunch of fancy random numbers for the top, why not!
  deco_rows = 4
  bit_stream = {}
  for i in range(deco_rows):
    random_bits = {}
    bit_stream[i] = {}
    random_bits[0] = random.randint(0, 99)
    for x in range(1,6):
      random_bits[x] = random.randint(0, 999)
    random_bits[6] = random.randint(0, 99)
    random_bits[7] = random.randint(0, 999)
    random_bits[8] = random.randint(0, 99)
    random_bits[9] = "•"
    random_bits[10] = random.randint(0, 9999)
    random_bits[11] = random.randint(0, 999)

    bit_stream[i][0] = f"{random_bits[0]:02}"
    for b in range(1,6):
      bit_stream[i][b] = "{:03}".format(random_bits[b])
    bit_stream[i][6] = f"{random_bits[6]:02}"
    bit_stream[i][7] = f"{random_bits[7]:03}" 
    bit_stream[i][8] = f"{random_bits[8]:02}"
    bit_stream[i][9] = f"{random_bits[9]}"
    bit_stream[i][10] = f"{random_bits[10]:04}"
    bit_stream[i][11] = f"{random_bits[11]:03}" 

  stream_x = 127
  stream_y = 6
  stream_line_height = 24
  stream_colors = ["#882211", "#BB6622", "#BB4411"]

  for counter, stream in bit_stream.items():
    stream_line_y = stream_y + (stream_line_height * counter)
    stream_text = " ".join(stream.values())
    draw.text( (stream_x, stream_line_y), stream_text, fill=random.choice(stream_colors), font=deco_font )
    counter += 1

  # done making the silly numbers at the top
  # now draw the actual scores

  text_x = 127
  text_y = 178
  line_height = 38
  counter = 0
  colors = ["#FF0000", "#FF9900", "#CC6699", "#BB4411", "#CC6666", "#FF9966"]

  for row in xp_data:
    line_y = text_y + (line_height * counter)
    rank = counter + 1
    if counter <= 4:
      color = colors[counter]
    else:
      color = colors[5]
    truncated_name = row["name"][0:32]
    draw.text( (text_x, line_y), "{:<2} {spacer:^4} {:>08d} {spacer:^4} {}".format(rank, row["xp"], truncated_name, spacer="•"), fill=color, font=xp_font, anchor="lt", align="left")
    counter += 1

  image.save("./images/reports/xp-report.png")
  return discord.File("./images/reports/xp-report.png")
