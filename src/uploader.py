import os
import base64
import logging
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI        =  os.getenv("MONGO_URI")


# Atlas — cloud backup, only used when internet is available
ATLAS_URI        = os.getenv("ATLAS_URI")
MONGO_DB         =  os.getenv("MONGO_DB")
MONGO_COLLECTION =  os.getenv("MONGO_COLLECTION")
CAPTURES_DIR     = os.path.join(os.path.dirname(__file__), "..", "captures")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── MongoDB helpers ───────────────────────────────────────────────────────────
def get_local_collection():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB][MONGO_COLLECTION]

def get_atlas_collection():
    client = MongoClient(ATLAS_URI, serverSelectionTimeoutMS=5000)
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

def build_doc(filename: str, image_b64: str) -> dict:
    # Generate thumbnail
    img = Image.open(BytesIO(base64.b64decode(image_b64))).convert("RGB")
    img.thumbnail((400, 300))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=60)
    thumbnail_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "filename":       filename,
        "captured_at":    datetime.now().isoformat(),
        "uploaded_at":    datetime.now().isoformat(),
        "image_b64":      image_b64,
        "thumbnail_b64":  thumbnail_b64,
        "ai_description": "",
        "ai_tags":        [],
        "user_tags":      [],
        "notes":          ""
    }

# ── Single file upload ────────────────────────────────────────────────────────
def upload_file(filepath: str):
    """Upload one photo to local MongoDB then sync to Atlas."""
    filename  = os.path.basename(filepath)
    image_b64 = encode_image(filepath)
    if not image_b64:
        return

    doc = build_doc(filename, image_b64)

    # Always save to local first
    try:
        local = get_local_collection()
        if not already_uploaded(local, filename):
            local.insert_one(doc.copy())
            log.info(f"Saved to local MongoDB: {filename}")
        else:
            log.info(f"Already in local MongoDB: {filename}")
    except Exception as e:
        log.error(f"Local MongoDB failed: {e}")

    # Then try Atlas — if no internet this just logs a warning
    try:
        atlas = get_atlas_collection()
        if not already_uploaded(atlas, filename):
            atlas.insert_one(doc.copy())
            log.info(f"Synced to Atlas: {filename}")
        else:
            log.info(f"Already in Atlas: {filename}")
    except Exception as e:
        log.warning(f"Atlas sync failed (no internet?): {e}")

# ── Bulk upload ───────────────────────────────────────────────────────────────
def upload_all():
    """Upload all captures not yet in MongoDB."""
    files = [
        f for f in os.listdir(CAPTURES_DIR)
        if f.endswith(".jpg") or f.endswith(".jpeg")
    ]

    if not files:
        log.info("No captures found")
        return

    log.info(f"Found {len(files)} capture(s)...")
    for filename in sorted(files):
        upload_file(os.path.join(CAPTURES_DIR, filename))
    log.info("Done")

# ── Sync local → Atlas ────────────────────────────────────────────────────────
def sync_to_atlas():
    """
    Push everything in local MongoDB up to Atlas.
    Run this manually whenever you want to force a full sync.
    """
    try:
        local = get_local_collection()
        atlas = get_atlas_collection()

        all_local = list(local.find({}))
        log.info(f"Syncing {len(all_local)} photos to Atlas...")

        synced  = 0
        skipped = 0
        for doc in all_local:
            if already_uploaded(atlas, doc["filename"]):
                skipped += 1
                continue
            doc.pop("_id")  # Remove local _id so Atlas generates its own
            atlas.insert_one(doc)
            synced += 1
            log.info(f"Synced: {doc['filename']}")

        log.info(f"Sync complete — {synced} synced, {skipped} already there")
    except Exception as e:
        log.error(f"Atlas sync failed: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        sync_to_atlas()
    else:
        upload_all()
