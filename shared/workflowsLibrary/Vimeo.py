import threading
import os
import mimetypes
import vimeo
from Mistika.classes import CuniversalPath

class vimeoToolsProgressPercentage:
    def __init__(self, node, size):
        self.m_size = size
        self.m_current = 0
        self.m_node = node
        node.setComplexity(self.m_size if self.m_size>0 else 100)
        self.m_lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self.m_lock:
            self.m_current += bytes_amount
            percentage = round((self.m_current / float(self.m_size)) * 100)if self.m_size>0 else 100
            self.m_node.progressUpdated(percentage)
            
class vimeoTools:
    def __init__(self, node):
        self.m_node = node
        self.m_token = None
        self.m_client = None

    def connect(self, token):
        self.m_token = token
        #Not in try because it does not return if connection was succesful or not
        self.m_client = vimeo.VimeoClient(
            token = self.m_token,
        )
        return True
    
    def uploadFile(self, file, title, description, view, embed, password):
        try:
            fileData={
                'name': title,
                'description': description,
                'privacy': {
                    'view': view,
                    'embed': embed,
                },
                'password': password
            }
            uri = self.m_client.upload(file, data=fileData)
            # Get the metadata response from the upload and log out the Vimeo.com url
            video_data = self.m_client.get(uri + '?fields=link').json()
            fileData["link"]=video_data['link']
            fileData["uri"]=uri
            self.m_node.info("vimeo:uploadFile:info","'{}' has been uploaded to '{}'. uri: {}".format(file, video_data['link'], uri))

        except Exception as e:
            print((e.message))
            if "Something strange occurred. Please contact the app owners." in e.message:
                self.m_node.critical("vimeo:uploadFile:wrongToken", "The token is not a valid token")
            elif "Unable to upload video. Please get in touch with the app's creator." in e.message:
                self.m_node.critical("vimeo:uploadFile:tokenWithoutPerms","The token does not have enough permissions to upload files")
            elif "You have provided an invalid parameter. Please contact developer of this application." in e.message:
                self.m_node.critical("vimeo:uploadFile:invalidView","Title or description too long or 'disable/unlisted' view options used with basic membership")
            else:
                self.m_node.critical("vimeo:uploadFile:exception", "{}".format(e.message))
            return {}
        print("fileData",fileData)
        return fileData
    
    def checkIfFileIsVideo(self, file):      
        return str(mimetypes.guess_type(file)[0]).startswith('video')


from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import os


def init(self):
    self.color = QColor(0x1fa3e9)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("errorMode",0)
    self.addEncryptedProperty("token")
    self.addProperty("title")
    self.addProperty("description")
    self.addProperty("view", "anybody")
    self.addProperty("embed", "public")
    self.addEncryptedProperty("password")
    self.setPropertyVisible("password", self.view == "password") 
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    token = self.token.strip()
    title = self.evaluate(str(self.title))
    description = self.evaluate(str(self.description))
    view = self.view
    password = str(self.password).strip()
    if token == "":
        res = self.critical("vimeo:token", "'token' can not be empty") and res
    if title == "":
        res = self.critical("vimeo:title", "'title' can not be empty") and res
    if description == "":
        res = self.critical("vimeo:description", "'description' can not be empty") and res
    if view == "password" and password == "":
        res = self.critical("vimeo:password", "'password' can not be empty") and res
    return res

def process(self):
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out = self.getFirstConnectorByName("out")
    func=[None,self.info,self.warning,self.critical][int(self.errorMode)]
    out.clearUniversalPaths()

    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                out.addUniversalPath(up)
        return True

    res = True
    token = self.token.strip()
    view = self.view
    embed = self.embed
    password = str(self.password).strip()
#    print(("Title: " + title + ", Description: "+ description + ", View: " + view + ", Embed: "+ embed + ", Password: " + password))
    
    vimeo = vimeoTools(self)

    vimeo.connect(token)

    for c in inputs:
        for up in c.getUniversalPaths():
            self.setPropertiesFromUP(up)
            newUP=CuniversalPath(up)
            files = newUP.getFiles()
            privateData=newUP.getPrivateData("vimeo")
            if not privateData:
                privateData={}
            for f in files:
                if self.isCancelled():
                    return False
                if vimeo.checkIfFileIsVideo(f):
                    title = self.evaluate(str(self.title))
                    title=up.evaluateTokensString(title)
                    description = self.evaluate(str(self.description))
                    description=up.evaluateTokensString(description)
                    fileData=vimeo.uploadFile(
                        file= f, 
                        title= title,
                        description= description,
                        view= view,
                        embed= embed,
                        password= password,
                        )
                    if fileData:
                        privateData=fileData
                    else:
                        res=self.critical("vimeo:uploadFileFailed", "Unable to upload file") and res
                else: res = func("vimeo:process:notvideo","'{}' is not a video file".format(f),"")
            if privateData:
                newUP.setPrivateData("vimeo",privateData)
                mfid=newUP.getMediaFileInfoData()
                mfid.setToken("vimeo_link",privateData["link"])
                newUP.setMediaFileInfoData(mfid)
            if res:
                out.addUniversalPath(newUP)
            else:
                self.addFailedUP(up)
    return res

def  onPropertyUpdated(self,name):
    try:
        if name=="view":
            self.setPropertyVisible("password", self.view == "password") 
    except AttributeError:
        pass