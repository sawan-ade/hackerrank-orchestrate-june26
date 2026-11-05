import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Models are managed in utils.py for rotation
MAX_IMAGE_SIZE = 1024          # px, longest dimension
MAX_CONCURRENT_CLAIMS = 3      # semaphore value (conservative for free tier: 15 RPM)
MAX_RETRIES = 3
API_TIMEOUT = 90.0             # seconds per API call

# Base path to the dataset folder (relative to code/)
DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "dataset")
