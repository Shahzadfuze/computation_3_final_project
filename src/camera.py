import os
import sys
import time
import logging
from gpiozero import Button
from signal import pause
from picamera2 import Picamera2

# So camera.py can find uploader.py in the same folder
sys.path.append(os.path.dirname(__file__))
from uploader import upload_file

# ── Config ────────────────────────────────────────────────────────────────────
SHARPNESS     = 2.0
CONTRAST      = 1.2
SATURATION    = 1.1
BUTTON_PIN    = 17
COOLDOWN_SEC  = 3
SETTLE_TIME   = 2.0
EXPOSURE_COMP = 1.0
ANALOGUE_GAIN = 2.0
CAPTURE_DIR   = os.path.join(os.path.dirname(__file__), "..", "captures")
LOG_FILE      = os.path.join(os.path.dirname(__file__), "..", "camera.log")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Setup ─────────────────────────────────────────────────────────────────────
os.makedirs(CAPTURE_DIR, exist_ok=True)

picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())

button = Button(BUTTON_PIN)

last_capture_time = 0

# ── Core ──────────────────────────────────────────────────────────────────────
def generate_filename() -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(CAPTURE_DIR, f"capture_{timestamp}.jpg")

def capture_photo() -> str | None:
    global last_capture_time

    elapsed = time.time() - last_capture_time
    if elapsed < COOLDOWN_SEC:
        remaining = round(COOLDOWN_SEC - elapsed, 1)
        log.warning(f"Cooldown active — please wait {remaining}s")
        return None

    filepath = generate_filename()
    try:
        log.info("Button pressed — capturing photo...")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        picam2.start()
        picam2.set_controls({
            "ExposureValue": EXPOSURE_COMP,
            "AnalogueGain":  ANALOGUE_GAIN,
            "Sharpness":     SHARPNESS,
            "Contrast":      CONTRAST,
            "Saturation":    SATURATION,
        })
        log.info(f"Waiting {SETTLE_TIME}s for exposure to settle...")
        time.sleep(SETTLE_TIME)
        picam2.capture_file(filepath)
        picam2.stop()
        last_capture_time = time.time()
        log.info(f"Photo saved: {filepath}")

        # ── Upload to MongoDB immediately ─────────────────────────────────────
        try:
            log.info("Uploading to MongoDB...")
            upload_file(filepath)
            log.info("Upload complete!")
        except Exception as e:
            log.warning(f"Upload failed — photo still saved locally: {e}")

        return filepath
    except Exception as e:
        log.error(f"Capture failed: {e}")
        picam2.stop()
        return None

# ── Button handler ────────────────────────────────────────────────────────────
def on_button_pressed():
    capture_photo()

button.when_pressed = on_button_pressed

# ── Run ───────────────────────────────────────────────────────────────────────
log.info(f"Camera ready — saving to: {CAPTURE_DIR}")
log.info("Listening for button press...")
pause()
