# Friends of DeSoto Bot

The Friends of DeSoto are a group of fans of Star Trek and [The Greatest Generation podcast](http://gagh.biz).

## Usage

This discord bot is built with python using the [discord.py library](https://discordpy.readthedocs.io/en/stable/api.html) and requires a mysql db with credentials stored in a .env file ([.env example](.env-example)). To develop locally, docker is used to standardize infrastructure and dependencies.

```bash
# Clone FoDBot source
git clone https://github.com/jp00p/FoDBot-SQL.git && cd FoDBot-SQL

# Fill out .env vars...
cp .env-example .env

# Build and start the docker containers
make docker-start

# Mysql session with database
make db-mysql

# Bash session in mysql container
make db-bash

# Mysql dump to file
make db-dump

# Mysql load from a file
make db-load

# Stop the containers
make docker-stop

# Blatent cheating
UPDATE users SET score=42069, spins=420, jackpots=69, wager=25, high_roller=1 WHERE id=1;
```

## Permissions

First you will need a discord app and bot token to send messages. See this youtube playlist to learn how: https://www.youtube.com/playlist?list=PLRqwX-V7Uu6avBYxeBSwF48YhAnSn_sA4

Additional [discord role permissions](https://support.discord.com/hc/en-us/articles/206029707-Setting-Up-Permissions-FAQ):

- View channels
- Send messages
- Send messages in thread
- Add reaction
- Manage messages

Also for the Slash Commands you'll need to enable the `applications.commands` Scope for your bot _Application_ via the OAuth2 URL Generator.
Instructions for how to do this are available through this video at the 58 second timestamp: https://youtu.be/ygc-HdZHO5A?t=58

## Commands

Bot commands are triggered by typing an exclamation point followed by a command. Commands must be defined in the [configuration.json](configuration.json) file, a python file in the [commands directory](commands), and an import line added to [main.py](main.py).

| Command                                                                                                                                                           | File                                    | Description                                                                                                                             |
| :-----------------------------------------------------------------------------------------------------------------------------------------------                  | :-------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| `!buy [profile \| badge \| role] [item_number]`                                                                                                                   | [buy.py](commands/buy.py)               | Allows user to "buy" a profile, badge or role from points earned playing bot games (see `!shop` command for options)                    |
| `!categories`                                                                                                                                                     | [categories.py](commands/categories.py) | Show possible trivia categories                                                                                                         |
| `!dustbuster`                                                                                                                                                     | [dustbuster.py](commands/dustbuster.py) | Return 5 random trek characters as discussion prompt                                                                                    |
| `!fmk`                                                                                                                                                            | [fmk.py](commands/fmk.py)               | Return 3 random trek characters as discussion prompt                                                                                    |
| `!help`                                                                                                                                                           | [help.py](commands/help.py)             | Show a help message for a specific channel                                                                                              |
| `!info [tng \| voy \| ds9 \| friends \| firefly \| simpsons \| enterprise \| tos \| lowerdecks \| disco \| picard \| tas \| sunny] [s##e##]`                      | [info.py](commands/info.py)             | Show information about a specific episode!                                                                                              |
| `!jackpot`                                                                                                                                                        | [jackpot.py](commands/jackpot.py)       | Show the current jackpot value                                                                                                          |
| `!jackpots`                                                                                                                                                       | [jackpots.py](commands/jackpots.py)     | Show the last 10 jackpot winners                                                                                                        |
| `!ping`                                                                                                                                                           | [ping.py](commands/ping.py)             | respond pong                                                                                                                            |
| `!poker`                                                                                                                                                          | [poker.py](commands/poker.py)           | 5 card stud style game                                                                                                                  |
| `!profile`                                                                                                                                                        | [profile.py](commands/profile.py)       | Generate profile card with user statistics/options                                                                                      |
| `!nasa [today\|YYYY-MM-DD]`                                                                                                                                       | [nasa.py](commands/nasa.py)             | pulls a random or specific 'picture of the day' from nasa api                                                                           |
| `!qget [user]`                                                                                                                                                    | [q.py](commands/q.py)                   | Get the information in mysql for a specific user                                                                                        |
| `!qset [user] [score \| spins \| jackpots \| wager \| high_roller \| chips \| profile_card \| profile_badge \| xp] [new-value]`                                         | [q.py](commands/q.py)                   | Set a value of a specific user in mysql                                                                                                 |
| `!quiz [tng \| voy \| ds9 \| friends \| firefly \| simpsons \| enterprise \| tos \| lowerdecks \| disco \| picard \| tas \| sunny]`                               | [quiz.py](commands/quiz.py)             | Guess the episode from a screen-shot!                                                                                                   |
| `!randomep [trek \| nontrek \| any \| tos \| tas \| tng \| ds9 \| voy \| enterprise \| lowerdecks \| disco \| picard \| friends \| firefly \| simpsons \| sunny]` | [randomep.py](commands/randomep.py)     | Show information about a random episode!                                                                                                |
| `!scores`                                                                                                                                                         | [scores.py](commands/scores.py)         | Show the leaderboard of points                                                                                                          |
| `!setwager`                                                                                                                                                       | [setwager.py](commands/setwager.py)     | Wager value for poker game                                                                                                              |
| `!shop [profiles \| badges \| roles]`                                                                                                                             | [shop.py](commands/shop.py)             | Possible options to `!buy`                                                                                                              |
| `!slots [tng \| ds9 \| voy \| holodeck \| ships]`                                                                                                                 | [slots.py](commands/slots.py)           | Slot machine game with trek characters or ships                                                                                         |
| `!testslots`                                                                                                                                                      | [testslots.py](commands/testslots.py)   | Restricted command to run through 10k `!slots` commands to test success/failure rate                                                    |
| `!trekduel`                                                                                                                                                       | [trekduel.py](commands/trekduel.py)     | Return 2 random trek characters as discussion prompt                                                                                    |
| `!trektalk`                                                                                                                                                       | [trektalk.py](commands/trektalk.py)     | Return a random trek related discussion prompt                                                                                          |
| `!triv`                                                                                                                                                           | [triv.py](commands/triv.py)             | Trivia game                                                                                                                             |
| `!tuvix`                                                                                                                                                          | [tuvix.py](commands/tuvix.py)           | Return 2 random trek characters as discussion prompt                                                                                    |

## Slash Commands

Slash commands are triggered by typing a forward slash (`/`) followed by the command text. The same basic rules apply as the regular ! commands above as far as the info necessary in the [configuration.json](configuration.json) file, python file in the [commands directory](commands), and import line in [main.py](main.py).

| Command                                                                                                                                                           | File                                    | Description                                                                                                                             |
| :-----------------------------------------------------------------------------------------------------------------------------------------------                  | :-------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| `/drop <query]>`                                                                                                                                                  | [drop.py](commands/drop.py)             | Posts a .mp4 drop file if it finds a match from the user's query                                                                        |
| `/drops`                                                                                                                                                          | [drop.py](commands/drop.py)             | Replies with a message to the user with a full list of the drops available from `/drop`                                                 |

### configuration.json

The [configuration.json](configuration.json) file defines metadata about each command like what channel they can be executed in, what parameters can be passed, if the command requires additional data loaded, or if it should be enabled/disabled.

```json
"setwager": {
  "channels": [821892686201094154, 934827868066828308],
  "enabled": true,
  "data": null,
  "parameters": [{
    "name": "wager_value",
    "allowed": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25],
    "required": true
  }]
}
```

The file also provides the "Guild ID" for your server, note this is required in order for the slash commands to register properly and will cause a permissions error on startup if not provided!
```json
"guild_ids": [
  820440093898440756
]
```

### commands/command.py

Each command requires a python script that accepts a discord message as input where the first word matches the filename (Example: `!setwager 25` => [commands/setwager.py](commands/setwager.py))

```python
from .common import *

# setwager() - Entrypoint for !setwager command
# message[required]: discord.Message
# This function is the main entrypoint of the !setwager command
# and will a user's wager value to the amount passed between 1-25
async def setwager(message:discord.Message):
  min_wager = 1
  max_wager = 25
  wager_val = message.content.lower().replace("!setwager ", "")
  player = get_player(message.author.id)
  current_wager = player["wager"]
  if wager_val.isnumeric():
    wager_val = int(wager_val)
    if wager_val >= min_wager and wager_val <= max_wager:
      set_player_wager(message.author.id, wager_val)
      msg = f"{message.author.mention}: Your default wager has been changed from `{current_wager}` to `{wager_val}`"
      await message.channel.send(msg)
    else:
      msg = f"{message.author.mention}: Wager must be a whole number between `{min_wager}` and `{max_wager}`\nYour current wager is: `{current_wager}`"
      await message.channel.send(msg)
  else:
    msg = f"{message.author.mention}: Wager must be a whole number between `{min_wager}` and `{max_wager}`\nYour current wager is: `{current_wager}`"
    await message.channel.send(msg)


# set_player_wager(discord_id, amt)
# discord_id[required]: int
# amt[required]: int
# This function takes a player's discord ID
# and a positive integer and updates the wager
# value for that user in the db
def set_player_wager(discord_id, amt):
  db = getDB()
  amt = max(amt, 0)
  query = db.cursor()
  sql = "UPDATE users SET wager = %s WHERE discord_id = %s"
  vals = (amt, discord_id)
  query.execute(sql, vals)
  db.commit()
  query.close()
  db.close()
```

### main.py

Each command requires an explicit import in the [main.py](main.py) script.

```python
from commands.setwager import setwager
```


### Utils

#### generate_episode_json.py
The repo also currently provides a way to automatically generate the files for the Greatest Gen `.json` files located under `data/episodes/` (such as `tgg_voy.json` for example). The utility is under `utils` as `generate_episode_json.py`.

The script uses Google to gather some of the metadata necessary for each entry, so you'll need to provide two additional ENV variables if you'd like to use this script.

```
export GOOGLE_API_KEY=
export GOOGLE_CX=
```

Step-by-step instructions for how to generate these credentials are documented in this [Stack Overflow post](https://stackoverflow.com/a/37084643)

Once those have been placed in your .env file, you can execute the script by providing the series prefix and path to the desired output file.

```bash
python utils/generate_episode_json.py -p VOY -o data/episodes/voy.json
```