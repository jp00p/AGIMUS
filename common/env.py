import os

from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv('LOG_LEVEL') or "INFO"

BOT_CONFIGURATION_FILEPATH = os.getenv('BOT_CONFIGURATION_FILEPATH')
BOT_LOCAL_CONFIGURATION_FILEPATH = os.getenv('BOT_LOCAL_CONFIGURATION_FILEPATH')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_SEED_FILEPATH = os.getenv('DB_SEED_FILEPATH')

