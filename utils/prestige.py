from common import *

from queries.echelon_xp import db_get_echelon_progress

PRESTIGE_TIERS = {
  0: 'Standard',
  1: 'Nebula',
  2: 'Galaxy',
  3: 'Supernova',
  4: 'Cascade',
  5: 'Nexus',
  6: 'Transcendence'
}

PRESTIGE_THEMES = {
  1: {  # Nebula
    "gradient_start": (0, 0, 0),
    "gradient_end": (24, 16, 48),
    "border_gradient_colors": [
      (75, 0, 130),      # Deep Purple
      (138, 43, 226),    # Violet
      (0, 191, 255)      # Bright Blue
    ],
    "primary": (108, 24, 157),
    "highlight": (148, 64, 197)
  },
  2: {  # Galaxy
    "gradient_start": (0, 0, 0),
    "gradient_end": (20, 60, 70),
    "border_gradient_colors": [
      (0, 20, 50),       # Deep Blue
      (75, 180, 200),    # Teal
      (150, 255, 255)    # White
    ],
    "primary": (30, 100, 125),
    "highlight": (70, 140, 165)
  },
    3: {  # Supernova
    "gradient_start": (0, 0, 0),
    "gradient_end": (30, 10, 10),
    "border_gradient_colors": [
      (255, 50, 50),     # Warm Red
      (255, 140, 50),    # Bright Gold-Orange
      (37, 9, 9)         # Deep Ember/Burnt Red
    ],
    "primary": (200, 60, 40),
    "highlight": (240, 100, 80)
  },
  4: {  # Cascade
    "gradient_start": (0, 0, 0),
    "gradient_end": (16, 32, 16),
    "border_gradient_colors": [
      (0, 255, 100),     # Bright green
      (50, 200, 140),    # Teal
      (160, 255, 240)    # Jade
    ],
    "primary": (40, 200, 120),
    "highlight": (80, 240, 160)
  },
  5: {  # Nexus
    "gradient_start": (0, 0, 0),
    "gradient_end": (40, 30, 64),
    "border_gradient_colors": [
      (255, 0, 255),      # Fuchsia
      (120, 0, 180),      # Indigo
      (0, 255, 255)       # Cyan
    ],
    "primary": (200, 0, 200),
    "highlight": (240, 40, 240)
  },
  6: {  # Transcendence
    "gradient_start": (0, 0, 0),
    "gradient_end": (30, 30, 60),
    "border_gradient_colors": [
      (255, 255, 255),    # White
      (200, 160, 255),    # Lilac
      (120, 180, 255)     # Light Blue
    ],
    "primary": (180, 200, 240),
    "highlight": (220, 240, 255)
  },
}

#    _____          __                                     .__          __
#   /  _  \  __ ___/  |_  ____   ____  ____   _____ ______ |  |   _____/  |_  ____
#  /  /_\  \|  |  \   __\/  _ \_/ ___\/  _ \ /     \\____ \|  | _/ __ \   __\/ __ \
# /    |    \  |  /|  | (  <_> )  \__(  <_> )  Y Y  \  |_> >  |_\  ___/|  | \  ___/
# \____|__  /____/ |__|  \____/ \___  >____/|__|_|  /   __/|____/\___  >__|  \___  >
#         \/                        \/            \/|__|             \/          \/
async def autocomplete_prestige_tiers(ctx: discord.AutocompleteContext):
  user_id = ctx.interaction.user.id
  echelon_progress = await db_get_echelon_progress(user_id)
  current_prestige = echelon_progress['current_prestige_level'] if echelon_progress else 0

  # Show all tiers from Standard up through the user's unlocked level
  options = [
    discord.OptionChoice(name=PRESTIGE_TIERS[i], value=str(i))
    for i in range(current_prestige + 1)
  ]

  # If there are more tiers beyond what they have, add the "???" teaser
  if current_prestige < max(PRESTIGE_TIERS.keys()):
    options.append(discord.OptionChoice(name="???", value="???"))

  return options


# ____   ____      .__  .__    .___       __  .__
# \   \ /   /____  |  | |__| __| _/____ _/  |_|__| ____   ____
#  \   Y   /\__  \ |  | |  |/ __ |\__  \\   __\  |/  _ \ /    \
#   \     /  / __ \|  |_|  / /_/ | / __ \|  | |  (  <_> )   |  \
#    \___/  (____  /____/__\____ |(____  /__| |__|\____/|___|  /
#                \/             \/     \/                    \/
async def is_prestige_valid(ctx: discord.ApplicationContext, prestige:str):
  if prestige == "???":
    await ctx.respond(
      embed=discord.Embed(
        title="Prestige Tier Yet Undiscovered",
        description="Well, that's certainly mysterious...",
        color=discord.Color.blurple()
      ).set_footer(text="🐨"),
      ephemeral=True
    )
    return False

  prestige = int(prestige)
  user_prestige = (await db_get_echelon_progress(ctx.author.id))['current_prestige_level']
  if prestige > user_prestige:
    await ctx.respond(
      embed=discord.Embed(
        title="Nope",
        description="Nice try, but you haven't discovered that Prestige Tier yet...",
        color=discord.Color.red()
      ),
      ephemeral=True
    )
    return False

  return True