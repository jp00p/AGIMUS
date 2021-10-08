import discord
from discord.ext import tasks
import os
import random
import time
import tmdbsimple as tmdb
import requests
import asyncio
import string
from PIL import Image
from fuzzywuzzy import fuzz
#from replit import db
from dotenv import load_dotenv
import mysql.connector