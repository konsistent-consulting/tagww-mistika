import Mistika
from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import os
import requests
import webbrowser
from datetime import datetime
import json
import msal
import baseItemTools

class oneTools:
    def __init__(self, node):
        self.m_node = node

    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    GRAPH_TOKEN_DIR = Mistika.sgoPaths.workflowsLibrary() + "/onedrive/"
    GRAPH_TOKEN_FILE = Mistika.sgoPaths.workflowsLibrary() + "/onedrive/ms_graph_api_token.json"

    def generate_access_token(self, app_id, scopes):
        if not os.path.exists(self.GRAPH_TOKEN_DIR):
            os.makedirs(self.GRAPH_TOKEN_DIR)
        # Save Session Token as a token file
        access_token_cache = msal.SerializableTokenCache()
        # read the token file
        if os.path.exists(self.GRAPH_TOKEN_FILE):
            access_token_cache.deserialize(open(self.GRAPH_TOKEN_FILE, "r").read())
            token_detail = json.load(open(self.GRAPH_TOKEN_FILE,))
            token_detail_key = list(token_detail['AccessToken'].keys())[0]
            token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
            # print("DatetimeNow: ", datetime.now(), " Expiration: ", token_expiration)
            # if datetime.now() > token_expiration:
            #     # os.remove(self.GRAPH_TOKEN_FILE)
            #     # access_token_cache = msal.SerializableTokenCache()
            #     print("Generating another accestoken form refresh token")
        # assign a SerializableTokenCache object to the client instance
        client = msal.PublicClientApplication(client_id=app_id, token_cache=access_token_cache)
        accounts = client.get_accounts()
        if accounts:
            # load the session
            token_response = client.acquire_token_silent(scopes, accounts[0])
        else:
            # authetnicate your accoutn as usual
            flow = client.initiate_device_flow(scopes=scopes)
            print('user_code: ' + flow['user_code'])
            webbrowser.open('https://microsoft.com/devicelogin')
            token_response = client.acquire_token_by_device_flow(flow)
        with open(self.GRAPH_TOKEN_FILE, 'w') as _f:
            _f.write(access_token_cache.serialize())
        return token_response  

def init(self):
    self.setClassName("OneDrive Out") 
    self.color=QColor(0x0061fe)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("clientId")
    self.addProperty("driveId")
    self.addProperty("folderName")
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    # accessToken = self.accessToken.strip()
    # if accessToken == "":
    #     res = self.critical("dropboxOut:accessToken", "'accessToken' can not be empty") and res
    return res

