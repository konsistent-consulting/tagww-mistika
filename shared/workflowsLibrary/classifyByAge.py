from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import os
import time

def init(self):
    res = True
    self.setClassName("Classify By Age")
    self.color=QColor(0x677688)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("younger",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("older",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)

    self.addProperty("timer", 15)
    self.addProperty("timeUnits", 0)
    self.addProperty("dateType", 1)
 
    self.bypassSupported=True
    self.setAcceptConnectors(True, "input")
    return res

def isReady(self):
    res = True
    if (self.bypassSupported and self.bypassEnabled):
        return True
    return res

def process(self):
    res = True
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    
    for c in outputs:
      c.clearUniversalPaths()

    if self.bypassEnabled:
        return True

    timer = self.timer
    timeUnits = [1, 60, 3600, 86400, 604800][int(self.timeUnits)]
    
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            try:
                f = up.getFiles()[0]
            except IndexError:
                continue

            actualTime = time.time()
            timeCheck = [os.stat(f).st_atime, os.stat(f).st_mtime][int(self.dateType)]
            elapsedTime = actualTime - timeCheck

            if elapsedTime < timer*timeUnits:
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "younger")
            else:
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "older")
            
            out.addUniversalPath(up)
    return res