import Mistika
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem
import json
from token2mdata import token2mdataMapper
    
def init(self):
    self.setClassName("NC To Metadata") 
    self.color=QColor(0x01376b)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL )    
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)    
    self.setAcceptConnectors(True, "input")
    self.bypassSupported=True
    return True

def isReady(self):
    return True


def process(self):
    res=True
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()
    if self.bypassEnabled:
        self.progressUpdated(self.complexity())
        for c in inputs:
            for up in c.getUniversalPaths():
                output.addUniversalPath(up)
        return True
    mapper=token2mdataMapper(self)
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            up=mapper.nc2mdata(up)
            output.addUniversalPath(up)
    return res
