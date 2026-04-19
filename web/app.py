import os
import base64
import logging
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import random 
from dotenv import load_dotenv


load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI        =  os.getenv("MONGO_URI")
MONGO_DB         =  os.getenv("MONGO_DB")
MONGO_COLLECTION =  os.getenv("MONGO_COLLECTION")
ATLAS_URI        = os.getenv("ATLAS_URI")

app = Flask(__name__)
app.secret_key =    os.getenv("SECRET_KEY")

log = logging.getLogger(__name__)

# ── MongoDB ───────────────────────────────────────────────────────────────────
def get_collection():
    """Try Atlas first, fall back to local if unavailable."""
    try:
        client = MongoClient(ATLAS_URI, serverSelectionTimeoutMS=3000)
        # Ping to verify the connection actually works
        client.admin.command("ping")
        log.info("Using Atlas")
        return client[MONGO_DB][MONGO_COLLECTION]
    except Exception:
        log.warning("Atlas unavailable — falling back to local MongoDB")
        client = MongoClient(LOCAL_URI)
        return client[MONGO_DB][MONGO_COLLECTION]

# ── Image processing ──────────────────────────────────────────────────────────
def apply_edits(image_b64: str, brightness: float, contrast: float, saturation: float, filter_name: str,  rotation: int = 0) -> str:
    """Apply edits to a base64 image and return the edited base64."""
    image_data = base64.b64decode(image_b64)
    img = Image.open(BytesIO(image_data)).convert("RGB")
    # Rotation of the image

    if rotation == 90:
        img = img.rotate(90, expand=True)
    elif rotation == 180:
        img = img.rotate(180, expand=True)
    elif rotation == 270:
        img = img.rotate(270, expand=True)


    # Now we deal with the brightness/contrast/saturation

    # 1.0 = unchanged, 2.0 = double, 0.5 = half
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)

    
    # Filtering (fun part)

    if filter_name == "bw":
        # grayscale our image
        
        img = ImageOps.grayscale(img).convert("RGB") # The reason why we convert it back to rgb
                                                     # after grayscaling it is because when its grayscale
                                                     # its whats called single channel and most systems work
                                                     # on the default RGB triple channel this is just for safety
    elif filter_name == "blur":
        # Adding a gausssian blur
        img = img.filter(ImageFilter.GaussianBlur(radius=5))

    elif filter_name == "random":
        if random.random() > 0.5:
            img = InamgeOps.posterize(img, 2)

        if random.random() > 0.5:
            img = ImageOps.invert(img)

        if random.random() > 0.5:
            img = img.filter(ImageFilter.GaussianBlur(radius=3))

        if random.random() > 0.5:
            img = img.convert("HSV")
            h, s, v = img.split()
            h = h.point(lambda p: (p + random.randinit(20, 80)) % 255)
            img = Image.merge("HSV", (h, s, v)).convert("RGB")

        



    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")




    
# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    tag_filter = request.args.get("tag", "").strip()
    page       = int(request.args.get("page", 1))
    per_page   = 12
    collection = get_collection()

    query = {}
    if tag_filter:
        query = {"$or": [{"ai_tags": tag_filter}, {"user_tags": tag_filter}]}

    total  = collection.count_documents(query)
    photos = list(collection.find(query, {
        "filename":    1,
        "captured_at": 1,
        "user_tags":   1,
        "ai_tags":     1,
        "image_b64":   1,  # Small enough now to include
    }).sort("captured_at", -1).skip((page - 1) * per_page).limit(per_page))

    all_tags = sorted(set(
        tag
        for p in collection.find({}, {"ai_tags": 1, "user_tags": 1})
        for tag in p.get("ai_tags", []) + p.get("user_tags", [])
    ))

    total_pages = (total + per_page - 1) // per_page

    return render_template("index.html",
                           photos=photos,
                           all_tags=all_tags,
                           active_tag=tag_filter,
                           page=page,
                           total_pages=total_pages)

@app.route("/photo/<photo_id>")
def photo(photo_id):
    try:
        p = get_collection().find_one({"_id": ObjectId(photo_id)})
        if not p:
            flash("Photo not found", "error")
            return redirect(url_for("index"))
        return render_template("photo.html", photo=p)
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

