import os
import time # We will assume we are connect to wifi at all times for now 
import logging
from gpiozero import Button
from signal import pause
from picamera2 import Picamera2 


# Config Inits
BUTTON_PIN  = 17
COOLDOWN_SEC = 3
SETTLE_TIME = 2.0
EXPOSURE_COMP = 1.0
ANALOGUE_GAIN = 2.0 
CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "captures") 
LOG_FILE    = os.path.join(os.path.dirname(__file__), "..", "camera.log") # its probably a good idea to keep a log just incase


# Logging all Actions 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# Setup
#
picam2 = Picamera2()
os.makedirs(CAPTURE_DIR, exist_ok=True)
button = Button(BUTTON_PIN)
picam2.configure(picam2.create_still_configuration()) # Init the camera with no preview screen

last_capture_time = 0  # Tracks the last capture timestamp

def generate_filename() -> str:
    """Generate a timestamped filename for each capture."""
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S") # Year-Month-Day-Hour-Min-Sec
    return os.path.join(CAPTURE_DIR, f"capture_{timestamp}.jpg")

            
def capture_photo() -> str | None:
    """Capture a photo, save it locally, and return the file path."""

    global last_capture_time
    
    elapsed = time.time() - last_capture_time
    if elapsed < COOLDOWN_SEC:
        remaining = round(COOLDOWN_SEC - elapsed, 1)
        log.warning(f"Cooldown active — please wait {remaining}s")
        return None


    filepath = generate_filename()
    try:
        log.info("Button Pressed - Now Capturing Photo")
        picam2.start()

        # auto exposure code
        picam2.set_controls({
            "ExposureValue": EXPOSURE_COMP,  # Positive value means brighter 
            "AnalogueGain":  ANALOGUE_GAIN,  # Increase the sensor sensitivity (allow for more light to get in kind of like iso)
            })

        log.info(f"Waiting {SETTLE_TIME}s for exposure to settle")
        time.sleep(SETTLE_TIME)

        
        picam2.capture_file(filepath)
        picam2.stop()
        last_capture_time = time.time()  # Update only on success
        log.info(f"Photo Saved: {filepath}")
        return filepath
    
    # Just incase camera ideas mid press or some
    except Exception as e:
        log.error(f"Capture Failed: {e}")
        picam2.stop()
        return None

def on_button_pressed():
    capture_photo()
    


button.when_pressed = on_button_pressed


print("Listening")
pause()
