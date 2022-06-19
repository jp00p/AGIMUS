from .common import *

# bot_affirmations(message) - responds to bot compliments
# message[required]: discord.Message
async def handle_bot_affirmations(message:discord.Message):
    for affirmation in config["bot_affirmations"]:
        if affirmation in message.content.lower():
            await message.add_reaction(EMOJI["love"])
            await message.reply(random.choice(config["bot_responses"]), mention_author=True)
            break