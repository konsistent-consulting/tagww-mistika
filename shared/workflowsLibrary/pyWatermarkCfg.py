import Mistika
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika.Qt import QColor

def init(self):
    self.setClassName("Watermark Cfg") 
    self.color=QColor(0x94b4f2)
    self.addProperty("header","HEADER LINE")
    self.addProperty("body"," Body Text Body Text")
    self.addProperty("footer","Mistika Workflows Footer")
    self.addConnector("in",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    return True

def isReady(self):
    res=True
    #if self.header=="":
    #    res=self.critical("PixarWatermark:header","'header' can not be empty") and res
    #if self.body=="":
    #    res=self.critical("PixarWatermark:body","'body' can not be empty") and res
    #if self.footer=="":
    #    res=self.critical("PixarWatermark:footer","'footer' can not be empty") and res
    return res

def process(self):
    input=self.getFirstConnectorByName("in")
    output=self.getFirstConnectorByName("out")
    output.clearUniversalPaths ()
    list=input.getUniversalPaths()
    for p in list:
        if self.isCancelled():
            return False
        data={}
        data["header.text"]=self.header
        data["body.text"]=self.body
        data["footer.text"]=self.footer
        p.setPrivateData("CurvesData",data)
        output.addUniversalPath(p)
    return True
   