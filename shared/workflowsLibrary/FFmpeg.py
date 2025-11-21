from Mistika.Qt import QColor,QRegularExpression
from Mistika.classes import Cconnector,CbaseItem,CexternalAppNodeLink
from Mistika import sgoPaths
import os
import sys
from baseItemTools import totalNumberOfUPs
import Mistika

def ffmpegPath():
    ext=".exe" if sys.platform == "win32" else ""
    fldr = "/MacOS" if sys.platform == "darwin" else "/bin"
    fp=sgoPaths.apps()+ fldr + "/ffmpeg" + ext
    return fp
    
def init(self):
    self.setClassName("FFmpeg") 
    self.color=QColor(92, 184, 92)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)    
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)    
    self.setAcceptConnectors(True,"input_%") 
    self.addProperty("url")    
    self.addProperty("threads",1)
    self.addProperty("dstExtension","mp4")
    self.addProperty("cmdLineParams","-i [input] -c:v [param1] -b:v [param2] -c:a [param3] [param4] [param5] [param6] [param7] [param8] [output]")
    self.addProperty("param1","h264_nvenc")
    self.addProperty("param2","5M")
    self.addProperty("param3","aac")
    self.addProperty("param4","")
    self.addProperty("param5","")
    self.addProperty("param6","")
    self.addProperty("param7","")
    self.addProperty("param8","")
    
    self.bypassSupported=True
    self.setDropToProperty("url")
    #1=Directories, 2=Files, 3=both
    self.setDropSupportedTypes(1) 
    return True
        
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True    
    fp=ffmpegPath()
    if not os.path.exists(fp):
        return self.critical("ffmpeg:isReady","ffmpeg binary not found: ".format(fp))
    return True


def process(self):      
        
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    out = self.getFirstConnectorByName("output")
    out.clearUniversalPaths()
    dstUrl=self.evaluate(self.url).strip()
    self.setComplexity(totalNumberOfUPs(self)*100)
    if self.bypassEnabled:
        return True
        
    self.progressUpdated(0)
    binfp=ffmpegPath()
    apps=[]
    threads=int(self.threads)    
# First, we create a queue of threads to execute the binary
    queue=self.createExecutionQueue(threads)
    cancelled=False
    totalFrames=0
    for c in inputs:
        if cancelled:
            break
        for up in c.getUniversalPaths():
            mfid=up.getMediaFileInfoData()
            frames=mfid.getToken("Frames")
            fp=up.getFilePath()
            self.info("ffmpeg:process:up","Preparing {}".format(fp))
            dst=self.composeDstFilePath(dstUrl,up,False,0)
            ext=self.evaluate(self.dstExtension.strip())
            if ext:
                dst.setExtension(ext)     
# For each UP to process, we create an instance of the app to execute it
            app=self.createExternalApp()
# Add the new app to the apps list. this list is used at the end to delete them
            apps.append((app,up,dst))
            if frames>0:
                totalFrames+=frames
                app.setMaxProgress(frames,totalFrames)       
# Register the Hooks to parse the command output
            app.addHookRX("errorRX",QRegularExpression("^(Error .*)$"))
            app.addHookRX("progressRX",QRegularExpression("^frame=\\s*(\\d+).*"))
            app.setOutputUP(dst)
# select if we want the app to print its output or not (printing it is not needed for the books to work, it is just for log/debug proposes            
            app.setPrintOutputs(app.EA_STD_BOTH)
# define the default tokens dictionary ([input] [input-firstFile] [output])            
            defTokens=app.createDefaultDict(up)
#parse the cmdLIne tokens            
            args=app.createArgumentsList(self.evaluate(self.cmdLineParams.strip()),up,defTokens)
            args=('-y',)+args # adds -y to cmdline to avoid ffmpeg blocking waiting an overwrite answer
# add " to the elements with spaces
            quoted=app.quoteList(args)
            if self.isCancelled():
                res=False
                cancelled=True
                queue.cancelAll()
                break
            self.info("ffmpeg:process:args","\"{}\" {}".format(binfp,' '.join(quoted)))
#execute the job           
            app.setParams(binfp,args)                   
            queue.addJob(app)
#wait for the apps to finish            
    queue.wait()
#build the output connector and delete all the apps and queue
    for app,up,dst in apps:   
        exitCode=app.exitCode()
        fp=up.getFilePath()
        if exitCode: 
            res=self.critical("ffmpeg:process:error","Unable to process {}. exitCode={}".format(fp,exitCode)) and res
            self.addFailedUP(up)
        else:
            out.addUniversalPath(dst)
        app.deleteLater()
    queue.deleteLater()
    self.progressUpdated(self.complexity())
    return res

# appId ExternalApp emiting the signal
# output can be EA_STD_OUT or EA_STD_ERR
# name is the hook name
# rxMatch is the matching QRegularExpressionMatch 
# line is the matching line
def onExternalAppHook(self,appId,output,name,rxMatch,line):
    # you can manage your custom hooks here
    print("Signal",name,"received from std",output,"(Ignored)")