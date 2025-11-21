from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import requests
import json
            
_WF_WHATSAPP_DEFAULT_MSG="""Put your text here
List of Input Files: 
<?py
for c in self.getConnectors():
    for p in c.getUniversalPaths():
      print (p.toString())
?>"""

def init(self):
    self.color=QColor(0x25d366)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("onlySendIfInput")
    self.addProperty("sendFiles")
    self.addEncryptedProperty("phoneNumberID")
    self.addEncryptedProperty("accessToken")
    self.addProperty("msgTo")
    self.addProperty("body",_WF_WHATSAPP_DEFAULT_MSG)    
    self.bypassSupported=True
    self.setAcceptConnectors(True,"input")
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    return True
    
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    
    if self.phoneNumberID.strip()=="":
      res=self.critical("mail:phoneNumberID","'phoneNumberID' can not be empty") and res
    if self.accessToken.strip()=="":
      res=self.critical("mail:accessToken","'accessToken' can not be empty") and res
    if self.msgTo.strip()=="":
      res=self.critical("mail:msgTo","'msgTo' can not be empty") and res
    return res
    
import json
import requests
import mimetypes

import json
import requests
import mimetypes

import json
import requests
import mimetypes

def process(self):
    res = True
    if self.bypassEnabled:
        return True
    
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    hasInput = False
    files_to_upload = []
    
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            hasInput = True
            files_to_upload.append(up)
    
    if not hasInput and self.onlySendIfInput:
        return True 
    
    headers = {
        "Authorization": "Bearer " + self.accessToken.strip(),
        "Content-Type": "application/json"
    }
    url = f"https://graph.facebook.com/v17.0/{self.phoneNumberID.strip()}/messages"
    
    try:
        body = self.evaluate(self.body)
        chunk_length = 4096
        split_body = [body[i:i + chunk_length] for i in range(0, len(body), chunk_length)]
        
        for body_chunk in split_body:
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.msgTo.strip(),
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": body_chunk
                }
            }
            response = requests.post(url, data=json.dumps(data), headers=headers)
            if "error" in response.json():
                return self.critical("process:smtp", "Error: {}".format(response.json()["error"]["message"]))
        
        if not self.sendFiles:
            return res
        # Subir y enviar archivos si hay alguno
        allowed_mime_types = [
            "image/jpeg", "image/png", "image/webp", 
            "video/mp4", "video/3gpp", 
            "audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg", "audio/opus", 
            "application/pdf", "application/msword", "application/vnd.ms-excel", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            "application/vnd.openxmlformats-officedocument.presentationml.presentation", 
            "application/vnd.ms-powerpoint", "text/plain"
        ]
        
        for up in files_to_upload:
            file_path = up.getFilePath()
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type not in allowed_mime_types:
                res = self.critical("process:smtp", "File not supported: {}".format(file_path)) * res
                self.addFailedUP(up)
                continue
            
            with open(file_path, "rb") as file:
                upload_url = f"https://graph.facebook.com/v17.0/{self.phoneNumberID.strip()}/media"
                upload_headers = {
                    "Authorization": "Bearer " + self.accessToken.strip()
                }
                files = {"file": (file_path, file, mime_type)}
                upload_data = {"messaging_product": "whatsapp", "type": mime_type}
                
                upload_response = requests.post(upload_url, files=files, data=upload_data, headers=upload_headers)
                upload_result = upload_response.json()
                
                if "id" not in upload_result:
                    res = self.critical("process:smtp", "Error uploading: {}".format(upload_result)) * res
                    self.addFailedUP(up)
                    continue
                
                # Determinar el tipo de archivo
                if "image" in mime_type:
                    media_type = "image"
                elif "video" in mime_type:
                    media_type = "video"
                elif "audio" in mime_type:
                    media_type = "audio"
                else:
                    media_type = "document"
                
                # Enviar archivo
                file_id = upload_result["id"]
                file_data = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": self.msgTo.strip(),
                    "type": media_type,
                    media_type: {"id": file_id}
                }
                
                file_response = requests.post(url, data=json.dumps(file_data), headers=headers)
                if "error" in file_response.json():
                    res = self.critical("process:smtp", "Error sending: {}".format(file_response.json()["error"]["message"])) * res
                    self.addFailedUP(up)
    
    except Exception as e:
        return self.critical("error", "Error: {}".format(e))
    
    return res