@app.route("/photo/<photo_id>/edit", methods=["POST"])
def edit_photo(photo_id):
    try:
        raw_tags  = request.form.get("user_tags", "")
        user_tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        notes     = request.form.get("notes", "").strip()
        get_collection().update_one(
            {"_id": ObjectId(photo_id)},
            {"$set": {"user_tags": user_tags, "notes": notes}}
        )
        flash("Photo updated!", "success")
        return redirect(url_for("photo", photo_id=photo_id))
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

@app.route("/photo/<photo_id>/save_edits", methods=["POST"])
def save_edits(photo_id):
    """Apply image edits and save the result back to MongoDB."""
    try:
        collection = get_collection()
        p = collection.find_one({"_id": ObjectId(photo_id)})
        if not p:
            return jsonify({"error": "Photo not found"}), 404

        brightness   = float(request.form.get("brightness", 1.0))
        contrast     = float(request.form.get("contrast", 1.0))
        saturation   = float(request.form.get("saturation", 1.0))
        filter_name  = request.form.get("filter", "none")
        rotation     = int(request.form.get("rotation", 0))
        # Use original if it exists, otherwise use current
        source_b64 = p.get("original_image_b64") or p["image_b64"]

        # Store original on first edit so it can always be restored
        if not p.get("original_image_b64"):
            collection.update_one(
                {"_id": ObjectId(photo_id)},
                {"$set": {"original_image_b64": p["image_b64"]}}
            )

        edited_b64 = apply_edits(source_b64, brightness, contrast, saturation, filter_name, rotation)

        collection.update_one(
            {"_id": ObjectId(photo_id)},
            {"$set": {
                "image_b64":   edited_b64,
                "last_edit":   {
                    "brightness":  brightness,
                    "contrast":    contrast,
                    "saturation":  saturation,
                    "filter":      filter_name,
                    "rotation":    rotation,
                }
            }}
        )
        flash("Edits saved!", "success")
        return redirect(url_for("photo", photo_id=photo_id))
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

@app.route("/photo/<photo_id>/thumbnail")
def thumbnail(photo_id):
    try:
        p = get_collection().find_one(
            {"_id": ObjectId(photo_id)},
            {"thumbnail_b64": 1, "image_b64": 1}
        )
        if not p:
            return "", 404

        # Use pre-generated thumbnail if available, otherwise resize on the fly
        b64 = p.get("thumbnail_b64") or p.get("image_b64")
        if not b64:
            return "", 404

        image_data = base64.b64decode(b64)

        # Only resize if we had to fall back to full image
        if not p.get("thumbnail_b64"):
            img = Image.open(BytesIO(image_data))
            img.thumbnail((400, 300))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=60)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")

        return send_file(BytesIO(image_data), mimetype="image/jpeg")
    except Exception:
        return "", 404


@app.route("/photo/<photo_id>/restore", methods=["POST"])
def restore_photo(photo_id):
    """Restore the original unedited photo."""
    try:
        collection = get_collection()
        p = collection.find_one({"_id": ObjectId(photo_id)})
        if not p or not p.get("original_image_b64"):
            flash("No original to restore", "error")
            return redirect(url_for("photo", photo_id=photo_id))

        collection.update_one(
            {"_id": ObjectId(photo_id)},
            {"$set":   {"image_b64": p["original_image_b64"]},
             "$unset": {"original_image_b64": "", "last_edit": ""}}
        )
        flash("Photo restored to original!", "success")
        return redirect(url_for("photo", photo_id=photo_id))
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

@app.route("/photo/<photo_id>/delete", methods=["POST"])
def delete_photo(photo_id):
    try:
        get_collection().delete_one({"_id": ObjectId(photo_id)})
        flash("Photo deleted", "success")
        return redirect(url_for("index"))
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

@app.route("/photo/<photo_id>/download")
def download_photo(photo_id):
    try:
        p = get_collection().find_one({"_id": ObjectId(photo_id)})
        if not p:
            flash("Photo not found", "error")
            return redirect(url_for("index"))
        image_data = base64.b64decode(p["image_b64"])
        return send_file(
            BytesIO(image_data),
            mimetype="image/jpeg",
            as_attachment=True,
            download_name=p["filename"]
        )
    except InvalidId:
        flash("Invalid photo ID", "error")
        return redirect(url_for("index"))

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
