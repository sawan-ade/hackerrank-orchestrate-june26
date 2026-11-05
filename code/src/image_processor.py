"""
image_processor.py — PIL load, resize, and prepare for Gemini Vision.
CPU-blocking PIL work is offloaded to ThreadPoolExecutor.
"""
import asyncio
import concurrent.futures
import os
from PIL import Image

from config import MAX_IMAGE_SIZE


def _load_and_resize_sync(path: str, max_size: int = MAX_IMAGE_SIZE) -> Image.Image:
    """Synchronous PIL work — runs in thread executor, not event loop."""
    img = Image.open(path)

    # Handle non-RGB modes
    if img.mode in ("CMYK", "P", "RGBA", "LA", "I", "F"):
        img = img.convert("RGB")

    # Resize keeping aspect ratio
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    return img


async def load_image(path: str, max_size: int = MAX_IMAGE_SIZE) -> Image.Image:
    """
    Async wrapper: offloads blocking PIL work to ThreadPoolExecutor.
    Returns a PIL Image object ready for Gemini.
    """
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, _load_and_resize_sync, path, max_size)


def extract_image_id(path: str) -> str:
    """Extract image_id from path: filename without extension."""
    return os.path.splitext(os.path.basename(path))[0]
