import datetime
import json
import math
import random

import discord

from common import logger, get_channel_ids_list, config
import queries.arena as db
from utils.show_utils import get_show_embed


phrases_for_splitting_vote = [
    "They’re about the same",
    "They’re about the same",
    "Six of one, half dozen of the other",
    "I can’t choose between them",
    "I can’t decide",
    "They’re both certainly episodes of Star Trek",
    "Can’t they just be friends?",
]

phrases_for_no_vote = [
    "I haven’t seen both episodes",
    "I don’t recognize one of the episodes",
    "I just want to feel included",
    "We get XP for voting, right?",
    "Are these both real episodes?",
]

cached_show_details = {}


def arena_task(bot: discord.Bot):
    """
    Two episodes enter!  One episode leaves! …with more points.
    
    What is the best episode of Star Trek?  Let the FoDs decide. Every hour, two episodes are pitted against each other
    in a Disord poll to see which one is “better”. When the poll expires, then we adjust based on how much better than
    expected one did. If we expect 90% to choose episode A, and B gets 25% of the vote, then B will take ranking points
    away from A.
    """
    
    def get_expected_percent(points_a: float, points_b: float) -> float:
        """
        Returns the percent win by A that we expect based on their points.  This function is very close to just being
        a-b when they are close, but as they get father away, it approaches 100 or -100
        
        example outputs:
        (55, 45) → 54.993
        (50, 100) or (25, 75) → 26.855
        (300, 2) → 99.746 because there will always be someone who thinks Code of Honor is better than In the Pale Moonlight
        """
        return 100 / (math.exp((points_b - points_a) / 49.9) + 1)
    
    
    def poll_winning_percent(poll: discord.Poll) -> tuple[float, int]:
        """
        Get the percent that voted for the first answer. The third answer is “same”
        """
        votes_for_a = poll.answers[0].count
        votes_for_b = poll.answers[1].count
        split_votes = poll.answers[2].count
        total_votes = votes_for_a + votes_for_b + split_votes
        if total_votes == 0:
            return -100, 0
        
        return ((votes_for_a + split_votes/2) / total_votes) * 100, total_votes
    
    async def finish_old_polls():
        """
        Find the polls that have expired, and move points to the one the beat the spread
        """
        for open_poll in await db.get_open_polls():
            print(open_poll)
            discord_poll = bot.get_poll(open_poll['message_id'])
            if discord_poll is None:
                logger.error(f"We’ve lost the message attached to the poll with message_id {open_poll['message_id']}!")
                await db.close_poll(open_poll['message_id'], -1., -1)
                continue
            if not discord_poll.has_ended():
                print(f"Poll will expire at {discord_poll.expiry.isoformat()}")
                continue
                
            episode_a = await db.get_episode(open_poll['episode_a_id'])
            episode_b = await db.get_episode(open_poll['episode_b_id'])
            expected_percent = get_expected_percent(episode_a['rank_points'], episode_b['rank_points'])
            actual_percent, total_votes = poll_winning_percent(discord_poll)
            
            if total_votes < 1:
                logger.info(f"Not counting poll with only {total_votes} vote on it")
            else:
                full_voter_count = config["tasks"]["arena"]["voter_full_count"]
                points_to_move = (actual_percent - expected_percent) * \
                                 (1 if total_votes - 1 > full_voter_count else (total_votes - 1) / full_voter_count)
                await db.update_episodes(episode_a['id'], episode_b['id'], points_to_move)
                logger.info(f"Moving {points_to_move} arena points from {episode_a['episode_name']} to {episode_b['episode_name']}")
            await db.close_poll(open_poll['message_id'], actual_percent, total_votes)
            

    def get_episode_details(episode: db.Episode) -> tuple[discord.Embed, str]:
        show = episode["show_name"]
        if show not in cached_show_details:
            with open(f"./data/episodes/{show}.json") as f:
                cached_show_details[show] = json.load(f)
        show_data = cached_show_details[show]
        embed = get_show_embed(show_data, episode["number"], show)
        return embed, embed.title.replace("\n", " ")
    
    async def create_new_poll():
        """
        Choose two episodes and create a new poll for them
        """
        episode_a = await db.get_next_episode()
        current_hour = datetime.datetime.now().hour
        episode_b = await db.get_nearest_episode(episode_a['id'], same_show=(current_hour % 2 == 0))
        episode_a_embed, episode_a_name = get_episode_details(episode_a)
        episode_b_embed, episode_b_name = get_episode_details(episode_b)
    
        channel_list = [bot.get_channel(c_id) for c_id in get_channel_ids_list(config["tasks"]["arena"]["channels"])]
        poll = discord.Poll("Which episode is better", duration=24, allow_multiselect=False) \
            .add_answer(episode_a_name) \
            .add_answer(episode_b_name) \
            .add_answer(random.choice(phrases_for_splitting_vote)) \
            .add_answer(random.choice(phrases_for_no_vote))
        for channel in channel_list:
            await channel.send(embeds=[episode_a_embed, episode_b_embed])
            poll_message = await channel.send(poll=poll)
            await db.create_new_poll({
                "message_id": poll_message.id,
                "episode_a_id": episode_a['id'],
                "episode_b_id": episode_b['id'],
            })
        logger.info(f"Created new Tsunkatse arena battle between {episode_a_name} and {episode_b_name}")

    async def process_polls():
        await finish_old_polls()
        await create_new_poll()


    return {
        "task": process_polls,
        "crontab": config["tasks"]["arena"]["crontab"]
    }