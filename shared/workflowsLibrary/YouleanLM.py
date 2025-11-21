from Mistika.Qt import QColor,QRegularExpression
from Mistika.classes import Cconnector,CbaseItem,CexternalAppNodeLink,CuniversalPath,CnameConvention
from Mistika import sgoPaths
import subprocess
import os
import platform
import sys
from baseItemTools import totalNumberOfUPs
import Mistika

def youleanPath(self):
    p=self.evaluate(self.binPath).strip()
    if not p:
        p=getDefaultYoulinePath()
    return p
    
def getDefaultYoulinePath():
    if platform.system()=="Windows":
        return "C:/Program Files/Youlean/Youlean Loudness Meter 2/ylm2.exe"
    elif platform.system()=="Darwin":
        return "/usr/local/bin/ylm2"
    return ""

    
def parseYouleanConfigPullDowns(self):
    def parseList(text,startText,endText="--"):
        lines=text.splitlines()
        startFound=False
        result=[]
        for line in lines:
            line=line.strip()
            if line.startswith(startText):
                startFound=True
                continue
            if startFound:
                if line.startswith(endText):
                    break
                if line:
                    result.append(line)
        return result
    if self.getStore().hasAttribute("configLists"):
        return False
    fp=youleanPath(self)
    if not fp:
        return False
    cmd="{} -h".format(fp)
    configLists={}
    try:
        if platform.system()=="Windows":
            result=subprocess.run([fp, "-h"], creationflags=subprocess.CREATE_NO_WINDOW,capture_output=True, text=True)
        else:
             result=subprocess.run([fp, "-h"], capture_output=True, text=True)
        configLists["preset"]=parseList(result.stdout,"--preset-name <name> available options:")
        configLists["channelConfig"]=["Auto","Custom"]+parseList(result.stdout,"--channel-config <config> available options:")
        configLists["reportType"]=parseList(result.stdout,"--export-type <type> available options:")
        if configLists["preset"] and configLists["channelConfig"] and configLists["reportType"]:
            self.getStore().setAttribute("configLists",configLists)
            setYouleanDefaultsFromConfigLists(self,configLists)
    except Exception as e:
        print("Exception",e)
        return False
    return True
            

def setYouleanDefaultsFromConfigLists(self,configLists=None):
    if not configLists:
        configLists=self.getStore().getAttribute("configLists")
    if configLists:
        self._presetList=configLists["preset"]
        self._channelConfigList=configLists["channelConfig"]
        self._reportTypeList=configLists["reportType"]
        if self._presetList:
            self.preset=self._presetList[0]
        if self._channelConfigList:
            self.channelConfig=self._channelConfigList[0]
        if self._reportTypeList:
            self.reportType=self._reportTypeList[0]
  
