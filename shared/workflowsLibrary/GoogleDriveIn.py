from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from Mistika.classes import CuniversalPath
from googleAuth import GoogleAuth
import Mistika
import os
import io
from googleapiclient.http import MediaIoBaseDownload
import json

class GoogleDriveInTools:
    def __init__(self, node):
        self.m_node = node

    def listContentsRecur(self, folderId, drive):
        recuFiles = []
        for item in self.listContents(folderId, drive):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                sublist = self.listContentsRecur(item["id"], drive)
                if sublist is not []:
                    for subitem in sublist:             
                        subitem["path"] = item["name"] + "/" + subitem["path"]                
                        recuFiles.append(subitem)
            else:
                #print("Item: ", item)
                recuFiles.append(item)
        return recuFiles

    def listContents(self, folderId, drive):
        query = f"parents = '{folderId}' and trashed = false"
        try:
            response = drive.files().list(q=query).execute()
        except Exception as e:
            return self.m_node.critical("GoogleDriveOut:process:error", e)
                    
        files = response.get('files')
        nextPageToken = response.get('nextPageToken')

        while nextPageToken:
            response = drive.files().list(q=query, pageToken=nextPageToken).execute()
            files.extend(response.get('files'))
            nextPageToken = response.get('nextPageToken')

        for item in files:
            item["path"] = ""
        
        return files

def init(self):
    self.setClassName("Google Drive In")
    self.color=QColor(0xfbbc04)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("clientId")
    self.addEncryptedProperty("clientSecret")
    self.addProperty("folderId")
    self.addProperty("localPath")
    self.addProperty("recursive")
    self.addProperty("areYouSure")
    self.addProperty("deleteAfterDownload")
    self.setPropertyVisible("areYouSure", False)
    self.addProperty("objectName")
    self.addProperty("credentialsString", "")  
    self.addProperty("_credentialsDict", {})
    self.bypassSupported=True
    self.setSupportedTypes(self.NODETYPE_INPUT)
    self.setComplexity(100)
    self.addActionToContextMenu("Authenticate")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    
    if self.clientId == "":
       res = self.critical("GoogleDriveOut:clientId", "'clientI' can not be empty") and res
    if self.clientSecret == "":
       res = self.critical("GoogleDriveOut:clientSecret", "'clientSecret' can not be empty") and res
    if self.folderId == "":
       res = self.critical("GoogleDriveOut:folderId", "'folderId' can not be empty") and res
    if len(self.localPath) == 0:
        res=self.critical("GoogleDriveOut:localPath:naming","localpath can't be empty") and res
    if len(self.localPath)>0 and not self.localPath.endswith("/"):
        res=self.critical("GoogleDriveOut:localPath:naming","localpath must end with '/' character") and res
    if not os.path.isdir(self.localPath):
        res=self.critical("GoogleDriveOut:localPath:notFound","localpath must be a real path:'{}'".format(self.localPath)) and res
    if not self.areYouSure:
        res = self.critical("dropboxIn:notSure", "can not delete files from Google Drive after download if not sure") and res
    return res

def process(self):
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    if self.bypassEnabled:
        return True

    res = True
 
    localPath = self.evaluate(self.localPath).strip()
    folderId = self.folderId.strip()

    tools = GoogleDriveInTools(self)

    self._credentialsDict = {} if not self.credentialsString else json.loads(self.credentialsString)
    goo = GoogleAuth(self, "https://www.googleapis.com/auth/drive", "drive", "v3", self._credentialsDict)
    drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
    self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

    if drive == "TimeOut": 
        return self.critical("GoogleDriveIn:process:authCanceled", "Authentication timeout")
    elif drive == None:
        return False
    if self.credentialsString == None or self.credentialsString == "{}": 
        return self.critical("GoogleDriveIn:process:authCanceled", "Authentication was rejected") 
    
    #--------------------------------------------------------------------------------------------
    if self.recursive:
        files = tools.listContentsRecur(folderId, drive)
    else:
        files = tools.listContents(folderId, drive)
    if not files:
        return False
    #---------------------------------------------------------------------------------------------
    #print(files)

    idList = [d["id"] for d in files if d["mimeType"] != "application/vnd.google-apps.folder"]
    nameList = [d["path"] + d["name"] for d in files if d["mimeType"] != "application/vnd.google-apps.folder"]
    fileList = [localPath + d["path"] + d["name"] for d in files if d["mimeType"] != "application/vnd.google-apps.folder"]
    pathList = [localPath + d["path"] for d in files if d["mimeType"] != "application/vnd.google-apps.folder"]
    #print(nameList)
    #print(fileList)

    for fileId, fileName, path in zip(idList, nameList, pathList):
        if not os.path.isdir(path):
            os.makedirs(path)

        request = drive.files().get_media(fileId = fileId)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fd=fh, request=request)
        done = False

        while not done:
            status, done = downloader.next_chunk()
            #print("Download progress {0}".format(status.progress()*100))
        
        fh.seek(0)

        with open(os.path.join(localPath, fileName), "wb") as f:
            f.write(fh.read())
            f.close()

        if self.areYouSure and self.deleteAfterDownload:
            try:
                # Delete the file
                drive.files().delete(fileId=fileId).execute()
                #print(f"File with ID {fileId} deleted successfully.")
            except Exception as e:
                self.warning("googleDriveIn:notDel", "Error deleting file {} from Google Drive".format(fileName))

    up = CuniversalPath()
    upList= up.buildUPfromFileList(fileList, self.getNameConvention(), localPath)
    out.setUniversalPaths(upList)
    return res

def onPropertyUpdated(self, name):
    try:
        if name == "deleteAfterDownload":
            self.setPropertyVisible("areYouSure", self.deleteAfterDownload)
            self.areYouSure = not self.deleteAfterDownload
    except AttributeError:
        pass

def menuAction(self,name):
    print ("menuAction",name)
    if name=="Authenticate":
        self.credentialsString = ""
        self._credentialsDict = {}
        goo = GoogleAuth(self, "https://www.googleapis.com/auth/drive", "drive", "v3", self._credentialsDict)
        drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
        self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

        if drive == "TimeOut": 
            return self.critical("GoogleDriveIn:process:authCanceled", "Authentication timeout")
        if self.credentialsString == None or self.credentialsString == "{}": 
            return self.critical("GoogleDriveIn:process:authCanceled", "Authentication was rejected") 