from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv('/home/weakahh_fuze/computation_3_final_project/.env')

client = MongoClient(os.getenv('ATLAS_URI'))
col = client['camera_project']['captures']

# Keep only 20 most recent
total = col.count_documents({})
print(f"Total photos: {total}")

keep = [
        p['_id']
            for p in col.find({}, {'_id': 1})
                .sort('captured_at', -1)
                    .limit(20)
                    ]

result = col.delete_many({'_id': {'$nin': keep}})
print(f"Deleted {result.deleted_count} photos")
print(f"Remaining: {col.count_documents({})}")