def process(self):
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                out.addUniversalPath(up)
        return True

    res = True
  
    tools = oneTools(self) 

    client_id = self.clientId
    drive_id = self.driveId
    scopes = ["Files.ReadWrite"]

    access_token = tools.generate_access_token(app_id= client_id, scopes= scopes)
    headers = {
        "Authorization": "Bearer " + access_token["access_token"],
        "Content-Type": "application/json"
    }

    for c in inputs:
        for up in c.getUniversalPaths():
            properties = up.getPrivateData("propertiesOverride")
            print(properties)
            if properties != None:
                baseItemTools.setPropertiesFromJson(self, properties)
            folder_name = self.folderName
            if self.isCancelled():
                return False
            files = up.getAllFiles()
            relPath = up.getRelPath()
            for f in files:
                print(f)

                if folder_name:
                    #EMPIEZA CREAR FOLDER
                    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
                    params = {
                        "$filter": f"name eq '{folder_name}'",
                        "$select": "id,name"
                    }
                    response = requests.get(url, headers=headers, params=params)
                    folder_data = response.json()
                    #print(folder_data)
                    # Check if the folder exists
                    if 'value' in folder_data and len(folder_data['value']) > 0:
                        # Folder already exists, retrieve its ID
                        folder_id = folder_data['value'][0]['id']
                        print(f"Folder '{folder_name}' already exists. Folder ID: {folder_id}")
                    else:
                        # Folder does not exist, create it
                        create_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
                        create_payload = {
                            "name": folder_name,
                            "folder": {},
                            "@microsoft.graph.conflictBehavior": "rename"
                        }
                        create_response = requests.post(create_url, data=json.dumps(create_payload), headers=headers)
                        #print(create_response.json())
                        folder_id = create_response.json()['id']
                        print(f"Folder '{folder_name}' created. Folder ID: {folder_id}")
                else: folder_id = "root"

                #UPLOOADITA     
                request_body = {
                    "item":{
                        "description": "test description",
                        "name": os.path.basename(f)
                    }
                }
                response_upload_session = requests.post(
                    tools.GRAPH_API_ENDPOINT + f"/me/drive/items/{folder_id}:/{os.path.basename(f)}:/createUploadSession",
                    headers= headers,
                    json= request_body
                )
                #print(response_upload_session.json())
                try:
                    upload_url = response_upload_session.json()["uploadUrl"]
                except Exception as e:
                    raise Exception(str(e))

                fileSize = os.path.getsize(f)
                print("File size: ", fileSize)

                with open(f, "rb") as upload:     
                    chunk_size = 32768000
                    chunk_number = fileSize // chunk_size
                    chunk_leftover = fileSize - chunk_size * chunk_number
                    counter = 0

                    while True:
                        chunk_data = upload.read(chunk_size)
                        
                        start_index = counter * chunk_size
                        end_index = start_index + chunk_size


                        if not chunk_data:
                            break;
                        if counter == chunk_number:
                            end_index = start_index + chunk_leftover
                        
                        headers = {
                            "Authorization": "Bearer " + access_token["access_token"],
                            "Content-Length": f"{chunk_size}",
                            "Content-Range": f'bytes {start_index}-{end_index-1}/{fileSize}'
                        }
                        chunk_data_upload_status = requests.put(upload_url, headers=headers, data = chunk_data)


                        print(chunk_data_upload_status.json())
                        if "createdBy" in chunk_data_upload_status.json():
                            file_id = chunk_data_upload_status.json()["id"]
                            print("File upload completed, file ID: ", file_id)
 
                            # Define the endpoint URL to get the parent directory ID
                            file_info_url = f"https://graph.microsoft.com/v1.0/drive/items/{file_id}"
                            headers = {
                                "Authorization": "Bearer " + access_token["access_token"],
                                "Content-Type": "application/json"
                            }
                            response = requests.get(file_info_url, headers=headers)
                            #print("LA ESPUETAAAAAAAAAAAAA" , response.json())
                            parent_directory_id = response.json()['parentReference']['id']

                            # Define the endpoint URL to create the share link for the parent directory
                            url = f"https://graph.microsoft.com/v1.0/drive/items/{parent_directory_id}/createLink"

                            # Define the payload
                            payload = {
                                "type": "view",
                                "scope": "anonymous"
                            }

                            # Send the POST request to create the link
                            response = requests.post(url, data=json.dumps(payload), headers=headers)
                            #print("LA SEGUNDAAA  ESPUETAAAAAAAAAAAAA" , response.json())
                            # Extract the link from the response
                            link = response.json()['link']['webUrl']

                            print(f"Here is the link to the parent directory: {link}")

                            outJson = {
                                "shareLink": link
                            }

                            up.setPrivateData("oneDrive", outJson)

                        elif "error" in chunk_data_upload_status.json():
                            self.critical("dropboxOut:accessToken", "{0} error. --> {1}".format(chunk_data_upload_status.json()["error"]["code"], chunk_data_upload_status.json()["error"]["message"]))
                            self.addFailedUP(up)
                        else:
                            print("Upload Progress: {0}".format(chunk_data_upload_status.json()["nextExpectedRanges"]))
                            counter +=1

                        if self.isCancelled():
                            requests.delete(upload_url)
                
            out.addUniversalPath(up)
    return res