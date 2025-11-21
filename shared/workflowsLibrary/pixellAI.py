import urllib.request
from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem,CuniversalPath
import json
from sgoAuth import sgoAuth
from pixellTools import PixellTools
import urllib
from lxml import html
import time
import webbrowser

def init(self):
    self.setClassName("Pixell AI")
    self.color=QColor(0xff411e)
    self.addConnector("in",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("out",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)     
    self.setAcceptConnectors(True,"in_%") 
    self.addProperty("token4by4")
    self.addProperty("pixellYn", True)
    self.addProperty("model", "M001")
    self.addProperty("deinterlaceYn", False)
    self.addProperty("addGrainYn", False)
    self.addProperty("addGrain", 10)
    self.addProperty("slowMotionYn", False)
    self.addProperty("slowMotion", "SM001")
    self.setPropertyVisible("slowMotion", self.slowMotionYn)
    self.addProperty("colorEnhancementYn", False)
    self.addProperty("resizeYn", False)
    self.addProperty("resizeCode", "RE001")
    self.setPropertyVisible("resizeCode", self.resizeYn)
    self.addProperty("targetFrameRate", "FR001")
    self.addProperty("aspectRatio", "AR001")
    self.addProperty("container", "mp4")
    self.addProperty("_container", "")
    self.addProperty("audioCodec", "AC001")
    self.addProperty("_audioCodec", "")
    self.addProperty("profile", "high")
    self.addProperty("_profile", "")
    self.addProperty("codec", "libx264")
    if self.codec=="libx264":
        self._container = ["mp4$$$mp4","mov$$$mov","mkv$$$mkv"]
        self._audioCodec = ["copy$$$AC001","aac$$$AC002"]
        self._profile = ["High$$$high","Main$$$main"]
        self.container="mp4"
        self.audioCodec="AC001"
        self.profile="high"
    elif self.codec=="libx265":
        self._container = ["mp4$$$mp4","mov$$$mov","mkv$$$mkv"]
        self._audioCodec = ["copy$$$AC001","aac$$$AC002"]
        self._profile = ["High$$$high","Main 10$$$main10"]
        self.container="mp4"
        self.audioCodec="AC001"
        self.profile="high"
    elif self.codec=="vp9":
        self._container = ["mp4$$$mp4","mkv$$$mkv","webm$$$webm"]
        self._audioCodec = ["copy$$$AC001","aac$$$AC002","opus$$$AC004"]
        self._profile = ["Good$$$good","Best$$$best"]
        self.container="mp4"
        self.audioCodec="AC001"
        self.profile="good"
    else:
        self._container = ["mov$$$mov"]
        self._audioCodec = ["copy$$$AC001","pcm$$$AC003"]
        self._profile = ["422 Proxy$$$422proxy","422 LT$$$422lt","422$$$422","422 HQ$$$422hq","4444$$$4444","4444 XQ$$$4444xq"]
        self.container="mov"
        self.audioCodec="AC001"
        self.profile="4444"
    self.addProperty("audioBitRate", "AB001")
    self.addProperty("quality", "1")
    self.addProperty("advancedSettingYn", True)
    self.addProperty("bitRateType", "VBR")
    self.addProperty("targetBitRate", 100)
    self.addProperty("maxBitRate", 100)
    self.addProperty("twoPass", False)
    self.setPropertyVisible("model", self.pixellYn)
    self.setPropertyVisible("addGrain", self.addGrainYn)
    self.setPropertyVisible("quality", not self.advancedSettingYn)
    self.setPropertyVisible("audioBitRate", self.audioCodec != "AC001")
    self.setPropertyVisible("bitRateType", self.advancedSettingYn)
    self.setPropertyVisible("targetBitRate", self.advancedSettingYn)
    self.setPropertyVisible("maxBitRate", self.advancedSettingYn)
    self.setPropertyVisible("twoPass", self.advancedSettingYn)
    self.setPropertyVisible("profile", self.advancedSettingYn)
    self.addProperty("localPath")
    self.bypassSupported=True
    self.addActionToContextMenu("Authenticate")
    return True

def isReady(self):
    res = True
    if self.bypassSupported and self.bypassEnabled:
        return True
    localPath = self.evaluate(self.localPath).strip()
    if not (self.pixellYn or self.deinterlaceYn or self.addGrainYn or self.slowMotionYn or self.colorEnhancementYn):
        res = self.critical("ObjectMatrixIn:mode", "At least one model must be chosen") and res
    if localPath == "":
        res = self.critical("ObjectMatrixIn:path", "'path' can not be empty") and res
    return res

def process(self):
    if self.bypassEnabled:
      return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()
    res = True

    tools=PixellTools(self)
    if not self.token4by4:
        goo = sgoAuth(self)
        code = goo.get_authenticated_service()
        #print(code)
        if code == None: 
            return self.critical("PixellUpload:process:authCanceled", "Authentication error, try again")
        link = "https://www.sgo.es/creditsvalidation?code="+code
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(link, headers=headers)
        f = urllib.request.urlopen(req)
        myData = f.read().decode('utf-8') 
        tree = html.fromstring(myData)
        resultados = tree.xpath('//div[@class="4by4Credits"]/@id')
        #print(resultados)
        try:
            id_ = json.loads(resultados[0])
        except IndexError:
            return self.critical("PixellUpload:process:authCanceled", "Authentication error, server error")
        #print("id: ",id_)
        self.token4by4 = id_["Msg"]
        #print("token: ", self.token4by4)
    apiKey = self.token4by4

    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            self.setPropertiesFromUP(up)
            mfid = up.getMediaFileInfoData()

            f = up.getFilePath()
            if f.lower().endswith(".mov") or f.lower().endswith(".mp4") or f.lower().endswith(".mxf") or f.lower().endswith(".ts"):
                contentType = "video"
            # elif f.lower().endswith(".jpg") or f.lower().endswith(".jpeg") or f.lower().endswith(".png") or f.lower().endswith(".bmp"):
            #     contentType = "image"           
            else:
                res = self.critical("pixellUpload:wrongFileType", "The file type '{}' is not suported".format(f)) and res
                self.addFailedUP(up)
                continue

            frames = mfid.getStringKeyValue(mfid.endsStringKeyToMediaDataFieldStringKey("frames"))
            resX = mfid.getStringKeyValue(mfid.endsStringKeyToMediaDataFieldStringKey("resolutionX"))
            resY = mfid.getStringKeyValue(mfid.endsStringKeyToMediaDataFieldStringKey("resolutionY"))
            size = mfid.getStringKeyValue(mfid.endsStringKeyToMediaDataFieldStringKey("size"))
            print(resX, resY, frames, size)

            if size >= 30 * 1024**3:
                res = self.critical("pixellUpload:wrongFileType", "The file '{}' is bigger than 30Gb".format(f)) and res
                self.addFailedUP(up)
                continue

            creditsCheckResponse = tools.creditCheck(apiKey, resX, resY, frames, self.model, self.pixellYn, self.deinterlaceYn, self.addGrainYn, self.slowMotionYn, self. colorEnhancementYn, self.quality, self.advancedSettingYn)
            print(creditsCheckResponse)
           
            #self.info("pixellUpload:creditInfo", "Actual Credit: '{}'".format(actualCredit))       
            if creditsCheckResponse["resCd"] >= 400:
                res = self.critical("pixellUpload:error", "Error: '{}'".format(creditsCheckResponse["resMsg"])) and res
                self.addFailedUP(up)
                continue
            elif creditsCheckResponse["items"]["requiredCredit"] > 0.0:
                res = self.critical("pixellUpload:noCredits", "Not enough credits, you need to recharge '{}' credits for this job".format(creditsCheckResponse["items"]["requiredCredit"])) and res
                webbrowser.open("https://www.sgo.es/pixell-ai-credits/")
                self.addFailedUP(up)
                continue
            else:
                reponseCredits = tools.getUserCredits(apiKey)
                actualCredit = float(reponseCredits["items"]["credits"])
                try:
                    responseUpload = tools.uploadFile(apiKey, f, contentType)
                except Exception as e:
                    res = self.critical("pixellUpload:error", "Upload Exception: '{}'".format(e)) and res
                    self.addFailedUP(up)
                    continue
                print(responseUpload)
                if responseUpload["resCd"] >= 400:
                    res = self.critical("pixellUpload:error", "Upload Error: '{}'".format(responseUpload["resMsg"])) and res
                    self.addFailedUP(up)
                    continue
                fileId = responseUpload["items"]["fileId"]
                if contentType == "video":              
                    reponseRequest = tools.requestTaskProcessing(contentType=contentType, pixellYn=int(self.pixellYn), model=self.model, fileId=fileId, apiKey=apiKey, deinterlaceYn=int(self.deinterlaceYn), addGrainYn=int(self.addGrainYn), addGrain=self.addGrain,
                                                        colorEnhancementYn=int(self.colorEnhancementYn), slowMotionYn=int(self.slowMotionYn), slowMotion=self.slowMotion, resizeYn=int(self.resizeYn), resizeCode=self.resizeCode, targetFrameRate=self.targetFrameRate,
                                                        aspectRatio=self.aspectRatio, codec=self.codec, container=self.container, audioCodec=self.audioCodec, audioBitRate=self.audioBitRate, quality=self.quality,
                                                        advancedSettingYn=int(self.advancedSettingYn), profile=self.profile, bitRateType=self.bitRateType, targetBitRate=self.targetBitRate, maxBitRate=self.maxBitRate, twoPass=int(self.twoPass))
                    
                    print(reponseRequest)
                    if reponseRequest["resCd"] == 200:
                        reponseCredits = tools.getUserCredits(apiKey)
                        remainCredit = float(reponseCredits["items"]["credits"])
                        self.info("pixellUpload:creditInfo", "Used Credit: '{}'".format(float("%.2f" % (actualCredit-remainCredit))))
                        self.info("pixellUpload:creditInfo", "Remain Credit: '{}'".format(remainCredit))
                        print(reponseCredits)
                        runId = reponseRequest["items"]["runId"]
                        status = None
                        while status != "done" and status != "rejected":
                            if self.isCancelled():
                                return False
                            resposeFileStatus = tools.getFileStatus(apiKey, runId)
                            #print(resposeFileStatus)
                            if resposeFileStatus["resCd"] == 500:
                                res = self.critical("pixellUpload:error", "Checking file status error: '{}'".format(reponseRequest["resMsg"])) and res
                                self.addFailedUP(up)
                                continue
                            status = resposeFileStatus["items"]["status"]
                            print(status)
                            time.sleep(2)
                        if status == "rejected":
                            res = self.critical("pixellUpload:error", "Request rejected") and res
                            self.addFailedUP(up)
                            continue
                        getDownloadLinkResponse = tools.getDownloadLink(apiKey, runId)
                        print(getDownloadLinkResponse)
                    #https://pms-download.4by4inc.com/download/prod/iVW5Kw90Xhdn4hNSuOoN/2024100914041152097699PXS.mp4
                        url = getDownloadLinkResponse["items"]["url"]
                        downLoadedFilePath = tools.descargar_archivo(url, self.localPath)
                     
                        upOut = CuniversalPath(up.getNameConvention(), downLoadedFilePath)
                        #up.readMetadataFromFile()
                        out.addUniversalPath(upOut)
                    elif reponseRequest["resCd"] >= 400:
                        res = self.critical("pixellUpload:error", "Request Error: '{}'".format(reponseRequest["resMsg"])) and res
                        self.addFailedUP(up)
                        continue
        #-------------------------------------------------------------------------------------------------------------------
    # getWorkListResponse = getWorkList("video", apiKey, size=100)
    # print(getWorkListResponse)
    return res

def  onPropertyUpdated(self,name):
    if name=="pixellYn":
        self.setPropertyVisible("model", self.pixellYn)
    if name=="addGrainYn":
        self.setPropertyVisible("addGrain", self.addGrainYn)
    if name=="slowMotionYn":
        self.setPropertyVisible("slowMotion", self.slowMotionYn)
    if name=="resizeYn":
        self.setPropertyVisible("resizeCode", self.resizeYn)
    if name=="advancedSettingYn":
        self.setPropertyVisible("bitRateType", self.advancedSettingYn)
        self.setPropertyVisible("targetBitRate", self.advancedSettingYn)
        self.setPropertyVisible("maxBitRate", self.advancedSettingYn)
        self.setPropertyVisible("twoPass", self.advancedSettingYn)
        self.setPropertyVisible("profile", self.advancedSettingYn)
    if name=="audioCodec":
        self.setPropertyVisible("audioBitRate", self.audioCodec != "AC001")
    if name=="codec":
        if self.codec=="libx264":
            self._container = ["mp4$$$mp4","mov$$$mov","mkv$$$mkv"]
            self._audioCodec = ["copy$$$AC001","aac$$$AC002"]
            self._profile = ["High$$$high","Main$$$main"]
            self.container="mp4"
            self.audioCodec="AC001"
            self.profile="high"
        elif self.codec=="libx265":
            self._container = ["mp4$$$mp4","mov$$$mov","mkv$$$mkv"]
            self._audioCodec = ["copy$$$AC001","aac$$$AC002"]
            self._profile = ["High$$$high","Main 10$$$main10"]
            self.container="mp4"
            self.audioCodec="AC001"
            self.profile="high"
        elif self.codec=="vp9":
            self._container = ["mp4$$$mp4","mkv$$$mkv","webm$$$webm"]
            self._audioCodec = ["copy$$$AC001","aac$$$AC002","opus$$$AC004"]
            self._profile = ["Good$$$good","Best$$$best"]
            self.container="mp4"
            self.audioCodec="AC001"
            self.profile="good"
        else:
            self._container = ["mov$$$mov"]
            self._audioCodec = ["copy$$$AC001","pcm$$$AC003"]
            self._profile = ["422 Proxy$$$422proxy","422 LT$$$422lt","422$$$422","422 HQ$$$422hq","4444$$$4444","4444 XQ$$$4444xq"]
            self.container="mov"
            self.audioCodec="AC001"
            self.profile="4444"
    self.rebuild()


def menuAction(self,name):
    print ("menuAction",name)
    if name=="Authenticate":
        goo = sgoAuth(self)
        code = goo.get_authenticated_service()
        #print(code)       
        if code == None: 
            return self.critical("PixellUpload:process:authCanceled", "Authentication error, try again")
        link = "https://www.sgo.es/creditsvalidation?code="+code
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(link, headers=headers)
        f = urllib.request.urlopen(req)
        myData = f.read().decode('utf-8') 
        tree = html.fromstring(myData)
        resultados = tree.xpath('//div[@class="4by4Credits"]/@id')
        #print(resultados)
        try:
            id_ = json.loads(resultados[0])
        except IndexError:
            return self.critical("PixellUpload:process:authCanceled", "Authentication error, server error")
        #print("id: ",id_)
        self.token4by4 = id_["Msg"]