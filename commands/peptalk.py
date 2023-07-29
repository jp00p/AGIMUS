from common import *

salutations = [
  "Champ", "Fact:", "Everybody says", "Dang..", "Check it:", "Just saying...", "Superstar", "Tiger", "Self", "Know this:", "News alert:",
  "Girl,", "Ace,", "Excuse me but", "Experts agree:", "In my opinion,", "Hear ye, hear ye", "Okay, listen up:"
]

subjects = [
  "The mere idea of you", "Your soul", "Your hair today", "Everything you do", "Your personal style", "Every thought you have", "That sparkle in your eye",
  "Your presence here", "What you got going on", "The essential you", "Your life's journey", "That saucy personality", "Your DNA", "That brain of yours",
  "Your choice of attire", "The way you roll", "Whatever your secret is", "All of y'all"
]

descriptions = [
  "has serious game", "rains magic", "deserves the Nobel Prize", "raises the roof", "breeds miracles", "is paying off big time", "shows mad skills",
  "just shimmers", "is a national treasure", "gets the party hopping", "is the next big thing", "roars like a lion", "is a rainbow factory",
  "is made of diamonds", "makes birds sing", "should be taught in school", "makes my world go 'round", "is 100 percent legit"
]

conclusions = [
  "24/7.", "can I get an amen?", "and that's a fact.", "so treat yourself.", "you feel me?", "that's just science.", "would I lie?", "for reals.",
  "mic drop.", "you hidden gem.", "snuggle bear.", "period.", "can I get a hallelujah?", "now let's dance.", "high five.", "say it again!", "according to CNN.", "so get used to it."
]

@bot.slash_command(
  name="peptalk",
  description="Have AGIMUS give a lil pep talk (due credit to Raccoon Society)"
)
async def peptalk(ctx:discord.ApplicationContext):
  salutation = random.choice(salutations)
  subject = random.choice(subjects)
  description = random.choice(descriptions)
  conclusion = random.choice(conclusions)
  embed = discord.Embed(
    title=salutation,
    description=f"{subject} {description}, {conclusion}",
    color=discord.Color.random()
  )
  await ctx.respond(embed=embed)
