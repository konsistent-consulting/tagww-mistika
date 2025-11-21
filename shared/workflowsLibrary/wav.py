from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem
from Mistika import sgoPaths
import os
import subprocess
from baseItemTools import totalNumberOfUPs
import sys

class wavConverter:   
    def __init__(self,node):      
        self.m_node=node
        
    def convertToWav(self,src,dst,bitsPerSample,sampleRate):
        print(("wavConverter:Convert","{}->{} :{}kbs,{}".format(src.getFileName(),dst.getFilePath(),bitsPerSample,sampleRate)))
        self.m_node.info("wavConverter:Convert","{}:{}:{} kbs:{}".format(src.getFileName(),dst.getFileName(),bitsPerSample,sampleRate))
        # create dst folder if it does not exists
        path=dst.getPath()
        if not os.path.exists(path):
            os.makedirs(path)
        cmd=self.ffmpegPath()
        #params=["-y","-i",src.getFilePath(),"-filter_complex","[0:a]amerge=inputs=4,pan=stereo|c0<c0+c1|c1<c2+c3[a]","-map","[a]"]
        params=["-y","-i",src.getFilePath()]
        if bitsPerSample>0:
            params = params+["-c:a", "pcm_s" + str(bitsPerSample) + "le"]
        if sampleRate>0:        
            params=params+["-ar",str(sampleRate)]
        params=params+[dst.getFilePath()]
        params = [param.replace(' ', '\ ') for param in params]
        paramsFinal = [cmd]+params if sys.platform == "win32" else ' '.join(['\''+cmd+'\'']+params)
        print(paramsFinal)
        try:
            subprocess.check_call(paramsFinal, shell=True)
            return True
        except subprocess.CalledProcessError as e:
            print("unable to exec",paramsFinal,"error",e)
            return self.m_node.critical("wavConverter:convert:call","unable to exec {}. error: {}".format([cmd]+params,e))
        except OSError as e:
            print("unable to exec",paramsFinal,"OS error",e)
            return self.m_node.critical("wavConverter:convert:os","unable to exec {}. error: {}".format([cmd]+params,e))
        return True
    @staticmethod  
    def ffmpegPath():
        ext=".exe" if sys.platform == "win32" else ""
        fldr = "/MacOS" if sys.platform == "darwin" else "/bin"
        fp=sgoPaths.apps()+ fldr + "/ffmpeg" + ext
        return fp
    
def init(self):
    self.setClassName("WAV") 
    self.color=QColor(120,180,180)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)    
    self.addConnector("wav",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)    
    self.setAcceptConnectors(True,"input_%") 
    self.addProperty("url")
    self.addProperty("bitsPerSample",0)
    self.addProperty("sampleRate",0)
    self.bypassSupported=True
    self.setDropToProperty("url")
    #1=Directories, 2=Files, 3=both
    self.setDropSupportedTypes(1) 
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True    
    fp=wavConverter.ffmpegPath();
    if not os.path.exists(fp):
        return self.critical("wavConverter:isReady","ffmpeg binary not found: ".format(fp))
    return True

def process(self):
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    out = self.getFirstConnectorByName("wav")
    out.clearUniversalPaths()
    dstUrl=self.evaluate(self.url).strip()
    wav=wavConverter(self)
    self.setComplexity(totalNumberOfUPs(self)*100)
    current=0
    if self.bypassEnabled:
        return True
        
    self.progressUpdated(0)
    for c in inputs:
        for input in c.getUniversalPaths():
            if self.isCancelled():
                return False
            dst=self.composeDstFilePath(dstUrl,input,False,0)
            dst.setExtension("wav")
            res=wav.convertToWav(input,dst,int(self.bitsPerSample),int(self.sampleRate)) and res
            out.addUniversalPath(dst)
            current=current+1
            self.progressUpdated(current*100)
    return res
    