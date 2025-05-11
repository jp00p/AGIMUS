import tempfile
import subprocess
import io
import os
import time

from common import *

async def encode_webp(frames: list[Image.Image], fps: int = 12) -> io.BytesIO:
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

  width, height = frames[0].size
  frame_count = len(frames)

  logger.info(f"[timing] Starting WebP encoding with {frame_count} frames at {fps}fps")
  start_encode = time.perf_counter()

  # Prepare raw RGBA frame data
  # Off-load raw RGBA concatenation to thread to avoid blocking
  loop = asyncio.get_running_loop()
  def _build_raw_rgb():
    return b''.join(f.convert("RGBA").tobytes() for f in frames)
  raw_rgb = await loop.run_in_executor(THREAD_POOL, _build_raw_rgb)

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
