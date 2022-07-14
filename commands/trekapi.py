from .common import *
import stapi


# trekapi() - Entrypoint for !trekapi command
# message[required]: discord.Message
# This function is the main entrypoint of the !trekapi command
async def trekapi(message:discord.Message):
  logger.info("!trekapi")
  # criteria = stapi.search_criteria.AnimalSearchCriteria(0, 50, "", avian=True)
  # response = stapi.RestClient().animal.search(criteria)
  # criteria = stapi.search_criteria.TradingCardSearchCriteria(0, 1, "data")
  # response = stapi.RestClient().tradingCard.search(criteria)
  # logger.info(response["tradingCards"][0])
  # await message.channel.send(response["tradingCards"][0])
  # RestClient Args:
  # rest_client = stapi.RestClient()
  # rest_client.DEFAULT_API_KEYrest_client.DEFAULT_URL
  # rest_client.animal
  # rest_client.apiKey
  # rest_client.astronomicalObject
  # rest_client.book
  # rest_client.bookCollection
  # rest_client.bookSeries
  # rest_client.character
  # rest_client.comicCollection
  # rest_client.comicSeries
  # rest_client.comicStrip
  # rest_client.comics
  # rest_client.company
  # rest_client.conflict
  # rest_client.element
  # rest_client.episode
  # rest_client.food
  # rest_client.literature
  # rest_client.location
  # rest_client.magazine
  # rest_client.magazineSeries
  # rest_client.material
  # rest_client.medicalCondition
  # rest_client.movie
  # rest_client.occupation
  # rest_client.organization
  # rest_client.performer
  # rest_client.season
  # rest_client.series
  # rest_client.soundtrack
  # rest_client.spacecraft
  # rest_client.spacecraftClass
  # rest_client.species
  # rest_client.staff
  # rest_client.technology
  # rest_client.title
  # rest_client.tradingCard
  # rest_client.tradingCardDeck
  # rest_client.tradingCardSet
  # rest_client.url
  # rest_client.videoGame
  # rest_client.videoRelease
  # rest_client.weapon
  # Search Criteria
  # stapi.search_criteria.AnimalSearchCriteria(
  # stapi.search_criteria.AstronomicalObjectSearchCriteria(
  # stapi.search_criteria.BookCollectionSearchCriteria(
  # stapi.search_criteria.BookSearchCriteria(
  # stapi.search_criteria.BookSeriesSearchCriteria(
  # stapi.search_criteria.CharacterSearchCriteria(
  # stapi.search_criteria.ComicCollectionSearchCriteria(
  # stapi.search_criteria.ComicSeriesSearchCriteria(
  # stapi.search_criteria.ComicStripSearchCriteria(
  # stapi.search_criteria.ComicsSearchCriteria(
  # stapi.search_criteria.CommonSearchCriteria(
  # stapi.search_criteria.CompanySearchCriteria(
  # stapi.search_criteria.ConflictSearchCriteria(
  # stapi.search_criteria.ElementSearchCriteria(
  # stapi.search_criteria.EpisodeSearchCriteria(
  # stapi.search_criteria.FoodSearchCriteria(
  # stapi.search_criteria.LiteratureSearchCriteria(
  # stapi.search_criteria.LocationSearchCriteria(
  # stapi.search_criteria.MagazineSearchCriteria(
  # stapi.search_criteria.MagazineSeriesSearchCriteria(
  # stapi.search_criteria.MaterialSearchCriteria(
  # stapi.search_criteria.MedicalConditionSearchCriteria(
  # stapi.search_criteria.MovieSearchCriteria(
  # stapi.search_criteria.OccupationSearchCriteria(
  # stapi.search_criteria.OrganizationSearchCriteria(
  # stapi.search_criteria.PerformerSearchCriteria(
  # stapi.search_criteria.SeasonSearchCriteria(
  # stapi.search_criteria.SeriesSearchCriteria(
  # stapi.search_criteria.SoundtrackSearchCriteria(
  # stapi.search_criteria.SpacecraftClassSearchCriteria(
  # stapi.search_criteria.SpacecraftSearchCriteria(
  # stapi.search_criteria.SpeciesSearchCriteria(
  # stapi.search_criteria.StaffSearchCriteria(
  # stapi.search_criteria.TechnologySearchCriteria(
  # stapi.search_criteria.TitleSearchCriteria(
  # stapi.search_criteria.TradingCardDeckSearchCriteria(
  # stapi.search_criteria.TradingCardSearchCriteria(
  # stapi.search_criteria.TradingCardSetSearchCriteria(
  # stapi.search_criteria.VideoGameSearchCriteria(
  # stapi.search_criteria.VideoReleaseSearchCriteria(
  # stapi.search_criteria.WeaponSearchCriteria(
criteria = stapi.search_criteria.CharacterSearchCriteria(0, 1, "", name="%Picard")
response = stapi.RestClient().character.search(criteria)
print(response)
logger.info(response)
  # await message.channel.send(response["tradingCards"][0])
  # logger.info(response)

