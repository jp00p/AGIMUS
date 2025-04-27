import tempfile
import subprocess
import io
import os
import time

from concurrent.futures import ThreadPoolExecutor

from common import *

THREAD_POOL = ThreadPoolExecutor(max_workers=24)

async def encode_webp(frames: list[Image.Image], fps: int = 12, resize: bool = True) -> io.BytesIO:
  """
  Encodes a list of RGBA frames into an animated WebP.

  Args:
    frames: List of PIL Image frames (RGBA).
    fps: Frames per second for animation.
    resize: Whether to resize frames to half size.

  Returns:
    io.BytesIO: In-memory WebP animation.
  """
  if not frames:
    raise ValueError("No frames provided for WebP encoding.")

  loop = asyncio.get_running_loop()

  # ---- Resizing Stage ----
  if resize:
    start_resize = time.perf_counter()

    def resize_frame(img: Image.Image) -> Image.Image:
      w, h = img.size
      return img.resize((int(w * 0.5), int(h * 0.5)), resample=Image.LANCZOS)

    resize_tasks = [loop.run_in_executor(THREAD_POOL, resize_frame, frame) for frame in frames]
    frames = await asyncio.gather(*resize_tasks)

    end_resize = time.perf_counter()
    logger.info(f"[timing] frame resizing took {end_resize - start_resize:.2f}s")

  width, height = frames[0].size
  frame_count = len(frames)

  # ---- Encoding Stage ----
  logger.info(f"[timing] Starting WebP encoding with {frame_count} frames at {fps}fps")
  start_encode = time.perf_counter()

  # Prepare raw RGBA frame data
  raw_rgb = b''.join(frame.convert("RGBA").tobytes() for frame in frames)

  with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as temp_outfile:
    output_path = temp_outfile.name

  try:
    command = [
      "ffmpeg",
      "-y",  # Overwrite output
      "-f", "rawvideo",
      "-pix_fmt", "rgba",
      "-s", f"{width}x{height}",
      "-r", str(fps),
      "-i", "pipe:0",
      "-c:v", "libwebp",
      "-lossless", "1",
      "-compression_level", "6",
      "-quality", "90",  # Good balance: faster and smaller
      "-loop", "0",
      "-preset", "picture",
      "-frames:v", str(frame_count),
      "-an",
      "-vsync", "0",
      output_path
    ]

    proc = await asyncio.create_subprocess_exec(
      *command,
      stdin=asyncio.subprocess.PIPE,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate(input=raw_rgb)

    if proc.returncode != 0:
      logger.error(f"[encode_webp] ffmpeg error: {stderr.decode()}")
      raise RuntimeError(f"FFmpeg WebP encoding failed:\n{stderr.decode()}")

    with open(output_path, "rb") as f:
      webp_data = f.read()

    end_encode = time.perf_counter()
    logger.info(f"[timing] webp encoding took {end_encode - start_encode:.2f}s")

    return io.BytesIO(webp_data)

  finally:
    if os.path.exists(output_path):
      os.remove(output_path)
