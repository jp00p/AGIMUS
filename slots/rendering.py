import time
import imageio
from common import *
from copy import deepcopy
from PIL import Image, ImageFilter
from typing import List


def preload_symbols():
    """preloads all slot symbol graphics into memory"""
    symbols_directory = "images/slots_2.0/symbols/bmp"
    logger.info("Loading symbol graphics...")
    temp_symbols = {}
    for filename in os.listdir(symbols_directory):
        if filename.endswith(".bmp"):
            img = np.array(
                Image.open(os.path.join(symbols_directory, filename)).convert("RGB")
            )
            temp_symbols[filename.lower().replace(".bmp", "")] = img
    logger.info(f"Loaded {len(temp_symbols)} symbol graphics!")
    return temp_symbols


SYMBOLS = preload_symbols()  # all symbol graphics
SPINS = [
    Image.open("images/slots_2.0/spin_1.png"),
    Image.open("images/slots_2.0/spin_2.png"),
    Image.open("images/slots_2.0/spin_3.png"),
]  # static spin graphics
PAYOUT_FONT = ImageFont.truetype("fonts/lcars.ttf", 60)  # font for payout text
SCORES_FONT = ImageFont.truetype("fonts/lcars.ttf", 40)  # font for leaderboards
USES_FONT = ImageFont.truetype("fonts/lcars.ttf", 30)  # font for uses text


def add_text(bordered_image, cell_text, font=PAYOUT_FONT, color="white", xy=(8, 50)):
    """add some text to a grid cell"""
    bordered_image = Image.fromarray(bordered_image)
    draw = ImageDraw.Draw(bordered_image)
    draw.text(
        xy,
        str(cell_text),
        font=font,
        fill=color,
        stroke_fill="black",
        stroke_width=2,
    )
    return np.array(bordered_image)


@to_thread
def numpy_grid(
    symbol_data,
    grid_size=(5, 5),
    image_border=8,
    gutter=8,
    margin=8,
    background=(33, 33, 33),
    cell_border=4,
    border_color=(24, 24, 0),
):
    """
    this takes a list of symbol data and spits out a PIL Image of a grid
    its so fast :O
    """
    start_time = time.time()
    images = [SYMBOLS[symbol[0].lower().replace(" ", "_")] for symbol in symbol_data]
    payouts = [symbol[1] for symbol in symbol_data]
    status_colors = [symbol[2] for symbol in symbol_data]
    wiggly = [symbol[3] for symbol in symbol_data]
    uses = [symbol[4] for symbol in symbol_data]

    # calculate the size of each grid cell
    cell_width = (images[0].shape[1] + gutter) * grid_size[1] - gutter
    cell_height = (images[0].shape[0] + gutter) * grid_size[0] - gutter

    # calculate the size of the final image
    width = cell_width + image_border * 2 + margin * 2
    height = cell_height + image_border * 2 + margin * 2

    # create the final image as a 3D numpy array - i'll be pasting into this
    image = np.ones((height, width, 3), dtype=np.uint8) * np.array(
        background, dtype=np.uint8
    )

    # draw the images onto the grid this is so easy to reeeead
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            index = i * grid_size[1] + j
            if index >= len(images):
                break

            # drawing grid cells
            # top left
            x0 = j * (images[0].shape[1] + gutter) + image_border + margin - cell_border
            # bottom left
            y0 = i * (images[0].shape[0] + gutter) + image_border + margin - cell_border
            # top right
            x1 = x0 + images[index].shape[1]
            # bottom right
            y1 = y0 + images[index].shape[0]

            # if the symbol did something, it will have wiggly=True
            if wiggly[index]:
                # jiggle it a lil!
                mod1 = random.randint(-2, 2)
                mod2 = random.randint(-2, 2)
                x0 += mod1
                y0 += mod2
                x1 += mod1
                y1 += mod2

            # status can affect the border of the grid cell
            border_color = status_colors[index]

            # "draw" border on the grid cell (actually extending the array with 1s)
            # numpy so mathy
            bordered_image = np.ones(
                (y1 - y0 + cell_border * 2, x1 - x0 + cell_border * 2, 3),
                dtype=np.uint8,
            ) * np.array(border_color, dtype=np.uint8)
            bordered_image[cell_border:-cell_border, cell_border:-cell_border] = images[
                index
            ]

            # add text to the grid cell
            # switch to PIL for this cuz numpy is too much for my brain
            # doesn't seem to slow it down too much
            if payouts[index] != 0:
                bordered_image = add_text(bordered_image, payouts[index])
            if uses[index] != 0:
                bordered_image = add_text(
                    bordered_image,
                    uses[index],
                    font=USES_FONT,
                    color="orange",
                    xy=(88, 8),
                )

            # combine everything back together in the image array
            image[y0 : y1 + cell_border * 2, x0 : x1 + cell_border * 2] = bordered_image

    end_time = time.time()
    total = end_time - start_time
    logger.info(f"{grid_size} grid Took {total}s")
    # convert the array back to a PIL image
    return Image.fromarray(image)


def generate_leaderboards(results):
    """build the daily leaderboards graphic"""
    board_bg = Image.new("RGB", (800, 800), "black")
    # add name, avatar, score, flourish
    x = 0
    y = 0
    cell_height = 132
    # also need to add the user name and score and stuff
    for res in results:
        id = res["user_discord_id"]
        user = get_user(id)
        score = res["total_winnings"]
        spins = res["spins"]
        username = user["name"]
        column_data = [score, username, spins]
        draw = ImageDraw.Draw(board_bg)
        for cd in column_data:
            draw.text((x, y + 15), f"{cd:<02}", font=SCORES_FONT, fill="white")
            x += 80
        img = Image.open(f"images/slots_2.0/draft_{id}.png").convert("RGB")
        board_bg.paste(img, (x, y))
        y += cell_height
        x = 0
    board_bg.save("images/slots_2.0/daily_leaderboards.png")


async def generate_transition_gif(
    images_1: list, images_2: list, output_file="results.gif", intermediate: list = None
) -> None:
    """generates the final 'spin' graphic for the game"""
    start_time = time.time()

    grid_image_1 = await numpy_grid(images_1)
    grid_image_2 = await numpy_grid(images_2)

    # create a list of frames for the GIF
    frames = [grid_image_1, grid_image_2]

    if intermediate:
        # wiggly frames
        for i in range(10):
            new_frame = await numpy_grid(intermediate)
            frames.insert(1, new_frame)

    # save the frames as a GIF file
    duration = [100, 100]
    if intermediate:
        duration = [500, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 8000]

    frames[0].save(
        output_file,
        format="GIF",
        append_images=frames[1:],
        save_all=True,
        compression=0,
        optimize=True,
        loop=0,
        duration=duration,
    )

    end_time = time.time()
    total = end_time - start_time
    logger.info(f"GIF Took {total}s")
