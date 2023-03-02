from pymongo import MongoClient
import json
import os



mongo_url = os.environ.get('DB_URI')
mongo_db_name = os.environ.get('DB_NAME')
mongo_client = MongoClient(mongo_url)
db = mongo_client[mongo_db_name]
jobs_cl = db["jobs_cl"]
links_cl = db["links_cl"]
res = links_cl.find({'jobid':'e5174956-9da7-4726-b67e-479f4483c12d','submitted': True})
print(type(res))
for it in res:
    print(str(it))