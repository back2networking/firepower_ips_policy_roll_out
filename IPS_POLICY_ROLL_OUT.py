############### Use carefully  ###############
# The script will retrieve all access control  rules from a policy and update all access rules with IPS Policy.
# General terms.  PUT: Modify an Existing Object.  POST: Create a New Object.  GET: Obtaining Data from the System
# API iterations are limited on FMC
# Author - Alexander Chachanidze/achachan@greennet.ge

import json
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

host = "FMC_IP_ADDRESS"
username = "FMC_USERNAME"
password = "FMC_PASSWORD"
domain = "Global"
acp="FMC_ACP_NAME"
ips_policy="FMC_IPS_POLICY_NAME"

#Generates authentication tokens

r = None
headers = {'Content-Type': 'application/json'}
path = "/api/fmc_platform/v1/auth/generatetoken"
server = "https://" + host
url = server + path
try:
    r = requests.post(url, headers=headers, auth=requests.auth.HTTPBasicAuth(username, password), verify=False)
    auth_headers = r.headers
    token = auth_headers.get('X-auth-access-token', default=None)
    domains = auth_headers.get('DOMAINS', default=None)
    domains = json.loads("{\"domains\":" + domains + "}")
    for item in domains["domains"]:
        if item["name"] == domain:
            uuid = item["uuid"]
            break
except Exception as err:
    print ("ERROR" + str(err))


headers['X-auth-access-token'] = token

#Gets Policy uuid and retrieves accessrules uuid

path = "/api/fmc_config/v1/domain/" + uuid + "/policy/accesspolicies"
server = "https://" + host
url = server + path
expanded = ''
fullurl = url + expanded
fullresponse = []
page = 1

r = None
try:
    r = requests.get(fullurl, headers=headers, verify=False)
    status_code = r.status_code
    resp = r.text
    json_response = json.loads(resp)
    for item in json_response["items"]:
        if item["name"]==acp:
            acp_id=item["id"]
            break
except Exception as err:
        print ("ERROR try 2 in connection" + str(err))

path = "/api/fmc_config/v1/domain/" + uuid + "/policy/accesspolicies/"+acp_id+"/accessrules"
server = "https://" + host
url = server + path
fullurl = url + expanded
page = 1
fullresponse=[]

while fullurl:

    r = None
    try:
        r = requests.get(fullurl, headers=headers, verify=False)
        status_code = r.status_code
        resp = r.text
        json_response = json.loads(resp)
        for item in json_response["items"]:
            rule_id = item["id"]
            fullresponse.append(rule_id)
        if status_code == 200:
            if 'next' in json_response['paging'].keys():
                fullurl = json_response['paging']['next'][0] + expanded
                page += 1
            else:
                fullurl = None
        else:
            print ("ERROR")

    except Exception as err:
        print ("ERROR" + str(err))
    finally:
        if r:
            r.close()

#Gets all access rules and their full content

json_response_list=[]
for i in range(0,len(fullresponse)):
 path = "/api/fmc_config/v1/domain/" + uuid + "/policy/accesspolicies/" + acp_id + "/accessrules/" + fullresponse[i]
 server = "https://" + host
 url = server + path
 r = None
 try:
                r = requests.get(url, headers=headers, verify=False)
                status_code = r.status_code
                resp = r.text
                json_response = json.loads(resp)
                json_response.pop('metadata', None)
                json_response.pop('links', None)
                json_response.pop('commentHistoryList', None)
                json_response_list.append(json_response)
 except Exception as err:
        print ("ERROR+"+str(err))
 finally:
                if r:r.close()



path = "/api/fmc_config/v1/domain/"+uuid+"/policy/intrusionpolicies"  # param
url = server + path
if (url[-1] == '/'):
    url = url[:-1]
try:
    r = requests.get(url, headers=headers, verify=False)
    status_code = r.status_code
    resp = r.text
    if (status_code == 200):
        print("GET successful. Response data --> ")
        json_resp = json.loads(resp)
        for item in json_resp["items"]:
            act_ips=item["name"]
            if act_ips==ips_policy:
                ips_id=item["id"]

                print (ips_id)
        print(json.dumps(json_resp, sort_keys=True, indent=4, separators=(',', ': ')))
    else:
        r.raise_for_status()
        print("Error occurred in GET --> " + resp)
except requests.exceptions.HTTPError as err:
    print("Error in connection --> " + str(err))
finally:
    if r: r.close()

#Updates all rules with IPS policy / all existing content of the acl rules will be send back while PUT operation, with new JSON key - in this script new value is 'ipsPolicy'.
#IF you do not send back existing rule configuration aka content and just send a single JSON key, for example ipsPolicy, The rest of the configuration of the rule, except new object value, will be removed.
#Rules with actions: "trust" , "block" and etc will not accept ips value and return an error.
#In case you need to apply different IPS policy, modify with appropriate value -> {'name': 'Maximum Detection', 'id': 'd224e29c-6c27-11e0-ac9d-988fc3da9be6', 'type': 'IntrusionPolicy'}
#IPS Policy id you can get from API-explorer.

for i in range(0,len(fullresponse)):
    path = "/api/fmc_config/v1/domain/" + uuid + "/policy/accesspolicies/" + acp_id + "/accessrules/" + fullresponse[i]
    server = "https://" + host
    url = server + path
    r = None

    file= json_response_list[i]
    file['ipsPolicy']={'name': ips_policy, 'id': ips_id, 'type': 'IntrusionPolicy'}
    print(file)
    try:
        r = requests.put(url, data=json.dumps(file), headers=headers,verify=False)
        status_code = r.status_code
        resp = r.text
        json_response = json.loads(resp)
        if (status_code == 200):
            print(" Rule Updated")
        elif status_code == 404:
            print("ERROR" +resp)
        else:
            print("ERROR  in PUT -->" + resp)
    except Exception as err:
        print("ERROR in connection " + str(err))
    finally:
        if r:
            r.close()
