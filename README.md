# 📷 Fuzer-Cam

> A handbuilt digital camera inspired by the **Yashica Yashicaflex** — powered by a Raspberry Pi 5, built from scratch, and paired with a web dashboard for editing and managing photos.

<p align="center">
  <img src="images/yashica_cam.JPG" width="400"/>
</p>

---

## What Is This?

Fuzer-Cam is a full end-to-end camera system built as a final project for Computation 3. The idea was simple: build something real. Not a simulation, not a toy — an actual camera you can hold, press a button on, and have photos appear on a website seconds later.

The inspiration came from the **Yashica Yashicaflex**, a vintage twin-lens reflex camera from the 1950s with a waist-level viewfinder — you look *down* into the top of the camera to compose your shot. That design challenge (hardware + software + physical build) is exactly what made this project interesting.

<p align="center">
  <img src="images/waist-level-camera-diagram.jpg" width="400"/>
</p>

---

## Features

- 📸 **Physical shutter button** — press to take a photo, cooldown prevents accidental double shots
- ☁️ **Automatic cloud upload** — photos go straight to MongoDB Atlas over WiFi
- 🖥️ **Web dashboard** — browse, edit, tag, and download photos from any browser
- 🎨 **Photo editor** — brightness, contrast, saturation sliders + filters (B&W, sepia, vivid, cool, warm)
- 🔄 **Rotation** — 90° left, 180°, 90° right
- 🏷️ **Tagging system** — add custom tags and filter your gallery by them
- 🔐 **Token-protected API** — all data transfers require authentication
- 🔁 **Offline resilience** — photos save locally if offline, sync when back on WiFi

---

## Hardware

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 | Main computer |
| Arducam UC-376 / OV5647 5MP Camera | Image capture |
| Push button (GPIO 17) | Physical shutter |
| 0.91" I2C OLED Display | Status display |
| PiSugar2 Plus Battery Module | Portable power |
| Custom 3D printed case | Enclosure |

### Maybe (stretch goals)
- AI camera module for object detection and auto-categorisation
- Waist-level viewfinder using a top-mounted screen if lens mirror doesn't work
- Open collaborative editing — anyone can edit photos and changes persist

---

## Architecture

```
┌─────────────────────────────────┐
│         Raspberry Pi 5          │
│                                 │
│  Button press (GPIO 17)         │
│         ↓                       │
│     camera.py                   │
│         ↓ saves .jpg            │
│      captures/                  │
│         ↓                       │
│     uploader.py ────────────────────────→ MongoDB Atlas ☁️
│                                 │                ↓
└─────────────────────────────────┘         Railway (Flask)
                                                    ↓
                                            Web Browser 🌐
```

---

## Project Structure

```
fuzer-cam/
├── src/
│   ├── camera.py           # Captures photos on button press
│   └── uploader.py         # Resizes and uploads photos to MongoDB
├── web/
│   ├── app.py              # Flask web app + REST API
│   ├── Procfile            # Railway start command
│   ├── requirements.txt    # Python dependencies
│   ├── nixpacks.toml       # Railway build config
│   ├── templates/
│   │   ├── base.html       # Shared layout
│   │   ├── index.html      # Photo gallery with pagination
│   │   └── photo.html      # Photo editor
│   └── tests/
│       └── test_api.py     # Unit tests
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI/CD
├── .env                    # Local secrets — never commit this
├── .gitignore
├── SPEC.md                 # Full system specification
└── README.md
```

---

## Setup & Deployment

### Prerequisites

- Raspberry Pi 5 running Raspberry Pi OS (64-bit, Bookworm or newer)
- Docker installed on the Pi
- Python 3.11+
- A MongoDB Atlas account (free M0 tier)
- A Railway account

---

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/fuzer-cam.git
cd fuzer-cam
```

### 2. Create a virtual environment

```bash
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r web/requirements.txt
```

The `--system-site-packages` flag is important — it lets the venv access `picamera2` and `libcamera` which are installed system-wide on Raspberry Pi OS.

### 3. Configure environment variables

```bash
cp .env.example .env
nano .env
```

```bash
# MongoDB
LOCAL_URI=mongodb://localhost:27017/
ATLAS_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB=camera_project
MONGO_COLLECTION=captures

# API
API_TOKEN=your-secret-token-here

# Flask
SECRET_KEY=your-flask-secret-key

# Camera
BUTTON_PIN=17
COOLDOWN_SEC=3
SETTLE_TIME=2.0
EXPOSURE_COMP=1.0
ANALOGUE_GAIN=2.0
SHARPNESS=2.0
CONTRAST=1.2
SATURATION=1.1
```

### 4. Start MongoDB with Docker

```bash
docker run --name mongo -p 27017:27017 -d \
  -v ~/fuzer-cam/mongo_data:/data/db \
  mongo

# Make it restart automatically on boot
docker update --restart unless-stopped mongo
```

### 5. Run the camera

```bash
cd src
python3 camera.py
```

Press the button — photos will save to `../captures/` and upload to MongoDB automatically.

### 6. Run the web app locally

```bash
cd web
python3 app.py
```

Visit `http://localhost:5000` or `http://<pi-ip>:5000` from any device on the same network.

