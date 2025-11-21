from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem,CuniversalPath
import time
import requests
import os

def init(self):
    self.setClassName("Amberscript")
    self.color=QColor(0x005a50)
    self.addConnector("in",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)     
    self.setAcceptConnectors(True,"in_%") 
    self.addProperty("apiKey")
    self.addProperty("language", "en")
    self.addProperty("transcriptionType", "transcription")
    self.addProperty("numberOfSpeakers", "2")
    self.addProperty("glossary", "")
    self.addProperty("_glossaryList", "")
    if self.apiKey and self._glossaryList=="":
        url = "https://api.amberscript.com/api/glossary"
        querystring = {"apiKey":self.apiKey}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        print(response.text)
        data = response.json()
        try:
            glossaryList = [f"{glossary['name']}$$${glossary['id']}" for glossary in data]
            glossaryList = ["No Glossary$$$None"]+glossaryList
            print(glossaryList)
        except Exception:
            pass
        self._glossaryList = glossaryList
    self.addProperty("transcriptionStyle", "cleanread")
    self.addProperty("targetLanguage", "en")
    self.setPropertyVisible("transcriptionStyle", self.transcriptionType == "transcription")
    self.setPropertyVisible("targetLanguage", self.transcriptionType == "translatedSubtitles")
    self.addProperty("outputFormat", "srt")
    self.addProperty("dstPath")
    self.bypassSupported=True
    self.addActionToContextMenu("Authenticate")
    return True

def isReady(self):
    res = True
    if self.bypassSupported and self.bypassEnabled:
        return True
    return res

def process(self):
    if self.bypassEnabled:
      return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()
    res = True

    apiKey = self.apiKey
    language = self.language
    transcriptionType = self.transcriptionType
    numberOfSpeakers= self.numberOfSpeakers
    transcriptionStyle = self.transcriptionStyle
    targetLanguage = self.targetLanguage
    outputFormat = self.outputFormat
    glossaryId = self.glossary
    print(glossaryId)

    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            #self.setPropertiesFromUP(up)
            #mfid = up.getMediaFileInfoData()
            f = up.getFilePath()
            dstPath=self.evaluate(self.dstPath).strip()
            dstPathTokens=up.getStringOverride(dstPath)
            dst=self.composeDstFilePath(dstPathTokens,up,False,0)
            if not os.path.exists(os.path.dirname(str(dst.getFilePath()))):
                os.makedirs(os.path.dirname(str(dst.getFilePath())))
            dst.setExtension(outputFormat)
            
            url = 'https://api.amberscript.com/api/jobs/upload-media'
            if glossaryId == "None":
                querystring = {"jobType":"direct","language":language,"transcriptionType":transcriptionType, "numberOfSpeakers":numberOfSpeakers, "transcriptionStyle":transcriptionStyle, "targetLanguage":targetLanguage, "apiKey":apiKey}
            else:
                querystring = {"jobType":"direct","language":language,"transcriptionType":transcriptionType, "numberOfSpeakers":numberOfSpeakers, "transcriptionStyle":transcriptionStyle, "targetLanguage":targetLanguage, "glossaryId":glossaryId, "apiKey":apiKey}
            files = {'file': open(f, 'rb')}
            response = requests.post(url, files=files, params=querystring)

            if response.status_code == 400:
                self.addFailedUP(up)
                return self.critical("Amberscript:error", response.json()["message"]) and res

            jobId = response.json()["jobStatus"]["jobId"]
            print(jobId)

            status = None
            elapsed=0
            while status != "DONE" and status != "ERROR":
                url = "https://api.amberscript.com/api/jobs/status"
                querystring = {"jobId":jobId,"apiKey":apiKey}
                payload = ""
                response = requests.request("GET", url, data=payload, params=querystring)
                status=response.json()["jobStatus"]["status"]
                elapsed +=2
                print(status, "Elapsed time:", elapsed)
                time.sleep(2)
            if status == "ERROR":
                res = self.critical("Amberscript:error", response.json()["jobStatus"]["errorMsg"]) and res
                self.addFailedUP(up)
                continue
            print("ACABADO")

            url = "https://api.amberscript.com/api/jobs/export-" + outputFormat
            querystring = {"jobId":jobId, "apiKey":apiKey}
            payload = ""
            response = None
            while response == None or hasattr(response, "json") and "invalid_job_status" in response.text:
                response = requests.request("GET", url, data=payload, params=querystring)
                print("Preparing file")
                time.sleep(2)

            with open(dst.getFilePath(), "w", encoding="utf-8") as filee:
                filee.write(response.text)
            out.addUniversalPath(dst)
        #-------------------------------------------------------------------------------------------------------------------
    # getWorkListResponse = getWorkList("video", apiKey, size=100)
    # print(getWorkListResponse)
    return res

def  onPropertyUpdated(self,name):
    if name=="transcriptionType":
        self.setPropertyVisible("transcriptionStyle", self.transcriptionType == "transcription")
        self.setPropertyVisible("targetLanguage", self.transcriptionType == "translatedSubtitles")
    if name=="apiKey":
        url = "https://api.amberscript.com/api/glossary"
        querystring = {"apiKey":self.apiKey}
        payload = ""
        response = requests.request("GET", url, data=payload, params=querystring)
        print(response.text)
        data = response.json()
        try:
            glossaryList = [f"{glossary['name']}$$${glossary['id']}" for glossary in data]
            glossaryList = ["No Glossary$$$None"]+glossaryList
            print(glossaryList)
        except Exception:
            return
        self._glossaryList = glossaryList
    self.rebuild()