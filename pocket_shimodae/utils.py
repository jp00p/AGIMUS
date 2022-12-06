""" 
a collection of utility functions for poshimo 
this mostly exists because i am bad at imports
"""

from common import *
import random
from .objects.trainer import PoshimoTrainer


def clamp(n: int, minn: int, maxn: int) -> int:
    """clamp a number `n` between a range `minn` and `maxn`"""
    if not minn:
        minn = 0
    return max(min(maxn, n), minn)


def roll(chance:float):
  ''' returns true if roll succeeds '''
  return random.random() <= chance


def get_trainer(discord_id=None, trainer_id=None) -> PoshimoTrainer:
    """
    Get a PoshimoTrainer object from the database based on discord ID or Trainer ID
    """
    logger.info(f"Attempting lookup on poshimo trainer {discord_id}...")
    with AgimusDB(dictionary=True) as query:
        if discord_id:
            sql = """SELECT *, poshimo_trainers.id as trainer_id FROM poshimo_trainers 
            LEFT JOIN users ON poshimo_trainers.user_id = users.id 
            WHERE users.discord_id = %s"""
            vals = (discord_id,)
        elif trainer_id:
            sql = """SELECT *, poshimo_trainers.id as trainer_id FROM poshimo_trainers 
            LEFT JOIN users ON poshimo_trainers.user_id = users.id 
            WHERE poshimo_trainers.id = %s"""
            vals = (trainer_id,)
        query.execute(sql, vals)
        trainer_data = query.fetchone()
        logger.info(f"Trainer found!")
        logger.info(trainer_data)
    return PoshimoTrainer(trainer_data["trainer_id"])


def get_all_trainers() -> list:
    """get a list of discord ids from all the registered trainers"""
    with AgimusDB() as query:
        sql = "SELECT users.discord_id, poshimo_trainers.id FROM poshimo_trainers LEFT JOIN users ON poshimo_trainers.user_id = users.id"
        query.execute(sql)
        all_trainers = [int(i[0]) for i in query.fetchall()]
    return all_trainers


def register_trainer(user_id) -> PoshimoTrainer:
    """
    Register a new trainer to the database

    Parameters
    ----
    `user_id`:`int`
      the users ID from the `users` table

    Returns
    ----
    PoshimoTrainer
    """
    logger.info(f"Attempting to register new trainer {user_id}")
    with AgimusDB() as query:
        sql = "INSERT INTO poshimo_trainers (user_id) VALUES (%s)"
        vals = (user_id,)
        query.execute(sql, vals)
        trainer_id = query.lastrowid
        if trainer_id:
            logger.info(f"Success! new trainer ID: {trainer_id}")
    return PoshimoTrainer(trainer_id)


def generate_random_name() -> str:
    fnames = [
        "Jean Luc",
        "Deanna",
        "Geordi",
        "Miles",
        "Tasha",
        "Brent",
        "William",
        "Reginald",
        "Leah",
        "Kevin",
        "Rishon",
    ]
    lnames = [
        "Picard",
        "Troi",
        "LaForge",
        "O'Brien",
        "Yar",
        "Spiner",
        "Riker",
        "Barclay",
        "Brahams",
        "Uxbridge",
        "Okona",
    ]
    return random.choice(fnames) + " " + random.choice(lnames)
