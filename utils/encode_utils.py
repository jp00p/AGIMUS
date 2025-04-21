import tempfile

from common import *

from concurrent.futures import ThreadPoolExecutor

THREAD_POOL = ThreadPoolExecutor(max_workers=24)

async def encode_webp(frames: list[Image.Image], resize=True):
  loop = asyncio.get_running_loop()

  # TODO: Make native canvas sizes smaller so we don't have to do this reize step...
  # Resize final output frames concurrently while preserving order
  start = time.perf_counter()
  def resize_frame(img: Image.Image) -> Image.Image:
    if resize:
      logger.info(f"[timing] Starting Stage 4: frame resizing")

      w, h = img.size
      return img.resize((int(w * 0.5), int(h * 0.5)), resample=Image.LANCZOS)
    else:
      return img

  resize_tasks = [
    loop.run_in_executor(THREAD_POOL, resize_frame, frame)
    for frame in frames
  ]
  final_frames = await asyncio.gather(*resize_tasks)

  if resize:
    end = time.perf_counter()
    logger.info(f"[timing] frame resizing took {end - start:.2f}s")

  return await loop.run_in_executor(THREAD_POOL, _encode_webp, final_frames)

def _encode_webp(frames: list[Image.Image]):
  buf = _encode_webp_ffmpeg_pipe(frames)
  buf.seek(0)
  return buf

def _encode_webp_ffmpeg_pipe(frames: list[Image.Image], fps=12) -> io.BytesIO:
  if not frames:
    raise ValueError("No frames provided for WebP encoding.")

  logger.info(f"[timing] Starting Stage 5: webp encoding")
  start = time.perf_counter()

  width, height = frames[0].size
  pix_fmt = "rgba"
  frame_count = len(frames)

  # Convert all frames to raw RGB data
  raw_rgb = b''.join(frame.convert("RGBA").tobytes() for frame in frames)

  # Create a temporary file for FFmpeg output
  with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as temp_outfile:
    output_path = temp_outfile.name

  try:
    # FFmpeg command to encode raw RGB to animated WebP
    command = [
      "ffmpeg",
      "-y",  # Overwrite output
      "-f", "rawvideo",
      "-pix_fmt", pix_fmt,
      "-s", f"{width}x{height}",
      "-r", str(fps),
      "-i", "pipe:0",  # Input from stdin
      "-c:v", "libwebp",
      "-lossless", "1",
      "-preset", "picture",
      "-loop", "0",
      "-frames:v", str(frame_count),
      "-an",
      "-vsync", "0",
      output_path  # Output to real file
    ]

    # Run ffmpeg and feed raw RGB bytes
    process = subprocess.run(
      command,
      input=raw_rgb,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE
    )

    if process.returncode != 0:
      raise RuntimeError(f"FFmpeg failed:\n{process.stderr.decode()}")

    # Read the output .webp back into memory
    with open(output_path, "rb") as f:
      webp_data = f.read()

    end = time.perf_counter()
    logger.info(f"[timing] _encode_webp_ffmpeg_pipe took {end - start:.2f}s")

    return io.BytesIO(webp_data)

  finally:
    if os.path.exists(output_path):
      os.remove(output_path)

def paginate(data_list, items_per_page):
  for i in range(0, len(data_list), items_per_page):
    yield data_list[i:i + items_per_page], (i // items_per_page) + 1
