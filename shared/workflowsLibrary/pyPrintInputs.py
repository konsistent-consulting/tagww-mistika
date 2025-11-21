from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem

def init(self):
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)    
    self.setAcceptConnectors(True,"files_%") 
    self.bypassSupported=True
    self.color=QColor(120,180,180)
    self.setSupportedTypes(CbaseItem.NODETYPE_OUTPUT)
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    return True

def process(self):
  if self.bypassEnabled:
      return True
  inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
  for c in inputs:
      print(c.label(),":")
      for up in c.getUniversalPaths():
        if self.isCancelled():
            return False
        print("  ",up.getFileName(),": ",up.toString())
        print(up.getMetadata())
  return True