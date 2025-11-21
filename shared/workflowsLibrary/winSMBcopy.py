import os
import subprocess
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath
from Mistika.Qt import QColor

class winSMBcopier:    
    MODE_MOVE=0
    MODE_COPY=1
    def __init__(self,node,mode):      
        self.m_node=node
        self.m_accumulatedSize=0
        self.m_mode=mode
        
    def connect(self,srv,user,pwd):
        usr="/user:{}".format(user)
        cmd=["net","use",srv,pwd,usr]
        try:
            subprocess.check_call(cmd)
            self.m_node.info("winSMBcopier:connected","connected")
            return True
        except subprocess.CalledProcessError as e:
            self.m_node.critical("winSMBcopier:callError","unable to call 'net'. error={}".format(e))
        except OSError as e:
            self.m_node.critical("winSMBcopier:osError","OS error: {}".format(e))
            print("unable to exec",[cmd]+params,"unable to call 'net'. OS error=",e)
        return False
    def copy(self,src,dst):
        try:
            O_BINARY = os.O_BINARY
        except:
            O_BINARY = 0
        READ_FLAGS = os.O_RDONLY | O_BINARY
        WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY
        BUFFER_SIZE = 128*1024       
        print(src,dst)
        try:
            fin = os.open(src, READ_FLAGS)
            stat = os.fstat(fin)
            fout = os.open(dst, WRITE_FLAGS, stat.st_mode)
            print(src)
            for x in iter(lambda: os.read(fin, BUFFER_SIZE), ""):
                bytes=os.write(fout, x)
                self.m_accumulatedSize+=bytes
                self.updateProgress(self.m_accumulatedSize)
        except OSError as err:            
            self.m_node.critical("winSMBcopier:copy:copyError","Error {}".format(err)) and res
        except IOError as err:                     
            self.m_node.critical("winSMBcopier:copy:copyError2","IO Error {}".format(err)) and res  
        finally:
            try: os.close(fin)
            except: pass
            try: os.close(fout)
            except: pass
            if self.m_mode==MODE_MOVE:
                if os.path.isdir(src):
                    if len(os.listdir(src))==0:
                        os.rmdir(src)
                else: 
                    self.m_node.info("winSMBcopier:copy:move","deleting {}".format(src)) #remove directory if empty
                    os.remove(src)

    def updateProgress(self,current):       
        self.m_node.progressUpdated(current/1024**2)  
    def getInputList(self):
        sz=0
        inputList=[]
        for c in self.m_node.getConnectorsByName("files"):
            for p in c.getUniversalPaths():
                inputList.append(p)
                files=p.getAllFiles()
                for f in files:
                    if os.path.isfile(f):
                        sz+=os.stat(f).st_size
        return [inputList,sz]
    
        
def init(self):
    self.setClassName("Win SMB Copy") 
    self.color=QColor(0x677688)
    self.addProperty("dst");    
    self.addProperty("user")
    self.addEncryptedProperty("pwd")
    self.addProperty("mode",1)
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"files")
    self.bypassSupported=True
    return True

def isReady(self):
    if self.bypassEnabled:
        return True
    if os.name!='nt':
        return self.critical("winSMBcopy:notWindows","this node is supported in windows systems only")
    return True

def process(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    mode=int(self.mode)
    copier=winSMBcopier(self,mode)
    if not copier.connect(self.dst,self.user,self.pwd):
        return False
    inputList,totalSize=copier.getInputList()
    print(totalSize)
    self.setComplexity(totalSize/(1024**2))    
    for p in inputList:
        srcPath=p.getRoot()
        if not srcPath:
            srcPath=p.getPath()           
        print(srcPath)
        files=p.getAllFiles()
        for f in files:
            name=f[len(srcPath):]
            dst=os.path.join(self.dst,name)
            copier.copy(f,dst)
    self.progressUpdated(totalSize/1024**2)
    return True