---

### Deploying to Railway

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) and create a new project from your GitHub repo
3. Set all environment variables from your `.env` in the Railway **Variables** tab
4. Railway will auto-detect the `Procfile` and deploy

Your app will be live at a URL like:
```
https://fuzer-cam-production.up.railway.app
```

Every push to `main` triggers an automatic redeploy.

---

### Setting up MongoDB Atlas

1. Create a free M0 cluster at [mongodb.com/atlas](https://mongodb.com/atlas)
2. Go to **Security → Database Access** → Add a new user with read/write permissions
3. Go to **Security → Network Access** → Allow access from anywhere (`0.0.0.0/0`)
4. Click **Connect → Drivers → Python** and copy your connection string
5. Paste it into `ATLAS_URI` in your `.env` and Railway variables
6. Create an index so sorting is fast:

```bash
python3 -c "
from pymongo import MongoClient, DESCENDING
import os
from dotenv import load_dotenv
load_dotenv('.env')
col = MongoClient(os.getenv('ATLAS_URI'))['camera_project']['captures']
col.create_index([('captured_at', DESCENDING)])
print('Index created!')
"
```

---

## API

All endpoints except `/api/health` require the header:

```
X-API-Token: your-secret-token
```

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | None | Health check |
| GET | `/api/photos` | Token | List recent photos |
| POST | `/api/photos` | Token | Upload a new photo |
| DELETE | `/api/photos/<id>` | Token | Delete a photo |

### Example: Upload a photo

```bash
curl -X POST https://your-app.railway.app/api/photos \
  -H "X-API-Token: your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "capture_20260419_120944.jpg",
    "image_b64": "<base64 encoded JPEG>",
    "captured_at": "2026-04-19T12:09:44"
  }'
```

### Example: Health check

```bash
curl https://your-app.railway.app/api/health
# {"status": "ok", "service": "fuzer-cam"}
```

---

## Running Tests

```bash
cd web
pip install pytest
pytest tests/ -v
```

Tests cover:
- Health endpoint returns 200 with no token
- API rejects missing and wrong tokens with 401
- API accepts correct token
- Photo upload succeeds with valid payload
- Upload rejects missing fields with 400
- Duplicate upload returns 200 not 500
- Brightness edit produces valid image
- B&W filter produces valid image
- 90° rotation swaps image dimensions correctly
- 180° rotation preserves image dimensions

---

## CI/CD

GitHub Actions runs automatically on every push to `main`:

```
Push to main
    ↓
GitHub Actions
    ├── Install Python 3.12
    ├── Install dependencies
    ├── Run pytest
    └── Verify app imports
    ↓
Railway auto-redeploys if tests pass
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `No module named 'libcamera'` | venv can't see system packages | Recreate venv with `--system-site-packages` |
| `Failed to reserve DRM plane` | Camera trying to open display | Already fixed — `create_still_configuration()` used |
| `Connection refused 27017` | Docker not running | `docker start mongo` |
| Atlas timeout on gallery | Too many large documents | Ensure images are resized to 800x600 before upload |
| `name must be an instance of str` | Env vars are None | Check `.env` has `MONGO_DB` and `MONGO_COLLECTION` |
| Railway build fails | Railpack can't detect app | Check `nixpacks.toml` and `Procfile` exist in `web/` |
| Photos not appearing | Atlas index missing | Create index on `captured_at` (see setup above) |
| Camera too dark | Exposure settings | Adjust `ANALOGUE_GAIN` and `EXPOSURE_COMP` in `.env` |
| Cooldown warning | Button pressed too fast | Wait `COOLDOWN_SEC` seconds between shots |

---

## Data Flow

```
1. Button pressed
        ↓
2. camera.py captures photo at 2592x1944
        ↓
3. Saved to captures/ as JPEG
        ↓
4. uploader.py resizes to 800x600 (faster uploads)
        ↓
5. Encoded as base64
        ↓
6. POST to MongoDB Atlas with metadata
        ↓
7. Flask (Railway) reads from Atlas
        ↓
8. Displayed in web gallery
```

---

## Camera Settings Reference

| Setting | Default | Range | Effect |
|---------|---------|-------|--------|
| `BUTTON_PIN` | 17 | Any GPIO | Shutter button pin |
| `COOLDOWN_SEC` | 3 | 0–60 | Min seconds between shots |
| `SETTLE_TIME` | 2.0 | 0–5 | Exposure settle time (seconds) |
| `EXPOSURE_COMP` | 1.0 | -8 to 8 | Brighter/darker overall |
| `ANALOGUE_GAIN` | 2.0 | 1–8 | Sensor sensitivity (like ISO) |
| `SHARPNESS` | 2.0 | 0–16 | Edge sharpening |
| `CONTRAST` | 1.2 | 0–32 | Light/dark difference |
| `SATURATION` | 1.1 | 0–32 | Colour intensity |

---

## License

MIT — do whatever you want with it.

---

*Built for Computation 3 — inspired by cameras that make you slow down and think before you shoot.*
