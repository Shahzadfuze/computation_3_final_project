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