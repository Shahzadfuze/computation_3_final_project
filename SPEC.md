# Fuzer-Cam System Specification

## 1. Overview

Fuzer-Cam is a Raspberry Pi-based camera system that captures photos via a physical button press, stores them in MongoDB Atlas, and displays them on a Flask web dashboard hosted on Railway.

---

## 2. Use Cases

| ID  | Actor | Action | Outcome |
|-----|-------|--------|---------|
| UC1 | User  | Presses physical button | Photo is captured and uploaded to MongoDB |
| UC2 | User  | Visits web dashboard | Sees gallery of all photos, paginated |
| UC3 | User  | Clicks a photo | Views full photo with edit panel |
| UC4 | User  | Adjusts sliders and saves | Photo is edited and saved back to MongoDB |
| UC5 | User  | Adds tags to a photo | Tags are saved and can be filtered by |
| UC6 | User  | Filters by tag | Gallery shows only matching photos |
| UC7 | User  | Downloads a photo | Receives original JPEG file |
| UC8 | User  | Deletes a photo | Photo removed from MongoDB |
| UC9 | System | Pi loses internet | Photos saved locally, synced when back online |
| UC10 | Developer | Pushes to main branch | GitHub Actions runs tests automatically |

---

## 3. System Architecture
┌─────────────────────────────────────────┐
│           Raspberry Pi                  │
│                                         │
│  Button (GPIO 17)                       │
│      ↓                                  │
│  camera.py                              │
│      ↓ saves .jpg                       │
│  captures/                              │
│      ↓                                  │
│  uploader.py ──────────────────────────────→ MongoDB Atlas (cloud)
│                                         │
└─────────────────────────────────────────┘
↓
Railway (Flask app)
↓
Web Browser




--
## 4. Data Models

### Photo Document (MongoDB)

```json
{
"_id":                "ObjectId",
"filename":           "capture_20260419_120944.jpg",
"captured_at":        "2026-04-19T12:09:44.000000",
"uploaded_at":        "2026-04-19T12:09:46.000000",
"image_b64":          "base64 encoded JPEG string (800x600 max)",
"original_image_b64": "base64 encoded original before edits",
"ai_description":     "A desk with a laptop and coffee mug",
"ai_tags":            ["desk", "indoor", "laptop"],
"user_tags":          ["work", "morning"],
"notes":              "Taken during study session",
"last_edit": {
"brightness":  1.2,
"contrast":    1.0,
"saturation":  1.1,
"filter":      "warm",
"rotation":    90
}
}


## 5. Error Handling

| Scenario | Handling |
|----------|----------|
| Camera fails mid-capture | Exception caught, camera stopped, error logged |
| MongoDB Atlas unavailable | Falls back to local Docker MongoDB |
| Local MongoDB unavailable | Error logged, photo still saved to captures/ |
| Invalid photo ID in URL | Returns 400 or redirects with flash message |
| Unauthorised API request | Returns 401 JSON response |
| Duplicate photo upload | Returns 200, skips insert |
| Gunicorn worker timeout | Increased to 120s, pagination limits query size |

## 6. Environment Variables

| Variable | Where Used | Description |
|----------|------------|-------------|
| LOCAL_URI | Pi + web | Local MongoDB connection string |
| ATLAS_URI | Pi + web | MongoDB Atlas connection string |
| MONGO_DB | Pi + web | Database name |
| MONGO_COLLECTION | Pi + web | Collection name |
| API_TOKEN | Pi + web | Token for API authentication |
| SECRET_KEY | Web | Flask session secret |
| BUTTON_PIN | Pi | GPIO pin number |
| COOLDOWN_SEC | Pi | Camera cooldown |
| SETTLE_TIME | Pi | Exposure settle time |
| EXPOSURE_COMP | Pi | Exposure value |
| ANALOGUE_GAIN | Pi | Sensor gain |
| SHARPNESS | Pi | Image sharpness |
| CONTRAST | Pi | Image contrast |
| SATURATION | Pi | Image saturation |