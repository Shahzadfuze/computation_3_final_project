import os
import base64
from io import BytesIO
from pymongo import MongoClient
from PIL import Image
from dotenv import load_dotenv

load_dotenv('/home/weakahh_fuze/computation_3_final_project/.env')

col = MongoClient(os.getenv('ATLAS_URI'))['camera_project']['captures']

photos = list(col.find({}, {'_id': 1, 'image_b64': 1, 'thumbnail_b64': 1}))
print(f'Processing {len(photos)} photos...')

for p in photos:
    if p.get('thumbnail_b64'):
        continue

    img = Image.open(BytesIO(base64.b64decode(p['image_b64']))).convert('RGB')
    img.thumbnail((400, 300))

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=60)

    col.update_one(
        {'_id': p['_id']},
        {'$set': {
            'thumbnail_b64': base64.b64encode(buf.getvalue()).decode()
        }}
    )

    print(f"Done: {p['_id']}")

print("All done!")