def init(self):
    self.setClassName("Youlean Loudness Meter")
    self.color=QColor(0, 84, 129)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)    
    self.addConnector("report",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("passed",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("failed",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"input_%") 
    self.addProperty("_presetList")
    self.addProperty("preset")
    self.addProperty("customPreset","")
    self.addProperty("_channelConfigList")   
    self.addProperty("channelConfig") 
    self.addProperty("generateReport",True)
    self.addProperty("_reportTypeList")   
    self.addProperty("reportType") 
    self.addProperty("reportFolderPath","") 
    self.addProperty("normalize",False)
    self.addProperty("normalizeFolderPath","") 
    self.addProperty("binPath",getDefaultYoulinePath())
    self.addProperty("threads",1)
    self.addProperty("IntegratedMin",-70)
    self.addProperty("IntegratedMax",30)
    self.addProperty("IntegratedDialMin",-70)
    self.addProperty("IntegratedDialMax",30)
    self.addProperty("LoudnessRangeMin",0)
    self.addProperty("LoudnessRangeMax",100)
    self.addProperty("LoudnessRangeDialMin",0)
    self.addProperty("LoudnessRangeDialMax",100)
    self.addProperty("SpeechContentMin",0)
    self.addProperty("SpeechContentMax",100)
    self.addProperty("AverageDynamicsMin",0)
    self.addProperty("AverageDynamicsMax",100)
    self.addProperty("MomentaryMaxMin",-70)
    self.addProperty("MomentaryMaxMax",30)
    self.addProperty("ShortTermMaxMin",-70)
    self.addProperty("ShortTermMaxMax",30)
    self.addProperty("TruePeakMaxMin",-70)
    self.addProperty("TruePeakMaxMax",30)
    
    self.setPropertyVisible("customPreset",False)
    self.bypassSupported=True
    self.setDropToProperty("normalizeFolderPath")
    self.nameConvention=CnameConvention("[path][baseName][.ext]")
    #1=Directories, 2=Files, 3=both
    self.setDropSupportedTypes(1)
    
    if parseYouleanConfigPullDowns(self):
        setYouleanDefaultsFromConfigLists(self)

    return True

def isReady(self):
    if parseYouleanConfigPullDowns(self):
        setYouleanDefaultsFromConfigLists(self)
    if self.bypassSupported and self.bypassEnabled:
        return True    
    res=True
    fp=youleanPath(self)
    if fp=="":
        res=self.critical("youlean:isReady:binUndef","Youlean binary not defined") and res
    elif not os.path.exists(fp):
        res= self.critical("youlean:isReady:binNotFound","Youlean binary not found: ".format(fp)) and res
    if self.preset=="Custom":
        fp=self.evaluate(self.customPreset)
        if fp=="":
            res=self.critical("youlean:isReady:presetUndef","Custom Preset not defined") and res
        elif not os.path.exists(fp):
            res= self.critical("youlean:isReady:presetNotFound","Youlean Preset not found: {fp}".format(fp)) and res        
    return res

def process(self):

    def composeCommandLineParams(self,finalRelExportPath,finalRelNormalizedPath):
        frep=os.path.normpath(finalRelExportPath) if finalRelExportPath else ""
        frep=frep.rstrip("/\\")
        frnp=os.path.normpath(finalRelNormalizedPath) if finalRelNormalizedPath else ""
        frnp=frnp.rstrip("/\\")
        cmdLineParams="--input-file-path \"[input]\""
        cmdLineParams+=" --print-result"
        if self.preset=="Custom":
            cmdLineParams+=" --preset-import-path \"{}\"".format(os.path.normpath(self.customPreset.strip()))
        elif not self.preset=="DEFAULT":
            cmdLineParams+=" --preset-name \"{}\"".format(self.preset)
        if not self.channelConfig=="Auto":
            cmdLineParams+=" --channel-config \"{}\"".format(self.channelConfig)
        if self.generateReport:
            cmdLineParams+=" --export --export-type \"{}\"".format(self.reportType)    
            path=os.path.normpath(self.evaluate(self.reportFolderPath.strip()))
            if frep:
                path=os.path.join(path,os.path.normpath(frep))
            if path!="":
                cmdLineParams+=" --export-folder-path \"{}\"".format(path)         
        if self.normalize:
            cmdLineParams+=" --normalize"
            path=os.path.normpath(self.evaluate(self.normalizeFolderPath.strip()))
            if frnp:
                path=os.path.join(path,os.path.normpath(frnp))
            if path!="":
                cmdLineParams+=" --normalize-folder-path \"{}\"".format(path)
        return cmdLineParams
        
    def getReportExtension(name):
        if (name=="PDF"):
            return "pdf"
        elif (name=="PNG"):
            return "png"
        elif(name=="SVG"):
            return "svg"
        elif(name=="CSV"):
            return "csv"
        elif(name=="DOLBY_CSV"):
            return "csv"
        elif(name=="GRAPH_MEMORY"):
            return "graph"
        elif(name=="TEXT_SUMMARY"):
            return "txt"
        return "unsupported"

    def inRange(data,name,min,max,errors,required):
        if not required and not name in data:
            return True
        v=float(data[name])
        if v<min or v>max:
            errors.append("{} is out of range({},{})".format(name,min,max))
            return False
        return True
    
    def qc(up,data,normalized):
        correct=False
        errors=data["Errors"] if "Errors" in data else []
        required=not normalized
        try:
            inRange(data,"Integrated",self.IntegratedMin,self.IntegratedMax,errors,False)
            inRange(data,"Loudness Range",self.LoudnessRangeMin,self.LoudnessRangeMax,errors,True)
            inRange(data,"Integrated Dial",self.IntegratedDialMin,self.IntegratedDialMax,errors,False)
            inRange(data,"Loudness Range Dial",self.LoudnessRangeDialMin,self.LoudnessRangeDialMax,errors,False)
            inRange(data,"Speech Content",self.SpeechContentMin,self.SpeechContentMax,errors,False)
            inRange(data,"Average Dynamics",self.AverageDynamicsMin,self.AverageDynamicsMax,errors,False)
            inRange(data,"Momentary Max",self.MomentaryMaxMin,self.MomentaryMaxMax,errors,False)
            inRange(data,"Short Term Max",self.ShortTermMaxMin,self.ShortTermMaxMax,errors,False)
            inRange(data,"True Peak Max",self.TruePeakMaxMin,self.TruePeakMaxMax,errors,False)                            
        except Exception as e:
            errors.append("Youlean QC metadata incomplete or not found")
        up.setPrivateData("youlean",data)
        if not errors:            
            correct=True
        else:
            data["Errors"]=errors                
        return [data,correct]
                
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    reportOut = self.getFirstConnectorByName("report")
    correctOut = self.getFirstConnectorByName("passed")
    failedOut = self.getFirstConnectorByName("failed")
    reportOut.clearUniversalPaths()
    correctOut.clearUniversalPaths()
    failedOut.clearUniversalPaths()
    dstUrl=self.evaluate(self.normalizeFolderPath).strip()
    self.setComplexity(totalNumberOfUPs(self)*100)
    if self.bypassEnabled:
        return True
        
    self.progressUpdated(0)
    binfp=youleanPath(self)
    apps=[]
    threads=int(self.threads)
    queue=self.createExecutionQueue(threads)
    cancelled=False
    totalFrames=0
    reportExt=self.reportType.lower()
    self.getStore().setAttribute("apps",{})
    reportFolderPath=self.evaluate(self.reportFolderPath.strip()) if self.generateReport else ""
    for c in inputs:
        if cancelled:
            break
        for up in c.getUniversalPaths():
            finalRelExportPath=""
            finalRelNormalizedPath=""
            # remove output files if they already exist
            if self.generateReport:
                #report
                reportfp=up.evaluateTokensString(reportFolderPath)
                os.makedirs(reportfp,exist_ok=True)
                toRemove=self.composeDstFilePath(reportfp,up,False,0)
                toRemove.setExtension(getReportExtension(self.reportType))
                finalRelExportPath=toRemove.getRelPath()
                try:
                    os.remove(toRemove.getFilePath())
                except:
                    pass
            if self.normalize:
                #normalized
                normalizedfp=up.evaluateTokensString(dstUrl)
                os.makedirs(normalizedfp,exist_ok=True)
                dst=self.composeDstFilePath(normalizedfp,up,False,0)                                
                finalRelNormalizedPath=dst.getRelPath()
                try:
                    os.remove(dst.getFilePath())
                except:
                    pass
            else:
                dst=up
                    
            cmdLineParams=composeCommandLineParams(self,finalRelExportPath,finalRelNormalizedPath)
            mfid=up.getMediaFileInfoData()
            frames=mfid.getToken("Frames")
            frames=100
            fp=up.getFilePath()
            #self.info("youlean:process:up","Preparing {}".format(fp))
            app=self.createExternalApp()
            if platform.system()=='Darwin':
                platormResult=subprocess.run(['sysctl', 'machdep.cpu.brand_string'], capture_output=True, text=True)
                isIntel='Apple' not in platormResult.stdout.strip()
            else:
                isIntel=True
            app.setRosettaMode(isIntel)
            apps.append((app,up,dst))
            if frames>0:
                totalFrames+=frames
                app.setMaxProgress(frames,totalFrames)                  
            app.addHookRX("errorRX",QRegularExpression("^((Normalize)? error\\:.*)$"))
            app.addHookRX("progressRX",QRegularExpression("^frame=\\s*(-?\\d+).*"))
            app.addHookRX("Integrated",QRegularExpression("^Integrated\\s*=\\s*(-?\\d+\\.\\d+) L[UK]FS.*"))
            app.addHookRX("Integrated Dial",QRegularExpression("^Integrated Dial\\s*=\\s*(-?\\d+\\.\\d+) L[UK]FS.*"))
            app.addHookRX("Loudness Range",QRegularExpression("^Loudness Range\\s*=\\s*(-?\\d+\\.\\d+) L[UK].*"))
            app.addHookRX("Loudness Range Dial",QRegularExpression("^Loudness Range Dial\\s*=\\s*(-?\\d+\\.\\d+) L[UK].*"))
            app.addHookRX("Speech Content",QRegularExpression("^Speech Content\\s*=\\s*(-?\\d+\\.\\d+) L[UK]FS.*"))
            app.addHookRX("Average Dynamics",QRegularExpression("^Average Dynamics \\(PLR\\)\\s*=\\s*(-?\\d+\\.\\d+) L[UK].*"))
            app.addHookRX("Momentary Max",QRegularExpression("^Momentary Max\\s*=\\s*(-?\\d+\\.\\d+) L[UK]FS.*"))
            app.addHookRX("Short Term Max",QRegularExpression("^Short Term Max\\s*=\\s*(-?\\d+\\.\\d+) L[UK]FS.*"))
            app.addHookRX("True Peak Max",QRegularExpression("^True Peak Max\\s*=\\s*(-?\\d+\\.\\d+) dBTP.*"))
            app.addHookRX("Report",QRegularExpression("^Export file path:\\s*(.*)\\s*"))
            app.addHookRX("Normalized",QRegularExpression("^Started normalizing:\\s*(.*)\\s*"))
            
            app.setOutputUP(dst)
            app.setPrintOutputs(app.EA_STD_BOTH)
            defTokens=app.createDefaultDict(up)
            args=app.createArgumentsList(self.evaluate(cmdLineParams.strip()),up,defTokens,False)
            #print("args",args)
            quoted=app.quoteList(args)
            if self.isCancelled():
                res=False
                cancelled=True
                queue.cancelAll()
                break
            self.info("youlean:process:args","\"{}\" {}".format(binfp,' '.join(quoted)))
            app.setParams(binfp,args)                   
            queue.addJob(app)
    queue.wait()
    yl=self.getStore().getAttribute("apps")
    reportFP=None
    for app,up,dst in apps:   
        exitCode=app.exitCode()
        fp=up.getFilePath()
        id=str(app.id())
        data=yl[id] if id in yl else {}
        if exitCode<0: #execution error
            print("Unable to process {}. exitCode={}".format(fp,exitCode))
            res=self.critical("youlean:process:error","Unable to process {}. exitCode={}".format(fp,exitCode)) and res
            failedUP=up
            if not data:
                data={}
            if not Errors in data:
                data["Errors"]=[]            
            data["Errors"].append("Unable to execute ylm2. exit with code {}".format(exitCode))                
            failedUP.setPrivateData("youlean",data)
            self.addFailedUP(failedUP)
            failedOut.addUniversalPath(failedUP)
        else:
            if self.normalize:
                if "Normalized" in data:
                    if "Errors" in data:
                        processed=up
                    else:
                        processed=CuniversalPath(self.getNameConvention(),data["Normalized"])
                else:
                    processed=dst
            else:
                processed=up
            errors=data["Errors"] if "Errors" in data else []
            if not self.normalize or not "Errors" in data:                     
                [data,correct]=qc(processed,data,self.normalize)
            else:
                correct=not "Errors" in data
            
            if self.generateReport:
                if "Report" in data:
                    reported=CuniversalPath(self.getNameConvention(),data["Report"])
                else:
                    reportfp=up.evaluateTokensString(reportFolderPath)
                    os.makedirs(reportfp,exist_ok=True)
                    reported=self.composeDstFilePath(reportfp,up,False,0)
                    reported.setExtension(getReportExtension(self.reportType))
                    data["Report"]=reported.getFilePath()
                reported.setPrivateData("youlean",data)
                reportOut.addUniversalPath(reported)
            processed.setPrivateData("youlean",data)            
            if correct:
                correctOut.addUniversalPath(processed)
            else :
                failedOut.addUniversalPath(processed)
            
        app.deleteLater()
    queue.deleteLater()
    self.progressUpdated(self.complexity())
    return res

# appId ExternalApp ID emiting the signal (None is not multithreaded)
# output can be EA_STD_OUT or EA_STD_ERR
# name is the hook name
# rxMatch is the matching QRegularExpressionMatch 
# line is the matching line
def onExternalAppHook(self,appId,output,name,rxMatch,line):
    # you can manage your custom hooks here
    id=str(appId)
    value=rxMatch.captured(1)
    data=self.getStore().getAttribute("apps")
    if not id in data:
        data[id]={}
    if name=="Report":
        value=value.replace('\\','/')
    if name=="errorRX":
        name="Errors"
        if "Errors" in data[id]:
            v=data[id]["Errors"]
            v.append(value)
            value=v
        else:
            v=[]
            v.append(value)
            value=v
            
        
    data[id][name]=value
    self.getStore().setAttribute("apps",data)
    
def onPropertyUpdated(self,name):
    param=None
    prop=None 
    try:
        if name=="preset":
            self.setPropertyVisible("customPreset",self.preset=="Custom")
        elif name=="generateReport":
            visible=self.generateReport==True
            self.setPropertyVisible("reportType",visible)
            self.setPropertyVisible("reportFolderPath",visible)
        elif name=="normalize":
            visible=self.normalize==True
            self.setPropertyVisible("normalizeFolderPath",visible)
#            visible=not visible #QC is hidden when normalizing
#            self.setPropertyVisible("IntegratedMin",visible)
#            self.setPropertyVisible("IntegratedMax",visible)
#            self.setPropertyVisible("IntegratedDialMin",visible)
#            self.setPropertyVisible("IntegratedDialMax",visible)
#            self.setPropertyVisible("LoudnessRangeMin",visible)
#            self.setPropertyVisible("LoudnessRangeMax",visible)
#            self.setPropertyVisible("LoudnessRangeDialMin",visible)
#            self.setPropertyVisible("LoudnessRangeDialMax",visible)
#            self.setPropertyVisible("SpeechContentMin",visible)
#            self.setPropertyVisible("SpeechContentMax",visible)
#            self.setPropertyVisible("XXAverageDynamicsMinX",visible)
#            self.setPropertyVisible("AverageDynamicsMax",visible)
#            self.setPropertyVisible("MomentaryMaxMin",visible)
#            self.setPropertyVisible("MomentaryMaxMax",visible)
#            self.setPropertyVisible("ShortTermMaxMin",visible)
#            self.setPropertyVisible("ShortTermMaxMax",visible)
#            self.setPropertyVisible("TruePeakMaxMin",visible)
#            self.setPropertyVisible("TruePeakMaxMax",visible)
    except AttributeError:
        pass
                