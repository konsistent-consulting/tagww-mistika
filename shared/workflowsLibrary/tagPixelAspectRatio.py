from logging import critical
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath
import Mistika
import os

def init(self):

    self.setClassName("Tag Pixel Aspect Ratio") 
    self.addProperty("pixelAspectRatio", "1")
    self.addProperty("overwriteIfExists")
    self.addProperty("_pixelAspectRatioList", "")
    self.addProperty("_hasTranscoder", True)
    self.addProperty("_hasList", True)
    node=self.getRegisteredItem("ProRes")

    if node:
        try:
            self._pixelAspectRatioList = node._pixelAspectRatioList[1:]
        except AttributeError:
            self._hasList = False
    else:
        self._hasTranscoder = False

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
    if not self._hasTranscoder:
        res=self.critical("tagPixelAspectRatio:errorGettingList","Error getting pixel aspect ratios list") and res 
    if not self._hasList:
        res=self.critical("tagPixelAspectRatio:errorGettingList","Error: this version of Mistika Workflows is not compatible with this node. Need 10.11 or higher") and res       
    return res

def process(self):
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out=self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    pixelAspectRatio = self.pixelAspectRatio
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
            fpsGet = mfid.getToken("pixelAspectRatio")
            if fpsGet is None or overWrite:
                mfid.setToken("pixelAspectRatio", pixelAspectRatio)

            newup.setMediaFileInfoData(mfid)
            out.addUniversalPath(newup)   
    return res
