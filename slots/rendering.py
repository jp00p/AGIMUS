import time
import imageio
from common import *
from wand.image import Image as WandImage
from copy import deepcopy
from PIL import Image, ImageOps
from typing import List

PAYOUT_FONT = ImageFont.truetype("fonts/lcars3.ttf", 55)
symbols_directory = "images/slots_2.0/symbols"


def preload_symbols():
    logger.info("Loading symbol graphics...")
    temp_symbols = {}
    for filename in os.listdir(symbols_directory):
        if filename.endswith(".png"):
            img = np.array(
                Image.open(os.path.join(symbols_directory, filename))
                .resize((96, 96))
                .convert("RGB")
            )
            temp_symbols[filename.lower().replace(".png", "")] = img
    logger.info(f"Loaded {len(temp_symbols)} symbol graphics!")
    return temp_symbols


SYMBOLS = preload_symbols()
font = ImageFont.truetype("fonts/lcars.ttf", 60)


def numpy_grid(
    symbol_data,
    grid_size=(5, 5),
    border=8,
    gutter=8,
    margin=8,
    background=(0, 0, 0),
    border_width=2,
    border_color=(0, 0, 0),
):
    images = [SYMBOLS[symbol[0].lower().replace(" ", "_")] for symbol in symbol_data]
    payouts = [symbol[1] for symbol in symbol_data]
    status_colors = [symbol[2] for symbol in symbol_data]

    # Calculate the size of each grid cell
    cell_width = (images[0].shape[1] + gutter) * grid_size[1] - gutter
    cell_height = (images[0].shape[0] + gutter) * grid_size[0] - gutter

    # Calculate the size of the final image
    width = cell_width + border * 2 + margin * 2
    height = cell_height + border * 2 + margin * 2

    # Create the final image as a NumPy array
    image = np.ones((height, width, 3), dtype=np.uint8) * np.array(
        background, dtype=np.uint8
    )

    # Draw the images onto the grid
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            index = i * grid_size[1] + j
            if index >= len(images):
                break
            x0 = j * (images[0].shape[1] + gutter) + border + margin
            y0 = i * (images[0].shape[0] + gutter) + border + margin
            x1 = x0 + images[index].shape[1]
            y1 = y0 + images[index].shape[0]

            border_color = status_colors[index]

            # Add a border to the individual image
            bordered_image = np.ones(
                (y1 - y0 + border_width * 2, x1 - x0 + border_width * 2, 3),
                dtype=np.uint8,
            ) * np.array(border_color, dtype=np.uint8)
            bordered_image[
                border_width:-border_width, border_width:-border_width
            ] = images[index]

            if symbol_data[index][1] != 0:
                bordered_image = Image.fromarray(bordered_image)
                draw = ImageDraw.Draw(bordered_image)
                draw.text((8, 50), str(payouts[index]), font=font, fill="white")
                bordered_image = np.array(bordered_image)

            image[
                y0 : y1 + border_width * 2, x0 : x1 + border_width * 2
            ] = bordered_image

    return Image.fromarray(image)


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
    if images_1 == images_2:
        logger.info("LUCKY!")
        grid_image = numpy_grid(images_1)
        grid_image.save(output_file, format="GIF", compression=0, optimize=True)
    else:
        grid_image_1 = numpy_grid(images_1)
        grid_image_2 = numpy_grid(images_2)
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
            compression=0,
            optimize=True,
            loop=0,
            duration=[2000, 100, 100, 50, 50, 20, 20, 20, 20, 50, 10000],
        )

    end_time = time.time()
    total = end_time - start_time
    logger.info(f"Took {total}s")
