from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from Mistika.classes import CuniversalPath
from wfAWS import wfAWS


def init(self):
    self.setClassName("Object Matrix In")
    self.color=QColor(0x00bcc2)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("endpointUrl")
    self.addProperty("bucket")
    self.addEncryptedProperty("key")
    self.addEncryptedProperty("secret")
    self.addProperty("localPath")
    self.addProperty("areYouSure")
    self.addProperty("deleteAfterDownload")
    self.addProperty("newFilesOnly")
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
    bucket = self.evaluate(self.bucket).strip()
    key = self.key.strip()
    secret = self.secret.strip()
    localPath = self.evaluate(self.localPath).strip()
    areYouSure = self.areYouSure
    if localPath == "":
        res = self.critical("ObjectMatrixIn:path", "'path' can not be empty") and res
    if key == "":
        res = self.critical("ObjectMatrixIn:key", "'key' can not be empty") and res
    if secret == "":
        res = self.critical("ObjectMatrixIn:secret", "'secret' can not be empty") and res
    if bucket=="":
        res=self.critical("ObjectMatrixIn:emptyBucket","'bucket' can not be empty") and res
    if not areYouSure:
        res = self.critical("ObjectMatrixIn:notSure", "can not delete files from bucket after download if not sure") and res
    return res

def process(self):
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    if self.bypassEnabled:
        return True

    res = True
    endpointUrl = self.endpointUrl.strip()
    if endpointUrl == "": endpointUrl = None

    partes = self.evaluate(self.bucket).strip().split('/', 1)
    bucket = partes[0]
    folder = partes[1] if len(partes) > 1 else ""

    key = self.key.strip()
    secret = self.secret.strip()
    localPath = self.evaluate(self.localPath).strip()
    deleteAfterDownload = self.deleteAfterDownload
    newFilesOnly = self.newFilesOnly
    aws = wfAWS(self)

    if not aws.connect(key = key, secret = secret, url = endpointUrl) or not aws.checkIfBucketExists(bucket):
        return False

    [res, fileList, metadataList] = aws.downloadPath(folder, localPath, deleteAfterDownload, newFilesOnly)
    up = CuniversalPath()
    upList= up.buildUPfromFileList(fileList, self.getNameConvention(), localPath)
    aws.addMetadataToUp(upList, metadataList)
    out.setUniversalPaths(upList)

    return res

def onPropertyUpdated(self, name):
    try:
        if name == "deleteAfterDownload":
            self.setPropertyVisible("areYouSure", self.deleteAfterDownload)
            self.areYouSure = not self.deleteAfterDownload
    except AttributeError:
        pass
