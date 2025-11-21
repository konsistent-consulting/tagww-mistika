from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import os
from dbxTools import dbxTools

def init(self):
    self.setClassName("Dropbox Out") 
    self.color=QColor(0x0061fe)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addEncryptedProperty("accessToken")
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
    accessToken = self.accessToken.strip()
    if accessToken == "":
        res = self.critical("dropboxOut:accessToken", "'accessToken' can not be empty") and res
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
    accessToken = self.accessToken.strip()
    dbx = dbxTools(self)

    if not dbx.connect(accessToken):
        return False

    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
            relPath = up.getRelPath()
            for f in files:
                if self.isCancelled():
                    return False
                name = "{}{}".format(relPath, os.path.basename(f))
                if not name.startswith("/"):
                    name = "/" + name
                res = dbx.uploadFile(f, name) and res
            out.addUniversalPath(up)
    return res