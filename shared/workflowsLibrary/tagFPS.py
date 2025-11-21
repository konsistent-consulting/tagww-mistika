from logging import critical
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
import Mistika
import os

def init(self):
    self.setClassName("Tag FPS") 
    self.addProperty("fps", "25.00")
    self.addProperty("overwriteIfExists")

    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    
    self.setAcceptConnectors(True,"files")
    #configuring the node
    self.bypassSupported=True
    self.color=QColor(0x677688)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    return res

def process(self):
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out=self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    fps = self.fps
    overWrite = self.overwriteIfExists

    if self.bypassEnabled:
        return True
    
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            newup=CuniversalPath(up)
            newup.unlinkMediaFileInfoData()
            if self.isCancelled():
                return False

            mfid=newup.getMediaFileInfoData()
            if mfid.dataTree() == {}:
                newup.readMetadataFromFile()
                mfid=newup.getMediaFileInfoData()
            fpsGet = mfid.getToken("fps")
            
            if fpsGet is None or overWrite:
                mfid.setToken("fps", fps)

            newup.setMediaFileInfoData(mfid)
            out.addUniversalPath(newup)   
    return res
