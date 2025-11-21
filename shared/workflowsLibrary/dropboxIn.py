from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from Mistika.classes import CuniversalPath
from dbxTools import dbxTools


def init(self):
    self.setClassName("Dropbox In")
    self.color=QColor(0x0061fe)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addEncryptedProperty("accessToken")
    self.addProperty("dropboxFilePath", "Leave empty to download all the Dropbox files")
    self.addProperty("localPath")
    self.addProperty("areYouSure")
    self.addProperty("deleteAfterDownload")
    self.setPropertyVisible("areYouSure", False)
    self.addProperty("objectName")
    self.bypassSupported=True
    self.setSupportedTypes(self.NODETYPE_INPUT)
    self.setComplexity(100)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    accessToken = self.accessToken.strip()
    localPath = self.evaluate(self.localPath).strip()
    areYouSure = self.areYouSure
    if localPath == "":
        res = self.critical("dropboxIn:path", "'localPath' can not be empty") and res
    if accessToken == "":
        res = self.critical("dropboxIn:accessToken", "'accessToken' can not be empty") and res
    if not areYouSure:
        res = self.critical("dropboxIn:notSure", "can not delete files from Dropbox after download if not sure") and res
    return res

def process(self):
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    if self.bypassEnabled:
        return True

    res = True

    dropboxFilePath = self.evaluate(self.dropboxFilePath).strip()
    
    if not dropboxFilePath.startswith("/") and not dropboxFilePath == "":
        dropboxFilePath = "/" + dropboxFilePath
    accessToken = self.accessToken.strip()
    
    localPath = self.evaluate(self.localPath).strip()
    deleteAfterDownload = self.deleteAfterDownload

    dbx = dbxTools(self)

    if not dbx.connect(accessToken):
        return False
 
    fileList = dbx.downloadPath(dropboxFilePath, localPath, deleteAfterDownload)[1]
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