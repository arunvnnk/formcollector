from flask import Flask, request,send_file
from pymongo import MongoClient
import json
import os
import logging
import hmac,hashlib
import base64
from string import Template
import datetime

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
jobs = {}
mongo_url = os.environ.get('DB_URI')
mongo_db_name = os.environ.get('DB_NAME')
SECRET_KEY = os.environ.get('APP_SECRET').encode()
mongo_client = MongoClient(mongo_url)
db = mongo_client[mongo_db_name]
jobs_cl = db["jobs_cl"]
links_cl = db["links_cl"]

# Helper function to compute HMAC signature
def compute_hmac_signature(data):
    return hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).hexdigest()

# Helper function to verify HMAC signature
def verify_hmac_signature(data, signature):
    return hmac.compare_digest(compute_hmac_signature(data), signature)

def verify_signature_wrapper(data_to_verify):
    signature = request.headers.get('X-HMAC-Signature')
    timestamp_str = request.headers.get('X-Timestamp')
    if not signature or not timestamp_str:
        return 'Missing HMAC signature or timestamp', 401
    timestamp = datetime.datetime.fromisoformat(timestamp_str)
    five_minutes_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
    
    if timestamp < five_minutes_ago:
        return 'Timestamp is too old', 401
    if not verify_hmac_signature(data_to_verify + timestamp_str, signature):
        return 'Invalid HMAC signature', 401
    
    return 'proceed','ok'

# GET request to retrieve a specific job details
@app.route('/jobdetails/<job_id>', methods=['GET'])
def get_job_details(job_id):
    msg,status = verify_signature_wrapper(job_id)
    if status!='ok':
        return msg,status
    jobs = jobs_cl.find_one({'job_id':job_id})
    if jobs is None:
        return "Job not found",404 
    jobs.pop("htmltemplate")     
    jobs.pop("_id")
    links = links_cl.find({'job_id':job_id,'submitted': True})
    to_return = []
    for li in links:
        temp_li = {}
        temp_li['data_submitted'] = li['data_submitted']
        temp_li["linkid"] = li['linkid']
        to_return.append(temp_li)
    jobs['links'] = to_return
    return json.dumps(jobs),200

# POST request to setup a new job
@app.route('/setupjob/<job_id>', methods=['POST'])
def update_job(job_id):
    msg,status = verify_signature_wrapper(request.data.decode('utf-8'))
    if status!='ok':
        return msg,status
    if job_id is None:
        return "job_id is missing"
    data = request.data.decode('utf-8')
    try:
        jobconfig = json.loads(data)
        html_template = jobconfig["htmltemplate"]
        unique_submissions = jobconfig["links_dict"]
        job_resp= jobconfig["response"]
    except:
        return "Invalid Json format / request structure"
    html_template = base64.b64decode(html_template.encode()).decode()
    jobs_cl.insert_one({'job_id': job_id,'htmltemplate':html_template,'job_response': job_resp})
    link_cl_list = [{'job_id':job_id,'linkid':link,"submitted":False,
                     "data_submitted":"nothing",
                     'template_dict':unique_submissions[link]['template_dict']} 
                     for link in unique_submissions]
    links_cl.insert_many(link_cl_list)
    return "Setup Job Successfully",200

# POST request to submit data for a specific link ID within a job
@app.route('/submitjob/<job_id>/<linkid>', methods=['POST'])
def submit_job(job_id, linkid):
    job_it = jobs_cl.find_one({'job_id':job_id})
    link_it = links_cl.find_one({'linkid':linkid})
    if job_it is None or link_it is None:
        return "Details Not found", 404
    links_cl.update_one({'linkid':linkid},
                        {'$set':{'data_submitted':  dict(request.form),'submitted': True}})
    return job_it['job_response'],200

@app.route('/removejob/<job_id>',methods=['GET'])
def remove_job(job_id):
    msg,status = verify_signature_wrapper(job_id)
    if status!='ok':
        return msg,status
    try:
        links_cl.delete_many({'job_id':job_id})
        jobs_cl.delete_one({'job_id':job_id})
    except Exception as e:
        return (str(e)),500
    return "Job deleted from the server",200

# GET request to retrieve the form for a specific linkid
@app.route('/submitjob/<job_id>/<linkid>', methods=['GET'])
def submit_job_get(job_id, linkid):
    job_it = jobs_cl.find_one({'job_id':job_id})
    link_it = links_cl.find_one({'linkid':linkid})
    if job_it is None or link_it is None:
        return "Details Not found", 404
    html_template = job_it['htmltemplate']
    link_dict = link_it['template_dict']
    to_return = Template(html_template).substitute(**link_dict)
    return to_return, 200

@app.route('/uploadFile/<filename>', methods=['POST'])
def upload_file(filename):
    msg,status = verify_signature_wrapper(filename)
    if status!='ok':
        return msg,status
    if 'file' not in request.files:
        return "no file",500
    file = request.files['file']
    if file.filename == '':
        return 'No selected file',500
    if file:
        file.save(f'/filestore/{filename}')
        return 'File uploaded successfully',200
    return "Upload failed",500

@app.route('/getfile/<filename>', methods=['GET'])
def get_file(filename):
    try:
        return send_file(filename)
    except FileNotFoundError:
        return "Not found",404


@app.route('/gethtmlfile/<filename>', methods=['GET'])
def get_file(filename):
    try:
        return send_file(filename)
    except FileNotFoundError:
        return "Not found",404
    
@app.route('/testconn/',methods=['GET'])
def test_connection():
    msg,status = verify_signature_wrapper(SECRET_KEY.decode())
    if status!='ok':
        return msg,status
    return "Alright",200

if __name__ == '__main__':
    host_ip = os.environ.get('APP_LISTEN')
    port_listen = os.environ.get('APP_PORT')
    app.run(host=host_ip, port=port_listen)