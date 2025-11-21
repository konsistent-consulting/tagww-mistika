import Mistika
from Mistika import workflows
from Mistika.classes import Cconnector 
from Mistika.classes import CbaseItem
from Mistika.classes import CuniversalPath
from baseItemTools import setPropertiesFromJson
from Mistika.Qt import QPointF,QColor
import json

class CdcpWfBuilder:    
    def __init__(self,node):
        self.m_node=node
        
    def buildWorkflow(self,name,jsonObject,nc):
        wf=workflows.addWorkflow(name)
        wf.setNameConvention(nc)
        # add DCP
        dcp=self.addNode(wf,"DCP",jsonObject,QPointF(600,0))
        #add Reels
        reels=jsonObject["reels"]
        n=0
        filePositionCounter=len(reels)
        for reelJson in reels:
            reel=self.addNode(wf,"DCPReel",reelJson,QPointF(300,n*200)) 
            fromConnector=reel.getFirstConnectorByName("toDCP")
            if not n:
                toConnector=dcp.getFirstConnectorByName("Reel 1")
                fromConnector.link(toConnector)
            else:
                dcp.dropConnector(fromConnector)

            #create compliant File
            compliant=self.addNode(wf,"DCPCompliantFile",reelJson["compliantFile"],QPointF(0,n*100)) 
            compliant.getFirstConnectorByName("VideoOut").link(reel.getFirstConnectorByName("Video"))
            jsonObject=reelJson["sourceFile"]
            sourceFilePath=jsonObject["import"]
            u=CuniversalPath()
            isSequence=u.isSequenceByExtension(sourceFilePath)
            source=wf.importFile(sourceFilePath,"File",isSequence)
            srcOut=self.getOutConnector(source)
            if source:
                setPropertiesFromJson(source,jsonObject)        
                source.pos=QPointF(-300,n*100)
                srcOut.link(compliant.getFirstConnectorByName("VideoIn"))
            # add audio channels
            for key in reelJson["channels"]:
                fileName=reelJson["channels"][key]
                audio=self.addNode(wf,"File",None,QPointF(0,filePositionCounter*100),CbaseItem.NODETYPE_INPUT)
                audio.getFirstConnectorByName("To").link(reel.getFirstConnectorByName(key))
                audio.url=fileName
                filePositionCounter+=1
            #add subtitle file
            fileName=reelJson["subtitleFile"]
            if fileName:
                sub=self.addNode(wf,"File",None,QPointF(0,filePositionCounter*100),CbaseItem.NODETYPE_INPUT)
                sub.getFirstConnectorByName("To").link(reel.getFirstConnectorByName("Subtitle"))
                sub.url=fileName
                filePositionCounter+=1
            n+=1
        wf.update()
        wf.giveBackAffinity()
        return wf    
        
    def getOutConnector(self,node):
        out=node.getFirstConnectorByName("VideoOut")
        if not out:
            out=node.getFirstConnectorByName("To")
        
        return out
            
        
          
    def addNode(self,wf,className,jsonObject=None,pos=None,nodeType=CbaseItem.NODETYPE_TASK):
        node=wf.addNode(className,nodeType)
        if node:
            if jsonObject:
                setPropertiesFromJson(node,jsonObject)        
            if pos:
                node.pos=pos;        
        return node

        
    
def init(self):
    self.setClassName("Auto DCP")
    self.color=QColor(0x677688)
    self.addConnector("json",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.bypassSupported=True
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    return True

def process(self):
    if self.bypassEnabled:
        return  True
    c=self.getFirstConnectorByName("json")
    nc=self.getWorkflow().getNameConvention()
    for up in c.getUniversalPaths():
        if self.isCancelled():
            return False
        files=up.getFiles()
        if not files:
            continue            
        f=open(files[0])
        if f:
            data=json.load(f)
            builder=CdcpWfBuilder(self)
            wf=builder.buildWorkflow(data["title"],data,nc)
            task=Mistika.tasks.addWorkflow(wf)
            config=data["config"]
            if config["autoRun"]:
                task.start()
        else:
            return self.critical("autoDCP:process:notFound","File not found: {}".format(files[0]))
    
    return True