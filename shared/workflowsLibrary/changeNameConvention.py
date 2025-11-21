from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CnameConvention,CuniversalPath



def init(self):
    self.setClassName("Change Name Convention")
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.bypassSupported=True
    self.setAcceptConnectors(False, "input")
    self.color = QColor(0, 0, 0)
    return True


def isReady(self):
    res=True
    if self.bypassSupported and self.bypassEnabled:
        return res
    return res


def process(self):
    res=True

    if self.bypassEnabled:
        #this node leaves the outputs empty during bypass as the files are not generated
        return True


    input=self.getFirstConnectorByName("input")
    list=input.getUniversalPaths()
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()
    nc=CnameConvention(self.getNameConvention())

    if not nc.toString():
        nc=self.getWorkflow().getNameConvention()

    for up in list:
        upOut = CuniversalPath(up)
        filePath=up.getFilePath()
        fileInfoData = up.getMediaFileInfoData()

        isSeq = CuniversalPath().isSequenceByExtension(up.getFileName())
        if isSeq:
            minRange = up.getMinRange()
            maxRange = up.getMaxRange()
            upOut.setRange(minRange,maxRange)
            upOut.setSequence(isSeq)

        upOut.setNameConvention(nc)
        upOut.setMediaFileInfoData(fileInfoData)
        upOut.setFilePath(filePath)
        output.addUniversalPath(upOut)

    return res


