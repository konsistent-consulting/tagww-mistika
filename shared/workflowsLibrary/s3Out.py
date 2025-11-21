from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from wfAWS import wfAWS
import os


def init(self):
    self.setClassName("S3 Out") 
    self.color=QColor(0xe19900)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("bucket")
    self.addEncryptedProperty("key")
    self.addEncryptedProperty("secret")
    self.addProperty("objectName")
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    return True


def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    bucket = self.evaluate(self.bucket).strip()
    key = self.key.strip()
    secret = self.secret.strip()
    if key == "":
        res = self.critical("s3Out:key", "'key' can not be empty") and res
    if secret == "":
        res = self.critical("s3Out:secret", "'secret' can not be empty") and res
    if bucket == "":
        res = self.critical("s3Out:emptyBucket", "'bucket' can not be empty") and res
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
    partes = self.evaluate(self.bucket).strip().split('/', 1)
    bucket = partes[0]
    folder = partes[1] if len(partes) > 1 else ""
    if not folder.endswith('/'):
        folder += '/'
    key = self.key.strip()
    secret = self.secret.strip()
    aws = wfAWS(self)

    if not aws.connect(key, secret) or not aws.checkIfBucketExists(bucket):
        return False

    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
 
            mfid=up.getMediaFileInfoData()
            metadata = mfid.getToken("s3metadata")

            for f in files:
                if self.isCancelled():
                    return False
                name = "{}{}".format(folder, os.path.basename(f))
                if name.startswith("/"):
                    name = name[1:]

                uploaded = aws.uploadFile(f, name, metadata = metadata)
                if not uploaded:
                    self.addFailedUP(up)
                res = res and uploaded
            out.addUniversalPath(up)
    return res