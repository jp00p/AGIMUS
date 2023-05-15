from .slots_symbol import *

basic_symbols = [
    SlotsSymbol(
        name="Janeway",
        base_payout=1,
        tags=[
            "captain",
            "voyager",
            "female",
            "human",
            "federation",
            "red uniform",
        ],
    ),
    SlotsSymbol(
        name="Picard",
        base_payout=1,
        effect_where="adjacent",
        effect_which="combadge",
        effect_name="alter_payout",
        effect_args={"new_payout": 1, "permanent": False},
        description="Increases in value near combadges",
        tags=[
            "captain",
            "next generation",
            "male",
            "human",
            "federation",
            "red uniform",
        ],
    ),
    SlotsSymbol(
        name="Riker",
        base_payout=0,
        effect_where="adjacent",
        effect_which="tag",
        affect_self=True,
        effect_name="alter_payout",
        description="Pays 3 more when near any woman, human or otherwise.",
        effect_args={"new_payout": 3, "permanent": False},
        match_tags=["female"],
        tags=[
            "commander",
            "next generation",
            "male",
            "human",
            "federation",
            "red uniform",
        ],
    ),
    SlotsSymbol(
        name="Kirk",
        tags=["captain", "tos", "male", "human", "gold uniform", "federation"],
    ),
    SlotsSymbol(
        name="Coffee",
        uses=3,
        limited=True,
        description="Permanently increases Janeway's payout by 1 when adjacent",
        effect_which="janeway",
        effect_where="adjacent",
        effect_name="alter_payout",
        affect_self=False,
        effect_args={"new_payout": 1, "permanent": True},
        tags=["beverage"],
    ),
    SlotsSymbol(
        name="Burnham", tags=["human", "female", "discovery", "federation", "captain"]
    ),
    SlotsSymbol(name="Pike", tags=["human", "male", "captain", "federation"]),
    SlotsSymbol(
        name="Sisko",
        effect_where="adjacent",
        effect_which="baseball glove",
        effect_name="alter_payout",
        effect_args={"new_payout": 1},
        description="He loves baseball!",
    ),
    SlotsSymbol(
        name="Kevin",
        effect_where="adjacent",
        effect_which="any",
        effect_name="destroy",
        effect_args={"payout": 1},
        affect_self=False,
        description="Ice cream truck music can be heard in the distance",
        tags=["alien", "male", "villain", "next generation"],
    ),
    SlotsSymbol(name="Combadge", tags=["gear"]),
    SlotsSymbol(name="Fedora", tags=["clothes"]),
    SlotsSymbol(name="Pants", tags=["clothes"]),
    SlotsSymbol(name="Baseball Glove", tags=["gear", "baseball"]),
    SlotsSymbol(
        name="Yelgrun", tags=["alien", "voorta", "male", "villain", "dominion", "ds9"]
    ),
    SlotsSymbol(name="Mugato", tags=["alien", "male"]),
    SlotsSymbol(
        name="Niners Rom",
        effect_where="adjacent",
        effect_which="baseball glove",
        effect_name="alter_payout",
        effect_args={"new_payout": 1},
        tags=["ds9", "alien", "male", "ferengi", "baseball"],
    ),
    SlotsSymbol(name="Onezerozeroone", tags=["alien", "next generation"]),
    SlotsSymbol(name="Kurros", tags=["alien", "voyager"]),
    SlotsSymbol(
        name="Dominion Dukat", tags=["alien", "villain", "cardassian", "ds9", "male"]
    ),
    SlotsSymbol(
        name="Commando Shran",
        tags=[
            "alien",
            "male",
            "andorian",
            "jeffrey combs",
        ],
    ),
    SlotsSymbol(name="Badgey", tags=["photonic", "villain", "lower decks"]),
    SlotsSymbol(
        name="Armus",
        effect_where="adjacent",
        effect_which="any",
        effect_name="destroy",
        description="Destroys everything around it",
        tags=["villain", "next generation"],
    ),
    SlotsSymbol(
        name="Admiral Nechayev",
        tags=["female", "federation", "red uniform", "next generation"],
    ),
]

