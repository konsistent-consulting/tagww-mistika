from Mistika.classes import Cconnector
import Mistika
from Mistika.Qt import QColor
import os
from googleAuth import GoogleAuth
from apiclient.http import MediaFileUpload
import json

class FolderManager:
    def __init__(self, node):
        self.m_node = node

    def create_folder_structure(self, folder_path, drive, parent):
        folders = folder_path.split('/')
        folders = folders[:-1]
        current_path = ''
        currentParent = parent
        
        for folder in folders:
            current_path = folder + '/'
            currentParent = self.create_folder_in_drive(current_path[:-1], drive, currentParent)
        
        return currentParent

    def create_folder_in_drive(self, folder_name, drive, parent):
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive.files().list(q=query).execute()
        items = results.get('files', [])
        
        if not items:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent]
            }
            try:
                folder = drive.files().create(body=file_metadata, fields='id').execute()
                #print(f'Se ha creado la carpeta con ID: {folder["id"]}')
                return folder['id']
            except Exception as e:
                self.m_node.critical("driveOut:erroFolderCreation", f'Error creating the folder: {e}')
        return items[0]['id']


def init(self):
    self.setClassName("Google Drive Out") 
    self.color=QColor(0xfbbc04)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("clientId")
    self.addEncryptedProperty("clientSecret")
    self.addProperty("folderId")
    self.addProperty("credentialsString", "")  
    self.addProperty("_credentialsDict", {})
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    self.addActionToContextMenu("Authenticate")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    if self.clientId == "":
       res = self.critical("GoogleDriveOut:clientId", "'clientId' can not be empty") and res
    if self.clientSecret == "":
       res = self.critical("GoogleDriveOut:clientSecret", "'clientSecret' can not be empty") and res
    if self.folderId == "":
       res = self.critical("GoogleDriveOut:folderId", "'folderId' can not be empty") and res
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

    self._credentialsDict = {} if not self.credentialsString else json.loads(self.credentialsString)
    goo = GoogleAuth(self, "https://www.googleapis.com/auth/drive", "drive", "v3", self._credentialsDict)
    drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
    self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

    if drive == "TimeOut": 
        return self.critical("GoogleDriveOut:process:authCanceled", "Authentication timeout")
    elif drive == None:
        return False
    if self.credentialsString == None or self.credentialsString == "{}": 
        return self.critical("GoogleDriveOut:process:authCanceled", "Authentication was rejected")    

    fm = FolderManager(self)
    parentId = self.folderId.strip()

    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
            relPath = up.getRelPath()
            for f in files:
                if self.isCancelled():
                    return False
                name = "{}{}".format(relPath, os.path.basename(f))
                if "/" in name:
                    parentId = fm.create_folder_structure(name, drive, self.folderId.strip())
                nameReal = name.split("/")[-1]
                file_metadata = {
                    'name': nameReal,
                    'parents': [parentId]
                }
                media_content = MediaFileUpload(f)
                try:
                    file = drive.files().create(
                        body=file_metadata,
                        media_body=media_content
                    ).execute()
                except Exception as e:
                    res = self.critical("GoogleDriveOut:process:error", e) and res
                    self.addFailedUP(up)
            out.addUniversalPath(up)
    return res

def menuAction(self,name):
    print ("menuAction",name)
    if name=="Authenticate":
        self.credentialsString = ""
        self._credentialsDict = {}
        goo = GoogleAuth(self, "https://www.googleapis.com/auth/drive", "drive", "v3", self._credentialsDict)
        drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
        self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

        if drive == "TimeOut": 
            return self.critical("GoogleDriveOut:process:authCanceled", "Authentication timeout")
        if self.credentialsString == None or self.credentialsString == "{}": 
            return self.critical("GoogleDriveOut:process:authCanceled", "Authentication was rejected") 