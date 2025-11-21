#v 1.0
# First operational version
#v 0.1
# initial draft
import os
import re
import lxml.etree as ET
import datetime
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika import workflows
from Mistika.Qt import QColor
from pathlib import Path

    
# Cp8Content class ##############################################
class Cp8Content:    
    _FIX_NODE_NAME="FixP2Serial"
    QUADRANT_1=0
    QUADRANT_2=1
    QUADRANT_3=2
    QUADRANT_4=3        
    QUADRANT_PROXY=4
    
    _QUADRANT_NAMES={0:"exP2-1",1:"exP2-2",2:"exP2-3",3:"exP2-4",4:"mP2"}
    _GAMMAS={0:"",1:"HD",2:"HLG"}
    _GAMUTS={0:"",1:"BT.709",2:"BT.2020"}   
 
    def __init__(self,node):      
        self.m_node=node
        self.m_userBit=""
        self.m_gamma=""
        self.m_gamut=""
        self.m_userBitCache={}
        self.m_fixer=node.getRegisteredItem(Cp8Content._FIX_NODE_NAME)
           
    def setUserBit(self,userBit):        
        self.m_userBit=userBit

    def setGamma(self,gamma):        
        self.m_gamma=gamma
        
    def setGamut(self,gamut):        
        self.m_gamut=gamut
        
    def getMediaDirectory(self,quadrant):
        return "AVCLIP" if quadrant<=self.QUADRANT_4 else "VIDEO"
    
    def getRelevantFiles(self,all,quadrant):
        mediaDir=self.getMediaDirectory(quadrant)
        rx=".*\/{}\/CONTENTS\/CLIP\/[a-zA-Z0-9]*\.XML$".format(self._QUADRANT_NAMES[quadrant])
        r = re.compile(rx)
        filtered = [s for s in all if r.match(s)]    
        res=[]        
        for f in filtered: 
            path=os.path.dirname(f) 
            parent=os.path.abspath(os.path.join(path,"..")) 
            mxfPath=os.path.join(parent,mediaDir)
            fileName=os.path.basename(f)   
            base =os.path.splitext(fileName)[0]  
            mxf = os.path.join(mxfPath,base+".MXF")                      
            xml = os.path.join(path,base+".XML") 
            res.append([xml,mxf])
        return res
        
    def findNodes(self,root,id,attribs={}):
        rx='\{{.*\}}{}$'.format(id)
        r = re.compile(rx)
        list=[s for s in root.iter() if r.match(s.tag)]            
        res=[]
        for item in list:
            fit=True
            for key in attribs:
                if attribs[key]!=item.attrib[key]:
                    fit=False
                    break
            if fit:
                res.append(item)
        return res
    
    def patchXmlNodes(self,nodes,value):
        for n in nodes:
            #print u"{} from {} to {}".format(n.tag,n.text,value)   
            n.text=value
            
        
    def fixXML(self,quadrant,xml):
        res=True
        self.m_node.info("changeP8KmetaData:fixXML:start","Patching {}".format(xml)) and res
        try: 
            tree=ET.parse(xml)
            root=tree.getroot()
            if len(self.m_gamma)>0:
                list=self.findNodes(root,'CaptureGamma')
                self.patchXmlNodes(list,self.m_gamma)
                if quadrant==self.QUADRANT_PROXY:         
                    memos=self.findNodes(root,'Memo',attribs={'MemoID':'1'})                
                    for m in memos:                    
                        list=self.findNodes(m,'Text')
                        self.patchXmlNodes(list,"SHV_Gamma:"+self.m_gamma)

            if len(self.m_gamut)>0:
                list=self.findNodes(root,'CaptureGamut')
                self.patchXmlNodes(list,self.m_gamut)
                if quadrant==self.QUADRANT_PROXY:         
                    memos=self.findNodes(root,'Memo',attribs={'MemoID':'2'})                
                    for m in memos:                    
                        list=self.findNodes(m,'Text')
                        self.patchXmlNodes(list,"SHV_Gamut:"+self.m_gamut)                    

            if len(self.m_userBit)>0:
                list=self.findNodes(root,'StartBinaryGroup')
                self.patchXmlNodes(list,self.m_userBit)
                        
            tree.write(xml,encoding="UTF-8",xml_declaration=True)
        except:
            res=self.m_node.critical("changeP8KmetaData:fixXML","Unable to fix {} file".format(xml)) and res
        return res
        
    def fix(self,quadrant,xml,mxf):
        res=True
        res=self.fixXML(quadrant,xml) and res
        if res:
            #print("fixMXF",mxf,xml)
            if not self.m_fixer.fixMXF(mxf,xml):
                res=self.m_node.critical("changeP8KmetaData:fix:fixMXF","Unable to patch {} file".format(mxf)) and res
        return res        

#generates a new userBit if needed or use the previous one created for the same folder
    def calculateUserBit(self,type,up):
        path=up.getPath()
        if path in self.m_userBitCache:
            ub=self.m_userBitCache[path]
            print("userBit found:",ub)
    
        else:
            ub=self.m_fixer.generateBinaryGroup(type)
            self.m_userBitCache[path]=ub
            print("generating userBit:",ub)
        return ub
    
def init(self):
    self.setClassName("Change 8KP2 Metadata")  
    self.color=QColor(0x678ca0)
    self.addProperty("userBit",-1) #-1=Fom Source  0=Date  1=Hash
    self.addProperty("gamma",0) #0=From Source, 1=709 2=2020
    self.addProperty("gamut",0) #0=From Source  1=HD  2=HLG
    self.addConnector("p8",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"p8")
    return True

def isReady(self):
    res=True
    fixer=self.getRegisteredItem(Cp8Content._FIX_NODE_NAME)
    if not fixer:
        res=self.critical("changeP8KmetaData:isReady:fixer","{} not registered, This node works in OSX only".format(Cp8Content._FIX_NODE_NAME)) and res       
    return res

def process(self):
    def getUbCacheKey(up):
        path = Path(up.getFilePath())
        parts=path.parts
        found=False
        while len(parts)>0 and not found:
            found=parts[-1].startswith("exP") or parts[-1]=="mP2"
            parts=parts[:-1]
        if not found:
            return None
        p="/".join(parts)
        #print ("getFilePath",up.getFilePath())
        #print ("getUbCacheKey",p)
        return p
    res=True    
    ubCache={}
    p8=Cp8Content(self)
    ubint=int(self.userBit)

    p8.setGamma(p8._GAMMAS[int(self.gamma)])
    p8.setGamut(p8._GAMUTS[int(self.gamut)])
    out=self.getFirstConnectorByName("out")
    out.clearUniversalPaths()
    for c in self.getConnectorsByName("p8"):
        for p in c.getUniversalPaths():
            if self.isCancelled():
                return False
            pack=p.getParam("megaPack","")            
            if pack!="Panasonic8k":
                res=self.warning("changeP8KmetaData:isReady:notp8","{} is not a Panasonic 8K content. Ignored".format(p.getFilePath())) and res
                continue
            if ubint>=0:
                key=getUbCacheKey(p)
                if key in ubCache:
                    ub=ubCache[key]                    
                else:
                    ub=p8.calculateUserBit(ubint,p)
                    ubCache[key]=ub
                p8.setUserBit(ub)
            out.addUniversalPath(p)
            all=p.getAllFiles()
            for q in p8._QUADRANT_NAMES:
                pairs=p8.getRelevantFiles(all,q)
                for [xml,mxf] in pairs:                    
                    res=p8.fix(q,xml,mxf) and res                    
    return res