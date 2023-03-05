import json
import uuid
import os
import base64
import datetime
import hmac, hashlib
import requests
import sys
from dotenv import load_dotenv
from urllib3 import encode_multipart_formdata

load_dotenv(override=True)
SECRET_KEY =  os.environ.get('APP_SECRET')
ssl_verify = not bool(os.environ.get('insecure', True))
endpoint = os.environ.get('SERVER_END').rstrip('/')

ic = {}
headers = {
    'X-HMAC-Signature': '',
    'Content-Type': 'application/json',
    'X-UTC-Timestamp': ''
    }

def compute_hmac_signature(data):
    return hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()

def ret_utc_timestamp():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def ret_signed_request_header(data,ts):
    headers_tmp = headers
    headers_tmp['X-HMAC-Signature'] = compute_hmac_signature(data+ts)
    headers_tmp['X-Timestamp'] = ts
    return headers_tmp

def setup_job(htmltemplate,identities,job_name,submission_response="Thanks for the submission"):
    url = endpoint + "/setupjob/{}"
    url_submit = endpoint + "/submitjob/{}/"
    jobid = str(uuid.uuid4())
    url = url.format(jobid)
    url_submit = url_submit.format(jobid)
    links_server = {}
    links_local = {}
    for iden in identities:
        link_uuid = str(uuid.uuid4())
        template_dict = {"submit1": f'{url_submit}{link_uuid}'}
        links_server[link_uuid] = {"link_uuid":link_uuid,"template_dict": template_dict,
                 "data_submitted":"nothing","submitted": False}
        links_local[link_uuid] = {"link_uuid":link_uuid,"identity": iden,
                                   "data_submitted":"nothing","submitted": False}
    msg_bytes = base64.b64encode(htmltemplate.encode())
    msg_b64 = msg_bytes.decode()
    utc_timestamp = ret_utc_timestamp()
    data = {
            "links_dict": links_server,
            "htmltemplate": msg_b64,
            "response": submission_response}
    data_to_send = json.dumps(data)
    headers_to_send = ret_signed_request_header(data_to_send,utc_timestamp)
    try:
        response = requests.post(url, data=data_to_send, headers=headers_to_send,verify=ssl_verify)
        print(response.text)
    except Exception as e:
        print("Could not setup job")
        print(str(e))
        return
    ic[jobid] = {"job_id": jobid, "job_links": links_local,
                 "no_of_links":len(identities),"submissions":0,'job_name':job_name}

def test_conn():
    data_to_sign = SECRET_KEY
    utc_timestamp = ret_utc_timestamp()
    headers_to_send = ret_signed_request_header(data_to_sign,utc_timestamp)
    try:
        response = requests.get(endpoint+"/testconn/", data="dummy", headers=headers_to_send,verify=ssl_verify)
    except Exception as e:
        print(str(e))
        return
    print(response.status_code)
    print(response.text)
   

def get_job_details(jobid):
    utc_timestamp = ret_utc_timestamp()
    headers_to_send = ret_signed_request_header(jobid,utc_timestamp)
    jobdetails = f"/jobdetails/{jobid}"
    try:
        response = requests.get(endpoint + jobdetails,data="dummy",headers=headers_to_send,verify=ssl_verify)
    except Exception as e:
        print(str(e))
        return
    if response.status_code in [404,401]:
        print(response.txt)
        return
    job_detail = json.loads(response.text)
    try:
        job = ic[jobid]
    except KeyError:
        print("Cant find the job_id in the internal dictionary")
        return
    job_links_internal = job['job_links']
    count = 0
    for link in job_detail['links']:
        link_id_remote = link['linkid']
        count = count + 1
        try:
            job_links_internal[link_id_remote]['submitted']=True
            job_links_internal[link_id_remote]['data_submitted']=link['data_submitted']
        except:
            print(f"Investigate link-id {link} on the db and locally; seems like there is mismatch")
            continue
    job['job_links'] = job_links_internal
    job['submissions'] = count
    ic[jobid] = job

def run_clear_integration_cache():
    ic = {}

def remove_job(jobid):
    try:
        job = ic[jobid]
    except KeyError:
        print("Job not found")
        return
    url = endpoint + f"/removejob/{jobid}"
    data_to_sign = jobid
    utc_timestamp = ret_utc_timestamp()
    headers_to_send = ret_signed_request_header(data_to_sign,utc_timestamp)
    try:
        response = requests.get(url, data="dummy", headers=headers_to_send,verify=ssl_verify)
    except Exception as e:
        print(str(e))
    if response.status_code == 200:
        print(response.text)
        ic.pop(jobid)

def send_file():
    file_contents = open('html_to_send.html', 'rb').read()
    fname = str(uuid.uuid4())
    files = {'file1':  ('html_to_send.html',file_contents,"text/plain")}
    url = endpoint + f"/uploadFile/{fname}"
    print(url)
    utc_timestamp = ret_utc_timestamp()
    headers_to_send = ret_signed_request_header(fname,utc_timestamp)
    body,ctype = encode_multipart_formdata(files)
    print(body)
    headers_to_send['content-type'] = ctype
    resp = requests.post(url,headers=headers_to_send,data=body,verify=False)
    print(resp.text)  

def run_setup_job():
    fname = sys.argv[1]
    with open(fname, 'r') as file:
        html_template = file.read()
    identities = ["iden1","iden2"]
    setup_job(html_template, identities)

send_file()