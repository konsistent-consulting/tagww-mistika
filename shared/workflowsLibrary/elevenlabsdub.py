from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem
import requests
import json
from elevenlabs.client import ElevenLabs
import os
import time

def init(self):
    self.setClassName("ElevenLabs Dub")
    self.addConnector("media",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)     
    self.setAcceptConnectors(True,"media_%") 
    self.addProperty("apiKey")
    self.addProperty("sourceLanguage", "auto")
    self.addProperty("targetLanguage", "en")
    self.addProperty("outputFormat", "mp3")
    self.addProperty("numberOfSpeakers", 1)
    self.addProperty("dstPath")
    self.bypassSupported=True
    self.color=QColor(255,255,255)
    return True

def isReady(self):
    res = True
    if self.bypassSupported and self.bypassEnabled:
        return True
    if not self.apiKey.strip():
        res=self.critical("11dub:isReady:apikey","apiKey can not be empty","apiKey")
    return res

def process(self):
    client = ElevenLabs(api_key = self.apiKey.strip())
    def download_dubbed_file(dubbing_id: str, language_code: str, path) -> str:
        with open(path, "wb") as file:
            for chunk in client.dubbing.get_dubbed_file(dubbing_id, language_code):
                file.write(chunk)
        return path

    def wait_for_dubbing_completion(dubbing_id: str) -> bool:
        MAX_ATTEMPTS = 120
        CHECK_INTERVAL = 10  # In seconds

        for _ in range(MAX_ATTEMPTS):
            metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)
            if metadata.status == "dubbed":
                return True
            elif metadata.status == "dubbing":
                print("Dubbing in progress... Will check status again in",CHECK_INTERVAL,"seconds.",)
                time.sleep(CHECK_INTERVAL)
            else:
                return self.critical("11Dub:dubFailed", "Dubbing failed: {}".format(f))
        print("Dubbing timed out")
        return self.critical("11Dub:dubTimeOut", "Dubbing timed out")

    if self.bypassEnabled:
        return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()

    res = True 

    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            self.setPropertiesFromUP(up)
            f = up.getFilePath()
            dstPath=self.evaluate(self.dstPath).strip()
            dst=self.composeDstFilePath(dstPath,up,False,0)
            dst.setExtension(self.outputFormat)

            try:
                with open(f, "rb") as audio_file:
                    response = client.dubbing.dub_a_video_or_an_audio_file(
                        file=(os.path.basename(f), audio_file),
                        target_lang=self.targetLanguage,
                        mode="automatic",
                        source_lang=self.sourceLanguage,
                        num_speakers=self.numberOfSpeakers,
                        watermark=False,
                    )
            except Exception as e:
                res = self.critical("11Dub:error", "Error: {}".format(e)) and res
                self.addFailedUP(dst)
                continue

            dubbing_id = response.dubbing_id
            if wait_for_dubbing_completion(dubbing_id):
                output_file_path = download_dubbed_file(dubbing_id, self.targetLanguage, dst.getFilePath())
                output.addUniversalPath(dst)
            else:
                res = False
                self.addFailedUP(dst)
    return res

def  onPropertyUpdated(self,name):
    a = 1