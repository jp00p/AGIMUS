import json
import random
import re

import discord
from colorama import Style
from discord.ext import commands

from utils.check_channel_access import access_check
from utils.show_utils import title_autocomplete
from common.logs import logger
import queries.arena as db


with open("data/info.json") as f:
    show_data:dict[str, dict[str, bool|str]] = json.load(f)


class ResultsView(discord.ui.DesignerView):
    """
    A designer view to make the results all pretty.
    """
    def __init__(self, episode_count: int, min_runs: int, max_runs: int, show: str|None = None):
        super().__init__(timeout=0, store=False)
        self.all_trek = show is None
        self.episode_count = episode_count
        self.add_item(discord.ui.TextDisplay(f"# The best and worst of {'all Star Trek' if self. all_trek else show}!\n"
                                             f"There are {episode_count} episodes, and they have been through the arena between "
                                             f"{min_runs} and {max_runs} times"))
        
    def add_winners(self, winners: list[dict]):
        best_container = discord.ui.Container(color=discord.Colour.random())
        # best_container.add_text("## The Best")
        for index, ep in enumerate(winners):
            text = (f"{index + 1}. {ep['show_name'] if self.all_trek else ''} S{ep['season']}E{ep['episode_number']}: "
                    f"[**{ep['episode_name']}**](https://memory-alpha.fandom.com/wiki/{ep['memoryalpha']})\n"
                    f" {ep['description']}")
            if ep['image']:
                thumbnail = discord.ui.Thumbnail(ep['image'])
                best_container.add_section(discord.ui.TextDisplay(text), accessory=thumbnail)
            else:
                best_container.add_text(text)
        self.add_item(best_container)
        
    def add_losers(self, losers: list[dict]):
        worst_container = discord.ui.Container(color=discord.Colour.random())
        # worst_container.add_text("### The Worst")
        for index, ep in reversed(list(enumerate(losers))):
            worst_container.add_text(
                f"{self.episode_count - index}. {ep['show_name'] if self.all_trek else ''} S{ep['season']}E{ep['episode_number']}: "
                f"[**{ep['episode_name']}**](https://memory-alpha.fandom.com/wiki/{ep['memoryalpha']})"
            )
        self.add_item(worst_container)


