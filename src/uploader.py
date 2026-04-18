import os
import base64
import logging
from datetime import datetime
from pymongo import MongoClient

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI        = "mongodb://localhost:27017/"
MONGO_DB         = "camera_project"
MONGO_COLLECTION = "captures"
CAPTURES_DIR     = os.path.join(os.path.dirname(__file__), "..", "captures")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── MongoDB ───────────────────────────────────────────────────────────────────
def get_collection():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB][MONGO_COLLECTION]

# ── Helpers ───────────────────────────────────────────────────────────────────
def encode_image(filepath: str) -> str | None:
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log.error(f"Failed to encode {filepath}: {e}")
        return None

def already_uploaded(collection, filename: str) -> bool:
    return collection.find_one({"filename": filename}) is not None

# ── Upload everything in captures/ ───────────────────────────────────────────
def upload_all():
    collection = get_collection()
    files = [
        f for f in os.listdir(CAPTURES_DIR)
        if f.endswith(".jpg") or f.endswith(".jpeg")
    ]

    if not files:
        log.info("No captures found")
        return

    log.info(f"Found {len(files)} capture(s)...")
    uploaded = 0
    skipped  = 0

    for filename in sorted(files):
        if already_uploaded(collection, filename):
            log.info(f"Skipping (already uploaded): {filename}")
            skipped += 1
            continue

        filepath  = os.path.join(CAPTURES_DIR, filename)
        image_b64 = encode_image(filepath)
        if not image_b64:
            continue

        doc = {
            "filename":       filename,
            "captured_at":    datetime.now().isoformat(),
            "uploaded_at":    datetime.now().isoformat(),
            "image_b64":      image_b64,
            "ai_description": "",
            "ai_tags":        [],
            "user_tags":      [],
            "notes":          ""
        }
        collection.insert_one(doc)
        log.info(f"Uploaded: {filename}")
        uploaded += 1

    log.info(f"Done — {uploaded} uploaded, {skipped} skipped")
def upload_file(filepath: str):
    """Upload a single specific file to MongoDB. Called directly from camera.py."""
    collection = get_collection()
    filename = os.path.basename(filepath)

    if already_uploaded(collection, filename):
        log.info(f"Already uploaded: {filename}")
        return

    image_b64 = encode_image(filepath)
    if not image_b64:
        return

    doc = {
        "filename":       filename,
        "captured_at":    datetime.now().isoformat(),
        "uploaded_at":    datetime.now().isoformat(),
        "image_b64":      image_b64,
        "ai_description": "",
        "ai_tags":        [],
        "user_tags":      [],
        "notes":          ""
    }
    collection.insert_one(doc)
    log.info(f"Uploaded to MongoDB: {filename}")

if __name__ == "__main__":
    upload_all()