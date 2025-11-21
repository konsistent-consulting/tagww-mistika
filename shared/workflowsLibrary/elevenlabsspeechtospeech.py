from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem
import requests
import json

def init(self):
    self.setClassName("ElevenLabs Speech To Speech")
    self.addConnector("audio",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)     
    self.setAcceptConnectors(True,"audio_%") 
    self.addProperty("apiKey")
    self.addProperty("voice", "21m00Tcm4TlvDq8ikWAM")
    self.addProperty("model", "eleven_multilingual_sts_v2")
    self.addProperty("dstPath")
    self.addProperty("format", "mp3_44100_128")
    self.addProperty("_voiceList", "")
    self.addProperty("_modelList", "")
    self.addProperty("stability", 0.50)
    self.addProperty("similarityBoost", 0.80)
    self.addProperty("style", 0.00)
    self.addProperty("useSpeakerBoost", True)
    self.bypassSupported=True
    self.color=QColor(255,255,255)
    return True

def isReady(self):
    res = True
    if self.bypassSupported and self.bypassEnabled:
        return True
    if not self.apiKey.strip():
        res=self.critical("11sts:isReady:apikey","apiKey can not be empty","apiKey")
    return res

def process(self):
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
        dst.setExtension("mp3")

        #-------------------------------------------------------------------------------------------------------------------
        CHUNK_SIZE = 1024

        sts_url = f"https://api.elevenlabs.io/v1/speech-to-speech/{self.voice}/stream"
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.apiKey.strip()
        }

        query = {"output_format":self.format}

        data = {
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        files = {
            "audio": open(f, "rb")
        }

        response = requests.post(sts_url, headers=headers, json=data, files=files, params=query, stream=True)

        if response.ok:
            with open(dst.getFilePath(), "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
            print("Audio stream saved successfully.")
            dst.readMetadataFromFile()
            output.addUniversalPath(dst)
        else:
            res = self.critical("textToSpeech:error", response.json()["detail"]["message"]) and res
            self.addFailedUP(dst)
        #-------------------------------------------------------------------------------------------------------------------
  return res

def  onPropertyUpdated(self,name):
    if name=="apiKey":
        headers = {
        "Accept": "application/json",
        "xi-api-key": self.apiKey.strip(),
        "Content-Type": "application/json"
        }
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        data = response.json()
        try:
            voiceList = [f"{voice['name']}$$${voice['voice_id']}" for voice in data['voices']]
        except KeyError:
            return
        self._voiceList = voiceList

        responseModels = requests.get("https://api.elevenlabs.io/v1/models", headers=headers)
        dataModels = responseModels.json()
        modelList = [f"{model['name']}$$${model['model_id']}" for model in dataModels if 'sts' in model['model_id']]
        print(modelList)
        self._modelList = modelList
        self.rebuild()