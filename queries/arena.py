from typing import TypedDict

from typing_extensions import NotRequired

from utils.database import AgimusDB


class Episode(TypedDict):
    id: int
    show_name: str
    number: int
    episode_name: str
    rank_points: float
    number_of_matches: int

class Poll(TypedDict):
    message_id: int
    episode_a_id: int
    episode_b_id: int
    result: NotRequired[float]
    vote_count: NotRequired[int]
    
    
async def get_episode(id: int) -> Episode:
    sql = """SELECT *
    FROM arena_episodes
    WHERE id = %s
    """
    async with AgimusDB(dictionary=True) as query:
        await query.execute(sql, (id, ))
        return await query.fetchone()
    
async def get_next_episode() -> Episode:
    sql = """SELECT *
    FROM arena_episodes
    ORDER BY number_of_matches, RAND()
    LIMIT 1
    """
    async with AgimusDB(dictionary=True) as query:
        await query.execute(sql)
        return await query.fetchone()

async def get_nearest_episode(id: int, same_show: bool=False) -> Episode:
    """
    Get the episode with the closest score as the one already selected that has NOT been in a match with it before.
    `same_show` will keep it in the family.
    """
    sql = """ SELECT b.*
    FROM arena_episodes a
    INNER JOIN arena_episodes b
    ON a.id != b.id
    AND b.id NOT IN (SELECT episode_b_id FROM arena_polls WHERE episode_a_id = a.id)
    AND b.id NOT IN (SELECT episode_a_id FROM arena_polls WHERE episode_b_id = a.id)
    """
    if same_show:
        sql += """ AND a.show_name = b.show_name
        """
    sql += """ WHERE a.id = %s
    ORDER BY abs(a.rank_points - b.rank_points), number_of_matches, RAND()
    LIMIT 1
    """
    async with AgimusDB(dictionary=True) as query:
        await query.execute(sql, (id, ))
        return await query.fetchone()
    
async def update_episodes(winner_id: int, loser_id: int, amount: float):
    """
    Move points from the loser to the winner
    """
    sql = """ UPDATE arena_episodes
    SET rank_points = rank_points + %s
    WHERE id = %s
    """
    async with AgimusDB() as query:
        await query.execute(sql, (amount, winner_id, ))
        await query.execute(sql, (-amount, loser_id, ))


async def get_open_polls() -> list[Poll]:
    """
    Get all polls that we think are still open.
    """
    sql = """ SELECT *
    FROM arena_polls
    WHERE result IS NULL
    """
    async with AgimusDB(dictionary=True) as query:
        await query.execute(sql)
        return await query.fetchall()

async def close_poll(message_id: int, result: float, voter_count: int):
    """
    We’re finished with a poll.
    """
    sql = """ UPDATE arena_polls
    SET result = %s,
        voter_count = %s
    WHERE message_id = %s
    """
    async with AgimusDB() as query:
        await query.execute(sql, (result, voter_count, message_id,))
        
async def create_new_poll(poll_data: Poll):
    """
    Save a poll that has already been added to the Discord.
    """
    sql = """ INSERT INTO arena_polls
    (message_id, episode_a_id, episode_b_id)
    VALUES (%s, %s, %s)
    """
    ep_count_sql = """ UPDATE arena_episodes
    SET number_of_matches = number_of_matches + 1
    WHERE id = %s
    """
    args = (poll_data['message_id'], poll_data['episode_a_id'], poll_data['episode_b_id'])
    async with AgimusDB() as query:
        await query.execute(sql, args)
        await query.execute(ep_count_sql, (poll_data["episode_a_id"], ))
        await query.execute(ep_count_sql, (poll_data["episode_b_id"], ))
        


    