class Leaderboard(commands.Cog):
    """
    A set of commands to find the best episodes ever!
    
    While the actual values are determined by the cron job in tasks/arena.py, this will actually show them to the user.
    """
    badge_group = discord.SlashCommandGroup("leaderboard", "Check the arena leaderboard!")
    # Discord options used by multiple commands
    public_option = discord.option(
        name="public",
        input_type=str,
        description="Show to the public?",
        required=True,
        choices=[
            discord.OptionChoice("No", 'no'),
            discord.OptionChoice("Yes", 'yes')
        ]
    )
    show_option = discord.option(
        name="show",
        input_type=str,
        description="Limit to this show",
        required=True,
        choices=[
            discord.OptionChoice(info['name'], key)
            for key, info in show_data.items()
            if info['enabled'] and info['trek']
               and key != 'snw'  # As SNW ans SFA are added to the DB, comment these lines out
               and key != 'sfa'
        ]
    )
    
    season_and_episode = re.compile(r"s\s*(\d+)\s*e\s*(\d+)", re.IGNORECASE)
    
    
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot
        # I'm caching here because we don't expect the info we care about to change.  That is, we aren't including the
        # podcast details.
        self.show_data_cache:dict[str, dict] = {}
        
        
    def get_episode_info(self, ep:db.Episode) -> dict:
        """
        Given an episode from the DB, get the details about it.
        """
        show_name = ep['show_name']
        if show_name not in self.show_data_cache:
            with open(show_data[show_name]['source']) as f:
                self.show_data_cache[show_name] = json.load(f)
        
        show_details = self.show_data_cache[show_name]
        episode_details = show_details['episodes'][ep['number']]
        
        return {
            'show_name': show_details['title'].replace("Star Trek: ", ""),
            'episode_name': episode_details['title'],
            'season': episode_details['season'],
            'episode_number': episode_details['episode'],
            'memoryalpha': episode_details['memoryalpha'],
            'rank_points': ep['rank_points'],
            'description': episode_details['description'] if len(episode_details['description']) <= 250
                                                          else f"{episode_details['description'][:249]}…",
            "image": random.choice(episode_details['stills']) if episode_details['stills'] else None,
        }
        
        
    @badge_group.command(description="Show the overall leader across all of Trek")
    @public_option
    @commands.check(access_check)
    async def overall(self, ctx: discord.ApplicationContext, public: str):
        logger.info(f"{ctx.author.name} is asking for the {Style.BRIGHT}overall leaderboard{Style.RESET_ALL}")
        
        episode_count, min_runs, max_runs = await db.get_stats()
        winners = [
            self.get_episode_info(episode)
            for episode in await db.get_rated_episodes(10, top=True)
        ]
        losers = [
            self.get_episode_info(episode)
            for episode in await db.get_rated_episodes(5, top=False)
        ]
    
        view = ResultsView(episode_count, min_runs, max_runs)
        view.add_winners(winners)
        view.add_losers(losers)

        
        await ctx.respond(view=view, ephemeral=False)
        
    
    @badge_group.command(description="Show the leaders for a specific show")
    @public_option
    @show_option
    @commands.check(access_check)
    async def show(self, ctx: discord.ApplicationContext, public:str, show:str):
        logger.info(f"{ctx.author.name} is looking for the {Style.BRIGHT}leaderboards for {show}{Style.RESET_ALL}")
        
        episode_count, min_runs, max_runs = await db.get_stats(show)
        if not episode_count:
            return await self.invalid_show(ctx, show)
        
        winners = [
            self.get_episode_info(ep)
            for ep in await db.get_rated_episodes(7, top=True, show=show)
        ]
        losers = [
            self.get_episode_info(ep)
            for ep in await db.get_rated_episodes(3, top=False, show=show)
        ]
        show_name = show_data[show]['name']
        
        view = ResultsView(episode_count, min_runs, max_runs, show_name)
        view.add_winners(winners)
        view.add_losers(losers)
        
        await ctx.respond(view=view, ephemeral=(public=='no'))
        
        
    @badge_group.command(description="See where this episode lands in the arena")
    @public_option
    @show_option
    @discord.option(
        name="episode_title",
        description="Episode Title (Search) or Number (S##E##)",
        required=True,
        autocomplete=title_autocomplete
    )
    @commands.check(access_check)
    async def episode(self, ctx: discord.ApplicationContext, public: str, show: str, episode_title: str):
        episode_title = episode_title.strip()
        season_episode_match = self.season_and_episode.match(episode_title)
        
        if show not in show_data:
            return await self.invalid_show(ctx, show)
        
        if show not in self.show_data_cache:
            with open(show_data[show]['source']) as f:
                self.show_data_cache[show] = json.load(f)
        
        episode_index = None
        if season_episode_match:
            season_number = season_episode_match[1]
            if len(season_number) == 1:
                season_number = f"0{season_number}"
            episode_number = season_episode_match[2]
            if len(episode_number) == 1:
                episode_number = f"0{episode_number}"
            for index, episode_information in enumerate(self.show_data_cache[show]['episodes']):
                if episode_information['season'] == season_number and episode_information['episode'] == episode_number:
                    episode_index = index
                    break
        else:
            for index, episode_information in enumerate(self.show_data_cache[show]['episodes']):
                if episode_information['title'] == episode_title:
                    episode_index = index
                    break
        
        if episode_index is None:
            return await ctx.respond(embed=discord.Embed(
                color=discord.Colour.red(),
                title="Invalid episode!",
                description=f"Unable to find episode named {episode_title}. If this should be, then bring it up with "
                            f"Agimus admins."
            ),
            ephemeral=True)
        
        episode = await db.get_episode_by_index(show, episode_index)
        if not episode:
            return await self.invalid_show(ctx, show)
        
        total_count, total_place, show_count, show_place = await db.get_episode_ranking(episode['id'])
        if not total_count:
            return await self.invalid_show(ctx, show)
        nearby_episodes = [self.get_episode_info(ep) for ep in await db.get_near_episodes(episode)]
        
        embed = discord.Embed(
            color=discord.Colour.random(),
            title=f"How well is {self.show_data_cache[show]['title']} "
                  f"S{episode_information['season']}E{episode_information['episode']} - "
                  f"{episode_information['title']} doing in the great episode battle?",
            thumbnail=random.choice(episode_information['stills']),
            description=f"It has gone up against {episode['number_of_matches']} other episodes."
        )
        embed.add_field(name="All shows", value=f"{total_place}/{total_count}", inline=True)
        embed.add_field(name=self.show_data_cache[show]['title'], value=f"{show_place}/{show_count}", inline=True)
        embed.add_field(name="Episodes in a similar place", value="\n".join(
            f"{ep['show_name']} S{ep['season']}E{ep['episode_number']}: **{ep['episode_name']}**"
            for ep in nearby_episodes
        ), inline=False)
        
        await ctx.respond(embed=embed, ephemeral=(public=='no'))
        
            
    async def invalid_show(self, ctx: discord.ApplicationContext, show: str):
        """
        If the show is invalid, then say so up front.
        """
        await ctx.respond(embed=discord.Embed(
            color=discord.Colour.red(),
            title="Invalid show!",
            description=f"I don't see any {show} episodes in the arena, so there’s no leaders!"
        ),
        ephemeral=True)

    