# keys unlock lockboxes
key_symbols = [
    SlotsSymbol(
        name="Basic key",
        tags=["key"],
        effect_where="adjacent",
        effect_which="basic lockbox",
        effect_args={"box": "basic lockbox"},
        effect_name="unlock",
        description="Opens a basic lockbox",
        limited=True,
        uses=1,  # unlock: give random item
    ),
]

basic_lockbox = SlotsSymbol(
    name="Basic lockbox",
    tags=["lockbox"],
    effect_args={"unlocks": [("rare_symbols", 50), ("borg_symbols", 10)]},
)

box_symbols = [
    SlotsSymbol(
        name="Basic lockbox",
        tags=["lockbox"],
        effect_args={"unlocks": [("rare_symbols", 50), ("borg_symbols", 10)]},
    )
]

borg_symbols = [
    BorgItemSymbol(name="Borg Nanoprobes"),
    BorgItemSymbol(name="Borg Exoplating"),
    BorgItemSymbol(name="Borg Cortical Node"),
    BorgItemSymbol(name="Borg Subdermal Probe"),
    BorgItemSymbol(name="Borg Interfacing Tentacles"),
    BorgItemSymbol(name="Borg Power Core"),
    BorgItemSymbol(
        name="Borg Occipital Implant",
    ),
]

basic_food_symbols = [
    BasicFoodSymbol(name="Tube Grubs", description="Yummy"),
    BasicFoodSymbol(name="Black Licorice", description="An Earth delicacy"),
    BasicFoodSymbol(name="Blood Pie", description="Full of blood"),
    BasicFoodSymbol(name="Blueberry Pie", description="A dunce's favorite"),
    BasicFoodSymbol(name="Bularian Canapes"),
    BasicFoodSymbol(name="Cheesecake"),
    BasicFoodSymbol(name="Chicken Soup"),
    BasicFoodSymbol(name="Chocolate Ice Cream"),
    BasicFoodSymbol(name="Cryogenic Food"),
    BasicFoodSymbol(name="Donuts"),
    BasicFoodSymbol(name="Feragoit Goulash"),
    BasicFoodSymbol(name="Gagh"),
    BasicFoodSymbol(name="Hot Chocolate"),
    BasicFoodSymbol(name="Ice Cream"),
    BasicFoodSymbol(name="Insect Larvae Meal"),
    BasicFoodSymbol(name="Joeseph Siskos Gumbo"),
    BasicFoodSymbol(name="Lemonade"),
    BasicFoodSymbol(name="Leola Root"),
    BasicFoodSymbol(name="Lunch Tray"),
    BasicFoodSymbol(name="Mushroom Soup"),
    BasicFoodSymbol(name="Pancakes"),
    BasicFoodSymbol(name="Pasta Dish"),
    BasicFoodSymbol(name="Potato"),
    BasicFoodSymbol(name="Romulan Soup"),
    BasicFoodSymbol(name="Thalian Chocolate Mousse"),
    BasicFoodSymbol(name="Tomato"),
]


rare_symbols = [
    SlotsSymbol(
        name="Replicator",
        tags=["technology"],
        effect_where="adjacent",
        effect_which="empty",
        effect_name="conversion",
        effect_args={"convert_to": "basic_food_symbols"},
        effect_chance=0.5,
        effect_self=False,
        uses=3,
        limited=True,
        description="Has a chance to create food in adjacent empty spaces",
    ),
]

basic_symbols += box_symbols + key_symbols

all_symbols = basic_symbols

# pulaski's purse = booze
# nasuicaan knife = kills picard
# darts = obrien + bashir
# neelix = ruins food except leola root

# effects = [
#     "conversion": {
#       "where":"",
#       "which":"",
#       "args":{},
#       "chance": 0.5,
#     }
# ]
