import time
import math
from common import *
from PIL import Image, ImageSequence
from typing import List
from typing import List
from PIL import Image
from pygifsicle import optimize


PAYOUT_FONT = ImageFont.truetype("fonts/lcars3.ttf", 55)
symbols_directory = "images/slots_2.0/symbols"
# create an empty list to store the images
SYMBOLS = {}

logger.info("Loading slot symbols...")
for filename in os.listdir(symbols_directory):
    if filename.endswith(".png"):
        img = Image.open(os.path.join(symbols_directory, filename))
        SYMBOLS[filename.lower().replace(".png", "")] = img
logger.info("Slot symbols loaded.")


def generate_grid_image(
    symbol_data: list, num_cols: int, margin: int, gutter: int, bg_color: tuple
) -> Image:
    # Load the first image to get the dimensions
    first_image = SYMBOLS[symbol_data[0][0]].copy()
    image_width, image_height = first_image.size

    # Calculate the size of each image tile
    tile_width = (image_width + gutter) * num_cols - gutter
    num_rows = (len(symbol_data) - 1) // num_cols + 1
    tile_height = image_height + margin
    if num_rows > 1:
        tile_height += margin + (image_height + margin) * (num_rows - 1)

    # Create a new image with the calculated size and background color
    grid_image = Image.new("RGB", (tile_width, tile_height), bg_color)

    # Load and resize the images to match the first image's dimensions
    images = [SYMBOLS[name[0]].copy() for name in symbol_data]

    # Paste the images onto the grid
    x_offset = margin
    y_offset = margin
    i = 0
    for image in images:
        # logger.info(f"Drawing {symbol_data[i][0]} with payout of {symbol_data[i][1]}")
        if symbol_data[i][0] != "empty":
            draw = ImageDraw.Draw(image)
            draw.text(
                (image_width // 2, image_height // 2),
                text=str(symbol_data[i][1]),
                fill="white",
                font=PAYOUT_FONT,
                align="center",
                stroke_width=2,
                stroke_fill="black",
            )
        i += 1
        grid_image.paste(image, (x_offset, y_offset))
        x_offset += image_width + gutter
        if x_offset >= tile_width:
            x_offset = margin
            y_offset += image_height + margin
    return grid_image


def generate_transition_gif(
    images_1: list,
    images_2: list,
    num_cols: int = 5,
    margin: int = 5,
    gutter: int = 5,
    bg_color: tuple = (0, 0, 0),
    duration: int = 100,
    output_file="results.gif",
) -> None:
    start_time = time.time()
    # Generate the grid images for the two sets of images
    logger.info(f"WHAT THE DEVIL\n\n{images_1}\n{images_2}")
    grid_image_1 = generate_grid_image(images_1, num_cols, margin, gutter, bg_color)
    grid_image_2 = generate_grid_image(images_2, num_cols, margin, gutter, bg_color)

    # grid_image_1.save("images/slots_2.0/grid1.png")
    # grid_image_2.save("images/slots_2.0/grid2.png")
    # Create a list of frames for the GIF
    frames = []
    for i in range(11):
        alpha = i / 10.0
        frame = Image.blend(grid_image_1, grid_image_2, alpha)
        frames.append(frame)

    # Save the frames as a GIF file
    frames[0].save(
        output_file,
        format="GIF",
        append_images=frames[1:],
        save_all=True,
        duration=[2000, 100, 100, 50, 50, 20, 20, 20, 20, 50, 50, 100, 1000],
    )
    end_time = time.time()
    total = end_time - start_time
    logger.info(f"Took {total}s")
    # optimize(output_file)
    # gifsicle(
    #     sources=frames,
    #     destination=output_file,  # or just omit it and will use the first source provided.
    #     optimize=3,  # Whetever to add the optimize flag of not
    #     colors=128,  # Number of colors t use
    #     options=["--delay", 1000],  # Options to use.
    # )
