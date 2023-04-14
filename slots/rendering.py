import time
import imageio
from common import *
from copy import deepcopy
from PIL import Image, ImageFilter
from typing import List

PAYOUT_FONT = ImageFont.truetype("fonts/lcars3.ttf", 55)
symbols_directory = "images/slots_2.0/symbols/bmp"


def preload_symbols():
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


SYMBOLS = preload_symbols()
SPINS = [
    Image.open("images/slots_2.0/spin_1.png"),
    Image.open("images/slots_2.0/spin_2.png"),
    Image.open("images/slots_2.0/spin_3.png"),
]
font = ImageFont.truetype("fonts/lcars.ttf", 60)


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
    start_time = time.time()
    images = [SYMBOLS[symbol[0].lower().replace(" ", "_")] for symbol in symbol_data]
    payouts = [symbol[1] for symbol in symbol_data]
    status_colors = [symbol[2] for symbol in symbol_data]
    wiggly = [symbol[3] for symbol in symbol_data]

    # calculate the size of each grid cell
    cell_width = (images[0].shape[1] + gutter) * grid_size[1] - gutter
    cell_height = (images[0].shape[0] + gutter) * grid_size[0] - gutter

    # calculate the size of the final image
    width = cell_width + image_border * 2 + margin * 2
    height = cell_height + image_border * 2 + margin * 2

    # create the final image as a NumPy array
    image = np.ones((height, width, 3), dtype=np.uint8) * np.array(
        background, dtype=np.uint8
    )

    # draw the images onto the grid
    for i in range(grid_size[0]):
        for j in range(grid_size[1]):
            index = i * grid_size[1] + j
            if index >= len(images):
                break
            x0 = j * (images[0].shape[1] + gutter) + image_border + margin - cell_border
            y0 = i * (images[0].shape[0] + gutter) + image_border + margin - cell_border
            x1 = x0 + images[index].shape[1]
            y1 = y0 + images[index].shape[0]

            if wiggly[index]:
                mod1 = random.randint(-4, 4)
                mod2 = random.randint(-4, 4)
                x0 += mod1
                y0 += mod2
                x1 += mod1
                y1 += mod2

            border_color = status_colors[index]

            # add border to the grid cell
            bordered_image = np.ones(
                (y1 - y0 + cell_border * 2, x1 - x0 + cell_border * 2, 3),
                dtype=np.uint8,
            ) * np.array(border_color, dtype=np.uint8)
            bordered_image[cell_border:-cell_border, cell_border:-cell_border] = images[
                index
            ]

            # add text to the grid cell
            if symbol_data[index][1] != 0:
                bordered_image = Image.fromarray(bordered_image)
                draw = ImageDraw.Draw(bordered_image)
                draw.text(
                    (8, 50),
                    str(payouts[index]),
                    font=font,
                    fill="white",
                    stroke_fill="black",
                    stroke_width=2,
                )
                bordered_image = np.array(bordered_image)

            image[y0 : y1 + cell_border * 2, x0 : x1 + cell_border * 2] = bordered_image

    end_time = time.time()
    total = end_time - start_time
    logger.info(f"{grid_size} grid Took {total}s")
    return Image.fromarray(image)


async def generate_transition_gif(
    images_1: list, images_2: list, output_file="results.gif", intermediate: list = None
) -> None:
    start_time = time.time()
    # if images_1 == images_2:
    #     logger.info("LUCKY!")
    #     grid_image = await numpy_grid(images_2)
    #     grid_image.save(output_file, format="GIF", compression=0, optimize=True)
    # else:

    grid_image_1 = await numpy_grid(images_1)
    grid_image_2 = await numpy_grid(images_2)

    # create a list of frames for the GIF
    frames = [grid_image_1, grid_image_2]

    if intermediate:
        for i in range(10):
            new_frame = await numpy_grid(intermediate)
            frames.insert(1, new_frame)

    # frame_count = 5
    # for i in range(frame_count + 1):  # the final frame will be 100% of the alpha
    #     # generate the alpha frames
    #     alpha = i / float(frame_count)
    #     frame = Image.blend(grid_image_1, grid_image_2, alpha)
    #     frames.append(frame)

    # frames.insert(2, grid_blur_2)

    # save the frames as a GIF file
    duration = [100, 100]
    if intermediate:
        duration = [500, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 8000]

    logger.info(duration)
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
